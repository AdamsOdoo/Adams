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
// resolves, or that the twelve steps appear in the accepted order on screen.
// Those failures only exist in a browser, and they are exactly the ones that
// make a feature look implemented and be unusable.
//
// The traversal tour walks all TWELVE steps in order and finishes by
// activating. It contacts no Shopify store: the test patches the transport
// seam before starting the browser, so the test-connection step's probe is
// answered locally, and no tour here ever admits a location-refresh job that
// would reach a socket.

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const menu = (xmlid) => `[data-menu-xmlid="shopify_connector_core.${xmlid}"]`;

// The premium IA keeps only four first-level homes, so Configuration normally
// fits without overflow. Keep the More fallback because translated labels or
// a narrow viewport can still make Odoo collapse a section.
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

const PHASE_PROGRESS = {
    1: ["Connect", "1 of 5"], 2: ["Connect", "2 of 5"],
    3: ["Connect", "3 of 5"], 4: ["Connect", "4 of 5"],
    5: ["Connect", "5 of 5"], 6: ["Configure", "1 of 4"],
    7: ["Configure", "2 of 4"], 8: ["Configure", "3 of 4"],
    9: ["Configure", "4 of 4"], 10: ["Protect", "1 of 1"],
    11: ["Launch", "1 of 2"], 12: ["Launch", "2 of 2"],
};
const heading = (n, label) => {
    const [phase, progress] = PHASE_PROGRESS[n];
    return `.sc_setup__heading:contains('${phase}'):contains('${progress}'):contains('${label}')`;
};

const CONTINUE = ".sc_setup_continue";

const openSetupWizard = () => [
    stepUtils.showAppsMenuItem(),
    {
        trigger: `.o_app${menu("menu_shopify_connector_root")}`,
        content: "Open the Shopify Connector app.",
        run: "click",
    },
    openConnectorSection("menu_shopify_connector_configuration"),
    {
        trigger: menu("menu_shopify_connector_connections"),
        content: "Open Connections.",
        run: "click",
    },
    {
        trigger: menu("menu_shopify_connector_setup_wizard"),
        content: "Open the guided setup.",
        run: "click",
    },
];

// --- 1. The full 12-step traversal, ending in activation. ---
registry.category("web_tour.tours").add("shopify_connector_s1_setup_tour", {
    url: "/odoo",
    steps: () => [
        ...openSetupWizard(),

        // --- 1: welcome / prerequisites ---
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

        // --- 2: store identity ---
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

        // --- 3: credential entry ---
        { trigger: heading(3, "Credentials") },
        {
            // Wave 5: the step opens on a two-path chooser, defaulting to the
            // Dev Dashboard path a merchant creating an app today actually
            // has. Its guidance states the same-organization requirement and
            // the automatic 24-hour renewal, and must NOT tell this user a
            // token will be shown once -- that is the old path's copy.
            trigger: ".sc_setup__mode--selected:contains('Dev Dashboard app')",
            content: "The Dev Dashboard path is the pre-selected default.",
        },
        {
            trigger: ".sc_setup__panel:contains('same Shopify organization')",
            content: "The same-organization requirement is stated up front.",
        },
        {
            // The client-secret field must be a password input for the same
            // reason the token field always was.
            trigger: "#sc_setup_client_secret[type='password']",
            content: "The Client secret is a password input on the default path.",
        },
        {
            // Switch to the offline-token path the rest of this tour uses.
            trigger: ".sc_setup__mode input[value='offline_access_token']",
            run: "click",
        },
        {
            // The three-value disclosure. An operator who pastes the Client
            // ID gets an authentication failure one step later with no way to
            // tell which of the three values was wrong, so the screen has to
            // say which one it wants and what the other two are not.
            trigger: ".sc_setup__panel:contains('not the Client ID')",
            content: "The token guidance names the Client ID as NOT the token.",
        },
        {
            trigger: ".sc_setup__panel:contains('Client Secret')",
            content: "...and the Client Secret as NOT the token either.",
        },
        {
            // The token field must be a password input: a plain text input is
            // readable over a shoulder and captured by every screenshot tool.
            trigger: "#sc_setup_token[type='password']",
            run: "edit shpat_S1TOURDUMMY000000000000000000000",
        },
        { trigger: CONTINUE, run: "click" },

        // --- 4: scope presentation ---
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
        {
            // The action row is reachable without scrolling to the bottom of
            // this long step -- which is the whole point of it being sticky.
            trigger: CONTINUE,
            content: "Continue is on screen on the longest step.",
            run() {
                const bar = document.querySelector(".sc_setup__actions");
                const rect = bar.getBoundingClientRect();
                if (rect.bottom > window.innerHeight + 1 || rect.top < 0) {
                    throw new Error(
                        "the action row is outside the viewport on the " +
                        "Permissions step; a sticky bar that is not on " +
                        "screen is not sticky"
                    );
                }
            },
        },
        { trigger: CONTINUE, run: "click" },

        // --- 5: test connection ---
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

        // --- 6: what to sync (BEFORE readiness now) ---
        { trigger: heading(6, "What to sync") },
        {
            trigger: "#sc_setup_domain_sale",
            content: "Enable order import.",
            run: "click",
        },
        { trigger: CONTINUE, run: "click" },

        // --- 7: location mapping, conditional ---
        {
            trigger: heading(7, "Location mapping"),
            content: "The conditional step exists and keeps its position.",
        },
        {
            // Inventory was not enabled, so this step is Not required -- and
            // it says so rather than vanishing. A step that disappeared would
            // renumber every step after it.
            trigger: ".sc_setup_location_skipped:contains('Not required')",
            content: "A skipped step explains itself instead of disappearing.",
        },
        { trigger: CONTINUE, run: "click" },

        // --- 8: source of truth ---
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

        // --- 9: notification default ---
        { trigger: heading(9, "Customer notifications") },
        {
            trigger: "#sc_setup_notify:not(:checked)",
            content: "Customer notifications are off by default.",
        },
        { trigger: CONTINUE, run: "click" },

        // --- 10: inventory first-push scheduling ---
        { trigger: heading(10, "First stock push") },
        { trigger: CONTINUE, run: "click" },

        // --- 11: final readiness, AFTER every choice it reads ---
        { trigger: heading(11, "Final readiness") },
        {
            // Entering the step evaluated the CURRENT configuration: the
            // results are on screen without anybody pressing anything.
            trigger: ".sc_setup__checks li",
            content: "Entering the step ran the checks against what is saved.",
        },
        {
            // Text, never colour alone, and the corrected wording.
            trigger: ".sc_setup__checks li:contains('Sync features selected')",
            content: "The domain check reads as a feature selection, not an error.",
        },
        {
            // Inventory is off, so the location check is Not required rather
            // than a green Passed for something nobody examined.
            trigger:
                ".sc_setup__checks li:contains('Inventory location mapping')" +
                ":contains('Not required')",
            content: "A check for a disabled domain is Not required, not Passed.",
        },
        { trigger: CONTINUE, run: "click" },

        // --- 12: review and activate ---
        { trigger: heading(12, "Review and activate") },
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
            trigger: ".sc_setup__complete:contains('is connected')",
            content: "Activation closes with a purposeful completion state.",
        },
        {
            trigger: ".sc_setup_dashboard:contains('Go to overview')",
            content: "The completion screen offers one clear primary next step.",
            run: "click",
        },
        {
            trigger: ".o_sc_dashboard",
            content: "The primary completion action opens the overview.",
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
        ...openSetupWizard(),
        {
            // The seeded store's resume point is the `directions` step, so the
            // wizard must open THERE rather than at step 1 -- which is the
            // whole point of a durable resume. The store was seeded with the
            // PRE-Wave-5 numeric progress and no semantic key, so this also
            // proves the warm translation reaches the browser.
            trigger: heading(6, "What to sync"),
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

// --- 4. Keyboard traversal, focus management and the sticky action row. ---
registry.category("web_tour.tours").add("shopify_connector_s1_keyboard_tour", {
    url: "/odoo",
    steps: () => [
        ...openSetupWizard(),
        {
            trigger: heading(1, "Welcome"),
            content: "Focus lands on the step heading, not at the page bottom.",
            run() {
                const stepHeading = document.querySelector(".sc_setup__heading");
                if (document.activeElement !== stepHeading) {
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
                    ".sc_setup__panel button, .sc_setup__panel input, " +
                    ".sc_setup__actions button"
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
            trigger: ".sc_setup__actions",
            content:
                "Every action-row control reserves clearance so focus cannot " +
                "land underneath the sticky bar.",
            run() {
                const controls = document.querySelectorAll(
                    ".sc_setup__actions button:not([disabled])"
                );
                if (!controls.length) {
                    throw new Error("the action row exposes no enabled control");
                }
                for (const control of controls) {
                    const margin = getComputedStyle(control)
                        .scrollMarginBlockEnd;
                    if (!margin || parseFloat(margin) <= 0) {
                        throw new Error(
                            "an action-row control reserves no scroll " +
                            "clearance, so keyboard focus can land under the " +
                            "sticky bar: " + control.outerHTML.slice(0, 80)
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
                const stepHeading = document.querySelector(".sc_setup__heading");
                if (document.activeElement !== stepHeading) {
                    throw new Error(
                        "focus did not follow the step advance"
                    );
                }
            },
        },
    ],
});

// --- 5. The location-mapping step with real cached locations. ---
//
// Inventory IS enabled for this store and three Shopify locations are already
// in the cache, one of them already mapped. That is the state the step exists
// for, and none of it can be observed from a server test: the mapped/unmapped
// distinction, the visible GID, the refresh state and the create control are
// all rendering.
registry.category("web_tour.tours").add("shopify_connector_s1_location_tour", {
    url: "/odoo",
    steps: () => [
        ...openSetupWizard(),
        {
            trigger: heading(7, "Location mapping"),
            content: "The wizard resumes on the location step.",
        },
        // --- Mapped state is asserted by EXACT attribute, never by substring.
        //
        //     hoot-dom's `:contains()` is a case-insensitive substring match, so
        //     `:contains('Mapped')` also matches "Not mapped". Every assertion
        //     here used to pass whichever badge was rendered -- including the
        //     final one below, which is supposed to prove a mapping was created
        //     and passed just as happily when the create had failed. The
        //     `data-mapped` attribute the template now carries is exact.
        {
            trigger: ".sc_setup__location[data-mapped='1']:contains('Tour Warehouse A')",
            content: "An already-mapped location says so.",
        },
        {
            trigger: ".sc_setup__location[data-mapped='0']:contains('Tour Warehouse B')",
            content:
                "An unmapped location is never described as synchronised.",
        },
        {
            trigger: ".sc_setup__location[data-mapped='0']:contains('Tour Warehouse C')",
            content: "Every cached location has a visible mapped state.",
        },
        {
            // The human-readable badge is still checked, on the row the
            // attribute has already identified -- so the copy cannot silently
            // disagree with the state.
            trigger: ".sc_setup__location[data-mapped='1'] .sc-badge--success",
            content: "The mapped row's badge is the success badge.",
        },
        {
            trigger: ".sc_setup__location-gid:contains('gid://shopify/Location/')",
            content: "The Shopify identity is shown, read-only.",
        },
        {
            trigger: ".sc_setup_refresh_locations",
            content: "A refresh control exists on the step itself.",
        },

        // --- Wave 5: the bounded server-side search, driven for real. The
        //     reachability BOUND (a row past the first page) is a server
        //     test; what the browser proves is that the search control
        //     genuinely filters through the RPC and genuinely clears.
        {
            trigger: ".sc_setup_search_shopify",
            run: "edit Warehouse C",
        },
        { trigger: ".sc_setup_search_shopify_go", run: "click" },
        {
            // The Shopify counter specifically. Two elements shared the
            // `.sc_setup__showing` class, so this could previously have been
            // satisfied by the Odoo counter instead.
            trigger: ".sc_setup__showing--shopify:contains('Showing 1 of 1')",
            content: "The search narrowed the list, with an honest count.",
        },
        {
            trigger: ".sc_setup__locations:not(:contains('Tour Warehouse A'))",
            content: "Rows that do not match are genuinely gone, not hidden.",
        },
        {
            trigger: ".sc_setup__location:contains('Tour Warehouse C')",
            content: "The matching row is the one shown.",
        },
        { trigger: ".sc_setup_search_shopify_clear", run: "click" },
        {
            trigger: ".sc_setup__location:contains('Tour Warehouse A')",
            content: "Clearing the search restores the full first page.",
        },

        {
            // Create a second mapping through the governed route.
            trigger: "#sc_setup_map_shopify",
            run: "select gid://shopify/Location/TOURB",
        },
        {
            // The eligible-Odoo-location assertion lives INSIDE this step's
            // `run()` rather than as its own `:not([value=''])` trigger. An
            // `<option>` inside a closed `<select>` has no layout box, so
            // hoot-dom correctly reports it as not visible and a trigger on
            // one can only ever time out -- it would be asserting that a
            // dropdown is open, which is not the claim.
            trigger: "#sc_setup_map_odoo",
            content: "At least one eligible Odoo location is offered, and a "
                     + "location not already mapped elsewhere is chosen.",
            run() {
                const select = document.querySelector("#sc_setup_map_odoo");
                // Pick a location that is NOT already the target of another
                // Shopify mapping. `UNIQUE(store_id, odoo_location_id)` refuses a
                // second mapping onto the same Odoo location, so taking the
                // first option with a value picked whichever row the fixture
                // happened to order first -- on a clean install that is the
                // location Warehouse A is already mapped to, the create was
                // refused, and the substring assertion below passed anyway. The
                // rows already on screen name their current Odoo targets, so the
                // set to avoid is readable from the DOM.
                const taken = new Set(
                    Array.from(
                        document.querySelectorAll(
                            ".sc_setup__location[data-mapped='1'] " +
                            ".sc_setup__location-target"
                        )
                    ).map((el) => el.textContent.replace(/^\s*Odoo location:\s*/, "").trim())
                );
                const option = Array.from(select.options).find(
                    (o) => o.value && !taken.has(o.textContent.trim())
                );
                if (!option) {
                    throw new Error(
                        "no ELIGIBLE Odoo location is offered: every option is " +
                        "already mapped to another Shopify location"
                    );
                }
                select.value = option.value;
                select.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        { trigger: ".sc_setup_create_mapping", run: "click" },
        {
            // Exact state, not a substring that "Not mapped" also satisfies.
            // The DATABASE consequence is asserted by the Python test that
            // drives this tour; this proves the surface reflects it.
            trigger: ".sc_setup__location[data-mapped='1']:contains('Tour Warehouse B')",
            content: "The mapping was created through the sanctioned service.",
        },
        {
            // And no refusal was silently rendered instead.
            trigger: ".o_sc_setup:not(:has(.sc_setup__error))",
            content: "The mapping was created without a server refusal.",
        },
    ],
});

// --- 6. A blocking readiness row, and its deep link BY STEP KEY. ---
registry.category("web_tour.tours").add("shopify_connector_s1_readiness_tour", {
    url: "/odoo",
    steps: () => [
        ...openSetupWizard(),
        {
            trigger: heading(11, "Final readiness"),
            content: "The wizard resumes on the final-readiness step.",
        },
        {
            trigger:
                ".sc_setup__checks li:contains('Inventory location mapping')" +
                ":contains('Must be fixed')",
            content:
                "Inventory is on and nothing is mapped, so the check blocks.",
        },
        {
            // The deep link carries the semantic key, not a position.
            trigger: ".sc_setup_check_action[data-step-key='location_mapping']",
            content: "The fix control addresses the step by key.",
            run: "click",
        },
        {
            trigger: heading(7, "Location mapping"),
            content: "The deep link landed on the location step.",
        },
    ],
});
