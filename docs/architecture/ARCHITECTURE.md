# Adams Shopify Connector — System Architecture

## Status: Initial Draft
## Last Updated: 2026-03-26 by Technical Architect Agent

---

## Module Overview

| Attribute | Value |
|-----------|-------|
| Module name | adams_shopify |
| Odoo version | 18.0+ (19.0 compatible) |
| Shopify API | GraphQL Admin API 2024-10+ |
| License | LGPL-3 |
| Deployment | Odoo.sh |
| Dependencies | adams_base, product, sale_management, stock, contacts |

---

## Core Design Patterns

### 1. Binding Model Pattern
Every entity synced between Odoo and Shopify has a dedicated binding model that acts as the bridge.

```
┌─────────────────┐         ┌──────────────────────┐         ┌─────────────────┐
│ product.template │◄───────│ shopify.product.binding │───────►│ Shopify Product │
│   (Odoo record)  │  odoo_id│                        │shopify_id│  (External)     │
└─────────────────┘         └──────────────────────┘         └─────────────────┘
                                    │
                                    │ backend_id
                                    ▼
                            ┌──────────────────┐
                            │ shopify.backend   │
                            │ (Connection Config)│
                            └──────────────────┘
```

### 2. Abstract Binding Base
```python
class ShopifyBinding(models.AbstractModel):
    _name = 'shopify.binding'
    _description = 'Shopify Binding (Abstract)'

    backend_id = fields.Many2one('shopify.backend', required=True, ondelete='cascade')
    shopify_id = fields.Char('Shopify ID', index=True)
    sync_checksum = fields.Char('Sync Checksum')
    last_sync_date = fields.Datetime('Last Sync Date')
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('error', 'Error'),
        ('permanent_error', 'Permanent Error'),
    ], default='pending')
    sync_error = fields.Text('Last Sync Error')
```

### 3. Sync Engine Flow

```
EXPORT (Odoo → Shopify):
  Trigger → Collect Changed → Filter by Checksum → Transform → API Call → Update Binding

IMPORT (Shopify → Odoo):
  Webhook/Poll → Verify → Find Binding → Transform → Create/Update Odoo Record → Update Binding
```

### 4. Layer Separation

```
┌────────────────────────────────────────┐
│           Presentation Layer           │
│  (XML Views, Wizards, Menu Items)      │
├────────────────────────────────────────┤
│           Business Logic Layer         │
│  (Odoo Models, Sync Engine, Crons)     │
├────────────────────────────────────────┤
│          Integration Layer             │
│  (Transformers, GraphQL Client)        │
├────────────────────────────────────────┤
│           Transport Layer              │
│  (HTTP Client, Rate Limiter, Auth)     │
└────────────────────────────────────────┘
```

Rules:
- Presentation calls Business Logic only
- Business Logic calls Integration Layer only
- Integration Layer calls Transport Layer only
- NO layer may skip a layer

---

## Model Catalog

### Core Infrastructure Models

| Model | Type | Purpose |
|-------|------|---------|
| shopify.backend | Concrete | Connection configuration, sync triggers, global settings |
| shopify.binding | Abstract | Base fields/methods for all binding models |
| shopify.webhook.log | Concrete | Webhook event tracking and dedup |
| shopify.sync.log | Concrete | Sync operation audit trail |

### Binding Models

| Model | Links | Unique Constraint |
|-------|-------|------------------|
| shopify.product.binding | product.template ↔ Shopify Product | (backend_id, shopify_id) |
| shopify.variant.binding | product.product ↔ Shopify Variant | (backend_id, shopify_id) |
| shopify.customer.binding | res.partner ↔ Shopify Customer | (backend_id, shopify_id) |
| shopify.order.binding | sale.order ↔ Shopify Order | (backend_id, shopify_id) |
| shopify.inventory.binding | stock.quant ↔ Shopify InventoryLevel | (backend_id, shopify_id) |

### Extended Odoo Models

| Model | Extension |
|-------|-----------|
| product.template | Add shopify_bind_ids (One2many to binding), sync button |
| product.product | Add shopify_variant_bind_ids |
| res.partner | Add shopify_bind_ids, shopify_customer indicator |
| sale.order | Add shopify_bind_ids, shopify_order_name, shopify_financial_status |

---

## Security Model

### Groups
```xml
<record id="group_shopify_user" model="res.groups">
    <field name="name">Shopify / User</field>
    <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
</record>

<record id="group_shopify_manager" model="res.groups">
    <field name="name">Shopify / Manager</field>
    <field name="implied_ids" eval="[(4, ref('group_shopify_user'))]"/>
</record>
```

### Access Rights Summary
| Model | User | Manager | Admin |
|-------|------|---------|-------|
| shopify.backend | read | read,write | full |
| shopify.*.binding | read | read,write,create | full |
| shopify.sync.log | read | read | full |
| shopify.webhook.log | read | read | full |

---

## Webhook Architecture

```
Shopify → HTTPS POST → /shopify/webhook/<backend_id>
                              │
                     ┌────────▼────────┐
                     │ HMAC Verify     │──── FAIL → 401
                     └────────┬────────┘
                              │ PASS
                     ┌────────▼────────┐
                     │ Dedup Check     │──── DUPLICATE → 200 (skip)
                     │ (webhook_id)    │
                     └────────┬────────┘
                              │ NEW
                     ┌────────▼────────┐
                     │ Log + Enqueue   │──── Return 200 immediately
                     └────────┬────────┘
                              │ (async)
                     ┌────────▼────────┐
                     │ Process Event   │──── Transform + Import
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │ Update Log      │──── Mark done/error
                     └─────────────────┘
```

---

## Rate Limiting Strategy

Shopify GraphQL uses cost-based throttling:
- Bucket size: 2,000 points (Shopify Plus: 4,000)
- Restore rate: 100 points/second
- Each query has a `requestedQueryCost`

```python
class RateLimiter:
    def __init__(self, bucket_size=2000, restore_rate=100):
        self.available = bucket_size
        self.last_update = time.time()

    def wait_if_needed(self, estimated_cost):
        now = time.time()
        elapsed = now - self.last_update
        self.available = min(
            self.available + elapsed * self.restore_rate,
            self.bucket_size
        )
        self.last_update = now

        if self.available < estimated_cost:
            wait_time = (estimated_cost - self.available) / self.restore_rate
            time.sleep(wait_time + 0.1)  # Small buffer

    def update_from_response(self, extensions):
        throttle = extensions.get('cost', {}).get('throttleStatus', {})
        if throttle:
            self.available = throttle.get('currentlyAvailable', self.available)
```

---

## Configuration Model

```python
class ShopifyBackend(models.Model):
    _name = 'shopify.backend'

    # Connection
    name = fields.Char(required=True)
    shop_url = fields.Char(required=True, help="mystore.myshopify.com")
    access_token = fields.Char(required=True, groups="base.group_system")
    api_version = fields.Char(default='2024-10')
    webhook_secret = fields.Char(groups="base.group_system")

    # Sync Settings
    auto_sync_products = fields.Boolean(default=True)
    auto_sync_customers = fields.Boolean(default=True)
    auto_sync_orders = fields.Boolean(default=True)
    auto_sync_inventory = fields.Boolean(default=True)
    sync_direction = fields.Selection([
        ('export', 'Odoo → Shopify'),
        ('import', 'Shopify → Odoo'),
        ('both', 'Bidirectional'),
    ], default='both')
    product_sync_interval = fields.Integer(default=15, help="Minutes")
    batch_size = fields.Integer(default=50)

    # Status
    state = fields.Selection([
        ('draft', 'Not Connected'),
        ('connected', 'Connected'),
        ('error', 'Connection Error'),
    ], default='draft')
    last_sync_date = fields.Datetime()
    company_id = fields.Many2one('res.company', required=True,
        default=lambda self: self.env.company)
```
