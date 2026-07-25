import re

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.exceptions import UserError

from ..models.shopify_connector_order_importer import ORDER_HEADER_QUERY
from .test_order_import_mapping import OrderImportCase


class TestOrderCustomerResolution(OrderImportCase):

    def test_existing_customer_binding_has_priority_and_parent_is_unchanged(self):
        partner = self.env['res.partner'].create({
            'name': 'Bound Customer',
            'email': 'bound@example.invalid',
        })
        self.env['shopify.connector.customer.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/1200',
            'partner_id': partner.id,
            'match_key': 'manual',
        })
        payload = self._payload('gid://shopify/Order/ExistingCustomer')
        payload['customer'] = {
            'id': 'gid://shopify/Customer/1200',
            'firstName': 'Changed',
            'lastName': 'Name',
            'defaultEmailAddress': {
                'emailAddress': 'different@example.invalid',
            },
            'defaultPhoneNumber': {'phoneNumber': '+15550000000'},
        }
        before = partner.read(['name', 'email', 'phone'])[0]
        binding = self.Importer._apply_import(self.store, payload)
        self.assertEqual(binding.sale_order_id.partner_id, partner)
        self.assertEqual(binding.customer_resolution, 'existing_binding')
        self.assertEqual(partner.read(['name', 'email', 'phone'])[0], before)

    def test_embedded_customer_reuses_indexed_email_match(self):
        partner = self.env['res.partner'].create({
            'name': 'Indexed Customer',
            'email': 'indexed@example.invalid',
        })
        payload = self._payload('gid://shopify/Order/EmailCustomer')
        payload['customer'] = {
            'id': 'gid://shopify/Customer/1201',
            'firstName': 'Indexed',
            'lastName': 'Customer',
            'defaultEmailAddress': {
                'emailAddress': 'INDEXED@example.invalid',
            },
            'defaultPhoneNumber': None,
        }
        binding = self.Importer._apply_import(self.store, payload)
        self.assertEqual(binding.sale_order_id.partner_id, partner)
        self.assertEqual(binding.customer_resolution, 'email_match')
        customer_binding = self.env[
            'shopify.connector.customer.binding'
        ].search([('shopify_gid', '=', 'gid://shopify/Customer/1201')])
        self.assertEqual(customer_binding.partner_id, partner)

    def test_embedded_customer_confident_no_match_creates_person_binding(self):
        payload = self._payload('gid://shopify/Order/NewCustomer')
        payload['customer'] = {
            'id': 'gid://shopify/Customer/1202',
            'firstName': 'New',
            'lastName': 'Customer',
            'defaultEmailAddress': {
                'emailAddress': 'new-customer@example.invalid',
            },
            'defaultPhoneNumber': {'phoneNumber': '+15550000001'},
        }
        binding = self.Importer._apply_import(self.store, payload)
        partner = binding.sale_order_id.partner_id
        self.assertEqual(binding.customer_resolution, 'created')
        self.assertFalse(partner.is_company)
        self.assertEqual(partner.email, 'new-customer@example.invalid')
        self.assertEqual(self.env[
            'shopify.connector.customer.binding'
        ].search_count([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Customer/1202'),
        ]), 1)

    def test_guest_email_match_and_no_pii_fallback(self):
        guest = self.env['res.partner'].create({
            'name': 'Guest Match',
            'email': 'guest@example.invalid',
        })
        payload = self._payload('gid://shopify/Order/GuestMatch')
        payload['email'] = 'GUEST@example.invalid'
        binding = self.Importer._apply_import(self.store, payload)
        self.assertEqual(binding.sale_order_id.partner_id, guest)
        self.assertEqual(binding.customer_resolution, 'guest_email_match')

        fallback_payload = self._payload('gid://shopify/Order/Fallback')
        fallback = self.Importer._apply_import(self.store, fallback_payload)
        self.assertEqual(
            fallback.sale_order_id.partner_id, self.fallback_partner,
        )
        self.assertEqual(fallback.customer_resolution, 'fallback')
        self.assertEqual(fallback._pii_snapshot_fields(), ())

    def test_ambiguous_customer_holds_whole_order_and_redacts_evidence(self):
        for name in ('Ambiguous A', 'Ambiguous B'):
            self.env['res.partner'].create({
                'name': name,
                'email': 'ambiguous-order@example.invalid',
            })
        payload = self._payload('gid://shopify/Order/AmbiguousCustomer')
        payload['email'] = 'ambiguous-order@example.invalid'
        orders_before = self.env['sale.order'].search_count([])
        with self.assertRaises(JobHandlerError) as caught:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(caught.exception.error_class, 'ambiguous_match')
        self.assertNotIn(
            'ambiguous-order@example.invalid',
            caught.exception.technical_detail,
        )
        self.assertEqual(self.env['sale.order'].search_count([]), orders_before)
        self.assertFalse(self.Binding.search([
            ('shopify_gid', '=', payload['id']),
        ]))

    def test_customer_company_boundary_blocks_before_order_creation(self):
        other_company = self.env['res.company'].sudo().create({
            'name': 'Order Customer Other Company',
        })
        partner = self.env['res.partner'].sudo().create({
            'name': 'Other Company Customer',
            'company_id': other_company.id,
        })
        # SEC-3 (#197): this binding can no longer be CREATED through the ORM
        # -- a store belongs to exactly one company and Odoo's `_check_company`
        # refuses a foreign-company partner, under `sudo()` too. Assert that
        # first (it is the stronger, earlier protection), then plant the row
        # with SQL so the importer's own company boundary is still exercised
        # against a HISTORIC binding, which is the case it exists for.
        with self.assertRaises(UserError):
            with self.env.cr.savepoint():
                self.env['shopify.connector.customer.binding'].sudo().create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/OtherCompany',
                    'partner_id': partner.id,
                })
        self.env.cr.execute(
            "INSERT INTO shopify_connector_customer_binding "
            "(store_id, company_id, shopify_gid, partner_id, status, "
            " create_uid, create_date, write_uid, write_date) "
            "VALUES (%s, %s, 'gid://shopify/Customer/OtherCompany', %s, "
            "'active', 1, now(), 1, now())",
            (self.store.id, self.store.company_id.id, partner.id),
        )
        self.env['shopify.connector.customer.binding'].invalidate_model()
        payload = self._payload('gid://shopify/Order/OtherCompany')
        payload['customer'] = {
            'id': 'gid://shopify/Customer/OtherCompany',
            'firstName': 'Other', 'lastName': 'Company',
            'defaultEmailAddress': None,
            'defaultPhoneNumber': None,
        }
        orders_before = self.env['sale.order'].search_count([])
        with self.assertRaises(JobHandlerError) as caught:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(
            caught.exception.error_class, 'odoo_validation_configuration',
        )
        self.assertEqual(self.env['sale.order'].search_count([]), orders_before)

    def test_addresses_are_child_records_and_deduplicate_on_refresh_path(self):
        self.assertIsNone(re.search(
            r'billingAddress\s*\{[^}]*\bcompany\b',
            ORDER_HEADER_QUERY,
            flags=re.DOTALL,
        ))
        self.assertIsNone(re.search(
            r'shippingAddress\s*\{[^}]*\bcompany\b',
            ORDER_HEADER_QUERY,
            flags=re.DOTALL,
        ))
        payload = self._payload('gid://shopify/Order/Addresses')
        payload['email'] = 'address-guest@example.invalid'
        address = {
            'firstName': 'Address', 'lastName': 'Guest',
            'company': 'Example Co', 'address1': '1 Main Street',
            'address2': 'Suite 2', 'city': 'Dubai', 'zip': '00000',
            'provinceCode': None, 'countryCodeV2': 'AE',
            'phone': '+971500000000',
        }
        payload['billingAddress'] = dict(address)
        payload['shippingAddress'] = dict(address)
        company_partners_before = self.env['res.partner'].search_count([
            ('is_company', '=', True),
        ])
        binding = self.Importer._apply_import(self.store, payload)
        partner = binding.sale_order_id.partner_id
        parent_before = partner.read([
            'name', 'is_company', 'parent_id', 'company_name',
        ])[0]
        children = partner.child_ids.filtered(
            lambda child: child.type in ('invoice', 'delivery')
        )
        self.assertEqual(len(children), 2)
        self.assertEqual(set(children.mapped('type')), {'invoice', 'delivery'})
        self.assertTrue(all(child.parent_id == partner for child in children))
        self.assertTrue(all(not child.is_company for child in children))
        self.assertTrue(all(not child.company_name for child in children))
        self.assertEqual(
            self.env['res.partner'].search_count([('is_company', '=', True)]),
            company_partners_before,
        )
        self.assertFalse(partner.is_company)
        self.assertEqual(partner.name, 'Address Guest')
        same = self.Importer._apply_import(self.store, payload)
        self.assertEqual(same, binding)
        self.assertEqual(len(partner.child_ids.filtered(
            lambda child: child.type in ('invoice', 'delivery')
        )), 2)

        second = self._payload('gid://shopify/Order/AddressesAgain')
        second['email'] = payload['email']
        second_address = dict(address)
        second_address.update({
            'company': 'Changed display company',
            'phone': '+971599999999',
        })
        second['billingAddress'] = dict(second_address)
        second['shippingAddress'] = dict(second_address)
        second_binding = self.Importer._apply_import(self.store, second)
        self.assertEqual(second_binding.sale_order_id.partner_id, partner)
        self.assertEqual(len(partner.child_ids.filtered(
            lambda child: child.type in ('invoice', 'delivery')
        )), 2)
        self.assertEqual(partner.read([
            'name', 'is_company', 'parent_id', 'company_name',
        ])[0], parent_before)
        self.assertEqual(
            self.env['res.partner'].search_count([('is_company', '=', True)]),
            company_partners_before,
        )

    def test_abandoned_checkouts_never_enter_order_pipeline(self):
        self.assertNotIn('abandonedCheckout', ORDER_HEADER_QUERY)
        self.assertNotIn('checkout', ORDER_HEADER_QUERY.casefold())
        with self.assertRaises(JobHandlerError):
            self.Importer._extract_order({
                'data': {'checkout': {'id': 'gid://shopify/Checkout/1'}},
            }, 'gid://shopify/Order/NotACheckout')
