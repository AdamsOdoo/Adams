/** @odoo-module **/

/*
 * Shared V2 presentation contracts.
 *
 * This module contains only closed vocabularies, envelope normalization and
 * pure display helpers.  It deliberately has no Owl components or services;
 * the component files can therefore remain small and dependency-directed.
 */

import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import {
    CONNECTOR_RESPONSE_STATES,
    CONNECTOR_ROLE_LABELS,
    workflowLabel as canonicalWorkflowLabel,
    normalizeConnectorState,
    normalizeConnectorErrorCode,
    safeConnectorErrorMessage,
} from "../connector_shared_contracts";

export const RESPONSE_STATES = CONNECTOR_RESPONSE_STATES;

const STATUS_META = Object.freeze({
    healthy: { tone: "success", icon: "fa-check-circle", label: _t("Healthy") },
    success: { tone: "success", icon: "fa-check-circle", label: _t("Complete") },
    unknown: { tone: "neutral", icon: "fa-question-circle", label: _t("Unknown") },
    testing: { tone: "info", icon: "fa-refresh", label: _t("Testing connection") },
    connected: { tone: "success", icon: "fa-link", label: _t("Connected") },
    reconnect_required: {
        tone: "danger",
        icon: "fa-unlink",
        label: _t("Reconnect required"),
    },
    reconnect_needed: {
        tone: "danger",
        icon: "fa-unlink",
        label: _t("Reconnect required"),
    },
    active: { tone: "success", icon: "fa-play-circle", label: _t("Active") },
    draft: { tone: "neutral", icon: "fa-pencil", label: _t("Draft") },
    retired: { tone: "neutral", icon: "fa-archive", label: _t("Retired") },
    incomplete: { tone: "warning", icon: "fa-exclamation-circle", label: _t("Incomplete") },
    valid: { tone: "success", icon: "fa-check-circle", label: _t("Valid") },
    setup_incomplete: {
        tone: "warning",
        icon: "fa-cog",
        label: _t("Setup incomplete"),
    },
    complete_current: {
        tone: "success",
        icon: "fa-check-circle",
        label: _t("Complete and current"),
    },
    ready: { tone: "success", icon: "fa-check-circle", label: _t("Ready") },
    succeeded: { tone: "success", icon: "fa-check-circle", label: _t("Succeeded") },
    queued: { tone: "info", icon: "fa-hourglass-start", label: _t("Queued") },
    skipped: { tone: "neutral", icon: "fa-forward", label: _t("Skipped") },
    retry_waiting: { tone: "warning", icon: "fa-clock-o", label: _t("Retry scheduled") },
    partially_succeeded: {
        tone: "warning",
        icon: "fa-check-circle",
        label: _t("Partially complete"),
    },
    info: { tone: "info", icon: "fa-info-circle", label: _t("Information") },
    warning: { tone: "warning", icon: "fa-exclamation-circle", label: _t("Needs review") },
    degraded: { tone: "warning", icon: "fa-exclamation-circle", label: _t("Degraded") },
    stale: { tone: "warning", icon: "fa-clock-o", label: _t("Stale") },
    waiting: { tone: "warning", icon: "fa-clock-o", label: _t("Waiting") },
    running: { tone: "info", icon: "fa-refresh", label: _t("In progress") },
    admitted: { tone: "info", icon: "fa-hourglass-start", label: _t("Admitted") },
    requested: { tone: "info", icon: "fa-hourglass-start", label: _t("Requested") },
    disabled: { tone: "neutral", icon: "fa-minus-circle", label: _t("Disabled") },
    not_ready: { tone: "warning", icon: "fa-exclamation-circle", label: _t("Not ready") },
    paused: { tone: "warning", icon: "fa-pause-circle", label: _t("Paused") },
    attention_required: {
        tone: "warning",
        icon: "fa-exclamation-circle",
        label: _t("Needs attention"),
    },
    manual_review: {
        tone: "warning",
        icon: "fa-hand-paper-o",
        label: _t("Manual review"),
    },
    blocked_manual_review: {
        tone: "warning",
        icon: "fa-hand-paper-o",
        label: _t("Manual review"),
    },
    critical: { tone: "danger", icon: "fa-exclamation-triangle", label: _t("Critical") },
    danger: { tone: "danger", icon: "fa-exclamation-triangle", label: _t("Blocked") },
    blocked: { tone: "danger", icon: "fa-ban", label: _t("Blocked") },
    disconnected: { tone: "danger", icon: "fa-unlink", label: _t("Disconnected") },
    invalid: { tone: "danger", icon: "fa-times-circle", label: _t("Connection needs repair") },
    terminal_error: {
        tone: "danger",
        icon: "fa-times-circle",
        label: _t("Could not complete"),
    },
    failed_terminal: {
        tone: "danger",
        icon: "fa-times-circle",
        label: _t("Failed permanently"),
    },
    failed_final: {
        tone: "danger",
        icon: "fa-times-circle",
        label: _t("Failed permanently"),
    },
    failed_retryable: {
        tone: "warning",
        icon: "fa-clock-o",
        label: _t("Temporarily delayed"),
    },
    retryable_error: {
        tone: "warning",
        icon: "fa-clock-o",
        label: _t("Temporarily delayed"),
    },
    pending: { tone: "warning", icon: "fa-hourglass-start", label: _t("Pending") },
    sending: { tone: "info", icon: "fa-refresh", label: _t("Sending") },
    accepted: { tone: "info", icon: "fa-check", label: _t("Accepted") },
    verified: { tone: "success", icon: "fa-check-circle", label: _t("Verified") },
    needs_attention: {
        tone: "warning",
        icon: "fa-exclamation-circle",
        label: _t("Needs attention"),
    },
    rejected: { tone: "danger", icon: "fa-times-circle", label: _t("Rejected") },
    failed_clean: { tone: "danger", icon: "fa-times-circle", label: _t("Not applied") },
    uncertain: { tone: "warning", icon: "fa-question-circle", label: _t("Outcome uncertain") },
    applied: { tone: "success", icon: "fa-check-circle", label: _t("Applied") },
    not_applied: { tone: "neutral", icon: "fa-ban", label: _t("Not applied") },
    offline: { tone: "warning", icon: "fa-wifi", label: _t("Offline") },
    cancelled: { tone: "neutral", icon: "fa-ban", label: _t("Cancelled") },
    loading: { tone: "neutral", icon: "fa-circle-o-notch", label: _t("Loading") },
    refreshing: { tone: "info", icon: "fa-refresh", label: _t("Refreshing") },
    empty: { tone: "neutral", icon: "fa-inbox", label: _t("Nothing here yet") },
    unconfigured: { tone: "neutral", icon: "fa-cog", label: _t("Setup required") },
    filtered_empty: { tone: "neutral", icon: "fa-filter", label: _t("No matching records") },
    permission_empty: { tone: "neutral", icon: "fa-lock", label: _t("Access is limited") },
    partial: { tone: "warning", icon: "fa-pie-chart", label: _t("Partially available") },
    conflict: { tone: "warning", icon: "fa-exchange", label: _t("Changed while you were working") },
    neutral: { tone: "neutral", icon: "fa-circle-o", label: _t("Unknown") },
});

const OWNER_ROLE_LABELS = Object.freeze({
    ...CONNECTOR_ROLE_LABELS,
    auditor: _t("Auditor"),
    system: _t("System"),
});

const TRIGGER_LABELS = Object.freeze({
    user: _t("User"),
    cron: _t("Scheduled"),
    webhook: _t("Shopify webhook"),
    odoo_event: _t("Odoo event"),
    reconciliation: _t("Reconciliation"),
    system: _t("System"),
});

const EVENT_KIND_LABELS = Object.freeze({
    response_interrupted: _t("Response interrupted"),
    request_created: _t("Request created"),
    admitted: _t("Work admitted"),
    started: _t("Work started"),
    completed: _t("Work completed"),
    retry_scheduled: _t("Retry scheduled"),
    verification_started: _t("Verification started"),
    verification_completed: _t("Verification completed"),
});

const OPERATION_LABELS = Object.freeze({
    import: _t("Import"),
    export: _t("Export"),
    tracking_update: _t("Tracking update"),
    reconciliation: _t("Reconciliation"),
    product_import: _t("Product import"),
    order_import: _t("Order import"),
    inventory_sync: _t("Inventory sync"),
    fulfillment_sync: _t("Fulfillment sync"),
});

const STATE_COPY = Object.freeze({
    loading: {
        title: _t("Loading connector evidence"),
        detail: _t("The connector is loading the selected store's stored evidence."),
    },
    refreshing: {
        title: _t("Refreshing stored evidence"),
        detail: _t("Existing evidence remains visible while the bounded read is updated."),
    },
    empty: {
        title: _t("Nothing needs attention"),
        detail: _t("The selected store has no records for this view."),
    },
    success: {
        title: _t("Complete"),
        detail: _t("The selected store has current connector evidence."),
    },
    unconfigured: {
        title: _t("Finish setting up this store"),
        detail: _t("Complete the guided setup before connector work can begin."),
    },
    filtered_empty: {
        title: _t("No records match these filters"),
        detail: _t("Clear one or more filters to review the available records."),
    },
    permission_empty: {
        title: _t("There is no data to show for this role"),
        detail: _t("Your access boundary is preserved; ask an administrator for access if needed."),
    },
    partial: {
        title: _t("Some evidence is unavailable"),
        detail: _t("The available sections remain visible. Retry the unavailable portion when ready."),
    },
    manual_review: {
        title: _t("A decision is required"),
        detail: _t("Review the available evidence before continuing this work."),
    },
    retryable_error: {
        title: _t("This view is temporarily unavailable"),
        detail: _t("No business action was claimed. Retry when the connector is available again."),
    },
    terminal_error: {
        title: _t("This view could not be loaded"),
        detail: _t("No action was taken. Review the message and use the available recovery path."),
    },
    stale: {
        title: _t("This information may be out of date"),
        detail: _t("Refresh the bounded read before making a decision."),
    },
    offline: {
        title: _t("You are offline"),
        detail: _t("Nothing was submitted. Your current page state is preserved until the connection returns."),
    },
    conflict: {
        title: _t("This changed while you were working"),
        detail: _t("Refresh the server evidence before choosing an action again."),
    },
});

const ACTION_PREFERENCE = Object.freeze([
    "open_attention",
    "repair_connection",
    "resume_setup",
    "review",
    "retry",
    "refresh",
]);

// Owl's `optional` flag permits an omitted prop, not an explicit null.  The
// server envelope and action projections legitimately use null for absent
// values, so the presentation boundary declares those values deliberately.
export const NULLABLE_OBJECT = Object.freeze({
    type: [Object, { value: null }],
    optional: true,
});
export const NULLABLE_STRING = Object.freeze({
    type: [String, { value: null }],
    optional: true,
});
export const NULLABLE_BOOLEAN = Object.freeze({
    type: [Boolean, { value: null }],
    optional: true,
});
export const NULLABLE_FUNCTION = Object.freeze({
    type: [Function, { value: null }],
    optional: true,
});

export function isRecord(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function localeDirection() {
    // Odoo's localization proxy can throw before the locale service has
    // resolved.  The component must remain mountable during that window.
    try {
        return localization.direction || "ltr";
    } catch {
        return "ltr";
    }
}

export function nonEmptyString(value) {
    return typeof value === "string" && value.trim() ? value : "";
}

function normalizeState(value) {
    return normalizeConnectorState(value);
}

function statusMeta(value) {
    const key = nonEmptyString(value).toLowerCase();
    return STATUS_META[key] || STATUS_META.neutral;
}

function mappedLabel(value, labels, fallback) {
    const key = nonEmptyString(value).toLowerCase();
    return labels[key] || fallback;
}

export function workflowLabel(value) {
    return canonicalWorkflowLabel(value);
}

export function ownerRoleLabel(value) {
    return mappedLabel(value, OWNER_ROLE_LABELS, _t("Assigned owner"));
}

export function triggerTypeLabel(value) {
    const key = isRecord(value) ? value.type : value;
    return mappedLabel(key, TRIGGER_LABELS, _t("Recorded trigger"));
}

export function eventKindLabel(value) {
    return mappedLabel(value, EVENT_KIND_LABELS, _t("Evidence update"));
}

export function operationLabel(value) {
    return mappedLabel(value, OPERATION_LABELS, _t("Connector work"));
}

export function dataObject(value) {
    return isRecord(value) ? value : null;
}

/** Normalize the common response envelope without deriving operational state. */
export function readEnvelope(value) {
    const input = isRecord(value) ? value : {};
    const data = dataObject(input.data);
    const rawState = input.status || input.state || (data ? "success" : "loading");
    const state = normalizeState(rawState);
    const error = dataObject(input.error);
    const providedErrorMessage = safeConnectorErrorMessage(
        error && (error.message || error.detail) || input.message,
    );
    const errorCode = normalizeConnectorErrorCode(
        error && (error.code || error.error_code) || input.error_code,
    );
    return Object.freeze({
        contractVersion: input.contract_version === undefined ? 1 : input.contract_version,
        generatedAt: nonEmptyString(input.generated_at),
        dataThrough: nonEmptyString(input.data_through),
        storeGeneration: input.store_generation,
        correlationId: nonEmptyString(input.correlation_id),
        state,
        data,
        error,
        errorCode,
        errorMessage:
            providedErrorMessage || _t("The connector did not provide a further explanation."),
        hasErrorMessage: Boolean(providedErrorMessage),
        hasData: Boolean(data),
        isRefreshing: state === "refreshing",
    });
}

export function stateMeta(value) {
    // Domain status and response state share visual semantics but are not the
    // same closed vocabulary, so do not route domain values through state
    // normalization.
    return statusMeta(value);
}

export function actionFor(value, preferredKeys = ACTION_PREFERENCE) {
    const actions = Array.isArray(value) ? value.filter(isRecord) : [];
    for (const key of preferredKeys) {
        const action = actions.find((candidate) => candidate.key === key);
        if (action) {
            return action;
        }
    }
    return actions[0] || null;
}

export function allowedStore(value, selectedId) {
    const stores = Array.isArray(value) ? value.filter(isRecord) : [];
    return stores.find((store) => String(store.id) === String(selectedId)) || null;
}

export function storeOptions(data) {
    if (!isRecord(data)) {
        return [];
    }
    const options = Array.isArray(data.allowed_stores)
        ? data.allowed_stores
        : Array.isArray(data.stores)
          ? data.stores
          : [];
    return options.filter((store) => isRecord(store) && store.id !== undefined);
}

export function stateCopy(value) {
    return STATE_COPY[normalizeState(value)] || STATE_COPY.terminal_error;
}

export function safeText(value, fallback = "—") {
    if (value === null || value === undefined || value === false || value === "") {
        return fallback;
    }
    if (typeof value === "string" || typeof value === "number") {
        return String(value);
    }
    if (isRecord(value)) {
        return nonEmptyString(value.label || value.value || value.name) || fallback;
    }
    return fallback;
}

export function formatAge(value) {
    const seconds =
        typeof value === "number"
            ? value
            : typeof value === "string" && value.trim()
              ? Number(value)
              : NaN;
    if (!Number.isFinite(seconds) || seconds < 0) {
        return _t("Age unavailable");
    }
    if (seconds < 60) {
        return _t("Less than a minute");
    }
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) {
        return `${minutes} ${minutes === 1 ? _t("minute") : _t("minutes")}`;
    }
    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
        return `${hours} ${hours === 1 ? _t("hour") : _t("hours")}`;
    }
    const days = Math.floor(hours / 24);
    return `${days} ${days === 1 ? _t("day") : _t("days")}`;
}

export function callback(props, name, ...args) {
    if (props && typeof props[name] === "function") {
        props[name](...args);
    }
}

export function envelopeState(props) {
    return readEnvelope(props && props.envelope);
}

export const V2ResponseStates = RESPONSE_STATES;
