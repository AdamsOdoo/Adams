"""Bounded P04 attention command adapter over accepted services only."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from uuid import UUID

from odoo import _, api, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..application.command_contracts import CommandEnvelope, CommandResult
from ..domain.immutability import to_plain
from ..domain.states import Role
from ..runtime.p04_recovery import (
    ACTION_REQUIRED_ROLE,
    AttentionCommand,
    RecoveryContractError,
    parse_run_ref,
    require_provider_action,
)
from ..tools.redaction import redact
from .shopify_connector_recovery_command_context import _RecoveryContext, _Target

_COMMAND_NAMES = frozenset((
    "resolve_attention_v1",
    "retry_job_v1",
    "cancel_job_v1",
))
_ENVELOPE_KEYS = frozenset((
    "contract_version",
    "command_id",
    "command_name",
    "store_id",
    "company_id",
    "expected_generation",
    "expected_configuration_generation",
    "actor_uid",
    "trigger",
    "requested_at",
    "payload",
))
_REASON_LIMIT = 512
_LEGACY_RETRY_STATES = frozenset(("failed_retryable",))
_STATE_VERSION_FIELDS = (
    "state", "error_class", "manual_review_subreason", "write_date",
)


class ShopifyConnectorRecoveryCommands(models.AbstractModel):
    _inherit = "shopify.connector.application.facade"

    @api.model
    def _recovery_parse_datetime(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(_("The command timestamp is invalid."))
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("The command timestamp is invalid.")) from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValidationError(_("The command timestamp must include UTC."))
        parsed = parsed.astimezone(timezone.utc)
        return parsed

    @api.model
    def _recovery_nonnegative(self, value, field_name):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValidationError(
                _("%(field)s must be a non-negative integer.", field=field_name)
            )
        return value

    @api.model
    def _recovery_parse_envelope(self, command, expected_name):
        config_generation = None
        if isinstance(command, CommandEnvelope):
            envelope = command
            payload = dict(envelope.payload)
        elif isinstance(command, Mapping):
            unknown = set(command) - _ENVELOPE_KEYS
            if unknown:
                raise ValidationError(_(
                    "Command envelope contains unsupported fields: %(fields)s",
                    fields=", ".join(sorted(str(item) for item in unknown)),
                ))
            required = {
                "contract_version", "command_id", "command_name", "store_id",
                "company_id", "expected_generation", "actor_uid", "trigger",
                "requested_at", "payload",
            }
            missing = required - set(command)
            if missing:
                raise ValidationError(_(
                    "Command envelope is missing: %(fields)s",
                    fields=", ".join(sorted(missing)),
                ))
            raw_payload = command.get("payload")
            if not isinstance(raw_payload, Mapping):
                raise ValidationError(_("Command payload must be a mapping."))
            try:
                envelope = CommandEnvelope(
                    contract_version=command["contract_version"],
                    command_id=(
                        command["command_id"]
                        if isinstance(command["command_id"], UUID)
                        else UUID(str(command["command_id"]))
                    ),
                    command_name=command["command_name"],
                    store_id=command["store_id"],
                    company_id=command["company_id"],
                    expected_generation=command["expected_generation"],
                    actor_uid=command["actor_uid"],
                    trigger=command["trigger"],
                    requested_at=self._recovery_parse_datetime(
                        command["requested_at"]
                    ),
                    payload=raw_payload,
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValidationError(_("The command envelope is invalid.")) from exc
            if "expected_configuration_generation" in command:
                config_generation = self._recovery_nonnegative(
                    command["expected_configuration_generation"],
                    "expected_configuration_generation",
                )
            payload = dict(envelope.payload)
        else:
            raise ValidationError(_("A typed command envelope is required."))

        if envelope.command_name != expected_name:
            raise ValidationError(_("The command name does not match the endpoint."))
        if expected_name not in _COMMAND_NAMES:
            raise ValidationError(_("The recovery command is not supported."))
        if envelope.company_id != self.env.company.id:
            raise AccessError(_("The command company must be the active company."))
        if envelope.trigger not in ("user", "system"):
            raise AccessError(_("Only an interactive recovery command is allowed."))
        if envelope.trigger == "system" and not self.env.su:
            raise AccessError(_(
                "System-triggered recovery commands require a trusted service."
            ))
        if envelope.trigger == "user" and envelope.actor_uid != self.env.uid:
            raise AccessError(_("The command actor could not be verified."))
        return _RecoveryContext(envelope, config_generation, payload)

    @api.model
    def _recovery_safe_reason(self, value, *, required):
        if value is None or value is False or value == "":
            if required:
                raise ValidationError(_("A non-empty reason is required."))
            return None
        if not isinstance(value, str):
            raise ValidationError(_("The reason must be text."))
        value = value.strip()
        if not value:
            if required:
                raise ValidationError(_("A non-empty reason is required."))
            return None
        if len(value) > _REASON_LIMIT:
            raise ValidationError(_("The reason is too long."))
        return redact(value)[:_REASON_LIMIT]

    @api.model
    def _recovery_result(
        self,
        status,
        message,
        *,
        envelope=None,
        store=None,
        run_ref=None,
        attention_ref=None,
        conflict_version=None,
        pending=None,
    ):
        result = CommandResult(
            status=status,
            run_ref=run_ref,
            attention_ref=attention_ref,
            message=message,
            conflict_version=conflict_version,
        ).as_dict()
        if envelope is not None:
            result["command_id"] = str(envelope.command_id)
        if store is not None:
            result["store_id"] = store.id
            result["connection_generation"] = int(
                store.connection_generation or 0
            )
            settings = self._recovery_settings(store)
            result["configuration_generation"] = int(
                settings.configuration_generation if settings else 0
            )
        if pending:
            result["pending"] = {
                key: int(value) for key, value in pending.items()
                if isinstance(key, str) and isinstance(value, int)
                and not isinstance(value, bool) and value >= 0
            }
        return to_plain(result)

    @api.model
    def _recovery_ui(self):
        return self.env["shopify.connector.ui.facade"]

    @api.model
    def _recovery_require_role(self, role):
        current = self._recovery_ui()._current_role()
        required = {
            "operator": Role.OPERATOR,
            "administrator": Role.ADMINISTRATOR,
        }.get(role)
        if required is None:
            raise AccessError(_("The recovery role is not supported."))
        if required == Role.OPERATOR:
            if current not in (Role.OPERATOR, Role.ADMINISTRATOR):
                raise AccessError(_("Your connector role cannot retry this job."))
        elif current != Role.ADMINISTRATOR:
            raise AccessError(_("Only a Connector Administrator may do this."))
        return current

    @api.model
    def _recovery_settings(self, store):
        Settings = self.env["shopify.connector.store.settings"]
        return Settings.search(
            [
                ("id", "!=", False),
                ("store_id", "=", store.id),
                ("company_id", "=", store.company_id.id),
            ],
            limit=1,
        )

    @api.model
    def _recovery_generation(self, store):
        connection = store.connection_generation or 0
        if isinstance(connection, bool) or not isinstance(connection, int):
            raise ValidationError(_("The store connection generation is invalid."))
        settings = self._recovery_settings(store)
        configuration = settings.configuration_generation if settings else 0
        if isinstance(configuration, bool) or not isinstance(configuration, int):
            raise ValidationError(_("The configuration generation is invalid."))
        if connection < 0 or configuration < 0:
            raise ValidationError(_("The store generation cannot be negative."))
        return int(connection), int(configuration), settings

    @api.model
    def _recovery_check_generation(
        self,
        target,
        *,
        expected_connection,
        expected_configuration,
        envelope=None,
    ):
        store = target.store
        current_connection, current_configuration, settings = (
            self._recovery_generation(store)
        )
        if expected_connection != current_connection:
            return current_connection, current_configuration, settings
        if (
            expected_configuration is not None
            and expected_configuration != current_configuration
        ):
            return current_connection, current_configuration, settings
        if target.is_v2:
            if not settings:
                return current_connection, current_configuration, settings
            job = target.job
            run = target.run or getattr(job, "run_id", False)
            if not job:
                run_snapshot = (
                    getattr(run, "expected_connection_generation", None),
                    getattr(run, "expected_configuration_generation", None),
                )
                if (
                    any(
                        isinstance(value, bool) or not isinstance(value, int)
                        or value < 0 for value in run_snapshot
                    )
                    or run_snapshot != (
                        current_connection,
                        current_configuration,
                    )
                    or expected_configuration is None
                ):
                    return current_connection, current_configuration, settings
                return None
            snapshots = (
                getattr(job, "expected_connection_generation", None),
                getattr(job, "expected_configuration_generation", None),
                getattr(run, "expected_connection_generation", None),
                getattr(run, "expected_configuration_generation", None),
            )
            if any(
                isinstance(value, bool) or not isinstance(value, int)
                or value < 0 for value in snapshots
            ):
                return current_connection, current_configuration, settings
            if snapshots != (
                current_connection,
                current_configuration,
                current_connection,
                current_configuration,
            ):
                return current_connection, current_configuration, settings
            if expected_configuration is None:
                return current_connection, current_configuration, settings
        return None

    @api.model
    def _recovery_target_from_ref(self, ref, *, store_id=None, action=None):
        try:
            kind, record_id = parse_run_ref(ref)
        except RecoveryContractError as exc:
            raise ValidationError(_("The job reference is invalid.")) from exc

        if kind == "job":
            Job = self.env["shopify.connector.job"]
            domain = [
                ("id", "=", record_id),
                ("company_id", "=", self.env.company.id),
            ]
            if store_id is not None:
                domain.append(("store_id", "=", store_id))
            job = Job.search(domain, limit=1)
            if not job:
                raise AccessError(_("The requested job is not available."))
            store = self._recovery_ui()._require_store(job.store_id.id)
            run = getattr(job, "run_id", False)
            if run and store_id is not None and run.store_id.id != store_id:
                raise AccessError(_("The run is outside the requested store."))
            return _Target(job=job, run=run, store=store)

        Run = self.env["shopify.connector.run"]
        domain = [
            ("id", "=", record_id),
            ("company_id", "=", self.env.company.id),
        ]
        if store_id is not None:
            domain.append(("store_id", "=", store_id))
        run = Run.search(domain, limit=1)
        if not run:
            raise AccessError(_("The requested run is not available."))
        store = self._recovery_ui()._require_store(run.store_id.id)
        if run.store_id.company_id != self.env.company:
            raise AccessError(_("The run is outside the active company."))

        Job = self.env["shopify.connector.job"]
        domain = [
            ("run_id", "=", run.id),
            ("store_id", "=", store.id),
            ("company_id", "=", self.env.company.id),
            ("superseded_by_job_id", "=", False),
        ]
        if action == "retry_job":
            domain.append(("state", "in", tuple(_LEGACY_RETRY_STATES)))
        elif action == "cancel_job":
            return _Target(job=False, run=run, store=store)
        children = Job.search(domain, order="id asc", limit=2)
        if len(children) != 1:
            if not children:
                raise UserError(_("The run has no eligible child for this command."))
            raise UserError(_(
                "The run has multiple eligible children; address one job at a time."
            ))
        return _Target(job=children, run=run, store=store)

    @api.model
    def _recovery_target_state_version(self, target):
        record = target.job
        return self._recovery_ui()._state_version(record, _STATE_VERSION_FIELDS)

    @api.model
    def _recovery_command_audited(self, job, command_id):
        if not job or not command_id:
            return False
        Log = self.env["shopify.connector.job.log"]
        return bool(Log.search([
            ("job_id", "=", job.id),
            ("event_type", "=", "note"),
            ("payload_snapshot", "ilike", str(command_id)),
        ], limit=1))

    @api.model
    def _recovery_audit_command(
        self, job, envelope, action_key, reason, before_state, after_state,
    ):
        if not job:
            return
        payload = json.dumps({
            "command_id": str(envelope.command_id),
            "command_name": envelope.command_name,
            "action_key": action_key,
            "actor_uid": int(self.env.uid),
            "reason": redact(reason)[:_REASON_LIMIT] if reason else None,
            "before_state": before_state,
            "after_state": after_state,
        }, sort_keys=True, separators=(",", ":"))
        self.env["shopify.connector.job.log"]._system_append(
            job,
            "note",
            "Recovery command accepted and delegated to the sanctioned service.",
            payload_snapshot=payload,
            from_state=before_state,
            to_state=after_state,
        )

    @api.model
    def _recovery_conflict(
        self, target, envelope, *, attention_ref=None, version=None, message=None,
    ):
        return self._recovery_result(
            "conflict",
            message or _("The item changed; refresh before acting."),
            envelope=envelope,
            store=target.store,
            run_ref=target.run_ref,
            attention_ref=attention_ref,
            conflict_version=version,
        )

    @api.model
    def resolve_attention_v1(self, command):
        context = self._recovery_parse_envelope(command, "resolve_attention_v1")
        try:
            recovery = AttentionCommand.from_mapping(context.payload)
        except RecoveryContractError as exc:
            raise ValidationError(_("The recovery command payload is invalid.")) from exc
        store = self._recovery_ui()._require_store(context.envelope.store_id)
        if store.company_id.id != context.envelope.company_id:
            raise AccessError(_("The attention item is outside the active company."))

        current_connection, current_configuration, _settings = self._recovery_generation(store)
        if context.envelope.expected_generation != current_connection:
            return self._recovery_result(
                "conflict",
                _("The store connection changed; refresh before acting."),
                envelope=context.envelope,
                store=store,
                attention_ref=recovery.item_ref,
                conflict_version=current_connection,
            )
        if (
            context.expected_configuration_generation is not None
            and context.expected_configuration_generation != current_configuration
        ):
            return self._recovery_result(
                "conflict",
                _("The store configuration changed; refresh before acting."),
                envelope=context.envelope,
                store=store,
                attention_ref=recovery.item_ref,
                conflict_version=current_configuration,
            )

        now = self._recovery_ui()._now_utc()
        row = self._recovery_ui()._load_attention_source(
            store, recovery.provider, recovery.source_id, now,
        )
        if row is None:
            return self._recovery_result(
                "conflict",
                _("That attention item is no longer available."),
                envelope=context.envelope,
                store=store,
                attention_ref=recovery.item_ref,
            )
        dto, meta = row
        if dto.item_ref != recovery.item_ref or dto.state_version != recovery.state_version:
            return self._recovery_result(
                "conflict",
                _("That attention item changed; refresh before acting."),
                envelope=context.envelope,
                store=store,
                run_ref=dto.run_ref,
                attention_ref=dto.item_ref,
                conflict_version=dto.state_version,
            )
        if not any(action.key == recovery.action_key for action in dto.allowed_actions):
            return self._recovery_result(
                "blocked",
                _("This action is not available for the current item."),
                envelope=context.envelope,
                store=store,
                run_ref=dto.run_ref,
                attention_ref=dto.item_ref,
                conflict_version=dto.state_version,
            )
        try:
            require_provider_action(recovery.provider, recovery.action_key)
        except RecoveryContractError as exc:
            return self._recovery_result(
                "blocked",
                _("This provider has no approved recovery service."),
                envelope=context.envelope,
                store=store,
                run_ref=dto.run_ref,
                attention_ref=dto.item_ref,
                conflict_version=dto.state_version,
            )

        if recovery.action_key not in ACTION_REQUIRED_ROLE:
            return self._recovery_result(
                "blocked",
                _("This action is navigation-only or has no approved write service."),
                envelope=context.envelope,
                store=store,
                run_ref=dto.run_ref,
                attention_ref=dto.item_ref,
                conflict_version=dto.state_version,
            )
        required_role = ACTION_REQUIRED_ROLE.get(recovery.action_key)
        self._recovery_require_role(required_role)
        record = meta.get("record")
        if not record:
            return self._recovery_result(
                "blocked",
                _("The recovery source is not actionable."),
                envelope=context.envelope,
                store=store,
                attention_ref=dto.item_ref,
                conflict_version=dto.state_version,
            )
        target = _Target(
            job=(record if meta.get("kind") == "job" else getattr(record, "job_id", False)),
            run=(getattr(record, "run_id", False) if meta.get("kind") == "job" else False),
            store=store,
        )
        if target.is_v2 and context.expected_configuration_generation is None:
            return self._recovery_result(
                "blocked",
                _("A V2 recovery command must include the configuration generation."),
                envelope=context.envelope,
                store=store,
                run_ref=dto.run_ref,
                attention_ref=dto.item_ref,
                conflict_version=dto.state_version,
            )
        if recovery.provider == "manual_review_job":
            job = record
            if job._has_mutation_attempt_evidence():
                return self._recovery_result(
                    "blocked",
                    _("Mutation evidence requires remote-outcome verification."),
                    envelope=context.envelope,
                    store=store,
                    run_ref="job:%d" % job.id,
                    attention_ref=dto.item_ref,
                    conflict_version=dto.state_version,
                )
            expected_configuration = context.expected_configuration_generation
            generation_conflict = self._recovery_check_generation(
                target,
                expected_connection=context.envelope.expected_generation,
                expected_configuration=expected_configuration,
                envelope=context.envelope,
            )
            if generation_conflict:
                return self._recovery_conflict(
                    target,
                    context.envelope,
                    attention_ref=dto.item_ref,
                    version=dto.state_version,
                    message=_("The store or run generation changed; refresh before acting."),
                )
            before = job.state
            try:
                if recovery.action_key == "retry_job":
                    if job.state != "failed_retryable":
                        return self._recovery_result(
                            "blocked",
                            _("This job no longer has a safe retry."),
                            envelope=context.envelope,
                            store=store,
                            run_ref=target.run_ref,
                            attention_ref=dto.item_ref,
                            conflict_version=dto.state_version,
                        )
                    job.action_manual_retry()
                elif recovery.action_key == "resolve_manual_review":
                    if job.state != "blocked_manual_review":
                        return self._recovery_result(
                            "blocked",
                            _("This review is no longer open."),
                            envelope=context.envelope,
                            store=store,
                            run_ref=target.run_ref,
                            attention_ref=dto.item_ref,
                            conflict_version=dto.state_version,
                        )
                    job.action_resolve_manual_review()
                else:
                    return self._recovery_result(
                        "blocked",
                        _("This job action is not approved."),
                        envelope=context.envelope,
                        store=store,
                        run_ref=target.run_ref,
                        attention_ref=dto.item_ref,
                        conflict_version=dto.state_version,
                    )
            except AccessError:
                raise
            except UserError:
                job.invalidate_recordset()
                current = self._recovery_target_state_version(target)
                if current != recovery.state_version or job.state not in (
                    "failed_retryable", "blocked_manual_review",
                ):
                    return self._recovery_conflict(
                        target,
                        context.envelope,
                        attention_ref=dto.item_ref,
                        version=current,
                    )
                raise
            job.invalidate_recordset()
            self._recovery_audit_command(
                job,
                context.envelope,
                recovery.action_key,
                recovery.reason,
                before,
                job.state,
            )
            return self._recovery_result(
                "accepted",
                _("The recovery action was accepted."),
                envelope=context.envelope,
                store=store,
                run_ref=target.run_ref,
            )

        if recovery.provider == "mutation_uncertainty":
            if recovery.action_key != "resolve_mutation":
                return self._recovery_result(
                    "blocked",
                    _("An uncertain mutation cannot use a generic recovery action."),
                    envelope=context.envelope,
                    store=store,
                    run_ref=dto.run_ref,
                    attention_ref=dto.item_ref,
                    conflict_version=dto.state_version,
                )
            attempt = record
            job = attempt.job_id
            target = _Target(
                job=job,
                run=getattr(job, "run_id", False),
                store=store,
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
                    attention_ref=dto.item_ref,
                    version=dto.state_version,
                    message=_("The store or run generation changed; refresh before acting."),
                )
            if attempt.observed_outcome != "uncertain" or attempt.resolution_disposition:
                return self._recovery_result(
                    "conflict",
                    _("The remote outcome was already changed; refresh before acting."),
                    envelope=context.envelope,
                    store=store,
                    run_ref=target.run_ref,
                    attention_ref=dto.item_ref,
                    conflict_version=dto.state_version,
                )
            before = job.state
            try:
                attempt.action_resolve_mutation_attempt(
                    recovery.inputs["disposition"],
                    recovery.reason,
                )
            except AccessError:
                raise
            except UserError:
                attempt.invalidate_recordset()
                fresh = self._recovery_ui()._state_version(
                    attempt,
                    ("observed_outcome", "resolution_disposition", "write_date"),
                )
                return self._recovery_conflict(
                    target,
                    context.envelope,
                    attention_ref=dto.item_ref,
                    version=fresh,
                    message=_("The mutation decision changed; refresh before acting."),
                )
            attempt.invalidate_recordset()
            job.invalidate_recordset()
            self._recovery_audit_command(
                job,
                context.envelope,
                recovery.action_key,
                recovery.reason,
                before,
                job.state,
            )
            return self._recovery_result(
                "accepted",
                _("The remote outcome decision was recorded."),
                envelope=context.envelope,
                store=store,
                run_ref=target.run_ref,
            )

        return self._recovery_result(
            "blocked",
            _("This attention provider has no approved command adapter."),
            envelope=context.envelope,
            store=store,
            run_ref=dto.run_ref,
            attention_ref=dto.item_ref,
            conflict_version=dto.state_version,
        )

__all__ = ["ShopifyConnectorRecoveryCommands"]
