{
    'name': 'Shopify Connector Product Webhooks',
    'version': '19.0.0.3.0',
    'summary': (
        'Read-first Shopify product webhook acceleration for the product '
        'importer.'
    ),
    'description': """
Shopify Connector Product Webhooks

This optional domain addon activates Shopify ``products/create``,
``products/update`` and ``products/delete`` after the generic webhook addon has installed its verified
delivery envelope.  It never performs a Shopify request in the webhook
handler: the handler validates the exact ``admin_graphql_api_id`` identity,
then admits the existing ``product_import_sync`` job.  The child job performs
the authoritative Shopify GraphQL read and the scheduled product scan remains
the loss-recovery path.

Product deletion is represented by a stale binding for review; no Odoo product
is deleted or archived.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['shopify_connector_webhook', 'shopify_connector_product'],
    'pre_init_hook': 'pre_init_hook',
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
