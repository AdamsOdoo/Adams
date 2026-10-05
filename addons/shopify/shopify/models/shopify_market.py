import logging

from odoo import models, fields, _

_logger = logging.getLogger("Qamah:Shopify")

MARKET_TYPES = [
    ('COMPANY_LOCATION', 'Company Location'),
    ('LOCATION', 'Location'),
    ('NONE', 'None'),
    ('REGION', 'Region'),
]

MARKET_STATUSES = [
    ('ACTIVE', 'Active'),
    ('DRAFT', 'Draft'),]


class ShopifyMarket(models.Model):
    _name = "shopify.market.ts"
    _description = "Shopify Market"
    _rec_name = "name"

    name = fields.Char("Name", required=True)
    active = fields.Boolean(default=True)
    shopify_market_id = fields.Char("Shopify Market ID", copy=False, index=True)
    market_type = fields.Selection(MARKET_TYPES, string="Market Type")
    status = fields.Selection(MARKET_STATUSES, string="Status")
    mk_instance_id = fields.Many2one('mk.instance', "Instance", ondelete='cascade', required=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', related='mk_instance_id.company_id', store=True)
    catalog_ids = fields.Many2many(comodel_name='shopify.catalog.ts', relation='shopify_market_catalog_rel', column1='market_id', column2='catalog_id', string="Catalogs", )

    _check_unique_shopify_mk_id = models.Constraint("UNIQUE (shopify_market_id, mk_instance_id)", "A Shopify Market with this ID already exists for this instance.")


class ShopifyCompanyLocation(models.Model):
    _name = "shopify.company.location.ts"
    _description = "Shopify Company Location"

    name = fields.Char("Name", required=True)
    shopify_location_id = fields.Char("Shopify Location ID", required=True)
    shopify_company_id = fields.Char("Shopify Company ID", required=True)
    shopify_company_name = fields.Char("Shopify Company Name", required=True)
    mk_instance_id = fields.Many2one('mk.instance', "Instance", required=True)

    def _compute_display_name(self):
        for record in self:
            if record.shopify_company_name:
                record.display_name = f"{record.name} ({record.shopify_company_name})"
            else:
                record.display_name = record.name


class ShopifyApp(models.Model):
    _name = "shopify.app.ts"
    _description = "Shopify App"

    title = fields.Char("Title", required=True)
    shopify_app_id = fields.Char("Shopify App ID", required=True)
    mk_instance_id = fields.Many2one('mk.instance', "Instance", required=True)
