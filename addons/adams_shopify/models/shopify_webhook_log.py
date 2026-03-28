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
            # GDPR mandatory compliance webhooks
            'customers/data_request': '_handle_gdpr_data_request',
            'customers/redact': '_handle_gdpr_customer_redact',
            'shop/redact': '_handle_gdpr_shop_redact',
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

    # ── GDPR Compliance Handlers ────────────────────────────

    def _handle_gdpr_data_request(self, data):
        """Handle customers/data_request webhook.

        Shopify sends this when a customer requests their data.
        We log the request — the merchant must fulfill it manually
        through Odoo's data export tools (GDPR module or similar).
        """
        customer_email = data.get('customer', {}).get('email', 'unknown')
        shop_domain = data.get('shop_domain', '')
        _logger.info(
            "GDPR data request received for customer %s from shop %s (backend %s). "
            "Merchant must fulfill via Odoo privacy tools.",
            customer_email, shop_domain, self.backend_id.id,
        )
        # Create an activity on the backend so the admin is notified
        self.backend_id.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=f"GDPR Data Request: {customer_email}",
            note=f"Shopify customer {customer_email} has requested their personal data. "
                 f"Please export their data using Odoo's privacy tools and provide it "
                 f"to the customer through the Shopify admin.",
        )

    def _handle_gdpr_customer_redact(self, data):
        """Handle customers/redact webhook.

        Shopify sends this when a customer requests deletion.
        We must remove/anonymize their personal data from our systems.
        """
        customer_email = data.get('customer', {}).get('email', '')
        shopify_customer_id = data.get('customer', {}).get('id')
        orders_to_redact = data.get('orders_to_redact', [])

        _logger.warning(
            "GDPR customer redact for %s (Shopify ID: %s, backend %s). "
            "Anonymizing customer data.",
            customer_email, shopify_customer_id, self.backend_id.id,
        )

        if shopify_customer_id:
            shopify_gid = f"gid://shopify/Customer/{shopify_customer_id}"
            binding = self.env['shopify.customer.binding'].search([
                ('backend_id', '=', self.backend_id.id),
                ('shopify_id', '=', shopify_gid),
            ], limit=1)
            if binding and binding.odoo_id:
                partner = binding.odoo_id
                # Anonymize personal data while preserving record for accounting
                partner.write({
                    'name': f"Redacted Customer #{partner.id}",
                    'email': False,
                    'phone': False,
                    'mobile': False,
                    'street': False,
                    'street2': False,
                    'comment': "Personal data redacted per GDPR request.",
                })
                binding.write({
                    'shopify_email': False,
                    'shopify_tags': False,
                    'sync_status': 'permanent_error',
                    'sync_error': 'Customer data redacted (GDPR)',
                })
                _logger.info("Customer %s anonymized successfully", partner.id)

    def _handle_gdpr_shop_redact(self, data):
        """Handle shop/redact webhook.

        Shopify sends this 48 hours after a merchant uninstalls the app.
        We must delete all shop data from our systems.
        """
        shop_domain = data.get('shop_domain', '')
        _logger.warning(
            "GDPR shop redact received for %s (backend %s). "
            "Scheduling data cleanup.",
            shop_domain, self.backend_id.id,
        )
        # Notify admin — actual deletion requires human decision due to accounting data
        self.backend_id.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=f"GDPR Shop Redact: {shop_domain}",
            note=f"Shopify shop {shop_domain} has been uninstalled and requests "
                 f"data deletion. Review and delete all Shopify-related data for "
                 f"this store. Note: order and invoice data may need to be retained "
                 f"per local accounting regulations.",
        )
