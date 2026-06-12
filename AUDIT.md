# AUDIT.md — Findings Ledger

Format per CLAUDE.md: ID, severity (critical/major/minor), file:line evidence,
description, proposed fix (not implemented), status (open/approved/fixed/wontfix).

Entries recorded before Tier 1 begins are marked PRELIMINARY: they came out of
STEP 0 environment runs, carry failing-test or log evidence, and still need the
full source-path walk during Tier 1 before any fix is proposed.

## Status updates — 2026-06-11 (Tier 1 checkpoint approved; Phase 2 granted)

Statuses below OVERRIDE the per-entry status lines (sequence in FINALIZE.md):

- **fixed (pending Odoo.sh confirmation):** AUD-019 — fix applied 2026-06-11
  (refund_sync.py: cn_currency from posted invoice/order + mismatch guard +
  currency_id on create). Fail-before 1 failed of 1; pass-after 0/0 of 3
  (TestRefundCreditNoteMultiCurrency, adams_strict_vat); no regression:
  0/0 of 535 (adams_strict1 full), 1/0 of 535 (adams_strict_vat full, sole
  failure = known AUD-001).
- **fixed (pending Odoo.sh confirmation):** AUD-020 — fix applied 2026-06-11
  (order_sync.py: visible currency auto-activation, usable-rate hierarchy
  with company-scoped order-dated pair rates, company-mode conversion,
  error-state binding + pending-gated retry path). Fail-before 3 failed of
  3; pass-after 0/0 of 6 (TestOrderImportCurrency) + retry-idempotency and
  pair-vs-daily-rate conversion tests; full suites strict1 0/0 of 541,
  strict_vat 1/0 of 541 (sole failure = known AUD-001). One regression
  caught and corrected during verification: the retry branch initially
  hijacked 'synced' bindings without odoo_id, breaking the webhook
  write_date invariant (test_refund_scan_pruning) — now gated on
  sync_status='pending'.
- **approved:** AUD-001, AUD-015, AUD-016,
  AUD-018 (item 3 — VAT-inclusive support now IN v1 scope, total-check guard
  permanent); AUD-003, AUD-004, AUD-005, AUD-006 (item 4); AUD-021, AUD-022
  (item 5).
- **approved as ride-along (same-file, small-diff only):** AUD-017 (item 3),
  AUD-007/008/011/012/013 (item 4), AUD-023 (item 5).
- **fixed (PENDING RETROACTIVE GO + Odoo.sh confirmation), 2026-06-12
  overnight window:** AUD-017 (item 3d — amount_type='percent' filter on
  the rate fallback; deterministic-ordering sub-item verified moot: core
  account.tax _order='sequence,id') and the AUD-016 remainder (dropped
  tax lines now schedule one deduplicated warning activity per order).
  Evidence in FINALIZE.md item 3d trail; consequence statement in
  MORNING_REVIEW.md §1.
- **fixed (PENDING RETROACTIVE GO + Odoo.sh confirmation), 2026-06-12
  overnight window:** AUD-021, AUD-022 and rider AUD-023 (item 5 —
  per-refund savepoint atomicity, shopify_refund_gid recovery guard on
  account.move, cumulative over-refund guard with visible degradation
  and retryable error binding; non-product drop logged, shipping refund
  account via get_product_accounts). Evidence in FINALIZE.md item 5
  trail; consequence statement in MORNING_REVIEW.md §1.
- **fixed (PENDING RETROACTIVE GO + Odoo.sh confirmation), 2026-06-12
  overnight window:** AUD-003, AUD-004, AUD-005, AUD-006 and ride-along
  minors AUD-007, AUD-008, AUD-011, AUD-012, AUD-013 (item 4 —
  visibility batch: cron counters surfaced via _notify_sync_error,
  webhook re-raise into the retry/dead-letter machine, reverse-sync
  failure activities, reconcile/cancel-failure activities, ERROR+
  traceback on unexpected raises incl. the activity helper itself).
  Evidence in FINALIZE.md item 4 trail; consequence statement in
  MORNING_REVIEW.md §1. AUD-008 note: the binding still advances to
  voided when the draft-invoice cancel fails — now WITH a visible
  activity; "do not return True" was considered and rejected as a
  behavior change beyond the approved visibility scope.
- **fixed (PENDING RETROACTIVE GO + Odoo.sh confirmation), 2026-06-12
  overnight window:** AUD-018 and AUD-001 (item 3e — taxesIncluded
  fetched and honored: flavor-preferring rate fallback + price/flavor
  alignment on product and shipping lines; simulator emits the flag).
  Both strict profiles fully green: strict1 0/0 of 562, strict_vat 0/0
  of 562 (standing AUD-001 pair cleared). Evidence in FINALIZE.md item
  3e trail; consequence statement in MORNING_REVIEW.md §1. With 3b+3c+
  3d+3e, AUD-015 and AUD-016 are also fully closed (same gating).
- **GREEN BUILD ledger (2026-06-11, local proxy):** class (c) noise, listed
  once per method step 2: docutils "(ERROR/3) Unexpected indentation" +
  "(WARNING/2) Block quote ends without a blank line" during install =
  CORE `mail` manifest description RST (proven by rendering every
  installed module's description; ours are clean). Container-only
  "Running as user 'root'" notice. Zero (a)-class lines on fresh-install
  AND upgrade logs of all 4 modules at warn level.
- **open (re-prioritized at later checkpoints):** AUD-009, AUD-010, AUD-014,
  ENV-1.

---

## Tier 2 (data integrity & security) — opened 2026-06-12 overnight

Method: fresh-context subagent fan-out scan + my source verification of
every reported candidate (rule 1). Surfaces verified CLEAN by the scan
and spot-checked: timing-safe HMAC (controllers/webhook.py:226), shop-
domain check, HMAC-before-rate-limit ordering, 10MB payload cap,
parameterized SQL only (customer_sync.py:136, inventory_sync.py:36),
record rules with backend scoping, admin-only token fields, Fernet+
PBKDF2 credential crypto, advisory-lock dedup in customer/inventory
sync. Tier 1 deferred lead (positional variant matching,
product_sync.py:240) remains open for this tier — not yet re-verified.

## AUD-024 — Webhook dedup is global, not per backend

- **Severity:** major (silent inbound-event loss in multi-backend setups)
- **Status:** fixed (PENDING RETROACTIVE GO + Odoo.sh confirmation), 2026-06-12
- **Evidence:** models/shopify_webhook_log.py:48-51 — `UNIQUE(webhook_id)`
  without backend_id; controllers/webhook.py:142-146 — dedup search
  `[('webhook_id','=',webhook_id)]` unscoped (every other dedup in the
  module is backend-scoped, incl. the fingerprint fallback right below).
- **Description:** when one Shopify shop feeds two backends (e.g. two
  companies in one DB), the second backend's delivery of the same
  webhook id is silently dropped: constraint rejects the log, controller
  answers 200 'ok'. Cross-shop UUID collision is negligible; the
  same-shop-two-backends case is real.
- **Fix:** constraint → UNIQUE(backend_id, webhook_id); controller
  search scoped by backend_id. Fail-before 1 error of 2 (constraint
  violation through the model), pass-after 0/0 of 2
  (test_tier2_webhook_integrity.py, adams_strict1; commit 5bdfc40).

## AUD-025 — GDPR customers/redact leaves PII on child contacts and parent city/zip

- **Severity:** major (GDPR compliance)
- **Status:** fixed (PENDING RETROACTIVE GO + Odoo.sh confirmation), 2026-06-12
- **Evidence:** models/shopify_webhook_log.py:444-453 — redaction wrote
  only parent name/email/phone/street/street2; order import creates
  delivery/invoice CHILD partners carrying the customer's address+phone
  (order_sync.py `_get_or_create_address`, used for shippingAddress /
  billingAddress), and parent city/zip stayed readable.
- **Fix:** parent write extended with city/zip; all partner.child_ids
  redacted (name → "Redacted Contact #id", email/phone/street/street2/
  city/zip cleared). Fail-before 1 failed of 2 → pass-after 0/0 of 2
  (test_tier2_webhook_integrity.py, adams_strict1).

## AUD-026 — Webhook payload retention: plaintext PII surface (decision item)

- **Severity:** minor (deliberate design with mitigations; flagged as a
  data-exposure surface)
- **Status:** open — decision for Ahmed (Tier 6 / hardening pass)
- **Evidence:** controllers/webhook.py:185 stores full payload JSON;
  models/shopify_webhook_log.py:32 restricts the field to
  group_shopify_user (not admin); 90-day cleanup exists
  (shopify_webhook_log.py:89-100).
- **Description:** payloads are needed for the retry/dead-letter machine
  (AUD-005), so they cannot simply be dropped; but they contain customer
  PII readable by every connector user and live in DB backups for up to
  90 days. Options, cheapest first: (a) tighten field group to
  group_shopify_admin; (b) shorten retention for state='done' logs
  (payload no longer needed once processed); (c) encrypt at rest via
  shopify.crypto (cost: dead-letter debugging friction). (a)+(b)
  recommended; not implemented — visibility/retention trade-off is a
  product decision.

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

## AUD-019 — Refund credit notes are created without currency: foreign-currency refunds are misbooked

- **Severity:** critical (wrong money posted silently in a realistic configuration)
- **Status:** open (verified — Tier 1)
- **Evidence:**
  - `sync/refund_sync.py:358-365` — `account.move.create({...})` passes
    `move_type, partner_id, journal_id, invoice_origin, ref,
    invoice_line_ids` — NO `currency_id`. The move therefore defaults to the
    journal/company currency.
  - Amounts on those lines come from `_money()`
    (`refund_sync.py:59-69`), which returns presentment- or shop-currency
    amounts per `backend.import_currency_mode`.
  - The original invoice, by contrast, IS in the order currency (order
    import sets `currency_id` + auto-created pricelist,
    `sync/order_sync.py:184-191`, `:434-457`).
- **Description:** for any order whose currency differs from the company
  currency (EUR presentment on a USD company, or EUR shop currency on a USD
  company), the refund posts a credit note labeled in COMPANY currency
  carrying ORDER-currency numerals. The receivable cannot reconcile against
  the foreign-currency invoice, and the auto-balance delta
  (`refund_sync.py:372`) compares amounts across currencies. Books are
  wrong with no signal. (The >0.05 delta activity may fire incidentally —
  with a misleading message.)
- **Test gap:** suite is green because no test refunds a non-company-
  currency order through the credit-note path (Tier 4 item).
- **Proposed fix (not implemented):** set `currency_id` on the credit note
  from the original invoice (preferred: `posted_invoices[0].currency_id`)
  or the order currency; assert the `_money()` currency code matches it and
  degrade visibly when it doesn't.

## AUD-020 — Unresolvable order currency: import proceeds, foreign amounts booked as company currency

- **Severity:** critical (silent misbooking in the DEFAULT Odoo configuration)
- **Status:** open (verified — Tier 1)
- **Evidence:**
  - `sync/order_sync.py:405-432` — `_resolve_currency` returns `False` when
    the currency is not found OR exists but is inactive (warning log:
    "Currency %s is inactive; activate it to import order %s with correct
    currency.").
  - Caller `order_sync.py:183-191` — `if currency:` block simply skipped on
    False → `order_vals` gets neither `currency_id` nor `pricelist_id` →
    the sale order lands in company currency.
  - Line amounts still come from `_get_money_amount`
    (`order_sync.py:392-404`), which returns presentment/shop amounts
    regardless of resolution outcome.
- **Description:** Odoo ships all non-company currencies INACTIVE by
  default, so a merchant with a USD company importing EUR-presentment
  orders hits this on day one: 110.00 EUR order books as a 110.00 USD sale
  order, invoice, and payment. Server-log warning only; order, invoice and
  payment all look healthy. This is the silent-wrong-money pattern at its
  worst.
- **Proposed fix (not implemented):** when the currency cannot be resolved,
  do not import silently — put the order binding in error state with an
  actionable `sync_error` ("Activate currency EUR in Odoo, then retry"),
  consistent with rule 5. Optionally auto-activate the currency (decision
  for Ahmed — touches config policy).

## AUD-021 — Refund idempotency hole: binding-create failure orphans a posted credit note → duplicate on retry

- **Severity:** major (double credit notes possible; low probability, high
  financial impact)
- **Status:** open (verified — Tier 1)
- **Evidence:**
  - Dedup is ONLY the binding-existence check
    (`refund_sync.py:42-48`).
  - `_create_refund_credit_note` creates AND posts the credit note inside
    its own savepoint (`refund_sync.py:356-403`), which is released before
    the binding is created at `refund_sync.py:150`.
  - A failure in `refund_binding.create()` (or anything between savepoint
    release and binding creation) is caught by the per-refund handler
    (`refund_sync.py:53-55`): the posted credit note SURVIVES in the
    transaction, the binding does not exist, and the next sync re-imports
    the refund and posts a second credit note.
  - No secondary marker exists on the move (no refund GID stored; `ref` is
    the free-text note), so no memo-style recovery guard is possible —
    contrast with `_register_payment`'s two-layer idempotency
    (`payment_status_sync.py:377-415`).
- **Proposed fix (not implemented):** create the binding (error state)
  BEFORE creating the credit note and update it after, OR wrap credit-note
  + binding creation in one savepoint, AND stamp the refund GID on the
  credit note (e.g. in `ref` or a dedicated field) with a search guard
  mirroring the payment memo pattern.

## AUD-022 — No cumulative over-refund guard on credit notes

- **Severity:** major
- **Status:** open (verified — Tier 1)
- **Evidence:** `refund_sync.py:74` takes Shopify's `totalRefundedSet` as
  truth; lines are built (`:226-346`) and the auto-balance delta
  (`:367-401`) forces the credit-note total to equal the Shopify refund
  amount. Nothing compares the refund — or the SUM of all refunds for the
  order — against the posted invoice total or captured amount. The only
  tripwire is the >0.05 delta activity (`:387-401`), which does NOT fire
  when Shopify itemizes the full amount (delta ≈ 0).
- **Description:** Shopify itself prevents refunding more than was
  captured, so the realistic exposure is Odoo-side mismatch (partial
  invoice, edited invoice, duplicate refund payloads, or AUD-021
  duplicates): credit notes can exceed the invoiced/captured amount and
  post silently.
- **Proposed fix (not implemented):** before posting, compare cumulative
  refund-binding amounts + current refund against the posted invoice
  total (same currency per AUD-019); degrade visibly above tolerance.

## AUD-023 — Refund line-building edge cases (bundled minor)

- **Severity:** minor (failure modes end visibly via the savepoint +
  activity backstop; bundled for the record)
- **Status:** open (verified — Tier 1)
- **Evidence / branches:**
  - `refund_sync.py:230` — zero-qty or zero-amount refund lines are
    skipped; any tax on them is recovered only via the untaxed delta
    adjustment line.
  - `refund_sync.py:259-264` — non-product line with no fallback account:
    `continue` (silent drop); the delta line then re-adds the amount
    untaxed, or the post fails into the visible handler (`:424-446`).
  - `refund_sync.py:300-302` — shipping line appended without `account_id`
    when no fallback account; relies on Odoo's product-based account
    auto-resolution; crashes visibly only when nothing resolves.
  - Tax-fallback branches (`:252-258`, `:296-299`) book gross amounts with
    taxes cleared and DO schedule review activities — visible by design
    (settled hardening; no finding).
- **Proposed fix (not implemented):** log+count the `:264` silent drop;
  resolve shipping account via `get_product_accounts` like product lines.

---

## Regression checklist — LEGACY_NOTES.md §1 (18 fixed bugs), verified 2026-06-11

Method: subagent scan + my spot-verification of the two shakiest items
(BUG-R2, BUG-EW-09). Suite context: 0 failed, 0 errors of 532 on
adams_strict1 (2026-06-10 baseline).

| Bug | Fix present? | Evidence | Test coverage |
|---|---|---|---|
| BUG-R1 | yes | refund_sync.py:114-117 None-guard | tested (test_core_workflow_hardening: TestRefundCreditNote, 6 methods) |
| BUG-R2 | yes (evolved) | both sides now use full GIDs: product_sync.py:244-247 stores `sv.get('id')`; refund matching searches full GID (refund_sync.py:89-94) — spot-verified | tested (variant fixtures use full GIDs, e.g. test_core_workflow_hardening.py:746) |
| BUG-O1 | yes | order_sync.py:647-708 rate fallback | tested (test_order_import taxed-order test) — but see AUD-001/015/016/017 |
| BUG-O2 | yes | order_sync.py:625-629 + base_importer.py:52 | tested (TestZeroPriceDiscount) |
| BUG-C1 | yes | collection_sync.py:52 | implicit only — Tier 4 gap |
| BUG-CU1 | yes | customer_sync.py:159 backend_id in dedup | tested (TestCustomerExportTags + dedup tests) |
| BUG-EW-08 | yes | base_importer.py:113 `_apply_import_mappings` | tested (test_field_mapping, 4+ methods) |
| BUG-EW-12a | yes | shopify_reconciliation.py:137-143 all 5 models | tested (test_reconciliation) |
| BUG-EW-12b | yes | shopify_reconciliation.py:161 increment | tested (test_retry_count_increments_not_resets) |
| BUG-EW-14a | yes | customer_sync.py:77 strip-split | implicit only — Tier 4 gap |
| BUG-EW-01a | yes | collection_export.py:45-53 skip w/o mark | implicit only — Tier 4 gap |
| BUG-EW-02a | yes | metafield_sync.py:137-152 type-aware serializer | implicit only — Tier 4 gap |
| BUG-EW-04a | yes | gift_card_sync.py:27-31, :96 | implicit only — Tier 4 gap |
| BUG-EW-07 | yes | order_sync.py:695-706 warnings | tested — but drop branch is log-only (AUD-016) |
| BUG-EW-09 | yes | product_sync.py:489-495 stale-image unlink — spot-verified | covered in test_product_sync |
| BUG-EW-05a | yes | payout_sync.py:156-172 type validation | covered in test_payout_import |
| EW side finding | yes | zero `self.env.with_company(` occurrences module-wide | exercised by suite execution |

Verdict: 18/18 fixes present. 5 bugs covered only implicitly → explicit
regression tests queued for Tier 4 (BUG-C1, EW-14a, EW-01a, EW-02a,
EW-04a).

## Tier 1 leads deferred to later tiers

- product_sync.py:240 — POSITIONAL variant matching
  (`odoo_variants[i] ... else odoo_variants[-1]`) when creating variant
  bindings; mis-ordered variants would silently mis-bind products (wrong
  product on orders/refunds). Needs Tier 2 verification of the call
  contexts (export-create vs import paths; SKU-based path exists at :449).
- shopify_reconciliation.py:95-126 — stale-binding heuristic warns on any
  catalog unchanged >24h; log-only noise, counter discarded (Tier 3).
- TestPaymentStatusSync exercises the gateway-fetch leg against the
  harness's BlockedRequest instead of a mocked client (Tier 4, with the
  AUD-002 timeout-tuple note).

---

## Environment-sensitivity notes (not defects in shipped code)

- **ENV-1 (test infrastructure): FIXED 2026-06-12** — promoted from Tier 4
  backlog after it broke the Odoo.sh build (install.log relayed by Ahmed:
  5 errors of 221, suite halted at the error cap; all five
  `null value in column "country_id" of relation "account_tax"`, the
  Odoo.sh dev DB having no chart and no company country). Full root
  cause, all chart-provided state the suite silently depended on:
  (1) `account.tax.country_id` required, computed from company country
  (core account_tax.py:197) — null without a company country;
  (2) `account.tax.tax_group_id` required, compute only searches
  existing groups (account_tax.py:156,284) — none exist without a chart;
  (3) no bank journal → `_resolve_payment_journal` has no fallback, the
  AUD-007 reconcile test never reached its assertion;
  (4) `company.income_account_id` empty — `_get_product_accounts`' final
  fallback (core account/models/product.py:73; set by charts,
  template_generic_coa.py:48), so the auto-created SHOPIFY-SHIPPING
  product resolved no income account and auto-invoicing was skipped in
  4 tests. Fix (test-code only, both mixins — connector tests/common.py
  and simulator tests/test_refund_fidelity.py): bootstrap company
  country (US), a tax group, a bank journal, and
  company.income_account_id, each ONLY when missing — all four are
  no-ops on charted DBs (verified: strict1 company already has
  income_account_id from the chart). Commits 2d88344 (+ efdd2e2
  predecessor), e39aebc. Evidence: chartless fresh profile fail-before
  1 failed + 15 errors of 578 → pass-after 0 failed, 0 errors of 578
  (first-ever green chartless run); regression: adams_strict1 0 failed,
  0 errors of 578; adams_strict_vat 0 failed, 0 errors of 578.

---

## Goal 0 Addendum — MORNING_REVIEW References (2026-06-12)

References to `MORNING_REVIEW.md` in this repository are historical audit/governance context. `MORNING_REVIEW.md` was retired before Goal 0 and is not an active instruction source. Consequence statements and operating guidance should now be found in `FINALIZE.md`, `docs/architecture/DECISIONS.md`, and `AGENTS.md` as applicable.

---

## AUD-027 — Onboarding webhook registration failure is swallowed during setup

- **Severity:** major
- **Evidence:** `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:92-99` — setup attempts `backend.action_register_webhooks()` but catches `Exception` and executes `pass`; no sync log, activity, notification, or wizard error records the failed webhook registration.
- **Description:** A merchant can finish setup believing webhooks are registered when registration failed. That violates the no-silent-failure rule for a reliability-critical setup step because future order/payment/refund events may not arrive.
- **Proposed fix:** Keep setup reversible, but record a warning notification and backend activity/sync log with the registration error and a retry action.
- **Status:** open

## AUD-028 — Outbound fulfillment push failure is warning-only after Odoo delivery validation

- **Severity:** major
- **Evidence:** `addons/shopify_connector_pro/models/stock_picking.py:34-59` — `_push_outbound_fulfillment()` catches fulfillment push exceptions and only logs a warning after the Odoo picking is already validated.
- **Description:** Odoo delivery can be completed while Shopify fulfillment creation fails with no merchant-visible activity on the order/picking. The systems diverge on fulfillment state, and the merchant may not know Shopify still needs manual fulfillment.
- **Proposed fix:** Schedule an activity and/or create a sync-log error on the sale order/backend when outbound fulfillment push fails; keep picking validation intact.
- **Status:** open

## AUD-029 — Odoo-to-Shopify refund reverse sync lacks an explicit idempotency key/persisted Shopify refund binding

- **Severity:** major
- **Evidence:** `addons/shopify_connector_pro/models/account_move.py:134-170` — reverse credit-note sync builds and sends `refundCreate`; no persisted Shopify refund ID/idempotency marker is written after success in this method.
- **Description:** Posting an Odoo credit note can create a real Shopify refund, but the inspected reverse path does not record a Shopify refund identifier or idempotency token. Retry/replay semantics are therefore unclear for a money-path operation.
- **Proposed fix:** Before enabling/claiming this in v1, decide the product policy and add a persisted idempotency marker/binding or require manual Shopify refund creation.
- **Status:** open
