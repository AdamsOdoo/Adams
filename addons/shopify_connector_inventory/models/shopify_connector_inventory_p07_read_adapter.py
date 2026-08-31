"""P07 reversible inventory read call-site extension.

The large V1 inventory service remains unchanged.  This final ``_inherit``
layer routes only the existing pair read through the core adapter; the
adapter's context-marked rollback call invokes the original implementation.
"""

from odoo import api, models

from odoo.addons.shopify_connector_core.models.shopify_connector_domain_read_gateway import (
    P07_LEGACY_CONTEXT_KEY,
)


class ShopifyConnectorInventoryP07ReadAdapter(models.AbstractModel):
    _inherit = "shopify.connector.inventory.service"

    @api.model
    def _read_shopify_inventory_pair(self, job, store, binding):
        if self.env.context.get(P07_LEGACY_CONTEXT_KEY):
            return super()._read_shopify_inventory_pair(job, store, binding)
        return self.env["shopify.connector.read.gateway"].read_inventory_pair(
            job, store, binding,
        )


__all__ = ["ShopifyConnectorInventoryP07ReadAdapter"]
