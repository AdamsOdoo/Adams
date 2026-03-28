import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

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

    auto_sync_inventory = fields.Boolean('Push Inventory', default=True)
    inventory_sync_interval = fields.Integer(
        'Inventory Interval (min)', default=10,
    )
    inventory_quantity_field = fields.Selection([
        ('free_qty', 'Free Quantity'),
        ('qty_available', 'On Hand Quantity'),
    ], string='Quantity Type', default='free_qty')

    batch_size = fields.Integer(default=50)

    # ── Field Mapping ───────────────────────────────────────
    field_mapping_ids = fields.One2many(
        'shopify.field.mapping', 'backend_id',
        string='Field Mappings',
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

    @api.depends_context('uid')
    def _compute_bind_counts(self):
        for rec in self:
            rec.product_bind_count = self.env['shopify.product.binding'].search_count(
                [('backend_id', '=', rec.id), ('sync_status', '=', 'synced')],
            )
            rec.customer_bind_count = self.env['shopify.customer.binding'].search_count(
                [('backend_id', '=', rec.id), ('sync_status', '=', 'synced')],
            )
            rec.order_bind_count = self.env['shopify.order.binding'].search_count(
                [('backend_id', '=', rec.id), ('sync_status', '=', 'synced')],
            )
            rec.product_error_count = self.env['shopify.product.binding'].search_count(
                [('backend_id', '=', rec.id), ('sync_status', '=', 'error')],
            )

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
            'view_mode': 'tree,form',
            'domain': [('backend_id', '=', self.id)],
        }

    def action_open_customer_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Bindings'),
            'res_model': 'shopify.customer.binding',
            'view_mode': 'tree,form',
            'domain': [('backend_id', '=', self.id)],
        }

    def action_open_order_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Order Bindings'),
            'res_model': 'shopify.order.binding',
            'view_mode': 'tree,form',
            'domain': [('backend_id', '=', self.id)],
        }

    def action_open_sync_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sync Logs'),
            'res_model': 'shopify.sync.log',
            'view_mode': 'tree,form',
            'domain': [('backend_id', '=', self.id)],
        }

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
            except Exception:
                _logger.exception("Product sync failed for backend %s", backend.id)

    @api.model
    def _cron_import_orders(self):
        backends = self.search([('state', '=', 'connected'), ('auto_sync_orders', '=', True)])
        for backend in backends:
            try:
                self.env['shopify.order.binding'].with_company(
                    backend.company_id
                ).run_import(backend)
                backend.last_sync_date = fields.Datetime.now()
            except Exception:
                _logger.exception("Order import failed for backend %s", backend.id)

    @api.model
    def _cron_sync_inventory(self):
        backends = self.search([('state', '=', 'connected'), ('auto_sync_inventory', '=', True)])
        for backend in backends:
            try:
                self.env['shopify.inventory.binding'].with_company(
                    backend.company_id
                ).run_export(backend)
                backend.last_sync_date = fields.Datetime.now()
            except Exception:
                _logger.exception("Inventory sync failed for backend %s", backend.id)

    @api.model
    def _cron_sync_customers(self):
        backends = self.search([('state', '=', 'connected'), ('auto_sync_customers', '=', True)])
        for backend in backends:
            try:
                self.env['shopify.customer.binding'].with_company(
                    backend.company_id
                ).run_import(backend)
                backend.last_sync_date = fields.Datetime.now()
            except Exception:
                _logger.exception("Customer sync failed for backend %s", backend.id)
