{
    'name': 'Shopify Connector Inventory Webhooks',
    'version': '19.0.0.1.0',
    'summary': 'Read-first Shopify inventory-level drift observations',
    'description': """
Shopify Connector Inventory Webhooks

This optional domain addon activates only Shopify ``inventory_levels/update``.
The verified W1 delivery is an acceleration signal: the asynchronous child
job performs one authoritative GraphQL read of the exact InventoryLevel and
records monotonic observation evidence. It never writes Odoo stock and never
creates an outbound inventory mutation. Scheduled observation remains the
loss-recovery backstop.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': [
        'shopify_connector_webhook',
        'shopify_connector_inventory',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/shopify_connector_inventory_webhook_company_rules.xml',
        'data/shopify_connector_inventory_webhook_cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
