# Shopify Connector Full

This thin Odoo 19 meta-application is the DEC-029 Full edition.  It installs
the Lite modules plus the guarded inventory, fulfillment, and controlled
product-export modules:

- `shopify_connector_core`
- `shopify_connector_product`
- `shopify_connector_sale`
- `shopify_connector_inventory`
- `shopify_connector_fulfillment`
- `shopify_connector_product_export`

Its installation closure also includes the generic webhook foundation and the
separate product, order, inventory, and fulfillment webhook accelerators.
They admit supported events to existing asynchronous read jobs; scheduled
reconciliation remains the loss-recovery backstop, with no timing or
exactly-once promise.

The write-back domains retain their existing preview, confirmation, readback,
and manual-review controls.  This package contains no pricing, billing,
entitlement, website, support, or live-store claims.

Full supports up to ten configured Shopify stores per Odoo database, subject
to each store's readiness and capacity checks.  This is a bounded support
limit, not a throughput or unlimited-scale guarantee.

The deterministic marketplace archive is built with:

```bash
python tools/build_shopify_connector_bundle.py --edition full
```

Screenshots are rendered Odoo browser evidence with synthetic fixtures.  They
are illustrative and are not live Shopify or Odoo.sh/UAT acceptance evidence.
