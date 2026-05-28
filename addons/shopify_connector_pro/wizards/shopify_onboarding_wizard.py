# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ShopifyOnboardingWizard(models.TransientModel):
    _name = 'shopify.onboarding.wizard'
    _description = 'Shopify Store Setup Wizard'

    # Step tracking
    step = fields.Selection([
        ('connection', 'Connection'),
        ('settings', 'Settings'),
        ('webhooks', 'Webhooks'),
        ('import', 'Initial Import'),
        ('done', 'Done'),
    ], default='connection')

    # Connection fields
    name = fields.Char('Store Name', required=True)
    shop_url = fields.Char('Shop URL', required=True)
    access_token = fields.Char('Access Token', required=True)
    webhook_secret = fields.Char('Webhook Secret')

    # Settings
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company,
    )
    warehouse_id = fields.Many2one('stock.warehouse')
    pricelist_id = fields.Many2one('product.pricelist')

    # Import options
    import_products = fields.Boolean(default=True)
    import_customers = fields.Boolean(default=True)
    import_orders = fields.Boolean(default=True)
    order_days = fields.Integer('Import orders from last N days', default=30)

    # Result
    backend_id = fields.Many2one('shopify.backend', readonly=True)
    connection_status = fields.Char(readonly=True)

    @api.model
    def action_open_onboarding(self):
        """Open the onboarding wizard from the empty state banner."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_test_connection(self):
        """Test connection and move to settings step."""
        from ..shopify_api.client import ShopifyClient

        class TempBackend:
            pass

        tmp = TempBackend()
        tmp.shop_url = self.shop_url
        tmp.access_token = self.access_token
        tmp.api_version = '2026-01'
        try:
            client = ShopifyClient(tmp)
            shop = client.fetch_shop_info()
            self.connection_status = _("Connected to %s", shop.get('name', 'Unknown'))
            self.step = 'settings'
        except Exception as e:
            self.connection_status = _("Failed: %s", str(e)[:200])
        return self._reopen()

    def action_next_to_webhooks(self):
        self.step = 'webhooks'
        return self._reopen()

    def action_next_to_import(self):
        """Create the backend and register webhooks."""
        backend = self.env['shopify.backend'].create({
            'name': self.name,
            'shop_url': self.shop_url,
            'access_token': self.access_token,
            'webhook_secret': self.webhook_secret or '',
            'company_id': self.company_id.id,
            'warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
            'pricelist_id': self.pricelist_id.id if self.pricelist_id else False,
            'state': 'connected',
        })
        self.backend_id = backend
        # Register webhooks if secret provided
        if self.webhook_secret:
            try:
                backend.action_register_webhooks()
            except Exception:
                pass  # Non-critical
        # Init field mappings
        backend.action_init_field_mappings()
        self.step = 'import'
        return self._reopen()

    def action_finish(self):
        """Run initial import and close wizard."""
        backend = self.backend_id
        if not backend:
            return {'type': 'ir.actions.act_window_close'}

        errors = []
        imports = [
            (self.import_products, '_cron_sync_products', 'Products'),
            (self.import_customers, '_cron_sync_customers', 'Customers'),
            (self.import_orders, '_cron_import_orders', 'Orders'),
        ]
        for enabled, method, label in imports:
            if enabled:
                try:
                    getattr(backend, method)()
                except Exception as e:
                    _logger.exception("Onboarding import failed for %s", label)
                    errors.append(f"{label}: {str(e)[:100]}")

        if errors:
            # Log the errors to sync log for visibility
            self.env['shopify.sync.log'].create({
                'backend_id': backend.id,
                'entity': 'product',
                'operation': 'import',
                'state': 'error',
                'finished_at': fields.Datetime.now(),
                'error_details': '\n'.join(errors),
                'error_count': len(errors),
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Import Completed with Errors"),
                    'message': _("%d import(s) failed. Check Sync Logs for details.") % len(errors),
                    'type': 'warning',
                    'sticky': True,
                    'next': {
                        'type': 'ir.actions.act_window',
                        'res_model': 'shopify.backend',
                        'res_id': backend.id,
                        'view_mode': 'form',
                        'target': 'current',
                    },
                },
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Import Started"),
                'message': _("Initial import completed. Check Sync Logs or the Health Dashboard for results."),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'shopify.backend',
                    'res_id': backend.id,
                    'view_mode': 'form',
                    'target': 'current',
                },
            },
        }

    def action_skip_import(self):
        """Skip import and go directly to the backend form."""
        if self.backend_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'shopify.backend',
                'res_id': self.backend_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
