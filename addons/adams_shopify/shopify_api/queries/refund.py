# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
REFUND_CREATE = """
mutation RefundCreate($input: RefundInput!) {
  refundCreate(input: $input) {
    refund {
      id
      totalRefundedSet {
        shopMoney {
          amount
          currencyCode
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

FETCH_REFUNDS = """
query FetchRefunds($orderId: ID!) {
  order(id: $orderId) {
    refunds {
      id
      note
      createdAt
      totalRefundedSet {
        shopMoney {
          amount
          currencyCode
        }
      }
      refundLineItems(first: 50) {
        edges {
          node {
            lineItem {
              id
              title
              variant {
                id
                sku
              }
            }
            quantity
            restockType
            subtotalSet {
              shopMoney {
                amount
              }
            }
          }
        }
      }
    }
  }
}
"""
