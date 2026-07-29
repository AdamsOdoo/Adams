{
    'name': 'Shopify Connector Product Export',
    'version': '19.0.1.0.0',
    'summary': (
        'Controlled Odoo -> Shopify product export (Task 015) and '
        'append-only product media export (Task 015B): per-template opt-in, '
        'preview-first, allowlisted, split-mutation, non-destructive.'
    ),
    'description': """
Shopify Connector Product Export
================================

The write-back half of the product domain, isolated in its own module so
the whole catalog-write risk surface can be removed by uninstalling one
addon (ARCH PD-1).

Mutation strategy (control-room ruling, 2026-07-26)
---------------------------------------------------

``productSet`` is **not** the general update mutation. Its documented
list-field semantics ("Creates new entries, updates existing entries, and
deletes existing entries that aren't included in the mutation's input")
make it unsafe for an existing product whose collections, metafields and
media the connector does not own, and the official documentation does not
state what happens to a list field omitted entirely. This module therefore
never depends on omitted-list preservation:

* **create path** -- ``productSet(synchronous: true, identifier:
  {customId: ...})``, used only after preflight and reconciliation prove no
  Shopify product is bound to the Odoo source identity. The create shape
  carries the connector-owned product scalars, options and variants and
  claims no merchant-owned list state.
* **existing-product update path** -- ``productUpdate`` for permitted
  scalars (its input object has no ``variants`` and no ``productOptions``
  field, and expresses collections as additive/subtractive
  ``collectionsToJoin``/``collectionsToLeave``, so it cannot delete
  merchant list state by omission), ``productVariantsBulkUpdate`` with
  ``allowPartialUpdates: false`` for mapped existing variants, and
  ``productVariantsBulkCreate`` with ``strategy:
  PRESERVE_STANDALONE_VARIANT`` for variants the confirmed preview
  enumerated.

Nothing in this module deletes a remote variant, option, option value,
collection membership, metafield or media asset. Every difference that
would require a remote deletion fails closed to manual review.

Media export (Task 015B) is **append-only**: staged upload -> ``fileCreate``
-> poll ``fileStatus`` until ``READY`` -> ``fileUpdate(referencesToAdd:
[productId])``. No ``fileDelete``, no detach, no reorder, no
``productCreateMedia`` (deprecated), and no ``productSet.files`` on an
existing product.

Every mutation runs under the accepted DEC-031 Layer 2 protocol: a durable
attempt record before the network call, reconciliation-by-identifier
before any retry, and no blind resend.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': [
        'shopify_connector_core',
        'shopify_connector_product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/shopify_connector_product_export_company_rules.xml',
        'data/shopify_connector_product_export_cron.xml',
        # U3 operator UI. Wizard actions first (views reference them), then
        # the Owl client action (the preview form's button targets it), then
        # the views, then the menus, so every action exists before it is
        # referenced.
        'views/shopify_connector_product_export_wizard_views.xml',
        'views/shopify_connector_export_diff_views.xml',
        'views/shopify_connector_product_export_views.xml',
        'views/shopify_connector_product_export_diagnostics_views.xml',
        'views/shopify_connector_product_export_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'shopify_connector_product_export/static/src/scss/shopify_connector_export_diff.scss',
            'shopify_connector_product_export/static/src/xml/shopify_connector_export_diff.xml',
            'shopify_connector_product_export/static/src/js/shopify_connector_export_diff.js',
        ],
        # See the TD-009 note in `shopify_connector_core/__manifest__.py`: a
        # tour in `web.assets_backend` lands in the HOOT module set and breaks
        # suite registration for its whole addon. Tours live in
        # `web.assets_tests`, which only the test-mode backend loads.
        'web.assets_tests': [
            'shopify_connector_product_export/static/src/js/tours/shopify_connector_u3_export_tour.js',
        ],
        'web.assets_unit_tests': [
            'shopify_connector_product_export/static/tests/shopify_connector_export_diff.test.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
