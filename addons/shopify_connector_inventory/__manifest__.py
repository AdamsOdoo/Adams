{
    'name': 'Shopify Connector Inventory',
    'version': '19.0.1.2.0',
    'summary': (
        'Shopify inventory synchronization (Task 013): explicit location '
        'mapping, per-pair inventory-level bindings, first-push guard, and '
        'the Odoo -> Shopify available-quantity push via inventorySetQuantities '
        '/ inventoryActivate through the existing Stage 0 Layer 2 wrapper.'
    ),
    'description': """
Shopify Connector Inventory

Inventory synchronization domain module, built on shopify_connector_core
and shopify_connector_product.

Provides shopify.connector.location.mapping (explicit Shopify Location
GID <-> Odoo internal stock.location mapping, store-scoped, no name
inference), shopify.connector.inventory.level.binding (per
(product-variant, mapped-location) pair binding, first-push preview and
confirmation, informational last-pushed/last-known-Shopify quantity
fields, and the public action_recheck_inventory_pair review-release
action), and shopify.connector.inventory.service (the orchestration
service): three standalone job types --
inventory_push_sync (orchestration/read-only, no Shopify mutation),
inventory_activate and inventory_set_quantities (each a standalone
mutation job registered on the existing Stage 0 Layer 2
C1/C2/NET/C3 wrapper, each owning at most one mutation attempt for its
entire lifetime) -- plus inventory_push_scan (scheduled scan cron),
inventory_first_push_preview, and inventory_location_sync (Shopify
location cache population via one named sudo elevation).

Odoo is the standing source of truth for inventory after onboarding
(DEC-010). Only Shopify 'available' is ever written; 'committed' is
never written. One (inventory item, location) pair per mutation
request -- no batching. Unexplained Shopify-side drift creates a
review case and blocks the pending push; it is never silently
overwritten. A bounded 3-replacement CAS-stale retry chain and a
reconciliation not-applied replacement each create a new job (never a
same-job redispatch); the public action_recheck_inventory_pair(reason)
action (Reviewer/Administrator only) is the sole release path for a
blocked pair.

No fulfillment, product export, webhook, OAuth, or UI logic. No
Shopify -> Odoo stock write of any kind (the one-time reviewed baseline
import is deferred to a separately-gated Task 013B). No
inventoryAdjustQuantities call anywhere in this module.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': [
        'shopify_connector_core',
        'shopify_connector_product',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/shopify_connector_inventory_company_rules.xml',
        'data/shopify_connector_inventory_cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
