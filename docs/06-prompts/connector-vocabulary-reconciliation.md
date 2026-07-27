# Connector vocabulary — the authoritative code→label reconciliation (TD-003)

> **Status: reference. NOT an acceptance, NOT a review.** Produced on
> `fable/wave-5-completion` by the implementing session, which per CLAUDE.md
> §13 may not review or accept its own work.
>
> **The implementation is authoritative.** Every value below was read from the
> shipped code at this branch's head. Where a product document says something
> different, the document is superseded — the code is not changed to match a
> document, and no working selection value is renamed to match superseded
> prose.

---

## 1. Why this file exists

TD-003 records a divergence between the pre-implementation product documents
and the shipped Wave 4 fulfillment code. The documents named
`external_service`, `over_fulfillment`, `under_review`, `auto_matched` and
`rejected`; none of those is a real selection value anywhere in the codebase.

That is not a cosmetic problem. The Gate-A static-validation rule exists
because a UI or test author who copies a value out of a product document
writes a selection that does not exist, and it fails at runtime rather than
at review. A copy deck that maps only the historical values leaves real code
values rendering as raw strings on an operator's screen.

So this file is the single place that answers "what is the actual value, and
what does the operator see?" — complete, and derived from the code.

**Scope discipline.** This reconciles vocabulary. It is not a product-document
rewrite: the superseded documents keep their structure and their `Proposed`
status, and gain a pointer to this file at the exact locations that carried a
stale value.

---

## 2. Origin classes

`addons/shopify_connector_fulfillment/models/shopify_connector_fulfillment_inbound_evidence.py`
· `ORIGIN_CLASS_SELECTION`

| Code value | Operator-facing label |
| --- | --- |
| `connector` | Connector-Created |
| `external_merchant` | External — Merchant |
| `external_app` | External — App/Service |
| `external_unknown` | External — Unknown Origin |

**Superseded, and not values:** `external_service`, `carrier_event_only`
(`fulfillment-operating-modes.md` §3). The closest real values are
`external_app` and `external_unknown` respectively, but they are **not**
renames — the shipped classification splits merchant from app from unknown,
which the two superseded names do not express.

---

## 3. Reconciliation states

Same file · `RECONCILED_STATE_SELECTION`

| Code value | Operator-facing label |
| --- | --- |
| `observed` | Observed |
| `review` | Review Case Open |
| `acknowledged` | Acknowledged (Handled Outside Odoo) |
| `applied` | Applied to Odoo |
| `superseded` | Superseded |

**`under_review` is not a value.** The code value is **`review`**. This is the
single most-copied stale token in the product documents, and the one TD-003
names explicitly.

**Superseded, and not values:** `auto_matched`, `rejected`
(`fulfillment-operating-modes.md` §5). There is no automatic-match state —
Mode 1 never applies stock automatically — and a rejected case is
`acknowledged`, which says what actually happened rather than implying the
connector passed judgement.

---

## 4. Review reasons — all 21

Same file · `REVIEW_REASON_SELECTION`. The count matters: a copy deck built
against the historical 20 leaves the 21st rendering as a raw string.

| Code value | Operator-facing label |
| --- | --- |
| `order_binding_missing` | Order Binding Missing |
| `fulfillment_state_not_success` | Fulfillment State Not SUCCESS |
| `fulfillment_order_unresolved` | FulfillmentOrder Unresolved |
| `product_binding_missing` | Product Binding Missing |
| `line_mapping_ambiguous` | Line Mapping Ambiguous |
| `quantity_overrun` | Quantity Exceeds Remaining |
| `quantity_mismatch` | Quantity Mismatch |
| `location_unmapped` | Location Unmapped |
| `picking_ambiguous` | Picking Ambiguous |
| `reservation_invalid` | Reservation Invalid |
| `lot_serial_ambiguous` | Lot/Serial Ambiguous |
| `already_reconciled` | Already Reconciled |
| `binding_conflict` | Fulfillment Binding Conflict |
| `remote_state_changed` | Remote State Changed |
| `origin_unconfirmed` | Origin Unconfirmed |
| `mode_not_enabled` | Mode 2 Not Enabled |
| `carrier_would_book` | Carrier Flow Would Book/Charge |
| `delivered_not_validated` | Delivered Per Carrier — Odoo Not Validated |
| `cancelled_after_validation` | Shopify Cancelled After Odoo Validation |
| `unknown_status_value` | Unknown Status Value |
| `external_fulfillment_observed` | External Fulfillment Observed |

**`over_fulfillment` is not a value** (`fulfillment-operating-modes.md` §4).
The quantity-overrun case is **`quantity_overrun`** here, and a fulfillment
review case that must also block a core job persists **`ambiguous_match`** as
the core `manual_review_subreason` — two different registries, deliberately,
per DEC-038 §7.2.

`external_fulfillment_observed` is the Wave 4 Theme H addition: the routine
Mode-1 "a confirmed external fulfillment was observed" baseline. It is
distinct from `remote_state_changed` (a narrow live-second-read gate) and
from `mode_not_enabled` (a mid-flight mode switch).

---

## 5. Roles — the concept and the string are different

This program discusses roles as **Connector User**, **Connector Operator**,
**Connector Reviewer**, **Connector Administrator** and **Connector Auditor**.
Those are role *concepts*, and they are useful. They are **not** the strings
Odoo renders.

`addons/shopify_connector_core/security/shopify_connector_security.xml`

| Concept used in this program | Actual `res.groups` name | Shown on the user form? |
| --- | --- | --- |
| Connector User | `User` | **Yes** — as a selectable level of the **Shopify Connector** privilege |
| Connector Administrator | `Administrator` | **Yes** — same privilege |
| Connector Auditor | `Auditor` | No — `privilege_id` is `False` |
| Connector Operator | `Operator` | No — `privilege_id` is `False` |
| Connector Reviewer | `Reviewer` | No — `privilege_id` is `False` |

Two consequences a UI or copy author has to act on:

1. **A screen must never print "Connector User".** The user sees
   `Shopify Connector: User`. Writing the concept name into a label invents a
   string Odoo does not show anywhere.
2. **Three of the five roles are invisible.** Operator, Reviewer and Auditor
   are server-side capability primitives with no `privilege_id`, so they do
   not appear on the user form at all. Copy that tells an administrator to
   "assign the Reviewer role" describes a control that is not on the screen.

**No group is ever renamed to match a document.** That was logged as OQ-5 and
the answer is recorded here: the document changes, not the group.

---

## 6. Residual stale locations — corrected in this cycle

TD-003 named two locations still carrying `under_review` and outside the
earlier annotation pass's allowed-files set. Both are corrected now, to the
real code value, with a pointer to this file:

| File | Location | Was | Now |
| --- | --- | --- | --- |
| `docs/05-qa/fulfillment-mode-uat-matrix.md` | UAT-FM-3.3 | `under_review` | `review` |
| `docs/02-product/premium-ux-master-specification.md` | §3 S21 | `observed`, `under_review`, `auto_matched`, `applied`, `acknowledged`, `rejected`, `superseded` | the five real `RECONCILED_STATE_SELECTION` values |

The two documents annotated in the 2026-07-23 pass
(`fulfillment-operating-modes.md`, `shopify-fulfillment-status-model.md`)
keep their non-destructive superseded-vocabulary notes and their section
values, exactly as that pass left them. Nothing in this cycle rewrites their
prose.

---

## 7. How to use this file

Building a screen, a copy deck entry, a test fixture or a domain: take the
value from the left column here, not from a product document. If a value you
need is not listed, read the selection in the code and add it here in the
same commit — a copy deck that has drifted from the code is the defect
TD-003 records, and it drifts one unlisted value at a time.

`addons/shopify_connector_core/tests/test_vocabulary_reconciliation.py`
asserts that every value in every table above still exists in the code, so
this file cannot go stale silently.
