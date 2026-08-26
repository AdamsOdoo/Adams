from odoo import api, models


class ShopifyConnectorJobEnqueue(models.AbstractModel):
    """The core job-enqueue service (Decision D, Task 006C gate-opening
    proposal §6) -- the sole call surface a future domain module would
    use to create a business `shopify.connector.job` row.

    Stateless, no table (`AbstractModel`, mirroring
    `shopify_connector_readiness_check.py`/`shopify_connector_api_client.py`
    -- no new ACL row needed). A thin wrapper around `Job.create()`
    only: store-state gating (job.py's `create()`, unmodified) and the
    existing `idempotency_key`/`operation_scope_key` computed fields and
    their DB-level unique constraints are inherited automatically -- this
    file introduces no new idempotency/scope-key mechanism, and never
    calls the Shopify API client.
    """

    _name = 'shopify.connector.job.enqueue'
    _description = 'Shopify Connector Job Enqueue Service'

    @api.model
    def enqueue(
        self, store, job_source, job_type, payload_hash=False,
        res_model=False, res_id=False, shopify_target_gid=False,
        trigger_origin=False, trigger_origin_event_ref=False,
        trigger_origin_event_at=False,
    ):
        """Create one `shopify.connector.job` row in state `queued`.

        `payload_hash` is caller-supplied -- a domain handler owns
        payload interpretation/normalization per the DEC-025 core-vs-
        domain responsibility boundary, not this core service -- and is
        passed straight into the existing computed `idempotency_key`,
        unchanged. Returns the new job record; raises whatever
        `Job.create()` itself raises (a store-state `ValidationError`,
        or a duplicate-key `IntegrityError` from the existing unique
        constraints) -- this method adds no new validation of its own.
        """
        vals = {
            'store_id': store.id,
            'job_source': job_source,
            'job_type': job_type,
            'state': 'queued',
            'payload_hash': payload_hash or False,
            # CORE-R2 (AR-047): capture the store's live connection epoch at
            # enqueue so `execute_business` admission can later fail closed on a
            # disconnect/reconnect cycle. Captured here, never inferred at
            # dispatch time. Dormant until the business call sites migrate to
            # `execute_business` in a later slice.
            'expected_connection_generation': store.connection_generation,
        }
        if res_model:
            vals['res_model'] = res_model
        if res_id:
            vals['res_id'] = res_id
        if shopify_target_gid:
            vals['shopify_target_gid'] = shopify_target_gid
        if trigger_origin:
            vals['trigger_origin'] = trigger_origin
        if trigger_origin_event_ref:
            vals['trigger_origin_event_ref'] = trigger_origin_event_ref
        if trigger_origin_event_at:
            vals['trigger_origin_event_at'] = trigger_origin_event_at
        job = self.env['shopify.connector.job'].sudo().create(vals)
        cron = self.env.ref(
            'shopify_connector_core.ir_cron_shopify_connector_job_dispatch_drain',
            raise_if_not_found=False,
        )
        if cron:
            # Odoo coalesces trigger rows for the scheduled action.  This is a
            # wakeup hint after a durable enqueue, never a replacement for the
            # normal interval and never an inline dispatch.
            cron.sudo()._trigger()
        return self.env['shopify.connector.job'].browse(job.id)
