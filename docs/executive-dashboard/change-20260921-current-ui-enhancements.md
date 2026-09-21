# Current dashboard enhancements

## Authorized scope

Keep the current dashboard design. Improve typography/spacing, ordinary-language guidance,
stock by product/location, useful cash balances and movement, active bank/cash accounts,
numbered pages, invoice/order salesperson rankings, product/customer rankings, company
section visibility, personal ordering and accurate scroll selection. The user selected
**Balances and movement** for cash and **Product by location** for inventory.
Only the two dashboard addons, disposable tests and the dashboard dossier change.
Development and the previously authorized Adams staging are in scope. Production,
main, financial mappings and business records remain outside this change.

## Implementation

- Stock uses Odoo product quantities with `location` and `strict=True`, avoiding
  parent/child double counting. Warehouse/category/name filters, an optional end-of-day
  historical date, and independent zero/negative filters apply to each location.
  Current stock exposes on-hand/free/incoming/outgoing/forecast; historical stock omits
  current reservations and forecasts. Row source actions preserve company, location,
  product and date. Company-wide valuation is not repeated on each location row.
- Invoice quantity rankings compare one product unit at a time, with signed refunds;
  value rankings use existing scoped Invoice Analysis. Confirmed-order salesperson
  rankings use Sales Analysis. Top 5/10 controls do not redefine headline totals.
- Cash retains Cash Flow Statement opening/net movement/closing values and linked
  detailed reports. The confusing activity subsection and composition disclaimer are
  removed. The account list excludes archived accounts without changing report totals.
- Numbered page controls use exact totals when available and discovered pages otherwise.
- Company section visibility is distinct from remembered browser-only order/collapse.
  Filter edits announce that Apply filters is required; sections can retry independently.
  Existing colors, Odoo theme integration, layout, icons and navigation are retained.
- Settings action target corrected from unsupported `inline` to `current` for Odoo19.
  Earlier builds 38373682/38374362 failed installation on that selection value; those
  candidates were never qualified. This supersedes the former queue-only status.

## Evidence and limits

36 local controller tests pass; Python/XML parse checks pass. New Odoo fixtures cover
strict location quantities, negative/zero filters, category/warehouse scope, pagination,
historical dates, source actions, archived accounts and unit-separated refund ranking.
These fixtures require the Odoo.sh build; their presence is not a passing result.
Native build, live staging reflow/interactions and owner UAT remain pending.

## Upgrade / rollback

Both addons advance to 19.0.1.4.0. No new business data migration or accounting formula.
Upgrade both addons after feature qualification. Roll back only the two addon trees to
previous staging 06a5274b if needed, preserving unrelated code and business data. Previous
staging backup was verified at 2026-09-21 08:28:54 UTC; take a fresh backup before upgrade.

## Primary source contracts

- [Odoo19 product stock quantities and location/date contexts](https://github.com/odoo/odoo/blob/19.0/addons/stock/models/product.py)
- [Inventory at Date wizard](https://github.com/odoo/odoo/blob/19.0/addons/stock/wizard/stock_quantity_history.py)
- [Invoice Analysis quantity and refund signs](https://github.com/odoo/odoo/blob/19.0/addons/account/report/account_invoice_report.py)

Verification update: candidate 4e06cafe, build 38407345, completed **65 Odoo tests, zero failures/errors**, 197.26s, 65,356 queries. Final stock navigation guards and unit restoration are in a subsequent candidate and require its own build. Fresh staging backup verified 2026-09-21 16:35:54 UTC at 06a5274b.
