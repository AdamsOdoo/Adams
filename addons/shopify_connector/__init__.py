from . import models
from .models.shopify_connector_package import REQUIRED_TECHNICAL_MODULES


def _post_init_install_full_suite(env):
    """One-action installation: mark the complete connector technical suite
    `to install`.

    Deliberately calls the deferred `button_install`, never
    `button_immediate_install`. `post_init_hook` runs mid-load, while
    `env.registry.ready` is still False (`_init` is still True), and
    `button_immediate_install` refuses to run in that state (see
    `_button_immediate_function`'s guard in the pinned Odoo's
    `ir_module.py`). `button_install` only marks rows `to install` and
    recurses through `depends` -- it needs no ready registry.

    Odoo's own loader (`odoo/modules/loading.py`, `load_modules`, the
    "STEP 3" loop) re-scans `ir_module_module` for any row in a
    to-do state that is not yet in its graph after every
    `load_module_graph` pass, and keeps looping until a pass adds nothing
    new. Marking these six `to install` here is enough for the SAME
    `-i shopify_connector` (or Apps-view install click) to install every
    one of them, and -- through their own existing `depends` -- every
    standard Odoo application they require, with no second manual step.

    Safe to call unconditionally: `button_install`/`_state_update` only
    transitions modules currently in state `uninstalled`; an already-
    installed technical module (warm adoption, Section 8) is left
    untouched.
    """
    Module = env['ir.module.module'].sudo()
    modules = Module.search([('name', 'in', list(REQUIRED_TECHNICAL_MODULES))])
    found = set(modules.mapped('name'))
    missing = set(REQUIRED_TECHNICAL_MODULES) - found
    if missing:
        # Fails loudly rather than silently installing a partial suite --
        # this can only happen if the addons path does not actually ship
        # one of the six technical modules alongside this package.
        raise RuntimeError(
            'Shopify Connector: the following mandatory technical module(s) '
            'are not present on the addons path and cannot be installed: '
            '%s' % ', '.join(sorted(missing))
        )
    modules.button_install()
    # Seed the package singleton now, with a PLAIN create on the ordinary
    # install-time env -- deliberately not `_get_singleton`'s side-cursor
    # path (there is nothing to protect against here: if this whole
    # install later fails and rolls back, this row correctly disappears
    # with everything else it was installed alongside, which is exactly
    # what should happen). This is the ONLY reason `_get_singleton`'s own
    # lazy, side-cursor-backed creation exists at all: to cover a database
    # that somehow reaches runtime without ever having run this hook --
    # there is no such supported path, but detecting a missing singleton
    # is cheap and strictly safer than assuming one always exists.
    Package = env['shopify.connector.package']
    if not Package.sudo().search([], limit=1):
        Package.sudo().create({'name': 'Shopify Connector'})
