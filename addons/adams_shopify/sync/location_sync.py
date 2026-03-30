import logging

from ..shopify_api.queries.location import FETCH_LOCATIONS

_logger = logging.getLogger(__name__)


class LocationSync:
    """Sync Shopify locations to map inventory to warehouses."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        from ..shopify_api.client import ShopifyClient
        self.client = ShopifyClient(backend)

    def import_locations(self):
        """Fetch all locations from Shopify and create/update records."""
        nodes = self.client.fetch_paginated(
            FETCH_LOCATIONS, 'locations',
            page_size=50,
            estimated_cost_per_page=5,
        )

        success = errors = 0
        for node in nodes:
            shopify_loc_id = node.get('id', '')
            try:
                existing = self.env['shopify.location'].search([
                    ('backend_id', '=', self.backend.id),
                    ('shopify_location_id', '=', shopify_loc_id),
                ], limit=1)

                address_data = node.get('address', {})
                vals = {
                    'name': node.get('name', ''),
                    'address': address_data.get('address1', ''),
                    'city': address_data.get('city', ''),
                    'country_code': address_data.get('countryCode', ''),
                    'is_active': node.get('isActive', True),
                    'is_primary': node.get('isPrimary', False),
                }

                if existing:
                    existing.write(vals)
                else:
                    vals.update({
                        'backend_id': self.backend.id,
                        'shopify_location_id': shopify_loc_id,
                    })
                    loc = self.env['shopify.location'].create(vals)
                    if loc.is_primary and self.backend.warehouse_id:
                        loc.warehouse_id = self.backend.warehouse_id
                success += 1
            except Exception as e:
                _logger.warning("Failed to import location %s: %s", shopify_loc_id, e)
                errors += 1

        return success, errors
