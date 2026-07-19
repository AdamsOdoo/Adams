from datetime import timedelta

from odoo import api, fields, models


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
    def run_sweep(self):
        timeout = self._positive_int_parameter(
            STALE_OWNER_TIMEOUT_PARAM, STALE_OWNER_TIMEOUT_MINUTES,
        )
        batch_size = self._positive_int_parameter(
            STALE_OWNER_BATCH_PARAM, STALE_OWNER_BATCH_SIZE,
        )
        cutoff = fields.Datetime.now() - timedelta(minutes=timeout)
        Job = self.env['shopify.connector.job']
        candidates = Job.search([
            ('state', '=', 'running'),
            ('current_attempt_token', '!=', False),
            ('running_since', '!=', False),
            ('running_since', '<=', cutoff),
        ], order='running_since, id', limit=batch_size)
        if not candidates:
            return 0
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
                ('attempt_token', '=', job.current_attempt_token),
            ], limit=1)
            if attempt and attempt.transport_attempted:
                attempt = attempt.try_lock_for_update()
                if not attempt:
                    continue
                existing = Job.search([
                    ('mutation_attempt_id', '=', attempt.id),
                ], limit=1)
                job.sudo().write({
                    'reconciliation_pending_until': False,
                    'current_attempt_token': False,
                    'owner_worker_ref': False,
                    'running_since': False,
                })
                Dispatch._ensure_reconciliation_job(job, attempt)
                if not existing:
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
        return processed
