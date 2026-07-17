{
    'name': 'Shopify Connector Sale',
    'version': '19.0.2.0.0',
    'summary': (
        'Shopify customer import and matching (Task 011): read-only '
        'Shopify customer import, a customer binding model, and the '
        'customer_import_sync job type. No order/product/inventory/'
        'fulfillment logic, no customer export, no Shopify write of '
        'any kind.'
    ),
    'description': """
Shopify Connector Sale

Customer import and matching domain module, built on
shopify_connector_core.

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
registration, with zero edits to shopify_connector_core itself.

Import-only. No customer export of any kind. No order, product,
inventory, or fulfillment logic. No UI, wizard, webhook, or OAuth
file.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['shopify_connector_core', 'shopify_connector_product', 'sale'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
