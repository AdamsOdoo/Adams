"""Durable replay adapter for the advertised P04 recovery command."""

from __future__ import annotations

from collections.abc import Mapping
from functools import wraps

from odoo import _, api, models
from odoo.exceptions import ValidationError

from ..domain.p15_foundation import command_request_fingerprint
from .shopify_connector_command_result import _COMMAND_RESULT_SERVICE_CAPABILITY


def recovery_command_replay_endpoint(expected_name):
    """Serialize one typed recovery command and replay its durable result."""
    def decorate(method):
        @wraps(method)
        def wrapped(self, command, *args, **kwargs):
            context = self._recovery_parse_envelope(command, expected_name)
            result_model = self.env["shopify.connector.command.result"]
            envelope = context.envelope
            store_id = envelope.store_id
            result_model._lock_scope(
                envelope.company_id,
                store_id,
                str(envelope.command_id),
                service_capability=_COMMAND_RESULT_SERVICE_CAPABILITY,
            )
            payload = dict(context.payload)
            if context.expected_configuration_generation is not None:
                payload["__expected_configuration_generation"] = (
                    context.expected_configuration_generation
                )
            request_hash = command_request_fingerprint(
                company_id=envelope.company_id,
                store_id=store_id,
                command_id=str(envelope.command_id),
                command_name=expected_name,
                payload=payload,
                expected_generation=envelope.expected_generation,
            )
            existing = result_model._find_for_command(
                company_id=envelope.company_id,
                store_id=store_id,
                command_id=str(envelope.command_id),
                service_capability=_COMMAND_RESULT_SERVICE_CAPABILITY,
            )
            if existing:
                if (
                    existing.command_name != expected_name
                    or existing.request_hash != request_hash
                ):
                    raise ValidationError(_(
                        "This command id was already used for a different request."
                    ))
                replay = dict(existing.result_json or {})
                replay.update({
                    "status": "duplicate",
                    "original_status": replay.get("status"),
                    "replayed": True,
                })
                return replay
            result = method(self, command, *args, **kwargs)
            if not isinstance(result, Mapping):
                raise ValidationError(_(
                    "A recovery command must return an object result."
                ))
            generation = result.get(
                "connection_generation",
                result.get(
                    "configuration_generation",
                    result.get("conflict_version", 0),
                ),
            )
            result_model._record_for_command(
                company_id=envelope.company_id,
                store_id=store_id,
                command_id=str(envelope.command_id),
                command_name=expected_name,
                request_hash=request_hash,
                result=dict(result),
                generation=generation,
                service_capability=_COMMAND_RESULT_SERVICE_CAPABILITY,
            )
            return result
        return wrapped
    return decorate


class ShopifyConnectorRecoveryReplay(models.AbstractModel):
    """Apply durable replay without enlarging the recovery command module."""

    _inherit = "shopify.connector.application.facade"

    @api.model
    @recovery_command_replay_endpoint("resolve_attention_v1")
    def resolve_attention_v1(self, command):
        return super().resolve_attention_v1(command)

    @api.model
    @recovery_command_replay_endpoint("retry_job_v1")
    def retry_job_v1(self, command):
        return super().retry_job_v1(command)

    @api.model
    @recovery_command_replay_endpoint("cancel_job_v1")
    def cancel_job_v1(self, command):
        return super().cancel_job_v1(command)


__all__ = [
    "ShopifyConnectorRecoveryReplay",
    "recovery_command_replay_endpoint",
]
