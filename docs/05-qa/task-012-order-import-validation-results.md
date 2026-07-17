# Task 012 — Order Import Validation Results

## Status

**Implementation and static/source validation assembled; exact-head Odoo.sh runtime not run.**

- Date: 2026-07-17
- Branch / PR: `sol/wave-2-order-import`; draft PR #176 → `mvp/program-integration`
- Verified base: `234c0bb50b3f61b7681e18f0b28839dee619cdb9`
- Task 012 commit: `92cab4c532e03102473a04cb2f2b23d7f307a480`
- Combined code head before this docs-only handoff: `a9e1d61a6655d6b46b53057e372115c02ba0bdfd`
- Runtime build / database: **not available**
- Hard stop: **condition 5 — no authenticated Odoo.sh capability in this session**

This record does not claim an Odoo test pass, install/upgrade success, runtime integration, residue result, or live Shopify call. The PR remains draft and cannot pass its wave gate until the matrix below is executed at the then-current exact PR head.

## Implemented scope

- PII-free `shopify.connector.order.binding` with permanent per-store Shopify GID and sale-order uniqueness, complete fail-closed stored-field classification, manual-gateway approval provenance, and Reviewer/Administrator audited approval action.
- `sale.order.line.shopify_line_item_gid` trace field.
- Four read-only GraphQL operations: header plus complete line-item, shipping-line and discount-application pagination. Every transport uses `execute_business`; no network call occurs in scan classification or local readiness.
- Atomic whole-order creation and binding; existing bindings refresh evidence without rewriting commercial lines.
- Product variant/template binding-chain resolution; custom-line and connector service products are idempotent and store-scoped.
- Existing customer binding/import sequence, guest email match/create, fallback partner and child-address deduplication.
- Decimal money validation; equal-currency shop/presentment checks; unsupported edit/refund/duty/fee/tip/cash-rounding gates; bounded whole-order reconciliation.
- Versioned exact tax fingerprint and explicit Administrator-maintained mapping; no automatic `account.tax` creation.
- Paid/authorized/pending/partial/terminal confirmation policies; manual gateway policies and approval refresh; COD read model only.
- `order_import_sync` handler, `sale_domain_enabled` gate, LC-1 historic conversion and `remote_read_replay_safe` policy.

## Static and source evidence actually executed

- Exact 20 Wave-2 Python files parsed successfully.
- Sale cron XML, manifest and ACL CSV parsed; manifest version is `19.0.2.0.0`; final ACL inventory is 12 rows.
- The four importer operations start with `query`, contain complete cursor/pageInfo pagination, and contain no mutation.
- AST guard confirms `execute_business` is present and raw `.execute()` / `with_context` bypasses are absent.
- Job types register exact LC-1 `selection_add` / `ondelete` conversion and `remote_read_replay_safe`; dispatch extensions create no job directly.
- Order binding asserts the exact 50 protected fields: 9 shared fields, `sale_order_id`, and 40 concrete system/snapshot/provenance fields; `_pii_snapshot_fields()` is empty.
- Exact production sudo inventory: order binding 2 (one exact two-field
  quotation read plus approval-provenance write); importer 2 (binding create
  and evidence refresh); scan 1 (checkpoint advance); tax mapping 0.
- Negative source scan found no `orderMarkAsPaid`, `orderCreateManualPayment`, connector mutation, account-tax auto-create, context bypass, TODO or FIXME.
- 86 test methods are authored across the exact 11 locked order test files. They are **not described as passing** because no Odoo runtime was available.

## Bounded behavior

| Boundary | Value |
| --- | --- |
| Line items | 100/page × 100 pages = 10,000 |
| Shipping lines | 50/page × 100 pages = 5,000 |
| Discount applications | 50/page × 100 pages = 5,000 |
| Solver | K=2; at most 2 dependent lines; at most 25 vectors |
| Tax suggestions | 20 non-binding candidates |
| Sale-line description | 512 characters |
| Pending-payment recheck | 15 minutes |
| Currency posture | rounding finer than 0.01 fails closed pending named dev-store evidence |

## Official-source compatibility refresh

Accessed 2026-07-17:

- Accessible — Shopify Admin GraphQL 2026-07 `OrderSortKeys.UPDATED_AT`: https://shopify.dev/docs/api/admin-graphql/2026-07/enums/OrderSortKeys
- Accessible — Odoo 19 sale-order tax calculation helpers: https://github.com/odoo/odoo/blob/19.0/addons/sale/models/sale_order.py
- Accessible — Odoo 19 account-tax `price_include_override`: https://github.com/odoo/odoo/blob/19.0/addons/account/models/account_tax.py

These checks confirm compatibility of the accepted implementation shape; they are not runtime evidence.

## Mandatory exact-head Odoo.sh operator matrix

Run on an Odoo 19 dev build checked out at the then-current PR #176 head and record the build, database, exact SHA, clean worktree, module versions, command forms, tags, counts and warnings.

1. Fresh install `shopify_connector_core,shopify_connector_product,shopify_connector_sale` with tests.
2. Upgrade from the inherited `mvp/program-integration@234c0bb...` module state.
3. All Task 012 and SEC-1/PII focused classes in the 11 order test files.
4. Full standard core, product and sale suites.
5. `shopify_connector_order_discovery_concurrency` with both the enqueue and permanent-binding/SO races; repeat for stability.
6. LC-1 install/disable/uninstall/reinstall, selection removal, historic conversion and no-orphan checks.
7. JOB-ACTIONS, CORE-R1, SEC-1 and one combined SRR-03 smoke regression.
8. Residue audit: connector jobs/logs/leases/stores/credentials/bindings/orders/products/mappings created by tests; cron triggers; temporary files; workers.
9. Database audit: sessions, idle transactions, cursors, locks, leases and cron triggers.
10. Security scan: credentials, access tokens, Authorization headers, raw PII and temporary paths.
11. If issue #157 reproduces exactly, apply only the accepted temporary `notification_type` and `color_scheme` defaults, rerun, then drop and verify both defaults are restored.
12. Read-only Shopify dev-store order evidence is preferred but may be deferred honestly to Wave 6 if credentials are unavailable.

Representative command forms (the operator must substitute the Odoo.sh checkout's actual binary/config/database):

```text
odoo-bin -d <db> -i shopify_connector_core,shopify_connector_product,shopify_connector_sale --test-enable --stop-after-init
odoo-bin -d <db> -u shopify_connector_core,shopify_connector_product,shopify_connector_sale --test-enable --test-tags /shopify_connector_sale --stop-after-init
odoo-bin -d <db> -u shopify_connector_sale --test-enable --test-tags shopify_connector_order_discovery_concurrency --stop-after-init
```

## Rollback

Pre-production: restore the database backup taken immediately before module upgrade and deploy a source revert. Production: set `order_scheduled_sync_enabled=False`, quiesce non-terminal jobs through existing actions, and preserve imported sale orders, bindings and tax mappings. Do not uninstall the sale addon as rollback; it also owns the merged customer domain.

## Proven / not proven

Proven statically: allowed-file scope, registration, read-only query posture, fail-closed field protection, replay/lifecycle declarations, explicit caps and exact sudo inventory.

Not proven: Odoo model setup, install/upgrade/uninstall/reinstall, functional tests, concurrency at runtime, full regression, residue/security runtime, dev-store behavior. No exactly-once remote-effect or DEC-031 Layer 2 claim is made.

## 2026-07-17 complete pre-runtime audit

This section supersedes the earlier preflight count and freezes the source
claims at the head produced by this audit's documentation commit. No Odoo.sh
build has been started or claimed. The prior `c6230361...` head exposed four
source-detectable gaps, all corrected before runtime freeze:

1. permanent-binding races could rely on visibility inside a PostgreSQL
   `REPEATABLE READ` transaction after a unique conflict; the loser now raises
   `concurrency_race_conflict` from a nested savepoint and the outer savepoint
   rolls back its quotation and lines, without handler replay;
2. scan/enqueue collision losers could leak `IntegrityError` when the winner
   was not visible in the old snapshot; they now return the visible winner or
   `False` and leave the database uniqueness contract authoritative;
3. several tests used weak fixtures/assertions or broad exception classes;
   exact state, side-effect, rollback, paging, configuration, and race
   assertions now exercise the production seams; and
4. connector Reviewer/Admin groups do not imply Odoo Sales ACLs, so the
   sanctioned manual-gateway action now sudo-reads only `company_id` and
   `state` from its one linked quotation. Generic `sale.order` read remains
   denied to a connector-only Reviewer; actor identity and every write remain
   governed by the accepted action contract.

### Contract-to-code-to-test traceability

Legend: **S** = implemented and statically proven; **R** = implemented, with
runtime-only proof remaining; **N/A** = that proof dimension does not apply.
The positive/negative cells name the exact test method suffix where the class
is evident from the file; fully-qualified names appear in the 86-test inventory
below. Runtime lifecycle proof is required for every row marked R.

| Contract requirement | Production symbol | Positive proof | Negative / fail-closed proof | Security / concurrency | Runtime | Status |
| --- | --- | --- | --- | --- | --- | --- |
| DoR registration: five models, eleven tests, manifest dependency/data order | `models/__init__.py`; `tests/__init__.py`; manifest | `test_all_five_model_files_are_registered_exactly_once`; `test_manifest_dependency_graph_and_registration_contract` | duplicate/import-count assertions | N/A | fresh install/upgrade | R |
| D-012-1 permanent order binding and dual uniqueness | `ShopifyConnectorOrderBinding`; two `models.Constraint` declarations | `test_required_fields_and_uniqueness`; repeat import | direct duplicate constraints | protected-field role matrix; two-connection binding race | DB constraints | R |
| D-012-1 PII-free binding | `_pii_snapshot_fields`; `_additional_protected_binding_fields` | `test_identity_and_pii_contract` | excluded-field/query and redaction guards | four-role create/write/clear denial | model setup | R |
| D-012-2 read-only header/detail retrieval | five query constants; `_execute_query` | four-query/minimization and pagination tests | mutation/raw-execute/torn-page/duplicate-node guards | N/A | mocked transport execution | R |
| D-012-2 explicit pagination bounds | `_paginate_connection`; scan enumeration | 100-line and paging tests | page-ceiling/repeated-cursor failures | N/A | Odoo execution | R |
| D-012-3 atomic whole-order import | `_apply_import`; outer/nested savepoints | happy-path and repeat import | financial mismatch/null status/race rollback | genuine two-connection race | transaction behavior | R |
| D-012-3 rediscovery refreshes evidence, never rewrites lines | `_refresh_existing_binding` | authorized-to-paid and repeat import | changed-money stale-quotation guard | binding uniqueness | runtime ORM | R |
| D-012-4 review/hold evidence is bounded and redacted | `_hold`; safe evidence helpers | preview/redaction tests | PII string-surface assertions | audit/log scan | runtime logs | R |
| D-012-5 customer resolution reuses accepted paths | `_resolve_customer`; customer importer | eight customer-resolution tests | ambiguity/company/no-PII fallback holds | existing binding ACLs | ORM matching | R |
| D-012-6 product/custom/gift-card resolution | `_resolve_line_product`; service-product helpers | service-product, custom and gift-card imports | missing product holds then exact retry | existing product bindings | ORM products | R |
| D-012-7 exact decimal/totals policy | money parsers; `_precreation_gates`; bounded solver | exact tax-free/tax-included/discount/high-value/zero-decimal tests | six gate families, currency/original/current/tip/duty/fee/rounding failures | N/A | Odoo tax engine | R |
| D-012-8 financial-state and confirmation policy | `_confirmation_decision`; `_route_job_error` | complete 8-state × 3-policy matrix | null status, reversals, partial/pending/expiry | protected snapshots | job transitions | R |
| D-012-9 explicit tax mapping only | `ShopifyConnectorTaxMapping`; `_resolve_tax` | explicit mapped-tax reuse | no auto-create/rate fallback; wrong-company/inactive/incompatible rejection | exact four-role ACL matrix | ACL/constraint setup | R |
| D-012-10 source-tax fingerprint | `build_tax_evidence_key`; preview helpers | full-tuple/version/case/NFC tests | collision/shape/uniqueness tests | admin-only write/create | DB uniqueness | R |
| D-012-11 COD read model only | binding COD fields; importer initialization | four COD tests | source guard forbids payment/mark-paid behavior | protected fields | ORM initialization | R |
| D-012-12 job handler/gating/replay | job extensions in importer | handler/replay/source guards | disabled/stale store refusal | existing JOB-ACTIONS | dispatcher regression | R |
| DEC-035 equal-currency and MoneyBag policy | `_money`; `_precreation_gates` | exact amount/currency tests | both-side mismatch failures | N/A | Decimal/currency runtime | R |
| DEC-035 taxes/discounts/shipping/tips/duties/fees/rounding | parser and solver helpers | mapped taxes, all-discount and shipping tests | unsupported component gates | N/A | Odoo tax engine | R |
| DEC-035 three confirmation policies | settings + `_confirmation_decision` | 8×3 matrix | changed evidence/no stale confirm | protected policy evidence | runtime | R |
| DEC-035 three manual-gateway policies | `_manual_gateway_decision` | all-policy/COD matrix | unapproved/card-PENDING/mixed/malformed guards | N/A | runtime | R |
| Manual approval authorization, reason and provenance | `action_approve_manual_gateway_order` | Reviewer success + Admin path | Auditor/Operator, empty reason, policy/gateway/evidence/state/company refusals | generic Sales ACL stays denied; exact read sudo only | ACL/action | R |
| Manual approval authoritative refresh/idempotency | action enqueue + importer refresh | refresh-confirm and repeat call | stale/changed evidence remains draft/review | one active job | job/runtime | R |
| Manual approval atomic audit/enqueue | action savepoint | exact actor/timestamp/one log | audit and enqueue failure rollbacks | redacted reason | transaction/log | R |
| DoR order defaults/readiness | settings fields + importer readiness gates | exact company/pricelist/payment-term/team assertions | missing term/pricelist failure | admin settings ACL inherited | upgrade/defaults | R |
| D-A6-2 enqueue-only manual/selected/scan | `_enqueue_order_scan`; `action_sync_*`; scan handler | trigger and enumerate tests | importer-not-called and collision tests | Operator+ action gate | cron/job | R |
| D-A6-3 opt-in scheduled cron | `_cron_enqueue_order_scans`; cron XML | both flags + connected store | disabled/disconnected refusal; cron continues after store error | internal cron | XML/cron | R |
| D-A6-4 30-minute watermark and safe checkpoint | `_scan_since`; `_run_order_scan_job` | overlap/complete-page advance | partial failure holds checkpoint | one exact checkpoint sudo | DB/cron | R |
| D-A6-6 stale generation/replay refusal | enqueue service + inherited store generation contract | fresh generation paths | stale/disconnected/disabled tests | replay policy guard | dispatcher | R |
| PD-RB preview has zero writes | `preview_order_backfill` | all bucket classification | all non-admin roles and zero business/job/log effects | Administrator gate | ORM/cache | R |
| PD-RB token binds exact current evidence | token/digest helpers; `confirm_order_backfill` | valid token enqueue/idempotency | Boolean/stale/generation-changed token refusal | Administrator gate | ORM | R |
| 60-day/read_all_orders honesty and bounds | backfill query/window validators | under-bound preview/confirm | over-bound and truncation refusal | admin only | Shopify fixture/runtime | R |
| LC-1 historic job conversion | both `selection_add` ondelete handlers | source registration test | immutable `original_job_type` inherited guard | SEC-1 inherited | uninstall/reinstall | R |
| No Wave-3+, mutation, UI, webhook or Layer-2 scope | complete Wave-2 production source | negative AST/source guards | forbidden-symbol scan | N/A | N/A | S |

No requirement was classified missing or contradictory. All production
behavior rows remain runtime-pending because source/static proof is not an
Odoo test pass.

### Complete 86-test inventory

The category shown is the test's primary purpose; many tests intentionally
cover more than one criterion.

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

There are exactly 86 unique methods: no duplicate names, skips, dynamically
excluded methods, placeholder assertions, broad `assertRaises(Exception)`, or
swallowed worker exceptions. Install/upgrade/uninstall behavior is deliberately
runtime matrix coverage rather than a fake unit-test count.

### Concurrency structural proof

Both tagged tests open independent `db_connect(dbname).cursor()` connections,
set bounded statement/lock timeouts, commit fixtures before racing, and use a
start barrier plus a second barrier at the exact production seam. The enqueue
race delegates to the real enqueue service; the binding race delegates to the
real precreation gates and then the real importer. Each worker catches every
`BaseException` into a queue, rolls back failures, commits success, and closes
its cursor in `finally`; the parent joins with a bound and fails on live
threads or missing outcomes. Final SQL asserts exactly one scan job, one
binding identity and one linked sale order. Any serialization, uniqueness,
lock, missing outcome, or unexpected error changes the exact result tuple and
fails the test. Actual overlap and PostgreSQL behavior remain runtime-only.

### Install, upgrade and migration precheck

- Baseline sale version: `19.0.1.2.1`; Wave-2 version: `19.0.2.0.0`.
- No migration directory is required. The order binding, tax mapping and their
  required fields are on new tables, populated atomically by their sanctioned
  create services. `sale.order.line.shopify_line_item_gid` is nullable.
- Existing settings rows receive ORM/database-safe defaults: confirmation
  `paid_only`, manual policy `require_approval`, gateways empty, window 30,
  pending expiry 24, include-test False, scheduled False, and company from the
  active company. Optional pricelist/team/payment-term/checkpoint remain null;
  importer readiness fails closed until required operational defaults exist.
- Existing customer bindings/partners receive no new field. Every order
  binding snapshot/provenance/COD field belongs to a new table and therefore
  has no legacy-row backfill risk. The tax fingerprint version default applies
  only to new tax-mapping rows.
- Both new job selections have LC-1 `ondelete` historic conversion. Cron XML is
  `noupdate=1`; ACL IDs and cron/model XML IDs are unique. Uninstall selection
  cleanup, historic conversion, cron/ACL removal and reinstall are runtime
  proof items. Rollback is backup + source revert; never uninstall sale as a
  rollback because it also owns customer history.

### Security, data minimization and exact sudo inventory

The ACL CSV has 12 rows: order binding follows the accepted
Auditor `r`, Operator `rc`, Reviewer `rw`, Admin `rwc` pattern; tax mapping is
read-only for Auditor/Operator/Reviewer and `rwc` for Admin; no row grants
unlink. The binding's exact 50 protected fields comprise the nine common
fields, `sale_order_id`, and all 40 concrete snapshot/provenance/COD fields;
all four approval fields are included and direct create/write/clear is denied.

Exact Wave-2 sudo sites after audit:

| File:line | Symbol | Narrow justification |
| --- | --- | --- |
| `shopify_connector_order_importer.py:530` | `_apply_import` | sanctioned creation of the complete protected order binding |
| `shopify_connector_order_importer.py:2393` | `_refresh_existing_binding` | sanctioned evidence/snapshot refresh only |
| `shopify_connector_order_binding.py:189` | `action_approve_manual_gateway_order` | read only linked quotation `company_id` and `state`; connector roles intentionally do not inherit Sales ACLs |
| `shopify_connector_order_binding.py:234` | same action | write only the four protected approval-provenance fields after caller-role/company/evidence checks |
| `shopify_connector_order_scan.py:73` | `_run_order_scan_job` | advance only the protected per-store checkpoint after complete pagination |

There is no tax-mapping sudo, public context bypass, broad public-method sudo,
or job create outside the enqueue service. Job payloads contain identifiers,
hashes and bounded non-PII evidence only. Preview tokens/fingerprints use
canonicalized non-PII evidence; they never hash raw customer PII, credentials,
access tokens, Authorization headers or full Shopify payloads. Audit/error/log
messages are identifier/count/reason-only and use the inherited redaction
helpers. Runtime log and residue scans remain mandatory.

### Reproducible static-tool result

Executed from the repository snapshot on 2026-07-17:

- `compileall` and AST parse: 26 sale-addon Python files, clean;
- XML parse: one cron file; CSV parse/column consistency: 12 ACL rows;
- manifest parse: `19.0.2.0.0`, exact dependencies/data order;
- imports: five new models and eleven tests, each exactly once;
- test discovery: 86 unique methods;
- GraphQL: five operation constants, all `query`, zero `mutation`;
- raw `.execute()`, tax auto-create, Wave-3 mutation, TODO/FIXME,
  `NotImplemented`, skip and broad-exception scans: clean;
- duplicate module XML ID and ACL ID scans: clean;
- query/parser coverage: parser-required fields are selected; the explicitly
  retained evidence-only fields are `Order.confirmed`, `Order.closed`,
  `Order.closedAt`,
  `Transaction.id`, and `Transaction.processedAt`; excluded/minimized fields
  remain absent under the existing AST guard;
- registration, job-type, replay-policy, LC-1 ondelete and exact protected-set
  guards: clean.

This is static evidence only. It does not claim an Odoo test pass, an Odoo.sh
build, install/upgrade success, a live Shopify call, or dev-store UAT.
