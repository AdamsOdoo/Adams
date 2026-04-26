# Shopify Connector Pro for Odoo 19

### Seamless, Real-Time Integration Between Your Odoo ERP and Shopify Store

---

## Executive Summary

The **Shopify Connector Pro** is a purpose-built, enterprise-grade integration that connects your Odoo 19 ERP system with one or more Shopify stores. It eliminates manual data entry, keeps your inventory accurate across all channels, and gives your team a single source of truth for products, orders, customers, finances, and fulfillment.

Unlike off-the-shelf connectors that bolt onto Odoo with limited features and outdated technology, the Shopify Connector Pro was designed from the ground up using **Shopify's latest GraphQL Admin API (2026-01)** — the only API Shopify actively supports and develops going forward. This means your integration is future-proof, faster, and more reliable than competitors still relying on Shopify's deprecated REST API.

Whether you operate a single Shopify storefront or manage multiple stores across different companies, this connector handles the complexity so your team can focus on growing the business.

---

## Who Is This For?

- **Retail and e-commerce businesses** running Shopify as their online storefront and Odoo as their back-office ERP
- **Multi-store operators** managing several Shopify stores from a centralized Odoo instance
- **Multi-company organizations** that need strict data isolation between legal entities while sharing a single Odoo platform
- **Wholesale + DTC businesses** that sell both B2B (directly in Odoo) and direct-to-consumer (via Shopify), and need both channels to coexist without interference
- **Growing brands** that need a connector that scales with them — from hundreds to tens of thousands of products and orders

---

## Complete Feature Overview

### 1. Product Synchronization

Keep your product catalog perfectly aligned between Odoo and Shopify — automatically.

- **Bidirectional sync**: Create or update products in either system; changes flow automatically to the other
- **Full product data**: Names, descriptions, prices, images, variants, SKUs, barcodes, weights, and more
- **Multiple images per product**: All product photos are synchronized in both directions
- **Pricelist-based pricing**: Use Odoo pricelists to control what prices appear on your Shopify store
- **Variant support**: Full support for products with multiple options (size, color, material, etc.)
- **Smart change detection**: Only products that have actually changed are synced — saving time and API resources
- **Automatic sync every 15 minutes**, or trigger manually at any time
- **Bulk export wizard**: Push your entire Odoo catalog to Shopify in one click, with filters for unlinked or recently modified products
- **Auto-export on save**: Optionally push changes to Shopify the moment a product is saved in Odoo

### 2. Order Management

Every Shopify order flows into Odoo automatically — complete with customer details, line items, taxes, discounts, shipping, and payment information.

- **Automatic import every 5 minutes** — near real-time order capture
- **Complete order data**: Customer info, shipping/billing addresses, line items, quantities, prices, taxes, discounts, and shipping charges
- **Automatic invoicing**: Paid orders can automatically generate and validate invoices in Odoo
- **Payment registration**: Payments are matched to the correct journal based on the Shopify payment gateway used
- **Tax mapping**: Shopify tax lines are mapped to your Odoo tax configuration using flexible mapping rules
- **Discount preservation**: All order-level and line-level discounts are captured accurately
- **Multi-currency support**: Orders in foreign currencies are handled with configurable currency settings
- **Gift card handling**: Gift card payments are properly recorded as separate payment lines
- **Order cancellation sync**: Cancellations in Shopify are reflected in Odoo

### 3. Inventory Management

Keep stock levels accurate across all your sales channels — automatically and in near real-time.

- **Automatic inventory push every 10 minutes** from Odoo to Shopify
- **Multi-location support**: Map each Shopify location to a specific Odoo warehouse; stock levels are pushed independently per location
- **Smart delta sync**: Only products whose stock levels have actually changed are updated — no wasted API calls
- **Flexible quantity modes**: Choose between "available" quantity (free stock after allocations) or "on-hand" quantity (total physical stock)
- **Automatic stock updates on shipment**: When a delivery is validated in Odoo, inventory levels on Shopify update automatically
- **One-click location import**: Pull all your Shopify locations into Odoo with a single button

### 4. Customer Synchronization

Maintain a unified customer database across Odoo and Shopify.

- **Bidirectional sync**: Customers created or updated in either system are reflected in the other
- **Intelligent deduplication**: Configurable matching by email, phone, or both — prevents duplicate customer records
- **Full contact data**: Names, email addresses, phone numbers, and multiple shipping/billing addresses
- **Customer tags**: Shopify customer tags are imported as Odoo partner categories for segmentation
- **Guest order handling**: Even guest checkout customers are captured and deduplicated properly
- **Bulk export**: Push your Odoo customer database to Shopify in bulk
- **Automatic sync every 15 minutes**

### 5. Fulfillment and Shipping

Seamlessly connect your warehouse operations with your Shopify storefront.

- **Automatic fulfillment push**: When a delivery order is validated in Odoo, the corresponding Shopify order is automatically marked as fulfilled — with tracking number and carrier information
- **Partial shipment support**: Ship part of an order from Odoo; only the shipped items are marked as fulfilled on Shopify
- **Line-level SKU matching**: Each delivery line is matched to the correct Shopify line item by SKU
- **Inbound fulfillment handling**: When fulfillments happen outside Odoo (e.g., dropshipping or 3PL), choose how Odoo responds:
  - Create an activity for manual review (default — safest option)
  - Automatically validate the corresponding delivery in Odoo
  - Ignore and track status only

### 6. Refund and Credit Note Processing

Handle returns and refunds without manual intervention.

- **Automatic refund import every 30 minutes**
- **Credit note creation**: Shopify refunds automatically generate credit notes in Odoo
- **Partial refund support**: Refunds for specific items or amounts are accurately reflected at the line level
- **Full refund support**: Complete order refunds create standard reversal credit notes
- **Deduplication**: The same refund is never imported twice

### 7. Financial Integration

Complete financial visibility across your Shopify and Odoo operations.

- **Tax mapping**: Define rules to map Shopify tax names and rates to Odoo taxes and fiscal positions
- **Payment journal mapping**: Route payments from different Shopify gateways (credit card, PayPal, Shop Pay, etc.) to the correct Odoo journals
- **Payout tracking**: Shopify Payments payouts are imported every 6 hours with full transaction-level detail — including charges, refunds, fees, adjustments, and disputes
- **Reverse payment sync**: When you mark an invoice as paid in Odoo, the corresponding Shopify order is automatically updated
- **Gift card tracking**: Shopify gift cards are imported with balance tracking and customer linking

### 8. Collections and Categorization

Keep your product organization consistent across both platforms.

- **Bidirectional collection sync**: Shopify collections map to Odoo product categories and vice versa
- **Automatic sync every hour**
- **Collection metadata**: Descriptions and images are synced alongside collections
- **Product membership**: Products are automatically linked to their correct collections/categories

### 9. Promoter and Affiliate System

A built-in promoter management system — no additional apps required.

- **Promoter profiles**: Create promoters linked to Odoo contacts, with configurable commission rates (percentage or fixed amount)
- **Automatic discount code generation**: Each promoter gets a unique discount code with customizable prefix
- **Flexible discount types**: Percentage off, fixed amount off, or free shipping
- **Usage controls**: Set minimum order amounts, usage limits per code, usage limits per customer, and expiration dates
- **Automatic tracking**: When an imported order uses a promoter's discount code, the system tracks it automatically
- **Performance dashboard**: View each promoter's total orders, revenue generated, discounts given, and commissions earned
- **Bulk export**: Push discount codes to Shopify in bulk

### 10. Real-Time Webhooks

Instant updates when something changes on Shopify — no waiting for the next sync cycle.

- **Supported events**: Product changes, new/updated/cancelled orders, customer updates, inventory changes, fulfillments, refunds, and app lifecycle events
- **Enterprise-grade security**: Every webhook is verified using HMAC-SHA256 cryptographic signatures
- **Automatic retry**: Failed webhook processing is retried up to 5 times with progressive delays
- **Dead-letter queue**: Events that fail repeatedly are moved to a review queue for manual investigation — nothing is silently lost
- **One-click registration**: Register all webhooks with Shopify from your backend configuration screen

### 11. B2B and Wholesale Isolation

Sell B2B through Odoo and DTC through Shopify — from the same system, without interference.

- **Sales channel separation**: Every order is tagged as either "direct" (B2B/manual) or "Shopify"
- **Automatic gating**: Only Shopify-originated orders trigger sync actions (fulfillment push, payment sync, inventory updates)
- **B2B orders are never sent to Shopify**: Your wholesale pricing, custom terms, and direct sales remain private
- **Shared product catalog**: The same products can be sold through both channels with different pricing via Odoo pricelists

### 12. Multi-Store and Multi-Company

Enterprise-ready architecture for complex business structures.

- **Unlimited Shopify stores**: Connect as many stores as you need to a single Odoo instance
- **Per-store configuration**: Each store has its own sync settings, tax mappings, payment journals, warehouse, and pricelist
- **Multi-company isolation**: Each store is scoped to an Odoo company with strict data separation enforced at the database level
- **Independent sync schedules**: Each store syncs on its own schedule and can be paused independently

### 13. Dashboard and Monitoring

Full visibility into your integration health — at a glance.

- **Store health dashboard**: See all your connected stores in a single view with real-time metrics
- **Live counters**: Synced products, orders, customers, collections, refunds, and active promoters — per store
- **Error visibility**: Error counts are shown prominently; drill down into specific failures with one click
- **Sync log analytics**: Graph and pivot views showing sync activity over time — identify trends and troubleshoot issues
- **Connection status**: Instant visibility into whether each store is connected, disconnected, or experiencing errors

### 14. Automated Reconciliation and Self-Healing

The connector continuously monitors its own health and fixes problems automatically.

- **Drift detection every 6 hours**: Compares record counts between Shopify and Odoo to catch missed syncs
- **Stale binding detection**: Identifies records that haven't synced in over 24 hours and flags them for review
- **Automatic error retry**: Records stuck in error state are automatically retried after a cooldown period
- **Payment and fulfillment reconciliation**: Detects mismatches between Shopify and Odoo financial/fulfillment status

### 15. Flexible Field Mapping and Metafields

Customize exactly which data flows between systems — without writing code.

- **Per-store field mappings**: Control which fields sync and in which direction for products, customers, and orders
- **Metafield sync**: Shopify metafields (custom data attached to products, variants, customers, or orders) can be mapped to Odoo fields
- **No code required**: All mapping configuration is done through the Odoo user interface

### 16. Guided Setup Wizard

Get up and running in minutes — not days.

- **5-step onboarding wizard**: Connection setup, sync configuration, webhook registration, initial data import, and completion
- **Connection testing**: Verify your credentials work before proceeding
- **One-click initial import**: Pull your existing Shopify products, customers, and order history into Odoo as part of setup
- **Configurable import window**: Choose how many days of historical orders to import

### 17. GDPR and Data Privacy Compliance

Built-in compliance with data privacy regulations.

- **Customer data request handling**: Automated processing of Shopify's mandatory GDPR webhooks
- **Data redaction support**: Customer and shop data redaction endpoints are fully implemented
- **Webhook log retention**: Logs containing personal data are automatically purged after 90 days
- **Audit trail**: All sync operations are logged for accountability and compliance

### 18. Enterprise Security

Designed with security as a foundational requirement — not an afterthought.

- **Role-based access control**: Three access tiers (User, Manager, System Administrator) with granular permissions
- **Secure credential storage**: API tokens are encrypted and visible only to system administrators
- **Webhook payload verification**: Every incoming webhook is cryptographically verified before processing
- **Rate limiting**: Built-in protection against excessive webhook traffic (200 requests per minute per store)
- **Replay protection**: Duplicate webhook deliveries are detected and rejected using timestamp validation and fingerprint caching

---

## Competitive Comparison

The Odoo Apps Store currently offers two established Shopify Connector Pros from third-party vendors. Here is how the Shopify Connector Pro compares against both.

### The Competitors

| | **Shopify Connector Pro** | **Emipro Technologies** | **VentorTech PRO** |
|---|---|---|---|
| **Pricing model** | Included with your project | ~$575 per Odoo version | ~$460 per Odoo version |
| **Upgrade cost** | Included | Must repurchase for each new Odoo version | Free with ecosystem subscription |
| **Support** | Dedicated, ongoing | 90 days free, then paid | With a subscription |

### Technology Foundation

| | **Adams** | **Emipro** | **VentorTech** |
|---|---|---|---|
| **Shopify API** | GraphQL Admin API (2026-01) | REST Admin API (legacy) | Partial GraphQL + REST |
| **Future-proof** | Yes — uses Shopify's only actively developed API | At risk — REST API deprecated Oct 2024, mandatory migration required | Partially — mixed approach |
| **Variant limit** | No limit (GraphQL native) | 100 variants max per product (REST limitation) | Varies by operation |
| **API efficiency** | Fetches exactly the data needed in a single request | Multiple REST calls required for the same data | Mixed |

> **Why this matters**: Shopify officially deprecated its REST Admin API in October 2024 and requires all new apps to use GraphQL since April 2025. Connectors still built on REST face increasing compatibility risks with each Shopify platform update, including hard failures for products with more than 100 variants.

### Feature Comparison

| Feature | **Adams** | **Emipro** | **VentorTech** |
|---|---|---|---|
| **Bidirectional product sync** | Yes | Yes | Yes |
| **Bidirectional customer sync** | Yes | Yes | Yes |
| **Order import** | Yes | Yes | Yes |
| **Inventory push** | Yes | Yes | Yes |
| **Multi-location inventory** | Yes, per-warehouse mapping | Limited | Basic |
| **Fulfillment push with tracking** | Yes, line-level | Yes | Yes |
| **Inbound fulfillment handling** | 3 modes (activity, auto-validate, ignore) | Basic | Basic |
| **Refund import with credit notes** | Yes, partial + full | Basic | Basic |
| **Payout import with transaction detail** | Yes | No | No |
| **Gift card tracking** | Yes | No | No |
| **Tax mapping rules** | Yes, name + rate matching with fiscal positions | Basic | Basic |
| **Payment journal mapping** | Yes, per gateway | Basic | Basic |
| **Metafield sync** | Bidirectional, configurable | No | Limited |
| **Collection sync** | Bidirectional | Basic | Basic |
| **Promoter/affiliate system** | Built-in (codes, commissions, tracking) | No | No |
| **B2B/wholesale isolation** | Yes, sales channel gating | No | No |
| **Reverse payment sync (Odoo → Shopify)** | Yes | No | No |
| **Reverse fulfillment sync (Odoo → Shopify)** | Yes, with line-level matching | Basic | Basic |
| **Field mapping customization** | Yes, per store, no code required | Limited | Yes |
| **Smart change detection (checksums)** | Yes | No | No |
| **Delta inventory sync** | Yes, only changed items | Full push each cycle | Not documented |
| **Guided setup wizard** | Yes, 5-step onboarding | No | No |
| **Dashboard with health metrics** | Yes, real-time counters and error badges | Basic | Basic |
| **Automated reconciliation** | Yes, drift detection + self-healing | No | No |
| **Dead-letter queue for failed events** | Yes, with retry + manual review | No | No |
| **Webhook replay protection** | Yes (HMAC + timestamp + fingerprint) | Basic HMAC only | Basic HMAC only |
| **Rate limiting on webhook endpoint** | Yes (200/min per store) | No | No |
| **GDPR compliance (data redaction)** | Yes, fully automated | Not documented | Not documented |
| **Webhook log retention policy** | Yes, 90-day auto-purge | No | No |
| **Multi-company support** | Yes, with database-level isolation rules | Claimed, limited documentation | Not prominently documented |
| **Bulk retry wizard** | Yes | No | No |

### Where Adams Stands Apart

**1. Built on Modern Technology**
The Adams connector is built entirely on Shopify's GraphQL Admin API — the only API Shopify is actively developing and supporting. Competitors relying on the deprecated REST API face growing compatibility risks and already cannot handle products with more than 100 variants.

**2. B2B and Wholesale Coexistence**
No competing connector offers sales channel isolation. If your business sells both B2B (directly through Odoo) and direct-to-consumer (through Shopify), competing connectors will attempt to sync your B2B orders to Shopify or interfere with your wholesale workflows. The Adams connector keeps both channels completely separate.

**3. Built-in Promoter and Affiliate Management**
Competing connectors require separate apps or manual processes to manage promoter codes, commissions, and performance tracking. The Adams connector includes a complete promoter system out of the box.

**4. Financial Depth**
No competing connector imports Shopify Payments payouts with transaction-level detail, tracks gift card balances, or provides reverse payment sync (marking Shopify orders as paid when invoices are posted in Odoo). The Adams connector gives your finance team complete visibility without switching between systems.

**5. Self-Healing and Resilience**
Automated reconciliation, drift detection, dead-letter queues, smart retry logic, and circuit breaker patterns mean the Adams connector recovers from problems on its own. Competing connectors require manual intervention when things go wrong — and often don't tell you something went wrong in the first place.

**6. Efficiency at Scale**
Checksum-based change detection and delta inventory sync mean the Adams connector only processes records that have actually changed. For a catalog of 10,000 products where 50 changed, the Adams connector makes 50 API calls. Competitors process all 10,000 every cycle — wasting time, bandwidth, and Shopify API quota.

**7. Enterprise Security**
Layered webhook security (HMAC verification, timestamp validation, replay protection, rate limiting, payload size limits), role-based access control, and encrypted credential storage provide a level of security that no competing connector matches.

**8. No Recurring Per-Version Cost**
Competing connectors charge $400–$460 for each Odoo version. When you upgrade from Odoo 19 to Odoo 20, you pay again. The Adams connector is included as part of your project — no surprise relicensing fees.

---

## Summary of Delivered Capabilities

| Area | Capabilities |
|---|---|
| **Products** | Bidirectional sync, images, variants, pricelists, metafields, collections, bulk export, change detection |
| **Orders** | Auto-import, invoicing, tax mapping, discounts, multi-currency, gift cards, cancellation handling |
| **Inventory** | Multi-location, delta sync, dual quantity modes, automatic updates on stock moves |
| **Customers** | Bidirectional sync, intelligent dedup (email/phone/both), tags, addresses, bulk export, guest handling |
| **Fulfillment** | Auto-push on delivery validation, tracking numbers, partial shipments, inbound handling (3 modes) |
| **Refunds** | Auto-import, credit note generation, partial + full support, line-level detail |
| **Finance** | Tax mapping, payment journals, payout import with transactions, reverse payment sync, gift cards |
| **Promoters** | Profiles, commission tracking, discount code generation, usage tracking, performance dashboard |
| **Webhooks** | Real-time events, HMAC security, retry + dead-letter, replay protection, rate limiting, GDPR compliance |
| **Operations** | Dashboard, sync logs, reconciliation, bulk retry, guided setup wizard, background import jobs |
| **Architecture** | Multi-store, multi-company, B2B isolation, role-based access, GraphQL API, adaptive rate limiting |

---

## Technical Specifications (Overview)

| Specification | Detail |
|---|---|
| Odoo version | 19 |
| Shopify API | GraphQL Admin API, version 2026-01 |
| Sync frequency | Configurable per entity (1 min to 6 hours) |
| Sync direction | Bidirectional (configurable per entity) |
| Multi-store | Unlimited stores per Odoo instance |
| Multi-company | Full support with database-level isolation |
| Webhooks | 14 event types with layered security |
| Automated jobs | 12 scheduled actions |
| Access control | 3-tier (User / Manager / System Administrator) |
| License | OPL-1 (Odoo Proprietary License) |

---

*Shopify Connector Pro — Built for businesses that demand reliability, completeness, and scalability from their Shopify-Odoo integration.*
