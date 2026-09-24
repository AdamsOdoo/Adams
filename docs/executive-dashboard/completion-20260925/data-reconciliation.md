# Data reconciliation — completion pass 25 September 2026

Scope: local Odoo 19 Community database with Odoo demo data (no customer data), apps Sales, Purchase,
Inventory with valuation, CRM, Time Off and Attendances. The dashboard's own service methods were
compared with independent document-level ORM queries in the same user context, for "This month" and
"Year to date" (1–25 September and 1 January–25 September 2026, the dates of the final run on the final
build). The script is read-only and kept in the private evidence bundle.

Result: **53 of 53 checks match.**

| Metric | Dashboard source | Independent comparison | Result |
| --- | --- | --- | --- |
| Invoiced sales | `account.invoice.report` price_subtotal, posted invoices and credit notes by invoice date | Sum of `account.move.amount_untaxed_signed` for the same documents | Match (both scopes) |
| Confirmed orders value | `sale.report` price_subtotal, state `sale`, order date in the user's timezone | `sale.order.amount_untaxed / currency_rate` in the same local-date bounds | Match |
| Confirmed orders count | `sale.report` distinct order references | Number of confirmed `sale.order` documents | Match |
| Quotations value and documents | `sale.report`, states draft and sent | Draft and sent `sale.order` documents | Match |
| Confirmed purchases | `purchase.report` untaxed_total, state `purchase` | `purchase.order.amount_untaxed / currency_rate` | Match |
| Weighted pipeline | `crm.lead` prorated_revenue, open opportunities created in the period | Expected revenue × probability recomputed per record | Match |
| Approved leave hours (signed) | `hr.leave.report` number_of_hours, approved requests | `hr.leave.number_of_hours` with the report's sign (requests negative) | Match; the label states "(signed)" |
| Active employees | Current `hr.employee` snapshot | Active employees of the company | Match |
| Checked in now | Distinct employees with an open `hr.attendance` | Same, from attendance records | Match |
| On approved time off today | Distinct employees with approved leave overlapping today | Same, from `hr.leave` | Match |
| Stock rows (17 product/location rows, current) | Product quantity at the exact location; reservations from `stock.quant` | `stock.quant` quantity and reserved quantity at that location | 34 of 34 match |

Observations for the owner, not defects:

- Year-to-date invoiced sales can be lower than the current month when earlier months contain credit
  notes. Both scopes reconcile to the posted documents.
- A dashboard user without HR rights sees Odoo's own-record counts (for example 0 checked in) for
  Attendances and Time Off, because the native record rules let every employee read their own records.
  The employee snapshot on the same panel shows "Access restricted". This follows the security rules in
  the HR addendum. Whether such users should see a restriction instead is an owner decision (see README).

Not verifiable locally: every Finance metric, cash, aging, supplier windows and the balance sheet use the
Enterprise `account_reports` engine through `adams_dashboard_finance`; Planning shifts need Enterprise
Planning. These are covered by the native tests on the Odoo.sh development build and by the earlier
Enterprise evidence recorded in `handoff-20260924.md`; they were not re-executed in this pass.
