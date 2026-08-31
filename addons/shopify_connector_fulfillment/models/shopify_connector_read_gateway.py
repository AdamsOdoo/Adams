"""Fulfillment-owned query registration for the shared P06 gateway."""

from __future__ import annotations

from odoo import api, models

from .shopify_connector_fulfillment_reader import LOCATIONS_QUERY


class ShopifyConnectorFulfillmentReadGateway(models.AbstractModel):
    """Provide the exact location document only when fulfillment is installed."""

    _inherit = "shopify.connector.read.gateway"

    @api.model
    def _extend_documents(
        self, names: set[str] | frozenset[str], documents: dict[str, str],
    ) -> dict[str, str]:
        documents = dict(super()._extend_documents(names, documents))
        if "ConnectorFulfillmentLocations" in names:
            documents["ConnectorFulfillmentLocations"] = LOCATIONS_QUERY
        return documents


__all__ = ["ShopifyConnectorFulfillmentReadGateway"]
