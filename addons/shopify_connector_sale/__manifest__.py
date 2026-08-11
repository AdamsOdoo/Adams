{
    'name': 'Shopify Connector Sale',
    'version': '19.0.2.10.0',
    'summary': (
        'Conservative Shopify customer and supported-kernel order import '
        'with bindings, tax decisions, guarded totals, scheduled scans, '
        'operator controls, and review-aware sales reporting. No customer '
        'export or Shopify mutation.'
    ),
    'description': """
Shopify Connector Sale
======================

Customer and supported-kernel order import domain module, built on
``shopify_connector_core`` and ``shopify_connector_product``.

Provides the shopify.connector.customer.binding model, which binds one
Shopify Customer to one Odoo res.partner; the inert
customer_fallback_partner_id store-settings configuration field
(Posture A -- defined here, never consumed by this module); the
shopify.connector.customer.importer read-only import and matching
service, using the match-key priority existing binding, then email,
then manual review, gated by the same no-blind-create discipline
already used by the product domain; and the customer_import_sync job
type, registered on the existing core job and dispatch substrate via
three narrow extension seams, a job_type selection addition, a domain
flag mapping gating it on sale_domain_enabled, and a handler
registration.

The order importer creates carefully validated initial Odoo sales orders
for supported Shopify order shapes, with explicit currency, tax, discount,
shipping, product and customer evidence. Existing imported orders are not
commercially rewritten after Shopify edits, cancellations or refunds;
divergent and otherwise unsupported lifecycle cases are routed to review
and excluded from reconciled sales totals. The addon includes order and
customer binding views, manual and scheduled scan controls, tax mapping and
decision workspaces, Store Settings contributions, and reporting fields.

Import-only. It performs no customer export and no Shopify mutation.
Inventory and fulfillment behavior are provided by their companion addons.
Freshness is scan/reconciliation based; there is no webhook delivery
pipeline or OAuth flow.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['shopify_connector_core', 'shopify_connector_product', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'security/shopify_connector_sale_company_rules.xml',
        'data/shopify_connector_sale_cron.xml',
        # U2 operator UI. Wizard actions first (the views reference them),
        # then the views, then the menus.
        'views/shopify_connector_sale_wizard_views.xml',
        'views/shopify_connector_order_binding_views.xml',
        'views/shopify_connector_customer_binding_views.xml',
        'views/shopify_connector_sale_menus.xml',
        # Batch 2 checkpoint 1: the order-import section of the canonical
        # Store Settings form, contributed by inheritance.
        'views/shopify_connector_store_settings_sale_views.xml',
        # Batch 2 checkpoint 2: the manual order controls. Inherits the core
        # store form and this module's own order-binding form, so both must
        # already be loaded.
        'views/shopify_connector_order_controls_views.xml',
        # Batch 2 checkpoint 2: the tax decision dialog, its entry point on
        # the stopped job, and the Tax Mapping workspace. Loads after the
        # sale menus, whose Orders branch its two menu items hang off.
        'views/shopify_connector_tax_decision_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
