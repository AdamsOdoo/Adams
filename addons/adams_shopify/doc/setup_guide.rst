===============================
Shopify Connector Pro - Setup Guide
===============================

Prerequisites
=============

* Odoo 19.0 with the following modules installed:

  - ``sale_management``
  - ``stock``
  - ``account``
  - ``contacts``
  - ``mail``

* A Shopify store with a **Custom App** created in the Shopify Admin:

  1. Go to **Settings > Apps and sales channels > Develop apps**.
  2. Click **Create an app**, name it (e.g. "Odoo Connector").
  3. Under **Configuration > Admin API access scopes**, enable:

     - ``read_products``, ``write_products``
     - ``read_orders``, ``write_orders``
     - ``read_customers``, ``write_customers``
     - ``read_inventory``, ``write_inventory``
     - ``read_fulfillments``, ``write_fulfillments``
     - ``read_locations``
     - ``read_shopify_payments_payouts``

  4. Click **Install app** and copy the **Admin API access token**
     (starts with ``shpat_``).


Installation
============

1. Place the ``adams_shopify`` folder in your Odoo addons path.
2. Update the module list: **Apps > Update Apps List**.
3. Search for "Shopify Connector Pro" and click **Install**.


Quick Start (5 minutes)
========================

Step 1: Create a Backend
------------------------

Navigate to **Shopify > Configuration > Backends** and click **Create**.

=========================  ==========================================
Field                      Value
=========================  ==========================================
Name                       Your store's name (e.g. "My Shopify Store")
Shop URL                   ``my-store.myshopify.com``
Access Token               Paste the ``shpat_...`` token
Webhook Secret             (set later, see Step 4)
=========================  ==========================================

Click **Test Connection**.  If successful, the status changes to
**Connected** and Shopify's shop name and plan are populated.

Step 2: Configure Sync Settings
--------------------------------

On the backend form, review these tabs:

**Products tab:**

- *Sync Products*: Enable/disable product sync.
- *Direction*: ``Odoo -> Shopify``, ``Shopify -> Odoo``, or ``Bidirectional``.
- *Auto-export on Change*: Push product updates immediately on save.

**Orders tab:**

- *Import Orders*: Enable automatic order import.
- *Auto-create Invoice*: Automatically create and post invoices for
  paid orders.
- *Order Currency Mode*:

  - ``Company Currency``: all orders use your Odoo company currency.
  - ``Shopify Store Currency``: use the shop's base currency.
  - ``Customer Currency``: use Shopify Markets / multi-currency
    (presentment) pricing.

**Customers tab:**

- *Dedup By*: How to match incoming Shopify customers to existing
  Odoo partners.  Options: ``Email``, ``Phone``, ``Email + Phone``.

**Inventory tab:**

- *Push Inventory*: Enable stock level pushes to Shopify.
- *Quantity Type*: ``Free Qty`` (available) or ``On Hand``.

**Fulfillments tab:**

- *External Fulfillment Handling*: What to do when Shopify (or a 3PL)
  fulfills an order:

  - ``Create Activity``: schedule a manual review activity.
  - ``Auto-validate``: auto-validate the Odoo delivery order.
  - ``Update Status Only``: just update fulfillment status fields.

Step 3: Initialize Field Mappings
---------------------------------

Click the **Init Mappings** button on the backend form.  This creates
default field mappings for products and customers.  You can customize
them in the **Field Mappings** tab.

Step 4: Register Webhooks
--------------------------

Webhooks enable **real-time sync** (products, orders, customers,
inventory, fulfillments).

1. Generate a secret string (e.g. ``openssl rand -hex 32``).
2. Paste it into the **Webhook Secret** field on the backend.
3. Click **Register Webhooks**.

The connector registers these topics automatically:

- ``PRODUCTS_CREATE``, ``PRODUCTS_UPDATE``, ``PRODUCTS_DELETE``
- ``ORDERS_CREATE``, ``ORDERS_UPDATED``, ``ORDERS_CANCELLED``
- ``CUSTOMERS_CREATE``, ``CUSTOMERS_UPDATE``
- ``INVENTORY_LEVELS_UPDATE``
- ``FULFILLMENTS_CREATE``
- ``APP_UNINSTALLED``

**Important:** Your Odoo instance must be publicly reachable
(HTTPS with valid certificate) for Shopify to deliver webhooks.

Step 5: Run Initial Import
--------------------------

Use the **Import Wizard** (Shopify > Operations > Import Wizard) to
pull existing data:

1. Select your backend.
2. Choose entities to import (Products, Customers, Orders).
3. Click **Start Import**.

Alternatively, wait for the scheduled crons to pick up data
automatically.


Cron Schedule Reference
========================

======================================  =========  =============================
Cron Job                                Interval   Description
======================================  =========  =============================
Shopify: Sync Products                  15 min     Bidirectional product sync
Shopify: Sync Customers                 15 min     Bidirectional customer sync
Shopify: Import Orders                  5 min      Fetch new/updated orders
Shopify: Push Inventory                 10 min     Push stock levels to Shopify
Shopify: Process Pending Webhooks       1 min      Process queued webhooks
Shopify: Sync Discount Codes            30 min     Push discount codes (promoters)
Shopify: Sync Collections               1 hour     Import Shopify collections
Shopify: Import Refunds                 30 min     Import refund/credit notes
Shopify: Import Payouts                 6 hours    Import Shopify payouts
Shopify: Import Abandoned Carts         30 min     Import abandoned checkouts
Shopify: Reconciliation Check           6 hours    Detect drift/mismatches
Shopify: Daily Error Digest             1 day      Post error summary to chatter
Shopify: Cleanup Old Webhook Logs       1 day      Purge old webhook logs
======================================  =========  =============================


Multi-Company Setup
===================

Each backend is bound to a single ``res.company``.  To connect
multiple Shopify stores:

1. Create one backend per store.
2. Assign each to the appropriate company.
3. Set the warehouse per backend (inventory is pushed from that
   warehouse).

Orders imported from each store are created in the backend's company,
ensuring accounting isolation.


Multi-Currency (Shopify Markets)
================================

If you use Shopify Markets (multi-currency storefront), set the
**Order Currency Mode** to ``Customer Currency``.  This will:

- Read prices from the ``presentmentMoney`` fields.
- Automatically find or create an Odoo pricelist for each currency.
- Set the correct currency on sale orders and invoices.

Make sure the required currencies are **active** in Odoo
(Accounting > Configuration > Currencies).


Reverse Sync (Odoo to Shopify)
===============================

Two reverse-sync features push accounting actions back to Shopify:

**Reverse Sync: Payment**
  When you manually post an invoice for a Shopify order in Odoo,
  the connector calls ``orderMarkAsPaid`` on Shopify.

**Reverse Sync: Refund**
  When you manually post a credit note for a Shopify order in Odoo,
  the connector creates a refund on Shopify.

Enable these in the backend settings.  They are **off by default** to
prevent unexpected API calls.


Promoter / Affiliate System
============================

The connector includes a built-in promoter tracking system:

1. Create promoters (Shopify > Promoters) linked to Odoo partners.
2. Generate unique discount codes per promoter.
3. When orders are imported, discount code usage is tracked
   automatically.
4. Commissions are computed (percentage or fixed) per usage.


Error Monitoring
================

The connector provides multiple layers of error visibility:

1. **Sync Logs**: every sync run is logged with success/error counts.
   Navigate to Shopify > Sync Logs.

2. **Binding status**: each product/customer/order binding shows its
   sync status (Pending, Synced, Error, Permanent Error).

3. **Backend dashboard**: the backend form shows real-time counts of
   errors, pending items, and sync health percentage.

4. **Daily Error Digest**: a daily cron posts an error summary to
   the backend's chatter, visible to all followers.

5. **Reconciliation**: a 6-hour cron detects drift between Odoo and
   Shopify (payment mismatches, fulfillment mismatches, stale
   bindings).

**Tip:** Follow the backend record to receive email notifications
when error digests or sync alerts are posted.
