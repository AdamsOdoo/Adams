import logging

from odoo import fields

from .base_exporter import BaseExporter
from .base_importer import BaseImporter
from .checksum import compute_checksum
from ..shopify_api.queries.order import FETCH_ORDERS, ORDER_UPDATE_MUTATION

_logger = logging.getLogger(__name__)


class OrderExporter(BaseExporter):
    entity_name = 'order'
    binding_model = 'shopify.order.binding'

    def _compute_checksum(self, binding):
        order = binding.odoo_id
        return compute_checksum({
            'note': order.note or '',
            'shopify_tags': order.shopify_tags or '',
        })

    def _export_one(self, binding):
        order = binding.odoo_id
        if not binding.shopify_id:
            _logger.warning(
                "Cannot export order %s: no Shopify ID on binding",
                order.name,
            )
            return

        order_input = {
            'id': binding.shopify_id,
            'note': order.note or '',
            'tags': [t.strip() for t in (order.shopify_tags or '').split(',') if t.strip()],
        }
        self.client.execute_mutation(
            ORDER_UPDATE_MUTATION,
            {'input': order_input},
            result_key='orderUpdate',
            estimated_cost=10,
        )


class OrderImporter(BaseImporter):
    entity_name = 'order'
    binding_model = 'shopify.order.binding'

    def _compute_shopify_checksum(self, node):
        return compute_checksum({
            'name': node.get('name', ''),
            'displayFinancialStatus': node.get('displayFinancialStatus', ''),
            'displayFulfillmentStatus': node.get('displayFulfillmentStatus', ''),
            'updatedAt': node.get('updatedAt', ''),
        })

    def _import_one(self, node, existing_binding=None):
        shopify_id = node.get('id')
        checksum = self._compute_shopify_checksum(node)
        financial_status = (node.get('displayFinancialStatus', '') or '').lower()
        fulfillment_status = (node.get('displayFulfillmentStatus', '') or '').lower()

        if existing_binding:
            # Update financial/fulfillment status on existing order
            update_vals = {}
            if existing_binding.shopify_financial_status != financial_status:
                update_vals['shopify_financial_status'] = financial_status
            if existing_binding.shopify_fulfillment_status != fulfillment_status:
                update_vals['shopify_fulfillment_status'] = fulfillment_status
            if update_vals:
                existing_binding.write(update_vals)
                if existing_binding.odoo_id:
                    existing_binding.odoo_id.write({
                        'shopify_financial_status': financial_status,
                        'shopify_fulfillment_status': fulfillment_status,
                    })
            existing_binding._mark_synced(checksum=checksum)
        else:
            order = self._create_sale_order(node)
            if order:
                order_binding = self.env['shopify.order.binding'].create({
                    'backend_id': self.backend.id,
                    'odoo_id': order.id,
                    'shopify_id': shopify_id,
                    'shopify_order_name': node.get('name', ''),
                    'shopify_financial_status': financial_status,
                    'shopify_fulfillment_status': fulfillment_status,
                    'shopify_created_at': node.get('createdAt'),
                    'sync_status': 'synced',
                    'sync_checksum': checksum,
                    'last_sync_date': fields.Datetime.now(),
                })
                self._track_discount_usage(order_binding, node)

    def _create_sale_order(self, node):
        """Create an Odoo sale.order from Shopify order data."""
        partner = self._resolve_customer(node)
        if not partner:
            _logger.warning("Could not resolve customer for order %s", node.get('name'))
            return None

        order_vals = {
            'partner_id': partner.id,
            'shopify_order_name': node.get('name', ''),
            'shopify_financial_status': (node.get('displayFinancialStatus', '') or '').lower(),
            'shopify_fulfillment_status': (node.get('displayFulfillmentStatus', '') or '').lower(),
            'note': node.get('note') or '',
            'company_id': self.backend.company_id.id,
            'warehouse_id': self.backend.warehouse_id.id,
        }

        # Multi-currency support
        if self.backend.import_currency_mode == 'shopify':
            currency_code = (
                node.get('totalPriceSet', {}).get('shopMoney', {}).get('currencyCode', '')
            )
            if currency_code:
                currency = self.env['res.currency'].search([
                    ('name', '=', currency_code),
                    ('active', '=', True),
                ], limit=1)
                if not currency:
                    # Try inactive currencies
                    currency = self.env['res.currency'].search([
                        ('name', '=', currency_code),
                    ], limit=1)
                    if currency:
                        _logger.warning(
                            "Currency %s is inactive; activate it to import "
                            "order %s with correct currency.",
                            currency_code, node.get('name'),
                        )
                        currency = False
                    else:
                        _logger.warning(
                            "Currency %s not found for order %s, "
                            "falling back to company currency.",
                            currency_code, node.get('name'),
                        )
                if currency:
                    company_currency = self.backend.company_id.currency_id
                    if currency != company_currency:
                        order_vals['currency_id'] = currency.id
                        # Find a pricelist with this currency
                        pricelist = self.env['product.pricelist'].search([
                            ('currency_id', '=', currency.id),
                            '|',
                            ('company_id', '=', self.backend.company_id.id),
                            ('company_id', '=', False),
                        ], limit=1)
                        if pricelist:
                            order_vals['pricelist_id'] = pricelist.id

        # Resolve shipping address
        shipping = node.get('shippingAddress')
        if shipping:
            ship_partner = self._get_or_create_address(partner, shipping, 'delivery')
            order_vals['partner_shipping_id'] = ship_partner.id

        # Resolve billing address
        billing = node.get('billingAddress')
        if billing:
            bill_partner = self._get_or_create_address(partner, billing, 'invoice')
            order_vals['partner_invoice_id'] = bill_partner.id

        order = self.env['sale.order'].create(order_vals)

        # Create order lines
        line_items = node.get('lineItems', {}).get('edges', [])
        for edge in line_items:
            li = edge.get('node', {})
            self._create_order_line(order, li)

        # Create shipping line
        shipping_lines = node.get('shippingLines', {}).get('edges', [])
        for edge in shipping_lines:
            sl = edge.get('node', {})
            self._create_shipping_line(order, sl)

        # Confirm order if paid
        if order_vals['shopify_financial_status'] in ('paid', 'partially_paid', 'authorized'):
            order.action_confirm()
            # Auto-create invoice if configured
            if self.backend.auto_create_invoice and order_vals['shopify_financial_status'] == 'paid':
                try:
                    invoice = order._create_invoices()
                    invoice.action_post()
                except Exception as e:
                    _logger.warning("Auto-invoice failed for order %s: %s", order.name, e)

        return order

    def _track_discount_usage(self, order_binding, node):
        """Check for promoter discount codes and record usage."""
        discount_codes = node.get('discountCodes') or []
        if not discount_codes:
            return

        # Get order total from Shopify data
        total_price = float(
            node.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', 0)
        )
        total_discounts = float(
            node.get('totalDiscountsSet', {}).get('shopMoney', {}).get('amount', 0)
        )

        for code_str in discount_codes:
            discount_binding = self.env['shopify.discount.code'].search([
                ('backend_id', '=', self.backend.id),
                ('code', '=ilike', code_str),
            ], limit=1)
            if not discount_binding:
                continue

            # Compute commission
            promoter = discount_binding.promoter_id
            if promoter.commission_type == 'percentage':
                commission = total_price * (promoter.commission_rate / 100.0)
            else:
                commission = promoter.commission_rate

            self.env['shopify.discount.usage'].create({
                'discount_code_id': discount_binding.id,
                'order_binding_id': order_binding.id,
                'discount_amount': total_discounts,
                'order_total': total_price,
                'commission_amount': commission,
                'date': fields.Datetime.now(),
            })

    def _resolve_customer(self, node):
        """Find or create the customer for this order."""
        customer_data = node.get('customer')
        if not customer_data:
            # Use shipping address to create a partner
            shipping = node.get('shippingAddress', {})
            if shipping:
                name = f"{shipping.get('firstName', '')} {shipping.get('lastName', '')}".strip()
                return self.env['res.partner'].create({
                    'name': name or 'Shopify Customer',
                    'customer_rank': 1,
                    'is_shopify_customer': True,
                })
            return None

        shopify_customer_id = customer_data.get('id', '')
        if shopify_customer_id:
            binding = self.env['shopify.customer.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('shopify_id', '=', shopify_customer_id),
            ], limit=1)
            if binding:
                return binding.odoo_id

        # Try by email
        email = customer_data.get('email')
        if email:
            partner = self.env['res.partner'].search([
                ('email', '=ilike', email),
                ('parent_id', '=', False),
            ], limit=1)
            if partner:
                return partner

        # Create new
        first_name = customer_data.get('firstName', '') or ''
        last_name = customer_data.get('lastName', '') or ''
        name = f"{first_name} {last_name}".strip() or email or 'Shopify Customer'
        return self.env['res.partner'].create({
            'name': name,
            'email': email or False,
            'customer_rank': 1,
            'is_shopify_customer': True,
        })

    def _get_or_create_address(self, parent, addr_data, addr_type):
        """Get or create an address partner."""
        country = self._resolve_country(addr_data.get('countryCodeV2'))
        state = self._resolve_state(addr_data.get('provinceCode'), country)

        first_name = addr_data.get('firstName', '') or ''
        last_name = addr_data.get('lastName', '') or ''
        name = f"{first_name} {last_name}".strip() or parent.name

        # Try to find existing child address
        existing = self.env['res.partner'].search([
            ('parent_id', '=', parent.id),
            ('type', '=', addr_type),
            ('street', '=', addr_data.get('address1', '')),
            ('city', '=', addr_data.get('city', '')),
        ], limit=1)
        if existing:
            return existing

        return self.env['res.partner'].create({
            'parent_id': parent.id,
            'type': addr_type,
            'name': name,
            'street': addr_data.get('address1') or False,
            'street2': addr_data.get('address2') or False,
            'city': addr_data.get('city') or False,
            'zip': addr_data.get('zip') or False,
            'country_id': country.id if country else False,
            'state_id': state.id if state else False,
            'phone': addr_data.get('phone') or False,
        })

    def _create_order_line(self, order, line_item):
        """Create a sale.order.line from a Shopify line item."""
        product = self._resolve_product(line_item)
        price_data = line_item.get('originalUnitPriceSet', {}).get('shopMoney', {})
        price_unit = float(price_data.get('amount', 0))

        # Calculate discount
        discount_total = 0
        for alloc in line_item.get('discountAllocations', []):
            discount_total += float(
                alloc.get('allocatedAmountSet', {}).get('shopMoney', {}).get('amount', 0)
            )
        quantity = line_item.get('quantity', 1)
        discount_pct = 0
        if price_unit and quantity:
            discount_pct = (discount_total / (price_unit * quantity)) * 100

        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product.id if product else False,
            'name': line_item.get('title', 'Shopify Item'),
            'product_uom_qty': quantity,
            'price_unit': price_unit,
            'discount': min(discount_pct, 100),
        })

    def _create_shipping_line(self, order, shipping_line):
        """Create a shipping line on the order."""
        price_data = shipping_line.get('originalPriceSet', {}).get('shopMoney', {})
        price = float(price_data.get('amount', 0))
        if not price:
            return

        # Find or create a shipping product
        shipping_product = self.env.ref(
            'adams_shopify.product_shopify_shipping', raise_if_not_found=False,
        )
        if not shipping_product:
            shipping_product = self.env['product.product'].search([
                ('default_code', '=', 'SHOPIFY-SHIPPING'),
            ], limit=1)
        if not shipping_product:
            shipping_product = self.env['product.product'].create({
                'name': 'Shopify Shipping',
                'default_code': 'SHOPIFY-SHIPPING',
                'detailed_type': 'service',
                'list_price': 0,
            })

        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': shipping_product.id,
            'name': shipping_line.get('title', 'Shipping'),
            'product_uom_qty': 1,
            'price_unit': price,
        })

    def _resolve_product(self, line_item):
        """Try to resolve the Odoo product for a Shopify line item."""
        variant_data = line_item.get('variant') or {}
        shopify_variant_id = variant_data.get('id', '')

        if shopify_variant_id:
            vbinding = self.env['shopify.variant.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('shopify_id', '=', shopify_variant_id),
            ], limit=1)
            if vbinding:
                return vbinding.odoo_id

        # Fallback: match by SKU
        sku = variant_data.get('sku', '')
        if sku:
            return self.env['product.product'].search([
                ('default_code', '=', sku),
            ], limit=1)

        return None

    def _resolve_country(self, code):
        if not code:
            return None
        return self.env['res.country'].search([('code', '=', code)], limit=1)

    def _resolve_state(self, state_code, country):
        if not state_code or not country:
            return None
        return self.env['res.country.state'].search([
            ('code', '=', state_code),
            ('country_id', '=', country.id),
        ], limit=1)


class OrderSync:
    """Orchestrates order sync."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.importer = OrderImporter(env, backend)
        self.exporter = OrderExporter(env, backend)

    def export_orders(self):
        return self.exporter.export_batch()

    def import_orders(self):
        nodes = self.importer.client.fetch_paginated(
            FETCH_ORDERS, 'orders',
            page_size=min(self.backend.batch_size, 50),
            estimated_cost_per_page=20,
        )
        return self.importer.import_batch(nodes)

    def import_single_order(self, webhook_data):
        """Import from webhook (REST payload)."""
        shopify_id = f"gid://shopify/Order/{webhook_data.get('id', '')}"
        try:
            from ..shopify_api.client import ShopifyClient
            client = ShopifyClient(self.backend)
            query = """
            query GetOrder($id: ID!) {
              order(id: $id) {
                id name createdAt updatedAt
                displayFinancialStatus displayFulfillmentStatus
                cancelledAt closed note tags
                totalPriceSet { shopMoney { amount currencyCode } }
                totalDiscountsSet { shopMoney { amount currencyCode } }
                discountCodes
                customer { id email firstName lastName }
                shippingAddress {
                  address1 address2 city province provinceCode
                  country countryCodeV2 zip phone firstName lastName
                }
                billingAddress {
                  address1 address2 city province country countryCodeV2 zip
                }
                lineItems(first: 50) {
                  edges {
                    node {
                      id title quantity
                      variant { id sku product { id } }
                      originalUnitPriceSet { shopMoney { amount currencyCode } }
                      discountAllocations {
                        allocatedAmountSet { shopMoney { amount currencyCode } }
                      }
                    }
                  }
                }
                shippingLines(first: 5) {
                  edges {
                    node {
                      title code
                      originalPriceSet { shopMoney { amount currencyCode } }
                    }
                  }
                }
              }
            }
            """
            body = client.execute(query, {'id': shopify_id}, estimated_cost=15)
            node = body.get('data', {}).get('order')
            if node:
                binding = self.importer._find_binding(shopify_id)
                self.importer._import_one(node, binding)
        except Exception:
            _logger.exception("Failed to import order from webhook: %s", shopify_id)
