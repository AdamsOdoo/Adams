# Batch 2 P0 merchant reachability — evidence

**`DRAFT — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

**Evidence class: local supporting evidence — NOT Odoo.sh exact-SHA acceptance
(DEC-041 D8), NOT live-Shopify validation, NOT UAT, NOT independent review.**

This directory is the index to what Batch 2 measured. The narrative belongs in
[`../../../07-implementation-plan/pr-204-batch-2-p0-merchant-reachability-2026-07-30.md`](../../../07-implementation-plan/pr-204-batch-2-p0-merchant-reachability-2026-07-30.md);
what is here is the pointer to each instrument and what it proves, so a
reviewer can re-run any of it rather than take a number on trust.

## How to reproduce every result

```bash
tools/run_connector_suite.sh          # all seven passes, no arguments
```

The runner pins Odoo to `tools/odoo-pin.txt`
(`30bde9ff758834a4912c5ae55843d3a7dad849f1`) and verifies it on every run, so a
cached checkout cannot quietly test a different Odoo. It aborts on any failing
pass, on an unexpected skip, on a missing tour and on a missing HOOT marker.

## The instruments, and what each one is evidence of

| Instrument | Where it lives | What it proves |
| --- | --- | --- |
| Decision behaviour | `addons/shopify_connector_product/tests/test_product_match_decision.py` | The durable decision's linkage, identity rule, refusals, roles, company isolation, consumption and evidence hygiene — 42 tests, each driving a production route |
| Consolidated journeys | `test_batch2_journeys_product.py`, `test_batch2_journeys_sale.py`, `test_batch2_journeys_core.py` | Journeys C, D-P0, I, J-P0 and K-P0, end to end, from a configured store to a database consequence |
| Enumeration producer | `test_product_scan_producer.py` | §8.3's enumeration half: routes, gates, pagination, checkpointing, fail-closed page validation, coalescing |
| Browser tours | `test_ui_b2_settings_tours.py`, `test_ui_b2_product_tours.py`, `test_ui_b2_sale_tours.py` | Each Batch 2 surface reached and operated the way a merchant reaches it, with the database consequence verified in Python afterwards |
| Enlargement / keyboard / RTL / motion / contrast | `test_ui_visual_evidence.py` (`shopify_connector_visual`) | 16 changed surfaces measured at three widths, both directions, 200% zoom, reduced motion, and real Tab traversal to the final actionable control |
| SEC-3 ownership matrix | `test_sec3_store_ownership.py` | The new decision model is covered by the same company/store isolation matrix as every other durable store-scoped model — its own completeness test is what forces that |

## Load-bearing proof

Eight production controls were removed or neutered one at a time and the test
that claims each was required to fail. **8 of 8 caught, 0 missed.** The full
table, with the exact test that caught each, is in §4 of the implementation
record. The production files are restored byte-for-byte, so none of the
mutations is in the diff — `connector_worktree_dirty: false` on the definitive
run is the check that this is true.

## Zero Shopify

No Shopify store, credential, request or mutation occurs anywhere in this
batch. Every test patches the single `_send` transport seam, the only Shopify
token in any fixture is the non-secret constant
`shpat_DUMMYDUMMYDUMMY0000000000000000`, and no real credential exists in the
repository or in the environment that produced this evidence.

## Definitive validation

**All seven passes green at `153be2baa6b77801f508680bc8da12646a10244f`** —
2373 standard tests and 59 non-standard, 36/36 tours on every standard pass,
three HOOT suites verified, both migration passes genuine version-to-version
upgrades with their idempotency re-runs asserting zero scripts,
`connector_worktree_dirty: false`, Odoo pin verified, `shopify_operations:
none`.

The pass table, the environment, the deltas against the `b0dbba2` baseline and
the account of the defect this validation found are in §9 of the implementation
record rather than duplicated here, so there is one place to correct if any of
it is ever superseded.
