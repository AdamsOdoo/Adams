# Executive Dashboard — build log

One line per phase (date, commit, tests run, result), then that phase's notes.

| Phase | Date | Commit | Tests | Result |
|---|---|---|---|---|
| 1 | 2026-09-25 | `c1b9a3a2` | `oh test executive_dashboard`: 12 run, 12 passed (Community, demo). `oh shot /odoo/executive` EN + AR desktop: 2/2 ok. Extra local browser check at 1440 / 1024 / 390 px: no horizontal overflow | **completed** locally; dark mode not verified (Enterprise) |
| 2 | 2026-09-25 | `e8fa1abc` | `oh test executive_dashboard`: 23 run, 23 passed (Community, demo). `oh shot /odoo/executive` EN + AR: 2/2 ok. Local browser check of Finance at 1440 / 1024 / 390 px, EN + AR: no console errors, no horizontal overflow, drawers and Open in Odoo work. Independent `odoo-reviewer` pass + re-check | **completed** locally; Enterprise report path **not verified** (see below) |
| 3 | 2026-09-25 | `c74f63f` | `oh test executive_dashboard`: 23 run, 23 passed, Sales/CRM classes skipped (only `web` + `account` installed). Kept DB + `sale_stock,crm`: 37 run, 37 passed (Sales 9, CRM 5). `oh shot /odoo/executive` EN + AR: 2/2 ok. Local browser check of Sales and CRM at 1440 / 1024 / 390 px, EN + AR: 12/12, no console errors, no horizontal overflow, order and opportunity drawers open, Open in Odoo opens the delivery order and the opportunity | **completed** locally; no Enterprise-only part in this phase |
| 4 | 2026-09-25 | `912c1e8` | `oh test executive_dashboard`: 23 run, 23 passed, Sales/CRM/Procurement/Inventory classes skipped (only `web` + `account` installed). Kept DB + `sale_stock,crm,purchase_stock,stock_account`: 51 run, 51 passed (Procurement 6, Inventory 8). `oh shot /odoo/executive` EN + AR: 2/2 ok. Local browser check of Procurement and Inventory at 1440 / 1024 / 390 px, EN + AR: 12/12, no console errors, no horizontal overflow; stock report hide checkbox, paging, search, product drawer, tiles, order drawers and month column work. Payload on demo data: Procurement 27 ms, Inventory 94 ms, a stock page 62 ms | **completed** locally; no Enterprise-only part in this phase |
| 5 | 2026-09-25 | `e3ae310` | `oh test executive_dashboard`: 23 run, 23 passed, app-specific classes skipped (only `web` + `account` installed). Kept DB + `sale_stock,crm,purchase_stock,stock_account,hr_attendance,hr_holidays`: 59 run, 59 passed (People 8). `oh shot /odoo/executive` EN + AR: 2/2 ok. Local browser check of People at 1440 / 1024 / 390 px, EN + AR: 6/6, no console errors, no horizontal overflow; direction follows the language; directory paging and search, attendance, employee and department drawers, and Open in Odoo work; Planning panel hidden (not installed). Payload on demo data: People 112 ms (cold), a directory page 16 ms | **completed** locally; Planning (Enterprise) **not verified** |

## Phase 1 notes

- Client action path is `/odoo/executive` (`/odoo/executive-dashboard` belongs to the old module until Phase 6).
- The search RPC is `global_search`, not `search`: `search` would override the ORM method on the model.
- Section cache key also holds the user id (the brief lists groups only): record rules such as "own documents only" depend on the user, so users never share an entry.
- Year to date starts at the company's fiscal year start (`compute_fiscalyear_dates`).
- No `ir.model.access.csv`: the module adds no stored model (the dashboard is an AbstractModel; settings are fields on `res.company`).
- Welcome search is already live (name search, 5 per model, record rules); Phase 6 still owns the configured model list, Needs attention and Definitions.
- Report-line overrides in Settings are left for Phase 2 (Finance), where they are used.
- Not ported from the reference page: the language and theme switches (Odoo's user settings decide both), and the IBM Plex web font (no external font request; falls back to the web client font).
- Odoo runs rtlcss on the Arabic bundle, so the reference's `[dir=rtl]` overrides of physical properties (drawer slide, tab padding) were dropped; they would have flipped twice.
- An uninstall test is not written yet; the uninstall steps come in Phase 6.

## Phase 2 notes

- Finance is one `get_section` call. Community: 10 queries (`_read_group` on posted journal items). With `account_reports`: Profit and Loss, the Balance Sheet line "Bank and Cash Accounts" expanded by account, and Aged Receivable/Payable, each in a savepoint; on any error or scope mismatch the figure falls back to journal items. On Community no `account_reports` xml id is looked up.
- Revenue = `income` accounts; gross profit = revenue − `expense_direct_cost`; net profit = all P&L account types. Other companies' amounts are converted to the dashboard company's currency (the KPI at the period end date, the chart per month, open items and bank at today).
- The monthly chart and the Expected view always use posted journal items (their captions say so). Due-date buckets use the entry date when the due date is missing.
- Access: `account.group_account_readonly` or `account.group_account_manager` (an Invoicing-only admin has only the manager group). Invoicing users see "restricted".
- The native Aged report's columns (`period0`–`period5`, 30-day interval) open the same due-date ranges in the drawer. The native Aged total is used only when it equals the journal-items total up to its sign; otherwise journal items are used.
- Settings → Executive Dashboard → Finance report lines: override lines for Revenue / Gross profit / Net profit (period reports only) and Bank and cash (as-of reports only).
- Odoo's asset minifier dropped the spaces inside nested template literals (SVG paths broke in the minified bundle only); chart code builds strings by concatenation.
- Shell fix: the grid columns were on the high-specificity `.o_action_manager > .ed-app.o_action` selector, so the tablet/phone breakpoints never applied (244 px rail kept at 390 px). Now only `display` uses that selector.
- Review: independent `odoo-reviewer` (read-only). Blocking: native Aged buckets could not be opened; drawer totals not converted across currencies. Should-fix: aged payable sign guess, no savepoint around engine SQL, date mode not checked for override lines, bank override accounts not openable, query-count tests on Enterprise. All fixed with tests where testable locally; the reviewer's re-check confirmed each fix and found no new blocking issue. Its remaining nit (native Aged sign undetermined when the payable total is near zero) is fixed by using journal items in that case.

## Phase 3 notes

- Sales is one `get_section` call (32 queries on demo data, test limit 35); CRM 18 (limit 20).
- Invoiced sales = posted `out_invoice` + `out_refund`, `amount_untaxed_signed`, **accounting date** in the period (same date field as Finance, so the invoice counts agree); credit notes are deducted. Salespeople group the same invoices by `invoice_user_id` ("No salesperson" when empty).
- Top products: posted invoice lines (`display_type = 'product'`) by `product_id` + `product_uom_id`, credit-note quantities deducted; different units are never added.
- Top customers: `account.payment` inbound customer payments `in_process`/`paid`, `date` in the period, `amount_company_currency_signed`. Hidden (widget `null`) when the user may not read payments, e.g. a salesman without accounting rights.
- Confirmed orders: `state = 'sale'`, `date_order` in the period (user's timezone). Open quotations (`draft`/`sent`) and Orders to invoice (`invoice_status = 'to invoice'`, amount = lines' `untaxed_amount_to_invoice`) are as of today. Order amounts are converted from the order currency at the period end (today for the as-of figures).
- Recent orders: the 10 latest confirmed orders of the period; Delivery Status is the stored `delivery_status` with Odoo's own (translated) label, shown only when `sale_stock` is installed. The order drawer lists `picking_ids` with their native state; Open in Odoo opens those delivery orders (the form when there is one).
- CRM: open pipeline = active opportunities with `won_status = 'pending'` (`expected_revenue`, weighted = `prorated_revenue`), as of today; Won = `won_status = 'won'` with `date_closed` in the period; New leads = leads and opportunities created in the period. Leads without a company count in the dashboard company's currency.
- Record rules apply everywhere (a salesman sees only their own orders; test `test_salesman_sees_own_documents_only`).
- Native screens are opened with their own actions (`account.action_move_out_invoice`, `sale.action_orders`, `sale.action_quotations`, `sale.action_orders_to_invoice`, `stock.action_picking_tree_all`, `account.action_account_payments`, `crm.crm_lead_action_pipeline`, `crm.crm_lead_all_leads`), resolved at click time; a plain list/form action is used if one is missing.
- Test setup: `oh test` installs only the dependencies, so `TestSales`/`TestCrm` skip there. Run them in the kept DB after `odoo-bin -i sale_stock,crm` (see the handoff).

## Phase 4 notes

- Procurement is one `get_section` call (17 queries on demo data as admin, test limit 30); Inventory 60 as admin, 63 in the test (limit 65), of which about 35 are Odoo's own valuation (`stock.quant.value`) behind Inventory value and the Value column.
- Purchases confirmed: `purchase.order` `state = 'purchase'` with `date_approve` in the period (user's timezone), `amount_untaxed` converted from the order currency at the period end (today at most). Top suppliers and Purchases by month group the same orders (by `partner_id`; by `date_approve:month`).
- To approve: `state = 'to approve'`, as of today. The list is oldest first by `date_order` (Odoo's "Order Deadline"); Odoo stores no "waiting since" date, so the column is labelled Order deadline instead of the reference's Waiting since.
- Open purchase value (needs `purchase_stock`, hidden otherwise): confirmed orders with Receipt Status Not/Partially Received; each line's untaxed subtotal times its share not yet received (`product_qty − qty_received`).
- Transfers: `stock.picking` by `picking_type_id.code` (`outgoing` / `incoming`) in states `waiting`, `confirmed`, `assigned`. Late = scheduled before the start of today, like Inventory's own "Late" filter (the brief said "before now"; this keeps Late and Due today separate). Next 7 days = tomorrow to today + 7. Waiting = Inventory's "Waiting" filter (`confirmed`, `waiting`). Days are the user's. Late receipts in Procurement use the same definition.
- Stock report: `stock.quant` on internal locations grouped by `product_id` and `location_id.warehouse_id` (stored), 10 lines a page; warehouse, category (`child_of`), name or internal reference (`ilike`) and "Hide zero and negative stock" (`having quantity:sum > 0`, on by default) are in the query. Pages are fetched through `get_drawer('inventory.stock', …)`, so the section's access checks apply. Open in Odoo opens Odoo's stock list (`action_view_quants`) with the same filters.
- Inventory value / Value column: Odoo 19 `stock.quant.value` (`stock_account`), which Odoo restricts to Inventory Administrators; other users see neither (no error). Without `stock_account` both are hidden.
- Reserved and Available come from `reserved_quantity`; Available = On hand − Reserved, red when zero or less.
- Owl templates cannot call globals such as `String()`; compare select values as strings built with `'' + id`.

## Phase 5 notes

- People is one `get_section` call (36 queries on demo data in the test, limit 40). Current position only (no period); days are the user's.
- Headcount: active `hr.employee` of the current companies. Departments group employees on `department_id`, which in Odoo 19 lives on `hr.version` (through `_inherits`); Odoo's own `hr.department` count groups the same way. The section needs read access to `hr.employee` (Employees officer or above); other users get "restricted".
- Attendance today (`hr_attendance`, shown to Attendance officers and above): `hr.attendance` with `check_in` today, one line per employee: first check-in, last check-out, `worked_hours` of closed attendances plus the time since check-in of an open one. Checked in = distinct employees (test: equals the native `hr.attendance` employees for today); still in = an open attendance.
- Time off (`hr_holidays`, shown to Time Off officers and responsibles; a plain employee may read only their own requests, so the widget would mislead): `hr.leave` `state = 'validate'` overlapping today (`date_from`/`date_to`, counted by employee), and those starting tomorrow to today + 7. Dates shown are the requested dates.
- Shifts today (`planning`, Enterprise): published `planning.slot` overlapping today, grouped by local start–end time (largest 4 slots as tiles), first 6 shifts listed. Every Planning field is checked in `_fields` before use; the widget and its KPI are `None` without Planning.
- Fix after the Odoo.sh build (2026-09-25): grouping `planning.slot` on raw `start_datetime`/`end_datetime` raised "Granularity not set on a date(time) field". Today's shifts are now read once (`search_fetch` of start/end) and tallied by exact local time; `test_shifts_today` covers it and runs only where Planning is installed (Odoo.sh).
- Directory: 10 employees a page, department filter and name search run in the query; the status chip is today's attendance (Checked in / Checked out), On time off, or Not checked in. The "Not checked in" list of the reference belongs to Needs attention (Phase 6).
- Open in Odoo: `hr.open_view_employee_list_my`, `hr_attendance.hr_attendance_action`, `hr_holidays.hr_leave_action_action_approve_department`, `planning.planning_action_schedule_by_resource` (plain list if that id is missing), each with the dashboard's domain.
- Reference labels Morning/Day/Evening are invented; slot tiles show the time range instead.

## Owner decision (2026-09-25)

- Invoiced sales keep the **accounting date** (as built in Phase 3). Phase 6 adds one line to Definitions: Odoo's Invoice Analysis uses the invoice date, so its figures can differ from the dashboard's at month ends.

## Verify on Odoo.sh (Enterprise)

- Dark mode (only `web_enterprise` builds the dark bundle).
- Finance with `account_reports` installed (install it on the development build; the module does not depend on it): the KPIs show the P&L values for the period (compare with Accounting › Reporting › Profit and Loss); Bank & Cash equals the Balance Sheet line "Bank and Cash Accounts" per account; Receivables/Payables totals and Aged columns equal Aged Receivable / Aged Payable as of today; each "Open in Odoo" opens the report with the same dates. Check the server log for "Executive Dashboard: … engine not used" warnings: each one means that figure fell back to journal items.
- The standard Net profit expression is looked up as `account_reports.account_financial_report_net_profit0_balance`, then line code `NEP`; if neither exists in this version, set the line in Settings.
- Aged Payable sign convention (the native total is accepted only when it matches the journal-items total up to sign).
- Planning (People › Shifts today): install `planning` on the development build, publish a few shifts for today; the KPI, slot tiles and list appear, and "View all" › Open in Odoo opens the shifts (check the action id `planning.planning_action_schedule_by_resource` exists; otherwise a plain list opens).
