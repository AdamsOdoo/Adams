# Task 006C — Validation Results (Sync-Engine Core Skeleton)

## Summary

**ACCEPTED / MERGED.** PR #131 ("Task 006C: sync-engine core skeleton
(enqueue, dispatch, retry)") merged into `Shopify-connector` on
2026-07-09T08:32:33Z, merge commit
`152b1553fe10c6efcbad75b4eba9cfcd2f101385` (PR #131 head commit before
merge: `e68a5319bb7a7602bb8cc72568ef0c022551f542`; base commit:
`6e482ec60b3601c3c77cba257f97b64cc889aae1`). This document is the
closure-level validation-evidence record for Task 006C's scope, mirroring
the format of [`task-005-validation-results.md`](./task-005-validation-results.md).

This is a **docs-only closure record**. No addon/code, test, manifest,
XML/security, migration, or CI file is touched by this document or by the
session that produced it.

## A. Scope

- PR #131, merge commit `152b1553fe10c6efcbad75b4eba9cfcd2f101385`,
  merged into `Shopify-connector`.
- Implementation scope: **core sync-engine skeleton only**, inside
  `shopify_connector_core`.
- **Explicitly out of scope for this PR** (unchanged, not implemented):
  - No product, customer, order, inventory, or fulfillment sync of any
    kind.
  - No webhook controller/receiver of any kind.
  - No OAuth or token-acquisition code of any kind.
  - No setup wizard, view, menu, action, or wizard file of any kind.
  - No security/ACL change (both new models are `AbstractModel`s; no
    new `ir.model.access.csv` row).

## B. What was implemented

- **Job enqueue service** — `shopify_connector_job_enqueue.py`, a new
  `AbstractModel` wrapping `Job.create()`. No new idempotency/scope-key
  mechanism: reuses the existing `idempotency_key`/`operation_scope_key`
  unique constraints verbatim.
- **Dispatch `AbstractModel`** — `shopify_connector_job_dispatch.py`,
  the `ir.cron`-driven claim/drain loop (`run_drain`).
- **Handler-registry dispatch seam** — `_get_handlers()`, a
  `job_type -> handler` dict-lookup registry. A missing handler fails
  safely to `failed_final`/`unknown_system_error`; never hangs, never
  silently drops.
- **Cron drain skeleton** — `shopify_connector_cron_drain.xml`
  (`ir.cron` record; batch size 20, 5-minute interval per the accepted
  Decision E).
- **Retry scheduling constants** — named, tunable constants (12 max
  attempts, 30s base, ×2 multiplier, 30-minute cap, ±20% jitter,
  24-hour window), plus a distinct 1-attempt "safety net" budget for
  `unknown_system_error`. Bounded retries only.
- **Job claim with `try_lock_for_update()`** —
  `_claim_for_dispatch()`: per-candidate-row `try_lock_for_update()`,
  silently skipping any row it cannot lock, re-checking claimability
  under the lock (accepted Decision A). Never a raw SQL `SKIP LOCKED`
  reimplementation, never a PostgreSQL advisory lock.
- **Diagnostic `core_dispatch_selftest` job type** — the accepted
  Decision F diagnostic job type, used for dispatch self-test coverage.
- **State transition helpers** — `_transition_retry_waiting`/
  `_failed_retryable`/`_failed_final`/`_blocked_manual_review`/
  `_skipped` on the job model, implementing the already-accepted
  DEC-009 state semantics, logging exclusively through
  `job.log._system_append()`.
- **Domain-enabled execution-time gating hook** —
  `_domain_flag_for_job_type` (DEC-013 §I.3), added inside `write()`'s
  existing `state -> 'running'` branch, alongside (never replacing) the
  unmodified store-state re-check. Every job_type shipped today maps to
  `None` (a true no-op in production); tested only via a patched
  synthetic mapping; never consulted at `create()` time.
- **Approved `action_disconnect()` one-file exception** —
  `shopify_connector_store.py`, exactly one `write()` vals key added
  (`'manual_review_subreason': False`) to the existing cancellation
  loop. See §C for why this was required and how it was approved.

`shopify_connector_job_log.py` was **not modified** — the existing five
`event_type` values fully covered every log write this task needed.

## C. Runtime validation timeline

Recorded honestly, including the failures found before the merged head
was reached:

1. **First Odoo.sh runtime attempt — failed.** A real Odoo 19/PostgreSQL
   runtime validation (external Odoo.sh, not any Claude session
   environment) starting from head `3e6edd8347560ed5e31bd60bb4296053bfa18c99`
   reported:
   - **4 failures**
   - **1 error**
   - **122 tests loaded before halt**

2. **Failure group 1 — fake-handler signature mismatch (4 test
   failures, fixed).** Fake handlers in `test_job_retry_scheduling.py`
   and `test_job_dispatch.py` were defined as `def _raise(self, job):`
   but stored directly in the `_get_handlers()` dict — a dict lookup
   never triggers Python's descriptor/binding protocol, so the
   retrieved callable was never bound. The dispatcher's real
   `handler(job)` call (one argument) then raised `TypeError` against
   the 2-argument fakes, silently reclassified as `unknown_system_error`
   by the fail-safe exception boundary, masking every intended
   assertion. **Production dispatch/routing code was inspected and
   proven correct — not modified.** Fixed by dropping the stray `self`
   parameter from the three affected fakes, in **test files only**.

3. **Failure group 2 — `action_disconnect()` / `manual_review_subreason`
   (1 error, fixed via approved exception).**
   `action_disconnect()` (`shopify_connector_store.py`) already
   deliberately cancels every non-terminal business job, including
   `blocked_manual_review` (correctly included — it is not in
   `TERMINAL_JOB_STATES`). A job in `blocked_manual_review` legitimately
   carries `manual_review_subreason`, but the cancellation `write()`
   never cleared it, so the move to `cancelled` violated the job
   model's own `_check_manual_review_subreason_required` constraint and
   raised `ValidationError`, aborting `action_disconnect()`. This was
   **identified as a real, pre-existing production lifecycle bug,
   exposed by Task 006C** because Task 006C is the first code path that
   ever sets `blocked_manual_review`. `shopify_connector_store.py` is
   outside Task 006C's allowed-file list, so the fix required explicit
   control-room approval before it could be applied.
   - **Approved one-file exception** granted by ChatGPT review
     artifact/comment ID `4923059289`.
   - **Fix applied:** added `'manual_review_subreason': False` to the
     cancellation `write()` vals (`state`/`cancel_reason`/`finished_at`
     unchanged). No broader disconnect semantics changed —
     `TERMINAL_JOB_STATES`, credential clearing,
     reconnect/activate/test-connection, and the API client are all
     untouched.

4. **Final Odoo.sh result.** The user reported a green Odoo.sh build
   after this final `action_disconnect()` fix. **This has not been, and
   still is not, independently verified by Claude through the GitHub
   API.** The PR #131 body records this the same way. As of this
   closure session, `pull_request_read get_status` for head
   `e68a5319bb7a7602bb8cc72568ef0c022551f542` still returns
   `state: pending`, `total_count: 0`, and `get_check_runs` still
   returns `total_count: 0`, `check_runs: []` — no CI/Odoo.sh
   integration is reachable via this repository's GitHub API (no
   `.github/workflows`, no configured checks), consistent with every
   prior session on this PR. The merge relied on the
   **user-provided Odoo.sh green-build confirmation**, not on
   independently observed build evidence.

## D. Static validation

The following static checks were run across the sessions that produced
PR #131 and hold at the merged head:

- `py_compile` was run on every changed Python file across sessions.
- Cron XML parse passed (`xml.dom.minidom`).
- `numbercall` removed from the cron XML (Odoo 19 does not support it).
- Invalid XML comment fixed.
- Manifest wording corrected (removed a false "no Shopify API
  client"/"no external API calls" whole-module claim; the module has
  carried a working API client/test-connection foundation since
  Task 003/004 — the corrected wording scopes the claim to the
  Task 006C skeleton itself).
- Source-level checks passed:
  - No direct `job.log.create()` call anywhere in dispatch.
  - `shopify_connector_job_enqueue.py`'s only `.create(` call targets
    `shopify.connector.job`.
  - No Shopify API client reference and no `.execute(` call in any
    Task 006C changed production file.
  - No new `sudo()` call introduced in any new production file.

## E. What is accepted

- Task 006C implementation is **accepted and merged** (PR #131, merge
  commit `152b1553fe10c6efcbad75b4eba9cfcd2f101385`).
- Runtime validation is **accepted as sufficient for merge** on the
  basis of the user-provided Odoo.sh green-build confirmation described
  in §C — not on independently observed build evidence.
- The approved one-file exception to `shopify_connector_store.py`
  (review artifact `4923059289`) is accepted, scoped exactly to the one
  `write()`-vals key described in §B/§C.

## F. What is NOT accepted / still open

Explicitly, none of the following are resolved, proven, or closed by
Task 006C or PR #131:

- **Multi-server/concurrent-worker safety is not proven.** The
  `try_lock_for_update()` claim mechanism is proven only at the code
  level (via a stubbed test) — it still requires future runtime proof
  under multiple workers / multi-server deployment where relevant.
- **VAL-B2** remains open (no live Shopify Admin API connection was
  made or attempted).
- **MBQ-05** remains open (scalable many-unrelated-customer
  distribution/auth architecture undecided).
- **TD-002** remains open (`read_fulfillments` readiness-scope
  correctness concern, unaffected by Task 006C).
- The **fulfillment API model** remains open.
- **Product first-sync dedup** thresholds remain open.
- **Token acquisition for many unrelated customers** remains open.
- **Lite/Full packaging** remains open.
- **Checkpoint/resume ownership** remains open.
- **No domain sync implementation exists yet** — no product, customer,
  order, inventory, or fulfillment sync code of any kind has been
  written.

## G. Release/UAT implication

- This PR is **core-engine substrate only** — an internal job
  enqueue/dispatch/retry skeleton with no domain sync wired to it.
- It is **not UAT-ready connector functionality** and must not be
  represented as such.
- Next implementation work (any domain sync, any further core
  prerequisite, or Product MVP work) **must be separately authorized**
  by a distinct ChatGPT implementation prompt; this closure record does
  not itself authorize any further implementation.

## Final acceptance decision

**Task 006C (sync-engine core skeleton) is ACCEPTED**, scoped exactly to
what PR #131 implemented:

- PR #131 merged into `Shopify-connector` — merge commit
  `152b1553fe10c6efcbad75b4eba9cfcd2f101385`.
- Real-runtime validation surfaced two genuine defects (a test-only
  fake-handler signature bug and a real production
  `action_disconnect()`/`manual_review_subreason` bug); both are fixed,
  the second only after an explicit, scoped, control-room-approved
  one-file exception (review artifact `4923059289`).
- Merge acceptance rests on the user-provided Odoo.sh green-build
  report; Claude has not independently verified this build through the
  GitHub API, at merge time or as of this closure session.
- This acceptance proves the Task 006C sync-engine skeleton and its
  tests exist, merged, and (per the user-reported build) pass in
  Odoo 19. It does **not** prove multi-server/concurrent-worker safety,
  and does **not** authorize any domain sync or further implementation.

**Next step:** control room (ChatGPT) reviews this closure package and
decides the next controlled task — see
[`research-handoff.md`](../01-research/research-handoff.md).
