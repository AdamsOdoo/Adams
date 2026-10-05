from odoo import models, fields


class ShopifyCollectionJob(models.Model):
    _name = "shopify.collection.job"
    _description = "Collection Products Job"

    job_id = fields.Text(string='Job Id', help="Products Job Id")
    response_data = fields.Char(string='Products in Job', help="Marketplace ids of the products this job was recomputing.")
    collection_id = fields.Many2one(comodel_name="shopify.collection.ts", string="Shopify Collection", ondelete='cascade')
