"""Durable, bounded replay records for named P15 commands.

The command result is an audit/replay envelope, not a second business source
of truth.  It contains only sanitized acknowledgements and is written by the
P15 command decorator after the owning legacy service has accepted/completed
the operation.  A transaction-scoped advisory lock closes the concurrent
duplicate window without holding a store row lock across any network call.
"""

from __future__ import annotations

import hashlib
import json
import string
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from ..domain.p15_foundation import (
    MAX_COMMAND_RESULT_DEPTH,
    command_scope_key,
    sanitize_command_result,
)


COMMAND_RESULT_RETENTION_DAYS = 90
COMMAND_RESULT_RETENTION_PARAM = "shopify_connector.command_result_retention_days"
COMMAND_RESULT_BATCH_SIZE = 2000
COMMAND_RESULT_SERVICE_CONTEXT = "shopify_command_result_service"
COMMAND_RESULT_SERVICE_SENTINEL = object()
COMMAND_RESULT_SERVICE_CAPABILITY_CONTEXT = (
    "shopify_command_result_service_capability"
)
# Object identity is the capability.  A serialized RPC value, including a
# boolean or a copied context string, can never satisfy this check.
_COMMAND_RESULT_SERVICE_CAPABILITY = object()


class ShopifyConnectorCommandResult(models.Model):
    """One immutable result per company/store/command id."""

    _name = "shopify.connector.command.result"
    _description = "Shopify Connector Named Command Result"
    _order = "id desc"

    company_id = fields.Many2one(
        "res.company", required=True, readonly=True, index=True,
        ondelete="restrict",
    )
    store_id = fields.Many2one(
        "shopify.connector.store", readonly=True, index=True,
        ondelete="restrict",
    )
    scope_key = fields.Char(required=True, readonly=True, index=True)
    command_id = fields.Char(required=True, readonly=True, index=True)
    command_name = fields.Char(required=True, readonly=True, index=True)
    request_hash = fields.Char(required=True, readonly=True, size=64)
    status = fields.Selection(
        selection=[
            ("accepted", "Accepted"),
            ("completed", "Completed"),
            ("blocked", "Blocked"),
            ("conflict", "Conflict"),
            ("duplicate", "Duplicate"),
        ],
        required=True,
        readonly=True,
        index=True,
    )
    generation = fields.Integer(required=True, readonly=True, default=0)
    result_json = fields.Json(required=True, readonly=True, default=dict)
    created_at = fields.Datetime(
        required=True, readonly=True, index=True, default=fields.Datetime.now,
    )

    _command_scope_uniq = models.Constraint(
        "UNIQUE(company_id, scope_key, command_id)",
        "A named connector command may be recorded only once per scope.",
    )

    @api.model
    def _service_context_is_open(self):
        return (
            self.env.su
            and self.env.context.get(COMMAND_RESULT_SERVICE_CONTEXT)
            is COMMAND_RESULT_SERVICE_SENTINEL
            and self.env.context.get(COMMAND_RESULT_SERVICE_CAPABILITY_CONTEXT)
            is _COMMAND_RESULT_SERVICE_CAPABILITY
        )

    @api.model
    def _require_service_capability(self, capability):
        if capability is not _COMMAND_RESULT_SERVICE_CAPABILITY:
            raise AccessError(
                "Named command results require the connector service capability."
            )

    @api.model
    def _authorize_scope(self, company_id, store_id):
        """Authorize the exact active company and optional store before sudo."""

        if company_id != self.env.company.id:
            raise AccessError(
                "Named command results are limited to the active company."
            )
        scope = command_scope_key(company_id, store_id)
        if store_id is None:
            return scope
        Store = self.env["shopify.connector.store"]
        store = Store.search(
            [("id", "=", store_id), ("company_id", "=", company_id)],
            limit=1,
        )
        if not store:
            raise AccessError(
                "The command result store is not available in the active company."
            )
        store.ensure_one()
        if store.company_id.id != self.env.company.id:
            raise AccessError(
                "The command result store is not in the active company."
            )
        return scope

    @api.model_create_multi
    def create(self, vals_list):
        if not self._service_context_is_open():
            raise AccessError(
                "Named command results can only be written by the connector service."
            )
        return super().create(vals_list)

    def write(self, vals):
        if not self._service_context_is_open():
            raise AccessError("Named command results are immutable.")
        return super().write(vals)

    def unlink(self):
        if not self._service_context_is_open():
            raise AccessError("Named command results are retained by policy.")
        return super().unlink()

    @api.model
    def _lock_scope(
        self, company_id, store_id, command_id, *, service_capability=None,
    ):
        """Serialize one command identity until the request transaction ends."""

        self._require_service_capability(service_capability)
        scope = command_scope_key(company_id, store_id)
        self._authorize_scope(company_id, store_id)
        digest = hashlib.sha256(
            ("%d:%s:%s" % (company_id, scope, command_id)).encode("utf-8")
        ).digest()
        # PostgreSQL advisory locks use a signed 32-bit integer here.  A
        # collision only serializes unrelated commands; the uniqueness key
        # remains the final correctness boundary.
        lock_id = int.from_bytes(digest[:4], "big") & 0x7FFFFFFF
        self.env.cr.execute("SELECT pg_advisory_xact_lock(%s)", (lock_id,))
        return scope

    @api.model
    def _find_for_command(
        self, *, company_id, store_id, command_id, service_capability=None,
    ):
        self._require_service_capability(service_capability)
        scope = self._authorize_scope(company_id, store_id)
        return self.sudo().search(
            [
                ("company_id", "=", company_id),
                ("store_id", "=", store_id or False),
                ("scope_key", "=", scope),
                ("command_id", "=", command_id),
            ],
            limit=1,
        )

    @api.model
    def _record_for_command(
        self, *, company_id, store_id, command_id, command_name,
        request_hash, result, generation=0, service_capability=None,
    ):
        """Persist one sanitized result through the closed service seam."""

        self._require_service_capability(service_capability)
        scope = self._authorize_scope(company_id, store_id)
        if not isinstance(command_id, str) or not command_id.strip():
            raise ValidationError("The command id is required.")
        if not isinstance(command_name, str) or not command_name.strip():
            raise ValidationError("The command name is required.")
        if (
            not isinstance(request_hash, str)
            or len(request_hash) != 64
            or any(char not in string.hexdigits for char in request_hash)
        ):
            raise ValidationError("The command request fingerprint is invalid.")
        normalized, encoded = sanitize_command_result(result)
        if not isinstance(normalized, dict):
            raise ValidationError("A command result must be an object.")
        try:
            generation = int(generation or 0)
        except (TypeError, ValueError) as exc:
            raise ValidationError("The command generation is invalid.") from exc
        if generation < 0:
            raise ValidationError("The command generation is invalid.")
        vals = {
            "company_id": company_id,
            "store_id": store_id or False,
            "scope_key": scope,
            "command_id": command_id,
            "command_name": command_name,
            "request_hash": request_hash,
            "status": normalized.get("status") or "accepted",
            "generation": generation,
            "result_json": json.loads(encoded),
        }
        # Keep this operation idempotent for callers which already hold the
        # command lock and for migration/test fixtures that replay a result.
        existing = self._find_for_command(
            company_id=company_id,
            store_id=store_id,
            command_id=command_id,
            service_capability=service_capability,
        )
        if existing:
            return existing
        return self.with_context(**{
            COMMAND_RESULT_SERVICE_CONTEXT: COMMAND_RESULT_SERVICE_SENTINEL,
            COMMAND_RESULT_SERVICE_CAPABILITY_CONTEXT:
                _COMMAND_RESULT_SERVICE_CAPABILITY,
        }).sudo().create(vals)

    @api.model
    def _retention_days(self):
        raw = self.env["ir.config_parameter"].sudo().get_param(
            COMMAND_RESULT_RETENTION_PARAM, COMMAND_RESULT_RETENTION_DAYS,
        )
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return COMMAND_RESULT_RETENTION_DAYS
        return value if value > 0 else COMMAND_RESULT_RETENTION_DAYS

    @api.model
    def run_retention(self):
        """Delete only old bounded replay envelopes in one batch."""

        if not self.env.su and not self.env.user.has_group(
            "shopify_connector_core.group_shopify_connector_admin"
        ):
            raise AccessError("Only a Connector Administrator may run command-result retention.")
        cutoff = fields.Datetime.now() - timedelta(days=self._retention_days())
        domain = [("created_at", "<", cutoff)]
        if not self.env.su:
            domain.append(("company_id", "=", self.env.company.id))
        rows = self.sudo().search(
            domain,
            order="created_at asc, id asc",
            limit=COMMAND_RESULT_BATCH_SIZE,
        )
        count = len(rows)
        rows.with_context(**{
            COMMAND_RESULT_SERVICE_CONTEXT: COMMAND_RESULT_SERVICE_SENTINEL,
            COMMAND_RESULT_SERVICE_CAPABILITY_CONTEXT:
                _COMMAND_RESULT_SERVICE_CAPABILITY,
        }).unlink()
        return count


__all__ = [
    "COMMAND_RESULT_BATCH_SIZE",
    "COMMAND_RESULT_RETENTION_DAYS",
    "COMMAND_RESULT_RETENTION_PARAM",
    "MAX_COMMAND_RESULT_DEPTH",
    "ShopifyConnectorCommandResult",
]
