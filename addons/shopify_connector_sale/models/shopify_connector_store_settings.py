import json
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ShopifyConnectorStoreSettingsCustomerExtension(models.Model):
    """Adds the fallback-partner configuration field (D5, Posture A).

    HISTORY, CORRECTED (Batch 2 checkpoint 1). Task 011 introduced this
    field as supporting substrate only, and this docstring said so: "zero
    order-resolution behaviour", never read by the customer importer. That
    stopped being true when Task 012 landed order import.
    `ShopifyConnectorOrderImporter._resolve_customer` now reads it directly
    -- an order carrying no usable customer email resolves to this partner
    with resolution `fallback`, and raises `odoo_validation_configuration`
    when it is unset. The description is corrected here rather than left
    standing, because the canonical Store Settings form decides whether to
    present a field as a real setting or as inert on exactly this question,
    and a stale comment is how it would have been presented wrongly.

    Still true: no default, no auto-creation of any partner record, no
    constraint requiring it, no compute/onchange, ordinary write path --
    contributed via the core settings extension seam, no
    shopify_connector_core file edit.
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
    # SEC-3 (#197) / control-room MVP ownership decision, 2026-07-25: this is
    # NO LONGER an independent ownership selector. The connector store owns the
    # company; this field must agree with it (`_check_order_company_matches_store`
    # below) and defaults from it. It is kept as a real field rather than made a
    # related one because the existing `write()` guard -- order company may not
    # change once an order binding or tax mapping exists -- is genuine
    # protection worth keeping, and because a related field's inverse would
    # write through and silently re-home the STORE, which is exactly what the
    # MVP decision forbids.
    order_company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self._default_order_company(),
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
    sale_order_scan_window_start_at = fields.Datetime(readonly=True)
    sale_order_scan_window_end_at = fields.Datetime(readonly=True)
    sale_order_scan_cursor = fields.Char(readonly=True)
    sale_order_scan_latest_at = fields.Datetime(readonly=True)
    sale_order_scan_page_count = fields.Integer(default=0, readonly=True)
    sale_order_scan_generation = fields.Integer(default=0, readonly=True)
    # --- Store 360 / R-4: generation-bound order catch-up stamps ---------
    # A successful connection probe alone must never mark Shopify-derived
    # order data current (spec §9.3/§9.5, R-4). These stamps record the one
    # thing that may: a COMPLETE order traversal for the CURRENT
    # `connection_generation` whose descendant import work all reached a
    # terminal, non-blocking state. `run_scan` records the pending lineage
    # (in the same savepoint as its enumeration and checkpoint advance);
    # the job-terminal promotion hook in
    # `shopify_connector_order_reconnect.py` promotes it. All five fields
    # are connector system state: readonly, written only by those two
    # sanctioned paths, never caller input.
    sale_order_catchup_pending_generation = fields.Integer(
        default=0, readonly=True,
        help='Connection generation of the most recent completed order '
             'scan traversal whose descendant imports are being tracked.',
    )
    sale_order_catchup_pending_upper_bound_at = fields.Datetime(
        readonly=True,
        help='Upper bound (scan start wall clock) of the traversal window '
             'the pending lineage enumerated through.',
    )
    sale_order_catchup_pending_scan_job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        readonly=True,
        ondelete='set null',
        help='The order scan job that recorded the pending lineage.',
    )
    sale_order_catchup_generation = fields.Integer(
        default=0, readonly=True,
        help='Connection generation for which the last COMPLETE order '
             'catch-up (traversal + all descendant imports terminal and '
             'non-blocking) is proven. Order data is only "current" when '
             'this equals the store\'s connection_generation.',
    )
    sale_order_catchup_synced_through_at = fields.Datetime(
        readonly=True,
        help='Shopify order data is synchronized through this instant: the '
             'upper bound of the last complete, current-generation catch-up '
             'traversal. Advanced only at complete catch-up; a page refresh '
             'or connection probe never moves it.',
    )

    def init(self):
        """Supply the sale module's share of the SEC-3 ownership backfill.

        `shopify.connector.store._backfill_company` can only prove ownership
        when the database has exactly one company. This module knows one more
        *provable* fact: a store whose settings already name an
        `order_company_id` was already operating in that company, so adopting
        it is a record of what was, not a guess. Stores with no such evidence
        are left NULL and stay fail-closed.
        """
        super().init()
        self.env.cr.execute("""
            UPDATE shopify_connector_store AS store
               SET company_id = settings.order_company_id
              FROM shopify_connector_store_settings AS settings
             WHERE settings.store_id = store.id
               AND store.company_id IS NULL
               AND settings.order_company_id IS NOT NULL
        """)
        if self.env.cr.rowcount:
            _logger.info(
                'SEC-3: adopted the configured order company as the owning '
                'company for %d historic Shopify store(s).',
                self.env.cr.rowcount,
            )

    @api.model_create_multi
    def create(self, vals_list):
        """Derive the order company from the store on every create path.

        `default_get` only sees the context, so it can serve the UI (where
        `default_store_id` is present) but not a plain ORM
        `create({'store_id': ...})`. Filling it here means the field is correct
        by construction in both, instead of defaulting to whichever company the
        acting user happened to have active and then failing the agreement
        constraint below. An explicitly supplied value is left alone -- and then
        validated, so an explicit wrong answer is still refused.
        """
        for vals in vals_list:
            if not vals.get('order_company_id') and vals.get('store_id'):
                store = self.env['shopify.connector.store'].browse(
                    vals['store_id'])
                if store.company_id:
                    vals['order_company_id'] = store.company_id.id
        return super().create(vals_list)

    @api.model
    def _default_order_company(self):
        """Default the order company from the store being configured.

        `default_get` runs with the create context, so a settings row created
        for a store (UI or ORM) picks up that store's company rather than
        whichever company the acting user happens to have active. Falls back to
        `env.company` only when there is no store in context yet.
        """
        store_id = self.env.context.get('default_store_id')
        if store_id:
            store = self.env['shopify.connector.store'].browse(store_id)
            if store.exists() and store.company_id:
                return store.company_id
        return self.env.company

    @api.constrains('order_company_id', 'store_id')
    def _check_order_company_matches_store(self):
        """The order company must be the store's company (SEC-3 / #197.11).

        Before this, `order_company_id` was a second, independent ownership
        selector: a store could be read by company A while its orders were
        created in company B. The MVP ownership decision is that a store
        belongs to exactly one company, so the two must agree.

        A store with no company yet (historic, awaiting the administrative
        backfill) is skipped here -- it is already fail-closed at read time,
        and blocking its settings write would remove the only path to fixing
        it.
        """
        for settings in self:
            store_company = settings.store_id.company_id
            if not store_company:
                continue
            if settings.order_company_id != store_company:
                raise ValidationError(
                    'The order company must be the company that owns the '
                    'Shopify store (%s). A store belongs to exactly one '
                    'company.' % (store_company.display_name,)
                )

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
        readiness_changed = self.filtered(lambda settings: (
            (
                'order_company_id' in vals
                and settings.order_company_id.id
                != (vals.get('order_company_id') or False)
            )
            or (
                'order_payment_term_id' in vals
                and settings.order_payment_term_id.id
                != (vals.get('order_payment_term_id') or False)
            )
        ))
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
        result = super().write(vals)
        if readiness_changed:
            readiness_changed._mark_setup_readiness_stale()
        return result

    @api.model
    def _sec3_parent_scope_relations(self):
        return super()._sec3_parent_scope_relations() + (
            ('sale_order_catchup_pending_scan_job_id', 'store'),
        )

    @api.constrains('sale_order_catchup_pending_scan_job_id', 'store_id')
    def _check_catchup_scan_job_store(self):
        """SEC-3 same-store agreement for the declared job pointer."""
        for settings in self:
            job = settings.sale_order_catchup_pending_scan_job_id
            if job and job.store_id != settings.store_id:
                raise ValidationError(
                    'The pending order catch-up scan job must belong to '
                    'the settings row\'s own store.'
                )

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
