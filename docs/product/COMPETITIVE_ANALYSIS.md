# Competitive Analysis & Feature Scope

## Market Landscape (2025-2026)

### Key Competitors

| Vendor | Module | Platform | Price Model | Rating | Odoo 19 |
|--------|--------|----------|-------------|--------|---------|
| **Emipro** | shopify_ept | apps.odoo.com | One-time (~€300-500) | 3.5/5 | Yes |
| **VentorTech** | integration_shopify | apps.odoo.com + ecosystem | Subscription / One-time | 4.2/5 | Yes |
| **Pragtech** | pragtech_odoo_shopify_connector_advanced | apps.odoo.com | One-time | 4.0/5 | v19 available |
| **TechMarbles** | Odoo Integration | Shopify App Store | $35/mo subscription | 4.8/5 | Yes |
| **OdooSyncO** (Techspawn) | synco-odoo-connector | Shopify App Store | Subscription | 4.7/5 | Yes |
| **Webkul** | shopify-openerp-connector | Shopify App Store | Subscription | 3.2/5 | Yes |
| **Setu Consulting** | setu_shopify_connector | apps.odoo.com | One-time | 3.8/5 | v18 |
| **Heliconia** | hspl_shopify | apps.odoo.com | One-time | New | v19 |

### Customer Pain Points from Reviews (Competitive Weakness = Our Opportunity)

| Pain Point | Frequency | Competitor | Our Strategy |
|-----------|-----------|-----------|-------------|
| **Duplicate records** (customers, products) | Very Common | Emipro, Webkul | Binding model with DB unique constraints + checksum dedup |
| **Orders missing or incomplete** | Common | Emipro | Webhook + polling reconciliation, never skip orders |
| **Poor error visibility** | Common | Most | Dedicated sync dashboard with per-record status, one-click retry |
| **Manual daily checking required** | Common | Emipro, Webkul | Self-healing sync with automated reconciliation cron |
| **Support quality** (slow, blame customer) | Very Common | Emipro, Webkul | Excellent docs + self-service diagnostics built into UI |
| **Performance issues at scale** | Common | Webkul | Batched processing, cursor pagination, rate limit awareness |
| **Variant price sync requires extra module** | Specific | Webkul | Native variant-level price sync from day one |
| **Version upgrade = re-purchase** | Common | Most Odoo Apps | Plan for v19+v20 compat from start, offer upgrade path |
| **No real-time sync** (only cron-based) | Common | Older connectors | Webhook-first for critical events, cron for reconciliation |
| **Multi-store limitations** | Occasional | Some | Multi-backend by design from day one |

---

## Feature Matrix: Adams Shopify Connector

### Priority Legend
- **P0** = Launch blocker (MVP must-have)
- **P1** = Important for market competitiveness (v1.1)
- **P2** = Differentiator (v1.2+)
- **P3** = Nice-to-have / Future

---

### A. Connection & Configuration

| Feature | Priority | Notes |
|---------|----------|-------|
| Shopify store connection (access token) | P0 | GraphQL Admin API auth |
| Connection test with diagnostics | P0 | Show API version, plan type, rate limits |
| Multiple Shopify stores per Odoo instance | P0 | One `shopify.backend` per store |
| Multi-company support | P0 | Backend scoped to company_id |
| Per-entity sync enable/disable | P0 | Toggle products, orders, customers, inventory independently |
| Sync direction per entity (→, ←, ↔) | P0 | Configuration on backend |
| Sync frequency configuration | P0 | Per-entity cron interval setting |
| Webhook auto-registration | P1 | Register webhooks on Shopify from Odoo |
| API version selection | P1 | Default to latest stable, allow override |
| Shopify plan detection | P2 | Adjust rate limiting based on plan |

### B. Product Sync

| Feature | Priority | Notes |
|---------|----------|-------|
| Export products Odoo → Shopify | P0 | product.template → Shopify Product |
| Import products Shopify → Odoo | P0 | Shopify Product → product.template |
| Variant sync (product.product ↔ Variant) | P0 | Full variant lifecycle |
| Product images sync (bidirectional) | P0 | image_1920 ↔ Shopify media |
| Product status mapping (active ↔ ACTIVE/DRAFT) | P0 | |
| SKU mapping (default_code ↔ sku) | P0 | |
| Barcode sync | P0 | |
| Weight sync (with unit conversion) | P0 | kg ↔ Shopify weight_unit |
| Price sync (lst_price ↔ price) | P0 | |
| Pricelist-based export pricing | P1 | Use specific Odoo pricelist for Shopify prices |
| Compare-at price (strikethrough) | P1 | Odoo list price → compareAtPrice |
| Product tags sync | P1 | |
| Product type / category mapping | P1 | categ_id ↔ productType |
| Product description (HTML) sync | P0 | description_sale ↔ bodyHtml |
| SEO fields sync (meta title, description, URL handle) | P1 | |
| Custom fields / metafields sync | P2 | Odoo custom fields ↔ Shopify metafields |
| Product collections / categories mapping | P1 | Odoo categories ↔ Shopify collections |
| Exclude specific products from sync | P1 | Per-product "do not sync" flag |
| Auto-export on product change in Odoo | P1 | Real-time via write override |
| Bulk initial import wizard | P0 | First-time import all products |
| Product archiving / deletion sync | P1 | Archive in Odoo ↔ Draft in Shopify |
| Product template attributes ↔ Shopify options | P0 | Color, Size, etc. |
| `productSet` mutation support (upsert) | P1 | Single-call create-or-update |

### C. Customer Sync

| Feature | Priority | Notes |
|---------|----------|-------|
| Import customers Shopify → Odoo | P0 | Shopify Customer → res.partner |
| Export customers Odoo → Shopify | P1 | Less common direction |
| Name split/join (firstName + lastName ↔ name) | P0 | |
| Email + phone sync | P0 | |
| Address sync (default + additional) | P0 | Billing + shipping addresses |
| Customer tags sync | P1 | |
| Duplicate detection by email | P0 | Don't create duplicate res.partner |
| Customer group / segment mapping | P2 | |
| Marketing consent sync | P2 | email_marketing_consent |
| Customer metafields | P2 | |
| Tax exemption sync | P2 | |
| Bulk initial import wizard | P0 | |

### D. Order Sync

| Feature | Priority | Notes |
|---------|----------|-------|
| Import orders Shopify → Odoo | P0 | Shopify Order → sale.order |
| Order line items with products | P0 | Map via variant bindings |
| Order line discounts | P0 | discountAllocations → discount field |
| Shipping line as Odoo delivery product | P0 | |
| Tax mapping (Shopify tax → Odoo fiscal position) | P0 | |
| Payment status tracking | P0 | financial_status on sale.order |
| Order status mapping | P0 | Shopify status → Odoo workflow state |
| Automatic invoice creation | P1 | On paid orders |
| Automatic payment registration | P1 | Match Shopify payment to Odoo journal |
| Order notes / customer notes | P1 | |
| Order tags import | P1 | |
| Discount codes import | P1 | Map to Odoo promo codes or as line discount |
| Shipping method mapping | P1 | Shopify shipping → Odoo carrier |
| Gift card orders handling | P2 | |
| Refund sync (Shopify → Odoo credit note) | P1 | |
| Partial refund support | P2 | |
| Order cancellation sync | P1 | |
| Historical order import | P0 | Import existing orders on setup |
| Multi-currency orders | P1 | presentmentMoney handling |
| Order risk level import | P2 | |
| Draft orders import | P2 | |
| POS order import | P2 | Shopify POS |

### E. Inventory Sync

| Feature | Priority | Notes |
|---------|----------|-------|
| Export inventory Odoo → Shopify | P0 | stock levels push |
| Location mapping (Odoo warehouse → Shopify location) | P0 | |
| Quantity type selection (free qty, on-hand, forecasted) | P1 | |
| Multi-warehouse support | P1 | |
| Real-time inventory push on stock move | P1 | Triggered by stock.picking validation |
| Scheduled inventory reconciliation | P0 | Cron-based full sync |
| Inventory import Shopify → Odoo | P2 | Less common |
| Safety stock / buffer configuration | P2 | |
| Inventory threshold alerts | P2 | |

### F. Fulfillment Sync

| Feature | Priority | Notes |
|---------|----------|-------|
| Push fulfillment Odoo → Shopify | P0 | When delivery order validated |
| Tracking number sync | P0 | carrier_tracking_ref → tracking |
| Carrier mapping (Odoo → Shopify) | P1 | |
| Partial fulfillment support | P1 | |
| Fulfillment notification to customer | P0 | Trigger Shopify email on fulfill |

### G. Webhook Handling

| Feature | Priority | Notes |
|---------|----------|-------|
| Webhook receiver with HMAC verification | P0 | |
| products/create, products/update | P0 | |
| orders/create, orders/updated | P0 | |
| customers/create, customers/update | P0 | |
| inventory_levels/update | P1 | |
| fulfillments/create, fulfillments/update | P1 | |
| refunds/create | P1 | |
| orders/cancelled | P1 | |
| Webhook auto-registration from Odoo | P1 | |
| Webhook health monitoring | P2 | |
| GDPR compliance webhooks | P0 | Mandatory for public Shopify apps |
| app/uninstalled webhook | P0 | Mandatory |

### H. Dashboard & UX

| Feature | Priority | Notes |
|---------|----------|-------|
| Sync overview dashboard | P0 | Per-entity counts: synced, pending, error |
| Sync log viewer with filtering | P0 | Date, entity, status, backend |
| Per-record sync status on forms | P0 | "Shopify" tab on product/customer/order forms |
| One-click retry for failed records | P0 | Button on error records |
| Bulk retry wizard | P1 | Retry all failed records of a type |
| Manual sync trigger buttons | P0 | "Sync Now" per entity |
| Error notification (Odoo discuss/email) | P1 | Alert on critical sync failures |
| Sync progress indicator | P1 | During bulk operations |
| Connection status indicator on backend | P0 | Green/red/yellow status |
| Import wizard with preview | P1 | Show what will be imported before executing |
| Sync conflict resolution UI | P2 | When both sides changed |
| Activity / chatter on sync records | P1 | Odoo activity tracking on bindings |

### I. Technical & Reliability

| Feature | Priority | Notes |
|---------|----------|-------|
| Idempotent operations (all entities) | P0 | Critical — our #1 differentiator |
| Exponential backoff with jitter | P0 | Rate limit handling |
| Per-record error isolation in batches | P0 | One failure doesn't stop the batch |
| Checksum-based change detection | P0 | Skip unchanged records |
| Database unique constraints on bindings | P0 | Race condition prevention |
| Webhook deduplication | P0 | By webhook event ID |
| Automatic retry for transient errors | P0 | 429, 500, 502, 503, timeouts |
| Circuit breaker for sustained failures | P1 | Don't hammer a dead API |
| Scheduled reconciliation (catch missed webhooks) | P0 | Cron-based safety net |
| Structured logging with correlation IDs | P1 | For debugging |
| Cursor-based pagination (no offset) | P0 | Shopify GraphQL requirement |

---

## Competitive Positioning Strategy

### Our Differentiators vs Market

1. **Reliability First**: Binding model + DB constraints + checksums = zero duplicates. This is the #1 customer pain point and we solve it architecturally, not with workarounds.

2. **Self-Healing Sync**: Webhook-first for speed + scheduled reconciliation as safety net. No "check manually every day."

3. **Transparent Error Handling**: Every record has visible sync status. One-click retry. No black-box sync logs.

4. **Modern API**: GraphQL Admin API (not deprecated REST). Bulk operations for initial import. Ready for Shopify API evolution.

5. **Multi-Store Native**: Not bolted on. Multiple backends from day one.

6. **Built for Odoo.sh**: Optimized for Odoo.sh worker limits, cron constraints, and deployment patterns.

7. **Odoo v19 Native**: Built on v19 ORM improvements (30-40% faster), not ported from older versions.

---

## Release Roadmap

### v1.0.0 (MVP) — All P0 Features
- Product sync (bidirectional)
- Customer sync (import-first, export available)
- Order import with line items, taxes, discounts, shipping
- Inventory export
- Fulfillment push
- Webhook handling
- Sync dashboard and per-record status
- Idempotent operations throughout
- Multi-store, multi-company

### v1.1.0 — P1 Features
- Pricelist-based pricing, SEO fields, product collections
- Refund sync, automatic invoicing/payment
- Shipping method and carrier mapping
- Multi-currency, customer tags
- Circuit breaker, import wizard with preview
- Webhook auto-registration

### v1.2.0 — P2 Features (Differentiators)
- Metafields sync (products + customers)
- Gift card handling, draft orders
- Customer segments, marketing consent
- Sync conflict resolution UI
- Shopify plan detection + adaptive rate limiting

### v2.0.0 — Future
- Shopify B2B / wholesale support
- Shopify Markets (international pricing)
- Shopify POS integration
- Shopify Flow triggers from Odoo events
- AI-powered field mapping suggestions
