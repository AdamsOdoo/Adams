"""SEC-3 (#197) connector-parent scope consistency.

Why this exists, stated plainly because the gap it closes is easy to miss.

The SEC-3 ownership model roots company in the STORE: every store-scoped row
carries a stored ``company_id`` related to ``store_id.company_id``, and a
fail-closed global record rule filters on it. That is sufficient for a row
whose only ancestor is its own store.

It is NOT sufficient for a row that also points at another connector row,
because **one company may own several stores**. Two stores in the same company
pass every company check while belonging to different Shopify shops. A job log
whose ``store_id`` is store A and whose ``job_id`` belongs to store B is
company-consistent and store-inconsistent, and nothing in the company model
notices. Cross-store bleed inside one company is a real defect: it mixes two
shops' operational records together.

So there are two distinct obligations here:

  * **New and updated rows** must be refused at the ORM boundary. That is
    ``_sec3_check_parent_scope``, invoked from a per-model ``@api.constrains``.
    It is a constraint rather than a record rule on purpose -- constraints fire
    under ``sudo()``, and every connector write path uses ``sudo()`` somewhere.

  * **Historic rows** written before the constraint existed cannot be fixed by
    a constraint, and must not be guessed at. Re-homing a row to its parent's
    store, or its parent to the row's store, would silently rewrite operational
    history and could just as easily be the wrong half. Instead the upgrade scan
    QUARANTINES them: ``sec3_scope_quarantined`` is set, the fail-closed record
    rules exclude quarantined rows from every read shape, and the exact ids are
    logged for an administrator. Nothing is deleted, nothing is re-homed, and
    the rows stay in the database for remediation.

A domain cannot compare two of a record's own fields, which is why the
quarantine is a stored boolean rather than a cleverer rule: there is no
``('store_id', '=', 'job_id.store_id')``. The boolean is the only way to make
"this row disagrees with its parent" expressible in a record rule at all.

Upstream ground truth (DEC-041 D1), odoo/odoo@19.0 ``30bde9ff``, read
2026-07-25:
  * ``odoo/addons/base/models/ir_rule.py::_compute_global`` -- a rule with no
    ``groups`` is global and is AND-ed with every other rule on the model, so
    adding a leaf here cannot be re-opened by a permissive group rule.
  * ``odoo/orm/models.py`` L4009 ``_check_company`` -- Odoo's own company
    consistency check compares COMPANIES only. It cannot express the
    same-store requirement, which is why these constraints exist alongside
    ``_check_company_auto`` rather than instead of it.

No Shopify request or mutation occurs anywhere in this file.
"""

import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.sql import table_exists

_logger = logging.getLogger(__name__)


class ShopifyConnectorScopeMixin(models.AbstractModel):
    """Same-store consistency for connector-to-connector relations."""

    _name = 'shopify.connector.scope.mixin'
    _description = 'Shopify Connector SEC-3 Scope Consistency Mixin'

    # Set ONLY by the upgrade scan below and cleared ONLY by the administrative
    # remediation action. Never caller input: a writable quarantine flag would
    # let the very rows it hides unhide themselves.
    sec3_scope_quarantined = fields.Boolean(
        string='SEC-3 Scope Quarantined',
        default=False,
        index=True,
        readonly=True,
        help='Set when this row disagrees with a connector parent about which '
             'store or company it belongs to. Quarantined rows are excluded '
             'from every read by the SEC-3 record rules and must be resolved '
             'by an administrator; nothing is re-homed automatically.',
    )

    # ------------------------------------------------------------------
    # Declaration
    # ------------------------------------------------------------------

    @api.model
    def _sec3_parent_scope_relations(self):
        """Connector relations this model must agree with.

        Returns a tuple of ``(field_name, axis)`` where ``axis`` is:

          * ``'store'`` -- both sides carry ``store_id`` and must name the SAME
            store. Use this whenever it is available: it is strictly stronger
            than the company axis, because one company may own several stores.
          * ``'company'`` -- this side has no store of its own (or the parent
            has none), so the strongest available agreement is the company.

        Empty by default: a model with no connector parent has nothing to
        disagree with.
        """
        return ()

    def _sec3_scope_of(self, record):
        """The ``(store_id, company_id)`` a record claims. ``0`` means unset."""
        if not record:
            return (0, 0)
        store = getattr(record, 'store_id', False)
        company = getattr(record, 'company_id', False)
        return (store.id if store else 0, company.id if company else 0)

    # ------------------------------------------------------------------
    # Write-side enforcement
    # ------------------------------------------------------------------

    def _sec3_check_parent_scope(self):
        """Refuse a row that disagrees with a connector parent.

        Called from each concrete model's ``@api.constrains``. The field names
        are declared there rather than here because Odoo resolves
        ``@api.constrains`` names at class definition time and cannot read them
        from a method.
        """
        relations = self._sec3_parent_scope_relations()
        if not relations:
            return
        # A declared relation may be contributed by a module that is not
        # installed: `order.binding.fulfillment_binding_id` is added by the
        # fulfillment module onto a model the sale module owns. The
        # declaration is written where the relation logically belongs, and the
        # check skips what the running registry does not have.
        present = [
            (name, axis) for name, axis in relations if name in self._fields
        ]
        if not present:
            return
        for record in self:
            own_store, own_company = self._sec3_scope_of(record)
            for field_name, axis in present:
                parent = record[field_name]
                if not parent:
                    continue
                parent_store, parent_company = self._sec3_scope_of(parent)
                if axis == 'store' and own_store and parent_store:
                    if own_store != parent_store:
                        raise ValidationError(
                            '%s and its %s must belong to the same Shopify '
                            'store. One company may own several stores, so '
                            'agreeing on the company is not enough.' % (
                                self._description, field_name,
                            )
                        )
                    continue
                # Company axis: either this side or the parent has no store of
                # its own, so the company is the strongest available agreement.
                if own_company and parent_company and own_company != parent_company:
                    raise ValidationError(
                        '%s and its %s must belong to the same company.' % (
                            self._description, field_name,
                        )
                    )

    # ------------------------------------------------------------------
    # Historic rows: deterministic, non-guessing quarantine
    # ------------------------------------------------------------------

    @api.model
    def _sec3_quarantine_scope_mismatches(self):
        """Quarantine historic rows that disagree with a connector parent.

        Runs from each concrete model's ``init()``, i.e. on every install and
        every ``-u`` update, so a database upgraded from before SEC-3 is swept
        exactly once per update rather than depending on anyone remembering a
        migration script.

        Deliberately does NOT decide which half is wrong. Re-homing the row to
        the parent's store, or the parent to the row's store, are both
        plausible and both destructive; picking one would rewrite operational
        history on a guess. The row is hidden and named in the log instead.
        """
        # A later addon can load the current Python registry while an older
        # installed core module is deliberately left untouched. In that
        # W2-only compatibility probe, additive core models are known to the
        # registry but their tables do not exist yet. The core upgrade owns
        # creating them; an init-time historic-row sweep must not query them.
        if not table_exists(self.env.cr, self._table):
            return 0
        relations = self._sec3_parent_scope_relations()
        if not relations:
            return 0
        quarantined = self.browse()
        for field_name, axis in relations:
            field = self._fields.get(field_name)
            if field is None or not field.relational:
                continue
            candidates = self.sudo().search([
                (field_name, '!=', False),
                ('sec3_scope_quarantined', '=', False),
            ])
            for record in candidates:
                own_store, own_company = self._sec3_scope_of(record)
                parent_store, parent_company = self._sec3_scope_of(
                    record[field_name])
                if axis == 'store' and own_store and parent_store:
                    mismatch = own_store != parent_store
                else:
                    mismatch = bool(
                        own_company and parent_company
                        and own_company != parent_company
                    )
                if mismatch:
                    _logger.warning(
                        'SEC-3 scope quarantine: %s id=%s claims store=%s '
                        'company=%s but its %s claims store=%s company=%s. '
                        'The row is hidden from every read until an '
                        'administrator resolves it; nothing was re-homed.',
                        self._name, record.id, own_store or None,
                        own_company or None, field_name,
                        parent_store or None, parent_company or None,
                    )
                    quarantined |= record
        if quarantined:
            # Written in SQL, deliberately. This runs from `init()`, an
            # install/upgrade hook, and several of the models it sweeps are
            # append-only evidence whose `write()` refuses everything outside a
            # named service surface (`shopify.connector.mutation.attempt` is
            # the clearest case). Opening a write surface so a maintenance flag
            # can be set would widen the evidence contract to solve a
            # bookkeeping problem. The flag is not business data and is never
            # caller input, so the upgrade path sets it directly and
            # invalidates the cache.
            self.env.cr.execute(
                'UPDATE %s SET sec3_scope_quarantined = TRUE WHERE id IN %%s'
                % self._table,
                (tuple(quarantined.ids),),
            )
            self.invalidate_model(['sec3_scope_quarantined'])
            self._sec3_after_quarantine_flag_update(quarantined.ids, True)
        return len(quarantined)

    @api.model
    def _sec3_after_quarantine_flag_update(self, ids, quarantined):
        """Hook: the quarantine flag of ``ids`` was just set to ``quarantined``.

        Both quarantine writers (the sweep above and the release below) run
        in SQL by design, so a model whose flag is mirrored onto another
        table cannot rely on ``write()`` to propagate it. A concrete model
        that maintains such a mirror (e.g. the sale-order projection of the
        order binding) extends this hook and updates its mirror in the SAME
        transaction. Default: nothing to propagate.
        """
        return None

    def action_sec3_release_scope_quarantine(self):
        """Administrative remediation: clear the quarantine once resolved.

        Gated on the Connector Administrator group and re-verified: releasing a
        row that still disagrees with its parent would put the leak straight
        back, so the check is re-run rather than trusted.
        """
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may release a SEC-3 '
                'scope quarantine.'
            )
        for record in self:
            if not record.sec3_scope_quarantined:
                raise UserError('This record is not quarantined.')
        # Re-verify BEFORE clearing. `_sec3_check_parent_scope` raises if the
        # disagreement is still there.
        self.sudo()._sec3_check_parent_scope()
        # SQL for the same reason the sweep uses it: several quarantinable
        # models are append-only evidence with a closed `write()` surface.
        self.env.cr.execute(
            'UPDATE %s SET sec3_scope_quarantined = FALSE WHERE id IN %%s'
            % self._table,
            (tuple(self.ids),),
        )
        self.invalidate_model(['sec3_scope_quarantined'])
        self._sec3_after_quarantine_flag_update(self.ids, False)
        return True
