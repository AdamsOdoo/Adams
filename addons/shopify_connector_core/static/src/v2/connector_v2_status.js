/** @odoo-module **/

/* Shared status and response-state presentation primitives. */

import { Component } from "@odoo/owl";
import {
    NULLABLE_BOOLEAN,
    NULLABLE_FUNCTION,
    NULLABLE_OBJECT,
    NULLABLE_STRING,
    callback,
    nonEmptyString,
    stateCopy,
    stateMeta,
} from "./connector_v2_contracts";

export class StatusPill extends Component {
    static template = "shopify_connector_core.v2.StatusPill";
    static props = {
        state: NULLABLE_STRING,
        label: NULLABLE_STRING,
        compact: NULLABLE_BOOLEAN,
        live: NULLABLE_BOOLEAN,
    };

    get meta() {
        return stateMeta(this.props.state);
    }

    get displayLabel() {
        return nonEmptyString(this.props.label) || this.meta.label;
    }

    get className() {
        return (
            `sc-v2-status-pill sc-v2-status-pill--${this.meta.tone}` +
            (this.props.compact ? " sc-v2-status-pill--compact" : "")
        );
    }
}

export class StateMessage extends Component {
    static template = "shopify_connector_core.v2.StateMessage";
    static props = {
        state: NULLABLE_STRING,
        title: NULLABLE_STRING,
        detail: NULLABLE_STRING,
        action: NULLABLE_OBJECT,
        onAction: NULLABLE_FUNCTION,
        busy: NULLABLE_BOOLEAN,
    };

    get meta() {
        return stateMeta(this.props.state);
    }

    get copy() {
        return stateCopy(this.props.state);
    }

    get displayTitle() {
        return nonEmptyString(this.props.title) || this.copy.title;
    }

    get displayDetail() {
        return nonEmptyString(this.props.detail) || this.copy.detail;
    }

    get isError() {
        return ["terminal_error", "retryable_error", "permission_empty", "conflict"].includes(
            this.props.state,
        );
    }

    emitAction() {
        callback(this.props, "onAction", this.props.action);
    }
}
