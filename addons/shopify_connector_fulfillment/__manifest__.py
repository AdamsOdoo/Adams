# Part of the Odoo 19 <-> Shopify Connector (Wave 4 Gate B).
# Fulfillment / tracking backend: both Mode 1 (Odoo-controlled) and Mode 2
# (bidirectional exact reconciliation). Every Shopify mutation runs under the
# accepted DEC-036/DEC-031 Layer 2 substrate. No UI (Wave 5). No live Shopify
# mutation in Gate B.
{
    'name': 'Shopify Connector - Fulfillment',
    'version': '19.0.1.0.0',
    'category': 'Connector',
    'summary': 'Odoo 19 <-> Shopify fulfillment and tracking synchronisation',
    'author': 'Adams',
    'license': 'LGPL-3',
    'depends': [
        'shopify_connector_core',
        'shopify_connector_sale',
        'stock_delivery',
        'sale_stock',
    ],
    # Data/security files are added as each model lands (Gate B build order).
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
