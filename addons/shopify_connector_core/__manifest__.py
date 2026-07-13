{
    'name': 'Shopify Connector Core',
    'version': '19.0.1.6.0',
    'summary': (
        'Core substrate for the Odoo <-> Shopify connector: store, '
        'settings, location cache, binding mixin, job and job log models, '
        'the credential/redaction foundation, the API-client/test-'
        'connection foundation, and a core job enqueue/dispatch/cron '
        'drain skeleton. The skeleton itself makes no Shopify API calls '
        'and implements no domain sync. No webhooks, no UI.'
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

This module includes the credential storage, masking, and redaction
foundation (masked storage behind access control, no encryption claim),
the API-client/test-connection foundation (a read-only Shopify GraphQL
transport used only by the existing test-connection/readiness checks),
and the core job enqueue/dispatch/cron drain skeleton (claim, retry
scheduling, and failure routing only). The Task 006C sync-engine
skeleton itself performs no Shopify API calls and implements no domain
sync logic. The module still contains no webhook handling, no setup
wizard, and no operator-facing UI. It is a core scaffold only; domain
modules (product, sale, inventory, fulfillment) build on top of it in
later, separately authorized tasks.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['base'],
    'data': [
        'security/shopify_connector_security.xml',
        'security/ir.model.access.csv',
        'data/shopify_connector_cron_drain.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
