# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from ..shopify_api.queries.metafield import (
    FETCH_PRODUCT_METAFIELDS,
    METAFIELD_SET_MUTATION,
)

_logger = logging.getLogger(__name__)


class MetafieldSync:
    """Sync metafields between Odoo and Shopify based on configured mappings."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.client = None

    def import_product_metafields(self, product_binding):
        """Import metafields for a specific product binding."""
        if not self.backend.enable_metafields:
            _logger.info(
                "Metafield import is disabled for backend %s; skipping.",
                self.backend.display_name,
            )
            return
        if not product_binding.shopify_id:
            return

        mappings = self.env['shopify.metafield.mapping'].search([
            ('backend_id', '=', self.backend.id),
            ('owner_type', '=', 'product'),
            ('direction', 'in', ['import', 'both']),
            ('active', '=', True),
        ])
        if not mappings:
            return

        self.client = self.backend._make_api_client()
        try:
            body = self.client.execute(
                FETCH_PRODUCT_METAFIELDS,
                {'productId': product_binding.shopify_id},
                estimated_cost=5,
            )
        except Exception as e:
            _logger.warning("Failed to fetch metafields for %s: %s",
                            product_binding.shopify_id, e)
            return

        metafield_edges = (
            body.get('data', {})
            .get('product', {})
            .get('metafields', {})
            .get('edges', [])
        )

        for edge in metafield_edges:
            mf = edge.get('node', {})
            namespace = mf.get('namespace', '')
            key = mf.get('key', '')

            existing = self.env['shopify.metafield'].search([
                ('backend_id', '=', self.backend.id),
                ('owner_type', '=', 'product'),
                ('owner_binding_id', '=', product_binding.id),
                ('namespace', '=', namespace),
                ('key', '=', key),
            ], limit=1)

            vals = {
                'value': mf.get('value', ''),
                'metafield_type': mf.get('type', ''),
                'shopify_metafield_id': mf.get('id', ''),
            }
            if existing:
                existing.write(vals)
            else:
                vals.update({
                    'backend_id': self.backend.id,
                    'owner_type': 'product',
                    'owner_binding_id': product_binding.id,
                    'namespace': namespace,
                    'key': key,
                })
                self.env['shopify.metafield'].create(vals)

            mapping = mappings.filtered(
                lambda m: m.shopify_namespace == namespace and m.shopify_key == key
            )
            if mapping and mapping[0].odoo_field:
                self._apply_metafield_to_odoo(
                    product_binding.odoo_id, mapping[0].odoo_field,
                    mf.get('value', ''), mapping[0].shopify_type,
                )

    def export_product_metafields(self, product_binding):
        """Export metafields from Odoo to Shopify for a product binding."""
        if not self.backend.enable_metafields:
            _logger.info(
                "Metafield export is disabled for backend %s; skipping.",
                self.backend.display_name,
            )
            return
        if not product_binding.shopify_id:
            return

        mappings = self.env['shopify.metafield.mapping'].search([
            ('backend_id', '=', self.backend.id),
            ('owner_type', '=', 'product'),
            ('direction', 'in', ['export', 'both']),
            ('active', '=', True),
        ])
        if not mappings:
            return

        metafields_input = []
        product = product_binding.odoo_id

        for mapping in mappings:
            odoo_field = mapping.odoo_field
            if odoo_field not in product._fields:
                continue
            value = product[odoo_field]
            if value is False or value is None:
                continue
            metafields_input.append({
                'ownerId': product_binding.shopify_id,
                'namespace': mapping.shopify_namespace,
                'key': mapping.shopify_key,
                'type': mapping.shopify_type,
                'value': self._serialize_metafield_value(value, mapping.shopify_type),
            })

        if not metafields_input:
            return

        self.client = self.backend._make_api_client()
        try:
            self.client.execute_mutation(
                METAFIELD_SET_MUTATION,
                {'metafields': metafields_input},
                result_key='metafieldsSet',
                estimated_cost=10,
            )
        except Exception as e:
            _logger.warning("Failed to export metafields for %s: %s",
                            product_binding.shopify_id, e)

    @staticmethod
    def _serialize_metafield_value(value, shopify_type):
        """Type-aware serialization of Python values for Shopify metafields.

        Handles booleans (True→"true"), floats (avoid repr noise),
        and falls back to str() for everything else.  (BUG-EW-02a)
        """
        if isinstance(value, bool):
            return 'true' if value else 'false'
        if isinstance(value, float):
            # Round to reasonable precision, strip trailing zeros
            return f'{value:.10g}'
        # Recordsets: use display_name
        if hasattr(value, '_name'):
            return value.display_name or ''
        return str(value)

    def _apply_metafield_to_odoo(self, record, field_name, value, mf_type):
        """Apply a metafield value to an Odoo record field."""
        if field_name not in record._fields:
            return
        try:
            field_def = record._fields[field_name]
            if field_def.type in ('integer',):
                value = int(value)
            elif field_def.type in ('float', 'monetary'):
                value = float(value)
            elif field_def.type == 'boolean':
                value = value.lower() in ('true', '1', 'yes')
            record.with_context(shopify_no_auto_export=True).write({field_name: value})
        except Exception as e:
            _logger.warning("Could not apply metafield %s to %s: %s",
                            field_name, record, e)
