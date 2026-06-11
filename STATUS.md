# STATUS.md

Updated: 2026-06-11 (session: Phase 2 items 1-2)

## Done this session
- Scope decision recorded: VAT-inclusive support IN v1 (CLAUDE.md updated);
  FINALIZE.md created with granted Phase 2 sequence + standing decisions
  (permanent total-check guard; currency policy).
- Strict profile 3 extended: explicit EUR rate 0.92 → tax-included AND
  multi-currency hold simultaneously on adams_strict_vat.
- ITEM 1 (AUD-019) FIXED, pending Odoo.sh confirmation:
  refund_sync.py — credit note carries invoice currency (order currency
  fallback) + visible mismatch guard. Fail-before: 1 failed of 1.
  Pass-after: 0 failed, 0 errors of 3 (TestRefundCreditNoteMultiCurrency).
  Full suites: adams_strict1 0 failed/0 errors of 535; adams_strict_vat
  1 failed/0 errors of 535 (sole failure = known AUD-001 taxed-order test).
  Confirmation command in FINALIZE.md.
- ITEM 2 (AUD-020) fail-before committed: 3 failed, 0 errors of 3
  (TestOrderImportCurrency on adams_strict1) — EUR not auto-activated,
  orders created in company currency despite unresolvable currency/no rate.
  Plan presented to Ahmed; AWAITING APPROVAL before editing shipped code.
- New scope note for item 2: import_currency_mode='company' (the DEFAULT)
  books shopMoney amounts with no conversion — only correct when shop
  currency equals company currency; folded into the item 2 plan as a
  decision point.

## Next
- Ahmed: approve/adjust item 2 plan (see chat + FINALIZE.md), relay item 1
  Odoo.sh confirmation.
- Then items 3 (tax workstream breakdown proposal), 4, 5 per FINALIZE.md.

## Open questions for Ahmed
- Item 2, 'company' mode: validate-at-setup (refuse foreign shop currency)
  or convert amounts to company currency using the usable rate? Plan
  recommends convert-with-rate (policy-consistent), validate as fallback.
