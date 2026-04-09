FETCH_PRODUCTS = """
query FetchProducts($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        title
        bodyHtml
        vendor
        productType
        tags
        status
        handle
        createdAt
        updatedAt
        options {
          name
          values
        }
        images(first: 20) {
          edges {
            node {
              id
              url
              altText
            }
          }
        }
        variants(first: 250) {
          edges {
            node {
              id
              title
              sku
              barcode
              price
              compareAtPrice
              weight
              weightUnit
              inventoryQuantity
              inventoryItem {
                id
              }
              selectedOptions {
                name
                value
              }
            }
          }
        }
      }
    }
  }
}
"""

PRODUCT_SET_MUTATION = """
mutation ProductSet($input: ProductSetInput!) {
  productSet(input: $input) {
    product {
      id
      title
      handle
      variants(first: 100) {
        edges {
          node {
            id
            sku
          }
        }
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

PRODUCT_CREATE_MUTATION = """
mutation ProductCreate($input: ProductInput!) {
  productCreate(input: $input) {
    product {
      id
      title
      handle
      variants(first: 100) {
        edges {
          node {
            id
            sku
            inventoryItem {
              id
            }
          }
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

PRODUCT_UPDATE_MUTATION = """
mutation ProductUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
    }
    userErrors {
      field
      message
    }
  }
}
"""

VARIANT_BULK_UPDATE_MUTATION = """
mutation VariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants {
      id
      sku
      price
    }
    userErrors {
      field
      message
    }
  }
}
"""
