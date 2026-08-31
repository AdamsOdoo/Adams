"""Named P15 read/scan/reconciliation operation options and admission."""

from __future__ import annotations

from odoo import _, api, models
from odoo.exceptions import ValidationError, UserError

from ..domain.dto import OperationOptionDTO
from ..domain.p15_foundation import (
    READ_ONLY_OPERATION_SPECS,
    operation_spec,
)
from .shopify_connector_p15_command_replay import p15_command_endpoint


class ShopifyConnectorP15Operations(models.AbstractModel):
    """Extend the named application facade with a closed operation registry."""

    _inherit = "shopify.connector.application.facade"

    @api.model
    def get_operation_options_v1(self, store_id):
        ui = self._p15_ui()
        ui._p15_require_admin()
        store = ui._p15_require_store(store_id)
        settings = ui._p15_settings_for_read(store)
        options = []
        for spec in READ_ONLY_OPERATION_SPECS:
            key = spec["key"]
            if not self._p15_operation_is_installed(store, key):
                continue
            readiness, reason = self._p15_operation_readiness(
                store, settings, spec,
            )
            options.append(OperationOptionDTO(
                operation_key=key,
                label=_(spec["label"]),
                workflow=self._p15_operation_workflow(key),
                mode=spec["mode"],
                required_role="administrator",
                available_scopes=("store",),
                filter_schema={},
                source_of_truth_summary=(
                    "Existing store settings, connection evidence, and "
                    "connector job records."
                ),
                side_effect_summary=(
                    "Starts one named bounded read/scan job; no remote "
                    "mutation is available through this endpoint."
                ),
                readiness=readiness,
                disabled_reason=reason,
            ))
        return ui._p15_envelope(
            store.connection_generation,
            {
                "operations": tuple(options),
                "allowed_actions": ui._p15_admin_actions(),
            },
            through=store.write_date,
        )

    @api.model
    def _p15_operation_workflow(self, operation_key):
        return {
            "core_readiness_check": "core",
            "core_test_connection": "core",
            "product_import_scan": "catalog",
            "inventory_location_sync": "inventory",
            "fulfillment_reconciliation_check": "fulfillment",
        }.get(operation_key, "core")

    @api.model
    def _p15_operation_is_installed(self, store, operation_key):
        if operation_key in ("core_readiness_check", "core_test_connection"):
            return True
        if operation_key == "product_import_scan":
            return hasattr(store, "action_sync_products_now")
        if operation_key == "inventory_location_sync":
            return (
                "shopify.connector.inventory.service" in self.env
                and hasattr(
                    self.env["shopify.connector.inventory.service"],
                    "action_refresh_shopify_locations",
                )
            )
        if operation_key == "fulfillment_reconciliation_check":
            return (
                "shopify.connector.fulfillment.service" in self.env
                and hasattr(
                    self.env["shopify.connector.fulfillment.service"],
                    "_enqueue_once",
                )
            )
        return False

    @api.model
    def _p15_operation_readiness(self, store, settings, spec):
        activation = getattr(store, "activation_state", "active")
        if activation in ("paused", "retired"):
            return "paused", "The store activation is %s." % activation
        if spec["requires_connected"] and store.state != "connected":
            return "not_ready", "The store must be connected first."
        if spec["key"] == "core_test_connection":
            if store.state not in (
                "setup_incomplete", "connected", "reconnect_needed",
            ):
                return "not_ready", "The connection probe is unavailable in this state."
            if not store.credential_present:
                return "not_ready", "Enter a credential before testing the connection."
        flag_by_operation = {
            "product_import_scan": "product_domain_enabled",
            "inventory_location_sync": "inventory_domain_enabled",
            "fulfillment_reconciliation_check": "fulfillment_domain_enabled",
        }
        field_name = flag_by_operation.get(spec["key"])
        if field_name and not (settings and getattr(settings, field_name, False)):
            return "not_ready", "The required domain is not enabled."
        return "ready", None

    @api.model
    @p15_command_endpoint("start_operation_v1")
    def start_operation_v1(self, command):
        envelope, payload = self._p15_parse_command(
            command, "start_operation_v1",
        )
        unknown = set(payload) - {"operation_key"}
        if unknown:
            raise ValidationError(_(
                "Unsupported operation fields: %(fields)s",
                fields=", ".join(sorted(str(item) for item in unknown)),
            ))
        try:
            spec = operation_spec(payload.get("operation_key"))
        except (TypeError, ValueError) as exc:
            raise ValidationError(_(
                "The operation is not an installed read-only control."
            )) from exc
        store = self._p15_store_for_command(envelope)
        _state, generation, matches = self._p15_check_store_generation(
            store, envelope.expected_generation,
        )
        if not matches:
            return self._p15_ack(
                "conflict",
                _("The store connection changed; reload before starting work."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=generation,
            )
        if not self._p15_operation_is_installed(store, spec["key"]):
            raise ValidationError(_("The operation is not installed."))
        readiness, reason = self._p15_operation_readiness(
            store, self._p15_settings_for_command(store), spec,
        )
        if readiness != "ready":
            return self._p15_ack(
                "blocked", reason or _("The operation is not ready."),
                command_id=envelope.command_id,
                store_id=store.id,
                generation=generation,
            )

        key = spec["key"]
        job = False
        if key == "core_readiness_check":
            result = self.env["shopify.connector.readiness.check"].run_for_store(store)
            job = result.get("job")
        elif key == "core_test_connection":
            store.action_test_connection()
            job = self.env["shopify.connector.job"].sudo().search([
                ("store_id", "=", store.id),
                ("job_type", "=", "core_test_connection"),
            ], order="id desc", limit=1)
        elif key == "product_import_scan":
            job = store.action_sync_products_now()
        elif key == "inventory_location_sync":
            job = self.env[
                "shopify.connector.inventory.service"
            ].action_refresh_shopify_locations(store.id)
        elif key == "fulfillment_reconciliation_check":
            job = self.env[
                "shopify.connector.fulfillment.service"
            ]._enqueue_once(
                store,
                "reconciliation",
                spec["job_type"],
                "p15-reconciliation:%d:%s" % (store.id, envelope.command_id),
                "shopify.connector.store",
                store.id,
            )
        else:  # pragma: no cover - operation_spec is closed above
            raise ValidationError(_("The operation is not supported."))
        job_id = getattr(job, "id", False)
        if not job_id:
            raise UserError(_("The operation did not produce a valid job."))
        return self._p15_ack(
            "completed" if key == "core_readiness_check" else "accepted",
            _("The named operation was admitted."),
            command_id=envelope.command_id,
            store_id=store.id,
            generation=generation,
            run_ref="job:%d" % job_id,
        )


__all__ = ["ShopifyConnectorP15Operations"]
