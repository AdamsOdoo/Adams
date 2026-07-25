from odoo import api, fields, models


class ShopifyConnectorLocation(models.Model):
    """Minimal, system-maintained, Shopify-side-only Location reference.

    Never stores Odoo-location IDs or mapping decisions itself -- that mapping
    belongs to the inventory domain module. No group is granted
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
    # SEC-3 (#197): company is inherited from the owning store and is never an
    # independent selector. Stored so record rules, searches and grouped reads
    # filter on it in SQL; readonly so it can never diverge from its store.
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='store_id.company_id',
        store=True,
        index=True,
        readonly=True,
    )
    shopify_location_gid = fields.Char(required=True, index=True, readonly=True)
    name = fields.Char(required=True, readonly=True)
    shopify_location_active = fields.Boolean(default=True, readonly=True)
    last_synced_at = fields.Datetime(readonly=True)

    _store_location_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_location_gid)',
        'A location with this Shopify location GID already exists for this store.',
    )

    @api.model
    def _resolve_odoo_location(self, store, shopify_location_gid):
        """Sanctioned extension point (F-4): resolve a Shopify location GID to
        its mapped Odoo `stock.location`, if any.

        Core owns no mapping concept and no Odoo-location storage on this
        model itself, so the base implementation always fails closed
        (returns `False`). `shopify_connector_inventory` overrides this exact
        method (via ordinary model inheritance on `shopify.connector.location`)
        to consult its own canonical `shopify.connector.location.mapping`
        table. A sibling domain (e.g. `shopify_connector_fulfillment`) calls
        only this core-defined method by name; it never reads
        `shopify.connector.location.mapping` directly and gains no new
        manifest dependency on the inventory addon.
        """
        return False
