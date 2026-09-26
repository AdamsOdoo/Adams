# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
FETCH_GIFT_CARDS = """
query FetchGiftCards($first: Int!, $after: String) {
  giftCards(first: $first, after: $after) {
    edges {
      cursor
      node {
        id
        maskedCode
        initialValue {
          amount
          currencyCode
        }
        balance {
          amount
          currencyCode
        }
        enabled
        expiresOn
        customer {
          id
        }
        order {
          id
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
