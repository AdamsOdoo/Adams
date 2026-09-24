# Approved dashboard candidate: owner check

Status: candidate deployed to staging and representative live checks completed.
See [the final handoff](handoff-20260924.md) for exact evidence and remaining
acceptance boundaries. Do not use historical UAT checkboxes as acceptance of this candidate. Exact build/deployment status is in
[implementation-status.md](implementation-status.md). PR214 stays draft and no
production release is authorized.

## Quick owner journey

1. Confirm active company/logo, reporting dates and balance cutoff. In Finance,
   open revenue, return, inspect Bank/Cash, expand chart data and an aging drawer.
2. In Inventory, choose warehouse/category/search, apply, move to page2, open a
   product/location source and return. Narrow the search; the page and total must
   recover. Clear restores the unfiltered scope.
3. In Sales, change invoice value/margin, Top5/10, product value/quantity and unit.
   Change recent document type and page. Open a record and return to the same scope.
4. In Procurement, open approval and late receipt worklists; view a purchase order
   and supplier bill window. CRM opens the corresponding opportunity or analysis.
5. In HR, use its independently labelled company/period, each of the five tabs,
   filters, Week/List, pagination, employee profile and source links. Missing apps
   and restricted records must remain explicitly unavailable.
6. Review paired reference/Odoo images, particularly dark, narrow and Arabic
   states. Report clipped text, changed geometry or missing controls as defects.

## Control/source/context checklist

| Controls | Authoritative source / destination | Retained or reset context |
|---|---|---|
| Company, reporting dates, cutoff, Refresh | Authorized company and existing report services | Applied scope retained across departments; company changes reload authorized values |
| Saved views, restore | Local selection preferences; data refreshed from Odoo | Department, dates, rankings and inventory filters restored; no values cached as truth |
| Finance values, source drawers, aging and cash links | Configured standard financial reports and permitted account/partner/document records | Matching company/period/cutoff; dashboard return restores selections |
| Finance chart month and data table | Posted financial series and report drilldowns | Selected month passed to source; dashboard period preserved |
| Sales rankings, Top5/10, value/margin, product unit | Invoice Analysis or Sales Analysis appropriate to each measure | Independent ranking selections retained; quantity restricted to one UoM |
| Recent Orders/Quotations/Invoices, pages, record links | Authorized sale orders/accounting moves | Type resets page; filter shrink clamps page; return retains meaningful scope |
| Delivery rows and source links | Sales Analysis, product/UoM groups | Company/period and product/unit preserved; signed quantities retained |
| Inventory filters, zero/negative flags, pages, expanded rows | Standard stock report and authorized location/product sources | Apply resets page; late responses rejected; return retains applied filters/date |
| Procurement metrics/worklists/recent records | Purchase Analysis and native approval/late purchase-order domains | Selected-period purchases; explicitly current approval/late worklists |
| Supplier payment windows | Posted payable installment source | Cutoff and exact due-window domain retained |
| CRM metrics, opportunities, report links | Authorized CRM pipeline | Company/date filter and measure definition preserved |
| HR Overview cards, departments, previews | Authorized Employees, Attendances, Time Off, Planning | Metric-specific current/today/period scope passed explicitly |
| HR tabs, search/department/status, archived flag, Clear | Source-specific rules and normal model/field permissions | Applied HR period retained; tab/page defaults reset intentionally |
| HR Week/List and pages/load more | Authorized Planning slots | Week first seven days; List full selected period; useful total and progress |
| Employee work profile and records | HR work-field allowlist and source-specific snapshots | Employee scope passed to selected records; no private employee fields |
| Retry, empty and unavailable states | Original authorized service request | Last successful unrelated sections remain usable; Retry keeps failed scope |
| Summary CSV/print and source exports | Current authorized values/native report export rights | Company/dates/status/unit remain labelled |

## Data reconciliation boundaries

- Finance remains report-first. UI07 removes unsupported comparisons. UI08 uses
  signed standard Bank/Cash journal accounts, deduplicating shared accounts.
- Quotation count uses distinct Sales Analysis order references with the same
  source domain. Delivery pagination counts product/UoM groups, not source lines.
- UI20 remains deferred: Procurement approval/late cards show source-backed order
  counts and current worklists. No unsupported monetary measure is introduced.
- HR list pagination uses six rows in the approved UI; normal API default remains
 25. Profiles fetch only permitted work fields. Current attendance/next shift/
  upcoming leave snapshots retain their explicit current meaning independently
  of a historical HR list period. Missing apps stay missing.

## Acceptance still required

The current native run, corrected comparison review, dashboard-only staging
upgrade, source/module/asset identity and representative live journeys are recorded
in the handoff. Full owner acceptance and independent review remain open.
Optional HR applications are not installed on Adams For Men staging; native
populated-app tests and live unavailable-state checks are separate evidence.
Owner visual/financial approval and production release approval remain separate.
