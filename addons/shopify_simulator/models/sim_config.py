# Part of Shopify Simulator. Internal QA tool — not for public distribution.
import logging
import os
import uuid

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

_RUNNING_ENV = os.environ.get('RUNNING_ENV', os.environ.get('ODOO_STAGE', 'dev'))

# All simulator record models that hold per-config data
_SIM_MODELS = [
    'sim.shopify.product',
    'sim.shopify.customer',
    'sim.shopify.order',
    'sim.shopify.fulfillment',
    'sim.shopify.fulfillment.order',
    'sim.shopify.refund',
    'sim.shopify.webhook.subscription',
    'sim.shopify.inventory.level',
    'sim.shopify.location',
    'sim.shopify.collection',
    'sim.shopify.metafield',
    'sim.shopify.gift.card',
    'sim.shopify.payout',
    'sim.shopify.payout.transaction',
    'sim.shopify.abandoned.cart',
    'sim.shopify.discount.code',
    'sim.shopify.discount.usage',
]


class SimShopifyConfig(models.Model):
    _name = 'sim.shopify.config'
    _description = 'Shopify Simulator Configuration'
    _rec_name = 'shop_name'

    # ── Link to real connector backend ────────────────────
    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
        string='Connector Backend',
        help='The real Shopify Connector Pro backend this simulator stands in for.',
    )

    # ── Simulated shop identity ───────────────────────────
    shop_name = fields.Char(
        string='Shop Name', default='Simulator Store',
        help='Simulated Shopify shop name returned in SHOP_QUERY.',
    )
    shop_email = fields.Char(
        string='Shop Email', default='admin@simulator-store.myshopify.com',
    )
    myshopify_domain = fields.Char(
        string='Myshopify Domain', default='simulator-store.myshopify.com',
    )
    plan_display_name = fields.Char(
        string='Plan Name', default='Development',
    )
    currency_code = fields.Char(
        string='Currency Code', default='USD',
    )
    timezone = fields.Char(
        string='Timezone', default='EST',
    )

    # ── Authentication ────────────────────────────────────
    access_token = fields.Char(
        string='Expected Access Token',
        default=lambda self: f'shpat_sim_{uuid.uuid4().hex[:16]}',
        help='The simulator validates incoming requests against this token.',
    )

    # ── Error / chaos mode ────────────────────────────────
    error_mode = fields.Selection([
        ('none', 'Normal'),
        ('random_errors', 'Random GraphQL Errors'),
        ('always_error', 'Always Return Error'),
        ('rate_limit', 'Rate Limit Exhausted'),
        ('timeout', 'Timeout (35s)'),
        ('user_errors', 'Return userErrors on Mutations'),
    ], default='none', string='Error Mode',
        help='Simulate error conditions for resilience testing.',
    )
    error_rate_pct = fields.Integer(
        string='Error Rate %', default=20,
        help='Probability of random errors (0-100). Used when error_mode=random_errors.',
    )

    # ── Rate limit simulation ─────────────────────────────
    rate_limit_bucket_size = fields.Float(default=1000.0, string='Bucket Size')
    rate_limit_available = fields.Float(default=1000.0, string='Available Budget')
    rate_limit_restore_rate = fields.Float(default=50.0, string='Restore Rate')

    # ── GID sequence counter ──────────────────────────────
    next_gid = fields.Integer(default=1001, string='Next GID Counter')

    # ── Computed: record counts ───────────────────────────
    product_count = fields.Integer(
        compute='_compute_record_counts', string='Products',
    )
    customer_count = fields.Integer(
        compute='_compute_record_counts', string='Customers',
    )
    order_count = fields.Integer(
        compute='_compute_record_counts', string='Orders',
    )
    fulfillment_count = fields.Integer(
        compute='_compute_record_counts', string='Fulfillments',
    )
    refund_count = fields.Integer(
        compute='_compute_record_counts', string='Refunds',
    )
    webhook_count = fields.Integer(
        compute='_compute_record_counts', string='Webhooks',
    )
    location_count = fields.Integer(
        compute='_compute_record_counts', string='Locations',
    )
    inventory_count = fields.Integer(
        compute='_compute_record_counts', string='Inventory Levels',
    )
    collection_count = fields.Integer(
        compute='_compute_record_counts', string='Collections',
    )
    metafield_count = fields.Integer(
        compute='_compute_record_counts', string='Metafields',
    )
    gift_card_count = fields.Integer(
        compute='_compute_record_counts', string='Gift Cards',
    )
    payout_count = fields.Integer(
        compute='_compute_record_counts', string='Payouts',
    )
    abandoned_cart_count = fields.Integer(
        compute='_compute_record_counts', string='Abandoned Carts',
    )
    discount_count = fields.Integer(
        compute='_compute_record_counts', string='Discount Codes',
    )

    # ── Computed: simulator URL ───────────────────────────
    simulator_url = fields.Char(
        compute='_compute_simulator_url', string='Simulator Endpoint',
    )

    def _compute_record_counts(self):
        for rec in self:
            rec.product_count = self.env['sim.shopify.product'].search_count(
                [('config_id', '=', rec.id)])
            rec.customer_count = self.env['sim.shopify.customer'].search_count(
                [('config_id', '=', rec.id)])
            rec.order_count = self.env['sim.shopify.order'].search_count(
                [('config_id', '=', rec.id)])
            rec.fulfillment_count = self.env['sim.shopify.fulfillment'].search_count(
                [('config_id', '=', rec.id)])
            rec.refund_count = self.env['sim.shopify.refund'].search_count(
                [('config_id', '=', rec.id)])
            rec.webhook_count = self.env['sim.shopify.webhook.subscription'].search_count(
                [('config_id', '=', rec.id)])
            rec.location_count = self.env['sim.shopify.location'].search_count(
                [('config_id', '=', rec.id)])
            rec.inventory_count = self.env['sim.shopify.inventory.level'].search_count(
                [('config_id', '=', rec.id)])
            rec.collection_count = self.env['sim.shopify.collection'].search_count(
                [('config_id', '=', rec.id)])
            rec.metafield_count = self.env['sim.shopify.metafield'].search_count(
                [('config_id', '=', rec.id)])
            rec.gift_card_count = self.env['sim.shopify.gift.card'].search_count(
                [('config_id', '=', rec.id)])
            rec.payout_count = self.env['sim.shopify.payout'].search_count(
                [('config_id', '=', rec.id)])
            rec.abandoned_cart_count = self.env['sim.shopify.abandoned.cart'].search_count(
                [('config_id', '=', rec.id)])
            rec.discount_count = self.env['sim.shopify.discount.code'].search_count(
                [('config_id', '=', rec.id)])

    def _compute_simulator_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.simulator_url = (
                f'{base_url}/shopify-sim/{rec.id}/admin/api/2026-01/graphql.json'
                if rec.id else ''
            )

    # ── Safeguard ─────────────────────────────────────────
    @api.constrains('backend_id')
    def _check_not_production(self):
        """Hard safeguard: prevent simulator use in production environments."""
        if _RUNNING_ENV == 'production':
            raise ValidationError(
                "The Shopify Simulator cannot be used in production environments. "
                "This module is for internal development and testing only."
            )

    def _next_gid(self, resource_type):
        """Generate next Shopify-style GID. Thread-safe via SQL."""
        self.ensure_one()
        self.env.cr.execute(
            "UPDATE sim_shopify_config SET next_gid = next_gid + 1 "
            "WHERE id = %s RETURNING next_gid - 1",
            (self.id,),
        )
        seq = self.env.cr.fetchone()[0]
        return f'gid://shopify/{resource_type}/{seq}'

    def _build_extensions(self, estimated_cost=10):
        """Build realistic Shopify-style extensions.cost block."""
        actual_cost = round(estimated_cost * 0.8, 1)
        # Decrease available budget
        new_available = max(0, self.rate_limit_available - actual_cost)
        if self.rate_limit_available != new_available:
            self.sudo().write({'rate_limit_available': new_available})
        return {
            'cost': {
                'requestedQueryCost': estimated_cost,
                'actualQueryCost': actual_cost,
                'throttleStatus': {
                    'maximumAvailable': self.rate_limit_bucket_size,
                    'currentlyAvailable': new_available,
                    'restoreRate': self.rate_limit_restore_rate,
                },
            },
        }

    # ── UI Action Buttons ─────────────────────────────────

    def action_reset_rate_limit(self):
        """Reset rate limit bucket to full."""
        self.sudo().write({'rate_limit_available': self.rate_limit_bucket_size})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Rate Limit Reset',
                'message': f'Budget restored to {self.rate_limit_bucket_size}.',
                'type': 'success', 'sticky': False,
            },
        }

    def action_seed_demo_store(self):
        """Seed demo store data from the UI."""
        self.ensure_one()
        from ..fixtures.demo_store import seed_demo_store
        data = seed_demo_store(self.env, self)
        counts = {k: len(v) if isinstance(v, list) else 1 for k, v in data.items()}
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Demo Store Seeded',
                'message': (
                    f'Created: {counts.get("products", 0)} products, '
                    f'{counts.get("customers", 0)} customers, '
                    f'{counts.get("orders", 0)} orders, '
                    f'{counts.get("locations", 0)} locations.'
                ),
                'type': 'success', 'sticky': False,
            },
        }

    def action_reset_all_data(self):
        """Delete all simulator records for this config."""
        self.ensure_one()
        total = 0
        for model_name in _SIM_MODELS:
            records = self.env[model_name].search([('config_id', '=', self.id)])
            total += len(records)
            records.unlink()
        # Reset the GID counter
        self.write({'next_gid': 1001})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Simulator Data Reset',
                'message': f'{total} records deleted. GID counter reset to 1001.',
                'type': 'warning', 'sticky': False,
            },
        }

    def action_open_seed_wizard(self):
        """Open the advanced seed data wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sim.seed.data.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_config_id': self.id},
        }

    def action_open_checklist(self):
        """Open the validation checklist."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sim.checklist',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_config_id': self.id},
        }

    def action_open_webhook_console(self):
        """Open the webhook test console."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sim.webhook.console',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_config_id': self.id},
        }

    # ── Stat button actions ───────────────────────────────

    def _action_view_records(self, model_name, action_name):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': action_name,
            'res_model': model_name,
            'view_mode': 'list,form',
            'domain': [('config_id', '=', self.id)],
            'context': {'default_config_id': self.id},
        }

    def action_view_products(self):
        return self._action_view_records('sim.shopify.product', 'Products')

    def action_view_customers(self):
        return self._action_view_records('sim.shopify.customer', 'Customers')

    def action_view_orders(self):
        return self._action_view_records('sim.shopify.order', 'Orders')

    def action_view_fulfillments(self):
        return self._action_view_records('sim.shopify.fulfillment', 'Fulfillments')

    def action_view_refunds(self):
        return self._action_view_records('sim.shopify.refund', 'Refunds')

    def action_view_webhooks(self):
        return self._action_view_records(
            'sim.shopify.webhook.subscription', 'Webhook Subscriptions')

    def action_view_locations(self):
        return self._action_view_records('sim.shopify.location', 'Locations')

    def action_view_inventory(self):
        return self._action_view_records(
            'sim.shopify.inventory.level', 'Inventory Levels')

    def action_view_collections(self):
        return self._action_view_records('sim.shopify.collection', 'Collections')

    def action_view_metafields(self):
        return self._action_view_records('sim.shopify.metafield', 'Metafields')

    def action_view_gift_cards(self):
        return self._action_view_records('sim.shopify.gift.card', 'Gift Cards')

    def action_view_payouts(self):
        return self._action_view_records('sim.shopify.payout', 'Payouts')

    def action_view_abandoned_carts(self):
        return self._action_view_records(
            'sim.shopify.abandoned.cart', 'Abandoned Carts')

    def action_view_discounts(self):
        return self._action_view_records(
            'sim.shopify.discount.code', 'Discount Codes')
