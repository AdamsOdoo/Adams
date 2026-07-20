import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
    REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    INCONCLUSIVE_RECONCILIATION_CAP,
)
from odoo.addons.shopify_connector_core.tools.redaction import redact

_logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Frozen job-contract vocabulary (DEC-037 §7). Do not invent additional
# values. `error_class`/`manual_review_subreason` values used below are
# all already registered on `shopify.connector.job`'s core
# ERROR_CLASS_SELECTION / MANUAL_REVIEW_SUBREASON_SELECTION -- this
# module adds none.
# ----------------------------------------------------------------------
JOB_TYPE_PUSH_SYNC = 'inventory_push_sync'
JOB_TYPE_PUSH_SCAN = 'inventory_push_scan'
JOB_TYPE_FIRST_PUSH_PREVIEW = 'inventory_first_push_preview'
JOB_TYPE_LOCATION_SYNC = 'inventory_location_sync'
JOB_TYPE_ACTIVATE = 'inventory_activate'
JOB_TYPE_SET_QUANTITIES = 'inventory_set_quantities'
# One new job_type this domain must add beyond the six named in DEC-037
# §7: a shared reconciliation-dispatch job_type for both mutation
# domains, accepted in principle by the control room (PR #182 comment
# 5025765389 disposition 2) and folded into DEC-037/the packet/the
# locked prompt by this same correction batch. DEC-036/DEC-037's own
# generic reconciliation mechanism requires every mutation domain's
# `reconciliation_job_type` to resolve to a real, dispatchable
# `job_type` value (`shopify.connector.job`'s own
# `_check_reconciliation_attempt_link` constraint requires it, and the
# two existing core values -- `mutation_dispatch_selftest_reconcile` and
# `mutation_dispatch_selftest` -- are explicitly reserved, "never a
# template for a future domain job_type"). One shared value here (not
# one per mutation domain) keeps this to a single, minimal addition:
# the shared handler dispatches purely on
# `job.mutation_attempt_id.mutation_domain`, exactly mirroring core's
# own generic reconciliation-handler shape. Read-only, never a mutation
# domain, never holds the inventory-pair operation scope, and links to
# exactly one existing mutation attempt (core's own unique index on
# `mutation_attempt_id`).
JOB_TYPE_MUTATION_RECONCILE = 'inventory_mutation_reconcile'

MUTATION_DOMAIN_ACTIVATE = JOB_TYPE_ACTIVATE
MUTATION_DOMAIN_SET_QUANTITIES = JOB_TYPE_SET_QUANTITIES

MAX_CAS_RETRY_ORDINAL = 3

# The fail-closed integral-quantity tolerance (control-room binding
# rule, PR #182 comment 5025765389 §16): harmless floating-point noise
# around a whole number is accepted; anything else is a meaningful
# fraction and must block before transport, never rounded/truncated.
QUANTITY_INTEGRALITY_TOLERANCE = 1e-4

ERROR_CLASS_VALIDATION = 'shopify_user_errors_validation'
ERROR_CLASS_LOCATION_MISSING = 'inventory_location_missing'
ERROR_CLASS_CONCURRENCY = 'concurrency_race_conflict'
ERROR_CLASS_THROTTLE = 'shopify_throttling_rate_limit'
ERROR_CLASS_TEMPORARY = 'shopify_temporary_server_network'
ERROR_CLASS_DATA_SHAPE = 'data_shape_schema_mismatch'
ERROR_CLASS_IDEMPOTENCY = 'idempotency_contract_violation'
ERROR_CLASS_NO_STRATEGY = 'no_reconciliation_strategy'
ERROR_CLASS_STORE_IDENTITY = 'store_identity_mismatch'

SUBREASON_LOCATION_MISSING = 'inventory_location_missing'
SUBREASON_BINDING_CONFLICT = 'binding_conflict'
SUBREASON_IDEMPOTENCY = 'idempotency_contract_violation'
SUBREASON_STORE_IDENTITY = 'store_identity_mismatch'
SUBREASON_DUPLICATE_RISK = 'duplicate_risk'
SUBREASON_DESTRUCTIVE_WRITE = 'destructive_write_guard_blocked'
SUBREASON_NO_STRATEGY = 'no_reconciliation_strategy'

INVENTORY_JOB_TYPES = (
    JOB_TYPE_PUSH_SYNC, JOB_TYPE_PUSH_SCAN, JOB_TYPE_FIRST_PUSH_PREVIEW,
    JOB_TYPE_LOCATION_SYNC, JOB_TYPE_ACTIVATE, JOB_TYPE_SET_QUANTITIES,
)

# The three "pair execution" job types (DEC-037 §5.3): the only types
# for which `operation_scope_key` must equal the exact frozen literal
# below, verbatim -- never the shared reconciliation type, never the
# preview/scan/location-sync types (PR #182 comment 5025765389 item 11).
PAIR_EXECUTION_JOB_TYPES = (
    JOB_TYPE_PUSH_SYNC, JOB_TYPE_ACTIVATE, JOB_TYPE_SET_QUANTITIES,
)

# The exact DB-level constraint message declared on
# `shopify.connector.job._store_operation_scope_key_uniq` -- the only
# reliable signal available at the Python except-clause layer to
# identify this specific collision (Odoo's ORM constraint-violation
# handling does not propagate the psycopg2 SQLSTATE/constraint name to
# the raised ValidationError). Re-verified independently below by
# re-querying for an actual non-terminal job on the same pair before
# ever treating a caught ValidationError as benign coalescing.
OPERATION_SCOPE_CONSTRAINT_MESSAGE = (
    'A non-terminal job already holds this operation scope for this store.'
)


def pair_scope_key(store_id, inventory_item_gid, location_gid):
    """The frozen pair-serialization literal (DEC-037 §5.3)."""
    return 'inventory_pair:%s:%s:%s' % (
        store_id, inventory_item_gid or '', location_gid or '',
    )


FIXED_ERROR_CLASS_VOCABULARY = frozenset((
    'shopify_user_errors_validation',
    'inventory_location_missing',
    'concurrency_race_conflict',
    'shopify_throttling_rate_limit',
    'shopify_temporary_server_network',
    'data_shape_schema_mismatch',
    'idempotency_contract_violation',
    'no_reconciliation_strategy',
    'store_identity_mismatch',
))


def _normalize_transport_error_class(exc):
    """Map any transport-level exception's `error_class` onto this
    module's own fixed nine-value vocabulary (DEC-037 §7/§9).

    `shopify.connector.api.client.ShopifyClientError` carries the full
    core-wide 16-value `error_class` registry (e.g.
    `shopify_permission_scope_auth`, which core's own generic
    consequence validator would accept but this domain's own governing
    contract never authorizes). Any value not already in this domain's
    fixed set is conservatively mapped to
    `shopify_temporary_server_network` (uncertain, reconcile-first) --
    never silently passed through, and never defaulted to an automatic
    retry.
    """
    error_class = getattr(exc, 'error_class', None)
    if error_class in FIXED_ERROR_CLASS_VOCABULARY:
        return error_class
    return ERROR_CLASS_TEMPORARY


def _integral_quantity_or_none(value):
    """Return `(int_value, True)` when `value` is integral within the
    accepted floating-point-noise tolerance, else `(None, False)`.

    Never rounds or truncates a meaningful fraction (control-room
    binding rule, PR #182 comment 5025765389 §16): 10.0 -> (10, True);
    0.0 -> (0, True); 9.999999997 (harmless noise) -> (10, True); 10.5
    (a meaningful fraction) -> (None, False).
    """
    rounded = round(value)
    if abs(value - rounded) <= QUANTITY_INTEGRALITY_TOLERANCE:
        return int(rounded), True
    return None, False


def _parse_shopify_datetime(value):
    """Parse a Shopify ISO-8601 timestamp into a timezone-aware UTC
    `datetime`, or `None` if absent/unparsable. Never compared as a raw
    string against Odoo's differently-formatted `Datetime` strings."""
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _odoo_datetime_to_utc(value):
    """Normalize an Odoo naive (UTC-convention) `Datetime` value into a
    timezone-aware UTC `datetime` for safe comparison against a parsed
    Shopify timestamp."""
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# ======================================================================
# Seam 1: shopify.connector.job -- job_type selection_add, the one new
# domain-owned job-lineage field (cas_retry_ordinal, now protected and
# range/domain-validated), and the exact pair-execution
# operation_scope_key override.
# ======================================================================
class ShopifyConnectorJobInventoryExtension(models.Model):
    _inherit = 'shopify.connector.job'

    job_type = fields.Selection(
        selection_add=[
            (JOB_TYPE_PUSH_SYNC, 'Inventory Push Sync'),
            (JOB_TYPE_PUSH_SCAN, 'Inventory Push Scan'),
            (JOB_TYPE_FIRST_PUSH_PREVIEW, 'Inventory First Push Preview'),
            (JOB_TYPE_LOCATION_SYNC, 'Inventory Location Sync'),
            (JOB_TYPE_ACTIVATE, 'Inventory Activate'),
            (JOB_TYPE_SET_QUANTITIES, 'Inventory Set Quantities'),
            (JOB_TYPE_MUTATION_RECONCILE, 'Inventory Mutation Reconciliation'),
        ],
        ondelete={
            JOB_TYPE_PUSH_SYNC: lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_PUSH_SCAN: lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_FIRST_PUSH_PREVIEW:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_LOCATION_SYNC:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_ACTIVATE: lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_SET_QUANTITIES:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_MUTATION_RECONCILE:
                lambda recs: recs._reassign_to_historic_job_type(),
        },
    )
    # The only new, domain-owned job-lineage field (DEC-037 §5.1/§5.4/§7).
    # Meaningful only for `inventory_set_quantities` jobs: 0 = original,
    # 1/2/3 = the first/second/third bounded CAS replacement. Checked
    # once at job creation against the predecessor's ordinal + 1; never
    # incremented mid-job. Protected below exactly like core's own
    # PROTECTED_JOB_FIELDS (create()/write() denial for non-sudo
    # callers) -- it directly controls retry-exhaustion and
    # review-release eligibility and must not be genuinely writable.
    cas_retry_ordinal = fields.Integer(default=0, readonly=True)

    @api.model
    def _domain_flag_for_job_type(self, job_type):
        if job_type in INVENTORY_JOB_TYPES + (JOB_TYPE_MUTATION_RECONCILE,):
            return 'inventory_domain_enabled'
        return super()._domain_flag_for_job_type(job_type)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            supplied = [
                vals for vals in vals_list if 'cas_retry_ordinal' in vals
            ]
            if supplied:
                raise AccessError(
                    "cas_retry_ordinal cannot be supplied through generic "
                    "create(). Use the sanctioned inventory service."
                )
        return super().create(vals_list)

    def write(self, vals):
        if 'cas_retry_ordinal' in vals and not self.env.su:
            raise AccessError(
                "cas_retry_ordinal can only be changed through a "
                "sanctioned connector service."
            )
        return super().write(vals)

    @api.constrains('cas_retry_ordinal', 'job_type')
    def _check_cas_retry_ordinal(self):
        for job in self:
            if job.job_type != JOB_TYPE_SET_QUANTITIES and job.cas_retry_ordinal:
                raise ValidationError(
                    "cas_retry_ordinal must be 0 for any job_type other "
                    "than inventory_set_quantities."
                )
            if not (0 <= job.cas_retry_ordinal <= MAX_CAS_RETRY_ORDINAL):
                raise ValidationError(
                    "cas_retry_ordinal must be between 0 and %d." % (
                        MAX_CAS_RETRY_ORDINAL,
                    )
                )

    @api.depends(
        'state', 'store_id', 'res_model', 'res_id', 'shopify_target_gid',
        'superseded_by_job_id', 'job_type',
    )
    def _compute_operation_scope_key(self):
        """Override: for the three pair-execution job types only, the
        stored `operation_scope_key` is the exact frozen literal
        (`shopify_target_gid`, already `pair_scope_key(...)` verbatim at
        creation time) -- never core's default
        `store|res_model|res_id|shopify_target_gid` composite (PR #182
        comment 5025765389 item 11). Every other job_type, including the
        shared reconciliation type, keeps core's own default behaviour
        unchanged. Retained while non-terminal (including
        `blocked_manual_review`), cleared on any terminal state or once
        superseded -- identical lifecycle rule to core's own
        implementation, just a different literal for these three types.
        """
        super()._compute_operation_scope_key()
        for job in self:
            if job.job_type not in PAIR_EXECUTION_JOB_TYPES:
                continue
            if (
                job.state in TERMINAL_JOB_STATES
                or job.superseded_by_job_id
                or not job.shopify_target_gid
            ):
                job.operation_scope_key = False
            else:
                job.operation_scope_key = job.shopify_target_gid


# ======================================================================
# Seam 2: shopify.connector.readiness.check -- replace the placeholder
# `_check_mapped_location` evaluation (D-013-5).
# ======================================================================
class ShopifyConnectorReadinessCheckInventoryExtension(models.AbstractModel):
    _inherit = 'shopify.connector.readiness.check'

    @api.model
    def _check_mapped_location(self, store):
        """Real mapped-location + write_inventory-scope readiness (D-013-5).

        Pure read-only evaluation (no `write`/`create`/`unlink`/`sudo`)
        -- the repo-wide AST guard on every `_check_*` method requires
        this. When the inventory domain is disabled, stays not-applicable
        pass (unchanged core behavior via the CORE-R1 baseline). When
        enabled: requires at least one active location mapping, and
        requires `write_inventory` to be present in the store's granted
        scopes snapshot.
        """
        code = 'mapped_location'
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings or not settings.inventory_domain_enabled:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_PASS,
                'Not applicable — the inventory domain is not enabled for '
                'this store.',
            )
        mapping_count = self.env[
            'shopify.connector.location.mapping'
        ].search_count([('store_id', '=', store.id)])
        if not mapping_count:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'The inventory domain is enabled but no Shopify location '
                'is mapped to an Odoo internal location yet.',
            )
        try:
            scopes = json.loads(store.granted_scopes or '[]')
        except (TypeError, ValueError):
            scopes = []
        if not isinstance(scopes, list) or 'write_inventory' not in scopes:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'The write_inventory scope is not present in the granted '
                'scopes snapshot.',
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_PASS,
            'At least one location is mapped and write_inventory is '
            'granted.',
        )


# ======================================================================
# Seam 3: stock.move -- the odoo_event trigger surface (D-013-6a).
# ======================================================================
class ShopifyConnectorStockMoveInventoryExtension(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        result = super()._action_done(cancel_backorder=cancel_backorder)
        try:
            self.env[
                'shopify.connector.inventory.service'
            ]._enqueue_from_stock_moves(self)
        except Exception:
            # A trigger-surface failure must never mask the already-
            # completed, authoritative stock-move validation itself.
            _logger.exception(
                'Failed to enqueue inventory push jobs after a stock '
                'move validation; the stock move itself is unaffected.'
            )
        return result


# ======================================================================
# Seam 4: shopify.connector.store -- the manual-trigger surface
# (D-013-6c).
# ======================================================================
class ShopifyConnectorStoreInventoryExtension(models.Model):
    _inherit = 'shopify.connector.store'

    def action_push_inventory_now(self):
        self.ensure_one()
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_operator'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                "Only a Shopify Connector Operator or Administrator may "
                "trigger a manual inventory push."
            )
        return self.env[
            'shopify.connector.inventory.service'
        ]._enqueue_manual_push(self)


# ======================================================================
# Seam 5: shopify.connector.job.dispatch -- handler / replay-policy /
# reconciliation-strategy registration.
# ======================================================================
class ShopifyConnectorJobDispatchInventoryExtension(models.AbstractModel):
    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_handlers(self):
        handlers = dict(super()._get_handlers())
        Service = self.env['shopify.connector.inventory.service']
        handlers.update({
            JOB_TYPE_PUSH_SYNC: Service._handle_inventory_push_sync,
            JOB_TYPE_PUSH_SCAN: Service._handle_inventory_push_scan,
            JOB_TYPE_FIRST_PUSH_PREVIEW:
                Service._handle_inventory_first_push_preview,
            JOB_TYPE_LOCATION_SYNC: Service._handle_inventory_location_sync,
            JOB_TYPE_MUTATION_RECONCILE:
                Service._handle_inventory_mutation_reconcile,
        })
        return handlers

    @api.model
    def _get_replay_policies(self):
        policies = dict(super()._get_replay_policies())
        policies.update({
            JOB_TYPE_PUSH_SYNC: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_PUSH_SCAN: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_FIRST_PUSH_PREVIEW: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_LOCATION_SYNC: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_ACTIVATE: REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            JOB_TYPE_SET_QUANTITIES: REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            JOB_TYPE_MUTATION_RECONCILE: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
        })
        return policies

    @api.model
    def _get_reconciliation_strategies(self):
        strategies = dict(super()._get_reconciliation_strategies())
        Service = self.env['shopify.connector.inventory.service']
        strategies[MUTATION_DOMAIN_SET_QUANTITIES] = {
            'reconciliation_job_type': JOB_TYPE_MUTATION_RECONCILE,
            'prepare_local': Service._prepare_local_set_quantities,
            'prepare_preconditions': Service._prepare_preconditions_set_quantities,
            'transport': Service._transport_set_quantities,
            'classify_direct_result': Service._classify_direct_set_quantities,
            'reconcile': Service._reconcile_set_quantities,
            'apply_consequence': Service._apply_consequence_set_quantities,
        }
        strategies[MUTATION_DOMAIN_ACTIVATE] = {
            'reconciliation_job_type': JOB_TYPE_MUTATION_RECONCILE,
            'prepare_local': Service._prepare_local_activate,
            'prepare_preconditions': Service._prepare_preconditions_activate,
            'transport': Service._transport_activate,
            'classify_direct_result': Service._classify_direct_activate,
            'reconcile': Service._reconcile_activate,
            'apply_consequence': Service._apply_consequence_activate,
        }
        return strategies


# ======================================================================
# The inventory service itself.
# ======================================================================
class ShopifyConnectorInventoryService(models.AbstractModel):
    """Task 013 orchestration/mutation service (stateless, no table).

    Owns: the `inventory_push_sync` orchestration handler and its
    trigger surfaces (stock-move hook, scheduled scan, manual action);
    the two mutation-domain Layer 2 strategy implementations
    (`inventory_activate`, `inventory_set_quantities`); the shared
    reconciliation-job handler; the Shopify location-cache sync (the one
    named `sudo()` elevation); the sanctioned backend creation/admission
    service methods for location mappings, inventory-level bindings, and
    the first-push-preview/location-sync job types; and the private
    review-release helper delegated to by `shopify.connector.inventory.
    level.binding.action_recheck_inventory_pair` (this service never
    exposes that public method itself).
    """

    _name = 'shopify.connector.inventory.service'
    _description = 'Shopify Connector Inventory Service'

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @api.model
    def _create_inventory_job(
        self, store, job_source, job_type, binding,
        trigger_origin=False, cas_retry_ordinal=0,
    ):
        """Create one inventory job under the pair-serialization identity,
        routed through the core's sole sanctioned domain enqueue service
        (`shopify.connector.job.enqueue`, PR #182 comment 5025765389 item
        9) -- never a direct `shopify.connector.job.sudo().create()`.

        Every repeat-run inventory job type uses a fresh UUID4
        `payload_hash` nonce, so a legitimate later re-creation for the
        same pair never collides on the globally-unique
        `(store_id, idempotency_key)` constraint (the never-cleared
        `idempotency_key`, unlike `operation_scope_key`, persists past a
        job's terminal state).

        `cas_retry_ordinal` is this domain's own protected field (not
        part of the core enqueue service's signature): when non-zero
        (an atomic CAS-replacement handoff), it is applied through one
        narrow, same-transaction `sudo()` write immediately after
        enqueueing -- no second transaction, no parallel enqueue
        mechanism (item 13).
        """
        pair_key = pair_scope_key(
            store.id,
            binding.shopify_inventory_item_gid,
            binding.location_mapping_id.shopify_gid,
        )
        job = self.env['shopify.connector.job.enqueue'].enqueue(
            store, job_source, job_type,
            payload_hash=uuid.uuid4().hex,
            res_model='shopify.connector.inventory.level.binding',
            res_id=binding.id,
            shopify_target_gid=pair_key,
            trigger_origin=trigger_origin or False,
        )
        if cas_retry_ordinal:
            job.sudo().write({'cas_retry_ordinal': cas_retry_ordinal})
        return job

    @api.model
    def _try_enqueue_push_sync(self, store, binding, job_source, trigger_origin=False):
        """Admit one `inventory_push_sync` job for `binding`, or coalesce.

        If a non-terminal inventory job already holds this pair's
        `operation_scope_key`, the DB-level unique constraint refuses the
        insert (core's existing `_store_operation_scope_key_uniq`); this
        is the expected, non-error "already in progress" outcome -- the
        caller's Odoo-side change is already reflected on
        `pending_target_available` by the caller, so nothing is lost.

        Only that exact collision is ever swallowed (PR #182 comment
        5025765389 item 10): the caught `ValidationError` is matched
        against the constraint's own exact declared message, and then
        independently re-verified by re-querying for an actual
        non-terminal job on this precise pair before being treated as
        benign. Every other `ValidationError` (store-state,
        domain-disabled, company, invalid fields, illegal transitions,
        security, unrelated constraints, malformed identity) propagates
        unchanged.
        """
        pair_key = pair_scope_key(
            store.id,
            binding.shopify_inventory_item_gid,
            binding.location_mapping_id.shopify_gid,
        )
        try:
            with self.env.cr.savepoint():
                return self._create_inventory_job(
                    store, job_source, JOB_TYPE_PUSH_SYNC, binding,
                    trigger_origin=trigger_origin,
                )
        except ValidationError as exc:
            if OPERATION_SCOPE_CONSTRAINT_MESSAGE not in str(exc):
                raise
            existing = self.env['shopify.connector.job'].sudo().search([
                ('store_id', '=', store.id),
                ('job_type', 'in', INVENTORY_JOB_TYPES),
                ('operation_scope_key', '=', pair_key),
            ], limit=1)
            if not existing:
                raise
            return self.env['shopify.connector.job']

    @api.model
    def _refresh_pending_target(self, binding):
        """Recompute and coalesce the pending Odoo target onto the binding.

        Last-value-wins (DEC-037 §10): always overwrites, never queues.
        A genuinely negative `free_qty` is clamped to zero, and the true
        negative value is preserved in a warning log entry (control-room
        binding rule, PR #182 comment 5025765389 §16) -- never silently
        dropped.
        """
        product = binding.product_variant_binding_id.product_variant_id
        location = binding.location_mapping_id.odoo_location_id
        free_qty = product.with_context(location=location.id).free_qty
        target = max(free_qty, 0.0)
        if free_qty < 0:
            _logger.warning(
                'Negative free_qty (%.4f) clamped to 0 for inventory pair '
                'store_id=%s item=%s location=%s.',
                free_qty, binding.store_id.id,
                binding.shopify_inventory_item_gid,
                binding.location_mapping_id.shopify_gid,
            )
        binding.sudo().write({'pending_target_available': target})
        return target, free_qty

    @api.model
    def _fail_closed_pre_c2(self, job_id, error_class, subreason, message):
        """Fail closed *before* C2 (PR #182 comment 5025803697 item 20 /
        comment 5025765389 §21): block the job for manual review and
        commit immediately, then raise.

        This is the extension seam that lets a domain's own
        `prepare_preconditions` callback reach the accepted
        `blocked_manual_review` disposition with its own `error_class`/
        `manual_review_subreason`, instead of the generic
        `shopify_temporary_server_network` bounded retry core's
        `_recover_pre_c2_failure` would otherwise apply to *any*
        exception raised from `prepare_preconditions`.

        How it works: `_block_original_job` (already used by this same
        module's `_handle_inventory_mutation_reconcile`, an existing
        cross-model call on `shopify.connector.job.dispatch` -- not a
        core file edit) writes `state='blocked_manual_review'` plus the
        domain's own error_class/subreason and clears the C1 ownership
        markers. Committing immediately (mirroring the commit-after-
        state-transition pattern core's own `_drain_mutation_one`
        already uses between C1 and `prepare_preconditions`) persists
        this disposition durably. The subsequent raise still triggers
        core's `_recover_pre_c2_failure`, but by that point
        `job.state != 'running'`, so its generic retry-scheduling branch
        is a no-op and the domain-specific blocked disposition is what
        survives. No mutation-attempt row is ever created (C2 is never
        reached), and no Shopify transport occurs.
        """
        job = self.env['shopify.connector.job'].browse(job_id)
        self.env['shopify.connector.job.dispatch']._block_original_job(
            job, error_class, subreason, message,
        )
        self.env.cr.commit()
        raise ValidationError(message)

    # ------------------------------------------------------------------
    # Triggers
    # ------------------------------------------------------------------

    @api.model
    def _enqueue_from_stock_moves(self, moves):
        """Odoo-event trigger (D-013-6a): enqueue push jobs for every
        mapped (variant, location) pair affected by a completed move.

        Only considers locations that are themselves mapped (source or
        destination), and only variants with an inventory-level binding
        for that mapping -- never unrelated products/stores/locations.
        """
        Binding = self.env['shopify.connector.inventory.level.binding']
        Mapping = self.env['shopify.connector.location.mapping']
        touched_location_ids = set()
        for move in moves:
            for loc in (move.location_id, move.location_dest_id):
                if loc.usage == 'internal':
                    touched_location_ids.add(loc.id)
        if not touched_location_ids:
            return
        mappings = Mapping.search([
            ('odoo_location_id', 'in', list(touched_location_ids)),
            ('push_enabled', '=', True),
        ])
        if not mappings:
            return
        product_ids = moves.product_id.ids
        bindings = Binding.search([
            ('location_mapping_id', 'in', mappings.ids),
            ('product_variant_binding_id.product_variant_id', 'in', product_ids),
        ])
        for binding in bindings:
            settings = self.env['shopify.connector.store.settings'].search(
                [('store_id', '=', binding.store_id.id)], limit=1,
            )
            if not settings or not settings.inventory_domain_enabled:
                continue
            self._refresh_pending_target(binding)
            self._try_enqueue_push_sync(
                binding.store_id, binding, 'odoo_event',
                trigger_origin='inventory_stock_change',
            )

    @api.model
    def _enqueue_manual_push(self, store):
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings or not settings.inventory_domain_enabled:
            raise UserError(
                'The inventory domain is not enabled for this store.'
            )
        bindings = self.env['shopify.connector.inventory.level.binding'].search([
            ('store_id', '=', store.id),
            ('location_mapping_id.push_enabled', '=', True),
        ])
        enqueued = self.env['shopify.connector.job']
        for binding in bindings:
            self._refresh_pending_target(binding)
            job = self._try_enqueue_push_sync(store, binding, 'manual_sync')
            enqueued |= job
        return enqueued

    @api.model
    def run_inventory_push_scan(self):
        """The scheduled push-scan cron entry point (D-013-6b, corrected
        per PR #182 comment 5025765389 item 13).

        Enqueues one typed, repeat-run `inventory_push_scan` job per
        eligible connected store, through the core enqueue service --
        the actual per-store scan work runs entirely on that job's own
        handler (`_handle_inventory_push_scan`), never inline on the
        cron thread, so retry/lifecycle/domain-gating/audit for the scan
        itself all use the job substrate like every other inventory job.
        """
        Settings = self.env['shopify.connector.store.settings']
        enqueued = self.env['shopify.connector.job']
        for settings in Settings.search([
            ('inventory_domain_enabled', '=', True),
            ('inventory_scheduled_sync_enabled', '=', True),
        ]):
            store = settings.store_id
            if store.state != 'connected':
                continue
            job = self.env['shopify.connector.job.enqueue'].enqueue(
                store, 'scheduled_sync', JOB_TYPE_PUSH_SCAN,
                payload_hash=uuid.uuid4().hex,
            )
            enqueued |= job
        return enqueued

    # ------------------------------------------------------------------
    # inventory_push_sync -- orchestration/read-only handler
    # ------------------------------------------------------------------

    @api.model
    def _handle_inventory_push_sync(self, job):
        """Orchestration/read-only handler (DEC-037 §5.1.A/§5.2).

        Issues no Shopify mutation and creates no `mutation.attempt`
        row. Performs the first-push/reconnect/store-identity/drift
        gates, derives the target, and enqueues at most one mutation job
        per dispatch.
        """
        Binding = self.env['shopify.connector.inventory.level.binding']
        binding = Binding.browse(job.res_id).exists()
        if not binding:
            job._transition_failed_final(
                'unknown_system_error',
                'The inventory-level binding no longer exists.',
            )
            return
        store = job.store_id

        # First-push guard (D-013-4): never enqueue any mutation for an
        # unconfirmed pair.
        if binding.first_push_state != 'confirmed':
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION, SUBREASON_DESTRUCTIVE_WRITE,
                'First push has not been confirmed for this pair; no '
                'mutation may be enqueued.',
            )
            return

        if not binding.location_mapping_id.push_enabled:
            job._transition_skipped(
                'Push is disabled for this mapped location.'
            )
            return

        # Store-identity check first (DEC-036 D18), then the fresh
        # Shopify read for this pair.
        try:
            read = self._read_shopify_inventory_pair(store, binding)
        except JobHandlerError:
            raise
        except Exception as exc:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'Failed to read the current Shopify inventory level.',
                type(exc).__name__,
            ) from exc

        if read['store_identity'] != store.shop_domain:
            job._transition_blocked_manual_review(
                ERROR_CLASS_STORE_IDENTITY, SUBREASON_STORE_IDENTITY,
                'Reconciliation-style read observed a different Shopify '
                'store identity before any push.',
            )
            return

        if read['tracked'] is False:
            job._transition_skipped(
                'The Shopify inventory item is not tracked; push skipped.'
            )
            return

        target, _free_qty = self._refresh_pending_target(binding)

        shopify_available = read['available']
        binding.sudo().write({
            'last_known_shopify_available': (
                shopify_available if shopify_available is not None
                else binding.last_known_shopify_available
            ),
        })

        if not read['level_exists']:
            # No InventoryLevel exists yet for this pair -- activation
            # is required before any quantity can be set. This
            # orchestration job's own `operation_scope_key` (identical
            # across job types for the same pair -- it never encodes
            # job_type) must be cleared *before* the child job's insert,
            # or the two would collide on the DB unique constraint while
            # this job is still non-terminal. Terminalize first and
            # flush, exactly mirroring `_handoff_supersede`'s own
            # ordering, before creating the child.
            job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
            job.flush_recordset(['state'])
            self._create_inventory_job(
                store, job.job_source, JOB_TYPE_ACTIVATE, binding,
                trigger_origin=job.trigger_origin or False,
            )
            job._log_transition(
                'state_change',
                'No Shopify inventory level exists yet; enqueued '
                'inventory_activate.',
                from_state='running', to_state='succeeded',
            )
            return

        # Drift classification -- corrected three-way matrix (PR #182
        # comment 5025765389 item 14): Shopify already reflecting the
        # current Odoo target is never drift, regardless of whether it
        # also still equals last_pushed_available. Unexplained drift
        # exists only when Shopify differs from BOTH last-pushed and the
        # current target -- never a silent overwrite either way.
        has_prior_push = bool(binding.last_pushed_at)

        if shopify_available == target:
            # Already at the target business state; nothing to push.
            job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
            job._log_transition(
                'state_change',
                'Shopify already reflects the current target; no push '
                'needed.',
                from_state='running', to_state='succeeded',
            )
            return

        if has_prior_push and shopify_available != binding.last_pushed_available:
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'Unexplained Shopify-side inventory drift detected '
                '(current=%.4f, last-pushed=%.4f, target=%.4f); the '
                'pending push is blocked until this is reviewed.' % (
                    shopify_available, binding.last_pushed_available, target,
                ),
            )
            return

        # Either no prior successful push is recorded yet, or Shopify
        # still matches the last-pushed value and only the Odoo target
        # changed -- a known local change; enqueue toward the fresh
        # target. Terminalize this orchestration job and flush first
        # (same reasoning as the activation branch above) so its own
        # `operation_scope_key` clears before the child's insert.
        job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
        job.flush_recordset(['state'])
        self._create_inventory_job(
            store, job.job_source, JOB_TYPE_SET_QUANTITIES, binding,
            trigger_origin=job.trigger_origin or False,
        )
        job._log_transition(
            'state_change',
            'Enqueued inventory_set_quantities toward the current target.',
            from_state='running', to_state='succeeded',
        )

    @api.model
    def _read_shopify_inventory_pair(self, store, binding):
        """One narrow Shopify read for a pair, corrected to the official
        Shopify Admin GraphQL 2026-07 request shape (PR #182 comment
        5025765389 item 1): the 2026-07 root `inventoryLevel` field no
        longer accepts `inventoryItemId`/`locationId` -- this always
        reads through `inventoryItem(id:) { inventoryLevel(locationId:)
        { ... } }` instead. Uses the read-only `execute()` transport
        (never `execute_business` -- this is not a mutation).

        Returns a structured dict distinguishing every case the review
        requires: `item_exists` (False only when the inventory item
        itself does not exist at Shopify), `tracked` (None only when
        `item_exists` is False), `level_exists` (whether an
        InventoryLevel row exists for this pair), `available`
        (non-`None` only when `level_exists`), and `updated_at`. Any
        malformed/partial/ambiguous response shape raises
        `JobHandlerError(data_shape_schema_mismatch, ...)` -- fails
        closed rather than silently defaulting a missing item to
        `tracked=True` or a malformed response to "no level".
        """
        client = self.env['shopify.connector.api.client']
        query = (
            'query InventoryPairRead($itemId: ID!, $locationId: ID!) { '
            'inventoryItem(id: $itemId) { id tracked '
            'inventoryLevel(locationId: $locationId) { id '
            'quantities(names: ["available"]) { name quantity updatedAt '
            '} } } '
            'shop { myshopifyDomain } }'
        )
        variables = {
            'itemId': binding.shopify_inventory_item_gid,
            'locationId': binding.location_mapping_id.shopify_gid,
        }
        result = client.execute(store, query, variables)
        data = (result or {}).get('data')
        if not isinstance(data, dict):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Malformed Shopify inventory-pair read response (no data).',
            )
        shop = data.get('shop') or {}
        store_identity = shop.get('myshopifyDomain')
        item = data.get('inventoryItem')
        if item is None:
            # The inventory item genuinely does not exist at Shopify --
            # never defaulted to tracked=True.
            return {
                'store_identity': store_identity,
                'item_exists': False,
                'tracked': None,
                'level_exists': False,
                'available': None,
                'updated_at': False,
            }
        if not isinstance(item, dict) or not isinstance(
            item.get('tracked'), bool
        ):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Malformed Shopify inventoryItem shape in pair read.',
            )
        tracked = item['tracked']
        level = item.get('inventoryLevel')
        if level is None:
            return {
                'store_identity': store_identity,
                'item_exists': True,
                'tracked': tracked,
                'level_exists': False,
                'available': None,
                'updated_at': False,
            }
        if not isinstance(level, dict):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Malformed Shopify inventoryLevel shape in pair read.',
            )
        available = None
        updated_at = False
        found_available_entry = False
        for quantity in level.get('quantities') or []:
            if not isinstance(quantity, dict):
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Malformed Shopify quantities entry in pair read.',
                )
            if quantity.get('name') == 'available':
                found_available_entry = True
                available = quantity.get('quantity')
                updated_at = quantity.get('updatedAt') or False
        if not found_available_entry:
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Shopify inventoryLevel is present but no "available" '
                'quantity entry was returned.',
            )
        return {
            'store_identity': store_identity,
            'item_exists': True,
            'tracked': tracked,
            'level_exists': True,
            'available': available,
            'updated_at': updated_at,
        }

    # ------------------------------------------------------------------
    # inventory_push_scan / inventory_first_push_preview /
    # inventory_location_sync handlers
    # ------------------------------------------------------------------

    @api.model
    def _handle_inventory_push_scan(self, job):
        """Scan one store's push-enabled bindings and enqueue deltas only
        (PR #182 comment 5025765389 item 13). Never runs inline on the
        cron thread -- `run_inventory_push_scan` only enqueues this
        typed per-store job; this handler performs the actual scan, and
        respects blocked-pair serialization and the first-push/reconnect
        gates enforced downstream by `inventory_push_sync` itself at
        dispatch time.
        """
        store = job.store_id
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings or not settings.inventory_domain_enabled:
            job._transition_skipped(
                'The inventory domain is no longer enabled for this store.'
            )
            return
        Binding = self.env['shopify.connector.inventory.level.binding']
        bindings = Binding.search([
            ('store_id', '=', store.id),
            ('location_mapping_id.push_enabled', '=', True),
        ])
        mapped = len(bindings)
        enqueued_count = 0
        coalesced_count = 0
        unchanged_count = 0
        for binding in bindings:
            target, _free_qty = self._refresh_pending_target(binding)
            if target == binding.last_pushed_available:
                unchanged_count += 1
                continue
            result = self._try_enqueue_push_sync(store, binding, 'scheduled_sync')
            if result:
                enqueued_count += 1
            else:
                coalesced_count += 1
        settings.sudo().write({
            'inventory_last_push_scan_at': fields.Datetime.now(),
        })
        job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
        job._log_transition(
            'state_change',
            'Inventory push scan for store %d: mapped=%d enqueued=%d '
            'coalesced=%d unchanged=%d.' % (
                store.id, mapped, enqueued_count, coalesced_count,
                unchanged_count,
            ),
            from_state='running', to_state='succeeded',
        )

    @api.model
    def _handle_inventory_first_push_preview(self, job):
        """Compute and store the first-push preview quantity for a pair.

        Never writes to Shopify. Sets `first_push_state='previewed'`
        only from `pending` -- an already-previewed or confirmed row is
        left untouched (idempotent re-run).
        """
        Binding = self.env['shopify.connector.inventory.level.binding']
        binding = Binding.browse(job.res_id).exists()
        if not binding:
            job._transition_failed_final(
                'unknown_system_error',
                'The inventory-level binding no longer exists.',
            )
            return
        target, _free_qty = self._refresh_pending_target(binding)
        if binding.first_push_state == 'pending':
            binding.sudo().write({
                'first_push_state': 'previewed',
                'first_push_preview_qty': target,
            })
        job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
        job._log_transition(
            'verification_read',
            'First-push preview recorded: %.4f.' % target,
            from_state='running', to_state='succeeded',
        )

    @api.model
    def enqueue_first_push_preview(self, binding):
        """Sanctioned `inventory_first_push_preview` job admission (PR
        #182 comment 5025803697 item 22.C). Private service method --
        no public action/UI is added. `job_source=
        'export_preview_dry_run'` (a core-recognized, store-state-
        ungated diagnostic source): this job never issues a Shopify
        mutation, it only computes and stores a preview quantity.
        """
        return self._create_inventory_job(
            binding.store_id, 'export_preview_dry_run',
            JOB_TYPE_FIRST_PUSH_PREVIEW, binding,
        )

    @api.model
    def enqueue_location_sync(self, store):
        """Sanctioned `inventory_location_sync` job admission (PR #182
        comment 5025803697 item 22.C). Private service method -- no
        public action/UI is added. Domain-gated on
        `inventory_domain_enabled`; the underlying store-connected gate
        for this business `job_source` is enforced by the core enqueue
        service itself.
        """
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings or not settings.inventory_domain_enabled:
            raise UserError(
                'The inventory domain is not enabled for this store.'
            )
        return self.env['shopify.connector.job.enqueue'].enqueue(
            store, 'scheduled_sync', JOB_TYPE_LOCATION_SYNC,
            payload_hash=uuid.uuid4().hex,
        )

    @api.model
    def _handle_inventory_location_sync(self, job):
        """Populate the core Shopify location cache (D-013-5).

        Reads the `locations` query (paginated, `includeInactive:
        false`) and upserts `shopify.connector.location` rows via the
        one sanctioned, narrow, named `sudo()` elevation this module
        introduces -- the core cache's ACL deliberately grants no
        group create/write, so a non-elevated upsert would always
        raise. This is the module's sole sudo() site.
        """
        store = job.store_id
        client = self.env['shopify.connector.api.client']
        Location = self.env['shopify.connector.location']
        cursor = None
        upserted = 0
        while True:
            query = (
                'query LocationsSync($cursor: String) { '
                'locations(first: 100, after: $cursor, '
                'includeInactive: false) { '
                'edges { cursor node { id name } } '
                'pageInfo { hasNextPage } } }'
            )
            result = client.execute(store, query, {'cursor': cursor})
            data = (result or {}).get('data') or {}
            connection = data.get('locations') or {}
            edges = connection.get('edges') or []
            for edge in edges:
                node = edge.get('node') or {}
                gid = node.get('id')
                if not gid:
                    continue
                existing = Location.sudo().search([
                    ('store_id', '=', store.id),
                    ('shopify_location_gid', '=', gid),
                ], limit=1)
                vals = {
                    'store_id': store.id,
                    'shopify_location_gid': gid,
                    'name': node.get('name') or gid,
                    'shopify_location_active': True,
                    'last_synced_at': fields.Datetime.now(),
                }
                if existing:
                    existing.sudo().write(vals)
                else:
                    Location.sudo().create(vals)
                upserted += 1
            page_info = connection.get('pageInfo') or {}
            if not page_info.get('hasNextPage') or not edges:
                break
            cursor = edges[-1].get('cursor')
        job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
        job._log_transition(
            'verification_read',
            'Location cache sync upserted %d location(s).' % upserted,
            from_state='running', to_state='succeeded',
        )

    # ------------------------------------------------------------------
    # Sanctioned backend creation/admission services (PR #182 comment
    # 5025803697 item 22): both the location-mapping and inventory-
    # level-binding models inherit the protected binding mixin, so
    # ordinary create() of their required fields is denied by design.
    # These are the narrow, authorization-checked, service-owned
    # creation surfaces -- no new public action, no UI.
    # ------------------------------------------------------------------

    @api.model
    def create_or_update_location_mapping(
        self, store, odoo_location, shopify_location_gid, push_enabled=True,
    ):
        """Sanctioned location-mapping creation/update (item 22.A).

        Resolves and validates `odoo_location` in the caller's own
        (non-elevated) environment first, so ordinary Odoo visibility
        and the model's own `@api.constrains` (internal-location,
        company, no-ancestor/descendant-overlap) all still apply before
        any elevation -- a narrow `sudo()` is used only for the mixin's
        protected-field create/write itself. Identity is always
        explicit: the Shopify Location GID must be supplied by the
        caller, never inferred by name.
        """
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_operator'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                "Only a Shopify Connector Operator or Administrator may "
                "create or update a location mapping."
            )
        if not isinstance(shopify_location_gid, str) or not shopify_location_gid:
            raise UserError("An explicit Shopify Location GID is required.")
        odoo_location = odoo_location.exists()
        if not odoo_location:
            raise UserError("The Odoo location does not exist.")
        if odoo_location.usage != 'internal':
            raise UserError(
                "Only an internal Odoo stock location can be mapped."
            )
        if odoo_location.company_id and odoo_location.company_id != self.env.company:
            raise UserError(
                "The Odoo location belongs to a different company."
            )
        Mapping = self.env['shopify.connector.location.mapping']
        existing = Mapping.search([
            ('store_id', '=', store.id),
            ('odoo_location_id', '=', odoo_location.id),
        ], limit=1)
        vals = {
            'store_id': store.id,
            'shopify_gid': shopify_location_gid,
            'odoo_location_id': odoo_location.id,
            'match_key': 'manual',
            'push_enabled': bool(push_enabled),
        }
        if existing:
            existing.sudo().write(vals)
            return existing
        return Mapping.sudo().create(vals)

    @api.model
    def ensure_inventory_level_binding(
        self, variant_binding, location_mapping, shopify_inventory_item_gid,
    ):
        """Sanctioned inventory-level-binding creation/ensure (item 22.B).

        Resolves both `variant_binding` and `location_mapping` in the
        caller's own environment, enforces same-store consistency
        before any elevation, and idempotently returns an already-
        existing exact binding rather than raising a duplicate-identity
        error when the caller re-requests the same pair with the same
        GID.
        """
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_operator'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                "Only a Shopify Connector Operator or Administrator may "
                "create an inventory-level binding."
            )
        variant_binding = variant_binding.exists()
        location_mapping = location_mapping.exists()
        if not variant_binding or not location_mapping:
            raise UserError(
                "The product-variant binding and location mapping must "
                "both exist."
            )
        if variant_binding.store_id != location_mapping.store_id:
            raise UserError(
                "The product-variant binding and location mapping must "
                "belong to the same store."
            )
        if (
            not isinstance(shopify_inventory_item_gid, str)
            or not shopify_inventory_item_gid
        ):
            raise UserError(
                "An explicit Shopify inventory-item GID is required."
            )
        Binding = self.env['shopify.connector.inventory.level.binding']
        existing = Binding.search([
            ('store_id', '=', variant_binding.store_id.id),
            ('product_variant_binding_id', '=', variant_binding.id),
            ('location_mapping_id', '=', location_mapping.id),
        ], limit=1)
        if existing:
            if existing.shopify_inventory_item_gid != shopify_inventory_item_gid:
                raise UserError(
                    "An inventory-level binding already exists for this "
                    "pair with a different Shopify inventory-item GID."
                )
            return existing
        return Binding.sudo().create({
            'store_id': variant_binding.store_id.id,
            'product_variant_binding_id': variant_binding.id,
            'location_mapping_id': location_mapping.id,
            'shopify_inventory_item_gid': shopify_inventory_item_gid,
        })

    # ------------------------------------------------------------------
    # Atomic handoff primitives (DEC-037 §5.4), used by both mutation
    # domains' `apply_consequence` callbacks below.
    # ------------------------------------------------------------------

    @api.model
    def _lock_binding_for_pair(self, job):
        Binding = self.env['shopify.connector.inventory.level.binding']
        binding = Binding.browse(job.res_id).exists()
        if not binding:
            raise ValidationError(
                'The inventory-level binding for this pair no longer exists.'
            )
        locked = binding.try_lock_for_update()
        if not locked:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'The inventory pair is held by another worker; retry '
                'later.',
            )
        locked.invalidate_recordset()
        return locked

    @api.model
    def _handoff_supersede(self, job, binding, cancel_reason, new_job_type, cas_retry_ordinal=0):
        """Handoffs C/D (DEC-037 §5.4): cancel `job`, superseding it with
        one atomically-created replacement of `new_job_type`, under the
        pair's row lock. Both writes occur in the transaction already
        open at C3/reconciliation-consequence-apply time.
        """
        from_state = job.state
        job.sudo().write({
            'state': 'cancelled',
            'cancel_reason': cancel_reason,
        })
        job._log_transition(
            'state_change', 'Superseded by a replacement job (%s).' % (
                cancel_reason,
            ),
            from_state=from_state, to_state='cancelled',
        )
        # Flush so this job's operation_scope_key clears (terminal state)
        # before the replacement job's own scope key is computed --
        # otherwise the two would momentarily collide on the DB unique
        # constraint within this same transaction.
        job.flush_recordset(['state'])
        new_job = self._create_inventory_job(
            job.store_id, job.job_source, new_job_type, binding,
            trigger_origin=job.trigger_origin or False,
            cas_retry_ordinal=cas_retry_ordinal,
        )
        job.sudo().write({'superseded_by_job_id': new_job.id})
        return new_job

    @api.model
    def _handoff_succeed_to_fresh_orchestration(self, job, binding):
        """Handoff B (DEC-037 §5.4): once `inventory_activate` reaches
        `succeeded` (already written by the generic C3/reconciliation
        committer before this domain callback runs), atomically enqueue
        a fresh `inventory_push_sync` in the same transaction -- never
        `superseded_by_job_id`/`cancel_reason` (this is a successful
        completion, not a replacement), and never waiting for an
        unrelated later scan/manual trigger."""
        job.flush_recordset(['state'])
        new_job = self._create_inventory_job(
            job.store_id, job.job_source, JOB_TYPE_PUSH_SYNC, binding,
            trigger_origin=job.trigger_origin or False,
        )
        job._log_transition(
            'state_change',
            'Activation confirmed applied; atomically enqueued a fresh '
            'inventory_push_sync (job %d).' % new_job.id,
        )
        return new_job

    @api.model
    def _block_pair(self, job, error_class, subreason, message):
        from_state = job.state
        job.sudo().write({
            'state': 'blocked_manual_review',
            'error_class': error_class,
            'manual_review_subreason': subreason,
            'finished_at': fields.Datetime.now(),
        })
        job._log_transition(
            'state_change', message,
            from_state=from_state, to_state='blocked_manual_review',
        )

    # ------------------------------------------------------------------
    # inventory_set_quantities -- mutation-domain strategy
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_set_quantities(self, job):
        binding = self.env[
            'shopify.connector.inventory.level.binding'
        ].browse(job.res_id)
        return {
            'job_id': job.id,
            'store_id': job.store_id.id,
            'binding_id': binding.id,
            'inventory_item_gid': binding.shopify_inventory_item_gid,
            'location_gid': binding.location_mapping_id.shopify_gid,
            'expected_connection_generation': job.expected_connection_generation,
            'expected_store_identity': job.store_id.shop_domain,
        }

    @api.model
    def _prepare_preconditions_set_quantities(self, local_snapshot, owner_context):
        """A fresh, narrow CAS pre-read immediately before this attempt's
        own C2 -- never the binding's informational
        `last_known_shopify_available` field (DEC-037 §4 row 1).

        Every genuinely unsafe precondition discovered by this fresh
        read fails closed *before* C2 via `_fail_closed_pre_c2` (PR #182
        comment 5025803697 item 20 / comment 5025765389 §21): a
        different store identity, a missing/inactive level, an item that
        has gone untracked, a non-integral target quantity, or a missing
        required GID -- none of these may silently proceed to transport,
        and none creates a mutation-attempt row.
        """
        job_id = local_snapshot['job_id']
        store = self.env['shopify.connector.store'].browse(
            local_snapshot['store_id']
        )
        binding = self.env['shopify.connector.inventory.level.binding'].browse(
            local_snapshot['binding_id']
        )
        if (
            not local_snapshot['inventory_item_gid']
            or not local_snapshot['location_gid']
        ):
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE_RISK,
                'Missing a required Shopify identifier before transport.',
            )

        read = self._read_shopify_inventory_pair(store, binding)

        if read['store_identity'] != local_snapshot['expected_store_identity']:
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_STORE_IDENTITY, SUBREASON_STORE_IDENTITY,
                'Fresh pre-C2 read observed a different Shopify store '
                'identity.',
            )
        if not read['level_exists']:
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_LOCATION_MISSING,
                SUBREASON_LOCATION_MISSING,
                'Fresh pre-C2 read found no Shopify inventory level for '
                'this pair; activation is required before quantities can '
                'be set.',
            )
        if read['tracked'] is False:
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_LOCATION_MISSING,
                SUBREASON_LOCATION_MISSING,
                'Fresh pre-C2 read found the Shopify inventory item is no '
                'longer tracked.',
            )

        change_from_quantity = read['available']
        target, _free_qty = self._refresh_pending_target(binding)
        target_int, is_integral = _integral_quantity_or_none(target)
        if not is_integral:
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_DATA_SHAPE, SUBREASON_BINDING_CONFLICT,
                'Target quantity %.6f is not integral within the accepted '
                'tolerance; refusing to round or truncate before Shopify '
                'transport.' % (target,),
            )

        db_uuid = self.env['ir.config_parameter'].sudo().get_param(
            'database.uuid'
        )
        if not db_uuid:
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE_RISK,
                'No stable database UUID is configured; refusing to build '
                'a reference document URI.',
            )
        reference_uri = 'odoo://%s/shopify.connector.job/%d' % (
            db_uuid, job_id,
        )

        idempotency_key = str(uuid.uuid4())
        operation = (
            'mutation InventorySetQuantities($input: '
            'InventorySetQuantitiesInput!, $idempotencyKey: String!) { '
            'inventorySetQuantities(input: $input) '
            '@idempotent(key: $idempotencyKey) { '
            'inventoryAdjustmentGroup { reason referenceDocumentUri '
            'changes { name delta quantityAfterChange } } '
            'userErrors { code field message } } }'
        )
        variables = {
            'input': {
                'name': 'available',
                'reason': 'correction',
                'referenceDocumentUri': reference_uri,
                'quantities': [{
                    'inventoryItemId': local_snapshot['inventory_item_gid'],
                    'locationId': local_snapshot['location_gid'],
                    'quantity': target_int,
                    'changeFromQuantity': int(change_from_quantity),
                }],
            },
            'idempotencyKey': idempotency_key,
        }
        return {
            'mutation_domain': MUTATION_DOMAIN_SET_QUANTITIES,
            'operation': operation,
            'variables': variables,
            'business_intent': {
                'mutation_domain': MUTATION_DOMAIN_SET_QUANTITIES,
                'inventory_item_gid': local_snapshot['inventory_item_gid'],
                'location_gid': local_snapshot['location_gid'],
                'target_quantity': target_int,
            },
            'remote_mutation_intent': {
                'operation_name': 'inventorySetQuantities',
                'inventory_item_gid': local_snapshot['inventory_item_gid'],
                'location_gid': local_snapshot['location_gid'],
            },
            'preconditions_snapshot': {
                'inventory_item_gid': local_snapshot['inventory_item_gid'],
                'location_gid': local_snapshot['location_gid'],
                'target_quantity': target_int,
                'change_from_quantity': int(change_from_quantity),
                'snapshot_taken_at': fields.Datetime.to_string(
                    fields.Datetime.now()
                ),
            },
            'expected_connection_generation':
                local_snapshot['expected_connection_generation'],
            'expected_store_identity':
                local_snapshot['expected_store_identity'],
            'shopify_idempotency_key': idempotency_key,
        }

    @api.model
    def _transport_set_quantities(self, request, attempt_context):
        store = self.env['shopify.connector.store'].browse(
            attempt_context['store_id']
        )
        client = self.env['shopify.connector.api.client']
        requested_target = (
            request.get('variables', {}).get('input', {})
            .get('quantities', [{}])[0].get('quantity')
        )
        try:
            with client.execute_business(
                attempt_context['job_id'], store,
                request['operation'], request['variables'],
                mutation_context={
                    'job_id': attempt_context['job_id'],
                    'attempt_id': attempt_context['attempt_id'],
                    'attempt_token': attempt_context['attempt_token'],
                    'mutation_domain': attempt_context['mutation_domain'],
                },
            ) as result:
                data = (result or {}).get('data') or {}
                payload = data.get('inventorySetQuantities') or {}
                return {
                    'outcome': None,
                    'user_errors': payload.get('userErrors') or [],
                    'adjustment_group': payload.get('inventoryAdjustmentGroup'),
                    'requested_target': requested_target,
                    'evidence': {'transport': 'inventorySetQuantities'},
                }
        except Exception as exc:
            return {
                'outcome': 'uncertain',
                'error_class': _normalize_transport_error_class(exc),
                'evidence': {'exception_class': type(exc).__name__},
            }

    @api.model
    def _is_valid_set_quantities_success(self, group, expected_target):
        """Direct-success evidence gate (PR #182 comment 5025765389 item
        6): an empty `userErrors` list alone is never sufficient. A
        `null`/missing group, missing/malformed `changes`, a wrong
        quantity name, an absent or mismatched `quantityAfterChange` --
        every one of these must be rejected here, never trusted."""
        if not isinstance(group, dict):
            return False
        changes = group.get('changes')
        if not isinstance(changes, list) or not changes:
            return False
        for change in changes:
            if not isinstance(change, dict):
                return False
            if change.get('name') != 'available':
                continue
            quantity_after = change.get('quantityAfterChange')
            if quantity_after is None:
                return False
            try:
                return int(quantity_after) == int(expected_target)
            except (TypeError, ValueError):
                return False
        return False

    @api.model
    def _classify_direct_set_quantities(self, result):
        result = result or {}
        if result.get('outcome') == 'uncertain':
            return {
                'observed_outcome': 'uncertain',
                'error_class': result.get('error_class', ERROR_CLASS_TEMPORARY),
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': 'Transport-level uncertainty during '
                            'inventorySetQuantities.',
                'evidence': result.get('evidence') or {},
            }
        user_errors = result.get('user_errors') or []
        evidence = result.get('evidence') or {}
        if not user_errors:
            group = result.get('adjustment_group')
            expected_target = result.get('requested_target')
            if not self._is_valid_set_quantities_success(group, expected_target):
                return {
                    'observed_outcome': 'uncertain',
                    'error_class': ERROR_CLASS_DATA_SHAPE,
                    'manual_review_subreason': False,
                    'action': 'reconcile',
                    'message': 'inventorySetQuantities returned an empty '
                                'userErrors list but the success payload '
                                'is missing or does not evidence the '
                                'requested change; reconciling before '
                                'trusting this as applied.',
                    'evidence': evidence,
                }
            return {
                'observed_outcome': 'succeeded',
                'error_class': False,
                'manual_review_subreason': False,
                'action': 'succeed',
                'message': 'inventorySetQuantities applied.',
                'evidence': evidence,
            }
        codes = {(error.get('code') or '') for error in user_errors}
        if 'CHANGE_FROM_QUANTITY_STALE' in codes:
            return {
                'observed_outcome': 'failed_clean',
                'error_class': ERROR_CLASS_CONCURRENCY,
                'manual_review_subreason': False,
                'action': 'domain_callback',
                'message': 'CAS mismatch: changeFromQuantity is stale.',
                'evidence': evidence,
                'domain_payload': {'reason': 'cas_stale'},
            }
        if 'ITEM_NOT_STOCKED_AT_LOCATION' in codes:
            return {
                'observed_outcome': 'failed_clean',
                'error_class': ERROR_CLASS_LOCATION_MISSING,
                'manual_review_subreason': SUBREASON_LOCATION_MISSING,
                'action': 'block_manual_review',
                'message': 'ITEM_NOT_STOCKED_AT_LOCATION: activation is '
                            'required before this pair can be set.',
                'evidence': evidence,
            }
        if codes & {
            'IDEMPOTENCY_KEY_PARAMETER_MISMATCH',
            'IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED',
        }:
            return {
                'observed_outcome': 'uncertain',
                'error_class': ERROR_CLASS_IDEMPOTENCY,
                'manual_review_subreason': SUBREASON_IDEMPOTENCY,
                'action': 'block_manual_review',
                'message': 'Structured idempotency-contract violation.',
                'evidence': evidence,
            }
        if 'IDEMPOTENCY_CONCURRENT_REQUEST' in codes:
            return {
                'observed_outcome': 'uncertain',
                'error_class': ERROR_CLASS_CONCURRENCY,
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': 'A concurrent identical request is already in '
                            'progress.',
                'evidence': evidence,
            }
        # Every other confirmed InventorySetQuantitiesUserErrorCode value
        # (INVALID_*, NO_DUPLICATE_..., NON_MUTABLE_INVENTORY_ITEM) --
        # ordinary clean-rejection/validation, never message-text routed.
        return {
            'observed_outcome': 'failed_clean',
            'error_class': ERROR_CLASS_VALIDATION,
            'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
            'action': 'block_manual_review',
            'message': 'Shopify rejected the inventorySetQuantities '
                        'request (validation/binding conflict).',
            'evidence': evidence,
        }

    @api.model
    def _reconcile_set_quantities(self, attempt):
        store = attempt.store_id
        binding = self.env[
            'shopify.connector.inventory.level.binding'
        ].search([('id', '=', attempt.job_id.res_id)], limit=1)
        read = self._read_shopify_inventory_pair(store, binding)
        if read['store_identity'] != attempt.expected_store_identity:
            return {
                'verdict': 'not_applied',
                'observed_store_identity': read['store_identity'] or '',
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_STORE_IDENTITY,
                'manual_review_subreason': SUBREASON_STORE_IDENTITY,
                'message': 'Reconciliation observed a different store '
                            'identity.',
                'evidence': {},
            }
        target = (attempt.preconditions_snapshot or {}).get('target_quantity')
        pre_attempt = (attempt.preconditions_snapshot or {}).get(
            'change_from_quantity'
        )
        current = read['available'] if read['level_exists'] else None
        parsed_updated_at = _parse_shopify_datetime(read['updated_at'])
        transport_at = _odoo_datetime_to_utc(attempt.transport_at)
        freshness_usable = bool(parsed_updated_at) and bool(transport_at)
        fresh_change_evidenced = (
            freshness_usable and parsed_updated_at > transport_at
        )
        if current is not None and target is not None and current == target:
            return {
                'verdict': 'applied',
                'observed_store_identity': read['store_identity'],
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Current available equals the target quantity.',
                'evidence': {'current': current, 'target': target},
            }
        if (
            current is not None and pre_attempt is not None
            and current == pre_attempt
            and freshness_usable and not fresh_change_evidenced
        ):
            return {
                'verdict': 'not_applied',
                'observed_store_identity': read['store_identity'],
                'action': 'domain_callback',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Current available still equals the '
                            'pre-attempt value with affirmative freshness '
                            'evidence of no post-transport change.',
                'evidence': {'current': current, 'pre_attempt': pre_attempt},
            }
        # Freshness unavailable/unparsable, a same-value ABA (current ==
        # pre_attempt but a later-timestamped change is evidenced), a
        # malformed timestamp, or any third value: never `not_applied` by
        # default -- scheduled for another read, and routed to the
        # existing bounded-inconclusive-then-data-shape-block safety cap
        # if it never resolves (never a silent guess).
        return {
            'verdict': 'inconclusive',
            'observed_store_identity': read['store_identity'] or '',
            'action': None,
            'error_class': None,
            'manual_review_subreason': None,
            'message': 'Reconciliation evidence is ambiguous; scheduling '
                        'another read.',
            'evidence': {'current': current},
        }

    @api.model
    def _apply_consequence_set_quantities(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        binding = self._lock_binding_for_pair(job)
        domain_payload = consequence.get('domain_payload') or {}
        if phase == 'direct' and domain_payload.get('reason') == 'cas_stale':
            if job.cas_retry_ordinal >= MAX_CAS_RETRY_ORDINAL:
                self._block_pair(
                    job, ERROR_CLASS_CONCURRENCY, SUBREASON_BINDING_CONFLICT,
                    'Bounded CAS-stale replacement chain exhausted at '
                    'ordinal %d; manual review is required.' % (
                        job.cas_retry_ordinal,
                    ),
                )
                return
            self._handoff_supersede(
                job, binding, 'cas_stale_bounded_replacement',
                JOB_TYPE_SET_QUANTITIES,
                cas_retry_ordinal=job.cas_retry_ordinal + 1,
            )
            return
        if phase == 'reconciliation' and consequence['action'] == 'domain_callback':
            # not_applied reconciliation verdict -> new same-domain job.
            self._handoff_supersede(
                job, binding, 'reconciliation_not_applied_replacement',
                JOB_TYPE_SET_QUANTITIES,
            )
            return
        if consequence['action'] == 'succeed':
            binding.sudo().write({
                'last_pushed_available': (
                    attempt.preconditions_snapshot or {}
                ).get('target_quantity'),
                'last_pushed_at': fields.Datetime.now(),
                'shopify_gid': binding.shopify_gid or (
                    '%s:%s' % (
                        binding.shopify_inventory_item_gid,
                        binding.location_mapping_id.shopify_gid,
                    )
                ),
            })

    # ------------------------------------------------------------------
    # inventory_activate -- mutation-domain strategy
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_activate(self, job):
        binding = self.env[
            'shopify.connector.inventory.level.binding'
        ].browse(job.res_id)
        return {
            'job_id': job.id,
            'store_id': job.store_id.id,
            'binding_id': binding.id,
            'inventory_item_gid': binding.shopify_inventory_item_gid,
            'location_gid': binding.location_mapping_id.shopify_gid,
            'expected_connection_generation': job.expected_connection_generation,
            'expected_store_identity': job.store_id.shop_domain,
        }

    @api.model
    def _prepare_preconditions_activate(self, local_snapshot, owner_context):
        if (
            not local_snapshot['inventory_item_gid']
            or not local_snapshot['location_gid']
        ):
            self._fail_closed_pre_c2(
                local_snapshot['job_id'], ERROR_CLASS_DATA_SHAPE,
                SUBREASON_DUPLICATE_RISK,
                'Missing a required Shopify identifier before transport.',
            )
        idempotency_key = str(uuid.uuid4())
        operation = (
            'mutation InventoryActivate($inventoryItemId: ID!, '
            '$locationId: ID!, $available: Int!, '
            '$idempotencyKey: String!) { '
            'inventoryActivate(inventoryItemId: $inventoryItemId, '
            'locationId: $locationId, available: $available, '
            'stockAtLegacyLocation: false) '
            '@idempotent(key: $idempotencyKey) { '
            'inventoryLevel { id item { id } location { id } '
            'quantities(names: ["available"]) { name quantity } } '
            'userErrors { field message } } }'
        )
        variables = {
            'inventoryItemId': local_snapshot['inventory_item_gid'],
            'locationId': local_snapshot['location_gid'],
            'available': 0,
            'idempotencyKey': idempotency_key,
        }
        return {
            'mutation_domain': MUTATION_DOMAIN_ACTIVATE,
            'operation': operation,
            'variables': variables,
            'business_intent': {
                'mutation_domain': MUTATION_DOMAIN_ACTIVATE,
                'inventory_item_gid': local_snapshot['inventory_item_gid'],
                'location_gid': local_snapshot['location_gid'],
                'initial_available': 0,
            },
            'remote_mutation_intent': {
                'operation_name': 'inventoryActivate',
                'inventory_item_gid': local_snapshot['inventory_item_gid'],
                'location_gid': local_snapshot['location_gid'],
            },
            'preconditions_snapshot': {
                'inventory_item_gid': local_snapshot['inventory_item_gid'],
                'location_gid': local_snapshot['location_gid'],
                'initial_available': 0,
                'snapshot_taken_at': fields.Datetime.to_string(
                    fields.Datetime.now()
                ),
            },
            'expected_connection_generation':
                local_snapshot['expected_connection_generation'],
            'expected_store_identity':
                local_snapshot['expected_store_identity'],
            'shopify_idempotency_key': idempotency_key,
        }

    @api.model
    def _transport_activate(self, request, attempt_context):
        store = self.env['shopify.connector.store'].browse(
            attempt_context['store_id']
        )
        client = self.env['shopify.connector.api.client']
        requested_item_gid = request.get('variables', {}).get('inventoryItemId')
        requested_location_gid = request.get('variables', {}).get('locationId')
        try:
            with client.execute_business(
                attempt_context['job_id'], store,
                request['operation'], request['variables'],
                mutation_context={
                    'job_id': attempt_context['job_id'],
                    'attempt_id': attempt_context['attempt_id'],
                    'attempt_token': attempt_context['attempt_token'],
                    'mutation_domain': attempt_context['mutation_domain'],
                },
            ) as result:
                data = (result or {}).get('data') or {}
                payload = data.get('inventoryActivate') or {}
                return {
                    'outcome': None,
                    'user_errors': payload.get('userErrors') or [],
                    'inventory_level': payload.get('inventoryLevel'),
                    'requested_item_gid': requested_item_gid,
                    'requested_location_gid': requested_location_gid,
                    'evidence': {'transport': 'inventoryActivate'},
                }
        except Exception as exc:
            return {
                'outcome': 'uncertain',
                'error_class': _normalize_transport_error_class(exc),
                'evidence': {'exception_class': type(exc).__name__},
            }

    @api.model
    def _is_valid_activate_success(
        self, level, expected_item_gid, expected_location_gid,
    ):
        """Direct-success evidence gate (PR #182 comment 5025765389 item
        7): a non-null `InventoryLevel` alone is never sufficient -- the
        returned item/location must match what was requested, and the
        returned `available` quantity must be exactly zero."""
        if not isinstance(level, dict):
            return False
        item = level.get('item') or {}
        location = level.get('location') or {}
        if not isinstance(item, dict) or item.get('id') != expected_item_gid:
            return False
        if (
            not isinstance(location, dict)
            or location.get('id') != expected_location_gid
        ):
            return False
        for quantity in level.get('quantities') or []:
            if not isinstance(quantity, dict):
                return False
            if quantity.get('name') == 'available':
                try:
                    return int(quantity.get('quantity')) == 0
                except (TypeError, ValueError):
                    return False
        return False

    @api.model
    def _classify_direct_activate(self, result):
        result = result or {}
        if result.get('outcome') == 'uncertain':
            return {
                'observed_outcome': 'uncertain',
                'error_class': result.get('error_class', ERROR_CLASS_TEMPORARY),
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': 'Transport-level uncertainty during '
                            'inventoryActivate.',
                'evidence': result.get('evidence') or {},
            }
        user_errors = result.get('user_errors') or []
        level = result.get('inventory_level')
        evidence = result.get('evidence') or {}
        # Classification by payload shape only -- inventoryActivate's
        # userErrors carry no structured code (DEC-037 §4 row 2). Never
        # matched on UserError.message text.
        if not user_errors:
            if not self._is_valid_activate_success(
                level, result.get('requested_item_gid'),
                result.get('requested_location_gid'),
            ):
                return {
                    'observed_outcome': 'uncertain',
                    'error_class': ERROR_CLASS_DATA_SHAPE,
                    'manual_review_subreason': False,
                    'action': 'reconcile',
                    'message': 'inventoryActivate returned an empty '
                                'userErrors list but the success payload '
                                'is missing, mismatched, or incomplete; '
                                'reconciling before trusting this as '
                                'applied.',
                    'evidence': evidence,
                }
            return {
                'observed_outcome': 'succeeded',
                'error_class': False,
                'manual_review_subreason': False,
                'action': 'succeed',
                'message': 'inventoryActivate applied.',
                'evidence': evidence,
            }
        if user_errors and level is None:
            return {
                'observed_outcome': 'failed_clean',
                'error_class': ERROR_CLASS_VALIDATION,
                'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
                'action': 'block_manual_review',
                'message': 'Shopify rejected the inventoryActivate '
                            'request.',
                'evidence': evidence,
            }
        return {
            'observed_outcome': 'uncertain',
            'error_class': ERROR_CLASS_DATA_SHAPE,
            'manual_review_subreason': False,
            'action': 'reconcile',
            'message': 'Ambiguous inventoryActivate response shape '
                        '(userErrors alongside a non-null level).',
            'evidence': evidence,
        }

    @api.model
    def _reconcile_activate(self, attempt):
        store = attempt.store_id
        binding = self.env[
            'shopify.connector.inventory.level.binding'
        ].search([('id', '=', attempt.job_id.res_id)], limit=1)
        read = self._read_shopify_inventory_pair(store, binding)
        if read['store_identity'] != attempt.expected_store_identity:
            return {
                'verdict': 'not_applied',
                'observed_store_identity': read['store_identity'] or '',
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_STORE_IDENTITY,
                'manual_review_subreason': SUBREASON_STORE_IDENTITY,
                'message': 'Reconciliation observed a different store '
                            'identity.',
                'evidence': {},
            }
        if not read['level_exists']:
            return {
                'verdict': 'not_applied',
                'observed_store_identity': read['store_identity'],
                'action': 'domain_callback',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'No inventory level exists yet for this pair.',
                'evidence': {},
            }
        if read['available'] == 0:
            return {
                'verdict': 'applied',
                'observed_store_identity': read['store_identity'],
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Activation confirmed at the accepted zero '
                            'baseline.',
                'evidence': {'available': read['available']},
            }
        return {
            'verdict': 'inconclusive',
            'observed_store_identity': read['store_identity'] or '',
            'action': None,
            'error_class': None,
            'manual_review_subreason': None,
            'message': 'Unexplained nonzero level after activation; '
                        'never auto-corrected.',
            'evidence': {'available': read['available']},
        }

    @api.model
    def _apply_consequence_activate(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        binding = self._lock_binding_for_pair(job)
        if phase == 'reconciliation' and consequence['action'] == 'domain_callback':
            self._handoff_supersede(
                job, binding, 'reconciliation_not_applied_replacement',
                JOB_TYPE_ACTIVATE,
            )
            return
        if consequence['action'] == 'succeed':
            binding.sudo().write({
                'shopify_gid': binding.shopify_gid or (
                    '%s:%s' % (
                        binding.shopify_inventory_item_gid,
                        binding.location_mapping_id.shopify_gid,
                    )
                ),
                'last_pushed_available': 0.0,
                'last_pushed_at': fields.Datetime.now(),
            })
            self._handoff_succeed_to_fresh_orchestration(job, binding)

    # ------------------------------------------------------------------
    # Shared reconciliation-job handler (one job_type, dispatches on the
    # attempt's own mutation_domain -- mirrors the core selftest shape).
    # ------------------------------------------------------------------

    @api.model
    def _handle_inventory_mutation_reconcile(self, job):
        Dispatch = self.env['shopify.connector.job.dispatch']
        attempt = job.mutation_attempt_id
        if not attempt:
            job._transition_failed_final(
                'unknown_system_error',
                'The reconciliation job has no mutation-attempt link.',
            )
            return
        original = attempt.job_id
        if attempt.observed_outcome == 'pending':
            Dispatch._block_original_job(
                original, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE_RISK,
                'Pending attempt reached reconciliation without recovery.',
            )
            Dispatch._complete_reconciliation_job(
                job, 'Pending reconciliation attempt was refused.',
            )
            return
        if attempt.effective_disposition() != 'unresolved':
            Dispatch._complete_reconciliation_job(
                job, 'Mutation attempt was already resolved.',
            )
            return
        try:
            strategy = Dispatch._validated_mutation_strategy(
                attempt.mutation_domain
            )
        except ValidationError:
            Dispatch._block_original_job(
                original, ERROR_CLASS_NO_STRATEGY, SUBREASON_NO_STRATEGY,
                'No valid reconciliation strategy is registered.',
            )
            Dispatch._complete_reconciliation_job(
                job, 'Missing strategy was routed to the original job.',
            )
            return
        try:
            result = strategy['reconcile'](attempt)
            normalized = Dispatch._validate_reconciliation_result(result)
        except Exception:
            Dispatch._block_original_job(
                original, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE_RISK,
                'The reconciliation result was malformed; no resend '
                'occurred.',
            )
            Dispatch._complete_reconciliation_job(
                job, 'Malformed read result was routed to the original job.',
            )
            return
        if normalized['observed_store_identity'] != attempt.expected_store_identity:
            Dispatch._block_original_job(
                original, ERROR_CLASS_STORE_IDENTITY, SUBREASON_STORE_IDENTITY,
                'Reconciliation observed a different Shopify store '
                'identity.',
            )
            Dispatch._complete_reconciliation_job(
                job, 'Store-identity mismatch was routed without a '
                     'verdict.',
            )
            return
        if normalized['verdict'] == 'inconclusive':
            count = attempt._record_inconclusive_reconciliation(
                normalized['evidence']
            )
            if count >= INCONCLUSIVE_RECONCILIATION_CAP:
                Dispatch._block_original_job(
                    original, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE_RISK,
                    'Reconciliation remained inconclusive at the safety '
                    'cap.',
                )
                Dispatch._complete_reconciliation_job(
                    job, 'Inconclusive reconciliation reached its safety '
                         'cap.',
                )
            else:
                job._transition_retry_waiting(
                    fields.Datetime.now() + timedelta(minutes=5),
                    job.retry_count + 1,
                    ERROR_CLASS_TEMPORARY,
                    normalized['message'],
                )
            return
        disposition = (
            'applied' if normalized['verdict'] == 'applied' else 'not_applied'
        )
        try:
            with self.env.cr.savepoint():
                attempt._record_reconciliation_result(
                    disposition, normalized['evidence'],
                )
                Dispatch._apply_validated_consequence(
                    original, attempt, 'reconciliation',
                    normalized['consequence'], strategy,
                    reconciliation_job=job,
                )
                Dispatch._complete_reconciliation_job(
                    job, 'Read-only mutation reconciliation completed.',
                )
        except Exception as exc:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'Atomic reconciliation consequence failed; read retry '
                'required.',
                type(exc).__name__,
            ) from exc

    # ------------------------------------------------------------------
    # Review-release private helper (delegated to by the binding's
    # public action_recheck_inventory_pair -- DEC-037 §5.5).
    # ------------------------------------------------------------------

    @api.model
    def _recheck_inventory_pair(self, binding, reason):
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_reviewer'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                "Only a Shopify Connector Reviewer or Administrator may "
                "release a blocked inventory pair."
            )
        if not isinstance(reason, str) or not reason.strip():
            raise UserError("A non-empty reason is required.")

        locked_binding = binding.try_lock_for_update()
        if not locked_binding:
            raise UserError(
                "This inventory pair is currently held by another "
                "operation; try again shortly."
            )
        locked_binding.invalidate_recordset()

        Job = self.env['shopify.connector.job']
        blocked = Job.search([
            ('res_model', '=', 'shopify.connector.inventory.level.binding'),
            ('res_id', '=', locked_binding.id),
            ('job_type', 'in', INVENTORY_JOB_TYPES),
            ('state', '=', 'blocked_manual_review'),
        ])
        if len(blocked) != 1:
            raise UserError(
                "Exactly one active blocked inventory job is required for "
                "this pair (found %d)." % len(blocked)
            )
        blocked_job = blocked.try_lock_for_update()
        if not blocked_job:
            raise UserError(
                "The blocked job is currently held by another operation; "
                "try again shortly."
            )
        blocked_job.invalidate_recordset()

        attempt = blocked_job.mutation_attempt_id
        eligible = False
        if attempt and attempt.observed_outcome == 'failed_clean' and (
            attempt.effective_disposition() == 'not_applied'
        ):
            subreason = blocked_job.manual_review_subreason
            if subreason == SUBREASON_LOCATION_MISSING:
                eligible = True
            elif subreason == SUBREASON_BINDING_CONFLICT:
                if blocked_job.error_class == ERROR_CLASS_CONCURRENCY:
                    eligible = (
                        blocked_job.cas_retry_ordinal == MAX_CAS_RETRY_ORDINAL
                    )
                elif blocked_job.error_class == ERROR_CLASS_VALIDATION:
                    eligible = True

        if not eligible:
            raise UserError(
                "This blocked job's outcome is not one of the cases "
                "eligible for release via action_recheck_inventory_pair. "
                "Uncertain, duplicate-risk, idempotency-contract, "
                "unresolved-reconciliation, store-identity-mismatch, and "
                "unexplained-drift/nonzero-post-activation cases require "
                "the Stage 0 Administrator-only manual resolution path "
                "instead."
            )

        safe_reason = redact(reason.strip())[:500]
        new_job = self._handoff_supersede(
            blocked_job, locked_binding, 'manual_review_release',
            JOB_TYPE_PUSH_SYNC,
        )
        _logger.info(
            'Inventory pair review released by actor_uid=%s: old_job=%s '
            'new_job=%s reason=%s',
            self.env.uid, blocked_job.id, new_job.id, safe_reason,
        )
        return True
