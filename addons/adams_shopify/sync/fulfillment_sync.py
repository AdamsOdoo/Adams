# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Fulfillment status sync between Odoo and Shopify.

Handles both directions:
- Odoo → Shopify: push_fulfillment() on stock.picking validation
- Shopify → Odoo: handle_inbound_fulfillment() from webhooks
"""

import logging

from odoo import _

_logger = logging.getLogger(__name__)

FULFILLMENT_CREATE_MUTATION = """
mutation FulfillmentCreate($fulfillment: FulfillmentInput!) {
  fulfillmentCreate(fulfillment: $fulfillment) {
    fulfillment {
      id
      status
      trackingInfo {
        number
        url
        company
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

FETCH_ORDER_FULFILLMENTS = """
query GetOrderFulfillments($id: ID!) {
  order(id: $id) {
    displayFulfillmentStatus
    fulfillmentOrders(first: 10) {
      edges {
        node {
          id
          status
          lineItems(first: 50) {
            edges {
              node {
                id
                remainingQuantity
                totalQuantity
                lineItem {
                  id
                  title
                  variant {
                    id
                    sku
                  }
                }
              }
            }
          }
        }
      }
    }
    fulfillments(first: 50) {
      id
      status
      createdAt
      trackingInfo {
        number
        url
        company
      }
      fulfillmentLineItems(first: 50) {
        edges {
          node {
            id
            quantity
            lineItem {
              id
              title
              variant {
                id
                sku
              }
            }
          }
        }
      }
    }
  }
}
"""


class FulfillmentSync:
    """Bidirectional fulfillment sync between Odoo and Shopify."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        from ..shopify_api.client import ShopifyClient
        self.client = ShopifyClient(backend)

    # ── Odoo → Shopify (outbound) ──────────────────────────

    def push_fulfillment(self, order_binding, picking=None,
                         tracking_number=None, tracking_url=None,
                         tracking_company=None):
        """Create a fulfillment on Shopify for a confirmed delivery.

        Enhanced to support line-level matching when a picking is provided,
        enabling correct split-shipment handling.
        """
        if not order_binding.shopify_id:
            _logger.warning("No Shopify ID on order binding %s", order_binding.id)
            return

        # Fetch fulfillment orders for this order
        query = """
        query GetFulfillmentOrders($id: ID!) {
          order(id: $id) {
            fulfillmentOrders(first: 10) {
              edges {
                node {
                  id
                  status
                  lineItems(first: 50) {
                    edges {
                      node {
                        id
                        remainingQuantity
                        lineItem {
                          variant {
                            id
                            sku
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        body = self.client.execute(
            query, {'id': order_binding.shopify_id}, estimated_cost=5,
        )
        fulfillment_orders = (
            body.get('data', {})
            .get('order', {})
            .get('fulfillmentOrders', {})
            .get('edges', [])
        )

        # Build a map of SKU → quantity from the picking's done moves
        picking_sku_qty = {}
        if picking:
            for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
                sku = move.product_id.default_code
                if sku:
                    picking_sku_qty[sku] = picking_sku_qty.get(sku, 0) + move.quantity

        for fo_edge in fulfillment_orders:
            fo = fo_edge.get('node', {})
            if fo.get('status') not in ('OPEN', 'IN_PROGRESS'):
                continue

            line_items = []
            for li_edge in fo.get('lineItems', {}).get('edges', []):
                li = li_edge.get('node', {})
                remaining = li.get('remainingQuantity', 0)
                if remaining <= 0:
                    continue

                if picking_sku_qty:
                    # Line-level matching: only fulfill lines that match
                    # the products in this specific picking
                    variant = li.get('lineItem', {}).get('variant', {})
                    sku = variant.get('sku', '')
                    if sku and sku in picking_sku_qty:
                        qty = min(remaining, int(picking_sku_qty[sku]))
                        if qty > 0:
                            line_items.append({
                                'id': li['id'],
                                'quantity': qty,
                            })
                            picking_sku_qty[sku] -= qty
                    # If no SKU match, skip this line (will be fulfilled
                    # by the picking that contains it)
                else:
                    # No picking context — fulfill everything remaining
                    # (legacy behavior for backward compat)
                    line_items.append({
                        'id': li['id'],
                        'quantity': remaining,
                    })

            if not line_items:
                continue

            fulfillment_input = {
                'lineItemsByFulfillmentOrder': [{
                    'fulfillmentOrderId': fo['id'],
                    'fulfillmentOrderLineItems': line_items,
                }],
            }

            if tracking_number:
                fulfillment_input['trackingInfo'] = {
                    'number': tracking_number,
                    'url': tracking_url or '',
                    'company': tracking_company or '',
                }

            self.client.execute_mutation(
                FULFILLMENT_CREATE_MUTATION,
                {'fulfillment': fulfillment_input},
                result_key='fulfillmentCreate',
                estimated_cost=10,
            )

        _logger.info(
            "Fulfillment pushed for order binding %s",
            order_binding.id,
        )

    # ── Shopify → Odoo (inbound) ──────────────────────────

    def handle_inbound_fulfillment(self, order_binding, webhook_data=None):
        """Handle a fulfillment created on Shopify (via webhook or import).

        Updates the binding status and, depending on backend settings,
        either creates an activity, auto-validates the picking, or ignores.
        """
        if not order_binding.odoo_id:
            _logger.warning(
                "No Odoo order for binding %s — cannot process inbound fulfillment",
                order_binding.id,
            )
            return

        order = order_binding.odoo_id

        # Fetch current fulfillment state from Shopify for accuracy
        new_fulfillment_status = self._fetch_fulfillment_status(order_binding)
        old_fulfillment_status = order_binding.shopify_fulfillment_status or 'unfulfilled'

        # Update binding + sale order
        order_binding.write({
            'shopify_fulfillment_status': new_fulfillment_status,
        })
        order.with_context(shopify_no_auto_export=True).write({
            'shopify_fulfillment_status': new_fulfillment_status,
        })

        if old_fulfillment_status == new_fulfillment_status:
            _logger.info(
                "Fulfillment status unchanged (%s) for order %s",
                new_fulfillment_status, order.name,
            )
            return

        handling = self.backend.external_fulfillment_handling

        if handling == 'ignore':
            _logger.info(
                "External fulfillment for order %s — status updated to %s (ignore mode)",
                order.name, new_fulfillment_status,
            )
            return

        # Find the outgoing pickings for this order
        out_pickings = order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.state not in ('done', 'cancel')
        )

        if not out_pickings:
            _logger.info(
                "No pending outgoing pickings for order %s — "
                "fulfillment may already be processed", order.name,
            )
            return

        if handling == 'auto_validate':
            self._auto_validate_pickings(order, out_pickings, webhook_data)
        elif handling == 'activity':
            self._create_fulfillment_activity(order, out_pickings, new_fulfillment_status)

    def handle_fulfillment_cancellation(self, order_binding, webhook_data=None):
        """Handle a fulfillment cancellation (restock) from Shopify."""
        if not order_binding.odoo_id:
            return

        order = order_binding.odoo_id

        # Update fulfillment status
        new_status = self._fetch_fulfillment_status(order_binding)
        order_binding.write({'shopify_fulfillment_status': new_status})
        order.with_context(shopify_no_auto_export=True).write({
            'shopify_fulfillment_status': new_status,
        })

        # Check if any pickings were already done
        done_pickings = order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.state == 'done'
        )

        if done_pickings:
            # Never auto-create returns — schedule activity instead
            try:
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_("Shopify Fulfillment Cancelled"),
                    note=_(
                        "A fulfillment was cancelled/restocked on Shopify for order %s. "
                        "Delivery %s has already been validated in Odoo. "
                        "Please review and create a return if necessary."
                    ) % (order.name, ', '.join(done_pickings.mapped('name'))),
                )
            except Exception as e:
                _logger.warning("Could not schedule activity: %s", e)
        else:
            _logger.info(
                "Fulfillment cancelled on Shopify for order %s — "
                "no done pickings in Odoo, no action needed", order.name,
            )

    def _fetch_fulfillment_status(self, order_binding):
        """Fetch the current fulfillment status from Shopify."""
        query = """
        query GetOrderStatus($id: ID!) {
          order(id: $id) {
            displayFulfillmentStatus
          }
        }
        """
        try:
            body = self.client.execute(
                query, {'id': order_binding.shopify_id}, estimated_cost=2,
            )
            status = (
                body.get('data', {})
                .get('order', {})
                .get('displayFulfillmentStatus', '')
            )
            return (status or '').lower()
        except Exception as e:
            _logger.warning("Failed to fetch fulfillment status: %s", e)
            return order_binding.shopify_fulfillment_status or 'unfulfilled'

    def _auto_validate_pickings(self, order, pickings, webhook_data):
        """Auto-validate outgoing pickings (for dropship/digital scenarios)."""
        for picking in pickings:
            try:
                # Set all move quantities to demand
                for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                    move.quantity = move.product_uom_qty
                picking.with_context(
                    skip_backorder=True,
                    shopify_no_auto_export=True,  # prevent re-pushing to Shopify
                ).button_validate()
                _logger.info(
                    "Auto-validated picking %s for externally fulfilled order %s",
                    picking.name, order.name,
                )
            except Exception as e:
                _logger.warning(
                    "Failed to auto-validate picking %s: %s", picking.name, e,
                )
                self._create_fulfillment_activity(
                    order, picking,
                    'fulfilled',
                    error_msg=str(e),
                )

    def _create_fulfillment_activity(self, order, pickings, new_status,
                                     error_msg=None):
        """Schedule an activity on the order about external fulfillment."""
        picking_names = ', '.join(
            pickings.mapped('name') if hasattr(pickings, 'mapped')
            else [pickings.name]
        )
        note = _(
            "Order was %s on Shopify (external fulfillment). "
            "Pending delivery: %s. "
            "Please verify inventory and validate the delivery."
        ) % (new_status, picking_names)

        if error_msg:
            note += _("\n\nAuto-validation failed: %s") % error_msg

        try:
            order.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_("External Shopify Fulfillment"),
                note=note,
            )
        except Exception as e:
            _logger.warning("Could not schedule fulfillment activity: %s", e)
