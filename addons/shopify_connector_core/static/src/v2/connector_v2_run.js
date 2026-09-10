/** @odoo-module **/

/* Run evidence and timeline presentation component. */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import {
    NULLABLE_FUNCTION,
    NULLABLE_OBJECT,
    actionFor,
    callback,
    dataObject,
    envelopeState,
    eventKindLabel,
    localeDirection,
    operationLabel,
    safeText,
    triggerTypeLabel,
    workflowLabel,
} from "./connector_v2_contracts";
import { nativeActionMatches, stableSerialize } from "./connector_v2_action_contracts";
import { recordAction } from "../connector_shared_contracts";
import { StateMessage, StatusPill } from "./connector_v2_status";

// Recovery actions are intentionally owned by the Needs Attention surface.
// Rendering them from a run would produce a button without the selected
// attention context required by the recovery adapter.
const RECOVERY_ACTION_KEYS = new Set([
    "retry_job",
    "resolve_manual_review",
    "resolve_mutation",
]);

export class RunTimeline extends Component {
    static template = "shopify_connector_core.v2.RunTimeline";
    static components = { StateMessage, StatusPill };
    static nextId = 1;
    static props = {
        envelope: NULLABLE_OBJECT,
        onAction: NULLABLE_FUNCTION,
        onOpenRecord: NULLABLE_FUNCTION,
    };

    get screen() {
        return envelopeState(this.props);
    }

    get data() {
        return this.screen.data || {};
    }

    get instanceId() {
        if (!this.__instanceId) {
            this.__instanceId = `sc-v2-run-${RunTimeline.nextId++}`;
        }
        return this.__instanceId;
    }

    get titleId() {
        return `${this.instanceId}-title`;
    }

    get resultTitleId() {
        return `${this.instanceId}-result`;
    }

    get timelineTitleId() {
        return `${this.instanceId}-timeline`;
    }

    get contextTitleId() {
        return `${this.instanceId}-context`;
    }

    get jobsTitleId() {
        return `${this.instanceId}-jobs`;
    }

    get recordsTitleId() {
        return `${this.instanceId}-records`;
    }

    get run() {
        return this.data.run || this.data;
    }

    get timeline() {
        return Array.isArray(this.run.timeline) ? this.run.timeline : [];
    }

    get action() {
        const actions = Array.isArray(this.run.allowed_actions)
            ? this.run.allowed_actions.filter(
                  (candidate) => !RECOVERY_ACTION_KEYS.has(candidate && candidate.key),
              )
            : [];
        return actionFor(actions);
    }

    get result() {
        return dataObject(this.run.result) || {};
    }

    get jobs() {
        return Array.isArray(this.run.jobs) ? this.run.jobs : [];
    }

    get affectedRecords() {
        const records = Array.isArray(this.run.affected_records)
            ? this.run.affected_records
            : [];
        return records.filter((record) => this._recordActionIsCurrent(record));
    }

    _recordActionIsCurrent(record) {
        const action = recordAction(record);
        const allowed = Array.isArray(this.run.allowed_actions)
            ? this.run.allowed_actions
            : [];
        if (!action || !allowed.length) {
            return false;
        }
        return allowed.some(
            (candidate) =>
                stableSerialize(candidate) === stableSerialize(action) ||
                nativeActionMatches(candidate, action),
        );
    }

    get truncation() {
        return dataObject(this.run.truncation) || {};
    }

    get incompleteEvidence() {
        return ["jobs", "timeline", "logs", "affected_records", "allowed_actions"].some(
            (key) => this.truncation[key] === true,
        );
    }

    get incompleteEvidenceMessage() {
        return _t(
            "This is a bounded run view. Some work, history, records, or available actions may be omitted; use diagnostics or narrow the operation scope before treating the evidence as complete.",
        );
    }

    get hasRun() {
        return Boolean(
            this.run &&
                (this.run.run_ref || this.run.id || this.run.display_name || this.run.name)
        );
    }

    get localizationDirection() {
        return localeDirection();
    }

    displayWorkflowLabel(value) {
        return workflowLabel(value);
    }

    scopeLabel(value) {
        return safeText(value && value.label, _t("Scope details unavailable"));
    }

    displayEventLabel(value) {
        return eventKindLabel(value);
    }

    triggerLabel(value) {
        return safeText(value && value.label, triggerTypeLabel(value));
    }

    jobLabel(value) {
        return safeText(value && value.label, operationLabel(value && value.operation));
    }

    recordLabel(value) {
        return safeText(
            value && (value.label || value.ref || value.id),
            _t("Affected record")
        );
    }

    act(action) {
        if (action) {
            callback(this.props, "onAction", action, this.run);
        }
    }

    openRecord(record) {
        if (record) {
            callback(this.props, "onOpenRecord", record);
        }
    }
}
