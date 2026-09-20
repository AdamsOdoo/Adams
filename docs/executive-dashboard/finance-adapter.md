# Native financial report integration

The optional `adams_dashboard_finance` addon extends the existing dashboard and
depends on licensed `account_reports`. It keeps report definitions and all ledger
calculations in Odoo. No Enterprise source is copied into Adams.

Accounting managers configure one mapping per company/metric in **Accounting →
Configuration → Dashboard Financial Definitions**. Choose the exact report and
expression, document its business meaning, and approve the definition. No customer
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

## Verification under development

New Enterprise tests use the built-in reports and independently known values:
signed invoice/refund results; genuine zero; definition drift and unapproved
mapping; protected approval fields; denied accounting access and company
isolation; native action scope; batched evaluation; and historical receivable
settlement (100,000 invoiced, 40,000 paid in August, 60,000 in September).

Execution and live-browser parity are pending for this candidate. These tests do
not qualify all currency/aging/cash-flow/ledger/budget cases. Full UAT readiness
still requires the remaining acceptance-plan gates and business-definition
decisions for genuine native-report gaps.
