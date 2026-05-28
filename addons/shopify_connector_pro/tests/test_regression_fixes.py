# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Regression tests for bugs fixed in 9bc6ec4.

These tests specifically guard against:
1. Sync-loop prevention: accounting operations triggered by inbound Shopify
   events must include `shopify_no_auto_export` context to suppress reverse-sync.
2. Singleton bug in _mark_error: must handle multi-record recordsets.
3. Missing images field in webhook product import query.
"""
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin


class TestSyncLoopPrevention(ShopifyAccountingMixin, TransactionCase):
    """Guard against Shopify<->Odoo infinite sync loops.

    The reverse-sync hooks on account.move.action_post fire when invoices
    are posted.  Inbound handlers (payment transitions, refund imports,
    refund webhooks) must suppress these hooks via context flags.
    """

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Loop Test Store',
            'shop_url': 'loop-test.myshopify.com',
            'access_token': 'shpat_loop_test',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'auto_handle_payment_transitions': True,
            'reverse_sync_payment': True,
        })

        self.product = self.env['product.product'].create({
            'name': 'Loop Widget', 'list_price': 100.0,
        })
        self._set_product_income_account(self.product)

        self.partner = self._create_accounting_partner(
            'Loop Customer', email='loop@example.com',
        )

    def _create_confirmed_order_with_binding(self, financial_status='authorized'):
        order = self.env['sale.order'].with_context(
            shopify_no_auto_export=True,
        ).create({
            'partner_id': self.partner.id,
            'company_id': self.backend.company_id.id,
            'warehouse_id': self.backend.warehouse_id.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        order.with_context(shopify_no_auto_export=True).action_confirm()
        binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': order.id,
            'shopify_id': f'gid://shopify/Order/{order.id}',
            'shopify_order_name': f'#TEST-{order.id}',
            'shopify_financial_status': financial_status,
            'sync_status': 'synced',
        })
        return order, binding

    def test_transition_to_paid_suppresses_reverse_sync(self):
        """_transition_to_paid must post invoice WITH shopify_no_auto_export."""
        from ..sync.payment_status_sync import PaymentStatusHandler

        order, binding = self._create_confirmed_order_with_binding('authorized')

        # Create a draft invoice on the order
        invoice = order.with_context(
            shopify_no_auto_export=True,
        )._create_invoices()
        self.assertTrue(invoice)
        self.assertEqual(invoice.state, 'draft')

        # Patch action_post to capture the context it's called with
        original_action_post = type(invoice).action_post
        contexts_seen = []

        def capture_post(self_move):
            contexts_seen.append(dict(self_move.env.context))
            return original_action_post(self_move)

        handler = PaymentStatusHandler(self.env, self.backend)

        with patch.object(type(invoice), 'action_post', capture_post):
            handler._transition_to_paid(binding, 'authorized', 'paid')

        self.assertTrue(contexts_seen, "action_post should have been called")
        self.assertTrue(
            contexts_seen[0].get('shopify_no_auto_export'),
            "action_post must be called with shopify_no_auto_export=True "
            "to prevent Shopify->Odoo->Shopify sync loop",
        )

    def test_transition_to_partially_paid_suppresses_reverse_sync(self):
        """_transition_to_partially_paid must post with loop prevention."""
        from ..sync.payment_status_sync import PaymentStatusHandler

        order, binding = self._create_confirmed_order_with_binding('pending')

        invoice = order.with_context(
            shopify_no_auto_export=True,
        )._create_invoices()

        original_action_post = type(invoice).action_post
        contexts_seen = []

        def capture_post(self_move):
            contexts_seen.append(dict(self_move.env.context))
            return original_action_post(self_move)

        handler = PaymentStatusHandler(self.env, self.backend)

        with patch.object(type(invoice), 'action_post', capture_post):
            handler._transition_to_partially_paid(binding, 'pending', 'partially_paid')

        self.assertTrue(contexts_seen, "action_post should have been called")
        self.assertTrue(
            contexts_seen[0].get('shopify_no_auto_export'),
            "partially_paid handler must suppress reverse sync",
        )

    def test_transition_to_voided_suppresses_reverse_sync(self):
        """_transition_to_voided must cancel with loop prevention."""
        from ..sync.payment_status_sync import PaymentStatusHandler

        order, binding = self._create_confirmed_order_with_binding('authorized')

        # Create a draft invoice
        invoice = order.with_context(
            shopify_no_auto_export=True,
        )._create_invoices()

        original_button_cancel = type(invoice).button_cancel
        contexts_seen = []

        def capture_cancel(self_move):
            contexts_seen.append(dict(self_move.env.context))
            return original_button_cancel(self_move)

        handler = PaymentStatusHandler(self.env, self.backend)

        with patch.object(type(invoice), 'button_cancel', capture_cancel):
            handler._transition_to_voided(binding, 'authorized', 'voided')

        self.assertTrue(contexts_seen, "button_cancel should have been called")
        self.assertTrue(
            contexts_seen[0].get('shopify_no_auto_export'),
            "voided handler must suppress reverse sync on invoice cancel",
        )

    def test_refund_import_suppresses_reverse_sync(self):
        """RefundImporter._import_one_refund must create credit note with loop guard.

        The refund importer now creates account.move directly (instead of
        account.move.reversal) to support partial-refund amounts.  We
        verify that the account.move is created under shopify_no_auto_export
        context so the reverse-sync hook does not fire.
        """
        from ..sync.refund_sync import RefundImporter

        order, binding = self._create_confirmed_order_with_binding('paid')
        # Create and post an invoice so the refund has something to reverse
        invoice = order.with_context(
            shopify_no_auto_export=True,
        )._create_invoices()
        invoice.with_context(shopify_no_auto_export=True).action_post()

        importer = RefundImporter.__new__(RefundImporter)
        importer.env = self.env
        importer.backend = self.backend

        refund_data = {
            'id': 'gid://shopify/Refund/999',
            'totalRefundedSet': {'shopMoney': {'amount': '50', 'currencyCode': 'USD'}},
            'note': 'Test refund',
            'refundLineItems': {'edges': []},
        }

        # Capture context on account.move creation (credit note)
        AccountMove = type(self.env['account.move'])
        original_create = AccountMove.create
        contexts_seen = []

        def capture_create(self_model, vals_list):
            ctx = dict(self_model.env.context)
            # Only capture credit note creations
            if isinstance(vals_list, dict):
                vl = [vals_list]
            else:
                vl = vals_list
            for v in vl:
                if v.get('move_type') == 'out_refund':
                    contexts_seen.append(ctx)
            return original_create(self_model, vals_list)

        with patch.object(AccountMove, 'create', capture_create):
            importer._import_one_refund(refund_data, binding)

        self.assertTrue(contexts_seen, "account.move.create (out_refund) should have been called")
        self.assertTrue(
            contexts_seen[0].get('shopify_no_auto_export'),
            "Refund import must create credit note with shopify_no_auto_export "
            "to prevent duplicate refund on Shopify",
        )


class TestMarkErrorMultiRecord(TransactionCase):
    """Regression: _mark_error must handle multi-record recordsets."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Error Test Store',
            'shop_url': 'err-test.myshopify.com',
            'access_token': 'shpat_err_test',
            'company_id': self.env.company.id,
        })
        self.product_a = self.env['product.product'].create({'name': 'Err A'})
        self.product_b = self.env['product.product'].create({'name': 'Err B'})

    def test_mark_error_on_multi_record_set(self):
        """_mark_error on a recordset with > 1 record must NOT raise singleton."""
        binding_a = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product_a.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/A',
            'sync_status': 'pending',
            'retry_count': 0,
        })
        binding_b = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product_b.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/B',
            'sync_status': 'pending',
            'retry_count': 2,
        })
        multi = binding_a | binding_b

        # This must not raise "Expected singleton"
        multi._mark_error("batch failure")

        self.assertEqual(binding_a.sync_status, 'error')
        self.assertEqual(binding_b.sync_status, 'error')
        self.assertEqual(binding_a.retry_count, 1)
        self.assertEqual(binding_b.retry_count, 3)

    def test_mark_error_permanent_on_multi_record(self):
        """permanent=True on multi-record sets retry_count unchanged."""
        binding_a = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product_a.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/PA',
            'sync_status': 'pending',
            'retry_count': 5,
        })
        binding_b = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product_b.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/PB',
            'sync_status': 'error',
            'retry_count': 3,
        })
        multi = binding_a | binding_b
        multi._mark_error("permanent failure", permanent=True)

        self.assertEqual(binding_a.sync_status, 'permanent_error')
        self.assertEqual(binding_b.sync_status, 'permanent_error')
        # retry_count should not increment for permanent errors
        self.assertEqual(binding_a.retry_count, 5)
        self.assertEqual(binding_b.retry_count, 3)


class TestProductWebhookImagesField(TransactionCase):
    """Regression: product webhook import query must include images field."""

    def test_import_single_product_query_includes_images(self):
        """The GraphQL query in import_single_product must fetch images."""
        from ..sync.product_sync import ProductSync

        backend = self.env['shopify.backend'].create({
            'name': 'Image Test Store',
            'shop_url': 'img-test.myshopify.com',
            'access_token': 'shpat_img_test',
            'company_id': self.env.company.id,
        })

        # import_single_product does `from ..shopify_api.client import ShopifyClient`
        # inline. Patch at the module level used by the import.
        mock_client = MagicMock()
        mock_client.execute.return_value = {
            'data': {'product': None},
        }

        with patch(
            'odoo.addons.shopify_connector_pro.shopify_api.client.ShopifyClient',
            return_value=mock_client,
        ):
            sync = ProductSync(self.env, backend)
            sync.importer.client = mock_client
            sync.import_single_product({'id': 12345})

            # Verify execute was called and the query includes images
            self.assertTrue(
                mock_client.execute.called,
                "ShopifyClient.execute should be called to fetch product",
            )
            query_arg = mock_client.execute.call_args[0][0]
            self.assertIn('images', query_arg,
                "Product webhook query must include images field "
                "to sync image changes from Shopify")
