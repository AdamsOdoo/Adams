# Master Blueprint — Part E: Implementation-Planning Bridge

## Status

- **Accepted by ChatGPT via [`DEC-017`](../04-decisions/DEC-017-master-blueprint-implementation-planning-bridge.md).**
  Acceptance date: **2026-07-04**.
- **Accepted as a documentation-only implementation-planning bridge.** This
  acceptance is **not implementation-authorizing**: no code, Odoo module,
  model, view, controller, security file, manifest, test, migration, or CI
  file was created or modified to produce this document, and none is
  authorized by its acceptance.
- **Part E planning only.** This was the first Part E planning-bridge
  session, opened after PR #79 merged into `Shopify-connector` (merge commit
  `77ee511036a98db36262bdbc9b4ae4371a2d85f8`), proposed via PR #80, and
  accepted via DEC-017.
- **Does not authorize code.** Nothing in this document creates or permits an
  Odoo module, model, view, controller, security file, manifest, test, CI
  workflow, or dependency change.
- **Does not open the implementation gate.** Opening the gate remains a
  separate, explicit ChatGPT act per `master-blueprint.md`'s "Criteria for
  when implementation may later be opened" and
  [`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md) §10
  — DEC-017 does not perform that act and this document is not written as if
  it does.
- **No implementation task exists.** No implementation task has been written
  to the CLAUDE.md §9 / `../06-prompts/implementation-task-template.md`
  template; none is authorized by this document or by its acceptance.
- **Implementation remains blocked.** Acceptance of this planning bridge is
  necessary but not sufficient to open the gate — see §3 below, unchanged by
  this acceptance except that "Parts A–D accepted" now also reads Part E's
  planning content as accepted.
- **Built on accepted DEC-003 through DEC-017 and Master Blueprint Parts A–D.**
  This document re-decides nothing DEC-003–016 already fixed; it does not
  reopen Part A, B, C, or D.
- **Created after the PR #78 Master Blueprint Integrity & Competitor Advantage
  Audit** (verdict: **READY FOR PART E WITH CONDITIONS**) and the PR #79
  Part D/`master-blueprint.md` residue-alignment cleanup that satisfied those
  conditions. This document executed the audit's own §10 "Required Part E
  focus areas" as its work plan — it does not re-litigate the audit's
  findings.
- **MBQ-64 and MBQ-65 are accepted at fact-verification level only** (per
  DEC-017) — their respective design/selection mechanism (MBQ-64) and
  payload/subscription/scope residual (MBQ-65) remain open; see §4/§5 below,
  unchanged in substance by this acceptance.
- **No ChatGPT-batch MBQ decision plan item is decided by this acceptance.**
  DEC-017 accepts the plan's routing (§4), not the decisions the plan
  recommends ChatGPT make.
- **DEC-018 Acceptance Patch note (2026-07-04).** The first controlled batch
  of this document's own §4 "ChatGPT batch" was proposed and then
  **accepted by ChatGPT** as
  [`DEC-018`](../04-decisions/DEC-018-mbq-decision-batch-1.md) — **Batch 1
  accepted except MBQ-62.** Ten rows are now decided: **MBQ-06, MBQ-08,
  MBQ-17 (posture only), MBQ-33, MBQ-34, MBQ-41, MBQ-45 (mapping/surface
  split), MBQ-52 (policy only), MBQ-54 (posture only), MBQ-60** — see
  `master-blueprint-open-questions.md` for each row's applied wording and
  remaining implementation-planning residual. **MBQ-62 is explicitly split
  to its own dedicated follow-up DEC**, not decided here. **§4's decision
  plan table below is unchanged** — this note does not edit that table;
  **the implementation gate remains closed, implementation remains
  blocked, and no implementation task has been created** by this
  acceptance.

## 1. Purpose of Part E

Part E translates the accepted architecture (DEC-003 through DEC-016; Master
Blueprint Parts A–D) into a **controlled implementation-readiness plan** — it
does not itself implement anything. Concretely, Part E's job is to produce:

- **MBQ decision plan** (§4) — a structured routing of every implementation-
  blocking open question to its decision owner, sequenced against the
  DEC-008 module dependency DAG, so the first implementation task is not
  blocked on an undecided question that could have been resolved cheaply and
  early.
- **Official-doc gap closure plan** (§5, §6) — closing the currency and
  product-webhook-topic gaps the PR #78 audit found untracked, using only
  official Shopify/Odoo documentation, and logging what remains inconclusive
  as open, not asserted.
- **Module-by-module implementation order** (§7) — a proposed sequence
  following the accepted DEC-008 dependency DAG (`core` → `product` →
  `sale`/`inventory` → `fulfillment`), not a redesign of module boundaries.
- **Implementation task template usage** (§11) — confirming every future
  implementation task will use
  [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)
  as-is, with no redesign needed.
- **Test strategy** (§9) — the test types and classic-defect regression
  coverage every future implementation task must include, at a planning
  level (no test file is written here).
- **Rollback strategy** (§10) — the safety/reversibility posture every future
  implementation task must satisfy, at a planning level.
- **Acceptance-criteria pattern** — already defined by the template (§11);
  this document does not redesign it.
- **No-code-to-code gate checklist** (§3) — an explicit, current statement of
  which of `master-blueprint.md`'s five gate-opening criteria are satisfied
  and which are not, so the gate's state is never ambiguous.

Part E does **not**: resolve every open MBQ (only what evidence permits, and
only as a **proposal** for ChatGPT — see §4/§5); open the implementation gate;
write any implementation task; create any code task; or change any accepted
DEC/AR/Part A–D status.

## 2. Current accepted foundation

Summarized for orientation only — none of the following is re-decided here.
Full detail lives in the cited source documents; this section does not
restate their content beyond a pointer.

- **DEC-003 through DEC-016** are all **Accepted by ChatGPT** (dates
  2026-07-01 through 2026-07-04; full chronology in
  [`../04-decisions/README.md`](../04-decisions/README.md)). DEC-003 fixes MVP
  scope; DEC-004–006 fix API/distribution/auth, sync orchestration, and
  binding/dedup strategy; DEC-007 closes five DEC-003 scope-hole
  clarifications; DEC-008–011 fix module boundaries, error/retry/idempotency,
  inventory, and fulfillment architecture; DEC-012 fixes the ten-flow
  operator-UX model; DEC-013–016 accept Master Blueprint Parts A (core
  substrate), B (product/customer/sale), C (inventory/fulfillment), and D
  (UI/UX screen design, at screen-design blueprint level only).
- **AR-002 through AR-013** are all **Accepted**
  ([`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)).
- **Master Blueprint Part A — Core/common substrate** — accepted via DEC-013:
  `shopify_connector_core` boundary; store/credential/API-health/Location-
  reference/settings concepts; binding abstraction; job/log/error/retry
  abstraction (6 sources, 10 states, 16 error classes); setup wizard,
  dashboard, sync center, error center blueprints; feature-flag mechanism;
  four-role access blueprint; cross-module extension rules.
- **Master Blueprint Part B — Product, Customer, Sale/Order domain
  blueprints** — accepted via DEC-014: product import/export/update
  (variant-mutation direction, draft/publish mechanism, media/price
  handling); customer import/matching (email-only match key); order import
  + total-check guard; automated-import create/bind policy accepted at
  blueprint-policy level (MBQ-59).
- **Master Blueprint Part C — Inventory and Fulfillment domain blueprints**
  — accepted via DEC-015: inventory binding/quantity-source direction
  (two candidate sources verified, non-equivalent — Fable finding C1);
  first-push guard granularity and apply-mode **recommendations** (not
  decided); FulfillmentOrder-based fulfillment; tracking-field resolution;
  location-confirmation mechanism accepted at blueprint level.
- **Master Blueprint Part D — UI/UX Screen Design Blueprint** — accepted via
  DEC-016, **at screen-design blueprint level only** (not pixel-level visual
  design): screen inventory, navigation/IA, Odoo-native interaction
  patterns, blueprint-level screen specs, empty/loading/success/error/
  manual-review states, UX-copy style guide, premium acceptance checklist.
  MBQ-53 partially resolved at that level only.
- **RA-001 through RA-023** are binding rejected approaches
  ([`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md))
  — checked and none reintroduced by Parts A–D (PR #78 audit §7); this
  document proposes no new architecture and therefore introduces no new
  rejected-approach risk.
- **PR #78 audit** ([`../05-qa/master-blueprint-integrity-competitor-advantage-audit.md`](../05-qa/master-blueprint-integrity-competitor-advantage-audit.md))
  — verdict **READY FOR PART E WITH CONDITIONS**: no contradiction across
  DEC-003–016; no accidental implementation authorization; no silent MBQ
  resolution; no rejected-approach drift; one blocking documentation-residue
  defect (Part D status header) and two minor `master-blueprint.md`
  staleness items, both fixed by **PR #79** before this session began.

## 3. Implementation gate remains closed

Restating the gate criteria from `master-blueprint.md`'s "Criteria for when
implementation may later be opened," with current status:

| # | Criterion | Satisfied? | Detail |
| --- | --- | --- | --- |
| 1 | Parts A–D accepted (Part D required for any operator-facing screen) | **Yes** | Parts A/B/C/D all accepted (DEC-013/014/015/016); Part D at screen-design blueprint level, sufficient for its own scope |
| 2 | Blocking MBQs resolved or consciously accepted as risk by ChatGPT in writing | **No** | ~45 "Blocks implementation: Yes" rows remain open per the PR #78 audit §4/§8; §4 below routes each to a decision owner and timing but resolves none itself |
| 3 | ChatGPT explicitly opens the implementation gate | **No** | A separate, explicit act per `../05-qa/quality-feedback-loop.md` §10 — not performed by this document or anything it reviews |
| 4 | Every implementation task written to the CLAUDE.md §9 / implementation-task-template.md template | **No** | No implementation task exists yet; §11 below confirms the template needs no redesign, only future use |
| 5 | No quality-gate escalation open (no defect-pattern category at its 3rd-occurrence pause without a prevention rule) | **Yes** | Confirmed clean by the PR #78 audit §8; `../05-qa/technical-debt-register.md` and `../05-qa/quality-feedback-loop.md` show no such escalation |

**Net: 2 of 5 criteria satisfied.** Criteria 2–4 are exactly what Part E exists
to make tractable (§4, §7, §11) — this document advances all three toward
readiness without itself satisfying any of them, since criteria 2 and 3 are
explicit ChatGPT acts and criterion 4 requires an actual implementation task
to exist. **DEC-017's acceptance of this document does not change this
table** — accepting the planning bridge is not the same act as satisfying
criteria 2–4; the count remains 2 of 5 after acceptance.

## 4. MBQ decision plan

Source of truth for every "Current status" cell is
[`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
as it stands after this session's own MBQ-64/MBQ-65 additions (§5). **No row
below is closed, resolved, or silently changed by this table** — "Proposed
Part E action" is a **recommendation for ChatGPT**, not a decision. Decision
type: **CG** = ChatGPT decision (a posture/policy call, typically cheap once
made); **ODV** = official-doc verification (a fact-finding task, may already
be done in part); **IP** = implementation-planning default/constant (decided
inside the first task that needs it, no ChatGPT gate required); **NAM** =
naming convention (Odoo model/field/view/group names — commit once, early,
since every later task references them); **RISK** = documented risk that can
remain open without blocking near-term work.

| MBQ | Current status | Blocks | Owner | Decision type | Recommended timing | Proposed Part E action |
| --- | --- | --- | --- | --- | --- | --- |
| MBQ-01 | Open | Everything (model names) | Implementation planning | NAM | Once, early — before any task | Bundle in the single naming pass with MBQ-02/03/44/55 |
| MBQ-02 | Open | Everything (field names/types) | Implementation planning | NAM | Once, early | Same naming-pass bundle as MBQ-01 |
| MBQ-03 | Open | Any operator-facing screen | Implementation planning | NAM | Before operator-screen implementation | Same naming-pass bundle; sibling of MBQ-53 |
| MBQ-04 | Open | Any credential-touching code | ChatGPT + ODV | CG + ODV | Before credential/setup-wizard task | Schedule as a ChatGPT + Odoo-capability-check pair with MBQ-08 |
| MBQ-05 | Open (within DEC-004's fixed model) | Setup wizard | Implementation planning | IP | Setup-wizard task | Decide inside that task; no ChatGPT gate |
| MBQ-06 | Open | Setup wizard | ChatGPT (or Implementation planning) | CG | Before setup-wizard task | Bundle in the cheap "ChatGPT recommendation" batch with MBQ-08/33/34/41/45/60 |
| MBQ-08 | Open | Disconnect flow | ChatGPT | CG | Before disconnect-flow task | Same ChatGPT batch as MBQ-06 |
| MBQ-09 | Open (conservative posture applies meanwhile) | Any compliance-relevant code | ODV | ODV | Before compliance-relevant code only | No near-term action; conservative posture already stands |
| MBQ-14 | Open | Inventory/refund write code | ODV | ODV | Before inventory/fulfillment task | Schedule official-doc check ahead of that task, not urgent for the core skeleton |
| MBQ-16 | Open | Retry/backoff code | Implementation planning | IP | First implementation task | Decide inside the recommended first slice (§8) |
| MBQ-17 | Open | Reconciliation job | ChatGPT (posture) + IP (constants) | CG + IP | Posture before first task; constants inside it | Bundle posture with the MBQ-06 ChatGPT batch |
| MBQ-18 | Open (throughput validation blocks release readiness, not code start) | Queue constants | Implementation planning | IP | First implementation task; throughput validation before release | Decide constants inside first task; validate throughput before release, not before code start |
| MBQ-19 | Open | Job/log model (foundational) | Implementation planning | IP | First implementation task (the recommended first slice itself) | Decide as part of §8's recommended first slice |
| MBQ-20 | Open | Idempotency-key code | Implementation planning | IP | First implementation task | Same bucket as MBQ-19 |
| MBQ-21 | Open | Ambiguous-operation guard code | Implementation planning | IP | First implementation task | Same bucket as MBQ-19 |
| MBQ-22 | Open (structure already fixed) | Nothing at code start | Later UI-design pass | RISK | Until the copy pass | Remains a documented risk; no Part E action |
| MBQ-23 | Partially resolved (DEC-014 — direction accepted) | Product export | ODV (done) + Implementation planning | IP | Product-export task | Decide exact mutation choice inside that task |
| MBQ-25 | Partially resolved (DEC-014 — mechanism accepted) | Product export | ODV (done) + Implementation planning | IP | Product-export task | Decide exact channel-selection UX inside that task |
| MBQ-27 | Open, inconclusive (Odoo tax mechanism unresolved) | Order import | ODV + Implementation planning | ODV | Before order-import task | Schedule a targeted Odoo accounting-doc recheck ahead of that task; still inconclusive after this session |
| MBQ-32 | Partially resolved (DEC-015 — sources verified, non-equivalent per Fable C1; selection open) | Inventory quantity write-back | ODV (done) + ChatGPT/Implementation planning | CG/IP | Before inventory quantity task | Bundle as a design/selection decision — facts are settled, this is a choice, not research |
| MBQ-33 | Open (DEC-015 carries a recommendation, not a decision) | First-push guard | ChatGPT | CG | Before inventory first-push task | Same ChatGPT batch as MBQ-06 |
| MBQ-34 | Open (DEC-015 recommendation, not decided) | Post-first-push writes | ChatGPT | CG | Before ongoing-apply-mode writes | Same ChatGPT batch as MBQ-06 |
| MBQ-35 | Open, unchanged | Only an `on_hand` UI, if ever built | ChatGPT | RISK | Only if `on_hand` UI is proposed | Remains a documented risk |
| MBQ-36 | Partially resolved (DEC-015 — direction accepted) | Inventory write-back | Implementation planning | IP | Inventory write-back task | Decide exact per-trigger/batching/error handling inside that task |
| MBQ-38 | Partially resolved (DEC-015 — concept accepted) | Inventory first-push | Implementation planning | NAM/IP | Inventory first-push task | Bundle schema/field names with the naming pass |
| MBQ-40 | Partially resolved (DEC-015 — fields verified; wizard-UX residual open) | Backorder handling | ODV + Implementation planning | IP | Fulfillment task | Decide residual inside that task |
| MBQ-41 | Open (DEC-015 recommendation, not decided) | Notification UI beyond per-store default | ChatGPT | CG | Before notification-UI-beyond-default work | Same ChatGPT batch as MBQ-06 |
| MBQ-42 | Partially resolved (DEC-015 — mechanism accepted at blueprint level) | Fulfillment location confirmation | Implementation planning | IP | Fulfillment task | Decide sub-reason-tagging detail inside that task |
| MBQ-43 | Partially resolved (DEC-015 — precedence rule accepted) | Location-reference cache | Implementation planning | IP | Fulfillment/inventory task | Decide refresh cadence/mechanism inside that task |
| MBQ-44 | Open | Everything (deny-by-default access) | Implementation planning | NAM | Before any code | Bundle in naming pass; needs MBQ-45 resolved first |
| MBQ-45 | Partially resolved (DEC-013 — hierarchy accepted; mapping open) | Group design before CSVs | Implementation planning (+ ChatGPT for surface split) | CG + NAM | Before MBQ-44's CSVs | Surface-split question joins the ChatGPT batch; group mapping joins the naming pass |
| MBQ-51 | Open | Transport client | Implementation planning | IP | Transport-client task (core, early) | Decide inside that task |
| MBQ-52 | Open | Transport client | ChatGPT (policy) + Implementation planning | CG | Transport-client task, early | Same ChatGPT batch as MBQ-06 |
| MBQ-53 | Partially resolved (DEC-016 — screen-design level only) | Any operator-facing screen | ChatGPT + later sprint | Composite | Full closure needs MBQ-03/22/44/45/06 all resolved | Track as the composite closure gate; resolved by resolving its siblings, not directly |
| MBQ-54 | Open | Uninstall/disable lifecycle only | ChatGPT + Implementation planning | CG | Before any uninstall-support code, or accept as guarded-out-of-scope | Recommend ChatGPT either decide the lifecycle now or explicitly accept "unsupported/guarded in Phase 1" as a documented risk |
| MBQ-55 | Open | Sprint B binding models | Implementation planning | NAM | Once, early | Same naming-pass bundle as MBQ-01/02 |
| MBQ-56 | Open | Order import | Implementation planning | IP | Order-import task | Decide inside that task; now informed by MBQ-64's currency facts (§5) |
| MBQ-57 | Open, current rule stands | Nothing now | ChatGPT (future, only if revisited) | RISK | None now | Remains a documented risk |
| MBQ-58 | Open, defensive design already stands | Nothing now | ODV | RISK | None now | Remains a documented risk |
| MBQ-60 | Open | Fulfillment tracking write-back | ChatGPT + Implementation planning | CG | Before fulfillment task | Same ChatGPT batch as MBQ-06 |
| MBQ-61 | Open | Not MVP core; yes if hold-aware UX later required | ChatGPT + Implementation planning | RISK | None now for MVP | Remains a documented risk for MVP |
| MBQ-62 | Open (Fable finding C2) | Odoo-event-triggered inventory push/fulfillment creation specifically | ChatGPT + Implementation planning | CG | Before those specific event-triggered paths | Same ChatGPT batch as MBQ-06 |
| MBQ-63 | Open (Fable minor finding 4) | Webhook-driven inventory import specifically | Implementation planning + ODV | ODV | Only if webhook-driven inventory import is implemented | No near-term action unless that path is chosen |

**Reading the plan:** the single largest lever is the **"ChatGPT batch"** —
MBQ-06/08/17(posture)/33/34/41/45(surface-split)/52/54/60/62 are all
ChatGPT-owned recommendations that already have a proposed direction on the
table (from DEC-013/DEC-015's own "recommendation, not decided" language);
deciding them costs ChatGPT one review pass, not new research, and it
unblocks the very first implementation tasks in `core`, `inventory`, and
`fulfillment`. The second lever is the **naming pass** (MBQ-01/02/03/44/45/55)
— committed once, early, since every later task references it. Everything
else (IP-tagged rows) is designed to be decided **inside** the first
implementation task that needs it, once the gate opens — it does not block
gate-opening itself.

## 5. New MBQ candidates from PR #78 audit

The PR #78 audit (§6 cross-check addendum) identified three untracked gaps.
After this session's official-doc research (§6 below), two were confirmed
real and are added to
[`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
as **MBQ-64** and **MBQ-65**, continuing the register's numbering after
MBQ-63. **Per DEC-017 (2026-07-04), the underlying platform facts for both
rows are now accepted at fact-verification level** — each row's own
design/selection mechanism (MBQ-64) or payload/subscription/scope residual
(MBQ-65) remains **open, not resolved, not decided**:

1. **Shopify multi-currency / presentment-currency order model → MBQ-64.**
   Confirmed real: Shopify's order-money fields are `MoneyBag`-typed
   (`shopMoney` + `presentmentMoney`, both verified against `shopify.dev`,
   2026-07-04), while Odoo's `sale.order` carries exactly one computed
   `currency_id` (verified against official 19.0 source, 2026-07-04). **This
   blocks implementation**: the total-check guard (MBQ-56,
   `master-blueprint-product-customer-sale.md` §C.8, "mandatory and
   permanent") and the price source-of-truth mechanism (DEC-007 §3) both
   implicitly assumed single-currency comparison, and neither the Shopify
   nor Odoo research notes previously documented the dual/single-currency
   shape mismatch. MBQ-64 does not duplicate MBQ-56 — MBQ-56 already asked
   for "the exact Shopify total field(s) used" and "currency-rounding
   tolerance"; MBQ-64 supplies the platform-fact context (both fields exist
   and are non-null; Odoo has only one) that MBQ-56's eventual answer must
   account for.
2. **Odoo multi-currency / pricelist ORM behavior → folded into MBQ-64.**
   Confirmed real and paired with item 1 above, per the audit's own framing
   ("both underpin the total-check guard and the price source-of-truth
   mechanism... add one [row] and resolve before the order-import/
   product-export tasks land"). `sale.order.currency_id` computes from
   `pricelist_id.currency_id` or, absent a pricelist, `company_id.currency_id`
   — confirmed against official 19.0 source. `res.currency.rounding` /
   `round()` / `compare_amounts()` are confirmed as Odoo's own
   currency-aware tolerance-comparison primitives — a **candidate**
   mechanism for MBQ-56's tolerance question, not adopted as a decision
   here.
3. **Shopify product-domain webhook topic strings → MBQ-65.** Confirmed
   real: `master-blueprint-product-customer-sale.md` §A.2 already flagged
   these as "not verified/cited this sprint," and no MBQ row tracked the
   gap (unlike its inventory analog, MBQ-37/MBQ-63). `PRODUCTS_CREATE`,
   `PRODUCTS_UPDATE`, and `PRODUCTS_DELETE` are now confirmed against the
   official `WebhookSubscriptionTopic` enum (2026-07-04) — **accepted at
   fact-verification level only by DEC-017**, mirroring MBQ-37's treatment.
   The broader payload-shape/subscription-scope/Phase-1-implementation-scope
   residual remains open, mirroring MBQ-63.

**Why each blocks or does not block implementation:**

- **MBQ-64 blocks** webhook-driven and reconciliation-driven order import
  (the total-check guard cannot be safely written without knowing which
  money field it compares) and product/price export (the price
  source-of-truth mechanism cannot safely write a price without knowing
  which currency it is writing in). It does **not** block `core`,
  `product`'s non-price fields, `inventory`, or `fulfillment` — none of
  those touch order-money or price-currency comparison.
- **MBQ-65 does not block** manual, scheduled, or reconciliation-driven
  product import/export (DEC-003/DEC-007's layered-sync posture already
  covers those triggers without depending on a webhook topic string) — it
  blocks **only** webhook-driven product import specifically, exactly as
  MBQ-63 blocks only webhook-driven inventory import specifically.

Both rows were added to the register with the exact wording above, cited
against this session's own research-notes additions (§6); no existing MBQ
row was modified, resolved, or re-routed to add them (register's own
Maintenance rule, and this document's own no-silent-resolution rule, both
honored).

## 6. Official-doc research notes for this sprint

Full facts, quotes, and URLs are in
[`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md)
("Part E pre-implementation research patch") and
[`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md)
("Part E pre-implementation research patch"), both accessed **2026-07-04**.
Summary only, no new facts beyond what those two files now cite:

**Shopify (official `shopify.dev` pages only):**

- `MoneyBag` = exactly two non-null `MoneyV2` fields, `shopMoney` ("Amount in
  shop currency") and `presentmentMoney` ("Amount in presentment currency").
- `Order.currencyCode` = "The shop currency when the order was placed";
  `Order.presentmentCurrencyCode` = "The currency used by the customer when
  placing the order." Every order money/total field (`totalPriceSet`,
  `currentTotalPriceSet`, `totalOutstandingSet`, `totalDiscountsSet`,
  `totalTaxSet`, and the rest — full list in the research notes) is
  `MoneyBag`-typed, i.e. carries both currencies simultaneously.
- **Open, not asserted:** whether `presentmentMoney` can diverge from
  `shopMoney` for a store that has not explicitly enabled Shopify Markets/
  multi-currency selling — not stated on the fetched pages; MBQ-64 stays
  open on this point rather than assuming either way.
- `WebhookSubscriptionTopic` confirms `PRODUCTS_CREATE`, `PRODUCTS_UPDATE`,
  `PRODUCTS_DELETE` (plus the non-required
  `PRODUCT_LISTINGS_*`/`PRODUCT_PUBLICATIONS_*`/`SCHEDULED_PRODUCT_LISTINGS_*`
  topics, logged for completeness, not required for Phase 1 scope).
- **Open, not asserted:** exact payload shape and required subscription
  scopes beyond `read_products` for the product topics — not verified this
  session; routed to MBQ-65's residual.

**Odoo (official 19.0 documentation + official `odoo/odoo` 19.0 source):**

- `sale.order.currency_id` — computed, stored, precomputed `Many2one` to
  `res.currency`; derives from `pricelist_id.currency_id` if a pricelist is
  set, else `company_id.currency_id`. Exactly one document currency per
  order, never a dual shop/presentment pair.
- `sale.order.company_id` — required `Many2one` to `res.company`, defaulting
  to `self.env.company`.
- `res.currency.rounding` — `Float(digits=(12, 6), default=0.01)`, "Amounts
  in this currency are rounded off to the nearest multiple of the rounding
  factor." `res.currency.round(amount)` and `res.currency.compare_amounts()`
  are Odoo's own currency-aware rounding/tolerance-comparison primitives —
  a **candidate** mechanism for MBQ-56, not adopted as a decision here.

**If browsing had failed or facts had been inconclusive:** none of the four
fetches above failed or returned an inconclusive result — every cited fact
was confirmed on the first fetch of its official page/source file. Where a
narrower question remains genuinely unanswered by the fetched pages (the
Markets-independence question above; the payload-shape/scope question for
product webhooks), this document states that explicitly and keeps the
relevant MBQ row open rather than inferring an answer.

## 7. Proposed implementation sequence

A **sequence only**, following the already-accepted DEC-008 module dependency
DAG (`core` has no upstream dependency; `product` depends only on `core`;
`sale`/`inventory` each depend on `product` but not on each other;
`fulfillment` depends on `sale`, never on `inventory`). **No implementation
task is created by this table.**

| Phase | Scope | Preconditions | MBQs needed | Why this order | Risks |
| --- | --- | --- | --- | --- | --- |
| 1. Core substrate / job-log-error foundation | `shopify_connector_core` job/log/error/retry abstraction (6 sources, 10 states, 16 classes, idempotency key, serialization guard) | Gate open (§3); naming pass started | MBQ-16/17(constants)/18/19/20/21 | No ChatGPT-only blocker; every later module depends on this substrate; recommended first slice (§8) | Under-scoping the schema here forces a painful later migration across every domain module |
| 2. Store credentials and connection test | Store/connection model, credential storage, API-health/version pinning | Phase 1 substrate exists | MBQ-04 (ChatGPT + ODV), MBQ-51/52 | Every domain module needs a working, authenticated transport before it can sync anything | Wrong credential-storage choice is a security defect, not a refactor — get MBQ-04 right before writing to it |
| 3. Setup wizard and readiness checks | Wizard flow, readiness-check list, feature-flag mechanism | Phases 1–2 | MBQ-05, MBQ-06 (ChatGPT), MBQ-17(posture) | DEC-012's first operator flow; nothing else is usable without a completed setup | A too-narrow readiness check ships a "connected" store that silently fails on first real sync |
| 4. Product binding/import/export/update | `shopify_connector_product`: product-template/variant binding, import, controlled export/update | Phases 1–3; `core` binding contract | MBQ-23/25 (direction accepted, detail here), MBQ-55 (naming), MBQ-64 (price-currency mechanism) | `product` is the DAG's first domain module; `sale`/`inventory` both resolve bindings through it | `productSet` delete-on-omit (already a known footgun, PR #78 audit §6) makes an under-tested export destructive |
| 5. Customer binding/import/matching | `shopify_connector_sale`'s customer sub-scope: binding, email-only matching, default-customer fallback | Phase 4 (product bindings exist for order lines) | MBQ-55 (naming) | Folded into `sale` per DEC-008; needed before order import can resolve a customer | Wrong match-key priority creates duplicate partners (RA-006 guardrail) |
| 6. Order import and total-check guard | `shopify_connector_sale`'s order sub-scope: import, financial-evidence capture, mandatory total-check guard | Phases 4–5 | MBQ-27 (ODV), MBQ-56, MBQ-64 (currency mechanism) | Order import needs both product and customer bindings resolved first | An unresolved currency mechanism (MBQ-64) risks a silently wrong total-check comparison — sequence this after MBQ-64 is decided, not before |
| 7. Inventory location mapping and quantity write-back | `shopify_connector_inventory`: location mapping, first-push guard, quantity write-back | Phase 4 (`product` bindings); parallel with `sale`, not dependent on it | MBQ-32 (selection), MBQ-33/34/41 (ChatGPT batch), MBQ-36/38 | DEC-008: `inventory` depends only on `product`, so it can run in parallel with `sale` | Double-decrementing multi-location SKUs (RA-019 guardrail) if location identity is wrong |
| 8. Fulfillment/tracking write-back | `shopify_connector_fulfillment`: FulfillmentOrder-based mutations, tracking write-back | Phase 6 (`sale`); never depends on `inventory` | MBQ-40/42/43, MBQ-60 (ChatGPT) | DEC-008: `fulfillment` depends on `sale` only — must follow order import, not inventory | Using legacy Order/Fulfillment endpoints (RA-022 guardrail) or fulfilling from a mismatched location |
| 9. Permissions/security | `ir.model.access.csv`, groups, record rules for all modules above | After each module's models exist (deny-by-default — nothing works without this) | MBQ-44/45 | `ir.model.access` is deny-by-default; every module needs its own access rows as it lands, not as one big deferred task | Shipping any module without its access rows makes it unusable, not just insecure |
| 10. Observability/dashboard/error center | Dashboard, sync center, error center, manual-review queue (Part A/D screens) | After enough job/log/error data exists to populate it (phases 1, 4–8) | MBQ-03/22 (naming/copy) | The screens are meaningful only once real domain jobs are flowing through the substrate | Building this before phases 1–8 land risks designing against synthetic, not real, job/error data |

## 8. First safe implementation slice recommendation

**Recommendation only — not an authorization.** The **job/log/error
abstraction skeleton** inside `shopify_connector_core` (MBQ-19/20/21, plus the
retry/reconciliation constants of MBQ-16/17/18) is the strongest first-slice
candidate, for the same reason the PR #78 audit named it (§8 of that audit):

- **Every domain module depends on it** — `product`, `sale`, `inventory`, and
  `fulfillment` all log through the same job/log/error/retry substrate (Part
  A §D); building it first means no domain module later has to retrofit
  logging against a substrate that changed shape underneath it.
- **No ChatGPT-only or official-doc precondition blocks it** — MBQ-19/20/21
  are all "Implementation planning"-owned in the register, unlike the
  credential/setup-wizard slice (blocked on the ChatGPT-owned MBQ-04/MBQ-06)
  or the access-groups slice (blocked on MBQ-44/45). It could be the very
  first task written to
  [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)
  once the gate opens.
- **It is the smallest coherent unit that is still useful on its own** —
  a job/log/error model with no domain module writing to it yet is
  testable in isolation (`TransactionCase` against the model's own
  states/classes/idempotency-key logic) without needing a live Shopify
  connection.

**Blockers/preconditions before this slice can start:** (1) the
implementation gate itself must open (§3, criteria 2–3); (2) MBQ-19 (job/log
model shape — single model vs. job+log split) and MBQ-20/21 (idempotency-key
schema; serialization-guard mechanism) must be decided **inside** the task
itself, per §4's IP tagging — no ChatGPT gate blocks this decision, but it
must still happen before the models are created; (3) the naming pass (§4,
MBQ-01/02) should ideally cover this model's own name/fields at the same
time, since it is the first model any later naming decision will be
compared against for consistency.

## 9. Test strategy by implementation area

**Planning only — no test file is created here.** Per `CLAUDE.md` §9 and
`../01-research/avoid-list.md` A-IMP-4, every future implementation task must
specify mandatory regression coverage for the classic connector defects this
project's own research has already identified as common market failure
modes, using the Odoo 19 official testing framework
(`../01-research/odoo-official-architecture-notes.md` "Testing guidance"):

- **`TransactionCase`** — ORM/mapping logic: binding uniqueness/dedup,
  job/log/error state transitions, idempotency-key generation/lookup,
  total-check guard tolerance comparison, inventory quantity-source
  selection, currency-comparison logic (once MBQ-64/56 are decided).
- **`HttpCase` / tours (tagged `post_install`)** — webhook controllers (HMAC
  verification, dedup via `X-Shopify-Webhook-Id`), setup-wizard flow,
  dashboard/sync-center/error-center screens.
- **Webhook controller tests** — signature verification rejects an invalid
  HMAC; a duplicate webhook delivery (same `X-Shopify-Webhook-Id`) is a
  no-op, not a duplicate write.
- **Duplicate-prevention tests** — binding-based dedup prevents a second
  product/customer/order record for the same Shopify GID across a repeated
  webhook, reconciliation pass, and manual sync of the same event.
- **Inventory multi-location tests** — a two-location SKU's quantity write
  targets the correct `(inventory_item_id, location_id)` pair and does not
  double-decrement the other location (RA-019 guardrail).
- **Order total-check tests** — a correct order passes the guard; a
  Shopify-side total divergence beyond tolerance is classified
  `financial total mismatch` and blocked, never silently accepted or
  silently auto-corrected.
- **Retry/idempotency tests** — an auto-retryable class retries with
  backoff and stops at its ceiling; a non-idempotent operation retried after
  an ambiguous outcome does not double-write (the serialization guard,
  MBQ-21).
- **Permission/security tests** — each of the four roles sees exactly the
  access `ir.model.access.csv`/record rules grant it, no more (deny-by-default
  verified, not assumed).

## 10. Rollback and safety strategy

**Planning only.** Every future implementation task must state its own
rollback notes per the template (§11); this section names the mechanisms
those notes will draw on:

- **Feature flags** — the accepted per-store feature-flag mechanism (Part A
  §I) gates every domain module's behavior; disabling a flag must stop new
  writes without deleting binding/job/log/audit history (already-accepted
  "disabling must not delete history" rule, Part A §I.4).
- **Disable without deleting history** — the same posture extends to a full
  module **uninstall**, per MBQ-54 — a decision this document recommends
  ChatGPT either make explicitly or consciously accept as an open risk
  (§4), not silently leave undecided into implementation.
- **Migration scripts** — per-version `migrations/{pre,post,end}-*.py`
  scripts (official Odoo upgrade-script convention,
  `../01-research/odoo-official-architecture-notes.md` "Upgrade and
  migration considerations") for any schema change after first release.
- **Data retention** — binding, job, log, and audit records survive
  disconnect (MBQ-08, still open — a ChatGPT decision this plan recommends
  bundling into the cheap-decision batch, §4) and survive a domain-module
  disable (already-accepted rule above).
- **Retry rollback / stuck-job handling** — the accepted job-state model
  (Part A §D) includes cancellation/supersede semantics for a job that must
  be abandoned; no implementation task may invent a new state outside the
  fixed 10-state model.
- **Uninstall/disable lifecycle caveat (MBQ-54)** — restated as a named,
  visible risk (§12) rather than assumed resolved by the general feature-flag
  safety posture.

## 11. Implementation task template enforcement

Every future implementation task **must** use
[`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)
as-is — this Part E session finds it complete and does not propose any
redesign. Required fields, restated for traceability only:

1. **Allowed files** — exact files/paths the task may create or modify,
   consistent with the DEC-008 module-family boundaries (§7) and isolated
   from `adams_base`/customer code.
2. **Forbidden files** — what must not be touched; restates the
   no-code-elsewhere rule.
3. **Acceptance criteria** — observable, testable conditions (functional +
   idempotency, error handling, retry/recovery, rate-limit behavior,
   security, performance).
4. **Tests** — per §9 above, including edge cases and any previously logged
   defect (`../05-qa/defect-pattern-log.md`).
5. **Rollback notes** — per §10 above.
6. **Definition of done** — code + tests pass, lint/format clean,
   `../05-qa/pr-review-checklist.md` section C satisfied, any shortcut logged
   in `../05-qa/technical-debt-register.md`, modularity preserved, self-review
   classified, handoff updated, quality gate confirmed.

No task is written by this document — the template is confirmed ready for
first use once the gate opens (§3) and the naming pass (§4) has committed at
least the names the first task needs.

## 12. Open risks before implementation

Risks that must remain visible and not be silently assumed resolved as
implementation planning proceeds:

- **Currency handling (MBQ-64, new this session)** — dual shop/presentment
  Shopify currency vs. single Odoo document currency; unresolved until a
  design/selection decision is made (§4, §5).
- **Product webhook topics (MBQ-65, new this session)** — topic strings
  proposed resolved; payload shape/subscription-scope/implementation-scope
  residual still open.
- **Credential storage** (MBQ-04) — encryption/storage-at-rest mechanism
  undecided; a security-relevant gap, not a cosmetic one.
- **Readiness checks** (MBQ-06) — essential-vs-nice-to-have split undecided;
  affects what "connected" means to an operator.
- **Security groups** (MBQ-44/45) — roles→groups mapping and admin-vs-
  functional surface split undecided; blocks every module's access rows.
- **Quantity-source selection** (MBQ-32 residual) — `free_qty` and
  `available_quantity` are verified non-equivalent (Fable finding C1); the
  selection is a substantive design choice, not yet made.
- **First-push guard granularity** (MBQ-33) and **apply-mode** (MBQ-34) —
  both carry a DEC-015 recommendation, neither is decided.
- **Fulfillment `stock_delivery` dependency** (MBQ-60) — whether
  `shopify_connector_fulfillment` requires that Odoo module is undecided;
  affects the module's manifest `depends` list once implementation starts.
- **MBQ-54 uninstall/disable lifecycle** — undecided whether Phase 1
  supports uninstall at all, or guards/blocks it; must not be silently
  assumed either way.
- **Pixel-level UI still deferred** — Part D's acceptance is screen-design-
  level only (DEC-016); no pixel-level visual design exists yet, and the
  deferred `sh_shopify_connector` "Daily Queue Activity Tracking" chart idea
  remains unadopted, not forgotten.

## 13. Recommendation to ChatGPT (as accepted)

**Accepted by ChatGPT via DEC-017 (2026-07-04).**

This session executed the PR #78 audit's own §10 priority list items 1
(MBQ decision plan, §4), 11 (currency research, §5/§6), and 12 (product-
webhook MBQ row, §5/§6) as its scoped work. ChatGPT accepted this Part E
planning-bridge document, AR-014, and the two research-notes findings (at
fact-verification level for MBQ-64/65) via
[`DEC-017`](../04-decisions/DEC-017-master-blueprint-implementation-planning-bridge.md).
**This acceptance did not thereby decide the MBQ decision plan's own
ChatGPT-batch items, did not resolve MBQ-64's design/selection mechanism,
and did not resolve MBQ-65's payload/subscription/scope residual** — see
DEC-017's own "MBQ impact" section. Implementation itself remains blocked
pending: (a) the MBQ decision plan's ChatGPT-batch items actually being
decided, and (b) a separate, explicit ChatGPT implementation-gate-opening
act (§3, criterion 3). Neither has happened yet. The recommended next
session is the MBQ decision plan's own ChatGPT-batch decision session, not
implementation.
