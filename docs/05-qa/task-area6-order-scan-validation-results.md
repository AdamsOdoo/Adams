# Area 6 Order-Scan Slice — Validation Results

## Status

**Exact-head Odoo.sh runtime validation campaign EXECUTED (2026-07-17, build `35080469`); outcome: CORRECTION REQUIRED for the backfill/watermark test suite.** (Static/source history retained below.)

- Date: 2026-07-17
- Branch / PR: `sol/wave-2-order-import`; draft PR #176
- Area-6 commit / combined code head: `a9e1d61a6655d6b46b53057e372115c02ba0bdfd`
- Tested runtime SHA (frozen candidate / branch tip): `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8`
- Runtime build / database: `35080469` / `adamsmen-sol-wave-2-order-import-35080469` (Odoo 19.0, PostgreSQL 16.14)

## Exact-head runtime results (Area-6 scope) — 2026-07-17

Full campaign evidence is in `task-012-order-import-validation-results.md` §"Exact-head runtime validation campaign". Area-6-specific results:

**Green at runtime:**

- Order-scan cron loaded exactly once (`ir_cron_shopify_connector_order_scan`, active, 15-minute interval); `order_import_scan` registered with `remote_read_replay_safe` and LC-1 `ondelete` reassignment.
- `TestOrderScanTriggers` (7 methods) all pass: cron requires connected store + `sale_domain_enabled` + `order_scheduled_sync_enabled`; default scheduled flag False; manual store/selected-binding triggers are role-gated, enqueue-only and collision-safe; **scan enumerates and enqueues only and never imports inline**; pagination/duplicate edges fail closed; store progress helpers are non-stored and accurate.
- `TestOrderWatermarkBackfill.test_watermark_advances_only_after_complete_pagination` and `test_watermark_uses_thirty_minute_overlap` pass.
- Two genuine independent-PostgreSQL-connection scan/binding-race tests pass across 3 OS-process repetitions (one scan job; one permanent binding; one sale order; losing path cleaned up).
- `preview_backfill`/`confirm_backfill` are correctly Administrator-gated at runtime (`_assert_admin` rejects Auditor/Operator/Reviewer and the default `SUPERUSER` env).

**Failing (5 of 7 watermark/backfill methods) — see the classified inventory in the Task 012 doc:**

- Four are **test defects**: the positive-path `preview_backfill`/`confirm_backfill` calls run from the default `SUPERUSER` env instead of `.with_user(<connector admin>)`, so the (correct) `_assert_admin` gate raises `AccessError` (`test_confirm_requires_exact_current_preview_token_then_enqueues`, `test_preview_classifies_all_buckets_and_creates_nothing`, `test_stale_or_boolean_confirmation_never_enqueues`, `test_read_all_orders_honesty_never_silently_truncates`).
- One needs **production-vs-test adjudication**: `test_partial_page_failure_holds_watermark_and_remains_resumable` expected 1 enqueued `order_import_sync` job after a mid-scan failure but found 0 — the "resumable partial page" contract versus whole-scan transactional rollback must be adjudicated in architecture review, not silently reconciled.

Correction is Sol-worker scope (DEC-032 / CLAUDE.md §13); the runtime operator made no code/test change. PR #176 remains draft/open/unmerged.

## Implemented behavior

- `order_import_scan` is gated by the accepted existing `sale_domain_enabled` flag and declares `remote_read_replay_safe` plus LC-1 historic conversion.
- The scan uses one read-only, cursor-paginated `orders` query sorted by `UPDATED_AT`; it enumerates and enqueues `order_import_sync` jobs only and never imports inline.
- A per-store `order_scheduled_sync_enabled` flag gates the 15-minute cron; disabling it stops only new scheduled scans.
- Operator/Administrator store and selected-binding actions enqueue only and reuse an active job on collisions.
- Incremental discovery starts at the last successful checkpoint minus 30 minutes. The checkpoint advances only after complete pagination and is held on partial failure.
- Administrator backfill supports `created_at` or `updated_at`, enforces the 60-day/`read_all_orders` boundary, performs a zero-write preview, includes the complete bounded evidence digest in its confirmation token, re-enumerates before confirmation, and emits one summary log.
- Candidate buckets are `new`, `changed`, `duplicate`, `skipped`, `needs_review`, `enqueued` and `collided`.

## Static/source evidence actually executed

- Order scan Python and cron XML parse.
- `ORDER_SCAN_QUERY` is a `query`, uses `sortKey: UPDATED_AT`, includes cursor/pageInfo pagination and contains no mutation.
- AST guard confirms `execute_business` only, no raw `.execute()`, no `with_context`, one narrow checkpoint `sudo()`, and no job `create()` in the dispatch extension.
- Manifest data registration is exact: ACL CSV then order-scan cron XML.
- Final model/test imports register each new file once.
- Seven scan-trigger and seven watermark/backfill tests are authored; duplicate-prevention adds overlapping-source and two genuine independent-connection concurrency proofs. None is claimed as runtime-passing.

## Explicit bounds

- Scan page size 100; page ceiling 100; maximum 10,000 candidate identities per scan/preview/confirmation enumeration.
- Watermark overlap 30 minutes.
- One active scan identity per store and one active order-import identity per store/order GID through the inherited enqueue uniqueness contract.
- Preview creates zero jobs, logs, sale orders or bindings. Confirmation re-runs discovery; stale/Boolean tokens fail before enqueue.

## Mandatory runtime operator matrix

Run this file's focused classes together with the complete Task 012 matrix at the then-current exact PR #176 head:

1. `TestOrderScanTriggers` and `TestOrderWatermarkBackfill`.
2. Both tests tagged `shopify_connector_order_discovery_concurrency`, repeated for stability.
3. Fresh install, baseline upgrade, cron activation and XML-ID inspection.
4. Disable, uninstall and reinstall: no orphan cron/ACL/XML ID/selection value; historic jobs retain audit history.
5. Full core/product/sale standard suite plus combined SRR-03 smoke.
6. Zero-residue and session/cursor/worker/lease/cron-trigger scans.
7. Credential/token/header/raw-PII log scan.
8. Apply and restore the accepted issue #157 defaults only if the exact known fixture artifact reproduces.

No build, database or passing count exists yet. SRR-03 remains CLOSED from Wave 1; this new read-only scan still needs regression proof and makes no exactly-once claim.

## 2026-07-17 pre-runtime completeness addendum

The complete Wave-2 audit found and corrected one scan collision defect before
runtime: after a PostgreSQL unique conflict, a `REPEATABLE READ` transaction
may not see the concurrently committed winner. `_enqueue_order_scan()` and the
selected-binding enqueue action now return the winner when visible or `False`
when it is not; they never leak the uniqueness exception and never replay a
handler. The database active-job uniqueness rule remains authoritative.

The focused scan tests now prove exact Operator/Admin permission and
Auditor/Reviewer denial, enqueue-only behavior, one-or-zero collision result,
cron catch/log/continue across stores, connected + domain + opt-in gating,
complete-page checkpoint advance, partial-page hold, repeated-cursor and page
ceiling refusal, zero-write preview, exact token/generation binding, and
60-day/`read_all_orders` honesty. The independent-connection enqueue race uses
two committed transactions, two barriers, bounded joins, captured worker
exceptions, exact one-row SQL assertions and unconditional cursor cleanup.

Static rerun: Python/AST, cron XML, manifest, ACL CSV, registration, five
query-only GraphQL constants, execute-wrapper-only, mutation-negative,
duplicate-ID, lifecycle/replay and placeholder/skip scans are clean. The exact
runtime candidate is the documentation commit carrying this addendum and is
recorded in PR #176 after publication. No Odoo.sh result is claimed.
