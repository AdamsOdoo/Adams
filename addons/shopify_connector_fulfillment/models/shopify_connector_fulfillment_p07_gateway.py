"""Fulfillment-owned P07 typed gateway registration."""

from odoo import api, models

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
)

from ..integration.shopify.fulfillment_read_gateway import (
    FulfillmentReadError as TypedFulfillmentReadError,
    FulfillmentReadGateway,
)
from .shopify_connector_fulfillment_reader import FulfillmentReadError


class ShopifyConnectorFulfillmentP07Gateway(models.AbstractModel):
    """Provide the fulfillment gateway through the owning addon."""

    _inherit = "shopify.connector.read.gateway"

    @api.model
    def _p07_gateway(self, family: str):
        if family == "fulfillment":
            return FulfillmentReadGateway, dict(FulfillmentReadGateway.operation_documents)
        return super()._p07_gateway(family)

    @api.model
    def _p07_raise_typed_error(self, family: str, exc: Exception):
        if family != "fulfillment" or not isinstance(
            exc, TypedFulfillmentReadError,
        ):
            return super()._p07_raise_typed_error(family, exc)
        cause = exc.__cause__
        error_class = (
            cause.error_class
            if isinstance(cause, ShopifyClientError)
            else "shopify_temporary_server_network"
            if exc.code == "shopify_unavailable"
            else "data_shape_schema_mismatch"
        )
        raise FulfillmentReadError(
            error_class,
            "Shopify fulfillment evidence could not be read safely.",
        ) from exc


__all__ = ["ShopifyConnectorFulfillmentP07Gateway"]
