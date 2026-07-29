import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

#: The verified mandatory connector technical suite (docs/03-architecture/
#: single-package-lifecycle.md §2, derived from the exact manifest graph at
#: the pinned head, not a guess). Every one of these six modules is either
#: this package's own foundation (`shopify_connector_core`) or a domain
#: module that adds `shopify_connector` to its own `depends` precisely so
#: that uninstalling THIS package cascades down and removes all six -- see
#: the architecture record for the full proof.
REQUIRED_TECHNICAL_MODULES = (
    'shopify_connector_core',
    'shopify_connector_product',
    'shopify_connector_product_export',
    'shopify_connector_sale',
    'shopify_connector_inventory',
    'shopify_connector_fulfillment',
)

#: The standard Odoo application each technical module cannot function
#: without, direct edges only (verified against each module's own
#: `__manifest__.py` `depends` list). Used only to turn "which technical
#: module went missing" into a human-actionable "which Odoo application is
#: unavailable" message; the technical module's own state is always the
#: ground truth the integrity check acts on.
_DIRECT_STANDARD_APP_DEPS = {
    'shopify_connector_product': ('product',),
    'shopify_connector_sale': ('sale',),
    'shopify_connector_inventory': ('stock',),
    'shopify_connector_fulfillment': ('stock_delivery', 'sale_stock'),
    'shopify_connector_product_export': (),
    'shopify_connector_core': (),
}

#: Module states that do NOT count as "installed" for integrity purposes.
#: `to upgrade` is intentionally treated as healthy (mid-upgrade, not
#: mid-removal); every other non-`installed` state is a problem.
_NOT_INSTALLED_STATES = (
    'uninstalled', 'to remove', 'to install', 'uninstallable',
)

PAUSE_MESSAGE_TEMPLATE = _(
    "Shopify Connector paused\n\n"
    "One or more required Odoo applications are unavailable: %(missing)s. "
    "No Shopify synchronization will run while the connector is paused. "
    "Reinstall the missing applications, restore the connector suite, "
    "rerun readiness, and resume explicitly."
)


class ShopifyConnectorPackage(models.Model):
    """The persistent, customer-facing package lifecycle controller.

    Deliberately a singleton (see `_get_singleton`): module install state is
    instance-wide, not company-scoped, so "the connector is paused" is one
    fact, not one per company. Owns no Shopify transport, no domain sync
    logic, no store/job data -- see the architecture record for the
    dependency-direction reasoning that makes this module's survival across
    a standard-dependency cascade possible at all.

    `state` only ever moves `healthy` -> `dependency_paused` automatically
    (fail-closed: `assert_healthy` re-checks on every call, per Section 21's
    "checked again immediately before every network boundary"). The reverse
    transition, `dependency_paused` -> `healthy`, happens ONLY through
    `action_confirm_resume`, an explicit administrator action that re-proves
    integrity before flipping the flag -- there is no code path that resumes
    on its own.
    """

    _name = 'shopify.connector.package'
    _description = 'Shopify Connector Package Lifecycle'

    name = fields.Char(default='Shopify Connector', required=True, readonly=True)
    state = fields.Selection(
        [('healthy', 'Healthy'), ('dependency_paused', 'Dependency Paused')],
        required=True, default='healthy', readonly=True,
    )
    missing_technical_modules = fields.Char(readonly=True, copy=False)
    missing_standard_apps = fields.Char(readonly=True, copy=False)
    paused_at = fields.Datetime(readonly=True, copy=False)
    prior_state = fields.Char(readonly=True, copy=False)
    resumed_at = fields.Datetime(readonly=True, copy=False)
    resumed_by_uid = fields.Many2one('res.users', readonly=True, copy=False)
    last_integrity_check = fields.Datetime(readonly=True, copy=False)
    audit_note = fields.Text(readonly=True, copy=False)

    _shopify_connector_package_singleton_name = models.Constraint(
        'unique(name)',
        'There is exactly one Shopify Connector package record.',
    )

    @api.model
    def _get_singleton(self):
        """Return the one package record, creating it if this is the very
        first read (e.g. right after `post_init_hook` runs, before any data
        file has had a chance to seed it -- this module ships no data file
        for it on purpose, so a fresh install and a warm adoption of an
        existing installation behave identically).

        Creation commits independently (see `_commit_via_side_cursor`):
        the very first call is typically `assert_healthy()` itself, which
        may raise right after this returns -- an ordinary `create()` on
        `self.env.cr` would then be rolled back along with everything else
        in the caller's transaction, and the singleton would silently
        vanish having never truly existed.
        """
        record = self.sudo().search([], limit=1)
        if not record:
            self._commit_via_side_cursor(None, {'name': 'Shopify Connector'})
            record = self.sudo().search([], limit=1)
        return record

    def _commit_via_side_cursor(self, record_id, vals):
        """Write (or, if `record_id` is falsy, create) on an independent,
        immediately-committed cursor (CORE-R2 pattern -- see
        `shopify_connector_api_client.py::_admit_lifecycle` for the
        established precedent in this codebase).

        Load-bearing here, not merely defensive: `assert_healthy` writes the
        newly-detected paused state and then raises `UserError` in the SAME
        method call, and Odoo (like any HTTP/RPC request that lets an
        exception escape) rolls back the calling transaction when that
        happens. Writing through `self.env.cr` directly would make the
        pause detection disappear the instant it was needed -- the model
        would "detect" a pause on every single call forever, never actually
        recording one. A side cursor commits before the caller's exception
        ever propagates, so the pause record survives regardless of what
        the caller does next.
        """
        self.env.flush_all()
        side_cr = self.env.registry.cursor()
        try:
            side_env = api.Environment(side_cr, api.SUPERUSER_ID, {})
            Package = side_env['shopify.connector.package']
            if record_id:
                Package.browse(record_id).write(vals)
            else:
                Package.create(vals)
            side_cr.commit()
        finally:
            side_cr.close()
        if record_id:
            self.browse(record_id).invalidate_recordset(list(vals.keys()))

    @api.model
    def action_open_singleton(self):
        """Resolve and open the one package record. A plain `ir.actions.
        act_window` cannot point at a dynamically-created record (this
        singleton is created lazily by `_get_singleton`, not shipped as
        static XML data), so the menu binds to a tiny server action that
        calls this instead.
        """
        record = self._get_singleton()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shopify Connector'),
            'res_model': 'shopify.connector.package',
            'view_mode': 'form',
            'res_id': record.id,
            'target': 'current',
        }

    def _compute_integrity(self):
        """Pure `ir.module.module` state inspection. No Shopify, no store,
        no job -- this method only ever needs `base`, which this module
        already depends on.

        Returns a dict: `healthy` (bool), `missing_technical_modules` (list
        of technical module names not in state `installed`/`to upgrade`),
        `missing_standard_apps` (sorted list of human `shortdesc` names for
        the standard Odoo applications behind whichever technical modules
        are missing).
        """
        Module = self.env['ir.module.module'].sudo()
        modules = Module.search([('name', 'in', list(REQUIRED_TECHNICAL_MODULES))])
        by_name = {m.name: m for m in modules}
        missing_technical = [
            name for name in REQUIRED_TECHNICAL_MODULES
            if by_name.get(name) is None
            or by_name[name].state in _NOT_INSTALLED_STATES
        ]
        missing_app_technical_names = set()
        for name in missing_technical:
            missing_app_technical_names.update(_DIRECT_STANDARD_APP_DEPS.get(name, ()))
        missing_standard_apps = []
        if missing_app_technical_names:
            app_modules = Module.search([('name', 'in', list(missing_app_technical_names))])
            app_by_name = {m.name: m for m in app_modules}
            for technical_name in sorted(missing_app_technical_names):
                app = app_by_name.get(technical_name)
                if app is None or app.state in _NOT_INSTALLED_STATES:
                    missing_standard_apps.append(app.shortdesc if app else technical_name)
        return {
            'healthy': not missing_technical,
            'missing_technical_modules': missing_technical,
            'missing_standard_apps': sorted(missing_standard_apps),
        }

    def _apply_detected_state(self, integrity=None):
        """Re-evaluate integrity and, if currently `healthy` but integrity
        now fails, transition to `dependency_paused` and stamp the pause
        record. Idempotent: calling this repeatedly while already paused
        only refreshes `last_integrity_check`/the missing-dependency lists,
        never re-stamps `paused_at` or `prior_state`.

        This is the ONE place `state` can become `dependency_paused`. There
        is no corresponding auto-heal here on purpose -- see the class
        docstring. Persisted via `_commit_via_side_cursor` -- see that
        method's docstring for why an ordinary `write()` would not survive
        the `UserError` most callers (e.g. `assert_healthy`) raise
        immediately afterward.
        """
        self.ensure_one()
        integrity = integrity if integrity is not None else self._compute_integrity()
        vals = {
            'last_integrity_check': fields.Datetime.now(),
            'missing_technical_modules': ', '.join(integrity['missing_technical_modules']) or False,
            'missing_standard_apps': ', '.join(integrity['missing_standard_apps']) or False,
        }
        if not integrity['healthy'] and self.state == 'healthy':
            vals.update({
                'state': 'dependency_paused',
                'paused_at': fields.Datetime.now(),
                'prior_state': self.state,
                'audit_note': (
                    "Automatically paused: required application(s) %s are "
                    "unavailable (missing technical component(s): %s)."
                ) % (
                    ', '.join(integrity['missing_standard_apps']) or 'unknown',
                    ', '.join(integrity['missing_technical_modules']),
                ),
            })
        self._commit_via_side_cursor(self.id, vals)
        return integrity

    @api.model
    def is_healthy(self):
        """Fast, side-effect-free read used by hot paths that only need a
        boolean (e.g. a computed field evaluated per row). Prefer
        `assert_healthy` at an actual gate, since that re-checks first.
        """
        return self._get_singleton().state == 'healthy'

    @api.model
    def assert_healthy(self):
        """THE gate. Re-detects the current state (fail-closed, immediately
        before whatever the caller is about to do) and raises a plain-
        language `UserError` if the connector is paused. Call this at every
        required boundary: job admission, job dispatch/cron drain, retry/
        replay dispatch, the store's test-connection/reconnect/activate
        actions, and the API client's `execute`/`execute_business` --
        the two methods that are the sole transport surface (see
        `shopify_connector_api_client.py`), so this call also serves as the
        final pre-network boundary check independently of every earlier one.
        """
        record = self._get_singleton()
        record._apply_detected_state()
        if record.state != 'healthy':
            # Normally a missing standard app IS the root cause and is named
            # directly. If one cannot be identified -- the technical module
            # itself went missing/corrupted while its standard Odoo
            # dependency is still installed, an abnormal partial state
            # (Section 11) rather than an ordinary dependency loss -- name
            # the technical component(s) instead of a bare "unknown".
            missing = (
                record.missing_standard_apps
                or record.missing_technical_modules
                or _('unknown')
            )
            raise UserError(PAUSE_MESSAGE_TEMPLATE % {'missing': missing})

    # ------------------------------------------------------------------
    # Administrator restore / explicit resume workflow (Section 13).
    #
    # Three separate, explicit stages on purpose -- never collapsed into
    # one atomic call -- so an administrator always sees which stage failed
    # rather than a single opaque "restore" button that silently did
    # several things. Every stage requires genuine Odoo system-
    # administrator authority (`env.is_admin()`), the same authority Odoo
    # itself requires for any module install/uninstall
    # (`assert_log_admin_access` in `ir_module.py`) -- restoring the suite
    # IS a module-lifecycle operation, so this is not a narrower gate than
    # Odoo's own, and this package cannot reference the connector's own
    # Administrator group (defined in `shopify_connector_core`, which
    # depends on THIS module -- referencing it back would be circular).
    # ------------------------------------------------------------------

    def _require_system_admin(self):
        if not self.env.is_admin():
            raise UserError(_(
                'Restoring the Shopify Connector suite requires Odoo '
                'system administrator access.'
            ))

    def action_recheck_dependencies(self):
        """Stage 1: recompute integrity and report it. Never installs,
        upgrades, or resumes anything by itself.
        """
        self.ensure_one()
        self._require_system_admin()
        integrity = self._apply_detected_state()
        if integrity['healthy']:
            note = (
                "Dependency recheck: every required application and "
                "technical component is present. Restore Suite can proceed."
            )
        else:
            note = (
                "Dependency recheck: still missing application(s) %s. "
                "Reinstall them before Restore Suite can proceed."
            ) % (', '.join(integrity['missing_standard_apps']) or 'unknown')
        self._commit_via_side_cursor(self.id, {'audit_note': note})
        return integrity

    def action_restore_suite(self):
        """Stage 2: with every standard dependency confirmed present,
        reinstall the complete technical suite as one action.

        Refuses (fail-closed) if a standard application is still missing --
        restoring the technical modules before their own Odoo dependency
        exists is not possible, and this method never tries. A genuine
        no-op (no commit, no registry reload) when every technical module
        is already installed.

        Uses the deferred `button_install` (never the registry-requiring
        `button_immediate_install`) followed by exactly ONE explicit
        commit + registry reload, mirroring the exact pattern the pinned
        Odoo's own `base.module.upgrade.upgrade_module()` uses. This
        matters because `self` (and every other recordset computed before
        the reload) becomes stale the moment `Registry.new(...)` runs --
        `self` is re-fetched by id afterward before being touched again.
        Reconciling a component whose code on disk moved ahead of its
        installed version (Section 11 "component version mismatch") is a
        separate concern, left to Odoo's own ordinary Apps "Upgrade"
        action rather than folded into every Restore Suite call.
        """
        self.ensure_one()
        self_id = self.id
        self._require_system_admin()
        integrity = self._apply_detected_state()
        if integrity['missing_standard_apps']:
            raise UserError(_(
                'Cannot restore the Shopify Connector suite yet: the '
                'following Odoo application(s) are still not installed: '
                '%s. Reinstall them first, then Restore Suite again.'
            ) % ', '.join(integrity['missing_standard_apps']))
        Module = self.env['ir.module.module'].sudo()
        modules = Module.search([('name', 'in', list(REQUIRED_TECHNICAL_MODULES))])
        found_names = set(modules.mapped('name'))
        missing_names = set(REQUIRED_TECHNICAL_MODULES) - found_names
        if missing_names:
            raise UserError(_(
                'Cannot restore the Shopify Connector suite: the following '
                'technical module(s) are not present in this database at '
                'all (their code may be missing from the addons path): %s.'
            ) % ', '.join(sorted(missing_names)))
        to_install = modules.filtered(lambda m: m.state != 'installed')
        if not to_install:
            # Every technical component is already installed: a genuine
            # no-op. Deliberately does NOT also force an upgrade pass on the
            # already-installed modules here -- that would commit and
            # reload the registry on every call even when restoration was
            # never needed. Reconciling a component whose code moved ahead
            # of its installed version (Section 11 "component version
            # mismatch") is Odoo's own ordinary Apps "Upgrade" action; it is
            # not blocked by anything this method does.
            return self._apply_detected_state()
        to_install.button_install()
        self.env.cr.commit()
        from odoo.modules.registry import Registry
        Registry.new(self.env.cr.dbname, update_module=True)
        self.env.cr.reset()
        record = self.env['shopify.connector.package'].browse(self_id)
        integrity = record._apply_detected_state()
        record._commit_via_side_cursor(record.id, {'audit_note': (
            "Restore Suite completed: technical components (re)installed. "
            "Package integrity: %s. Run Readiness for each store, then "
            "resume explicitly -- restoring the suite does not resume "
            "synchronization by itself."
        ) % ('healthy' if integrity['healthy'] else 'still degraded')})
        return integrity

    def action_confirm_resume(self):
        """Stage 3: the ONLY method that can move `state` from
        `dependency_paused` back to `healthy`. Re-verifies integrity itself
        rather than trusting the caller's prior view of it, and refuses if
        anything is still missing.

        This does not touch any store, job, or per-store readiness/
        activation state -- those are owned by `shopify_connector_core`
        (which depends on this module and so can safely reference it, the
        reverse is not true) and are unaffected by this package-level gate
        one way or the other: a store that was disconnected before the
        pause stays disconnected after this call, and a store's own
        existing readiness/activation requirements still apply exactly as
        they did before Wave 5 -- this method only lifts the ADDITIONAL
        package-wide veto that Section 10's gates check, it does not grant
        any store a pass on its own pre-existing rules.
        """
        self.ensure_one()
        self._require_system_admin()
        integrity = self._apply_detected_state()
        if not integrity['healthy']:
            raise UserError(_(
                'Cannot resume: the Shopify Connector is still missing '
                '%s. Restore the suite before resuming.'
            ) % ', '.join(integrity['missing_standard_apps'] or integrity['missing_technical_modules']))
        if self.state != 'healthy':
            # Side cursor (see `_commit_via_side_cursor`): this resume must
            # survive even if something else in the same request fails
            # afterward -- an explicit resume the administrator just
            # confirmed must never silently revert.
            self._commit_via_side_cursor(self.id, {
                'state': 'healthy',
                'resumed_at': fields.Datetime.now(),
                'resumed_by_uid': self.env.uid,
                'audit_note': (
                    "Resumed explicitly by %s. Package integrity confirmed "
                    "healthy. Per-store readiness and activation still "
                    "govern whether any individual store may sync."
                ) % self.env.user.display_name,
            })
        return integrity

    def get_status_payload(self):
        """Read-only projection for a dashboard/banner: JSON-serializable,
        no secret, no PII -- module names and timestamps only.
        """
        self.ensure_one()
        return {
            'state': self.state,
            'missing_technical_modules': (
                self.missing_technical_modules.split(', ')
                if self.missing_technical_modules else []
            ),
            'missing_standard_apps': (
                self.missing_standard_apps.split(', ')
                if self.missing_standard_apps else []
            ),
            'paused_at': self.paused_at and fields.Datetime.to_string(self.paused_at),
            'resumed_at': self.resumed_at and fields.Datetime.to_string(self.resumed_at),
            'last_integrity_check': (
                self.last_integrity_check
                and fields.Datetime.to_string(self.last_integrity_check)
            ),
            'audit_note': self.audit_note or False,
        }
