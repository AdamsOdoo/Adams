import json

from odoo import api, models

# Q7: the accepted API-version compatibility set. `2026-07` is the present
# verified contract; expanding this set requires current official research +
# control-room acceptance (never a silent `latest`, never a fulfillment-only
# pin). Calls go through the core client and `store.api_version`.
FULFILLMENT_ACCEPTED_API_VERSIONS = ('2026-07',)

WRITE_SCOPE = 'write_merchant_managed_fulfillment_orders'


class ShopifyConnectorReadinessCheckFulfillmentExtension(models.AbstractModel):
    """Seam: append fulfillment-domain readiness checks (D-014-2 / Q7 / Q8).

    All checks are pure read-only evaluations (no write/create/unlink/sudo — the
    repo-wide `_check_*` AST guard requires it). When the fulfillment domain is
    disabled every check is not-applicable and passes.
    """

    _inherit = 'shopify.connector.readiness.check'

    @api.model
    def _get_checks(self, store):
        checks = super()._get_checks(store)
        checks.append(self._check_fulfillment_write_scope(store))
        checks.append(self._check_fulfillment_api_version(store))
        checks.append(self._check_fulfillment_staff_permission(store))
        return checks

    @api.model
    def _governed_scope_catalog(self):
        catalog = super()._governed_scope_catalog()
        if not any(entry['scope'] == WRITE_SCOPE for entry in catalog):
            catalog.append({
                'scope': WRITE_SCOPE,
                'reason': (
                    'so reviewed Odoo deliveries can create and update '
                    'merchant-managed Shopify fulfillments'
                ),
            })
        return catalog

    @api.model
    def _fulfillment_enabled(self, store):
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        return bool(settings and settings.fulfillment_domain_enabled)

    @api.model
    def _check_fulfillment_write_scope(self, store):
        """D-014-2 conditional essential check: when the fulfillment domain is
        enabled, `write_merchant_managed_fulfillment_orders` must be present in
        the granted-scopes snapshot."""
        code = 'fulfillment_write_scope'
        if not self._fulfillment_enabled(store):
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_PASS,
                'Not applicable — the fulfillment domain is not enabled for '
                'this store.',
                not_applicable=True,
            )
        if not store.granted_scopes:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'No granted-scopes snapshot recorded for this store yet.',
            )
        try:
            scopes = json.loads(store.granted_scopes)
        except (TypeError, ValueError):
            scopes = None
        if not isinstance(scopes, list) or not scopes:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'Stored granted-scopes snapshot is empty or malformed.',
            )
        if WRITE_SCOPE not in scopes:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'The %s scope is not present in the granted-scopes snapshot.'
                % WRITE_SCOPE,
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_PASS,
            'The fulfillment write scope is granted.',
        )

    @api.model
    def _check_fulfillment_api_version(self, store):
        """Q7 API-version compatibility gate: block unsupported/unverified
        versions; never a fulfillment-only pin, never a silent `latest`."""
        code = 'fulfillment_api_version'
        if not self._fulfillment_enabled(store):
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_PASS,
                'Not applicable — the fulfillment domain is not enabled for '
                'this store.',
                not_applicable=True,
            )
        if not store.api_version:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'No Shopify API version is configured for this store.',
            )
        if store.api_version not in FULFILLMENT_ACCEPTED_API_VERSIONS:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'Store API version %s is outside the accepted fulfillment '
                'compatibility set %s.' % (
                    store.api_version,
                    ', '.join(FULFILLMENT_ACCEPTED_API_VERSIONS),
                ),
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_PASS,
            'Store API version %s is in the accepted fulfillment '
            'compatibility set.' % store.api_version,
        )

    @api.model
    def _check_fulfillment_staff_permission(self, store):
        """Q8 staff-permission axis: `fulfill_and_ship_orders` is a Shopify
        staff permission, a separate axis from API scopes with no proven
        introspection mechanism. It is carried as NOT_PROVEN (never inferred
        from granted scopes) on the warning tier — surfaced, not overall
        fail-closed — while live-mutation qualification stays blocked until it
        is operator-confirmed and dev-store-validated (CV-013 / #185)."""
        code = 'fulfillment_staff_permission'
        if not self._fulfillment_enabled(store):
            return self._check_result(
                code, self.WARNING, self.RESULT_PASS,
                'Not applicable — the fulfillment domain is not enabled for '
                'this store.',
                not_applicable=True,
            )
        # Wave 5: the reason is what an operator READS on the final-readiness
        # step, so it names the two axes as separate things and gives the
        # exact Shopify navigation path rather than a scope handle nobody can
        # act on. The severity, the tier and the not-proven verdict are
        # unchanged -- only the wording an operator has to act on is.
        return self._check_result(
            code, self.WARNING, self.RESULT_NOT_PROVEN,
            'Shopify API scopes and Shopify staff permissions are separate '
            'things, and the connector cannot prove the staff role '
            'automatically. Check it yourself in Shopify Admin -> Settings '
            '-> Users and permissions -> role -> Orders -> Fulfill and ship. '
            'It must also be dev-store verified (CV-013) before live '
            'fulfillment mutation.',
        )
