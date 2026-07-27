/** @odoo-module **/
// Part of the Shopify Connector (U3 export operator experience).
//
// S7 / S27 — the export preview and diff surface the premium UX master
// specification assigns to U3 as an Owl surface.
//
// WHAT THIS COMPONENT IS ALLOWED TO DO. Render what the server already
// decided, and delegate. It builds no payload, computes no difference,
// evaluates no guard and makes no ownership decision: every value it shows
// came from `shopify.connector.product.export.ui.get_export_preview_data`,
// which is a pure read-only projection of a preview the export service
// recorded when it took a fresh read of Shopify.
//
// The confirm button calls `action_confirm_export_preview` on the preview
// record — the one sanctioned server door — and nothing else. There is no
// apply-without-preview path, no auto-apply toggle and no bulk confirm here,
// because no such server path exists to wire one to.
//
// WHY `canConfirm` IS NOT THE AUTHORISATION. The server re-checks the role,
// the state, the expiry and the plan under a row lock on every confirmation.
// This flag only decides whether to *render* a control that would otherwise
// fail — a surface that offers an action the backend refuses teaches
// operators to distrust it. Hiding the button is never what makes the export
// safe.

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";

// `localization` is a Proxy that THROWS for any parameter not yet loaded
// (`web/static/src/core/l10n/localization.js`), so reading it before the
// localization service has resolved would stop this component mounting. A
// surface must never fail to render over a locale parameter, and "ltr" is the
// documented default.
function localeDirection() {
    try {
        return localization.direction || "ltr";
    } catch {
        return "ltr";
    }
}

export class ShopifyConnectorExportDiff extends Component {
    static template = "shopify_connector_product_export.ExportDiff";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        // RTL: bind the reading direction to the USER'S LOCALE, not to the
        // content. `dir="auto"` resolves from the first strong character of
        // what is on screen, so an Arabic operator reading English
        // operational data got `ltr` and every logical property in the
        // stylesheet resolved LTR-ward.
        //
        // This matters here and nowhere else in Odoo. Odoo 19's BACKEND does
        // not set `dir` on `<html>` or `<body>` at all -- measured under
        // `ar_001` with both rtlcss bundles served and `.o_rtl` present:
        // `documentElement` and `body` both compute `direction: ltr`. Its RTL
        // mechanism is rtlcss, which flips PHYSICAL properties in the CSS
        // bundle. That works for Odoo's own stylesheets and does nothing for
        // this one, because this stylesheet is written entirely in LOGICAL
        // properties -- which resolve against `direction`, and `direction` was
        // never set. Reading the SCSS suggested RTL was handled; rendering it
        // proved it was not.
        this.direction = localeDirection();
        this.state = useState({
            status: "loading", // "loading" | "ready" | "error"
            data: null,
            errorMessage: "",
            confirming: false,
        });
        onWillStart(async () => {
            await this._load();
        });
    }

    get previewId() {
        const context = (this.props.action && this.props.action.context) || {};
        return context.active_id || context.default_preview_id || null;
    }

    async _load() {
        const previewId = this.previewId;
        if (!previewId) {
            this.state.status = "error";
            this.state.errorMessage = _t("No export preview was selected.");
            return;
        }
        try {
            this.state.data = await this.orm.call(
                "shopify.connector.product.export.ui",
                "get_export_preview_data",
                [previewId]
            );
            this.state.status = "ready";
        } catch (error) {
            this.state.status = "error";
            this.state.errorMessage =
                (error && error.data && error.data.message) ||
                (error && error.message) ||
                _t("This export preview could not be loaded.");
        }
    }

    async refresh() {
        await this._load();
    }

    async confirm() {
        // Guarded against a double submit: confirmation enqueues an apply
        // job, and two clicks must not become two apply jobs. The server
        // would refuse the second (the preview is no longer `previewed`),
        // but the operator should not have to find that out from an error.
        if (this.state.confirming) {
            return;
        }
        this.state.confirming = true;
        try {
            await this.orm.call(
                "shopify.connector.product.export.preview",
                "action_confirm_export_preview",
                [[this.state.data.id]]
            );
            await this._load();
        } catch (error) {
            this.state.status = "error";
            this.state.errorMessage =
                (error && error.data && error.data.message) ||
                (error && error.message) ||
                _t("This export could not be confirmed.");
        } finally {
            this.state.confirming = false;
        }
    }

    openRecord() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "shopify.connector.product.export.preview",
            res_id: this.state.data.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // --- presentation helpers (class strings only; no state derivation) ---
    toneClass(prefix, tone) {
        return prefix + " " + prefix + "--" + (tone || "neutral");
    }
    get hasAnythingToShow() {
        const data = this.state.data;
        if (!data) {
            return false;
        }
        return (
            data.sections.length > 0 ||
            data.media.exported ||
            data.refusals.length > 0 ||
            data.tag_replacement.applies
        );
    }
}

registry
    .category("actions")
    .add("shopify_connector_export_diff", ShopifyConnectorExportDiff);
