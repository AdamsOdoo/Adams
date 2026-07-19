# DEC-037 — Wave 3 Gate B: Task 013/013B Inventory Readiness

- **Status: PROPOSED FOR CONTROL-ROOM GATE B ACCEPTANCE.** Produced
  2026-07-19 by the Gate B planning session (this session), based on
  `mvp/program-integration` @
  `3a2043cb8d45a4b9bc7bdb3ea39b58515e706da9` (PR #177 merge commit).
  **Claude did not accept its own package.** Acceptance authority: product
  owner + ChatGPT control room, exactly as DEC-036.
- **Decision owner (candidate author, not acceptor):** Claude, the Gate B
  planning/contradiction-resolution/documentation worker, per this
  session's governing task and CLAUDE.md §13. Sol is the Task 013/013B
  implementation worker (not yet issued a prompt — see
  [`../06-prompts/sol-wave-3-task-013-locked-prompt.md`](../06-prompts/sol-wave-3-task-013-locked-prompt.md)
  and
  [`../06-prompts/sol-wave-3-task-013b-locked-prompt.md`](../06-prompts/sol-wave-3-task-013b-locked-prompt.md),
  both LOCKED, unissued).
- **Scope:** closes every remaining inventory-planning contradiction named
  by DEC-036 Part 0.5 ("Gate B / Task 013 corrections carried forward")
  and Part 5 item 11 ("Out-of-scope document corrections"), plus the
  additional contradictions this session found by direct inspection of
  the Task 013/013B packets and the inventory operating model. This
  record does **not** reopen any DEC-036 decision (D1–D38) — it
  propagates those decisions, unchanged, into the inventory domain's own
  documents, and settles the domain-specific questions DEC-036 explicitly
  left to a Gate B session (mutation-domain matrix rows, job-contract
  vocabulary, activation sequencing).
- **Relationship to DEC-036:** DEC-036 is the generic Layer 2 substrate
  decision (Stage 0). This record is the domain-specific application of
  that substrate to the two Shopify mutations Task 013 issues
  (`inventorySetQuantities`, `inventoryActivate`) and the explicit
  non-application of Layer 2 to Task 013B. Where this record and DEC-036
  overlap, DEC-036 governs the substrate mechanism and this record governs
  the domain's use of it — they must never be read as alternatives.
- **Evidence base:** direct inspection of DEC-036 (full text), the
  accepted Layer 2 design doc, the Wave 3 DoR, the Task 013 packet (incl.
  its 2026-07-16 addendum), the Task 013 proposal (historical), the Task
  013B packet, the inventory operating model, the reconnect/backfill
  policy, the reconnect UAT matrix, the MVP acceptance matrix, the Stage 0
  packet (for file/registry ownership and job-field names), and the
  locked Stage 0 Sol prompt (for the locked-prompt template this record's
  own two locked prompts follow). Official-source re-verification against
  Shopify Admin GraphQL API **2026-07** performed narrowly where the
  accepted Gate A capture
  ([`shopify-layer2-mutation-safety-refresh-2026-07-18.md`](../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md))
  did not already cover a needed detail — see §2 below.

---

## 1. Contradiction inventory and disposition (Pass 1)

Every contradiction found between the accepted DEC-036 Layer 2 substrate
and the pre-existing inventory-domain documents, with its binding
resolution.

| # | Original document / section | Conflicting document / section | Binding resolution | Corrected document | Test/implementation implication |
|---|---|---|---|---|---|
| C1 | `inventory-operating-model.md` §4.4 heading "compareQuantity CAS" and body, citing `compareQuantity`/`ignoreCompareQuantity` as the live field | DEC-036 D12 (fact: `changeFromQuantity` is the only current CAS field, 2026-04+) | `changeFromQuantity` is the sole current-facing CAS field name everywhere in this document set; the "evidence-conflict" framing is retired — Gate A's capture already resolved it as a Fact, not an open conflict | `inventory-operating-model.md` §4.4 (rewritten, this session) | Static test: no `addons/shopify_connector_inventory/**` file references `compareQuantity`/`ignoreCompareQuantity` (already named in DEC-036 D12; restated in the locked Task 013 prompt) |
| C2 | `task-013-inventory-sync-implementation-packet.md`'s §"CAS via `compareQuantity`" addendum heading (its own D-013-3 body already said `changeFromQuantity`; only the addendum heading/rationale was stale) | DEC-036 D12; DEC-036 Part 5 item 11 (named as a Gate B follow-up) | Heading and rationale corrected to `changeFromQuantity`; the 2026-07-16 "evidence conflict" framing removed (resolved, not open) | `task-013-inventory-sync-implementation-packet.md` §A.2 (this session) | Same static test as C1 |
| C3 | `inventory-operating-model.md` §4.3 ("Batching") and §9 ("Batch sizing... multi-entry `inventorySetQuantities` batches") | DEC-036 D4 (binding: exactly one `(inventory_item_id, location_id)` pair per mutation request; multi-entry `quantities[]` batching excluded from Wave 3 MVP) | One-pair-per-request only for Wave 3 MVP; batching text rewritten to state it is explicitly out of scope, a future separately-gated optimization, not an accepted MVP behavior | `inventory-operating-model.md` §4.3/§9 (rewritten) | Static/AST test: no call site constructs a `quantities[]` array with length > 1 (already named in DEC-036 D4; restated in the locked Task 013 prompt) |
| C4 | `inventory-operating-model.md` §10 ("Partial failures") describing per-entry `userErrors` batch routing | DEC-036 D4 (no batching) | Rewritten for one-pair-per-request: a failing request routes that one pair's job to retry/review; there is no "rest of the batch" to commit separately, because there is no batch | `inventory-operating-model.md` §10 (rewritten) | Removes a batching-shaped test expectation that could never be exercised under D4 |
| C5 | Task 013 packet D-013-1(b)/D-013-3: `last_push_idempotency_key` and `last_push_params_hash` stored **on the binding row** as the mutation retry/dedup authority | DEC-036 D6 (idempotency key is request-level and **attempt-owned**, never binding-owned, after Layer 2 adoption); this session's task §7 item 3 | Both fields are **removed** from the binding schema. The Shopify idempotency key and the exact-request fingerprint live exclusively on `shopify.connector.mutation.attempt` (Layer 2, core). The binding retains only informational, last-observed business fields (`last_pushed_available`, `last_pushed_at`), refreshed from a reconciliation read or a resolved-`succeeded` attempt — never read as transport-replay authority | `task-013-inventory-sync-implementation-packet.md` D-013-1(b)/D-013-3/D-013-9 (rewritten) | Test: no code path reads `last_pushed_available`/`last_pushed_at` to decide idempotency-key reuse or retry eligibility; those fields are display/coalescing-only |
| C6 | Task 013 packet D-013-6: unexplained Shopify-side drift is "pushed over **only after** being logged as a drift note (Odoo-SoT)" | DEC-036 Part 0.5 item 3 (review-case-first for unexplained drift, no automatic overwrite); this session's task §7 item 5 | Unexplained drift (differs from both last-pushed and current Odoo) creates a **review case** and **blocks** the pending push for that pair until reviewed or superseded by a fresh, explained state; it is never auto-pushed-over | `task-013-inventory-sync-implementation-packet.md` D-013-6/D-013-9 (rewritten); `inventory-operating-model.md` §5 (tightened) | Test: an induced unexplained-drift fixture asserts a review case is created and the pending push does **not** execute until the case clears |
| C7 | Task 013 packet D-013-3: CAS-stale routes to `concurrency_race_conflict` with no explicit retry bound; no explicit "persistent divergence → review" rule | Task master prompt §9.A (bounded re-read/re-derive; persistent divergence → review); inventory-operating-model.md §4.4 already proposed bounded retries (3) but was never cross-referenced from the packet | Bounded retry count = **3** (matches the operating model's existing proposed value); each CAS-stale retry is a **new** Layer 2 attempt (new `attempt_token`, new fingerprints, new idempotency key, since `changeFromQuantity` — part of `exact_request_fingerprint` — necessarily changed); after 3 bounded retries without a successful `set`, the pair routes to `blocked_manual_review`/`binding_conflict` (review case), never a fourth silent retry | `task-013-inventory-sync-implementation-packet.md` D-013-3/D-013-9 (rewritten) | Test: 3-strikes CAS-stale fixture asserts review-case routing on the 4th mismatch, never a further auto-retry |
| C8 | Task 013 packet D-013-3: `inventoryActivate` invoked inline inside the same handler/attempt as the `inventorySetQuantities` retry, with no explicit Layer 2 wrapper, no explicit second attempt/idempotency key | DEC-036 Hard Rule 1/D16/D37 (every Shopify mutation call site must be inside the Layer 2 wrapper); this session's task §7 item 8, §13 | `inventoryActivate` is its **own** mutation domain (`inventory_activate`), its own Layer 2 attempt, own idempotency key, own fingerprints — never combined with the `inventorySetQuantities` attempt. Sequencing defined in §5 below | `task-013-inventory-sync-implementation-packet.md` D-013-3/D-013-9 (rewritten); new matrix row, §4 below | Test: activation and set-quantity are asserted to use two distinct `attempt_token`/idempotency-key values within the same job |
| C9 | `wave-3-definition-of-ready.md` §5 item 3 flags `inventory-operating-model.md` §4.4 as needing correction "in a future Gate B session" | This session (Gate B) | Flag closed — corrected in this same session (C1 above) | `wave-3-definition-of-ready.md` §5 (updated) | N/A — status update only |
| C10 | No document defined the exact `manual_review_subreason` values this domain adds, nor the exact `operation_scope_key` convention for the domain's reconciliation jobs | DEC-036 D18/D28/D6/D17 define the *generic* subreasons (`store_identity_mismatch`, `idempotency_contract_violation`, `duplicate_risk`, `no_reconciliation_strategy`) and D14 defines the *generic* reconciliation `operation_scope_key` convention (`reconcile:{store}:{mutation_domain}:{attempt_token}`), but neither packet had frozen the domain's own job-contract vocabulary | This session freezes the exact vocabulary — §7 below | `task-013-inventory-sync-implementation-packet.md` D-013-9 (new); locked Task 013 prompt | Test: job-contract vocabulary test enumerated in §7 |
| C11 | Task 013B packet does not explicitly state its own Layer-2-non-applicability (it is stated in the Stage 0 packet and DEC-036, but not in Task 013B's own document) | This session's task §10 | Explicit statement added to the Task 013B packet itself, not merely cross-referenced | `task-013b-initial-inventory-baseline-packet.md` (new §0 preamble) | N/A — documentation completeness |
| C12 | `reconnect-catchup-backfill-policy.md` §4.4 (Inventory): "pushes resume only with fresh `compareQuantity` bases" | DEC-036 D12 | `changeFromQuantity` | `reconnect-catchup-backfill-policy.md` §4.4 (corrected) | Same static test as C1 |
| C13 | `reconnect-backfill-uat-matrix.md` UAT-RB-2.6: "pushes resume only with fresh `compareQuantity` bases" | DEC-036 D12 | `changeFromQuantity` | `reconnect-backfill-uat-matrix.md` UAT-RB-2.6 (corrected) | Same static test as C1 |

No contradiction above disappears without the recorded resolution in its
row; every corrected document is listed in §10 (allowed files) of this
session's governing task and was in scope to fix.

---

## 2. Official-source verification performed this session

Per this session's task §4/§8, the accepted Gate A capture
(`shopify-layer2-mutation-safety-refresh-2026-07-18.md`) is the default
source basis and was **not** re-fetched for facts it already establishes
(CAS field name, `@idempotent` mandatory scope/timing, THROTTLED
non-guarantee, `InventoryLevel.quantities` shape, Odoo 19 isolation
level). Two narrow gaps that capture did not cover — both directly needed
to complete the `inventoryActivate` matrix row without a "TBD" cell — were
verified live against `shopify.dev` (2026-07-19, API 2026-07):

1. **`inventoryActivate` default quantities.** Source:
   https://shopify.dev/docs/api/admin-graphql/2026-07/mutations/inventoryactivate
   — Accessible, 2026-07-19. Quote: *"If you don't specify quantities,
   then `available` and `onHand` default to zero."* `available` (Int,
   optional, default 0), `onHand` (Int, optional, default 0),
   `stockAtLegacyLocation` (Boolean, optional, default false).
   **[Fact.]**
2. **`inventoryActivate` error-reporting shape.** Source:
   https://shopify.dev/docs/api/admin-graphql/2026-07/objects/UserError —
   Accessible, 2026-07-19. The `userErrors` field on the `inventoryActivate`
   payload is typed `[UserError!]!`, and `UserError` has **exactly two
   fields**: `field: [String!]` and `message: String!` — **no `code`
   field**, unlike `InventorySetQuantitiesUserErrorCode`'s rich, dedicated
   enum. A `WebSearch` for a dedicated `InventoryActivateUserErrorCode`
   enum page returned no such page (only the unrelated
   `InventoryBulkToggleActivationUserErrorCode`, which this connector does
   not call). **[Fact.]** This materially affects failure classification
   — see the matrix row §4 below.

Both facts are folded into the `inventory_activate` matrix row (§4). No
other official-source re-verification was performed this session — every
other Layer 2/inventory fact used below cites the accepted Gate A capture
or DEC-036 directly.

---

## 3. Binding decisions propagated without reopening (per task §7)

The fourteen decisions listed in this session's governing task §7 are
binding and are propagated into the Task 013/013B documents unchanged.
They are not re-derived here; each is cited to its DEC-036 source and its
concrete point of application in the inventory documents:

| # | Decision | DEC-036 source | Applied in |
|---|---|---|---|
| 1 | CAS input field = `changeFromQuantity` | D12 | Task 013 D-013-3, §4 row 1 below |
| 2 | CAS mismatch error = `CHANGE_FROM_QUANTITY_STALE` | D12 (source-materials refresh §1) | Task 013 D-013-9, §4 row 1 |
| 3 | Idempotency: attempt-owned, request-level, persisted by Layer 2, not binding-owned; no binding-owned transport retry key; no `last_push_params_hash` as transport authority | D6 | Task 013 D-013-1(b)/D-013-9 (C5 above) |
| 4 | Mutation granularity: one item+location pair, one request, one attempt, no batching | D4 | Task 013 D-013-6/D-013-9 (C3/C4 above) |
| 5 | Unexplained Shopify drift: review-case-first, no silent/automatic overwrite | Part 0.5 item 3 | Task 013 D-013-6 (C6 above) |
| 6 | Task 013 mutations all pass through Layer 2; no direct API-client mutation call | D16/D37, Hard Rule 1 | Task 013 D-013-9 (C8 above); locked Task 013 prompt |
| 7 | `inventorySetQuantities`: separate mutation-domain registration, exact reconciliation strategy, mandatory Layer 2 wrapper | D15/D16 | §4 row 1 |
| 8 | `inventoryActivate`: also a mutation, mandatory Layer 2 wrapper, own reconciliation strategy (not combined) | D16/D37, this session's §13 analysis | §4 row 2, §5 |
| 9 | Task 013B: no Layer 2, Shopify reads, guarded local Odoo writes, no mutation, separate Stage 2 | Part 0.5 item 5; Stage 0 packet §2 | §8 below; Task 013B packet §0 (new) |
| 10 | Reconnect: reconciliation read before first post-reconnect push, never blind | inventory-operating-model.md §11 (already Proposed); reconnect policy §4.4 | §9 below (unchanged in substance, corrected field name) |
| 11 | Standing direction: Odoo authoritative after onboarding, no standing Shopify→Odoo stock sync | DEC-010 (unchanged) | §9 below |
| 12 | Shopify quantity writes: `available` only, never `committed`, never `on_hand` | DEC-010/RA-018 (unchanged) | §9 below; `inventoryActivate` row explicitly never sends `onHand` as a non-zero value |
| 13 | Negative quantity: clamp to zero, log/review evidence, never send negative `available` | inventory-operating-model.md §7 (unchanged); confirmed by `INVALID_QUANTITY_NEGATIVE` existing as a live error code (§2 note: this code cannot occur because the connector clamps before send — a defensive, not corrective, guard) | §9 below |
| 14 | First push: preview, explicit confirmation, recorded actor/time/quantity, no unconfirmed mutation | Task 013 D-013-4 (unchanged); tightened by C8's activation-sequencing rule | Task 013 D-013-4/D-013-9 |

---

## 4. Complete Layer 2 inventory mutation-domain matrix

Two rows — `inventory_set_quantities` and `inventory_activate` — each
defining every cell required by this session's task §11. No cell says
"implementation choice," "TBD," or equivalent; where a fact is genuinely
unknowable before implementation, a fail-closed default, a named
implementation-time verification, and an explicit stop condition are
given instead.

### Row 1 — `inventory_set_quantities`

| Field | Value |
|---|---|
| `job_type` | `inventory_push_sync` (existing, Task 013 D-013-6) |
| `mutation_domain` | `inventory_set_quantities` (new registry-validated `Char` value, DEC-036 D2/D35) |
| Replay-policy class | `remote_effect_not_replay_safe` (Layer 1, unchanged — every Shopify mutation is this class by construction; Layer 2 supplies the reconciliation path, it does not change the Layer 1 class) |
| Reconciliation-strategy registry key | `inventory_set_quantities`, registered via `_inherit`+`super()` on `shopify_connector_job_dispatch.py`'s `_get_reconciliation_strategies()` seam (DEC-036 D15) from `shopify_connector_inventory` |
| Domain-enable flag | `inventory_domain_enabled` (existing store setting, Task 013 §4) |
| `operation_scope_key` | `inventory_push:{store_id}:{shopify_inventory_item_gid}:{location_mapping_shopify_gid}` — one per (item, location) pair, serializes concurrent jobs for the same pair (Task 013 D-013-6, unchanged in substance, name frozen here) |
| Business-intent fingerprint inputs | `{mutation_domain: 'inventory_set_quantities', inventory_item_id, location_id, target_quantity}` — excludes `changeFromQuantity` and the idempotency key (DEC-036 D5) |
| Exact-request fingerprint inputs | Normalized `inventorySetQuantities` GraphQL document + exact variables: `name: 'available'`, `reason`, `referenceDocumentUri`, one `InventoryQuantityInput` entry `{inventoryItemId, locationId, quantity, changeFromQuantity}`, plus the `@idempotent(key: ...)` directive value (DEC-036 D5) |
| `preconditions_snapshot` allowlist | `{inventory_item_id, location_id, target_quantity, change_from_quantity, snapshot_taken_at}` (DEC-036 D7, inventory-domain instance) |
| `remote_mutation_intent` allowlist | `{inventory_item_gid, location_gid, mutation_name: 'inventorySetQuantities'}` — identifiers only, never payload bodies (DEC-036 D7) |
| `remote_evidence_refs` allowlist | `{remote_gids: [...], user_errors: [{code, field}], http_status, graphql_error_codes: [...], throttle_status: {maximumAvailable, currentlyAvailable, restoreRate} \| null}` (DEC-036 D8, unchanged shape) |
| Shopify idempotency-key lifecycle | Fresh UUIDv4 per attempt, persisted on `mutation.attempt` at C2 (never on the binding, C5 above); reused verbatim only for an identical `exact_request_fingerprint` retry within `idempotency_valid_until` (Shopify's 24h window minus the configurable local safety margin, provisional 23h — DEC-036 D6, ratification open, non-blocking); past the window, reconciliation runs first, never a blind fresh-key resend |
| Expected connection generation / store identity | Snapshotted at C2 on the attempt row (DEC-036 D18/D29); reconciliation begins by verifying current `myshopifyDomain` against the snapshot |
| Direct `succeeded` evidence | Response has no `userErrors` and the mutation's own returned quantity data reflects the requested `quantity` → `observed_outcome='succeeded'` |
| Direct `failed_clean` evidence | `userErrors` containing one of: `INVALID_INVENTORY_ITEM`, `INVALID_LOCATION`, `INVALID_NAME`, `INVALID_QUANTITY_TOO_HIGH`, `INVALID_QUANTITY_TOO_LOW`, `INVALID_REASON`, `INVALID_REFERENCE_DOCUMENT`, `NO_DUPLICATE_INVENTORY_ITEM_ID_GROUP_ID_PAIR`, `NON_MUTABLE_INVENTORY_ITEM` (all confirmed live on `InventorySetQuantitiesUserErrorCode`, API 2026-07 — see the accepted Gate A capture §1). `INVALID_QUANTITY_NEGATIVE` is a **confirmed-existing but never-triggerable** code under this connector's own clamp-before-send discipline (DEC-036/task §7 item 13) — a defensive test asserts it is never observed, it is not a routing target. `NON_MUTABLE_INVENTORY_ITEM` routes to `blocked_manual_review`/`binding_conflict` (existing DEC-009 clean-rejection classification, unchanged from Task 013 D-013-3) |
| Direct `uncertain` evidence | Network timeout after send; HTTP 5xx; `THROTTLED`; ambiguous/partial `userErrors` (data + errors both present); `IDEMPOTENCY_CONCURRENT_REQUEST`; worker crash between send and outcome commit (DEC-036 D9/D19/D23/D24) |
| `THROTTLED` handling | `uncertain`, reconcile-first, never auto-classified `failed_clean`, for this domain like every other (DEC-036 D9) |
| Idempotency-error handling | `IDEMPOTENCY_CONCURRENT_REQUEST` → `uncertain`; `IDEMPOTENCY_KEY_PARAMETER_MISMATCH` / `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` → `idempotency_contract_violation`, `blocked_manual_review`, no automatic retry (DEC-036 D6) |
| Reconciliation read | `InventoryLevel.quantities(names: ["available"])` for the exact (inventory_item_id, location_id) pair; **first** step is the store-identity check (current `myshopifyDomain` vs. the attempt's `expected_store_identity`, DEC-036 D18) before interpreting the quantity |
| `applied` verdict | Current Shopify `available` equals this attempt's `target_quantity` (from `exact_request_fingerprint`), and `InventoryQuantity.updatedAt` is not older than this attempt's `transport_at` where present → `resolution_disposition='applied'`, `resolution_source='reconciliation_read'`; job completes without resend; the binding's informational `last_pushed_available`/`last_pushed_at` are refreshed from this same read (display-only, never transport authority — C5 above) |
| `not-applied` verdict | Current Shopify `available` equals this attempt's own `changeFromQuantity` (i.e., unchanged from immediately before the attempt) → `resolution_disposition='not_applied'`; job becomes retry-eligible; a **new** attempt (fresh `changeFromQuantity` re-read, fresh fingerprints, fresh idempotency key) is created only on the job's next dispatch, never by mutating the resolved attempt row |
| Inconclusive verdict | Current Shopify `available` equals **neither** the pre-attempt nor the post-attempt value (a third-party or concurrent change occurred, and the read cannot attribute or rule out this attempt's own effect) → `inconclusive_reconciliation_count` increments under a re-acquired row lock (DEC-036 D17); next reconciliation read scheduled; never inferred as one verdict or the other from ambiguous evidence |
| Manual-review subreason | `duplicate_risk` (N=3 inconclusive cap, DEC-036 D17); `store_identity_mismatch` (DEC-036 D18); `idempotency_contract_violation` (DEC-036 D6); `binding_conflict` (`NON_MUTABLE_INVENTORY_ITEM`; persistent CAS divergence after 3 bounded retries, C7 above; unexplained-drift review case, C6 above); `no_reconciliation_strategy` (registry lookup failure — should never occur once this row is registered; guarded by DEC-036 D16's runtime gate and a build-time completeness test) |
| Retry eligibility | Per the effective-disposition helper (DEC-036 D10): `failed_clean` → normal DEC-009 bounded class-based retry (new attempt); `uncertain` unresolved → reconcile-then-retry only; resolved `not_applied` → retry-eligible with a fresh CAS-based attempt; effective `applied` → no resend |
| First-push interaction | This mutation domain **never** fires for a pair whose binding `first_push_state != 'confirmed'` — the push handler refuses before an attempt is ever created (`destructive_write_guard_blocked`, Task 013 D-013-4, unchanged) |
| Reconnect interaction | No `inventory_push_sync` job is admitted for a pair until a reconciliation read (a `remote_read_replay_safe` job, Layer 1 class, unchanged) of that pair's current `available` has completed after reconnect; any pending push target is recomputed against that fresh read (§9 below) |
| Disconnect interaction | Per DEC-036 D28: if disconnect/quiescence begins while an `inventory_set_quantities` attempt is `uncertain`/pending reconciliation, credential-clearing is deferred until resolved; new pushes are blocked immediately at admission, unaffected by this domain specifically (generic Layer 2 behavior) |
| Rollback/disable behavior | Per DEC-036 D36 (two mechanisms together): `inventory_domain_enabled=False` blocks new jobs; this `mutation_domain`'s replay-policy registry entry is (and remains) `remote_effect_not_replay_safe`, fail-closing any in-flight retry |
| Exact tests | `test_inventory_push_mechanics.py` (Task 013 §5, extended): CAS-stale bounded-retry-then-review (3-strikes, C7); fresh-attempt-per-CAS-retry (new fingerprint/key each retry); `THROTTLED`→`uncertain`; both idempotency-defect codes → `idempotency_contract_violation`/`blocked_manual_review`/no-retry; reconciliation `applied`/`not_applied`/`inconclusive` (three distinct cases); store-identity-mismatch routing; first-push-confirmed gate (no attempt created for an unconfirmed row); binding never stores a Shopify idempotency key or exact-request fingerprint (C5) |
| Exact dev-store evidence | Dev-store validation plan (§16 of this session's task; see the new plan document) scenarios 1–8 and 10–12 |

### Row 2 — `inventory_activate`

| Field | Value |
|---|---|
| `job_type` | `inventory_push_sync` (same enclosing job as row 1 — see §5 sequencing; **not** a new job type) |
| `mutation_domain` | `inventory_activate` (new registry-validated `Char` value, distinct from `inventory_set_quantities`) |
| Replay-policy class | `remote_effect_not_replay_safe` |
| Reconciliation-strategy registry key | `inventory_activate`, registered alongside `inventory_set_quantities` in the same `_get_reconciliation_strategies()` extension — **its own row, never folded into the set-quantities strategy** |
| Domain-enable flag | `inventory_domain_enabled` (same) |
| `operation_scope_key` | Same `inventory_push:{store_id}:{shopify_inventory_item_gid}:{location_mapping_shopify_gid}` as row 1 — this is the same job and the same pair; the scope key governs job admission per pair, not per attempt |
| Business-intent fingerprint inputs | `{mutation_domain: 'inventory_activate', inventory_item_id, location_id, initial_available: 0}` — the stable intent is always "activate this pair at a zero baseline," never a nonzero initial value (see below) |
| Exact-request fingerprint inputs | Normalized `inventoryActivate` GraphQL document + exact variables: `inventoryItemId`, `locationId`, **`available: 0`** (explicit, never omitted — see Fact below), `onHand` omitted (defaults to 0; never sent as nonzero — DEC-036/task §7 item 12, never `on_hand` writes), `stockAtLegacyLocation: false` (explicit default; a `true` value is out of MVP scope — see stop condition below), plus the `@idempotent(key: ...)` directive value, **distinct from** row 1's key |
| `preconditions_snapshot` allowlist | `{inventory_item_id, location_id, initial_available: 0, snapshot_taken_at}` |
| `remote_mutation_intent` allowlist | `{inventory_item_gid, location_gid, mutation_name: 'inventoryActivate'}` |
| `remote_evidence_refs` allowlist | Same D8 shape as row 1; `graphql_error_codes` will be empty for this mutation in practice (see next row — no dedicated error-code enum exists), populated only if a future API version adds one |
| Shopify idempotency-key lifecycle | Fresh UUIDv4 for this attempt, **distinct from** the subsequent set-quantities attempt's key (this session's task §13, "separate attempt and idempotency key for each mutation"); same 24h-minus-margin reuse rule as row 1 |
| Expected connection generation / store identity | Snapshotted at this attempt's own C2, independently of row 1's snapshot |
| Direct `succeeded` evidence | **[Fact, verified live 2026-07-19]** Response returns a non-null `inventoryLevel` and an empty `userErrors` array → `observed_outcome='succeeded'`. The level now exists with `available=0`/`on_hand=0` (confirmed default when quantities are omitted: *"If you don't specify quantities, then `available` and `onHand` default to zero"* — https://shopify.dev/docs/api/admin-graphql/2026-07/mutations/inventoryactivate). This connector explicitly passes `available: 0` rather than relying on the omitted-argument default, so the sent value is always visible in `exact_request_fingerprint` and never ambiguous between "we asked for zero" and "we asked for nothing." |
| Direct `failed_clean` evidence | **[Fact, verified live 2026-07-19]** `inventoryActivate`'s `userErrors` field is typed `[UserError!]!`, and `UserError` has **exactly two fields, `field` and `message` — no `code` field** (https://shopify.dev/docs/api/admin-graphql/2026-07/objects/UserError). No dedicated `InventoryActivateUserErrorCode` enum exists as of API 2026-07 (confirmed by a targeted search finding no such page — only the unrelated `InventoryBulkToggleActivationUserErrorCode`, which this connector never calls). **[Recommendation, extending DEC-036 D9's established ambiguous-response reasoning to this mutation]:** classify by **payload shape**, not by message-string matching (message text is not a stable machine-classification surface): a non-empty `userErrors` array **with a null `inventoryLevel`** → `failed_clean` (clean rejection, nothing created — consistent with the GraphQL convention that a wholly-rejected mutation returns no partial object); route to `blocked_manual_review`/`binding_conflict` (the same clean-rejection class Task 013 already uses for `NON_MUTABLE_INVENTORY_ITEM`), since no finer-grained code exists to classify further |
| Direct `uncertain` evidence | Network timeout after send; HTTP 5xx; `THROTTLED`; **a non-empty `userErrors` array together with a non-null `inventoryLevel`** (ambiguous/partial — same DEC-036 D9 reasoning as row 1, applied here because the payload shape, not an error-code enum, is this mutation's only classification signal); worker crash between send and outcome commit |
| `THROTTLED` handling | `uncertain`, reconcile-first — identical policy to row 1 (DEC-036 D9 applies per-domain, not per-mutation-error-shape) |
| Idempotency-error handling | Same three codes/behaviors as row 1 apply generically at the Layer 2 wrapper level (the `@idempotent` directive and its defect codes are a transport-layer contract, not specific to `InventorySetQuantitiesUserErrorCode`) — **[Open question, non-blocking]** whether `IDEMPOTENCY_CONCURRENT_REQUEST`/`IDEMPOTENCY_KEY_PARAMETER_MISMATCH`/`IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` are surfaced as `UserError.message` text (no code) for `inventoryActivate` specifically was not directly observed in this session's fetches; **fail-closed default:** any `UserError.message` containing recognizable idempotency-defect language (case-insensitive match against the three known message strings quoted in the accepted Gate A capture §2) is classified as `idempotency_contract_violation`; **named implementation-time verification:** confirm this message-matching approach against a live dev-store idempotency-conflict trigger during the dev-store validation plan (scenario 8); **stop condition:** if the message text cannot be reliably distinguished from an ordinary validation `UserError`, escalate to the control room before shipping message-based classification for this mutation |
| Reconciliation read | `InventoryLevel.quantities(names: ["available", "on_hand"])` for the pair — read both names to prove the level exists and to confirm `on_hand` is exactly 0 (never nonzero) after activation; same store-identity-first check as row 1 |
| `applied` verdict | The level now exists (query returns a non-null `InventoryLevel` for the pair) and `available == 0` and `on_hand == 0` → `resolution_disposition='applied'` |
| `not-applied` verdict | The level still does not exist for the pair (query returns null/absent) → `resolution_disposition='not_applied'`; job becomes retry-eligible, new activation attempt on next dispatch |
| Inconclusive verdict | The level exists but `available`/`on_hand` are **not both** 0 (a value other than the connector's own zero-activation intent is present) — this can only mean a concurrent, unexplained write reached the pair between this attempt and the read → `inconclusive_reconciliation_count` increments (never auto-corrected, never assumed to be this attempt's own effect) |
| Manual-review subreason | `duplicate_risk` (N=3 cap); `store_identity_mismatch`; `idempotency_contract_violation` (message-matched, see above); `binding_conflict` (a nonzero level found during reconciliation with no attributable cause — treated as unexplained drift, review-case-first, C6's posture extended to activation) |
| Retry eligibility | Same effective-disposition helper as row 1 |
| First-push interaction | Fires **only** for a pair whose binding is `first_push_state='confirmed'` **and** whose most recent `inventorySetQuantities` attempt (or reconciliation read) returned `ITEM_NOT_STOCKED_AT_LOCATION` — never fired speculatively, never fired for an unconfirmed row (Task 013 D-013-3/D-013-4, unchanged) |
| Reconnect interaction | Same admission gate as row 1 — no activation attempt is admitted until the pair's reconnect reconciliation read has completed |
| Disconnect interaction | Same as row 1 |
| Rollback/disable behavior | Same as row 1 |
| Exact tests | New assertions in `test_inventory_push_mechanics.py`: activation attempt always sends explicit `available: 0` (never omitted, never nonzero); activation and the following set-quantities attempt use two distinct `attempt_token`/idempotency-key values; activation never sends `onHand` as nonzero; reconciliation reads both `available` and `on_hand` and requires both zero for `applied`; message-based idempotency-defect classification test (dev-store-validated per scenario 8); a nonzero post-activation level routes to `binding_conflict`, never silently accepted |
| Exact dev-store evidence | Dev-store validation plan scenario 9 |

No matrix cell above is "TBD" or "implementation choice." Every
genuinely unknown item (the idempotency-defect message-matching approach
for `inventoryActivate`) carries a fail-closed default, a named
implementation-time/dev-store verification step, and an explicit stop
condition.

---

## 5. `inventoryActivate` / `inventorySetQuantities` sequencing (new — closes contradiction C8)

DEC-036's job model gives one job a single `current_attempt_token` "of the
attempt this job currently owns" at any moment, but a first push to a pair
with no existing `InventoryLevel` requires **two** sequential Shopify
mutations. This record defines the sequencing DEC-036 left to Gate B:

1. The enclosing `inventory_push_sync` job's **C1** (claim) is unchanged —
   one claim per job, exactly as DEC-036 D19 already specifies.
2. **Attempt 1 (`inventory_activate`)** runs its own complete C2/NET/C3
   cycle under the job's current claim: a fresh `attempt_token` is
   generated and becomes the job's `current_attempt_token` for this
   attempt; C2 commits the activation attempt-intent (side cursor); NET
   sends `inventoryActivate`; C3 commits the activation outcome.
3. **Activation resolution.** If Attempt 1's effective disposition
   (DEC-036 D10 helper) is anything other than `applied` — `uncertain`
   (routes to reconciliation, §4 row 2), `not_applied` (retry-eligible,
   a fresh Attempt 1 on next dispatch), or an unresolved manual-review
   state — the job **stops here**. The set-quantities mutation is never
   attempted while activation's own effective disposition is not
   `applied`.
4. **Only after Attempt 1's effective disposition is `applied`**, the same
   job (still `running`, still holding its original job-level claim from
   C1) proceeds: a **new** `attempt_token` is generated (overwriting the
   job's `current_attempt_token`, which is safe — Attempt 1 is
   terminal/immutable per DEC-036 D10 and no longer needs the token to
   remain "current"), and **Attempt 2 (`inventory_set_quantities`)** runs
   its own complete C2/NET/C3 cycle, with `changeFromQuantity` set to the
   value the activation reconciliation read just confirmed (`0`).
5. Each attempt has its **own** idempotency key, its own fingerprints, its
   own `mutation.attempt` row — never one combined, untraceable logical
   attempt. Both attempts share the job's single `operation_scope_key`
   (they are the same business pair, the same job) but are otherwise
   fully independent Layer 2 attempts.
6. The job itself does not reach a terminal state until **both** attempts
   have reached a resolved effective disposition (Attempt 2's, in the
   normal case where Attempt 1 succeeded; or Attempt 1's alone, if the
   job stopped at step 3).

This sequencing is a **new Gate B recommendation**, not a restatement of
an existing DEC-036 item — DEC-036 D19's C1/C2/NET/C3 protocol is defined
per-attempt and does not itself say how many attempts one job may own in
sequence. It does not modify DEC-036's schema (D1/D2) — it uses the
existing `current_attempt_token` regeneration mechanism (already how a
`failed_clean` retry creates a new attempt row per DEC-036 D9) in the same
way, applied twice within one job dispatch instead of across two separate
dispatches.

---

## 6. First-push guard (tightened)

Per this session's task §9.F, restated precisely for Task 013:

- Preview (`inventory_first_push_preview`) and explicit confirmation
  (`action_confirm_first_push()`, recording actor/time/preview quantity)
  are required before the **first** Layer 2 attempt of either mutation
  domain for a pair (Task 013 D-013-4, unchanged).
- First push never bypasses Layer 2 — both the activation attempt (if
  needed) and the set-quantities attempt run through the full wrapper,
  exactly like every later push.
- Activation (§5) never creates an unreviewed nonzero stock state: it is
  always requested at an explicit `available: 0`, and its own
  reconciliation read (§4 row 2) verifies zero before the set-quantities
  attempt is allowed to run.

---

## 7. Task 013 job contract — frozen (closes contradiction C10)

The following vocabulary is frozen for `shopify_connector_inventory`.
Nothing below is left to Sol's discretion.

- **`job_type` values (four, unchanged from Task 013 §4):**
  `inventory_push_sync`, `inventory_push_scan`,
  `inventory_first_push_preview`, `inventory_location_sync`. Layer 2
  reconciliation reads use the existing generic `remote_read_replay_safe`
  job type (DEC-036 D14) — **no new job type is added for
  reconciliation.**
- **`job_source` values (unchanged, Task 013 D-013-6):**
  `odoo_event` (`trigger_origin='inventory_stock_change'`),
  `scheduled_sync`, `manual_sync`, `export_preview_dry_run`.
- **Error/manual-review-subreason vocabulary this domain adds or
  consumes:**
  - `inventory_location_missing` (existing, unmapped item/location)
  - `binding_conflict` (existing — stale/recreated Shopify identity;
    extended by this record to also cover: `NON_MUTABLE_INVENTORY_ITEM`,
    persistent CAS divergence after 3 bounded retries, unexplained
    inventory drift, and a nonzero post-activation level)
  - `destructive_write_guard_blocked` (existing — unconfirmed first-push
    row)
  - `duplicate_risk` (DEC-036 D17, generic — N=3 inconclusive
    reconciliation cap, both matrix rows)
  - `store_identity_mismatch` (DEC-036 D18, generic)
  - `idempotency_contract_violation` (DEC-036 D6, generic)
  - `no_reconciliation_strategy` (DEC-036 D16, generic — should never
    fire once both matrix rows are registered; a build-time completeness
    test guards this)
- **`operation_scope_key` convention:**
  `inventory_push:{store_id}:{shopify_inventory_item_gid}:{location_mapping_shopify_gid}`
  for push/activation jobs (one per pair, §4); reconciliation jobs use the
  existing generic convention
  `reconcile:{store}:{mutation_domain}:{attempt_token}` (DEC-036 D14).
- **Domain-enable flag:** `inventory_domain_enabled` (existing store
  setting) gates all four job types above, plus both matrix rows'
  admission via the C2 registry gate (DEC-036 D16).
- **Connection-generation behavior:** unchanged from the existing generic
  admission behavior (stale-generation jobs never execute); both matrix
  rows snapshot `expected_connection_generation`/`expected_store_identity`
  at their own C2 (DEC-036 D18/D29), independently per attempt.

---

## 8. Task 013B — Layer 2 non-applicability (closes contradiction C11)

Restated bindingly, in this record and in the Task 013B packet's own new
§0 (this session):

- Task 013B issues **zero** Shopify mutations. It reads
  `InventoryLevel.quantities` (a `remote_read_replay_safe` Layer 1 job,
  unchanged) and performs guarded local Odoo writes via the standard
  Odoo 19 inventory-adjustment path.
- Because Task 013B never calls a Shopify mutation, **DEC-036's mutation
  attempt model, C1/C2/NET/C3 protocol, and reconciliation contract do not
  apply to it** — there is no `mutation.attempt` row, no `mutation_domain`
  registration, and no Layer 2 wrapper call anywhere in Task 013B's scope.
- Task 013B's own safety contract (database-backed row locking, final
  re-read under lock, drift/topology abort, post-write `free_qty`
  verification with rollback) is a **local Odoo transaction/locking**
  concern, already fully specified in the accepted Task 013B packet
  (D-013B-4) and unchanged by this session.
- **No Layer 2 mutation wrapper is added to Task 013B merely for
  symmetry** with Task 013 — doing so would wrap a Shopify **read**, which
  the Layer 1 replay-policy registry already classifies correctly as
  `remote_read_replay_safe`, and would misrepresent a local-only Odoo
  write as if it carried Shopify-mutation risk it does not have.
- **Exact interaction with Task 013 (unchanged, restated):** Task 013 must
  be installed and its Gate B/Stage 0 dependencies accepted first; a
  baseline apply for a pair blocks any concurrent push job for that same
  pair (shared `operation_scope_key`, Task 013B D-013B-4); after a
  successful baseline, Odoo is the standing authority and the next Task
  013 push for that pair begins from the accepted baseline state
  (D-013B-8, unchanged).

---

## 9. Inventory operating model — reconciled (summary; full text in the
corrected document)

- Standing model unchanged from DEC-010: Odoo authoritative after
  onboarding; push `available` only; source is Odoo location-context
  `free_qty`; one mapped pair per request (corrected from the prior
  batching text, C3/C4); Layer 2 wraps every Shopify mutation (both matrix
  rows, not just the set-quantities call, C8); reverse direction is
  read/verify/review only; Task 013B is the only controlled onboarding
  exception; unexplained drift creates review evidence, never a silent
  overwrite (C6); reconnect reads before push; no standing bidirectional
  sync; no committed/`on_hand` write; no batching; no binding-owned
  transport idempotency (C5).
- Five distinct flows, kept explicit and never conflated (this session's
  task §14): (1) standing Odoo→Shopify push (§4 row 1, §5 sequencing when
  activation is needed); (2) Shopify reconciliation read (§4, both rows);
  (3) reconnect catch-up read (§9 reconnect, unchanged mechanism, DEC-036
  D18 store-identity check now explicitly the first reconciliation step);
  (4) Task 013B one-time reviewed baseline (§8, no Layer 2); (5) manual
  divergence review (review cases from C6/C7/matrix `binding_conflict`
  routing).

---

## 10. Reconnect policy — reconciled (summary; full text in the corrected
document)

Per this session's task §15, the inventory reconnect sequence is:

1. Store reconnect succeeds (existing eight-step sequence, unchanged).
2. Connection generation is current (existing, unchanged).
3. New push/activation admission remains blocked for every mapped pair
   until step 4 clears.
4. Read Shopify `available` (and, if the pair has no confirmed baseline,
   `on_hand`) for every mapped pair — the reconciliation read begins, as
   always, with the store-identity check (DEC-036 D18).
5. Read Odoo current `free_qty` for every mapped pair.
6. Read the last accepted/pushed business state (the binding's
   informational `last_pushed_available`/`last_pushed_at`, C5 — never
   used as retry authority, only as the comparison baseline here).
7. Classify: expected match (resume normally); known local change (Odoo
   changed, Shopify unchanged — resume, next push carries the new value);
   unexplained Shopify drift (differs from both last-pushed and current
   Odoo, with no attributable cause — review case, C6's posture);
   identity mismatch (`store_identity_mismatch`, never retried); missing
   level/activation required (route through §5's activation sequencing on
   the next confirmed push, not automatically).
8. Unexplained drift routes to review, never a blind push.
9. Never blind push, for any classification.
10. A new push is permitted only after the read/review gate clears for
    that specific pair.

Behavior for the named edge cases (long disconnect, credential rotation,
store identity mismatch, pending uncertain attempt, pending
reconciliation, mapping change, product binding change, inactive Shopify
location) is unchanged from the existing accepted reconnect
policy/DEC-036 D28/D18 — this record does not alter those, only the field
name (`changeFromQuantity`, C12) and the explicit ordering above.

---

## 11. Traceability (Pass 2 summary)

For both matrix rows, the full chain is unbroken:

**`inventorySetQuantities`:** product decision (DEC-010, unchanged) → Task
013 packet D-013-2/D-013-3/D-013-9 → §4 row 1 of this record → locked
Task 013 Sol prompt (Layer 2 integration section) → `test_inventory_push_mechanics.py`
(unit) + genuine-concurrency tests (Stage 0's proven pattern, extended)
→ Odoo.sh evidence (Task 013 §5, unchanged requirement) → dev-store
scenarios 1–8/10–12 (new plan) → rollback (Task 013 §6, unchanged
single-PR revert; attempt evidence retained per DEC-036 D32).

**`inventoryActivate`:** product decision (this record, §5, new
sequencing) → Task 013 packet D-013-3/D-013-9 → §4 row 2 of this record →
locked Task 013 Sol prompt → `test_inventory_push_mechanics.py` (new
activation assertions) → Odoo.sh evidence (same requirement, both
mutations covered) → dev-store scenario 9 (new plan) → rollback (same
mechanism, both matrix rows disabled together by the domain-enable flag).

---

## 12. Status

**PROPOSED FOR CONTROL-ROOM GATE B ACCEPTANCE.** No decision in this
record has been self-accepted. No DEC-036 decision is reopened. No
`addons/**` file was created or modified. No Odoo/Odoo.sh run occurred. No
Shopify mutation was issued — only Shopify **reads** (the two narrow
official-source page fetches in §2) were performed, consistent with this
session's execution limits.
