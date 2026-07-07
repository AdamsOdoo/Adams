{
    'name': 'Shopify Connector Core',
    'version': '19.0.1.1.0',
    'summary': (
        'Core substrate for the Odoo <-> Shopify connector: store, '
        'settings, location cache, binding mixin, job and job log models, '
        'plus the credential storage and redaction foundation. No '
        'Shopify API calls, no webhooks, no UI.'
    ),
    'description': """
Shopify Connector Core
=======================

The shared, domain-agnostic substrate for the Odoo <-> Shopify connector
addon family:

* ``shopify.connector.store`` -- one connection record per Shopify shop.
* ``shopify.connector.store.settings`` -- store-scoped feature flags and
  domain-enablement configuration.
* ``shopify.connector.location`` -- read-only cache of Shopify Locations.
* ``shopify.connector.binding.mixin`` -- abstract contract inherited by
  future per-domain binding models.
* ``shopify.connector.job`` -- sync job/state-machine substrate shared by
  every domain module.
* ``shopify.connector.job.log`` -- append-only per-attempt/event history
  for jobs.

This module now includes the credential storage, masking, and redaction
foundation (masked storage behind access control, no encryption claim).
It still contains no Shopify API client, no external API calls, no
webhook handling, no cron execution, no setup wizard, and no
operator-facing UI. It is a core scaffold only; domain modules (product,
sale, inventory, fulfillment) build on top of it in later, separately
authorized tasks.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['base'],
    'data': [
        'security/shopify_connector_security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
