{
    'name': 'Shopify Connector Fulfillment Webhooks',
    'version': '19.0.0.1.0',
    'summary': (
        'Read-first Shopify fulfillment webhook acceleration for inbound '
        'observation.'
    ),
    'description': """
Shopify Connector Fulfillment Webhooks
======================================

This optional domain addon activates only ``fulfillments/create`` and
``fulfillments/update``.  W1 owns HTTPS/HMAC verification, delivery-ID
deduplication and the durable processing envelope.  The webhook handler
validates Shopify's explicit Fulfillment GID and admits a read-first resolver
job.  The resolver queries the Fulfillment node to obtain its exact Order GID,
then enqueues the existing ``fulfillment_inbound_observation`` job for a bound
order.  It never applies the webhook body, creates a fulfillment, updates
tracking, or performs any Shopify mutation.

Shopify's legacy numeric ``order_id`` is deliberately ignored: an Order GID
is never constructed from it.  Unbound orders become actionable manual-review
evidence, while scheduled/reconnect reconciliation remains the loss-recovery
path.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['shopify_connector_webhook', 'shopify_connector_fulfillment'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
