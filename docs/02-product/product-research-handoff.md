# Product Research Handoff

> The **product-side** handoff for the Odoo 19 ↔ Shopify Connector. It records what
> the product-research work (starting with Sprint D) produced, what it now enables,
> and the implications/inputs it hands to later gated sprints. It complements the
> rolling engineering-research handoff at
> [`../01-research/research-handoff.md`](../01-research/research-handoff.md).
>
> **Governance:** research/synthesis phase; **no-code gate in force**
> (`CLAUDE.md` §4–§5). From Sprint G the **MVP *product scope* is accepted** (RB-13,
> DEC-003); **architecture remains gated** (RB-14 / AR-002…AR-008) and **implementation
> remains blocked**. Access date for competitor evidence: 2026-06-30; session date:
> 2026-07-01.

# Product Sprint G Handoff

> **Product Sprint G — MVP Scope Acceptance and Decision Baseline (RB-13).** Records
> ChatGPT's accepted MVP scope decisions in GitHub and aligns the product documents to
> that accepted baseline. **Documentation/decision-recording sprint only** — no new
> sources crawled, no research agents, no architecture. **No-code gate in force**
> (`CLAUDE.md` §4–§5). Session date 2026-07-01.

## Sprint G revision (PR #55 review — 2026-07-01)

ChatGPT reviewed PR #55 and returned **REVISE** — the first draft **over-deferred product
export**. Corrected on the same branch (`docs: revise mvp baseline for controlled product
export`), a **product-scope correction only** (no architecture, no code):

- **Controlled product export/update is now IN MVP** — Shopify→Odoo product import **and**
  Odoo→Shopify product export/update, with product/variant **matching**, **binding**,
  **preview/dry-run**, **duplicate prevention**, and **draft/unpublished/channel-controlled**
  export safety. This is **controlled bidirectional product onboarding**, not import-first.
- **Full autonomous bidirectional catalog management remains later** — automatic all-field
  two-way conflict resolution, complex field-ownership matrix, advanced publish/channel
  campaign management, and catalog breadth (Markets/pricelists/metafields/SEO/custom
  transforms/full-multi-store) stay Phase 2+.
- **Customer export remains later.**
- **Evidence:** product import/export/update is **market-baseline** — EM/VT/WK/SH
  demonstrated in the already-merged matrix. **TeqStars docs**, recorded 403-blocked in
  Sprint C (2026-06-30), were **re-checked by ChatGPT on 2026-07-01 and found accessible**
  (product import/export/update flows documented); a **full TeqStars rebaseline is pending
  a later research sprint** and was **not** performed here.
- **No architecture finalized; no implementation authorized.** Binding/data model stays
  **AR-005**; API/destructive-apply mechanics stay **AR-002**; destructive/full-state write
  safety stays mandatory but architecture-gated.

*(The Session summary and sections below were authored for the initial Sprint G recording;
read them with the correction above applied — "import-first" is superseded by "controlled
bidirectional product onboarding," and product export is in MVP.)*

## Session summary

ChatGPT made the **RB-13 MVP scope decisions**; this sprint recorded them as the accepted
baseline. Created **`docs/04-decisions/DEC-003-mvp-scope.md`** (the accepted MVP
**product-scope** decision record — Option A correctness-core **with controlled
bidirectional product onboarding**; the accepted direction; the Domain 9
minimal-financial-evidence decision; refunds/cancellations deferred; bulk ops not
user-facing; single-store/single-company; P1-primary/P2-secondary; and an explicit "no
architecture decided / implementation blocked" clause). Aligned the three product docs —
**`mvp-scope.md`** (status → accepted baseline; new *ChatGPT RB-13 acceptance* + *Product
onboarding and duplicate-prevention baseline* sections; every former `open` fork resolved
inline; open-questions split into resolved vs still-open), **`non-mvp-and-later-phases.md`**
(status → accepted boundary; **product export removed from non-MVP**; new *Full autonomous
bidirectional catalog management* boundary; customer-export/refunds-cancellations/
Domain-9-accounting/bulk-ops/App-Store/multi-store-company confirmed non-MVP with revisit
conditions), and **`user-stories.md`** (US-E2-05 → controlled MVP export/update; new US-E2-06
first-sync matching; customer-export/refund stories → later; Domain 9 story → MVP
minimal-evidence-only; bulk ops → internal-only; persona → P1 primary/P2 secondary). Updated both handoffs and applied the
**DP-006 evidence-consistency gate**. **No connector code, no Odoo module, no architecture
doc, no architecture ADR, no implementation plan, no module boundary, no REST/GraphQL,
queue-framework, data-model, or distribution decision** was produced.

## Files created or updated

- `docs/04-decisions/DEC-003-mvp-scope.md` (**new** — accepted MVP product-scope baseline).
- `docs/02-product/mvp-scope.md` (**updated** — accepted; RB-13 acceptance section + inline
  resolutions).
- `docs/02-product/non-mvp-and-later-phases.md` (**updated** — accepted non-MVP boundary).
- `docs/02-product/user-stories.md` (**updated** — MVP-relevance aligned to accepted scope).
- `docs/02-product/product-research-handoff.md` (**updated** — this Sprint G section).
- `docs/01-research/research-handoff.md` (**updated** — Sprint G section + checkpoints).
- QA logs — non-decision notes only (see *Evidence-consistency gate* / *Learning feedback
  loop*): `defect-pattern-log.md`, `architecture-review-log.md`,
  `rejected-approaches-log.md`, `technical-debt-register.md`.

## MVP acceptance summary

The MVP is **accepted as Option A — a correct, observable, recoverable single-store sync
loop across the core commerce objects, with controlled bidirectional product onboarding
(product import **and** controlled export/update)**, plus inventory + fulfilment/tracking
write-back — winning on depth of correctness and operator experience, **not** breadth
(specifically **not** unrestricted autonomous bidirectional catalog ownership). This is a
**product-scope** acceptance only; every *mechanism* stays gated (RB-14).

## Accepted MVP decisions

- **Option:** Option A (correctness core, with controlled bidirectional product onboarding —
  PR #55 correction).
- **Direction:** Shopify→Odoo import (products, variants/options, basic images, base
  price/compare-at, customers + matching, orders, order status/lifecycle); **Odoo→Shopify
  controlled product export/update** (product export/update, image/price update where
  feasible — matched, bound, previewed, draft/channel-safe); Odoo→Shopify write-back
  (inventory multi-location-aware/idempotent; fulfilment + tracking). **Deferred:** customer
  export; unrestricted autonomous bidirectional catalog ownership.
- **Domain 9:** minimal financial **evidence/representation only** (financial + payment
  status, gateway/method label, transaction reference(s), paid/unpaid/refunded flags as
  source info, totals/taxes/shipping/discounts/currency, basic gateway/journal mapping as
  config input if needed) — **no accounting automation** (no auto invoices/payments, no
  bank/payout reconciliation, no auto refund/payment posting). Rule: *preserve financial
  evidence and order actionability; do not automate accounting.*
- **Inventory:** write-back in MVP; multi-location-aware; **never write `committed`**;
  write only allowed Shopify quantity fields; initial stock import controlled/reviewed;
  **auto-apply not accepted as default (AR-007-dependent).**
- **Reliability/observability:** layered sync (webhooks + scheduled + manual +
  reconciliation); HMAC; webhook-ID dedup; fast ack; idempotency keys/writes; duplicate
  prevention; per-record isolation; reason-coded logs; safe manual retry; retry
  classification concept; rate-limit/cost awareness; resumable jobs; honest freshness.
- **UX:** guided setup; credential masking; test connection; readiness/self-test; basic
  command center (health + activity/failure counts); recovery-first error center (MVP
  version); quick actions that enqueue; essential mappings only; role-based access (admin
  vs functional); open docs + dated changelog + built-in self-test.
- **Store/company:** single-store, single-company; no multi-store UI/logic, no
  multi-company logic; **architecture-safe** (keys multi-store-safe; WK Company field ≠
  multi-company evidence).
- **Persona:** **P1 (operations/e-commerce user) primary; P2 (Odoo admin/consultant)
  secondary;** P3/P4 remain important buyer/deployer personas.

## Deferred scope

**Unrestricted autonomous bidirectional catalog ownership** (automatic all-field two-way
conflict resolution; complex field-ownership matrix; advanced publish/channel campaign
management); **customer export**; refund sync; cancellation reflection; returns/RMA; full
Domain 9 accounting automation; payout/bank reconciliation; multi-package fulfilment;
complex tax engine; Shopify Markets/B2B/POS/gift cards/metafields/subscriptions/
abandoned-checkout/recommendations/Buy-with-Prime; multi-store UI/logic + multi-company
logic; custom Python transforms; advanced analytics/reporting; public App-Store + demo
packaging + app billing/compliance webhooks (distribution-gated). **Bulk Operations are not
a user-facing MVP feature** (RB-14/AR-002 may assess an internal mechanism only).
*(**Controlled** product export/update — matched, bound, previewed, draft/channel-safe —
**is in MVP**, not deferred.)* Each deferral carries a
revisit condition in `non-mvp-and-later-phases.md`. **Mandatory future rule:** if refund
handling is later included, the idempotent-refund / no-double-refund regression is
mandatory.

## Architecture dependencies still open

All **Not decided / Evidence pending** (RB-14): AR-002 distribution/API strategy (+ any
internal bulk-ops need); AR-003 sync orchestration/queue framework + Odoo-Online
feasibility; AR-004 module boundaries/config model; AR-005 binding/dedup data model +
per-store keys + deleted-binding handling; AR-006 error/retry taxonomy + idempotency
mechanism + reconciliation cadence; AR-007 inventory design incl. apply mode (auto-apply);
AR-008 fulfilment design. Also open: the **Domain 9 draft-artifact exception** (returns to
ChatGPT if RB-14 finds a draft invoice/payment artifact is required). **DEC-003 feeds these
rows; it decides none of them.**

## Evidence-consistency gate

**DP-006 evidence-consistency gate applied; no new issue discovered.** Recording the
accepted scope introduced **no** claim→fact promotion: competitor claims stayed claims;
weak/claim-only evidence stayed out of scope (pHash, TQ 403 breadth, EC/SH breadth); WK
default-Company field stayed a config field (**not** multi-company evidence, DP-004);
auto-apply stock stayed an **[Inference]** routed to AR-007 (DP-006); "real-time" was never
asserted. Scope acceptance was kept strictly separate from any mechanism decision
(architecture stays gated). **No new DP row; no counter change** — see the Sprint G note in
`../05-qa/defect-pattern-log.md`.

## No-code / no-architecture confirmation

**No connector code**, no Odoo module, no `*.py`/`*.xml`/`*.csv`/manifest/controller/
security/data/migration/test files, no CI/Docker, no architecture doc, no architecture
ADR, no implementation-plan doc, no module boundary, and no REST/GraphQL, queue-framework,
data-model, or distribution decision were created. Only the allowed docs were changed.
**Implementation remains blocked** until RB-14 and later planning are approved.

## Recommended next sprint

**RB-14 Architecture Preparation — Part 1: Architecture decision framing and
official-source refresh**, starting with **AR-002** (distribution/API strategy), **AR-003**
(sync orchestration/queue), and **AR-005** (binding/dedup model). Keep the no-code gate;
one scoped objective per session; route every proposal through the architecture-review log
and (on acceptance) an ADR. **Do not start RB-14 in this sprint.**

## Learning feedback loop

- **New issues discovered:** **none.** DP-006 gate applied, not re-triggered; DP-003/004
  (claim ≠ fact; config field ≠ demonstrated support) and DP-005 (classification/scope is
  an input until accepted) held. This sprint *does* record an accepted **product-scope**
  decision (DEC-003) — the first `04-decisions` record — which is the correct, gated way to
  finalize scope (ChatGPT-approved), not a defect.
- **Repeated issue patterns:** none at threshold (no new occurrence).
- **Rules/checklists updated:** none required.
- **New rejected approaches:** none — deferrals are **product-scope boundary decisions**
  with revisit conditions, **not** rejected architecture approaches (`CLAUDE.md` §10).
- **New technical debt:** none (no code).
- **Architecture concerns:** DEC-003 supplies scope inputs to AR-002…AR-008 — recorded as a
  non-decision note in `architecture-review-log.md`; all rows stay Not decided / Evidence
  pending.
- **Should future prompts change? No** — the acceptance flow worked: ChatGPT decides, Claude
  records in a gated `04-decisions` record + aligns docs, architecture stays RB-14-gated.
  Branch reality remains the harness-designated `claude/...` branch while the PR targets
  `Shopify-connector`.

## What ChatGPT should review

1. **DEC-003** records only the accepted MVP **product scope**, not architecture.
2. **Domain 9** is minimal financial evidence/order representation only; no accounting
   automation (and the draft-artifact exception is architecture-gated).
3. **Product/customer export** and **refunds/cancellations** are deferred; user stories +
   boundaries agree.
4. **Bulk ops** are not a user-facing MVP feature; RB-14 may assess internal need.
5. **Single-store/single-company** baseline with future-safe keys.
6. **No AR row is decided**; every mechanism stays gated.

## Stop confirmation

Stopped at the Sprint G boundary as instructed. **No** connector code, **no** Odoo module,
**no** architecture decision, **no** architecture doc/ADR, **no** implementation plan,
**no** module boundary, **no** REST/GraphQL/queue-framework/data-model/distribution choice.
MVP **product scope is accepted** (DEC-003); architecture remains gated; implementation
remains blocked. `main` and plain `dev` untouched; only Sprint G allowed files changed.
Awaiting ChatGPT review.

---

# Product Sprint F Handoff

> **Product Sprint F — MVP Scope Proposal, Non-MVP Boundaries, and User Stories
> (RB-13).** MVP-proposal synthesis only; **no-code gate in force** (`CLAUDE.md`
> §4–§5). High-power mode **not required** (focused MVP synthesis of already-merged
> repo evidence — no new competitor crawling, no research fan-out). Everything is a
> **proposal / input / inference / recommendation** — **no MVP scope is finalized**
> (ChatGPT accepts at RB-13) and **no architecture is decided** (RB-14 / AR-002…AR-008,
> all Not decided / Evidence pending). Session date 2026-07-01.

## Sprint F revision (PR #54 review — 2026-07-01)

ChatGPT review returned **REVISE** — a small consistency patch (no new research, no
scope change). Corrected on the same branch (`docs: clarify refund acceptance principle
in sprint f`):

- **Refund sync remains open / lean defer** (C-RET-01, US-E4-06) — **not** turned into
  MVP.
- The **MVP acceptance principles** (`mvp-scope.md`) and the user-stories acceptance
  principles now clarify that the **idempotent-refund / no-double-refund regression
  scenario (A-IMP-4) applies only if refund handling is included in MVP; if refunds are
  deferred, it is carried forward as a mandatory acceptance principle for the first
  refund/refund-sync sprint** (never dropped).
- **No MVP scope finalized; no architecture decision made.** Consistency correction only
  (see the Sprint F revision note in `../05-qa/defect-pattern-log.md`; not a new defect
  occurrence, no counter change). MVP remains **proposed, not final**.

## Session summary

Produced the **evidence-based MVP scope proposal** for the Odoo 19 ↔ Shopify
Connector — `docs/02-product/mvp-scope.md` (the main deliverable),
`docs/02-product/non-mvp-and-later-phases.md` (strict boundaries), and
`docs/02-product/user-stories.md` (10 MVP epics + 6 later-phase epics) — consuming the
Sprint D taxonomy/evidence map and the Sprint E vision + setup/UX principles. The
proposal recommends **Option A — "correctness core, import-first"**: a **single-store**
connector that **imports** products (variants + basic images + base price), customers
(deduped), and orders (basic lifecycle + the minimal payment/journal representation the
Odoo order flow needs), and **writes back** inventory (multi-location-aware, idempotent)
and fulfilment/tracking, on a full **correctness engine** (layered webhooks + scheduled
+ first-class reconciliation + manual; idempotency; GID↔Odoo binding + documented dedup
keys; per-record isolation; retry classification with safe manual retry; rate-limit
awareness; resumable jobs) with an **operator experience** (guided setup + readiness
self-test; command center; recovery-first error center; honest freshness) and
**role-based access** + open docs. It **excludes/defers** product/customer export,
refunds/returns lifecycle, payouts, Markets/B2B/POS/gift cards/metafields, multi-store &
multi-company, pricelists/per-market, custom transforms, bulk-ops-as-a-feature, and
advanced analytics. The **DP-006 evidence-consistency gate** (8 checks) was applied to
every capability. **No connector code, no Odoo module, no MVP finalization, no
architecture decisions, no ADRs, no implementation plan, no module boundaries, no
queue/API/distribution/data-model choices** were produced. Synthesis was
**worker-owned** (no fan-out).

## Files created or updated

- `docs/02-product/mvp-scope.md` (**new** — main deliverable).
- `docs/02-product/non-mvp-and-later-phases.md` (**new**).
- `docs/02-product/user-stories.md` (**new**).
- `docs/02-product/product-research-handoff.md` (**updated** — this Sprint F section).
- `docs/01-research/research-handoff.md` (**updated** — Sprint F handoff + checkpoints).
- `docs/05-qa/defect-pattern-log.md` (**updated** — Sprint F note: DP-006 gate applied,
  not re-triggered; no new occurrence).
- `docs/05-qa/architecture-review-log.md` (**updated** — Sprint F non-decision note:
  MVP proposal supplies capability-scope inputs to AR-002…AR-008; all still Not decided
  / Evidence pending).
- `docs/05-qa/rejected-approaches-log.md` (**updated** — Sprint F "nothing rejected"
  note; MVP exclusions are recommendations-against-MVP, not rejected approaches).
- `docs/05-qa/technical-debt-register.md` (**updated** — Sprint F "no debt" note).

## MVP proposal summary

- **Thesis:** *small but excellent = a correct, observable, recoverable single-store
  sync loop across the core objects — proven, not just claimed — wrapped in an operator
  experience a non-developer can run.* Win on **demonstrated correctness** +
  **operator experience**, at the **demonstrated object baseline for one store** — not
  on object-direction breadth or premium surfaces.
- **Recommended option:** Option A (correctness core, import-first), chosen over
  Option B (bidirectional catalog — doubles complexity, forces destructive-apply safety
  + AR-002/005 early) and Option C (thin import-only pilot — violates the correctness
  non-negotiables; small but not excellent).
- **Quality bar:** correct-under-failure, recoverable, observable & honest, safe,
  approachable-then-powerful, evidenced & documented, modular & upgrade-safe.

## Recommended MVP scope

**Proposed for ChatGPT review — not final until accepted.** Include: store connection
+ credential masking + guided setup + test-connection + readiness self-test
(C-CONN-01…06, C-FUL-03); product/variant/basic-image/base-price import + exclude-from-
sync (C-PROD-01/04, C-VAR-01/02, C-PRICE-01); customer import + multi-key matching +
basic address (C-CUST-01/03/04); order import + backfill (60-day gate) + status map +
basic workflow (C-ORD-01…04); inventory write-back (multi-location-aware, idempotent) +
quantity-field default + controlled stock import (C-INV-01…04); fulfilment + tracking
write-back (C-FUL-01/03); layered sync + reconciliation + HMAC + id-dedup + freshness
(C-SYNC-01…07); queue/job concept + retry classification + safe retry + idempotency +
rate-limit awareness + resumable jobs (C-JOB-01…05/07); reason-coded logs + audit +
recovery-first error center + notifications (C-OBS-01…04); command center
(C-DASH-01…06); essential mappings + binding/dedup keys + location/gateway routing
(C-MAP-01…04); role-based access + multi-store-safe keys (C-MULTI-03, C-MULTI-01);
open docs + changelog + built-in self-test (C-DOCS-01…03). **Open (ChatGPT direction
call):** product/customer export (C-PROD-02/05, C-CUST-02), Domain 9 minimum
(C-PAY-01/02/03), refunds/cancellations (C-RET-01/03), bulk ops (C-JOB-06).

## Recommended exclusions

Advanced refunds/returns lifecycle (C-RET-02), payouts (C-POUT-01/02), Markets/B2B/POS/
gift cards/metafields/extended breadth (C-ADV-01…06), multi-company (C-MULTI-02),
full multi-store (C-MULTI-01), pricelists/per-market (C-PRICE-02/03), SEO/taxonomy +
BoM/kit (C-VAR-03/04), order risk (C-ORD-05), multi-package fulfilment (C-FUL-02),
custom Python transforms (within C-MAP-03), dedicated analytics/financial reporting
(C-RPT-01/02), App-Store/Built-for-Shopify + public demo packaging (C-DOCS-04, within
C-DOCS-03 — distribution-gated). Full rationale + revisit conditions in
`non-mvp-and-later-phases.md`.

## User story summary

10 MVP epics (store setup & readiness; product/catalog; customer import & matching;
order import & lifecycle; inventory & freshness; fulfilment & tracking; logs/errors/
retries/recovery; command center; mapping & configuration; permissions & roles) with
persona-driven, testable, product-level stories (P1–P4), each traced to capability IDs,
evidence strength, and AR gate; plus 6 later-phase epics (L1 bidirectional; L2 financial
depth; L3 payouts; L4 premium breadth; L5 multi-tenancy; L6 scale & analytics).
**Stories are not implementation tasks** (no code-level criteria, no screens/modules).

## Evidence-consistency gate

The **DP-006 evidence-consistency gate** was **applied, not re-triggered** (see
`mvp-scope.md` "Evidence-consistency review", 8 checks): Tier-1 facts labelled
**[Fact]**; EM/VT-demonstrated weighted over SH/WK/EC/TQ claims; competitor-claim-only
items kept out or flagged (pHash image dedup, TQ breadth); improvement opportunities
labelled **[Inference]** (unified command center, recovery-first error center, freshness,
empty states, **auto-apply stock C-INV-04** → routed to AR-007, not decided); conditional
items kept conditional (OAuth/distribution/queue/binding/taxonomy/inventory/fulfilment/
module-boundaries); WK multi-company stays a config field (➖, DP-004), WK import-stock
stays ⬜; "real-time" never asserted (C-SYNC-07 honesty). No claim was promoted to a
fact and no capability entered MVP as a decision.

## MVP inputs, not final decisions

The MVP scope, the three options, the include/exclude/defer/open calls, the
MVP-critical spine, and the acceptance principles are **inputs for RB-13 acceptance**,
**not** commitments. Every inclusion is marked **"Proposed MVP inclusion — pending
ChatGPT acceptance."** The document is banner-marked **proposed, not final**.

## Architecture inputs, not decisions

MVP commits **requirements/intent**, never mechanism. Architecture-dependent items are
mapped to **AR-002…AR-008** (all Not decided / Evidence pending) in `mvp-scope.md`
"Architecture-dependent MVP items": AR-002 (distribution/API/bulk/App-Store), AR-003
(orchestration/queue framework), AR-004 (module boundaries/config model/feature flags),
AR-005 (binding/dedup data model/keys), AR-006 (error-retry taxonomy/idempotency
mechanism/reconciliation cadence), AR-007 (inventory design/apply mode), AR-008
(fulfilment design). **No AR row is decided, proposed for active review, or
re-litigated** — logged as a Sprint F non-decision note in `architecture-review-log.md`.

## Open questions

Primary MVP persona (P1 vs P2); **direction** (is export in MVP or Phase 2); **Domain 9
minimum** (smallest payment/invoice/journal representation); **refunds/cancellations**
(basic idempotent, or deferred); **distribution (AR-002)** (unblocks OAuth-mandatory,
GraphQL-only, App-Store/demo packaging); single- vs multi-store/company at MVP
(proposed: single-store, multi-store-safe keys); reconciliation cadence + per-object vs
global freshness (AR-003/006); error/retry taxonomy depth + auto-retry set (AR-006);
essential mappings + dedup/match key set (AR-005); bulk-ops need for backfill (C-JOB-06);
readiness/self-test check set; Odoo edition/hosting (Odoo Online support? edition-gated
reports disclosure).

## Learning feedback loop

- **New issues discovered:** none. No new defect pattern emerged. The **DP-006
  evidence-consistency gate** (3rd-occurrence, ESCALATED) was **applied, not
  re-triggered**: no competitor claim was promoted to a fact, no capability entered MVP
  as a decision, weak/claim-only evidence was kept out of scope (not turned into scope),
  and no architecture was finalized. DP-003/DP-004 (claim ≠ fact; config field ≠
  demonstrated support; market promise ≠ demonstrated bidirectionality) and DP-005
  (classification/scope is an input, not a decision) were applied throughout.
- **Repeated issue patterns:** none at threshold this sprint (no new occurrence added to
  any category).
- **Rules/checklists updated:** none required — existing rules sufficed and were
  applied. QA logs received non-decision / no-new-issue notes only.
- **New rejected approaches:** none — MVP exclusions are **recommendations against MVP
  inclusion only**, not rejected architecture approaches (`CLAUDE.md` §10); noted in
  `rejected-approaches-log.md`.
- **New technical debt:** none (no code). Noted in `technical-debt-register.md`.
- **Architecture concerns:** the MVP proposal supplies **capability-scope inputs** to
  AR-002…AR-008 — recorded as a **non-decision note** in `architecture-review-log.md`.
  All rows stay Not decided / Evidence pending.
- **Tests or review gates needed:** none active (synthesis). The DP-006
  evidence-consistency gate remains the standing pre-MVP/architecture review gate; the
  MVP acceptance principles reference the seeded regression scenarios (A-IMP-4).
- **Should future prompts change? No** (beyond what Sprints D/E encoded) — MVP-synthesis
  prompts should keep requiring every scope call to be an **input** with MVP=RB-13 /
  architecture=RB-14 gating, keep synthesis worker-owned, keep conditional platform
  items conditional (DP-006), and keep exclusions as recommendations-against-MVP (not
  rejected approaches). Branch reality remains the harness-designated `claude/...`
  branch while the PR targets `Shopify-connector`.

## What ChatGPT should review

1. **Thesis & option choice** — is "correct, observable, recoverable single-store loop,
   import-first" the right MVP thesis, and is **Option A** right over B and C?
2. **Evidence-consistency gate (DP-006)** — confirm the 8-check review holds and nothing
   weak/claim-only became scope; auto-apply (C-INV-04) stays inference.
3. **Include/exclude/defer/open** — especially the **open** direction forks
   (export, Domain 9 minimum, refunds/cancellations, bulk ops).
4. **Architecture-dependent table** — confirm MVP commits *intent* only; no AR row
   decided.
5. **MVP-critical spine + acceptance principles** — endorse/amend the reliability/UX/
   config/security core and the (product-level, not code-level) acceptance principles.
6. **Boundaries & stories** — confirm the non-MVP boundaries are strict enough and the
   user stories are not implementation tasks.

## Recommended next sprint

Await ChatGPT's **RB-13 MVP acceptance/revision**. On acceptance, proceed to **RB-14
(architecture preparation)** against AR-002…AR-008 — starting with the **distribution
decision (AR-002)**, which unblocks the most conditionals (OAuth/GraphQL/App-Store), and
the **queue-framework/orchestration (AR-003)** and **binding/dedup model (AR-005)** that
the correctness core depends on — all gated and ChatGPT-reviewed. Optionally firm up
weak/blocked evidence (TQ 403; EC/R5; 17 unread VT Confluence) if ChatGPT wants firmer
classification. Keep the no-code gate; one scoped objective per session.

## Stop confirmation

Stopped at the Sprint F boundary as instructed. **No** connector code, **no** Odoo
module, **no** MVP finalization, **no** architecture decisions, **no** ADRs, **no**
implementation plan, **no** module boundaries, **no** REST/GraphQL, queue-framework,
distribution, or data-model choices. MVP scope is marked **proposed, not final**.
`main` and plain `dev` untouched; only the Sprint F allowed files changed. Awaiting
ChatGPT review.

---

# Product Sprint E Handoff

> **Product Sprint E — Product Vision, Quality Bar, UX Principles, and
> Differentiation Strategy (RB-11).** Product strategy / synthesis only; **no-code
> gate in force** (`CLAUDE.md` §4–§5). High-power mode **not required** (synthesis of
> already-merged repo evidence — no new competitor crawling, no research fan-out).
> Everything is an **input / thesis / principle / inference / recommendation** —
> **no MVP scope and no architecture is decided** (MVP = RB-13, architecture = RB-14
> / AR-002…AR-008, both gated). Session date 2026-07-01.

## Session summary

Created the **product vision** ([`./product-vision.md`](./product-vision.md)) and the
**setup/UX principles** ([`./setup-ux-principles.md`](./setup-ux-principles.md)) for
the Odoo 19 ↔ Shopify Connector, consuming the Sprint C research baseline and the
Sprint D canonical feature taxonomy + capability evidence map. The vision positions
the connector as **correctness-first, UX-first, recovery-first, observable, honest,
modular/customizable, performance-aware, evidence-based, upgrade-safe, and premium
but not bloated** — simple for normal users, powerful for advanced users. It states
the product thesis, target personas (inference-level), core customer problems, ten
product principles, a premium quality bar, a five-theme differentiation strategy,
per-domain strategies (UX, reliability, modularity, performance, security, docs/trust),
seven product non-negotiables, and explicit **MVP / later / architecture inputs (not
decisions)**. The UX doc defines a UX north star and 12 principles plus per-area
principle sets. **No connector code, no Odoo module, no MVP finalization, no
architecture decisions, no ADRs, no implementation plan, no module boundaries** were
produced. The **DP-006 evidence-consistency gate** was applied throughout: competitor
claims stayed claims, conditional platform items (OAuth, distribution, queue,
REST/GraphQL, multi-company, module boundaries, payouts, data models) stayed
conditional/open, and improvement opportunities were labelled inference, not
demonstrated competitor evidence. Synthesis was **worker-owned** (no fan-out).

## Files created or updated

- `docs/02-product/product-vision.md` (**new** — main deliverable).
- `docs/02-product/setup-ux-principles.md` (**new** — UX principles/quality bar).
- `docs/02-product/product-research-handoff.md` (**updated** — this Sprint E section).
- `docs/01-research/research-handoff.md` (**updated** — Sprint E handoff + checkpoints).
- `docs/05-qa/defect-pattern-log.md` (**updated** — Sprint E note: DP-006 gate applied,
  not re-triggered; no new occurrence).
- `docs/05-qa/architecture-review-log.md` (**updated** — Sprint E non-decision note:
  vision/UX principles supply product-intent inputs to AR-002…AR-008; all still Not
  decided / Evidence pending).
- `docs/05-qa/rejected-approaches-log.md` (**updated** — Sprint E "nothing rejected"
  note).
- `docs/05-qa/technical-debt-register.md` (**updated** — Sprint E "no debt" note).

## Product vision summary

- **What:** a best-in-class, modular, reliable Odoo 19 ↔ Shopify connector — a
  correct, observable sync core wrapped in an operator experience, delivered as an
  isolated, upgrade-safe addon family.
- **Positioning:** *correct by design, honest by default — and can prove both to the
  operator.*
- **Thesis:** breadth is table stakes; win on **demonstrated correctness** and the
  **operator experience**, ship the demonstrated breadth as a clean baseline, and
  offer premium breadth as **optional add-ons** on an honest, modular core.
- **Premium quality bar** is defined by correctness/experience/trust, **not** feature
  count; seven **non-negotiables** form the quality contract.
- **Differentiation (inputs):** (1) demonstrated correctness (idempotency +
  reconciliation + rate-limit awareness), (2) command center + recovery-first errors
  together, (3) easy onboarding with real reliability, (4) honesty/transparency, (5)
  premium breadth as clean add-ons.

## UX principles summary

- **North star:** the operator always knows *is everything OK / what failed and why /
  what do I do next* and can act without reading source or filing a ticket.
- **12 principles:** guided setup; prove readiness before sync; progressive
  disclosure; honest status & freshness; command center over scattered menus;
  recovery-first errors; safe-by-default actions; human-readable logs; guided
  mappings; role-aware UX; modular feature visibility; documentation mirrors the
  product — plus per-area principle sets (setup, config, dashboard, sync, logs/recovery,
  mapping, multi-store/permissions, advanced). **No screens or menus are designed.**

## Strong product implications

Grounded in demonstrated (EM/VT) evidence + Tier-1 facts (weighted over SH/WK/EC/TQ
claims):

1. **Correctness is the spine and the headline** — idempotency + first-class
   reconciliation + rate-limit/cost-aware throttling is the market's biggest
   whitespace and Tier-1-mandated.
2. **The operator experience is the second whitespace** — unify the command center
   with a recovery-first error center, which no competitor combines.
3. **Easy + reliable onboarding together** is a combination nobody has — guided
   OAuth-style setup + readiness check without excluding Odoo Online.
4. **Trust is cheap and rewarded** — honest latency/freshness, dated changelog, open
   docs/demo, visible reconciliation/throttle status.
5. **Premium = correct and well-run, not more toggles** — breadth ships as
   feature-flagged optional add-ons on the core.

## MVP inputs, not decisions

> Candidates for **RB-13** review only; **not** selected/sequenced/committed.

- **Candidate core (input):** connect+prove; core object sync at the demonstrated
  baseline; the sync+correctness engine (webhooks + reconciliation + scheduled +
  manual, idempotency, dedup/binding, retry/recovery); operator UX (command center +
  recovery-first errors + honest freshness); role-based access.
- **Explicitly later (input):** advanced breadth (Markets, B2B, POS, gift cards,
  metafields, extended breadth), payouts, financial reporting, per-market pricing,
  custom-Python transforms, multi-company.
- **Open MVP-shaping questions:** single/multi-store; single/multi-company; core vs
  optional add-on grouping (feature flags); **primary MVP persona (P1 operator vs P2
  admin/consultant)**.

## Architecture inputs, not decisions

> Routed to **AR-002…AR-008**, all **Not decided / Evidence pending**. This vision
> chooses none and re-litigates none (`CLAUDE.md` §10).

- **AR-002:** distribution (public vs custom) **OPEN** — gates OAuth-mandatory,
  GraphQL-only, billing/compliance webhooks. REST/GraphQL/hybrid **OPEN**.
- **AR-003:** sync orchestration + queue framework (`ir.cron` vs OCA `queue_job`)
  **OPEN**; Odoo-Online implications open.
- **AR-004:** module boundaries/names **OPEN** (layered family is the direction only);
  feature-flag mechanism open.
- **AR-005:** binding/dedup data model **OPEN** (`ir.model.data` reuse vs dedicated).
- **AR-006:** error/retry taxonomy + idempotency mechanism **OPEN**.
- **AR-007/008:** inventory & fulfilment design **OPEN** (product intent is Tier-1
  anchored: multi-location, write `available`/`on_hand` only, FulfillmentOrder-based).

## Open questions

Distribution model (AR-002); primary MVP persona + single/multi-store & company
(RB-13); core vs add-on grouping / feature-flag model (RB-13/AR-004); reconciliation
cadence + per-object vs global freshness (AR-003/006); error/retry taxonomy (AR-006);
binding model + deleted-binding handling (AR-005); queue framework + Odoo-Online
(AR-003); payout modelling for non-Shopify-Payments gateways; Odoo edition gating
disclosure; whether firming up weak/blocked evidence (TQ 403, EC/R5, 17 unread VT
Confluence) changes any product framing; demo/docs hosting + self-test scope.

## Learning feedback loop

- **New issues discovered:** none. No new defect pattern emerged. The **DP-006
  evidence-consistency gate** (3rd-occurrence, ESCALATED) was **applied, not
  re-triggered**: no product claim was promoted to a fact, no candidate to a decision,
  and all conditional platform items stayed conditional/open. DP-003/DP-004
  (competitor claim ≠ fact; config field ≠ demonstrated support; market promise ≠
  demonstrated bidirectionality) and DP-005 (classification is an input, not a
  decision) were applied throughout.
- **Repeated issue patterns:** none at threshold this sprint (no new occurrence added
  to any category). The escalation gates remain honoured by the no-code gate.
- **Rules/checklists updated:** none required — existing rules were sufficient and
  were applied. QA logs received non-decision / no-new-issue notes only.
- **New rejected approaches:** none (product-strategy synthesis; nothing evaluated to
  rejection). Noted in `rejected-approaches-log.md`.
- **New technical debt:** none (no code). Noted in `technical-debt-register.md`.
- **Architecture concerns:** the vision/UX principles now supply **product-intent
  inputs** to AR-002…AR-008 — recorded as a **non-decision note** in
  `architecture-review-log.md`. **All rows stay Not decided / Evidence pending.**
- **Tests or review gates needed:** none active (synthesis). The DP-006
  evidence-consistency gate remains the standing pre-MVP/architecture review gate.
- **Should future prompts change? No** (beyond what Sprint D already encoded) —
  product-synthesis prompts should keep requiring every principle/candidate to be an
  **input** with MVP=RB-13 / architecture=RB-14 gating, keep synthesis worker-owned,
  and keep conditional platform items conditional (DP-006). Branch reality remains the
  harness-designated `claude/...` branch while the PR targets `Shopify-connector`.

## What ChatGPT should review

1. **Positioning & thesis** — is "correct by design, honest by default, prove both to
   the operator" right, and are the five differentiation themes correctly prioritised
   as inputs (correctness + operator UX + easy-reliable onboarding first; breadth
   later)?
2. **Evidence discipline (DP-003/004/006)** — no claim-as-fact; EM/VT-demonstrated
   weighted over SH/WK/EC/TQ; WK multi-company config-field-only; conditional items
   (OAuth, distribution, queue, REST/GraphQL, multi-company, module boundaries,
   payouts, data models) stay conditional/open.
3. **No premature MVP/architecture (DP-005 guard)** — confirm principles, quality bar,
   differentiation, strategies, and UX principles read as **inputs**, not decisions or
   final UI/menus; flag any hardening.
4. **Personas** — are P1–P4 reasonable inference-level inputs, and is "primary MVP
   persona" correctly left open?
5. **Non-negotiables** — endorse/amend the seven-item quality contract without
   implying a specific implementation.
6. **Sequencing** — confirm RB-13 (MVP implications) next, then RB-14 (architecture
   prep), both consuming this vision + UX principles.

## Recommended next sprint

**RB-13 (MVP scope implications — not finalized)** consuming this vision + UX
principles + the Sprint D taxonomy/evidence map under the DP-006 evidence-consistency
gate, then **RB-14 (architecture preparation)** against AR-002…AR-008 — all gated and
ChatGPT-reviewed. Optionally firm up weak/blocked evidence (TQ 403; EC/R5; 17 unread
VT Confluence) if ChatGPT wants firmer classification. Keep the no-code gate; one
scoped objective per session.

## Stop confirmation

Stopped at the Sprint E boundary as instructed. **No** connector code, **no** Odoo
module, **no** MVP finalization, **no** architecture decisions, **no** ADRs, **no**
implementation plan, **no** module boundaries, **no** REST/GraphQL or queue-framework
or data-model choices. `main` and plain `dev` untouched; only the Sprint E allowed
files changed. Awaiting ChatGPT review.

---

## Sprint D summary

Sprint D converted the Sprint C competitor evidence into a **canonical feature
taxonomy** and a **capability evidence map** for the connector. It normalized the
messy, marketing-heavy competitor feature matrix into **20 canonical domains** and
≈90 **canonical capabilities**, each classified by evidence status/strength,
capability type (product-UX / reliability / configuration / architecture), candidate
class (baseline / premium / advanced-later / optional add-on / unknown), MVP
relevance (candidate / later / unknown), and architecture-review dependency
(AR-002…AR-008). It **decides nothing** — it produces the shared product vocabulary
that MVP scoping, architecture, setup UX, menu/config design, sync-engine design,
logs/error/retry UX, permission design, test strategy, and implementation prompts
will reuse. No new competitor sources were crawled (synthesis of already-merged
repo evidence only).

## Sprint D revision (PR #52 review — 2026-07-01)

ChatGPT review returned **REVISE** (small taxonomy precision patch). Corrected on
the same branch (`docs: correct sprint d taxonomy precision`); logged as **DP-006**:

- **Removed the `SH` abbreviation collision** — `SH` now means **only**
  sh_shopify_connector / Softhealer; Shopify official docs are keyed
  **SHOPIFY-OFFICIAL** (Odoo official = **ODOO-OFFICIAL**).
- **Made OAuth-first's official-platform dependency conditional** — C-CONN-01 is
  a strong UX/security/product direction and competitor-demonstrated (VT), but is a
  platform *requirement* **only if public/App-Store distribution is chosen**;
  custom/private flows may use Admin API token / custom-app access. AR-002
  (distribution) remains open; do **not** treat OAuth-first as a finalized
  architecture decision. Evidence strength changed `A` → `B / A-if-public`.
- **Reframed stock import (C-INV-04)** as "Stock import with controlled
  apply/review": stock import is demonstrated, but **auto-apply is a recommended
  improvement/inference, not demonstrated competitor evidence**; AR-007 still
  applies.
- **Corrected Webkul import-stock coverage** — WK is **⬜ (not found)** for import
  stock per Sprint C matrix §3 (was incorrectly ✅); matrix-consistent coverage is
  EM✅ VT✅ SH✅ TQ🟨 EC🟨 WK⬜.

## Files created or updated

- `docs/02-product/feature-taxonomy.md` (**new**) — the canonical taxonomy (main
  deliverable): 20 domains, per-capability blocks, cross-cutting groups,
  classification summary, MVP/later/architecture-review inputs, weak-evidence
  register, open questions, ChatGPT review notes.
- `docs/02-product/capability-evidence-map.md` (**new**) — compact per-capability
  traceability (evidence strength A–E, strongest evidence, WK/TQ/EM/VT/EC/SH
  coverage, platform dependency, AR need, MVP relevance).
- `docs/02-product/product-research-handoff.md` (**new**, this file).
- `docs/01-research/research-handoff.md` (**updated**) — Sprint D handoff section +
  checkpoint log entries.
- `docs/05-qa/defect-pattern-log.md` (**updated**) — DP-005 (premature-decision
  risk of taxonomy synthesis; Mitigated) + counter.
- `docs/05-qa/architecture-review-log.md` (**updated**) — Sprint D non-decision
  note (taxonomy supplies capability inputs to AR-002…AR-008; all still Not
  decided / Evidence pending).
- `docs/05-qa/rejected-approaches-log.md` (**updated**) — Sprint D note (nothing
  rejected).
- `docs/05-qa/technical-debt-register.md` (**updated**) — Sprint D note (no debt;
  no code).

## What the taxonomy now enables

- **MVP scoping (RB-13):** a de-duplicated capability list with MVP-relevance tags
  to reason over — *candidates*, not a scope.
- **Modular architecture (RB-14 / AR-004):** capability → domain grouping and
  cross-cutting groups (feature flags, transport abstraction, extension points) as
  **inputs** — no module names or boundaries defined.
- **Setup UX / menu structure / config screens:** Domains 1–2 + cross-cutting
  progressive-disclosure/inline-help/dry-run groups give a canonical UX vocabulary.
- **Sync-engine design (AR-002/003/006):** Domains 13–16 name the trigger/verify/
  reconcile/queue/retry/idempotency/mapping capabilities to design against.
- **Logs/error/retry UX:** Domain 15 + the recovery-first error center capability.
- **Permission design:** Domain 17 (per-store/company isolation, role-based access).
- **Test strategy:** capabilities map to the regression tests already seeded
  (duplicate orders, multi-location double-decrement, missed-webhook reconciliation,
  idempotent refunds, timezone/paging — A-IMP-4).
- **Implementation task prompts:** capability IDs (`C-…`) give stable handles for
  allowed-files/acceptance-criteria scoping when the gate opens.

## Strong product implications

Grounded in **demonstrated** evidence (EM screenshots / VT dated release notes) and
Tier-1 platform facts:

1. **A correct, observable core is the product's spine** — webhooks + HMAC + dedup
   + fast-ack + scheduled + manual + **first-class reconciliation**, idempotent
   writes, queue with per-record isolation, reason-coded logs, and a binding/dedup
   model. Most are **platform-required**, not optional.
2. **The best operator UX is a whitespace we can own** — a **unified command center**
   (SH monitoring + VT diagnostics, which neither fully combines) plus a
   **recovery-first error center** (reasons + isolation + auto-retry + one-click
   manual retry + named causes).
3. **Multi-location inventory and FulfillmentOrder-based fulfillment are baseline**
   (EM/VT demonstrated; platform-required); single-location (WK) and legacy
   fulfillment are anti-patterns.
4. **Idempotency + reconciliation + rate-limit awareness** is the market's biggest
   demonstrated whitespace and is Tier-1-mandated.

## Weak / risky implications

Flagged so they are **not overweighted** downstream (DP-003/DP-004):

- **Teqstars (docs 403):** breadth (Markets/B2B/payouts/queue-retry/idempotency) is
  **claim-only / unverifiable** — do not treat as demonstrated.
- **ecommerce_shopify (no screenshots):** all capabilities are listing claims;
  product **export direction not found**; webhooks **explicitly absent**; errors
  **email-only**.
- **sh_shopify_connector (captions; no ratings/changelog):** breadth rests on
  captions; **multi-company not-found**; idempotency/HMAC unstated.
- **Webkul multi-company:** a **configuration field only** (➖) — not demonstrated
  support (DP-004).
- **Whitespace (no competitor evidence):** rate-limit throttling, first-class
  reconciliation surface, webhook-id dedup — classified by **platform requirement /
  inference**, not competitor demonstration.

## MVP inputs, not decisions

> Candidates for **RB-13** review only. Not selected, sequenced, or committed.

- **Cluster tagged `candidate`:** connect+prove (C-CONN-01…05), core object sync
  (products/variants/pricing/inventory/customers/orders/payments/fulfillment/
  refunds), the sync+correctness engine (C-SYNC-01…07, C-JOB-01…05/07, C-MAP-01…04),
  operator UX (C-DASH-01…05, C-OBS-01…04), and role-based access (C-MULTI-03).
- **Explicitly `later` / not-MVP inputs:** advanced breadth (Markets, B2B, POS,
  gift cards, metafields, extended breadth), payouts, financial reporting, per-
  market pricing, custom-Python transforms, multi-company.
- **Open MVP-shaping questions:** single- vs multi-store; single- vs multi-company;
  which capability groups are core vs optional add-ons (feature flags).

## Architecture inputs, not decisions

> Routed to AR-002…AR-008 — **all Not decided / Evidence pending**. No approach is
> chosen, and none is re-litigated (`CLAUDE.md` §10).

- **AR-002 (API/distribution/bulk):** connection auth, product/variant/backfill
  sync, bulk ops, App-Store readiness. *Distribution (public vs custom) unresolved.*
- **AR-003 (sync orchestration/queue):** webhooks+reconcile+scheduled+manual, queue,
  auto-workflow, resumable jobs. *`ir.cron` vs OCA `queue_job` unresolved.*
- **AR-004 (module boundaries):** domain-isolated config, mapping/metafield
  extensibility, feature flags. *No module names/boundaries defined.*
- **AR-005 (binding/dedup):** GID binding model, dedup keys, multi-store keys,
  customer matching. *`ir.model.data` reuse vs dedicated model unresolved.*
- **AR-006 (error/retry/idempotency):** retry classification, auto-retry,
  idempotency keys, error center, reconciliation.
- **AR-007 (inventory):** quantity sync, quantity-field choice, multi-location,
  auto-apply, BoM stock.
- **AR-008 (fulfillment):** FulfillmentOrder-based fulfillment, multi-package/location.

## UX/UI inputs

- **Onboarding:** OAuth-first + credential masking + explicit test-connection +
  scope/readiness pre-flight; never gate the setup guide.
- **Command center:** health traffic-light + activity timeline + queue/failure
  counts + quick actions + freshness ("last synced / last reconciled").
- **Errors:** reason-coded per-record logs, isolated failures, named causes + fix
  hints, one-click retry; never email-only.
- **Safety:** dry-run/preview before destructive apply; irreversible-action
  warnings; progressive disclosure + inline help on jargon; honest latency labels;
  admin vs functional-user separation.

## Reliability/performance inputs

- **Correctness:** idempotency keys (Tier-1 `@idempotent` 2026-04), first-class
  reconciliation (webhook delivery not guaranteed), webhook HMAC + id-dedup +
  fast-ack, binding-key uniqueness (avoid duplicate/double-decrement).
- **Resilience:** per-record failure isolation, retry classification (auto-safe vs
  manual-fixable), automatic retry with backoff, resumable/chunked jobs.
- **Scale:** rate-limit / GraphQL-cost-aware throttling (whitespace), Bulk
  Operations for backfills, batched ORM writes + indexed binding lookups, no long
  syncs in an HTTP request (Odoo worker limits; crons off on Odoo.sh staging).

## Open questions

1. Distribution model (public App-Store vs custom app) — decides GraphQL-only /
   billing / compliance webhooks (AR-002).
2. Single- vs multi-store, single- vs multi-company at MVP (RB-13).
3. Reconciliation cadence/scope; per-object vs global freshness.
4. Error/retry taxonomy (which errors auto-retry vs need humans).
5. Binding model: `ir.model.data` vs dedicated per-store model; deleted-binding
   handling (AR-005).
6. Queue framework: `ir.cron` vs OCA `queue_job` (non-core; Odoo-Online implications)
   (AR-003).
7. Which capability groups are core vs optional add-ons (feature flags; RB-13).
8. Firm up weak/blocked evidence (Teqstars 403; EC setup guide R5; 17 unread VT
   Confluence articles) — does any classification change?
9. Payout modelling for non-Shopify-Payments gateways (`OrderTransaction` ledger).
10. Odoo edition gating (Enterprise-only reports) disclosure/handling.

## Recommended next sprint

**RB-11 (product vision draft)** and/or **RB-13 (MVP scope implications — not
finalized)**, both consuming this taxonomy + evidence map, then feeding **RB-14
(architecture preparation)** against AR-002…AR-008 — all **gated and
ChatGPT-reviewed**. In parallel, resolve the weak-evidence unblocks (Teqstars docs
403; EC/R5 setup guide; unread VT Confluence) if ChatGPT wants firmer classification.
Keep the no-code gate; one scoped objective per session.

## Stop confirmation

Stopped at the Sprint D boundary as instructed. **No** connector code, **no** Odoo
module, **no** MVP finalization, **no** architecture decisions, **no** ADRs, **no**
implementation plan, **no** module boundaries. `main` and plain `dev` untouched;
only the Sprint D allowed files changed. Awaiting ChatGPT review.
