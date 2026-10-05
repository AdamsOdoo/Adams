from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """
    TASK: T6274 - When the version was a upgrade then automatic location_id available location set to the export_location_ids.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    shopify_location_ids = env['shopify.location.ts'].search([])

    for shopify_location_id in shopify_location_ids:
        if shopify_location_id.location_id:
            shopify_location_id.write({'export_location_ids': [(4, shopify_location_id.location_id.id)]})
