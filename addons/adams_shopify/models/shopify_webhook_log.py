import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ShopifyWebhookLog(models.Model):
    _name = 'shopify.webhook.log'
    _description = 'Shopify Webhook Log'
    _order = 'received_at desc'

    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
    )
    webhook_id = fields.Char('Shopify Webhook ID', index=True)
    topic = fields.Char(required=True, index=True)
    shopify_id = fields.Char('Resource Shopify ID')
    payload = fields.Text()
    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error'),
        ('skipped', 'Skipped'),
    ], default='pending', index=True)
    error_message = fields.Text()
    received_at = fields.Datetime(default=fields.Datetime.now)
    processed_at = fields.Datetime()

    _sql_constraints = [
        ('unique_webhook_id', 'UNIQUE(webhook_id)',
         'This webhook event has already been received.'),
    ]

    @api.model
    def _cron_process_pending(self):
        """Process pending webhook events in batches."""
        pending = self.search([('state', '=', 'pending')], limit=100, order='received_at asc')
        for log in pending:
            try:
                log.state = 'processing'
                log.flush_recordset()
                log._process_event()
                log.write({
                    'state': 'done',
                    'processed_at': fields.Datetime.now(),
                })
            except Exception as e:
                _logger.exception("Webhook processing failed for %s", log.id)
                log.write({
                    'state': 'error',
                    'error_message': str(e),
                    'processed_at': fields.Datetime.now(),
                })
            # Commit after each event to release locks and ensure progress
            self.env.cr.commit()  # noqa: E501

    def _process_event(self):
        """Dispatch webhook event to the appropriate handler."""
        self.ensure_one()
        import json
        data = json.loads(self.payload) if self.payload else {}
        topic = self.topic

        handler_map = {
            'products/create': '_handle_product_webhook',
            'products/update': '_handle_product_webhook',
            'products/delete': '_handle_product_delete_webhook',
            'orders/create': '_handle_order_webhook',
            'orders/updated': '_handle_order_webhook',
            'orders/cancelled': '_handle_order_cancel_webhook',
            'customers/create': '_handle_customer_webhook',
            'customers/update': '_handle_customer_webhook',
            'inventory_levels/update': '_handle_inventory_webhook',
            'fulfillments/create': '_handle_fulfillment_webhook',
            'app/uninstalled': '_handle_app_uninstalled',
        }

        method_name = handler_map.get(topic)
        if method_name:
            getattr(self, method_name)(data)
        else:
            _logger.info("No handler for webhook topic: %s", topic)
            self.state = 'skipped'

    def _handle_product_webhook(self, data):
        self.env['shopify.product.binding'].process_webhook_event(
            self.backend_id, data, self.topic,
        )

    def _handle_product_delete_webhook(self, data):
        shopify_gid = f"gid://shopify/Product/{data.get('id', '')}"
        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend_id.id),
            ('shopify_id', '=', shopify_gid),
        ], limit=1)
        if binding:
            binding.write({'sync_status': 'permanent_error', 'sync_error': 'Deleted on Shopify'})

    def _handle_order_webhook(self, data):
        self.env['shopify.order.binding'].process_webhook_event(
            self.backend_id, data, self.topic,
        )

    def _handle_order_cancel_webhook(self, data):
        shopify_gid = f"gid://shopify/Order/{data.get('id', '')}"
        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend_id.id),
            ('shopify_id', '=', shopify_gid),
        ], limit=1)
        if binding and binding.odoo_id:
            binding.odoo_id.with_context(disable_cancel_warning=True).action_cancel()

    def _handle_customer_webhook(self, data):
        self.env['shopify.customer.binding'].process_webhook_event(
            self.backend_id, data, self.topic,
        )

    def _handle_inventory_webhook(self, data):
        _logger.info("Inventory webhook received — skipping (Odoo is source of truth)")
        self.state = 'skipped'

    def _handle_fulfillment_webhook(self, data):
        _logger.info("Fulfillment webhook received for backend %s", self.backend_id.id)

    def _handle_app_uninstalled(self, data):
        _logger.warning("App uninstalled webhook for backend %s", self.backend_id.id)
        self.backend_id.write({'state': 'error'})
