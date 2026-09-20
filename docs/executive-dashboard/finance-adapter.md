# Native financial report integration

The optional `adams_dashboard_finance` addon extends the existing dashboard and
depends on licensed `account_reports`. It keeps report definitions and all ledger
calculations in Odoo. No Enterprise source is copied into Adams.

Accounting managers configure one mapping per company/metric in **Accounting →
Configuration → Dashboard Financial Definitions**. Choose the exact report and
expression (and native denominator for a ratio), document its business meaning, and approve the definition. No customer
mapping is installed automatically. Business data changes flow through on refresh;
mapping/report definition changes withhold the value until reviewed again.

The adapter consumes native `get_options(previous_options)` and
`get_report_information(options)` results. Related cards share one report
evaluation. Numeric totals come from native expression totals, independently of
detail pagination. It validates report/date/company/column-group scope, preserves
native signs and zero values, and exposes warning presence. Unsupported scope,
missing approval, denied access and errors remain distinct from zero.

Drill-down uses the native `account_report` client action with explicit options,
`ignore_session`, and retained journal-group options. Dashboard membership does
not grant accounting permissions. Configuration uses accounting-manager ACLs and
company record rules; readers still require native accounting access.

## Inspected contracts

Authorized Odoo.sh Enterprise revision:
`c874ba3aab567f9b3c6a86dedabf7e76ceb8cef7`.

- `account_reports/models/account_report.py`: options initialization, variant
  routing, native report information and expression-total output.
- `account_reports/static/src/components/account_report/controller.js`: action
  context, passed options, saved-session precedence and report loading.
- `account_reports/data/account_report_actions.xml`: native client-action tag.
- `account_reports/data/profit_and_loss.xml`: Revenue and Gross Profit expressions.
- `account_reports/data/aged_partner_balance.xml`: Aged Receivable and total expression.

## Native verification, 20 September 2026

New Enterprise tests use the built-in reports and independently known values:
signed invoice/refund results; genuine zero; definition drift and unapproved
mapping; protected approval fields; denied accounting access and company
isolation; native action scope; batched evaluation; and historical receivable
settlement (100,000 invoiced, 40,000 paid in August, 60,000 in September).

Application `2389d8930e4856ec04c56fd3aa79bf8d09f6b448`, Odoo.sh build
`38342887`: **35 tests, zero failures/errors**, including nine financial tests.
The build displays Test: Warning; it is not warning-free. Ten local frontend tests
also pass. Margin coverage verifies native percentage units, zero-denominator
withholding, and approval invalidation after changes in referenced P&L definitions.

[Retained native evidence](https://github.com/MostafaEssamm12/Odoo/tree/6afc5ef453cd6aa407d955c9ef03790f52ab7b43/evidence/adams-dashboard/20260920-2389d89)
was read back after storage. Original harness qualification was reused.

The deployed browser session can open the dashboard but lacks accounting-report
access: all twelve financial cards correctly display Access restricted. Financial
native UI/export parity needs an accounting-authorized session and approved
company mappings. Automated test mappings exist only inside rolled-back fixtures.
These tests do not qualify all currency/aging/cash-flow/ledger/budget cases. Full UAT readiness
still requires the remaining acceptance-plan gates and business-definition
decisions for genuine native-report gaps.
