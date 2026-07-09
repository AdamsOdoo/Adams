{
    'name': 'Shopify Connector Product',
    'version': '19.0.1.0.0',
    'summary': (
        'Shopify product import and variant binding (Task 010): '
        'read-only Shopify product/variant import, template/variant '
        'binding models, and the product_import_sync job type. No '
        'product export, update, or write back to Shopify of any kind.'
    ),
    'description': """
Shopify Connector Product
==========================

Product/variant import and binding domain module, built on
``shopify_connector_core``:

* ``shopify.connector.product.template.binding`` -- binds one Shopify
  Product to one Odoo ``product.template``.
* ``shopify.connector.product.variant.binding`` -- binds one Shopify
  ProductVariant to one Odoo ``product.product``, always linked to its
  parent template binding.
* ``shopify.connector.product.importer`` -- the read-only import/matching
  service (existing binding -> SKU -> barcode -> manual review), gated by
  the MBQ-59 two-tier no-blind-create policy.
* The ``product_import_sync`` job type, registered on the existing core
  job/dispatch substrate via three narrow extension seams (``job_type``
  ``selection_add``, a ``_domain_flag_for_job_type()`` override gating it
  on ``product_domain_enabled``, and a ``_get_handlers()`` override) --
  zero edits to ``shopify_connector_core`` itself.

Import-only: no product/variant export, update, or write back to
Shopify of any kind. No customer, order, inventory, or fulfillment
logic. No UI, wizard, webhook, or OAuth file.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['shopify_connector_core', 'product'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
