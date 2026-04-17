# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
FETCH_PRODUCT_METAFIELDS = """
query FetchProductMetafields($productId: ID!) {
  product(id: $productId) {
    metafields(first: 50) {
      edges {
        node {
          id
          namespace
          key
          value
          type
        }
      }
    }
  }
}
"""

METAFIELD_SET_MUTATION = """
mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields {
      id
      namespace
      key
      value
    }
    userErrors {
      field
      message
    }
  }
}
"""

METAFIELD_DELETE_MUTATION = """
mutation MetafieldDelete($input: MetafieldDeleteInput!) {
  metafieldDelete(input: $input) {
    deletedId
    userErrors {
      field
      message
    }
  }
}
"""
