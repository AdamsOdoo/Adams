import json
import uuid

from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_inbound import (  # noqa: E501
    A4_DEPRECATED,
    A4_FULFILLMENT_STATUS_KNOWN,
    A4_SUCCESS_VALUE,
    A5_EVENT_DELIVERED,
)


class TestFulfillmentStateModel(TransactionCase):
    """Layer-A state normalization (status model §7, unknown-future-value
    contract). `_normalize_fulfillment_status` returns (label, is_success,
    is_known): SUCCESS is the only success value; the terminal non-success
    values and the deprecated OPEN/PENDING are known-but-not-success; any
    unverified value is preserved raw, never success, and flagged. Through
    `_observe_fulfillment` an unknown status raises a schema warning and keeps
    the raw value, an A5 DELIVERED milestone never marks success, and the
    state snapshot stores the raw A4 and A7 values (seven-family audit)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['shopify.connector.fulfillment.service']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'FUL Test',
            'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'fulfillment_domain_enabled': True,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'C'})
        cls.sale = cls.env['sale.order'].create({'partner_id': cls.partner.id})
        cls.order_binding = cls.env['shopify.connector.order.binding'].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Order/900',
            'sale_order_id': cls.sale.id,
            'status': 'active',
        })

    def _observe(self, fulfillment_gid, status, display_status='FULFILLED'):
        node = {
            'id': fulfillment_gid,
            'status': status,
            'displayStatus': display_status,
            'trackingInfo': [],
        }
        return self.Service._observe_fulfillment(
            self.store, self.order_binding, node, 'mode1',
        )

    # ------------------------------------------------------------------
    # _normalize_fulfillment_status
    # ------------------------------------------------------------------

    def test_success_is_success_and_known(self):
        label, is_success, is_known = self.Service._normalize_fulfillment_status(
            A4_SUCCESS_VALUE,
        )
        self.assertEqual(label, 'Success')
        self.assertTrue(is_success)
        self.assertTrue(is_known)

    def test_terminal_non_success_values_are_known_not_success(self):
        for raw in ('CANCELLED', 'ERROR', 'FAILURE'):
            label, is_success, is_known = (
                self.Service._normalize_fulfillment_status(raw)
            )
            self.assertTrue(is_known, raw)
            self.assertFalse(is_success, raw)
            self.assertEqual(label, A4_FULFILLMENT_STATUS_KNOWN[raw], raw)

    def test_deprecated_open_pending_known_but_not_success(self):
        for raw in A4_DEPRECATED:  # {'OPEN', 'PENDING'}
            label, is_success, is_known = (
                self.Service._normalize_fulfillment_status(raw)
            )
            self.assertTrue(is_known, raw)
            self.assertFalse(is_success, raw)
            self.assertTrue(label.startswith('Legacy:'), raw)

    def test_unknown_future_value_is_unknown_not_success(self):
        label, is_success, is_known = (
            self.Service._normalize_fulfillment_status('FUTURE_STATE')
        )
        self.assertFalse(is_known)
        self.assertFalse(is_success)
        self.assertTrue(label.startswith('Unknown:'))
        self.assertIn('FUTURE_STATE', label)

    def test_a5_delivered_milestone_never_marks_success(self):
        # A5 FulfillmentEvent DELIVERED is a delivery milestone, not an A4
        # FulfillmentStatus success value; it is never treated as success.
        label, is_success, is_known = (
            self.Service._normalize_fulfillment_status(A5_EVENT_DELIVERED)
        )
        self.assertFalse(is_success)
        self.assertFalse(is_known)
        self.assertTrue(label.startswith('Unknown:'))

    # ------------------------------------------------------------------
    # _observe_fulfillment
    # ------------------------------------------------------------------

    def test_unknown_status_sets_schema_warning_and_preserves_raw(self):
        evidence = self._observe(
            'gid://shopify/Fulfillment/UNK', 'FUTURE_STATE',
        )
        self.assertTrue(evidence.schema_warning)
        self.assertEqual(evidence.fulfillment_status_raw, 'FUTURE_STATE')
        self.assertFalse(evidence.fulfillment_status_is_success)
        self.assertTrue(
            evidence.fulfillment_status_normalized.startswith('Unknown:')
        )

    def test_observed_a5_delivered_status_never_marks_success(self):
        evidence = self._observe(
            'gid://shopify/Fulfillment/DEL', A5_EVENT_DELIVERED,
        )
        self.assertFalse(evidence.fulfillment_status_is_success)
        # DELIVERED is not an A4 value -> preserved raw and flagged.
        self.assertTrue(evidence.schema_warning)
        self.assertEqual(evidence.fulfillment_status_raw, A5_EVENT_DELIVERED)

    def test_state_snapshot_stores_raw_a4_and_a7(self):
        evidence = self._observe(
            'gid://shopify/Fulfillment/SNAP', 'SUCCESS',
            display_status='FULFILLED',
        )
        snapshot = json.loads(evidence.state_snapshot)
        self.assertEqual(snapshot['A4_FulfillmentStatus'], 'SUCCESS')
        self.assertEqual(snapshot['A7_displayStatus'], 'FULFILLED')
