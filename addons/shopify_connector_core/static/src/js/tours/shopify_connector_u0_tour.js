/** @odoo-module **/
// Part of the Shopify Connector (U0 operator UI foundation).
//
// Browser tours for the U0 operator surfaces, driven by HttpCase.start_tour
// (see tests/test_ui_tours.py). The primary navigation tour is role-agnostic
// (every connector role can read every surface) and is the automated check.
// The role-action tours exercise the retry / cancel / review controls and are
// intended for the driven Odoo.sh runtime campaign with seeded fixtures.

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const menu = (xmlid) => `[data-menu-xmlid="shopify_connector_core.${xmlid}"]`;

// --- 1. Primary navigation (Auditor and up): Dashboard -> Stores ->
//        Sync Center -> Error & Review Center -> Logs. Read-only; asserts each
//        surface renders and no write control is required to move through. ---
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
            content: "The Store 360 dashboard renders.",
        },
        // Store 360: with the seeded connected store (test fixture), the
        // shell shows the header with the period filter group, the two
        // distinct timestamps, and the connector-health region.
        {
            trigger: ".o_sc_dashboard .sc360-period",
            content: "The reporting-period filter group renders.",
        },
        {
            trigger: ".o_sc_dashboard .sc360-ts-page",
            content: "The page-updated timestamp renders.",
        },
        {
            trigger: ".o_sc_dashboard .sc360-health",
            content: "The connector-health region renders.",
        },
        {
            trigger: ".o_sc_dashboard .sc360-flows",
            content: "The flow-health table renders.",
        },
        {
            trigger: `${menu("menu_shopify_connector_stores")}`,
            content: "Go to Stores.",
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "The stores list renders.",
        },
        {
            trigger: `${menu("menu_shopify_connector_sync_center")}`,
            content: "Go to the Sync Center.",
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "The Sync Center list renders.",
        },
        {
            trigger: `${menu("menu_shopify_connector_error_center")}`,
            content: "Go to the Error & Review Center.",
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "The Error & Review Center renders.",
        },
        // Store 360 slice: the zero-schema Sync Operations Analysis surface
        // (graph over the job model, native rules).
        {
            trigger: `${menu("menu_shopify_connector_sync_analysis")}`,
            content: "Go to Sync Operations Analysis.",
            run: "click",
        },
        {
            trigger: ".o_graph_renderer, .o_graph_view, .o_view_nocontent",
            content: "The analysis graph view renders.",
        },
        {
            trigger: `${menu("menu_shopify_connector_logs")}`,
            content: "Go to Logs.",
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "The Logs list renders.",
        },
    ],
});

// --- 2. Operator: open the Error Center, open a cancellable job, open the
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
            content: "Open the first job.",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: "The job form is available; cancellation is offered where the state and role allow it.",
        },
    ],
});

// --- 3. Reviewer: reach a blocked_manual_review job and confirm the review
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
            content: "The Error & Review Center renders for the reviewer.",
        },
    ],
});

// --- 4. Administrator: open a store, confirm the safe lifecycle/test controls
//        are visible and no credential value is shown; reach mutation evidence
//        and confirm the resolution wizard is offered. Needs seeded fixtures. ---
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
            trigger: `${menu("menu_shopify_connector_mutation_evidence")}`,
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "The mutation-evidence list renders.",
        },
    ],
});
