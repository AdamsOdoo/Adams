import hashlib
import logging

from odoo import models, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException

_logger = logging.getLogger("Teqstars:Shopify")

# Pricelist item fields that, when changed, can affect the resolved price.
PRICELIST_ITEM_PRICE_FIELDS = (
    'fixed_price', 'compute_price', 'percent_price', 'price_discount',
    'price_round', 'price_min_margin', 'price_max_margin', 'price_surcharge',
    'base', 'base_pricelist_id', 'product_tmpl_id', 'product_id',
    'categ_id', 'applied_on', 'min_quantity', 'date_start', 'date_end',
)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def write(self, vals):
        """
        Task: T7486 - Trigger real-time Shopify price sync on product template price update.

        Overrides `write` to:
        - Detect changes to `list_price` on product templates.
        - Prevent recursive sync using context flag.
        - Collect all related product variants.
        - Trigger real-time Shopify price synchronization for those variants.

        Args:
            vals (dict): Values to update.

        Returns:
            result: Super method result.
        """
        trigger_sync = 'list_price' in vals and not self.env.context.get('shopify_skip_auto_price_sync', False)

        ctx = dict(self.env.context)
        if trigger_sync:
            ctx.update({'shopify_skip_auto_price_sync': True})

        res = super(ProductTemplate, self.with_context(ctx)).write(vals)

        # Trigger synchronization after the transaction successfully writes
        if trigger_sync:
            product_ids = self.mapped('product_variant_ids').ids
            if product_ids:
                self.env['product.product'].shopify_realtime_price_sync(product_ids, pricelist_ids=None)

        return res

    def shopify_export_product_limitation(self):
        """
        Checking for maximum product export limit to prevent user's process.

        :return: True if selected product isn't more than limit.
        :rtype: bool
        :raise MarketplaceException:
                * if selected product more than given limit.
        """
        max_limit = 80
        if self and len(self) > max_limit:
            raise MarketplaceException(_("System won't allows to export more then 80 products at a time. Please select only 80 product for export."))
        return True

    def shopify_prepare_vals_for_create_listing(self, mk_instance_id):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        """
        vals = {}
        if hasattr(self, 'website_description'):
            description = getattr(self, 'website_description')
        else:
            description = self.description_sale
        description and vals.update({'description': description})
        if self.product_tag_ids:
            shopify_tag_vals = self.env['mk.listing'].prepare_tag_vals(','.join(self.product_tag_ids.mapped('name')))
            vals.update(shopify_tag_vals)
        if self.categ_id.shopify_category_id:
            shopify_category_id = self.env['shopify.product.category.ts'].search([('shopify_category_id', '=ilike', self.categ_id.shopify_category_id)])
            vals.update({'shopify_product_category_id': shopify_category_id.id})
        return vals

    def handle_shopify_listing_images(self, listing_id):
        """
        Task: T7309 - Refactor Listing Image Handling to Marketplace
        Shopify-specific method to handle listing images.
        Handle listing images by checking existing images and adding new ones if they do not already exist.
        Args:
            listing_id (obj): The listing to sync images for.
        """
        new_images = []
        listing_image_obj = self.env['mk.listing.image']

        # Collect all existing image hashes for the listing in a set for quick lookup
        existing_images = listing_image_obj.search([('mk_listing_id', '=', listing_id.id)])
        existing_image_hashes = {img.image_hex for img in existing_images}

        for product_template_image in self.product_template_image_ids:
            image_hash = hashlib.md5(product_template_image.image_1920).hexdigest()

            # Check if the image already exists in the listing
            if image_hash in existing_image_hashes:
                continue

            # If not, prepare a new image record to be created
            new_images.append({
                'name': product_template_image.name,
                'image': product_template_image.image_1920,
                'mk_listing_id': listing_id.id,
                'image_hex': image_hash
            })

        # Batch create new images
        if new_images:
            listing_image_obj.create(new_images)

    def get_hs_code_and_country_origin(self, mk_log_id, shopify_product_dict, mk_instance_id):
        """
        Task: T7393 - Retrieve and validate HS code and country of origin for Shopify product variants.

        Extracts inventory item details from Shopify product variants and checks whether
        all variants have consistent country of origin and HS code values. If consistency
        is found (either country or HS code), updates the product template accordingly.

        Args:
            mk_log_id: Log record for tracking updates.
            shopify_product_dict (dict): Shopify product data containing variants.
            mk_instance_id (record): Marketplace instance.

        Returns:
            bool: True after processing.
        """
        inventory_item_dict_list = []

        shopify_variant_list = shopify_product_dict.get("variants", {}) if isinstance(shopify_product_dict, dict) else {}

        for variant in shopify_variant_list.get('nodes', []):
            inventory_item_dict = variant.get('inventoryItem', {}) if variant else {}
            inventory_item_dict_list.append(inventory_item_dict)
        is_same_country_code, is_same_hs_code = inventory_item_dict_list and self.check_all_varinat_inventory_item(inventory_item_dict_list)
        if is_same_country_code or is_same_hs_code:
            # T7393 inventory_item_dict_list[0] Static because always same For all list value.
            self.set_hs_code_and_country_origin(mk_log_id, inventory_item_dict_list[0], mk_instance_id, is_same_country_code, is_same_hs_code)
        return True

    def check_all_varinat_inventory_item(self, inventory_item_list):
        """
        Task: T7393 - Check if all inventory items have the same country of origin and HS code.

        Args:
            inventory_item_list (list): A list of dictionaries containing inventory item details.

        Returns:
            is_same_country_code (bool): True if all items have the same country of origin.
            is_same_hs_code (bool): True if all items have the same HS code.
        """
        reference = inventory_item_list[0]

        is_same_country_code = all(item.get('countryCodeOfOrigin', '') == reference.get('countryCodeOfOrigin', '') for item in inventory_item_list)
        is_same_hs_code = all(item.get('harmonizedSystemCode', '') == reference.get('harmonizedSystemCode', '') for item in inventory_item_list)
        return is_same_country_code, is_same_hs_code

    def set_hs_code_and_country_origin(self, mk_log_id, inventory_item_dict, mk_instance_id, is_same_country_code, is_same_hs_code):
        """
        Task: T7393 - Update HS code and country of origin on product template from Shopify data.

        Updates the product template with country of origin and HS code based on the
        provided inventory item data, only if values are consistent across variants.
        Also logs the update details for tracking.

        Args:
            mk_log_id: Log record for tracking updates.
            inventory_item_dict (dict): Inventory item data containing HS code and country of origin.
            mk_instance_id (record): Marketplace instance.
            is_same_country_code (bool): Indicates if all variants share the same country of origin.
            is_same_hs_code (bool): Indicates if all variants share the same HS code.

        Returns:
            bool: True after processing.
        """
        vals, log_message_list = {}, []
        country_origin = inventory_item_dict.get('countryCodeOfOrigin', '') if isinstance(inventory_item_dict, dict) else False
        hs_code = inventory_item_dict.get('harmonizedSystemCode') if isinstance(inventory_item_dict, dict) else ''
        if not (country_origin or hs_code):
            return True
        country_id = self.env['res.country'].search([('code', '=', country_origin)], limit=1)

        if is_same_country_code:
            vals.update({'country_of_origin': country_id.id})
            log_message_list.append(_('Country Origin: %s |') % country_id.name)
        if is_same_hs_code:
            vals.update({'hs_code': hs_code})
            log_message_list.append(_('HS Code: %s') % hs_code)

        if vals:
            self.sudo().write(vals)

        if log_message_list:
            log_message = _('PRODUCT UPDATE: %s successfully updated %s') % (self.display_name, " ".join(log_message_list))
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, operation_type='import', mk_log_line_dict={'success': [{'log_message': log_message}]})
        return True


class ProductProduct(models.Model):
    _inherit = "product.product"

    def write(self, vals):
        """
        Task: T7486 - Trigger real-time Shopify price sync on product price update.

        Overrides the default `write` to:
        - Detect changes to `lst_price`.
        - Prevent recursive calls using context flag.
        - Trigger real-time Shopify price synchronization.

        Returns:
            result: Super method result.
        """
        trigger_sync = 'lst_price' in vals and not self.env.context.get('shopify_skip_auto_price_sync', False)

        ctx = dict(self.env.context)
        if trigger_sync:
            ctx.update({'shopify_skip_auto_price_sync': True})

        res = super(ProductProduct, self.with_context(ctx)).write(vals)

        if trigger_sync:
            self.shopify_realtime_price_sync(self.product_variant_ids.ids, pricelist_ids=None)

        return res

    def shopify_realtime_price_sync(self, product_ids, pricelist_ids=None):
        """
        Task: T7486 - Perform real-time Shopify price synchronization.

        Fetches Shopify listing items linked to updated products and:
        - Filters only listed products from confirmed Shopify instances.
        - Supports optional pricelist filtering.
        - Groups listing items per marketplace instance.
        - Triggers bulk price update per instance.
        - Prevents recursive execution using context flags.

        Args:
            product_ids (list): List of product IDs to sync.
            pricelist_ids (list, optional): Filter by specific pricelists.

        Returns:
            bool: True after processing.
        """
        context = self.env.context
        is_update_pricelist_price = context.get('is_update_pricelist_price', False)
        shopify_skip_auto_price_sync = context.get('shopify_skip_auto_price_sync', False)

        product_ids = list({product_id for product_id in product_ids if product_id})
        if not product_ids or shopify_skip_auto_price_sync:
            return

        params = [tuple(product_ids)]
        pricelist_clause = ""
        if pricelist_ids is not None:
            pricelist_ids = tuple({pid for pid in pricelist_ids if pid})
            if not pricelist_ids:
                return
            pricelist_clause = " AND mi.pricelist_id IN %s"
            params.append(pricelist_ids)

        query = """
            SELECT mkli.id, mkli.mk_instance_id
            FROM mk_listing_item mkli
            JOIN mk_instance mi ON mkli.mk_instance_id = mi.id
            WHERE mkli.product_id IN %s
              AND mkli.is_listed = TRUE
              AND mi.marketplace = 'shopify'
              AND mi.state = 'confirmed'
              AND mi.auto_sync_price_to_shopify = TRUE
        """ + pricelist_clause

        with self.env.cr.savepoint(flush=False):
            self.env.cr.execute(query, tuple(params))
            rows = self.env.cr.fetchall()

        if not rows:
            return

        items_per_instance = {}
        for item_id, instance_id in rows:
            items_per_instance.setdefault(instance_id, []).append(item_id)

        sync_ctx = {'shopify_skip_auto_price_sync': True, 'is_manual_update_price': True}
        listing_obj = self.env['mk.listing']
        for instance_id, item_ids in items_per_instance.items():
            mk_instance_id = self.env['mk.instance'].browse(instance_id)
            if not is_update_pricelist_price and not mk_instance_id.is_export_product_sale_price:
                continue
            elif is_update_pricelist_price and mk_instance_id.is_export_product_sale_price:
                continue
            listing_items = self.env['mk.listing.item'].browse(item_ids)

            try:
                listing_obj.with_context(sync_ctx).shopify_update_product_price(mk_instance_id, listing_item_ids=listing_items)
            except Exception as e:
                _logger.error(_(f"Real-time Shopify price sync failed for instance {mk_instance_id.name}: {e}"))

    def shopify_prepare_vals_for_update_listing_item(self, mk_instance_id):
        return {'barcode': self.barcode}

    def convert_weight_uom_for_shopify(self):
        default_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        if default_uom_id == self.env.ref('uom.product_uom_lb'):
            return 'lb'
        elif default_uom_id == self.env.ref('uom.product_uom_oz'):
            return 'oz'
        elif default_uom_id == self.env.ref('uom.product_uom_kgm'):
            return 'kg'
        elif default_uom_id == self.env.ref('uom.product_uom_gram'):
            return 'g'
        raise MarketplaceException(_("Unsupported Weight UOM for Shopify. Supported weight UOM: g, kg, oz, and lb"))

    def shopify_prepare_vals_for_create_listing_item(self, mk_instance_id):
        vals = {'weight_unit': self.convert_weight_uom_for_shopify()}
        if self.type == 'consu' and not self.is_storable:
            vals.update({'inventory_management': 'dont_track'})
        if self.barcode:
            vals.update({'barcode': self.barcode})
        return vals


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def _shopify_collect_affected_products(self):
        """
        Task: T7486 - Collect affected product variants from pricelist items.

        Identifies all `product.product` records impacted by the current
        pricelist items, including:
        - Direct product references.
        - All variants of referenced product templates.

        Returns:
            list: List of affected product.product IDs.
        """
        product_ids = set()
        for item in self:
            if item.product_id:
                product_ids.add(item.product_id.id)
            elif item.product_tmpl_id:
                product_ids.update(item.product_tmpl_id.product_variant_ids.ids)
        return list(product_ids)

    def write(self, vals):
        """
        Task: T7486 - Trigger real-time Shopify price sync on pricelist item update.

        Overrides `write` to:
        - Detect changes in price-related fields.
        - Prevent recursive sync using context flag.
        - Collect affected products from pricelist items.
        - Trigger real-time Shopify price synchronization for those products.

        Args:
            vals (dict): Values to update.

        Returns:
            result: Super method result.
        """
        if self.env.context.get('shopify_skip_auto_price_sync', False) or not any(key in vals for key in PRICELIST_ITEM_PRICE_FIELDS):
            return super(ProductPricelistItem, self).write(vals)

        res = super(ProductPricelistItem, self.with_context(shopify_skip_auto_price_sync=True)).write(vals)
        product_ids = self._shopify_collect_affected_products()
        pricelist_ids = self.mapped('pricelist_id').ids
        self.env['product.product'].with_context(is_update_pricelist_price=True).shopify_realtime_price_sync(product_ids, pricelist_ids=pricelist_ids)
        return res
