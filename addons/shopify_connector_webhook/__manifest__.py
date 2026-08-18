{
    'name': 'Shopify Connector Webhooks',
    'version': '19.0.1.0.0',
    'summary': 'Secure Shopify webhook intake and subscription health',
    'description': """
Shopify Connector Webhooks
==========================

The modular W1 webhook foundation for the Shopify connector.  It verifies
Shopify signatures over the raw request body, resolves an unguessable
store-scoped callback token, persists redacted delivery metadata, and queues
durable Odoo jobs for asynchronous processing.  It also reconciles the
expected subscription registry with Shopify's Admin GraphQL state.

Webhooks accelerate synchronization; scheduled reconciliation remains the
correctness backstop.  This addon does not perform domain writes inline and
does not claim real-time processing.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['shopify_connector_core'],
    'data': [
        'security/ir.model.access.csv',
        'security/shopify_connector_webhook_company_rules.xml',
        'data/shopify_connector_webhook_cron.xml',
        'views/shopify_connector_webhook_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
