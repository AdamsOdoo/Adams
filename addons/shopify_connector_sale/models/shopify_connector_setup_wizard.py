from odoo import _, api, models
from odoo.exceptions import AccessError, UserError


class ShopifyConnectorSetupWizardSaleExtension(models.AbstractModel):
    """Keep the Orders prerequisite inside the guided setup flow."""

    _inherit = 'shopify.connector.setup.wizard'

    @api.model
    def get_setup_state(self, store_id=None, new_store=False):
        payload = super().get_setup_state(
            store_id=store_id, new_store=new_store,
        )
        store = self._resolve_store(store_id) if store_id else False
        settings = self._settings_for(store) if store else False
        terms = self.env['account.payment.term'].search([], order='name, id')
        payload['order_setup'] = {
            'payment_term_id': (
                settings.order_payment_term_id.id if settings else False
            ),
            'payment_terms': [
                {'id': term.id, 'name': term.display_name}
                for term in terms
            ],
        }
        return payload

    @api.model
    def save_directions(
        self, store_id, enabled_keys, order_payment_term_id=None,
    ):
        keys = set(enabled_keys or [])
        if 'sale' in keys:
            if not order_payment_term_id:
                raise UserError(_(
                    'Choose the payment term that imported Shopify orders '
                    'will use before enabling Orders.'
                ))
            try:
                term_id = int(order_payment_term_id)
            except (TypeError, ValueError):
                raise UserError(_('Choose a valid order payment term.'))
            term = self.env['account.payment.term'].browse(term_id).exists()
            if not term:
                raise UserError(_('The selected payment term no longer exists.'))
            try:
                term.check_access('read')
            except AccessError:
                raise UserError(_(
                    'You no longer have access to the selected payment term.'
                ))
            store = self._resolve_store(store_id)
            settings = self._settings_for(store)
            settings.write({'order_payment_term_id': term.id})
        return super().save_directions(store_id, enabled_keys)

    @api.model
    def _readiness_action(self, check, state):
        if check.get('code') == 'sale_order_defaults':
            if state in ('passed', 'not_required'):
                return {}
            return {
                'label': _('Choose order payment term'),
                'step_key': 'directions',
            }
        return super()._readiness_action(check, state)

    @api.model
    def _readiness_label(self, code):
        if code == 'sale_order_defaults':
            return _('Imported-order defaults')
        return super()._readiness_label(code)
