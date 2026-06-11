# STATUS.md

Updated: 2026-06-11 (session: Tier 1 — financial correctness audit)

## Done this session
- AUD-002 resolved: TypeError = Odoo test-harness artifact
  (core tests/common.py:341-344 vs client.py:21 tuple timeout); the real
  finding is silent default-journal fallback. Full broad-except sweep of
  financial code: 36 except clauses reviewed against rule 5 →
  AUD-002..AUD-014 ledgered (4 major, 8 minor + 1 reclassified).
- AUD-001 completed: full tax-resolution branch map in AUDIT.md (doubles as
  the VAT-inclusive spec). Verdict for Ahmed: YES, a tax-included company
  produces legally wrong posted invoices today. Three new tax findings:
  AUD-015 (shipping taxed at company default rate — wrong on tax-excluded
  companies too), AUD-016 (default-tax leak on unresolved/empty tax lines +
  log-only drops), AUD-017 (fallback matches wrong tax flavor), AUD-018
  (taxesIncluded never fetched — deferred-by-design spec item).
- Refund/credit-note deep audit: AUD-019 (CRITICAL: credit note created
  without currency_id — foreign-currency refunds misbooked), AUD-020
  (CRITICAL: unresolvable/inactive currency → foreign amounts booked as
  company currency, default Odoo config), AUD-021 (idempotency hole →
  possible duplicate credit notes), AUD-022 (no cumulative over-refund
  guard), AUD-023 (minor edge bundle).
- Regression checklist: 18/18 LEGACY_NOTES fixes present (BUG-R2 evolved,
  verified); 5 covered only implicitly → Tier 4 test backlog.
- Reconciliation reviewed: financial checks write visible sync logs (good);
  digest omits refund bindings from its error census.

## Next
- CHECKPOINT: Ahmed reviews Tier 1 (this is the stop point).
- Severity ranking and Phase 2 recommendation in the checkpoint report.
- Tier 2 leads parked: positional variant matching (product_sync.py:240),
  product/customer webhook swallow check (AUD-005 sibling paths).

## Open questions for Ahmed
- AUD-001: approve "total-check guard" direction for v1 vs full deferral?
- AUD-020: may the connector auto-activate currencies, or error-state only?
