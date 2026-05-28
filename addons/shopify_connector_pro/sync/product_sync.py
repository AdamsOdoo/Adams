# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import base64
import logging
import requests
from urllib.parse import urlparse

from odoo import fields

from .base_exporter import BaseExporter
from .base_importer import BaseImporter
from .checksum import product_checksum, shopify_product_checksum
from ..shopify_api.queries.product import (
    FETCH_PRODUCTS,
    PRODUCT_CREATE_MUTATION,
    PRODUCT_SET_MUTATION,
    PRODUCT_UPDATE_MUTATION,
    VARIANT_BULK_UPDATE_MUTATION,
)

# Allowed domains for image downloads (SSRF prevention)
_ALLOWED_IMAGE_DOMAINS = {
    'cdn.shopify.com',
    'cdn.shopifycdn.net',
    'burst.shopifycdn.com',
}

_logger = logging.getLogger(__name__)


def _validate_image_url(url):
    """Validate that an image URL points to an allowed Shopify CDN domain.

    Returns True if the URL is safe to download, False otherwise.
    Prevents SSRF by restricting downloads to known Shopify domains.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('https', 'http'):
            return False
        hostname = parsed.hostname or ''
        # Allow exact matches and subdomains
        for allowed in _ALLOWED_IMAGE_DOMAINS:
            if hostname == allowed or hostname.endswith('.' + allowed):
                return True
        return False
    except Exception:
        return False


class ProductExporter(BaseExporter):
    entity_name = 'product'
    binding_model = 'shopify.product.binding'

    def _compute_checksum(self, binding):
        return product_checksum(binding.odoo_id)

    def _get_variant_price(self, variant):
        """Get variant price using backend pricelist if configured, else lst_price."""
        pricelist = self.backend.pricelist_id
        if pricelist and variant:
            try:
                return pricelist._get_product_price(
                    variant, 1.0, currency=pricelist.currency_id,
                )
            except TypeError:
                # Older Odoo versions without currency kwarg
                return pricelist._get_product_price(variant, 1.0)
        return variant.lst_price

    def _export_one(self, binding):
        product = binding.odoo_id
        if binding.shopify_id:
            self._update_product(binding, product)
        else:
            self._create_product(binding, product)

    def _create_product(self, binding, product):
        """Create a product on Shopify using productSet (2026-01 compatible).

        productSet accepts product data, variants, options, and files in a
        single mutation, replacing the deprecated embedded variants/images
        arrays in productCreate.
        """
        product_input = {
            'title': product.name,
            'descriptionHtml': product.description_sale or '',
            'productType': product.categ_id.name or '',
            'vendor': product.seller_ids[:1].partner_id.name if product.seller_ids else '',
            'status': 'ACTIVE',
            'tags': binding.shopify_tags.split(', ') if binding.shopify_tags else [],
            'variants': self._build_variant_inputs(product),
        }
        options = self._build_options(product)
        if options:
            product_input['productOptions'] = options
        variables = {'input': product_input}
        result = self.client.execute_mutation(
            PRODUCT_SET_MUTATION,
            variables,
            result_key='productSet',
            estimated_cost=15,
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
                'descriptionHtml': product.description_sale or '',
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

    def _build_options(self, product):
        """Build Shopify productOptions list from product attribute lines.

        productSet expects `productOptions: [OptionCreateInput]` where each
        option has `name` and `values: [OptionValueCreateInput]`.
        """
        options = []
        for line in product.attribute_line_ids:
            options.append({
                'name': line.attribute_id.name,
                'values': [{'name': v.name} for v in line.value_ids],
            })
        return options

    def _build_variant_inputs(self, product):
        variants = []
        for v in product.product_variant_ids:
            variant_input = {
                'sku': v.default_code or '',
                'price': str(self._get_variant_price(v)),
                'barcode': v.barcode or None,
            }
            # In 2026-01, weight moved to inventoryItem.measurement.weight
            if v.weight:
                variant_input['inventoryItem'] = {
                    'measurement': {
                        'weight': {
                            'value': float(v.weight),
                            'unit': 'KILOGRAMS',
                        },
                    },
                }
            # Add option values from variant attributes
            option_values = []
            for ptav in v.product_template_attribute_value_ids:
                option_values.append({
                    'optionName': ptav.attribute_id.name,
                    'name': ptav.name,
                })
            if option_values:
                variant_input['optionValues'] = option_values
            variants.append(variant_input)
        if not variants:
            first_variant = (
                product.product_variant_ids[0] if product.product_variant_ids else None
            )
            price = (
                self._get_variant_price(first_variant) if first_variant
                else product.list_price
            )
            return [{'price': str(price)}]
        return variants

    def _build_image_inputs(self, product):
        """Build Shopify image inputs from Odoo product images.

        Uses Odoo's web/image controller URL so Shopify can fetch the image.
        Only works if the Odoo instance is publicly accessible (which it
        must be for webhooks anyway).
        """
        images = []
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if not base_url:
            return images

        # Main product image
        if product.image_1920:
            url = f"{base_url}/web/image/product.template/{product.id}/image_1920"
            images.append({'src': url, 'altText': product.name})

        # Extra product images (product.image model)
        if 'product.image' in self.env:
            for img in product.product_template_image_ids:
                if img.image_1920:
                    url = f"{base_url}/web/image/product.image/{img.id}/image_1920"
                    images.append({'src': url, 'altText': img.name or product.name})

        return images

    def _sync_variant_bindings(self, product_binding, product, shopify_variants):
        """Create variant bindings from Shopify response after product create."""
        odoo_variants = product.product_variant_ids
        for i, edge in enumerate(shopify_variants):
            sv = edge.get('node', {})
            odoo_variant = odoo_variants[i] if i < len(odoo_variants) else odoo_variants[-1]
            if not odoo_variant:
                continue
            inv_item = sv.get('inventoryItem', {})
            self.env['shopify.variant.binding'].create({
                'backend_id': self.backend.id,
                'odoo_id': odoo_variant.id,
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
            self._import_attributes(existing_binding.odoo_id, node)
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

            self._import_attributes(product, node)

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

        # Extract weight from inventoryItem.measurement.weight (2026-01 shape)
        inv_item = first_variant.get('inventoryItem') or {}
        measurement = inv_item.get('measurement') or {}
        weight_data = measurement.get('weight') or {}
        weight = float(weight_data.get('value', 0) or 0)

        vals = {
            'name': node.get('title', 'Untitled'),
            'description_sale': node.get('descriptionHtml', ''),
            'list_price': float(first_variant.get('price', 0)),
            'default_code': first_variant.get('sku', ''),
            'barcode': first_variant.get('barcode') or False,
            'weight': weight,
        }

        # Download main image from first image node
        image_edges = node.get('images', {}).get('edges', [])
        if image_edges:
            image_url = image_edges[0].get('node', {}).get('url') or \
                        image_edges[0].get('node', {}).get('originalSrc')
            if image_url:
                if not _validate_image_url(image_url):
                    _logger.warning("Blocked image download from untrusted domain: %s",
                                    urlparse(image_url).hostname)
                else:
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

    def _import_attributes(self, product, node):
        """Create product attribute lines from Shopify options data."""
        options = node.get('options', [])
        if not options:
            return

        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']

        for option in options:
            option_name = option.get('name', '')
            option_values = option.get('values', [])
            if not option_name or not option_values:
                continue

            # Find or create the attribute
            attribute = ProductAttribute.search([('name', '=ilike', option_name)], limit=1)
            if not attribute:
                attribute = ProductAttribute.create({'name': option_name})

            # Find or create attribute values
            value_ids = []
            for val_name in option_values:
                attr_value = ProductAttributeValue.search([
                    ('attribute_id', '=', attribute.id),
                    ('name', '=ilike', val_name),
                ], limit=1)
                if not attr_value:
                    attr_value = ProductAttributeValue.create({
                        'attribute_id': attribute.id,
                        'name': val_name,
                    })
                value_ids.append(attr_value.id)

            # Check if attribute line already exists on this product
            existing_line = product.attribute_line_ids.filtered(
                lambda l: l.attribute_id.id == attribute.id
            )
            if existing_line:
                # Add any new values to the existing line
                existing_value_ids = set(existing_line.value_ids.ids)
                new_value_ids = set(value_ids)
                if not new_value_ids.issubset(existing_value_ids):
                    existing_line.write({'value_ids': [(4, vid) for vid in new_value_ids - existing_value_ids]})
            else:
                self.env['product.template.attribute.line'].with_context(
                    shopify_no_auto_export=True,
                ).create({
                    'product_tmpl_id': product.id,
                    'attribute_id': attribute.id,
                    'value_ids': [(6, 0, value_ids)],
                })

    def _match_variant_by_options(self, odoo_variants, selected_options):
        """Match an Odoo variant by its attribute values against Shopify selectedOptions."""
        if not selected_options:
            return False
        for variant in odoo_variants:
            ptav_map = {
                ptav.attribute_id.name.lower(): ptav.name.lower()
                for ptav in variant.product_template_attribute_value_ids
            }
            if not ptav_map:
                continue
            match = all(
                ptav_map.get(opt.get('name', '').lower()) == opt.get('value', '').lower()
                for opt in selected_options
            )
            if match:
                return variant
        return False

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

            # Try matching by selectedOptions first, fall back to index
            selected_options = sv.get('selectedOptions', [])
            odoo_variant = self._match_variant_by_options(odoo_variants, selected_options)
            if not odoo_variant:
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
            if not _validate_image_url(image_url):
                _logger.warning("Blocked image download from untrusted domain: %s",
                                urlparse(image_url).hostname)
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
            client = self.backend._make_api_client()
            query = """
            query GetProduct($id: ID!) {
              product(id: $id) {
                id title descriptionHtml vendor productType tags status handle
                createdAt updatedAt
                options { name values }
                images(first: 20) {
                  edges {
                    node {
                      url
                      altText
                    }
                  }
                }
                variants(first: 250) {
                  edges {
                    node {
                      id title sku barcode price compareAtPrice
                      inventoryQuantity
                      inventoryItem {
                        id
                        measurement {
                          weight { value unit }
                        }
                      }
                      selectedOptions { name value }
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
