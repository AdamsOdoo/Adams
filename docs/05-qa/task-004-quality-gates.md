# Task 004 Quality Gates

> **Preparatory only. Not authorization to code, not an architecture
> decision, and not a claim that Task 004 is unblocked.** This is a generic
> quality-gate checklist for whatever Task 004 ("Readiness check substrate")
> eventually becomes, once ChatGPT unblocks it. It is deliberately written
> to not assume Task 004's final scope — see
> [`../07-implementation-plan/task-004-readiness-preflight.md`](../07-implementation-plan/task-004-readiness-preflight.md)
> §4 for the current candidate scope, which this checklist does not
> re-litigate.

## Status

Prepared 2026-07-07, docs-only, companion to the Task 004 readiness
preflight package. Branch `claude/task-004-readiness-preflight-vgbkt3`.
Modeled on this project's existing gate discipline
(`task-002-credential-storage-gate.md`,
`task-003-api-client-test-connection-gate.md`,
`../06-prompts/implementation-task-template.md`,
`quality-feedback-loop.md`) rather than inventing a new review process.

---

## 1. Pre-start gate

> **State as of 2026-07-07, per
> [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md):**
> Task 004 implementation is **still not started**. ChatGPT has formally
> **deferred VAL-B2** from the Task 003 → Task 004 gate, which allows
> Task 004 to proceed to **gate-opening review only** — the checkboxes
> below are **not** satisfied by that deferral alone, and none is checked
> off by this document. TD-001's routing *requirement* is now recorded
> (`../05-qa/technical-debt-register.md`), but the actual routing
> *decision* (fixed in Task 004 vs. a separate patch) remains open pending
> the gate-opening package's review. **No customer-facing readiness pass,
> activation, setup wizard, or domain sync may depend on the unproven
> VAL-B2** — this constraint applies to every gate below, not just the
> pre-start gate.

Before any Task 004 code is written:

- [ ] Task 003 manual validation (`task-003-validation-results.md`) has an
      actual ChatGPT-reviewed Go/No-Go recommendation — not "not yet
      determined." **Conditionally accepted 2026-07-07 for Task 004
      gate-opening review purposes only, per DEC-021 — still requires
      ChatGPT's own review of this PR to become the actual acceptance
      act.**
- [ ] VAL-B2 has passed, or ChatGPT has explicitly accepted a formal
      re-scope of it (per the token-acquisition decision brief §8–§9).
      **Formally deferred (not re-scoped, not passed) 2026-07-07 via
      DEC-021, for Task 004 gate-opening review only.**
- [ ] MBQ-05 (token-acquisition direction) is accepted or explicitly
      deferred by ChatGPT. **Deferred for Task 004 only 2026-07-07 via
      DEC-021 — not resolved; see `master-blueprint-open-questions.md`
      MBQ-05 row.**
- [ ] TD-001's routing decision is made (folded into the Task 004 gate by
      name, or scheduled as its own separate follow-up patch) — not left
      silently unrouted. **Routing requirement recorded 2026-07-07**
      (`../05-qa/technical-debt-register.md`); the specific choice (fold
      into Task 004 vs. separate patch) remains open, to be fixed in the
      accepted gate-opening act.
- [ ] MBQ-06's residual (exact readiness-check copy/XML IDs/thresholds) is
      fixed in the Task 004 task prompt itself, not left as a TBD inside
      the code.
- [ ] A Task 004 gate-opening act exists, is its own separate merged
      document (not this preflight package), and has been merged into
      `Shopify-connector`.
- [ ] A Task 004 final implementation prompt exists, naming an exact,
      exhaustive allowed-files list and an exact, exhaustive forbidden-files
      list, per `CLAUDE.md` §9.
- [ ] The feedback-loop files (`defect-pattern-log.md`,
      `rejected-approaches-log.md`, `architecture-review-log.md`,
      `technical-debt-register.md`) have been checked and are current.
- [ ] No issue type sits at its 3rd-occurrence pause without a prevention
      rule/test/gate in place (per `implementation-task-template.md`).

## 2. PR gate

Before any Task 004 PR is merged:

- [ ] Only the files named in the accepted allowed-files list were changed
      — confirmed by `git diff` review, not by assumption.
- [ ] No file under `addons/` outside the named module's own directory was
      touched; no `adams_base` file was touched.
- [ ] No UI file (views/menus/actions/wizards/XML) exists unless a
      separately-named, gate-opened UI stage explicitly authorized it.
- [ ] No webhook, controller, or cron file exists.
- [ ] No domain module (`shopify_connector_product`/`_sale`/`_inventory`/
      `_fulfillment`) file exists.
- [ ] No change to `shopify_connector_store_credential.py` or any security
      file (`ir.model.access.csv`, `*_security.xml`) beyond read-only
      consumption, unless explicitly named in the task prompt.
- [ ] PR description honestly states what was and was not executed (Odoo
      runtime availability), mirroring the Task 001A/003 precedent rather
      than implying tests ran if they did not.
- [ ] Manifest version bumped, if the task prompt requires it.
- [ ] The mandatory research-handoff update is included in the PR.

## 3. Test gate

- [ ] Tier semantics are tested: a single failed essential check yields an
      overall fail regardless of any passing/warning checks; a warning-only
      result never yields an overall fail.
- [ ] Every check's named-reason output is tested (no check may report a
      pass/fail/warn without an accompanying human-readable reason).
- [ ] Per-check JSON result persistence into `job.log.payload_snapshot` is
      tested.
- [ ] Summary mirroring onto `store.last_readiness_result`/`_at` is tested,
      including the "unknown = not passed" fail-closed aggregation rule.
- [ ] The domain-registration seam is tested (a check can be registered
      from outside `shopify_connector_core` without modifying core files).
- [ ] Every check implemented in this stage is tested as provably
      read-only (no mutation-capable call path exists).
- [ ] If the repository still has no Odoo runtime/CI at the time this task
      runs, tests are honestly recorded as written and
      `py_compile`/`pyflakes`-validated only, and a manual validation
      checklist (mirroring `task-003-manual-validation-checklist.md`) is
      prepared as mandatory review evidence — never silently skipped or
      silently claimed as executed.
- [ ] Prior-defect regression tests exist for any defect named in
      `defect-pattern-log.md` or `technical-debt-register.md` that this
      task's scope touches (specifically: a TD-001 non-regression test, if
      TD-001's routing decision assigns its fix to this task; otherwise a
      test proving TD-001's behavior is unchanged, if this task's scope
      merely consumes the same job type without fixing it).

## 4. Security gate

- [ ] No new `sudo()` call site is added beyond what the accepted task
      prompt names explicitly (mirroring the Task 003 "exactly two
      `sudo()` sites" discipline).
- [ ] No credential value (`access_token` or any secret) is read, logged,
      or echoed anywhere outside the already-reviewed Task 002
      `_get_access_token`/`redact()` substrate.
- [ ] Every check result written to `job.log` fields
      (`message`/`technical_detail`/`payload_snapshot`) is passed through
      the existing redaction contract — no raw credential, raw stack
      trace, or raw internal token appears as a primary label (per RA-016).
- [ ] No new ACL row widens read/write access to `job.log` or the
      credential model beyond what already exists.
- [ ] The VAL-C1 server-log-grep gap (if still open at the time this task
      starts) is either closed first, or explicitly, separately accepted
      by ChatGPT as a residual this task does not need to re-verify itself.

## 5. Retry/idempotency gate

- [ ] TD-001's exact defect (a second `core_readiness_check` job for the
      same store colliding on `store_idempotency_key_uniq`) is verified as
      either fixed (if this task's scope names that fix explicitly) or
      unchanged-and-explicitly-acknowledged (if not) — never silently left
      ambiguous.
- [ ] If this task introduces its own new job-creation path, a repeat-run
      test (mirroring Task 003's VAL-B3) confirms no unintended unique-
      constraint collision.
- [ ] Every check is confirmed idempotent to re-run (re-running the same
      readiness check twice produces the same tier/reason, absent an
      actual underlying state change).

## 6. Logging/error-handling gate

- [ ] Every check failure produces a business-friendly, named reason — no
      raw exception text or stack trace surfaces as the primary message.
- [ ] Every check's outcome is logged via the existing `job.log` write
      path (system-append or the already-reviewed pattern from Task 003),
      not a new, parallel logging mechanism (per RA-013's "no forked
      per-domain logging" rule, extended here to "no forked readiness
      logging").
- [ ] Fail-closed aggregation is provable: an unknown/uncomputed check
      state must never be treated as "passed" in the overall summary.

## 7. No-duplicate-prevention gate

- [ ] No duplicate `core_readiness_check` job can be silently created for
      a store where one is already running/pending, beyond whatever
      behavior TD-001's routing decision explicitly accepts or fixes.
- [ ] If this task adds any create-path for a readiness-related record
      beyond the job/job.log pattern already accepted, a pre-create
      duplicate check is required, per the same two-path duplicate-
      prevention discipline (interactive-preview / automated pre-create
      check) already accepted for domain modules in
      `../07-implementation-plan/mvp-domain-implementation-sequence.md`.

## 8. Rollback gate

- [ ] Rollback is a single-PR revert with no destructive migration
      required.
- [ ] `store.last_readiness_result`/`_at` mirror fields, if already
      populated, remain harmlessly stale on rollback (no downstream code
      assumes they are always current).
- [ ] No other accepted module or task is broken by reverting this task's
      PR (verified by checking whether Task 005/006 planning material, at
      the time of rollback, already assumes this task's output — if so,
      rollback notes must say so explicitly rather than assume it away).

## 9. Documentation gate

- [ ] The mandatory research-handoff update (`CLAUDE.md` §12) is written,
      including the Learning feedback loop section.
- [ ] Any shortcut or compromise is logged honestly in
      `technical-debt-register.md` — not hidden or minimized.
- [ ] Any newly rejected approach is logged in `rejected-approaches-log.md`
      with a stated revisit condition, per `CLAUDE.md` §10.
- [ ] The MBQ register (`master-blueprint-open-questions.md`) is updated
      only if this task's own scope is explicitly authorized to close or
      partially resolve an MBQ row (e.g., MBQ-06's residual) — not
      speculatively touched otherwise.
- [ ] The exact next-session prompt is stated at the end of the session,
      per `CLAUDE.md` §12's "Quick start" step 5.

## 10. ChatGPT review gate

- [ ] Task 004's PR is reviewed and explicitly classified by ChatGPT as
      one of: accepted / accepted with minor corrections / revise / reject
      (per `quality-feedback-loop.md` §2) — before any next task (Task 005
      or otherwise) is started.
- [ ] Any "revise" or "reject" issue is logged by category
      (`quality-feedback-loop.md` §3) and, if it recurs a third time
      without a prevention rule, escalated per that document's own
      escalation rule.
- [ ] ChatGPT's review explicitly confirms whether this Task 004 stage's
      merge changes the status of any downstream item (Task 005
      prerequisites, the Dashboard's "connection health" card assumptions,
      etc.) — not left implicit.

---

## What this checklist does not do

- It does not assume Task 004's final scope will match the candidate
  described in `task-004-readiness-preflight.md` §4 — every item above is
  phrased generically enough to apply whether the final scope matches that
  candidate exactly, is narrowed further, or is revised by ChatGPT.
- It does not authorize Task 004 to start.
- It does not mark any Task 003 item complete.
- It does not decide MBQ-05, MBQ-06, or TD-001's routing — it only lists
  them as gate conditions that must be decided by someone with the
  authority to decide them (ChatGPT, per `CLAUDE.md` §2).
