# Batch 2 real-data and company-isolation correction — before/after evidence

**`DRAFT — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

This directory holds the two runs that make the correction's reproducers
load-bearing rather than descriptive.

## What is here

| File | What it is |
| --- | --- |
| `reproducers-at-ccad8bf.log` | The three head-agnostic reproducer classes run against the **unchanged starting head** `ccad8bf432868650abb80bfb2103bd8d397be549`, in a clean external `git worktree`, with only those files and their `tests/__init__.py` registration added. **13 failed, 0 error(s) of 17 tests.** |
| `reproducers-after-correction.log` | The same 17 tests at the corrected head. **0 failed, 0 error(s) of 17 tests.** |

## Why the reproducers are separate files

`test_product_match_decision.py` and `test_tax_decision_route.py` import the
symbols the correction introduced (`opaque_identity`, `match_value_digest`,
`eligible_sale_tax_domain`, `tax_posture_included`, the cron external-id
constants), so at the starting head they would fail at IMPORT time — which
proves nothing about any defect. The three files below drive PUBLIC production
routes only and import nothing the starting head does not already have, so the
same code runs on both sides:

- `addons/shopify_connector_product/tests/test_batch2_correction_at_any_head.py`
- `addons/shopify_connector_sale/tests/test_batch2_correction_at_any_head.py`
- `addons/shopify_connector_sale/tests/test_tax_mapping_race.py` (`-standard`)

## The four that pass at BOTH heads, and why that is correct

`test_the_display_scrubber_rewrites_every_shape_used_here` is the measurement
the rest of the file rests on — it must hold at both heads or the tests are not
about the defect. `test_manual_product_import_survives_a_disabled_cron` and
`test_manual_order_import_survives_a_disabled_cron` guard that making the
scheduled-state claim truthful did not remove the manual route or its role
gate; nothing about them should change.
`test_recording_one_ambiguity_does_not_supersede_an_unrelated_one` is a
regression guard whose sharper twin — the re-point test — is the discriminator.

## What these logs are NOT

Local supporting evidence. **NOT** Odoo.sh exact-SHA acceptance (DEC-041 D8),
**NOT** live-Shopify validation, **NOT** UAT, and **NOT** an independent review
of the corrected head. Zero live Shopify contact: every test patches the
transport seams and no credential exists in the repository or the environment.
