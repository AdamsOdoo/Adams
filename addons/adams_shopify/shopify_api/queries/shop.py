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
