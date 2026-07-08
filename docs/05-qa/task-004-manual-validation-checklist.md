# Task 004 — Manual Validation Checklist

> **Superseding status note (2026-07-08).** Task 004 implementation PR
> [#115](https://github.com/AdamsOdoo/Adams/pull/115) exists and **has
> merged** into `Shopify-connector` (merge commit
> `4145faf69ae6c1d541006890fc2b997fe4c07238`). **Automated/live Odoo.sh
> `TransactionCase` validation has passed** — see
> [`task-004-validation-results.md`](./task-004-validation-results.md)
> for the full evidence record (full module: `0 failed, 0 error(s) of 78
> tests`; focused `TestReadinessCheck`: `0 failed, 0 error(s) of 31
> tests`). **This checklist is now partially superseded by
> `task-004-validation-results.md`** — the substance of most sections
> below (B readiness job creation/TD-001 regression, C tier semantics, D
> payload-snapshot structure, F no domain mutation, G no Shopify
> mutation) is covered by the automated `TestReadinessCheck` suite that
> ran live in that validation pass. A few steps were **not** exercised by
> the automated suite (E's literal Odoo-server-log grep; H's literal
> `ir.ui.menu`/`ir.actions`/`ir.cron` row inspection; I's literal
> revert-and-reinspect) — these **remain optional future hardening, not a
> blocker to Task 004 acceptance**, unless ChatGPT explicitly reopens
> them. **This note does not claim VAL-B2 has passed** (the readiness
> substrate's credential/test-connection check still only reads stored
> evidence and never asserts a live connection — see
> `task-004-validation-results.md`) **and does not claim customer-facing
> readiness** — three essential checks remain registered pending slots by
> design, so a fresh store may still compute overall readiness `fail`.
>
> The original text below is preserved as a reference checklist —
> written before Task 004 implementation existed, describing what a
> future validation session should check. It is retained for its
> per-item detail, not as a live "not yet executed" status.

This document was originally prepared as part of the Task 004
gate-opening package, mirroring the precedent set by
[`task-003-manual-validation-checklist.md`](./task-003-manual-validation-checklist.md)
for Task 003.

## Status (original, pre-implementation)

Prepared 2026-07-07, docs-only, as part of the Task 004 gate-opening
package (branch `claude/task-004-gate-opening-w3f1zg`), **before** any
Task 004 code existed. See the superseding status note above for the
current (post-merge, post-live-validation) status.

## Verified starting state (original, pre-implementation)

- [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)
  (2026-07-07) formally defers VAL-B2 from the Task 003 → Task 004 gate —
  it does not prove a live Shopify connection, and this checklist's own
  future execution must not be read as depending on VAL-B2 having passed
  (Task 004's readiness engine only reads Task 003's existing stored
  mirror; it does not require a fresh Shopify call to validate its own
  registry/tier/aggregation behavior). **VAL-B2 remains deferred, not
  passed, as of the superseding status note above too.**
- [`TD-001`](./technical-debt-register.md) — the `core_readiness_check`
  target-less idempotency-collision defect — was **open** as of this
  original session, with its route decided: ChatGPT accepted fixing
  TD-001 **inside** Task 004, as the first mandatory implementation
  acceptance criterion (see
  [`../07-implementation-plan/task-004-readiness-check-substrate-gate.md`](../07-implementation-plan/task-004-readiness-check-substrate-gate.md)
  §TD-001 route). **TD-001 is now `Resolved`** (see
  `technical-debt-register.md`) — PR #115's regression test proved a
  second `core_readiness_check` job for the same store succeeds with no
  collision, live on Odoo 19.

## Why this exists

Task 004, per its candidate scope, adds a new registry/tier/aggregation
layer on top of the already-validated Task 001–003 job/log substrate, and
writes additional per-check JSON into the same `job.log.payload_snapshot`
family whose live server-log redaction has never been confirmed (VAL-C1's
still-open server-log half). Per `CLAUDE.md` §9's "definition of done" and
this project's Task 001A/Task 003 precedent, a live manual validation pass
is expected before Task 004's implementation PR can be considered fully
reviewed, in addition to whatever automated tests exist.

## Preconditions before starting (future session)

- [ ] A Task 004 implementation PR exists and is in draft, per an accepted
      [`task-004-readiness-check-substrate-gate.md`](../07-implementation-plan/task-004-readiness-check-substrate-gate.md).
- [ ] A live Odoo 19 instance with PostgreSQL is available, isolated from
      any production data.
- [ ] The tester has read: this checklist, the Task 004 implementation
      PR's own description, `technical-debt-register.md` (TD-001's
      recorded disposition for this task), and
      `credential-security-redaction-review-checklist.md`.
- [ ] The tester records environment details (Odoo build, database name,
      module version) before running any step.

---

## A. Install/upgrade and registry checks

- **Install/upgrade.** Install or upgrade `shopify_connector_core` with
  the Task 004 readiness-check model(s) present.
  **Expected:** installs/upgrades without a manifest, security, or model
  registry error; no traceback.
- **Model registry loads.** Query `ir.model` for the new readiness-check
  registry/service model(s).
  **Expected:** the model(s) load with no schema drift to any pre-existing
  Task 001–003 model.

## B. Readiness job creation

- **Readiness job creation.** Trigger a `core_readiness_check` job for a
  test store (with dummy/development credentials only — never a
  production token).
  **Expected:** exactly one `job` row is created
  (`job_type='core_readiness_check'`), with per-check results present.
- **Repeated readiness job behavior / TD-001 regression check.**
  Immediately trigger a second `core_readiness_check` job for the **same**
  store.
  **Expected: the second job succeeds with no collision.** TD-001's route
  is decided — fixed inside Task 004 — so this is the single expected
  outcome, not a two-branch choice. No
  `store_idempotency_key_uniq` violation may occur on the second attempt.
  **If the second job still collides, this is a defect in the Task 004
  implementation PR** (TD-001's mandatory first acceptance criterion was
  not actually satisfied) — record it as a failed acceptance criterion,
  not as an acceptable "TD-001 left unchanged" outcome.

## C. Tier semantics

- **Essential failure → overall fail.** Force at least one essential check
  (e.g., credential validity/test-connection) to fail.
  **Expected:** the overall readiness summary is `fail`, regardless of any
  passing or warning checks.
- **Warning-only → overall warning/pass as defined.** Force at least one
  warning-tier check to fail while all essential checks pass.
  **Expected:** the overall readiness summary reflects the accepted
  warning semantics (warning or pass, per the implementation PR's own
  definition) — never blocked by a warning alone.
- **Unknown/uncomputed → not passed.** Force at least one check to be
  uncomputed (e.g., simulate a check that cannot run).
  **Expected:** the overall readiness summary is never "passed" when any
  essential check's state is unknown/uncomputed — fail-closed aggregation
  confirmed.
- **No live-connection "pass" claim without VAL-B2 evidence.** With the
  store's `last_test_connection_result` mirror in its default/never-passed
  state (i.e., VAL-B2 has not been executed against this store), run the
  readiness check.
  **Expected:** the credential-validity/test-connection essential check
  reports unknown/not-proven — **never** a "connected"/"pass" state. This
  is a hard, non-negotiable check per DEC-021 §4.

## D. `job.log.payload_snapshot` structure

- **Payload snapshot structure.** Inspect the `job.log.payload_snapshot`
  field for a completed readiness-check job.
  **Expected:** contains one JSON entry per check, each with a tier
  (essential/warning), a result, and a named, human-readable reason — no
  raw exception text or stack trace as the primary message.

## E. Redaction scan

- **Redaction scan.** After running at least one readiness-check job
  against a store with a dummy credential set, grep for the exact dummy
  token string used across every persisted surface (`job`, `job.log`
  fields including `payload_snapshot`, and the Odoo server log, if
  available).
  **Expected:** zero hits anywhere other than the intended
  `store.credential.access_token` storage location — mirroring the VAL-C1
  discipline from Task 003's checklist.

## F. No domain model mutation

- **No domain model mutation.** Confirm no
  product/customer/order/inventory/fulfillment record on the Odoo side was
  created or modified by any readiness-check run.
  **Expected:** zero changes — Task 004's scope never touches domain
  models.

## G. No Shopify mutation

- **No Shopify mutation.** If the credential-validity check triggers any
  read against Shopify (it should not, per §Acceptance criteria in the
  gate document — it should read only the stored mirror), inspect the
  Shopify development store's admin for any new or changed record.
  **Expected:** zero changes of any kind; zero webhooks registered.

## H. No UI/menu/controller/cron

- **No UI/menu/controller/cron unless explicitly authorized.** Inspect the
  installed module's `ir.ui.menu`, `ir.actions.act_window`,
  `ir.actions.server`, `ir.cron`, and `ir.model.data` records.
  **Expected:** zero new rows of any of these kinds, unless the accepted
  Task 004 implementation PR explicitly and separately authorized a
  specific one by name (expected: none, per the accepted gate's excluded
  scope).

## I. Rollback observation

- **Rollback observation.** Revert the Task 004 implementation PR (or
  simulate reverting it in a disposable environment) and re-inspect the
  store record.
  **Expected:** `store.last_readiness_result`/`_at` mirror fields (if
  populated) remain harmlessly stale with no downstream error; no other
  accepted module or task is broken by the revert.

---

## Explicit exclusions for this future validation session

- No addon code, test file, security file, manifest, XML, or migration is
  created or modified by executing this checklist.
- No bug found during validation is fixed in the same session — defects
  are recorded and routed to `technical-debt-register.md` or a new,
  separately scoped bug-fix task, mirroring the Task 003 precedent.
- No production Shopify store is used for any step.
- No Shopify write/mutation/webhook of any kind is performed.
- No claim of customer-facing readiness is made by executing this
  checklist — Task 004's readiness substrate remains an internal signal
  until VAL-B2 (or an accepted replacement validation) passes.

## Acceptance / non-acceptance

This checklist, on its own, **proves nothing** — it is not "passed" or
"failed" until either every applicable step is actually executed against
a live environment, or an equivalent automated live-Odoo run covers the
same substance. **As of the original 2026-07-07 session, no step above
had been executed** (no Task 004 code existed yet).

**Update (2026-07-08):** Task 004 implementation PR #115 merged and was
live-validated against a real Odoo 19 + PostgreSQL registry on Odoo.sh —
see [`task-004-validation-results.md`](./task-004-validation-results.md),
which is now the authoritative results document (mirroring
[`task-003-validation-results.md`](./task-003-validation-results.md)'s
role for Task 003). That automated `TestReadinessCheck` suite covers the
substance of sections B, C, D, F, and G above. Sections E (the literal
Odoo-server-log grep), H (the literal `ir.ui.menu`/`ir.actions`/`ir.cron`
row inspection), and I (the literal revert-and-reinspect) were **not**
exercised by that automated run and remain optional future hardening —
not a blocker to the Task 004 acceptance recorded in
`task-004-validation-results.md`, unless ChatGPT explicitly reopens them.
