/** @odoo-module **/

/*
 * Concrete semantic controls for the four setup choices that used to be
 * represented only by a link to grouped Settings.  The server supplies the
 * initial scalar values; this component emits only the closed field key and
 * the typed value back to the single setup command.
 */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { asArray, asObject } from "./shopify_connector_p16_contract";

const CONTROL_FIELDS = Object.freeze({
    directions: Object.freeze([
        { key: "product_domain_enabled", type: "boolean", label: _t("Catalog import") },
        { key: "product_export_domain_enabled", type: "boolean", label: _t("Catalog export") },
        { key: "sale_domain_enabled", type: "boolean", label: _t("Order import") },
        { key: "inventory_domain_enabled", type: "boolean", label: _t("Inventory sync") },
        { key: "fulfillment_domain_enabled", type: "boolean", label: _t("Fulfillment sync") },
    ]),
    source_of_truth: Object.freeze([
        {
            key: "product_first_sync_source",
            type: "selection",
            label: _t("Initial catalog source"),
            choices: Object.freeze([
                { value: "shopify_source", label: _t("Shopify source") },
                { value: "odoo_source", label: _t("Odoo source") },
                { value: "both_match_first", label: _t("Both; match first") },
            ]),
        },
        {
            key: "price_source_of_truth",
            type: "selection",
            label: _t("Price source of truth"),
            choices: Object.freeze([
                { value: "odoo_authoritative", label: _t("Odoo") },
                { value: "shopify_authoritative", label: _t("Shopify") },
            ]),
        },
        {
            key: "media_source_of_truth",
            type: "selection",
            label: _t("Media source of truth"),
            choices: Object.freeze([
                { value: "odoo", label: _t("Odoo") },
                { value: "shopify", label: _t("Shopify") },
            ]),
        },
    ]),
    notification: Object.freeze([
        {
            key: "notification_default_enabled",
            type: "boolean",
            label: _t("Enable customer delivery notifications"),
        },
    ]),
    first_push: Object.freeze([
        {
            key: "inventory_scheduled_sync_enabled",
            type: "boolean",
            label: _t("Enable the first stock preview scan"),
        },
    ]),
});

function callback(props, name, ...args) {
    if (props && typeof props[name] === "function") {
        return props[name](...args);
    }
    return undefined;
}

export class P16SetupStepControls extends Component {
    static template = "shopify_connector_core.P16SetupStepControls";
    static props = { "*": true };
    static nextId = 1;

    setup() {
        this.instanceId = `p16-setup-controls-${P16SetupStepControls.nextId++}`;
    }

    get fields() {
        const values = asObject(this.props.values);
        return asArray(CONTROL_FIELDS[this.props.stepKey]).filter((field) =>
            Object.prototype.hasOwnProperty.call(values, field.key),
        );
    }

    get values() {
        return asObject(this.props.values);
    }

    fieldId(field) {
        return `${this.instanceId}-${field.key}`;
    }

    value(field) {
        const value = this.values[field.key];
        return field.type === "boolean" ? Boolean(value) : (value || "");
    }

    input(field, ev) {
        const value = field.type === "boolean" ? Boolean(ev.target.checked) : ev.target.value;
        callback(this.props, "onChange", field.key, value);
    }

    choices(field) {
        return asArray(field.choices);
    }
}

export { CONTROL_FIELDS };
