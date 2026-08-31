"""Semantic setup-step persistence for the P15 named command facade."""

from __future__ import annotations

from collections.abc import Mapping

from odoo import _, api, models
from odoo.exceptions import ValidationError

from ..domain.p15_foundation import validate_setup_payload
from ..domain.store_admin import require_setup_step_key
from .shopify_connector_p15_command_replay import p15_command_endpoint
from .shopify_connector_p15_shared import _p15_nonnegative_int
from .shopify_connector_setup_wizard import setup_step_index


class ShopifyConnectorP15SetupCommands(models.AbstractModel):
    """Persist only the scalar choices owned by each semantic step."""

    _inherit = "shopify.connector.application.facade"

    @api.model
    @p15_command_endpoint("save_setup_step_v1")
    def save_setup_step_v1(self, command):
        envelope, payload = self._p15_parse_command(
            command, "save_setup_step_v1",
        )
        store = self._p15_store_for_command(envelope)
        if (
            getattr(store, "activation_state", "draft") == "retired"
            or store.state in ("disconnecting", "disconnected")
        ):
            return self._p15_ack(
                "blocked",
                _("Setup cannot be changed for this store lifecycle state."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=int(store.connection_generation or 0),
            )
        step_key = require_setup_step_key(payload.get("step_key"))
        unknown_payload = set(payload) - {"step_key", "values"}
        if unknown_payload:
            raise ValidationError(_(
                "Unsupported setup payload fields: %(fields)s",
                fields=", ".join(sorted(str(item) for item in unknown_payload)),
            ))
        try:
            semantic_values = validate_setup_payload(
                step_key, payload.get("values") or {},
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(_(
                "The setup-step values are not supported for this step."
            )) from exc
        Settings = self.env["shopify.connector.store.settings"]
        settings = Settings._p15_get_or_create(store)
        current_generation = Settings._p15_lock_generation(settings)
        expected = _p15_nonnegative_int(
            envelope.expected_generation, "expected_generation",
        )
        if current_generation != expected:
            return self._p15_ack(
                "conflict",
                _("Store settings changed; reload setup before continuing."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=current_generation,
            )
        setting_values = {
            key: value for key, value in semantic_values.items()
            if key != "acknowledged"
        }
        missing_fields = set(setting_values) - set(settings._fields)
        if missing_fields:
            raise ValidationError(_(
                "These setup controls are not installed: %(fields)s",
                fields=", ".join(sorted(missing_fields)),
            ))
        normalized = self._p15_validate_setting_values(settings, setting_values)
        current_payloads = settings.setup_step_payloads or {}
        if not isinstance(current_payloads, Mapping):
            raise ValidationError(_(
                "Stored setup evidence is invalid; repair it before continuing."
            ))
        checked_payloads = {}
        for old_key, old_values in current_payloads.items():
            try:
                checked_payloads[old_key] = validate_setup_payload(
                    old_key, old_values,
                )
            except (TypeError, ValueError) as exc:
                raise ValidationError(_(
                    "Stored setup evidence contains an unsupported step."
                )) from exc
        checked_payloads[step_key] = dict(semantic_values)
        Wizard = self.env["shopify.connector.setup.wizard"]
        current_key = Wizard._resume_key(settings)
        requested_ordinal = setup_step_index(step_key)
        current_ordinal = setup_step_index(current_key)
        # Forward progress is fenced to the resumable step and its immediate
        # successor.  The ordinal is display-only for addressing, but the
        # closed semantic order is still the server-side guard against a
        # forged command jumping over unsaved prerequisites.
        if requested_ordinal > current_ordinal + 1:
            raise ValidationError(_(
                "Complete the current setup step before opening a later step."
            ))
        changed = (
            checked_payloads != current_payloads
            or requested_ordinal > current_ordinal
            or any(
                self._p15_normalized_setting_value(settings, key) != value
                for key, value in normalized.items()
            )
        )
        if not changed:
            return self._p15_ack(
                "completed",
                _("Setup progress was already saved."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=current_generation,
            )
        write_values = dict(normalized)
        write_values["setup_step_payloads"] = checked_payloads
        if requested_ordinal > current_ordinal:
            write_values.update({
                "setup_wizard_step_key": step_key,
                "setup_wizard_step": requested_ordinal,
            })
        settings._p15_service_write(write_values)
        settings.invalidate_recordset(["configuration_generation"])
        accepted_generation = int(settings.configuration_generation or 0)
        return self._p15_ack(
            "completed",
            _("Setup progress saved."),
            command_id=envelope.command_id,
            store_id=store.id,
            generation=accepted_generation,
        )


__all__ = ["ShopifyConnectorP15SetupCommands"]
