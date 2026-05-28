# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import hashlib
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Maximum age (in hours) of a webhook payload's updated_at before
# it is treated as stale.  Matches Shopify's 48-hour retry window
# plus a generous margin for clock skew.
WEBHOOK_STALE_HOURS = 50


class ShopifyWebhookLog(models.Model):
    _name = 'shopify.webhook.log'
    _description = 'Shopify Webhook Log'
    _order = 'received_at desc'

    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
    )
    webhook_id = fields.Char('Shopify Webhook ID', index=True)
    webhook_fingerprint = fields.Char(
        'Webhook Fingerprint', index=True,
        help="SHA-256 fingerprint of topic + resource ID + updated_at, "
             "used as fallback dedup when webhook_id is absent.",
    )
    topic = fields.Char(required=True, index=True)
    shopify_id = fields.Char('Resource Shopify ID')
    payload = fields.Text(groups='shopify_connector_pro.group_shopify_user')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error'),
        ('dead_letter', 'Dead Letter'),
        ('skipped', 'Skipped'),
    ], default='pending', index=True)
    error_message = fields.Text()
    retry_count = fields.Integer(default=0)
    max_retries = fields.Integer(default=5)
    received_at = fields.Datetime(default=fields.Datetime.now)
    processed_at = fields.Datetime()


    _unique_webhook_id = models.Constraint(
        'UNIQUE(webhook_id)',
        'This webhook event has already been received.',
    )

    @api.model
    def compute_fingerprint(self, topic, resource_id, updated_at):
        """Compute a deterministic fingerprint for dedup fallback.

        The fingerprint is a SHA-256 hash of the topic, resource ID, and
        updated_at timestamp.  This catches duplicate events when the
        webhook_id header is missing or empty.
        """
        raw = "%s|%s|%s" % (topic or '', resource_id or '', updated_at or '')
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:40]

    @api.model
    def is_stale_payload(self, payload):
        """Return True if the payload's updated_at is older than the
        staleness window.  Returns False (allow) when the timestamp
        cannot be parsed — we err on the side of processing.
        """
        updated_at = payload.get('updated_at') or payload.get('updatedAt')
        if not updated_at:
            return False
        try:
            dt = fields.Datetime.to_datetime(
                str(updated_at).replace('T', ' ').replace('Z', ''),
            )
            cutoff = fields.Datetime.now() - timedelta(hours=WEBHOOK_STALE_HOURS)
            return dt < cutoff
        except (ValueError, TypeError):
            return False

    @api.model
    def _cron_cleanup_old_logs(self, days=90):
        """Purge webhook logs older than the retention period.

        Removes processed/skipped logs to limit PII exposure.
        Dead-letter logs are kept longer for debugging (2x retention).
        """
        cutoff = fields.Datetime.now() - timedelta(days=days)
        dead_cutoff = fields.Datetime.now() - timedelta(days=days * 2)
        old_logs = self.search([
            '|',
            '&', ('state', 'in', ['done', 'skipped']),
                 ('received_at', '<', cutoff),
            '&', ('state', '=', 'dead_letter'),
                 ('received_at', '<', dead_cutoff),
        ])
        count = len(old_logs)
        if count:
            old_logs.unlink()
            _logger.info("Purged %d old webhook logs (retention: %d days)", count, days)

    @api.model
    def _cron_process_pending(self):
        """Process pending and retryable webhook events in batches."""
        pending = self.search([
            ('state', 'in', ['pending', 'error']),
            ('retry_count', '<', 5),
        ], limit=100, order='received_at asc')
        for log in pending:
            with self.env.cr.savepoint():
                try:
                    log.state = 'processing'
                    log.flush_recordset()
                    log._process_event()
                    # _process_event() may set state='skipped' for
                    # no-op topics; preserve it instead of clobbering.
                    if log.state != 'skipped':
                        log.write({
                            'state': 'done',
                            'processed_at': fields.Datetime.now(),
                        })
                    else:
                        log.write({'processed_at': fields.Datetime.now()})
                except Exception as e:
                    _logger.exception("Webhook processing failed for %s", log.id)
                    new_retry = log.retry_count + 1
                    if new_retry >= log.max_retries:
                        log.write({
                            'state': 'dead_letter',
                            'error_message': str(e),
                            'retry_count': new_retry,
                            'processed_at': fields.Datetime.now(),
                        })
                        _logger.warning(
                            "Webhook %s moved to dead letter after %d retries",
                            log.id, new_retry,
                        )
                    else:
                        log.write({
                            'state': 'error',
                            'error_message': str(e),
                            'retry_count': new_retry,
                            'processed_at': fields.Datetime.now(),
                        })

    def action_retry_webhook(self):
        """Manually retry a dead-letter or error webhook."""
        for log in self:
            if log.state in ('error', 'dead_letter'):
                log.write({
                    'state': 'pending',
                    'retry_count': 0,
                    'error_message': False,
                })

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
            'refunds/create': '_handle_refund_webhook',
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
        """Handle order create/update — includes payment status transition detection."""
        # First, check if this is a status change on an existing order
        order_id = data.get('id')
        if order_id and self.topic == 'orders/updated':
            shopify_gid = f"gid://shopify/Order/{order_id}"
            binding = self.env['shopify.order.binding'].search([
                ('backend_id', '=', self.backend_id.id),
                ('shopify_id', '=', shopify_gid),
            ], limit=1)

            if binding:
                # Detect financial status change
                new_financial = (data.get('financial_status', '') or '').lower()
                old_financial = binding.shopify_financial_status or ''
                if new_financial and new_financial != old_financial:
                    from ..sync.payment_status_sync import PaymentStatusHandler
                    handler = PaymentStatusHandler(self.env, self.backend_id)
                    handler.handle_status_change(binding, old_financial, new_financial)

                # Detect fulfillment status change and trigger sync
                new_fulfillment = (data.get('fulfillment_status') or 'unfulfilled').lower()
                old_fulfillment = binding.shopify_fulfillment_status or 'unfulfilled'
                if new_fulfillment != old_fulfillment:
                    binding.write({'shopify_fulfillment_status': new_fulfillment})
                    if binding.odoo_id:
                        binding.odoo_id.with_context(
                            shopify_no_auto_export=True,
                        ).write({'shopify_fulfillment_status': new_fulfillment})
                        # Trigger fulfillment workflow (not just status update)
                        if new_fulfillment in ('fulfilled', 'partial'):
                            try:
                                from ..sync.fulfillment_sync import FulfillmentSync
                                syncer = FulfillmentSync(
                                    self.env, self.backend_id,
                                )
                                syncer.handle_inbound_fulfillment(
                                    binding, webhook_data=data,
                                )
                            except Exception as e:
                                _logger.warning(
                                    "Fulfillment sync failed for order %s "
                                    "during orders/updated: %s",
                                    binding.shopify_order_name, e,
                                )

        # Still run the standard order import/update logic
        self.env['shopify.order.binding'].process_webhook_event(
            self.backend_id, data, self.topic,
        )

    def _handle_order_cancel_webhook(self, data):
        """Cancel an Odoo order from a Shopify cancellation webhook.

        Wraps ``action_cancel()`` in error handling so that orders with
        done pickings or posted invoices schedule an activity instead of
        silently dead-lettering (BUG-C1).
        """
        shopify_gid = f"gid://shopify/Order/{data.get('id', '')}"
        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend_id.id),
            ('shopify_id', '=', shopify_gid),
        ], limit=1)
        if not binding or not binding.odoo_id:
            return
        order = binding.odoo_id
        # Idempotent: already cancelled
        if order.state == 'cancel':
            return
        try:
            order.with_context(
                disable_cancel_warning=True,
                shopify_no_auto_export=True,
            ).action_cancel()
        except Exception as e:
            _logger.warning(
                "Could not cancel order %s from webhook: %s", order.name, e,
            )
            reasons = []
            done_pickings = order.picking_ids.filtered(
                lambda p: p.state == 'done'
            )
            if done_pickings:
                reasons.append(
                    f"{len(done_pickings)} delivery order(s) already done"
                )
            posted_invoices = order.invoice_ids.filtered(
                lambda i: i.state == 'posted'
                and i.move_type == 'out_invoice'
            )
            if posted_invoices:
                reasons.append(f"{len(posted_invoices)} posted invoice(s)")
            note = (
                "Shopify sent a cancellation for this order but it could "
                "not be cancelled automatically.\n"
                f"Reason: {e}\n"
            )
            if reasons:
                note += f"Blocking factors: {', '.join(reasons)}.\n"
            note += "Please review and handle manually."
            order.activity_schedule(
                'mail.mail_activity_data_todo',
                summary="Shopify Cancellation Failed",
                note=note,
            )

    def _handle_customer_webhook(self, data):
        self.env['shopify.customer.binding'].process_webhook_event(
            self.backend_id, data, self.topic,
        )

    def _handle_inventory_webhook(self, data):
        _logger.info("Inventory webhook received — skipping (Odoo is source of truth)")
        self.state = 'skipped'

    def _handle_fulfillment_webhook(self, data):
        """Handle inbound fulfillment from Shopify (3PL, dropship, admin)."""
        order_id = data.get('order_id')
        if not order_id:
            _logger.warning("Fulfillment webhook without order_id")
            return
        shopify_gid = f"gid://shopify/Order/{order_id}"
        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend_id.id),
            ('shopify_id', '=', shopify_gid),
        ], limit=1)
        if not binding:
            _logger.info("No order binding for fulfillment, order_id=%s", order_id)
            return

        # Check if this fulfillment was pushed FROM Odoo (avoid loop)
        # If the order's picking was just validated, the fulfillment push
        # would have originated from us — skip inbound processing
        if self.env.context.get('shopify_no_auto_export'):
            return

        from ..sync.fulfillment_sync import FulfillmentSync
        syncer = FulfillmentSync(self.env, self.backend_id)

        status = (data.get('status', '') or '').lower()
        if status == 'cancelled':
            syncer.handle_fulfillment_cancellation(binding, webhook_data=data)
        else:
            syncer.handle_inbound_fulfillment(binding, webhook_data=data)

    def _handle_refund_webhook(self, data):
        """Create credit note from Shopify refund by delegating to the
        canonical RefundImporter. The importer creates a shopify.refund.binding
        record, which is what prevents the RefundSync cron from later
        re-importing the same refund and producing a duplicate credit note.
        """
        order_id = data.get('order_id')
        if not order_id:
            return
        shopify_gid = f"gid://shopify/Order/{order_id}"
        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend_id.id),
            ('shopify_id', '=', shopify_gid),
        ], limit=1)
        if not binding or not binding.odoo_id:
            _logger.warning("No order found for refund, order_id=%s", order_id)
            return
        try:
            from ..sync.refund_sync import RefundImporter
            importer = RefundImporter(self.env, self.backend_id)
            success, errors, skipped = importer.import_refunds_for_order(binding)
            _logger.info(
                "Refund webhook processed for order %s: %s imported, %s errors, %s skipped",
                binding.odoo_id.name, success, errors, skipped,
            )
        except Exception as e:
            _logger.warning(
                "Failed to process refund webhook for order %s: %s",
                binding.odoo_id.name, e,
            )

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
