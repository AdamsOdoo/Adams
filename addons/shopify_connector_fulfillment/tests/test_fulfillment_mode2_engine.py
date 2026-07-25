import uuid
from contextlib import ExitStack
from unittest.mock import Mock, patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_reader import (
    FulfillmentReadError,
)


class _FakeRecordset(list):
    """Minimal `.filtered()`-capable stand-in for an Odoo recordset, used to
    unit-test `_quantity_compatible_pickings` against plain Mock pickings
    without requiring real stock.move fixtures."""

    def filtered(self, predicate):
        return _FakeRecordset(x for x in self if predicate(x))

# Stable GIDs shared across the fixture and the stubbed reader nodes.
LINE_ITEM_GID = 'gid://shopify/LineItem/111'
FULFILLMENT_GID = 'gid://shopify/Fulfillment/1'
FO_GID = 'gid://shopify/FulfillmentOrder/1'
FO_LINE_GID = 'gid://shopify/FulfillmentOrderLineItem/1'
FL_GID = 'gid://shopify/FulfillmentLineItem/1'
ORDER_GID = 'gid://shopify/Order/900'
LOCATION_GID = 'gid://shopify/Location/1'


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestFulfillmentMode2Engine(TransactionCase):
    """The Mode 2 16-condition evaluator (Modes §4).

    The checklist is ordered; the first failing condition stops evaluation and
    returns that condition's named review_reason with ZERO Odoo stock change.
    Only a 16/16 pass authorises a local write. These tests drive the engine
    end-to-end through
    ``self.env['shopify.connector.fulfillment.service']._evaluate_mode2(evidence)``
    with the two decision-critical reads (``_read_order_fulfillments`` and
    ``_read_fulfillment_orders``) and the deterministic picking selector stubbed
    to controlled recipe shapes, so exactly one condition can be broken per
    negative test. Q6 (carrier fail-closed) is exercised against a REAL
    ``delivery.carrier`` + picking through ``_carrier_would_book`` and
    ``_apply_mode2``.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['shopify.connector.fulfillment.service']
        cls.Evidence = cls.env['shopify.connector.fulfillment.inbound.evidence']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'FUL Test',
            'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'fulfillment_domain_enabled': True,
        })
        # fulfillment_operating_mode is Administrator-grouped -> write via sudo.
        cls.settings.sudo().write({
            'fulfillment_operating_mode': 'mode2',
            'fulfillment_switch_in_progress': False,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'P1', 'type': 'consu', 'is_storable': True,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'C'})
        cls.sale = cls.env['sale.order'].create({'partner_id': cls.partner.id})
        cls.sale_line = cls.env['sale.order.line'].create({
            'order_id': cls.sale.id,
            'product_id': cls.product.id,
            'product_uom_qty': 2.0,
            'shopify_line_item_gid': LINE_ITEM_GID,
        })
        cls.order_binding = cls.env[
            'shopify.connector.order.binding'
        ].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': ORDER_GID,
            'sale_order_id': cls.sale.id,
            'status': 'active',
        })
        # Core location cache entry the location resolver (_c8) needs.
        cls.env['shopify.connector.location'].sudo().create({
            'store_id': cls.store.id,
            'shopify_location_gid': LOCATION_GID,
            'name': 'L',
            'shopify_location_active': True,
        })
        cls.stock_loc = cls.env.ref('stock.stock_location_stock')
        cls.customer_loc = cls.env.ref('stock.stock_location_customers')
        cls.pt_out = cls.env['stock.picking.type'].search(
            [('code', '=', 'outgoing')], limit=1,
        )
        # A real picking, only ever referenced by id (the deterministic
        # selector is stubbed in these engine tests); it never gets validated.
        cls.picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.pt_out.id,
            'location_id': cls.stock_loc.id,
            'location_dest_id': cls.customer_loc.id,
            'sale_id': cls.sale.id,
        })
        # Q6 carrier fixtures: a real rate_and_ship delivery.carrier + a real
        # outgoing picking carrying it.
        cls.delivery_product = cls.env['product.product'].create({
            'name': 'Delivery', 'type': 'service',
        })
        cls.carrier = cls.env['delivery.carrier'].create({
            'name': 'Test Carrier',
            'delivery_type': 'fixed',
            'product_id': cls.delivery_product.id,
            'integration_level': 'rate_and_ship',
        })
        cls.carrier_picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.pt_out.id,
            'location_id': cls.stock_loc.id,
            'location_dest_id': cls.customer_loc.id,
            'sale_id': cls.sale.id,
            'carrier_id': cls.carrier.id,
        })

    # ------------------------------------------------------------------
    # Fixture builders
    # ------------------------------------------------------------------

    def _evidence(self, **overrides):
        vals = {
            'store_id': self.store.id,
            'shopify_fulfillment_gid': FULFILLMENT_GID,
            'shopify_order_gid': ORDER_GID,
            'order_binding_id': self.order_binding.id,
            'origin_class': 'external_merchant',
            'origin_confirmed': True,
            'fulfillment_status_raw': 'SUCCESS',
            'fulfillment_status_normalized': 'Success',
            'fulfillment_status_is_success': True,
            'reconciled_state': 'observed',
        }
        vals.update(overrides)
        return self.Evidence.sudo().create(vals)

    def _fulfillment_node(self, status='SUCCESS', lines=None,
                          fulfillment_gid=FULFILLMENT_GID):
        """A Fulfillment node as returned by _read_order_fulfillments (used by
        _c3 / _c14). ``fulfillment_gid`` defaults to the shared constant but
        must be passed explicitly (or derived from the evidence under test)
        whenever the evidence carries a non-default
        ``shopify_fulfillment_gid``, so the positive-path node's ``id``
        always matches what Condition 3/14 look for."""
        if lines is None:
            lines = [{
                'id': FL_GID, 'quantity': 2,
                'lineItem': {'id': LINE_ITEM_GID},
            }]
        return {
            'id': fulfillment_gid,
            'status': status,
            'displayStatus': 'FULFILLED',
            'trackingInfo': [{'number': 'TN1', 'url': '', 'company': 'UPS'}],
            'fulfillmentLineItems': {'nodes': lines},
        }

    def _fo_node(self, location_gid=LOCATION_GID, status='OPEN'):
        """A FulfillmentOrder node as returned by _read_fulfillment_orders
        (used by _c8 location resolution)."""
        return {
            'id': FO_GID,
            'status': status,
            'requestStatus': 'SUBMITTED',
            'assignedLocation': {'location': {'id': location_gid, 'name': 'L'}},
            'supportedActions': [{'action': 'CREATE_FULFILLMENT'}],
            'line_items': [{
                'id': FO_LINE_GID, 'remainingQuantity': 2,
                'lineItem': {'id': LINE_ITEM_GID},
            }],
        }

    def _mock_picking(self, state='assigned', move_ids=None,
                      carrier_id=False, carrier_tracking_ref='',
                      location_id=None):
        """A stand-in for the deterministically-selected picking exposing only
        the exact attributes the post-selection conditions read
        (_c10 state, _c11 move_ids, _c13 id, _c8/_c14 location_id)."""
        picking = Mock()
        picking.id = self.picking.id
        picking.state = state
        picking.move_ids = [] if move_ids is None else move_ids
        picking.carrier_id = carrier_id
        picking.carrier_tracking_ref = carrier_tracking_ref
        # Theme I (F-4): defaults to the real fixture warehouse location, so
        # the shared _evaluate() helper's default mapped-location patch
        # (also self.stock_loc) keeps every pre-existing test's 16/16 happy
        # path passing condition 8 unchanged.
        picking.location_id = self.stock_loc if location_id is None else location_id
        return picking

    def _mock_picking_with_matching_move(self, qty=2.0, sale_line=None, **overrides):
        """Like `_mock_picking`, but carries one real-shaped move whose
        aggregated pending demand exactly matches `qty` for `sale_line` --
        for tests that must pass the exact-quantity relock/recheck gate
        (Corrections P0-1/P1-1) on the way into `_apply_mode2`. The move's
        `product_id` is the real (untracked, `tracking == 'none'`) fixture
        product and `move_line_ids` a concrete empty recordset stand-in, so
        a full-pass evaluation genuinely reaching Condition 11
        (`_c11_lot_serial`) skips its tracked-product branch instead of
        operating on unconstrained `Mock` attributes."""
        picking = self._mock_picking(**overrides)
        line = sale_line or self.sale_line
        move = Mock()
        move.state = 'confirmed'
        move.sale_line_id.id = line.id
        move.product_uom_qty = qty
        move.product_uom = line.product_uom_id
        move.product_id = line.product_id
        move.move_line_ids = _FakeRecordset()
        picking.move_ids = [move]
        return picking

    _UNSET = object()

    def _evaluate(self, evidence, fulfillments=_UNSET, fos=_UNSET,
                  picking=_UNSET, quantity_compatible=_UNSET,
                  fulfillments_side_effect=None, fos_side_effect=None,
                  mapped_location=_UNSET, mapped_location_side_effect=None):
        """Run _evaluate_mode2 with the two reads + the deterministic selector
        stubbed. Defaults produce a fully-valid 16/16 pass; a test overrides one
        input to break exactly one condition.

        ``quantity_compatible``, when given, patches
        ``_quantity_compatible_pickings`` directly (condition 7's real coverage
        check) and leaves ``_select_deterministic_picking`` UNPATCHED so its
        real ambiguity logic runs against that list — this is how the
        quantity_mismatch-vs-picking_ambiguous distinction is exercised without
        real stock.move fixtures. ``fulfillments_side_effect``/
        ``fos_side_effect``, when given, let a test return a genuinely
        different value on condition 14's second call than condition 3/8's
        first call (proving the second read is separate, not reused).
        ``mapped_location``/``mapped_location_side_effect`` patch the F-4 core
        seam (``shopify.connector.location._resolve_odoo_location``) directly
        — default is ``self.stock_loc``, matching every mock picking's own
        default ``location_id``, so the happy path passes condition 8/14
        unchanged; pass ``False`` for an unmapped/disabled seam, or a
        different real location for a mismatched-subtree case.
        """
        Service = self.Service
        LocationModel = type(self.env['shopify.connector.location'])
        with ExitStack() as stack:
            if fulfillments_side_effect is not None:
                stack.enter_context(patch.object(
                    type(Service), '_read_order_fulfillments',
                    side_effect=fulfillments_side_effect,
                ))
            else:
                if fulfillments is self._UNSET:
                    # Default positive-path node: its GID must always match
                    # the evidence under test, not the shared module-level
                    # default, so a test that overrides
                    # evidence.shopify_fulfillment_gid still passes
                    # Condition 3/14's exact-GID match.
                    fulfillments = [self._fulfillment_node(
                        fulfillment_gid=evidence.shopify_fulfillment_gid,
                    )]
                stack.enter_context(patch.object(
                    type(Service), '_read_order_fulfillments',
                    return_value=fulfillments,
                ))
            if fos_side_effect is not None:
                stack.enter_context(patch.object(
                    type(Service), '_read_fulfillment_orders',
                    side_effect=fos_side_effect,
                ))
            else:
                if fos is self._UNSET:
                    fos = [self._fo_node()]
                stack.enter_context(patch.object(
                    type(Service), '_read_fulfillment_orders',
                    return_value=fos,
                ))
            if mapped_location_side_effect is not None:
                stack.enter_context(patch.object(
                    LocationModel, '_resolve_odoo_location',
                    side_effect=mapped_location_side_effect,
                ))
            else:
                if mapped_location is self._UNSET:
                    mapped_location = self.stock_loc
                stack.enter_context(patch.object(
                    LocationModel, '_resolve_odoo_location',
                    return_value=mapped_location,
                ))
            if quantity_compatible is not self._UNSET:
                stack.enter_context(patch.object(
                    type(Service), '_quantity_compatible_pickings',
                    return_value=quantity_compatible,
                ))
            else:
                if picking is self._UNSET:
                    picking = self._mock_picking()
                # Condition 7 (the P2-1 real coverage check) runs before the
                # deterministic selector; the fixture picking carries no real
                # stock.move, so supply a non-empty quantity-compatible set here
                # so evaluation can reach the condition actually under test. The
                # explicit ``quantity_compatible=`` path above is left untouched
                # so the quantity_mismatch-vs-picking_ambiguous split is still
                # exercised against the real selector.
                stack.enter_context(patch.object(
                    type(Service), '_quantity_compatible_pickings',
                    return_value=[picking],
                ))
                stack.enter_context(patch.object(
                    type(Service), '_select_deterministic_picking',
                    return_value=picking,
                ))
            return Service._evaluate_mode2(evidence)

    def _assert_stopped(self, result, evidence, reason, unchanged_state='observed'):
        """A failing condition: not passed, the matching named reason, and ZERO
        stock change (evidence untouched by _evaluate_mode2; nothing applied)."""
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], reason)
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, unchanged_state)
        # No picking was validated: the real picking is never touched here.
        self.picking.invalidate_recordset()
        self.assertNotEqual(self.picking.state, 'done')

    # ------------------------------------------------------------------
    # Full 16/16 pass
    # ------------------------------------------------------------------

    def test_all_sixteen_conditions_pass(self):
        evidence = self._evidence()
        result = self._evaluate(evidence)
        self.assertTrue(result['passed'])
        self.assertIsNone(result['reason'])
        # A 16/16 pass carries the deterministically-selected picking in the plan.
        self.assertIn('picking', result['plan'])
        self.assertTrue(result['plan']['picking'])
        # _evaluate_mode2 itself writes nothing (application is a separate step).
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'observed')

    # ------------------------------------------------------------------
    # One negative per condition family (ordered; first failure wins)
    # ------------------------------------------------------------------

    def test_c1_order_binding_missing(self):
        evidence = self._evidence(order_binding_id=False)
        result = self._evaluate(evidence)
        self._assert_stopped(result, evidence, 'order_binding_missing')

    def test_c2_fulfillment_state_not_success(self):
        # The condition-2 automation gate: the stored A4 FulfillmentStatus is
        # not SUCCESS -> stop, never auto-apply.
        evidence = self._evidence(fulfillment_status_is_success=False)
        result = self._evaluate(evidence)
        self._assert_stopped(result, evidence, 'fulfillment_state_not_success')

    def test_c3_fulfillment_order_unresolved(self):
        # The fresh live re-read finds no Fulfillment matching the evidence GID.
        evidence = self._evidence()
        result = self._evaluate(evidence, fulfillments=[])
        self._assert_stopped(result, evidence, 'fulfillment_order_unresolved')

    def test_c4_product_binding_missing(self):
        # The fulfilled line resolves to no Odoo sale line (unknown LineItem GID).
        evidence = self._evidence()
        node = self._fulfillment_node(lines=[{
            'id': FL_GID, 'quantity': 2,
            'lineItem': {'id': 'gid://shopify/LineItem/UNKNOWN'},
        }])
        result = self._evaluate(evidence, fulfillments=[node])
        self._assert_stopped(result, evidence, 'product_binding_missing')

    def test_c5_line_mapping_ambiguous(self):
        # Two fulfilled lines collapse onto the same Odoo line -> ambiguous.
        evidence = self._evidence()
        node = self._fulfillment_node(lines=[
            {'id': FL_GID, 'quantity': 1, 'lineItem': {'id': LINE_ITEM_GID}},
            {'id': 'gid://shopify/FulfillmentLineItem/2', 'quantity': 1,
             'lineItem': {'id': LINE_ITEM_GID}},
        ])
        result = self._evaluate(evidence, fulfillments=[node])
        self._assert_stopped(result, evidence, 'line_mapping_ambiguous')

    def test_c6_quantity_overrun_maps_to_quantity_overrun_not_over_fulfillment(self):
        # Fulfilled qty (3) exceeds the ordered qty (2). The named reason is
        # 'quantity_overrun' -- the removed 'over_fulfillment' vocabulary is
        # deliberately NOT used.
        evidence = self._evidence()
        node = self._fulfillment_node(lines=[{
            'id': FL_GID, 'quantity': 3, 'lineItem': {'id': LINE_ITEM_GID},
        }])
        result = self._evaluate(evidence, fulfillments=[node])
        self._assert_stopped(result, evidence, 'quantity_overrun')
        self.assertNotEqual(result['reason'], 'over_fulfillment')

    # -- P2 correction: condition 7 (quantity_mismatch) --------------------
    # Corrected contract: condition 7 now actually determines quantity/
    # coverage compatibility (it was previously a permanent no-op that always
    # passed). A quantity incompatibility across every open candidate is
    # reported HERE as 'quantity_mismatch' and must never fall through to be
    # reported only as condition 9's 'picking_ambiguous'.

    def _covering_picking(self, qty=2.0, sale_line=None):
        picking = Mock()
        picking.picking_type_code = 'outgoing'
        picking.location_dest_id.usage = 'customer'
        picking.state = 'assigned'
        line = sale_line or self.sale_line
        move = Mock()
        move.state = 'confirmed'
        move.sale_line_id.id = line.id
        move.product_uom_qty = qty
        move.product_uom = line.product_uom_id
        picking.move_ids = [move]
        return picking

    def test_c7_exact_quantity_coverage_records_required_and_passes(self):
        covering = self._covering_picking(qty=2.0)
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset([covering])
        ctx = {
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
            'order_binding': order_binding, 'plan': {},
        }
        ok, _detail = self.Service._c7_quantity_match(ctx)
        self.assertTrue(ok)
        self.assertEqual(ctx['required_qty'], {self.sale_line.id: 2})
        self.assertEqual(ctx['quantity_compatible_pickings'], [covering])

    def test_c7_surplus_demand_now_fails_closed_quantity_mismatch(self):
        # Correction P0-1: automatic Mode 2 application now requires EXACT
        # per-line equality. A same-line surplus (Odoo pending demand 10 vs
        # Shopify-confirmed quantity 3, per the control-room's own concrete
        # failure scenario) must fail closed as quantity_mismatch, never
        # silently validate the larger picking. Over-provisioning is no
        # longer "safe and still covers" -- it is now excluded.
        surplus = self._covering_picking(qty=10.0)
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset([surplus])
        ctx = {
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 3)},
            'order_binding': order_binding, 'plan': {},
        }
        ok, _detail = self.Service._c7_quantity_match(ctx)
        self.assertFalse(ok)
        self.assertEqual(ctx['quantity_compatible_pickings'], [])

    def test_surplus_end_to_end_zero_stock_change(self):
        # Real picking, real move: the surplus picking is proven completely
        # untouched (never validated) when its pending demand exceeds the
        # exact Shopify-confirmed quantity.
        picking = self._real_picking_with_moves([(self.sale_line, 10.0)])
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset([picking])
        ctx = {
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 3)},
            'order_binding': order_binding, 'plan': {},
        }
        compatible = self.Service._quantity_compatible_pickings(ctx)
        self.assertEqual(compatible, [])
        self.assertNotEqual(picking.state, 'done')

    def test_two_moves_same_line_aggregate_to_exact_quantity_eligible(self):
        # Two separate Odoo moves for the SAME evidenced sale line, summing
        # exactly to the Shopify-confirmed quantity, are eligible. The moves
        # are put through the genuine Odoo confirmation transition (never a
        # direct `state` write) -- a picking whose moves are all still
        # 'draft' is correctly excluded by `_quantity_compatible_pickings`'s
        # own candidate filter, so a draft fixture can never reach this
        # assertion honestly.
        picking = self._real_picking_with_moves([
            (self.sale_line, 1.0), (self.sale_line, 1.0),
        ])
        picking.move_ids._action_confirm()
        for move in picking.move_ids:
            move.invalidate_recordset()
            self.assertNotIn(move.state, ('draft', 'done'))
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset([picking])
        ctx = {
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
            'order_binding': order_binding, 'plan': {},
        }
        compatible = self.Service._quantity_compatible_pickings(ctx)
        self.assertIn(picking, compatible)

    def test_two_moves_same_line_aggregate_above_required_fails_closed(self):
        # Two moves for the same line summing ABOVE the Shopify quantity:
        # review, zero stock change -- aggregation surplus is exactly as
        # unsafe as single-move surplus.
        picking = self._real_picking_with_moves([
            (self.sale_line, 2.0), (self.sale_line, 2.0),
        ])
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset([picking])
        ctx = {
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
            'order_binding': order_binding, 'plan': {},
        }
        compatible = self.Service._quantity_compatible_pickings(ctx)
        self.assertEqual(compatible, [])
        self.assertNotEqual(picking.state, 'done')

    def test_backorder_chain_candidate_exact_remaining_demand(self):
        # A genuine partial-completion / backorder chain. The ORIGINAL outgoing
        # picking is created for the full ordered demand (2.0); a real 1.0
        # portion is reserved, picked and validated through the genuine Odoo
        # stock workflow, and Odoo itself spins off a SEPARATE backorder
        # picking carrying the live remaining 1.0 move. Candidate discovery
        # must exclude the completed original (genuinely 'done') and select
        # exactly the live backorder, whose pending demand is exactly 1.0 in
        # the sale line's own UoM.
        #
        # This shape is mandated by the genuine Odoo 19 stock source: a move
        # created on a 'done' picking is forced to state='done'
        # (stock.move.create), and _action_confirm() skips any non-'draft'
        # move, so a live pending move can only ever exist on a distinct
        # backorder picking -- never as a second move hand-added to the
        # completed original. No workflow state is ever written directly.
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_loc.id,
            'quantity': 2.0,
        })
        original = self._real_picking_with_moves([(self.sale_line, 2.0)])
        original_move = original.move_ids
        original.action_confirm()
        original.action_assign()
        self.assertEqual(original_move.state, 'assigned')
        # Record a genuine 1.0 picked portion (never a direct `state`/quantity
        # write on the move) and validate that ONE picking through the real
        # workflow; the 1.0 shortfall makes Odoo create a backorder for the
        # remaining 1.0.
        for line in original_move.move_line_ids:
            line.quantity = 1.0
        original_move.picked = True
        original._action_done()

        original.invalidate_recordset()
        original_move.invalidate_recordset()
        self.assertEqual(original_move.state, 'done')
        self.assertEqual(original.state, 'done')

        # Odoo created exactly one genuine backorder: a DIFFERENT record linked
        # back to the completed original through the real backorder
        # relationship, still open and eligible for candidate discovery.
        backorder = original.backorder_ids
        self.assertEqual(len(backorder), 1)
        self.assertNotEqual(backorder, original)
        self.assertEqual(backorder.backorder_id, original)
        self.assertIn(backorder.state, ('assigned', 'confirmed', 'waiting'))

        # The live remaining move on the backorder: genuinely pending (not
        # draft/done/cancel), exactly 1.0 in the sale line's own UoM, and still
        # bound to the evidenced sale line.
        remaining = backorder.move_ids
        self.assertEqual(len(remaining), 1)
        self.assertNotIn(remaining.state, ('draft', 'done', 'cancel'))
        self.assertEqual(remaining.sale_line_id, self.sale_line)
        self.assertEqual(
            self.Service._move_qty_in_sale_uom(remaining, self.sale_line), 1.0,
        )

        # Candidate discovery is exposed to BOTH the completed original and the
        # live backorder; only the backorder is selected.
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset(
            [original, backorder],
        )
        ctx = {
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 1)},
            'order_binding': order_binding, 'plan': {},
        }
        required, required_lines = self.Service._required_from_line_mapping(
            ctx['line_mapping'],
        )
        # The completed original contributes zero pending demand (all done).
        self.assertEqual(
            self.Service._picking_pending_demand(
                original, required, required_lines,
            ),
            {},
        )
        # The live backorder's pending demand is exactly the remaining 1.0.
        self.assertEqual(
            self.Service._picking_pending_demand(
                backorder, required, required_lines,
            ),
            {self.sale_line.id: 1.0},
        )

        compatible = self.Service._quantity_compatible_pickings(ctx)
        self.assertEqual(compatible, [backorder])
        self.assertNotIn(original, compatible)

    def test_move_qty_uom_conversion_to_sale_line_uom(self):
        # Direct unit test of the UoM-conversion helper: a move recorded in
        # Units converts correctly into the sale line's own Dozens.
        dozen = self.env.ref('uom.product_uom_dozen')
        unit = self.env.ref('uom.product_uom_unit')
        sale_line = Mock()
        sale_line.product_uom_id = dozen
        move = Mock()
        move.product_uom_qty = 24.0
        move.product_uom = unit
        qty = self.Service._move_qty_in_sale_uom(move, sale_line)
        self.assertAlmostEqual(qty, 2.0)

    def test_c7_uom_converted_exact_equality_end_to_end(self):
        # A REAL sale line ordered in Dozens, fulfilled by a REAL stock.move
        # recorded in Units: the aggregation must convert the move's UoM
        # into the sale line's own UoM before the exact-equality check, so
        # 24 units == 2 dozen is correctly recognised as an exact match.
        dozen = self.env.ref('uom.product_uom_dozen')
        unit = self.env.ref('uom.product_uom_unit')
        sale_line = self.env['sale.order.line'].create({
            'order_id': self.sale.id, 'product_id': self.product.id,
            'product_uom_qty': 2.0, 'product_uom_id': dozen.id,
            'shopify_line_item_gid': 'gid://shopify/LineItem/UOM-DOZEN',
        })
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.pt_out.id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'sale_id': self.sale.id,
        })
        move = self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom_qty': 24.0, 'product_uom': unit.id,
            'picking_id': picking.id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'sale_line_id': sale_line.id,
        })
        # Genuine Odoo confirmation transition (never a direct `state`
        # write) -- the picking's own candidate-filter state is computed
        # from its moves, so a still-draft move would make this picking
        # ineligible before the UoM-conversion/exact-equality check under
        # test is even reached.
        move._action_confirm()
        move.invalidate_recordset()
        self.assertNotIn(move.state, ('draft', 'done'))
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset([picking])
        ctx = {
            'line_mapping': {'gid://shopify/LineItem/UOM-DOZEN': (sale_line, 2)},
            'order_binding': order_binding, 'plan': {},
        }
        compatible = self.Service._quantity_compatible_pickings(ctx)
        self.assertIn(picking, compatible)

    def test_c7_insufficient_quantity_no_compatible_candidate(self):
        short = self._covering_picking(qty=1.0)  # required is 2
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset([short])
        ctx = {
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
            'order_binding': order_binding, 'plan': {},
        }
        ok, detail = self.Service._c7_quantity_match(ctx)
        self.assertFalse(ok)
        self.assertEqual(ctx['quantity_compatible_pickings'], [])

    def test_c7_multiple_candidates_only_one_quantity_compatible(self):
        short = self._covering_picking(qty=1.0)
        covering = self._covering_picking(qty=2.0)
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset(
            [short, covering])
        ctx = {
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
            'order_binding': order_binding, 'plan': {},
        }
        ok, _detail = self.Service._c7_quantity_match(ctx)
        self.assertTrue(ok)
        self.assertEqual(ctx['quantity_compatible_pickings'], [covering])

    def test_c7_quantity_mismatch_no_compatible_picking_end_to_end(self):
        # No open candidate covers the required quantities: the first-fail
        # reason is quantity_mismatch, never picking_ambiguous.
        evidence = self._evidence()
        result = self._evaluate(evidence, quantity_compatible=[])
        self._assert_stopped(result, evidence, 'quantity_mismatch')

    def test_c9_single_quantity_compatible_candidate_is_selected(self):
        # Exactly one quantity-compatible candidate: condition 7 passes and
        # condition 9 deterministically selects it (real, unpatched
        # _select_deterministic_picking) -- no ambiguity.
        evidence = self._evidence()
        picking = self._mock_picking()
        result = self._evaluate(evidence, quantity_compatible=[picking])
        self.assertTrue(result['passed'])
        self.assertEqual(result['plan']['picking'], picking)

    def test_c9_picking_ambiguous_multiple_quantity_compatible_candidates(self):
        # Two+ candidates both quantity-compatible: genuine deterministic-
        # selection ambiguity -> picking_ambiguous (coverage was never the
        # problem here, so quantity_mismatch must NOT fire).
        evidence = self._evidence()
        result = self._evaluate(
            evidence,
            quantity_compatible=[self._mock_picking(), self._mock_picking()],
        )
        self._assert_stopped(result, evidence, 'picking_ambiguous')
        self.assertNotEqual(result['reason'], 'quantity_mismatch')

    def test_c8_location_unmapped(self):
        # The FO's assigned Shopify location is absent from the core cache.
        evidence = self._evidence()
        fo = self._fo_node(location_gid='gid://shopify/Location/UNMAPPED')
        result = self._evaluate(evidence, fos=[fo])
        self._assert_stopped(result, evidence, 'location_unmapped')

    def test_c9_picking_ambiguous(self):
        # Low-level unit check of condition 9 IN ISOLATION (direct call, not
        # through the full engine): the deterministic selector itself
        # reports no resolvable picking, independent of conditions 7/8's own
        # candidate-filtering logic. See
        # test_c9_picking_ambiguous_multiple_quantity_compatible_candidates
        # above for the real end-to-end genuine-ambiguity path, and
        # test_c7_quantity_mismatch_no_compatible_picking_end_to_end for the
        # corrected quantity_mismatch routing this must never fall back to.
        ctx = {'quantity_compatible_pickings': None, 'plan': {}}
        with patch.object(
            type(self.Service), '_select_deterministic_picking',
            return_value=False,
        ):
            ok, _detail = self.Service._c9_picking(ctx)
        self.assertFalse(ok)
        self.assertNotIn('picking', ctx['plan'])

    def test_c10_reservation_invalid(self):
        # The selected picking is not fully reserved (state != assigned).
        evidence = self._evidence()
        picking = self._mock_picking(state='confirmed')
        result = self._evaluate(evidence, picking=picking)
        self._assert_stopped(result, evidence, 'reservation_invalid')

    def test_c11_lot_serial_ambiguous(self):
        # A tracked move lacks a complete lot/serial reservation.
        evidence = self._evidence()
        move = Mock()
        move.product_id.tracking = 'lot'
        move.move_line_ids.filtered.return_value = []  # no lot lines
        move.product_uom_qty = 2
        picking = self._mock_picking(move_ids=[move])
        result = self._evaluate(evidence, picking=picking)
        self._assert_stopped(result, evidence, 'lot_serial_ambiguous')

    def test_c12_already_reconciled(self):
        # The duplicate-application backstop: an evidence already 'applied' for
        # this exact Fulfillment GID (the UNIQUE(store, gid) row) stops re-apply.
        evidence = self._evidence(reconciled_state='applied')
        result = self._evaluate(evidence)
        self._assert_stopped(
            result, evidence, 'already_reconciled', unchanged_state='applied',
        )

    def test_c13_binding_conflict(self):
        # Another fulfillment binding already owns the selected picking under a
        # different Fulfillment GID.
        evidence = self._evidence()
        self.env['shopify.connector.fulfillment.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/OTHER',
            'picking_id': self.picking.id,
            'order_binding_id': self.order_binding.id,
        })
        result = self._evaluate(evidence)
        self._assert_stopped(result, evidence, 'binding_conflict')

    def test_c14_remote_state_changed(self):
        # The stored evidence says SUCCESS, but the fresh live re-read shows the
        # Fulfillment is no longer SUCCESS (e.g. CANCELLED) -> fail closed.
        evidence = self._evidence()
        node = self._fulfillment_node(status='CANCELLED')
        result = self._evaluate(evidence, fulfillments=[node])
        self._assert_stopped(result, evidence, 'remote_state_changed')

    # -- P2 correction: condition 14 performs a SEPARATELY fresh live read --
    # (never reuses condition 3's read). Each test below uses
    # ``fulfillments_side_effect``/``fos_side_effect`` -- a distinct value per
    # call -- so that condition 3/8's first call and condition 14's second
    # call are provably independent reads, not one cached observation.

    def test_c14_second_read_is_executed_separately(self):
        # _read_order_fulfillments must be called twice during one evaluation
        # pass: once for condition 3, once (genuinely re-invoked) for
        # condition 14. This test calls `_evaluate_mode2` directly rather
        # than through the `_evaluate()` wrapper, so it must supply every
        # seam that wrapper normally patches by default: the fulfillment
        # node's GID matching the evidence GID, the sanctioned location
        # seam, and a single consistent picking instance used by both the
        # quantity-compatible candidate list and the deterministic
        # selector, so Condition 8/9/14 are genuinely exercised instead of
        # failing closed on an unmapped location.
        evidence = self._evidence()
        node = self._fulfillment_node(
            fulfillment_gid=evidence.shopify_fulfillment_gid,
        )
        picking = self._mock_picking()
        Service = self.Service
        LocationModel = type(self.env['shopify.connector.location'])
        with patch.object(type(Service), '_read_order_fulfillments',
                          return_value=[node]) as mocked, \
                patch.object(type(Service), '_read_fulfillment_orders',
                             return_value=[self._fo_node()]), \
                patch.object(LocationModel, '_resolve_odoo_location',
                             return_value=self.stock_loc), \
                patch.object(type(Service), '_quantity_compatible_pickings',
                             return_value=[picking]), \
                patch.object(type(Service), '_select_deterministic_picking',
                             return_value=picking):
            result = Service._evaluate_mode2(evidence)
        self.assertTrue(result['passed'])
        self.assertEqual(result['plan']['picking'], picking)
        self.assertEqual(mocked.call_count, 2)

    def test_c14_first_read_cannot_be_reused(self):
        # If condition 14 wrongly reused condition 3's cached node, a SUCCESS
        # first read followed by a CANCELLED second read would incorrectly
        # pass all 16 conditions. It must not: the second, genuinely separate
        # read is what condition 14 evaluates.
        evidence = self._evidence()
        first = self._fulfillment_node(status='SUCCESS')
        second = self._fulfillment_node(status='CANCELLED')
        result = self._evaluate(
            evidence, fulfillments_side_effect=[[first], [second]],
        )
        self._assert_stopped(result, evidence, 'remote_state_changed')

    def test_c14_unchanged_second_read_permits_continuation(self):
        # Two independently-constructed but equal reads (not the same cached
        # object) -> condition 14 passes and evaluation continues to 16/16.
        evidence = self._evidence()
        result = self._evaluate(
            evidence,
            fulfillments_side_effect=[
                [self._fulfillment_node()], [self._fulfillment_node()],
            ],
        )
        self.assertTrue(result['passed'])

    def test_c14_quantity_changed_between_reads(self):
        # The first read shows the expected quantity (2); the second,
        # genuinely separate read shows a different quantity -> fail closed,
        # never silently proceeding to local validation on stale quantities.
        evidence = self._evidence()
        first = self._fulfillment_node()
        second = self._fulfillment_node(lines=[{
            'id': FL_GID, 'quantity': 1, 'lineItem': {'id': LINE_ITEM_GID},
        }])
        result = self._evaluate(
            evidence, fulfillments_side_effect=[[first], [second]],
        )
        self._assert_stopped(result, evidence, 'remote_state_changed')

    def test_c14_state_changed_between_reads(self):
        evidence = self._evidence()
        first = self._fulfillment_node(status='SUCCESS')
        second = self._fulfillment_node(status='CANCELLED')
        result = self._evaluate(
            evidence, fulfillments_side_effect=[[first], [second]],
        )
        self._assert_stopped(result, evidence, 'remote_state_changed')

    def test_c14_location_changed_between_reads(self):
        # A second Shopify location, also present in the core cache, so the
        # second read resolves cleanly but to a DIFFERENT location than
        # condition 8 already established -> fail closed.
        other_location_gid = 'gid://shopify/Location/2'
        self.env['shopify.connector.location'].sudo().create({
            'store_id': self.store.id,
            'shopify_location_gid': other_location_gid,
            'name': 'L2', 'shopify_location_active': True,
        })
        evidence = self._evidence()
        first_fo = self._fo_node(location_gid=LOCATION_GID)
        second_fo = self._fo_node(location_gid=other_location_gid)
        result = self._evaluate(
            evidence, fos_side_effect=[[first_fo], [second_fo]],
        )
        self._assert_stopped(result, evidence, 'remote_state_changed')

    def test_c14_target_fulfillment_disappeared_on_second_read(self):
        evidence = self._evidence()
        first = self._fulfillment_node()
        result = self._evaluate(
            evidence, fulfillments_side_effect=[[first], []],
        )
        self._assert_stopped(result, evidence, 'remote_state_changed')

    def test_c14_second_read_incomplete_fails_closed(self):
        # The second read raises (pagination cap / malformed page): an
        # incomplete read is never proof of anything and must fail closed,
        # exactly like any other decision-critical read (§11.4).
        evidence = self._evidence()
        first = self._fulfillment_node()
        result = self._evaluate(
            evidence,
            fulfillments_side_effect=[
                [first],
                FulfillmentReadError(
                    'data_shape_schema_mismatch', 'incomplete second read'),
            ],
        )
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'remote_state_changed')

    def test_c14_repeated_cursor_on_second_read_fails_closed(self):
        evidence = self._evidence()
        first = self._fulfillment_node()
        result = self._evaluate(
            evidence,
            fulfillments_side_effect=[
                [first],
                FulfillmentReadError(
                    'data_shape_schema_mismatch',
                    'A paginated read repeated or dropped its cursor.'),
            ],
        )
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'], 'remote_state_changed')

    def test_c14_transport_failure_never_reaches_local_validation(self):
        # A raw transport failure on the second read propagates (it is not
        # silently swallowed as a pass) and local validation is proven
        # un-called.
        evidence = self._evidence()
        first = self._fulfillment_node()
        job = self._mode2_job(evidence)
        Service = self.Service
        LocationModel = type(self.env['shopify.connector.location'])
        with patch.object(type(Service), '_read_order_fulfillments',
                          side_effect=[[first], ConnectionError('down')]), \
                patch.object(type(Service), '_read_fulfillment_orders',
                             return_value=[self._fo_node()]), \
                patch.object(LocationModel, '_resolve_odoo_location',
                             return_value=self.stock_loc), \
                patch.object(type(Service), '_quantity_compatible_pickings',
                             return_value=[self._mock_picking()]), \
                patch.object(type(Service), '_select_deterministic_picking',
                             return_value=self._mock_picking()), \
                patch.object(type(Service), '_validate_picking_local',
                             side_effect=AssertionError(
                                 'a failed second read must never validate')):
            with self.assertRaises(ConnectionError):
                Service._handle_fulfillment_mode2_evaluation(job)
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'observed')

    def test_c15_origin_unconfirmed(self):
        # An external origin that is not positively confirmed is never automated.
        evidence = self._evidence(origin_confirmed=False)
        result = self._evaluate(evidence)
        self._assert_stopped(result, evidence, 'origin_unconfirmed')

    def test_c16_mode_not_enabled(self):
        # A switch back to Mode 1 (here: a switch in progress suspends Mode 2)
        # disables auto-application.
        self.settings.sudo().write({'fulfillment_switch_in_progress': True})
        evidence = self._evidence()
        result = self._evaluate(evidence)
        self._assert_stopped(result, evidence, 'mode_not_enabled')

    # ------------------------------------------------------------------
    # Handler-level: no partial automation on a failing condition
    # ------------------------------------------------------------------

    def _mode2_job(self, evidence):
        return self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'fulfillment_mode2_evaluation',
            'state': 'queued',
            'res_model': 'shopify.connector.fulfillment.inbound.evidence',
            'res_id': evidence.id,
            'payload_hash': 'mode2:%d' % evidence.id,
        })

    def test_handler_failing_condition_opens_review_and_never_validates(self):
        # End-to-end handler: a failing condition opens a review case carrying
        # the named reason, applies ZERO stock change, and never validates a
        # picking (the local validate is proven un-called).
        evidence = self._evidence(fulfillment_status_is_success=False)
        job = self._mode2_job(evidence)
        Service = self.Service
        with patch.object(type(Service), '_read_order_fulfillments',
                          return_value=[self._fulfillment_node()]), \
                patch.object(type(Service), '_read_fulfillment_orders',
                             return_value=[self._fo_node()]), \
                patch.object(type(Service), '_select_deterministic_picking',
                             return_value=self._mock_picking()), \
                patch.object(type(Service), '_validate_picking_local',
                             side_effect=AssertionError(
                                 'a failing condition must never validate')):
            Service._handle_fulfillment_mode2_evaluation(job)
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'review')
        self.assertEqual(evidence.review_reason, 'fulfillment_state_not_success')

    def test_handler_full_pass_applies_locally(self):
        # The happy path: a 16/16 pass applies (evidence -> 'applied') after the
        # carrier fail-closed check clears (no carrier here). The local validate
        # is stubbed to a no-op so no real stock engine runs in the unit test.
        # Theme B: the cross-fulfillment ledger row is genuinely written.
        evidence = self._evidence()
        job = self._mode2_job(evidence)
        Service = self.Service
        LocationModel = type(self.env['shopify.connector.location'])
        picking = self._mock_picking_with_matching_move(qty=2.0, carrier_id=False)
        with patch.object(type(Service), '_read_order_fulfillments',
                          return_value=[self._fulfillment_node()]), \
                patch.object(type(Service), '_read_fulfillment_orders',
                             return_value=[self._fo_node()]), \
                patch.object(LocationModel, '_resolve_odoo_location',
                             return_value=self.stock_loc), \
                patch.object(type(Service), '_quantity_compatible_pickings',
                             return_value=[picking]), \
                patch.object(type(Service), '_select_deterministic_picking',
                             return_value=picking), \
                patch.object(type(Service), '_validate_picking_local',
                             return_value=None):
            Service._handle_fulfillment_mode2_evaluation(job)
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'applied')
        Line = self.env['shopify.connector.fulfillment.inbound.evidence.line']
        ledger_rows = Line.search([('evidence_id', '=', evidence.id)])
        self.assertEqual(len(ledger_rows), 1)
        self.assertEqual(ledger_rows.line_item_gid, LINE_ITEM_GID)
        self.assertEqual(ledger_rows.sale_line_id, self.sale_line)
        self.assertEqual(ledger_rows.reconciled_quantity, 2)
        # Correction P0-2: exactly one binding survives the atomic unit.
        Binding = self.env['shopify.connector.fulfillment.binding']
        binding = Binding.search([
            ('store_id', '=', self.store.id), ('picking_id', '=', picking.id),
        ])
        self.assertEqual(len(binding), 1)

    # ------------------------------------------------------------------
    # Q6 carrier fail-closed (real delivery.carrier + picking)
    # ------------------------------------------------------------------

    def test_carrier_would_book_true_for_rate_and_ship_without_ref(self):
        # Default rate_and_ship carrier, no tracking ref yet -> validation would
        # auto-book/charge.
        self.assertTrue(self.Service._carrier_would_book(self.carrier_picking))

    def test_carrier_would_book_false_for_rate_only_carrier(self):
        self.carrier.sudo().write({'integration_level': 'rate'})
        self.carrier_picking.invalidate_recordset()
        self.assertFalse(self.Service._carrier_would_book(self.carrier_picking))

    def test_carrier_would_book_false_when_tracking_ref_present(self):
        # A verified non-booking path: a tracking ref is already set.
        self.carrier_picking.sudo().write({'carrier_tracking_ref': 'TN1'})
        self.assertFalse(self.Service._carrier_would_book(self.carrier_picking))

    def test_carrier_would_book_false_without_carrier(self):
        self.assertFalse(self.Service._carrier_would_book(self.picking))

    def test_apply_mode2_carrier_would_book_opens_review_never_validates(self):
        # Q6: with a would-book carrier, _apply_mode2 opens a review carrying
        # 'carrier_would_book' and never reaches local validation.
        evidence = self._evidence()
        Service = self.Service
        with patch.object(type(Service), '_validate_picking_local',
                          side_effect=AssertionError(
                              'must fail closed before any validation/booking')):
            Service._apply_mode2(evidence, {'picking': self.carrier_picking})
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'review')
        self.assertEqual(evidence.review_reason, 'carrier_would_book')
        # Not applied: no stock change.
        self.assertNotEqual(evidence.reconciled_state, 'applied')

    # ------------------------------------------------------------------
    # Theme B — P0-B: partial fulfillment must not validate sibling moves
    # ------------------------------------------------------------------

    def _real_picking_with_moves(self, line_specs):
        """A real outbound picking with one stock.move per (sale_line, qty)."""
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.pt_out.id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'sale_id': self.sale.id,
        })
        for sale_line, qty in line_specs:
            self.env['stock.move'].create({
                'product_id': sale_line.product_id.id,
                'product_uom_qty': qty,
                'product_uom': sale_line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': self.stock_loc.id,
                'location_dest_id': self.customer_loc.id,
                'sale_line_id': sale_line.id,
            })
        return picking

    def test_sibling_unevidenced_move_excludes_picking(self):
        # Theme B P0-B baseline: a candidate picking carrying a move for a
        # sale line this fulfillment does NOT evidence must never be
        # quantity-compatible -- it would otherwise be whole-picking-
        # validated, silently stock-deducting the sibling, un-evidenced line.
        sibling_sale_line = self.env['sale.order.line'].create({
            'order_id': self.sale.id, 'product_id': self.product.id,
            'product_uom_qty': 1.0,
            'shopify_line_item_gid': 'gid://shopify/LineItem/SIBLING-UNIT',
        })
        picking = Mock()
        picking.picking_type_code = 'outgoing'
        picking.location_dest_id.usage = 'customer'
        picking.state = 'assigned'
        move_a = Mock()
        move_a.state = 'confirmed'
        move_a.sale_line_id.id = self.sale_line.id
        move_a.product_uom_qty = 2.0
        move_a.product_uom = self.sale_line.product_uom_id
        move_sibling = Mock()
        move_sibling.state = 'confirmed'
        move_sibling.sale_line_id.id = sibling_sale_line.id
        move_sibling.product_uom_qty = 1.0
        move_sibling.product_uom = sibling_sale_line.product_uom_id
        picking.move_ids = [move_a, move_sibling]
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset([picking])
        ctx = {
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
            'order_binding': order_binding, 'plan': {},
        }
        compatible = self.Service._quantity_compatible_pickings(ctx)
        self.assertEqual(compatible, [])

    def test_sibling_move_end_to_end_zero_stock_change(self):
        # Real picking, real moves: the sibling line's move is proven
        # completely untouched (never validated) when only the OTHER line
        # is evidenced by this fulfillment.
        sibling_sale_line = self.env['sale.order.line'].create({
            'order_id': self.sale.id, 'product_id': self.product.id,
            'product_uom_qty': 1.0,
            'shopify_line_item_gid': 'gid://shopify/LineItem/SIBLING-E2E',
        })
        picking = self._real_picking_with_moves([
            (self.sale_line, 2.0), (sibling_sale_line, 1.0),
        ])
        picking.move_ids._action_confirm()
        sibling_move = picking.move_ids.filtered(
            lambda m: m.sale_line_id == sibling_sale_line)
        sibling_state_before = sibling_move.state
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset([picking])
        ctx = {
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
            'order_binding': order_binding, 'plan': {},
        }
        compatible = self.Service._quantity_compatible_pickings(ctx)
        self.assertNotIn(picking, compatible)
        sibling_move.invalidate_recordset()
        self.assertEqual(sibling_move.state, sibling_state_before)
        self.assertNotEqual(sibling_move.state, 'done')
        self.assertNotEqual(picking.state, 'done')

    def test_no_sibling_move_still_compatible(self):
        # Control: an otherwise-identical picking with NO sibling move (only
        # the evidenced line) remains a genuine candidate -- the sibling
        # check must not over-exclude.
        picking = self._real_picking_with_moves([(self.sale_line, 2.0)])
        picking.move_ids._action_confirm()
        order_binding = Mock()
        order_binding.sale_order_id.picking_ids = _FakeRecordset([picking])
        ctx = {
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
            'order_binding': order_binding, 'plan': {},
        }
        compatible = self.Service._quantity_compatible_pickings(ctx)
        self.assertIn(picking, compatible)

    def test_c6_no_overrun_sums_other_applied_evidence_not_own(self):
        # Theme B: the ledger sums OTHER applied evidence records' lines for
        # this exact sale line -- never the current (always-empty at
        # evaluation time) evidence's own lines.
        other_evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/C6-OTHER-1',
            reconciled_state='applied',
        )
        self.env[
            'shopify.connector.fulfillment.inbound.evidence.line'
        ].sudo().create({
            'evidence_id': other_evidence.id,
            'line_item_gid': LINE_ITEM_GID,
            'sale_line_id': self.sale_line.id,
            'quantity': 1, 'reconciled_quantity': 1,
        })
        current_evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/C6-CURRENT-1',
        )
        ctx = {
            'evidence': current_evidence, 'store': self.store,
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 1)},
        }
        ok, _detail = self.Service._c6_no_overrun(ctx)
        self.assertTrue(ok)  # 1 (other, applied) + 1 (this) == ordered (2)

    def test_c6_no_overrun_rejects_cumulative_over_ordered(self):
        # Repeated partial fulfillments cumulatively exceeding the ordered
        # quantity are rejected BEFORE any local stock mutation (this is a
        # pure evaluation-time check; _apply_mode2/_validate_picking_local
        # are never reached when this returns False).
        other_evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/C6-OTHER-2',
            reconciled_state='applied',
        )
        self.env[
            'shopify.connector.fulfillment.inbound.evidence.line'
        ].sudo().create({
            'evidence_id': other_evidence.id,
            'line_item_gid': LINE_ITEM_GID,
            'sale_line_id': self.sale_line.id,
            'quantity': 2, 'reconciled_quantity': 2,
        })
        current_evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/C6-CURRENT-2',
        )
        ctx = {
            'evidence': current_evidence, 'store': self.store,
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 1)},
        }
        ok, detail = self.Service._c6_no_overrun(ctx)
        self.assertFalse(ok)
        self.assertIn('quantity_overrun', detail)

    def test_c6_no_overrun_ignores_non_applied_evidence(self):
        # An observed/review (not-yet-applied) evidence record's lines must
        # never count toward the overrun ledger.
        other_evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/C6-OTHER-3',
            reconciled_state='observed',
        )
        self.env[
            'shopify.connector.fulfillment.inbound.evidence.line'
        ].sudo().create({
            'evidence_id': other_evidence.id,
            'line_item_gid': LINE_ITEM_GID,
            'sale_line_id': self.sale_line.id,
            'quantity': 2, 'reconciled_quantity': 2,
        })
        current_evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/C6-CURRENT-3',
        )
        ctx = {
            'evidence': current_evidence, 'store': self.store,
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
        }
        ok, _detail = self.Service._c6_no_overrun(ctx)
        self.assertTrue(ok)

    # -- Correction P0-2: atomic Mode-2 application ------------------------

    def test_apply_mode2_expected_validation_failure_rolls_back_atomically(self):
        # An EXPECTED business/applicability failure (UserError) during
        # local validation must roll back the ENTIRE bind/validate/ledger
        # unit atomically via savepoint: no binding, no ledger row, and the
        # evidence reverts to a review-safe state.
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/ROLLBACK-1',
        )
        picking = self._mock_picking_with_matching_move(qty=2.0)
        plan = {
            'picking': picking,
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
        }
        with patch.object(
            type(self.Service), '_validate_picking_local',
            side_effect=UserError('simulated expected validation failure'),
        ):
            self.Service._apply_mode2(evidence, plan)
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'review')
        self.assertEqual(evidence.review_reason, 'reservation_invalid')
        Line = self.env['shopify.connector.fulfillment.inbound.evidence.line']
        self.assertFalse(Line.search([('evidence_id', '=', evidence.id)]))
        Binding = self.env['shopify.connector.fulfillment.binding']
        self.assertFalse(Binding.search([
            ('store_id', '=', self.store.id), ('picking_id', '=', picking.id),
        ]))

    def test_apply_mode2_unexpected_exception_propagates_after_rollback(self):
        # An UNEXPECTED exception (not a recognised business/applicability
        # error) must propagate after the savepoint rolls back -- never be
        # silently reinterpreted as a normal applicability failure, and
        # never leave a binding behind.
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/UNEXPECTED-1',
        )
        picking = self._mock_picking_with_matching_move(qty=2.0)
        plan = {
            'picking': picking,
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
        }
        with patch.object(
            type(self.Service), '_validate_picking_local',
            side_effect=RuntimeError('simulated unexpected failure'),
        ):
            with self.assertRaises(RuntimeError):
                self.Service._apply_mode2(evidence, plan)
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'observed')
        self.assertFalse(evidence.review_reason)
        Binding = self.env['shopify.connector.fulfillment.binding']
        self.assertFalse(Binding.search([
            ('store_id', '=', self.store.id), ('picking_id', '=', picking.id),
        ]))

    def test_apply_mode2_failure_after_validation_before_ledger_rolls_back(self):
        # Local validation SUCCEEDS, but a later failure inside the same
        # atomic unit (ledger creation) still rolls back the EARLIER binding
        # creation too -- proving true atomicity of the whole unit, not just
        # the validation step.
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/AFTER-VALIDATE',
        )
        picking = self._mock_picking_with_matching_move(qty=2.0)
        plan = {
            'picking': picking,
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
        }
        with patch.object(type(self.Service), '_validate_picking_local',
                           return_value=None), \
                patch.object(type(self.Service), '_record_reconciled_lines',
                             side_effect=UserError('simulated ledger failure')):
            self.Service._apply_mode2(evidence, plan)
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'review')
        self.assertEqual(evidence.review_reason, 'reservation_invalid')
        Binding = self.env['shopify.connector.fulfillment.binding']
        self.assertFalse(Binding.search([
            ('store_id', '=', self.store.id), ('picking_id', '=', picking.id),
        ]))

    def test_retry_after_rolled_back_failure_can_succeed(self):
        # After a failed+rolled-back attempt, retrying the same evidence
        # must be able to succeed cleanly -- nothing left over from the
        # rolled-back attempt spuriously blocks the retry.
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/RETRY-SAFE',
        )
        picking = self._mock_picking_with_matching_move(qty=2.0)
        plan = {
            'picking': picking,
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
        }
        with patch.object(
            type(self.Service), '_validate_picking_local',
            side_effect=UserError('first attempt fails'),
        ):
            self.Service._apply_mode2(evidence, plan)
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'review')
        evidence.sudo().write({
            'reconciled_state': 'observed', 'review_reason': False,
        })
        with patch.object(
            type(self.Service), '_validate_picking_local', return_value=None,
        ):
            self.Service._apply_mode2(evidence, plan)
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'applied')
        Binding = self.env['shopify.connector.fulfillment.binding']
        binding = Binding.search([
            ('store_id', '=', self.store.id), ('picking_id', '=', picking.id),
        ])
        self.assertEqual(len(binding), 1)

    # -- Correction P1-1: no lock across Shopify reads, locked re-check ----

    def test_lock_affected_sale_lines_acquires_in_ascending_id_order(self):
        line_a = self.sale_line
        line_b = self.env['sale.order.line'].create({
            'order_id': self.sale.id, 'product_id': self.product.id,
            'product_uom_qty': 1.0,
            'shopify_line_item_gid': 'gid://shopify/LineItem/ORDER-B',
        })
        # Intentionally inserted out of ID order.
        line_mapping = {'gid-b': (line_b, 1), 'gid-a': (line_a, 2)}
        ordered_ids = sorted([line_a.id, line_b.id])
        call_order = []
        SaleLine = type(self.env['sale.order.line'])

        def _fake_lock(rec):
            call_order.append(rec.id)
            return rec

        with patch.object(
            SaleLine, 'try_lock_for_update', autospec=True, side_effect=_fake_lock,
        ):
            locked = self.Service._lock_affected_sale_lines(line_mapping)
        self.assertEqual(call_order, ordered_ids)
        self.assertEqual(sorted(locked.ids), ordered_ids)

    def test_relock_recheck_rereads_ledger_fresh_not_reused_from_c6(self):
        # The locked re-check must genuinely re-read the ledger, not reuse
        # any value cached from condition 6's earlier (now-stale) pass.
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/RELOCK-LEDGER',
        )
        ctx = {
            'evidence': evidence, 'store': self.store,
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
        }
        # C6's preliminary check passes (nothing applied yet).
        ok, _detail = self.Service._c6_no_overrun(ctx)
        self.assertTrue(ok)
        # Another evaluation "wins the race" and applies in between.
        other_evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/RELOCK-OTHER',
            reconciled_state='applied',
        )
        self.env[
            'shopify.connector.fulfillment.inbound.evidence.line'
        ].sudo().create({
            'evidence_id': other_evidence.id, 'line_item_gid': LINE_ITEM_GID,
            'sale_line_id': self.sale_line.id,
            'quantity': 2, 'reconciled_quantity': 2,
        })
        plan = {
            'picking': self._covering_picking(qty=2.0),
            'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)},
        }
        ok, reason = self.Service._relock_and_recheck(evidence, plan)
        self.assertFalse(ok)
        self.assertEqual(reason, 'quantity_overrun')

    # ------------------------------------------------------------------
    # Theme I — F-4 permanent location cross-check
    # ------------------------------------------------------------------

    def test_c8_mapped_exact_picking_source_passes(self):
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/F4-EXACT',
        )
        picking = self._mock_picking(location_id=self.stock_loc)
        result = self._evaluate(
            evidence, quantity_compatible=[picking],
            mapped_location=self.stock_loc,
        )
        # GID-coherence regression (Correction A): the evidence carries a
        # custom fulfillment GID; the default positive-path node built by
        # _evaluate() must carry that exact same GID so Condition 3 passes
        # and evaluation genuinely reaches this test's own intended
        # condition (8) rather than stopping early at
        # 'fulfillment_order_unresolved'.
        self.assertEqual(
            evidence.shopify_fulfillment_gid,
            'gid://shopify/Fulfillment/F4-EXACT',
        )
        self.assertTrue(result['passed'])
        self.assertNotEqual(result['reason'], 'fulfillment_order_unresolved')

    def test_c8_mapped_parent_with_descendant_picking_source_passes(self):
        child_loc = self.env['stock.location'].create({
            'name': 'F4 Child', 'usage': 'internal',
            'location_id': self.stock_loc.id,
        })
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/F4-DESC',
        )
        picking = self._mock_picking(location_id=child_loc)
        result = self._evaluate(
            evidence, quantity_compatible=[picking],
            mapped_location=self.stock_loc,
        )
        self.assertTrue(result['passed'])

    def test_c8_picking_source_outside_mapped_subtree_fails_closed(self):
        other_loc = self.env['stock.location'].create({
            'name': 'F4 Unrelated', 'usage': 'internal',
            'location_id': self.stock_loc.location_id.id,
        })
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/F4-OUTSIDE',
        )
        picking = self._mock_picking(location_id=other_loc)
        result = self._evaluate(
            evidence, quantity_compatible=[picking],
            mapped_location=self.stock_loc,
        )
        self._assert_stopped(result, evidence, 'location_unmapped')

    def test_c8_missing_mapping_fails_closed(self):
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/F4-MISSING',
        )
        result = self._evaluate(evidence, mapped_location=False)
        self._assert_stopped(result, evidence, 'location_unmapped')

    def test_c8_no_seam_available_fails_closed(self):
        # No inventory addon/override available -> the core base seam
        # (`shopify.connector.location._resolve_odoo_location`'s own
        # unconditional `return False`) fails closed exactly like a known
        # mapping absence -- the fulfillment layer cannot and must not
        # distinguish the two causes; both yield `location_unmapped`.
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/F4-NOSEAM',
        )
        result = self._evaluate(evidence, mapped_location=False)
        self._assert_stopped(result, evidence, 'location_unmapped')

    def test_c14_mapping_changed_between_c8_and_c14_fails_closed(self):
        other_loc = self.env['stock.location'].create({
            'name': 'F4 Changed Mapping', 'usage': 'internal',
            'location_id': self.stock_loc.location_id.id,
        })
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/F4-CHANGED',
        )
        # C8's read resolves to self.stock_loc; C14's genuinely separate
        # second read resolves the SAME Shopify location GID to a DIFFERENT
        # Odoo location -- the mapping changed between the two reads.
        result = self._evaluate(
            evidence,
            mapped_location_side_effect=[self.stock_loc, other_loc],
        )
        self._assert_stopped(result, evidence, 'remote_state_changed')

    def test_c14_mapping_unchanged_permits_continuation(self):
        evidence = self._evidence(
            shopify_fulfillment_gid='gid://shopify/Fulfillment/F4-UNCHANGED',
        )
        result = self._evaluate(
            evidence,
            mapped_location_side_effect=[self.stock_loc, self.stock_loc],
        )
        self.assertTrue(result['passed'])
