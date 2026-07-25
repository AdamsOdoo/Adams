import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

from .shopify_connector_fulfillment_reader import FulfillmentReadError

_logger = logging.getLogger(__name__)

# Carrier integration_level that auto-books on delivery validation (Q6).
CARRIER_BOOKING_LEVEL = 'rate_and_ship'

# Correction P0-2: the ONLY exception classes treated as an expected local
# applicability/business failure and converted into a review case. A raw
# database/framework/programming exception is deliberately excluded here --
# it must propagate after the atomic savepoint rolls back, never be silently
# reinterpreted as a normal validation outcome.
_EXPECTED_MODE2_APPLICATION_ERRORS = (UserError, ValidationError)


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
        # Correction P1-1: a preliminary, READ-ONLY cumulative-quantity check
        # ONLY. It acquires NO row lock -- the authoritative, locked re-check
        # runs immediately before the atomic local-application unit
        # (`_relock_and_recheck`), only after every Shopify read (conditions
        # 8/14) has already completed. A pass here is not a final decision;
        # it exists only to fail fast on an obvious overrun before the
        # (comparatively expensive) location resolution and second live read
        # that follow. Sums only OTHER, already-`applied` evidence records'
        # lines for this exact sale line, keyed by the order-level LineItem
        # GID -- this record's own lines are always empty at evaluation time.
        Line = self.env[
            'shopify.connector.fulfillment.inbound.evidence.line'
        ].sudo()
        for gid, (sale_line, qty) in ctx['line_mapping'].items():
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
        # Correction P0-1: the candidate picking's pending demand must equal
        # -- EXACTLY, never merely cover -- the fulfilled quantities per
        # evidenced sale line, UoM-converted and compared against Odoo 19
        # stock.move.line.quantity via non-done stock.move.product_uom_qty,
        # never qty_done. A same-line surplus is no longer safe: unless a
        # fully source-backed deterministic split/backorder implementation
        # is completed and tested, automatic Mode 2 application requires
        # exact per-line equality; any surplus or shortage fails closed here
        # as `quantity_mismatch`, before any local stock mutation. Condition
        # 9 is reserved for genuine deterministic-selection ambiguity among
        # candidates that already passed this exact-equality check.
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
        whose demand exactly matches the required lines with no sibling
        moves; this condition further narrows that same list to only the
        candidates whose own source location is the mapped Odoo location or
        one of its descendants, so condition 9's deterministic selection can
        never land on a picking from an incompatible warehouse. No valid
        mapping (core seam absent/returns False; no candidate is location-
        compatible) fails closed to `location_unmapped`, exactly as it
        always has."""
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
        # it (Correction P1-1: condition 6 no longer locks, so no earlier
        # condition can spill a lock across this or any other read). Any
        # change, absence, or incompleteness fails closed and never reaches
        # local validation.
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
    def _required_from_line_mapping(self, line_mapping):
        """Aggregate `{sale_line_id: required_qty}` plus a
        `{sale_line_id: sale_line}` lookup from a `line_mapping` dict
        (`{shopify_line_item_gid: (sale_line, qty)}`) -- the single source of
        truth both the evaluation-time filter and the apply-time locked
        re-check derive their required set from."""
        required, required_lines = {}, {}
        for gid, (sale_line, qty) in line_mapping.items():
            required[sale_line.id] = required.get(sale_line.id, 0) + qty
            required_lines[sale_line.id] = sale_line
        return required, required_lines

    @api.model
    def _move_qty_in_sale_uom(self, move, sale_line):
        """A move's pending quantity, converted into the evidenced sale
        line's own UoM (Odoo 19 `uom.uom._compute_quantity`) when the two
        differ -- a picking's `stock.move` can legitimately be recorded in a
        different (but convertible) UoM than the sale order line it
        fulfils."""
        qty = move.product_uom_qty or 0.0
        move_uom = getattr(move, 'product_uom', False)
        sale_uom = sale_line.product_uom_id if sale_line else False
        if move_uom and sale_uom and move_uom.id != sale_uom.id:
            qty = move_uom._compute_quantity(qty, sale_uom)
        return qty

    @api.model
    def _qty_equal(self, demand_qty, required_qty, sale_line):
        rounding = (
            sale_line.product_uom_id.rounding
            if sale_line and sale_line.product_uom_id else 0.01
        )
        return float_compare(
            demand_qty, required_qty, precision_rounding=rounding,
        ) == 0

    @api.model
    def _picking_pending_demand(self, picking, required, required_lines):
        """Aggregate `picking`'s pending (non-`done`) per-sale-line demand,
        each move converted into its evidenced sale line's own UoM. Returns
        `None` when the picking carries so much as one sibling, un-evidenced
        move (Theme B P0-B baseline) -- such a picking is never a candidate
        at all, whether at evaluation time or at the apply-time locked
        re-check."""
        demand = {}
        for move in picking.move_ids:
            if move.state == 'done':
                # Historical fact from an earlier, already-completed partial
                # pass on this same picking (a backorder-chain predecessor);
                # not part of this candidate's own pending-demand evaluation.
                continue
            sale_line_id = move.sale_line_id.id
            if sale_line_id not in required:
                return None
            sale_line = required_lines[sale_line_id]
            demand[sale_line_id] = demand.get(
                sale_line_id, 0.0
            ) + self._move_qty_in_sale_uom(move, sale_line)
        return demand

    @api.model
    def _demand_matches_exactly(self, demand, required, required_lines):
        if not demand:
            return False
        return all(
            self._qty_equal(demand.get(line_id, 0.0), qty, required_lines[line_id])
            for line_id, qty in required.items()
        )

    @api.model
    def _quantity_compatible_pickings(self, ctx):
        """Every open outgoing candidate picking whose pending per-line demand
        equals -- EXACTLY, per Correction P0-1 -- the required fulfillment
        quantities AND whose non-done moves are exclusively for sale lines
        this fulfillment evidences (Modes §4.1; Theme B P0-B baseline). A
        picking carrying so much as one sibling, un-evidenced move is never a
        candidate at all -- it is excluded here, never validated as a whole
        and never speculatively split; a same-line surplus or shortage is
        equally excluded here, never validated on the larger/smaller
        picking. The caller (condition 7/9) surfaces the existing
        `quantity_mismatch`/`picking_ambiguous` review reasons exactly as it
        already does, with no new vocabulary. Read-only, no other selection/
        ambiguity judgement — condition 7 uses this to decide
        `quantity_mismatch`; condition 9's `_select_deterministic_picking`
        uses the same list to decide `picking_ambiguous`."""
        order = ctx['order_binding'].sale_order_id
        required, required_lines = self._required_from_line_mapping(
            ctx['line_mapping'],
        )
        candidates = order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
            and p.location_dest_id.usage == 'customer'
            and p.state in ('assigned', 'confirmed', 'waiting')
        )
        compatible = []
        for picking in candidates:
            demand = self._picking_pending_demand(picking, required, required_lines)
            if demand is None:
                continue
            if self._demand_matches_exactly(demand, required, required_lines):
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
    # Apply-time locked re-check (Correction P1-1) + atomic application
    # (Correction P0-2): Q6 carrier fail-closed, then locked re-check, then
    # local validate -- all as one savepoint-protected unit.
    # ------------------------------------------------------------------

    @api.model
    def _lock_affected_sale_lines(self, line_mapping):
        """Acquire every affected sale-line row lock in deterministic
        ascending-ID order (`try_lock_for_update`, non-blocking `FOR UPDATE
        SKIP LOCKED`), sequentially and all-or-nothing: the moment one lock
        cannot be acquired, stop and return whatever was locked so far
        (short of the full required set) -- the caller treats anything less
        than the complete set as a total failure. Ascending-ID ordering
        avoids a lock-order deadlock between two concurrent multi-line
        applications. Called only AFTER every Shopify read has already
        completed, never before/during one."""
        sale_line_ids = sorted({
            sale_line.id for sale_line, qty in line_mapping.values()
        })
        sale_lines = self.env['sale.order.line'].browse(sale_line_ids)
        locked = self.env['sale.order.line']
        for sale_line in sale_lines:
            one_locked = sale_line.try_lock_for_update()
            if not one_locked:
                return locked
            locked |= one_locked
        return locked

    @api.model
    def _relock_and_recheck(self, evidence, plan):
        """Correction P1-1: immediately before the atomic local-application
        unit, acquire every affected sale-line lock (deterministic ascending
        order), then re-verify -- under that lock -- both the cross-
        fulfillment reconciled-quantity ledger (C6) and the exact current
        Odoo pending demand (C7) are still exactly what evaluation observed.
        Performs NO further Shopify or other network read. `ok=False` fails
        the whole application closed with zero local mutation, before the
        atomic savepoint ever opens."""
        line_mapping = plan.get('line_mapping') if isinstance(plan, dict) else None
        picking = plan.get('picking') if isinstance(plan, dict) else None
        if not line_mapping or not picking:
            return False, 'picking_ambiguous'
        required, required_lines = self._required_from_line_mapping(line_mapping)
        locked = self._lock_affected_sale_lines(line_mapping)
        if len(locked) != len(required):
            # A lock that cannot be acquired right now is itself an
            # inconclusive overrun check -- fail closed rather than proceed
            # on a possibly-stale read (mirrors the prior C6 contract, now
            # relocated here so it never spans a Shopify read).
            return False, 'quantity_overrun'
        Line = self.env[
            'shopify.connector.fulfillment.inbound.evidence.line'
        ].sudo()
        for gid, (sale_line, qty) in line_mapping.items():
            already = sum(Line.search([
                ('line_item_gid', '=', gid),
                ('evidence_id.store_id', '=', evidence.store_id.id),
                ('evidence_id', '!=', evidence.id),
                ('evidence_id.reconciled_state', '=', 'applied'),
            ]).mapped('reconciled_quantity'))
            ordered = int(round(sale_line.product_uom_qty or 0))
            if qty + already > ordered:
                return False, 'quantity_overrun'
        demand = self._picking_pending_demand(picking, required, required_lines)
        if not self._demand_matches_exactly(demand, required, required_lines):
            return False, 'quantity_mismatch'
        return True, None

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
        ok, reason = self._relock_and_recheck(evidence, plan)
        if not ok:
            self._open_review(evidence, reason)
            return
        line_mapping = plan.get('line_mapping') if isinstance(plan, dict) else None
        try:
            # Correction P0-2: binding creation, local picking validation,
            # quantity-ledger creation and the `applied` state transition are
            # one savepoint-protected atomic unit. The binding is created
            # BEFORE validating, inside this same savepoint, so the outbound
            # `stock.picking._action_done` trigger sees it already committed
            # in this still-open transaction and enqueues no redundant
            # `fulfillment_picking_admission` (`_enqueue_picking_admission`'s
            # own minimal technical-sudo existence check). Any failure below
            # rolls the ENTIRE unit back -- no binding, no ledger row, no
            # move/picking state change, and no `applied` evidence state
            # ever survives a failed application.
            with self.env.cr.savepoint():
                self._bind_external_fulfillment(evidence, picking)
                self._validate_picking_local(picking)
                self._record_reconciled_lines(evidence, line_mapping)
                evidence.sudo().write({
                    'reconciled_state': 'applied',
                    'resolution_at': fields.Datetime.now(),
                })
        except _EXPECTED_MODE2_APPLICATION_ERRORS:
            # Only an expected business/applicability failure is converted to
            # review, and only AFTER the savepoint has already rolled the
            # whole unit back -- the review write below runs in the clean
            # outer transaction, never inside the rolled-back savepoint.
            # Anything NOT in `_EXPECTED_MODE2_APPLICATION_ERRORS` (a raw
            # database/framework/programming error) propagates unchanged
            # after the same rollback -- never silently reinterpreted as a
            # normal applicability failure.
            _logger.exception(
                'Mode 2 local application failed for picking %s; the entire '
                'bind/validate/ledger unit was rolled back and routed to '
                'review.', picking.id,
            )
            self._open_review(evidence, 'reservation_invalid')
            return

    @api.model
    def _record_reconciled_lines(self, evidence, line_mapping):
        """Write the cross-fulfillment reconciled-quantity ledger rows
        `_c6_no_overrun`/`_relock_and_recheck` consult for future
        evaluations (Theme B). Runs inside `_apply_mode2`'s own savepoint."""
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
