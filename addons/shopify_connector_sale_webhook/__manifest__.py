{
    'name': 'Shopify Connector Sale Webhooks',
    'version': '19.0.0.1.0',
    'summary': (
        'Read-first Shopify order webhook acceleration for the existing '
        'order importer.'
    ),
    'description': """
Shopify Connector Sale Webhooks
==============================

This optional domain addon activates only the three assessed order topics:
``orders/create``, ``orders/updated`` and ``orders/cancelled``.  The generic
webhook addon owns raw-body HMAC verification, delivery deduplication and the
durable processing envelope.  This addon validates Shopify's exact Order GID,
then admits the existing ``order_import_sync`` job; the child job performs the
authoritative Shopify GraphQL read.

Cancellation deliveries are evidence-refresh signals only.  They never
cancel an Odoo order, reverse stock, issue a refund, or perform a Shopify
mutation.  Scheduled order reconciliation remains the loss-recovery path.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['shopify_connector_webhook', 'shopify_connector_sale'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
