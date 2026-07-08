# Task 004 Quality Gates

> **Preparatory only, at original authoring time. Not authorization to
> code, not an architecture decision, and not a claim that Task 004 is
> unblocked.** This is a generic quality-gate checklist for whatever Task
> 004 ("Readiness check substrate") eventually became, once ChatGPT
> unblocked it. It was deliberately written to not assume Task 004's
> final scope — see
> [`../07-implementation-plan/task-004-readiness-preflight.md`](../07-implementation-plan/task-004-readiness-preflight.md)
> §4 for the original candidate scope. **See the acceptance status block
> immediately below for the current (post-implementation, post-merge)
> state — this original preparatory framing is retained as history, not
> current status.**

## Acceptance status (2026-07-08)

**Task 004 implementation gate: PASSED / ACCEPTED, scoped exactly to the
readiness-check substrate implemented by PR #115.**

- **PR #115 merged** into `Shopify-connector` — merge commit
  `4145faf69ae6c1d541006890fc2b997fe4c07238`.
- **Live Odoo.sh validation passed** — a real Odoo 19 + PostgreSQL
  registry ran the full `shopify_connector_core` suite
  (`0 failed, 0 error(s) of 78 tests`) and the focused
  `TestReadinessCheck` class (`0 failed, 0 error(s) of 31 tests`) against
  PR #115's exact head commit
  (`ddecd9d28ac543145e9b4ec303e84e2afbbd2b15`) before merge. Full
  evidence: [`task-004-validation-results.md`](./task-004-validation-results.md).
- **TD-001 resolved** — see
  [`technical-debt-register.md`](./technical-debt-register.md); proven by
  the live-run regression test, not merely a routing decision.

**Explicit non-claims (unchanged by this acceptance):**

- **VAL-B2 remains deferred, not passed.**
- **MBQ-05 remains deferred for Task 004 only, not resolved** as a final
  token-acquisition strategy.
- **No OAuth, no setup wizard, no UI (views/menus/actions/wizards/
  controllers), no lifecycle (activate/disconnect/reconnect) code, and no
  product/customer/order/inventory/fulfillment/domain sync** exist
  anywhere in PR #115's scope.
- Three essential checks (webhook HMAC, mapped Location, cron/queue
  health) remain registered pending slots by design — a
  fresh/current-state store may still compute overall readiness `fail`
  until future tasks give them a real signal. No customer-facing
  readiness pass is claimed by this acceptance.

## Status (original, pre-implementation)

Prepared 2026-07-07, docs-only, companion to the Task 004 readiness
preflight package. Branch `claude/task-004-readiness-preflight-vgbkt3`.
Modeled on this project's existing gate discipline
(`task-002-credential-storage-gate.md`,
`task-003-api-client-test-connection-gate.md`,
`../06-prompts/implementation-task-template.md`,
`quality-feedback-loop.md`) rather than inventing a new review process.

---

## 1. Pre-start gate

> **State as of 2026-07-07 (original authoring), per
> [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md) and
> ChatGPT's gate-acceptance decision recorded in
> [`task-004-readiness-check-substrate-gate.md`](../07-implementation-plan/task-004-readiness-check-substrate-gate.md):**
> Task 004 implementation was **not started** at authoring time. **Superseded
> 2026-07-08 — see the "Acceptance status" block above: Task 004 implemented,
> PR #115 merged, live-validated, TD-001 resolved.** ChatGPT had formally
> **deferred VAL-B2** from the Task 003 → Task 004 gate (still deferred,
> not passed), and accepted the Task 004 gate document, opening Task 004
> implementation *planning*; implementation itself was then run as a
> separate, later coding session using the finalized
> [`task-004-final-implementation-prompt.md`](../07-implementation-plan/task-004-final-implementation-prompt.md).
> **TD-001's route was decided: fix inside Task 004**, as the first
> mandatory implementation acceptance criterion — and TD-001 **is now
> fixed and resolved**, proven by a live regression-test run on Odoo 19
> (see `technical-debt-register.md`). **No customer-facing readiness
> pass, activation, setup wizard, or domain sync depends on the still-
> unproven VAL-B2** — this constraint applies to every gate below, not
> just the pre-start gate, and remains true after this acceptance.

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
- [x] TD-001's routing decision is made (folded into the Task 004 gate by
      name, or scheduled as its own separate follow-up patch) — not left
      silently unrouted. **Decided 2026-07-07 by ChatGPT's gate-acceptance
      act: fix TD-001 inside Task 004**, as the first mandatory
      implementation acceptance criterion (see
      `../07-implementation-plan/task-004-readiness-check-substrate-gate.md`
      §TD-001 route and `../05-qa/technical-debt-register.md`). **TD-001
      is now `Resolved` (2026-07-08)** — fixed by PR #115 and proven by
      its live-run regression test on Odoo 19; no longer just a routing
      decision.
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
- [x] If the repository still has no Odoo runtime/CI at the time this task
      runs, tests are honestly recorded as written and
      `py_compile`/`pyflakes`-validated only, and a manual validation
      checklist (mirroring `task-003-manual-validation-checklist.md`) is
      prepared as mandatory review evidence — never silently skipped or
      silently claimed as executed. **Satisfied and then superseded:**
      the implementation session honestly recorded `py_compile`-only
      evidence (no local Odoo runtime); a later session then ran the
      real suite live on Odoo.sh — see
      `../05-qa/task-004-validation-results.md`.
- [x] **The TD-001 regression test is mandatory and present**: two
      `core_readiness_check` job-creation attempts for the same store both
      succeed, with no `store_idempotency_key_uniq` collision. **Present
      and passed live** (`test_td001_repeated_readiness_job_does_not_collide`,
      confirmed on Odoo 19 via Odoo.sh — see
      `../05-qa/task-004-validation-results.md`).

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

- [x] TD-001's exact defect (a second `core_readiness_check` job for the
      same store colliding on `store_idempotency_key_uniq`) is **verified
      as fixed** — proven by the mandatory regression test (§3 above),
      run live on Odoo 19 via Odoo.sh. **`Resolved` in
      `technical-debt-register.md` as of 2026-07-08**, after PR #115
      merged and this validation passed.
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

- [x] Task 004's PR is reviewed and explicitly classified by ChatGPT as
      one of: accepted / accepted with minor corrections / revise / reject
      (per `quality-feedback-loop.md` §2) — before any next task (Task 005
      or otherwise) is started. **PR #115 was reviewed across its
      revision cycle: ChatGPT's first review returned a required
      correction** (the `_check_required_scopes`/`_check_domain_flag_enablement`
      fixes, applied before merge) **and the PR was then accepted for
      live validation, merged, and this acceptance recorded** — Task 005
      is not started by this acceptance.
- [ ] Any "revise" or "reject" issue is logged by category
      (`quality-feedback-loop.md` §3) and, if it recurs a third time
      without a prevention rule, escalated per that document's own
      escalation rule.
- [ ] ChatGPT's review explicitly confirms whether this Task 004 stage's
      merge changes the status of any downstream item (Task 005
      prerequisites, the Dashboard's "connection health" card assumptions,
      etc.) — not left implicit.

---

## Acceptance decision (2026-07-08)

**Task 004's implementation gate is PASSED / ACCEPTED for the
readiness-check substrate scope implemented by PR #115** — see
"Acceptance status" at the top of this document and
[`task-004-validation-results.md`](./task-004-validation-results.md) for
the full evidence. This decision does **not** extend to any capability
outside that scope: it does not authorize Task 005, OAuth, the setup
wizard, any UI, any lifecycle action, or any domain sync, and it does not
change VAL-B2's or MBQ-05's own deferred status.

## What this checklist does not do

- It does not assume Task 004's final scope will match the candidate
  described in `task-004-readiness-preflight.md` §4 — every item above is
  phrased generically enough to apply whether the final scope matches that
  candidate exactly, is narrowed further, or is revised by ChatGPT.
- It does not authorize Task 005 or any further implementation.
- It does not mark any Task 003 item complete.
- It does not decide MBQ-05, or resolve it — MBQ-05 remains deferred for
  Task 004 only. MBQ-06 was already decided prior to Task 004 (via
  DEC-018) and TD-001's routing/fix is now resolved (see above) — this
  document only lists them as gate conditions; it is not itself the
  authority that decided them (ChatGPT, per `CLAUDE.md` §2, is).
