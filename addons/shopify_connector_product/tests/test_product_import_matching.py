import contextlib
import logging
import queue
import threading
import uuid
from unittest.mock import patch

from odoo import SUPERUSER_ID, api
import odoo.service.model as service_model
from odoo.exceptions import ValidationError
from odoo.sql_db import db_connect
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
    ShopifyQuiescedError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_product_importer import PRODUCT_IMPORT_QUERY

# CORE-R2 Slice 2B: the product importer now issues every Shopify Admin page
# call through the core `execute_business` admission-lease context manager
# (`_send` transport seam), not the legacy value-returning `execute()`. The
# transport tests below drive the REAL admission gate; `DUMMY_TOKEN` is a
# non-secret test constant (never a live token) and no live Shopify request runs
# (`_send` is stubbed with the accepted Task 010B fixtures).
DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


class _FakeSendResponse:
    """Minimal `requests.Response` stand-in for the `_send` transport seam;
    `_normalize_response` reads `.status_code`, `.json()`, `.headers` and
    `.text` only, and the JSON body is the accepted Task 010B fixture dict, so
    `{'data': {...}}` normalizes to the exact result the legacy `execute()`
    returned."""

    def __init__(self, body, status_code=200, headers=None):
        self._body = body
        self.status_code = status_code
        self.headers = headers or {}
        self.text = ''

    def json(self):
        return self._body


class TestProductImportMatching(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Product Import Matching Test Store',
            'shop_domain': 'product-import-matching-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.product.importer']
        cls.TemplateBinding = cls.env['shopify.connector.product.template.binding']
        cls.VariantBinding = cls.env['shopify.connector.product.variant.binding']
        cls.Job = cls.env['shopify.connector.job']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.Settings = cls.env['shopify.connector.store.settings']
        # Seed a credential while the store is still `setup_incomplete`, so no
        # `connection_generation` bump occurs; the store stays at generation 0,
        # matching a directly-created job's default expected generation.
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN,
        )
        cls.env.flush_all()

    def setUp(self):
        super().setUp()
        # `execute_business._admit` runs its gate/lease on a `registry.cursor()`
        # side transaction; under a plain TransactionCase that cursor cannot see
        # this test's uncommitted fixture, so admission would fail closed.
        # Entering registry test mode makes every `registry.cursor()` reuse the
        # single test connection as a TestCursor (the sanctioned core-test
        # mechanism); it changes no production behaviour and is left on teardown.
        # This class runs no genuine separate-connection test, so class-wide test
        # mode is safe here.
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _import_job(self, shopify_target_gid):
        """Connect the store (the business-job create gate requires `connected`)
        and return a product-import job at generation 0 (matching the store), so
        `execute_business._admit` admits it. Flush so the admission side cursor
        observes the connected store and the job."""
        self.store.write({'state': 'connected'})
        job = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': shopify_target_gid,
        })
        self.env.flush_all()
        return job

    def _patch_send(self, fake_execute):
        """Route an accepted normalized-response `fake_execute(self, store,
        query, variables=None)` fixture through the real `execute_business`
        gate by patching only the `_send` transport seam. A `fake_execute` that
        raises `ShopifyClientError` propagates unchanged (the gate re-raises it;
        the importer maps it to `JobHandlerError`)."""
        Client = self.env['shopify.connector.api.client']

        def fake_send(client_self, store, body, token=None):
            body = body or {}
            outcome = fake_execute(
                client_self, store, body.get('query'), body.get('variables'),
            )
            return _FakeSendResponse(outcome)

        return patch.object(type(Client), '_send', fake_send)

    # ------------------------------------------------------------------
    # Fixtures.
    # ------------------------------------------------------------------

    def _make_product(self, name, default_code=None, barcode=None):
        template = self.env['product.template'].create({'name': name})
        variant = template.product_variant_id
        vals = {}
        if default_code:
            vals['default_code'] = default_code
        if barcode:
            vals['barcode'] = barcode
        if vals:
            variant.write(vals)
        return template, variant

    def _variant_payload(
        self, gid, sku=None, barcode=None, price=19.99,
        compare_at_price=None, option_values=None, image_url=None,
    ):
        return {
            'gid': gid, 'sku': sku, 'barcode': barcode, 'price': price,
            'compare_at_price': compare_at_price,
            'option_values': option_values, 'image_url': image_url,
        }

    def _product_payload(
        self, gid, variants, title='Test Product', status='active',
        image_url=None,
    ):
        return {
            'gid': gid, 'title': title, 'status': status,
            'image_url': image_url, 'variants': variants,
        }

    # ------------------------------------------------------------------
    # 1. Existing-binding match takes priority over SKU/barcode.
    # ------------------------------------------------------------------

    def test_existing_binding_takes_priority_over_sku_barcode(self):
        """Regression test (control-room review, comment 4927278355, fix
        1): the existing template binding resolves the template
        regardless of the decoy SKU, and -- since the payload carries
        exactly one variant and the bound template has exactly one,
        unbound Odoo variant -- the singleton-variant shortcut binds
        that Shopify variant directly, without SKU/barcode candidate
        search ever considering the (irrelevant) decoy match."""
        bound_template, bound_variant = self._make_product('Bound Product')
        template_binding = self.TemplateBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/900',
            'product_template_id': bound_template.id,
            'match_key': 'manual',
        })
        # A different, unbound product coincidentally shares the SKU the
        # incoming payload carries -- must NOT be used, since an existing
        # binding for this exact Shopify GID already resolves it.
        self._make_product('Decoy Product', default_code='SKU-DECOY')

        payload = self._product_payload(
            gid='gid://shopify/Product/900',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/900', sku='SKU-DECOY',
                ),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result['template_binding'], template_binding)
        self.assertEqual(
            result['template_binding'].product_template_id, bound_template,
        )
        self.assertEqual(len(result['variant_bindings']), 1)
        self.assertEqual(
            result['variant_bindings'].product_variant_id, bound_variant,
        )
        self.assertEqual(
            result['variant_bindings'].shopify_gid,
            'gid://shopify/ProductVariant/900',
        )
        # The singleton shortcut never ran SKU/barcode candidate search
        # -- match_key stays unset, exactly like the auto-created-
        # singleton case.
        self.assertFalse(result['variant_bindings'].match_key)

    def test_existing_template_singleton_variant_already_bound_blocks_safely(self):
        """Existing template binding + one Shopify variant, but the
        template's singleton Odoo variant is already bound to a
        *different* Shopify variant for this store -- must block,
        classified, never silently rebind or guess."""
        template, variant = self._make_product('Already Bound Singleton')
        template_binding = self.TemplateBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/990',
            'product_template_id': template.id,
            'match_key': 'manual',
        })
        self.VariantBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/other-990',
            'product_variant_id': variant.id,
            'product_template_binding_id': template_binding.id,
            'match_key': 'manual',
        })
        payload = self._product_payload(
            gid='gid://shopify/Product/990',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/990', sku='SKU-990-UNMATCHED',
                ),
            ],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'duplicate_risk')
        self.assertFalse(self.VariantBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/ProductVariant/990'),
        ]))
        # The pre-existing binding to the other Shopify variant is
        # completely untouched.
        self.assertEqual(
            self.VariantBinding.search_count([
                ('store_id', '=', self.store.id),
                ('product_variant_id', '=', variant.id),
            ]), 1,
        )

    def test_existing_template_multi_variant_payload_still_conservative_and_atomic(self):
        """Existing template binding + multiple Shopify variants must
        NOT take the singleton shortcut for any variant (even the one
        whose SKU legitimately matches) -- an unmatched later variant
        still blocks the whole import, and the savepoint still rolls
        back the would-be-successful earlier variant too."""
        template, variant = self._make_product(
            'Existing Multi Variant Template', default_code='SKU-991-MATCH',
        )
        template_binding = self.TemplateBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/991',
            'product_template_id': template.id,
            'match_key': 'manual',
        })
        payload = self._product_payload(
            gid='gid://shopify/Product/991',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/991a', sku='SKU-991-MATCH',
                ),
                self._variant_payload(
                    'gid://shopify/ProductVariant/991b',
                    sku='SKU-991-NO-MATCH',
                ),
            ],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'duplicate_risk')
        # Atomic: variant 991a's would-be-successful SKU match must not
        # persist once variant 991b fails.
        self.assertFalse(self.VariantBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', 'in', [
                'gid://shopify/ProductVariant/991a',
                'gid://shopify/ProductVariant/991b',
            ]),
        ]))
        self.assertEqual(
            self.TemplateBinding.search([
                ('store_id', '=', self.store.id),
                ('shopify_gid', '=', 'gid://shopify/Product/991'),
            ]),
            template_binding,
        )

    # ------------------------------------------------------------------
    # 2. SKU match when no existing binding.
    # ------------------------------------------------------------------

    def test_sku_match_when_no_existing_binding(self):
        """Regression test (control-room review, comment 4927455927, fix
        1): the template here has exactly one product.product variant
        and the payload carries exactly one variant -- the same shape
        the existing-binding singleton shortcut uses -- but this
        template is resolved via SKU candidate match, not an existing
        binding, so the shortcut must NOT apply and the variant's own
        match_key must still come from _find_variant_candidates()."""
        template, variant = self._make_product('SKU Product', default_code='SKU-42')
        payload = self._product_payload(
            gid='gid://shopify/Product/901',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/901', sku='SKU-42',
                ),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result['template_binding'].product_template_id, template)
        self.assertEqual(result['template_binding'].match_key, 'sku_reference')
        self.assertEqual(result['variant_bindings'].product_variant_id, variant)
        self.assertEqual(result['variant_bindings'].match_key, 'sku_reference')

    # ------------------------------------------------------------------
    # 3. Barcode match when no SKU match.
    # ------------------------------------------------------------------

    def test_barcode_match_when_no_sku_match(self):
        """Regression test (control-room review, comment 4927455927, fix
        1): same singleton template/payload shape as
        test_sku_match_when_no_existing_binding above, but for the
        barcode candidate-match path -- must not take the
        existing-binding singleton shortcut either."""
        template, variant = self._make_product(
            'Barcode Product', barcode='0123456789012',
        )
        payload = self._product_payload(
            gid='gid://shopify/Product/902',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/902',
                    barcode='0123456789012',
                ),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result['template_binding'].product_template_id, template)
        self.assertEqual(result['template_binding'].match_key, 'barcode')
        self.assertEqual(result['variant_bindings'].product_variant_id, variant)
        self.assertEqual(result['variant_bindings'].match_key, 'barcode')

    # ------------------------------------------------------------------
    # 4. Ambiguous match -> review / ambiguous_match / blocked_manual_
    # review -- never creates.
    # ------------------------------------------------------------------

    def test_ambiguous_match_never_creates(self):
        self._make_product('Dup Product A', default_code='DUP-1')
        self._make_product('Dup Product B', default_code='DUP-1')
        templates_before = self.env['product.template'].search_count([])
        payload = self._product_payload(
            gid='gid://shopify/Product/903',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/903', sku='DUP-1',
                ),
            ],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'ambiguous_match')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Product/903'),
        ]))

    def test_ambiguous_match_routes_job_to_blocked_manual_review(self):
        """End-to-end: the dispatcher's existing, unmodified
        `_route_failure()` routes an importer-raised `ambiguous_match`
        `JobHandlerError` to `blocked_manual_review` with the matching
        `manual_review_subreason` -- no new routing logic in this
        module."""
        self._make_product('Dup Product C', default_code='DUP-2')
        self._make_product('Dup Product D', default_code='DUP-2')
        self.store.write({'state': 'connected'})
        self.Settings.create({
            'store_id': self.store.id, 'product_domain_enabled': True,
        })
        job = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': 'gid://shopify/Product/904',
        })

        def fake_execute(self, store, query, variables=None):
            return {
                'data': {
                    'product': {
                        'id': 'gid://shopify/Product/904',
                        'title': 'Ambiguous Product',
                        'status': 'ACTIVE',
                        'featuredImage': None,
                        'variants': {
                            'nodes': [{
                                'id': 'gid://shopify/ProductVariant/904',
                                'sku': 'DUP-2', 'barcode': None,
                                'price': None, 'compareAtPrice': None,
                                'selectedOptions': [], 'image': None,
                            }],
                            'pageInfo': {'hasNextPage': False, 'endCursor': None},
                        },
                    },
                },
            }

        # Flush so the admission side cursor sees the connected store + job.
        self.env.flush_all()
        with self._patch_send(fake_execute):
            self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'ambiguous_match')

    # ------------------------------------------------------------------
    # 5. Import creates and binds both template and variant, populating
    # product_template_binding_id correctly.
    # ------------------------------------------------------------------

    def test_import_creates_and_binds_template_and_variant(self):
        payload = self._product_payload(
            gid='gid://shopify/Product/905', title='New Product',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/905', sku='NEW-SKU-1',
                ),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        template_binding = result['template_binding']
        variant_bindings = result['variant_bindings']
        self.assertTrue(template_binding.product_template_id)
        self.assertEqual(len(variant_bindings), 1)
        self.assertEqual(
            variant_bindings.product_template_binding_id, template_binding,
        )
        self.assertEqual(
            variant_bindings.product_variant_id,
            template_binding.product_template_id.product_variant_id,
        )

    # ------------------------------------------------------------------
    # 6. Template GID and variant GID are never conflated.
    # ------------------------------------------------------------------

    def test_template_and_variant_gids_never_conflated(self):
        payload = self._product_payload(
            gid='gid://shopify/Product/906',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/906', sku='SKU-906',
                ),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(
            result['template_binding'].shopify_gid, 'gid://shopify/Product/906',
        )
        self.assertEqual(
            result['variant_bindings'].shopify_gid,
            'gid://shopify/ProductVariant/906',
        )
        self.assertNotEqual(
            result['template_binding'].shopify_gid,
            result['variant_bindings'].shopify_gid,
        )

    # ------------------------------------------------------------------
    # 7. The importer constructs zero Shopify mutation calls.
    # ------------------------------------------------------------------

    def test_product_import_query_is_never_a_mutation(self):
        self.assertTrue(
            PRODUCT_IMPORT_QUERY.strip().startswith('query')
        )
        self.assertNotIn('mutation', PRODUCT_IMPORT_QUERY.lower())

    def test_import_product_sync_only_issues_read_query_calls(self):
        calls = []

        def fake_execute(self, store, query, variables=None):
            calls.append(query)
            return {
                'data': {
                    'product': {
                        'id': 'gid://shopify/Product/907',
                        'title': 'Fetched Product', 'status': 'ACTIVE',
                        'featuredImage': None,
                        'variants': {
                            'nodes': [{
                                'id': 'gid://shopify/ProductVariant/907',
                                'sku': 'SKU-907', 'barcode': None,
                                'price': 9.99, 'compareAtPrice': None,
                                'selectedOptions': [
                                    {'name': 'Size', 'value': 'M'},
                                ],
                                'image': None,
                            }],
                            'pageInfo': {'hasNextPage': False, 'endCursor': None},
                        },
                    },
                },
            }

        gid = 'gid://shopify/Product/907'
        with self._patch_send(fake_execute):
            result = self.Importer.import_product_sync(
                self.store, gid, job=self._import_job(gid),
            )
        self.assertTrue(calls)
        for query in calls:
            self.assertNotIn('mutation', query.lower())
        self.assertEqual(
            result['template_binding'].shopify_gid, 'gid://shopify/Product/907',
        )
        self.assertEqual(
            result['variant_bindings'].shopify_option_values, 'Size: M',
        )

    # ------------------------------------------------------------------
    # 8. Product-domain gating.
    # ------------------------------------------------------------------

    def _make_job(self, job_source='scheduled_sync'):
        return self.Job.create({
            'store_id': self.store.id,
            'job_source': job_source,
            'job_type': 'product_import_sync',
            'state': 'draft',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': 'gid://shopify/Product/908',
        })

    def test_cannot_start_when_product_domain_disabled(self):
        self.store.write({'state': 'connected'})
        self.Settings.create({
            'store_id': self.store.id, 'product_domain_enabled': False,
        })
        job = self._make_job()
        with self.assertRaises(ValidationError):
            job.write({'state': 'running'})

    def test_cannot_start_when_settings_missing(self):
        self.store.write({'state': 'connected'})
        job = self._make_job()
        with self.assertRaises(ValidationError):
            job.write({'state': 'running'})

    def test_can_start_when_product_domain_enabled(self):
        self.store.write({'state': 'connected'})
        self.Settings.create({
            'store_id': self.store.id, 'product_domain_enabled': True,
        })
        job = self._make_job()
        job.write({'state': 'running'})
        self.assertEqual(job.state, 'running')

    def test_core_dispatch_selftest_still_dispatches_with_product_installed(self):
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
            Job._domain_flag_for_job_type('product_import_sync'),
            'product_domain_enabled',
        )

    def test_product_import_sync_declared_remote_read_replay_safe(self):
        """DEC-031 Layer 1 (AR-048): `product_import_sync` issues only a
        Shopify read (see `PRODUCT_IMPORT_QUERY`) -- replaying it has no
        Shopify-side effect, so the domain extension declares it
        `remote_read_replay_safe`, never the conservative default."""
        policies = self.Dispatch._get_replay_policies()
        self.assertEqual(
            policies.get('product_import_sync'), 'remote_read_replay_safe',
        )

    # ------------------------------------------------------------------
    # 9. Shopify API client error taxonomy preserved (control-room
    # review, comment 4927037139, fix 1) -- a ShopifyClientError raised
    # by execute() must keep its accepted DEC-009 error_class through
    # the dispatcher's own, unmodified _route_failure() routing, never
    # falling through to unknown_system_error.
    # ------------------------------------------------------------------

    def _make_client_error_job(self, shopify_target_gid):
        self.store.write({'state': 'connected'})
        self.Settings.create({
            'store_id': self.store.id, 'product_domain_enabled': True,
        })
        return self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': shopify_target_gid,
        })

    def test_shopify_client_error_throttling_preserved_not_unknown(self):
        job = self._make_client_error_job('gid://shopify/Product/960')

        def fake_execute(self, store, query, variables=None):
            raise ShopifyClientError(
                'shopify_throttling_rate_limit',
                'Shopify is asking us to slow down — try again shortly.',
            )

        # Flush so the admission side cursor sees the connected store + job.
        self.env.flush_all()
        with self._patch_send(fake_execute):
            self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        self.assertEqual(job.error_class, 'shopify_throttling_rate_limit')
        self.assertNotEqual(job.error_class, 'unknown_system_error')
        # DEC-009: throttling is auto-retryable -- a fresh job's first
        # failure schedules a retry rather than terminating immediately.
        self.assertEqual(job.state, 'retry_waiting')

    def test_shopify_client_error_temporary_network_preserved_not_unknown(self):
        job = self._make_client_error_job('gid://shopify/Product/961')

        def fake_execute(self, store, query, variables=None):
            raise ShopifyClientError(
                'shopify_temporary_server_network',
                'Shopify could not be reached right now — this is '
                'usually temporary.',
            )

        # Flush so the admission side cursor sees the connected store + job.
        self.env.flush_all()
        with self._patch_send(fake_execute):
            self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        self.assertEqual(job.error_class, 'shopify_temporary_server_network')
        self.assertNotEqual(job.error_class, 'unknown_system_error')
        self.assertEqual(job.state, 'retry_waiting')

    def test_shopify_client_error_permission_scope_auth_preserved_not_unknown(self):
        job = self._make_client_error_job('gid://shopify/Product/962')

        def fake_execute(self, store, query, variables=None):
            raise ShopifyClientError(
                'shopify_permission_scope_auth',
                'Your access token appears invalid or was revoked — '
                'replace it.',
                credential_invalid=True,
            )

        # Flush so the admission side cursor sees the connected store + job.
        self.env.flush_all()
        with self._patch_send(fake_execute):
            self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        self.assertEqual(job.error_class, 'shopify_permission_scope_auth')
        self.assertNotEqual(job.error_class, 'unknown_system_error')
        # DEC-009: permission/scope/auth is "manual fix then retry" --
        # never auto-retried.
        self.assertEqual(job.state, 'failed_retryable')

    def test_shopify_client_error_never_calls_execute_a_second_time(self):
        """The importer re-raises immediately as JobHandlerError -- it
        does not itself retry the Shopify call (retry policy belongs to
        the job layer, per shopify_connector_api_client.py's own
        docstring)."""
        calls = []

        def fake_execute(self, store, query, variables=None):
            calls.append(1)
            raise ShopifyClientError(
                'shopify_throttling_rate_limit', 'Slow down.',
            )

        gid = 'gid://shopify/Product/963'
        with self._patch_send(fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(
                    self.store, gid, job=self._import_job(gid),
                )
        self.assertEqual(ctx.exception.error_class, 'shopify_throttling_rate_limit')
        self.assertEqual(len(calls), 1)

    # ------------------------------------------------------------------
    # 10. Malformed payloads are validated explicitly, before any write
    # (control-room review, comment 4927037139, fix 3).
    # ------------------------------------------------------------------

    def test_malformed_payload_missing_product_node_blocked(self):
        templates_before = self.env['product.template'].search_count([])
        payload = {
            'gid': None, 'title': None, 'status': None,
            'image_url': None, 'variants': [],
        }
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )

    def test_malformed_payload_missing_product_node_blocked_end_to_end(self):
        """Same case, exercised through the real import_product_sync()
        entry point against a GraphQL response with no `product` node at
        all -- not just the lower-level _apply_import() unit test
        above."""
        def fake_execute(self, store, query, variables=None):
            return {'data': {'product': None}}

        gid = 'gid://shopify/Product/970'
        with self._patch_send(fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(
                    self.store, gid, job=self._import_job(gid),
                )
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')

    def test_malformed_payload_missing_product_gid_blocked(self):
        payload = self._product_payload(
            gid=None,
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/971', sku='SKU-971',
                ),
            ],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')

    def test_malformed_payload_missing_variant_gid_blocked(self):
        templates_before = self.env['product.template'].search_count([])
        payload = self._product_payload(
            gid='gid://shopify/Product/972',
            variants=[self._variant_payload(None, sku='SKU-972')],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Product/972'),
        ]))

    def test_malformed_payload_unexpected_status_blocked(self):
        templates_before = self.env['product.template'].search_count([])
        payload = self._product_payload(
            gid='gid://shopify/Product/973', status='some_unexpected_status',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/973', sku='SKU-973',
                ),
            ],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )

    def test_well_formed_status_values_pass_validation(self):
        """All four accepted statuses must pass payload validation -- a
        regression guard against over-tightening. (An archived product then
        follows its own D-010B-8 path; that is asserted in the refresh/stale
        suite, not here.)"""
        for status in ('active', 'archived', 'draft', 'unlisted'):
            payload = self._product_payload(
                gid='gid://shopify/Product/974-%s' % status, status=status,
                variants=[
                    self._variant_payload(
                        'gid://shopify/ProductVariant/974-%s' % status,
                        sku='SKU-VAL-%s' % status,
                    ),
                ],
            )
            # Does not raise data_shape_schema_mismatch for a valid status.
            self.Importer._validate_payload(payload)

    def test_non_archived_statuses_import_and_snapshot_status(self):
        """A first-seen active/draft/unlisted product imports and snapshots
        its Shopify status. (Archived is excluded: a first-seen archived
        product creates no Odoo master data -- see D-010B-8.)"""
        for index, status in enumerate(('active', 'draft', 'unlisted')):
            payload = self._product_payload(
                gid='gid://shopify/Product/97%d' % (4 + index),
                status=status,
                variants=[
                    self._variant_payload(
                        'gid://shopify/ProductVariant/97%d' % (4 + index),
                        sku='SKU-STATUS-%d' % index,
                    ),
                ],
            )
            result = self.Importer._apply_import(self.store, payload)
            self.assertEqual(result['template_binding'].shopify_status, status)

    # ------------------------------------------------------------------
    # 11. Variant pagination (D-010B-1). The former >100-variant
    # truncation-blocking tests are now pagination tests: multi-page
    # payloads import completely, and only genuinely malformed pagination
    # (malformed pageInfo, missing endCursor, over-ceiling) is blocked.
    # ------------------------------------------------------------------

    def test_product_import_query_requests_page_info(self):
        self.assertIn('pageInfo', PRODUCT_IMPORT_QUERY)
        self.assertIn('hasNextPage', PRODUCT_IMPORT_QUERY)
        self.assertIn('endCursor', PRODUCT_IMPORT_QUERY)
        # first: is always explicit (no documented default page size).
        self.assertIn('first: 100', PRODUCT_IMPORT_QUERY)
        self.assertIn('$cursor', PRODUCT_IMPORT_QUERY)

    def _single_option_pages(self, product_gid, total, page_size=100):
        """Build paged GraphQL responses for a one-option, `total`-variant
        product (option 'SC010B Paged Edition' with values E0..E{total-1})."""
        option_values = [{'id': 'ov-%d' % i, 'name': 'E%d' % i} for i in range(total)]
        nodes = [
            {
                'id': '%s/variant/%d' % (product_gid, i),
                'sku': 'PAGED-%s-%d' % (product_gid.split('/')[-1], i),
                'barcode': None, 'price': '10.00', 'compareAtPrice': None,
                'selectedOptions': [{'name': 'SC010B Paged Edition', 'value': 'E%d' % i}],
                'image': None, 'inventoryItem': {'id': 'ii-%d' % i},
            }
            for i in range(total)
        ]
        pages = []
        for start in range(0, total, page_size):
            chunk = nodes[start:start + page_size]
            has_next = (start + page_size) < total
            end_cursor = 'cursor-%d' % (start // page_size) if has_next else None
            pages.append((chunk, has_next, end_cursor))
        return option_values, pages

    def _paginated_execute(self, product_gid, title, option_values, pages):
        def fake_execute(client_self, store, query, variables=None):
            cursor = (variables or {}).get('cursor')
            index = 0 if cursor is None else int(cursor.split('-')[1]) + 1
            nodes, has_next, end_cursor = pages[index]
            return {
                'data': {
                    'product': {
                        'id': product_gid, 'title': title, 'status': 'ACTIVE',
                        'descriptionHtml': '', 'vendor': '', 'productType': '',
                        'tags': [], 'updatedAt': '2026-07-11T00:00:00Z',
                        'featuredImage': None,
                        'options': [{
                            'id': 'opt-1', 'name': 'SC010B Paged Edition', 'position': 1,
                            'optionValues': option_values,
                        }],
                        'variants': {
                            'nodes': nodes,
                            'pageInfo': {
                                'hasNextPage': has_next, 'endCursor': end_cursor,
                            },
                        },
                    },
                },
            }
        return fake_execute

    def test_two_hundred_fifty_variants_across_pages_import_completely(self):
        """A 250-variant product spanning three variant pages
        (100+100+50) imports every variant -- none truncated."""
        gid = 'gid://shopify/Product/1250'
        option_values, pages = self._single_option_pages(gid, 250)
        self.assertEqual(len(pages), 3)
        fake_execute = self._paginated_execute(gid, 'Paged 250', option_values, pages)
        with self._patch_send(fake_execute):
            result = self.Importer.import_product_sync(self.store, gid, job=self._import_job(gid))
        self.assertEqual(len(result['variant_bindings']), 250)
        self.assertEqual(
            self.VariantBinding.search_count([
                ('product_template_binding_id', '=', result['template_binding'].id),
            ]), 250,
        )
        # Odoo instantiated exactly the 250 Shopify variants -- no more.
        self.assertEqual(
            len(result['template_binding'].product_template_id.product_variant_ids),
            250,
        )

    def test_missing_end_cursor_with_has_next_page_blocked(self):
        gid = 'gid://shopify/Product/1251'
        pages = [
            ([{
                'id': '%s/variant/0' % gid, 'sku': 'MEC-0', 'barcode': None,
                'price': '10.00', 'compareAtPrice': None,
                'selectedOptions': [{'name': 'SC010B Paged Edition', 'value': 'E0'}],
                'image': None, 'inventoryItem': None,
            }], True, None),  # hasNextPage True but endCursor None
        ]
        fake_execute = self._paginated_execute(
            gid, 'Bad Cursor', [{'id': 'ov0', 'name': 'E0'}], pages,
        )
        templates_before = self.env['product.template'].search_count([])
        with self._patch_send(fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid, job=self._import_job(gid))
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )

    # ------------------------------------------------------------------
    # Strict pagination-shape validation (review 4950202231 item 1): a
    # missing/null/wrong-type variants.pageInfo is NEVER treated as a
    # completed single page (that would silently truncate). Each malformed
    # shape routes to data_shape_schema_mismatch and writes nothing.
    # ------------------------------------------------------------------

    def _one_page_execute(self, product_node):
        def fake_execute(client_self, store, query, variables=None):
            return {'data': {'product': product_node}}
        return fake_execute

    def _one_variant_product(self, gid, variants_connection):
        return {
            'id': gid, 'title': 'Shape Product', 'status': 'ACTIVE',
            'featuredImage': None, 'options': [],
            'variants': variants_connection,
        }

    def _assert_shape_blocked(self, gid, variants_connection):
        templates_before = self.env['product.template'].search_count([])
        product_node = self._one_variant_product(gid, variants_connection)
        with self._patch_send(self._one_page_execute(product_node)):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(
                    self.store, gid, job=self._import_job(gid),
                )
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))

    def _one_node(self):
        return [{
            'id': 'gid://shopify/ProductVariant/shape', 'sku': 'SHP-0',
            'barcode': None, 'price': None, 'compareAtPrice': None,
            'selectedOptions': [], 'image': None, 'inventoryItem': None,
        }]

    def test_page_info_missing_blocked(self):
        self._assert_shape_blocked(
            'gid://shopify/Product/1260', {'nodes': self._one_node()},
        )

    def test_page_info_null_blocked(self):
        self._assert_shape_blocked(
            'gid://shopify/Product/1261',
            {'nodes': self._one_node(), 'pageInfo': None},
        )

    def test_page_info_wrong_type_blocked(self):
        self._assert_shape_blocked(
            'gid://shopify/Product/1262',
            {'nodes': self._one_node(), 'pageInfo': ['not', 'a', 'mapping']},
        )

    def test_has_next_page_missing_blocked(self):
        self._assert_shape_blocked(
            'gid://shopify/Product/1263',
            {'nodes': self._one_node(), 'pageInfo': {'endCursor': None}},
        )

    def test_has_next_page_wrong_type_blocked(self):
        self._assert_shape_blocked(
            'gid://shopify/Product/1264',
            {'nodes': self._one_node(),
             'pageInfo': {'hasNextPage': 'true', 'endCursor': 'c'}},
        )

    def test_nodes_wrong_type_blocked(self):
        self._assert_shape_blocked(
            'gid://shopify/Product/1265',
            {'nodes': {'not': 'a list'},
             'pageInfo': {'hasNextPage': False, 'endCursor': None}},
        )

    def test_variants_wrong_type_blocked(self):
        self._assert_shape_blocked(
            'gid://shopify/Product/1266', ['not', 'a', 'mapping'],
        )

    def test_has_next_page_true_empty_end_cursor_blocked(self):
        self._assert_shape_blocked(
            'gid://shopify/Product/1267',
            {'nodes': self._one_node(),
             'pageInfo': {'hasNextPage': True, 'endCursor': ''}},
        )

    def test_null_product_first_page_no_binding_is_data_error(self):
        gid = 'gid://shopify/Product/1268'
        with self._patch_send(self._one_page_execute(None)):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid, job=self._import_job(gid))
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')

    def test_valid_single_page_shape_accepted(self):
        gid = 'gid://shopify/Product/1269'
        product_node = self._one_variant_product(gid, {
            'nodes': [{
                'id': '%s/v' % gid, 'sku': 'SHP-OK', 'barcode': None,
                'price': None, 'compareAtPrice': None,
                'selectedOptions': [], 'image': None, 'inventoryItem': None,
            }],
            'pageInfo': {'hasNextPage': False, 'endCursor': None},
        })
        with self._patch_send(self._one_page_execute(product_node)):
            result = self.Importer.import_product_sync(self.store, gid, job=self._import_job(gid))
        self.assertEqual(result['template_binding'].shopify_gid, gid)

    def test_over_ceiling_variant_count_blocked(self):
        """More than 2,048 accumulated variants (unreachable by the
        platform) routes to the schema-mismatch hold."""
        gid = 'gid://shopify/Product/1253'

        def fake_execute(client_self, store, query, variables=None):
            cursor = (variables or {}).get('cursor')
            page = 0 if cursor is None else int(cursor.split('-')[1]) + 1
            nodes = [
                {
                    'id': '%s/v/%d-%d' % (gid, page, i), 'sku': None,
                    'barcode': None, 'price': None, 'compareAtPrice': None,
                    'selectedOptions': [], 'image': None, 'inventoryItem': None,
                }
                for i in range(100)
            ]
            return {
                'data': {
                    'product': {
                        'id': gid, 'title': 'Huge', 'status': 'ACTIVE',
                        'featuredImage': None, 'options': [],
                        'variants': {
                            'nodes': nodes,
                            'pageInfo': {
                                'hasNextPage': True, 'endCursor': 'cursor-%d' % page,
                            },
                        },
                    },
                },
            }

        with self._patch_send(fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid, job=self._import_job(gid))
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')

    def test_variant_single_page_not_blocked(self):
        """Regression guard: a normal single-page product (hasNextPage
        False) imports cleanly."""
        def fake_execute(self, store, query, variables=None):
            return {
                'data': {
                    'product': {
                        'id': 'gid://shopify/Product/982',
                        'title': 'Single Page Product', 'status': 'ACTIVE',
                        'featuredImage': None, 'options': [],
                        'variants': {
                            'nodes': [{
                                'id': 'gid://shopify/ProductVariant/982',
                                'sku': 'SKU-982', 'barcode': None,
                                'price': '9.99', 'compareAtPrice': None,
                                'selectedOptions': [], 'image': None,
                                'inventoryItem': None,
                            }],
                            'pageInfo': {
                                'hasNextPage': False, 'endCursor': None,
                            },
                        },
                    },
                },
            }

        gid = 'gid://shopify/Product/982'
        with self._patch_send(fake_execute):
            result = self.Importer.import_product_sync(
                self.store, gid, job=self._import_job(gid),
            )
        self.assertEqual(
            result['template_binding'].shopify_gid, 'gid://shopify/Product/982',
        )

    # ------------------------------------------------------------------
    # 12. Pagination forward-progress and product/variant identity guards
    # (review 4950339305 item 1). A connection that never advances its
    # cursor, replays a seen cursor, repeats a variant GID, or returns a
    # different product GID must route to data_shape_schema_mismatch and
    # write nothing -- and must never spin in an infinite loop. Each fake
    # below caps its call count so a regressed guard fails fast, never hangs.
    # ------------------------------------------------------------------

    def _pnode(self, gid, i):
        """One raw variant node with a deterministic, unique-by-`i` GID."""
        return {
            'id': '%s/v/%d' % (gid, i), 'sku': None, 'barcode': None,
            'price': None, 'compareAtPrice': None, 'selectedOptions': [],
            'image': None, 'inventoryItem': None,
        }

    def _sequenced_execute(self, gid, responses, title='Seq', max_calls=12):
        """Return `(nodes, has_next, end_cursor)` responses in call order,
        independent of the cursor the importer echoes back. A hard
        `max_calls` cap raises rather than allowing an unbounded loop, so a
        regressed forward-progress guard makes the test FAIL instead of
        hanging."""
        state = {'i': 0}

        def fake_execute(client_self, store, query, variables=None):
            if state['i'] >= max_calls:
                raise AssertionError(
                    'pagination exceeded %d calls -- forward-progress guard '
                    'did not stop it.' % (max_calls,))
            nodes, has_next, end_cursor = responses[
                min(state['i'], len(responses) - 1)
            ]
            state['i'] += 1
            return {
                'data': {
                    'product': {
                        'id': gid, 'title': title, 'status': 'ACTIVE',
                        'featuredImage': None, 'options': [],
                        'variants': {
                            'nodes': nodes,
                            'pageInfo': {
                                'hasNextPage': has_next, 'endCursor': end_cursor,
                            },
                        },
                    },
                },
            }
        return fake_execute

    def _assert_sequenced_blocked(self, gid, responses):
        templates_before = self.env['product.template'].search_count([])
        fake_execute = self._sequenced_execute(gid, responses)
        with self._patch_send(fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(
                    self.store, gid, job=self._import_job(gid),
                )
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))

    def test_repeated_cursor_zero_nodes_blocked(self):
        """hasNextPage stays true with the same cursor and zero nodes -- the
        classic infinite-loop shape. The forward-progress guard stops it."""
        self._assert_sequenced_blocked(
            'gid://shopify/Product/1280',
            [([], True, 'stuck'), ([], True, 'stuck')],
        )

    def test_repeated_cursor_repeated_nodes_blocked(self):
        gid = 'gid://shopify/Product/1281'
        node = self._pnode(gid, 0)
        self._assert_sequenced_blocked(
            gid, [([node], True, 'c1'), ([node], True, 'c1')],
        )

    def test_cursor_equal_to_current_cursor_blocked(self):
        gid = 'gid://shopify/Product/1282'
        self._assert_sequenced_blocked(gid, [
            ([self._pnode(gid, 0)], True, 'c1'),
            ([self._pnode(gid, 1)], True, 'c1'),  # endCursor == cursor just used
        ])

    def test_previously_seen_cursor_replayed_blocked(self):
        gid = 'gid://shopify/Product/1283'
        self._assert_sequenced_blocked(gid, [
            ([self._pnode(gid, 0)], True, 'c1'),
            ([self._pnode(gid, 1)], True, 'c2'),
            ([self._pnode(gid, 2)], True, 'c1'),  # c1 already seen
        ])

    def test_duplicate_variant_gid_across_pages_blocked(self):
        gid = 'gid://shopify/Product/1284'
        node = self._pnode(gid, 0)
        self._assert_sequenced_blocked(gid, [
            ([node], True, 'c1'),
            ([node], False, None),  # same variant GID on a later page
        ])

    def test_duplicate_variant_gid_within_one_page_blocked(self):
        gid = 'gid://shopify/Product/1285'
        node = self._pnode(gid, 0)
        self._assert_shape_blocked(gid, {
            'nodes': [node, node],  # same GID twice in one page
            'pageInfo': {'hasNextPage': False, 'endCursor': None},
        })

    def test_non_mapping_variant_node_blocked(self):
        self._assert_shape_blocked('gid://shopify/Product/1286', {
            'nodes': [None],
            'pageInfo': {'hasNextPage': False, 'endCursor': None},
        })

    def test_variant_node_missing_gid_blocked(self):
        self._assert_shape_blocked('gid://shopify/Product/1287', {
            'nodes': [{'sku': 'NO-GID'}],  # a mapping, but no id
            'pageInfo': {'hasNextPage': False, 'endCursor': None},
        })

    def test_returned_product_gid_mismatch_blocked(self):
        requested = 'gid://shopify/Product/1288'
        templates_before = self.env['product.template'].search_count([])
        other_node = {
            'id': 'gid://shopify/Product/DIFFERENT', 'title': 'Wrong Product',
            'status': 'ACTIVE', 'featuredImage': None, 'options': [],
            'variants': {
                'nodes': [self._pnode(requested, 0)],
                'pageInfo': {'hasNextPage': False, 'endCursor': None},
            },
        }
        with self._patch_send(self._one_page_execute(other_node)):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(
                    self.store, requested, job=self._import_job(requested),
                )
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', requested),
        ]))

    def test_valid_two_page_progressing_cursors_accepted(self):
        """Regression guard: a genuine two-page product with distinct,
        strictly progressing cursors and unique variant GIDs still imports
        completely under the new forward-progress/identity guards."""
        gid = 'gid://shopify/Product/1289'
        option_values, pages = self._single_option_pages(gid, 2, page_size=1)
        self.assertEqual(len(pages), 2)
        fake_execute = self._paginated_execute(
            gid, 'Two Page', option_values, pages,
        )
        with self._patch_send(fake_execute):
            result = self.Importer.import_product_sync(self.store, gid, job=self._import_job(gid))
        self.assertEqual(len(result['variant_bindings']), 2)

    # ------------------------------------------------------------------
    # 13. Zero-node forward progress (review 4951145191 item 1). A
    # `hasNextPage=true` page carrying zero variants makes no data progress;
    # combined with the unique-GID guard and the 2,048-variant cap it would
    # otherwise loop forever behind ever-fresh cursors. It must be blocked.
    # ------------------------------------------------------------------

    def _empty_fresh_cursor_execute(self, gid, max_calls=25):
        """Every page: `hasNextPage=true`, `nodes=[]`, and a brand-new,
        never-repeating cursor. Without the zero-node guard this loops
        forever (no cursor repeats, no variant accumulates, the 2,048 cap
        never fires); the `max_calls` cap turns a regression into a FAILURE
        rather than a hang."""
        state = {'i': 0}

        def fake_execute(client_self, store, query, variables=None):
            state['i'] += 1
            if state['i'] > max_calls:
                raise AssertionError(
                    'zero-node pagination did not terminate after %d calls -- '
                    'the forward-progress guard did not stop it.' % (max_calls,))
            return {
                'data': {
                    'product': {
                        'id': gid, 'title': 'Empty Pages', 'status': 'ACTIVE',
                        'updatedAt': '2026-07-12T00:00:00Z',
                        'featuredImage': None, 'options': [],
                        'variants': {
                            'nodes': [],
                            'pageInfo': {
                                'hasNextPage': True,
                                'endCursor': 'fresh-%d' % state['i'],
                            },
                        },
                    },
                },
            }
        return fake_execute

    def test_zero_node_pages_with_fresh_cursors_blocked(self):
        gid = 'gid://shopify/Product/1290'
        templates_before = self.env['product.template'].search_count([])
        with self._patch_send(self._empty_fresh_cursor_execute(gid)):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid, job=self._import_job(gid))
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))

    # ------------------------------------------------------------------
    # 14. Cross-page updatedAt torn-read guard (review 4951145191 item 2).
    # Each page is a separate request; the product's updatedAt captured on
    # page one must be carried unchanged (same present/absent shape and
    # value) on every later page, or the fetch would splice one remote
    # version's metadata onto another version's variants. Any change routes
    # to data_shape_schema_mismatch before any write. In-run torn-read guard
    # only -- not Area-6 enqueue deduplication.
    # ------------------------------------------------------------------

    def _two_page_updated_at_execute(
        self, gid, first_updated, second_updated,
        first_present=True, second_present=True,
    ):
        """Two-page product; page one carries `first_updated`, page two
        `second_updated`. `*_present` toggles whether the `updatedAt` key is
        present at all (to exercise the present/absent shape guard)."""
        v0 = self._pnode(gid, 0)
        v1 = self._pnode(gid, 1)

        def product_node(updated, present, nodes, has_next, end_cursor):
            node = {
                'id': gid, 'title': 'TP', 'status': 'ACTIVE',
                'featuredImage': None, 'options': [],
                'variants': {
                    'nodes': nodes,
                    'pageInfo': {'hasNextPage': has_next, 'endCursor': end_cursor},
                },
            }
            if present:
                node['updatedAt'] = updated
            return node

        def fake_execute(client_self, store, query, variables=None):
            cursor = (variables or {}).get('cursor')
            if cursor is None:
                return {'data': {'product': product_node(
                    first_updated, first_present, [v0], True, 'c1')}}
            return {'data': {'product': product_node(
                second_updated, second_present, [v1], False, None)}}
        return fake_execute

    def _assert_cross_page_blocked(self, gid, fake_execute):
        templates_before = self.env['product.template'].search_count([])
        with self._patch_send(fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(
                    self.store, gid, job=self._import_job(gid),
                )
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))

    def test_cross_page_identical_updated_at_accepted(self):
        """Two pages carrying the SAME product `updatedAt` accumulate both
        variants and import completely -- the cross-page torn-read guard does
        NOT reject a consistent product (`_paginated_execute` stamps one
        identical `updatedAt` on every page).

        CORE-R2 Slice 2B: the former assertion on the now-dissolved
        `_fetch_product_with_all_variant_pages` return value is replaced by the
        full loop-owned call site, which accumulates across per-page
        `execute_business` leases and reconciles inside the terminal page's
        lease -- so the observable is the two imported variant bindings."""
        gid = 'gid://shopify/Product/1291'
        option_values, pages = self._single_option_pages(gid, 2, page_size=1)
        self.assertEqual(len(pages), 2)
        fake_execute = self._paginated_execute(
            gid, 'Consistent Two Page', option_values, pages,
        )
        with self._patch_send(fake_execute):
            result = self.Importer.import_product_sync(
                self.store, gid, job=self._import_job(gid),
            )
        self.assertEqual(len(result['variant_bindings']), 2)

    def test_cross_page_changed_updated_at_blocked(self):
        gid = 'gid://shopify/Product/1292'
        self._assert_cross_page_blocked(
            gid, self._two_page_updated_at_execute(gid, 'U1', 'U2'))

    def test_cross_page_first_missing_second_present_blocked(self):
        gid = 'gid://shopify/Product/1293'
        self._assert_cross_page_blocked(
            gid,
            self._two_page_updated_at_execute(
                gid, None, 'U2', first_present=False, second_present=True),
        )

    def test_cross_page_first_present_second_missing_blocked(self):
        gid = 'gid://shopify/Product/1294'
        self._assert_cross_page_blocked(
            gid,
            self._two_page_updated_at_execute(
                gid, 'U1', None, first_present=True, second_present=False),
        )


class TestProductCallSiteExecuteBusiness(TransactionCase):
    """CORE-R2 Slice 2B (AR-047, RD-P): the product importer's call-site
    migration from the legacy value-returning `execute()` to the loop-owned
    `execute_business(job, store, query, variables)` admission-lease context
    manager.

    These are the Slice-2B activation tests. They exercise the REAL core
    admission gate + `_send` transport seam (no lifecycle/state monkeypatch):
    one committed `shopify.connector.call.lease` per Shopify Admin page, held
    from before that page's transport through -- on the terminal page -- the
    complete reconciliation and the final `flush_all`, released on every exit.
    Static/public-call guards, one-page and multi-page lease lifecycles, and
    the failure/quiescence/disconnect paths are all covered here; the existing
    Task 010B suites (adapted to the same gate) provide the behavioural
    regression coverage (item E)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'CORE-R2 Product Call-Site Store',
            'shop_domain': 'core-r2-product-callsite.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.product.importer']
        cls.TemplateBinding = cls.env['shopify.connector.product.template.binding']
        cls.VariantBinding = cls.env['shopify.connector.product.variant.binding']
        cls.Job = cls.env['shopify.connector.job']
        cls.Lease = cls.env['shopify.connector.call.lease']
        # Seed a credential while `setup_incomplete` so no generation bump
        # occurs; the store stays at generation 0, matching a job's default
        # captured generation.
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN,
        )
        cls.env.flush_all()

    def setUp(self):
        super().setUp()
        # Enter registry test mode so `execute_business._admit`'s side cursor
        # sees the fixture (the sanctioned core-test mechanism); no production
        # behaviour changes and it is auto-left on teardown.
        self.env.flush_all()
        self.registry_enter_test_mode()

    # -- helpers -------------------------------------------------------

    def _import_job(self, shopify_target_gid):
        """Connect the store (business-job create gate) and return a
        product-import job at generation 0 (matching the store)."""
        self.store.write({'state': 'connected'})
        job = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': shopify_target_gid,
        })
        self.env.flush_all()
        return job

    def _patch_send(self, fake_execute):
        """Patch only the `_send` transport seam so `fake_execute` drives the
        real `execute_business` gate + `_normalize_response`."""
        Client = self.env['shopify.connector.api.client']

        def fake_send(client_self, store, body, token=None):
            body = body or {}
            outcome = fake_execute(
                client_self, store, body.get('query'), body.get('variables'),
            )
            return _FakeSendResponse(outcome)

        return patch.object(type(Client), '_send', fake_send)

    def _lease_count(self):
        return self.Lease.search_count([('store_id', '=', self.store.id)])

    def _make_product(self, name, default_code=None):
        template = self.env['product.template'].create({'name': name})
        if default_code:
            template.product_variant_id.default_code = default_code
        return template

    def _variant_node(self, gid, sku, selected=None, image_url=None):
        node = {
            'id': gid, 'sku': sku, 'barcode': None,
            'price': None, 'compareAtPrice': None,
            'selectedOptions': selected or [], 'image': None,
            'inventoryItem': None,
        }
        if image_url:
            node['image'] = {'url': image_url}
        return node

    def _product_page(
        self, gid, nodes, has_next, end_cursor, options=None,
        updated='2026-07-13T00:00:00Z', image_url=None,
    ):
        return {'data': {'product': {
            'id': gid, 'title': 'Call-Site Product', 'status': 'ACTIVE',
            'updatedAt': updated,
            'featuredImage': {'url': image_url} if image_url else None,
            'options': options or [],
            'variants': {
                'nodes': nodes,
                'pageInfo': {'hasNextPage': has_next, 'endCursor': end_cursor},
            },
        }}}

    def _single_page_fake(self, gid, sku='CS-SINGLE'):
        """One no-option, single-variant product -> a clean singleton import."""
        def fake_execute(client_self, store, query, variables=None):
            return self._product_page(
                gid, [self._variant_node('%s/v/0' % gid, sku)], False, None,
            )
        return fake_execute

    def _multi_page_fake(self, gid, pages):
        """One structured product spanning `pages` variant pages (one variant
        per page, each a distinct value of a single `Edition` option), so the
        product is genuinely importable. Returns `(fake_execute, calls)`."""
        option_values = [
            {'id': 'ov-%d' % i, 'name': 'Ed-%d' % i} for i in range(pages)
        ]
        options = [{
            'id': 'opt', 'name': 'Edition', 'position': 1,
            'optionValues': option_values,
        }]
        calls = {'n': 0}

        def fake_execute(client_self, store, query, variables=None):
            idx = calls['n']
            calls['n'] += 1
            node = self._variant_node(
                '%s/v/%d' % (gid, idx), 'CS-MP-%d' % idx,
                selected=[{'name': 'Edition', 'value': 'Ed-%d' % idx}],
            )
            has_next = idx < pages - 1
            end_cursor = 'cur-%d' % idx if has_next else None
            return self._product_page(
                gid, [node], has_next, end_cursor, options=options,
            )
        return fake_execute, calls

    # ==================================================================
    # A. Static / public-call guards.
    # ==================================================================

    def _importer_source(self):
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'shopify_connector_product_importer.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            return source_file.read()

    def test_source_guard_execute_business_only(self):
        import re
        src = self._importer_source()
        # No reachable legacy value-returning api-client `execute()` call.
        self.assertNotIn('.execute(', src)
        # The value-escaping fetch/transport helpers are dissolved.
        self.assertNotIn('_execute_query', src)
        self.assertNotIn('_fetch_product_with_all_variant_pages', src)
        # `execute_business` is the sole transport entry, admitted WITH a job.
        self.assertIn('client.execute_business(', src)
        self.assertTrue(
            re.search(r'execute_business\(\s*job,', src),
            'execute_business must be admitted with the real job as first arg',
        )

    def test_source_guard_no_manual_lease_or_commit(self):
        src = self._importer_source()
        # Admission + release are owned by the core context manager -- the
        # importer never touches the lease model or releases a lease itself.
        self.assertNotIn('call.lease', src)
        self.assertNotIn('_release_lease', src)
        # No explicit main-cursor commit anywhere in the importer.
        self.assertNotIn('cr.commit(', src)
        # The terminal reconciliation materializes via flush_all (in-txn).
        self.assertIn('self.env.flush_all()', src)

    def test_no_legacy_execute_fallback_at_runtime(self):
        """The migrated path never falls back to the legacy `execute()`."""
        gid = 'gid://shopify/Product/CS-NOFB'
        Client = self.env['shopify.connector.api.client']
        exec_calls = []
        orig_execute = type(Client).execute

        def spy_execute(client_self, store, query, variables=None):
            exec_calls.append(1)
            return orig_execute(client_self, store, query, variables=variables)

        job = self._import_job(gid)
        with patch.object(type(Client), 'execute', spy_execute), \
                self._patch_send(self._single_page_fake(gid)):
            result = self.Importer.import_product_sync(self.store, gid, job=job)
        self.assertEqual(exec_calls, [])   # legacy execute() never called
        self.assertEqual(len(result['variant_bindings']), 1)

    # ==================================================================
    # B. One-page product: one lease, reconcile + flush + release inside.
    # ==================================================================

    def test_single_page_one_lease_reconciles_flushes_releases(self):
        gid = 'gid://shopify/Product/CS-100'
        at_send = []
        at_apply = []
        flushed_at_apply = []
        Importer = type(self.Importer)
        orig_apply = Importer._apply_import

        def spy_apply(imp_self, store, payload, job=None, requested_gid=None):
            # Reconciliation runs while the (single) lease is still held.
            at_apply.append(self._lease_count())
            return orig_apply(
                imp_self, store, payload, job=job, requested_gid=requested_gid,
            )

        def fake_execute(client_self, store, query, variables=None):
            # Transport runs with the lease already committed (== 1).
            at_send.append(self._lease_count())
            return self._product_page(
                gid, [self._variant_node('%s/v/0' % gid, 'CS-100-0')],
                False, None,
            )

        job = self._import_job(gid)
        with patch.object(Importer, '_apply_import', spy_apply), \
                self._patch_send(fake_execute):
            result = self.Importer.import_product_sync(self.store, gid, job=job)

        self.assertEqual(len(at_send), 1)          # exactly one page/transport
        self.assertEqual(at_send, [1])             # lease held at transport
        self.assertEqual(at_apply, [1])            # lease held through reconcile
        self.assertEqual(self._lease_count(), 0)   # released after reconcile+flush
        self.assertEqual(result['template_binding'].shopify_gid, gid)
        self.assertEqual(len(result['variant_bindings']), 1)

    def test_single_page_return_and_bindings_come_from_terminal_context(self):
        """The binding is created (reconciliation ran) and the lease is gone
        (released) -- proving reconcile+flush+release all completed inside the
        one terminal context."""
        gid = 'gid://shopify/Product/CS-101'
        job = self._import_job(gid)
        with self._patch_send(self._single_page_fake(gid, sku='CS-101-0')):
            result = self.Importer.import_product_sync(self.store, gid, job=job)
        self.assertTrue(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))
        self.assertEqual(len(result['variant_bindings']), 1)
        self.assertEqual(self._lease_count(), 0)

    # ==================================================================
    # C. Multi-page product: one lease per page, terminal reconciliation.
    # ==================================================================

    def test_multi_page_one_lease_per_page_terminal_reconciles(self):
        gid = 'gid://shopify/Product/CS-300'
        pages = 3
        fake_execute, calls = self._multi_page_fake(gid, pages)
        lease_at_send = []
        bindings_at_send = []
        apply_calls = []
        Importer = type(self.Importer)
        orig_apply = Importer._apply_import
        Client = self.env['shopify.connector.api.client']

        def spy_apply(imp_self, store, payload, job=None, requested_gid=None):
            apply_calls.append(1)
            return orig_apply(
                imp_self, store, payload, job=job, requested_gid=requested_gid,
            )

        def spy_send(client_self, store, body, token=None):
            # At every page's transport: exactly one lease, and no product
            # binding yet (non-terminal pages write no business records; the
            # terminal page reconciles only AFTER its transport returns).
            lease_at_send.append(self._lease_count())
            bindings_at_send.append(self.TemplateBinding.search_count([
                ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
            ]))
            body = body or {}
            return _FakeSendResponse(fake_execute(
                client_self, store, body.get('query'), body.get('variables'),
            ))

        job = self._import_job(gid)
        with patch.object(Importer, '_apply_import', spy_apply), \
                patch.object(type(Client), '_send', spy_send):
            result = self.Importer.import_product_sync(self.store, gid, job=job)

        self.assertEqual(calls['n'], pages)                 # exactly N API calls
        self.assertEqual(len(lease_at_send), pages)
        self.assertTrue(all(c == 1 for c in lease_at_send)) # one lease at a time
        self.assertTrue(all(b == 0 for b in bindings_at_send))  # no early write
        self.assertEqual(len(apply_calls), 1)               # terminal reconcile only
        self.assertEqual(self._lease_count(), 0)            # released after
        self.assertEqual(len(result['variant_bindings']), pages)
        self.assertEqual(
            len(result['template_binding'].product_template_id
                .product_variant_ids),
            pages,
        )

    def test_multi_page_existing_cursor_and_dedup_guards_still_fire(self):
        """A repeated variant GID across pages still routes to a schema
        mismatch under the loop-owned context -- the pagination guards run
        inside each page's lease exactly as before."""
        gid = 'gid://shopify/Product/CS-301'
        node = self._variant_node('%s/v/0' % gid, 'CS-301-0')

        def fake_execute(client_self, store, query, variables=None):
            cursor = (variables or {}).get('cursor')
            if cursor is None:
                return self._product_page(gid, [node], True, 'cur-0')
            return self._product_page(gid, [node], False, None)  # repeated GID

        job = self._import_job(gid)
        with self._patch_send(fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid, job=job)
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(self._lease_count(), 0)   # every page's lease released

    # ==================================================================
    # D. Failure and lifecycle: lease released once on every failure path;
    #    quiescence propagates uncaught; no partial write across a disconnect.
    # ==================================================================

    def test_transport_client_error_routes_and_releases_once(self):
        gid = 'gid://shopify/Product/CS-400'

        def fake_execute(client_self, store, query, variables=None):
            raise ShopifyClientError(
                'shopify_throttling_rate_limit', 'Slow down.',
            )

        job = self._import_job(gid)
        with self._patch_send(fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid, job=job)
        self.assertEqual(
            ctx.exception.error_class, 'shopify_throttling_rate_limit',
        )
        self.assertEqual(self._lease_count(), 0)

    def test_normalization_error_releases_once(self):
        gid = 'gid://shopify/Product/CS-401'

        def fake_execute(client_self, store, query, variables=None):
            # variants is not a mapping -> a page validation (normalization)
            # error inside the terminal context, before any write.
            return {'data': {'product': {
                'id': gid, 'title': 'X', 'status': 'ACTIVE',
                'featuredImage': None, 'options': [],
                'variants': ['not', 'a', 'mapping'],
            }}}

        job = self._import_job(gid)
        with self._patch_send(fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid, job=job)
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(self._lease_count(), 0)

    def test_reconciliation_error_releases_once(self):
        gid = 'gid://shopify/Product/CS-402'
        # Two Odoo products share the incoming SKU -> ambiguous template match
        # raised inside `_apply_import`, inside the terminal lease.
        self._make_product('Dup A', default_code='CS-DUP')
        self._make_product('Dup B', default_code='CS-DUP')

        def fake_execute(client_self, store, query, variables=None):
            return self._product_page(
                gid, [self._variant_node('%s/v/0' % gid, 'CS-DUP')],
                False, None,
            )

        job = self._import_job(gid)
        with self._patch_send(fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid, job=job)
        self.assertEqual(ctx.exception.error_class, 'ambiguous_match')
        self.assertEqual(self._lease_count(), 0)

    def test_media_error_releases_once(self):
        gid = 'gid://shopify/Product/CS-403'
        Importer = type(self.Importer)

        def fake_execute(client_self, store, query, variables=None):
            return self._product_page(
                gid,
                [self._variant_node('%s/v/0' % gid, 'CS-403-0')],
                False, None, image_url='https://cdn.shopify.com/p.png',
            )

        def boom(inner, url):
            raise JobHandlerError(
                'shopify_temporary_server_network', 'unreachable image',
            )

        job = self._import_job(gid)
        with self._patch_send(fake_execute), \
                patch.object(Importer, '_fetch_image', boom):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid, job=job)
        self.assertEqual(
            ctx.exception.error_class, 'shopify_temporary_server_network',
        )
        self.assertEqual(self._lease_count(), 0)

    def test_quiesced_admission_propagates_uncaught_no_transport_no_write(self):
        """Exception-contract proof (validation-plan M9, generation-mismatch
        trigger): a `ShopifyQuiescedError` from a fail-closed admission
        propagates UNCAUGHT from the importer (never remapped to
        `JobHandlerError`), with no transport and no write. This is a
        same-test-transaction generation bump under registry test mode -- an
        M9 refusal proof, NOT the genuine cross-connection admission-vs-
        `action_disconnect` race (M8), which is proven by
        `TestProductCallSiteLifecycleGenuine`."""
        gid = 'gid://shopify/Product/CS-404'
        sent = []

        def fake_execute(client_self, store, query, variables=None):
            sent.append(1)
            return self._product_page(
                gid, [self._variant_node('%s/v/0' % gid, 'CS-404-0')],
                False, None,
            )

        job = self._import_job(gid)
        # M9: a generation move after enqueue makes admission fail closed
        # (a data-value generation bump, not a genuine action_disconnect).
        self.store.write({
            'connection_generation': job.expected_connection_generation + 1,
        })
        self.env.flush_all()
        with self._patch_send(fake_execute):
            with self.assertRaises(ShopifyQuiescedError):
                self.Importer.import_product_sync(self.store, gid, job=job)
        # ShopifyQuiescedError is NOT remapped to JobHandlerError, no transport
        # occurred, no lease survives, and nothing was written.
        self.assertEqual(sent, [])
        self.assertEqual(self._lease_count(), 0)
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))

    def test_generation_bump_between_pages_refuses_next_admission_m9_m10(self):
        """Validation-plan M9/M10 (generation mismatch / no-second-call): a
        generation bump landing BETWEEN pages fails the next page's admission
        closed -- page 2 never transports, page 1's lease is released, and no
        partial product is written.

        This is a same-test-transaction generation bump under registry test
        mode -- an M9/M10 next-admission-refusal proof. It is **not** Race A
        (M8): it does not use the genuine cross-connection
        `action_disconnect` vs `_admit` lock protocol. Genuine M8 (both
        orderings) is proven by `TestProductCallSiteLifecycleGenuine`."""
        gid = 'gid://shopify/Product/CS-405'
        job = self._import_job(gid)
        sent = []
        options = [{
            'id': 'opt', 'name': 'Edition', 'position': 1,
            'optionValues': [{'id': 'ov0', 'name': 'Ed-0'},
                             {'id': 'ov1', 'name': 'Ed-1'}],
        }]

        def fake_execute(client_self, store, query, variables=None):
            sent.append(1)
            if len(sent) == 1:
                # M9/M10: a generation bump lands BETWEEN pages (a data-value
                # bump, NOT a genuine action_disconnect) after this (page-1)
                # admission committed but before page 2 admits.
                self.store.write({
                    'connection_generation':
                        job.expected_connection_generation + 1,
                })
                self.env.flush_all()
                return self._product_page(
                    gid,
                    [self._variant_node(
                        '%s/v/0' % gid, 'CS-405-0',
                        selected=[{'name': 'Edition', 'value': 'Ed-0'}])],
                    True, 'cur-0', options=options,
                )
            return self._product_page(
                gid,
                [self._variant_node(
                    '%s/v/1' % gid, 'CS-405-1',
                    selected=[{'name': 'Edition', 'value': 'Ed-1'}])],
                False, None, options=options,
            )

        with self._patch_send(fake_execute):
            with self.assertRaises(ShopifyQuiescedError):
                self.Importer.import_product_sync(self.store, gid, job=job)
        # Page 1 transported once; page 2 was refused BEFORE its transport.
        self.assertEqual(len(sent), 1)
        # Page 1's lease released; page 2 never admitted -> zero leases.
        self.assertEqual(self._lease_count(), 0)
        # No product/binding was written (reconciliation never began).
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))
        self.assertFalse(self.VariantBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', '%s/v/0' % gid),
        ]))


@tagged(
    # Opt-in only: this class opens genuine independent `db_connect`
    # PostgreSQL connections and spawns worker threads, so it is deliberately
    # EXCLUDED from the standard CI suite (`-standard`) and from the
    # at-install phase (`-at_install`); it runs post-install and only when its
    # own explicit tag is selected, e.g.
    #   odoo --test-tags shopify_connector_product_callsite_lifecycle
    'post_install', '-at_install', '-standard',
    'shopify_connector_product_callsite_lifecycle',
)
class TestProductCallSiteLifecycleGenuine(TransactionCase):
    """Genuine independent-PostgreSQL-connection lifecycle proofs for the
    CORE-R2 Slice 2B product call site (validation plan M1/M2, M8, M18).

    Mirrors the accepted core `TestGenuineRealAdmission` harness: each worker
    owns a real pooled `db_connect` main cursor + Environment created AFTER the
    fixtures commit; the production `_admit`/`_release_lease` side transactions
    are made genuinely independent (real pooled bounded cursors that commit and
    are observable cross-connection) by patching the registry cursor factory for
    the bounded window. `action_disconnect`, `_admit`, the lease ORM, the
    generation checks, and `_run_disconnect_quiesce` are the REAL production
    code -- only `_send` is replaced (the network seam), and reconciliation is
    paused via an observe-and-delegate spy on the product-domain `_apply_import`
    (never a lifecycle/state/controller monkeypatch). Raw SQL is used only to
    OBSERVE committed rows and to clean up; it never creates the lease under
    test.

    These tests require a live PostgreSQL backend and a fully-built Odoo
    registry; they are authored to run under the Odoo test runner (Odoo.sh /
    dev), not in a plain GitHub session. No live Shopify request is made and no
    real token is used.
    """

    STATEMENT_TIMEOUT_MS = 10000
    LOCK_TIMEOUT_MS = 8000
    BOUND_SECONDS = 20

    # -- genuine-connection harness (mirrors TestGenuineRealAdmission) --

    def _open_bounded(self, dbname):
        """Open a genuine pooled cursor and apply BOTH transaction-local
        PostgreSQL limits (statement_timeout + lock_timeout); close + re-raise on
        a setup failure so no genuine cursor is ever left unbounded."""
        cr = db_connect(dbname).cursor()
        try:
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(self.LOCK_TIMEOUT_MS)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _real_registry_cursor(self, dbname):
        """registry.cursor() replacement handing out bounded real pooled cursors,
        so every production `_admit`/`_release_lease` side transaction is time
        bounded and genuinely independent (accepts/ignores any args)."""
        return lambda *args, **kwargs: self._open_bounded(dbname)

    # -- test-owned connector-cron trigger ownership (runtime finding #3) --
    #
    # `action_disconnect` and every quiescing controller pass schedule
    # `ir_cron_trigger` rows on the connector's disconnect-quiesce cron (and the
    # job path may schedule the drain cron). Those trigger rows carry no store_id,
    # so ownership is established by a per-test BASELINE captured in setUp: cleanup
    # deletes ONLY the ids that appeared after that snapshot (`current - baseline`)
    # -- exactly the rows this test created -- never a pre-existing trigger, never
    # a whole-cron wipe; `_assert_zero_residue` recomputes the same delta to prove
    # none remain. (Mirrors the accepted customer `_CustomerGenuineHelpers`
    # pattern; the earlier product tests had no such ownership, so their
    # controller triggers accumulated across runs -- runtime finding #3.)

    _CONNECTOR_CRON_XMLIDS = (
        'shopify_connector_core.ir_cron_shopify_connector_disconnect_quiesce',
        'shopify_connector_core.ir_cron_shopify_connector_job_dispatch_drain',
    )

    def setUp(self):
        super().setUp()
        # Snapshot the connector-cron trigger ids that exist BEFORE this test, so
        # teardown deletes (and residue-checks) only the ids this test created.
        self._connector_trigger_baseline = self._trigger_baseline(
            self.env.cr.dbname)

    def _connector_cron_ids(self, cr):
        env = api.Environment(cr, SUPERUSER_ID, {})
        ids = []
        for xmlid in self._CONNECTOR_CRON_XMLIDS:
            cron = env.ref(xmlid, raise_if_not_found=False)
            if cron:
                ids.append(cron.id)
        return ids

    def _trigger_baseline(self, dbname):
        cr = self._open_bounded(dbname)
        try:
            cron_ids = self._connector_cron_ids(cr)
            if not cron_ids:
                cr.rollback()
                return frozenset()
            cr.execute(
                "SELECT id FROM ir_cron_trigger WHERE cron_id = ANY(%s)",
                (cron_ids,))
            baseline = frozenset(row[0] for row in cr.fetchall())
            cr.rollback()
            return baseline
        finally:
            cr.close()

    def _trigger_delta_ids(self, cr, baseline):
        """`sorted(current - baseline)` connector-cron trigger ids on `cr` -- the
        test-owned delta; by construction never a pre-existing/baseline id."""
        cron_ids = self._connector_cron_ids(cr)
        if not cron_ids:
            return []
        cr.execute(
            "SELECT id FROM ir_cron_trigger WHERE cron_id = ANY(%s)", (cron_ids,))
        current = frozenset(row[0] for row in cr.fetchall())
        return sorted(current - baseline)

    def _observe_job_state(self, dbname, job_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT state FROM shopify_connector_job WHERE id = %s", (job_id,))
            row = obs.fetchone()
            obs.rollback()
            return row[0] if row else None
        finally:
            obs.close()

    @staticmethod
    @contextlib.contextmanager
    def _instant_retry_backoff():
        """Make the REAL `odoo.service.model.retrying` inter-try backoff instant
        WITHOUT touching its retry decision or exception classification."""
        patches = []
        if hasattr(service_model, 'time') and hasattr(service_model.time, 'sleep'):
            patches.append(patch.object(service_model.time, 'sleep',
                                        lambda *a, **k: None))
        if hasattr(service_model, 'random') and hasattr(
                service_model.random, 'uniform'):
            patches.append(patch.object(service_model.random, 'uniform',
                                        lambda *a, **k: 0.0))
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            yield

    @contextlib.contextmanager
    def _capture_service_retry(self):
        """Capture the dispatcher's concurrency-recovery log (and the legacy
        `odoo.service.model` retry log) so a genuine SQLSTATE 40001 -- never an
        injected exception -- that drove the corrected no-replay recovery can be
        evidenced. Process-global logging -- a record emitted from a worker
        thread is captured too. (The dispatcher no longer wraps the handler in
        `odoo.service.model.retrying`; the corrected per-job boundary logs the
        SQLSTATE itself from `shopify_connector_job_dispatch` before rolling back
        and reacquiring the job under a fresh row lock -- runtime correction,
        review `4699752673`.)"""
        records = []

        class _Capture(logging.Handler):
            def emit(self_handler, record):
                try:
                    records.append(record.getMessage())
                except Exception:
                    pass

        handler = _Capture()
        loggers = [logging.getLogger(name) for name in (
            'odoo.addons.shopify_connector_core.models.'
            'shopify_connector_job_dispatch',
            'odoo.service.model',
        )]
        prior = [(lg, lg.level) for lg in loggers]
        for lg in loggers:
            lg.setLevel(logging.DEBUG)
            lg.addHandler(handler)
        try:
            yield records
        finally:
            for lg, level in prior:
                lg.removeHandler(handler)
                lg.setLevel(level)

    def _sanitize(self, exc, phase):
        """Type-only, non-sensitive finding for a worker-thread failure (never
        str/repr, SQL, paths, credentials, payloads, or tokens)."""
        error_class = getattr(exc, 'error_class', None)
        return {
            'phase': phase,
            'type': type(exc).__name__,
            'error_class': error_class if isinstance(error_class, str) else None,
        }

    def _safe_worker_teardown(self, wcr, diagnostics):
        if wcr is None:
            return
        try:
            wcr.rollback()
        except BaseException as exc:
            diagnostics.put(self._sanitize(exc, 'rollback'))
        try:
            wcr.close()
        except BaseException as exc:
            diagnostics.put(self._sanitize(exc, 'cursor_close'))

    def _drain(self, diagnostics):
        findings = []
        while True:
            try:
                findings.append(diagnostics.get_nowait())
            except queue.Empty:
                break
        return findings

    def _finalize_threaded(self, threads, resume_events, diagnostics,
                           dbname, store_id, job_id):
        """Cleanup-first, fail-loud teardown for the threaded genuine tests,
        called from the test's `finally` so it runs even when a body assertion
        raised first. Ordered exactly so cleanup can never be skipped by an
        assertion and a stuck worker can never deadlock the delete path or
        yield a false pass:

        1. set every resume gate (release any barrier the worker waits on);
        2. bounded-join each worker (normal, then the join IS the emergency
           recovery -- a genuine `db_connect` cursor cannot be force-killed
           from here, and `_open_bounded`'s statement/lock timeouts guarantee
           the worker self-terminates within the bound);
        3. record worker liveness;
        4. the worker owns and closes its OWN cursor (`_safe_worker_teardown`),
           so nothing the worker holds is closed from here;
        5. if any worker is still alive: DO NOT run destructive cleanup (it may
           still hold row locks -- deleting under it could deadlock or corrupt
           the result); preserve sanitized findings and fail loudly;
        6. only when every worker has stopped: run durable cleanup +
           zero-residue verification;
        7. assertions (here, the loud failure) occur only after that.
        """
        for event in resume_events:
            event.set()
        for thread in threads:
            if thread is not None:
                thread.join(timeout=self.BOUND_SECONDS)
        alive = [t for t in threads if t is not None and t.is_alive()]
        if alive:
            diagnostics.put({
                'phase': 'teardown', 'type': 'WorkerStillAlive',
                'error_class': None,
            })
            # Fail loud, but never issue destructive cleanup against a lock a
            # live worker may own; leave residue diagnosable rather than hang.
            self.fail(
                'worker thread still alive at teardown boundary; skipped '
                'destructive cleanup to avoid a lock deadlock. findings: %s'
                % (self._drain(diagnostics),))
        # Every worker has stopped and released its cursor -> durable cleanup
        # is safe, and its own bounded cursor prevents an indefinite hang.
        self._cleanup(dbname, store_id, job_id)

    # -- fixtures + observers -----------------------------------------

    def _commit_product_fixtures(self, dbname, gid):
        """On an independent bounded connection, create+commit a connected
        store, its credential, and one matching `product_import_sync` job (its
        generation captured at enqueue). Returns `(store_id, job_id)`."""
        setup = self._open_bounded(dbname)
        try:
            env = api.Environment(setup, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Genuine Product Call-Site Store',
                'shop_domain': 'genuine-prod-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07',
                'state': 'connected',
            })
            env['shopify.connector.store.credential'].action_set_token(
                store, DUMMY_TOKEN
            )
            # action_set_token demotes connected -> reconnect_needed; re-assert.
            store.write({'state': 'connected'})
            # Enable the product domain flag so the REAL scheduled-dispatch start
            # gate (`_domain_flag_for_job_type` -> `product_domain_enabled`) admits
            # a `product_import_sync` job driven through run_drain. (The other
            # genuine tests call the importer directly and bypass this gate.)
            env['shopify.connector.store.settings'].create({
                'store_id': store.id, 'product_domain_enabled': True})
            job = env['shopify.connector.job.enqueue'].enqueue(
                store, 'manual_sync', 'product_import_sync',
                payload_hash=uuid.uuid4().hex, shopify_target_gid=gid,
            )
            store_id, job_id = store.id, job.id
            setup.commit()
            return store_id, job_id
        finally:
            setup.close()

    def _committed_lease_rows(self, dbname, store_id):
        """Observe committed leases from a fresh, bounded independent cursor."""
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT lease_key, job_id FROM shopify_connector_call_lease "
                "WHERE store_id = %s ORDER BY lease_key", (store_id,))
            rows = obs.fetchall()
            obs.rollback()
            return rows
        finally:
            obs.close()

    def _store_state(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT state FROM shopify_connector_store WHERE id = %s",
                (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row[0] if row else None
        finally:
            obs.close()

    def _credential_present(self, dbname, store_id):
        """Observe the store's `credential_present` mirror cross-connection."""
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT credential_present FROM shopify_connector_store "
                "WHERE id = %s", (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return bool(row[0]) if row else False
        finally:
            obs.close()

    def _binding_count(self, dbname, store_id):
        """Committed template + variant bindings for the store, cross-connection."""
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT "
                "(SELECT count(*) FROM shopify_connector_product_template_binding "
                " WHERE store_id = %s) "
                "+ (SELECT count(*) FROM shopify_connector_product_variant_binding "
                " WHERE store_id = %s)", (store_id, store_id))
            total = obs.fetchone()[0]
            obs.rollback()
            return total
        finally:
            obs.close()

    def _cleanup(self, dbname, store_id, job_id):
        """Durable, bounded, fail-loud teardown + zero-residue check.

        A successful genuine import commits real Odoo master data (a
        `product.template`, its `product.product` variants, and -- for the
        structured M1/M2 fixture -- a per-test `product.attribute` with its
        `product.attribute.value` set), not just connector rows. This teardown
        removes ALL of it by EXACT id (never a broad name search), in FK-safe
        order, and leaves every pre-existing record untouched:

        1. capture this store's test-owned template/variant/attribute/value ids
           from the store's own template bindings (exact ids only);
        2. unlink the connector product variant bindings (drops FKs into the
           product variants);
        3. unlink the connector product template bindings (drops FKs into the
           templates);
        4. unlink the test-created templates via ORM -- Odoo cascades their
           `product.product`, `product.template.attribute.line`, and
           `product.template.attribute.value` rows;
        5. unlink each captured attribute VALUE only if no attribute line
           anywhere still references it (so a value shared with a pre-existing
           product is never removed);
        6. unlink each captured ATTRIBUTE only if no attribute line anywhere
           still references it (same pre-existing-safety guard);
        7. delete the connector job logs, leases, jobs, credential, and store
           (raw SQL, FK-safe order: logs before jobs because
           `job_log.job_id` is `ondelete='restrict'`) -- this bypasses the
           store model's ORM guards but touches only this store's rows;
        8. verify zero residue for the connector rows AND every captured
           master-data id.
        """
        if store_id is None:
            return
        captured = {
            'templates': [], 'variants': [], 'attributes': [], 'values': [],
        }
        cr = self._open_bounded(dbname)
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            TB = env['shopify.connector.product.template.binding']
            VB = env['shopify.connector.product.variant.binding']
            PTAL = env['product.template.attribute.line']
            # 1. Capture exact test-owned master-data ids from this store only.
            tbindings = TB.search([('store_id', '=', store_id)])
            templates = tbindings.product_template_id.exists()
            captured['templates'] = templates.ids
            captured['variants'] = templates.product_variant_ids.ids
            lines = templates.attribute_line_ids
            captured['attributes'] = lines.attribute_id.ids
            captured['values'] = lines.value_ids.ids
            # 2-3. Connector bindings first (FKs into the product master data).
            VB.search([('store_id', '=', store_id)]).unlink()
            tbindings.unlink()
            # 4. Test-created templates (ORM cascade of variants + line/ptav).
            templates.unlink()
            # 5. Orphaned test-created attribute values (no remaining line ref).
            for value in env['product.attribute.value'].browse(
                captured['values'],
            ).exists():
                if not PTAL.search_count([('value_ids', 'in', value.id)]):
                    value.unlink()
            # 6. Orphaned test-created attributes (no remaining line ref).
            for attribute in env['product.attribute'].browse(
                captured['attributes'],
            ).exists():
                if not PTAL.search_count([('attribute_id', '=', attribute.id)]):
                    attribute.unlink()
            # 6b. Test-owned connector-cron triggers (the delta this test's
            # action_disconnect / controller passes created) -- scoped by id, so a
            # pre-existing trigger is never removed and a whole-cron wipe is never
            # done. This closes the product-lifecycle cron-trigger residue
            # (runtime finding #3).
            delta_ids = self._trigger_delta_ids(
                cr, getattr(self, '_connector_trigger_baseline', frozenset()))
            if delta_ids:
                cr.execute(
                    "DELETE FROM ir_cron_trigger WHERE id = ANY(%s)", (delta_ids,))
            # 7. Connector rows (raw SQL; logs before jobs -- restrict FK).
            cr.execute(
                "DELETE FROM shopify_connector_job_log WHERE job_id IN "
                "(SELECT id FROM shopify_connector_job WHERE store_id = %s)",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_call_lease WHERE store_id = %s",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_job WHERE store_id = %s",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store_settings WHERE store_id = %s",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store WHERE id = %s", (store_id,))
            cr.commit()
        finally:
            cr.close()
        # 8. Zero-residue verification (connector rows + captured master data).
        self._assert_zero_residue(dbname, store_id, captured)

    def _assert_zero_residue(self, dbname, store_id, captured=None):
        v = self._open_bounded(dbname)
        try:
            for table, msg in (
                ('shopify_connector_call_lease', 'lease residue'),
                ('shopify_connector_store', 'store residue'),
                ('shopify_connector_store_credential', 'credential residue'),
                ('shopify_connector_store_settings', 'settings residue'),
                ('shopify_connector_job', 'job residue'),
                ('shopify_connector_job_log', 'job-log residue'),
                ('shopify_connector_product_template_binding',
                 'template-binding residue'),
                ('shopify_connector_product_variant_binding',
                 'variant-binding residue'),
            ):
                col = 'id' if table == 'shopify_connector_store' else 'store_id'
                v.execute(
                    "SELECT count(*) FROM %s WHERE %s = %%s" % (table, col),
                    (store_id,))
                self.assertEqual(v.fetchone()[0], 0, '%s after cleanup' % msg)
            # Every captured Odoo master-data id must be gone -- verified by
            # EXACT id, so the check can never mask residue behind a name match
            # nor implicate a pre-existing record.
            for table, ids, msg in (
                ('product_template', (captured or {}).get('templates') or [],
                 'product.template residue'),
                ('product_product', (captured or {}).get('variants') or [],
                 'product.product residue'),
                ('product_attribute', (captured or {}).get('attributes') or [],
                 'product.attribute residue'),
                ('product_attribute_value',
                 (captured or {}).get('values') or [],
                 'product.attribute.value residue'),
            ):
                if ids:
                    v.execute(
                        "SELECT count(*) FROM %s WHERE id = ANY(%%s)" % table,
                        (list(ids),))
                    self.assertEqual(
                        v.fetchone()[0], 0, '%s after cleanup' % msg)
            # No test-created connector-cron trigger delta may remain (every
            # pre-existing/baseline trigger is untouched by construction).
            self.assertEqual(
                self._trigger_delta_ids(
                    v, getattr(self, '_connector_trigger_baseline', frozenset())),
                [], 'connector cron-trigger delta residue after cleanup')
            v.rollback()
        finally:
            v.close()

    # -- product page fixtures ----------------------------------------

    def _variant_node(self, gid, sku, selected=None):
        return {
            'id': gid, 'sku': sku, 'barcode': None,
            'price': None, 'compareAtPrice': None,
            'selectedOptions': selected or [], 'image': None,
            'inventoryItem': None,
        }

    def _page(self, gid, nodes, has_next, end_cursor, options=None):
        return {'data': {'product': {
            'id': gid, 'title': 'Genuine Product', 'status': 'ACTIVE',
            'updatedAt': '2026-07-14T00:00:00Z', 'featuredImage': None,
            'options': options or [],
            'variants': {
                'nodes': nodes,
                'pageInfo': {'hasNextPage': has_next, 'endCursor': end_cursor},
            },
        }}}

    def _edition_options(self, n, name='Edition'):
        return [{
            'id': 'opt', 'name': name, 'position': 1,
            'optionValues': [{'id': 'ov%d' % i, 'name': 'Ed-%d' % i}
                             for i in range(n)],
        }]

    # ==================================================================
    # M1/M2 — genuine committed-lease visibility before each _send and
    # through terminal reconciliation, one lease at a time, released after.
    # ==================================================================

    def test_real_lease_visible_before_send_and_through_reconciliation(self):
        dbname = self.env.cr.dbname
        gid = 'gid://shopify/Product/GEN-M12'
        store_id = job_id = worker_cr = None
        try:
            store_id, job_id = self._commit_product_fixtures(dbname, gid)
            worker_cr = self._open_bounded(dbname)
            wenv = api.Environment(worker_cr, SUPERUSER_ID, {})
            store = wenv['shopify.connector.store'].browse(store_id)
            job = wenv['shopify.connector.job'].browse(job_id)
            Importer = wenv['shopify.connector.product.importer']
            Client = wenv['shopify.connector.api.client']
            # Unique per-test attribute name: the importer maps a Shopify
            # option name straight to `product.attribute.name`, so a marker
            # here guarantees the attribute is CREATED (never a pre-existing
            # one reused) and is unambiguously attributable to this test for
            # the by-exact-id cleanup below.
            attr_name = 'SC2B-%s Edition' % uuid.uuid4().hex
            options = self._edition_options(2, name=attr_name)
            obs = {'sends': [], 'tokens': [], 'apply': []}

            def observing_send(client_self, store_arg, body, token=None):
                obs['tokens'].append(token)
                obs['sends'].append(self._committed_lease_rows(dbname, store_id))
                cursor = ((body or {}).get('variables') or {}).get('cursor')
                if cursor is None:
                    node = self._variant_node(
                        '%s/v/0' % gid, 'M12-0',
                        selected=[{'name': attr_name, 'value': 'Ed-0'}])
                    return _FakeSendResponse(
                        self._page(gid, [node], True, 'cur-0', options=options))
                node = self._variant_node(
                    '%s/v/1' % gid, 'M12-1',
                    selected=[{'name': attr_name, 'value': 'Ed-1'}])
                return _FakeSendResponse(
                    self._page(gid, [node], False, None, options=options))

            real_apply = type(Importer)._apply_import

            def observing_apply(imp_self, store_a, payload, job=None,
                                requested_gid=None):
                obs['apply'].append(self._committed_lease_rows(dbname, store_id))
                return real_apply(imp_self, store_a, payload, job=job,
                                  requested_gid=requested_gid)

            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor(dbname)):
                with patch.object(type(Importer), '_apply_import',
                                  observing_apply):
                    with patch.object(type(Client), '_send', observing_send):
                        result = Importer.import_product_sync(
                            store, gid, job=job)
            # Commit the worker's own transaction so the reconciled master data
            # (template, variants, and the created attribute + values) is
            # genuinely persisted -- making the by-exact-id master-data cleanup
            # and its zero-residue check a real proof, not a no-op.
            worker_cr.commit()
            obs['after'] = self._committed_lease_rows(dbname, store_id)

            # M1: exactly one committed lease is visible before EACH page's send.
            self.assertEqual(len(obs['sends']), 2)          # two pages, two sends
            self.assertEqual(len(obs['sends'][0]), 1)       # one lease, page 1
            self.assertEqual(len(obs['sends'][1]), 1)       # one lease, page 2
            # one lease at a time: the non-terminal page's lease released before
            # the next admission (page-2's key differs from page-1's).
            self.assertNotEqual(obs['sends'][0][0][0], obs['sends'][1][0][0])
            self.assertEqual(obs['sends'][0][0][1], job_id)         # real job id
            self.assertRegex(obs['sends'][0][0][0], r'^[0-9a-f]{32}$')  # opaque key
            self.assertEqual(set(obs['tokens']), {DUMMY_TOKEN})     # real snapshot
            # M2: reconciliation runs exactly once (terminal), lease still visible.
            self.assertEqual(len(obs['apply']), 1)
            self.assertEqual(len(obs['apply'][0]), 1)
            # terminal lease released only AFTER reconciliation + flush + return.
            self.assertEqual(len(obs['after']), 0)
            self.assertEqual(len(result['variant_bindings']), 2)
            # The committed reconciliation is observable cross-connection: two
            # bindings (template + variant... two variants -> three) persisted.
            self.assertEqual(self._binding_count(dbname, store_id), 3)
        finally:
            if worker_cr is not None:
                worker_cr.rollback()
                worker_cr.close()
            self._cleanup(dbname, store_id, job_id)

    # ==================================================================
    # Race A / M8 — disconnect-first ordering (genuine action_disconnect).
    # ==================================================================

    def test_race_a_disconnect_first_refuses_admission(self):
        dbname = self.env.cr.dbname
        gid = 'gid://shopify/Product/GEN-M8A'
        store_id = job_id = worker_cr = None
        try:
            store_id, job_id = self._commit_product_fixtures(dbname, gid)
            # Disconnect COMMITS first on an independent connection (real
            # action_disconnect: FOR NO KEY UPDATE + generation bump +
            # state->disconnecting).
            dcr = self._open_bounded(dbname)
            try:
                denv = api.Environment(dcr, SUPERUSER_ID, {})
                denv['shopify.connector.store'].browse(store_id).action_disconnect()
                dcr.commit()
            finally:
                dcr.close()
            # Worker opens AFTER the disconnect committed -> its admission
            # observes the new state/generation and fails closed.
            worker_cr = self._open_bounded(dbname)
            wenv = api.Environment(worker_cr, SUPERUSER_ID, {})
            store = wenv['shopify.connector.store'].browse(store_id)
            job = wenv['shopify.connector.job'].browse(job_id)
            Importer = wenv['shopify.connector.product.importer']
            Client = wenv['shopify.connector.api.client']
            sent = []

            def counting_send(client_self, store_arg, body, token=None):
                sent.append(1)
                return _FakeSendResponse(self._page(
                    gid, [self._variant_node('%s/v/0' % gid, 'M8A-0')],
                    False, None))

            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor(dbname)):
                with patch.object(type(Client), '_send', counting_send):
                    with self.assertRaises(ShopifyQuiescedError):
                        Importer.import_product_sync(store, gid, job=job)
            # Disconnect-first: no transport, no lease, no partial write.
            self.assertEqual(sent, [])
            self.assertEqual(len(self._committed_lease_rows(dbname, store_id)), 0)
            self.assertEqual(self._binding_count(dbname, store_id), 0)
        finally:
            if worker_cr is not None:
                worker_cr.rollback()
                worker_cr.close()
            self._cleanup(dbname, store_id, job_id)

    # ==================================================================
    # Race A / M8 — admission-first ordering (lease commits, then a
    # concurrent action_disconnect returns without aborting the call).
    # ==================================================================

    def test_race_a_admission_first_lease_commits_then_disconnect_returns(self):
        dbname = self.env.cr.dbname
        gid = 'gid://shopify/Product/GEN-M8B'
        store_id = job_id = t = None
        admitted = threading.Semaphore(0)
        resume = threading.Event()
        diagnostics = queue.Queue()
        tokens = []
        try:
            store_id, job_id = self._commit_product_fixtures(dbname, gid)

            def blocking_send(client_self, store_arg, body, token=None):
                # Race-specific token proof: the page was admitted with the
                # pre-disconnect credential snapshot; record it so the test can
                # assert the admitted call carries exactly that token.
                tokens.append(token)
                admitted.release()        # _admit already committed this lease
                if not resume.wait(timeout=self.BOUND_SECONDS):
                    raise AssertionError('resume gate not set within bound')
                return _FakeSendResponse(self._page(
                    gid, [self._variant_node('%s/v/0' % gid, 'M8B-0')],
                    False, None))

            def worker():
                wcr = None
                try:
                    threading.current_thread().dbname = dbname
                    wcr = self._open_bounded(dbname)
                    wenv = api.Environment(wcr, SUPERUSER_ID, {})
                    store = wenv['shopify.connector.store'].browse(store_id)
                    job = wenv['shopify.connector.job'].browse(job_id)
                    wenv['shopify.connector.product.importer'].import_product_sync(
                        store, gid, job=job)
                    wcr.commit()
                except BaseException as exc:
                    diagnostics.put(self._sanitize(exc, 'worker_body'))
                finally:
                    self._safe_worker_teardown(wcr, diagnostics)

            Client = self.env['shopify.connector.api.client']
            observed = {}
            got = False
            with patch.object(type(self.registry), '_lock', threading.RLock()), \
                    patch.object(self.registry, 'cursor',
                                 self._real_registry_cursor(dbname)):
                with patch.object(type(Client), '_send', blocking_send):
                    t = threading.Thread(target=worker, daemon=True)
                    t.start()
                    got = admitted.acquire(timeout=self.BOUND_SECONDS)
                    if got:
                        # Admission-first: the lease/token snapshot is committed
                        # before the disconnect proceeds.
                        observed['lease_before'] = self._committed_lease_rows(
                            dbname, store_id)
                        dcr = self._open_bounded(dbname)
                        try:
                            denv = api.Environment(dcr, SUPERUSER_ID, {})
                            # Returns within the bound WITHOUT waiting for the
                            # parked, already-admitted worker (uncontended
                            # FOR NO KEY UPDATE; the admission released FOR SHARE).
                            denv['shopify.connector.store'].browse(
                                store_id).action_disconnect()
                            dcr.commit()
                            observed['disconnect_returned'] = True
                        finally:
                            dcr.close()
                    resume.set()
                    # Gate the post-run observation on the worker finishing;
                    # the AUTHORITATIVE liveness check + cleanup run in finally.
                    t.join(timeout=self.BOUND_SECONDS)
            observed['after'] = self._committed_lease_rows(dbname, store_id)

            findings = self._drain(diagnostics)
            self.assertEqual(findings, [], 'worker findings: %s' % findings)
            self.assertTrue(got, 'admission did not commit within bound')
            self.assertEqual(len(observed['lease_before']), 1)   # committed first
            self.assertEqual(observed['lease_before'][0][1], job_id)
            # Race-specific token proof: exactly one transport, carrying the
            # pre-disconnect credential snapshot.
            self.assertEqual(tokens, [DUMMY_TOKEN])
            self.assertTrue(observed.get('disconnect_returned'))  # returned w/o wait
            # The already-admitted page proceeded to completion and released;
            # no untracked admitted call is possible (the one lease is accounted).
            self.assertEqual(len(observed['after']), 0)
            self.assertEqual(self._binding_count(dbname, store_id), 2)
        finally:
            self._finalize_threaded(
                [t], [resume], diagnostics, dbname, store_id, job_id)

    # ==================================================================
    # Race B / M18 — terminal reconciliation survives a concurrent
    # action_disconnect; the controller defers finalization until release.
    # ==================================================================

    def test_race_b_terminal_reconciliation_retry_refuses_after_disconnect(self):
        """Corrected M18 contract (runtime correction, review `4699752673`): the
        terminal-page admission holds a lease and a concurrent real
        ``action_disconnect`` returns without waiting; the controller does NOT
        finalize while the lease is open (credential retained). On release the
        reconciliation's binding write touches the store row the disconnect
        committed and raises a genuine SQLSTATE 40001; the REAL scheduled
        ``run_drain`` dispatcher catches it at its per-job boundary WITHOUT
        replaying the handler -- it rolls back (the lease has already released via
        the ``execute_business`` context exit), resets, REACQUIRES the exact job
        under a real ``FOR UPDATE SKIP LOCKED`` row lock, and routes it ONCE to the
        bounded ``concurrency_race_conflict`` -> ``retry_waiting`` state. A later
        controller pass SWEEPS that (retry_waiting) business job to ``cancelled``
        under the disconnect and finalizes the store. Net: exactly one transport,
        ZERO binding from the aborted attempt, NO second transport (no replay), no
        raw concurrency exception as the outcome, and the superseded job cancelled
        by the disconnect (credential cleared only after the lease releases). (Was
        a ``retrying``-boundary proof whose reset RE-INVOCATION was gate-refused
        into ``failed_retryable``; the corrected dispatcher no longer replays the
        handler and routes once under a reacquired lock, so the disconnect sweep
        cancels the retry_waiting job -- runtime correction, review `4699752673`.)"""
        dbname = self.env.cr.dbname
        gid = 'gid://shopify/Product/GEN-M18'
        store_id = job_id = t = None
        reconciling = threading.Semaphore(0)
        resume = threading.Event()
        diagnostics = queue.Queue()
        tokens = []
        try:
            store_id, job_id = self._commit_product_fixtures(dbname, gid)
            Importer_cls = type(self.env['shopify.connector.product.importer'])
            real_apply = Importer_cls._apply_import

            def pausing_apply(imp_self, store_a, payload, job=None,
                              requested_gid=None):
                # Terminal admission has committed; the lease is held. Pause
                # here (inside terminal reconciliation) while a concurrent
                # disconnect runs, then delegate to the REAL reconciliation.
                reconciling.release()
                if not resume.wait(timeout=self.BOUND_SECONDS):
                    raise AssertionError('resume gate not set within bound')
                return real_apply(imp_self, store_a, payload, job=job,
                                  requested_gid=requested_gid)

            def ok_send(client_self, store_arg, body, token=None):
                # One entry per transport invocation (total across all attempts):
                # proves the terminal admission carries the pre-disconnect
                # credential snapshot AND that the refused retry adds no second
                # transport.
                tokens.append(token)
                return _FakeSendResponse(self._page(
                    gid, [self._variant_node('%s/v/0' % gid, 'M18-0')],
                    False, None))

            def worker():
                wcr = None
                try:
                    threading.current_thread().dbname = dbname
                    wcr = self._open_bounded(dbname)
                    wenv = api.Environment(wcr, SUPERUSER_ID, {})
                    # Drive the REAL scheduled entrypoint so the production
                    # concurrency-retry boundary applies end to end (claims this
                    # job, dispatches it under odoo.service.model.retrying).
                    wenv['shopify.connector.job.dispatch'].run_drain(1)
                    wcr.commit()
                except BaseException as exc:
                    diagnostics.put(self._sanitize(exc, 'worker_body'))
                finally:
                    self._safe_worker_teardown(wcr, diagnostics)

            Client = self.env['shopify.connector.api.client']
            obs = {}
            got = False
            with self._capture_service_retry() as retry_log, \
                    self._instant_retry_backoff(), \
                    patch.object(type(self.registry), '_lock', threading.RLock()), \
                    patch.object(self.registry, 'cursor',
                                 self._real_registry_cursor(dbname)):
                with patch.object(Importer_cls, '_apply_import', pausing_apply):
                    with patch.object(type(Client), '_send', ok_send):
                        t = threading.Thread(target=worker, daemon=True)
                        t.start()
                        got = reconciling.acquire(timeout=self.BOUND_SECONDS)
                        if got:
                            obs['lease_during'] = self._committed_lease_rows(
                                dbname, store_id)
                            obs['cred_before'] = self._credential_present(
                                dbname, store_id)
                            dcr = self._open_bounded(dbname)
                            try:
                                denv = api.Environment(dcr, SUPERUSER_ID, {})
                                # Concurrent disconnect returns within the bound,
                                # WITHOUT waiting for the paused reconciliation.
                                denv['shopify.connector.store'].browse(
                                    store_id).action_disconnect()
                                dcr.commit()
                                obs['disconnect_returned'] = True
                                # Controller must NOT finalize while a lease exists.
                                denv['shopify.connector.store'
                                     ]._run_disconnect_quiesce()
                                dcr.commit()
                            finally:
                                dcr.close()
                            obs['lease_after_ctrl'] = self._committed_lease_rows(
                                dbname, store_id)
                            obs['state_during'] = self._store_state(
                                dbname, store_id)
                            obs['cred_during'] = self._credential_present(
                                dbname, store_id)
                        resume.set()
                        # Gate the post-release observation on the worker
                        # finishing; the AUTHORITATIVE liveness check + cleanup
                        # run in finally so an assertion can never skip cleanup.
                        t.join(timeout=self.BOUND_SECONDS)
            obs['retry_serialization_logged'] = any(
                'serial' in m.lower() or '40001' in m for m in retry_log)
            obs['retry_log_sample'] = list(retry_log)[:6]
            obs['after_release'] = self._committed_lease_rows(dbname, store_id)
            # After the aborted terminal reconciliation released its lease, a
            # fresh controller pass finalizes `completed` and clears the
            # credential.
            fcr = self._open_bounded(dbname)
            try:
                fenv = api.Environment(fcr, SUPERUSER_ID, {})
                fenv['shopify.connector.store']._run_disconnect_quiesce()
                fcr.commit()
            finally:
                fcr.close()
            obs['state_final'] = self._store_state(dbname, store_id)
            obs['cred_final'] = self._credential_present(dbname, store_id)
            obs['job_state_final'] = self._observe_job_state(dbname, job_id)

            findings = self._drain(diagnostics)
            self.assertEqual(findings, [], 'worker findings: %s' % findings)
            self.assertTrue(got, 'terminal reconciliation did not start in bound')
            self.assertEqual(len(obs['lease_during']), 1)   # lease held mid-reconcile
            self.assertTrue(obs['cred_before'])             # credential present
            self.assertTrue(obs.get('disconnect_returned'))  # returned w/o waiting
            self.assertEqual(len(obs['lease_after_ctrl']), 1)  # not reaped early
            self.assertEqual(obs['state_during'], 'disconnecting')  # deferred
            self.assertTrue(obs['cred_during'])             # credential remains
            # Exactly one terminal transport carrying the pre-disconnect snapshot;
            # the refused retry adds none.
            self.assertEqual(tokens, [DUMMY_TOKEN])
            self.assertEqual(len(obs['after_release']), 0)  # released after 40001
            # The aborted attempt bound nothing (retried-then-refused), a genuine
            # 40001 drove the REAL retry boundary, and the job ended in a safe
            # retryable state -- never a raw concurrency error.
            self.assertEqual(
                self._binding_count(dbname, store_id), 0,
                'the superseded (retried-then-refused) attempt must leave no '
                'binding')
            self.assertTrue(
                obs.get('retry_serialization_logged'),
                'a genuine SQLSTATE 40001 must have driven the corrected '
                'dispatcher concurrency-recovery boundary; recovery log sample: '
                '%s' % obs.get('retry_log_sample'))
            self.assertEqual(
                obs.get('job_state_final'), 'cancelled',
                'the superseded job must be routed once (no replay) to '
                'retry_waiting and then cancelled by the disconnect sweep; saw %s'
                % obs.get('job_state_final'))
            self.assertEqual(obs['state_final'], 'disconnected')  # finalized after
            self.assertFalse(obs['cred_final'])             # credential cleared then
        finally:
            self._finalize_threaded(
                [t], [resume], diagnostics, dbname, store_id, job_id)
