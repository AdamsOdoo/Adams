# DEC-003 — MVP Scope Baseline

> Accepted **product scope** decision record for the premium Odoo 19 ↔ Shopify
> Connector. It finalizes **what the first excellent MVP covers** — the accepted
> RB-13 baseline from ChatGPT — and nothing else. It is **not** an architecture
> decision, an ADR for any AR row, or an authorization to implement. Companion
> product docs: [`../02-product/mvp-scope.md`](../02-product/mvp-scope.md),
> [`../02-product/non-mvp-and-later-phases.md`](../02-product/non-mvp-and-later-phases.md),
> [`../02-product/user-stories.md`](../02-product/user-stories.md).

## Status

**Accepted by ChatGPT on 2026-07-01.**

- **Sprint:** Product Sprint G (RB-13 — MVP scope acceptance).
- **Supersedes:** nothing. It **accepts** and finalizes the Sprint F MVP scope
  *proposal* (PR #54, merged into `Shopify-connector`) as the product-scope baseline.
- **Phase:** product/MVP scope only — the **no-code gate remains in force**
  (`CLAUDE.md` §4–§5). Architecture (RB-14 / AR-002…AR-008) and implementation remain
  **blocked**.

## Decision type

**Product scope decision, not architecture decision.** This record fixes the MVP
capability boundary (the *what*). It makes **no** decision about the *how*: no API
strategy, no queue framework, no data model, no module boundary, no binding/dedup
mechanism, no distribution model, and no implementation plan (see
*Architecture dependencies* and *Review / change control*).

## Context

- **Where we are.** Research Sprints A–C and Product Sprints D–F produced the
  governance foundation, the Tier-1 Shopify/Odoo platform facts, the competitor
  evidence base, the canonical feature taxonomy + capability evidence map, the product
  vision + setup/UX principles, and — in Sprint F (PR #54) — an **evidence-based MVP
  scope proposal**, strict non-MVP boundaries, and user stories. The proposal was
  explicitly **"proposed, not final"** and left several **direction forks open for
  ChatGPT** (product/customer export, the Domain 9 financial minimum, refunds/
  cancellations, bulk operations, primary persona).
- **Forces.** A premium MVP must beat existing connectors on **demonstrated
  correctness** and **operator experience**, not on breadth. It also fails if it
  **over-scopes** — pulling in a second sync direction, full accounting, refunds/
  returns depth, and multi-tenancy that each multiply complexity and fragility.
- **Evidence discipline.** The **DP-006 evidence-consistency gate** (3rd-occurrence,
  ESCALATED — `../05-qa/defect-pattern-log.md`) governs this decision: no capability
  enters the baseline as a decision unless its evidence strength, conditionality, and
  competitor coverage are consistent. Competitor claims stay **claims**; a config field
  is **not** demonstrated support (DP-004); a market promise is **not** demonstrated
  bidirectionality; improvement opportunities are **inference**; conditional platform
  requirements stay **conditional**.
- **Input labels.** **[Fact]** = Tier-1 Shopify/Odoo official; **[Demonstrated]** = a
  specific competitor workflow/screenshot/dated release note; **[Competitor claim]**,
  **[Inference]**, **[Recommendation]**, **[Open question]**. Competitor evidence access
  date **2026-06-30**; decision/session date **2026-07-01**.

## Decision

ChatGPT accepts **Option A — Correctness core, import-first** as the MVP scope
baseline: a **correct, observable, recoverable single-store sync loop** across the core
commerce objects — proven, not merely claimed — wrapped in an operator experience a
non-developer can run. The MVP wins on **depth of correctness** (idempotency +
first-class reconciliation + rate-limit awareness + recovery-first operations), **not**
on breadth of coverage, a second catalog direction, or financial/accounting depth.

The sections below record the accepted baseline precisely. Everything not listed as
**in MVP** is **deferred** or **excluded** (see *Non-goals* and
[`../02-product/non-mvp-and-later-phases.md`](../02-product/non-mvp-and-later-phases.md)).

## Accepted MVP option

**Option A — Correctness core, import-first (ACCEPTED).**

- **Meaning:** a small but excellent MVP is a **correct, observable, recoverable
  single-store sync loop** across the core commerce objects — **not** a broad
  bidirectional connector.
- **Rejected for MVP (kept as later phases, not rejected approaches):**
  - **Option B — Bidirectional catalog (broader):** Option A plus product/customer
    export, publish/channel control, pricelist mapping. Deferred — it doubles
    direction/conflict complexity, forces the destructive-apply safety (**[Fact]**
    `productSet` delete-on-omit) and AR-002/AR-005 earlier, and trades correctness depth
    for coverage breadth. Natural **Phase 2**.
  - **Option C — Thin import-only pilot (narrower):** import + manual sync only, no
    webhooks/reconciliation/write-back. Rejected — it violates the correctness
    non-negotiables (webhook-less/cron-only with no reconciliation is a demonstrated
    anti-pattern) and removes the back-office value; *small but not excellent.*

## Accepted MVP scope

**Primary direction (accepted).**

- **Shopify → Odoo (import):**
  - product import
  - variant / options import
  - basic image / media import
  - base price / compare-at import
  - customer import and matching (deduplicated; email primary, multi-key allowed)
  - order import
  - order status / basic order lifecycle representation
- **Odoo → Shopify (write-back):**
  - inventory write-back (multi-location-aware; idempotent)
  - fulfillment and tracking write-back

**Correctness / reliability / observability spine (accepted, MVP-critical).** The
non-negotiable core of "small but excellent":

- **Layered sync:** webhooks + scheduled sync + manual sync + **reconciliation**
  (never one mechanism alone).
- **HMAC verification** of webhooks; **webhook ID deduplication**; **fast webhook
  acknowledgement**.
- **Idempotency keys / idempotent write strategy**; **duplicate prevention**.
- **Per-record failure isolation**; **reason-coded logs**; **safe manual retry**;
  **retry classification concept**.
- **Rate-limit / cost awareness**; **resumable jobs**.
- **Honest freshness** — truthful "last synced / last reconciled" labels; no
  "real-time" overstatement.

**Operator experience / UX (accepted, MVP scope).**

- Guided setup; credential masking; test connection; readiness / self-test.
- A **basic command center** with health indicators and activity / failure counts.
- A **recovery-first error center (MVP version)** — every failure isolated,
  reason-coded, retryable, with a named next action.
- Quick actions that **enqueue** work (never run heavy sync inline).
- **Essential mappings only** (no custom transforms).
- **Role-based access:** admin vs functional user.
- Open, screenshot-rich docs; a **dated changelog**; a **built-in self-test**.

**Inventory (accepted, MVP scope).**

- Inventory write-back is **in MVP**.
- Must be **multi-location-aware enough** to avoid a wrong single-location design.
- **`committed` must never be written**; write only allowed Shopify quantity fields.
- Initial Shopify stock import is **controlled / reviewed**.
- **Auto-apply stock is NOT accepted as default MVP behaviour yet** — it remains an
  **[Inference]** routed to **AR-007** (do not implement auto-apply as a decided MVP
  behaviour).

**Store / company scope (accepted).**

- **Single-store MVP**; **single-company MVP**.
- **No multi-store UI/logic** and **no multi-company logic** in MVP.
- But **architecture-safe**: binding keys must not block future multi-store;
  configuration assumptions must not make future multi-store impossible; Webkul's
  default Company field is **not** treated as real multi-company evidence (DP-004).

## Deferred from MVP

Deferred (recognised, planned for a later phase — **not** rejected, **not** technical
debt):

- Odoo → Shopify **product export**.
- Odoo → Shopify **customer export**.
- **Publish / unpublish / channel-control** export flows.
- **Bidirectional catalog ownership.**
- **Refund sync**, **cancellation reflection**, and the **returns / RMA lifecycle**
  (see *Refund/cancellation decision*).
- **Bulk Operations as a user-facing feature** (see *Bulk operations decision*).

Deferral revisit conditions are recorded in
[`../02-product/non-mvp-and-later-phases.md`](../02-product/non-mvp-and-later-phases.md).

## Domain 9 financial/payment decision

**Accepted: include minimal financial/payment representation only.** The MVP must
preserve enough Shopify financial information on the imported Odoo order to make the
order **understandable and operationally useful** — it does **not** automate
accounting.

**In MVP (financial *evidence* / order representation):**

- Shopify **financial status**
- **payment status**
- **gateway / payment method label**
- **transaction reference(s)**, where available
- **paid / unpaid / refunded status flags** — as **source information only**
- order **totals**, **taxes**, **shipping**, **discounts**, **currency**
- **basic gateway/journal mapping as configuration input** — only if needed for
  classification / routing

**Explicitly excluded from MVP (accounting automation):**

- automatic posted invoices
- automatic posted payments
- bank reconciliation
- payout reconciliation
- full accounting workflow
- gateway-specific accounting depth
- automatic refund accounting
- automatic payment posting on retry

**Rule:** *MVP preserves financial evidence and order actionability. It does not
automate accounting.*

**Guard (returned to ChatGPT if triggered):** if RB-14 discovers that some **draft
invoice/payment artifact is absolutely required** for a valid Odoo order flow, it must
be treated as **architecture-dependent** and returned to ChatGPT for review **before
implementation**. Do **not** silently add automatic invoice/payment creation.

## Refund/cancellation decision

**Accepted:**

- **Refund sync is deferred.**
- **Cancellation reflection is deferred.**
- **Returns / RMA lifecycle is deferred.**

**Mandatory future rule (carried forward, never dropped):** if refund handling is later
included, the **idempotent-refund / no-double-refund regression scenario is mandatory**
(**[Fact]** non-idempotent refunds → double-refund). Because refunds are deferred here,
this scenario is carried forward as a mandatory acceptance principle for the first
refund/refund-sync sprint.

## Bulk operations decision

**Accepted:**

- **Bulk Operations are not a user-facing MVP feature.**
- Do **not** expose "bulk operation management" as an MVP feature.

**Architecture note:** RB-14 (**AR-002**) must assess whether **Shopify Bulk
Operations are required internally** for safe/resumable large backfills. If required
internally, that is an **architecture mechanism, not a product-scope expansion** — it
does not change this MVP baseline.

## Store/company decision

**Accepted:** single-store, single-company MVP — **no** multi-store UI/logic and **no**
multi-company logic in the first release — but **architecture-safe** so the future is
not designed out:

- Binding keys **must** be per-store-safe (must not block future multi-store).
- Configuration assumptions **must not** make future multi-store impossible.
- Webkul's default Company field is **not** real multi-company evidence (DP-004);
  multi-company support requires demonstrated record-rule isolation and a future
  decision.

The isolated per-store config **model** (C-MULTI-04) and full multi-store (C-MULTI-01)
remain **architecture-dependent** (AR-004/AR-005) and out of MVP; only the **keys** stay
multi-store-safe.

## Primary MVP persona decision

**Accepted persona priority:**

1. **Primary MVP persona: P1 — Operations / e-commerce user.** MVP UX serves P1's daily
   operation first (run, monitor, read logs, recover).
2. **Secondary MVP persona: P2 — Odoo administrator / implementation consultant.** MVP
   UX serves P2's setup / configuration second.
3. **P3 (business owner / finance buyer)** and **P4 (partner / integrator)** remain
   important buyer/deployer personas, but MVP UX **priority** serves P1 daily operation
   and P2 setup/configuration first.

## Architecture dependencies

This decision commits **MVP intent/requirements only**; each architecture-sensitive
capability's **mechanism** remains gated and **Not decided / Evidence pending** in
[`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md). DEC-003
**feeds** these AR rows; it **decides none** of them:

| AR row | Open decision (NOT made here) | MVP capabilities that depend on it |
| --- | --- | --- |
| **AR-002** | Distribution (public vs custom); REST/GraphQL/hybrid; bulk (internal); App-Store | store connection auth style, product/backfill import, bulk-internal assessment |
| **AR-003** | Sync orchestration + **queue framework** (`ir.cron` vs `queue_job`); Odoo-Online feasibility | layered sync, resumable jobs, order workflow, enqueue actions |
| **AR-004** | Module boundaries/names; feature-flag + config model | essential mappings, per-store config model, multi-store-safe structure |
| **AR-005** | Binding/dedup **data model**; per-store keys; deleted-binding handling | product/customer binding, dedup/match keys, multi-store-safe keys |
| **AR-006** | Error/retry **taxonomy**; idempotency mechanism; reconciliation cadence | retry classification, idempotent writes, reconciliation |
| **AR-007** | Inventory design (fields, multi-location, **apply mode / auto-apply**) | inventory write-back, quantity field, controlled stock import |
| **AR-008** | Fulfilment design (FulfillmentOrder; multi-package/location) | fulfilment + tracking write-back |

**No AR row is decided, accepted, proposed for active review, or re-litigated by this
record** (`CLAUDE.md` §10; DP-005/DP-006).

## Evidence basis

- **Tier-1 platform facts [Fact]:** `../01-research/shopify-official-api-notes.md`,
  `../01-research/odoo-official-architecture-notes.md` (e.g. webhook delivery not
  guaranteed → reconciliation required; `committed` read-only + `@idempotent` on
  inventory/refund writes; FulfillmentOrder-based fulfilment; 60-day `read_all_orders`
  gate; Odoo has no core job queue).
- **Canonical capability model:** `../02-product/feature-taxonomy.md`,
  `../02-product/capability-evidence-map.md` (every `C-…` ID, evidence strength A–E,
  competitor coverage, AR mapping).
- **Product strategy:** `../02-product/product-vision.md`,
  `../02-product/setup-ux-principles.md`.
- **MVP proposal (Sprint F, PR #54):** `../02-product/mvp-scope.md`,
  `../02-product/non-mvp-and-later-phases.md`, `../02-product/user-stories.md`.
- **Quality memory:** `../05-qa/defect-pattern-log.md` (DP-001…DP-006 incl. the
  evidence-consistency gate), `../05-qa/architecture-review-log.md` (AR-002…AR-008).
- **Evidence weighting:** Emipro (EM, screenshot-rich) and VentorTech (VT, dated
  release notes) are the most robustly **[Demonstrated]** sources, weighted over
  caption/guide/claim-only vendors (SH/WK/EC/TQ); Tier-1 platform facts outrank all
  vendor evidence.

## Consequences

**Positive.**

- A **bounded, defensible** MVP that maximises the two differentiation whitespaces
  (demonstrated correctness + operator experience) on a single-store loop.
- Every open Sprint-F direction fork is **resolved**, so RB-14 and later implementation
  planning inherit a **fixed scope** without re-deriving it.
- Financial evidence is preserved (orders are actionable) **without** dragging a full
  accounting integration into MVP.
- Deferrals are **explicit** with revisit conditions, so later phases inherit a clean
  backlog instead of re-litigating scope.

**Negative / trade-offs (accepted).**

- MVP is **import-first, single-direction for catalog/customers** — no Odoo-authored
  product/customer export until Phase 2.
- MVP **does not reflect refunds or cancellations**; finance consistency for those
  events waits for a later phase (with mandatory idempotency).
- MVP **does not automate accounting** — users get financial *evidence*, not posted
  invoices/payments; a genuine draft-artifact requirement is a ChatGPT-gated exception.
- **Single-store / single-company only** — multi-tenancy is deferred (keys stay
  multi-store-safe).

**Follow-ups.**

- Align the product docs to this accepted baseline (Sprint G Stage 3).
- Route the still-open *mechanism* questions to **RB-14** (AR-002/003/005 first).
- No technical debt is created (no code); no rejected-approach entry is created
  (deferral ≠ rejection).

## Non-goals

Explicitly **out of MVP** (deferred or excluded; full treatment + revisit conditions in
[`../02-product/non-mvp-and-later-phases.md`](../02-product/non-mvp-and-later-phases.md)):

- product export; customer export; full bidirectional catalog sync
- advanced refunds; returns / RMA; cancellation processing
- payout reconciliation; full invoices/payments/accounting automation; bank
  reconciliation
- complex tax engine
- Shopify Markets; Shopify B2B; Shopify POS; gift cards; metafields; subscriptions;
  abandoned checkout → CRM; recommendations; Buy with Prime
- multi-store UI/logic; multi-company logic
- custom Python transforms
- advanced analytics / reporting
- public App-Store packaging; public marketplace demo packaging
- app billing / compliance webhook work — unless distribution is later decided

**This record makes no architecture decision, no API-strategy decision, no
queue-framework decision, no data-model decision, no module-boundary decision, and
authorizes no implementation plan.**

## Open architecture questions

These remain **open and gated** (RB-14 / AR-002…AR-008, all Not decided / Evidence
pending) — DEC-003 supplies scope inputs to them but decides none:

1. **Distribution model** (public App-Store vs custom/private) — AR-002; unblocks
   OAuth-mandatory / GraphQL-only / App-Store readiness / internal bulk need.
2. **Sync orchestration + queue framework** (`ir.cron` vs OCA `queue_job`) and
   **Odoo-Online feasibility** — AR-003.
3. **Binding / dedup data model** (`ir.model.data` reuse vs dedicated per-store model)
   and deleted-binding handling; MVP match-key set — AR-005.
4. **Error/retry taxonomy** depth, idempotency mechanism, and reconciliation cadence —
   AR-006.
5. **Inventory design** — quantity field default, minimum multi-location support, and
   **apply mode (auto-apply vs review-then-apply)** — AR-007.
6. **Fulfilment design** (FulfillmentOrder; single- vs multi-package/location) — AR-008.
7. **Module boundaries / names** and the feature-flag + config model — AR-004.
8. **Whether any draft invoice/payment artifact is required** for a valid Odoo order
   flow (Domain 9 guard) — architecture-dependent; return to ChatGPT before
   implementation.
9. **Whether Shopify Bulk Operations are required internally** for safe/resumable
   backfills — AR-002 (internal mechanism, not product scope).

## Review / change control

- **This record finalizes the MVP *product scope* baseline only.** Explicitly:
  - **no architecture decision is made**
  - **no API strategy is decided**
  - **no queue framework is decided**
  - **no data model is decided**
  - **no module boundary is decided**
  - **no implementation plan is authorized**
  - **implementation remains blocked** until RB-14 architecture and later
    implementation planning are approved by ChatGPT.
- **Changes** to this baseline (adding to or removing from MVP scope) require a new
  ChatGPT-reviewed decision record (or an explicit amendment here), not a silent edit in
  a product doc.
- **Related:** RB-13 (this acceptance); RB-14 (architecture prep, next); AR-002…AR-008
  (`../05-qa/architecture-review-log.md`, all Not decided / Evidence pending); PR #54
  (the Sprint F proposal this record accepts).
