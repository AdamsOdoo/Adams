import logging

_logger = logging.getLogger(__name__)

FULFILLMENT_CREATE_MUTATION = """
mutation FulfillmentCreate($fulfillment: FulfillmentV2Input!) {
  fulfillmentCreateV2(fulfillment: $fulfillment) {
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


class FulfillmentSync:
    """Push fulfillment information from Odoo to Shopify."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        from ..shopify_api.client import ShopifyClient
        self.client = ShopifyClient(backend)

    def push_fulfillment(self, order_binding, tracking_number=None,
                         tracking_url=None, tracking_company=None):
        """Create a fulfillment on Shopify for a confirmed delivery."""
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

        for fo_edge in fulfillment_orders:
            fo = fo_edge.get('node', {})
            if fo.get('status') not in ('OPEN', 'IN_PROGRESS'):
                continue

            line_items = []
            for li_edge in fo.get('lineItems', {}).get('edges', []):
                li = li_edge.get('node', {})
                if li.get('remainingQuantity', 0) > 0:
                    line_items.append({
                        'id': li['id'],
                        'quantity': li['remainingQuantity'],
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
                result_key='fulfillmentCreateV2',
                estimated_cost=10,
            )

        _logger.info(
            "Fulfillment pushed for order binding %s",
            order_binding.id,
        )
