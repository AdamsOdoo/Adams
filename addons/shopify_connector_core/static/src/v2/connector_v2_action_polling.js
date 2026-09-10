/** @odoo-module **/

/*
 * Poll lifecycle for the canonical V2 Operations shell.
 *
 * Timers are presentation refreshes, never execution guarantees.  Keeping
 * their lifecycle in a mixin leaves the action controller under the review
 * size limit while preserving one state owner and one request authority.
 */

import {
    POLL_INTERVAL_MS,
    V2_VIEWS,
    isActiveRunEnvelope,
} from "./connector_v2_action_contracts";

export function installV2ActionPollingMethods(ActionClass) {
    Object.assign(ActionClass.prototype, {
        _clearPoll() {
            if (this._pollTimer !== null) {
                window.clearTimeout(this._pollTimer);
                this._pollTimer = null;
            }
        },

        _shouldPoll() {
            if (this._recoveryInFlight || this._recoveryUncertainContext) {
                return false;
            }
            if (!this.state.storeId) {
                return false;
            }
            if (this.state.view === V2_VIEWS.run) {
                return isActiveRunEnvelope(this.state.run);
            }
            return this.state.view === V2_VIEWS.overview || this.state.view === V2_VIEWS.attention;
        },

        _schedulePoll() {
            this._clearPoll();
            if (!this._mounted || document.hidden || !this._shouldPoll()) {
                return;
            }
            const interval = POLL_INTERVAL_MS[this.state.view] || POLL_INTERVAL_MS.overview;
            const scheduledGeneration = this._navigationGeneration;
            const scheduledSelectionEpoch = this._attentionSelectionEpoch;
            this._pollTimer = window.setTimeout(() => {
                this._pollTimer = null;
                // Clearing a timer cannot cancel a callback that has already
                // entered the event queue.  Bind the callback to the same
                // navigation/selection epoch as the timer so it cannot start
                // a stale list read after a same-view attention selection.
                if (
                    scheduledGeneration !== this._navigationGeneration ||
                    scheduledSelectionEpoch !== this._attentionSelectionEpoch
                ) {
                    return;
                }
                void this._pollCurrent();
            }, interval);
        },

        async _pollCurrent() {
            if (
                this._pollInFlight ||
                this._recoveryInFlight ||
                this._recoveryUncertainContext ||
                !this._mounted ||
                document.hidden
            ) {
                return;
            }
            const pollGeneration = this._navigationGeneration;
            const pollSelectionEpoch = this._attentionSelectionEpoch;
            this._pollInFlight = true;
            try {
                if (this.state.view === V2_VIEWS.overview) {
                    await this._loadOverview(this.state.storeId);
                } else if (this.state.view === V2_VIEWS.attention) {
                    await this._loadAttentionList(null, {
                        detailRef: this.state.selectedItemRef,
                    });
                } else if (this.state.view === V2_VIEWS.run && this.state.runRef) {
                    await this._loadRun(this.state.runRef);
                }
            } finally {
                this._pollInFlight = false;
                // An in-flight poll may have completed after a same-view
                // selection.  Do not let its finally block schedule a timer
                // for the superseded selection and race the authoritative
                // detail read.
                if (
                    pollGeneration === this._navigationGeneration &&
                    pollSelectionEpoch === this._attentionSelectionEpoch
                ) {
                    this._schedulePoll();
                }
            }
        },

        _onVisibilityChange() {
            this._clearPoll();
            if (!document.hidden) {
                void this._pollCurrent();
            }
        },
    });
}
