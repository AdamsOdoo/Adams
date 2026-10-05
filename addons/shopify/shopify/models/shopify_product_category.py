import threading

import requests
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.modules.registry import Registry

from odoo import fields, models, api, SUPERUSER_ID, _


class ShopifyProductCategory(models.Model):
    _name = "shopify.product.category.ts"
    _description = "Shopify Product Category"
    _rec_name = 'complete_name'

    name = fields.Char('Name', required=True, copy=False)
    parent_id = fields.Many2one('shopify.product.category.ts', 'Parent Category', ondelete='cascade')
    shopify_category_id = fields.Char("Shopify Category Id", copy=False, help='Indicates shopify category id')
    listing_count = fields.Integer('Listings', compute='_compute_shopify_listing_count', help="The number of listing under this category (Does not consider the children categories)")
    complete_name = fields.Char('Complete Name', compute='_compute_shopify_category_complete_name', recursive=True, store=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_shopify_category_complete_name(self):
        """
        Task: T5836 - Migrate Shopify to v19
        Computes the complete_name of the shopify category by combining its name with the names
        of its parent categories in a hierarchical format (e.g. "Parent / Parent Child/ Child").
        This computed field is used as the display name (rec_name) for Shopify product categories,
        similar to how Odoo handles category names.
        """
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    def _compute_shopify_listing_count(self):
        """
        Task: T5836 - Migrate Shopify to v19
        Computes the total number of listings (`mk.listing` records) linked to each Shopify product category,
        including its child categories.
        """
        read_group_res = self.env['mk.listing']._read_group([('shopify_product_category_id', 'child_of', self.ids)], ['shopify_product_category_id'], ['__count'])
        group_data = {categ.id: count for categ, count in read_group_res}
        for shopify_categ in self:
            listing_count = 0
            for sub_categ_id in shopify_categ.search([('id', 'child_of', shopify_categ.ids)]).ids:
                listing_count += group_data.get(sub_categ_id, 0)
            shopify_categ.listing_count = listing_count

    def action_view_shopify_listings(self):
        """
        Task: T5836 - Migrate Shopify to v19
        Opens listing view from shopify product category, on click on listing smart button.
        """
        category_ids = self.search([('id', 'child_of', self.id)]).ids

        # Return action with filtered listings
        return {
            'type': 'ir.actions.act_window',
            'name': _("Listing"),
            'view_mode': 'list,form',
            'res_model': 'mk.listing',
            'domain': [('shopify_product_category_id', 'in', category_ids)],
        }

    def import_category_from_shopify(self, db_name):
        """
        Task: T5836 - Migrate Shopify to v19
        This method will create all category from shopify to 'shopify.product.category.ts' model.
        """
        try:
            url = "https://raw.githubusercontent.com/Shopify/product-taxonomy/main/dist/en/categories.json"
            # Task: T7725 - Added timeout and response status validation for Shopify category API request.
            response = requests.get(url, timeout=(5, 30))
            response.raise_for_status()
            shopify_categories = response.json()

            # Access the database registry for the specified database
            db_registry = Registry(db_name)
            with db_registry.cursor() as cr:
                # Create a new Odoo environment
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['shopify.product.category.ts'].create_shopify_category(shopify_categories)

        except Exception as e:
            raise MarketplaceException(_(f"Error while importing the shopify category!: {e}"))

    def create_shopify_category(self, shopify_categories, parent_id=None):
        """
        Task: T5836 - Migrate Shopify to v19
        Recursively creates product categories in shopify product category using unique Shopify IDs.
        """

        def process_shopify_category(cat_data, parent_id):
            shopify_category_id = str(cat_data.get('id')).split('/')[-1]  # e.g cat_data.get('id') : 'gid://shopify/TaxonomyCategory/ap-1'
            category_name = cat_data.get('name')

            existing_category = self.search([('shopify_category_id', '=', shopify_category_id)], limit=1)
            if existing_category:
                category = existing_category
            else:
                category_vals = {
                    'name': category_name,
                    'parent_id': parent_id,
                    'shopify_category_id': shopify_category_id,
                }
                category = self.create(category_vals)

            # Recursively process children if present
            for child in cat_data.get('children', []):
                process_shopify_category(child, parent_id=category.id)

        for vertical in shopify_categories.get('verticals', []):
            for category in vertical.get('categories', []):
                process_shopify_category(category, parent_id=parent_id)

    def fetch_category_from_shopify(self):
        """
        Task T7221 - Fetch and import product categories from Shopify.
        Returns:
            True if the category fetch process is successfully triggered.
        """
        db_name = self.env.cr.dbname
        try:
            order_thread = threading.Thread(target=self.env['shopify.product.category.ts'].import_category_from_shopify, args=(db_name,))
            order_thread.start()
        except Exception as e:
            raise MarketplaceException(e)
        return True
