/** @odoo-module **/
// C7 split-dashboard HOOT coverage. EXACT COUNT CONTRACT: 8 tests.

import { expect, test, describe, beforeEach } from "@odoo/hoot";
import { queryFirst, queryText } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, mockService } from "@web/../tests/web_test_helpers";
import {
    ShopifyConnectorDashboard,
    ShopifyConnectorHealth,
} from "@shopify_connector_core/js/shopify_connector_dashboard";

const CURRENCY = {
    id: 1,
    name: "EUR",
    symbol: "€",
    decimal_places: 2,
    position: "after",
};

function salesPayload(overrides = {}) {
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
            commercial: {
                available: true,
                blocks: [
                    {
                        currency: CURRENCY,
                        sales: 18432.5,
                        gross: 18432.5,
                        refunds: 0,
                        net: 18432.5,
                        orders: 26,
                        aov: 708.9,
                        previous: {
                            sales: 15000,
                            gross: 15000,
                            refunds: 0,
                            net: 15000,
                            orders: 20,
                            aov: 750,
                        },
                    },
                ],
                orders_total: 26,
                units: 61,
                previous_units: 50,
                orders_target: {
                    res_model: "sale.order",
                    domain: [["shopify_connector_store_id", "=", 7]],
                    name: "Imported Odoo orders",
                },
                units_target: {
                    res_model: "sale.order.line",
                    domain: [["shopify_line_item_gid", "!=", false]],
                    name: "Imported Odoo order lines",
                },
                awaiting_review: {
                    count: 3,
                    blocks: [
                        {
                            currency: CURRENCY,
                            value: 275.5,
                            count: 3,
                            target: {
                                res_model: "sale.order",
                                domain: [
                                    ["shopify_connector_review", "=", true],
                                    ["currency_id", "=", 2],
                                ],
                                name: "Awaiting data review — EUR",
                            },
                        },
                    ],
                    target: {
                        res_model: "sale.order",
                        domain: [["shopify_connector_review", "=", true]],
                        name: "Awaiting data review",
                    },
                },
                refund_scope_note:
                    "Refunded or divergent imported orders are excluded from reconciled figures.",
                trend: { available: false, buckets: [] },
            },
            bridge: {
                available: true,
                state: "complete_current",
                text: "Complete & current",
                synced_through: "2026-07-31 09:45:00",
            },
            lifecycle: { available: false, reason: "no_permission" },
            critical: { active: false, causes: [] },
            refresh_interval_seconds: 30,
            generated_at: "2026-07-31 10:00:00",
        },
        overrides
    );
}

function healthPayload(overrides = {}) {
    return Object.assign(
        {
            meta: {
                store_id: false,
                stores: [
                    { id: 7, name: "Aurora", state: "connected" },
                    { id: 8, name: "Borealis", state: "reconnect_needed" },
                ],
            },
            health: {
                state: "degraded",
                lead: {
                    severity: "danger",
                    icon: "fa-exclamation-triangle",
                    text: "Connector attention required",
                    hint: "One store is failing.",
                },
                jobs: { retry_waiting: 2, failed_final: 1 },
                needs_review: 1,
                backlog: 4,
                oldest_blocked: {
                    age: "2 h ago",
                    target: {
                        res_model: "shopify.connector.job",
                        domain: [["state", "=", "blocked_manual_review"]],
                        name: "Blocked connector cases",
                    },
                },
                week: { succeeded: 12, failed: 1 },
                exceptions: [],
                activity: [],
            },
            stores_region: {
                available: true,
                summary: { healthy: 1, working: 0, attention: 1, unknown: 0 },
                rows: [
                    {
                        id: 7,
                        name: "Aurora",
                        state: "connected",
                        tone: "healthy",
                        backlog: 0,
                        attention: 0,
                        ambiguous_mutations: 0,
                        last_activity_relative: "1 h ago",
                    },
                    {
                        id: 8,
                        name: "Borealis",
                        state: "reconnect_needed",
                        tone: "attention",
                        backlog: 4,
                        attention: 1,
                        ambiguous_mutations: 1,
                        last_activity_relative: false,
                    },
                ],
            },
            flows: [
                {
                    id: "orders",
                    label: "Orders",
                    backlog: 0,
                    failures: 0,
                    last_success_relative: false,
                    tone: "unknown",
                },
            ],
            throttle: {
                rows: [
                    {
                        store_id: 7,
                        store: "Aurora",
                        headroom_ratio: null,
                        observed_at: false,
                    },
                ],
            },
            mappings: {
                rows: [
                    {
                        id: "products",
                        label: "Product mappings",
                        state: "unknown",
                        count: 0,
                    },
                ],
            },
            reconciliation: {
                pending_runs: 1,
                failed_runs: 0,
                ambiguous_mutations: 1,
                verified_mutations: 4,
            },
            mode_switch: {
                rows: [
                    {
                        store_id: 7,
                        store: "Aurora",
                        effective_mode: false,
                        requested_mode: false,
                        state: "unknown",
                        stale: false,
                    },
                ],
            },
            setup_available: true,
            refresh_interval_seconds: 30,
            generated_at: "2026-07-31 10:00:00",
        },
        overrides
    );
}

function mockOrm(expectedMethod, getData, capture) {
    let calls = 0;
    mockService("orm", {
        call: async (model, method, args) => {
            expect(model).toBe("shopify.connector.ui.dashboard");
            expect(method).toBe(expectedMethod);
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
    beforeEach(() => {
        lastAction = null;
        mockService("action", {
            doAction: async (action) => {
                lastAction = action;
            },
        });
    });

    test("sales renders per-currency figures and the separate review population", async () => {
        mockOrm("get_sales_dashboard_data", () => salesPayload());
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc360-sales-currencies tbody tr").toHaveCount(1);
        expect(queryText(".sc360-sales-currencies tbody")).toInclude("EUR");
        expect(queryText(".sc360-commercial")).toInclude("Awaiting data review");
        expect(queryText(".sc360-review-currencies tbody")).toInclude("275.50");
        expect(".o_sc_connector_health").toHaveCount(0);
    });

    test("sales no-permission variant never renders invented zero KPIs", async () => {
        mockOrm("get_sales_dashboard_data", () =>
            salesPayload({ commercial: { available: false, reason: "no_permission" } })
        );
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc360-commercial .sc360-no-permission").toHaveCount(1);
        expect(".sc360-kpi").toHaveCount(0);
    });

    test("sales order KPI opens the server-built native action verbatim", async () => {
        mockOrm("get_sales_dashboard_data", () => salesPayload());
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        queryFirst(".sc360-kpi:first-child").click();
        await animationFrame();
        expect(lastAction.res_model).toBe("sale.order");
        expect(JSON.stringify(lastAction.domain)).toBe(
            JSON.stringify([["shopify_connector_store_id", "=", 7]])
        );
    });

    test("sales bridge renders freshness without a connector-health KPI", async () => {
        mockOrm("get_sales_dashboard_data", () =>
            salesPayload({
                bridge: Object.assign(salesPayload().bridge, {
                    state: "processing",
                    text: "Reconciliation in progress",
                }),
            })
        );
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc-bridge--processing").toHaveCount(1);
        expect(queryText(".sc-bridge__state")).toBe("Reconciliation in progress");
        expect(queryText(".o_sc_dashboard")).not.toInclude("Queue depth");
    });

    test("failed sales RPC renders an error band with retry", async () => {
        mockOrm("get_sales_dashboard_data", () => {
            throw new Error("boom");
        });
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(".sc-band--danger").toHaveCount(1);
        expect(".sc-btn").toHaveCount(1);
    });

    test("sales timestamps distinguish page refresh from source freshness", async () => {
        mockOrm("get_sales_dashboard_data", () => salesPayload());
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        expect(queryText(".sc360-ts-page")).toInclude("Page updated");
        expect(queryText(".sc360-ts-source")).toInclude("synchronized through");
    });

    test("sales period buttons re-query with a server-provided key", async () => {
        const seen = [];
        mockOrm("get_sales_dashboard_data", () => salesPayload(), (args) => seen.push(args));
        await mountWithCleanup(ShopifyConnectorDashboard, { props: {} });
        queryFirst(".sc360-period__btn").click();
        await animationFrame();
        expect(seen.length).toBe(2);
        expect(seen[1][1]).toBe("24h");
    });

    test("health preserves the failing store and explicit unknown evidence without sales", async () => {
        mockOrm("get_connector_health_data", () => healthPayload());
        await mountWithCleanup(ShopifyConnectorHealth, { props: {} });
        expect(".sc360-stores-table tbody tr").toHaveCount(2);
        expect(queryText(".sc360-stores-table tbody")).toInclude("Borealis");
        expect(queryText(".o_sc_connector_health")).toInclude("Unknown");
        expect(queryText(".o_sc_connector_health")).toInclude("Queue depth");
        expect(queryText(".o_sc_connector_health")).toInclude("Oldest blocked case");
        expect(queryText(".o_sc_connector_health")).not.toInclude("Imported Odoo order value");
    });
});
