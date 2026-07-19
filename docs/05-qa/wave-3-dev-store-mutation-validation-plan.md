# Wave 3 Dev-Store Mutation-Validation Plan — Task 013/013B Inventory

> **Status: GATE B ACCEPTANCE CANDIDATE (Revision 3) — PLANNING ONLY. NOT
> EXECUTED. NO GATE OPENED.** Produced 2026-07-19, Wave 3 Gate B session,
> corrected Revision 3 same date per control-room comment `5015830229`:
> scenarios 3/5/9 corrected for the one-job/one-attempt-lifetime job
> model (a CAS retry or an activation handoff creates a **new**, atomic
> job — never a same-job redispatch or a later scan/trigger dependency);
> scenario 19's error-class value corrected to the fixed vocabulary; two
> new scenarios (20, 21) cover `blocked_manual_review` non-automatic-child
> behavior and the `action_recheck_inventory_pair` release action; per
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
  (activation, its own separate job) has already gone terminal
  `succeeded`, and — **atomically, in the same transaction that
  terminalized the activation job** (DEC-037 §5.2 step 7/§5.4 handoff B;
  Revision 3: this is not a later, separately-admitted scan/manual
  trigger) — a fresh `inventory_push_sync` orchestration dispatch (a
  distinct job from scenario 9's activation job) was enqueued, has
  re-read Shopify, found the level at `available=0`, and enqueued this
  scenario's `inventory_set_quantities` job.
- **Permitted mutations:** 1 (`inventorySetQuantities`, target quantity
  7).
- **Operator approval:** operator triggers the push (manual sync) or
  allows the odoo_event-triggered orchestration job to run, having
  already confirmed first-push in scenario 2.
- **Odoo action:** the standalone `inventory_set_quantities` job (its own
  `job_type`/`job_type == mutation_domain`, its own job ID, distinct from
  both the intervening orchestration job and scenario 9's `inventory_activate`
  job) dispatches its own Layer 2 attempt: C2 commits intent with
  `changeFromQuantity=0` (the fresh read the intervening orchestration
  dispatch obtained), `quantity=7`; NET sends the mutation.
- **Shopify request:** `inventorySetQuantities(name: 'available',
  quantities: [{inventoryItemId, locationId, quantity: 7,
  changeFromQuantity: 0}]) @idempotent(key: <uuid>)`.
- **Expected Odoo result:** `mutation.attempt.observed_outcome='succeeded'`;
  binding's informational `last_pushed_available=7`/`last_pushed_at` set.
- **Expected Shopify result:** `InventoryLevel.quantities(names:
  ["available"])` for the pair returns `7`.
- **Expected job state:** `done`.
- **Expected attempt state:** `observed_outcome='succeeded'`,
  `resolution_disposition` null (not needed — direct success). Evidence
  must record this attempt's `job_type`/job ID/`mutation_domain`/
  `attempt_token`/idempotency key as distinct from the intervening
  orchestration job's and scenario 9's activation job's own values.
- **Expected logs:** attempt intent + outcome logged; no `userErrors`.
- **Cleanup:** none; state carries forward.
- **Stop conditions:** any `userErrors` on this call → stop, investigate
  before proceeding (this scenario expects a clean success); this job
  directly enqueued by scenario 9's activation job (rather than by a
  fresh, independent orchestration dispatch) → stop, this is the exact
  direct-mutation-chaining defect DEC-037 §5 forbids.

### Scenario 4 — Successful `changeFromQuantity` CAS (normal round-trip)

- **Preconditions:** scenario 3 complete (Shopify `available=7`); Odoo
  `free_qty` changed to a new distinctive value (e.g. `4`) via a normal
  stock move.
- **Permitted mutations:** 1.
- **Operator approval:** operator allows the resulting push job to run.
- **Odoo action:** a fresh `inventory_push_sync` orchestration dispatch
  for the pair reads the current Shopify `available` fresh (expected `7`)
  and, finding the pair safe to push, enqueues a new
  `inventory_set_quantities` job; that job's own handler uses the
  orchestration read as `changeFromQuantity` before sending — the
  orchestration job itself never sends the mutation.
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

### Scenario 5 — Deliberately provoked `CHANGE_FROM_QUANTITY_STALE`, replacement-job model (corrected, Revision 3, DEC-037 §4 row 1/§5.4 handoff C)

- **Preconditions:** Shopify `available=4` (scenario 4); the confirmed
  pair's `inventory_set_quantities` job at `cas_retry_ordinal=0`.
  Immediately before the connector's push fires, the **operator
  manually** changes the Shopify level via the Shopify Admin UI (or a
  separate, out-of-band API call the operator makes directly, not
  through the connector) to a different value (e.g. `9`), simulating a
  concurrent external writer.
- **Permitted mutations:** 1 connector mutation attempt (which is
  expected to fail with `CHANGE_FROM_QUANTITY_STALE`) + 1 operator-made
  out-of-band mutation (the provoking change, made directly via Shopify
  Admin, not via the connector's Layer 2 wrapper — this is the "someone
  else changed it" simulation, not a connector-issued mutation).
- **Operator approval:** the operator explicitly performs the
  out-of-band change and then allows the connector's queued push to
  proceed.
- **Odoo action:** the `cas_retry_ordinal=0` job's single attempt sends
  `changeFromQuantity=4` (its last fresh read, now stale).
- **Shopify request:** `inventorySetQuantities(..., changeFromQuantity: 4)`
  against a level now at `9` → `CHANGE_FROM_QUANTITY_STALE` `userError`.
- **Expected Odoo result:** the `cas_retry_ordinal=0` job's attempt
  observes `observed_outcome='failed_clean'`,
  `error_class='concurrency_race_conflict'`. **Revision 3 correction:**
  this job then **terminalizes** — `superseded_by_job_id` set,
  `cancel_reason='cas_stale_bounded_replacement'` — atomically, in the
  same transaction, with a **new**, separate `inventory_set_quantities`
  job created at `cas_retry_ordinal=1`, carrying its own fresh job ID,
  `attempt_token`, idempotency key, and a fresh `changeFromQuantity`
  read (`9`). This job is **never redispatched** to make a second
  attempt itself.
- **Expected Shopify result:** the ordinal-1 job's attempt succeeds,
  setting the intended target against the now-current `9` basis.
- **Expected job state:** the `cas_retry_ordinal=0` job is terminal
  (`failed_clean`, superseded); the `cas_retry_ordinal=1` job is `done`
  after its own successful attempt.
- **Expected attempt state:** exactly one `mutation.attempt` row on the
  ordinal-0 job (`failed_clean`); exactly one `mutation.attempt` row on
  the distinct ordinal-1 job (`succeeded`) — never two attempt rows on
  one job.
- **Expected logs:** both jobs' single attempts logged distinctly, plus
  the `superseded_by_job_id` lineage linking ordinal 0 → ordinal 1.
- **Cleanup:** none.
- **Stop conditions:** the ordinal-0 job is found to make a second
  attempt itself (redispatched) rather than terminalizing and handing
  off to a new ordinal-1 job → stop immediately, this is the exact
  same-job-redispatch defect binding correction 1 (control-room comment
  `5015830229`) forbids; more than 3 bounded replacements needed → stop
  (indicates a persistent divergence the design did not anticipate for
  this scenario, and would exercise the ordinal-3 exhaustion path
  instead — see the note below); no replacement job created at all →
  stop (guard defect).
- **Note (ordinal-3 exhaustion, not separately re-run in this
  scenario):** were a 4th `CHANGE_FROM_QUANTITY_STALE` to occur on the
  job at `cas_retry_ordinal=3`, no further replacement job would be
  created — that job terminalizes `blocked_manual_review`/
  `binding_conflict` instead, and the pending target stays coalesced on
  the binding. Implementation evidence must include this exhaustion path
  as part of the genuine-concurrency/unit test matrix (DEC-037 §4 row 1
  exact tests), even though this dev-store scenario exercises only the
  ordinal 0→1 replacement.

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

### Scenario 9 — `inventoryActivate` when needed (own job, Revision 2)

- **Preconditions:** the pair's `InventoryLevel` does not yet exist at
  the mapped location (true from onboarding per §2); binding confirmed
  (scenario 2). A **prior** `inventory_push_sync` orchestration dispatch
  has already run, read Shopify, found no existing level for this pair,
  and — because `first_push_state='confirmed'` — enqueued this scenario's
  `inventory_activate` job (DEC-037 §5.2 step 5). This scenario does
  **not** begin from a set-quantities attempt observing
  `ITEM_NOT_STOCKED_AT_LOCATION` — that race case is scenario 19.
- **Permitted mutations:** 1 (`inventoryActivate`).
- **Operator approval:** implicit in the first-push confirmation
  (scenario 2) — activation is part of the same reviewed first-push flow,
  not a separately re-confirmed action, per DEC-037 §6.
- **Odoo action:** the standalone `inventory_activate` job (its own
  `job_type == mutation_domain`, its own job ID, enqueued by the
  orchestration dispatch above, never by a set-quantities job) runs its
  own Layer 2 attempt.
- **Shopify request:** `inventoryActivate(inventoryItemId, locationId,
  available: 0, stockAtLegacyLocation: false)` — `available` sent
  explicitly, never omitted.
- **Expected Odoo result:** `mutation.attempt` (domain `inventory_activate`,
  on the `inventory_activate` job) `observed_outcome='succeeded'`.
- **Expected Shopify result:** `InventoryLevel` now exists,
  `available=0`, `on_hand=0`.
- **Expected job state:** this `inventory_activate` job goes **terminal**
  (`succeeded`) on its own — it does **not** enqueue, dispatch, or
  contain any `inventorySetQuantities` call. **Revision 3 correction:**
  atomically, in the **same transaction** that terminalizes this job as
  `succeeded` (DEC-037 §5.2 step 7/§5.4 handoff B) — not dependent on a
  later, separately-admitted scan or manual trigger — a **fresh,
  separate** `inventory_push_sync` orchestration job is enqueued for the
  pair, which re-reads Shopify (now `available=0`) and enqueues the
  `inventory_set_quantities` job exercised in scenario 3.
- **Expected attempt state:** exactly one `mutation.attempt` row for this
  job (domain `inventory_activate`); its `job_type`/job ID/`attempt_token`/
  idempotency key must all be distinct from the intervening orchestration
  job's and from scenario 3's `inventory_set_quantities` job's — evidence
  must record all four as distinct values, plus the pair-serialization
  `operation_scope_key` as the one value shared across all three jobs
  (DEC-037 §5.3).
- **Expected logs:** activation logged on its own job; the subsequent
  orchestration re-read and scenario 3's set-quantities job are logged as
  separate job records, connected only by the shared pair-serialization
  identity.
- **Cleanup:** none; feeds the intervening orchestration dispatch, which
  feeds scenario 3.
- **Stop conditions:** the post-activation level is nonzero → stop
  (`binding_conflict`, unexplained), never proceed to a set-quantities
  push on an unreviewed nonzero baseline; this job directly enqueues or
  contains an `inventorySetQuantities` call → stop immediately, this is
  the exact same-job/two-mutation defect DEC-037 §5 forbids.

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
- **Odoo action:** the push-scan/manual-sync path dispatches, per pair, an
  `inventory_push_sync` orchestration job followed (once admitted) by an
  `inventory_set_quantities` mutation job — two job dispatches per pair,
  exactly one Shopify mutation call per pair (no activation needed, since
  every dedicated pair already has a confirmed baseline level from
  earlier scenarios).
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

### Scenario 18 — ABA/freshness protection (new, Revision 2, DEC-037 §4 row 1)

- **Preconditions:** a push job ready to dispatch; Shopify `available` at
  a known value (e.g. `4`).
- **Permitted mutations:** 1 connector mutation (deliberately made
  uncertain, as in scenario 7) + 2 operator-made out-of-band changes (the
  ABA round-trip — see below), all against the dedicated test pair only.
- **Operator approval:** the operator sets up a timeout-injection harness
  (as scenario 7) on the connector's `inventorySetQuantities` call, then,
  while the connector's outcome remains `uncertain`, performs two
  out-of-band Admin-UI changes in sequence: first to a **different** value
  (e.g. `9`), then back to the **original pre-attempt** value (`4`) —
  simulating a third-party ABA write that lands after the connector's
  attempt but resolves back to the same numeric value the connector's own
  `changeFromQuantity` used.
- **Odoo action:** the attempt's C3 outcome-commit observes the timeout →
  `observed_outcome='uncertain'`; the linked reconciliation read then
  observes `available=4` — numerically identical to the pre-attempt
  `changeFromQuantity` — but with `InventoryQuantity.updatedAt` **later**
  than this attempt's `transport_at` (because of the intervening ABA
  writes).
- **Shopify request:** the original (ambiguous-outcome) mutation, plus the
  reconciliation job's `InventoryLevel.quantities` read (requesting
  `updatedAt` where the schema exposes it).
- **Expected Odoo result:** the reconciliation verdict is
  **`inconclusive`**, never `not_applied` — a same-value read whose
  `updatedAt` postdates the attempt must not be treated as proof the
  attempt had no effect (DEC-037 §4 row 1, binding correction 4).
  `inconclusive_reconciliation_count` increments; a further reconciliation
  read is scheduled.
- **Expected Shopify result:** unchanged by this scenario beyond the
  operator's own out-of-band changes.
- **Expected job state:** requeued for a further reconciliation read, not
  closed `done` and not immediately retried with a fresh attempt.
- **Expected attempt state:** `uncertain` (permanently) +
  `resolution_disposition` left unset (inconclusive is not a terminal
  disposition).
- **Expected logs:** the ABA sequence (pre-attempt value → intervening
  value → post-attempt value, with timestamps) fully logged for audit.
- **Cleanup:** resolve the pair to a known state before further scenarios.
- **Stop conditions:** the reconciliation verdict is `not_applied` despite
  the later `updatedAt` → stop immediately, this is the exact false-negative
  defect DEC-037 §4 row 1's freshness/ABA rule exists to prevent, escalate
  to the control room.

### Scenario 19 — `ITEM_NOT_STOCKED_AT_LOCATION` race, fail-closed (new, Revision 2, DEC-037 §4 row 1/§5)

- **Preconditions:** a pair whose binding is `first_push_state='confirmed'`
  and whose prior `inventory_push_sync` orchestration read believed a
  Shopify level existed (e.g. immediately after scenario 9/3, before this
  scenario's provoking change). Immediately before the connector's
  `inventory_set_quantities` job sends its request, the **operator**
  manually deactivates the level via the Shopify Admin UI (or an
  equivalent out-of-band action), so the level genuinely does not exist
  by send time — simulating a race between the orchestration read and the
  mutation send.
- **Permitted mutations:** 1 connector mutation (expected to fail with
  `ITEM_NOT_STOCKED_AT_LOCATION`) + 1 operator-made out-of-band
  deactivation.
- **Operator approval:** the operator performs the out-of-band
  deactivation and then allows the connector's queued `inventory_set_quantities`
  job to proceed.
- **Odoo action:** the `inventory_set_quantities` job's attempt observes
  `ITEM_NOT_STOCKED_AT_LOCATION`.
- **Shopify request:** `inventorySetQuantities(...)` against a pair whose
  level no longer exists → `ITEM_NOT_STOCKED_AT_LOCATION` `userError`.
- **Expected Odoo result:** `observed_outcome='failed_clean'`,
  `error_class='inventory_location_missing'` (Revision 3 — the fixed
  vocabulary value; corrects the earlier draft's invented
  `remote_precondition_mismatch`), routes to
  `blocked_manual_review`/`inventory_location_missing` — **this job issues
  no `inventoryActivate` call, inline or otherwise, in any form.** The
  pending target stays coalesced on the binding.
- **Expected Shopify result:** unchanged by this job (no activation, no
  set-quantities value recorded).
- **Expected job state:** the `inventory_set_quantities` job goes terminal
  `blocked_manual_review`. Only a later, independently-triggered fresh
  `inventory_push_sync` orchestration dispatch (not created by this job)
  re-reads Shopify, correctly finds the level absent, and — since
  `first_push_state='confirmed'` — enqueues a new `inventory_activate`
  job (exercising the same path as scenario 9).
- **Expected attempt state:** one `mutation.attempt` row, domain
  `inventory_set_quantities`, `failed_clean`; no `inventory_activate`
  attempt exists until the later, separate orchestration-triggered job
  runs.
- **Expected logs:** the diagnostic `UserError.message` text may be
  captured (redacted) for human triage only — it is not used to select
  any error class, retry decision, or manual-review subreason (DEC-037 §4
  row 2's uniform-classification rule applies to message-text handling
  generally in this module).
- **Cleanup:** resolve the review case (operator re-confirms and lets the
  next scan re-orchestrate), restoring the pair to a known state.
- **Stop conditions:** this job issues `inventoryActivate` in any form
  (inline call, direct enqueue from within this job, or reuse of this
  job's own attempt/idempotency key for an activation call) → stop
  immediately, this is the exact defect binding correction 1 (control-room
  comment `5015619162`) forbids.

### Scenario 20 — `blocked_manual_review` is not terminal; no automatic child (new, Revision 3, DEC-037 §5.5)

- **Preconditions:** scenario 19 complete — the pair's
  `inventory_set_quantities` job is `blocked_manual_review`
  (`inventory_location_missing`), holding the pair's
  `operation_scope_key`. No review action has yet been performed.
- **Permitted mutations:** 0.
- **Operator approval:** none — this scenario proves the *absence* of
  automatic action while blocked.
- **Odoo action:** the normal scheduled push-scan cron fires for the
  store while the pair remains blocked; separately, a normal Odoo stock
  move changes `free_qty` for the same pair (simulating ordinary
  business activity continuing while the pair is under review).
- **Shopify request:** none for this pair (the scan skips pairs whose
  `operation_scope_key` is already held).
- **Expected Odoo result:** no new `inventory_push_sync`,
  `inventory_activate`, or `inventory_set_quantities` job is created for
  this pair by the scan or by the stock-move trigger; the new `free_qty`
  instead coalesces onto the binding's `pending_target_available`
  (DEC-037 §10), to be read once the pair is released.
- **Expected Shopify result:** unchanged.
- **Expected job state:** the blocked job remains the pair's sole
  non-terminal job; no sibling or child job exists for the pair.
- **Expected attempt state:** unchanged from scenario 19 — no new
  attempt created.
- **Expected logs:** the scan's own log shows the pair skipped
  (blocked), not silently ignored.
- **Cleanup:** none; feeds scenario 21.
- **Stop conditions:** any new job of any of the three inventory job
  types is created for this pair while it remains `blocked_manual_review`
  → stop immediately, this is the exact automatic-child-from-blocked-review
  defect DEC-037 §5.5 forbids.

### Scenario 21 — `action_recheck_inventory_pair` release (new, Revision 3, DEC-037 §5.5)

- **Preconditions:** scenario 20 complete — the pair remains
  `blocked_manual_review`, attempt `failed_clean`/effective disposition
  `not_applied`-equivalent for `inventory_location_missing` (the safe,
  enumerated release case).
- **Permitted mutations:** 0 (this action is a local Odoo service call;
  it does not itself contact Shopify).
- **Operator approval:** a Reviewer/Administrator explicitly calls
  `action_recheck_inventory_pair(reason="location re-stocked, re-run")`
  after confirming out of band (e.g. via Shopify Admin) that the
  location is stocked again.
- **Odoo action:** the action acquires the pair's row lock; confirms
  exactly one active `blocked_manual_review` inventory job for the pair
  with the required subreason; atomically terminalizes/supersedes that
  job (`cancel_reason='manual_review_release'`, `superseded_by_job_id`
  set) and enqueues exactly one fresh `inventory_push_sync` job — all in
  one transaction.
- **Shopify request:** none from the action itself; the newly-enqueued
  `inventory_push_sync` job performs its own fresh read afterward
  (exercising the same path as scenario 3/10).
- **Expected Odoo result:** the old job is terminal, `superseded_by_job_id`
  pointing at the new orchestration job; `observed_outcome` and
  `resolution_disposition` on the old attempt are **unchanged** by this
  action; actor UID, reason, old job ID, and new job ID are recorded in
  the audit log.
- **Expected Shopify result:** unchanged until the new orchestration
  job's own read.
- **Expected job state:** exactly one new `inventory_push_sync` job
  created; the pair's `operation_scope_key` transfers to it atomically —
  never a window where the pair is unheld.
- **Expected attempt state:** no new `mutation.attempt` row from the
  action itself (it is not a mutation job).
- **Expected logs:** the release action's actor/reason/old-job-ID/
  new-job-ID logged; no credential or PII present (this domain carries
  none).
- **Cleanup:** allow the new orchestration job to run to completion,
  restoring the pair to a known state.
- **Stop conditions:** the action modifies `observed_outcome` or
  `resolution_disposition` → stop immediately, this is forbidden by
  DEC-037 §5.5; the action succeeds for an `uncertain`,
  `duplicate_risk`, `idempotency_contract_violation`, or
  `store_identity_mismatch` job → stop immediately, this action is
  explicitly forbidden for those cases; more than one new job is created,
  or the old job's `operation_scope_key` is not held continuously through
  the handoff → stop, this is an atomicity defect.

---

## 5. No silent caps

Every scenario above either executes fully, is explicitly marked
not-executable with a stated reason (scenario 8's possible outcome), or
is intentionally bounded (scenario 17's pair count, stated before the
run). No scenario's mutation count or coverage may be silently reduced
without recording the reduction and its reason in the eventual validation
results document.

**Error-class vocabulary check (Revision 3, DEC-037 §7/§9):** the
evidence captured for every scenario above must show only `error_class`
values from the fixed set (`shopify_user_errors_validation`,
`inventory_location_missing`, `concurrency_race_conflict`,
`shopify_throttling_rate_limit`, `shopify_temporary_server_network`,
`data_shape_schema_mismatch`, `idempotency_contract_violation`,
`no_reconciliation_strategy`, `store_identity_mismatch`). If any
evidence file records `remote_validation_rejected`,
`remote_precondition_mismatch`, `transport_ambiguous`, or
`clean_rejection` (the withdrawn Revision 2 values), that is a defect to
report, not a value to accept as observed.

---

*References: DEC-036 (Layer 2 substrate, ACCEPTED), DEC-037 (Gate B —
this plan's own decision basis, Revision 3), the Task 013/013B packets,
the inventory operating model, the reconnect/backfill policy, the Wave 3
Definition of Ready §2.6. This plan is now 21 scenarios (20 and 21 added
Revision 3: `blocked_manual_review` non-automatic-child behavior and the
`action_recheck_inventory_pair` release action, DEC-037 §5.5). Execution
produces `docs/05-qa/task-013-inventory-sync-validation-results.md` and
`docs/05-qa/task-013b-validation-results.md` (created at implementation
time, not by this plan).*
