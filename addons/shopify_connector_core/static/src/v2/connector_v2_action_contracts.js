/** @odoo-module **/

/*
 * Client-action contract helpers.
 *
 * These are deliberately separate from the controller so the action shell's
 * security and polling decisions can be tested as pure functions.  The
 * controller remains the only module that owns local lifecycle state.
 */

import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import {
    CONNECTOR_ACTION_SERVICE_KEYS,
    CONNECTOR_APPLICATION_MODEL,
    CONNECTOR_READ_METHODS,
    CONNECTOR_ROLE_LABELS,
    isRecord,
    nonEmptyString,
    safeConnectorErrorMessage,
    serverActionTarget,
    serverAllowsAction,
} from "../connector_shared_contracts";

export const FACADE_MODEL = CONNECTOR_APPLICATION_MODEL;

export const RPC_METHODS = CONNECTOR_READ_METHODS;

export {
    isRecord,
    nonEmptyString,
    serverActionTarget,
    serverAllowsAction,
};

export const V2_VIEWS = Object.freeze({
    overview: "overview",
    attention: "attention",
    run: "run",
});

// Active run evidence is refreshed quickly; passive projections are quiet and
// bounded. These are presentation cadences, not execution guarantees.
export const POLL_INTERVAL_MS = Object.freeze({
    overview: 30_000,
    attention: 15_000,
    run: 5_000,
});

const ACTIVE_RUN_STATES = Object.freeze([
    "requested",
    "admitted",
    "running",
    "waiting",
]);

// Only these keys may hand a server-built native action to Odoo. The target
// itself must be returned by the server; the browser never creates a model,
// domain, view or action id. Command keys without a facade method fail closed.
export const ACTION_SERVICE_KEYS = CONNECTOR_ACTION_SERVICE_KEYS;

const ACCESS_ERROR_NAMES = new Set([
    "accesserror",
    "odoo.exceptions.accesserror",
    "permissionerror",
    "forbidden",
    "access_denied",
]);

const RETRYABLE_ERROR_NAMES = new Set([
    "connectionerror",
    "networkerror",
    "timeouterror",
    "odoonetworkerror",
    "rpc_network_error",
    "service_unavailable",
    "temporarily_unavailable",
]);

export const ROLE_LABELS = CONNECTOR_ROLE_LABELS;

export function positiveStoreId(value) {
    const number =
        typeof value === "number" && Number.isSafeInteger(value)
            ? value
            : typeof value === "string" && value.trim()
              ? Number(value)
              : NaN;
    return Number.isSafeInteger(number) && number > 0 ? number : null;
}

export function localeDirection() {
    try {
        return localization.direction || "ltr";
    } catch {
        return "ltr";
    }
}

function stableValue(value, ancestors = new Set()) {
    if (value === null || typeof value === "string" || typeof value === "boolean") {
        return value;
    }
    if (typeof value === "number") {
        return Number.isFinite(value) ? value : String(value);
    }
    if (value === undefined) {
        return "__undefined__";
    }
    if (Array.isArray(value)) {
        if (ancestors.has(value)) {
            return "__cycle__";
        }
        ancestors.add(value);
        const result = value.map((item) => stableValue(item, ancestors));
        ancestors.delete(value);
        return result;
    }
    if (isRecord(value)) {
        if (ancestors.has(value)) {
            return "__cycle__";
        }
        ancestors.add(value);
        const result = {};
        for (const key of Object.keys(value).sort()) {
            result[key] = stableValue(value[key], ancestors);
        }
        ancestors.delete(value);
        return result;
    }
    return String(value);
}

export function stableSerialize(value) {
    return JSON.stringify(stableValue(value));
}

/**
 * Compare a native action by its executable security tuple.
 *
 * AllowedActionDTO deliberately carries presentation and input metadata in
 * addition to the target.  A record projection only needs to carry the
 * action key, item reference, and target, so comparing the entire objects
 * would hide an otherwise server-authorized record link.  The target itself
 * is still compared canonically and is accepted only through the same
 * allowlisted native-action validator used by the action service.
 */
export function nativeActionMatches(candidate, wanted) {
    if (!isRecord(candidate) || !isRecord(wanted)) {
        return false;
    }
    if (
        nonEmptyString(candidate.key) !== nonEmptyString(wanted.key) ||
        nonEmptyString(candidate.item_ref) !== nonEmptyString(wanted.item_ref)
    ) {
        return false;
    }
    const candidateTarget = serverActionTarget(candidate);
    const wantedTarget = serverActionTarget(wanted);
    return Boolean(candidateTarget && wantedTarget) &&
        stableSerialize(candidateTarget) === stableSerialize(wantedTarget);
}

/** Ignore request-time metadata when deciding whether polling changed data. */
export function responseFingerprint(value) {
    if (!isRecord(value)) {
        return stableSerialize(value);
    }
    return stableSerialize({
        contract_version: value.contract_version,
        status: value.status,
        state: value.state,
        data: value.data,
        data_through: value.data_through,
        store_generation: value.store_generation,
        error: value.error,
        message: value.message,
    });
}

export function makeEnvelope(status, data = null, message = "") {
    const envelope = {
        contract_version: 1,
        status: status || "terminal_error",
        data,
    };
    if (nonEmptyString(message)) {
        envelope.message = nonEmptyString(message).slice(0, 500);
    }
    return envelope;
}

function errorName(value) {
    if (!isRecord(value)) {
        return "";
    }
    const data = isRecord(value.data) ? value.data : {};
    return nonEmptyString(data.name || data.type || data.code || value.name || value.code).toLowerCase();
}

function errorMessage(value) {
    if (!isRecord(value)) {
        return "";
    }
    const data = isRecord(value.data) ? value.data : {};
    // Odoo may prepend a transport marker. Keep only safe user-facing server
    // copy; tracebacks, debug text and credential-bearing values are hidden.
    return safeConnectorErrorMessage(data.message || data.detail || value.message);
}

/** Normalize Odoo transport errors without exposing debug/traceback fields. */
export function normalizeRpcError(value) {
    const name = errorName(value);
    const access = ACCESS_ERROR_NAMES.has(name) || /access|permission|forbidden/.test(name);
    const retryable =
        RETRYABLE_ERROR_NAMES.has(name) ||
        /network|timeout|temporar|unavailable|gateway|429|503/.test(name);
    const status = access ? "permission_empty" : retryable ? "retryable_error" : "terminal_error";
    const message =
        errorMessage(value) ||
        (access
            ? _t("Your role does not have access to this connector evidence.")
            : retryable
              ? _t("The connector is temporarily unavailable. No business action was claimed.")
              : _t("The connector could not load this evidence."));
    return Object.freeze({ status, message, retryable: !access && retryable });
}

export function isActiveRunEnvelope(envelope) {
    if (!isRecord(envelope)) {
        return false;
    }
    const data = isRecord(envelope.data) ? envelope.data : {};
    const run = isRecord(data.run) ? data.run : data;
    return ACTIVE_RUN_STATES.includes(nonEmptyString(run.state).toLowerCase());
}

function contextFromProps(props) {
    const action = isRecord(props && props.action) ? props.action : {};
    return isRecord(action.context) ? action.context : {};
}

export function initialStoreId(props) {
    const action = isRecord(props && props.action) ? props.action : {};
    const context = contextFromProps(props);
    return positiveStoreId(
        context.default_store_id ||
            context.store_id ||
            context.active_store_id ||
            (isRecord(action.params) && action.params.store_id)
    );
}

export function initialStoreName(props) {
    const action = isRecord(props && props.action) ? props.action : {};
    const context = contextFromProps(props);
    return nonEmptyString(
        context.default_store_name ||
            context.store_name ||
            (isRecord(action.params) && action.params.store_name)
    );
}

export function responseData(envelope) {
    return isRecord(envelope && envelope.data) ? envelope.data : {};
}
