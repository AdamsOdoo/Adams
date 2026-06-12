# Part of Shopify Simulator. Internal QA tool — not for public distribution.
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def _money_set(amount, currency='USD', presentment_currency=None):
    """Build a Shopify MoneyV2Set (shopMoney + presentmentMoney)."""
    return {
        'shopMoney': {
            'amount': str(amount),
            'currencyCode': currency,
        },
        'presentmentMoney': {
            'amount': str(amount),
            'currencyCode': presentment_currency or currency,
        },
    }


class SimShopifyOrder(models.Model):
    _name = 'sim.shopify.order'
    _description = 'Simulated Shopify Order'
    _order = 'create_date desc, id desc'
    _rec_name = 'name'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)
    name = fields.Char(string='Order Name', help='e.g. #1001')
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    updated_at = fields.Datetime(default=fields.Datetime.now)
    closed_at = fields.Datetime()
    cancelled_at = fields.Datetime()

    financial_status = fields.Selection([
        ('PENDING', 'Pending'),
        ('AUTHORIZED', 'Authorized'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('PARTIALLY_REFUNDED', 'Partially Refunded'),
        ('REFUNDED', 'Refunded'),
        ('VOIDED', 'Voided'),
    ], default='PAID', required=True)
    fulfillment_status = fields.Selection([
        ('UNFULFILLED', 'Unfulfilled'),
        ('PARTIALLY_FULFILLED', 'Partially Fulfilled'),
        ('FULFILLED', 'Fulfilled'),
    ], default='UNFULFILLED')

    note = fields.Text()
    tags = fields.Char()
    currency_code = fields.Char(default='USD')
    presentment_currency_code = fields.Char(default='USD')
    # Shopify Order.taxesIncluded (Boolean!): line/shipping prices are
    # tax-inclusive when true. Default False = Shopify's default
    # (tax-exclusive pricing).
    taxes_included = fields.Boolean(default=False)

    total_price = fields.Float(default=0.0)
    subtotal_price = fields.Float(default=0.0)
    total_shipping = fields.Float(default=0.0)
    total_tax = fields.Float(default=0.0)
    total_discounts = fields.Float(default=0.0)

    discount_codes_json = fields.Text(
        string='Discount Codes (JSON)',
        help='JSON array of {code, amount, type}',
    )

    customer_id = fields.Many2one('sim.shopify.customer', ondelete='set null')
    line_item_ids = fields.One2many('sim.shopify.order.line', 'order_id')
    shipping_line_ids = fields.One2many('sim.shopify.shipping.line', 'order_id')

    # Shipping address
    ship_first_name = fields.Char()
    ship_last_name = fields.Char()
    ship_address1 = fields.Char()
    ship_address2 = fields.Char()
    ship_city = fields.Char()
    ship_province = fields.Char()
    ship_province_code = fields.Char()
    ship_country = fields.Char()
    ship_country_code = fields.Char()
    ship_zip = fields.Char()
    ship_phone = fields.Char()

    # Billing address (separate from shipping — real Shopify can differ)
    bill_address1 = fields.Char()
    bill_address2 = fields.Char()
    bill_city = fields.Char()
    bill_province = fields.Char()
    bill_country = fields.Char()
    bill_country_code = fields.Char()
    bill_zip = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            config = self.env['sim.shopify.config'].browse(vals.get('config_id'))
            if config and not vals.get('shopify_gid'):
                vals['shopify_gid'] = config._next_gid('Order')
            if not vals.get('name'):
                # Auto-generate order name
                vals['name'] = f'#{1000 + (config.next_gid if config else 1)}'
        records = super().create(vals_list)
        # Auto-create fulfillment orders after line items are available
        # (deferred to write or explicit call since lines are O2M)
        return records

    def action_create_fulfillment_orders(self):
        """Create fulfillment orders for this order's line items.

        Called after order lines have been created. Creates one
        FulfillmentOrder per order (single-location simplification),
        with one FulfillmentOrderLineItem per order line.
        """
        FO = self.env['sim.shopify.fulfillment.order']
        FOLine = self.env['sim.shopify.fulfillment.order.line']

        for order in self:
            if not order.line_item_ids:
                continue

            # Check if FOs already exist
            existing = FO.search([('order_id', '=', order.id)], limit=1)
            if existing:
                continue

            # Find primary location
            location = self.env['sim.shopify.location'].search([
                ('config_id', '=', order.config_id.id),
                ('is_primary', '=', True),
            ], limit=1)

            fo = FO.create({
                'config_id': order.config_id.id,
                'order_id': order.id,
                'status': 'OPEN',
                'assigned_location_id': location.id if location else False,
            })

            for line in order.line_item_ids:
                FOLine.create({
                    'fulfillment_order_id': fo.id,
                    'order_line_id': line.id,
                    'variant_gid': line.variant_gid or '',
                    'sku': line.sku or '',
                    'title': line.title or '',
                    'total_quantity': line.quantity,
                    'remaining_quantity': line.quantity,
                })

    def write(self, vals):
        if 'updated_at' not in vals:
            vals['updated_at'] = fields.Datetime.now()
        return super().write(vals)

    def _to_graphql_node(self):
        """Return dict matching Shopify FETCH_ORDERS GraphQL response shape."""
        self.ensure_one()
        cc = self.currency_code or 'USD'
        pc = self.presentment_currency_code or cc

        customer_node = None
        if self.customer_id:
            c = self.customer_id
            customer_node = {
                'id': c.shopify_gid,
                'email': c.email or '',
                'firstName': c.first_name or '',
                'lastName': c.last_name or '',
                'phone': c.phone or '',
            }

        shipping_address = None
        if self.ship_address1 or self.ship_city:
            shipping_address = {
                'firstName': self.ship_first_name or '',
                'lastName': self.ship_last_name or '',
                'address1': self.ship_address1 or '',
                'address2': self.ship_address2 or '',
                'city': self.ship_city or '',
                'province': self.ship_province or '',
                'provinceCode': self.ship_province_code or '',
                'country': self.ship_country or '',
                'countryCodeV2': self.ship_country_code or '',
                'zip': self.ship_zip or '',
                'phone': self.ship_phone or '',
            }

        line_items_edges = []
        for line in self.line_item_ids:
            line_items_edges.append({'node': line._to_graphql_node(cc, pc)})

        shipping_lines_edges = [
            {'node': sl._to_graphql_node(cc, pc)} for sl in self.shipping_line_ids
        ]

        discount_codes = []
        if self.discount_codes_json:
            try:
                discount_codes = json.loads(self.discount_codes_json)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            'id': self.shopify_gid,
            'name': self.name or '',
            'createdAt': self.created_at.isoformat() + 'Z' if self.created_at else '',
            'updatedAt': self.updated_at.isoformat() + 'Z' if self.updated_at else '',
            'closedAt': self.closed_at.isoformat() + 'Z' if self.closed_at else None,
            'cancelledAt': self.cancelled_at.isoformat() + 'Z' if self.cancelled_at else None,
            'closed': bool(self.closed_at),
            'displayFinancialStatus': self.financial_status,
            'displayFulfillmentStatus': self.fulfillment_status,
            'note': self.note or '',
            'tags': [t.strip() for t in (self.tags or '').split(',') if t.strip()],
            'currencyCode': cc,
            'presentmentCurrencyCode': pc,
            'taxesIncluded': bool(self.taxes_included),
            'totalPriceSet': _money_set(self.total_price, cc, pc),
            'subtotalPriceSet': _money_set(self.subtotal_price, cc, pc),
            'totalShippingPriceSet': _money_set(self.total_shipping, cc, pc),
            'totalTaxSet': _money_set(self.total_tax, cc, pc),
            'totalDiscountsSet': _money_set(self.total_discounts, cc, pc),
            'discountCodes': discount_codes,
            'customer': customer_node,
            'shippingAddress': shipping_address,
            'billingAddress': self._build_billing_address() or shipping_address,
            'lineItems': {
                'edges': line_items_edges,
                'pageInfo': {
                    'hasNextPage': False,
                },
            },
            'shippingLines': {'edges': shipping_lines_edges},
            'refunds': [
                {'id': r.shopify_gid}
                for r in self.env['sim.shopify.refund'].search([
                    ('order_id', '=', self.id),
                ])
            ],
        }

    def _build_billing_address(self):
        """Build billing address dict if billing fields are set, else None."""
        self.ensure_one()
        if not (self.bill_address1 or self.bill_city):
            return None
        # billingAddress in FETCH_ORDERS has fewer fields than shippingAddress
        # (no phone, no firstName/lastName, no provinceCode — see order.py:63-71)
        return {
            'address1': self.bill_address1 or '',
            'address2': self.bill_address2 or '',
            'city': self.bill_city or '',
            'province': self.bill_province or '',
            'country': self.bill_country or '',
            'countryCodeV2': self.bill_country_code or '',
            'zip': self.bill_zip or '',
        }


class SimShopifyOrderLine(models.Model):
    _name = 'sim.shopify.order.line'
    _description = 'Simulated Shopify Order Line Item'
    _order = 'sequence, id'

    order_id = fields.Many2one(
        'sim.shopify.order', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Line Item GID', readonly=True)
    title = fields.Char(required=True)
    quantity = fields.Integer(default=1)
    sku = fields.Char()
    variant_gid = fields.Char(string='Variant GID')
    product_gid = fields.Char(string='Product GID')
    unit_price = fields.Float(default=0.0)
    total_discount = fields.Float(default=0.0)
    tax_amount = fields.Float(default=0.0)
    tax_rate = fields.Float(default=0.0, help='Tax rate as decimal, e.g. 0.10 for 10%')
    sequence = fields.Integer(default=10)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order = self.env['sim.shopify.order'].browse(vals.get('order_id'))
            config = order.config_id if order else None
            if config and not vals.get('shopify_gid'):
                vals['shopify_gid'] = config._next_gid('LineItem')
        return super().create(vals_list)

    def _to_graphql_node(self, currency='USD', presentment_currency='USD'):
        self.ensure_one()
        variant_node = None
        if self.variant_gid:
            variant_node = {
                'id': self.variant_gid,
                'sku': self.sku or '',
                'product': {
                    'id': self.product_gid or '',
                },
            }

        discounts = []
        if self.total_discount:
            discounts.append({
                'allocatedAmountSet': _money_set(
                    self.total_discount, currency, presentment_currency,
                ),
            })

        taxes = []
        if self.tax_amount:
            taxes.append({
                'title': 'Tax',
                'rate': self.tax_rate,
                'priceSet': _money_set(
                    self.tax_amount, currency, presentment_currency,
                ),
            })

        return {
            'id': self.shopify_gid,
            'title': self.title or '',
            'quantity': self.quantity,
            'variant': variant_node,
            'originalUnitPriceSet': _money_set(
                self.unit_price, currency, presentment_currency,
            ),
            'discountAllocations': discounts,
            'taxLines': taxes,
        }


class SimShopifyShippingLine(models.Model):
    _name = 'sim.shopify.shipping.line'
    _description = 'Simulated Shopify Shipping Line'

    order_id = fields.Many2one(
        'sim.shopify.order', required=True, ondelete='cascade', index=True,
    )
    title = fields.Char(default='Standard Shipping')
    code = fields.Char(default='standard')
    price = fields.Float(default=0.0)
    tax_amount = fields.Float(default=0.0)
    tax_rate = fields.Float(
        default=0.0, help='Tax rate as decimal, e.g. 0.10 for 10%',
    )

    def _to_graphql_node(self, currency='USD', presentment_currency='USD'):
        self.ensure_one()
        # Shopify ShippingLine carries taxLines: [TaxLine!]! with the
        # same shape as line-item tax lines (title/rate/priceSet).
        taxes = []
        if self.tax_amount:
            taxes.append({
                'title': 'Tax',
                'rate': self.tax_rate,
                'priceSet': _money_set(
                    self.tax_amount, currency, presentment_currency,
                ),
            })
        return {
            'title': self.title or '',
            'code': self.code or '',
            'originalPriceSet': _money_set(
                self.price, currency, presentment_currency,
            ),
            'taxLines': taxes,
        }
