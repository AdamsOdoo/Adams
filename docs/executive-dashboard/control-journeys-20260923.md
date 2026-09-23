# Dashboard control and journey checklist

**In progress; not owner acceptance.** This maps the existing implementation's controls to their sources and context behavior. Final visual/staging qualification is still pending. Latest completed native candidate: `81e76b213d22db282fdb001431224cc4d40a9cf4` /38562949 (125/125). Follow-up RTL/caption/control corrections remain subject to native validation.

| Controls | Action and authoritative source | Result and context |
|---|---|---|
| Company selector | Standard Odoo authorized-company API; fresh bootstrap and company name/logo | Switch active company; retain dates/department; clear company-specific data and filters. Reject unauthorized choices. |
| Period, custom dates, balance cutoff, Apply, Refresh | Existing report options; period and balance dates are distinct | Reload matching sources; show unapplied changes; preserve applied scope after failures. |
| Department navigation / mobile tabs | Existing Owl client action | One active department; retain working selections; reset page scroll when changing department. |
| Finance values, report links, chart bars/table amounts | Approved company account-report definitions; selected chart month for bar/table actions | Native financial report with matching company/date scope; dashboard breadcrumb restores meaningful context. |
| Source information icons / source drawer / Back | Source metadata and signed report value | Show company, period/cutoff, report definition; close restores focus; View report opens that source. |
| Bank/cash split, accounts drawer, account rows | Standard Bank/Cash journals and associated unique accounts; signed closing balances reconciled to approved cash report | Account directory and scoped General Ledger; no duplicated shared-account totals or invented bank/cash classification. |
| Receivable/payable overdue, aging bars/details, bucket values, Partner Ledger | Native aged reports and Partner Ledger; signed buckets | Full balances remain distinct from overdue and supplier-only schedules. Due-today amounts excluded from overdue. |
| Cash flow, forecast, supplier windows | Native Cash Flow Statement / approved forecast definition / payable invoice instalments | Posted source scope and selected cutoff; overdue/today/7-day/30-day screens retain their distinct filters. No unsupported comparable-period claims. |
| Inventory search, warehouse, category, stock date, quantity checkboxes, sort, Clear, Apply | Authorized stock products/locations and native quantity computation | Applied filter summary; eight-row pages; filter changes restart/clamp page; historical quantities do not imply historical reservations. |
| Inventory page controls / expanded rows / stock row actions | Same filtered product/location set | Position and totals, disabled unavailable directions; row and page context restored on return when still valid. |
| Inventory Valuation / Forecast / Replenishment / quantity source actions | Native stock valuation, forecast product view and stock source records | Matching authorized company and relevant warehouse/location/product/category/search scope. Forecast destination is the native forecast-capable product view. |
| Sales ranking tabs, product value/quantity and unit selector, customer/order rankings | Invoice Analysis / Sales Analysis; posted invoice less credit-note signs and distinct document scopes | Matching dimension/record source; do not aggregate unlike units or mixed document currencies. Selections retained through saved/return journeys. |
| Sales recent document tabs, paging, document rows and fulfilment | Authorized sale orders/quotations/invoices and native stock moves | Open corresponding native document or scoped fulfilment records; restore list tab, page and filters. |
| Procurement worklists, state selections, paging and record/source links | Authorized purchase orders and receipts | Truthful order-count labels/worklists; UI20 monetary-versus-count choice stays deferred. |
| CRM stage/worklists, paging and opportunity/source links | Authorized CRM leads/opportunities and source stage/state scope | Corresponding native CRM records; retain company/period and current list selections. |
| HR Overview cards, department rows and upcoming records | Authorized employee/attendance/time-off/planning sources | Move directly to the corresponding HR tab/filter or native record; independent HR dates remain explicit. |
| HR Attendance, Time off, Shifts, Employees tabs, filters, paging/week/load-more | Installed source applications and actual source-model permissions | Honest unavailable/restricted states; apply/reset offsets on filter changes; native source views retain HR scope. |
| Employee work profile, Back, employee/source-related records | Permitted work-profile fields and source-specific authorization | No private fields exposed; linked attendance/leave/shifts use the selected employee. |
| Search and result rows | Authorized invoices, bills, orders and quotations within applied company/period | Scoped result drawer and native document; unavailable sources stay explicit. |
| Saved views, restore and reset | Browser-local selections only | Persist company-keyed dates/tabs/filters, never business rows; reload sources on restore; reset does not delete the saved view. |
| CSV, print preview, PDF and detail exports | Existing source-backed export services | Scope and unavailable states remain explicit; source report exports stay native. |
| More, layout controls, definitions and settings | Existing client controls / authorized configuration action | Menu/focus recovery; settings only for permitted users; no prototype explanation dialogs. |

## Verification still required on the final candidate

- Paired visual acceptance across all six departments and five HR tabs, including representative responsive/appearance/RTL and interaction states.
- Real staging company/date/filter/report-return journeys and changed Inventory Forecast/page-size reconciliation.
- Loaded assets, exact source/module/build identity, console/RPC errors and dashboard-only upgrade evidence.
- Review the separate synthetic-capture websocket access error; passing unit/browser assertions alone do not waive it.
- Optional HR applications remain uninstalled in staging; do not claim populated live Attendance/Time off/Planning journeys or install them for screenshots.

Existing focused frontend tests cover stale responses, failed requests, retry/unlock, company isolation and saved/returned selections. Existing native source tests cover report options, signed values, role/company denial and operational source scopes. Their passing results are evidence for those checks, not blanket visual or production approval.
