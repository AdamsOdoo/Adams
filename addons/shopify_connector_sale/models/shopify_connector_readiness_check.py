from odoo import _, api, models


class ShopifyConnectorReadinessCheckSaleExtension(models.AbstractModel):
    """Fail closed before an Orders-enabled store can activate incomplete."""

    _inherit = 'shopify.connector.readiness.check'

    @api.model
    def _get_checks(self, store):
        checks = super()._get_checks(store)
        checks.append(self._check_sale_order_defaults(store))
        return checks

    @api.model
    def _check_sale_order_defaults(self, store):
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings or not settings.sale_domain_enabled:
            return self._check_result(
                'sale_order_defaults', self.ESSENTIAL, self.RESULT_PASS,
                _('Not applicable — Orders is not enabled for this store.'),
                not_applicable=True,
            )
        missing = []
        if not settings.order_company_id:
            missing.append(_('order company'))
        if not settings.order_payment_term_id:
            missing.append(_('order payment term'))
        if missing:
            return self._check_result(
                'sale_order_defaults', self.ESSENTIAL, self.RESULT_FAIL,
                _(
                    'Orders cannot start until these imported-order defaults '
                    'are configured: %(names)s.',
                    names=', '.join(missing),
                ),
            )
        return self._check_result(
            'sale_order_defaults', self.ESSENTIAL, self.RESULT_PASS,
            _('The imported-order company and payment term are configured.'),
        )
