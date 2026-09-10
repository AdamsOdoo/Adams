"""Shared P15 administrator constants and validation helpers.

This module has no model registration.  Keeping the vocabulary here lets the
store, settings, read, and command extensions remain cohesive and small while
the legacy p15_admin import continues to load them in order.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from odoo import _, fields
from odoo.exceptions import ValidationError

from ..domain.store_admin import LIFECYCLE_TRANSITIONS, MAX_SUPPORTED_STORES
from ..domain.p15_foundation import SETUP_STEP_PAYLOAD_FIELDS


P15_CAPACITY_ADVISORY_CLASSID = 0x53484F50  # ``SHOP``; xact-scoped
P15_MAX_LIST_LIMIT = MAX_SUPPORTED_STORES
P15_MAX_SEARCH_LENGTH = 120
P15_MAX_TEXT_SETTING_LENGTH = 2000
P15_CURSOR_RE = re.compile(r"^s:[1-9][0-9]{0,18}$")
P15_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
P15_SERVICE_SENTINEL_CONTEXT = "shopify_p15_service_sentinel"
P15_SERVICE_SENTINEL = object()

P15_COMMAND_NAMES = frozenset({
    "create_store_v1",
    "save_store_settings_group_v1",
    "save_setup_step_v1",
    "replace_credential_v1",
    "test_connection_v1",
    "activate_store_v1",
    "pause_store_v1",
    "resume_store_v1",
    "disconnect_store_v1",
    "retire_store_v1",
    "set_workflow_state_v1",
    "start_operation_v1",
})

# Browser-facing keys are intentionally a small, closed vocabulary.  Each
# command-bearing key below has a corresponding ``*_v1`` adapter in
# ``P15_COMMAND_NAMES``; the remaining keys are local navigation capabilities
# whose targets are either a server-owned native action or the existing P16
# subordinate surface.
P15_UI_ACTION_KEYS = frozenset({
    "manage_stores",
    "create_store",
    "open_store_settings",
    "open_setup",
    "open_readiness",
    "test_connection",
    "activate_store",
    "replace_credential",
    "save_setup_step",
    "save_store_settings_group",
    "set_workflow_state",
    "pause_store",
    "resume_store",
    "disconnect_store",
    "retire_store",
})

# These are the typed fields projected by the grouped P15 settings response.
# Connector-owned identity/evidence and fulfillment switch state are included
# only as read-only facts; the separate editable map below is the command's
# strict write allowlist.
P15_SETTINGS_GROUP_FIELDS = {
    "sync_domains": (
        "product_domain_enabled",
        "product_export_domain_enabled",
        "sale_domain_enabled",
        "inventory_domain_enabled",
        "fulfillment_domain_enabled",
    ),
    "direction_policy": (
        "product_first_sync_source",
        "price_source_of_truth",
        "media_source_of_truth",
    ),
    "notifications": (
        "notification_default_enabled",
    ),
    "retention": (
        "log_redaction_retention_days",
    ),
    "product": (
        "product_import_media_enabled",
        "product_import_refresh_mode",
        "product_import_attribute_conflict_mode",
        "product_scheduled_sync_enabled",
    ),
    "orders": (
        "order_confirmation_policy",
        "manual_gateway_policy",
        "approved_manual_gateways",
        "order_import_window",
        "pending_wait_expiry",
        "order_import_include_test",
        "order_scheduled_sync_enabled",
        "order_pricelist_id",
        "order_sales_team_id",
        "order_payment_term_id",
        "customer_fallback_partner_id",
    ),
    "inventory": (
        "inventory_scheduled_sync_enabled",
    ),
    # Fulfillment operating mode is a state-machine action
    # (`action_start_mode2_switch`/`action_rollback_to_mode1`), not a plain
    # field update.  The protected
    # fields are nevertheless projected read-only so an Administrator can
    # see the effective mode, switch nonce/state and notification gate in the
    # same typed settings response.
    "fulfillment": (
        "fulfillment_operating_mode",
        "fulfillment_switch_in_progress",
        "fulfillment_mode_switch_nonce",
        "fulfillment_requested_mode",
        "fulfillment_mode_switch_state",
        "fulfillment_mode_switch_job_id",
        "fulfillment_mode_switch_failure_reason",
        "fulfillment_mode_switch_next_action",
        "fulfillment_mode_switch_next_retry_at",
        "fulfillment_mode_switch_is_stale",
        "fulfillment_mode_switch_verified_at",
        "fulfillment_last_mode_switch_at",
        "fulfillment_notification_confirmed",
    ),
}

# A grouped settings projection may include connector-owned evidence, but the
# grouped write command may only edit the merchant policy fields below.  Keep
# this separate from ``P15_SETTINGS_GROUP_FIELDS`` so read DTOs do not hide
# fulfillment state merely because it is intentionally not writable.
P15_EDITABLE_SETTINGS_GROUP_FIELDS = {
    key: tuple(
        field_name for field_name in fields_list
        if field_name not in {
            "fulfillment_operating_mode",
            "fulfillment_switch_in_progress",
            "fulfillment_mode_switch_nonce",
            "fulfillment_requested_mode",
            "fulfillment_mode_switch_state",
            "fulfillment_mode_switch_job_id",
            "fulfillment_mode_switch_failure_reason",
            "fulfillment_mode_switch_next_action",
            "fulfillment_mode_switch_next_retry_at",
            "fulfillment_mode_switch_is_stale",
            "fulfillment_mode_switch_verified_at",
            "fulfillment_last_mode_switch_at",
            "fulfillment_notification_confirmed",
        }
    )
    for key, fields_list in P15_SETTINGS_GROUP_FIELDS.items()
}

# One authoritative policy vocabulary drives the generation fence.  Runtime
# progress/checkpoint fields are intentionally absent; every merchant choice,
# setup-state choice, V2 mode and effective fulfillment policy is present.
P15_CONFIGURATION_POLICY_FIELDS = frozenset(
    set().union(*P15_EDITABLE_SETTINGS_GROUP_FIELDS.values())
    | {
        "setup_step_payloads",
        "setup_wizard_step_key",
        "setup_wizard_step",
        "v2_ui_mode",
        "v2_gateway_mode",
        "v2_runtime_mode",
        "fulfillment_operating_mode",
        "fulfillment_requested_mode",
        "fulfillment_notification_confirmed",
    }
)

P15_SETTINGS_GROUP_LABELS = {
    "sync_domains": "Synchronization domains",
    "direction_policy": "Direction and source of truth",
    "notifications": "Notifications",
    "retention": "Log retention",
    "product": "Catalog",
    "orders": "Orders",
    "inventory": "Inventory",
    "fulfillment": "Fulfillment",
}

P15_READINESS_GROUP_LABELS = {
    "essential": "Required checks",
    "warning": "Warnings",
}

# Keep the semantic setup vocabulary visible to Odoo/source-contract callers
# without duplicating its allowlist in a model module.
P15_SETUP_STEP_PAYLOAD_FIELDS = SETUP_STEP_PAYLOAD_FIELDS


def _p15_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        result = value
    else:
        result = fields.Datetime.to_datetime(value)
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _p15_parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(_("The command timestamp is invalid.")) from exc
    else:
        raise ValidationError(_("The command timestamp is required."))
    if result.tzinfo is None or result.utcoffset() != timezone.utc.utcoffset(result):
        raise ValidationError(_("The command timestamp must be UTC."))
    return result


def _p15_positive_id(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError(_("%(name)s must be a positive integer.", name=name))
    return value


def _p15_nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(_("%(name)s must be a non-negative integer.", name=name))
    return value


def _p15_safe_text(value: Any, name: str, *, max_length: int = P15_MAX_TEXT_SETTING_LENGTH) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(_("%(name)s must be non-empty.", name=name))
    value = value.strip()
    if len(value) > max_length:
        raise ValidationError(_("%(name)s is too long.", name=name))
    return value

__all__ = [
    "P15_CAPACITY_ADVISORY_CLASSID",
    "P15_COMMAND_NAMES",
    "P15_UI_ACTION_KEYS",
    "P15_CURSOR_RE",
    "P15_CONFIGURATION_POLICY_FIELDS",
    "P15_EDITABLE_SETTINGS_GROUP_FIELDS",
    "P15_MAX_LIST_LIMIT",
    "P15_MAX_SEARCH_LENGTH",
    "P15_MAX_TEXT_SETTING_LENGTH",
    "P15_READINESS_GROUP_LABELS",
    "P15_SERVICE_SENTINEL",
    "P15_SERVICE_SENTINEL_CONTEXT",
    "P15_SETTINGS_GROUP_FIELDS",
    "P15_SETTINGS_GROUP_LABELS",
    "P15_SETUP_STEP_PAYLOAD_FIELDS",
    "P15_SHA256_RE",
    "_p15_datetime",
    "_p15_nonnegative_int",
    "_p15_parse_datetime",
    "_p15_positive_id",
    "_p15_safe_text",
]
