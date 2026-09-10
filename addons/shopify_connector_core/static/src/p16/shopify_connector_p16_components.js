/** @odoo-module **/

/*
 * P16 presentational components.  They accept server-shaped props and emit
 * opaque ids, semantic step keys, or explicit callback payloads.  They never
 * call ORM, inspect user groups, decide readiness, or manufacture actions.
 */

import { Component, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

import {
    P16_ACTIVATION_COPY,
    P16_LIFECYCLE_COPY,
    asArray,
    asObject,
    canSelectSetupStep,
    fieldInputValue,
    fieldIsReadOnly,
    hasServerAction,
    itemStoreId,
    normalizeResponseState,
    phaseForStep,
    serverActions,
    setupPhaseRows,
    stateMeta,
    storeFromItem,
    storeItems,
    stepState,
} from "@shopify_connector_core/p16/shopify_connector_p16_contract";
import { P16SetupStepControls } from "./shopify_connector_p16_setup_controls";

function callback(props, name, ...args) {
    if (props && typeof props[name] === "function") {
        return props[name](...args);
    }
    return undefined;
}

function display(value, fallback = "—") {
    if (value === false || value === null || value === undefined || value === "") {
        return fallback;
    }
    return String(value);
}

function resultLabel(result) {
    return {
        pass: _t("Passed"),
        warning: _t("Worth checking"),
        fail: _t("Must be fixed"),
        not_proven: _t("Not proven yet"),
        not_run: _t("Not run yet"),
    }[result] || _t("Not available");
}

function lifecycleLabel(lifecycle, fallbackState = "unknown") {
    const value = asObject(lifecycle);
    const connection = P16_LIFECYCLE_COPY[value.state || fallbackState] || _t("Unknown");
    const activation = P16_ACTIVATION_COPY[value.activation_state];
    return activation ? `${activation} · ${connection}` : connection;
}

export class P16StatePanel extends Component {
    static template = "shopify_connector_core.P16StatePanel";
    static props = { "*": true };

    get state() {
        return normalizeResponseState(this.props.state || "loading");
    }

    get meta() {
        return stateMeta(this.state);
    }

    get title() {
        return this.props.title || this.meta.title;
    }

    get detail() {
        return this.props.detail || _t("The server has not supplied further evidence.");
    }

    get action() {
        return this.props.action || null;
    }

    get isError() {
        return ["terminal_error", "retryable_error", "permission_empty", "conflict"].includes(
            this.state,
        );
    }

    invokeAction() {
        callback(this.props, "onAction", this.action);
    }
}

export class P16StoreList extends Component {
    static template = "shopify_connector_core.P16StoreList";
    static props = { "*": true };
    static components = { P16StatePanel };

    setup() {
        this.instanceId = `p16-store-list-${P16StoreList.nextId++}`;
    }

    get titleId() {
        return `${this.instanceId}-title`;
    }

    get searchId() {
        return `${this.instanceId}-search`;
    }

    static nextId = 1;

    get items() {
        return storeItems(this.props.envelope);
    }

    get capacity() {
        return asObject(asObject(this.props.envelope).data).capacity || {};
    }

    get state() {
        const explicit = this.props.state;
        if (explicit) {
            return explicit;
        }
        return this.items.length ? "success" : "empty";
    }

    get hasMore() {
        return Boolean(asObject(asObject(this.props.envelope).data).has_more);
    }

    get canNativeList() {
        return Boolean(
            this.props.nativeAction ||
                this.items.some((item) => hasServerAction(item, "manage_stores")),
        );
    }

    get selectedId() {
        return Number(this.props.selectedStoreId) || null;
    }

    isSelected(item) {
        return itemStoreId(item) === this.selectedId;
    }

    storeName(item) {
        return display(storeFromItem(item) && storeFromItem(item).name, _t("Unnamed store"));
    }

    storeDomain(item) {
        return display(storeFromItem(item) && storeFromItem(item).shop_domain);
    }

    stateLabel(item) {
        const store = storeFromItem(item) || {};
        return lifecycleLabel(
            {
                state: store.connection,
                activation_state: store.activation,
            },
            store.connection,
        );
    }

    open(item) {
        callback(this.props, "onOpen", itemStoreId(item));
    }

    resume(item) {
        callback(this.props, "onResume", itemStoreId(item));
    }

    readiness(item) {
        callback(this.props, "onReadiness", itemStoreId(item));
    }

    settings(item) {
        callback(this.props, "onSettings", itemStoreId(item));
    }

    diagnostics(item) {
        callback(this.props, "onDiagnostics", itemStoreId(item));
    }

    retry() {
        callback(this.props, "onRetry");
    }

    newStore() {
        callback(this.props, "onNewStore");
    }

    nativeList() {
        callback(this.props, "onNativeList", this.props.nativeAction || null);
    }

    searchInput(ev) {
        callback(this.props, "onSearchInput", ev.target.value);
    }

    submitSearch() {
        callback(this.props, "onSearch");
    }

    nextPage() {
        callback(this.props, "onNextPage");
    }

    itemStoreId(item) {
        return itemStoreId(item);
    }

    storeFromItem(item) {
        return storeFromItem(item) || {};
    }

    hasServerAction(value, key) {
        return hasServerAction(value, key);
    }

    canOpen(item) {
        return ["open_store", "open_setup", "open_store_settings", "open_readiness"].some((key) =>
            hasServerAction(item, key),
        );
    }

    canReadiness(item) {
        return hasServerAction(item, "open_readiness") || hasServerAction(item, "open_setup");
    }

    workflowCount(item) {
        return asArray(item && item.workflows).filter((workflow) => workflow.readiness !== "disabled").length;
    }

    setupResumeLabel(item) {
        const key = item && item.setup_continuation && item.setup_continuation.step_key;
        return phaseForStep(key)?.label || _t("Setup welcome");
    }
}

export class P16PhaseRail extends Component {
    static template = "shopify_connector_core.P16PhaseRail";
    static props = { "*": true };

    get rows() {
        return setupPhaseRows(asObject(this.props.setup).steps);
    }

    get currentStep() {
        return asObject(this.props.setup).resume_step_key || "welcome";
    }

    phaseState(phase) {
        if (phase.key === phaseForStep(this.currentStep)?.key) {
            return "current";
        }
        const steps = phase.steps || [];
        if (steps.length && steps.every((step) => stepState(step) !== "pending")) {
            return "completed";
        }
        return "pending";
    }

    canChoose(step) {
        // A setup rail is a resumable workflow, not a free-form router.  A
        // user may revisit completed steps or open the immediate next step,
        // but cannot jump over an unsaved prerequisite.
        return canSelectSetupStep(
            asArray(asObject(this.props.setup).steps),
            this.currentStep,
            step && step.step_key,
        );
    }

    choose(step) {
        if (this.canChoose(step)) {
            callback(this.props, "onSelect", step.step_key);
        }
    }

    stepLabel(step) {
        return display(step.label, step.step_key);
    }

    stepState(step) {
        return stepState(step);
    }

    stepStateLabel(step) {
        return {
            completed: _t("Completed"),
            not_required: _t("Not required"),
            pending: _t("Pending"),
            blocked: _t("Blocked"),
            current: _t("Current"),
        }[stepState(step)] || _t("Pending");
    }

    phaseNumber(phase) {
        return this.rows.findIndex((row) => row.key === phase.key) + 1;
    }
}

export class P16ReadinessPanel extends Component {
    static template = "shopify_connector_core.P16ReadinessPanel";
    static props = { "*": true };
    static components = { P16StatePanel };

    setup() {
        this.instanceId = `p16-readiness-${P16ReadinessPanel.nextId++}`;
    }

    get titleId() {
        return `${this.instanceId}-title`;
    }

    static nextId = 1;

    get readiness() {
        return asObject(this.props.readiness);
    }

    get checks() {
        return asArray(this.readiness.checks);
    }

    get overallLabel() {
        return resultLabel(this.readiness.overall_result);
    }

    get overallState() {
        if (this.readiness.stale) {
            return "stale";
        }
        return this.readiness.overall_result || "not_run";
    }

    checkLabel(check) {
        return resultLabel(check && check.result);
    }

    checkName(check) {
        return display(check && (check.label || check.name || check.code), _t("Readiness check"));
    }

    checkClass(check) {
        const result = (check && check.result) || "not_proven";
        return `sc-p16-check sc-p16-check--${result}`;
    }

    canAction(key) {
        return hasServerAction(this.readiness, key) || hasServerAction(this.props, key);
    }

    runTest() {
        callback(this.props, "onTestConnection");
    }

    runReadiness() {
        callback(this.props, "onRefresh");
    }

    activate() {
        callback(this.props, "onActivate");
    }

    get canPresentActivation() {
        // This only controls disabled presentation.  The server reruns all
        // checks and owns activation authorization/fencing on submit.
        return ["pass", "warning"].includes(this.readiness.overall_result) && !this.readiness.stale;
    }
}

export class P16SettingsGroups extends Component {
    static template = "shopify_connector_core.P16SettingsGroups";
    static props = { "*": true };
    static components = { P16StatePanel };

    setup() {
        this.instanceId = `p16-settings-${P16SettingsGroups.nextId++}`;
    }

    get titleId() {
        return `${this.instanceId}-title`;
    }

    fieldId(group, field) {
        return `${this.instanceId}-${group.key}-${field.key}`;
    }

    static nextId = 1;

    get groups() {
        return asArray(asObject(this.props.settings).groups);
    }

    get drafts() {
        return asObject(this.props.drafts);
    }

    fieldValue(group, field) {
        const key = `${group.key}.${field.key}`;
        return Object.prototype.hasOwnProperty.call(this.drafts, key)
            ? this.drafts[key]
            : fieldInputValue(field);
    }

    fieldIsReadOnly(field) {
        return fieldIsReadOnly(field);
    }

    fieldDisabled(group, field) {
        return Boolean(this.props.busy) || fieldIsReadOnly(field) || !hasServerAction(
            group,
            "open_store_settings",
        );
    }

    fieldText(field, value) {
        if (field.value_type === "boolean") {
            return value ? _t("Enabled") : _t("Disabled");
        }
        return display(value);
    }

    input(group, field, ev) {
        let value;
        if (field.value_type === "boolean") {
            value = Boolean(ev.target.checked);
        } else if (field.value_type === "integer" || field.value_type === "number" || field.value_type === "reference") {
            value = ev.target.value === "" ? false : Number(ev.target.value);
        } else {
            value = ev.target.value;
        }
        callback(this.props, "onChange", group.key, field.key, value);
    }

    save(group) {
        callback(this.props, "onSave", group.key);
    }

    canSave(group) {
        return asArray(group.fields).some(
            (field) => !fieldIsReadOnly(field),
        ) && hasServerAction(group, "open_store_settings");
    }

    choices(field) {
        return asArray(asObject(field.schema).choices);
    }
}

export class P16CredentialPanel extends Component {
    static template = "shopify_connector_core.P16CredentialPanel";
    static props = { "*": true };

    setup() {
        this.instanceId = `p16-credential-${P16CredentialPanel.nextId++}`;
        this.state = useState({ mode: "offline_access_token" });
        this.tokenRef = useRef("token");
        this.clientIdRef = useRef("clientId");
        this.clientSecretRef = useRef("clientSecret");
    }

    get titleId() {
        return `${this.instanceId}-title`;
    }

    get modeId() {
        return `${this.instanceId}-mode`;
    }

    get tokenId() {
        return `${this.instanceId}-token`;
    }

    get clientId() {
        return `${this.instanceId}-client-id`;
    }

    get clientSecretId() {
        return `${this.instanceId}-client-secret`;
    }

    static nextId = 1;

    get store() {
        return asObject(this.props.store);
    }

    get credentialPresent() {
        return Boolean(asObject(this.store.credentials).present || this.store.credential_present);
    }

    setMode(ev) {
        this.state.mode = ev.target.value;
    }

    clearInputs() {
        for (const ref of [this.tokenRef, this.clientIdRef, this.clientSecretRef]) {
            if (ref.el) {
                ref.el.value = "";
            }
        }
    }

    async submit() {
        const payload = { auth_mode: this.state.mode };
        if (this.state.mode === "offline_access_token") {
            payload.access_token = this.tokenRef.el ? this.tokenRef.el.value : "";
        } else {
            payload.client_id = this.clientIdRef.el ? this.clientIdRef.el.value : "";
            payload.client_secret = this.clientSecretRef.el ? this.clientSecretRef.el.value : "";
        }
        try {
            await callback(this.props, "onReplace", payload);
        } finally {
            // Secret material is never put in Owl state and is removed from
            // the DOM immediately after the one write-only request settles.
            this.clearInputs();
        }
    }

    testConnection() {
        callback(this.props, "onTestConnection");
    }
}

export class P16LifecyclePanel extends Component {
    static template = "shopify_connector_core.P16LifecyclePanel";
    static props = { "*": true };

    setup() {
        this.instanceId = `p16-lifecycle-${P16LifecyclePanel.nextId++}`;
        this.form = useState({ reason: "" });
    }

    get titleId() {
        return `${this.instanceId}-title`;
    }

    static nextId = 1;

    get summary() {
        return asObject(this.props.summary);
    }

    get lifecycle() {
        return asObject(this.summary.lifecycle);
    }

    get state() {
        return this.lifecycle.state || (this.summary.store && this.summary.store.connection) || "unknown";
    }

    get activationState() {
        return this.lifecycle.activation_state || (this.summary.store && this.summary.store.activation_state) || "";
    }

    get stateLabel() {
        return lifecycleLabel(this.lifecycle, this.state);
    }

    canRequest(operation) {
        const commandKey = `${operation}_store`;
        return (
            hasServerAction(this.lifecycle, commandKey) ||
            hasServerAction(this.summary, commandKey)
        );
    }

    request(operation) {
        callback(this.props, "onRequest", operation, this.form.reason);
    }

    setReason(ev) {
        this.form.reason = typeof ev.target.value === "string"
            ? ev.target.value.slice(0, 512)
            : "";
    }
}

export class P16DiagnosticsPanel extends Component {
    static template = "shopify_connector_core.P16DiagnosticsPanel";
    static props = { "*": true };
    static components = { P16ReadinessPanel };

    setup() {
        this.instanceId = `p16-diagnostics-${P16DiagnosticsPanel.nextId++}`;
    }

    get titleId() {
        return `${this.instanceId}-title`;
    }

    static nextId = 1;

    get summary() {
        return asObject(this.props.summary);
    }

    get credentials() {
        return asObject(this.summary.credentials);
    }

    get webhooks() {
        return asObject(this.summary.webhooks);
    }

    get identity() {
        return asObject(this.summary.identity_immutability);
    }

    get lifecycle() {
        return asObject(this.summary.lifecycle);
    }

    get lifecycleLabel() {
        return lifecycleLabel(this.lifecycle);
    }

    value(value, fallback = "—") {
        return display(value, fallback);
    }

    refresh() {
        callback(this.props, "onRefresh");
    }

    testConnection() {
        callback(this.props, "onTestConnection");
    }

    activate() {
        callback(this.props, "onActivate");
    }
}

export const P16Components = Object.freeze({
    P16CredentialPanel,
    P16DiagnosticsPanel,
    P16LifecyclePanel,
    P16PhaseRail,
    P16ReadinessPanel,
    P16SettingsGroups,
    P16SetupStepControls,
    P16StatePanel,
    P16StoreList,
});
