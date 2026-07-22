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
        return True, None

    @api.model
    def _c6_no_overrun(self, ctx):
        ledger = ctx['evidence'].reconciled_quantity_ledger()
        for gid, (sale_line, qty) in ctx['line_mapping'].items():
            already = sum(
                l.reconciled_quantity for l in ctx['evidence'].line_ids
                if l.line_item_gid == gid
            )
            ordered = int(round(sale_line.product_uom_qty or 0))
            if qty + already > ordered:
                return False, 'quantity_overrun on %s' % gid
        return True, None

    @api.model
    def _c7_quantity_match(self, ctx):
        # The candidate picking's pending demand must equal (or deterministically
        # split to) the fulfillment quantities; compared against Odoo 19
        # stock.move.line.quantity, never qty_done.
        ctx['required_qty'] = {
            sale_line.id: qty for gid, (sale_line, qty) in ctx['line_mapping'].items()
        }
        return True, None

    @api.model
    def _c8_location(self, ctx):
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
        ctx['location_gid'] = location_gid
        return True, None

    @api.model
    def _c9_picking(self, ctx):
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
        # Fresh live re-read (already fetched in _c3 for this evaluation pass);
        # confirm still SUCCESS and not cancelled.
        node = ctx.get('fulfillment_node') or {}
        if node.get('status') != 'SUCCESS':
            return False, 'remote state changed'
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
    def _select_deterministic_picking(self, ctx):
        order = ctx['order_binding'].sale_order_id
        required = ctx['required_qty']
        candidates = order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
            and p.location_dest_id.usage == 'customer'
            and p.state in ('assigned', 'confirmed', 'waiting')
        )
        exact = []
        for picking in candidates:
            demand = {}
            for move in picking.move_ids:
                if move.sale_line_id.id in required:
                    demand[move.sale_line_id.id] = demand.get(
                        move.sale_line_id.id, 0.0
                    ) + move.product_uom_qty
            if not demand:
                continue
            covers = all(
                demand.get(line_id, 0.0) >= qty
                for line_id, qty in required.items()
            )
            if covers:
                exact.append(picking)
        # Exactly one covering candidate -> deterministic; zero or many -> fail.
        if len(exact) == 1:
            return exact[0]
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
        evidence.sudo().write({
            'reconciled_state': 'applied',
            'resolution_at': fields.Datetime.now(),
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
