# MVP Remaining-Gap Inventory (Waves 2–6)

> **Status:** Fable gap-closure mission working document (2026-07-16). Verified
> current-state inventory of every research, product, architecture, UX,
> performance, testing, and readiness gap that stands between the merged Wave 1
> baseline (`mvp/program-integration` @ `1e46c23`, PR #172) and
> implementation-ready Waves 2–6. Produced from a complete repository preflight
> (all of `docs/00`–`docs/09` plus a read-only inventory of
> `addons/shopify_connector_{core,product,sale}`). This document decides
> nothing; it routes work. Each gap is closed by a canonical artifact listed in
> the "Closure artifact" column, produced or updated in this mission.
> Classification labels follow `research-methodology.md` §4 / `CLAUDE.md` §8.

## 1. Verified baseline (what exists and is NOT a gap)

All items below are [Fact — repository state verified 2026-07-16]:

- **Wave 1 merged foundation:** store/connection lifecycle with connection
  generations and two-phase disconnect quiescence; job substrate (10 states,
  legal-transition enforcement, idempotency + operation-scope keys, 16-class
  error taxonomy, retry policy, DEC-031 Layer 1 fail-closed replay-policy
  registry); append-only job log; admission leases; readiness registry;
  binding mixin with fail-closed protected-field classification (16/17/14
  protected sets); product template/variant + customer import with matching,
  duplicate prevention, PII masking/retention; four internal security groups
  (`group_shopify_connector_{auditor,operator,reviewer,admin}`); 32 test files
  incl. extensive source/AST guards. Runtime-green: build `34995642`,
  0 failed / 0 errors / 644 tests.
- **Current official evidence (Tier 1):** Shopify orders/inventory/
  FulfillmentOrder/product/PCD/scopes captures of 2026-07-10/11/15 (API
  2026-07) and Odoo 19 captures — current except the named gaps in §2.
- **Packet base:** Task 012/013/013B/014/015/015B and PERF-1/Area-6/UI packets
  exist at Proposed level with near-complete DoR structure.
- **Accepted decision spine:** DEC-003..DEC-034 (statuses per
  `docs/04-decisions/**` with the known header defects listed in §8).
- **UX base:** accepted design system + `docs/09-ui-prototype/**` accepted
  visual baseline (5 surfaces, token-driven, WCAG-verified).
- **Absent by design (not a defect):** no order-import, inventory, fulfillment,
  product-export, UI, webhook, or DEC-031 Layer 2 implementation exists.

## 2. Research gaps

| # | Gap | Severity | Closure artifact |
|---|---|---|---|
| R-1 | **COD / manual-payment-gateway evidence absent.** No capture of Shopify manual gateways, `OrderTransaction.manualPaymentGateway`, `orderMarkAsPaid`, COD financial-state behavior. | Blocking for Wave 2 product design | `docs/00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md` (new) |
| R-2 | **Abandoned-checkout evidence absent.** No AbandonedCheckout object/query capture (identity, recovery state, `completedAt` conversion, limits). | Blocking for abandoned-checkout policy | same capture file as R-1 |
| R-3 | **Fulfillment-state completeness.** FulfillmentOrder captures exist (2026-07-10/15) but no complete verified map of all four state families (order summary, FulfillmentOrder status/requestStatus, Fulfillment status, FulfillmentEvent milestones) + holds + deprecations. | Blocking for Waves 4 product/UX design | same capture file as R-1; mapped in `docs/02-product/shopify-fulfillment-status-model.md` (new) |
| R-4 | **Competitor corpus currency.** All competitor evidence dated 2026-06-30/07-01 (re-verified 07-04); mission requires a 2026-07-16 refresh incl. COD/reconnect/fulfillment-mode behavior and any new material competitor. | Non-blocking but required output | refresh notes in `docs/00-source-materials/competitor-refresh-2026-07-16.md` (new) + deltas into existing matrix/deep-dives |
| R-5 | **Order sort/filter + order-edit surface.** `OrderSortKeys` values, `orders/edited` implications, order-edit (`CalculatedOrder`) impact on an importer. | Medium (Wave 2 packet detail) | same capture file as R-1 |
| R-6 | **Odoo 19 delivery/backorder/return + free_qty verification.** Source-backed statements exist but no consolidated capture for COD/fulfillment/inventory design (picking states, backorders, returns restoring stock, `free_qty` vs `qty_available`, implied groups). | Blocking for COD/fulfillment/inventory closure | `docs/00-source-materials/odoo19-sale-stock-security-captures-2026-07-16.md` (new) |
| R-7 | **UX premium benchmark refresh** (Polaris current, Apple HIG, WCAG 2.2, best-in-class connector dashboards) to justify the premium spec. | Medium | `docs/01-research/ux-ui-benchmark.md` (dated delta section) |
| R-8 | Standing flagged open questions (GraphQL default page size, THROTTLED retry-after absence, GID permanence, etc.). | Low — remain Open questions | carried in refreshed `shopify-official-api-notes.md` delta + research handoff |

## 3. Product-definition gaps

| # | Gap | Severity | Closure artifact |
|---|---|---|---|
| P-1 | **Role model contradiction.** Foundational docs assume 2 audiences; design layer (DEC-012/013/018) hard-codes 4 roles/groups; binding product direction now mandates exactly 2 customer-facing roles (Connector User, Connector Administrator) with automatic inheritance. Migration design from 4 internal groups required (not implemented). | Blocking (touches every wave + UI) | `docs/02-product/connector-roles-and-permissions.md` (new canonical) + Proposed decision |
| P-2 | **Order-confirmation policy undefined.** Flow 5 covers import mechanics but no per-store confirmation policy (paid-only / paid-or-authorized / quotation-only), no manual-gateway sub-policy, no financial-state map to Odoo results. | Blocking Wave 2 | `docs/02-product/sales-order-lifecycle-and-confirmation-policy.md` (new) |
| P-3 | **Abandoned checkouts unclassified.** Currently only post-MVP breadth mention; binding direction requires explicit default (no quotation) + optional workspace design + MVP/optional-MVP/post-MVP classification. | Blocking (explicit DoD item) | `docs/02-product/abandoned-checkout-policy.md` (new) |
| P-4 | **COD lifecycle absent entirely** (no doc mentions COD). Three-dimension state model, 16 mandated scenarios, partial delivery/collection rules, evidence-source policy, accounting boundary. | Blocking Waves 2/4/6 | `docs/02-product/cod-lifecycle-and-reconciliation.md` (new) |
| P-5 | **Fulfillment operating modes absent.** No Mode 1 / Mode 2 concept, no mode-switching design, no external-fulfillment review flow. | Blocking Wave 4 | `docs/02-product/fulfillment-operating-modes.md` (new) |
| P-6 | **Shopify fulfillment-state mapping absent.** C-ORD-03 is conceptual only; no per-state table (raw value → label/badge/severity/actions/tests/unknown-value behavior). | Blocking Wave 4 + UI | `docs/02-product/shopify-fulfillment-status-model.md` (new) |
| P-7 | **Reconnect/catch-up/backfill under-specified per domain.** Reconnect lifecycle + generations exist; missing: per-domain watermark/overlap catch-up strategies, backfill preview, onboarding import windows. | Blocking Waves 2–5 | `docs/02-product/reconnect-catchup-backfill-policy.md` (new) |
| P-8 | **Inventory operating model needs closure** on the mission's full checklist (reservation vs available, coalescing, negative/inactive/unmapped cases, large-catalog behavior). Existing DEC-010 + blueprint cover part. | Blocking Wave 3 | `docs/02-product/inventory-operating-model.md` (new, consolidating; supersedes scattered fragments) |
| P-9 | **Product-export operating model needs closure** (ownership, overwrite prevention, changed-since-read, uncertainty after mutation). Partial in scope docs + Task 015 packet. | Blocking Wave 5 | `docs/02-product/product-export-operating-model.md` (new) |
| P-10 | **Lite/Full matrix not tied to capabilities/toggles/uninstall** at the required granularity; DEC-029 accepted the model, proposal doc predates Wave 1. | Medium | capability/module dependency matrix inside `docs/03-architecture/modular-architecture-recommendation.md` (new) + product delta in `lite-full-packaging-final-proposal.md` |
| P-11 | **MVP capability map refresh** post-Wave-1 (current status per capability). | Medium | `docs/02-product/mvp-capability-map.md` (new snapshot) |

## 4. Architecture gaps

| # | Gap | Severity | Closure artifact |
|---|---|---|---|
| A-1 | **DEC-031 Layer 2 undesigned.** Layer 1 accepted; Layer 2 (durable mutation ownership, attempt identity, uncertain-outcome reconciliation) exists only as companion-doc recommendation §8.2. Gates Waves 3/4/5. | Blocking Waves 3–5 | Complete Proposed design: `docs/03-architecture/dec-031-layer-2-mutation-safety-design.md` (new) + dated Layer-2-Proposed revision section appended to `DEC-031` record (per mission: update existing record, no duplicate DEC) |
| A-2 | **Mutation-domain reconciliation matrix absent** (per-mutation idempotency capability, reconciliation read, fail-closed rule). | Blocking Waves 3–5 | section of A-1 design doc |
| A-3 | **Modular architecture final recommendation unaccepted**; 10-module hypothesis unvalidated vs actual 3 modules; sale-module naming (holds customers, not orders) unexamined. | High | `docs/03-architecture/modular-architecture-recommendation.md` (new, builds on `final-mvp-module-and-dependency-architecture.md`) |
| A-4 | **Domain flow diagrams missing** (order, inventory, outbound/inbound fulfillment, reconnect, COD). | Medium | flow sections in the new product/architecture docs (Mermaid) |
| A-5 | **Inbound fulfillment reconciliation architecture absent** (origin classification, line-level evidence, dedup). | Blocking Wave 4 | `docs/02-product/fulfillment-operating-modes.md` §inbound + architecture appendix |
| A-6 | **Data retention & audit model consolidation** (job/log/attempt retention, redaction, uninstall) not in one place. | Medium | section in A-1 doc + roles doc |
| A-7 | **Performance architecture** beyond PB-1..23 budgets (coalescing, batching, backlog behavior at scale) not consolidated. | Medium | `docs/05-qa/performance-slo-benchmark-plan.md` (new) + architecture notes |

## 5. UX gaps

| # | Gap | Severity | Closure artifact |
|---|---|---|---|
| U-1 | **No premium UX master specification** covering the 26 mandated areas at per-screen depth (purpose/roles/data/actions/states/accessibility/etc.). Existing spec covers S1–S14 at 4-role granularity. | Blocking Wave 5 | `docs/02-product/premium-ux-master-specification.md` (new canonical; supersedes role/screen conflicts in `ui-ux-final-design-spec.md` at proposal level) |
| U-2 | **Prototype coverage ~6–7 of ~25 screens**; missing orders, COD reconciliation, inventory, fulfillment, external-fulfillment review, tracking timeline, reconnect/backfill, settings/permissions, offline/unknown-schema states. | Blocking product-owner review | extend `docs/09-ui-prototype/**` in place (canonical; no migration) |
| U-3 | **Prototype persona/terminology** predates two-role model. | Medium | new/updated surfaces use Connector User/Administrator language |

## 6. Implementation-planning gaps

| # | Gap | Severity | Closure artifact |
|---|---|---|---|
| I-1 | Wave 2 Definition of Ready absent (Task 012 packet exists but no consolidated wave DoR; packet predates two-role/COD/confirmation-policy directions). | Blocking Wave 2 gate | `docs/07-implementation-plan/wave-2-definition-of-ready.md` (new) + revision addendum to Task 012 packet |
| I-2 | Wave 3 DoR absent; Task 013/013B packets predate Layer 2 design. | Blocking Wave 3 gate | `wave-3-definition-of-ready.md` + packet addenda |
| I-3 | Wave 4 DoR absent; Task 014 packet predates fulfillment modes/state model/inbound design. | Blocking Wave 4 gate | `wave-4-definition-of-ready.md` + packet addendum |
| I-4 | Wave 5 DoR absent; U2/U3 locked prompts deliberately deferred; PERF-1 packet needs wave anchoring; Task 015/015B predate export operating model. | Blocking Wave 5 gate | `wave-5-definition-of-ready.md` + packet addenda + U2/U3 prompt completion in `ui-implementation-phases-packet.md` |
| I-5 | **No Wave 6 packet exists** (E2E/UAT/release is program-level prose only). | Blocking Wave 6 | `docs/07-implementation-plan/wave-6-e2e-uat-release-packet.md` (new) + `wave-6-definition-of-ready.md` |
| I-6 | Cross-wave dependency, migration/rollback, and decision-gate maps absent. | High | `docs/07-implementation-plan/waves-2-6-dependency-and-gate-map.md` (new) |
| I-7 | Four-group→two-role migration plan absent (design-only this mission). | Blocking Wave 5 (UI) and role GA | section of `connector-roles-and-permissions.md` + packet addendum |

## 7. QA / release gaps

| # | Gap | Severity | Closure artifact |
|---|---|---|---|
| Q-1 | Cross-domain test matrix predates Waves 2–6 designs (no COD, modes, reconnect, Layer 2, unknown-state rows). | Blocking Wave 6 | `docs/05-qa/waves-2-6-cross-domain-test-matrix.md` (new) |
| Q-2 | COD UAT matrix absent (16 scenarios). | Blocking | `docs/05-qa/cod-uat-matrix.md` (new) |
| Q-3 | Fulfillment-mode UAT matrix absent. | Blocking | `docs/05-qa/fulfillment-mode-uat-matrix.md` (new) |
| Q-4 | Reconnect/backfill UAT matrix absent. | Blocking | `docs/05-qa/reconnect-backfill-uat-matrix.md` (new) |
| Q-5 | Performance SLOs (PB-1..23) unaccepted, partly uncalibrated; no benchmark execution plan per environment/dataset. | High | `docs/05-qa/performance-slo-benchmark-plan.md` (new) |
| Q-6 | Security/PII matrix not consolidated for Waves 2–6 surfaces (order PII, COD amounts, fulfillment addresses). | High | `docs/05-qa/security-pii-matrix-waves-2-6.md` (new) |
| Q-7 | `docs/08-release-readiness/**` framing stale (pre-implementation, 2026-07-10; 0/15 UAT executable) — needs post-Wave-1 re-baseline + release-readiness gap list. | High | `docs/08-release-readiness/release-readiness-gap-list.md` (new) + README delta note |
| Q-8 | Implementation-readiness checklist (per-wave gate checklist) absent. | High | `docs/07-implementation-plan/implementation-readiness-checklist.md` (new) |

## 8. Documentation-consistency defects to reconcile (no history rewriting)

| # | Defect | Fix |
|---|---|---|
| D-1 | DEC-028 / DEC-029 file headers still "Proposed… NOT accepted" although DEC-033 (Accepted) records them Accepted. | Dated status-sync note in each header pointing to DEC-033 (not a new acceptance). |
| D-2 | DEC-025 title "(Proposed)" / DEC-026 "(Proposal)" vs Accepted status blocks. | Dated title-clarification note (leave titles; add note). |
| D-3 | `task-012-order-import-decision-closure.md` stale "SRR-03 CLOSED"/"CORE-R1 merged" strings — already flagged in-file as historical; SRR-03 is in fact now CLOSED (Wave 1), making the flag itself stale. | Dated note updating the reconciliation notice to the post-Wave-1 truth. |
| D-4 | `task-core-r2-disconnect-quiescence-packet.md` (+ slice-2B docs) "CODE GATE NOT OPEN" wording predates the Wave 1 merge of that work. | Dated "implemented in Wave 1 (PR #172)" note. |
| D-5 | `07-implementation-plan/README.md`, `08-release-readiness/README.md` and readiness docs describe a pre-implementation project. | Dated re-baseline notes (not rewrites). |
| D-6 | `-proposed.md` packet predecessors carry live-looking headers identical to canonical `-implementation-packet.md`. | Dated "superseded by …-implementation-packet.md" banner on each predecessor. |
| D-7 | Four-role terminology across `ui-ux-final-design-spec.md`, `screen-inventory-and-navigation-map.md`, `ux-operator-flow.md` §10 vs the new two-role direction. | Proposal-layer supersession via the new roles doc + dated pointers; accepted docs not rewritten. |

## 9. Consolidated blocking-decision list (preview)

Full pack: `docs/04-decisions/fable-proposed-decision-pack.md` (produced by this
mission; every item remains **Proposed**). Headline items: two-role model +
group migration; order-confirmation + manual-gateway policy; abandoned-checkout
classification; COD three-dimension lifecycle + evidence-source policy;
fulfillment Modes 1/2 + switching rules; per-domain reconnect/backfill policy;
inventory operating model closure; product-export operating model; DEC-031
Layer 2 design; modular architecture + Lite/Full matrix; performance SLO set;
premium UX master spec adoption.

## 10. Method note

[Fact] This inventory was produced by six parallel read-only preflight agents
covering `docs/00`–`docs/09` and `addons/**` (2026-07-16), cross-checked
against `mvp-program-state.md`, `mvp-completion-program.md`, and the live
GitHub state verified at mission start. [Recommendation] Close gaps in the
order: research captures → product definitions → architecture/Layer 2 → UX →
wave packets → QA matrices → decision pack → handoff, since each layer cites
the previous one.
