# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
INVENTORY_SET_QUANTITIES = """
mutation InventorySet($input: InventorySetQuantitiesInput!) {
  inventorySetQuantities(input: $input) {
    inventoryAdjustmentGroup {
      reason
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

INVENTORY_ADJUST_QUANTITIES = """
mutation InventoryAdjust($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    inventoryAdjustmentGroup {
      reason
      changes {
        name
        delta
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
