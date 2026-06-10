# STATUS.md

Updated: 2026-06-10 (session: STEP -1 reset + STEP 0 environment)

## Done this session
- STEP -1: deleted 26 AI orchestration/instruction artifacts (approved kill
  list); salvaged bug ledger, deferred features, known limitations, and the
  mandatory accounting test recipe into LEGACY_NOTES.md; wrote the new
  governing CLAUDE.md. Commit be0568b on claude/admiring-bell-e9g6qp.
- STEP 0: SSH to Odoo.sh impossible (port 22 blocked) → hybrid runtime
  approved and built: local Odoo 19 Community (commit 07a333c8) + PG16.
  Test command + dependency quirks recorded in CLAUDE.md Environment.
- Baseline runs (literal counts): adams_strict1 (chart applied, upgraded
  path): 0 failed, 0 errors of 532 tests (connector 280 + simulator 241
  at_install, 11 post-install). adams_test_fresh (chartless): 0 failed,
  4 errors of 532 (ENV-1, test-setup gap). adams_strict_vat (tax-included
  pricing + EUR): 1 failed, 0 errors of 532 → AUD-001.
- AUDIT.md opened with: AUD-001 (major, VAT-inclusive order import totals
  wrong, failing production-path test attached), AUD-002 (lead: swallowed
  TypeError in payment transaction fetch, payment_status_sync.py:587-592),
  ENV-1 (test-infra: account.tax without tax_group_id, 3 files).

## Next
- CHECKPOINT: Ahmed reviews STEP 0 results, then Tier 1 begins (financial
  correctness, line-by-line: payments, refunds, taxes, reconciliation).
- Tier 1 must resolve AUD-001 root path and AUD-002 TypeError site.
- Tier 4 backlog seeded: fix ENV-1 test setups (tax_group_id-safe).

## Open questions for Ahmed
- None blocking; Odoo.sh confirmation pass channel to be exercised when the
  first Phase 2 fix lands (per hybrid runtime rule).
