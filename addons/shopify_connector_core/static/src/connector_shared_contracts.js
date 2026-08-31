/** @odoo-module **/

/*
 * Canonical, transport-free vocabulary shared by the V2 Operations shell and
 * the subordinate Administrator/setup surfaces.
 *
 * This module intentionally contains no Odoo service, ORM call, router, or
 * command implementation.  It only makes the two inert UI families agree on
 * the server contract and fail closed when a DTO is incomplete.
 */

import { _t } from "@web/core/l10n/translation";

export const CONNECTOR_APPLICATION_MODEL = "shopify.connector.application.facade";

export const CONNECTOR_READ_METHODS = Object.freeze({
    overview: "get_overview_v1",
    attention: "search_attention_v1",
    attentionDetail: "get_attention_detail_v1",
    run: "get_run_v1",
    stores: "get_store_list_v1",
});

export const CONNECTOR_RESPONSE_STATES = Object.freeze([
    "loading",
    "refreshing",
    "success",
    "empty",
    "unconfigured",
    "filtered_empty",
    "permission_empty",
    "partial",
    "retryable_error",
    "manual_review",
    "terminal_error",
    "stale",
    "offline",
    "conflict",
]);

export const CONNECTOR_ROLES = Object.freeze([
    "administrator",
    "operator",
    "reviewer",
    "auditor",
]);

export const CONNECTOR_ROLE_LABELS = Object.freeze({
    administrator: _t("Administrator"),
    operator: _t("Operator"),
    reviewer: _t("Reviewer"),
    auditor: _t("Auditor"),
    no_access: _t("No access"),
});

export const CONNECTOR_WORKFLOWS = Object.freeze({
    products: _t("Products"),
    orders: _t("Orders"),
    inventory: _t("Inventory"),
    fulfillment: _t("Fulfillment"),
});

const WORKFLOW_ALIASES = Object.freeze({
    catalog: "products",
    product: "products",
    product_export: "products",
    sale: "orders",
    sales: "orders",
});

export const CONNECTOR_ACTION_KEYS = Object.freeze([
    "manage_stores",
    "open_store_settings",
    "open_native_record",
    "open_product_record",
    "open_order_record",
    "open_inventory_record",
    "open_fulfillment_review",
    "open_attention",
    "open_run",
    "refresh",
    "new_operation",
    "open_setup",
    "open_readiness",
    "open_diagnostics",
]);

export const CONNECTOR_ACTION_SERVICE_KEYS = new Set([
    "manage_stores",
    "open_store_settings",
    "open_native_record",
    "open_product_record",
    "open_order_record",
    "open_inventory_record",
    "open_fulfillment_review",
]);

// Canonical public codes mirror ``domain/errors.py`` and the V2 contract
// documentation.  Older aliases remain accepted at the transport boundary
// so an upgraded browser can safely read a response from one older worker.
export const CONNECTOR_ERROR_CODES = Object.freeze([
    "validation_error",
    "access_denied",
    "store_scope_mismatch",
    "stale_generation",
    "state_conflict",
    "readiness_blocked",
    "operation_conflict",
    "duplicate_command",
    "preview_stale",
    "shopify_throttled",
    "shopify_unavailable",
    "shopify_auth_required",
    "shopify_validation",
    "verification_required",
    "manual_review_required",
    "terminal_failure",
    "contract_version_unsupported",
]);

export const CONNECTOR_ERROR_ALIASES = Object.freeze({
    throttled: "shopify_throttled",
    service_unavailable: "shopify_unavailable",
    authentication_failed: "shopify_auth_required",
    manual_review: "manual_review_required",
    unsupported: "contract_version_unsupported",
});

export function normalizeConnectorErrorCode(value, fallback = "terminal_failure") {
    const candidate = nonEmptyString(value).toLowerCase();
    const normalized = CONNECTOR_ERROR_ALIASES[candidate] || candidate;
    if (CONNECTOR_ERROR_CODES.includes(normalized)) {
        return normalized;
    }
    return CONNECTOR_ERROR_CODES.includes(fallback) ? fallback : "terminal_failure";
}

const ACTION_SERVICE_TYPES = new Set(["ir.actions.act_window", "ir.actions.client"]);
const CONNECTOR_CLIENT_ACTION_TAGS = new Set(["shopify_connector_p16_admin"]);

export function isRecord(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function nonEmptyString(value) {
    return typeof value === "string" && value.trim() ? value.trim() : "";
}

const UNSAFE_ERROR_TEXT = /(?:access[ _-]?token|client[ _-]?secret|password|authorization|credential|traceback|debug)/i;

export function safeConnectorErrorMessage(value, fallback = "") {
    const message = nonEmptyString(value)
        .replace(/^\s*(?:RPC_ERROR|Odoo Server Error)\s*[:\-]\s*/i, "")
        .replace(/\s+/g, " ")
        .slice(0, 500);
    return message && !UNSAFE_ERROR_TEXT.test(message) ? message : fallback;
}

export function positiveId(value) {
    const id = typeof value === "string" && value.trim() ? Number(value) : value;
    return Number.isSafeInteger(id) && id > 0 ? id : null;
}

export function companyIdFromContext(context) {
    const source = isRecord(context) ? context : {};
    return positiveId(
        source.active_company_id || source.company_id || source.default_company_id,
    );
}

export function companyIdFromProps(props) {
    const action = isRecord(props && props.action) ? props.action : {};
    const context = isRecord(action.context) ? action.context : {};
    return companyIdFromContext(context);
}

export function normalizeWorkflowKey(value) {
    const key = nonEmptyString(isRecord(value) ? value.key || value.workflow : value).toLowerCase();
    return WORKFLOW_ALIASES[key] || (Object.prototype.hasOwnProperty.call(CONNECTOR_WORKFLOWS, key) ? key : "other");
}

export function workflowLabel(value) {
    return CONNECTOR_WORKFLOWS[normalizeWorkflowKey(value)] || _t("Other workflow");
}

export function normalizeConnectorState(value, fallback = "terminal_error") {
    const aliases = {
        ready: "success",
        loaded: "success",
        accepted: "success",
        completed: "success",
        verified: "success",
        error: "terminal_error",
        failed: "terminal_error",
        blocked: "terminal_error",
        retryable: "retryable_error",
        no_data: "empty",
        no_access: "permission_empty",
    };
    const candidate = nonEmptyString(value).toLowerCase();
    const normalized = aliases[candidate] || candidate;
    if (CONNECTOR_RESPONSE_STATES.includes(normalized)) {
        return normalized;
    }
    return CONNECTOR_RESPONSE_STATES.includes(fallback) ? fallback : "terminal_error";
}

export function collectServerActions(value) {
    if (!isRecord(value)) {
        return [];
    }
    const data = isRecord(value.data) ? value.data : value;
    const nested = [
        data,
        isRecord(data.health) ? data.health : null,
        isRecord(data.store) ? data.store : null,
        isRecord(data.detail) ? data.detail : null,
        isRecord(data.run) ? data.run : null,
        isRecord(data.lifecycle) ? data.lifecycle : null,
    ];
    return nested
        .flatMap((item) => (Array.isArray(item && item.allowed_actions) ? item.allowed_actions : []))
        .filter((action) => isRecord(action) && nonEmptyString(action.key));
}

export function actionIdentity(action) {
    if (!isRecord(action)) {
        return "";
    }
    return `${nonEmptyString(action.key)}::${nonEmptyString(action.item_ref)}`;
}

export function serverAllowsAction(value, action) {
    const identity = actionIdentity(action);
    const key = nonEmptyString(action && action.key);
    return Boolean(identity) && collectServerActions(value).some((candidate) =>
        actionIdentity(candidate) === identity ||
        (nonEmptyString(candidate.key) === key && !nonEmptyString(candidate.item_ref)),
    );
}

/**
 * Accept only a server-built native Odoo target.  The browser never creates
 * a model, domain, view, URL, or action id from an opaque UI payload.
 */
export function serverActionTarget(action) {
    if (!isRecord(action) || !CONNECTOR_ACTION_SERVICE_KEYS.has(nonEmptyString(action.key))) {
        return null;
    }
    const target = isRecord(action.target)
        ? action.target
        : isRecord(action.odoo_action)
          ? action.odoo_action
          : null;
    if (!target || !ACTION_SERVICE_TYPES.has(nonEmptyString(target.type))) {
        return null;
    }
    if (
        target.type === "ir.actions.act_window" &&
        !nonEmptyString(target.res_model)
    ) {
        return null;
    }
    if (
        target.type === "ir.actions.client" &&
        !CONNECTOR_CLIENT_ACTION_TAGS.has(nonEmptyString(target.tag))
    ) {
        return null;
    }
    return target;
}

/** A record DTO must carry the complete server-authorized target. */
export function recordAction(record, key = "open_native_record") {
    if (!isRecord(record)) {
        return null;
    }
    const actionKey = nonEmptyString(record.action_key) || key;
    const target = serverActionTarget({
        key: actionKey,
        target: record.target || record.odoo_action,
    });
    const itemRef = record.item_ref || record.ref || record.id;
    return target
        ? {
              key: actionKey,
              target,
              item_ref: itemRef === null || itemRef === undefined ? "" : String(itemRef),
          }
        : null;
}

/** Explicitly read-only, never a command target or inferred store count. */
export function isReadOnlyAllStores(value) {
    return isRecord(value) && value.kind === "all" && value.read_only === true;
}

export function unavailableAction(key, label, reason = "unavailable") {
    return Object.freeze({
        key: nonEmptyString(key),
        label: nonEmptyString(label) || _t("Action unavailable"),
        state: "unavailable",
        reason,
        allowed: false,
    });
}
