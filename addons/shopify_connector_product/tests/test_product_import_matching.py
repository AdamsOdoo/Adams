import uuid
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

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
        bound_template, _bound_variant = self._make_product('Bound Product')
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

    # ------------------------------------------------------------------
    # 2. SKU match when no existing binding.
    # ------------------------------------------------------------------

    def test_sku_match_when_no_existing_binding(self):
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
                        'variants': {'nodes': [{
                            'id': 'gid://shopify/ProductVariant/904',
                            'sku': 'DUP-2', 'barcode': None,
                            'price': None, 'compareAtPrice': None,
                            'selectedOptions': [], 'image': None,
                        }]},
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
                        'variants': {'nodes': [{
                            'id': 'gid://shopify/ProductVariant/907',
                            'sku': 'SKU-907', 'barcode': None,
                            'price': 9.99, 'compareAtPrice': None,
                            'selectedOptions': [
                                {'name': 'Size', 'value': 'M'},
                            ],
                            'image': None,
                        }]},
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
