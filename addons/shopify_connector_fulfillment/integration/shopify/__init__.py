"""Canonical Odoo-loaded fulfillment read gateway."""

from .fulfillment_read_gateway import (
    FulfillmentReadGateway,
    FulfillmentReadError,
)

__all__ = ["FulfillmentReadError", "FulfillmentReadGateway"]
