import uuid
from unittest.mock import Mock, patch

from odoo.tests.common import TransactionCase

# Stable GIDs shared across the fixture and the stubbed reader nodes.
LINE_ITEM_GID = 'gid://shopify/LineItem/111'
FULFILLMENT_GID = 'gid://shopify/Fulfillment/1'
FO_GID = 'gid://shopify/FulfillmentOrder/1'
FO_LINE_GID = 'gid://shopify/FulfillmentOrderLineItem/1'
FL_GID = 'gid://shopify/FulfillmentLineItem/1'
ORDER_GID = 'gid://shopify/Order/900'
LOCATION_GID = 'gid://shopify/Location/1'


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

    def _fulfillment_node(self, status='SUCCESS', lines=None):
        """A Fulfillment node as returned by _read_order_fulfillments (used by
        _c3 / _c14)."""
        if lines is None:
            lines = [{
                'id': FL_GID, 'quantity': 2,
                'lineItem': {'id': LINE_ITEM_GID},
            }]
        return {
            'id': FULFILLMENT_GID,
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
                      carrier_id=False, carrier_tracking_ref=''):
        """A stand-in for the deterministically-selected picking exposing only
        the exact attributes the post-selection conditions read
        (_c10 state, _c11 move_ids, _c13 id)."""
        picking = Mock()
        picking.id = self.picking.id
        picking.state = state
        picking.move_ids = [] if move_ids is None else move_ids
        picking.carrier_id = carrier_id
        picking.carrier_tracking_ref = carrier_tracking_ref
        return picking

    _UNSET = object()

    def _evaluate(self, evidence, fulfillments=_UNSET, fos=_UNSET,
                  picking=_UNSET):
        """Run _evaluate_mode2 with the two reads + the deterministic selector
        stubbed. Defaults produce a fully-valid 16/16 pass; a test overrides one
        input to break exactly one condition."""
        if fulfillments is self._UNSET:
            fulfillments = [self._fulfillment_node()]
        if fos is self._UNSET:
            fos = [self._fo_node()]
        if picking is self._UNSET:
            picking = self._mock_picking()
        Service = self.Service
        with patch.object(type(Service), '_read_order_fulfillments',
                          return_value=fulfillments), \
                patch.object(type(Service), '_read_fulfillment_orders',
                             return_value=fos), \
                patch.object(type(Service), '_select_deterministic_picking',
                             return_value=picking):
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

    def test_c7_quantity_match_currently_always_passes_and_records_required(self):
        # _c7_quantity_match is a no-op gate in the current engine: it always
        # passes and records the required-quantity map for the selector. There
        # is therefore no input that makes it emit 'quantity_mismatch'; this
        # documents the helper's actual contract rather than inventing one.
        ctx = {'line_mapping': {LINE_ITEM_GID: (self.sale_line, 2)}, 'plan': {}}
        ok, _detail = self.Service._c7_quantity_match(ctx)
        self.assertTrue(ok)
        self.assertEqual(ctx['required_qty'], {self.sale_line.id: 2})

    def test_c8_location_unmapped(self):
        # The FO's assigned Shopify location is absent from the core cache.
        evidence = self._evidence()
        fo = self._fo_node(location_gid='gid://shopify/Location/UNMAPPED')
        result = self._evaluate(evidence, fos=[fo])
        self._assert_stopped(result, evidence, 'location_unmapped')

    def test_c9_picking_ambiguous(self):
        # The deterministic selector cannot resolve exactly one covering picking.
        evidence = self._evidence()
        result = self._evaluate(evidence, picking=False)
        self._assert_stopped(result, evidence, 'picking_ambiguous')

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
        evidence = self._evidence()
        job = self._mode2_job(evidence)
        Service = self.Service
        with patch.object(type(Service), '_read_order_fulfillments',
                          return_value=[self._fulfillment_node()]), \
                patch.object(type(Service), '_read_fulfillment_orders',
                             return_value=[self._fo_node()]), \
                patch.object(type(Service), '_select_deterministic_picking',
                             return_value=self._mock_picking(carrier_id=False)), \
                patch.object(type(Service), '_validate_picking_local',
                             return_value=None):
            Service._handle_fulfillment_mode2_evaluation(job)
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'applied')

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
