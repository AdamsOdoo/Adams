"""Keep run-linked V2 reads outside the legacy dispatcher claim path."""

from odoo import api, models
from odoo.exceptions import ValidationError

from ..runtime.p10_priority import MAX_CLAIM_BATCH


class ShopifyConnectorJobV2ClaimFence(models.Model):
    _inherit = "shopify.connector.job"

    @api.model
    def _registered_v2_dispatch_types(self):
        values = tuple(sorted(
            self.env["shopify.connector.job.dispatch"]._get_v2_job_types()
        ))
        if len(values) > MAX_CLAIM_BATCH:
            raise ValidationError(
                "The registered V2 dispatcher type set exceeds its bound."
            )
        return values

    @api.model
    def _claimable_domain(self, now=False, exclude_store_ids=()):
        domain = super()._claimable_domain(
            now=now, exclude_store_ids=exclude_store_ids,
        )
        registered = self._registered_v2_dispatch_types()
        if not registered:
            return domain + [("run_id", "=", False)]
        return domain + [
            "|",
            ("run_id", "=", False),
            "&",
            ("run_id", "!=", False),
            ("job_type", "in", registered),
        ]

    @api.model
    def _claim_for_dispatch(self, limit, exclude_store_ids=()):
        claimed = super()._claim_for_dispatch(
            limit, exclude_store_ids=exclude_store_ids,
        )
        if not claimed:
            return claimed
        registered = self._registered_v2_dispatch_types()
        return claimed.filtered(
            lambda job: not job.run_id or job.job_type in registered
        )
