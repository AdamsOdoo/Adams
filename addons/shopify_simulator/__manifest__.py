# Part of Shopify Simulator. Internal QA tool — not for public distribution.
{
    'name': 'Shopify Simulator (Internal QA)',
    'version': '19.0.1.0.0',
    'category': 'Hidden/Tools',
    'summary': 'Fake Shopify GraphQL API server for testing Shopify Connector Pro',
    'description': """
Internal-only module that simulates the Shopify Admin GraphQL API.
Used for end-to-end integration testing and UAT of the Shopify Connector Pro
module without connecting to a real Shopify store.

NOT FOR PRODUCTION USE. NOT FOR PUBLIC DISTRIBUTION.
    """,
    'author': 'Qamah Solutions',
    'license': 'OPL-1',
    'depends': [
        'shopify_connector_pro',
    ],
    'data': [
        'security/shopify_sim_security.xml',
        'security/ir.model.access.csv',
        'data/sim_sequences.xml',
        'views/sim_config_views.xml',
        'views/sim_product_views.xml',
        'views/sim_customer_views.xml',
        'views/sim_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
