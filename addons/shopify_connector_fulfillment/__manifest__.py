# Part of the Odoo 19 <-> Shopify Connector (Wave 4 Gate B).
# Fulfillment / tracking backend: both Mode 1 (Odoo-controlled) and Mode 2
# (bidirectional exact reconciliation). Every Shopify mutation runs under the
# accepted DEC-036/DEC-031 Layer 2 substrate.
{
    'name': 'Shopify Connector - Fulfillment',
    'version': '19.0.1.9.0',
    'category': 'Connector',
    'summary': (
        'Guarded Odoo <-> Shopify fulfillment and tracking synchronization: '
        'Mode 1 outbound operations, Mode 2 reconciliation, durable mode '
        'transitions, review queues, operator controls, and recovery evidence.'
    ),
    'description': """
Shopify Connector Fulfillment
=============================

Fulfillment and tracking domain module with two explicit operating modes.
Mode 1 keeps Odoo in control of outbound Shopify fulfillment/tracking
mutations. Mode 2 adds conservative inbound reconciliation and applies only
eligible, fully evidenced changes. Mode changes use durable requested and
effective state, a transition run, blocker/reason evidence, last-verified
timestamps, and a normal-UI rollback path.

Every Shopify mutation uses the connector's durable Layer 2 attempt and
reconciliation protocol. The addon includes fulfillment binding and review
workspaces, job recovery views, a mode-switch wizard and Store Settings
controls. Unsupported or ambiguous cases fail closed to review. Freshness is
scan/reconciliation based; there is no webhook delivery pipeline or OAuth
flow, and no claim of live-Shopify certification in the module metadata.
""",
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
