# Part of the Shopify Connector (Store 360 slice 1).
#
# Protected sale-order projection of connector order evidence.
#
# WHY THESE COLUMNS EXIST. The Store 360 dashboard aggregates commercial and
# lifecycle numbers as the CURRENT USER with the caller's own `sale.order`
# ACLs and record rules active, and drills down to a native `sale.order`
# list built from the very same domain. That is only rule-safe when the
# aggregate model, the rule model and the drill-down model are the same
# model (spec §6.1, accepted 2026-08-01) — so the connector dimensions the
# aggregation needs (store, cancellation, quarantine, and the lifecycle
# snapshots) must exist ON `sale.order` itself. They are maintained as a
# read-only projection of the order binding, written in the SAME transaction
# as the authoritative binding change, by the same sanctioned writers.
#
# WRITE PROTECTION (non-forgeable — PR #204 P0-1 correction, 2026-08-01).
# The columns are evidence, not business input. The public `create()` and
# `write()` refuse ANY of the eleven fields UNCONDITIONALLY — no context
# value, no `sudo()`, and no RPC-supplied key can ever authorise them.
# `odoo/service/model.py::call_kw` copies the raw client `context` into the
# environment verbatim, so an authorisation expressed in `self.env.context`
# is client-forgeable by construction; the earlier `PROJECTION_SANCTION_KEY`
# context key was exactly that hole and has been removed. The ONLY path that
# may set these columns is the private, non-RPC helper
# `_shopify_connector_write_projection()` below: it is name-guarded from RPC
# (a leading underscore is refused by `call_kw::check_method_name`), it
# validates that it receives only projection fields, and it reaches the next
# MRO `write()` directly rather than re-entering the refusing public
# override. The boundary is therefore a Python reference held only by the
# binding-synchronisation code — unforgeable over the wire — not a value any
# caller can put in a dict. The SEC-3 quarantine propagation keeps writing
# in SQL, mirroring the sweep's own discipline.
#
# ROLLBACK POSTURE (handoff §12): reverting the module code orphans these
# columns and their backfilled values harmlessly; destructive removal is a
# separate forward cleanup migration, never an automatic side effect.

import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)

# The eleven stored projection columns (3 core + 8 lifecycle mirrors).
SALE_ORDER_PROJECTION_FIELDS = (
    # core
    'shopify_connector_store_id',
    'shopify_connector_cancelled_at',
    'shopify_connector_quarantined',
    # lifecycle mirrors
    'shopify_connector_financial_status',
    'shopify_connector_is_cod',
    'shopify_connector_approval_state',
    'shopify_connector_cod_commercial_state',
    'shopify_connector_cod_collection_state',
    'shopify_connector_fulfillment_status',
    'shopify_connector_review',
    'shopify_connector_evidence_refreshed_at',
)

# Binding fields whose change must resynchronise the projection.
_PROJECTION_SOURCE_FIELDS = frozenset((
    'store_id',
    'sale_order_id',
    'status',
    'shopify_financial_status_snapshot',
    'shopify_fulfillment_status_snapshot',
    'shopify_cancelled_at',
    'is_cod',
    'manual_gateway_approval_state',
    'cod_commercial_state',
    'cod_collection_state',
    'shopify_last_evidence_refresh_at',
    'sec3_scope_quarantined',
))


class ShopifyConnectorSaleOrderProjection(models.Model):
    _inherit = 'sale.order'

    # --- core projection (3) --------------------------------------------
    shopify_connector_store_id = fields.Many2one(
        'shopify.connector.store',
        string='Shopify Store',
        index=True,
        readonly=True,
        copy=False,
        ondelete='restrict',
        # sale.order sets `_check_company_auto = True` at the pin
        # (odoo/addons/sale/models/sale_order.py:39, odoo/odoo@30bde9ff), so
        # check_company here refuses an order that projects another
        # company's store at every ORM write.
        check_company=True,
        help='Connector projection: the Shopify store this order was '
             'imported from. Maintained by the connector; not editable.',
    )
    shopify_connector_cancelled_at = fields.Datetime(
        string='Shopify Cancelled At',
        readonly=True,
        copy=False,
        help='Connector projection of the Shopify order cancellation '
             'evidence (binding shopify_cancelled_at).',
    )
    shopify_connector_quarantined = fields.Boolean(
        string='Shopify Scope Quarantined',
        default=False,
        index=True,
        readonly=True,
        copy=False,
        help='Connector projection of the SEC-3 scope quarantine flag of '
             'the order binding. Quarantined orders are excluded from every '
             'Store 360 aggregate.',
    )

    # --- lifecycle mirrors (8) ------------------------------------------
    shopify_connector_financial_status = fields.Char(
        string='Shopify Financial Status',
        readonly=True,
        copy=False,
        help='Raw Shopify displayFinancialStatus snapshot mirrored from the '
             'order binding at import/refresh. Unknown values are preserved '
             'raw and bucketed as "needs review", never as healthy.',
    )
    shopify_connector_is_cod = fields.Boolean(
        string='Shopify COD',
        readonly=True,
        copy=False,
        help='Connector COD classification (unambiguous approved manual '
             'gateway), mirrored from the order binding.',
    )
    shopify_connector_approval_state = fields.Selection(
        selection=[
            ('not_required', 'Not Required'),
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('superseded', 'Superseded'),
        ],
        string='Shopify Manual-Gateway Approval',
        readonly=True,
        copy=False,
        help='Mirror of the binding manual_gateway_approval_state.',
    )
    shopify_connector_cod_commercial_state = fields.Selection(
        selection=[
            ('imported', 'Imported'),
            ('quotation', 'Quotation'),
            ('confirmed', 'Confirmed'),
            ('review', 'Review'),
            ('cancelled', 'Cancelled'),
        ],
        string='Shopify COD Commercial State',
        readonly=True,
        copy=False,
        help='Mirror of the binding cod_commercial_state.',
    )
    shopify_connector_cod_collection_state = fields.Selection(
        selection=[
            ('nothing_collected', 'Nothing Collected'),
            ('partially_collected', 'Partially Collected'),
            ('fully_collected', 'Fully Collected'),
            ('discrepancy', 'Discrepancy'),
        ],
        string='Shopify COD Collection State',
        readonly=True,
        copy=False,
        help='Mirror of the binding cod_collection_state.',
    )
    shopify_connector_fulfillment_status = fields.Char(
        string='Shopify Fulfillment Status',
        readonly=True,
        copy=False,
        help='Raw Shopify order-level displayFulfillmentStatus snapshot '
             'mirrored from the order binding. This is Shopify evidence '
             'observed at import/refresh time, never a live carrier feed.',
    )
    shopify_connector_review = fields.Boolean(
        string='Shopify Review',
        readonly=True,
        copy=False,
        help='True when the order binding lifecycle state is "review".',
    )
    shopify_connector_evidence_refreshed_at = fields.Datetime(
        string='Shopify Evidence Refreshed At',
        readonly=True,
        copy=False,
        help='Mirror of the binding shopify_last_evidence_refresh_at — when '
             'the Shopify payment/lifecycle evidence for this order was '
             'last re-read.',
    )

    # --- non-forgeable write surface ------------------------------------
    @api.model
    def _shopify_connector_projection_fields(self):
        return SALE_ORDER_PROJECTION_FIELDS

    def _shopify_connector_reject_projection_write(self, vals):
        """Refuse any attempt to set a projection field on the public path.

        Unconditional: no `env.context` value and no `sudo()` lifts it,
        because the only legitimate writer is the private helper below,
        which never comes through here.
        """
        touched = sorted(set(vals) & set(SALE_ORDER_PROJECTION_FIELDS))
        if touched:
            raise AccessError(
                "Shopify connector projection fields on sale.order are "
                "evidence maintained by the connector's sanctioned "
                "import/refresh/approval/quarantine writers and cannot be "
                "written directly. Fields: %s" % ', '.join(touched)
            )

    def _shopify_connector_write_projection(self, vals):
        """The one sanctioned projection writer — private and non-RPC.

        Not reachable over RPC: `call_kw` refuses methods whose name starts
        with an underscore, so no request can name it. It authorises nothing
        by itself beyond what its own caller (the binding-synchronisation
        choke point) holds a Python reference to invoke it.

        Contract:
          * accepts ONLY the eleven projection fields — an arbitrary or
            non-projection key is a programming error and is refused, so the
            helper can never become a general back-door write;
          * reaches the next MRO `write()` implementation directly
            (`super().write()`), so it neither re-enters the refusing public
            `write()` above nor recurses;
          * depends on NO caller-controlled context value;
          * preserves normal ORM constraints, recompute, cache and
            transaction rollback, because `super().write()` runs the full
            write machinery from this point in the MRO onward.
        """
        stray = sorted(set(vals) - set(SALE_ORDER_PROJECTION_FIELDS))
        if stray:
            raise ValueError(
                "The sanctioned projection writer accepts only projection "
                "fields; refused: %s" % ', '.join(stray)
            )
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._shopify_connector_reject_projection_write(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._shopify_connector_reject_projection_write(vals)
        return super().write(vals)

    @api.constrains('shopify_connector_store_id')
    def _check_projection_store_matches_binding(self):
        """The projected store must agree with the order's own binding.

        This is the `sale.order`-side counterpart to the binding-side
        `_check_projection_store_agreement` (which fires only on binding
        writes and is left unchanged). It fires whenever the projected store
        is written, so drift introduced by any path that does NOT write a
        binding — the only surviving way to reach these columns is the
        private helper above — cannot persist:

          * an order WITH a binding must project exactly that binding's
            store;
          * an order WITHOUT a binding must carry no projected store.

        Same-company drift is refused, not only cross-company: `check_company`
        on the field already refuses a different-company store, and this
        constraint additionally refuses a same-company store that is not the
        binding's own. Copy/duplicate stays clean because every projection
        field is `copy=False`, so a copied order carries no projected store
        and satisfies the no-binding branch.
        """
        Binding = self.env['shopify.connector.order.binding'].sudo()
        for order in self:
            binding = Binding.search(
                [('sale_order_id', '=', order.id)], limit=1,
            )
            projected = order.shopify_connector_store_id
            if binding:
                if projected != binding.store_id:
                    raise ValidationError(
                        'The sale order projection store (%s) must equal its '
                        'Shopify order binding store (%s).' % (
                            projected.id or 'unset', binding.store_id.id,
                        )
                    )
            elif projected:
                raise ValidationError(
                    'A sale order with no Shopify order binding cannot carry '
                    'a Shopify store projection (store %s).' % projected.id
                )


class ShopifyConnectorOrderBindingProjectionSync(models.Model):
    """Binding-level choke point: every sanctioned binding writer syncs.

    The importer's create (`_apply_import`, order_importer.py:532), the
    refresh writer (`_refresh_existing`, order_importer.py:2403) and the
    approval action (`action_approve_manual_gateway_order`,
    order_binding.py:241) all end in this model's `create()`/`write()`, so
    hooking the projection here covers every existing production writer —
    and every future one — by construction, in the same transaction as the
    authoritative binding change. The SEC-3 quarantine sweep bypasses the
    ORM by design; it is covered by the `_sec3_after_quarantine_flag_update`
    hook below.
    """

    _inherit = 'shopify.connector.order.binding'

    @api.model_create_multi
    def create(self, vals_list):
        bindings = super().create(vals_list)
        bindings._shopify_connector_sync_sale_order_projection()
        return bindings

    def write(self, vals):
        result = super().write(vals)
        if set(vals) & _PROJECTION_SOURCE_FIELDS:
            self._shopify_connector_sync_sale_order_projection()
        return result

    def _shopify_connector_sync_sale_order_projection(self):
        """Project this binding's evidence onto its sale order.

        Runs under `sudo()` because the projection write must not depend on
        the acting user's `sale.order` write rights (the approval action,
        for instance, is taken by a Reviewer who may hold none) — the values
        are connector evidence, not user input. Authorisation comes from the
        private `_shopify_connector_write_projection()` helper, never from a
        context value, so it cannot be forged from an RPC caller's context.

        Idempotent: only fields whose value actually differs are written, so
        a duplicate/replayed refresh leaves no extra writes behind and a
        re-run converges to the same state.
        """
        for binding in self.sudo():
            order = binding.sale_order_id
            if not order:
                continue
            target = {
                'shopify_connector_store_id': binding.store_id.id,
                'shopify_connector_cancelled_at':
                    binding.shopify_cancelled_at or False,
                'shopify_connector_quarantined':
                    bool(binding.sec3_scope_quarantined),
                'shopify_connector_financial_status':
                    binding.shopify_financial_status_snapshot or False,
                'shopify_connector_is_cod': bool(binding.is_cod),
                'shopify_connector_approval_state':
                    binding.manual_gateway_approval_state or False,
                'shopify_connector_cod_commercial_state':
                    binding.cod_commercial_state or False,
                'shopify_connector_cod_collection_state':
                    binding.cod_collection_state or False,
                'shopify_connector_fulfillment_status':
                    binding.shopify_fulfillment_status_snapshot or False,
                'shopify_connector_review': binding.status == 'review',
                'shopify_connector_evidence_refreshed_at':
                    binding.shopify_last_evidence_refresh_at or False,
            }
            changed = {}
            for field_name, value in target.items():
                current = order[field_name]
                if field_name == 'shopify_connector_store_id':
                    current = current.id if current else False
                if current != value:
                    changed[field_name] = value
            if changed:
                # sudo() supplies the sale.order-write elevation the acting
                # user may lack (e.g. a Reviewer approving an order); the
                # private helper — never the refusing public write() —
                # supplies the projection authorisation. No context key is
                # involved, so nothing here is client-forgeable.
                order.sudo()._shopify_connector_write_projection(changed)

    @api.constrains('store_id', 'sale_order_id')
    def _check_projection_store_agreement(self):
        """The order's projected store must equal its binding's store.

        The sync above establishes the equality; this constraint keeps any
        unsanctioned drift (or a missed writer) from surviving a binding
        write. Company equality is separately enforced by `check_company`
        on both `sale_order_id` (binding side) and
        `shopify_connector_store_id` (order side).
        """
        for binding in self.sudo():
            order = binding.sale_order_id
            if not order:
                continue
            projected = order.shopify_connector_store_id
            if projected and projected != binding.store_id:
                raise ValidationError(
                    'The sale order projection store (%s) disagrees with '
                    'its binding store (%s).' % (
                        projected.id, binding.store_id.id,
                    )
                )

    @api.model
    def _sec3_after_quarantine_flag_update(self, ids, quarantined):
        """Propagate the SQL quarantine sweep/release into the mirror.

        The SEC-3 sweep and release write `sec3_scope_quarantined` in SQL by
        design (scope mixin rationale, scope_mixin.py:212-227); this hook
        extends the same statement discipline to the sale-order mirror in
        the SAME transaction, exactly as the fulfillment module already
        propagates quarantine to child lines in SQL
        (`_sec3_sync_line_quarantine`, fulfillment_inbound_evidence.py).
        The dashboard's no-raw-SQL guard is scoped to the runtime aggregate
        service, not to install/upgrade maintenance paths.
        """
        super()._sec3_after_quarantine_flag_update(ids, quarantined)
        if not ids:
            return
        self.env.cr.execute(
            'UPDATE sale_order o SET shopify_connector_quarantined = %s '
            'FROM shopify_connector_order_binding b '
            'WHERE b.sale_order_id = o.id AND b.id IN %s '
            'AND o.shopify_connector_quarantined IS DISTINCT FROM %s',
            (quarantined, tuple(ids), quarantined),
        )
        self.env['sale.order'].invalidate_model(
            ['shopify_connector_quarantined']
        )
