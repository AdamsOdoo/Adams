"""Retention-only progress marker for mutation-attempt evidence.

The durable mutation-attempt identity/state model stays at its accepted
baseline size.  This additive extension owns only the indexed marker used by
the bounded PII-retention sweep to advance past already-masked rows.
"""

from odoo import fields, models


class ShopifyConnectorMutationAttemptRetention(models.Model):
    _inherit = 'shopify.connector.mutation.attempt'

    evidence_masked_at = fields.Datetime(readonly=True, index=True)

    def _retention_mark_masked(self, records):
        records = records.filtered(
            lambda attempt: (
                attempt.resolved_at
                and attempt.effective_disposition() in ('applied', 'not_applied')
                and not attempt.evidence_masked_at
            )
        )
        if records:
            records._surface('_mask_terminal_evidence').write({
                'evidence_masked_at': fields.Datetime.now(),
            })

    def _mask_terminal_evidence(self):
        result = super()._mask_terminal_evidence()
        self._retention_mark_masked(self)
        return result
