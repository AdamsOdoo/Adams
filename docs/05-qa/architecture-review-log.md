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

_**Research Sprint C competitor-evidence note (2026-06-30) — NOT decisions; AR
rows remain "Not decided / Evidence pending".** The Sprint C competitor deep
dives, feature matrix, patterns, gaps, and avoid-list now supply **competitor
evidence** that informs (does not resolve) several AR rows. For the record only:
**AR-002 (API)** — every studied connector adopts/positions on **GraphQL**
(VentorTech migrated REST→GraphQL in v2.0.0, Jan 2026), consistent with Tier-1;
the custom-app/distribution choice stays open. **AR-003 (sync orchestration)** —
the market pattern is **webhooks + cron/scheduled + manual** with staging/queues
common; **VentorTech runs on the OCA `queue_job` async queue** (a real-world data
point for the queue dependency question), while cron-only/webhook-less
(ecommerce_shopify) and webhook-only designs risk drift. **AR-005 (mapping/dedup)**
— competitors bind via **SKU/barcode (products) + email (customers) + Shopify-ID
write-back**; none clearly documents bound-record-deletion handling. **AR-006
(error/retry/idempotency)** — **VentorTech ships GraphQL `@idempotent` directives
(Shopify 2026-04) + automatic retry**; others recover manually — corroborating the
idempotency+retry direction; **no competitor describes rate-limit/cost-aware
throttling** (whitespace). **AR-007 (inventory)** — multi-location mapping is
demonstrated (Emipro/VentorTech); single-location (Webkul) and manual
stock-adjustment-on-import (Emipro) are anti-patterns to avoid. **AR-008
(fulfillment)** — FulfillmentOrder-era flows + tracking write-back + multi-package
(Emipro Put-in-Pack) are the norm. **No AR row is decided, accepted, or
re-litigated here.** Avoid-list items tagged "Arch review: YES" are seeded against
these rows and become formal `rejected-approaches-log.md` entries **only after
ChatGPT review**. Evidence: `../01-research/competitor-deep-dives.md`,
`../01-research/gaps-opportunities.md`, `../01-research/avoid-list.md`._

_**Research/Product Sprint D non-decision note (2026-07-01) — NOT decisions; AR
rows remain "Not decided / Evidence pending".** The Sprint D canonical feature
taxonomy (`../02-product/feature-taxonomy.md`) and capability evidence map
(`../02-product/capability-evidence-map.md`) now provide **capability-level
inputs** to the open architecture questions. For the record only, each AR row has
named dependent capabilities: **AR-002 (API/distribution/bulk)** — connection
auth, product/variant/backfill sync, bulk ops, App-Store readiness (distribution
public-vs-custom still open); **AR-003 (sync orchestration/queue)** — webhooks +
reconciliation + scheduled + manual, queue with per-record isolation, auto-workflow,
resumable jobs (`ir.cron` vs OCA `queue_job` still open); **AR-004 (module
boundaries)** — domain-isolated config, mapping/metafield extensibility, feature
flags, transport abstraction (**no module names/boundaries defined**); **AR-005
(binding/dedup)** — Shopify-GID binding model, documented dedup keys, per-store
keys, multi-key customer matching (`ir.model.data` reuse vs dedicated model, and
deleted-binding handling, still open); **AR-006 (error/retry/idempotency)** — retry
classification, automatic retry, idempotency keys, recovery-first error center,
reconciliation; **AR-007 (inventory)** — quantity sync (write `available`/`on_hand`
only), quantity-field choice, multi-location, auto-apply, BoM stock; **AR-008
(fulfillment)** — FulfillmentOrder-based fulfillment, multi-package/location. The
taxonomy classifies these as **inputs/candidates only** and routes them here; **no
AR row is decided, accepted, proposed for active review, or re-litigated.** All
remain "Not decided / Evidence pending" pending sufficient research + ChatGPT
approval (`CLAUDE.md` §4–§5; RB-14). See also DP-005 (`defect-pattern-log.md`) — the
prevention rule that a taxonomy classification is an input, not a decision._

_**Product Sprint E non-decision note (2026-07-01) — NOT decisions; AR rows remain
"Not decided / Evidence pending".** The Sprint E product vision
(`../02-product/product-vision.md`) and setup/UX principles
(`../02-product/setup-ux-principles.md`) now provide **product-intent inputs** to the
open architecture questions — product direction only, never a design choice. For the
record only: **AR-002 (API/distribution)** — the vision states OAuth-first as a strong
but **conditional** direction (mandatory only if public/App-Store distribution is
chosen) and keeps **distribution (public vs custom) and REST/GraphQL/hybrid OPEN**;
**AR-003 (sync orchestration/queue)** — product intent requires webhooks + first-class
reconciliation + scheduled + manual together with out-of-band, resumable processing,
but the **`ir.cron` vs OCA `queue_job` choice and Odoo-Online feasibility stay OPEN**;
**AR-004 (module boundaries)** — a layered, isolated addon family with feature flags
is the direction, **no boundaries/names defined**; **AR-005 (binding/dedup)** —
documented binding + dedup keys and deleted-binding handling are required, **the data
model (`ir.model.data` reuse vs dedicated) stays OPEN**; **AR-006
(error/retry/idempotency)** — idempotency-by-default + recovery-first error center +
retry classification are product non-negotiables, **the error/retry taxonomy and
mechanism stay OPEN**; **AR-007 (inventory)** — multi-location, write
`available`/`on_hand` only, controlled apply (auto-apply is an improvement inference,
DP-006), **design OPEN**; **AR-008 (fulfilment)** — FulfillmentOrder-based +
multi-package/location, **design OPEN**. The vision routes these here as **inputs
only** and re-litigates nothing; **no AR row is decided, accepted, proposed for active
review, or re-litigated.** All remain "Not decided / Evidence pending" pending
sufficient research + ChatGPT approval (`CLAUDE.md` §4–§5; RB-14). See DP-006's
evidence-consistency gate in `defect-pattern-log.md`._

_**Product Sprint F non-decision note (2026-07-01) — NOT decisions; AR rows remain "Not
decided / Evidence pending".** The Sprint F MVP scope proposal (`../02-product/mvp-scope.md`),
non-MVP boundaries (`../02-product/non-mvp-and-later-phases.md`), and user stories
(`../02-product/user-stories.md`) now provide **capability-scope inputs** to the open
architecture questions — MVP *intent/requirements* only, never a design choice. The MVP
proposal commits the **what**, not the **how**, and explicitly maps each
architecture-sensitive capability to its AR row as *Architecture-dependent — must be
resolved in RB-14 before implementation* (`mvp-scope.md` "Architecture-dependent MVP
items"). For the record only: **AR-002 (API/distribution/bulk/App-Store)** — depends
C-CONN-01 (auth style), C-PROD-01/02, C-VAR-01, C-ORD-02, C-JOB-05/06, C-DOCS-04
(distribution public-vs-custom still open; REST/GraphQL/hybrid open); **AR-003 (sync
orchestration/queue)** — depends C-SYNC-01/03/04/06, C-JOB-01/07, C-ORD-01/04, C-DASH
enqueue (`ir.cron` vs OCA `queue_job` still open; Odoo-Online feasibility open); **AR-004
(module boundaries/config/feature flags)** — depends C-MAP-03, C-MULTI-04, feature-flag
visibility (**no module names/boundaries defined**); **AR-005 (binding/dedup)** — depends
C-MAP-01/02, C-CUST-03, C-PROD-01, C-MULTI-01 multi-store-safe keys (`ir.model.data`
reuse vs dedicated model, and deleted-binding handling, still open); **AR-006
(error/retry/idempotency)** — depends C-JOB-02/03/04, C-OBS-03, C-DASH-04, C-SYNC-06
(taxonomy, idempotency mechanism, reconciliation cadence open); **AR-007 (inventory)** —
depends C-INV-01/02/03/04 (fields, multi-location, **auto-apply-vs-review** open — DP-006);
**AR-008 (fulfilment)** — depends C-FUL-01/02 (FulfillmentOrder, multi-package/location
open). The proposal routes these here as **inputs only** and re-litigates nothing; **no
AR row is decided, accepted, proposed for active review, or re-litigated.** All remain
"Not decided / Evidence pending" pending sufficient research + ChatGPT approval
(`CLAUDE.md` §4–§5; RB-14). See DP-006's evidence-consistency gate in
`defect-pattern-log.md`._

_**Product Sprint G non-decision note (2026-07-01) — NOT an architecture decision; AR rows
remain "Not decided / Evidence pending".** ChatGPT accepted the **MVP product scope**
baseline in [`../04-decisions/DEC-003-mvp-scope.md`](../04-decisions/DEC-003-mvp-scope.md)
(RB-13). **DEC-003 is a product-scope decision, not an architecture decision:** it fixes the
MVP *what* (Option A correctness-core **with controlled bidirectional product onboarding**
— product import **and** controlled export/update; import + inventory/fulfilment write-back;
Domain 9 minimal financial **evidence** only, no accounting automation; refunds/cancellations
deferred; bulk ops **not a user-facing feature**; single-store/single-company with
multi-store-safe keys; P1-primary/P2-secondary) and **feeds AR-002…AR-008 as scope inputs**,
but **decides, accepts, proposes-for-active-review, and re-litigates no AR row.** Specifically
still open: **AR-002** distribution/API strategy — and whether Shopify **Bulk Operations are
required internally** for safe/resumable backfills (an architecture mechanism, not a
product-scope expansion); **AR-003** orchestration/queue framework + Odoo-Online feasibility;
**AR-004** module boundaries/config model; **AR-005** binding/dedup data model + per-store keys
+ deleted-binding handling; **AR-006** error/retry taxonomy + idempotency mechanism +
reconciliation cadence; **AR-007** inventory design incl. **apply mode (auto-apply vs
review)**; **AR-008** fulfilment design. Additionally, the **Domain 9 draft-artifact
exception** (whether a draft invoice/payment artifact is absolutely required for a valid Odoo
order flow) is **architecture-dependent** and must **return to ChatGPT before
implementation** — no silent automatic invoice/payment creation. All rows remain "Not decided
/ Evidence pending" pending sufficient research + ChatGPT approval (`CLAUDE.md` §4–§5; RB-14).
See DP-006's evidence-consistency gate in `defect-pattern-log.md`._

_**Product Sprint G revision non-decision note (2026-07-01, PR #55 review) — NOT an
architecture decision; AR rows remain "Not decided / Evidence pending".** ChatGPT corrected
DEC-003 to include **controlled bidirectional product onboarding** in MVP (controlled product
export/update, with matching, binding, preview/dry-run, and draft/unpublished/channel-controlled
safety). This adds **product-scope inputs** to two AR rows without deciding them: **AR-002**
now also carries the **destructive-apply / full-state-write mechanics** (`productSet`
delete-on-omit) that the controlled export path must guard, plus the API-strategy dependency;
**AR-005** now also carries **product export/import matching + binding + the first-sync source
strategy** (Shopify-source / Odoo-source / both-match-first) and the **product match-key set**
(SKU/internal-reference, barcode). **Full autonomous bidirectional catalog management** —
automatic all-field two-way conflict resolution, a complex field-ownership matrix, and advanced
publish/channel campaign management — **remains later and architecture-gated** (a future
field-ownership + conflict-resolution design must be reviewed and accepted before inclusion).
**No AR row is decided, accepted, proposed for active review, or re-litigated.** All remain
"Not decided / Evidence pending" (`CLAUDE.md` §4–§5; RB-14). NB: **TeqStars** documentation,
recorded 403-blocked in Sprint C, was **re-checked accessible on 2026-07-01**; a **full
TeqStars rebaseline is pending a later research sprint** — it does not change any AR row here._
