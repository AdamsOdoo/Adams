# Part of Shopify Simulator. Internal QA tool — not for public distribution.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SimShopifyProduct(models.Model):
    _name = 'sim.shopify.product'
    _description = 'Simulated Shopify Product'
    _order = 'create_date desc, id desc'
    _rec_name = 'title'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(
        string='Shopify GID', index=True, readonly=True,
        help='Auto-generated: gid://shopify/Product/{id}',
    )
    title = fields.Char(required=True)
    description_html = fields.Html(string='Description HTML')
    vendor = fields.Char(default='Simulator')
    product_type = fields.Char(string='Product Type')
    tags = fields.Char(help='Comma-separated tags')
    status = fields.Selection([
        ('ACTIVE', 'Active'),
        ('DRAFT', 'Draft'),
        ('ARCHIVED', 'Archived'),
    ], default='ACTIVE', required=True)
    handle = fields.Char()
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    updated_at = fields.Datetime(default=fields.Datetime.now)

    variant_ids = fields.One2many('sim.shopify.variant', 'product_id', string='Variants')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            config = self.env['sim.shopify.config'].browse(vals.get('config_id'))
            if config and not vals.get('shopify_gid'):
                vals['shopify_gid'] = config._next_gid('Product')
            if not vals.get('handle') and vals.get('title'):
                vals['handle'] = (vals['title'] or '').lower().replace(' ', '-')
        records = super().create(vals_list)
        # Auto-create default variant if none provided
        for rec in records:
            if not rec.variant_ids:
                self.env['sim.shopify.variant'].create({
                    'product_id': rec.id,
                    'title': 'Default Title',
                    'price': '0.00',
                    'sku': '',
                })
        return records

    def write(self, vals):
        vals['updated_at'] = fields.Datetime.now()
        return super().write(vals)

    def _to_graphql_node(self):
        """Return dict matching Shopify FETCH_PRODUCTS GraphQL response shape."""
        self.ensure_one()
        variants_edges = []
        for v in self.variant_ids:
            variants_edges.append({
                'node': v._to_graphql_node(),
            })
        # Build options from variant data
        options = []
        if self.variant_ids:
            option_names = set()
            for v in self.variant_ids:
                if v.option1_name and v.option1_name not in option_names:
                    option_names.add(v.option1_name)
                    options.append({
                        'name': v.option1_name,
                        'values': list({
                            vv.option1_value
                            for vv in self.variant_ids
                            if vv.option1_value and vv.option1_name == v.option1_name
                        }),
                    })
            if not options:
                options = [{'name': 'Title', 'values': ['Default Title']}]
        else:
            options = [{'name': 'Title', 'values': ['Default Title']}]

        return {
            'id': self.shopify_gid,
            'title': self.title or '',
            'descriptionHtml': self.description_html or '',
            'vendor': self.vendor or '',
            'productType': self.product_type or '',
            'tags': [t.strip() for t in (self.tags or '').split(',') if t.strip()],
            'status': self.status,
            'handle': self.handle or '',
            'createdAt': self.created_at.isoformat() + 'Z' if self.created_at else '',
            'updatedAt': self.updated_at.isoformat() + 'Z' if self.updated_at else '',
            'options': options,
            'images': {'edges': []},
            'variants': {'edges': variants_edges},
        }


class SimShopifyVariant(models.Model):
    _name = 'sim.shopify.variant'
    _description = 'Simulated Shopify Product Variant'
    _order = 'sequence, id'

    product_id = fields.Many2one(
        'sim.shopify.product', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(
        string='Shopify GID', index=True, readonly=True,
    )
    inventory_item_gid = fields.Char(
        string='Inventory Item GID', readonly=True,
    )
    title = fields.Char(default='Default Title')
    sku = fields.Char(string='SKU')
    barcode = fields.Char()
    price = fields.Char(default='0.00', help='Price as string (Shopify format)')
    compare_at_price = fields.Char()
    inventory_quantity = fields.Integer(default=0)
    weight = fields.Float()
    weight_unit = fields.Char(default='KILOGRAMS')
    sequence = fields.Integer(default=10)

    # Option values (up to 3 options like Shopify)
    option1_name = fields.Char(string='Option 1 Name')
    option1_value = fields.Char(string='Option 1 Value')
    option2_name = fields.Char(string='Option 2 Name')
    option2_value = fields.Char(string='Option 2 Value')
    option3_name = fields.Char(string='Option 3 Name')
    option3_value = fields.Char(string='Option 3 Value')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            product = self.env['sim.shopify.product'].browse(vals.get('product_id'))
            config = product.config_id if product else None
            if config and not vals.get('shopify_gid'):
                vals['shopify_gid'] = config._next_gid('ProductVariant')
            if config and not vals.get('inventory_item_gid'):
                vals['inventory_item_gid'] = config._next_gid('InventoryItem')
        return super().create(vals_list)

    def _to_graphql_node(self):
        """Return dict matching Shopify variant node shape."""
        self.ensure_one()
        selected_options = []
        if self.option1_name:
            selected_options.append({
                'name': self.option1_name,
                'value': self.option1_value or '',
            })
        if self.option2_name:
            selected_options.append({
                'name': self.option2_name,
                'value': self.option2_value or '',
            })
        if self.option3_name:
            selected_options.append({
                'name': self.option3_name,
                'value': self.option3_value or '',
            })
        if not selected_options:
            selected_options = [{'name': 'Title', 'value': self.title or 'Default Title'}]

        return {
            'id': self.shopify_gid,
            'title': self.title or 'Default Title',
            'sku': self.sku or '',
            'barcode': self.barcode or '',
            'price': self.price or '0.00',
            'compareAtPrice': self.compare_at_price or None,
            'inventoryQuantity': self.inventory_quantity,
            'inventoryItem': {
                'id': self.inventory_item_gid,
            },
            'weight': self.weight,
            'weightUnit': self.weight_unit or 'KILOGRAMS',
            'selectedOptions': selected_options,
            'product': {
                'id': self.product_id.shopify_gid,
            },
        }
