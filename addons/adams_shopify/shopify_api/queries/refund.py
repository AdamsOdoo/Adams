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
