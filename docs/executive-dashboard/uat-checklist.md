# Executive Dashboard — staging UAT

Module `executive_dashboard` ("Executive Dashboard"), version 19.0.1.6.0. It replaces the
old `adams_executive_dashboard` and `adams_dashboard_finance`, which are no longer in
the repository.

## Before testing (owner, on Odoo.sh)

1. If the staging database has the old dashboards installed, uninstall **Adams Dashboard
   Finance** first, then **Adams Executive Dashboard** (Apps, remove the "Apps" filter,
   search "Adams"). Do this before the new code reaches staging: without their code they
   can no longer be uninstalled cleanly.
2. Put the UAT candidate on `staging` (see the build log, "UAT candidate").
3. When the build is green, install **Executive Dashboard** from Apps.
4. Give testers access: Settings › Users › the user › Executive Dashboard: **Administrator**.
   Settings of the dashboard are for system administrators.
5. Test in English and in Arabic (user preferences › language), on a computer, an iPad
   and a phone.

## Checks

Mark each line OK or write what you saw.

### General
- [ ] The menu "Executive Dashboard" opens Welcome: "Greetings, <name>", date, company, section cards, no figures.
- [ ] Sections in order: Welcome, Finance, Sales, CRM, Procurement, Inventory, People. A section whose app is not installed is not shown.
- [ ] Period: This month, Last month, This quarter, Year to date, Custom. The dates next to it always show the period on screen and are read-only; choosing Custom makes them editable and nothing moves.
- [ ] Open any record, list or report from a side panel, then come back (breadcrumb, phone back arrow or browser Back): same section, period, dates, open panel and scroll position.
- [ ] Arabic: the whole page is right-to-left and the texts are Arabic.
- [ ] Dark mode (user preferences) looks right.
- [ ] Search (`/` or the search button) finds customers, products, orders, invoices, employees.

### Finance
- [ ] Revenue, gross and net profit for This month match Accounting › Reporting › Profit and Loss for the same dates.
- [ ] Bank & Cash lists the accounts of the Balance Sheet line "Bank and Cash Accounts" with the same balances and total.
- [ ] A bank account opens its detail; "Open report" opens the **Trial Balance** filtered on that account.
- [ ] Receivables and Payables each show two boxes, **Aged** and **Expected**; totals match Aged Receivable / Aged Payable.
- [ ] "Details" of Receivables shows **By account** and **By partner**; an account opens the Trial Balance for it, a partner opens the **Partner Ledger** for that partner.

### Sales
- [ ] Recent orders show the Delivery Status exactly as on the order; a row opens the order panel; "Deliveries" lists its delivery orders.
- [ ] Recent quotations is its own box under Recent orders.

### CRM, Procurement, Inventory, People
- [ ] CRM pipeline and weighted pipeline match CRM › Pipeline (list, sum).
- [ ] Purchases to approve and late receipts match Purchase and Inventory.
- [ ] Stock report: warehouse, category and search filters; "Hide zero and negative stock" on by default; paging.
- [ ] People: checked in today matches Attendances; time off, departments, directory; Shifts today when Planning is installed.

## Known limits of this candidate

- Not built yet: Needs attention, Definitions, search model settings, performance tests (Phase 6).
- Invoiced sales use the accounting date; Odoo's Invoice Analysis uses the invoice date and can differ at month ends.
