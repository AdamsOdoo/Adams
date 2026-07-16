{
    'name': 'Shopify Connector Product',
    'version': '19.0.2.1.2',
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
        'data/shopify_connector_attribute_lock.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
