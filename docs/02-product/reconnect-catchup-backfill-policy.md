# Reconnect, Catch-Up & Backfill Policy — Per-Domain Recovery After Disconnection

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** This document
> closes gap P-7 of
> [`../01-research/mvp-remaining-gap-inventory.md`](../01-research/mvp-remaining-gap-inventory.md)
> (reconnect/catch-up/backfill under-specified per domain). Acceptance
> authority: product owner + Claude control room. No implementation
> authorized. Claims are labelled per CLAUDE.md §8; Shopify platform facts
> cite the 2026-07-16 capture
> [`../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md`](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md).

---

## 1. Purpose and binding direction

[Proposed product decision — PD-RB-1] Disconnect/reconnect must **never
blindly replay old jobs**. Reconnect is a controlled re-entry: verify the
connection, recognize a new connection generation, preserve — but do not
execute — historic work, and start **fresh domain scans** that catch up on
what was missed, deduplicating against what already exists. Order history
beyond the automatic catch-up window is imported only through an
**Administrator-controlled manual backfill with a preview**, never
automatically.

Companion documents: Flow 2 and Flow 9 of
[`mvp-user-flows-and-state-models.md`](mvp-user-flows-and-state-models.md)
(reconnect UX skeleton), the fulfillment operating-modes policy
([`fulfillment-operating-modes.md`](fulfillment-operating-modes.md)) and COD
lifecycle ([`cod-lifecycle-and-reconciliation.md`](cod-lifecycle-and-reconciliation.md))
for disconnected-period event handling, and
[`../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md`](../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md)
for mutation replay safety.

## 2. Reconnect sequence design (the eight steps)

Most of this sequence already exists in shipped core code; the new elements
are the per-domain watermark records (§3) and the fresh-scan mandate (step 8).

| # | Step | Status |
|---|---|---|
| 1 | **Verify credentials.** `action_reconnect` runs the connection probe before any state change. | [Fact — repo, verified 2026-07-16] Existing. |
| 2 | **Verify Shopify scopes.** Granted scopes are mirrored on the store (`granted_scopes`) and checked by readiness. | [Fact — repo] Existing mirrors; [Recommendation] reconnect must diff granted vs required scopes per enabled domain and surface any loss (e.g. a token re-issued without `read_all_orders`) before declaring `connected`. |
| 3 | **Verify API version.** The store mirrors `api_version`; the connector pins 2026-07 and must detect Shopify's silent "fall forward" to another version ([Fact] capture §11). | [Fact — repo] mirror exists; [Recommendation] readiness check compares mirrored vs pinned version. |
| 4 | **Re-run readiness.** The readiness registry re-runs all checks on reconnect. | [Fact — repo] Existing. |
| 5 | **Create/recognize a new connection generation.** `connection_generation` is a monotonic epoch bumped on activate, reconnect success, disconnect request, and connected-credential mutation. | [Fact — repo] Existing. |
| 6 | **Preserve historic jobs as evidence.** Jobs from prior generations are preserved via the `historic_domain_job` sink — audit trail, never an execution queue. | [Fact — repo] Existing. |
| 7 | **Prevent stale-generation execution.** Jobs capture `expected_connection_generation` at enqueue; admission refuses stale-generation jobs. `action_reconnect` itself refuses to complete if the epoch changed mid-flight. | [Fact — repo] Existing. |
| 8 | **Start fresh domain scans.** For each enabled domain, enqueue a *new* catch-up scan job (new generation) using that domain's watermark + overlap strategy (§3–§4). | [Proposed product decision — PD-RB-2] New behavior; nothing in steps 1–7 replays content — step 8 is the only source of post-reconnect work. |

[Proposed product decision — PD-RB-3] Store lifecycle states remain exactly
the shipped set (`setup_incomplete` / `connected` / `reconnect_needed` /
`disconnecting` / `disconnected` — [Fact — repo]); catch-up introduces **no
new store state**. Catch-up progress is job/domain-level status, not a
lifecycle state.

## 3. Watermark model

### 3.1 Watermark record

[Proposed product decision — PD-RB-4] One watermark record per **store ×
domain**, with:

- `domain` — products / customers / orders / inventory / fulfillment /
  product_export / abandoned_checkouts (if enabled).
- `last_successful_scan_at` — UTC timestamp of the newest **remote
  `updatedAt`** fully covered by the last *successful, completed* scan.
  Advanced only when a scan completes without unrecovered errors; a partial
  or failed scan never advances it.
- `overlap_window` — per-domain duration subtracted from the watermark when
  building the next scan's `updated_at:>` filter.
- Pagination posture — cursors are **never persisted** across jobs
  ([Fact — repo] accepted posture ARCH PD-5 in
  [`../07-implementation-plan/task-012-order-import-implementation-packet.md`](../07-implementation-plan/task-012-order-import-implementation-packet.md):
  `sortKey: UPDATED_AT`, `updated_at:>watermark−overlap`, bounded page size,
  cursors live only inside a single job run). Watermarks are timestamps, not
  cursors; a crashed scan restarts from the timestamp filter, and dedup (§3.4)
  absorbs the re-read.

[Inference] Timestamp watermarks + in-run cursors are the only crash-safe
combination given Shopify's cursor semantics: a persisted cursor is tied to a
specific query execution and sort order, whereas an `updated_at` filter is
re-derivable at any time.

### 3.2 Overlap window default

[Recommendation] Default `overlap_window` = **30 minutes** for all domains
(configurable per domain within 15–60 minutes; technical setting, not exposed
to Connector Users).

Justification: [Fact] Shopify states webhook "delivery isn't always
guaranteed", ordering is not guaranteed within or across topics, and apps
"shouldn't rely on receiving data from Shopify webhooks" — reconciliation
jobs are the mandated safety net (capture §7). [Inference] The overlap must
cover (a) clock skew between the connector and Shopify, (b) the gap between
a record's `updatedAt` and its visibility in query results, and (c) the
window between "scan started" and "watermark timestamp computed". Minutes,
not seconds, of tolerance are required; hours would only inflate re-read
volume that dedup then discards. 30 minutes is a defensible midpoint; UAT
(§9) validates it. [Open question — OQ-RB-1] No official Shopify figure
exists for query-visibility lag; the default is engineering judgment and
must be tunable.

### 3.3 Idempotent enqueue

[Fact — repo] The job substrate already provides `idempotency_key` /
`operation_scope_key` enqueue dedup. [Proposed product decision — PD-RB-5]
Catch-up uses it in two layers:

1. **Scan jobs**: one active scan per store × domain — scope key
   `catchup:{store}:{domain}:{generation}`; re-triggering while a scan is
   active is a no-op (active-job dedup).
2. **Per-record jobs** fanned out by a scan: idempotency key includes store,
   domain, remote GID, and the remote `updatedAt` observed by the scan — the
   same observed version is never enqueued twice, while a newer version is.

### 3.4 Skip logic (exact)

[Proposed product decision — PD-RB-6] For each remote record returned by a
catch-up scan, in order:

1. **No binding exists** → enqueue import/review per the domain's normal
   inbound rules → counted **new**.
2. **Binding exists AND remote `updatedAt` ≤ binding's recorded last-synced
   remote `updatedAt`** → **skip** (no job). This is the common case inside
   the overlap window.
3. **Binding exists AND remote `updatedAt` is newer**:
   a. Where a payload/version hash of the last-applied remote snapshot is
      stored (products, customers), recompute the hash of the relevant
      fetched fields; **equal hash → skip** (touch-only update), record the
      new `updatedAt` on the binding. [Inference] `updatedAt` moves on
      changes the connector does not map (e.g. metafields), so hash
      comparison prevents no-op job churn.
   b. Hash differs, or no snapshot hash exists for the domain → enqueue an
      update job → counted **changed**.
4. **Ambiguity** (conflicting candidate bindings, identity fields changed,
   locally modified counterpart since disconnect) → **manual review case**,
   never an automatic write → counted **needs-review**.

## 4. Per-domain catch-up strategies

Shared query posture for all Shopify-side scans [Fact — capture §3]: filtered
query `updated_at:>{watermark − overlap}` with `sortKey: UPDATED_AT` where the
domain query supports it, cursor pagination via
`pageInfo { hasNextPage endCursor }`, throttle-aware paging (cost-based leaky
bucket, `THROTTLED` + `throttleStatus` backoff — capture §11).

### 4.1 Products (import)

- **Scan**: `products` query, `query: "updated_at:>…"`.
- **Watermark semantics**: newest product `updatedAt` fully processed.
- **Dedup keys**: product/variant bindings (GID-based per DEC-006); variant
  identity via existing binding + SKU rules; payload hash per §3.4.3a.
- **Review triggers**: variant set restructured while disconnected (variants
  deleted/re-created with new GIDs), duplicate-SKU collisions, product
  deleted remotely (absence is *not* detected by an `updated_at` scan —
  [Inference] deletions surface via webhooks or full reconciliation passes,
  logged as [Open question — OQ-RB-2] cadence of full-list reconciliation).
- **Must NOT happen**: catch-up never mutates Shopify; product import is
  read-only into staging/bindings.

### 4.2 Customers

- **Scan**: `customers` query with `updated_at:>` filter.
- **Watermark semantics**: as §3.1.
- **Dedup keys**: customer binding (GID); email/phone matching per Task-011
  matching rules only for unbound records.
- **Review triggers**: unbound remote customer matching multiple Odoo
  partners; email/phone changed on a bound customer that also changed
  locally. [Fact — capture §12] name/address/email/phone are protected
  customer data — review queues must respect the redaction posture.
- **Must NOT happen**: no automatic partner merges; `mergeable`/merge events
  from the disconnected period always route to review.

### 4.3 Orders

- **Scan**: `orders` query, `query: "updated_at:>{watermark − overlap}"`,
  `sortKey: UPDATED_AT` posture per ARCH PD-5, plus the store's eligibility
  filters (e.g. `status`, `financial_status`, `test:false`) from the order
  policy ([`sales-order-lifecycle-and-confirmation-policy.md`](sales-order-lifecycle-and-confirmation-policy.md)).
  [Fact — capture §3] all listed filters verified on the 2026-07 `orders`
  query page.
- **Automatic catch-up scope** [Proposed product decision — PD-RB-7]:
  every **missing or changed eligible order since the last successful
  watermark minus overlap** is caught up automatically. The connector does
  **NOT** auto-import all historic lifetime orders on reconnect — anything
  older than the watermark window is manual backfill only (§5).
- **Watermark semantics**: `updatedAt`-based, so order **edits**, cancels,
  refunds, and financial-state changes made while disconnected re-enter as
  *changed* records ([Fact — capture §3] edits fire `orders/edited` and move
  `updatedAt`; line items and totals are mutable post-import).
- **Dedup keys**: order binding by GID (primary), Shopify order name/number
  as secondary guard; per-record idempotency key per §3.3.
- **Review triggers**: changed order whose Odoo counterpart progressed
  (confirmed/invoiced/delivered) in ways the update cannot safely apply;
  eligible order referencing an unbound/ambiguous customer; COD orders whose
  collection state diverged — route per COD scenarios in
  [`cod-lifecycle-and-reconciliation.md`](cod-lifecycle-and-reconciliation.md).
- **Access limitation (must be represented honestly)** [Fact — capture §4]:
  only the **last 60 days** of orders are accessible from the Order object
  by default; older orders require **`read_all_orders`** combined with
  `read_orders`/`write_orders`, granted only after a Partner-Dashboard
  request and **Shopify approval**. [Inference] If a store was disconnected
  for more than ~60 days and lacks `read_all_orders`, part of the catch-up
  window itself is unreachable — the connector must detect this (watermark
  older than 60 days + scope absent) and surface it as a warning with the
  backfill/approval path, never silently report a complete catch-up.
- **Must NOT happen**: no automatic full-history import; no re-import of
  orders already bound (dedup, not duplicate sale orders); no automatic
  confirmation-policy bypass for caught-up orders.

### 4.4 Inventory

- **Scan**: reconciliation **read** of `InventoryLevel.quantities` for
  mapped item×location pairs (capture §9), driven from the binding set
  rather than an `updated_at` query. [Open question — OQ-RB-3] Whether an
  efficient changed-since filter exists for inventory levels in 2026-07 —
  not captured; default design is a bounded full reconciliation read of
  mapped pairs.
- **Watermark semantics**: `last_successful_scan_at` = completion time of
  the last full reconciliation read (freshness marker, not a filter).
- **Dedup keys**: item×location binding; export-side pushes carry the
  mandatory `@idempotent` UUID key ([Fact — capture §9], 24 h retention).
- **Must NOT happen — no blind push after reconnect.** Any pre-disconnect
  computed quantities are stale. The first post-reconnect inventory action
  is always a **reconciliation read**; only then may pushes resume, using
  `inventorySetQuantities` with `compareQuantity` optimistic concurrency
  ([Fact — capture §9]) so a concurrent remote change fails closed. This is
  a DEC-031 **Layer 2** consumer: inventory mutation resumption after
  reconnect is gated on the accepted Layer 2 design
  ([`../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md`](../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md)).
- **Review triggers**: negative/implausible remote quantities; unmapped
  locations that appeared while disconnected; per
  [`inventory-operating-model.md`](inventory-operating-model.md).

### 4.5 Fulfillment (+ tracking events)

- **Scan**: per open bound order, re-read `fulfillmentOrders` (status,
  requestStatus, holds, assigned location) and `fulfillments`
  (status, `trackingInfo`, `events`) — [Fact — capture §6] full state
  families verified 2026-07-16. Orders-domain catch-up (§4.3) already
  surfaces orders whose fulfillment changed (fulfillments move order
  `updatedAt`); the fulfillment scan is scoped to bound orders with open
  Odoo pickings plus orders flagged by §4.3.
- **Watermark semantics**: freshness marker per §4.4; tracking events are
  read via `Fulfillment.events` and deduped by event identity + status +
  `happenedAt`.
- **Dedup keys**: fulfillment GID ledger — [Fact — capture §6.6] the
  Fulfillment object has **no app-attribution field**, so the connector's
  own durable ledger of fulfillment GIDs returned by its `fulfillmentCreate`
  calls is the primary self/external discriminator (secondary:
  `service.handle`, order-event attribution).
- **Must NOT happen — no blind `fulfillmentCreate` replay.**
  [Fact — capture §6.5] `fulfillmentCreate` documents **no idempotency
  key**; a replay creates a duplicate fulfillment. Before any queued
  outbound fulfillment executes after reconnect, the handler must re-read
  the FO line-item **remaining quantities** and skip/shrink accordingly
  (DEC-031 Layer 2 reconciliation-read pattern). Stale-generation
  fulfillment jobs are already refused at admission ([Fact — repo]); new
  ones are created only from current Odoo picking state.
- **Review triggers**: external fulfillments created while disconnected
  (Mode-dependent — see [`fulfillment-operating-modes.md`](fulfillment-operating-modes.md));
  FO moved/split/merged so that a pending Odoo picking no longer maps
  cleanly; holds added by other apps ([Fact — capture §6.2] multiple apps
  can hold the same FO).

### 4.6 Product export reconciliation

- **Scan**: for each Odoo product marked exported/pending-export, re-read
  the bound Shopify product (or resolve by `productSet` identifier where a
  binding is incomplete) and compare against the stored exported-state
  snapshot/hash.
- **Must NOT happen — no resumed export writes before an exported-state
  verification read.** [Inference] Shopify-side edits during disconnection
  would otherwise be silently overwritten — worse under `productSet`'s
  declarative list semantics, which **delete list entries omitted from the
  input** ([Fact — capture §10]). Divergence between "what we last wrote"
  and "what is there now" routes to review (ownership/overwrite policy in
  [`product-export-operating-model.md`](product-export-operating-model.md));
  identical state resumes normally.
- **Dedup keys**: product binding + exported-payload hash; `productSet`
  upsert-by-identifier prevents duplicate product creation on retry
  ([Fact — capture §10]).

### 4.7 Abandoned checkouts (only if the optional feature is enabled)

- **Scan**: `abandonedCheckouts` query with `updated_at`/`created_at`
  filters, `recovery_state`, `status` ([Fact — capture §5]).
- **Watermark semantics**: standard §3.1.
- **Must NOT happen**: no quotation creation by default; conversion linking
  keys on the resulting **Order** (webhook/scan), never on checkout-to-order
  correlation heuristics ([Fact/Inference — capture §5]). Policy:
  [`abandoned-checkout-policy.md`](abandoned-checkout-policy.md). PCD
  handling applies ([Fact — capture §5]).

## 5. Order backfill (Administrator-controlled, preview-first)

[Proposed product decision — PD-RB-8] Historic order import beyond the
automatic catch-up window is exclusively a **manual backfill wizard**,
restricted to the Connector Administrator role
([`connector-roles-and-permissions.md`](connector-roles-and-permissions.md)).

1. **Inputs**: date range (created_at or updated_at basis — default
   `created_at`), optional filters mirroring the eligibility policy
   (`financial_status`, `status`, `fulfillment_status`, exclude `test:true`)
   — all verified query filters ([Fact — capture §3]).
2. **Access-window honesty** [Fact — capture §4]: if the requested range
   extends beyond 60 days and the token lacks `read_all_orders`, the wizard
   states this **before scanning**, shows the reachable sub-range, and links
   the approval path (Partner Dashboard → API access → "Read all orders" →
   request with justification → Shopify approval). It never silently
   truncates.
3. **Preview before enqueue** (mandatory): a **read-only scan** of the range
   computes counts — **new / changed / duplicate / skipped / needs-review** —
   using exactly the §3.4 skip logic, creating **no jobs and no records**.
   The Administrator sees the counts (and samples) and explicitly confirms
   before anything is enqueued.
4. **Enqueue**: confirmed backfill enqueues per-record jobs with §3.3
   idempotency keys, tagged with a backfill batch id and the current
   connection generation.
5. **Throttle-aware batching**: paging respects the cost-based rate limit
   with `throttleStatus`-driven backoff ([Fact — capture §11]); batch size
   bounded; backfill runs at lower priority than live sync.
6. **Resumability**: batch progress is tracked per page-window of the date
   range; an interrupted backfill resumes from the last completed window,
   and re-scanned records are absorbed by dedup. A backfill interrupted by
   disconnect is generation-fenced like any job and must be re-confirmed
   (fresh preview) after reconnect. [Recommendation]
7. **Backfilled orders obey the same confirmation policy and COD rules** as
   live imports — backfill is an ingestion path, not a policy bypass.

## 6. Onboarding initial-import windows

[Proposed product decision — PD-RB-9] Initial activation offers controlled
import windows per domain, subject to the same Shopify access rules:

| Domain | Default | Options |
|---|---|---|
| Products | Full catalog | Full / none (export-first stores) |
| Customers | Full | Full / none / with-orders-only [Open question — OQ-RB-4: exact option set for MVP] |
| Orders | **Recent 30 days** | Recent N days (≤60 without `read_all_orders`) / custom range (>60 days requires approved `read_all_orders`; wizard honesty per §5.2) / none |
| Inventory | Baseline reconciliation read at activation | per [`inventory-operating-model.md`](inventory-operating-model.md) |
| Fulfillment/tracking | Only for imported orders | — |
| Abandoned checkouts | None (feature off by default) | window selectable when enabled |

After the initial import completes, each domain's watermark is seeded to the
scan completion posture (§3.1), and normal incremental sync takes over.

## 7. Disconnected-period events

[Inference] Nothing special "replays" the disconnected period: externally
changed orders, fulfillments, refunds, and COD collection events that
occurred while disconnected simply **land via catch-up as normal updates or
review cases**, because the `updated_at` scan window spans the disconnection.
Concretely: an order edited and fulfilled externally while disconnected
arrives as one *changed* record; the fulfillment scan classifies the external
fulfillment per the operating mode
([`fulfillment-operating-modes.md`](fulfillment-operating-modes.md)); a COD
order collected-and-refunded while disconnected follows the corresponding COD
scenario (see scenario 16 — disconnected-period COD divergence — in
[`cod-lifecycle-and-reconciliation.md`](cod-lifecycle-and-reconciliation.md)).
Webhooks missed during disconnection are irrelevant by design — the
reconciliation-first posture ([Fact — capture §7]) makes the scan the source
of truth.

## 8. UX summary

[Recommendation — visuals deferred to the premium UX specification
([`premium-ux-master-specification.md`](premium-ux-master-specification.md))
and prototype (`../09-ui-prototype/`)]:

- **Reconnect status**: Flow 2/9 banner language (reassurance-first: settings,
  mappings, history preserved — [Fact — repo] Flow 2 "Premium UX treatment"),
  extended with a post-reconnect "Catching up…" phase showing per-domain
  progress (scanned / new / changed / skipped / needs-review counts).
- **Catch-up progress**: per-domain rows with counts and a link to the
  review queue; completion marked per domain, with an explicit warning state
  for the >60-day unreachable-window case (§4.3).
- **Backfill preview screen**: date-range + filters form, access-window
  notice, count summary (new / changed / duplicate / skipped / needs-review),
  sample records, explicit confirm; visible to Connector Administrators only.

## 9. Test / UAT hooks

Acceptance scenarios for this policy (watermark advance/hold-back, overlap
dedup, stale-generation refusal, 60-day boundary honesty, preview-count
accuracy, no-blind-push proofs for inventory/fulfillment/export, resumable
backfill) are enumerated in
[`../05-qa/reconnect-backfill-uat-matrix.md`](../05-qa/reconnect-backfill-uat-matrix.md)
(companion deliverable of this mission). Each per-domain "must NOT happen"
in §4 must have at least one negative UAT case.

## 10. Wave allocation

Per [`../07-implementation-plan/mvp-completion-program.md`](../07-implementation-plan/mvp-completion-program.md):

| Scope | Wave |
|---|---|
| Order catch-up scan + manual backfill wizard/preview | **Wave 2** |
| Inventory reconciliation-read catch-up (no-blind-push) | **Wave 3** |
| Fulfillment/tracking catch-up + external-fulfillment review | **Wave 4** |
| Product-export reconciliation on reconnect | **Wave 5** |
| Watermark substrate + generic scan-job pattern | earliest consuming wave (Wave 2), designed once [Recommendation] |

## 11. Proposed decisions and open questions

**Proposed product decisions** (acceptance: product owner + control room):

- PD-RB-1 — no blind replay; reconnect = verify → new generation → fresh
  scans (§1–§2).
- PD-RB-2 — step 8 fresh domain scans are the sole source of post-reconnect
  work.
- PD-RB-3 — no new store lifecycle state for catch-up.
- PD-RB-4 — per-store per-domain timestamp watermarks; cursors never
  persisted (consistent with accepted ARCH PD-5).
- PD-RB-5 — two-layer idempotent enqueue (scan-level scope key,
  record-level version key).
- PD-RB-6 — exact skip logic incl. payload-hash short-circuit and
  ambiguity→review.
- PD-RB-7 — orders: automatic catch-up limited to watermark−overlap window;
  historic lifetime import only via manual backfill.
- PD-RB-8 — Administrator-only backfill wizard with mandatory read-only
  preview and 60-day/`read_all_orders` honesty.
- PD-RB-9 — onboarding initial-import windows (orders default: recent
  30 days).

**Open questions:**

- OQ-RB-1 — no official figure for Shopify query-visibility lag; 30-minute
  overlap default needs UAT validation.
- OQ-RB-2 — remote-deletion detection cadence (webhooks + periodic full-list
  reconciliation) is not defined by this document.
- OQ-RB-3 — existence of a changed-since query surface for inventory levels
  in 2026-07 (fallback: bounded full reconciliation read).
- OQ-RB-4 — exact customer initial-import option set for MVP.
- OQ-RB-5 — whether `read_all_orders` approval is realistically obtainable
  for the current custom-app distribution posture
  ([`../01-research/shopify-token-acquisition-notes.md`](../01-research/shopify-token-acquisition-notes.md));
  if not, the >60-day backfill path may be unavailable for some stores and
  the UX must degrade honestly.
- OQ-RB-6 — full `OrderSortKeys` enum values (capture §13.1) — posture does
  not depend on them, but Wave 2 should confirm `UPDATED_AT` exists as
  assumed by ARCH PD-5.
