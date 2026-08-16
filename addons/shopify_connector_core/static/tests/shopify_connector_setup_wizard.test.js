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
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { mountWithCleanup, mockService } from "@web/../tests/web_test_helpers";
import { ShopifyConnectorSetupWizard } from "@shopify_connector_core/js/shopify_connector_setup_wizard";

const STEPS = [
    ["welcome", "Welcome", "connect", "Connect", 1],
    ["identity", "Store identity", "connect", "Connect", 1],
    ["credential", "Credentials", "connect", "Connect", 1],
    ["scopes", "Permissions", "connect", "Connect", 1],
    ["test_connection", "Test connection", "connect", "Connect", 1],
    ["directions", "What to sync", "choose", "Choose", 2],
    ["location_mapping", "Location mapping", "map", "Map", 3],
    ["source_of_truth", "Source of truth", "protect", "Protect", 4],
    ["notification", "Customer notifications", "protect", "Protect", 4],
    ["first_push", "First stock push", "protect", "Protect", 4],
    ["final_readiness", "Final readiness", "verify", "Verify", 5],
    ["review", "Review and activate", "verify", "Verify", 5],
];

const PHASES = [
    ["connect", "Connect"],
    ["choose", "Choose"],
    ["map", "Map"],
    ["protect", "Protect"],
    ["verify", "Verify"],
];

function payload(overrides = {}) {
    return Object.assign(
        {
            steps: STEPS.map(([key, label, phaseKey, phaseLabel, phaseIndex], index) => ({
                index: index + 1,
                key,
                label,
                phase_key: phaseKey,
                phase_label: phaseLabel,
                phase_index: phaseIndex,
                applicable: true,
                skipped_reason: "",
            })),
            step_count: STEPS.length,
            phases: PHASES.map(([key, label], index) => ({
                index: index + 1,
                key,
                label,
                step_keys: STEPS.filter((step) => step[2] === key).map((step) => step[0]),
            })),
            phase_count: PHASES.length,
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
                auth_mode: "offline_access_token",
                client_credentials_present: false,
                token_expires_at: false,
                token_last_failure_reason: "",
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
                mapping_complete: false,
                shopify_total: 0,
                odoo_total: 0,
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

    test("groups the unchanged twelve steps into the five merchant phases", async () => {
        mockOrm(() => payload());
        await mount();
        const phases = queryAll(".sc_setup_phase__label").map((el) =>
            el.textContent.trim()
        );
        expect(phases).toEqual(PHASES.map(([, label]) => label));
        expect(queryAll(".sc_setup_phase")).toHaveLength(5);
        expect(queryAll(".sc_setup_step")).toHaveLength(12);
        expect(queryText(".sc_setup__heading")).toInclude("Phase 1 of 5");
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

    test("the credential step opens on the Dev Dashboard path by default", async () => {
        mockOrm(() => payload({ resume_step_key: "credential" }));
        await mount();
        const panel = queryText(".sc_setup__panel");
        // The current Shopify path: same-organization requirement and the
        // automatic 24-hour renewal are stated; a "token shown once" claim --
        // the OLD path's copy -- must not be shown to a Dev Dashboard user.
        expect(panel).toInclude("same Shopify organization");
        expect(panel).toInclude("24 hours");
        expect(panel).not.toInclude("shown once");
        expect(Boolean(queryFirst(".sc_setup_client_id"))).toBe(true);
        expect(
            queryFirst(".sc_setup_client_secret").getAttribute("type")
        ).toBe("password");
        // The offline token field belongs to the OTHER path and is absent.
        expect(queryFirst(".sc_setup_token")).toBe(null);
    });

    test("the offline path names the two values that are not the token", async () => {
        mockOrm(() => payload({ resume_step_key: "credential" }));
        await mount();
        queryFirst(".sc_setup__mode input[value='offline_access_token']").click();
        await animationFrame();
        const panel = queryText(".sc_setup__panel");
        expect(panel).toInclude("Admin API access token");
        expect(panel).toInclude("not the Client ID");
        expect(panel).toInclude("Client Secret");
        // No universal-expiry claim on the offline path: how long an existing
        // token lives depends on how it was issued.
        expect(panel).not.toInclude("24 hours");
        // And the client-credential inputs belong to the other path.
        expect(queryFirst(".sc_setup_client_secret")).toBe(null);
    });

    test("a stored mode reopens the step on the merchant's actual path", async () => {
        mockOrm(() =>
            payload({
                resume_step_key: "credential",
                store: Object.assign(payload().store, {
                    id: 9,
                    credential_present: true,
                    auth_mode: "offline_access_token",
                }),
            })
        );
        await mount();
        expect(queryText(".sc_setup__mode--selected")).toInclude(
            "Existing Admin API access token"
        );
        expect(Boolean(queryFirst(".sc_setup_token"))).toBe(true);
    });

    test("the client secret is never held in component state", async () => {
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
                    auth_mode: "dev_dashboard_client_credentials",
                    client_credentials_present: true,
                }),
            });
        });
        const component = await mount();
        queryFirst(".sc_setup_client_id").value = "hoot-client-id";
        queryFirst(".sc_setup_client_secret").value =
            "hoot-secret-LEAKCANARY-000";
        queryFirst(".sc_setup_continue").click();
        await animationFrame();
        await animationFrame();
        const sent = calls.find((c) => c.method === "save_client_credentials");
        expect(Boolean(sent)).toBe(true);
        expect(sent.kwargs.client_id).toBe("hoot-client-id");

        // --- Batch 1 correction: this guard used to be able to pass while
        //     leaking. `document.body.innerHTML` cannot contain a value set
        //     through the `.value` PROPERTY at all -- the attribute is
        //     untouched -- so that assertion was vacuous for the very
        //     mechanism the test names. And `component.state` is one object;
        //     a secret parked on any other component property, in any other
        //     RPC payload, or in a DOM attribute went unnoticed.
        //
        //     ANTI-VACUITY FIRST. If the secret never reached the request, every
        //     "not present" assertion below would pass for the wrong reason.
        expect(sent.kwargs.client_secret).toBe("hoot-secret-LEAKCANARY-000");

        // 1. No OTHER request carries it.
        for (const call of calls) {
            if (call === sent) {
                continue;
            }
            expect(JSON.stringify(call)).not.toInclude("LEAKCANARY");
        }

        // 2. Nowhere on the component -- every own property, not just `state`.
        const seen = new Set();
        const walk = (value, depth) => {
            if (depth > 6 || value === null || value === undefined) {
                return false;
            }
            if (typeof value === "string") {
                return value.includes("LEAKCANARY");
            }
            if (typeof value !== "object") {
                return false;
            }
            if (seen.has(value)) {
                return false;
            }
            seen.add(value);
            return Object.values(value).some((v) => walk(v, depth + 1));
        };
        expect(walk(component, 0)).toBe(false);

        // 3. Nowhere in the DOM -- markup, every attribute, and every input's
        //    live value property, which is the one `innerHTML` cannot see.
        expect(document.body.innerHTML).not.toInclude("LEAKCANARY");
        for (const el of queryAll("*")) {
            for (const attr of el.attributes) {
                expect(attr.value).not.toInclude("LEAKCANARY");
            }
            if ("value" in el && typeof el.value === "string") {
                expect(el.value).not.toInclude("LEAKCANARY");
            }
        }

        // 4. Not in anything the component surfaced to the operator.
        expect(queryText(".sc_setup__panel")).not.toInclude("LEAKCANARY");
        expect(String(component.state.errorMessage || "")).not.toInclude(
            "LEAKCANARY"
        );

        // The client id is not a secret, but it is not retained either.
        expect(JSON.stringify(component.state)).not.toInclude("hoot-client-id");
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
        queryFirst(".sc_setup__mode input[value='offline_access_token']").click();
        await animationFrame();
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
                    mapping_complete: false,
                    shopify_total: 0,
                    odoo_total: 0,
                },
            })
        );
        await mount();
        const panel = queryText(".sc_setup__panel");
        expect(panel).toInclude("Reading your Shopify locations");
        expect(panel).toInclude("not a report that Shopify has no locations");
        expect(queryText(".sc_setup_refresh_state")).toInclude("Waiting");
    });

    test("entering the required location step starts discovery automatically", async () => {
        const initial = payload({
            resume_step_key: "location_mapping",
            store: Object.assign(payload().store, { id: 5 }),
            location_mapping: Object.assign({}, payload().location_mapping, {
                refresh: { state: "none", job_id: false, reason: "" },
            }),
        });
        const loaded = payload({
            resume_step_key: "location_mapping",
            store: Object.assign(payload().store, { id: 5 }),
            location_mapping: Object.assign({}, payload().location_mapping, {
                refresh: { state: "succeeded", job_id: false, reason: "" },
            }),
        });
        mockOrm((method) =>
            method === "refresh_shopify_locations" ? loaded : initial
        );

        await mount();

        expect(
            calls.some((call) => call.method === "refresh_shopify_locations")
        ).toBe(true);
    });

    test("Continue stays disabled until every active location is mapped", async () => {
        mockOrm(() => payload({
            resume_step_key: "location_mapping",
            store: Object.assign(payload().store, { id: 5 }),
            location_mapping: Object.assign({}, payload().location_mapping, {
                refresh: { state: "succeeded", job_id: false, reason: "" },
                shopify_total: 2,
                unmapped_count: 1,
                mapping_complete: false,
            }),
        }));
        await mount();
        expect(queryFirst(".sc_setup_continue").disabled).toBe(true);
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
                    has_valid_mapping: false,
                    mapping_complete: false,
                    shopify_total: 2,
                    odoo_total: 1,
                },
            })
        );
        await mount();
        const rows = queryAll(".sc_setup__location").map((el) => el.textContent);
        expect(rows[0]).toInclude("Mapped");
        expect(rows[0]).toInclude("WH/Stock");
        expect(rows[1]).toInclude("Not mapped");
        expect(rows[1]).toInclude("Choose the Odoo location");
    });

    // ======================================================================
    // The location step's bounded search, driven through the MOUNTED
    // component and the real RPC boundary.
    //
    // WHY THIS SECTION EXISTS. The Batch 1 correction rebuilt this client:
    // server-issued continuation instead of a client-derived offset, the
    // `state.busy` discipline the search had bypassed, per-identity
    // deduplication, revalidation of a selection the operator can no longer
    // see, an in-place row update after a mapping, and four distinguishable
    // empty states. All of it was proved on the SERVER and by a tour that
    // walks one happy path. Neither can see any of the properties above:
    // a tour cannot hold a response open, cannot inspect what was sent, and
    // cannot distinguish "the client asked for the right page" from "the
    // client asked for the wrong page and the fixture made it look the same".
    //
    // The fake server below enforces the REAL contract rather than answering
    // whatever it is asked. It refuses a continuation that does not belong to
    // the (side, query) being paged, exactly as `search_location_options`
    // does, and it issues a `next_offset` that is deliberately NOT the number
    // of rows the client is holding -- so a client that derives its position
    // from its own array length asks for the wrong rows and the assertion
    // fails, rather than passing because the two numbers happened to agree.
    // ======================================================================

    /** One Shopify row, in the shape `_setup_search_locations` returns. */
    function shopifyRow(index, overrides = {}) {
        return Object.assign(
            {
                shopify_gid: `gid://shopify/Location/${index}`,
                name: `Warehouse ${index}`,
                mapped: false,
                mapping_id: false,
                odoo_location_id: false,
                odoo_location_name: "",
                push_enabled: false,
            },
            overrides
        );
    }

    /** One Odoo row, in the same shape. */
    function odooRow(index, overrides = {}) {
        return Object.assign({ id: index, name: `WH${index}/Stock` }, overrides);
    }

    /**
     * A server that behaves like `search_location_options`, not like a stub.
     *
     * `nextOffsetFor` is the whole point of the fixture: the position the
     * server hands back is a number only the server knows, and here it is
     * chosen so that it can never coincide with the length of the client's
     * accumulated array. Deriving the offset locally is then observable
     * rather than merely disapproved of.
     */
    function makeLocationServer({
        shopify = [],
        odoo = [],
        pageSize = 2,
        nextOffsetFor = null,
        emptyReasonFor = null,
    } = {}) {
        const server = {
            pageSize,
            pending: null,
            hold: false,
            searchCalls: [],
            token: (side, query) => `continuation:${side}:${query}`,
            rowsFor(side, query) {
                const all = side === "shopify" ? shopify : odoo;
                if (!query) {
                    return all;
                }
                return all.filter((row) =>
                    row.name.toLowerCase().includes(query.toLowerCase())
                );
            },
            /** The server's own validation, reproduced rather than assumed. */
            page(kwargs) {
                const { side, query = "", offset = 0, continuation = null } =
                    kwargs;
                if (!Number.isInteger(offset) || offset < 0) {
                    throw new Error("The location list position is not valid.");
                }
                if (offset && continuation !== server.token(side, query)) {
                    throw new Error(
                        "The location list moved on while you were reading it. " +
                            "Search again to start from the first page."
                    );
                }
                const rows = server.rowsFor(side, query);
                // The offsets the server issues are its own; the fixture maps
                // them back to real slices so a wrong offset returns wrong
                // rows instead of throwing.
                const start = server.sliceStart(side, query, offset);
                const items = rows.slice(start, start + pageSize);
                const consumed = start + items.length;
                const exhausted = consumed >= rows.length;
                return {
                    items,
                    total: rows.length,
                    offset,
                    next_offset: exhausted
                        ? false
                        : nextOffsetFor
                          ? nextOffsetFor(consumed)
                          : consumed,
                    continuation: server.token(side, query),
                    empty_reason: rows.length
                        ? ""
                        : emptyReasonFor
                          ? emptyReasonFor(side, query)
                          : query
                            ? "no_results"
                            : side === "shopify"
                              ? "no_cached_locations"
                              : "no_eligible_odoo_locations",
                };
            },
            sliceStart(side, query, offset) {
                if (!offset || !nextOffsetFor) {
                    return offset;
                }
                // Undo the deliberate skew so the fixture still serves the
                // NEXT rows when the client echoes the server's number back.
                const rows = server.rowsFor(side, query);
                for (let real = 0; real <= rows.length; real++) {
                    if (nextOffsetFor(real) === offset) {
                        return real;
                    }
                }
                throw new Error(
                    "The location list position is out of range: " + offset
                );
            },
        };
        return server;
    }

    /** Mount the wizard on its location step against `server`. */
    async function mountLocationStep(server, options = {}) {
        const { storeId = 5, locationMapping = {}, onSaveMapping = null } =
            options;
        const state = payload({
            resume_step_key: "location_mapping",
            store: Object.assign(payload().store, {
                id: storeId,
                state: "connected",
            }),
            location_mapping: Object.assign(
                {
                    available: true,
                    reason: "",
                    locations: [],
                    odoo_locations: [],
                    refresh: { state: "succeeded", job_id: 7, reason: "" },
                    mapped_count: 0,
                    unmapped_count: 0,
                    has_valid_mapping: false,
                    mapping_complete: false,
                    shopify_total: 0,
                    odoo_total: 0,
                },
                locationMapping
            ),
        });
        mockService("orm", {
            call: async (model, method, args, kwargs) => {
                expect(model).toBe("shopify.connector.setup.wizard");
                calls.push({ method, kwargs });
                if (method === "search_location_options") {
                    server.searchCalls.push(kwargs);
                    if (server.hold) {
                        const deferred = new Deferred();
                        server.pending = { kwargs, deferred };
                        return deferred;
                    }
                    return server.page(kwargs);
                }
                if (method === "save_location_mapping") {
                    return onSaveMapping ? onSaveMapping(kwargs) : state;
                }
                return state;
            },
        });
        return await mount();
    }

    /** Resolve the held response with the page the server would have sent. */
    async function releaseSearch(server) {
        const { kwargs, deferred } = server.pending;
        server.pending = null;
        try {
            deferred.resolve(server.page(kwargs));
        } catch (error) {
            deferred.reject(error);
        }
        await animationFrame();
    }

    const gidsOnScreen = () =>
        queryAll(".sc_setup__location").map((el) =>
            el.getAttribute("data-shopify-gid")
        );

    test("the location search obeys the same busy discipline as every other call", async () => {
        // Search was the ONE call that bypassed `state.busy`, which is why the
        // `disabled` bindings on Search and Load more were inert: nothing ever
        // set the flag they read. Held open, the flag and the controls it
        // drives are both observable.
        const server = makeLocationServer({
            shopify: [shopifyRow(1), shopifyRow(2), shopifyRow(3)],
            odoo: [odooRow(9)],
        });
        const component = await mountLocationStep(server, {
            locationMapping: {
                locations: [shopifyRow(1)],
                odoo_locations: [odooRow(9)],
                shopify_total: 11,
            },
        });
        component.setLocationMappingChoice(
            "gid://shopify/Location/1",
            "9"
        );
        await animationFrame();
        expect(queryFirst(".sc_setup_create_mapping").disabled).toBe(false);

        server.hold = true;
        const inFlight = component.searchLocations("shopify");
        await animationFrame();

        expect(component.state.busy).toBe(true);
        expect(queryFirst(".sc_setup_search_shopify_go").disabled).toBe(true);
        expect(queryFirst(".sc_setup_create_mapping").disabled).toBe(true);

        await releaseSearch(server);
        await inFlight;
        await animationFrame();
        expect(component.state.busy).toBe(false);
        expect(queryFirst(".sc_setup_search_shopify_go").disabled).toBe(false);
        expect(queryFirst(".sc_setup_create_mapping").disabled).toBe(false);
        expect(server.searchCalls).toHaveLength(1);
    });

    test("no second search, load-more, clear or mapping is admitted while one is in flight", async () => {
        // Every overlapping action, against ONE held response. Two searches in
        // flight at once meant the later-resolving one won regardless of which
        // query it answered; a clear during a search was overwritten by the
        // response that arrived after it; a Load more during a search paged
        // from a position that was about to change.
        const server = makeLocationServer({
            shopify: [shopifyRow(1), shopifyRow(2), shopifyRow(3), shopifyRow(4)],
            odoo: [odooRow(9)],
        });
        const component = await mountLocationStep(server, {
            locationMapping: {
                locations: [shopifyRow(1), shopifyRow(2)],
                odoo_locations: [odooRow(9)],
            },
        });
        component.state.form.mapShopifyGid = "gid://shopify/Location/1";
        component.state.form.mapOdooLocationId = "9";
        component.state.locationSearch.shopify.query = "warehouse";
        server.hold = true;
        const inFlight = component.searchLocations("shopify");
        await animationFrame();
        const held = server.pending.kwargs;

        // Four overlapping actions, none of which may reach the server or
        // move what is on screen while the first is unresolved.
        await component.searchLocations("shopify");
        await component.loadMoreLocations("shopify");
        component.clearLocationSearch("shopify");
        await component.createMapping();
        await animationFrame();

        expect(server.searchCalls).toHaveLength(1);
        expect(server.pending.kwargs).toBe(held);
        expect(
            calls.filter((c) => c.method === "save_location_mapping")
        ).toHaveLength(0);
        // The mapping was stopped by the busy discipline, not by an empty
        // form: both identities were chosen and still on screen.
        expect(component.state.errorMessage).toBe("");
        // The clear did not survive into the state the response then lands in.
        expect(component.state.locationSearch.shopify.query).toBe("warehouse");

        await releaseSearch(server);
        await inFlight;
        expect(gidsOnScreen()).toEqual([
            "gid://shopify/Location/1",
            "gid://shopify/Location/2",
        ]);
        expect(server.searchCalls).toHaveLength(1);
    });

    test("load more sends the server's own next_offset, never the length of the list on screen", async () => {
        // The server's position here is `real + 100`, so a client deriving it
        // from `items.length` sends 2 and this assertion fails. The fixture
        // maps the skewed number back to the real slice, so the ONLY way to
        // see rows 3 and 4 is to echo what the server sent.
        const server = makeLocationServer({
            shopify: [shopifyRow(1), shopifyRow(2), shopifyRow(3), shopifyRow(4)],
            odoo: [odooRow(9)],
            nextOffsetFor: (real) => real + 100,
        });
        const component = await mountLocationStep(server);

        await component.searchLocations("shopify");
        await animationFrame();
        expect(server.searchCalls[0].offset).toBe(0);
        expect(server.searchCalls[0].continuation).toBe(null);
        expect(component.state.locationSearch.shopify.nextOffset).toBe(102);
        expect(component.locationHasMore("shopify")).toBe(true);

        await component.loadMoreLocations("shopify");
        await animationFrame();
        expect(server.searchCalls[1].offset).toBe(102);
        expect(server.searchCalls[1].continuation).toBe(
            "continuation:shopify:"
        );
        expect(gidsOnScreen()).toEqual([
            "gid://shopify/Location/1",
            "gid://shopify/Location/2",
            "gid://shopify/Location/3",
            "gid://shopify/Location/4",
        ]);
        // The server said the set is exhausted, so Load more is gone and a
        // further request would restart at page 0 and duplicate everything.
        expect(component.state.locationSearch.shopify.nextOffset).toBe(false);
        expect(component.locationHasMore("shopify")).toBe(false);
        await component.loadMoreLocations("shopify");
        expect(server.searchCalls).toHaveLength(2);
    });

    test("a new query and a clear both invalidate the continuation the old set issued", async () => {
        // The fixture REFUSES a continuation that does not belong to the
        // (side, query) being paged, exactly as the server does. So a client
        // that kept the old token does not merely offend a rule here -- it
        // gets the refusal on screen, which is the assertion at the end.
        const server = makeLocationServer({
            shopify: [
                shopifyRow(1, { name: "North depot A" }),
                shopifyRow(2, { name: "North depot B" }),
                shopifyRow(3, { name: "North depot C" }),
                shopifyRow(4, { name: "South depot A" }),
                shopifyRow(5, { name: "South depot B" }),
                shopifyRow(6, { name: "South depot C" }),
            ],
            odoo: [odooRow(9)],
        });
        const component = await mountLocationStep(server);
        const search = component.state.locationSearch.shopify;

        search.query = "north";
        await component.searchLocations("shopify");
        await component.loadMoreLocations("shopify");
        await animationFrame();
        expect(server.searchCalls[1].continuation).toBe(
            "continuation:shopify:north"
        );

        // A new query is a new set: position 0, nothing carried over.
        search.query = "south";
        await component.searchLocations("shopify");
        await animationFrame();
        expect(server.searchCalls[2].offset).toBe(0);
        expect(server.searchCalls[2].query).toBe("south");
        expect(server.searchCalls[2].continuation).toBe(null);
        expect(search.continuation).toBe("continuation:shopify:south");

        // And the next page of the NEW set carries the new set's token.
        await component.loadMoreLocations("shopify");
        await animationFrame();
        expect(server.searchCalls[3].offset).toBe(2);
        expect(server.searchCalls[3].continuation).toBe(
            "continuation:shopify:south"
        );
        expect(component.state.errorMessage).toBe("");

        // Clearing drops the whole continuation, so the next search starts
        // over rather than resuming a set that is no longer displayed.
        // `clearLocationSearch` REPLACES the side's state object, so the
        // cleared state has to be read back rather than held from before.
        component.clearLocationSearch("shopify");
        const cleared = component.state.locationSearch.shopify;
        expect(cleared).not.toBe(search);
        expect(cleared.continuation).toBe(null);
        expect(cleared.nextOffset).toBe(false);
        expect(cleared.items).toBe(null);
        expect(cleared.query).toBe("");
        expect(cleared.emptyReason).toBe("");
        cleared.query = "north";
        await component.searchLocations("shopify");
        await animationFrame();
        expect(server.searchCalls[4].offset).toBe(0);
        expect(server.searchCalls[4].continuation).toBe(null);
        expect(component.state.errorMessage).toBe("");
    });

    test("pages accumulate and are deduplicated by identity, not by position", async () => {
        // A row inserted or removed between two page requests shifts every
        // row after it, so the same location can be served on two pages. The
        // list whose whole purpose is that every eligible location is
        // reachable must not show one twice.
        const rows = [shopifyRow(1), shopifyRow(2), shopifyRow(3), shopifyRow(4)];
        const server = makeLocationServer({ shopify: rows, odoo: [odooRow(9)] });
        const component = await mountLocationStep(server);

        await component.searchLocations("shopify");
        await animationFrame();
        expect(gidsOnScreen()).toHaveLength(2);

        // The set shifts under us: row 2 is served again on page 2.
        rows.splice(2, 0, shopifyRow(2));
        await component.loadMoreLocations("shopify");
        await animationFrame();

        const gids = gidsOnScreen();
        expect(gids).toEqual([
            "gid://shopify/Location/1",
            "gid://shopify/Location/2",
            "gid://shopify/Location/3",
        ]);
        expect(new Set(gids).size).toBe(gids.length);
        // The count the operator reads is the count of rows they can see.
        expect(component.locationShowing("shopify").shown).toBe(3);
        expect(queryText(".sc_setup__showing--shopify")).toInclude("Showing 3");
    });

    test("mapping a location updates that row in place instead of collapsing the pages behind it", async () => {
        // Re-running the search after a mapping fetched ONE page at the last
        // requested offset and replaced everything with it, so an operator who
        // had paged deep into the list watched every earlier row disappear.
        const server = makeLocationServer({
            shopify: [shopifyRow(1), shopifyRow(2), shopifyRow(3), shopifyRow(4)],
            odoo: [odooRow(9), odooRow(10)],
        });
        const component = await mountLocationStep(server, {
            onSaveMapping: () => true,
        });

        await component.searchLocations("shopify");
        await component.loadMoreLocations("shopify");
        await animationFrame();
        expect(gidsOnScreen()).toHaveLength(4);
        await component.searchLocations("odoo");
        await animationFrame();

        component.setLocationMappingChoice("gid://shopify/Location/3", "10");
        const searchesBefore = server.searchCalls.length;
        await component.createMapping("gid://shopify/Location/3");
        await animationFrame();

        // The write happened, with both identities explicit.
        expect(
            calls.filter((c) => c.method === "save_location_mapping")
        ).toHaveLength(1);
        const written = calls.find(
            (c) => c.method === "save_location_mapping"
        ).kwargs;
        expect(written.store_id).toBe(5);
        expect(written.shopify_location_gid).toBe("gid://shopify/Location/3");
        // An integer, not the string the `<select>` holds: the server refuses
        // a non-integer location id outright.
        expect(written.odoo_location_id).toBe(10);
        // ...and cost no further paging.
        expect(server.searchCalls).toHaveLength(searchesBefore);
        // All four pages are still on screen, and exactly one row moved.
        expect(gidsOnScreen()).toHaveLength(4);
        const mapped = queryAll('.sc_setup__location[data-mapped="1"]');
        expect(mapped).toHaveLength(1);
        expect(mapped[0].getAttribute("data-shopify-gid")).toBe(
            "gid://shopify/Location/3"
        );
        expect(mapped[0].textContent).toInclude("WH10/Stock");
        // The selection is consumed, not left armed for a second click.
        expect(
            component.state.locationMappingChoices["gid://shopify/Location/3"]
        ).toBe(undefined);
    });

    test("a selection is revalidated after every search, clear and load more", async () => {
        // `<select>` keeps an assigned value after its `<option>` is gone, so
        // a chosen location that scrolls out of the result set stays in
        // `state.form` -- invisible, and submitted on the next click.
        const server = makeLocationServer({
            shopify: [
                shopifyRow(1, { name: "North depot" }),
                shopifyRow(2, { name: "South depot" }),
                shopifyRow(3, { name: "South annex" }),
            ],
            odoo: [odooRow(9, { name: "North/Stock" }), odooRow(10, { name: "South/Stock" })],
            pageSize: 1,
        });
        const component = await mountLocationStep(server);
        const shopify = component.state.locationSearch.shopify;

        // Chosen from the results of one search...
        shopify.query = "north";
        await component.searchLocations("shopify");
        await animationFrame();
        component.state.form.mapShopifyGid = "gid://shopify/Location/1";
        await animationFrame();

        // ...and gone after the next one.
        shopify.query = "south";
        await component.searchLocations("shopify");
        await animationFrame();
        expect(component.state.form.mapShopifyGid).toBe("");

        // Load more keeps a selection that is still on screen...
        component.state.form.mapShopifyGid = "gid://shopify/Location/2";
        await component.loadMoreLocations("shopify");
        await animationFrame();
        expect(gidsOnScreen()).toHaveLength(2);
        expect(component.state.form.mapShopifyGid).toBe(
            "gid://shopify/Location/2"
        );

        // ...and clearing drops one the base list cannot show.
        component.clearLocationSearch("shopify");
        await animationFrame();
        expect(component.state.form.mapShopifyGid).toBe("");

        // The Odoo side is revalidated on its own searches, independently.
        const odoo = component.state.locationSearch.odoo;
        odoo.query = "north";
        await component.searchLocations("odoo");
        await animationFrame();
        component.state.form.mapOdooLocationId = "9";
        odoo.query = "south";
        await component.searchLocations("odoo");
        await animationFrame();
        expect(component.state.form.mapOdooLocationId).toBe("");
    });

    test("a stale, off-screen or foreign location identity is refused at submit and never sent", async () => {
        // The last line of defence, and the one that matters: the server would
        // refuse an ineligible GID anyway, but a refusal whose cause the
        // operator cannot see is the worse outcome of the two -- and a stale
        // identity that is still ELIGIBLE would not be refused at all.
        const server = makeLocationServer({
            shopify: [shopifyRow(1), shopifyRow(2)],
            odoo: [odooRow(9)],
        });
        const component = await mountLocationStep(server, {
            onSaveMapping: () => true,
        });
        await component.searchLocations("shopify");
        await component.searchLocations("odoo");
        await animationFrame();

        for (const [gid, odooId, label] of [
            ["gid://shopify/Location/999", "9", "never present"],
            ["gid://shopify/Location/1", "999", "foreign Odoo location"],
        ]) {
            calls.length = 0;
            component.state.errorMessage = "";
            // Assigned behind the list's back, which is exactly the shape of
            // the defect: a value the operator cannot see on screen.
            component.state.form.mapShopifyGid = gid;
            component.state.form.mapOdooLocationId = odooId;
            await component.createMapping();
            await animationFrame();
            expect(
                calls.filter((c) => c.method === "save_location_mapping")
            ).toHaveLength(0, {
                message: `a ${label} identity was submitted`,
            });
            expect(component.state.errorMessage).toInclude(
                "no longer in the list on screen"
            );
        }

        // And the row that WAS on screen a moment ago is refused too, once a
        // later search has taken it away.
        component.state.form.mapShopifyGid = "gid://shopify/Location/1";
        component.state.form.mapOdooLocationId = "9";
        component.state.locationSearch.shopify.items = [shopifyRow(2)];
        calls.length = 0;
        await component.createMapping();
        await animationFrame();
        expect(
            calls.filter((c) => c.method === "save_location_mapping")
        ).toHaveLength(0);
        expect(component.state.errorMessage).toInclude(
            "no longer in the list on screen"
        );
    });

    test("an empty Shopify list says WHY, and a fruitless search keeps its way out", async () => {
        // One line was shown for every empty state, so an operator whose
        // SEARCH matched nothing was told their store had no locations. The
        // two conditions need opposite actions -- clear the search, or press
        // Refresh -- so one sentence could only ever be wrong for one of them.
        let reason = "no_results";
        const server = makeLocationServer({
            shopify: [],
            odoo: [],
            emptyReasonFor: () => reason,
        });
        const component = await mountLocationStep(server, {
            locationMapping: {
                refresh: {
                    state: "failed",
                    job_id: 7,
                    reason: "Automatic loading did not finish.",
                },
            },
        });

        component.state.locationSearch.shopify.query = "nothing matches this";
        await component.searchLocations("shopify");
        await animationFrame();
        const noResults = queryText(".sc_setup__empty--shopify");
        expect(noResults).toInclude("No location matches this search");
        // The controls that are the way OUT of a fruitless search must survive
        // it: a zero-result search used to hide the search row, the Clear
        // button together, leaving no visible route back.
        expect(queryAll(".sc_setup_search_shopify")).toHaveLength(1);
        expect(queryAll(".sc_setup_search_shopify_clear")).toHaveLength(1);

        reason = "no_cached_locations";
        component.state.locationSearch.shopify.query = "";
        await component.searchLocations("shopify");
        await animationFrame();
        const noCache = queryText(".sc_setup__empty--shopify");
        expect(noCache).toInclude("No Shopify locations have been read");
        expect(noCache).toInclude("Try again");
        expect(queryText(".sc_setup_refresh_locations")).toInclude("Try again");
        expect(noCache).not.toBe(noResults);
    });

    test("an empty Odoo list distinguishes no match, no access and no warehouse", async () => {
        // Three conditions with three different remedies. The one line that
        // used to be shown for all of them told an operator with no Inventory
        // access to create a warehouse they would not have been able to see.
        let reason = "no_results";
        const server = makeLocationServer({
            shopify: [shopifyRow(1)],
            odoo: [],
            emptyReasonFor: () => reason,
        });
        const component = await mountLocationStep(server, {
            locationMapping: {
                locations: [shopifyRow(1)],
                odoo_locations: [],
            },
        });

        const rendered = [];
        for (const [current, text] of [
            ["no_results", "No location matches this search"],
            ["no_inventory_permission", "You do not have access to Odoo's"],
            [
                "no_eligible_odoo_locations",
                "There are no internal Odoo locations in this company yet",
            ],
        ]) {
            reason = current;
            await component.searchLocations("odoo");
            await animationFrame();
            const shown = queryText(".sc_setup__empty--odoo");
            expect(shown).toInclude(text, {
                message: `${current} rendered: ${shown}`,
            });
            rendered.push(shown);
        }
        expect(new Set(rendered).size).toBe(3);
    });
});
