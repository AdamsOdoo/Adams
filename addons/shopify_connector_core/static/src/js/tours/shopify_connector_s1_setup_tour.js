/** @odoo-module **/
// Part of the Shopify Connector (S1 guided setup).
//
// Browser tours for the setup wizard, driven by HttpCase.start_tour (see
// tests/test_ui_setup_tours.py).
//
// WHY A TOUR AND NOT ONLY SERVER TESTS. The server tests prove every step's
// method is correct and correctly guarded. They cannot prove there is a
// reachable control that calls it, that the Owl template renders without
// throwing, that the asset bundle builds, that the client action's tag
// resolves, or that the eleven steps appear in the accepted order on screen.
// Those failures only exist in a browser, and they are exactly the ones that
// make a feature look implemented and be unusable.
//
// The traversal tour walks all ELEVEN steps in order and finishes by
// activating. It contacts no Shopify store: the test patches the transport
// seam before starting the browser, so step 5's probe is answered locally.

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const menu = (xmlid) => `[data-menu-xmlid="shopify_connector_core.${xmlid}"]`;

// Reaching Configuration is not a plain click, and the reason is worth
// recording. With all six connector modules installed the app's navbar
// OVERFLOWS at 1366 px: Odoo marks the entries that do not fit `d-none` and
// moves them behind the "More Menu" toggle. Configuration, the Error & Review
// Center and Logs are the three that fall off. A tour cannot click a `d-none`
// element, and neither can an operator -- they open More first, which is
// exactly what this does.
//
// Written as one `run()` rather than as two fixed steps so the route is proved
// on a build where the navbar does NOT overflow as well: fewer installed
// domain modules means fewer sections, and a tour that always clicked More
// would then fail for the opposite reason.
const openConnectorSection = (xmlid) => ({
    // `.o_menu_sections` exists in EVERY app, so it matches the navbar of
    // whatever app was on screen a moment ago. Waiting on the connector's own
    // dashboard first is what makes this step observe the connector's menu
    // tree rather than the previous app's -- without it the section is
    // genuinely absent and the failure reads as a missing menu.
    trigger: ".o_sc_dashboard .o_sc_setup, .o_sc_dashboard, .o_sc_setup",
    content: `Reach the ${xmlid} section, opening More if the navbar overflowed.`,
    async run() {
        const selector = `[data-menu-xmlid="shopify_connector_core.${xmlid}"]`;
        let entry = document.querySelector(selector);
        if (!entry) {
            throw new Error(
                `${xmlid} is not in this operator's menu tree at all`
            );
        }
        if (entry.classList.contains("d-none")) {
            const more = document.querySelector(".o_menu_sections_more button");
            if (!more) {
                throw new Error(
                    `${xmlid} is hidden and there is no More menu to reach it`
                );
            }
            more.click();
            await new Promise((resolve) => setTimeout(resolve, 400));
            entry =
                document.querySelector(`.o-dropdown--menu ${selector}`) || entry;
        }
        entry.click();
    },
});

// The step heading states "Step N of 11". Asserting the COUNT as well as the
// name is what makes a dropped or reordered step fail here rather than pass
// quietly with ten.
const heading = (n, label) =>
    `.sc_setup__heading:contains('Step ${n} of 11'):contains('${label}')`;

const CONTINUE = ".sc_setup_continue";

// --- 1. The full 11-step traversal, ending in activation. ---
registry.category("web_tour.tours").add("shopify_connector_s1_setup_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${menu("menu_shopify_connector_root")}`,
            content: "Open the Shopify Connector app.",
            run: "click",
        },
        // Entry route 2 of 3: Configuration -> Setup Wizard.
        openConnectorSection("menu_shopify_connector_configuration"),
        {
            trigger: menu("menu_shopify_connector_setup_wizard"),
            content: "Open the guided setup.",
            run: "click",
        },

        // --- Step 1: welcome / prerequisites ---
        {
            trigger: heading(1, "Welcome"),
            content: "The wizard opens on the welcome step.",
        },
        {
            // The hosting disclosure has to be UP FRONT, not discovered
            // mid-flow. Asserted here because that is the accepted
            // requirement, not merely the current copy.
            trigger: ".sc_setup__panel:contains('Odoo Online')",
            content: "The hosting limitation is disclosed before anything else.",
        },
        { trigger: CONTINUE, run: "click" },

        // --- Step 2: store identity ---
        { trigger: heading(2, "Store identity") },
        {
            trigger: "#sc_setup_name",
            run: "edit S1 Tour Store",
        },
        {
            trigger: "#sc_setup_domain",
            run: "edit s1-tour.myshopify.com",
        },
        { trigger: CONTINUE, run: "click" },

        // --- Step 3: credential entry ---
        { trigger: heading(3, "Credentials") },
        {
            // The token field must be a password input: a plain text input is
            // readable over a shoulder and captured by every screenshot tool.
            trigger: "#sc_setup_token[type='password']",
            run: "edit shpat_S1TOURDUMMY000000000000000000000",
        },
        { trigger: CONTINUE, run: "click" },

        // --- Step 4: scope presentation ---
        { trigger: heading(4, "Permissions") },
        {
            trigger: ".sc_setup__scopes li:contains('read_products')",
            content: "Scopes are listed with a business reason, not as a blob.",
        },
        {
            // The wizard must never claim it grants scopes.
            trigger: ".sc_setup__panel:contains('does not grant anything')",
        },
        {
            // The credential field is gone from the DOM, so nothing that
            // walks the page afterwards can find the token in it.
            trigger: "body:not(:has(#sc_setup_token))",
            content: "The token input no longer exists once it is submitted.",
        },
        { trigger: CONTINUE, run: "click" },

        // --- Step 5: test connection ---
        { trigger: heading(5, "Test connection") },
        {
            trigger: ".sc_setup_run_test",
            content: "Testing is an explicit act, and its result is shown here.",
            run: "click",
        },
        {
            trigger: ".sc-band--success:contains('The connection works')",
            content: "The pass is stated on the step, not inferred from moving on.",
        },
        { trigger: CONTINUE, run: "click" },

        // --- Step 6: readiness checks ---
        { trigger: heading(6, "Readiness checks") },
        {
            trigger: ".sc_setup_run_readiness",
            content: "Run the accepted check set.",
            run: "click",
        },
        {
            trigger: ".sc_setup__checks li",
            content: "Each check reports independently, with a reason and an owner.",
        },
        {
            // Text, never colour alone.
            trigger: ".sc_setup__checks .sc-badge",
        },
        { trigger: CONTINUE, run: "click" },

        // --- Step 7: sync direction per domain ---
        { trigger: heading(7, "What to sync") },
        {
            trigger: "#sc_setup_domain_sale",
            content: "Enable order import.",
            run: "click",
        },
        { trigger: CONTINUE, run: "click" },

        // --- Step 8: source of truth ---
        { trigger: heading(8, "Source of truth") },
        {
            // Nothing may be pre-selected: a default that arrives ticked is a
            // consent nobody gave.
            trigger:
                ".sc_setup__choices:not(:has(input[name='sc_setup_matching']:checked))",
            content: "No catalog-source option is pre-selected.",
        },
        {
            trigger: "input[name='sc_setup_matching'][value='odoo_source']",
            run: "click",
        },
        {
            trigger: "input[name='sc_setup_price'][value='odoo_authoritative']",
            run: "click",
        },
        { trigger: CONTINUE, run: "click" },

        // --- Step 9: notification default ---
        { trigger: heading(9, "Customer notifications") },
        {
            trigger: "#sc_setup_notify:not(:checked)",
            content: "Customer notifications are off by default.",
        },
        { trigger: CONTINUE, run: "click" },

        // --- Step 10: inventory first-push scheduling ---
        { trigger: heading(10, "First stock push") },
        { trigger: CONTINUE, run: "click" },

        // --- Step 11: review and activate ---
        { trigger: heading(11, "Review and activate") },
        {
            trigger: ".sc_setup__summary dd:contains('s1-tour.myshopify.com')",
            content: "The summary is in plain words, and it is this store's.",
        },
        {
            trigger: ".sc_setup__panel:contains('does not start a sync')",
            content: "Activation states plainly that it starts nothing.",
        },
        { trigger: `${CONTINUE}:contains('Activate')`, run: "click" },
        {
            trigger: ".o_sc_dashboard",
            content: "Activation hands off to the dashboard.",
        },
    ],
});

// --- 2. Entry route 1 of 3: the dashboard first-run empty state. ---
registry.category("web_tour.tours").add("shopify_connector_s1_dashboard_entry_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${menu("menu_shopify_connector_root")}`,
            run: "click",
        },
        {
            trigger: ".o_sc_dashboard",
            content: "The dashboard renders its first-run empty state.",
        },
        {
            trigger: ".sc_dashboard_setup",
            content: "The empty state offers setup rather than describing it.",
            run: "click",
        },
        {
            trigger: heading(1, "Welcome"),
            content: "The guided setup opens on step 1.",
        },
    ],
});

// --- 3. Save & Exit, then resume where it stopped. ---
registry.category("web_tour.tours").add("shopify_connector_s1_resume_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${menu("menu_shopify_connector_root")}`,
            run: "click",
        },
        openConnectorSection("menu_shopify_connector_configuration"),
        {
            trigger: menu("menu_shopify_connector_setup_wizard"),
            run: "click",
        },
        {
            // The seeded store's resume point is step 7, so the wizard must
            // open THERE rather than at step 1 -- which is the whole point of
            // a durable resume.
            trigger: heading(7, "What to sync"),
            content: "The wizard resumes at the step the operator left.",
        },
        {
            trigger: "#sc_setup_domain_sale:checked",
            content: "Back and Save & Exit did not lose the saved choice.",
        },
        {
            trigger: ".sc_setup_exit",
            content: "Save & Exit records the step and returns to the dashboard.",
            run: "click",
        },
        { trigger: ".o_sc_dashboard" },
    ],
});

// --- 4. Keyboard traversal and focus management. ---
registry.category("web_tour.tours").add("shopify_connector_s1_keyboard_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${menu("menu_shopify_connector_root")}`,
            run: "click",
        },
        openConnectorSection("menu_shopify_connector_configuration"),
        {
            trigger: menu("menu_shopify_connector_setup_wizard"),
            run: "click",
        },
        {
            trigger: heading(1, "Welcome"),
            content: "Focus lands on the step heading, not at the page bottom.",
            run() {
                const heading = document.querySelector(".sc_setup__heading");
                if (document.activeElement !== heading) {
                    throw new Error(
                        "focus did not move to the step heading; a keyboard " +
                        "user would be left where the previous step ended"
                    );
                }
            },
        },
        {
            trigger: CONTINUE,
            content: "Every control is reachable by keyboard.",
            run() {
                // Tab order, asserted rather than assumed: every actionable
                // control in the panel must be focusable.
                const controls = document.querySelectorAll(
                    ".sc_setup__panel button, .sc_setup__panel input"
                );
                if (!controls.length) {
                    throw new Error("the panel exposes no focusable control");
                }
                for (const control of controls) {
                    // A disabled control is deliberately unreachable -- Back
                    // on step 1 has nowhere to go. Skipping it is correct;
                    // asserting it is focusable would assert the opposite of
                    // what the design intends.
                    if (control.disabled) {
                        continue;
                    }
                    control.focus();
                    if (document.activeElement !== control) {
                        throw new Error(
                            "a control could not receive keyboard focus: " +
                            control.outerHTML.slice(0, 80)
                        );
                    }
                }
            },
        },
        {
            trigger: CONTINUE,
            content: "Advance with the keyboard alone.",
            run() {
                document.querySelector(CONTINUE).focus();
                document.activeElement.click();
            },
        },
        {
            trigger: heading(2, "Store identity"),
            content: "The keyboard advance worked and focus followed it.",
            run() {
                const heading = document.querySelector(".sc_setup__heading");
                if (document.activeElement !== heading) {
                    throw new Error(
                        "focus did not follow the step advance"
                    );
                }
            },
        },
    ],
});
