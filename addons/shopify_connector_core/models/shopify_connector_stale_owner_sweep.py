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
    def _stale_v2_attempt_jobs(self, *, job_types, cutoff, limit, company_ids=None):
        """Return the oldest bounded jobs identified by durable V2 C2 rows.

        Odoo 19 does not accept a dotted relational field in ``search``'s
        ``order`` argument.  This narrow query joins core-owned lineage tables
        so the limit is still applied after ordering on the original job's
        stale timestamp.  Values remain bound parameters; the table and column
        identifiers are static connector schema.
        """
        if company_ids is None and not self.env.su:
            company_ids = tuple(self.env.companies.ids)
        Job = self.env['shopify.connector.job'].sudo()
        Attempt = self.env['shopify.connector.mutation.attempt'].sudo()
        Attempt.flush_model(['run_id', 'mutation_domain', 'job_id', 'company_id', 'store_id'])
        Job.flush_model(['state', 'running_since', 'company_id', 'store_id'])
        self.env['shopify.connector.run'].sudo().flush_model(['company_id', 'store_id'])
        self.env['shopify.connector.store'].sudo().flush_model(['company_id'])
        self.env.cr.execute(
            'SELECT j.id '
            'FROM shopify_connector_job AS j '
            'JOIN shopify_connector_store AS s ON s.id = j.store_id '
            'WHERE j.state = %s '
            'AND j.running_since IS NOT NULL '
            'AND j.running_since <= %s '
            'AND (%s OR j.company_id = ANY(%s)) '
            'AND s.company_id = j.company_id '
            'AND EXISTS ('
            'SELECT 1 FROM shopify_connector_mutation_attempt AS a '
            'JOIN shopify_connector_run AS r ON r.id = a.run_id '
            'WHERE a.job_id = j.id '
            'AND a.run_id IS NOT NULL '
            'AND a.company_id = j.company_id '
            'AND a.store_id = j.store_id '
            'AND r.company_id = j.company_id '
            'AND r.store_id = j.store_id '
            'AND a.mutation_domain = ANY(%s)'
            ') '
            'ORDER BY j.running_since, j.id '
            'LIMIT %s',
            ('running', cutoff, company_ids is None, list(company_ids or ()),
             list(sorted(job_types)), limit),
        )
        return Job.browse([row[0] for row in self.env.cr.fetchall()])

    @api.model
    def _stale_scope_matches(self, job, company_ids, attempt=None):
        """Recheck tenant lineage after locking, before recovery side effects."""
        company = job.company_id
        if not company or (company_ids is not None and company.id not in company_ids):
            return False
        records = [job.store_id]
        if attempt:
            records.extend((attempt, attempt.store_id))
            if attempt.run_id:
                records.extend((attempt.run_id, attempt.run_id.store_id))
        elif job.run_id:
            records.extend((job.run_id, job.run_id.store_id))
        for record in records:
            record.invalidate_recordset()
            if not record or record.company_id != company:
                return False
        if attempt:
            return bool(
                attempt.store_id == job.store_id
                and attempt.run_id
                and attempt.run_id.store_id == job.store_id
            )
        if not job.run_id or job.run_id.store_id != job.store_id:
            return False
        return True

    @api.model
    def _sweep_v2_mutation_owners(self, *, job_types=None):
        """Recover stale V2 mutation owners without replaying transport.

        V2 read-only attempts are handled by the P10 side-cursor repository;
        this method handles only mutation types explicitly registered by a
        domain addon.  A committed mutation attempt is always moved to the
        existing reconciliation job.  Only a stale C1 owner with no attempt
        can be requeued automatically.
        """
        # Evaluate allowed companies before any sudo search. Cron's explicit
        # superuser environment intentionally retains a global sweep.
        company_ids = None if self.env.su else tuple(self.env.companies.ids)
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
        attempt_jobs = self._stale_v2_attempt_jobs(
            job_types=types, cutoff=cutoff, limit=batch_size,
            company_ids=company_ids,
        )
        domain = [
            ('run_id', '!=', False),
            ('job_type', 'in', tuple(sorted(types))),
            ('state', '=', 'running'),
            ('current_attempt_token', '!=', False),
            ('running_since', '!=', False),
            ('running_since', '<=', cutoff),
        ]
        if company_ids is not None:
            domain.extend([
                ('company_id', 'in', company_ids),
                ('store_id.company_id', 'in', company_ids),
                ('run_id.company_id', 'in', company_ids),
                ('run_id.store_id.company_id', 'in', company_ids),
            ])
        c1_candidates = Job.search(domain, order='running_since, id', limit=batch_size)
        candidates = (attempt_jobs | c1_candidates).sorted(
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
            projection_run = False
            # A committed C2 row is stronger evidence than the current mode,
            # generation or cancellation fence, but never caller tenant scope.
            # otherwise a reconnect/mode change could strand the owner as a
            # blocked job without the exact read-only reconciliation that
            # proves whether Shopify accepted the write.
            if attempt:
                attempt = attempt.try_lock_for_update()
                if not attempt:
                    continue
                attempt.invalidate_recordset()
                if not self._stale_scope_matches(job, company_ids, attempt):
                    continue
                projection_run = attempt.run_id
                Dispatch._recover_committed_attempt_to_reconciliation(
                    job,
                    attempt,
                    'stale_owner_post_c2',
                    'stale_owner_sweep',
                )
            elif not self._stale_scope_matches(job, company_ids):
                continue
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
                projection_run = job.run_id
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
            if callable(project) and projection_run:
                project(projection_run)
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
            return v2_count
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
