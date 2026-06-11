# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
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
        currencyCode
        presentmentCurrencyCode
        totalPriceSet {
          shopMoney { amount currencyCode }
          presentmentMoney { amount currencyCode }
        }
        subtotalPriceSet {
          shopMoney { amount currencyCode }
          presentmentMoney { amount currencyCode }
        }
        totalShippingPriceSet {
          shopMoney { amount currencyCode }
          presentmentMoney { amount currencyCode }
        }
        totalTaxSet {
          shopMoney { amount currencyCode }
          presentmentMoney { amount currencyCode }
        }
        totalDiscountsSet {
          shopMoney { amount currencyCode }
          presentmentMoney { amount currencyCode }
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
        lineItems(first: 250) {
          pageInfo {
            hasNextPage
          }
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
                presentmentMoney { amount currencyCode }
              }
              discountAllocations {
                allocatedAmountSet {
                  shopMoney { amount currencyCode }
                  presentmentMoney { amount currencyCode }
                }
              }
              taxLines {
                title
                rate
                priceSet {
                  shopMoney { amount currencyCode }
                  presentmentMoney { amount currencyCode }
                }
              }
            }
          }
        }
        shippingLines(first: 10) {
          edges {
            node {
              title
              code
              originalPriceSet {
                shopMoney { amount currencyCode }
                presentmentMoney { amount currencyCode }
              }
              taxLines {
                title
                rate
                priceSet {
                  shopMoney { amount currencyCode }
                  presentmentMoney { amount currencyCode }
                }
              }
            }
          }
        }
        refunds { id }
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
