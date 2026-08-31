"""Shared V2 mutation hooks layered after the protected dispatcher.

This module is intentionally an inherited model extension.  It owns the
additive V2 job vocabulary, the common C1/C2/C3 fence calls, and V2
reconciliation lineage without enlarging the legacy dispatcher source.
"""

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ShopifyConnectorV2MutationDispatch(models.AbstractModel):
    """Add V2 mutation admission to the established Layer-2 protocol."""

    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_v2_job_types(self):
        """Return additive claimable V2 types; domain addons extend this."""
        return frozenset()

    @api.model
    def _get_v2_mutation_job_types(self):
        """Return V2 types that own durable mutation attempts."""
        return frozenset()

    @api.model
    def _is_v2_mutation_job(self, job, *, attempt=False):
        """Recognize V2 from its job marker or durable C2 lineage.

        A nullable ``job.run_id`` is not strong enough after C2: a damaged or
        deleted relation must never demote a durable mutation attempt into the
        legacy transport path.  Before C2, an explicitly assigned V2 lane is
        the fail-closed marker.  After C2, the immutable attempt run/domain is
        authoritative and scope validation reports any job drift.
        """
        if not job:
            return False
        registered = self._get_v2_mutation_job_types()
        if (
            attempt
            and getattr(attempt, 'run_id', False)
            and attempt.mutation_domain in registered
        ):
            return True
        return bool(
            job.job_type in registered
            and (getattr(job, 'run_id', False) or getattr(job, 'lane', False))
        )

    @api.model
    def _v2_validate_mutation_job(self, job, *, phase='c1'):
        """Domain-specific mode/object validation hook; local only."""
        del job, phase
        return True

    @api.model
    def _v2_admit_mutation_job(self, job, *, phase='c1', attempt=False):
        """Apply the shared mode/run/company/store/generation fence."""
        # A queued/retry original that already owns a committed C2 attempt is
        # not a fresh C1 candidate.  Let the recovery path below consume it
        # into one read-only reconciliation child; otherwise a stale
        # generation/cancel flag would block it here and leave the durable
        # remote-effect evidence stranded.  Malformed evidence deliberately
        # returns False and is blocked by the caller.
        queued_attempt = self._v2_queued_c2_attempt(job)
        if queued_attempt is False:
            return False
        if queued_attempt is not None:
            return True
        if not self._is_v2_mutation_job(job, attempt=attempt):
            return True
        try:
            reason = self.env[
                'shopify.connector.mutation.attempt'
            ]._v2_scope_mismatch(job, attempt=attempt, lock=True)
            if reason:
                return False
            return bool(self._v2_validate_mutation_job(job, phase=phase))
        except (AccessError, ValidationError):
            # Admission failures are safe local blocks.  C2's caller turns
            # this false result into a side-cursor rollback via ValidationError.
            return False

    @api.model
    def _v2_queued_c2_attempt(self, job):
        """Return a valid queued/retry C2 attempt, or a fail-closed marker.

        ``None`` means the job is not a queued/retry V2 recovery candidate;
        an attempt record means its immutable C2 evidence is structurally
        complete; ``False`` means a V2-looking candidate is malformed.  This
        check is intentionally local and side-effect free.  The caller still
        owns the claim lock and the recovery routine re-locks the attempt
        before recording evidence or creating the unique reconciliation child.
        """
        if not job or job.state not in ('queued', 'retry_waiting'):
            return None
        attempts = self.env[
            'shopify.connector.mutation.attempt'
        ].sudo().search([
            ('job_id', '=', job.id),
        ], order='id asc')
        if not attempts:
            return None
        registered = frozenset(self._get_v2_mutation_job_types())
        looks_v2 = bool(getattr(job, 'run_id', False)) or any(
            getattr(item, 'run_id', False)
            and item.mutation_domain in registered
            for item in attempts
        )
        if not looks_v2:
            return None
        if len(attempts) != 1:
            return False
        attempt = attempts[0]
        try:
            strategy = self._validated_mutation_strategy(
                attempt.mutation_domain,
            )
        except ValidationError:
            return False
        run = getattr(attempt, 'run_id', False)
        # After C2 the attempt's run/store identity is authoritative.  The
        # original job is still the durable parent, but its mutable runtime
        # projection (run pointer, type, owner token and captured generations)
        # may have drifted while a recovery transaction was being lost.
        store = run.store_id if run else False
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        ) if store else False
        required_strings = (
            attempt.attempt_token,
            attempt.mutation_domain,
            attempt.expected_store_identity,
            attempt.business_intent_fingerprint,
            attempt.exact_request_fingerprint,
            attempt.shopify_idempotency_key,
        )
        valid = (
            bool(run and store and settings)
            and attempt.transport_attempted is True
            and attempt.observed_outcome in ('pending', 'uncertain')
            and not attempt.resolution_disposition
            and not attempt.resolution_source
            and all(
                isinstance(value, str) and value
                for value in required_strings
            )
            and isinstance(attempt.remote_mutation_intent, dict)
            and isinstance(attempt.preconditions_snapshot, dict)
            and attempt.transport_at
            and type(attempt.expected_connection_generation) is int
            and attempt.expected_connection_generation >= 0
            and type(attempt.expected_configuration_generation) is int
            and attempt.expected_configuration_generation >= 0
            and attempt.job_id == job
            and run.store_id == store
            and attempt.run_id == run
            and attempt.store_id == store
            and attempt.mutation_domain in registered
            and store.company_id
            and store.company_id == run.company_id
            and settings.company_id == store.company_id
            and attempt.expected_store_identity == store.shop_domain
            and store.shop_domain
            and store.api_version
            and strategy['reconciliation_job_type']
        )
        return attempt if valid else False

    @api.model
    def _v2_recover_queued_c2_attempt(self, job):
        """Move one claimed queued/retry C2 original to reconciliation.

        The original is made non-claimable only after the unique reconciliation
        child is present.  A connected store keeps the original in ``running``
        with no worker owner, matching the established C3 ``reconcile``
        posture; a disconnecting store cannot restart the original business
        job, so it is blocked while its read child remains the only recovery
        route.  Any malformed or uncreatable evidence is blocked and never
        reaches a mutation handler.
        """
        attempt = self._v2_queued_c2_attempt(job)
        if attempt is None:
            return False
        if attempt is False:
            self._block_v2_admission(
                job,
                'Malformed durable V2 C2 evidence blocked redispatch; no '
                'Shopify mutation was resent.',
            )
            return True
        reconciliation = self.env['shopify.connector.job']
        try:
            with self.env.cr.savepoint():
                reconciliation = self._recover_committed_attempt_to_reconciliation(
                    job,
                    attempt,
                    'post_c2_owner_recovery',
                    'dispatcher_recovery',
                )
        except Exception:
            # A unique child created by a competing recovery is still the
            # correct outcome.  Re-read it before deciding that evidence is
            # malformed or stranded.
            reconciliation = self.env['shopify.connector.job'].sudo().search([
                ('mutation_attempt_id', '=', attempt.id),
            ], limit=1)
        if not reconciliation:
            self._block_v2_admission(
                job,
                'Durable V2 C2 evidence could not be linked to a single '
                'reconciliation job; no Shopify mutation was resent.',
            )
            return True
        if job.state not in ('queued', 'retry_waiting'):
            return True
        lineage_drift = (
            job.job_type != attempt.mutation_domain
            or not getattr(job, 'run_id', False)
            or job.run_id != attempt.run_id
            or job.current_attempt_token != attempt.attempt_token
            or job.expected_connection_generation
            != attempt.expected_connection_generation
            or job.expected_configuration_generation
            != attempt.expected_configuration_generation
        )
        if job.store_id.state == 'connected' and not lineage_drift:
            from_state = job.state
            try:
                job.sudo().write({
                    'state': 'running',
                    'started_at': job.started_at or fields.Datetime.now(),
                    'current_attempt_token': False,
                    'owner_worker_ref': False,
                    'running_since': False,
                    'reconciliation_pending_until': False,
                })
            except Exception:
                self._block_v2_admission(
                    job,
                    'The recovered V2 original could not be held out of the '
                    'mutation queue; no Shopify mutation was resent.',
                )
                return True
            job._log_transition(
                'state_change',
                'Durable C2 evidence recovered through one read-only '
                'reconciliation job; mutation redispatch was suppressed.',
                from_state=from_state,
                to_state='running',
            )
        elif lineage_drift:
            self._block_v2_admission(
                job,
                'Durable V2 C2 evidence was recovered through reconciliation, '
                'but the original job lineage drifted; no mutation was resent.',
            )
        else:
            self._block_v2_admission(
                job,
                'Durable V2 C2 evidence was recovered through reconciliation; '
                'the original business job remains blocked while the store '
                'is not connected.',
            )
        return True

    @api.model
    def _block_v2_admission(self, job, message=None):
        self._block_original_job(
            job,
            'store_identity_mismatch',
            'store_identity_mismatch',
            message or (
                'V2 mutation admission is stale or outside the current '
                'store, company, generation, or runtime mode.'
            ),
        )

    @api.model
    def _v2_locked_job_identity(self, job_id):
        """Read one V2 job/store/settings snapshot under a short lock.

        The cursor is committed and closed before the caller continues with
        request preparation, so this helper never holds a scope lock during
        C2 or Shopify transport.
        """
        side_cr = self.env.registry.cursor()
        try:
            side_env = api.Environment(side_cr, self.env.uid, dict(self.env.context))
            job = side_env['shopify.connector.job'].browse(
                job_id,
            ).try_lock_for_update()
            if not job:
                raise ValidationError('The mutation job is unavailable.')
            scope = side_env[
                'shopify.connector.mutation.attempt'
            ]._v2_locked_scope(job)
            if not scope:
                raise ValidationError('The mutation job scope is unavailable.')
            job, _attempt, run, store, settings = scope
            result = {
                'is_v2': bool(
                    run
                    and job.job_type in side_env[
                        'shopify.connector.job.dispatch'
                    ]._get_v2_mutation_job_types()
                ),
                'job_id': job.id,
                'run_id': run.id if run else False,
                'expected_connection_generation':
                    store.connection_generation if store else 0,
                'expected_store_identity':
                    store.shop_domain if store else False,
                'expected_configuration_generation': (
                    settings.configuration_generation if settings else 0
                ),
            }
            side_cr.commit()
            return result
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()

    @api.model
    def _drain_mutation_one(self, job):
        """Fence C1 before strategy preparation or any transport call."""
        if self._v2_recover_queued_c2_attempt(job):
            self.env.cr.commit()
            return
        if not self._v2_admit_mutation_job(job, phase='c1'):
            self._block_v2_admission(job)
            self.env.cr.commit()
            return
        return super()._drain_mutation_one(job)

    @api.model
    def _dispatch_one(self, job):
        """Never let durable V2 evidence fall into an ordinary handler.

        This guard is intentionally before the generic running transition.
        It covers a damaged or manually requeued original whose nullable run
        or current job type no longer identifies the C2 mutation.  The durable
        attempt may only move toward readback/manual review; it can never
        authorize another handler invocation.
        """
        if self._v2_recover_queued_c2_attempt(job):
            return
        attempt = self.env['shopify.connector.mutation.attempt'].sudo().search([
            ('job_id', '=', job.id),
            ('run_id', '!=', False),
        ], limit=1)
        if attempt:
            if attempt.transport_attempted:
                self._recover_committed_attempt_to_reconciliation(
                    job,
                    attempt,
                    'redispatch_with_durable_c2',
                    'dispatcher_recovery',
                )
                if job.state != 'running':
                    self._block_original_job(
                        job,
                        'duplicate_risk',
                        'duplicate_risk',
                        'Durable V2 mutation evidence blocked redispatch; '
                        'read-only reconciliation was queued.',
                    )
            else:
                self._block_original_job(
                    job,
                    'duplicate_risk',
                    'duplicate_risk',
                    'Malformed durable V2 mutation evidence blocked '
                    'redispatch.',
                )
            return
        return super()._dispatch_one(job)

    @api.model
    def _validated_mutation_strategy(self, mutation_domain):
        """Wrap registered V2 transport with the final locked admission."""
        strategy = super()._validated_mutation_strategy(mutation_domain)
        if mutation_domain not in self._get_v2_mutation_job_types():
            return strategy
        transport = strategy['transport']

        def transport_with_final_admission(request, attempt_context):
            self._v2_assert_transport_admission(attempt_context)
            return transport(request, attempt_context)

        strategy = dict(strategy)
        strategy['transport'] = transport_with_final_admission
        return strategy

    @api.model
    def _v2_assert_transport_admission(self, attempt_context):
        """Atomically authorize transport immediately before the network call.

        The short-lived side cursor locks every owner/scope row, validates
        immutable attempt identity and all live generations/mode/cancellation
        fences, commits that serialization point, and closes before the
        domain transport callback runs.
        """
        side_cr = self.env.registry.cursor()
        try:
            side_env = api.Environment(side_cr, self.env.uid, dict(self.env.context))
            Dispatch = side_env['shopify.connector.job.dispatch']
            Attempt = side_env['shopify.connector.mutation.attempt']
            job = side_env['shopify.connector.job'].browse(
                attempt_context.get('job_id'),
            )
            attempt = Attempt.browse(attempt_context.get('attempt_id'))
            scope = Attempt._v2_locked_scope(job, attempt=attempt)
            if not scope:
                raise ValidationError(
                    'The V2 transport owner or attempt is unavailable.'
                )
            job, attempt, run, store, settings = scope
            if not run or not store or not settings:
                raise ValidationError('The V2 transport scope is incomplete.')
            if not Dispatch._is_v2_mutation_job(job, attempt=attempt):
                raise ValidationError('The V2 mutation type is not registered.')
            if (
                job.state != 'running'
                or not job.owner_worker_ref
                or job.current_attempt_token != attempt_context.get(
                    'attempt_token'
                )
                or attempt.attempt_token != job.current_attempt_token
                or attempt.job_id != job
                or attempt.mutation_domain != job.job_type
                or attempt.observed_outcome != 'pending'
                or not attempt.transport_attempted
                or attempt_context.get('mutation_domain') != job.job_type
                or attempt_context.get('store_id') != store.id
                or job.store_id != store
                or attempt.store_id != store
                or attempt.run_id != run
            ):
                raise ValidationError(
                    'The V2 transport owner or attempt identity is stale.'
                )
            if not Dispatch._v2_admit_mutation_job(
                job, phase='transport', attempt=attempt,
            ):
                raise ValidationError(
                    'The V2 transport admission fence failed.'
                )
            side_cr.commit()
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()

    @api.model
    def _validate_prepared_request(self, request, job_id, token, job_type):
        """Canonicalize V2 identity in the in-memory prepared request."""
        exact = super()._validate_prepared_request(
            request, job_id, token, job_type,
        )
        job = self.env['shopify.connector.job'].browse(job_id).exists()
        if not self._is_v2_mutation_job(job):
            return exact
        identity = self._v2_locked_job_identity(job_id)
        if not identity or not identity['is_v2']:
            raise ValidationError(
                'Prepared V2 request lost its durable run identity.'
            )
        expected_run_id = identity['run_id']
        supplied_run_id = exact.get('run_id', expected_run_id)
        if getattr(supplied_run_id, 'id', supplied_run_id) != expected_run_id:
            raise ValidationError(
                'Prepared V2 request run identity does not match the job.'
            )
        expected_connection = identity['expected_connection_generation']
        supplied_connection = exact['expected_connection_generation']
        if isinstance(supplied_connection, bool):
            raise ValidationError(
                'Prepared V2 connection generation must be an integer.'
            )
        try:
            supplied_connection = int(supplied_connection)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                'Prepared V2 connection generation must be an integer.'
            ) from exc
        if supplied_connection != expected_connection:
            raise ValidationError(
                'Prepared V2 connection generation is stale.'
            )
        expected_store_identity = identity['expected_store_identity']
        if exact['expected_store_identity'] != expected_store_identity:
            raise ValidationError('Prepared V2 store identity is stale.')
        expected_configuration = identity[
            'expected_configuration_generation'
        ]
        supplied_configuration = exact.get(
            'expected_configuration_generation', expected_configuration,
        )
        if isinstance(supplied_configuration, bool):
            raise ValidationError(
                'Prepared V2 configuration generation must be an integer.'
            )
        try:
            supplied_configuration = int(supplied_configuration)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                'Prepared V2 configuration generation must be an integer.'
            ) from exc
        if supplied_configuration != expected_configuration:
            raise ValidationError(
                'Prepared V2 configuration generation is stale.'
            )
        exact['run_id'] = expected_run_id
        exact['expected_connection_generation'] = expected_connection
        exact['expected_store_identity'] = expected_store_identity
        exact['expected_configuration_generation'] = expected_configuration
        return exact

    @api.model
    def _v2_force_reconcile_consequence(self, consequence):
        """Convert a stale direct result into a bounded readback decision."""
        evidence = dict(consequence.get('evidence') or {})
        evidence['v2_c3_admission'] = 'reconciliation_required'
        return {
            'observed_outcome': 'uncertain',
            'error_class': 'store_identity_mismatch',
            'manual_review_subreason': False,
            'action': 'reconcile',
            'message': (
                'V2 mutation scope changed before C3; read-only '
                'reconciliation is required.'
            ),
            'evidence': evidence,
            'domain_payload': dict(consequence.get('domain_payload') or {}),
        }

    @api.model
    def _apply_validated_consequence(
        self, job, attempt, phase, consequence, strategy,
        reconciliation_job=False,
    ):
        """Never block a stale direct result before reconciliation enqueue."""
        if (
            phase in ('reconciliation', 'manual_resolution')
            and getattr(attempt, 'run_id', False)
            and job.job_type != attempt.mutation_domain
        ):
            self._block_original_job(
                job,
                'store_identity_mismatch',
                'store_identity_mismatch',
                'Durable mutation-domain lineage changed; the local '
                'consequence was refused.',
            )
            return True
        if (
            phase == 'direct'
            and self._is_v2_mutation_job(job, attempt=attempt)
            and not self._v2_admit_mutation_job(
                job, phase='c3', attempt=attempt,
            )
        ):
            if attempt.observed_outcome == 'pending':
                attempt._record_recovery_uncertain(
                    'c3_scope_fence', 'dispatcher_recovery',
                )
            consequence = self._v2_force_reconcile_consequence(consequence)
        return super()._apply_validated_consequence(
            job, attempt, phase, consequence, strategy,
            reconciliation_job=reconciliation_job,
        )

    @api.model
    def _commit_mutation_outcome_c3(
        self, job_id, attempt_id, token, consequence, strategy,
    ):
        """Record a stale V2 result as uncertain, then use base reconcile C3."""
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
        v2_stale = (
            self._is_v2_mutation_job(locked, attempt=attempt)
            and not self._v2_admit_mutation_job(
                locked, phase='c3', attempt=attempt,
            )
        )
        locked.store_id.invalidate_recordset()
        identity_mismatch = (
            locked.store_id.connection_generation
            != attempt.expected_connection_generation
            or locked.store_id.shop_domain
            != attempt.expected_store_identity
            or locked.job_type != attempt.mutation_domain
        )
        if v2_stale:
            forced = self._v2_force_reconcile_consequence(consequence)
            attempt._record_direct_outcome(
                'uncertain', evidence=forced['evidence'],
            )
            self._apply_validated_consequence(
                locked, attempt, 'direct', forced, strategy,
            )
        else:
            attempt._record_direct_outcome(
                consequence['observed_outcome'],
                evidence=consequence['evidence'],
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
        """Attach V2 run lineage to the existing reconciliation record."""
        result = super()._ensure_reconciliation_job(
            original_job, attempt, strategy,
        )
        run = getattr(attempt, 'run_id', False) or getattr(
            original_job, 'run_id', False,
        )
        if not run or not result:
            return result
        store = attempt.store_id
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().search([('store_id', '=', store.id)], limit=1)
        if (
            not store
            or run.store_id != store
            or original_job.store_id != store
            or not settings
            or settings.company_id != store.company_id
        ):
            self._block_original_job(
                original_job,
                'store_identity_mismatch',
                'store_identity_mismatch',
                'The durable V2 attempt cannot be linked to a safe '
                'reconciliation scope.',
            )
            return result
        result.sudo().write({
            'run_id': run.id,
            'parent_job_id': original_job.id,
            'expected_connection_generation': store.connection_generation,
            'expected_configuration_generation':
                settings.configuration_generation,
            'lane': 'safety_verification',
            'lane_priority': 1000,
            'available_at': fields.Datetime.now(),
        })
        return result


__all__ = ['ShopifyConnectorV2MutationDispatch']
