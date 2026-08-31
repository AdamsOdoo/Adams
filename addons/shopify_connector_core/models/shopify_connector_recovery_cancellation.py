"""Administrator-gated P04 cancellation adapter.

Cancellation is a request for quiescence, not a claim that an in-flight
remote operation was undone.  The run service records the request; only
queued children with no mutation evidence are settled immediately.  Running
or uncertain work remains visible for the existing runtime/finalization or
mutation-verification boundary.
"""

from __future__ import annotations

from odoo import _, api, models
from odoo.exceptions import AccessError, UserError

from .shopify_connector_recovery_commands import _Target

_CANCELLABLE_STATES = frozenset(("draft", "queued", "retry_waiting"))
_MAX_CHILDREN_PER_CANCEL = 100
_RUN_STATE_VERSION_FIELDS = (
    "state", "cancel_requested_at", "cancel_reason", "write_date",
)


class ShopifyConnectorRecoveryCancellation(models.AbstractModel):
    """Named cancellation implementation; no generic transition API."""

    _inherit = "shopify.connector.application.facade"

    @api.model
    def _recovery_run_state_version(self, run):
        return self._recovery_ui()._state_version(run, _RUN_STATE_VERSION_FIELDS)

    @api.model
    def _recovery_lock_cancel_scope(self, run, store):
        """Lock cancellable job roots before the run, without waiting on claims.

        Claim/finalize owns a job before it owns the run.  Cancellation follows
        that same order and skips a job already owned by a worker; the durable
        run request still makes that worker settle at its normal boundary.
        """
        self.env.cr.execute(
            """
                SELECT id
                  FROM shopify_connector_job
                 WHERE run_id = %s
                   AND store_id = %s
                   AND company_id = %s
                   AND state IN %s
                   AND superseded_by_job_id IS NULL
                 ORDER BY id
                 LIMIT %s
                 FOR UPDATE SKIP LOCKED
            """,
            [run.id, store.id, self.env.company.id,
             tuple(sorted(_CANCELLABLE_STATES)),
             _MAX_CHILDREN_PER_CANCEL + 1],
        )
        child_ids = tuple(row[0] for row in self.env.cr.fetchall())
        self.env.cr.execute(
            """SELECT id FROM shopify_connector_run
                 WHERE id = %s AND store_id = %s AND company_id = %s
                 FOR UPDATE""",
            [run.id, store.id, self.env.company.id],
        )
        if not self.env.cr.fetchone():
            return ()
        return child_ids

    @api.model
    def _recovery_cancel_v2_or_legacy(
        self, target, context, reason, expected_version, current_version,
    ):
        if target.is_v2:
            return self._recovery_cancel_v2_run(
                target, context, reason, expected_version,
            )

        job = target.job
        if job.state not in _CANCELLABLE_STATES:
            return self._recovery_result(
                "blocked",
                _(
                    "A running or terminal job must settle at its service "
                    "boundary."
                ),
                envelope=context.envelope,
                store=target.store,
                run_ref=target.run_ref,
                conflict_version=current_version,
            )
        before = job.state
        job.action_cancel(reason)
        job.invalidate_recordset()
        self._recovery_audit_command(
            job,
            context.envelope,
            "cancel_job",
            reason,
            before,
            job.state,
        )
        return self._recovery_result(
            "accepted",
            _("The job cancellation was recorded."),
            envelope=context.envelope,
            store=target.store,
            run_ref=target.run_ref,
        )

    @api.model
    def _recovery_cancel_v2_run(self, target, context, reason, expected_version):
        run = target.run or (target.job and target.job.run_id)
        if not run:
            return self._recovery_result(
                "blocked",
                _("The V2 cancellation run is not available."),
                envelope=context.envelope,
                store=target.store,
            )
        child_ids = self._recovery_lock_cancel_scope(run, target.store)
        run.invalidate_recordset()
        current_run_version = self._recovery_run_state_version(run)
        if expected_version is not None and expected_version != current_run_version:
            return self._recovery_conflict(
                target,
                context.envelope,
                version=current_run_version,
            )
        if run.cancel_requested_at:
            return self._recovery_result(
                "duplicate",
                _("Cancellation was already requested for this run."),
                envelope=context.envelope,
                store=target.store,
                run_ref="run:%d" % run.id,
                conflict_version=current_run_version,
            )

        # This is the sole run cancellation write.  It stores actor, time and
        # redacted reason through the accepted service, and intentionally does
        # not force a terminal run state while a worker may still be active.
        run._request_cancel_service(reason)

        Job = self.env["shopify.connector.job"]
        children = Job.browse(child_ids).exists().sorted("id")
        settled = 0
        pending_running = Job.search_count(
            [
                ("run_id", "=", run.id),
                ("store_id", "=", target.store.id),
                ("company_id", "=", self.env.company.id),
                ("state", "=", "running"),
                ("superseded_by_job_id", "=", False),
            ]
        )
        protected = 0
        for child in children[:_MAX_CHILDREN_PER_CANCEL]:
            child.invalidate_recordset()
            if (
                child.run_id != run
                or child.store_id != target.store
                or child.company_id != self.env.company
                or child.state not in _CANCELLABLE_STATES
                or child.superseded_by_job_id
            ):
                protected += 1
                continue
            # A mutation-evidence-linked child is never generically cancelled,
            # even when its physical state is queued.  Its accepted mutation
            # service owns the eventual verification decision.
            if child._has_mutation_attempt_evidence():
                protected += 1
                continue
            before = child.state
            try:
                child.action_cancel(reason)
            except (AccessError, UserError):  # Odoo race boundary; no blind retry.
                # The request itself is durable.  A concurrent state change or
                # ACL/service refusal leaves the child for its owner boundary.
                protected += 1
                continue
            child.invalidate_recordset()
            self._recovery_audit_command(
                child,
                context.envelope,
                "cancel_job",
                reason,
                before,
                child.state,
            )
            settled += 1
        remaining_queued = Job.search_count(
            [
                ("run_id", "=", run.id),
                ("store_id", "=", target.store.id),
                ("company_id", "=", self.env.company.id),
                ("state", "in", tuple(_CANCELLABLE_STATES)),
                ("superseded_by_job_id", "=", False),
            ]
        )
        if len(children) > _MAX_CHILDREN_PER_CANCEL:
            # The count is deliberately bounded; report that more work needs
            # the same run-level request without scanning an unbounded queue.
            remaining_queued = max(1, int(remaining_queued))
        return self._recovery_result(
            "accepted",
            _(
                "Cancellation was requested; queued read work was settled "
                "where safe."
            ),
            envelope=context.envelope,
            store=target.store,
            run_ref="run:%d" % run.id,
            pending={
                "settled": settled,
                "running": pending_running,
                "protected": protected,
                "queued": remaining_queued,
            },
        )

    @api.model
    def cancel_job_v1(self, command):
        return self._recovery_retry_or_cancel(
            command,
            None,
            None,
            "cancel_job_v1",
        )


__all__ = ["ShopifyConnectorRecoveryCancellation"]
