# Fable Gap-Closure Mission — Consolidated Proposed-Decision Pack (2026-07-16)

> **Status: every decision in this pack is PROPOSED — none is accepted.**
> This pack is the single consolidated review surface for the product owner
> and Claude control room over all decisions raised by the Fable
> remaining-gap-closure mission (draft PR #173). Each entry lists its full
> record location (statement, evidence, alternatives, consequences, risks,
> rollback live in the linked canonical document), the affected waves, the
> acceptance authority, and whether implementation is blocked on it.
> Per the mission's decision-status rules, existing Accepted decisions
> (DEC-003..DEC-034 as recorded) are untouched; nothing here rewrites them.
> This file does not follow the one-decision-per-ADR template because it is
> an index, not a decision record; on acceptance, the control room may
> promote entries into numbered DEC records or accept the canonical docs
> directly (recording the act in the architecture-review/decision logs).

## How to review

Recommended order: A (roles) → B (orders/COD) → C (fulfillment) → D
(reconnect/inventory/export) → E (Layer 2) → F (architecture/packaging) →
G (UX) → H (QA/SLO). Groups A–E block Wave 2–5 gates as noted; G blocks
Wave 5 UI; H blocks Wave 6.

## A. Roles and permissions — `../02-product/connector-roles-and-permissions.md`

| ID | Decision | Blocks |
|---|---|---|
| ROLE-1 | Two customer-facing roles only: Connector User, Connector Administrator; Administrator auto-inherits User (single assignment) | Wave 5 (SEC-2 + U1); product direction is binding, record formalizes it |
| ROLE-2 | Migration design 4 internal groups → 2 roles (option M-A: new `group_shopify_connector_user`; admin implies user; old groups retained as hidden technical groups; stable XML IDs) | Wave 5 SEC-2 |
| ROLE-3 | Reviewer's audited resolution acts move to Connector User; destructive/exceptional overrides stay Administrator-only | Wave 5 |
| ROLE-4 | PII: User sees masked by default; unmasked = Administrator-only plus optional per-store Administrator toggle | Wave 5; interacts with PCD posture (DEC-028, Accepted) |
| ROLE-5 | Auditor disposition (recommendation: retain as hidden technical group) | Wave 5 (non-blocking for backend waves) |

## B. Orders, COD, abandoned checkouts

`../02-product/sales-order-lifecycle-and-confirmation-policy.md` (PD-A..E):

| ID | Decision | Blocks |
|---|---|---|
| ORD-1 (PD-A) | Per-store confirmation policy: paid-only (default) / paid-or-authorized / quotations-only | Wave 2 |
| ORD-2 (PD-B) | Separate manual-gateway sub-policy (auto-confirm / quotation / User approval) keyed on `manualPaymentGateway` + approved-gateway list; card-PENDING never confirms | Wave 2 |
| ORD-3 (PD-C) | Complete 8-state financial map incl. transition/reconciliation rules; confirmed SOs never auto-cancelled | Wave 2 |
| ORD-4 (PD-D) | Fail-closed financial gates (total check, currency, tax posture) mapped onto 16-class taxonomy | Wave 2 |
| ORD-5 (PD-E) | Settings inventory incl. `paid_only` default (note: Task 012 addendum flags tension with packet's "no default" posture — resolve at packet re-acceptance) | Wave 2 |

`../02-product/cod-lifecycle-and-reconciliation.md` (PD-COD-1..6): three-dimension state model; stock restored only by validated return picking; partial-delivery/backorder rules; value ledger + append-only collection events, no mark-as-paid for partial; per-store authoritative evidence source; accounting boundary (operational-only MVP; `orderMarkAsPaid` optional, policy-gated, Layer-2-gated). Blocks Waves 2/4/5 as allocated in the doc §9.

`../02-product/abandoned-checkout-policy.md` (PD-AC-1..4): binding no-auto-quotation default (MVP); optional workspace classified **post-MVP**; audited manual quotation action; retention coverage. PD-AC-1 blocks Wave 2 (import must ignore checkouts); the rest block nothing in MVP.

## C. Fulfillment — `../02-product/fulfillment-operating-modes.md` + `../02-product/shopify-fulfillment-status-model.md`

| ID | Decision | Blocks |
|---|---|---|
| FUL-1 | Per-store operating mode; Mode 1 (Odoo-controlled) default; external fulfillments → review cases, never auto-validate stock | Wave 4 |
| FUL-2 | Mode 2 auto-reconciliation only under all 16 exact conditions; any ambiguity → review; recommended wave: Wave 5 (Wave 4 stretch) | Wave 4/5 |
| FUL-3 | Inbound reconciliation data model (per-fulfillment binding + per-line evidence; origin classification; lots/serials only with deterministic evidence) | Wave 4 |
| FUL-4 | Mode-switching contract (Administrator-only, audited, idempotent, rollback-safe, reconciliation scan) | Wave 4/5 |
| FUL-5 | Complete four-family state mapping + deprecated-value handling + unknown-future-value contract + carrier-Delivered-never-validates-stock rule | Wave 4 + UI |

## D. Reconnect/backfill, inventory, product export

`../02-product/reconnect-catchup-backfill-policy.md`: per-domain watermark catch-up with overlap; order catch-up automatic since watermark; manual Administrator backfill with mandatory preview (new/changed/duplicate/skipped/review counts); onboarding import windows; 60-day/`read_all_orders` honesty. Blocks Waves 2–5 per domain.

`../02-product/inventory-operating-model.md` (12 PDs): free_qty-per-mapped-location export basis; last-value-wins coalescing; CAS compareQuantity flow (note: CAS field-name evidence conflict vs D-013-3 `changeFromQuantity` — mandatory re-verification at Wave 3 preflight, recorded in the Task 013 addendum); clamp+warn negatives; read-only Shopify→Odoo with divergence review. Blocks Wave 3.

`../02-product/product-export-operating-model.md` (PD-PX-1..7): field-ownership matrix; changed-since-read gate; complete-variant-list destructive-guard; DRAFT/unpublished default; identifier upsert dedup; Layer 2 uncertainty reconciliation. Blocks Wave 5.

## E. DEC-031 Layer 2 — `../03-architecture/dec-031-layer-2-mutation-safety-design.md` (registered by the dated revision note in `DEC-031-core-r2-job-execution-replay-safety.md`)

The complete Proposed mutation-safety design (durable attempt identity, ownership, transport_attempted fencing, per-mutation idempotency/reconciliation matrix, uncertain-outcome handling, crash/stale-owner recovery, no-lock-across-network commit boundaries, audit/retention, test strategy) with its enumerated L2-D* acceptance items. **Blocks Waves 3, 4, and 5 mutation domains** (implemented as Wave 3 Stage 0 per `../07-implementation-plan/wave-3-definition-of-ready.md`). Acceptance authority: product owner + Claude control room. Explicitly claims at-most-once-ambiguous with reconciliation convergence — never exactly-once.

## F. Modular architecture & packaging — `../03-architecture/modular-architecture-recommendation.md` (MA-D*)

Six-module MVP family (core, product, sale(+orders), inventory, fulfillment, product_export); customer module rejected for MVP (revisit at customer-export phase); sale-module naming kept with documented reality; accounting/refund/payout deferred (no empty modules); multi-store is core data-model, not a module; Layer 2 substrate lives in core (inert under Lite). Capability/module matrix incl. Lite/Full mapping per accepted DEC-029. Blocks Waves 3–5 module creation.

## G. Premium UX — `../02-product/premium-ux-master-specification.md` (PD-UX-1..6) + `../09-ui-prototype/` extension

Apple×enterprise synthesis; IA extension S15–S32 under the 7-menu structure; 11-state global contract; 3D-only-in-onboarding/education/empty rule; density modes; U1/U2/U3 phase allocation with SEC-2-first sequencing; twelve new prototype surfaces (Proposed, awaiting visual review). Blocks Wave 5 UI packets.

## H. QA / SLO / release

`../05-qa/performance-slo-benchmark-plan.md` (SLO set incl. new provisional rows — calibration owned by PERF-1/Wave 6); `../05-qa/waves-2-6-cross-domain-test-matrix.md`; COD / fulfillment-mode / reconnect-backfill UAT matrices; `../05-qa/security-pii-matrix-waves-2-6.md`; `../08-release-readiness/release-readiness-gap-list.md`. These are planning artifacts: acceptance = adoption as the binding test/UAT basis for each wave's DoR. Blocks Wave 6 execution; matrix existence is a Wave 2+ DoR item.

## Wave-gate summary

| Wave | Must be Accepted first |
|---|---|
| 2 | ORD-1..5, PD-COD import subset (1–3), PD-AC-1, reconnect order-domain subset, Task 012 packet re-acceptance (with addendum), Wave 2 DoR |
| 3 | Layer 2 (E) accepted → implemented → runtime-proven; inventory PDs; CAS field re-verification; MA-D module decisions; Task 013/013B re-acceptance; Wave 3 DoR |
| 4 | FUL-1..5; COD fulfillment subset (4–13); Task 014 re-acceptance; Wave 4 DoR |
| 5 | ROLE-1..5 (SEC-2); PD-UX-1..6 + prototype visual review; PD-PX-1..7; U1–U3/PERF-1 packet acceptance; optional FUL-2 Mode 2; Wave 5 DoR |
| 6 | All QA/UAT matrices adopted; dev-store credentials provisioned (hard stop); Wave 6 DoR + packet; product-owner release sign-off |

**Nothing in this pack is accepted. Wave 2 remains unauthorized and unstarted.
The draft PR #173 remains draft and unmerged.**
