"""P07 reversible fulfillment read call-site extension.

All methods are installed after the fulfillment service siblings so this
single extension is the final dispatch layer.  It does not alter fulfillment
selection, notification or mutation policy.
"""

from odoo import api, models

from odoo.addons.shopify_connector_core.models.shopify_connector_domain_read_gateway import (
    P07_LEGACY_CONTEXT_KEY,
)


class ShopifyConnectorFulfillmentP07ReadAdapter(models.AbstractModel):
    _inherit = "shopify.connector.fulfillment.service"

    @api.model
    def _read_fulfillment_orders(self, job, store, order_gid):
        if self.env.context.get(P07_LEGACY_CONTEXT_KEY):
            return super()._read_fulfillment_orders(job, store, order_gid)
        return self.env["shopify.connector.read.gateway"].read_fulfillment_orders(
            job, store, order_gid,
        )

    @api.model
    def _read_order_fulfillments(self, job, store, order_gid):
        if self.env.context.get(P07_LEGACY_CONTEXT_KEY):
            return super()._read_order_fulfillments(job, store, order_gid)
        return self.env["shopify.connector.read.gateway"].read_order_fulfillments(
            job, store, order_gid,
        )

    @api.model
    def _read_fulfillment(self, job, store, fulfillment_gid):
        if self.env.context.get(P07_LEGACY_CONTEXT_KEY):
            return super()._read_fulfillment(job, store, fulfillment_gid)
        return self.env["shopify.connector.read.gateway"].read_fulfillment(
            job, store, fulfillment_gid,
        )

    @api.model
    def _read_fulfillments_batch(self, job, store, fulfillment_gids):
        if self.env.context.get(P07_LEGACY_CONTEXT_KEY):
            return super()._read_fulfillments_batch(job, store, fulfillment_gids)
        return self.env["shopify.connector.read.gateway"].read_fulfillments_batch(
            job, store, fulfillment_gids,
        )


__all__ = ["ShopifyConnectorFulfillmentP07ReadAdapter"]
