# Executive Dashboard — UX improvement plan (2026-09-25)

Status: **noted, not implemented.** Owner feedback after the completion build
(modules 19.0.1.8.0). Nothing here changes the approved HTML until each item is
recorded as a deviation (D19 onward) and approved.

Visual reference for this plan: `reference/executive-360-concept.html`
(published copy: https://claude.ai/artifact/3JGeUFdrqBkgAgrDgkRbEY)
(example figures only).

## Owner feedback

1. Quick access navigation is poor; it should open a side panel, not jump down the page.
2. "Performance context" adds nothing.
3. The progress bars carry no meaning; use real charts or keep it clean.
4. Bank & cash shows "Breakdown unavailable" although the Balance Sheet has the detail.
5. Delivery status should open delivery orders; every figure should open the records behind it.
6. It must look, feel and work like an executive 360° view of the company.

## Current behaviour (from the code)

- Quick access: "Needs attention" and "Data & definitions" are in-page anchors
  (`#adams-attention`, `#adams-trust`); "Search documents" opens a centred modal.
  The dashboard uses seven modal dialogs (source, analysis, search, print,
  employee, cash, saved views) that block the page.
- Delivery status (`open_fulfillment`, `models/dashboard.py`) opens a
  `sale.report` pivot, not `stock.picking`. The order list opens the sales order form.
- Bars: top-5 ranking rows (`adams_rank_track`), aging rows (`adams_aging_track`)
  and the analysis trend table (`adams_bar_track`) redraw the printed number.
- Bank & cash split (`_cash_journal_breakdown`, `adams_dashboard_finance/models/dashboard.py`)
  is shown only if a General Ledger detail mapping exists, **every** `asset_cash`
  account is the default account of exactly one bank or cash journal, and the
  total reconciles. Staging has unlinked cash accounts (see
  `future-work-20260923.md` item 3), so the status is `ambiguous` and both lines
  read "Breakdown unavailable".

## Plan

### 1. One side panel for all detail
- One reusable panel on the right (left in Arabic). The dashboard stays visible
  and scrollable behind it. It replaces the source, analysis, cash, search,
  employee and needs-attention modals.
- Quick access opens the panel: **Needs attention** (ranked items, each linking
  to its records), **Search** (grouped results: orders, invoices, deliveries,
  partners), **Definitions**.
- Print and saved views stay as small dialogs (they are actions, not places).

### 2. Every figure opens the records behind it
A click opens the records someone would act on, in the same period and company
scope; the analysis view is a secondary link.

| Element | Today | Target |
|---|---|---|
| Delivery status, product row | `sale.report` pivot | Outgoing `stock.picking` not done/cancelled, filtered to the product |
| Delivery status, order row | Sales order form | That order's delivery orders (`action_view_delivery`) |
| Receivables / payables overdue | Aging report | Keep, plus a list of the overdue invoices/bills |
| Late purchase orders | Purchase order list | Late incoming receipts |
| Bank & cash | Account directory modal | Per-account balances in the panel, each opening that account's General Ledger |

Before coding: walk the control-sweep inventory and write the target of every
clickable element.

### 3. Remove what doesn't help decisions
- Remove "Performance context". Reporting status becomes a header badge; the
  revenue target shows only when a budget exists.
- Remove the ranking and aging bars. Aging becomes one stacked bar
  (current → 90+). The analysis trend becomes a line chart.
- Keep charts only where they answer a question: revenue & profit by month,
  cash trend, aging mix.

### 4. Bank & cash breakdown from the Balance Sheet
- Take the account lines of the Balance Sheet's own "Bank and Cash Accounts"
  line (expanded by account, same options and cutoff). They sum to the headline
  by construction.
- Show every account with its balance. Group as Bank / Cash when a journal
  identifies it, otherwise "Other"; never hide the list because one account is unlinked.
- "Unavailable" only for missing access or a missing report mapping.

### 5. Executive 360 layout
- New **Overview** page first: company pulse KPIs with comparison and trend,
  needs attention, cash, receivables, operations, people. Department pages follow.
- One filter bar: period, comparison (prior period / last year), company, saved views.
- Every KPI shows its change against the comparison period and opens its records.

## Dark mode
The dashboard has no theme switch of its own by design (`dashboard.scss`
header): it follows Odoo's theme. Odoo's dark mode is an **Enterprise**
feature (`web_enterprise`), switched per user from the avatar menu at the
top right. Community (local tests) has no dark mode, so it can only be
checked on the Odoo.sh build. Option: add a dashboard toggle that calls the
same user preference; recommended only if the owner wants it on the dashboard itself.

## Order and cost
1. Bank & cash (§4) and drill-down targets (§2): backend-first, low risk.
2. Removals (§3).
3. Side panel (§1) and Overview (§5): the largest change; the drawer/dialog
   sweep (112) and browser checks (66) must be rewritten.
