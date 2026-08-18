# Batch 1 Pre-UAT Review Packet — order + fulfillment verticals at `f62db111`

> Independent adversarial pre-UAT review (DEC-042 reviewer role) of the code
> the Batch 1 live campaign will exercise: the order-import vertical
> (`shopify_connector_sale`) and the fulfillment vertical
> (`shopify_connector_fulfillment`). Neither has ever touched a real Shopify
> order/fulfillment; both suites are green because fixtures manufacture the
> payloads and mock the readers wholesale. GraphQL documents were validated
> against the live Shopify Admin 2026-07 schema where possible. **Batch 1 must
> execute this packet's pre-flight and blocking fixes before the live
> campaign** — otherwise the first UAT run dies at the first order import and,
> if that is bypassed, again at the first fulfillment write.
>
> Summary verdict: the verticals' safety architecture (atomic order import,
> post-C2 discipline, cursor pagination, notification freeze, Mode 2 TOCTOU
> machinery) is sound; the defects are contact-with-reality seams exactly like
> the ones live UAT found in the product vertical. Fix here is cheaper than
> discovering them one dev-store round trip at a time.

## 0. Pre-flight (minutes each, do first, before any code change)

| # | Check | Decides |
| --- | --- | --- |
| PF-1 | Run the raw `ConnectorOrderHeader` query against the dev store with a real order GID. The schema validator rejects `LineItem.priceAfterAllDiscountsBeforeTaxesSet` while the changelog says it shipped in 2026-07 — the two authorities disagree. | O-P0-1: if rejected, **no order can import at all** and the symptom is an unnamed `data_shape_schema_mismatch`. |
| PF-2 | Run the raw `ORDER_FULFILLMENTS_QUERY` — expected to **fail**: `Order.fulfillments` is a plain list, not a connection (`after`/`pageInfo`/`nodes` invalid). | F-P0-1 confirmation. |
| PF-3 | Confirm protected-customer-data access is granted for the dev app; without it `customer`/`email`/addresses return null and every order takes the fallback path. | D-9 severity. |
| PF-4 | Confirm scopes include `read_locations`, `read_assigned_fulfillment_orders`, `read_third_party_fulfillment_orders` (readiness only checks the write scope today). | F-P1-5. |
| PF-5 | Configure `customer_fallback_partner_id` on the store settings. | Guest/no-email orders block otherwise. |
| PF-6 | On the dev store, check whether `Order.taxLines` includes shipping tax (place one taxed-shipping order, read both fields). | O-P1-2 fix direction. |

## 1. Order vertical — blocking before live campaign

- **O-P0-1 — order header query may not compile** (`shopify_connector_order_importer.py:110-113`, `:163-166`): `priceAfterAllDiscountsBeforeTaxesSet` rejected by the live schema validator. Resolve per PF-1; if invalid, source the pre-tax net from fields that exist (e.g. `originalTotalSet` − tax) and add a test that asserts the on-wire document against a recorded live validation.
- **O-P0-2 — zero-tolerance tax-inclusive rounding** (`:1315-1332`): Shopify's rounded pre-tax net is compared to Odoo's independently rounded de-taxed figure with **no tolerance**; a £9.99 VAT-inclusive line has ~coin-flip odds per line of `financial_total_mismatch` (hard block) or a silently invented fractional discount (wrong data). No fixture in the suite uses a non-round price. Fix: compare within `currency_id.rounding`, or derive the base from Shopify's own totals; add non-round-price tax-inclusive tests (9.99/19.99 at 20%).

## 2. Order vertical — material (fix in Batch 1)

- **O-P1-1** `displayFinancialStatus: null` (nullable per schema): scan tolerates it and enqueues; importer raises fatal-schema → `failed_final` (never retried) — the vertical manufactures its own dead jobs, and a test codifies the bug (`test_null_financial_status_is_fatal_schema_mismatch`). Route to review/retry, not `failed_final`.
- **O-P1-2** Taxable shipping likely breaks both order-level tax reconciliations (`:1017-1044`) if `Order.taxLines` covers line items only (docs say so). Shipping-line import branch (`:1390-1468`) has zero positive test coverage. Resolve with PF-6, fix accordingly, add positive taxed-shipping tests.
- **O-P1-3** `TaxLine.rate`/`ratePercentage` are nullable; `Decimal(str(None))` explodes into an opaque schema error instead of the tax-decision wizard (`tax_mapping.py:20-47`); also requires *both* representations present and agreeing. Treat missing-rate as a wizard-routable condition.
- **O-P1-4** `totalTaxSet: null` on a legitimately tax-free order is a hard block (`:584-588`, `:860-864`); read as zero tax instead.
- **O-P1-5** Policy skips (edited/test/cancelled) run *after* strict shape validation (`:589` vs `:595-614`) — an order cancelled between scan and import hard-fails as a schema defect instead of skipping. Reorder.
- **O-P1-6** Fiscal-position remapping mutates the mapped tax then blocks with no wizard escape (`:1780-1791`, `:1838`); any auto fiscal position (intra-EU/export) triggers it. Decide policy: respect the mapped result or validate pre-mapping.
- **O-P1-7** Customer with GID but null email falls into the guest branch: no customer binding is created, GID→partner link dropped, possible wrong-partner attach recorded as `guest_email_match` (`:1086-1172`). Also `_find_active_candidates` matches child-address partners (`type='delivery'`) with no type filter (`customer_importer.py:353-367`).

## 3. Fulfillment vertical — blocking before live campaign

- **F-P0-1 — `ORDER_FULFILLMENTS_QUERY` is invalid GraphQL** (`shopify_connector_fulfillment_reader.py:51-70`): `Order.fulfillments` is `[Fulfillment!]!`, not a connection (validated: three schema errors). Every reconcile read, the hourly reconciliation cron, inbound observation, reconnect catch-up, and the mode-switch scan die on first live contact — and the resulting `ShopifyClientError` bypasses every `except FulfillmentReadError` guard, escaping unclassified. Rewrite as the list form with a `fulfillmentsCount` truncation guard; also catch `ShopifyClientError` in the fail-closed paths.
- **F-P0-2 — location cache is never populated** (`reader.py:394-467`; `__manifest__.py:34-39`): `_refresh_location_cache` has zero production callers, and the addon does not depend on `shopify_connector_inventory` — the only module that fills the cache. Every fulfillment admission fails `ambiguous_match` before any Shopify write. Additionally Mode 2 check 8 requires a mapping with `push_enabled=True`, so fulfillment-without-inventory-push can never pass. Fix: wire cache population into this addon's lifecycle (or declare the dependency deliberately) and decouple check 8 from push-enablement.
- **F-P0-3 — reconcile adopts the wrong fulfillment GID** (`fulfillment_create_strategy.py:500-513`, `:544-580`): with no tracking numbers, matching short-circuits to the **first** SUCCESS fulfillment on the order (the *oldest*), overwrites picking 1's binding (which never updates `picking_id`), orphans picking 2, and spawns a spurious external-fulfillment review — while looking like success. Identity must come from FO-line matching against `preconditions_snapshot['line_items_by_fo']` plus `createdAt > snapshot` — never order-level tracking-number/first-SUCCESS heuristics.
- **F-P0-4 — Mode 2 can never be enabled**: the switch scan hits F-P0-1 (`fulfillment_scans.py:324-330`), the error escapes, and the settings hook writes `failed_retryable` every attempt. Fixed by F-P0-1 + catching the right exception; verify end-to-end after.

## 4. Fulfillment vertical — material (fix in Batch 1)

- **F-P1-1** `_enqueue_once` matches **terminal** jobs by payload hash (`fulfillment_admission.py:192-200`): reverting a tracking number to a previously-sent value is a silent permanent no-op; re-saving an identical value after a failure enqueues nothing. Filter by non-terminal state (or include attempt generation in the hash).
- **F-P1-2** One `ON_HOLD`/`SCHEDULED` FO anywhere on the order blocks the whole order (`admission.py:260-267`) — any pre-order line or fraud hold rejects a picking whose lines map to a perfectly OPEN FO. Scope the check to the FOs the picking ships from.
- **F-P1-3** Kit/phantom-BoM components share the kit's `sale_line_id`, sum against the kit line's `remainingQuantity`, and fail `ambiguous_match`/`quantity_mismatch` (`reader.py:311-359`, `mode2.py:450-471`); fractional components round via `int(round(...))`.
- **F-P1-4** No carrier mapping: Odoo delivery-method labels ("Standard delivery") are sent as Shopify `trackingInfo.company`, which requires exact names from Shopify's list — tracking renders unlinked/stale. Add a carrier mapping (data + per-carrier field).
- **F-P1-5** Scope-filtered FO reads are silently partial (`hasNextPage:false` on a scope-truncated set); readiness never asserts the read scopes (PF-4).
- **F-P1-6** "Validate proposed" review action calls Mode 2 evaluation with `job=None` → `ShopifyQuiescedError` traceback at the Administrator instead of a review reason (`fulfillment_review.py:188` → `mode2.py:61,114`).

## 5. Same-pass cleanups (P2/P3 — fix inline, no separate cycle)

Order: tautological line-base check makes the solver's line adjustment dead (`:1355-1365` vs `:1980-1983`); tolerance scales with line count; `_resolve_product` ignores `active`/`sale_ok`; `match_key='existing_binding'` recorded on first import; exact-string `ValidationError` matching in `_invoke_handler`; gift-card orders block at `mapping_missing` before the documented note path.
Fulfillment: C13 misses the reverse `(store, gid)` binding conflict (IntegrityError escapes unclassified); clearing tracking can never be pushed but still enqueues a visible failure; C11 lot/serial compares across UoMs without `float_compare`; inert `reconciled_quantity_ledger` (keys mismatch); dead `target_fo_gid` + false comment; stale A4 enum values.

## 6. What is confirmed solid (preserve; do not refactor in Batch 1)

Order: savepoint atomicity of customer+order+lines+binding with correct replay refusal; cursor discipline (non-advancing/repeated cursor refusal, pinned `updatedAt`); shipping-tax inclusive/exclusive posture; tax fingerprinting and the tax-decision wizard routing; pending-wait expiry; zero/3-decimal currency fail-closed.
Fulfillment: admission gating for non-Shopify pickings; outbound partial/backorder matching (caps at `remainingQuantity` — correct); `fulfillmentCreate` 2026-07 shape and the four other GraphQL documents (validated clean); notification freeze; post-C2 discipline (`not_applied`→`inconclusive` coercion, inconclusive cap, no resend authority); Mode 2 TOCTOU machinery (second fresh read, zero-I/O relock, ordered `FOR UPDATE SKIP LOCKED`, savepoint application); mode-switch end fence.

## 7. Open questions (resolve with official docs / live store; never assert)

1. `LineItem.priceAfterAllDiscountsBeforeTaxesSet` in 2026-07 — decisive (PF-1).
2. Does `Order.taxLines` include shipping tax (PF-6)?
3. When do `totalTaxSet` / `displayFinancialStatus` actually come back null on a dev store?
4. Does un-bounded `Order.transactions` truncate (manual-gateway classification depends on completeness)?
5. `Order.fulfillments(first:)` cap and truncation behavior (sizes the F-P0-1 guard).
6. Does `fulfillmentCreate` accept `lineItemsByFulfillmentOrder` spanning FOs at different locations?
7. Exact `trackingInfo.company` accepted list and unrecognized-string behavior (sizes F-P1-4).
8. Can Shopify Protect / risk auto-apply `ON_HOLD` on a dev store (sizes F-P1-2)?
9. `fulfillmentTrackingInfoUpdate` replace-vs-merge semantics, and whether company-only input clears numbers.

## 8. Definition of done for the Batch 1 code portion

Pre-flight PF-1…PF-6 executed and recorded; all P0s fixed with behavioral tests that use production payload shapes (non-round prices, taxed shipping, no-tracking fulfillments, multi-FO orders); P1s fixed or explicitly review-routed; P2/P3 fixed inline; the live vertical then executed per the master prompt's Batch 1 script with full ledger evidence. Tests may not encode defects (the `test_null_financial_status_is_fatal_schema_mismatch` pattern); fixture realism is part of acceptance.
