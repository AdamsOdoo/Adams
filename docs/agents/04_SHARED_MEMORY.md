# Shared Memory / Context Structure

## Overview

The shared memory system is a structured set of files that serves as the single source of truth for all agents. The Orchestrator manages writes; agents read from shared memory and produce outputs that the Orchestrator integrates.

## File Structure

```
docs/
├── agents/
│   ├── 00_SYSTEM_OVERVIEW.md          # This multi-agent system design
│   ├── 01_AGENT_DEFINITIONS.md        # All agent roles and contracts
│   ├── 02_PROMPT_TEMPLATES.md         # Ready-to-use prompts
│   ├── 03_ORCHESTRATION_WORKFLOW.md   # Workflow and validation gates
│   ├── 04_SHARED_MEMORY.md            # This file
│   ├── 05_FOLDER_STRUCTURE.md         # Module folder layout
│   ├── 06_QUALITY_CONTROL.md          # Quality standards and enforcement
│   └── 07_FAILURE_SCENARIOS.md        # Common failures and prevention
│
├── architecture/
│   ├── ARCHITECTURE.md                # System architecture (Technical Architect owns)
│   ├── API_MAPPING.md                 # Field-level Odoo ↔ Shopify mapping
│   ├── DECISIONS.md                   # Numbered decision log
│   ├── SYNC_ENGINE.md                 # Sync engine design details
│   └── SECURITY_MODEL.md             # Access rights and security design
│
├── specs/
│   ├── SPEC-001_product_sync.md       # Product sync functional spec
│   ├── SPEC-002_customer_sync.md      # Customer sync functional spec
│   ├── SPEC-003_order_sync.md         # Order sync functional spec
│   ├── SPEC-004_inventory_sync.md     # Inventory sync functional spec
│   └── SPEC-005_webhook_handling.md   # Webhook handling functional spec
│
├── tracking/
│   ├── TASKS.md                       # Task tracking with status
│   ├── ERRORS.md                      # Error log with root causes
│   └── CHANGELOG.md                   # Version-level change history
│
└── reviews/
    ├── REV-001_initial_models.md      # Code review records
    └── ...
```

---

## File Templates

### docs/architecture/ARCHITECTURE.md

```markdown
# Adams Shopify Connector — System Architecture

## Last Updated
{{date}} by {{agent}}

## Module Overview
- Module name: adams_shopify
- Odoo version: 18.0+
- Shopify API version: 2024-10

## Model Hierarchy

### Core Models
| Model | Purpose | Key Fields |
|-------|---------|-----------|
| shopify.backend | Connection config | shop_url, access_token, api_version |
| shopify.product.binding | Product link | backend_id, odoo_id, shopify_id, sync_checksum |
| shopify.variant.binding | Variant link | backend_id, odoo_id, shopify_id |
| shopify.customer.binding | Customer link | backend_id, odoo_id, shopify_id |
| shopify.order.binding | Order link | backend_id, odoo_id, shopify_id |
| shopify.inventory.binding | Inventory link | backend_id, odoo_id, shopify_id |

### Model Relationships
```
shopify.backend (1) ──── (N) shopify.product.binding
shopify.product.binding (1) ──── (1) product.template
shopify.product.binding (1) ──── (N) shopify.variant.binding
shopify.variant.binding (1) ──── (1) product.product
shopify.backend (1) ──── (N) shopify.customer.binding
shopify.customer.binding (1) ──── (1) res.partner
shopify.backend (1) ──── (N) shopify.order.binding
shopify.order.binding (1) ──── (1) sale.order
```

## Sync Engine Architecture

### Flow: Odoo → Shopify Export
```
1. Trigger (cron/manual/record write)
2. Collect changed records (write_date > last_sync_date)
3. For each record:
   a. Find or create binding
   b. Compute checksum of syncable fields
   c. If checksum unchanged → skip
   d. Transform Odoo record → Shopify input
   e. Call Shopify API (create or update based on binding.shopify_id)
   f. Store Shopify response ID in binding
   g. Update sync_checksum and last_sync_date
   h. Log success/failure
4. Update backend.last_export_date
```

### Flow: Shopify → Odoo Import
```
1. Trigger (webhook/cron poll)
2. Receive Shopify data (webhook payload or API response)
3. For each Shopify record:
   a. Find existing binding by shopify_id
   b. If no binding → create Odoo record + binding
   c. If binding exists → compare updated_at timestamps
   d. Transform Shopify data → Odoo values
   e. Write to Odoo record
   f. Update binding.last_sync_date
   g. Log success/failure
```

## Directory Structure
See docs/agents/05_FOLDER_STRUCTURE.md
```

---

### docs/architecture/API_MAPPING.md

```markdown
# Odoo ↔ Shopify Field Mapping

## Products

### product.template ↔ Shopify Product
| Odoo Field | Shopify Field | Direction | Transform | Notes |
|-----------|--------------|-----------|-----------|-------|
| name | title | bidirectional | none | |
| description_sale | bodyHtml | bidirectional | text→html | Sanitize HTML on import |
| default_code | - | - | - | Mapped at variant level |
| categ_id.name | productType | odoo→shopify | category path | First-level only |
| tag_ids.name | tags | bidirectional | comma-separated | |
| active | status | bidirectional | bool→ACTIVE/DRAFT | |
| image_1920 | images[0].src | bidirectional | base64↔URL | Download on import |
| website_published | publishedAt | odoo→shopify | bool→datetime/null | |

### product.product ↔ Shopify ProductVariant
| Odoo Field | Shopify Field | Direction | Transform | Notes |
|-----------|--------------|-----------|-----------|-------|
| default_code | sku | bidirectional | none | |
| lst_price | price | bidirectional | float→string | |
| barcode | barcode | bidirectional | none | |
| weight | weight | bidirectional | convert units | kg→g or respect Shopify weight_unit |
| qty_available | inventoryQuantity | odoo→shopify | via InventoryLevel | Not direct field |

## Customers

### res.partner ↔ Shopify Customer
| Odoo Field | Shopify Field | Direction | Transform | Notes |
|-----------|--------------|-----------|-----------|-------|
| name | firstName + lastName | bidirectional | split/join | Split on first space |
| email | email | bidirectional | none | Used for duplicate detection |
| phone | phone | bidirectional | none | |
| street | addresses[].address1 | bidirectional | none | Default address |
| street2 | addresses[].address2 | bidirectional | none | |
| city | addresses[].city | bidirectional | none | |
| state_id | addresses[].province | bidirectional | code→name | Lookup state by code |
| zip | addresses[].zip | bidirectional | none | |
| country_id | addresses[].countryCode | bidirectional | code lookup | ISO alpha-2 |
| customer_rank | - | - | - | Set ≥1 on import |
| category_id | tags | bidirectional | tag name | |

## Orders

### sale.order ↔ Shopify Order
| Odoo Field | Shopify Field | Direction | Transform | Notes |
|-----------|--------------|-----------|-----------|-------|
| name | name | shopify→odoo | #1001→SO format | Prefix with shop code |
| partner_id | customer.id | shopify→odoo | binding lookup | Via customer binding |
| date_order | createdAt | shopify→odoo | ISO→datetime | |
| order_line | lineItems | shopify→odoo | complex | See line mapping below |
| amount_total | totalPriceSet.shopMoney | shopify→odoo | verify only | Use as verification |
| state | displayFulfillmentStatus | shopify→odoo | map states | See state mapping |

### sale.order.line ↔ Shopify LineItem
| Odoo Field | Shopify Field | Direction | Transform | Notes |
|-----------|--------------|-----------|-----------|-------|
| product_id | variant.id | shopify→odoo | binding lookup | Via variant binding |
| product_uom_qty | quantity | shopify→odoo | int→float | |
| price_unit | originalUnitPriceSet.shopMoney | shopify→odoo | string→float | |
| discount | discountAllocations | shopify→odoo | calculate % | Sum allocations |

## Inventory

### stock.quant ↔ Shopify InventoryLevel
| Odoo Field | Shopify Field | Direction | Transform | Notes |
|-----------|--------------|-----------|-----------|-------|
| quantity | available | odoo→shopify | compute available | qty - reserved |
| location_id | locationId | odoo→shopify | config mapping | Map Odoo warehouse → Shopify location |
| product_id | inventoryItemId | odoo→shopify | via variant binding | |
```

---

### docs/architecture/DECISIONS.md

```markdown
# Architecture Decisions Log

| ID | Date | Decision | Rationale | Made By | Status |
|----|------|----------|-----------|---------|--------|
| DEC-001 | {{date}} | Use binding model pattern for all synced entities | Industry standard for Odoo connectors, supports idempotency, allows tracking sync state per record | Technical Architect | Active |
| DEC-002 | {{date}} | Use GraphQL Admin API (not REST) | Better performance (request only needed fields), supports bulk operations, is Shopify's recommended API | Technical Architect | Active |
| DEC-003 | {{date}} | Use checksum-based change detection | Prevents unnecessary API calls, reduces rate limit consumption, makes sync truly idempotent | Technical Architect | Active |
| DEC-004 | {{date}} | Process webhooks async via cron/queue | Webhook handlers must return 200 within 5s, complex processing must be deferred | Technical Architect | Active |
| DEC-005 | {{date}} | Use HMAC-SHA256 for webhook verification | Shopify standard, prevents forged webhook attacks | Technical Architect | Active |
| DEC-006 | {{date}} | Orders are import-only (Shopify→Odoo) for MVP | Bidirectional order sync is complex (fulfillment states), MVP focuses on order capture | Solution Architect | Active |
| DEC-007 | {{date}} | Use exponential backoff for rate limit handling | Shopify uses leaky bucket (2 calls/s), exponential backoff is the recommended retry strategy | Technical Architect | Active |
```

---

### docs/tracking/TASKS.md

```markdown
# Task Tracking

## Status Legend
- ⬜ TODO
- 🔄 IN PROGRESS
- 🔍 IN REVIEW
- ✅ DONE
- ❌ BLOCKED
- 🐛 BUG

## Phase 1: Requirements & Architecture

| Task ID | Description | Assigned To | Status | Depends On | Notes |
|---------|-------------|-------------|--------|------------|-------|
| TASK-001 | Product sync functional spec | Solution Architect | ⬜ | - | |
| TASK-002 | Customer sync functional spec | Solution Architect | ⬜ | - | |
| TASK-003 | Order sync functional spec | Solution Architect | ⬜ | - | |
| TASK-004 | Inventory sync functional spec | Solution Architect | ⬜ | - | |
| TASK-005 | Technical architecture design | Technical Architect | ⬜ | TASK-001..004 | |
| TASK-006 | Sync engine design | Technical Architect | ⬜ | TASK-005 | |

## Phase 2: Core Implementation

| Task ID | Description | Assigned To | Status | Depends On | Notes |
|---------|-------------|-------------|--------|------------|-------|
| TASK-010 | shopify.backend model | Odoo Developer | ⬜ | TASK-005 | |
| TASK-011 | GraphQL client + auth | Shopify Agent | ⬜ | TASK-005 | |
| TASK-012 | Binding model base | Odoo Developer | ⬜ | TASK-005 | |
| TASK-013 | Webhook controller | Shopify Agent | ⬜ | TASK-005 | |
| TASK-014 | Product sync implementation | Both | ⬜ | TASK-010..013 | |
| TASK-015 | Customer sync implementation | Both | ⬜ | TASK-010..013 | |
| TASK-016 | Order sync implementation | Both | ⬜ | TASK-010..013 | |
| TASK-017 | Inventory sync implementation | Both | ⬜ | TASK-010..013 | |

## Phase 3: Quality & Packaging

| Task ID | Description | Assigned To | Status | Depends On | Notes |
|---------|-------------|-------------|--------|------------|-------|
| TASK-020 | Code review — all modules | Code Reviewer | ⬜ | TASK-014..017 | |
| TASK-021 | Unit + integration tests | Testing Agent | ⬜ | TASK-020 | |
| TASK-022 | Bug fixes from testing | Debugging Agent | ⬜ | TASK-021 | |
| TASK-023 | Module packaging | DevOps Agent | ⬜ | TASK-022 | |
| TASK-024 | Final regression tests | Testing Agent | ⬜ | TASK-023 | |
```

---

### docs/tracking/ERRORS.md

```markdown
# Error Log

| Bug ID | Date | Description | Root Cause | Fix | Regression Test | Status |
|--------|------|-------------|-----------|-----|----------------|--------|
| BUG-001 | {{date}} | Example: Duplicate products created on webhook + cron overlap | Race condition: no DB unique constraint on (backend_id, shopify_id) | Added _sql_constraints + IntegrityError catch with retry | test_concurrent_product_create | ✅ Fixed |
```

---

### docs/tracking/CHANGELOG.md

```markdown
# Changelog

## [18.0.1.0.0] - {{date}}
### Added
- Initial release
- Shopify backend configuration with connection test
- Product sync (bidirectional)
- Customer sync (bidirectional)
- Order import (Shopify → Odoo)
- Inventory sync (Odoo → Shopify)
- Webhook handling with HMAC verification
- Scheduled sync via cron jobs
- Manual sync wizards
```
