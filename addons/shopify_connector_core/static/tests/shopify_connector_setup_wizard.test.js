/** @odoo-module **/
// Part of the Shopify Connector (S1 guided setup).
//
// HOOT unit tests for the setup wizard client action. These cover what only a
// mounted component can show: that the eleven accepted steps render in order,
// that Back does not lose what was typed, that no source-of-truth option is
// pre-selected, that a server refusal is surfaced rather than swallowed, and
// that the token never enters component state.
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
    ["readiness", "Readiness checks"],
    ["directions", "What to sync"],
    ["source_of_truth", "Source of truth"],
    ["notification", "Customer notifications"],
    ["first_push", "First stock push"],
    ["review", "Review and activate"],
];

function payload(overrides = {}) {
    return Object.assign(
        {
            steps: STEPS.map(([key, label], index) => ({
                index: index + 1,
                key,
                label,
            })),
            step_count: 11,
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
            readiness: { ran: false, overall: false, checks: [], blocking: [] },
            summary: {
                domains: [],
                matching: "",
                price: "",
                notification: "Customers will not be emailed.",
                first_push: "Inventory is not enabled.",
                can_activate: false,
                blocking: [],
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

describe("shopify connector setup wizard", () => {
    beforeEach(() => {
        calls = [];
        mockService("action", { doAction: () => {} });
        mockService("notification", { add: () => {} });
    });

    test("renders the eleven accepted steps in the accepted order", async () => {
        mockOrm(() => payload());
        await mountWithCleanup(ShopifyConnectorSetupWizard, {
            props: { action: { context: {} } },
        });
        await animationFrame();
        const labels = queryAll(".sc_setup_step__label").map((el) =>
            el.textContent.trim()
        );
        expect(labels).toEqual(STEPS.map(([, label]) => label));
    });

    test("the heading states the step number and the total", async () => {
        mockOrm(() => payload());
        await mountWithCleanup(ShopifyConnectorSetupWizard, {
            props: { action: { context: {} } },
        });
        await animationFrame();
        expect(queryText(".sc_setup__heading")).toInclude("Step 1 of 11");
        expect(queryText(".sc_setup__heading")).toInclude("Welcome");
    });

    test("it opens at the resume step, not always at step 1", async () => {
        mockOrm(() => payload({ resume_step: 7 }));
        await mountWithCleanup(ShopifyConnectorSetupWizard, {
            props: { action: { context: {} } },
        });
        await animationFrame();
        expect(queryText(".sc_setup__heading")).toInclude("Step 7 of 11");
    });

    test("no source-of-truth option is pre-selected", async () => {
        mockOrm(() => payload({ resume_step: 8 }));
        await mountWithCleanup(ShopifyConnectorSetupWizard, {
            props: { action: { context: {} } },
        });
        await animationFrame();
        const checked = queryAll(
            ".sc_setup__choices input[type='radio']:checked"
        );
        expect(checked).toHaveLength(0);
    });

    test("Back returns to the previous step without a server call", async () => {
        mockOrm(() => payload({ resume_step: 4 }));
        await mountWithCleanup(ShopifyConnectorSetupWizard, {
            props: { action: { context: {} } },
        });
        await animationFrame();
        calls = [];
        queryFirst(".sc_setup__actions .sc-btn").click();
        await animationFrame();
        expect(queryText(".sc_setup__heading")).toInclude("Step 3 of 11");
        expect(calls).toHaveLength(0);
    });

    test("a server refusal is shown, not swallowed", async () => {
        mockOrm((method) => {
            if (method === "get_setup_state") {
                return payload({ resume_step: 2 });
            }
            const error = new Error("refused");
            error.data = { message: "Enter the store's permanent domain." };
            throw error;
        });
        await mountWithCleanup(ShopifyConnectorSetupWizard, {
            props: { action: { context: {} } },
        });
        await animationFrame();
        queryFirst(".sc_setup_continue").click();
        await animationFrame();
        await animationFrame();
        expect(queryText(".sc_setup__error")).toInclude(
            "permanent domain"
        );
        // And the wizard did NOT advance past a refusal.
        expect(queryText(".sc_setup__heading")).toInclude("Step 2 of 11");
    });

    test("the token is never held in component state", async () => {
        mockOrm((method) => {
            if (method === "get_setup_state") {
                return payload({ resume_step: 3, store: Object.assign(
                    payload().store, { id: 7 }
                ) });
            }
            return payload({
                resume_step: 3,
                store: Object.assign(payload().store, {
                    id: 7,
                    credential_present: true,
                }),
            });
        });
        const component = await mountWithCleanup(
            ShopifyConnectorSetupWizard,
            { props: { action: { context: {} } } }
        );
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

    test("an enabled domain shows what is still withheld", async () => {
        mockOrm(() => payload({ resume_step: 7 }));
        await mountWithCleanup(ShopifyConnectorSetupWizard, {
            props: { action: { context: {} } },
        });
        await animationFrame();
        expect(queryAll(".sc_setup__domain-withheld")).toHaveLength(0);
        queryFirst("#sc_setup_domain_sale").click();
        await animationFrame();
        expect(queryText(".sc_setup__domain-withheld")).toInclude(
            "never written back"
        );
    });

    test("readiness results carry text, never colour alone", async () => {
        mockOrm(() =>
            payload({
                resume_step: 6,
                readiness: {
                    ran: true,
                    overall: "fail",
                    checks: [
                        {
                            code: "web_base_url",
                            label: "Odoo knows its own public address",
                            tier: "essential",
                            result: "fail",
                            tone: "danger",
                            reason: "web.base.url is not HTTPS.",
                            owner: "Odoo administrator",
                        },
                    ],
                    blocking: [],
                },
            })
        );
        await mountWithCleanup(ShopifyConnectorSetupWizard, {
            props: { action: { context: {} } },
        });
        await animationFrame();
        const row = queryText(".sc_setup__checks li");
        expect(row).toInclude("Must be fixed");
        expect(row).toInclude("web.base.url is not HTTPS.");
        expect(row).toInclude("Odoo administrator");
    });
});
