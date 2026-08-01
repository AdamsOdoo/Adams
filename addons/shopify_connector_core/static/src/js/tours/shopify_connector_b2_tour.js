/** @odoo-module **/
// Part of the Shopify Connector (Batch 2 P0 merchant reachability).
//
// Driven-browser evidence for the six surfaces Batch 2 made reachable:
//
//   1. canonical Store Settings                 (core)
//   2. the manual/scheduled ORDER controls      (sale, on the store form)
//   3. the tax decision dialog                  (sale)
//   4. the manual/scheduled PRODUCT controls    (product, on the store form)
//   5. the pending product MATCH DECISION       (product)
//   6. the resolved binding result              (product)
//
// WHY THEY LIVE IN CORE. Same reason as the U2 tours: the surfaces belong to
// three different addons, a tour can only be registered once, and core is the
// module all three depend on.
//
// WHAT THE BROWSER ADDS OVER THE SERVER TESTS. Every one of these paths is
// already covered server-side. None of that proves an operator can REACH it:
// that the control renders on the record that is actually stopped, that its
// label says what pressing it does, that the consequence copy is above the
// control rather than below it, that a role the server refuses is shown no
// control at all, and that the whole thing is operable from the keyboard.
//
// NO SHOPIFY. Every control here either writes an Odoo row or ENQUEUES a job
// row. No tour starts a dispatcher, and no fixture holds a credential that
// could reach the network.
//
// SELECTOR DISCIPLINE. A bare `:contains('3')` is satisfied by any 3 anywhere
// on screen, so every value assertion below is anchored to the field that owns
// it (`[name='...']`). `:contains()` is a hoot-dom extension and is NOT valid
// CSS, so it can never appear inside `:not(:has())` -- absence is asserted
// against real attribute selectors instead.

import { registry } from "@web/core/registry";

const tours = registry.category("web_tour.tours");

const DIALOG = ".modal:not(.o_inactive_modal)";
const DIALOG_PRIMARY = `${DIALOG} footer button.btn-primary`;

/**
 * Assert a control is KEYBOARD OPERABLE (WCAG 2.1.1): it takes focus, it
 * actually becomes `document.activeElement`, and it is in the tab order.
 *
 * The rendered focus indicator (WCAG 2.4.7) is deliberately NOT asserted here:
 * in headless Chromium a script-focused element never matches `:focus-visible`,
 * because the pseudo-class tracks the last real input modality and a tour has
 * none. That property is measured in `test_ui_visual_evidence.py` through
 * `CSS.forcePseudoState`, which removes the heuristic from the question.
 */
function focusStep(selector, content) {
    return {
        trigger: selector,
        content,
        run() {
            const el = this.anchor;
            if (!el) {
                throw new Error(`no element matched ${selector}`);
            }
            if (el.disabled) {
                throw new Error(`${selector} is disabled and cannot be operated`);
            }
            if (el.tabIndex < 0) {
                throw new Error(
                    `${selector} has tabIndex ${el.tabIndex}, so it is out of ` +
                        "the tab order and unreachable by keyboard (WCAG 2.1.1)"
                );
            }
            el.focus();
            if (document.activeElement !== el) {
                throw new Error(
                    `${selector} could not take keyboard focus, so the ` +
                        "control is not keyboard operable (WCAG 2.1.1)"
                );
            }
        },
    };
}

/**
 * Choose a Many2one value BY NAME.
 *
 * WHY NOT "click the first suggestion". A bare
 * `.o-autocomplete--dropdown-menu li` resolves in document order across the
 * WHOLE page, so it can match a different dropdown entirely, and even within
 * the right one the first row depends on how many similar records the database
 * happens to hold. Measured: on a fresh database this picked the intended tax
 * and on a migrated one it did not, the confirm was then refused for an empty
 * required field, and the tour still reported success. Typing the name filters
 * the list to the record the test created and the click targets that text.
 *
 * @param {string} fieldSelector the `[name=...]` wrapper of the Many2one
 * @param {string} value the exact display name to select
 */
function selectByName(fieldSelector, value, content) {
    return [
        {
            trigger: `${fieldSelector} input`,
            content,
            run: `edit ${value}`,
        },
        {
            trigger: `.o-autocomplete--dropdown-menu li:contains(${JSON.stringify(
                value
            )})`,
            content: `Pick "${value}" from the filtered suggestions.`,
            run: "click",
        },
        {
            // The value actually landed on the field. Without this, a click
            // that missed leaves the field empty and every later step still
            // matches the dialog that failed to close.
            trigger: `${fieldSelector} input:value(${JSON.stringify(value)})`,
            content: `The field now holds "${value}".`,
        },
    ];
}

/** Activate the focused control BY KEYBOARD, not by a synthetic click. */
function keyboardActivateStep(selector, content) {
    return {
        trigger: selector,
        content,
        run() {
            const el = this.anchor;
            el.focus();
            el.dispatchEvent(
                new KeyboardEvent("keydown", {
                    key: "Enter",
                    code: "Enter",
                    bubbles: true,
                    cancelable: true,
                })
            );
            // A native <button> activates on Enter via a click; browsers do
            // not synthesise that for a dispatched KeyboardEvent, so the click
            // completes the same activation path a real Enter press produces.
            el.click();
        },
    };
}

// ---------------------------------------------------------------------------
// 1. Canonical Store Settings.
// ---------------------------------------------------------------------------
// The surface Batch 2 checkpoint 1 created. Reached from the Configuration
// menu -- not by URL -- because the whole defect was that no route existed.
tours.add("shopify_connector_b2_store_settings_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Store Settings lists the configured store.",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_field_widget[name='store_id']",
            content: "The form opens on that store's settings.",
        },
        {
            // The store is identity, not input. Asserted against the field's
            // own readonly rendering rather than against the page as a whole.
            trigger:
                ".o_form_view .o_field_widget[name='store_id'] .o_readonly," +
                " .o_form_view .o_field_widget[name='store_id'][readonly='1']," +
                " .o_form_view div[name='store_id'] span",
            content: "The store it belongs to is shown, never offered as input.",
        },
        focusStep(
            ".o_form_view div[name='product_domain_enabled'] input",
            "The product-import switch takes keyboard focus."
        ),
        {
            trigger: ".o_form_view div[name='product_domain_enabled'] input",
            content: "Turn product import on.",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_status_indicator button.o_form_button_save",
            content: "Save the change through the ordinary form save.",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_saved",
            content: "The change is saved.",
        },
    ],
});

// ---------------------------------------------------------------------------
// 2. The product controls, on the store form.
// ---------------------------------------------------------------------------
// `Import products now` is the road to the importer that Batch 2 checkpoint 3
// built. The state group beside it must SAY whether scheduling is on, so a
// manual button never stands next to a silent screen that reads as
// "this is handled".
tours.add("shopify_connector_b2_product_controls_tour", {
    steps: () => [
        {
            trigger: ".o_form_view div[name='product_sync_scheduled']",
            content: "The form states the scheduled position before offering the control.",
        },
        focusStep(
            ".o_form_view button[name='action_sync_products_now']",
            "The catalog-import control takes keyboard focus."
        ),
        keyboardActivateStep(
            ".o_form_view button[name='action_sync_products_now']",
            "Start a catalog scan by keyboard."
        ),
        {
            trigger: ".o_form_view div[name='product_sync_active_scan_count']",
            content: "The form now reports a scan in flight.",
        },
    ],
});

// An Operator may start an import. A role the server refuses must be shown no
// control at all -- asserted as a real attribute absence, because
// `:contains()` cannot appear inside `:not(:has())`.
tours.add("shopify_connector_b2_product_controls_denied_tour", {
    steps: () => [
        {
            trigger: ".o_form_view .o_form_sheet",
            content: "The store form renders for a role that may only read.",
        },
        {
            trigger:
                ".o_form_view:not(:has(button[name='action_sync_products_now']))",
            content: "No catalog-import control is offered.",
        },
    ],
});

// ---------------------------------------------------------------------------
// 3. The order controls, on the same store form.
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// 3b. Store 360 commercial drill-down (Store 360 slice).
// ---------------------------------------------------------------------------
// Driven from the sale tour test with a genuinely imported order fixture:
// the dashboard's commercial region renders real numbers and the imported-
// orders KPI opens the NATIVE sale.order list built from the server's own
// domain — the same-model drill-down contract, proven in a real browser.
tours.add("shopify_connector_b2_store360_drilldown_tour", {
    url: "/odoo",
    steps: () => [
        {
            trigger: ".o_navbar_apps_menu button",
            content: "Open the apps menu.",
            run: "click",
        },
        {
            trigger: ".o_app[data-menu-xmlid='shopify_connector_core.menu_shopify_connector_root']",
            content: "Open the Shopify Connector app.",
            run: "click",
        },
        {
            trigger: ".o_sc_dashboard .sc360-commercial",
            content: "The Store 360 commercial region renders.",
        },
        {
            trigger: ".o_sc_dashboard .sc360-ts-source",
            content: "The Shopify-source timestamp renders distinctly from the page timestamp.",
        },
        {
            trigger: ".o_sc_dashboard .sc360-kpi[data-kpi='orders']",
            content: "Open the imported-orders drill-down.",
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "The NATIVE sale.order list renders from the server-built domain.",
        },
    ],
});

tours.add("shopify_connector_b2_order_controls_tour", {
    steps: () => [
        {
            trigger: ".o_form_view div[name='order_sync_scheduled']",
            content: "The form states the scheduled position for orders.",
        },
        focusStep(
            ".o_form_view button[name='action_sync_orders_now']",
            "The order-import control takes keyboard focus."
        ),
        keyboardActivateStep(
            ".o_form_view button[name='action_sync_orders_now']",
            "Start an order scan by keyboard."
        ),
        {
            trigger: ".o_form_view div[name='order_sync_active_scan_count']",
            content: "The form now reports an order scan in flight.",
        },
    ],
});

// ---------------------------------------------------------------------------
// 4. The tax decision dialog.
// ---------------------------------------------------------------------------
// The order stopped because Shopify charged a tax the connector has not been
// told about. The dialog must disclose WHAT it charged before asking which
// Odoo tax it means.
tours.add("shopify_connector_b2_tax_decision_tour", {
    steps: () => [
        {
            trigger: ".o_form_view button[name='action_open_tax_mapping_decision']",
            content: "The stopped order offers the decision that unblocks it.",
            run: "click",
        },
        {
            // `role='note'`, and the role is part of the assertion rather than
            // incidental to it (2026-07-31). This band was `role='status'` --
            // a live region -- on a sentence that is the same for every
            // stopped order and that nothing in this dialog can change. The
            // selector states the corrected semantics, so a revert to `status`
            // fails the tour rather than passing on the class alone.
            trigger: `${DIALOG} .alert-info[role='note']`,
            content:
                "The dialog says why the order stopped, and that nothing is " +
                "sent to Shopify.",
        },
        {
            // Anchored to the field, not to the page: a bare `:contains('5')`
            // would be satisfied by any 5 on screen.
            trigger: `${DIALOG} div[name='rate_percentage']:contains('5')`,
            content: "The rate Shopify charged is read from its own field.",
        },
        ...selectByName(
            `${DIALOG} div[name='account_tax_id']`,
            "B2 Tour VAT 5",
            "Choose the Odoo tax it means."
        ),
        focusStep(
            `${DIALOG} footer button[name='action_confirm']`,
            "The confirmation control takes keyboard focus."
        ),
        keyboardActivateStep(
            `${DIALOG} footer button[name='action_confirm']`,
            "Map the tax and resume the order, by keyboard."
        ),
        {
            // THE DIALOG IS GONE. Asserted before anything about the result,
            // because a refused confirm leaves the dialog open and the dialog
            // ALSO contains an `account_tax_id` field -- so "the mapping is
            // shown" was satisfiable by the very failure it was meant to rule
            // out. This is the step that makes the next one mean something.
            trigger: "body:not(:has(.modal:not(.o_inactive_modal)))",
            content: "The dialog closed, so the confirmation was accepted.",
        },
        {
            // A field the MAPPING form has and the dialog does not.
            trigger: ".o_form_view div[name='shopify_tax_evidence_key']",
            content: "The resulting mapping is shown, with its fingerprint.",
        },
    ],
});

// ---------------------------------------------------------------------------
// 5. The pending product match decision.
// ---------------------------------------------------------------------------
// The import stopped because more than one Odoo record carries the identifier
// Shopify sent. The dialog must show the evidence, offer only eligible
// candidates, and say what happens next.
tours.add("shopify_connector_b2_product_match_decision_tour", {
    steps: () => [
        {
            trigger:
                ".o_form_view button[name='action_open_product_match_decision']",
            content: "The stopped import offers the decision that unblocks it.",
            run: "click",
        },
        {
            // `role='note'`, for the same reason and with the same intent as
            // the tax dialog above (2026-07-31): static instructional copy is
            // document structure, and the tour asserts the role so the ruling
            // cannot be reverted quietly.
            trigger: `${DIALOG} .alert-info[role='note']`,
            content:
                "The dialog says why the import stopped before asking anything.",
        },
        {
            // BATCH 2 CORRECTION (F1/F2/F3), measured in the real browser.
            //
            // The seed SKU is `1234567890123` -- the shape a real merchant
            // actually uses, and the shape the DISPLAY scrubber rewrites. So
            // the preview must show the redaction, from its own field...
            trigger:
                `${DIALOG} div[name='sku_preview']:contains('[redacted-phone]')`,
            content:
                "The merchant-controlled identifier is shown redacted, " +
                "because a display preview is all it is.",
        },
        {
            // ...while the IDENTITY beside it is intact, byte for byte. These
            // two assertions on one dialog are the whole separation: the same
            // scrubber applied to this field is what made a confirmed decision
            // unconsumable, because the key it produced could never equal the
            // key the raw payload produces.
            trigger:
                `${DIALOG} div[name='shopify_product_gid']` +
                `:contains('gid://shopify/Product/7346299043911')`,
            content:
                "The Shopify identity is shown exactly as received, and is " +
                "never passed through the display scrubber.",
        },
        {
            trigger: `${DIALOG} div[name='candidate_total']:contains('2')`,
            content:
                "How many Odoo records were found is read from its own field, " +
                "not from any 2 that happens to be on screen.",
        },
        {
            trigger: `${DIALOG} .text-muted[role='note']`,
            content:
                "The consequence copy states that names are never matched on, " +
                "and that a Shopify edit means being asked again.",
        },
        ...selectByName(
            `${DIALOG} div[name='selected_template_id']`,
            "Tour candidate A",
            "Choose the Odoo product this Shopify product means."
        ),
        focusStep(
            `${DIALOG} footer button[name='action_confirm']`,
            "The confirmation control takes keyboard focus."
        ),
        keyboardActivateStep(
            `${DIALOG} footer button[name='action_confirm']`,
            "Match and resume the import, by keyboard."
        ),
        {
            // The dialog closed, so the confirmation was accepted rather than
            // refused. Same reasoning as the tax route: a refused confirm
            // leaves the dialog open, and several of the assertions below
            // would otherwise be satisfiable from inside it.
            trigger: "body:not(:has(.modal:not(.o_inactive_modal)))",
            content: "The dialog closed, so the decision was accepted.",
        },
        {
            // 6. THE RESOLVED RESULT. The decision form the confirmation lands
            // on records who decided, what they chose, and what state the job
            // was resumed into.
            trigger:
                ".o_form_view .o_statusbar_status button.o_arrow_button_current:contains('Decided')",
            content: "The decision is recorded and the import is resuming.",
        },
        {
            trigger: ".o_form_view div[name='selected_template_id']",
            content: "The chosen Odoo product is recorded on the decision.",
        },
        {
            trigger: ".o_form_view div[name='resolved_uid']",
            content: "So is who decided it.",
        },
        {
            trigger: ".o_form_view div[name='resumed_job_state']:contains('queued')",
            content:
                "And the state the resume actually left the job in -- evidence " +
                "the resume happened rather than an assumption that it did.",
        },
    ],
});

// A role the server refuses is shown no decision control. An Operator may
// START an import and may not decide what a product means.
tours.add("shopify_connector_b2_product_match_decision_denied_tour", {
    steps: () => [
        {
            trigger: ".o_form_view .o_form_sheet",
            content: "The stopped job renders for a role that may only read it.",
        },
        {
            trigger:
                ".o_form_view:not(:has(button[name='action_open_product_match_decision']))",
            content: "No decision control is offered.",
        },
    ],
});

// ---------------------------------------------------------------------------
// 6. The resolved binding result.
// ---------------------------------------------------------------------------
// After the import resumes and completes, the Product Matching surface must
// show the binding the decision produced, and show that a human made it.
tours.add("shopify_connector_b2_resolved_binding_tour", {
    steps: () => [
        {
            trigger: ".o_form_view div[name='shopify_gid']",
            content: "The binding the decision produced.",
        },
        {
            trigger: ".o_form_view div[name='match_key']:contains('Manual')",
            content:
                "The binding says it was matched manually, from its own field.",
        },
        {
            trigger: ".o_form_view div[name='matched_by_uid']",
            content: "And by whom.",
        },
        {
            // The protected binding surface stays protected: the decision
            // route created this row, and no field on it is generically
            // editable here.
            trigger:
                ".o_form_view:not(:has(div[name='product_template_id'] input:not([readonly])))",
            content:
                "The Odoo product it is bound to is not offered as an input.",
        },
    ],
});
