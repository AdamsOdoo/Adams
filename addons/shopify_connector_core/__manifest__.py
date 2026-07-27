{
    'name': 'Shopify Connector Core',
    'version': '19.0.1.14.0',
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
        # PERF-1: the drain's per-pass cap parameter is seeded before the
        # drain cron that consumes it.
        'data/shopify_connector_config_params.xml',
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
        ],
        # TOURS BELONG HERE, NOT IN `web.assets_backend` (TD-009).
        #
        # `web.assets_unit_tests_setup` does `('include', 'web.assets_backend')`,
        # so anything in the backend bundle is also a candidate module for a
        # HOOT run. HOOT then builds a per-suite MODULE SET from the test
        # file's addon plus that addon's declared Odoo dependencies
        # (`web/static/tests/_framework/module_set.hoot.js::defineModuleSet`)
        # and STARTS EVERY MODULE IN IT. `web_tour` is not a declared
        # dependency of this addon, so `@web_tour/tour_utils` is filtered OUT
        # of the set -- and a tour that imports `stepUtils` from it therefore
        # threw `Cannot destructure property 'stepUtils' of 'require(...)' as
        # it is undefined`, which failed the whole module set and produced
        # `HootError: error while registering suite
        # "shopify_connector_dashboard"`. That is the entire residual cause of
        # TD-009: the dashboard suite was never broken, a file sharing its
        # bundle was.
        #
        # `web.assets_tests` is Odoo's own home for HttpCase tours (see
        # `account`, `crm`, `calendar` ... at the pin). It is loaded into the
        # backend only when `test_mode_enabled` or `'tests' in debug`
        # (`web/views/webclient_templates.xml::conditional_assets_tests`), which
        # is exactly when `start_tour` runs, and it is in NO unit-test bundle,
        # so a tour can never again break a HOOT suite.
        'web.assets_tests': [
            'shopify_connector_core/static/src/js/tours/shopify_connector_u0_tour.js',
            # U2 lives in core because the surfaces it walks belong to four
            # different addons and a tour can only be registered once; core is
            # the only module all four depend on.
            'shopify_connector_core/static/src/js/tours/shopify_connector_u2_tour.js',
            'shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js',
        ],
        'web.assets_unit_tests': [
            'shopify_connector_core/static/tests/shopify_connector_dashboard.test.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
