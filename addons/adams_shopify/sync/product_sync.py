import base64
import logging
import requests

from odoo import fields

from .base_exporter import BaseExporter
from .base_importer import BaseImporter
from .checksum import product_checksum, shopify_product_checksum
from ..shopify_api.queries.product import (
    FETCH_PRODUCTS,
    PRODUCT_CREATE_MUTATION,
    PRODUCT_UPDATE_MUTATION,
    VARIANT_BULK_UPDATE_MUTATION,
)

_logger = logging.getLogger(__name__)


class ProductExporter(BaseExporter):
    entity_name = 'product'
    binding_model = 'shopify.product.binding'

    def _compute_checksum(self, binding):
        return product_checksum(binding.odoo_id)

    def _get_variant_price(self, variant):
        """Get variant price using backend pricelist if configured, else lst_price."""
        pricelist = self.backend.pricelist_id
        if pricelist:
            return pricelist._get_product_price(variant, 1.0)
        return variant.lst_price

    def _export_one(self, binding):
        product = binding.odoo_id
        if binding.shopify_id:
            self._update_product(binding, product)
        else:
            self._create_product(binding, product)

    def _create_product(self, binding, product):
        variables = {
            'input': {
                'title': product.name,
                'bodyHtml': product.description_sale or '',
                'productType': product.categ_id.name or '',
                'vendor': product.seller_ids[:1].partner_id.name if product.seller_ids else '',
                'status': 'ACTIVE',
                'tags': binding.shopify_tags.split(', ') if binding.shopify_tags else [],
                'variants': self._build_variant_inputs(product),
            },
        }
        result = self.client.execute_mutation(
            PRODUCT_CREATE_MUTATION,
            variables,
            result_key='productCreate',
            estimated_cost=10,
        )
        shopify_product = result.get('product', {})
        binding.shopify_id = shopify_product.get('id')
        binding.shopify_handle = shopify_product.get('handle', '')
        binding.shopify_status = 'active'

        # Create variant bindings
        shopify_variants = shopify_product.get('variants', {}).get('edges', [])
        self._sync_variant_bindings(binding, product, shopify_variants)

    def _update_product(self, binding, product):
        shopify_gid = binding.shopify_id
        variables = {
            'input': {
                'id': shopify_gid,
                'title': product.name,
                'bodyHtml': product.description_sale or '',
                'productType': product.categ_id.name or '',
                'tags': binding.shopify_tags.split(', ') if binding.shopify_tags else [],
            },
        }
        self.client.execute_mutation(
            PRODUCT_UPDATE_MUTATION,
            variables,
            result_key='productUpdate',
            estimated_cost=10,
        )

        # Update variants
        variant_inputs = []
        for variant in product.product_variant_ids:
            vbinding = self.env['shopify.variant.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('odoo_id', '=', variant.id),
            ], limit=1)
            if vbinding and vbinding.shopify_id:
                variant_inputs.append({
                    'id': vbinding.shopify_id,
                    'sku': variant.default_code or '',
                    'price': str(self._get_variant_price(variant)),
                    'barcode': variant.barcode or None,
                })

        if variant_inputs:
            self.client.execute_mutation(
                VARIANT_BULK_UPDATE_MUTATION,
                {'productId': shopify_gid, 'variants': variant_inputs},
                result_key='productVariantsBulkUpdate',
                estimated_cost=10,
            )

    def _build_variant_inputs(self, product):
        variants = []
        for v in product.product_variant_ids:
            variants.append({
                'sku': v.default_code or '',
                'price': str(self._get_variant_price(v)),
                'barcode': v.barcode or None,
                'weight': v.weight,
                'weightUnit': 'KILOGRAMS',
            })
        if not variants:
            pricelist = self.backend.pricelist_id
            price = pricelist._get_product_price(
                product.product_variant_ids[:1], 1.0,
            ) if pricelist and product.product_variant_ids else product.list_price
            return [{'price': str(price)}]
        return variants

    def _sync_variant_bindings(self, product_binding, product, shopify_variants):
        """Create variant bindings from Shopify response after product create."""
        odoo_variants = product.product_variant_ids
        for i, edge in enumerate(shopify_variants):
            sv = edge.get('node', {})
            odoo_variant = odoo_variants[i] if i < len(odoo_variants) else odoo_variants[-1:]
            if not odoo_variant:
                continue
            inv_item = sv.get('inventoryItem', {})
            self.env['shopify.variant.binding'].create({
                'backend_id': self.backend.id,
                'odoo_id': odoo_variant.id if hasattr(odoo_variant, 'id') else odoo_variant.ids[0],
                'shopify_id': sv.get('id'),
                'product_binding_id': product_binding.id,
                'shopify_inventory_item_id': inv_item.get('id', ''),
                'shopify_sku': sv.get('sku', ''),
                'sync_status': 'synced',
                'last_sync_date': fields.Datetime.now(),
            })


class ProductImporter(BaseImporter):
    entity_name = 'product'
    binding_model = 'shopify.product.binding'

    def _compute_shopify_checksum(self, node):
        return shopify_product_checksum(node)

    def _import_one(self, node, existing_binding=None):
        shopify_id = node.get('id')
        vals = self._map_to_odoo(node)
        checksum = self._compute_shopify_checksum(node)

        # Build tags string
        tags = node.get('tags', [])
        if isinstance(tags, list):
            shopify_tags = ', '.join(tags)
        else:
            shopify_tags = tags or ''

        if existing_binding:
            existing_binding.odoo_id.with_context(shopify_no_auto_export=True).write(vals)
            existing_binding.write({'shopify_tags': shopify_tags})
            existing_binding._mark_synced(checksum=checksum)
            self._import_variants(existing_binding, node)
            self._import_images(existing_binding.odoo_id, node)
        else:
            # Try to match by SKU first
            product = self._find_odoo_product(node)
            if not product:
                product = self.env['product.template'].with_context(
                    shopify_no_auto_export=True,
                ).create(vals)
            else:
                product.with_context(shopify_no_auto_export=True).write(vals)

            binding = self.env['shopify.product.binding'].create({
                'backend_id': self.backend.id,
                'odoo_id': product.id,
                'shopify_id': shopify_id,
                'shopify_handle': node.get('handle', ''),
                'shopify_status': (node.get('status', 'ACTIVE')).lower(),
                'shopify_product_type': node.get('productType', ''),
                'shopify_tags': shopify_tags,
                'sync_status': 'synced',
                'sync_checksum': checksum,
                'last_sync_date': fields.Datetime.now(),
            })
            self._import_variants(binding, node)
            self._import_images(product, node)

    def _map_to_odoo(self, node):
        tags = node.get('tags', [])
        if isinstance(tags, list):
            tags = ', '.join(tags)

        first_variant = {}
        variant_edges = node.get('variants', {}).get('edges', [])
        if variant_edges:
            first_variant = variant_edges[0].get('node', {})

        vals = {
            'name': node.get('title', 'Untitled'),
            'description_sale': node.get('bodyHtml', ''),
            'list_price': float(first_variant.get('price', 0)),
            'default_code': first_variant.get('sku', ''),
            'barcode': first_variant.get('barcode') or False,
            'weight': first_variant.get('weight', 0),
        }

        # Download main image from first image node
        image_edges = node.get('images', {}).get('edges', [])
        if image_edges:
            image_url = image_edges[0].get('node', {}).get('url') or \
                        image_edges[0].get('node', {}).get('originalSrc')
            if image_url:
                try:
                    resp = requests.get(image_url, timeout=15)
                    if resp.status_code == 200:
                        vals['image_1920'] = base64.b64encode(resp.content).decode('utf-8')
                except Exception:
                    _logger.warning("Failed to download product image from %s", image_url)

        return vals

    def _find_odoo_product(self, node):
        """Try to match an existing Odoo product by SKU."""
        variant_edges = node.get('variants', {}).get('edges', [])
        if variant_edges:
            sku = variant_edges[0].get('node', {}).get('sku', '')
            if sku:
                variant = self.env['product.product'].search([
                    ('default_code', '=', sku),
                ], limit=1)
                if variant:
                    return variant.product_tmpl_id
        return None

    def _import_variants(self, product_binding, node):
        """Create/update variant bindings from Shopify data."""
        variant_edges = node.get('variants', {}).get('edges', [])
        odoo_variants = product_binding.odoo_id.product_variant_ids

        for i, edge in enumerate(variant_edges):
            sv = edge.get('node', {})
            shopify_vid = sv.get('id')

            existing_vb = self.env['shopify.variant.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('shopify_id', '=', shopify_vid),
            ], limit=1)

            odoo_variant = odoo_variants[i] if i < len(odoo_variants) else False
            if not odoo_variant:
                continue

            inv_item = sv.get('inventoryItem', {})

            if existing_vb:
                existing_vb._mark_synced()
            else:
                self.env['shopify.variant.binding'].create({
                    'backend_id': self.backend.id,
                    'odoo_id': odoo_variant.id,
                    'shopify_id': shopify_vid,
                    'product_binding_id': product_binding.id,
                    'shopify_inventory_item_id': inv_item.get('id', ''),
                    'shopify_sku': sv.get('sku', ''),
                    'sync_status': 'synced',
                    'last_sync_date': fields.Datetime.now(),
                })


    def _import_images(self, product, node):
        """Import additional product images (beyond the first) as product.image records."""
        image_edges = node.get('images', {}).get('edges', [])
        if len(image_edges) <= 1:
            return  # First image already set as image_1920 via _map_to_odoo

        for edge in image_edges[1:]:
            image_node = edge.get('node', {})
            image_url = image_node.get('url') or image_node.get('originalSrc')
            if not image_url:
                continue
            try:
                resp = requests.get(image_url, timeout=15)
                if resp.status_code == 200:
                    image_data = base64.b64encode(resp.content).decode('utf-8')
                    # Check if product.image model exists (requires product_images module)
                    if 'product.image' in self.env:
                        self.env['product.image'].create({
                            'product_tmpl_id': product.id,
                            'name': image_node.get('altText') or product.name,
                            'image_1920': image_data,
                        })
            except Exception:
                _logger.warning("Failed to download additional product image from %s", image_url)


class ProductSync:
    """Orchestrates bidirectional product sync."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.exporter = ProductExporter(env, backend)
        self.importer = ProductImporter(env, backend)

    def export_products(self):
        return self.exporter.export_batch()

    def import_products(self):
        nodes = self.importer.client.fetch_paginated(
            FETCH_PRODUCTS, 'products',
            page_size=self.backend.batch_size,
            estimated_cost_per_page=12,
        )
        return self.importer.import_batch(nodes)

    def import_single_product(self, webhook_data):
        """Import a single product from webhook payload (REST format)."""
        shopify_id = f"gid://shopify/Product/{webhook_data.get('id', '')}"
        # Webhook data is REST format — fetch fresh GraphQL data
        # for consistent field mapping
        try:
            from ..shopify_api.client import ShopifyClient
            client = ShopifyClient(self.backend)
            query = """
            query GetProduct($id: ID!) {
              product(id: $id) {
                id title bodyHtml vendor productType tags status handle
                createdAt updatedAt
                variants(first: 100) {
                  edges {
                    node {
                      id title sku barcode price compareAtPrice
                      weight weightUnit inventoryQuantity
                      inventoryItem { id }
                    }
                  }
                }
              }
            }
            """
            body = client.execute(query, {'id': shopify_id}, estimated_cost=5)
            node = body.get('data', {}).get('product')
            if node:
                binding = self.importer._find_binding(shopify_id)
                self.importer._import_one(node, binding)
        except Exception:
            _logger.exception("Failed to import product from webhook: %s", shopify_id)
