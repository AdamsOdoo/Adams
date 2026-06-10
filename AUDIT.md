# AUDIT.md — Findings Ledger

Format per CLAUDE.md: ID, severity (critical/major/minor), file:line evidence,
description, proposed fix (not implemented), status (open/approved/fixed/wontfix).

Entries recorded before Tier 1 begins are marked PRELIMINARY: they came out of
STEP 0 environment runs, carry failing-test or log evidence, and still need the
full source-path walk during Tier 1 before any fix is proposed.

---

## AUD-001 — VAT-inclusive company breaks taxed order import totals

- **Severity:** major (financial correctness; falls inside the known-deferred
  VAT-inclusive area, but it breaks TODAY on any company configured
  tax-included — flagged per the "anything that would break before staging"
  rule)
- **Status:** open (PRELIMINARY — Tier 1 to map the exact tax-resolution path)
- **Evidence:**
  - Failing test through the production import path:
    `TestOrderImport.test_import_taxed_order_creates_invoice_with_tax_lines`
    (`addons/shopify_connector_pro/tests/test_order_import.py:568`)
    on DB profile `adams_strict_vat` (company
    `account_price_include = 'tax_included'`, generic_coa chart, EUR active):
    `AssertionError: 99.61 != 110.0 within 2 places (10.39 difference) :
    Untaxed total: $100 product + $10 shipping = $110`
    (log: /tmp/odoo_test_run4.log, 2026-06-10 18:11:13)
  - Same test passes on `adams_strict1` (identical DB, default tax-excluded
    pricing): 0 failed, 0 errors of 532.
- **Description:** Shopify order amounts (line prices, `taxLines`) are
  tax-exclusive in this scenario, but when the company default is
  tax-included, the tax resolved/auto-applied on imported invoice lines is
  price-included, so Odoo reinterprets the unit prices as VAT-inclusive and
  computes a wrong untaxed base (99.61 vs 110.00). Hypothesis (unverified):
  the rate-based fallback tax resolution (BUG-O1 fix) matches on `amount`
  without constraining price-include semantics, and/or shipping-line default
  taxes follow the company default.
- **Proposed fix:** none yet — Tier 1 must first map every tax-resolution
  branch (mapping table, rate fallback, shipping defaults) before a fix is
  proposed. Do not redesign the deferred VAT-inclusive feature; scope is
  "imports must not be silently wrong on tax-included companies."

## AUD-002 — Swallowed TypeError in payment transaction fetch (visibility lead)

- **Severity:** unclassified lead (payments / Tier 1)
- **Status:** open (PRELIMINARY)
- **Evidence:** during the (passing) test
  `TestPaymentStatusSync.test_authorized_to_paid_posts_draft_invoice` on
  `adams_strict_vat`, production code logged:
  `WARNING ... Could not fetch transactions for order #1001: '<' not
  supported between instances of 'tuple' and 'int'` — emitted by the broad
  handler at
  `addons/shopify_connector_pro/sync/payment_status_sync.py:587-592`
  (`except Exception` → `_logger.warning` → `return None`), after which the
  code proceeded with `No gateway mapping for 'unknown' — using default bank
  journal Bank`.
- **Description:** the `except Exception` around transaction fetching hides a
  programming error (a tuple-vs-int comparison somewhere in the try block or
  the client beneath it). Consequences when it fires: `shopify.order.transaction`
  audit records are silently not created and gateway→journal mapping degrades
  to the default journal with only a server-log warning — invisible to a
  merchant. Tier 1 must (a) locate the actual TypeError site, (b) decide
  whether this degradation is "visible enough" under discipline rule 5, and
  (c) check whether payments can land in the wrong journal silently.
- **Proposed fix:** none yet.

---

## Environment-sensitivity notes (not defects in shipped code)

- **ENV-1 (test infrastructure, Tier 4 backlog):** three test setups create
  `account.tax` without `tax_group_id` and crash with a NOT NULL violation on
  any DB without a chart of accounts:
  `tests/test_core_workflow_hardening.py:713`,
  `tests/test_order_import.py:406` (connector),
  `tests/test_refund_fidelity.py:222` (simulator).
  4 tests error on the chartless fresh profile; all pass once `generic_coa`
  is applied. Test-code fix (always-writable) deferred to Tier 4 to keep this
  session single-purpose.
