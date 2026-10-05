from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """
    T6290 - Post-migration script to generate missing Shopify Metafield Resources for existing Shopify instances.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Find all existing Shopify instances
    shopify_instances = env['mk.instance'].search([('marketplace', '=', 'shopify')])

    if not shopify_instances:
        return

    # Get the Odoo model IDs efficiently from the ORM cache
    product_template_model_id = env['ir.model']._get('product.template').id
    product_variant_model_id = env['ir.model']._get('product.product').id

    metafield_resources_vals = []

    for instance in shopify_instances:
        # Check if Product Template Metafield Resource already exists for this instance
        existing_template_resource = env['shopify.metafield.resource.ts'].search([
            ('mk_instance_id', '=', instance.id),
            ('resource_name', '=', 'product')
        ], limit=1)

        if not existing_template_resource:
            metafield_resources_vals.append({
                'mk_instance_id': instance.id,
                'name': 'Product Metafields',
                'resource_name': 'product',
                'shopify_owner_type': 'PRODUCT',
                'dashboard_icon': 'fa fa-cube',
                'odoo_model_id': product_template_model_id,
            })

        # Check if Variant Metafield Resource already exists for this instance
        existing_variant_resource = env['shopify.metafield.resource.ts'].search([
            ('mk_instance_id', '=', instance.id),
            ('resource_name', '=', 'product_variant')
        ], limit=1)

        if not existing_variant_resource:
            metafield_resources_vals.append({
                'mk_instance_id': instance.id,
                'name': 'Variant Metafields',
                'resource_name': 'product_variant',
                'shopify_owner_type': 'PRODUCTVARIANT',
                'dashboard_icon': 'fa fa-tags',
                'odoo_model_id': product_variant_model_id,
            })

    # Batch create all missing metafield records in a single database query for speed
    if metafield_resources_vals:
        env['shopify.metafield.resource.ts'].create(metafield_resources_vals)
