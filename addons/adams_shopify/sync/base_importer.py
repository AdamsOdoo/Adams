import logging

from psycopg2 import IntegrityError

from odoo import fields

_logger = logging.getLogger(__name__)


class BaseImporter:
    """Base class for Shopify → Odoo import sync operations."""

    entity_name = ''  # Override: 'product', 'customer', etc.
    binding_model = ''  # Override: 'shopify.product.binding'

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        from ..shopify_api.client import ShopifyClient
        self.client = ShopifyClient(backend)

    def _create_log(self, operation='import'):
        return self.env['shopify.sync.log'].create({
            'backend_id': self.backend.id,
            'entity': self.entity_name,
            'operation': operation,
        })

    def _find_binding(self, shopify_id):
        """Find existing binding by shopify_id."""
        return self.env[self.binding_model].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', shopify_id),
        ], limit=1)

    def import_batch(self, shopify_nodes):
        """Import a batch of Shopify nodes.

        Args:
            shopify_nodes: iterable of Shopify GraphQL node dicts.

        Returns:
            Tuple of (success, errors, skipped) counts.
        """
        log = self._create_log()
        success = errors = skipped = 0
        error_details = []

        for node in shopify_nodes:
            shopify_id = node.get('id', '')
            try:
                new_checksum = self._compute_shopify_checksum(node)
                binding = self._find_binding(shopify_id)

                if binding and new_checksum == binding.sync_checksum:
                    skipped += 1
                    continue

                self._import_one(node, binding)
                success += 1
            except IntegrityError:
                self.env.cr.rollback()
                _logger.info("Duplicate binding for %s %s — skipping", self.entity_name, shopify_id)
                skipped += 1
            except Exception as e:
                _logger.warning(
                    "Import failed for %s %s: %s",
                    self.entity_name, shopify_id, e,
                )
                errors += 1
                error_details.append(f"{shopify_id}: {e}")

        log._finalize(success, errors, skipped, '\n'.join(error_details) or None)
        return success, errors, skipped

    def _compute_shopify_checksum(self, node):
        """Override: compute checksum from Shopify data."""
        raise NotImplementedError

    def _import_one(self, node, existing_binding=None):
        """Override: import a single Shopify node into Odoo."""
        raise NotImplementedError
