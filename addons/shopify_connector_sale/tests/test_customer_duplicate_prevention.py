import json
import os

from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)


class TestCustomerDuplicatePrevention(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Customer Duplicate Prevention Test Store',
            'shop_domain': 'customer-duplicate-prevention-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.customer.importer']
        cls.CustomerBinding = cls.env['shopify.connector.customer.binding']

    def _customer_payload(
        self, gid, email=None, display_name=None, address=None,
    ):
        return {
            'gid': gid, 'first_name': None, 'last_name': None,
            'display_name': display_name or gid, 'email': email,
            'phone': None, 'address': address,
        }

    def _make_partner(self, name, email=None):
        vals = {'name': name}
        if email is not None:
            vals['email'] = email
        return self.env['res.partner'].create(vals)

    # ------------------------------------------------------------------
    # 1. Re-importing the same Customer GID binds to the existing row --
    # never a duplicate partner, never a duplicate binding.
    # ------------------------------------------------------------------

    def test_reimport_same_gid_binds_existing_never_duplicates(self):
        payload = self._customer_payload(
            'gid://shopify/Customer/1000', email='repeat@example.com',
        )
        result_1 = self.Importer._apply_import(self.store, payload)
        result_2 = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result_1, result_2)
        self.assertEqual(
            self.CustomerBinding.search_count([
                ('store_id', '=', self.store.id),
                ('shopify_gid', '=', 'gid://shopify/Customer/1000'),
            ]), 1,
        )
        self.assertEqual(
            self.env['res.partner'].search_count([
                ('email', '=', 'repeat@example.com'),
            ]), 1,
        )

    # ------------------------------------------------------------------
    # 2. Recall-safety duplicate-prevention proof: wrapped/display-name/
    # mixed-case email on an existing active partner never falls through
    # to create; the same coverage for an archived partner via the
    # archived-inclusive search.
    # ------------------------------------------------------------------

    def test_recall_safety_active_wrapped_email_never_falls_through_to_create(self):
        partner = self._make_partner(
            'Wrapped Jane', email='"Wrapped Jane" <Wrapped.JANE@Example.COM>',
        )
        partners_before = self.env['res.partner'].search_count([])
        payload = self._customer_payload(
            'gid://shopify/Customer/1001', email='wrapped.jane@example.com',
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result.partner_id, partner)
        self.assertEqual(
            self.env['res.partner'].search_count([]), partners_before,
        )

    def test_recall_safety_archived_wrapped_email_routes_duplicate_risk(self):
        partner = self._make_partner(
            'Archived Wrapped',
            email='"Archived Wrapped" <Archived.WRAPPED@Example.COM>',
        )
        partner.write({'active': False})
        partners_before = self.env['res.partner'].with_context(
            active_test=False
        ).search_count([])
        payload = self._customer_payload(
            'gid://shopify/Customer/1002', email='archived.wrapped@example.com',
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'duplicate_risk')
        self.assertEqual(
            self.env['res.partner'].with_context(active_test=False).search_count([]),
            partners_before,
        )
        self.assertFalse(self.CustomerBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Customer/1002'),
        ]))
        # Never un-archived.
        partner.invalidate_recordset()
        self.assertFalse(partner.active)
        detail = json.loads(ctx.exception.technical_detail)
        self.assertEqual(detail['candidates'][0]['active'], False)

    # ------------------------------------------------------------------
    # 3. Missing/empty email on the automated path -> no create;
    # blocked_manual_review / duplicate_risk.
    # ------------------------------------------------------------------

    def test_missing_email_no_create_duplicate_risk(self):
        partners_before = self.env['res.partner'].search_count([])
        payload = self._customer_payload(
            'gid://shopify/Customer/1003', email=None,
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'duplicate_risk')
        self.assertEqual(
            self.env['res.partner'].search_count([]), partners_before,
        )

    def test_empty_string_email_no_create_duplicate_risk(self):
        partners_before = self.env['res.partner'].search_count([])
        payload = self._customer_payload(
            'gid://shopify/Customer/1003b', email='',
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'duplicate_risk')
        self.assertEqual(
            self.env['res.partner'].search_count([]), partners_before,
        )

    # ------------------------------------------------------------------
    # 4. Archived-only email match -> no create, no bind, no un-archive;
    # duplicate_risk with "active": false candidate detail.
    # ------------------------------------------------------------------

    def test_archived_only_match_no_create_no_bind_no_unarchive(self):
        partner = self._make_partner(
            'Archived Simple', email='archived-simple@example.com',
        )
        partner.write({'active': False})
        payload = self._customer_payload(
            'gid://shopify/Customer/1004', email='archived-simple@example.com',
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'duplicate_risk')
        self.assertFalse(self.CustomerBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Customer/1004'),
        ]))
        partner.invalidate_recordset()
        self.assertFalse(partner.active)
        detail = json.loads(ctx.exception.technical_detail)
        self.assertEqual(detail['candidates'][0]['partner_id'], partner.id)
        self.assertEqual(detail['candidates'][0]['active'], False)

    # ------------------------------------------------------------------
    # 5. No settings flag/config combination bypasses any §8.1 rule.
    # ------------------------------------------------------------------

    def _importer_source(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'shopify_connector_customer_importer.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            return path, source_file.read()

    def test_source_level_no_bypass_flag_in_matching_logic(self):
        """Part A §I.5's no-bypass rule (restated, final prompt §8): no
        feature flag/setting/config combination may skip the pre-create
        duplicate check or the match-quality gate. Confirmed here at
        source level -- no bypass/force/skip identifier exists anywhere
        in the importer's matching/creation logic."""
        _path, content = self._importer_source()
        for forbidden in (
            'bypass', 'force_create', 'skip_gate', 'skip_duplicate',
            'ignore_duplicate', 'allow_blind',
        ):
            self.assertNotIn(forbidden, content.lower())

    # ------------------------------------------------------------------
    # 6. Uniqueness constraints hold as the backstop.
    # ------------------------------------------------------------------

    def test_direct_create_collisions_prove_uniqueness_backstop(self):
        partner_1 = self._make_partner('Uniq A')
        partner_2 = self._make_partner('Uniq B')
        self.CustomerBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/1005',
            'partner_id': partner_1.id,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.CustomerBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/1005',
                    'partner_id': partner_2.id,
                })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.CustomerBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/1006',
                    'partner_id': partner_1.id,
                })

    # ------------------------------------------------------------------
    # 7. The import produces zero order/product/inventory/fulfillment
    # side effects (no such model touched anywhere in the diff).
    # ------------------------------------------------------------------

    def test_source_level_no_order_product_inventory_fulfillment_models(self):
        models_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
        )
        forbidden_models = (
            'sale.order', 'product.template', 'product.product',
            'stock.quant', 'stock.picking', 'stock.move', 'stock.location',
            'account.move', 'account.payment', 'delivery.carrier',
        )
        for filename in (
            'shopify_connector_customer_binding.py',
            'shopify_connector_store_settings.py',
            'shopify_connector_customer_importer.py',
        ):
            path = os.path.join(models_dir, filename)
            with open(path, 'r', encoding='utf-8') as source_file:
                content = source_file.read()
            for forbidden in forbidden_models:
                self.assertNotIn(forbidden, content, (path, forbidden))

    def test_import_creates_exactly_one_partner_and_one_binding(self):
        partners_before = self.env['res.partner'].search_count([])
        bindings_before = self.CustomerBinding.search_count([])
        payload = self._customer_payload(
            'gid://shopify/Customer/1007', email='side-effect@example.com',
        )
        self.Importer._apply_import(self.store, payload)
        self.assertEqual(
            self.env['res.partner'].search_count([]), partners_before + 1,
        )
        self.assertEqual(
            self.CustomerBinding.search_count([]), bindings_before + 1,
        )
