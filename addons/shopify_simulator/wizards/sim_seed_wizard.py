# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Advanced Seed Data Wizard.

Lets users choose exactly which data types to seed, with quantity controls,
instead of using the all-or-nothing seed_demo_store() fixture.
"""
import logging
import random
import string

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Realistic test data pools
_FIRST_NAMES = [
    'Alice', 'Bob', 'Carlos', 'Diana', 'Erik', 'Fatima', 'George', 'Hana',
    'Ivan', 'Julia', 'Karim', 'Lina', 'Marco', 'Nora', 'Oscar', 'Priya',
]
_LAST_NAMES = [
    'Johnson', 'Smith', 'García', 'Lee', 'Müller', 'Patel', 'Dubois',
    'Nakamura', 'Costa', 'Hansen', 'Ali', 'Kim', 'Brown', 'Rossi',
]
_PRODUCT_ADJECTIVES = [
    'Premium', 'Classic', 'Deluxe', 'Pro', 'Ultra', 'Eco', 'Vintage',
    'Modern', 'Artisan', 'Signature', 'Essential', 'Limited Edition',
]
_PRODUCT_NOUNS = [
    'Widget', 'Gadget', 'T-Shirt', 'Mug', 'Notebook', 'Backpack',
    'Watch', 'Headphones', 'Candle', 'Soap', 'Poster', 'Keychain',
]
_VENDORS = [
    'WidgetCo', 'TechBrand', 'FashionHouse', 'HomeGoods', 'ArtisanCraft',
    'EcoLine', 'SportsPro', 'UrbanStyle',
]


class SimSeedDataWizard(models.TransientModel):
    _name = 'sim.seed.data.wizard'
    _description = 'Seed Data Wizard'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade',
        string='Simulator Config',
        default=lambda self: self.env.context.get('default_config_id'),
    )

    # ── Seed options ──────────────────────────────────────
    seed_products = fields.Boolean(string='Seed Products', default=True)
    product_count = fields.Integer(string='Number of Products', default=5)
    variants_per_product = fields.Integer(
        string='Variants per Product', default=1,
        help='1 = simple products, 2-6 = multi-variant products.',
    )

    seed_customers = fields.Boolean(string='Seed Customers', default=True)
    customer_count = fields.Integer(string='Number of Customers', default=3)

    seed_orders = fields.Boolean(string='Seed Orders', default=True)
    order_count = fields.Integer(string='Number of Orders', default=5)

    seed_locations = fields.Boolean(string='Seed Locations', default=True)
    location_count = fields.Integer(string='Number of Locations', default=1)

    seed_inventory = fields.Boolean(
        string='Seed Inventory Levels', default=True,
        help='Requires products and locations to exist.',
    )

    seed_mode = fields.Selection([
        ('append', 'Append to existing data'),
        ('replace', 'Clear existing data first'),
    ], default='append', string='Seed Mode', required=True)

    use_demo_store = fields.Boolean(
        string='Use Curated Demo Store',
        default=False,
        help='Instead of random data, use the curated demo store fixture '
             'with realistic edge cases (Arabic text, missing SKUs, etc.).',
    )

    def action_seed(self):
        """Execute the seed operation."""
        self.ensure_one()
        config = self.config_id

        if self.use_demo_store:
            from ..fixtures.demo_store import seed_demo_store
            if self.seed_mode == 'replace':
                config.action_reset_all_data()
            data = seed_demo_store(self.env, config)
            counts = {k: len(v) if isinstance(v, list) else 1
                      for k, v in data.items()}
            msg = (
                f"Demo store seeded: {counts.get('products', 0)} products, "
                f"{counts.get('customers', 0)} customers, "
                f"{counts.get('orders', 0)} orders, "
                f"{counts.get('locations', 0)} locations."
            )
        else:
            if self.seed_mode == 'replace':
                config.action_reset_all_data()
            msg = self._seed_random_data(config)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Seed Complete',
                'message': msg,
                'type': 'success',
                'sticky': False,
            },
        }

    def _seed_random_data(self, config):
        """Generate random but realistic test data."""
        cid = config.id
        created = {}

        # ── Locations ─────────────────────────────────────
        if self.seed_locations:
            Location = self.env['sim.shopify.location']
            locs = []
            for i in range(self.location_count):
                is_primary = i == 0 and not Location.search(
                    [('config_id', '=', cid), ('is_primary', '=', True)], limit=1,
                )
                loc = Location.create({
                    'config_id': cid,
                    'name': f'Warehouse {i + 1}' if i > 0 else 'Main Warehouse',
                    'address1': f'{random.randint(1, 999)} Commerce Ave',
                    'city': random.choice([
                        'Dallas', 'New York', 'London', 'Berlin', 'Tokyo',
                    ]),
                    'country_code': random.choice(['US', 'GB', 'DE', 'JP']),
                    'is_active': True,
                    'is_primary': is_primary,
                })
                locs.append(loc)
            created['locations'] = len(locs)

        # ── Products ──────────────────────────────────────
        products = []
        if self.seed_products:
            Product = self.env['sim.shopify.product']
            Variant = self.env['sim.shopify.variant']
            for _i in range(self.product_count):
                adj = random.choice(_PRODUCT_ADJECTIVES)
                noun = random.choice(_PRODUCT_NOUNS)
                title = f'{adj} {noun}'
                product = Product.create({
                    'config_id': cid,
                    'title': title,
                    'vendor': random.choice(_VENDORS),
                    'product_type': noun,
                    'status': random.choices(
                        ['ACTIVE', 'DRAFT', 'ARCHIVED'],
                        weights=[80, 15, 5],
                    )[0],
                    'tags': ','.join(random.sample(
                        ['sale', 'new', 'featured', 'clearance', 'premium'],
                        k=random.randint(1, 3),
                    )),
                })
                # Handle variants
                num_variants = min(self.variants_per_product, 6)
                if num_variants <= 1:
                    # Simple product — update default variant
                    for v in product.variant_ids:
                        v.write({
                            'sku': self._random_sku(),
                            'price': str(round(random.uniform(5, 200), 2)),
                        })
                else:
                    # Multi-variant — delete default and create custom
                    product.variant_ids.unlink()
                    sizes = ['S', 'M', 'L', 'XL'][:num_variants]
                    for size in sizes:
                        Variant.create({
                            'product_id': product.id,
                            'title': size,
                            'sku': self._random_sku(),
                            'price': str(round(random.uniform(10, 150), 2)),
                            'option1_name': 'Size',
                            'option1_value': size,
                        })
                products.append(product)
            created['products'] = len(products)

        # ── Inventory ─────────────────────────────────────
        if self.seed_inventory and products:
            Inventory = self.env['sim.shopify.inventory.level']
            Location = self.env['sim.shopify.location']
            locations = Location.search([('config_id', '=', cid)])
            inv_count = 0
            for prod in products:
                for variant in prod.variant_ids:
                    for loc in locations:
                        Inventory.create({
                            'config_id': cid,
                            'variant_id': variant.id,
                            'location_id': loc.id,
                            'available': random.randint(0, 200),
                        })
                        inv_count += 1
            created['inventory_levels'] = inv_count

        # ── Customers ─────────────────────────────────────
        customers = []
        if self.seed_customers:
            Customer = self.env['sim.shopify.customer']
            for _i in range(self.customer_count):
                first = random.choice(_FIRST_NAMES)
                last = random.choice(_LAST_NAMES)
                cust = Customer.create({
                    'config_id': cid,
                    'first_name': first,
                    'last_name': last,
                    'email': f'{first.lower()}.{last.lower()}@example.com',
                    'phone': f'+1{random.randint(2000000000, 9999999999)}',
                    'address1': f'{random.randint(1, 999)} Test Street',
                    'city': random.choice([
                        'San Francisco', 'Austin', 'Chicago', 'Miami',
                    ]),
                    'province_code': random.choice(['CA', 'TX', 'IL', 'FL']),
                    'country_code': 'US',
                    'zip_code': f'{random.randint(10000, 99999)}',
                })
                customers.append(cust)
            created['customers'] = len(customers)

        # ── Orders ────────────────────────────────────────
        if self.seed_orders and products and customers:
            Order = self.env['sim.shopify.order']
            OrderLine = self.env['sim.shopify.order.line']
            # Get the current max order number
            existing = Order.search(
                [('config_id', '=', cid)], order='id desc', limit=1,
            )
            order_num = 1001
            if existing and existing.name:
                try:
                    order_num = int(existing.name.lstrip('#')) + 1
                except (ValueError, AttributeError):
                    pass

            for i in range(self.order_count):
                customer = random.choice(customers)
                num_lines = random.randint(1, min(3, len(products)))
                order_products = random.sample(products, num_lines)
                subtotal = 0.0

                order = Order.create({
                    'config_id': cid,
                    'name': f'#{order_num + i}',
                    'financial_status': random.choice([
                        'PAID', 'PAID', 'PAID', 'PENDING', 'AUTHORIZED',
                    ]),
                    'fulfillment_status': 'UNFULFILLED',
                    'currency_code': config.currency_code or 'USD',
                    'customer_id': customer.id,
                    'ship_first_name': customer.first_name,
                    'ship_last_name': customer.last_name,
                    'ship_address1': customer.address1 or '123 Test St',
                    'ship_city': customer.city or 'Test City',
                    'ship_country_code': customer.country_code or 'US',
                })

                for prod in order_products:
                    variant = prod.variant_ids[:1]
                    if not variant:
                        continue
                    qty = random.randint(1, 5)
                    price = float(variant.price or '10.00')
                    line_total = round(qty * price, 2)
                    subtotal += line_total
                    OrderLine.create({
                        'order_id': order.id,
                        'title': prod.title,
                        'quantity': qty,
                        'sku': variant.sku or '',
                        'variant_gid': variant.shopify_gid,
                        'product_gid': prod.shopify_gid,
                        'unit_price': price,
                    })

                shipping = round(random.choice([0.0, 5.0, 7.99, 12.50]), 2)
                tax = round(subtotal * 0.08, 2)
                order.write({
                    'subtotal_price': subtotal,
                    'total_shipping': shipping,
                    'total_tax': tax,
                    'total_price': round(subtotal + shipping + tax, 2),
                })
            created['orders'] = self.order_count

        parts = [f"{v} {k}" for k, v in created.items()]
        return f"Created: {', '.join(parts)}." if parts else "Nothing to seed."

    @staticmethod
    def _random_sku():
        prefix = ''.join(random.choices(string.ascii_uppercase, k=3))
        suffix = ''.join(random.choices(string.digits, k=4))
        return f'{prefix}-{suffix}'
