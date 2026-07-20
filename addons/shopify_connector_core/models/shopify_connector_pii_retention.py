import json
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


MASKED_PII_VALUE = '***'
ATTEMPT_EVIDENCE_RETENTION_DAYS = 180
ATTEMPT_EVIDENCE_RETENTION_PARAM = (
    'shopify_connector.layer2_attempt_evidence_retention_days'
)

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
    def _binding_models_with_pii(self):
        result = []
        for model_name in sorted(self.env.registry.models):
            model = self.env[model_name]
            hook = getattr(model, '_pii_snapshot_fields', None)
            if not hook or getattr(model, '_abstract', False):
                continue
            field_names = list(hook())
            if (
                field_names
                and 'store_id' in model._fields
                and 'create_date' in model._fields
            ):
                result.append((model, field_names))
        return result

    @api.model
    def action_mask_customer_pii(self, binding):
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                "Only a Shopify Connector Administrator may mask customer PII."
            )
        if not binding or not getattr(binding, '_name', False):
            raise UserError("A concrete PII-bearing binding is required.")
        binding = self.env[binding._name].browse(binding.id)
        binding.ensure_one()
        field_names = list(binding._pii_snapshot_fields())
        if not field_names:
            raise UserError("This binding does not declare PII snapshots.")

        values = {}
        for field_name in field_names:
            if field_name not in binding._fields:
                raise UserError(
                    "The binding declares an unknown PII snapshot field."
                )
            if binding.sudo()[field_name] not in (
                False, None, '', MASKED_PII_VALUE,
            ):
                values[field_name] = MASKED_PII_VALUE
        if values:
            binding.sudo().write(values)
        binding.store_id._create_lifecycle_audit_job(
            'Manual PII mask model=%s binding_id=%d masked_field_count=%d '
            'actor_uid=%d' % (
                binding._name,
                binding.id,
                len(values),
                self.env.uid,
            )
        )
        return True

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
    def _run_attempt_evidence_masking(self):
        cutoff = fields.Datetime.now() - timedelta(
            days=self._attempt_evidence_retention_days(),
        )
        Attempt = self.env['shopify.connector.mutation.attempt']
        attempts = Attempt.search([
            ('resolved_at', '!=', False),
            ('resolved_at', '<', cutoff),
        ], order='store_id, id')
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
        settings_records = self.env[
            'shopify.connector.store.settings'
        ].sudo().search([('pii_snapshot_retention_days', '>', 0)])
        binding_models = self._binding_models_with_pii()
        JobLog = self.env['shopify.connector.job.log']

        for settings in settings_records:
            store = self.env['shopify.connector.store'].browse(
                settings.store_id.id
            )
            cutoff = fields.Datetime.now() - timedelta(
                days=settings.pii_snapshot_retention_days,
            )
            masked_binding_count = 0
            masked_field_count = 0
            masked_payload_count = 0

            for Binding, field_names in binding_models:
                bindings = Binding.sudo().search([
                    ('store_id', '=', store.id),
                    ('create_date', '<', cutoff),
                ])
                for binding in bindings:
                    values = {
                        field_name: MASKED_PII_VALUE
                        for field_name in field_names
                        if binding[field_name] not in (
                            False, None, '', MASKED_PII_VALUE,
                        )
                    }
                    if values:
                        binding.write(values)
                        masked_binding_count += 1
                        masked_field_count += len(values)

            logs = JobLog.sudo().search([
                ('store_id', '=', store.id),
                ('occurred_at', '<', cutoff),
                ('payload_snapshot', 'not in', (False, '')),
            ])
            for log in logs:
                try:
                    payload = json.loads(log.payload_snapshot)
                except (TypeError, ValueError):
                    continue
                masked_payload, changed = self._mask_payload(payload)
                if changed:
                    log.write({
                        'payload_snapshot': json.dumps(
                            masked_payload,
                            sort_keys=True,
                            separators=(',', ':'),
                        ),
                    })
                    masked_payload_count += 1
                    masked_field_count += changed

            if (
                masked_binding_count
                or masked_payload_count
                or masked_field_count
            ):
                store._create_lifecycle_audit_job(
                    'PII retention sweep store_id=%d '
                    'masked_binding_count=%d masked_payload_count=%d '
                    'masked_field_count=%d' % (
                        store.id,
                        masked_binding_count,
                        masked_payload_count,
                        masked_field_count,
                    )
                )
        self._run_attempt_evidence_masking()
        return True
