# Product Research Handoff

> The **product-side** handoff for the Odoo 19 ↔ Shopify Connector. It records what
> the product-research work (starting with Sprint D) produced, what it now enables,
> and the implications/inputs it hands to later gated sprints. It complements the
> rolling engineering-research handoff at
> [`../01-research/research-handoff.md`](../01-research/research-handoff.md).
>
> **Governance:** research/synthesis phase; **no-code gate in force**
> (`CLAUDE.md` §4–§5). Everything here is an **input/inference/recommendation** —
> **no MVP scope and no architecture is decided** (MVP = RB-13, architecture =
> RB-14 / AR-002…AR-008, both gated). Access date for competitor evidence:
> 2026-06-30; session date: 2026-07-01.

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
