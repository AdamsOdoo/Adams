/** @odoo-module **/

/*
 * P16 presentation contracts.
 *
 * This file contains presentation-only vocabulary and normalizers for the
 * P15 application facade.  It deliberately does not import an Odoo service,
 * inspect groups, construct an ORM domain, or infer authorization.  The
 * server response remains the source of truth; these helpers only keep the
 * shell deterministic while a response is loading, stale, or unavailable.
 */

import { _t } from "@web/core/l10n/translation";
import {
    CONNECTOR_ACTION_SERVICE_KEYS,
    CONNECTOR_APPLICATION_MODEL,
    CONNECTOR_READ_METHODS,
    CONNECTOR_RESPONSE_STATES,
    CONNECTOR_ROLE_LABELS,
    collectServerActions,
    isRecord,
    normalizeConnectorState,
    nonEmptyString,
    safeConnectorErrorMessage,
    serverActionTarget,
    serverAllowsAction,
} from "../connector_shared_contracts";

export const P16_APPLICATION_MODEL = CONNECTOR_APPLICATION_MODEL;
export const P16_READ_METHODS = CONNECTOR_READ_METHODS;
export const P16_ROLE_LABELS = CONNECTOR_ROLE_LABELS;
export const P16_ACTION_SERVICE_KEYS = CONNECTOR_ACTION_SERVICE_KEYS;
export const P16_STORE_LIST_LIMIT = 10;

export const P16_SURFACES = Object.freeze({
    LIST: "list",
    CREATE: "create",
    SETUP: "setup",
    READINESS: "readiness",
    SETTINGS: "settings",
    DIAGNOSTICS: "diagnostics",
});

export const P16_DETAIL_METHODS = Object.freeze({
    setup: "get_setup_v1",
    readiness: "get_store_readiness_v1",
    settings: "get_store_settings_v1",
    diagnostics: "get_store_admin_summary_v1",
});

export const P16_SETUP_PHASES = Object.freeze([
    Object.freeze({
        key: "store_credential",
        label: _t("Store and credential"),
        stepKeys: Object.freeze(["welcome", "identity", "credential"]),
    }),
    Object.freeze({
        key: "connection_scopes",
        label: _t("Connection and scopes"),
        stepKeys: Object.freeze(["scopes", "test_connection"]),
    }),
    Object.freeze({
        key: "workflows",
        label: _t("Workflows"),
        stepKeys: Object.freeze(["directions"]),
    }),
    Object.freeze({
        key: "locations",
        label: _t("Locations"),
        stepKeys: Object.freeze(["location_mapping"]),
    }),
    Object.freeze({
        key: "authority_protections",
        label: _t("Authority and protections"),
        stepKeys: Object.freeze(["source_of_truth", "notification", "first_push"]),
    }),
    Object.freeze({
        key: "readiness_activation",
        label: _t("Readiness and activation"),
        stepKeys: Object.freeze(["final_readiness", "review"]),
    }),
]);

// These values are safe facts but never controls in grouped Settings.  The
// backend owns the same boundary; the UI repeats it only to make the control
// affordance honest.  A forged command is still rejected by the server.
export const P16_READ_ONLY_SETTING_FIELDS = Object.freeze(new Set([
    "notification_default_enabled",
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
]));

export const P16_LIFECYCLE_COPY = Object.freeze({
    setup_incomplete: _t("Setup incomplete"),
    connected: _t("Connected"),
    reconnect_needed: _t("Reconnect required"),
    disconnecting: _t("Disconnecting"),
    disconnected: _t("Disconnected"),
    paused: _t("Paused"),
});

export const P16_ACTIVATION_COPY = Object.freeze({
    draft: _t("Draft"),
    active: _t("Active"),
    paused: _t("Paused"),
    retired: _t("Retired"),
});

export const P16_STATE_META = Object.freeze({
    loading: Object.freeze({ tone: "neutral", icon: "fa-circle-o-notch", title: _t("Loading") }),
    refreshing: Object.freeze({ tone: "info", icon: "fa-refresh", title: _t("Refreshing") }),
    success: Object.freeze({ tone: "success", icon: "fa-check-circle", title: _t("Ready") }),
    empty: Object.freeze({ tone: "neutral", icon: "fa-inbox", title: _t("No stores yet") }),
    filtered_empty: Object.freeze({ tone: "neutral", icon: "fa-filter", title: _t("No matching stores") }),
    conflict: Object.freeze({ tone: "warning", icon: "fa-exchange", title: _t("This changed while you were working") }),
    stale: Object.freeze({ tone: "warning", icon: "fa-clock-o", title: _t("Refresh required") }),
    permission_empty: Object.freeze({ tone: "neutral", icon: "fa-lock", title: _t("Access is restricted") }),
    unconfigured: Object.freeze({ tone: "neutral", icon: "fa-cog", title: _t("Setup required") }),
    partial: Object.freeze({ tone: "warning", icon: "fa-pie-chart", title: _t("Partially available") }),
    manual_review: Object.freeze({ tone: "warning", icon: "fa-hand-paper-o", title: _t("Manual review") }),
    offline: Object.freeze({ tone: "warning", icon: "fa-wifi", title: _t("Offline") }),
    not_applicable: Object.freeze({ tone: "neutral", icon: "fa-minus-circle", title: _t("Not applicable") }),
    action_required: Object.freeze({ tone: "warning", icon: "fa-exclamation-circle", title: _t("Action required") }),
    retryable_error: Object.freeze({ tone: "warning", icon: "fa-refresh", title: _t("Temporarily unavailable") }),
    terminal_error: Object.freeze({ tone: "danger", icon: "fa-exclamation-triangle", title: _t("Could not load this view") }),
});

export const P16_RESPONSE_STATES = CONNECTOR_RESPONSE_STATES;

export function asArray(value) {
    return Array.isArray(value) ? value : [];
}

export function asObject(value) {
    return isRecord(value) ? value : {};
}

export function normalizeResponseState(value, fallback = "loading") {
    return normalizeConnectorState(value, fallback);
}

/**
 * Normalize a P15 envelope without manufacturing server state.
 *
 * P15 read envelopes omit a `status` on successful reads, while command
 * acknowledgements carry one and usually have no `data`.  Both forms are
 * accepted here so a later additive response field does not break the shell.
 */
export function normalizeEnvelope(value, fallback = "loading") {
    const input = asObject(value);
    const data = isRecord(input.data) ? input.data : null;
    const rawStatus = input.status || input.state || (data ? "success" : fallback);
    const state = normalizeResponseState(rawStatus, fallback);
    const error = asObject(input.error);
    return Object.freeze({
        raw: input,
        state,
        data,
        status: typeof input.status === "string" ? input.status : null,
        contractVersion: input.contract_version,
        generatedAt: input.generated_at || null,
        dataThrough: input.data_through || null,
        storeGeneration: input.store_generation,
        correlationId: input.correlation_id || null,
        message: safeErrorMessage(input.message || error.message || error.detail),
        hasData: Boolean(data),
    });
}

export function safeErrorMessage(value) {
    return safeConnectorErrorMessage(
        value,
        _t("The server did not provide a safe explanation. Nothing was submitted."),
    );
}

export function stateMeta(value) {
    return P16_STATE_META[normalizeResponseState(value, "terminal_error")];
}

export function storeItems(envelope) {
    return asArray(asObject(envelope).data && asObject(envelope.data).stores)
        .filter((item) => isRecord(item) && isRecord(item.store));
}

export function storeFromItem(item) {
    return isRecord(item) && isRecord(item.store) ? item.store : null;
}

export function itemStoreId(item) {
    const store = storeFromItem(item);
    return store && store.id ? Number(store.id) : null;
}

export function findStoreItem(items, storeId) {
    const wanted = Number(storeId);
    return asArray(items).find((item) => itemStoreId(item) === wanted) || null;
}

export function serverActions(value) {
    if (Array.isArray(value)) {
        return value.filter((action) => isRecord(action) && typeof action.key === "string");
    }
    return collectServerActions(value);
}

/**
 * This is a presentation hint only.  It never substitutes for server
 * authorization: every command is sent to a server method that rechecks the
 * role, company, store, state and generation.
 */
export function hasServerAction(value, key) {
    return serverActions(value).some((action) => action.key === key);
}

export {
    isRecord,
    nonEmptyString,
    serverActionTarget,
    serverAllowsAction,
};

export function phaseForStep(stepKey) {
    return P16_SETUP_PHASES.find((phase) => phase.stepKeys.includes(stepKey)) || null;
}

export function setupPhaseRows(steps) {
    const source = asArray(steps).filter((step) => isRecord(step) && typeof step.step_key === "string");
    return P16_SETUP_PHASES.map((phase) => Object.freeze({
        ...phase,
        steps: Object.freeze(
            phase.stepKeys
                .map((key) => source.find((step) => step.step_key === key))
                .filter(Boolean),
        ),
    }));
}

export function nextSetupStep(steps, currentKey) {
    const source = asArray(steps).filter((step) => isRecord(step) && typeof step.step_key === "string");
    const currentIndex = source.findIndex((step) => step.step_key === currentKey);
    return currentIndex >= 0 && source[currentIndex + 1]
        ? source[currentIndex + 1].step_key
        : null;
}

export function canSelectSetupStep(steps, currentKey, targetKey) {
    const source = asArray(steps).filter(
        (step) => isRecord(step) && typeof step.step_key === "string",
    );
    const currentIndex = source.findIndex((step) => step.step_key === currentKey);
    const targetIndex = source.findIndex((step) => step.step_key === targetKey);
    return currentIndex >= 0 && targetIndex >= 0 && targetIndex <= currentIndex + 1;
}

export function stepState(step) {
    if (!isRecord(step)) {
        return "pending";
    }
    if (step.state === "completed" || step.state === "not_required") {
        return step.state;
    }
    return "pending";
}

export function settingsGroups(envelope) {
    return asArray(asObject(envelope).data && asObject(envelope.data).groups)
        .filter((group) => isRecord(group) && typeof group.key === "string");
}

export function settingsGeneration(envelope) {
    const data = asObject(asObject(envelope).data);
    const generation = Number(data.configuration_generation);
    return Number.isInteger(generation) && generation >= 0 ? generation : 0;
}

export function connectionGeneration(envelope, fallback = 0) {
    const generation = Number(asObject(envelope).storeGeneration);
    return Number.isInteger(generation) && generation >= 0 ? generation : fallback;
}

export function fieldIsReadOnly(field) {
    return !isRecord(field) || P16_READ_ONLY_SETTING_FIELDS.has(field.key);
}

export function fieldInputValue(field) {
    if (!isRecord(field)) {
        return "";
    }
    if (field.value === false || field.value === null || field.value === undefined) {
        return field.value_type === "boolean" ? false : "";
    }
    return field.value;
}

export function commandEnvelope({
    commandName,
    companyId,
    actorUid,
    expectedGeneration = 0,
    storeId = null,
    payload = {},
    trigger = "user",
    commandId = null,
    requestedAt = null,
} = {}) {
    const command = {
        contract_version: 1,
        command_id: commandId || newCommandId(),
        command_name: commandName,
        company_id: Number(companyId),
        expected_generation: Number(expectedGeneration),
        actor_uid: actorUid === null || actorUid === undefined ? null : Number(actorUid),
        trigger,
        requested_at: requestedAt || new Date().toISOString(),
        payload: isRecord(payload) ? payload : {},
    };
    if (storeId !== null && storeId !== undefined) {
        command.store_id = Number(storeId);
    }
    return command;
}

export function newCommandId() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
        return globalThis.crypto.randomUUID();
    }
    // UUID-shaped fallback for browsers/test runners without Web Crypto.  It
    // is only a request identity; the server remains authoritative.
    const random = () => Math.floor(Math.random() * 0x100000000).toString(16).padStart(8, "0");
    return `${random()}-${random().slice(0, 4)}-4${random().slice(0, 3)}-${[8, 9, "a", "b"][Math.floor(Math.random() * 4)]}${random().slice(0, 3)}-${random()}${random()}`;
}

export function actionLabel(actions, key, fallback) {
    const action = serverActions(actions).find((candidate) => candidate.key === key);
    return action && action.label ? action.label : fallback;
}
