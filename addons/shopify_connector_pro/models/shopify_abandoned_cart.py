# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import json
import logging

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ShopifyAbandonedCart(models.Model):
    _name = 'shopify.abandoned.cart'
    _inherit = ['shopify.binding']
    _description = 'Shopify Abandoned Cart'
    _order = 'abandoned_at desc'

    # ── Identity ────────────────────────────────────────
    name = fields.Char(
        'Name', compute='_compute_name', store=True, index=True,
    )

    # ── Multi-company ───────────────────────────────────
    company_id = fields.Many2one(
        'res.company', related='backend_id.company_id',
        store=True, index=True, readonly=True,
    )

    # ── Shopify data ────────────────────────────────────
    shopify_checkout_token = fields.Char('Checkout Token', index=True)
    abandoned_at = fields.Datetime('Abandoned At')
    recovery_url = fields.Char('Recovery URL')
    customer_email = fields.Char('Customer Email')
    customer_phone = fields.Char('Customer Phone')
    customer_name = fields.Char('Customer Name')
    shopify_customer_id = fields.Char('Shopify Customer ID')
    total_price = fields.Monetary('Total Price', currency_field='currency_id')
    subtotal_price = fields.Monetary('Subtotal Price', currency_field='currency_id')
    currency_code = fields.Char('Currency Code', default='USD')
    currency_id = fields.Many2one(
        'res.currency', compute='_compute_currency_id', store=True,
    )
    line_items_json = fields.Text(
        'Line Items (JSON)',
        help='Serialized line item data from Shopify.',
    )
    line_item_count = fields.Integer(
        'Item Count', compute='_compute_line_item_count', store=True,
    )

    # ── Odoo links ──────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        help='Linked Odoo customer (if resolved).',
    )
    sale_order_id = fields.Many2one(
        'sale.order', string='Draft Quotation',
        help='Draft quotation created from this abandoned cart.',
    )

    # ── Recovery tracking ───────────────────────────────
    recovered = fields.Boolean(
        'Recovered', default=False, index=True,
        help='Set when a completed order matches this checkout.',
    )
    recovered_order_binding_id = fields.Many2one(
        'shopify.order.binding', string='Recovered Order',
    )
    recovery_email_sent = fields.Boolean('Recovery Email Sent', default=False)


    _backend_shopify_unique = models.Constraint(
        'UNIQUE(backend_id, shopify_id)',
        'Abandoned cart binding must be unique per backend.',
    )

    @api.depends('customer_name', 'customer_email', 'shopify_id')
    def _compute_name(self):
        for rec in self:
            who = rec.customer_name or rec.customer_email or ''
            if rec.shopify_id:
                short_id = (
                    rec.shopify_id.split('/')[-1]
                    if '/' in (rec.shopify_id or '') else rec.shopify_id
                )
                rec.name = f"Cart #{short_id} - {who}" if who else f"Cart #{short_id}"
            else:
                rec.name = who or _('Unknown Cart')

    @api.depends('currency_code')
    def _compute_currency_id(self):
        Currency = self.env['res.currency']
        for rec in self:
            if rec.currency_code:
                currency = Currency.with_context(active_test=False).search([
                    ('name', '=', rec.currency_code),
                ], limit=1)
                rec.currency_id = currency.id if currency else False
            else:
                rec.currency_id = False

    @api.depends('line_items_json')
    def _compute_line_item_count(self):
        for rec in self:
            if rec.line_items_json:
                try:
                    items = json.loads(rec.line_items_json)
                    rec.line_item_count = len(items)
                except (json.JSONDecodeError, TypeError):
                    rec.line_item_count = 0
            else:
                rec.line_item_count = 0

    def get_line_items(self):
        """Return parsed line items list."""
        self.ensure_one()
        if not self.line_items_json:
            return []
        try:
            return json.loads(self.line_items_json)
        except (json.JSONDecodeError, TypeError):
            return []

    def action_create_quotation(self):
        """Manually create a draft quotation from this abandoned cart."""
        self.ensure_one()
        if self.sale_order_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': self.sale_order_id.id,
                'view_mode': 'form',
            }
        order = self._create_draft_quotation()
        if not order:
            raise UserError(_(
                "Cannot create quotation: no customer email or name on this cart."
            ))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
        }

    def _create_draft_quotation(self):
        """Create a draft sale.order from this abandoned cart data."""
        self.ensure_one()
        partner = self._resolve_partner()
        if not partner:
            _logger.warning(
                "Cannot create quotation for abandoned cart %s: no customer",
                self.shopify_id,
            )
            return None

        backend = self.backend_id
        order_vals = {
            'partner_id': partner.id,
            'sales_channel': 'shopify',
            'company_id': backend.company_id.id,
            'warehouse_id': backend.warehouse_id.id,
            'note': _('Created from Shopify abandoned cart (recovery URL: %s)') % (
                self.recovery_url or 'N/A',
            ),
        }

        # Resolve currency (use non-active too; backends may reference inactive)
        if self.currency_code:
            currency = self.env['res.currency'].with_context(
                active_test=False,
            ).search([('name', '=', self.currency_code)], limit=1)
            if currency and currency != backend.company_id.currency_id:
                order_vals['currency_id'] = currency.id
                pricelist = self.env['product.pricelist'].search([
                    ('currency_id', '=', currency.id),
                    ('company_id', 'in', [backend.company_id.id, False]),
                ], limit=1)
                if pricelist:
                    order_vals['pricelist_id'] = pricelist.id
                else:
                    _logger.warning(
                        "No pricelist found for currency %s on backend %s; "
                        "quotation will use company default pricelist",
                        self.currency_code, backend.id,
                    )

        order = self.env['sale.order'].with_context(
            shopify_no_auto_export=True,
        ).create(order_vals)

        # Create order lines from stored line items
        line_items = self.get_line_items()
        for item in line_items:
            self._create_quotation_line(order, item)

        self.write({
            'sale_order_id': order.id,
            'partner_id': partner.id,
        })
        return order

    def _create_quotation_line(self, order, item):
        """Create a sale.order.line from an abandoned cart line item."""
        product = None
        variant_shopify_id = item.get('variant_id')
        sku = item.get('sku')

        # Try to find product by Shopify variant binding. The stored JSON can
        # contain either a full GID or a bare numeric id, so support both.
        if variant_shopify_id:
            if '/' not in str(variant_shopify_id):
                lookup_id = f"gid://shopify/ProductVariant/{variant_shopify_id}"
            else:
                lookup_id = variant_shopify_id
            variant_binding = self.env['shopify.variant.binding'].search([
                ('backend_id', '=', self.backend_id.id),
                ('shopify_id', '=', lookup_id),
            ], limit=1)
            if variant_binding:
                product = variant_binding.odoo_id

        # Fallback to SKU match
        if not product and sku:
            product = self.env['product.product'].search([
                ('default_code', '=', sku),
            ], limit=1)

        quantity = float(item.get('quantity', 1))
        price = float(item.get('price', 0))
        title = item.get('title', 'Unknown Product')

        if product:
            # Create line with product, then write price_unit to override
            # Odoo's onchange-driven recompute from pricelist
            line = self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': product.id,
                'product_uom_qty': quantity,
            })
            line.write({'price_unit': price})
        else:
            # Create a note line for unresolved products
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'display_type': 'line_note',
                'name': f"[Unresolved] {title} (SKU: {sku or 'N/A'}) x{int(quantity)} @ {price}",
            })

    def _resolve_partner(self):
        """Find or create the customer for this abandoned cart."""
        self.ensure_one()
        # Check if already linked
        if self.partner_id:
            return self.partner_id

        # Try by Shopify customer binding. Support both GID and raw id.
        if self.shopify_customer_id:
            if '/' not in str(self.shopify_customer_id):
                lookup_id = f"gid://shopify/Customer/{self.shopify_customer_id}"
            else:
                lookup_id = self.shopify_customer_id
            binding = self.env['shopify.customer.binding'].search([
                ('backend_id', '=', self.backend_id.id),
                ('shopify_id', '=', lookup_id),
            ], limit=1)
            if binding and binding.odoo_id:
                return binding.odoo_id

        # Try by email dedup (normalized, case-insensitive)
        if self.customer_email:
            normalized = tools.email_normalize(self.customer_email)
            if normalized:
                partner = self.env['res.partner'].search([
                    ('email_normalized', '=', normalized),
                    ('parent_id', '=', False),
                ], limit=1)
                if partner:
                    return partner

        # Create new partner
        if self.customer_email or self.customer_name:
            return self.env['res.partner'].create({
                'name': self.customer_name or self.customer_email,
                'email': self.customer_email,
                'phone': self.customer_phone,
                'company_id': self.backend_id.company_id.id,
            })
        return None

    def action_mark_recovered(self):
        """Manually mark this cart as recovered."""
        self.write({'recovered': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Cart Recovered"),
                'message': _("%d cart(s) marked as recovered.") % len(self),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_open_recovery_url(self):
        """Open the Shopify recovery URL in a new tab."""
        self.ensure_one()
        if not self.recovery_url:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("No Recovery URL"),
                    'message': _("This abandoned cart does not have a recovery URL from Shopify."),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.act_url',
            'url': self.recovery_url,
            'target': 'new',
        }
