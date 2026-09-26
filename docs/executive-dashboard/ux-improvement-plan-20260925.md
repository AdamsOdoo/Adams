# Executive Dashboard — redesign plan (2026-09-25, revision 3)

Status: **agreed direction, not implemented.** Revision 3 incorporates the
owner's second review. Each change against the approved HTML is recorded as a
deviation (D19 onward) before implementation.

Reference design: `reference/executive-360-concept.html`
(published copy: https://claude.ai/artifact/3JGeUFdrqBkgAgrDgkRbEY). Example
figures only.

## 1. Product rules (owner decisions)

| # | Rule |
|---|---|
| R1 | **One module, `executive_dashboard`, named "Executive Dashboard"**, installable on any Odoo 19 database. No customer name in code, data or UI. |
| R2 | Navigation: **Welcome, Finance, Sales, CRM, Procurement, Inventory, People**. A section appears only when its app is installed and the user may read its data. |
| R3 | **Welcome** shows no figures: "Greetings, <name>", date, company, search and the section cards. |
| R4 | **No comparisons** (no deltas, no "vs" labels). |
| R5 | Periods: This month, Last month, This quarter, Year to date, Custom. Inventory and People show the current position and have no period selector. |
| R6 | Direction follows the user's language through Odoo's localization. |
| R7 | Detail opens in a side panel; every figure opens its records; "Open in Odoo" opens the native screen with the same filters. |
| R8 | Search covers every record the user may read, not the dashboard's filters. |
| R9 | Use native Odoo values wherever they exist (e.g. the sales order **Delivery Status** field, as is). |
| R10 | Fast and smooth on computer, iPad and iPhone (sections 4 and 5). |

## 2. Sections

### Finance
Revenue, Gross profit, Net profit, Bank & Cash, Receivables, Payables ·
Revenue & net profit by month · **Bank & Cash**: the accounts under the Balance
Sheet line "Bank and Cash Accounts" with their balances and total, nothing
else · **Receivables** and **Payables**, each with *Aged* and *Expected* (by
due date: overdue, next 7 days, 8–30, 31–60, later).

### Sales
Invoiced sales, Confirmed orders, Open quotations, Orders to invoice ·
Invoiced sales by month · Salespeople by invoiced sales · Top products by
quantity · Top customers by payments received · Recent orders with the order's
own **Delivery Status** field (`sale_stock`: Not Delivered, Started, Partially
Delivered, Fully Delivered) shown exactly as Odoo shows it; clicking it lists
that order's delivery orders.

### CRM
Open pipeline, Weighted pipeline, New leads, Won · Pipeline by stage ·
Pipeline by salesperson · Closing soonest.

### Procurement
Purchases confirmed, To approve, Late receipts, Open purchase value · Waiting
for approval · Late receipts · Top suppliers by purchase value · Purchases by month.

### Inventory
Inventory value, Late deliveries, Deliveries due today, Receipts due today ·
Deliveries (late, today, next 7 days, waiting) and Receipts (late, today, next
7 days, waiting) · **Stock report** with warehouse, category and
name/internal-reference filters and one checkbox **"Hide zero and negative
stock"** (on by default).

### People
Tracks attendance, time off, headcount, the directory and shifts.
- Figures: Headcount, **Checked in today**, On time off today, Shifts today.
- **Attendance today** (Attendances app): each employee's first check-in, last check-out, worked hours and whether they are still in.
- **Time off**: today and the next 7 days, with leave type.
- **Shifts today** (Planning, Enterprise): by time slot and role.
- **Headcount by department** (a department opens its employees) and **Employees directory** (search, department filter).
Widgets whose app is not installed are hidden.

## 3. One module, plug and play

- `executive_dashboard` depends only on `web` and `account` (Invoicing is present in practically every database). All other apps (`sale`, `sale_stock`, `crm`, `purchase`, `stock`, `hr`, `hr_attendance`, `hr_holidays`, `planning`, `account_reports`) are **detected at runtime** (`'sale.order' in env`, `env.ref(..., raise_if_not_found=False)`).
- Consequences of one module: it does not extend other apps' models or views and does not reference their XML ids in data files; actions are resolved when clicked. This keeps installation and uninstallation clean on any database.
- Financial statements: Enterprise `account_reports` engines when installed (Balance Sheet, P&L, aged reports); on Community, the same figures from posted journal items with the equivalent account types.
- Settings screen: which sections are enabled, and which report lines are used when a localization renames them.
- Replacing the current `adams_executive_dashboard` + `adams_dashboard_finance` on this database: install `executive_dashboard`, run a one-time data move (settings, saved views, report mappings), uninstall the old modules. Tested on a staging copy first.

## 4. Speed and smoothness

Goal: switching sections feels instant; first data appears in under a second
on a production-size database; nothing freezes while loading.

### Backend (server)
1. **One request per section.** `get_section(section, period)` returns every widget of that section in a single call, instead of one call per widget (the current dashboard makes many separate calls).
2. **Totals are computed in the database, not in Python.** Every figure uses grouped SQL through `_read_group` or the native report engine, run once per section. No Python loops over records, and no per-account fallback calls (the current bank/cash code can call the report engine once per account).
3. **Only stored, indexed fields.** Example: the stock report groups `stock.quant` by product and warehouse instead of reading `qty_available` (computed per product, slow). Delivery status is a stored field. Product search uses Odoo's trigram index on the name.
4. **Paging on the server.** Lists return 10–25 rows plus a total count; filters and search run in SQL.
5. **Short-lived cache.** Section results are kept 60 seconds per company, user rights, section, period and language. Repeated opens and back-and-forth navigation read from the cache; the Refresh button bypasses it.
6. **Drawers load on demand** with only the rows they show.
7. **Search in one request:** up to 5 results per model across all models, with record rules applied.
8. **Performance tests** with limits: maximum number of SQL queries per section, and time limits (section under 300 ms and drawer under 200 ms on a staging-size copy). A slow widget fails the build.

### Frontend (browser)
1. **Instant frame.** Navigation, title and empty cards appear immediately; each widget shows a placeholder and fills in when its data arrives.
2. **Browser cache per section and period** for the session: returning to a section shows the last result at once and refreshes it quietly in the background.
3. **Prefetch.** While the user is on Welcome or pointing at a section in the menu, that section's data is requested in advance. Nothing is shown until the section is opened, so Welcome stays private.
4. **Cancel stale requests.** Switching period or section drops requests the user no longer needs.
5. **Light code.** Charts are small inline SVG (no chart library to download); the dashboard code is split into small components and loaded only when the dashboard opens.
6. **Search** waits 250 ms after typing stops, then shows grouped results.

## 5. Screen sizes

| Width | Device | Layout |
|---|---|---|
| ≥ 1200 px | Computer | Full sidebar with labels; 12-column grid; up to 6 figures per row |
| 768–1199 px | iPad, small laptop | Icon-only sidebar; 3 figures per row; panels pair up or go full width |
| < 768 px | iPhone | Section tabs scroll across the top; 2 figures per row; one panel per row; tables turn into cards; the side panel opens full screen |

**No empty gaps:** panels in the same row stretch to equal height; paired
panels are designed with the same number of rows (for example top-5 lists side
by side); charts grow to fill their card; on very wide screens content stops at
1,680 px and is centred.

## 6. Colour

Each section has its own colour for its menu icon, card icons and page wash:
Finance teal, Sales blue, CRM violet, Procurement amber, Inventory green,
People rose. Status colours (red, amber, green) are kept separate and always
come with a label. Figures and text stay in neutral ink. Dark mode has lighter
versions of the same colours.

## 7. Order of work
1. Record deviations D19+; create `executive_dashboard` with the shell, Welcome, side panel, period selector, section cache and `get_section`.
2. Finance, Sales, Inventory (stock report), then CRM, Procurement, People.
3. Search, performance tests, Arabic, dark mode, iPad and iPhone checks.
4. Data move from the old modules on a staging copy; owner acceptance.
