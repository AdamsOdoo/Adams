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
| AR-002 | 2026-06-30 | API strategy: REST vs GraphQL vs hybrid | To be researched / evidence pending — candidates: GraphQL-Admin-only; a REST-where-simpler hybrid; GraphQL + Bulk Operations for backfill | **Accepted by ChatGPT** (2026-07-02 — see note below) | Tier-1: REST is legacy (2024-10-01) and new public apps are GraphQL-only (2025-04-01), but the custom/non-public scope is open (`../01-research/shopify-official-api-notes.md`) | Confirm target distribution (public App Store vs custom app); any REST sunset date; GraphQL coverage gaps for needed resources | REST = dead end for public apps; GraphQL calculated-cost model adds throttling complexity | RB-14 → **accepted** [`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md) (Accepted by ChatGPT, 2026-07-02) | **Accepted** |
| AR-003 | 2026-06-30 | Sync orchestration model | To be researched / evidence pending — candidates: `ir.cron`-only; webhooks + cron reconciliation; OCA `queue_job`-based | **Accepted by ChatGPT** (2026-07-02 — see note below) | Tier-1: Shopify webhook delivery is not guaranteed (reconciliation required); Odoo core has **no** official job queue (only `ir.cron`); `queue_job` is community | Whether to adopt OCA `queue_job` (Jobrunner/dependency cost); cron throughput (`--max-cron-threads`); 5s webhook-ack constraint; competitor patterns (RB-07) | Webhook-only → silent data drift; cron-only → latency/throughput limits; `queue_job` → non-core dependency | RB-14 → **accepted** [`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md) (Accepted by ChatGPT, 2026-07-02) | **Accepted** |
| AR-004 | 2026-06-30 | Module boundaries (addon family) | To be researched / evidence pending — modular connector addon family (transport / mapping / orchestration / domain / UI), link modules for `sale`/`stock`/`account`/`delivery` glue, isolated from `adams_base` | **Not decided** | Odoo docs favour link modules; exact boundaries are **not final** (`CLAUDE.md` §9) | Competitor module decomposition (RB-02); feature taxonomy (RB-12); which Odoo apps must be extended | One-giant-module bias (guarded against) vs over-fragmentation; dependency coupling | RB-14, RB-06 | **Evidence pending** |
| AR-005 | 2026-06-30 | Mapping & duplicate prevention | To be researched / evidence pending — candidates: reuse `ir.model.data` external IDs vs a dedicated per-store binding model (Shopify GID ↔ Odoo `res_id`) | **Accepted by ChatGPT** (2026-07-02 — see note below) | External IDs give an idempotent, db-id-independent handle, but users can delete them and multi-store needs per-store keys (`../01-research/odoo-official-architecture-notes.md`) | `ir.model.data` `(module,name)` uniqueness (open question); Shopify GID stability; competitor dedup approaches | Duplicate records / double-decrement if keys are wrong (cf. `quality-feedback-loop.md` §5); bound-record deletion | RB-14 → **accepted** [`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) (Accepted by ChatGPT, 2026-07-02) | **Accepted** |
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

_**Research Sprint C2 non-decision note (2026-07-01) — NOT decisions; AR rows remain "Not
decided / Evidence pending".** The Sprint C2 TeqStars rebaseline (docs now accessible;
`../01-research/competitor-deep-dives.md`, `competitor-feature-matrix.md`) upgraded TeqStars
from listing-claim-only to **page-classified demonstrated evidence**, which now supplies
**additional competitor inputs** (not resolutions) to several AR rows. For the record only:
**AR-002 (API/distribution)** — the TeqStars docs **state the Shopify GraphQL Admin API** for
sync/webhooks/refunds/cancel/payouts (a vendor doc statement corroborating GraphQL
convergence), and demonstrate a **controlled, draft-safe product export** (Add-to-Listings →
Export Listings with sales-channels-optional = unpublished, Publish/Unpublish, per-listing
Skip-Sync) — a concrete competitor pattern for the DEC-003 controlled-onboarding path, but
**REST/GraphQL/hybrid, distribution (public vs custom), and the `productSet` delete-on-omit /
full-state-write mechanics stay OPEN**. **AR-003 (orchestration/queue)** — TeqStars runs
**webhooks (background-thread fast-ack) + scheduled Automatic Jobs + manual + per-operation
queues** (Product/Customer/Order/Return, Queue Batch Limit 100, **cron-processed — framework
not named**) with a collection background job that "retries in the next run" — a real-world
data point that a **cron-processed per-op queue** (not necessarily OCA `queue_job`) is viable,
alongside VentorTech's `queue_job`; the **`ir.cron` vs `queue_job` choice and Odoo-Online
feasibility stay OPEN**. **AR-005 (binding/dedup)** — TeqStars binds via **Listing / Listing
Item** entities to Odoo products/variants, matches on **"Sync Listings Based On" = SKU /
Barcode / both**, dedups customers on a **multi-field search**, and guards product creation
(Create-Odoo-Products) — corroborating a **dedicated binding model + SKU/barcode match keys +
first-sync guard**, but the `ir.model.data`-reuse-vs-dedicated model, per-store keys, and
deleted-binding handling **stay OPEN**. **AR-006 (error/retry/idempotency)** — TeqStars shows
**adjacent guards only** (refund amount-match, already-cancelled) + typed logs +
Activity-on-failure, but **no explicit `@idempotent` directive, no automatic-retry/backoff
taxonomy, no first-class cross-object reconciliation, and no rate-limit/GraphQL-cost
throttling** (adversarially verified ⬜) — **reinforcing** (not closing) the idempotency +
reconciliation + retry + throttle whitespace that AR-006 must resolve. **AR-007 (inventory)** —
TeqStars demonstrates **multi-location** (export combines multiple locations; third-party
location excluded), **quantity-field choice** (Free-to-Use / On-Hand / Forecasted), and
**controlled apply** (Validate Inventory Adjustment; lot/serial skipped) — corroborating the
AR-007 direction; design **stays OPEN**. **AR-008 (fulfilment)** — TeqStars demonstrates
deliver → **Update in Marketplace** (status + tracking), **click & collect** pickup lifecycle,
and shipped-order import → stock moves — corroborating FulfillmentOrder-era + tracking
write-back; design **stays OPEN**. The rebaseline routes these here as **competitor inputs
only** and re-litigates nothing; **no AR row is decided, accepted, proposed for active review,
or re-litigated.** All remain "Not decided / Evidence pending" pending sufficient research +
ChatGPT approval (`CLAUDE.md` §4–§5; RB-14). No architecture doc, ADR, or implementation plan
was produced. See DP-006's evidence-consistency gate in `defect-pattern-log.md`._

_**RB-14 Architecture Preparation — Part 1 non-decision note (2026-07-01) — NOT decisions; AR
rows remain "Not decided / Evidence pending".** This sprint produced the **first architecture
framing documents** under `../03-architecture/` — an
[`architecture-decision-framing.md`](../03-architecture/architecture-decision-framing.md) map
plus **deep framing** for **AR-002** (distribution/API), **AR-003** (sync orchestration/queue),
and **AR-005** (binding/dedup/identity), backed by a current **official-source refresh**
([`rb14-official-source-refresh.md`](../03-architecture/rb14-official-source-refresh.md), access
date 2026-07-01, ~40 Tier-1 Shopify/Odoo pages re-verified). **These documents FRAME the
decisions and DECIDE none of them.** Explicitly: **no** REST/GraphQL/hybrid choice, **no**
public-vs-custom distribution choice, **no** OAuth-vs-token choice, **no** `ir.cron`-vs-`queue_job`-
vs-external-worker choice, **no** binding data model, **no** module boundaries, **no** data model
— every candidate option is labelled `[Not decided]` with evidence-for/against, risks, UX
implications, and required-evidence-before-decision. **AR-002, AR-003, AR-005 are now FRAMED
(not decided); AR-004, AR-006, AR-007, AR-008 remain NOT framed and NOT decided** (AR-006/007/008
depend on AR-002/003/005; AR-004 module boundaries are recommended to wait until enough data-flow
decisions are framed — a **recommendation, not a decision**). **Official-source refresh completed**
and dated; the load-bearing facts were re-confirmed current with a few **version-sensitive deltas
flagged** (GraphQL `latest` alias now `2026-07`; `@idempotent` on inventory set/adjust
**required as of 2026-04**, optional from 2026-01; `productSet` delete-on-omit is **list-fields-
only**; dual offline-token model). The **Odoo async-queue absence is classified as an [Inference
from official fact]** — the official docs document **only `ir.cron`** for scheduled/background
work and do **not** document a general-purpose async job queue (absence of documentation, not a
positive Official fact; OCA `queue_job` is **community, not core**; confirm against 19.0 source if
load-bearing). **New/sharpened open questions** surfaced for ChatGPT
(custom-vs-public GraphQL mandate; **GID permanence not asserted**; **no general mutation
idempotency** beyond `@idempotent`; `ir.model.data` `(module,name)` uniqueness unconfirmed;
`sudo()` bypass not literally on `security.rst`; **Odoo Online feasibility open**). **DEC-003 and
MVP scope are unchanged; competitor evidence was not promoted to official fact; implementation
remains blocked.** The framing routes everything back here as **inputs**; **no AR row is decided,
accepted, proposed for active review, or re-litigated.** All rows stay "Not decided / Evidence
pending" pending sufficient research + ChatGPT approval (`CLAUDE.md` §4–§5; RB-14). Recommended
decision order (a **recommendation**): decide **AR-002, AR-003, AR-005 before implementation
planning**; **AR-006/007/008 depend on them**; **AR-004 waits**. See DP-006's evidence-
consistency gate in `defect-pattern-log.md`._

_**RB-14 Architecture Preparation — Part 2 non-decision note (2026-07-01) — NOT decisions; AR
rows remain "Not decided / Evidence pending".** This sprint re-checked **only** the high-risk
open questions surfaced by RB-14 Part 1 against **official Shopify docs**, **official Odoo 19.0
docs**, and **official Odoo 19.0 source code** (`odoo/odoo` 19.0), then **narrowed** AR-002/AR-003/
AR-005 into **decision candidates** for ChatGPT — producing
[`rb14-part2-open-question-resolution.md`](../03-architecture/rb14-part2-open-question-resolution.md)
and [`rb14-decision-candidate-brief.md`](../03-architecture/rb14-decision-candidate-brief.md) and
adding RB-14 Part 2 notes to the AR-002/003/005 framing docs + the framing map. **These documents
RESOLVE/NARROW EVIDENCE and DECIDE nothing.** Explicitly: **no** REST/GraphQL/hybrid choice,
**no** public-vs-custom distribution choice, **no** OAuth-vs-token choice, **no** `ir.cron`-vs-
`queue_job`-vs-external-worker choice, **no** binding data model, **no** module boundaries — every
narrowing is labelled `[Recommendation]` / `[Decision candidate]`; **AR-002, AR-003, AR-005 stay
"Not decided / Evidence pending"; AR-004/006/007/008 remain later and not framed.** Evidence
outcomes (facts, not decisions): **resolved from source** — `ir.cron` signatures + failure
constants 3/5/7d (RQ-003-3), `ir.model.data` fields + **`UniqueIndex('(module, name)')`** with no
per-store/audit fields (RQ-005-3), **`sudo()` bypasses access rights AND record rules** (RQ-005-4);
**materially narrowed** — **24-hour** idempotency dedup TTL + fixed **17-mutation** `@idempotent`
set + **no general mutation idempotency/`clientMutationId`** (RQ-005-2), **"Odoo Online is
incompatible with custom modules"** → substrate is Odoo.sh/on-prem (RQ-003-1), custom apps **not
categorically forbidden from REST** with GraphQL the sole long-term API and no REST EOL (RQ-002-1),
protected-data access **"Always available"** for custom apps vs **"Requires review"** for public
with compliance webhooks App-Store-scoped (RQ-002-2), offline token model + 90-day rotating refresh
(RQ-002-3); **re-confirmed open** — **GID permanence not asserted** (RQ-005-1); and for RQ-003-2
the reviewed source confirms `ir.cron` (`[Official source-code fact]`) and that `with_delay` is
absent, while a general async queue was **not found** in the reviewed docs/source (`[Inference]`;
whole-repo absence `[Open question]`; OCA `queue_job` community). **Still-open items
kept open** (custom-app compliance obligations — **not assumed absent**; `@idempotent` key
uniqueness scope; bulk-op idempotency; Odoo.sh/on-prem jobrunner/`server_wide_modules` support;
whole-repo async-queue absence). Candidate carry-forwards (inputs only): **AR-002** custom +
GraphQL-first + offline token; **AR-003** internal cron-queue or `queue_job` (turnkey); **AR-005**
dedicated per-domain or hybrid binding model. **Weak/avoid-candidates were noted but NOT entered in
`rejected-approaches-log.md`** (formal rejection needs ChatGPT, `CLAUDE.md` §10). **DEC-003 and MVP
scope unchanged; competitor evidence was excluded from this official-only pass; implementation
remains blocked.** Recommended next: **RB-14 Part 3 — AR-002 decision sprint, only if ChatGPT
accepts Part 2.** All rows stay "Not decided / Evidence pending" pending ChatGPT approval
(`CLAUDE.md` §4–§5; RB-14). See DP-006's evidence-consistency gate in `defect-pattern-log.md`._

_**Control-Room Reset Sprint 1 note (2026-07-02): no AR-row change; non-decision confirmed.** A
mechanical documentation-residue sweep (`../05-qa/documentation-residue-sweep.md`) ran after PR #58
(RB-14 Part 2) merged — **no research, no fan-out, no new evidence gathered.** It corrected stale
current-truth statements (MVP-not-finalized wording superseded by DEC-003; TeqStars/TQ 403-blocked
wording superseded by the Sprint C2 rebaseline; "Empty" claims in the `04-decisions/` and
`03-architecture/` READMEs) and logged DEC-003's already-decided Option C rejection into
`rejected-approaches-log.md` (RA-001) — **it did not evaluate or reject any new approach.** It also
added (as `[Recommendation — becomes binding when merged by ChatGPT]`) phase-exit criteria and a
documentation-maintenance rule to `quality-feedback-loop.md` §10–§11. **AR-002, AR-003, AR-005 stay
"Not decided / Evidence pending"; AR-004/006/007/008 remain not framed. No AR row changed status.
DEC-003 body untouched; MVP scope unchanged; implementation remains blocked.** Recommended next
(unchanged from the RB-14 Part 2 note above, pending ChatGPT/Fable review of this sweep): **RB-14
Part 3 / Evidence Refresh + Combined AR-002/003/005 Decision Preparation.**_

_**Evidence Refresh + Combined AR-002/003/005 Decision Preparation (2026-07-02) — AR-002, AR-003,
AR-005 move from "Not decided / Evidence pending" to "Proposed for ChatGPT review"; still NOT
accepted.** A small, targeted official-source refresh (Odoo.sh `server_wide_modules`/Jobrunner
silence; Odoo.sh production-cron "best effort" behavior, both new 2026-07-02 facts; OCA
`queue_job` 19.0 community evidence — full record in
[`../03-architecture/ar002-ar003-ar005-evidence-refresh.md`](../03-architecture/ar002-ar003-ar005-evidence-refresh.md))
plus the already-strong RB-14 Part 1/2 evidence base (2026-07-01) produced three **proposed**
decision records: [`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md)
(AR-002 — custom/Admin-created app, GraphQL-first, offline token; public App Store/OAuth/Billing
deferred), [`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md)
(AR-003 — webhook + `ir.cron` + internal queue model as the Phase 1 default substrate on
Odoo.sh/on-prem; OCA `queue_job` deferred/optional, not default), and
[`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md)
(AR-005 — a dedicated/hybrid per-store binding model as the source of truth; `ir.model.data`
rejected as the *primary* mechanism; no name-only matching). **Each DEC file is explicitly
`Status: Proposed for ChatGPT review`, not `Accepted` — this sprint does not self-accept any
decision.** The Status cells for AR-002/AR-003/AR-005 above are updated to **"Proposed for
ChatGPT review"** accordingly; **AR-004/AR-006/AR-007/AR-008 are untouched** (still not framed /
not decided). A small number of options were explicitly proposed-rejected as part of these DEC
files (REST-heavy API, public App Store as a Phase 1 requirement, OCA `queue_job` as the Phase 1
*default*, `ir.model.data` as the *primary* binding mechanism, name-only automatic matching) —
logged in `rejected-approaches-log.md` as **proposed**, pending the same ChatGPT review as the DEC
files themselves (not yet final rejections). **DEC-003 and MVP scope are unchanged; no
implementation is authorized.** Recommended next (pending this review): **ChatGPT/Fable review of
DEC-004/005/006, then a Phase 1 Domain Model + DEC-003 Scope-Hole Closure sprint if accepted.**_

_**DEC-004/005/006 Acceptance Patch (2026-07-02) — AR-002, AR-003, AR-005 move from "Proposed for
ChatGPT review" to "Accepted."** After PR #60 merged into `Shopify-connector` (merge commit
`7eb875e4ca29b80c4745bd8f5354450aa1e4d37b`) and Fable's minor-change review was applied, **ChatGPT
formally accepted** all three proposed decision records:
[`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md)
(AR-002), [`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md)
(AR-003), and [`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md)
(AR-005), each now **`Status: Accepted by ChatGPT`, acceptance date 2026-07-02**. The Review
decision and Status cells for AR-002/AR-003/AR-005 above are updated to **"Accepted by ChatGPT"** /
**"Accepted"** accordingly. The five (now six, with RA-007) proposed-rejection rows tied to these
DEC files (`rejected-approaches-log.md` RA-002–RA-007) **became binding final rejected approaches**
on this same acceptance — see that log's own acceptance note. **AR-004/AR-006/AR-007/AR-008 are
untouched** (still "Not decided / Evidence pending," not framed). **This acceptance decides the
architecture direction for AR-002/003/005 only — it does not by itself authorize implementation.**
DEC-003 and MVP scope remain unchanged; no code, Odoo module, or implementation plan was produced.
Per `../05-qa/quality-feedback-loop.md` §10, AR-002/AR-003/AR-005 acceptance is **one of several**
Phase 1 research-phase-exit criteria (alongside Phase 1 domain-model briefs, a DEC-003 scope-hole
amendment, and a UX/operator-flow sprint) — the implementation gate itself opens only after ChatGPT
separately approves that full exit. Recommended next: **Phase 1 Domain Model + DEC-003 Scope-Hole
Closure sprint.**_

_**Phase 1 Domain Model + DEC-003 Scope-Hole Closure sprint (2026-07-02) — NOT an architecture
decision; AR-006, AR-007, AR-008 remain "Not decided / Evidence pending."** This sprint produced
[`../03-architecture/phase1-domain-model-brief.md`](../03-architecture/phase1-domain-model-brief.md)
(a documentation-level Phase 1 domain-model brief covering store/connection, binding/identity,
product, customer, order/sale, inventory, fulfilment, and queue/log/error concepts) and proposed
[`../04-decisions/DEC-007-phase1-scope-clarifications.md`](../04-decisions/DEC-007-phase1-scope-clarifications.md)
(`Status: Proposed for ChatGPT review`) closing five DEC-003 scope-hole wordings (variant
export/update; image/media and price "where feasible" wording; a first-inventory-push guard;
fulfilment customer-notification default; tax/shipping/discount/payment/order-accounting
treatment). **For the record only, this sprint feeds — and explicitly does not decide — three AR
rows:** **AR-006** (error/retry/idempotency taxonomy) — the domain-model brief names a minimum
job/log concept (source, state, retry count, error class placeholder) per the already-accepted
DEC-005 substrate, but the **full taxonomy stays AR-006, not decided here**; **AR-007** (inventory
architecture) — the proposed first-inventory-push guard is a **scope-level guardrail statement**
(preview + confirmation + mapped location + recorded source-of-truth before the first
Odoo→Shopify write), **not** a quantity-field default, multi-location mechanism, or apply-mode
decision, all of which **stay AR-007, not decided here**; **AR-008** (fulfilment architecture) —
the proposed fulfilment customer-notification default (no notification unless explicitly enabled,
grounded in Shopify's own `FulfillmentInput.notifyCustomer`/`fulfillmentTrackingInfoUpdate`
defaults) is a **scope-level default statement**, **not** a FulfillmentOrder-orchestration or
multi-package/location design, which **stay AR-008, not decided here**. **AR-004** module
boundaries are untouched by this sprint. **No AR row changes status; AR-006/AR-007/AR-008 remain
"Not decided / Evidence pending"; AR-002/AR-003/AR-005 remain "Accepted."** DEC-003 body was not
edited; DEC-004/005/006 were not edited; implementation remains blocked. Recommended next (pending
ChatGPT/Fable review of DEC-007 and the domain-model brief): **Master Blueprint sprint**, and/or a
dedicated **AR-006/AR-007/AR-008 architecture-decision sprint**._
