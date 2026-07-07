# Task 004 Readiness Check Substrate — Gate Document (Accepted)

> **ChatGPT has accepted this gate document, pending this PR's own
> review/merge into `Shopify-connector`.** It mirrors the
> AR-021/AR-026/AR-028 precedent
> (`limited-core-implementation-gate.md`, `task-002-credential-storage-gate.md`,
> `task-003-api-client-test-connection-gate.md`): the gate formally opens
> once this document, carrying that acceptance, is merged into
> `Shopify-connector` — not before. This document was originally prepared
> as a **proposal** (part of the Task 004 gate-opening package); this
> revision records ChatGPT's control-room decision to **accept** it, and
> to select TD-001's disposition (see §TD-001 route below).

## Status

- **ACCEPTED by ChatGPT — pending PR review/merge.** This acceptance
  patch, prepared 2026-07-07 on branch
  `claude/task-004-gate-acceptance-338b3a`, records ChatGPT's
  control-room decision to accept this gate document. **The gate formally
  opens, and Task 004 implementation planning is authorized, only once
  this PR is merged into `Shopify-connector`** — not on draft, not on
  review approval alone in chat, and not by this session's own act of
  writing it.
- **Docs-only.** No code, no model, no field, no view, no XML, no Python is
  created by this document or this PR.
- **This acceptance opens Task 004 implementation *planning* only** — it
  does not itself write any code. **Task 004 implementation must be run
  in a separate, later coding session**, using the finalized
  [`task-004-final-implementation-prompt.md`](./task-004-final-implementation-prompt.md),
  issued by ChatGPT in chat after this PR is merged.
- **Does not implement Task 004.** No implementation code exists as of
  this PR, and none is written by it.
- **Does not create code.**
- **Does not call Shopify.** No external network call is made by this
  document or this PR.
- **Does not issue the final implementation prompt** — issuing
  [`task-004-final-implementation-prompt.md`](./task-004-final-implementation-prompt.md)
  is the action that starts the future Task 004 coding session, and that
  action must happen in a separate turn/session, after this PR merges,
  and only when ChatGPT explicitly issues that prompt in chat — not
  inside this PR.
- **Authorizes at most one future coding session** scoped exactly to the
  readiness-check substrate named below (including the TD-001 fix named
  in §TD-001 route) — not a standing implementation mandate.

## Preconditions

Confirmed on-disk before this document was written:

- **PR #111 merged into `Shopify-connector`** — merge commit
  `43f3b2a923a420e523cd2ec2662a46e2a9abed26` (Task 004 readiness preflight
  package, docs-only).
- **DEC-021 prepared this session** —
  [`../04-decisions/DEC-021-val-b2-deferral-for-task-004.md`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md),
  recording ChatGPT's control-room decision to defer VAL-B2 from the Task
  003 → Task 004 gate. **This gate document's own acceptance is
  conditional on DEC-021 being merged** — see §Gate conditions below.
- **Task 004 is not started.** No readiness-check registry/service model,
  no `shopify.connector.readiness.*` model, and no change to
  `shopify_connector_job.py`/`shopify_connector_job_log.py` beyond what
  Task 003 already merged exists in the repository as of this branch.
- **Task 003 is merged** (PR #101, merge commit
  `e27f10e55f3504d1a9b8871a207b3d9762a3c783`) but its manual validation is
  **conditionally accepted for Task 004 gate-opening review only** — see
  [`../05-qa/task-003-validation-results.md`](../05-qa/task-003-validation-results.md)
  §5.
- **TD-001 is open**, tracked in
  [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md).
  **Its route is now decided by this acceptance: fixed inside Task 004**,
  as the first mandatory implementation acceptance criterion (see
  §TD-001 route below). TD-001 remains `Open` — not fixed, not closed —
  until the future Task 004 implementation PR actually merges the fix and
  it is validated.

## Gate constraints (exact)

If accepted, this gate would authorize **exactly**: Task 004 — Readiness
Check Substrate, scoped to:

- a read-only readiness-check registry/service model (or model set) in
  `shopify_connector_core` — core-owned checks plus a domain-extension
  registration seam;
- essential/warning tier semantics exactly per the accepted DEC-018/MBQ-06
  split (credential validity/test-connection result, required scopes
  present, API-version health, store identity, `web.base.url`
  reachability, webhook HMAC secret presence if webhooks are enabled,
  cron/queue health, at least one mapped Location with an enabled domain,
  and intentional domain-flag enablement, as essential; all other
  candidate checks warn only);
- fail-closed aggregation: an unknown/uncomputed check state is never
  "passed"; a single failed essential check always yields overall fail;
- per-check JSON result persistence to `job.log.payload_snapshot`, using
  the existing `_system_append` system-append path Task 003 already
  established — no new, parallel logging mechanism;
- a summary mirror on `store.last_readiness_result`/`store.last_readiness_at`,
  if and only if these fields do not already require a schema decision
  outside this gate's scope (the exact final implementation prompt must
  confirm this before coding);
- the webhook-HMAC check and the mapped-Location check registered as
  **pending slots only** — not implemented;
- **the TD-001 fix, as the first mandatory acceptance criterion** (see
  §TD-001 route) — repeated `core_readiness_check` job creation for the
  same store must be safe;
- tests covering tier semantics, per-check persistence, summary mirroring,
  fail-closed aggregation, seam registration, and the mandatory TD-001
  regression test (two `core_readiness_check` runs for the same store do
  not collide);
- a manifest version bump, if the final implementation prompt requires it;
- the mandatory research-handoff update.

**Any deviation from the eventual, separately-accepted final
implementation prompt requires a new ChatGPT decision** — the implementer
may not improvise a different model shape, tier list, aggregation rule, or
test list.

## Exact non-goals

Explicitly, and without exception, until their own separate, explicitly
named gate acts:

- **OAuth of any kind** — no client credential handling, no authorization-
  code-grant flow, no token exchange.
- **Token acquisition of any kind.**
- **Setup wizard** of any kind.
- **Lifecycle actions** — no activate/disconnect/reconnect implementation.
- **Product/customer/order/inventory/fulfillment sync** — no domain module
  code of any kind.
- **Dashboards/UI** — no views, menus, actions, wizards, or XML of any
  kind (zero XML in this task).
- **Webhooks/cron implementation** — registered as pending slots only, per
  §Gate constraints above.
- **Any change to `shopify_connector_store_credential.py`** or any
  security file (`ir.model.access.csv`, `shopify_connector_security.xml`)
  beyond read-only consumption of already-existing fields.
- **Any migration** — none is justified by this scope; a future gate that
  needs one must say so by name.
- **Any CI/workflow file.**
- **Any claim that VAL-B2 has passed, or that a live Shopify connection
  has been proven**, anywhere in code, tests, docstrings, or the PR body.
- **Any customer-facing readiness "pass" claim, activation, setup-wizard
  step, or domain-sync enablement that depends on the unproven VAL-B2** —
  per DEC-021 §4, this constraint is binding on every stage of Task 004.
- **Any second task after Task 004** before ChatGPT reviews Task 004's
  implementation PR — this gate, if accepted, authorizes one coding
  session's scope, not a standing mandate.

## TD-001 route

**Decided by ChatGPT's control-room acceptance decision (2026-07-07):
option (a) — fix TD-001 inside Task 004, as the first mandatory
implementation acceptance criterion.**

- **TD-001 is fixed inside Task 004's own scope.** The Task 004
  implementation must make the `core_readiness_check` target-less
  idempotency-collision defect safe for repeated runs — a second
  `core_readiness_check` job for the same store must no longer collide on
  `store_idempotency_key_uniq`. This is the **first** mandatory
  acceptance criterion of the Task 004 implementation PR — it is not
  optional, and it is not deferred to a separate patch.
- **The fix must be minimal and scoped to target-less readiness jobs.**
  It must not alter the already-accepted `core_test_connection` behavior
  (its per-run UUID4 `payload_hash` nonce, established by Task 003) unless
  strictly necessary and explicitly justified in the implementation PR's
  own description.
- **A regression test is mandatory**, proving that two
  `core_readiness_check` job-creation attempts for the same store do not
  collide — mirroring the proof style already used for
  `core_test_connection` (Task 003's VAL-B3).
- **No Task 004 implementation may silently inherit the existing
  `core_readiness_check` collision behavior**, and no implementation may
  silently skip this fix — it is a named, mandatory, first acceptance
  criterion, not a residual to be separately routed.
- **The candidate name "Task 001B — job-framework target-less idempotency
  patch" is retired** as an alternative — it is no longer the chosen
  route; TD-001's fix is folded into Task 004 itself.

## MBQ-05 deferral conditions

Per [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)
and the corresponding
[`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
MBQ-05 row update:

- MBQ-05 (the token-acquisition direction — Option A/B/C) is **deferred
  for Task 004 only, not resolved**, as a final MVP token-acquisition
  strategy.
- This gate, if accepted, does **not** require MBQ-05 to close first — the
  deferral exists precisely so that the readiness-check substrate (which
  only *reads* Task 003's existing test-connection mirror, and never
  acquires or exchanges tokens itself) can be gated for review without
  waiting on the token-acquisition decision.
- **The deferral condition is conditional, not unconditional:** it holds
  only so long as Task 004 (a) implements no OAuth or token-acquisition
  code of any kind, and (b) never asserts a live "connected"/"pass" state
  that VAL-B2 has not actually proven. If either condition is violated,
  the deferral no longer applies and the underlying MBQ-05/VAL-B2 blockers
  revert to fully blocking, per DEC-021 §4.

## Acceptance criteria for the future implementation PR

- Essential-vs-warning behavior is provable: a failed essential check can
  never yield an overall "pass"; warnings never block.
- Every check returns a named, human-readable reason — no raw exception
  text or stack trace surfaces as the primary message.
- Every check is provably read-only — no mutation-capable call path exists
  in any check implementation.
- The credential-validity/test-connection essential check reads only the
  existing `last_test_connection_result` mirror — it does not perform a
  new live Shopify call, and it reports unknown/not-proven when that
  mirror has never recorded a pass (i.e., it never asserts "connected"
  from VAL-B2-absent evidence).
- The webhook-HMAC check and mapped-Location check exist as registered,
  non-implemented pending slots only.
- The domain-extension registration seam is provable: a check can be
  registered from outside `shopify_connector_core` without modifying core
  files.
- **TD-001 is fixed** — a second `core_readiness_check` job for the same
  store no longer collides on `store_idempotency_key_uniq`, proven by the
  mandatory regression test. This is the first acceptance criterion; no
  silent deviation (fix skipped, or fix broadened beyond target-less
  readiness jobs without justification) is acceptable.
- Only the files named in the accepted final implementation prompt's
  allowed-files list were changed — confirmed by `git diff` review, not by
  assumption.
- No file under `addons/` outside the named module's own directory was
  touched; no `adams_base` file was touched; no UI/webhook/cron/domain-
  module file exists; no change to
  `shopify_connector_store_credential.py` or any security file beyond
  read-only consumption.

## Test expectations

- Tier-semantics test: a single failed essential check yields an overall
  fail regardless of any passing/warning checks; a warning-only result
  never yields an overall fail.
- Per-check JSON result persistence into `job.log.payload_snapshot` is
  tested.
- Summary-mirroring test, including the "unknown = not passed" fail-closed
  aggregation rule.
- Seam-registration test proving a check can be registered from outside
  core without modifying core files.
- Read-only guarantee test: no mutation-capable call path exists in any
  check implementation this stage implements.
- **The mandatory TD-001 fix-verification/regression test:** two
  `core_readiness_check` job-creation attempts for the same store must
  both succeed, with no `store_idempotency_key_uniq` collision.
- If the repository still has no Odoo runtime/CI at the time this task
  runs, tests are honestly recorded as written and
  `py_compile`/`pyflakes`-validated only, and
  [`../05-qa/task-004-manual-validation-checklist.md`](../05-qa/task-004-manual-validation-checklist.md)
  becomes mandatory review evidence — never silently skipped or silently
  claimed as executed.

## Rollback expectations

- Rollback is a single-PR revert with no destructive migration required.
- `store.last_readiness_result`/`_at` mirror fields, if populated, remain
  harmlessly stale on rollback — no downstream code may assume they are
  always current.
- No other accepted module or task is broken by reverting this task's PR;
  if Task 005/006 planning material, at the time of rollback, already
  assumes this task's output, the rollback notes in the final
  implementation prompt must say so explicitly rather than assume it away.

## Definition of done for Task 004 implementation

- Code + tests written; tests pass, or are honestly recorded as
  `py_compile`/`pyflakes`-validated only per the Task 001A precedent, with
  the manual validation checklist prepared as mandatory review evidence.
- Lint/format clean.
- `pr-review-checklist.md` section C satisfied.
- Any shortcut logged honestly in `technical-debt-register.md` — not
  hidden or minimized.
- Only the files named in the accepted final implementation prompt's
  allowed-files list were changed.
- The mandatory research-handoff update (`CLAUDE.md` §12) is written,
  including the Learning feedback loop section.
- ChatGPT reviews and explicitly classifies the implementation PR
  (accepted / accepted with minor corrections / revise / reject) before
  any next task starts.
- The change is modular and isolated, consistent with `CLAUDE.md` §9.

## Explicit acceptance requirement

**ChatGPT has reviewed and accepted this gate document's content**,
including the TD-001 route decision above (§TD-001 route). Per the
AR-021/AR-026/AR-028 precedent, this acceptance becomes operative — and
Task 004 implementation *planning* is authorized — **only once this PR is
merged into `Shopify-connector`**, not on draft, and not by this
acceptance being recorded in chat alone. **Task 004 implementation itself
must still be run as its own, separate, later coding session** — issuing
[`task-004-final-implementation-prompt.md`](./task-004-final-implementation-prompt.md)
is a distinct action ChatGPT takes in chat after this PR merges; merging
this PR does not itself start that coding session. Until this PR merges,
Task 004 remains at **gate-opening review** status only.

## Closure rule

- **This gate, if accepted, closes after the future Task 004
  implementation PR is opened as draft.** Opening that PR consumes the
  gate; it does not remain open for repeated or follow-on use.
- **No follow-on coding is authorized by this gate.** Once a Task 004 PR
  exists, any further change beyond fixing review feedback on that same PR
  requires its own separate ChatGPT decision and, if it touches new
  forbidden territory, its own separate gate act.
- **Every future domain task** (product/customer/order/inventory/
  fulfillment, setup wizard, UI, webhooks, lifecycle actions) requires its
  own separate decision-closure package and gate-opening act, mirroring
  this Task 002 → Task 003 → Task 004 pattern; none of it is authorized,
  implied, or shortcut by this document.
