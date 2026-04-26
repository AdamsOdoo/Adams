# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging
import random
import string
from datetime import timedelta

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ShopifyDemoDataWizard(models.TransientModel):
    _name = 'shopify.demo.data.wizard'
    _description = 'Shopify Demo Data Seeder'

    backend_id = fields.Many2one(
        'shopify.backend', string='Store', required=True,
    )
    seed_products = fields.Boolean('Products', default=True)
    seed_customers = fields.Boolean('Customers', default=True)
    seed_orders = fields.Boolean('Orders', default=True)
    seed_abandoned_carts = fields.Boolean('Abandoned Carts', default=True)
    seed_collections = fields.Boolean('Collections', default=True)
    seed_promoters = fields.Boolean('Promoters', default=True)
    product_count = fields.Integer('Number of Products', default=10)
    customer_count = fields.Integer('Number of Customers', default=15)
    order_count = fields.Integer('Number of Orders', default=20)
    abandoned_cart_count = fields.Integer('Number of Abandoned Carts', default=5)

    def action_seed(self):
        """Generate demo data for testing."""
        self.ensure_one()
        backend = self.backend_id
        results = []

        if self.seed_products:
            count = self._seed_products(backend)
            results.append(_("%d products") % count)

        if self.seed_customers:
            count = self._seed_customers(backend)
            results.append(_("%d customers") % count)

        if self.seed_orders:
            count = self._seed_orders(backend)
            results.append(_("%d orders") % count)

        if self.seed_abandoned_carts:
            count = self._seed_abandoned_carts(backend)
            results.append(_("%d abandoned carts") % count)

        if self.seed_collections:
            count = self._seed_collections(backend)
            results.append(_("%d collections") % count)

        if self.seed_promoters:
            count = self._seed_promoters(backend)
            results.append(_("%d promoters") % count)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Demo Data Created"),
                'message': _("Created: %s") % ', '.join(results),
                'type': 'success',
                'sticky': False,
            },
        }

    def _random_gid(self, entity):
        """Generate a fake Shopify GID."""
        num = random.randint(100000, 9999999)
        return f"gid://shopify/{entity}/{num}"

    def _random_string(self, length=8):
        return ''.join(random.choices(string.ascii_lowercase, k=length))

    # ── Products ────────────────────────────────────────

    _PRODUCT_NAMES = [
        'Organic Cotton T-Shirt', 'Wireless Bluetooth Headphones',
        'Bamboo Water Bottle', 'Leather Messenger Bag',
        'Scented Soy Candle', 'Stainless Steel Watch',
        'Handmade Ceramic Mug', 'Yoga Mat Premium',
        'Artisan Coffee Beans', 'Smart Fitness Tracker',
        'Silk Sleep Mask', 'Portable Phone Charger',
        'Recycled Notebook Set', 'Essential Oil Diffuser',
        'Merino Wool Socks', 'Cast Iron Skillet',
        'Teak Cutting Board', 'Linen Throw Pillow',
        'French Press Coffee Maker', 'Titanium Travel Mug',
    ]

    def _seed_products(self, backend):
        count = min(self.product_count, len(self._PRODUCT_NAMES))
        names = random.sample(self._PRODUCT_NAMES, count)
        created = 0
        for i, name in enumerate(names):
            sku = f"DEMO-{self._random_string(4).upper()}-{i+1:03d}"
            price = round(random.uniform(9.99, 199.99), 2)

            product = self.env['product.product'].create({
                'name': name,
                'default_code': sku,
                'list_price': price,
                'type': 'consu',
            })

            product_binding = self.env['shopify.product.binding'].create({
                'backend_id': backend.id,
                'odoo_id': product.product_tmpl_id.id,
                'shopify_id': self._random_gid('Product'),
                'shopify_handle': name.lower().replace(' ', '-'),
                'shopify_status': random.choice(['active', 'active', 'active', 'draft']),
                'sync_status': random.choice(['synced', 'synced', 'synced', 'error', 'pending']),
                'sync_error': 'Demo error for testing' if random.random() < 0.15 else False,
            })

            self.env['shopify.variant.binding'].create({
                'backend_id': backend.id,
                'odoo_id': product.id,
                'shopify_id': self._random_gid('ProductVariant'),
                'product_binding_id': product_binding.id,
                'sync_status': product_binding.sync_status,
            })
            created += 1
        return created

    # ── Customers ───────────────────────────────────────

    _FIRST_NAMES = [
        'Emma', 'Liam', 'Olivia', 'Noah', 'Ava', 'James', 'Sophia',
        'William', 'Isabella', 'Oliver', 'Mia', 'Benjamin', 'Charlotte',
        'Elijah', 'Amelia',
    ]
    _LAST_NAMES = [
        'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia',
        'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez',
        'Lopez', 'Wilson', 'Anderson', 'Thomas',
    ]

    def _seed_customers(self, backend):
        count = min(self.customer_count, 50)
        created = 0
        for i in range(count):
            first = random.choice(self._FIRST_NAMES)
            last = random.choice(self._LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}.{self._random_string(3)}@example.com"

            partner = self.env['res.partner'].create({
                'name': f"{first} {last}",
                'email': email,
                'phone': f"+1555{random.randint(1000000, 9999999)}",
                'street': f"{random.randint(100, 9999)} {random.choice(['Oak', 'Elm', 'Main', 'Pine', 'Cedar'])} St",
                'city': random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']),
                'zip': f"{random.randint(10000, 99999)}",
                'company_id': backend.company_id.id,
            })

            self.env['shopify.customer.binding'].create({
                'backend_id': backend.id,
                'odoo_id': partner.id,
                'shopify_id': self._random_gid('Customer'),
                'shopify_email': email,
                'sync_status': random.choice(['synced', 'synced', 'synced', 'error']),
                'sync_error': 'Demo sync error' if random.random() < 0.1 else False,
            })
            created += 1
        return created

    # ── Orders ──────────────────────────────────────────

    def _seed_orders(self, backend):
        count = min(self.order_count, 50)
        # Get existing product and customer bindings to reference
        product_bindings = self.env['shopify.variant.binding'].search([
            ('backend_id', '=', backend.id),
        ])
        customer_bindings = self.env['shopify.customer.binding'].search([
            ('backend_id', '=', backend.id),
        ])

        if not product_bindings or not customer_bindings:
            _logger.warning("Need products and customers before seeding orders")
            return 0

        created = 0
        for i in range(count):
            cust_binding = random.choice(customer_bindings)
            partner = cust_binding.odoo_id

            # Create sale order
            order = self.env['sale.order'].create({
                'partner_id': partner.id,
                'sales_channel': 'shopify',
                'shopify_order_name': f"#DEMO-{1000 + i}",
                'company_id': backend.company_id.id,
                'warehouse_id': backend.warehouse_id.id,
            })

            # Add 1-3 random product lines
            line_count = random.randint(1, min(3, len(product_bindings)))
            for vb in random.sample(list(product_bindings), line_count):
                qty = random.randint(1, 5)
                self.env['sale.order.line'].create({
                    'order_id': order.id,
                    'product_id': vb.odoo_id.id,
                    'product_uom_qty': qty,
                    'price_unit': vb.odoo_id.list_price,
                })

            financial = random.choice(['paid', 'paid', 'paid', 'pending', 'partially_paid'])
            fulfillment = random.choice(['unfulfilled', 'unfulfilled', 'fulfilled', 'partial'])

            created_at = fields.Datetime.now() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
            )

            self.env['shopify.order.binding'].create({
                'backend_id': backend.id,
                'odoo_id': order.id,
                'shopify_id': self._random_gid('Order'),
                'shopify_order_name': order.shopify_order_name,
                'shopify_financial_status': financial,
                'shopify_fulfillment_status': fulfillment,
                'shopify_created_at': created_at,
                'sync_status': random.choice(['synced', 'synced', 'synced', 'error']),
                'sync_error': 'Demo order sync error' if random.random() < 0.1 else False,
            })

            # Confirm paid orders
            if financial in ('paid', 'partially_paid'):
                try:
                    order.action_confirm()
                except Exception:
                    pass

            created += 1
        return created

    # ── Abandoned Carts ─────────────────────────────────

    def _seed_abandoned_carts(self, backend):
        import json
        count = min(self.abandoned_cart_count, 20)
        product_bindings = self.env['shopify.variant.binding'].search([
            ('backend_id', '=', backend.id),
        ])

        created = 0
        for i in range(count):
            first = random.choice(self._FIRST_NAMES)
            last = random.choice(self._LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}.cart@example.com"

            line_items = []
            for vb in random.sample(list(product_bindings), min(random.randint(1, 3), len(product_bindings))):
                line_items.append({
                    'title': vb.odoo_id.name,
                    'quantity': random.randint(1, 3),
                    'variant_id': vb.shopify_id,
                    'sku': vb.odoo_id.default_code or '',
                    'price': float(vb.odoo_id.list_price),
                })

            total = sum(li['price'] * li['quantity'] for li in line_items)

            self.env['shopify.abandoned.cart'].create({
                'backend_id': backend.id,
                'shopify_id': self._random_gid('Checkout'),
                'abandoned_at': fields.Datetime.now() - timedelta(
                    days=random.randint(0, 14),
                    hours=random.randint(0, 23),
                ),
                'customer_email': email,
                'customer_name': f"{first} {last}",
                'total_price': round(total, 2),
                'subtotal_price': round(total * 0.9, 2),
                'currency_code': 'USD',
                'line_items_json': json.dumps(line_items),
                'recovery_url': f"https://{backend.shop_url}/checkouts/recover/demo-{self._random_string(8)}",
                'recovered': random.random() < 0.2,
                'sync_status': 'synced',
            })
            created += 1
        return created

    # ── Collections ─────────────────────────────────────

    _COLLECTION_NAMES = [
        'New Arrivals', 'Best Sellers', 'Summer Collection',
        'Winter Essentials', 'Sale Items', 'Premium Selection',
    ]

    def _seed_collections(self, backend):
        created = 0
        for name in self._COLLECTION_NAMES:
            cat = self.env['product.category'].create({
                'name': f"[Shopify] {name}",
            })
            self.env['shopify.collection.binding'].create({
                'backend_id': backend.id,
                'odoo_id': cat.id,
                'shopify_id': self._random_gid('Collection'),
                'shopify_title': name,
                'shopify_handle': name.lower().replace(' ', '-'),
                'product_count': random.randint(3, 25),
                'sync_status': 'synced',
            })
            created += 1
        return created

    # ── Promoters ───────────────────────────────────────

    _PROMOTER_NAMES = [
        ('Sarah', 'Influencer'), ('Mike', 'Affiliate'),
        ('Lisa', 'Partner'), ('Jake', 'Ambassador'),
    ]

    def _seed_promoters(self, backend):
        created = 0
        for name, ptype in self._PROMOTER_NAMES:
            partner = self.env['res.partner'].create({
                'name': f"{name} ({ptype})",
                'email': f"{name.lower()}.{ptype.lower()}@example.com",
                'company_id': backend.company_id.id,
            })
            promoter = self.env['shopify.promoter'].create({
                'name': f"{name} - {ptype}",
                'partner_id': partner.id,
                'company_id': backend.company_id.id,
                'commission_type': random.choice(['percentage', 'fixed']),
                'commission_rate': random.choice([5.0, 10.0, 15.0, 20.0]),
                'status': 'active',
            })
            # Create a discount code for the promoter
            code = f"DEMO-{name.upper()}-{random.randint(10, 99)}"
            self.env['shopify.discount.code'].create({
                'backend_id': backend.id,
                'promoter_id': promoter.id,
                'code': code,
                'shopify_id': self._random_gid('DiscountCodeNode'),
                'discount_type': random.choice(['percentage', 'fixed_amount']),
                'discount_value': random.choice([10, 15, 20, 25]),
            })
            created += 1
        return created
