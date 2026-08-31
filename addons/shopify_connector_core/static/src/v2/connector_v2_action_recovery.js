/** @odoo-module **/

/*
 * Explicit recovery adapter for the V2 attention detail.
 *
 * Recovery buttons are not generic RPC affordances.  They are enabled only
 * from a server-returned action and all three advertised keys are submitted
 * through the one named ``resolve_attention_v1`` envelope.  The server still
 * reloads the opaque source and owns the final authorization/state fence.
 */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import {
    FACADE_MODEL,
    V2_VIEWS,
    isRecord,
    normalizeRpcError,
    nonEmptyString,
    positiveStoreId,
    responseData,
    stableSerialize,
} from "./connector_v2_action_contracts";

const RECOVERY_ACTION_KEYS = new Set([
    "retry_job",
    "resolve_manual_review",
    "resolve_mutation",
]);
const RECOVERY_COMMAND = "resolve_attention_v1";
const MAX_REASON_LENGTH = 512;

function newRecoveryCommandId() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
        return globalThis.crypto.randomUUID();
    }
    const random = () => Math.floor(Math.random() * 0x100000000).toString(16).padStart(8, "0");
    return `${random()}-${random().slice(0, 4)}-4${random().slice(0, 3)}-a${random().slice(0, 3)}-${random()}${random()}`;
}

function boundedReason(value) {
    if (typeof value !== "string") {
        return "";
    }
    return value
        .replace(/[\u0000-\u001f\u007f]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function serverGeneration(component, envelope) {
    const candidates = [
        envelope,
        component.state.attention,
        component.state.overview,
    ];
    for (const candidate of candidates) {
        const generation = candidate && candidate.store_generation;
        if (Number.isSafeInteger(generation) && generation >= 0) {
            return generation;
        }
    }
    return null;
}

function configurationGeneration(component, item, envelope) {
    const data = responseData(envelope);
    const overview = responseData(component.state.overview);
    const candidates = [
        item && item.configuration_generation,
        data.configuration_generation,
        overview.configuration_generation,
    ];
    for (const candidate of candidates) {
        const generation = Number(candidate);
        if (Number.isSafeInteger(generation) && generation >= 0) {
            return generation;
        }
    }
    return null;
}

function actionNeedsReason(action) {
    return Boolean(
        action && (
            action.requires_reason ||
            action.key === "resolve_manual_review" ||
            action.key === "resolve_mutation"
        ),
    );
}

function actionNeedsDisposition(action) {
    const schema = action && action.input_schema;
    return Boolean(
        action && action.key === "resolve_mutation" &&
        (!isRecord(schema) || !Array.isArray(schema.required) || schema.required.includes("disposition")),
    );
}

function promptValue(message) {
    if (typeof globalThis.prompt !== "function") {
        return null;
    }
    return globalThis.prompt(message);
}

/*
 * A confirmation dialog can outlive the render that opened it.  Keep a
 * detached copy of the server DTOs used by the command so a later Owl render
 * cannot change what the user is confirming.  The live server envelope is
 * still checked immediately before the command is sent.
 */
function copyForRecovery(value) {
    if (Array.isArray(value)) {
        return value.map(copyForRecovery);
    }
    if (isRecord(value)) {
        return Object.keys(value).reduce((result, key) => {
            result[key] = copyForRecovery(value[key]);
            return result;
        }, {});
    }
    return value;
}

/*
 * Only durable server-authority fields belong in a recovery context
 * fingerprint.  Display fields such as age_seconds are recalculated on each
 * read and must not invalidate an otherwise unchanged confirmation.
 */
function recoveryItemFingerprint(item) {
    if (!isRecord(item)) {
        return "";
    }
    const stateVersion = Number(item.state_version);
    const configurationGeneration = Number(item.configuration_generation);
    return stableSerialize({
        item_ref: nonEmptyString(item.item_ref),
        state_version: Number.isSafeInteger(stateVersion) ? stateVersion : null,
        configuration_generation: Number.isSafeInteger(configurationGeneration)
            ? configurationGeneration
            : null,
        allowed_actions: Array.isArray(item.allowed_actions) ? item.allowed_actions : [],
    });
}

function rpcErrorName(value) {
    if (!isRecord(value)) {
        return "";
    }
    const data = isRecord(value.data) ? value.data : {};
    return nonEmptyString(
        data.name || data.type || data.code || value.name || value.code,
    ).toLowerCase();
}

/*
 * A typed application rejection is authoritative: the server received the
 * command and rejected it before claiming an outcome.  Generic transport or
 * framework errors are deliberately not treated as proof of non-execution.
 */
function isAuthoritativeRpcRejection(value) {
    const name = rpcErrorName(value);
    return Boolean(
        name && (
            /accesserror|permission|forbidden|validationerror|usererror|badrequest|constraint/.test(name)
        ),
    );
}

function actionIdentityMatches(candidate, wanted) {
    return Boolean(
        isRecord(candidate) &&
        isRecord(wanted) &&
        nonEmptyString(candidate.key) === nonEmptyString(wanted.key) &&
        nonEmptyString(candidate.item_ref) === nonEmptyString(wanted.item_ref),
    );
}

function serverRecoveryAction(item, wanted) {
    if (!isRecord(item) || !Array.isArray(item.allowed_actions) || !isRecord(wanted)) {
        return null;
    }
    const wantedFingerprint = stableSerialize(wanted);
    return item.allowed_actions.find(
        (candidate) =>
            actionIdentityMatches(candidate, wanted) &&
            stableSerialize(candidate) === wantedFingerprint,
    ) || null;
}

export function installV2ActionRecoveryMethods(ActionClass) {
    Object.assign(ActionClass.prototype, {
        _selectedAttentionItem() {
            const selectedRef = nonEmptyString(this.state.selectedItemRef);
            if (!selectedRef) {
                return null;
            }
            const data = responseData(this.state.attention);
            if (
                isRecord(data.detail) &&
                nonEmptyString(data.detail.item_ref) === selectedRef
            ) {
                return data.detail;
            }
            if (nonEmptyString(data.item_ref) === selectedRef) {
                return data;
            }
            return Array.isArray(data.items)
                ? data.items.find(
                    (item) => isRecord(item) && nonEmptyString(item.item_ref) === selectedRef,
                ) || null
                : null;
        },

        _recoveryInput(action) {
            const inputs = {};
            if (actionNeedsDisposition(action)) {
                const disposition = boundedReason(
                    promptValue(
                        _t("Confirm the remote outcome: enter applied or not_applied."),
                    ),
                );
                if (!["applied", "not_applied"].includes(disposition)) {
                    this._setNotice(
                        _t("Enter exactly applied or not_applied; no mutation was replayed."),
                    );
                    return null;
                }
                inputs.disposition = disposition;
            }
            let reason = "";
            if (actionNeedsReason(action)) {
                reason = boundedReason(
                    promptValue(_t("Enter a short reason for this recovery decision.")),
                );
                if (!reason) {
                    this._setNotice(_t("A reason is required; no command was submitted."));
                    return null;
                }
                if (reason.length > MAX_REASON_LENGTH) {
                    this._setNotice(_t("The reason is limited to 512 characters."));
                    return null;
                }
            }
            return { inputs, reason: reason || null };
        },

        _recoveryCommand(action, item, input) {
            const storeId = positiveStoreId(this.state.storeId);
            const companyId = Number(this.state.companyId);
            const stateVersion = Number(item && item.state_version);
            const expectedGeneration = serverGeneration(this, this.state.attention);
            const actorUid = Number(this.user && (this.user.userId || this.user.user_id));
            if (
                !storeId || !Number.isSafeInteger(companyId) || companyId <= 0 ||
                !Number.isSafeInteger(stateVersion) || stateVersion <= 0 ||
                !Number.isSafeInteger(expectedGeneration) || expectedGeneration < 0 ||
                !Number.isSafeInteger(actorUid) || actorUid <= 0 ||
                !nonEmptyString(item && item.item_ref)
            ) {
                this._setNotice(_t("Refresh the exact store evidence before choosing recovery."));
                return null;
            }
            const command = {
                contract_version: 1,
                command_id: newRecoveryCommandId(),
                command_name: RECOVERY_COMMAND,
                store_id: storeId,
                company_id: companyId,
                expected_generation: expectedGeneration,
                actor_uid: actorUid,
                trigger: "user",
                requested_at: new Date().toISOString(),
                payload: {
                    item_ref: item.item_ref,
                    state_version: stateVersion,
                    action_key: action.key,
                    inputs: input.inputs,
                    reason: input.reason,
                },
            };
            const config = configurationGeneration(this, item, this.state.attention);
            if (config !== null) {
                command.expected_configuration_generation = config;
            }
            return command;
        },

        _recoveryContextIsCurrent(context) {
            if (!context || !isRecord(context)) {
                return false;
            }
            const request = context;
            const currentItem = this._selectedAttentionItem();
            const currentAction = serverRecoveryAction(currentItem, context.action);
            const currentStoreGeneration = serverGeneration(this, this.state.attention);
            const currentConfigurationGeneration = configurationGeneration(
                this,
                currentItem,
                this.state.attention,
            );
            return Boolean(
                !this._unmounted &&
                context.sequence === this._recoverySequence &&
                request.navigationGeneration === this._navigationGeneration &&
                request.selectionEpoch === this._attentionSelectionEpoch &&
                request.companyId === Number(this.state.companyId) &&
                request.storeId === positiveStoreId(this.state.storeId) &&
                request.selectedItemRef === nonEmptyString(this.state.selectedItemRef) &&
                request.view === this.state.view &&
                this.state.view === V2_VIEWS.attention &&
                currentItem &&
                request.itemRef === nonEmptyString(currentItem.item_ref) &&
                request.itemFingerprint === recoveryItemFingerprint(currentItem) &&
                currentAction &&
                request.actionFingerprint === stableSerialize(currentAction) &&
                request.storeGeneration === currentStoreGeneration &&
                request.configurationGeneration === currentConfigurationGeneration
            );
        },

        async _refreshCurrentAttentionAfterStale() {
            if (
                this._unmounted ||
                !this._mounted ||
                this._recoveryInFlight ||
                this._recoveryUncertainContext ||
                this.state.view !== V2_VIEWS.attention ||
                !positiveStoreId(this.state.storeId)
            ) {
                return;
            }
            await this._loadAttentionList(null, {
                detailRef: nonEmptyString(this.state.selectedItemRef),
            });
        },

        _markRecoveryUncertain(context, message) {
            this._requestSequence.attention += 1;
            this._activeRecoveryContext = null;
            this._recoveryUncertainContext = context;
            this._recoveryInFlight = false;
            this._clearPoll();
            this._setNotice(
                nonEmptyString(message) ||
                    _t("The recovery command's transport outcome is uncertain. Retry the same command to resolve it."),
                () => this._retryUncertainRecovery(context),
            );
        },

        async _retryUncertainRecovery(context) {
            if (
                this._unmounted ||
                this._recoveryUncertainContext !== context ||
                context.sequence !== this._recoverySequence ||
                !this._recoveryContextIsCurrent(context)
            ) {
                return;
            }
            this._setNotice(_t("Checking the same recovery command; no new mutation was created."));
            await this._submitRecovery(context, { explicitRetry: true });
        },

        async _submitRecovery(context, { explicitRetry = false } = {}) {
            if (!context || !isRecord(context.command) || this._unmounted || !this._mounted) {
                return;
            }
            if (this._recoveryInFlight && this._activeRecoveryContext === context) {
                return;
            }
            if (
                (
                    explicitRetry &&
                    (
                        this._recoveryUncertainContext !== context ||
                        !this._recoveryContextIsCurrent(context)
                    )
                ) ||
                (!explicitRetry && !this._recoveryContextIsCurrent(context))
            ) {
                // A response from an older intent must never overwrite the
                // current item or show an old command's notice.  Refresh only
                // the current attention context when the newer intent is not
                // itself still doing safety work.
                await this._refreshCurrentAttentionAfterStale();
                if (
                    !explicitRetry &&
                    !this._unmounted &&
                    this._mounted &&
                    this.state.view === V2_VIEWS.attention
                ) {
                    this._setNotice(
                        _t("The attention evidence changed before confirmation; no recovery command was submitted."),
                    );
                }
                return;
            }
            this._activeRecoveryContext = context;
            // Any list/detail read that began before this command must not
            // repaint the selected item while the command is in flight.
            this._requestSequence.attention += 1;
            this._recoveryInFlight = true;
            this._clearPoll();
            try {
                if (this._unmounted) {
                    return;
                }
                // ``context.command`` is intentionally reused byte-for-byte
                // for an explicit retry.  Rebuilding it would create a new
                // command_id and could resend an uncertain mutation.
                const result = await this.orm.call(
                    FACADE_MODEL,
                    RECOVERY_COMMAND,
                    [context.command],
                );
                if (this._activeRecoveryContext !== context) {
                    return;
                }
                this._recoveryInFlight = false;
                if (!isRecord(result)) {
                    this._activeRecoveryContext = null;
                    this._markRecoveryUncertain(
                        context,
                        _t("The recovery response was incomplete; the remote outcome may have been recorded. Retry the same command to check it."),
                    );
                    return;
                }
                const status = nonEmptyString(result.status).toLowerCase();
                const originalStatus = nonEmptyString(result.original_status).toLowerCase();
                if (!this._recoveryContextIsCurrent(context)) {
                    this._activeRecoveryContext = null;
                    // A definitive server response resolves a prior
                    // uncertain transport even when the user navigated while
                    // it was pending.  Do not retain a dead retry banner.
                    this._recoveryUncertainContext = null;
                    await this._refreshCurrentAttentionAfterStale();
                    return;
                }
                const accepted =
                    status === "accepted" ||
                    (
                        status === "duplicate" &&
                        ["accepted", "duplicate"].includes(originalStatus)
                    );
                const definitiveRejection =
                    ["blocked", "conflict", "rejected"].includes(status) ||
                    (
                        status === "duplicate" &&
                        Boolean(originalStatus) &&
                        !["accepted", "duplicate"].includes(originalStatus)
                    );
                if (definitiveRejection) {
                    this._activeRecoveryContext = null;
                    this._recoveryUncertainContext = null;
                    this._setNotice(
                        nonEmptyString(result.message) ||
                            _t("The server did not accept this recovery decision."),
                    );
                    this._schedulePoll();
                    return;
                }
                if (!accepted) {
                    this._activeRecoveryContext = null;
                    this._markRecoveryUncertain(
                        context,
                        _t("The recovery response was not recognized; the remote outcome may have been recorded. Retry the same command to check it."),
                    );
                    return;
                }
                const serverNotice =
                    nonEmptyString(result && result.message) ||
                    _t("The recovery decision was recorded.");
                this._activeRecoveryContext = null;
                this._recoveryUncertainContext = null;
                this._clearPoll();

                // Accepted recovery can remove or materially change the
                // selected item.  Clear its detail before reloading, and do
                // not ask the server for the obsolete detail again.
                this._attentionSelectionEpoch += 1;
                this.state.selectedItemRef = null;
                this._focusDetailAfterSelection = false;
                this._focusRowAfterBack = true;
                this._commit("attention", { ...this.state.attention, data: null });
                const refreshEpoch = this._attentionSelectionEpoch;
                await this._loadAttentionList(null, { initial: true });
                if (
                    !this._unmounted &&
                    this._mounted &&
                    this.state.view === V2_VIEWS.attention &&
                    this._navigationGeneration === context.navigationGeneration &&
                    this._attentionSelectionEpoch === refreshEpoch
                ) {
                    // The read helper clears transient notices on success;
                    // restore the server's accepted/duplicate notice after it
                    // has refreshed the list so the user can see the result.
                    this._setNotice(serverNotice);
                }
                this._schedulePoll();
            } catch (error) {
                if (this._activeRecoveryContext !== context) {
                    return;
                }
                this._activeRecoveryContext = null;
                this._recoveryInFlight = false;
                const failure = normalizeRpcError(error);
                if (!isAuthoritativeRpcRejection(error)) {
                    // A retryable transport error is not proof that the
                    // server did not execute the command.  Stop reads/polling
                    // and offer an explicit retry of the exact same envelope.
                    this._markRecoveryUncertain(context, failure.message);
                } else if (this._recoveryContextIsCurrent(context)) {
                    this._recoveryUncertainContext = null;
                    this._setNotice(failure.message);
                    this._schedulePoll();
                } else {
                    this._recoveryUncertainContext = null;
                    await this._refreshCurrentAttentionAfterStale();
                }
            }
        },

        requestRecoveryAction(action, item = null) {
            const key = nonEmptyString(action && action.key);
            if (!RECOVERY_ACTION_KEYS.has(key)) {
                this._setNotice(_t("This action has no approved recovery adapter."));
                return;
            }
            if (this._recoveryUncertainContext) {
                this._setNotice(
                    _t("Resolve the pending uncertain recovery command before starting another one."),
                    () => this._retryUncertainRecovery(this._recoveryUncertainContext),
                );
                return;
            }
            if (this._recoveryInFlight) {
                this._setNotice(_t("A recovery decision is already being submitted."));
                return;
            }
            // Allocate the serial at intent start.  A newer dialog therefore
            // invalidates an older one even if the user returns A→B→A.
            const sequence = ++this._recoverySequence;
            const currentItem = this._selectedAttentionItem();
            if (
                !currentItem ||
                (
                    isRecord(item) &&
                    recoveryItemFingerprint(item) !== recoveryItemFingerprint(currentItem)
                )
            ) {
                this._setNotice(_t("This recovery action is no longer allowed by the server."));
                return;
            }
            const currentAction = serverRecoveryAction(currentItem, action);
            if (!currentAction) {
                this._setNotice(_t("This recovery action is no longer allowed by the server."));
                return;
            }
            const actionSnapshot = copyForRecovery(currentAction);
            const itemSnapshot = copyForRecovery(currentItem);
            const input = this._recoveryInput(actionSnapshot);
            if (!input) {
                return;
            }
            const inputSnapshot = copyForRecovery(input);
            const command = this._recoveryCommand(actionSnapshot, itemSnapshot, inputSnapshot);
            if (!command) {
                return;
            }
            const stateSnapshot = {
                view: this.state.view,
                companyId: Number(this.state.companyId),
                storeId: positiveStoreId(this.state.storeId),
                selectedItemRef: nonEmptyString(this.state.selectedItemRef),
                navigationGeneration: this._navigationGeneration,
                selectionEpoch: this._attentionSelectionEpoch,
                storeGeneration: serverGeneration(this, this.state.attention),
                configurationGeneration: configurationGeneration(
                    this,
                    itemSnapshot,
                    this.state.attention,
                ),
            };
            // This context is intentionally assembled before opening the
            // dialog.  Confirmation revalidates it against the current
            // selection, state version, action and both generation fences.
            const context = {
                sequence,
                state: stateSnapshot,
                view: stateSnapshot.view,
                navigationGeneration: stateSnapshot.navigationGeneration,
                selectionEpoch: stateSnapshot.selectionEpoch,
                companyId: stateSnapshot.companyId,
                storeId: stateSnapshot.storeId,
                selectedItemRef: stateSnapshot.selectedItemRef,
                itemRef: itemSnapshot.item_ref,
                item: itemSnapshot,
                itemFingerprint: recoveryItemFingerprint(itemSnapshot),
                action: actionSnapshot,
                actionFingerprint: stableSerialize(actionSnapshot),
                input: inputSnapshot,
                storeGeneration: stateSnapshot.storeGeneration,
                configurationGeneration: stateSnapshot.configurationGeneration,
                command: copyForRecovery(command),
            };
            this.dialog.add(ConfirmationDialog, {
                title: actionSnapshot.label || _t("Confirm recovery decision"),
                body: actionSnapshot.consequence || _t("The server will recheck the stored evidence before acting."),
                confirmLabel: _t("Confirm and submit"),
                cancelLabel: _t("Cancel"),
                confirm: () => this._submitRecovery(context),
            });
        },
    });
}

export { RECOVERY_ACTION_KEYS, RECOVERY_COMMAND };
