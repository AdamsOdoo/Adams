# FINALIZE.md — v1 Finalization Backlog

Created 2026-06-11 at the Tier 1 checkpoint (Phase 2 granted by Ahmed).
Rules: one item per session; plan first, Ahmed approves before any shipped-
code edit; fail-before/pass-after on the relevant strict profile + a
no-regression run on adams_strict1; every fix stays **pending Odoo.sh
confirmation** until Ahmed relays the confirmation run. Minors ride along
only when they touch the same file and keep the diff small.

## Standing decisions (Ahmed, 2026-06-11)

- SCOPE: full VAT-inclusive support is IN v1 (see CLAUDE.md Mission).
- GUARD: the total-check guard (computed invoice totals vs Shopify
  `totalPriceSet`, visible degradation on mismatch) is PERMANENT product
  behavior — it remains after full VAT-inclusive support lands. It is the
  rule-5 net for all future tax bugs.
- CURRENCY POLICY (AUD-020): auto-activating currencies is allowed, done
  VISIBLY (log + existing notify/activity pattern). Hard condition: never
  post a financial document without a usable exchange rate. Rate
  preference: (1) rate derivable from the order's own Shopify money fields,
  (2) Odoo rates, (3) neither usable → error-state the order with an
  actionable merchant message. Never book foreign amounts as company
  currency.

## Phase 2 fix sequence (granted)

| # | Item | Findings | Size | Status | Odoo.sh |
|---|------|----------|------|--------|---------|
| 1 | Credit note currency_id | AUD-019 | S | FIXED locally (fail-before 1/1 → pass-after 0/0 of 3; strict1 full 0/0 of 535; strict_vat full 1/0 of 535, sole failure = known AUD-001) | **pending Odoo.sh confirmation** |
| 2 | Order-currency handling per currency policy | AUD-020 | M | FIXED locally (fail-before 3/3 → pass-after 0/0 of 6 + retry/conversion tests; strict1 full 0/0 of 541; strict_vat full 1/0 of 541, sole failure = known AUD-001) | **pending Odoo.sh confirmation** |

Item 2 Odoo.sh confirmation command (Ahmed relays, expect "0 failed, 0
error(s) of 6 tests"):

```
odoo-bin -d <staging-db> --addons-path=<core-addons>,<repo>/addons \
  -u shopify_connector_pro \
  --test-tags /shopify_connector_pro:TestOrderImportCurrency \
  --stop-after-init --no-http
```

Item 2 implementation notes: company mode CONVERTS (decision 2026-06-11) —
presentment side taken directly when it is the company currency (order-pair
rate wins over Odoo daily rates), Odoo-rate conversion dated to the order
otherwise, error-state when neither. Foreign-booking modes auto-activate
currencies visibly and create company-scoped, order-dated res.currency.rate
records from the money pair only when no rate exists for that date (existing
merchant rates are never overwritten). Retryability: `_import_one` completes
SO creation for bindings reset to 'pending' by Retry Sync; non-pending
no-order bindings keep the status-update path (refund-window invariant).

Item 1 Odoo.sh confirmation command (Ahmed relays, expect "0 failed, 0
error(s) of 3 tests"):

```
odoo-bin -d <staging-db> --addons-path=<core-addons>,<repo>/addons \
  -u shopify_connector_pro \
  --test-tags /shopify_connector_pro:TestRefundCreditNoteMultiCurrency \
  --stop-after-init --no-http
```
| 3 | Tax workstream — steps 3a-3f approved 2026-06-11; 3a (total-check guard) implemented, awaiting go on consequence statement (touchpoint 2) | AUD-001, AUD-015, AUD-016, AUD-018 + permanent guard; AUD-017 rides along | L (split: 3a M done, 3b S, 3c S, 3d S, 3e L, 3f S) | 3a: verified locally | 3a: pending go + Odoo.sh |
| 4 | Visibility batch (surface discarded counters, webhook dead-letter, reverse-sync activities) | AUD-003, AUD-004, AUD-005, AUD-006 (minors AUD-007/008/011/012/013 ride along where same-file) | M | not started | pending |
| 5 | Refund idempotency + over-refund guard | AUD-021, AUD-022 (AUD-023 rides along) | M | not started | pending |

After item 5: pause fixes, resume audit at Tier 2. Tier 2-3 findings that
touch already-fixed files are ledgered as NEW findings — no opportunistic
edits outside the granted item.

## Verification matrix per item

- Fail-before: failing test through the production path, committed before
  the fix (test code is always writable).
- Pass-after: same test green; plus full suite literal counts on
  adams_strict1 (no regression) and adams_strict_vat (now tax-included +
  multi-currency with explicit EUR rate 0.92 — see CLAUDE.md profile 3).
- Odoo.sh: confirmation command relayed by Ahmed; item stays "pending
  Odoo.sh confirmation" here until reported green.

## Not yet scheduled (await later tiers)

- Tier 4 test backlog: explicit regression tests for BUG-C1, EW-14a,
  EW-01a, EW-02a, EW-04a; multi-currency refund e2e; mocked-client
  TestPaymentStatusSync (AUD-002 harness note); ENV-1 chartless test setup.
- AUD-009 (dead payout journal_entry_id field), AUD-010, AUD-014 and other
  minors not riding along — re-prioritized at the Tier 4/6 checkpoints.

## Item 3a evidence trail (total-check guard, DEC-011/012)

- Fail-before: 1 failed, 4 errors of 6 — test_total_guard.py on
  adams_strict1 before implementation (FAIL = production path posted a
  mismatched invoice silently; errors = stamp field absent).
- Pass-after: 0 failed, 0 errors of 26 (TestTotalGuardPaymentPath,
  TestTotalGuardAutoInvoice, TestOrderImport, TestPaymentStatusSync).
- Full suites: adams_strict1 0 failed, 0 errors of 547. adams_strict_vat
  2 failed, 0 errors of 547 — NEW BASELINE: both failures are
  AUD-001-rooted and now represent the guard VISIBLY blocking wrong
  invoices that previously posted silently on tax-included companies
  (test_import_taxed_order... exact-totals marker; TestTaxedRefundE2E
  needs a posted invoice). Both clear at 3e.
- Guard exposed and fixed two inconsistent test fixtures (test_order_import
  totalPriceSet 29.99 vs 59.98 lines; e2e fixture's untaxed shipping vs
  default-taxed shipping product) — both were masking AUD-015/016 symptoms.
- Upgraded-DB safety: zero/absent stamp ⇒ guard skips (tested).

Item 3a Odoo.sh confirmation (batched below).

## Batched Odoo.sh confirmation commands (touchpoint 1)

Run all three on the staging build; paste the three result lines.

```
odoo-bin -d <staging-db> --addons-path=<core-addons>,<repo>/addons -u shopify_connector_pro --test-tags /shopify_connector_pro:TestRefundCreditNoteMultiCurrency --stop-after-init --no-http
odoo-bin -d <staging-db> --addons-path=<core-addons>,<repo>/addons -u shopify_connector_pro --test-tags /shopify_connector_pro:TestOrderImportCurrency --stop-after-init --no-http
odoo-bin -d <staging-db> --addons-path=<core-addons>,<repo>/addons -u shopify_connector_pro --test-tags /shopify_connector_pro:TestTotalGuardPaymentPath,/shopify_connector_pro:TestTotalGuardAutoInvoice --stop-after-init --no-http
```

Expected: 0 failed, 0 errors of 3 / of 6 / of 6 respectively.
