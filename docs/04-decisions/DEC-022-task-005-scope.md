# DEC-022 — Task 005 Scope (Proposal)

## Status

**Proposed, not accepted.** Prepared 2026-07-08. Does not authorize any
code. Does not open the Task 005 gate. Does not resolve MBQ-05, the
in-flight-job disposition, or the `perm_create` ACL posture. Requires
explicit ChatGPT review and acceptance before any part of it becomes
binding, per `CLAUDE.md` §2/§6/§8.

## 1. Decision proposal

**Propose that Task 005 be scoped as "Connection lifecycle actions"** —
`activate`, `disconnect`, `reconnect`, and `reconnect_needed`
auto-transition, plus the `perm_create` store/settings ACL decision — as
already sketched in
[`../07-implementation-plan/credential-connection-foundation-task-plan.md`](../07-implementation-plan/credential-connection-foundation-task-plan.md)
and compared against five other candidate directions in
[`../07-implementation-plan/task-005-gate-proposal.md`](../07-implementation-plan/task-005-gate-proposal.md).

This is a **proposal for ChatGPT to accept, revise, or reject** — it does
not itself decide anything.

## 2. Context

- Task 004 (readiness-check substrate) is merged (PR #115) and its
  acceptance recorded (PR #116, merge commit
  `f4a6ace519bed1073d9b76e0fd91823e03ab7a59`); TD-001 is Resolved.
- VAL-B2 remains deferred, not passed
  (`DEC-021-val-b2-deferral-for-task-004.md`). MBQ-05 remains open, not
  resolved (`../03-architecture/master-blueprint-open-questions.md`).
- PR #117 (branch `claude/token-acquisition-val-b2-5zi8bg`) is open, draft,
  proposing `DEC-023` (token-acquisition strategy + VAL-B2 closure plan) —
  **not yet accepted**. This decision proposal treats PR #117 as an active,
  unresolved parallel track, not as settled input (per the session
  instruction that produced this document: "do not make final
  token-acquisition assumptions... treat PR #117 as an active
  dependency/risk, not an accepted decision").
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
| A. Token acquisition / VAL-B2 closure | Close VAL-B2 with live evidence, or decide a durable OAuth architecture | Not a codeable implementation task; actively under separate review as PR #117/DEC-023; would pre-empt that review and MBQ-05 |
| B. Setup wizard / connection UX | Build the 11-step wizard UI | Already named "Task 006 (horizon only)" in the accepted foundation plan; requires the still-closed UI implementation gate and Task 005 itself as a prerequisite |
| C. Queue/job runner execution layer | Build a dedicated job-execution substrate | No accepted document names this as a discrete future task; the core job/queue substrate already exists from Task 001 |
| D. Store configuration/readiness display | Build a Dashboard-style readiness UI | UI work requiring the closed UI gate; depends on state fields Task 005 has not yet created |
| E. Product sync foundation | Product/variant import and binding | Already named "Task 010"/"Area 1"; explicitly blocked on Task 005 by the existing accepted domain-sequencing document's own dependency analysis |
| F. Connection lifecycle actions (chosen) | activate/disconnect/reconnect/reconnect_needed + `perm_create` | Only candidate with all named prerequisites (Tasks 002–004) already merged; already carries an existing implementation-planning-level acceptance under this name |

## 4. Chosen proposed Task 005 scope

**Connection lifecycle actions**, exactly as scoped in
`credential-connection-foundation-task-plan.md`'s existing Task 005
spec-sketch:

- `activate` (wizard-final semantics at service level — no wizard code
  itself).
- `disconnect` (clear credential value via the existing Task 002 service
  method; preserve all history; cancel-or-hold in-flight jobs per a
  disposition ChatGPT fixes in the eventual task prompt).
- `reconnect` (re-enter credential → call existing Task 003 test-connection
  → call existing Task 004 readiness → resume).
- `reconnect_needed` auto-transition on an authentication-failure signal.
- The `perm_create` store/settings ACL decision surfaced by the accepted
  architecture package.

Explicitly **service-layer/model-layer only** — no UI, no views, no wizard
files.

## 5. Rejected/deferred alternatives

None of Options A–E is a **rejected approach** in the
`../05-qa/rejected-approaches-log.md` sense (`CLAUDE.md` §10) — no candidate
was evaluated on its technical merits and refused. All five are **deferred
by sequencing**, not rejected:

- **Option A** is not deferred by this decision at all — it proceeds on its
  own separate track (PR #117/DEC-023), unaffected by whichever way Task 005
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
  Task 005 merges; two decision points (in-flight-job disposition;
  `perm_create` posture) must be explicitly fixed by ChatGPT before a final
  task prompt can be written — this proposal does not resolve them.
- **Follow-ups:** an explicit Task 005 gate-opening act (separate from this
  proposal); a final `CLAUDE.md` §9 task prompt naming exact allowed/
  forbidden files; no technical debt introduced by this proposal itself
  (docs-only).

## 7. Dependencies

- Tasks 002, 003, 004 merged and reviewed — **satisfied**.
- ChatGPT decision on the in-flight-job disposition (cancel vs. hold) —
  **open**.
- ChatGPT decision on the `perm_create` ACL posture — **open**.
- An explicit Task 005 gate-opening act — **not yet performed**.
- A final Task 005 implementation task prompt — **not yet written**.
- **Not** dependent on PR #117/DEC-023's acceptance, revision, or rejection
  (see `task-005-gate-proposal.md` §16 for the full interaction analysis).

## 8. Explicit non-claims

This decision proposal does **not**:

- authorize any Task 005 code;
- open the Task 005 gate (a separate, explicit ChatGPT act is required,
  per the AR-021 per-task-gate precedent);
- resolve MBQ-05, the in-flight-job disposition, or the `perm_create`
  posture;
- pass VAL-B2 or change its deferred status;
- authorize OAuth, a setup wizard, any UI, or any domain sync;
- take any position on PR #117 or DEC-023's eventual acceptance, revision,
  or rejection;
- reopen or revisit DP-008 (the separate PR #116 merge-process finding in
  `../05-qa/defect-pattern-log.md`) — this document is unrelated to that
  finding and does not touch it.

## 9. What this does not authorize

No code of any kind. No addon file, no Python, no XML, no CSV, no manifest/
security/migration/CI file. No OAuth implementation. No setup wizard. No UI.
No sync code. This is a scope **proposal** only.

## 10. Review status

**Awaiting ChatGPT control-room review.** Per this session's own instructed
boundaries, this PR must not be merged, and must not be marked ready for
review, except by later ChatGPT/control-room instruction.

## Evidence / references

- `../07-implementation-plan/credential-connection-foundation-task-plan.md`
  — existing accepted (AR-024, 2026-07-06) Task 005 spec-sketch.
- `../07-implementation-plan/mvp-domain-implementation-sequence.md` —
  Foundation dependency analysis (Task 005 gates domain sync enqueue).
- `../04-decisions/DEC-021-val-b2-deferral-for-task-004.md` — VAL-B2/MBQ-05
  deferred status, unchanged.
- `../05-qa/architecture-review-log.md` — AR-024 acceptance record.
- PR #117 (`claude/token-acquisition-val-b2-5zi8bg`), open/draft — access:
  Accessible via GitHub API, 2026-07-08.
