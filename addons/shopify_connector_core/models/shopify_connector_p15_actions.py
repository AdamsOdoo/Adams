"""Closed P15 administrator action projections.

The action vocabulary is kept separate from the larger read projection so the
P15 controller and every generated DTO stay below the source-size review
ceiling.  This is an inherited method extension, not another application
facade or client root.
"""

from __future__ import annotations

from odoo import _, api, models
from odoo.exceptions import ValidationError

from ..domain.dto import AllowedActionDTO
from ..domain.states import Role
from .shopify_connector_p15_shared import (
    P15_UI_ACTION_KEYS,
)
from ..domain.store_admin import MAX_SUPPORTED_STORES


class ShopifyConnectorP15Actions(models.AbstractModel):
    """Advertise only implemented P15 commands and authorized targets."""

    _inherit = "shopify.connector.ui.facade"

    @api.model
    def _p15_action(
        self, key, label, *, required_role=None, consequence=None,
        requires_reason=False, input_schema=None, target=None,
    ):
        if key not in P15_UI_ACTION_KEYS:
            raise ValidationError(_(
                "The requested administrator action is not implemented."
            ))
        return AllowedActionDTO(
            key=key,
            label=label,
            required_role=required_role,
            consequence=consequence,
            requires_reason=requires_reason,
            input_schema=input_schema or {},
            target=target,
        )

    @api.model
    def _p15_admin_actions(self, store=None, settings=None):
        if not (
            self.env.su
            or self.env.user.has_group(
                "shopify_connector_core.group_shopify_connector_admin"
            )
        ):
            return ()
        admin_role = Role.ADMINISTRATOR.value
        actions = []
        target = self._authorized_store_admin_target()
        if not target:
            target = self._authorized_native_collection_target(
                "shopify.connector.store",
                domain=[("company_id", "=", self.env.company.id)],
                label=_("Manage Shopify stores"),
            )
        if target:
            actions.append(self._p15_action(
                "manage_stores", _("Manage stores"),
                required_role=admin_role, target=target,
            ))
        store_count = self._search_count(
            "shopify.connector.store",
            [("company_id", "=", self.env.company.id)],
        )
        if target and store_count < MAX_SUPPORTED_STORES:
            actions.append(self._p15_action(
                "create_store", _("Add a store"), required_role=admin_role,
            ))
        if not store:
            return tuple(actions)
        if settings:
            settings_target = self._authorized_native_record_target(
                settings,
                store,
                action_key="open_store_settings",
                label=_("Edit store settings"),
            )
            if settings_target:
                actions.append(self._p15_action(
                    "open_store_settings", _("Edit store settings"),
                    required_role=admin_role, target=settings_target,
                ))
        actions.extend((
            self._p15_action(
                "open_setup", _("Open setup"), required_role=admin_role,
            ),
            self._p15_action(
                "open_readiness", _("Open readiness"), required_role=admin_role,
            ),
        ))
        activation_state = getattr(store, "activation_state", "draft")
        if (
            activation_state != "retired"
            and store.state not in ("disconnecting", "disconnected")
        ):
            actions.extend((
                self._p15_action(
                    "test_connection", _("Test connection"),
                    required_role=admin_role,
                ),
                self._p15_action(
                    "replace_credential", _("Replace credential"),
                    required_role=admin_role,
                    input_schema={"type": "object", "required": ["auth_mode"]},
                ),
                self._p15_action(
                    "save_setup_step", _("Save setup step"),
                    required_role=admin_role,
                    input_schema={
                        "type": "object",
                        "required": ["step_key", "values"],
                    },
                ),
            ))
        if settings:
            actions.extend((
                self._p15_action(
                    "save_store_settings_group", _("Save settings"),
                    required_role=admin_role,
                    input_schema={
                        "type": "object",
                        "required": ["group_key", "values"],
                    },
                ),
                self._p15_action(
                    "set_workflow_state", _("Change workflow mode"),
                    required_role=admin_role,
                    input_schema={
                        "type": "object",
                        "required": ["workflow", "state"],
                    },
                ),
            ))
        if store.state == "connected" and activation_state == "active":
            actions.append(self._p15_action(
                "pause_store", _("Pause store"), required_role=admin_role,
            ))
        if store.state == "connected" and activation_state == "paused":
            actions.append(self._p15_action(
                "resume_store", _("Resume store"), required_role=admin_role,
            ))
        if store.state != "disconnected" and activation_state != "retired":
            actions.append(self._p15_action(
                "disconnect_store", _("Disconnect store"),
                required_role=admin_role,
            ))
        if (
            store.state == "connected"
            and activation_state == "draft"
            and getattr(store, "last_readiness_result", False) in ("pass", "warning")
        ):
            actions.append(self._p15_action(
                "activate_store", _("Activate store"), required_role=admin_role,
            ))
        if store.state == "disconnected" and activation_state != "retired":
            actions.append(self._p15_action(
                "retire_store", _("Retire store"),
                required_role=admin_role,
                requires_reason=True,
                input_schema={"type": "object", "required": ["reason"]},
            ))
        return tuple(actions)


__all__ = ["ShopifyConnectorP15Actions"]
