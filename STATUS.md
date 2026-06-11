# STATUS.md

Updated: 2026-06-11 (session: governance change + item 3a)

## Done this session
- Governance: CLAUDE.md updated to standing-approval/self-verification
  model with three human touchpoints; M1-M3 milestones recorded. DEC-011
  (guard blocks posting), DEC-012 (tolerance = 2 × currency rounding),
  DEC-013 (no auto-created taxes; degrade to mapping instruction) in
  docs/architecture/DECISIONS.md. Committed.
- ITEM 3a (total-check guard) IMPLEMENTED + verified locally; UNCOMMITTED,
  awaiting Ahmed's go on the touchpoint-2 consequence statement.
  - shopify_order_binding.shopify_total_amount stamp (import + retry paths)
  - check_total_against_shopify + mismatch activity (accounting.py)
  - guard wired before all 4 auto-posting branches (order_sync auto-invoice;
    payment_status_sync paid×2 + partially_paid)
  - Evidence trail in FINALIZE.md (fail-before 1f/4e of 6; impacted classes
    0/0 of 26; strict1 full 0/0 of 547; strict_vat 2/0 of 547 = new
    baseline, both failures AUD-001-rooted and now VISIBLY blocked instead
    of silently wrong — clear at 3e).
- Batched Odoo.sh confirmations for items 1, 2, 3a in FINALIZE.md.
- SSH enablement instructions sent to Ahmed (eliminates touchpoint 1).

## Next
- On Ahmed's go: commit+push 3a, then 3b (explicit zero-tax lines), 3c
  (shipping tax), 3d (fallback flavor + dropped-tax visibility), 3e
  (taxesIncluded/VAT-inclusive core — clears the 2 strict_vat baseline
  failures), 3f (docs sweep). Touchpoint-2 statement before each commit.
- Then items 4-5, then Tier 2 audit resume.

## Open questions for Ahmed
- Go/no-go on 3a consequence statement (in chat).
- Odoo.sh batch results when convenient.
