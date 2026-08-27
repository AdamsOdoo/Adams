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
# Frozen job-contract vocabulary (DEC-037 Â§7). Do not invent additional
# values. `error_class`/`manual_review_subreason` values used below are
# all already registered on `shopify.connector.job`'s core
# ERROR_CLASS_SELECTION / MANUAL_REVIEW_SUBREASON_SELECTION -- this
# module adds none.
# ----------------------------------------------------------------------
JOB_TYPE_PUSH_SYNC = 'inventory_push_sync'
JOB_TYPE_PUSH_SCAN = 'inventory_push_scan'
INVENTORY_PUSH_SCAN_BATCH = 200
JOB_TYPE_FIRST_PUSH_PREVIEW = 'inventory_first_push_preview'
JOB_TYPE_LOCATION_SYNC = 'inventory_location_sync'
JOB_TYPE_ACTIVATE = 'inventory_activate'
JOB_TYPE_SET_QUANTITIES = 'inventory_set_quantities'
# One new job_type this domain must add beyond the six named in DEC-037
# Â§7: a shared reconciliation-dispatch job_type for both mutation
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
# rule, PR #182 comment 5025765389 Â§16): harmless floating-point noise
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

# The three "pair execution" job types (DEC-037 Â§5.3): the only types
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
    """The frozen pair-serialization literal (DEC-037 Â§5.3)."""
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
    module's own fixed nine-value vocabulary (DEC-037 Â§7/Â§9).

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
    binding rule, PR #182 comment 5025765389 Â§16): 10.0 -> (10, True);
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
    # The only new, domain-owned job-lineage field (DEC-037 Â§5.1/Â§5.4/Â§7).
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
                'Not applicable â€” the inventory domain is not enabled for '
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
        the fast-path coalesce never fired and â€” worse â€” the
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

        Last-value-wins (DEC-037 Â§10): always overwrites, never queues.
        A genuinely negative `free_qty` is clamped to zero, and the true
        negative value is preserved in a warning log entry (control-room
        binding rule, PR #182 comment 5025765389 Â§16) -- never silently
        dropped.
        """
        target, free_qty = self._current_odoo_available(
            binding, include_unclamped=True,
        )
        binding.sudo().write({'pending_target_available': target})
        return target, free_qty

    @api.model
    def _current_odoo_available(self, binding, include_unclamped=False):
        """Read the pair's current Odoo-authoritative available quantity."""
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
        return (target, free_qty) if include_unclamped else target

    @api.model
    def _fail_closed_pre_c2(self, job_id, error_class, subreason, message):
        """Fail closed *before* C2 (PR #182 comment 5025803697 item 20 /
        comment 5025765389 Â§21; commit removed per comment 5028910116
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
            if binding.first_push_state != 'confirmed':
                self._admit_first_push_preview(binding)
                continue
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
            if binding.first_push_state != 'confirmed':
                enqueued |= self._admit_first_push_preview(binding)
                continue
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
        if not self.env.su and not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may start the '
                'scheduled inventory push scan outside the root cron '
                'environment.'
            )
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
        """Orchestration/read-only handler (DEC-037 Â§5.1.A/Â§5.2).

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
        # #182 comment 5029906989 item 4/Â§10): a re-check at dispatch
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
            self._refresh_pending_target(binding)
            job._transition_skipped(
                'First push is not confirmed; this push request ended '
                'without Shopify work and returned the pair to preview.',
            )
            self._admit_first_push_preview(binding)
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
            # is required before any quantity can be set. DEC-037 Â§5.4
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
                    'orchestration job was terminyï¾õ¶‰žËkºwµçBF—7F6‚åö&Æö6µö÷&–v–æÅö¦ö"€¢÷&–v–æÂÂU%$õ%ô4Ä55ôDDõ4„RÂ5T%$T4ôåôEUÄ”4DUõ$•4²À¢u&V6öæ6–Æ–F–öâ&VÖ–æVB–æ6öæ6ÇW6—fRBF†R6fWG’p¢v6ârÀ¢¢F—7F6‚åö6ö×ÆWFU÷&V6öæ6–Æ–F–öåö¦ö"€¢¦ö"Ât–æ6öæ6ÇW6—fR&V6öæ6–Æ–F–öâ&V6†VB—G26fWG’p¢v6ârÀ¢¢VÇ6S ¢¦ö"å÷G&ç6—F–öå÷&WG'•÷v—F–ær€¢f–VÆG2äFFWF–ÖRææ÷r‚’²F–ÖVFVÇF†Ö–çWFW3ÓR’À¢¦ö"ç&WG'•ö6÷VçB²À¢U%$õ%ô4Ä55õDTÕõ$%’À¢æ÷&ÖÆ—¦VE²vÖW76vRuÒÀ¢¢&WGW&à¢F—7÷6—F–öâÒ€¢vÆ–VBr–bæ÷&ÖÆ—¦VE²wfW&F–7BuÒÓÒvÆ–VBrVÇ6Rvæ÷EöÆ–VBp¢¢G'“ ¢v—F‚6VÆbæVçbæ7"ç6fWö–çB‚“ ¢GFV×Bå÷&V6÷&E÷&V6öæ6–Æ–F–öå÷&W7VÇB€¢F—7÷6—F–öâÂæ÷&ÖÆ—¦VE²vWf–FVæ6RuÒÀ¢¢F—7F6‚åöÇ•÷fÆ–FFVEö6öç6WVVæ6R€¢÷&–v–æÂÂGFV×BÂw&V6öæ6–Æ–F–öârÀ¢æ÷&ÖÆ—¦VE²v6öç6WVVæ6RuÒÂ7G&FVw’À¢&V6öæ6–Æ–F–öåö¦ö#Ö¦ö"À¢¢F—7F6‚åö6ö×ÆWFU÷&V6öæ6–Æ–F–öåö¦ö"€¢¦ö"Âu&VBÖöæÇ’×WFF–öâ&V6öæ6–Æ–F–öâ6ö×ÆWFVBârÀ¢¢W†6WBuô4ôä5U%$Tä5•ôU„4UD”ôå5õDõõ$UE%“ ¢26ÖR×GFW&âVF—B†—FVÒ‚“¢æWfW"w&vVçV–æP¢2÷7Fw&U5Â6öæ7W'&Væ7’f–ÇW&R–çFò¦ö$†æFÆW$W'&÷"†W&RÒÐ¢2Fö–ær6òv÷VÆB&÷WFR—BF‡&÷Vv‚÷&÷WFUöf–ÇW&Vw2õ$Ð¢2w&—FR–ç7FVBöbF†RvVæW&–2F—7F6†W"w2÷vâ&÷'FVBÐ¢2G&ç67F–öâ×6fR6öæ7W'&Væ7’&V6÷fW'’à¢&—6P¢W†6WBW†6WF–öâ2W†3 ¢&—6R¦ö$†æFÆW$W'&÷"€¢U%$õ%ô4Ä55õDTÕõ$%’À¢tFöÖ–2&V6öæ6–Æ–F–öâ6öç6WVVæ6Rf–ÆVC²&VB&WG'’p¢w&WV—&VBârÀ¢G—R†W†2’åõöæÖUõòÀ¢’g&öÒW†0 ¢2ÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÐ¢2&Wf–Wr×&VÆV6R&—fFR†VÇW"†FVÆVvFVBFò'’F†R&–æF–ærw0¢2V&Æ–27F–öå÷&V6†V6µö–çfVçF÷'•÷—"ÒÒDT2Ó3r*sRãR’à¢2ÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÐ ¢’æÖöFVÀ¢FVb÷&V6†V6µö–çfVçF÷'•÷—"‡6VÆbÂ&–æF–ærÂ&V6öâ“ ¢–bæ÷B6VÆbæVçbçW6W"æ†5öw&÷W€¢w6†÷–g•ö6öææV7F÷%ö6÷&Ræw&÷W÷6†÷–g•ö6öææV7F÷%öFÖ–âp¢“ ¢&—6R66W74W'&÷"€¢$öæÇ’6†÷–g’6öææV7F÷"FÖ–æ—7G&F÷"Ö’ ¢'&VÆV6R&Æö6¶VB–çfVçF÷'’—"â ¢¢–bæ÷B—6–ç7Fæ6R‡&V6öâÂ7G"’÷"æ÷B&V6öâç7G&—‚“ ¢&—6RW6W$W'&÷"‚$æöâÖV×G’&V6öâ—2&WV—&VBâ" ¢Æö6¶VEö&–æF–ærÒ&–æF–ærçG'•öÆö6µöf÷%÷WFFR‚¢–bæ÷BÆö6¶VEö&–æF–æs ¢&—6RW6W$W'&÷"€¢%F†—2–çfVçF÷'’—"—27W'&VçFÇ’†VÆB'’æ÷F†W" ¢&÷W&F–öã²G'’v–â6†÷'FÇ’â ¢¢Æö6¶VEö&–æF–æræ–çfÆ–FFU÷&V6÷&G6WB‚ ¢¦ö"Ò6VÆbæVçe²w6†÷–g’æ6öææV7F÷"æ¦ö"uÐ¢&Æö6¶VBÒ¦ö"ç6V&6‚…°¢‚w&W5öÖöFVÂrÂsÒrÂw6†÷–g’æ6öææV7F÷"æ–çfVçF÷'’æÆWfVÂæ&–æF–ærr’À¢‚w&W5ö–BrÂsÒrÂÆö6¶VEö&–æF–æræ–B’À¢‚v¦ö%÷G—RrÂv–ârÂ”ådTåDõ%•ô¤ô%õE•U2’À¢‚w7FFRrÂsÒrÂv&Æö6¶VEöÖçVÅ÷&Wf–Wrr’À¢Ò¢–bÆVâ†&Æö6¶VB’Ò ¢&—6RW6W$W'&÷"€¢$W†7FÇ’öæR7F—fR&Æö6¶VB–çfVçF÷'’¦ö"—2&WV—&VBf÷" ¢'F†—2—"†f÷VæBVB’â"RÆVâ†&Æö6¶VB¢¢&Æö6¶VEö¦ö"Ò&Æö6¶VBçG'•öÆö6µöf÷%÷WFFR‚¢–bæ÷B&Æö6¶VEö¦ö# ¢&—6RW6W$W'&÷"€¢%F†R&Æö6¶VB¦ö"—27W'&VçFÇ’†VÆB'’æ÷F†W"÷W&F–öã² ¢'G'’v–â6†÷'FÇ’â ¢¢&Æö6¶VEö¦ö"æ–çfÆ–FFU÷&V6÷&G6WB‚ ¢2â÷&F–æ'’×WFF–öâ¦ö"w2÷vâGFV×B—2æWfW"Æ–æ¶VBF‡&÷Vv€¢2F†R&V6öæ6–Æ–F–öâÖ¦ö"Ö÷væVB×WFF–öåöGFV×Eö–Ff–VÆB†6÷&Rw0¢2ö6†V6µ÷&V6öæ6–Æ–F–öåöGFV×EöÆ–æ¶6öç7G&–çBf÷&&–G2—BÂæ@¢2—B7F—2åTÄÂf÷"–çfVçF÷'•÷6WE÷VçF—F–W6ö–çfVçF÷'•ö7F—fFV ¢2¦ö'2“²—B×W7B&R&W6öÇfVB'’F†RGFV×Bw2f÷'v&B¦ö%ö–FÀ¢2W†7FÇ’2ö7&VFUö65÷7V66W76÷%ö¦ö&Ç&VG’FöW2…"3ƒ ¢26öÖÖVçBS3sƒ33’âBÖ÷7BöæRGFV×B6âWfW"W†—7BW"¦ö ¢2‡F†R†¦ö%ö–B–Væ—VR–æFW‚Væf÷&6W2—BB3"7&VF–öâF–ÖR’À¢26òF†—26V&6‚—2&WV—&VBFò&W6öÇfRFòW†7FÇ’öæRÒÒ¦W&ð¢2†æòGFV×B’æBF†R–×÷76–&ÆRGWÆ–6FR&÷F‚f–Â6Æ÷6VBà¢GFV×BÒ6VÆbæVçe²w6†÷–g’æ6öææV7F÷"æ×WFF–öâæGFV×BuÒç7VFò‚’ç6V&6‚€¢²‚v¦ö%ö–BrÂsÒrÂ&Æö6¶VEö¦ö"æ–B•ÒÀ¢¢VÆ–v–&ÆRÒfÇ6P¢–bÆVâ†GFV×B’ÓÒæBGFV×Bæö'6W'fVEö÷WF6öÖRÓÒvf–ÆVEö6ÆVâræB€¢GFV×BæVffV7F—fUöF—7÷6—F–öâ‚’ÓÒvæ÷EöÆ–VBp¢“ ¢7V'&V6öâÒ&Æö6¶VEö¦ö"æÖçVÅ÷&Wf–Wu÷7V'&V6öà¢–b7V'&V6öâÓÒ5T%$T4ôåôÄô4D”ôåôÔ•54”äs ¢VÆ–v–&ÆRÒG'VP¢VÆ–b7V'&V6öâÓÒ5T%$T4ôåô$”äD”äuô4ôädÄ”5C ¢–b&Æö6¶VEö¦ö"æW'&÷%ö6Æ72ÓÒU%$õ%ô4Ä55ô4ôä5U%$Tä5“ ¢242ÖW††W7F–öâ&VÆV6RFF—F–öæÆÇ’&WV—&W2F†P¢2f–æÂGFV×BFò†fR7GVÆÇ’&V6÷&FVBâW†7@¢27G'V7GW&VBVçG'’v—F‚6öFSÔ4„ätUôe$ôÕõTåD•E•õ5DÄP¢2ÒÒ÷&F–æÂÆöæR—2æ÷B&ööb…"3ƒ"6öÖÖVç@¢2S#ƒ“b—FVÒ‚’ÂæBF†—26†V6·2F†Rg&÷¦Và¢27G'V7GW&VBW6W%öW'&÷'3¢·¶6öFRÂf–VÆGÕÖWf–FVæ6P¢26†RÂæWfW"7V'7G&–ær÷"vVæW&–26öçF–æW ¢2ÖVÖ&W'6†—FW7Böâg&VRÖf÷&ÒÆ—7B…"3ƒ ¢26öÖÖVçBS#““c“ƒ’—FVÒr’à¢F—&V7EöWf–FVæ6RÒ€¢†GFV×Bç&VÖ÷FUöWf–FVæ6U÷&Vg2÷"·Ò’ævWB‚vF—&V7Br¢÷"·Ð¢¢7G'V7GW&VEöW'&÷'2ÒF—&V7EöWf–FVæ6RævWB‚wW6W%öW'&÷'2r’÷"µÐ¢†5öW†7E÷7FÆUö6öFRÒç’€¢—6–ç7Fæ6R†VçG'’ÂF–7B¢æBVçG'’ævWB‚v6öFRr’ÓÒt4„ätUôe$ôÕõTåD•E•õ5DÄRp¢f÷"VçG'’–â7G'V7GW&VEöW'&÷'0¢¢VÆ–v–&ÆRÒ€¢&Æö6¶VEö¦ö"æ65÷&WG'•ö÷&F–æÂÓÒÔ…ô45õ$UE%•ôõ$D”äÀ¢æB†5öW†7E÷7FÆUö6öFP¢¢VÆ–b&Æö6¶VEö¦ö"æW'&÷%ö6Æ72ÓÒU%$õ%ô4Ä55õdÄ”DD”ôã ¢VÆ–v–&ÆRÒG'VP ¢–bæ÷BVÆ–v–&ÆS ¢&—6RW6W$W'&÷"€¢%F†—2&Æö6¶VB¦ö"w2÷WF6öÖR—2æ÷BöæRöbF†R66W2 ¢&VÆ–v–&ÆRf÷"&VÆV6Rf–7F–öå÷&V6†V6µö–çfVçF÷'•÷—"â ¢%Væ6W'F–âÂGWÆ–6FR×&—6²Â–FV×÷FVæ7’Ö6öçG&7BÂ ¢'Vç&W6öÇfVB×&V6öæ6–Æ–F–öâÂ7F÷&RÖ–FVçF—G’ÖÖ—6ÖF6‚ÂæB ¢'VæW‡Æ–æVBÖG&–gBöæöç¦W&ò×÷7BÖ7F—fF–öâ66W2&WV—&R ¢'F†R7FvRFÖ–æ—7G&F÷"ÖöæÇ’ÖçVÂ&W6öÇWF–öâF‚ ¢&–ç7FVBâ ¢ ¢26V7&WBäB”’×6fR&VF7F–öâ…"3ƒ"6öÖÖVçBS#ƒ“b—FVÐ¢2’ÒÒF†R&–æF–ærÖ—†–âw2öVF—E÷6fU÷&V6öæ†Ç&VG’W6V@¢2'’7F–öåö÷fW'&–FUö&–æF–æv’&VF7G27&VFVçF–Ç2÷Fö¶Vç2ÇW0¢2VÖ–Ç2÷†öæRçVÖ&W'2ÂæWfW"§W7B6V7&WG2à¢6fU÷&V6öâÒÆö6¶VEö&–æF–æråöVF—E÷6fU÷&V6öâ‡&V6öâ¢æWuö¦ö"Ò6VÆbåö†æFöfe÷7WW'6VFR€¢&Æö6¶VEö¦ö"ÂÆö6¶VEö&–æF–ærÂvÖçVÅ÷&Wf–Wu÷&VÆV6RrÀ¢¤ô%õE•UõU4…õ5”ä2À¢¢öÆövvW"æ–æfò€¢t–çfVçF÷'’—"&Wf–Wr&VÆV6VB'’7F÷%÷V–CÒW3¢öÆEö¦ö#ÒW2p¢væWuö¦ö#ÒW2&V6öãÒW2rÀ¢6VÆbæVçbçV–BÂ&Æö6¶VEö¦ö"æ–BÂæWuö¦ö"æ–BÂ6fU÷&V6öâÀ¢¢&WGW&âG'VP