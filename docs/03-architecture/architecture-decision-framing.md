# Architecture Decision Framing — Map of Active AR Rows

> **RB-14 Architecture Preparation — Part 1.** This is the **single map** of all
> active architecture-review (AR) rows for the Odoo 19 ↔ Shopify Connector. It
> **frames** the decisions — it does **not** make any of them. In this sprint only
> **AR-002** (distribution / API strategy), **AR-003** (sync orchestration / queue),
> and **AR-005** (binding / dedup / identity) receive **deep framing** (their own
> companion documents); the other rows are mapped and their dependencies recorded.
>
> **Gate status (unchanged):** the **no-code gate** (`CLAUDE.md` §4–§5) and the
> **no-architecture-decision gate** remain in force. Every AR row below is
> **[Not decided]** and stays **"Evidence pending"** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).
> **No REST/GraphQL, queue-framework, binding/data-model, module-boundary, or
> distribution choice is made here.** This document exists so ChatGPT can review
> the framing **before** any architecture-decision sprint.

## Evidence classification used in this document

Per the RB-14 prompt and `CLAUDE.md` §8, every statement is one of:
`[Official fact]` · `[Official limitation]` · `[Competitor demonstrated]` ·
`[Competitor claim]` · `[Inference]` · `[Recommendation]` · `[Open question]` ·
`[Decision — existing]` · `[Not decided]`.

Rules re-stated: competitor evidence **cannot** become an official fact; official
docs **cannot** decide our architecture by themselves; recommendations and options
are **not** decisions; **MVP scope is already decided by DEC-003 and is not
re-opened**; **architecture remains not decided**.

---

## 1. Current architecture gate status

- **[Decision — existing]** The MVP **product scope** is fixed by
  [`../04-decisions/DEC-003-mvp-scope.md`](../04-decisions/DEC-003-mvp-scope.md)
  (accepted 2026-07-01, revised same day after PR #55): **Option A — correctness
  core with controlled bidirectional product onboarding.** DEC-003 is a
  **product-scope** decision that **feeds** AR-002…AR-008 and **decides none** of
  them.
- **[Not decided]** All architecture rows **AR-002…AR-008** are **"Not decided /
  Evidence pending."** No ADR exists in
  [`../04-decisions/`](../04-decisions/) for any AR row.
- **[Decision — existing]** The **no-code gate** holds: no `*.py`/`*.xml`/`*.csv`/
  manifest/module/CI/Docker files; only Markdown governance/documentation is
  writable this phase (`CLAUDE.md` §5, §11).
- **[Recommendation]** This sprint frames **AR-002, AR-003, AR-005** and recommends
  a **decision order** (below) for a **future, ChatGPT-approved** architecture
  sprint. It authorizes nothing.

## 2. MVP inputs from DEC-003 (scope the architecture must serve)

These are **[Decision — existing]** product-scope inputs (the *what*); the *how*
stays gated:

- **Controlled bidirectional product onboarding in MVP** — Shopify→Odoo product
  import **and** Odoo→Shopify controlled product export/update, with product/variant
  **matching before first sync**, an explicit **first-sync source strategy**
  (Shopify-source / Odoo-source / both-match-first), **binding** between Shopify
  product/variant IDs and Odoo records, **SKU/internal-reference + barcode** matching
  (ambiguous → manual review; **no name-only automatic matching**), a
  **duplicate-prevention preview** (no blind create), **draft/unpublished/
  channel-controlled export safety**, and a **preview/dry-run before any
  destructive/full-state write**.
- **Import** for orders, customers (deduped; email primary, multi-key allowed), and
  order status/lifecycle; **write-back** for inventory (multi-location-aware,
  idempotent, never `committed`) and fulfilment + tracking.
- **Reliability spine (MVP-critical):** layered sync (webhooks + scheduled + manual
  + reconciliation); HMAC; webhook-ID dedup; fast ack; idempotency; per-record
  isolation; reason-coded logs; safe manual retry; retry classification concept;
  rate-limit awareness; resumable jobs; honest freshness.
- **Domain 9:** minimal financial **evidence** only (no accounting automation);
  refunds/cancellations/returns **deferred**.
- **Store/company:** single-store, single-company MVP, but **architecture-safe keys**
  (must not block future multi-store; Webkul's default Company field is **not**
  multi-company evidence — DP-004).
- **Bulk Operations** are **not** a user-facing MVP feature; whether they are needed
  **internally** for safe/resumable backfills is an **AR-002** question.
- **Deferred (later, architecture-gated):** unrestricted autonomous bidirectional
  catalog ownership (all-field two-way conflict resolution + field-ownership matrix +
  advanced publish/channel campaign management); customer export.

## 3. Research inputs from Sprint C / C2 (competitor evidence)

Competitor evidence is **[Competitor demonstrated]** or **[Competitor claim]** — it
**informs** the AR rows but **decides nothing** and is **never** promoted to an
official fact (DP-003/DP-004). Consolidated in
[`../01-research/competitor-feature-matrix.md`](../01-research/competitor-feature-matrix.md)
and [`../01-research/competitor-deep-dives.md`](../01-research/competitor-deep-dives.md);
opportunities/anti-patterns in
[`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md) and
[`../01-research/avoid-list.md`](../01-research/avoid-list.md). Highlights per row are
carried into the three deep-framing documents.

## 4. Official-source inputs from the RB-14 refresh

Tier-1 platform facts are **[Official fact]** / **[Official limitation]**, refreshed
in this sprint (access date **2026-07-01**) in
[`rb14-official-source-refresh.md`](./rb14-official-source-refresh.md) and carried in
[`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md)
and
[`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md).
The load-bearing facts (GraphQL-primary / REST-legacy; webhook delivery
not-guaranteed → reconciliation; `@idempotent` on inventory/refund writes from
2026-04; `productSet` delete-on-omit; Odoo core has only `ir.cron`, no async queue)
were **re-verified current** on 2026-07-01.

---

## 5. Active AR rows — framed now vs later

| AR row | Topic | Framed in RB-14 Part 1? | Companion doc | Status |
| --- | --- | --- | --- | --- |
| **AR-002** | Distribution / API strategy (public vs custom app; REST/GraphQL/hybrid; `productSet` destructive-apply; internal bulk; App-Store) | **Yes — deep framing** | [`ar-002-distribution-api-framing.md`](./ar-002-distribution-api-framing.md) | **[Not decided]** |
| **AR-003** | Sync orchestration / queue (`ir.cron` vs OCA `queue_job` vs external worker; webhook+reconciliation; Odoo-Online feasibility) | **Yes — deep framing** | [`ar-003-sync-orchestration-framing.md`](./ar-003-sync-orchestration-framing.md) | **[Not decided]** |
| **AR-004** | Module boundaries / config model (addon family; link modules; feature flags) | **No — later** | — | **[Not decided]** |
| **AR-005** | Binding / dedup / identity data model (dedicated vs generic vs `ir.model.data` vs Shopify-ID-on-record vs hybrid) | **Yes — deep framing** | [`ar-005-binding-dedup-framing.md`](./ar-005-binding-dedup-framing.md) | **[Not decided]** |
| **AR-006** | Error / retry / idempotency taxonomy; reconciliation cadence | **No — later (depends on AR-002/003/005)** | — | **[Not decided]** |
| **AR-007** | Inventory design (quantity field, multi-location, apply mode / auto-apply) | **No — later (depends on AR-002/005)** | — | **[Not decided]** |
| **AR-008** | Fulfilment design (FulfillmentOrder; multi-package/location) | **No — later (depends on AR-002/003/005)** | — | **[Not decided]** |

### Which rows are framed now

- **AR-002, AR-003, AR-005** — because they are the **foundational data-flow
  decisions** the DEC-003 correctness core depends on: *how we talk to Shopify and
  distribute the app* (AR-002), *how we move work reliably and out-of-band* (AR-003),
  and *how we identify records so nothing duplicates or double-writes* (AR-005).

### Which rows remain later

- **AR-006** (error/retry/idempotency taxonomy + reconciliation cadence) — the
  **mechanism** depends on the API surface (AR-002: `@idempotent`, cost model) and
  the queue/orchestration substrate (AR-003) and binding identity (AR-005).
- **AR-007** (inventory design) — depends on the API/apply mechanics (AR-002) and the
  binding identity for `inventory_item_id`+`location_id` (AR-005).
- **AR-008** (fulfilment design) — depends on the API surface (AR-002), the
  orchestration substrate (AR-003), and order/fulfilment binding (AR-005).
- **AR-004** (module boundaries / config model) — **[Recommendation]** should wait
  until enough data-flow decisions are framed/decided, so boundaries are drawn around
  **real** layering (transport / mapping / orchestration / domain / UI) rather than
  guessed; drawing them too early risks the "one giant module" (A-MOD-1) or
  over-fragmentation (A-MOD-2) traps.

## 6. Dependencies between AR rows

- **[Inference]** **AR-002 → everything.** The API choice (GraphQL-primary; REST
  legacy; `productSet` full-state semantics; GraphQL cost model; `@idempotent`
  surface) and the distribution choice (public vs custom → OAuth mandate,
  protected-customer-data levels, App-Store GraphQL-only rule) set the constraints
  every other row inherits.
- **[Inference]** **AR-003 → AR-006, AR-007, AR-008.** Whether work runs on
  `ir.cron`, an internal queue model, OCA `queue_job`, or an external worker
  determines what retry/backoff, reconciliation cadence, inventory-apply, and
  fulfilment orchestration can look like.
- **[Inference]** **AR-005 → AR-006, AR-007, AR-008.** The binding/identity model is
  the substrate for idempotency keys (AR-006), for `inventory_item_id`+`location_id`
  mapping (AR-007), and for order/fulfilment linkage (AR-008). Duplicate-prevention
  and first-sync matching (DEC-003) live here.
- **[Inference]** **AR-002 ↔ AR-005.** `productSet` delete-on-omit (AR-002) makes the
  binding + preview/dry-run (AR-005/DEC-003) a **correctness** requirement, not a
  convenience — full-state writes are unsafe without a reliable binding + diff.
- **[Inference]** **AR-002 ↔ AR-003.** Distribution/hosting choices (public
  App-Store, Odoo Online vs Odoo.sh vs on-prem) constrain the queue/orchestration
  substrate (e.g. whether a `queue_job` Jobrunner or an external worker is even
  installable).
- **[Inference]** **AR-004 depends on all of the above** — module boundaries should
  encode the chosen transport (AR-002), orchestration (AR-003), and binding (AR-005)
  layering.

## 7. Recommended decision order (recommendation, not a decision)

- **[Recommendation]** Decide **AR-002, AR-003, and AR-005 before implementation
  planning** — they are the load-bearing data-flow decisions.
- **[Recommendation]** Sequence: **AR-002 first** (it constrains the others), then
  **AR-003 and AR-005** (which can be framed/decided in parallel once AR-002 sets the
  API/distribution constraints), then **AR-006, AR-007, AR-008** (which depend on
  them).
- **[Recommendation]** **AR-004 (module boundaries) last** among the architecture
  rows — after enough data-flow decisions exist to draw boundaries around real
  layering.
- **[Open question]** Whether AR-002 must be split into two decisions —
  **distribution (public vs custom)** and **API strategy (REST/GraphQL/hybrid)** —
  since the distribution choice materially changes the API constraints (e.g. new
  public apps are GraphQL-only). Raised for ChatGPT; **not** resolved here.

> **This document decides nothing.** It maps the AR rows, records their dependencies,
> and recommends (not decides) a framing/decision order. AR-002, AR-003, and AR-005
> are **framed** (see their companion docs); AR-004/006/007/008 remain **later**. All
> rows stay **[Not decided] / Evidence pending** pending sufficient research and
> **ChatGPT approval** (`CLAUDE.md` §4–§5; RB-14).
