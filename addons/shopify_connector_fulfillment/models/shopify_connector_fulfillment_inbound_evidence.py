from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Origin classification (Modes §3). The own-GID ledger is the authoritative
# signal; there is no app-attribution field on the Fulfillment object, so
# unknown origin is classified external but never treated as confirmed-external
# for automation (Mode 2 condition 15).
ORIGIN_CLASS_SELECTION = [
    ('connector', 'Connector-Created'),
    ('external_merchant', 'External — Merchant'),
    ('external_app', 'External — App/Service'),
    ('external_unknown', 'External — Unknown Origin'),
]

# Domain-owned review-case vocabulary (Modes §4 named reasons + the
# carrier/delivered/cancelled cases). This is NOT the core
# manual_review_subreason registry — a fulfillment review case that must also
# block a core job maps to an accepted core error_class/subreason separately
# (DEC-038 §7.2). `over_fulfillment` is deliberately absent (removed
# vocabulary); the quantity-overrun case uses `quantity_overrun` here and
# persists `ambiguous_match` on any core job.
REVIEW_REASON_SELECTION = [
    ('order_binding_missing', 'Order Binding Missing'),
    ('fulfillment_state_not_success', 'Fulfillment State Not SUCCESS'),
    ('fulfillment_order_unresolved', 'FulfillmentOrder Unresolved'),
    ('product_binding_missing', 'Product Binding Missing'),
    ('line_mapping_ambiguous', 'Line Mapping Ambiguous'),
    ('quantity_overrun', 'Quantity Exceeds Remaining'),
    ('quantity_mismatch', 'Quantity Mismatch'),
    ('location_unmapped', 'Location Unmapped'),
    ('picking_ambiguous', 'Picking Ambiguous'),
    ('reservation_invalid', 'Reservation Invalid'),
    ('lot_serial_ambiguous', 'Lot/Serial Ambiguous'),
    ('already_reconciled', 'Already Reconciled'),
    ('binding_conflict', 'Fulfillment Binding Conflict'),
    ('remote_state_changed', 'Remote State Changed'),
    ('origin_unconfirmed', 'Origin Unconfirmed'),
    ('mode_not_enabled', 'Mode 2 Not Enabled'),
    ('carrier_would_book', 'Carrier Flow Would Book/Charge'),
    ('delivered_not_validated', 'Delivered Per Carrier — Odoo Not Validated'),
    ('cancelled_after_validation', 'Shopify Cancelled After Odoo Validation'),
    ('unknown_status_value', 'Unknown Status Value'),
    # Theme H (decision-lock Decision C): the routine Mode-1 "confirmed-
    # external fulfillment observed" baseline case -- distinct from
    # `remote_state_changed` (Condition 14's narrow live-second-read-changed
    # gate) and `mode_not_enabled` (Condition 16's mid-flight mode-switch
    # cancellation). Zero Odoo stock modification either way.
    ('external_fulfillment_observed', 'External Fulfillment Observed'),
]

RECONCILED_STATE_SELECTION = [
    ('observed', 'Observed'),
    ('review', 'Review Case Open'),
    ('acknowledged', 'Acknowledged (Handled Outside Odoo)'),
    ('applied', 'Applied to Odoo'),
    ('superseded', 'Superseded'),
]


class ShopifyConnectorFulfillmentInboundEvidence(models.Model):
    """Per-fulfillment inbound observation + origin classification (Modes §3/§5).

    Records every observed Shopify Fulfillment with its raw + normalized state
    (the seven Layer-A families), its origin classification, and a per-line
    reconciled-quantity ledger. Externally-created fulfillments become review
    cases (zero automatic Odoo stock change). The unique Fulfillment GID plus
    the per-line ledger are the duplicate-application backstop (Mode 2
    condition 12).
    """

    _name = 'shopify.connector.fulfillment.inbound.evidence'
    _description = 'Shopify Connector Fulfillment Inbound Evidence'
    _order = 'last_observed_at desc, id desc'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    order_binding_id = fields.Many2one(
        comodel_name='shopify.connector.order.binding',
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    fulfillment_binding_id = fields.Many2one(
        comodel_name='shopify.connector.fulfillment.binding',
        index=True,
        readonly=True,
        ondelete='set null',
    )
    shopify_fulfillment_gid = fields.Char(required=True, index=True, readonly=True)
    shopify_order_gid = fields.Char(index=True, readonly=True)

    origin_class = fields.Selection(
        selection=ORIGIN_CLASS_SELECTION,
        required=True,
        default='external_unknown',
        readonly=True,
    )
    # external_* origins are "confirmed external" only when the own-GID ledger
    # positively excludes connector origin; an unknown-pending observation is
    # not confirmed-external for automation (Mode 2 condition 15).
    origin_confirmed = fields.Boolean(default=False, readonly=True)

    # A4 FulfillmentStatus — the Mode 2 condition-2 automation gate.
    fulfillment_status_raw = fields.Char(readonly=True)
    fulfillment_status_normalized = fields.Char(readonly=True)
    fulfillment_status_is_success = fields.Boolean(default=False, readonly=True)
    # A7 FulfillmentDisplayStatus — display only, never an automation input.
    display_status_raw = fields.Char(readonly=True)
    display_status_normalized = fields.Char(readonly=True)
    # JSON snapshot of every observed Layer-A family value (raw), for audit and
    # the Wave 5 badge taxonomy.
    state_snapshot = fields.Text(readonly=True)
    # Unknown-future-value contract (status model §7): an enum value outside
    # the verified set is preserved raw, flagged, never treated as success.
    schema_warning = fields.Boolean(default=False, readonly=True)
    # A5 DELIVERED milestone while the Odoo picking is not `done`
    # (status model §8): a milestone never writes stock.
    delivered_inconsistency = fields.Boolean(default=False, readonly=True)

    tracking_snapshot = fields.Text(readonly=True)

    reconciled_state = fields.Selection(
        selection=RECONCILED_STATE_SELECTION,
        required=True,
        default='observed',
        index=True,
        readonly=True,
    )
    review_reason = fields.Selection(
        selection=REVIEW_REASON_SELECTION,
        readonly=True,
    )
    # Sanitized structured detail (e.g. the over-fulfillment amounts) — never a
    # persisted core selection value.
    review_detail = fields.Text(readonly=True)
    resolution_actor_uid = fields.Many2one('res.users', readonly=True)
    resolution_at = fields.Datetime(readonly=True)

    first_observed_at = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    last_observed_at = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    line_ids = fields.One2many(
        comodel_name='shopify.connector.fulfillment.inbound.evidence.line',
        inverse_name='evidence_id',
        readonly=True,
    )

    _store_fulfillment_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_fulfillment_gid)',
        'Inbound evidence for this Shopify Fulfillment GID already exists for '
        'this store.',
    )

    @api.constrains('reconciled_state', 'review_reason')
    def _check_review_reason(self):
        for record in self:
            if record.reconciled_state == 'review' and not record.review_reason:
                raise ValidationError(
                    'A fulfillment review case requires a named review reason.'
                )

    def reconciled_quantity_ledger(self):
        """Return {fo_line_item_gid: reconciled_quantity} — the per-line
        applied ledger used by the no-over-fulfillment / no-duplicate checks."""
        self.ensure_one()
        ledger = {}
        for line in self.line_ids:
            if line.fo_line_item_gid:
                ledger[line.fo_line_item_gid] = (
                    ledger.get(line.fo_line_item_gid, 0)
                    + (line.reconciled_quantity or 0)
                )
        return ledger


class ShopifyConnectorFulfillmentInboundEvidenceLine(models.Model):
    """Per-line inbound evidence + the reconciled-quantity ledger row."""

    _name = 'shopify.connector.fulfillment.inbound.evidence.line'
    _description = 'Shopify Connector Fulfillment Inbound Evidence Line'

    evidence_id = fields.Many2one(
        comodel_name='shopify.connector.fulfillment.inbound.evidence',
        required=True,
        index=True,
        readonly=True,
        ondelete='cascade',
    )
    fo_line_item_gid = fields.Char(index=True, readonly=True)
    line_item_gid = fields.Char(index=True, readonly=True)
    sale_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        index=True,
        readonly=True,
        ondelete='set null',
    )
    quantity = fields.Integer(default=0, readonly=True)
    reconciled_quantity = fields.Integer(default=0, readonly=True)

    _non_negative_quantity = models.Constraint(
        'CHECK(quantity >= 0 AND reconciled_quantity >= 0)',
        'Fulfillment evidence quantities cannot be negative.',
    )
