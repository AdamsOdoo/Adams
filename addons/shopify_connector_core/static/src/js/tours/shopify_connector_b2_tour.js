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
            trigger: `${DIALOG} .alert-info[role='status']`,
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
        {
            trigger: `${DIALOG} div[name='account_tax_id'] input`,
            content: "Choose the Odoo tax it means.",
            run: "click",
        },
        {
            trigger: ".ui-autocomplete .ui-menu-item, .o-autocomplete--dropdown-menu li",
            content: "Pick the offered tax.",
            run: "click",
        },
        focusStep(
            `${DIALOG} footer button[name='action_confirm']`,
            "The confirmation control takes keyboard focus."
        ),
        keyboardActivateStep(
            `${DIALOG} footer button[name='action_confirm']`,
            "Map the tax and resume the order, by keyboard."
        ),
        {
            trigger: ".o_form_view .o_field_widget[name='account_tax_id']",
            content: "The resulting mapping is shown.",
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
            trigger: `${DIALOG} .alert-info[role='status']`,
            content:
                "The dialog says why the import stopped before asking anything.",
        },
        {
            trigger: `${DIALOG} div[name='sku_preview']:contains('TOUR-DUP')`,
            content: "The identifier Shopify sent is read from its own field.",
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
        {
            trigger: `${DIALOG} div[name='selected_template_id'] input`,
            content: "Choose the Odoo product this Shopify product means.",
            run: "click",
        },
        {
            trigger: ".ui-autocomplete .ui-menu-item, .o-autocomplete--dropdown-menu li",
            content: "Pick one of the eligible candidates.",
            run: "click",
        },
        focusStep(
            `${DIALOG} footer button[name='action_confirm']`,
            "The confirmation control takes keyboard focus."
        ),
        keyboardActivateStep(
            `${DIALOG} footer button[name='action_confirm']`,
            "Match and resume the import, by keyboard."
        ),
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
