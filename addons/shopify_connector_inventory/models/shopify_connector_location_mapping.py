from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class ShopifyConnectorLocationMapping(models.Model):
    """Explicit Shopify Location <-> Odoo internal `stock.location` mapping.

    D-013-1(a). Store-scoped, on the shared binding mixin. Identity is
    always explicit -- `match_key` is always `'manual'`; this model never
    infers a mapping from a name or any other heuristic (DEC-010). No
    mapped location for one store may be an ancestor or descendant of
    another mapped location for that same store, so that Odoo's
    location-subtree aggregation (`free_qty` with a location context)
    can never double-count one physical location under two different
    Shopify Location mappings.
    """

    _name = 'shopify.connector.location.mapping'
    _inherit = 'shopify.connector.binding.mixin'
    _description = 'Shopify Connector Location Mapping'

    odoo_location_id = fields.Many2one(
        comodel_name='stock.location',
        required=True,
        index=True,
        ondelete='restrict',
        domain=[('usage', '=', 'internal')],
    )
    shopify_location_name_snapshot = fields.Char(readonly=True)
    push_enabled = fields.Boolean(default=True)

    _store_odoo_location_uniq = models.Constraint(
        'UNIQUE(store_id, odoo_location_id)',
        'This Odoo location is already mapped for this store.',
    )
    _store_shopify_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_gid)',
        'A location mapping with this Shopify Location GID already '
        'exists for this store.',
    )

    def _odoo_binding_field_name(self):
        return 'odoo_location_id'

    @api.model
    def _additional_protected_binding_fields(self):
        return super()._additional_protected_binding_fields() | frozenset((
            'shopify_location_name_snapshot',
            'push_enabled',
        ))

    @api.constrains('store_id', 'odoo_location_id')
    def _check_no_ancestor_descendant_overlap(self):
        for mapping in self:
            if not mapping.odoo_location_id:
                continue
            siblings = self.search([
                ('id', '!=', mapping.id),
                ('store_id', '=', mapping.store_id.id),
            ])
            this_path = mapping.odoo_location_id.parent_path or ''
            for sibling in siblings:
                other_path = sibling.odoo_location_id.parent_path or ''
                if not this_path or not other_path:
                    continue
                if this_path.startswith(other_path) or other_path.startswith(
                    this_path,
                ):
                    raise UserError(
                        "This Odoo location is an ancestor or descendant of "
                        "another location already mapped for this store "
                        "(%s). Overlapping mapped locations would let one "
                        "physical location's stock be counted under two "
                        "different Shopify locations." % (
                            sibling.odoo_location_id.display_name,
                        )
                    )

    @api.constrains('store_id', 'odoo_location_id')
    def _check_location_company_consistency(self):
        for mapping in self:
            location_company = mapping.odoo_location_id.company_id
            if location_company and location_company != self.env.company:
                raise UserError(
                    "The mapped Odoo location belongs to a different "
                    "company than the current company."
                )

    def action_set_push_enabled(self, enabled):
        self.ensure_one()
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_operator'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                "Only a Shopify Connector Operator or Administrator may "
                "change a location mapping's push-enable flag."
            )
        self.sudo().write({'push_enabled': bool(enabled)})
        return True
