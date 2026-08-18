"""Monotonic remote snapshot guard for product imports."""

from datetime import datetime, timezone

from odoo import api, models

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)


class ShopifyConnectorProductImporterWebhookGuard(models.AbstractModel):
    """Reject an older remote snapshot before the product importer writes."""

    _inherit = 'shopify.connector.product.importer'

    @api.model
    def _remote_snapshot_datetime(self, value):
        """Parse Shopify's ISO timestamp; legacy test markers remain opaque."""
        if not isinstance(value, str) or not value.strip():
            return False
        try:
            parsed = datetime.fromisoformat(
                value.strip().replace('Z', '+00:00'),
            )
        except (TypeError, ValueError, OverflowError):
            # The pre-W2 importer accepted opaque legacy stamps.  Shopify's
            # GraphQL updatedAt is ISO-8601, so only comparable source stamps
            # participate in this guard; no identity is guessed from a bad
            # timestamp and the existing schema validator remains authoritative.
            return False
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @api.model
    def _locked_snapshot_binding(self, store, payload):
        if not isinstance(payload, dict):
            return self.env['shopify.connector.product.template.binding'].browse()
        gid = payload.get('gid')
        if not isinstance(gid, str) or not gid:
            return self.env['shopify.connector.product.template.binding'].browse()
        Binding = self.env['shopify.connector.product.template.binding']
        binding = Binding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', gid),
        ], limit=1)
        if not binding:
            return binding
        # The importer may be invoked by a webhook and by the scheduled scan.
        # Lock the existing binding before comparing/writing so an older job
        # cannot pass its comparison concurrently with a newer job's stamp.
        locked = binding.try_lock_for_update()
        if not locked:
            raise JobHandlerError(
                'concurrency_race_conflict',
                'The product binding is being refreshed by another importer; '
                'retry the durable product job.',
            )
        return locked

    @api.model
    def _stale_snapshot_outcome(self, store, payload, job):
        binding = self._locked_snapshot_binding(store, payload)
        if not binding or not binding.shopify_updated_at:
            return False
        incoming = self._remote_snapshot_datetime(payload.get('updated_at'))
        stored = self._remote_snapshot_datetime(binding.shopify_updated_at)
        if not incoming or not stored or incoming >= stored:
            return False
        variant_bindings = self.env[
            'shopify.connector.product.variant.binding'
        ].search([
            ('product_template_binding_id', '=', binding.id),
        ], order='id')
        note = (
            'Ignored stale Shopify product snapshot for %s: remote '
            'updatedAt %s is older than stored snapshot %s. No product, '
            'variant, or binding field was overwritten.'
            % (binding.shopify_gid, payload.get('updated_at'),
               binding.shopify_updated_at)
        )
        self._emit_note(job, note)
        return {
            'template_binding': binding,
            'variant_bindings': variant_bindings,
            'stale': True,
            'out_of_order': True,
            'notes': [('stale_remote_update', note)],
        }

    @api.model
    def _apply_import(self, store, payload, job=None, requested_gid=None):
        stale = self._stale_snapshot_outcome(store, payload, job)
        if stale:
            return stale
        return super()._apply_import(
            store, payload, job=job, requested_gid=requested_gid,
        )
