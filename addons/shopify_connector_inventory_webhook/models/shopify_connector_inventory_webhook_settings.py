"""SQL-searchable store checkpoint for the bounded observer scheduler."""

from odoo import fields, models


class ShopifyConnectorInventoryObservationSettings(models.Model):
    """Expose the store checkpoint on the one-row settings relation.

    Odoo cannot order a settings search by an unstored dotted related path.
    Keeping this related value stored and indexed makes NULL-first/oldest-first
    selection a bounded SQL operation while retaining the store as its sole
    source of truth.
    """

    _inherit = 'shopify.connector.store.settings'

    inventory_observation_scheduled_at = fields.Datetime(
        related='store_id.inventory_observation_scheduled_at',
        store=True,
        index=True,
        readonly=True,
    )
