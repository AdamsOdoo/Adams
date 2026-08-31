"""Inventory-owned P07 typed gateway registration."""

from odoo import api, models

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..integration.shopify.inventory_read_gateway import (
    InventoryReadError,
    InventoryReadGateway,
)


class ShopifyConnectorInventoryP07Gateway(models.AbstractModel):
    """Provide the inventory gateway without reversing the core dependency."""

    _inherit = "shopify.connector.read.gateway"

    @api.model
    def _p07_gateway(self, family: str):
        if family == "inventory":
            return InventoryReadGateway, dict(InventoryReadGateway.operation_documents)
        return super()._p07_gateway(family)

    @api.model
    def _p07_raise_typed_error(self, family: str, exc: Exception):
        if family != "inventory" or not isinstance(exc, InventoryReadError):
            return super()._p07_raise_typed_error(family, exc)
        cause = exc.__cause__
        if isinstance(cause, ShopifyClientError):
            raise JobHandlerError(
                cause.error_class, cause.reason, cause.technical_detail,
            ) from exc
        error_class = (
            "shopify_temporary_server_network"
            if exc.code == "shopify_unavailable"
            else "data_shape_schema_mismatch"
        )
        raise JobHandlerError(
            error_class,
            "Shopify inventory evidence could not be read safely.",
        ) from exc


__all__ = ["ShopifyConnectorInventoryP07Gateway"]
