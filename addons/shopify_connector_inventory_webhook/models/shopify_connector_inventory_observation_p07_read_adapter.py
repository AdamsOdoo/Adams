"""P07 reversible inventory-observation read call-site extension."""

from odoo import api, models

from odoo.addons.shopify_connector_core.models.shopify_connector_domain_read_gateway import (
    P07_LEGACY_CONTEXT_KEY,
)


class ShopifyConnectorInventoryObservationP07ReadAdapter(models.AbstractModel):
    _inherit = "shopify.connector.inventory.observation.service"

    @api.model
    def _read_inventory_level(self, job, store, level_gid):
        if self.env.context.get(P07_LEGACY_CONTEXT_KEY):
            return super()._read_inventory_level(job, store, level_gid)
        return self.env["shopify.connector.read.gateway"].read_inventory_level(
            job, store, level_gid,
        )


__all__ = ["ShopifyConnectorInventoryObservationP07ReadAdapter"]
