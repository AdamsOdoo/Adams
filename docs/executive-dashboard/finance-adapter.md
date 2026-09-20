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

## Native budgets, cash and partner reporting (20 September)

The approved cash mapping can additionally select the native General Ledger and
Cash Flow Statement. The cash account directory reads the native GL balance
expression with account grouping and the selected cutoff. Native CFS lines are
presented unchanged, including unclassified and reconciliation-difference lines;
its account membership may differ from the Balance Sheet or account directory.
AR/AP mappings can select the native Partner Ledger, preserving separate trade and
non-trade receivable/payable roles. Ledger activity uses the selected period;
aging uses its independent cutoff. No roles are silently netted.

Profitability mappings can select a same-company `account.report.budget` when the
native report supports budgets. Values come from the native budget column group;
no independent daily/monthly prorating occurs. A period with no dated budget items
is unavailable, while an explicit zero budget remains zero. The native Executive
Summary forecast is receivables plus signed payables at period end, separate from
bank cash and any enhanced dated cash plan. It is not guaranteed future liquidity.

All selected report definitions/columns/handlers/linked reports and budget identity
participate in mapping approval fingerprints. Business-record changes flow through;
report definition changes invalidate approval. Native fixtures passed in build
38344123 at source fd3fd714 (44 total tests, zero failures/errors).
