/** @odoo-module **/
// Part of the Shopify Connector (U0 operator UI foundation).
//
// HOOT unit tests for the operational dashboard client action. Covers the
// render states (empty / healthy / degraded / manual-review), filtered
// navigation, failed RPC, and accessible labels. The >=30s refresh floor and
// the visibility-aware background-tab pause are implemented in the client
// action (see shopify_connector_dashboard.js) and are covered by source review
// plus the driven runtime walkthrough, not asserted here. Reduced-motion and
// responsive behaviour are CSS-only (media queries), covered by the SCSS + the
// runtime walkthrough.

import { expect, test, describe } from "@odoo/hoot";
import { queryAll, queryFirst, queryText } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, mockService } from "@web/../tests/web_test_helpers";
import { ShopifyConnectorDashboard } from "@shopify_connector_core/js/shopify_connector_dashboard";

function payload(overrides = {}) {
    return Object.assign(
        {
            state: "healthy",
            lead: { severity: "success", icon: "fa-check-circle", text: "All systems normal", hint: "ok" },
            exceptions: [],
            affirmative: "All clear — nothing needs your attention right now.",
            chips: [{ id: "queued", label: "Queued", value: 0, tone: "info", loud: false }],
            activity: [],
            cadence: "Automatic checks run on a schedule.",
            sparkline: { available: false, days: [], summary: "" },
            stores: { total: 1, connected: 1, reconnect_needed: 0, setup_incomplete: 0,
                      disconnecting: 0, disconnected: 0, api_degraded: 0 },
            refresh_interval_seconds: 30,
            generated_at: "2026-07-22 00:00:00",
        },
        overrides
    );
}

function mockOrm(getData) {
    let calls = 0;
    mockService("orm", {
        call: async (model, method) => {
            expect(model).toBe("shopify.connector.ui.dashboard");
            expect(method).toBe("get_dashboard_data");
            calls += 1;
            return getData(calls);
        },
    });
}

let lastAction = null;
mockService("action", { doAction: async (action) => { lastAction = action; } });

describe("shopify connector dashboard", () => {
    test("healthy state renders the success band and an affirmative line", async () => {
        mockOrm(() => payload());
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc-band--success").toHaveCount(1);
        expect(queryText(".sc-band__text")).toBe("All systems normal");
        expect(".sc-affirm").toHaveCount(1);
        expect(".sc-exception").toHaveCount(0);
    });

    test("empty state renders the guided setup card", async () => {
        mockOrm(() => payload({
            state: "empty",
            lead: { severity: "info", icon: "fa-plug", text: "Store setup is incomplete", hint: "Connect your store." },
        }));
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc-band--info").toHaveCount(1);
        expect(".sc-empty").toHaveCount(1);
    });

    test("degraded state renders ranked exceptions with counts", async () => {
        mockOrm(() => payload({
            state: "degraded",
            lead: { severity: "danger", icon: "fa-exclamation-triangle", text: "2 items need your attention", hint: "" },
            exceptions: [
                { id: "failed_final", severity: "danger", icon: "fa-exclamation-triangle",
                  title: "Jobs that stopped", count: 2, why: "why", owner: "Operator",
                  target: { res_model: "shopify.connector.job", domain: [["state", "=", "failed_final"]], name: "x" } },
            ],
        }));
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc-band--danger").toHaveCount(1);
        expect(".sc-exception").toHaveCount(1);
        expect(queryText(".sc-exception__count")).toBe("2");
    });

    test("manual-review distinguished by icon and owner, not colour alone", async () => {
        mockOrm(() => payload({
            state: "manual_review",
            lead: { severity: "danger", icon: "fa-hand-paper-o", text: "1 item waiting on a decision", hint: "reviewer" },
            exceptions: [
                { id: "blocked_manual_review", severity: "danger", icon: "fa-hand-paper-o",
                  title: "Waiting on a review decision", count: 1, why: "why", owner: "Reviewer",
                  target: { res_model: "shopify.connector.job", domain: [["state", "=", "blocked_manual_review"]], name: "x" } },
            ],
        }));
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        // icon present and owner text present -> not colour-only.
        expect(".sc-exception .fa-hand-paper-o").toHaveCount(1);
        expect(queryText(".sc-owner-chip")).toInclude("Reviewer");
    });

    test("clicking an exception opens a filtered native action", async () => {
        lastAction = null;
        mockOrm(() => payload({
            state: "degraded",
            lead: { severity: "danger", icon: "fa-exclamation-triangle", text: "1 item needs your attention", hint: "" },
            exceptions: [
                { id: "failed_final", severity: "danger", icon: "fa-exclamation-triangle",
                  title: "Jobs that stopped", count: 1, why: "why", owner: "Operator",
                  target: { res_model: "shopify.connector.job", domain: [["state", "=", "failed_final"]], name: "Failed jobs" } },
            ],
        }));
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        queryFirst(".sc-exception .sc-btn").click();
        await animationFrame();
        expect(lastAction).not.toBe(null);
        expect(lastAction.res_model).toBe("shopify.connector.job");
        expect(lastAction.type).toBe("ir.actions.act_window");
    });

    test("failed RPC renders an error band with a retry control", async () => {
        mockOrm(() => { throw new Error("boom"); });
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc-band--danger").toHaveCount(1);
        expect(".sc-btn").toHaveCount(1); // "Try again"
    });

    test("accessible labels: lead band is a polite live region", async () => {
        mockOrm(() => payload());
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(queryFirst(".sc-band").getAttribute("aria-live")).toBe("polite");
    });

    test("chips carry a textual value, never colour alone", async () => {
        mockOrm(() => payload({
            chips: [{ id: "retry_waiting", label: "Waiting to retry", value: 3, tone: "warning", loud: true }],
        }));
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(queryAll(".sc-chip__value").length).toBe(1);
        expect(queryText(".sc-chip__value")).toBe("3");
    });
});
