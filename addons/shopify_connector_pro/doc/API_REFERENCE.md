# API Reference — Shopify Connector Pro

Programmatic reference for developers extending or integrating with the connector.

---

## Models

### shopify.backend

The central configuration model. One record per Shopify store.

| Field | Type | Description |
|---|---|---|
| `name` | Char | Display name |
| `shop_url` | Char | myshopify.com domain |
| `access_token` | Char | Shopify Admin API token (shpat_…) |
| `api_version` | Char | Shopify API version (default: 2026-01) |
| `webhook_secret` | Char | HMAC verification secret |
| `company_id` | Many2one(res.company) | Owning company |
| `warehouse_id` | Many2one(stock.warehouse) | Default warehouse |
| `pricelist_id` | Many2one(product.pricelist) | Export pricelist |
| `state` | Selection | draft / connected / error |
| `batch_size` | Integer | Records per API call (1–250) |

**Key methods:**

```python
backend.action_test_connection()      # Test API connection, update state
backend.action_register_webhooks()    # Register all webhook topics
backend.action_unregister_webhooks()  # Remove all webhooks
backend.action_import_locations()     # Import Shopify locations
backend.action_init_field_mappings()  # Create default field mappings
```

---

### shopify.binding (Abstract)

Base model inherited by all binding models. Provides sync infrastructure.

| Field | Type | Description |
|---|---|---|
| `backend_id` | Many2one(shopify.backend) | Parent store |
| `shopify_id` | Char | Shopify GID (e.g. `gid://shopify/Product/123`) |
| `sync_status` | Selection | pending / synced / error / permanent_error |
| `sync_checksum` | Char | SHA-256 of last synced state |
| `sync_error` | Text | Last error message |
| `last_sync_date` | Datetime | Last successful sync |

**Key methods:**

```python
binding._mark_synced(checksum='...')    # Set synced + update checksum
binding._mark_error(error='...')        # Set error + record message
binding._needs_sync(new_checksum)       # True if checksum differs
```

---

### shopify.product.binding

Links `product.template` ↔ Shopify Product.

```python
# Trigger sync for a backend
env['shopify.product.binding'].run_sync(backend)

# Process incoming webhook
env['shopify.product.binding'].process_webhook_event(backend, data, topic)
```

### shopify.variant.binding

Links `product.product` ↔ Shopify ProductVariant.

| Extra Fields | Type | Description |
|---|---|---|
| `product_binding_id` | Many2one | Parent product binding |
| `shopify_inventory_item_id` | Char | Inventory item GID |
| `shopify_sku` | Char | SKU on Shopify |

### shopify.customer.binding

Links `res.partner` ↔ Shopify Customer.

### shopify.order.binding

Links `sale.order` ↔ Shopify Order.

| Extra Fields | Type | Description |
|---|---|---|
| `shopify_order_name` | Char | Order number (#1001) |
| `shopify_financial_status` | Selection | pending/authorized/paid/… |
| `shopify_fulfillment_status` | Selection | unfulfilled/partial/fulfilled |
| `shopify_created_at` | Datetime | When created on Shopify |

### shopify.inventory.binding

Links variant + location for inventory tracking.

### shopify.collection.binding

Links Odoo product categories ↔ Shopify Collections.

### shopify.refund.binding

Links `account.move` (credit note) ↔ Shopify Refund.

### shopify.abandoned.cart

Imported abandoned checkouts (inherits `shopify.binding`).

```python
cart.action_create_quotation()   # Create draft sale.order from cart
cart.action_mark_recovered()     # Manually mark as recovered
```

---

## Sync Engine Classes

All sync classes follow the same pattern:

```python
from shopify_connector_pro.sync.product_sync import ProductSync

syncer = ProductSync(env, backend)
syncer.import_products()   # Import from Shopify
syncer.export_products()   # Export to Shopify
```

### Available Sync Classes

| Class | Module | Methods |
|---|---|---|
| `ProductSync` | `sync.product_sync` | `import_products()`, `export_products()`, `import_single_product(data)` |
| `CustomerSync` | `sync.customer_sync` | `import_customers()`, `export_customers()`, `import_single_customer(data)` |
| `OrderSync` | `sync.order_sync` | `import_orders()`, `export_orders()`, `import_single_order(data)` |
| `InventorySync` | `sync.inventory_sync` | `export_inventory(backend)` |
| `FulfillmentSync` | `sync.fulfillment_sync` | `push_fulfillment(picking)`, `handle_inbound_fulfillment(binding, data)` |
| `CollectionSync` | `sync.collection_sync` | `import_collections()` |
| `RefundSync` | `sync.refund_sync` | `import_refunds()` |
| `AbandonedCartSync` | `sync.abandoned_cart_sync` | `import_abandoned_carts()` |
| `DiscountSync` | `sync.discount_sync` | `export_discounts()` |
| `PayoutSync` | `sync.payout_sync` | `import_payouts()` |

---

## Shopify API Client

```python
from shopify_connector_pro.shopify_api.client import ShopifyClient

client = ShopifyClient(backend)

# Execute a GraphQL query
result = client.execute(query_string, variables={}, estimated_cost=10)

# Execute a mutation with error handling
result = client.execute_mutation(
    mutation_string,
    variables={'input': {...}},
    result_key='mutationName',
    estimated_cost=10,
)

# Fetch paginated data (handles cursor pagination automatically)
nodes = client.fetch_paginated(
    query_string,
    root_key='products',
    page_size=50,
    estimated_cost_per_page=15,
)

# Fetch shop info
shop_data = client.fetch_shop_info()
```

### Rate Limiter

The client includes an adaptive rate limiter that reads `extensions.cost` from every GraphQL response and pauses when approaching the throttle threshold. No configuration needed.

### Circuit Breaker

After 5 consecutive failures, the circuit breaker opens for 5 minutes, preventing further API calls. It auto-recovers with a half-open test call.

---

## Webhook Processing

Incoming webhooks are enqueued in `shopify.webhook.log` and processed by cron.

### Adding a Custom Webhook Handler

1. Add the topic to the handler map in `shopify_webhook_log.py`:

```python
handler_map = {
    ...
    'my_topic/event': '_handle_my_event',
}
```

2. Implement the handler method:

```python
def _handle_my_event(self, data):
    """Handle my custom event."""
    # data is the parsed JSON payload
    pass
```

---

## Field Mapping

Configure which fields sync and in which direction via `shopify.field.mapping`:

```python
env['shopify.field.mapping'].create({
    'backend_id': backend.id,
    'entity': 'product',          # product / customer / order
    'odoo_field': 'description_sale',
    'shopify_field': 'descriptionHtml',
    'direction': 'both',          # export / import / both
    'sequence': 10,
})
```

---

## Tax Mapping

Map Shopify tax names to Odoo taxes via `shopify.tax.mapping`:

```python
env['shopify.tax.mapping'].create({
    'backend_id': backend.id,
    'shopify_tax_name': 'VAT',
    'shopify_tax_rate': 20.0,
    'odoo_tax_id': vat_20_tax.id,
})
```

When importing orders, the connector:
1. Checks tax mappings by Shopify tax title (exact match).
2. Falls back to matching Odoo taxes by rate.
3. Applies matched taxes to order lines.

---

## Extending the Connector

### Adding a New Entity Sync

1. Create a binding model inheriting `shopify.binding`:

```python
class ShopifyMyBinding(models.Model):
    _name = 'shopify.my.binding'
    _inherit = 'shopify.binding'
    odoo_id = fields.Many2one('my.model', ondelete='cascade')
```

2. Create an importer inheriting `BaseImporter`:

```python
from .base_importer import BaseImporter

class MyImporter(BaseImporter):
    entity_name = 'my_entity'
    binding_model = 'shopify.my.binding'

    def _compute_shopify_checksum(self, node):
        return compute_checksum({...})

    def _import_one(self, node, existing_binding=None):
        # Your import logic
        pass
```

3. Add GraphQL queries in `shopify_api/queries/`.
4. Register in `__init__.py` files.
5. Add security rules to `ir.model.access.csv`.
6. Add cron job to `data/shopify_cron.xml`.

---

## Cron Entry Points

All crons are defined in `data/shopify_cron.xml` and call methods on `shopify.backend`:

| Method | What it does |
|---|---|
| `_cron_sync_products` | Product bidirectional sync |
| `_cron_import_orders` | Order import |
| `_cron_sync_inventory` | Inventory push |
| `_cron_sync_customers` | Customer bidirectional sync |
| `_cron_sync_collections` | Collection import |
| `_cron_import_refunds` | Refund import |
| `_cron_import_payouts` | Payout import |
| `_cron_import_abandoned_carts` | Abandoned cart import |
| `_cron_sync_discounts` | Discount code export |

Each method iterates over connected backends with the relevant flag enabled.
