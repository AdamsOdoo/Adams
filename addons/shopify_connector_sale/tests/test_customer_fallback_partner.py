import os

from odoo.tests.common import TransactionCase


class TestCustomerFallbackPartner(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Settings = cls.env['shopify.connector.store.settings']
        cls.Importer = cls.env['shopify.connector.customer.importer']

    def _make_store(self, domain):
        return self.env['shopify.connector.store'].create({
            'name': 'Fallback Partner Test Store %s' % domain,
            'shop_domain': domain,
            'api_version': '2026-07',
        })

    def _customer_payload(
        self, gid, email=None, display_name=None, address=None,
    ):
        return {
            'gid': gid, 'first_name': None, 'last_name': None,
            'display_name': display_name or gid, 'email': email,
            'phone': None, 'address': address,
        }

    # ------------------------------------------------------------------
    # 1. Field exists on shopify.connector.store.settings, type
    # Many2one('res.partner'), unset by default.
    # ------------------------------------------------------------------

    def test_field_exists_and_unset_by_default(self):
        store = self._make_store('fallback-field-test.myshopify.com')
        settings = self.Settings.create({'store_id': store.id})
        field = self.Settings._fields['customer_fallback_partner_id']
        self.assertEqual(field.type, 'many2one')
        self.assertEqual(field.comodel_name, 'res.partner')
        self.assertFalse(settings.customer_fallback_partner_id)

    # ------------------------------------------------------------------
    # 2. No partner record is auto-created anywhere by module install,
    # settings creation, or import runs.
    # ------------------------------------------------------------------

    def test_no_partner_auto_created_by_settings_creation(self):
        store = self._make_store('fallback-no-autocreate-test.myshopify.com')
        partners_before = self.env['res.partner'].search_count([])
        self.Settings.create({'store_id': store.id})
        self.assertEqual(
            self.env['res.partner'].search_count([]), partners_before,
        )

    def test_no_partner_auto_created_by_import_run(self):
        store = self._make_store(
            'fallback-import-no-autocreate-test.myshopify.com',
        )
        fallback_partner = self.env['res.partner'].create({
            'name': 'Fallback Partner',
        })
        self.Settings.create({
            'store_id': store.id,
            'customer_fallback_partner_id': fallback_partner.id,
        })
        partners_before = self.env['res.partner'].search_count([])
        payload = self._customer_payload(
            'gid://shopify/Customer/2000', email='no-autocreate@example.com',
        )
        self.Importer._apply_import(store, payload)
        # Exactly one new partner -- the matched customer, never a
        # second copy of the fallback partner.
        self.assertEqual(
            self.env['res.partner'].search_count([]), partners_before + 1,
        )

    # ------------------------------------------------------------------
    # 3. Posture A behavioral proof: identical payload streams produce
    # byte-identical matching outcomes whether the field is unset or set;
    # no importer code path reads the field.
    # ------------------------------------------------------------------

    def test_posture_a_unset_vs_set_byte_identical_outcome(self):
        store_unset = self._make_store('fallback-unset-test.myshopify.com')
        store_set = self._make_store('fallback-set-test.myshopify.com')
        fallback_partner = self.env['res.partner'].create({
            'name': 'Fallback Partner 2',
        })
        self.Settings.create({'store_id': store_unset.id})
        self.Settings.create({
            'store_id': store_set.id,
            'customer_fallback_partner_id': fallback_partner.id,
        })
        address = {
            'address1': '1 Posture Way', 'address2': None,
            'city': 'Postureville', 'zip': '54321',
            'province_code': None, 'country_code': None,
        }
        payload_unset = self._customer_payload(
            'gid://shopify/Customer/2001', email='posture-a@example.com',
            display_name='Posture Customer', address=address,
        )
        payload_set = dict(payload_unset, gid='gid://shopify/Customer/2002')
        result_unset = self.Importer._apply_import(store_unset, payload_unset)
        result_set = self.Importer._apply_import(store_set, payload_set)
        self.assertEqual(result_unset.match_key, result_set.match_key)
        self.assertEqual(
            result_unset.partner_id.name, result_set.partner_id.name,
        )
        self.assertEqual(
            result_unset.partner_id.street, result_set.partner_id.street,
        )
        self.assertEqual(
            result_unset.partner_id.is_company, result_set.partner_id.is_company,
        )
        self.assertEqual(
            result_unset.partner_id.company_type,
            result_set.partner_id.company_type,
        )

    def test_source_level_importer_never_reads_fallback_field(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'shopify_connector_customer_importer.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            content = source_file.read()
        self.assertNotIn('customer_fallback_partner_id', content)
