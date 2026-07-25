import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

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
    # SEC-3 (#197): this row points at TWO connector parents (an order binding
    # and a fulfillment binding) that each carry their own store. Company
    # equality cannot catch a cross-store link, because one company may own
    # several stores.
    _inherit = ['shopify.connector.scope.mixin']
    _description = 'Shopify Connector Fulfillment Inbound Evidence'
    _order = 'last_observed_at desc, id desc'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    # SEC-3 (#197): company is inherited from the owning store and is never an
    # independent selector. Stored so record rules, searches and grouped reads
    # filter on it in SQL; readonly so it can never diverge from its store.
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='store_id.company_id',
        store=True,
        index=True,
        readonly=True,
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


    # ------------------------------------------------------------------
    # SEC-3 (#197): same-store consistency with both connector parents.
    #
    # An evidence row names an order binding and a fulfillment binding, each
    # with its own store. Company equality is not enough: one company may own
    # several stores, so an observation recorded against store A could point at
    # store B's order binding and still pass every company check -- two shops'
    # fulfillment records merged, with the per-line ledger (the duplicate-
    # application backstop) computed across both.
    # ------------------------------------------------------------------

    @api.model
    def _sec3_parent_scope_relations(self):
        return (
            ('order_binding_id', 'store'),
            ('fulfillment_binding_id', 'store'),
        )

    @api.constrains('store_id', 'order_binding_id', 'fulfillment_binding_id')
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    @api.model
    def _sec3_quarantine_scope_mismatches(self):
        """Sweep this row's own parents, then its lines' sale-order lines.

        A line has no store, so it cannot be quarantined on its own evidence;
        it inherits the flag from this row. A historic line pointing at another
        company's sale-order line therefore quarantines the EVIDENCE, which
        hides the observation and its whole ledger together. Hiding the line
        while leaving the observation readable would split one record across a
        company boundary.
        """
        quarantined = super()._sec3_quarantine_scope_mismatches()
        # `init()` runs during install, and on a FRESH install the line
        # table does not exist yet when this model is initialised.
        self.env.cr.execute(
            "SELECT to_regclass('public."
            "shopify_connector_fulfillment_inbound_evidence_line')")
        if not self.env.cr.fetchone()[0]:
            return quarantined
        self.env.cr.execute(
            'SELECT DISTINCT line.evidence_id '
            'FROM shopify_connector_fulfillment_inbound_evidence_line line '
            'JOIN shopify_connector_fulfillment_inbound_evidence evidence '
            '  ON evidence.id = line.evidence_id '
            'JOIN sale_order_line sol ON sol.id = line.sale_line_id '
            'JOIN sale_order so ON so.id = sol.order_id '
            'WHERE line.sale_line_id IS NOT NULL '
            '  AND evidence.company_id IS NOT NULL '
            '  AND so.company_id IS NOT NULL '
            '  AND so.company_id != evidence.company_id '
            '  AND evidence.sec3_scope_quarantined = FALSE'
        )
        evidence_ids = [row[0] for row in self.env.cr.fetchall()]
        if evidence_ids:
            _logger.warning(
                'SEC-3 scope quarantine: evidence ids %s own a line whose '
                'sale-order line belongs to another company. The evidence and '
                'its whole ledger are hidden until an administrator resolves '
                'it; nothing was re-homed.', evidence_ids,
            )
            self.env.cr.execute(
                'UPDATE shopify_connector_fulfillment_inbound_evidence '
                'SET sec3_scope_quarantined = TRUE WHERE id IN %s',
                (tuple(evidence_ids),),
            )
            self.invalidate_model(['sec3_scope_quarantined'])
            self.env['shopify.connector.fulfillment.inbound.evidence.line'
                     ].invalidate_model(['sec3_scope_quarantined'])
            quarantined += len(evidence_ids)
        # The lines' stored related flag does not follow a SQL write to their
        # parent. Propagate it, or the ledger stays readable under a hidden
        # observation.
        self._sec3_sync_line_quarantine()
        return quarantined

    def _sec3_sync_line_quarantine(self):
        """Push this row's quarantine flag down onto its lines, in SQL.

        The line's `sec3_scope_quarantined` is a stored RELATED field, and a
        stored related field is only recomputed when its source is written
        **through the ORM**. Both the upgrade sweep and the release action
        write the parent in SQL -- deliberately, because several quarantinable
        models are append-only evidence with a closed `write()` surface -- so
        the related column would never be refreshed and the lines would stay
        readable while their evidence was hidden. That is the same leak one
        level down, so the flag is propagated explicitly.
        """
        self.env.cr.execute(
            'UPDATE shopify_connector_fulfillment_inbound_evidence_line line '
            'SET sec3_scope_quarantined = evidence.sec3_scope_quarantined '
            'FROM shopify_connector_fulfillment_inbound_evidence evidence '
            'WHERE evidence.id = line.evidence_id '
            '  AND line.sec3_scope_quarantined '
            '      IS DISTINCT FROM evidence.sec3_scope_quarantined'
        )
        self.env['shopify.connector.fulfillment.inbound.evidence.line'
                 ].invalidate_model(['sec3_scope_quarantined'])

    def action_sec3_release_scope_quarantine(self):
        result = super().action_sec3_release_scope_quarantine()
        self._sec3_sync_line_quarantine()
        return result

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()


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
    # SEC-3 (#197): one hop further than its parent -- the line has no store of
    # its own, so it inherits the company through the evidence row it belongs
    # to. Without this the lines would be readable across companies even while
    # their parent evidence rows were correctly hidden.
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='evidence_id.store_id.company_id',
        store=True,
        index=True,
        readonly=True,
    )
    # SEC-3 (#197): a line has no store or company of its own -- it is entirely
    # a child of its evidence row -- so it inherits the quarantine too. Without
    # this, quarantining an evidence row would hide the observation while
    # leaving its per-line ledger readable, which is the same leak one level
    # down. Stored so the record rule filters on it in SQL rather than
    # traversing into the parent model (a dotted path would re-enter the parent
    # model's own rules during rule evaluation).
    sec3_scope_quarantined = fields.Boolean(
        related='evidence_id.sec3_scope_quarantined',
        store=True,
        index=True,
        readonly=True,
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

    @api.constrains('evidence_id', 'sale_line_id')
    def _check_sale_line_company(self):
        """The mapped sale-order line must belong to the evidence's company.

        This is the one relation on this model that leaves the connector: a
        line points at a `sale.order.line`. `_check_company_auto` cannot be
        used for it, because the line carries no company column of its own --
        its company is two hops away, through `evidence_id.store_id`. So the
        check is written out.

        The comparison is on COMPANY rather than store on purpose: a sale order
        has no Shopify store, so the company is the strongest agreement that
        exists between the two sides.
        """
        for line in self:
            if not line.sale_line_id or not line.company_id:
                continue
            order_company = line.sale_line_id.order_id.company_id
            if order_company and order_company != line.company_id:
                raise ValidationError(
                    'A fulfillment evidence line and its sale-order line must '
                    'belong to the same company.'
                )
