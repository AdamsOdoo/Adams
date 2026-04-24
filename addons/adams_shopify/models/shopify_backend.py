# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging
import re
from datetime import timedelta

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

    # ── Abandoned Cart Settings ────────────────────────────
    auto_sync_abandoned_carts = fields.Boolean(
        'Sync Abandoned Carts', default=False,
        help="Import abandoned checkouts from Shopify.",
    )
    auto_create_abandoned_quotation = fields.Boolean(
        'Auto-create Quotations', default=False,
        help="Automatically create draft quotations for abandoned carts.",
    )

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

    @api.constrains('batch_size', 'product_sync_interval',
                    'customer_sync_interval', 'order_sync_interval',
                    'inventory_sync_interval')
    def _check_positive_intervals(self):
        """Guard against misconfiguration that would stall sync loops."""
        for rec in self:
            if rec.batch_size is not None and rec.batch_size < 1:
                raise ValidationError(_(
                    "Batch size must be at least 1 (got %s).", rec.batch_size,
                ))
            if rec.batch_size and rec.batch_size > 250:
                raise ValidationError(_(
                    "Batch size cannot exceed 250 (Shopify API limit).",
                ))
            for name, val in (
                ('Product', rec.product_sync_interval),
                ('Customer', rec.customer_sync_interval),
                ('Order', rec.order_sync_interval),
                ('Inventory', rec.inventory_sync_interval),
            ):
                if val is not None and val < 1:
                    raise ValidationError(_(
                        "%s sync interval must be at least 1 minute.", name,
                    ))

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
    inventory_bind_count = fields.Integer(compute='_compute_bind_counts')
    inventory_error_count = fields.Integer(compute='_compute_bind_counts')
    payout_count = fields.Integer(compute='_compute_bind_counts')
    permanent_error_count = fields.Integer(compute='_compute_bind_counts')

    # ── Per-entity last sync (computed) ────────────────────
    last_product_sync = fields.Datetime(compute='_compute_last_entity_sync')
    last_customer_sync = fields.Datetime(compute='_compute_last_entity_sync')
    last_order_sync = fields.Datetime(compute='_compute_last_entity_sync')
    last_inventory_sync = fields.Datetime(compute='_compute_last_entity_sync')
    last_fulfillment_sync = fields.Datetime(compute='_compute_last_entity_sync')
    last_collection_sync = fields.Datetime(compute='_compute_last_entity_sync')

    # ── Webhook health (computed) ──────────────────────────
    webhook_pending_count = fields.Integer(compute='_compute_webhook_health')
    webhook_dead_letter_count = fields.Integer(compute='_compute_webhook_health')

    # ── Reconciliation health (computed) ───────────────────
    payment_mismatch_count = fields.Integer(compute='_compute_reconciliation_health')
    fulfillment_mismatch_count = fields.Integer(compute='_compute_reconciliation_health')

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

    @api.depends('state', 'last_sync_date')
    @api.depends_context('uid')
    def _compute_bind_counts(self):
        # Seed defaults on every record so unsaved NewId records (and empty
        # recordsets) still satisfy Odoo's compute-assignment contract during
        # onchange snapshotting. Real records get overwritten below.
        _zero_fields = (
            'product_bind_count', 'customer_bind_count', 'order_bind_count',
            'product_error_count', 'customer_error_count', 'order_error_count',
            'inventory_bind_count', 'inventory_error_count',
            'total_error_count', 'total_synced_count', 'total_pending_count',
            'permanent_error_count', 'collection_bind_count',
            'refund_bind_count', 'sync_log_today_count', 'promoter_count',
            'abandoned_cart_count', 'payout_count',
        )
        for rec in self:
            for fname in _zero_fields:
                setattr(rec, fname, 0)
            rec.sync_health_pct = 100

        today_start = fields.Datetime.now().replace(hour=0, minute=0, second=0)
        backend_ids = self.ids
        if not backend_ids:
            return

        binding_models = {
            'product': 'shopify.product.binding',
            'customer': 'shopify.customer.binding',
            'order': 'shopify.order.binding',
        }

        # Aggregate counts per (backend_id, sync_status) with a single
        # read_group per binding model, O(models) queries total.
        aggregated = {}  # {(model_key, backend_id, status): count}
        for key, model_name in binding_models.items():
            Model = self.env[model_name].sudo()
            groups = Model._read_group(
                [('backend_id', 'in', backend_ids)],
                groupby=['backend_id', 'sync_status'],
                aggregates=['__count'],
            )
            for backend, status, count in groups:
                aggregated[(key, backend.id, status)] = count

        # Inventory binding counts
        inv_aggregated = {}
        InvModel = self.env['shopify.inventory.binding'].sudo()
        inv_groups = InvModel._read_group(
            [('backend_id', 'in', backend_ids)],
            groupby=['backend_id', 'sync_status'],
            aggregates=['__count'],
        )
        for backend, status, count in inv_groups:
            inv_aggregated[(backend.id, status)] = count

        # Payout counts
        payout_counts = dict(
            (b.id, c) for b, c in self.env['shopify.payout'].sudo()._read_group(
                [('backend_id', 'in', backend_ids)],
                groupby=['backend_id'],
                aggregates=['__count'],
            )
        )

        # Other one-off counts also grouped.
        collection_counts = dict(
            (b.id, c) for b, c in self.env['shopify.collection.binding'].sudo()._read_group(
                [('backend_id', 'in', backend_ids), ('sync_status', '=', 'synced')],
                groupby=['backend_id'],
                aggregates=['__count'],
            )
        )
        refund_counts = dict(
            (b.id, c) for b, c in self.env['shopify.refund.binding'].sudo()._read_group(
                [('backend_id', 'in', backend_ids), ('sync_status', '=', 'synced')],
                groupby=['backend_id'],
                aggregates=['__count'],
            )
        )
        log_counts = dict(
            (b.id, c) for b, c in self.env['shopify.sync.log'].sudo()._read_group(
                [('backend_id', 'in', backend_ids), ('create_date', '>=', today_start)],
                groupby=['backend_id'],
                aggregates=['__count'],
            )
        )
        abandoned_counts = {}
        if 'shopify.abandoned.cart' in self.env:
            abandoned_counts = dict(
                (b.id, c) for b, c in self.env['shopify.abandoned.cart'].sudo()._read_group(
                    [('backend_id', 'in', backend_ids), ('recovered', '=', False)],
                    groupby=['backend_id'],
                    aggregates=['__count'],
                )
            )

        # Promoters grouped by company (shared across backends).
        company_ids = self.mapped('company_id').ids
        promoter_counts = {}
        if company_ids:
            promoter_counts = dict(
                (c.id, n) for c, n in self.env['shopify.promoter'].sudo()._read_group(
                    [('company_id', 'in', company_ids), ('status', '=', 'active')],
                    groupby=['company_id'],
                    aggregates=['__count'],
                )
            )

        for rec in self:
            synced_total = error_total = pending_total = perm_total = 0
            for key in binding_models:
                synced = aggregated.get((key, rec.id, 'synced'), 0)
                errors = aggregated.get((key, rec.id, 'error'), 0)
                perm = aggregated.get((key, rec.id, 'permanent_error'), 0)
                pending = aggregated.get((key, rec.id, 'pending'), 0)
                setattr(rec, f'{key}_bind_count', synced)
                setattr(rec, f'{key}_error_count', errors + perm)
                synced_total += synced
                error_total += errors + perm
                pending_total += pending
                perm_total += perm

            # Inventory counts
            inv_synced = inv_aggregated.get((rec.id, 'synced'), 0)
            inv_error = inv_aggregated.get((rec.id, 'error'), 0)
            inv_perm = inv_aggregated.get((rec.id, 'permanent_error'), 0)
            inv_pending = inv_aggregated.get((rec.id, 'pending'), 0)
            rec.inventory_bind_count = inv_synced
            rec.inventory_error_count = inv_error + inv_perm
            synced_total += inv_synced
            error_total += inv_error + inv_perm
            pending_total += inv_pending
            perm_total += inv_perm

            rec.total_error_count = error_total
            rec.total_synced_count = synced_total
            rec.total_pending_count = pending_total
            rec.permanent_error_count = perm_total

            grand_total = synced_total + error_total + pending_total
            rec.sync_health_pct = int(
                (synced_total / grand_total * 100) if grand_total else 100
            )

            rec.collection_bind_count = collection_counts.get(rec.id, 0)
            rec.refund_bind_count = refund_counts.get(rec.id, 0)
            rec.payout_count = payout_counts.get(rec.id, 0)
            rec.sync_log_today_count = log_counts.get(rec.id, 0)
            rec.promoter_count = promoter_counts.get(rec.company_id.id, 0)
            rec.abandoned_cart_count = abandoned_counts.get(rec.id, 0)

    @api.depends('state', 'last_sync_date')
    @api.depends_context('uid')
    def _compute_last_entity_sync(self):
        entity_field_map = {
            'product': 'last_product_sync',
            'customer': 'last_customer_sync',
            'order': 'last_order_sync',
            'inventory': 'last_inventory_sync',
            'fulfillment': 'last_fulfillment_sync',
            'collection': 'last_collection_sync',
        }

        latest = {}
        backend_ids = self.ids
        if backend_ids:
            groups = self.env['shopify.sync.log'].sudo()._read_group(
                [
                    ('backend_id', 'in', backend_ids),
                    ('state', 'in', ('done', 'partial')),
                    ('entity', 'in', list(entity_field_map.keys())),
                ],
                groupby=['backend_id', 'entity'],
                aggregates=['finished_at:max'],
            )
            for backend, entity, max_finished in groups:
                latest[(backend.id, entity)] = max_finished

        for rec in self:
            for entity, field_name in entity_field_map.items():
                setattr(rec, field_name, latest.get((rec.id, entity), False))

    @api.depends('state', 'last_sync_date')
    @api.depends_context('uid')
    def _compute_webhook_health(self):
        pending = {}
        dead = {}
        backend_ids = self.ids
        if backend_ids:
            WebhookLog = self.env['shopify.webhook.log'].sudo()
            pending = dict(
                (b.id, c) for b, c in WebhookLog._read_group(
                    [('backend_id', 'in', backend_ids), ('state', '=', 'pending')],
                    groupby=['backend_id'],
                    aggregates=['__count'],
                )
            )
            dead = dict(
                (b.id, c) for b, c in WebhookLog._read_group(
                    [('backend_id', 'in', backend_ids), ('state', '=', 'dead_letter')],
                    groupby=['backend_id'],
                    aggregates=['__count'],
                )
            )
        for rec in self:
            rec.webhook_pending_count = pending.get(rec.id, 0)
            rec.webhook_dead_letter_count = dead.get(rec.id, 0)

    @api.depends('state', 'last_sync_date')
    @api.depends_context('uid')
    def _compute_reconciliation_health(self):
        cutoff = fields.Datetime.now() - timedelta(days=30)
        for rec in self:
            if rec.state != 'connected':
                rec.payment_mismatch_count = 0
                rec.fulfillment_mismatch_count = 0
                continue

            OrderBinding = self.env['shopify.order.binding'].sudo()

            # Payment mismatches: paid on Shopify but no posted invoice
            paid_bindings = OrderBinding.search([
                ('backend_id', '=', rec.id),
                ('shopify_financial_status', '=', 'paid'),
                ('sync_status', '=', 'synced'),
                ('create_date', '>=', cutoff),
            ])
            pay_mismatch = 0
            for binding in paid_bindings:
                order = binding.odoo_id
                if not order:
                    continue
                posted = order.invoice_ids.filtered(
                    lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
                )
                if not posted:
                    pay_mismatch += 1
            rec.payment_mismatch_count = pay_mismatch

            # Fulfillment mismatches: fulfilled on Shopify but pending in Odoo
            fulfilled_bindings = OrderBinding.search([
                ('backend_id', '=', rec.id),
                ('shopify_fulfillment_status', '=', 'fulfilled'),
                ('sync_status', '=', 'synced'),
                ('create_date', '>=', cutoff),
            ])
            ful_mismatch = 0
            for binding in fulfilled_bindings:
                order = binding.odoo_id
                if not order:
                    continue
                out_pickings = order.picking_ids.filtered(
                    lambda p: p.picking_type_code == 'outgoing'
                )
                if not out_pickings:
                    continue
                pending = out_pickings.filtered(
                    lambda p: p.state not in ('done', 'cancel')
                )
                if pending:
                    ful_mismatch += 1
            rec.fulfillment_mismatch_count = ful_mismatch

    # ── Actions ─────────────────────────────────────────────

    def action_retry_all_errors(self):
        self.ensure_one()
        binding_models = [
            'shopify.product.binding',
            'shopify.customer.binding',
            'shopify.order.binding',
            'shopify.inventory.binding',
        ]
        total = 0
        for model_name in binding_models:
            bindings = self.env[model_name].search([
                ('backend_id', '=', self.id),
                ('sync_status', '=', 'error'),
            ])
            if bindings:
                bindings.write({
                    'sync_status': 'pending',
                    'sync_error': False,
                    'retry_count': 0,
                })
                total += len(bindings)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Errors Reset"),
                'message': _("%d bindings reset to pending for retry.") % total,
                'type': 'success' if total else 'info',
                'sticky': False,
            },
        }

    def action_open_error_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sync Errors'),
            'res_model': 'shopify.sync.log',
            'view_mode': 'list,form',
            'domain': [
                ('backend_id', '=', self.id),
                ('state', 'in', ('error', 'partial')),
            ],
        }

    def action_open_payment_mismatches(self):
        self.ensure_one()
        cutoff = fields.Datetime.now() - timedelta(days=30)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Mismatches'),
            'res_model': 'shopify.order.binding',
            'view_mode': 'list,form',
            'domain': [
                ('backend_id', '=', self.id),
                ('shopify_financial_status', '=', 'paid'),
                ('sync_status', '=', 'synced'),
                ('create_date', '>=', str(cutoff)),
            ],
        }

    def action_open_fulfillment_mismatches(self):
        self.ensure_one()
        cutoff = fields.Datetime.now() - timedelta(days=30)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fulfillment Mismatches'),
            'res_model': 'shopify.order.binding',
            'view_mode': 'list,form',
            'domain': [
                ('backend_id', '=', self.id),
                ('shopify_fulfillment_status', '=', 'fulfilled'),
                ('sync_status', '=', 'synced'),
                ('create_date', '>=', str(cutoff)),
            ],
        }

    def action_run_reconciliation(self):
        self.ensure_one()
        if self.state != 'connected':
            raise UserError(_("Please test your connection first."))
        self.env['shopify.reconciliation']._reconcile_backend(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Reconciliation Complete"),
                'message': _("Reconciliation finished. Check sync logs for details."),
                'type': 'info',
                'sticky': False,
            },
        }

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

    def action_open_inventory_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inventory Bindings'),
            'res_model': 'shopify.inventory.binding',
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

    # ── Error Monitoring ──────────────────────────────────────

    @api.model
    def _cron_error_digest(self):
        """Daily error digest — posts a summary to chatter for each backend
        that accumulated sync errors in the last 24 hours.

        This ensures sync failures are visible to followers without requiring
        someone to check the sync log manually.
        """
        cutoff = fields.Datetime.now() - timedelta(hours=24)
        backends = self.search([('state', '=', 'connected')])

        for backend in backends:
            # Gather error/partial sync logs from the last 24 hours
            error_logs = self.env['shopify.sync.log'].sudo().search([
                ('backend_id', '=', backend.id),
                ('state', 'in', ('error', 'partial')),
                ('create_date', '>=', cutoff),
            ])
            if not error_logs:
                continue

            # Count binding errors (persistent)
            binding_models = {
                'Products': 'shopify.product.binding',
                'Customers': 'shopify.customer.binding',
                'Orders': 'shopify.order.binding',
                'Inventory': 'shopify.inventory.binding',
            }
            error_lines = []
            total_binding_errors = 0
            for label, model_name in binding_models.items():
                count = self.env[model_name].sudo().search_count([
                    ('backend_id', '=', backend.id),
                    ('sync_status', 'in', ('error', 'permanent_error')),
                ])
                if count:
                    error_lines.append(f"<li>{label}: {count} binding(s) in error</li>")
                    total_binding_errors += count

            # Count dead-letter webhooks
            dead_count = self.env['shopify.webhook.log'].sudo().search_count([
                ('backend_id', '=', backend.id),
                ('state', '=', 'dead_letter'),
            ])

            # Build digest message
            parts = [
                "<p><strong>🔔 Daily Sync Error Digest</strong></p>",
                f"<p>In the last 24 hours: <b>{len(error_logs)}</b> sync "
                f"run(s) with errors.</p>",
            ]
            if error_lines:
                parts.append(
                    "<p><b>Bindings in error state:</b></p><ul>"
                    + ''.join(error_lines)
                    + "</ul>"
                )
            if dead_count:
                parts.append(
                    f"<p>⚠ <b>{dead_count}</b> dead-letter webhook(s) "
                    "require manual investigation.</p>"
                )
            total = total_binding_errors + dead_count
            if total == 0:
                parts.append(
                    "<p>All sync-run errors were transient (retryable). "
                    "No persistent binding errors.</p>"
                )
            parts.append(
                "<p><i>Tip: open the Shopify backend form → Sync Errors "
                "to review and retry.</i></p>"
            )

            backend.message_post(
                body=''.join(parts),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

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

    @api.model
    def _cron_import_abandoned_carts(self):
        backends = self.search([
            ('state', '=', 'connected'),
            ('auto_sync_abandoned_carts', '=', True),
        ])
        for backend in backends:
            try:
                from ..sync.abandoned_cart_sync import AbandonedCartSync
                syncer = AbandonedCartSync(
                    self.env.with_company(backend.company_id), backend,
                )
                syncer.import_abandoned_carts()
            except Exception as e:
                _logger.exception("Abandoned cart import failed for backend %s", backend.id)
                backend._notify_sync_error('abandoned_carts', 1, str(e))

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
