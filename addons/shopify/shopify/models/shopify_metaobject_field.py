from odoo import models, fields, api
from odoo.addons.shopify.models.shopify_metafield_mapping import METAFIELD_TYPE

SUPPORTED_FIELD_TYPES = {t[0] for t in METAFIELD_TYPE}


class ShopifyMetaobjectField(models.Model):
    _name = 'shopify.metaobject.field.ts'
    _description = 'Shopify Metaobject Field'
    _order = 'definition_id, id'
    _rec_name = 'name'

    definition_id = fields.Many2one('shopify.metaobject.definition.ts', string="Definition", required=True, ondelete='cascade', help="Metaobject definition this field belongs to.")
    mk_instance_id = fields.Many2one(related='definition_id.mk_instance_id', store=True, string="Instance")

    key = fields.Char(string="Key", required=True, help="Shopify field key, e.g. 'profile_link'. Used as the key in metaobject mutations.")
    name = fields.Char(string="Name", help="Display name of the field as shown in Shopify.")
    field_type = fields.Char(string="Type", help="Shopify field type, stored verbatim so unsupported types are still visible.")
    is_supported = fields.Boolean(string="Editable", compute='_compute_is_shopify_supported', store=True,
                                  help="False for a Shopify type this connector cannot convert. Such fields are imported read-only and are never included when pushing the entry, so Shopify keeps its own value.")
    scale_min = fields.Float(string="Rating Minimum Scale", help="Minimum value allowed for rating-type fields.")
    scale_max = fields.Float(string="Rating Maximum Scale", help="Maximum value allowed for rating-type fields.")
    ref_definition_id = fields.Many2one('shopify.metaobject.definition.ts', string="Referenced Definition", ondelete='set null',
                                        help="For metaobject_reference fields: the metaobject definition the referenced entries must belong to. Parsed from the Shopify 'metaobject_definition_id' validation and used to restrict the picker.")

    @api.depends('field_type')
    def _compute_is_shopify_supported(self):
        for record in self:
            record.is_supported = (record.field_type or '') in SUPPORTED_FIELD_TYPES
