{
    'name': 'Shopify Connector Product',
    'version': '19.0.2.5.0',
    'summary': (
        'Shopify product import completeness (Task 010/010B): read-only '
        'Shopify product/variant import with attributes, variants, '
        'prices, and basic images; template/variant binding models; and '
        'the product_import_sync job type. No product export, update, or '
        'write back to Shopify of any kind.'
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

Import-only. No product or variant export, update, or write back to
Shopify of any kind. No customer, order, inventory, or fulfillment
logic. No UI, wizard, webhook, or OAuth file.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['shopify_connector_core', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'security/shopify_connector_product_company_rules.xml',
        'data/shopify_connector_attribute_lock.xml',
        # U2 operator UI. Views before menus, so every action referenced by a
        # menu already exists when the menu record is created.
        'views/shopify_connector_product_binding_views.xml',
        'views/shopify_connector_product_menus.xml',
        # Batch 2 checkpoint 1: the product-import section of the canonical
        # Store Settings form, contributed by inheritance.
        'views/shopify_connector_store_settings_product_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
