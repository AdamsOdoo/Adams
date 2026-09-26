# Executive Dashboard — implementation brief

Start here. This brief, the plan and the reference page are the complete
handover; nothing else from earlier sessions is needed.

1. `docs/executive-dashboard/implementation-brief.md` (this file): what to build, how to work, how to verify.
2. `docs/executive-dashboard/ux-improvement-plan-20260925.md` (revision 3): owner rules R1–R10, section contents, performance and responsive design.
3. `docs/executive-dashboard/reference/executive-360-concept.html`: **the visual source of truth**: layout, CSS tokens (light/dark, section colours), breakpoints, copy, Arabic strings, side-panel behaviour. Port its CSS and structure; do not redesign. Figures in it are invented.

## Owner decisions (final)

- One module **`executive_dashboard`**, display name **"Executive Dashboard"**, installable on any Odoo 19 database (target: Odoo.sh **Enterprise**). No customer name anywhere.
- `depends`: `['web', 'account']` only. Every other app is detected at runtime; its section/widget is hidden when missing or unreadable. Do not inherit other apps' models/views and do not reference their XML ids in data files; resolve actions at click time with `env.ref(..., raise_if_not_found=False)`.
- Sections in order: Welcome, Finance, Sales, CRM, Procurement, Inventory, People. Welcome shows **no figures**: "Greetings, <user>", date, company, search, section cards.
- No comparisons anywhere. Periods: This month, Last month, This quarter, Year to date, Custom. Inventory and People show the current position (no period selector).
- Use native values as they are, e.g. `sale.order.delivery_status` (Not Delivered / Started / Partially Delivered / Fully Delivered).
- Invoiced sales use the accounting date (`date`). Definitions (Phase 6) says in one line that Odoo's Invoice Analysis uses the invoice date and can differ at month ends.
- Bank & Cash = the accounts under the Balance Sheet line "Bank and Cash Accounts" with their balances and total. No bank/cash split, no reconciliation message.
- Stock report: warehouse (all/one), category, search by name or internal reference, one checkbox "Hide zero and negative stock" (on by default).
- People = attendance (check-in/out today), time off, headcount by department, directory, shifts (Planning).
- Direction follows the user's language through Odoo (`localization.direction`); no manual switch. Dark mode follows Odoo's user setting.
- The old modules `adams_executive_dashboard` and `adams_dashboard_finance` (and their test module) were removed from the repository on 2026-09-25 for UAT. They were never deployed to production, so no data move is needed; a staging database that still has them installed uninstalls them from Apps first.

### Owner decisions (2026-09-25, after Phase 5)

- **Access**: one level, **Administrator**, or no access (replaces User/Manager). An Administrator sees every section and figure whatever their rights in other apps (the dashboard reads its data with elevated rights), only for the companies they may use. Dashboard settings stay with Odoo system administrators. Side panels show full details; the button to the native screen appears only when the user can open it (a list: only when the user sees every record the dashboard shows). Global search covers every search model; a result opens only when the user may open it.
- **Finance report lines**: no settings. Always Odoo's standard report lines, falling back to journal items automatically.
- **Sales, recent orders**: a row opens a side panel with the order's details (customer, order date, salesperson, untaxed and total amounts, Delivery Status and Invoice Status as stored, lines with quantity ordered, delivered and invoiced). "Deliveries" lists the order's delivery orders (each opens in Inventory); the record button opens the sales order.
- **Sales, recent quotations**: a separate full-width box under Recent orders (no tabs): latest quotations (draft or sent) with reference, customer, date, validity date, amount and status; a row opens the same panel; the record button opens the quotation.
- **Button wording**: "Open record" (one record), "Open list" (filtered list), "Open report" (report); Arabic فتح السجل / فتح القائمة / فتح التقرير. The destination line under the button stays.

### Owner decisions (2026-09-25, Finance usability, before UAT)

- An account (Bank & Cash, or a receivable/payable account under "By account" in the Receivables/Payables panel) opens the native **Trial Balance** filtered on that account, fiscal year to date; without it the General Ledger unfolded on the account; journal items only without the Enterprise reports. A partner opens the **Partner Ledger** for that partner; a bucket opens the Aged report.
- Receivables and Payables each have two boxes, **Aged** and **Expected**, side by side (no tabs): total, overdue chip, one bar row per bucket with amount and share.
- Leaving for a native screen and coming back (breadcrumb, phone back arrow or browser Back) returns to the same section, period, dates, open side panel, scroll position and table filters.
- The period's dates are always shown next to the period selector, read-only; they become editable only when Custom is chosen (no layout shift).

## Data sources (verify each field with `.odoo-harness/oh src` before use)

| Widget | Source |
|---|---|
| Revenue / gross profit / net profit | Enterprise: P&L via `account_reports` engine. Community fallback: posted `account.move.line` `_read_group` by `account_id.account_type` (income, income_other, expense_direct_cost, expense, …) |
| Revenue & net profit by month | Same source, grouped by month, 12 months |
| Bank & Cash | Enterprise: Balance Sheet line "Bank and Cash Accounts" expanded by account (same options/cutoff). Fallback: accounts with `account_type = 'asset_cash'`, posted balance to today |
| Receivables / Payables · Aged | Enterprise: Aged Receivable / Aged Payable. Fallback: open posted lines on `asset_receivable` / `liability_payable`, `amount_residual` by `date_maturity` bucket |
| Receivables / Payables · Expected | Open posted lines, `amount_residual` grouped by `date_maturity`: overdue, next 7, 8–30, 31–60, later |
| Invoiced sales, salespeople | Posted `out_invoice`/`out_refund`, untaxed signed, by `invoice_user_id` |
| Top products by quantity | Posted invoice lines by `product_id` + `product_uom_id` (never sum different units) |
| Top customers by payments | `account.payment` inbound customer payments posted/in process in the period, by `partner_id` |
| Recent orders | `sale.order` confirmed, `delivery_status` as stored; drawer lists its `picking_ids` |
| Orders to invoice / open quotations | `sale.order` `invoice_status = 'to invoice'` / `state in ('draft','sent')` |
| CRM | `crm.lead` opportunities: `expected_revenue`, `prorated_revenue`, stage; new = `create_date` in period; won/lost fields as in Odoo 19 source |
| Procurement | `purchase.order` (`state`, `date_approve`, `amount_untaxed`), to approve = `state = 'to approve'`; late receipts = incoming `stock.picking` not done/cancelled with `scheduled_date` < now |
| Deliveries / receipts tiles | `stock.picking` by `picking_type_code`, `state`, `scheduled_date` |
| Stock report / inventory value | `stock.quant` `_read_group` on internal locations by product and warehouse (not `qty_available`), server-side paging; value from the Odoo 19 valuation fields |
| Headcount, directory | `hr.employee` active, by `department_id` |
| Attendance today | `hr.attendance` with `check_in` today in the user's timezone: first check-in, last check-out, `worked_hours` |
| Time off | `hr.leave` validated, today and next 7 days |
| Shifts today | `planning.slot` published, overlapping today (Enterprise; hide if missing) |
| Search | configured list of models, name search, 5 results per model, the user's current companies (elevated read); a result opens only when the user may read it |

Reusable from the old modules (read, adapt, do not copy wholesale):
`adams_dashboard_finance/models/dashboard.py` and `account_report.py` (calling the
`account_reports` engine, report options, date scoping), `adams_executive_dashboard/models/access.py`
(`check_readable`), `_scope` date logic, and the Arabic `i18n/ar.po` wording.
Do **not** reuse: the bank/cash split, comparisons, the modal dialogs, `dashboard.js` as a whole.

## Architecture

```
addons/executive_dashboard/
  __manifest__.py            name "Executive Dashboard", depends web + account, version 19.0.1.0.0
  security/                  one group: Executive Dashboard / Administrator
  models/
    dashboard.py             get_section(section, period), get_drawer(key, args), search(query), open_action(key, args)
    sections/finance.py sales.py crm.py procurement.py inventory.py people.py   one provider per widget
    settings.py              enabled sections
  static/src/                Owl: shell (nav/topbar/period), SidePanel, Kpi, Panel, LineChart, ColumnChart, AgeBar, tables; one file per section
  views/                     client action + menu, settings form
  i18n/ar.po
  tests/
```

Rules: one RPC per section; totals via `_read_group` or the report engine once per
section; only stored fields in domains/groups; lists paged on the server (10–25
rows + count); 60-second section cache keyed by company, user groups, section,
period and language (Refresh bypasses it); drawers fetched on open; browser keeps
section results per period for the session and refreshes in the background;
prefetch a section on menu hover without rendering it; charts are inline SVG.

## How to work (owner instruction, overrides heavier defaults)

- Use the `odoo-dev` skill and `.odoo-harness/oh`, but **lightly**:
  - `oh src <pattern>` before using any Odoo 19 API or field.
  - `oh test executive_dashboard` for each phase; while iterating run one test with `--tags`.
  - `oh shot` only once per phase, for that phase's section, English and Arabic, desktop; phone width in the last phase.
- **Do not** build coverage ledgers, control sweeps, paired-capture sets, reconciliation matrices or evidence bundles. Keep a short results line per phase in `docs/executive-dashboard/build-log.md` (date, commit, tests run, result).
- Tests to write (small, fast): install/uninstall; each section returns its widget keys; 2–3 figures checked against native values on demo data; an Administrator without app rights sees the same figures but no button to screens they cannot open; records of other companies are refused; a query-count limit per section.
- Local Odoo is **Community** (no Enterprise source here). Sales, Inventory, CRM, Purchase, Attendances and Time Off run locally; test there. `account_reports` and `planning` are Enterprise: code them with runtime detection plus the Community fallback, and list them under "verify on Odoo.sh" in the build log. `oh test` exit code 3 (blocked) for Enterprise-only parts is expected, not a failure to chase.
- Independent review: run the `odoo-reviewer` agent once after Finance (money) and once at the end.
- This repository is public: example data only, no customer data, credentials or Enterprise source.
- Work on a feature branch; never push to `main`, `staging` or `test`. Commit and push at the end of every phase.

## Phases (one session each; stop and hand over at the end of each)

| # | Scope | Done when |
|---|---|---|
| 1 | Module skeleton, security, client action and menu, settings, shell (nav, topbar, period selector, section colours, light/dark, RTL, breakpoints), Welcome, side panel, `get_section` framework and caches | Installs on a fresh DB; Welcome and empty sections render EN/AR; access test passes |
| 2 | Finance (figures, chart, Bank & Cash, Receivables/Payables aged and expected) | Figures match native on demo data; reviewer pass; Enterprise items listed for Odoo.sh |
| 3 | Sales and CRM | Delivery Status shows the native value; drawers open delivery orders and opportunities |
| 4 | Procurement and Inventory (stock report with filters and paging) | Stock report paging and filters run server-side; zero/negative filter works |
| 5 | People (attendance, time off, shifts, departments, directory) | Attendance matches `hr.attendance` for today; Planning hidden when absent |
| 6 | Search, Needs attention, Definitions, performance tests, Arabic review, phone check; final reviewer pass (old modules already removed) | Section payload < 300 ms and drawer < 200 ms on demo data; owner checklist for the Odoo.sh build written |

At the end of each phase: update `.odoo-harness/HANDOFF.md` (under 40 lines) with the
next phase's exact first step, append the build-log line, commit, push.
