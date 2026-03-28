import logging

from odoo import fields

_logger = logging.getLogger(__name__)


class BaseExporter:
    """Base class for Odoo → Shopify export sync operations."""

    entity_name = ''  # Override: 'product', 'customer', etc.
    binding_model = ''  # Override: 'shopify.product.binding'

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        from ..shopify_api.client import ShopifyClient
        self.client = ShopifyClient(backend)

    def _get_bindings_to_export(self):
        """Get bindings that need to be exported (pending or error with retry < 5)."""
        return self.env[self.binding_model].search([
            ('backend_id', '=', self.backend.id),
            ('sync_status', 'in', ['pending', 'error']),
            ('retry_count', '<', 5),
            ('no_sync', '=', False) if 'no_sync' in self.env[self.binding_model]._fields else ('id', '!=', 0),
        ], limit=self.backend.batch_size)

    def _create_log(self, operation='export'):
        return self.env['shopify.sync.log'].create({
            'backend_id': self.backend.id,
            'entity': self.entity_name,
            'operation': operation,
        })

    def export_batch(self, bindings=None):
        """Export a batch of bindings. Returns (success, errors, skipped) counts."""
        if bindings is None:
            bindings = self._get_bindings_to_export()

        log = self._create_log()
        success = errors = skipped = 0
        error_details = []

        for binding in bindings:
            try:
                new_checksum = self._compute_checksum(binding)
                if new_checksum == binding.sync_checksum:
                    skipped += 1
                    continue

                self._export_one(binding)
                binding._mark_synced(checksum=new_checksum)
                success += 1
            except Exception as e:
                _logger.warning(
                    "Export failed for %s binding %s: %s",
                    self.entity_name, binding.id, e,
                )
                binding._mark_error(str(e))
                errors += 1
                error_details.append(f"{binding.odoo_id.display_name}: {e}")

        log._finalize(success, errors, skipped, '\n'.join(error_details) or None)
        return success, errors, skipped

    def _compute_checksum(self, binding):
        """Override: compute checksum for the Odoo record."""
        raise NotImplementedError

    def _export_one(self, binding):
        """Override: export a single binding to Shopify."""
        raise NotImplementedError
