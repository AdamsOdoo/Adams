from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError


STALE_OWNER_TIMEOUT_MINUTES = 30
STALE_OWNER_BATCH_SIZE = 20
STALE_OWNER_TIMEOUT_PARAM = (
    'shopify_connector.layer2_stale_owner_timeout_minutes'
)
STALE_OWNER_BATCH_PARAM = 'shopify_connector.layer2_stale_owner_batch_size'


class ShopifyConnectorStaleOwnerSweep(models.AbstractModel):
    _name = 'shopify.connector.stale.owner.sweep'
    _description = 'Shopify Connector Layer 2 Stale Owner Sweep'

    @api.model
    def _positive_int_parameter(self, name, default):
        raw = self.env['ir.config_parameter'].sudo().get_param(
            name, default,
        )
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return value if value > 0 else default

    @api.model
    def _sweep_v2_mutation_owners(self, *, job_types=None):
        """Recover stale V2 mutation owners without replaying transport.

        V2 read-only attempts are handled by the P10 side-cursor repository;
        this method handles only mutation types explicitly registered by a
        domain addon.  A committed mutation attempt is always moved to the
        existing reconciliation job.  Only a stale C1 owner with no attempt
        can be requeued automatically.
        """
        Dispatch = self.env['shopify.connector.job.dispatch']
        registered = frozenset(Dispatch._get_v2_mutation_job_types())
        if job_types is None:
            types = registered
        else:
            types = registered.intersection(frozenset(job_types))
        if not types:
            return 0
        timeout = self._positive_int_parameter(
            STALE_OWNER_TIMEOUT_PARAM, STALE_OWNER_TIMEOUT_MINUTES,
        )
        batch_size = self._positive_int_parameter(
            STALE_OWNER_BATCH_PARAM, STALE_OWNER_BATCH_SIZE,
        )
        cutoff = fields.Datetime.now() - timedelta(minutes=timeout)
        Job = self.env['shopify.connector.job'].sudo()
        Attempt = self.env['shopify.connector.mutation.attempt'].sudo()
        # Durable C2 lineage is authoritative even if a damaged original job
        # has lost its nullable run relation or current job type.  Include
        # those owners from the immutable attempt domain, then union the
        # ordinary pre-C2 V2 candidates that have no attempt yet.
        attempt_candidates = Attempt.search([
            ('run_id', '!=', False),
            ('mutation_domain', 'in', tuple(sorted(types))),
            ('job_id.state', '=', 'running'),
            ('job_id.running_since', '!=', False),
            ('job_id.running_since', '<=', cutoff),
        ], order='job_id.running_since, id', limit=batch_size)
        c1_candidates = Job.search([
            ('run_id', '!=', False),
            ('job_type', 'in', tuple(sorted(types))),
            ('state', '=', 'running'),
            ('current_attempt_token', '!=', False),
            ('running_since', '!=', False),
            ('running_since', '<=', cutoff),
        ], order='running_since, id', limit=batch_size)
        candidates = (attempt_candidates.mapped('job_id') | c1_candidates).sorted(
            key=lambda item: (item.running_since, item.id),
        )[:batch_size]
        locked = candidates.try_lock_for_update(limit=batch_size)
        if not locked:
            return 0
        locked.invalidate_recordset()
        now = fields.Datetime.now()
        processed = 0
        for job in locked:
            if (
                job.state != 'running'
                or not job.running_since
                or job.running_since > cutoff
            ):
                continue
            attempt = Attempt.search([
                ('job_id', '=', job.id),
            ], limit=1)
            # A committed C2 row is stronger evidence than the current mode,
            # generation, company, or cancellation fence.  Recover it first;
            # otherwise a reconnect/mode change could strand the owner as a
            # blocked job without the exact read-only reconciliation that
            # proves whether Shopify accepted the write.
            if attempt:
                attempt = attempt.try_lock_for_update()
                if not attempt:
                    continue
                Dispatch._recover_committed_attempt_to_reconciliation(
                    job,
                    attempt,
                    'stale_owner_post_c2',
                    'stale_owner_sweep',
                )
            elif not job.current_attempt_token:
                Dispatch._block_original_job(
                    job,
                    'duplicate_risk',
                    'duplicate_risk',
                    'A stale V2 owner has no durable attempt or owner token; '
                    'automatic replay is refused.',
                )
                processed += 1
                continue
            elif not Dispatch._v2_admit_mutation_job(job, phase='stale'):
                Dispatch._block_v2_admission(job)
                processed += 1
                continue
            else:
                from_state = job.state
                job.sudo().write({
                    'state': 'retry_waiting',
                    'next_retry_at': now,
                    'current_attempt_token': False,
                    'owner_worker_ref': False,
                    'running_since': False,
                    'reconciliation_pending_until': False,
                })
                job._log_transition(
                    'state_change',
                    'Stale V2 owner had no committed attempt; safely requeued.',
                    from_state=from_state,
                    to_state='retry_waiting',
                )
            project = getattr(Dispatch, '_v2_project_run', False)
            if callable(project) and job.run_id:
                project(job.run_id)
            processed += 1
        return processed

    @api.model
    def run_sweep(self):
        if not self.env.su and not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may run the stale '
                'Layer-2 owner sweep.'
            )
        v2_count = self._sweep_v2_mutation_owners()
        timeout = self._positive_int_parameter(
            STALE_OWNER_TIMEOUT_PARAM, STALE_OWNER_TIMEOUT_MINUTES,
        )
        batch_size = self._positive_int_parameter(
            STALE_OWNER_BATCH_PARAM, STALE_OWNER_BATCH_SIZE,
        )
        cutoff = fields.Datetime.now() - timedelta(minutes=timeout)
        Job = self.env['shopify.connector.job']
        candidates = Job.search([
            # V2 read-only attempts have their own durable attempt evidence
            # and stale-owner policy.  Keep the legacy Layer-2 sweep strictly
            # on legacy jobs so it cannot reinterpret a V2 attempt as a
            # mutation owner with no committed transport evidence.
            ('run_id', '=', False),
            ('state', '=', 'running'),
            ('current_attempt_token', '!=', False),
            ('running_since', '!=', False),
            ('running_since', '<=', cutoff),
        ], order='running_since, id', limit=batch_size)
        if not candidates:
            return v2_count
        locked = candidates.try_lock_for_update(limit=batch_size)
        if not locked:
            return 0
        locked.invalidate_recordset()
        processed = 0
        Dispatch = self.env['shopify.connector.job.dispatch']
        Attempt = self.env['shopify.connector.mutation.attempt']
        now = fields.Datetime.now()
        for job in locked:
            if (
                job.state != 'running'
                or not job.current_attempt_token
                or not job.running_since
                or job.running_since > cutoff
            ):
                continue
            attempt = Attempt.search([
                ('job_id', '=', job.id),
            ], limit=1)
            if attempt and attempt.transport_attempted:
                attempt = attempt.try_lock_for_update()
                if not attempt:
                    continue
                existing = Job.search([
                    ('mutation_attempt_id', '=', attempt.id),
                ], limit=1)
                reconciliation = (
                    Dispatch._recover_committed_attempt_to_reconciliation(
                        job,
                        attempt,
                        'stale_owner_post_c2',
                        'stale_owner_sweep',
                    )
                )
                if reconciliation and not existing:
                    job._log_transition(
                        'manual_action',
                        'Stale Layer 2 owner recovered through reconciliation; '
                        'mutation transport was not replayed.',
                        from_state='running',
                        to_state='running',
                    )
            else:
                from_state = job.state
                job.sudo().write({
                    'state': 'retry_waiting',
                    'next_retry_at': now,
                    'current_attempt_token': False,
                    'owner_worker_ref': False,
                    'running_since': False,
                    'reconciliation_pending_until': False,
                })
                job._log_transition(
                    'state_change',
                    'Stale Layer 2 owner had no committed transport attempt; '
                    'safely requeued.',
                    from_state=from_state,
                    to_state='retry_waiting',
                )
            processed += 1
        return v2_count + processed
