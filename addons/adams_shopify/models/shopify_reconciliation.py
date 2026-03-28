import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ShopifyReconciliation(models.TransientModel):
    """Detects drift between Odoo bindings and actual Shopify state.

    Run via cron to catch records that fell out of sync due to
    missed webhooks, API errors, or manual Shopify admin changes.
    """
    _name = 'shopify.reconciliation'
    _description = 'Shopify Reconciliation'

    @api.model
    def _cron_reconcile(self):
        """Reconciliation cron entry point — runs for all connected backends."""
        backends = self.env['shopify.backend'].search([
            ('state', '=', 'connected'),
        ])
        for backend in backends:
            try:
                self._reconcile_backend(backend)
            except Exception:
                _logger.exception(
                    "Reconciliation failed for backend %s", backend.id,
                )

    def _reconcile_backend(self, backend):
        """Run reconciliation checks for a single backend."""
        _logger.info("Starting reconciliation for backend %s (%s)", backend.id, backend.name)
        from ..shopify_api.client import ShopifyClient
        client = ShopifyClient(backend)

        errors_found = 0
        errors_found += self._reconcile_products(backend, client)
        errors_found += self._reconcile_stale_bindings(backend)
        errors_found += self._reconcile_retry_errors(backend)

        _logger.info(
            "Reconciliation complete for backend %s: %d issues found",
            backend.id, errors_found,
        )

    def _reconcile_products(self, backend, client):
        """Check for products that exist in Shopify but not in Odoo bindings."""
        errors = 0
        query = """
        query ProductCount {
          productsCount { count }
        }
        """
        try:
            body = client.execute(query, estimated_cost=2)
            shopify_count = body.get('data', {}).get('productsCount', {}).get('count', 0)
            odoo_count = self.env['shopify.product.binding'].search_count([
                ('backend_id', '=', backend.id),
                ('sync_status', '=', 'synced'),
            ])

            drift = abs(shopify_count - odoo_count)
            if drift > 0:
                _logger.warning(
                    "Product count drift for backend %s: Shopify=%d, Odoo=%d (drift=%d)",
                    backend.id, shopify_count, odoo_count, drift,
                )
                # Log as sync entry for visibility
                self.env['shopify.sync.log'].create({
                    'backend_id': backend.id,
                    'entity': 'product',
                    'operation': 'import',
                    'state': 'partial',
                    'total_records': drift,
                    'error_count': drift,
                    'error_details': (
                        f"Reconciliation: count mismatch. "
                        f"Shopify has {shopify_count} products, "
                        f"Odoo has {odoo_count} synced bindings. "
                        f"Consider running a full import to resolve."
                    ),
                    'started_at': fields.Datetime.now(),
                    'finished_at': fields.Datetime.now(),
                })
                errors += 1
        except Exception as e:
            _logger.warning("Product reconciliation failed: %s", e)
            errors += 1

        return errors

    def _reconcile_stale_bindings(self, backend):
        """Find bindings that haven't synced in over 24 hours while auto-sync is on."""
        errors = 0
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), hours=24)

        stale_products = self.env['shopify.product.binding'].search_count([
            ('backend_id', '=', backend.id),
            ('sync_status', '=', 'synced'),
            ('last_sync_date', '<', cutoff),
        ])

        if stale_products > 0 and backend.auto_sync_products:
            _logger.warning(
                "Backend %s has %d product bindings not synced in 24h",
                backend.id, stale_products,
            )
            errors += 1

        stale_orders = self.env['shopify.order.binding'].search_count([
            ('backend_id', '=', backend.id),
            ('sync_status', '=', 'synced'),
            ('last_sync_date', '<', cutoff),
        ])

        if stale_orders > 10 and backend.auto_sync_orders:
            _logger.warning(
                "Backend %s has %d order bindings not synced in 24h",
                backend.id, stale_orders,
            )
            errors += 1

        return errors

    def _reconcile_retry_errors(self, backend):
        """Reset retryable errors that have been stuck for too long."""
        stuck_cutoff = fields.Datetime.subtract(fields.Datetime.now(), hours=6)
        stuck_bindings = self.env['shopify.product.binding'].search([
            ('backend_id', '=', backend.id),
            ('sync_status', '=', 'error'),
            ('retry_count', '<', 5),
            ('write_date', '<', stuck_cutoff),
        ])

        if stuck_bindings:
            _logger.info(
                "Resetting %d stuck error bindings for backend %s",
                len(stuck_bindings), backend.id,
            )
            stuck_bindings.write({
                'sync_status': 'pending',
                'retry_count': 0,
            })

        return len(stuck_bindings)
