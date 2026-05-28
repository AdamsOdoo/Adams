# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from datetime import timedelta
from unittest.mock import patch, MagicMock

from odoo import fields
from odoo.tests.common import TransactionCase


class TestReconciliationRetryErrors(TransactionCase):
    """Tests for _reconcile_retry_errors (BUG-EW-12a/12b)."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
        })
        self.reconciliation = self.env['shopify.reconciliation']
        self.old_date = fields.Datetime.now() - timedelta(hours=7)

    def test_retry_errors_includes_customer_bindings(self):
        """BUG-EW-12a: reconciliation should retry stuck customer bindings, not just products."""
        partner = self.env['res.partner'].create({'name': 'Stuck Customer'})
        binding = self.env['shopify.customer.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': partner.id,
            'shopify_id': 'gid://shopify/Customer/100',
            'sync_status': 'error',
            'sync_error': 'Temporary failure',
            'retry_count': 2,
        })
        # Backdate write_date to make it "stuck"
        self.env.cr.execute(
            "UPDATE shopify_customer_binding SET write_date = %s WHERE id = %s",
            (self.old_date, binding.id),
        )
        binding.invalidate_recordset()

        self.reconciliation._reconcile_retry_errors(self.backend)

        binding.invalidate_recordset()
        self.assertEqual(
            binding.sync_status, 'pending',
            "Stuck customer binding should be reset to pending",
        )

    def test_retry_errors_includes_order_bindings(self):
        """BUG-EW-12a: reconciliation should retry stuck order bindings."""
        order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'P'}).id,
        })
        binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': order.id,
            'shopify_id': 'gid://shopify/Order/200',
            'sync_status': 'error',
            'sync_error': 'Temporary failure',
            'retry_count': 1,
        })
        self.env.cr.execute(
            "UPDATE shopify_order_binding SET write_date = %s WHERE id = %s",
            (self.old_date, binding.id),
        )
        binding.invalidate_recordset()

        self.reconciliation._reconcile_retry_errors(self.backend)

        binding.invalidate_recordset()
        self.assertEqual(
            binding.sync_status, 'pending',
            "Stuck order binding should be reset to pending",
        )

    def test_retry_count_increments_not_resets(self):
        """BUG-EW-12b: retry_count should increment, not reset to 0."""
        product = self.env['product.template'].create({'name': 'Retry Test'})
        binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': product.id,
            'shopify_id': 'gid://shopify/Product/300',
            'sync_status': 'error',
            'sync_error': 'Temp error',
            'retry_count': 3,
        })
        self.env.cr.execute(
            "UPDATE shopify_product_binding SET write_date = %s WHERE id = %s",
            (self.old_date, binding.id),
        )
        binding.invalidate_recordset()

        self.reconciliation._reconcile_retry_errors(self.backend)

        binding.invalidate_recordset()
        self.assertEqual(binding.sync_status, 'pending')
        self.assertEqual(
            binding.retry_count, 4,
            "retry_count should increment from 3 to 4, not reset to 0",
        )

    def test_retry_skips_permanent_errors(self):
        """Permanent errors should not be retried by reconciliation."""
        product = self.env['product.template'].create({'name': 'Permanent'})
        binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': product.id,
            'shopify_id': 'gid://shopify/Product/400',
            'sync_status': 'permanent_error',
            'sync_error': '404 Not Found',
            'retry_count': 2,
        })
        self.env.cr.execute(
            "UPDATE shopify_product_binding SET write_date = %s WHERE id = %s",
            (self.old_date, binding.id),
        )
        binding.invalidate_recordset()

        self.reconciliation._reconcile_retry_errors(self.backend)

        binding.invalidate_recordset()
        self.assertEqual(
            binding.sync_status, 'permanent_error',
            "Permanent errors should not be retried",
        )
