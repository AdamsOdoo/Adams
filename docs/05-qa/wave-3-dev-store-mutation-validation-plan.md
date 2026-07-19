# Wave 3 Dev-Store Mutation-Validation Plan — Task 013/013B Inventory

> **Status: GATE B ACCEPTANCE CANDIDATE — PLANNING ONLY. NOT EXECUTED. NO
> GATE OPENED.** Produced 2026-07-19, Wave 3 Gate B session, per
> [DEC-037](../04-decisions/DEC-037-wave-3-inventory-gate-b.md). This
> document defines the exact scenarios, preconditions, and evidence
> capture for the genuine dev-store mutation evidence Wave 3 requires
> ([`wave-3-definition-of-ready.md`](../07-implementation-plan/wave-3-definition-of-ready.md)
> §2.6). **This session did not execute any step of this plan and issued
> no Shopify mutation.** Execution is Task 013/013B implementation-wave
> scope (Sol, under the locked prompts), reviewed by the control room at
> wave-close.

---

## 1. Test store prerequisites

- A dedicated Shopify **development store** (Partner-Dashboard
  development store or an equivalent disposable test store), never a
  live merchant store.
- API access scoped at minimum: `read_inventory`, `write_inventory`,
  `read_products`, `read_locations` (location cache sync, Task 013
  D-013-5).
- Pinned API version **2026-07** (matching this connector's pinned
  version).
- The store must be reachable by the implementing session's Odoo.sh
  instance (credential path per DEC-028's accepted deployment posture).

## 2. Dedicated test fixtures (never shared with other domains' evidence)

- **Dedicated Shopify product/variant:** one product with exactly one
  variant, created solely for this plan, clearly named/tagged (e.g.
  `ZZ-GATEB-INV-TEST-01`) so it is never mistaken for real catalog data
  and can be deleted after the run.
- **Dedicated Shopify inventory item:** the `InventoryItem` behind that
  variant (1:1, automatic).
- **Dedicated Shopify location:** either a new disposable test location
  on the dev store, or an existing dev-store location reserved for this
  plan only (never a location shared with other domains' concurrent
  evidence capture, to avoid cross-scenario interference).
- **Matching Odoo product:** one Odoo product/variant bound to the
  Shopify variant above via the existing product-binding mechanism (Task
  010), used only for this plan.
- **Matching Odoo stock location:** one Odoo `stock.location` mapped 1:1
  to the dedicated Shopify location via `shopify.connector.location.mapping`
  (Task 013 D-013-1(a)).
- **Initial Shopify available:** 0 (the location starts with no
  `InventoryLevel` for the item — proves the activation path, scenario 9,
  is genuinely exercised, not skipped).
- **Initial Odoo `free_qty`:** a small, distinctive, non-zero value (e.g.
  `7`) at the mapped location, set via a normal Odoo stock quant, so the
  first push has an observably distinct target.

## 3. Mutation budget, authorization, evidence, redaction, restoration

- **Mutation budget:** exactly the mutations named per scenario below —
  no exploratory/ad hoc mutation calls against this store outside the
  enumerated scenarios. Each scenario states its own permitted mutation
  count.
- **Operator authorization point:** every scenario that reaches a
  Shopify mutation requires the human operator's explicit go-ahead
  immediately before that mutation fires — this plan does not authorize
  autonomous, unattended mutation execution. First-push scenarios (2, 13,
  14) additionally require the connector's own first-push
  preview/confirm flow (Task 013 D-013-4 / Task 013B D-013B-3), which is
  itself a second, independent confirmation layer.
- **Evidence capture:** for each scenario, capture (redacted): the
  GraphQL request shape (operation name + variable **names**, never raw
  tokens/credentials), the response's `userErrors`/outcome shape, the
  resulting `mutation.attempt` row's `observed_outcome`/
  `resolution_disposition` values, the job's final state, and the
  relevant job-log entries.
- **Redaction:** no credential, access token, or raw HTTP header may
  enter the evidence file. No PII exists in this domain (inventory
  carries no customer data), but store domain/shop name should still be
  redacted or replaced with a placeholder (e.g. `{DEV_STORE}`) in any
  evidence committed to the repository.
- **Restoration/rollback:** after all scenarios complete, delete the
  dedicated test product/variant (which also removes its inventory item
  and level) from the dev store; remove the dedicated Odoo product/stock
  quant/location-mapping test fixtures; confirm no dedicated test data
  remains referenced by any non-test job/binding row.

---

## 4. Scenarios

Each scenario states: preconditions, permitted mutation count, exact
operator approval, Odoo action, Shopify request, expected Odoo result,
expected Shopify result, expected job state, expected attempt state,
expected logs, cleanup, stop conditions.

### Scenario 1 — First-push preview

- **Preconditions:** fixtures per §2; binding row `first_push_state='pending'`.
- **Permitted mutations:** 0 (read-only preview).
- **Operator approval:** none required (dry-run).
- **Odoo action:** trigger `action_confirm_first_push()`'s preceding
  preview step (`inventory_first_push_preview` job) for the pair.
- **Shopify request:** none (preview computes from the last-known/fresh
  Odoo `free_qty`; may perform a read of current `InventoryLevel` if the
  handler chooses to preview against live Shopify state — read-only
  either way).
- **Expected Odoo result:** binding `first_push_state='previewed'`,
  `first_push_preview_qty` = the dedicated fixture's `free_qty` (7).
- **Expected Shopify result:** unchanged (no level exists yet).
- **Expected job state:** `done` (preview job).
- **Expected attempt state:** no `mutation.attempt` row created (no
  mutation attempted).
- **Expected logs:** preview job log entry recording the computed
  quantity.
- **Cleanup:** none needed; state carries into scenario 2.
- **Stop conditions:** preview quantity does not match the fixture's
  known `free_qty` → stop, investigate before proceeding.

### Scenario 2 — Explicit first-push confirmation

- **Preconditions:** scenario 1 complete (`first_push_state='previewed'`).
- **Permitted mutations:** 0 (confirmation is a local Odoo action).
- **Operator approval:** the human operator explicitly calls
  `action_confirm_first_push()` (Reviewer/Admin role), reviewing the
  scenario-1 preview quantity before confirming.
- **Odoo action:** `action_confirm_first_push()`.
- **Shopify request:** none.
- **Expected Odoo result:** binding `first_push_state='confirmed'`,
  `first_push_confirmed_at`/`first_push_confirmed_by_uid` recorded.
- **Expected Shopify result:** unchanged.
- **Expected job state:** N/A (not a job — a direct service-method call).
- **Expected attempt state:** none.
- **Expected logs:** confirmation actor/time recorded.
- **Cleanup:** none; state carries into scenario 9 (activation, since the
  level does not exist yet) then scenario 3.
- **Stop conditions:** confirmation succeeds without the preceding
  preview → stop, this is a guard defect.

### Scenario 3 — Successful `inventorySetQuantities`

- **Preconditions:** binding confirmed (scenario 2); scenario 9
  (activation) has already run and the level exists at `available=0`.
- **Permitted mutations:** 1 (`inventorySetQuantities`, target quantity
  7).
- **Operator approval:** operator triggers the push job (manual sync) or
  allows the odoo_event-triggered job to run, having already confirmed
  first-push in scenario 2.
- **Odoo action:** the `inventory_push_sync` job dispatches; Layer 2
  attempt: C2 commits intent with `changeFromQuantity=0` (the fresh read
  from scenario 9's activation), `quantity=7`; NET sends the mutation.
- **Shopify request:** `inventorySetQuantities(name: 'available',
  quantities: [{inventoryItemId, locationId, quantity: 7,
  changeFromQuantity: 0}]) @idempotent(key: <uuid>)`.
- **Expected Odoo result:** `mutation.attempt.observed_outcome='succeeded'`;
  binding's informational `last_pushed_available=7`/`last_pushed_at` set.
- **Expected Shopify result:** `InventoryLevel.quantities(names:
  ["available"])` for the pair returns `7`.
- **Expected job state:** `done`.
- **Expected attempt state:** `observed_outcome='succeeded'`,
  `resolution_disposition` null (not needed — direct success).
- **Expected logs:** attempt intent + outcome logged; no `userErrors`.
- **Cleanup:** none; state carries forward.
- **Stop conditions:** any `userErrors` on this call → stop, investigate
  before proceeding (this scenario expects a clean success).

### Scenario 4 — Successful `changeFromQuantity` CAS (normal round-trip)

- **Preconditions:** scenario 3 complete (Shopify `available=7`); Odoo
  `free_qty` changed to a new distinctive value (e.g. `4`) via a normal
  stock move.
- **Permitted mutations:** 1.
- **Operator approval:** operator allows the resulting push job to run.
- **Odoo action:** `inventory_push_sync` job for the pair; the handler
  reads the current Shopify `available` fresh (expected `7`) into
  `changeFromQuantity` before sending.
- **Shopify request:** `inventorySetQuantities(..., quantity: 4,
  changeFromQuantity: 7)`.
- **Expected Odoo result:** attempt `succeeded`.
- **Expected Shopify result:** `available=4`.
- **Expected job state:** `done`.
- **Expected attempt state:** `succeeded`.
- **Expected logs:** CAS basis (7) and target (4) both logged.
- **Cleanup:** none.
- **Stop conditions:** `CHANGE_FROM_QUANTITY_STALE` observed here (it
  should not be, since no concurrent writer exists) → stop, investigate
  the fresh-read mechanism.

### Scenario 5 — Deliberately provoked `CHANGE_FROM_QUANTITY_STALE`

- **Preconditions:** Shopify `available=4` (scenario 4). Immediately
  before the connector's push fires, the **operator manually** changes
  the Shopify level via the Shopify Admin UI (or a separate, out-of-band
  API call the operator makes directly, not through the connector) to a
  different value (e.g. `9`), simulating a concurrent external writer.
- **Permitted mutations:** 1 connector mutation attempt (which is
  expected to fail with `CHANGE_FROM_QUANTITY_STALE`) + 1 operator-made
  out-of-band mutation (the provoking change, made directly via Shopify
  Admin, not via the connector's Layer 2 wrapper — this is the "someone
  else changed it" simulation, not a connector-issued mutation).
- **Operator approval:** the operator explicitly performs the
  out-of-band change and then allows the connector's queued push to
  proceed.
- **Odoo action:** the connector's stale attempt sends
  `changeFromQuantity=4` (its last fresh read, now stale).
- **Shopify request:** `inventorySetQuantities(..., changeFromQuantity: 4)`
  against a level now at `9` → `CHANGE_FROM_QUANTITY_STALE` `userError`.
- **Expected Odoo result:** attempt `observed_outcome='failed_clean'`
  (clean rejection); routes to a **new** bounded retry attempt (1 of 3)
  with a fresh `changeFromQuantity` read (`9`).
- **Expected Shopify result:** the retry succeeds, setting the intended
  target against the now-current `9` basis.
- **Expected job state:** `done` after the successful retry.
- **Expected attempt state:** first attempt `failed_clean`; second
  attempt (new `attempt_token`) `succeeded`.
- **Expected logs:** both attempts logged distinctly; retry count = 1.
- **Cleanup:** none.
- **Stop conditions:** more than 3 bounded retries needed → stop
  (indicates a persistent divergence the design did not anticipate for
  this scenario); no retry attempted at all → stop (guard defect).

### Scenario 6 — Same-key exact-request idempotent replay

- **Preconditions:** a push job in flight; the operator simulates a
  network-level retry (e.g. by the connector's own transport-layer retry
  logic re-sending the identical request within `idempotency_valid_until`)
  rather than a fresh CAS-driven attempt.
- **Permitted mutations:** 1 logical mutation, sent twice at the
  transport layer with the identical `@idempotent` key and identical
  variables (same `exact_request_fingerprint`).
- **Operator approval:** operator triggers the controlled replay (e.g.
  via a test harness that resends the exact same signed request).
- **Odoo action:** none beyond the original attempt; Layer 2 does not
  create a second `mutation.attempt` row for a same-key transport retry.
- **Shopify request:** the identical `inventorySetQuantities` call,
  same `@idempotent(key: ...)`, sent twice.
- **Expected Odoo result:** the connector's own attempt/outcome recording
  reflects a single logical effect.
- **Expected Shopify result:** Shopify returns the cached original
  response on the second send, without re-executing (per the accepted
  24h idempotency-window fact) — inventory changes exactly once, not
  twice.
- **Expected job state:** `done`, once.
- **Expected attempt state:** one attempt row; `succeeded`.
- **Expected logs:** the replay is observable as a second HTTP round trip
  producing an identical response.
- **Cleanup:** none.
- **Stop conditions:** the second send produces a **different** result
  or a visibly different inventory effect → stop immediately, this would
  indicate a genuine idempotency-guarantee violation on Shopify's side or
  a fingerprint-construction defect on this connector's side — escalate
  to the control room, do not proceed with further scenarios until
  resolved.

### Scenario 7 — Uncertainty and reconciliation

- **Preconditions:** a push job ready to dispatch.
- **Permitted mutations:** 1 (its outcome is deliberately made
  unobservable to the connector, e.g. by the test harness injecting a
  network timeout on the response leg after the request was actually
  sent — the operator must confirm via the Shopify Admin UI, out of
  band, whether the mutation actually landed, to score this scenario,
  without revealing that answer to the connector under test).
- **Operator approval:** the operator sets up the timeout-injection
  harness and confirms afterward, out of band, what actually happened on
  Shopify's side (for scoring only, not fed back into the connector).
- **Odoo action:** the attempt's C3 outcome-commit observes a timeout →
  `observed_outcome='uncertain'`; `reconciliation_pending_until` set; a
  linked `remote_read_replay_safe` reconciliation job created.
- **Shopify request:** the original (ambiguous-outcome) mutation, plus
  the reconciliation job's `InventoryLevel.quantities` read.
- **Expected Odoo result:** the reconciliation read correctly determines
  applied/not-applied based on the actual post-mutation Shopify value,
  matching the operator's out-of-band observation.
- **Expected Shopify result:** exactly one logical effect (whether the
  original ambiguous call landed or not, no duplicate mutation is ever
  sent while the reconciliation is pending).
- **Expected job state:** `done` (if applied) or requeued with a fresh
  attempt (if not-applied).
- **Expected attempt state:** `uncertain` (permanently, immutable) +
  `resolution_disposition` set from the reconciliation verdict.
- **Expected logs:** the full uncertain→reconciled sequence logged.
- **Cleanup:** none.
- **Stop conditions:** the reconciliation verdict disagrees with the
  operator's out-of-band observation → stop, this is a reconciliation
  logic defect, escalate before proceeding.

### Scenario 8 — Idempotency concurrent-request handling (where safely reproducible)

- **Preconditions:** a push job ready to dispatch.
- **Permitted mutations:** 2 near-simultaneous sends of the identical
  `@idempotent`-keyed request, deliberately raced by the test harness (if
  safely reproducible against the dev store — if not reliably
  reproducible, this scenario is recorded as **not-executable** with the
  reason stated, not silently skipped).
- **Operator approval:** operator runs the racing-request harness.
- **Odoo action:** the connector's own attempt bookkeeping expects at
  most one of the two races to observe `IDEMPOTENCY_CONCURRENT_REQUEST`.
- **Shopify request:** two concurrent `inventorySetQuantities` calls,
  identical key.
- **Expected Odoo result:** the race loser's response is classified
  `observed_outcome='uncertain'` (DEC-036 D6), never `failed_clean`;
  reconciliation resolves it.
- **Expected Shopify result:** exactly one logical mutation effect.
- **Expected job state:** both jobs eventually `done` with no duplicate
  effect.
- **Expected attempt state:** one attempt `succeeded`, the racing one
  `uncertain`→resolved `applied` (same effect, correctly not resent).
- **Expected logs:** both attempts logged, race outcome visible.
- **Cleanup:** none.
- **Stop conditions:** not reliably reproducible against this dev store
  → record as not-executable, state the reason, do not block the wave on
  it (per this session's task §16 requirement to state this explicitly
  rather than silently skip).

### Scenario 9 — `inventoryActivate` when needed

- **Preconditions:** the pair's `InventoryLevel` does not yet exist at
  the mapped location (true from onboarding per §2); binding confirmed
  (scenario 2).
- **Permitted mutations:** 1 (`inventoryActivate`).
- **Operator approval:** implicit in the first-push confirmation
  (scenario 2) — activation is part of the same reviewed first-push flow,
  not a separately re-confirmed action, per DEC-037 §6.
- **Odoo action:** the push handler observes `ITEM_NOT_STOCKED_AT_LOCATION`
  (or proactively detects the missing level) and issues the
  `inventory_activate` mutation domain's own Layer 2 attempt.
- **Shopify request:** `inventoryActivate(inventoryItemId, locationId,
  available: 0, stockAtLegacyLocation: false)` — `available` sent
  explicitly, never omitted.
- **Expected Odoo result:** `mutation.attempt` (domain `inventory_activate`)
  `observed_outcome='succeeded'`.
- **Expected Shopify result:** `InventoryLevel` now exists,
  `available=0`, `on_hand=0`.
- **Expected job state:** the enclosing `inventory_push_sync` job
  proceeds to scenario 3's set-quantities attempt immediately after.
- **Expected attempt state:** two distinct attempt rows in sequence
  (`inventory_activate` then `inventory_set_quantities`), two distinct
  `attempt_token`/idempotency-key values (DEC-037 §5).
- **Expected logs:** activation logged distinctly from the set-quantities
  attempt that follows it.
- **Cleanup:** none; feeds directly into scenario 3.
- **Stop conditions:** the post-activation level is nonzero → stop
  (`binding_conflict`, unexplained), never proceed to set-quantities on
  an unreviewed nonzero baseline.

### Scenario 10 — Reconnect read-before-push

- **Preconditions:** scenario 3/4 complete (Shopify `available` at a
  known value); a pending push target exists in Odoo.
- **Permitted mutations:** 0 for the reconnect step itself (read-only);
  1 for the subsequent push once cleared.
- **Operator approval:** operator disconnects and reconnects the dev
  store's credentials (`action_reconnect`).
- **Odoo action:** reconnect sequence runs; a reconciliation read
  (`remote_read_replay_safe`) of the mapped pair executes before any new
  push job is admitted.
- **Shopify request:** `InventoryLevel.quantities` read only, plus
  `shop { myshopifyDomain }` for the store-identity check.
- **Expected Odoo result:** the pending push target is recomputed against
  the fresh read; the push then proceeds normally (scenario 3-equivalent).
- **Expected Shopify result:** unchanged until the subsequent push.
- **Expected job state:** reconciliation job `done` before the push job
  is ever admitted.
- **Expected attempt state:** no mutation attempt exists until after the
  reconciliation read clears.
- **Expected logs:** reconnect sequence's eight steps observable in
  order (per the reconnect UAT matrix UAT-RB-1.1).
- **Cleanup:** none.
- **Stop conditions:** any push job admitted before the reconciliation
  read completes → stop, this is a blind-push defect.

### Scenario 11 — Unexplained drift, review-case-first

- **Preconditions:** Shopify `available` at a known value (e.g. `4`,
  post-scenario 4); Odoo `free_qty` unchanged since the last push.
- **Permitted mutations:** 0 connector mutations (the drift is provoked
  by an operator out-of-band change, then a scan runs and must **not**
  mutate).
- **Operator approval:** operator manually changes the Shopify level via
  Admin UI to an unexplained value (e.g. `2`, matching neither the
  last-pushed value nor any known Odoo-side change) before the next scan.
- **Odoo action:** the scheduled reconciliation/push-scan job's fresh
  read observes `available=2`, which matches neither `last_pushed_available`
  (4) nor current Odoo `free_qty`-derived target.
- **Shopify request:** the scan's read only; **no** `inventorySetQuantities`
  call is made for this pair.
- **Expected Odoo result:** a review case is created for the pair; the
  pending push is blocked.
- **Expected Shopify result:** unchanged (no overwrite).
- **Expected job state:** the scan job completes; no push job is created
  for this pair until the review case clears.
- **Expected attempt state:** no mutation attempt created.
- **Expected logs:** the review case's three values (Shopify current /
  last-pushed / Odoo current) logged.
- **Cleanup:** operator resolves the review case (e.g. confirms a fresh
  push), restoring the pair to a known state before further scenarios.
- **Stop conditions:** the scan pushes over the drift without creating a
  review case → stop immediately, this is the exact behavior DEC-037 §1
  item C6 forbids.

### Scenario 12 — Negative `free_qty` clamp

- **Preconditions:** Odoo `free_qty` for the pair driven negative (e.g.
  via an over-reservation on a test order) — a normal, reproducible Odoo
  state, not a Shopify-side action.
- **Permitted mutations:** 1 (the clamped push).
- **Operator approval:** operator triggers the push.
- **Odoo action:** the handler computes the clamp: target sent to
  Shopify = `max(0, free_qty)` = `0`; a divergence warning is logged
  carrying the true negative value.
- **Shopify request:** `inventorySetQuantities(..., quantity: 0, ...)`.
- **Expected Odoo result:** attempt `succeeded`; divergence warning
  logged with the true (negative) Odoo value.
- **Expected Shopify result:** `available=0`, never a negative value
  (consistent with `INVALID_QUANTITY_NEGATIVE` existing as a live,
  never-triggered guard).
- **Expected job state:** `done`.
- **Expected attempt state:** `succeeded`.
- **Expected logs:** clamp + warning entry.
- **Cleanup:** resolve the over-reservation fixture.
- **Stop conditions:** a negative value is ever sent to Shopify → stop
  immediately, hard safety violation.

### Scenario 13 — Task 013B preview

- **Preconditions:** a second dedicated pair (or the same pair reset to
  an onboarding-like state) with Shopify `available` at a known nonzero
  value and Odoo `free_qty` at a different known value, simulating a
  merchant onboarding with pre-existing Shopify stock.
- **Permitted mutations:** 0 (Task 013B preview is read-only — no Layer 2
  involvement, §0 of the Task 013B packet).
- **Operator approval:** none required for the preview step itself.
- **Odoo action:** `inventory_baseline_preview` job runs; reads Shopify
  `available`, computes `target_on_hand = desired_free + current_reserved`.
- **Shopify request:** `InventoryLevel.quantities` read only.
- **Expected Odoo result:** `shopify.connector.inventory.baseline.run`
  record in state `previewed`, with the correct per-pair
  free/on-hand/reserved/target breakdown.
- **Expected Shopify result:** unchanged.
- **Expected job state:** `done`.
- **Expected attempt state:** N/A (no Layer 2 attempt for this task).
- **Expected logs:** preview breakdown logged.
- **Cleanup:** none; feeds scenario 14.
- **Stop conditions:** the preview's `target_on_hand` arithmetic does not
  match `desired_free + reserved` exactly → stop.

### Scenario 14 — Task 013B confirmation

- **Preconditions:** scenario 13 complete, preview unexpired.
- **Permitted mutations:** 0.
- **Operator approval:** `action_confirm_baseline_run()` (Reviewer/Admin),
  reviewing the scenario-13 breakdown before confirming.
- **Odoo action:** the run record transitions to `confirmed`.
- **Shopify request:** none.
- **Expected Odoo result:** `confirmed_by`/`confirmed_at` recorded.
- **Expected Shopify result:** unchanged.
- **Expected job state:** N/A (direct service-method call).
- **Expected attempt state:** N/A.
- **Expected logs:** confirmation actor/time recorded.
- **Cleanup:** none; feeds scenario 15.
- **Stop conditions:** confirmation succeeds against an expired preview
  → stop, guard defect.

### Scenario 15 — Task 013B apply

- **Preconditions:** scenario 14 complete (confirmed, unexpired).
- **Permitted mutations:** 0 Shopify mutations (Task 013B never mutates
  Shopify); 1 **local Odoo** inventory adjustment.
- **Operator approval:** the apply job is enqueued only after scenario
  14's confirmation; no further approval gate (the confirmation **is**
  the approval for apply).
- **Odoo action:** the apply handler acquires row locks
  (`try_lock_for_update()`) on the dependent quant/binding/mapping rows,
  re-reads under lock, computes and books `target_on_hand`, verifies
  post-write `free_qty == desired_shopify_available`.
- **Shopify request:** none (read-only toward Shopify throughout this
  task).
- **Expected Odoo result:** `stock.quant` counted on-hand adjusted;
  post-write `free_qty` matches the confirmed preview's `desired_free`;
  `baseline_applied_at`/`baseline_run_id` stamped on the level binding.
- **Expected Shopify result:** unchanged (Task 013B never writes
  Shopify).
- **Expected job state:** `done`.
- **Expected attempt state:** N/A.
- **Expected logs:** prior/on-hand/reserved/new/delta evidence logged.
- **Cleanup:** this pair is now Task-013-authoritative; the next Task 013
  push for it begins from this baselined state.
- **Stop conditions:** post-write `free_qty` verification fails → the
  apply must roll back to `blocked_manual_review`/`binding_conflict`,
  never leave an unverified baseline.

### Scenario 16 — Task 013B drift abort

- **Preconditions:** scenario 14 complete (confirmed, unexpired).
- **Permitted mutations:** 0 Shopify; 0 local Odoo (this scenario proves
  the abort path, not a successful write).
- **Operator approval:** operator deliberately introduces a competing
  Odoo-side change (e.g. a concurrent reservation or quant change against
  the same pair) between confirmation and apply, in a second
  transaction/session, to provoke the drift-abort path.
- **Odoo action:** the apply handler's under-lock re-read detects the
  drift (value or quant-topology change from the confirmed preview
  snapshot) and aborts before writing.
- **Shopify request:** none.
- **Expected Odoo result:** no adjustment written;
  `destructive_write_guard_blocked`; the operator must re-preview.
- **Expected Shopify result:** unchanged.
- **Expected job state:** the apply job fails closed, not `done`.
- **Expected attempt state:** N/A.
- **Expected logs:** the detected drift (old vs. new value/topology)
  logged.
- **Cleanup:** resolve the competing change, re-preview, re-confirm.
- **Stop conditions:** the apply proceeds despite the provoked drift →
  stop immediately, this is the exact race the row-lock design exists to
  prevent.

### Scenario 17 — PB-20 throughput measurement

- **Preconditions:** a set of dedicated test pairs (≥10, all clearly
  tagged per §2, never overlapping with other domains' concurrent
  evidence capture) each requiring a push.
- **Permitted mutations:** one `inventorySetQuantities` call per pair
  (one-pair-per-request, no batching) — the count is bounded by the
  number of dedicated test pairs prepared for this scenario, stated in
  the evidence record before the run.
- **Operator approval:** operator triggers the batch of pushes (e.g. via
  `action_push_inventory_now()` across the dedicated test pairs) and
  monitors the run.
- **Odoo action:** the push-scan/manual-sync path dispatches one job per
  pair.
- **Shopify request:** one `inventorySetQuantities` call per pair,
  paced by `throttleStatus`.
- **Expected Odoo result:** all dedicated pairs reach `succeeded`.
- **Expected Shopify result:** each pair's `available` matches its sent
  target.
- **Expected job state:** all `done`.
- **Expected attempt state:** all `succeeded`.
- **Expected logs:** measured throughput (pushes/hour extrapolated from
  the observed rate) recorded against the PB-20 ≥300/hour target.
- **Cleanup:** none beyond the general restoration in §3.
- **Stop conditions:** measured throughput cannot be extrapolated to meet
  PB-20 within the observed throttle budget → record as a Stage-1 sizing
  finding for the control room, not a silent pass.

---

## 5. No silent caps

Every scenario above either executes fully, is explicitly marked
not-executable with a stated reason (scenario 8's possible outcome), or
is intentionally bounded (scenario 17's pair count, stated before the
run). No scenario's mutation count or coverage may be silently reduced
without recording the reduction and its reason in the eventual validation
results document.

---

*References: DEC-036 (Layer 2 substrate, ACCEPTED), DEC-037 (Gate B —
this plan's own decision basis), the Task 013/013B packets, the
inventory operating model, the reconnect/backfill policy, the Wave 3
Definition of Ready §2.6. Execution produces
`docs/05-qa/task-013-inventory-sync-validation-results.md` and
`docs/05-qa/task-013b-validation-results.md` (created at implementation
time, not by this plan).*
