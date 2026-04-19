# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
DISCOUNT_CODE_BASIC_CREATE = """
mutation discountCodeBasicCreate($basicCodeDiscount: DiscountCodeBasicInput!) {
  discountCodeBasicCreate(basicCodeDiscount: $basicCodeDiscount) {
    codeDiscountNode {
      id
      codeDiscount {
        ... on DiscountCodeBasic {
          title
          status
          codes(first: 1) {
            edges {
              node {
                code
              }
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

DISCOUNT_CODE_BASIC_UPDATE = """
mutation discountCodeBasicUpdate($id: ID!, $basicCodeDiscount: DiscountCodeBasicInput!) {
  discountCodeBasicUpdate(id: $id, basicCodeDiscount: $basicCodeDiscount) {
    codeDiscountNode {
      id
    }
    userErrors {
      field
      message
    }
  }
}
"""

DISCOUNT_CODE_FREE_SHIPPING_CREATE = """
mutation discountCodeFreeShippingCreate($freeShippingCodeDiscount: DiscountCodeFreeShippingInput!) {
  discountCodeFreeShippingCreate(freeShippingCodeDiscount: $freeShippingCodeDiscount) {
    codeDiscountNode {
      id
      codeDiscount {
        ... on DiscountCodeFreeShipping {
          title
          status
          codes(first: 1) {
            edges {
              node {
                code
              }
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

DISCOUNT_CODE_FREE_SHIPPING_UPDATE = """
mutation discountCodeFreeShippingUpdate($id: ID!, $freeShippingCodeDiscount: DiscountCodeFreeShippingInput!) {
  discountCodeFreeShippingUpdate(id: $id, freeShippingCodeDiscount: $freeShippingCodeDiscount) {
    codeDiscountNode {
      id
    }
    userErrors {
      field
      message
    }
  }
}
"""

DISCOUNT_CODE_DELETE = """
mutation discountCodeDelete($id: ID!) {
  discountCodeDelete(id: $id) {
    deletedCodeDiscountId
    userErrors {
      field
      message
    }
  }
}
"""
