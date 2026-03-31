FETCH_LOCATIONS = """
query FetchLocations {
  locations(first: 50) {
    edges {
      node {
        id
        name
        isActive
        address {
          address1
          city
          province
          country
          zip
        }
      }
    }
  }
}
"""

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
