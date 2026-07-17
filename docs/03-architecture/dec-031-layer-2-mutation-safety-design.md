# DEC-031 Layer 2 — Shopify Mutation Safety Design (Durable Attempt Identity, Reconciliation-Before-Retry)

> **Status: PROPOSED — NOT accepted. Fable gap-closure mission, 2026-07-16.
> This is the complete Layer 2 design registered by DEC-031's dated revision
> note. Acceptance authority: product owner + Claude control room. No
> implementation authorized; Waves 3/4/5 mutation domains are blocked until
> this design is accepted and implemented with runtime proof.**

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

- `attempt_id` (Char, UUIDv4, opaque) — regenerated per attempt; CAS token
  at finalize/sweep.
- `owner_worker_ref` (Char, diagnostic, mirrors `call.lease.worker_ref`).
- `transport_attempted` (Boolean, default False) — committed **before** any
  network send.

### 1.2 New model: `shopify.connector.mutation.attempt` [Proposed decision — L2-D2]

One row per mutation attempt. Fields:

| Field | Type | Meaning |
|---|---|---|
| `job_id` | Many2one job, required, indexed | Owning job. |
| `attempt_id` | Char (UUID), required, unique | Matches the job-row token for this attempt. |
| `mutation_domain` | Selection (matrix rows, §4) | e.g. `inventory_set_quantities`, `fulfillment_create`. |
| `remote_mutation_intent` | Char/JSON summary | Named mutation + target identifiers (GIDs/handles/SKUs) — identifiers only, never payloads. |
| `preconditions_snapshot` | JSON (redacted) | Persisted local pre-check evidence (§3). |
| `request_fingerprint` | Char (SHA-256) | Hash of normalized mutation document + normalized variables (§4.1). |
| `shopify_idempotency_key` | Char (UUID), nullable | Persisted where the mutation supports/requires `@idempotent` (24h retention on Shopify's side [Fact — capture §9]); reused verbatim on reconcile-then-retry within the window. |
| `transport_attempted` | Boolean | Committed BEFORE network; mirrors job field for this attempt. |
| `outcome` | Selection: `pending` / `succeeded` / `failed_clean` / `uncertain` | §5 taxonomy decides the value. |
| `remote_evidence_refs` | Text | Remote GIDs, counts, userError codes, throttle status — references, not payload bodies. |
| `created_at`, `transport_at`, `resolved_at` | Datetime | Commit-point timestamps (§11). |

Uniqueness: `(job_id, attempt_id)` unique; the job's `operation_scope_key`
uniqueness [Fact — current code] continues to prevent two concurrent jobs
for the same business operation — the attempt table adds *per-attempt*
identity underneath that, it does not replace it.

## 2. Job ownership

**[Proposed decision — L2-D3]** Companion §4 Option A verbatim: claim →
commit `state='running'` + `attempt_id` + `owner_worker_ref` **before** the
handler runs; finalize re-locks and CAS-verifies `attempt_id`; a stale
owner's finalize fails closed (companion §6 invariants).

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
  used as `compareQuantity`, per `(inventory_item_id, location_id)` binding
  identity (RA-019 honored), plus the Odoo source quantity and the recorded
  source-of-truth decision (RA-021 honored).
- **Fulfillment create:** the FulfillmentOrder GID, per-line remaining
  quantities read from Shopify immediately before send [Fact — FO
  `lineItems` carry remaining quantities, capture §6.2], location match
  (RA-023 honored).
- **Product export:** the product binding snapshot version / write-date and
  the identifier (`id`/`handle`/`customId`) that `productSet` will upsert
  by [Fact — capture §10].

## 4. Request fingerprint + mutation-domain reconciliation matrix

### 4.1 Request fingerprint [Proposed decision — L2-D5]

`request_fingerprint = SHA-256(normalized GraphQL document ‖ canonical-JSON
variables)`, with volatile fields (timestamps, the idempotency key itself)
excluded from normalization. Purpose: (a) detect that a retry is byte-wise
the *same* intent (safe to reuse the persisted Shopify idempotency key);
(b) audit trail without storing payloads (hashes carry no PII, §12).

### 4.2 The matrix — one row per MVP mutation [Proposed decision — L2-D6]

All idempotency-capability claims below are [Fact], sourced from
[`shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md`](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)
§6.5, §9, §10, §11 (accessed 2026-07-16, API 2026-07); reconciliation
strategies are [Recommendation].

| Mutation | Scopes | Idempotency capability | Fingerprint basis | Reconciliation read | Retry after `uncertain` | Fail-closed rule |
|---|---|---|---|---|---|---|
| `inventorySetQuantities` | `write_inventory` | **Mandatory `@idempotent` UUID key (24h, cached response)** + `compareQuantity` CAS — idempotent + CAS = strongest class | items/locations/quantities/compare values | `InventoryLevel.quantities(names)` per item+location | Yes — reuse persisted key within 24h; after 24h re-read then re-issue with fresh compare | CAS mismatch or expired key without fresh read → no send |
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
| **`THROTTLED`** | **NOT uncertain — the request was not executed** [Fact — throttle returns error code `THROTTLED` with `throttleStatus`; recommended backoff 1s, capture §11] | `failed_clean`, retry-eligible with backoff (§10) |
| HTTP 5xx | Ambiguous (may have executed) | `uncertain` |
| GraphQL `userErrors` | Clean remote rejection — classified via existing 16-class taxonomy [Fact — DEC-009] | `failed_clean` |
| Ambiguous/partial `userErrors` (mutation returns both effect and errors) | Ambiguous | `uncertain` |
| Worker crash between send and outcome commit | Ambiguous (found by sweep, §2/§9) | `uncertain` |
| Clean success response | Applied | `succeeded` + evidence refs |

### 5.2 Reconciliation reads as first-class jobs [Proposed decision — L2-D8]

A reconciliation read is its own job (`job_type` registered
`remote_read_replay_safe` — reads are replay-safe by the accepted Layer 1
contract), linked to the attempt it resolves. It executes the matrix row's
"reconciliation read", decides **applied / not-applied / inconclusive**, and
updates the attempt record: applied → attempt `succeeded` (evidence refs =
the read's proof), job finalizes without re-send; not-applied → attempt
`failed_clean`, job becomes retry-eligible per §5.3.

### 5.3 Retry eligibility [Proposed decision — L2-D9]

- `failed_clean` → normal DEC-009 retry policy (class-based, bounded).
- `uncertain` → **reconcile-then-retry only**; no retry path exists that
  does not pass through a completed reconciliation decision.
- Reconciliation **inconclusive after N attempts** (proposed N = 3,
  config-tunable) → `blocked_manual_review` /
  `manual_review_subreason='duplicate_risk'` [Fact — value exists,
  companion §7], with the attempt record and reconciliation evidence
  attached.

## 6. Terminal failure, manual review, operator override

**[Proposed decision — L2-D10]** `blocked_manual_review` presents the
attempt record (intent, preconditions, fingerprint, evidence refs).
A new **Administrator-only, audited override** lets an operator mark an
uncertain attempt `resolved_applied` or `resolved_not_applied` **with a
mandatory reason**, logged append-only via the existing `job.log` mechanism
[Fact — append-only redacted log exists]. The override **never edits remote
state silently** — it only records the operator's judgment locally; any
corrective Shopify action is a new, ordinary, fully-wrapped mutation job.
Operator-authorized retry remains the one path that may re-attempt a
`remote_effect_not_replay_safe` job (companion §6, last row) — now further
gated: the retry still runs through the attempt wrapper with a fresh
`attempt_id`.

## 7. Disconnect / credential replacement / connection generation

**[Proposed decision — L2-D11]** Every attempt record binds to the job's
`expected_connection_generation` [Fact — field exists; stale-generation
jobs never execute under existing admission]. On a generation bump
(credential replacement/reconnect):

- In-flight `uncertain` attempts are routed to reconciliation **under the
  new generation** before any mutation domain resumes — the reconciliation
  read runs with current credentials against the same store identity.
- Stale-generation mutation jobs never execute [Fact — existing admission
  behavior, unchanged].
- Disconnect quiescence semantics are untouched (§15); the sweep defers to
  quiescence (§2 timeout ordering).
- [Open question] If the store identity itself changed (not just
  credentials), reconciliation evidence may not be comparable —
  route to manual review; exact detection criteria to be fixed at
  acceptance.

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
structurally prevented per companion §6's invariant list (attempt_id CAS).

## 9. Crash recovery

Restart with a committed `running` + `transport_attempted = true` row: the
stale-owner sweep (§2) finds it after timeout and routes to reconciliation —
companion §6 rows 2–3 ("during transport" and "after response, before
commit" deliberately collapse to the same conservative handling). With
`transport_attempted = false`, safe requeue. No in-memory state is consulted
(hard rule 3); the sweep is purely row-driven and cron-scheduled, so it
survives any process death.

## 10. Remote rate limiting and userErrors

- **`THROTTLED` = not executed** [Fact — capture §11]: record
  `failed_clean` (not uncertain), retry with backoff honoring
  `throttleStatus.restoreRate` / `currentlyAvailable` (restore rates
  100–2000 pts/s by plan; mutations cost 10 [Fact]); recommended minimum
  backoff 1s [Fact — quote]. The persisted idempotency key (where present)
  is reused on the throttle retry — same intent, same key.
- **userErrors** are clean failures, classified via the existing 16-class
  taxonomy [Fact — DEC-009]; no new error class is required for them.
  Partial-effect responses (data + userErrors) classify as `uncertain`
  (§5.1).
- API version pinned to 2026-07; the fall-forward risk on unsupported
  versions [Fact — capture §11] is monitored per the capture's
  recommendation; a version fall-forward observed mid-attempt → treat the
  attempt as `uncertain` (semantics may have shifted).

## 11. Local transaction boundaries — exact commit points

**[Proposed decision — L2-D13]** Four commit points per mutation attempt:

```
C1: CLAIM COMMIT           main txn: try_lock_for_update → state='running',
                           attempt_id, owner_worker_ref → COMMIT
C2: ATTEMPT-INTENT COMMIT  main txn (fresh, pre-network): attempt row created
                           (intent, preconditions, fingerprint, idempotency
                           key), transport_attempted=true → COMMIT
    [no DB lock held beyond C2]
NET: network call          outside any DB transaction/lock; call.lease
                           admission (side txn, FOR SHARE, committed before
                           network) unchanged [Fact]
C3: OUTCOME COMMIT         fresh txn: re-lock, CAS attempt_id, write outcome
                           + evidence + terminal/retry state → COMMIT
```

**Choice and justification:** the intent commit (C2) is a **pre-network
commit of the main cursor**, not a side transaction. Justification: (a) the
no-lock-across-network rule is satisfied — committing C2 releases all locks
before the send, and the pattern is exactly Odoo's documented cron
`_commit_progress` per-item durability idiom that `_drain_one` already uses
[Fact — companion §2.3 evidence; PR #163's per-job-commit pattern];
(b) unlike the `call.lease` side transaction (which exists so an
*independent* observer can see in-flight traffic), the attempt intent has no
reader that needs it visible mid-transaction other than post-rollback
recovery — and a committed main-cursor write survives rollback of the
*subsequent* transaction just as durably; (c) a side transaction would put
attempt-intent and job-state writes on different cursors, creating a
new consistency seam for no benefit. Option A already establishes the
multiple-commits-per-job precedent (companion §4).

**PG failure between points — recovery table:**

| Failure window | Durable state | Recovery |
|---|---|---|
| Before C1 | nothing | ordinary re-claim |
| C1→C2 | running + attempt_id, no attempt row / transport_attempted=false | sweep or recovery: safe requeue (fresh attempt_id) |
| C2→NET (crash before send) | intent committed, transport_attempted=true | conservative: treated as post-send → reconciliation (cannot distinguish; companion §6 row 3 rationale) |
| NET→C3 | intent committed, no outcome | reconciliation (sweep or 40001-recovery branch, §8/§9) |
| During C3 (40001/lock timeout) | intent committed, transport done | §8 branch: transport_attempted=true → reconciliation |
| After C3 | outcome committed | terminal/retry per outcome; done |

## 12. Audit evidence, retention, upgrade, uninstall, rollback

**[Proposed decision — L2-D14]**

- **Audit:** attempt records + `job.log` entries carry identifiers, counts,
  and reasons only — payload bodies are never stored; existing redaction
  rules apply [Fact — append-only redacted log exists]. Fingerprints are
  SHA-256 hashes; **no PII** is derivable from them.
- **Retention:** attempt rows for **terminal** jobs are pruned by the
  existing retention sweep integration after a configurable window
  (proposed default 180 days, aligned with job retention); a `running`
  job's attempt row is never a cleanup candidate (companion §6 invariant).
- **Upgrade:** purely **additive** — three job fields + one new model; no
  data migration of existing rows (all historical jobs have
  `transport_attempted=false` semantics vacuously). Standard Odoo
  additive-field upgrade; no pre/post migrate script anticipated.
- **Uninstall:** DEC-030 alignment — attempt evidence follows the same
  export-then-drop policy as other connector audit data: offered for export
  during the uninstall flow, then dropped with the module's models.
  [Open question] confirm DEC-030's exact export format applies unchanged.
- **Rollback:** before any mutation domain ships, the feature rolls back
  cleanly (drop fields/model — nothing depends on them). **After** a
  mutation domain has run, the attempt table is **retained as evidence**
  even if the feature is disabled; rollback then means disabling mutation
  job types (fail-closed registry makes them non-executable), never
  deleting attempt history.

## 13. Performance and test strategy

**Performance [Inference]:** ~2 extra commits per mutation (C1 already
exists in Option A's design; C2 and the attempt-row insert are new) — small,
bounded, and per-mutation, dwarfed by the network round-trip. Batching
interplay: batched mutations (e.g. `inventorySetQuantities` with multiple
quantities) get **one** attempt record per request, with per-item evidence
in `remote_evidence_refs`; bulk operations (`bulkOperationRunMutation`,
per-row `@idempotent` [Fact — capture §11]) are out of MVP scope and would
need a per-row attempt design before use ([Open question]). PB alignment:
the DEF-PB-1/SRR-03 performance-baseline observations are re-measured in the
runtime-proof pass below.

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
5. **Source guards:** an AST guard mirroring the existing
   `execute_business` guard pattern [Fact — pattern exists]: **no Shopify
   mutation call site outside the attempt wrapper** — any GraphQL document
   containing `mutation` issued by the API client must originate from the
   wrapper, enforced by static test.
6. **Runtime proof (blocking for acceptance of each mutation wave):**
   Odoo.sh multi-worker proof at exact committed head — Worker B cannot
   execute a handler Worker A durably owns; sweep-driven reconciliation
   observed on a real killed worker; zero residue; no secret leakage.

## 14. Decisions requiring acceptance before implementation

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
DEC-009/DEC-010/DEC-011/DEC-025/DEC-030/DEC-031; capture file 2026-07-16
(§1, §2, §6.2, §6.5, §6.6, §9, §10, §11); rejected-approaches log
RA-001…RA-024 (checked, none re-proposed); SRR-03/04/09.*
