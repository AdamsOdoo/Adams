/** @odoo-module **/
// Part of the Shopify Connector (U3 export operator experience).
//
// Browser tours for the U3 export surfaces, driven by HttpCase.start_tour (see
// tests/test_u3_export_tours.py).
//
// The navigation tour is the automated acceptance: it walks the whole Export
// branch and asserts every U3 surface renders for a connector user. It needs
// no seeded Shopify state, so it runs in the ordinary suite rather than only
// in a driven runtime campaign.
//
// The review tour opens the Owl diff surface on a seeded preview and asserts
// the three things that make it safe: the refusals are on screen, the tag
// removals are on screen, and the confirm control is present for a reviewer.
// It deliberately does NOT click confirm — confirming enqueues an apply job,
// and a tour must not leave a queued mutation behind.

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

// An XML `type="action"` button renders its `name` attribute as the RESOLVED
// numeric action id (Odoo writes the id, not the xmlid), so selecting on
// `name*='action_…'` matches nothing. The button is targeted by the label an
// operator actually reads, which is also the thing worth asserting.
const REVIEW_BUTTON = ".o_form_view button:contains('Review Export')";

const coreMenu = (xmlid) => `[data-menu-xmlid="shopify_connector_core.${xmlid}"]`;
const menu = (xmlid) =>
    `[data-menu-xmlid="shopify_connector_product_export.${xmlid}"]`;

// --- 1. Navigation: every U3 export surface renders. ---
registry.category("web_tour.tours").add("shopify_connector_u3_export_nav_tour", {
    url: "/odoo",
    steps: () => [
        // In Odoo 19 the `.o_app` tiles live inside the apps-menu sidebar and
        // do not exist in the DOM until it is opened (odoo/odoo@19.0
        // `web/static/src/webclient/navbar/navbar.xml`). A tour that triggers
        // on `.o_app` without this step waits for an element that will never
        // appear, and times out looking like a broken surface.
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${coreMenu("menu_shopify_connector_root")}`,
            content: "Open the Shopify Connector app.",
            run: "click",
        },
        {
            trigger: menu("menu_shopify_connector_product_export"),
            content: "Open the Export branch.",
            run: "click",
        },
        {
            trigger: menu("menu_shopify_connector_product_export_preview"),
            content: "Export Previews.",
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "The export previews list renders.",
        },
        {
            trigger: menu("menu_shopify_connector_product_export"),
            content: "Re-open the Export branch — the dropdown collapses on navigation.",
            run: "click",
        },
        {
            trigger: menu("menu_shopify_connector_product_export_media"),
            content: "Exported Media.",
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "The exported-media registry renders.",
        },
        {
            trigger: menu("menu_shopify_connector_product_export"),
            run: "click",
        },
        {
            trigger: menu("menu_shopify_connector_product_export_backfill"),
            content: "Reconnect and Backfill.",
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "The reconnect/backfill catch-up surface renders.",
        },
        {
            trigger: menu("menu_shopify_connector_product_export"),
            run: "click",
        },
        {
            trigger: menu("menu_shopify_connector_product_export_settings"),
            content: "Export Settings.",
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "The per-store export settings render.",
        },
        {
            trigger: menu("menu_shopify_connector_product_export"),
            run: "click",
        },
        {
            trigger: menu("menu_shopify_connector_product_export_diagnostics"),
            content: "Export Diagnostics.",
            run: "click",
        },
        {
            trigger: ".o_list_view, .o_nocontent_help",
            content:
                "Diagnostics renders — either rows that need a decision, or the " +
                "empty state that says nothing does.",
        },
    ],
});

// --- 2. Review: the Owl diff surface discloses before it offers. ---
registry.category("web_tour.tours").add("shopify_connector_u3_export_review_tour", {
    url: "/odoo",
    steps: () => [
        // In Odoo 19 the `.o_app` tiles live inside the apps-menu sidebar and
        // do not exist in the DOM until it is opened (odoo/odoo@19.0
        // `web/static/src/webclient/navbar/navbar.xml`). A tour that triggers
        // on `.o_app` without this step waits for an element that will never
        // appear, and times out looking like a broken surface.
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${coreMenu("menu_shopify_connector_root")}`,
            run: "click",
        },
        {
            trigger: menu("menu_shopify_connector_product_export"),
            run: "click",
        },
        {
            trigger: menu("menu_shopify_connector_product_export_preview"),
            run: "click",
        },
        {
            trigger: ".o_list_view .o_data_row:first-child .o_data_cell",
            content: "Open the seeded preview.",
            run: "click",
        },
        {
            trigger: REVIEW_BUTTON,
            content: "Open the Owl review surface.",
            run: "click",
        },
        {
            trigger: ".o_sc_export_diff",
            content: "The export diff surface renders.",
        },
        {
            // The refusal section must be reachable BEFORE the confirm
            // control, which is what the reading order in the template is
            // for. If this step ever has to scroll past a confirm button to
            // find the refusals, the ordering regressed.
            trigger: ".o_sc_export_diff .sc-x-section__title--danger",
            content: "The refused differences are disclosed.",
        },
        {
            trigger: ".o_sc_export_diff .sc-x-tag--removed",
            content: "The tags this export removes are enumerated by name.",
        },
        {
            trigger: ".o_sc_export_diff button[name='confirm_export']",
            content:
                "The confirm control is present for a reviewer. The tour stops " +
                "here on purpose: confirming enqueues a real apply job.",
        },
    ],
});

// --- 3. Keyboard-only: the whole review surface is reachable by Tab, and
//        every focused control shows a visible focus ring. Asserted by
//        driving Tab rather than by clicking. ---
registry.category("web_tour.tours").add("shopify_connector_u3_export_keyboard_tour", {
    url: "/odoo",
    steps: () => [
        // In Odoo 19 the `.o_app` tiles live inside the apps-menu sidebar and
        // do not exist in the DOM until it is opened (odoo/odoo@19.0
        // `web/static/src/webclient/navbar/navbar.xml`). A tour that triggers
        // on `.o_app` without this step waits for an element that will never
        // appear, and times out looking like a broken surface.
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${coreMenu("menu_shopify_connector_root")}`,
            run: "click",
        },
        {
            trigger: menu("menu_shopify_connector_product_export"),
            run: "click",
        },
        {
            trigger: menu("menu_shopify_connector_product_export_preview"),
            run: "click",
        },
        {
            trigger: ".o_list_view .o_data_row:first-child .o_data_cell",
            run: "click",
        },
        {
            trigger: REVIEW_BUTTON,
            run: "click",
        },
        {
            trigger: ".o_sc_export_diff .sc-x-actions .sc-x-btn",
            content: "Focus the first action by keyboard.",
            run() {
                const button = document.querySelector(
                    ".o_sc_export_diff .sc-x-actions .sc-x-btn"
                );
                button.focus();
                if (document.activeElement !== button) {
                    throw new Error(
                        "the export action control could not take keyboard focus"
                    );
                }
                // A focus ring that is only in the stylesheet is not evidence.
                // `:focus-visible` is what the sheet styles, so assert the
                // focused element actually matches it.
                if (!button.matches(":focus-visible")) {
                    throw new Error(
                        "the focused export control does not match :focus-visible, " +
                            "so it renders no visible focus indicator"
                    );
                }
            },
        },
    ],
});
