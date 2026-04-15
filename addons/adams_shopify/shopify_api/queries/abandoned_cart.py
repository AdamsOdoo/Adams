# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
FETCH_ABANDONED_CHECKOUTS = """
query FetchAbandonedCheckouts($first: Int!, $after: String) {
  abandonedCheckouts(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        createdAt
        updatedAt
        abandonedCheckoutUrl
        totalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
          presentmentMoney {
            amount
            currencyCode
          }
        }
        subtotalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        lineItems(first: 50) {
          edges {
            node {
              title
              quantity
              variant {
                id
                sku
                product {
                  id
                }
              }
              customAttributes {
                key
                value
              }
              originalUnitPriceSet {
                shopMoney {
                  amount
                  currencyCode
                }
                presentmentMoney {
                  amount
                  currencyCode
                }
              }
            }
          }
        }
        customer {
          id
          email
          firstName
          lastName
          phone
        }
      }
    }
  }
}
"""
