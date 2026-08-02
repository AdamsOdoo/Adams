/** @odoo-module **/
// Part of the Shopify Connector (U2 domain operator surfaces).
//
// ACTION tours for U2. The navigation tour in `shopify_connector_u2_tour.js`
// proves every U2 surface renders and is reachable; it is read-only by
// construction and deliberately clicks nothing that writes. That left the
// four sanctioned U2 operator controls with no driven-browser evidence at all,
// which is the gap this file closes:
//
//   1. Approve Payment          -> action_approve_manual_gateway_order
//   2. Confirm First Push       -> action_confirm_first_push
//   3. Verify inventory now     -> action_recheck_inventory_pair
//   4. Change inventory push    -> action_set_push_enabled
//
// These DO write, and two of them enqueue a job. That is exactly why they need
// a browser test rather than only a server-side one: three real UI/server
// disagreements were found here by pressing the controls, and none of them is
// visible to a test that calls the method directly.
//
//   * `Confirm First Push` was shown only while `first_push_state == 'pending'`
//     -- the one state `action_confirm_first_push` refuses -- and hidden in
//     `previewed`, the one state it accepts. The sanctioned confirmation was
//     unreachable from the shipped UI.
//   * `Verify inventory now` was gated on Operator while its service admits only
//     Reviewer or Administrator.
//   * `Change inventory push` was gated on Operator while the transient wizard behind it
//     was ACL'd to Administrator alone, so a Connector User was refused at the
//     dialog rather than at the control.
//
// Each tour runs against fixtures seeded by its own `HttpCase`, inside that
// test's transaction, and is rolled back with it. No step contacts Shopify:
// the actions these controls reach either write Odoo rows or ENQUEUE a job
// row, and job execution is a separate cron/dispatcher concern that no tour
// starts.
//
// WHY THEY LIVE IN CORE. Same reason as the navigation tour: the surfaces
// belong to `shopify_connector_sale` and `shopify_connector_inventory`, a tour
// can only be registered once, and core is the module both depend on.
//
// NOTE ON SELECTORS. An XML `type="action"` button renders its `name`
// attribute as the RESOLVED numeric action id, so `button[name^='action_']`
// matches nothing for a wizard-opening button. Those are targeted by the label
// an operator actually reads. `type="object"` buttons keep their method name
// and are targeted by it, because the method name is the thing worth pinning.

import { registry } from "@web/core/registry";

const tours = registry.category("web_tour.tours");

// Odoo renders a `confirm="..."` button through the confirmation dialog; the
// accept control is the dialog's primary button.
const DIALOG = ".modal:not(.o_inactive_modal)";
const DIALOG_PRIMARY = `${DIALOG} footer button.btn-primary`;

/**
 * Assert an element is KEYBOARD OPERABLE (WCAG 2.1.1): it takes focus, it
 * actually becomes `document.activeElement`, and it is in the tab order rather
 * than being reachable only by script.
 *
 * WHAT THIS DELIBERATELY DOES NOT ASSERT, AND WHERE THAT LIVES INSTEAD.
 * It does not assert `:focus-visible`. In headless Chromium 141 a `<button>`
 * focused from script never matches `:focus-visible` -- measured directly:
 * plain `focus()`, `focus({focusVisible: true})` and click-then-focus all
 * return false -- because the pseudo-class tracks the last *real* input
 * modality, and a tour has none. Asserting it here would either fail on a
 * correct focus ring or pass by accident depending on what the previous step
 * happened to click, and an accessibility assertion that depends on that is
 * not evidence.
 *
 * The rendered focus indicator (WCAG 2.4.7) is proven in
 * `shopify_connector_core/tests/test_ui_visual_evidence.py`, which drives the
 * same controls through the DevTools protocol, forces `:focus-visible` with
 * `CSS.forcePseudoState`, reads the resulting computed style, and MEASURES the
 * indicator's contrast against SC 1.4.11. That is a stronger instrument than a
 * pseudo-class match, and it is the one that produces the durable artifact.
 *
 * @param {string} selector
 */
function focusStep(selector, content) {
    return {
        trigger: selector,
        content,
        run() {
            // `this.anchor` is the element the tour framework already matched
            // for `trigger`. It must be used rather than re-querying, because
            // `:contains()` is a hoot-dom extension and is NOT valid CSS --
            // `document.querySelector` with it throws or matches nothing.
            const el = this.anchor;
            if (!el) {
                throw new Error(`no element matched ${selector}`);
            }
            if (el.disabled) {
                throw new Error(`${selector} is disabled and cannot be operated`);
            }
            if (el.tabIndex < 0) {
                throw new Error(
                    `${selector} has tabIndex ${el.tabIndex}, so it is out of the ` +
                        "tab order and unreachable by keyboard (WCAG 2.1.1)"
                );
            }
            el.focus();
            if (document.activeElement !== el) {
                throw new Error(
                    `${selector} could not take keyboard focus, so the control ` +
                        "is not keyboard operable (WCAG 2.1.1)"
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
            // not synthesise that for a dispatched KeyboardEvent, so the
            // click is issued here to complete the same activation path a
            // real Enter press produces.
            el.click();
        },
    };
}

// ---------------------------------------------------------------------------
// 1. First-push confirmation (S11) -- the heaviest ceremony in the module.
// ---------------------------------------------------------------------------
// Walks the First-Push Guard queue, which must LIST a `previewed` row (it
// listed only `pending` before, so the queue could never reach a confirmable
// row), opens it, and confirms by keyboard.
tours.add("shopify_connector_u2_first_push_confirm_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "The guard queue lists the pair awaiting confirmation.",
            run: "click",
        },
        {
            trigger: ".o_form_view .alert-warning:contains('Waiting for a first-push confirmation')",
            content:
                "The form discloses that nothing has been pushed yet, before " +
                "offering the control.",
        },
        focusStep(
            ".o_form_view button[name='action_confirm_first_push']",
            "The confirmation control takes keyboard focus and shows a focus ring."
        ),
        keyboardActivateStep(
            ".o_form_view button[name='action_confirm_first_push']",
            "Activate the confirmation by keyboard."
        ),
        {
            trigger: `${DIALOG}:contains('This is the FIRST stock push')`,
            content:
                "The consequence is named in words before anything is written.",
        },
        {
            trigger: DIALOG_PRIMARY,
            content: "Accept the first-push consequence.",
            run: "click",
        },
        {
            trigger:
                ".o_form_view .o_statusbar_status button.o_arrow_button_current:contains('Confirmed')",
            content: "The pair is now confirmed.",
        },
        {
            trigger: ".o_form_view:not(:has(button[name='action_confirm_first_push']))",
            content:
                "The control is gone once it has been used, so a second " +
                "confirmation cannot be pressed.",
        },
    ],
});

// A pair still awaiting its PREVIEW must offer no confirmation control at all:
// the server refuses that state, and a button that can only raise an error is
// worse than no button.
tours.add("shopify_connector_u2_first_push_pending_has_no_control_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Open the pair that has not been previewed yet.",
            run: "click",
        },
        {
            trigger: ".o_form_view .alert-warning:contains('Waiting for a first-push preview')",
            content: "The form says what is missing and what happens next.",
        },
        {
            trigger: ".o_form_view:not(:has(button[name='action_confirm_first_push']))",
            content:
                "No confirmation control is offered in a state the server refuses.",
        },
    ],
});

// The same surface, opened by a role the server refuses. The control must be
// ABSENT rather than present-and-failing.
tours.add("shopify_connector_u2_first_push_denied_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Open the pair awaiting confirmation as a non-reviewer.",
            run: "click",
        },
        {
            trigger: ".o_form_view .alert-warning:contains('Waiting for a first-push confirmation')",
            content: "The disclosure is still readable -- the role may read.",
        },
        {
            trigger: ".o_form_view:not(:has(button[name='action_confirm_first_push']))",
            content:
                "The confirmation control is not offered to a role the server " +
                "would refuse.",
        },
    ],
});

// ---------------------------------------------------------------------------
// 2. Location push toggle (S10) -- wizard-and-delegate.
// ---------------------------------------------------------------------------
tours.add("shopify_connector_u2_push_toggle_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Open the mapped location.",
            run: "click",
        },
        focusStep(
            ".o_form_view button:contains('Change inventory push')",
            "The push control takes keyboard focus and shows a focus ring."
        ),
        {
            trigger: ".o_form_view button:contains('Change inventory push')",
            content: "Open the push-change dialog.",
            run: "click",
        },
        {
            trigger: `${DIALOG} .alert:contains('will stop pushing')`,
            content:
                "The dialog states the consequence, including that quantities " +
                "already on Shopify are left as they are.",
        },
        {
            trigger: `${DIALOG} footer button:contains('Confirm')`,
            content: "Apply the change the dialog described.",
            run: "click",
        },
        {
            trigger: `body:not(:has(${DIALOG}))`,
            content: "The dialog closes.",
        },
    ],
});

// ---------------------------------------------------------------------------
// 3. Inventory re-check (S19) -- wizard-and-delegate, enqueues a job.
// ---------------------------------------------------------------------------
tours.add("shopify_connector_u2_recheck_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Open the blocked pair.",
            run: "click",
        },
        {
            trigger: ".o_form_view button:contains('Verify inventory now')",
            content: "Open the verification dialog.",
            run: "click",
        },
        {
            trigger: `${DIALOG} .alert:contains('changes no quantity on either side')`,
            content: "The dialog states that verification is read-only.",
        },
        {
            trigger: `${DIALOG} div[name='reason'] input, ${DIALOG} input[name='reason']`,
            content: "A reason is mandatory; it lands on the job's audit trail.",
            run: "edit Operator re-check from the U2 action tour.",
        },
        {
            trigger: `${DIALOG} footer button:contains('Queue verification')`,
            content: "Queue the verification.",
            run: "click",
        },
        {
            trigger: `body:not(:has(${DIALOG}))`,
            content: "The dialog closes.",
        },
    ],
});

// A blank reason must be refused by the server, not silently accepted.
tours.add("shopify_connector_u2_recheck_blank_reason_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Open the blocked pair.",
            run: "click",
        },
        {
            trigger: ".o_form_view button:contains('Verify inventory now')",
            content: "Open the verification dialog.",
            run: "click",
        },
        {
            trigger: `${DIALOG} footer button:contains('Queue verification')`,
            content: "Queue with no reason at all.",
            run: "click",
        },
        {
            // The refusal happens at the FIELD, not at the server. `reason` is
            // `required=True`, so the web client marks it invalid and never
            // calls `action_confirm` -- the server's
            // "Describe why this pair is being re-checked." `UserError` is the
            // second line of defence and is covered by
            // `test_recheck_wizard_requires_a_reason`. What matters for the
            // operator is that the refusal is visible and nothing is queued,
            // which is what this asserts.
            trigger: `${DIALOG} .o_field_invalid[name='reason'], ` +
                     `${DIALOG} [name='reason'].o_field_invalid, ` +
                     `${DIALOG} .o_field_widget[name='reason'].o_field_invalid`,
            content: "The empty reason is marked invalid and the dialog stays open.",
        },
        {
            trigger: DIALOG,
            content: "Nothing was queued: the dialog is still on screen.",
        },
    ],
});

// ---------------------------------------------------------------------------
// 4. Manual-gateway approval (S17) -- wizard-and-delegate, writes + enqueues.
// ---------------------------------------------------------------------------
tours.add("shopify_connector_u2_order_approval_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Open the order awaiting a payment decision.",
            run: "click",
        },
        {
            trigger:
                ".o_form_view .alert-warning:contains('payment was taken outside')",
            content:
                "The form discloses that the connector cannot verify the " +
                "payment, above the control that acts on it.",
        },
        focusStep(
            ".o_form_view button:contains('Approve Payment')",
            "The approval control takes keyboard focus and shows a focus ring."
        ),
        {
            trigger: ".o_form_view button:contains('Approve Payment')",
            content: "Open the approval dialog.",
            run: "click",
        },
        {
            trigger: `${DIALOG} .alert:contains('You are confirming payment was received')`,
            content:
                "The dialog states plainly that this records a commercial " +
                "judgement and reconciles nothing.",
        },
        {
            trigger: `${DIALOG} div[name='reason'] input, ${DIALOG} input[name='reason']`,
            content: "A reason is mandatory; it lands on the approval audit trail.",
            run: "edit Customer paid the driver in cash; receipt filed.",
        },
        {
            trigger: `${DIALOG} footer button:contains('Approve')`,
            content: "Record the approval.",
            run: "click",
        },
        {
            trigger: `body:not(:has(${DIALOG}))`,
            content: "The dialog closes.",
        },
    ],
});

// The same order, opened by a role the server refuses.
tours.add("shopify_connector_u2_order_approval_denied_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Open the order as a role without approval authority.",
            run: "click",
        },
        {
            trigger:
                ".o_form_view .alert-warning:contains('payment was taken outside')",
            content: "The disclosure is still readable -- the role may read.",
        },
        {
            trigger: ".o_form_view:not(:has(button:contains('Approve Payment')))",
            content:
                "The approval control is not offered to a role the server " +
                "would refuse.",
        },
    ],
});

// ---------------------------------------------------------------------------
// 5. Blocked state: a scope-quarantined pair is not reachable at all.
// ---------------------------------------------------------------------------
// This tour asserts an ABSENCE, and the absence is the point.
//
// The U2 forms carry an `alert-danger` "Excluded from synchronisation" banner
// for `sec3_scope_quarantined` rows. Driving it in a browser establishes that
// it can never render for an ordinary operator: the SEC-3 store rule is a
// GLOBAL `ir.rule` whose domain is
// `[('company_id','in',company_ids), ('sec3_scope_quarantined','=',False)]`,
// so a quarantined row is filtered out of every non-superuser READ. The row
// the banner would appear on is invisible, and the operator's real experience
// of the blocked state is that the pair is simply not in the queue.
//
// That is stricter than the banner and is the correct fail-closed posture, so
// nothing here is "fixed" by weakening the rule. The banner's unreachability
// is recorded as a P3 finding instead (dead UI, not a hole).
tours.add("shopify_connector_u2_quarantined_is_not_listed_tour", {
    steps: () => [
        {
            trigger: ".o_list_view",
            content: "The workspace renders for the operator.",
        },
        {
            trigger: ".o_list_view:not(:has(.o_data_row)), .o_view_nocontent",
            content:
                "The quarantined pair is absent: SEC-3 filters it out of every " +
                "ordinary read, so no operator can act on it.",
        },
    ],
});

// ---------------------------------------------------------------------------
// 6. The TD-020 closure: withdrawing a confirmed first-push decision.
// ---------------------------------------------------------------------------
// A confirmed pair used to be a permanent dead end -- the remap guard's
// refusal was correct, and there was no governed way to unwind the decision
// it protects. This traversal drives the closure from the browser: the
// Administrator opens the confirmed pair, reads the consequence in words,
// gives a reason, ticks the explicit confirmation, and watches the pair
// return to Pending -- where the FULL preview-and-confirm ceremony is
// mandatory again before any push.
tours.add("shopify_connector_u2_first_push_withdraw_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Open the confirmed pair.",
            run: "click",
        },
        {
            trigger:
                ".o_form_view .o_statusbar_status button.o_arrow_button_current:contains('Confirmed')",
            content: "The pair is confirmed -- the state TD-020 stranded.",
        },
        // Selected by its visible label: the button's `name` attribute is a
        // numeric action id resolved at load time, not the xmlid.
        focusStep(
            ".o_form_view button:contains('Withdraw First Push')",
            "The withdrawal control takes keyboard focus and shows a focus ring."
        ),
        keyboardActivateStep(
            ".o_form_view button:contains('Withdraw First Push')",
            "Open the withdrawal dialog by keyboard."
        ),
        {
            trigger: `${DIALOG}:contains('withdraws the pair')`,
            content: "The consequence is named in words before anything changes.",
        },
        {
            trigger: `${DIALOG}:contains('never') .alert-warning`,
            content: "The dialog states the old confirmation is never reused.",
        },
        {
            trigger: `${DIALOG} .o_field_widget[name='reason'] input`,
            content: "A reason is mandatory and lands on the audit trail.",
            run: "edit Physical warehouse move - tour",
        },
        {
            trigger: `${DIALOG} .o_field_widget[name='confirmed'] input`,
            content: "The explicit confirmation is a deliberate second act.",
            run: "click",
        },
        {
            trigger: `${DIALOG} footer button[name='action_confirm']`,
            content: "Withdraw the decision.",
            run: "click",
        },
        {
            trigger:
                ".o_form_view .o_statusbar_status button.o_arrow_button_current:contains('Pending')",
            content:
                "The pair is back to Pending: a completely new preview and " +
                "confirmation are required before any push.",
        },
        {
            trigger:
                ".o_form_view .alert-warning:contains('Waiting for a first-push preview')",
            content: "The form says plainly what has to happen next.",
        },
    ],
});

// ---------------------------------------------------------------------------
// The TD-020 mapping-level closure: withdrawing EVERY first-push decision
// under one Shopify location, driven through the real action/view/wizard/
// service chain.
// ---------------------------------------------------------------------------
// A service-level or direct-wizard-method test cannot see any of the things
// that go wrong here, because all of them are on the way IN: whether the
// control exists for the role the server admits and not for the one it
// refuses, whether the counts the operator confirms against are the counts the
// service will act on, whether the consequence that Shopify is NOT changed is
// stated where the decision is made, and whether a refusal reaches the screen
// rather than a stack trace. So this is driven end to end.

/**
 * Confirm one still-previewed pair under the mapping the dialog is open on.
 *
 * This is the interfering actor the staleness refusal exists for, and it has
 * to be REAL: the signature is snapshotted when the dialog opens, so the
 * refusal can only fire if something genuinely moves afterwards. It calls the
 * same `type="object"` method the pair form's own Confirm First Push button
 * calls, through the same RPC endpoint the web client uses, so what races the
 * dialog is an ordinary operator action rather than a contrivance.
 *
 * The pair is FOUND rather than passed in: a tour that had an id threaded into
 * it would silently do nothing if the fixture changed, and "did nothing" is
 * indistinguishable from "the refusal did not fire" in the assertion below.
 * Finding no pair is an explicit failure instead.
 */
const CONCURRENT_CONFIRM_STEP = {
    trigger: `${DIALOG} footer button[name='action_confirm']`,
    content: "A concurrent administrator confirms one of the pairs.",
    async run() {
        const { rpc } = odoo.loader.modules.get("@web/core/network/rpc");
        const call = (model, method, args, kwargs = {}) =>
            rpc("/web/dataset/call_kw", { model, method, args, kwargs });
        // Scoped by the SEC-3 record rules to what this user may see, and the
        // fixture holds exactly one still-previewed pair, which the Python
        // assertions then name explicitly. Looked up rather than threaded in:
        // an id baked into a tour goes stale silently, and "did nothing" is
        // indistinguishable from "the refusal never fired".
        const rows = await call(
            "shopify.connector.inventory.level.binding",
            "search_read",
            [[["first_push_state", "=", "previewed"]], ["id"]],
            { limit: 1 }
        );
        if (!rows.length) {
            throw new Error(
                "no previewed pair to confirm, so nothing would have moved " +
                    "and the staleness assertion below could not mean anything"
            );
        }
        await call(
            "shopify.connector.inventory.level.binding",
            "action_confirm_first_push",
            [[rows[0].id]]
        );
        // The interference has to have LANDED, or the refusal asserted below
        // would be proving nothing. Re-read the same pair and require it.
        const after = await call(
            "shopify.connector.inventory.level.binding",
            "read",
            [[rows[0].id], ["first_push_state"]]
        );
        if (after[0].first_push_state !== "confirmed") {
            throw new Error(
                `pair ${rows[0].id} is ${after[0].first_push_state} after the ` +
                    "concurrent confirmation, so nothing moved and the " +
                    "staleness refusal below cannot mean anything"
            );
        }
    },
};

tours.add("shopify_connector_u2_location_withdraw_all_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Open the Shopify location whose warehouse has moved.",
            run: "click",
        },
        focusStep(
            ".o_form_view button:contains('Withdraw First Pushes')",
            "The mapping-level withdrawal control is keyboard operable."
        ),
        keyboardActivateStep(
            ".o_form_view button:contains('Withdraw First Pushes')",
            "Open the mapping-level withdrawal dialog by keyboard."
        ),
        {
            trigger: `${DIALOG}:contains('withdraws the first-push decision of every')`,
            content:
                "The consequence is stated for the WHOLE location before " +
                "anything is written.",
        },
        // The counts, each read from its own labelled field rather than from
        // the dialog's text as a whole: a single `:contains('3')` would be
        // satisfied by any 3 anywhere on screen, including a different count.
        {
            trigger: `${DIALOG} .o_field_widget[name='total_pairs']:contains('4')`,
            content: "Every pair under this location is counted.",
        },
        {
            trigger: `${DIALOG} .o_field_widget[name='affected_pairs']:contains('3')`,
            content: "The pairs this actually acts on are counted separately.",
        },
        {
            trigger: `${DIALOG} .o_field_widget[name='previewed_pairs']:contains('1')`,
            content: "Previewed and confirmed pairs are distinguished.",
        },
        {
            trigger: `${DIALOG} .o_field_widget[name='confirmed_pairs']:contains('2')`,
            content: "...so the operator can see what each decision was.",
        },
        // The remote-inventory consequence, as a NUMBER. "Nothing is changed
        // on Shopify" is the reassuring half; how much is still live out there
        // is the half an operator actually needs to decide with.
        {
            trigger: `${DIALOG} .alert-warning:contains('Shopify is not changed by this')`,
            content: "The storefront consequence is named.",
        },
        {
            trigger: `${DIALOG} .o_field_widget[name='pairs_live_on_shopify']:contains('2')`,
            content:
                "...and quantified: how many of the affected pairs have a " +
                "quantity live on the storefront right now.",
        },
        {
            trigger: `${DIALOG}:contains('STAY as they are')`,
            content:
                "The copy states the quantities STAY -- it never implies " +
                "they were reverted or zeroed.",
        },
        // Refusal one: no reason.
        {
            trigger: `${DIALOG} footer button[name='action_confirm']`,
            content: "Confirming with nothing typed must be refused.",
            run: "click",
        },
        {
            trigger:
                `${DIALOG} [name='reason'].o_field_invalid, ` +
                ".o_notification_body:contains('Invalid fields')",
            content:
                "The mandatory reason is enforced before the request is even " +
                "sent.",
        },
        {
            trigger: `${DIALOG} .o_field_widget[name='reason'] input`,
            content: "A reason is mandatory and lands on the audit trail.",
            run: "edit Warehouse physically relocated - tour",
        },
        // Refusal two: a reason, but no consequence confirmation.
        {
            trigger: `${DIALOG} footer button[name='action_confirm']`,
            content:
                "A reason alone is not consent: the consequence has to be " +
                "confirmed explicitly.",
            run: "click",
        },
        {
            trigger: `${DIALOG}:contains('Confirm that explicitly')`,
            content: "The service refuses, and the refusal reaches the screen.",
        },
        {
            trigger: `${DIALOG} footer button`,
            content: "Dismiss the refusal and complete the decision properly.",
            run: "click",
        },
        {
            trigger: `${DIALOG} .o_field_widget[name='confirmed'] input`,
            content: "The single consequence confirmation is a deliberate act.",
            run: "click",
        },
        {
            trigger: `${DIALOG} footer button[name='action_confirm']`,
            content: "Withdraw every first-push decision for this location.",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
            content: "The dialog closes: the decision was accepted.",
        },
    ],
});

tours.add("shopify_connector_u2_location_withdraw_all_stale_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Open the location mapping.",
            run: "click",
        },
        {
            trigger: ".o_form_view button:contains('Withdraw First Pushes')",
            content: "Open the withdrawal dialog.",
            run: "click",
        },
        {
            trigger: `${DIALOG} .o_field_widget[name='affected_pairs']:contains('2')`,
            content:
                "The dialog snapshots the state it is being decided against.",
        },
        // ANOTHER administrator confirms one of these pairs while this dialog
        // sits open. Same method the pair form's own control calls.
        CONCURRENT_CONFIRM_STEP,
        {
            trigger: `${DIALOG} .o_field_widget[name='reason'] input`,
            content: "The operator types their reason, unaware anything moved.",
            run: "edit Warehouse physically relocated - stale tour",
        },
        {
            trigger: `${DIALOG} .o_field_widget[name='confirmed'] input`,
            content: "...and confirms the consequence.",
            run: "click",
        },
        {
            trigger: `${DIALOG} footer button[name='action_confirm']`,
            content: "Applying a decision made against stale information.",
            run: "click",
        },
        {
            trigger: `${DIALOG}:contains('changed while the dialog was open')`,
            content:
                "Refused, and told to reopen and decide against the current " +
                "state. NOTHING was withdrawn.",
        },
    ],
});

tours.add("shopify_connector_u2_location_withdraw_all_denied_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "A Connector User opens the same location mapping.",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_statusbar, .o_form_view header",
            content: "The form renders for this role...",
        },
        {
            // Absence, asserted by reading every button in the header. A CSS
            // `:not(:has(:contains()))` cannot express this: `:contains()` is
            // a hoot-dom extension, not CSS, so it is unavailable inside the
            // structural pseudo-classes the browser evaluates itself.
            //
            // Absent, not disabled: a control a role can see and cannot use is
            // a worse screen than no control at all, and it is the exact
            // defect shape three other U2 controls shipped with.
            trigger: ".o_form_view",
            content:
                "...without the mapping-level withdrawal control, which the " +
                "server admits for Administrator alone.",
            run() {
                const header = document.querySelector(
                    ".o_form_view .o_form_statusbar, .o_form_view header"
                );
                if (!header) {
                    throw new Error(
                        "the mapping form rendered no header at all, so the " +
                            "absence of one control proves nothing"
                    );
                }
                const buttons = [...header.querySelectorAll("button")];
                if (!buttons.length) {
                    throw new Error(
                        "the header carries no controls at all for this role, " +
                            "so this is not evidence about one of them"
                    );
                }
                const offending = buttons.filter((b) =>
                    b.textContent.includes("Withdraw First Pushes")
                );
                if (offending.length) {
                    throw new Error(
                        "a Connector User was offered the mapping-level " +
                            "withdrawal control, which the server refuses"
                    );
                }
            },
        },
    ],
});

// The same staleness protection on the SINGLE-PAIR route. Both wizards
// snapshot the state they were opened against into a `readonly` field, and
// both were losing it the same way, so both need the evidence.
tours.add("shopify_connector_u2_first_push_withdraw_stale_tour", {
    steps: () => [
        {
            trigger: ".o_list_view .o_data_row .o_data_cell",
            content: "Open the previewed pair.",
            run: "click",
        },
        {
            trigger: ".o_form_view button:contains('Withdraw First Push')",
            content: "Open the single-pair withdrawal dialog.",
            run: "click",
        },
        {
            trigger: `${DIALOG}:contains('withdraws the pair')`,
            content:
                "The dialog snapshots the state it is being decided against.",
        },
        CONCURRENT_CONFIRM_STEP,
        {
            trigger: `${DIALOG} .o_field_widget[name='reason'] input`,
            content: "The operator types their reason, unaware anything moved.",
            run: "edit Withdrawn against stale state - tour",
        },
        {
            trigger: `${DIALOG} .o_field_widget[name='confirmed'] input`,
            content: "...and confirms the consequence.",
            run: "click",
        },
        {
            trigger: `${DIALOG} footer button[name='action_confirm']`,
            content: "Applying a decision made against stale information.",
            run: "click",
        },
        {
            trigger: `${DIALOG}:contains('changed while the dialog was open')`,
            content: "Refused. NOTHING was withdrawn.",
        },
    ],
});
