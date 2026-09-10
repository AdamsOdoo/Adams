# Shopify Connector Lite

This thin Odoo 19 meta-application is the DEC-029 Lite edition.  It installs
the shared, product-import, and sales/customer modules:

- `shopify_connector_core`
- `shopify_connector_product`
- `shopify_connector_sale`

Its installation closure also includes the generic webhook foundation and the
separate product and order webhook accelerators.  They admit supported events
to the existing asynchronous read jobs; scheduled reconciliation remains the
loss-recovery backstop, with no timing or exactly-once promise.

Lite contains no connector write-back modules; additional write-capable
domains belong to the Full edition.  This package contains no pricing,
billing, entitlement, website, support, or live-store claims.

The deterministic marketplace archive is built with:

```bash
python tools/build_shopify_connector_bundle.py --edition lite
```

No listing screenshots are published in this candidate because the available
captures include surfaces outside Lite.  The repository's visual evidence
uses synthetic fixtures and is not live Shopify or Odoo.sh/UAT acceptance
evidence.
