{
    'name': 'Shopify Connector Product',
    'version': '19.0.2.10.0',
    'summary': (
        'Read-only Shopify product and variant import with scheduled scans, '
        'bindings, attributes, prices, images, explicit match decisions, '
        'and operator import controls. Product write-back remains isolated '
        'in the optional product-export addon.'
    ),
    'description': """
Shopify Connector Product

Product and variant import and binding domain module, built on
shopify_connector_core.

Provides the shopify.connector.product.template.binding model, which
binds one Shopify Product to one Odoo product.template; the
shopify.connector.product.variant.binding model, which binds one
Shopify ProductVariant to one Odoo product.product and is always linked
to its parent template binding; the shopify.connector.product.importer
read-only import and matching service, using the match-key priority
existing binding, then SKU, then barcode, then manual review, gated by
the MBQ-59 two-tier no-blind-create policy; and the product_import_sync
job type, registered on the existing core job and dispatch substrate
via three narrow extension seams, a job_type selection addition, a
domain flag mapping gating it on product_domain_enabled, and a handler
registration, with zero edits to shopify_connector_core itself.

This addon is import-only: it never creates or updates a product or variant
in Shopify. It includes merchant-facing binding lists, import controls,
scheduled discovery scans, matching decisions and Store Settings fields.
Product write-back is isolated in ``shopify_connector_product_export``.
Customer, order, inventory and fulfillment logic live in their respective
domain addons. There is no webhook delivery pipeline or OAuth flow.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['shopify_connector_core', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'security/shopify_connector_product_company_rules.xml',
        'data/shopify_connector_attribute_lock.xml',
        # Batch 2 checkpoint 3: the scheduled product enumeration cron.
        'data/shopify_connector_product_cron.xml',
        # U2 operator UI. Views before menus, so every action referenced by a
        # menu already exists when the menu record is created.
        'views/shopify_connector_product_binding_views.xml',
        'views/shopify_connector_product_menus.xml',
        # Batch 2 checkpoint 1: the product-import section of the canonical
        # Store Settings form, contributed by inheritance.
        'views/shopify_connector_store_settings_product_views.xml',
        # Batch 2 checkpoint 3: the product import controls, and the two
        # settings the producer makes real. Loads after the settings section
        # it extends by `inherit_id`.
        'views/shopify_connector_product_controls_views.xml',
        # Batch 2 §8.2: the durable match decision, its dialog and its
        # workspace. Loads after the menus file, whose Catalog & Matching
        # branch it hangs the Match Decisions entry off.
        'views/shopify_connector_product_match_decision_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
