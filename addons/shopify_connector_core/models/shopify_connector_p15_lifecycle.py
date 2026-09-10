"""Independent P15 activation lifecycle over the legacy connection state."""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..domain.p15_foundation import activation_transition
from .shopify_connector_job import BUSINESS_JOB_SOURCES


class ShopifyConnectorP15Lifecycle(models.Model):
    """Persist pause/resume/retire without aliasing disconnect."""

    _inherit = "shopify.connector.store"

    activation_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("paused", "Paused"),
            ("retired", "Retired"),
        ],
        required=True,
        readonly=True,
        default="draft",
        index=True,
    )
    activation_changed_at = fields.Datetime(readonly=True)
    activation_changed_by = fields.Many2one(
        "res.users", readonly=True, ondelete="set null",
    )
    retire_requested_at = fields.Datetime(readonly=True)
    retire_requested_by = fields.Many2one(
        "res.users", readonly=True, ondelete="set null",
    )
    retire_reason = fields.Char(readonly=True)

    def _p15_set_activation(self, target, *, reason=False):
        self.ensure_one()
        current = self.activation_state or "draft"
        try:
            activation_transition(current, target)
        except ValueError as exc:
            raise UserError(_(
                "Activation cannot move from %(current)s to %(target)s.",
                current=current,
                target=target,
            )) from exc
        if current == target:
            return False
        now = fields.Datetime.now()
        values = {
            "activation_state": target,
            "activation_changed_at": now,
            "activation_changed_by": self.env.uid,
        }
        if target == "retired":
            values.update({
                "retire_requested_at": now,
                "retire_requested_by": self.env.uid,
                "retire_reason": (reason or "Retired after disconnected quiescence.")[:255],
            })
        self._store_service_write("_lifecycle", values)
        self._create_lifecycle_audit_job(
            "Store activation changed from %s to %s%s."
            % (
                current,
                target,
                " (retire intent recorded)" if target == "retired" else "",
            )
        )
        return True

    def _p15_activation_command(self, operation, *, reason=False):
        """Return ``(status, message, generation)`` for one lifecycle intent."""

        self.ensure_one()
        state, generation = self._lock_store_for_lifecycle()
        self.invalidate_recordset(["activation_state", "disconnect_status"])
        current = self.activation_state or "draft"
        if operation == "pause":
            if state != "connected" or current != "active":
                return (
                    "blocked",
                    "Pause requires a connected active store; it does not disconnect the store.",
                    generation,
                )
            self._p15_set_activation("paused", reason=reason)
            return "completed", "Store paused; connection state was preserved.", generation
        if operation == "resume":
            if current == "retired":
                return "blocked", "A retired store cannot be resumed.", generation
            if state != "connected":
                return (
                    "blocked",
                    "Resume requires a connected store; reconnect first.",
                    generation,
                )
            if current == "active":
                return "completed", "Store is already active.", generation
            self._p15_set_activation("active", reason=reason)
            return "completed", "Store resumed; connection state was preserved.", generation
        if operation == "retire":
            if current == "retired":
                return "completed", "Store is already retired.", generation
            if state != "disconnected" or self.disconnect_status not in (
                "completed", "timed_out",
            ):
                return (
                    "blocked",
                    "Retire requires a safely disconnected store; disconnect and quiesce it first.",
                    generation,
                )
            leases = self.env["shopify.connector.call.lease"].sudo().search_count([
                ("store_id", "=", self.id),
            ])
            attempts, reconciliations = self._layer2_disconnect_blockers()
            if leases or attempts or reconciliations:
                return (
                    "blocked",
                    "Retire is blocked while connector evidence is still outstanding.",
                    generation,
                )
            self._p15_set_activation("retired", reason=reason)
            return "completed", "Retire intent recorded after safe disconnect.", generation
        raise UserError(_("Unsupported activation operation."))

    def action_activate(self):
        for store in self:
            if store.activation_state == "retired":
                raise UserError("A retired store cannot be activated.")
            if store.activation_state == "paused":
                raise UserError("Resume a paused store before activation.")
        result = super().action_activate()
        for store in self:
            store.invalidate_recordset(["activation_state"])
            if store.state == "connected" and store.activation_state != "active":
                store._p15_set_activation("active")
        return result

    def action_reconnect(self):
        if any(store.activation_state == "retired" for store in self):
            raise UserError("A retired store cannot be reconnected.")
        result = super().action_reconnect()
        for store in self:
            store.invalidate_recordset(["activation_state"])
            if store.state == "connected" and store.activation_state == "draft":
                store._p15_set_activation("active")
        return result


class ShopifyConnectorP15JobActivation(models.Model):
    """Keep the durable activation gate outside the legacy hotspot."""

    _inherit = "shopify.connector.job"

    @api.model
    def _p15_activation_allows_business_job(self, store):
        return getattr(store, "activation_state", "active") == "active"

    @api.model_create_multi
    def create(self, vals_list):
        Store = self.env["shopify.connector.store"]
        for values in vals_list:
            if values.get("job_source") not in BUSINESS_JOB_SOURCES:
                continue
            store = Store.browse(values.get("store_id")).exists()
            if not store or not self._p15_activation_allows_business_job(store):
                raise ValidationError(
                    "A business job cannot be created while the store "
                    "activation is paused or retired."
                )
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("state") == "running":
            Store = self.env["shopify.connector.store"]
            for job in self:
                source = vals.get("job_source", job.job_source)
                if source not in BUSINESS_JOB_SOURCES:
                    continue
                store = (
                    Store.browse(vals["store_id"])
                    if "store_id" in vals else job.store_id
                )
                if not self._p15_activation_allows_business_job(store):
                    raise ValidationError(
                        "This business job's store activation is not active "
                        "-- it cannot start."
                    )
        return super().write(vals)


class ShopifyConnectorP15DispatchActivation(models.AbstractModel):
    """Reject paused/retired business work at the final dispatch boundary."""

    _inherit = "shopify.connector.job.dispatch"

    @api.model
    def _invoke_handler(self, job):
        store = job.store_id
        if (
            job.job_source in BUSINESS_JOB_SOURCES
            and getattr(store, "activation_state", "active") != "active"
        ):
            job._transition_skipped(
                "Store activation is paused or retired immediately before "
                "dispatch -- skipped without invoking a handler."
            )
            return
        return super()._invoke_handler(job)


__all__ = ["ShopifyConnectorP15Lifecycle"]
