{
    'name': 'Shopify Connector Core',
    'version': '19.0.1.12.0',
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
    # 'web' is required by the U0 operator UI (menus, views, the Owl dashboard
    # client action, SCSS/JS assets, and browser tours).
    'depends': ['base', 'web'],
    'data': [
        'security/shopify_connector_security.xml',
        'security/ir.model.access.csv',
        # SEC-3 (#197): store-rooted, fail-closed multi-company record rules.
        # Loaded after the ACLs, because a record rule refines an access
        # right that must already exist.
        'security/shopify_connector_company_rules.xml',
        'data/shopify_connector_cron_drain.xml',
        'data/shopify_connector_cron_disconnect.xml',
        'data/shopify_connector_pii_retention_cron.xml',
        'data/shopify_connector_stale_owner_sweep_cron.xml',
        # U0 operator UI. Load order honours cross-references: the dashboard
        # client action and the two wizard actions are defined before the
        # views that reference them, the Logs action before the job form that
        # links to it, and the menus last so every action already exists.
        'views/shopify_connector_dashboard_views.xml',
        'views/shopify_connector_ui_wizard_views.xml',
        'views/shopify_connector_store_views.xml',
        'views/shopify_connector_job_log_views.xml',
        'views/shopify_connector_job_views.xml',
        'views/shopify_connector_mutation_attempt_views.xml',
        'views/shopify_connector_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'shopify_connector_core/static/src/scss/shopify_connector_tokens.scss',
            'shopify_connector_core/static/src/scss/shopify_connector_dashboard.scss',
            'shopify_connector_core/static/src/xml/shopify_connector_dashboard.xml',
            'shopify_connector_core/static/src/js/shopify_connector_dashboard.js',
            'shopify_connector_core/static/src/js/tours/shopify_connector_u0_tour.js',
        ],
        'web.assets_unit_tests': [
            'shopify_connector_core/static/tests/shopify_connector_dashboard.test.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
