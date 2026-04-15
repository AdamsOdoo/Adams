# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
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
        domain = [
            ('backend_id', '=', self.backend.id),
            ('sync_status', 'in', ['pending', 'error']),
            ('retry_count', '<', 5),
        ]
        model = self.env[self.binding_model]
        if 'no_sync' in model._fields:
            domain.append(('no_sync', '=', False))
        return model.search(domain, limit=self.backend.batch_size)

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
                is_permanent = self._is_permanent_error(e)
                binding._mark_error(str(e), permanent=is_permanent)
                errors += 1
                display = binding.odoo_id.display_name if binding.odoo_id else f'binding#{binding.id}'
                error_details.append(f"{display}: {e}")

        log._finalize(success, errors, skipped, '\n'.join(error_details) or None)
        return success, errors, skipped

    def _compute_checksum(self, binding):
        """Override: compute checksum for the Odoo record."""
        raise NotImplementedError

    def _export_one(self, binding):
        """Override: export a single binding to Shopify."""
        raise NotImplementedError

    @staticmethod
    def _is_permanent_error(exc):
        """Determine if an error should not be retried."""
        from ..shopify_api.client import ShopifyAPIError
        if isinstance(exc, ShopifyAPIError):
            # 401/403/404 are not retryable
            if exc.status_code in (401, 402, 403, 404):
                return True
            # Validation errors from Shopify are typically permanent
            if exc.user_errors:
                return True
        return False
