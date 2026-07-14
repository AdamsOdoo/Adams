import uuid
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_product_importer import PRODUCT_IMPORT_QUERY


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

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
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

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            result = self.Importer.import_product_sync(
                self.store, 'gid://shopify/Product/907',
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

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
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

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
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

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
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

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(
                    self.store, 'gid://shopify/Product/963',
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

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(
                    self.store, 'gid://shopify/Product/970',
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
        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            result = self.Importer.import_product_sync(self.store, gid)
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
        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid)
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
        Client = self.env['shopify.connector.api.client']
        with patch.object(
            type(Client), 'execute', self._one_page_execute(product_node),
        ):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid)
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
        Client = self.env['shopify.connector.api.client']
        with patch.object(
            type(Client), 'execute', self._one_page_execute(None),
        ):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid)
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
        Client = self.env['shopify.connector.api.client']
        with patch.object(
            type(Client), 'execute', self._one_page_execute(product_node),
        ):
            result = self.Importer.import_product_sync(self.store, gid)
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

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid)
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

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            result = self.Importer.import_product_sync(
                self.store, 'gid://shopify/Product/982',
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
        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid)
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
        Client = self.env['shopify.connector.api.client']
        with patch.object(
            type(Client), 'execute', self._one_page_execute(other_node),
        ):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, requested)
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
        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            result = self.Importer.import_product_sync(self.store, gid)
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
        Client = self.env['shopify.connector.api.client']
        with patch.object(
            type(Client), 'execute', self._empty_fresh_cursor_execute(gid),
        ):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid)
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
        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(self.store, gid)
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))

    def test_cross_page_identical_updated_at_accepted(self):
        """Two pages carrying the same updatedAt accumulate both variants --
        the torn-read guard does not reject a consistent product."""
        gid = 'gid://shopify/Product/1291'
        Client = self.env['shopify.connector.api.client']
        with patch.object(
            type(Client), 'execute',
            self._two_page_updated_at_execute(gid, 'U1', 'U1'),
        ):
            node = self.Importer._fetch_product_with_all_variant_pages(
                self.store, gid)
        self.assertEqual(len(node['variants']['nodes']), 2)

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
