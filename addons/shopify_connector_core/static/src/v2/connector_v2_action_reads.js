/** @odoo-module **/

/*
 * Read lifecycle mixin for the canonical V2 Operations shell.
 *
 * Keeping the bounded reads outside the controller leaves the controller
 * focused on navigation/focus/visibility, and makes the transport seam easy
 * to test without introducing a second state owner.  Every method still
 * calls one fixed application-facade method and treats the server envelope as
 * authoritative.
 */

import { _t } from "@web/core/l10n/translation";
import {
    FACADE_MODEL,
    RPC_METHODS,
    V2_VIEWS,
    isRecord,
    makeEnvelope,
    normalizeRpcError,
    nonEmptyString,
    positiveStoreId,
    responseData,
    responseFingerprint,
} from "./connector_v2_action_contracts";

export function installV2ActionReadMethods(ActionClass) {
    Object.assign(ActionClass.prototype, {
        async _rpc(method, args) {
            // `method` comes only from the frozen local map. There is no
            // client-provided model, method, domain or arbitrary dispatcher.
            try {
                return await this.orm.call(FACADE_MODEL, method, args);
            } catch (error) {
                throw normalizeRpcError(error);
            }
        },

        _isCurrent(kind, sequence, generation, view = this.state.view) {
            return (
                !this._unmounted &&
                this._requestSequence[kind] === sequence &&
                this._navigationGeneration === generation &&
                this.state.view === view
            );
        },

        _serverEnvelope(value) {
            return isRecord(value)
                ? value
                : makeEnvelope(
                      "terminal_error",
                      null,
                      _t("The connector returned an invalid read response."),
                  );
        },

        async _loadOverview(storeId, { initial = false } = {}) {
            if (this._recoveryInFlight || this._recoveryUncertainContext) {
                return;
            }
            const normalizedStoreId = positiveStoreId(storeId);
            const generation = this._navigationGeneration;
            const sequence = ++this._requestSequence.overview;
            if (initial) {
                this._commit("overview", makeEnvelope("loading"));
            }
            if (!normalizedStoreId) {
                this._commit(
                    "overview",
                    makeEnvelope("unconfigured", {}, _t("No permitted store is selected.")),
                );
                return;
            }
            try {
                let result = this._serverEnvelope(
                    await this._rpc(RPC_METHODS.overview, [normalizedStoreId]),
                );
                const resultData = responseData(result);
                if (Array.isArray(resultData.allowed_actions)) {
                    result = {
                        ...result,
                        data: {
                            ...resultData,
                            // The V2 shell has no create-store command seam;
                            // keep the capability on P15 where the named
                            // create_store_v1 adapter is executable.
                            allowed_actions: resultData.allowed_actions.filter(
                                (action) => action && (
                                    action.key !== "create_store" ||
                                    isRecord(action.target)
                                ),
                            ),
                        },
                    };
                }
                if (this._isCurrent("overview", sequence, generation, V2_VIEWS.overview)) {
                    this._commit("overview", result);
                    this.clearNotice();
                }
            } catch (error) {
                if (this._isCurrent("overview", sequence, generation, V2_VIEWS.overview)) {
                    const failure = error && error.status ? error : normalizeRpcError(error);
                    this._commit("overview", makeEnvelope(failure.status, null, failure.message));
                    if (failure.retryable) {
                        this._setNotice(
                            _t("The overview read can be requested again."),
                            () => this._loadOverview(normalizedStoreId),
                        );
                    }
                }
            }
        },

        _mergeStoreSelectorIntoOverview() {
            const listData = responseData(this.state.stores);
            if (!Array.isArray(listData.stores)) {
                return;
            }
            const current = responseData(this.state.overview);
            const allowedStores = listData.stores
                .map((item) => (isRecord(item && item.store) ? item.store : item))
                .filter((item) => isRecord(item) && positiveStoreId(item.id));
            const actions = [
                ...(Array.isArray(current.allowed_actions) ? current.allowed_actions : []),
                ...(Array.isArray(listData.allowed_actions) ? listData.allowed_actions : []),
            ];
            const seen = new Set();
            const allowedActions = actions.filter((action) => {
                if (!isRecord(action) || !nonEmptyString(action.key)) {
                    return false;
                }
                // The V2 shell can execute a native target or one of its
                // small local read transitions.  P15's create command is
                // intentionally owned by the subordinate administrator
                // surface; carrying its bare capability into V2 would make
                // a button that has no executable V2 handler.
                if (action.key === "create_store" && !isRecord(action.target)) {
                    return false;
                }
                const identity = `${action.key}::${action.item_ref || ""}`;
                if (seen.has(identity)) {
                    return false;
                }
                seen.add(identity);
                return true;
            });
            this._commit("overview", {
                ...this.state.overview,
                data: {
                    ...current,
                    allowed_stores: allowedStores,
                    all_stores: {
                        allowed: allowedStores.length > 1,
                        read_only: true,
                        selected: this.state.storeKind === "all",
                    },
                    allowed_actions: allowedActions,
                },
            });
        },

        async _loadStores({ initial = false } = {}) {
            if (this._recoveryInFlight || this._recoveryUncertainContext) {
                return;
            }
            const generation = this._navigationGeneration;
            const sequence = ++this._requestSequence.stores;
            if (initial) {
                this._commit("stores", makeEnvelope("loading"));
            }
            try {
                const result = this._serverEnvelope(
                    await this._rpc(RPC_METHODS.stores, [null, null, null, 10, null]),
                );
                if (
                    this._requestSequence.stores !== sequence ||
                    this._navigationGeneration !== generation ||
                    this._unmounted
                ) {
                    return;
                }
                this._commit("stores", result);
                this._mergeStoreSelectorIntoOverview();
            } catch (error) {
                if (
                    this._requestSequence.stores === sequence &&
                    this._navigationGeneration === generation &&
                    !this._unmounted
                ) {
                    const failure = error && error.status ? error : normalizeRpcError(error);
                    this._commit("stores", makeEnvelope(failure.status, null, failure.message));
                }
            }
        },

        _attentionDataWithDetail(listEnvelope, detailEnvelope) {
            const listData = responseData(listEnvelope);
            return {
                ...detailEnvelope,
                data: {
                    ...listData,
                    detail: detailEnvelope.data,
                },
            };
        },

        async _loadAttentionList(
            cursor = null,
            {
                initial = false,
                detailRef = null,
                selectionEpoch = this._attentionSelectionEpoch,
            } = {},
        ) {
            if (this._recoveryInFlight || this._recoveryUncertainContext) {
                return;
            }
            const storeId = positiveStoreId(this.state.storeId);
            const generation = this._navigationGeneration;
            const sequence = ++this._requestSequence.attention;
            if (initial) {
                this._commit("attention", makeEnvelope("loading"));
            }
            if (!storeId) {
                this._commit(
                    "attention",
                    makeEnvelope("unconfigured", {}, _t("No permitted store is selected.")),
                );
                return;
            }
            try {
                const result = this._serverEnvelope(
                    await this._rpc(RPC_METHODS.attention, [storeId, 80, 0, {}, cursor || null]),
                );
                if (
                    !this._isCurrent("attention", sequence, generation, V2_VIEWS.attention) ||
                    this._attentionSelectionEpoch !== selectionEpoch
                ) {
                    return;
                }
                const previous = responseData(this.state.attention);
                const incoming = responseData(result);
                const merged = cursor
                    ? {
                          ...result,
                          data: {
                              ...incoming,
                              items: [
                                  ...(Array.isArray(previous.items) ? previous.items : []),
                                  ...(Array.isArray(incoming.items) ? incoming.items : []),
                              ].slice(0, 80),
                          },
                      }
                    : result;
                this._commit("attention", merged);
                this.clearNotice();
                if (detailRef) {
                    await this._loadAttentionDetail(detailRef, generation, selectionEpoch);
                }
            } catch (error) {
                if (
                    this._isCurrent("attention", sequence, generation, V2_VIEWS.attention) &&
                    this._attentionSelectionEpoch === selectionEpoch
                ) {
                    const failure = error && error.status ? error : normalizeRpcError(error);
                    this._commit("attention", makeEnvelope(failure.status, null, failure.message));
                    if (failure.retryable) {
                        this._setNotice(
                            _t("The attention read can be requested again."),
                            () => this._loadAttentionList(null, { initial: true }),
                        );
                    }
                }
            }
        },

        async _loadAttentionDetail(
            itemRef,
            generation = this._navigationGeneration,
            selectionEpoch = this._attentionSelectionEpoch,
        ) {
            if (this._recoveryInFlight || this._recoveryUncertainContext) {
                return;
            }
            const ref = nonEmptyString(itemRef);
            const storeId = positiveStoreId(this.state.storeId);
            const sequence = ++this._requestSequence.attention;
            if (!ref || !storeId) {
                return;
            }
            try {
                const result = this._serverEnvelope(
                    await this._rpc(RPC_METHODS.attentionDetail, [storeId, ref]),
                );
                if (
                    !this._isCurrent("attention", sequence, generation, V2_VIEWS.attention) ||
                    this._attentionSelectionEpoch !== selectionEpoch
                ) {
                    return;
                }
                this._commit("attention", this._attentionDataWithDetail(this.state.attention, result));
                this.state.selectedItemRef = ref;
                this._focusDetailAfterSelection = true;
                this.clearNotice();
            } catch (error) {
                if (
                    this._isCurrent("attention", sequence, generation, V2_VIEWS.attention) &&
                    this._attentionSelectionEpoch === selectionEpoch
                ) {
                    const failure = error && error.status ? error : normalizeRpcError(error);
                    this._setNotice(
                        failure.message,
                        failure.retryable
                            ? () => this._loadAttentionDetail(ref, generation, selectionEpoch)
                            : null,
                    );
                }
            }
        },

        async _loadRun(runRef, { initial = false } = {}) {
            if (this._recoveryInFlight || this._recoveryUncertainContext) {
                return;
            }
            const ref = nonEmptyString(runRef);
            const storeId = positiveStoreId(this.state.storeId);
            const generation = this._navigationGeneration;
            const sequence = ++this._requestSequence.run;
            if (initial) {
                this._commit("run", makeEnvelope("loading"));
            }
            if (!ref || !storeId) {
                this._commit(
                    "run",
                    makeEnvelope("unconfigured", {}, _t("No run is selected for this store.")),
                );
                return;
            }
            try {
                const result = this._serverEnvelope(await this._rpc(RPC_METHODS.run, [storeId, ref]));
                if (this._isCurrent("run", sequence, generation, V2_VIEWS.run)) {
                    this._commit("run", result);
                    this.clearNotice();
                }
            } catch (error) {
                if (this._isCurrent("run", sequence, generation, V2_VIEWS.run)) {
                    const failure = error && error.status ? error : normalizeRpcError(error);
                    this._commit("run", makeEnvelope(failure.status, null, failure.message));
                    if (failure.retryable) {
                        this._setNotice(
                            _t("The run read can be requested again."),
                            () => this._loadRun(ref),
                        );
                    }
                }
            }
        },
    });
}
