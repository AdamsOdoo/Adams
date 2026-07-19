from datetime import timedelta
import logging
import os
import random
import uuid

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from ..tools.redaction import redact
from .shopify_connector_job import (
    BUSINESS_JOB_SOURCES,
    ERROR_CLASS_SELECTION,
    MANUAL_REVIEW_SUBREASON_SELECTION,
)
from .shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
    INCONCLUSIVE_RECONCILIATION_CAP,
    canonical_sha256,
)

_logger = logging.getLogger(__name__)

# Decision E (gate-opening proposal §6) -- a conservative implementation
# default pending live-runtime validation (see docs/07-implementation-
# plan/task-006c-sync-engine-gate-opening-proposal.md §8), well below
# the documented >64-savepoint performance ceiling (SRR-01). Named,
# tunable constant, never an inlined magic number.
DISPATCH_BATCH_SIZE = 20

# Decision C (gate-opening proposal §6 / MBQ-16 implementation-planning
# defaults, restated in DEC-009's own acceptance note as "implementation
# planning defaults, not final production-tuned constants"). Named,
# tunable constants -- a future retuning session can change these
# without an architecture change.
RETRY_MAX_ATTEMPTS = 12
RETRY_BASE_DELAY_SECONDS = 30
RETRY_MULTIPLIER = 2
RETRY_MAX_DELAY_SECONDS = 30 * 60
RETRY_JITTER_FRACTION = 0.2
RETRY_WINDOW_HOURS = 24
# unknown_system_error's own "single safety-net auto-retry, then human"
# posture (architecture gate §E) -- a distinct, smaller attempt budget
# than the general auto-retry classes below.
SAFETY_NET_MAX_ATTEMPTS = 1

# CORE-R2 Slice 2A (AR-047; analysis §14/§16, packet §7/§13) disconnect
# quiescence controller cadence + timeout. Named, tunable constants
# [Open -- tuning only, analysis §26]; a future retuning session can change
# these without an architecture change. The disconnect controller
# (`shopify_connector_store.py::_run_disconnect_quiesce`) imports them.
#
# * DISCONNECT_QUIESCE_TIMEOUT is measured from `store.disconnect_requested_at`
#   and MUST exceed the admission lease lifetime
#   (`shopify_connector_api_client._CALL_LEASE_LIFETIME_SECONDS`, 300s) so a
#   genuinely-live-but-slow admitted call inside its own lifetime is never
#   force-finalized as `timed_out` before it can release its lease.
# * POLL_DELAY is the still-`quiescing` re-poll cadence, scheduled via a
#   delayed `_trigger(at=now+POLL_DELAY)` (never an immediate same-store
#   re-trigger, no busy loop). It is >= 1 minute -- the `ir_cron._trigger`
#   scheduling granularity floor (analysis §14, `ir_cron.py:735`).
DISCONNECT_QUIESCE_TIMEOUT = timedelta(minutes=15)
POLL_DELAY = timedelta(minutes=1)

# DEC-009 §E retry-class taxonomy, applied to the fixed ERROR_CLASS_
# SELECTION registry already encoded in shopify_connector_job.py. This
# module does not introduce a 17th class or alter the registry -- it
# only routes the existing 16 classes to a job-state transition.
AUTO_RETRY_ERROR_CLASSES = (
    'shopify_throttling_rate_limit',
    'shopify_temporary_server_network',
    'concurrency_race_conflict',
)
MANUAL_FIX_THEN_RETRY_ERROR_CLASSES = (
    'shopify_permission_scope_auth',
    'shopify_user_errors_validation',
    'odoo_validation_configuration',
    'mapping_missing',
    'data_shape_schema_mismatch',
)
# "Conservative, never silent" (architecture gate §E) -- stops the job
# without an automatic retry, same as the manual-fix-then-retry family,
# but financial_total_mismatch is not one of the six manual_review_
# subreason values, so it cannot route to blocked_manual_review (the
# job model's own _check_manual_review_subreason_required constraint
# would reject that combination).
CONSERVATIVE_NEVER_SILENT_ERROR_CLASSES = (
    'financial_total_mismatch',
)
# The six DEC-009 §D.5.4 operator-confirmation-required classes double
# as their own manual_review_subreason value -- imported, not
# redeclared, so the two vocabularies can never drift apart.
MANUAL_REVIEW_ERROR_CLASSES = tuple(
    value for value, _label in MANUAL_REVIEW_SUBREASON_SELECTION
)
SAFETY_NET_ERROR_CLASSES = (
    'unknown_system_error',
)

# DEC-031 Layer 1 (AR-048) -- the fail-closed replay-policy registry's
# fixed three-value vocabulary. Do not add a fourth class here.
REPLAY_POLICY_LOCAL_ONLY = 'local_only'
REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE = 'remote_read_replay_safe'
REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE = 'remote_effect_not_replay_safe'
# Policies for which replaying a recovered job's existing bounded
# concurrency_race_conflict auto-retry (this module's own recovery
# mechanism, unmodified) stays safe: a purely local no-op or a remote
# *read* has no Shopify-side effect, so a further automatic retry after
# recovery cannot cause a duplicate remote effect.
REPLAY_SAFE_RETRY_POLICIES = (
    REPLAY_POLICY_LOCAL_ONLY,
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)

MUTATION_STRATEGY_KEYS = frozenset((
    'reconciliation_job_type',
    'prepare_local',
    'prepare_preconditions',
    'transport',
    'classify_direct_result',
    'reconcile',
    'apply_consequence',
))
DIRECT_ACTIONS = frozenset((
    'succeed', 'fail_final', 'block_manual_review', 'reconcile',
    'domain_callback',
))
RECONCILIATION_ACTIONS = frozenset((
    'succeed', 'fail_final', 'cancel', 'block_manual_review',
    'domain_callback',
))
REGISTERED_ERROR_CLASSES = frozenset(
    value for value, _label in ERROR_CLASS_SELECTION
)
REGISTERED_MANUAL_SUBREASONS = frozenset(
    value for value, _label in MANUAL_REVIEW_SUBREASON_SELECTION
)


class JobHandlerError(Exception):
    """Raised by a registered handler to report a classified failure.

    `error_class` must be one of `shopify.connector.job`'s fixed
    `ERROR_CLASS_SELECTION` values -- the dispatcher routes the job to
    `retry_waiting`/`failed_retryable`/`failed_final`/
    `blocked_manual_review` based on it, per the DEC-009 taxonomy this
    module encodes above. Any other exception a handler raises is
    treated as `unknown_system_error`. Mirrors `ShopifyClientError`'s
    own redact-at-construction discipline: `reason`/`technical_detail`
    are redacted here too, as defense in depth, even though every write
    path this exception reaches also redacts via `_system_append()`.
    """

    def __init__(self, error_class, reason, technical_detail=False):
        reason = redact(reason)
        super().__init__(reason)
        self.error_class = error_class
        self.reason = reason
        self.technical_detail = (
            redact(technical_detail) if technical_detail else technical_detail
        )


class ShopifyConnectorJobDispatch(models.AbstractModel):
    """The core job-dispatch service (Decision D): the `ir.cron`-driven
    drain-loop entry point, the handler-registry seam, the dispatcher,
    and the retry-scheduling sweep.

    Stateless, no table (`AbstractModel`, mirroring
    `shopify_connector_readiness_check.py` -- no new ACL row needed).
    Every write path here goes through `shopify.connector.job`'s own
    `write()`/state-transition-helper methods and
    `job.log._system_append()` -- no second job-log write path, no
    direct `job.log.create()` call, and no live Shopify API
    call anywhere in this file.
    """

    _name = 'shopify.connector.job.dispatch'
    _description = 'Shopify Connector Job Dispatch Service'

    # ------------------------------------------------------------------
    # ir.cron entry point
    # ------------------------------------------------------------------

    @api.model
    def run_drain(self, limit=DISPATCH_BATCH_SIZE):
        """Claim and dispatch up to ``limit`` jobs -- the ``ir.cron`` target.

        Each job is claimed, dispatched, and committed on its own per-job
        transaction (see :meth:`_drain_one`). The dispatcher deliberately does
        NOT wrap the handler in ``odoo.service.model.retrying``: that boundary
        automatically RE-INVOKES the complete handler after a rollback, which
        -- once a Shopify transport has already occurred -- risks a duplicate
        request, and it re-drives the job by a bare id without ever
        reacquiring the row-lock claim the rollback released. Instead a genuine
        PostgreSQL serialization/deadlock/lock failure (SQLSTATE
        40001/40P01/55P03) is caught at the per-job outer boundary, which rolls
        back, resets the environment, REACQUIRES the exact job under a real
        ``FOR UPDATE SKIP LOCKED`` row lock, revalidates its claimable state
        under that lock, and -- only if the job is still safely owned and
        claimable -- routes it ONCE through its declared DEC-031 Layer 1
        (AR-048) replay policy WITHOUT the recovery call itself re-invoking
        the handler: a ``local_only`` or ``remote_read_replay_safe`` job may
        be scheduled for a later bounded ``concurrency_race_conflict`` retry,
        while a ``remote_effect_not_replay_safe`` or undeclared job is routed
        to manual review instead of any automatic retry. This routing is
        policy-gated and makes no exactly-once claim. Per-job commit keeps one
        racing (or failing) job from rolling back the work of jobs already
        committed in the same drain (batch integrity); and because the claim is
        only a transaction-scoped row lock, a rolled-back job is never
        re-exposed by a bare re-browse -- after any rollback the job MUST be
        re-locked before any dispatch or state transition
        (:meth:`_recover_after_concurrency_conflict`).
        """
        for _slot in range(limit):
            if not self._drain_one():
                break

    @api.model
    def _drain_one(self):
        """Claim and dispatch a single job on its own per-job transaction.

        The claim (``shopify.connector.job._claim_for_dispatch``) is a
        transaction-scoped ``FOR UPDATE SKIP LOCKED`` row lock, NOT a durable
        state flag: it is held only until this transaction commits or rolls
        back. On the success path the whole dispatch (start -> handler ->
        outcome) runs and commits under that one held claim, so the job is
        never dispatched or transitioned without a currently-held lock, and a
        later job's rollback can never undo it. On a genuine PostgreSQL
        concurrency failure the aborted transaction has lost BOTH the claim and
        every uncommitted write; recovery re-locks the job before touching it
        (:meth:`_recover_after_concurrency_conflict`), which itself never
        re-invokes the handler and instead routes the still-owned job once
        through its declared DEC-031 Layer 1 replay policy (a bounded retry
        for ``local_only``/``remote_read_replay_safe`` jobs, manual review
        for ``remote_effect_not_replay_safe``/undeclared ones).

        Returns ``True`` when a job was claimed and handled (whether it
        succeeded, was refused, routed, recovered, or left to another worker),
        ``False`` when no claimable job remains so ``run_drain`` can stop early.
        """
        claimed = self.env['shopify.connector.job']._claim_for_dispatch(1)
        if not claimed:
            return False
        job_id = claimed.id

        if self._is_mutation_job_type(claimed.job_type):
            if not self._concurrency_retry_supported():
                raise ValidationError(
                    'Layer 2 mutation dispatch requires an owned cursor with '
                    'real commit boundaries.'
                )
            self._drain_mutation_one(claimed)
            return True

        if not self._concurrency_retry_supported():
            # The shared in-test transaction cursor forbids commit/rollback, so
            # the per-job transaction boundary below cannot run here. The
            # standard suite exercises normal dispatch and classified-failure
            # routing; a genuine PostgreSQL serialization failure cannot occur
            # on its single shared connection anyway. The genuine
            # independent-connection lifecycle tests drive the real boundary
            # below on real pooled cursors.
            self._dispatch_one(claimed)
            return True

        try:
            # Dispatch the claimed job ONCE, under the currently-held claim.
            # Flush inside the guard so a deferred serialization failure (Odoo
            # runs REPEATABLE READ, where 40001 surfaces at statement/flush
            # time) is caught here -- never after the commit, where it would
            # escape as a raw concurrency error.
            self._dispatch_one(claimed)
            self.env.cr.flush()
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY as exc:
            # A genuine 40001/40P01/55P03 aborted this transaction AFTER a
            # transport may already have occurred. The recovery call does NOT
            # replay the handler: reset, reacquire the exact job under a real
            # row lock, and -- only if we still own it -- route it once
            # through its declared DEC-031 Layer 1 replay policy (a bounded
            # conflict retry for replay-safe jobs, manual review otherwise).
            # Record the SQLSTATE (operationally useful, and the observable
            # evidence that a genuine PostgreSQL concurrency failure -- not an
            # injected exception -- drove this recovery).
            _logger.info(
                "Job %s hit a PostgreSQL concurrency failure (SQLSTATE %s) "
                "after dispatch; rolling back and reacquiring the job under a "
                "fresh row lock before any routing -- the handler is not "
                "replayed.",
                job_id, getattr(exc, 'pgcode', None),
            )
            self._recover_after_concurrency_conflict(job_id)
        else:
            # Commit this job's own outcome so a later job's rollback can never
            # undo it and it is never re-exposed to a duplicate call.
            self.env.cr.commit()
        return True

    @api.model
    def _recover_after_concurrency_conflict(self, job_id):
        """Recover ownership after a genuine PostgreSQL concurrency failure
        aborted a dispatch transaction, WITHOUT replaying the handler.

        The aborted transaction has already lost BOTH the original claim (a
        transaction-scoped ``FOR UPDATE`` row lock the rollback released) AND
        every uncommitted write (``state`` -> ``running``, any handler write).
        A Shopify transport MAY already have occurred, so the handler is never
        re-invoked here. Ownership contract (every reset loses the claim):

        1. roll back the aborted transaction and reset the environment, so the
           cursor is usable and no stale claim, lock, or cache (including the
           rolled-back ``running`` write) survives;
        2. reacquire the EXACT job under the real non-blocking
           ``try_lock_for_update`` (``FOR UPDATE SKIP LOCKED``) claim -- an
           empty result means another worker holds it (or the row is gone), so
           we own nothing and must not touch it;
        3. revalidate its CLAIMABLE state under that lock -- a job another
           worker already moved to ``running``/terminal/etc. is not claimable
           and must never be overwritten;
        4. only a still-owned, still-claimable job is routed ONCE, in this
           clean transaction we own, through its declared DEC-031 Layer 1
           (AR-048) replay policy -- never by re-invoking the handler: a
           ``local_only`` or ``remote_read_replay_safe`` job may be scheduled
           for a later bounded ``concurrency_race_conflict`` retry
           (``retry_waiting``, or ``failed_final`` once the bounded budget is
           exhausted), while a ``remote_effect_not_replay_safe`` or undeclared
           job is routed to manual review (``duplicate_risk``) instead of any
           automatic retry. The routing is policy-gated and makes no
           exactly-once claim.

        Every exit commits the (owned or empty) transaction so the row lock, if
        any, is released and the next ``_drain_one`` claim starts clean. Another
        worker winning the post-rollback claim, or having already transitioned
        the job, is a valid outcome -- never an error.
        """
        Job = self.env['shopify.connector.job']
        # (1) Make the aborted cursor usable again and drop all stale ORM state
        # (recordset caches, to-compute/to-flush) so nothing from the lost
        # transaction leaks into the recovery transaction.
        self.env.cr.rollback()
        self.env.transaction.reset()
        # (2) Reacquire the exact job under a real FOR UPDATE SKIP LOCKED row
        # lock. Empty => another worker holds it (or the row is gone): we own
        # nothing, so we do nothing.
        locked = Job.browse(job_id).try_lock_for_update()
        if not locked:
            self.env.cr.commit()
            return
        # Layer 2: a durably-running owned mutation is not claimable, but a
        # committed C2 attempt means transport may have occurred. Reconcile;
        # never invoke the mutation handler again.
        locked.invalidate_recordset()
        if (
            locked.state == 'running'
            and locked.current_attempt_token
            and self._is_mutation_job_type(locked.job_type)
        ):
            attempt = self.env[
                'shopify.connector.mutation.attempt'
            ].search([
                ('job_id', '=', locked.id),
                ('attempt_token', '=', locked.current_attempt_token),
            ], limit=1)
            if attempt and attempt.transport_attempted:
                locked.sudo().write({
                    'reconciliation_pending_until': fields.Datetime.now(),
                })
                self._ensure_reconciliation_job(locked, attempt)
                self.env.cr.commit()
                return
            # C1 committed but C2 did not: no transport was possible.
            from_state = locked.state
            locked.sudo().write({
                'state': 'retry_waiting',
                'next_retry_at': fields.Datetime.now(),
                'current_attempt_token': False,
                'owner_worker_ref': False,
                'running_since': False,
            })
            locked._log_transition(
                'state_change',
                'Recovered a C1-only mutation owner; safe requeue before C2.',
                from_state=from_state,
                to_state='retry_waiting',
            )
            self.env.cr.commit()
            return
        # (3) Revalidate CLAIMABLE state UNDER the lock (mirrors
        # ``_claim_for_dispatch``): only a still-queued or genuinely-due
        # retry_waiting job may be routed; a running/terminal/otherwise
        # non-claimable job is owned or finished by another worker and must
        # never be overwritten.
        locked.invalidate_recordset()
        claimable = locked.filtered(lambda job: job.state == 'queued' or (
            job.state == 'retry_waiting'
            and job.next_retry_at
            and job.next_retry_at <= fields.Datetime.now()
        ))
        if not claimable:
            self.env.cr.commit()
            return
        # (4) We hold the lock and the job is still safely claimable: route
        # it WITHOUT replaying the handler -- so no second Shopify transport
        # is issued -- through whichever path its declared replay policy
        # (DEC-031 Layer 1, AR-048) allows.
        policy = self._get_replay_policy(claimable.job_type)
        if policy in REPLAY_SAFE_RETRY_POLICIES:
            self._route_failure(
                claimable, 'concurrency_race_conflict',
                'A concurrent-update conflict aborted the dispatch '
                'transaction after a transport may have occurred; the job '
                'was re-locked and routed once to a bounded retry without '
                'replaying its handler.',
            )
        else:
            # remote_effect_not_replay_safe, or any undeclared/unexpected
            # policy (fail-closed default -- never a read-safe default): an
            # automatic retry here could re-issue a Shopify-side effect, so
            # this never reaches concurrency_race_conflict's auto-retry.
            # Routed instead through the existing blocked_manual_review /
            # duplicate_risk vocabulary -- no new error class, no automatic
            # retry, never retry_waiting.
            self._route_failure(
                claimable, 'duplicate_risk',
                'A concurrent-update conflict aborted the dispatch '
                'transaction for a job whose remote effect is not declared '
                'replay-safe. After the rollback, a prior remote effect '
                'cannot be safely ruled out -- this does not claim a '
                'Shopify mutation occurred, nor exactly-once execution. '
                'The job was re-locked and routed to manual review instead '
                'of an automatic retry.',
            )
        self.env.cr.commit()

    # ------------------------------------------------------------------
    # DEC-031 Layer 2 mutation protocol
    # ------------------------------------------------------------------

    @api.model
    def _get_reconciliation_strategies(self):
        """Mutation-domain registry; domain addons extend by add-only merge."""
        return {
            'mutation_dispatch_selftest': {
                'reconciliation_job_type':
                    'mutation_dispatch_selftest_reconcile',
                'prepare_local': self._prepare_local_mutation_selftest,
                'prepare_preconditions':
                    self._prepare_preconditions_mutation_selftest,
                'transport': self._transport_mutation_dispatch_selftest,
                'classify_direct_result':
                    self._classify_direct_mutation_selftest,
                'reconcile': self._reconcile_mutation_dispatch_selftest,
                'apply_consequence':
                    self._apply_consequence_mutation_selftest,
            },
        }

    @api.model
    def _validated_mutation_strategy(self, mutation_domain):
        strategy = self._get_reconciliation_strategies().get(mutation_domain)
        if (
            not isinstance(strategy, dict)
            or set(strategy) != MUTATION_STRATEGY_KEYS
            or not isinstance(strategy.get('reconciliation_job_type'), str)
            or not strategy.get('reconciliation_job_type')
            or any(
                not callable(strategy.get(key))
                for key in MUTATION_STRATEGY_KEYS
                if key != 'reconciliation_job_type'
            )
        ):
            raise ValidationError(
                'The mutation strategy is missing or malformed.'
            )
        return strategy

    @api.model
    def _is_mutation_job_type(self, job_type):
        return job_type in self._get_reconciliation_strategies()

    @api.model
    def _prepare_local_mutation_selftest(self, job):
        return {
            'mutation_domain': job.job_type,
            'job_id': job.id,
            'store_id': job.store_id.id,
            'expected_connection_generation':
                job.expected_connection_generation,
            'expected_store_identity': job.store_id.shop_domain,
            'synthetic_outcome': 'succeeded',
        }

    @api.model
    def _prepare_preconditions_mutation_selftest(
        self, local_snapshot, owner_context,
    ):
        if owner_context['job_id'] != local_snapshot['job_id']:
            raise ValidationError('The synthetic owner snapshot is invalid.')
        idempotency_key = uuid.uuid4().hex
        operation = (
            'mutation MutationDispatchSelftest($idempotencyKey: String!) { '
            'shop { id } @idempotent(key: $idempotencyKey) }'
        )
        return {
            'mutation_domain': local_snapshot['mutation_domain'],
            'operation': operation,
            'variables': {'idempotencyKey': idempotency_key},
            'business_intent': {
                'mutation_domain': local_snapshot['mutation_domain'],
                'store_id': local_snapshot['store_id'],
                'job_id': local_snapshot['job_id'],
            },
            'remote_mutation_intent': {
                'operation_name': 'MutationDispatchSelftest',
                'store_id': local_snapshot['store_id'],
                'job_id': local_snapshot['job_id'],
            },
            'preconditions_snapshot': {
                'expected_connection_generation':
                    local_snapshot['expected_connection_generation'],
                'expected_store_identity':
                    local_snapshot['expected_store_identity'],
            },
            'expected_connection_generation':
                local_snapshot['expected_connection_generation'],
            'expected_store_identity':
                local_snapshot['expected_store_identity'],
            'shopify_idempotency_key': idempotency_key,
            'synthetic_outcome': local_snapshot['synthetic_outcome'],
        }

    @api.model
    def _transport_mutation_dispatch_selftest(self, request, attempt_context):
        del attempt_context
        return {
            'outcome': request.get('synthetic_outcome', 'succeeded'),
            'evidence': {'transport': 'synthetic_stub'},
        }

    @api.model
    def _classify_direct_mutation_selftest(self, result):
        code = (result or {}).get('error_code')
        evidence = dict((result or {}).get('evidence') or {})
        if code in (
            'IDEMPOTENCY_KEY_PARAMETER_MISMATCH',
            'IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED',
        ):
            return {
                'observed_outcome': 'uncertain',
                'error_class': 'idempotency_contract_violation',
                'manual_review_subreason':
                    'idempotency_contract_violation',
                'action': 'block_manual_review',
                'message': 'Synthetic idempotency contract violation.',
                'evidence': evidence,
            }
        outcome = (result or {}).get('outcome')
        if outcome == 'succeeded':
            action = 'succeed'
            error_class = False
        elif outcome == 'failed_clean':
            action = 'fail_final'
            error_class = 'shopify_user_errors_validation'
        elif outcome == 'uncertain':
            action = 'reconcile'
            error_class = 'shopify_temporary_server_network'
        else:
            raise ValidationError('The direct result is malformed.')
        return {
            'observed_outcome': outcome,
            'error_class': error_class,
            'manual_review_subreason': False,
            'action': action,
            'message': 'Synthetic direct mutation outcome: %s.' % outcome,
            'evidence': evidence,
        }

    @api.model
    def _reconcile_mutation_dispatch_selftest(self, attempt):
        return {
            'verdict': 'applied',
            'observed_store_identity': attempt.expected_store_identity,
            'action': 'succeed',
            'error_class': False,
            'manual_review_subreason': False,
            'message': 'Synthetic read-only reconciliation applied.',
            'evidence': {'reconciliation': 'synthetic_stub'},
        }

    @api.model
    def _apply_consequence_mutation_selftest(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        del job, attempt, phase, consequence, reconciliation_job
        return True

    @api.model
    def _handle_mutation_dispatch_selftest(self, job):
        raise ValidationError(
            'Mutation jobs must be executed by the C1/C2/NET/C3 wrapper.'
        )

    @api.model
    def _safe_message(self, value, fallback):
        if not isinstance(value, str) or not value.strip():
            return fallback
        return redact(value.strip())

    @api.model
    def _validate_job_consequence(self, value, phase):
        if not isinstance(value, dict):
            raise ValidationError('A mutation consequence must be a dict.')
        required = {
            'observed_outcome', 'error_class', 'manual_review_subreason',
            'action', 'message', 'evidence',
        }
        allowed = required | {'domain_payload'}
        if set(value) - allowed or required - set(value):
            raise ValidationError(
                'The mutation consequence has an invalid field set.'
            )
        consequence = dict(value)
        outcome = consequence['observed_outcome']
        error_class = consequence['error_class'] or False
        subreason = consequence['manual_review_subreason'] or False
        action = consequence['action']
        if outcome not in ('succeeded', 'failed_clean', 'uncertain'):
            raise ValidationError('Unknown mutation observed outcome.')
        if error_class and error_class not in REGISTERED_ERROR_CLASSES:
            raise ValidationError('Unknown mutation error class.')
        if subreason and subreason not in REGISTERED_MANUAL_SUBREASONS:
            raise ValidationError('Unknown manual-review subreason.')
        if not isinstance(consequence['evidence'], dict):
            raise ValidationError('Mutation evidence must be a dict.')
        if not isinstance(consequence.get('domain_payload', {}), dict):
            raise ValidationError('Mutation domain_payload must be a dict.')
        consequence['domain_payload'] = dict(
            consequence.get('domain_payload') or {}
        )
        consequence['evidence'] = dict(consequence['evidence'])
        consequence['error_class'] = error_class
        consequence['manual_review_subreason'] = subreason
        consequence['message'] = self._safe_message(
            consequence['message'], 'Mutation consequence recorded.',
        )
        if phase == 'direct':
            if action not in DIRECT_ACTIONS:
                raise ValidationError('Unknown direct mutation action.')
            if action == 'succeed' and outcome != 'succeeded':
                raise ValidationError('succeed requires a succeeded outcome.')
            if action == 'fail_final' and (
                outcome != 'failed_clean' or not error_class
            ):
                raise ValidationError(
                    'fail_final requires failed_clean and an error class.'
                )
            if action == 'reconcile' and outcome != 'uncertain':
                raise ValidationError('reconcile requires uncertainty.')
        else:
            if action not in RECONCILIATION_ACTIONS:
                raise ValidationError(
                    'Unknown resolved mutation consequence action.'
                )
            if outcome != 'uncertain':
                raise ValidationError(
                    'Resolved consequences retain the uncertain machine outcome.'
                )
        if action == 'block_manual_review' and (
            not error_class or not subreason
        ):
            raise ValidationError(
                'Manual-review blocking requires registered vocabulary.'
            )
        return consequence

    @api.model
    def _validate_prepared_request(self, request, job_id, token, job_type):
        if not isinstance(request, dict):
            raise ValidationError('Prepared mutation request must be a dict.')
        required = {
            'mutation_domain', 'operation', 'variables', 'business_intent',
            'remote_mutation_intent', 'preconditions_snapshot',
            'expected_connection_generation', 'expected_store_identity',
            'shopify_idempotency_key',
        }
        if required - set(request):
            raise ValidationError('Prepared mutation request is incomplete.')
        if (
            request['mutation_domain'] != job_type
            or not isinstance(request['operation'], str)
            or not request['operation']
            or not isinstance(request['variables'], dict)
            or not isinstance(request['business_intent'], dict)
            or not isinstance(request['remote_mutation_intent'], dict)
            or not isinstance(request['preconditions_snapshot'], dict)
            or not isinstance(request['expected_store_identity'], str)
            or not request['expected_store_identity']
            or not isinstance(request['shopify_idempotency_key'], str)
            or not request['shopify_idempotency_key']
        ):
            raise ValidationError('Prepared mutation request is malformed.')
        exact = dict(request)
        exact['variables'] = dict(request['variables'])
        exact['business_intent'] = dict(request['business_intent'])
        exact['remote_mutation_intent'] = dict(
            request['remote_mutation_intent']
        )
        exact['preconditions_snapshot'] = dict(
            request['preconditions_snapshot']
        )
        canonical_sha256({
            'job_id': job_id,
            'attempt_token': token,
            'request': exact,
        })
        return exact

    @api.model
    def _fallback_uncertain_consequence(self, exc):
        return {
            'observed_outcome': 'uncertain',
            'error_class': 'data_shape_schema_mismatch',
            'manual_review_subreason': False,
            'action': 'reconcile',
            'message': 'Mutation result was malformed; reconciliation required.',
            'evidence': {'exception_class': type(exc).__name__},
            'domain_payload': {},
        }

    @api.model
    def _owner_cleanup_values(self):
        return {
            'current_attempt_token': False,
            'owner_worker_ref': False,
            'running_since': False,
            'reconciliation_pending_until': False,
        }

    @api.model
    def _block_original_job(self, job, error_class, subreason, message):
        from_state = job.state
        values = {
            'state': 'blocked_manual_review',
            'error_class': error_class,
            'manual_review_subreason': subreason,
            'finished_at': fields.Datetime.now(),
        }
        values.update(self._owner_cleanup_values())
        job.sudo().write(values)
        job._log_transition(
            'state_change',
            self._safe_message(message, 'Mutation blocked for manual review.'),
            from_state=from_state,
            to_state='blocked_manual_review',
        )

    @api.model
    def _apply_validated_consequence(
        self, job, attempt, phase, consequence, strategy,
        reconciliation_job=False,
    ):
        consequence = self._validate_job_consequence(consequence, phase)
        action = consequence['action']
        message = consequence['message']
        from_state = job.state
        now = fields.Datetime.now()
        values = self._owner_cleanup_values()
        to_state = False
        if action == 'succeed':
            to_state = 'succeeded'
            values.update({
                'state': to_state,
                'error_class': False,
                'manual_review_subreason': False,
                'finished_at': now,
            })
        elif action == 'fail_final':
            to_state = 'failed_final'
            values.update({
                'state': to_state,
                'error_class': consequence['error_class'],
                'manual_review_subreason': False,
                'finished_at': now,
            })
        elif action == 'block_manual_review':
            to_state = 'blocked_manual_review'
            values.update({
                'state': to_state,
                'error_class': consequence['error_class'],
                'manual_review_subreason':
                    consequence['manual_review_subreason'],
                'finished_at': now,
            })
        elif action == 'cancel':
            to_state = 'cancelled'
            values.update({
                'state': to_state,
                'cancel_reason': message,
                'manual_review_subreason': False,
                'finished_at': now,
            })
        elif action == 'reconcile':
            self._ensure_reconciliation_job(job, attempt, strategy)
            values.update({
                'error_class': consequence['error_class'],
                'manual_review_subreason': False,
                'finished_at': False,
            })
        job.sudo().write(values)
        if to_state:
            job._log_transition(
                'state_change', message,
                from_state=from_state, to_state=to_state,
            )
        if action != 'reconcile':
            strategy['apply_consequence'](
                job,
                attempt,
                phase,
                consequence,
                reconciliation_job=reconciliation_job,
            )
            job.invalidate_recordset()
            if action == 'domain_callback' and job.state == 'running':
                raise ValidationError(
                    'The domain callback did not transition the mutation job.'
                )
        return True

    @api.model
    def _handle_mutation_dispatch_selftest_reconcile(self, job):
        attempt = job.mutation_attempt_id
        if not attempt:
            job._transition_failed_final(
                'unknown_system_error',
                'The reconciliation job has no mutation-attempt link.',
            )
            return
        original = attempt.job_id
        if attempt.effective_disposition() != 'unresolved':
            return
        try:
            strategy = self._validated_mutation_strategy(
                attempt.mutation_domain
            )
        except ValidationError:
            self._block_original_job(
                original,
                'no_reconciliation_strategy',
                'no_reconciliation_strategy',
                'No valid reconciliation strategy is registered.',
            )
            return
        try:
            result = strategy['reconcile'](attempt)
            normalized = self._validate_reconciliation_result(result)
        except Exception:
            self._block_original_job(
                original,
                'data_shape_schema_mismatch',
                'duplicate_risk',
                'The reconciliation result was malformed; no resend occurred.',
            )
            return
        if (
            normalized['observed_store_identity']
            != attempt.expected_store_identity
        ):
            self._block_original_job(
                original,
                'store_identity_mismatch',
                'store_identity_mismatch',
                'Reconciliation observed a different Shopify store identity.',
            )
            return
        if normalized['verdict'] == 'inconclusive':
            count = attempt._record_inconclusive_reconciliation(
                normalized['evidence']
            )
            if count >= INCONCLUSIVE_RECONCILIATION_CAP:
                self._block_original_job(
                    original,
                    'duplicate_risk',
                    'duplicate_risk',
                    'Reconciliation remained inconclusive at the safety cap.',
                )
            else:
                job._transition_retry_waiting(
                    fields.Datetime.now() + timedelta(minutes=5),
                    job.retry_count + 1,
                    'shopify_temporary_server_network',
                    normalized['message'],
                )
            return
        disposition = (
            'applied' if normalized['verdict'] == 'applied'
            else 'not_applied'
        )
        try:
            with self.env.cr.savepoint():
                attempt._record_reconciliation_result(
                    disposition, normalized['evidence'],
                )
                self._apply_validated_consequence(
                    original,
                    attempt,
                    'reconciliation',
                    normalized['consequence'],
                    strategy,
                    reconciliation_job=job,
                )
        except Exception as exc:
            raise JobHandlerError(
                'shopify_temporary_server_network',
                'Atomic reconciliation consequence failed; read retry required.',
                type(exc).__name__,
            )

    @api.model
    def _validate_reconciliation_result(self, value):
        if not isinstance(value, dict):
            raise ValidationError('A reconciliation result must be a dict.')
        required = {
            'verdict', 'observed_store_identity', 'action', 'error_class',
            'manual_review_subreason', 'message', 'evidence',
        }
        allowed = required | {'domain_payload'}
        if set(value) - allowed or required - set(value):
            raise ValidationError(
                'The reconciliation result has an invalid field set.'
            )
        verdict = value['verdict']
        identity = value['observed_store_identity']
        if verdict not in ('applied', 'not_applied', 'inconclusive'):
            raise ValidationError('Unknown reconciliation verdict.')
        if not isinstance(identity, str) or not identity:
            raise ValidationError(
                'Reconciliation must report the observed store identity.'
            )
        if not isinstance(value['evidence'], dict):
            raise ValidationError('Reconciliation evidence must be a dict.')
        message = self._safe_message(
            value['message'], 'Reconciliation result recorded.',
        )
        if verdict == 'inconclusive':
            if value['action'] not in (False, None, 'reconcile'):
                raise ValidationError(
                    'An inconclusive verdict may only continue reconciliation.'
                )
            return {
                'verdict': verdict,
                'observed_store_identity': identity,
                'message': message,
                'evidence': dict(value['evidence']),
            }
        consequence = {
            'observed_outcome': 'uncertain',
            'error_class': value['error_class'],
            'manual_review_subreason': value['manual_review_subreason'],
            'action': value['action'],
            'message': message,
            'evidence': dict(value['evidence']),
            'domain_payload': dict(value.get('domain_payload') or {}),
        }
        return {
            'verdict': verdict,
            'observed_store_identity': identity,
            'message': message,
            'evidence': dict(value['evidence']),
            'consequence': self._validate_job_consequence(
                consequence, 'reconciliation',
            ),
        }

    @api.model
    def _drain_mutation_one(self, job):
        """Execute one mutation through prepare/C1/precondition/C2/NET/C3."""
        try:
            strategy = self._validated_mutation_strategy(job.job_type)
        except ValidationError:
            self._block_original_job(
                job,
                'no_reconciliation_strategy',
                'no_reconciliation_strategy',
                'No valid mutation strategy is registered; transport refused.',
            )
            self.env.cr.commit()
            return
        if self.env['shopify.connector.mutation.attempt'].search_count([
            ('job_id', '=', job.id),
        ]):
            self._block_original_job(
                job,
                'duplicate_risk',
                'duplicate_risk',
                'Existing attempt evidence blocks mutation-job redispatch.',
            )
            self.env.cr.commit()
            return
        try:
            local_snapshot = dict(strategy['prepare_local'](job))
            canonical_sha256(local_snapshot)
        except Exception as exc:
            self._schedule_retry_or_fail(
                job,
                'shopify_temporary_server_network',
                'Local mutation preparation failed before C1.',
                type(exc).__name__,
                max_attempts=RETRY_MAX_ATTEMPTS,
            )
            self.env.cr.commit()
            return
        token = uuid.uuid4().hex
        job_id = job.id
        job_type = job.job_type
        owner_context = {
            'job_id': job_id,
            'store_id': job.store_id.id,
            'attempt_token': token,
            'mutation_domain': job_type,
        }
        from_state = job.state
        job.sudo().write({
            'state': 'running',
            'started_at': job.started_at or fields.Datetime.now(),
            'current_attempt_token': token,
            'owner_worker_ref': '%s:%s' % (self.env.cr.dbname, os.getpid()),
            'running_since': fields.Datetime.now(),
            'reconciliation_pending_until': False,
        })
        job._log_transition(
            'attempt',
            'Layer 2 mutation claim committed.',
            from_state=from_state,
            to_state='running',
        )
        self.env.flush_all()
        self.env.cr.commit()

        try:
            request = self._validate_prepared_request(
                strategy['prepare_preconditions'](
                    dict(local_snapshot), dict(owner_context),
                ),
                job_id,
                token,
                job_type,
            )
            attempt_id = self._commit_attempt_intent_c2(
                job_id, token, request,
            )
        except Exception as exc:
            self._recover_pre_c2_failure(job_id, token, exc)
            return

        try:
            raw_result = strategy['transport'](
                dict(request),
                {
                    'job_id': job_id,
                    'store_id': owner_context['store_id'],
                    'attempt_id': attempt_id,
                    'attempt_token': token,
                    'mutation_domain': request['mutation_domain'],
                },
            )
        except Exception as exc:
            raw_result = {
                'outcome': 'uncertain',
                'evidence': {
                    'exception_class': type(exc).__name__,
                    'transport': 'exception_after_c2',
                },
            }
        try:
            consequence = self._validate_job_consequence(
                strategy['classify_direct_result'](raw_result), 'direct',
            )
        except Exception as exc:
            consequence = self._fallback_uncertain_consequence(exc)
        try:
            self._commit_mutation_outcome_c3(
                job_id, attempt_id, token, consequence, strategy,
            )
        except Exception:
            self._recover_layer2_owner(job_id, token)

    @api.model
    def _recover_pre_c2_failure(self, job_id, token, exc):
        self.env.cr.rollback()
        self.env.transaction.reset()
        job = self.env['shopify.connector.job'].browse(
            job_id
        ).try_lock_for_update()
        if not job:
            self.env.cr.commit()
            return
        job.invalidate_recordset()
        attempt = self.env['shopify.connector.mutation.attempt'].search([
            ('job_id', '=', job_id),
        ], limit=1)
        if attempt:
            if attempt.attempt_token == token:
                self._ensure_reconciliation_job(job, attempt)
                job.sudo().write(self._owner_cleanup_values())
            else:
                self._block_original_job(
                    job,
                    'duplicate_risk',
                    'duplicate_risk',
                    'Concurrent attempt evidence blocked C2.',
                )
        elif job.current_attempt_token == token and job.state == 'running':
            job.sudo().write(self._owner_cleanup_values())
            self._schedule_retry_or_fail(
                job,
                'shopify_temporary_server_network',
                'Pre-C2 mutation preparation failed safely.',
                type(exc).__name__,
                max_attempts=RETRY_MAX_ATTEMPTS,
            )
        self.env.cr.commit()

    @api.model
    def _recover_layer2_owner(self, job_id, token):
        """Fresh-transaction recovery for every caught post-C2 failure."""
        self.env.cr.rollback()
        self.env.transaction.reset()
        job = self.env['shopify.connector.job'].browse(
            job_id
        ).try_lock_for_update()
        if not job:
            self.env.cr.commit()
            return
        job.invalidate_recordset()
        attempt = self.env['shopify.connector.mutation.attempt'].search([
            ('job_id', '=', job_id),
        ], limit=1)
        if attempt and attempt.transport_attempted:
            attempt = attempt.try_lock_for_update()
            if attempt and attempt.effective_disposition() == 'unresolved':
                self._ensure_reconciliation_job(job, attempt)
                job.sudo().write(self._owner_cleanup_values())
        elif job.current_attempt_token == token and job.state == 'running':
            job.sudo().write(self._owner_cleanup_values())
            self._schedule_retry_or_fail(
                job,
                'shopify_temporary_server_network',
                'Recovered a pre-C2 failure; no transport was possible.',
                False,
                max_attempts=RETRY_MAX_ATTEMPTS,
            )
        self.env.cr.commit()

    @api.model
    def _commit_attempt_intent_c2(self, job_id, token, request):
        side_cr = self.env.registry.cursor()
        try:
            side_context = dict(self.env.context)
            side_context[C2_SENTINEL_CONTEXT] = C2_SIDE_CURSOR_SENTINEL
            side_env = api.Environment(side_cr, self.env.uid, side_context)
            exact_request = {
                'operation': request['operation'],
                'variables': request['variables'],
            }
            attempt = side_env[
                'shopify.connector.mutation.attempt'
            ]._create_attempt_intent({
                'job_id': job_id,
                'attempt_token': token,
                'mutation_domain': request['mutation_domain'],
                'expected_connection_generation':
                    request['expected_connection_generation'],
                'expected_store_identity':
                    request['expected_store_identity'],
                'remote_mutation_intent':
                    request['remote_mutation_intent'],
                'preconditions_snapshot':
                    request['preconditions_snapshot'],
                'business_intent_fingerprint': canonical_sha256(
                    request['business_intent']
                ),
                'exact_request_fingerprint': canonical_sha256(exact_request),
                'shopify_idempotency_key':
                    request['shopify_idempotency_key'],
            })
            attempt_id = attempt.id
            side_cr.commit()
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()
        return attempt_id

    @api.model
    def _commit_mutation_outcome_c3(
        self, job_id, attempt_id, token, consequence, strategy,
    ):
        self.env.transaction.reset()
        locked = self.env['shopify.connector.job'].browse(
            job_id
        ).try_lock_for_update()
        if not locked:
            raise ValidationError(
                'C3 could not reacquire the mutation job owner row.'
            )
        locked.invalidate_recordset()
        if (
            locked.state != 'running'
            or locked.current_attempt_token != token
        ):
            raise ValidationError(
                'C3 mutation owner state/token mismatch; outcome refused.'
            )
        attempt = self.env[
            'shopify.connector.mutation.attempt'
        ].browse(attempt_id).try_lock_for_update()
        if not attempt:
            raise ValidationError(
                'C3 could not reacquire the mutation attempt row.'
            )
        attempt.invalidate_recordset()
        if (
            attempt.attempt_token != token
            or attempt.job_id != locked
            or attempt.observed_outcome != 'pending'
        ):
            raise ValidationError('C3 mutation attempt identity mismatch.')
        consequence = self._validate_job_consequence(consequence, 'direct')
        attempt._record_direct_outcome(
            consequence['observed_outcome'],
            evidence=consequence['evidence'],
        )
        locked.store_id.invalidate_recordset()
        identity_mismatch = (
            locked.store_id.connection_generation
            != attempt.expected_connection_generation
            or locked.store_id.shop_domain
            != attempt.expected_store_identity
            or locked.job_type != attempt.mutation_domain
        )
        if identity_mismatch:
            self._block_original_job(
                locked,
                'store_identity_mismatch',
                'store_identity_mismatch',
                'Local store generation or identity changed before C3.',
            )
        else:
            self._apply_validated_consequence(
                locked,
                attempt,
                'direct',
                consequence,
                strategy,
            )
        self.env.cr.flush()
        self.env.cr.commit()

    @api.model
    def _ensure_reconciliation_job(self, original_job, attempt, strategy=None):
        try:
            strategy = strategy or self._validated_mutation_strategy(
                attempt.mutation_domain
            )
        except ValidationError:
            self._block_original_job(
                original_job,
                'no_reconciliation_strategy',
                'no_reconciliation_strategy',
                'No valid reconciliation strategy exists for this attempt.',
            )
            return self.env['shopify.connector.job']
        locked_attempt = attempt.try_lock_for_update()
        if not locked_attempt:
            return self.env['shopify.connector.job']
        Job = self.env['shopify.connector.job']
        existing = Job.search([
            ('mutation_attempt_id', '=', attempt.id),
        ], limit=1)
        if existing:
            if (
                existing.state in ('succeeded', 'failed_final', 'cancelled')
                and attempt.effective_disposition() == 'unresolved'
                and original_job.state != 'blocked_manual_review'
            ):
                self._block_original_job(
                    original_job,
                    'duplicate_risk',
                    'duplicate_risk',
                    'The reconciliation job is terminal while unresolved.',
                )
            return existing
        return Job.sudo().create({
            'store_id': original_job.store_id.id,
            'job_source': 'reconciliation',
            'job_type': strategy['reconciliation_job_type'],
            'state': 'queued',
            'payload_hash': 'reconcile:%s' % attempt.attempt_token,
            'mutation_attempt_id': attempt.id,
            'expected_connection_generation':
                attempt.expected_connection_generation,
        })

    @api.model
    def _concurrency_retry_supported(self):
        """Whether the per-job transaction boundary (:meth:`_drain_one`) can
        manage its own commit/rollback on the current cursor.

        That boundary commits each job on success and rolls back + recovers on
        a genuine concurrency failure. The Odoo test runner replaces the shared
        ``TransactionCase`` cursor's ``commit`` with a guard that raises, so the
        boundary runs on production and on the genuine independent-connection
        lifecycle tests (real pooled ``db_connect`` cursors) and is bypassed on
        the shared in-test cursor -- where a genuine PostgreSQL serialization
        failure cannot occur on the single shared connection anyway. Detected by
        the forbidden-commit guard rather than ``in_test_mode()``, because the
        genuine tests are themselves in test mode yet legitimately commit on
        their own real cursors.
        """
        commit = getattr(self.env.cr, 'commit', None)
        return getattr(commit, '__name__', '') != 'forbidden'

    # ------------------------------------------------------------------
    # Registry / domain-extension seam (Decision B)
    # ------------------------------------------------------------------

    @api.model
    def _get_handlers(self):
        """`job_type` -> handler mapping.

        Domain-extension seam: override via classic Odoo inheritance
        (`_inherit = 'shopify.connector.job.dispatch'`), calling
        `super()._get_handlers()` and updating the returned dict with
        additional `job_type` -> handler entries -- never removing or
        overwriting a core-owned entry. Adapts (does not copy) the
        `_get_checks()` inheritance-append precedent
        (`shopify_connector_readiness_check.py`): a job routes to
        exactly one handler by `job_type` key lookup -- it does not
        aggregate every registered handler the way `_get_checks()`
        aggregates independently-evaluated checks.
        """
        return {
            'core_dispatch_selftest': self._handle_core_dispatch_selftest,
            'mutation_dispatch_selftest': (
                self._handle_mutation_dispatch_selftest
            ),
            'mutation_dispatch_selftest_reconcile': (
                self._handle_mutation_dispatch_selftest_reconcile
            ),
        }

    @api.model
    def _handle_core_dispatch_selftest(self, job):
        """No-op diagnostic handler for `core_dispatch_selftest`
        (Decision F) -- exercises the registry/dispatch mechanism only.
        Never calls Shopify, never represents domain sync."""
        return None

    @api.model
    def _get_replay_policies(self):
        """`job_type` -> replay policy (DEC-031 Layer 1, AR-048).

        Same domain-extension seam shape as `_get_handlers()`: override
        via classic Odoo inheritance, calling
        `super()._get_replay_policies()` and updating the returned dict
        with additional `job_type` -> policy entries -- never removing
        or overwriting a core-owned entry. Every key `_get_handlers()`
        returns must have an explicit entry here (build-time
        completeness invariant, `test_job_dispatch.py`); the runtime
        lookup (`_get_replay_policy`) independently stays fail-closed
        for any undeclared `job_type` regardless of that test.
        """
        return {
            'core_dispatch_selftest': REPLAY_POLICY_LOCAL_ONLY,
            'mutation_dispatch_selftest': (
                REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE
            ),
            'mutation_dispatch_selftest_reconcile': (
                REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE
            ),
        }

    @api.model
    def _get_replay_policy(self, job_type):
        """Fail-closed replay-policy lookup for a single `job_type`.

        Returns the explicitly registered policy
        (:meth:`_get_replay_policies`) when present; defaults any
        unexpected or undeclared `job_type` to the conservative
        `remote_effect_not_replay_safe` -- never a read-safe default.
        """
        return self._get_replay_policies().get(
            job_type, REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    @api.model
    def _dispatch_one(self, job):
        """Start a claimed job, then invoke its registered handler."""
        if not self._start_running(job):
            return
        self._invoke_handler(job)

    @api.model
    def _start_running(self, job):
        """Checkpoint 2: the `state` -> `running` transition, through
        `shopify.connector.job`'s own `write()` (the unmodified
        store-state gate plus the new domain-flag gate).

        If a gating check blocks the start, the job is routed to
        `failed_retryable` with `error_class='odoo_validation_
        configuration'` -- a visible, audited outcome (via the existing
        `_transition_failed_retryable()` helper, logged exclusively
        through `_system_append()`) rather than silently remaining
        `queued`/`retry_waiting` forever. This does not bypass or weaken
        either gate: the sanctioned protected write still raises exactly as
        before -- this only makes an already-blocked start observable,
        as a configuration/state problem an operator can correct and
        retry later (the same DEC-009 "manual fix then retry" class
        `odoo_validation_configuration` already routes to via
        `_route_failure()`). Never raises out of the drain loop, so one
        blocked job never stops the rest of the batch -- `write()`
        either succeeds (returns `True`) or is caught here and routed
        to `failed_retryable` (returns `False`).
        """
        JobLog = self.env['shopify.connector.job.log']
        from_state = job.state
        try:
            job.sudo().write({
                'state': 'running',
                'started_at': job.started_at or fields.Datetime.now(),
            })
        except ValidationError as exc:
            job._transition_failed_retryable(
                error_class='odoo_validation_configuration',
                message=(
                    'Job could not start: a start-time gating check '
                    'blocked it (%s).' % str(exc)
                ),
            )
            return False
        JobLog._system_append(
            job, 'attempt', 'Dispatch attempt started.',
            from_state=from_state, to_state='running',
        )
        return True

    @api.model
    def _invoke_handler(self, job):
        """Checkpoint 3 (SRR-03 narrowing) + handler invocation +
        outcome routing.

        Re-checks store state immediately before invoking the handler --
        this narrows, but per the Task 006C gate-opening proposal's own
        explicit framing never claims to close, the disconnect/
        in-flight-job race (Decision A / implementation-scope §F item
        9). A job whose `job_type` has no registered handler fails
        safely (never hangs, never silently drops).
        """
        if job.job_type == 'historic_domain_job':
            # LC-1 / DEC-030: this permanent sink has no handler by design.
            # The ondelete conversion leaves only terminal rows, but a
            # directly-created/malformed non-terminal row must still fail
            # closed instead of falling into any future domain handler.
            job._transition_failed_final(
                error_class='unknown_system_error',
                message=(
                    'Historic domain jobs are audit-only and cannot be '
                    'dispatched.'
                ),
            )
            return

        store = job.store_id
        store.invalidate_recordset()
        if (
            job.job_source in BUSINESS_JOB_SOURCES
            and store.state != 'connected'
        ):
            job._transition_skipped(
                'Store is no longer connected immediately before '
                'dispatch -- skipped without invoking a handler.'
            )
            return

        handler = self._get_handlers().get(job.job_type)
        if handler is None:
            job._transition_failed_final(
                error_class='unknown_system_error',
                message='No handler is registered for job_type %r.' % (
                    job.job_type,
                ),
            )
            return

        try:
            handler(job)
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            # A genuine PostgreSQL concurrency failure (SQLSTATE
            # 40001/40P01/55P03) has aborted the transaction. It must NEVER
            # be caught and routed through an ORM write here: that write
            # would run inside the already-aborted transaction and fail as
            # InFailedSqlTransaction, masking the real conflict. Re-raise it
            # unchanged so the drain's per-job outer boundary rolls back,
            # resets the environment, REACQUIRES the exact job under a real
            # row lock and -- without the recovery call re-invoking this
            # handler -- routes it once through its declared DEC-031 Layer 1
            # replay policy (``_drain_one`` /
            # ``_recover_after_concurrency_conflict``): a bounded
            # ``concurrency_race_conflict`` retry only for
            # ``local_only``/``remote_read_replay_safe`` jobs, manual review
            # for ``remote_effect_not_replay_safe``/undeclared ones.
            # (Classified handler
            # conflicts a handler can detect BEFORE poisoning the transaction
            # still raise ``JobHandlerError('concurrency_race_conflict', ...)``
            # and route below.)
            raise
        except JobHandlerError as exc:
            self._route_failure(
                job, exc.error_class, exc.reason, exc.technical_detail,
            )
            return
        except Exception as exc:  # fail-safe dispatcher boundary
            self._route_failure(
                job, 'unknown_system_error', str(exc), repr(exc),
            )
            return

        if job.state != 'running':
            return
        JobLog = self.env['shopify.connector.job.log']
        from_state = job.state
        job.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt', 'Dispatch succeeded.',
            from_state=from_state, to_state='succeeded',
        )

    # ------------------------------------------------------------------
    # Retry / failure routing (DEC-009 taxonomy)
    # ------------------------------------------------------------------

    @api.model
    def _route_failure(self, job, error_class, reason, technical_detail=False):
        """Route a classified handler failure to the correct terminal/
        loop-back job state, per the DEC-009 error-class taxonomy
        encoded in this module's constants above."""
        if error_class in MANUAL_REVIEW_ERROR_CLASSES:
            job._transition_blocked_manual_review(
                error_class=error_class,
                manual_review_subreason=error_class,
                message=reason, technical_detail=technical_detail,
            )
            return
        if (
            error_class in MANUAL_FIX_THEN_RETRY_ERROR_CLASSES
            or error_class in CONSERVATIVE_NEVER_SILENT_ERROR_CLASSES
        ):
            job._transition_failed_retryable(
                error_class=error_class, message=reason,
                technical_detail=technical_detail,
            )
            return
        if error_class in AUTO_RETRY_ERROR_CLASSES:
            self._schedule_retry_or_fail(
                job, error_class, reason, technical_detail,
                max_attempts=RETRY_MAX_ATTEMPTS,
            )
            return
        if error_class in SAFETY_NET_ERROR_CLASSES:
            self._schedule_retry_or_fail(
                job, error_class, reason, technical_detail,
                max_attempts=SAFETY_NET_MAX_ATTEMPTS,
            )
            return
        # Unclassified error_class (should never happen -- the fixed
        # 16-class registry is exhaustive) -- fail safe, never hang.
        job._transition_failed_final(
            error_class='unknown_system_error', message=reason,
            technical_detail=technical_detail,
        )

    @api.model
    def _schedule_retry_or_fail(
        self, job, error_class, reason, technical_detail, max_attempts,
    ):
        """Bounded retries only -- no infinite retries under any
        circumstance (DEC-009). Fails permanently once either the
        attempt budget or the 24-hour retry window is exhausted,
        whichever comes first."""
        new_retry_count = job.retry_count + 1
        started_at = job.started_at or fields.Datetime.now()
        elapsed = fields.Datetime.now() - started_at
        if (
            new_retry_count > max_attempts
            or elapsed > timedelta(hours=RETRY_WINDOW_HOURS)
        ):
            # The job did attempt and fail again -- persist the
            # exhausted attempt count (one more than its last recorded
            # retry_count), not just the terminal state.
            job._transition_failed_final(
                error_class=error_class, message=reason,
                technical_detail=technical_detail,
                retry_count=new_retry_count,
            )
            return
        delay_seconds = self._retry_delay_seconds(new_retry_count - 1)
        next_retry_at = fields.Datetime.now() + timedelta(seconds=delay_seconds)
        job._transition_retry_waiting(
            next_retry_at=next_retry_at, retry_count=new_retry_count,
            error_class=error_class, message=reason,
            technical_detail=technical_detail,
        )

    @api.model
    def _retry_delay_seconds(self, attempt_index):
        """Jittered exponential backoff (Decision C): base 30s, x2 per
        attempt, capped at 30 minutes, +/-20% jitter. `attempt_index` is
        zero-based (0 = first retry).

        Tests may patch `random.uniform` for a deterministic value, or
        assert bounds on the returned delay -- this must never be
        flaky by relying on unseeded randomness or wall-clock timing for
        a pass/fail result.
        """
        capped = min(
            RETRY_BASE_DELAY_SECONDS * (RETRY_MULTIPLIER ** attempt_index),
            RETRY_MAX_DELAY_SECONDS,
        )
        jitter_amount = capped * RETRY_JITTER_FRACTION
        return capped + random.uniform(-jitter_amount, jitter_amount)
