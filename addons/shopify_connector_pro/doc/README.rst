=============================================
Shopify Connector Pro Ultimate Edition v19.0
=============================================

A production-grade, bidirectional connector between Odoo 19 and Shopify,
built on Shopify's GraphQL Admin API (2026-01).

Quick Start
============

1. Install the module from the Odoo Apps Store.
2. Navigate to **Shopify → Configuration → Shopify Stores** and create a backend.
3. Enter your ``myshopify.com`` URL and a Shopify **Admin API Access Token**
   (Custom App or Shopify App with ``read/write`` scopes for products, orders,
   customers, inventory, fulfillments, and assigned fulfillment orders).
4. Click **Test Connection** — the shop name and plan will be populated.
5. Click **Register Webhooks** (requires a publicly reachable URL or a tunnel).
6. Use the **Setup Wizard** (Configuration → Setup Wizard) for guided setup.

Connection Requirements
========================

* **Shopify Plan**: Basic or above.
* **Scopes** (recommended): ``read_products``, ``write_products``,
  ``read_orders``, ``write_orders``, ``read_customers``, ``write_customers``,
  ``read_inventory``, ``write_inventory``, ``read_fulfillments``,
  ``write_fulfillments``, ``read_assigned_fulfillment_orders``,
  ``write_assigned_fulfillment_orders``, ``read_shopify_payments_payouts``,
  ``read_all_orders``, ``read_discounts``, ``write_discounts``.

Architecture
=============

::

  ┌──────────────┐         ┌──────────────┐         ┌──────────────────┐
  │  Odoo Models │  ←───→  │  Sync Layer  │  ←───→  │  Shopify GraphQL │
  │  (Bindings)  │         │  (Importers/ │         │  Admin API       │
  │              │         │   Exporters) │         │  (2026-01)       │
  └──────────────┘         └──────────────┘         └──────────────────┘

* **Models layer** (``models/``): Binding records linking Odoo ↔ Shopify IDs.
  Checksum-based change detection to avoid redundant writes.
* **Sync layer** (``sync/``): Business logic for import/export per entity.
  Each entity has its own importer/exporter class.
* **API layer** (``shopify_api/``): GraphQL client with rate-limit handling,
  cost estimation, automatic retries, and bucket-based throttling.

Layers never skip: a model never calls the API directly; the sync layer
always mediates.

Entities
=========

+-----------------------+-------------------+----------------------------------+
| Entity                | Direction         | Notes                            |
+=======================+===================+==================================+
| Products / Variants   | Bidirectional     | Images, metafields, collections  |
+-----------------------+-------------------+----------------------------------+
| Customers             | Bidirectional     | Dedup by email/phone, tags       |
+-----------------------+-------------------+----------------------------------+
| Orders                | Shopify → Odoo    | Auto invoice, multi-currency     |
+-----------------------+-------------------+----------------------------------+
| Inventory             | Odoo → Shopify    | Multi-location, delta push       |
+-----------------------+-------------------+----------------------------------+
| Fulfillments          | Odoo → Shopify    | Tracking numbers, partial ship   |
+-----------------------+-------------------+----------------------------------+
| Collections           | Bidirectional     | Smart + Custom collections       |
+-----------------------+-------------------+----------------------------------+
| Refunds               | Shopify → Odoo    | Credit notes, line-level         |
+-----------------------+-------------------+----------------------------------+
| Discount Codes        | Odoo → Shopify    | Promoter-linked codes            |
+-----------------------+-------------------+----------------------------------+
| Payouts               | Shopify → Odoo    | Transaction-level breakdown      |
+-----------------------+-------------------+----------------------------------+
| Gift Cards            | Shopify → Odoo    | Read-only import                 |
+-----------------------+-------------------+----------------------------------+
| Metafields            | Bidirectional     | Configurable field mappings      |
+-----------------------+-------------------+----------------------------------+
| Locations             | Shopify → Odoo    | Warehouse mapping                |
+-----------------------+-------------------+----------------------------------+

Webhooks
=========

Supported topics (real-time):

* ``products/create``, ``products/update``, ``products/delete``
* ``orders/create``, ``orders/updated``, ``orders/cancelled``
* ``customers/create``, ``customers/update``
* ``inventory_levels/update`` (logged, Odoo is source of truth)
* ``fulfillments/create``
* ``refunds/create``
* ``app/uninstalled``
* GDPR: ``customers/data_request``, ``customers/redact``, ``shop/redact``

All webhooks are HMAC-verified using the configured secret.
Failed events are automatically retried up to 5 times, then moved to a
**dead-letter queue** for manual review and retry.

Background Import Jobs
=======================

For large initial imports, use **Operations → Import Data** to create
background import jobs. Jobs process data page-by-page via a cron
(every 2 minutes), with cursor-based pagination. Track progress from
**Operations → Import Jobs**.

Multi-Location Inventory
=========================

1. Click **Import Locations** on the backend form to pull Shopify locations.
2. Map each Shopify location to an Odoo warehouse under
   **Sync Status → Locations**.
3. Inventory sync will push stock for each mapped location independently.

If no location mapping exists, the legacy single-location mode is used
(``shopify_location_id`` on the backend).

Promoter / Affiliate System
=============================

Built-in promoter management with:

* Promoter records with discount codes and commission tracking.
* Automatic usage tracking when imported orders contain a promoter discount code.
* Performance computed fields (total orders, revenue, commission).

Payouts
========

The connector imports Shopify Payments payouts every 6 hours, including
per-transaction breakdowns (charges, refunds, fees, adjustments). View
payouts under **Sync Status → Payouts**.

Scheduled Actions (Crons)
==========================

+------------------------------------+------------+----------------------------+
| Cron                               | Interval   | Description                |
+====================================+============+============================+
| Sync Products                      | 15 min     | Bidirectional product sync |
+------------------------------------+------------+----------------------------+
| Sync Customers                     | 15 min     | Bidirectional customer sync|
+------------------------------------+------------+----------------------------+
| Import Orders                      | 5 min      | New/updated orders         |
+------------------------------------+------------+----------------------------+
| Push Inventory                     | 10 min     | Delta inventory push       |
+------------------------------------+------------+----------------------------+
| Process Webhooks                   | 1 min      | Pending webhook queue      |
+------------------------------------+------------+----------------------------+
| Sync Discount Codes                | 30 min     | Promoter discount export   |
+------------------------------------+------------+----------------------------+
| Sync Collections                   | 1 hour     | Collection import          |
+------------------------------------+------------+----------------------------+
| Import Refunds                     | 30 min     | Refund / credit note       |
+------------------------------------+------------+----------------------------+
| Import Payouts                     | 6 hours    | Shopify Payments payouts   |
+------------------------------------+------------+----------------------------+
| Process Import Jobs                | 2 min      | Background bulk imports    |
+------------------------------------+------------+----------------------------+
| Reconciliation Check               | 6 hours    | Detect sync drift          |
+------------------------------------+------------+----------------------------+

Troubleshooting
================

**Connection fails with "401 Unauthorized"**
   Your access token is invalid or expired. Generate a new one from your
   Shopify Custom App settings.

**Webhooks not arriving**
   Ensure your Odoo instance is publicly reachable (HTTPS required).
   Check ``Shopify → Logs → Webhook Log`` for received events.
   Use ``ngrok`` or similar for development/testing.

**Products not syncing**
   Check ``Sync Status → Products`` for error bindings.
   Verify the product has required fields (name, price).
   Check the ``Shopify → Logs → Sync Log`` for detailed error messages.

**Orders missing or duplicated**
   The connector deduplicates by Shopify GID. If orders are missing, check
   the order date range and import filters. Run a manual import from
   **Operations → Import Data**.

**Inventory not pushing**
   Confirm a Shopify location is configured (either legacy ``shopify_location_id``
   or mapped via ``Sync Status → Locations``). Only changed quantities
   are pushed (delta sync).

**Rate limit errors (429)**
   The client automatically handles Shopify's cost-based throttle.
   If you see persistent 429s, reduce ``batch_size`` on the backend.

**Dead-letter webhooks**
   Navigate to ``Logs → Webhook Log``, filter by "Dead Letter".
   Review the error, fix the underlying issue, then click **Retry**.

**Multi-company issues**
   Each backend is scoped to a company. Ensure you're in the correct
   company when viewing data. Record rules enforce isolation.

Security
=========

* **Groups**: ``Shopify User`` (read-only), ``Shopify Manager`` (CRUD),
  ``System Admin`` (full access including delete).
* **Record rules**: Multi-company isolation on all models.
* **Webhook verification**: HMAC-SHA256 signature validation on every
  incoming webhook.
* **Access tokens**: Stored with ``groups='base.group_system'`` — only
  system administrators can view/edit them.

License
========

OPL-1 (Odoo Proprietary License v1.0)

Author
=======

Developed by **Qamah Solutions** under the management of
**Odoo Partner Ahmed Saad** (ahmedsaad@tech-oriented.com).

Support
========

For issues or feature requests, contact ahmedsaad@tech-oriented.com
or open an issue on the project repository.
