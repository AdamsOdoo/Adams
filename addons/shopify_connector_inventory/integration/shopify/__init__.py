"""Canonical Odoo-loaded inventory read gateway."""

from .inventory_read_gateway import (
    InventoryReadGateway,
    InventoryReadError,
)

__all__ = ["InventoryReadError", "InventoryReadGateway"]
