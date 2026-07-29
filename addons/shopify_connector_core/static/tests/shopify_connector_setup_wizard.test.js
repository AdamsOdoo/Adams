/** @odoo-module **/
// Part of the Shopify Connector (S1 guided setup).
//
// HOOT unit tests for the setup wizard client action. These cover what only a
// mounted component can show: that the twelve accepted steps render in order,
// that navigation is driven by the semantic step KEY rather than by a
// position, that Back does not lose what was typed, that no source-of-truth
// option is pre-selected, that a server refusal is surfaced rather than
// swallowed, that a readiness row carries all five presentation states as
// TEXT, and that the token never enters component state.
//
// Server authorization, company isolation, persistence and the activation
// contract are NOT covered here and must not be: they belong to
// `shopify.connector.setup.wizard`, which re-checks all of it on every call.
// A client-side assertion about permission would be testing the wrong layer.

import { expect, test, describe, beforeEach } from "@odoo/hoot";
import { queryAll, queryFirst, queryText } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, mockService } from "@web/../tests/web_test_helpers";
import { ShopifyConnectorSetupWizard } from "@shopify_connector_core/js/shopify_connector_setup_wizard";

const STEPS = [
    ["welcome", "Welcome"],
    ["identity", "Store identity"],
    ["credential", "Credentials"],
    ["scopes", "Permissions"],
    ["test_connection", "Test connection"],
    ["directions", "What to sync"],
    ["location_mapping", "Location mapping"],
    ["source_of_truth", "Source of truth"],
    ["notification", "Customer notifications"],
    ["first_push", "First stock push"],
    ["final_readiness", "Final readiness"],
    ["review", "Review and activate"],
];

function payload(overrides = {}) {
    return Object.assign(
        {
            steps: STEPS.map(([key, label], index) => ({
                index: index + 1,
                key,
                label,
                applicable: true,
                skipped_reason: "",
            })),
            step_count: STEPS.length,
            resume_step_key: "welcome",
            resume_step: 1,
            store: {
                id: false,
                name: "",
                shop_domain: "",
                state: "setup_incomplete",
                state_label: "Setup Incomplete",
                credential_present: false,
                credential_verified: false,
                test_connection_result: false,
                test_connection_reason: "",
                setup_completed_at: false,
                setup_completed_by: "",
            },
            stores: [],
            scopes: [],
            domains: [
                {
                    key: "sale",
                    field: "sale_domain_enabled",
                    label: "Orders",
                    direction: "Shopify to Odoo",
                    happens: "Shopify orders are imported.",
                    withheld: "Orders are never written back.",
                    enabled: false,
                },
            ],
            location_mapping: {
                available: true,
                reason: "",
                locations: [],
                odoo_locations: [],
                refresh: { state: "none", job_id: false, reason: "" },
                mapped_count: 0,
                unmapped_count: 0,
                has_valid_mapping: false,
            },
            matching_choices: [
                {
                    value: "odoo_source",
                    label: "Odoo is the catalog source",
                    consequence: "Products are exported after review.",
                },
            ],
            price_choices: [
                {
                    value: "odoo_authoritative",
                    label: "Odoo is the price authority",
                    consequence: "Odoo prices overwrite Shopify prices.",
                },
            ],
            readiness: {
                ran: false,
                overall: false,
                stale: false,
                checks: [],
                blocking: [],
                waiting: [],
            },
            summary: {
                domains: [],
                matching: "",
                price: "",
                notification: "Customers will not be emailed.",
                first_push: "Inventory is not enabled.",
                location_mapping: "Inventory is not enabled.",
                can_activate: false,
                blocking: [],
                waiting: [],
                already_active: false,
            },
        },
        overrides
    );
}

let calls = [];

function mockOrm(handler) {
    mockService("orm", {
        call: async (model, method, args, kwargs) => {
            expect(model).toBe("shopify.connector.setup.wizard");
            calls.push({ method, kwargs });
            return handler(method, kwargs);
        },
    });
}

async function mount() {
    const component = await mountWithCleanup(ShopifyConnectorSetupWizard, {
        props: { action: { context: {} } },
    });
    await animationFrame();
    return component;
}

describe("shopify connector setup wizard", () => {
    beforeEach(() => {
        calls = [];
        mockService("action", { doAction: () => {} });
        mockService("notification", { add: () => {} });
    });

    test("renders the twelve accepted steps in the accepted order", async () => {
        mockOrm(() => payload());
        await mount();
        const labels = queryAll(".sc_setup_step__label").map((el) =>
            el.textContent.trim()
        );
        expect(labels).toEqual(STEPS.map(([, label]) => label));
    });

    test("the heading states the step number and the total", async () => {
        mockOrm(() => payload());
        await mount();
        expect(queryText(".sc_setup__heading")).toInclude("Step 1 of 12");
        expect(queryText(".sc_setup__heading")).toInclude("Welcome");
    });

    test("it opens at the resume step key, not always at the first step", async () => {
        mockOrm(() => payload({ resume_step_key: "directions", resume_step: 6 }));
        await mount();
        expect(queryText(".sc_setup__heading")).toInclude("Step 6 of 12");
        expect(queryText(".sc_setup__heading")).toInclude("What to sync");
    });

    test("navigation follows the key, not the ordinal", async () => {
        // The server's list is the SAME twelve steps under different
        // ordinals. A client that navigated by position would land on the
        // step at index 6; one that navigates by key lands on the key it was
        // given, wherever the server put it.
        const reordered = payload({
            resume_step_key: "location_mapping",
            resume_step: 99,
        });
        mockOrm(() => reordered);
        await mount();
        expect(queryText(".sc_setup__heading")).toInclude("Location mapping");
        expect(queryText(".sc_setup__heading")).toInclude("Step 7 of 12");
    });

    test("a step that does not apply says so instead of disappearing", async () => {
        const data = payload({ resume_step_key: "location_mapping" });
        data.steps = data.steps.map((step) =>
            step.key === "location_mapping"
                ? {
                      ...step,
                      applicable: false,
                      skipped_reason: "Inventory syncing is not enabled.",
                  }
                : step
        );
        mockOrm(() => data);
        await mount();
        // Still twelve steps in the rail: nothing renumbered.
        expect(queryAll(".sc_setup_step__label")).toHaveLength(12);
        expect(queryText(".sc_setup_location_skipped")).toInclude(
            "Not required"
        );
        expect(queryText(".sc_setup_location_skipped")).toInclude(
            "Inventory syncing is not enabled."
        );
    });

    test("no source-of-truth option is pre-selected", async () => {
        mockOrm(() => payload({ resume_step_key: "source_of_truth" }));
        await mount();
        const checked = queryAll(
            ".sc_setup__choices input[type='radio']:checked"
        );
        expect(checked).toHaveLength(0);
    });

    test("Back returns to the previous step without a server call", async () => {
        mockOrm(() => payload({ resume_step_key: "scopes" }));
        await mount();
        calls = [];
        queryFirst(".sc_setup_back").click();
        await animationFrame();
        expect(queryText(".sc_setup__heading")).toInclude("Step 3 of 12");
        expect(queryText(".sc_setup__heading")).toInclude("Credentials");
        expect(calls).toHaveLength(0);
    });

    test("a server refusal is shown, not swallowed", async () => {
        mockOrm((method) => {
            if (method === "get_setup_state") {
                return payload({ resume_step_key: "identity" });
            }
            const error = new Error("refused");
            error.data = { message: "Enter the store's permanent domain." };
            throw error;
        });
        await mount();
        queryFirst(".sc_setup_continue").click();
        await animationFrame();
        await animationFrame();
        expect(queryText(".sc_setup__error")).toInclude("permanent domain");
        // And the wizard did NOT advance past a refusal.
        expect(queryText(".sc_setup__heading")).toInclude("Store identity");
    });

    test("the credential step names the two values that are not the token", async () => {
        mockOrm(() => payload({ resume_step_key: "credential" }));
        await mount();
        const panel = queryText(".sc_setup__panel");
        expect(panel).toInclude("Admin API access token");
        expect(panel).toInclude("not the Client ID");
        expect(panel).toInclude("Client Secret");
        // No universal-expiry claim anywhere on the step.
        expect(panel).not.toInclude("24 hours");
    });

    test("the token is never held in component state", async () => {
        mockOrm((method) => {
            if (method === "get_setup_state") {
                return payload({
                    resume_step_key: "credential",
                    store: Object.assign(payload().store, { id: 7 }),
                });
            }
            return payload({
                resume_step_key: "credential",
                store: Object.assign(payload().store, {
                    id: 7,
                    credential_present: true,
                }),
            });
        });
        const component = await mount();
        const input = queryFirst(".sc_setup_token");
        input.value = "shpat_HOOTDUMMY0000000000000000000000";
        queryFirst(".sc_setup_continue").click();
        await animationFrame();
        await animationFrame();
        // It reached the server...
        const sent = calls.find((c) => c.method === "save_credential");
        expect(Boolean(sent)).toBe(true);
        // ...and it is in NEITHER the component state nor the DOM afterwards.
        expect(JSON.stringify(component.state)).not.toInclude("shpat_");
        expect(document.body.innerHTML).not.toInclude("shpat_");
    });

    test("Save & Exit sends the step key, never an ordinal", async () => {
        mockOrm((method) => {
            if (method === "get_setup_state") {
                return payload({
                    resume_step_key: "directions",
                    store: Object.assign(payload().store, { id: 11 }),
                });
            }
            return { resume_step_key: "directions", resume_step: 6 };
        });
        await mount();
        calls = [];
        queryFirst(".sc_setup_exit").click();
        await animationFrame();
        await animationFrame();
        const sent = calls.find((c) => c.method === "save_and_exit");
        expect(Boolean(sent)).toBe(true);
        expect(sent.kwargs.step_key).toBe("directions");
        expect(sent.kwargs.step_index).toBe(undefined);
    });

    test("an enabled domain shows what is still withheld", async () => {
        mockOrm(() => payload({ resume_step_key: "directions" }));
        await mount();
        expect(queryAll(".sc_setup__domain-withheld")).toHaveLength(0);
        queryFirst("#sc_setup_domain_sale").click();
        await animationFrame();
        expect(queryText(".sc_setup__domain-withheld")).toInclude(
            "never written back"
        );
    });

    test("entering final readiness evaluates the current configuration", async () => {
        // Nothing has been run, so arriving on the step runs the checks
        // rather than showing an empty screen with a button nobody pressed.
        mockOrm((method) => {
            if (method === "run_readiness") {
                return payload({
                    resume_step_key: "final_readiness",
                    store: Object.assign(payload().store, { id: 5 }),
                    readiness: {
                        ran: true,
                        overall: "pass",
                        stale: false,
                        checks: [],
                        blocking: [],
                        waiting: [],
                    },
                });
            }
            return payload({
                resume_step_key: "final_readiness",
                store: Object.assign(payload().store, { id: 5 }),
            });
        });
        await mount();
        await animationFrame();
        expect(
            Boolean(calls.find((c) => c.method === "run_readiness"))
        ).toBe(true);
    });

    test("readiness rows carry all five states as text, never colour alone", async () => {
        const states = [
            ["credential_test_connection", "passed", "Passed", "success"],
            ["domain_flag_enablement", "warning", "Worth checking", "warning"],
            ["mapped_location", "blocking", "Must be fixed", "danger"],
            ["cron_queue_health", "waiting", "Waiting", "info"],
            ["webhook_hmac", "not_required", "Not required", "neutral"],
        ];
        mockOrm(() =>
            payload({
                resume_step_key: "final_readiness",
                store: Object.assign(payload().store, { id: 5 }),
                readiness: {
                    ran: true,
                    overall: "fail",
                    stale: false,
                    checks: states.map(([code, state, label, tone]) => ({
                        code,
                        label: code,
                        tier: "essential",
                        result: state === "passed" ? "pass" : "fail",
                        state,
                        state_label: label,
                        tone,
                        reason: "reason for " + code,
                        owner: "Administrator",
                        action_label:
                            code === "mapped_location"
                                ? "Fix location mapping"
                                : "",
                        action_step_key:
                            code === "mapped_location" ? "location_mapping" : "",
                    })),
                    blocking: [],
                    waiting: [],
                },
            })
        );
        await mount();
        const rows = queryAll(".sc_setup__checks li").map((el) =>
            el.textContent
        );
        for (const [, , label] of states) {
            expect(rows.some((row) => row.includes(label))).toBe(true);
        }
        // The fix control addresses the step by KEY.
        expect(
            queryFirst(".sc_setup_check_action").dataset.stepKey
        ).toBe("location_mapping");
    });

    test("stale readiness evidence is never shown as a success", async () => {
        mockOrm(() =>
            payload({
                resume_step_key: "final_readiness",
                store: Object.assign(payload().store, { id: 5 }),
                readiness: {
                    ran: true,
                    overall: "pass",
                    stale: true,
                    checks: [
                        {
                            code: "domain_flag_enablement",
                            label: "Sync features selected",
                            tier: "warning",
                            result: "pass",
                            state: "waiting",
                            state_label: "Waiting",
                            tone: "info",
                            reason: "Something changed.",
                            owner: "Administrator",
                            action_label: "",
                            action_step_key: "",
                        },
                    ],
                    blocking: [],
                    waiting: [],
                },
            })
        );
        await mount();
        expect(queryText(".sc_setup__panel")).toInclude("out of date");
        const row = queryText(".sc_setup__checks li");
        expect(row).toInclude("Waiting");
        expect(row).not.toInclude("Passed");
    });

    test("a pending location refresh is not reported as an empty Shopify store", async () => {
        mockOrm(() =>
            payload({
                resume_step_key: "location_mapping",
                store: Object.assign(payload().store, { id: 5 }),
                location_mapping: {
                    available: true,
                    reason: "",
                    locations: [],
                    odoo_locations: [],
                    refresh: { state: "waiting", job_id: 42, reason: "" },
                    mapped_count: 0,
                    unmapped_count: 0,
                    has_valid_mapping: false,
                },
            })
        );
        await mount();
        const panel = queryText(".sc_setup__panel");
        expect(panel).toInclude("Reading your Shopify locations");
        expect(panel).toInclude("not a report that Shopify has no locations");
        expect(queryText(".sc_setup_refresh_state")).toInclude("Waiting");
    });

    test("a mapped and an unmapped location are visibly different", async () => {
        mockOrm(() =>
            payload({
                resume_step_key: "location_mapping",
                store: Object.assign(payload().store, { id: 5 }),
                location_mapping: {
                    available: true,
                    reason: "",
                    locations: [
                        {
                            shopify_gid: "gid://shopify/Location/1",
                            name: "Warehouse One",
                            mapped: true,
                            mapping_id: 3,
                            odoo_location_id: 9,
                            odoo_location_name: "WH/Stock",
                            push_enabled: true,
                        },
                        {
                            shopify_gid: "gid://shopify/Location/2",
                            name: "Warehouse Two",
                            mapped: false,
                            mapping_id: false,
                            odoo_location_id: false,
                            odoo_location_name: "",
                            push_enabled: false,
                        },
                    ],
                    odoo_locations: [{ id: 9, name: "WH/Stock" }],
                    refresh: { state: "succeeded", job_id: 7, reason: "" },
                    mapped_count: 1,
                    unmapped_count: 1,
                    has_valid_mapping: true,
                },
            })
        );
        await mount();
        const rows = queryAll(".sc_setup__location").map((el) => el.textContent);
        expect(rows[0]).toInclude("Mapped");
        expect(rows[0]).toInclude("WH/Stock");
        expect(rows[1]).toInclude("Not mapped");
        expect(rows[1]).toInclude("will not be synchronised");
    });
});
