/** @odoo-module **/

/*
 * P03/P04 client-action integration tests.  These are real HOOT sources and
 * intentionally remain outside the manifest until the Odoo shell activation
 * gate is accepted.  The test seam mocks only Odoo's ORM/action services;
 * production code still calls the named application facade methods.
 */

import { describe, expect, test, beforeEach } from "@odoo/hoot";
import { queryFirst, queryText } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, mockService } from "@web/../tests/web_test_helpers";
import {
    FACADE_MODEL,
    POLL_INTERVAL_MS,
    ROLE_LABELS,
    RPC_METHODS,
    ShopifyConnectorV2Action,
    isActiveRunEnvelope,
    makeEnvelope,
    normalizeRpcError,
    recordAction,
    responseFingerprint,
    serverActionTarget,
    serverAllowsAction,
} from "@shopify_connector_core/v2/connector_v2_action";

const STORE = {
    id: 7,
    name: "Aurora Shopify",
    connection: "connected",
    configuration: "valid",
    activation: "active",
    runtime_health: "healthy",
};

function overviewEnvelope(overrides = {}) {
    return makeEnvelope("success", {
        store: STORE,
        allowed_stores: [
            STORE,
            {
                id: 8,
                name: "Borealis Shopify",
                connection: "connected",
                configuration: "valid",
                activation: "active",
                runtime_health: "healthy",
            },
        ],
        health: {
            title: "Synchronization is healthy.",
            reason: "No unresolved connector exception is recorded.",
            severity: "info",
            observed_at: "2026-08-30T13:08:00Z",
            allowed_actions: [],
        },
        workflows: [],
        attention: { total: 0, items: [] },
        activity: null,
        permissions: { role: "operator", can_start_operation: true, can_configure: false },
        ...overrides,
    });
}

function attentionEnvelope(items = []) {
    return makeEnvelope("success", {
        total: items.length,
        items,
        next_cursor: null,
        has_more: false,
    });
}

function runEnvelope(state = "running", overrides = {}) {
    return makeEnvelope("success", {
        run: {
            run_ref: "job:1842",
            display_name: "RUN-001842",
            state,
            workflow: "orders",
            operation: "order_import",
            store: STORE,
            trigger: { type: "webhook", label: "Shopify webhook" },
            scope: { label: "Order import" },
            result: { title: "In progress", message: "The run is still being observed." },
            timeline: [],
            jobs: [],
            affected_records: [],
            allowed_actions: [],
            ...overrides,
        },
    });
}

describe("V2 client-action contract helpers", () => {
    test("uses the exact versioned attention detail method and shared roles", async () => {
        expect(RPC_METHODS.attentionDetail).toBe("get_attention_detail_v1");
        expect(ROLE_LABELS.reviewer).toBe("Reviewer");
        expect(serverAllowsAction(makeEnvelope("success", {
            permissions: { role: "reviewer" },
            run: { allowed_actions: [{ key: "open_native_record" }] },
        }), { key: "open_native_record", item_ref: "record:1" })).toBe(true);
    });

    test("normalizes access and transient RPC errors without debug fields", () => {
        expect(normalizeRpcError({ data: { name: "AccessError", debug: "secret traceback" } }).status).toBe(
            "permission_empty"
        );
        expect(normalizeRpcError({ name: "NetworkError", message: "temporary outage" }).status).toBe(
            "retryable_error"
        );
        expect(normalizeRpcError({ message: "RPC_ERROR: safe message" }).message).toBe(
            "safe message"
        );
    });

    test("polls only active run states and ignores request-only metadata", () => {
        expect(isActiveRunEnvelope(runEnvelope("running"))).toBe(true);
        expect(isActiveRunEnvelope(runEnvelope("succeeded"))).toBe(false);
        const first = { ...overviewEnvelope(), correlation_id: "sc_a", generated_at: "one" };
        const second = { ...first, correlation_id: "sc_b", generated_at: "two" };
        expect(responseFingerprint(first)).toBe(responseFingerprint(second));
        expect(POLL_INTERVAL_MS.run).toBeLessThan(POLL_INTERVAL_MS.attention);
    });

    test("accepts only a server-returned allowlisted native action target", () => {
        const target = {
            type: "ir.actions.act_window",
            res_model: "stock.picking",
            views: [[false, "form"]],
        };
        expect(serverActionTarget({ key: "open_native_record", target })).toBe(target);
        expect(serverActionTarget({ key: "execute_arbitrary", target })).toBe(null);
        expect(serverActionTarget({ key: "open_native_record", target: { type: "ir.actions.act_url" } })).toBe(
            null
        );
        expect(recordAction({
            id: 1842,
            action_key: "open_order_record",
            target,
        })).toEqual({ key: "open_order_record", target, item_ref: "1842" });
        const envelope = makeEnvelope("success", { allowed_actions: [{ key: "refresh" }] });
        expect(serverAllowsAction(envelope, { key: "refresh" })).toBe(true);
        expect(serverAllowsAction(envelope, { key: "retry_job", item_ref: "job:1" })).toBe(false);
    });
});

describe("V2 client-action shell", () => {
    let calls;
    let actions;

    beforeEach(() => {
        calls = [];
        actions = [];
        mockService("action", {
            doAction: async (target) => actions.push(target),
        });
    });

    test("uses one named application-facade RPC for the initial Overview", async () => {
        mockService("orm", {
            call: async (model, method, args) => {
                calls.push({ model, method, args });
                return overviewEnvelope();
            },
        });
        await mountWithCleanup(ShopifyConnectorV2Action, {
            props: { action: { context: { default_store_id: 7 } } },
        });

        expect(calls).toHaveLength(1);
        expect(calls[0]).toEqual({
            model: FACADE_MODEL,
            method: RPC_METHODS.overview,
            args: [7],
        });
        expect(queryText(".sc-v2-shell__nav")).toInclude("Overview");
        expect(queryText(".sc-v2-overview")).toInclude("Synchronization is healthy");
    });

    test("changes stores only through a server-provided option and re-reads Overview", async () => {
        mockService("orm", {
            call: async (model, method, args) => {
                calls.push({ model, method, args });
                return overviewEnvelope({ store: args[0] === 8 ? { ...STORE, id: 8, name: "Borealis Shopify" } : STORE });
            },
        });
        await mountWithCleanup(ShopifyConnectorV2Action, {
            props: { action: { context: { default_store_id: 7 } } },
        });
        const select = queryFirst("select");
        select.value = "8";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        await animationFrame();

        expect(calls).toHaveLength(2);
        expect(calls[1]).toEqual({
            model: FACADE_MODEL,
            method: RPC_METHODS.overview,
            args: [8],
        });
        expect(queryText(".sc-v2-shell__identity")).toInclude("Borealis Shopify");
    });

    test("renders a permission state and never invokes an absent action", async () => {
        mockService("orm", {
            call: async () => {
                throw { data: { name: "AccessError", message: "Access is restricted" } };
            },
        });
        const component = await mountWithCleanup(ShopifyConnectorV2Action, {
            props: { action: { context: { default_store_id: 7 } } },
        });

        expect(queryText(".sc-v2-state-message__title")).toBe("There is no data to show for this role");
        await component.handleAction({ key: "retry_job", item_ref: "job:1" });
        expect(actions).toHaveLength(0);
    });

    test("passes a returned native target verbatim to the Odoo action service", async () => {
        const target = {
            type: "ir.actions.act_window",
            res_model: "shopify.connector.store",
            views: [[false, "list"]],
        };
        mockService("orm", {
            call: async () => overviewEnvelope({
                allowed_actions: [{ key: "manage_stores", label: "Manage stores", target }],
            }),
        });
        const component = await mountWithCleanup(ShopifyConnectorV2Action, {
            props: { action: { context: { default_store_id: 7 } } },
        });
        await component.handleAction(component.state.overview.data.allowed_actions[0]);
        expect(actions).toHaveLength(1);
        expect(actions[0]).toBe(target);
    });

    test("loads attention detail through the named detail RPC and restores focus", async () => {
        const item = {
            item_ref: "attn:manual_review_job:1842:7",
            state_version: 7,
            severity: "warning",
            severity_label: "Needs review",
            title: "A sync job needs investigation.",
            impact_summary: "The operation ended without a successful terminal result.",
            age_seconds: 60,
            workflow: "orders",
            owner_role: "operator",
            allowed_actions: [],
        };
        const detail = { ...item, what_happened: "Review the stored evidence." };
        mockService("orm", {
            call: async (model, method, args) => {
                calls.push({ model, method, args });
                if (method === RPC_METHODS.attention) {
                    return attentionEnvelope([item]);
                }
                if (method === RPC_METHODS.attentionDetail) {
                    return makeEnvelope("success", detail);
                }
                throw new Error("unexpected method");
            },
        });
        const component = await mountWithCleanup(ShopifyConnectorV2Action, {
            props: { action: { context: { default_store_id: 7 } } },
        });
        await component.openAttention(item);
        await animationFrame();

        expect(calls.map((call) => call.method)).toEqual([
            RPC_METHODS.overview,
            RPC_METHODS.attention,
            RPC_METHODS.attentionDetail,
        ]);
        expect(queryFirst(".sc-v2-attention__detail")).toBeTruthy();
        expect(document.activeElement).toBe(queryFirst(".sc-v2-attention__detail"));
    });

    test("does not repaint unchanged polling evidence", async () => {
        const result = overviewEnvelope();
        mockService("orm", {
            call: async () => ({ ...result, correlation_id: `sc_${calls.length}` }),
        });
        const component = await mountWithCleanup(ShopifyConnectorV2Action, {
            props: { action: { context: { default_store_id: 7 } } },
        });
        const before = component.state.overview;
        await component._pollCurrent();
        expect(component.state.overview).toBe(before);
    });
});
