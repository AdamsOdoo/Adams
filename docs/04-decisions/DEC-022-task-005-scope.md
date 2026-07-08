# DEC-022 — Task 005 Scope

## Status

**Accepted — Task 005 gate opened for final implementation prompt.**
Prepared 2026-07-08 (proposal, via PR #118); **accepted by ChatGPT
2026-07-08** (this revision, gate-opening level). Does not authorize any
code by itself. Does not fully resolve MBQ-05. Does not pass VAL-B2. Does
not fix TD-002. The two decision points this proposal originally left open
— the in-flight-job disposition and the `perm_create` ACL posture — are now
decided; see "Acceptance note" immediately below and
[`task-005-connection-lifecycle-gate.md`](../07-implementation-plan/task-005-connection-lifecycle-gate.md)
for the full binding decision record.

## Acceptance note (2026-07-08)

- **ChatGPT accepted Task 005 scope** as "Connection lifecycle actions" —
  `activate`, `disconnect`, `reconnect`, `reconnect_needed` auto-transition,
  business-job enqueue/execution gating by store connection state, and the
  `perm_create` store/settings ACL posture — exactly as proposed in §4
  below.
- **This opens the gate for a separate final implementation prompt only.**
  The `CLAUDE.md` §9 final Task 005 implementation task prompt, naming
  exact allowed/forbidden files, has not been written and is not issued by
  this acceptance.
- **This document does not itself implement code.** No `addons/` file, no
  Python, no XML, no CSV, no manifest/security/migration/CI file is
  created or modified by this acceptance.
- **Binding decisions are recorded in
  [`task-005-connection-lifecycle-gate.md`](../07-implementation-plan/task-005-connection-lifecycle-gate.md)**
  — that document, not this one, carries the full text of each decision;
  this note is a summary only.
- **The two open decision points named in §7 below are now decided:**
  - **Disconnect cancels non-terminal business jobs**, preserving history —
    no job record is deleted; core maintenance/readiness jobs and
    terminal-state jobs are unaffected.
  - **Store/settings `perm_create` remains closed for Task 005** — no
    `perm_create` grant on `shopify.connector.store` or
    `shopify.connector.store.settings`, except a narrow, explicitly named
    test-only carve-out the future final implementation prompt may specify.
- **VAL-B2 remains deferred / not passed.** This acceptance supplies no
  live Shopify connection evidence and does not change VAL-B2's status
  (`DEC-021-val-b2-deferral-for-task-004.md`).
- **MBQ-05 remains partially routed / open**, not fully resolved
  (`master-blueprint-open-questions.md` MBQ-05 row, as updated by PR #119
  — unmodified by this acceptance).
- **TD-002 remains open**, not fixed (`technical-debt-register.md`,
  unmodified by this acceptance).
- **No OAuth, setup wizard, UI, or sync implementation is authorized** by
  this acceptance, or by the gate document it opens.

## 1. Decision proposal

**Propose that Task 005 be scoped as "Connection lifecycle actions"** —
`activate`, `disconnect`, `reconnect`, and `reconnect_needed`
auto-transition, plus the `perm_create` store/settings ACL decision — as
already sketched in
[`../07-implementation-plan/credential-connection-foundation-task-plan.md`](../07-implementation-plan/credential-connection-foundation-task-plan.md)
and compared against five other candidate directions in
[`../07-implementation-plan/task-005-gate-proposal.md`](../07-implementation-plan/task-005-gate-proposal.md).

This proposal was **accepted by ChatGPT on 2026-07-08** (see "Acceptance
note" above) at gate-opening/scope-decision level. Acceptance of this scope
does not itself decide the two open decision points named in §7 as
"open" — those are decided separately, in
[`task-005-connection-lifecycle-gate.md`](../07-implementation-plan/task-005-connection-lifecycle-gate.md),
and §7/§8 below are updated accordingly.

## 2. Context

- Task 004 (readiness-check substrate) is merged (PR #115) and its
  acceptance recorded (PR #116, merge commit
  `f4a6ace519bed1073d9b76e0fd91823e03ab7a59`); TD-001 is Resolved.
- VAL-B2 remains deferred, not passed
  (`DEC-021-val-b2-deferral-for-task-004.md`). MBQ-05 remains partially
  routed / open, not fully resolved
  (`../03-architecture/master-blueprint-open-questions.md`, as updated by
  PR #119).
- **PR #117 merged the separate DEC-023 token-acquisition / VAL-B2 proposal
  package** (branch `claude/token-acquisition-val-b2-5zi8bg`, carrying
  `DEC-023-token-acquisition-and-val-b2.md` and `val-b2-closure-plan.md`).
  **PR #119 later accepted DEC-023, but only in limited scope, as a
  routing decision** — not as a final token-acquisition-strategy decision.
  DEC-023 is accepted only for: (a) the staged VAL-B2 closure plan as the
  next evidence path to attempt, and (b) one-store / same-Plus-org /
  private-customer / VAL-B2-evidence-gathering use of Custom
  Distribution/manual OAuth. **DEC-023 does not decide the final, scalable
  many-unrelated-customer distribution architecture** — that remains a
  separate, unevaluated, gated research/decision task. **DEC-023 does not
  fully resolve MBQ-05, does not pass VAL-B2, and does not authorize
  OAuth, a setup wizard, a UI, or sync implementation of any kind.** None
  of this changes Task 005's scope: Task 005's lifecycle actions call the
  existing Task 003/004 test-connection/readiness substrate and do not
  implement token acquisition, so Task 005 remains independent of
  whichever final token-acquisition/distribution architecture DEC-023's
  still-open branch eventually resolves to.
- The existing accepted `credential-connection-foundation-task-plan.md`
  (AR-024, accepted by ChatGPT at implementation-planning level, PR #92,
  2026-07-06) already names "Task 005" as "Connection lifecycle actions" and
  sequences it immediately after Task 004, before Task 006 (setup wizard
  UI). This decision proposal is consistent with, not a departure from, that
  existing acceptance.
- `mvp-domain-implementation-sequence.md` independently states that product
  sync (Area 1 / Task 010) cannot safely begin until Task 005 exists,
  because Task 005 provides the store-state gating that determines whether
  business sync/write jobs may be enqueued at all.

## 3. Options considered

Six candidates were compared in full in
[`task-005-gate-proposal.md`](../07-implementation-plan/task-005-gate-proposal.md)
§3–§5:

| Option | Summary | Why not chosen as Task 005 |
| --- | --- | --- |
| A. Token acquisition / VAL-B2 closure | Close VAL-B2 with live evidence, or decide a durable OAuth architecture | Not a codeable implementation task; covered separately by the DEC-023 track (PR #117, merged; DEC-023 later accepted only in limited routing scope via PR #119); would pre-empt DEC-023's still-open scalable-distribution-architecture decision and MBQ-05's full resolution |
| B. Setup wizard / connection UX | Build the 11-step wizard UI | Already named "Task 006 (horizon only)" in the accepted foundation plan; requires the still-closed UI implementation gate and Task 005 itself as a prerequisite |
| C. Queue/job runner execution layer | Build a dedicated job-execution substrate | No accepted document names this as a discrete future task; the core job/queue substrate already exists from Task 001 |
| D. Store configuration/readiness display | Build a Dashboard-style readiness UI | UI work requiring the closed UI gate; depends on state fields Task 005 has not yet created |
| E. Product sync foundation | Product/variant import and binding | Already named "Task 010"/"Area 1"; explicitly blocked on Task 005 by the existing accepted domain-sequencing document's own dependency analysis |
| F. Connection lifecycle actions (chosen) | activate/disconnect/reconnect/reconnect_needed + `perm_create` | Only candidate with all named prerequisites (Tasks 002–004) already merged; already carries an existing implementation-planning-level acceptance under this name |

## 4. Chosen and accepted Task 005 scope

**Connection lifecycle actions**, exactly as scoped in
`credential-connection-foundation-task-plan.md`'s existing Task 005
spec-sketch, and accepted per the "Acceptance note" above:

- `activate` (wizard-final semantics at service level — no wizard code
  itself).
- `disconnect` (clear credential value via the existing Task 002 service
  method; preserve all history; **cancel non-terminal business jobs**, per
  the disposition decided in
  [`task-005-connection-lifecycle-gate.md`](../07-implementation-plan/task-005-connection-lifecycle-gate.md)
  §4.1).
- `reconnect` (re-enter credential → call existing Task 003 test-connection
  → call existing Task 004 readiness → resume).
- `reconnect_needed` auto-transition on an authentication-failure signal.
- The `perm_create` store/settings ACL decision surfaced by the accepted
  architecture package — **decided: remains closed for Task 005**.

Explicitly **service-layer/model-layer only** — no UI, no views, no wizard
files.

## 5. Rejected/deferred alternatives

None of Options A–E is a **rejected approach** in the
`../05-qa/rejected-approaches-log.md` sense (`CLAUDE.md` §10) — no candidate
was evaluated on its technical merits and refused. All five are **deferred
by sequencing**, not rejected:

- **Option A** is not deferred by this decision at all — it proceeded on
  its own separate track (PR #117, merged; DEC-023 accepted only in
  limited routing scope via PR #119), unaffected by whichever way Task 005
  is scoped.
- **Options B and D** become buildable once Task 005 merges and the UI
  implementation gate separately opens (AR-023).
- **Option C** has no accepted task definition to defer — it would need its
  own architecture-review pass before it could even be proposed as a task.
- **Option E** becomes buildable once Task 005 merges and MBQ-55 (binding
  naming/schema) is separately resolved.

No entry is added to `rejected-approaches-log.md` by this decision, per the
reasoning above.

## 6. Consequences

- **Positive:** unblocks the specific mechanism (`connected`/
  `setup_incomplete`/`reconnect_needed`/`disconnected` state gating) that
  three other candidates (B, D, E) each separately depend on; requires no
  UI-gate widening; requires no MBQ-05 resolution; reuses Task 003/004's
  existing test-connection/readiness substrate without modification.
- **Negative / trade-offs:** does not close VAL-B2 or advance the
  token-acquisition decision; leaves the setup wizard, readiness dashboard,
  and product sync all still blocked on their own separate gates even after
  Task 005 merges.
- **Follow-ups:** the two decision points (in-flight-job disposition;
  `perm_create` posture) are now decided (see "Acceptance note" above and
  `task-005-connection-lifecycle-gate.md` §4); a final `CLAUDE.md` §9 task
  prompt naming exact allowed/forbidden files remains to be written; no
  technical debt introduced by this proposal or its acceptance (docs-only).

## 7. Dependencies

- Tasks 002, 003, 004 merged and reviewed — **satisfied**.
- ChatGPT decision on the in-flight-job disposition (cancel vs. hold) —
  **decided (2026-07-08): cancel non-terminal business jobs, preserving
  history** — see
  [`task-005-connection-lifecycle-gate.md`](../07-implementation-plan/task-005-connection-lifecycle-gate.md)
  §4.1.
- ChatGPT decision on the `perm_create` ACL posture — **decided
  (2026-07-08): remains closed for Task 005** — see
  [`task-005-connection-lifecycle-gate.md`](../07-implementation-plan/task-005-connection-lifecycle-gate.md)
  §4.3.
- An explicit Task 005 gate-opening act — **performed by this acceptance,
  in conjunction with
  [`task-005-connection-lifecycle-gate.md`](../07-implementation-plan/task-005-connection-lifecycle-gate.md)**.
- A final Task 005 implementation task prompt — **still not yet written**;
  a separate, later ChatGPT act, per `CLAUDE.md` §9.
- **Not** dependent on DEC-023's limited-scope routing acceptance (PR #119)
  or on its still-open scalable-distribution-architecture branch (see
  `task-005-gate-proposal.md` §16 for the full interaction analysis) —
  Task 005's lifecycle actions call the existing Task 003/004 substrate
  and do not implement token acquisition.

## 8. Explicit non-claims

This decision, even as accepted, does **not**:

- authorize any Task 005 code — code authorization requires the separate
  final implementation task prompt named in §7;
- fully resolve MBQ-05;
- pass VAL-B2 or change its deferred status;
- fix TD-002;
- authorize OAuth, a setup wizard, any UI, or any domain sync;
- take any position on PR #117/PR #119's DEC-023 acceptance beyond
  reading its current (limited-scope, routing-only) status.

## 9. What this does not authorize

No code of any kind. No addon file, no Python, no XML, no CSV, no manifest/
security/migration/CI file. No OAuth implementation. No setup wizard. No UI.
No sync code. This acceptance opens the Task 005 gate at
documentation/governance/scope-decision level only — a separate final
`CLAUDE.md` §9 implementation task prompt is required before any code may
be written.

## 10. Review status

**Accepted by ChatGPT, 2026-07-08, at gate-opening level.** This revision's
own PR must still be reviewed and merged into `Shopify-connector` before
the gate is operative, per the AR-021/AR-026/AR-028 per-task-gate
precedent (mirroring `task-004-readiness-check-substrate-gate.md`'s
Status section) — this PR must not be marked ready for review or merged
except by later ChatGPT/control-room instruction.

## Evidence / references

- `../07-implementation-plan/credential-connection-foundation-task-plan.md`
  — existing accepted (AR-024, 2026-07-06) Task 005 spec-sketch.
- `../07-implementation-plan/mvp-domain-implementation-sequence.md` —
  Foundation dependency analysis (Task 005 gates domain sync enqueue).
- `../04-decisions/DEC-021-val-b2-deferral-for-task-004.md` — VAL-B2/MBQ-05
  deferred status, unchanged.
- `../05-qa/architecture-review-log.md` — AR-024 acceptance record.
- PR #117 (merged), the separate token-acquisition/VAL-B2 proposal package
  (`claude/token-acquisition-val-b2-5zi8bg`, `DEC-023-token-acquisition-and-val-b2.md`)
  — access: Accessible via GitHub API, observed 2026-07-08.
- PR #119 (merged), merge commit
  `eb5d8d91b46c4b3e21c1387eee03bc9688b773e6` — ChatGPT's limited-scope
  routing acceptance of DEC-023 and the corresponding MBQ-05 register-row
  update — access: Accessible via GitHub API, observed 2026-07-08.
