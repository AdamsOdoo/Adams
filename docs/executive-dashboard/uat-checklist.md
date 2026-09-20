# Executive dashboard — UAT preparation

**Status: not ready for business UAT.** This is the planned checklist, not a record
of completed acceptance. The full contract, customer-approved definitions and visual fidelity gates remain open. Native financial integration and bounded responsive browser evidence are now available; they do not establish full UAT readiness.

## Development installation

Install `adams_executive_dashboard` on the dashboard development branch only.
For licensed financial reports also install `adams_dashboard_finance`; configure
company mappings under Accounting → Configuration → Dashboard Financial
Definitions. Only an accounting manager can approve these business definitions.
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
locally per user. Native drilldown/back now preserves applied filters, selected analysis/pages and scroll in the action stack, while reloading values and rechecking permissions. Persistent local preferences contain section expansion only. Actual browser restoration remains to be verified.

## Business acceptance journeys (pending)

| Journey | Expected behavior | Status |
|---|---|---|
| Historical receivables/payables | Known dated settlements match native aging; drill to aging, original document, full export and back | Native historical receivable fixture passes; approved company mapping and accounting-authorized UI journey pending |
| Financial statements and cash | Native P&L/BS/CFS values and comparisons; complete dynamic account balances including zero and archived history | Native P&L/BS/CFS/GL/aging/budget/forecast adapters and fixtures pass; company approval and full parity matrix remain open |
| Sales and purchasing | Dashboard amount, distinct count, group/trend, native pivot and full export agree under the same company/dates/state/currency | Bounded native fixtures passed; one Invoice Analysis pivot/browser comparison passed at 2389d89, remaining journeys pending |
| CRM | Weighted open pipeline uses native prorated revenue and current pending status for opportunities created in period; stages remain dynamic | Bounded native fixtures passed; browser comparison pending |
| Inventory | Current quantities match native Stock by product/UoM; no false historical cutoff or mixed-unit total | Native current/historical quantity, valuation, archived-product and route fixtures passed at 4f50789; extended owner/location/aging and browser matrix remain open |
| HR | Only authorized native approved-request hours appear, retaining negative native signs and start-date semantics | Native signed leave and current workforce/department/access fixtures passed; full browser journey pending |
| Authorization | Finance, sales-only, no-dashboard, export-disabled and separate-company users cannot obtain unauthorized values through UI or direct RPC | Bounded automated coverage; full role matrix pending |
| Recent orders/quotations | Paged native records and draft/sent quotation values use the selected period/company; individual amounts keep document currencies; wrong-company/state/period record IDs cannot be opened | Native recent-list fixtures passed; browser acceptance pending |
| Delivery quantities | Native Sales Analysis ordered/delivered/remaining quantities by product/UoM, with current-data/order-date-cohort semantics and matching drilldown scope | Native signed-value fixture passed; backlog value/on-time completion and browser acceptance remain pending |
| Navigation and exports | Row drilldown preserves group scope; back restores context; CSV includes all groups or directs large datasets to native export | Server/controller checks only; browser pending |
| Arabic/English UX | Desktop/mobile RTL, long names, signs, keyboard, focus, error/retry and independent loading work at agreed widths | Native HttpCase EN/AR at six widths passes on 9e097f5; Finance screenshot visually reviewed. Reference Sales/mobile comparison and full interaction matrix still open |
| Performance | Measure usable Finance and filter-refresh p95 against representative data | Pending completed financial adapter and source-matched build |

## Explicit remaining functionality

Company/report/variant and completeness-policy approval; overdue/future maturity
worklists and full financial comparisons; enhanced cash plan only after approved
business definitions; backlog value/on-time measures after native-gap inspection
and approval; inventory aging/shortage and expanded warehouse/location/owner scope;
reference-matching Sales/mobile/RTL visual completion; full detail/export/security
parity; upgrade and representative performance evidence. See visual-acceptance.md.
Native cash balances, CFS, aging buckets, Partner Ledger scopes, standard forecast,
budgets, signed monthly trends, workforce, stock valuation/history, commercial
margin and purchase approval/late worklists are implemented with bounded tests.


Do not treat an unavailable card or a passing native fixture test as delivery of the
full required workflow. The project acceptance plan retains the original scope.

## First session after access is restored

1. Pin the feature-branch build and exact Community/Enterprise revisions. The
   onboarding URL alone does not establish that the new dashboard is deployed.
2. Install/upgrade the production addon only; check asset loading, server logs and
   menu access. Keep disposable test addons out of the customer database.
3. Verify installed report variants/localizations and the financial source catalog
   before connecting P&L, Balance Sheet, Cash Flow, aging or Partner Ledger values.
4. Exercise native list/report -> original record -> breadcrumb return. Confirm
   applied company/date, selected dimension/page and scroll restore, and confirm
   data is fetched again after changed permissions or records.
5. Compare English and Arabic at 320/390/768/1024/1440/1920 widths, including long
   customer names, mixed-script references, negative delivery quantities, focus
   order, keyboard controls and table scrolling. Screenshots must be from the
   actual feature build, not the supplied prototype.
6. Verify role/company/export matrices and report/native-UI/export parity using
   representative records and currencies. Native fixture evidence does not
   establish customer data completeness or every installed customization.
7. Finish the remaining accepted source mappings and definition decisions, then
   measure performance and complete business-owner UAT before proposing a merge.

## Current verified visual candidate

Source 9e097f54206d647b1bc3b0418125ec4d7d288f8f, Odoo.sh build 38345405:
50 tests, zero failures/errors. The browser fixture now additionally enforces four
primary profitability cards, six department tabs, required 320/390/1440/1920 column
counts and a performance-context panel. Native commercial margin/current-cost and
purchase worklist/no-approval-side-effect fixtures pass. Desktop Finance screenshot
was visually compared to the supplied reference on 20 September. This does not
close the Sales/mobile visual fidelity gate or full v4 UAT.
