# Approved dashboard owner decisions

Status: Decisions 1–10 approved below. This records the material business choices required
by sections 2.2 and 2.5 of the supplied v4 contract. Explicit exclusions in Decisions 4 and 6–9 amend the delivery scope; all remaining accuracy, design and acceptance requirements remain applicable.
Developer configuration/testing and owner acceptance remain separate.

## Decision 1 — approved UAT company and environment

The owner selected **Adams for Men**, using a test copy of the actual business
company for UAT, and explicitly authorized deployment to **staging**.
**No production actions are authorized.** This supersedes the earlier
development-only / staging-excluded boundary for this dashboard's UAT work.
It does not authorize a main/production merge or approve financial definitions.

Staging deployment and configuration have been performed for Adams For Men
(company 1, EGP, Egyptian localization). Thirteen mappings were approved against
its existing native report definitions. Existing staging work was preserved; see
implementation-status.md for exact revisions and verification boundaries.
The US/USD demo company is not the chosen business UAT company.
The owner requested the remaining decisions one at a time.

## Decision 2 — approved posting policy

Financial figures use **posted accounting entries only**. Draft invoices, bills
and journal entries are excluded. Quotations and pending operational documents
remain separately visible under their native operational definitions.

## Decision 3 — approved native financial authority

Use **Adams for Men's existing native Odoo financial reports and company currency**,
including its configured Profit & Loss, Balance Sheet, Cash Flow Statement and
aging reports, with matching filters. Do not introduce a separate management
accounting calculation engine.

This approves the source policy, not arbitrary report/expression IDs. Inspect the
actual staging company's installed/localized definitions and verify mappings
against those reports before configuration. Report parity does not establish
financial close or source completeness. Exact mappings, budgets and native
dependencies still need technical verification; do not inherit demo-company IDs.

## Decision 4 — approved cash forecast scope

Use **the standard Odoo cash forecast only**. The additional custom daily cash
plan and minimum projected cash balance are explicitly **excluded from this
delivery** by the owner's choice. Preserve the native forecast's actual semantics
and label it accordingly; do not present it as a daily schedule.

## Decision 5 — approved future payments and retained aging

Upcoming supplier-payment cards use outstanding amounts from **posted supplier
bills by installment due date**:
- Next 7 days: days 1–7 after the reference date.
- Next 30 days: days 1–30, including the first seven days.
- Due today and overdue are separate from those future windows.

**Both Aged Receivable and Aged Payable remain included**, with total outstanding,
overdue amounts, native signed aging buckets and links to the corresponding native
reports. Upcoming supplier-payment cards supplement rather than replace aging.
Aging uses the selected **Balance as of** date and authoritative native report
results. Use that same displayed reference date consistently for future windows.

The owner explicitly confirmed inclusion of overdue receivables and payables.
Implementation and tests must still verify historical settlement, installment and
native currency behavior. Treatment of standalone credits/unapplied payments and
non-supplier obligations is not newly approved by this decision; retain native
aging semantics and expose any additional definition choice before custom netting.

## Decision 6 — approved delivery quantities only

Show native **ordered, delivered and remaining quantities**. Monetary undelivered
order/backlog value is excluded from this delivery. Retain native product/UoM
semantics and signed quantities; do not add incompatible units into one total.

## Decision 7 — approved native delivery status only

Use native delivery status and quantities. A custom on-time delivery percentage
is excluded from this delivery. No new original-promise/completion calculation
is required for the agreed scope.

## Decision 8 — approved native management worklists

Management attention uses existing native worklists only: purchase orders awaiting
approval and late receipts, alongside separately displayed overdue receivables and
payables. Custom materiality thresholds, custom alerts and escalation rules are
excluded. Preserve native permissions and document routes.

## Decision 9 — approved native inventory views

Include native stock quantities, valuation, forecast and replenishment views.
Custom stock-aging and shortage-exposure metrics are excluded from this delivery.
Retain the native current/historical distinctions and authorized stock scope.

## Decision 10 — approved existing budgets and explicit missing targets

Use existing Odoo financial budgets **where configured**. Otherwise display
**No target configured**; never invent targets or derive them from actuals.
Verify the applicable native budget, company, period and report mapping in staging.
The decision does not select an arbitrary budget when several are applicable,
approve invented sales targets or waive comparison-scope validation.

## Resulting delivery scope and engineering follow-through

All ten choices in the one-by-one owner decision round are now recorded.
The approved scope is a native-report-first workspace, supplemented by the
approved supplier-bill maturity windows in Decision 5. No custom daily cash plan,
minimum projected cash, valued backlog, on-time percentage, alert rules, stock
aging or shortage-exposure measure is required for this delivery.

These are business decisions, not evidence of completed implementation or UAT.
Implementation, staging configuration and native comparisons are recorded in
implementation-status.md with exact tested revisions. Final export, visual and
review gates remain distinct from these business choices. Prior exact-source
evidence and unchanged harness qualification are retained. Production remains prohibited.
