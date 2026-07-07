# Task 004 Readiness Check Substrate — Gate Document (Proposed)

> **This is the proposed gate document, not code authorization, until
> ChatGPT explicitly accepts and merges it.** It mirrors the
> AR-021/AR-026/AR-028 precedent
> (`limited-core-implementation-gate.md`, `task-002-credential-storage-gate.md`,
> `task-003-api-client-test-connection-gate.md`): a gate exists only once
> its opening document is merged into `Shopify-connector` **with ChatGPT's
> explicit acceptance**. Unlike those three precedent documents — each of
> which was written to perform an already-ChatGPT-reviewed gate-opening
> act — this document has **not** yet been reviewed by ChatGPT. It is a
> **proposal for that act**, prepared as part of this session's
> gate-opening package alongside
> [`task-004-gate-opening-proposal.md`](./task-004-gate-opening-proposal.md).

## Status

- **PROPOSED. NOT YET ACCEPTED. Does not open the Task 004 gate.**
- **Docs-only.** No code, no model, no field, no view, no XML, no Python is
  created by this document or this PR.
- **Will open the Task 004 implementation gate only if and when ChatGPT
  explicitly reviews and accepts this exact document** (or a
  ChatGPT-revised version of it) **and it is merged into
  `Shopify-connector` carrying that acceptance** — not on draft, not on
  review approval alone in chat, not on any earlier commit, and not by
  this session's own act of writing it.
- **Does not implement Task 004.**
- **Does not create code.**
- **Does not call Shopify.** No external network call is made by this
  document or this PR.
- **Does not issue the final implementation prompt** — issuing
  [`task-004-final-implementation-prompt.md`](./task-004-final-implementation-prompt.md)
  is the action that would start a future Task 004 coding session, and
  that action must happen in a separate turn/session, after this gate
  document is accepted, not inside this PR.
- **If accepted, authorizes at most one future coding session** scoped
  exactly to the readiness-check substrate named below — not a standing
  implementation mandate.

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
  [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md),
  with a routing note recorded this session requiring it to be handled
  explicitly by this gate or a separate pre-Task-004 patch (see §TD-001
  route below).

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
- the TD-001 disposition named explicitly in the final implementation
  prompt (see §TD-001 route);
- tests covering tier semantics, per-check persistence, summary mirroring,
  fail-closed aggregation, seam registration, and a TD-001
  non-regression/regression test consistent with whichever disposition the
  final implementation prompt names;
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

Per the routing note recorded this session in
[`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md):

- **TD-001 must be explicitly handled** — either (a) named as a mandatory
  first Task 004 implementation acceptance criterion (i.e., the final
  implementation prompt fixes the `core_readiness_check` target-less
  idempotency-collision defect as part of Task 004's own scope), or (b)
  split out as its own separate pre-Task-004 patch (candidate name: "Task
  001B — job-framework target-less idempotency patch") that must merge
  before Task 004's implementation PR is opened.
- **This gate document does not itself choose (a) or (b).** That choice is
  reserved for ChatGPT's review of this gate document and the final
  implementation prompt — whichever choice ChatGPT makes must be named
  explicitly in the accepted final implementation prompt before any code
  is written.
- **No Task 004 implementation may silently inherit the existing
  `core_readiness_check` collision behavior** without that behavior being
  named and accounted for, either as a fix-in-scope or as an
  explicitly-acknowledged, unchanged residual with its own regression
  test proving the behavior is unchanged.

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
- TD-001's disposition (fixed-in-scope or explicitly-unchanged-residual)
  matches exactly what the accepted final implementation prompt named —
  no silent deviation either way.
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
- A TD-001 test matching whichever disposition the final implementation
  prompt names: either a fix-verification test (if TD-001 is fixed in
  this scope) or a non-regression test proving the existing collision
  behavior is unchanged (if it is not).
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

**This document must be explicitly reviewed and accepted by ChatGPT, and
merged into `Shopify-connector` carrying that acceptance, before Task 004
implementation may begin.** Preparing, drafting, or reading this document
does not open the gate. Neither does merging this docs-only PR by itself
constitute "acceptance" unless the PR's own review record shows ChatGPT
explicitly accepting this gate document's content (mirroring the
AR-021/AR-026/AR-028 precedent, where the gate-opening documents were
merged only after ChatGPT had already reviewed and accepted their
content). Until that acceptance is recorded, Task 004 remains at
**gate-opening review** status only — implementation is not authorized.

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
