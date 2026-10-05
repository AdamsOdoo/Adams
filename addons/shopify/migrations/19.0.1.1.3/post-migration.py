from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """
    T6294 - included script to generate missing Shopify customer Metafield Resources for existing Shopify instances.
    T6290 - Post-migration script to generate missing Shopify order Metafield Resources for existing Shopify instances.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Find all existing Shopify instances
    shopify_instances = env['mk.instance'].search([('marketplace', '=', 'shopify')])

    if not shopify_instances:
        return

    # Get the Odoo model IDs efficiently from the ORM cache
    sale_order_model_id = env['ir.model']._get('sale.order').id
    res_partner_model_id = env['ir.model']._get('res.partner').id

    metafield_resources_vals = []

    for instance in shopify_instances:
        # Check if order Metafield Resource already exists for this instance
        existing_template_resource = env['shopify.metafield.resource.ts'].search([
            ('mk_instance_id', '=', instance.id),
            ('resource_name', '=', 'order')
        ], limit=1)

        if not existing_template_resource:
            metafield_resources_vals.append({
                'mk_instance_id': instance.id,
                'name': 'Order Metafields',
                'resource_name': 'order',
                'shopify_owner_type': 'ORDER',
                'dashboard_icon': 'fa fa-shopping-cart',
                'odoo_model_id': sale_order_model_id,
            })

        # Create Customer Card
        existing_customer_resource = env['shopify.metafield.resource.ts'].search([
            ('mk_instance_id', '=', instance.id),
            ('resource_name', '=', 'customer')
        ], limit=1)

        if not existing_customer_resource:
            metafield_resources_vals.append({
                'mk_instance_id': instance.id,
                'name': 'Customer Metafields',
                'resource_name': 'customer',
                'shopify_owner_type': 'CUSTOMER',
                'dashboard_icon': 'fa fa-users',
                'odoo_model_id': res_partner_model_id,
            })

    # Batch create all missing metafield records in a single database query for speed
    if metafield_resources_vals:
        env['shopify.metafield.resource.ts'].create(metafield_resources_vals)