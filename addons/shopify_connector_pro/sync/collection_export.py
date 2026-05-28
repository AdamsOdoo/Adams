# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields

from .checksum import compute_checksum
from ..shopify_api.queries.collection import COLLECTION_CREATE_MUTATION

_logger = logging.getLogger(__name__)


class CollectionExporter:
    """Export Odoo product categories to Shopify as collections."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.client = backend._make_api_client()

    def export_collections(self):
        """Export all collection bindings that need syncing."""
        bindings = self.env['shopify.collection.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('sync_status', 'in', ['pending', 'error']),
            ('retry_count', '<', 5),
        ], limit=self.backend.batch_size)

        log = self.env['shopify.sync.log'].create({
            'backend_id': self.backend.id,
            'entity': 'collection',
            'operation': 'export',
        })
        success = errors = skipped = 0
        error_details = []

        for binding in bindings:
            try:
                category = binding.odoo_id
                checksum = compute_checksum({'name': category.name})

                if checksum == binding.sync_checksum:
                    skipped += 1
                    continue

                if binding.shopify_id:
                    # Update not yet supported — skip without marking
                    # synced to avoid false confidence (BUG-EW-01a)
                    _logger.debug(
                        "Collection update not yet supported, skipping %s",
                        binding.shopify_id,
                    )
                    skipped += 1
                    continue

                # Create new collection
                result = self.client.execute_mutation(
                    COLLECTION_CREATE_MUTATION,
                    {'input': {
                        'title': category.name,
                        'descriptionHtml': '',
                    }},
                    result_key='collectionCreate',
                    estimated_cost=10,
                )
                collection = result.get('collection', {})
                binding.shopify_id = collection.get('id', '')
                binding.shopify_handle = collection.get('handle', '')
                binding.shopify_title = category.name
                binding._mark_synced(checksum=checksum)
                success += 1

            except Exception as e:
                _logger.warning("Collection export failed for %s: %s", binding.id, e)
                binding._mark_error(str(e))
                errors += 1
                error_details.append(f"{binding.odoo_id.name}: {e}")

        log._finalize(success, errors, skipped, '\n'.join(error_details) or None)
        return success, errors, skipped
