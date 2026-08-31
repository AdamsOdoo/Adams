"""P15 named administrator commands and stale-submit fences."""

from __future__ import annotations

from collections.abc import Mapping

from psycopg2 import IntegrityError

from odoo import _, api, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..application.command_contracts import CommandEnvelope, CommandResult
from ..domain.store_admin import canonical_shop_domain
from .shopify_connector_p15_command_replay import p15_command_endpoint
from .shopify_connector_p15_shared import (
    P15_COMMAND_NAMES,
    P15_EDITABLE_SETTINGS_GROUP_FIELDS,
    P15_MAX_TEXT_SETTING_LENGTH,
    P15_SETTINGS_GROUP_FIELDS,
    P15_SHA256_RE,
    _p15_nonnegative_int,
    _p15_parse_datetime,
    _p15_positive_id,
    _p15_safe_text,
)


class ShopifyConnectorP15ApplicationFacade(models.AbstractModel):
    """Named P15 read delegates and generation-fenced write commands."""

    _inherit = "shopify.connector.application.facade"

    @api.model
    def _p15_ui(self):
        return self.env["shopify.connector.ui.facade"]

    @api.model
    def get_store_list_v1(
        self, company_ids=None, state_filter=None, search=None,
        limit=10, cursor=None,
    ):
        return self._p15_ui().get_store_list_v1(
            company_ids=company_ids,
            state_filter=state_filter,
            search=search,
            limit=limit,
            cursor=cursor,
        )

    @api.model
    def get_store_settings_v1(self, store_id):
        return self._p15_ui().get_store_settings_v1(store_id)

    @api.model
    def get_store_admin_summary_v1(self, store_id):
        return self._p15_ui().get_store_admin_summary_v1(store_id)

    @api.model
    def get_store_readiness_v1(self, store_id):
        return self._p15_ui().get_store_readiness_v1(store_id)

    @api.model
    def get_setup_v1(self, store_id):
        return self._p15_ui().get_setup_v1(store_id)

    @api.model
    def _p15_require_admin(self):
        return self._p15_ui()._p15_require_admin()

    @api.model
    def _p15_parse_command(self, command, expected_name, *, create=False):
        """Parse one strict command envelope and bind actor/company identity."""

        if isinstance(command, CommandEnvelope):
            envelope = command
        elif isinstance(command, Mapping):
            allowed = {
                "contract_version", "command_id", "command_name", "store_id",
                "company_id", "expected_generation", "actor_uid", "trigger",
                "requested_at", "payload",
            }
            unknown = set(command) - allowed
            if unknown:
                raise ValidationError(_(
                    "Command envelope contains unsupported fields: %(fields)s",
                    fields=", ".join(sorted(str(item) for item in unknown)),
                ))
            required = {
                "contract_version", "command_id", "command_name", "company_id",
                "expected_generation", "actor_uid", "trigger", "requested_at",
            }
            if create and "store_id" in command:
                raise ValidationError(_(
                    "A store-create command must not include a store id."
                ))
            if not create:
                required.add("store_id")
            missing = required - set(command)
            if missing:
                raise ValidationError(_(
                    "Command envelope is missing: %(fields)s",
                    fields=", ".join(sorted(missing)),
                ))
            try:
                from uuid import UUID
                envelope = CommandEnvelope(
                    contract_version=command["contract_version"],
                    command_id=(
                        command["command_id"]
                        if isinstance(command["command_id"], UUID)
                        else UUID(str(command["command_id"]))
                    ),
                    command_name=command["command_name"],
                    # CommandEnvelope is deliberately store-scoped and
                    # requires a positive id.  Create is the one command
                    # whose target does not exist yet; a private placeholder
                    # is used only while parsing and is never persisted or
                    # trusted as an identity.
                    store_id=(1 if create else command["store_id"]),
                    company_id=command["company_id"],
                    expected_generation=command["expected_generation"],
                    actor_uid=command["actor_uid"],
                    trigger=command["trigger"],
                    requested_at=_p15_parse_datetime(command["requested_at"]),
                    payload=command.get("payload", {}),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValidationError(_("The command envelope is invalid.")) from exc
        else:
            raise ValidationError(_("A typed command envelope is required."))
        if envelope.command_name != expected_name:
            raise ValidationError(_("The command name does not match the endpoint."))
        if expected_name not in P15_COMMAND_NAMES:
            raise ValidationError(_("The command is not supported."))
        self._p15_require_admin()
        if envelope.company_id != self.env.company.id:
            raise AccessError(_("The command company must be the active company."))
        if envelope.trigger not in ("user", "system"):
            raise AccessError(_("Only an interactive administrator command is allowed."))
        if envelope.trigger == "system" and not self.env.su:
            raise AccessError(_(
                "System-triggered commands are limited to trusted internal "
                "services."
            ))
        if (
            envelope.trigger == "user"
            and not self.env.su
            and envelope.actor_uid != self.env.uid
        ):
            raise AccessError(_("The command actor could not be verified."))
        payload = dict(envelope.payload)
        return envelope, payload

    @api.model
    def _p15_ack(self, status, message, *, command_id=None, store_id=None, generation=None, run_ref=None):
        result = CommandResult(
            status=status,
            run_ref=run_ref,
            attention_ref=None,
            message=message,
            conflict_version=generation,
        ).as_dict()
        if command_id is not None:
            result["command_id"] = str(command_id)
        if store_id is not None:
            result["store_id"] = store_id
        if generation is not None:
            result["generation"] = generation
        return result

    @api.model
    def _p15_store_for_command(self, envelope):
        store = self._p15_ui()._p15_require_store(envelope.store_id)
        if store.company_id.id != envelope.company_id:
            raise AccessError(_("The store is not in the active company."))
        return store

    @api.model
    def _p15_check_store_generation(self, store, expected):
        expected = _p15_nonnegative_int(expected, "expected_generation")
        # Read only for the optimistic precondition.  The existing lifecycle
        # services take their own blocking store-row lock at the point where a
        # transition is committed; keeping that lock out of this helper is
        # essential for `test_connection_v1`, whose diagnostic network call
        # must never run while a database row lock is held.
        store.invalidate_recordset(["state", "connection_generation"])
        current_state = store.state
        current = int(store.connection_generation or 0)
        if current != expected:
            return current_state, current, False
        return current_state, current, True

    @api.model
    def _p15_settings_for_command(self, store):
        Settings = self.env["shopify.connector.store.settings"]
        return Settings._p15_get_or_create(store)

    @api.model
    @p15_command_endpoint("create_store_v1", create=True)
    def create_store_v1(self, command):
        envelope, payload = self._p15_parse_command(
            command, "create_store_v1", create=True,
        )
        allowed = {"name", "shop_domain"}
        unknown = set(payload) - allowed
        if unknown:
            raise ValidationError(_("Unsupported store fields: %(fields)s", fields=", ".join(sorted(unknown))))
        name = _p15_safe_text(payload.get("name"), "name", max_length=255)
        try:
            domain = canonical_shop_domain(payload.get("shop_domain"))
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("The Shopify domain is not canonical.")) from exc
        if envelope.expected_generation != 0:
            raise ValidationError(_("A new store must use generation zero."))
        Store = self.env["shopify.connector.store"].sudo()
        try:
            with self.env.cr.savepoint():
                store = Store._store_service_create("_setup", {
                    "name": name,
                    "shop_domain": domain,
                    "company_id": self.env.company.id,
                })
        except IntegrityError as exc:
            raise UserError(_(
                "A store already exists for this Shopify domain."
            )) from exc
        Settings = self.env["shopify.connector.store.settings"]
        settings = Settings._p15_get_or_create(store, lock_store=False)
        return self._p15_ack(
            "completed",
            _("Store created and settings initialized."),
            command_id=envelope.command_id,
            store_id=store.id,
            generation=int(getattr(settings, "configuration_generation", 0) or 0),
        )

    @api.model
    @p15_command_endpoint("save_store_settings_group_v1")
    def save_store_settings_group_v1(self, command):
        envelope, payload = self._p15_parse_command(
            command, "save_store_settings_group_v1",
        )
        store = self._p15_store_for_command(envelope)
        group_key = payload.get("group_key")
        if not isinstance(group_key, str) or group_key not in P15_SETTINGS_GROUP_FIELDS:
            raise ValidationError(_("The settings group is not supported."))
        values = payload.get("values")
        if not isinstance(values, Mapping) or not values:
            raise ValidationError(_("The settings group values are required."))
        allowed = set(P15_EDITABLE_SETTINGS_GROUP_FIELDS[group_key])
        unknown = set(values) - allowed
        if unknown:
            raise AccessError(_(
                "These settings are connector-owned or unsupported: %(fields)s",
                fields=", ".join(sorted(str(item) for item in unknown)),
            ))
        if not allowed:
            raise AccessError(_(
                "Fulfillment operating mode is changed only by its mode "
                "switch command."
            ))
        Settings = self.env["shopify.connector.store.settings"]
        settings = Settings._p15_get_or_create(store)
        current_generation = Settings._p15_lock_generation(settings)
        expected = _p15_nonnegative_int(
            envelope.expected_generation, "expected_generation",
        )
        if current_generation != expected:
            return self._p15_ack(
                "conflict",
                _("Store settings changed; reload before saving."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=current_generation,
            )
        # Optional group fingerprint is a second stale-submit fence.  It is
        # computed from current effective values, not from labels/timestamps.
        supplied_fingerprint = payload.get("expected_fingerprint")
        if supplied_fingerprint is not None:
            if not isinstance(supplied_fingerprint, str) or not P15_SHA256_RE.fullmatch(supplied_fingerprint):
                raise ValidationError(_("The settings fingerprint is invalid."))
            ui = self._p15_ui()
            groups, effective = ui._p15_settings_groups(store, settings)
            current_group = next((item for item in groups if item.key == group_key), None)
            if not current_group or current_group.fingerprint != supplied_fingerprint:
                return self._p15_ack(
                    "conflict",
                    _("This settings group changed; reload before saving."),
                    command_id=envelope.command_id,
                    store_id=store.id,
                    generation=current_generation,
                )
        normalized = self._p15_validate_setting_values(settings, values)
        changed = any(
            self._p15_normalized_setting_value(settings, key) != value
            for key, value in normalized.items()
        )
        if not changed:
            return self._p15_ack(
                "completed",
                _("No settings changed."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=current_generation,
            )
        normalized["configuration_generation"] = current_generation + 1
        settings._p15_service_write(normalized)
        return self._p15_ack(
            "completed",
            _("Store settings saved."),
            command_id=envelope.command_id,
            store_id=store.id,
            generation=current_generation + 1,
        )

    @api.model
    def _p15_normalized_setting_value(self, settings, key):
        value = settings[key]
        if hasattr(value, "id"):
            return value.id or False
        return value

    @api.model
    def _p15_validate_setting_values(self, settings, values):
        normalized = {}
        for key, value in values.items():
            if not isinstance(key, str) or key not in settings._fields:
                raise ValidationError(_("The settings field is not installed."))
            field = settings._fields[key]
            if field.type == "boolean":
                if not isinstance(value, bool):
                    raise ValidationError(_("%(field)s must be boolean.", field=key))
                normalized[key] = value
            elif field.type == "selection":
                selection = field.selection
                if callable(selection):
                    selection = selection(settings.env)
                choices = {item[0] for item in (selection or ())}
                if value not in choices:
                    raise ValidationError(_("The value for %(field)s is invalid.", field=key))
                normalized[key] = value
            elif field.type == "integer":
                normalized[key] = _p15_nonnegative_int(value, key)
            elif field.type == "many2one":
                normalized[key] = (
                    False
                    if value in (None, False, "")
                    else _p15_positive_id(value, key)
                )
            elif field.type in ("char", "text"):
                if not isinstance(value, str) or len(value) > P15_MAX_TEXT_SETTING_LENGTH:
                    raise ValidationError(_("The value for %(field)s is invalid.", field=key))
                normalized[key] = value
            else:
                raise ValidationError(_("The settings field %(field)s is not editable here.", field=key))
        # Identity/company references never enter the grouped command, even if
        # an optional addon later adds a similarly named field.
        forbidden = {
            "store_id", "company_id", "order_company_id", "configuration_generation",
            "fulfillment_operating_mode", "fulfillment_switch_in_progress",
            "fulfillment_mode_switch_nonce", "fulfillment_requested_mode",
            "fulfillment_mode_switch_state", "fulfillment_mode_switch_job_id",
            "fulfillment_mode_switch_failure_reason", "fulfillment_notification_confirmed",
        }
        if forbidden.intersection(normalized):
            raise AccessError(_("Connector-owned settings require their named service."))
        # A reference is part of the store's configuration, so accepting a
        # record from another company would create a cross-company oracle or
        # cause later workers to operate with a foreign policy.  Odoo's
        # related models do not all expose the same company field; when they
        # do, a NULL company denotes a shared record and is safe to use.
        for key, value in normalized.items():
            if not value or settings._fields[key].type != "many2one":
                continue
            field = settings._fields[key]
            target = self.env[field.comodel_name].browse(value).exists()
            if not target:
                raise ValidationError(_(
                    "The reference for %(field)s is not available.", field=key,
                ))
            if "company_id" in target._fields and target.company_id and (
                target.company_id.id != settings.company_id.id
            ):
                raise AccessError(_(
                    "The reference for %(field)s belongs to another company.",
                    field=key,
                ))
        return normalized

    @api.model
    @p15_command_endpoint("replace_credential_v1")
    def replace_credential_v1(self, command):
        envelope, payload = self._p15_parse_command(
            command, "replace_credential_v1",
        )
        store = self._p15_store_for_command(envelope)
        if (
            getattr(store, "activation_state", "draft") == "retired"
            or store.state in ("disconnecting", "disconnected")
        ):
            return self._p15_ack(
                "blocked",
                _("Credentials cannot be replaced for this store lifecycle state."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=int(store.connection_generation or 0),
            )
        state, current_generation, matches = self._p15_check_store_generation(
            store, envelope.expected_generation,
        )
        if not matches:
            return self._p15_ack(
                "conflict",
                _("The store connection changed; reload before replacing credentials."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=current_generation,
            )
        mode = payload.get("auth_mode", "offline_access_token")
        Credential = self.env["shopify.connector.store.credential"]
        # Secret values are accepted only as write-only command payloads and
        # are immediately handed to the existing credential service.  They are
        # never interpolated into an exception, log, result, or DTO.
        if mode == "offline_access_token":
            token = payload.get("access_token")
            if not isinstance(token, str) or not token:
                raise ValidationError(_("A non-empty access token is required."))
            if store.credential_present:
                Credential.action_replace_token(store, token)
            else:
                Credential.action_set_token(store, token)
            token = None
        elif mode == "dev_dashboard_client_credentials":
            client_id = payload.get("client_id")
            client_secret = payload.get("client_secret")
            if not isinstance(client_id, str) or not client_id.strip():
                raise ValidationError(_("A non-empty Client ID is required."))
            if not isinstance(client_secret, str) or not client_secret:
                raise ValidationError(_("A non-empty Client secret is required."))
            Credential.action_set_client_credentials(
                store, client_id.strip(), client_secret,
            )
            client_secret = None
        else:
            raise ValidationError(_("The credential acquisition mode is invalid."))
        store.invalidate_recordset()
        return self._p15_ack(
            "completed",
            _("Credential replaced; connection evidence must be refreshed."),
            command_id=envelope.command_id,
            store_id=store.id,
            generation=int(store.connection_generation or current_generation),
        )

    @api.model
    @p15_command_endpoint("test_connection_v1")
    def test_connection_v1(self, command):
        envelope, payload = self._p15_parse_command(
            command, "test_connection_v1",
        )
        if payload:
            raise ValidationError(_("Test Connection accepts no payload."))
        store = self._p15_store_for_command(envelope)
        if (
            getattr(store, "activation_state", "draft") == "retired"
            or store.state in ("disconnecting", "disconnected")
        ):
            return self._p15_ack(
                "blocked",
                _("Connection testing is unavailable for this store lifecycle state."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=int(store.connection_generation or 0),
            )
        _state, current_generation, matches = self._p15_check_store_generation(
            store, envelope.expected_generation,
        )
        if not matches:
            return self._p15_ack(
                "conflict",
                _("The store connection changed; reload before testing."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=current_generation,
            )
        # This is the existing read-only diagnostic probe, not a business
        # mutation.  It owns credential access, audit, and post-network fences.
        store.action_test_connection()
        return self._p15_ack(
            "completed",
            _("Connection test submitted."),
            command_id=envelope.command_id,
            store_id=store.id,
            generation=current_generation,
        )

    @api.model
    @p15_command_endpoint("activate_store_v1")
    def activate_store_v1(self, command):
        envelope, payload = self._p15_parse_command(
            command, "activate_store_v1",
        )
        store = self._p15_store_for_command(envelope)
        supplied = payload.get("readiness_fingerprint")
        if not isinstance(supplied, str) or not P15_SHA256_RE.fullmatch(supplied):
            raise ValidationError(_("A current readiness fingerprint is required."))
        state, current_generation, matches = self._p15_check_store_generation(
            store, envelope.expected_generation,
        )
        if not matches:
            return self._p15_ack(
                "conflict",
                _("The store connection changed; reload before activating."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=current_generation,
            )
        settings = self._p15_settings_for_read(store)
        readiness = self._p15_ui()._p15_readiness_dto(store, settings)
        if readiness.fingerprint != supplied:
            return self._p15_ack(
                "conflict",
                _("Readiness changed; reload before activating."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=current_generation,
            )
        store.action_activate()
        store.invalidate_recordset()
        return self._p15_ack(
            "completed",
            _("Store activation accepted."),
            command_id=envelope.command_id,
            store_id=store.id,
            generation=int(store.connection_generation or current_generation),
        )

    @api.model
    def _p15_lifecycle_command(self, command, command_name, operation):
        envelope, payload = self._p15_parse_command(command, command_name)
        allowed_payload = {"reason"} if operation == "retire" else set()
        if set(payload) - allowed_payload:
            raise ValidationError(_("This lifecycle command accepts no such payload."))
        reason = payload.get("reason")
        if reason is not None:
            reason = _p15_safe_text(reason, "reason", max_length=255)
        store = self._p15_store_for_command(envelope)
        state, current_generation, matches = self._p15_check_store_generation(
            store, envelope.expected_generation,
        )
        if not matches:
            return self._p15_ack(
                "conflict",
                _("The store lifecycle changed; reload before retrying."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=current_generation,
            )
        if operation in ("pause", "resume", "retire"):
            status, message, generation = store._p15_activation_command(
                operation, reason=reason,
            )
            return self._p15_ack(
                status,
                _(message),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=generation,
            )
        if operation == "disconnect":
            if state == "disconnected":
                status, message = "completed", "Store is already disconnected."
            else:
                store.action_disconnect()
                status, message = "accepted", "Store disconnect accepted."
        else:
            if operation != "disconnect":
                raise ValidationError(_("Unsupported lifecycle operation."))
        store.invalidate_recordset()
        return self._p15_ack(
            status,
            message,
            command_id=envelope.command_id,
            store_id=store.id,
            generation=int(store.connection_generation or current_generation),
        )

    @api.model
    @p15_command_endpoint("disconnect_store_v1")
    def disconnect_store_v1(self, command):
        return self._p15_lifecycle_command(command, "disconnect_store_v1", "disconnect")

    @api.model
    @p15_command_endpoint("pause_store_v1")
    def pause_store_v1(self, command):
        return self._p15_lifecycle_command(command, "pause_store_v1", "pause")

    @api.model
    @p15_command_endpoint("resume_store_v1")
    def resume_store_v1(self, command):
        return self._p15_lifecycle_command(command, "resume_store_v1", "resume")

    @api.model
    @p15_command_endpoint("retire_store_v1")
    def retire_store_v1(self, command):
        return self._p15_lifecycle_command(command, "retire_store_v1", "retire")

    @api.model
    @p15_command_endpoint("set_workflow_state_v1")
    def set_workflow_state_v1(self, command):
        envelope, payload = self._p15_parse_command(
            command, "set_workflow_state_v1",
        )
        store = self._p15_store_for_command(envelope)
        workflow = payload.get("workflow")
        requested_state = payload.get("state")
        if workflow != "fulfillment" or requested_state not in ("mode1", "mode2"):
            raise ValidationError(_(
                "Only the fulfillment mode state-machine command is available."
            ))
        Settings = self.env["shopify.connector.store.settings"]
        settings = Settings._p15_get_or_create(store)
        current_generation = Settings._p15_lock_generation(settings)
        if current_generation != envelope.expected_generation:
            return self._p15_ack(
                "conflict",
                _("Store settings changed; reload before changing workflow state."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=current_generation,
            )
        if "fulfillment_operating_mode" not in settings._fields:
            raise UserError(_("Fulfillment is not installed for this database."))
        if requested_state == "mode2":
            settings.action_start_mode2_switch()
        else:
            settings.action_rollback_to_mode1()
        # Mode switch methods own their durable state transitions; generation
        # is the P15 stale-submit fence and is advanced only after that named
        # service accepted the request.
        settings._p15_service_write({
            "configuration_generation": current_generation + 1,
        })
        return self._p15_ack(
            "accepted",
            _("Fulfillment mode change accepted for verification."),
            command_id=envelope.command_id,
            store_id=store.id,
            generation=current_generation + 1,
        )
