/** @odoo-module **/

/*
 * Current-surface action authority for the V2 shell.
 *
 * A DTO from another view, run, store or selected attention item is not an
 * executable capability.  Keep this small mixin separate from lifecycle and
 * transport code so the exact server-action check remains easy to review.
 */

import {
    V2_VIEWS,
    isRecord,
    nonEmptyString,
    nativeActionMatches,
    positiveStoreId,
    responseData,
    stableSerialize,
} from "./connector_v2_action_contracts";

export function installV2ActionAuthorityMethods(ActionClass) {
    Object.assign(ActionClass.prototype, {
        _currentActionCandidates(envelope) {
            const data = responseData(envelope);
            const candidates = [];
            const append = (value) => {
                if (Array.isArray(value)) {
                    candidates.push(...value.filter(isRecord));
                }
            };
            if (this.state.view === V2_VIEWS.overview) {
                append(data.allowed_actions);
                append(data.health && data.health.allowed_actions);
                append(data.store && data.store.allowed_actions);
                append(data.lifecycle && data.lifecycle.allowed_actions);
            } else if (this.state.view === V2_VIEWS.attention) {
                const selected = typeof this._selectedAttentionItem === "function"
                    ? this._selectedAttentionItem()
                    : null;
                // Never borrow an item action from another attention row.
                append(selected ? selected.allowed_actions : data.allowed_actions);
            } else if (this.state.view === V2_VIEWS.run) {
                const run = isRecord(data.run) ? data.run : data;
                if (
                    this.state.runRef &&
                    nonEmptyString(run.run_ref) !== this.state.runRef
                ) {
                    return [];
                }
                const store = isRecord(run.store) ? run.store : null;
                if (
                    store &&
                    this.state.storeId &&
                    positiveStoreId(store.id) !== positiveStoreId(this.state.storeId)
                ) {
                    return [];
                }
                append(run.allowed_actions);
            }
            return candidates;
        },

        _currentActionAuthority(action, item = null) {
            if (!isRecord(action)) {
                return null;
            }
            if (
                this.state.view === V2_VIEWS.attention &&
                isRecord(item) &&
                nonEmptyString(item.item_ref) !== nonEmptyString(this.state.selectedItemRef)
            ) {
                return null;
            }
            const wanted = stableSerialize(action);
            return this._currentActionCandidates(this.state[this.state.view]).find(
                (candidate) =>
                    stableSerialize(candidate) === wanted ||
                    nativeActionMatches(candidate, action),
            ) || null;
        },
    });
}
