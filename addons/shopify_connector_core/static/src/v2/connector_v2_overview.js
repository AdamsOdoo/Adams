/** @odoo-module **/

/* Store overview presentation components. */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import {
    NULLABLE_BOOLEAN,
    NULLABLE_FUNCTION,
    NULLABLE_OBJECT,
    NULLABLE_STRING,
    actionFor,
    allowedStore,
    callback,
    dataObject,
    envelopeState,
    formatAge,
    localeDirection,
    nonEmptyString,
    safeText,
    storeOptions,
    workflowLabel,
    stateMeta,
} from "./connector_v2_contracts";
import { isReadOnlyAllStores } from "../connector_shared_contracts";
import { StateMessage, StatusPill } from "./connector_v2_status";

export class HealthBand extends Component {
    static template = "shopify_connector_core.v2.HealthBand";
    static components = { StatusPill, StateMessage };
    static props = {
        envelope: NULLABLE_OBJECT,
        compact: NULLABLE_BOOLEAN,
        onAction: NULLABLE_FUNCTION,
    };

    get screen() {
        return envelopeState(this.props);
    }

    get health() {
        return dataObject(this.screen.data && this.screen.data.health);
    }

    get action() {
        return actionFor(this.health && this.health.allowed_actions);
    }

    get severity() {
        return (this.health && this.health.severity) || this.screen.state;
    }

    get healthToneClass() {
        return stateMeta(this.severity).tone;
    }

    get healthTitle() {
        return safeText(this.health && this.health.title, _t("Store health is not available"));
    }

    get healthReason() {
        return safeText(this.health && this.health.reason, _t("Refresh the stored evidence to continue."));
    }

    get observedAt() {
        return safeText(
            this.health && (this.health.observed_label || this.health.observed_at),
            _t("Observation time unavailable")
        );
    }

    get nextCheckAt() {
        return safeText(
            this.health && (this.health.next_check_label || this.health.next_check_at),
            ""
        );
    }

    emitAction() {
        callback(this.props, "onAction", this.action);
    }
}

export class StoreSwitcher extends Component {
    static template = "shopify_connector_core.v2.StoreSwitcher";
    static components = { StatusPill };
    static nextId = 1;
    static props = {
        envelope: NULLABLE_OBJECT,
        id: NULLABLE_STRING,
        onSelect: NULLABLE_FUNCTION,
        onManage: NULLABLE_FUNCTION,
    };

    get screen() {
        return envelopeState(this.props);
    }

    get data() {
        return this.screen.data || {};
    }

    get stores() {
        return storeOptions(this.data);
    }

    get selectedId() {
        if (
            this.hasAllStoresOption &&
            (this.data.selected_store_id === "__all__" ||
                this.data.selected_store_id === "all" ||
                (this.data.all_stores && this.data.all_stores.selected))
        ) {
            return "__all__";
        }
        return this.data.selected_store_id || (this.data.store && this.data.store.id) || "";
    }

    get selectId() {
        if (nonEmptyString(this.props.id)) {
            return this.props.id;
        }
        if (!this.__selectId) {
            this.__selectId = `sc-v2-store-select-${StoreSwitcher.nextId++}`;
        }
        return this.__selectId;
    }

    isSelectedStore(store) {
        return Boolean(store) && String(store.id) === String(this.selectedId);
    }

    get selectedStore() {
        if (this.selectedId === "__all__") {
            return null;
        }
        return (
            allowedStore(this.stores, this.selectedId) ||
            dataObject(this.data.store) ||
            null
        );
    }

    get hasAllStoresOption() {
        return Boolean(
            this.data.all_stores &&
                this.data.all_stores.allowed &&
                isReadOnlyAllStores({ kind: "all", read_only: this.data.all_stores.read_only }),
        );
    }

    get canManage() {
        return Boolean(actionFor(this.data.allowed_actions, ["manage_stores", "add_store"]));
    }

    selectStore(ev) {
        const value = ev && ev.target ? ev.target.value : "";
        if (value === "__all__") {
            if (this.hasAllStoresOption) {
                callback(this.props, "onSelect", { kind: "all", read_only: true });
            }
            return;
        }
        const store = allowedStore(this.stores, value);
        if (store) {
            callback(this.props, "onSelect", store);
        }
    }

    manageStores() {
        const action = actionFor(this.data.allowed_actions, ["manage_stores", "add_store"]);
        if (action) {
            callback(this.props, "onManage", action);
        }
    }
}

export class Overview extends Component {
    static template = "shopify_connector_core.v2.Overview";
    static components = { HealthBand, StateMessage, StatusPill, StoreSwitcher };
    static nextId = 1;
    static props = {
        envelope: NULLABLE_OBJECT,
        onStoreChange: NULLABLE_FUNCTION,
        onAction: NULLABLE_FUNCTION,
        onOpenAttention: NULLABLE_FUNCTION,
        onOpenWorkflow: NULLABLE_FUNCTION,
        onOpenRun: NULLABLE_FUNCTION,
    };

    get screen() {
        return envelopeState(this.props);
    }

    get data() {
        return this.screen.data || {};
    }

    get instanceId() {
        if (!this.__instanceId) {
            this.__instanceId = `sc-v2-overview-${Overview.nextId++}`;
        }
        return this.__instanceId;
    }

    get titleId() {
        return `${this.instanceId}-title`;
    }

    get workflowsTitleId() {
        return `${this.instanceId}-workflows`;
    }

    get attentionTitleId() {
        return `${this.instanceId}-attention`;
    }

    get activityTitleId() {
        return `${this.instanceId}-activity`;
    }

    get workflows() {
        return Array.isArray(this.data.workflows) ? this.data.workflows : [];
    }

    get attentionItems() {
        const attention = dataObject(this.data.attention);
        return Array.isArray(attention && attention.items)
            ? attention.items.slice(0, 3)
            : [];
    }

    get attentionIncomplete() {
        const attention = dataObject(this.data.attention);
        return Boolean(attention && (attention.partial || attention.truncated));
    }

    get attentionIncompleteMessage() {
        const attention = dataObject(this.data.attention);
        if (attention && attention.partial) {
            return _t(
                "Some attention providers were unavailable. The visible items are not a complete clear result; refresh before treating this store as healthy.",
            );
        }
        return _t(
            "More attention items exist beyond this bounded preview. Open Needs Attention or narrow the result before treating this store as clear.",
        );
    }

    ageLabel(item) {
        return nonEmptyString(item && item.age_label) || formatAge(item && item.age_seconds);
    }

    displayWorkflowLabel(value) {
        return workflowLabel(value);
    }

    get activity() {
        return dataObject(this.data.activity);
    }

    get stateAction() {
        return actionFor(this.data.allowed_actions);
    }

    get hasStore() {
        return Boolean(this.data.store && this.data.store.id);
    }

    get localizationDirection() {
        return localeDirection();
    }

    emitAction(action) {
        callback(this.props, "onAction", action);
    }

    selectStore(store) {
        callback(this.props, "onStoreChange", store);
    }

    openAttention(item) {
        callback(this.props, "onOpenAttention", item);
    }

    openWorkflow(workflow) {
        callback(this.props, "onOpenWorkflow", workflow);
    }

    openRun(runRef) {
        if (runRef) {
            callback(this.props, "onOpenRun", runRef);
        }
    }
}
