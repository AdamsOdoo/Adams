from odoo.addons.shopify.models.shopify_catalog_validation import check_variant_rule, check_variant_tier, check_variant_tier_cap
from odoo.tools import float_round

from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException


class ShopifyCatalogVariantPrice(models.Model):
    _name = "shopify.catalog.variant.price.ts"
    _description = "Shopify Catalog Variant Price"
    _order = "catalog_id, mk_listing_id, variant_shopify_id"
    _rec_name = "mk_listing_item_id"

    catalog_id = fields.Many2one('shopify.catalog.ts', string="Catalog", ondelete='cascade', required=True, index=True)
    mk_listing_item_id = fields.Many2one('mk.listing.item', string="Listing Item", ondelete='set null')
    mk_listing_id = fields.Many2one('mk.listing', string="Listing", index=True)
    variant_shopify_id = fields.Char("Marketplace Identification", index=True, related="mk_listing_item_id.mk_id")
    currency_id = fields.Many2one('res.currency', string="Currency", related='catalog_id.currency_id', store=True)
    price = fields.Monetary("Fixed Price", default=0.0)
    compare_at_price = fields.Monetary("Compare At Price", default=0.0)
    minimum_quantity = fields.Integer("Minimum Qty", default=1)
    maximum_quantity = fields.Integer("Maximum Qty", help="0 means no upper limit.")
    increment = fields.Integer("Increment", default=1)
    origin_type = fields.Selection([('FIXED', 'Fixed'), ('RELATIVE', 'Relative')], string="Rule Origin")
    is_default = fields.Boolean("Default Rule")
    quantity_price_break_ids = fields.One2many('shopify.catalog.variant.price.break.ts', 'variant_price_id', string="Volume Pricing Tiers")
    show_rule_shopify_button = fields.Boolean(compute="_compute_show_rule_shopify_button")
    validation_error_summary = fields.Text("Validation Error", compute="_compute_validation_error_summary")
    has_validation_error = fields.Boolean(compute="_compute_validation_error_summary")

    @api.model_create_multi
    def create(self, vals_list):
        """
        Task: T7700 - Default the pricing origin and seed relative prices, mirroring Shopify:
            a freshly added variant follows the catalog's relative adjustment
            (RELATIVE) when one is set, otherwise it is a FIXED row. Rows imported
            from Shopify pass origin_type explicitly and are left untouched.
        Args:
            vals_list (list): List of field-value dicts to create.
        Returns:
            recordset: The created shopify.catalog.variant.price.ts records.
        """
        catalog_obj = self.env['shopify.catalog.ts']
        derived_relative_idx = []
        for index, vals in enumerate(vals_list):
            if vals.get('origin_type'):
                continue
            catalog = catalog_obj.browse(vals['catalog_id']) if vals.get('catalog_id') else catalog_obj
            if catalog and catalog.adjustment_type and catalog.adjustment_value:
                vals['origin_type'] = 'RELATIVE'
                derived_relative_idx.append(index)
            else:
                vals['origin_type'] = 'FIXED'
        records = super().create(vals_list)
        for index in derived_relative_idx:
            records[index]._apply_relative_pricing()
        return records

    def write(self, vals):
        """
        Task: T7700 - A manual price edit converts the row to a FIXED override (Shopify drops the
            relative % for that variant). Programmatic recompute passes the
            relative_recompute context, so it never trips this.
        Args:
            vals (dict): Field values to write.
        Returns:
            bool: True.
        """
        if ('price' in vals or 'compare_at_price' in vals) and 'origin_type' not in vals and not self.env.context.get('relative_recompute'):
            vals = dict(vals, origin_type='FIXED')
        return super().write(vals)

    def _compute_relative_values(self):
        """
        Task: T7700 - Effective (price, compare_at_price) for a RELATIVE row: the variant's base
            sale price adjusted by the catalog's percentage. When "Include Compare-at
            Price" is on for a decrease, the un-adjusted base price is kept as the
            compare-at so the markdown shows; otherwise compare-at is cleared.
        Returns:
            tuple: Rounded (price, compare_at_price).
        """
        self.ensure_one()
        catalog_id = self.catalog_id
        sale_price = self.mk_listing_item_id.sale_price or 0.0
        compare_at_price = self.compare_at_price
        adjustment_value = catalog_id.adjustment_value or 0.0
        if adjustment_value and catalog_id.adjustment_type:
            price_factor = (1 + adjustment_value / 100.0) if catalog_id.adjustment_type == 'PERCENTAGE_INCREASE' else (1 - adjustment_value / 100.0)
            price = sale_price * price_factor
        else:
            price = sale_price
        if adjustment_value and catalog_id.include_compare_at_price and compare_at_price:
            factor = (1 + adjustment_value / 100.0) if catalog_id.adjustment_type == 'PERCENTAGE_INCREASE' else (1 - adjustment_value / 100.0)
            compare = factor
        else:
            compare = 0.0
        rounding = catalog_id.currency_id.rounding if catalog_id.currency_id else 0.01
        return float_round(price, precision_rounding=rounding), float_round(compare, precision_rounding=rounding)

    def _apply_relative_pricing(self, old_factor=1.0):
        """
        Task: T7700 - Refresh price/compare-at on every RELATIVE row in self from the catalog's
            current adjustment. FIXED (manually overridden) rows are left alone.
        Args:
            old_factor (float): Previous relative factor, for re-basing (default 1.0).
        """
        for rec in self:
            if rec.origin_type == 'FIXED':
                continue
            price, compare = rec._compute_relative_values()
            rec.with_context(relative_recompute=True).write({
                'origin_type': 'RELATIVE',
                'price': price,
                'compare_at_price': compare,
            })

    @api.depends('catalog_id.catalog_type', 'catalog_id.market_ids')
    def _compute_show_rule_shopify_button(self):
        """
        Task: T7700 - Mirror Shopify's rule-availability matrix:
            - APP / COMPANY_LOCATION catalogs always support quantity rules.
            - MARKET catalogs only allow rules in the unbound state; once a
              market is assigned, Shopify wipes the rules server-side, so we
              hide the entry point.
        Returns:
            None: Sets ``show_rule_shopify_button`` on each record.
        """
        for variant_price_id in self:
            catalog_id = variant_price_id.catalog_id
            if not catalog_id:
                variant_price_id.show_rule_shopify_button = False
            elif catalog_id.catalog_type in ['APP', 'COMPANY_LOCATION']:
                variant_price_id.show_rule_shopify_button = True
            elif catalog_id.catalog_type == 'MARKET':
                variant_price_id.show_rule_shopify_button = not bool(catalog_id.market_ids)
            else:
                variant_price_id.show_rule_shopify_button = False

    @api.depends('minimum_quantity', 'maximum_quantity', 'increment', 'quantity_price_break_ids', 'quantity_price_break_ids.validation_error')
    def _compute_validation_error_summary(self):
        """
        Task: T7700 - Aggregate own rule errors, child-tier errors, and the per-variant tier-cap check
            into a single banner string so the form can render a Shopify-style "N errors"
            alert without raising.
        Returns:
            None: Sets ``validation_error_summary`` and ``has_validation_error``.
        """
        for rec in self:
            errors = list(rec._get_rule_validation_errors())
            cap_msg = check_variant_tier_cap(len(rec.quantity_price_break_ids))
            if cap_msg:
                errors.append(cap_msg)
            for tier in rec.quantity_price_break_ids:
                if tier.validation_error:
                    errors.append(tier.validation_error)
            rec.has_validation_error = bool(errors)
            if not errors:
                rec.validation_error_summary = False
            elif len(errors) == 1:
                rec.validation_error_summary = errors[0]
            else:
                rec.validation_error_summary = _("%s errors\n%s") % (len(errors), "\n".join(errors))

    @api.constrains('minimum_quantity', 'maximum_quantity', 'increment', 'quantity_price_break_ids')
    def _check_shopify_rules(self):
        """
        Task: T7700 - Blocking constraint: raise when a variant-price row carries any
            aggregated validation error so invalid quantity rules/tiers cannot be saved.
        Raises:
            MarketplaceException: When ``validation_error_summary`` is set.
        """
        for rec in self:
            if rec.validation_error_summary:
                raise MarketplaceException(rec.validation_error_summary)

    def _get_rule_validation_errors(self):
        """
        Task: T7700 - Return Shopify quantity-rule violations for this variant row.
            Single source of truth shared by the live UI compute and the
            pre-push aggregator on the parent catalog. Delegates to the
            pure helper in shopify_catalog_validation so message wording
            stays consistent between the inline banner and the blocker.
        Returns:
            list: Validation error messages for this variant row.
        """
        self.ensure_one()
        return check_variant_rule(self)

    @api.constrains('catalog_id', 'mk_listing_item_id')
    def _check_unique_variant_per_catalog(self):
        """
        Task: T7700 - Block manual duplicate of the same Shopify variant under one catalog —
            mirrors the (catalog_id, variant_shopify_id) upsert key used by import.
        Raises:
            MarketplaceException: When the variant already exists on the catalog.
        """
        for rec in self:
            if not rec.variant_shopify_id:
                continue
            duplicate = self.search_count([
                ('id', '!=', rec.id),
                ('catalog_id', '=', rec.catalog_id.id),
                ('variant_shopify_id', '=', rec.variant_shopify_id),
            ])
            if duplicate:
                raise MarketplaceException(_("This variant is already added to the catalog."))

    @api.constrains('price', 'compare_at_price')
    def _check_price_non_negative(self):
        """
        Task: T7700 - Hard invariant — corruption guard only. Shopify policy rules
            (tier-vs-base, ordering, etc.) live in the live compute so the
            user can save partial state and iterate.
        Raises:
            MarketplaceException: When price or compare-at price is negative.
        """
        for rec in self:
            if rec.price and rec.price < 0:
                raise MarketplaceException(_("Price cannot be negative."))
            if rec.compare_at_price and rec.compare_at_price < 0:
                raise MarketplaceException(_("Compare-at price cannot be negative."))

    def action_open_variant_price_form(self):
        """
        Task: T7700 - Open the variant-price detail form in a modal so users can edit price,
            quantity rules, and the volume-pricing tiers in a Shopify-style popup.
        Returns:
            dict: An ir.actions.act_window action opening the detail form.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Edit quantity rules and volume pricing',
            'res_model': 'shopify.catalog.variant.price.ts',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('shopify.shopify_catalog_variant_price_rules_form_view').id,
            'target': 'new',
        }


class ShopifyCatalogVariantPriceBreak(models.Model):
    _name = "shopify.catalog.variant.price.break.ts"
    _description = "Shopify Catalog Quantity Price Break"
    _order = "id"

    catalog_id = fields.Many2one('shopify.catalog.ts', string="Catalog", ondelete='cascade', required=True, index=True)
    variant_price_id = fields.Many2one('shopify.catalog.variant.price.ts', string="Variant Price", ondelete='cascade', index=True)
    mk_instance_id = fields.Many2one('mk.instance', related='catalog_id.mk_instance_id', store=True, index=True)
    mk_listing_item_id = fields.Many2one('mk.listing.item', string="Listing Variant", ondelete='set null')
    variant_shopify_id = fields.Char("Variant Shopify ID", index=True, related='mk_listing_item_id.mk_id')
    shopify_break_id = fields.Char("Shopify Break ID", index=True,
                                   help="Globally-unique Shopify GID for this tier. Empty for tiers created locally that haven't been pushed back to Shopify yet.")
    minimum_quantity = fields.Integer("Minimum Qty", default=1)
    currency_id = fields.Many2one('res.currency', string="Currency", related='catalog_id.currency_id', store=True)
    price = fields.Monetary("Tier Price", default=0.0)
    break_label = fields.Char("Break", compute="_compute_break_label")
    validation_error = fields.Char("Validation Error", compute="_compute_validation_error")
    is_invalid = fields.Boolean(compute="_compute_validation_error")

    _check_unique_break_id = models.Constraint("UNIQUE (catalog_id, shopify_break_id)", "A quantity price break with this ID already exists for this catalog.")

    @api.depends('variant_price_id.quantity_price_break_ids')
    def _compute_break_label(self):
        """
        Task: T7700 - Shopify-style sequential tier label ("Break 1", "Break 2", ...) based on the
            tier's position within its parent variant-price row.
        Returns:
            None: Sets ``break_label`` on each record.
        """
        for rec in self:
            breaks = rec.variant_price_id.quantity_price_break_ids
            rec.break_label = _("Break %s") % (list(breaks).index(rec) + 1) if rec in breaks else _("Break")

    @api.depends('minimum_quantity', 'price', 'variant_price_id.minimum_quantity',
                 'variant_price_id.maximum_quantity', 'variant_price_id.increment', 'variant_price_id.quantity_price_break_ids',
                 'variant_price_id.quantity_price_break_ids.minimum_quantity')
    def _compute_validation_error(self):
        """
        Task: T7700 - Live (non-blocking) validation message for this tier; rendered inline
            in the form. Empty when the tier is valid.
        Returns:
            None: Sets ``validation_error`` and ``is_invalid``.
        """
        for rec in self:
            errors = rec._get_tier_validation_errors()
            rec.validation_error = errors[0] if errors else False
            rec.is_invalid = bool(errors)

    def _get_tier_validation_errors(self):
        """
        Task: T7700 - Return the list of Shopify rule violations for this tier.
            Single source of truth — used by the live compute on this model,
            the aggregator on the parent variant-price row, and the pre-push
            guard on the catalog. Delegates to the pure helper so wording
            matches across every render site.
        Returns:
            list: Validation error messages for this tier.
        """
        self.ensure_one()
        return check_variant_tier(self)

    @api.constrains('price')
    def _check_tier_price_non_negative(self):
        """
        Task: T7700 - Hard invariant — corruption guard only. Policy rules live in the
            live compute so the user can save and iterate.
        Raises:
            MarketplaceException: When the tier price is negative.
        """
        for rec in self:
            if rec.price and rec.price < 0:
                raise MarketplaceException(_("Tier price cannot be negative."))

    @api.onchange('variant_price_id')
    def _onchange_variant_price_id(self):
        """
        Task: T7700 - Inherit identity (catalog, listing item) from the parent variant-price
            row when a tier is added in the form.
        """
        for rec in self:
            if rec.variant_price_id:
                rec.catalog_id = rec.variant_price_id.catalog_id
                rec.mk_listing_item_id = rec.variant_price_id.mk_listing_item_id

    @api.model_create_multi
    def create(self, vals_list):
        """
        Task: T7700 - Derive catalog_id / variant_shopify_id / mk_listing_item_id from the parent
            variant-price row when a tier is created via the One2many form. The onchange
            only fires on UI interaction, so an embedded popup save can submit a vals
            dict that omits these required fields; we backfill them here.
        Args:
            vals_list (list): List of field-value dicts to create.
        Returns:
            recordset: The created shopify.catalog.variant.price.break.ts records.
        """
        variant_price_obj = self.env['shopify.catalog.variant.price.ts']
        for vals in vals_list:
            parent_id = vals.get('variant_price_id')
            if not parent_id:
                continue
            parent = variant_price_obj.browse(parent_id)
            if not vals.get('catalog_id') and parent.catalog_id:
                vals['catalog_id'] = parent.catalog_id.id
            if not vals.get('mk_listing_item_id') and parent.mk_listing_item_id:
                vals['mk_listing_item_id'] = parent.mk_listing_item_id.id
        return super().create(vals_list)
