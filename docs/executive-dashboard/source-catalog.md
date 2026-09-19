# ED-001 native source catalog — discovery checkpoint

Status: partial source inspection; **not an installed-report catalog or approved production mapping**. All installation-specific mappings remain blocked by ED-B01 in [the dossier](README.md).

Public code below was fetched on 19 September 2026 at Odoo Community commit `82f4b92eaf3f2014eb1667e4845e80c377dbfb4f`, the inherited disposable runner pin. Future target extensions must be inspected before adopting these measures. The initial native invoice adapter was exercised in the first campaign; subsequent adapters are tracked in implementation-status.md.

## Verified source findings

| Family | Verified source facts | Mapping implications |
|---|---|---|
| Accounting definitions | `account.report` exposes report roots/variants, lines, expressions and columns in [account_report.py](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/account/models/account_report.py). The inspected Community file does not supply the required aging evaluation/action implementation. | Definition records are not numeric results. Native licensed engine, handlers, localization and UI options must be inspected; no guessed `_get_lines`/options call is implemented. |
| Cash configuration | [account_account.py](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/account/models/account_account.py) uses `company_ids`, `active`, `account_type`, `currency_id`; `asset_cash` and `liability_credit_card` are distinct types. [account_journal.py](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/account/models/account_journal.py) has `company_id`, `type`, `default_account_id`, and `bank_account_id`. A bank journal's account domain can include credit-card liabilities. | Discover ledger identities, not partner-bank records or names. A bank journal alone does not prove an asset is cash. Directory membership and native statement composition remain separate. Amount source is still blocked. |
| Sales Analysis | [sale_report.py](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/sale/report/sale_report.py): model `sale.report`; `date` derives from order date; native `price_subtotal`, quantity fields, and `order_reference` with `count_distinct`. `nbr` counts lines. Report includes native currency conversion. | Candidate confirmed-order scope `state = sale`; native untaxed amount and distinct orders, never sum `nbr` as orders. Verify target extensions and effective UI filters. |
| Sales action | [sale_report_views.xml](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/sale/report/sale_report_views.xml): `sale.action_order_report_all` targets `sale.report`, includes noncancelled domain, default Sales and last-365-days search filters. | Scoped drill-down must not silently retain a conflicting default date filter. Native search defaults are part of parity. |
| Invoice Analysis | [account_invoice_report.py](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/account/report/account_invoice_report.py): `account.invoice.report`, `invoice_date`, `state`, `move_type`, `invoice_user_id`; `price_subtotal` is the native converted untaxed measure. `price_margin` uses company-dependent product standard cost. `price_average:avg` has a native weighted aggregation override. | Posted customer invoices/credit notes are the candidate net-sales scope. Do not label commercial margin P&L gross profit, calculate currency conversion independently, or average subgroup averages. Document currency and report amount are distinct. |
| Invoice views | [account_invoice_report_view.xml](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/account/report/account_invoice_report_view.xml) provides native pivot/search definitions and customer/vendor, posting and date filters. | Target action identity is not yet verified; the view file is not proof of an installed action or permission. |
| Purchase Analysis | [purchase_report.py](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/purchase/report/purchase_report.py): `purchase.report`, `untaxed_total`, `qty_ordered/received/billed`, `date_order`, `date_approve`. `delay_pass` uses planned line date minus order date; `price_average:avg` uses native weighted grouping. | Do not present `delay_pass` as actual receipt performance. Respect native aggregate methods, company conversion and UoM semantics. |
| Purchase action | [purchase_report_views.xml](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/purchase/report/purchase_report_views.xml): `purchase.action_purchase_order_report_all`, model `purchase.report`; default order/year filters; native Orders search excludes draft/sent/cancel, potentially including approvals. | Owner's confirmed commitments and awaiting-approval widgets may need separate supported filters. Do not adopt the default Orders filter without examining its meaning. |

## Widget coverage and unresolved mapping

Every row requires actual installed action/backend, supported scope, technical measure/expression/column, aggregation, date basis, unit/currency, groups, permission and destination before enabling it. Financial identities are deliberately unset until discovery; translated labels, row indexes and invented database IDs are forbidden.

| Widget family | Required native source / provisional classification | Still to verify |
|---|---|---|
| Revenue, gross profit, net result, operating expenses and signed trend | P&L; direct native report results and comparisons | Localized report/variant, lines, expressions, columns, sign and periods |
| Margins / ratios | Executive Summary or native expression first | Exact denominator, zero behavior; any gap and approved composition |
| Assets, liabilities, equity | Balance Sheet | Approved lines/options/variant and cut-off |
| Bank/cash headline | Balance Sheet cash composition | Cash-equivalent policy, native membership, full total |
| Dynamic cash account directory / balances | Authorized accounts/journals plus Balance Sheet detail or aligned GL/TB | Complete include-zero semantics, account-level result route, archived history, FX and exclusion display |
| Cash movement / cash flow | Cash Flow Statement | Opening/closing/operating/investing/financing/other/FX technical mapping |
| Receivable total, aging, overdue, collections | Aged Receivable; first vertical slice | Handler/results, native buckets and overdue availability, historical settlement, complete totals, action/export |
| Payable total, aging, overdue, upcoming payments | Aged Payable | Same mapping and due-date rules; payable sign; worklist source |
| Partner balances, activity, statements/follow-up | Partner Ledger and installed statement/follow-up | Customer/vendor account scopes, opening amounts, child contacts and native detail actions |
| Budgets / targets | Installed approved budget/target reports | Scope, version, calendar and owner approval; absent means not configured |
| Standard forecast | Executive Summary / installed planning | Exact native horizon and assumptions |
| Enhanced daily cash plan and minimum cash | Inspect native options first; gap not established | Definition and approval only if native capability does not satisfy need; disabled |
| Net invoiced sales; top customers/products; salesperson ranking | Invoice Analysis; supported grouping/filtering | Target action/security; posting/type/date/currency context; unassigned/inactive groups |
| Commercial margin ranking | Invoice Analysis commercial margin if accepted | Actual extensions/cost basis and truthful label; never substitute accounting gross profit |
| Confirmed order amount/count; delivery quantities | Sales Analysis; supported measures | Target dates/currency/UoM/state and distinct count parity |
| Open quotations; recent orders/quotes | Native authorized record views/report | Validity rule, draft/sent scope, creation date, bounded lists and actual actions |
| Backlog value; open-late / completed-late; on-time completion | Installed operational reports first; gap not established | Partial deliveries/returns/cancellations, event/date definition, original-promise history and approval |
| Inventory quantities/value/aging | Stock/valuation reports; aging gap not established | Installed Odoo 19 backend, valuation basis, history, company/warehouse/location/owner scopes |
| Inventory shortage/supply/demand | Forecast, Locations, Moves, Replenishment | Native quantities and specialized services, reservations, physical vs projected shortages |
| Purchase commitments and approvals | Purchase Analysis plus authorized native operations views | State boundary, measure/currency/date, complete vendor/category/buyer groups |
| Procurement late supply / vendor timing | Installed receipt/vendor reports | Actual receipt event; `delay_pass` is not proof; gap approval if necessary |
| CRM pipeline/stages/activities | Installed native CRM reports/views | Current vs historical measures, stages/team/probability/date and native access |
| HR workforce/leave/attendance/capacity | Installed Employees/Time Off/Attendance/Planning reports | Actual modules, aggregate access, departments, current/scheduled/actual distinction |
| Payroll | Separately restricted installed source | Explicit authorized scope; never exposed through generic HR access |
| Management attention and thresholds | Native exception views / approved rules | Materiality, owner, dates, deduplication and supporting action; sample thresholds are not policy |

Inventory, CRM and HR implementation sources have not yet been inspected. Their rows explicitly remain unresolved; the catalog is not G0-complete.

## Additional-logic register

No demonstrated native gap and no approved custom formula yet. Candidate investigations are the contract section 2.5 items: cash planning, backlog, on-time delivery, collection rate, attention/targets and stock/procurement/history metrics. Each requires inspected native alternatives, exact source/formula/dates/exclusions/currency, owner, supporting records and independent expectations before an approval can enable it. A missing dependency is not a native gap.

## Expanded Community adapters (19 September 2026)

The following mappings were inspected at the same immutable Community source before
implementation. Their runtime results are bound to the subsequent feature campaign.

| Source | Verified definition and implementation boundary |
|---|---|
| CRM Pipeline Analysis | `crm.crm_opportunity_report_action`, `crm.lead`, native `prorated_revenue:sum`. Inspected `addons/crm/report/crm_opportunity_report_views.xml` and `addons/crm/models/crm_lead.py`. Scope is active pending opportunities created within the period and assigned to the selected company. Native weighted revenue is not a cash forecast; no custom probability formula. Stage/salesperson groups are native. |
| Time Off by Type | `hr_holidays.action_hr_leave_report`, `hr.leave.report`, native `number_of_hours:sum`. Inspected `addons/hr_holidays/report/hr_leave_report.py` and `hr_leave_reports.xml`. Approved requests starting in period only. The report excludes inactive employees and represents request hours as negative; preserve the sign. This is not headcount, period-prorated leave or available capacity. |
| Stock | `stock.action_product_stock_view`, `product.product`, native `qty_available`, `free_qty`, `virtual_available`, `uom_id`. Inspected `addons/stock/views/product_views.xml` and `addons/stock/models/product.py`. Current active storable products in selected company/shared product scope. Native computed quantities by product; no total across UoMs and no historical/valuation claim. Specialized forecast and valuation remain separate pending sources. |
| Dynamic cash directory | Authorized `account.account` with `asset_cash`, `company_ids` and archived history, joined to visible company bank/cash journals by `default_account_id`. Identity deduplicates accounts; unlinked accounts remain visible. Paginated metadata only; native financial balances still unavailable. This does not satisfy ED-CASH financial acceptance. |

All analytical dimensions are server-allowlisted; grouping, monthly trends and
amounts use native ORM report aggregation. Total cards are independent of paged
groups. Group CSV exports require native export permission, escape text formulas,
and refuse more than 5,000 groups rather than truncate. Full native exports remain
available via the native action; financial exports are not implemented.
