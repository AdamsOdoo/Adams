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
        errors_found += self._reconcile_payment_status(backend)
        errors_found += self._reconcile_fulfillment_status(backend)

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

    # ── Payment Status Reconciliation ──────────────────────

    def _reconcile_payment_status(self, backend):
        """Check that Odoo invoice state matches Shopify financial status.

        For recent orders (within reconciliation_order_days), compare:
        - binding.shopify_financial_status vs invoice state
        - Flag mismatches as sync log warnings
        """
        days = backend.reconciliation_order_days or 30
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        errors = 0

        # Orders marked as paid on Shopify but no posted invoice in Odoo
        paid_bindings = self.env['shopify.order.binding'].search([
            ('backend_id', '=', backend.id),
            ('shopify_financial_status', '=', 'paid'),
            ('sync_status', '=', 'synced'),
            ('create_date', '>=', cutoff),
        ])

        missing_invoice_count = 0
        for binding in paid_bindings:
            order = binding.odoo_id
            if not order:
                continue
            posted_invoices = order.invoice_ids.filtered(
                lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
            )
            if not posted_invoices:
                missing_invoice_count += 1
                _logger.warning(
                    "Payment mismatch: Shopify order %s is 'paid' but no posted "
                    "invoice in Odoo (order: %s)",
                    binding.shopify_order_name, order.name,
                )

        if missing_invoice_count:
            self.env['shopify.sync.log'].create({
                'backend_id': backend.id,
                'entity': 'order',
                'operation': 'import',
                'state': 'partial',
                'total_records': missing_invoice_count,
                'error_count': missing_invoice_count,
                'error_details': (
                    f"Reconciliation: {missing_invoice_count} orders marked as 'paid' "
                    f"on Shopify but missing a posted invoice in Odoo. "
                    f"These may need manual invoice creation."
                ),
                'started_at': fields.Datetime.now(),
                'finished_at': fields.Datetime.now(),
            })
            errors += 1

        # Orders with refund status but no credit note
        refund_bindings = self.env['shopify.order.binding'].search([
            ('backend_id', '=', backend.id),
            ('shopify_financial_status', 'in', ['refunded', 'partially_refunded']),
            ('sync_status', '=', 'synced'),
            ('create_date', '>=', cutoff),
        ])

        missing_credit_count = 0
        for binding in refund_bindings:
            order = binding.odoo_id
            if not order:
                continue
            credit_notes = order.invoice_ids.filtered(
                lambda i: i.move_type == 'out_refund'
            )
            refund_bindings_exist = self.env['shopify.refund.binding'].search_count([
                ('order_binding_id', '=', binding.id),
            ])
            if not credit_notes and not refund_bindings_exist:
                missing_credit_count += 1

        if missing_credit_count:
            self.env['shopify.sync.log'].create({
                'backend_id': backend.id,
                'entity': 'order',
                'operation': 'import',
                'state': 'partial',
                'total_records': missing_credit_count,
                'error_count': missing_credit_count,
                'error_details': (
                    f"Reconciliation: {missing_credit_count} orders marked as refunded "
                    f"on Shopify but no credit note or refund binding in Odoo. "
                    f"Run refund import to resolve."
                ),
                'started_at': fields.Datetime.now(),
                'finished_at': fields.Datetime.now(),
            })
            errors += 1

        # Orders with posted invoice but Shopify still shows pending/authorized
        pending_bindings = self.env['shopify.order.binding'].search([
            ('backend_id', '=', backend.id),
            ('shopify_financial_status', 'in', ['pending', 'authorized']),
            ('sync_status', '=', 'synced'),
            ('create_date', '>=', cutoff),
        ])

        premature_invoice_count = 0
        for binding in pending_bindings:
            order = binding.odoo_id
            if not order:
                continue
            posted_invoices = order.invoice_ids.filtered(
                lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
            )
            if posted_invoices:
                premature_invoice_count += 1
                _logger.warning(
                    "Payment mismatch: Shopify order %s is '%s' but has a posted "
                    "invoice in Odoo (order: %s)",
                    binding.shopify_order_name,
                    binding.shopify_financial_status, order.name,
                )

        if premature_invoice_count:
            self.env['shopify.sync.log'].create({
                'backend_id': backend.id,
                'entity': 'order',
                'operation': 'import',
                'state': 'partial',
                'total_records': premature_invoice_count,
                'error_count': premature_invoice_count,
                'error_details': (
                    f"Reconciliation: {premature_invoice_count} orders still pending/"
                    f"authorized on Shopify but have posted invoices in Odoo. "
                    f"Payment may have been captured — check Shopify admin."
                ),
                'started_at': fields.Datetime.now(),
                'finished_at': fields.Datetime.now(),
            })
            errors += 1

        return errors

    # ── Fulfillment Status Reconciliation ──────────────────

    def _reconcile_fulfillment_status(self, backend):
        """Check that Odoo delivery state matches Shopify fulfillment status."""
        days = backend.reconciliation_order_days or 30
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        errors = 0

        # Orders fulfilled on Shopify but not all pickings done in Odoo
        fulfilled_bindings = self.env['shopify.order.binding'].search([
            ('backend_id', '=', backend.id),
            ('shopify_fulfillment_status', '=', 'fulfilled'),
            ('sync_status', '=', 'synced'),
            ('create_date', '>=', cutoff),
        ])

        undelivered_count = 0
        for binding in fulfilled_bindings:
            order = binding.odoo_id
            if not order:
                continue
            out_pickings = order.picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing'
            )
            if not out_pickings:
                continue
            pending = out_pickings.filtered(lambda p: p.state not in ('done', 'cancel'))
            if pending:
                undelivered_count += 1
                _logger.warning(
                    "Fulfillment mismatch: Shopify order %s is 'fulfilled' but "
                    "picking(s) %s still pending in Odoo",
                    binding.shopify_order_name,
                    ', '.join(pending.mapped('name')),
                )

        if undelivered_count:
            self.env['shopify.sync.log'].create({
                'backend_id': backend.id,
                'entity': 'order',
                'operation': 'export',
                'state': 'partial',
                'total_records': undelivered_count,
                'error_count': undelivered_count,
                'error_details': (
                    f"Reconciliation: {undelivered_count} orders marked as 'fulfilled' "
                    f"on Shopify but have pending deliveries in Odoo. "
                    f"These may have been fulfilled externally."
                ),
                'started_at': fields.Datetime.now(),
                'finished_at': fields.Datetime.now(),
            })
            errors += 1

        # Orders with done pickings in Odoo but unfulfilled on Shopify
        unfulfilled_bindings = self.env['shopify.order.binding'].search([
            ('backend_id', '=', backend.id),
            ('shopify_fulfillment_status', '=', 'unfulfilled'),
            ('sync_status', '=', 'synced'),
            ('create_date', '>=', cutoff),
        ])

        ghost_delivery_count = 0
        for binding in unfulfilled_bindings:
            order = binding.odoo_id
            if not order:
                continue
            done_pickings = order.picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing' and p.state == 'done'
            )
            if done_pickings:
                ghost_delivery_count += 1
                _logger.warning(
                    "Fulfillment mismatch: Shopify order %s is 'unfulfilled' but "
                    "picking(s) %s are done in Odoo. Fulfillment push may have failed.",
                    binding.shopify_order_name,
                    ', '.join(done_pickings.mapped('name')),
                )

        if ghost_delivery_count:
            self.env['shopify.sync.log'].create({
                'backend_id': backend.id,
                'entity': 'order',
                'operation': 'export',
                'state': 'partial',
                'total_records': ghost_delivery_count,
                'error_count': ghost_delivery_count,
                'error_details': (
                    f"Reconciliation: {ghost_delivery_count} orders 'unfulfilled' on "
                    f"Shopify but have completed deliveries in Odoo. "
                    f"Fulfillment push may have failed — consider manual retry."
                ),
                'started_at': fields.Datetime.now(),
                'finished_at': fields.Datetime.now(),
            })
            errors += 1

        return errors
