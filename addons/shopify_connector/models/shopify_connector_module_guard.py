from odoo import _, models
from odoo.exceptions import UserError

from .shopify_connector_package import REQUIRED_TECHNICAL_MODULES

#: The umbrella application's own technical name. Kept as a module-level
#: constant (not read from `ir.model.data`) so the guard below works even
#: if this module's own `ir.model.data` row is unavailable for any reason
#: -- the guard's whole job is to fail closed, so it must not depend on the
#: thing it is protecting.
PACKAGE_MODULE_NAME = 'shopify_connector'

_PROTECTED_NAMES = set(REQUIRED_TECHNICAL_MODULES)


class IrModuleModuleUninstallGuard(models.Model):
    """Refuses a direct uninstall of any of the six connector technical
    modules unless the umbrella `shopify_connector` application is also
    part of the SAME root selection (a genuine full-package uninstall).

    Why checking `self` here is safe and unspoofable (Section 9): `self` at
    entry to `button_uninstall` is always exactly the caller's root
    selection -- verified against the pinned Odoo 19 source
    (`ir_module.py`): the Apps-view single-module uninstall button, the
    `base.module.uninstall` wizard's `action_uninstall`
    (`self.module_ids.button_immediate_uninstall()`, where `module_ids` is
    the wizard's own `default_module_ids` from the ORIGINAL click, not the
    computed `impacted_module_ids`), and `button_immediate_uninstall`
    itself (`self._button_immediate_function(...button_uninstall)`) all
    pass the ORIGINAL selection through unchanged. Odoo's own downstream
    cascade (`self.downstream_dependencies()`) is computed strictly AFTER
    this point and is never part of `self` -- so a legitimate cascade from
    uninstalling a standard dependency (e.g. `self == {stock}`) never
    contains a connector module here, and this guard never sees it, let
    alone blocks it. There is no caller-supplied context flag consulted
    anywhere in this method -- authorization is derived only from the
    verified identity of the root selection itself, so a crafted RPC that
    tries to co-select a connector module alongside an unrelated standard
    module (to make it "look like" part of an authorized cascade) is
    refused exactly the same as a bare direct attempt.
    """

    _inherit = 'ir.module.module'

    def button_uninstall(self):
        protected_selected = self.filtered(lambda m: m.name in _PROTECTED_NAMES)
        package_selected = any(m.name == PACKAGE_MODULE_NAME for m in self)
        if protected_selected and not package_selected:
            raise UserError(_(
                'The "%(names)s" module(s) are part of the Shopify '
                'Connector application and cannot be uninstalled on their '
                'own. To remove the connector completely, uninstall the '
                '"Shopify Connector" application instead. If you intended '
                'to remove an Odoo application it depends on (Sales, '
                'Inventory, ...), uninstall that application directly -- '
                'the affected connector component(s) will be paused '
                'automatically, not deleted.'
            ) % {'names': ', '.join(sorted(protected_selected.mapped('name')))})
        return super().button_uninstall()
