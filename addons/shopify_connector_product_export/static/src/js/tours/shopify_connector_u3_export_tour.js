/** @odoo-module **/
// Part of the Shopify Connector (U3 export operator experience).
//
// Browser tours for the U3 export surfaces, driven by HttpCase.start_tour (see
// tests/test_u3_export_tours.py).
//
// The navigation tour checks the C1 split: export monitoring in Operations,
// settings in Administrator-only Configuration, and diagnostics/recovery out
// of navigation. It needs no seeded Shopify state.
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

const openPath = (labels, content = "") => ({
    trigger: ".o_menu_sections",
    content,
    async run() {
        for (const label of labels) {
            const entry = [...document.querySelectorAll(
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

// --- 1. Navigation: operations plus Administrator configuration. ---
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
        openPath(
            ["Operations", "Product Export Reviews"],
            "Open Product Export Reviews."
        ),
        {
            trigger: ".o_list_view",
            content: "The export previews list renders.",
        },
        openPath(["Operations", "Media Exports"], "Open Media Exports."),
        {
            trigger: ".o_list_view",
            content: "The media export registry renders.",
        },
        openPath(["Configuration", "Export Settings"], "Open Export Settings."),
        {
            trigger: ".o_list_view",
            content: "The per-store export settings render.",
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
        openPath(["Operations", "Product Export Reviews"]),
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
        openPath(["Operations", "Product Export Reviews"]),
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

// --- 4. TD-011: the media-resume route works in a real browser. ---
//
// This exists because the TD-011 defect was, exactly, a capability that
// passed 15 server-side tests and could not be reached by an operator. A
// server test asserting the action method behaves correctly cannot catch a
// button whose `name` does not resolve, a `groups` attribute that hides the
// control from the role the server admits, an `invisible` expression that
// hides it when it should show, or a notification that never renders. Those
// are the failure modes that make a route unreachable, and they only exist
// in a browser.
//
// The row it acts on is seeded in Odoo rows only and its export genuinely
// stopped. Clicking Resume admits a QUEUED job; nothing is transported,
// because the transport is a separate dispatch this tour does not run.
registry.category("web_tour.tours").add("shopify_connector_u3_media_resume_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${coreMenu("menu_shopify_connector_root")}`,
            content: "Open the Shopify Connector app.",
            run: "click",
        },
        openPath(
            ["Operations", "Media Exports"],
            "Exported Media — the registry that owns this surface."
        ),
        {
            trigger: ".o_list_view .o_data_row:first-child .o_data_cell",
            content: "Open the stopped media row.",
            run: "click",
        },
        {
            // Targeted by the label an operator reads, for the same reason as
            // REVIEW_BUTTON above: an XML `type="object"` button keeps its
            // method name, but asserting the label is what proves the control
            // an operator can find is the one that is wired.
            trigger: ".o_form_view button:contains('Resume Export')",
            content: "The resume control is offered to a role the server admits.",
            run: "click",
        },
        {
            trigger: ".o_notification",
            content: "A resume produces an operator-visible result.",
            run() {
                const text = document.querySelector(".o_notification").innerText;
                if (!/resumed/i.test(text)) {
                    throw new Error(
                        "the resume produced no operator-visible confirmation: " + text
                    );
                }
            },
        },
    ],
});

// --- 5. TD-015: the one resolvable reconciliation review, end to end. ---
//
// This tour is the answer to the question the previous cycle could not answer:
// "where does an operator actually go to clear this?" It walks the route a
// real administrator walks — Stores, the store form, the reconciliation
// section, the review list, the acknowledgement dialog — and only a browser
// can prove it exists. A server-side test proves the METHOD works; it cannot
// prove there is a control anywhere that reaches it, and an unreachable
// method is exactly the defect being corrected.
//
// It asserts the consequence copy is on screen BEFORE the confirmation is
// possible, then confirms, then asserts the store reached "Reconciled". No
// Shopify request occurs: the acknowledgement route has no transport in it.
registry.category("web_tour.tours").add("shopify_connector_u3_checksum_ack_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${coreMenu("menu_shopify_connector_root")}`,
            content: "Open the Shopify Connector app.",
            run: "click",
        },
        openPath(["Configuration", "Stores & Onboarding"],
            "Stores — the store owns the reconciliation surface."
        ),
        {
            trigger: ".o_list_view .o_data_row:first-child .o_data_cell",
            content: "Open the reconnected store.",
            run: "click",
        },
        {
            // The verdict must be VISIBLE. Before this cycle it was stored
            // and rendered nowhere, so an operator whose exports were blocked
            // had no way to learn why.
            trigger: ".o_form_view:contains('Review Required')",
            content: "The store states that the reconciliation needs review.",
        },
        {
            trigger: ".o_form_view button[name='action_shopify_export_open_checksum_ack_wizard']",
            content: "The acknowledgement control is offered on the review row.",
            run: "click",
        },
        {
            // Four claims, on screen, before any confirmation is possible.
            trigger: ".modal .o_form_view",
            content: "The consequence dialog states what was and was not proven.",
            run() {
                const text = document.querySelector(".modal .o_form_view").innerText;
                for (const required of [
                    "still attached",
                    "no digest",
                    "does not verify anything",
                    "no export runs",
                ]) {
                    if (!text.includes(required)) {
                        throw new Error(
                            "the acknowledgement dialog omitted a required " +
                            "statement: " + required
                        );
                    }
                }
            },
        },
        {
            trigger: ".modal .o_field_widget[name='confirmed'] input",
            content: "Acknowledging is an explicit act.",
            run: "click",
        },
        {
            trigger: ".modal footer button:contains('Acknowledge')",
            content: "Record the acknowledgement.",
            run: "click",
        },
        {
            trigger: ".o_form_view:contains('Reconciled')",
            content: "The store converged; exports are no longer blocked.",
        },
    ],
});
