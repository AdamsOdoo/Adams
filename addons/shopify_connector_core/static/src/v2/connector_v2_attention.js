/** @odoo-module **/

/* Attention workspace presentation component. */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import {
    NULLABLE_FUNCTION,
    NULLABLE_OBJECT,
    NULLABLE_STRING,
    actionFor,
    callback,
    dataObject,
    envelopeState,
    eventKindLabel,
    formatAge,
    localeDirection,
    nonEmptyString,
    ownerRoleLabel,
    workflowLabel,
} from "./connector_v2_contracts";
import { StateMessage, StatusPill } from "./connector_v2_status";

// Recovery decisions must remain the primary attention action even when a
// record also exposes navigation actions (for example, "View run").  The
// generic presentation preference intentionally does not know about this
// domain-specific safety priority.
const RECOVERY_ACTION_PREFERENCE = [
    "retry_job",
    "resolve_manual_review",
    "resolve_mutation",
];

export class AttentionWorkspace extends Component {
    static template = "shopify_connector_core.v2.AttentionWorkspace";
    static components = { StateMessage, StatusPill };
    static nextId = 1;
    static props = {
        envelope: NULLABLE_OBJECT,
        selectedItemRef: NULLABLE_STRING,
        onSelect: NULLABLE_FUNCTION,
        onAction: NULLABLE_FUNCTION,
        onPage: NULLABLE_FUNCTION,
        onBack: NULLABLE_FUNCTION,
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
            this.__instanceId = `sc-v2-attention-${AttentionWorkspace.nextId++}`;
        }
        return this.__instanceId;
    }

    get workspaceTitleId() {
        return `${this.instanceId}-title`;
    }

    get listTitleId() {
        return `${this.instanceId}-list`;
    }

    get items() {
        return Array.isArray(this.data.items) ? this.data.items : [];
    }

    get selected() {
        // The list contract may carry a server-selected `detail` projection;
        // the dedicated detail read returns that same DTO directly.  Both
        // forms stay under one envelope and never require a second browser
        // state model.
        const selectedRef = nonEmptyString(this.props.selectedItemRef);
        if (!selectedRef) {
            return null;
        }
        const detail = dataObject(this.data.detail);
        if (detail && nonEmptyString(detail.item_ref) === selectedRef) {
            return detail;
        }
        if (!detail) {
            const inline = this.data.item_ref ? dataObject(this.data) : null;
            if (inline && nonEmptyString(inline.item_ref) === selectedRef) {
                return inline;
            }
        }
        return (
            this.items.find((item) => item.item_ref === selectedRef) || null
        );
    }

    get detailId() {
        return `${this.instanceId}-detail`;
    }

    get detailTitleId() {
        return `${this.detailId}-title`;
    }

    get resolutionTitleId() {
        return `${this.detailId}-resolution`;
    }

    get emptyState() {
        if (this.incompleteProjection) {
            return "partial";
        }
        const state = this.screen.state;
        return ["filtered_empty", "partial", "stale", "refreshing", "manual_review"].includes(
            state
        )
            ? state
            : "empty";
    }

    ageLabel(item) {
        return nonEmptyString(item && item.age_label) || formatAge(item && item.age_seconds);
    }

    displayWorkflowLabel(value) {
        return workflowLabel(value);
    }

    displayOwnerRoleLabel(value) {
        return ownerRoleLabel(value);
    }

    displayEventLabel(value) {
        return eventKindLabel(value);
    }

    get hasDetail() {
        return Boolean(this.selected);
    }

    get hasNextPage() {
        // A page response has no detail projection.  Keep the list-only
        // pagination control truthful while the selected evidence panel is
        // open; the shell will also reject a stale click defensively.
        return Boolean(this.data.next_cursor) && !this.hasDetail;
    }

    get incompleteProjection() {
        return Boolean(this.data.partial || this.data.truncated);
    }

    get incompleteProjectionMessage() {
        return this.data.partial
            ? _t("Some providers could not return a complete bounded result. Refresh or narrow the filters before treating this list as clear.")
            : _t("More attention items exist beyond this bounded view. Narrow the filters to inspect the omitted items.");
    }

    get total() {
        return Number.isFinite(this.data.total) ? this.data.total : this.items.length;
    }

    get filtersSummary() {
        return nonEmptyString(this.data.filters_summary);
    }

    get action() {
        const actions = this.selected && this.selected.allowed_actions;
        return (
            actionFor(actions, RECOVERY_ACTION_PREFERENCE) ||
            actionFor(actions)
        );
    }

    get localizationDirection() {
        return localeDirection();
    }

    select(item) {
        if (item && item.item_ref) {
            callback(this.props, "onSelect", item);
        }
    }

    act(action) {
        if (action) {
            callback(this.props, "onAction", action, this.selected);
        }
    }

    nextPage() {
        if (this.data.next_cursor && !this.hasDetail) {
            callback(this.props, "onPage", this.data.next_cursor);
        }
    }

    back() {
        callback(this.props, "onBack");
    }

    openRun() {
        if (this.selected && this.selected.run_ref) {
            callback(this.props, "onOpenRun", this.selected.run_ref);
        }
    }
}
