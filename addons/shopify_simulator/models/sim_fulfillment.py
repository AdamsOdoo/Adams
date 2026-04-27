# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Fulfillment, FulfillmentOrder, and FulfillmentOrderLineItem models.

These simulate the Shopify fulfillment lifecycle:
  Order → FulfillmentOrder(s) → Fulfillment(s)

FulfillmentOrders are auto-created when an order is created (one per location).
Fulfillments are created via the fulfillmentCreate mutation.
"""
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SimShopifyFulfillment(models.Model):
    _name = 'sim.shopify.fulfillment'
    _description = 'Simulated Shopify Fulfillment'
    _order = 'create_date desc, id desc'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    order_id = fields.Many2one(
        'sim.shopify.order', required=True, ondelete='cascade', index=True,
        string='Order',
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)
    status = fields.Selection([
        ('SUCCESS', 'Success'),
        ('CANCELLED', 'Cancelled'),
        ('ERROR', 'Error'),
        ('FAILURE', 'Failure'),
    ], default='SUCCESS', required=True, string='Status')

    tracking_number = fields.Char(string='Tracking Number')
    tracking_company = fields.Char(string='Tracking Company')
    tracking_url = fields.Char(string='Tracking URL')

    # JSON list of {lineItemId, quantity} fulfilled in this fulfillment
    line_items_json = fields.Text(
        string='Fulfillment Line Items (JSON)',
        help='JSON array of {lineItemId, quantity, title, variantId, sku}',
    )
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('shopify_gid'):
                config = self.env['sim.shopify.config'].browse(
                    vals.get('config_id')
                    or self.env['sim.shopify.order'].browse(
                        vals.get('order_id')
                    ).config_id.id
                )
                if config:
                    vals['shopify_gid'] = config._next_gid('Fulfillment')
        return super().create(vals_list)

    def _to_graphql_node(self):
        """Return dict matching Shopify Fulfillment GraphQL shape."""
        self.ensure_one()
        tracking_info = []
        if self.tracking_number:
            tracking_info.append({
                'number': self.tracking_number or '',
                'url': self.tracking_url or '',
                'company': self.tracking_company or '',
            })

        line_items_data = []
        if self.line_items_json:
            try:
                line_items_data = json.loads(self.line_items_json)
            except (json.JSONDecodeError, TypeError):
                pass

        fulfillment_line_items = []
        for li in line_items_data:
            fulfillment_line_items.append({
                'node': {
                    'id': li.get('lineItemId', ''),
                    'quantity': li.get('quantity', 0),
                    'lineItem': {
                        'id': li.get('lineItemId', ''),
                        'title': li.get('title', ''),
                        'variant': {
                            'id': li.get('variantId', ''),
                            'sku': li.get('sku', ''),
                        } if li.get('variantId') else None,
                    },
                },
            })

        return {
            'id': self.shopify_gid,
            'status': self.status,
            'createdAt': (
                self.created_at.isoformat() + 'Z' if self.created_at else ''
            ),
            'trackingInfo': tracking_info,
            'fulfillmentLineItems': {
                'edges': fulfillment_line_items,
            },
        }


class SimShopifyFulfillmentOrder(models.Model):
    _name = 'sim.shopify.fulfillment.order'
    _description = 'Simulated Shopify Fulfillment Order'
    _order = 'id'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    order_id = fields.Many2one(
        'sim.shopify.order', required=True, ondelete='cascade', index=True,
        string='Order',
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)
    status = fields.Selection([
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('CLOSED', 'Closed'),
        ('CANCELLED', 'Cancelled'),
        ('SCHEDULED', 'Scheduled'),
    ], default='OPEN', required=True, string='Status')
    assigned_location_id = fields.Many2one(
        'sim.shopify.location', ondelete='set null',
        string='Assigned Location',
    )
    line_item_ids = fields.One2many(
        'sim.shopify.fulfillment.order.line', 'fulfillment_order_id',
        string='Line Items',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('shopify_gid'):
                config = self.env['sim.shopify.config'].browse(
                    vals.get('config_id')
                    or self.env['sim.shopify.order'].browse(
                        vals.get('order_id')
                    ).config_id.id
                )
                if config:
                    vals['shopify_gid'] = config._next_gid('FulfillmentOrder')
        return super().create(vals_list)

    def _to_graphql_node(self):
        """Return dict matching Shopify FulfillmentOrder response shape."""
        self.ensure_one()
        line_edges = []
        for line in self.line_item_ids:
            line_edges.append({'node': line._to_graphql_node()})

        return {
            'id': self.shopify_gid,
            'status': self.status,
            'lineItems': {
                'edges': line_edges,
            },
        }


class SimShopifyFulfillmentOrderLine(models.Model):
    _name = 'sim.shopify.fulfillment.order.line'
    _description = 'Simulated Shopify Fulfillment Order Line Item'
    _order = 'id'

    fulfillment_order_id = fields.Many2one(
        'sim.shopify.fulfillment.order', required=True,
        ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(
        string='FulfillmentOrderLineItem GID', index=True, readonly=True,
    )
    # Link to the original order line item
    order_line_id = fields.Many2one(
        'sim.shopify.order.line', ondelete='set null',
        string='Order Line Item',
    )
    variant_gid = fields.Char(string='Variant GID')
    sku = fields.Char(string='SKU')
    title = fields.Char(string='Title')
    total_quantity = fields.Integer(
        string='Total Quantity', default=1,
        help='Original order quantity for this line.',
    )
    remaining_quantity = fields.Integer(
        string='Remaining Quantity', default=1,
        help='Quantity not yet fulfilled.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('shopify_gid'):
                fo = self.env['sim.shopify.fulfillment.order'].browse(
                    vals.get('fulfillment_order_id')
                )
                config = fo.config_id if fo else None
                if config:
                    vals['shopify_gid'] = config._next_gid(
                        'FulfillmentOrderLineItem'
                    )
        return super().create(vals_list)

    def _to_graphql_node(self):
        """Return dict matching Shopify FulfillmentOrderLineItem shape."""
        self.ensure_one()
        variant_node = None
        if self.variant_gid:
            variant_node = {
                'id': self.variant_gid,
                'sku': self.sku or '',
            }

        return {
            'id': self.shopify_gid,
            'remainingQuantity': self.remaining_quantity,
            'totalQuantity': self.total_quantity,
            'lineItem': {
                'id': self.order_line_id.shopify_gid if self.order_line_id else '',
                'title': self.title or '',
                'variant': variant_node,
            },
        }
