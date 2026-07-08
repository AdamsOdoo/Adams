# Task 005 Gate Proposal

> **Proposal only. Does not open the Task 005 gate. Does not authorize
> implementation.** This document proposes the scope and conditions for a
> future, separate Task 005 gate-opening act — mirroring the
> `task-002-gate-opening-proposal.md` → `task-002-credential-storage-gate.md`
> and `task-004-gate-opening-proposal.md` →
> `task-004-readiness-check-substrate-gate.md` precedent. Nothing here
> authorizes code. See the companion
> [`DEC-022-task-005-scope.md`](../04-decisions/DEC-022-task-005-scope.md)
> (Status: Proposed, not accepted) and
> [`task-005-planning-handoff.md`](./task-005-planning-handoff.md).

## 1. Current project state after PR #116

- **Task 004 (readiness-check substrate) is complete and closed.** PR #115
  implemented it; PR #116 recorded acceptance and closed TD-001. Merge
  commit `f4a6ace519bed1073d9b76e0fd91823e03ab7a59` is the current
  `Shopify-connector` HEAD (confirmed by `git fetch` + `git merge-base
  --is-ancestor` at the time of writing).
- **TD-001 is Resolved** (`../05-qa/technical-debt-register.md`) — proven by
  a live regression test on Odoo 19 via Odoo.sh, not merely a routing
  decision.
- **VAL-B2 remains deferred, not passed.** No live, valid Shopify Admin API
  connection has been established in any session to date
  (`../04-decisions/DEC-021-val-b2-deferral-for-task-004.md`).
- **MBQ-05 remains open, not resolved** as a final token-acquisition
  strategy (`../03-architecture/master-blueprint-open-questions.md`).
- **PR #117** ("Token acquisition and VAL-B2 closure proposal," branch
  `claude/token-acquisition-val-b2-5zi8bg`) is open, **draft**, base
  `Shopify-connector` at the same commit `f4a6ace...`, with **zero** merged
  content — it proposes `DEC-023` (Status: Proposed, not accepted) and a
  `val-b2-closure-plan.md`. It is a **parallel, not-yet-accepted** research/
  decision track, not a dependency this proposal treats as decided. See §10.
- **No OAuth, no setup wizard, no UI, no lifecycle action, no
  product/customer/order/inventory/fulfillment/domain sync exists** anywhere
  in the merged codebase as of this commit.
- **Task 005 has not started.** No code, model, view, or file for any
  candidate direction below exists.

## 2. A note on the candidate list

This proposal was scoped to compare five candidate directions: token
acquisition/VAL-B2 closure, setup wizard/connection UX, queue/job runner
execution layer, store configuration/readiness display, and product sync
foundation. Cross-checking the existing accepted planning material
surfaced a **sixth candidate that the given list omitted**:

- **Connection lifecycle actions** (activate / disconnect / reconnect /
  `reconnect_needed`) — already named **"Task 005"** in
  [`credential-connection-foundation-task-plan.md`](./credential-connection-foundation-task-plan.md),
  a package **accepted by ChatGPT at implementation-planning level on
  2026-07-06** (PR #92 acceptance patch; AR-024 — see
  `../05-qa/architecture-review-log.md`).

Per this project's own evidence discipline (`CLAUDE.md` §7–§8; the DP-007
"unclear handoff" lesson in `../05-qa/defect-pattern-log.md`, about not
reconciling new work against existing accepted material), this proposal
cannot honestly compare "candidates for Task 005" while omitting the
direction that already carries that exact name and an existing
implementation-planning-level acceptance. **Connection lifecycle actions is
therefore added as Candidate 6 and compared on equal footing below** — this
proposal does not silently prefer it; §5–§7 show the dependency/risk
reasoning that leads to recommending it.

## 3. Candidate directions compared

### Candidate 1 — Token acquisition / VAL-B2 closure path

- **What it would be:** either (a) executing
  `../05-qa/val-b2-closure-plan.md` to obtain a real, valid Shopify Admin API
  token and close VAL-B2 with live evidence, or (b) implementing a durable
  token-acquisition architecture (OAuth app, setup flow) per whatever DEC-023
  eventually decides.
- **Status:** actively being proposed by **PR #117** (open, draft, not
  accepted) — `DEC-023-token-acquisition-and-val-b2.md`. Not this session's
  work to re-decide (see §10).
- **Fit as "Task 005":** poor. Closure of VAL-B2 (a) is a manual
  evidence-gathering activity outside the Odoo codebase, not a coded
  implementation task with an allowed/forbidden-files shape. A durable OAuth
  architecture (b) is explicitly **not yet decided** — DEC-023 itself
  proposes only a *candidate* future architecture, correctly hedged
  ("Proposed, not accepted... does not authorize OAuth implementation").
  Numbering either of these "Task 005" would pre-empt DEC-023's own review
  and MBQ-05's resolution.
- **Dependencies:** ChatGPT's review/acceptance of DEC-023; for (a), a human
  operator with real Shopify Partner/Dev Dashboard access (no session has
  had this to date, per `val-b2-closure-plan.md` §Status).
- **Risk if forced into Task 005 now:** would require asserting a
  token-acquisition strategy before MBQ-05 is resolved — directly
  contradicts DEC-021 §3's explicit non-decision ("does not resolve OAuth or
  token acquisition") and risks the same "premature architecture" category
  (#4) already at 2 occurrences in `defect-pattern-log.md`.

### Candidate 2 — Setup wizard / connection UX

- **What it would be:** the accepted 11-step wizard UI.
- **Fit as "Task 005":** not possible under the existing accepted sequencing.
  `credential-connection-foundation-task-plan.md` names this **"Task 006
  (horizon only)"**, explicitly gated on (a) Tasks 002–005 **all** merged,
  and (b) **a separate, explicit ChatGPT UI-implementation-gate opening**
  which "AR-023 kept it closed" and which "none exists" as of the cited
  research. Numbering it Task 005 would invert the accepted dependency
  order.
- **Dependencies:** the UI implementation gate (closed); Tasks 002–005 (Task
  005 itself is a prerequisite, not this candidate); MBQ-03 (XML IDs),
  MBQ-05 (token-acquisition decision — this candidate cannot proceed while
  MBQ-05 is open, since the wizard's OAuth step depends on it), MBQ-22
  (wizard copy).
- **Risk if forced into Task 005 now:** would require building UI before the
  UI gate opens (a standing prohibition — AR-023) and before the lifecycle
  actions it is meant to call exist.

### Candidate 3 — Queue/job runner execution layer

- **What it would be:** a dedicated job-execution/queue-runner substrate.
- **Fit as "Task 005":** the core job/queue substrate (the `job`/`job.log`
  models, `job_source`/`trigger_origin` vocabulary, DEC-005's layered-sync
  pattern) **already exists**, accepted and merged under Task 001 — per
  `../07-implementation-plan/mvp-domain-implementation-sequence.md` Area 6:
  "the underlying mechanism ... is core-owned and already exists in accepted
  form." No accepted planning document names a distinct, not-yet-built
  "queue/job runner execution layer" task. Proposing one as Task 005 would
  either (a) duplicate already-merged Task 001 substrate, or (b) require
  first defining what net-new capability it names — neither of which this
  session is scoped or evidenced to do.
- **Dependencies:** none named, because no accepted document defines this as
  a discrete future task.
- **Risk if forced into Task 005 now:** would invent a task with no
  architecture-review or MBQ backing — a "premature architecture" risk
  (category #4, already at 2 occurrences per `defect-pattern-log.md`) with
  no evidence base to review against.

### Candidate 4 — Store configuration/readiness display

- **What it would be:** a Dashboard-style UI surface showing store
  configuration/readiness state to an operator.
- **Fit as "Task 005":** this is UI work. It maps to the accepted
  "Dashboard/sync/error center operational views" (Area 7 in
  `mvp-domain-implementation-sequence.md`) or to the wizard's own
  readiness-summary step (Task 006 horizon) — both require **the UI
  implementation gate**, which is closed, and both are sequenced **after**
  the foundation tasks (002→003→004→005→006) in every accepted document
  read for this proposal. The underlying data it would display
  (`store.last_readiness_result`/`_at`) already exists from Task 004 with no
  UI consuming it yet — consistent with "core-only, zero-UI" being an
  accepted, deliberate precedent (Task 001), not a gap needing urgent
  closure.
- **Dependencies:** the UI implementation gate (closed); Task 005 (lifecycle
  actions) itself, since the Dashboard's "connection health" card content
  depends on lifecycle/state fields this candidate does not itself create.
- **Risk if forced into Task 005 now:** same UI-before-gate risk as
  Candidate 2.

### Candidate 5 — Product sync foundation

- **What it would be:** product/variant import and binding — named **"Task
  010"** and "Area 1" in `mvp-domain-implementation-sequence.md`.
- **Fit as "Task 005":** explicitly blocked by the existing accepted
  document's own dependency analysis. `mvp-domain-implementation-sequence.md`
  §"Foundation dependency (a)" states that **four** foundation tasks —
  **Task 002, Task 003, Task 004, and Task 005** — "must exist (merged,
  gate-opened, reviewed) before **any** domain module ... can safely
  enqueue or execute a real operation," specifically because "**Task 005**
  — store-state gating (`setup_incomplete`/`reconnect_needed`/`disconnected`)
  determines whether business sync/write jobs are enqueueable at all ...
  enforced in the queue substrate itself at enqueue time and again at
  execution time." Product sync structurally **requires** Task 005
  (lifecycle actions) to exist first — it cannot itself be numbered Task
  005 without contradicting that already-accepted dependency chain.
- **Dependencies:** Tasks 002–005 all merged; MBQ-55 (binding-model
  naming/schema pass, stated as blocking "before the product/customer/order
  slice starts"); a not-yet-defined "product domain gate."
- **Risk if forced into Task 005 now:** domain sync jobs could be enqueued
  for a store with no lifecycle/state gating in place — directly
  contradicting the accepted "no business sync/write job is enqueueable for
  a store whose setup is incomplete" rule this same document states is
  enforced partly *by* Task 005.

### Candidate 6 — Connection lifecycle actions

- **What it would be, per the existing accepted spec-sketch**
  (`credential-connection-foundation-task-plan.md`): the audited service
  actions — **activate** (wizard-final semantics at service level),
  **disconnect** (clear credential value, preserve history, cancel-or-hold
  in-flight jobs per a disposition ChatGPT must fix in the task prompt),
  **reconnect** (re-enter → test → readiness → resume), and
  **`reconnect_needed`** auto-transition on auth failure; plus the
  store/settings `perm_create` ACL decision the architecture package
  surfaced.
- **Fit as "Task 005":** exact match to the existing accepted naming.
  Already sequenced immediately after Task 004 in the accepted dependency
  map ("Task 004 readiness substrate → Task 005 lifecycle actions → Task 006
  wizard UI"), and already identified (§"Foundation dependency (a)" above)
  as the **specific mechanism** that gates whether business sync/write jobs
  may be enqueued at all — the same mechanism Candidate 5 (product sync)
  depends on.
- **Dependencies:** Tasks 002–004 merged (**satisfied** — PR #115/#116);
  ChatGPT decisions on (i) the in-flight-job disposition on disconnect
  (cancel vs. hold — not yet decided in any reviewed document) and (ii) the
  `perm_create` ACL posture for store/settings; an explicit gate-opening act
  naming Task 005; a final `CLAUDE.md` §9 task prompt.
- **Risk:** the in-flight-job disposition and `perm_create` posture are
  **open decision points**, not yet resolved by any ChatGPT act found in
  this repository — this proposal does not resolve them (see §8, Open
  questions). Building lifecycle actions without gating enqueue on
  connection state would recreate the very risk Candidate 5's blocked-domain
  analysis describes.

## 4. Dependency analysis

```
Task 004 (readiness substrate) — MERGED, PR #115/#116
        │
        ▼
Task 005 — the only candidate whose prerequisites are already satisfied
        │         (Tasks 002–004 merged; no UI gate needed; no MBQ-05
        │          resolution needed — see below)
        ├──▶ Task 006 (setup wizard UI)          — needs Task 005 + UI gate (closed)
        ├──▶ Store config/readiness display      — needs Task 005 + UI gate (closed)
        └──▶ Task 010 (product sync foundation)  — needs Task 005 + MBQ-55 pass
```

- **Candidates 2 and 4** both require the UI implementation gate, which
  `architecture-review-log.md` (AR-023) records as still closed, and both
  are sequenced in every accepted document **after** Task 005.
- **Candidate 5** is explicitly blocked, by the existing accepted domain
  sequencing document's own words, on Task 005 existing.
- **Candidate 3** has no accepted planning document naming it as a discrete
  future task — the substrate it would build already exists from Task 001.
- **Candidate 1** is a parallel, not-yet-accepted research/decision track
  (PR #117 / DEC-023), not a codeable implementation task, and does not
  itself require or block Task 005 — see §10.
- **Candidate 6** is the only direction with all of its named code-level
  prerequisites (Tasks 002, 003, 004) already merged, and is the specific
  item every other blocked candidate (2, 4, 5) names as its own remaining
  blocker.

## 5. Risk analysis

| Candidate | Primary risk if pursued as Task 005 now |
| --- | --- |
| 1. Token acquisition/VAL-B2 | Pre-empts DEC-023 (still under review) and MBQ-05; not a codeable task shape |
| 2. Setup wizard/UX | Builds UI before the UI gate opens (AR-023) and before its own mechanics (lifecycle) exist |
| 3. Queue/job runner | Invents an unbacked task; risks duplicating already-merged Task 001 substrate |
| 4. Store config/readiness display | Same UI-gate risk as Candidate 2; displays state fields Candidate 6 has not yet created |
| 5. Product sync foundation | Contradicts the accepted rule that Task 005 itself gates whether sync jobs may be enqueued at all |
| 6. Connection lifecycle actions | Two named decision points (in-flight-job disposition; `perm_create` posture) are open — this proposal does not resolve them |

Candidate 6 is the only direction whose risk is a **named, boundable open
question** rather than a **structural dependency violation**.

## 6. Recommended Task 005 scope

**Connection lifecycle actions** (Candidate 6), exactly as scoped in
`credential-connection-foundation-task-plan.md`'s existing Task 005
spec-sketch: `activate`, `disconnect`, `reconnect`, `reconnect_needed`
auto-transition, and the `perm_create` ACL decision — audited service-layer
actions only, no UI.

## 7. Why this should come next

1. It is the only candidate whose prerequisites (Tasks 002, 003, 004) are
   already merged and reviewed.
2. It already carries an existing, implementation-planning-level ChatGPT
   acceptance under this exact name and number (AR-024, 2026-07-06) — this
   proposal does not invent a new direction, it operationalizes one already
   on record.
3. It is the named blocker every other still-blocked candidate (setup
   wizard, readiness display, product sync) cites as its own remaining
   dependency — building it unblocks three other candidates at once rather
   than deepening a queue of blocked work.
4. It does **not** require the UI implementation gate (no views/wizard/menu
   files), so it does not conflict with AR-023's still-closed UI gate.
5. It does **not** require MBQ-05 to be resolved or VAL-B2 to be passed —
   `reconnect`'s "test → readiness" sub-steps call the **existing** Task
   003/004 test-connection and readiness substrate exactly as they already
   behave (including their existing "unknown/not-proven" fail-closed
   reporting when no valid connection evidence exists); this task does not
   change, assume, or depend on what VAL-B2's eventual resolution will be.

## 8. Explicit non-goals

This proposal does **not**:

- authorize any Task 005 code;
- resolve MBQ-05 or the in-flight-job disposition / `perm_create` open
  decision points named in §3/§5 (these remain for ChatGPT to decide in the
  eventual gate-opening act, per `CLAUDE.md` §9);
- mark VAL-B2 passed, or change its deferred status;
- authorize OAuth, a setup wizard, any UI, or any domain sync;
- open the UI implementation gate (AR-023 stays closed);
- decide DEC-023, or take any position on PR #117's proposed token-
  acquisition architecture;
- reject Candidates 1–5 as approaches — they are **sequenced later**, per
  already-accepted dependency ordering, not judged wrong. None is logged in
  `../05-qa/rejected-approaches-log.md`, because none is a rejected
  approach — that log is reserved for approaches decided *not* to use, per
  `CLAUDE.md` §10, and no candidate here has been evaluated and refused on
  its merits; all six remain candidates for their own eventual, later task
  number.

## 9. Allowed files for the future Task 005 implementation task

*(To be fixed exactly by that future task's own `CLAUDE.md` §9 prompt — the
following is this proposal's best-evidenced expectation, not a final list.)*

- `addons/shopify_connector_core/models/shopify_connector_store.py` (state
  transition methods only)
- `addons/shopify_connector_core/models/shopify_connector_store_credential.py`
  (clear-on-disconnect only, reusing the existing Task 002 service methods —
  no schema change)
- `addons/shopify_connector_core/security/*.csv` /
  `*_security.xml` (only for the `perm_create` ACL decision, once ChatGPT
  fixes it)
- `addons/shopify_connector_core/tests/*` (new lifecycle-transition tests)
- The mandatory research-handoff update (`docs/01-research/research-handoff.md`)

## 10. Forbidden files for the future Task 005 implementation task

- Any UI file (views/menus/actions/wizards/XML) of any kind.
- Any OAuth or token-acquisition code.
- Any `shopify_connector_product`/`_sale`/`_inventory`/`_fulfillment` (domain
  module) file.
- Any webhook or controller file.
- Any change to the credential model's stored-value schema (only the
  already-existing clear/redaction path may be called).
- `adams_base`, `main`, plain `dev`.
- Any PR #117 file (`docs/01-research/shopify-token-acquisition-notes.md`,
  `docs/04-decisions/DEC-023-token-acquisition-and-val-b2.md`,
  `docs/05-qa/val-b2-closure-plan.md`) unless that proposal has separately
  merged and this task explicitly cites the merged version.

## 11. Acceptance criteria for future implementation

- Every state transition (`activate`, `disconnect`, `reconnect`,
  `reconnect_needed`) is audited: who/when + a `job.log` trail.
- `disconnect` provably preserves all history (no record deleted) and
  clears the credential value via the existing Task 002 service method.
- `reconnect` provably re-runs test-connection and readiness (Task
  003/004's existing substrate, unmodified) before transitioning to
  `connected` — it must never assert `connected` without doing so.
- `reconnect_needed` auto-transitions on an authentication failure signal,
  and no automatic reconnect exists (a human action is always required to
  leave `reconnect_needed`).
- No business sync/write job is enqueueable for a store whose state is not
  `connected` — enforced at both enqueue time and execution time (defense
  in depth), per the rule `mvp-domain-implementation-sequence.md` already
  states this task is responsible for.
- No new customer-facing "pass"/"connected" claim is asserted from
  inference — every claim must be backed by an actual test/readiness result,
  consistent with DEC-021 §4's fail-closed rule (unchanged, still binding).

## 12. Required tests/validation for future implementation

- Full lifecycle transition matrix (every legal from→to state pair, and
  proof that illegal transitions are rejected).
- History-preservation assertions on `disconnect` (no row deleted/unlinked).
- Credential-clear assertion on `disconnect` (value actually cleared, not
  merely marked).
- Enqueue-block test: a business sync/write job cannot be created/run while
  state ≠ `connected`.
- `reconnect_needed` auto-transition test on a simulated auth-failure
  signal.
- `perm_create` ACL test matrix, once ChatGPT fixes that posture.
- Regression coverage for TD-001's pattern (any new job-creation path this
  task adds must be checked for the same idempotency-key collision class,
  per the standing lesson in `technical-debt-register.md`).

## 13. Rollback notes

Single-PR revert. No data migration — lifecycle actions operate on already-
existing `store`/`store_credential` fields (state, credential value) with no
new schema beyond the `perm_create` ACL row (itself trivially revertible).
Reverting leaves stores in whatever state they were in at revert time; no
downstream task (product sync, wizard) is merged yet to be broken by the
revert, per the current, still-unstarted state of Candidates 2/4/5.

## 14. Definition of done

Per `CLAUDE.md` §9 / `../06-prompts/implementation-task-template.md` §7: code
+ tests pass; `../05-qa/pr-review-checklist.md` Section C satisfied
(idempotency, error handling, retry/recovery, rate-limit awareness,
security/permissions, performance, tests, rollback notes); any shortcut
logged in `technical-debt-register.md`; the mandatory handoff updated
(`CLAUDE.md` §12); ChatGPT review recorded as accepted / accepted with minor
corrections / revise / reject (`quality-feedback-loop.md` §2) **before** any
Task 006/010 work starts.

## 15. Open questions

- **In-flight-job disposition on disconnect** (cancel vs. hold) — not
  resolved by any document reviewed for this proposal; ChatGPT must fix this
  in the eventual gate-opening act or final task prompt.
- **`perm_create` ACL posture** for store/settings — surfaced by the
  accepted architecture package but not yet decided.
- **MBQ-05** (token-acquisition direction) — remains open; Task 005 as
  scoped here does not require its resolution, but the eventual Task 006
  wizard will.
- Whether the "product domain gate" and other named-but-undefined domain
  gates (per `mvp-domain-implementation-sequence.md` §"Dependencies that
  only block UI") get a formal triggering definition before or after Task
  005 — not resolved here.

## 16. Interaction with PR #117

- **If PR #117 / DEC-023 is accepted as currently proposed:** no change to
  this proposal's recommendation. DEC-023's own scope is a token-acquisition
  *strategy* decision (MBQ-05) and a VAL-B2 evidence-closure plan — neither
  changes Task 005's lifecycle-action scope, since `reconnect`'s
  "re-enter → test → readiness" steps call the existing Task 003/004
  substrate regardless of which token-acquisition path is eventually chosen.
  Acceptance would, however, likely accelerate a *future* Task 006 (wizard)
  by resolving MBQ-05 — it does not accelerate or change Task 005 itself.
- **If PR #117 / DEC-023 is revised or rejected:** Task 005 as scoped here
  is **not blocked**. Nothing in §6–§12 assumes a particular
  token-acquisition mechanism; `reconnect`'s test/readiness calls are
  agnostic to how the stored credential was originally obtained. A revision
  or rejection of DEC-023 would only affect the eventual Task 006 wizard's
  OAuth step, not this proposal's recommended scope.
- **Isolation confirmed:** this proposal touches none of PR #117's four
  files (`research-handoff.md`, `shopify-token-acquisition-notes.md`,
  `DEC-023-token-acquisition-and-val-b2.md`, `val-b2-closure-plan.md`) —
  verified by the allowed-files list in §17 of the companion handoff and by
  `git diff --name-only` before commit.
