{
    'name': 'Shopify Connector Lite',
    'version': '19.0.1.0.0',
    'summary': (
        'Read-first Odoo 19 Shopify connector edition for products, customers, '
        'and supported orders.'
    ),
    'description': """
Shopify Connector Lite
======================

The DEC-029 Lite edition installs the shared connector substrate together
with product import and supported customer/order synchronization:
``shopify_connector_core``, ``shopify_connector_product``, and
``shopify_connector_sale``.

The edition's installation closure also includes the generic webhook
foundation plus the separate product and order webhook accelerators.  Those
handlers admit the existing asynchronous read jobs for supported topics;
scheduled reconciliation remains the loss-recovery backstop.  No timing or
exactly-once promise is made by this listing.

Lite contains no connector write-back modules.  Additional write-capable
domains are delivered separately in the Full edition.  The edition boundary
is enforced by the Odoo module set; it does not add license keys, billing,
entitlement checks, or remote Shopify requests of its own.

This meta-application adds no models, views, data records, controllers,
scheduled actions, credentials, or Shopify behavior.  The companion modules
remain independently identifiable and own their existing lifecycle and
security contracts.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': [
        'shopify_connector_core',
        'shopify_connector_product',
        'shopify_connector_sale',
        'shopify_connector_webhook',
        'shopify_connector_product_webhook',
        'shopify_connector_sale_webhook',
    ],
    # No screenshot is published for Lite until a core/product/sale-only
    # browser-evidence set exists; existing captures expose Full navigation.
    'images': [],
    'data': [],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
