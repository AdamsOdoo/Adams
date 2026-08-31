"""Shared durable lock/replay wrapper for named P15 commands."""

from __future__ import annotations

from collections.abc import Mapping
from functools import wraps

from odoo import _, api, models
from odoo.exceptions import ValidationError

from ..domain.p15_foundation import command_request_fingerprint
from .shopify_connector_command_result import (
    _COMMAND_RESULT_SERVICE_CAPABILITY,
)


def p15_command_endpoint(expected_name, *, create=False):
    """Decorate a named command with scoped lock and result replay."""

    def decorate(method):
        @wraps(method)
        def wrapped(self, command, *args, **kwargs):
            envelope, _payload = self._p15_parse_command(
                command, expected_name, create=create,
            )
            self._p15_lock_command(envelope, create=create)
            replay = self._p15_replay_command(
                envelope, expected_name, create=create,
            )
            if replay is not None:
                return replay
            result = method(self, command, *args, **kwargs)
            self._p15_record_command_result(
                envelope, expected_name, result, create=create,
            )
            return result
        return wrapped
    return decorate


class ShopifyConnectorP15CommandReplay(models.AbstractModel):
    """Methods shared by the command and operation facade extensions."""

    _inherit = "shopify.connector.application.facade"

    @api.model
    def _p15_lock_command(self, envelope, *, create=False):
        store_id = None if create else envelope.store_id
        self.env["shopify.connector.command.result"]._lock_scope(
            envelope.company_id,
            store_id,
            str(envelope.command_id),
            service_capability=_COMMAND_RESULT_SERVICE_CAPABILITY,
        )

    @api.model
    def _p15_replay_command(self, envelope, expected_name, *, create=False):
        store_id = None if create else envelope.store_id
        result_model = self.env["shopify.connector.command.result"]
        existing = result_model._find_for_command(
            company_id=envelope.company_id,
            store_id=store_id,
            command_id=str(envelope.command_id),
            service_capability=_COMMAND_RESULT_SERVICE_CAPABILITY,
        )
        if not existing:
            return None
        request_hash = command_request_fingerprint(
            company_id=envelope.company_id,
            store_id=store_id,
            command_id=str(envelope.command_id),
            command_name=expected_name,
            payload=envelope.payload,
            expected_generation=envelope.expected_generation,
        )
        if (
            existing.command_name != expected_name
            or existing.request_hash != request_hash
        ):
            raise ValidationError(_(
                "This command id was already used for a different request."
            ))
        replay = dict(existing.result_json or {})
        original_status = replay.get("status")
        replay.update({
            "status": "duplicate",
            "original_status": original_status,
            "replayed": True,
        })
        return replay

    @api.model
    def _p15_record_command_result(
        self, envelope, command_name, result, *, create=False,
    ):
        if not isinstance(result, Mapping):
            raise ValidationError(_("A named command must return an object result."))
        store_id = None if create else envelope.store_id
        request_hash = command_request_fingerprint(
            company_id=envelope.company_id,
            store_id=store_id,
            command_id=str(envelope.command_id),
            command_name=command_name,
            payload=envelope.payload,
            expected_generation=envelope.expected_generation,
        )
        generation = result.get("generation", result.get("conflict_version", 0))
        self.env["shopify.connector.command.result"]._record_for_command(
            company_id=envelope.company_id,
            store_id=store_id,
            command_id=str(envelope.command_id),
            command_name=command_name,
            request_hash=request_hash,
            result=dict(result),
            generation=generation,
            service_capability=_COMMAND_RESULT_SERVICE_CAPABILITY,
        )


__all__ = ["ShopifyConnectorP15CommandReplay", "p15_command_endpoint"]
