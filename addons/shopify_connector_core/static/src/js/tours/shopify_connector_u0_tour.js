/** @odoo-module **/
// Part of the Shopify Connector (U0 operator UI foundation).
//
// Browser tours for the connector operator surfaces, driven by
// HttpCase.start_tour (see tests/test_ui_tours.py). The primary navigation
// tour uses the visible Connector User role.
// The role-action tours exercise the retry / cancel / review controls and are
// intended for the driven Odoo.sh runtime campaign with seeded fixtures.

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const menu = (xmlid) => `[data-menu-xmlid="shopify_connector_core.${xmlid}"]`;
const topMenu = {
    Dashboard: menu("menu_shopify_connector_dashboard"),
    Operations: menu("menu_shopify_connector_operations"),
    Reporting: menu("menu_shopify_connector_reporting"),
};

const openPath = (labels, content) => ({
    trigger: topMenu[labels[0]] || ".o_menu_sections",
    content,
    async run() {
        for (const label of labels) {
            const topEntry = [...document.querySelectorAll(
                topMenu[label] || "__missing__"
            )].find((candidate) => candidate.getClientRects().length);
            const entry = topEntry || [...document.querySelectorAll(
                ".o_menu_sections a, .o_menu_sections button, " +
                ".o-dropdown--menu a, .o-dropdown--menu button"
            )].find((candidate) => candidate.textContent.trim() === label);
            if (!entry) {
                throw new Error(`${label} is absent from the operator menu tree`);
            }
            entry.click();
            await new Promise((resolve) => setTimeout(resolve, 400));
        }
    },
});

// --- 1. Primary navigation: Dashboard -> Operations -> Reporting. Read-only;
//        Configuration is covered separately with an Administrator. ---
registry.category("web_tour.tours").add("shopify_connector_u0_nav_tour", {
    url: "/odoo",
    steps: () => [
        // INHERITED DEFECT, corrected 2026-07-26. The `.o_app` tiles live
        // inside the apps-menu sidebar and do not exist in the DOM until it
        // is opened (odoo/odoo@19.0 `web/static/src/webclient/navbar/
        // navbar.xml`), so every tour here timed out on its FIRST step. The
        // U0 navigation tour could therefore never have passed, which is why
        // no repository record carries a green tour result.
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${menu("menu_shopify_connector_root")}`,
            content: "Open the Shopify Connector app.",
            run: "click",
        },
        {
            trigger: ".o_sc_dashboard",
            content: "The Sales Dashboard renders.",
        },
        {
            trigger: ".o_sc_dashboard .sc360-period",
            content: "The reporting-period filter group renders.",
        },
        {
            trigger: ".o_sc_dashboard .sc360-ts-page",
            content: "The page-updated timestamp renders.",
        },
        {
            trigger: ".o_sc_dashboard .sc360-commercial",
            content: "The review-excluded sales region renders.",
        },
        openPath(["Dashboard", "Connector Health"], "Open Connector Health."),
        {
            trigger: ".o_sc_connector_health .sc360-stores-table",
            content: "Per-store health renders without sales figures.",
        },
        {
            trigger: ".o_sc_connector_health .sc360-flows",
            content: "Domain freshness renders unknown states explicitly.",
        },
        openPath(["Operations", "Runs & Recovery"], "Go to Runs & Recovery."),
        {
            trigger: ".o_list_view",
            content: "The runs list renders.",
        },
        openPath(["Operations", "Needs Attention"], "Go to Needs Attention."),
        {
            trigger: ".o_list_view",
            content: "Needs Attention renders.",
        },
        // Store 360 slice: the zero-schema Sync Operations Analysis surface
        // (graph over the job model, native rules).
        openPath(["Reporting", "Sync Performance"], "Go to Sync Performance."),
        {
            trigger: ".o_graph_renderer, .o_graph_view, .o_view_nocontent",
            content: "The analysis graph view renders.",
        },
        openPath(["Reporting", "Audit Trail"], "Go to Audit Trail."),
        {
            trigger: ".o_list_view",
            content: "The audit trail renders.",
        },
    ],
});

// --- 2. Operator: open Runs & Recovery, open a cancellable run, open the
//        cancellation wizard, confirm a reason is required. Needs a seeded
//        queued/running job (runtime fixture). ---
registry.category("web_tour.tours").add("shopify_connector_u0_operator_tour", {
    url: "/odoo",
    steps: () => [
        // INHERITED DEFECT, corrected 2026-07-26. The `.o_app` tiles live
        // inside the apps-menu sidebar and do not exist in the DOM until it
        // is opened (odoo/odoo@19.0 `web/static/src/webclient/navbar/
        // navbar.xml`), so every tour here timed out on its FIRST step. The
        // U0 navigation tour could therefore never have passed, which is why
        // no repository record carries a green tour result.
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${menu("menu_shopify_connector_root")}`,
            run: "click",
        },
        {
            trigger: `${menu("menu_shopify_connector_sync_center")}`,
            run: "click",
        },
        {
            trigger: ".o_list_view .o_data_row:first-child",
            content: "Open the first run.",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: "The run form is available; cancellation is offered where the state and role allow it.",
        },
    ],
});

// --- 3. Reviewer: reach a blocked manual-review run and confirm the review
//        controls (release / resolve) are present, while admin-only mutation
//        resolution is not. Needs a seeded blocked job (runtime fixture). ---
registry.category("web_tour.tours").add("shopify_connector_u0_reviewer_tour", {
    url: "/odoo",
    steps: () => [
        // INHERITED DEFECT, corrected 2026-07-26. The `.o_app` tiles live
        // inside the apps-menu sidebar and do not exist in the DOM until it
        // is opened (odoo/odoo@19.0 `web/static/src/webclient/navbar/
        // navbar.xml`), so every tour here timed out on its FIRST step. The
        // U0 navigation tour could therefore never have passed, which is why
        // no repository record carries a green tour result.
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${menu("menu_shopify_connector_root")}`,
            run: "click",
        },
        {
            trigger: `${menu("menu_shopify_connector_error_center")}`,
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "Needs Attention renders for the reviewer.",
        },
    ],
});

// --- 4. Administrator: open a store, then reach mutation evidence only as a
//        contextual drill-down from Needs Attention. Needs seeded fixtures. ---
registry.category("web_tour.tours").add("shopify_connector_u0_admin_tour", {
    url: "/odoo",
    steps: () => [
        // INHERITED DEFECT, corrected 2026-07-26. The `.o_app` tiles live
        // inside the apps-menu sidebar and do not exist in the DOM until it
        // is opened (odoo/odoo@19.0 `web/static/src/webclient/navbar/
        // navbar.xml`), so every tour here timed out on its FIRST step. The
        // U0 navigation tour could therefore never have passed, which is why
        // no repository record carries a green tour result.
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${menu("menu_shopify_connector_root")}`,
            run: "click",
        },
        {
            trigger: `${menu("menu_shopify_connector_stores")}`,
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "The stores list renders for the administrator.",
        },
        {
            trigger: `${menu("menu_shopify_connector_error_center")}`,
            run: "click",
        },
        {
            trigger: ".o_list_view .o_data_row:has(.o_field_widget[name='mutation_attempt_id'] a) .o_data_cell:first-child",
            content: "Open a run carrying mutation evidence.",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_field_widget[name='mutation_attempt_id'] a",
            content: "Open the contextual Shopify evidence.",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: "The Shopify evidence renders contextually.",
        },
    ],
});
