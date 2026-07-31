{
    'name': 'Shopify Connector Core',
    'version': '19.0.1.20.0',
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
        # S1 LOADS LAST, and the ordering is load-bearing rather than tidy.
        #
        # This file needs BOTH `view_shopify_connector_store_form` (which it
        # inherits, from the store views) and `menu_shopify_connector_root`
        # (which its Configuration branch hangs off, from the menus file). It
        # was originally placed beside the store views, where the menu ref did
        # not yet exist -- invisible on a warm `-u` update of a database that
        # already had the menu, and a hard `ParseError` on a FRESH install.
        # The fresh-install pass in `tools/run_connector_suite.sh` is what
        # caught it, which is exactly the failure family that pass exists for
        # (issue #193: fresh and warm are not interchangeable).
        'views/shopify_connector_setup_views.xml',
        # Batch 2 checkpoint 1: the canonical Store Settings surface. LOADS
        # AFTER the setup views for the same load-bearing reason they load
        # after the menus -- its menu hangs off `menu_shopify_connector_
        # configuration`, which the setup views file defines. Placed earlier
        # this would be invisible on a warm `-u` of a database that already
        # had that menu and a hard `ParseError` on a fresh install.
        'views/shopify_connector_store_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'shopify_connector_core/static/src/scss/shopify_connector_tokens.scss',
            'shopify_connector_core/static/src/scss/shopify_connector_dashboard.scss',
            'shopify_connector_core/static/src/xml/shopify_connector_dashboard.xml',
            'shopify_connector_core/static/src/js/shopify_connector_dashboard.js',
            # S1 guided setup. Same bundle, same token layer, same
            # component vocabulary — it is a second surface in one app, not
            # a second app.
            'shopify_connector_core/static/src/scss/shopify_connector_setup_wizard.scss',
            'shopify_connector_core/static/src/xml/shopify_connector_setup_wizard.xml',
            'shopify_connector_core/static/src/js/shopify_connector_setup_wizard.js',
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
            # S1 guided setup: the 11-step traversal, the three entry routes
            # and the keyboard walkthrough.
            'shopify_connector_core/static/src/js/tours/shopify_connector_s1_setup_tour.js',
            # Batch 2 P0 merchant reachability: canonical Store Settings, the
            # order and product controls, and the two decision dialogs. Here
            # for the same reason as U2 -- the surfaces belong to core,
            # `shopify_connector_sale` and `shopify_connector_product`, and a
            # tour can only be registered once.
            'shopify_connector_core/static/src/js/tours/shopify_connector_b2_tour.js',
        ],
        'web.assets_unit_tests': [
            'shopify_connector_core/static/tests/shopify_connector_dashboard.test.js',
            'shopify_connector_core/static/tests/shopify_connector_setup_wizard.test.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
