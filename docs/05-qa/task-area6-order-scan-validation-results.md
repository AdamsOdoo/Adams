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

## 2026-07-18 runtime-correction reconciliation and candidate freeze

The failed campaign above remains authoritative for SHA
`2e1b1eb62c1fd267bc8ac737e945bc962624e3a8`, build `35080469`, database
`adamsmen-sol-wave-2-order-import-35080469`, and its 5-failure/6-error result.
It is not rewritten as a pass.

Binding rulings in PR #176 comments `5006941549` and `5007682381` were applied
through these correction commits:

- `589739667e0e575ee434cd541277bfdbcc54c5e5` — test/harness corrections;
- `e4a75fc49af622ba908d5a9f15e7272030c2379b` — whole-scan atomic savepoint;
- `662402849401df604f048afd78953c06a6d956a0` — exact address-company query/storage deferral.

The partial-page contract is now explicit: one savepoint spans enumeration,
child-job enqueue, page logs, and checkpoint advancement. A failed attempt
persists no child import jobs and does not move the checkpoint. A successful
retry re-enumerates from the unchanged checkpoint/overlap, creates each child
identity once, and advances only after complete pagination. No explicit commit,
secondary connection, page-level durability, new job state, or new job type was
introduced.

The positive backfill tests now run as a real Connector Administrator while the
Auditor/Operator/Reviewer denial coverage remains. Preview remains zero-write;
confirmation still requires the exact current token; stale or Boolean tokens
enqueue nothing; the 60-day/`read_all_orders` boundary remains fail-closed.

The exact corrected runtime-candidate SHA is the documentation commit carrying
this addendum and is recorded in the PR #176 body. No corrected-head Odoo pass
is claimed. The independent rerun must include clean/full, isolated upgrade
(`19.0.1.2.1` to `19.0.2.0.0` from base
`234c0bb50b3f61b7681e18f0b28839dee619cdb9`), and isolated lifecycle
(uninstall/reinstall/historic-conversion/zero-residue) environments. If either
isolated environment cannot be prepared, the result is `ENVIRONMENT BLOCKED`,
not merge-ready.

The deprecated test-only `check_access_rights()` use was replaced by Odoo 19
`check_access('read')`. The earlier docutils `Unexpected indentation` warning
had no source attribution; no unrelated file is changed and no warning is
globally suppressed. If it recurs, capture logger, module, path/source location,
and surrounding text.

PR #176 must remain open, draft, and unmerged. Wave 3 remains unstarted. No
further source change is planned before the independent exact-head runtime run.

### Complete eleven-failure disposition ledger

| # | Runtime failure | Corrected file(s) | Exact test method | Production/test change | Accepted-contract preservation |
|---|---|---|---|---|---|
| 1 | Address-company query/storage | `models/shopify_connector_order_importer.py`; `tests/test_order_customer_resolution.py` | `TestOrderCustomerResolution.test_addresses_are_child_records_and_deduplicate_on_refresh_path` | Production + test | Shopify address-company is deferred; parent stays a person; invoice/delivery records stay ordinary children; no company partner, B2B field, note, or log is added; address identity remains unchanged. |
| 2 | Tax-fingerprint test duplication | `tests/test_order_tax_resolution.py` | `TestOrderTaxResolution.test_v1_fingerprint_is_full_tuple_versioned_and_fold_free` | Test only | Production fingerprint/version remains unchanged; explicit pairwise assertions prove all accepted tuple distinctions and NFC behavior. |
| 3 | Partial-scan rollback and retry | `models/shopify_connector_order_scan.py`; `tests/test_order_watermark_backfill.py` | `TestOrderWatermarkBackfill.test_partial_page_failure_holds_watermark_and_remains_resumable` | Production + test | One savepoint enforces whole-scan atomicity; failed attempt leaves no child jobs/checkpoint movement; successful retry re-enumerates and advances once complete. |
| 4 | Wave-1 exact `account.payment` source guard | `tests/test_customer_duplicate_prevention.py` | `TestCustomerDuplicatePrevention.test_source_level_no_order_product_inventory_fulfillment_models` | Test only | Exact AST string-token matching blocks `account.payment` without false-matching legitimate `account.payment.term`. |
| 5 | COD zero-side-effect assertion | `tests/test_order_cod_import_readmodel.py` | `TestOrderCodImportReadModel.test_successful_manual_transaction_is_snapshot_only` | Test only | Odoo-19-valid before/after row count proves zero `account.payment` creation; COD remains read-model only. |
| 6 | Legal pending wait/expiry fixture | `tests/test_order_confirmation_policy.py` | `TestOrderConfirmationPolicy.test_pending_wait_and_expiry_use_existing_job_states` | Test only | Exercises legal `running` to `retry_waiting`/`skipped` transitions; production state machine is unchanged. |
| 7 | Odoo 19 tax-group fixture | `tests/test_order_tax_resolution.py` | `TestOrderTaxResolution.test_mapping_rejects_wrong_company_inactive_or_incompatible_tax` | Test only | Company-aligned `tax_group_id` satisfies Odoo 19; explicit mapping remains required and no tax is auto-created. |
| 8 | Administrator confirmation path | `tests/test_order_watermark_backfill.py` | `TestOrderWatermarkBackfill.test_confirm_requires_exact_current_preview_token_then_enqueues` | Test only | Real Connector Administrator reaches confirmation; exact token/current-evidence requirement remains. |
| 9 | Administrator preview path | `tests/test_order_watermark_backfill.py` | `TestOrderWatermarkBackfill.test_preview_classifies_all_buckets_and_creates_nothing` | Test only | Real Administrator reaches preview; preview remains zero-write and non-admin denial remains. |
| 10 | Administrator read-all-orders path | `tests/test_order_watermark_backfill.py` | `TestOrderWatermarkBackfill.test_read_all_orders_honesty_never_silently_truncates` | Test only | Administrator reaches the intended scope boundary; 60-day/read-all-orders behavior remains fail-closed. |
| 11 | Administrator stale/Boolean-token path | `tests/test_order_watermark_backfill.py` | `TestOrderWatermarkBackfill.test_stale_or_boolean_confirmation_never_enqueues` | Test only | Administrator reaches token validation; stale/Boolean inputs still enqueue nothing. |

No failure is unresolved or partially resolved in the correction batch.

### Exact amended 29-file allowlist

1. `addons/shopify_connector_sale/__manifest__.py`
2. `addons/shopify_connector_sale/data/shopify_connector_sale_cron.xml`
3. `addons/shopify_connector_sale/models/__init__.py`
4. `addons/shopify_connector_sale/models/shopify_connector_order_binding.py`
5. `addons/shopify_connector_sale/models/shopify_connector_order_importer.py`
6. `addons/shopify_connector_sale/models/shopify_connector_order_scan.py`
7. `addons/shopify_connector_sale/models/shopify_connector_sale_order_line.py`
8. `addons/shopify_connector_sale/models/shopify_connector_store_settings.py`
9. `addons/shopify_connector_sale/models/shopify_connector_tax_mapping.py`
10. `addons/shopify_connector_sale/security/ir.model.access.csv`
11. `addons/shopify_connector_sale/tests/__init__.py`
12. `addons/shopify_connector_sale/tests/test_customer_duplicate_prevention.py`
13. `addons/shopify_connector_sale/tests/test_order_binding.py`
14. `addons/shopify_connector_sale/tests/test_order_cod_import_readmodel.py`
15. `addons/shopify_connector_sale/tests/test_order_confirmation_policy.py`
16. `addons/shopify_connector_sale/tests/test_order_customer_resolution.py`
17. `addons/shopify_connector_sale/tests/test_order_duplicate_prevention.py`
18. `addons/shopify_connector_sale/tests/test_order_import_mapping.py`
19. `addons/shopify_connector_sale/tests/test_order_manual_gateway_overlay.py`
20. `addons/shopify_connector_sale/tests/test_order_scan_triggers.py`
21. `addons/shopify_connector_sale/tests/test_order_tax_resolution.py`
22. `addons/shopify_connector_sale/tests/test_order_totals_guard.py`
23. `addons/shopify_connector_sale/tests/test_order_watermark_backfill.py`
24. `docs/01-research/research-handoff.md`
25. `docs/05-qa/architecture-review-log.md`
26. `docs/05-qa/mvp-acceptance-matrix.md`
27. `docs/05-qa/task-012-order-import-validation-results.md`
28. `docs/05-qa/task-area6-order-scan-validation-results.md`
29. `docs/07-implementation-plan/mvp-program-state.md`

The correction continuation itself changes only the importer and this evidence
file. The full PR remains exactly the 29-file allowlist above. No forbidden
scope is added.

### Correction-delta static and source audit

- Exact continuation delta: two commits, two files; importer patch is precisely two GraphQL `company` token removals plus one child `company_name` removal; documentation is append-only.
- The exact 86 authored Wave 2 methods remain across the locked 11 test files; the continuation changes no test file, so no test is skipped, removed, renamed, dynamically excluded, or weakened.
- Five model imports and eleven test-file imports remain unchanged.
- Query/parser consistency is preserved while address-company is absent from both address selections and partner create values.
- Tax-fingerprint production code/version is untouched.
- Scan production delta is one savepoint only; there is no explicit commit or secondary connection.
- Legal job-transition assertions, Administrator-positive paths, non-admin denials, exact payment-source guard, and Odoo-19 tax-group fixture corrections are committed in `5897396`.
- The exact 50 protected binding fields, five read-only GraphQL operations, zero-mutation posture, no-tax-autocreate posture, exact sudo inventory, PII/credential/log redaction, and forbidden-scope guards remain unchanged by the continuation.
- No corrected-head Odoo test, install, upgrade, lifecycle, concurrency, residue, or dev-store pass is claimed from this source audit.
