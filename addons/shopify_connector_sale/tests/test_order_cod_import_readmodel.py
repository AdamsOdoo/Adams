from pathlib import Path

from .test_order_import_mapping import OrderImportCase


class TestOrderCodImportReadModel(OrderImportCase):

    def _cod_payload(self, gid, transaction_status='PENDING', amount='0.00'):
        payload = self._payload(gid, 'PENDING')
        payload['paymentGatewayNames'] = ['Cash on Delivery']
        payload['transactions'] = [self._transaction(
            gateway='Cash on Delivery', manual=True,
            status=transaction_status, amount=amount,
        )]
        return payload

    def test_cod_dimensions_initialize_without_accounting_side_effects(self):
        self.settings.write({
            'manual_gateway_policy': 'quotation',
            'approved_manual_gateways': 'Cash on Delivery',
        })
        moves_before = self.env['account.move'].search_count([])
        payments_before = self.env['account.payment'].search_count([])
        binding = self.Importer._apply_import(
            self.store,
            self._cod_payload('gid://shopify/Order/CODReadModel'),
        )
        self.assertTrue(binding.is_cod)
        self.assertEqual(binding.cod_commercial_state, 'quotation')
        self.assertEqual(binding.cod_fulfillment_state, 'not_dispatched')
        self.assertEqual(binding.cod_collection_state, 'nothing_collected')
        self.assertEqual(binding.cod_order_value_amount, '100.00')
        self.assertEqual(binding.cod_fulfilled_value_amount, '0')
        self.assertEqual(binding.cod_collected_value_amount, '0')
        self.assertEqual(binding.cod_refunded_value_amount, '0')
        self.assertEqual(binding.cod_cancelled_value_amount, '0')
        self.assertEqual(self.env['account.move'].search_count([]), moves_before)
        self.assertEqual(
            self.env['account.payment'].search_count([]), payments_before,
        )

    def test_successful_manual_transaction_is_snapshot_only(self):
        self.settings.write({
            'manual_gateway_policy': 'quotation',
            'approved_manual_gateways': 'Cash on Delivery',
        })
        binding = self.Importer._apply_import(
            self.store,
            self._cod_payload(
                'gid://shopify/Order/CODCollected',
                transaction_status='SUCCESS', amount='100.00',
            ),
        )
        self.assertEqual(binding.cod_collection_state, 'fully_collected')
        self.assertEqual(binding.cod_collected_value_amount, '100.00')
        self.assertEqual(binding.sale_order_id.state, 'draft')
        self.assertFalse(self.env['account.payment'].search([
            ('ref', '=', binding.shopify_order_name),
        ]))

    def test_non_cod_order_does_not_acquire_cod_flag(self):
        binding = self.Importer._apply_import(
            self.store, self._payload('gid://shopify/Order/NotCOD'),
        )
        self.assertFalse(binding.is_cod)
        self.assertEqual(binding.cod_collection_state, 'nothing_collected')

    def test_source_contains_no_mark_paid_or_payment_creation(self):
        source = (
            Path(__file__).resolve().parents[1]
            / 'models' / 'shopify_connector_order_importer.py'
        ).read_text(encoding='utf-8')
        self.assertNotIn('orderMarkAsPaid', source)
        self.assertNotIn('orderCreateManualPayment', source)
        self.assertNotIn("env['account.payment'].create", source)
        self.assertNotIn("env['account.move'].create", source)

