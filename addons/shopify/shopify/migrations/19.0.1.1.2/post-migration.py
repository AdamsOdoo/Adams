import logging

from odoo import api, SUPERUSER_ID
from odoo.addons.shopify.models.graphql_queries import GET_ALL_PRODUCT_PUBLICATIONS
from odoo.addons.shopify.models.misc import extract_numeric_id

_logger = logging.getLogger("Teqstars:Shopify")


def migrate(cr, version):
    """
    Task: Make Shopify Sales Channels instance-specific.

    Strategy:
        For every confirmed Shopify instance, fetch its publications (sales channels) from
        Shopify via GraphQL. For each fetched publication, find the matching channel record
        by `sales_channel_id` and stamp it with that instance. A channel that no instance
        claims is left untouched (the user can re-import or delete it manually).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Ensure the new column exists (Odoo creates it during the module update; defensive guard)
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'shopify_sales_channels_ts' AND column_name = 'mk_instance_id'
    """)
    if not cr.fetchone():
        _logger.info("shopify_sales_channels_ts.mk_instance_id missing; skipping migration.")
        return

    sale_channel_obj = env['shopify.sales.channels.ts']
    shopify_instance_ids = env['mk.instance'].search([('marketplace', '=', 'shopify')])

    for instance in shopify_instance_ids:
        try:
            instance.connection_to_shopify()
            res = instance.execute_graphql_query(GET_ALL_PRODUCT_PUBLICATIONS)
        except Exception as e:
            _logger.warning(f"Sales-channels migration: skipping instance {instance.name} ({instance.id}) – {e}")
            continue

        catalogs = (res or {}).get('data', {}).get('catalogs', []) if isinstance(res, dict) else []
        for entry in catalogs:
            publication = entry.get('publication') if isinstance(entry, dict) else None
            if not publication:
                continue
            sales_channel_id = str(extract_numeric_id(publication.get('id', '')))
            if not sales_channel_id:
                continue

            channel = sale_channel_obj.search([('sales_channel_id', '=', sales_channel_id), ('mk_instance_id', '=', False)], limit=1)
            if channel:
                channel.write({'mk_instance_id': instance.id})

    _logger.info(f"Sales-channels migration: assigned mk_instance_id for ({len(shopify_instance_ids)}) instance(s).")
