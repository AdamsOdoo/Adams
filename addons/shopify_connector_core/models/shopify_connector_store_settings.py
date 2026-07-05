from odoo import fields, models


class ShopifyConnectorStoreSettings(models.Model):
    """Store-scoped feature flags and domain-enablement configuration.

    Kept as its own model, not folded onto ``shopify.connector.store``,
    so domain modules can cleanly extend it via classic Odoo ``_inherit``
    without adding fields to the busier store record
    (core-naming-schema-planning.md §3/§5).
    """

    _name = 'shopify.connector.store.settings'
    _description = 'Shopify Connector Store Settings'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    product_domain_enabled = fields.Boolean(default=False)
    sale_domain_enabled = fields.Boolean(default=False)
    inventory_domain_enabled = fields.Boolean(default=False)
    fulfillment_domain_enabled = fields.Boolean(default=False)
    product_first_sync_source = fields.Selection(
        selection=[
            ('shopify_source', 'Shopify Source'),
            ('odoo_source', 'Odoo Source'),
            ('both_match_first', 'Both, Match First'),
        ],
    )
    price_source_of_truth = fields.Selection(
        selection=[
            ('odoo_authoritative', 'Odoo Authoritative'),
            ('shopify_authoritative', 'Shopify Authoritative'),
        ],
    )
    notification_default_enabled = fields.Boolean(default=False)

    _sql_constraints = [
        (
            'store_id_uniq',
            'unique(store_id)',
            'Only one settings record is allowed per store.',
        ),
    ]
