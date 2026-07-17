# Task 012 — Order Import Validation Results

## Status

**Implementation and complete pre-runtime source validation assembled; exact-head Odoo.sh runtime not run.**

- Date: 2026-07-17
- Branch / PR: `sol/wave-2-order-import`; draft PR #176 → `mvp/program-integration`
- Verified base / merge base: `234c0bb50b3f61b7681e18f0b28839dee619cdb9`
- Audit starting head supplied by the product owner: `c62303611e7c5337e08d1632d0541be55df248ba`
- First audit freeze: `d348b9a180578992317840dc0e99b5349b89eada`
- Post-freeze discrepancy corrections: stronger dispatcher-commit concurrency proof and restoration of the complete research-handoff history
- Runtime build / database: **not available**
- Hard stop: **condition 5 — no authenticated Odoo.sh capability in this session**

This record does not claim an Odoo test pass, install/upgrade success, runtime integration, residue result, or live Shopify call. The exact final runtime-candidate SHA is recorded in draft PR #176 after the last documentation commit.

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
