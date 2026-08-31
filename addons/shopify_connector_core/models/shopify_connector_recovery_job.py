"""Explicit P04 retry adapter over the accepted job retry service."""

from __future__ import annotations

from collections.abc import Mapping
from odoo import _, api, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..application.command_contracts import CommandEnvelope
from ..runtime.p04_recovery import RecoveryContractError, parse_run_ref
from .shopify_connector_recovery_commands import (
    _LEGACY_RETRY_STATES,
    _RecoveryContext,
    _Target,
)


_JOB_PAYLOAD_KEYS = frozenset((
    "target_ref", "job_ref", "job_id", "reason", "state_version",
))
class ShopifyConnectorRecoveryJobCommands(models.AbstractModel):
    """Versioned retry command; no arbitrary model/method dispatch."""

    _inherit = "shopify.connector.application.facade"

    @api.model
    def _recovery_job_payload(self, payload, *, endpoint):
        if not isinstance(payload, Mapping):
            raise ValidationError(_("The job command payload must be a mapping."))
        unknown = set(payload) - _JOB_PAYLOAD_KEYS
        if unknown:
            raise ValidationError(_("The job command contains unsupported fields."))
        refs = [
            payload[key] for key in ("target_ref", "job_ref", "job_id")
            if key in payload
        ]
        if len(refs) != 1:
            raise ValidationError(_("Exactly one target job reference is required."))
        ref = refs[0]
        if "job_id" in payload and (
            isinstance(ref, bool) or not isinstance(ref, int) or ref <= 0
        ):
            raise ValidationError(_("job_id must be a positive integer."))
        try:
            parse_run_ref(ref)
        except RecoveryContractError as exc:
            raise ValidationError(_("The job reference is invalid.")) from exc
        state_version = payload.get("state_version")
        if state_version is None or (
            isinstance(state_version, bool)
            or not isinstance(state_version, int)
            or state_version <= 0
        ):
            raise ValidationError(_("state_version must be positive."))
        reason = self._recovery_safe_reason(
            payload.get("reason"),
            required=endpoint == "cancel_job_v1",
        )
        return ref, state_version, reason

    @api.model
    def _recovery_command_from_job_input(
        self, command_or_ref, reason, state_version, endpoint,
    ):
        if not isinstance(command_or_ref, (CommandEnvelope, Mapping)):
            raise ValidationError(_(
                "A typed command envelope is required; positional recovery "
                "arguments are not accepted."
            ))
        if state_version is not None or reason not in (None, False, ""):
            raise ValidationError(_("Command arguments must be inside the payload."))
        context = self._recovery_parse_envelope(command_or_ref, endpoint)
        ref, payload_version, payload_reason = self._recovery_job_payload(
            context.payload, endpoint=endpoint,
        )
        return context, ref, payload_version, payload_reason

    @api.model
    def _recovery_target_version_for_command(self, target, endpoint):
        if endpoint == "cancel_job_v1" and target.run and not target.job:
            return self._recovery_run_state_version(target.run)
        return self._recovery_target_state_version(target)

    @api.model
    def _recovery_retry_or_cancel(self, command_or_ref, reason, state_version, endpoint):
        context, ref, expected_version, safe_reason = (
            self._recovery_command_from_job_input(
                command_or_ref, reason, state_version, endpoint,
            )
        )
        required_role = (
            "operator" if endpoint == "retry_job_v1" else "administrator"
        )
        self._recovery_require_role(required_role)
        target = self._recovery_target_from_ref(
            ref,
            store_id=context.envelope.store_id,
            action=(
                "retry_job" if endpoint == "retry_job_v1" else "cancel_job"
            ),
        )
        current_version = self._recovery_target_version_for_command(target, endpoint)
        if expected_version is not None and expected_version != current_version:
            return self._recovery_conflict(
                target, context.envelope, version=current_version,
            )
        if target.is_v2 and context.expected_configuration_generation is None:
            return self._recovery_result(
                "blocked",
                _("A V2 command must include the configuration generation."),
                envelope=context.envelope,
                store=target.store,
                run_ref=target.run_ref,
                conflict_version=current_version,
            )
        generation_conflict = self._recovery_check_generation(
            target,
            expected_connection=context.envelope.expected_generation,
            expected_configuration=context.expected_configuration_generation,
            envelope=context.envelope,
        )
        if generation_conflict:
            return self._recovery_conflict(
                target,
                context.envelope,
                version=current_version,
                message=_(
                    "The store or run generation changed; refresh before acting."
                ),
            )

        job = target.job
        if endpoint == "retry_job_v1":
            if self._recovery_command_audited(job, context.envelope.command_id):
                return self._recovery_result(
                    "duplicate",
                    _("This recovery command was already accepted."),
                    envelope=context.envelope,
                    store=target.store,
                    run_ref=target.run_ref,
                )
            if job._has_mutation_attempt_evidence():
                return self._recovery_result(
                    "blocked",
                    _(
                        "Mutation evidence requires remote-outcome verification; "
                        "it cannot be retried generically."
                    ),
                    envelope=context.envelope,
                    store=target.store,
                    run_ref=target.run_ref,
                    conflict_version=current_version,
                )
            if job.state not in _LEGACY_RETRY_STATES:
                return self._recovery_result(
                    "blocked",
                    _("This job has no currently returned safe retry action."),
                    envelope=context.envelope,
                    store=target.store,
                    run_ref=target.run_ref,
                    conflict_version=current_version,
                )
            before = job.state
            try:
                job.action_manual_retry()
            except AccessError:
                raise
            except UserError:
                job.invalidate_recordset()
                fresh = self._recovery_target_state_version(target)
                if fresh != current_version or job.state != "failed_retryable":
                    return self._recovery_conflict(
                        target, context.envelope, version=fresh,
                    )
                raise
            job.invalidate_recordset()
            self._recovery_audit_command(
                job, context.envelope, "retry_job", safe_reason, before, job.state,
            )
            return self._recovery_result(
                "accepted",
                _("The job was safely re-queued."),
                envelope=context.envelope,
                store=target.store,
                run_ref=target.run_ref,
            )
        return self._recovery_cancel_v2_or_legacy(
            target, context, safe_reason, expected_version, current_version,
        )

    @api.model
    def retry_job_v1(self, command):
        return self._recovery_retry_or_cancel(
            command, None, None, "retry_job_v1",
        )


__all__ = ["ShopifyConnectorRecoveryJobCommands"]
