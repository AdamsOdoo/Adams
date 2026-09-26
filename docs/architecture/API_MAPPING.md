# Odoo ↔ Shopify API Mapping

## Status: Initial Draft
## See also: docs/agents/04_SHARED_MEMORY.md for detailed field mapping tables

---

## Shopify GraphQL Endpoints

| Operation | Shopify API | GraphQL Type | Estimated Cost |
|-----------|------------|-------------|---------------|
| Get Products | products | Query | 10-50 |
| Get Single Product | product(id:) | Query | 5-10 |
| Create Product | productCreate | Mutation | 10 |
| Update Product | productUpdate | Mutation | 10 |
| Delete Product | productDelete | Mutation | 10 |
| Get Customers | customers | Query | 10-50 |
| Create Customer | customerCreate | Mutation | 10 |
| Update Customer | customerUpdate | Mutation | 10 |
| Get Orders | orders | Query | 10-50 |
| Get Inventory | inventoryLevels | Query | 10-50 |
| Adjust Inventory | inventoryAdjustQuantities | Mutation | 10 |
| Get Locations | locations | Query | 5 |

## API Base URL Pattern
```
https://{shop_url}/admin/api/{api_version}/graphql.json
```

## Authentication Header
```
X-Shopify-Access-Token: {access_token}
Content-Type: application/json
```
