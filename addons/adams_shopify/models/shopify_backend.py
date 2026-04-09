import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

DEFAULT_API_VERSION = '2026-01'


class ShopifyBackend(models.Model):
    _name = 'shopify.backend'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Shopify Backend'
    _check_company_auto = True

    # ── Connection ──────────────────────────────────────────
    name = fields.Char(required=True)
    shop_url = fields.Char(
        'Shop URL', required=True,
        help="Your myshopify.com domain, e.g. my-store.myshopify.com",
    )
    access_token = fields.Char(
        'Access Token', required=True,
        groups='base.group_system',
    )
    api_version = fields.Char(default=DEFAULT_API_VERSION)
    webhook_secret = fields.Char(
        'Webhook Secret',
        groups='base.group_system',
    )

    # ── Company / Warehouse ─────────────────────────────────
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse', check_company=True,
        default=lambda self: self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1,
        ),
    )
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Price List',
        help="Pricelist used when exporting prices to Shopify.",
    )
    shopify_location_id = fields.Char(
        'Shopify Location ID',
        help="Primary Shopify location GID for inventory sync.",
    )

    # ── Sync Settings ───────────────────────────────────────
    auto_sync_products = fields.Boolean('Sync Products', default=True)
    product_sync_direction = fields.Selection([
        ('export', 'Odoo → Shopify'),
        ('import', 'Shopify → Odoo'),
        ('both', 'Bidirectional'),
    ], string='Product Direction', default='both')
    product_sync_interval = fields.Integer(
        'Product Interval (min)', default=15,
    )
    auto_export_on_change = fields.Boolean(
        'Auto-export Product on Change', default=True,
    )

    auto_sync_customers = fields.Boolean('Sync Customers', default=True)
    customer_sync_direction = fields.Selection([
        ('export', 'Odoo → Shopify'),
        ('import', 'Shopify → Odoo'),
        ('both', 'Bidirectional'),
    ], string='Customer Direction', default='import')
    customer_sync_interval = fields.Integer(
        'Customer Interval (min)', default=15,
    )
    customer_dedup_field = fields.Selection([
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('email_phone', 'Email + Phone'),
    ], string='Customer Dedup By', default='email')

    auto_sync_orders = fields.Boolean('Import Orders', default=True)
    order_sync_interval = fields.Integer(
        'Order Interval (min)', default=5,
    )
    auto_create_invoice = fields.Boolean(
        'Auto-create Invoice', default=True,
    )
    import_currency_mode = fields.Selection([
        ('company', 'Always Use Company Currency'),
        ('shopify', 'Use Shopify Store Currency'),
        ('presentment', 'Use Customer Currency (Shopify Markets)'),
    ], string='Order Currency Mode', default='company',
        help="Controls how currency is set on imported orders.\n"
             "'Store Currency' uses the shop's base currency.\n"
             "'Customer Currency' uses the currency the customer paid in "
             "(required for Shopify Markets / multi-currency storefronts).",
    )

    auto_sync_inventory = fields.Boolean('Push Inventory', default=True)
    inventory_sync_interval = fields.Integer(
        'Inventory Interval (min)', default=10,
    )
    inventory_quantity_field = fields.Selection([
        ('free_qty', 'Free Quantity'),
        ('qty_available', 'On Hand Quantity'),
    ], string='Quantity Type', default='free_qty')

    auto_sync_collections = fields.Boolean('Sync Collections', default=True)

    # ── Status Sync Settings ───────────────────────────────
    external_fulfillment_handling = fields.Selection([
        ('activity', 'Create Activity (manual review)'),
        ('auto_validate', 'Auto-validate Delivery'),
        ('ignore', 'Update Status Only'),
    ], string='External Fulfillment Handling', default='activity',
        help="How to handle fulfillments created on Shopify "
             "(e.g. by 3PL, dropship, or direct Shopify admin).",
    )
    auto_handle_payment_transitions = fields.Boolean(
        'Auto-handle Payment Transitions', default=True,
        help="Automatically post/cancel invoices when payment status "
             "changes on Shopify (e.g. authorized→paid, pending→voided).",
    )
    reverse_sync_payment = fields.Boolean(
        'Reverse Sync: Payment', default=False,
        help="When an invoice is posted in Odoo for a Shopify order, "
             "mark the order as paid on Shopify via orderMarkAsPaid.",
    )
    reverse_sync_refund = fields.Boolean(
        'Reverse Sync: Refund', default=False,
        help="When a credit note is posted in Odoo for a Shopify order, "
             "create a refund on Shopify.",
    )
    reconciliation_order_days = fields.Integer(
        'Reconciliation Lookback (days)', default=30,
        help="How many days back to check for status mismatches.",
    )

    shipping_product_id = fields.Many2one(
        'product.product', string='Shipping Product',
        help="Product used for shipping lines on imported orders. "
             "If not set, a default 'Shopify Shipping' product is used.",
    )

    batch_size = fields.Integer(default=50)

    # ── Field Mapping ───────────────────────────────────────
    field_mapping_ids = fields.One2many(
        'shopify.field.mapping', 'backend_id',
        string='Field Mappings',
    )
    tax_mapping_ids = fields.One2many(
        'shopify.tax.mapping', 'backend_id',
        string='Tax Mappings',
    )
    metafield_mapping_ids = fields.One2many(
        'shopify.metafield.mapping', 'backend_id',
        string='Metafield Mappings',
    )

    # ── Status ──────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Not Connected'),
        ('connected', 'Connected'),
        ('error', 'Connection Error'),
    ], default='draft', readonly=True)
    last_sync_date = fields.Datetime(readonly=True)
    shop_name = fields.Char('Shopify Shop Name', readonly=True)
    shop_plan = fields.Char('Shopify Plan', readonly=True)

    # ── Binding counts (computed) ───────────────────────────
    product_bind_count = fields.Integer(compute='_compute_bind_counts')
    customer_bind_count = fields.Integer(compute='_compute_bind_counts')
    order_bind_count = fields.Integer(compute='_compute_bind_counts')
    product_error_count = fields.Integer(compute='_compute_bind_counts')
    customer_error_count = fields.Integer(compute='_compute_bind_counts')
    order_error_count = fields.Integer(compute='_compute_bind_counts')
    total_error_count = fields.Integer(compute='_compute_bind_counts')
    total_synced_count = fields.Integer(compute='_compute_bind_counts')
    total_pending_count = fields.Integer(compute='_compute_bind_counts')
    collection_bind_count = fields.Integer(compute='_compute_bind_counts')
    refund_bind_count = fields.Integer(compute='_compute_bind_counts')
    sync_log_today_count = fields.Integer(compute='_compute_bind_counts')
    promoter_count = fields.Integer(compute='_compute_bind_counts')
    abandoned_cart_count = fields.Integer(compute='_compute_bind_counts')
    sync_health_pct = fields.Integer(
        compute='_compute_bind_counts',
        string='Sync Health %',
        help='Percentage of bindings in synced state (vs error/pending).',
    )

    # ── Constraints ─────────────────────────────────────────
    @api.constrains('shop_url')
    def _check_shop_url(self):
        """Validate shop_url is a legitimate myshopify.com domain."""
        pattern = re.compile(
            r'^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$'
        )
        for rec in self:
            url = (rec.shop_url or '').strip().rstrip('/')
            # Strip protocol if user pasted full URL
            if '://' in url:
                url = url.split('://', 1)[1]
            # Strip trailing path
            url = url.split('/')[0]
            if not pattern.match(url):
                raise ValidationError(_(
                    "Shop URL must be a valid myshopify.com domain "
                    "(e.g. my-store.myshopify.com). Got: %s",
                    rec.shop_url,
                ))

    @api.constrains('access_token')
    def _check_access_token(self):
        """Validate access token format (Shopify custom app tokens start with shpat_)."""
        for rec in self:
            token = rec.access_token or ''
            if token and not token.startswith('shpat_'):
                raise ValidationError(_(
                    "Access token should start with 'shpat_'. "
                    "Please use a valid Shopify Admin API access token.",
                ))

    @api.depends_context('uid')
    def _compute_bind_counts(self):
        today_start = fields.Datetime.now().replace(hour=0, minute=0, second=0)
        binding_models = {
            'product': 'shopify.product.binding',
            'customer': 'shopify.customer.binding',
            'order': 'shopify.order.binding',
        }
        for rec in self:
            synced_total = error_total = pending_total = 0
            for key, model_name in binding_models.items():
                Model = self.env[model_name]
                synced = Model.search_count(
                    [('backend_id', '=', rec.id), ('sync_status', '=', 'synced')])
                errors = Model.search_count(
                    [('backend_id', '=', rec.id), ('sync_status', '=', 'error')])
                pending = Model.search_count(
                    [('backend_id', '=', rec.id), ('sync_status', '=', 'pending')])
                setattr(rec, f'{key}_bind_count', synced)
                setattr(rec, f'{key}_error_count', errors)
                synced_total += synced
                error_total += errors
                pending_total += pending

            rec.total_error_count = error_total
            rec.total_synced_count = synced_total
            rec.total_pending_count = pending_total

            # Sync health percentage
            grand_total = synced_total + error_total + pending_total
            rec.sync_health_pct = int(
                (synced_total / grand_total * 100) if grand_total else 100
            )

            rec.collection_bind_count = self.env['shopify.collection.binding'].search_count(
                [('backend_id', '=', rec.id), ('sync_status', '=', 'synced')],
            )
            rec.refund_bind_count = self.env['shopify.refund.binding'].search_count(
                [('backend_id', '=', rec.id), ('sync_status', '=', 'synced')],
            )
            rec.sync_log_today_count = self.env['shopify.sync.log'].search_count(
                [('backend_id', '=', rec.id), ('create_date', '>=', today_start)],
            )
            rec.promoter_count = self.env['shopify.promoter'].search_count(
                [('company_id', '=', rec.company_id.id), ('status', '=', 'active')],
            )
            # Abandoned carts
            if 'shopify.abandoned.cart' in self.env:
                rec.abandoned_cart_count = self.env['shopify.abandoned.cart'].search_count(
                    [('backend_id', '=', rec.id), ('recovered', '=', False)])
            else:
                rec.abandoned_cart_count = 0

    # ── Actions ─────────────────────────────────────────────

    def action_test_connection(self):
        """Test the Shopify API connection and update status."""
        self.ensure_one()
        from ..shopify_api.client import ShopifyClient
        try:
            client = ShopifyClient(self)
            shop_data = client.fetch_shop_info()
            self.write({
                'state': 'connected',
                'shop_name': shop_data.get('name', ''),
                'shop_plan': shop_data.get('plan', {}).get('displayName', ''),
            })
        except Exception as e:
            self.write({'state': 'error'})
            raise UserError(_("Connection failed: %s") % str(e))

    def action_register_webhooks(self):
        """Register all required webhooks on Shopify."""
        self.ensure_one()
        if self.state != 'connected':
            raise UserError(_("Please test your connection first."))
        if not self.webhook_secret:
            raise UserError(_("Please set a Webhook Secret before registering webhooks. "
                              "This secret is used to verify incoming webhook signatures."))
        from ..shopify_api.client import ShopifyClient
        client = ShopifyClient(self)
        topics = [
            'PRODUCTS_CREATE', 'PRODUCTS_UPDATE', 'PRODUCTS_DELETE',
            'ORDERS_CREATE', 'ORDERS_UPDATED', 'ORDERS_CANCELLED',
            'CUSTOMERS_CREATE', 'CUSTOMERS_UPDATE',
            'INVENTORY_LEVELS_UPDATE',
            'FULFILLMENTS_CREATE',
            'APP_UNINSTALLED',
        ]
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        callback_url = f"{base_url}/shopify/webhook/{self.id}"
        registered = 0
        for topic in topics:
            try:
                client.register_webhook(topic, callback_url)
                registered += 1
            except Exception as e:
                _logger.warning("Failed to register webhook %s: %s", topic, e)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Webhooks Registered"),
                'message': _("%d of %d webhooks registered successfully.") % (registered, len(topics)),
                'type': 'success' if registered == len(topics) else 'warning',
                'sticky': False,
            },
        }

    def action_init_field_mappings(self):
        """Initialize default field mappings if none exist."""
        self.ensure_one()
        if self.field_mapping_ids:
            return
        FieldMapping = self.env['shopify.field.mapping']
        seq = 10
        for m in FieldMapping._get_default_product_mappings():
            FieldMapping.create({
                'backend_id': self.id,
                'entity': 'product',
                'odoo_field': m['odoo_field'],
                'shopify_field': m['shopify_field'],
                'direction': m['direction'],
                'sequence': seq,
            })
            seq += 10
        for m in FieldMapping._get_default_customer_mappings():
            FieldMapping.create({
                'backend_id': self.id,
                'entity': 'customer',
                'odoo_field': m['odoo_field'],
                'shopify_field': m['shopify_field'],
                'direction': m['direction'],
                'sequence': seq,
            })
            seq += 10

    def action_open_product_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Bindings'),
            'res_model': 'shopify.product.binding',
            'view_mode': 'list,form',
            'domain': [('backend_id', '=', self.id)],
        }

    def action_open_customer_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Bindings'),
            'res_model': 'shopify.customer.binding',
            'view_mode': 'list,form',
            'domain': [('backend_id', '=', self.id)],
        }

    def action_open_order_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Order Bindings'),
            'res_model': 'shopify.order.binding',
            'view_mode': 'list,form',
            'domain': [('backend_id', '=', self.id)],
        }

    def action_open_sync_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sync Logs'),
            'res_model': 'shopify.sync.log',
            'view_mode': 'list,form',
            'domain': [('backend_id', '=', self.id)],
        }

    def _notify_sync_error(self, entity, error_count, error_details=''):
        """Post a notification to the backend's chatter about sync errors."""
        if error_count == 0:
            return
        body = (
            f"<p><strong>Sync Alert: {error_count} {entity} error(s)</strong></p>"
            f"<p>{error_details[:500] if error_details else 'Check the sync log for details.'}</p>"
        )
        self.message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_note')

    # ── Cron entry points ───────────────────────────────────

    @api.model
    def _cron_sync_products(self):
        backends = self.search([('state', '=', 'connected'), ('auto_sync_products', '=', True)])
        for backend in backends:
            try:
                self.env['shopify.product.binding'].with_company(
                    backend.company_id
                ).run_sync(backend)
                backend.last_sync_date = fields.Datetime.now()
            except Exception as e:
                _logger.exception("Product sync failed for backend %s", backend.id)
                backend._notify_sync_error('products', 1, str(e))

    @api.model
    def _cron_import_orders(self):
        backends = self.search([('state', '=', 'connected'), ('auto_sync_orders', '=', True)])
        for backend in backends:
            try:
                self.env['shopify.order.binding'].with_company(
                    backend.company_id
                ).run_import(backend)
                backend.last_sync_date = fields.Datetime.now()
            except Exception as e:
                _logger.exception("Order import failed for backend %s", backend.id)
                backend._notify_sync_error('orders', 1, str(e))

    @api.model
    def _cron_sync_inventory(self):
        backends = self.search([('state', '=', 'connected'), ('auto_sync_inventory', '=', True)])
        for backend in backends:
            try:
                self.env['shopify.inventory.binding'].with_company(
                    backend.company_id
                ).run_export(backend)
                backend.last_sync_date = fields.Datetime.now()
            except Exception as e:
                _logger.exception("Inventory sync failed for backend %s", backend.id)
                backend._notify_sync_error('inventory', 1, str(e))

    @api.model
    def _cron_sync_customers(self):
        backends = self.search([('state', '=', 'connected'), ('auto_sync_customers', '=', True)])
        for backend in backends:
            try:
                direction = backend.customer_sync_direction or 'import'
                if direction in ('import', 'both'):
                    self.env['shopify.customer.binding'].with_company(
                        backend.company_id
                    ).run_import(backend)
                if direction in ('export', 'both'):
                    from ..sync.customer_sync import CustomerSync
                    syncer = CustomerSync(
                        self.env.with_company(backend.company_id), backend,
                    )
                    syncer.export_customers()
                backend.last_sync_date = fields.Datetime.now()
            except Exception as e:
                _logger.exception("Customer sync failed for backend %s", backend.id)
                backend._notify_sync_error('customers', 1, str(e))

    @api.model
    def _cron_sync_discounts(self):
        backends = self.search([('state', '=', 'connected')])
        for backend in backends:
            try:
                from ..sync.discount_sync import DiscountSync
                syncer = DiscountSync(
                    self.env.with_company(backend.company_id), backend,
                )
                syncer.export_discounts()
            except Exception as e:
                _logger.exception("Discount sync failed for backend %s", backend.id)
                backend._notify_sync_error('discounts', 1, str(e))

    @api.model
    def _cron_sync_collections(self):
        backends = self.search([('state', '=', 'connected'), ('auto_sync_collections', '=', True)])
        for backend in backends:
            try:
                from ..sync.collection_sync import CollectionSync
                syncer = CollectionSync(
                    self.env.with_company(backend.company_id), backend,
                )
                syncer.import_collections()
                backend.last_sync_date = fields.Datetime.now()
            except Exception as e:
                _logger.exception("Collection sync failed for backend %s", backend.id)
                backend._notify_sync_error('collections', 1, str(e))

    @api.model
    def _cron_import_payouts(self):
        backends = self.search([('state', '=', 'connected')])
        for backend in backends:
            try:
                from ..sync.payout_sync import PayoutSync
                syncer = PayoutSync(
                    self.env.with_company(backend.company_id), backend,
                )
                syncer.import_payouts()
            except Exception as e:
                _logger.exception("Payout import failed for backend %s", backend.id)
                backend._notify_sync_error('payouts', 1, str(e))

    @api.model
    def _cron_import_refunds(self):
        backends = self.search([('state', '=', 'connected'), ('auto_sync_orders', '=', True)])
        for backend in backends:
            try:
                from ..sync.refund_sync import RefundSync
                syncer = RefundSync(
                    self.env.with_company(backend.company_id), backend,
                )
                syncer.import_refunds()
            except Exception as e:
                _logger.exception("Refund import failed for backend %s", backend.id)
                backend._notify_sync_error('refunds', 1, str(e))

    def action_import_locations(self):
        """Import locations from Shopify."""
        self.ensure_one()
        from ..sync.location_sync import LocationSync
        syncer = LocationSync(self.env, self)
        success, errors = syncer.import_locations()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Locations Imported"),
                'message': _("%d locations imported, %d errors.") % (success, errors),
                'type': 'success' if not errors else 'warning',
                'sticky': False,
            },
        }

    def action_open_promoters(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Promoters'),
            'res_model': 'shopify.promoter',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.company_id.id)],
        }

    def action_open_webhook_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Webhook Logs'),
            'res_model': 'shopify.webhook.log',
            'view_mode': 'list,form',
            'domain': [('backend_id', '=', self.id)],
            'context': {'default_backend_id': self.id},
        }

    def action_unregister_webhooks(self):
        """Unregister all webhooks from Shopify."""
        self.ensure_one()
        if self.state != 'connected':
            raise UserError(_("Please test your connection first."))
        from ..shopify_api.client import ShopifyClient
        client = ShopifyClient(self)
        # Fetch existing webhook subscriptions and delete them
        query = """
        query {
          webhookSubscriptions(first: 50) {
            edges {
              node { id topic }
            }
          }
        }
        """
        try:
            body = client.execute(query, estimated_cost=5)
            subscriptions = body.get('data', {}).get('webhookSubscriptions', {}).get('edges', [])
            delete_mutation = """
            mutation deleteWebhook($id: ID!) {
              webhookSubscriptionDelete(id: $id) {
                deletedWebhookSubscriptionId
                userErrors { field message }
              }
            }
            """
            deleted = 0
            for edge in subscriptions:
                sub_id = edge.get('node', {}).get('id')
                if sub_id:
                    try:
                        client.execute_mutation(
                            delete_mutation,
                            {'id': sub_id},
                            result_key='webhookSubscriptionDelete',
                            estimated_cost=5,
                        )
                        deleted += 1
                    except Exception as e:
                        _logger.warning("Failed to delete webhook %s: %s", sub_id, e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Webhooks Removed"),
                    'message': _("%d webhooks removed.") % deleted,
                    'type': 'success',
                    'sticky': False,
                },
            }
        except Exception as e:
            raise UserError(_("Failed to unregister webhooks: %s") % str(e))

    def action_check_webhook_status(self):
        """Check and display current webhook subscription status from Shopify."""
        self.ensure_one()
        if self.state != 'connected':
            raise UserError(_("Please test your connection first."))
        from ..shopify_api.client import ShopifyClient
        client = ShopifyClient(self)
        query = """
        query {
          webhookSubscriptions(first: 50) {
            edges {
              node {
                id
                topic
                endpoint {
                  ... on WebhookHttpEndpoint { callbackUrl }
                }
                createdAt
              }
            }
          }
        }
        """
        try:
            body = client.execute(query, estimated_cost=5)
            subscriptions = body.get('data', {}).get('webhookSubscriptions', {}).get('edges', [])
            topics = [e.get('node', {}).get('topic', '') for e in subscriptions]
            topic_list = '\n'.join(f"  - {t}" for t in sorted(topics)) if topics else "None"
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Webhook Status"),
                    'message': _("%d active webhooks:\n%s") % (len(topics), topic_list),
                    'type': 'info',
                    'sticky': True,
                },
            }
        except Exception as e:
            raise UserError(_("Failed to check webhook status: %s") % str(e))
