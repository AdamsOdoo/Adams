from odoo import models, fields, api, _

# Task: T8887 - A collection has one or more sources; its products are the products of all of them.
SOURCE_TARGET_TYPE = [('PRODUCTS', 'Products'), ('VARIANTS', 'Variants')]

# A source adds products by rules and by hand (Conditions), or takes them from other collections.
SOURCE_KIND = [('conditions', 'Conditions'), ('sub_collections', 'Collections')]

# The single source type choice shown on Shopify; it sets the kind and the target.
SOURCE_TYPE = [('products', 'Products'), ('variants', 'Variants'), ('collections', 'Collections')]
MATCH_TYPE_SELECTION = [('all', 'All Condition'), ('any', 'Any Condition')]


def default_source_title(source_kind, target_type):
    """
    Task: T8887 - Give the title Shopify needs for a new source: Products, Variants or Collection.
    Args:
        source_kind (str): 'conditions' or 'sub_collections'.
        target_type (str): 'PRODUCTS' or 'VARIANTS'.
    Returns:
        str: The title.
    """
    if source_kind == 'sub_collections':
        return 'Collection'
    return dict(SOURCE_TARGET_TYPE).get(target_type, 'Products')


class ShopifyCollectionSource(models.Model):
    """One "Products" (or "Variants") card of a Shopify collection."""
    _name = "shopify.collection.source.ts"
    _description = "Shopify Collection Source"
    _order = "sequence, id"

    sequence = fields.Integer("Sequence", default=10, help="Sets the order of this source in the collection.")
    collection_id = fields.Many2one("shopify.collection.ts", "Collection", ondelete='cascade', required=True, index=True, help="Collection this source belongs to.")
    mk_instance_id = fields.Many2one(related='collection_id.mk_instance_id', string="Instance", store=True, help="Shopify store of the collection.")
    shopify_source_id = fields.Char("Shopify Source ID", copy=False, help="The ID of this source in Shopify..")
    # Products sources add whole products; Variants sources add only the matching variants.
    target_type = fields.Selection(SOURCE_TARGET_TYPE, "Applies To", default='PRODUCTS', required=True, help="Choose whether the rules apply to whole products or specific variants.")
    source_kind = fields.Selection(SOURCE_KIND, "Source Kind", default='conditions', required=True, help="Conditions: add products by rules. Collections: add products from other collections.")
    sub_collection_ids = fields.Many2many("shopify.collection.ts", "shopify_collection_source_sub_rel", "source_id", "sub_collection_id", string="Collections",
                                          help="Collections whose products are added to this collection.")

    inclusion_match_type = fields.Selection(MATCH_TYPE_SELECTION, "Products must match", default='any', help="Add a product when it matches all or any of the rules.")
    exclusion_match_type = fields.Selection(MATCH_TYPE_SELECTION, "Exclude products matching", default='any', help="Exclude a product when it matches all or any of the exclude rules.")

    condition_ids = fields.One2many("shopify.collection.condition.ts", "source_id", string="Conditions", domain=[('kind', '=', 'inclusion')], context={'default_kind': 'inclusion'}, help="Rules that add products to this collection.")
    exclusion_condition_ids = fields.One2many("shopify.collection.condition.ts", "source_id", string="Exclude Conditions", domain=[('kind', '=', 'exclusion')], context={'default_kind': 'exclusion'}, help="Rules that keep products out of this collection.")
    selection_ids = fields.One2many("shopify.collection.source.selection.ts", "source_id", string="Manually Included Products", help="Products added by hand, with the variants chosen for each.")
    selection_listing_ids = fields.Many2many("mk.listing", string="Hand-picked Products", compute='_compute_selection_mirrors', inverse='_inverse_selection_listing_ids',
                                             help="Products added to this source by hand.")
    selection_item_ids = fields.Many2many("mk.listing.item", string="Manually Included Variants", compute='_compute_selection_mirrors', inverse='_inverse_selection_item_ids',
                                          help="Hand-picked variants for a Variants source.")
    exclusion_listing_ids = fields.Many2many("mk.listing", "shopify_collection_source_exclusion_rel", "source_id", "listing_id", string="Manually Excluded Products",
                                             help="Products always kept out, even when the rules match them.")

    # The single source type choice; it sets the kind and target fields that are sent to Shopify.
    source_type = fields.Selection(SOURCE_TYPE, "Source Type", compute='_compute_source_type',
                                   inverse='_inverse_source_type',
                                   help="What this source adds: products, variants or other collections. Fixed once synced to Shopify.")
    condition_count = fields.Integer(compute='_compute_condition_counts', help="Number of include rules.")
    exclusion_condition_count = fields.Integer(compute='_compute_condition_counts', help="Number of exclude rules.")
    has_category_condition = fields.Boolean(compute='_compute_condition_counts', help="Set when an include rule matches product categories.")
    has_exclusion_category_condition = fields.Boolean(compute='_compute_condition_counts', help="Set when an exclude rule matches product categories.")
    has_status_condition = fields.Boolean(compute='_compute_condition_counts', help="Set when an include rule matches the product status.")

    display_name = fields.Char(compute='_compute_display_name', store=False)

    def action_open_source_picker(self, view_xmlid, name, prefill):
        """
        Task: T8887 - Open a popup to choose the products, variants or collections of this source.
            The popup opens with what the source already holds.
        Args:
            view_xmlid (str): The popup view.
            name (str): The popup title.
            prefill (dict): Popup fields to fill with the current records.
        Returns:
            dict: Action that opens the popup.
        """
        self.ensure_one()
        context = {'default_collection_source_id': self.id, 'default_mk_instance_id': self.mk_instance_id.id}
        context.update({field: [(6, 0, record_ids)] for field, record_ids in prefill.items()})
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'mk.operation',
            'view_mode': 'form',
            'views': [(self.env.ref(view_xmlid).id, 'form')],
            'target': 'new',
            'context': context,
        }

    def action_open_select_products_wizard(self):
        """
        Task: T8887 - Open the popup to add products to this source, or variants for a Variants source.
        Returns:
            dict: Action that opens the popup.
        """
        if self.target_type == 'VARIANTS':
            return self.action_open_source_picker(
                'shopify.mk_operation_add_variants_to_source_view', _("Add Variants"),
                {'default_add_selection_item_ids': self.selection_item_ids.ids})
        return self.action_open_source_picker(
            'shopify.mk_operation_add_products_to_source_view', _("Add Products"),
            {'default_add_selection_listing_ids': self.selection_listing_ids.ids})

    def action_open_select_collections_wizard(self):
        """
        Task: T8887 - Open the popup to choose the collections this source takes products from.
        Returns:
            dict: Action that opens the popup.
        """
        return self.action_open_source_picker(
            'shopify.mk_operation_add_collections_to_source_view', _("Add Collections"),
            {'default_add_sub_collection_ids': self.sub_collection_ids.ids})

    @api.model_create_multi
    def create(self, vals_list):
        """
        Task: T8887 - Create the sources, and show their products added by hand on the collection right away.
        Args:
            vals_list (list): Values of the new sources.
        Returns:
            recordset: The new sources.
        """
        sources = super().create(vals_list)
        for source in sources.filtered('selection_ids'):
            source.collection_id.update_hand_picked_items(source.selection_ids.mk_listing_id, self.env['mk.listing'])
        return sources

    def write(self, vals):
        """
        Task: T8887 - Update the source, and keep its products added by hand when its first rule is added.
            Without this, adding a rule would remove those products from Shopify. Products added or
            removed by hand show on the collection right away.
        Args:
            vals (dict): Values to update.
        Returns:
            bool: True.
        """
        gaining_conditions = self.browse()
        if 'condition_ids' in vals and 'selection_listing_ids' not in vals:
            gaining_conditions = self.filtered(lambda source: not source.condition_ids and not source.selection_listing_ids)
        old_listings_by_source = {}
        if {'selection_ids', 'selection_listing_ids', 'selection_item_ids', 'source_type', 'source_kind'} & set(vals):
            old_listings_by_source = {source: source.selection_ids.mk_listing_id for source in self}
        res = super().write(vals)
        for source in gaining_conditions:
            if source.condition_ids and not source.selection_listing_ids and source.collection_id.mk_listing_ids:
                source.selection_listing_ids = [(6, 0, source.collection_id.mk_listing_ids.ids)]
        for source, old_listings in old_listings_by_source.items():
            new_listings = source.selection_ids.mk_listing_id
            source.collection_id.update_hand_picked_items(new_listings - old_listings, old_listings - new_listings)
        return res

    def unlink(self):
        """
        Task: T8887 - Delete the sources, and take their products added by hand off the collection when nothing else holds them.
        Returns:
            bool: True.
        """
        removed_listings_by_collection = {}
        for source in self:
            removed_listings = removed_listings_by_collection.get(source.collection_id, self.env['mk.listing'])
            removed_listings_by_collection[source.collection_id] = removed_listings | source.selection_ids.mk_listing_id
        res = super().unlink()
        for collection, removed_listings in removed_listings_by_collection.items():
            if collection.exists():
                collection.update_hand_picked_items(self.env['mk.listing'], removed_listings)
        return res

    @api.depends('selection_ids.mk_listing_id', 'selection_ids.mk_listing_item_ids')
    def _compute_selection_mirrors(self):
        """
        Task: T8887 - Fill the product and variant lists from the lines added by hand.
        """
        for source in self:
            source.selection_listing_ids = source.selection_ids.mk_listing_id
            source.selection_item_ids = source.selection_ids.mk_listing_item_ids

    def _inverse_selection_listing_ids(self):
        """
        Task: T8887 - Update the lines added by hand from the product list.
            A product removed from the list takes its variants with it.
        """
        for source in self:
            wanted = source.selection_listing_ids
            # As superuser, because the Marketplace User edits this list but holds no delete right.
            source.selection_ids.filtered(lambda line: line.mk_listing_id not in wanted).sudo().unlink()
            missing = wanted - source.selection_ids.mk_listing_id
            if missing:
                source.selection_ids = [(0, 0, {'mk_listing_id': listing.id}) for listing in missing]

    def _inverse_selection_item_ids(self):
        """
        Task: T8887 - Update the lines added by hand from the variant list.
        """
        for source in self:
            picked_variants = source.selection_item_ids
            for listing in picked_variants.mk_listing_id:
                line = source.selection_ids.filtered(lambda record: record.mk_listing_id == listing)[:1]
                listing_variants = picked_variants.filtered(lambda item: item.mk_listing_id == listing)
                if line:
                    line.mk_listing_item_ids = [(6, 0, listing_variants.ids)]
                else:
                    source.selection_ids = [(0, 0, {'mk_listing_id': listing.id, 'mk_listing_item_ids': [(6, 0, listing_variants.ids)]})]
            # A product left with none of its variants named goes back to meaning the whole product.
            source.selection_ids.filtered(lambda line: line.mk_listing_id not in picked_variants.mk_listing_id).mk_listing_item_ids = [(5, 0, 0)]

    @api.depends('condition_ids.is_category_condition', 'exclusion_condition_ids.is_category_condition', 'condition_ids.is_status_condition')
    def _compute_condition_counts(self):
        """
        Task: T8887 - Count the include and exclude rules of the source and flag the ones matching product categories.
        """
        for source in self:
            source.condition_count = len(source.condition_ids)
            source.exclusion_condition_count = len(source.exclusion_condition_ids)
            # The category columns are only shown when a rule actually matches categories.
            source.has_category_condition = any(source.condition_ids.mapped('is_category_condition'))
            source.has_exclusion_category_condition = any(source.exclusion_condition_ids.mapped('is_category_condition'))
            source.has_status_condition = any(source.condition_ids.mapped('is_status_condition'))

    @api.depends('target_type', 'source_kind')
    def _compute_display_name(self):
        """
        Task: T8887 - Name the source Products, Variants or Collection, as Shopify does.
        """
        for source in self:
            source.display_name = default_source_title(source.source_kind, source.target_type)

    @api.depends('source_kind', 'target_type')
    def _compute_source_type(self):
        """
        Task: T8887 - Compute the source type from its kind and target.
        """
        for source in self:
            if source.source_kind == 'sub_collections':
                source.source_type = 'collections'
            else:
                source.source_type = 'variants' if source.target_type == 'VARIANTS' else 'products'

    def _inverse_source_type(self):
        """
        Task: T8887 - Set the kind and target of the source from the chosen source type.
            What the new type cannot hold is cleared: a Collections source has no rules or
            products, and a Products or Variants source takes no collections.
        """
        for source in self:
            if source.source_type == 'collections':
                source.source_kind = 'sub_collections'
                source.target_type = 'PRODUCTS'
                source.condition_ids = [(5, 0, 0)]
                source.exclusion_condition_ids = [(5, 0, 0)]
                source.selection_ids = [(5, 0, 0)]
                source.exclusion_listing_ids = [(5, 0, 0)]
            else:
                source.source_kind = 'conditions'
                source.target_type = 'VARIANTS' if source.source_type == 'variants' else 'PRODUCTS'
                source.sub_collection_ids = [(5, 0, 0)]


class ShopifyCollectionSourceSelection(models.Model):
    _name = "shopify.collection.source.selection.ts"
    _description = "Shopify Collection Source Selection"
    _order = "id"

    source_id = fields.Many2one("shopify.collection.source.ts", "Source", ondelete='cascade',
                                required=True, index=True, help="Source this product is added to.")
    mk_instance_id = fields.Many2one(related='source_id.mk_instance_id', string="Instance", store=True, help="Shopify store of the source.")
    mk_listing_id = fields.Many2one("mk.listing", "Product", ondelete='cascade', required=True, help="Product added by hand.")
    mk_listing_item_ids = fields.Many2many("mk.listing.item", "shopify_source_selection_item_rel",
                                           "selection_id", "item_id", string="Variants",
                                           help="Variants of this product to add.")

    _source_listing_uniq = models.Constraint('unique(source_id, mk_listing_id)', "A product can only be hand-picked once on a source.")

    @api.onchange('mk_listing_id')
    def _onchange_mk_listing_id_drop_foreign_variants(self):
        """
        Task: T8887 - Remove the chosen variants that do not belong to the newly chosen product.
        """
        for line in self:
            line.mk_listing_item_ids = line.mk_listing_item_ids.filtered(lambda item: item.mk_listing_id == line.mk_listing_id)