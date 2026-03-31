FETCH_ORDERS = """
query FetchOrders($first: Int!, $after: String, $query: String) {
  orders(first: $first, after: $after, query: $query) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        name
        createdAt
        updatedAt
        displayFinancialStatus
        displayFulfillmentStatus
        cancelledAt
        closed
        note
        tags
        totalPriceSet {
          shopMoney { amount currencyCode }
        }
        subtotalPriceSet {
          shopMoney { amount currencyCode }
        }
        totalShippingPriceSet {
          shopMoney { amount currencyCode }
        }
        totalTaxSet {
          shopMoney { amount currencyCode }
        }
        totalDiscountsSet {
          shopMoney { amount currencyCode }
        }
        discountCodes
        customer {
          id
          email
          firstName
          lastName
        }
        shippingAddress {
          address1
          address2
          city
          province
          provinceCode
          country
          countryCodeV2
          zip
          phone
          firstName
          lastName
        }
        billingAddress {
          address1
          address2
          city
          province
          country
          countryCodeV2
          zip
        }
        lineItems(first: 50) {
          edges {
            node {
              id
              title
              quantity
              variant {
                id
                sku
                product {
                  id
                }
              }
              originalUnitPriceSet {
                shopMoney { amount currencyCode }
              }
              discountAllocations {
                allocatedAmountSet {
                  shopMoney { amount currencyCode }
                }
              }
              taxLines {
                title
                rate
                priceSet {
                  shopMoney { amount currencyCode }
                }
              }
            }
          }
        }
        shippingLines(first: 5) {
          edges {
            node {
              title
              code
              originalPriceSet {
                shopMoney { amount currencyCode }
              }
            }
          }
        }
      }
    }
  }
}
"""

ORDER_UPDATE_MUTATION = """
mutation orderUpdate($input: OrderInput!) {
  orderUpdate(input: $input) {
    order {
      id
      tags
      note
    }
    userErrors {
      field
      message
    }
  }
}
"""
