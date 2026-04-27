# Part of Shopify Simulator. Internal QA tool — not for public distribution.
import logging
import os
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

_RUNNING_ENV = os.environ.get('RUNNING_ENV', os.environ.get('ODOO_STAGE', 'dev'))


class ShopifyBackendSimulator(models.Model):
    _inherit = 'shopify.backend'

    use_simulator = fields.Boolean(
        string='Use Simulator',
        default=False,
        help='When enabled, API calls go to the local Shopify Simulator '
             'instead of a real Shopify store. Only available in dev/test.',
    )
    sim_config_id = fields.Many2one(
        'sim.shopify.config',
        string='Simulator Config',
        ondelete='set null',
        help='The simulator configuration providing fake Shopify data.',
    )

    @api.constrains('use_simulator')
    def _check_simulator_not_production(self):
        for rec in self:
            if rec.use_simulator and _RUNNING_ENV == 'production':
                raise ValidationError(
                    "Simulator mode cannot be enabled in production environments."
                )

    @api.constrains('shop_url')
    def _check_shop_url(self):
        """Override: allow non-myshopify URLs when simulator mode is active."""
        pattern = re.compile(
            r'^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$'
        )
        for rec in self:
            if rec.use_simulator:
                # In simulator mode, any URL that starts with http is OK
                url = (rec.shop_url or '').strip()
                if not url:
                    raise ValidationError("Shop URL is required even in simulator mode.")
                continue
            # Standard validation for real Shopify stores
            url = (rec.shop_url or '').strip().rstrip('/')
            if '://' in url:
                url = url.split('://', 1)[1]
            url = url.split('/')[0]
            if not pattern.match(url):
                raise ValidationError(
                    "Shop URL must be a valid myshopify.com domain "
                    "(e.g. my-store.myshopify.com). Got: %s" % rec.shop_url,
                )

    @api.constrains('access_token')
    def _check_access_token(self):
        """Override: allow non-shpat_ tokens when simulator mode is active."""
        for rec in self:
            if rec.use_simulator:
                continue
            token = rec.access_token or ''
            if token and not token.startswith('shpat_'):
                raise ValidationError(
                    "Access token should start with 'shpat_'. "
                    "Please use a valid Shopify Admin API access token."
                )

    def _make_api_client(self):
        """Override: return SimulatorClient when simulator mode is active."""
        if self.use_simulator and self.sim_config_id:
            from ..lib.simulator_client import SimulatorClient
            return SimulatorClient(self)
        return super()._make_api_client()

    def action_create_simulator(self):
        """Quick action: create a simulator config and link it to this backend."""
        self.ensure_one()
        if _RUNNING_ENV == 'production':
            raise ValidationError("Simulator cannot be created in production.")
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        config = self.env['sim.shopify.config'].create({
            'backend_id': self.id,
            'shop_name': f'Sim - {self.name}',
        })
        self.write({
            'use_simulator': True,
            'sim_config_id': config.id,
            'shop_url': f'{base_url}/shopify-sim/{config.id}',
            'access_token': config.access_token,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Simulator Created',
                'message': f'Simulator config #{config.id} created and linked.',
                'type': 'success',
                'sticky': False,
            },
        }
