# Executive Dashboard — redesign plan (2026-09-25, revision 2)

Status: **agreed direction, not implemented.** Revision 2 incorporates the
owner's review of the first reference design. Each change against the approved
HTML is recorded as a deviation (D19 onward) before implementation.

Reference design: `reference/executive-360-concept.html`
(published copy: https://claude.ai/artifact/3JGeUFdrqBkgAgrDgkRbEY). Example
figures only.

## 1. Product rules (owner decisions)

| # | Rule |
|---|---|
| R1 | The product is **Executive Dashboard**, reusable for any customer. No customer name in module names, titles, code, data or UI. |
| R2 | Navigation order: **Welcome, Finance, Sales, CRM, Procurement, Inventory, People**. |
| R3 | **Welcome** shows no figures (privacy when the screen is visible to others): greeting, date, company and the sections the user can open. |
| R4 | **No comparisons anywhere** (no deltas, no "vs prior period", no sparklines). |
| R5 | Periods: **This month, Last month, This quarter, Year to date, Custom** (from/to dates). Balances (bank, receivables, payables, stock) are always as of today. |
| R6 | Layout direction follows the **user's language** in Odoo (Arabic → right to left) using Odoo's standard localization. No manual switch. |
| R7 | Detail opens in a **side panel**; every figure opens the records behind it; "Open in Odoo" goes to the native screen with the same filters. |
| R8 | **Search** covers the whole database the user may read (not the dashboard's filters or displayed rows). |
| R9 | Loading must be fast: the page frame appears immediately, each widget loads independently, drawers load on demand. |

## 2. Sections

### Welcome
Greeting with the user's name, today's date, company logo and name; one card
per section the user has access to (hidden when the app is not installed or the
user lacks rights). Search is available; no figures.

### Finance
- Figures: Revenue, Gross profit (with margin %), Net profit, **Bank & Cash**, Receivables, Payables.
- Revenue & net profit by month (12 months; the current month drawn dashed as month-to-date).
- **Bank & Cash**: the accounts under the Balance Sheet's "Bank and Cash Accounts" line, each with its balance, and the line total. Nothing else: no bank/cash split, no reconciliation message, no extra calculation. Clicking an account opens its General Ledger.
- **Receivables**: two views, *Aged* (not due, 1–30, 31–60, 61–90, over 90 days) and *Expected* (open customer invoices by due date: next 7 days, 8–30, 31–60, 61–90, later). Source: Aged Receivable report / open posted invoices' residual amounts.
- **Payables**: the same two views for vendor bills.

### Sales
- Figures: Invoiced sales, Confirmed orders, Open quotations, Orders to invoice.
- Invoiced sales by month.
- **Salespeople by invoiced sales**, **Top products by quantity sold** (per unit of measure), **Top customers by payments received** in the period.
- Recent orders with **delivery status** (rule below). The status opens that order's delivery orders.

**Delivery status rule.** Odoo's native `delivery_status` is `full` when every
picking is done *or cancelled* (`sale_stock/models/sale_order.py`,
`_compute_delivery_status`). The dashboard shows **Delivered** only when every
outgoing delivery order of the order is **done** and none was cancelled with
quantity left; otherwise **Partially delivered**, **Not delivered** or **Late**
(a delivery order past its scheduled date). Returns are excluded.

### CRM (new)
- Figures: Open pipeline (expected revenue), Weighted pipeline (by probability), New leads, Won (count and value) in the period.
- Pipeline by stage (value and count per stage; a stage opens its opportunities).
- Opportunities closing soonest, by expected revenue.
- Pipeline by salesperson.

### Procurement
- Figures: Purchases confirmed, Purchase orders to approve, Late receipts, Open purchase value.
- Waiting for approval (oldest first), Late receipts, Top suppliers by purchase value.

### Inventory
- Figures: Inventory value, Late deliveries, Deliveries due today, Receipts due today.
- Delivery status tiles: Late, Due today, Next 7 days, Waiting for stock (each opens the delivery orders).
- **Stock report**: filters for **warehouse** (all or one), **product category**, and **search by name or internal reference**; columns: reference, product, category, warehouse, on hand, reserved, available, unit, value; server-side paging; a row opens the product's stock by location.
- Removed: "Below reorder point".

### People
- Figures: Headcount, **On shift now**, On leave today.
- **On shift now**: employees whose Planning shift covers the current time (Enterprise Planning); if Planning is not installed, employees checked in (Attendances).
- **Headcount by department**: a department opens its employees.
- **Employees directory**: search by name, filter by department; a row opens the employee.
- Removed: Open positions, Contracts ending.

### Quick access
Search (whole database), Needs attention (ranked items across sections),
Definitions. Each opens the side panel.

## 3. Architecture and refactor (for R1 and R9)

### Module family (plug and play)
| Module | Depends | Provides |
|---|---|---|
| `executive_dashboard` | `web` | Shell, Welcome, side panel, search, settings, access groups, widget registry |
| `executive_dashboard_account` | core, `account` (auto-install) | Finance widgets from native reports; Enterprise `account_reports` used when present |
| `executive_dashboard_sale` | core, `sale_management`, `sale_stock` (auto-install) | Sales widgets, delivery status rule |
| `executive_dashboard_crm` | core, `crm` (auto-install) | CRM widgets |
| `executive_dashboard_purchase` | core, `purchase` (auto-install) | Procurement widgets |
| `executive_dashboard_stock` | core, `stock` (auto-install) | Inventory widgets and stock report |
| `executive_dashboard_hr` | core, `hr` (auto-install); Planning/Attendance optional | People widgets |

A customer installs `executive_dashboard`; the bridge for each installed app
installs itself. Sections without their app never appear.

**Renaming.** Odoo cannot rename an installed module. Recommended: publish the
new modules, add a one-time migration for this database (settings, saved
views, report mappings), then uninstall the old `adams_*` dashboard modules.
**Owner decision needed** before implementation (alternative: keep the
technical names and change only the displayed names).

### Backend
- One call per section, `get_section(section, period)`, returns every widget's payload; each widget is a small provider registered by its bridge module.
- Aggregates use `_read_group` / native report engines; no per-record Python loops for totals; lists are limited and paged on the server.
- Each provider checks access and returns `restricted` / `not_installed` states instead of failing the section.
- Drawer content is fetched only when a drawer opens.
- Global search: `name_search`-style lookups on a configurable list of models, 5 results per model, record rules applied, 250 ms debounce.
- Performance budget (checked by `test_performance` query counts and timings on a staging-size dataset): section payload under 300 ms; drawer under 200 ms; search under 300 ms.

### Frontend
- One Owl component per widget with its own skeleton, error and empty state; the frame and navigation render before any data.
- Section payloads are cached per period in the browser for the session and refreshed in the background (stale while revalidate); changing period does not rebuild the page.
- CSS uses logical properties only; direction comes from Odoo (`localization.direction`); all strings go through `_t` with Arabic translations.
- Dark mode follows Odoo's user setting (Enterprise).

## 4. Order of work
1. Owner decision on module renaming; record deviations D19+.
2. Core refactor: registry, `get_section`, side panel, Welcome, period selector, removal of comparisons.
3. Finance (Bank & Cash from the Balance Sheet, expected receivables/payables).
4. Sales (delivery status rule, three rankings) and Inventory (stock report).
5. CRM, Procurement, People (on shift now, directory).
6. Global search, performance budget tests, Arabic/RTL, dark mode on Odoo.sh.
