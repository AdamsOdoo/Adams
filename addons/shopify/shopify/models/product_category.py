from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    shopify_category_id = fields.Char("Shopify Category", copy=False, help='Indicates shopify product category id')

    def create_or_get_odoo_category_for_shopify_product(self, shopify_category):
        """
        Task: T4887 - Migrate Shopify REST API to Graphql API
        Recursively creates or return Odoo product categories based on a Shopify category.

        shopify_category(recordset): Recordset containing Shopify category details.
        (recordset): The Odoo category recordset.
        """
        if not shopify_category:
            return False

        parts = shopify_category.display_name
        parts = parts.split('/')
        category_id = shopify_category.shopify_category_id
        parent_id, category = False, False
        for part in parts:
            domain = ['|',
                      ('shopify_category_id', '=ilike', category_id),
                      ('name', '=ilike', part.strip()), ('parent_id', '=', parent_id)]
            category = self.search(domain, limit=1)

            if not category:
                vals = {
                    'name': part.strip(),
                    'parent_id': parent_id,
                }
                category = self.create(vals)

            # Set current category as parent for next level
            parent_id = category.id

        category.write({'shopify_category_id': category_id})
        return category
