from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ShopifyConnectorFulfillmentBinding(models.Model):
    """D-014-1: the fulfillment binding — one row per created Shopify Fulfillment.

    ``shopify_gid`` is the created **Fulfillment** GID (never the
    FulfillmentOrder GID: a backorder chain fulfils one FO through several
    pickings, so FO-GID uniqueness would break — DEC-011). Each validated
    outbound picking is exactly one fulfilment event
    (``UNIQUE(store_id, picking_id)``). Transport idempotency / request-hash
    evidence never lives here — it lives on ``shopify.connector.mutation.attempt``.
    """

    _name = 'shopify.connector.fulfillment.binding'
    _inherit = 'shopify.connector.binding.mixin'
    _description = 'Shopify Connector Fulfillment Binding'

    # SEC-3 (#197): opt in to Odoo 19's native company consistency check
    # (`odoo/orm/models.py` L451/L4516/L4743). Together with `check_company=True`
    # on the business relation below, a store can only ever bind a record of its
    # own company -- enforced on create AND write, and under `sudo()`.
    _check_company_auto = True

    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
        check_company=True,
    )
    order_binding_id = fields.Many2one(
        comodel_name='shopify.connector.order.binding',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    # JSON list of the FulfillmentOrder GIDs this fulfilment was created
    # against (audit; a single fulfilment may span >1 FO at one location).
    shopify_fulfillment_order_gids = fields.Text(readonly=True)
    tracking_numbers_snapshot = fields.Text(readonly=True)
    tracking_company_snapshot = fields.Char(readonly=True)
    tracking_urls_snapshot = fields.Text(readonly=True)
    # The enqueue-time persisted notification decision (RA-009); never re-read
    # at retry, never recomputed.
    notify_customer_sent = fields.Boolean(readonly=True)
    shopify_status_snapshot = fields.Char(readonly=True)
    shopify_status_normalized = fields.Char(readonly=True)
    shopify_last_synced_at = fields.Datetime(readonly=True)

    _store_fulfillment_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_gid)',
        'A fulfillment binding with this Shopify Fulfillment GID already '
        'exists for this store.',
    )
    _store_picking_uniq = models.Constraint(
        'UNIQUE(store_id, picking_id)',
        'This picking already has a fulfillment binding for this store.',
    )

    @api.model
    def _odoo_binding_field_name(self):
        return 'picking_id'

    @api.model
    def _pii_snapshot_fields(self):
        # Recipient names/addresses are never stored on the fulfillment
        # binding (RA-009 redaction discipline; tracking data is not PII).
        return []

    @api.model
    def _additional_protected_binding_fields(self):
        return frozenset((
            'picking_id',
            'order_binding_id',
            'shopify_fulfillment_order_gids',
            'tracking_numbers_snapshot',
            'tracking_company_snapshot',
            'tracking_urls_snapshot',
            'notify_customer_sent',
            'shopify_status_snapshot',
            'shopify_status_normalized',
            'shopify_last_synced_at',
        ))

    @api.constrains('order_binding_id', 'store_id')
    def _check_order_binding_store(self):
        for binding in self:
            if (
                binding.order_binding_id
                and binding.order_binding_id.store_id != binding.store_id
            ):
                raise ValidationError(
                    'A fulfillment binding and its order binding must share '
                    'a store.'
                )

    def action_release_fulfillment_review(self, reason=False):
        """Public Administrator-only review-release action (DEC-038 §7.3): delegates to the
        private sanctioned service helper (defined on the fulfillment service,
        which the review module extends). Never a ``job_type``."""
        self.ensure_one()
        return self.env[
            'shopify.connector.fulfillment.service'
        ]._release_blocked_mutation(self, reason)

    # ------------------------------------------------------------------
    # SEC-3 (#197): same-store consistency with the connector parent.
    #
    # Company equality is NOT enough here. One Odoo company may own several
    # Shopify stores, so a row in store A pointing at a parent in store B is
    # company-consistent and store-inconsistent -- two different shops' records
    # mixed together, which no company check can see. `init()` additionally
    # quarantines rows written before this constraint existed; it never guesses
    # which half is wrong and never re-homes anything.
    # ------------------------------------------------------------------

    @api.model
    def _sec3_parent_scope_relations(self):
        return (('order_binding_id', 'store'),)

    @api.constrains('store_id', 'order_binding_id')
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()
