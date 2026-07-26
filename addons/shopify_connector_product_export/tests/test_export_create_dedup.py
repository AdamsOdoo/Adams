"""Create-path duplicate prevention: reconciliation before any retry."""

from odoo.tests.common import tagged

from ..models.shopify_connector_product_export_service import (
    BINDING_METAFIELD_KEY,
    JOB_TYPE_CREATE,
)
from .common import ExportCase, FakeSendResponse, PRODUCT_GID


@tagged('post_install', '-at_install')
class TestExportCreateDedup(ExportCase):

    def _confirmed_create_preview(self):
        self.settings.sudo().write(
            {'product_export_binding_namespace_ready': True}
        )
        preview = self.make_preview(
            export_path='create', state='applying',
            steps=[{'step': JOB_TYPE_CREATE, 'state': 'pending',
                    'variant_ids': self.variant.ids}],
            diff={'variants_create': [
                {'odoo_variant_id': self.variant.id, 'values': {}},
            ], 'untouched': {}},
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        return preview

    # ------------------------------------------------------------------
    # The custom-id upsert identity
    # ------------------------------------------------------------------

    def test_create_carries_the_custom_id_identifier(self):
        preview = self._confirmed_create_preview()
        job = self.make_job(JOB_TYPE_CREATE, preview._name, preview.id)
        snapshot = self.Service._prepare_local_create(job)
        request = self.Service._prepare_preconditions_create(snapshot, {})
        identifier = request['variables']['identifier']['customId']
        self.assertEqual(identifier['key'], BINDING_METAFIELD_KEY)
        self.assertEqual(identifier['value'], str(self.template.id))
        # Synchronous mode is explicit in the document: the async
        # ProductSetOperation polling path is not used in MVP.
        self.assertIn('synchronous: true', request['operation'])

    # ------------------------------------------------------------------
    # Reconciliation by custom id, before any retry
    # ------------------------------------------------------------------

    def _reconcile_with(self, nodes):
        preview = self._confirmed_create_preview()
        job = self.make_job(JOB_TYPE_CREATE, preview._name, preview.id)
        job.sudo().write({'state': 'running'})
        attempt = self.env[
            'shopify.connector.mutation.attempt'
        ].sudo().browse()
        # A minimal stand-in for the attempt the Layer 2 wrapper would have
        # committed: reconciliation reads only these three values from it.
        class _Attempt:
            store_id = self.store
            expected_store_identity = self.store.shop_domain
            preconditions_snapshot = {'custom_id_value': str(self.template.id)}
        body = {'data': {
            'products': {'nodes': nodes},
            'shop': {'myshopifyDomain': self.store.shop_domain},
        }}
        response = FakeSendResponse(body)
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            return self.Service._reconcile_create(_Attempt())

    def test_reconciliation_adopts_a_single_matching_product(self):
        verdict = self._reconcile_with([{
            'id': PRODUCT_GID, 'title': 'Exportable Widget',
            'updatedAt': '2026-07-26T00:00:00Z',
            'variants': {'nodes': []},
        }])
        self.assertEqual(verdict['verdict'], 'applied')
        self.assertEqual(verdict['action'], 'succeed')

    def test_reconciliation_refuses_to_choose_between_two_products(self):
        verdict = self._reconcile_with([
            {'id': PRODUCT_GID, 'title': 'A', 'updatedAt': 'x',
             'variants': {'nodes': []}},
            {'id': 'gid://shopify/Product/222', 'title': 'B', 'updatedAt': 'y',
             'variants': {'nodes': []}},
        ])
        self.assertEqual(verdict['verdict'], 'not_applied')
        self.assertEqual(verdict['action'], 'block_manual_review')
        self.assertEqual(verdict['error_class'], 'duplicate_risk')

    def test_reconciliation_reports_not_applied_when_nothing_matches(self):
        verdict = self._reconcile_with([])
        self.assertEqual(verdict['verdict'], 'not_applied')
        # A reviewer releases the retry: the connector does not resend on its
        # own after an ambiguous create.
        self.assertEqual(verdict['action'], 'block_manual_review')

    def test_reconciliation_refuses_a_different_store_identity(self):
        preview = self._confirmed_create_preview()

        class _Attempt:
            store_id = self.store
            expected_store_identity = self.store.shop_domain
            preconditions_snapshot = {'custom_id_value': str(self.template.id)}

        body = {'data': {
            'products': {'nodes': []},
            'shop': {'myshopifyDomain': 'someone-else.myshopify.com'},
        }}
        response = FakeSendResponse(body)
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            verdict = self.Service._reconcile_create(_Attempt())
        self.assertEqual(verdict['error_class'], 'store_identity_mismatch')

    # ------------------------------------------------------------------
    # Bindings are written immediately after a create
    # ------------------------------------------------------------------

    def test_bindings_are_written_so_the_next_run_takes_the_update_path(self):
        preview = self._confirmed_create_preview()
        product = {
            'id': PRODUCT_GID,
            'title': 'Exportable Widget',
            'updatedAt': '2026-07-26T00:00:00Z',
            'variants': {'nodes': [{
                'id': 'gid://shopify/ProductVariant/777',
                'inventoryItem': {'id': 'i', 'sku': 'WIDGET-1'},
            }]},
        }
        binding = self.Service._bind_created_product(
            self.store, preview, product,
        )
        self.assertEqual(binding.shopify_gid, PRODUCT_GID)
        variant_binding = self.VariantBinding.sudo().search([
            ('store_id', '=', self.store.id),
            ('product_variant_id', '=', self.variant.id),
        ])
        self.assertEqual(
            variant_binding.shopify_gid, 'gid://shopify/ProductVariant/777',
        )
        self.assertEqual(
            variant_binding.product_template_binding_id, binding,
        )

    def test_the_sku_duplicate_gate_reports_every_hit(self):
        body = {'data': {'productVariants': {'nodes': [{
            'id': 'gid://shopify/ProductVariant/900',
            'sku': 'WIDGET-1',
            'product': {'id': 'gid://shopify/Product/900', 'title': 'Theirs'},
        }]}}}
        preview = self._confirmed_create_preview()
        job = self.make_job(
            'product_export_preview', 'product.template', self.template.id,
        )
        job.sudo().write({'state': 'running'})
        response = FakeSendResponse(body)
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            hits = self.Service._search_remote_by_sku(
                self.store, job, {'WIDGET-1'},
            )
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['sku'], 'WIDGET-1')
