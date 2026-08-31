{
    'name': 'Shopify Connector Full',
    'version': '19.0.1.0.0',
    'summary': (
        'Full Odoo 19 Shopify connector edition with guarded inventory, '
        'fulfillment, and product export.'
    ),
    'description': """
Shopify Connector Full
======================

The DEC-029 Full edition installs the Lite modules and the controlled
write-back domains: ``shopify_connector_inventory``,
``shopify_connector_fulfillment``, and ``shopify_connector_product_export``.

Full adds guarded inventory operations, fulfillment/tracking workflows, and
controlled catalog export.  Each domain retains its existing preview,
confirmation, readback, and review controls.  This meta-application adds no
models, views, data records, controllers, scheduled actions, credentials, or
Shopify behavior of its own.

The installation closure also includes the generic webhook foundation and the
separate product, order, inventory, and fulfillment webhook accelerators.
These handlers admit existing asynchronous read jobs for supported topics;
scheduled reconciliation remains the loss-recovery backstop.  No timing or
exactly-once promise is made by this listing.

The edition boundary is enforced by the Odoo module set.  It does not add
license keys, billing, entitlement checks, pricing, or a support service.

The supported deployment boundary is up to ten configured Shopify stores per
Odoo database, subject to each store's readiness and capacity checks.  This
is a bounded support limit, not a throughput or unlimited-scale guarantee.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': [
        'shopify_connector_core',
        'shopify_connector_product',
        'shopify_connector_sale',
        'shopify_connector_inventory',
        'shopify_connector_fulfillment',
        'shopify_connector_product_export',
        'shopify_connector_webhook',
        'shopify_connector_product_webhook',
        'shopify_connector_sale_webhook',
        'shopify_connector_inventory_webhook',
        'shopify_connector_fulfillment_webhook',
    ],
    'images': [
        'images/dashboard_screenshot.png',
        'images/settings_screenshot.png',
        'images/order_review_screenshot.png',
        'images/inventory_screenshot.png',
        'images/fulfillment_screenshot.png',
        'images/jobs_screenshot.png',
    ],
    'data': [],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
