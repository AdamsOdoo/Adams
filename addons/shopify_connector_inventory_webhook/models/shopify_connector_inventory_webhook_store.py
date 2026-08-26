"""Store-local cursor for fair scheduled inventory observation."""

from odoo import fields, models


class ShopifyConnectorInventoryObservationStoreExtension(models.Model):
    _inherit = 'shopify.connector.store'

    inventory_observation_scheduled_at = fields.Datetime(
        string='Inventory observation store checkpoint', index=True,
        readonly=True,
        help=(
            'The last bounded inventory-observation pass that explicitly '
            'accounted for this store. It is a fair store scheduler '
            'checkpoint, not evidence that every pair was scanned.'
        ),
    )
    inventory_observation_cursor_id = fields.Integer(
        string='Inventory observation cursor', index=True, readonly=True,
        help=(
            'The last mapped, previously pushed inventory pair selected by '
            'the bounded observation fallback. It is a fairness cursor, not '
            'a Shopify identity or a correctness watermark.'
        ),
    )
