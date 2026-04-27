# Part of Shopify Simulator. Internal QA tool — not for public distribution.
import logging
import os
import uuid

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

_RUNNING_ENV = os.environ.get('RUNNING_ENV', os.environ.get('ODOO_STAGE', 'dev'))


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

    def _reset_rate_limit(self):
        """Reset rate limit bucket to full (call from tests or UI)."""
        self.sudo().write({'rate_limit_available': self.rate_limit_bucket_size})
