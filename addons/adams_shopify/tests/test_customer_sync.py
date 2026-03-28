from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase


class TestCustomerSync(TransactionCase):

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
        })

    def test_import_new_customer(self):
        """Should create a new partner from Shopify customer data."""
        from ..sync.customer_sync import CustomerImporter

        node = {
            'id': 'gid://shopify/Customer/100',
            'firstName': 'John',
            'lastName': 'Doe',
            'email': 'john.doe@example.com',
            'phone': '+1234567890',
            'tags': ['vip', 'wholesale'],
            'state': 'ENABLED',
            'defaultAddress': {
                'address1': '123 Main St',
                'address2': '',
                'city': 'New York',
                'province': 'New York',
                'provinceCode': 'NY',
                'country': 'United States',
                'countryCodeV2': 'US',
                'zip': '10001',
                'phone': '+1234567890',
            },
            'addresses': [],
        }

        importer = CustomerImporter.__new__(CustomerImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.customer.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Customer/100'),
        ])
        self.assertTrue(binding)
        self.assertEqual(binding.shopify_email, 'john.doe@example.com')
        self.assertEqual(binding.odoo_id.name, 'John Doe')
        self.assertEqual(binding.odoo_id.email, 'john.doe@example.com')
        self.assertTrue(binding.odoo_id.is_shopify_customer)

    def test_import_dedup_by_email(self):
        """Should match existing partner by email instead of creating duplicate."""
        from ..sync.customer_sync import CustomerImporter

        existing_partner = self.env['res.partner'].create({
            'name': 'Existing Customer',
            'email': 'existing@example.com',
        })

        node = {
            'id': 'gid://shopify/Customer/200',
            'firstName': 'Existing',
            'lastName': 'Customer',
            'email': 'existing@example.com',
            'phone': '',
            'tags': [],
            'state': 'ENABLED',
            'defaultAddress': None,
            'addresses': [],
        }

        importer = CustomerImporter.__new__(CustomerImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.customer.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Customer/200'),
        ])
        self.assertTrue(binding)
        # Should link to existing partner, not create a new one
        self.assertEqual(binding.odoo_id.id, existing_partner.id)

    def test_import_updates_existing_binding(self):
        """Should update partner when binding already exists."""
        from ..sync.customer_sync import CustomerImporter

        partner = self.env['res.partner'].create({
            'name': 'Old Name',
            'email': 'test@example.com',
        })
        binding = self.env['shopify.customer.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': partner.id,
            'shopify_id': 'gid://shopify/Customer/300',
            'sync_status': 'synced',
        })

        node = {
            'id': 'gid://shopify/Customer/300',
            'firstName': 'New',
            'lastName': 'Name',
            'email': 'test@example.com',
            'phone': '+9876543210',
            'tags': [],
            'defaultAddress': None,
            'addresses': [],
        }

        importer = CustomerImporter.__new__(CustomerImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        importer._import_one(node, existing_binding=binding)

        partner.invalidate_recordset()
        self.assertEqual(partner.name, 'New Name')
        self.assertEqual(partner.phone, '+9876543210')
