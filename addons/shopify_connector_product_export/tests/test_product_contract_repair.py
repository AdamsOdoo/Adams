"""Runtime regressions for the repaired product export contract."""

from odoo.tests.common import tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_product_export_service import JOB_TYPE_CREATE
from .common import ExportCase, PRODUCT_GID, VARIANT_GID


@tagged('post_install', '-at_install')
class TestProductContractRepair(ExportCase):

    def test_unmanaged_blanks_are_omitted_and_managed_blanks_clear(self):
        self.template.write({
            'description_sale': False,
            'shopify_export_vendor': False,
            'shopify_export_product_type': False,
            'shopify_export_tags': False,
            'shopify_export_description_managed': False,
            'shopify_export_vendor_managed': False,
            'shopify_export_product_type_managed': False,
            'shopify_export_tags_managed': False,
        })
        desired = self.Service._desired_scalars(self.template)
        for field in ('descriptionHtml', 'vendor', 'productType', 'tags'):
            self.assertNotIn(field, desired)

        self.template.write({
            'shopify_export_description_managed': True,
            'shopify_export_vendor_managed': True,
            'shopify_export_product_type_managed': True,
            'shopify_export_tags_managed': True,
        })
        desired = self.Service._desired_scalars(self.template)
        self.assertEqual(desired['descriptionHtml'], '')
        self.assertEqual(desired['vendor'], '')
        self.assertEqual(desired['productType'], '')
        self.assertEqual(desired['tags'], [])

    def test_singleton_product_set_uses_top_level_sku_and_transport_option(self):
        self.settings.sudo().write({
            'product_export_binding_namespace_ready': True,
        })
        preview = self.make_preview(
            export_path='create', state='applying',
            steps=[{
                'step': JOB_TYPE_CREATE, 'state': 'pending',
                'variant_ids': self.variant.ids,
            }],
            diff={'variants_create': [
                {'odoo_variant_id': self.variant.id, 'values': {}},
            ], 'untouched': {}},
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        job = self.make_job(JOB_TYPE_CREATE, preview._name, preview.id)
        request = self.Service._prepare_preconditions_create(
            self.Service._prepare_local_create(job), {},
        )
        entry = request['variables']['input']['variants'][0]
        self.assertEqual(entry['sku'], 'WIDGET-1')
        self.assertNotIn('inventoryItem', entry)
        self.assertEqual(
            entry['optionValues'], [
                {'optionName': 'Title', 'name': 'Default Title'},
            ],
        )
        self.assertIn('$input: ProductSetInput!', request['operation'])

    def test_default_title_singleton_is_a_safe_update_noop(self):
        binding = self.bind_template()
        remote_variant = {
            'id': VARIANT_GID,
            'barcode': '0001',
            'price': '12.50',
            'compareAtPrice': None,
            'inventoryItem': {
                'id': 'gid://shopify/InventoryItem/1',
                'sku': 'WIDGET-1',
            },
            'selectedOptions': [
                {'name': 'Title', 'value': 'Default Title'},
            ],
        }
        read = {
            'store_identity': self.store.shop_domain,
            'exists': True,
            'product': {
                'id': PRODUCT_GID,
                'title': 'Exportable Widget',
                'descriptionHtml': '<p>A widget.</p>',
                'vendor': 'Adams',
                'productType': 'Widgets',
                'tags': ['alpha', 'beta'],
                'status': 'DRAFT',
                'updatedAt': '2026-07-26T00:00:00Z',
                'options': [{
                    'name': 'Title', 'position': 1,
                    'optionValues': [{'name': 'Default Title'}],
                }],
                'variants': {'nodes': [remote_variant]},
            },
            'variants': [remote_variant],
            'updated_at': '2026-07-26T00:00:00Z',
            'has_collections': False,
            'has_metafields': False,
            'has_media': False,
        }
        diff, steps, blocked = self.Service._preview_update_path(
            self.store, self.template, binding,
            self.Service._desired_scalars(self.template),
            self.Service._desired_options(self.template),
            self.template.product_variant_ids, True, read,
        )
        self.assertFalse([
            item for item in blocked
            if item['kind'] == 'remote_option_divergence'
        ])
        self.assertEqual(steps, [])
        self.assertEqual(diff['scalars'], [])

    def test_create_binding_prefers_direct_sku_and_persists_identity_evidence(self):
        preview = self.make_preview(export_path='create')
        product = {
            'id': PRODUCT_GID,
            'title': 'Exportable Widget',
            'status': 'ACTIVE',
            'descriptionHtml': '<p>A widget.</p>',
            'vendor': 'Adams',
            'productType': 'Widgets',
            'tags': ['alpha', 'beta'],
            'updatedAt': '2026-08-17T00:00:00Z',
            'variants': {'nodes': [{
                'id': VARIANT_GID,
                'sku': 'WIDGET-1',
                'barcode': '0001',
                'price': '12.50',
                'compareAtPrice': None,
                'selectedOptions': [],
                'inventoryItem': {
                    'id': 'gid://shopify/InventoryItem/1',
                    'sku': 'STALE-NESTED-SKU',
                    'tracked': True,
                },
            }]},
        }
        binding = self.Service._bind_created_product(
            self.store, preview, product,
        )
        variant_binding = self.VariantBinding.sudo().search([
            ('store_id', '=', self.store.id),
            ('product_variant_id', '=', self.variant.id),
        ])
        self.assertEqual(variant_binding.shopify_gid, VARIANT_GID)
        self.assertEqual(variant_binding.shopify_sku_snapshot, 'WIDGET-1')
        self.assertEqual(
            variant_binding.shopify_inventory_item_gid,
            'gid://shopify/InventoryItem/1',
        )
        self.assertTrue(variant_binding.shopify_inventory_tracked)
        self.assertTrue(variant_binding.shopify_inventory_tracked_known)
        # Finalization is replay-safe: the same response updates the one
        # binding and never creates a second row.
        self.Service._bind_created_product(self.store, preview, product)
        self.assertEqual(self.TemplateBinding.search_count([
            ('store_id', '=', self.store.id),
            ('product_template_id', '=', self.template.id),
        ]), 1)
        self.assertEqual(self.VariantBinding.search_count([
            ('store_id', '=', self.store.id),
            ('product_variant_id', '=', self.variant.id),
        ]), 1)

    def test_create_finalization_rejects_duplicate_remote_sku_atomically(self):
        extra = self.env['product.product'].create({
            'product_tmpl_id': self.template.id,
            'default_code': 'WIDGET-1',
            'barcode': '0002',
        })
        preview = self.make_preview(export_path='create')
        remote_variants = [{
            'id': VARIANT_GID,
            'sku': 'WIDGET-1',
            'barcode': '0001',
            'inventoryItem': {'id': 'gid://shopify/InventoryItem/1'},
        }, {
            'id': 'gid://shopify/ProductVariant/duplicate',
            'sku': 'WIDGET-1',
            'barcode': '0002',
            'inventoryItem': {'id': 'gid://shopify/InventoryItem/2'},
        }]
        with self.assertRaises(JobHandlerError):
            self.Service._bind_created_product(
                self.store, preview, {
                    'id': PRODUCT_GID,
                    'title': 'Exportable Widget',
                    'variants': {'nodes': remote_variants},
                },
            )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id),
            ('product_template_id', '=', self.template.id),
        ]))
        self.assertFalse(self.VariantBinding.search([
            ('store_id', '=', self.store.id),
            ('product_variant_id', 'in', [self.variant.id, extra.id]),
        ]))
