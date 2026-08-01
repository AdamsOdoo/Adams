# Part of the Odoo 19 <-> Shopify Connector (Wave 4 Gate B).
# Fulfillment / tracking backend: both Mode 1 (Odoo-controlled) and Mode 2
# (bidirectional exact reconciliation). Every Shopify mutation runs under the
# accepted DEC-036/DEC-031 Layer 2 substrate. No UI (Wave 5). No live Shopify
# mutation in Gate B.
{
    'name': 'Shopify Connector - Fulfillment',
    'version': '19.0.1.4.0',
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
    'data': [
        'security/shopify_connector_fulfillment_security.xml',
        'security/ir.model.access.csv',
        'security/shopify_connector_fulfillment_company_rules.xml',
        'data/shopify_connector_fulfillment_cron.xml',
        # U1 operator UI. ORDER MATTERS (Odoo 19 data load order, U0 lesson):
        # the wizard act_windows are defined FIRST, because the settings and
        # binding views below reference them by `%(...)d`. A view that names an
        # action not yet loaded fails at install time.
        'wizards/shopify_connector_fulfillment_mode_switch_wizard_views.xml',
        'views/shopify_connector_store_settings_fulfillment_views.xml',
        'views/shopify_connector_fulfillment_review_views.xml',
        'views/shopify_connector_fulfillment_binding_views.xml',
        'views/shopify_connector_job_fulfillment_views.xml',
        # Menus last: every act_window they reference now exists.
        'views/shopify_connector_fulfillment_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
