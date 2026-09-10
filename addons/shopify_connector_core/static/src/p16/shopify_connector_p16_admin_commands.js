/** @odoo-module **/

/*
 * Command/navigation mixin for the subordinate P16 surface.  These hooks do
 * not manufacture commands or targets: the action component must receive the
 * corresponding server `allowed_actions` entry before a named command can be
 * requested.  Missing authority remains an explicit unavailable state.
 */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import {
    P16_SURFACES,
    asObject,
    connectionGeneration,
    hasServerAction,
    normalizeEnvelope,
    nextSetupStep,
} from "./shopify_connector_p16_contract";

export const P16_LIFECYCLE_COMMANDS = Object.freeze({
    disconnect: "disconnect_store_v1",
    pause: "pause_store_v1",
    resume: "resume_store_v1",
    retire: "retire_store_v1",
});

const LIFECYCLE_CONFIRMATIONS = Object.freeze({
    disconnect: Object.freeze({
        title: _t("Disconnect this store?"),
        body: _t(
            "Disconnect is a one-way local shutdown transition. It stops connector work and removes local credential usability; Shopify-side token revocation remains an explicit Administrator follow-up.",
        ),
        confirmLabel: _t("Disconnect store"),
    }),
    retire: Object.freeze({
        title: _t("Retire this store?"),
        body: _t(
            "Retirement is unavailable until the server supplies a distinct, reversible lifecycle contract. No command was submitted.",
        ),
        confirmLabel: _t("Retire store"),
    }),
    resume: Object.freeze({
        title: _t("Resume this store?"),
        body: _t(
            "The server will recheck connection and readiness before allowing connector work to resume.",
        ),
        confirmLabel: _t("Resume store"),
    }),
    pause: Object.freeze({
        title: _t("Pause this store?"),
        body: _t(
            "The store stays connected for diagnostics while new connector work is paused.",
        ),
        confirmLabel: _t("Pause store"),
    }),
});

const COMMAND_ACTION_ALIASES = Object.freeze({
    create_store_v1: ["create_store"],
    save_setup_step_v1: ["save_setup_step"],
    replace_credential_v1: ["replace_credential"],
    test_connection_v1: ["test_connection"],
    activate_store_v1: ["activate_store"],
    save_store_settings_group_v1: ["save_store_settings_group"],
    disconnect_store_v1: ["disconnect_store"],
    resume_store_v1: ["resume_store"],
    pause_store_v1: ["pause_store"],
    retire_store_v1: ["retire_store"],
});

function setupSemanticValues(setup, stepKey) {
    const source = setup && setup.step_values && setup.step_values[stepKey];
    if (!source || typeof source !== "object" || Array.isArray(source)) {
        return {};
    }
    const values = {};
    for (const [key, value] of Object.entries(source)) {
        if (
            typeof key !== "string" ||
            !key ||
            key.length > 80 ||
            /token|secret|password|credential|authorization/i.test(key) ||
            (value !== null && typeof value !== "string" && typeof value !== "boolean" && typeof value !== "number") ||
            (typeof value === "number" && !Number.isFinite(value))
        ) {
            continue;
        }
        values[key] = typeof value === "string" ? value.slice(0, 2000) : value;
    }
    return values;
}

function commandAuthorityCandidates(component, commandName) {
    if (commandName === "create_store_v1") {
        // Creation has no selected store/detail DTO.  Its only authority is
        // the latest successful bounded store-list response, including while
        // the create form is open.  Error/loading/permission responses are
        // never treated as create permission evidence.
        if (![P16_SURFACES.LIST, P16_SURFACES.CREATE].includes(component.state.surface)) {
            return [];
        }
        const listState = component.state.listState;
        const listEnvelope = component.state.listEnvelope;
        if (!listEnvelope || !["success", "empty", "filtered_empty"].includes(listState)) {
            return [];
        }
        const normalized = normalizeEnvelope(listEnvelope, "loading");
        return normalized.state === "success" && normalized.data
            ? [asObject(normalized.data)]
            : [];
    }
    const surface = component.state.surface;
    const stateKey = `${surface}State`;
    const envelope = {
        [P16_SURFACES.SETUP]: component.state.setupEnvelope,
        [P16_SURFACES.READINESS]: component.state.readinessEnvelope,
        [P16_SURFACES.SETTINGS]: component.state.settingsEnvelope,
        [P16_SURFACES.DIAGNOSTICS]: component.state.diagnosticsEnvelope,
    }[surface];
    // A previous successful DTO may remain cached while the current detail
    // read is loading or has failed.  Only the visible surface's success
    // envelope can authorize a command or provide its generation.
    if (!envelope || component.state[stateKey] !== "success") {
        return [];
    }
    const normalized = normalizeEnvelope(envelope, "loading");
    return normalized.state === "success" && normalized.data
        ? [asObject(normalized.data)]
        : [];
}

function authorityStoreId(candidate) {
    const value = asObject(candidate);
    const store = asObject(value.store);
    const id = Number(value.store_id || store.id || 0);
    return Number.isInteger(id) && id > 0 ? id : null;
}

export function commandIsAdvertised(component, commandName) {
    const candidates = commandAuthorityCandidates(component, commandName);
    const keys = COMMAND_ACTION_ALIASES[commandName] || [commandName];
    const storeId = Number(component.activeStoreId) || null;
    if (commandName !== "create_store_v1" && !storeId) {
        return false;
    }
    return candidates.some((candidate) => {
        if (commandName !== "create_store_v1" && (
            !authorityStoreId(candidate) || authorityStoreId(candidate) !== storeId
        )) {
            return false;
        }
        return keys.some((key) => hasServerAction(candidate, key));
    });
}

export { setupSemanticValues };

export function installP16AdminCommandMethods(ActionClass) {
    Object.assign(ActionClass.prototype, {
        async saveSetupStep(requestContext = this._contextSnapshot()) {
            const stepKey = this.setupCurrentStep.step_key;
            const values = setupSemanticValues(
                {
                    step_values: {
                        [stepKey]: this.state.setupDraftValues[stepKey] || {},
                    },
                },
                stepKey,
            );
            const result = await this._command("save_setup_step_v1", {
                generation: this.setupGeneration,
                payload: { step_key: stepKey, values },
                context: requestContext,
            });
            if (
                result &&
                result.status !== "conflict" &&
                result.status !== "blocked" &&
                this._contextIsCurrent(requestContext)
            ) {
                await this._loadSurface(P16_SURFACES.SETUP);
            }
            return Boolean(result && result.status !== "conflict" && result.status !== "blocked");
        },

        async advanceSetup() {
            const requestContext = this._contextSnapshot();
            const saved = await this.saveSetupStep(requestContext);
            if (!saved || !this._contextIsCurrent(requestContext)) {
                return;
            }
            const next = nextSetupStep(this.setup.steps, this.setupCurrentStep.step_key);
            if (next) {
                this.selectSetupStep(next);
            }
        },

        async replaceCredential(payload) {
            const requestContext = this._contextSnapshot();
            const result = await this._command("replace_credential_v1", {
                generation: connectionGeneration(this.state.setupEnvelope, 0),
                payload,
                context: requestContext,
            });
            if (
                result &&
                result.status !== "conflict" &&
                result.status !== "blocked" &&
                this._contextIsCurrent(requestContext)
            ) {
                await this._loadSurface(P16_SURFACES.SETUP);
            }
            return result;
        },

        async testConnection() {
            const requestContext = this._contextSnapshot();
            const currentEnvelope = {
                [P16_SURFACES.SETUP]: this.state.setupEnvelope,
                [P16_SURFACES.READINESS]: this.state.readinessEnvelope,
                [P16_SURFACES.DIAGNOSTICS]: this.state.diagnosticsEnvelope,
            }[this.state.surface];
            const result = await this._command("test_connection_v1", {
                generation: connectionGeneration(currentEnvelope, 0),
                payload: {},
                context: requestContext,
            });
            if (
                result &&
                result.status !== "conflict" &&
                result.status !== "blocked" &&
                this._contextIsCurrent(requestContext)
            ) {
                await this._loadSurface(
                    this.state.surface === P16_SURFACES.SETUP
                        ? P16_SURFACES.SETUP
                        : P16_SURFACES.READINESS,
                );
            }
            return result;
        },

        async refreshReadiness() {
            await this._loadSurface(P16_SURFACES.READINESS);
        },

        async activate() {
            const fingerprint = this.readiness.fingerprint;
            if (typeof fingerprint !== "string" || !fingerprint) {
                this.state.surfaceMessage = _t("Refresh readiness before requesting activation.");
                return;
            }
            const requestContext = this._contextSnapshot();
            const result = await this._command("activate_store_v1", {
                generation: this.readinessGeneration,
                payload: { readiness_fingerprint: fingerprint },
                context: requestContext,
            });
            if (
                result &&
                result.status !== "conflict" &&
                result.status !== "blocked" &&
                this._contextIsCurrent(requestContext)
            ) {
                await this._loadSurface(P16_SURFACES.READINESS);
                if (!this._contextIsCurrent(requestContext)) {
                    return result;
                }
                await this.loadStores();
            }
            return result;
        },

        requestLifecycle(operation, reason = "") {
            const confirmation = LIFECYCLE_CONFIRMATIONS[operation];
            const commandName = P16_LIFECYCLE_COMMANDS[operation];
            if (!confirmation || !commandName) {
                return;
            }
            if (!commandIsAdvertised(this, commandName)) {
                this.state.commandState = "unavailable";
                this.state.commandMessage = _t(
                    "This lifecycle action is not available from the server response. No command was submitted.",
                );
                return;
            }
            const requestContext = this._contextSnapshot();
            const requestGeneration = connectionGeneration(
                this.state.diagnosticsEnvelope,
                0,
            );
            this.dialog.add(ConfirmationDialog, {
                title: confirmation.title,
                body: confirmation.body,
                confirmLabel: confirmation.confirmLabel,
                cancelLabel: _t("Cancel"),
                confirm: () => this._submitLifecycle(
                    operation,
                    commandName,
                    reason,
                    requestContext,
                    requestGeneration,
                ),
            });
        },

        async _submitLifecycle(
            operation,
            commandName,
            reason = "",
            requestContext = null,
            requestGeneration = null,
        ) {
            // A confirmation can outlive a route/company/store change.  It
            // must never reuse its old generation against the new context.
            if (requestContext && !this._contextIsCurrent(requestContext)) {
                return null;
            }
            if (operation === "retire" && !String(reason || "").trim()) {
                this.state.commandState = "unavailable";
                this.state.commandMessage = _t(
                    "Enter a bounded retirement reason before submitting.",
                );
                return;
            }
            const result = await this._command(commandName, {
                generation: requestGeneration === null
                    ? connectionGeneration(this.state.diagnosticsEnvelope, 0)
                    : requestGeneration,
                payload: operation === "retire" ? { reason: String(reason).trim().slice(0, 512) } : {},
                context: requestContext,
            });
            if (
                result &&
                result.status !== "conflict" &&
                result.status !== "blocked" &&
                (!requestContext || this._contextIsCurrent(requestContext))
            ) {
                await this._loadSurface(P16_SURFACES.DIAGNOSTICS);
                if (requestContext && !this._contextIsCurrent(requestContext)) {
                    return result;
                }
                await this.loadStores();
                if (requestContext && !this._contextIsCurrent(requestContext)) {
                    return result;
                }
                this.notification.add(
                    operation === "retire"
                        ? _t("Retirement was accepted by the server.")
                        : _t("The lifecycle request was accepted."),
                    { type: "success" },
                );
            }
        },
    });
}
