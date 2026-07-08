# Task 005 Connection Lifecycle — Gate Document (Gate Opened)

> **This document opens the Task 005 gate at documentation/governance
> level.** It mirrors the AR-021/AR-026/AR-028 precedent
> (`task-002-credential-storage-gate.md`,
> `task-003-api-client-test-connection-gate.md`,
> `task-004-readiness-check-substrate-gate.md`): the gate formally opens,
> and Task 005 implementation *planning* is authorized, once this document,
> carrying ChatGPT's decisions below, is merged into `Shopify-connector` —
> not before, and not by this session's own act of writing it. This
> document does **not** itself authorize any code, and it does **not**
> itself constitute the final `CLAUDE.md` §9 implementation task prompt.

## Status

**Gate opened for final implementation prompt; no code authorized by this
document alone.** Prepared 2026-07-08, on branch
`claude/task-005-gate-opening-jr5a9i`, branched from the current
`Shopify-connector` HEAD (see §Preconditions). This document records
ChatGPT's control-room decisions on the two open decision points named in
`DEC-022-task-005-scope.md` §7 (in-flight-job disposition; `perm_create`
posture) plus five further binding semantics decisions (activate,
disconnect, reconnect, `reconnect_needed`, and business-job
enqueue/execution gating). It does not write, and does not authorize, any
Odoo module, model, view, controller, security, migration, test, or CI
file. **The separate, final Task 005 implementation task prompt — naming
exact allowed/forbidden files per `CLAUDE.md` §9 and the
`implementation-task-template.md` — has not been written and is not
authorized by this document.** That prompt is the next, distinct act
ChatGPT takes after this gate document is reviewed and merged.

## Preconditions

Confirmed on-disk before this document was written:

- **PR #118 merged into `Shopify-connector`** — merge commit
  `440b9beec108bf1cf7617688f1e32ba60b6a661f` ("Task 005 gate proposal"),
  carrying `task-005-gate-proposal.md`, `DEC-022-task-005-scope.md`
  (Proposed, not accepted at that point), and
  `task-005-planning-handoff.md`.
- **PR #119 merged into `Shopify-connector`** — merge commit
  `eb5d8d91b46c4b3e21c1387eee03bc9688b773e6` ("DEC-023 limited acceptance
  and MBQ-05 routing"), carrying DEC-023's limited-scope acceptance and the
  MBQ-05 register-row routing note.
- Both merge commits confirmed as ancestors of the current
  `origin/Shopify-connector` HEAD via `git fetch origin Shopify-connector`
  and `git merge-base --is-ancestor <sha> origin/Shopify-connector` before
  this document was written.
- **Task 005 is not started.** No `activate`/`disconnect`/`reconnect`/
  `reconnect_needed` code, no business-job enqueue/execution gating code,
  and no `perm_create` ACL change exists anywhere in the merged codebase as
  of this commit.

## 1. Current state after PR #118 and PR #119

- **PR #118** merged the Task 005 gate *proposal* package: it compared six
  candidate directions for Task 005 and recommended "Connection lifecycle
  actions" (`activate`/`disconnect`/`reconnect`/`reconnect_needed` +
  `perm_create`), consistent with the existing AR-024/PR #92
  implementation-planning-level naming of "Task 005" in
  `credential-connection-foundation-task-plan.md`. It left **DEC-022 at
  "Proposed, not accepted"** and named two explicit open decision points:
  the in-flight-job disposition on disconnect, and the `perm_create` ACL
  posture. It did not open the Task 005 gate.
- **PR #119** merged a **separate, parallel track**: DEC-023 (token
  acquisition / VAL-B2) was accepted **only in limited, routing-decision
  scope** — the staged VAL-B2 closure plan as the next evidence path, and
  Custom Distribution / manual OAuth restricted to one-store /
  same-Plus-org / private-customer / VAL-B2-evidence-gathering use only.
  MBQ-05's register row was updated to **"Partially routed / Open"** — not
  Resolved. The `read_fulfillments` least-privilege scope-naming concern
  was logged as **TD-002 (Open, Medium)**. PR #119 did not touch Task 005's
  scope, DEC-022, or any lifecycle-action decision point.
- **TD-001 is Resolved** (fixed inside Task 004 per PR #115, verified live
  on Odoo.sh — `technical-debt-register.md`).
- **TD-002 is Open** (`read_fulfillments` scope-naming concern, routed to a
  future fulfillment-domain task spec — unaffected by this document).
- **VAL-B2 remains deferred, not passed** — no live, valid Shopify Admin
  API connection has been established in any session to date
  (`DEC-021-val-b2-deferral-for-task-004.md`;
  `task-003-validation-results.md`).
- **MBQ-05 remains partially routed / open**, not resolved as a final
  token-acquisition strategy (`master-blueprint-open-questions.md` MBQ-05
  row, as updated by PR #119).
- **No OAuth, no setup wizard, no UI, no sync, and no domain
  implementation exists** anywhere in the merged codebase as of this
  commit.
- **Task 005 is not implemented.** This document, like PR #118 before it,
  authorizes no code.

This document is the **explicit Task 005 gate-opening act** that
`DEC-022-task-005-scope.md` §7 and `task-005-gate-proposal.md` §15 both
named as a required, not-yet-performed follow-up.

## 2. Accepted Task 005 scope

**Connection lifecycle actions in `shopify_connector_core`**, exactly as
proposed in `DEC-022-task-005-scope.md` §4 and `task-005-gate-proposal.md`
§6, now accepted by ChatGPT:

- `activate`
- `disconnect`
- `reconnect`
- `reconnect_needed` auto-transition
- Business-job enqueue/execution gating by store connection state
- Service/model layer only
- No UI
- No OAuth
- No setup wizard
- No sync/domain implementation

This scope is unchanged from the PR #118 proposal. What this document adds
is (a) ChatGPT's acceptance of that scope, and (b) resolution of the two
decision points the proposal left open, plus five further binding
semantics decisions — all recorded in §4 below.

## 3. Explicit non-goals

This gate document, and any future Task 005 implementation authorized
under it, does **not**:

- implement OAuth of any kind (no client credential handling, no
  authorization-code-grant flow, no token exchange);
- implement a setup wizard of any kind;
- implement any UI (no views, menus, actions, wizards, or XML beyond the
  minimum `perm_create`-adjacent security CSV rows named in §5, if any);
- implement any product/customer/order/inventory/fulfillment domain sync;
- pass VAL-B2 or change its deferred/not-passed status;
- fully resolve MBQ-05 (the token-acquisition direction remains partially
  routed / open; Task 005 does not require its resolution — `reconnect`
  calls the existing Task 003/004 substrate exactly as-is regardless of
  which acquisition mechanism MBQ-05 eventually resolves to);
- fix TD-002 (the `read_fulfillments` scope-naming concern remains routed
  to a future fulfillment-domain task spec, unaffected by this gate).

## 4. Binding implementation decisions

The following seven decisions are **binding** on the eventual Task 005
final implementation task prompt. They may not be silently altered,
narrowed, or widened by that future prompt without a new, explicit ChatGPT
decision.

### 4.1 In-flight job disposition on disconnect

**Decision: cancel pending/non-terminal business jobs on disconnect.**

- When a store is disconnected, future business/sync work must not
  continue automatically.
- Non-terminal business jobs must be moved to `cancelled`, with a clear
  cancel reason and a `job.log` entry recording the transition.
- **No job record may be deleted.** Cancellation is a state transition, not
  a removal — consistent with the already-accepted MBQ-08 posture that
  disconnect "preserves the store record, bindings, jobs, logs, audit
  records, and mapping/error history."
- Core maintenance/test/readiness jobs (e.g. `core_test_connection`,
  `core_readiness_check`) must **not** be cancelled merely because the
  store is disconnected — they are allowed to run even for a disconnected
  store (see §4.2's core-vs-business distinction).
- Historical `succeeded`/`failed`/`cancelled`/`skipped` jobs must remain
  unchanged — disconnect's cancellation sweep only affects jobs that are
  still in a non-terminal state (e.g. `pending`/`queued`/`running`,
  whatever the exact accepted job-state vocabulary names as non-terminal)
  at the moment `disconnect` executes.
- **Business jobs**, for this decision, are jobs associated with business
  sync sources: `webhook`, `manual_sync`, `scheduled_sync`,
  `reconciliation`, or `odoo_event` (the existing `job_source`/
  `trigger_origin` vocabulary from Task 001/DEC-005).
- **Core setup/readiness/maintenance jobs** are allowed to run even if the
  store is not connected — they exist precisely to determine/report
  connection and readiness state, and gating them on `connected` would be
  circular.

### 4.2 Business job enqueue/execution gating

**Decision: do not rely on cancellation alone for safety.**

- Task 005 must add store-state gating at **both**:
  - enqueue/create time, and
  - execution/start time.
- A business job must not be created, or moved to `running`, unless the
  store state is `connected`.
- If a store changes state after a job was created (race between enqueue
  and execution), execution must **fail closed** before any Shopify
  operation — the job must not proceed to a live Shopify call just because
  it was created while the store was still connected.
- No Shopify API write, domain sync, or business operation may proceed for
  a store in `setup_incomplete`, `reconnect_needed`, or `disconnected`.
- This is the specific mechanism `mvp-domain-implementation-sequence.md`
  already names Task 005 as responsible for providing, and that Task 010
  (product sync) and every other domain task depend on before they may
  enqueue or execute a real operation.

### 4.3 `perm_create` ACL posture

**Decision: keep store/settings generic create closed for Task 005.**

- Do **not** grant `perm_create` on `shopify.connector.store`.
- Do **not** grant `perm_create` on `shopify.connector.store.settings`.
- Do **not** change existing ACL rows in Task 005, unless the final
  implementation prompt explicitly allows a narrow, named, test-only
  assertion (e.g. a test fixture that creates a store record directly
  because no controlled creation service exists yet) — any such carve-out
  must be named explicitly in that future prompt, not assumed here.
- Store/settings creation belongs to a future setup wizard or a controlled
  creation service, neither of which is in scope for Task 005.
- **Consequence: Task 005 operates on already-existing stores only.** No
  lifecycle action creates a `shopify.connector.store` or
  `shopify.connector.store.settings` record; all four actions
  (`activate`/`disconnect`/`reconnect`/`reconnect_needed`) act on a store
  record that already exists before the action runs.

### 4.4 Activate semantics

- `activate` is service/model-layer only — no wizard, no button, no view.
- It must **never infer** connection success.
- It may transition a store to `connected` only when existing Task 003
  test-connection evidence (`core_test_connection`'s recorded result) and
  Task 004 readiness evidence (`core_readiness_check`'s essential-tier
  pass) both actually support it — never from assumption, never from the
  mere presence of a stored credential value.
- It must **not** claim VAL-B2 has passed. If no live, valid test-connection
  result exists, `activate` must report the existing Task 003/004
  "unknown/not-proven" fail-closed state, exactly as those substrates
  already behave — it introduces no new inference layer on top of them.
- It must **not** require MBQ-05 resolution — it consumes whatever
  credential value Task 002's existing storage already holds, regardless
  of how that value was acquired.
- It must **not** implement OAuth.

### 4.5 Disconnect semantics

- `disconnect` clears the stored credential value using the **existing**
  Task 002 credential-clear service method — no new credential-mutation
  code path.
- It preserves the credential row and its history (create/write stamps,
  `credential_last_replaced_at`, prior state) — clearing the secret value
  is not the same as deleting the row.
- It transitions the store to `disconnected`.
- It cancels non-terminal business jobs, per §4.1.
- It is **idempotent** — calling `disconnect` on an already-`disconnected`
  store is a safe no-op (or an audited no-op with its own `job.log` entry),
  never an error that leaves the store in an inconsistent state.

### 4.6 Reconnect semantics

- `reconnect` is service/model-layer only.
- Token re-entry/replacement is handled through the **already-existing**
  credential service (the same Task 002 write path `activate`/initial
  setup already uses) — no new credential-input mechanism.
- `reconnect` must call the **existing** Task 003 test-connection and Task
  004 readiness-check substrate — it does not reimplement, wrap with new
  inference, or bypass either.
- It transitions to `connected` **only if** the required evidence passes
  under the accepted essential-tier criteria (DEC-018/MBQ-06, as already
  implemented by Task 004).
- Otherwise it remains in, or transitions to, `reconnect_needed` (or
  another fail-closed state, as the final implementation prompt's exact
  state machine specifies) — it never asserts `connected` on partial or
  absent evidence.
- It must **not** implement OAuth or setup-wizard logic of any kind.

### 4.7 `reconnect_needed` auto-transition

- Authentication/permission/scope-invalidation signals surfaced by the
  Shopify client or the test-connection paths (e.g. a 401/403-class
  response, an invalidated-scope signal) must move the store to
  `reconnect_needed`.
- Credential state may be marked invalid where the existing code already
  supports such a state value — no new credential-state vocabulary is
  introduced by this decision beyond what Task 002 already defined.
- **No automatic reconnect is allowed.** The system must never attempt to
  silently re-acquire or re-validate a credential and transition back to
  `connected` on its own.
- **Human/admin action is required** to leave `reconnect_needed` — only an
  explicit `reconnect` (or `disconnect`) action, taken by an operator, may
  change the state away from `reconnect_needed`.

## 5. Future implementation allowed files (proposal, not final)

*(To be fixed exactly by the future Task 005 final implementation task
prompt, per `CLAUDE.md` §9 — the following is this gate document's
best-evidenced expectation, carried forward unchanged from
`task-005-gate-proposal.md` §9, not itself a final list.)*

- `addons/shopify_connector_core/models/shopify_connector_store.py` (state
  transition methods — `activate`/`disconnect`/`reconnect`/
  `reconnect_needed` — and business-job enqueue/execution gating checks
  only)
- `addons/shopify_connector_core/models/shopify_connector_store_credential.py`
  (clear-on-disconnect only, reusing the existing Task 002 service
  method — no schema change)
- `addons/shopify_connector_core/models/shopify_connector_job.py` (the
  enqueue-time and execution-time store-state gating checks named in
  §4.2, and the disconnect-time cancellation sweep named in §4.1, only)
- `addons/shopify_connector_core/security/*.csv` /
  `*_security.xml` (only if the final prompt names a narrow, explicit
  `perm_create` test-only carve-out per §4.3 — otherwise no security file
  changes at all)
- `addons/shopify_connector_core/tests/*` (new lifecycle-transition and
  enqueue/execution-gating tests)
- The mandatory research-handoff update
  (`docs/01-research/research-handoff.md`)

## 6. Future implementation forbidden files

- Any UI file (views/menus/actions/wizards/XML) of any kind.
- Any OAuth or token-acquisition code.
- Any `shopify_connector_product`/`_sale`/`_inventory`/`_fulfillment`
  (domain module) file.
- Any webhook or controller file.
- Any change to the credential model's stored-value schema (only the
  already-existing clear/redaction path may be called).
- Any grant of `perm_create` on `shopify.connector.store` or
  `shopify.connector.store.settings`, except the narrow test-only
  carve-out §4.3 permits the final prompt to name explicitly.
- `adams_base`, `main`, plain `dev`.
- Any file belonging to the separate PR #117/PR #119 token-acquisition
  track (`docs/01-research/shopify-token-acquisition-notes.md`,
  `docs/04-decisions/DEC-023-token-acquisition-and-val-b2.md`,
  `docs/05-qa/val-b2-closure-plan.md`) — Task 005 does not depend on, and
  must not modify, that track's decisions.
- Any manifest/security/migration/CI file beyond the narrow carve-out named
  in §5, unless the final implementation prompt explicitly names one.

## 7. Acceptance criteria for future implementation

- Every state transition (`activate`, `disconnect`, `reconnect`,
  `reconnect_needed`) is audited: who/when + a `job.log` trail.
- `disconnect` provably preserves all history (no record deleted) and
  clears the credential value via the existing Task 002 service method.
- `disconnect` provably cancels every non-terminal business job for that
  store, with a cancel reason and `job.log` entry, while leaving core
  maintenance/readiness jobs and all terminal-state jobs untouched.
- `reconnect` provably re-runs the existing Task 003 test-connection and
  Task 004 readiness-check substrate, unmodified, before transitioning to
  `connected` — it must never assert `connected` without doing so.
- `reconnect_needed` auto-transitions on an authentication/permission/
  scope-invalidation failure signal, and no automatic reconnect exists — a
  human/admin action is always required to leave `reconnect_needed`.
- No business sync/write job is enqueueable, and no business sync/write job
  is executable, for a store whose state is not `connected` — enforced at
  **both** enqueue time and execution time (defense in depth), per §4.2.
- No `perm_create` grant exists on `shopify.connector.store` or
  `shopify.connector.store.settings`, except a carve-out the final
  implementation prompt explicitly names per §4.3.
- No new customer-facing "pass"/"connected" claim is asserted from
  inference — every claim is backed by an actual Task 003/004 test/
  readiness result, consistent with DEC-021 §4's fail-closed rule
  (unchanged, still binding).
- `activate` does not claim VAL-B2 has passed and does not require MBQ-05
  resolution, per §4.4.
- Only the files named in the eventual, separately-accepted final
  implementation prompt's allowed-files list were changed — confirmed by
  `git diff` review, not by assumption.

## 8. Required tests for future implementation

- Full lifecycle transition matrix (every legal from→to state pair among
  `setup_incomplete`/`connected`/`reconnect_needed`/`disconnected`, and
  proof that illegal transitions are rejected).
- History-preservation assertion on `disconnect` (no row deleted/unlinked;
  credential row and its audit metadata survive).
- Credential-clear assertion on `disconnect` (the secret value is actually
  cleared, not merely marked).
- Disconnect job-cancellation test: non-terminal business jobs (webhook/
  manual_sync/scheduled_sync/reconciliation/odoo_event sources) are moved
  to `cancelled` with a reason and `job.log` entry; core
  maintenance/readiness jobs are unaffected; terminal-state jobs
  (succeeded/failed/cancelled/skipped) are unchanged.
- Enqueue-block test: a business job cannot be **created** while store
  state ≠ `connected`.
- Execution-block test: a business job cannot be **moved to running** (and
  performs no Shopify call) while store state ≠ `connected` at execution
  time, even if it was created while the store was still connected
  (race/fail-closed case).
- `activate` evidence test: `activate` transitions to `connected` only when
  both a passing Task 003 test-connection result and a passing Task 004
  essential-tier readiness result exist; it reports the existing
  unknown/not-proven state otherwise.
- `reconnect` re-run test: `reconnect` provably invokes the existing Task
  003/004 substrate (not a bypass/shortcut) before any `connected`
  transition.
- `reconnect_needed` auto-transition test on a simulated auth/permission/
  scope-invalidation failure signal, plus a negative test proving no
  automatic reconnect occurs.
- `perm_create` ACL test: `shopify.connector.store` and
  `shopify.connector.store.settings` remain non-creatable by any
  non-carve-out role.
- `disconnect` idempotency test: calling `disconnect` twice in a row does
  not error and does not leave the store or its jobs in an inconsistent
  state.
- Regression coverage for TD-001's pattern (any new job-creation path this
  task adds must be checked for the same idempotency-key collision class,
  per the standing lesson in `technical-debt-register.md`).

## 9. Rollback notes

- Single-PR revert. No data migration is required — lifecycle actions
  operate on already-existing `store`/`store_credential`/`job` fields
  (state, credential value, job status) with no new schema beyond the
  narrow §4.3 test-only ACL carve-out (if the final prompt names one),
  itself trivially revertible.
- Reverting leaves stores and jobs in whatever state they were in at
  revert time. Jobs already cancelled by a `disconnect` call before revert
  remain `cancelled` — reverting the code does not retroactively
  un-cancel jobs, and no rollback step may attempt to do so, since that
  would itself be a mutation outside this task's scope.
- No downstream task (Task 006 wizard, Task 010 product sync) is merged
  yet to be broken by the revert, per the current, still-unstarted state
  of every task after Task 005.

## 10. Definition of done

Per `CLAUDE.md` §9 / `implementation-task-template.md` §7, for the future
Task 005 implementation PR:

- Code + tests written; tests pass, or are honestly recorded as
  `py_compile`/`pyflakes`-validated only (per the Task 001A precedent) with
  a manual validation checklist prepared as mandatory review evidence, if
  no live Odoo runtime/CI is available at the time.
- Lint/format clean.
- `pr-review-checklist.md` Section C satisfied (idempotency, error
  handling, retry/recovery, rate-limit awareness, security/permissions,
  performance, tests, rollback notes).
- Only the files named in the eventual final implementation prompt's
  allowed-files list were changed — confirmed, not assumed.
- Any shortcut logged honestly in `technical-debt-register.md` — not
  hidden or minimized.
- The mandatory research-handoff update (`CLAUDE.md` §12) is written,
  including the Learning feedback loop section.
- ChatGPT reviews and explicitly classifies the implementation PR
  (accepted / accepted with minor corrections / revise / reject) before
  any next task (Task 006 or Task 010) starts.
- The change is modular and isolated, consistent with `CLAUDE.md` §9 —
  `shopify_connector_core` only, no domain-module coupling.

## 11. Open risks

- **VAL-B2 remains deferred/not passed.** `activate`/`reconnect` must keep
  reporting the honest unknown/not-proven state until live evidence
  exists; any future session that treats a lifecycle-action `connected`
  transition as proof of VAL-B2 would violate §4.4/§4.6 and DEC-021 §4.
- **MBQ-05 remains partially routed / open.** The eventual Task 006 setup
  wizard, not Task 005, is the point where MBQ-05's resolution actually
  matters — Task 005 must not be misread as depending on it.
- **TD-002 remains open.** Unrelated to Task 005's scope, but any future
  session must not conflate readiness-check scope-naming cleanup with
  Task 005 lifecycle work.
- **Exact job-state vocabulary for "non-terminal"** is assumed (`pending`/
  `queued`/`running` as non-terminal; `succeeded`/`failed`/`cancelled`/
  `skipped` as terminal) based on the existing Task 001/004 job model —
  the final implementation prompt must confirm the exact accepted state
  list before coding, not assume this gate document's paraphrase is
  itself the schema.
- **`perm_create` carve-out ambiguity.** §4.3 permits a narrow, explicitly
  named test-only carve-out; if the final implementation prompt does not
  name one, no carve-out exists and `perm_create` stays fully closed on
  both models — this gate document does not itself grant one.
- **Race between enqueue and execution.** §4.2's fail-closed execution-time
  check is the safety net for the case where a store's state changes
  between a business job's creation and its start; the final
  implementation prompt must specify the exact re-check mechanism (e.g. a
  guard at the start of the job's `run`/`_execute` method) precisely,
  since an incomplete guard would silently reintroduce the risk this
  decision exists to close.

## 12. Exact next step

**ChatGPT reviews this gate document.** If accepted, the next act is a
**separate**, explicit `CLAUDE.md` §9 final Task 005 implementation task
prompt — naming exact allowed/forbidden files, mirroring
`task-004-final-implementation-prompt.md` — issued by ChatGPT in chat
after this document is merged into `Shopify-connector`. That prompt is the
action that starts the future Task 005 coding session; merging this
document does not itself start that session, and this document does not
itself authorize any code.

## Closure rule

- **This gate, once accepted and merged, closes after the future Task 005
  implementation PR is opened as draft.** Opening that PR consumes the
  gate; it does not remain open for repeated or follow-on use.
- **No follow-on coding is authorized by this gate.** Once a Task 005 PR
  exists, any further change beyond fixing review feedback on that same PR
  requires its own separate ChatGPT decision and, if it touches new
  forbidden territory, its own separate gate act.
- **Every future domain/UI task** (setup wizard, product/customer/order/
  inventory/fulfillment sync, dashboards) requires its own separate
  decision-closure package and gate-opening act, mirroring this Task 002 →
  Task 003 → Task 004 → Task 005 pattern; none of it is authorized,
  implied, or shortcut by this document.

## Evidence / references

- [`DEC-022-task-005-scope.md`](../04-decisions/DEC-022-task-005-scope.md)
  — the companion decision record, updated by this same session to
  "Accepted — Task 005 gate opened for final implementation prompt."
- [`task-005-gate-proposal.md`](./task-005-gate-proposal.md) — the PR #118
  candidate-comparison proposal this gate document accepts and builds on
  (unmodified by this session).
- [`task-005-planning-handoff.md`](./task-005-planning-handoff.md) — the
  PR #118 session handoff (unmodified by this session).
- [`credential-connection-foundation-task-plan.md`](./credential-connection-foundation-task-plan.md)
  — AR-024 (2026-07-06), the existing implementation-planning-level Task
  005 spec-sketch this gate document operationalizes.
- [`DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md)
  — the separate, parallel PR #119 token-acquisition/VAL-B2 track
  (unmodified by this session; consulted read-only for current VAL-B2/
  MBQ-05 status).
- [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  — MBQ-05 ("Partially routed / Open") and MBQ-08 (disconnect
  data-retention posture, consistent with §4.1) rows (unmodified by this
  session; consulted read-only).
- [`technical-debt-register.md`](../05-qa/technical-debt-register.md) —
  TD-001 (Resolved) and TD-002 (Open) rows (unmodified by this session;
  consulted read-only).
- [`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md)
  — the immediately preceding gate document, whose structure and AR-021
  precedent this document mirrors.
