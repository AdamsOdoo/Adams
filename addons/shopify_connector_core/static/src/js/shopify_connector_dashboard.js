/** @odoo-module **/
// Part of the Shopify Connector (U0 foundation → Store 360, spec
// docs/02-product/ui-operations-360-dashboard-spec-2026-08-01.md).
//
// C7's two separate dashboards share one restrained component base and two
// bounded RPCs. The sales page never receives health aggregates; Connector
// Health never receives a sales KPI.
// It stays inside the Odoo web client (standard action + ORM services,
// standard menus/breadcrumbs); it is not an SPA, has no custom router, no
// parallel state store, and no client-side list re-implementation. It reads
// ONLY the read-only aggregate service's sales/health methods and navigates
// to native filtered lists through SERVER-BUILT targets — the client never
// constructs a domain, model name or action id of its own.
//
// Auto-refresh is never faster than 30s and is paused while the browser tab
// is hidden (PB-12 / WCAG 2.2.2). A page refresh updates "Page updated" and
// must NEVER advance the Shopify-source timestamps — those come from the
// completion stamps the backend promotes (spec §9.1/§9.5).

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";

// `localization` is a Proxy that THROWS for any parameter not yet loaded
// (`web/static/src/core/l10n/localization.js`), so reading it before the
// localization service has resolved would stop this component mounting. A
// surface must never fail to render over a locale parameter, and "ltr" is
// the documented default.
function localeDirection() {
    try {
        return localization.direction || "ltr";
    } catch {
        return "ltr";
    }
}

export class ShopifyConnectorDashboard extends Component {
    static template = "shopify_connector_core.SalesDashboard";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        // RTL: bind the reading direction to the USER'S LOCALE (see the
        // rtlcss note in the git history of this file): Odoo 19 sets the
        // CSS `direction` property on inner containers, and this attribute
        // makes the component's logical properties resolve from the locale
        // without depending on a flipped bundle.
        this.direction = localeDirection();
        this.state = useState({
            status: "loading", // "loading" | "ready" | "error"
            data: null,
            errorMessage: "",
            // Server-validated filters. The client only ever sends a store
            // id from the server-provided list and a period KEY from the
            // server-provided registry.
            storeId: false,
            period: "30d",
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

    get rpcMethod() {
        return "get_sales_dashboard_data";
    }

    get rpcArgs() {
        return [this.state.storeId || false, this.state.period];
    }

    async _load() {
        try {
            const data = await this.orm.call(
                "shopify.connector.ui.dashboard",
                this.rpcMethod,
                this.rpcArgs
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

    // --- filters (values come exclusively from the server payload) --------
    async onStoreChange(ev) {
        const raw = ev.target.value;
        this.state.storeId = raw ? parseInt(raw, 10) : false;
        await this._load();
    }

    async setPeriod(period) {
        this.state.period = period;
        await this._load();
    }

    // --- navigation: server-built targets only -----------------------------
    openTarget(target) {
        if (!target || !target.res_model) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: target.name,
            res_model: target.res_model,
            domain: target.domain || [],
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    // Kept for the health region (same payload shape as before).
    openException(exception) {
        if (exception) {
            this.openTarget(exception.target);
        }
    }

    // S1 entry route 1 of 3. Opens the guided setup client action; the setup
    // service refuses a non-Administrator on the server regardless, so this
    // is navigation rather than authorization.
    openSetup() {
        this.action.doAction(
            "shopify_connector_core.action_shopify_connector_setup_wizard"
        );
    }

    // --- presentation helpers (class strings / formatting only) -----------
    bandClass(severity) {
        return "sc-band sc-band--" + (severity || "neutral");
    }
    exceptionClass(severity) {
        return "sc-exception sc-exception--" + (severity || "danger");
    }
    badgeClass(tone) {
        return "sc-badge sc-badge--" + (tone || "neutral");
    }
    bridgeClass(state) {
        return "sc-bridge sc-bridge--" + (state || "stale");
    }

    formatMoney(currency, value) {
        if (value === false || value === null || value === undefined) {
            return "—";
        }
        const decimals =
            currency && currency.decimal_places !== undefined
                ? currency.decimal_places
                : 2;
        // Plain grouped decimal; the currency name/symbol is rendered
        // beside the amount inside a <bdi> so RTL contexts keep the pair
        // intact (spec §11 bidi isolation).
        const amount = Number(value).toLocaleString(undefined, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        });
        if (!currency || !currency.symbol) {
            return amount;
        }
        return currency.position === "before"
            ? currency.symbol + " " + amount
            : amount + " " + currency.symbol;
    }

    formatNumber(value) {
        if (value === false || value === null || value === undefined) {
            return "—";
        }
        return Number(value).toLocaleString();
    }

    formatShare(share) {
        if (share === false || share === null || share === undefined) {
            return "—";
        }
        return Math.round(share * 1000) / 10 + "%";
    }

    // C∆: truthful comparison caption. Previous 0 → "no prior-period data",
    // never a percentage (spec C∆).
    deltaInfo(current, previous) {
        if (!previous) {
            return { available: false, text: _t("no prior-period data") };
        }
        const ratio = (current - previous) / previous;
        const pct = Math.round(Math.abs(ratio) * 1000) / 10;
        if (ratio > 0.0005) {
            return { available: true, tone: "up", text: "+" + pct + "%" };
        }
        if (ratio < -0.0005) {
            return { available: true, tone: "down", text: "−" + pct + "%" };
        }
        return { available: true, tone: "flat", text: "±0%" };
    }

    barHeight(value, max) {
        const m = max || 1;
        const pct = Math.round((Math.min(value, m) / m) * 100);
        return "height:" + Math.max(pct, value > 0 ? 2 : 0) + "%";
    }

    get trendMax() {
        const data = this.state.data;
        const trend =
            data && data.commercial && data.commercial.trend;
        if (!trend || !trend.available) {
            return 1;
        }
        let max = 1;
        for (const bucket of trend.buckets) {
            max = Math.max(max, bucket.value, bucket.previous);
        }
        return max;
    }

    // Localised HH:MM for the two header timestamps. Server sends UTC
    // strings; the Date conversion applies the browser locale/zone, and the
    // two labels stay visually and semantically distinct (spec §9.1).
    formatInstant(value) {
        if (!value) {
            return _t("not yet");
        }
        const date = new Date(value.replace(" ", "T") + "Z");
        if (isNaN(date.getTime())) {
            return value;
        }
        return date.toLocaleString(undefined, {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    periodLabel(period) {
        return {
            "24h": _t("Last 24 hours"),
            "7d": _t("Last 7 days"),
            "30d": _t("Last 30 days"),
            "90d": _t("Last 90 days"),
        }[period] || period;
    }

    bridgeLabel(state) {
        return {
            complete_current: _t("Complete & current"),
            processing: _t("Reconciliation in progress"),
            stale: _t("Not proven current"),
            incomplete: _t("Incomplete — action needed"),
        }[state] || state;
    }

    storeStateLabel(state) {
        return {
            setup_incomplete: _t("Setup incomplete"),
            connected: _t("Connected"),
            reconnect_needed: _t("Reconnect needed"),
            disconnecting: _t("Disconnecting"),
            disconnected: _t("Disconnected"),
        }[state] || state;
    }

    healthToneLabel(tone) {
        return {
            healthy: _t("Healthy"),
            working: _t("Work in progress"),
            attention: _t("Needs attention"),
            unknown: _t("Unknown"),
        }[tone] || tone;
    }

    evidenceStateLabel(state) {
        return {
            observed: _t("Observed"),
            unknown: _t("Unknown"),
        }[state] || state;
    }

    modeLabel(mode) {
        return {
            mode1: _t("Mode 1 — review first"),
            mode2: _t("Mode 2 — automatic apply"),
        }[mode] || _t("Unknown");
    }
}

export class ShopifyConnectorHealth extends ShopifyConnectorDashboard {
    static template = "shopify_connector_core.ConnectorHealth";

    get rpcMethod() {
        return "get_connector_health_data";
    }

    get rpcArgs() {
        return [this.state.storeId || false];
    }
}

// The original tag remains a compatibility alias, but it now resolves to the
// sales-only page rather than the retired combined Store 360 presentation.
registry.category("actions").add("shopify_connector_dashboard", ShopifyConnectorDashboard);
registry.category("actions").add("shopify_connector_sales_dashboard", ShopifyConnectorDashboard);
registry.category("actions").add("shopify_connector_health", ShopifyConnectorHealth);
