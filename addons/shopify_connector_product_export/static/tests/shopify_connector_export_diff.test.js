/** @odoo-module **/
// Part of the Shopify Connector (U3 export operator experience).
//
// HOOT unit tests for the S7 export diff client action.
//
// What these assert is the thing the surface exists to guarantee: that a
// reviewer cannot reach the confirm control without the removals and the
// refusals being on screen, and that the component never invents a
// confirmation path of its own.
//
// Reduced-motion, contrast and the responsive table are CSS-only (media
// queries and token pairs in the SCSS) and are covered by the stylesheet plus
// the browser tour, not asserted here — HOOT renders without the backend
// bundle's computed styles, so a colour assertion here would be testing the
// test harness.

import { expect, test, describe, beforeEach } from "@odoo/hoot";
import { queryAll, queryText } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, mountWithCleanup, mockService } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";

// `mountWithCleanup` boots the real web env, which starts every registered
// service. With `mail` present in the database that includes the discuss
// store, and its first fetch fails the test with `Cannot find a definition
// for model "discuss.channel"` unless the mock server knows the models.
//
// `defineModels(mailModels)` rather than `defineMailModels()`: the latter also
// calls `defineParams({suite: "mail"})`, which would rename this suite and
// make it unreachable by the filter the Python runner uses.
defineModels(mailModels);
import { ShopifyConnectorExportDiff } from "@shopify_connector_product_export/js/shopify_connector_export_diff";

function payload(overrides = {}) {
    return Object.assign(
        {
            id: 7,
            state: "previewed",
            state_label: "Previewed",
            state_tone: "warning",
            export_path: "update",
            product_name: "Exportable Widget",
            store_name: "Export Test Store",
            previewed_at: "2026-07-26 00:00:00",
            expires_at: "2026-07-27 00:00:00",
            confirmed_by: "",
            is_expired: false,
            can_confirm: true,
            sections: [
                {
                    key: "scalars",
                    title: "Product details",
                    rows: [{ field: "title", from: "Old", to: "New" }],
                },
            ],
            tag_replacement: {
                applies: true,
                removes: true,
                removed: ["merchant-added"],
                resulting: ["keep-me"],
                note: "Confirming replaces the COMPLETE Shopify tag list.",
            },
            media: { exported: false, reason: "Media export is off.", appends: [] },
            untouched: {
                items: [{ key: "collections", label: "Collections", present: true }],
                note: "Never included in this export.",
            },
            refusals: [
                {
                    kind: "unowned_remote_variant",
                    label: "Shopify variant this connector does not own",
                    detail: "It is left exactly as it is.",
                },
            ],
            plan: {
                steps: [
                    { index: 1, step: "product_export_update", label: "Update product details",
                      state: "pending", tone: "neutral" },
                ],
                total: 1,
                done: 0,
                percent: 0,
            },
        },
        overrides
    );
}

const PROPS = { action: { context: { active_id: 7 } } };

function mockOrm(handlers = {}) {
    mockService("orm", {
        call: async (model, method, args) => {
            if (method === "get_export_preview_data") {
                expect(model).toBe("shopify.connector.product.export.ui");
                return (handlers.get || (() => payload()))(args);
            }
            if (method === "action_confirm_export_preview") {
                expect(model).toBe("shopify.connector.product.export.preview");
                return (handlers.confirm || (() => true))(args);
            }
            throw new Error("unexpected RPC: " + model + "." + method);
        },
    });
}

describe("shopify connector export diff", () => {
    // `mockService` mutates the services registry. Called at MODULE scope it
    // runs while HOOT is still registering the suite, which HOOT rejects
    // outright ("error while registering suite"). It belongs in a per-test
    // hook, where the registry patch is set up and torn down around each
    // test the way the helper is designed for.
    beforeEach(() => {
        mockService("action", { doAction: async () => {} });
    });

    test("renders the product, the store and the state", async () => {
        mockOrm();
        await mountWithCleanup(ShopifyConnectorExportDiff, { props: PROPS });
        expect(queryText(".sc-x-head__title")).toBe("Exportable Widget");
        expect(".sc-x-badge--warning").toHaveCount(1);
    });

    test("tag removals are enumerated by name in an alert", async () => {
        mockOrm();
        await mountWithCleanup(ShopifyConnectorExportDiff, { props: PROPS });
        const alert = queryAll(".sc-x-band--warning[role='alert']");
        expect(alert).toHaveLength(1);
        expect(queryText(".sc-x-tag--removed")).toInclude("merchant-added");
    });

    test("a tag change that only ADDS raises no removal alert", async () => {
        // Crying wolf on every tag edit is how a real removal stops being
        // read, so the alert is keyed on `removes`, not on `applies`.
        mockOrm({
            get: () =>
                payload({
                    tag_replacement: {
                        applies: true, removes: false, removed: [],
                        resulting: ["keep-me", "new"], note: "n/a",
                    },
                }),
        });
        await mountWithCleanup(ShopifyConnectorExportDiff, { props: PROPS });
        expect(".sc-x-band--warning[role='alert']").toHaveCount(0);
    });

    test("refusals render with their own heading and detail", async () => {
        mockOrm();
        await mountWithCleanup(ShopifyConnectorExportDiff, { props: PROPS });
        expect(".sc-x-section__title--danger").toHaveCount(1);
        expect(queryText(".sc-x-list__item--danger")).toInclude(
            "Shopify variant this connector does not own"
        );
    });

    test("the confirm control is absent when the server would refuse", async () => {
        mockOrm({ get: () => payload({ can_confirm: false }) });
        await mountWithCleanup(ShopifyConnectorExportDiff, { props: PROPS });
        expect("button[name='confirm_export']").toHaveCount(0);
    });

    test("an expired preview says so and offers no confirm", async () => {
        mockOrm({
            get: () => payload({ is_expired: true, can_confirm: false, state: "expired" }),
        });
        await mountWithCleanup(ShopifyConnectorExportDiff, { props: PROPS });
        expect(".sc-x-band--neutral[role='status']").toHaveCount(1);
        expect("button[name='confirm_export']").toHaveCount(0);
    });

    test("confirm calls exactly action_confirm_export_preview and nothing else", async () => {
        // The component must have no confirmation path of its own. If a
        // future edit ever writes a field or enqueues a job directly, the
        // ORM mock throws on the unexpected call and this fails.
        let confirmed = null;
        mockOrm({ confirm: (args) => { confirmed = args; return true; } });
        const component = await mountWithCleanup(ShopifyConnectorExportDiff, {
            props: PROPS,
        });
        await component.confirm();
        await animationFrame();
        expect(confirmed).toEqual([[7]]);
    });

    test("a double click cannot enqueue two applies", async () => {
        let calls = 0;
        mockOrm({
            confirm: async () => {
                calls += 1;
                return true;
            },
        });
        const component = await mountWithCleanup(ShopifyConnectorExportDiff, {
            props: PROPS,
        });
        await Promise.all([component.confirm(), component.confirm()]);
        expect(calls).toBe(1);
    });

    test("a failed load renders an error rather than an empty screen", async () => {
        mockOrm({
            get: () => {
                throw new Error("nope");
            },
        });
        await mountWithCleanup(ShopifyConnectorExportDiff, { props: PROPS });
        expect(".sc-x-band--danger[role='alert']").toHaveCount(1);
    });

    test("a preview with nothing to do says so instead of rendering blank", async () => {
        mockOrm({
            get: () =>
                payload({
                    sections: [],
                    refusals: [],
                    tag_replacement: { applies: false, removes: false, removed: [],
                                       resulting: [], note: "" },
                    media: { exported: false, reason: "Media export is off.", appends: [] },
                    plan: { steps: [], total: 0, done: 0, percent: 0 },
                    can_confirm: false,
                }),
        });
        await mountWithCleanup(ShopifyConnectorExportDiff, { props: PROPS });
        expect(".sc-x-empty").toHaveCount(1);
    });

    test("the progress bar carries accessible bounds", async () => {
        mockOrm({
            get: () =>
                payload({
                    plan: {
                        steps: [
                            { index: 1, step: "product_export_update", label: "Update",
                              state: "done", tone: "success" },
                            { index: 2, step: "product_export_media_stage", label: "Append",
                              state: "pending", tone: "neutral" },
                        ],
                        total: 2, done: 1, percent: 50,
                    },
                }),
        });
        await mountWithCleanup(ShopifyConnectorExportDiff, { props: PROPS });
        expect("[role='progressbar']").toHaveAttribute("aria-valuenow", "1");
        expect("[role='progressbar']").toHaveAttribute("aria-valuemax", "2");
    });
});
