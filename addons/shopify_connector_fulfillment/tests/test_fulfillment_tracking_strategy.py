import uuid
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_tracking_strategy import (  # noqa: E501
    FULFILLMENT_TRACKING_UPDATE_DOCUMENT,
)
from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_create_strategy import (  # noqa: E501
    FulfillmentPreC2FailClosedError,
)


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
class TestFulfillmentTrackingStrategy(TransactionCase):
    """Layer 2 `fulfillment_tracking_update` strategy callbacks tested directly.

    Covers callback 5 (`_classify_direct_fulfillment_tracking_update`) with the
    same positive-id matrix as create, the in-place update document (never a
    second fulfillment), and callback 3
    (`_prepare_preconditions_fulfillment_tracking_update`) building the request
    from a fresh fulfillment read while failing closed on a cancelled/missing
    node and persisting the notifyCustomer decision."""

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

    def _local_snapshot(self, **overrides):
        snap = {
            'job_id': 1,
            'store_id': self.store.id,
            'binding_id': False,
            'fulfillment_gid': 'gid://shopify/Fulfillment/1',
            'notify_customer': True,
            'tracking_numbers': ['TN1'],
            'tracking_company': 'UPS',
            'tracking_urls': [],
            'expected_connection_generation': self.store.connection_generation,
            'expected_store_identity': self.store.shop_domain,
        }
        snap.update(overrides)
        return snap

    # ------------------------------------------------------------------
    # Callback 5: _classify_direct_fulfillment_tracking_update (same matrix)
    # ------------------------------------------------------------------

    def test_classify_uncertain_transport_reconciles(self):
        consequence = self.Service._classify_direct_fulfillment_tracking_update({
            'outcome': 'uncertain',
            'error_class': 'shopify_temporary_server_network',
            'evidence': {},
        })
        self.assertEqual(consequence['action'], 'reconcile')
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_classify_user_errors_is_clean_final_failure(self):
        consequence = self.Service._classify_direct_fulfillment_tracking_update({
            'outcome': None,
            'user_errors': [{'field': ['trackingInfoInput'], 'message': 'bad'}],
            'fulfillment': None,
            'evidence': {},
        })
        self.assertEqual(consequence['action'], 'fail_final')
        self.assertEqual(consequence['observed_outcome'], 'failed_clean')
        self.assertEqual(
            consequence['error_class'], 'shopify_user_errors_validation',
        )

    def test_classify_empty_user_errors_with_id_succeeds(self):
        consequence = self.Service._classify_direct_fulfillment_tracking_update({
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
        consequence = self.Service._classify_direct_fulfillment_tracking_update({
            'outcome': None,
            'user_errors': [],
            'fulfillment': None,
            'evidence': {},
        })
        self.assertEqual(consequence['action'], 'reconcile')
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_classify_malformed_user_errors_reconciles(self):
        consequence = self.Service._classify_direct_fulfillment_tracking_update({
            'outcome': None,
            'user_errors': 'oops',
            'fulfillment': None,
            'evidence': {},
        })
        self.assertEqual(consequence['action'], 'reconcile')
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    # ------------------------------------------------------------------
    # In-place update document (never a second fulfillment)
    # ------------------------------------------------------------------

    def test_document_updates_in_place_never_creates(self):
        self.assertIn(
            'fulfillmentTrackingInfoUpdate', FULFILLMENT_TRACKING_UPDATE_DOCUMENT,
        )
        self.assertNotIn(
            'fulfillmentCreate', FULFILLMENT_TRACKING_UPDATE_DOCUMENT,
        )

    def test_document_carries_no_idempotent_directive(self):
        self.assertNotIn('@idempotent', FULFILLMENT_TRACKING_UPDATE_DOCUMENT)

    # ------------------------------------------------------------------
    # Callback 3: _prepare_preconditions_fulfillment_tracking_update
    # ------------------------------------------------------------------

    def test_prepare_builds_request_with_persisted_notify_and_tracking(self):
        node = {
            'id': 'gid://shopify/Fulfillment/1', 'status': 'SUCCESS',
            'displayStatus': 'FULFILLED',
            'trackingInfo': [{'number': 'OLD', 'url': '', 'company': 'UPS'}],
        }
        snapshot = self._local_snapshot(notify_customer=True)
        with patch.object(
            type(self.Service), '_read_fulfillment', return_value=node,
        ):
            request = (
                self.Service
                ._prepare_preconditions_fulfillment_tracking_update(snapshot, {})
            )
        self.assertEqual(
            request['operation'], FULFILLMENT_TRACKING_UPDATE_DOCUMENT,
        )
        self.assertEqual(
            request['variables']['fulfillmentId'], 'gid://shopify/Fulfillment/1',
        )
        self.assertIn('trackingInfoInput', request['variables'])
        # notifyCustomer is the persisted enqueue-time decision, not recomputed.
        self.assertEqual(
            request['variables']['notifyCustomer'], snapshot['notify_customer'],
        )
        self.assertEqual(
            request['preconditions_snapshot']['notify_customer'],
            snapshot['notify_customer'],
        )
        self.assertTrue(request['shopify_idempotency_key'])  # non-empty (core gate); never in the operation

    def test_prepare_persists_notify_false_decision(self):
        node = {'id': 'gid://shopify/Fulfillment/1', 'status': 'SUCCESS',
                'trackingInfo': []}
        snapshot = self._local_snapshot(notify_customer=False)
        with patch.object(
            type(self.Service), '_read_fulfillment', return_value=node,
        ):
            request = (
                self.Service
                ._prepare_preconditions_fulfillment_tracking_update(snapshot, {})
            )
        self.assertFalse(request['variables']['notifyCustomer'])
        self.assertFalse(request['preconditions_snapshot']['notify_customer'])

    def test_prepare_cancelled_fulfillment_fails_closed(self):
        node = {'id': 'gid://shopify/Fulfillment/1', 'status': 'CANCELLED',
                'trackingInfo': []}
        snapshot = self._local_snapshot()
        with patch.object(
            type(self.Service), '_read_fulfillment', return_value=node,
        ):
            with self.assertRaises(FulfillmentPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_fulfillment_tracking_update(
                    snapshot, {},
                )
        self.assertEqual(ctx.exception.error_class, 'binding_conflict')

    def test_prepare_missing_fulfillment_fails_closed(self):
        snapshot = self._local_snapshot()
        with patch.object(
            type(self.Service), '_read_fulfillment', return_value=None,
        ):
            with self.assertRaises(FulfillmentPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_fulfillment_tracking_update(
                    snapshot, {},
                )
        self.assertEqual(ctx.exception.error_class, 'ambiguous_match')

    # ------------------------------------------------------------------
    # Multi-number split reaches the trackingInfoInput
    # ------------------------------------------------------------------

    def test_carrier_ref_comma_split_to_numbers_list(self):
        # `_picking_tracking_numbers` splits a 'A,B' carrier_tracking_ref into
        # the two-number list that feeds trackingInfoInput.
        customer_loc = self.env.ref('stock.stock_location_customers')
        stock_loc = self.env.ref('stock.stock_location_stock')
        pt_out = self.env['stock.picking.type'].search(
            [('code', '=', 'outgoing')], limit=1,
        )
        picking = self.env['stock.picking'].create({
            'picking_type_id': pt_out.id,
            'location_id': stock_loc.id,
            'location_dest_id': customer_loc.id,
            'carrier_tracking_ref': 'A,B',
        })
        self.assertEqual(
            self.Service._picking_tracking_numbers(picking), ['A', 'B'],
        )

    def test_prepare_multi_number_split_reaches_tracking_input(self):
        node = {'id': 'gid://shopify/Fulfillment/1', 'status': 'SUCCESS',
                'trackingInfo': []}
        snapshot = self._local_snapshot(tracking_numbers=['A', 'B'])
        with patch.object(
            type(self.Service), '_read_fulfillment', return_value=node,
        ):
            request = (
                self.Service
                ._prepare_preconditions_fulfillment_tracking_update(snapshot, {})
            )
        self.assertEqual(
            request['variables']['trackingInfoInput']['numbers'], ['A', 'B'],
        )
