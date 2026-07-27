/** @odoo-module **/
// Part of the Shopify Connector (U0 operator UI foundation).
//
// The operational dashboard: the single bounded Owl client action in U0. It
// stays inside the Odoo web client (standard action + ORM services, standard
// menus/breadcrumbs); it is not an SPA, has no custom router, no parallel
// state store, and no client-side list re-implementation. It reads ONLY the
// read-only aggregate service `shopify.connector.ui.dashboard.get_dashboard_data`
// and navigates to native filtered lists via the action service.
//
// Auto-refresh is never faster than 30s and is paused while the browser tab is
// hidden (PB-12 / WCAG 2.2.2).

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
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

export class ShopifyConnectorDashboard extends Component {
    static template = "shopify_connector_core.Dashboard";
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
        // Odoo 19's backend sets no `dir` ATTRIBUTE on `<html>` or `<body>`.
        // It sets the CSS `direction` PROPERTY instead, on inner containers
        // (`webclient_layout.scss` lines 22/73/84 at the pinned 30bde9ff),
        // expressly so rtlcss can flip it -- Odoo's own comment there says
        // so. Binding `dir` on this root is therefore belt-and-braces rather
        // than a substitute for Odoo's mechanism: it makes this component's
        // logical properties resolve correctly from the user's locale
        // without depending on the asset pipeline having produced a flipped
        // bundle.
        //
        // A correction to what this comment previously said: it claimed
        // `direction` "was never set" by Odoo. That was measured in an
        // environment where the `rtlcss` binary was MISSING, in which case
        // `AssetsBundle.run_rtlcss` returns the stylesheet unflipped while
        // the `.rtl.` URL is still served from the locale alone. The LTR
        // render was real; the conclusion about Odoo was not.
        this.direction = localeDirection();
        this.state = useState({
            status: "loading", // "loading" | "ready" | "error"
            data: null,
            errorMessage: "",
        });
        this._refreshTimer = null;
        this._onVisibility = this._onVisibility.bind(this);

        onWillStart(async () => {
            await this._load();
        });
        onMounted(() => {
            document.addEventListener("visibilitychange", this._onVisibility);
            this._scheduleRefresh();
        });
        onWillUnmount(() => {
            document.removeEventListener("visibilitychange", this._onVisibility);
            this._clearRefresh();
        });
    }

    get refreshMs() {
        const secs = (this.state.data && this.state.data.refresh_interval_seconds) || 30;
        // Hard floor of 30s regardless of what the server suggests (PB-12).
        return Math.max(30, secs) * 1000;
    }

    async _load() {
        try {
            const data = await this.orm.call(
                "shopify.connector.ui.dashboard",
                "get_dashboard_data",
                []
            );
            this.state.data = data;
            this.state.status = "ready";
        } catch (error) {
            this.state.status = "error";
            this.state.errorMessage =
                (error && error.data && error.data.message) ||
                (error && error.message) ||
                _t("The dashboard could not be loaded.");
        }
    }

    _scheduleRefresh() {
        this._clearRefresh();
        if (document.hidden) {
            return; // paused in a background tab
        }
        this._refreshTimer = window.setInterval(() => {
            if (!document.hidden) {
                this._load();
            }
        }, this.refreshMs);
    }

    _clearRefresh() {
        if (this._refreshTimer) {
            window.clearInterval(this._refreshTimer);
            this._refreshTimer = null;
        }
    }

    _onVisibility() {
        if (document.hidden) {
            this._clearRefresh();
        } else {
            this._load();
            this._scheduleRefresh();
        }
    }

    async refresh() {
        await this._load();
    }

    openException(exception) {
        if (!exception || !exception.target) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: exception.target.name,
            res_model: exception.target.res_model,
            domain: exception.target.domain || [],
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    // S1 entry route 1 of 3. Opens the guided setup client action; the setup
    // service refuses a non-Administrator on the server regardless, so this
    // is navigation rather than authorization.
    openSetup() {
        this.action.doAction(
            "shopify_connector_core.action_shopify_connector_setup_wizard"
        );
    }

    // --- presentation helpers (class strings only; no state derivation) ---
    bandClass(severity) {
        return "sc-band sc-band--" + (severity || "neutral");
    }
    exceptionClass(severity) {
        return "sc-exception sc-exception--" + (severity || "danger");
    }
    chipClass(chip) {
        let cls = "sc-chip sc-chip--" + (chip.tone || "neutral");
        if (chip.loud) {
            cls += " sc-chip--loud";
        }
        return cls;
    }
    badgeClass(tone) {
        return "sc-badge sc-badge--" + (tone || "neutral");
    }
    // Fixed bar heights so the sparkline stays a bounded DOM with no inline math in template.
    barHeight(value, max) {
        const m = max || 1;
        const pct = Math.round((Math.min(value, m) / m) * 100);
        return "height:" + pct + "%";
    }
    get sparkMax() {
        const data = this.state.data;
        if (!data || !data.sparkline || !data.sparkline.available) {
            return 1;
        }
        let max = 1;
        for (const d of data.sparkline.days) {
            max = Math.max(max, d.success + d.failure);
        }
        return max;
    }
}

registry.category("actions").add("shopify_connector_dashboard", ShopifyConnectorDashboard);
