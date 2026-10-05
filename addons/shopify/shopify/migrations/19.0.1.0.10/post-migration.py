import base64
import hashlib

import requests

from odoo import api, SUPERUSER_ID, tools
from odoo.addons.shopify.models.graphql_queries import GET_COLLECTION_PUBLICATION
from odoo.addons.shopify.models.misc import extract_numeric_id


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    cr.execute("""
            UPDATE shopify_collection_ts
            SET sort_order = CASE
                WHEN sort_order = 'alpha-asc' THEN 'ALPHA_ASC'
                WHEN sort_order = 'alpha-desc' THEN 'ALPHA_DESC'
                WHEN sort_order = 'best-selling' THEN 'BEST_SELLING'
                WHEN sort_order = 'created' THEN 'CREATED'
                WHEN sort_order = 'created-desc' THEN 'CREATED_DESC'
                WHEN sort_order = 'manual' THEN 'MANUAL'
                WHEN sort_order = 'price-asc' THEN 'PRICE_ASC'
                WHEN sort_order = 'price-desc' THEN 'PRICE_DESC'
                ELSE sort_order
            END
            WHERE sort_order IN ('alpha-asc','alpha-desc', 'best-selling', 'created', 'created-desc', 'manual', 'price-asc', 'price-desc')
              OR sort_order IS NULL;
        """)

    cr.execute("""
            DELETE FROM ir_model_fields_selection s
            USING ir_model_fields f
            WHERE s.field_id = f.id
              AND f.model = 'shopify.collection.ts'
              AND f.name = 'sort_order'
              AND s.value IN ('alpha-asc', 'alpha-desc', 'best-selling', 'created', 'created-desc', 'manual', 'price-asc', 'price-desc');
        """)

    condition_columns = env["shopify.collection.condition.column.ts"].search([])
    for condition_column in condition_columns:
        if condition_column.shopify_name:
            # Update the 'shopify_name' to uppercase
            condition_column.shopify_name = condition_column.shopify_name.upper()
    cr.execute("""
                    UPDATE shopify_collection_condition_ts
                    SET "column" = UPPER("column")
                    WHERE "column" IN ('title', 'type', 'vendor', 'variant_title', 'variant_compare_at_price', 'variant_weight', 'variant_inventory', 'variant_price', 'product_taxonomy_node_id', 'tag');
                """)

    cr.execute("""
                    DELETE FROM ir_model_fields_selection s
                    USING ir_model_fields f
                    WHERE s.field_id = f.id
                      AND f.model = 'shopify.collection.condition.ts'
                      AND f.name = 'column'
                      AND s.value IN ('title', 'type', 'vendor', 'variant_title', 'variant_compare_at_price', 'variant_weight', 'variant_inventory', 'variant_price', 'product_taxonomy_node_id', 'tag');
    """)

    cr.execute("""
                    UPDATE shopify_collection_condition_ts
                    SET relation = UPPER(relation)
                    WHERE relation IN ('greater_than', 'less_than', 'equals', 'is_set', 'is_not_set', 'not_equals', 'starts_with', 'ends_with', 'contains', 'not_contains');
                """)

    cr.execute("""
                    DELETE FROM ir_model_fields_selection s
                    USING ir_model_fields f
                    WHERE s.field_id = f.id
                      AND f.model = 'shopify.collection.condition.ts'
                      AND f.name = 'relation'
                      AND s.value IN ('greater_than', 'less_than', 'equals', 'is_set', 'is_not_set', 'not_equals', 'starts_with', 'ends_with', 'contains', 'not_contains');
                """)

    cr.execute("""
                    UPDATE shopify_collection_ts
                    SET collection_type = 'smart'
                    WHERE collection_type = 'automated';
                """)

    mk_instance_obj, collection_obj = env['mk.instance'], env['shopify.collection.ts']
    mk_instance_ids = mk_instance_obj.search([('marketplace', '=', 'shopify')])
    for instance_id in mk_instance_ids:
        collection_ids = collection_obj.search([('shopify_collection_id', '!=', False), ('mk_instance_id', '=', instance_id.id)])
        instance_id.connection_to_shopify()

        batch_size = 250
        for collection_batch in tools.split_every(batch_size, collection_ids):
            # Exclude None values from the collection_dict keys
            collection_dict = {collection.shopify_collection_id: collection for collection in collection_batch if collection.shopify_collection_id is not None}

            # Create the id_filter from valid collection ids
            id_filter = ", ".join([f"{id}" for id in collection_dict.keys() if id is not None])
            ids_list = id_filter.replace('"', "").split(", ") if id_filter else []
            variables = {"ids": [f"gid://shopify/Collection/{id}" for id in ids_list if id]}

            res = instance_id.execute_graphql_query(GET_COLLECTION_PUBLICATION, variables)

            response = res.get('data', {}).get('nodes', []) if isinstance(res, dict) else []
            for shopify_collection_dict in response:
                # Skip only empty publication,
                vals = {}
                if not shopify_collection_dict:
                    continue

                collection_id = extract_numeric_id(shopify_collection_dict.get('id', ''))
                collection = collection_dict.get(str(collection_id))
                image_url_data = shopify_collection_dict.get('image', {}).get('url', '') if shopify_collection_dict.get('image', {}) else None
                if not collection:
                    continue

                odoo_image = collection.image if collection.image else None
                if image_url_data:
                    image_binary = image_url_data and requests.get(image_url_data).content
                    image_base64 = base64.b64encode(image_binary)
                    shopify_image_hash = hashlib.md5(image_base64).hexdigest()

                    if odoo_image:
                        odoo_image_hash = hashlib.md5(odoo_image).hexdigest()
                        if shopify_image_hash == odoo_image_hash:
                            vals.update({'image_url': image_url_data})
                        elif shopify_image_hash != odoo_image_hash:
                            collection.process_collection_image_url(collection, odoo_image)
                elif odoo_image and not image_url_data:
                    collection.process_collection_image_url(collection, odoo_image)
                if shopify_collection_dict and shopify_collection_dict.get('resourcePublications', {}) and shopify_collection_dict.get('resourcePublications', {}).get('nodes', []):
                    shopify_publications, shopify_sales_channel_ids_list = collection.get_shopify_sales_channels_collection(shopify_collection_dict)
                    shopify_publications and vals.update(shopify_publications)
                    is_published = collection.shopify_check_is_collection_published(shopify_sales_channel_ids_list)
                    vals.update({'is_available_in_website': is_published})
                collection.write(vals)
