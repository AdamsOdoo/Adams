# Executive Dashboard — build log

One line per phase (date, commit, tests run, result), then that phase's notes.

| Phase | Date | Commit | Tests | Result |
|---|---|---|---|---|
| 1 | 2026-09-25 | `c1b9a3a2` | `oh test executive_dashboard`: 12 run, 12 passed (Community, demo). `oh shot /odoo/executive` EN + AR desktop: 2/2 ok. Extra local browser check at 1440 / 1024 / 390 px: no horizontal overflow | **completed** locally; dark mode not verified (Enterprise) |
| 2 | 2026-09-25 | `e8fa1abc` | `oh test executive_dashboard`: 23 run, 23 passed (Community, demo). `oh shot /odoo/executive` EN + AR: 2/2 ok. Local browser check of Finance at 1440 / 1024 / 390 px, EN + AR: no console errors, no horizontal overflow, drawers and Open in Odoo work. Independent `odoo-reviewer` pass + re-check | **completed** locally; Enterprise report path **not verified** (see below) |
| 3 | 2026-09-25 | `c74f63f` | `oh test executive_dashboard`: 23 run, 23 passed, Sales/CRM classes skipped (only `web` + `account` installed). Kept DB + `sale_stock,crm`: 37 run, 37 passed (Sales 9, CRM 5). `oh shot /odoo/executive` EN + AR: 2/2 ok. Local browser check of Sales and CRM at 1440 / 1024 / 390 px, EN + AR: 12/12, no console errors, no horizontal overflow, order and opportunity drawers open, Open in Odoo opens the delivery order and the opportunity | **completed** locally; no Enterprise-only part in this phase |
| 4 | 2026-09-25 | `912c1e8` | `oh test executive_dashboard`: 23 run, 23 passed, Sales/CRM/Procurement/Inventory classes skipped (only `web` + `account` installed). Kept DB + `sale_stock,crm,purchase_stock,stock_account`: 51 run, 51 passed (Procurement 6, Inventory 8). `oh shot /odoo/executive` EN + AR: 2/2 ok. Local browser check of Procurement and Inventory at 1440 / 1024 / 390 px, EN + AR: 12/12, no console errors, no horizontal overflow; stock report hide checkbox, paging, search, product drawer, tiles, order drawers and month column work. Payload on demo data: Procurement 27 ms, Inventory 94 ms, a stock page 62 ms | **completed** locally; no Enterprise-only part in this phase |
| 5 | 2026-09-25 | `e3ae310` | `oh test executive_dashboard`: 23 run, 23 passed, app-specific classes skipped (only `web` + `account` installed). Kept DB + `sale_stock,crm,purchase_stock,stock_account,hr_attendance,hr_holidays`: 59 run, 59 passed (People 8). `oh shot /odoo/executive` EN + AR: 2/2 ok. Local browser check of People at 1440 / 1024 / 390 px, EN + AR: 6/6, no console errors, no horizontal overflow; direction follows the language; directory paging and search, attendance, employee and department drawers, and Open in Odoo work; Planning panel hidden (not installed). Payload on demo data: People 112 ms (cold), a directory page 16 ms | **completed** locally; Planning (Enterprise) **not verified** |
| Owner decisions | 2026-09-25 | `7677ff0` | `oh test executive_dashboard`: 26 run, 26 passed, app-specific classes skipped. Kept DB + `sale_stock,crm,purchase_stock,stock_account,hr_attendance,hr_holidays`: 66 run, 66 passed. Local browser check of Sales at 1440 px, EN + AR: both boxes, order and quotation panels, Deliveries › delivery order in Inventory, Open record › sales order / quotation; no console errors, no horizontal overflow | **completed** locally; Enterprise report path and Planning still **not verified** |

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

## Owner decisions (2026-09-25, after Phase 5; module 19.0.1.5.0)

- Access: the User/Manager groups are replaced by one group, **Executive Dashboard / Administrator** (admin and superuser are members on install). Without it the dashboard is refused, including for system administrators; Settings stays for `base.group_system`. No migration moves members of the old groups (the module has not been deployed beyond development builds); on a development build, add users to Administrator after the update.
- Elevated read: `get_section`, `get_drawer`, `open_action` and `global_search` validate `env.companies` with the user's rights (an unauthorized company raises), then run `sudo()`. Every query already filters on `scope['companies']`; records fetched by id go through `_check_company` (company or companies must be among the user's current ones). The "restricted" status and the per-app group gates (Finance accounting groups, People Attendance/Time Off groups, Inventory value for Inventory administrators) are gone.
- Native screens: `get_drawer` builds the drawer's action (and each row's) and keeps it only when `_open_info` allows it with the user's own rights: a record when the user may read it, a report when the user may read `account.report`, a list only when the user's own `search_count` of the domain equals the elevated one (so the screen never shows less than the panel). The action then carries `kind` (record / list / report), which names the button. `open_action` refuses the same way. The Inventory stock list and People directory buttons use the same list rule (`can_open` in the section payload). This builds each drawer's action once more; on Enterprise the Finance report actions call the engine's `get_options` again.
- Search: every search model, `company_id` in the user's current companies (or empty); each result carries `can_open` (the user's own read access); others are shown without a link.
- Finance report-line settings and their four `res.company` fields removed; `_fin_expression` and the bank line use Odoo's standard records only, with the journal-items fallback as before.
- Sales: drawer `sales.order` = order or quotation details (customer, order date, validity date for quotations, salesperson, status, `delivery_status` and `invoice_status` with Odoo's labels, untaxed/total, first 50 non-section lines with `product_uom_qty`, `qty_delivered`, `qty_invoiced`); its button opens the order (`sale.action_orders`) or quotation (`sale.action_quotations`) form. Drawer `sales.deliveries` lists `picking_ids`; each row opens its delivery order (`sales.picking`, only a picking of that order). Widget `quotations`: the 10 latest `draft`/`sent` orders by `date_order`, as of today like the Open quotations figure, amount untaxed like Recent orders.
- Query counts dropped under elevated rights (no record-rule queries): Sales 31, CRM 14, Procurement 17, Inventory 63; limits unchanged.

## Verify on Odoo.sh (Enterprise)

- Dark mode (only `web_enterprise` builds the dark bundle).
- Finance with `account_reports` installed (install it on the development build; the module does not depend on it): the KPIs show the P&L values for the period (compare with Accounting › Reporting › Profit and Loss); Bank & Cash equals the Balance Sheet line "Bank and Cash Accounts" per account; Receivables/Payables totals and Aged columns equal Aged Receivable / Aged Payable as of today; each "Open report" opens the report with the same dates. Check the server log for "Executive Dashboard: … engine not used" warnings: each one means that figure fell back to journal items.
- The standard Net profit expression is looked up as `account_reports.account_financial_report_net_profit0_balance`, then line code `NEP`; if neither exists in this version, the figure falls back to journal items (the report-line settings were removed by owner decision).
- Aged Payable sign convention (the native total is accepted only when it matches the journal-items total up to sign).
- Planning (People › Shifts today): install `planning` on the development build, publish a few shifts for today; the KPI, slot tiles and list appear, and "View all" › Open list opens the shifts (check the action id `planning.planning_action_schedule_by_resource` exists; otherwise a plain list opens).

## Odoo.sh build fixes (2026-09-25)

- The first Enterprise build ran 196 tests: 2 failed, 2 errors. All were test assumptions that only hold on Community; no figure was wrong.
  - Finance: with `account_reports` the Aged buckets are the native columns (`period0`, `period1`, ...), not `not_due`/`d30`/...; the tests now accept either key for the same range.
  - People: which HR groups grant Attendances rights differs between databases; the test now checks the rule itself (button shown only when the user's own rights cover every listed record, otherwise `open_action` is refused).
  - CRM: New leads counts active leads created in the period (Odoo archives lost ones); the test now compares with the native count instead of a fixed 3.
- "aged report engine not used (UnsupportedScope)" warnings: this is the designed fallback to journal items. Each fallback now states its reason and is logged at INFO; a native total that differs from the open journal items stays a WARNING (money mismatch), as do engine and access errors.
- Not ours: `bus.websocket` `KeyError: 'record'` (Odoo `sendone_wrapper` test helper with Enterprise `ai_fields._create`) during the old `adams_dashboard_finance` browser tests; goes away when that module is uninstalled in Phase 6.
- Local: `oh test executive_dashboard` 26 passed; kept DB with all Community apps 66 passed, no warnings.

## Finance usability and UAT preparation (2026-09-25, 19.0.1.6.0)

- Owner requests: accounts open the Trial Balance (not journal items); Receivables and Payables split into Aged and Expected boxes with bar rows; returning from a native screen restores the dashboard as it was; period dates always visible, editable only for Custom. Decisions recorded in the brief.
- Trial Balance: `account_reports.trial_balance_report` with `filter_search_bar` = account code, fiscal year to date; accepted only when the report echoes the option (`_fin_options`), else the General Ledger unfolded on the account (`caret_option_open_general_ledger`, as the old module did on Odoo.sh), else journal items. Partner rows open the Partner Ledger (`partner_ids`); buckets open the Aged report. The Receivables/Payables panel lists "By account" and "By partner".
- Return: `useSetupAction({getLocalState})` keeps page, period, dates, panel, scroll, section results and stock/directory filters for Odoo's breadcrumb and the phone back arrow; for the browser's Back button the view (no figures) is kept in `sessionStorage` for 10 minutes, used once.
- Removed from the repository: `adams_executive_dashboard`, `adams_dashboard_finance`, `test_addons/adams_dashboard_native_tests` and the old-dashboard docs (history in git). Production (`main`) never had them.
- Local: `oh test executive_dashboard` 27 passed (5 skipped: apps not installed); kept DB with all Community apps 67 passed, no warnings. Browser at 1440 / 1024 / 390 px, EN + AR: no console errors, no horizontal overflow, period bar does not move when Custom is chosen, breadcrumb / phone arrow / browser Back return to the same section, panel and scroll.
- Verify on Odoo.sh: the Trial Balance opens filtered on the account (else the General Ledger on it); the Partner Ledger opens on the partner; Aged Receivable/Payable totals as before.
- Independent review (`odoo-reviewer`, read-only) of `c4c0621`: 5 defects and 5 smaller issues, all fixed:
  - `test_drawers` asserted journal items where Enterprise now opens the Partner Ledger (Enterprise build would fail); the journal-item checks now run only without the Enterprise reports.
  - `_open_info` read an action context that `ir.actions.client` stores as text; it now parses it. The General Ledger fallback is built by the dashboard (`unfolded_lines`), no longer through `caret_option_open_general_ledger`.
  - The Trial Balance has several column groups; `_fin_options(single_group=False)` accepts it. The test checks the action is the Trial Balance with the account code in `filter_search_bar`. Known limit: the search matches line names, so a code that begins another account's code lists both.
  - Browser-Back memory: written only when a dashboard button opens a native screen, always consumed on the next open, removed otherwise (menu switch, Welcome). A menu reopen lands on Welcome (checked).
  - Stock/directory filters stored when the section unmounts (plain copies) and reloaded with their page; dates cleared while a new period loads; the account panel names its real destination; box titles are whole translatable strings; test for another company's receivable account.
- Local after the fixes: 67 passed, no warnings; browser: breadcrumb, phone arrow and browser Back restore section, panel and scroll at 1440 / 1024 / 390 px; menu switch reopens on Welcome; stock filters survive a section switch; no console errors.

## UAT candidate

- Branch `uat/executive-dashboard` (`4be9282`), built on `origin/staging` (`a653e81`) like earlier stagings: `executive_dashboard` from `73cfd09` added, `adams_executive_dashboard` and `adams_dashboard_finance` removed, `adams_base` and `adams_shopify` unchanged. It is a fast-forward of `staging`; the owner moves `staging` to it (Odoo.sh or GitHub), after uninstalling the old dashboards on the staging database if they are installed. Then install Executive Dashboard from Apps and follow `uat-checklist.md`.

## Owner feedback on staging (2026-09-26, 19.0.1.7.0)

Eight points from the owner's staging review; each point, the decision and its test are tracked in `owner-feedback-20260926.md`.

- Bank & Cash lists every active bank/cash account (zero balances and accounts without entries included); the card list scrolls after about six rows so it no longer stretches the chart beside it (all card lists do the same).
- Year to date is the default period. Switching periods keeps the figures on screen (dimmed) until the new ones arrive; after a section loads, its other periods load in the background one after the other.
- Receivables and Payables: one box each with an Aged / Expected switch. The Overdue chip counts past-due invoices (bills) only; unapplied credits / advances are a separate chip; shares are hidden when buckets mix signs; a negative net explains itself.
- Balances follow the period end (`scope['as_of']` = period end, never after today): Bank & Cash, Receivables, Payables, their drawers and native screens (Balance Sheet, Aged report, Partner Ledger, Trial Balance). Journal-item figures at an earlier date add back the matches made after it (`account.partial.reconcile.max_date`), as the Aged reports do.
- Journal items and the Aged reports' default Account filter agree: Non Trade receivable/payable accounts (e.g. a VAT receivable) are left out. The native Aged total is now always the figure shown; a remaining difference from the journal items is shown in the box.
- Account rows open the Trial Balance directly; the "Latest journal items" panel is removed.
- Sales: Top customers by collections (money received: payments, bank statement lines and journal entries on a bank/cash account), replacing payments only.
- Dark mode: unchanged by design; the dashboard follows Odoo's own colour scheme (see the feedback note).
- Local: `oh test executive_dashboard` 31 passed (5 skipped: apps absent); kept DB with sale_stock, crm, purchase_stock, stock_account, hr_attendance, hr_holidays: 72 passed. Browser (1440 px, EN + AR): Year to date selected on open, Last month shown in 45 ms with no placeholder, drawer values aligned, bank list capped at 300 px with scroll, chart gap 19 px, account row opens its native screen, no console errors.
- Verify on Odoo.sh (Enterprise): Aged Receivable / Payable totals and the difference note, Aged report / Partner Ledger / Trial Balance / Balance Sheet opening at the period end, dark mode with the owner's preference.
- Independent review (`odoo-reviewer`, read-only) of `b52221a`: 9 findings, all fixed:
  - Collections counted the receivable side, so a write-off, discount or withholding settled with a payment counted as money received; now the money side is measured (payment amount; bank/cash lines of other entries, shared between the entry's customers). Test with a write-off and a refund paid out.
  - A post-dated payment matched today hid the invoice at today; matches dated after the balance date are now always added back (one cheap check first). Test added.
  - The native Aged total was re-signed from the journal total; both Aged reports show amounts owed positive, so it is used as it is (verify payables on Odoo.sh).
  - Rows sharing one report check are still validated one by one (`_check_finance_account`); Bank & Cash rows that cannot open are plain rows (`can_open`), also on the card.
  - Expected first bucket renamed "Past due (net)"; unused net overdue KPIs dropped; open-item counts no longer include add-backs; the journal-items fallback of a bucket uses today's ranges and says "today"; the difference note is one translatable sentence; due dates formatted.
- Query limit for the Finance section: 17 on Community (one check for later matches, one account-button check).
- Background period loading computes up to four more periods per visited section (sequential, silent): an accepted cost of instant switching.
- Local after the fixes: `oh test executive_dashboard` 32 passed (5 skipped); kept DB with all Community apps 73 passed.

## Owner feedback on staging, round 2 (2026-09-26, 19.0.1.8.0)

Nine points; each point, the decision and its test are tracked in `owner-feedback-20260926.md` ("Round 2").

- Receivables / Payables: the share next to Overdue is removed. The Overdue chip and the credits chip open their items by partner (`finance.open_items` with `side`); Overdue opens the Aged report, credits their journal items (the Aged report does not separate them).
- "View all" on Salespeople, Top products, Top customers (`sales.salespeople`, `sales.products`, `sales.customers`) and Top suppliers (`procurement.suppliers`): every one of the period; cards stay top 5.
- Side-panel lists page: 25 rows, then "Show more" (`get_drawer(key, args, limit)`, 25 to 1000; `more: {shown, count}`). The native "Open list" still shows everything. Quotations stay as of today (owner decision).
- Tables with fixed column widths (Sales, Procurement, CRM) so the Date column no longer moves with the period; card lists and side panels never scroll sideways.
- Accounts open the General Ledger with the account unfolded (balance accounts: fiscal year start to the balance date; P&L accounts: the period), else their journal items. The Trial Balance is no longer used.
- Revenue, Gross profit and Net profit open their own panel (`finance.profit`): accounts grouped by type with subtotals, adding up to the figure, with a note when the native P&L figure differs. The chart keeps the monthly panel.
- New app icon (gauge). Native lists opened from the dashboard keep the dashboard's title in the breadcrumb (`display_name`).
- Local: `oh test executive_dashboard` 34 passed (5 skipped); kept DB with sale_stock, crm, purchase_stock, stock_account, hr_attendance, hr_holidays: 78 passed. Browser (1440 px, EN + AR): chips, three profit panels, View all, Show more (25 → 49 of 49), Date column at the same x for every period, no sideways scroll, account opens its screen, no console errors.
- Verify on Odoo.sh (Enterprise): the General Ledger opens on the account (unfolded, searched on its code) at the period end.
- Independent review (`odoo-reviewer`, read-only) of `7d5900b`: no blocking findings. Fixed: the General Ledger no longer gets a search on the account code (it could hide the account's entries; the account is unfolded instead); salespeople ties are ranked by id so the card and "View all" agree; fixed-width table cells clip their second line with an ellipsis; stale Trial Balance comments. Accepted: a P&L account's General Ledger may add an opening balance from the fiscal year start (the listed entries are the period's); per-row checks of account buttons without Enterprise and the id list behind Top customers' "Open list" (bounded by the period's collections).
- Local after the fixes: 34 passed (5 skipped); all Community apps 78 passed.
