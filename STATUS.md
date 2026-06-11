# STATUS.md

Updated: 2026-06-11 (session: Phase 2 item 2 + item 3 plan)

## Done this session
- ITEM 2 (AUD-020) FIXED, pending Odoo.sh confirmation. order_sync.py:
  visible currency auto-activation; usable-rate hierarchy (order money-pair
  preferred → company-scoped rate record dated to the order, never
  overwriting existing rates; Odoo rates fallback; error-state binding with
  actionable message otherwise); company mode CONVERTS per decision
  (presentment-side direct when company currency — pair beats Odoo daily
  rate; else dated Odoo-rate conversion); Retry Sync completes SO creation
  via pending-gated branch in _import_one.
- Verification: fail-before 3 failed of 3 → pass-after 0 failed, 0 errors
  of 6 (TestOrderImportCurrency, incl. exact conversion arithmetic,
  pair-vs-daily-rate, retry idempotency, rate scoping). Full suites:
  adams_strict1 0 failed/0 errors of 541; adams_strict_vat 1 failed/0
  errors of 541 (sole failure = known AUD-001). Regression caught during
  verification (retry branch vs webhook write_date invariant) and fixed by
  gating on sync_status='pending' — documented in AUDIT.md.
- FINALIZE.md: items 1-2 pending Odoo.sh confirmation with commands.
- Item 3 (tax workstream) breakdown plan presented to Ahmed — AWAITING
  APPROVAL, no shipped-code edits made for it.

## Next
- Ahmed: relay items 1-2 Odoo.sh confirmations; approve/adjust item 3
  breakdown (steps 3a-3f in chat; decisions: guard blocking vs
  activity-only, guard tolerance, missing tax-flavor handling).
- Then execute item 3 step by step, one per session.

## Open questions for Ahmed
- Item 3 decisions (see plan): guard behavior on mismatch, tolerance,
  and tax-flavor fallback when no matching price-include variant exists.
