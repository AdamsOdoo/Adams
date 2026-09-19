# Executive dashboard — UAT preparation

**Status: not ready for business UAT.** This is the planned checklist, not a record
of completed acceptance. Enterprise finance implementation and source-matched
browser/deployment evidence are still required before inviting finance users.

## Development installation

Install `adams_executive_dashboard` on the dashboard development branch only.
It depends on Web and Accounting. Sales, Purchase, CRM, Stock and Time Off are
optional; install their normal apps to enable the corresponding native adapters.
Do not install `adams_dashboard_native_tests` in a customer database. That addon
lives under `test_addons` solely for disposable runner fixtures.

Grant the Executive Dashboard group and the user's existing native report rights.
The dashboard group itself does not grant accounting, export, inventory or HR rights.
Administrators can access the dashboard without the additional dashboard group.
CSV download also requires Odoo's export permission. Payroll is not exposed.

Use one currently selected, authorized Odoo company. Apply period and balance
cutoff explicitly. Supporting sections start collapsed; section expansion is saved
locally per user. Company/date filters are not restored from browser preferences.

## Business acceptance journeys (pending)

| Journey | Expected behavior | Status |
|---|---|---|
| Historical receivables/payables | Known dated settlements match native aging; drill to aging, original document, full export and back | Blocked: licensed engine mapping |
| Financial statements and cash | Native P&L/BS/CFS values and comparisons; complete dynamic account balances including zero and archived history | Blocked: licensed engine mapping |
| Sales and purchasing | Dashboard amount, distinct count, group/trend, native pivot and full export agree under the same company/dates/state/currency | Bounded native fixtures passed; actual browser comparison pending |
| CRM | Weighted open pipeline uses native prorated revenue and current pending status for opportunities created in period; stages remain dynamic | Bounded native fixtures passed; browser comparison pending |
| Inventory | Current quantities match native Stock by product/UoM; no false historical cutoff or mixed-unit total | Native current-quantity fixture passed; valuation/history/browser checks still pending |
| HR | Only authorized native approved-request hours appear, retaining negative native signs and start-date semantics | Native action scope only; business-value fixtures/browser checks pending |
| Authorization | Finance, sales-only, no-dashboard, export-disabled and separate-company users cannot obtain unauthorized values through UI or direct RPC | Bounded automated coverage; full role matrix pending |
| Navigation and exports | Row drilldown preserves group scope; back restores context; CSV includes all groups or directs large datasets to native export | Server/controller checks only; browser pending |
| Arabic/English UX | Desktop/mobile RTL, long names, signs, keyboard, focus, error/retry and independent loading work at agreed widths | Pending actual deployed browser evidence |
| Performance | Measure usable Finance and filter-refresh p95 against representative data | Pending completed financial adapter and source-matched build |

## Explicit remaining functionality

Financial engine adapters and report/variant approval; historical aging and partner
journeys; complete bank/cash balances; native forecasts/budgets where configured;
fulfillment/backlog/on-time measures after native-gap inspection and approved
business definitions; inventory valuation/aging/shortage coverage; workforce
aggregation; recent orders/quotations; preservation of report/back navigation state;
representative-volume performance and full independent acceptance review.

Do not treat an unavailable card or a passing native fixture test as delivery of the
full required workflow. The project acceptance plan retains the original scope.
