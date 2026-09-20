# Decisions needed to finish the full v4 scope

Status: Decisions 1–5 approved below; remaining proposals are unapproved. This records the material business choices required
by sections 2.2 and 2.5 of the supplied v4 contract. Only the explicit scope choice in Decision 4 changes the requested delivery scope.
Developer configuration/testing and owner acceptance remain separate.

## Decision 1 — approved UAT company and environment

The owner selected **Adams for Men**, using a test copy of the actual business
company for UAT, and explicitly authorized deployment to **staging**.
**No production actions are authorized.** This supersedes the earlier
development-only / staging-excluded boundary for this dashboard's UAT work.
It does not authorize a main/production merge or approve financial definitions.

Staging deployment is authorized but has not yet been performed. Preserve existing
staging work and verify the selected company's identity, native currency,
localization, reports and permissions before treating its figures as UAT evidence.
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

## Additional measures

| Requested outcome | Current native source and gap | Decision / remaining choice |
|---|---|---|
| Daily cash outlook / minimum cash | Standard Executive Summary short-term forecast is available; it is not a dated receipt/payment schedule | Approved Decision 4: standard native forecast only; custom daily plan and minimum projected balance excluded from this delivery. |
| Payments due in 7 / 30 days | Native aging has maturity buckets but the requested exact forward windows have not been qualified | Approved Decision 5: posted supplier-bill installments, overlapping days 1–7/1–30; due today and overdue separate. Keep native AR/AP totals, overdue and aging buckets. Technical parity remains to be implemented/qualified. |
| Remaining backlog value | Native ordered/delivered/remaining quantities are implemented; there is no approved value/history rule | Define goods-only versus services/kits, returns/overdelivery/cancellations, discounted untaxed price, native currency and current versus historical cutoff. Native quantity views remain available. |
| On-time completion | Native first-delivery date is not final completion; original-promise coverage is unverified | Choose transfer/order/line denominator, dispatch versus customer receipt, original deadline and timezone/grace period, partials/returns and missing-history treatment. Show coverage and N/A for no denominator. |
| Management attention | Native purchase approval/late-receipt worklists are implemented; executive materiality/owner rules are undefined | Identify thresholds, responsible role and actionable native route per alert. Do not invent red/green risk badges from sample data. |
| Stock aging / shortage exposure | Native dated valuation and current forecast routes are implemented; aging/nonmovement and exposure definitions are not equivalent | Choose receipt age versus last movement; owned versus consigned stock; product/warehouse scope; physical versus projected shortage and forecast horizon. Reuse the native report where the definition matches. |
| Targets and historical comparisons | Native financial budgets and signed monthly trends are implemented | Select approved budgets and explicit comparable dates. Missing commercial targets or original historical events remain unavailable, never inferred from actuals. |

The owner may approve explicit definitions or defer named extra measures from the
first UAT scope. Until that decision is recorded, the full v4 requirement remains
open. A deferral must be explicit; an unavailable widget is not completed scope.
