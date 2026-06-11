# AUDIT.md — Findings Ledger

Format per CLAUDE.md: ID, severity (critical/major/minor), file:line evidence,
description, proposed fix (not implemented), status (open/approved/fixed/wontfix).

Entries recorded before Tier 1 begins are marked PRELIMINARY: they came out of
STEP 0 environment runs, carry failing-test or log evidence, and still need the
full source-path walk during Tier 1 before any fix is proposed.

---

## AUD-001 — Tax resolution on imported orders: branch map, and wrong invoices on tax-included companies

- **Severity:** major (financial correctness)
- **Status:** open (verified — Tier 1). This entry doubles as the SPEC for
  the deferred VAT-inclusive work.

### Branch map (verified against source, 2026-06-11)

Inputs fetched from Shopify (`shopify_api/queries/order.py`):
`totalPriceSet` (:23), `subtotalPriceSet` (:27), `totalTaxSet` (:35), line
`taxLines` (:98). NOT fetched: `taxesIncluded` (order level), line
`taxable`, shipping `taxLines` usage — `taxesIncluded` appears nowhere in
the connector (verified by module-wide grep). The importer therefore has no
knowledge of whether Shopify amounts are tax-inclusive.

Per product line (`sync/order_sync.py:611-645`):
1. `price_unit` = Shopify `originalUnitPriceSet` (shop or presentment money
   per `backend.import_currency_mode`) — tax-exclusive by Shopify default,
   tax-INCLUSIVE if the store has taxesIncluded=true (not detected).
2. `_resolve_taxes(taxLines)` (`order_sync.py:647-708`):
   - Branch A — mapping table: `shopify.tax.mapping` matched
     case-insensitively on tax TITLE (`:657-676`). Mapped Odoo tax used
     as-is, including its price_include and amount_type semantics
     (merchant-controlled; correct if the merchant maps consistently).
   - Branch B — rate fallback (`:679-693`): search `account.tax` with
     `type_tax_use='sale'`, `amount` within ±0.005 of the Shopify rate,
     `company_id` — NO filter on `price_include`/`price_include_override`,
     NO filter on `amount_type` (a fixed-amount tax of 10.0 matches a 10%
     lookup), `limit=1` with default ordering. First match wins.
   - Branch C — no match: tax line DROPPED with a server-log warning only
     (`:694-706`) → see AUD-016.
3. If `_resolve_taxes` returns taxes → set explicitly `[(6,0,...)]`. If it
   returns [] (no taxLines, or all dropped) → `tax_ids` key omitted → Odoo
   fills the line with the PRODUCT's default taxes; imported products carry
   the company default sale tax because `product_sync.py` never sets
   `taxes_id` and core defaults it
   (`odoo/addons/account/models/product.py:40-44`, verified) → see AUD-016.

Shipping line (`order_sync.py:710-760`): Shopify shipping `taxLines` are
never resolved (documented known gap in the docstring `:713-733`) — BUT the
docstring's claim that the line ends up with "no taxes" is WRONG on any
company with a default sale tax: the auto-created SHOPIFY-SHIPPING product
inherits the company default sale tax (verified empirically: new service
product on adams_strict_vat gets the 15% generic-chart tax), so shipping is
taxed at an arbitrary default rate instead of Shopify's shipping tax → see
AUD-015.

Company-config behavior matrix (run evidence):
- Tax-EXCLUDED company (adams_strict1): explicit-tax product lines correct;
  shipping over/mis-taxed at default rate (15% on generic chart) →
  invoice amount_total 121.50 for a $120.00 Shopify charge in the regression
  test scenario; the test tolerates it (assertGreaterEqual,
  `tests/test_order_import.py:562-577`).
- Tax-INCLUDED company (adams_strict_vat): rate-fallback resolves a
  price-included 10% tax → the tax-exclusive $50 unit prices are
  reinterpreted as tax-inclusive (net 90.91), shipping $10 gets the
  15%-included default (net 8.70) → amount_untaxed 99.61 vs charged-basis
  110.00. Failing test through the production path:
  `TestOrderImport.test_import_taxed_order_creates_invoice_with_tax_lines`,
  `AssertionError: 99.61 != 110.0` (run 2026-06-10, /tmp/odoo_test_run4.log).
  Arithmetic verified: 100/1.1 + 10/1.15 = 90.91 + 8.70 = 99.61.

### Can a tax-included company produce a LEGALLY wrong invoice today?

**YES.** On a tax-included company, every imported taxed order books an
invoice whose untaxed base and tax amounts are computed on an inclusive
reading of amounts Shopify reported as exclusive: the invoice total
(99.61 + tax) no longer equals what the customer was actually charged
(120.00), and the declared VAT base/amounts are misstated. This is not a
display issue — posted `account.move` records carry the wrong tax lines.
Recommendation: full VAT-inclusive support can stay deferred, but v1 MUST
NOT silently post wrong invoices — minimum viable guard is to detect the
mismatch (company tax-included pricing, or resolved tax with
price_include=True, or |invoice total − Shopify totalPriceSet| > rounding)
and degrade visibly (activity + binding error state) instead of posting.

### Proposed direction (not implemented; needs Ahmed's scoping decision)

1. Guard (v1): post-import total check against Shopify `totalPriceSet`
   with visible degradation on mismatch — catches AUD-001/015/016 symptoms
   generically.
2. Rate fallback: filter `amount_type='percent'` and prefer
   price-exclusive taxes (or taxes matching the store's taxesIncluded
   semantics once fetched) — see AUD-017/AUD-018.
3. Defer: true tax-included import (fetch `taxesIncluded`, map to
   price-included taxes, validate totals) = the deferred VAT-inclusive
   feature; this branch map is its spec.

### Original preliminary entry (superseded, kept for history)

AUD-001 (2026-06-10) — VAT-inclusive company breaks taxed order import totals

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

## AUD-002 — Silent degradation in payment transaction fetch → wrong journal, skipped audit records

- **Severity:** major (payments; rule 5)
- **Status:** open (verified — Tier 1)
- **Evidence:**
  - `sync/payment_status_sync.py:587-592` — `except Exception` around the
    whole transaction-fetch block logs a WARNING and `return None`.
  - Caller `_resolve_payment_journal` (`payment_status_sync.py:498-522`):
    `gateway_name=None` → falls through to the company's first bank journal
    with only an INFO log (`payment_status_sync.py:513-521`), then
    `_register_payment` books the payment there.
  - The try block also creates `shopify.order.transaction` audit records
    (`payment_status_sync.py:564-580`); on failure these are silently
    skipped (and a mid-loop failure leaves them partially written — no
    savepoint around the loop).
- **Description:** ANY failure fetching transactions (network, auth,
  GraphQL error, or a programming error) silently degrades journal
  resolution: the payment is registered against the company's first bank
  journal instead of the gateway-mapped journal, with no merchant-visible
  signal (no activity, no sync log, no chatter). Payment audit records are
  silently missing. Gateway-payout reconciliation then breaks downstream.
- **TypeError root cause (resolved):** the observed
  `'<' not supported between instances of 'tuple' and 'int'` is NOT a
  production bug. Odoo 19's test harness compares request timeouts with
  `timeout < 10` (`/home/user/odoo/odoo/tests/common.py:341-344`) and our
  client passes `REQUEST_TIMEOUT = (10, 30)` — a (connect, read) tuple,
  valid for `requests` in production (`shopify_api/client.py:21,157`).
  Test-environment-only artifact; noted for Tier 4 (the test exercised a
  harness error path, not real transaction-fetch behavior, and
  `TestPaymentStatusSync` never mocks the API client).
- **Proposed fix (not implemented):** narrow the except to expected API
  errors; on failure, schedule the existing manual-review activity (the
  `_schedule_activity` helper) or return a sentinel that makes
  `_register_payment` abort visibly instead of silently using the default
  journal; wrap the audit-record loop in a savepoint. Unexpected exceptions
  should log at ERROR with traceback.

## AUD-003 — Refund import failures counted, then counters discarded by the cron

- **Severity:** major (refunds/credit notes; rule 5)
- **Status:** open (verified — Tier 1)
- **Evidence:**
  - `sync/refund_sync.py:32-35` — refund FETCH failure: WARNING log,
    `return 0, 1, 0`.
  - `sync/refund_sync.py:53-55` — per-refund import failure before the
    binding exists: WARNING log, `errors += 1`.
  - `models/shopify_backend.py:1188-1199` — `_cron_import_refunds` calls
    `syncer.import_refunds()` and DISCARDS the returned
    `(success, errors, skipped)`; `_notify_sync_error` fires only when an
    exception escapes — which the handlers above prevent.
  - RefundSync writes no `shopify.sync.log` records (verified by grep), so
    the daily error digest sees nothing either.
- **Description:** a persistent refund-fetch failure (e.g. revoked token
  scope, API change) means credit notes are never created and the merchant
  is never told — Shopify shows refunds, Odoo books don't, indefinitely.
  Mitigation that DOES work: when the failure happens inside credit-note
  creation, `_import_one_refund` records an error-state binding with
  `sync_error` and an activity (`refund_sync.py:136-148`, `:189-215`) — the
  silent cases are fetch failures and crashes before binding creation.
- **Proposed fix (not implemented):** in `_cron_import_refunds`, pass the
  returned counters to the existing `_notify_sync_error` when errors>0
  (pattern already used for exceptions); consider a sync-log record per
  refund batch for digest coverage.

## AUD-004 — Payout import failures counted, then counters discarded by the cron

- **Severity:** major (payouts feed reconciliation; rule 5)
- **Status:** open (verified — Tier 1)
- **Evidence:** `models/shopify_backend.py:1174-1185` — `_cron_import_payouts`
  discards `import_payouts()` counters identically to AUD-003;
  `sync/payout_sync.py:36` (fetch, `_logger.exception`, error counted),
  `:54` (per-payout, WARNING, counted), `:133` (per-payout transactions
  fetch, WARNING, skipped) — none merchant-visible.
- **Description:** silent payout gaps make the payout screen and any
  payout-based reconciliation silently incomplete.
- **Proposed fix (not implemented):** same as AUD-003 — surface non-zero
  error counters through `_notify_sync_error` / sync log.

## AUD-005 — Order webhook import failure marked 'done'; dead-letter machinery bypassed

- **Severity:** major (orders/invoices; data integrity + rule 5)
- **Status:** open (verified — Tier 1)
- **Evidence:**
  - `sync/order_sync.py:932-933` — `import_single_order` ends with
    `except Exception: _logger.exception(...)` and swallows.
  - `models/shopify_webhook_log.py:104-144` — `_cron_process_pending` has a
    correct retry → `error` → `dead_letter` state machine driven by
    exceptions from `_process_event()`… which it never receives for order
    webhooks, because of the swallow above. The log is then written
    `state='done'` (`shopify_webhook_log.py:118-122`).
  - Call chain verified: `_handle_order_webhook`
    (`shopify_webhook_log.py:263`) → `shopify.order.binding
    .process_webhook_event` (`models/shopify_order_binding.py:79-82`) →
    `import_single_order`.
- **Description:** an orders/create webhook whose import crashes is recorded
  as successfully processed; no retry, no dead-letter, no error message.
  The order silently never reaches Odoo until a later bulk import happens to
  pick it up (and AUD-003-style silence applies if it doesn't).
- **Proposed fix (not implemented):** let the exception propagate from
  `import_single_order` (log, then re-raise) so the webhook state machine
  does its job. Check product/customer `process_webhook_event` paths for the
  same pattern in Tier 2.

## AUD-006 — Reverse-sync failures (orderMarkAsPaid / refundCreate) are log-only

- **Severity:** major (cross-system financial divergence; rule 5)
- **Status:** open (verified — Tier 1)
- **Evidence:** `models/account_move.py:76-80` (mark-as-paid mutation
  failure: WARNING, no activity) and `:151-155` (Shopify refundCreate
  failure after credit note posted: WARNING, no activity). Contrast with
  `button_cancel` in the same file, which schedules a proper warning
  activity (`account_move.py:176-191`).
- **Description:** with reverse sync enabled, a merchant posting an invoice
  or credit note expects Shopify to follow. On failure, Odoo and Shopify
  silently diverge (credit note exists, Shopify refund doesn't — money
  story differs between systems).
- **Proposed fix (not implemented):** mirror the `button_cancel` pattern —
  schedule a warning activity on the sale order naming the Shopify order
  and the failed mutation.

## AUD-007 — Payment/invoice reconciliation failure is log-only

- **Severity:** minor (payment exists and is visible; linkage missing)
- **Status:** open (verified — Tier 1)
- **Evidence:** `sync/payment_status_sync.py:476-481` — reconcile failure:
  WARNING "manual reconciliation required", no activity.
- **Proposed fix (not implemented):** schedule the existing activity helper
  so "manual reconciliation required" actually reaches a human.

## AUD-008 — Voided-payment transition: cancel failures partially invisible

- **Severity:** minor
- **Status:** open (verified — Tier 1)
- **Evidence:** `sync/payment_status_sync.py:305-308` (draft-invoice cancel
  failure: WARNING only, flow continues and returns True → binding advances
  to voided with a live draft invoice) and `:327-328` (SO cancel failure in
  draft/sent: WARNING only). The `state == 'sale'` branch DOES schedule an
  activity (`:336-342`) — inconsistent.
- **Proposed fix (not implemented):** schedule the activity in both silent
  branches; consider not returning True when the draft invoice could not be
  cancelled.

## AUD-009 — `shopify.payout.journal_entry_id` is a dead field

- **Severity:** minor (feature stub visible in model; merchant-facing
  promise unfulfilled)
- **Status:** open (verified — Tier 1)
- **Evidence:** `models/shopify_payout.py:35-37` defines the field
  ("Accounting journal entry created for this payout"); module-wide grep
  shows no writer and no `action_*` method on the model populates it.
- **Proposed fix (not implemented):** Tier 6 decides — either hide the
  field/help text or ship the journal-entry feature in v1.1 (ROADMAP).

## AUD-010 — Shopify-cancelled order: Odoo cancel failure is log-only

- **Severity:** major (merchant can ship a cancelled order)
- **Status:** open (verified — Tier 1)
- **Evidence:** `sync/order_sync.py:233-241` — when an imported order is
  cancelled on Shopify, `action_cancel()` failure (e.g. done pickings) is
  WARNING-logged and the import returns the order with no activity. (The
  webhook path for orders/cancelled DOES handle this visibly per its
  docstring — `models/shopify_webhook_log.py:269+`, BUG-C1 fix; the bulk
  import path at order_sync.py lacks the same treatment.)
- **Proposed fix (not implemented):** schedule the same warning activity as
  the webhook cancel path when auto-cancel fails during import.

## AUD-011 — Payment transition during bulk import: unexpected raise is silent

- **Severity:** minor (known failures inside the handler are visible;
  only unexpected raises are swallowed)
- **Status:** open (verified — Tier 1)
- **Evidence:** `sync/order_sync.py:92-102` — `handle_status_change` wrapped
  in `except Exception` → WARNING only. Transient errors self-heal on the
  next status change; persistent programming errors repeat silently.
- **Proposed fix (not implemented):** log at ERROR with traceback
  (`_logger.exception`) at minimum; consider activity on repeated failure.

## AUD-012 — `_auto_register_payment` outer guard swallows unexpected raises

- **Severity:** minor (inner `_register_payment` failure paths schedule
  activities; outer guard catches only unexpected errors — silently)
- **Status:** open (verified — Tier 1)
- **Evidence:** `sync/order_sync.py:330-344`.
- **Proposed fix (not implemented):** `_logger.exception` + activity, since
  a swallowed unexpected error here means a captured payment was never
  registered.

## AUD-013 — The visibility mechanism itself can fail silently

- **Severity:** minor
- **Status:** open (verified — Tier 1)
- **Evidence:** `sync/payment_status_sync.py:594-603` —
  `_schedule_activity` wraps `activity_schedule` in `except Exception` →
  WARNING. Every "visible degradation" in this file depends on it.
- **Proposed fix (not implemented):** keep the guard (an activity failure
  must not roll back a payment) but log at ERROR with traceback so support
  can detect it.

## AUD-014 — Unknown payment transitions advance status with no accounting action

- **Severity:** minor (pending verification of which combos occur in practice)
- **Status:** open (verified code path — Tier 1; needs Shopify-status-matrix
  check)
- **Evidence:** `sync/payment_status_sync.py:86-92` — transitions not in
  `TRANSITION_MAP` (e.g. `partially_paid → voided`,
  `partially_paid → refunded`) log a WARNING and update the status anyway,
  returning True. Refund-type transitions are independently covered by
  RefundSync; void-type ones are not.
- **Proposed fix (not implemented):** decide per missing combo: map it, or
  schedule a manual-review activity instead of silently advancing.


## AUD-015 — Shipping line is taxed at the company default rate, not Shopify's shipping tax

- **Severity:** major (wrong invoice totals TODAY on tax-excluded companies
  too; in-code documentation of the gap is factually wrong)
- **Status:** open (verified — Tier 1)
- **Evidence:** `sync/order_sync.py:710-760` — `_create_shipping_line`
  never resolves shipping `taxLines` (docstring `:713-733` documents this
  as "the SO line and invoice line have no taxes"). In reality the
  auto-created SHOPIFY-SHIPPING product inherits the company default sale
  tax (`odoo/addons/account/models/product.py:40-44`; empirically verified
  on adams_strict_vat: new service product carries the 15% generic-chart
  tax), so every imported shipping line is taxed at the company default
  rate regardless of what Shopify charged. Run evidence: regression test
  invoice shows 110.00 untaxed + 11.50 tax (10 product + 1.50 shipping@15%)
  for a Shopify order that charged 10.00 tax total; the test tolerates it
  (`tests/test_order_import.py:562-577` uses assertGreaterEqual).
- **Description:** stale deferral note understates the defect: instead of
  under-taxing shipping (the documented gap), the connector mis-taxes it at
  an arbitrary default rate — invoice total ≠ amount charged whenever the
  default differs from Shopify's shipping tax (including the common
  shipping-tax-free US case, which gets over-taxed). Cross-check
  KNOWN_LIMITATIONS.md wording in Tier 6.
- **Proposed fix (not implemented):** resolve shipping `taxLines` via
  `_resolve_taxes()` exactly like product lines (the docstring itself
  proposes this), and create the SHOPIFY-SHIPPING product with explicit
  `taxes_id=[]` so nothing leaks in when Shopify charges no shipping tax.

## AUD-016 — Lines without resolvable Shopify taxes inherit default taxes; dropped tax lines are log-only

- **Severity:** major (tax-exempt orders get taxed; dropped tax lines
  silently under-tax — both invisible to the merchant)
- **Status:** open (verified — Tier 1)
- **Evidence:** `sync/order_sync.py:640-644` — `tax_ids` key omitted when
  `_resolve_taxes` returns []; the SO line then computes the product's
  default taxes (company default sale tax, see AUD-015 evidence).
  `order_sync.py:694-706` — unmapped/unmatched tax lines are dropped with
  `_logger.warning` only (BUG-O1's fix made resolution smarter but the
  terminal drop branch remains log-only).
- **Description:** two silent wrong-invoice cases: (a) a genuinely tax-free
  Shopify order (exempt customer, no-nexus US sale) imports with the
  company default tax applied — over-charged invoice; (b) a taxed Shopify
  order whose title/rate matches nothing drops the tax — under-charged
  invoice; the merchant learns from neither (server log only).
- **Proposed fix (not implemented):** when Shopify reports zero tax for a
  line, set `tax_ids = [(5,)]` (explicitly no taxes) instead of omitting
  the key; when a tax line is dropped, degrade visibly (activity or order
  binding error state), consistent with rule 5. The AUD-001 total-check
  guard would catch both as a backstop.

## AUD-017 — Rate-fallback tax search can match the wrong tax flavor

- **Severity:** minor
- **Status:** open (verified — Tier 1)
- **Evidence:** `sync/order_sync.py:684-689` — fallback search filters only
  `type_tax_use`, `amount` ±0.005, `company_id`: no `amount_type` filter
  (an `amount_type='fixed'` tax of 10.0 currency units matches a 10% rate
  lookup), no price-include filter (root of AUD-001), `limit=1` relying on
  default ordering when several same-rate taxes exist (e.g. included +
  excluded variants of the same VAT rate).
- **Proposed fix (not implemented):** add `('amount_type','=','percent')`,
  prefer price-exclusive (until AUD-018 lands), and make ordering
  deterministic.

## AUD-018 — Shopify `taxesIncluded` flag is never fetched or honored (spec item)

- **Severity:** major as a correctness root cause; remediation deferred by
  design (this is the VAT-inclusive feature)
- **Status:** open — deferred-by-design pending Ahmed's v1/v1.1 scoping
- **Evidence:** module-wide grep: `taxesIncluded` absent from all queries
  and sync code; `shopify_api/queries/order.py` fetches price sets and
  `taxLines` only.
- **Description:** Shopify stores configured with tax-inclusive pricing
  (common in EU/UK/AU) send line prices that INCLUDE tax with
  `taxesIncluded=true`. The importer reads prices as exclusive and maps
  onto whatever price_include semantics the resolved Odoo tax has — wrong
  in three of the four store×company combinations. The AUD-001 branch map
  is the implementation spec; the AUD-001 guard is the v1 stopgap.

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
