# Counterfactual proof — the Store 360 test families fail without the implementation

**Purpose.** Prove the five new test suites measure the new capability itself —
not fixture accidents — by running them against the PR #204 base head
`a1c593183f6aaa1238e87486ca518717cefc53a9` (the commit *before* the Store 360
implementation), where they must fail. [Fact — reproduced locally, method and
distilled log below.]

**Method.**
- A clean git worktree was checked out at `a1c5931` (verified
  `git rev-parse HEAD` = `a1c593183f6aaa1238e87486ca518717cefc53a9`).
- ONLY the five new test files were overlaid onto that worktree
  (`test_sale_order_projection.py`, `test_store360_aggregates.py`,
  `test_store360_security.py`, `test_order_reconnect_catchup.py` in
  `shopify_connector_sale/tests/`; `test_fulfillment_reconnect_catchup.py` in
  `shopify_connector_fulfillment/tests/`). No model, view, or migration file
  was copied — the production capability stayed absent.
- Each overlay import was individually guarded in `tests/__init__.py` so that
  one suite's expected `ImportError` could not silently suppress the other
  suites (Odoo drops a module's whole test package when its `tests/__init__`
  raises).
- Fresh database `cf_a1c5931`, same pinned Odoo source
  (`30bde9ff758834a4912c5ae55843d3a7dad849f1`), same Python 3.12 venv,
  `--test-tags` selecting exactly the five suite classes.

**Verdict at a1c5931 (2026-08-01).**

| Outcome | Detail |
| --- | --- |
| Import failure | `test_sale_order_projection` cannot even be imported: it imports `models/shopify_connector_sale_order_projection.py`, which does not exist at the base. Logged marker: `COUNTERFACTUAL: suite test_sale_order_projection cannot even be imported at a1c5931 (capability absent)`. |
| Test run | The four importable suites ran **38 tests: 3 failed, 33 errored** — `3 failed, 33 error(s) of 38 tests` (`cf_a1c5931`). |
| Vacuous passes | Exactly 2 of 38 passed, both *negative-behavior* tests that hold trivially when the capability is absent: `test_skipped_and_failed_final_priors_do_not_auto_resume` (no resume mechanism exists at base, so nothing auto-resumes) and `test_catchup_coexists_with_an_inflight_reconciliation_check` (the two job types' scope keys differ at base as well, prefix or no prefix). [Inference — from the test bodies and the base source; every capability-positive test failed.] |

**At the candidate head the same suites are green** inside the full connector
suite (see `connector-suite-summary.json` in this directory).

## Distilled log (complete FAIL/ERROR inventory of the counterfactual run)

Timestamps trimmed; full raw log was session-local (ephemeral CI container).

```
COUNTERFACTUAL: suite test_sale_order_projection cannot even be imported at a1c5931 (capability absent)
ERROR: TestOrderReconnectCatchup.test_blocking_failure_prevents_the_stamp
FAIL:  TestOrderReconnectCatchup.test_cancelled_import_resumes_exactly_once_with_a_deterministic_key
ERROR: TestOrderReconnectCatchup.test_failed_scan_records_no_pending_lineage
ERROR: TestOrderReconnectCatchup.test_long_gap_without_read_all_orders_fails_closed
ERROR: TestOrderReconnectCatchup.test_promotion_waits_for_descendants_then_stamps
FAIL:  TestOrderReconnectCatchup.test_reconnect_admits_exactly_one_catchup_and_retires_stale_jobs
ERROR: TestOrderReconnectCatchup.test_reconnect_without_sale_domain_admits_nothing
ERROR: TestOrderReconnectCatchup.test_run_scan_records_pending_lineage_in_the_same_pass
ERROR: TestOrderReconnectCatchup.test_stale_lineage_never_stamps_a_newer_generation
ERROR: TestStore360Aggregates.test_bridge_incomplete_on_failures_drives_the_critical_band
ERROR: TestStore360Aggregates.test_bridge_reports_processing_while_a_scan_is_live
ERROR: TestStore360Aggregates.test_commercial_arithmetic_and_exclusions
ERROR: TestStore360Aggregates.test_lifecycle_buckets_count_exactly_and_match_their_drilldowns
ERROR: TestStore360Aggregates.test_mixed_currencies_are_partitioned_never_combined
ERROR: TestStore360Aggregates.test_multi_fulfillment_orders_count_once_at_order_grain
ERROR: TestStore360Aggregates.test_previous_period_zero_gives_no_percentage_basis
ERROR: TestStore360Aggregates.test_previous_window_is_the_shifted_equivalent
ERROR: TestStore360Aggregates.test_top_products_share_uses_the_goods_subtotal_basis
ERROR: TestStore360Aggregates.test_trend_buckets_cover_the_window_and_sum_to_c1
ERROR: TestStore360Aggregates.test_unknown_status_values_fail_closed_into_not_observed
ERROR: TestStore360Aggregates.test_unvalidated_filters_are_refused
ERROR: TestStore360Aggregates.test_zero_orders_never_divides
ERROR: TestStore360Security.test_caller_without_sale_access_gets_the_honest_refusal
ERROR: TestStore360Security.test_non_connector_caller_is_refused_outright
ERROR: TestStore360Security.test_payload_carries_no_secret_or_internal_token
ERROR: TestStore360Security.test_provider_files_perform_no_write_or_enqueue_or_transport
ERROR: TestStore360Security.test_provider_files_use_no_sudo_and_no_raw_sql
ERROR: TestStore360Security.test_provider_reads_are_orm_grouped_reads_or_counts
ERROR: TestStore360Security.test_restricted_caller_aggregates_only_their_own_rule_population
ERROR: TestStore360Security.test_restricted_drilldowns_agree_with_their_counts
ERROR: TestStore360Security.test_restricted_line_rule_governs_units_and_products
ERROR: TestFulfillmentReconnectCatchup.test_complete_pass_records_pending_and_partial_pass_does_not
ERROR: TestFulfillmentReconnectCatchup.test_dispatch_counts_are_governed_by_picking_rules
ERROR: TestFulfillmentReconnectCatchup.test_promotion_requires_quiescence_and_fences_stale_lineages
FAIL:  TestFulfillmentReconnectCatchup.test_reconnect_admits_the_registered_catchup_route
ERROR: TestFulfillmentReconnectCatchup.test_reconnect_without_the_domain_admits_nothing
RESULT: 3 failed, 33 error(s) of 38 tests when loading database 'cf_a1c5931'
```
