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
