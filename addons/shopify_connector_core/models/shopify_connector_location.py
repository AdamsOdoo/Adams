from odoo import fields, models


class ShopifyConnectorLocation(models.Model):
    """Minimal, system-maintained, Shopify-side-only Location reference.

    Never stores Odoo-location IDs or mapping decisions -- that mapping
    belongs to a future inventory domain module. No group is granted
    create/write/unlink on this model (see security/ir.model.access.csv);
    the cache is populated by system code only.
    """

    _name = 'shopify.connector.location'
    _description = 'Shopify Connector Location'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        ondelete='restrict',
    )
    shopify_location_gid = fields.Char(required=True, index=True, readonly=True)
    name = fields.Char(required=True, readonly=True)
    shopify_location_active = fields.Boolean(default=True, readonly=True)
    last_synced_at = fields.Datetime(readonly=True)

    _sql_constraints = [
        (
            'store_location_gid_uniq',
            'unique(store_id, shopify_location_gid)',
            'A location with this Shopify location GID already exists for this store.',
        ),
    ]
