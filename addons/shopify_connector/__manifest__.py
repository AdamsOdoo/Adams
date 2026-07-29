{
    'name': 'Shopify Connector',
    'version': '19.0.1.0.0',
    'summary': (
        'The single customer-facing Shopify Connector application: '
        'one-action install of the complete connector suite, package '
        'lifecycle integrity, global pause on dependency loss, and '
        'administrator-driven restore/resume.'
    ),
    'description': """
Shopify Connector -- package lifecycle
=======================================

This module is the ONE customer-facing application card for the Odoo 19
<-> Shopify connector. It is deliberately domain-empty: it contains no
product, order, customer, inventory or fulfillment sync logic, and no
Shopify API call of its own. Its only job is the package lifecycle:

* one-action installation of the complete mandatory connector suite
  (``shopify_connector_core`` and every domain technical module) plus
  every standard Odoo application they require;
* refusing a direct attempt to uninstall a connector technical module on
  its own, everywhere that can be attempted (Apps view, uninstall
  wizard, ``button_immediate_uninstall`` RPC);
* detecting when a standard Odoo dependency (Sales, Inventory, ...) has
  been uninstalled out from under the connector, and putting the whole
  connector into a durable, global, fail-closed dependency-paused state;
* an administrator-only, staged restore/resume workflow that never
  auto-resumes synchronisation.

Why this needs its own module, and why the dependency direction here is
the reverse of what the six connector technical modules use internally
(architecture record: docs/03-architecture/single-package-lifecycle.md).

In short: Odoo's ``ir.module.module.downstream_dependencies()`` is a
transitive, unconditional cascade -- uninstalling ``stock`` uninstalls
(and physically deletes the owned data of) every module that depends on
``stock``, directly or through any chain of ``depends``. If this package
depended on the six connector technical modules the ordinary way, losing
``stock`` would cascade all the way up and uninstall this package too,
which is exactly the persistence this package exists to guarantee does
NOT happen. So the direction here is inverted: this module depends on
nothing but ``base``/``web`` (never realistically uninstalled), and the
six connector technical modules each add THIS module to their own
``depends`` instead. That keeps this package upstream of (and therefore
immune to) any standard-dependency cascade, while still letting a full
"uninstall Shopify Connector" cascade correctly downward through Odoo's
own dependency graph to remove every connector technical module.

Installing the complete suite in one action is achieved with
``post_init_hook`` rather than a static manifest dependency, for the
same reason: a static dependency edge from this package onto the six
technical modules would recreate the exact fragility above. The hook
marks the six technical modules ``to install`` (``button_install``,
never the registry-requiring ``button_immediate_install``, which is
unsafe to call mid-load); Odoo's own module loader
(``odoo/modules/loading.py``, the ``STEP 3`` loop in ``load_modules``)
re-scans ``ir_module_module`` for newly-marked ``to install`` rows and
keeps loading until none remain -- so the whole suite, and every
standard Odoo application the six technical modules need, is installed
within the SAME install action, with no second manual step.
""",
    'author': 'Adams',
    'license': 'LGPL-3',
    'category': 'Connector',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/shopify_connector_package_views.xml',
    ],
    'post_init_hook': '_post_init_install_full_suite',
    'installable': True,
    'application': True,
    'auto_install': False,
}
