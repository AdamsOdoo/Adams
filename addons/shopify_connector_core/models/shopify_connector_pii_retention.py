import json
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError


MASKED_PII_VALUE = '***'
ATTEMPT_EVIDENCE_RETENTION_DAYS = 180
ATTEMPT_EVIDENCE_RETENTION_PARAM = (
    'shopify_connector.layer2_attempt_evidence_retention_days'
)
TERMINAL_JOB_RETENTION_DAYS = 90
TERMINAL_JOB_RETENTION_PARAM = 'shopify_connector.terminal_job_retention_days'
RETENTION_BATCH_SIZE = 2000

PII_KEY_PARTS = (
    'email',
    'phone',
    'first_name',
    'last_name',
    'display_name',
    'customer_name',
    'address',
)


class ShopifyConnectorPiiRetention(models.AbstractModel):
    _name = 'shopify.connector.pii.retention'
    _description = 'Shopify Connector PII Retention Service'

    @api.model
    def _mask_payload(self, value):
        """Redact PII-keyed entries out of a stored log/audit payload.

        This is *evidence redaction*, not business-record masking: it only
        ever rewrites a `shopify.connector.job.log` `payload_snapshot`, never
        a binding field. SEC-2 removes masking; redaction stays mandatory.
        """
        if isinstance(value, dict):
            masked = {}
            changed = 0
            for key, item in value.items():
                key_lower = str(key).lower()
                if any(part in key_lower for part in PII_KEY_PARTS):
                    if item not in (False, None, '', MASKED_PII_VALUE):
                        changed += 1
                    masked[key] = MASKED_PII_VALUE
                else:
                    masked[key], nested = self._mask_payload(item)
                    changed += nested
            return masked, changed
        if isinstance(value, list):
            masked = []
            changed = 0
            for item in value:
                masked_item, nested = self._mask_payload(item)
                masked.append(masked_item)
                changed += nested
            return masked, changed
        return value, 0

    @api.model
    def _attempt_evidence_retention_days(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(
            ATTEMPT_EVIDENCE_RETENTION_PARAM,
            ATTEMPT_EVIDENCE_RETENTION_DAYS,
        )
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return ATTEMPT_EVIDENCE_RETENTION_DAYS
        return value if value > 0 else ATTEMPT_EVIDENCE_RETENTION_DAYS

    @api.model
    def _terminal_job_retention_days(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(
            TERMINAL_JOB_RETENTION_PARAM, TERMINAL_JOB_RETENTION_DAYS,
        )
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return TERMINAL_JOB_RETENTION_DAYS
        return value if value > 0 else TERMINAL_JOB_RETENTION_DAYS

    @api.model
    def _run_terminal_job_retention(self):
        """Delete only low-risk terminal history in one bounded batch.

        Failed/review jobs and every job with Layer-2 attempt evidence are
        deliberately retained. Referentially-owned jobs are skipped under a
        savepoint, so retention can never damage a business record merely to
        satisfy an age target.
        """
        cutoff = fields.Datetime.now() - timedelta(
            days=self._terminal_job_retention_days(),
        )
        Job = self.env['shopify.connector.job'].sudo()
        Attempt = self.env['shopify.connector.mutation.attempt'].sudo()
        candidates = Job.search([
            ('state', 'in', ('succeeded', 'skipped', 'cancelled')),
            ('finished_at', '!=', False),
            ('finished_at', '<', cutoff),
        ], order='id asc', limit=RETENTION_BATCH_SIZE)
        attempt_job_ids = set(Attempt.search([
            ('job_id', 'in', candidates.ids),
        ]).mapped('job_id').ids)
        removed = 0
        for job in candidates.filtered(lambda row: row.id not in attempt_job_ids):
            try:
                with self.env.cr.savepoint():
                    self.env['shopify.connector.job.log'].sudo().search([
                        ('job_id', '=', job.id),
                    ]).unlink()
                    job.unlink()
                removed += 1
            except Exception:
                # A domain addon may own a restrict reference. That job is
                # evidence and remains intact; later candidates still drain.
                continue
        return removed

    @api.model
    def _run_attempt_evidence_masking(self):
        """Mask at most one indexed, oldest batch of resolved attempts."""
        cutoff = fields.Datetime.now() - timedelta(
            days=self._attempt_evidence_retention_days(),
        )
        Attempt = self.env['shopify.connector.mutation.attempt']
        attempts = Attempt.search([
            ('resolved_at', '!=', False),
            ('resolved_at', '<', cutoff),
            ('evidence_masked_at', '=', False),
        ], order='resolved_at, id', limit=RETENTION_BATCH_SIZE)
        counts = {}
        for attempt in attempts:
            if attempt.effective_disposition() == 'unresolved':
                continue
            before = (
                attempt.remote_mutation_intent,
                attempt.preconditions_snapshot,
                attempt.remote_evidence_refs,
            )
            attempt._mask_terminal_evidence()
            after = (
                attempt.remote_mutation_intent,
                attempt.preconditions_snapshot,
                attempt.remote_evidence_refs,
            )
            if before != after:
                counts[attempt.store_id.id] = (
                    counts.get(attempt.store_id.id, 0) + 1
                )
        for store_id, count in counts.items():
            self.env['shopify.connector.store'].browse(
                store_id
            )._create_lifecycle_audit_job(
                'Layer 2 attempt evidence retention store_id=%d '
                'masked_attempt_count=%d' % (store_id, count)
            )
        return sum(counts.values())

    @api.model
    def run_sweep(self):
        """Redact aged log/audit evidence. Never masks a business record.

        SEC-2 (packet §D Option 1, control-room decision TA-C5 2026-07-17)
        removed customer-binding snapshot masking from this sweep. What
        remains is log/audit hygiene only: job-log ``payload_snapshot``
        redaction and Layer-2 terminal attempt-evidence redaction. Both are
        redaction of *evidence*, which stays mandatory; neither touches a
        binding's stored business fields.
        """
        if not self.env.su and not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may run PII '
                'retention maintenance.'
            )
        settings_records = self.env[
            'shopify.connector.store.settings'
        ].sudo().search([('log_redaction_retention_days', '>', 0)])
        JobLog = self.env['shopify.connector.job.log']

        for settings in settings_records:
            store = self.env['shopify.connector.store'].browse(
                settings.store_id.id
            )
            cutoff = fields.Datetime.now() - timedelta(
                days=settings.log_redaction_retention_days,
            )
            redacted_field_count = 0
            redacted_payload_count = 0

            logs = JobLog.sudo().search([
                ('store_id', '=', store.id),
                ('occurred_at', '<', cutoff),
                ('payload_snapshot', 'not in', (False, '')),
            ], order='occurred_at, id', limit=RETENTION_BATCH_SIZE)
            for log in logs:
                try:
                    payload = json.loads(log.payload_snapshot)
                except (TypeError, ValueError):
                    continue
                redacted_payload, changed = self._mask_payload(payload)
                if changed:
                    log.write({
                        'payload_snapshot': json.dumps(
                            redacted_payload,
                            sort_keys=True,
                            separators=(',', ':'),
                        ),
                    })
                    redacted_payload_count += 1
                    redacted_field_count += changed

            if redacted_payload_count or redacted_field_count:
                store._create_lifecycle_audit_job(
                    'Log redaction sweep store_id=%d '
                    'redacted_payload_count=%d redacted_field_count=%d' % (
                        store.id,
                        redacted_payload_count,
                        redacted_field_count,
                    )
                )
        self._run_attempt_evidence_masking()
        self._run_terminal_job_retention()
        # Named P15 acknowledgements are bounded, non-secret evidence too.
        # Keep their cleanup on the same administrator/root cron so there is
        # one retention control and no unbounded replay table.
        if 'shopify.connector.command.result' in self.env:
            self.env['shopify.connector.command.result'].run_retention()
        return True
