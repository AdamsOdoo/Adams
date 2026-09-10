/** @odoo-module **/

/*
 * Pure contract tests for the inert V2 presentation package.  DOM coverage is
 * kept in the sibling `.mount.test.js` source so these checks stay independent
 * of an RPC service, router, fixture database, or production model.
 */

import { describe, expect, test } from "@odoo/hoot";
import {
    V2ResponseStates,
    actionFor,
    allowedStore,
    formatAge,
    readEnvelope,
    safeText,
    stateCopy,
    stateMeta,
    storeOptions,
} from "@shopify_connector_core/v2/connector_v2_components";

const ENVELOPE = {
    contract_version: 1,
    generated_at: "2026-08-30T13:20:00Z",
    data_through: "2026-08-30T13:19:42Z",
    store_generation: 18,
    correlation_id: "sc_test_read",
    data: {
        store: { id: 7, name: "Bound store" },
        allowed_stores: [
            { id: 7, name: "Bound store", connection: "connected" },
            { id: 8, name: "Second store", connection: "disconnected" },
        ],
    },
};

describe("V2 presentation response contract", () => {
    test("keeps the common envelope metadata and defaults a data envelope to success", () => {
        const result = readEnvelope(ENVELOPE);

        expect(result.state).toBe("success");
        expect(result.contractVersion).toBe(1);
        expect(result.generatedAt).toBe("2026-08-30T13:20:00Z");
        expect(result.dataThrough).toBe("2026-08-30T13:19:42Z");
        expect(result.storeGeneration).toBe(18);
        expect(result.correlationId).toBe("sc_test_read");
        expect(result.hasData).toBe(true);
        expect(result.data.allowed_stores).toHaveLength(2);
    });

    test("maps compatibility aliases and fails closed for an unknown state", () => {
        expect(readEnvelope({ state: "ready", data: {} }).state).toBe("success");
        expect(readEnvelope({ status: "retryable", data: {} }).state).toBe(
            "retryable_error"
        );
        expect(readEnvelope({ status: "not_a_state", data: {} }).state).toBe(
            "terminal_error"
        );
        expect(readEnvelope(null).state).toBe("loading");
        expect(V2ResponseStates.includes("offline")).toBe(true);
        expect(V2ResponseStates.includes("stale")).toBe(true);
    });

    test("keeps the last DTO visible during a background refresh", () => {
        const result = readEnvelope({ status: "refreshing", data: ENVELOPE.data });

        expect(result.state).toBe("refreshing");
        expect(result.isRefreshing).toBe(true);
        expect(result.data.store.id).toBe(7);
    });

    test("preserves server error copy without manufacturing a retry action", () => {
        const result = readEnvelope({
            status: "offline",
            error: { message: "Network unavailable" },
        });

        expect(result.errorMessage).toBe("Network unavailable");
        expect(result.hasErrorMessage).toBe(true);
        expect(result.data).toBe(null);
        expect(actionFor(undefined)).toBe(null);
        expect(readEnvelope({ status: "terminal_error" }).hasErrorMessage).toBe(false);
    });
});

describe("V2 presentation decisions", () => {
    test("uses the server action preference order and does not invent missing actions", () => {
        const actions = [
            { key: "refresh", label: "Refresh" },
            { key: "open_attention", label: "Review mapping" },
        ];

        expect(actionFor(actions).key).toBe("open_attention");
        expect(actionFor(actions, ["refresh"]).key).toBe("refresh");
        expect(actionFor([], ["retry"])).toBe(null);
    });

    test("only resolves stores from the explicitly supplied permitted list", () => {
        const stores = storeOptions(ENVELOPE.data);

        expect(stores).toHaveLength(2);
        expect(allowedStore(stores, 8).name).toBe("Second store");
        expect(allowedStore(stores, 99)).toBe(null);
        expect(storeOptions({ stores: "not-a-list" })).toHaveLength(0);
    });

    test("uses semantic status metadata and state-specific copy", () => {
        expect(stateMeta("blocked").tone).toBe("danger");
        expect(stateMeta("healthy").tone).toBe("success");
        expect(stateMeta("stale").tone).toBe("warning");
        expect(stateMeta("testing").label).toBe("Testing connection");
        expect(stateMeta("incomplete").label).toBe("Incomplete");
        expect(stateMeta("unknown").label).toBe("Unknown");
        expect(stateCopy("filtered_empty").title).toInclude("filters");
        expect(stateCopy("manual_review").title).toInclude("decision");
        expect(stateCopy("loading").detail).toInclude("stored evidence");
        expect(safeText({ label: "Server label" })).toBe("Server label");
        expect(safeText({ secret: "not rendered" })).toBe("—");
    });

    test("formats bounded age values without exposing a raw age token", () => {
        expect(formatAge(0)).toBe("Less than a minute");
        expect(formatAge(60)).toBe("1 minute");
        expect(formatAge("3600")).toBe("1 hour");
        expect(formatAge(-1)).toBe("Age unavailable");
        expect(formatAge("not-a-number")).toBe("Age unavailable");
    });
});
