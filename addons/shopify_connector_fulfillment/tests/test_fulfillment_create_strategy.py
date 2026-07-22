import uuid
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_create_strategy import (  # noqa: E501
    CREATE_FULFILLMENT_ACTION,
    FO_ELIGIBLE_STATUSES,
    FULFILLMENT_CREATE_DOCUMENT,
    FulfillmentPreC2FailClosedError,
)


class TestFulfillmentCreateStrategy(TransactionCase):
    """Layer 2 `fulfillment_create` strategy callbacks tested directly, without
    the C1/C2/NET/C3 wrapper.

    Covers callback 5 (`_classify_direct_fulfillment_create`) code_required=False
    positive-id classification, the `_build_tracking_info` request builder, the
    no-@idempotent contract, and the pre-C2 fail-closed FulfillmentOrder gates in
    callback 3 (`_prepare_preconditions_fulfillment_create`)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['shopify.connector.fulfillment.service']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'FUL Test',
            'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id, 'fulfillment_domain_enabled': True,
        })

    # ------------------------------------------------------------------
    # Fixtures / builders
    # ------------------------------------------------------------------

    def _eligible_fo(self, status=FO_ELIGIBLE_STATUSES[0],
                     actions=(CREATE_FULFILLMENT_ACTION,)):
        """A FulfillmentOrder node in the exact reader-returned shape, i.e. with
        line items already flattened onto the `line_items` key."""
        return {
            'id': 'gid://shopify/FulfillmentOrder/1',
            'status': status,
            'requestStatus': 'UNSUBMITTED',
            'assignedLocation': {'location': {
                'id': 'gid://shopify/Location/1', 'name': 'L',
            }},
            'supportedActions': [{'action': a} for a in actions],
            'line_items': [{
                'id': 'gid://shopify/FulfillmentOrderLineItem/1',
                'remainingQuantity': 2,
                'lineItem': {'id': 'gid://shopify/LineItem/111'},
            }],
        }

    def _local_snapshot(self, picking_id=0, **overrides):
        snap = {
            'job_id': 1,
            'store_id': self.store.id,
            'picking_id': picking_id,
            'order_binding_id': False,
            'order_gid': 'gid://shopify/Order/900',
            'target_fo_gid': 'gid://shopify/FulfillmentOrder/1',
            'notify_customer': False,
            'tracking_numbers': [],
            'tracking_company': '',
            'tracking_urls': [],
            'expected_connection_generation': self.store.connection_generation,
            'expected_store_identity': self.store.shop_domain,
        }
        snap.update(overrides)
        return snap

    def _picking_with_move(self):
        """Build a customer-bound outgoing picking with one done move line whose
        Shopify line-item GID matches the eligible FO line, plus the core
        location-cache entry the location resolver needs. Used only by the tests
        that exercise the full `_prepare_preconditions_fulfillment_create` path."""
        self.env['shopify.connector.location'].sudo().search([
            ('store_id', '=', self.store.id),
            ('shopify_location_gid', '=', 'gid://shopify/Location/1'),
        ]) or self.env['shopify.connector.location'].sudo().create({
            'store_id': self.store.id,
            'shopify_location_gid': 'gid://shopify/Location/1',
            'name': 'L', 'shopify_location_active': True,
        })
        product = self.env['product.product'].create({
            'name': 'P1', 'type': 'consu', 'is_storable': True,
        })
        partner = self.env['res.partner'].create({'name': 'C'})
        sale = self.env['sale.order'].create({'partner_id': partner.id})
        sale_line = self.env['sale.order.line'].create({
            'order_id': sale.id, 'product_id': product.id,
            'product_uom_qty': 2.0,
            'shopify_line_item_gid': 'gid://shopify/LineItem/111',
        })
        customer_loc = self.env.ref('stock.stock_location_customers')
        stock_loc = self.env.ref('stock.stock_location_stock')
        pt_out = self.env['stock.picking.type'].search(
            [('code', '=', 'outgoing')], limit=1,
        )
        picking = self.env['stock.picking'].create({
            'picking_type_id': pt_out.id,
            'location_id': stock_loc.id,
            'location_dest_id': customer_loc.id,
            'sale_id': sale.id,
        })
        move = self.env['stock.move'].create({
            'name': 'm', 'product_id': product.id, 'product_uom_qty': 2.0,
            'picking_id': picking.id, 'location_id': stock_loc.id,
            'location_dest_id': customer_loc.id, 'sale_line_id': sale_line.id,
        })
        self.env['stock.move.line'].create({
            'move_id': move.id, 'product_id': product.id, 'quantity': 2.0,
            'picking_id': picking.id, 'location_id': stock_loc.id,
            'location_dest_id': customer_loc.id,
        })
        return picking

    # ------------------------------------------------------------------
    # Callback 5: _classify_direct_fulfillment_create (positive-id matrix)
    # ------------------------------------------------------------------

    def test_classify_uncertain_transport_reconciles(self):
        # A transport-level uncertain outcome is never trusted as applied.
        consequence = self.Service._classify_direct_fulfillment_create({
            'outcome': 'uncertain',
            'error_class': 'shopify_temporary_server_network',
            'evidence': {},
        })
        self.assertEqual(consequence['action'], 'reconcile')
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_classify_user_errors_is_clean_final_failure(self):
        # A synchronous structured userErrors rejection is a clean failure
        # (correctable by a NEW replacement job), never a post-C2 uncertain.
        consequence = self.Service._classify_direct_fulfillment_create({
            'outcome': None,
            'user_errors': [{'field': ['fulfillment'], 'message': 'bad'}],
            'fulfillment': None,
            'evidence': {},
        })
        self.assertEqual(consequence['action'], 'fail_final')
        self.assertEqual(consequence['observed_outcome'], 'failed_clean')
        self.assertEqual(
            consequence['error_class'], 'shopify_user_errors_validation',
        )

    def test_classify_empty_user_errors_with_id_succeeds(self):
        # Empty userErrors AND a real Fulfillment id is positive success evidence.
        consequence = self.Service._classify_direct_fulfillment_create({
            'outcome': None,
            'user_errors': [],
            'fulfillment': {
                'id': 'gid://shopify/Fulfillment/1', 'status': 'SUCCESS',
            },
            'evidence': {},
        })
        self.assertEqual(consequence['action'], 'succeed')
        self.assertEqual(consequence['observed_outcome'], 'succeeded')

    def test_classify_empty_user_errors_without_id_reconciles(self):
        # Empty userErrors but NO Fulfillment id is not positive success
        # evidence -> reconcile before trusting it as applied.
        consequence = self.Service._classify_direct_fulfillment_create({
            'outcome': None,
            'user_errors': [],
            'fulfillment': None,
            'evidence': {},
        })
        self.assertEqual(consequence['action'], 'reconcile')
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_classify_malformed_user_errors_reconciles(self):
        # A userErrors container that is not a list is a schema mismatch ->
        # reconcile, never a trusted success or a clean failure.
        consequence = self.Service._classify_direct_fulfillment_create({
            'outcome': None,
            'user_errors': {'not': 'a list'},
            'fulfillment': None,
            'evidence': {},
        })
        self.assertEqual(consequence['action'], 'reconcile')
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    # ------------------------------------------------------------------
    # _build_tracking_info request builder
    # ------------------------------------------------------------------

    def test_build_tracking_single_number(self):
        info = self.Service._build_tracking_info(
            self._local_snapshot(tracking_numbers=['TN1']),
        )
        self.assertEqual(info, {'number': 'TN1'})

    def test_build_tracking_multiple_numbers_split(self):
        info = self.Service._build_tracking_info(
            self._local_snapshot(tracking_numbers=['A', 'B']),
        )
        self.assertEqual(info, {'numbers': ['A', 'B']})

    def test_build_tracking_includes_company(self):
        info = self.Service._build_tracking_info(self._local_snapshot(
            tracking_numbers=['TN1'], tracking_company='UPS',
        ))
        self.assertEqual(info, {'company': 'UPS', 'number': 'TN1'})

    def test_build_tracking_urls_position_matched_equal_length(self):
        info = self.Service._build_tracking_info(self._local_snapshot(
            tracking_numbers=['A', 'B'], tracking_urls=['u1', 'u2'],
        ))
        self.assertEqual(info['numbers'], ['A', 'B'])
        self.assertEqual(info['urls'], ['u1', 'u2'])

    def test_build_tracking_single_number_single_url(self):
        info = self.Service._build_tracking_info(self._local_snapshot(
            tracking_numbers=['TN1'], tracking_urls=['u1'],
        ))
        self.assertEqual(info, {'number': 'TN1', 'url': 'u1'})

    def test_build_tracking_urls_omitted_when_unequal_length(self):
        # Never guess: urls that do not position-match the numbers are dropped.
        info = self.Service._build_tracking_info(self._local_snapshot(
            tracking_numbers=['A', 'B'], tracking_urls=['u1'],
        ))
        self.assertEqual(info['numbers'], ['A', 'B'])
        self.assertNotIn('urls', info)
        self.assertNotIn('url', info)

    def test_build_tracking_none_when_no_tracking(self):
        # D-014-6: a no-tracking fulfillment is still created (no trackingInfo).
        self.assertIsNone(
            self.Service._build_tracking_info(self._local_snapshot()),
        )

    # ------------------------------------------------------------------
    # No @idempotent contract + prepare request shape
    # ------------------------------------------------------------------

    def test_document_carries_no_idempotent_directive(self):
        # fulfillmentCreate is not on Shopify's @idempotent mutation list.
        self.assertNotIn('@idempotent', FULFILLMENT_CREATE_DOCUMENT)

    def test_prepare_returns_empty_idempotency_key_and_create_document(self):
        picking = self._picking_with_move()
        snapshot = self._local_snapshot(picking_id=picking.id)
        with patch.object(
            type(self.Service), '_read_fulfillment_orders',
            return_value=[self._eligible_fo()],
        ):
            request = self.Service._prepare_preconditions_fulfillment_create(
                snapshot, {},
            )
        # Fulfillment mutations have no @idempotent key; kept empty by design.
        self.assertTrue(request['shopify_idempotency_key'])  # non-empty (core gate); never in the operation
        self.assertIs(request['operation'], FULFILLMENT_CREATE_DOCUMENT)
        self.assertEqual(request['mutation_domain'], 'fulfillment_create')
        # The picking's shipped line reached the fulfillmentCreate input.
        self.assertTrue(
            request['variables']['fulfillment']['lineItemsByFulfillmentOrder'],
        )

    # ------------------------------------------------------------------
    # Pre-C2 fail-closed FulfillmentOrder gates
    # ------------------------------------------------------------------

    def test_missing_create_fulfillment_action_fails_closed(self):
        # An OPEN FO that does not support CREATE_FULFILLMENT is not eligible;
        # with no eligible FO the prepare fails closed before C2.
        snapshot = self._local_snapshot()
        fo = self._eligible_fo(actions=('MARK_AS_OPEN',))
        with patch.object(
            type(self.Service), '_read_fulfillment_orders', return_value=[fo],
        ):
            with self.assertRaises(FulfillmentPreC2FailClosedError):
                self.Service._prepare_preconditions_fulfillment_create(
                    snapshot, {},
                )

    def test_blocking_status_on_hold_fails_closed(self):
        # A blocking FulfillmentOrder status fails closed immediately; the
        # connector never places or releases holds.
        snapshot = self._local_snapshot()
        fo = self._eligible_fo(status='ON_HOLD')
        with patch.object(
            type(self.Service), '_read_fulfillment_orders', return_value=[fo],
        ):
            with self.assertRaises(FulfillmentPreC2FailClosedError):
                self.Service._prepare_preconditions_fulfillment_create(
                    snapshot, {},
                )
