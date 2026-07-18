import json
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ShopifyConnectorStoreSettingsCustomerExtension(models.Model):
    """Adds the inert fallback-partner configuration field (D5, Posture A).

    Task 011 defines this field as supporting substrate only -- zero
    order-resolution behaviour, zero consumption within Task 011's own
    import/matching flow (see shopify_connector_customer_importer.py,
    which never reads this field), and zero coupling to order import.
    When and how an order routes to this partner, and the order-level
    audit marker that decision requires, are entirely Task 012's own
    future, separately-authorized scope. No default, no auto-creation of
    any partner record, no constraint requiring it, no compute/onchange,
    ordinary write path -- contributed via the core settings extension
    seam, no shopify_connector_core file edit.
    """

    _inherit = 'shopify.connector.store.settings'

    customer_fallback_partner_id = fields.Many2one(
        comodel_name='res.partner',
        ondelete='restrict',
    )

    # Task 012 / DEC-035 order-import policy. Access is inherited from the
    # core store-settings model: all roles read, Administrator writes.
    order_confirmation_policy = fields.Selection(
        selection=[
            ('paid_only', 'Confirm Paid Orders Only'),
            ('paid_or_authorized', 'Confirm Paid or Authorized Orders'),
            ('quotations_only', 'Import as Quotations'),
        ],
        required=True,
        default='paid_only',
    )
    manual_gateway_policy = fields.Selection(
        selection=[
            ('confirm_auto', 'Confirm Automatically'),
            ('quotation', 'Create Quotation'),
            ('require_approval', 'Require Approval'),
        ],
        required=True,
        default='require_approval',
    )
    approved_manual_gateways = fields.Text(
        default='',
        help='One approved Shopify gateway identity per line or comma.',
    )
    order_import_window = fields.Integer(default=30, required=True)
    pending_wait_expiry = fields.Integer(
        default=24,
        required=True,
        help='Pending-payment wait duration in hours (1 to 168).',
    )
    order_import_include_test = fields.Boolean(default=False)
    order_scheduled_sync_enabled = fields.Boolean(default=False)
    order_company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
        ondelete='restrict',
    )
    order_pricelist_id = fields.Many2one(
        comodel_name='product.pricelist', ondelete='restrict',
    )
    order_sales_team_id = fields.Many2one(
        comodel_name='crm.team', ondelete='set null',
    )
    order_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term', ondelete='restrict',
    )
    sale_order_last_import_checkpoint_at = fields.Datetime()

    @api.constrains('order_import_window', 'pending_wait_expiry')
    def _check_order_window_policy(self):
        for settings in self:
            if settings.order_import_window < 1:
                raise ValidationError(
                    'The order import window must be at least one day.'
                )
            if (
                settings.order_import_window > 60
                and 'read_all_orders' not in settings._granted_scope_set()
            ):
                raise ValidationError(
                    'An order import window beyond 60 days requires Shopify '
                    'approval and the granted read_all_orders scope.'
                )
            if not 1 <= settings.pending_wait_expiry <= 24 * 7:
                raise ValidationError(
                    'Pending wait expiry must be between 1 hour and 7 days.'
                )

    @api.constrains(
        'order_company_id', 'order_pricelist_id', 'order_sales_team_id',
        'order_payment_term_id', 'customer_fallback_partner_id',
    )
    def _check_order_pricelist_company(self):
        for settings in self:
            pricelist = settings.order_pricelist_id
            if (
                pricelist
                and pricelist.company_id
                and pricelist.company_id != settings.order_company_id
            ):
                raise ValidationError(
                    'The order pricelist must be company-neutral or belong '
                    'to the configured order company.'
                )
            team = settings.order_sales_team_id
            if (
                team
                and team.company_id
                and team.company_id != settings.order_company_id
            ):
                raise ValidationError(
                    'The order sales team must be company-neutral or belong '
                    'to the configured order company.'
                )
            payment_term = settings.order_payment_term_id
            if (
                payment_term
                and 'company_id' in payment_term._fields
                and payment_term.company_id
                and payment_term.company_id != settings.order_company_id
            ):
                raise ValidationError(
                    'The order payment term must be company-neutral or belong '
                    'to the configured order company.'
                )
            fallback = settings.customer_fallback_partner_id
            if (
                fallback
                and fallback.company_id
                and fallback.company_id != settings.order_company_id
            ):
                raise ValidationError(
                    'The fallback customer must be company-neutral or belong '
                    'to the configured order company.'
                )

    def write(self, vals):
        if 'order_company_id' in vals:
            target_company_id = vals.get('order_company_id') or False
            for settings in self:
                if target_company_id == settings.order_company_id.id:
                    continue
                binding_exists = self.env[
                    'shopify.connector.order.binding'
                ].search_count([('store_id', '=', settings.store_id.id)], limit=1)
                mapping_exists = self.env[
                    'shopify.connector.tax.mapping'
                ].search_count([('store_id', '=', settings.store_id.id)], limit=1)
                if binding_exists or mapping_exists:
                    raise ValidationError(
                        'Order company cannot change after an order binding '
                        'or tax mapping exists for the store.'
                    )
        return super().write(vals)

    def _approved_manual_gateway_set(self):
        self.ensure_one()
        values = re.split(r'[,\n]', self.approved_manual_gateways or '')
        return {
            value.strip().casefold() for value in values if value.strip()
        }

    def _granted_scope_set(self):
        self.ensure_one()
        raw = self.store_id.granted_scopes or ''
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            parsed = re.split(r'[,\s]+', raw)
        if not isinstance(parsed, list):
            return set()
        return {
            str(value).strip() for value in parsed if str(value).strip()
        }
