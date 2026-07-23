import logging

from odoo import api, fields, models

from .shopify_connector_fulfillment_reader import FulfillmentReadError

_logger = logging.getLogger(__name__)

# Carrier integration_level that auto-books on delivery validation (Q6).
CARRIER_BOOKING_LEVEL = 'rate_and_ship'


class ShopifyConnectorFulfillmentMode2(models.AbstractModel):
    """The 16-condition Mode 2 evaluator + local application (Modes §4).

    Evaluated strictly in order; the first failing condition stops evaluation
    and opens a User review case carrying that condition's named reason, with
    ZERO Odoo stock change. Only a 16/16 pass authorises a local Odoo write
    (validate the deterministically-selected picking). Any ambiguity fails
    closed to review. Q6: fail closed before validation if the configured
    carrier flow would book/charge."""

    _inherit = 'shopify.connector.fulfillment.service'

    # ------------------------------------------------------------------
    # Handler
    # ------------------------------------------------------------------

    @api.model
    def _handle_fulfillment_mode2_evaluation(self, job):
        evidence = self.env[
            'shopify.connector.fulfillment.inbound.evidence'
        ].browse(job.res_id)
        if not evidence.exists():
            return
        # A mode switch back to Mode 1 in flight cancels evaluation back to
        # review without applying (Modes §6 rule 4).
        if self._store_operating_mode(evidence.store_id) != 'mode2':
            self._open_review(evidence, 'mode_not_enabled')
            return
        result = self._evaluate_mode2(evidence)
        if not result['passed']:
            self._open_review(evidence, result['reason'], result.get('detail'))
            return
        self._apply_mode2(evidence, result['plan'])

    # ------------------------------------------------------------------
    # 16-condition checklist (ordered; first failure stops)
    # ------------------------------------------------------------------

    @api.model
    def _evaluate_mode2(self, evidence):
        ctx = {'evidence': evidence, 'store': evidence.store_id, 'plan': {}}
        checks = (
            ('order_binding_missing', self._c1_order_binding),
            ('fulfillment_state_not_success', self._c2_fulfillment_success),
            ('fulfillment_order_unresolved', self._c3_fo_resolved),
            ('product_binding_missing', self._c4_product_bindings),
            ('line_mapping_ambiguous', self._c5_line_mapping),
            ('quantity_overrun', self._c6_no_overrun),
            ('quantity_mismatch', self._c7_quantity_match),
            ('location_unmapped', self._c8_location),
            ('picking_ambiguous', self._c9_picking),
            ('reservation_invalid', self._c10_reservation),
            ('lot_serial_ambiguous', self._c11_lot_serial),
            ('already_reconciled', self._c12_not_duplicate),
            ('binding_conflict', self._c13_no_binding_conflict),
            ('remote_state_changed', self._c14_remote_state),
            ('origin_unconfirmed', self._c15_origin),
            ('mode_not_enabled', self._c16_mode_enabled),
        )
        for reason, check in checks:
            try:
                ok, detail = check(ctx)
            except FulfillmentReadError:
                # A read that cannot complete is an ambiguity -> review, never a
                # silent pass.
                return {'passed': False, 'reason': reason,
                        'detail': 'read incomplete'}
            if not ok:
                return {'passed': False, 'reason': reason, 'detail': detail}
        return {'passed': True, 'reason': None, 'plan': ctx['plan']}

    @api.model
    def _c1_order_binding(self, ctx):
        binding = ctx['evidence'].order_binding_id
        if not binding:
            return False, 'no order binding'
        ctx['order_binding'] = binding
        return True, None

    @api.model
    def _c2_fulfillment_success(self, ctx):
        return bool(ctx['evidence'].fulfillment_status_is_success), None

    @api.model
    def _c3_fo_resolved(self, ctx):
        store = ctx['store']
        order_gid = ctx['order_binding'].shopify_gid
        fulfillments = self._read_order_fulfillments(store, order_gid)
        node = next(
            (f for f in fulfillments
             if isinstance(f, dict)
             and f.get('id') == ctx['evidence'].shopify_fulfillment_gid),
            None,
        )
        if not node:
            return False, 'fulfillment not found on fresh read'
        ctx['fulfillment_node'] = node
        lines = ((node.get('fulfillmentLineItems') or {}).get('nodes')) or []
        if not lines:
            return False, 'no fulfillment line items'
        for line in lines:
            if not isinstance(line, dict) or not (line.get('lineItem') or {}).get('id'):
                return False, 'unresolved fulfillment line'
        ctx['fulfillment_lines'] = lines
        return True, None

    @api.model
    def _c4_product_bindings(self, ctx):
        for line in ctx['fulfillment_lines']:
            gid = (line.get('lineItem') or {}).get('id')
            sale_line = self._resolve_sale_line(ctx['order_binding'], gid)
            if not sale_line or not sale_line.product_id:
                return False, 'missing product for line'
        return True, None

    @api.model
    def _c5_line_mapping(self, ctx):
        mapping = {}
        for line in ctx['fulfillment_lines']:
            gid = (line.get('lineItem') or {}).get('id')
            sale_line = self._resolve_sale_line(ctx['order_binding'], gid)
            if not sale_line:
                return False, 'unmapped line %s' % gid
            if gid in mapping:
                return False, 'ambiguous line %s' % gid
            mapping[gid] = (sale_line, line.get('quantity') or 0)
        ctx['line_mapping'] = mapping
        # Carried into the plan so `_apply_mode2` can write the real
        # cross-fulfillment reconciled-quantity ledger once local validation
        # genuinely succeeds (Theme B) -- never before.
        ctx['plan']['line_mapping'] = mapping
        return True, None

    @api.model
    def _c6_no_overrun(self, ctx):
        # Theme B: a real cross-fulfillment ledger, keyed consistently by the
        # order-level LineItem GID (never `fo_line_item_gid`, which is a
        # different id space -- `reconciled_quantity_ledger()`'s own per-
        # record arithmetic is unrelated and untouched here). Sums only
        # OTHER, already-`applied` evidence records' lines for this exact
        # sale line -- this record's own lines are always empty at
        # evaluation time (the ledger writer runs only after a successful
        # apply, see `_record_reconciled_lines`).
        Line = self.env[
            'shopify.connector.fulfillment.inbound.evidence.line'
        ].sudo()
        for gid, (sale_line, qty) in ctx['line_mapping'].items():
            # Serialize concurrent Mode-2 evaluations of two separate
            # Fulfillment events on the SAME sale line: without this, both
            # evaluations could read the same "already reconciled" sum and
            # both pass, double-spending the ordered quantity (a genuine
            # TOCTOU window). A lock that cannot be acquired right now is
            # itself an inconclusive overrun check -- fail closed rather
            # than proceed on a possibly-stale read.
            locked = sale_line.try_lock_for_update()
            if not locked:
                return False, (
                    'quantity_overrun on %s (locked by a concurrent '
                    'evaluation)' % gid
                )
            already = sum(Line.search([
                ('line_item_gid', '=', gid),
                ('evidence_id.store_id', '=', ctx['store'].id),
                ('evidence_id', '!=', ctx['evidence'].id),
                ('evidence_id.reconciled_state', '=', 'applied'),
            ]).mapped('reconciled_quantity'))
            ordered = int(round(sale_line.product_uom_qty or 0))
            if qty + already > ordered:
                return False, 'quantity_overrun on %s' % gid
        return True, None

    @api.model
    def _c7_quantity_match(self, ctx):
        # The candidate picking's pending demand must equal (or deterministically
        # split to) the fulfillment quantities; compared against Odoo 19
        # stock.move.line.quantity, never qty_done. A quantity/coverage failure
        # across every open candidate is reported HERE as quantity_mismatch;
        # condition 9 is reserved for genuine deterministic-selection ambiguity
        # among candidates that already passed this coverage check.
        ctx['required_qty'] = {
            sale_line.id: qty for gid, (sale_line, qty) in ctx['line_mapping'].items()
        }
        compatible = self._quantity_compatible_pickings(ctx)
        ctx['quantity_compatible_pickings'] = compatible
        if not compatible:
            return False, 'no quantity-compatible picking candidate'
        return True, None

    @api.model
    def _c8_location(self, ctx):
        """F-4 permanent seam: resolve the Shopify fulfillment location
        (already fail-closed on absence/ambiguity/inactive via
        `_resolve_single_location`), then cross-check it against the actual
        picking source warehouse through the sanctioned core extension point
        only (`shopify.connector.location._resolve_odoo_location`) -- never a
        direct read of `shopify.connector.location.mapping`. Condition 7 has
        already narrowed `ctx['quantity_compatible_pickings']` to pickings
        whose demand covers the required lines with no sibling moves; this
        condition further narrows that same list to only the candidates
        whose own source location is the mapped Odoo location or one of its
        descendants, so condition 9's deterministic selection can never land
        on a picking from an incompatible warehouse. No valid mapping (core
        seam absent/returns False; no candidate is location-compatible)
        fails closed to `location_unmapped`, exactly as it always has."""
        node_fos = self._read_fulfillment_orders(
            ctx['store'], ctx['order_binding'].shopify_gid,
        )
        try:
            location_gid = self._resolve_single_location(
                ctx['store'],
                [fo for fo in node_fos if fo.get('status') in ('OPEN', 'IN_PROGRESS')]
                or node_fos,
            )
        except FulfillmentReadError:
            return False, 'location unmapped'
        mapped_location = self.env[
            'shopify.connector.location'
        ]._resolve_odoo_location(ctx['store'], location_gid)
        if not mapped_location:
            return False, 'location unmapped'
        candidates = ctx.get('quantity_compatible_pickings') or []
        compatible = [
            picking for picking in candidates
            if self._picking_location_in_subtree(picking, mapped_location)
        ]
        if not compatible:
            return False, 'location unmapped'
        ctx['quantity_compatible_pickings'] = compatible
        ctx['location_gid'] = location_gid
        ctx['mapped_odoo_location_id'] = mapped_location.id
        return True, None

    @api.model
    def _picking_location_in_subtree(self, picking, mapped_location):
        """True when `picking`'s source location IS the mapped Odoo location
        or a genuine descendant of it, using Odoo's own location-hierarchy
        `parent_path` semantics (the same idiom
        `shopify_connector_location_mapping.py`'s own ancestor/descendant
        overlap guard uses)."""
        if not picking or not mapped_location:
            return False
        source = picking.location_id
        if not source:
            return False
        if source.id == mapped_location.id:
            return True
        mapped_path = mapped_location.parent_path or ''
        source_path = source.parent_path or ''
        return bool(mapped_path) and source_path.startswith(mapped_path)

    @api.model
    def _c9_picking(self, ctx):
        # Reserved for genuine deterministic-selection ambiguity ONLY: condition
        # 7 has already proved at least one quantity-compatible candidate exists.
        picking = self._select_deterministic_picking(ctx)
        if not picking:
            return False, 'no single deterministic picking'
        ctx['picking'] = picking
        ctx['plan']['picking'] = picking
        return True, None

    @api.model
    def _c10_reservation(self, ctx):
        return ctx['picking'].state == 'assigned', 'picking not assigned'

    @api.model
    def _c11_lot_serial(self, ctx):
        for move in ctx['picking'].move_ids:
            if move.product_id.tracking != 'none':
                lines = move.move_line_ids.filtered(lambda ml: ml.lot_id)
                if not lines or sum(lines.mapped('quantity')) < move.product_uom_qty:
                    return False, 'lot/serial ambiguous'
        return True, None

    @api.model
    def _c12_not_duplicate(self, ctx):
        applied = self.env[
            'shopify.connector.fulfillment.inbound.evidence'
        ].sudo().search([
            ('store_id', '=', ctx['store'].id),
            ('shopify_fulfillment_gid', '=', ctx['evidence'].shopify_fulfillment_gid),
            ('reconciled_state', '=', 'applied'),
        ], limit=1)
        return not applied, 'already reconciled'

    @api.model
    def _c13_no_binding_conflict(self, ctx):
        conflict = self.env['shopify.connector.fulfillment.binding'].sudo().search([
            ('store_id', '=', ctx['store'].id),
            ('picking_id', '=', ctx['picking'].id),
            ('shopify_gid', '!=', ctx['evidence'].shopify_fulfillment_gid),
        ], limit=1)
        return not conflict, 'binding conflict'

    @api.model
    def _c14_remote_state(self, ctx):
        # Separately fresh, authoritative Shopify read — deliberately NOT the
        # node captured by condition 3. Performed immediately before the local
        # stock validation that follows a 16/16 pass, through the same
        # sanctioned read-only reader methods, no lock/transaction held across
        # it. Any change, absence, or incompleteness fails closed and never
        # reaches local validation.
        store = ctx['store']
        order_gid = ctx['order_binding'].shopify_gid
        fulfillments = self._read_order_fulfillments(store, order_gid)
        node = next(
            (f for f in fulfillments
             if isinstance(f, dict)
             and f.get('id') == ctx['evidence'].shopify_fulfillment_gid),
            None,
        )
        if not node:
            return False, 'target fulfillment missing on second read'
        if node.get('status') != 'SUCCESS':
            return False, 'remote state changed'
        lines = ((node.get('fulfillmentLineItems') or {}).get('nodes')) or []
        if not lines:
            return False, 'no fulfillment line items on second read'
        second_qty_by_line = {}
        for line in lines:
            if not isinstance(line, dict):
                return False, 'malformed fulfillment line on second read'
            gid = (line.get('lineItem') or {}).get('id')
            if not gid:
                return False, 'unresolved fulfillment line on second read'
            second_qty_by_line[gid] = (
                second_qty_by_line.get(gid, 0) + (line.get('quantity') or 0)
            )
        first_qty_by_line = {}
        for gid, (sale_line, qty) in ctx['line_mapping'].items():
            first_qty_by_line[gid] = first_qty_by_line.get(gid, 0) + qty
        if second_qty_by_line != first_qty_by_line:
            return False, 'fulfillment quantities changed on second read'
        # Location evidence must remain resolvable and unchanged (a fresh read
        # of the same sanctioned FO/location path condition 8 already used).
        node_fos = self._read_fulfillment_orders(store, order_gid)
        try:
            second_location_gid = self._resolve_single_location(
                store,
                [fo for fo in node_fos if fo.get('status') in ('OPEN', 'IN_PROGRESS')]
                or node_fos,
            )
        except FulfillmentReadError:
            return False, 'location evidence changed on second read'
        if second_location_gid != ctx.get('location_gid'):
            return False, 'location evidence changed on second read'
        # F-4: re-resolve and re-confirm the Odoo-location correspondence
        # immediately before local application, through the same sanctioned
        # core seam condition 8 used. A mapping that changed (re-pointed to a
        # different Odoo location, or been disabled/removed) between the
        # first and second read fails closed exactly like any other changed
        # evidence here — never silently reused from condition 8's context.
        second_mapped_location = self.env[
            'shopify.connector.location'
        ]._resolve_odoo_location(store, second_location_gid)
        if (
            not second_mapped_location
            or second_mapped_location.id != ctx.get('mapped_odoo_location_id')
        ):
            return False, 'location evidence changed on second read'
        if not self._picking_location_in_subtree(
            ctx.get('picking'), second_mapped_location,
        ):
            return False, 'location evidence changed on second read'
        return True, None

    @api.model
    def _c15_origin(self, ctx):
        evidence = ctx['evidence']
        return bool(
            evidence.origin_class in ('external_merchant', 'external_app')
            and evidence.origin_confirmed
        ), 'origin unconfirmed'

    @api.model
    def _c16_mode_enabled(self, ctx):
        return self._store_operating_mode(ctx['store']) == 'mode2', 'mode not enabled'

    # ------------------------------------------------------------------
    # Deterministic picking selection (§4.1)
    # ------------------------------------------------------------------

    @api.model
    def _quantity_compatible_pickings(self, ctx):
        """Every open outgoing candidate picking whose pending per-line demand
        covers the required fulfillment quantities AND whose non-done moves
        are exclusively for sale lines this fulfillment evidences (Modes
        §4.1; Theme B P0-B baseline). A picking carrying so much as one
        sibling, un-evidenced move is never a candidate at all -- it is
        excluded here, never validated as a whole and never speculatively
        split; the caller (condition 7/9) surfaces the existing
        `quantity_mismatch`/`picking_ambiguous` review reasons exactly as it
        already does for insufficient coverage or genuine selection
        ambiguity, with no new vocabulary. Read-only, no other selection/
        ambiguity judgement — condition 7 uses this to decide
        `quantity_mismatch`; condition 9's `_select_deterministic_picking`
        uses the same list to decide `picking_ambiguous`."""
        order = ctx['order_binding'].sale_order_id
        required = ctx['required_qty']
        candidates = order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
            and p.location_dest_id.usage == 'customer'
            and p.state in ('assigned', 'confirmed', 'waiting')
        )
        compatible = []
        for picking in candidates:
            demand = {}
            has_sibling_move = False
            for move in picking.move_ids:
                if move.state == 'done':
                    # Historical fact from an earlier, already-completed
                    # partial pass on this same picking; not part of this
                    # candidate's own pending-demand evaluation.
                    continue
                sale_line_id = move.sale_line_id.id
                if sale_line_id not in required:
                    # A sibling, un-evidenced move: this exact Shopify
                    # fulfillment never proves this line, so the whole
                    # picking may never be auto-validated by it.
                    has_sibling_move = True
                    break
                demand[sale_line_id] = demand.get(
                    sale_line_id, 0.0
                ) + move.product_uom_qty
            if has_sibling_move or not demand:
                continue
            covers = all(
                demand.get(line_id, 0.0) >= qty
                for line_id, qty in required.items()
            )
            if covers:
                compatible.append(picking)
        return compatible

    @api.model
    def _select_deterministic_picking(self, ctx):
        # Genuine deterministic-selection ambiguity ONLY: condition 7 already
        # proved at least one quantity-compatible candidate exists, so a
        # coverage failure can never reach here as 'no candidates'. Exactly
        # one compatible candidate -> deterministic; more than one -> ambiguous
        # (never re-classified as quantity_mismatch — coverage is not the
        # problem, selection is).
        compatible = ctx.get('quantity_compatible_pickings')
        if compatible is None:
            compatible = self._quantity_compatible_pickings(ctx)
        if len(compatible) == 1:
            return compatible[0]
        return False

    # ------------------------------------------------------------------
    # Application (16/16 pass): Q6 carrier fail-closed, then local validate
    # ------------------------------------------------------------------

    @api.model
    def _apply_mode2(self, evidence, plan):
        picking = plan.get('picking') if isinstance(plan, dict) else None
        if not picking:
            # A 16/16 pass always carries the deterministic picking; its absence
            # is an internal inconsistency -> fail closed.
            self._open_review(evidence, 'picking_ambiguous')
            return
        if self._carrier_would_book(picking):
            # Q6: fail closed BEFORE any validation (no book/charge).
            self._open_review(evidence, 'carrier_would_book')
            return
        # Bind the picking to the EXTERNAL Fulfillment GID BEFORE validating it,
        # so the outbound `stock.picking._action_done` trigger sees an existing
        # fulfillment binding and does NOT enqueue a duplicate fulfillmentCreate
        # (a picking is one fulfillment event, UNIQUE(store, picking)). This is
        # the inbound-application record: the external fulfillment IS this
        # picking's fulfillment.
        self._bind_external_fulfillment(evidence, picking)
        try:
            self._validate_picking_local(picking)
        except Exception:
            _logger.exception(
                'Mode 2 local validation failed for picking %s; routed to '
                'review.', picking.id,
            )
            self._open_review(evidence, 'reservation_invalid')
            return
        # The ledger is written ONLY here, after local validation has
        # genuinely succeeded (Theme B) -- never at evaluation time, so a
        # validation failure (the except branch above) never records a
        # quantity for an application that did not happen. Runs inside the
        # same transaction as the write below; a later failure in this same
        # job execution rolls both back together.
        self._record_reconciled_lines(
            evidence, plan.get('line_mapping') if isinstance(plan, dict) else None,
        )
        evidence.sudo().write({
            'reconciled_state': 'applied',
            'resolution_at': fields.Datetime.now(),
        })

    @api.model
    def _record_reconciled_lines(self, evidence, line_mapping):
        """Write the cross-fulfillment reconciled-quantity ledger rows
        `_c6_no_overrun` consults for future evaluations (Theme B)."""
        if not line_mapping:
            return
        Line = self.env[
            'shopify.connector.fulfillment.inbound.evidence.line'
        ].sudo()
        for gid, (sale_line, qty) in line_mapping.items():
            Line.create({
                'evidence_id': evidence.id,
                'line_item_gid': gid,
                'sale_line_id': sale_line.id,
                'quantity': qty,
                'reconciled_quantity': qty,
            })

    @api.model
    def _bind_external_fulfillment(self, evidence, picking):
        Binding = self.env['shopify.connector.fulfillment.binding'].sudo()
        existing = Binding.search([
            ('store_id', '=', evidence.store_id.id),
            ('picking_id', '=', picking.id),
        ], limit=1)
        if existing:
            binding = existing
        else:
            binding = Binding.create({
                'store_id': evidence.store_id.id,
                'shopify_gid': evidence.shopify_fulfillment_gid,
                'picking_id': picking.id,
                'order_binding_id': evidence.order_binding_id.id,
                'shopify_status_snapshot': evidence.fulfillment_status_raw,
                'shopify_last_synced_at': fields.Datetime.now(),
            })
        evidence.sudo().write({'fulfillment_binding_id': binding.id})
        return binding

    @api.model
    def _carrier_would_book(self, picking):
        """Q6: True when the configured carrier flow would invoke
        send_to_shipper / book / charge on validation, and no verified
        non-booking path is proven (a rate-only carrier, or an already-present
        carrier_tracking_ref)."""
        carrier = picking.carrier_id
        if not carrier:
            return False
        integration_level = getattr(carrier, 'integration_level', CARRIER_BOOKING_LEVEL)
        if integration_level != CARRIER_BOOKING_LEVEL:
            return False
        # rate_and_ship auto-books only when no tracking ref is set yet.
        return not picking.carrier_tracking_ref

    @api.model
    def _validate_picking_local(self, picking):
        # Local Odoo write only; forces the backorder policy explicitly, never
        # the interactive 'ask' wizard.
        picking = picking.with_context(
            cancel_backorder=False, skip_backorder=True,
        )
        picking._action_done()

    @api.model
    def _open_review(self, evidence, reason, detail=None):
        vals = {'reconciled_state': 'review', 'review_reason': reason}
        if detail:
            vals['review_detail'] = detail
        evidence.sudo().write(vals)

    @api.model
    def _resolve_sale_line(self, order_binding, line_item_gid):
        if not line_item_gid:
            return self.env['sale.order.line']
        return self.env['sale.order.line'].search([
            ('order_id', '=', order_binding.sale_order_id.id),
            ('shopify_line_item_gid', '=', line_item_gid),
        ], limit=1)
