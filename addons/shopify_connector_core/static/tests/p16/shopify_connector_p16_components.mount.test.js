/** @odoo-module **/

/* Real HOOT mounts for the isolated P16 components.  The tests deliberately
 * mount each surface without a backend service: the components only render
 * server-shaped DTOs and emit callbacks. */

import { describe, expect, test } from "@odoo/hoot";
import { queryAll, queryFirst, queryText } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import {
    P16CredentialPanel,
    P16PhaseRail,
    P16ReadinessPanel,
    P16SettingsGroups,
    P16StoreList,
} from "@shopify_connector_core/p16/shopify_connector_p16_components";

const phases = [
    { step_key: "welcome", label: "Welcome", state: "completed" },
    { step_key: "credential", label: "Credential", state: "pending" },
    { step_key: "scopes", label: "Scopes", state: "pending" },
    { step_key: "directions", label: "Directions", state: "pending" },
    { step_key: "location_mapping", label: "Locations", state: "pending" },
    { step_key: "source_of_truth", label: "Authority", state: "pending" },
    { step_key: "notification", label: "Notifications", state: "pending" },
    { step_key: "first_push", label: "First push", state: "pending" },
    { step_key: "test_connection", label: "Test", state: "pending" },
    { step_key: "final_readiness", label: "Readiness", state: "pending" },
    { step_key: "review", label: "Review", state: "pending" },
];

function storeItem(id, name, domain, activation = "active", connection = "connected") {
    return {
        store: { id, name, shop_domain: domain, connection, activation },
        attention_count: 1,
        workflows: [{ readiness: "ready" }, { readiness: "disabled" }],
        setup_continuation: { step_key: "credential" },
        allowed_actions: [{ key: "open_setup", label: "Resume setup" }],
    };
}

describe("P16 administrator component mounts", () => {
    test("renders multiple isolated stores and bounded actions", async () => {
        await mountWithCleanup(P16StoreList, {
            props: {
                state: "success",
                envelope: { data: { stores: [
                    storeItem(7, "Aurora", "aurora.myshopify.com"),
                    storeItem(8, "Borealis", "borealis.myshopify.com"),
                ], capacity: { maximum: 10 } } },
                canAddStore: true,
                selectedStoreId: 8,
            },
        });
        expect(queryAll(".sc-p16-store-card")).toHaveLength(2);
        expect(queryText(".sc-p16-store-list__meta")).toInclude("2 permitted store(s)");
        expect(queryText(".sc-p16-store-list__meta")).toInclude("10");
        expect(queryText(".sc-p16-store-card--selected")).toInclude("Borealis");
    });

    test("renders an empty list as a closed panel", async () => {
        await mountWithCleanup(P16StoreList, {
            props: { state: "empty", envelope: { data: { stores: [] } }, canAddStore: true },
        });
        expect(queryText(".sc-p16-state__title")).toInclude("No stores yet");
    });

    test("distinguishes activation from connection on store cards", async () => {
        await mountWithCleanup(P16StoreList, {
            props: {
                state: "success",
                envelope: { data: { stores: [
                    storeItem(7, "Paused", "paused.myshopify.com", "paused", "connected"),
                    storeItem(8, "Retired", "retired.myshopify.com", "retired", "disconnected"),
                ] } },
                canAddStore: false,
            },
        });
        const cards = queryAll(".sc-p16-store-card");
        expect(cards[0].textContent).toInclude("Paused · Connected");
        expect(cards[1].textContent).toInclude("Retired · Disconnected");
    });

    test("renders a loading list as a closed panel", async () => {
        await mountWithCleanup(P16StoreList, {
            props: { state: "loading", envelope: null, canAddStore: false },
        });
        expect(queryText(".sc-p16-state__title")).toInclude("Loading stores");
    });

    test("renders a terminal list error as a closed panel", async () => {
        await mountWithCleanup(P16StoreList, {
            props: { state: "terminal_error", errorMessage: "Try again", envelope: null },
        });
        expect(queryText(".sc-p16-state__title")).toInclude("Could not load this view");
        expect(queryFirst("button")).toBeTruthy();
    });

    test("shows all six setup phases and semantic step selection", async () => {
        await mountWithCleanup(P16PhaseRail, {
            props: { setup: { resume_step_key: "credential", steps: phases } },
        });
        expect(queryAll(".sc-p16-phase")).toHaveLength(6);
        expect(queryAll(".sc-p16-phase__number").map((node) => node.textContent.trim())).toEqual([
            "1", "2", "3", "4", "5", "6",
        ]);
        expect(queryText(".sc-p16-step--current")).toInclude("Credential");
    });

    test("makes stale readiness visible and keeps activation gated", async () => {
        await mountWithCleanup(P16ReadinessPanel, {
            props: {
                readiness: {
                    stale: true,
                    overall_result: "pass",
                    allowed_actions: [
                        { key: "test_connection" },
                        { key: "refresh_readiness" },
                        { key: "activate_store" },
                    ],
                    checks: [{ code: "credential", owner: "core", result: "pass", reason: "Old evidence" }],
                },
            },
        });
        expect(queryFirst(".alert-warning")).toBeTruthy();
        expect(queryText(".sc-p16-result")).toInclude("Passed");
        expect(queryFirst("button.btn-primary").disabled).toBe(true);
    });

    test("renders protected settings as output rather than controls", async () => {
        await mountWithCleanup(P16SettingsGroups, {
            props: {
                settings: { configuration_generation: 3, groups: [{
                    key: "workflow",
                    label: "Workflow posture",
                    allowed_actions: [{ key: "open_store_settings" }],
                    fields: [
                        { key: "product_domain_enabled", value_type: "boolean", value: true },
                        { key: "notification_default_enabled", value_type: "boolean", value: false },
                        { key: "fulfillment_operating_mode", value_type: "selection", value: "hybrid" },
                    ],
                }] },
                drafts: {},
            },
        });
        expect(queryAll(".sc-p16-setting-field__readonly")).toHaveLength(2);
        expect(queryAll("input[type='checkbox']")).toHaveLength(1);
        expect(queryAll("select")).toHaveLength(0);
    });

    test("clears write-only credential inputs after the callback settles", async () => {
        const seen = [];
        const component = await mountWithCleanup(P16CredentialPanel, {
            props: {
                store: { credentials: { present: true } },
                onReplace: async (payload) => seen.push(payload),
            },
        });
        const token = queryFirst(".sc-p16-credential input[type='password']");
        token.value = "shpat_HOOT_DUMMY";
        await component.submit();
        expect(seen).toHaveLength(1);
        expect(seen[0].access_token).toBe("shpat_HOOT_DUMMY");
        expect(token.value).toBe("");
        expect(queryText(".sc-p16-credential")).not.toInclude("shpat_HOOT_DUMMY");
    });
});
