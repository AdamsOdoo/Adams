"""Dependency-free canonical Shopify inventory documents shared by adapters."""

INVENTORY_PAIR_QUERY = (
    "query InventoryPairRead($itemId: ID!, $locationId: ID!) { "
    "inventoryItem(id: $itemId) { id tracked "
    "inventoryLevel(locationId: $locationId) { id item { id } location { id } "
    "quantities(names: [\"available\"]) { name quantity updatedAt } } } "
    "shop { myshopifyDomain } }"
)

__all__ = ["INVENTORY_PAIR_QUERY"]
