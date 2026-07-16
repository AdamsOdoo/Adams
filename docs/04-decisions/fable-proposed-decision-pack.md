# Fable Gap-Closure Mission — Consolidated Decision Pack (2026-07-16, corrected)

> **How to read this pack.** It is the single consolidated review surface for the
> product owner and Claude control room over everything the Fable
> remaining-gap-closure mission raised (draft PR #173). It is organized into
> **five classes**, not one undifferentiated acceptance act:
>
> - **Class A — Binding product-owner rulings.** Already decided by the product
>   owner (PR #172/#173 rulings). *Not a new numbered DEC acceptance in this PR* —
>   recorded here so downstream docs bind to them. The corpus is aligned to these.
> - **Class B — Product decisions still requiring acceptance.**
> - **Class C — Technical architecture decisions requiring Claude review.**
> - **Class D — Empirical questions for implementation preflight** (fail-closed
>   now; resolved at a named wave preflight).
> - **Class E — Post-MVP items** (explicitly out of MVP scope).
>
> **Nothing in Classes B–D is accepted by this PR. DEC-031 Layer 2 is NOT marked
> Accepted. Existing Accepted decisions (DEC-003..DEC-034) are untouched. Wave 2
> remains unauthorized and unstarted. Draft PR #173 remains draft and unmerged.**
> Each entry links the canonical document that carries its full statement,
> evidence, alternatives, consequences, risks, and rollback.

---

## Class A — Binding product-owner rulings (not a new numbered DEC acceptance in this PR)

These are settled product direction. Every canonical doc, packet, DoR, matrix, and
prototype in PR #173 is aligned to them.

| # | Binding ruling | Source | Canonical doc |
|---|---|---|---|
| A-1 | Exactly **two customer-facing roles** — Connector User and Connector Administrator | roles direction 2026-07-16 | `../02-product/connector-roles-and-permissions.md` §1 |
| A-2 | **Administrator inherits User** (single role assignment per person) | same | roles §1/§4 |
| A-3 | **No separate customer-facing Auditor or Reviewer** — Reviewer's audited acts move to User; Auditor retained only as a hidden technical group | same | roles §2 |
| A-4 | **No PII masking in the MVP** — no masked snapshot display, no manual/scheduled masking as a capability | PR #173 ruling `4994990296` | roles §3 |
| A-5 | **No User-unmask toggle / no per-store PII-visibility toggle / no third PII role/tier** | same | roles §3 |
| A-6 | **Raw operational PII available to both final roles** per their permitted operations (normal ACL/company/redaction/audit still apply) | same | roles §3 |
| A-7 | **Abandoned checkouts never auto-create quotations** in the MVP | orders direction | `../02-product/abandoned-checkout-policy.md` (PD-AC-1) |
| A-8 | **Paid-only default order-confirmation policy** (per-store policy selectable) | orders direction | `../02-product/sales-order-lifecycle-and-confirmation-policy.md` (PD-A/ORD-1) |
| A-9 | **Approved manual-gateway policy** — manual gateways gated by an approved-gateway list; card-PENDING never confirms | orders direction | sales-order lifecycle (PD-B/ORD-2) |
| A-10 | **Complete COD lifecycle** — three-dimension model, stock restored only by a validated return picking, append-only collection events, operational-only accounting boundary in MVP | COD direction | `../02-product/cod-lifecycle-and-reconciliation.md` |
| A-11 | **Mode 1 (Odoo-controlled) is the default** fulfillment mode | fulfillment direction | `../02-product/fulfillment-operating-modes.md` §1 |
| A-12 | **Mode 1 and Mode 2 are BOTH mandatory MVP Wave 4 backend scope** (per-store mode field, 16-condition engine, inbound evidence/bindings, mode-switch state machine, reconnect reconciliation, genuine dev-store mutation UAT). **Wave 5 owns only the mode UI, not the Mode 2 backend.** | PR #173 ruling `4993775983` §2 | fulfillment-operating-modes §10 |
| A-13 | **Administrator selects the fulfillment mode per store** | fulfillment direction | fulfillment-operating-modes §1/§6 |
| A-14 | **Carrier "Delivered" never validates Odoo stock** — a milestone cannot move real inventory | fulfillment direction | `../02-product/shopify-fulfillment-status-model.md` §8 |
| A-15 | **Odoo is the inventory authority** — Shopify→Odoo is read-only with divergence review | inventory direction | `../02-product/inventory-operating-model.md` |
| A-16 | **Reconnect uses fresh catch-up** (per-domain watermark), never stale-job blind replay | reconnect direction | `../02-product/reconnect-catchup-backfill-policy.md` |
| A-17 | **Product export remains MVP** (after DEC-031 Layer 2) | scope direction | `../02-product/product-export-operating-model.md` |
| A-18 | **Premium UX direction** — Apple×enterprise synthesis, single role-gated surface, 11-state global contract | UX direction | `../02-product/premium-ux-master-specification.md` |

## Class B — Product decisions still requiring acceptance

Genuinely open product choices not yet fixed by the product owner.

| ID | Decision | Wave | Canonical doc |
|---|---|---|---|
| PD-B1 | Precise **pending-payment expiry** duration before a pending order is closed/expired | 2 | sales-order lifecycle |
| PD-B2 | Exact **initial import-window** options at onboarding (e.g. 30/60/90 days) | 2 | reconnect-catchup-backfill-policy |
| PD-B3 | Exact **COD collection evidence-source** default per store | 2/4 | cod-lifecycle-and-reconciliation |
| PD-B4 | Exact **Mode-switch reconciliation-scan boundary** (how far back the switch scan reaches) | 4 | fulfillment-operating-modes §6 |
| PD-B5 | Exact **Lite/Full capability allocation** where not already fixed by DEC-029 (Accepted) | 3–5 | modular-architecture-recommendation |
| PD-B6 | **8-state financial map** transition/reconciliation detail (ORD-3), **fail-closed financial gates** (ORD-4), and the **settings inventory + `paid_only` default vs Task-012 "no default" tension** (ORD-5) | 2 | sales-order lifecycle; Task 012 addendum |
| PD-B7 | **Product-export field-ownership/guard defaults** (PD-PX-1..7: field-ownership matrix, changed-since-read gate, DRAFT default, identifier upsert dedup) | 5 | product-export-operating-model |

## Class C — Technical architecture decisions requiring Claude review

| ID | Decision | Wave | Canonical doc |
|---|---|---|---|
| TA-C1 | **DEC-031 Layer 2** mutation-safety design and its enumerated **L2-D** acceptance items (durable attempt identity, ownership, `transport_attempted` fencing, per-mutation idempotency/reconciliation matrix, uncertain-outcome handling, crash/stale-owner recovery). **Proposed — NOT Accepted here.** Claims at-most-once-ambiguous + reconciliation convergence, never exactly-once | 3 (Stage 0) | `../03-architecture/dec-031-layer-2-mutation-safety-design.md` |
| TA-C2 | **Mutation-attempt model + commit boundaries + stale-owner sweep** (no lock held across a network call) | 3 | dec-031-layer-2 |
| TA-C3 | **Module boundaries** (six-module MVP family; MA-D* decisions) | 3–5 | modular-architecture-recommendation |
| TA-C4 | **Two-role migration mechanics** (Option M-A groups/privilege/ACL re-key/migration script) | 5 (SEC-2) | roles §4 |
| TA-C5 | **PII-simplification implementation option** — SEC-2 Option 1 (full removal) vs Option 2 (deprecate-dormant); recommend Option 1 | 5 (SEC-2) | `../07-implementation-plan/task-sec2-two-role-and-pii-simplification-packet.md` |
| TA-C6 | **Inbound reconciliation registries** (per-fulfillment binding + per-line evidence; origin classification; lot/serial only on deterministic evidence — FUL-3) | 4 | fulfillment-operating-modes §5 |
| TA-C7 | **CAS technical contract** (compare-and-set inventory mutation shape) | 3 | inventory-operating-model |
| TA-C8 | **Performance architecture / SLO set** (provisional rows pending PERF-1 calibration) | 6 | `../05-qa/performance-slo-benchmark-plan.md` |

## Class D — Empirical questions for implementation preflight

Not product decisions. Each fails **closed** today and is resolved at a named wave
preflight against an exact source.

| ID | Question | Current fail-closed behavior | Source to re-check | Preflight owner | Blocking? |
|---|---|---|---|---|---|
| EQ-D1 | **CAS field name** — `compareQuantity` (2026-07-16 capture) vs `changeFromQuantity` (D-013-3) | inventory mutation withheld until confirmed | Shopify `inventorySetQuantities`/`inventoryAdjustQuantities` 2026-07 docs | Wave 3 | **Blocking** for the inventory mutation |
| EQ-D2 | **Shopify mutation idempotency** details (which mutations expose idempotency keys) | verification-read-before-retry on any ambiguous outcome | Shopify mutation docs + live probe | Wave 3/4/5 | Non-blocking (safe default holds) |
| EQ-D3 | **Webhook payload attribution** (does a fulfillment/order webhook expose the originating API client?) | origin classified `external`/unknown, never assumed connector | live webhook payload | Wave 4 | Non-blocking |
| EQ-D4 | **Per-plan throttle** behavior (cost points/refill by plan) | conservative rate limiting | Shopify GraphQL rate-limit docs + live headers | Wave 3+ | Non-blocking |
| EQ-D5 | **Actual performance calibration** (real throughput/latency) | provisional SLOs labeled provisional | PERF-1 measurement | Wave 6 | Non-blocking |
| EQ-D6 | **Live enum/schema confirmation** at each wave freeze | unknown values stored raw, automation stops (§7 contract) | official enum pages (Layer A re-verified 2026-07-16) | each wave | Non-blocking |
| EQ-D7 | **Dev-store evidence questions** (read-only order import; mutation proofs) | no live proof claimed; read-only deferrable to Wave 6; mutation waves require genuine dev-store evidence | dev-store when provisioned | Wave 2 (read-only, non-blocking) / Waves 3–5 (mutation, blocking) | see Wave-2 rule |

## Class E — Post-MVP items (explicitly out of MVP scope)

Optional **PII masking / privacy enhancement** (separately reviewed later);
abandoned-checkout recovery **workspace**; advanced **accounting**; **refunds**;
**payout reconciliation**; **B2B**; **subscriptions**; **gift cards**; **Shopify
Markets**; advanced **analytics**; **app-store packaging**; and the other agreed
exclusions recorded in `../02-product/mvp-capability-map.md`.

---

## Wave-gate summary (what must be Accepted before each wave)

| Wave | Must be Accepted first |
|---|---|
| 2 | Class A order/COD/abandoned rulings recorded; PD-B1/B3/B6 accepted; reconnect order-domain subset; Task 012 packet re-acceptance (with addendum); Wave 2 DoR. **Odoo.sh evidence mandatory; read-only Shopify preferred, deferrable to Wave 6 (no waiver) — not a merge blocker.** |
| 3 | TA-C1 DEC-031 Layer 2 accepted → implemented Stage 0 → runtime-proven; inventory PDs; EQ-D1 CAS field re-verified; TA-C3 module decisions; Task 013/013B re-acceptance; Wave 3 DoR. **Genuine dev-store mutation evidence required.** |
| 4 | Class A fulfillment rulings (A-11..A-14); **both Mode 1 and Mode 2 backend** (A-12); TA-C6 registries; COD fulfillment subset; Task 014 re-acceptance; Wave 4 DoR. **Genuine dev-store fulfillment mutation evidence required.** |
| 5 | **SEC-2** (A-1..A-6 two-role + no-masking; TA-C4/TA-C5); premium UX (A-18, PD-UX) + prototype visual review; the fulfillment **mode UI** (selector/review/dashboards — not the Mode 2 backend); PD-PX; U1–U3/PERF-1 packet acceptance; Wave 5 DoR. |
| 6 | All QA/UAT matrices adopted; deferred read-only order UAT + all mutation-domain UAT executed; two-role + no-masking UAT; Wave 6 DoR + packet; product-owner release sign-off. |

**Nothing in Classes B–D is accepted. DEC-031 Layer 2 is not Accepted. Wave 2
remains unauthorized and unstarted. Draft PR #173 remains draft and unmerged.**
