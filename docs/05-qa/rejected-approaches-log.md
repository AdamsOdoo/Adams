# Rejected Approaches Log

> Captures approaches we **explicitly decided not to use**, so they are not
> reintroduced later. Per `CLAUDE.md` §10, before proposing any architecture or
> implementation approach, **check this log** — do not re-propose a rejected
> approach unless its **Future revisit condition** is met (and say so).

## How to use

1. Add a row whenever an approach is rejected (in design, review, or
   implementation).
2. **Why rejected** + **Evidence / reasoning** must be concrete enough that a
   future session understands the rejection without re-deriving it.
3. **Future revisit condition** states the specific change that would make the
   approach worth reconsidering. If revisiting, route via the
   [architecture-review log](./architecture-review-log.md).
4. Link the accepted alternative's ADR in **Related decision record**, if any.

---

## Log

| ID | Date | Rejected approach | Why rejected | Evidence / reasoning | Future revisit condition | Related decision record |
| --- | --- | --- | --- | --- | --- | --- |
| _RA-000_ | _YYYY-MM-DD_ | _Approach we will not use_ | _Core reason_ | _Concrete evidence/reasoning_ | _What would change our mind_ | _ADR link, if any_ |
| RA-001 | 2026-07-01 | **Option C — Thin import-only pilot** as the MVP scope (import + manual sync only; no webhooks/reconciliation/write-back) | Violates the correctness non-negotiables — a webhook-less/cron-only sync with no reconciliation is a demonstrated market anti-pattern (`../01-research/avoid-list.md`); removes the back-office value; "small but not excellent" | Evaluated as an MVP-scope option alongside Option A (accepted) during RB-13 and explicitly rejected by ChatGPT in the DEC-003 decision record | Would need a documented reason the correctness spine (webhooks + reconciliation + write-back) is infeasible for the MVP substrate — no such evidence exists today | [`../04-decisions/DEC-003-mvp-scope.md`](../04-decisions/DEC-003-mvp-scope.md) ("Accepted MVP option" section) |
| RA-002 | 2026-07-02 | REST-heavy Shopify API strategy for Phase 1 (AR-002 Option D) | `[Official fact]` REST is legacy as of 2024-10-01; `[Official limitation]` GraphQL is signalled the sole long-term API; the 2,048-variant product model degrades off the GraphQL product APIs; no current evidence supports it | Evaluated as an AR-002 candidate in `ar-002-distribution-api-framing.md`; the only real-world precedent (VentorTech) migrated **away** from REST (v2.0.0, 2026-01-23) | A Shopify reversal of the GraphQL-primary direction, or a documented REST-only requirement for a needed resource with no GraphQL equivalent | [`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-003 | 2026-07-02 | Public Shopify App Store distribution / OAuth public-app flow / Billing API as a Phase 1 architecture requirement (AR-002 Option A as Phase 1) | Carries the full App-Store burden (3 mandatory compliance webhooks, protected-data "Requires review," Billing API, Built-for-Shopify performance thresholds) that DEC-003 already defers as product scope; this is the matching architecture-mechanism deferral, not a duplicate of the product-scope one | Evaluated as an AR-002 candidate in `ar-002-distribution-api-framing.md`; DEC-003 non-goals already exclude public App-Store packaging "unless distribution is later decided" | A future, ChatGPT-approved decision to pursue public App Store distribution for Phase 2+ | [`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-004 | 2026-07-02 | OCA `queue_job` as the Phase 1 DEFAULT sync-orchestration substrate (AR-003 Option 3 as default; `queue_job` itself is NOT rejected, only its default-substrate role) | Non-core community dependency; Odoo.sh `server_wide_modules`/external-Jobrunner support is **not confirmed** by official docs (2026-07-02 refresh — silence, not a documented denial); competitor evidence (VentorTech) shows real `odoo.conf`-edit install friction; DEC-003's effortless-onboarding intent argues against depending on an unconfirmed hosting capability as the *default* | Evaluated as an AR-003 candidate in `ar-003-sync-orchestration-framing.md` and the 2026-07-02 evidence refresh (`../03-architecture/ar002-ar003-ar005-evidence-refresh.md`) | Odoo.sh (or on-prem) officially documents/demonstrates `server_wide_modules` + turnkey Jobrunner support, or MVP-scale throughput proves insufficient under the internal cron-queue | [`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-005 | 2026-07-02 | Reuse of `ir.model.data` as the PRIMARY per-store binding/dedup mechanism (AR-005 Option C as primary; `ir.model.data` itself is not rejected for all uses) | `[Official source-code fact]` has `UniqueIndex('(module, name)')` and is designed for third-party data sync in principle, but has **no per-store column, no binding-status/audit fields**, and its `module`/`noupdate` semantics are tied to module-data lifecycle — a poor fit for a multi-store-safe, auditable runtime binding store | Evaluated as an AR-005 candidate in `ar-005-binding-dedup-framing.md` and the RB-14 Part 2 source-code resolution (`../03-architecture/rb14-part2-open-question-resolution.md`, RQ-005-3) | Official evidence that `ir.model.data` gains a per-store/audit-capable shape (no realistic path known; would need core changes) | [`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-006 | 2026-07-02 | Name-only automatic product/customer matching (AR-005) | No evidence supports it as safe; directly contradicts the DEC-003 mandatory "no automatic name-only matching" + duplicate-prevention-preview rules; the classic root cause of connector duplicate-record defects | Evaluated as an AR-005 matching-priority question in `ar-005-binding-dedup-framing.md`; DEC-003 already requires SKU/barcode-first matching with ambiguous → manual review | None anticipated — would need a demonstrated, safe disambiguation method that does not exist today | [`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-007 | 2026-07-02 | External worker / out-of-Odoo processor as the Phase 1 sync-orchestration substrate (AR-003 Option 4) | Heaviest operational/deployment/security/monitoring surface; no competitor demonstrates it; contradicts DEC-003 install-and-go / Early Access simplicity | Evaluated as AR-003 Option 4 in `../04-decisions/DEC-005-sync-orchestration-strategy.md`; Phase 1 already has the Odoo.sh/on-prem internal cron-queue direction proposed; no evidence justifies a separate worker for single-store MVP | Serious throughput/hosting limitation proven after MVP-scale testing, or a later enterprise deployment explicitly accepts external infrastructure | [`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-008 | 2026-07-02 | blind first Odoo→Shopify inventory push (no preview, no operator confirmation, no mapped-location check before the first write) | Risks overwriting **live** Shopify stock on the very first write, before an operator has reviewed the quantities, the location mapping, or the assumed source-of-truth; the Shopify → Odoo import direction already requires a controlled/reviewed apply (DEC-003) and the symmetric Odoo → Shopify direction is the one that can damage a live storefront | Evaluated as part of the DEC-007 first-inventory-push-guard clarification (scope hole 3); no evidence supports skipping preview/confirmation for a live-storefront-affecting first write | A demonstrated, equally-safe automated guard that does not require operator confirmation (none anticipated) | [`../04-decisions/DEC-007-phase1-scope-clarifications.md`](../04-decisions/DEC-007-phase1-scope-clarifications.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-009 | 2026-07-02 | fulfilment/tracking write-back with a hidden, silent, or default-on customer-notification side effect | Customers should not be surprised by an unintended shipping-notification email triggered by a back-office sync action; `[Official fact]` Shopify's own `FulfillmentInput.notifyCustomer` defaults to `false` and `fulfillmentTrackingInfoUpdate`'s `notifyCustomer` defaults to no notification, so a connector default of "on" or an opaque setting would be a self-inflicted risk with no platform requirement behind it | Evaluated as part of the DEC-007 fulfilment customer-notification clarification (scope hole 4), grounded in the newly verified Shopify defaults cited in that record | A demonstrated operator need for opaque/automatic notification with no visibility (none anticipated) | [`../04-decisions/DEC-007-phase1-scope-clarifications.md`](../04-decisions/DEC-007-phase1-scope-clarifications.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-010 | 2026-07-02 | automatic full accounting/payment reconciliation (automatic posted invoices/payments, bank reconciliation, or payout reconciliation) as default Phase 1 order-import behaviour | Contradicts the already-accepted DEC-003 Domain 9 rule ("MVP preserves financial evidence and order actionability; it does not automate accounting"); pulls a large, edition-sensitive accounting surface into a correctness-core MVP; risks double-invoice/double-payment on retry without idempotency | Evaluated as part of the DEC-007 tax/shipping/discount/payment clarification (scope hole 5), which reaffirms — as an explicit mechanism-level rejection, not previously logged here — the existing DEC-003 accounting-automation exclusion | A future, ChatGPT-approved decision to include full accounting automation as an explicit, idempotent, opt-in Phase 2/3 module | [`../04-decisions/DEC-007-phase1-scope-clarifications.md`](../04-decisions/DEC-007-phase1-scope-clarifications.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-011 | 2026-07-02 | one giant `shopify_connector` module (AR-004 Option 1 — every domain, transport, queue, binding, and UI in a single module) | Contradicts the accepted product-vision modularity principle and `CLAUDE.md` §9; matches the named competitor anti-pattern A-MOD-1 (poor isolation, hard maintenance, coupling risk); fails the accepted per-domain enable/disable requirement (`../02-product/product-vision.md` principle 6; `../02-product/feature-taxonomy.md` CC-6/CC-7) — a merchant could not selectively disable fulfilment write-back without custom code | Evaluated as AR-004 Option 1 in `../03-architecture/ar004-module-boundary-decision-brief.md`; no evidence in the corpus supports a monolithic module over a layered addon family | A demonstrated Phase 1 case where domain separation itself (not implementation effort) is harmful — none anticipated | [`../04-decisions/DEC-008-module-boundary-strategy.md`](../04-decisions/DEC-008-module-boundary-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-012 | 2026-07-02 | per-feature micro-module explosion for Phase 1 (AR-004 Option 2 — a separate installable module per fine-grained capability, e.g. one module each for price sync, image sync, tax-line capture) | Matches the named competitor anti-pattern A-MOD-2 (over-fragmentation, dependency-coupling overhead); fine-grained capabilities inside one domain share the same binding record and job/queue substrate and are enabled/disabled together in practice, so splitting them buys no operator-visible independence | Evaluated as AR-004 Option 2 in `../03-architecture/ar004-module-boundary-decision-brief.md`; no Phase 1 capability needs sub-domain-level independent activation | A demonstrated Phase 1 need to enable one fine-grained capability (e.g. image sync) independently of its parent domain (e.g. product sync) — none anticipated | [`../04-decisions/DEC-008-module-boundary-strategy.md`](../04-decisions/DEC-008-module-boundary-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-013 | 2026-07-02 | duplicating the queue/job/log/binding abstractions in each domain module separately, instead of sharing them via `shopify_connector_core` | Produces duplicated code, inconsistent error-class taxonomies across domains, and breaks the single recovery-first error-center UX that DEC-003 requires as a non-negotiable; makes DEC-006's audit-field shape (matched-by/at, source strategy, match key, status) harder to keep consistent across bindings | Evaluated in `../03-architecture/ar004-module-boundary-decision-brief.md` §"Rejected or weakened alternatives"; DEC-005/006 already require one consistent job/log/binding shape across the connector | Evidence that a specific domain's job/log/binding needs are irreconcilably incompatible with a shared core abstraction — none anticipated | [`../04-decisions/DEC-008-module-boundary-strategy.md`](../04-decisions/DEC-008-module-boundary-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-014 | 2026-07-02 | retry-everything automatically regardless of error class (AR-006 Option A) | Violates DEC-003's explicit "retry classification concept" requirement; risks double-acting on non-idempotent operations since most Shopify mutations have no platform idempotency guarantee (only 17 mutations support `@idempotent`); matches avoid-list A-RET-3 ("naive retry that double-acts") | Evaluated as AR-006 Option A in `../03-architecture/ar006-error-retry-idempotency-decision-brief.md`; `[Official limitation]` no general/all-mutation Shopify idempotency exists | Both of the following would need to be true: (1) Shopify/platform idempotency becomes general enough to prevent double-acting across all mutations, **and** (2) a proven classifier or platform signal exists that distinguishes transient from permanent failures without operator risk. None anticipated; even broad platform idempotency would not make permanent validation/configuration errors safe to retry blindly — an idempotent replay of a request that is rejected for the same reason every time still wastes throttle budget and delays the operator seeing an error that requires a fix, not a retry | [`../04-decisions/DEC-009-error-retry-idempotency-strategy.md`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-015 | 2026-07-02 | never-retry-anything automatically / manual-only recovery (AR-006 Option B) | Contradicts DEC-003's "safe manual retry" and "retry classification concept" (which implies some classes are auto-retryable); reproduces avoid-list A-RET-1 ("manual-only recovery... only VT auto-retries"); forces an operator to babysit routine transient errors such as rate-limit throttling | Evaluated as AR-006 Option B in `../03-architecture/ar006-error-retry-idempotency-decision-brief.md`; competitor evidence shows only one connector (VentorTech) auto-retries, and the market gap is flagged as a differentiation opportunity (O-REL-3) | A demonstrated safety reason that automatic retry of clearly transient/idempotent-safe errors is harmful — none anticipated | [`../04-decisions/DEC-009-error-retry-idempotency-strategy.md`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-016 | 2026-07-02 | user-facing stack traces as the primary error message | Contradicts the DEC-003 recovery-first UX spine; matches avoid-list A-LOG-1/A-LOG-3 (email-only/technical error handling; logs without a human-readable reason) | Evaluated in `../03-architecture/ar006-error-retry-idempotency-decision-brief.md` §7 (user-facing log requirements); no evidence supports raw technical output as a primary UX for a non-developer operator | A demonstrated operator preference for raw technical detail as the primary view (technical details remain available on demand, just not primary) — none anticipated | [`../04-decisions/DEC-009-error-retry-idempotency-strategy.md`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-017 | 2026-07-02 | no connector-designed idempotency key / relying on the binding alone to prevent duplicate operations (binding-first retry strategy with no per-operation idempotency key) | The binding prevents *identity* duplication (the same Shopify record mapping to two Odoo records) but not *operation* duplication (two retries of the same mutation against an already-correctly-bound record); DEC-006 explicitly names the binding as the home for idempotency keys, not a substitute for them | Evaluated in `../03-architecture/ar006-error-retry-idempotency-decision-brief.md` §"Rejected or weakened alternatives"; `[Official limitation]` the Shopify `@idempotent` surface covers only 17 mutations with a 24-hour TTL, leaving every other write needing a connector-designed key | Evidence that Shopify's own idempotency mechanism becomes general-purpose (no general mechanism exists today) — none anticipated | [`../04-decisions/DEC-009-error-retry-idempotency-strategy.md`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-018 | 2026-07-02 | writing Shopify's `committed` inventory quantity (AR-007 Phase 1 inventory architecture) | `[Official limitation]` `committed` is API-read-only — it changes only via order creation/fulfillment, never via the Admin API; attempting to write it produces an API error or a meaningless write with no effect, and misrepresents the inventory model to the operator | Formalizes avoid-list `A-INV-3` context (`../01-research/avoid-list.md`) now that AR-007 is under formal review; **citation corrected (PR #66 Fable review) — `A-INV-2` belongs to RA-019 (single-location/SKU-only), not this row**; evaluated in `../03-architecture/ar007-inventory-architecture-decision-brief.md` §"Rejected or weakened alternatives"; already an accepted DEC-003 MVP rule ("`committed` must never be written") — this row formalizes it as an AR-007 architecture-level rejection, not a re-litigation of DEC-003 | A future Shopify API change making `committed` independently writable (no evidence of this today) | [`../04-decisions/DEC-010-inventory-architecture-strategy.md`](../04-decisions/DEC-010-inventory-architecture-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-019 | 2026-07-02 | single-location-only inventory design, or inventory writes keyed by SKU alone without per-location (`inventory_item_id` + `location_id`) binding identity (AR-007 Phase 1 inventory architecture) | A single-location design is a demonstrated market anti-pattern (Webkul); SKU-only writes double-decrement multi-location SKUs because Shopify's InventoryLevel is per-location, not per-item; both stem from the same root cause — missing per-location identity in the write path | Formalizes avoid-list `A-INV-2` (`../01-research/avoid-list.md`, "Arch review: YES (AR-007)"); evaluated in `../03-architecture/ar007-inventory-architecture-decision-brief.md` §2/§4/§"Rejected or weakened alternatives"; consistent with the already-accepted DEC-006 requirement that inventory identity needs `inventory_item_id` + `location_id` | A demonstrated Phase 1 case where per-location identity is provably unnecessary — none anticipated (multi-location-awareness is an accepted DEC-003 MVP requirement) | [`../04-decisions/DEC-010-inventory-architecture-strategy.md`](../04-decisions/DEC-010-inventory-architecture-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-020 | 2026-07-02 | autonomous bidirectional inventory conflict resolution in Phase 1 (both systems independently change quantities and the connector automatically merges/resolves conflicts) | Mirrors the already-accepted DEC-003 exclusion of "unrestricted autonomous bidirectional catalog ownership" for the closely analogous product domain, with higher stakes for inventory (an incorrect automatic merge directly risks overselling/underselling live stock, with no draft/unpublished safety net); the DEC-009 ambiguous-outcome rule and `blocked_manual_review` state exist precisely because Shopify write outcomes cannot always be safely inferred — an autonomous conflict engine would have to guess in exactly the cases DEC-009 already routes to manual review | Evaluated in `../03-architecture/ar007-inventory-architecture-decision-brief.md` §1; no competitor evidence in the repo demonstrates a safe autonomous bidirectional inventory-conflict engine (`../01-research/common-patterns.md`, `../01-research/best-in-class-observations.md`) | A demonstrated, safe conflict-resolution algorithm with an accepted field-ownership model — none anticipated for Phase 1 | [`../04-decisions/DEC-010-inventory-architecture-strategy.md`](../04-decisions/DEC-010-inventory-architecture-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-021 | 2026-07-02 | treating Shopify and Odoo inventory quantities as directly equivalent without an explicit source-of-truth and documented quantity-field semantics (AR-007 Phase 1 inventory architecture) | Shopify's `on_hand` is a sum (`available + committed + reserved + damaged + safety_stock + quality_control`) while Odoo's report-level "On Hand"/"Free to Use"/"Forecasted" concepts have distinct, non-identical semantics (`../03-architecture/ar007-ar008-evidence-refresh.md`); silently assuming any Odoo quantity number equals any Shopify quantity field risks pushing the wrong number and violates DEC-007's requirement for a *recorded* source-of-truth decision on every first push | Evaluated in `../03-architecture/ar007-inventory-architecture-decision-brief.md` §1/§3; grounded in `[Official fact]` Shopify's quantity-state formula (`../01-research/shopify-official-api-notes.md`) and the newly-verified Odoo report-level definitions (`../03-architecture/ar007-ar008-evidence-refresh.md`) | **Corrected (PR #66 Fable review) — covers both required conditions:** (1) an **explicit, recorded source-of-truth decision** governing which system's number is authoritative for a given write, **and** (2) **official, documented confirmation** that a specific Odoo quantity field and a specific Shopify quantity field are formally equivalent in every case — neither is established today; both would need to hold before this approach is revisited | [`../04-decisions/DEC-010-inventory-architecture-strategy.md`](../04-decisions/DEC-010-inventory-architecture-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-022 | 2026-07-02 | legacy Order/Fulfillment API flow instead of FulfillmentOrder-based mutations (AR-008 Phase 1 fulfillment architecture) | `[Official fact]` the legacy Order/Fulfillment workflow is unsupported as of API version 2022-07, and all apps should use the FulfillmentOrder object by 2023-07; using it would build the connector's fulfillment feature on an unsupported API surface | Formalizes avoid-list `A-FUL-1` (`../01-research/avoid-list.md`, "Arch review: YES (AR-008)"); evaluated in `../03-architecture/ar008-fulfillment-architecture-decision-brief.md` §2/§"Rejected or weakened alternatives"; `../01-research/shopify-official-api-notes.md` (Fulfillment and tracking section) | A Shopify reversal reinstating the legacy workflow — no evidence of this; none anticipated | [`../04-decisions/DEC-011-fulfillment-architecture-strategy.md`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-023 | 2026-07-02 | creating a Shopify fulfillment by order ID alone, or treating every validated Odoo picking as automatically safe to fulfill, without explicit FulfillmentOrder/line-item/quantity/location matching (AR-008 Phase 1 fulfillment architecture) | An order can have more than one open FulfillmentOrder (one per location/routing rule); fulfilling "the order" without matching the specific FulfillmentOrder, line items, quantities, and location risks fulfilling the wrong lines, the wrong quantities, or the wrong location, and risks double-fulfilling lines already covered by a prior partial fulfillment | Evaluated in `../03-architecture/ar008-fulfillment-architecture-decision-brief.md` §2/§5/§"Rejected or weakened alternatives"; grounded in `[Official fact]` `fulfillmentCreate`'s `lineItemsByFulfillmentOrder` parameter and the FulfillmentOrder-per-location model (`../01-research/shopify-official-api-notes.md`) | **Corrected (PR #66 Fable review) — no longer self-negating:** none anticipated. Explicit FulfillmentOrder/line-item/quantity/location matching remains required even for single-FulfillmentOrder, single-location stores, so no future condition is expected to make implicit/order-ID-only matching safe | [`../04-decisions/DEC-011-fulfillment-architecture-strategy.md`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |

_No approaches rejected yet, **as of Research Sprints A–C** — historical for
that period only; **superseded for the log overall by RA-001** (added
2026-07-02, Control-Room Reset Sprint 1, from DEC-003's Option C rejection;
see the Log table above). Entries begin once design options are evaluated and
ChatGPT/architecture review formally rejects one._

_**Research Sprint C note (2026-06-30):** the competitor research produced an
**avoid-list** of competitor anti-patterns —
[`../01-research/avoid-list.md`](../01-research/avoid-list.md). Those items are
**recommendations/inferences, NOT rejected-approach decisions**: they describe
mistakes **competitors** made (e.g. webhook-only/cron-only sync, `ir.cron`-as-a-
queue, manual-only recovery, email-only errors, single-location inventory,
"real-time" mislabelling, bot-blocked/gated docs). Per `CLAUDE.md` §10 and this
log's rules, an approach is only entered here as **Rejected** after it is
evaluated for **our** design and ChatGPT/architecture review rejects it. The
avoid-list items tagged "Arch review: YES" are seeded against AR-002…AR-008
(evidence-pending) and will route through the architecture-review log first. **No
approach is rejected in this sprint.**_

_**Research/Product Sprint D note (2026-07-01):** **none.** Sprint D was a
product-synthesis sprint (canonical feature taxonomy + capability evidence map). It
**evaluated no design option to rejection** — capability classifications
(baseline / premium / advanced-later / optional add-on / unknown) and MVP-relevance
tags are **inputs** for the gated RB-13 (MVP) and RB-14 (architecture) reviews, not
rejections. The taxonomy's "Capabilities with weak or blocked evidence" section
records competitor claims that are **not adopted as demonstrated** (e.g. Teqstars
docs-403 claims, WK config-field-only multi-company) — these are **evidence
downgrades under DP-003/DP-004, not rejected approaches**. No entry is added here._

_**Product Sprint E note (2026-07-01): none.** Sprint E was a product-strategy /
synthesis sprint (product vision + setup/UX principles). It **evaluated no design
option to rejection** — the product principles, premium quality bar, differentiation
themes, non-negotiables, and UX principles are **inputs** for the gated RB-13 (MVP)
and RB-14 (architecture) reviews, not rejections. The vision's "What we will avoid"
section and the UX doc's "Anti-patterns to avoid" restate the Sprint C **avoid-list**
(competitor anti-patterns) as **recommendations/inferences**, which — per `CLAUDE.md`
§10 and this log's rules — become formal rejections **only after** they are evaluated
for our design and ChatGPT/architecture review rejects them (the "Arch review: YES"
items remain seeded against AR-002…AR-008, evidence-pending). No approach is rejected
in this sprint; no entry is added here._

_**Product Sprint F note (2026-07-01): none.** Sprint F was an MVP-proposal / synthesis
sprint (MVP scope proposal + non-MVP boundaries + user stories). It **evaluated no design
option to rejection.** Items placed outside the MVP in
`../02-product/non-mvp-and-later-phases.md` (export, full payments/refunds/returns/
cancellations, payouts, multi-package fulfilment, order risk, SEO/BoM/pricelists/
per-market, Markets/B2B/POS/gift cards/metafields/extended breadth, multi-store/company,
custom transforms, analytics, App-Store/demo packaging) are **recommendations against
MVP inclusion only** — each carries a "what must be true before including" **revisit
condition** and a later phase. Per `CLAUDE.md` §10 and this log's rules, an approach is
entered here as **Rejected** only after it is evaluated for **our** design and
ChatGPT/architecture review rejects it — which has not happened. The weak/blocked
competitor evidence kept out of scope (pHash image dedup, Teqstars 403 breadth, EC/SH
breadth, WK config-field-only multi-company) are **evidence down-weights under
DP-003/DP-004, not rejected approaches**. No entry is added here._

_**Product Sprint G note (2026-07-01): none.** Sprint G recorded ChatGPT's **accepted MVP
scope** (`../04-decisions/DEC-003-mvp-scope.md`) and aligned the product docs. The items
**deferred/excluded from MVP** (**unrestricted autonomous bidirectional catalog ownership** —
all-field two-way conflict resolution, field-ownership matrix, advanced publish/channel
campaign management; **customer export**; refund sync, cancellation reflection, returns/RMA,
full Domain 9 accounting automation, payout/bank reconciliation, multi-package fulfilment,
complex tax, Markets/B2B/POS/gift cards/metafields/subscriptions/abandoned-checkout/
recommendations/Buy-with-Prime, multi-store/multi-company logic, custom transforms, advanced
analytics, public App-Store/demo packaging, and **bulk operations as a user-facing feature**)
are **product-scope boundary decisions with revisit conditions** in
`../02-product/non-mvp-and-later-phases.md` — **not** rejected architecture approaches. Per
`CLAUDE.md` §10 and this log's rules, an approach is entered here as **Rejected** only after
it is evaluated for **our** design and ChatGPT/architecture review rejects it — which had
**not** happened *at Sprint G authoring time* (no AR row is decided). The weak/blocked
competitor evidence kept out of scope (pHash, EC/SH breadth, WK config-field-only multi-company)
are **evidence down-weights under DP-003/DP-004, not rejected approaches**. ~~(TeqStars docs
were 403-blocked in Sprint C but re-checked accessible 2026-07-01; a full rebaseline is
pending.)~~ **Superseded:** the full TeqStars rebaseline was completed the same day
(Research Sprint C2, PR #56, 2026-07-01) — see `../01-research/competitor-feature-matrix.md`.
No entry was added in Sprint G itself, but **DEC-003 — recorded in this same Sprint G —
did explicitly reject an MVP-scope option ("Option C — Thin import-only pilot"); that
rejection was later logged here as RA-001** in Control-Room Reset Sprint 1 (2026-07-02),
after being found missing from this log during a residue sweep._

_**Product Sprint G revision note (2026-07-01, PR #55): still none.** ChatGPT's PR #55
correction moved **controlled product export/update INTO MVP** (product export is **not**
deferred) and kept **unrestricted autonomous bidirectional catalog ownership** and **customer
export** later. This is a **product-scope correction** — **no approach was rejected**, so no
entry is added here._

_**Evidence Refresh + Combined AR-002/003/005 Decision Preparation (2026-07-02) — RA-002 through
RA-006 originally added, marked PROPOSED (history).** Unlike RA-001 (added only **after** ChatGPT
accepted DEC-003), RA-002–RA-006 were added **alongside** their DEC-004/005/006 proposals, per
that sprint's explicit instruction to log rejected/deferred approaches "if the proposed decisions
explicitly reject them." Each row was tagged **PROPOSED** at the time, citing the DEC file's own
then-current `Status: Proposed for ChatGPT review` — **at that time none of these was a final
rejection.** No approach outside the five tied to DEC-004/005/006 was evaluated to rejection in
that sprint; DEC-003's non-MVP deferrals were not re-logged there (see the Sprint G note above).
**Superseded by the acceptance note below** — all six rows (plus RA-007) are now final._

_**PR #60 minor revision (2026-07-02, ChatGPT + Fable review — ACCEPT WITH MINOR CHANGES) —
RA-007 added (history).** Fable flagged a dangling pointer: DEC-005's rejected-options table
cited this log for AR-003 Option 4 (external worker) with no corresponding row. Added **RA-007**
(external worker as the Phase 1 sync-orchestration substrate), tagged **PROPOSED** at the time,
same pattern as RA-002–RA-006. **Superseded by the acceptance note below.**_

_**DEC-004/005/006 Acceptance Patch (2026-07-02) — RA-002 through RA-007 are now binding final
rejected approaches.** ChatGPT formally accepted
[`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md),
[`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md),
and [`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md)
on **2026-07-02** (after PR #60 merged into `Shopify-connector`, merge commit
`7eb875e4ca29b80c4745bd8f5354450aa1e4d37b`, and Fable's minor-change review was applied). The
**`PROPOSED:` prefix has been removed** from RA-002 through RA-007's titles and their "Related
decision record" cells now cite each DEC file's `Status: Accepted by ChatGPT, 2026-07-02`. Per
`CLAUDE.md` §10, **the do-not-re-propose bar now applies in full** to these six rows — they are no
longer "candidate rejections under review" but **binding final rejections**, on the same footing
as RA-001, and may only be revisited via their stated **Future revisit condition**, routed through
`architecture-review-log.md`. This acceptance does **not** authorize implementation; DEC-003 and
MVP scope remain unchanged; AR-004/AR-006/AR-007/AR-008 remain not decided._

_**Phase 1 Domain Model + DEC-003 Scope-Hole Closure sprint (2026-07-02) — RA-008, RA-009, RA-010
added, tagged PROPOSED (history, not yet final at the time).** Following the same pattern as
RA-002–RA-007 (added alongside their DEC proposal, not after acceptance), this sprint added three
rows tied to the then-proposed
[`DEC-007`](../04-decisions/DEC-007-phase1-scope-clarifications.md)
(`Status: Proposed for ChatGPT review` at that time): **RA-008** (blind first Odoo→Shopify
inventory push), **RA-009** (fulfilment write-back with a hidden/default-on customer-notification
side effect), and **RA-010** (automatic full accounting/payment reconciliation as default Phase 1
behaviour). Per `CLAUDE.md` §10 and this log's governance rule, these three rows were **non-binding
candidate rejections until DEC-007 was accepted** by ChatGPT — the same footing RA-002–RA-006 held
before the DEC-004/005/006 acceptance patch above. **Automatic name-only product/customer matching
was considered and NOT re-logged here** — it is already covered by the binding **RA-006**
(`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`, Accepted), so adding a near-duplicate
row was avoided per this sprint's explicit instruction. **Superseded by the acceptance note
below.**_

_**DEC-007 Acceptance Patch (2026-07-02) — RA-008 through RA-010 are now binding final rejected
approaches.** ChatGPT formally accepted
[`../04-decisions/DEC-007-phase1-scope-clarifications.md`](../04-decisions/DEC-007-phase1-scope-clarifications.md)
on **2026-07-02** (after PR #62 merged into `Shopify-connector` and Fable's minor-change review —
**ACCEPT WITH MINOR CHANGES** — was applied). The **`PROPOSED:` prefix has been removed** from
RA-008 through RA-010's titles and their "Related decision record" cells now cite DEC-007's
`Status: Accepted by ChatGPT, 2026-07-02`. Per `CLAUDE.md` §10, **the do-not-re-propose bar now
applies in full** to these three rows — they were "proposed alongside DEC-007" and are now, on this
acceptance, **binding final rejections**, on the same footing as RA-001–RA-007, and may only be
revisited via their stated **Future revisit condition**, routed through
`architecture-review-log.md`. This acceptance does **not** authorize implementation; DEC-003 and
DEC-004/005/006 remain unchanged; AR-004/AR-006/AR-007/AR-008 remain not decided._

_**AR-004 + AR-006 Decision Preparation (2026-07-02) — RA-011 through RA-017 added, tagged
PROPOSED (non-binding until DEC-008/DEC-009 are accepted).** Following the same pattern as
RA-002–RA-010 (added alongside their DEC proposal, not after acceptance), this sprint added
seven rows tied to the then-proposed
[`DEC-008`](../04-decisions/DEC-008-module-boundary-strategy.md) (AR-004, three rows:
RA-011 one giant module, RA-012 per-feature micro-module explosion, RA-013 duplicated
queue/job/log/binding abstractions per domain) and
[`DEC-009`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md) (AR-006, four
rows: RA-014 retry-everything automatically, RA-015 never-retry-automatically/manual-only
recovery, RA-016 user-facing stack traces as primary error UX, RA-017 no connector-designed
idempotency key / binding-alone retry strategy), both `Status: Proposed for ChatGPT review`
at the time of this note. Per `CLAUDE.md` §10 and this log's governance rule, these seven
rows are **non-binding candidate rejections until DEC-008/DEC-009 are accepted** by
ChatGPT — the same footing RA-002–RA-006 and RA-008–RA-010 held before their respective
acceptance patches. No duplicate of an existing RA row was added (checked against RA-001
through RA-010 before adding). AR-007 and AR-008 remain untouched — no rejected approach
tied to inventory or fulfilment internal design was evaluated or added. This entry does not
itself finalize RA-011–017; a future acceptance patch (mirroring the DEC-004/005/006 and
DEC-007 patches above) will remove the PROPOSED prefix if and when ChatGPT accepts
DEC-008/DEC-009._

_**DEC-008/DEC-009 Acceptance Patch (2026-07-02) — RA-011 through RA-017 are now binding
final rejected approaches.** ChatGPT formally accepted
[`../04-decisions/DEC-008-module-boundary-strategy.md`](../04-decisions/DEC-008-module-boundary-strategy.md)
and
[`../04-decisions/DEC-009-error-retry-idempotency-strategy.md`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md)
on **2026-07-02** (after PR #64 merged into `Shopify-connector`, merge commit
`e4c74abf0e3b4ad32e66413d27b40287ed4c5822`, and Fable's minor-change review — **ACCEPT WITH
MINOR CHANGES** — was applied). RA-011 through RA-017 were **proposed alongside**
DEC-008/DEC-009, per the same pattern as RA-002–RA-010: each was added at proposal time,
not after acceptance. The **`PROPOSED:` prefix has been removed** from RA-011 through
RA-017's titles and their "Related decision record" cells now cite each DEC file's
`Status: Accepted by ChatGPT, 2026-07-02`. Per `CLAUDE.md` §10, **the do-not-re-propose bar
now applies in full** to these seven rows — they are no longer "candidate rejections under
review" but **binding final rejections**, on the same footing as RA-001–RA-010, and **may
only be revisited through their stated Future revisit condition and the architecture-review
process** (`architecture-review-log.md`). This acceptance does **not** authorize
implementation; DEC-003/004/005/006/007 remain unchanged; AR-007/AR-008 remain not
decided._

_**AR-007 + AR-008 Decision Preparation (2026-07-02) — RA-018 through RA-023 added, tagged
PROPOSED (non-binding until DEC-010/DEC-011 are accepted).** Following the same pattern as
RA-002–RA-017 (added alongside their DEC proposal, not after acceptance), this sprint added
six rows tied to the then-proposed
[`DEC-010`](../04-decisions/DEC-010-inventory-architecture-strategy.md) (AR-007, four rows:
RA-018 writing Shopify's read-only `committed` quantity, RA-019 single-location-only/
SKU-only inventory writes without per-location binding identity, RA-020 autonomous
bidirectional inventory conflict resolution in Phase 1, RA-021 treating Shopify/Odoo
inventory quantities as equivalent without an explicit source-of-truth) and
[`DEC-011`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md) (AR-008, two rows:
RA-022 legacy fulfillment API flow instead of FulfillmentOrder-based mutations, RA-023
fulfillment creation without FulfillmentOrder/line/quantity/location matching), both
`Status: Proposed for ChatGPT review` at the time of this note. Per `CLAUDE.md` §10 and this
log's governance rule, these six rows are **non-binding candidate rejections until
DEC-010/DEC-011 are accepted** by ChatGPT — the same footing RA-002–RA-017 held before their
respective acceptance patches. **Checked against RA-001 through RA-017 before adding — no
duplicate row was added.** Specifically: blind first Odoo→Shopify inventory push
(already **RA-008**), hidden/default-on fulfilment customer notification (already
**RA-009**), blind retry of fulfillment creation after ambiguous timeout / retry-everything
automatically (already **RA-014**), and relying on the binding alone for operation
idempotency (already **RA-017**) were evaluated and **not** re-logged — the AR-007/AR-008
briefs reference the existing rows instead. Multi-package/multi-location fulfillment
automation in Phase 1 was evaluated and **not** logged as a rejection — it is an existing
**deferral** (not a rejection) under DEC-003/`non-mvp-and-later-phases.md` (C-FUL-02).
Webhook-only inventory sync without reconciliation was evaluated and **not** logged as a new
row — it is already governed by the accepted DEC-005 layered-sync policy. This entry does
not itself finalize RA-018–023; a future acceptance patch (mirroring the DEC-004/005/006,
DEC-007, and DEC-008/009 patches above) will remove the PROPOSED prefix if and when ChatGPT
accepts DEC-010/DEC-011._

_**DEC-010/DEC-011 Acceptance Patch (2026-07-02) — RA-018 through RA-023 are now binding
final rejected approaches.** ChatGPT formally accepted
[`../04-decisions/DEC-010-inventory-architecture-strategy.md`](../04-decisions/DEC-010-inventory-architecture-strategy.md)
and
[`../04-decisions/DEC-011-fulfillment-architecture-strategy.md`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md)
on **2026-07-02** (after PR #66 merged into `Shopify-connector`, merge commit
`14af2fb3becb47ba7c32a50715d85f6eaab0d855`, and Fable's minor-change review — **ACCEPT WITH
MINOR CHANGES** — was applied). RA-018 through RA-023 were **proposed alongside**
DEC-010/DEC-011, per the same pattern as RA-002–RA-017: each was added at proposal time,
not after acceptance. The **`PROPOSED:` prefix has been removed** from RA-018 through
RA-023's titles and their "Related decision record" cells now cite each DEC file's
`Status: Accepted by ChatGPT, 2026-07-02`. Per `CLAUDE.md` §10, **the do-not-re-propose bar
now applies in full** to these six rows — they are no longer "candidate rejections under
review" but **binding final rejections**, on the same footing as RA-001–RA-017, and **may
only be revisited through their stated Future revisit condition and the architecture-review
process** (`architecture-review-log.md`). This acceptance does **not** authorize
implementation; DEC-003/004/005/006/007/008/009 remain unchanged; AR-007 is accepted
through DEC-010 and AR-008 is accepted through DEC-011 (`architecture-review-log.md`); all
architecture decisions AR-002 through AR-008 are now accepted; implementation remains
blocked._
