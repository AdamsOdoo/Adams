# Counterfactual — new tests against OLD-head production (proves the defects)

The new/changed tests were overlaid onto a clean worktree at the current
committed head `53d6a74` (the pre-correction PRODUCTION code), with only the
three test files copied in. Command (from .odoo-src, pinned odoo/odoo@30bde9ff):

```
odoo-bin -c cf-oldhead.conf -d blocker_cf \
  -i shopify_connector_core,shopify_connector_product,shopify_connector_sale,\
  shopify_connector_inventory,shopify_connector_fulfillment,\
  shopify_connector_product_export,account,stock --stop-after-init --test-enable \
  --test-tags ':TestSaleOrderProjection,:TestSaleOrderProjectionRpc,\
  :TestOrderReconnectCatchup,:TestFulfillmentReconnectCatchup'
# cf-oldhead.conf addons_path -> a detached worktree at 53d6a74 + old tests replaced
```

Result: **7 failed, 4 error(s) of 41 tests** — the capability is genuinely absent
at the old head. The three REQUIRED demonstrations:

- P0-1 request-level spoof: `TestSaleOrderProjectionRpc.test_no_client_input_reaches_the_projection_over_rpc` **FAIL** (the forged context key writes succeed over RPC);
- P0-1 context-key: `TestSaleOrderProjection.test_no_context_key_authorises_a_projection_write` **FAIL** (the removed key authorises a write at the old head);
- P1-1 order: `TestOrderReconnectCatchup.test_cancelled_import_blocks_until_linked_replacement_succeeds` **FAIL** (cancelling the descendant advances the freshness stamp);
- P1-1 fulfillment: `TestFulfillmentReconnectCatchup.test_cancelled_fulfillment_descendant_blocks_the_stamp` **FAIL** (same, fulfillment side).

Full FAIL/ERROR inventory + result line:

```
FAIL: TestOrderReconnectCatchup.test_a_cancelled_scan_job_remains_blocking
FAIL: TestOrderReconnectCatchup.test_cancelled_import_blocks_until_linked_replacement_succeeds
FAIL: TestOrderReconnectCatchup.test_cancelled_import_resumes_exactly_once_with_a_deterministic_key
FAIL: TestOrderReconnectCatchup.test_other_store_or_generation_successor_never_covers
ERROR: TestSaleOrderProjection.test_a_bindingless_order_cannot_carry_a_store_projection
ERROR: TestSaleOrderProjection.test_cross_company_projection_is_refused
FAIL: TestSaleOrderProjection.test_no_context_key_authorises_a_projection_write
ERROR: TestSaleOrderProjection.test_private_writer_rejects_non_projection_fields
ERROR: TestSaleOrderProjection.test_same_company_store_drift_is_refused_by_the_order_side
FAIL: TestSaleOrderProjectionRpc.test_no_client_input_reaches_the_projection_over_rpc
FAIL: TestFulfillmentReconnectCatchup.test_cancelled_fulfillment_descendant_blocks_the_stamp
7 failed, 4 error(s) of 41 tests when loading database 'blocker_cf' 
```

At the candidate head (fix applied) every one of these is green — see
`focused-candidate-head.md` and the full-suite summary.
