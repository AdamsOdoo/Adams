from odoo import _, api, models
from odoo.exceptions import UserError


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
        # The setup service has already admitted a Connector Administrator.
        # Payment terms are company configuration, not commerce/PII records,
        # and that role does not necessarily carry Accounting's model ACL.
        # Elevate only this bounded choice projection so setup remains usable;
        # store/settings access and the write below remain caller-governed.
        terms = self.env['account.payment.term'].sudo().search(
            [], order='name, id', limit=200,
        )
        pricelist_domain = [('active', '=', True)]
        if store and store.company_id:
            pricelist_domain += [
                '|', ('company_id', '=', False),
                ('company_id', '=', store.company_id.id),
            ]
        pricelists = self.env['product.pricelist'].sudo().search(
            pricelist_domain, order='name, id', limit=200,
        )
        partner_domain = [('active', '=', True)]
        if store and store.company_id:
            partner_domain += [
                '|', ('company_id', '=', False),
                ('company_id', '=', store.company_id.id),
            ]
        fallback_partners = self.env['res.partner'].sudo().search(
            partner_domain, order='name, id', limit=200,
        )
        payload['order_setup'] = {
            'pricelist_id': (
                settings.order_pricelist_id.id if settings else False
            ),
            'pricelists': [
                {
                    'id': pricelist.id,
                    'name': '%s (%s)' % (
                        pricelist.display_name,
                        pricelist.currency_id.name,
                    ),
                }
                for pricelist in pricelists
            ],
            'payment_term_id': (
                settings.order_payment_term_id.id if settings else False
            ),
            'payment_terms': [
                {'id': term.id, 'name': term.display_name}
                for term in terms
            ],
            'fallback_partner_id': (
                settings.customer_fallback_partner_id.id
                if settings else False
            ),
            'fallback_partners': [
                {'id': partner.id, 'name': partner.display_name}
                for partner in fallback_partners
            ],
        }
        return payload

    @api.model
    def save_directions(
        self, store_id, enabled_keys,
        order_pricelist_id='__not_provided__',
        order_payment_term_id='__not_provided__',
        customer_fallback_partner_id='__not_provided__',
    ):
        # Resolve first so an unauthorized caller always receives AccessError,
        # never configuration feedback about a store they may not inspect.
        store = self._resolve_store(store_id)
        keys = set(enabled_keys or [])
        legacy_omitted = (
            order_pricelist_id == '__not_provided__'
            or order_payment_term_id == '__not_provided__'
            or customer_fallback_partner_id == '__not_provided__'
        )
        if 'sale' in keys and not legacy_omitted:
            if not order_pricelist_id:
                raise UserError(_(
                    'Choose the active pricelist whose currency matches '
                    'Shopify before enabling Orders.'
                ))
            try:
                pricelist_id = int(order_pricelist_id)
            except (TypeError, ValueError):
                raise UserError(_('Choose a valid order pricelist.'))
            pricelist = self.env['product.pricelist'].sudo().browse(
                pricelist_id
            ).exists()
            if not pricelist or not pricelist.active:
                raise UserError(_(
                    'The selected order pricelist is missing or inactive.'
                ))
            if not order_payment_term_id:
                raise UserError(_(
                    'Choose the payment term that imported Shopify orders '
                    'will use before enabling Orders.'
                ))
            try:
                term_id = int(order_payment_term_id)
            except (TypeError, ValueError):
                raise UserError(_('Choose a valid order payment term.'))
            term = self.env['account.payment.term'].sudo().browse(
                term_id
            ).exists()
            if not term:
                raise UserError(_('The selected payment term no longer exists.'))
            if not customer_fallback_partner_id:
                raise UserError(_(
                    'Choose the fallback customer used when a Shopify order '
                    'has no usable customer email before enabling Orders.'
                ))
            try:
                fallback_id = int(customer_fallback_partner_id)
            except (TypeError, ValueError):
                raise UserError(_('Choose a valid fallback customer.'))
            fallback = self.env['res.partner'].sudo().browse(
                fallback_id
            ).exists()
            if not fallback:
                raise UserError(_(
                    'The selected fallback customer no longer exists.'
                ))
            settings = self._settings_for(store)
            settings.write({
                'order_pricelist_id': pricelist.id,
                'order_payment_term_id': term.id,
                'customer_fallback_partner_id': fallback.id,
            })
        payload = super().save_directions(store_id, enabled_keys)
        if 'sale' in keys and legacy_omitted:
            # Older internal callers pre-date the explicit order-defaults
            # argument.  They may enable the domain, but must never silently
            # admit scheduled order imports without their required payment
            # term.  The browser always supplies the argument (including an
            # explicit null, which is refused above); keeping the scheduler
            # off here is the safe compatibility boundary for tests, scripts,
            # and upgraded integrations that still use the old RPC shape.
            settings = self._settings_for(store)
            if settings.order_scheduled_sync_enabled:
                settings.write({'order_scheduled_sync_enabled': False})
            payload = self.get_setup_state(store_id=store.id)
        return payload

    @api.model
    def _readiness_action(self, check, state):
        if check.get('code') == 'sale_order_defaults':
            if state in ('passed', 'not_required'):
                return {}
            return {
                'label': _('Choose imported-order defaults'),
                'step_key': 'directions',
            }
        return super()._readiness_action(check, state)

    @api.model
    def _readiness_label(self, code):
        if code == 'sale_order_defaults':
            return _('Imported-order defaults')
        return super()._readiness_label(code)
