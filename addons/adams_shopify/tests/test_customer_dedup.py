from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase


class TestCustomerDedup(TransactionCase):
    """Tests for customer deduplication across import paths."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'customer_dedup_field': 'email',
        })

    def _get_importer(self):
        from ..sync.customer_sync import CustomerImporter
        importer = CustomerImporter.__new__(CustomerImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        return importer

    def _make_customer_node(self, shopify_id, email=None, phone=None,
                            first='John', last='Doe'):
        return {
            'id': shopify_id,
            'firstName': first,
            'lastName': last,
            'email': email,
            'phone': phone,
            'tags': [],
            'defaultAddress': {},
            'addresses': [],
        }

    def test_email_dedup_matches_existing_partner(self):
        """Email dedup should find existing partner by email."""
        existing = self.env['res.partner'].create({
            'name': 'Existing Customer',
            'email': 'john@example.com',
        })
        importer = self._get_importer()
        node = self._make_customer_node(
            'gid://shopify/Customer/100', email='john@example.com',
        )
        found = importer._find_odoo_partner(node)
        self.assertEqual(found, existing)

    def test_email_dedup_case_insensitive(self):
        """Email matching should be case-insensitive."""
        existing = self.env['res.partner'].create({
            'name': 'Jane', 'email': 'JANE@EXAMPLE.COM',
        })
        importer = self._get_importer()
        node = self._make_customer_node(
            'gid://shopify/Customer/101', email='jane@example.com',
        )
        found = importer._find_odoo_partner(node)
        self.assertEqual(found, existing)

    def test_phone_dedup_matches_by_phone_field(self):
        """Phone dedup should match by phone field."""
        self.backend.customer_dedup_field = 'phone'
        existing = self.env['res.partner'].create({
            'name': 'Phone User', 'phone': '+15551234567',
        })
        importer = self._get_importer()
        node = self._make_customer_node(
            'gid://shopify/Customer/102', phone='+15551234567',
        )
        found = importer._find_odoo_partner(node)
        self.assertEqual(found, existing)

    def test_phone_dedup_matches_by_mobile_field(self):
        """Phone dedup should also check mobile field."""
        self.backend.customer_dedup_field = 'phone'
        existing = self.env['res.partner'].create({
            'name': 'Mobile User', 'mobile': '+15559876543',
        })
        importer = self._get_importer()
        node = self._make_customer_node(
            'gid://shopify/Customer/103', phone='+15559876543',
        )
        found = importer._find_odoo_partner(node)
        self.assertEqual(found, existing)

    def test_email_phone_dedup_prefers_email(self):
        """email_phone strategy should try email first."""
        self.backend.customer_dedup_field = 'email_phone'
        email_partner = self.env['res.partner'].create({
            'name': 'Email Match', 'email': 'both@example.com',
        })
        phone_partner = self.env['res.partner'].create({
            'name': 'Phone Match', 'phone': '+15550001111',
        })
        importer = self._get_importer()
        node = self._make_customer_node(
            'gid://shopify/Customer/104',
            email='both@example.com',
            phone='+15550001111',
        )
        found = importer._find_odoo_partner(node)
        self.assertEqual(found, email_partner)

    def test_email_phone_dedup_falls_back_to_phone(self):
        """email_phone strategy falls back to phone when no email match."""
        self.backend.customer_dedup_field = 'email_phone'
        phone_partner = self.env['res.partner'].create({
            'name': 'Phone Fallback', 'phone': '+15552223333',
        })
        importer = self._get_importer()
        node = self._make_customer_node(
            'gid://shopify/Customer/105',
            email='nonexistent@example.com',
            phone='+15552223333',
        )
        found = importer._find_odoo_partner(node)
        self.assertEqual(found, phone_partner)

    def test_no_match_returns_none(self):
        """Should return None when no partner matches."""
        importer = self._get_importer()
        node = self._make_customer_node(
            'gid://shopify/Customer/106', email='nobody@nowhere.com',
        )
        found = importer._find_odoo_partner(node)
        self.assertFalse(found)

    def test_binding_lookup_takes_priority(self):
        """Existing binding should be found before email dedup."""
        partner = self.env['res.partner'].create({
            'name': 'Bound Customer', 'email': 'bound@example.com',
        })
        self.env['shopify.customer.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': partner.id,
            'shopify_id': 'gid://shopify/Customer/107',
            'sync_status': 'synced',
        })
        # Create another partner with the same email
        self.env['res.partner'].create({
            'name': 'Other Partner', 'email': 'bound@example.com',
        })

        importer = self._get_importer()
        node = self._make_customer_node(
            'gid://shopify/Customer/107', email='bound@example.com',
        )
        found = importer._find_odoo_partner(node)
        self.assertEqual(found, partner)

    def test_address_dedup_prevents_duplicates(self):
        """Re-importing addresses should not create duplicates."""
        partner = self.env['res.partner'].create({
            'name': 'Addr Test', 'email': 'addr@example.com',
        })
        # Create an existing child address
        self.env['res.partner'].create({
            'parent_id': partner.id,
            'type': 'other',
            'name': 'Addr Test',
            'street': '123 Main St',
            'city': 'Springfield',
        })

        importer = self._get_importer()
        node = self._make_customer_node(
            'gid://shopify/Customer/108', email='addr@example.com',
        )
        node['addresses'] = [
            {'address1': '123 Main St', 'city': 'Springfield'},  # default (skipped)
            {'address1': '123 Main St', 'city': 'Springfield'},  # dupe
        ]
        importer._import_addresses(partner, node)

        children = self.env['res.partner'].search([
            ('parent_id', '=', partner.id),
        ])
        self.assertEqual(len(children), 1)  # Should still be 1, not 2

    def test_order_import_creates_binding(self):
        """Order import should create a customer binding for new customers."""
        from ..sync.order_sync import OrderImporter
        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        node = {
            'customer': {
                'id': 'gid://shopify/Customer/200',
                'email': 'newbuyer@example.com',
                'firstName': 'New',
                'lastName': 'Buyer',
                'phone': None,
            },
        }
        partner = importer._resolve_customer(node)
        self.assertTrue(partner)
        self.assertEqual(partner.email, 'newbuyer@example.com')

        # Binding should have been created
        binding = self.env['shopify.customer.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Customer/200'),
        ])
        self.assertTrue(binding)
        self.assertEqual(binding.odoo_id, partner)

    def test_guest_order_dedup_by_email(self):
        """Guest orders should dedup by email from shipping address."""
        existing = self.env['res.partner'].create({
            'name': 'Guest', 'email': 'guest@example.com',
        })

        from ..sync.order_sync import OrderImporter
        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        node = {
            'customer': None,
            'email': 'guest@example.com',
            'shippingAddress': {
                'firstName': 'Guest', 'lastName': 'User',
                'phone': '+15551112222',
            },
        }
        partner = importer._resolve_customer(node)
        self.assertEqual(partner, existing)
