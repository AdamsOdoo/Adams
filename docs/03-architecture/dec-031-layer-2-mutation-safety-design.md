# DEC-031 Layer 2 — Shopify Mutation Safety Design (Durable Attempt Identity, Reconciliation-Before-Retry)

> **Status: ACCEPTED — CONTROL-ROOM GATE A**, via DEC-036 D1–D38, per PR
> #177 comment
> [`5015044226`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5015044226)
> (2026-07-19). Originally registered 2026-07-16
> (Fable gap-closure mission); corrected 2026-07-18 (Wave 3 Gate A, Session
> A) and again 2026-07-19 (final consolidated Sessions-2-and-3 correction
> batch) per
> [`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) — read
> DEC-036 first, it is the authoritative decision record; this document is
> the narrative design companion. Acceptance authority: product owner +
> Claude control room. Design accepted; implementation is authorized only
> through the separately-issued, still-unissued Stage 0 prompt — Waves
> 3/4/5 mutation domains remain blocked until implemented with runtime
> proof.**
>
> **2026-07-19 correction notice (supersedes the 2026-07-18 notice below
> for every point it touches).** Per PR #177 comment
> [`5014689445`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5014689445)
> (the consolidated Sessions-2-and-3 ruling), the following are now
> binding and correct every prior mention in this document: the attempt
> model's `job_id` is `Many2one('shopify.connector.job', required=True,
> index=True, ondelete='restrict')` (§1.2); `mutation_domain` is a
> required, indexed `Char`, registry-validated, never a Selection of
   either kind (§1.2, §4.2); `outcome` is renamed `observed_outcome` and is
> **immutable once it leaves `pending`** — a human/reconciliation
> resolution never overwrites it, it only ever sets a separate,
> orthogonal `resolution_disposition`/`resolution_source` pair, read
> through a shared effective-disposition helper (§6); the single
> `request_fingerprint` field is split into `business_intent_fingerprint`
> (excludes CAS/idempotency mechanics) and `exact_request_fingerprint`
> (**includes** `changeFromQuantity` and the idempotency key — §4.1); C2
> commits on a **dedicated side cursor**, not the main cursor (§11); the
> job-row token field is `current_attempt_token`, not `attempt_id` (§1.1);
> retention (§12) is indefinite for unresolved attempts and configurable
> masking (not deletion, and not permanent full retention either) for
> resolved-terminal attempts after a window. Full detail and reasoning:
> DEC-036 Part 3 (D2, D5, D6, D10, D11, D14, D17, D19, D20, D28, D32,
> D35, D38).
>
> **2026-07-18 correction notice.** The decision numbering below
> (`L2-D1`–`L2-D15`) is the *original* registration and is **superseded**
> by DEC-036's complete, gap-free `L2-D1`–`L2-D38` numbering, which is the
> current acceptance candidate. This document's prose has been corrected
> in place (CAS field name, THROTTLED classification, transaction-boundary
> isolation-level assumptions, uninstall self-contradiction, batching
> default) but its own `L2-D#` labels are retained only as a cross-reference
> map into DEC-036 — do **not** treat this document's numbering as current
> for acceptance purposes. Full citations for every correction below:
> [`../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md`](../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md).

This document is the full Layer 2 design that
[`DEC-031`](../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md)
deferred ("reopened by name the moment a Shopify-mutation domain is
proposed"). The MVP completion program's Waves 3/4/5 propose exactly such
domains (inventory export, fulfillment/tracking write-back, product export),
so the reopening trigger is met. This document does not restate the accepted
Layer 1 analysis — the companion document
[`core-r2-job-execution-replay-safety.md`](core-r2-job-execution-replay-safety.md)
§3 (semantic contract), §4 (Options A–D comparison), §6 (crash/stale-owner
recovery table), §7 (state/error mapping), §8.2 (Option A recommendation and
field list, lines ~1219–1237), and §11 (carried open questions) remains the
evidence base and is **referenced, not duplicated**, throughout.

The rejected-approaches log (RA-001…RA-024) was checked in full. Nothing
below re-proposes a rejected approach; RA-014 (retry-everything), RA-017
(no connector idempotency key), RA-019/RA-021 (inventory identity/semantics),
RA-022/RA-023 (legacy fulfillment / order-ID-only fulfillment) directly
constrain and are honored by this design.

## Hard safety rules (binding on every section below)

1. **Never hold a PostgreSQL transaction lock across a remote Shopify
   call.** The existing `call.lease` side-transaction admission pattern
   (admitted under `FOR SHARE`, committed **before** the network call) is
   the model [Fact — current code].
2. **Never claim exactly-once remote effects.** The strongest claim this
   design makes is **at-most-once-ambiguous with reconciliation
   convergence**: an attempt either provably applied, provably did not
   apply, or is ambiguous until a reconciliation read resolves it.
3. **Never rely solely on in-memory state** — every safety decision keys
   off committed rows.
4. **Never blindly replay an uncertain mutation.** Uncertain → reconcile
   first, always.
5. **No hidden context bypasses** (no `sudo`/context flag that skips the
   attempt wrapper).
6. **Never weaken Wave 1 mechanics** — admission/lease, disconnect
   quiescence, security, protected-field behavior are preserved verbatim
   (§15).
7. **Every mutation domain declares its reconciliation strategy** in the
   matrix (§4). A mutation without a safe reconciliation strategy **fails
   closed** — it may not be registered or executed.

---

## 1. Durable operation identity

**[Proposed decision — L2-D1]** Adopt companion §8.2 Option A's job-row
fields **plus** a dedicated persisted mutation-attempt record (companion §4
Option B's audit shape, now justified because real mutation forensics are
needed — the exact revisit condition companion §4 recorded for Option B).

### 1.1 Job-row fields (companion §8.2 Option A basis) [Fact — already designed there]

**Corrected 2026-07-19 — see DEC-036 D1/D2 for the authoritative field
list; summarized here:**

- `current_attempt_token` (Char, UUIDv4, opaque) — regenerated per attempt;
  CAS token at finalize/sweep. **Renamed from `attempt_id`** to avoid
  colliding with `mutation.attempt`'s own per-row `attempt_token` field.
- `owner_worker_ref` (Char, diagnostic, mirrors `call.lease.worker_ref`).
- `running_since` (Datetime, set once per claim at C1).

`transport_attempted` lives on the attempt row only (§1.2) — **not**
duplicated on the job row, correcting this document's earlier drafting.

### 1.2 New model: `shopify.connector.mutation.attempt` [RESOLVED — DEC-036 D2, 2026-07-19]

One row per mutation attempt. Fields (**corrected 2026-07-19 per the
consolidated Sessions-2-and-3 ruling — see DEC-036 D2 for full reasoning**):

| Field | Type | Meaning |
|---|---|---|
| `job_id` | `Many2one('shopify.connector.job', required=True, index=True, ondelete='restrict')` | Owning job. **Resolved Many2one-restrict**, not a non-FK Integer — writes come from the single worker holding the job's claim lock, the same pattern that already makes `job_log.job_id`'s FK safe. |
| `attempt_token` | Char (UUID), required, unique | Matches the job-row's `current_attempt_token` for this attempt. **Renamed from `attempt_id`.** |
| `mutation_domain` | Char, required, indexed | **Resolved as registry-validated Char**, not a Selection of either kind — validated fail-closed against the reconciliation/mutation registry (DEC-036 D15/D16/D35). |
| `store_id` | Many2one, `related`, stored, indexed, readonly | Derived from the job (DEC-036 D3). |
| `expected_connection_generation` | Integer | Snapshotted at C2 (DEC-036 D18/D29). |
| `expected_store_identity` | Char | `myshopifyDomain` snapshotted at C2 (DEC-036 D18, new). |
| `remote_mutation_intent` | Char/JSON summary | Named mutation + target identifiers (GIDs/handles/SKUs) — identifiers only, never payloads. |
| `preconditions_snapshot` | JSON (redacted) | Persisted local pre-check evidence (§3). |
| `business_intent_fingerprint` | Char (SHA-256) | Stable business intent only; excludes CAS/idempotency mechanics (§4.1, DEC-036 D5, new split field). |
| `exact_request_fingerprint` | Char (SHA-256) | The exact normalized mutation document + exact transmitted variables, **including** `changeFromQuantity` and the idempotency key (§4.1, DEC-036 D5, new split field). |
| `shopify_idempotency_key` | Char (UUID), nullable | Persisted where the mutation supports/requires `@idempotent` (24h retention on Shopify's side [Fact — capture §9]); reused verbatim on reconcile-then-retry within `idempotency_valid_until`. |
| `idempotency_valid_until` | Datetime, nullable | Shopify's 24h window minus a configurable local safety margin (DEC-036 D6, new). |
| `transport_attempted` | Boolean | Committed BEFORE network; lives on this row only, never duplicated on `job`. |
| `observed_outcome` | Selection: `pending` / `succeeded` / `failed_clean` / `uncertain` | §5 taxonomy decides the value. **Renamed from `outcome`; immutable once it leaves `pending`** (DEC-036 D10). |
| `resolution_disposition` | Selection (2), nullable: `applied` / `not_applied` | Orthogonal to `observed_outcome`, never overwrites it (DEC-036 D10/D11). |
| `resolution_source` | Selection (2), nullable: `reconciliation_read` / `manual_admin` | New field (DEC-036 D10/D11). |
| `resolution_reason`, `resolution_uid`, `resolution_at` | Text / Many2one / Datetime | DEC-036 D11. |
| `inconclusive_reconciliation_count` | Integer, default 0 | Per-attempt scope, resolved sufficient (DEC-036 D17). |
| `remote_evidence_refs` | JSON | Remote GIDs, counts, userError codes, throttle status — references, not payload bodies (structured, not Text — DEC-036 D8). |
| `created_at`, `transport_at`, `resolved_at` | Datetime | Commit-point timestamps (§11). |

Uniqueness: `(job_id, attempt_token)` via `models.UniqueIndex` (never
`_sql_constraints`, confirmed silently inert); the job's
`operation_scope_key` uniqueness [Fact — current code] continues to
prevent two concurrent jobs for the same business operation — the attempt
table adds *per-attempt* identity underneath that, it does not replace it.

## 2. Job ownership

**[Proposed decision — L2-D3]** Companion §4 Option A verbatim: claim →
commit `state='running'` + `current_attempt_token` + `owner_worker_ref`
**before** the handler runs; finalize re-locks and CAS-verifies
`current_attempt_token`; a stale owner's finalize fails closed (companion
§6 invariants).

**Stale-owner sweep** — new `_sweep_stale_running_jobs()` cron (mirroring
the disconnect-quiescence controller's cron pattern [Fact — current code]):

- **Trigger:** `running` with `running_since` older than the sweep timeout.
  [Recommendation] Timeout basis: strictly greater than the worst-case
  handler duration, and jointly sized with `DISCONNECT_QUIESCE_TIMEOUT`
  (15 min) — companion §11 item 3 is resolved here as: sweep timeout ≥
  quiescence timeout, so the sweep never takes over a job the quiescence
  controller still counts as legitimately in flight. Proposed default:
  30 minutes, config-parameter-tunable. [Open question] final value needs
  Odoo.sh runtime measurement at implementation time.
- **Evidence-preserving takeover:** stale `running` +
  `transport_attempted = true` → route the attempt to **reconciliation**
  (§5), **never re-execute**; `transport_attempted = false` → safe requeue
  regardless of policy (nothing external happened — companion §6 row 1).
- Takeover uses the existing re-lock-and-revalidate discipline; expiry
  never auto-finalizes as succeeded/failed (companion §6).

## 3. Remote mutation intent + local preconditions

**[Proposed decision — L2-D4]** Before the intent commit (§11), the handler
persists into `preconditions_snapshot` the local evidence its mutation
depends on, so reconciliation and audit can later judge the attempt against
what was known at send time. Examples per domain:

- **Inventory export:** the CAS basis — the last-known Shopify quantity
  used as `changeFromQuantity` **[corrected 2026-07-18 — `compareQuantity`
  does not exist as an input field from Shopify Admin GraphQL API 2026-04
  onward; see source-materials refresh §1 and DEC-036 D12]**, per
  `(inventory_item_id, location_id)` binding identity (RA-019 honored),
  plus the Odoo source quantity and the recorded source-of-truth decision
  (RA-021 honored).
- **Fulfillment create:** the FulfillmentOrder GID, per-line remaining
  quantities read from Shopify immediately before send [Fact — FO
  `lineItems` carry remaining quantities, capture §6.2], location match
  (RA-023 honored).
- **Product export:** the product binding snapshot version / write-date and
  the identifier (`id`/`handle`/`customId`) that `productSet` will upsert
  by [Fact — capture §10].

## 4. Request fingerprint + mutation-domain reconciliation matrix

### 4.1 Two-hash fingerprint split [RESOLVED — DEC-036 D5, 2026-07-19]

**Corrected 2026-07-19.** The original single `request_fingerprint` field,
which excluded `changeFromQuantity` from the hash, was unsafe: that value
is part of what the connector actually transmits, and a fingerprint that
omits a transmitted parameter cannot be relied on for exact-parameter
matching. Two distinct hashes now exist:

- `business_intent_fingerprint = SHA-256({mutation_domain,
  inventory_item_id, location_id, target_quantity, ...domain equivalent})`
  — stable business intent only, excludes `changeFromQuantity` and the
  idempotency key/directive. Purpose: detect that two attempts share the
  same underlying business goal, for audit/dedup reasoning that must not
  vary with a fresh CAS read.
- `exact_request_fingerprint = SHA-256(normalized GraphQL document ‖
  canonical-JSON variables)`, with the GraphQL document normalized to
  parsed/re-serialized AST form (not raw string) and **including**
  `changeFromQuantity` and the idempotency key/directive. Purpose: (a)
  prove exactly what was transmitted, the basis for idempotency-key reuse
  decisions (§7) and forensic replay proof; (b) audit trail without
  storing payloads (hashes carry no PII, §12). **Never** reuse an
  idempotency key based on a hash that omits a transmitted request
  parameter — `exact_request_fingerprint`, not `business_intent_fingerprint`,
  governs key-reuse safety.

### 4.2 The matrix — one row per MVP mutation [Proposed decision — L2-D6]

All idempotency-capability claims below are [Fact], sourced from
[`shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md`](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)
§6.5, §9, §10, §11 (accessed 2026-07-16, API 2026-07); reconciliation
strategies are [Recommendation].

| Mutation | Scopes | Idempotency capability | Fingerprint basis | Reconciliation read | Retry after `uncertain` | Fail-closed rule |
|---|---|---|---|---|---|---|
| `inventorySetQuantities` | `write_inventory` | **Mandatory `@idempotent` UUID key from API 2026-04 (24h retention, cached response on replay)** + `changeFromQuantity` CAS **[corrected 2026-07-18 — field renamed from `compareQuantity`; `ignoreCompareQuantity` removed; see source-materials refresh §1/§2, DEC-036 D6/D12]** — idempotent + CAS = strongest class | items/locations/quantities/change-from values | `InventoryLevel.quantities(names)` per item+location | Yes — reuse persisted key within a local staleness window below Shopify's 24h (DEC-036 D6); after the window, reconcile first, never blind-reuse | CAS mismatch (`CHANGE_FROM_QUANTITY_STALE`) or stale key without fresh read → no send; batching is deferred (DEC-036 D4) — one pair per request |
| `inventoryAdjustQuantities` | `write_inventory` | Mandatory key, but delta-based — **excluded by design**: the connector is set-based (DEC-010 source-of-truth model; a replayed delta cannot be verified against an absolute read) | — | — | — | Never registered; registry has no entry → fail-closed |
| `fulfillmentCreate` | one of the three `write_*_fulfillment_orders` (+ fulfill-and-ship) | **NO documented idempotency** [Fact — capture §6.5] | FO GID + line items + quantities + tracking | FO line-item **remaining quantities** re-read + connector's **own fulfillment-GID ledger** (capture §6.6 — no app-attribution field on Fulfillment) | Only after reconciliation proves not-applied (remaining quantities unchanged AND no new own-ledger GID) | Reconciliation inconclusive → `blocked_manual_review`, never re-send |
| `fulfillmentTrackingInfoUpdate` | same three write scopes | Naturally idempotent **by convergence** (same tracking values → same end state) | fulfillment GID + tracking values | Read `Fulfillment.trackingInfo`, compare to intended values | Yes, after read confirms values absent | Fulfillment GID missing on read → manual review |
| `fulfillmentCancel` | [Open question — scopes not on fetched page, capture §6.5] | Idempotent **by state** (already-cancelled converges) | fulfillment GID | Read `Fulfillment.status == CANCELLED` | Yes, after state read | Status neither active nor cancelled as expected → manual review |
| `fulfillmentEventCreate` | `write_fulfillments` | None documented; **dedupe by event status + happenedAt** on read of `Fulfillment.events` | fulfillment GID + status + happenedAt | Read events, match status+time | Yes if matching event absent | Ambiguous match → skip (event is informational), log |
| `productSet` | `write_products` | **Natural idempotency via identifier upsert** (`ProductSetIdentifiers`: id/handle/customId) [Fact — capture §10]; note list-field semantics are declaratively destructive for omitted entries | identifier + normalized product input | Re-read product by the same identifier; compare intended fields | Yes — replay converges by upsert | Identifier absent/ambiguous → no send |
| `productVariantsBulkCreate` / `productVariantsBulkUpdate` | `write_products` | None documented; **reconciliation by variant identity** (SKU/option-combination under the bound product) | product GID + variant identities + values | Re-read variants of product; match by identity | Create: only if identity absent on read. Update: replay converges | Variant identity collision → manual review (RA-006 spirit: no fuzzy matching) |
| `publishablePublish` | `write_publications` | Idempotent **by state convergence** (already-published converges) | publishable GID + publication ids | Read publication status | Yes | Missing publication id → clean failure, no retry |
| `orderMarkAsPaid` | `write_orders` | Idempotent **by financial state re-read** (PAID converges; capture §1/§2) | order GID | Read `displayFinancialStatus` + transactions (`manualPaymentGateway`) | Only if re-read shows not PAID and no matching capture/sale transaction | Financial state ambiguous (e.g. PARTIALLY_PAID unexpected) → manual review |
| `metafieldsSet` (if used) | `write_products` (owner-dependent) | Set-semantics idempotent by convergence | owner GID + namespace/key/value | Re-read metafield by namespace/key | Yes | Owner missing → clean failure |

Every row registers `remote_effect_not_replay_safe` in the Layer 1 registry
[Fact — fail-closed default already accepted]; the matrix adds the
*reconciliation* strategy that the recovery path consults (§8). A future
mutation not in this matrix has no reconciliation strategy → fails closed
(hard rule 7); adding a row is a control-room-reviewed doc change plus
registry entry, never an implicit inheritance.

## 5. Uncertain remote outcome handling

### 5.1 Outcome taxonomy [Proposed decision — L2-D7]

| Event | Classification | Recorded outcome |
|---|---|---|
| Network timeout **after** send | Ambiguous | `uncertain` |
| **`THROTTLED`** | **[Corrected 2026-07-18 — reclassified from an original, unlabeled-Inference-as-Fact "not executed" claim.] Ambiguous — no official Shopify source establishes that a THROTTLED response guarantees the resolver did not execute** [Fact — absence of a guarantee; throttle returns error code `THROTTLED` with `throttleStatus`; the "recommended backoff time is one second" language is a stated recommendation, not a documented contractual minimum — see source-materials refresh §3, DEC-036 D9] | `uncertain`, reconcile-first for every mutation domain, never auto-classified `failed_clean` |
| HTTP 5xx | Ambiguous (may have executed) | `uncertain` |
| GraphQL `userErrors` | Clean remote rejection — classified via existing 16-class taxonomy [Fact — DEC-009] | `failed_clean` |
| Ambiguous/partial `userErrors` (mutation returns both effect and errors) | Ambiguous | `uncertain` |
| Worker crash between send and outcome commit | Ambiguous (found by sweep, §2/§9) | `uncertain` |
| Clean success response | Applied | `succeeded` + evidence refs |

### 5.2 Reconciliation reads as first-class jobs [RESOLVED — DEC-036 D10/D14, corrected 2026-07-19]

A reconciliation read is its own job (`job_type` registered
`remote_read_replay_safe` — reads are replay-safe by the accepted Layer 1
contract), linked to its target attempt via `mutation_attempt_id`
(`Many2one`, required, `ondelete='restrict'` — DEC-036 D14). It executes
the matrix row's "reconciliation read" (beginning with the store-identity
check, §7), and decides **applied / not-applied / inconclusive**. **Corrected
2026-07-19:** the verdict is recorded via `resolution_disposition`
(`applied`/`not_applied`) and `resolution_source='reconciliation_read'` —
it **never** overwrites `observed_outcome`, which remains permanently
`uncertain` for this attempt (DEC-036 D10). Applied → the original
mutation job completes without resend; not-applied → the reconciliation
gate clears and the original job becomes retry-eligible, with a **new**
attempt created only on its next dispatch (never by mutating the resolved
attempt row); inconclusive → `inconclusive_reconciliation_count`
increments under a re-acquired row lock and the next reconciliation read is
scheduled (§5.3).

### 5.3 Retry eligibility [RESOLVED — DEC-036 D10, corrected 2026-07-19]

Job consequences are derived from the effective-disposition helper (DEC-036
D10), never from `observed_outcome` alone:

- effective **applied** (`observed_outcome='succeeded'`, or `'uncertain'`
  with `resolution_disposition='applied'`) → the original mutation job
  completes without resend.
- effective **not_applied** (`observed_outcome='failed_clean'`, or
  `'uncertain'` with `resolution_disposition='not_applied'`) → normal
  DEC-009 retry policy (class-based, bounded) for the `failed_clean` case;
  for the resolved-`uncertain` case, the original job becomes
  retry-eligible and a new attempt is created only on its next dispatch.
- effective **unresolved** (`observed_outcome='uncertain'`,
  `resolution_disposition` still null) → **reconcile-then-retry only**; no
  retry path exists that does not pass through a completed reconciliation
  decision.
- Reconciliation **inconclusive after N attempts** (N = 3, per-attempt
  scope, resolved sufficient — DEC-036 D17) → `blocked_manual_review` /
  `manual_review_subreason='duplicate_risk'` [Fact — value exists,
  companion §7], with the attempt record and reconciliation evidence
  attached.

## 6. Terminal failure, manual review, operator override

**[RESOLVED — DEC-036 D10/D11, 2026-07-19, corrected per the consolidated
Sessions-2-and-3 ruling; supersedes L2-D10's original design below.]**
`blocked_manual_review` presents the attempt record (intent, preconditions,
both fingerprints, evidence refs). `observed_outcome` (renamed from
`outcome`) is **immutable once it leaves `pending`** — no code path,
including the override below, ever rewrites it; it permanently records
what transport evidence actually showed. A new **Administrator-only,
audited override** (`action_resolve_mutation_attempt`) lets an operator set
a *separate*, orthogonal `resolution_disposition` (`applied`/`not_applied`)
plus `resolution_source='manual_admin'`, **with a mandatory reason**,
logged append-only via the existing `job.log` mechanism [Fact —
append-only redacted log exists]. A shared, pure effective-disposition
helper derives the job consequence from both `observed_outcome` and
`resolution_disposition` together (full branch table: DEC-036 D10) — the
override **never** forces `observed_outcome` to `succeeded`/`failed_clean`,
correcting this document's earlier "atomically forces outcome" design,
which was itself found to violate the three-layer separation it was meant
to implement. The override **never edits remote state silently** — it only
records the operator's judgment locally; any corrective Shopify action is
a new, ordinary, fully-wrapped mutation job. Both pre-existing
`blocked_manual_review→queued` actions (`action_resolve_manual_review`,
`action_manual_retry`) are extended to refuse any `duplicate_risk`,
mutation-attempt-linked job, closing the bypass this design originally left
open around the stricter override action. Operator-authorized retry
remains the one path that may re-attempt a `remote_effect_not_replay_safe`
job (companion §6, last row) — now further gated: the retry still runs
through the attempt wrapper with a fresh `attempt_token`.

## 7. Disconnect / credential replacement / connection generation

**[RESOLVED — DEC-036 D18/D28/D29, 2026-07-19, corrected per the
consolidated Sessions-2-and-3 ruling; supersedes L2-D11's original design
below.]** Every attempt record snapshots `expected_connection_generation`
**and** `expected_store_identity` (`myshopifyDomain`, new field) at C2
[Fact — `expected_connection_generation` already exists; stale-generation
jobs never execute under existing admission]. On a generation bump
(credential replacement/reconnect):

- In-flight `uncertain` attempts are routed to reconciliation **under the
  new generation** before any mutation domain resumes — the reconciliation
  read runs with current credentials, and **begins by verifying the
  current `myshopifyDomain` against the attempt's snapshotted
  `expected_store_identity`** (DEC-036 D18) before interpreting any other
  response data. Mismatch → `blocked_manual_review`/
  `store_identity_mismatch`, never retried.
- Stale-generation mutation jobs never execute [Fact — existing admission
  behavior, unchanged]. **Correction, 2026-07-19:** `_mutate_token`'s
  existing behavior already, correctly, bumps `connection_generation`
  atomically on any credential set/replace while `connected` — any prior
  reading of this document implying the bump does not already happen is
  stale and is corrected here.
- **Disconnect/quiescence is now awareness-based, not a timeout race**
  (§15, DEC-036 D28): new mutation admissions stop immediately on
  disconnect/quiescence; automatic finalization defers credential-clearing
  while any mutation attempt is unresolved or a linked reconciliation job
  is pending; force-disconnect is Administrator-only, requires a reason,
  is audited, and routes unresolved attempts to manual review rather than
  silently resolving them.
- **Resolved** (was: open question): store-identity change detection is a
  reconciliation-read-first check (DEC-036 D18), reusing the existing
  `store.py` single-field equality check; `_run_connection_probe`'s
  domain-mismatch branch additionally calls `action_mark_reconnect_needed`.

## 8. Concurrency

Existing lease admission + per-job claim are preserved [Fact]. New behavior
in `_recover_after_concurrency_conflict` (real PG 40001/lock-timeout
recovery, runtime-proven [Fact — current code]):

**[Proposed decision — L2-D12] The new recovery branch:** on a genuine
serialization failure / lock timeout in a mutation job, recovery consults
the replay-policy registry (Layer 1 mechanism, unchanged) and, for
`remote_effect_not_replay_safe`, the attempt record:

- `transport_attempted = false` → **safe re-run** (nothing was sent; the
  rolled-back transaction had no external effect) — routes through the
  existing bounded `concurrency_race_conflict` retry.
- `transport_attempted = true` → **route to reconciliation** (§5), never
  the blanket auto-retry. This is exactly companion §6 row 4, now with the
  attempt record as durable evidence (the intent commit survives the main
  transaction's rollback because it is committed pre-network, §11).

Two active owners, stale finalize, takeover-without-expiry remain
structurally prevented per companion §6's invariant list
(`current_attempt_token` CAS).

## 9. Crash recovery

Restart with a committed `running` + `transport_attempted = true` row: the
stale-owner sweep (§2) finds it after timeout and routes to reconciliation —
companion §6 rows 2–3 ("during transport" and "after response, before
commit" deliberately collapse to the same conservative handling). With
`transport_attempted = false`, safe requeue. No in-memory state is consulted
(hard rule 3); the sweep is purely row-driven and cron-scheduled, so it
survives any process death.

## 10. Remote rate limiting and userErrors

- **`THROTTLED` = `uncertain` [corrected 2026-07-18 — the original
  "= not executed" claim had no official-source support; see source-materials
  refresh §3, DEC-036 D9].** Record `uncertain`, route through
  reconciliation before any retry, for every mutation domain — never
  auto-classify `failed_clean`. If a retry is later authorized after
  reconciliation resolves the attempt, honor `throttleStatus.restoreRate`/
  `currentlyAvailable` for backoff pacing; the shopify.dev rate-limits page
  states "the recommended backoff time is one second" as guidance, not a
  documented guarantee [Fact — quote, source-materials refresh §3]. The
  persisted idempotency key (where present) is reused on the throttle
  retry only if still within the local staleness window (DEC-036 D6) —
  same intent, same key, never a blind fresh-key resend past the window.
- **userErrors** are clean failures, classified via the existing 16-class
  taxonomy [Fact — DEC-009]; no new error class is required for them.
  Partial-effect responses (data + userErrors) classify as `uncertain`
  (§5.1).
- API version pinned to 2026-07; the fall-forward risk on unsupported
  versions [Fact — capture §11] is monitored per the capture's
  recommendation; a version fall-forward observed mid-attempt → treat the
  attempt as `uncertain` (semantics may have shifted).

## 11. Local transaction boundaries — exact commit points

**[RESOLVED — DEC-036 D19/D20/D21/D22, 2026-07-19, corrected per the
consolidated Sessions-2-and-3 ruling — see DEC-036 Part 6 for the complete
authoritative version of this section; the `L2-D#` numbering here is
retained only as a historical cross-reference into DEC-036.]**

**Governing isolation-level fact, established 2026-07-18 (previously
absent from this document):** Odoo 19 sets every cursor to PostgreSQL
**`REPEATABLE READ`**, not the PostgreSQL default `Read Committed`
(`odoo/sql_db.py`, `Cursor.__init__`,
`self.connection.set_isolation_level(ISOLATION_LEVEL_REPEATABLE_READ)` —
source-materials refresh §5). This means a worker's later statement inside
the **same** transaction does **not** automatically see another
connection's newly committed data — the snapshot is fixed at the
transaction's first statement. Every commit point below must therefore be a
genuine, separate transaction boundary, and any code that reads a row
across one of these boundaries (recovery, reconciliation, the sweep) must
force a fresh read via `invalidate_recordset()` + re-`browse()`/
re-`search()` — the existing, proven precedent for this is
`_claim_for_dispatch`'s own post-lock-acquisition invalidate-and-re-filter
step (`shopify_connector_job.py`), which every new cross-transaction read
point in this protocol must follow identically (DEC-036 D21).

Four commit points per mutation attempt:

```
C1: CLAIM COMMIT           main cursor: try_lock_for_update →
                           state='running', current_attempt_token,
                           owner_worker_ref, running_since → COMMIT
C2: ATTEMPT-INTENT COMMIT  RESOLVED: dedicated SIDE CURSOR, mirroring
                           call_lease's _admit pattern (DEC-036 D20).
                           Attempt row created (intent, preconditions,
                           both fingerprints, idempotency key),
                           transport_attempted=true → COMMIT, strictly
                           before any network call. All request data is
                           materialized into plain immutable Python
                           values before this commit.
    [No DB lock held beyond C2 — PROVEN. No main-cursor statement occurs
    between C1's commit and C3's re-lock, by construction, since C2 lives
    entirely on its own side cursor — DEC-036 D22.]
NET: network call          bounded window, not itself a commit point;
                           no main-cursor ORM/SQL operation occurs; no
                           open main-cursor transaction spans this
                           window; call.lease admission (side txn, FOR
                           SHARE, committed before network) unchanged
                           [Fact].
C3: OUTCOME COMMIT         fresh main-cursor txn: invalidate/re-browse
                           (Odoo REPEATABLE READ), re-lock, verify
                           current_attempt_token matches; write
                           observed_outcome + evidence + terminal/retry
                           state → COMMIT. Claimability-gate widening
                           required for 40001/lock-timeout recovery to
                           actually reach this point (DEC-036 D25).
```

**Choice and justification — RESOLVED 2026-07-19.** The intent commit
(C2) commits on a **dedicated side cursor**, mirroring `call_lease`'s
`_admit` pattern — see DEC-036 D20. **The original justification for
main-cursor C2 was withdrawn on 2026-07-18**: it cited Odoo's
`_commit_progress()` API as the pattern `_drain_one` "exactly" follows;
direct code reading confirms `_drain_one` uses a bare, commented
`cr.commit()`, **not** the `_commit_progress()` helper — that citation was
factually wrong (DEC-036 D19). The side-cursor design, now accepted,
**structurally eliminates** the "unrelated main-cursor business changes
accidentally co-committed at C2" risk rather than merely testing for it
after the fact — a stronger guarantee than the main-cursor alternative
could ever provide. `mutation_attempt.job_id`'s field type is **resolved**
under DEC-036 D2 (`Many2one-FK-restrict` — the `call_lease.job_id`
lock-contention precedent does not transfer, since `mutation.attempt`
writes come from a single sequential owner, the same pattern that already
makes `job_log.job_id`'s FK safe). The main-cursor write-isolation
invariant (DEC-036 D21) is now scoped to the **C1 claim-commit only**,
since C2 never touches the main cursor. The open-transaction-vs-network-call
question (DEC-036 D22) is resolved by design — the main cursor's last
statement before NET is C1's own commit — with its `pg_stat_activity`-based
runtime proof remaining a Stage 0 merge-acceptance criterion (DEC-036 D38),
not a precondition to beginning implementation.

**PG failure between points — recovery table** [corrected 2026-07-18/19 to
distinguish plain-crash vs. genuine-PG-exception recovery ownership, and to
distinguish an ordinary non-crashing exception from both — see DEC-036
D23/D24/D25 for the authoritative version]:

| Failure window | Durable state | Recovery |
|---|---|---|
| Before C1 | nothing | ordinary re-claim |
| C1→C2 | running + `current_attempt_token`, no attempt row / `transport_attempted=false` | sweep (plain crash) or `_recover_after_concurrency_conflict` (PG exception): safe requeue (fresh `current_attempt_token`) |
| C2→NET (crash before send) | intent committed, `transport_attempted=true` | **unconditionally** treated as "transport may have occurred" → reconciliation, never re-invoked directly. Sweep owns plain-crash recovery; the widened `_recover_after_concurrency_conflict` branch (DEC-036 D25, requires a structural fix to the current claimability gate — a `running` row is otherwise always treated as stale) owns genuine PG 40001/lock-timeout recovery in this window. An ordinary, non-crashing Python exception in this window routes through normal `_route_failure`, **not** this table (DEC-036 D23). |
| NET→C3 | intent committed, no outcome | identical handling to C2→NET — reconciliation, never re-invoked (DEC-036 D24) |
| During C3 (40001/lock timeout) | intent committed, transport done | widened recovery branch (DEC-036 D25) → reconciliation |
| After C3 | `observed_outcome` committed (immutable) | effective disposition (DEC-036 D10) per outcome/resolution; done |

## 12. Audit evidence, retention, upgrade, uninstall, rollback

**[RESOLVED — DEC-036 D32/D33/D34/D36, 2026-07-19 — supersedes L2-D14's
original design below.]**

- **Audit:** attempt records + `job.log` entries carry identifiers, counts,
  and reasons only — payload bodies are never stored; existing redaction
  rules apply [Fact — append-only redacted log exists]. Both fingerprints
  are SHA-256 hashes; **no PII** is derivable from them.
- **Retention — corrected 2026-07-19 (DEC-036 D32).** Two-tier: **unresolved,
  uncertain, or manual-review attempts are retained indefinitely** — no
  cron, sweep, or manual action ever deletes or masks these rows while
  their effective disposition (DEC-036 D10) is `unresolved`. **Resolved
  terminal attempts** retain full allowlisted evidence for a configurable
  period (default candidate 180 days); after that period, a new sweep
  masks bulky evidence fields in place (mirroring the existing
  `pii_retention.run_sweep()` pattern), while permanently keeping the row,
  its identifiers, both fingerprints, `observed_outcome`,
  `resolution_disposition`/`resolution_source`/`resolution_reason`/
  `resolution_uid`/`resolution_at`, and all timestamps. The row itself is
  **never** `.unlink()`d by any Stage 0 mechanism, in either tier —
  mirroring `job`/`job.log`'s append-only, `ondelete='restrict'`-anchored
  posture (DEC-030). This corrects the original design's ungrounded
  "pruned by existing retention sweep... aligned with job retention" claim,
  which referred to no mechanism verifiable anywhere in the codebase; a
  `running` job's attempt row is never a cleanup candidate under either
  tier (companion §6 invariant).
- **Upgrade:** purely **additive** — three job fields + one new model; no
  data migration of existing rows (all historical jobs have
  `transport_attempted=false` semantics vacuously). Standard Odoo
  additive-field upgrade; no pre/post migrate script anticipated.
- **Uninstall — corrected 2026-07-18, simplified further 2026-07-19.**
  This bullet previously self-contradicted the Rollback bullet immediately
  below it (which already said attempt history is never deleted).
  Corrected per DEC-036 D34: `shopify.connector.mutation.attempt` is
  **core-owned** (`addons/shopify_connector_core/models/`) and therefore
  inherits `shopify.connector.job`/`job.log`'s DEC-030 posture, **not** the
  domain-owned-binding-table export-then-drop posture. On a **domain-level**
  uninstall (e.g. the inventory module), `mutation.attempt` rows survive
  core-side, joined to their LC-1-retyped owning job, remaining queryable
  by `mutation_domain` (a plain `Char`, unaffected by any Selection
  uninstall lifecycle). Only a **core/Lite-substrate** uninstall (itself
  unsupported while any domain module remains installed) loses this data,
  identically to `job`/`job.log`, under DEC-030's existing, unmodified
  matrix. **DEC-036 D35 is now resolved** (`mutation_domain` is a
  registry-validated indexed `Char`, not a Selection of either kind) —
  this removes the contingency this bullet previously carried: there is no
  Selection-value historic-conversion mechanism needed at all, since a
  `Char` field has no enumerated-value lifecycle to reconcile with an
  uninstall in the first place.
- **Rollback:** before any mutation domain ships, the feature rolls back
  cleanly (drop fields/model — nothing depends on them; proven by a
  negative-migration test, DEC-036 D33). **After** a mutation domain has
  run, the attempt table is **retained as evidence, never deleted**
  (DEC-036 D32); rollback requires **two coordinated mechanisms together,
  not either alone** (corrected 2026-07-18 — the original single-mechanism
  wording under-specified this): (a) the relevant
  `store.settings.*_domain_enabled` flag set to `False`, blocking any *new*
  job from reaching `running`; **and** (b) the job_type's replay-policy
  registry entry set/reverted to `remote_effect_not_replay_safe`, fail-closing
  auto-retry for anything already in flight. Mechanism (b) alone — as this
  bullet originally implied — does not stop an already-`queued` job from
  starting its *first* attempt, since the replay-policy check never fires
  on a first attempt (DEC-036 D36).

## 13. Performance and test strategy

**Performance [Inference]:** ~2 extra commits per mutation (C1 already
exists in Option A's design; C2 and the attempt-row insert are new) — small,
bounded, and per-mutation, dwarfed by the network round-trip. **Batching —
corrected 2026-07-18, implements the ruling on PR #177 comment 5012854989
point 5:** the original "one attempt record per request, with per-item
evidence" design assumed batch partial-success semantics that are
**unproven** — no source confirms whether Shopify's `userErrors` carry a
per-entry field-path index, or whether one bad entry fails the whole
request. Per DEC-036 D4, Stage 0/1 instead **default to one
`(inventory_item_id, location_id)` pair per mutation request/attempt row**;
multi-entry `quantities[]` batching is explicitly out of scope until
partial-batch semantics are proven or every entry can be independently
reconciled. Bulk operations (`bulkOperationRunMutation`) remain out of MVP
scope, unchanged. PB alignment: the DEF-PB-1/SRR-03 performance-baseline
observations are re-measured in the runtime-proof pass below; the
throughput cost of one-pair-per-request against PB-20's ≥300 pushes/hour
target is a Stage 1 sizing question, not a Stage 0 design question.

**Test strategy [Proposed decision — L2-D15]:**

1. **Unit:** attempt state machine (all outcome transitions), fingerprint
   normalization (stable across key order, excludes volatile fields),
   idempotency-key persistence/reuse rules.
2. **Concurrency:** real PG 40001/lock-timeout injection (extending the
   existing proven harness [Fact]) with mutation policies registered —
   proving the §8 branch: pre-transport → re-run; post-transport →
   reconciliation, never handler re-invocation.
3. **Crash-injection:** kill between each commit-point pair of §11's table;
   assert the recovery column's disposition.
4. **Reconciliation-decision matrix tests:** one test per §4.2 row per
   decision outcome (applied / not-applied / inconclusive).
5. **Source guards — extended 2026-07-19 (DEC-036 D16/D37):** an AST guard
   mirroring the existing `execute_business` guard pattern [Fact — pattern
   exists]: **no Shopify mutation call site outside the attempt wrapper** —
   any GraphQL document containing `mutation` issued by the API client must
   originate from the wrapper, enforced by static test. **Plus a runtime
   guard**: `shopify_connector_api_client.py`'s send path fails closed —
   raises, never silently proceeds — when a mutation document is submitted
   without a valid Layer 2 attempt context/token, independent of and
   complementary to the static AST guard (defense in depth: the AST guard
   catches a bypass before merge; the runtime guard catches it if the AST
   guard is ever bypassed or misses a call site). `shopify_connector_api_client.py`
   is therefore in Stage 0's allowed-file list (corrected from the
   original Stage 0 packet, which omitted it).
6. **Runtime proof — four distinct layers, corrected 2026-07-19 (DEC-036
   D38; not conditioned on Odoo.sh-internal `SIGKILL` being the sole
   acceptable crash-proof route):** (1) static/unit/logical tests over
   C1/C2/NET/C3; (2) genuine PostgreSQL multi-connection concurrency tests
   under Odoo REPEATABLE READ; (3) a controlled real process-death/crash
   harness against real PostgreSQL, run outside or alongside Odoo.sh
   wherever process control is actually available; (4) exact-head Odoo.sh
   multi-worker proof — Worker B cannot execute a handler Worker A durably
   owns; sweep-driven reconciliation observed on a real killed worker; zero
   residue; no secret leakage. All four are Stage 0 **merge-acceptance**
   criteria, not preconditions to beginning implementation.

## 14. Decisions requiring acceptance before implementation

**[Superseded 2026-07-18 — this table's `L2-D1`–`L2-D15` numbering is kept
only as a historical cross-reference; the current, complete, gap-free
`L2-D1`–`L2-D38` decision inventory — with full fact/inference/recommendation/
accepted-candidate-wording/alternatives/risk/rollback/impact/tests/unresolved-question
detail for every item, and explicit BLOCKING flags — is
[`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) §3. Read DEC-036
for acceptance purposes; this table is retained for historical continuity
only.]**

Each item is a [Proposed decision]; acceptance authority for all: **product
owner + Claude control room**. All block Waves 3/4/5 mutation
implementation.

| ID | Statement | Evidence | Alternatives | Consequences / risks | Rollback | Affected waves |
|---|---|---|---|---|---|---|
| L2-D1 | Option A job fields + attempt model together | Companion §4/§8.2; capture §6.5/§9 | Option A fields only (weaker forensics); Option C outbox (heavier) | +1 model; strongest audit | Additive, droppable pre-ship | 3,4,5 |
| L2-D2 | `shopify.connector.mutation.attempt` schema (§1.2) | Companion §4 Option B revisit condition met | Fields-on-job only | New ACL + join cost | Drop model | 3,4,5 |
| L2-D3 | Committed running + attempt_id CAS + `_sweep_stale_running_jobs` cron, 30-min default | Companion §4/§6 | Heartbeat-based lease | Sweep/quiescence timeout coupling (risk: mis-sized timeout) | Disable cron; fields inert | 3,4,5 |
| L2-D4 | Persisted preconditions snapshot per domain | §3; RA-019/021/023 | None (audit-blind) | Snapshot staleness risk — mitigated by CAS/re-reads | Field inert | 3,4,5 |
| L2-D5 | SHA-256 request fingerprint, normalization rules | §4.1 | Store full payloads (rejected: PII/redaction) | Hash collisions negligible | Field inert | 3,4,5 |
| L2-D6 | The §4.2 matrix as the closed set of MVP mutations, incl. excluding `inventoryAdjustQuantities` | Capture §6.5/§9/§10/§11; DEC-010 | Delta-based inventory (conflicts with set-based source-of-truth model) | New mutation ⇒ doc + review | Matrix rows removable | 3,4,5 |
| L2-D7 | Outcome taxonomy incl. THROTTLED = failed_clean | Capture §11 [Fact] | Treat THROTTLED as uncertain (wasteful, wrong) | — | — | 3,4,5 |
| L2-D8 | Reconciliation reads as first-class `remote_read_replay_safe` jobs | Layer 1 contract [Fact] | Inline reconciliation in recovery path (violates no-network-in-recovery-txn) | More jobs; clean layering | Job type removable | 3,4,5 |
| L2-D9 | Reconcile-then-retry only for uncertain; N=3 inconclusive cap | §5.3; DEC-009 | Unbounded reconciliation | Manual-review volume risk | Tune N | 3,4,5 |
| L2-D10 | Audited admin-only override, local-only effect | §6 | No override (operators stuck) | Misuse risk — mitigated by audit + reason | Remove UI action | 3,4,5 |
| L2-D11 | Generation-bound attempts; reconcile under new generation before resume | §7; existing admission [Fact] | Resume blindly (unsafe) | Store-identity edge case open | — | 3,4,5 |
| L2-D12 | 40001-recovery branch keyed on transport_attempted | §8; companion §6 row 4 | 17th error class (companion §7 fallback — not preferred) | Resolves companion §11 item 2 in favor of the boolean | Revert branch | 3,4,5 |
| L2-D13 | C1/C2/NET/C3 commit-point protocol, C2 on main cursor pre-network | §11; Odoo `_commit_progress` evidence [Fact] | C2 as side txn (rejected: consistency seam, no reader needs it) | 2 extra commits/mutation | — | 3,4,5 |
| L2-D14 | Audit/retention/uninstall/rollback policy (§12) | DEC-030; existing redaction [Fact] | — | — | — | 3,4,5 |
| L2-D15 | Test strategy incl. AST wrapper guard + Odoo.sh multi-worker proof as acceptance blockers | §13; existing guard pattern [Fact] | Trust code review alone | CI cost | — | 3,4,5 |

Also resolved-by-acceptance: companion §11 item 1 (`transport_attempted`
set **generically by the dispatcher/API-client boundary**, per the wrapper),
item 2 (boolean field, not a 17th class — L2-D12), item 3 (timeout ordering,
§2), item 4 (the 2026-07-16 capture is that refresh), items 5–6 (L2-D2,
§5.2).

## 15. What Layer 2 does NOT change — Wave 1 mechanics preserved verbatim

[Fact — all of the following remain exactly as shipped and accepted]

- The job state machine incl. `running` / `retry_waiting` /
  `failed_retryable` / `blocked_manual_review` and the 16-class error
  taxonomy (DEC-009) — no new state, no new error class.
- `idempotency_key` + `operation_scope_key` uniqueness constraints.
- `expected_connection_generation` admission — stale-generation jobs never
  execute.
- The Layer 1 replay-policy registry: three classes, fail-closed default,
  registry-completeness test, existing declarations.
- `_drain_one`'s per-job transaction pattern and
  `_recover_after_concurrency_conflict`'s re-lock-and-revalidate discipline
  (extended by §8's branch, not modified for read-only jobs).
- `call.lease` admission on a side transaction under `FOR SHARE`, committed
  before network — the lease model is neither extended nor repurposed
  (companion §4 Option B analysis stands).
- `job.log` append-only redacted logging.
- Disconnect quiescence controller behavior and timeouts.
- Security, ACLs, and protected-field behavior.
- All currently shipped read-only handlers' observable behavior.

---

*References: companion doc §3, §4, §6, §7, §8.2, §9, §11;
DEC-009/DEC-010/DEC-011/DEC-025/DEC-030/DEC-031/DEC-036; capture file
2026-07-16 (§1, §2, §6.2, §6.5, §6.6, §9, §10, §11); capture file
2026-07-18
([`shopify-layer2-mutation-safety-refresh-2026-07-18.md`](../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md),
full document); rejected-approaches log RA-001…RA-024 (checked, none
re-proposed); SRR-03/04/09 (SRR-04/09 remain open per DEC-036 D38 —
required-resolved-or-explicitly-carried-forward condition on runtime-proof
acceptance).*

**2026-07-18 correction summary (Wave 3 Gate A, Session A):** this document
was corrected for (1) the CAS field name (`compareQuantity`/
`ignoreCompareQuantity` → `changeFromQuantity`, §3/§4.2); (2) `THROTTLED`
reclassification (`failed_clean` → `uncertain`, §5.1/§10); (3) the
transaction-boundary section's isolation-level assumptions (Odoo 19 uses
PostgreSQL REPEATABLE READ, not Read Committed, and the section's
`_commit_progress()` citation was factually wrong, §11); (4) the
Uninstall/Rollback self-contradiction (§12); (5) the batching default
(one pair per request, not one-attempt-per-batched-request, §13); and (6)
pointers to DEC-036's complete, gap-free `L2-D1`–`L2-D38` decision
inventory, which supersedes this document's own `L2-D1`–`L2-D15` numbering
for acceptance purposes (§14). **This design remains status Proposed —
these are corrections to the candidate text, not an acceptance.**

**2026-07-19 correction summary (final consolidated Sessions-2-and-3
ruling, PR #177 comment
[`5014689445`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5014689445)):**
this document was corrected again for (1) the schema — `job_id` resolved
`Many2one`-restrict, `mutation_domain` resolved registry-validated `Char`,
job-row token renamed `current_attempt_token`, attempt-row token renamed
`attempt_token` (§1); (2) the fingerprint split — `business_intent_fingerprint`
(excludes CAS/idempotency) and `exact_request_fingerprint` (includes
`changeFromQuantity` and the idempotency key), replacing the single,
unsafe `request_fingerprint` (§4.1); (3) `outcome` renamed
`observed_outcome`, now immutable once it leaves `pending`, with a new
orthogonal `resolution_disposition`/`resolution_source` pair and a shared
effective-disposition helper replacing the "resolution forces outcome"
mechanism (§5.2/§5.3/§6); (4) idempotency defect-code fail-closed routing
and `idempotency_valid_until` (§7 cross-reference, DEC-036 D6); (5) C2
resolved onto a dedicated side cursor, closing the cursor-placement and
`job_id`-type BLOCKING items (§11); (6) reconciliation-job linkage
resolved to `Many2one`-restrict, not a non-FK Char (§11 cross-reference,
DEC-036 D14); (7) retention resolved to indefinite-for-unresolved plus
configurable-masking-for-resolved-terminal, replacing both the original
claim and this document's own first, over-corrected retain-forever-with-no-masking
design (§12); (8) disconnect/quiescence resolved to awareness-based
finalization, not a timeout race (§7); (9) the mutation-wrapper/API-client
runtime guard and the four-layer proof-environment plan (§13). **Every
item this document's 2026-07-18 revision left as a DEC-036 BLOCKING
cross-reference is now resolved** — see DEC-036 Part 3/5/6 for the
complete, authoritative reasoning. **At the time this correction batch was
written, the design remained status CONTROL-ROOM ACCEPTANCE CANDIDATE —
NOT YET ACCEPTED** — these were corrections to the candidate text, not an
acceptance act. **Acceptance act (2026-07-19, later the same day): ACCEPTED
— CONTROL-ROOM GATE A**, per PR #177 comment
[`5015044226`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5015044226)
— see the status banner at the top of this document.
