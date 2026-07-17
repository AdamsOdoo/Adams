# Task 012 — Order Import Validation Results

## Status

**CORRECTIONS COMPLETE — CORRECTED-HEAD RUNTIME PENDING (2026-07-17).** See the "Correction addendum — 2026-07-17 (current status)" section below for the full current-facing record; all eleven runtime findings from the first campaign are dispositioned and committed, no corrected-head Odoo.sh pass exists yet, and PR #176 remains open, draft and unmerged.

**Exact-head Odoo.sh runtime validation campaign EXECUTED (2026-07-17, build `35080469`); outcome at that time: CORRECTION REQUIRED — 11 sale-module test failures; `shopify_connector_core` and `shopify_connector_product` green. (Historical — first-campaign record; superseded by the Correction addendum below: all eleven findings are now dispositioned and the correction batch is committed; corrected-head runtime remains pending.)** (The pre-runtime source-validation history below is retained and remains accurate. No source or test code was changed by the runtime operator.)

- Date: 2026-07-17
- Branch / PR: `sol/wave-2-order-import`; draft PR #176 → `mvp/program-integration`
- Verified base / merge base: `234c0bb50b3f61b7681e18f0b28839dee619cdb9`
- Audit starting head supplied by the product owner: `c62303611e7c5337e08d1632d0541be55df248ba`
- First audit freeze: `d348b9a180578992317840dc0e99b5349b89eada`
- Post-freeze discrepancy corrections: stronger dispatcher-commit concurrency proof and restoration of the complete research-handoff history
- Runtime build / database: **not available**
- Hard stop: **condition 5 — no authenticated Odoo.sh capability in this session**

This record's pre-runtime section does not claim an Odoo test pass; the runtime campaign section immediately below now supplies the executed runtime evidence.

## Correction addendum — 2026-07-17 (current status)

**CORRECTIONS COMPLETE — CORRECTED-HEAD RUNTIME PENDING.**

This addendum is the current-facing record for Task 012 / order import. The complete first-campaign evidence in "Exact-head runtime validation campaign — 2026-07-17" below is retained verbatim as historical evidence; its "CORRECTION REQUIRED" recommendation is superseded by this addendum.

- Failed implementation SHA: `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8`
- Build: `35080469`
- Database: `adamsmen-sol-wave-2-order-import-35080469`
- Evidence commit: `936cdf9ebc44c1655ffd2ad46b44d7f7619f895b`
- Failed result: **5 failures / 6 errors** (11 unique findings)
- Binding control-room comments: [`5006941549`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5006941549), [`5007682381`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5007682381), [`5008012338`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5008012338), [`5008123769`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5008123769)
- Correction commits: `589739667e0e575ee434cd541277bfdbcc54c5e5`, `e4a75fc49af622ba908d5a9f15e7272030c2379b`, `662402849401df604f048afd78953c06a6d956a0`, `32237410b45c37f92f80fc07d43ddd6541d6134d`
- All eleven findings (8 test-harness defects + 3 production-vs-test adjudication items) are resolved in source/tests per the binding rulings above; none remains unresolved or partially resolved.
- Whole-scan atomic rollback is the accepted and committed behavior (ruling `5006941549` item 3): a failed scan persists no child job or checkpoint change, and a successful retry re-enumerates and advances only after full pagination.
- Shopify address-`company` mapping to child-address `company_name` is removed and deferred to a post-MVP/B2B enhancement (ruling `5006941549` item 1; commit `662402849401df604f048afd78953c06a6d956a0`).
- Tax-fingerprint production code, version and NFC-normalization semantics are unchanged; only the defective set-cardinality test was replaced with explicit pairwise assertions (ruling `5006941549` item 2).
- All 86 authored Wave 2 order-import test methods remain; no test was removed, skipped, renamed, dynamically excluded or weakened by the correction batch.
- No corrected-head Odoo.sh pass exists yet. The next independent runtime campaign requires: a clean/full install environment; an isolated baseline-upgrade environment; and an isolated uninstall/reinstall lifecycle environment.
- PR #176 remains open, draft and unmerged.
- Wave 3 remains unstarted.

## Exact-head runtime validation campaign — 2026-07-17 (historical — first campaign; superseded by the Correction addendum above)

> Operator runtime campaign run against the frozen runtime candidate in an authenticated Odoo.sh dev build. No source or test file was modified before, during, or as a result of this campaign; the SHA below is the exact frozen head. Correction of the failures found is implementation/test work reserved to the Sol worker (DEC-032 / CLAUDE.md §13) and was **not** performed by the control-room operator.

### Environment (recorded)

- Tested SHA (== branch tip `sol/wave-2-order-import`): `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8`
- Merge base: `234c0bb50b3f61b7681e18f0b28839dee619cdb9` (direct ancestor; exactly 28 changed files; 25 commits since base)
- Odoo.sh build id `35080469`; database `adamsmen-sol-wave-2-order-import-35080469`
- Odoo `19.0` (base module `19.0.1.3`); PostgreSQL `16.14`
- Installed module versions: core `19.0.1.9.1`, product `19.0.2.1.2`, sale `19.0.2.0.0`
- Checkout clean, detached at the frozen head; protected checkpoint `acd8c4691e72cf5590f2a56228b08f183b76cd9a` unchanged; Wave 3 unstarted; SRR-03 remains CLOSED. (`gh`/PR-API state is not queryable in-container — PR status asserted from git-level evidence only.)

### Fresh install with tests enabled — green install, clean registry

Verified in the live DB: five Wave-2 models registered; `shopify_connector_order_binding` and `shopify_connector_tax_mapping` physical tables present (importer/scan are AbstractModel services, no table); three live `UNIQUE` constraints — order `(store_id, shopify_gid)`, order `(store_id, sale_order_id)`, tax `(store_id, shopify_tax_evidence_key)`; both job types `order_import_sync` and `order_import_scan` registered with LC-1 `ondelete` reassignment and `remote_read_replay_safe` replay policy; order-scan cron loaded exactly once (15-minute, active); twelve ACL rows resolve for the four roles (tax-mapping = Administrator write/create only, no role unlink; order-binding = no role unlink); zero duplicate XML IDs; documented store-settings defaults present (`paid_only`, `require_approval`, empty allowlist, window 30, expiry 24, include-test False, scheduled-sync False, company = `env.company`). No migrations directory (none required).

### Test execution (failure cap lifted: `ODOO_TEST_MAX_FAILED_TESTS` raised from the build's `5`)

| Suite | Command | Result |
|---|---|---|
| `shopify_connector_core` (own tests) | `-u shopify_connector_core --test-enable` | **0 failed / 0 errors** (green; 291 tests / 198 at-install) |
| `shopify_connector_product` (own tests) | `-u shopify_connector_product --test-enable` | **0 failed / 0 errors** (green; 183 tests) |
| `shopify_connector_sale` (standard) | `-u shopify_connector_sale --test-enable` | **5 failed / 6 errors of 194** (232 methods, 13.8 s) |
| Order-discovery concurrency (genuine independent PG connections) | `--test-tags shopify_connector_order_discovery_concurrency` ×3 | **3/3 repetitions 0 failed / 0 errors of 2** |

The 86 authored order-import methods = 76 pass / 10 fail (the 2 genuine-connection order tests are `-standard`, excluded from the 194 and run/green separately). The eleventh failure is an inherited Wave-1 customer test.

> Cascade-attribution note: a `-u shopify_connector_core` run cascades to dependents, so Odoo's per-module lines report "0 failures, 8 errors (core)" and "0 failures, 2 errors (product)". These are **double-counting of the same 11 sale failures** during dependents' post_install — verified by extracting the full FAIL/ERROR header set: exactly **11 unique headers, all `shopify_connector_sale`**; zero core-own or product-own test failed.

### Complete sale-module failure inventory (5 FAIL + 6 ERROR) with classification

| # | Class.method | Verdict | Root cause | Classification |
|---|---|---|---|---|
| 1 | `TestCustomerDuplicatePrevention.test_source_level_no_order_product_inventory_fulfillment_models` | FAIL | `assertNotIn('account.payment', src)` matches the legitimate `account.payment.term` (order payment term) added to `store_settings.py` | Wave-2 test defect (over-broad inherited Wave-1 source guard; production correct) |
| 2 | `TestOrderCodImportReadModel.test_successful_manual_transaction_is_snapshot_only` | ERROR | searches `account.payment` by field `ref`, which does not exist on that model in Odoo 19 | Wave-2 test defect / Odoo-19 compatibility |
| 3 | `TestOrderConfirmationPolicy.test_pending_wait_and_expiry_use_existing_job_states` | ERROR | `expired` job fixture built with `state='queued'`; handler calls `_transition_skipped` → `queued→skipped` illegal. Matrix allows `running→skipped`; real dispatch runs handlers on `running` jobs | Wave-2 test-fixture defect (production expiry path correct) |
| 4 | `TestOrderCustomerResolution.test_addresses_are_child_records_and_deduplicate_on_refresh_path` | FAIL | child address `company_name != 'Example Co'` | **Needs production-vs-test adjudication** (does the importer map Shopify address `company` → `res.partner.company_name` on child addresses?) |
| 5 | `TestOrderTaxResolution.test_mapping_rejects_wrong_company_inactive_or_incompatible_tax` | ERROR | `_tax()` helper creates `account.tax` without `tax_group_id`, which is NOT NULL in Odoo 19 (surfaced when the fixture targets a second company with no resolvable default group) | Wave-2 test defect / Odoo-19 compatibility |
| 6 | `TestOrderTaxResolution.test_v1_fingerprint_is_full_tuple_versioned_and_fold_free` | FAIL | expects 8 distinct fingerprints, gets 7 — two evidence variants collide (most likely `source=None` vs `source=''`) | **Needs production-vs-test adjudication** (financial tax-fingerprint contract: are None and empty source intended to be distinct?) |
| 7 | `TestOrderWatermarkBackfill.test_confirm_requires_exact_current_preview_token_then_enqueues` | ERROR | `preview_backfill`/`confirm_backfill` invoked from the default `SUPERUSER` env, which is not in `group_shopify_connector_admin`; `_assert_admin` raises `AccessError` | Wave-2 test defect (production `_assert_admin` gate correct) |
| 8 | `TestOrderWatermarkBackfill.test_partial_page_failure_holds_watermark_and_remains_resumable` | FAIL | expected 1 enqueued `order_import_sync` job after a mid-scan failure, found 0 | **Needs production-vs-test adjudication** (resumable-partial-page contract vs. whole-scan transactional rollback) |
| 9 | `TestOrderWatermarkBackfill.test_preview_classifies_all_buckets_and_creates_nothing` | ERROR | positive-path `preview_backfill` from default env (not Administrator) | Wave-2 test defect (admin context) |
| 10 | `TestOrderWatermarkBackfill.test_read_all_orders_honesty_never_silently_truncates` | FAIL | expected `UserError('Partner Dashboard')`; admin gate raised `AccessError` first (default env not Administrator) | Wave-2 test defect (admin context) |
| 11 | `TestOrderWatermarkBackfill.test_stale_or_boolean_confirmation_never_enqueues` | ERROR | `preview_backfill` from default env (not Administrator) | Wave-2 test defect (admin context) |

Summary: **8 Wave-2 test-harness defects** (including 3 with an Odoo-19-compatibility flavour and 4 sharing the single "backfill positive path not invoked as Administrator" root cause) + **3 items requiring production-vs-test adjudication** (#4 address `company` mapping, #6 tax-fingerprint collision, #8 partial-page resumability). **No confirmed production defect was found**; the three adjudication items could resolve either way and touch financial-fingerprint correctness, the address data model, and a resumability guarantee — they must be routed through architecture review rather than "fixed to make the test pass".

### Business-contract evidence that PASSED at runtime

Protected-field forge/clear guard; complete 50-field stored-field classification; empty PII snapshot / no-customer-PII contract; tax-mapping ACL (Administrator write/create only, no role unlink); manual-gateway approval permissions (Reviewer/Administrator allowed, Auditor/Operator denied) with reason redaction; the full 8-financial-state × 3-confirmation-policy matrix; all manual-gateway policies + COD read-model; scan enumerates/enqueues only and never imports inline; genuine two-connection binding race → exactly one permanent binding, one sale order, one active job, losing path cleaned up (3 independent OS-process repetitions).

### Residue / credential / PII / log audit — clean

0 idle-in-transaction and 0 leaked non-self sessions on the DB; 0 advisory locks; 0 running / 0 retry-waiting jobs; 0 call-leases; 0 leftover order bindings / tax mappings / test stores after all suites; no Shopify access-token, `Authorization`/`Bearer`, connection-string, or raw customer PII in any runtime log; evidence-redaction machinery active; the order-binding table exposes only identifier columns (`shopify_order_name`, `manual_gateway_name`) — no customer email/phone/address/name column. No outbound Shopify HTTP occurred (network-free via patched `execute_business`); no Shopify mutation.

### Not runtime-exercised — environment-constrained / deferred

- **§4 baseline-upgrade** (`19.0.1.2.1 → 19.0.2.0.0`) and **§10 isolated uninstall/reinstall lifecycle**: the container is bound to a single injected database (`-d` is auto-injected) and the scoped PostgreSQL role cannot create a second database; these were not performed rather than mutate/destroy the frozen-head build. Structural upgrade-safety indicators are green (no migrations directory; fresh-install of the new columns is green; new NOT-NULL settings columns rely on the standard ORM `default=` backfill during `-u`; `ondelete`/`selection_add` register cleanly). The live upgrade-replay and uninstall/reinstall remain deferred to an environment that permits a second database.
- **Issue #157 accommodation**: NOT applied — the `notification_type`/`color_scheme` defect did not reproduce.
- **Read-only dev-store evidence (§15)**: no authenticated Shopify credentials are available in this session; no live-evidence claim is made; deferred to Wave 6.

### Recommendation — CORRECTION REQUIRED (historical; superseded by the Correction addendum above)

The frozen runtime candidate `2e1b1eb…` is **not green**. Failed SHA: `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8`. The corrected SHA is to be recorded by the corrector alongside a corrected-head rerun. Correcting the 8 test-harness defects and adjudicating the 3 production-vs-test contract questions is implementation/test work reserved to the Sol worker under DEC-032 / CLAUDE.md §13; the control-room operator made no code or test change. PR #176 remains draft, open and unmerged; Wave 3 remains unstarted. This recommendation reflects the first campaign only; see the Correction addendum near the top of this document for the current, corrected-head-runtime-pending status.

## Implemented scope

- PII-free `shopify.connector.order.binding` with permanent per-store Shopify GID and sale-order uniqueness, complete fail-closed stored-field classification, manual-gateway approval provenance, and Reviewer/Administrator audited approval action.
- `sale.order.line.shopify_line_item_gid` trace field.
- Four read-only importer GraphQL operations: header plus complete line-item, shipping-line and discount-application pagination. Every transport uses `execute_business`; no network call occurs in scan classification or local readiness.
- One read-only order-scan GraphQL operation. Scan enumerates and enqueues only; it never imports inline.
- Atomic whole-order creation and binding; existing bindings refresh evidence without rewriting commercial lines.
- Product variant/template binding-chain resolution; custom-line and connector service products are idempotent and store-scoped.
- Existing customer binding/import sequence, guest email match/create, fallback partner and child-address deduplication.
- Decimal money validation; equal-currency shop/presentment checks; unsupported edit/refund/duty/fee/tip/cash-rounding gates; bounded whole-order reconciliation.
- Versioned exact tax fingerprint and explicit Administrator-maintained mapping; no automatic `account.tax` creation.
- Paid/authorized/pending/partial/terminal confirmation policies; manual-gateway policies and approval refresh; COD read model only.
- `order_import_sync` and `order_import_scan` handlers, `sale_domain_enabled` gate, LC-1 historic conversion and `remote_read_replay_safe` policy.

## Static and source evidence

The complete audit at `d348b9a...` recorded:

- exact 20 Wave-2 changed Python files parsed successfully;
- sale cron XML, manifest and ACL CSV parsed; manifest version `19.0.2.0.0`; ACL inventory 12 rows;
- five GraphQL operation constants, all `query`, zero `mutation`;
- `execute_business` present; raw `.execute()` and `with_context` transport bypasses absent;
- five new models and eleven tests imported exactly once;
- both job types registered once with LC-1 `ondelete` conversion and `remote_read_replay_safe`;
- exact 50-field protected order-binding set and empty `_pii_snapshot_fields()`;
- no Shopify mutation, `account.tax` auto-create, TODO, FIXME, `NotImplemented`, skipped test or broad `assertRaises(Exception)`;
- duplicate XML ID, ACL ID, model, job-type and selection-value scans clean;
- query/parser field coverage reconciled, including explicitly retained evidence-only fields;
- 86 unique test methods across the exact 11 locked order test files.

The post-freeze test correction did not add, remove, skip or rename a test method; the exact count remains 86. No Odoo runtime result is inferred from these source checks.

## Explicit bounds

| Boundary | Value |
| --- | --- |
| Line items | 100/page × 100 pages = 10,000 |
| Shipping lines | 50/page × 100 pages = 5,000 |
| Discount applications | 50/page × 100 pages = 5,000 |
| Order scan / preview | 100/page × 100 pages = 10,000 candidates |
| Solver | K=2; at most 2 dependent lines; at most 25 vectors |
| Tax suggestions | 20 non-binding candidates |
| Sale-line description | 512 characters |
| Pending-payment recheck | 15 minutes |
| Watermark overlap | 30 minutes |
| Currency posture | rounding finer than 0.01 fails closed pending named dev-store evidence |

## Contract-to-code-to-test traceability

Legend: **S** = implemented and statically proven; **R** = implemented, with runtime-only proof remaining; **N/A** = not applicable. No requirement is unclassified.

| Contract requirement | Exact production symbol | Positive proof | Negative / fail-closed proof | Security / concurrency | Runtime | Status |
| --- | --- | --- | --- | --- | --- | --- |
| DoR registration: five models, eleven tests, dependency/data order | `models/__init__.py`; `tests/__init__.py`; `__manifest__.py` | `test_all_five_model_files_are_registered_exactly_once`; `test_manifest_dependency_graph_and_registration_contract` | duplicate/import-count assertions | N/A | fresh install/upgrade | R |
| D-012-1 permanent binding and dual uniqueness | `ShopifyConnectorOrderBinding`; `_store_shopify_gid_uniq`; `_store_sale_order_uniq` | required-field/uniqueness and repeat-import tests | direct duplicate constraints | four-role protected-field matrix; two-connection binding race | DB constraints | R |
| D-012-1 PII-free binding | `_pii_snapshot_fields`; `_additional_protected_binding_fields` | identity/PII and exact-classification tests | excluded-field/query and redaction guards | direct create/write/clear denial | model setup | R |
| D-012-2 read-only header/detail retrieval | `import_order_sync`; four importer query constants; `execute_business` | query-minimization and pagination tests | mutation/raw-execute/torn-page/duplicate-node guards | N/A | mocked transport execution | R |
| D-012-2 explicit pagination bounds | `_collect_connection`; `ShopifyConnectorOrderScan._enumerate` | 100-line and multi-page tests | page-ceiling/repeated-cursor failures | N/A | Odoo execution | R |
| D-012-3 atomic whole-order import | `_apply_import`; outer and nested savepoints | happy-path and repeat import | financial mismatch/null status/race rollback | genuine two-connection race | transaction behavior | R |
| D-012-3 rediscovery refreshes evidence, never rewrites lines | `_refresh_existing`; `_binding_financial_evidence_matches` | authorized-to-paid and repeat import | changed-money stale-quotation guard | binding uniqueness | runtime ORM | R |
| D-012-4 bounded/redacted review evidence | `_redact_evidence`; `_safe_evidence`; `_safe_gateway_evidence`; job transitions | preview/redaction tests | PII string-surface assertions | audit/log scan | runtime logs | R |
| D-012-5 customer resolution reuses accepted paths | `_resolve_customer`; existing customer importer/matcher | eight customer-resolution tests | ambiguity/company/no-PII fallback holds | inherited binding ACLs | ORM matching | R |
| D-012-6 product/custom/gift-card resolution | `_resolve_line_product`; connector service-product helpers | service-product, custom and gift-card imports | missing product holds then exact retry | inherited product bindings | ORM products | R |
| D-012-7 exact decimal/totals policy | money validators; `_precreation_gates`; `_solve_and_assert_totals`; bounded solver | exact tax-free/tax-included/discount/high-value/zero-decimal tests | currency/original/current/tip/duty/fee/rounding failures | N/A | Odoo tax engine | R |
| D-012-8 financial-state and confirmation policy | `_confirmation_outcome`; `_handle_order_import_sync` | complete 8-state × 3-policy matrix | null/reversal/partial/pending/expiry routes | protected snapshots | job transitions | R |
| D-012-9 explicit tax mapping only | `ShopifyConnectorTaxMapping`; `_resolve_tax` | explicit mapped-tax reuse | no auto-create/rate fallback; company/inactive/incompatible rejection | four-role ACL matrix | ACL/constraint setup | R |
| D-012-10 source-tax fingerprint | `build_tax_fingerprint`; `canonical_tax_rate`; preview helpers | full-tuple/version/case/NFC tests | collision/shape/uniqueness tests | Administrator-only create/write | DB uniqueness | R |
| D-012-11 COD read model only | binding COD fields; `_binding_snapshot_vals`; `_manual_collected_amount` | four COD tests | source guard forbids payment/mark-paid behavior | protected fields | ORM initialization | R |
| D-012-12 handler/gating/replay | `ShopifyConnectorJobOrderExtension`; `ShopifyConnectorJobDispatchOrderExtension`; `_handle_order_import_sync` | handler/replay/source guards | disabled/stale store refusal | inherited JOB-ACTIONS | dispatcher regression | R |
| DEC-035 equal-currency/MoneyBag policy | `_validate_money_bag_shape`; `_validate_money_bag_currency`; `_money_equal`; `_precreation_gates` | exact amount/currency tests | both-side mismatch failures | N/A | Decimal/currency runtime | R |
| DEC-035 taxes/discounts/shipping/tips/duties/fees/rounding | parser, mapping and solver helpers | mapped taxes, all-discount and shipping tests | unsupported-component gates | N/A | Odoo tax engine | R |
| DEC-035 three confirmation policies | settings + `_confirmation_outcome` | 8×3 matrix | changed evidence/no stale confirm | protected policy evidence | runtime | R |
| DEC-035 three manual-gateway policies | `_classify_manual_gateway`; `_confirmation_outcome` | all-policy/COD matrix | unapproved/card-PENDING/mixed/malformed guards | N/A | runtime | R |
| Manual approval authorization/reason/provenance | `action_approve_manual_gateway_order` | Reviewer success + Administrator path | Auditor/Operator, empty reason, policy/gateway/evidence/state/company refusals | exact two-field quotation read sudo | ACL/action | R |
| Manual approval authoritative refresh/idempotency | approval enqueue + `_refresh_existing` | refresh-confirm and repeated approval | stale/changed evidence remains draft/review | one active job | job/runtime | R |
| Manual approval atomic audit/enqueue | action savepoint; `_create_lifecycle_audit_job`; enqueue service | exact actor/timestamp/one audit | audit and enqueue failure rollbacks | redacted reason | transaction/log | R |
| DoR order defaults/readiness | settings fields; `_settings_for_store`; `_resolve_pricelist`; `_validate_payment_term` | exact company/pricelist/payment-term/team tests | missing configuration failures | inherited Administrator settings ACL | upgrade/defaults | R |
| D-A6-2 enqueue-only manual/selected/scan | `_enqueue_order_scan`; `action_sync_orders_now`; `action_sync_selected`; `_enqueue_order` | trigger/enumeration tests | importer-not-called and collision tests | Operator/Administrator gates | cron/job | R |
| D-A6-3 opt-in scheduled cron | `_cron_enqueue_order_scans`; cron XML | both flags + connected store | disabled/disconnected refusal; per-store error continuation | internal cron | XML/cron | R |
| D-A6-4 30-minute watermark and safe checkpoint | `_incremental_start`; `run_scan`; `_enumerate` | overlap/complete-page advance | partial failure holds checkpoint | one exact settings checkpoint sudo | DB/cron | R |
| D-A6-6 stale generation/replay refusal | enqueue service + inherited generation/domain contracts | fresh-generation paths | stale/disconnected/disabled tests | replay-policy guard | dispatcher | R |
| PD-RB preview has zero writes | `preview_backfill`; `_enumerate(enqueue=False)` | bucket classification | non-admin and zero business/job effects | Administrator gate | ORM/cache | R |
| PD-RB token binds exact evidence | `_preview_token`; `confirm_backfill` | valid token enqueue/idempotency | Boolean/stale/generation-changed token refusal | Administrator gate | ORM | R |
| 60-day/read-all-orders honesty and bounds | `_assert_access_window`; `_validate_backfill_range`; `_enumerate` | in-window preview/confirm | over-window and truncation refusal | Administrator gate | Shopify fixture/runtime | R |
| LC-1 historic conversion | both `selection_add` `ondelete` handlers | source-registration test | inherited immutable `original_job_type` guard | inherited SEC-1 | uninstall/reinstall | R |
| No Wave 3+, mutation, UI, webhook or Layer-2 scope | complete Wave-2 production source | negative AST/source guards | forbidden-symbol scan | N/A | N/A | S |

## Complete 86-test inventory

The category shown is primary; many tests cover multiple acceptance criteria.

| Class | Category | Exact methods |
| --- | --- | --- |
| `TestOrderBinding` | schema/model; protected fields; ACL/security | `test_identity_and_pii_contract`; `test_every_stored_connector_field_is_classified`; `test_required_fields_and_uniqueness`; `test_all_roles_cannot_forge_or_clear_protected_fields` |
| `TestOrderImportMappingStatic` | source/AST guard; schema/model; lifecycle | `test_all_five_model_files_are_registered_exactly_once`; `test_four_graphql_operations_are_read_only_and_minimal`; `test_execute_business_only_and_no_context_bypass`; `test_exact_sudo_inventory_and_dispatch_create_guard`; `test_manifest_dependency_graph_and_registration_contract`; `test_job_types_have_lc1_ondelete_and_replay_policy`; `test_no_tax_autocreate_or_shopify_mutation_surface`; `test_redaction_extension_covers_direct_order_pii`; `test_connection_pagination_collects_once_and_detects_torn_reads`; `test_duplicate_node_across_pages_fails_closed` |
| `TestOrderImportMappingFunctional` | customer/product resolution; totals; regression | `test_connector_service_products_are_idempotent_and_store_scoped`; `test_one_hundred_line_order_imports_without_truncation` |
| `TestOrderTotalsGuard` | totals; tax; financial state | `test_null_financial_status_is_fatal_schema_mismatch`; `test_null_original_tax_is_schema_mismatch_even_when_current_zero`; `test_edit_refund_and_shipping_gates_hold_whole_order`; `test_duty_first_fee_cash_rounding_and_tip_gates`; `test_currency_gate_checks_both_moneybag_sides`; `test_original_and_current_money_amounts_must_match`; `test_basic_tax_free_order_reconciles_exactly`; `test_exact_all_discount_line_is_not_double_subtracted`; `test_financial_mismatch_rolls_back_order_and_binding`; `test_tax_excluded_and_tax_included_orders_use_mapped_engine_taxes`; `test_order_and_source_tax_fingerprints_must_reconcile`; `test_high_value_discount_uses_exact_negative_tax_preserving_residual`; `test_zero_decimal_currency_imports_but_three_decimal_is_held` |
| `TestOrderTaxResolution` | tax; ACL/security | `test_v1_fingerprint_is_full_tuple_versioned_and_fold_free`; `test_previews_are_bounded_and_redacted`; `test_mapping_acl_is_admin_write_create_only_and_no_unlink`; `test_mapping_rejects_wrong_company_inactive_or_incompatible_tax`; `test_explicit_mapping_only_resolution`; `test_mapping_key_shape_and_uniqueness` |
| `TestOrderDuplicatePrevention` | duplicate prevention | `test_repeat_import_refreshes_one_permanent_binding_and_order`; `test_every_discovery_source_collides_on_same_entity_identity`; `test_overlapping_windows_and_repeated_pages_do_not_duplicate`; `test_database_binding_constraints_are_the_last_race_anchor` |
| `TestOrderDiscoveryConcurrencyGenuine` | concurrency | `test_two_connections_return_one_scan_job`; `test_two_connections_create_one_permanent_binding_and_sale_order` |
| `TestOrderCustomerResolution` | customer/product resolution | `test_existing_customer_binding_has_priority_and_parent_is_unchanged`; `test_embedded_customer_reuses_indexed_email_match`; `test_embedded_customer_confident_no_match_creates_person_binding`; `test_guest_email_match_and_no_pii_fallback`; `test_ambiguous_customer_holds_whole_order_and_redacts_evidence`; `test_customer_company_boundary_blocks_before_order_creation`; `test_addresses_are_child_records_and_deduplicate_on_refresh_path`; `test_abandoned_checkouts_never_enter_order_pipeline` |
| `TestOrderConfirmationPolicy` | confirmation policy; financial state | `test_complete_eight_state_by_three_policy_matrix`; `test_authorized_to_paid_refresh_confirms_without_line_rewrite`; `test_post_confirmation_cancellation_is_evidence_only`; `test_post_confirmation_payment_evidence_loss_is_note_only`; `test_changed_money_never_confirms_stale_quotation`; `test_pending_wait_and_expiry_use_existing_job_states`; `test_null_status_routes_failed_final_without_handler_replay` |
| `TestOrderManualGatewayOverlay` | manual gateway; COD; ACL/security | `test_gateway_diagnostic_evidence_redacts_every_string_surface`; `test_all_manual_gateway_policies_and_cod_read_model`; `test_unapproved_and_card_pending_never_take_manual_path`; `test_mixed_transaction_imports_review_draft`; `test_malformed_transaction_authority_is_review_never_confirmation`; `test_approval_permissions_reason_provenance_and_redaction`; `test_approval_refreshes_before_confirm_and_is_idempotent`; `test_changed_evidence_supersedes_approval_without_confirming`; `test_later_paid_evidence_reuses_binding_without_pending_approval`; `test_paid_change_after_recorded_approval_stays_review_draft`; `test_atomic_rollback_when_audit_creation_fails`; `test_policy_or_gateway_change_refuses_without_audit` |
| `TestOrderWatermarkBackfill` | watermark/backfill; ACL/security | `test_watermark_uses_thirty_minute_overlap`; `test_watermark_advances_only_after_complete_pagination`; `test_partial_page_failure_holds_watermark_and_remains_resumable`; `test_preview_classifies_all_buckets_and_creates_nothing`; `test_confirm_requires_exact_current_preview_token_then_enqueues`; `test_stale_or_boolean_confirmation_never_enqueues`; `test_read_all_orders_honesty_never_silently_truncates` |
| `TestOrderCodImportReadModel` | COD; source/AST guard | `test_cod_dimensions_initialize_without_accounting_side_effects`; `test_successful_manual_transaction_is_snapshot_only`; `test_non_cod_order_does_not_acquire_cod_flag`; `test_source_contains_no_mark_paid_or_payment_creation` |
| `TestOrderScanTriggers` | scan; source/AST guard; regression | `test_manual_store_trigger_is_role_gated_enqueue_only_and_idempotent`; `test_selected_binding_trigger_is_enqueue_only_and_collision_safe`; `test_cron_requires_both_flags_and_connected_store`; `test_scan_enumerates_and_enqueues_but_never_imports_inline`; `test_pagination_and_duplicate_edge_fail_closed`; `test_store_progress_helpers_are_nonstored_and_state_accurate`; `test_disconnected_store_and_disabled_domain_refuse_manual_scan` |

There are exactly 86 unique methods: no duplicate names, skips, dynamically excluded methods, placeholder assertions or broad `assertRaises(Exception)`.

## Concurrency structural proof

Both tagged tests open independent `db_connect(dbname).cursor()` connections, set bounded statement/lock timeouts, commit fixtures before racing, and use a start barrier plus a second barrier at the exact production seam.

- The scan race delegates to the real enqueue service. Every worker captures its outcome, closes its cursor in `finally`, and the parent fails on live threads, missing outcomes, unexpected error types or a row count other than one.
- The permanent-binding race delegates to the real precreation gates and real importer. The winner commits normally. The `concurrency_race_conflict` loser intentionally executes `SELECT 1` and commits in the same transaction after catching `JobHandlerError`, matching the dispatcher's continuation posture; therefore the test fails if the importer's outer savepoint did not restore transaction usability.
- Final SQL asserts exactly one binding, one distinct bound `sale_order_id`, and exactly one sale order with the race's unique Shopify-origin marker. An orphan losing quotation therefore fails the test instead of being hidden by a full worker rollback or by a query limited to bound orders.
- Cleanup deletes both bound orders and any same-origin orphan candidate, then closes every connection.

Actual overlap, PostgreSQL lock timing and Odoo registry behavior remain runtime-only until the exact-head Odoo.sh repetitions run.

## Install, upgrade and migration precheck

- Baseline sale version: `19.0.1.2.1`; Wave-2 version: `19.0.2.0.0`.
- No migration directory is required. The order binding and tax mapping are new tables; their required fields are populated by sanctioned create services. `sale.order.line.shopify_line_item_gid` is nullable.
- Existing settings rows receive ORM/database-safe defaults: confirmation `paid_only`, manual policy `require_approval`, gateways empty, window 30, pending expiry 24, include-test False, scheduled False, and company from the active company. Optional pricelist/team/payment-term/checkpoint remain null; importer readiness fails closed until required operational mappings exist.
- Existing customer bindings and partners receive no new field. Order snapshot/provenance/COD fields are on a new table and have no legacy-row backfill risk. The tax fingerprint version default applies only to new tax-mapping rows.
- Both new job selections have LC-1 `ondelete` historic conversion. Cron XML is `noupdate=1`; ACL and model/XML IDs are unique. Uninstall selection cleanup, historic conversion, cron/ACL removal and reinstall remain runtime proof.
- Rollback is database backup restoration plus source revert before production, or forward-disable with preserved imported records in production. Uninstalling `shopify_connector_sale` is not an authorized rollback because it also owns customer history.

## Security, data minimization and exact sudo inventory

The ACL CSV has 12 rows. Order binding follows the accepted Auditor `r`, Operator `rc`, Reviewer `rw`, Administrator `rwc` pattern. Tax mapping is read-only for Auditor/Operator/Reviewer and `rwc` for Administrator. No row grants unlink.

The exact 50 protected order-binding fields comprise nine common binding fields, `sale_order_id`, and all 40 concrete snapshot/provenance/COD fields. All four approval-provenance fields are protected; direct create/write/clear attempts are denied.

| File:line | Symbol | Narrow justification |
| --- | --- | --- |
| `shopify_connector_order_importer.py:530` | `_apply_import` | sanctioned creation of the complete protected order binding |
| `shopify_connector_order_importer.py:2393` | `_refresh_existing` | sanctioned evidence/snapshot refresh only |
| `shopify_connector_order_binding.py:189` | `action_approve_manual_gateway_order` | read only linked quotation `company_id` and `state`; connector roles intentionally do not inherit Sales ACLs |
| `shopify_connector_order_binding.py:234` | same action | write only the four protected approval-provenance fields after caller-role/company/evidence checks |
| `shopify_connector_order_scan.py:73` | `run_scan` | advance only the protected per-store checkpoint after complete pagination |

There is no tax-mapping sudo, public context bypass, broad public-method sudo or job creation outside the enqueue service. Job payloads contain identifiers, hashes and bounded non-PII evidence only. Preview tokens and tax fingerprints use canonicalized non-PII evidence; they never hash raw customer PII, credentials, access tokens, Authorization headers or full Shopify payloads. Runtime log/residue inspection remains mandatory.

## Documentation-accuracy corrections

The final discrepancy pass corrected the following source-document mismatches:

1. restored the complete 18,000+ line `research-handoff.md` history after the first audit publication accidentally replaced it with a compact 23-line snapshot;
2. replaced stale/nonexistent traceability aliases (`_execute_query`, `_paginate_connection`, `_refresh_existing_binding`, `_confirmation_decision`, `_manual_gateway_decision`, `_scan_since`, `_run_order_scan_job`, `preview_order_backfill`, `confirm_order_backfill`, `build_tax_evidence_key`) with the exact current symbols listed above;
3. corrected the sudo inventory names from `_refresh_existing_binding`/`_run_order_scan_job` to `_refresh_existing`/`run_scan`;
4. strengthened the permanent-binding race test so a full worker rollback can no longer mask an ineffective importer savepoint or orphan quotation;
5. required the PR body to name only the final post-correction runtime-candidate SHA.

## Mandatory exact-head Odoo.sh matrix

Run only against the exact frozen SHA recorded in PR #176:

1. Fresh install `shopify_connector_core,shopify_connector_product,shopify_connector_sale` with tests.
2. Upgrade from `mvp/program-integration@234c0bb50b3f61b7681e18f0b28839dee619cdb9`.
3. All Task 012, Area-6, SEC-1 and PII-focused classes in the 11 order test files.
4. Full standard core, product and sale suites.
5. `shopify_connector_order_discovery_concurrency`, both tests, repeated for stability; prove registry-lock restoration, first collision, loser transaction usability and no orphan sale order.
6. LC-1 disable/uninstall/reinstall, selection removal, historic conversion and no-orphan checks.
7. CORE-R1, JOB-ACTIONS, SEC-1 and one combined SRR-03 smoke.
8. Residue audit: jobs/logs/leases/stores/credentials/bindings/orders/products/mappings, cron triggers, temporary files and workers.
9. Database audit: sessions, idle transactions, cursors, locks, leases and cron triggers.
10. Security scan: credentials, access tokens, Authorization headers, raw PII and temporary paths.
11. If issue #157 reproduces exactly, use only the accepted temporary `notification_type` and `color_scheme` defaults, rerun, then drop and verify both defaults are restored.
12. Read-only Shopify dev-store order evidence is preferred but may be deferred honestly to Wave 6 if credentials are unavailable.

Representative command forms:

```text
odoo-bin -d <db> -i shopify_connector_core,shopify_connector_product,shopify_connector_sale --test-enable --stop-after-init
odoo-bin -d <db> -u shopify_connector_core,shopify_connector_product,shopify_connector_sale --test-enable --test-tags /shopify_connector_sale --stop-after-init
odoo-bin -d <db> -u shopify_connector_sale --test-enable --test-tags shopify_connector_order_discovery_concurrency --stop-after-init
```

## Proven / not proven

**Proven statically:** allowed-file scope, registration, read-only query posture, fail-closed field protection, exact symbol traceability, replay/lifecycle declarations, explicit caps, exact sudo inventory, and structural concurrency-test intent.

**Not proven:** Odoo model setup, install/upgrade/uninstall/reinstall, functional test execution, actual concurrency behavior, full regression, runtime residue/security, or dev-store behavior. No Odoo.sh build, Odoo test pass, exactly-once remote-effect claim, Shopify mutation or DEC-031 Layer 2 claim is made.
