import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import (
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
)
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

# The ONLY job sources a location sync may ever be admitted under (Wave 5).
# `scheduled_sync` is the existing scheduled path; `manual_sync` is an
# operator pressing Refresh on a connected store; `setup_readiness_check` is
# the pre-activation guided-setup path, and is one of core's own two
# deliberately store-state-ungated sources. Every one of them is still gated
# on `inventory_domain_enabled` at start time, and nothing outside
# `action_refresh_shopify_locations` chooses between them.
LOCATION_SYNC_JOB_SOURCES = (
    'scheduled_sync', 'manual_sync', 'setup_readiness_check',
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
# The DB unique index enforcing the operation-scope serialization. A
# violated `models.Constraint` surfaces on flush as a raw psycopg2
# `IntegrityError` whose message carries this index name -- never the
# friendly `models.Constraint` message above (Odoo only substitutes the
# friendly text at the HTTP boundary, not inside an inline savepoint
# flush). Both forms are matched below so coalescing works in-process.
OPERATION_SCOPE_CONSTRAINT_NAME = (
    'shopify_connector_job_store_operation_scope_key_uniq'
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


def _strict_shopify_int(value):
    """Strict Shopify-integer validator (PR #182 comment 5028910116 item
    4): accepts only a genuine, non-bool Python `int` -- never coerces a
    `bool`, a meaningful float, a numeric string, `None`, or any other
    shape. Raises `ValueError` for anything else, for the caller to
    translate into its own fail-closed disposition. `int(...)` is never
    used as a permissive validator anywhere in this module."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError('Not a strict Shopify integer: %r' % (value,))
    return value


def _validate_structured_user_errors(user_errors, code_required):
    """Strictly validate and sanitize a Shopify `userErrors` list into
    the frozen structured evidence shape `[{code, field}]` (PR #182
    comment 5029906989 item 7) -- replaces the free-form
    `user_error_codes` list entirely. Returns `(sanitized_list, True)`
    when every entry is well-formed, else `(None, False)` -- never
    raises, and never persists message text (`message` is read from the
    transport response but is never copied into the returned sanitized
    entries or any evidence dict).

    `code_required=True` (`inventorySetQuantities`) additionally
    requires a non-empty string `code` on every entry.
    `code_required=False` (`inventoryActivate`) only validates the
    `field` shape -- the 2026-07 schema exposes no structured code for
    that mutation's userErrors, so classification for it stays
    payload-shape-only, never message-text-routed."""
    if not isinstance(user_errors, list):
        return None, False
    sanitized = []
    for entry in user_errors:
        if not isinstance(entry, dict):
            return None, False
        field = entry.get('field')
        if field is None:
            field = []
        elif not (
            isinstance(field, list)
            and all(isinstance(part, str) for part in field)
        ):
            return None, False
        if code_required:
            code = entry.get('code')
            if not isinstance(code, str) or not code:
                return None, False
            sanitized.append({'code': code, 'field': field})
        else:
            sanitized.append({'field': field})
    return sanitized, True


class InventoryPreC2FailClosedError(Exception):
    """Domain-owned pre-C2 fail-closed signal (PR #182 comment
    5028910116 item 3).

    Raised by `_fail_closed_pre_c2` -- never writes to the job and never
    commits (LL-005: a `TransactionCase` must never directly execute a
    production commit path). Carries the exact blocked disposition this
    domain requires; the disposition is written and committed
    exclusively by
    `ShopifyConnectorJobDispatchInventoryExtension._recover_pre_c2_failure`
    below, an inherited dispatcher recovery seam that runs only after
    core's own rollback/reset has already occurred -- mirroring the
    cursor-boundary discipline core's own recovery methods already use.
    """

    def __init__(self, error_class, subreason, message):
        super().__init__(message)
        self.error_class = error_class
        self.subreason = subreason
        self.message = message


class InventoryActivationSupersededError(Exception):
    """Domain-owned pre-C2 signal (PR #182 comment 5029906989 item 3):
    raised by `_prepare_preconditions_activate` when its fresh pre-C2
    read finds a valid Shopify InventoryLevel already exists for this
    pair -- an activation mutation is no longer necessary or safe to
    send (it would either fail or silently reset a level another actor
    already established).

    Never writes to the job and never commits (LL-005), exactly like
    `InventoryPreC2FailClosedError`: the skip-and-handoff disposition is
    applied exclusively by
    `ShopifyConnectorJobDispatchInventoryExtension._recover_pre_c2_failure`
    below, after core's own rollback/reset has already occurred.
    """

    def __init__(self, observed_level_gid):
        super().__init__(
            'A valid Shopify InventoryLevel already exists for this pair; '
            'no activation mutation may be sent.'
        )
        self.observed_level_gid = observed_level_gid


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
    def _governed_scope_catalog(self):
        catalog = super()._governed_scope_catalog()
        if not any(entry['scope'] == 'write_inventory' for entry in catalog):
            catalog.append({
                'scope': 'write_inventory',
                'reason': (
                    'so reviewed Odoo stock changes can be sent to mapped '
                    'Shopify locations'
                ),
            })
        return catalog

    @api.model
    def _check_mapped_location(self, store):
        """Real mapped-location + write_inventory-scope readiness (D-013-5).

        Pure read-only evaluation (no `write`/`create`/`unlink`/`sudo`)
        -- the repo-wide AST guard on every `_check_*` method requires
        this. When the inventory domain is disabled, stays not-applicable
        pass (unchanged core behavior via the CORE-R1 baseline). When
        enabled: requires a successful current location discovery, requires
        every active cached Shopify location to have an explicit mapping, and
        requires `write_inventory` to be present in the store's granted scopes
        snapshot.  The setup step and readiness therefore enforce one rule.
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
                not_applicable=True,
            )
        refresh = self.env[
            'shopify.connector.inventory.service'
        ].location_refresh_state(store)
        if refresh.get('state') != 'succeeded':
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'Inventory syncing is on, but the current Shopify location '
                'list has not been loaded successfully yet.',
            )
        active_locations = self.env['shopify.connector.location'].search([
            ('store_id', '=', store.id),
            ('shopify_location_active', '=', True),
        ])
        if not active_locations:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'Shopify returned no active inventory locations for this '
                'store.',
            )
        active_gids = active_locations.mapped('shopify_location_gid')
        mapped_gids = set(self.env[
            'shopify.connector.location.mapping'
        ].search([
            ('store_id', '=', store.id),
            ('shopify_gid', 'in', active_gids),
        ]).mapped('shopify_gid'))
        missing_count = len(set(active_gids) - mapped_gids)
        if missing_count:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                '%d active Shopify location(s) still need an explicit Odoo '
                'location mapping.' % missing_count,
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
            'Every active Shopify location is mapped and write_inventory is '
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

    @api.model
    def _recover_pre_c2_failure(self, job_id, token, exc):
        """Domain-specific pre-C2 recovery seam (PR #182 comment
        5028910116 item 3; extended by comment 5029906989 item 3): for
        `InventoryPreC2FailClosedError` and `InventoryActivationSupersededError`
        only, allows core's own rollback/reset to occur first, then
        applies this domain's own disposition inside the fresh recovery
        transaction that follows -- never a domain-side commit inside
        `prepare_preconditions` itself (LL-005). Every other exception
        (a genuine transport/precondition failure, a core-recognized
        concurrency race, etc.) delegates unchanged to `super()`, which
        keeps its existing generic bounded-retry behaviour.
        """
        if isinstance(exc, InventoryActivationSupersededError):
            self._recover_activation_superseded(job_id, token, exc)
            return
        if not isinstance(exc, InventoryPreC2FailClosedError):
            return super()._recover_pre_c2_failure(job_id, token, exc)
        self.env.cr.rollback()
        self.env.transaction.reset()
        job = self.env['shopify.connector.job'].browse(
            job_id
        ).try_lock_for_update()
        if not job:
            self.env.cr.commit()
            return
        job.invalidate_recordset()
        attempt_exists = bool(
            self.env['shopify.connector.mutation.attempt'].search_count([
                ('job_id', '=', job_id),
            ])
        )
        if (
            not attempt_exists
            and job.current_attempt_token == token
            and job.state == 'running'
        ):
            self._block_original_job(
                job, exc.error_class, exc.subreason, exc.message,
            )
        self.env.cr.commit()

    @api.model
    def _recover_activation_superseded(self, job_id, token, exc):
        """Skip an unnecessary `inventory_activate` job and atomically
        hand off to a fresh `inventory_push_sync` (PR #182 comment
        5029906989 item 3), entirely inside the fresh recovery
        transaction that follows core's own rollback/reset -- never a
        domain-side commit inside `prepare_preconditions` itself
        (LL-005). No mutation attempt row exists (C2 was never reached)
        and no Shopify transport occurs. Reacquires both the job and the
        binding under locks; pair serialization is preserved by
        terminalizing this job (state='skipped') and flushing before the
        successor's insert, exactly mirroring every other handoff in
        this module.
        """
        self.env.cr.rollback()
        self.env.transaction.reset()
        job = self.env['shopify.connector.job'].browse(
            job_id
        ).try_lock_for_update()
        if not job:
            self.env.cr.commit()
            return
        job.invalidate_recordset()
        attempt_exists = bool(
            self.env['shopify.connector.mutation.attempt'].search_count([
                ('job_id', '=', job_id),
            ])
        )
        if not (
            not attempt_exists
            and job.current_attempt_token == token
            and job.state == 'running'
        ):
            self.env.cr.commit()
            return
        Binding = self.env['shopify.connector.inventory.level.binding']
        binding = Binding.browse(job.res_id).exists()
        locked_binding = binding.try_lock_for_update() if binding else binding
        if not locked_binding:
            # No stable binding to hand off to this pass -- leave the
            # job at its post-rollback 'running' state (unchanged) and
            # let the ordinary scheduler re-dispatch it, exactly like
            # the sibling `InventoryPreC2FailClosedError` seam's own
            # "job not lockable" branch above.
            self.env.cr.commit()
            return
        locked_binding.invalidate_recordset()
        Service = self.env['shopify.connector.inventory.service']
        if not Service._binding_scope_compatible(
            locked_binding, expected_store=job.store_id,
        ):
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'The activation recovery binding is outside the job store '
                'or company scope; no identity evidence or successor job '
                'was recorded.',
            )
            self.env.cr.commit()
            return
        if exc.observed_level_gid and not locked_binding.shopify_gid:
            locked_binding.sudo().write({'shopify_gid': exc.observed_level_gid})
        job.sudo().write({'state': 'skipped', 'finished_at': fields.Datetime.now()})
        job.flush_recordset(['state', 'operation_scope_key'])
        new_job = Service._create_inventory_job(
            job.store_id, job.job_source, JOB_TYPE_PUSH_SYNC, locked_binding,
            trigger_origin=job.trigger_origin or False,
            allow_ineligible=True,
        )
        if not new_job:
            job._log_transition(
                'state_change',
                'A valid Shopify InventoryLevel already exists; skipped '
                'this unnecessary activation, but the fresh push-sync '
                'successor was suppressed because the pair became '
                'ineligible. predecessor_job_id=%d.' % (job.id,),
                from_state='running', to_state='skipped',
            )
            self.env.cr.commit()
            return
        job._log_transition(
            'state_change',
            'A valid Shopify InventoryLevel already exists; skipped this '
            'unnecessary activation and enqueued a fresh '
            'inventory_push_sync; predecessor_job_id=%d '
            'successor_job_id=%d.' % (job.id, new_job.id),
            from_state='running', to_state='skipped',
        )
        self.env.cr.commit()

    @api.model
    def _ensure_reconciliation_job(self, original_job, attempt, strategy=None):
        """Exact frozen reconciliation identity for the two inventory
        mutation domains only (PR #182 comment 5028910116 item 6):
        `reconcile:{store}:{mutation_domain}:{attempt_token}` -- never
        core's own bare `reconcile:{attempt_token}` identity, which
        would no longer reveal which mutation domain produced it now
        that both domains share one `inventory_mutation_reconcile`
        `job_type`. Every non-inventory domain delegates unchanged to
        `super()`. The attempt-link uniqueness, one-reconciliation-job-
        per-attempt idempotency, `job_source`, lifecycle-conversion, and
        disconnecting-state recovery semantics are otherwise identical
        to core's own implementation -- only the `payload_hash` fed into
        the durable identity differs for these two domains. No inventory
        pair scope is ever held (`res_model`/`res_id`/
        `shopify_target_gid` are never set here, exactly as core's own
        version never sets them).
        """
        if attempt.mutation_domain not in (
            MUTATION_DOMAIN_ACTIVATE, MUTATION_DOMAIN_SET_QUANTITIES,
        ):
            return super()._ensure_reconciliation_job(
                original_job, attempt, strategy,
            )
        try:
            strategy = strategy or self._validated_mutation_strategy(
                attempt.mutation_domain
            )
        except ValidationError:
            self._block_original_job(
                original_job,
                ERROR_CLASS_NO_STRATEGY, SUBREASON_NO_STRATEGY,
                'No valid reconciliation strategy exists for this attempt.',
            )
            return self.env['shopify.connector.job']
        locked_attempt = attempt.try_lock_for_update()
        if not locked_attempt:
            return self.env['shopify.connector.job']
        # Every subsequent identity/domain/token/generation/disposition
        # read uses `locked_attempt`, never the pre-lock `attempt`
        # reference (PR #182 comment 5029906989 item 1): the lock exists
        # precisely to prevent acting on a value a concurrent writer may
        # have already changed.
        Job = self.env['shopify.connector.job']
        existing = Job.search([
            ('mutation_attempt_id', '=', locked_attempt.id),
        ], limit=1)
        if existing:
            if (
                existing.state in TERMINAL_JOB_STATES
                and locked_attempt.effective_disposition() == 'unresolved'
                and original_job.state != 'blocked_manual_review'
            ):
                # `duplicate_risk` is a valid core registry value but is
                # outside Task 013's frozen nine-value `error_class`
                # vocabulary (PR #182 comment 5029906989 item 1): the
                # error_class position always uses
                # `data_shape_schema_mismatch`; `duplicate_risk` is only
                # ever valid in the subreason position.
                self._block_original_job(
                    original_job,
                    ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE_RISK,
                    'The reconciliation job is terminal while unresolved.',
                )
            return existing
        return Job.sudo().create({
            'store_id': original_job.store_id.id,
            'job_source': 'reconciliation',
            'job_type': strategy['reconciliation_job_type'],
            'state': 'queued',
            'payload_hash': 'reconcile:%s:%s:%s' % (
                original_job.store_id.id, locked_attempt.mutation_domain,
                locked_attempt.attempt_token,
            ),
            'mutation_attempt_id': locked_attempt.id,
            'expected_connection_generation':
                locked_attempt.expected_connection_generation,
        })


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
        self, store, job_source, job_type, binding, trigger_origin=False,
        allow_ineligible=False,
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

        This is the ONLY inventory job creation surface, and it accepts
        no `cas_retry_ordinal` parameter at all (PR #182 comment
        5029906989 item 6): every job created here is ordinal 0 (the
        field's own model-level default) -- there is no argument or
        context path through this method for a nonzero value. The sole
        surface that can ever produce a nonzero ordinal is
        `_create_cas_successor_job` below.

        ``allow_ineligible`` is reserved for callers that have already
        terminalized a predecessor in the same transaction. It suppresses a
        successor when parent status or scope changed in the final TOCTOU
        window; ordinary admission leaves it false so scope errors remain
        strict before business intent is created.
        """
        Job = self.env['shopify.connector.job']
        binding = binding.sudo().exists()
        # A deleted/expired binding is an idempotent no-successor outcome
        # after a predecessor has already been terminalized. Do not raise
        # here: the caller must retain that terminal evidence and commit it.
        if len(binding) != 1:
            return Job
        if binding.store_id != store:
            if allow_ineligible:
                return Job
            raise UserError(
                'The inventory job store must match the level binding store.'
            )
        # Store/company topology is a pre-intent contract. Unlike an
        # active/stale transition, a scope mismatch is not a benign TOCTOU
        # race: refuse it before a job identity or business intent exists.
        if not self._binding_scope_compatible(binding, expected_store=store):
            if allow_ineligible:
                return Job
            raise UserError(
                'Inventory work cannot be admitted outside the owning '
                'store/company scope.'
            )
        if not self._binding_operationally_eligible(binding):
            # Parent status/push-enable changes can race the final enqueue
            # check. Return an empty job recordset instead of raising after
            # a caller has terminalized its predecessor.
            return Job
        pair_key = pair_scope_key(
            store.id,
            binding.shopify_inventory_item_gid,
            binding.location_mapping_id.shopify_gid,
        )
        return self.env['shopify.connector.job.enqueue'].enqueue(
            store, job_source, job_type,
            payload_hash=uuid.uuid4().hex,
            res_model='shopify.connector.inventory.level.binding',
            res_id=binding.id,
            shopify_target_gid=pair_key,
            trigger_origin=trigger_origin or False,
        )

    @api.model
    def _binding_scope_compatible(self, binding, expected_store=None):
        """Return whether the pair's immutable store/company scope is valid.

        This deliberately excludes operational status and push-enable state;
        callers use it to distinguish a hard pre-intent scope rejection from
        an ineligible parent that may have changed after a terminal handoff.
        """
        binding = binding.sudo().exists()
        if len(binding) != 1:
            return False
        store = binding.store_id
        variant_binding = binding.product_variant_binding_id
        mapping = binding.location_mapping_id
        if not store or not store.company_id or not variant_binding or not mapping:
            return False
        if expected_store is not None and store != expected_store:
            return False
        if (
            variant_binding.store_id != store
            or mapping.store_id != store
            or binding.company_id != store.company_id
        ):
            return False
        product = variant_binding.product_variant_id
        location = mapping.odoo_location_id
        if not product or not location:
            return False
        if (
            product.company_id and product.company_id != store.company_id
        ) or (
            location.company_id and location.company_id != store.company_id
        ):
            return False
        return True

    @api.model
    def _create_cas_successor_job(
        self, locked_predecessor, binding, allow_ineligible=False,
    ):
        """The sole creation surface for a nonzero `cas_retry_ordinal`
        (PR #182 comment 5029906989 item 6). Requires an already
        row-locked `inventory_set_quantities` predecessor (the caller
        must have locked it, exactly like `_handoff_supersede` below
        does before calling this); derives the successor ordinal
        exclusively from that locked predecessor's own recorded
        ordinal, exactly predecessor + 1 -- never a caller-supplied
        value, and never invocable for ordinary (non-CAS) admission.
        Only ordinal 1, 2, or 3 can ever result; the bounded ceiling is
        enforced here, not by the caller. The ordinal is applied through
        one narrow, same-transaction `sudo()` write immediately after
        enqueueing via the ordinal-less `_create_inventory_job` -- no
        second transaction, no parallel enqueue mechanism (item 13).
        """
        if (
            locked_predecessor.job_type != JOB_TYPE_SET_QUANTITIES
            or locked_predecessor.cas_retry_ordinal >= MAX_CAS_RETRY_ORDINAL
        ):
            raise ValidationError(
                'A CAS replacement may only be created for an '
                'inventory_set_quantities job below the bounded ordinal '
                'ceiling.'
            )
        # This helper is the sole nonzero-ordinal creation surface, so it
        # must independently re-verify the immutable stale-CAS evidence
        # itself rather than trust the caller (PR #182 comment 5030514895
        # item 3): exactly one immutable mutation attempt, a
        # `failed_clean` outcome with `not_applied` effective
        # disposition, and an exact structured `user_errors` entry with
        # `code == 'CHANGE_FROM_QUANTITY_STALE'` -- never a substring or
        # generic-container membership test.
        # `mutation_attempt_id` is a reconciliation-job-owned field (it
        # points a reconciliation job at the attempt it reconciles); an
        # ordinary mutation job's own attempt is never linked through
        # that field (core's own `_check_reconciliation_attempt_link`
        # constraint forbids it) and must instead be found by the
        # attempt's forward `job_id` reference, exactly mirroring
        # core's own `_has_mutation_attempt_evidence` fallback. At most
        # one attempt can ever exist per job (enforced at C2 creation
        # time), so this search is inherently "exactly one."
        attempt = self.env['shopify.connector.mutation.attempt'].sudo().search(
            [('job_id', '=', locked_predecessor.id)], limit=1,
        )
        if not attempt or attempt.observed_outcome != 'failed_clean' or (
            attempt.effective_disposition() != 'not_applied'
        ):
            raise ValidationError(
                'A CAS replacement requires the locked predecessor to '
                'carry exactly one immutable failed_clean/not_applied '
                'mutation attempt.'
            )
        direct_evidence = (
            (attempt.remote_evidence_refs or {}).get('direct') or {}
        )
        structured_errors = direct_evidence.get('user_errors')
        if not isinstance(structured_errors, list) or not structured_errors:
            raise ValidationError(
                'A CAS replacement requires the locked predecessor\'s '
                'attempt to carry a non-empty structured user_errors '
                'list.'
            )
        if not all(isinstance(entry, dict) for entry in structured_errors):
            raise ValidationError(
                'A CAS replacement requires every structured user_errors '
                'entry on the locked predecessor\'s attempt to be a '
                'dict.'
            )
        has_exact_stale_code = any(
            entry.get('code') == 'CHANGE_FROM_QUANTITY_STALE'
            for entry in structured_errors
        )
        if not has_exact_stale_code:
            raise ValidationError(
                'A CAS replacement requires the locked predecessor\'s '
                'attempt to carry an exact CHANGE_FROM_QUANTITY_STALE '
                'structured user-error entry.'
            )
        cas_retry_ordinal = locked_predecessor.cas_retry_ordinal + 1
        new_job = self._create_inventory_job(
            locked_predecessor.store_id, locked_predecessor.job_source,
            JOB_TYPE_SET_QUANTITIES, binding,
            trigger_origin=locked_predecessor.trigger_origin or False,
            allow_ineligible=allow_ineligible,
        )
        if not new_job:
            return self.env['shopify.connector.job']
        new_job.sudo().write({'cas_retry_ordinal': cas_retry_ordinal})
        return new_job

    @api.model
    def _binding_operationally_eligible(self, binding):
        """Return whether a pair may enter any inventory work path.

        This is deliberately narrower than the existing review/stale gate:
        a level row is usable only while its own binding, its product-variant
        parent, and its mapped location parent are all active, the mapping is
        push-enabled, and every relation remains inside one store/company
        scope.  The helper is internal and reads through a narrow sudo so
        background jobs can validate parent state without granting users raw
        access to stock records.
        """
        binding = binding.sudo().exists()
        if len(binding) != 1:
            return False
        variant_binding = binding.product_variant_binding_id
        mapping = binding.location_mapping_id
        if not variant_binding or not mapping:
            return False
        if not self._binding_scope_compatible(binding):
            return False
        if (
            binding.status != 'active'
            or variant_binding.status != 'active'
            or mapping.status != 'active'
            or not mapping.push_enabled
        ):
            return False
        location = mapping.odoo_location_id
        if not location or location.usage != 'internal':
            return False
        if (
            not isinstance(binding.shopify_inventory_item_gid, str)
            or not binding.shopify_inventory_item_gid.strip()
            or not isinstance(mapping.shopify_gid, str)
            or not mapping.shopify_gid.strip()
        ):
            return False
        return True

    @api.model
    def _binding_push_admission_blocked(self, binding):
        """Preserve the existing review/stale freeze gate.

        `_binding_operationally_eligible` is the broader operational gate;
        this predicate remains separate so the established review/stale
        disposition is still enforced at every later handoff and replacement
        path without changing its audit semantics.
        """
        return binding.status in ('review', 'stale')

    @api.model
    def _existing_pair_scope_job(self, store, pair_key):
        """The non-terminal inventory job holding this pair's scope, if any.

        Two things this has to get right, both of which the previous
        inline version got wrong:

        **The field it queries.** `operation_scope_key` is not the pair
        key. It is the composite `store|res_model|res_id|target_gid`
        built by core's `_compute_operation_scope_key`, and the pair key
        is only its last segment. Comparing the two could never match, so
        the fast-path coalesce never fired and — worse — the
        re-verification after catching the constraint violation could
        never confirm the collision either, turning a benign concurrent
        admission into a raised error. The pair key IS `shopify_target_gid`
        verbatim (`_create_inventory_job` passes it as such), so that is
        what gets compared. `operation_scope_key != False` restricts the
        match to non-terminal jobs, using exactly the guarantee the unique
        constraint relies on: core clears the key on reaching a terminal
        state or being superseded.

        **When it reads.** `operation_scope_key` is a STORED COMPUTE, so a
        sibling created earlier in this same transaction has no value for
        it in PostgreSQL until the ORM flushes. Without the flush an
        unflushed sibling is invisible here and the caller falls through
        to the constraint. The constraint is still the atomic guard for
        the cross-worker window, which no flush can close.
        """
        Job = self.env['shopify.connector.job']
        Job.flush_model()
        return Job.sudo().search([
            ('store_id', '=', store.id),
            ('job_type', 'in', INVENTORY_JOB_TYPES),
            ('shopify_target_gid', '=', pair_key),
            ('operation_scope_key', '!=', False),
        ], limit=1)

    @api.model
    def _try_enqueue_push_sync(self, store, binding, job_source, trigger_origin=False):
        """Admit one `inventory_push_sync` job for `binding`, or coalesce.

        The sole `inventory_push_sync` admission point for every trigger
        surface (stock-move event, manual push, scheduled scan) --
        gating here on `_binding_operationally_eligible` plus the existing
        `_binding_push_admission_blocked` freeze gate covers all three at
        once; the direct
        orchestration dispatch and the CAS/reconciliation replacement
        paths each re-check the same gate independently since a binding
        can be flagged `review`/`stale` after this job was already
        admitted.

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
        if not self._binding_operationally_eligible(binding):
            _logger.info(
                'Inventory pair store_id=%s item=%s location=%s: '
                'push_sync admission refused while its level, variant, '
                'or location binding is inactive, disabled, or out of scope.',
                store.id,
                binding.shopify_inventory_item_gid,
                binding.location_mapping_id.shopify_gid,
            )
            return self.env['shopify.connector.job']
        if self._binding_push_admission_blocked(binding):
            _logger.info(
                'Inventory pair store_id=%s item=%s location=%s: '
                'push_sync admission refused while the binding is '
                'flagged %s.', store.id,
                binding.shopify_inventory_item_gid,
                binding.location_mapping_id.shopify_gid, binding.status,
            )
            return self.env['shopify.connector.job']
        pair_key = pair_scope_key(
            store.id,
            binding.shopify_inventory_item_gid,
            binding.location_mapping_id.shopify_gid,
        )
        def _existing_pair_job():
            return self._existing_pair_scope_job(store, pair_key)

        # Fast-path coalesce: a non-terminal inventory job already holding
        # this pair's operation_scope_key means "already in progress" -- the
        # caller's Odoo-side change is already reflected on the binding's
        # pending_target_available, so nothing is lost by admitting no new
        # job. The DB-level unique constraint below stays the atomic guard
        # for the narrow TOCTOU window where a concurrent worker inserts
        # between this read and the create.
        if _existing_pair_job():
            return self.env['shopify.connector.job']
        try:
            with self.env.cr.savepoint():
                return self._create_inventory_job(
                    store, job_source, JOB_TYPE_PUSH_SYNC, binding,
                    trigger_origin=trigger_origin,
                )
        except (ValidationError, IntegrityError) as exc:
            # A violated operation-scope constraint surfaces either as the
            # friendly ValidationError message (HTTP boundary) or, inside
            # this inline savepoint flush, as a raw psycopg2 IntegrityError
            # naming the unique index; match both. Every other error
            # (store-state, domain-disabled, company, invalid field,
            # illegal transition, security, unrelated constraint) still
            # propagates unchanged. Only re-treat it as benign coalescing
            # after independently confirming a real non-terminal job now
            # holds this exact pair scope.
            message = str(exc)
            if (
                OPERATION_SCOPE_CONSTRAINT_MESSAGE not in message
                and OPERATION_SCOPE_CONSTRAINT_NAME not in message
            ):
                raise
            if not _existing_pair_job():
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
        # Deriving the Odoo-side available quantity is an internal system
        # read: an authorized Connector Operator/Administrator triggers the
        # push, but computing `free_qty` walks stock.location/stock.quant,
        # which the Shopify-connector groups do not (and should not) grant
        # raw ACL for. Elevate exactly this quantity read via sudo (the
        # result is already written back through `binding.sudo()` below) so
        # the sanctioned trigger never demands a full Odoo Inventory role.
        free_qty = product.sudo().with_context(location=location.id).free_qty
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
        comment 5025765389 §21; commit removed per comment 5028910116
        item 3): raise `InventoryPreC2FailClosedError` only -- never
        writes to the job and never commits here (LL-005: a
        `TransactionCase` must never directly execute a production
        commit path, and this method is called directly by unit tests
        exercising `prepare_preconditions`).

        The domain's own `blocked_manual_review` disposition (instead of
        the generic `shopify_temporary_server_network` bounded retry
        core's `_recover_pre_c2_failure` would otherwise apply to *any*
        exception raised from `prepare_preconditions`) is written and
        committed exclusively by
        `ShopifyConnectorJobDispatchInventoryExtension._recover_pre_c2_failure`
        above, an inherited dispatcher recovery seam that only runs
        after core's own rollback/reset has already occurred. No
        mutation-attempt row is ever created (C2 is never reached), and
        no Shopify transport occurs -- `job_id` is accepted for call-
        site symmetry with that recovery seam but is not otherwise used
        here.
        """
        del job_id
        raise InventoryPreC2FailClosedError(error_class, subreason, message)

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
            ('status', '=', 'active'),
            ('product_variant_binding_id.status', '=', 'active'),
            ('location_mapping_id.status', '=', 'active'),
        ])
        for binding in bindings:
            if not self._binding_operationally_eligible(binding):
                continue
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
            ('status', '=', 'active'),
            ('product_variant_binding_id.status', '=', 'active'),
            ('location_mapping_id.status', '=', 'active'),
        ])
        enqueued = self.env['shopify.connector.job']
        for binding in bindings:
            if not self._binding_operationally_eligible(binding):
                continue
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

        # `review`/`stale` bindings must never enter orchestration (PR
        # #182 comment 5029906989 item 4/§10): a re-check at dispatch
        # time, independent of `_try_enqueue_push_sync`'s own admission-
        # time gate, since the binding may have been flagged after this
        # job was already created.
        if (
            binding.store_id != store
            or not self._binding_operationally_eligible(binding)
        ):
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'The inventory pair is not operationally eligible: its '
                'level binding, variant binding, or location mapping is '
                'inactive, disabled, or outside the owning store/company '
                'scope. No Shopify work was sent.',
            )
            return

        if self._binding_push_admission_blocked(binding):
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'This inventory pair is flagged %s; no automatic or '
                'manual push may proceed until it is reviewed.' % (
                    binding.status,
                ),
            )
            return

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
            read = self._read_shopify_inventory_pair(job, store, binding)
        except JobHandlerError:
            raise
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
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

        if not read['item_exists']:
            # A stale or recreated InventoryItem identity (PR #182
            # comment 5028910116 item 1): must never be treated as
            # "no InventoryLevel yet" and routed to activation. Fails
            # closed through the existing binding_conflict review route.
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'The Shopify inventory item no longer exists (a stale or '
                'recreated identity); manual review is required before '
                'any mutation may be enqueued.',
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
            # is required before any quantity can be set. DEC-037 §5.4
            # handoff A: acquire the pair's binding row lock (PR #182
            # comment 5028910116 item 12) before terminalizing this
            # orchestration job and creating the child -- the ambient
            # per-job transaction rolls the whole handoff back together
            # if child creation fails, so atomicity is preserved. This
            # orchestration job's own `operation_scope_key` (identical
            # across job types for the same pair -- it never encodes
            # job_type) must be cleared *before* the child job's insert,
            # or the two would collide on the DB unique constraint while
            # this job is still non-terminal. Terminalize first and
            # flush, exactly mirroring `_handoff_supersede`'s own
            # ordering, before creating the child.
            locked_binding = binding.try_lock_for_update()
            if not locked_binding:
                raise JobHandlerError(
                    ERROR_CLASS_TEMPORARY,
                    'The inventory pair is held by another worker or no '
                    'longer exists; retry later.',
                )
            locked_binding.invalidate_recordset()
            if not self._binding_operationally_eligible(locked_binding):
                job._transition_blocked_manual_review(
                    ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                    'The inventory pair became ineligible before its '
                    'activation handoff; no Shopify mutation may proceed.',
                )
                return
            if self._binding_push_admission_blocked(locked_binding):
                # Re-checked under the row lock (PR #182 comment
                # 5029906989 item 4): a concurrent writer may have
                # flagged this pair `review`/`stale` after the earlier
                # unlocked check above but before this handoff acquired
                # the lock -- never create a child against a stale
                # admission decision.
                job._transition_blocked_manual_review(
                    ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                    'This inventory pair is flagged %s; no automatic or '
                    'manual push may proceed until it is reviewed.' % (
                        locked_binding.status,
                    ),
                )
                return
            job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
            job.flush_recordset(['state', 'operation_scope_key'])
            new_job = self._create_inventory_job(
                store, job.job_source, JOB_TYPE_ACTIVATE, locked_binding,
                trigger_origin=job.trigger_origin or False,
                allow_ineligible=True,
            )
            if not new_job:
                job._log_transition(
                    'state_change',
                    'No Shopify inventory level exists yet; the '
                    'orchestration job was terminalized, but activation '
                    'was suppressed because the pair became ineligible. '
                    'predecessor_job_id=%d.' % (job.id,),
                    from_state='running', to_state='succeeded',
                )
                return
            job._log_transition(
                'state_change',
                'No Shopify inventory level exists yet; enqueued '
                'inventory_activate; predecessor_job_id=%d '
                'successor_job_id=%d.' % (job.id, new_job.id),
                from_state='running', to_state='succeeded',
            )
            return

        # Real InventoryLevel GID persistence *before* any no-op/drift/
        # child-admission decision (PR #182 comment 5029906989 item 4):
        # a no-op equality path below must never leave `shopify_gid`
        # empty forever, and a conflicting already-recorded GID must
        # fail closed here -- before any successor could be enqueued --
        # never a synthetic identity.
        observed_level_gid = read.get('inventory_level_gid')
        if (
            observed_level_gid and binding.shopify_gid
            and binding.shopify_gid != observed_level_gid
        ):
            job._transition_blocked_manual_review(
                ERROR_CLASS_DATA_SHAPE, SUBREASON_BINDING_CONFLICT,
                'Orchestration read observed an InventoryLevel GID that '
                'conflicts with the already-recorded value; manual '
                'review is required before any mutation may be '
                'enqueued.',
            )
            return
        if observed_level_gid and not binding.shopify_gid:
            binding.sudo().write({'shopify_gid': observed_level_gid})

        # Drift classification -- corrected three-way matrix (PR #182
        # comment 5025765389 item 14): Shopify already reflecting the
        # current Odoo target is never drift, regardless of whether it
        # also still equals last_pushed_available. Unexplained drift
        # exists only when Shopify differs from BOTH last-pushed and the
        # current target -- never a silent overwrite either way.
        has_prior_push = bool(binding.last_pushed_at)

        if shopify_available == target:
            # Verified no-op baseline (PR #182 comment 5029906989 item
            # 5): a fresh, identity-validated read proving Shopify
            # already equals the current Odoo target is recorded as the
            # accepted synchronized baseline for scheduling purposes --
            # never left with `last_pushed_at` unset, which would
            # otherwise cause the scheduled scan (item 5's
            # never-pushed-zero admission fix) to re-admit this exact
            # pair on every later scan indefinitely. No Shopify mutation
            # is sent and none is implied by recording this baseline.
            binding.sudo().write({
                'last_pushed_available': target,
                'last_pushed_at': fields.Datetime.now(),
            })
            job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
            job._log_transition(
                'state_change',
                'Shopify already matched the current Odoo target; no '
                'Shopify mutation was sent, no mutation attempt was '
                'created; the verified read was recorded as the '
                'synchronized baseline.',
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
        # target. DEC-037 §5.4 handoff A: acquire the pair's binding row
        # lock (PR #182 comment 5028910116 item 12) before terminalizing
        # this orchestration job and flushing first (same reasoning as
        # the activation branch above) so its own `operation_scope_key`
        # clears before the child's insert.
        locked_binding = binding.try_lock_for_update()
        if not locked_binding:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'The inventory pair is held by another worker or no '
                'longer exists; retry later.',
            )
        locked_binding.invalidate_recordset()
        if not self._binding_operationally_eligible(locked_binding):
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'The inventory pair became ineligible before its quantity '
                'handoff; no Shopify mutation may proceed.',
            )
            return
        if self._binding_push_admission_blocked(locked_binding):
            # Re-checked under the row lock (PR #182 comment 5029906989
            # item 4) -- see the identical reasoning in the activation
            # branch above.
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'This inventory pair is flagged %s; no automatic or '
                'manual push may proceed until it is reviewed.' % (
                    locked_binding.status,
                ),
            )
            return
        job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
        job.flush_recordset(['state', 'operation_scope_key'])
        new_job = self._create_inventory_job(
            store, job.job_source, JOB_TYPE_SET_QUANTITIES, locked_binding,
            trigger_origin=job.trigger_origin or False,
            allow_ineligible=True,
        )
        if not new_job:
            job._log_transition(
                'state_change',
                'The orchestration job was terminalized, but the quantity '
                'push was suppressed because the pair became ineligible. '
                'predecessor_job_id=%d.' % (job.id,),
                from_state='running', to_state='succeeded',
            )
            return
        job._log_transition(
            'state_change',
            'Enqueued inventory_set_quantities toward the current '
            'target; predecessor_job_id=%d successor_job_id=%d.' % (
                job.id, new_job.id,
            ),
            from_state='running', to_state='succeeded',
        )

    @api.model
    def _read_shopify_inventory_pair(self, job, store, binding):
        """One narrow Shopify read for a pair, corrected to the official
        Shopify Admin GraphQL 2026-07 request shape (PR #182 comment
        5025765389 item 1): the 2026-07 root `inventoryLevel` field no
        longer accepts `inventoryItemId`/`locationId` -- this always
        reads through `inventoryItem(id:) { inventoryLevel(locationId:)
        { ... } }` instead. Uses the job-bound business-read seam.

        Returns a structured dict distinguishing every case the review
        requires: `item_exists` (False only when the inventory item
        itself does not exist at Shopify), `tracked` (None only when
        `item_exists` is False), `level_exists` (whether an
        InventoryLevel row exists for this pair), `inventory_level_gid`
        (the real Shopify InventoryLevel GID, non-`None` only when
        `level_exists`), `available` (a strict Python `int`, non-`None`
        only when `level_exists`), and `updated_at`. Any
        malformed/partial/ambiguous response shape raises
        `JobHandlerError(data_shape_schema_mismatch, ...)` -- fails
        closed rather than silently defaulting a missing item to
        `tracked=True`, a malformed response to "no level", or coercing
        a non-integer `available` value (PR #182 comment 5028910116
        items 2/4).
        """
        client = self.env['shopify.connector.api.client']
        query = (
            'query InventoryPairRead($itemId: ID!, $locationId: ID!) { '
            'inventoryItem(id: $itemId) { id tracked '
            'inventoryLevel(locationId: $locationId) { id '
            'item { id } location { id } '
            'quantities(names: ["available"]) { name quantity updatedAt '
            '} } } '
            'shop { myshopifyDomain } }'
        )
        requested_item_gid = binding.shopify_inventory_item_gid
        requested_location_gid = binding.location_mapping_id.shopify_gid
        variables = {
            'itemId': requested_item_gid,
            'locationId': requested_location_gid,
        }
        with client.execute_business_read(
            job, store, query, variables, purpose='inventory',
        ) as result:
            return self._inventory_pair_read_result(
                result, requested_item_gid, requested_location_gid,
            )

    @api.model
    def _inventory_pair_read_result(
        self, result, requested_item_gid, requested_location_gid,
    ):
        """Validate and normalize one pair read while its lease is held."""
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
                'inventory_level_gid': None,
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
        # The returned InventoryItem identity must equal the requested
        # one (PR #182 comment 5029906989 item 4) -- never trusted by
        # position alone.
        if item.get('id') != requested_item_gid:
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Shopify returned a different InventoryItem identity '
                'than requested.',
            )
        tracked = item['tracked']
        level = item.get('inventoryLevel')
        if level is None:
            return {
                'store_identity': store_identity,
                'item_exists': True,
                'tracked': tracked,
                'level_exists': False,
                'inventory_level_gid': None,
                'available': None,
                'updated_at': False,
            }
        if not isinstance(level, dict):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Malformed Shopify inventoryLevel shape in pair read.',
            )
        inventory_level_gid = level.get('id')
        if not isinstance(inventory_level_gid, str) or not inventory_level_gid:
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Shopify inventoryLevel is present but its GID is missing '
                'or malformed.',
            )
        # The returned level's item/location identity must belong to
        # the requested pair, where the schema exposes it (PR #182
        # comment 5029906989 item 4) -- this query requests both.
        level_item = level.get('item') or {}
        level_location = level.get('location') or {}
        if (
            not isinstance(level_item, dict)
            or level_item.get('id') != requested_item_gid
        ):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Shopify inventoryLevel item identity does not match the '
                'requested InventoryItem.',
            )
        if (
            not isinstance(level_location, dict)
            or level_location.get('id') != requested_location_gid
        ):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Shopify inventoryLevel location identity does not match '
                'the requested location.',
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
                if found_available_entry:
                    # A duplicate "available" entry is never silently
                    # resolved by taking the last one (PR #182 comment
                    # 5029906989 item 8) -- fails closed instead.
                    raise JobHandlerError(
                        ERROR_CLASS_DATA_SHAPE,
                        'Shopify returned more than one "available" '
                        'quantity entry in pair read.',
                    )
                found_available_entry = True
                try:
                    available = _strict_shopify_int(quantity.get('quantity'))
                except ValueError:
                    raise JobHandlerError(
                        ERROR_CLASS_DATA_SHAPE,
                        'Shopify returned a non-integer "available" '
                        'quantity in pair read.',
                    )
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
            'inventory_level_gid': inventory_level_gid,
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
        # Legacy rows can pre-date the inventory-level pair table, and a
        # product binding and a location mapping are allowed to arrive in
        # either order.  Reconcile that durable identity before taking the
        # scan snapshot so the first-push ceremony is reachable from this
        # production entry point as well as from the write hooks below.
        self._bootstrap_inventory_level_bindings(store=store)
        Binding = self.env['shopify.connector.inventory.level.binding']
        bindings = Binding.search([
            ('store_id', '=', store.id),
            ('location_mapping_id.push_enabled', '=', True),
            ('status', '=', 'active'),
            ('product_variant_binding_id.status', '=', 'active'),
            ('location_mapping_id.status', '=', 'active'),
        ])
        mapped = len(bindings)
        enqueued_count = 0
        coalesced_count = 0
        unchanged_count = 0
        previewed_count = 0
        for binding in bindings:
            if not self._binding_operationally_eligible(binding):
                continue
            target, _free_qty = self._refresh_pending_target(binding)
            # TD-012. The shipped first-push form tells the operator, in
            # the `pending` empty state, that "the preview runs on the next
            # scheduled pass". Nothing made that true: the only writer of
            # `previewed` is the `inventory_first_push_preview` handler,
            # and its only admission surface had no production caller at
            # all -- so a pair could never leave `pending`, the confirm
            # control could never appear, and the entire first-push
            # ceremony was unreachable outside a test that wrote the state
            # itself.
            #
            # The preview is admitted INSTEAD OF a push_sync, not beside
            # it, for two independent reasons. Semantically, an unconfirmed
            # pair has nothing to push -- `inventory_push_sync` gates every
            # mutation on `first_push_state='confirmed'` (D-013-4), so the
            # push job it would admit could only ever decline. Mechanically,
            # both job types share this pair's `operation_scope_key`, so
            # admitting both would collide on the unique constraint and one
            # would be swallowed as a coalesce -- silently, and not always
            # the same one.
            if binding.first_push_state == 'pending':
                if self._admit_first_push_preview(binding):
                    previewed_count += 1
                else:
                    coalesced_count += 1
                continue
            # A Float `last_pushed_available` defaults to 0.0 -- that
            # alone never distinguishes "never successfully pushed" from
            # "successfully pushed a confirmed zero" (PR #182 comment
            # 5028910116 item 5). Only a populated `last_pushed_at`
            # proves a prior successful push; a never-pushed pair must
            # always be admitted to orchestration, even when the target
            # itself is zero (activation may still be required).
            never_pushed = not binding.last_pushed_at
            if not never_pushed and target == binding.last_pushed_available:
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
            'coalesced=%d unchanged=%d first_push_previews=%d.' % (
                store.id, mapped, enqueued_count, coalesced_count,
                unchanged_count, previewed_count,
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
        if not self._binding_operationally_eligible(binding):
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'The first-push preview cannot run while its level binding, '
                'variant binding, or location mapping is inactive, disabled, '
                'or outside the owning store/company scope.',
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
    def _enqueue_first_push_preview(self, binding):
        """Sanctioned `inventory_first_push_preview` job admission (PR
        #182 comment 5025803697 item 22.C; hardened per comment
        5028910116 item 13). Private service method (leading
        underscore) -- no public action/UI is added, and explicit
        Operator/Administrator authority is required so this is never an
        unguarded admission surface. `job_source=
        'export_preview_dry_run'` (a core-recognized, store-state-
        ungated diagnostic source): this job never issues a Shopify
        mutation, it only computes and stores a preview quantity.
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
                "enqueue a first-push preview."
            )
        # Company isolation is asserted BEFORE the admission elevates, so
        # an authorised Operator of company A can never admit a preview for
        # company B's pair by holding the right group in the wrong company.
        self._assert_first_push_company_access(binding)
        return self._admit_first_push_preview(binding)

    @api.model
    def _assert_first_push_company_access(self, binding):
        """The pair's company must be one the acting user actually has."""
        company = binding.company_id
        if company and company not in self.env.user.company_ids:
            raise AccessError(
                "This inventory pair belongs to another company. A "
                "first-push preview may only be admitted from a company "
                "you have access to."
            )
        return True

    @api.model
    def _admit_first_push_preview(self, binding):
        """TD-012: the admission itself, shared by both trigger surfaces.

        Split out from `_enqueue_first_push_preview` because there are two
        callers with two different authorities and only one of them is a
        user. A person pressing a control is role-gated and
        company-checked; the scheduled pass is the system acting on its own
        schedule and has no user to gate. Collapsing them would mean either
        an unauthenticated user-facing admission or a scan that fails
        whenever the dispatcher identity is not in a connector group --
        both wrong, in opposite directions.

        Never issues a Shopify mutation: the job type it admits is
        `inventory_first_push_preview`, whose handler only computes and
        stores a quantity, and whose `job_source` is the read-only
        `export_preview_dry_run`.

        Duplicate-safe on the same terms as `_try_enqueue_push_sync`: a
        non-terminal inventory job already holding this pair's
        `operation_scope_key` means "already in progress", and admitting
        nothing loses nothing. The savepoint plus the constraint remain the
        atomic guard for the TOCTOU window between the read and the create.
        """
        if not self._binding_operationally_eligible(binding):
            return self.env['shopify.connector.job']
        if self._binding_push_admission_blocked(binding):
            return self.env['shopify.connector.job']
        store = binding.store_id
        pair_key = pair_scope_key(
            store.id,
            binding.shopify_inventory_item_gid,
            binding.location_mapping_id.shopify_gid,
        )

        def _existing_pair_job():
            return self._existing_pair_scope_job(store, pair_key)

        if _existing_pair_job():
            return self.env['shopify.connector.job']
        try:
            with self.env.cr.savepoint():
                return self._create_inventory_job(
                    store, 'export_preview_dry_run',
                    JOB_TYPE_FIRST_PUSH_PREVIEW, binding,
                )
        except (ValidationError, IntegrityError) as exc:
            message = str(exc)
            if (
                OPERATION_SCOPE_CONSTRAINT_MESSAGE not in message
                and OPERATION_SCOPE_CONSTRAINT_NAME not in message
            ):
                raise
            if not _existing_pair_job():
                raise
            return self.env['shopify.connector.job']

    @api.model
    def _enqueue_location_sync(self, store, job_source='scheduled_sync'):
        """Sanctioned `inventory_location_sync` job admission (PR #182
        comment 5025803697 item 22.C; hardened per comment 5028910116
        item 13). Private service method (leading underscore) -- explicit
        Operator/Administrator authority is required so this is never an
        unguarded admission surface. Domain-gated on
        `inventory_domain_enabled`; the store-state gate for a business
        `job_source` is enforced by the core job model itself, at both
        creation and start.

        `job_source` is a bounded choice, not a free parameter (Wave 5).
        Only the three values in `LOCATION_SYNC_JOB_SOURCES` are accepted,
        and the ONE public caller --
        `action_refresh_shopify_locations` -- derives which one applies
        from the store's own lifecycle state rather than taking it from a
        caller. Anything else raises, so no RPC can pick its own gate.
        """
        if job_source not in LOCATION_SYNC_JOB_SOURCES:
            raise ValidationError(
                "A location sync may only be admitted under one of the "
                "sanctioned job sources."
            )
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
                "enqueue a location sync."
            )
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings or not settings.inventory_domain_enabled:
            raise UserError(
                'The inventory domain is not enabled for this store.'
            )
        return self.env['shopify.connector.job.enqueue'].enqueue(
            store, job_source, JOB_TYPE_LOCATION_SYNC,
            payload_hash=uuid.uuid4().hex,
        )

    @api.model
    def _resolve_store_for_location_action(self, store_id):
        """A caller-supplied store id -> a store this caller may act on.

        Two checks, in this order, because each catches something the other
        does not, and both run BEFORE any elevation anywhere below them.

        1. **Ordinary record access, as the calling user.** `browse(id)`
           bypasses no ACL and proves nothing; `check_access` is what turns
           an id somebody typed into an RPC call into a record they may
           read. The SEC-3 record rule makes a foreign store invisible, so
           this is where a cross-company id is refused. Both refusals --
           `AccessError` for a real-but-foreign store and `MissingError`
           for an id that was never real -- collapse to ONE generic
           message, so the difference between them cannot be used as an
           existence oracle for stores in another company.
        2. **`env.companies`.** The same rule's own comparison, restated
           for the case a store's `company_id` is unset, and evaluated
           against the switcher selection rather than `user.company_ids`
           -- otherwise a user allowed in two companies could act on the
           one they are not currently in.
        """
        Store = self.env['shopify.connector.store']
        if not store_id:
            raise UserError('No Shopify store was selected.')
        store = Store.browse(int(store_id))
        try:
            store.check_access('read')
        except (AccessError, MissingError):
            raise UserError('This Shopify store is not available.')
        if store.company_id and store.company_id not in self.env.companies:
            raise AccessError(
                'This Shopify store belongs to another company.'
            )
        return store

    @api.model
    def _location_refresh_job(self, store):
        """The non-terminal location-sync job for this store, if any."""
        Job = self.env['shopify.connector.job']
        Job.flush_model()
        return Job.sudo().search([
            ('store_id', '=', store.id),
            ('job_type', '=', JOB_TYPE_LOCATION_SYNC),
            ('state', 'not in', TERMINAL_JOB_STATES),
        ], order='id desc', limit=1)

    @api.model
    def _location_refresh_failure_reason(self, job):
        """Last redacted operator-facing transition message for this run."""
        log = self.env['shopify.connector.job.log'].sudo().search([
            ('job_id', '=', job.id),
            ('event_type', '=', 'state_change'),
            ('to_state', 'in', (
                'failed_retryable', 'failed_final',
                'blocked_manual_review', 'skipped',
            )),
        ], order='id desc', limit=1)
        if log and log.message:
            return log.message
        if job.error_class:
            labels = dict(job._fields['error_class'].selection)
            return labels.get(job.error_class, job.error_class)
        return 'The location refresh did not finish safely.'

    @api.model
    def location_refresh_state(self, store, job_id=None):
        """What the last/current Shopify-location refresh is actually doing.

        Four states an operator can act on, and the distinction between them
        is load bearing: an EMPTY location cache means something completely
        different depending on which one applies.

        * `waiting`  -- a job is admitted and has not started.
        * `running`  -- a job has started.
        * `succeeded`-- the most recent job finished; the cache is an answer.
        * `failed`   -- the most recent job did not finish successfully, so
          the cache is whatever it was before and is NOT an answer.
        * `none`     -- no refresh has ever been asked for.

        A surface that reported "Shopify has no locations" while a refresh
        was queued or had failed would be stating a fact about the merchant's
        Shopify store that nobody has established. `waiting`/`running`/
        `failed` all exist so it cannot.

        Read-only, and elevated only to read connector-owned job rows for a
        store the caller may see. Callers have already resolved the store, but
        the visibility check is repeated here rather than assumed: this is a
        public method, and a public method that trusts its caller's resolution
        is one refactor away from being the route that skipped it. The
        elevation is scoped to this store's own jobs and exposes an id, a
        state and the redacted operator message already recorded on its audit
        transition -- never a Shopify response body, technical detail, or a
        traceback.
        """
        store = self._resolve_store_for_location_action(store.id)
        domain = [
            ('store_id', '=', store.id),
            ('job_type', '=', JOB_TYPE_LOCATION_SYNC),
        ]
        if job_id is not None:
            try:
                exact_id = int(job_id)
            except (TypeError, ValueError):
                raise UserError('This location refresh is not available.')
            domain.append(('id', '=', exact_id))
        last = self.env['shopify.connector.job'].sudo().search(
            domain, order='id desc', limit=1,
        )
        if job_id is not None and not last:
            # Exact store + type agreement, without revealing whether the id
            # belongs to another store or never existed.
            raise UserError('This location refresh is not available.')
        if not last:
            return {
                'state': 'none', 'job_id': False, 'job_state': '', 'reason': '',
                'next_retry_at': False, 'can_retry': False,
            }
        base = {
            'job_id': last.id,
            'job_state': last.state,
            'reason': '',
            'next_retry_at': last.next_retry_at or False,
            'can_retry': last.state in ('failed_retryable', 'failed_final'),
        }
        if last.expected_connection_generation != store.connection_generation:
            return dict(
                base,
                state='stale',
                reason=(
                    'This refresh belongs to an earlier store connection. '
                    'Run a new refresh for the current connection.'
                ),
                can_retry=False,
            )
        if last.state == 'running':
            return dict(base, state='running')
        if last.state in ('draft', 'queued', 'retry_waiting'):
            return dict(base, state='waiting')
        if last.state == 'succeeded':
            return dict(base, state='succeeded')
        # Everything else terminal is a refresh that did not deliver: failed,
        # cancelled, skipped. The operator gets the connector's own error
        # CLASS, which is a fixed vocabulary value -- never a raw traceback,
        # never a Shopify response body.
        return dict(
            base,
            state='failed',
            reason=self._location_refresh_failure_reason(last),
        )

    @api.model
    def action_refresh_shopify_locations(self, store_id):
        """Ask Shopify for this store's locations. The customer-operable route.

        This is the ONE public entry point for a location refresh, shared by
        the guided setup's Location mapping step and the Location Mapping
        workspace, and it admits a JOB. It issues no Shopify request: the
        request happens later, on the ordinary dispatcher, inside
        `_handle_inventory_location_sync`. No wizard, no Owl component, no
        controller and no view in this repository holds a transport, and this
        method is what makes that possible rather than merely intended.

        WHY THE JOB SOURCE DEPENDS ON THE STORE'S STATE, AND WHY THAT IS NOT
        A LOOPHOLE.

        `manual_sync` is a business job source, so core refuses to create it
        -- and refuses to start it -- for a store that is not `connected`.
        That is exactly right for the workspace: an operator refreshing a
        live store's locations is doing business work and should be stopped
        while the store is disconnecting.

        It is exactly wrong for guided setup, where the whole point is that
        the store is NOT connected yet: the `mapped_location` readiness check
        gates activation, mapping needs the location list, and the location
        list would need the store to be activated first. Core already names
        that shape and already provides for it -- `setup_readiness_check` is
        one of two sources deliberately exempt from store-state gating,
        because such jobs "exist to determine connection/readiness state, so
        gating them on 'connected' would be circular". A pre-activation
        location refresh is that, precisely: it exists so a readiness check
        can be satisfied.

        So the source is derived from the state, and only two states admit
        anything at all:

        * `connected`        -> `manual_sync`, fully business-gated;
        * `setup_incomplete` -> `setup_readiness_check`, the setup path.

        `reconnect_needed`, `disconnecting` and `disconnected` are refused
        outright rather than routed down the ungated path -- using the setup
        source there would turn a deliberate exemption into a way around the
        business gate, which is the one thing this must not become. The
        domain-enablement gate (`inventory_domain_enabled`) applies to every
        one of these at start time regardless, since core evaluates it for
        every job whatever its source.
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
                "refresh the Shopify location list."
            )
        store = self._resolve_store_for_location_action(store_id)
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings or not settings.inventory_domain_enabled:
            raise UserError(
                'Inventory syncing is not enabled for this store, so there '
                'are no locations to refresh. Enable it first.'
            )
        # The credential conditions this read-only operation genuinely
        # needs, and no more: a token on record, verified since it was last
        # changed, and a test connection that actually passed. Without all
        # three the request could only fail, and it would fail after being
        # queued -- which reads to an operator as "Shopify is broken" rather
        # than "finish the previous step".
        if not store.credential_present:
            raise UserError(
                'Enter the Shopify Admin API access token before refreshing '
                'the location list.'
            )
        if not store.credential_last_verified_at:
            raise UserError(
                'Test the connection before refreshing the location list. '
                'The stored token has not been verified since it was last '
                'changed.'
            )
        if store.last_test_connection_result != 'pass':
            raise UserError(
                'The last connection test did not pass, so the location list '
                'cannot be refreshed yet. Fix the connection first.'
            )
        if store.state == 'connected':
            job_source = 'manual_sync'
        elif store.state == 'setup_incomplete':
            job_source = 'setup_readiness_check'
        else:
            raise UserError(
                'This store is not in a state where its Shopify location '
                'list can be refreshed. Reconnect it first.'
            )
        return self._admit_location_refresh(store, job_source)

    @api.model
    def _setup_refresh_shopify_locations(self, store_id):
        """Admit the setup-only location read for an unfinished recovery.

        Credential replacement deliberately demotes a previously connected
        store to ``reconnect_needed``.  The guided setup is also the surface
        where that Administrator repairs configuration, so refusing its
        read-only location discovery there makes mapping and readiness
        circular.  This private seam keeps the exemption narrow:

        * the setup wizard has already enforced Administrator authority and
          this method repeats it before admission;
        * ``setup_incomplete`` and ``reconnect_needed`` use the narrow setup
          read, while a connected store keeps the ordinary manual-sync route;
        * a fresh passing connection test is mandatory;
        * the exact ``setup_readiness_check`` / ``inventory_location_sync``
          read is admitted; no business write or ordinary sync is opened;
        * ``disconnecting`` and ``disconnected`` remain closed.

        The public workspace action above intentionally keeps its existing
        lifecycle contract.  A generic RPC cannot select this private method.
        """
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may refresh '
                'locations during guided setup.'
            )
        store = self._resolve_store_for_location_action(store_id)
        if store.last_test_connection_result != 'pass':
            raise UserError(
                'The connection test must pass before Shopify locations can '
                'be loaded.'
            )
        if store.state == 'connected':
            return self._admit_location_refresh(store, 'manual_sync')
        if store.state not in ('setup_incomplete', 'reconnect_needed'):
            raise UserError(
                'Location discovery is not available from this setup state.'
            )
        return self._admit_location_refresh(
            store, 'setup_readiness_check',
        )

    @api.model
    def _admit_location_refresh(self, store, job_source):
        """Coalesce/retry/admit one location refresh under a chosen source."""
        # Duplicate admission is coalesced rather than queued twice: two
        # refreshes of the same read-only list are the same refresh, and a
        # second one would only compete for the same rate limit. The caller
        # gets the REAL admitted job either way, so the surface reports the
        # identity and state of work that genuinely exists.
        existing = self._location_refresh_job(store)
        if existing:
            if existing.state == 'failed_retryable':
                # Retry the preserved logical run.  A new row would discard
                # the failure lineage the setup surface is asking to recover.
                existing.with_user(self.env.user).action_manual_retry()
            self._trigger_dispatch_after_location_refresh()
            return existing
        previous = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', store.id),
            ('job_type', '=', JOB_TYPE_LOCATION_SYNC),
        ], order='id desc', limit=1)
        if (
            previous.state == 'failed_final'
            and previous.expected_connection_generation
            == store.connection_generation
        ):
            previous.with_user(self.env.user).action_manual_retry()
            self._trigger_dispatch_after_location_refresh()
            return previous
        job = self._enqueue_location_sync(store, job_source=job_source)
        self._trigger_dispatch_after_location_refresh()
        return job

    @api.model
    def _trigger_dispatch_after_location_refresh(self):
        """Schedule the governed dispatcher promptly after this RPC commits.

        This preserves the queue boundary: the screen never calls Shopify.
        It only asks Odoo to run the existing dispatcher without waiting for
        its five-minute fallback cadence.
        """
        cron = self.env.ref(
            'shopify_connector_core.'
            'ir_cron_shopify_connector_job_dispatch_drain',
            raise_if_not_found=False,
        )
        if cron:
            cron.sudo()._trigger()
        return True

    @api.model
    def _validate_locations_response(self, result):
        """Fail-closed GraphQL response/pagination-shape validation for
        the location cache sync (PR #182 comment 5028910116 item 10): a
        malformed or partial page must never be silently treated as
        "zero locations, no next page" -- every shape defect raises
        `JobHandlerError(data_shape_schema_mismatch, ...)`, which routes
        through the ordinary read-safe retry path, never a spurious
        succeeded-empty-store outcome."""
        if not isinstance(result, dict) or not isinstance(
            result.get('data'), dict
        ):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Malformed Shopify locations response (no data).',
            )
        connection = result['data'].get('locations')
        if not isinstance(connection, dict):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Malformed Shopify locations connection shape.',
            )
        edges = connection.get('edges')
        if not isinstance(edges, list):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Malformed Shopify locations edges shape.',
            )
        page_info = connection.get('pageInfo')
        if not isinstance(page_info, dict):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Malformed Shopify locations pageInfo shape.',
            )
        has_next_page = page_info.get('hasNextPage')
        if not isinstance(has_next_page, bool):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Malformed Shopify locations hasNextPage shape.',
            )
        validated_edges = []
        for edge in edges:
            if not isinstance(edge, dict):
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Malformed Shopify locations edge shape.',
                )
            node = edge.get('node')
            if not isinstance(node, dict):
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Malformed Shopify locations node shape.',
                )
            gid = node.get('id')
            if not isinstance(gid, str) or not gid:
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Malformed or missing Shopify Location GID.',
                )
            name = node.get('name')
            if name is not None and not isinstance(name, str):
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Malformed Shopify locations name shape.',
                )
            validated_edges.append({
                'gid': gid, 'name': name or gid, 'cursor': edge.get('cursor'),
            })
        next_cursor = None
        if has_next_page:
            if not validated_edges:
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'hasNextPage is true but no edges were returned to '
                    'derive a page cursor.',
                )
            last_cursor = validated_edges[-1]['cursor']
            if not isinstance(last_cursor, str) or not last_cursor:
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'hasNextPage is true but the page cursor is missing '
                    'or malformed.',
                )
            next_cursor = last_cursor
        return {
            'edges': validated_edges, 'has_next_page': has_next_page,
            'next_cursor': next_cursor,
        }

    @api.model
    def _handle_inventory_location_sync(self, job):
        """Populate the core Shopify location cache (D-013-5).

        Reads the `locations` query (paginated, `includeInactive:
        false`) and upserts `shopify.connector.location` rows via one
        of this module's several narrow, named `sudo()` elevations --
        the core cache's ACL deliberately grants no group create/write,
        so a non-elevated upsert would always raise.
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
            try:
                with client.execute_business_read(
                    job, store, query, {'cursor': cursor}, purpose='inventory',
                ) as result:
                    connection = self._validate_locations_response(result)
                    for edge in connection['edges']:
                        existing = Location.sudo().search([
                            ('store_id', '=', store.id),
                            ('shopify_location_gid', '=', edge['gid']),
                        ], limit=1)
                        vals = {
                            'store_id': store.id,
                            'shopify_location_gid': edge['gid'],
                            'name': edge['name'],
                            'shopify_location_active': True,
                            'last_synced_at': fields.Datetime.now(),
                        }
                        if existing:
                            existing.sudo().write(vals)
                        else:
                            Location.sudo().create(vals)
                        upserted += 1
            except ShopifyClientError as exc:
                # This is a replay-safe read. Preserve the API client's
                # accepted fixed taxonomy and redacted operator reason so the
                # dispatcher can route the exact run and setup can show why it
                # stopped. Letting this escape as a generic exception would
                # erase both facts behind ``unknown_system_error``.
                raise JobHandlerError(
                    exc.error_class, exc.reason, exc.technical_detail,
                ) from exc
            if not connection['has_next_page']:
                break
            cursor = connection['next_cursor']
        settings = self.env['shopify.connector.store.settings'].sudo().search([
            ('store_id', '=', store.id),
        ], limit=1)
        if settings:
            # The cache is readiness evidence. A complete traversal invalidates
            # a verdict recorded before it; exact-run follow-up recomputes it.
            settings._mark_setup_readiness_stale()
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

        Wave 5 closes the hole that made "explicit" weaker than it sounds.
        The GID was accepted as whatever string the caller passed: every
        existing test handed it a fabricated one and every one of them
        passed, which is the proof that nothing ever checked it. A GID must
        now correspond to a currently-ACTIVE cached
        `shopify.connector.location` row belonging to THIS store, so an
        arbitrary GID typed into an RPC call, a GID belonging to another
        store, and a location Shopify no longer reports are all refused
        before any mapping exists. `shopify_location_name_snapshot` is then
        taken from that validated cached row -- never from caller input,
        which would let a browser choose the name an operator later reads
        back as identity.
        """
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                "Only a Shopify Connector Administrator may "
                "create or update a location mapping."
            )
        store = self._resolve_store_for_location_action(store.id)
        if not isinstance(shopify_location_gid, str) or not shopify_location_gid:
            raise UserError("An explicit Shopify Location GID is required.")
        cached_location = self._validated_cached_location(
            store, shopify_location_gid,
        )
        # Rebound into this service's own environment before anything is
        # checked: a caller-supplied recordset carries its own environment,
        # and an elevated one would otherwise answer its own visibility and
        # company questions. The docstring's "resolves in the caller's own
        # (non-elevated) environment" is only true because of this line.
        odoo_location = odoo_location.with_env(self.env).exists()
        if not odoo_location:
            raise UserError("The Odoo location does not exist.")
        try:
            odoo_location.check_access('read')
        except (AccessError, MissingError):
            raise UserError("That Odoo location is not available.")
        if odoo_location.usage != 'internal':
            raise UserError(
                "Only an internal Odoo stock location can be mapped."
            )
        if (
            odoo_location.company_id
            and odoo_location.company_id != store.company_id
        ):
            raise UserError(
                "The Odoo location belongs to a different company than the "
                "Shopify store."
            )
        Mapping = self.env['shopify.connector.location.mapping']
        existing = Mapping.search([
            ('store_id', '=', store.id),
            ('odoo_location_id', '=', odoo_location.id),
        ], limit=1)
        if existing:
            # Exact existing identity may update non-identity controls
            # (push_enabled); a differing GID for the same Odoo location
            # is an identity conflict and must fail closed, never
            # silently replace the recorded Shopify identity (PR #182
            # comment 5028910116 item 13).
            if existing.shopify_gid != shopify_location_gid:
                raise UserError(
                    "A location mapping already exists for this Odoo "
                    "location with a different Shopify Location GID. "
                    "This service never silently replaces an existing "
                    "mapping's identity; use the reviewed remap path to "
                    "change it."
                )
            existing.sudo().write({
                'push_enabled': bool(push_enabled),
                'shopify_location_name_snapshot': cached_location.name,
            })
            return existing
        # Never silently move an already-mapped Shopify GID to a
        # different Odoo location either.
        gid_collision = Mapping.search([
            ('store_id', '=', store.id),
            ('shopify_gid', '=', shopify_location_gid),
        ], limit=1)
        if gid_collision:
            raise UserError(
                "This Shopify Location GID is already mapped to a "
                "different Odoo location for this store. This service "
                "never silently moves an existing mapping's identity; "
                "use the reviewed remap path to move it."
            )
        mapping = Mapping.sudo().create({
            'store_id': store.id,
            'shopify_gid': shopify_location_gid,
            'odoo_location_id': odoo_location.id,
            'match_key': 'manual',
            'push_enabled': bool(push_enabled),
            'shopify_location_name_snapshot': cached_location.name,
        })
        self._mark_location_readiness_stale(store)
        return mapping

    @api.model
    def _validated_cached_location(self, store, shopify_location_gid):
        """The active cached Shopify location this GID names, or a refusal.

        The cache is read elevated because `shopify.connector.location`
        deliberately grants no group create/write and this module's own named
        elevation is how it is maintained -- but the STORE was already
        resolved through the caller's own record access, so this can only
        ever read rows belonging to a store the caller may act on. The
        `store_id` term is what makes that true, and it is not optional.

        Every refusal is deliberately identical in shape and says nothing
        about what does exist elsewhere: a caller must not be able to
        distinguish "no such location anywhere" from "that location belongs
        to somebody else's store" by comparing two messages.
        """
        cached = self.env['shopify.connector.location'].sudo().search([
            ('store_id', '=', store.id),
            ('shopify_location_gid', '=', shopify_location_gid),
        ], limit=1)
        if not cached:
            raise UserError(
                "This is not an active Shopify location for this store. "
                "Refresh the Shopify location list and choose one from it; "
                "a mapping is never created for a location this store's "
                "own list does not contain."
            )
        if not cached.shopify_location_active:
            raise UserError(
                "This Shopify location is no longer active in this store's "
                "location list and cannot be mapped. Refresh the list and "
                "choose an active location."
            )
        return cached

    @api.model
    def _mark_location_readiness_stale(self, store):
        """A mapping changed, so `mapped_location`'s last result is stale."""
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if settings:
            settings._mark_setup_readiness_stale()
        return True

    # ------------------------------------------------------------------
    # Remap: change the Odoo target of an already-bound Shopify location
    # ------------------------------------------------------------------

    @api.model
    def remap_location_mapping(
        self, mapping, odoo_location, reason, confirmed=False,
    ):
        """Point an existing Shopify location at a different Odoo location.

        WHY THIS EXISTS RATHER THAN A DIRECT `action_override_binding` BUTTON.

        The generic protected-binding mixin can already change a binding's
        bound Many2one, and it is correct for what it does -- but it admits
        **Reviewer** or Administrator, and it proves nothing about whether an
        INVENTORY remap is operationally safe. Moving the Odoo location under
        a pair whose first push is already previewed or confirmed silently
        changes which warehouse's stock is about to be written to a live
        storefront, and doing it while inventory work is in flight changes
        the target under a job that has already read the old one. Neither is
        something the mixin can know about, so exposing it directly on this
        screen would be exposing a control that looks reviewed and is not.

        So the mixin is not weakened and is not bypassed: it is called, once,
        as the final step, AFTER this method has established every additional
        thing the inventory domain requires. The Shopify identity
        (`shopify_gid`) is never touched, and nothing is ever unlinked and
        recreated -- a remap that deleted and re-made the row would discard
        the binding's own provenance and every foreign key pointing at it.
        """
        mapping.ensure_one()
        # REBIND THE RECORD INTO THIS SERVICE'S OWN ENVIRONMENT, FIRST.
        #
        # A caller hands in a recordset, and a recordset carries its
        # environment with it -- including `su=True` if it was obtained
        # through `sudo()`. Every check below would then be evaluated against
        # THAT environment rather than against the caller: `check_access`
        # would pass unconditionally, and the mixin's own
        # Reviewer-or-Administrator gate would be answered by whichever user
        # the caller's recordset happened to carry rather than by the person
        # pressing the button. Rebinding makes the authorization questions be
        # about the caller, which is the only reading under which asking them
        # means anything.
        mapping = mapping.with_env(self.env)
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                "Only a Shopify Connector Administrator may remap a Shopify "
                "location to a different Odoo location."
            )
        if not confirmed:
            raise UserError(
                "Remapping changes which Odoo location's stock this Shopify "
                "location reflects. Confirm that explicitly."
            )
        if not isinstance(reason, str) or not reason.strip():
            raise UserError("A non-empty remap reason is required.")
        try:
            mapping.check_access('write')
        except (AccessError, MissingError):
            raise UserError("This location mapping is not available.")
        store = self._resolve_store_for_location_action(mapping.store_id.id)
        # The Shopify side must still be a real, active location OF THIS
        # STORE. A remap of a location Shopify no longer reports would bind
        # an Odoo warehouse to an identity that cannot receive anything.
        cached = self._validated_cached_location(store, mapping.shopify_gid)
        # Same rebinding, same reason: an elevated `stock.location` recordset
        # must not be able to answer its own visibility check.
        odoo_location = odoo_location.with_env(self.env).exists()
        if not odoo_location:
            raise UserError("The Odoo location does not exist.")
        try:
            odoo_location.check_access('read')
        except (AccessError, MissingError):
            raise UserError("That Odoo location is not available.")
        if odoo_location.usage != 'internal':
            raise UserError(
                "Only an internal Odoo stock location can be mapped."
            )
        if (
            odoo_location.company_id
            and odoo_location.company_id != store.company_id
        ):
            raise UserError(
                "The Odoo location belongs to a different company than the "
                "Shopify store."
            )
        if odoo_location == mapping.odoo_location_id:
            raise UserError(
                "This Shopify location is already mapped to that Odoo "
                "location."
            )
        self._assert_remap_is_safe(mapping)
        # The mixin owns the write, the duplicate check, the company
        # comparison and the audit entry. The reason is sanitized by its own
        # `_audit_safe_reason` before it reaches the audit trail, so a
        # merchant email or phone number typed into the box never lands in
        # connector history.
        mapping.action_override_binding(odoo_location.id, reason=reason)
        mapping.sudo().write({
            'shopify_location_name_snapshot': cached.name,
        })
        self._mark_location_readiness_stale(store)
        return mapping

    @api.model
    def _assert_remap_is_safe(self, mapping):
        """Refuse a remap that would move the target under live work.

        Two distinct refusals, because they fail for two different reasons
        and an operator needs to know which one they are looking at.

        **Non-terminal inventory work.** A queued or running inventory job
        for one of this mapping's pairs has already read -- or is about to
        read -- the location this mapping currently names. Changing it
        underneath would make that job's own evidence describe a pairing
        that no longer exists.

        **Dependent first-push state.** A pair whose first push is
        `previewed` or `confirmed` carries a decision a human made about a
        specific Odoo location's stock. Silently re-pointing it would reuse
        that confirmation for a quantity nobody reviewed, which is exactly
        what the first-push guard exists to prevent.

        `pending` pairs are deliberately NOT a refusal: nothing has been
        computed or confirmed for them yet, so the mapping is still free.
        """
        Binding = self.env['shopify.connector.inventory.level.binding']
        bindings = Binding.sudo().search([
            ('location_mapping_id', '=', mapping.id),
        ])
        if bindings:
            Job = self.env['shopify.connector.job']
            Job.flush_model()
            busy = Job.sudo().search_count([
                ('store_id', '=', mapping.store_id.id),
                ('job_type', 'in', INVENTORY_JOB_TYPES),
                ('res_model', '=',
                 'shopify.connector.inventory.level.binding'),
                ('res_id', 'in', bindings.ids),
                ('state', 'not in', TERMINAL_JOB_STATES),
            ])
            if busy:
                raise UserError(
                    "Inventory work for this location has not finished. "
                    "Wait for it to complete, or resolve it, before "
                    "remapping."
                )
            committed = bindings.filtered(
                lambda binding: binding.first_push_state in (
                    'previewed', 'confirmed',
                )
            )
            if committed:
                raise UserError(
                    "A first stock push has already been previewed or "
                    "confirmed for this location, so its Odoo target cannot "
                    "be changed here. An Administrator can withdraw each "
                    "pair's first-push decision from the inventory pair "
                    "itself (Withdraw first push), after which the remap "
                    "becomes possible and a completely new preview and "
                    "confirmation are required."
                )
        return True

    def withdraw_first_push_decision(
        self, binding, reason, confirmed=False, expected_state=None,
        _locked_state_proof=None,
    ):
        """Withdraw a pair's previewed/confirmed first-push decision (TD-020).

        WHY THIS EXISTS. `first_push_state='confirmed'` was terminal: no route
        returned a confirmed pair to `pending`, so `_assert_remap_is_safe`'s
        correct refusal became PERMANENT -- a merchant who physically moved a
        warehouse after their first push could never re-point the Shopify
        location again (TD-020). The refusal was right; the missing piece was
        a governed way to unwind the DECISION it protects, and that unwinding
        is a first-push-guard concern, which is why it lives here and not on
        the mapping.

        WHAT IT NEVER DOES. It never reuses the old confirmation -- the pair
        returns to `pending`, so a completely new preview AND a new explicit
        confirmation are mandatory before any mutation can ever be enqueued
        again (the `inventory_push_sync` handler's D-013-4 gate is untouched).
        It performs no Shopify call and enqueues nothing.

        WHEN IT REFUSES. The decision may only be withdrawn from a PROVEN
        safe terminal state:

        * any non-terminal inventory job for the pair -- queued, running,
          waiting to retry, or blocked in review -- must finish or be
          resolved first (a job that already read the old pairing must not
          have the decision changed underneath it);
        * any unresolved mutation attempt -- `pending`, or `uncertain`
          without a recorded resolution -- must be resolved through the
          accepted mutation-resolution route first (an ambiguous outcome is
          exactly the state in which nothing may be assumed);
        * a pair flagged `stale`/`review` must be released through the
          accepted re-check route first.

        A pair whose past mutations all ended in recorded terminal outcomes
        (succeeded, failed clean, or resolved) IS a proven safe terminal
        state: the withdrawal changes only the stored decision, and the
        consequence disclosure tells the operator that Shopify keeps the last
        pushed quantity until a new first push is previewed, confirmed and
        applied.

        CONCURRENCY. The binding row is locked (`FOR UPDATE`) and the state
        re-read under the lock; `expected_state` -- the state the wizard
        showed the operator -- must still match, so a stale dialog or a
        concurrent withdrawal/confirmation loses instead of silently winning.
        """
        binding.ensure_one()
        # Same environment rebinding, same reason as `remap_location_mapping`:
        # authorization questions must be about the CALLER.
        binding = binding.with_env(self.env)
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                "Only a Shopify Connector Administrator may withdraw a "
                "first-push decision."
            )
        if not confirmed:
            raise UserError(
                "Withdrawing the first-push decision means this pair cannot "
                "push any stock until a new preview is run and explicitly "
                "confirmed. Confirm that explicitly."
            )
        if not isinstance(reason, str) or not reason.strip():
            raise UserError("A non-empty withdrawal reason is required.")
        try:
            binding.check_access('read')
        except (AccessError, MissingError):
            raise UserError("This inventory pair is not available.")
        store = self._resolve_store_for_location_action(binding.store_id.id)
        # Lock the binding row so two withdrawals -- or a withdrawal racing a
        # confirmation -- serialize, then re-read the state under the lock.
        binding.flush_recordset()
        self.env.cr.execute(
            "SELECT first_push_state "
            "FROM shopify_connector_inventory_level_binding "
            "WHERE id = %s FOR UPDATE",
            (binding.id,),
        )
        row = self.env.cr.fetchone()
        binding.invalidate_recordset(['first_push_state'])
        locked_state = row[0] if row else False
        # `expected_state` is MANDATORY at every public boundary (Batch 1
        # correction). It was optional, and the UI wizard passed
        # `self.expected_state or None` -- so an empty string silently disabled
        # the staleness check and a stale dialog could win a race it must lose.
        # Only an internal caller that already holds the row lock and has
        # compared the state itself may omit it, and it must say so explicitly
        # by passing its own locked-state proof rather than by passing nothing.
        if expected_state is None and _locked_state_proof is None:
            raise UserError(
                "Withdrawing a first-push decision requires the state the "
                "dialog was opened against, so a decision made against stale "
                "information cannot be applied."
            )
        if expected_state is None:
            expected_state = _locked_state_proof
        if locked_state != expected_state:
            raise UserError(
                "This pair's first-push state changed while the dialog was "
                "open (it is now '%s'). Nothing was withdrawn; reopen the "
                "pair and decide against its current state." % (
                    locked_state or 'unknown',
                )
            )
        if locked_state not in ('previewed', 'confirmed'):
            raise UserError(
                "This pair has no previewed or confirmed first push to "
                "withdraw."
            )
        self._assert_first_push_withdrawal_is_safe(binding)
        old_target = binding.location_mapping_id.odoo_location_id.display_name
        safe_reason = binding._audit_safe_reason(reason)
        binding.sudo().write({
            'first_push_state': 'pending',
            'first_push_preview_qty': False,
            'first_push_confirmed_at': False,
            'first_push_confirmed_by_uid': False,
        })
        # The one sanctioned audit-trail path lifecycle actions funnel
        # through: actor and time are the job row's own provenance.
        store._create_lifecycle_audit_job(
            'First-push decision withdrawn for inventory pair #%d '
            '(%s at %s): state %s returned to pending. A new preview and a '
            'new explicit confirmation are required before any push. '
            'Reason: %s' % (
                binding.id,
                binding.shopify_inventory_item_gid,
                old_target,
                locked_state,
                safe_reason,
            )
        )
        self._mark_location_readiness_stale(store)
        return True

    def first_push_withdrawal_preview(self, mapping):
        """What withdrawing this Shopify location's first-push decisions costs.

        Read-only, and the ONLY source the confirmation dialog renders from, so
        the counts an operator confirms against and the rows the withdrawal acts
        on are computed by one method. It returns a `signature` describing the
        exact mapping/binding state it observed; the withdrawal requires that
        signature back and refuses if anything moved meanwhile.

        Administrator-only and store/company-structural, like every other
        location action here -- a preview that disclosed pair counts to a caller
        who may not act on them would be an enumeration surface.
        """
        mapping.ensure_one()
        mapping = mapping.with_env(self.env)
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                "Only a Shopify Connector Administrator may withdraw a "
                "location's first-push decisions."
            )
        try:
            mapping.check_access('read')
        except (AccessError, MissingError):
            raise UserError("This location mapping is not available.")
        self._resolve_store_for_location_action(mapping.store_id.id)
        bindings = self._first_push_bindings_of(mapping)
        affected = bindings.filtered(
            lambda b: b.first_push_state in ('previewed', 'confirmed')
        )
        pushed = affected.filtered(lambda b: b.last_pushed_at)
        return {
            'mapping_id': mapping.id,
            'shopify_location': (
                mapping.shopify_location_name_snapshot or mapping.shopify_gid
            ),
            'odoo_location': mapping.odoo_location_id.display_name,
            'total_pairs': len(bindings),
            'affected_pairs': len(affected),
            'previewed_pairs': len(affected.filtered(
                lambda b: b.first_push_state == 'previewed'
            )),
            'confirmed_pairs': len(affected.filtered(
                lambda b: b.first_push_state == 'confirmed'
            )),
            'pairs_live_on_shopify': len(pushed),
            'signature': self._first_push_withdrawal_signature(bindings),
        }

    @api.model
    def _first_push_bindings_of(self, mapping):
        """Every inventory pair under one Shopify location mapping, id-ordered.

        `order='id asc'` is not cosmetic: it is the deterministic lock order the
        bulk withdrawal takes its row locks in, so two administrators acting on
        overlapping mappings queue behind one another instead of deadlocking.
        """
        return self.env[
            'shopify.connector.inventory.level.binding'
        ].sudo().search(
            [('location_mapping_id', '=', mapping.id)], order='id asc',
        )

    @api.model
    def _first_push_withdrawal_signature(self, bindings):
        """A compact description of the exact state a decision was made against.

        `expected_state` on the single-pair route is one value; a mapping-level
        withdrawal spans many pairs, and "nothing moved" has to mean nothing
        moved about ANY of them -- a pair added, removed, previewed or confirmed
        between the dialog opening and the operator confirming all change what
        the confirmation means. Hashed rather than listed so the token stays one
        short field, and non-secret: it describes states, not data.
        """
        material = ';'.join(
            '%d:%s:%s' % (
                binding.id, binding.first_push_state,
                '1' if binding.last_pushed_at else '0',
            )
            for binding in bindings
        )
        return hashlib.sha256(material.encode()).hexdigest()[:32]

    def withdraw_first_push_decisions_for_mapping(
        self, mapping, reason, confirmed=False, expected_signature=None,
    ):
        """Withdraw EVERY first-push decision under one Shopify location.

        WHY THIS EXISTS BESIDE THE SINGLE-PAIR ROUTE (Batch 1 correction). The
        single-pair withdrawal is the right instrument for focused recovery, and
        it is the wrong one for the case TD-020 was actually raised about: a
        merchant who physically moved a warehouse must clear EVERY pair under
        that Shopify location before `_assert_remap_is_safe` will let them
        re-point it, because that guard scans all of them. With one pair per
        product variant, "withdraw them all" meant opening a dialog, typing a
        reason and confirming a consequence once per variant -- hundreds of
        times, with no atomicity, so an interruption left the location half
        withdrawn and still un-remappable. That is a dead end with extra steps.

        WHAT IT IS NOT. It is not a bulk action over arbitrary records: it takes
        ONE mapping, never a recordset the caller assembled, so there is no
        cross-mapping or cross-store selection to smuggle. It needs no developer
        mode. It performs ZERO Shopify mutations -- nothing here contacts
        Shopify, and the quantity already on the storefront is untouched, which
        the dialog states. It does not weaken `_assert_remap_is_safe`: that
        guard is unchanged and still refuses a remap until every pair is
        `pending`; this is the governed route TO that state, not around it.

        ATOMICITY is the transaction's, and deliberately so. Every safety check
        runs against every affected pair BEFORE anything is written, and any
        refusal raises -- so either all eligible pairs return to `pending` or
        none do. A partially withdrawn location is exactly the state that makes
        the remap guard look broken to the operator.

        THE OLD CONFIRMATION IS NEVER REUSED. Each pair returns to `pending`
        with its preview quantity, confirmation stamp and confirming user
        cleared, so D-013-4's untouched gate forces the complete preview and
        confirm ceremony again before any push.
        """
        mapping.ensure_one()
        # Authorization, company and store, re-established as the CALLER --
        # never trusting the environment a recordset arrived with.
        preview = self.first_push_withdrawal_preview(mapping)
        mapping = mapping.with_env(self.env)
        if not confirmed:
            raise UserError(
                "Withdrawing this location's first-push decisions means no "
                "stock can be pushed for any of its pairs until each is "
                "previewed and confirmed again. Confirm that explicitly."
            )
        if not isinstance(reason, str) or not reason.strip():
            raise UserError("A non-empty withdrawal reason is required.")
        if not expected_signature:
            raise UserError(
                "Withdrawing this location's first-push decisions requires the "
                "state the dialog was opened against, so a decision made "
                "against stale information cannot be applied."
            )
        store = self._resolve_store_for_location_action(mapping.store_id.id)
        # Lock the mapping first, then its pairs in ascending id order. Two
        # administrators acting at once therefore queue rather than deadlock,
        # and the states compared below cannot move under us.
        mapping.flush_recordset()
        self.env.cr.execute(
            'SELECT id FROM shopify_connector_location_mapping '
            'WHERE id = %s FOR UPDATE',
            (mapping.id,),
        )
        if not self.env.cr.fetchone():
            raise UserError("This location mapping is not available.")
        bindings = self._first_push_bindings_of(mapping)
        if bindings:
            bindings.flush_recordset()
            self.env.cr.execute(
                'SELECT id FROM shopify_connector_inventory_level_binding '
                'WHERE id IN %s ORDER BY id FOR UPDATE',
                (tuple(bindings.ids),),
            )
            bindings.invalidate_recordset(['first_push_state'])
            bindings = self._first_push_bindings_of(mapping)
        # Staleness, under the locks. Not optional, and not a subset check: a
        # pair added or removed since the dialog opened changes what the
        # operator confirmed just as much as one whose state moved.
        if self._first_push_withdrawal_signature(bindings) != expected_signature:
            raise UserError(
                "This location's pairs changed while the dialog was open. "
                "Nothing was withdrawn; reopen it and decide against the "
                "current state."
            )
        affected = bindings.filtered(
            lambda b: b.first_push_state in ('previewed', 'confirmed')
        )
        if not affected:
            raise UserError(
                "This location has no previewed or confirmed first-push "
                "decision to withdraw."
            )
        # EVERY check, on EVERY pair, before ANY write. All or nothing.
        for binding in affected:
            self._assert_first_push_withdrawal_is_safe(binding)
        safe_reason = mapping._audit_safe_reason(reason)
        withdrawn = []
        for binding in affected:
            previous = binding.first_push_state
            binding.sudo().write({
                'first_push_state': 'pending',
                'first_push_preview_qty': False,
                'first_push_confirmed_at': False,
                'first_push_confirmed_by_uid': False,
            })
            withdrawn.append((binding, previous))
        # An auditable trail at BOTH levels: one record of the decision, and one
        # per pair, so the set acted on can be reconstructed exactly rather than
        # inferred from a count.
        store._create_lifecycle_audit_job(
            "First-push decisions withdrawn for Shopify location '%s' "
            '(mapping #%d, currently mapped to %s): %d of %d pair(s) returned '
            'to pending, %d of which have a quantity live on Shopify that is '
            'unchanged by this. A new preview and a new explicit confirmation '
            'are required before any push. Reason: %s' % (
                preview['shopify_location'], mapping.id,
                preview['odoo_location'], len(withdrawn), preview['total_pairs'],
                preview['pairs_live_on_shopify'], safe_reason,
            )
        )
        for binding, previous in withdrawn:
            store._create_lifecycle_audit_job(
                'First-push decision withdrawn for inventory pair #%d '
                '(%s) as part of the location-level withdrawal of mapping '
                '#%d: state %s returned to pending. Reason: %s' % (
                    binding.id, binding.shopify_inventory_item_gid,
                    mapping.id, previous, safe_reason,
                )
            )
        self._mark_location_readiness_stale(store)
        return len(withdrawn)

    @api.model
    def _assert_first_push_withdrawal_is_safe(self, binding):
        """Refuse a withdrawal outside a proven safe terminal state."""
        Job = self.env['shopify.connector.job']
        Job.flush_model()
        busy = Job.sudo().search_count([
            ('store_id', '=', binding.store_id.id),
            ('job_type', 'in', INVENTORY_JOB_TYPES),
            ('res_model', '=', 'shopify.connector.inventory.level.binding'),
            ('res_id', '=', binding.id),
            ('state', 'not in', TERMINAL_JOB_STATES),
        ])
        if busy:
            raise UserError(
                "Inventory work for this pair has not finished. Wait for it "
                "to complete, or resolve it, before withdrawing the "
                "first-push decision."
            )
        Attempt = self.env['shopify.connector.mutation.attempt']
        unresolved = Attempt.sudo().search_count([
            ('job_id.store_id', '=', binding.store_id.id),
            ('job_id.res_model', '=',
             'shopify.connector.inventory.level.binding'),
            ('job_id.res_id', '=', binding.id),
            '|',
            ('observed_outcome', '=', 'pending'),
            '&',
            ('observed_outcome', '=', 'uncertain'),
            ('resolution_disposition', '=', False),
        ])
        if unresolved:
            raise UserError(
                "A Shopify mutation for this pair has an unresolved or "
                "uncertain outcome. Resolve it through the mutation review "
                "route first; nothing may be withdrawn while what Shopify "
                "actually did is unknown."
            )
        if binding.status in ('stale', 'review'):
            raise UserError(
                "This pair is flagged '%s'. Release it through its re-check "
                "route first, then withdraw the first-push decision." % (
                    binding.status,
                )
            )
        return True

    @api.model
    def _bootstrap_inventory_level_bindings(
        self, variant_bindings=None, location_mappings=None, store=None,
    ):
        """Reconcile durable variant identity with mapped locations.

        This is an internal production hook, not a public binding-creation
        API.  Product import/create finalisation, location mapping changes,
        scheduled scans, and mutation reconciliation may all call it.  The
        public :meth:`ensure_inventory_level_binding` guard remains the only
        user-facing creation route; this helper deliberately has no role
        check because its callers are trusted connector transitions or
        background jobs.

        The Shopify InventoryItem GID is read only from the already persisted
        product-variant binding.  No Shopify lookup or synthetic identity is
        performed here.  The pair is created only when both sides name the
        same store and their Odoo company scope is compatible.  A savepoint
        around the create makes the database unique constraints the atomic
        race guard; a concurrent exact create is treated as an idempotent
        success, while a different identity is left for review.

        ``shopify_inventory_tracked`` is intentionally not used to change
        Odoo product configuration.  A false source value remains evidence on
        the variant binding and the existing push handler's live read routes
        that pair to ``skipped`` before any Shopify mutation.
        """
        VariantBinding = self.env[
            'shopify.connector.product.variant.binding'
        ].sudo()
        Mapping = self.env['shopify.connector.location.mapping'].sudo()
        LevelBinding = self.env[
            'shopify.connector.inventory.level.binding'
        ].sudo()

        stores = self.env['shopify.connector.store'].sudo().browse()
        store_scope_requested = store is not None
        if store_scope_requested:
            stores = store.sudo().exists()
        scope_store_ids = set(stores.ids)

        # A supplied recordset is itself the scope.  Derive this before any
        # widening search so a mapping write can never scan every product
        # binding in the database merely because the mapping-side hook did
        # not receive an explicit ``store`` argument.
        if not store_scope_requested and variant_bindings is not None:
            scope_store_ids.update(
                variant_bindings.sudo().exists().mapped('store_id').ids
            )
        if not store_scope_requested and location_mappings is not None:
            scope_store_ids.update(
                location_mappings.sudo().exists().mapped('store_id').ids
            )
        if store_scope_requested and not stores:
            return LevelBinding.browse()

        # When one side is supplied, constrain the other side to that side's
        # store set.  Passing ``None`` means "discover all legacy candidates";
        # an explicitly empty recordset remains empty and is not widened.
        if variant_bindings is None:
            variant_domain = [
                ('shopify_inventory_item_gid', '!=', False),
                ('status', '=', 'active'),
            ]
            if scope_store_ids:
                variant_domain.append(
                    ('store_id', 'in', sorted(scope_store_ids)),
                )
            variants = VariantBinding.search(variant_domain)
        else:
            variants = variant_bindings.sudo().exists()
            if scope_store_ids:
                variants = variants.filtered(
                    lambda binding: binding.store_id.id in scope_store_ids
                )
            variants = variants.filtered(
                lambda binding: (
                    binding.status == 'active'
                    and
                    isinstance(binding.shopify_inventory_item_gid, str)
                    and bool(binding.shopify_inventory_item_gid.strip())
                )
            )
        if variant_bindings is None:
            variants = variants.filtered(
                lambda binding: binding.status == 'active'
            )

        if location_mappings is None:
            mapping_domain = [
                ('shopify_gid', '!=', False),
                ('status', '=', 'active'),
                ('push_enabled', '=', True),
            ]
            if scope_store_ids:
                mapping_domain.append(
                    ('store_id', 'in', sorted(scope_store_ids)),
                )
            mappings = Mapping.search(mapping_domain)
        else:
            mappings = location_mappings.sudo().exists()
            if scope_store_ids:
                mappings = mappings.filtered(
                    lambda mapping: mapping.store_id.id in scope_store_ids
                )
            mappings = mappings.filtered(
                lambda mapping: (
                    mapping.status == 'active'
                    and mapping.push_enabled
                    and
                    isinstance(mapping.shopify_gid, str)
                    and bool(mapping.shopify_gid.strip())
                )
            )
        if location_mappings is None:
            mappings = mappings.filtered(
                lambda mapping: (
                    mapping.status == 'active' and mapping.push_enabled
                )
            )

        if not variants or not mappings:
            return LevelBinding.browse()

        mappings_by_store = {}
        for mapping in mappings:
            mappings_by_store.setdefault(mapping.store_id.id, Mapping.browse())
            mappings_by_store[mapping.store_id.id] |= mapping

        ensured = LevelBinding.browse()
        for variant in variants:
            store_record = variant.store_id
            if not store_record or not store_record.company_id:
                _logger.warning(
                    'Inventory pair bootstrap skipped variant binding %s: '
                    'the owning store has no company.', variant.id,
                )
                continue
            inventory_item_gid = variant.shopify_inventory_item_gid
            if not isinstance(inventory_item_gid, str):
                continue
            inventory_item_gid = inventory_item_gid.strip()
            if not inventory_item_gid:
                continue

            product = variant.product_variant_id
            for mapping in mappings_by_store.get(
                store_record.id, Mapping.browse(),
            ):
                location = mapping.odoo_location_id
                store_company = store_record.company_id
                if (
                    product.company_id and
                    product.company_id != store_company
                ) or (
                    location.company_id and
                    location.company_id != store_company
                ):
                    # The pair must fail closed rather than relying on the
                    # current worker company (which may differ from the
                    # store's company in a multi-company cron run).
                    _logger.warning(
                        'Inventory pair bootstrap skipped variant binding '
                        '%s and location mapping %s: company scope does not '
                        'match store %s.', variant.id, mapping.id,
                        store_record.id,
                    )
                    continue

                pair_domain = [
                    ('store_id', '=', store_record.id),
                    ('product_variant_binding_id', '=', variant.id),
                    ('location_mapping_id', '=', mapping.id),
                ]
                existing = LevelBinding.search(pair_domain, limit=1)
                if existing:
                    if (
                        existing.shopify_inventory_item_gid
                        == inventory_item_gid
                    ):
                        ensured |= existing
                    else:
                        # The binding identity is immutable.  Do not repair a
                        # conflicting legacy row by silently changing the
                        # stored GID; a reviewed recovery must do that.
                        _logger.error(
                            'Inventory pair bootstrap found conflicting '
                            'InventoryItem identity for level binding %s; '
                            'leaving it unchanged.', existing.id,
                        )
                    continue

                vals = {
                    'store_id': store_record.id,
                    'product_variant_binding_id': variant.id,
                    'location_mapping_id': mapping.id,
                    'shopify_inventory_item_gid': inventory_item_gid,
                }
                try:
                    with self.env.cr.savepoint():
                        created = LevelBinding.with_company(
                            store_company
                        ).create(vals)
                except IntegrityError:
                    # Another import/mapping transition may have created the
                    # exact row between the search and insert.  Re-read after
                    # the savepoint; only the exact same pair/GID is benign.
                    created = LevelBinding.search(pair_domain, limit=1)
                    if not created:
                        raise
                    if (
                        created.shopify_inventory_item_gid
                        != inventory_item_gid
                    ):
                        _logger.error(
                            'Inventory pair bootstrap raced with a '
                            'conflicting InventoryItem identity for pair '
                            'variant=%s mapping=%s.', variant.id, mapping.id,
                        )
                        continue
                ensured |= created
        return ensured

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
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                "Only a Shopify Connector Administrator may create an "
                "inventory-level binding."
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
        if variant_binding.status != 'active':
            raise UserError(
                "The product-variant binding is not active and cannot "
                "create an inventory pair."
            )
        if (
            location_mapping.status != 'active'
            or not location_mapping.push_enabled
        ):
            raise UserError(
                "The location mapping must be active and push-enabled "
                "before an inventory pair can be created."
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
    def _handoff_supersede(
        self, job, binding, cancel_reason, new_job_type,
        is_cas_replacement=False,
    ):
        """Handoffs C/D (DEC-037 §5.4): cancel `job`, superseding it with
        one atomically-created replacement of `new_job_type`, under the
        pair's row lock. Both writes occur in the transaction already
        open at C3/reconciliation-consequence-apply time.

        A CAS replacement (`is_cas_replacement=True`) is always created
        through `_create_cas_successor_job`, which itself derives the
        ordinal from this exact locked predecessor -- never accepted as
        a caller-supplied ordinal here (PR #182 comment 5029906989 item
        6): no caller may request an arbitrary jump, and
        `_create_inventory_job` itself accepts no such parameter at all.
        Every other handoff (reconciliation-not-applied, manual-review
        release) always creates its replacement at ordinal 0 via the
        ordinary `_create_inventory_job`, regardless of the
        predecessor's own ordinal -- a non-CAS replacement never
        inherits a nonzero ordinal.
        """
        locked_job = job.try_lock_for_update()
        if not locked_job:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'The predecessor job is held by another worker; retry '
                'later.',
            )
        locked_job.invalidate_recordset()
        from_state = locked_job.state
        # A manual-review release supersedes a job in `blocked_manual_review`,
        # which still carries a `manual_review_subreason`. Core's
        # `_check_manual_review_subreason` constraint requires that field to
        # be empty in every non-blocked state, so it must be cleared as part
        # of the same transition to `cancelled` (the CAS/reconciliation
        # supersede paths already carry an empty subreason, so this is a
        # no-op for them).
        locked_job.sudo().write({
            'state': 'cancelled',
            'cancel_reason': cancel_reason,
            'manual_review_subreason': False,
        })
        # Flush so this job's operation_scope_key clears (terminal state)
        # before the replacement job's own scope key is computed --
        # otherwise the two would momentarily collide on the DB unique
        # constraint within this same transaction.
        locked_job.flush_recordset(['state', 'operation_scope_key'])
        if is_cas_replacement:
            new_job = self._create_cas_successor_job(
                locked_job, binding, allow_ineligible=True,
            )
        else:
            new_job = self._create_inventory_job(
                locked_job.store_id, locked_job.job_source, new_job_type,
                binding, trigger_origin=locked_job.trigger_origin or False,
                allow_ineligible=True,
            )
        if not new_job:
            locked_job._log_transition(
                'state_change',
                'Replacement %s was suppressed because the inventory pair '
                'became ineligible after the predecessor was terminalized; '
                'predecessor_job_id=%d.' % (cancel_reason, locked_job.id),
                from_state=from_state, to_state='cancelled',
            )
            return self.env['shopify.connector.job']
        locked_job.sudo().write({'superseded_by_job_id': new_job.id})
        locked_job._log_transition(
            'state_change',
            'Superseded by a replacement job (%s); predecessor_job_id=%d '
            'successor_job_id=%d.' % (
                cancel_reason, locked_job.id, new_job.id,
            ),
            from_state=from_state, to_state='cancelled',
        )
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
        job.flush_recordset(['state', 'operation_scope_key'])
        new_job = self._create_inventory_job(
            job.store_id, job.job_source, JOB_TYPE_PUSH_SYNC, binding,
            trigger_origin=job.trigger_origin or False,
            allow_ineligible=True,
        )
        if not new_job:
            job._log_transition(
                'state_change',
                'Activation confirmed applied; the fresh push-sync '
                'successor was suppressed because the pair became '
                'ineligible. predecessor_job_id=%d.' % (job.id,),
            )
            return self.env['shopify.connector.job']
        job._log_transition(
            'state_change',
            'Activation confirmed applied; atomically enqueued a fresh '
            'inventory_push_sync; predecessor_job_id=%d '
            'successor_job_id=%d.' % (job.id, new_job.id),
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
            binding.store_id.id != local_snapshot['store_id']
            or not self._binding_operationally_eligible(binding)
        ):
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'The inventory pair is no longer operationally eligible: '
                'its level binding, variant binding, or location mapping is '
                'inactive, disabled, or outside the owning store/company '
                'scope; no Shopify work may proceed.',
            )
        if (
            not local_snapshot['inventory_item_gid']
            or not local_snapshot['location_gid']
        ):
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE_RISK,
                'Missing a required Shopify identifier before transport.',
            )

        read = self._read_shopify_inventory_pair(
            self.env['shopify.connector.job'].browse(job_id), store, binding,
        )

        if read['store_identity'] != local_snapshot['expected_store_identity']:
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_STORE_IDENTITY, SUBREASON_STORE_IDENTITY,
                'Fresh pre-C2 read observed a different Shopify store '
                'identity.',
            )
        if not read['item_exists']:
            # A stale or recreated InventoryItem identity discovered by
            # the fresh pre-C2 read (PR #182 comment 5028910116 item 1):
            # fails closed through the existing binding_conflict review
            # route, never treated as a missing level.
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'Fresh pre-C2 read found the Shopify inventory item no '
                'longer exists (a stale or recreated identity).',
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

        # Real InventoryLevel GID persistence (PR #182 comment
        # 5028910116 item 2): opportunistically capture it when the
        # binding is still empty (this fresh read already proves it);
        # a conflicting already-recorded value fails closed here --
        # still pre-C2, nothing has been committed yet -- rather than
        # silently overwriting a recorded identity.
        observed_level_gid = read.get('inventory_level_gid')
        if observed_level_gid and binding.shopify_gid:
            if binding.shopify_gid != observed_level_gid:
                self._fail_closed_pre_c2(
                    job_id, ERROR_CLASS_DATA_SHAPE, SUBREASON_BINDING_CONFLICT,
                    'Fresh pre-C2 read observed an InventoryLevel GID '
                    'that conflicts with the already-recorded value.',
                )
        elif observed_level_gid and not binding.shopify_gid:
            binding.sudo().write({'shopify_gid': observed_level_gid})

        # Defensive strict-integer re-validation at this exact callback
        # boundary (PR #182 comment 5029906989 item 8): `read['available']`
        # is already `_strict_shopify_int`-validated by the real
        # `_read_shopify_inventory_pair`, but a mocked/overridden read in
        # a test or future extension must never let a non-integer value
        # silently become `changeFromQuantity` in the mutation request.
        try:
            change_from_quantity = _strict_shopify_int(read['available'])
        except ValueError:
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_DATA_SHAPE, SUBREASON_BINDING_CONFLICT,
                'The pre-C2 read did not return a strict integer '
                '"available" quantity; refusing to build a Shopify '
                'mutation request.',
            )
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
                    'changeFromQuantity': change_from_quantity,
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
                'change_from_quantity': change_from_quantity,
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
        input_vars = request.get('variables', {}).get('input', {})
        requested_target = (
            (input_vars.get('quantities') or [{}])[0].get('quantity')
        )
        requested_reason = input_vars.get('reason')
        requested_reference_uri = input_vars.get('referenceDocumentUri')
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
                    # Preserve the raw returned value -- never default a
                    # missing/malformed container to `[]` here; the
                    # classifier is the single place that validates shape
                    # (PR #182 comment 5030514895 item 2).
                    'user_errors': payload.get('userErrors'),
                    'adjustment_group': payload.get('inventoryAdjustmentGroup'),
                    'requested_target': requested_target,
                    'requested_reason': requested_reason,
                    'requested_reference_uri': requested_reference_uri,
                    'evidence': {'transport': 'inventorySetQuantities'},
                }
        except Exception as exc:
            return {
                'outcome': 'uncertain',
                'error_class': _normalize_transport_error_class(exc),
                'evidence': {'exception_class': type(exc).__name__},
            }

    @api.model
    def _is_valid_set_quantities_success(
        self, group, expected_target, expected_reason,
        expected_reference_uri,
    ):
        """Direct-success evidence gate (PR #182 comment 5025765389 item
        6; strict-integer/no-duplicate/exact-request corrections per
        comment 5028910116 item 4; non-empty-value correction per
        comment 5029906989 item 8): an empty `userErrors` list alone is
        never sufficient. Requires a non-null adjustment group, a
        non-empty, exactly-matching `reason`/`referenceDocumentUri` --
        two missing values comparing equal (`None == None`) is never
        valid success evidence -- exactly one change (never a duplicate
        or extra quantity-name change), that change named `available`,
        and its `quantityAfterChange` a strict integer exactly equal to
        the requested target -- `int(...)` is never used as a
        permissive coercion here."""
        if not isinstance(group, dict):
            return False
        if not isinstance(expected_reason, str) or not expected_reason:
            return False
        returned_reason = group.get('reason')
        if (
            not isinstance(returned_reason, str) or not returned_reason
            or returned_reason != expected_reason
        ):
            return False
        if (
            not isinstance(expected_reference_uri, str)
            or not expected_reference_uri
        ):
            return False
        returned_reference_uri = group.get('referenceDocumentUri')
        if (
            not isinstance(returned_reference_uri, str)
            or not returned_reference_uri
            or returned_reference_uri != expected_reference_uri
        ):
            return False
        changes = group.get('changes')
        if not isinstance(changes, list) or len(changes) != 1:
            return False
        change = changes[0]
        if not isinstance(change, dict) or change.get('name') != 'available':
            return False
        if not isinstance(expected_target, int) or isinstance(
            expected_target, bool
        ):
            return False
        try:
            quantity_after = _strict_shopify_int(
                change.get('quantityAfterChange')
            )
        except ValueError:
            return False
        return quantity_after == expected_target

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
        user_errors = result.get('user_errors')
        evidence = dict(result.get('evidence') or {})
        # A malformed falsey container (`{}`, `''`, `0`, `False`, `None`,
        # a tuple, a bare string) must never be coerced into an empty
        # list via `or []` -- that would let a malformed response reach
        # the success validator as an apparent clean pass (PR #182
        # comment 5030514895 item 2). The container's shape is validated
        # before its emptiness is ever checked.
        if not isinstance(user_errors, list):
            return {
                'observed_outcome': 'uncertain',
                'error_class': ERROR_CLASS_DATA_SHAPE,
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': 'inventorySetQuantities returned a malformed '
                            'userErrors container (not a list); '
                            'reconciling before trusting either '
                            'disposition.',
                'evidence': evidence,
            }
        if not user_errors:
            group = result.get('adjustment_group')
            expected_target = result.get('requested_target')
            if not self._is_valid_set_quantities_success(
                group, expected_target, result.get('requested_reason'),
                result.get('requested_reference_uri'),
            ):
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
            evidence['reason'] = group.get('reason')
            evidence['reference_document_uri'] = group.get(
                'referenceDocumentUri'
            )
            evidence['quantity_after_change'] = (
                group['changes'][0]['quantityAfterChange']
            )
            return {
                'observed_outcome': 'succeeded',
                'error_class': False,
                'manual_review_subreason': False,
                'action': 'succeed',
                'message': 'inventorySetQuantities applied.',
                'evidence': evidence,
            }
        # A non-null adjustment group alongside userErrors is ambiguous
        # -- never a clean rejection (PR #182 comment 5028910116 item 4).
        if result.get('adjustment_group') is not None:
            return {
                'observed_outcome': 'uncertain',
                'error_class': ERROR_CLASS_DATA_SHAPE,
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': 'inventorySetQuantities returned both '
                            'userErrors and a non-null adjustment group; '
                            'ambiguous, reconciling before trusting '
                            'either.',
                'evidence': evidence,
            }
        # Strict structured evidence shape `[{code, field}]` (PR #182
        # comment 5029906989 item 7) -- replaces the free-form
        # `user_error_codes` list entirely; never persists message text.
        # A malformed entry (missing/non-string code, malformed field)
        # is never trusted for a clean rejection -- ambiguous, reconcile
        # first.
        sanitized_errors, errors_ok = _validate_structured_user_errors(
            user_errors, code_required=True,
        )
        if not errors_ok:
            return {
                'observed_outcome': 'uncertain',
                'error_class': ERROR_CLASS_DATA_SHAPE,
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': 'inventorySetQuantities returned a malformed '
                            'userErrors shape; reconciling before '
                            'trusting either disposition.',
                'evidence': evidence,
            }
        evidence['user_errors'] = sanitized_errors
        codes = {entry['code'] for entry in sanitized_errors}
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
    def _reconcile_set_quantities(self, attempt, reconciliation_job=None):
        store = attempt.store_id
        binding = self.env[
            'shopify.connector.inventory.level.binding'
        ].search([('id', '=', attempt.job_id.res_id)], limit=1)
        read = self._read_shopify_inventory_pair(
            reconciliation_job or attempt.job_id, store, binding,
        )
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
        if not read['item_exists']:
            # A stale or recreated InventoryItem identity discovered
            # during reconciliation (PR #182 comment 5028910116 item 1):
            # fails closed through the existing binding_conflict review
            # route, never left to loop as inconclusive.
            return {
                'verdict': 'not_applied',
                'observed_store_identity': read['store_identity'] or '',
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_VALIDATION,
                'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
                'message': 'Reconciliation found the Shopify inventory '
                            'item no longer exists (a stale or recreated '
                            'identity).',
                'evidence': {},
            }
        if not read['level_exists']:
            # A set-quantities effect cannot be applied to a nonexistent
            # InventoryLevel (PR #182 comment 5029906989 item 9): routed
            # fail closed through the accepted inventory-location-
            # missing/not_applied consequence instead of falling through
            # to a generic `current=None` comparison, which would
            # otherwise consume the bounded inconclusive-retry budget by
            # looping as `inconclusive` forever.
            return {
                'verdict': 'not_applied',
                'observed_store_identity': read['store_identity'] or '',
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_LOCATION_MISSING,
                'manual_review_subreason': SUBREASON_LOCATION_MISSING,
                'message': 'Reconciliation found no Shopify inventory '
                            'level exists for this pair; activation is '
                            'required before quantities can be set.',
                'evidence': {},
            }
        target = (attempt.preconditions_snapshot or {}).get('target_quantity')
        pre_attempt = (attempt.preconditions_snapshot or {}).get(
            'change_from_quantity'
        )
        current = read['available']
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
                'evidence': {
                    'current': current, 'target': target,
                    'inventory_level_gid': read.get('inventory_level_gid'),
                },
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
        if (
            consequence['action'] == 'succeed'
            and not self._binding_scope_compatible(
                binding, expected_store=job.store_id,
            )
        ):
            raise ValidationError(
                'Inventory quantity evidence cannot be recorded for a '
                'binding outside the job store/company scope.'
            )
        domain_payload = consequence.get('domain_payload') or {}
        if phase == 'direct' and domain_payload.get('reason') == 'cas_stale':
            if not self._binding_operationally_eligible(binding):
                self._block_pair(
                    job, ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                    'The inventory pair is no longer operationally eligible; '
                    'no CAS replacement may be created until its level, '
                    'variant, and location bindings are active and in scope.',
                )
                return
            if self._binding_push_admission_blocked(binding):
                self._block_pair(
                    job, ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                    'This inventory pair is flagged %s; no CAS '
                    'replacement may be created until it is '
                    'reviewed.' % (binding.status,),
                )
                return
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
                JOB_TYPE_SET_QUANTITIES, is_cas_replacement=True,
            )
            return
        if phase == 'reconciliation' and consequence['action'] == 'domain_callback':
            # not_applied reconciliation verdict -> new same-domain job.
            # Never a CAS replacement -- always ordinal 0, regardless of
            # this job's own possibly-nonzero ordinal (PR #182 comment
            # 5028910116 item 7).
            if not self._binding_operationally_eligible(binding):
                self._block_pair(
                    job, ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                    'The inventory pair is no longer operationally eligible; '
                    'no reconciliation replacement may be created until its '
                    'level, variant, and location bindings are active and '
                    'in scope.',
                )
                return
            if self._binding_push_admission_blocked(binding):
                self._block_pair(
                    job, ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                    'This inventory pair is flagged %s; no '
                    'reconciliation replacement may be created until it '
                    'is reviewed.' % (binding.status,),
                )
                return
            self._handoff_supersede(
                job, binding, 'reconciliation_not_applied_replacement',
                JOB_TYPE_SET_QUANTITIES,
            )
            return
        if consequence['action'] == 'succeed':
            write_vals = {
                'last_pushed_available': (
                    attempt.preconditions_snapshot or {}
                ).get('target_quantity'),
                'last_pushed_at': fields.Datetime.now(),
            }
            # Real InventoryLevel GID persistence, never a synthetic
            # composite identity (PR #182 comment 5028910116 item 2). A
            # conflicting already-recorded GID fails closed by flagging
            # the binding for review instead of silently overwriting it
            # -- the mutation itself already succeeded and this job is
            # already terminal, so the disposition cannot itself block.
            observed_gid = (consequence.get('evidence') or {}).get(
                'inventory_level_gid'
            )
            if observed_gid and not binding.shopify_gid:
                write_vals['shopify_gid'] = observed_gid
            elif (
                observed_gid and binding.shopify_gid
                and binding.shopify_gid != observed_gid
            ):
                write_vals['status'] = 'review'
                _logger.warning(
                    'Inventory-level binding %d: observed InventoryLevel '
                    'GID differs from the recorded value after a '
                    'successful inventorySetQuantities; flagged for '
                    'review rather than silently overwritten.',
                    binding.id,
                )
            binding.sudo().write(write_vals)

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
        """A fresh, narrow pre-C2 Shopify pair read immediately before
        this attempt's own C2 (PR #182 comment 5029906989 item 3):
        `inventory_activate` previously validated only local GIDs and
        went straight to transport, so a topology/identity race between
        orchestration and this dispatch could still reach Shopify with a
        stale disposition.

        Mirrors `_prepare_preconditions_set_quantities`'s gate exactly:
        a different store identity, a missing/recreated item, an item
        that has gone untracked, or a conflicting already-recorded
        InventoryLevel GID all fail closed via `_fail_closed_pre_c2` --
        no mutation-attempt row is ever created. When the fresh read
        instead finds a valid level already exists, sending an
        activation mutation is never safe (it would either fail or
        silently reset a level another actor already established) --
        `InventoryActivationSupersededError` signals the dedicated
        non-committing recovery seam to skip this job and hand off to a
        fresh orchestration read instead, with no attempt and no
        transport.
        """
        job_id = local_snapshot['job_id']
        if (
            not local_snapshot['inventory_item_gid']
            or not local_snapshot['location_gid']
        ):
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE_RISK,
                'Missing a required Shopify identifier before transport.',
            )

        store = self.env['shopify.connector.store'].browse(
            local_snapshot['store_id']
        )
        binding = self.env['shopify.connector.inventory.level.binding'].browse(
            local_snapshot['binding_id']
        )
        if (
            binding.store_id.id != local_snapshot['store_id']
            or not self._binding_operationally_eligible(binding)
        ):
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'The inventory pair is no longer operationally eligible: '
                'its level binding, variant binding, or location mapping is '
                'inactive, disabled, or outside the owning store/company '
                'scope; no Shopify work may proceed.',
            )
        read = self._read_shopify_inventory_pair(
            self.env['shopify.connector.job'].browse(job_id), store, binding,
        )

        if read['store_identity'] != local_snapshot['expected_store_identity']:
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_STORE_IDENTITY, SUBREASON_STORE_IDENTITY,
                'Fresh pre-C2 read observed a different Shopify store '
                'identity.',
            )
        if not read['item_exists']:
            # A stale or recreated InventoryItem identity discovered by
            # the fresh pre-C2 read (PR #182 comment 5028910116 item 1):
            # fails closed through the existing binding_conflict review
            # route.
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'Fresh pre-C2 read found the Shopify inventory item no '
                'longer exists (a stale or recreated identity).',
            )
        if read['tracked'] is False:
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_LOCATION_MISSING,
                SUBREASON_LOCATION_MISSING,
                'Fresh pre-C2 read found the Shopify inventory item is no '
                'longer tracked.',
            )

        observed_level_gid = read.get('inventory_level_gid')
        if (
            observed_level_gid and binding.shopify_gid
            and binding.shopify_gid != observed_level_gid
        ):
            self._fail_closed_pre_c2(
                job_id, ERROR_CLASS_DATA_SHAPE, SUBREASON_BINDING_CONFLICT,
                'Fresh pre-C2 read observed an InventoryLevel GID that '
                'conflicts with the already-recorded value.',
            )

        if read['level_exists']:
            # A valid InventoryLevel already exists for this pair --
            # activation is no longer necessary or safe to send (PR
            # #182 comment 5029906989 item 3). No mutation is sent, no
            # attempt row is created.
            raise InventoryActivationSupersededError(observed_level_gid)

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
                    # Preserve the raw returned value -- never default a
                    # missing/malformed container to `[]` here; the
                    # classifier is the single place that validates shape
                    # (PR #182 comment 5030514895 item 2).
                    'user_errors': payload.get('userErrors'),
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
        7; strict-integer/non-empty-GID/no-duplicate corrections per
        comment 5028910116 items 2/4): a non-null `InventoryLevel` alone
        is never sufficient -- requires a non-empty InventoryLevel GID,
        the returned item/location matching exactly what was requested,
        exactly one valid `available` quantity entry (never a duplicate
        or malformed one), and that quantity a strict integer exactly
        zero. `int(...)` is never used as a permissive coercion here."""
        if not isinstance(level, dict):
            return False
        inventory_level_gid = level.get('id')
        if not isinstance(inventory_level_gid, str) or not inventory_level_gid:
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
        quantities = level.get('quantities')
        if not isinstance(quantities, list) or len(quantities) != 1:
            return False
        quantity = quantities[0]
        if not isinstance(quantity, dict) or quantity.get('name') != 'available':
            return False
        try:
            value = _strict_shopify_int(quantity.get('quantity'))
        except ValueError:
            return False
        return value == 0

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
        user_errors = result.get('user_errors')
        level = result.get('inventory_level')
        evidence = dict(result.get('evidence') or {})
        # A malformed falsey container (`{}`, `''`, `0`, `False`, `None`,
        # a tuple, a bare string) must never be coerced into an empty
        # list via `or []` -- that would let a malformed response reach
        # the success validator as an apparent clean pass (PR #182
        # comment 5030514895 item 2). The container's shape is validated
        # before its emptiness is ever checked.
        if not isinstance(user_errors, list):
            return {
                'observed_outcome': 'uncertain',
                'error_class': ERROR_CLASS_DATA_SHAPE,
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': 'inventoryActivate returned a malformed '
                            'userErrors container (not a list); '
                            'reconciling before trusting either '
                            'disposition.',
                'evidence': evidence,
            }
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
            # Real InventoryLevel GID persistence, never a synthetic
            # composite identity (PR #182 comment 5028910116 item 2).
            evidence['inventory_level_gid'] = level.get('id')
            return {
                'observed_outcome': 'succeeded',
                'error_class': False,
                'manual_review_subreason': False,
                'action': 'succeed',
                'message': 'inventoryActivate applied.',
                'evidence': evidence,
            }
        # Strict `field`-shape validation (PR #182 comment 5029906989
        # item 7) -- inventoryActivate's userErrors carry no structured
        # `code` in the 2026-07 schema, so classification here stays
        # payload-shape-only, but a malformed entry is still never
        # trusted for a clean rejection; never persists message text.
        sanitized_errors, errors_ok = _validate_structured_user_errors(
            user_errors, code_required=False,
        )
        if not errors_ok:
            return {
                'observed_outcome': 'uncertain',
                'error_class': ERROR_CLASS_DATA_SHAPE,
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': 'inventoryActivate returned a malformed '
                            'userErrors shape; reconciling before '
                            'trusting either disposition.',
                'evidence': evidence,
            }
        evidence['user_errors'] = sanitized_errors
        if level is None:
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
    def _reconcile_activate(self, attempt, reconciliation_job=None):
        store = attempt.store_id
        binding = self.env[
            'shopify.connector.inventory.level.binding'
        ].search([('id', '=', attempt.job_id.res_id)], limit=1)
        read = self._read_shopify_inventory_pair(
            reconciliation_job or attempt.job_id, store, binding,
        )
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
        if not read['item_exists']:
            # A stale or recreated InventoryItem identity discovered
            # during reconciliation (PR #182 comment 5028910116 item 1):
            # fails closed through the existing binding_conflict review
            # route, never left to loop as inconclusive.
            return {
                'verdict': 'not_applied',
                'observed_store_identity': read['store_identity'] or '',
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_VALIDATION,
                'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
                'message': 'Reconciliation found the Shopify inventory '
                            'item no longer exists (a stale or recreated '
                            'identity).',
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
                'evidence': {
                    'available': read['available'],
                    'inventory_level_gid': read.get('inventory_level_gid'),
                },
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
        if (
            consequence['action'] == 'succeed'
            and not self._binding_scope_compatible(
                binding, expected_store=job.store_id,
            )
        ):
            raise ValidationError(
                'Inventory activation evidence cannot be recorded for a '
                'binding outside the job store/company scope.'
            )
        if phase == 'reconciliation' and consequence['action'] == 'domain_callback':
            if not self._binding_operationally_eligible(binding):
                self._block_pair(
                    job, ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                    'The inventory pair is no longer operationally eligible; '
                    'no reconciliation replacement may be created until its '
                    'level, variant, and location bindings are active and '
                    'in scope.',
                )
                return
            if self._binding_push_admission_blocked(binding):
                self._block_pair(
                    job, ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                    'This inventory pair is flagged %s; no '
                    'reconciliation replacement may be created until it '
                    'is reviewed.' % (binding.status,),
                )
                return
            self._handoff_supersede(
                job, binding, 'reconciliation_not_applied_replacement',
                JOB_TYPE_ACTIVATE,
            )
            return
        if consequence['action'] == 'succeed':
            write_vals = {
                'last_pushed_available': 0.0,
                'last_pushed_at': fields.Datetime.now(),
            }
            # Real InventoryLevel GID persistence, never a synthetic
            # composite identity (PR #182 comment 5028910116 item 2). A
            # conflicting already-recorded GID fails closed by flagging
            # the binding for review instead of silently overwriting it
            # -- the mutation itself already succeeded and this job is
            # already terminal, so the disposition cannot itself block.
            observed_gid = (consequence.get('evidence') or {}).get(
                'inventory_level_gid'
            )
            if observed_gid and not binding.shopify_gid:
                write_vals['shopify_gid'] = observed_gid
            elif (
                observed_gid and binding.shopify_gid
                and binding.shopify_gid != observed_gid
            ):
                write_vals['status'] = 'review'
                _logger.warning(
                    'Inventory-level binding %d: observed InventoryLevel '
                    'GID differs from the recorded value after a '
                    'successful inventoryActivate; flagged for review '
                    'rather than silently overwritten.', binding.id,
                )
            binding.sudo().write(write_vals)
            # A post-mutation GID conflict must create no successor
            # (PR #182 comment 5029906989 item 4): the fresh orchestration
            # handoff below is skipped whenever this outcome flagged the
            # binding for review rather than cleanly recording the GID.
            if write_vals.get('status') != 'review':
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
        binding = self.env[
            'shopify.connector.inventory.level.binding'
        ].browse(original.res_id).exists()
        if (
            not binding
            or original.res_model
            != 'shopify.connector.inventory.level.binding'
            or binding.store_id != job.store_id
            or not self._binding_operationally_eligible(binding)
        ):
            Dispatch._block_original_job(
                original, ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'Reconciliation was refused because the inventory pair is '
                'no longer operationally eligible; no Shopify read or '
                'mutation was sent.',
            )
            Dispatch._complete_reconciliation_job(
                job, 'Ineligible inventory pair was routed to review.',
            )
            return
        # Reconciliation is also a repair boundary for installations that
        # were upgraded with product/location identity but without the
        # derived inventory-level pair.  This is idempotent and does not
        # alter the mutation attempt being reconciled.
        self._bootstrap_inventory_level_bindings(store=job.store_id)
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
        # Exception ordering, specific to general (LL-013; PR #182
        # comment 5028910116 item 9): execution of the reconciliation
        # read is a SEPARATE try block from validation/normalization of
        # its returned structure. A `JobHandlerError` a strategy raises,
        # a genuine PostgreSQL concurrency failure, or any other
        # transient read-execution exception must retry through the
        # ordinary read-safe job path -- never be misclassified as
        # malformed evidence and used to block the original job. Only a
        # result the strategy actually returns, but that fails schema
        # validation, blocks.
        try:
            result = strategy['reconcile'](attempt, job)
        except JobHandlerError:
            raise
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            raise
        except Exception as exc:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'The reconciliation read failed transiently; retry '
                'required.',
                type(exc).__name__,
            ) from exc
        try:
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
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            # Same-pattern audit (item 18): never wrap a genuine
            # PostgreSQL concurrency failure into JobHandlerError here --
            # doing so would route it through `_route_failure`'s ORM
            # write instead of the generic dispatcher's own aborted-
            # transaction-safe concurrency recovery.
            raise
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
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                "Only a Shopify Connector Administrator may "
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

        # An ordinary mutation job's own attempt is never linked through
        # the reconciliation-job-owned `mutation_attempt_id` field (core's
        # `_check_reconciliation_attempt_link` constraint forbids it, and
        # it stays NULL for `inventory_set_quantities`/`inventory_activate`
        # jobs); it must be resolved by the attempt's forward `job_id`,
        # exactly as `_create_cas_successor_job` already does (PR #182
        # comment 5030781330). At most one attempt can ever exist per job
        # (the `(job_id)` unique index enforces it at C2 creation time),
        # so this search is required to resolve to exactly one -- zero
        # (no attempt) and the impossible duplicate both fail closed.
        attempt = self.env['shopify.connector.mutation.attempt'].sudo().search(
            [('job_id', '=', blocked_job.id)],
        )
        eligible = False
        if len(attempt) == 1 and attempt.observed_outcome == 'failed_clean' and (
            attempt.effective_disposition() == 'not_applied'
        ):
            subreason = blocked_job.manual_review_subreason
            if subreason == SUBREASON_LOCATION_MISSING:
                eligible = True
            elif subreason == SUBREASON_BINDING_CONFLICT:
                if blocked_job.error_class == ERROR_CLASS_CONCURRENCY:
                    # CAS-exhaustion release additionally requires the
                    # final attempt to have actually recorded an exact
                    # structured entry with code=CHANGE_FROM_QUANTITY_STALE
                    # -- ordinal alone is not proof (PR #182 comment
                    # 5028910116 item 8), and this checks the frozen
                    # structured `user_errors: [{code, field}]` evidence
                    # shape, never a substring or generic container
                    # membership test on a free-form list (PR #182
                    # comment 5029906989 item 7).
                    direct_evidence = (
                        (attempt.remote_evidence_refs or {}).get('direct')
                        or {}
                    )
                    structured_errors = direct_evidence.get('user_errors') or []
                    has_exact_stale_code = any(
                        isinstance(entry, dict)
                        and entry.get('code') == 'CHANGE_FROM_QUANTITY_STALE'
                        for entry in structured_errors
                    )
                    eligible = (
                        blocked_job.cas_retry_ordinal == MAX_CAS_RETRY_ORDINAL
                        and has_exact_stale_code
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

        # Secret AND PII-safe redaction (PR #182 comment 5028910116 item
        # 11) -- the binding mixin's `_audit_safe_reason` (already used
        # by `action_override_binding`) redacts credentials/tokens plus
        # emails/phone numbers, never just secrets.
        safe_reason = locked_binding._audit_safe_reason(reason)
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
