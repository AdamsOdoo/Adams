import json
import re
import uuid
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_customer_importer import CUSTOMER_IMPORT_QUERY


class TestCustomerImportMatching(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Customer Import Matching Test Store',
            'shop_domain': 'customer-import-matching-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.customer.importer']
        cls.CustomerBinding = cls.env['shopify.connector.customer.binding']
        cls.Job = cls.env['shopify.connector.job']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.Settings = cls.env['shopify.connector.store.settings']

    # ------------------------------------------------------------------
    # Fixtures.
    # ------------------------------------------------------------------

    def _customer_payload(
        self, gid, email=None, display_name=None, phone=None, address=None,
    ):
        return {
            'gid': gid, 'first_name': None, 'last_name': None,
            'display_name': display_name or gid, 'email': email,
            'phone': phone, 'address': address,
        }

    def _make_partner(self, name, email=None):
        vals = {'name': name}
        if email is not None:
            vals['email'] = email
        return self.env['res.partner'].create(vals)

    # ------------------------------------------------------------------
    # 1. Existing-binding match takes priority over email.
    # ------------------------------------------------------------------

    def test_existing_binding_takes_priority_over_email(self):
        partner = self._make_partner('Bound Partner', email='bound@example.com')
        binding = self.CustomerBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/900',
            'partner_id': partner.id,
            'match_key': 'manual',
        })
        # A different, unrelated partner coincidentally shares the
        # incoming email -- must NOT be used, since an existing binding
        # for this exact Shopify GID already resolves it.
        self._make_partner('Decoy Partner', email='decoy@example.com')

        payload = self._customer_payload(
            'gid://shopify/Customer/900', email='decoy@example.com',
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result, binding)
        self.assertEqual(result.partner_id, partner)

    # ------------------------------------------------------------------
    # 2. Exactly-one-active-email match binds with match_key='email'.
    # ------------------------------------------------------------------

    def test_email_match_binds_when_one_active_candidate(self):
        partner = self._make_partner('Jane', email='jane@example.com')
        payload = self._customer_payload(
            'gid://shopify/Customer/901', email='jane@example.com',
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result.partner_id, partner)
        self.assertEqual(result.match_key, 'email')

    # ------------------------------------------------------------------
    # 3. Case-folding: incoming Foo@BAR.com matches foo@bar.com.
    # ------------------------------------------------------------------

    def test_case_folding_email_match(self):
        partner = self._make_partner('Foo', email='foo@bar.com')
        payload = self._customer_payload(
            'gid://shopify/Customer/902', email='Foo@BAR.com',
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result.partner_id, partner)
        self.assertEqual(result.match_key, 'email')

    # ------------------------------------------------------------------
    # 4. Recall-safety: a display-name/wrapped, mixed-case partner email
    # is found and bound -- never missed, never a duplicate create.
    # ------------------------------------------------------------------

    def test_recall_safety_wrapped_display_name_email_matched(self):
        partner = self._make_partner(
            'Jane Doe', email='"Jane Doe" <Jane.DOE@Example.COM>',
        )
        partners_before = self.env['res.partner'].search_count([])
        payload = self._customer_payload(
            'gid://shopify/Customer/903', email='jane.doe@example.com',
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result.partner_id, partner)
        self.assertEqual(result.match_key, 'email')
        self.assertEqual(
            self.env['res.partner'].search_count([]), partners_before,
        )

    # ------------------------------------------------------------------
    # 5. Single candidate already bound to a different Customer GID in
    # this store -> binding_conflict, no new row.
    # ------------------------------------------------------------------

    def test_single_candidate_already_bound_routes_binding_conflict(self):
        partner = self._make_partner(
            'Already Bound', email='alreadybound@example.com',
        )
        self.CustomerBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/904',
            'partner_id': partner.id,
            'match_key': 'manual',
        })
        payload = self._customer_payload(
            'gid://shopify/Customer/905', email='alreadybound@example.com',
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'binding_conflict')
        self.assertFalse(self.CustomerBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Customer/905'),
        ]))

    # ------------------------------------------------------------------
    # 6. Ambiguous match -> no binding row; blocked_manual_review /
    # ambiguous_match; exact JSON payload; >20-candidates cap.
    # ------------------------------------------------------------------

    def test_ambiguous_match_never_creates_binding_row(self):
        self._make_partner('Dup A', email='dup@example.com')
        self._make_partner('Dup B', email='dup@example.com')
        partners_before = self.env['res.partner'].search_count([])
        payload = self._customer_payload(
            'gid://shopify/Customer/906', email='dup@example.com',
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'ambiguous_match')
        self.assertEqual(
            self.env['res.partner'].search_count([]), partners_before,
        )
        self.assertFalse(self.CustomerBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Customer/906'),
        ]))

        detail = json.loads(ctx.exception.technical_detail)
        self.assertEqual(
            set(detail.keys()),
            {
                'kind', 'shopify_customer_gid', 'incoming_email_normalized',
                'candidate_count', 'candidates',
            },
        )
        self.assertEqual(detail['kind'], 'customer_ambiguous_match_candidates')
        self.assertEqual(
            detail['shopify_customer_gid'], 'gid://shopify/Customer/906',
        )
        self.assertEqual(detail['candidate_count'], 2)
        self.assertEqual(len(detail['candidates']), 2)
        for candidate in detail['candidates']:
            self.assertEqual(
                set(candidate.keys()),
                {'partner_id', 'display_name', 'email', 'active'},
            )
            self.assertTrue(candidate['active'])
        # message is human-readable prose, never JSON.
        self.assertNotIn('{', ctx.exception.reason)

    def test_ambiguous_match_candidate_list_capped_at_20(self):
        for index in range(25):
            self._make_partner('Dup Cap %d' % index, email='dupcap@example.com')
        payload = self._customer_payload(
            'gid://shopify/Customer/907', email='dupcap@example.com',
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        detail = json.loads(ctx.exception.technical_detail)
        self.assertEqual(detail['candidate_count'], 25)
        self.assertEqual(len(detail['candidates']), 20)

    def test_ambiguous_match_routes_job_to_blocked_manual_review(self):
        """End-to-end: the dispatcher's existing, unmodified
        `_route_failure()` routes an importer-raised `ambiguous_match`
        `JobHandlerError` to `blocked_manual_review` with the matching
        `manual_review_subreason` -- no new routing logic in this
        module."""
        self._make_partner('Dup C', email='dupc@example.com')
        self._make_partner('Dup D', email='dupc@example.com')
        self.store.write({'state': 'connected'})
        self.Settings.create({
            'store_id': self.store.id, 'sale_domain_enabled': True,
        })
        job = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'customer_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': 'gid://shopify/Customer/908',
        })

        def fake_execute(self, store, query, variables=None):
            return {
                'data': {
                    'customer': {
                        'id': 'gid://shopify/Customer/908',
                        'firstName': 'Dup', 'lastName': 'C',
                        'displayName': 'Dup C',
                        'defaultEmailAddress': {
                            'emailAddress': 'dupc@example.com',
                        },
                        'defaultPhoneNumber': None,
                        'defaultAddress': None,
                        'updatedAt': '2026-07-10T00:00:00Z',
                    },
                },
            }

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'ambiguous_match')

    # ------------------------------------------------------------------
    # 7. Create path maps §8.3 address fields; unresolvable countryCodeV2
    # leaves country_id empty without failing; no child partner created.
    # ------------------------------------------------------------------

    def test_create_path_maps_address_fields(self):
        payload = self._customer_payload(
            'gid://shopify/Customer/909', email='new-customer@example.com',
            display_name='New Customer',
            address={
                'address1': '123 Main St', 'address2': 'Suite 4',
                'city': 'Springfield', 'zip': '12345',
                'province_code': 'IL', 'country_code': 'US',
            },
        )
        result = self.Importer._apply_import(self.store, payload)
        partner = result.partner_id
        self.assertEqual(partner.street, '123 Main St')
        self.assertEqual(partner.street2, 'Suite 4')
        self.assertEqual(partner.city, 'Springfield')
        self.assertEqual(partner.zip, '12345')
        self.assertEqual(partner.country_id.code, 'US')
        self.assertFalse(partner.child_ids)

    def test_create_path_unresolvable_country_leaves_field_empty(self):
        payload = self._customer_payload(
            'gid://shopify/Customer/910', email='unresolvable@example.com',
            address={
                'address1': '1 Nowhere Rd', 'address2': None,
                'city': 'Nowhere', 'zip': '00000',
                'province_code': 'ZZ', 'country_code': 'ZZ',
            },
        )
        result = self.Importer._apply_import(self.store, payload)
        partner = result.partner_id
        self.assertFalse(partner.country_id)
        self.assertFalse(partner.state_id)
        self.assertEqual(partner.street, '1 Nowhere Rd')

    def test_existing_matched_partner_address_never_written(self):
        partner = self._make_partner(
            'Existing No Overwrite', email='no-overwrite@example.com',
        )
        self.assertFalse(partner.street)
        payload = self._customer_payload(
            'gid://shopify/Customer/9091', email='no-overwrite@example.com',
            address={
                'address1': 'Should Not Be Written', 'address2': None,
                'city': 'Nowhere', 'zip': '00000',
                'province_code': None, 'country_code': None,
            },
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result.partner_id, partner)
        self.assertFalse(partner.street)

    # ------------------------------------------------------------------
    # 8. Created partner is a person; company string mapped nowhere.
    # ------------------------------------------------------------------

    def test_created_partner_is_person_even_with_raw_company_string(self):
        def fake_execute(self, store, query, variables=None):
            return {
                'data': {
                    'customer': {
                        'id': 'gid://shopify/Customer/912',
                        'firstName': 'Acme', 'lastName': 'Rep',
                        'displayName': 'Acme Rep',
                        'defaultEmailAddress': {
                            'emailAddress': 'acme-rep@example.com',
                        },
                        'defaultPhoneNumber': None,
                        'defaultAddress': {
                            'address1': '1 Biz Ave', 'address2': None,
                            'city': 'Bizville', 'zip': '11111',
                            'provinceCode': None, 'countryCodeV2': None,
                            'company': 'Acme Corp',
                        },
                        'updatedAt': '2026-07-10T00:00:00Z',
                    },
                },
            }

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            binding = self.Importer.import_customer_sync(
                self.store, 'gid://shopify/Customer/912',
            )
        partner = binding.partner_id
        self.assertFalse(partner.is_company)
        self.assertEqual(partner.company_type, 'person')
        self.assertFalse(partner.company_name)
        self.assertNotEqual(partner.name, 'Acme Corp')

    # ------------------------------------------------------------------
    # 9. Null defaultEmailAddress and null defaultAddress are tolerated.
    # ------------------------------------------------------------------

    def test_null_email_and_null_address_tolerated(self):
        def fake_execute(self, store, query, variables=None):
            return {
                'data': {
                    'customer': {
                        'id': 'gid://shopify/Customer/913',
                        'firstName': None, 'lastName': None,
                        'displayName': 'No Email Customer',
                        'defaultEmailAddress': None,
                        'defaultPhoneNumber': None,
                        'defaultAddress': None,
                        'updatedAt': '2026-07-10T00:00:00Z',
                    },
                },
            }

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_customer_sync(
                    self.store, 'gid://shopify/Customer/913',
                )
        # Tolerated, not a malformed-payload error -- routed through the
        # ordinary missing-email rule (5), never data_shape_schema_mismatch.
        self.assertEqual(ctx.exception.error_class, 'duplicate_risk')

    def test_null_address_with_valid_email_creates_without_address(self):
        payload = self._customer_payload(
            'gid://shopify/Customer/914', email='no-address@example.com',
            address=None,
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertTrue(result.partner_id.id)
        self.assertFalse(result.partner_id.street)

    # ------------------------------------------------------------------
    # 10. Sale-domain gating (mirrors Task 010).
    # ------------------------------------------------------------------

    def _make_job(self, job_source='scheduled_sync'):
        return self.Job.create({
            'store_id': self.store.id,
            'job_source': job_source,
            'job_type': 'customer_import_sync',
            'state': 'draft',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': 'gid://shopify/Customer/915',
        })

    def test_cannot_start_when_sale_domain_disabled(self):
        self.store.write({'state': 'connected'})
        self.Settings.create({
            'store_id': self.store.id, 'sale_domain_enabled': False,
        })
        job = self._make_job()
        with self.assertRaises(ValidationError):
            job.write({'state': 'running'})

    def test_cannot_start_when_settings_missing(self):
        self.store.write({'state': 'connected'})
        job = self._make_job()
        with self.assertRaises(ValidationError):
            job.write({'state': 'running'})

    def test_can_start_when_sale_domain_enabled(self):
        self.store.write({'state': 'connected'})
        self.Settings.create({
            'store_id': self.store.id, 'sale_domain_enabled': True,
        })
        job = self._make_job()
        job.write({'state': 'running'})
        self.assertEqual(job.state, 'running')

    def test_core_dispatch_selftest_still_dispatches_with_sale_installed(self):
        self.store.write({'state': 'connected'})
        job = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
        })
        self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')

    def test_domain_flag_unchanged_for_every_pre_existing_core_job_type(self):
        Job = self.Job
        for job_type in (
            'core_readiness_check', 'core_manual_maintenance',
            'core_test_connection', 'core_dispatch_selftest',
        ):
            self.assertIsNone(Job._domain_flag_for_job_type(job_type))
        self.assertEqual(
            Job._domain_flag_for_job_type('customer_import_sync'),
            'sale_domain_enabled',
        )

    # ------------------------------------------------------------------
    # 11. Zero-mutation proof.
    # ------------------------------------------------------------------

    def test_customer_import_query_is_never_a_mutation(self):
        self.assertTrue(CUSTOMER_IMPORT_QUERY.strip().startswith('query'))
        self.assertNotIn('mutation', CUSTOMER_IMPORT_QUERY.lower())

    def test_import_customer_sync_only_issues_read_query_calls(self):
        calls = []

        def fake_execute(self, store, query, variables=None):
            calls.append(query)
            return {
                'data': {
                    'customer': {
                        'id': 'gid://shopify/Customer/916',
                        'firstName': 'Fetched', 'lastName': 'Customer',
                        'displayName': 'Fetched Customer',
                        'defaultEmailAddress': {
                            'emailAddress': 'fetched@example.com',
                        },
                        'defaultPhoneNumber': None,
                        'defaultAddress': None,
                        'updatedAt': '2026-07-10T00:00:00Z',
                    },
                },
            }

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            result = self.Importer.import_customer_sync(
                self.store, 'gid://shopify/Customer/916',
            )
        self.assertTrue(calls)
        for query in calls:
            self.assertNotIn('mutation', query.lower())
        self.assertEqual(result.shopify_email_snapshot, 'fetched@example.com')

    def test_source_level_single_execute_call_uses_fixed_query_constant(self):
        """Confirms exactly one Shopify API-client call exists in the
        whole module, and it always passes the fixed
        `CUSTOMER_IMPORT_QUERY` constant -- never a dynamically-built or
        second operation string that could be a mutation."""
        path = self._importer_source_path()
        with open(path, 'r', encoding='utf-8') as source_file:
            content = source_file.read()
        self.assertEqual(content.count("api.client'].execute("), 1)
        self.assertIn('CUSTOMER_IMPORT_QUERY, variables=', content)

    # ------------------------------------------------------------------
    # 12. The importer requests only the §9 field list.
    # ------------------------------------------------------------------

    def test_customer_import_query_uses_only_non_deprecated_fields(self):
        self.assertIsNone(re.search(r'\bemail\b', CUSTOMER_IMPORT_QUERY))
        self.assertIsNone(re.search(r'\bphone\b', CUSTOMER_IMPORT_QUERY))
        self.assertIsNone(re.search(r'\baddresses\b', CUSTOMER_IMPORT_QUERY))
        for expected in (
            'id', 'firstName', 'lastName', 'displayName',
            'defaultEmailAddress', 'emailAddress',
            'defaultPhoneNumber', 'phoneNumber',
            'defaultAddress', 'address1', 'address2', 'city', 'zip',
            'provinceCode', 'countryCodeV2', 'updatedAt',
        ):
            self.assertIn(expected, CUSTOMER_IMPORT_QUERY)

    # ------------------------------------------------------------------
    # Helpers.
    # ------------------------------------------------------------------

    def _importer_source_path(self):
        import os
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'shopify_connector_customer_importer.py',
        )
