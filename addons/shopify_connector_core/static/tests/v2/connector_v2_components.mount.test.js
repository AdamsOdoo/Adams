/** @odoo-module **/

/*
 * Real HOOT mount coverage for the inert V2 components.  This source is
 * deliberately kept outside the manifest until the shell/client-action
 * wiring gate is accepted; once wired, these tests prove the Owl templates
 * and the controlled accessibility contract in a real DOM.
 */

import { describe, expect, test } from "@odoo/hoot";
import { queryFirst, queryText } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import {
    AttentionWorkspace,
    Overview,
    RunTimeline,
    StateMessage,
    StatusPill,
    StoreSwitcher,
} from "@shopify_connector_core/v2/connector_v2_components";

function envelope(data, status = "success") {
    return { contract_version: 1, status, data };
}

describe("V2 component Owl mounts", () => {
    test("binds the selected store option and its label to a unique select", async () => {
        await mountWithCleanup(StoreSwitcher, {
            props: {
                envelope: envelope({
                    selected_store_id: 8,
                    allowed_stores: [
                        { id: 7, name: "Aurora", connection: "connected" },
                        { id: 8, name: "Borealis", connection: "disconnected" },
                    ],
                }),
            },
        });

        const select = queryFirst("select");
        expect(select).toBeTruthy();
        expect(select.value).toBe("8");
        expect(select.id).toInclude("sc-v2-store-select-");
        expect(queryFirst("label").getAttribute("for")).toBe(select.id);
        expect(queryFirst("option[value='8']").selected).toBe(true);
    });

    test("exposes a selected detail as a focusable live region", async () => {
        const item = {
            item_ref: "attention:orders:missing_mapping:17",
            severity: "critical",
            severity_label: "Critical",
            title: "Order mapping needs review",
            impact_summary: "One order is held until its product is mapped.",
            age_seconds: 3600,
            allowed_actions: [],
        };
        await mountWithCleanup(AttentionWorkspace, {
            props: {
                envelope: envelope({ items: [item], total: 1 }),
                selectedItemRef: item.item_ref,
            },
        });

        const row = queryFirst(".sc-v2-attention-row");
        const detail = queryFirst(".sc-v2-attention__detail");
        expect(row.getAttribute("aria-current")).toBe("true");
        expect(row.getAttribute("aria-expanded")).toBe("true");
        expect(row.getAttribute("aria-controls")).toBe(detail.id);
        expect(detail.getAttribute("tabindex")).toBe("-1");
        expect(detail.getAttribute("aria-live")).toBe("polite");
        expect(detail.getAttribute("aria-labelledby")).toBe(
            queryFirst(".sc-v2-detail-header h2").id
        );

        detail.focus();
        expect(document.activeElement).toBe(detail);
        expect(queryText(".sc-v2-attention-row__age")).toBe("1 hour");
    });

    test("keeps collapsed rows linked to the empty detail target", async () => {
        await mountWithCleanup(AttentionWorkspace, {
            props: {
                envelope: envelope({
                    items: [
                        {
                            item_ref: "attention:inventory:drift:23",
                            severity: "warning",
                            title: "Inventory drift needs review",
                            impact_summary: "One location is out of date.",
                        },
                    ],
                    total: 1,
                }),
            },
        });

        const row = queryFirst(".sc-v2-attention-row");
        const detail = queryFirst(".sc-v2-attention__detail--empty");
        expect(row.getAttribute("aria-current")).toBe(null);
        expect(row.getAttribute("aria-expanded")).toBe("false");
        expect(row.getAttribute("aria-controls")).toBe(detail.id);
        expect(detail.getAttribute("tabindex")).toBe("-1");
        expect(detail.getAttribute("aria-labelledby")).toBe(
            queryFirst(".sc-v2-attention__detail--empty h2").id
        );
    });

    test("renders bounded attention truth even when the envelope status is success", async () => {
        await mountWithCleanup(AttentionWorkspace, {
            props: {
                envelope: envelope({ items: [], total: 80, truncated: true, partial: false }),
            },
        });

        expect(queryText(".sc-v2-inline-notice")).toInclude(
            "More attention items exist beyond this bounded view"
        );
    });

    test("prioritizes a recovery action over navigation actions", async () => {
        const item = {
            item_ref: "attention:orders:job:17",
            state_version: 4,
            severity: "warning",
            title: "A retry is available",
            impact_summary: "The order import is waiting for a safe retry.",
            allowed_actions: [
                { key: "open_run", label: "View run", item_ref: "job:17" },
                { key: "retry_job", label: "Retry safely", item_ref: "job:17" },
            ],
        };
        await mountWithCleanup(AttentionWorkspace, {
            props: {
                envelope: envelope({ items: [item], total: 1 }),
                selectedItemRef: item.item_ref,
            },
        });

        expect(queryText(".sc-v2-resolution .sc-v2-button--primary")).toInclude(
            "Retry safely"
        );
    });

    test("does not trust a detail projection for another selected item", async () => {
        await mountWithCleanup(AttentionWorkspace, {
            props: {
                envelope: envelope({
                    items: [],
                    detail: {
                        item_ref: "attention:other",
                        title: "Stale detail",
                        allowed_actions: [],
                    },
                }),
                selectedItemRef: "attention:selected",
            },
        });

        expect(queryFirst(".sc-v2-attention__detail--empty")).toBeTruthy();
        expect(queryText(".sc-v2-attention__detail")).not.toInclude("Stale detail");
    });

    test("does not render a run recovery or unauthorized record link", async () => {
        await mountWithCleanup(RunTimeline, {
            props: {
                envelope: envelope({
                    run_ref: "run:17",
                    display_name: "RUN-000017",
                    state: "failed_retryable",
                    allowed_actions: [
                        { key: "retry_job", label: "Retry safely", item_ref: "job:17" },
                    ],
                    affected_records: [
                        {
                            item_ref: "stock.picking:23",
                            action_key: "open_native_record",
                            target: {
                                type: "ir.actions.act_window",
                                res_model: "stock.picking",
                            },
                        },
                    ],
                }),
            },
        });

        expect(queryFirst(".sc-v2-run-summary .sc-v2-button")).toBe(null);
        expect(queryFirst(".sc-v2-run__evidence .sc-v2-link-button")).toBe(null);
    });

    test("surfaces an incomplete nested overview attention projection", async () => {
        await mountWithCleanup(Overview, {
            props: {
                envelope: envelope({
                    store: { id: 7, name: "Aurora" },
                    health: { severity: "healthy", title: "Healthy", reason: "Recorded" },
                    workflows: [],
                    attention: { items: [], total: 0, truncated: true },
                    activity: null,
                }),
            },
        });

        expect(queryText(".sc-v2-overview")).toInclude("Incomplete preview");
        expect(queryText(".sc-v2-overview")).not.toInclude("Nothing needs attention");
    });

    test("renders a closed business-language label for a terminal state", async () => {
        await mountWithCleanup(StateMessage, {
            props: { state: "terminal_error", detail: null, action: null },
        });

        expect(queryText(".sc-v2-state-message__title")).toBe(
            "This view could not be loaded"
        );
        expect(queryText(".sc-v2-state-message__detail")).toInclude("No action was taken");
    });

    test("does not render an empty run shell when the response has no run", async () => {
        await mountWithCleanup(RunTimeline, {
            props: { envelope: envelope({}, "unconfigured") },
        });

        expect(queryText(".sc-v2-state-message__title")).toBe("Finish setting up this store");
        expect(queryFirst(".sc-v2-run__loading")).toBe(null);
    });

    test("renders bounded run evidence truth even when the envelope status is success", async () => {
        await mountWithCleanup(RunTimeline, {
            props: {
                envelope: envelope({
                    run_ref: "run:17",
                    display_name: "RUN-000017",
                    state: "succeeded",
                    scope: { label: "Bounded test" },
                    result: { title: "Completed", message: "Recorded" },
                    timeline: [],
                    jobs: [],
                    affected_records: [],
                    allowed_actions: [],
                    truncation: { affected_records: true },
                }),
            },
        });

        expect(queryText(".sc-v2-inline-notice")).toInclude("bounded run view");
    });

    test("escapes status labels through the Owl text renderer", async () => {
        await mountWithCleanup(StatusPill, {
            props: { state: "warning", label: "<img src=x onerror=alert(1)>" },
        });

        expect(queryFirst(".sc-v2-status-pill__label").textContent).toBe(
            "<img src=x onerror=alert(1)>"
        );
        expect(queryFirst(".sc-v2-status-pill__label img")).toBe(null);
    });
});
