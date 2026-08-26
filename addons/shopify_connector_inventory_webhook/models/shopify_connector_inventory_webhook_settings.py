"""Compatibility projection for the inventory-observation checkpoint."""

from odoo import fields, models


class ShopifyConnectorInventoryObservationSettings(models.Model):
    """Expose the store checkpoint without persisting a second copy.

    The scheduler now performs its bounded eligibility join against the owning
    store.  Keeping this projection non-stored prevents an inventory checkpoint
    advance from rewriting the shared settings row used by product and order
    scan windows, while preserving read compatibility for existing callers.
    A warm upgrade may leave the historic database column in place; it is no
    longer a field source and no recomputation writes it.
    """

    _inherit = 'shopify.connector.store.settings'

    inventory_observation_scheduled_at = fields.Datetime(
        related='store_id.inventory_observation_scheduled_at',
        readonly=True,
    )
