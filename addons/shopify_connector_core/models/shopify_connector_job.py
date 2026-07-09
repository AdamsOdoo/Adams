from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Shared with shopify_connector_job_log.py (from_state/to_state) so the two
# models can never drift apart on the job state vocabulary (DEC-009).
JOB_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('queued', 'Queued'),
    ('running', 'Running'),
    ('succeeded', 'Succeeded'),
    ('failed_final', 'Failed (Final)'),
    ('skipped', 'Skipped'),
    ('cancelled', 'Cancelled'),
    ('retry_waiting', 'Retry Waiting'),
    ('failed_retryable', 'Failed (Retryable)'),
    ('blocked_manual_review', 'Blocked - Manual Review'),
]

TERMINAL_JOB_STATES = ('succeeded', 'failed_final', 'skipped', 'cancelled')

# The Task 005 / DEC-022 §4.2 business-job source subset: job_source
# values representing business sync/write work, subject to store-state
# gating at both enqueue (create()) and execution (write() to 'running')
# time. setup_readiness_check/export_preview_dry_run, and any other
# source outside this tuple, remain ungated core/diagnostic sources --
# gating them on 'connected' would be circular, since they exist to
# determine connection/readiness state in the first place.
BUSINESS_JOB_SOURCES = (
    'webhook', 'manual_sync', 'scheduled_sync', 'reconciliation', 'odoo_event',
)

# The six DEC-009 §D.5.4 confirmation-required error classes, reused as
# both a subset of ERROR_CLASS_SELECTION and the full
# manual_review_subreason vocabulary.
MANUAL_REVIEW_SUBREASON_SELECTION = [
    ('ambiguous_match', 'Ambiguous Match'),
    ('binding_conflict', 'Binding Conflict'),
    ('duplicate_risk', 'Duplicate Risk'),
    ('destructive_write_guard_blocked', 'Destructive-Write Guard Blocked'),
    ('inventory_location_missing', 'Inventory Location Missing'),
    (
        'fulfillment_notification_confirmation_missing',
        'Fulfillment Notification Confirmation Missing',
    ),
]

ERROR_CLASS_SELECTION = [
    ('shopify_throttling_rate_limit', 'Shopify Throttling / Rate Limit'),
    ('shopify_temporary_server_network', 'Shopify Temporary / Server / Network'),
    ('shopify_permission_scope_auth', 'Shopify Permission / Scope / Auth'),
    ('shopify_user_errors_validation', "Shopify userErrors / Validation"),
    ('odoo_validation_configuration', 'Odoo Validation / Configuration'),
    ('mapping_missing', 'Mapping Missing'),
] + MANUAL_REVIEW_SUBREASON_SELECTION + [
    ('financial_total_mismatch', 'Financial Total Mismatch'),
    ('data_shape_schema_mismatch', 'Data Shape / Schema Mismatch'),
    ('concurrency_race_conflict', 'Concurrency / Race Conflict'),
    ('unknown_system_error', 'Unknown / System Error'),
]


class ShopifyConnectorJob(models.Model):
    """The job/log/error/retry substrate (core-naming-schema-planning.md §4.5).

    One record per logical sync operation, carrying current state, error
    class, retry counters, the idempotency key, and the DB-backed
    serialization-guard key. No Shopify API call, webhook, or domain sync
    logic is implemented here -- only the shared state-machine schema.
    """

    _name = 'shopify.connector.job'
    _description = 'Shopify Connector Job'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    job_source = fields.Selection(
        selection=[
            ('webhook', 'Webhook'),
            ('manual_sync', 'Manual Sync'),
            ('scheduled_sync', 'Scheduled Sync'),
            ('reconciliation', 'Reconciliation'),
            ('setup_readiness_check', 'Setup Readiness Check'),
            ('export_preview_dry_run', 'Export Preview Dry Run'),
            ('odoo_event', 'Odoo Event'),
        ],
        required=True,
        index=True,
        readonly=True,
    )
    trigger_origin = fields.Selection(
        selection=[
            ('inventory_stock_change', 'Inventory Stock Change'),
            ('fulfillment_picking_validation', 'Fulfillment Picking Validation'),
        ],
        readonly=True,
    )
    trigger_origin_event_ref = fields.Char(readonly=True)
    trigger_origin_event_at = fields.Datetime(readonly=True)
    job_type = fields.Selection(
        selection=[
            ('core_readiness_check', 'Core Readiness Check'),
            ('core_manual_maintenance', 'Core Manual Maintenance'),
            ('core_test_connection', 'Core Test Connection'),
            # Task 006C / Decision F (gate-opening proposal §6):
            # core/diagnostic-only, reserved solely for the dispatcher's
            # own registry/dispatch self-tests (shopify_connector_job_
            # dispatch.py) -- never dispatched to a live Shopify call,
            # never a template for a future domain job_type.
            ('core_dispatch_selftest', 'Core Dispatch Selftest'),
        ],
        required=True,
        index=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=JOB_STATE_SELECTION,
        required=True,
        index=True,
        default='draft',
        readonly=True,
    )
    error_class = fields.Selection(
        selection=ERROR_CLASS_SELECTION,
        index=True,
        readonly=True,
    )
    manual_review_subreason = fields.Selection(
        selection=MANUAL_REVIEW_SUBREASON_SELECTION,
        readonly=True,
    )
    retry_count = fields.Integer(default=0, readonly=True)
    next_retry_at = fields.Datetime(readonly=True)
    res_model = fields.Char(index=True, readonly=True)
    res_id = fields.Integer(index=True, readonly=True)
    shopify_target_gid = fields.Char(index=True, readonly=True)
    # payload_hash serves two purposes: a hash of the normalized outbound
    # payload for target-bearing domain jobs, and a per-run UUID4 nonce for
    # target-less job types (core_test_connection only, as of Task 003) so
    # that repeat runs do not collide under the (store_id, idempotency_key)
    # unique constraint. core_readiness_check shares the identical
    # target-less exposure but is not fixed by this task -- see TD-001
    # (docs/05-qa/technical-debt-register.md).
    payload_hash = fields.Char(readonly=True)
    # Not `required=True`: in Odoo 19 the initial INSERT of a new record
    # happens before its stored-computed fields are evaluated, so a
    # NOT NULL column here fails create() before `_compute_idempotency_key`
    # ever runs. `store_id` is always required, so the compute below still
    # always yields a non-empty value once the row exists -- the
    # `(store_id, idempotency_key)` unique constraint below still enforces
    # the same guarantee.
    idempotency_key = fields.Char(
        compute='_compute_idempotency_key',
        store=True,
        index=True,
        readonly=True,
    )
    operation_scope_key = fields.Char(
        compute='_compute_operation_scope_key',
        store=True,
        index=True,
        readonly=True,
    )
    enqueue_decisions = fields.Text(readonly=True)
    superseded_by_job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        readonly=True,
    )
    cancel_reason = fields.Char(readonly=True)
    started_at = fields.Datetime(readonly=True)
    finished_at = fields.Datetime(readonly=True)

    _store_idempotency_key_uniq = models.Constraint(
        'UNIQUE(store_id, idempotency_key)',
        'A job with this idempotency key already exists for this store.',
    )
    _store_operation_scope_key_uniq = models.Constraint(
        'UNIQUE(store_id, operation_scope_key)',
        'A non-terminal job already holds this operation scope for this store.',
    )

    @api.model
    def _is_business_job_source(self, job_source):
        """Whether `job_source` is one of the Task 005 business-gated sources.

        The one place future domain job-creation code should consult
        before assuming a job needs store-state gating -- keeps this
        list from drifting between callers (create()/write() below, and
        `shopify_connector_store.py`'s disconnect cancellation sweep).
        """
        return job_source in BUSINESS_JOB_SOURCES

    @api.model_create_multi
    def create(self, vals_list):
        """Enqueue-time store-state gating (Task 005 / DEC-022 §4.2).

        A business job (`job_source` in `BUSINESS_JOB_SOURCES`) may only
        be created for a store already in state `connected` -- regardless
        of the job's own initial `state` (draft/queued/running all
        gated alike). Core setup/readiness/test/maintenance jobs are
        exempt: they exist to determine connection/readiness state, so
        gating them on `connected` would be circular.
        """
        Store = self.env['shopify.connector.store']
        for vals in vals_list:
            if self._is_business_job_source(vals.get('job_source')):
                store = Store.browse(vals.get('store_id')).exists()
                if not store or store.state != 'connected':
                    raise ValidationError(
                        "A business job (job_source=%r) can only be "
                        "created for a store in state 'connected'." % (
                            vals.get('job_source'),
                        )
                    )
        return super().create(vals_list)

    def write(self, vals):
        """Execution/start-time gating (Task 005 / DEC-022 §4.2, plus
        Task 006C's domain-enabled hook below).

        Re-checks store state the moment a business job is about to
        start (`state` -> 'running') -- the fail-closed guard for the
        race between a job's creation and its execution, so a store
        disconnected after enqueue can never let a business job proceed
        to a live Shopify call. Writes to any other state (including
        `cancelled`, e.g. `action_disconnect`'s cancellation sweep) are
        never blocked by this check.

        Evaluates the *effective* post-write `job_source`/`job_type`/
        `store_id` -- i.e. the incoming `vals` value when present, the
        job's current value otherwise -- not the stale pre-write cache,
        so a single call that also changes `job_source`/`job_type`/
        `store_id` alongside `state` cannot slip a job past either gate
        below by changing identity in the same write() as the state
        transition.

        Alongside (not replacing) the store-state re-check: a
        domain-enabled execution-time-only gating hook (Task 006C,
        DEC-013 §I.3) -- see `_domain_flag_for_job_type()`. This second
        check runs for every job, not only business-sourced ones, since
        a domain-enablement requirement is orthogonal to trigger source;
        every job_type shipped in this file maps to no flag today, so it
        is a no-op unless/until a future domain module registers one.
        """
        if vals.get('state') == 'running':
            Store = self.env['shopify.connector.store']
            Settings = self.env['shopify.connector.store.settings']
            for job in self:
                job_source = vals.get('job_source', job.job_source)
                job_type = vals.get('job_type', job.job_type)
                if 'store_id' in vals:
                    store = Store.browse(vals['store_id'])
                else:
                    store = job.store_id
                if self._is_business_job_source(job_source):
                    if store.state != 'connected':
                        raise ValidationError(
                            "This business job's store is not "
                            "'connected' -- it cannot start."
                        )
                flag_name = self._domain_flag_for_job_type(job_type)
                if flag_name:
                    settings = Settings.search(
                        [('store_id', '=', store.id)], limit=1,
                    )
                    if not settings or not settings[flag_name]:
                        raise ValidationError(
                            "This job's required domain flag (%r) is "
                            "not enabled for this store -- it cannot "
                            "start." % (flag_name,)
                        )
        return super().write(vals)

    @api.model
    def _domain_flag_for_job_type(self, job_type):
        """`job_type` -> the required `shopify.connector.store.settings`
        boolean flag name, or `None` if this job_type has no
        domain-enablement requirement.

        Execution-time-only gating hook (DEC-013 §I.3): consulted only
        from `write()`'s state -> 'running' re-check above, never from
        `create()` -- this hook may stop/hold/block a job at start time,
        it never alters an enqueue-time decision, and it can only ever
        ADD a new reason to block a start -- it never bypasses the
        store-state check above or any other existing guard.

        Every job_type shipped in this file today (`core_readiness_
        check`, `core_manual_maintenance`, `core_test_connection`,
        `core_dispatch_selftest`) maps to `None` -- no domain flag ever
        drives real behavior yet, since no domain module exists to
        register one. A domain module extends this mapping via classic
        Odoo inheritance (`_inherit` + `super()._domain_flag_for_
        job_type(job_type)`), mirroring the `_get_checks()`/
        `_get_handlers()` append-seam pattern -- never removing or
        silently overriding an already-mapped job_type.
        """
        return None

    # ------------------------------------------------------------------
    # Task 006C: execution-time claim mechanism (Decision A)
    # ------------------------------------------------------------------

    @api.model
    def _claim_for_dispatch(self, limit):
        """Claim up to `limit` claimable (`queued`, or due `retry_
        waiting`) jobs for one drain pass.

        Non-blocking claim: `try_lock_for_update()` (Odoo 19's official
        row-locking primitive, documented for exactly this cron-batch-
        processing pattern) attempts a PostgreSQL row lock per candidate
        row and silently skips any row already locked by a concurrent
        claim attempt in the same pass -- never a raw SQL `SKIP LOCKED`
        reimplementation, never a PostgreSQL advisory lock (Decision A,
        Task 006C gate-opening proposal §6). After locking, re-checks
        each row's actual current state under the lock -- mirroring
        Odoo's own official "Writing cron functions" worked example
        (`record.try_lock_for_update().filtered_domain(domain)`: lock,
        then re-check nothing changed underneath) -- since a
        concurrently committed write could have moved a row out of a
        claimable state between the initial search and the lock being
        acquired.

        This is a code-level claim guard only. `TransactionCase` cannot
        exercise real concurrent workers, so this method's behavior
        under actual multi-worker/multi-server execution is NOT proven
        by any unit test in this repository -- see the Task 006C
        gate-opening proposal §4/§8 for the live-runtime validation this
        does not, and could not, perform.
        """
        now = fields.Datetime.now()
        candidates = self.search([
            '|',
            ('state', '=', 'queued'),
            '&', ('state', '=', 'retry_waiting'), ('next_retry_at', '<=', now),
        ], limit=limit, order='id asc')
        if not candidates:
            return candidates
        locked = candidates.try_lock_for_update()
        if not locked:
            return locked
        locked.invalidate_recordset()
        return locked.filtered(
            lambda job: job.state == 'queued' or (
                job.state == 'retry_waiting'
                and job.next_retry_at
                and job.next_retry_at <= fields.Datetime.now()
            )
        )

    # ------------------------------------------------------------------
    # Task 006C: state-transition helpers (permanent-failure /
    # manual-review / retry / skip), implementing already-accepted
    # DEC-009 state semantics. Every transition below writes state
    # (+ error_class/manual_review_subreason/finished_at as applicable)
    # in a single write() call, then logs it exclusively through the
    # existing sanctioned `job.log._system_append()` path -- no direct
    # `job.log.create()` call, no `sudo()`.
    # ------------------------------------------------------------------

    def _log_transition(
        self, event_type, message, technical_detail=False,
        from_state=False, to_state=False,
    ):
        self.env['shopify.connector.job.log']._system_append(
            self, event_type, message, technical_detail=technical_detail,
            from_state=from_state, to_state=to_state,
        )

    def _transition_retry_waiting(
        self, next_retry_at, retry_count, error_class, message,
        technical_detail=False,
    ):
        """Move a claimed job back to `retry_waiting`, scheduled per the
        Task 006C retry-scheduling constants
        (`shopify_connector_job_dispatch.py`)."""
        self.ensure_one()
        from_state = self.state
        self.write({
            'state': 'retry_waiting',
            'error_class': error_class,
            'next_retry_at': next_retry_at,
            'retry_count': retry_count,
        })
        self._log_transition(
            'state_change', message, technical_detail=technical_detail,
            from_state=from_state, to_state='retry_waiting',
        )

    def _transition_failed_retryable(
        self, error_class, message, technical_detail=False,
    ):
        """Move a claimed job to `failed_retryable` -- a manual-fix-
        then-retry class error (DEC-009): the job stops, no automatic
        retry is scheduled, an operator fix is required before any
        future retry attempt."""
        self.ensure_one()
        from_state = self.state
        self.write({
            'state': 'failed_retryable',
            'error_class': error_class,
            'finished_at': fields.Datetime.now(),
        })
        self._log_transition(
            'state_change', message, technical_detail=technical_detail,
            from_state=from_state, to_state='failed_retryable',
        )

    def _transition_failed_final(
        self, error_class, message, technical_detail=False,
    ):
        """Move a claimed job to the permanent-failure terminal state."""
        self.ensure_one()
        from_state = self.state
        self.write({
            'state': 'failed_final',
            'error_class': error_class,
            'finished_at': fields.Datetime.now(),
        })
        self._log_transition(
            'state_change', message, technical_detail=technical_detail,
            from_state=from_state, to_state='failed_final',
        )

    def _transition_blocked_manual_review(
        self, error_class, manual_review_subreason, message,
        technical_detail=False,
    ):
        """Move a claimed job to the operator-confirmation-required
        state, setting the matching `manual_review_subreason` in the
        same write() the `_check_manual_review_subreason_required`
        constraint requires."""
        self.ensure_one()
        from_state = self.state
        self.write({
            'state': 'blocked_manual_review',
            'error_class': error_class,
            'manual_review_subreason': manual_review_subreason,
            'finished_at': fields.Datetime.now(),
        })
        self._log_transition(
            'state_change', message, technical_detail=technical_detail,
            from_state=from_state, to_state='blocked_manual_review',
        )

    def _transition_skipped(self, message, technical_detail=False):
        """Move a claimed job to `skipped` without ever invoking a
        handler -- used by the dispatcher's execution-time-immediately-
        before-dispatch store-state re-check (SRR-03 narrowing;
        narrows, never claims to close, the disconnect/in-flight-job
        race)."""
        self.ensure_one()
        from_state = self.state
        self.write({
            'state': 'skipped',
            'finished_at': fields.Datetime.now(),
        })
        self._log_transition(
            'state_change', message, technical_detail=technical_detail,
            from_state=from_state, to_state='skipped',
        )

    @api.depends(
        'store_id', 'job_type', 'res_model', 'res_id',
        'shopify_target_gid', 'payload_hash',
    )
    def _compute_idempotency_key(self):
        # Answers "is this the same operation, same target, same payload,
        # already known?" (core-naming-schema-planning.md §8). Persists
        # for the life of the job -- never recomputed to a falsy value.
        for job in self:
            job.idempotency_key = '|'.join(
                str(part) if part else ''
                for part in (
                    job.store_id.id,
                    job.job_type,
                    job.res_model,
                    job.res_id,
                    job.shopify_target_gid,
                    job.payload_hash,
                )
            )

    @api.depends(
        'state', 'store_id', 'res_model', 'res_id', 'shopify_target_gid',
        'superseded_by_job_id',
    )
    def _compute_operation_scope_key(self):
        # The DB-backed serialization guard key (§8): populated only
        # while the job is non-terminal and has a known target; cleared
        # on reaching a terminal state or being superseded, so a
        # terminal-or-superseded job never collides with a new job under
        # the (store_id, operation_scope_key) unique constraint.
        for job in self:
            if (
                job.state in TERMINAL_JOB_STATES
                or job.superseded_by_job_id
                or not job.res_model
            ):
                job.operation_scope_key = False
            else:
                job.operation_scope_key = '|'.join(
                    str(part) if part else ''
                    for part in (
                        job.store_id.id,
                        job.res_model,
                        job.res_id,
                        job.shopify_target_gid,
                    )
                )

    @api.constrains('job_source', 'trigger_origin')
    def _check_trigger_origin_required(self):
        for job in self:
            if job.job_source == 'odoo_event' and not job.trigger_origin:
                raise ValidationError(
                    "trigger_origin is required when job_source is 'odoo_event'."
                )
            if job.job_source != 'odoo_event' and job.trigger_origin:
                raise ValidationError(
                    "trigger_origin must be empty unless job_source is 'odoo_event'."
                )

    @api.constrains('state', 'manual_review_subreason')
    def _check_manual_review_subreason_required(self):
        for job in self:
            if job.state == 'blocked_manual_review' and not job.manual_review_subreason:
                raise ValidationError(
                    "manual_review_subreason is required when state is "
                    "'blocked_manual_review'."
                )
            if job.state != 'blocked_manual_review' and job.manual_review_subreason:
                raise ValidationError(
                    "manual_review_subreason must be empty unless state is "
                    "'blocked_manual_review'."
                )
