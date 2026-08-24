import ast
import json
import re
import uuid
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.shopify_connector_core.tools.api_version import (
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
)

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
    ShopifyQuiescedError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_customer_importer import CUSTOMER_IMPORT_QUERY

# A non-secret placeholder token. The transport is always the injected
# `_send` seam, so this value never reaches a network call; it exists only
# so the real `execute_business`/`_admit` admission gate can read a
# credential (CORE-R2 Slice 2B: the importer no longer stubs `execute`).
DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


class _FakeResponse:
    """Minimal stand-in for a `requests.Response` for the `_send()`
    transport-injection seam -- no network call is ever made. Mirrors the
    CORE-R2 core-test `FakeResponse` so `execute_business`'s
    `_normalize_response` runs exactly as it does in production, turning
    this `{'data': ...}` body into the normalized dict the importer's
    `_normalize_payload` consumes."""

    def __init__(self, status_code, json_body=None, headers=None):
        self.status_code = status_code
        # The API-version ruling (2026-07-26) makes `_normalize_response`
        # fail closed when the response carries no `X-Shopify-API-Version`
        # header, so a fake transport response has to state the version it
        # is pretending to have been served by -- exactly as a real one
        # does. An explicit `headers` argument still overrides this.
        self.headers = headers or {
            API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION,
        }
        self._json_body = json_body
        self.text = json.dumps(json_body) if json_body is not None else ''

    def json(self):
        return self._json_body


def _ok_send(json_body):
    """Build a fake `_send` returning a 200 `_FakeResponse(json_body)`.

    Replaces ONLY `_send` (never `execute_business`/`_admit`/lease): the
    real admission-gated context manager, the committed lease
    create/release, and `_normalize_response` all still run -- exactly the
    CORE-R2 Slice 2B seam (packet §5.2, "use the real execute_business gate
    + the _send transport-injection seam")."""

    def fake_send(self, store, body, token=None):
        return _FakeResponse(200, json_body=json_body)

    return fake_send


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
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
    # CORE-R2 Slice 2B seam helpers: the importer now issues its one
    # Shopify Admin call through the admission-gated `execute_business`
    # context manager, so the end-to-end tests need a connected,
    # credentialed store, a generation-matched job, and registry test mode
    # (so `_admit`'s independent side cursor can see the uncommitted
    # fixtures). Matching-only tests keep calling `_apply_import` directly
    # and are untouched by this.
    # ------------------------------------------------------------------

    def _connect_store_with_credential(self):
        self.env['shopify.connector.store.credential'].action_set_token(
            self.store, DUMMY_TOKEN,
        )
        # action_set_token demotes a connected store to `reconnect_needed`
        # and bumps the connection generation; re-assert `connected` so the
        # business admission gate passes (mirrors the CORE-R2
        # TestBusinessAdmission setup).
        self.store.write({'state': 'connected'})
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _make_business_job(self, gid):
        return self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'customer_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': gid,
            'expected_connection_generation':
                self.store.connection_generation,
        })

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
                'kind', 'shopify_customer_gid', 'incoming_email_sha256',
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
                {'partner_id', 'active'},
            )
            self.assertTrue(candidate['active'])
        self.assertNotIn('dup@example.com', ctx.exception.technical_detail)
        self.assertNotIn('Dup A', ctx.exception.technical_detail)
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
        self._connect_store_with_credential()
        self.Settings.create({
            'store_id': self.store.id, 'sale_domain_enabled': True,
        })
        job = self._make_business_job('gid://shopify/Customer/908')
        self.env.flush_all()

        body = {
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
        with patch.object(type(Client), '_send', _ok_send(body)):
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
        JobLog = self.env['shopify.connector.job.log']
        logs_before = JobLog.search_count([])
        payload = self._customer_payload(
            'gid://shopify/Customer/910', email='unresolvable@example.com',
            address={
                'address1': '1 Nowhere Rd', 'address2': None,
                'city': 'Nowhere', 'zip': '00000',
                'province_code': 'ZZ', 'country_code': 'ZZ',
            },
        )
        # Direct _apply_import(store, payload) call, no job context.
        result = self.Importer._apply_import(self.store, payload)
        partner = result.partner_id
        self.assertFalse(partner.country_id)
        self.assertFalse(partner.state_id)
        self.assertEqual(partner.street, '1 Nowhere Rd')
        # Import succeeds and requires no job context whatsoever; with
        # no job to log through, no job-log note is (or could be)
        # appended -- proves _apply_import(store, payload) remains
        # fully usable with zero job context.
        self.assertEqual(JobLog.search_count([]), logs_before)

    def test_create_path_unresolvable_state_leaves_field_empty(self):
        """Country resolves but the province/state code does not --
        state_id stays empty, country_id is still set, import
        succeeds."""
        payload = self._customer_payload(
            'gid://shopify/Customer/9102',
            email='unresolvable-state@example.com',
            address={
                'address1': '2 Somewhere Rd', 'address2': None,
                'city': 'Somewhere', 'zip': '00001',
                'province_code': 'ZZ', 'country_code': 'US',
            },
        )
        result = self.Importer._apply_import(self.store, payload)
        partner = result.partner_id
        self.assertTrue(partner.country_id)
        self.assertEqual(partner.country_id.code, 'US')
        self.assertFalse(partner.state_id)

    # ------------------------------------------------------------------
    # 7b. Unresolved country/state informational job-log note --
    # appended only through the dispatcher/job path (control-room
    # review comment 4934451381).
    # ------------------------------------------------------------------

    def test_unresolved_country_logs_informational_note_via_job_path(self):
        self._connect_store_with_credential()
        self.Settings.create({
            'store_id': self.store.id, 'sale_domain_enabled': True,
        })
        job = self._make_business_job('gid://shopify/Customer/920')
        self.env.flush_all()

        body = {
            'data': {
                'customer': {
                    'id': 'gid://shopify/Customer/920',
                    'firstName': 'Un', 'lastName': 'Resolved',
                    'displayName': 'Un Resolved',
                    'defaultEmailAddress': {
                        'emailAddress': 'unresolved-country@example.com',
                    },
                    'defaultPhoneNumber': {
                        'phoneNumber': '+15551234567',
                    },
                    'defaultAddress': {
                        'address1': '1 Test St', 'address2': None,
                        'city': 'Testville', 'zip': '99999',
                        'provinceCode': 'ZZ', 'countryCodeV2': 'ZZ',
                    },
                    'updatedAt': '2026-07-10T00:00:00Z',
                },
            },
        }

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), '_send', _ok_send(body)):
            self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')

        JobLog = self.env['shopify.connector.job.log']
        notes = JobLog.search([
            ('job_id', '=', job.id), ('event_type', '=', 'note'),
        ])
        self.assertEqual(len(notes), 1)
        note = notes[0]
        self.assertIn('country', note.message.lower())
        # Minimal and operator-safe: no phone, no full address, no
        # Shopify-bound sensitive data (email/phone/street/city) in the
        # human-readable message.
        self.assertNotIn('phone', note.message.lower())
        self.assertNotIn('+15551234567', note.message)
        self.assertNotIn('1 Test St', note.message)
        self.assertNotIn('Testville', note.message)
        self.assertNotIn('unresolved-country@example.com', note.message)
        self.assertEqual(note.technical_detail, 'country_code=ZZ')

    def test_unresolved_state_logs_informational_note_via_job_path(self):
        self._connect_store_with_credential()
        self.Settings.create({
            'store_id': self.store.id, 'sale_domain_enabled': True,
        })
        job = self._make_business_job('gid://shopify/Customer/921')
        self.env.flush_all()

        body = {
            'data': {
                'customer': {
                    'id': 'gid://shopify/Customer/921',
                    'firstName': 'State', 'lastName': 'Unresolved',
                    'displayName': 'State Unresolved',
                    'defaultEmailAddress': {
                        'emailAddress': 'unresolved-state@example.com',
                    },
                    'defaultPhoneNumber': None,
                    'defaultAddress': {
                        'address1': '2 Test Ave', 'address2': None,
                        'city': 'Testburg', 'zip': '88888',
                        'provinceCode': 'ZZ', 'countryCodeV2': 'US',
                    },
                    'updatedAt': '2026-07-10T00:00:00Z',
                },
            },
        }

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), '_send', _ok_send(body)):
            self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')

        JobLog = self.env['shopify.connector.job.log']
        notes = JobLog.search([
            ('job_id', '=', job.id), ('event_type', '=', 'note'),
        ])
        self.assertEqual(len(notes), 1)
        note = notes[0]
        self.assertIn('province', note.message.lower())
        self.assertNotIn('2 Test Ave', note.message)
        self.assertNotIn('Testburg', note.message)
        self.assertEqual(note.technical_detail, 'province_code=ZZ')

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
        self._connect_store_with_credential()
        job = self._make_business_job('gid://shopify/Customer/912')
        self.env.flush_all()
        body = {
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
        with patch.object(type(Client), '_send', _ok_send(body)):
            binding = self.Importer.import_customer_sync(
                self.store, 'gid://shopify/Customer/912', job=job,
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
        self._connect_store_with_credential()
        job = self._make_business_job('gid://shopify/Customer/913')
        self.env.flush_all()
        body = {
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
        with patch.object(type(Client), '_send', _ok_send(body)):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_customer_sync(
                    self.store, 'gid://shopify/Customer/913', job=job,
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
            'state': 'queued',
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

    def test_customer_import_sync_declared_remote_read_replay_safe(self):
        """DEC-031 Layer 1 (AR-048): `customer_import_sync` issues only a
        Shopify read (see `CUSTOMER_IMPORT_QUERY`) -- replaying it has no
        Shopify-side effect, so the domain extension declares it
        `remote_read_replay_safe`, never the conservative default."""
        policies = self.Dispatch._get_replay_policies()
        self.assertEqual(
            policies.get('customer_import_sync'), 'remote_read_replay_safe',
        )

    def test_installed_scope_every_handler_has_replay_policy(self):
        """DEC-031 Layer 1 (AR-048) completeness invariant, proven in the
        sale/customer-installed scope: every `job_type` the dispatcher can
        route (`_get_handlers()`) -- including the `customer_import_sync`
        handler this module contributes -- has an explicit entry in
        `_get_replay_policies()`. The fail-closed runtime lookup
        (`_get_replay_policy`) still defaults any undeclared `job_type`
        conservatively, but a handler this build actually registers must
        never silently rely on that default. The set difference must be
        empty; the failure message lists any missing handler keys."""
        handlers = set(self.Dispatch._get_handlers())
        policies = set(self.Dispatch._get_replay_policies())
        missing = handlers - policies
        self.assertEqual(
            missing, set(),
            'Every registered handler must declare an explicit replay '
            'policy; handler keys with no replay policy: %s' % sorted(missing),
        )

    # ------------------------------------------------------------------
    # 11. Zero-mutation proof.
    # ------------------------------------------------------------------

    def test_customer_import_query_is_never_a_mutation(self):
        self.assertTrue(CUSTOMER_IMPORT_QUERY.strip().startswith('query'))
        self.assertNotIn('mutation', CUSTOMER_IMPORT_QUERY.lower())

    def test_import_customer_sync_only_issues_read_query_calls(self):
        self._connect_store_with_credential()
        job = self._make_business_job('gid://shopify/Customer/916')
        self.env.flush_all()
        calls = []
        body = {
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

        def recording_send(self, store, req_body, token=None):
            calls.append(req_body.get('query'))
            return _FakeResponse(200, json_body=body)

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), '_send', recording_send):
            result = self.Importer.import_customer_sync(
                self.store, 'gid://shopify/Customer/916', job=job,
            )
        self.assertTrue(calls)
        for query in calls:
            self.assertNotIn('mutation', query.lower())
        self.assertEqual(result.shopify_email_snapshot, 'fetched@example.com')

    def test_source_level_single_execute_business_call_uses_fixed_query_constant(self):
        """CORE-R2 Slice 2B: the importer's single Shopify Admin business
        call now flows through the admission-gated `execute_business()`
        context manager -- never the legacy value-returning `execute()`.

        Confirms exactly one `execute_business` API-client call exists in
        the whole module, that no bare `execute(` call survives the
        migration, and that the one call still passes the fixed
        `CUSTOMER_IMPORT_QUERY` constant -- never a dynamically-built or
        second operation string that could be a mutation.

        Parses the source with `ast` (control-room review `4934627954`) so
        the property holds independent of whitespace/line-wrapping/argument
        formatting.
        """
        path = self._importer_source_path()
        with open(path, 'r', encoding='utf-8') as source_file:
            content = source_file.read()
        tree = ast.parse(content, filename=path)

        business_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'execute_business'
        ]
        legacy_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'execute'
        ]
        # 1. Exactly one execute_business() call exists, and the legacy
        # value-returning execute() call is gone.
        self.assertEqual(
            len(business_calls), 1,
            'exactly one Shopify API-client execute_business() call must '
            'exist in the importer module',
        )
        self.assertEqual(
            len(legacy_calls), 0,
            'the legacy value-returning execute() call must be gone after '
            'the CORE-R2 Slice 2B call-site migration',
        )
        call = business_calls[0]

        # 2. That one call uses the fixed CUSTOMER_IMPORT_QUERY
        # constant -- a plain Name reference among its arguments,
        # regardless of positional/keyword form or line placement.
        referenced_names = {
            arg.id for arg in call.args if isinstance(arg, ast.Name)
        } | {
            keyword.value.id for keyword in call.keywords
            if isinstance(keyword.value, ast.Name)
        }
        self.assertIn(
            'CUSTOMER_IMPORT_QUERY', referenced_names,
            'the execute_business() call must reference the fixed '
            'CUSTOMER_IMPORT_QUERY constant',
        )

        # 3. No dynamically-built query string or second operation
        # string is introduced -- no argument is a literal string
        # (other than via the named constant above), an f-string, or a
        # string concatenation/call result standing in for a query.
        for argument in list(call.args) + [kw.value for kw in call.keywords]:
            self.assertNotIsInstance(
                argument, ast.JoinedStr,
                'execute_business() must never receive a dynamically-built '
                '(f-string) query argument',
            )
            if isinstance(argument, ast.Constant) and isinstance(
                argument.value, str,
            ):
                self.fail(
                    'execute_business() must never receive a literal string '
                    'argument -- the query must always be the named '
                    'CUSTOMER_IMPORT_QUERY constant'
                )

        # 4. The referenced constant itself is still read-only -- a
        # query, never a mutation.
        self.assertTrue(CUSTOMER_IMPORT_QUERY.strip().startswith('query'))
        self.assertNotIn('mutation', CUSTOMER_IMPORT_QUERY.lower())

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


@tagged('post_install', '-at_install')
class TestCustomerCallsiteExecuteBusiness(TransactionCase):
    """CORE-R2 Slice 2B -- the customer importer's call-site migration to the
    admission-gated `execute_business()` lease (AR-047; packet §5.2 RD-C).

    These tests exercise the REAL production
    `execute_business`/`_admit`/`_release_lease` path with the `_send`
    transport-injection seam (no `execute`/lifecycle monkeypatch), proving:

      * the single lease covers transport -> normalization -> full
        reconciliation -> flush -> return, releasing only after
        reconciliation (§6 B);
      * `ShopifyClientError` still maps to the DEC-009 `JobHandlerError`,
        every failure path releases the lease exactly once, and a
        fail-closed `ShopifyQuiescedError` propagates uncaught with no
        transport and no leaked lease (§6 C);
      * source-level guards: no bare `execute(`, `execute_business` receives
        a real `job`, no explicit commit, no manual lease/transport access,
        and no `result` escapes the context (§6 A).

    No Task 011/011B matching behaviour is changed here; matching regression
    stays proven by `TestCustomerImportMatching` and the scalability suite.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Client = cls.env['shopify.connector.api.client']
        cls.Lease = cls.env['shopify.connector.call.lease']
        cls.Importer = cls.env['shopify.connector.customer.importer']
        cls.CustomerBinding = cls.env['shopify.connector.customer.binding']
        cls.Job = cls.env['shopify.connector.job']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Customer Callsite Store',
            'shop_domain': 'customer-callsite-%s.myshopify.com' % (
                uuid.uuid4().hex,
            ),
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN,
        )
        # action_set_token demotes connected -> reconnect_needed and bumps
        # the generation; re-assert connected for the admission gate.
        cls.store.write({'state': 'connected'})
        cls.env.flush_all()

    def setUp(self):
        super().setUp()
        # `_admit` opens its gate/lease insert on an independent
        # `registry.cursor()` side transaction; registry test mode makes it a
        # TestCursor sharing the single test connection so the uncommitted
        # fixtures and the committed lease are visible cross-cursor (the
        # sanctioned CORE-R2 TestBusinessAdmission mechanism).
        self.env.flush_all()
        self.registry_enter_test_mode()

    # ------------------------------------------------------------------
    # Fixtures / helpers.
    # ------------------------------------------------------------------

    def _job(self, gid, generation=None):
        return self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'customer_import_sync',
            'state': 'queued',
            'payload_hash': uuid.uuid4().hex,
            'shopify_target_gid': gid,
            'expected_connection_generation': (
                self.store.connection_generation
                if generation is None else generation
            ),
        })

    def _partner(self, name, email=None):
        vals = {'name': name}
        if email is not None:
            vals['email'] = email
        return self.env['res.partner'].create(vals)

    def _customer_body(self, gid, email=None, display_name=None):
        return {'data': {'customer': {
            'id': gid, 'firstName': None, 'lastName': None,
            'displayName': display_name or gid,
            'defaultEmailAddress': (
                {'emailAddress': email} if email else None
            ),
            'defaultPhoneNumber': None, 'defaultAddress': None,
            'updatedAt': '2026-07-12T00:00:00Z',
        }}}

    def _lease_count(self):
        return self.Lease.search_count([('store_id', '=', self.store.id)])

    def _release_spy(self):
        releases = []
        orig = type(self.Client)._release_lease

        def spy(client_self, lease_key):
            releases.append(lease_key)
            return orig(client_self, lease_key)

        return releases, spy

    def _counting_send(self, json_body=None):
        calls = []

        def spy(client_self, store, body, token=None):
            calls.append(1)
            return _FakeResponse(200, json_body=json_body or {
                'data': {'customer': None},
            })

        return calls, spy

    def _importer_source(self):
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'shopify_connector_customer_importer.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            return path, source_file.read()

    def _importer_ast(self):
        path, content = self._importer_source()
        return ast.parse(content, filename=path)

    def _find_func(self, tree, name):
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        return None

    # ==================================================================
    # A. Static guards.
    # ==================================================================

    def test_guard_no_bare_execute_call_remains(self):
        tree = self._importer_ast()
        bare = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'execute'
        ]
        self.assertEqual(
            bare, [],
            'no legacy value-returning api-client execute() call may remain '
            'in the customer importer after the Slice 2B migration',
        )

    def test_guard_execute_business_call_passes_real_job(self):
        tree = self._importer_ast()
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'execute_business'
        ]
        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertTrue(
            call.args,
            'execute_business must be called with job as its first '
            'positional argument',
        )
        first = call.args[0]
        self.assertIsInstance(first, ast.Name)
        self.assertEqual(
            first.id, 'job',
            'execute_business must receive the handler `job` (never a '
            'literal or None) as its admission credential',
        )

    def test_guard_no_explicit_commit(self):
        tree = self._importer_ast()
        commits = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'commit'
        ]
        self.assertEqual(
            commits, [],
            'the importer must not issue an explicit commit -- the lease '
            'contract ends at flush, and the outer transaction boundary '
            'commits',
        )

    def test_guard_no_manual_lease_or_transport_access(self):
        tree = self._importer_ast()
        forbidden = {
            '_admit', '_admit_lifecycle', '_release_lease', '_send',
            '_send_lifecycle',
        }
        called = {
            node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        self.assertFalse(
            called & forbidden,
            'the importer must not touch the private admission/lease/'
            'transport seam directly: %r' % (called & forbidden),
        )
        _path, content = self._importer_source()
        for token in ('shopify.connector.call.lease', 'lease_key'):
            self.assertNotIn(
                token, content,
                'the importer must not manually handle leases (%r)' % token,
            )

    def test_guard_result_never_escapes_execute_business_context(self):
        tree = self._importer_ast()
        fn = self._find_func(tree, 'import_customer_sync')
        self.assertIsNotNone(fn)
        target_with = None
        bound_name = None
        for node in ast.walk(fn):
            if not isinstance(node, ast.With):
                continue
            for item in node.items:
                ce = item.context_expr
                if (
                    isinstance(ce, ast.Call)
                    and isinstance(ce.func, ast.Attribute)
                    and ce.func.attr == 'execute_business'
                ):
                    target_with = node
                    self.assertIsNotNone(
                        item.optional_vars,
                        'execute_business must be entered as a context '
                        'manager with an `as` target',
                    )
                    self.assertIsInstance(item.optional_vars, ast.Name)
                    bound_name = item.optional_vars.id
        self.assertIsNotNone(
            target_with,
            'the importer must open an execute_business with-block',
        )
        within = {id(node) for node in ast.walk(target_with)}
        # Every load of the bound `result` name is inside the with-block.
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Name)
                and node.id == bound_name
                and isinstance(node.ctx, ast.Load)
            ):
                self.assertIn(
                    id(node), within,
                    'the execute_business result must not escape its context',
                )
        # Every return sits inside the with-block, so the value is
        # constructed and returned before the lease releases.
        for node in ast.walk(fn):
            if isinstance(node, ast.Return):
                self.assertIn(
                    id(node), within,
                    'import_customer_sync must return inside the '
                    'execute_business context (before the lease releases)',
                )

    # ==================================================================
    # B. Success -- one lease, held through reconciliation, released after.
    # ==================================================================

    def test_single_context_lease_through_reconciliation_and_release(self):
        gid = 'gid://shopify/Customer/cs-success-1'
        partner = self._partner('Solo Match', email='solo@callsite.example')
        job = self._job(gid)
        body = self._customer_body(
            gid, email='solo@callsite.example', display_name='Solo Match',
        )
        self.env.flush_all()

        send_lease_counts = []
        apply_lease_counts = []
        release_binding_present = []
        releases = []
        orig_release = type(self.Client)._release_lease
        orig_apply = type(self.Importer)._apply_import

        def spy_send(client_self, store, req_body, token=None):
            # The committed lease exists BEFORE the transport call.
            send_lease_counts.append(self._lease_count())
            return _FakeResponse(200, json_body=body)

        def spy_apply(imp_self, store, payload, job=False):
            # The lease is still held DURING the local reconciliation.
            apply_lease_counts.append(self._lease_count())
            return orig_apply(imp_self, store, payload, job=job)

        def spy_release(client_self, lease_key):
            # At release time (context exit, after reconciliation + flush)
            # the binding is already persisted.
            release_binding_present.append(self.CustomerBinding.search_count([
                ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
            ]))
            releases.append(lease_key)
            return orig_release(client_self, lease_key)

        with patch.object(type(self.Client), '_send', spy_send), \
                patch.object(type(self.Importer), '_apply_import', spy_apply), \
                patch.object(type(self.Client), '_release_lease', spy_release):
            result = self.Importer.import_customer_sync(
                self.store, gid, job=job,
            )

        # Return value is the (matched) binding.
        self.assertEqual(result._name, 'shopify.connector.customer.binding')
        self.assertEqual(result.partner_id, partner)
        self.assertEqual(result.match_key, 'email')
        # Exactly one context: one transport, one reconciliation, one release.
        self.assertEqual(len(send_lease_counts), 1)
        self.assertEqual(len(apply_lease_counts), 1)
        self.assertEqual(len(releases), 1)
        # Lease held before transport and through reconciliation.
        self.assertEqual(
            send_lease_counts[0], 1, 'lease must be held before the transport',
        )
        self.assertEqual(
            apply_lease_counts[0], 1, 'lease must be held through reconciliation',
        )
        # Reconciliation (and flush) completed before the lease released.
        self.assertEqual(
            release_binding_present[0], 1,
            'the binding must be materialized before the lease releases',
        )
        # Lease released after reconciliation.
        self.assertEqual(self._lease_count(), 0, 'lease must release after')

    # ==================================================================
    # C. Error behaviour -- classification, release-once, quiesced uncaught.
    # ==================================================================

    def test_shopify_client_error_maps_to_job_handler_error_releases_once(self):
        gid = 'gid://shopify/Customer/cs-401'
        job = self._job(gid)
        self.env.flush_all()
        releases, spy_release = self._release_spy()

        def auth_send(client_self, store, body, token=None):
            return _FakeResponse(401, json_body={'errors': [{'message': 'x'}]})

        with patch.object(type(self.Client), '_send', auth_send), \
                patch.object(type(self.Client), '_release_lease', spy_release):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_customer_sync(self.store, gid, job=job)
        # DEC-009 classification is preserved from the ShopifyClientError.
        self.assertEqual(
            ctx.exception.error_class, 'shopify_permission_scope_auth',
        )
        self.assertEqual(len(releases), 1, 'lease released exactly once')
        self.assertEqual(self._lease_count(), 0)

    def test_normalization_failure_releases_lease_once(self):
        gid = 'gid://shopify/Customer/cs-normfail'
        job = self._job(gid)
        body = self._customer_body(gid, email='n@callsite.example')
        self.env.flush_all()
        releases, spy_release = self._release_spy()

        def boom_normalize(imp_self, result):
            raise JobHandlerError(
                'data_shape_schema_mismatch', 'simulated normalize failure',
            )

        with patch.object(type(self.Client), '_send', _ok_send(body)), \
                patch.object(
                    type(self.Importer), '_normalize_payload', boom_normalize,
                ), \
                patch.object(type(self.Client), '_release_lease', spy_release):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_customer_sync(self.store, gid, job=job)
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(len(releases), 1, 'lease released exactly once')
        self.assertEqual(self._lease_count(), 0)

    def test_ambiguity_failure_releases_lease_once(self):
        gid = 'gid://shopify/Customer/cs-amb'
        self._partner('Amb One', email='amb@callsite.example')
        self._partner('Amb Two', email='amb@callsite.example')
        job = self._job(gid)
        body = self._customer_body(gid, email='amb@callsite.example')
        self.env.flush_all()
        releases, spy_release = self._release_spy()

        with patch.object(type(self.Client), '_send', _ok_send(body)), \
                patch.object(type(self.Client), '_release_lease', spy_release):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_customer_sync(self.store, gid, job=job)
        self.assertEqual(ctx.exception.error_class, 'ambiguous_match')
        self.assertEqual(len(releases), 1, 'lease released exactly once')
        self.assertEqual(self._lease_count(), 0)
        # No binding row was created on the blocked path.
        self.assertFalse(self.CustomerBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))

    def test_binding_conflict_failure_releases_lease_once(self):
        partner = self._partner('Bound Already', email='bc@callsite.example')
        self.CustomerBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/cs-bc-existing',
            'partner_id': partner.id,
            'match_key': 'manual',
        })
        gid = 'gid://shopify/Customer/cs-bc-new'
        job = self._job(gid)
        body = self._customer_body(gid, email='bc@callsite.example')
        self.env.flush_all()
        releases, spy_release = self._release_spy()

        with patch.object(type(self.Client), '_send', _ok_send(body)), \
                patch.object(type(self.Client), '_release_lease', spy_release):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_customer_sync(self.store, gid, job=job)
        self.assertEqual(ctx.exception.error_class, 'binding_conflict')
        self.assertEqual(len(releases), 1, 'lease released exactly once')
        self.assertEqual(self._lease_count(), 0)

    def test_partner_write_failure_releases_lease_once(self):
        gid = 'gid://shopify/Customer/cs-pwfail'
        job = self._job(gid)
        body = self._customer_body(gid, email='confident@callsite.example')
        self.env.flush_all()
        releases, spy_release = self._release_spy()

        def boom_create(imp_self, shopify_gid, payload, job=False):
            raise RuntimeError('simulated partner write failure')

        with patch.object(type(self.Client), '_send', _ok_send(body)), \
                patch.object(
                    type(self.Importer), '_create_partner', boom_create,
                ), \
                patch.object(type(self.Client), '_release_lease', spy_release):
            with self.assertRaises(RuntimeError):
                self.Importer.import_customer_sync(self.store, gid, job=job)
        self.assertEqual(len(releases), 1, 'lease released exactly once')
        self.assertEqual(self._lease_count(), 0)
        self.assertFalse(self.CustomerBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))

    def test_quiesced_error_propagates_uncaught_no_transport_no_lease(self):
        gid = 'gid://shopify/Customer/cs-quiesced'
        # Force a generation mismatch so _admit fails closed at admission.
        job = self._job(gid, generation=self.store.connection_generation + 7)
        self.env.flush_all()
        send_calls, spy_send = self._counting_send()
        releases, spy_release = self._release_spy()

        with patch.object(type(self.Client), '_send', spy_send), \
                patch.object(type(self.Client), '_release_lease', spy_release):
            with self.assertRaises(ShopifyQuiescedError):
                self.Importer.import_customer_sync(self.store, gid, job=job)
        # Fail-closed: no transport, no lease, no release, and NOT remapped
        # to a ShopifyClientError/JobHandlerError.
        self.assertEqual(send_calls, [], 'no Shopify call on a quiesced refusal')
        self.assertEqual(releases, [], 'no lease to release on a refusal')
        self.assertEqual(self._lease_count(), 0)

    def test_disconnected_store_fails_closed_uncaught_no_transport(self):
        gid = 'gid://shopify/Customer/cs-disc'
        job = self._job(gid)
        # A PRE-ADMISSION refusal (unit-level, registry test mode): the store is
        # not `connected` at admission, so _admit fails closed before any Shopify
        # call. This is NOT Race A -- it does not exercise the concurrent
        # action_disconnect vs admission ordering. The GENUINE independent-
        # connection Race A proof (a real action_disconnect racing a real
        # admission across distinct backends) is TestCustomerCallsiteRaceAGenuine
        # in test_customer_matching_scalability.py.
        self.store.write({'state': 'disconnected'})
        self.env.flush_all()
        send_calls, spy_send = self._counting_send()

        with patch.object(type(self.Client), '_send', spy_send):
            with self.assertRaises(ShopifyQuiescedError):
                self.Importer.import_customer_sync(self.store, gid, job=job)
        self.assertEqual(send_calls, [], 'no Shopify call on a fail-closed store')
        self.assertEqual(self._lease_count(), 0)
