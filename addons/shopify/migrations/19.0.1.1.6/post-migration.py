import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger("Teqstars:Shopify")


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # T7796 - Sales channels for existing listing items via Shopify GraphQL.
    instance_ids = env['mk.instance'].search([('marketplace', '=', 'shopify')])

    for instance in instance_ids:
        instance_id = instance.id
        state = instance.state

        # Get listing-wise item counts for items that still need sales channels
        cr.execute("""
            SELECT
                ml.id AS listing_id,
                COUNT(mli.id) AS item_count
            FROM mk_listing_item mli
            JOIN mk_listing ml ON ml.id = mli.mk_listing_id
            WHERE ml.mk_instance_id = %s
              AND mli.is_listed = TRUE
              AND mli.mk_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM mk_listing_item_sales_channels_rel rel
                  WHERE rel.listing_item_id = mli.id
              )
            GROUP BY ml.id
            ORDER BY ml.id
        """, (instance_id,))

        listing_counts = cr.fetchall()

        processed_count = 0
        listing_ids_to_process = []
        remaining_listing_exists = False

        for listing_id, item_count in listing_counts:
            # Don't split a listing across migration/manual sync
            if processed_count + item_count > 500:
                remaining_listing_exists = True
                break

            listing_ids_to_process.append(listing_id)
            processed_count += item_count

        # If first listing itself exceeds 500 items, leave everything for manual processing.
        if not listing_ids_to_process and listing_counts:
            instance.need_sync_shopify_sales_channels_item = True
            continue

        listing_item_ids_list = []

        if listing_ids_to_process:
            cr.execute("""
                SELECT mli.id
                FROM mk_listing_item mli
                WHERE mli.mk_listing_id IN %s
                  AND mli.is_listed = TRUE
                  AND mli.mk_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM mk_listing_item_sales_channels_rel rel
                      WHERE rel.listing_item_id = mli.id
                  )
            """, (tuple(listing_ids_to_process),))

            listing_item_ids_list = [row[0] for row in cr.fetchall()]

        count = len(listing_item_ids_list)

        if count > 0:
            if state == 'confirmed':
                try:
                    listing_item_ids = env['mk.listing.item'].browse(listing_item_ids_list)

                    config_param_key = f'shopify.migration_processed_listing_item_id_{instance_id}'

                    instance.set_shopify_sales_channels_to_listing_item(listing_item_ids, config_param_key)

                    env['ir.config_parameter'].search([('key', '=', config_param_key)]).unlink()

                except Exception as e:
                    _logger.warning("Failed to auto-apply sales channels for " "listing items during migration for instance %s: %s", instance_id, e)
                    instance.need_sync_shopify_sales_channels_item = True

            else:
                instance.need_sync_shopify_sales_channels_item = True

        # Some listings were intentionally skipped because of the 500 item limit.
        if remaining_listing_exists:
            # Nothing processed but records still remain
            instance.need_sync_shopify_sales_channels_item = True