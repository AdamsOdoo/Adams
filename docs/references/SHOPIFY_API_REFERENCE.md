# Shopify GraphQL Admin API Reference for Adams Shopify Connector

> Sources: [GraphQL Admin API](https://shopify.dev/docs/api/admin-graphql/latest), [API Limits](https://shopify.dev/docs/api/usage/limits), [Bulk Operations](https://shopify.dev/docs/api/usage/bulk-operations), [Webhooks](https://shopify.dev/docs/apps/build/webhooks/subscribe/https)

---

## 1. API Version & Authentication

### Current Versions (March 2026)
| Version | Status | Support Until |
|---------|--------|--------------|
| **2026-01** | **Latest Stable** | ~Jan 2027 |
| 2025-10 | Stable | ~Oct 2026 |
| 2025-07 | Stable | ~Jul 2026 |
| 2025-04 | Stable (nearing EOL) | ~Apr 2026 |
| 2026-04 | Release Candidate | — |

**Recommendation**: Target `2026-01` as default, allow config override. Each version supported for 12 months minimum.

### Authentication
```
POST https://{shop}.myshopify.com/admin/api/2026-01/graphql.json
Headers:
  Content-Type: application/json
  X-Shopify-Access-Token: {access_token}
```

### Access Scopes Required
```
read_products, write_products
read_customers, write_customers
read_orders, write_orders
read_inventory, write_inventory
read_locations
read_fulfillments, write_fulfillments
read_shipping, write_shipping
```

---

## 2. Rate Limiting (Cost-Based Throttling)

### Bucket Model
| Plan | Bucket Size | Restore Rate | Effective Max |
|------|-------------|-------------|---------------|
| Standard | 1,000 points | 50 pts/sec | ~50 queries/sec for simple queries |
| Advanced | 2,000 points | 100 pts/sec | Higher throughput |
| Shopify Plus | 20,000 points | 1,000 pts/sec | 5-10x standard |

### How It Works
- Each query has a `requestedQueryCost` (estimated before execution)
- Bucket must have enough capacity for `requestedQueryCost` before execution starts
- After execution, actual cost is returned — difference is refunded to bucket
- If bucket < requestedQueryCost → 429 THROTTLED response

### Reading Throttle Status from Response
```json
{
  "data": { "products": { "..." } },
  "extensions": {
    "cost": {
      "requestedQueryCost": 12,
      "actualQueryCost": 8,
      "throttleStatus": {
        "maximumAvailable": 2000,
        "currentlyAvailable": 1988,
        "restoreRate": 100
      }
    }
  }
}
```

### Implementation Pattern
```python
class ShopifyRateLimiter:
    """Adaptive rate limiter using Shopify's throttle status."""

    def __init__(self, bucket_size=1000, restore_rate=50):
        self.available = bucket_size
        self.bucket_size = bucket_size
        self.restore_rate = restore_rate
        self.last_update = time.time()

    def wait_if_needed(self, estimated_cost):
        """Block until enough budget is available."""
        self._restore()
        if self.available < estimated_cost:
            wait = (estimated_cost - self.available) / self.restore_rate
            time.sleep(wait + 0.1)
            self._restore()

    def update_from_response(self, extensions):
        """Update state from actual Shopify response."""
        throttle = extensions.get('cost', {}).get('throttleStatus', {})
        if throttle:
            self.available = throttle['currentlyAvailable']
            self.bucket_size = throttle['maximumAvailable']
            self.restore_rate = throttle['restoreRate']
            self.last_update = time.time()

    def _restore(self):
        now = time.time()
        elapsed = now - self.last_update
        self.available = min(
            self.available + elapsed * self.restore_rate,
            self.bucket_size
        )
        self.last_update = now
```

---

## 3. Product API

### Query: Fetch Products (with pagination)
```graphql
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
        images(first: 10) {
          edges {
            node {
              id
              url
              altText
            }
          }
        }
        variants(first: 100) {
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
        metafields(first: 20) {
          edges {
            node {
              namespace
              key
              value
              type
            }
          }
        }
      }
    }
  }
}
```

### Mutation: productSet (Create or Update — RECOMMENDED for sync)
```graphql
mutation ProductSet($input: ProductSetInput!) {
  productSet(input: $input) {
    product {
      id
      title
      variants(first: 10) {
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
```

**CRITICAL**: `productSet` is the recommended mutation for sync use cases. It creates or updates in one call. However, list fields (variants, metafields) are treated as a complete replacement — any omitted variant will be DELETED. Always include all variants when using `productSet`.

### Mutation: productCreate (New products only)
```graphql
mutation ProductCreate($input: ProductInput!) {
  productCreate(input: $input) {
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
```

### Mutation: productUpdate (Existing products only)
```graphql
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
```

**Note**: `productUpdate` does NOT support updating variants. Use `productVariantsBulkUpdate` for that.

### Mutation: productVariantsBulkUpdate
```graphql
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
```

---

## 4. Customer API

### Query: Fetch Customers
```graphql
query FetchCustomers($first: Int!, $after: String) {
  customers(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        firstName
        lastName
        email
        phone
        tags
        state
        createdAt
        updatedAt
        amountSpent {
          amount
          currencyCode
        }
        defaultAddress {
          address1
          address2
          city
          province
          provinceCode
          country
          countryCodeV2
          zip
          phone
        }
        addresses {
          address1
          address2
          city
          province
          provinceCode
          country
          countryCodeV2
          zip
          phone
        }
        emailMarketingConsent {
          marketingState
          consentUpdatedAt
        }
        metafields(first: 10) {
          edges {
            node {
              namespace
              key
              value
              type
            }
          }
        }
      }
    }
  }
}
```

### Mutation: customerCreate
```graphql
mutation CustomerCreate($input: CustomerInput!) {
  customerCreate(input: $input) {
    customer {
      id
      email
    }
    userErrors {
      field
      message
    }
  }
}
```

---

## 5. Order API

### Query: Fetch Orders
```graphql
query FetchOrders($first: Int!, $after: String, $query: String) {
  orders(first: $first, after: $after, query: $query) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        name
        createdAt
        updatedAt
        displayFinancialStatus
        displayFulfillmentStatus
        cancelledAt
        closed
        note
        tags
        totalPriceSet {
          shopMoney { amount currencyCode }
          presentmentMoney { amount currencyCode }
        }
        subtotalPriceSet {
          shopMoney { amount currencyCode }
        }
        totalShippingPriceSet {
          shopMoney { amount currencyCode }
        }
        totalTaxSet {
          shopMoney { amount currencyCode }
        }
        totalDiscountsSet {
          shopMoney { amount currencyCode }
        }
        customer {
          id
          email
          firstName
          lastName
        }
        shippingAddress {
          address1
          address2
          city
          province
          provinceCode
          country
          countryCodeV2
          zip
          phone
          firstName
          lastName
        }
        billingAddress {
          address1
          address2
          city
          province
          country
          countryCodeV2
          zip
        }
        lineItems(first: 50) {
          edges {
            node {
              id
              title
              quantity
              variant {
                id
                sku
                product {
                  id
                }
              }
              originalUnitPriceSet {
                shopMoney { amount currencyCode }
              }
              discountAllocations {
                allocatedAmountSet {
                  shopMoney { amount currencyCode }
                }
              }
              taxLines {
                title
                rate
                priceSet {
                  shopMoney { amount currencyCode }
                }
              }
            }
          }
        }
        shippingLines(first: 5) {
          edges {
            node {
              title
              code
              originalPriceSet {
                shopMoney { amount currencyCode }
              }
            }
          }
        }
        transactions(first: 10) {
          id
          kind
          status
          amountSet {
            shopMoney { amount currencyCode }
          }
          gateway
          processedAt
        }
        fulfillmentOrders(first: 10) {
          edges {
            node {
              id
              status
              assignedLocation {
                name
              }
            }
          }
        }
        refunds(first: 10) {
          id
          createdAt
          totalRefundedSet {
            shopMoney { amount currencyCode }
          }
          refundLineItems(first: 20) {
            edges {
              node {
                lineItem { id }
                quantity
                subtotalSet {
                  shopMoney { amount currencyCode }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### Order Financial Status Values
| Shopify Status | Odoo Mapping |
|---------------|-------------|
| PENDING | Draft / Quotation |
| AUTHORIZED | Sale Order (confirmed) |
| PARTIALLY_PAID | Sale Order (partial payment registered) |
| PAID | Sale Order + Invoice + Payment |
| PARTIALLY_REFUNDED | Credit Note (partial) |
| REFUNDED | Credit Note (full) |
| VOIDED | Cancelled |

### Order Access Note
Only last 60 days of orders accessible by default. For historical import, the app must request `read_all_orders` scope — requires Shopify approval for public apps.

---

## 6. Inventory API

### Mutation: inventoryAdjustQuantities (CURRENT — use this)
```graphql
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
```

Variables:
```json
{
  "input": {
    "reason": "correction",
    "name": "Odoo inventory sync",
    "changes": [
      {
        "delta": 10,
        "inventoryItemId": "gid://shopify/InventoryItem/123",
        "locationId": "gid://shopify/Location/456",
        "ledgerDocumentUri": "odoo://stock.quant/789"
      }
    ]
  }
}
```

### Mutation: inventorySetQuantities (Alternative — absolute values)
```graphql
mutation InventorySet($input: InventorySetQuantitiesInput!) {
  inventorySetQuantities(input: $input) {
    inventoryAdjustmentGroup {
      reason
    }
    userErrors {
      field
      message
    }
  }
}
```

**Note**: `inventorySetQuantities` sets absolute values. Safer for sync (no delta calculation needed) but requires knowing the exact quantity. `inventoryAdjustQuantities` applies delta changes.

### Location Query
```graphql
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
```

---

## 7. Webhook Specification

### Available Topics for Connector
| Topic | Priority | Trigger |
|-------|----------|---------|
| `products/create` | P0 | Product created in Shopify |
| `products/update` | P0 | Product modified in Shopify |
| `products/delete` | P1 | Product deleted in Shopify |
| `orders/create` | P0 | New order placed |
| `orders/updated` | P0 | Order status changed |
| `orders/cancelled` | P1 | Order cancelled |
| `customers/create` | P0 | New customer registered |
| `customers/update` | P0 | Customer info updated |
| `inventory_levels/update` | P1 | Inventory changed in Shopify |
| `fulfillments/create` | P1 | Fulfillment created |
| `refunds/create` | P1 | Refund issued |
| `app/uninstalled` | P0 | **Mandatory** — app removed |
| `shop/update` | P1 | Shop settings changed |

### Mandatory Compliance Webhooks (GDPR — Required for public apps)
| Topic | Purpose |
|-------|---------|
| `customers/data_request` | Customer requests their data |
| `customers/redact` | Customer requests data deletion |
| `shop/redact` | Merchant uninstalls, requests data deletion |

### Delivery & Retry Behavior
- Shopify expects HTTP 200 response within **5 seconds**
- If no 200 received: retries **19 times** over **48 hours** with exponential backoff
- After all retries fail: webhook is automatically removed
- Webhook payloads are **JSON** over HTTPS
- Headers include: `X-Shopify-Topic`, `X-Shopify-Hmac-Sha256`, `X-Shopify-Shop-Domain`, `X-Shopify-Webhook-Id`, `X-Shopify-Api-Version`

### HMAC Verification (Python)
```python
import hmac
import hashlib
import base64

def verify_shopify_hmac(raw_body: bytes, hmac_header: str, secret: str) -> bool:
    """Verify Shopify webhook HMAC-SHA256 signature."""
    if not secret or not hmac_header:
        return False
    computed = base64.b64encode(
        hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).digest()
    ).decode('utf-8')
    return hmac.compare_digest(computed, hmac_header)
```

### Webhook Registration via GraphQL
```graphql
mutation WebhookCreate($topic: WebhookSubscriptionTopic!, $url: URL!) {
  webhookSubscriptionCreate(
    topic: $topic,
    webhookSubscription: {
      callbackUrl: $url,
      format: JSON
    }
  ) {
    webhookSubscription {
      id
      topic
      endpoint {
        __typename
        ... on WebhookHttpEndpoint {
          callbackUrl
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

---

## 8. Bulk Operations API (2026-01+)

### Key Change in 2026-01
- **Up to 5 concurrent bulk queries** per shop (was 1)
- **Up to 5 concurrent bulk mutations** per shop (was 1)
- New `bulkOperations` query for listing/filtering operations

### Bulk Query (Export large datasets)
```graphql
mutation BulkExportProducts {
  bulkOperationRunQuery(
    query: """
    {
      products {
        edges {
          node {
            id
            title
            variants {
              edges {
                node {
                  id
                  sku
                  inventoryQuantity
                }
              }
            }
          }
        }
      }
    }
    """
  ) {
    bulkOperation {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
```

### Poll for Completion
```graphql
query BulkOperationStatus($id: ID!) {
  node(id: $id) {
    ... on BulkOperation {
      id
      status
      errorCode
      objectCount
      fileSize
      url           # JSONL download URL when COMPLETED
      createdAt
      completedAt
    }
  }
}
```

### When to Use Bulk Operations
| Scenario | Use Bulk? | Why |
|---------|-----------|-----|
| Initial product import (1000+) | Yes | Avoids rate limits, single JSONL download |
| Daily incremental sync (50 records) | No | Regular queries are faster |
| Full inventory reconciliation | Yes | Fetch all levels at once |
| Single webhook event | No | One query is sufficient |

---

## 9. Pagination Pattern

### Cursor-Based (Required for all list queries)
```python
def fetch_all_products(self, backend):
    """Generator that yields all products using cursor pagination."""
    cursor = None
    while True:
        variables = {'first': 50}
        if cursor:
            variables['after'] = cursor

        response = backend._call_shopify(PRODUCTS_QUERY, variables)
        products = response['data']['products']

        for edge in products['edges']:
            yield edge['node']

        if not products['pageInfo']['hasNextPage']:
            break
        cursor = products['pageInfo']['endCursor']
```

---

## 10. Error Handling Patterns

### userErrors (Validation failures — NOT exceptions)
```json
{
  "data": {
    "productCreate": {
      "product": null,
      "userErrors": [
        {
          "field": ["title"],
          "message": "Title can't be blank",
          "code": "BLANK"
        }
      ]
    }
  }
}
```

**Always check `userErrors` even when HTTP status is 200.** A 200 response with `userErrors` means the mutation was rejected.

### HTTP-Level Errors
| Code | Meaning | Retry? |
|------|---------|--------|
| 200 | Success (check userErrors!) | No |
| 401 | Invalid access token | No — fix credentials |
| 402 | Shop frozen (unpaid) | No |
| 403 | Insufficient scope | No — request scope |
| 404 | Resource not found | No |
| 423 | Shop locked | Wait and retry |
| 429 | Throttled | Yes — backoff |
| 500 | Internal error | Yes — backoff |
| 502 | Bad gateway | Yes — backoff |
| 503 | Service unavailable | Yes — backoff |

---

## 11. Key References

| Topic | URL |
|-------|-----|
| GraphQL Admin API Reference | https://shopify.dev/docs/api/admin-graphql/latest |
| API Versioning | https://shopify.dev/docs/api/usage/versioning |
| Rate Limits | https://shopify.dev/docs/api/usage/limits |
| Bulk Operations | https://shopify.dev/docs/api/usage/bulk-operations |
| Webhooks Guide | https://shopify.dev/docs/apps/build/webhooks/subscribe/https |
| HMAC Verification | https://shopify.dev/docs/apps/build/webhooks/subscribe/https#verify-hmac |
| Privacy/GDPR Webhooks | https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance |
| Product Object | https://shopify.dev/docs/api/admin-graphql/latest/objects/Product |
| Customer Object | https://shopify.dev/docs/api/admin-graphql/latest/objects/Customer |
| Order Object | https://shopify.dev/docs/api/admin-graphql/latest/objects/Order |
| InventoryLevel Object | https://shopify.dev/docs/api/admin-graphql/latest/objects/InventoryLevel |
| 2026-01 Release Notes | https://shopify.dev/docs/api/release-notes/2026-01 |
| Shopify Changelog | https://shopify.dev/changelog |
