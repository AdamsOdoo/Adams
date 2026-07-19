# DEC-037 — Wave 3 Gate B: Task 013/013B Inventory Readiness

- **Status: REVISED — RESUBMITTED FOR CONTROL-ROOM GATE B ACCEPTANCE
  (Revision 2, 2026-07-19).** Originally produced 2026-07-19 by the Gate B
  planning session (this session), based on `mvp/program-integration` @
  `3a2043cb8d45a4b9bc7bdb3ea39b58515e706da9` (PR #177 merge commit).
  Revision 1 was reviewed by the control room on PR #179 and returned
  **REVISE, NOT REJECTED** (comment
  [`5015619162`](https://github.com/AdamsOdoo/Adams/pull/179#issuecomment-5015619162)).
  This revision applies every binding correction in that comment. **Claude
  did not accept its own package** in Revision 1 and does not in Revision
  2. Acceptance authority: product owner + ChatGPT control room, exactly
  as DEC-036.
- **Decision owner (candidate author, not acceptor):** Claude, the Gate B
  planning/contradiction-resolution/documentation worker, per this
  session's governing tasks and CLAUDE.md §13. Sol/"GPT-5.6 Sol" is the
  Task 013/013B implementation worker (not yet issued a prompt — see
  [`../06-prompts/sol-wave-3-task-013-locked-prompt.md`](../06-prompts/sol-wave-3-task-013-locked-prompt.md)
  and
  [`../06-prompts/sol-wave-3-task-013b-locked-prompt.md`](../06-prompts/sol-wave-3-task-013b-locked-prompt.md),
  both LOCKED, unissued).
- **Scope:** closes every remaining inventory-planning contradiction named
  by DEC-036 Part 0.5 ("Gate B / Task 013 corrections carried forward")
  and Part 5 item 11 ("Out-of-scope document corrections"), the
  contradictions this session found in Revision 1 by direct inspection of
  the Task 013/013B packets and the inventory operating model, and — in
  this revision — the six binding corrections in comment `5015619162`.
  This record does **not** reopen any DEC-036 decision (D1–D38) and does
  **not** reopen Gate A — it propagates those decisions, unchanged, into
  the inventory domain's own documents, and settles the domain-specific
  questions DEC-036 explicitly left to a Gate B session (mutation-domain
  matrix rows, job-contract vocabulary, activation sequencing).
- **Relationship to DEC-036:** DEC-036 is the generic Layer 2 substrate
  decision (Stage 0). This record is the domain-specific application of
  that substrate to the two Shopify mutations Task 013 issues
  (`inventorySetQuantities`, `inventoryActivate`) and the explicit
  non-application of Layer 2 to Task 013B. Where this record and DEC-036
  overlap, DEC-036 governs the substrate mechanism and this record governs
  the domain's use of it — they must never be read as alternatives.
- **Evidence base:** unchanged from Revision 1 (direct inspection of
  DEC-036 full text, the accepted Layer 2 design doc, the Wave 3 DoR, the
  Task 013/013B packets, the inventory operating model, the
  reconnect/backfill policy, the reconnect UAT matrix, the MVP acceptance
  matrix, the Stage 0 packet, the locked Stage 0 Sol prompt), plus one
  additional narrow official-source verification performed in this
  revision (§2) and direct re-inspection of PR #178's current, factual
  state (§13).

---

## 1. Contradiction inventory and disposition (Pass 1, Revision 1)

Every contradiction found between the accepted DEC-036 Layer 2 substrate
and the pre-existing inventory-domain documents, with its binding
resolution. Rows C1–C7 and C9–C13 are unchanged from Revision 1. **C8 is
corrected in this revision** — its Revision 1 resolution proposed a
same-job, two-sequential-attempt design that the control room rejected
(comment `5015619162`, binding correction 1); the corrected resolution is
struck through and replaced below, per this project's established
correction convention (do not silently rewrite; mark superseded, state
the correction).

| # | Original document / section | Conflicting document / section | Binding resolution | Corrected document | Test/implementation implication |
|---|---|---|---|---|---|
| C1 | `inventory-operating-model.md` §4.4 heading "compareQuantity CAS" and body, citing `compareQuantity`/`ignoreCompareQuantity` as the live field | DEC-036 D12 (fact: `changeFromQuantity` is the only current CAS field, 2026-04+) | `changeFromQuantity` is the sole current-facing CAS field name everywhere in this document set; the "evidence-conflict" framing is retired — Gate A's capture already resolved it as a Fact, not an open conflict | `inventory-operating-model.md` §4.4 | Static test: no `addons/shopify_connector_inventory/**` file references `compareQuantity`/`ignoreCompareQuantity` |
| C2 | `task-013-inventory-sync-implementation-packet.md`'s §"CAS via `compareQuantity`" addendum heading | DEC-036 D12; DEC-036 Part 5 item 11 | Heading and rationale corrected to `changeFromQuantity`; the 2026-07-16 "evidence conflict" framing removed (resolved, not open) | `task-013-inventory-sync-implementation-packet.md` §A.2 | Same static test as C1 |
| C3 | `inventory-operating-model.md` §4.3/§9 batching text | DEC-036 D4 (one pair per request, no `quantities[]` batching in Wave 3 MVP) | One-pair-per-request only for Wave 3 MVP; batching text rewritten as explicitly out of scope | `inventory-operating-model.md` §4.3/§9 | Static/AST test: no call site constructs a `quantities[]` array with length > 1 |
| C4 | `inventory-operating-model.md` §10 ("Partial failures") describing per-entry `userErrors` batch routing | DEC-036 D4 (no batching) | Rewritten for one-pair-per-request | `inventory-operating-model.md` §10 | Removes a batching-shaped test expectation |
| C5 | Task 013 packet D-013-1(b)/D-013-3: `last_push_idempotency_key`/`last_push_params_hash` on the binding row | DEC-036 D6 (idempotency key attempt-owned, never binding-owned) | Both fields removed from the binding schema; the key and both fingerprints live exclusively on `shopify.connector.mutation.attempt` | `task-013-inventory-sync-implementation-packet.md` D-013-1(b)/D-013-3/D-013-9 | Test: no code path reads `last_pushed_available`/`last_pushed_at` to decide idempotency-key reuse or retry eligibility |
| C6 | Task 013 packet D-013-6: unexplained Shopify-side drift "pushed over only after being logged" | DEC-036 Part 0.5 item 3 (review-case-first, no automatic overwrite) | Unexplained drift creates a review case and blocks the pending push until reviewed | `task-013-inventory-sync-implementation-packet.md` D-013-6/D-013-9; `inventory-operating-model.md` §5 | Test: induced unexplained-drift fixture asserts a review case is created and the pending push does not execute until cleared |
| C7 | Task 013 packet D-013-3: CAS-stale routes to `concurrency_race_conflict` with no explicit retry bound | Task master prompt §9.A; inventory-operating-model.md §4.4 proposed bounded retries (3) | Bounded retry count = 3; each retry is a new Layer 2 attempt; after 3 mismatches → `blocked_manual_review`/`binding_conflict` | `task-013-inventory-sync-implementation-packet.md` D-013-3/D-013-9 | Test: 3-strikes CAS-stale fixture asserts review-case routing on the 4th mismatch |
| C8 | Task 013 packet D-013-3: `inventoryActivate` invoked inline inside the same handler/attempt as the `inventorySetQuantities` retry, with no explicit Layer 2 wrapper, no explicit second attempt/idempotency key | DEC-036 Hard Rule 1/D16/D37 (every Shopify mutation call site must be inside the Layer 2 wrapper); Gate A binding: one mutation job : one Shopify mutation request : one attempt row | ~~`inventoryActivate` is its own mutation domain, its own attempt, own idempotency key, own fingerprints — never combined with the `inventorySetQuantities` attempt, but both run as two sequential attempts inside the same `inventory_push_sync` job (Revision 1 §5).~~ **Superseded, Revision 2 (comment `5015619162` binding correction 1/2):** `inventory_activate` and `inventory_set_quantities` are each their **own separate mutation job type** (`job_type == mutation_domain` for each), never two attempts inside one job; `inventory_push_sync` is demoted to an orchestration/read-only job that enqueues at most one mutation job per dispatch. Full job model in §5 below | `task-013-inventory-sync-implementation-packet.md` D-013-3/D-013-6/D-013-9 (rewritten, Revision 2); new matrix rows, §4 below | Test: activation and set-quantities are asserted to be two distinct **jobs** (distinct `job_type`, distinct job IDs), each with its own single `attempt_token`/idempotency-key value — never one job executing two mutations |
| C9 | `wave-3-definition-of-ready.md` §5 item 3 flags §4.4 as needing correction "in a future Gate B session" | This session (Gate B) | Flag closed — corrected in Revision 1 | `wave-3-definition-of-ready.md` §5 | N/A — status update only |
| C10 | No document defined the exact `manual_review_subreason` values this domain adds, nor the exact pair-serialization convention | DEC-036 D18/D28/D6/D17 (generic subreasons); D14 (generic `operation_scope_key` convention) | Domain vocabulary frozen — §7; pair-serialization identity frozen — §6 (Revision 2 renames/re-derives the exact key literal per comment `5015619162` §5) | `task-013-inventory-sync-implementation-packet.md` D-013-9; locked Task 013 prompt | Test: job-contract vocabulary test enumerated in §7 |
| C11 | Task 013B packet did not explicitly state its own Layer-2-non-applicability | This session's governing task | Explicit statement added to the Task 013B packet itself | `task-013b-initial-inventory-baseline-packet.md` (§0) | N/A — documentation completeness |
| C12 | `reconnect-catchup-backfill-policy.md` §4.4 (Inventory): "pushes resume only with fresh `compareQuantity` bases" | DEC-036 D12 | `changeFromQuantity` | `reconnect-catchup-backfill-policy.md` §4.4 | Same static test as C1 |
| C13 | `reconnect-backfill-uat-matrix.md` UAT-RB-2.6: "pushes resume only with fresh `compareQuantity` bases" | DEC-036 D12 | `changeFromQuantity` | `reconnect-backfill-uat-matrix.md` UAT-RB-2.6 | Same static test as C1 |

No contradiction above disappears without the recorded resolution in its
row; every corrected document is listed in this session's governing
task's allowed-files list and was in scope to fix.

---

## 1A. Revision 2 — control-room binding corrections (Pass 3, closes review round 1)

Six binding corrections from comment `5015619162`, each with disposition
in this revision. None of these reopen Gate A or DEC-036; all are
corrections to this record's own Revision 1 domain-specific design.

| # | Binding correction (comment `5015619162`) | Disposition in Revision 2 |
|---|---|---|
| 1 | One mutation job means one mutation only — `inventoryActivate`/`inventorySetQuantities` must be two separate mutation jobs, not two attempts inside `inventory_push_sync` | Applied. New job model, §5. `inventory_push_sync` demoted to orchestration/read-only; `inventory_activate` and `inventory_set_quantities` are each a standalone mutation job type |
| 2 | Exact Stage 0 compatibility — mutation job types must be exactly `inventory_activate`/`inventory_set_quantities`, `job_type == mutation_domain`, `inventory_push_sync` kept outside the mutation registry | Applied. §4 (matrix), §5 (job model), §7 (job contract) |
| 3 | No message-string idempotency classification for `inventoryActivate` | Applied. §4 row 2 no longer proposes message-matching as a production classification path; removed entirely, replaced with a uniform payload-shape rule (§4 row 2, §9) |
| 4 | Safe reconciliation verdicts — freshness/ABA protection for `inventory_set_quantities` `not_applied`; explicit three-way verdict for `inventory_activate` | Applied. §4 rows 1 and 2, reconciliation-verdict cells rewritten |
| 5 | Job consequences must be explicit for every direct clean failure | Applied. New §9, job/mutation-consequence contract |
| 6 | Factual Stage 0 status — PR #178 exists, open/draft, at the stated head; correct stale "no PR" wording | Applied. New §13; every stale "no PR yet" statement in this record and the shared trackers is corrected |

---

## 2. Official-source verification performed this session

Per this session's governing tasks, the accepted Gate A capture
(`shopify-layer2-mutation-safety-refresh-2026-07-18.md`) is the default
source basis and was **not** re-fetched for facts it already establishes
(CAS field name, `@idempotent` mandatory scope/timing, THROTTLED
non-guarantee, `InventoryLevel.quantities` shape, Odoo 19 isolation
level, the CAS mismatch code `CHANGE_FROM_QUANTITY_STALE`, the two
idempotency-defect codes' message text). Three narrow gaps that capture
did not cover — each directly needed to complete a matrix cell without a
"TBD" — were verified live against `shopify.dev`:

1. **`inventoryActivate` default quantities** (Revision 1, 2026-07-19).
   Source: https://shopify.dev/docs/api/admin-graphql/2026-07/mutations/inventoryactivate
   — Accessible. Quote: *"If you don't specify quantities, then
   `available` and `onHand` default to zero."* **[Fact.]**
2. **`inventoryActivate` error-reporting shape** (Revision 1, 2026-07-19).
   Source: https://shopify.dev/docs/api/admin-graphql/2026-07/objects/UserError
   — Accessible. `UserError` has exactly two fields, `field` and
   `message` — no `code` field, unlike
   `InventorySetQuantitiesUserErrorCode`. **[Fact.]**
3. **Complete `InventorySetQuantitiesUserErrorCode` enum** (Revision 2,
   2026-07-19, added because it is needed to correctly resolve binding
   correction 1's `ITEM_NOT_STOCKED_AT_LOCATION` handling and because
   Revision 1's matrix row 1 cited a partial list without capturing the
   full enum in this repository's own source materials — a citation gap
   this revision closes; no new source-materials file was created because
   this revision's allowed-files list authorizes no new file, so the full
   quote is captured directly in this decision record instead). Source:
   https://shopify.dev/docs/api/admin-graphql/2026-07/enums/InventorySetQuantitiesUserErrorCode
   — Accessible, 2026-07-19. All 17 values, in order: `CHANGE_FROM_QUANTITY_STALE`
   ("The changeFromQuantity value does not match persisted value."),
   `COMPARE_QUANTITY_REQUIRED` (legacy field, historical),
   `COMPARE_QUANTITY_STALE` (legacy field, historical),
   `IDEMPOTENCY_CONCURRENT_REQUEST` ("This request is currently in
   progress, please try again."), `IDEMPOTENCY_KEY_PARAMETER_MISMATCH`
   ("The same idempotency key cannot be used with different operation
   parameters."), `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` ("A previous
   request with this idempotency key failed. Retry with a new idempotency
   key."), `INVALID_INVENTORY_ITEM` ("The specified inventory item could
   not be found."), `INVALID_LOCATION` ("The specified location could not
   be found."), `INVALID_NAME` ("The quantity name must be either
   'available' or 'on_hand'."), `INVALID_QUANTITY_NEGATIVE` ("The
   quantity can't be negative."), `INVALID_QUANTITY_TOO_HIGH` ("The total
   quantity can't be higher than 1,000,000,000."),
   `INVALID_QUANTITY_TOO_LOW` ("The total quantity can't be lower than
   -1,000,000,000."), `INVALID_REASON` ("The specified reason is
   invalid."), `INVALID_REFERENCE_DOCUMENT` ("The specified reference
   document is invalid."), **`ITEM_NOT_STOCKED_AT_LOCATION`** ("The
   specified inventory item is not stocked at the location."),
   `NO_DUPLICATE_INVENTORY_ITEM_ID_GROUP_ID_PAIR` ("The combination of
   inventoryItemId and locationId must be unique."),
   `NON_MUTABLE_INVENTORY_ITEM` ("The specified inventory item is not
   allowed to be adjusted via API. Example: if the inventory item is a
   parent bundle."). **[Fact.]** `ITEM_NOT_STOCKED_AT_LOCATION` exists and
   is folded into §4 row 1 and §9 per binding correction 1's exact
   handling rule (fail-closed to review/re-orchestration, never an inline
   activation trigger).

No other official-source re-verification was performed in this revision
— this is a documentation-correction batch, not another research round,
per this revision's governing task.

---

## 3. Binding decisions propagated without reopening

The fourteen decisions from Revision 1's governing task §7 remain binding
and are propagated unchanged. Pointers to items 7 and 8 are updated to
this revision's rewritten job-model section.

| # | Decision | DEC-036 source | Applied in |
|---|---|---|---|
| 1 | CAS input field = `changeFromQuantity` | D12 | Task 013 D-013-3, §4 row 1 |
| 2 | CAS mismatch error = `CHANGE_FROM_QUANTITY_STALE` | D12 | Task 013 D-013-9, §4 row 1 |
| 3 | Idempotency: attempt-owned, request-level, persisted by Layer 2, not binding-owned | D6 | Task 013 D-013-1(b)/D-013-9 (C5) |
| 4 | Mutation granularity: one item+location pair, one request, one attempt, no batching | D4 | Task 013 D-013-6/D-013-9 (C3/C4) |
| 5 | Unexplained Shopify drift: review-case-first, no silent overwrite | Part 0.5 item 3 | Task 013 D-013-6 (C6) |
| 6 | Task 013 mutations all pass through Layer 2; no direct API-client mutation call | D16/D37, Hard Rule 1 | Task 013 D-013-9 (C8); locked Task 013 prompt |
| 7 | `inventorySetQuantities`: separate mutation-domain registration, own job type, own reconciliation strategy, mandatory Layer 2 wrapper | D15/D16 | §4 row 1, §5 |
| 8 | `inventoryActivate`: also a mutation, own job type, mandatory Layer 2 wrapper, own reconciliation strategy | D16/D37 | §4 row 2, §5 |
| 9 | Task 013B: no Layer 2, Shopify reads, guarded local Odoo writes, no mutation, separate Stage 2 | Part 0.5 item 5; Stage 0 packet §2 | §8; Task 013B packet §0 |
| 10 | Reconnect: reconciliation read before first post-reconnect push, never blind | inventory-operating-model.md §11; reconnect policy §4.4 | §12 |
| 11 | Standing direction: Odoo authoritative after onboarding, no standing Shopify→Odoo stock sync | DEC-010 (unchanged) | §11/§12 |
| 12 | Shopify quantity writes: `available` only, never `committed`, never `on_hand` | DEC-010/RA-018 (unchanged) | §11; `inventoryActivate` row never sends `onHand` as nonzero |
| 13 | Negative quantity: clamp to zero, log/review evidence, never send negative `available` | inventory-operating-model.md §7 (unchanged) | §11 |
| 14 | First push: preview, explicit confirmation, recorded actor/time/quantity, no unconfirmed mutation | Task 013 D-013-4 (unchanged); tightened by §6 | Task 013 D-013-4/D-013-9 |

---

## 4. Complete Layer 2 inventory mutation-domain matrix

Two rows — `inventory_set_quantities` and `inventory_activate` — each a
**standalone mutation job type**, per binding corrections 1 and 2. No
cell says "implementation choice," "TBD," or equivalent.

### Row 1 — `inventory_set_quantities`

| Field | Value |
|---|---|
| `job_type` | **`inventory_set_quantities`** (Revision 2 — was `inventory_push_sync` in Revision 1; corrected per binding correction 2: `job_type == mutation_domain` for every mutation job) |
| `mutation_domain` | `inventory_set_quantities` |
| Replay-policy class | `remote_effect_not_replay_safe` (every Shopify mutation is this class by construction) |
| Reconciliation-strategy registry key | `inventory_set_quantities`, registered via `_inherit`+`super()` on `shopify_connector_job_dispatch.py`'s `_get_reconciliation_strategies()` seam (DEC-036 D15) |
| Domain-enable flag | `inventory_domain_enabled` |
| Pair-serialization identity | `inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}` (frozen literal, §6 — shared with the `inventory_push_sync` orchestration job and the `inventory_activate` job for the same pair; this is what `operation_scope_key` is set to for this job type) |
| Business-intent fingerprint inputs | `{mutation_domain: 'inventory_set_quantities', inventory_item_id, location_id, target_quantity}` — excludes `changeFromQuantity` and the idempotency key (DEC-036 D5) |
| Exact-request fingerprint inputs | Normalized `inventorySetQuantities` GraphQL document + exact variables: `name: 'available'`, `reason`, `referenceDocumentUri`, one `InventoryQuantityInput` entry `{inventoryItemId, locationId, quantity, changeFromQuantity}`, plus the `@idempotent(key: ...)` directive value (DEC-036 D5) |
| `preconditions_snapshot` allowlist | `{inventory_item_id, location_id, target_quantity, change_from_quantity, snapshot_taken_at}` (DEC-036 D7) |
| `remote_mutation_intent` allowlist | `{inventory_item_gid, location_gid, mutation_name: 'inventorySetQuantities'}` |
| `remote_evidence_refs` allowlist | `{remote_gids: [...], user_errors: [{code, field}], http_status, graphql_error_codes: [...], throttle_status: {maximumAvailable, currentlyAvailable, restoreRate} \| null}` (DEC-036 D8) |
| Shopify idempotency-key lifecycle | Fresh UUIDv4 per attempt, persisted on `mutation.attempt` at C2 (never on the binding, C5); reused verbatim only for an identical `exact_request_fingerprint` retry within `idempotency_valid_until` (24h minus a configurable local safety margin, provisional 23h) |
| Expected connection generation / store identity | Snapshotted at C2 on the attempt row (DEC-036 D18/D29); reconciliation begins with the store-identity check |
| Job-level bounded CAS-retry field | **`cas_mismatch_count`** (Integer, default 0, new — Revision 2, closes binding correction 5's requirement for an explicit retry-counter source): incremented once per `CHANGE_FROM_QUANTITY_STALE` dispatch outcome; checked at the start of the job's next dispatch |
| Direct `succeeded` evidence | Response has no `userErrors` and the mutation's own returned quantity data reflects the requested `quantity` → `observed_outcome='succeeded'` |
| Direct `failed_clean` evidence — validation/binding codes | `userErrors` containing one of: `INVALID_INVENTORY_ITEM`, `INVALID_LOCATION`, `INVALID_NAME`, `INVALID_QUANTITY_TOO_HIGH`, `INVALID_QUANTITY_TOO_LOW`, `INVALID_REASON`, `INVALID_REFERENCE_DOCUMENT`, `NO_DUPLICATE_INVENTORY_ITEM_ID_GROUP_ID_PAIR`, `NON_MUTABLE_INVENTORY_ITEM` (all confirmed live on `InventorySetQuantitiesUserErrorCode`, §2 item 3). `INVALID_QUANTITY_NEGATIVE` is confirmed-existing but never-triggerable under this connector's clamp-before-send discipline — a defensive test asserts it is never observed. `NON_MUTABLE_INVENTORY_ITEM` routes to `blocked_manual_review`/`binding_conflict`. No blind automatic retry for any of these (§9) |
| Direct `failed_clean` evidence — CAS stale | `CHANGE_FROM_QUANTITY_STALE` → `observed_outcome='failed_clean'`, `error_class='concurrency_race_conflict'`. Bounded retry **permitted**, maximum **3** retries (`cas_mismatch_count < 3`). **Every retry is a new job dispatch of this same job** (Revision 2, corrects Revision 1's phrasing — the job is not re-created, it is redispatched): a new `mutation.attempt` row, a fresh, narrow, single-purpose Shopify read of the pair's current `available`/`updatedAt` (a `remote_read_replay_safe` read performed by this job's own dispatch handler, not a re-run of full `inventory_push_sync` orchestration — this is a CAS pre-read, not a reconnect/drift classification, and does not re-derive the target or re-run first-push/drift/reconnect gates), a fresh `changeFromQuantity`, a fresh exact-request fingerprint, and a fresh idempotency key. The retry also re-reads the binding's current coalesced `pending_target_available` (§10) rather than resending a possibly-stale target. After 3 mismatches (the 4th `CHANGE_FROM_QUANTITY_STALE`) → `blocked_manual_review`/`binding_conflict`, never a 4th retry |
| Direct `failed_clean` evidence — `ITEM_NOT_STOCKED_AT_LOCATION` | **[Fact, §2 item 3]** Confirmed on `InventorySetQuantitiesUserErrorCode`. **Revision 2 correction (binding correction 1):** this is a race/contract exception, not an inline activation trigger — `inventory_push_sync`'s own prior read found (or believed it found) an existing level, but the level was not actually stocked at send time. → `observed_outcome='failed_clean'`, `error_class='remote_precondition_mismatch'`, routes to `blocked_manual_review`/`inventory_location_missing` (the existing accepted subreason for this exact "level not present/not stocked" condition). This job **never** issues `inventoryActivate` inline or in any form. The pending target remains coalesced (§10) unresolved; the pair's next `inventory_push_sync` orchestration job (admitted normally by scan/manual trigger, §5) re-reads Shopify, correctly detects the level is genuinely absent, and — only if `first_push_state='confirmed'` — enqueues a fresh `inventory_activate` job |
| Direct `uncertain` evidence | Network timeout after send; HTTP 5xx; `THROTTLED`; ambiguous/partial `userErrors` (data + errors both present — does not apply cleanly to this mutation's error shape, retained for completeness); `IDEMPOTENCY_CONCURRENT_REQUEST`; worker crash between send and outcome commit (DEC-036 D9/D19/D23/D24) |
| `THROTTLED` handling | `uncertain`, reconcile-first, never auto-classified `failed_clean` (DEC-036 D9) |
| Idempotency-error handling | `IDEMPOTENCY_CONCURRENT_REQUEST` → `uncertain`; `IDEMPOTENCY_KEY_PARAMETER_MISMATCH` / `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` → `idempotency_contract_violation`, `blocked_manual_review`, no automatic retry (DEC-036 D6). These are structured codes on this mutation's own error enum (§2 item 3) — no message-text matching is needed or used for this row |
| Reconciliation read | `InventoryLevel.quantities(names: ["available"])` for the exact pair, including `updatedAt` where the schema exposes it on the returned `InventoryQuantity`; **first** step is the store-identity check (DEC-036 D18) |
| `applied` verdict | Current Shopify `available` equals this attempt's `target_quantity`, **and** `InventoryQuantity.updatedAt` (where present) is not later than this attempt's `transport_at` → `resolution_disposition='applied'`; the effective business state is already achieved regardless of whether this exact attempt or a later one produced it (Revision 2, binding correction 4: applied is about the achieved state, not attribution); no resend |
| `not-applied` verdict — freshness/ABA-safe (Revision 2, binding correction 4) | Current Shopify `available` equals this attempt's own pre-attempt `changeFromQuantity` **and** freshness evidence does **not** show a post-transport change: i.e., `updatedAt`, where present, is **not later than** `transport_at`, and no other evidence (a differing `myshopifyDomain`, a third-party attribution signal) indicates an ABA round-trip or third-party write → `resolution_disposition='not_applied'`; job becomes retry-eligible, a new attempt on next dispatch |
| Inconclusive verdict — freshness/ABA-safe (Revision 2) | Any of: (a) current `available` equals **neither** the pre- nor post-attempt value; (b) current `available` equals the pre-attempt value **but** `updatedAt` is **later** than `transport_at` (an ABA round-trip cannot be ruled out — the value could have changed away and back); (c) freshness evidence is unavailable and attribution to this attempt cannot otherwise be established. **No verdict may depend only on response absence, and a same-value read is never, by itself, treated as proof of not-applied** (this replaces Revision 1's weaker formulation, which did not yet require freshness evidence for the not-applied verdict) → `inconclusive_reconciliation_count` increments under a re-acquired row lock (DEC-036 D17); next reconciliation read scheduled |
| Manual-review subreason | `duplicate_risk` (N=3 inconclusive cap); `store_identity_mismatch`; `idempotency_contract_violation`; `binding_conflict` (`NON_MUTABLE_INVENTORY_ITEM`; persistent CAS divergence after 3 bounded retries); `inventory_location_missing` (`ITEM_NOT_STOCKED_AT_LOCATION`); `no_reconciliation_strategy` (registry lookup failure, should never fire) |
| Retry eligibility | Per the effective-disposition helper (DEC-036 D10), see §9 for the full consequence table |
| First-push interaction | Never fires for a pair whose binding `first_push_state != 'confirmed'` — `destructive_write_guard_blocked`, unchanged |
| Reconnect interaction | Never admitted for a pair until that pair's post-reconnect `inventory_push_sync` reconciliation read has completed (§12) |
| Disconnect interaction | Per DEC-036 D28, unchanged |
| Rollback/disable behavior | Per DEC-036 D36, unchanged |
| Exact tests | `test_inventory_push_mechanics.py` (extended, Revision 2): CAS-stale bounded-retry-then-review (3-strikes) is a **redispatch of the same `inventory_set_quantities` job**, not a new job and not a resumption of `inventory_push_sync`; each redispatch performs its own narrow CAS pre-read (not a full orchestration re-run); `ITEM_NOT_STOCKED_AT_LOCATION` never triggers an inline `inventoryActivate` call in this job — asserted by a static/AST guard that this job's handler contains no `inventoryActivate` call site; `THROTTLED`→`uncertain`; both idempotency-defect codes → `idempotency_contract_violation`/`blocked_manual_review`/no-retry; reconciliation `applied`/`not_applied`/`inconclusive` including an induced ABA fixture (value changes away and back with a later `updatedAt`) asserting `inconclusive`, never `not_applied`; store-identity-mismatch routing; first-push-confirmed gate; binding never stores a Shopify idempotency key or exact-request fingerprint |
| Exact dev-store evidence | Dev-store validation plan scenarios 1–8, 10–12, 17–19 (18 is the new ABA/freshness scenario; 19 is the new `ITEM_NOT_STOCKED_AT_LOCATION` race scenario, both Revision 2) |

### Row 2 — `inventory_activate`

| Field | Value |
|---|---|
| `job_type` | **`inventory_activate`** (Revision 2 — was `inventory_push_sync` in Revision 1; corrected per binding correction 2) |
| `mutation_domain` | `inventory_activate` |
| Replay-policy class | `remote_effect_not_replay_safe` |
| Reconciliation-strategy registry key | `inventory_activate`, its own row, never folded into the set-quantities strategy |
| Domain-enable flag | `inventory_domain_enabled` |
| Pair-serialization identity | `inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}` — same identity as row 1 and the orchestration job for this pair (§6); this job and the `inventory_set_quantities` job for the same pair are never both non-terminal at once (§6) |
| Business-intent fingerprint inputs | `{mutation_domain: 'inventory_activate', inventory_item_id, location_id, initial_available: 0}` |
| Exact-request fingerprint inputs | Normalized `inventoryActivate` GraphQL document + exact variables: `inventoryItemId`, `locationId`, **`available: 0`** (explicit, never omitted), `onHand` omitted (defaults to 0; never sent nonzero), `stockAtLegacyLocation: false` (explicit), plus this job's own `@idempotent(key: ...)` value, distinct from row 1's key |
| `preconditions_snapshot` allowlist | `{inventory_item_id, location_id, initial_available: 0, snapshot_taken_at}` |
| `remote_mutation_intent` allowlist | `{inventory_item_gid, location_gid, mutation_name: 'inventoryActivate'}` |
| `remote_evidence_refs` allowlist | Same D8 shape as row 1; `graphql_error_codes` empty in practice (no dedicated enum, §2 item 2) |
| Shopify idempotency-key lifecycle | Fresh UUIDv4 for this attempt, distinct from the `inventory_set_quantities` job's key; same 24h-minus-margin reuse rule |
| Expected connection generation / store identity | Snapshotted at this job's own attempt's C2, independently of any other job |
| Direct `succeeded` evidence | **[Fact, §2 item 1]** Response returns a non-null `inventoryLevel` and an empty `userErrors` array → `observed_outcome='succeeded'`. The level now exists at `available=0`/`on_hand=0` (this connector explicitly sends `available: 0` rather than relying on the omitted-argument default, so the sent value is always visible in `exact_request_fingerprint`) |
| Direct `failed_clean` evidence — **Revision 2, binding correction 3, replaces Revision 1's message-matching design entirely** | **[Fact, §2 item 2]** `userErrors` is `[UserError!]!`; `UserError` has exactly `field`/`message` — no `code`. Classification is by **payload shape only**: a non-empty `userErrors` array **with a null `inventoryLevel`** → `observed_outcome='failed_clean'`, `error_class='clean_rejection'`, routes to `blocked_manual_review`/`binding_conflict`, **never automatic retry** — this single rule covers every clean-rejection cause this mutation can report, including any idempotency-contract defect Shopify may express through this shape, without needing to distinguish the specific cause (no finer-grained routing is possible or claimed, since no structured code exists). `UserError.message` text **may be captured as redacted diagnostic evidence only** (e.g., in job logs, for human triage) and **must never be used to select an error class, a retry decision, or a manual-review subreason** — Revision 1's proposed case-insensitive message matching for `IDEMPOTENCY_CONCURRENT_REQUEST`/`IDEMPOTENCY_KEY_PARAMETER_MISMATCH`/`IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED`-equivalent text is **withdrawn** — it is unnecessary (the uniform clean-rejection rule already routes any such case to manual review, correctly and safely) and unsafe as a production control surface. **No claim is made that a stable structured idempotency-defect surface exists for `inventoryActivate`** unless directly proven by a future official-source change; if Shopify later adds a dedicated error-code enum for this mutation, this row must be revisited under a further Gate decision, not silently patched |
| Direct `uncertain` evidence | Network timeout after send; HTTP 5xx; `THROTTLED`; **a non-empty `userErrors` array together with a non-null `inventoryLevel`** (ambiguous/partial — the payload itself, not message text, is the classification signal); worker crash between send and outcome commit |
| `THROTTLED` handling | `uncertain`, reconcile-first — identical policy to row 1 |
| Idempotency-error handling | Folded into the uniform clean-rejection rule above; no separate handling, no message matching (Revision 2 removes the Revision 1 open question and its dev-store-deferred verification step entirely — there is nothing left to verify, since the uniform rule requires no cause-specific classification) |
| Reconciliation read | `InventoryLevel.quantities(names: ["available", "on_hand"])` for the pair; same store-identity-first check as row 1 |
| `applied` verdict — Revision 2, binding correction 4, explicit three-way | The level exists (non-null `InventoryLevel`) **and** `available == 0` **and** `on_hand == 0` → `resolution_disposition='applied'` |
| `not-applied` verdict | The level still does not exist for the pair (query returns null/absent) → `resolution_disposition='not_applied'`; job becomes retry-eligible, a new activation attempt on next dispatch |
| Inconclusive verdict | The level exists but `available`/`on_hand` are **not both** 0 — an unexplained non-zero quantity reached the pair between this attempt and the read → `inconclusive_reconciliation_count` increments; **never auto-corrected** |
| Manual-review subreason | `duplicate_risk` (N=3 cap); `store_identity_mismatch`; `binding_conflict` (clean rejection; a nonzero level found during reconciliation) |
| Retry eligibility | Per the effective-disposition helper (DEC-036 D10), see §9 |
| First-push interaction | Enqueued **only** by a fresh `inventory_push_sync` orchestration dispatch (§5) that finds no existing Shopify level for a pair whose binding is `first_push_state='confirmed'` — **never** enqueued directly by an `inventory_set_quantities` job's own outcome (Revision 2, corrects Revision 1: `ITEM_NOT_STOCKED_AT_LOCATION` is handled entirely within row 1 as a fail-closed review case, §4 row 1, §9 — it does not trigger this job) |
| Reconnect interaction | Same admission gate as row 1 |
| Disconnect interaction | Same as row 1 |
| Rollback/disable behavior | Same as row 1 |
| Exact tests | New assertions in `test_inventory_push_mechanics.py`: activation always sends explicit `available: 0`; activation and a subsequent `inventory_set_quantities` job use two distinct job records, `job_type` values, `attempt_token`/idempotency-key values, and are connected only by the shared pair-serialization identity and a fresh orchestration handoff (§5/§6) — never a direct enqueue from one to the other; activation never sends `onHand` nonzero; reconciliation requires both `available`/`on_hand` zero for `applied`; **no code path matches on `UserError.message` text for this mutation** (static/AST guard); a nonzero post-activation level routes to `binding_conflict`, never silently accepted |
| Exact dev-store evidence | Dev-store validation plan scenario 9 (activation, its own standalone job, Revision 2) |

No matrix cell above is "TBD" or "implementation choice."

---

## 5. Job model, orchestration flow, and pair serialization (Revision 2 — replaces Revision 1's same-job sequencing design entirely)

### 5.1 Three job types (binding, comment `5015619162`)

**A. `inventory_push_sync` — orchestration and read job only.**

- Replay policy: `remote_read_replay_safe`.
- Performs **no** Shopify mutation and creates **no** `mutation.attempt`
  row.
- Performs, per dispatch: first-push confirmation checks; reconnect
  read-first checks; the current Shopify level/`available` read; the
  Odoo `free_qty` read; the last-accepted business-state comparison;
  drift classification; target derivation; activation-required
  determination.
- Enqueues **at most one** mutation job per dispatch (either
  `inventory_activate` or `inventory_set_quantities`, never both, never
  neither-then-retry-itself-as-a-mutation).
- Kept **outside** the mutation-domain registry (no `mutation_domain`
  value, no reconciliation-strategy entry, no idempotency key) — it is a
  Layer 1 read job, exactly like the existing generic
  `remote_read_replay_safe` reconciliation reads DEC-036 already defines.

**B. `inventory_activate` — mutation job.**

- `mutation_domain = 'inventory_activate'`; `job_type == mutation_domain`.
- One job, one Shopify request, one Layer 2 attempt, one idempotency key.
- Full contract: §4 row 2.

**C. `inventory_set_quantities` — mutation job.**

- `mutation_domain = 'inventory_set_quantities'`; `job_type ==
  mutation_domain`.
- One job, one Shopify request per dispatch, one Layer 2 attempt per
  dispatch (bounded CAS-retry redispatches this same job, §4 row 1 — it
  does not create a second concurrent job).
- Full contract: §4 row 1.

**No mutation job may execute two Shopify mutations. No job may combine
two conceptually distinct business mutations (activation and a quantity
set) into one execution.** This is distinct from a mutation job's own
bounded self-retry of the *same* mutation after a transient/CAS failure
(an established, generic Layer 2 pattern — DEC-036 D9's `failed_clean`
retry-creates-a-new-attempt-on-next-dispatch mechanism, applied here to
the same job type, same mutation) — that is not "two mutations," it is
one bounded, self-healing retry sequence of one mutation kind. Every
statement in Revision 1 saying `inventory_push_sync` is itself a mutation
job, that it contains both attempts, that both attempts occur inside the
same job claim, or that `current_attempt_token` is overwritten for a
second *different* mutation within one job, is withdrawn.

### 5.2 Orchestration flow (frozen)

1. A trigger (odoo_event/scheduled_sync/manual_sync) or scan coalesces
   the latest Odoo target for one pair (§10).
2. It enqueues or refreshes one `inventory_push_sync` orchestration job
   for that pair (subject to §6's one-non-terminal-job-per-pair rule).
3. `inventory_push_sync` performs the fresh Shopify read and all gates
   (§5.1.A).
4. When the Shopify level exists and the pair is safe to push: enqueue
   one `inventory_set_quantities` mutation job.
5. When the Shopify level does not exist and first push is confirmed:
   enqueue one `inventory_activate` mutation job.
6. `inventory_activate` performs only activation, at explicit
   `available: 0` (§4 row 2).
7. After `inventory_activate` becomes effectively `applied`: the pending
   Odoo target remains coalesced on the binding (§10); this job does
   **not** issue `inventorySetQuantities`; the normal scan/manual trigger
   admits a **fresh** `inventory_push_sync` orchestration job for the
   pair (once the activation job has gone terminal, §6); that fresh job
   re-reads Shopify (now finding the level present at zero) and, per
   step 4, enqueues `inventory_set_quantities`.
8. `ITEM_NOT_STOCKED_AT_LOCATION` received by `inventory_set_quantities`
   is not an inline activation trigger — it routes fail-closed to review
   /re-orchestration (§4 row 1, §9), never issuing `inventoryActivate`
   from the same job.

No direct mutation chaining is permitted — a mutation job never enqueues
another mutation job; only `inventory_push_sync` enqueues mutation jobs,
and only after its own fresh read and gates.

### 5.3 Pair serialization and handoff (binding, comment `5015619162` §5)

- **Pair-serialization identity (frozen literal):**
  `inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}`.
  All three job types (`inventory_push_sync`, `inventory_activate`,
  `inventory_set_quantities`) for the same pair use this exact identity
  as their `operation_scope_key`. (Cross-reference for implementers: the
  Task 013 packet's `shopify_inventory_item_gid` and
  `location_mapping_id → shopify_gid` fields are the concrete sources for
  `inventory_item_gid`/`shopify_location_gid` in this literal.)
- **Admission rule:** only one non-terminal inventory job (of any of the
  three types) may exist for a given pair-serialization identity at a
  time. A new job for the same pair is refused admission (not silently
  duplicated, not silently dropped — refused, and any pending target
  update instead coalesces onto the binding, §10) while one is
  non-terminal.
- **Handoff rule:** the current job must transition to a terminal state
  (`succeeded` effective disposition, `failed_clean` exhausted-and-routed
  to review, or `blocked_manual_review`) **before** the next phase job
  (an orchestration re-read after activation, or a mutation job enqueued
  by an orchestration read) is created. Terminalization of the current
  job and enqueue of the next phase job occur **atomically**, in the same
  database transaction, under a row lock on the pair's binding record
  (`shopify.connector.inventory.level.binding`), held for the duration of
  the handoff.
- **Rollback guarantee:** if that transaction rolls back for any reason,
  both the current job's terminal state **and** the next phase job's
  existence roll back together — the system is left exactly as if the
  handoff had not been attempted (no orphaned child job, no job silently
  stuck non-terminal with no successor).
- **Concurrency proof required:** the Task 013 implementation must
  include a genuine independent-PostgreSQL-connection concurrency test
  (mirroring the Stage 0 pattern already proven for job claims) proving
  that two concurrent transactions attempting to create the next phase
  job for the same pair cannot both succeed — exactly one wins, the other
  observes the pair already non-terminal (or the already-created
  successor) and refuses. This is a **named, required test**, not an
  implementation choice left open (Task 013 §5, `test_inventory_push_mechanics.py`).
- **Stage 0 seam, not a Stage 0 change:** where the existing Layer 2
  substrate derives `operation_scope_key` from job identity (DEC-036
  D14), Task 013 adapts through that **existing, accepted domain
  extension seam** — it does not modify Stage 0's architecture, schema,
  or protocol. The pair-serialization identity above is this domain's own
  value for that existing generic field.

---

## 6. First-push guard (tightened, Revision 2 wording update)

- Preview (`inventory_first_push_preview`) and explicit confirmation
  (`action_confirm_first_push()`, recording actor/time/preview quantity)
  are required before `inventory_push_sync` is permitted to enqueue
  **either** mutation job type for a pair (Task 013 D-013-4, unchanged in
  substance; Revision 2 corrects the mechanism — the gate is checked by
  the orchestration job at enqueue time, not "inside" a combined mutation
  job).
- First push never bypasses Layer 2 — both `inventory_activate` (if
  needed) and `inventory_set_quantities` run through the full wrapper as
  their own standalone jobs, exactly like every later push.
- Activation never creates an unreviewed nonzero stock state: it always
  requests an explicit `available: 0`, and its own reconciliation read
  (§4 row 2) must show `applied` before a **fresh** orchestration job
  (§5.2 step 7) may enqueue the set-quantities job.

---

## 7. Task 013 job contract — frozen (closes contradiction C10, updated Revision 2)

- **`job_type` values (six — Revision 2 adds two):**
  `inventory_push_sync` (orchestration/read-only, `remote_read_replay_safe`),
  `inventory_push_scan`, `inventory_first_push_preview`,
  `inventory_location_sync` (unchanged, existing four), plus
  **`inventory_activate`** and **`inventory_set_quantities`** (new,
  Revision 2 — each a standalone mutation job type, `job_type ==
  mutation_domain`). No new job type is added for reconciliation reads —
  those continue to use the existing generic `remote_read_replay_safe`
  job type (DEC-036 D14).
- **`job_source` values (unchanged, Task 013 D-013-6):** `odoo_event`
  (`trigger_origin='inventory_stock_change'`), `scheduled_sync`,
  `manual_sync`, `export_preview_dry_run`.
- **Error/manual-review-subreason vocabulary:**
  - `inventory_location_missing` (existing — unmapped item/location;
    Revision 2 also routes `ITEM_NOT_STOCKED_AT_LOCATION` here)
  - `binding_conflict` (existing — stale/recreated Shopify identity;
    extended to also cover: `NON_MUTABLE_INVENTORY_ITEM`, persistent CAS
    divergence after 3 bounded retries, unexplained inventory drift, and
    a nonzero post-activation level or activation clean-rejection)
  - `destructive_write_guard_blocked` (existing — unconfirmed first-push
    row)
  - `duplicate_risk` (DEC-036 D17, generic — N=3 inconclusive cap, both
    matrix rows)
  - `store_identity_mismatch` (DEC-036 D18, generic)
  - `idempotency_contract_violation` (DEC-036 D6, generic; `inventory_set_quantities`
    row only — `inventory_activate` folds any equivalent case into
    `binding_conflict`'s uniform clean-rejection rule, §4 row 2)
  - `no_reconciliation_strategy` (DEC-036 D16, generic — should never
    fire once both matrix rows are registered)
- **Pair-serialization identity convention:** §5.3, frozen literal
  `inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}`
  for all three inventory job types on a pair; reconciliation jobs use
  the existing generic convention
  `reconcile:{store}:{mutation_domain}:{attempt_token}` (DEC-036 D14).
- **Domain-enable flag:** `inventory_domain_enabled` gates all six job
  types above, plus both matrix rows' admission via the C2 registry gate.
- **Connection-generation behavior:** unchanged from the existing generic
  admission behavior; every job type snapshots
  `expected_connection_generation`/`expected_store_identity` at its own
  C1/C2, independently per job.

---

## 8. Task 013B — Layer 2 non-applicability (closes contradiction C11, unaffected in substance by Revision 2)

Restated bindingly, in this record and in the Task 013B packet's own §0:

- Task 013B issues **zero** Shopify mutations. It reads
  `InventoryLevel.quantities` (a `remote_read_replay_safe` Layer 1 job,
  unchanged) and performs guarded local Odoo writes.
- Because Task 013B never calls a Shopify mutation, DEC-036's mutation
  attempt model, C1/C2/NET/C3 protocol, and reconciliation contract do
  not apply to it — no `mutation.attempt` row, no `mutation_domain`
  registration, no Layer 2 wrapper call anywhere in its scope.
- Task 013B's own safety contract (row locking, final re-read under
  lock, drift/topology abort, post-write `free_qty` verification) is a
  local Odoo transaction/locking concern, unchanged by this revision.
- No Layer 2 mutation wrapper is added to Task 013B merely for symmetry
  with Task 013.
- **Exact interaction with Task 013 (unchanged, restated):** Task 013
  must be installed and its Gate B/Stage 0 dependencies accepted first; a
  baseline apply for a pair blocks any concurrent inventory job for that
  same pair (shared pair-serialization identity, §5.3, Task 013B
  D-013B-4); after a successful baseline, Odoo is the standing authority
  and the next Task 013 push for that pair begins from the accepted
  baseline state (D-013B-8, unchanged).

---

## 9. Job/mutation-consequence contract (new, Revision 2, closes binding correction 5)

For every Task 013 mutation outcome, this table specifies
`observed_outcome`, `error_class`, `manual_review_subreason` (where
applicable), whether automatic retry is permitted, the retry class and
its counter/delay sources, whether reconciliation is required, and the
next orchestration behavior. Unknown or malformed consequence data
(anything not enumerated below, e.g. a `mutation.attempt`-consequence
payload that fails schema validation) **must never default to automatic
retry** — it routes fail-closed to `uncertain`/`blocked_manual_review`/
`no_reconciliation_strategy`-equivalent handling. Domain code must never
write job state directly outside the accepted Layer 2 consequence
interface (DEC-036's existing C3 outcome-commit seam) — this table
constrains what that interface is told to do, it does not add a second
write path.

| Outcome | `observed_outcome` | `error_class` | `manual_review_subreason` | Auto-retry | Retry class / bound | Retry counter source | Retry-delay source | Reconciliation required | Next orchestration behavior |
|---|---|---|---|---|---|---|---|---|---|
| `inventory_set_quantities` succeeded | `succeeded` | — | — | No | — | — | — | No (evidence is direct) | Job terminal `succeeded`; binding's `last_pushed_available`/`last_pushed_at` refreshed |
| CAS stale, retry 1–3 | `failed_clean` | `concurrency_race_conflict` | — | Yes, bounded | Same-job redispatch, max 3 | `cas_mismatch_count` (job field, §4 row 1) | Existing generic bounded-retry backoff policy (DEC-009 pattern; no new backoff mechanism introduced) | No (fresh CAS pre-read substitutes) | Job redispatches itself with a fresh attempt |
| CAS stale, 4th mismatch | `failed_clean` | `concurrency_race_conflict` | `binding_conflict` | No | Exhausted | `cas_mismatch_count >= 3` | — | No | Job terminal `blocked_manual_review`; pending target stays coalesced |
| Validation/binding code (`INVALID_*`, `NON_MUTABLE_INVENTORY_ITEM`, `NO_DUPLICATE_...`) | `failed_clean` | `remote_validation_rejected` | `binding_conflict` | No | — | — | — | No | Job terminal `blocked_manual_review` |
| `ITEM_NOT_STOCKED_AT_LOCATION` | `failed_clean` | `remote_precondition_mismatch` | `inventory_location_missing` | No (not by this job) | — | — | — | No (this job); a fresh `inventory_push_sync` orchestration read is required | Job terminal `blocked_manual_review`/routed-for-re-orchestration; pending target stays coalesced; next scan/manual trigger admits a fresh `inventory_push_sync` |
| `IDEMPOTENCY_CONCURRENT_REQUEST` | `uncertain` | `transport_ambiguous` | — | No (reconcile first) | — | — | — | Yes | Reconciliation read scheduled; retry only after resolution |
| `IDEMPOTENCY_KEY_PARAMETER_MISMATCH` / `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` | `uncertain` (until reconciled) | `idempotency_contract_violation` | `idempotency_contract_violation` | No | — | — | — | Yes | Job terminal `blocked_manual_review`, no automatic retry |
| `THROTTLED`/network/HTTP ambiguity (either domain) | `uncertain` | `transport_ambiguous` | — | No (reconcile first) | — | — | — | Yes | Reconciliation read scheduled |
| `inventory_set_quantities` reconciliation → `not_applied` | (resolved) `not_applied` | — | — | Yes | Fresh attempt on next dispatch | Normal job dispatch counter | Existing generic backoff | Already performed | Job redispatches with a fresh CAS-based attempt |
| `inventory_set_quantities` reconciliation → inconclusive | (unresolved) | — | `duplicate_risk` (at N=3 cap) | No | — | `inconclusive_reconciliation_count` | — | Yes, repeat | Next reconciliation read scheduled; at cap, `blocked_manual_review` |
| `inventory_activate` succeeded | `succeeded` | — | — | No | — | — | — | No | Job terminal `succeeded`; triggers §5.2 step 7 handoff via a fresh orchestration job |
| `inventory_activate` clean rejection (any `userErrors`+null `inventoryLevel`) | `failed_clean` | `clean_rejection` | `binding_conflict` | No | — | — | — | No | Job terminal `blocked_manual_review` |
| `inventory_activate` ambiguous (`userErrors`+non-null `inventoryLevel`) | `uncertain` | `transport_ambiguous` | — | No (reconcile first) | — | — | — | Yes | Reconciliation read scheduled |
| `inventory_activate` reconciliation → `not_applied` | (resolved) `not_applied` | — | — | Yes | Fresh attempt on next dispatch | Normal job dispatch counter | Existing generic backoff | Already performed | Job redispatches with a fresh activation attempt |
| `inventory_activate` reconciliation → inconclusive | (unresolved) | — | `duplicate_risk` (at N=3 cap) | No | — | `inconclusive_reconciliation_count` | — | Yes, repeat | Next reconciliation read scheduled; at cap, `blocked_manual_review` |

---

## 10. Coalescing (expanded, Revision 2)

- **Binding-level allowed business fields** (informational/coalescing
  only, refreshed from a reconciliation read or a `succeeded` attempt's
  evidence): `pending_target_available`, `last_pushed_available`,
  `last_pushed_at`, `last_known_shopify_available`, and the existing
  first-push state/evidence fields (`first_push_state`,
  `first_push_preview_qty`, `first_push_confirmed_at`,
  `first_push_confirmed_by_uid`).
- **These must never include:** the Shopify transport idempotency key;
  the exact-request fingerprint as replay authority; the attempt token as
  transport authority. All three live exclusively on
  `shopify.connector.mutation.attempt` (C5, unchanged).
- **While any inventory job for the pair is non-terminal** (§5.3): new
  Odoo stock changes update/coalesce `pending_target_available` on the
  binding (last-value-wins — a later change overwrites an earlier
  uncommitted one, it does not queue); no duplicate pair job is admitted;
  no second mutation attempt is created for the pair outside the bounded
  CAS-retry redispatch mechanism already described for the currently
  non-terminal job itself.
- **After the active job finishes** (goes terminal): the next
  `inventory_push_sync` orchestration dispatch reads the latest coalesced
  `pending_target_available` — a stale target (one superseded by a later
  Odoo change while the prior job ran) is never pushed; the fresh read
  always wins.

---

## 11. Inventory operating model — reconciled (summary; full text in the corrected document)

- Standing model unchanged from DEC-010: Odoo authoritative after
  onboarding; push `available` only; source is Odoo location-context
  `free_qty`; one mapped pair per request; Layer 2 wraps every Shopify
  mutation, each as its **own standalone mutation job** (Revision 2, §5);
  reverse direction is read/verify/review only; Task 013B is the only
  controlled onboarding exception; unexplained drift creates review
  evidence, never a silent overwrite; reconnect reads before push; no
  standing bidirectional sync; no committed/`on_hand` write; no
  batching; no binding-owned transport idempotency.
- Five distinct flows, kept explicit and never conflated: (1) standing
  Odoo→Shopify push (§4 row 1, §5 job model and orchestration flow when
  activation is needed); (2) Shopify reconciliation read (§4, both
  rows); (3) reconnect catch-up read (§12, DEC-036 D18 store-identity
  check as the first reconciliation step); (4) Task 013B one-time
  reviewed baseline (§8, no Layer 2); (5) manual divergence review
  (review cases from C6/C7/matrix `binding_conflict` routing, §9).

---

## 12. Reconnect policy — reconciled (summary; full text in the corrected document)

The inventory reconnect sequence is:

1. Store reconnect succeeds (existing eight-step sequence, unchanged).
2. Connection generation is current (existing, unchanged).
3. New push/activation admission remains blocked for every mapped pair
   until step 4 clears — enforced by `inventory_push_sync`'s own
   admission gate (§5.1.A), not by any mutation job classifying
   reconnect state itself. **No mutation job performs the reconnect
   classification itself** — this is exclusively an `inventory_push_sync`
   responsibility.
4. Read Shopify `available` (and, if the pair has no confirmed baseline,
   `on_hand`) for every mapped pair — beginning with the store-identity
   check (DEC-036 D18).
5. Read Odoo current `free_qty` for every mapped pair.
6. Read the last accepted/pushed business state (`last_pushed_available`/
   `last_pushed_at`, C5 — never retry authority, only the comparison
   baseline here).
7. Classify: expected match (resume normally); known local change
   (resume, next push carries the new value); unexplained Shopify drift
   (review case); identity mismatch (`store_identity_mismatch`, never
   retried); missing level/activation required (the fresh
   `inventory_push_sync` orchestration job enqueues `inventory_activate`
   on the **next confirmed push**, per §5.2 step 5 — not automatically
   and not from any other job).
8. Unexplained drift routes to review, never a blind push.
9. Never blind push, for any classification.
10. A new push is permitted only after the read/review gate clears for
    that specific pair, and only `inventory_push_sync` may then enqueue
    the resulting mutation job.

Behavior for the named edge cases (long disconnect, credential rotation,
store identity mismatch, pending uncertain attempt, pending
reconciliation, mapping change, product binding change, inactive Shopify
location) is unchanged from the existing accepted reconnect
policy/DEC-036 D28/D18.

---

## 13. Factual Stage 0 status (new, Revision 2, closes binding correction 6)

As of this revision (2026-07-19), directly re-verified:

- **PR #178** ("Wave 3 Stage 0: DEC-031 Layer 2 core substrate") **exists**,
  is **open**, is a **draft**, is **unmerged**, at head
  `644853a68b3497c134ee648ce7399e50d30ff397`.
- PR #178's own body states: implementation complete by its own report;
  static validation (AST parse, XML parse, line-length scan, required
  tests present/registered, cron/ACL checks, production-mutation scan,
  base-to-head file-scope check, protected-ref recheck) performed and
  passing, by its own report; Odoo is **not installed** in that session's
  execution workspace, so the genuine PostgreSQL runtime tests, the
  process-death harness, the install/upgrade test, and the full connector
  regression were **not run there** — no runtime-pass claim is made by
  that PR itself.
- This record makes **no claim** that Stage 0 is accepted, merged,
  synchronized with this Gate B package, runtime-tested, or "frozen" as a
  runtime candidate. Every prior statement in this document set saying
  Stage 0 "has no PR yet" is corrected by this section and by the
  corresponding correction in each shared tracker (`mvp-program-state.md`,
  `research-handoff.md`) — those documents are updated to point here
  rather than repeating the stale claim inline.
- This Gate B package's own content does not depend on Stage 0's
  progress in either direction — it specifies the domain-specific
  contract Stage 0's generic substrate must support once both are
  accepted and merged.

---

## 14. Traceability (Pass 2 summary, updated Revision 2)

For both matrix rows, the full chain is unbroken:

**`inventorySetQuantities`:** product decision (DEC-010, unchanged) → Task
013 packet D-013-2/D-013-3/D-013-9 → §4 row 1 of this record → §5 job
model/orchestration flow → §9 consequence contract → locked Task 013 Sol
prompt (Layer 2 integration section) → `test_inventory_push_mechanics.py`
(unit) + genuine-concurrency tests (§5.3, Stage 0's proven pattern,
extended) → Odoo.sh evidence (Task 013 §5, unchanged requirement) →
dev-store scenarios 1–8/10–12/17–19 (plan) → rollback (Task 013 §6,
unchanged single-PR revert; attempt evidence retained per DEC-036 D32).

**`inventoryActivate`:** product decision (this record, §5, job model) →
Task 013 packet D-013-3/D-013-9 → §4 row 2 of this record → §9
consequence contract → locked Task 013 Sol prompt → `test_inventory_push_mechanics.py`
(activation assertions) → Odoo.sh evidence (same requirement, both
mutations covered) → dev-store scenario 9 (plan) → rollback (same
mechanism, both matrix rows disabled together by the domain-enable flag).

---

## 15. Status

**REVISED — RESUBMITTED FOR CONTROL-ROOM GATE B ACCEPTANCE (Revision 2).**
No decision in this record has been self-accepted. No DEC-036 decision is
reopened. Gate A is not reopened. No `addons/**` file was created or
modified. No Odoo/Odoo.sh run occurred. No Shopify mutation was issued —
only Shopify **reads** (three narrow official-source page fetches across
both revisions, §2) were performed, consistent with this session's
execution limits.
