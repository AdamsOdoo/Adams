from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

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

# SEC-1 D-SEC1-1/D-SEC1-2: correctness and permission invariants enforced
# server-side for every caller. Context flags are intentionally not accepted.
LEGAL_JOB_TRANSITIONS = {
    'draft': frozenset(('queued', 'cancelled', 'failed_retryable')),
    'queued': frozenset((
        'running', 'cancelled', 'failed_retryable', 'retry_waiting',
        'failed_final', 'blocked_manual_review',
    )),
    'running': frozenset((
        'succeeded', 'failed_final', 'skipped', 'retry_waiting',
        'failed_retryable', 'blocked_manual_review', 'cancelled',
    )),
    'retry_waiting': frozenset((
        'running', 'cancelled', 'failed_retryable', 'failed_final',
        'blocked_manual_review',
    )),
    'failed_retryable': frozenset(('queued', 'cancelled')),
    'failed_final': frozenset(('queued',)),
    'blocked_manual_review': frozenset((
        'queued', 'cancelled', 'succeeded',
    )),
    'skipped': frozenset(('queued',)),
    'succeeded': frozenset(),
    'cancelled': frozenset(),
}

PROTECTED_JOB_FIELDS = frozenset((
    'state', 'retry_count', 'error_class', 'manual_review_subreason',
    'payload_hash', 'res_model', 'res_id', 'shopify_target_gid', 'job_type',
    'original_job_type', 'job_source', 'trigger_origin', 'next_retry_at',
    'started_at', 'finished_at', 'superseded_by_job_id', 'cancel_reason',
    'current_attempt_token', 'owner_worker_ref', 'running_since',
    'reconciliation_pending_until', 'mutation_attempt_id',
))

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
    ('no_reconciliation_strategy', 'No Reconciliation Strategy'),
    ('idempotency_contract_violation', 'Idempotency Contract Violation'),
    ('store_identity_mismatch', 'Store Identity Mismatch'),
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
    _inherit = ['shopify.connector.scope.mixin']
    _description = 'Shopify Connector Job'

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
            # LC-1 / DEC-030: permanent core-owned sink for jobs whose
            # domain selection value is removed during supported uninstall.
            ('historic_domain_job', 'Historic Domain Job'),
            # Task 006C / Decision F (gate-opening proposal §6):
            # core/diagnostic-only, reserved solely for the dispatcher's
            # own registry/dispatch self-tests (shopify_connector_job_
            # dispatch.py) -- never dispatched to a live Shopify call,
            # never a template for a future domain job_type.
            ('core_dispatch_selftest', 'Core Dispatch Selftest'),
            ('mutation_dispatch_selftest', 'Mutation Dispatch Selftest'),
            (
                'mutation_dispatch_selftest_reconcile',
                'Mutation Dispatch Selftest Reconciliation',
            ),
        ],
        required=True,
        index=True,
        readonly=True,
    )
    # LC-1 / DEC-030: set once at creation and deliberately not computed
    # from job_type, so domain uninstall can retype the row without losing
    # the original domain identity used for audit and later querying.
    original_job_type = fields.Char(index=True, readonly=True)

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
    # CORE-R2 (AR-047) connection epoch captured at business-job enqueue
    # (`shopify.connector.job.enqueue`). `execute_business` admission compares it
    # against the store's live `connection_generation` under a `FOR SHARE` lock
    # and refuses the call on mismatch, so an old handler cannot resume across a
    # future disconnect/reconnect cycle. Captured at enqueue, never inferred at
    # dispatch time. Additive/inert in this slice; existing rows and
    # directly-created (non-enqueued) jobs default to 0 (analysis §22).
    expected_connection_generation = fields.Integer(
        default=0,
        readonly=True,
    )
    # DEC-031 Layer 2 durable claim ownership (D1).
    current_attempt_token = fields.Char(index=True, readonly=True)
    owner_worker_ref = fields.Char(index=True, readonly=True)
    running_since = fields.Datetime(index=True, readonly=True)
    reconciliation_pending_until = fields.Datetime(index=True, readonly=True)
    mutation_attempt_id = fields.Many2one(
        'shopify.connector.mutation.attempt',
        index=True,
        readonly=True,
        ondelete='restrict',
    )

    _store_idempotency_key_uniq = models.Constraint(
        'UNIQUE(store_id, idempotency_key)',
        'A job with this idempotency key already exists for this store.',
    )
    _store_operation_scope_key_uniq = models.Constraint(
        'UNIQUE(store_id, operation_scope_key)',
        'A non-terminal job already holds this operation scope for this store.',
    )
    _mutation_attempt_reconciliation_unique = models.UniqueIndex(
        '(mutation_attempt_id) WHERE mutation_attempt_id IS NOT NULL',
        'Only one reconciliation job may own a mutation attempt.',
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
        vals_list = [dict(vals) for vals in vals_list]
        if not self.env.su:
            protected = sorted(set().union(
                *(set(vals) & PROTECTED_JOB_FIELDS for vals in vals_list)
            ))
            if protected:
                raise AccessError(
                    "Protected Shopify job fields cannot be supplied through "
                    "generic create(). Use the sanctioned enqueue or core "
                    "service. Protected fields: %s" % ', '.join(protected)
                )
        Store = self.env['shopify.connector.store']
        for vals in vals_list:
            # Never trust an RPC-supplied historic identity: the immutable
            # snapshot is always the effective job_type at creation.
            vals['original_job_type'] = vals.get('job_type')
            if self._is_business_job_source(vals.get('job_source')):
                store = Store.browse(vals.get('store_id')).exists()
                is_layer2_reconciliation = (
                    vals.get('job_source') == 'reconciliation'
                    and vals.get('mutation_attempt_id')
                )
                allowed_states = (
                    ('connected', 'disconnecting')
                    if is_layer2_reconciliation else ('connected',)
                )
                if not store or store.state not in allowed_states:
                    raise ValidationError(
                        "A business job (job_source=%r) can only be "
                        "created for a store in state 'connected'." % (
                            vals.get('job_source'),
                        )
                    )
        return super().create(vals_list)

    def _reassign_to_historic_job_type(self):
        """Preserve jobs when a domain module removes its selection value.

        Odoo calls this method from each domain job type's ``selection_add``
        ``ondelete`` callback. Non-terminal work is cancelled first through
        the current sanctioned state-write path and receives exactly one
        auditable manual-action log entry; terminal work is only retyped.
        No job or log row is unlinked.
        """
        reason = (
            'Domain capability uninstalled; job preserved as historic '
            'connector history.'
        )
        for job in self:
            original_job_type = job.original_job_type or job.job_type
            if job.state not in TERMINAL_JOB_STATES:
                from_state = job.state
                job.sudo().write({
                    'state': 'cancelled',
                    'cancel_reason': reason,
                    'finished_at': fields.Datetime.now(),
                    'manual_review_subreason': False,
                })
                job._log_transition(
                    'manual_action',
                    'Job cancelled during domain uninstall; original job '
                    'type %r is preserved.' % original_job_type,
                    from_state=from_state,
                    to_state='cancelled',
                )
            values = {'job_type': 'historic_domain_job'}
            if not job.original_job_type:
                values['original_job_type'] = original_job_type
            job.sudo().write(values)
        return True

    def _has_mutation_attempt_evidence(self):
        self.ensure_one()
        return bool(
            self.mutation_attempt_id
            or self.env['shopify.connector.mutation.attempt'].sudo().search(
                [('job_id', '=', self.id)], limit=1,
            )
        )

    def action_resolve_manual_review(self):
        self.ensure_one()
        if self._has_mutation_attempt_evidence():
            raise UserError(
                'Mutation-evidence-linked jobs may only be resolved through '
                'action_resolve_mutation_attempt.'
            )
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
                "resolve a manual-review job."
            )
        if self.state != 'blocked_manual_review':
            raise UserError(
                "Only a blocked_manual_review job can be resolved."
            )
        from_state = self.state
        self.sudo().write({
            'state': 'queued',
            'manual_review_subreason': False,
            'finished_at': False,
        })
        self._log_transition(
            'manual_action',
            'Manual review resolved by actor_uid=%d.' % self.env.uid,
            from_state=from_state,
            to_state='queued',
        )
        return True

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
        protected = sorted(set(vals) & PROTECTED_JOB_FIELDS)
        if protected and not self.env.su:
            raise AccessError(
                "Protected Shopify job fields can only be changed through "
                "a sanctioned connector action or service. Protected fields: "
                "%s" % ', '.join(protected)
            )
        if 'state' in vals:
            to_state = vals['state']
            for job in self:
                if to_state != job.state and to_state not in (
                    LEGAL_JOB_TRANSITIONS.get(job.state, frozenset())
                ):
                    raise ValidationError(
                        "Illegal Shopify job transition: %s -> %s." % (
                            job.state, to_state,
                        )
                    )

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
                    mutation_attempt_id = vals.get(
                        'mutation_attempt_id', job.mutation_attempt_id.id,
                    )
                    is_layer2_reconciliation = (
                        job_source == 'reconciliation'
                        and mutation_attempt_id
                    )
                    allowed_states = (
                        ('connected', 'disconnecting')
                        if is_layer2_reconciliation else ('connected',)
                    )
                    if store.state not in allowed_states:
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
    def _claimable_domain(self, now=False, exclude_store_ids=()):
        """The candidate domain a drain pass may claim from.

        PERF-1 extracted this literal from `_claim_for_dispatch` so the
        dispatcher can COUNT what remains with exactly the same predicate it
        claims with -- `ir.cron._commit_progress(remaining=...)` reporting a
        number derived from a second, hand-copied domain would drift from the
        claim the moment either changed. The predicate itself is unchanged.

        `exclude_store_ids` is the PERF-1 D-PERF1-4 backpressure lever: a
        store under Shopify throttle pressure is dropped from the CANDIDATE
        SEARCH for the rest of the pass, so its jobs are never locked and
        never transitioned. It can only ever narrow the set -- backpressure
        never raises the drain rate.
        """
        now = now or fields.Datetime.now()
        domain = [
            '&',
            '|',
            ('reconciliation_pending_until', '=', False),
            ('reconciliation_pending_until', '<=', now),
            '|',
            ('state', '=', 'queued'),
            '&', ('state', '=', 'retry_waiting'), ('next_retry_at', '<=', now),
        ]
        if exclude_store_ids:
            domain = [
                ('store_id', 'not in', list(exclude_store_ids)),
            ] + domain
        return domain

    @api.model
    def _claimable_count(self, exclude_store_ids=()):
        """How many jobs a further pass could claim right now.

        Read-only; takes no lock. Used only to report cron progress.
        """
        return self.search_count(
            self._claimable_domain(exclude_store_ids=exclude_store_ids),
        )

    @api.model
    def _claim_for_dispatch(self, limit, exclude_store_ids=()):
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

        PERF-1 note: only the CANDIDATE SEARCH gained the optional
        `exclude_store_ids` narrowing above. The `try_lock_for_update()`
        claim and the under-lock state re-check below are unchanged and are
        held to that by a source guard
        (`test_dispatch_throughput.py::test_claim_lock_and_recheck_unchanged`).
        """
        now = fields.Datetime.now()
        candidates = self.search(
            self._claimable_domain(now, exclude_store_ids),
            limit=limit,
            order='id asc',
        )
        if not candidates:
            return candidates
        locked = candidates.try_lock_for_update()
        if not locked:
            return locked
        locked.invalidate_recordset()
        return locked.filtered(
            lambda job: (
                not job.reconciliation_pending_until
                or job.reconciliation_pending_until <= fields.Datetime.now()
            ) and (
                job.state == 'queued' or (
                    job.state == 'retry_waiting'
                    and job.next_retry_at
                    and job.next_retry_at <= fields.Datetime.now()
                )
            )
        )

    # ------------------------------------------------------------------
    # Task 006C: state-transition helpers (permanent-failure /
    # manual-review / retry / skip), implementing already-accepted
    # DEC-009 state semantics. Every transition below writes state
    # (+ error_class/manual_review_subreason/finished_at as applicable)
    # in a single write() call, then logs it exclusively through the
    # existing sanctioned `job.log._system_append()` path -- no direct
    # `job.log.create()` call. SEC-1 elevates only each protected write;
    # transition logging retains the original caller environment.
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
        self.sudo().write({
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
        self.sudo().write({
            'state': 'failed_retryable',
            'error_class': error_class,
            'finished_at': fields.Datetime.now(),
        })
        self._log_transition(
            'state_change', message, technical_detail=technical_detail,
            from_state=from_state, to_state='failed_retryable',
        )

    def _transition_failed_final(
        self, error_class, message, technical_detail=False, retry_count=False,
    ):
        """Move a claimed job to the permanent-failure terminal state.

        `retry_count` is optional and only written when explicitly
        provided (truthy) -- callers reached via a retry-exhaustion path
        (`shopify_connector_job_dispatch.py::_schedule_retry_or_fail`)
        pass the exhausted attempt count so it is persisted (the job did
        attempt and fail again, one more time than its last recorded
        `retry_count`); callers with no attempt to count (e.g. a
        missing-handler failure, or a blocked start-time gate) omit it,
        leaving the field untouched, exactly as before this parameter
        existed.
        """
        self.ensure_one()
        from_state = self.state
        vals = {
            'state': 'failed_final',
            'error_class': error_class,
            'finished_at': fields.Datetime.now(),
        }
        if retry_count:
            vals['retry_count'] = retry_count
        self.sudo().write(vals)
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
        self.sudo().write({
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
        self.sudo().write({
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

    @api.constrains('job_type', 'mutation_attempt_id')
    def _check_reconciliation_attempt_link(self):
        strategies = self.env[
            'shopify.connector.job.dispatch'
        ]._get_reconciliation_strategies()
        reconciliation_types = {
            item['reconciliation_job_type']
            for item in strategies.values()
        }
        for job in self:
            is_layer2_reconciliation = job.job_type in reconciliation_types
            may_retain_historic_link = (
                job.job_type == 'historic_domain_job'
                and bool(job.mutation_attempt_id)
            )
            if (
                is_layer2_reconciliation
                != bool(job.mutation_attempt_id)
                and not may_retain_historic_link
            ):
                raise ValidationError(
                    'A Layer 2 reconciliation job requires one exact mutation '
                    'attempt; only historic domain jobs may retain that link.'
                )
            if (
                job.mutation_attempt_id
                and job.store_id != job.mutation_attempt_id.store_id
            ):
                raise ValidationError(
                    'A reconciliation job and its mutation attempt must share a store.'
                )

    # SEC-3 (#197) scope closure. The write-side rule for this relation is
    # already enforced above, so it is declared here only so the upgrade sweep
    # covers rows written BEFORE that constraint existed -- a constraint can
    # refuse a new row, it can never see an old one.
    @api.model
    def _sec3_parent_scope_relations(self):
        return (
            ('mutation_attempt_id', 'store'),
            # Found by the SEC-3 completeness guard rather than by reading the
            # model: a superseding job is another job, so a job in store A can
            # name a superseding job in store B and stay company-consistent
            # throughout. Nothing else in the ownership model looks at it.
            ('superseded_by_job_id', 'store'),
        )

    @api.constrains('store_id', 'superseded_by_job_id')
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()

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
