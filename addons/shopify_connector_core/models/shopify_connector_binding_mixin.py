from odoo import fields, models


class ShopifyConnectorBindingMixin(models.AbstractModel):
    """The per-domain-concrete-on-core-contract shape (DEC-013).

    Concrete domain binding models (out of scope for this core-only
    slice) will ``_inherit`` this mixin. It carries no
    ``res_model``/``res_id`` pair -- each concrete binding model adds its
    own specific ``Many2one`` to the Odoo business object it binds.
    Composite uniqueness on ``(store_id, shopify_gid)`` is enforced per
    concrete model, not here, since an abstract model has no table of
    its own.
    """

    _name = 'shopify.connector.binding.mixin'
    _description = 'Shopify Connector Binding Mixin'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        ondelete='restrict',
    )
    shopify_gid = fields.Char(required=True, index=True, readonly=True)
    status = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('stale', 'Stale'),
            ('manually_overridden', 'Manually Overridden'),
            ('review', 'Review'),
        ],
        required=True,
        index=True,
        default='active',
    )
    match_key = fields.Selection(
        selection=[
            ('existing_binding', 'Existing Binding'),
            ('sku_reference', 'SKU Reference'),
            ('barcode', 'Barcode'),
            ('email', 'Email'),
            ('manual', 'Manual'),
        ],
        readonly=True,
    )
    matched_by_uid = fields.Many2one(comodel_name='res.users', readonly=True)
    matched_at = fields.Datetime(readonly=True)
    override_uid = fields.Many2one(comodel_name='res.users', readonly=True)
    override_at = fields.Datetime(readonly=True)
    override_previous_candidate = fields.Char(readonly=True)
