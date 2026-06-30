# Architecture Review Log

> Tracks architecture discussions **before** they become finalized decision
> records. An entry here is a proposal under review (typically reviewed by
> ChatGPT), not a commitment. Accepted proposals are promoted to an ADR in
> [`../04-decisions/`](../04-decisions/) and linked back here.

## How to use

1. Add a row when an architectural approach is proposed or debated.
2. **Review decision** vocabulary: `accepted` / `accepted with minor
   corrections` / `revise` / `reject`.
   - `reject` → also log in
     [`rejected-approaches-log.md`](./rejected-approaches-log.md).
   - `accepted` → create an ADR (`../04-decisions/`) and put the link in
     **Follow-up action**.
3. **Evidence required** must name concrete proof needed (a Shopify/Odoo
   capability, a competitor behaviour, a benchmark) before acceptance. Do not
   accept while required evidence is missing.
4. **Status** values: `Proposed`, `Under review`, `Evidence pending`,
   `Accepted → ADR`, `Rejected`, `Deferred`.

> Read this log **before finalizing any design** so prior outcomes are not
> re-litigated or contradicted.

---

## Log

| ID | Date | Topic | Proposed approach | Review decision | Reason | Evidence required | Risks | Follow-up action | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _AR-000_ | _YYYY-MM-DD_ | _e.g. Sync orchestration model_ | _Short description_ | _accepted/revise/reject_ | _Why_ | _Proof needed_ | _Key risks_ | _ADR link / next step_ | _Proposed_ |
| AR-001 | 2026-06-30 | Governance foundation branch | Use the Research Sprint A branch (`docs/research-sprint-a-governance-inventory`) as the canonical governance foundation | Accepted after revision patch | It defers active skills/agents and preserves the no-code, research-first gate | n/a — governance/process decision | Branch divergence if the earlier `claude/odoo-shopify-research-setup-fs4wzi` branch is reused | Do not continue from the old branch; treat it as non-canonical unless ChatGPT explicitly reopens it | Accepted |
| AR-002 | 2026-06-30 | API strategy: REST vs GraphQL vs hybrid | To be researched / evidence pending — candidates: GraphQL-Admin-only; a REST-where-simpler hybrid; GraphQL + Bulk Operations for backfill | **Not decided** | Tier-1: REST is legacy (2024-10-01) and new public apps are GraphQL-only (2025-04-01), but the custom/non-public scope is open (`../01-research/shopify-official-api-notes.md`) | Confirm target distribution (public App Store vs custom app); any REST sunset date; GraphQL coverage gaps for needed resources | REST = dead end for public apps; GraphQL calculated-cost model adds throttling complexity | RB-14; resolve distribution model with ChatGPT before deciding | **Evidence pending** |
| AR-003 | 2026-06-30 | Sync orchestration model | To be researched / evidence pending — candidates: `ir.cron`-only; webhooks + cron reconciliation; OCA `queue_job`-based | **Not decided** | Tier-1: Shopify webhook delivery is not guaranteed (reconciliation required); Odoo core has **no** official job queue (only `ir.cron`); `queue_job` is community | Whether to adopt OCA `queue_job` (Jobrunner/dependency cost); cron throughput (`--max-cron-threads`); 5s webhook-ack constraint; competitor patterns (RB-07) | Webhook-only → silent data drift; cron-only → latency/throughput limits; `queue_job` → non-core dependency | RB-14; RB-07 common patterns | **Evidence pending** |
| AR-004 | 2026-06-30 | Module boundaries (addon family) | To be researched / evidence pending — modular connector addon family (transport / mapping / orchestration / domain / UI), link modules for `sale`/`stock`/`account`/`delivery` glue, isolated from `adams_base` | **Not decided** | Odoo docs favour link modules; exact boundaries are **not final** (`CLAUDE.md` §9) | Competitor module decomposition (RB-02); feature taxonomy (RB-12); which Odoo apps must be extended | One-giant-module bias (guarded against) vs over-fragmentation; dependency coupling | RB-14, RB-06 | **Evidence pending** |
| AR-005 | 2026-06-30 | Mapping & duplicate prevention | To be researched / evidence pending — candidates: reuse `ir.model.data` external IDs vs a dedicated per-store binding model (Shopify GID ↔ Odoo `res_id`) | **Not decided** | External IDs give an idempotent, db-id-independent handle, but users can delete them and multi-store needs per-store keys (`../01-research/odoo-official-architecture-notes.md`) | `ir.model.data` `(module,name)` uniqueness (open question); Shopify GID stability; competitor dedup approaches | Duplicate records / double-decrement if keys are wrong (cf. `quality-feedback-loop.md` §5); bound-record deletion | RB-14 | **Evidence pending** |
| AR-006 | 2026-06-30 | Error handling & retries | To be researched / evidence pending — per-record retry/backoff, idempotency keys, partial-failure isolation (savepoints), dead-letter handling | **Not decided** | `ir.cron` auto-deactivates after repeated failures; Shopify returns 429/throttle and requires `@idempotent` on some mutations (2026-04) | Shopify idempotency surface + Retry-After semantics; Odoo savepoint/exception handling in cron; competitor recovery (RB-09 reliability) | Missing retry → lost syncs; naive retry → duplicates / rate-limit storms | RB-14 | **Evidence pending** |
| AR-007 | 2026-06-30 | Inventory architecture | To be researched / evidence pending — map Odoo stock (product / location / quants) ↔ Shopify InventoryItem / InventoryLevel / Location; write only `available`/`on_hand` | **Not decided** | Tier-1: Shopify `committed` is API-read-only (order-driven), `on_hand` is a sum, set/adjust need `@idempotent` (2026-04), multi-location mapping required | Odoo multi-warehouse/location → Shopify location mapping; sync direction & conflict policy; competitor inventory handling | Double-decrement of multi-location SKUs; attempting to write `committed`; over/under-sell on drift | RB-14; future Odoo `stock` deep dive | **Evidence pending** |
| AR-008 | 2026-06-30 | Fulfillment architecture | To be researched / evidence pending — drive fulfillment via FulfillmentOrder-based mutations; map Odoo delivery/`stock.picking` → Shopify fulfillment + tracking | **Not decided** | Tier-1: legacy Order/Fulfillment workflow unsupported since 2022-07; one fulfillment per order + location; tracking via `fulfillmentTrackingInfoUpdate` | Odoo delivery/carrier tracking model; per-location fulfillment split; whether the connector acts as a fulfillment service; competitor tracking write-back | Using legacy fulfillment endpoints; multi-location mismatch; tracking-URL generation | RB-14 | **Evidence pending** |

_AR-001 is a governance/process decision (not a product-architecture choice);
it is recorded here because it concerns the canonical foundation all later
architecture work builds on._

_**AR-002 … AR-008** were seeded in **Research Sprint B** as **evidence-pending
research questions only** — every one has Review decision **"Not decided"** and
Status **"Evidence pending."** They are **not proposals under active review and
not decisions**; they exist so the open architecture questions implied by the
Tier-1 Shopify/Odoo baselines are tracked and not forgotten. No design may be
accepted while its **Evidence required** is missing, and any acceptance must
route through this log and (when accepted) an ADR in `../04-decisions/`. All
architecture work remains gated until research is sufficient and ChatGPT
approves (see `CLAUDE.md` §4–§5; backlog item RB-14)._
