from html import escape

from odoo import models, fields, api, _

# Form view to inject the auto-created metaobject fields into, per owner type.
OWNER_TYPE_FORM_VIEW = {
    'PRODUCT': 'product.product_template_only_form_view',
    'PRODUCTVARIANT': 'product.product_normal_form_view',
    'ORDER': 'sale.view_order_form',
    'CUSTOMER': 'base.view_partner_form',
}


class ShopifyMetafieldResource(models.Model):
    _name = 'shopify.metafield.resource.ts'
    _description = 'Shopify Metafield Configuration'

    name = fields.Char(string="Resource Name", required=True, help="Display name of the resource configuration (e.g. Product Metafields).")
    mk_instance_id = fields.Many2one('mk.instance', string="Instance", required=True, ondelete='cascade', help="Marketplace instance for which metafields will be synced.")

    # Use for hook method name
    resource_name = fields.Char(string="Resource Name For Which We Fetch Metafield", required=True, help="e.g. 'products', 'orders'")

    # Required for GraphQL Fetching
    shopify_owner_type = fields.Char(string="Owner Type/Resource", required=True, help="Shopify GraphQL owner type e.g. PRODUCT, PRODUCTVARIANT, ORDER, CUSTOMER")

    odoo_model_id = fields.Many2one('ir.model', string="Odoo Model", required=True, ondelete="cascade", help="Odoo model where the metafield values will be mapped.")

    # Master Toggle on card
    active_sync = fields.Boolean(string="Enable Sync", default=False, help="Enable to allow import/export of metafields for this resource.")

    # card(resource) having multiple mapping
    mapping_ids = fields.One2many('shopify.metafield.mapping.ts', 'resource_id', string="Metafields", help="List of metafield mappings associated with this resource.")

    # Dashboard Statistics
    resource_total = fields.Integer(string="Total", compute='_compute_shopify_metafield_statistics', help="Total number of metafield mappings.")
    total_active_resource = fields.Integer(string="Active", compute='_compute_shopify_metafield_statistics', help="Number of active metafield mappings.")
    total_ready_resource = fields.Integer(string="Ready", compute='_compute_shopify_metafield_statistics', help="Number of mappings ready for sync (properly configured).")
    dashboard_icon = fields.Char(string="Dashboard Icon", help="Icon identifier used to visually represent this resource (e.g. 'fa fa-product').")

    @api.depends('mapping_ids.active_mapping', 'mapping_ids.mapping_status')
    def _compute_shopify_metafield_statistics(self):
        """
        T6290 - Compute count of Total, Active, and Ready metafield mappings.
        - resource_total: Count of all metafield mappings linked to the resource.
        - total_active_resource: Count of mappings that are enabled (active_mapping = True).
        - total_ready_resource: Count of active mappings that are properly configured (Odoo field selected).
        """
        for rec in self:
            mappings_ids = rec.mapping_ids
            rec.resource_total = len(mappings_ids)
            rec.total_active_resource = len(mappings_ids.filtered(lambda m: m.active_mapping))
            rec.total_ready_resource = len(mappings_ids.filtered(lambda m: m.mapping_status == 'ready'))

    def action_open_shopify_metafield_mappings(self):
        """
        T6290 - Open the metafield mapping records for the selected resource.
        Returns:
            dict: Action to open the list view of related metafield mappings configurations.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} Configuration',
            'res_model': 'shopify.metafield.mapping.ts',
            'view_mode': 'list',
            'views': [(False, 'list')],
            'domain': [('resource_id', '=', self.id)],
            'context': {'default_resource_id': self.id},
        }

    def action_fetch_shopify_metafield_definitions(self):
        """
        T6290 - Fetch and sync Shopify metafield definitions for this resource.
        """
        self.ensure_one()
        mapping_model = self.env['shopify.metafield.mapping.ts']
        return mapping_model.with_context(default_resource_id=self.id).action_fetch_shopify_metafields()

    def _rebuild_shopify_metaobject_view(self):
        """Task: T9096 - (Re)generate the inherited form view exposing the auto-created metaobject fields.

        Auto-created fields are `state='manual'` and therefore invisible until placed on a
        view. They go on ONE new notebook page (a tab) per Odoo form, however many
        instances use it: each instance gets its own titled section inside that tab, with
        its fields in two columns, so the form never grows a tab per instance. Because that
        one view is shared, it is regenerated from every resource of the same owner type -
        not only the ones in self - whenever any of them changes, and removed when none has
        an enabled mapping left.
        """
        view_obj = self.env['ir.ui.view'].sudo()
        resource_obj = self.env['shopify.metafield.resource.ts'].sudo()
        unified_names = [f"shopify_metaobject_fields_{owner_type.lower()}" for owner_type in OWNER_TYPE_FORM_VIEW]

        for owner_type in set(self.mapped('shopify_owner_type')):
            parent_ref = OWNER_TYPE_FORM_VIEW.get(owner_type)
            parent_view = view_obj.env.ref(parent_ref, raise_if_not_found=False) if parent_ref else None
            if not parent_view:
                continue

            # Earlier versions made one view (so one tab) per resource; remove any left over
            # instead of showing a second tab next to the shared one.
            view_obj.search([
                ('inherit_id', '=', parent_view.id),
                ('name', '=like', 'shopify_metaobject_fields_%'),
                ('name', 'not in', unified_names),
            ]).unlink()
            view_name = f"shopify_metaobject_fields_{owner_type.lower()}"
            existing_view = view_obj.search([('name', '=', view_name)], limit=1)

            mappings_by_instance = {}
            resources = resource_obj.search([('shopify_owner_type', '=', owner_type)])
            for resource in resources.sorted(key=lambda r: (r.mk_instance_id.id, r.id)):
                enabled_mappings = resource.mapping_ids.filtered(
                    lambda m: 'metaobject_reference' in (m.types or '') and m.odoo_field_id)
                if enabled_mappings:
                    mappings_by_instance.setdefault(resource.mk_instance_id, []).extend(enabled_mappings)

            sections = []
            for instance, mappings in mappings_by_instance.items():
                field_nodes = []
                for mapping in mappings:
                    widget = ' widget="many2many_tags"' if mapping.types.startswith('list.') else ''
                    context_attr = (
                        f' context="{{\'default_definition_id\': {mapping.metaobject_definition_id.id},'
                        f' \'default_mk_instance_id\': {instance.id}}}"'
                    ) if mapping.metaobject_definition_id else ''
                    # The section title already names the instance, so the label is just the
                    # metafield's name, without the "(instance id)" the stored field label
                    # carries to tell instances apart in generic Odoo screens.
                    label = escape(mapping.name or mapping.namespace_and_key or '', quote=True)
                    field_nodes.append(
                        f'<field name="{mapping.odoo_field_id.name}" string="{label}"'
                        f'{widget}{context_attr} readonly="0"/>')

                # Alternate left/right so the two columns read in mapping order across each row.
                left_column = ''.join(field_nodes[0::2])
                right_column = ''.join(field_nodes[1::2])
                right_group = f'<group>{right_column}</group>' if right_column else ''
                instance_title = escape(instance.name or '', quote=True)
                sections.append(
                    f'<separator string="{instance_title}"/>'
                    f'<group><group>{left_column}</group>{right_group}</group>')

            if not sections:
                existing_view.unlink()
                continue

            tab_label = escape(_("Shopify Metaobject Fields"), quote=True)
            sections_xml = ''.join(sections)
            arch = (
                '<data>'
                '<xpath expr="//sheet/notebook" position="inside">'
                f'<page string="{tab_label}" name="shopify_metaobject_fields">'
                f'{sections_xml}'
                '</page>'
                '</xpath>'
                '</data>'
            )

            view_vals = {
                'name': view_name,
                'model': parent_view.model,
                'inherit_id': parent_view.id,
                'arch_base': arch,
                'priority': 99,
            }
            if existing_view:
                existing_view.write(view_vals)
            else:
                view_obj.create(view_vals)
        return True