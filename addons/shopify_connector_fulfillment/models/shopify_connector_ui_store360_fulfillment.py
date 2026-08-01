# Part of the Shopify Connector (Store 360 slice 1, fulfillment-owned
# sections).
#
# Warehouse dispatch (L5) and the fulfillment-evidence lifecycle exception
# items (L7), contributed through the core dashboard's
# `_store_360_extra_sections` seam.
#
# RULING D, stated where it is implemented (spec §6.1): the dispatch block
# is explicitly the RULE-VISIBLE WAREHOUSE POPULATION. It aggregates on
# `stock.picking` as the current user — `stock.picking` ACLs and record
# rules govern these numbers, and they are NOT claimed equal to the
# caller's sale-order rules — and drills down to the native Delivery
# Orders list with the identical domain, so each count is exact on its own
# model. The L7 items stay on their connector evidence models with native
# connector-list drill-downs (the existing tested invariant).

import logging

from odoo import _, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class ShopifyConnectorUiStore360Fulfillment(models.AbstractModel):
    _inherit = 'shopify.connector.ui.dashboard'

    def _store_360_extra_sections(self, ctx):
        sections = super()._store_360_extra_sections(ctx)
        try:
            sections['dispatch'] = self._store_360_dispatch(ctx)
        except AccessError:
            sections['dispatch'] = {
                'available': False, 'reason': 'no_permission',
            }
        lifecycle = sections.get('lifecycle')
        if lifecycle and lifecycle.get('available'):
            lifecycle['exceptions'] = (
                lifecycle.get('exceptions', [])
                + self._store_360_fulfillment_exceptions(ctx)
            )
            settings = self._store_360_fulfillment_settings(ctx)
            if settings:
                lifecycle['fulfillment_observed_through'] = (
                    fields.Datetime.to_string(
                        settings.fulfillment_catchup_observed_through_at)
                    if settings.fulfillment_catchup_observed_through_at
                    else False
                )
        return sections

    def _store_360_fulfillment_settings(self, ctx):
        store = ctx['store']
        if len(store) != 1:
            return False
        return self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )

    # ------------------------------------------------------------------ #
    #  L5 — Odoo warehouse dispatch (rule-visible stock.picking population)
    # ------------------------------------------------------------------ #
    def _store_360_dispatch(self, ctx):
        Picking = self.env['stock.picking']
        store = ctx['store']
        window = ctx['window']
        base = [
            ('picking_type_id.code', '=', 'outgoing'),
            ('location_dest_id.usage', '=', 'customer'),
            ('sale_id', '!=', False),
            ('sale_id.shopify_connector_quarantined', '=', False),
            ('sale_id.shopify_connector_cancelled_at', '=', False),
            ('sale_id.state', '!=', 'cancel'),
            ('sale_id.date_order', '>=', window['start']),
            ('sale_id.date_order', '<', window['end']),
        ]
        if len(store) == 1:
            base.insert(0, ('sale_id.shopify_connector_store_id', '=',
                            store.id))
        else:
            base.insert(0, ('sale_id.shopify_connector_store_id', '!=',
                            False))

        def _serialize(domain):
            return [list(term) for term in domain]

        buckets = []
        for bucket_id, label, extra in (
            ('to_dispatch', _("To dispatch"),
             [('state', 'not in', ('done', 'cancel'))]),
            ('ready', _("Ready"), [('state', '=', 'assigned')]),
            ('dispatched', _("Dispatched"), [('state', '=', 'done')]),
        ):
            domain = base + extra
            buckets.append({
                'id': bucket_id,
                'label': label,
                'count': Picking.search_count(domain),
                'target': {
                    'res_model': 'stock.picking',
                    'domain': _serialize(domain),
                    'name': _("Delivery orders — %s", label),
                },
            })
        return {
            'available': True,
            # The block label the UI must carry (ruling D): these are the
            # deliveries THIS USER can see under Inventory rules.
            'scope_note': _(
                "Odoo delivery status for the deliveries you can see — "
                "governed by your Inventory access, not by sales access."),
            'buckets': buckets,
        }

    # ------------------------------------------------------------------ #
    #  L7 — fulfillment-evidence exception items (connector models)
    # ------------------------------------------------------------------ #
    def _store_360_fulfillment_exceptions(self, ctx):
        store = ctx['store']
        Evidence = self.env[
            'shopify.connector.fulfillment.inbound.evidence'
        ]
        term = []
        if len(store) == 1:
            term = [('store_id', '=', store.id)]

        def _serialize(domain):
            return [list(t) for t in domain]

        items = []
        external_domain = term + [
            ('reconciled_state', '=', 'review'),
            ('review_reason', 'in',
             ('external_fulfillment_observed', 'origin_unconfirmed')),
        ]
        external = Evidence.search_count(external_domain)
        if external:
            items.append({
                'id': 'external_fulfillment',
                'severity': 'warning',
                'title': _("External fulfillment recorded in Shopify"),
                'count': external,
                'why': _("Someone fulfilled these in Shopify outside the "
                         "connector — review how they map to deliveries."),
                'owner': _("Reviewer"),
                'target': {
                    'res_model':
                        'shopify.connector.fulfillment.inbound.evidence',
                    'domain': _serialize(external_domain),
                    'name': _("External fulfillments to review"),
                },
            })
        cancelled_domain = term + [
            ('reconciled_state', '=', 'review'),
            ('review_reason', '=', 'cancelled_after_validation'),
        ]
        cancelled = Evidence.search_count(cancelled_domain)
        if cancelled:
            items.append({
                'id': 'cancelled_after_validation',
                'severity': 'danger',
                'title': _("Shopify cancelled a validated fulfillment"),
                'count': cancelled,
                'why': _("Shopify reports these fulfillments cancelled "
                         "after the delivery was validated in Odoo — "
                         "nothing was auto-reversed."),
                'owner': _("Reviewer"),
                'target': {
                    'res_model':
                        'shopify.connector.fulfillment.inbound.evidence',
                    'domain': _serialize(cancelled_domain),
                    'name': _("Cancelled after validation"),
                },
            })
        unknown_domain = term + [('schema_warning', '=', True)]
        unknown = Evidence.search_count(unknown_domain)
        if unknown:
            items.append({
                'id': 'unknown_fulfillment_status',
                'severity': 'warning',
                'title': _("Unknown fulfillment status observed"),
                'count': unknown,
                'why': _("Shopify returned a status value this connector "
                         "version does not recognise — treated as needing "
                         "review, never as healthy."),
                'owner': _("Reviewer"),
                'target': {
                    'res_model':
                        'shopify.connector.fulfillment.inbound.evidence',
                    'domain': _serialize(unknown_domain),
                    'name': _("Unknown status evidence"),
                },
            })
        return items
