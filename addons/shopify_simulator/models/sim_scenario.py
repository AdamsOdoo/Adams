# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Scenario Library — pre-built test flows for the simulator.

A scenario is a named, repeatable multi-step test flow that sets up data,
runs connector sync operations, and validates expected outcomes.
Scenarios are defined in code but executed from the UI.
"""
import json
import logging
import traceback

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


# ── Scenario definitions ──────────────────────────────────
# Each scenario is a dict with:
#   key: unique identifier
#   name: human-readable name
#   description: what it tests
#   category: grouping
#   steps: list of (step_name, callable(env, config) → str|None)

def _scenario_happy_path_import(env, config):
    """Set up a complete store and run a full import cycle."""
    from ..fixtures.demo_store import seed_demo_store
    data = seed_demo_store(env, config)
    products = data.get('products', [])
    customers = data.get('customers', [])
    orders = data.get('orders', [])
    return (
        f"Seeded {len(products)} products, {len(customers)} customers, "
        f"{len(orders)} orders. Ready for full import test."
    )


def _scenario_partial_refund(env, config):
    """Create an order with a partial refund."""
    from ..fixtures.demo_store import seed_demo_store
    data = seed_demo_store(env, config)
    order = data['orders'][0]  # First order (paid, unfulfilled)
    Refund = env['sim.shopify.refund']
    RefundLine = env['sim.shopify.refund.line']

    # Get first line item
    line = order.line_item_ids[0]
    refund = Refund.create({
        'config_id': config.id,
        'order_id': order.id,
        'total_refunded': float(line.unit_price),
        'currency_code': order.currency_code,
        'note': 'Partial refund — 1 unit returned',
    })
    RefundLine.create({
        'refund_id': refund.id,
        'line_item_gid': line.shopify_gid,
        'line_item_title': line.title,
        'variant_gid': line.variant_gid,
        'variant_sku': line.sku,
        'quantity': 1,
        'restock_type': 'RETURN',
        'subtotal': float(line.unit_price),
    })
    order.write({'financial_status': 'PARTIALLY_REFUNDED'})
    return (
        f"Order {order.name}: refunded 1x '{line.title}' "
        f"(${line.unit_price}). Status → PARTIALLY_REFUNDED."
    )


def _scenario_rate_limit_exhaustion(env, config):
    """Drain the rate limit bucket to simulate throttling."""
    config.sudo().write({
        'rate_limit_available': 0.0,
        'error_mode': 'rate_limit',
    })
    return (
        "Rate limit bucket drained to 0. Error mode set to 'rate_limit'. "
        "Next API call will receive HTTP 429."
    )


def _scenario_multi_location_inventory(env, config):
    """Set up products with inventory across multiple locations."""
    Product = env['sim.shopify.product']
    Location = env['sim.shopify.location']
    Inventory = env['sim.shopify.inventory.level']

    # Ensure 3 locations
    locations = Location.search([('config_id', '=', config.id)])
    while len(locations) < 3:
        loc = Location.create({
            'config_id': config.id,
            'name': f'Warehouse {len(locations) + 1}',
            'city': ['Dallas', 'London', 'Tokyo'][len(locations)],
            'country_code': ['US', 'GB', 'JP'][len(locations)],
            'is_active': True,
        })
        locations |= loc

    # Create products with split inventory
    product = Product.create({
        'config_id': config.id,
        'title': 'Multi-Location Widget',
        'status': 'ACTIVE',
    })
    product.variant_ids.write({'sku': 'MLW-001', 'price': '49.99'})

    inv_count = 0
    for i, loc in enumerate(locations):
        qty = [100, 50, 25][i] if i < 3 else 10
        Inventory.create({
            'config_id': config.id,
            'variant_id': product.variant_ids[0].id,
            'location_id': loc.id,
            'available': qty,
        })
        inv_count += 1

    return (
        f"Created product with inventory across {len(locations)} locations "
        f"({inv_count} inventory levels). Quantities: 100/50/25."
    )


def _scenario_abandoned_cart_recovery(env, config):
    """Set up abandoned carts with varying customer data."""
    Cart = env['sim.shopify.abandoned.cart']
    customer = env['sim.shopify.customer'].search(
        [('config_id', '=', config.id)], limit=1,
    )
    carts = []
    # Cart with full customer data
    carts.append(Cart.create({
        'config_id': config.id,
        'customer_email': 'alice@example.com',
        'customer_name': 'Alice Johnson',
        'customer_gid': customer.shopify_gid if customer else '',
        'total_price': 149.99,
        'subtotal_price': 139.99,
        'line_items_json': json.dumps([
            {'title': 'Premium Widget', 'quantity': 2, 'price': '69.99'},
        ]),
    }))
    # Anonymous cart
    carts.append(Cart.create({
        'config_id': config.id,
        'customer_email': '',
        'customer_name': '',
        'total_price': 24.99,
        'line_items_json': json.dumps([
            {'title': 'Basic Gadget', 'quantity': 1, 'price': '24.99'},
        ]),
    }))
    return f"Created {len(carts)} abandoned carts (1 known customer, 1 anonymous)."


def _scenario_discount_codes(env, config):
    """Set up various discount code types."""
    DC = env['sim.shopify.discount.code']
    codes = []
    codes.append(DC.create({
        'config_id': config.id,
        'code': 'SAVE10',
        'discount_type': 'percentage',
        'discount_value': 10.0,
        'title': '10% Off Everything',
    }))
    codes.append(DC.create({
        'config_id': config.id,
        'code': 'FLAT20',
        'discount_type': 'fixed_amount',
        'discount_value': 20.0,
        'minimum_order_amount': 100.0,
        'title': '$20 Off Orders Over $100',
    }))
    codes.append(DC.create({
        'config_id': config.id,
        'code': 'FREESHIP',
        'discount_type': 'free_shipping',
        'title': 'Free Shipping',
    }))
    return f"Created {len(codes)} discount codes: SAVE10 (10%), FLAT20 ($20), FREESHIP."


# ── Scenario registry ────────────────────────────────────
SCENARIOS = [
    {
        'key': 'happy_path_import',
        'name': 'Happy Path — Full Import',
        'description': 'Seeds a complete demo store with products, customers, '
                       'orders, and inventory. Ready for a full connector import.',
        'category': 'Import',
        'run': _scenario_happy_path_import,
    },
    {
        'key': 'partial_refund',
        'name': 'Partial Refund Flow',
        'description': 'Creates a paid order and issues a partial refund on '
                       'one line item, setting financial_status to PARTIALLY_REFUNDED.',
        'category': 'Refunds',
        'run': _scenario_partial_refund,
    },
    {
        'key': 'rate_limit_exhaustion',
        'name': 'Rate Limit Exhaustion',
        'description': 'Drains the rate limit bucket and enables rate_limit error mode. '
                       'Tests connector rate-limit retry logic.',
        'category': 'Error Handling',
        'run': _scenario_rate_limit_exhaustion,
    },
    {
        'key': 'multi_location_inventory',
        'name': 'Multi-Location Inventory',
        'description': 'Sets up a product with inventory split across 3 locations '
                       '(US, UK, JP). Tests multi-location inventory sync.',
        'category': 'Inventory',
        'run': _scenario_multi_location_inventory,
    },
    {
        'key': 'abandoned_cart_recovery',
        'name': 'Abandoned Cart Recovery',
        'description': 'Creates abandoned carts with and without customer data. '
                       'Tests abandoned cart import and recovery URL handling.',
        'category': 'Abandoned Carts',
        'run': _scenario_abandoned_cart_recovery,
    },
    {
        'key': 'discount_codes',
        'name': 'Discount Code Varieties',
        'description': 'Creates percentage, fixed-amount, and free-shipping discount codes. '
                       'Tests discount code sync with different types.',
        'category': 'Discounts',
        'run': _scenario_discount_codes,
    },
]


class SimScenario(models.Model):
    _name = 'sim.scenario'
    _description = 'Simulator Scenario'
    _order = 'category, name'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, readonly=True)
    key = fields.Char(string='Key', required=True, readonly=True, index=True)
    description = fields.Text(string='Description', readonly=True)
    category = fields.Char(string='Category', readonly=True)

    @api.model
    def _sync_scenarios(self):
        """Sync scenario records from the SCENARIOS registry.

        Called during module loading to ensure the DB matches code.
        """
        existing = {s.key: s for s in self.search([])}
        for scn in SCENARIOS:
            if scn['key'] in existing:
                existing[scn['key']].write({
                    'name': scn['name'],
                    'description': scn['description'],
                    'category': scn['category'],
                })
            else:
                self.create({
                    'key': scn['key'],
                    'name': scn['name'],
                    'description': scn['description'],
                    'category': scn['category'],
                })

    def action_run(self):
        """Execute this scenario against a config (from context)."""
        self.ensure_one()
        config_id = self.env.context.get('active_config_id')
        if not config_id:
            # Try to find the first config
            config = self.env['sim.shopify.config'].search([], limit=1)
        else:
            config = self.env['sim.shopify.config'].browse(config_id)

        if not config.exists():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Config',
                    'message': 'Please create a simulator config first.',
                    'type': 'warning', 'sticky': False,
                },
            }

        # Find the callable
        runner = None
        for scn in SCENARIOS:
            if scn['key'] == self.key:
                runner = scn['run']
                break

        if not runner:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'No runner found for scenario: {self.key}',
                    'type': 'danger', 'sticky': False,
                },
            }

        try:
            result_msg = runner(self.env, config)
        except Exception as exc:
            _logger.exception("Scenario %s failed", self.key)
            result_msg = f'Error: {exc}'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': f'Scenario Failed: {self.name}',
                    'message': result_msg[:500],
                    'type': 'danger', 'sticky': True,
                },
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': f'Scenario Complete: {self.name}',
                'message': result_msg or 'Done.',
                'type': 'success', 'sticky': False,
            },
        }
