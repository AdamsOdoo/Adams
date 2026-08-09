/** @odoo-module **/
// Part of the Shopify Connector (Store 360 dashboard).
//
// HOOT unit tests for the Store 360 client action. Covers the render states
// (empty / healthy commercial / no-permission), server-built drill-down
// navigation, the truthful bridge and comparison captions, the two distinct
// header timestamps, server-validated period filtering, and the failed-RPC
// band. The >=30s refresh floor and the visibility-aware background-tab
// pause are implemented in the client action (see
// shopify_connector_dashboard.js) and are covered by source review plus the
// driven runtime walkthrough, not asserted here. Reduced-motion and
// responsive behaviour are CSS-only (media queries), covered by the SCSS +
// the runtime walkthrough.
//
// EXACT COUNT CONTRACT: this suite carries exactly 8 tests — the executor
// (`test_u3_hoot_suite.py` EXPECTED_SUITES) asserts equality.

import { expect, test, describe, beforeEach } from "@odoo/hoot";
import { queryFirst, queryText } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, mockService } from "@web/../tests/web_test_helpers";
import { ShopifyConnectorDashboard } from "@shopify_connector_core/js/shopify_connector_dashboard";

const CURRENCY = { id: 1, name: "EUR", symbol: "€", decimal_places: 2, position: "after" };

function payload(overrides = {}) {
    return Object.assign(
        {
            meta: {
                period: "30d",
                periods: ["24h", "7d", "30d", "90d"],
                tz: "UTC",
                window_start: "2026-07-01 00:00:00",
                window_end: "2026-07-31 00:00:00",
                store_id: 7,
                stores: [{ id: 7, name: "Aurora Home Goods", state: "connected" }],
            },
            health: {
                state: "healthy",
                lead: { severity: "success", icon: "fa-check-circle", text: "All systems normal", hint: "ok" },
                jobs: {},
                needs_review: 0,
                backlog: 0,
                oldest_waiting: false,
                week: { succeeded: 12, failed: 0 },
                exceptions: [],
                activity: [],
            },
            flows: [
                { id: "orders", label: "Orders", backlog: 0, failures: 0,
                  last_success: "2026-07-30 10:00:00", last_success_relative: "1 h ago", tone: "neutral" },
            ],
            stores_region: { available: false, rows: [] },
            commercial: {
                available: true,
                blocks: [{
                    currency: CURRENCY, sales: 18432.5, orders: 26, aov: 708.9,
                    previous: { sales: 15000.0, orders: 20, aov: 750.0 },
                }],
                orders_total: 26,
                units: 61,
                previous_units: 50,
                awaiting_review: {
                    count: 0,
                    target: {
                        res_model: "sale.order",
                        domain: [["shopify_connector_review_required", "=", true]],
                        name: "Awaiting data review",
                    },
                },
                orders_target: { res_model: "sale.order", domain: [["shopify_connector_store_id", "=", 7]], name: "Imported Shopify orders" },
                units_target: { res_model: "sale.order.line", domain: [["shopify_line_item_gid", "!=", false]], name: "Lines" },
                trend: { available: false, buckets: [] },
                products: { available: false, rows: [] },
            },
            bridge: {
                available: true, state: "complete_current",
                text: "Complete & current — every discoverable importable order has landed.",
                synced_through: "2026-07-31 09:45:00",
                checkpoint: "2026-07-31 09:50:00",
                scheduled: true, g2: 0, g3: 0, reconciling: false, disconnected: false,
                g2_target: { res_model: "shopify.connector.job", domain: [], name: "g2" },
                g3_target: { res_model: "shopify.connector.job", domain: [], name: "g3" },
            },
            lifecycle: { available: false, reason: "no_permission" },
            dispatch: { available: false, reason: "no_permission" },
            critical: { active: false, causes: [] },
            setup_available: true,
            refresh_interval_seconds: 30,
            generated_at: "2026-07-31 10:00:00",
        },
        overrides
    );
}

function emptyPayload() {
    return payload({
        health: {
            state: "empty",
            lead: { severity: "info", icon: "fa-plug", text: "Store setup is incomplete", hint: "Connect your store." },
            jobs: {}, needs_review: 0, backlog: 0, oldest_waiting: false,
            week: { succeeded: 0, failed: 0 }, exceptions: [], activity: [],
        },
    });
}

function mockOrm(getData, capture) {
    let calls = 0;
    mockService("orm", {
        call: async (model, method, args) => {
            expect(model).toBe("shopify.connector.ui.dashboard");
            expect(method).toBe("get_store_360_data");
            calls += 1;
            if (capture) {
                capture(args, calls);
            }
            return getData(calls);
        },
    });
}

let lastAction = null;

describe("shopify connector dashboard", () => {
    // `mockService` must be called per-test (module scope mutates the
    // services registry while HOOT is still registering the suite).
    beforeEach(() => {
        lastAction = null;
        mockService("action", { doAction: async (action) => { lastAction = action; } });
    });

    test("healthy payload renders the KPI cards and the success band", async () => {
        mockOrm(() => payload());
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc-band--success").toHaveCount(1);
        expect(".sc360-kpi").toHaveCount(5);
        expect(
            queryText(".sc360-kpi[data-kpi='awaiting-review'] .sc360-kpi__value")
        ).toBe("0");
        expect(queryText(".sc360-kpi[data-kpi='orders'] .sc360-kpi__value")).toBe("26");
        // truthful comparison caption present on the sales card
        expect(queryText(".sc360-kpi[data-kpi='sales'] .sc360-kpi__delta")).toInclude("vs previous period");
    });

    test("empty state renders the guided setup card", async () => {
        mockOrm(() => emptyPayload());
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc-band--info").toHaveCount(1);
        expect(".sc-empty").toHaveCount(1);
        expect(".sc_dashboard_setup").toHaveCount(1);
    });

    test("no-permission commercial variant renders the note, never zeros", async () => {
        mockOrm(() => payload({
            commercial: { available: false, reason: "no_permission" },
        }));
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        // Notes are PER SECTION by design: the default payload also carries a
        // no-permission lifecycle section, so scope the assertions to the
        // commercial section this test is about.
        expect(".sc360-commercial .sc360-no-permission").toHaveCount(1);
        expect(".sc360-lifecycle .sc360-no-permission").toHaveCount(1);
        expect(".sc360-kpi").toHaveCount(0);
        expect(queryText(".sc360-commercial .sc360-no-permission")).toInclude(
            "connector health is unaffected"
        );
    });

    test("clicking the orders KPI opens the server-built native action verbatim", async () => {
        mockOrm(() => payload());
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        queryFirst(".sc360-kpi[data-kpi='orders']").click();
        await animationFrame();
        expect(lastAction).not.toBe(null);
        expect(lastAction.type).toBe("ir.actions.act_window");
        expect(lastAction.res_model).toBe("sale.order");
        expect(JSON.stringify(lastAction.domain)).toBe(
            JSON.stringify([["shopify_connector_store_id", "=", 7]])
        );
    });

    test("bridge renders its state label and copy", async () => {
        mockOrm(() => payload({
            bridge: Object.assign(payload().bridge, {
                state: "processing",
                text: "Reconciliation in progress — figures may rise shortly.",
                reconciling: true,
            }),
        }));
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc-bridge--processing").toHaveCount(1);
        expect(queryText(".sc-bridge__state")).toBe("Reconciliation in progress");
    });

    test("failed RPC renders an error band with a retry control", async () => {
        mockOrm(() => { throw new Error("boom"); });
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc-band--danger").toHaveCount(1);
        expect(".sc-btn").toHaveCount(1); // "Try again"
    });

    test("the two header timestamps are distinct: page updated vs Shopify source", async () => {
        mockOrm(() => payload());
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc360-ts-page").toHaveCount(1);
        expect(".sc360-ts-source").toHaveCount(1);
        expect(queryText(".sc360-ts-page")).toInclude("Page updated");
        expect(queryText(".sc360-ts-source")).toInclude("synchronized through");
        // the lead band stays a polite live region
        expect(queryFirst(".sc-band").getAttribute("aria-live")).toBe("polite");
    });

    test("period buttons come from the server registry and re-query with the key", async () => {
        const seen = [];
        mockOrm(() => payload(), (args) => seen.push(args));
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc360-period__btn").toHaveCount(4);
        const first = queryFirst(".sc360-period__btn"); // "24h"
        first.click();
        await animationFrame();
        expect(seen.length).toBe(2);
        expect(seen[1][1]).toBe("24h"); // period KEY, never a domain
    });
});
