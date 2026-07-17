# Area 6 Order-Scan Slice — Validation Results

## Status

**Implementation and static/source validation assembled; exact-head Odoo.sh runtime not run.**

- Date: 2026-07-17
- Branch / PR: `sol/wave-2-order-import`; draft PR #176
- Area-6 commit / combined code head: `a9e1d61a6655d6b46b53057e372115c02ba0bdfd`
- Runtime build / database: **not available**
- Hard stop: **condition 5**

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
