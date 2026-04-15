# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
SHOP_QUERY = """
query {
  shop {
    name
    email
    myshopifyDomain
    plan {
      displayName
      partnerDevelopment
      shopifyPlus
    }
    currencyCode
    timezoneAbbreviation
  }
}
"""
