# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
FETCH_DISCOUNT_CODES = """
query FetchDiscountCodes($first: Int!, $after: String) {
  codeDiscountNodes(first: $first, after: $after) {
    edges {
      cursor
      node {
        id
        codeDiscount {
          ... on DiscountCodeBasic {
            title
            status
            startsAt
            endsAt
            usageLimit
            codes(first: 5) {
              edges {
                node {
                  code
                }
              }
            }
            customerGets {
              value {
                ... on DiscountPercentage {
                  percentage
                }
                ... on DiscountAmount {
                  amount {
                    amount
                    currencyCode
                  }
                }
              }
            }
            minimumRequirement {
              ... on DiscountMinimumSubtotal {
                greaterThanOrEqualToSubtotal {
                  amount
                }
              }
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""
