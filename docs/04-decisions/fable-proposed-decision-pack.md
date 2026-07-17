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
> **At first delivery, nothing in Classes B–D was accepted by this PR.**
> Each entry links the canonical document that carries its full statement,
> evidence, alternatives, consequences, risks, and rollback.
>
> **Update — 2026-07-17 control-room decision session.** The Claude control room
> has now reviewed the corrected PR #173 as a complete product/architecture
> package and **decided every Class B item and dispositioned every Class C item**
> — see **§Control-room decisions (2026-07-17)** at the foot of this document for
> the binding record. **DEC-031 Layer 2 was NOT DEC-accepted** (its design is
> accepted only as the authoritative *proposal* routed to a dedicated pre-Wave-3
> architecture gate); existing Accepted decisions (DEC-003..DEC-034) are
> untouched; **Wave 2 remains unauthorized and unstarted**; no implementation is
> authorized by these decisions.

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

---

## Control-room decisions (2026-07-17)

> **Authority:** Claude control room (DEC-032 macro-wave model), acting as scope
> governor, architecture reviewer, and merge gatekeeper for PR #173. **Decision
> date: 2026-07-17.** These are binding for the MVP completion program. They are
> **documentation/planning decisions only** — no connector code is authorized, no
> `addons/**` file is changed, DEC-031 Layer 2 is **not** DEC-accepted, and Wave 2
> stays unauthorized/unstarted. Each Wave still opens only through its own gate act
> (§Wave-gate summary).

### Class A — confirmed (already-settled product-owner rulings)
A-1..A-18 are confirmed **faithfully and consistently recorded** across the
canonical product docs, the Wave 2–6 DoRs, the QA/UAT matrices, and the rendered
prototypes; no current-facing document contradicts them. This is a confirmation,
not a new numbered DEC acceptance.

### Class B — product decisions (all decided)

| ID | Decision | Disposition | Binding default vs configurable |
|---|---|---|---|
| PD-B1 | **Pending-payment expiry.** Per-store `pending_wait_expiry`, **default 24 h**, **min 1 h**, **max 7 d**; a PENDING order stays tracked-but-unconfirmed; expiry ends the auto-wait and creates an **auditable skipped/review** state; a later PAID transition reconciles (manually or automatically) with **no duplicate order**. | **ACCEPT WITH AMENDMENT** | 24 h is the *default* (was "proposed 7 d", OQ-C): 24 h clears the vast majority of legitimately delayed card authorizations while not leaving orders in limbo; **7 d is retained as the configurable maximum**; 1 h floor prevents premature drops. **OQ-C resolved.** |
| PD-B2 | **Initial import-window.** Quick choices **7 / 30 / 60 days** + **custom range**; **default 30 days**; **90 days is not offered generally without `read_all_orders`**; any range beyond available Shopify order access is **blocked with an exact scope explanation**; **mandatory read-only preview before enqueue**. | **ACCEPT** | Matches reconnect policy §6/PD-RB-9 (≤60 without `read_all_orders`, custom >60 gated, 60-day honesty). Quick set 7/30/60 made explicit. |
| PD-B3 | **COD collection evidence-source.** Default authority per store = **Odoo User-confirmed operational collection evidence**; Shopify transaction evidence may confirm collection **when exact and available**; external courier evidence is **supporting-only absent an accepted integration**; conflicting sources **route to manual review**; **no automatic accounting posting in MVP** (RA-010). | **ACCEPT** | Per-store configurable authoritative source (COD doc §4.1); append-only ledger. |
| PD-B4 | **Mode-switch reconciliation-scan boundary.** Scan from the **earlier of** (a) last successful fulfillment watermark minus the configured overlap, (b) the latest unresolved external-fulfillment evidence boundary; **bounded initial lookback default 30 days**; **Administrator preview + custom extension**; **never replay/reapply** historic fulfillment; every discovered past fulfillment is **classified and deduplicated before any action**. | **ACCEPT** | Refines fulfillment-operating-modes §6 (already read-only, watermark-based, never-replay). Exact boundary + 30-day default recorded there. |
| PD-B5 | **Lite/Full allocation.** Adopt the DEC-029 edition split (Lite = `core+product+sale`, read-only/zero-mutation; Full = Lite + `inventory+fulfillment+product_export`). **Correction:** **Mode 1 outbound fulfillment/tracking is FULL, not Lite** — `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate` are Shopify **mutations** and live in the Full-only `shopify_connector_fulfillment` module under Layer 2; placing them in Lite would break Lite's "structurally zero Shopify mutations" safety guarantee. **No separate codebases or duplicate apps** — editions are module sets; dependency-safe per the module DAG. | **ACCEPT WITH AMENDMENT** | Amends the reviewer's draft Lite list (which placed Mode 1 outbound in Lite) to conform to Accepted DEC-029 and modular-architecture §6/§8. Mode 2 inbound = Full. |
| PD-B6 | **8-state financial map / fail-closed gates / settings defaults.** `paid_only` **default** (binding); `paid_or_authorized` and `quotations_only` options; manual-gateway overlay (approved list, evidence-discriminated, card-PENDING never manual); **null financial status fails closed**; partially-paid/refunded → review; **no automatic cancellation of a confirmed Odoo SO**; **no silent financial-line rewrite**; **currency/tax/total mismatch blocks before SO creation**; settings inventory per lifecycle §7. **Task-012 "no default" tension resolved:** the 2026-07-16 policy-layer addendum's **`order_confirmation_policy` default `paid_only` supersedes** the earlier §15 "NO default (unset holds imports)" posture; packet re-acceptance carries the single reconciled field. | **ACCEPT** | paid_only default is binding; the rest is per lifecycle §1/§7 + matrix. |
| PD-B7 | **Product-export ownership/guards.** Field-ownership matrix (Odoo-authoritative for allowlisted fields); **DRAFT/unpublished default on create**; **changed-since-read gate**; **mandatory preview → explicit confirm**; **complete-variant-list destructive guard (fail closed, `destructive_write_guard_blocked`)**; **identifier-based upsert** (`productSet` customId/handle/id); **no silent overwrite** (all Shopify-side edits shown in the preview diff first); **Layer-2 reconciliation on ambiguous outcomes**; **media detach-only, two-phase READY-gated** (never deletes merchant media). | **ACCEPT** | Safest defaults; product stays practical (preview-first). Product-export-operating-model §2–§5/§16. |

### Class C — technical architecture decisions

| ID | Decision | Disposition |
|---|---|---|
| TA-C1 / TA-C2 | **DEC-031 Layer 2 mutation-safety design (L2-D1..D15) + mutation-attempt model / commit boundaries / stale-owner sweep.** Verified against all eight hard safety properties (no DB lock across a remote call; never claims exactly-once — only at-most-once-ambiguous + reconciliation convergence; commits intent before send; distinguishes not-attempted from uncertain via `transport_attempted`; reconciles before retry; fails closed without a registered domain strategy; preserves Wave-1 leases/disconnect/security verbatim §15; covers every crash/stale-owner window §2/§9/§11). | **PROPOSED DESIGN ACCEPTED FOR A FUTURE DEDICATED GATE REVIEW — NOT IMPLEMENTATION-AUTHORIZED AND NOT DEC-ACCEPTED.** Formal acceptance occurs only at a dedicated pre-Wave-3 architecture gate after exact-codebase re-read, exact Wave-3 base SHA, mutation-domain API re-verification, exact allowed-file list, complete caller inventory, reconciliation-matrix validation, migration/uninstall review, and independent adversarial review. |
| TA-C3 | **Module boundaries — 6-module MVP family** (`core`, `_product`, `_sale`, `_inventory`, `_fulfillment`, `_product_export`), MA-D1..D5. Customer stays in `_sale` for MVP; **no empty accounting/refund/payout modules**; multi-store is a **core data-model property, not a module**; strict one-directional DAG (no cycles); uninstall/data-ownership explicit; Lite/Full maps cleanly. | **ACCEPT** as a planning/architecture decision (authorizes no code by itself). |
| TA-C4 | **Two-role migration — Option M-A.** New `group_shopify_connector_user` (implies operator+reviewer); Administrator implies User; legacy groups retained as **hidden** technical groups; **XML IDs never renamed**; existing assignments migrated **idempotently**; ACLs re-keyed **exhaustively** (packet supplies the CSV diff); **one** customer-visible privilege selection (User/Administrator). | **ACCEPT** (design; no code). |
| TA-C5 | **PII simplification — SEC-2 Option 1 (controlled full removal).** Remove the masked computed field, the manual masking action, the business-record masking service + setting, and the customer-snapshot masking from the retention sweep. **Retention cron is retained but rescoped to log/audit `payload_snapshot` redaction only** (redaction ≠ masking, stays mandatory); if no redaction job remains it may be retired — the packet's preflight fixes this against the exact code. Already-masked values → refresh/re-import where Shopify is available, else **"data unavailable"**; **never reconstruct/fabricate PII**. Future allowlist per SEC-2 §G. | **ACCEPT Option 1.** |
| TA-C6 | **Inbound fulfillment evidence architecture** (Wave 4 baseline): per-fulfillment binding, per-line reconciliation evidence, origin classification (unknown → external), exact per-line quantity ledger, deterministic lots/serials only on deterministic evidence, unique-GID/no-duplicate-application constraints, stock-application audit, carrier-Delivered never validates stock. | **ACCEPT** as the Wave 4 design baseline. |
| TA-C7 | **Inventory CAS contract (semantic).** Read current remote quantity → compare against last-known → **set the absolute Odoo-authoritative quantity** via Shopify-supported compare-and-set; **fail closed on schema drift**; **never `ignoreCompareQuantity`**. The **exact GraphQL argument name is NOT frozen** (`compareQuantity` vs `changeFromQuantity`) — resolved by the blocking Wave-3 empirical preflight (EQ-D1). | **ACCEPT the semantic requirement**; field name deferred to EQ-D1. |
| TA-C8 | **Performance architecture / SLOs.** Adopt the measurement framework now; the new-domain rows (PB-24p..30p) are **provisional** until PERF-1/Wave 6 measurement; the **existing accepted PB-1..23 budgets (incl. PB-19 ≥600 jobs/h and PB-20 ≥300 inv-pushes/h) remain binding**; **no invented final release thresholds** (silence is not a waiver). | **ACCEPT the framework**; numeric release thresholds provisional except already-accepted PB rows. |

### Class D — empirical preflight questions (classification validated)
Each of EQ-D1..D7 carries an exact wave, owner, official/live source, fail-closed
behavior, and blocking classification (Class D table above). **D1** (CAS field
name) is **BLOCKING before any inventory mutation**; **D2** (mutation idempotency
uncertainty) defaults to **reconciliation-before-retry**; **D3** (unknown webhook
origin) defaults to **external/manual review**; **D4** (unknown throttle) uses
**conservative limits**; **D5** (performance) stays **provisional until measured**;
**D6** (schema/enum drift) **stores raw values and stops unsafe automation**; **D7**
read-only Wave-2 live evidence **may defer to Wave 6**, while mutation evidence for
Waves 3–5 is **blocking**. No empirical question is converted into a guessed
architecture fact.

### Class E — post-MVP (confirmed)
Optional PII masking/privacy enhancement; abandoned-checkout recovery **workspace**;
advanced **accounting**; **refunds**; **payout reconciliation**; **B2B**;
**subscriptions**; **gift cards**; **Shopify Markets**; advanced **analytics**;
**app-store packaging** — all **post-MVP**. **Operational COD reconciliation
remains MVP; automatic accounting posting remains outside MVP.**

### Standing boundaries after these decisions
No `addons/**` change; no implementation authorized; **DEC-031 Layer 2 not
DEC-accepted**; **Wave 2 unauthorized and unstarted**. The next authorized activity
is a **separate Wave 2 decision-acceptance + Definition-of-Ready + packet
re-acceptance + exact-base preflight session** — not Wave 2 implementation.

---

**Class A is confirmed; every Class B item is decided; every Class C item is
decided or routed to a named dedicated gate; Class D is safely classified;
Class E is post-MVP. DEC-031 Layer 2 is not DEC-accepted and Wave 2 remains
unauthorized and unstarted.**
