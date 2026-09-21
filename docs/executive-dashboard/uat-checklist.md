# Adams For Men dashboard — staging UAT

Use the authorized **Adams For Men staging database**, company **Adams For Men**,
currency **EGP**. Production and main are excluded. The agreed scope is recorded
in [owner decisions](owner-decisions.md). See [implementation status](implementation-status.md)
for the exact tested/deployed source and evidence boundaries.

**New follow-up is pending native qualification and is not deployed:** source
6ac4798a adds product ranking, section settings and scroll tracking (19.0.1.3.0).
28 local controller checks pass; Odoo.sh is still queuing the native test build.
Fresh pre-upgrade backup: **2026-09-21 08:28:54 UTC**, staging 06a5274b.
The three new journeys below are acceptance instructions, not completed results.

The staging candidate is **ready for owner UAT** at source **ef01fbe6**, addon version **19.0.1.2.2**.
Native build **38371030** passes **60 tests with zero failures/errors**; the 25 controller checks pass. Staging is **06a5274b**; exact identities and evidence are in implementation-status.md.
The current pre-update backup is **21 September 2026, 07:08 UTC**. Older
source/build/backup details below are retained as historical evidence.

## Start UAT

Open [Executive Dashboard in staging](https://adamsmen-staging-38326320.dev.odoo.com/odoo/action-1004)
or use the app menu. Use existing authorized native roles.
Select the company, period and Balance as of date, then Apply filters. Check the
applied dates before comparing any result. Returning through the dashboard
breadcrumb restores the scope and reloads current authorized values.

| Journey | Acceptance check |
|---|---|
| Profitability | Revenue, gross profit, operating expenses, net profit and ratios match the same posted-only native reports. Native warnings remain visible. |
| Cash | Compare Bank and cash to Balance Sheet, account balances to General Ledger and opening/movement/closing to Cash Flow Statement. Standard forecast keeps its native meaning. |
| AR and AP | Compare totals, overdue and signed aging buckets at the selected cutoff. Follow native report and partner/document routes. Credits and unapplied payments retain native aging treatment. |
| Supplier windows | Check overdue, due today, days 1–7 and days 1–30. The 30-day window includes the first seven days. Drill-down and export must identify and retain the same bill-installment window. |
| Budgets | Use existing applicable native budgets only. This staging company has none configured; expect No target configured. |
| Sales | Compare invoiced sales, confirmed orders and quotations separately. Check salesperson/customer breakdowns, recent documents, native analysis and export. |
| Product ranking | Compare the top five signed net invoiced product values to Invoice Analysis for the same company/date range; credit notes reduce sales, tax is excluded. Open a product and Full ranking. |
| Section settings | As administrator disable HR, Save and reload: HR disappears from both navigation surfaces, body and summary. Re-enable and verify it returns. Verify choices are company-specific; all-disabled has a clear empty state. |
| Scroll tracking | Scroll down and up; the active category follows the visible section beneath the sticky tabs. Click a short final section and verify it stays selected. Repeat after resizing and in Arabic. |
| Fulfillment | Inspect ordered, delivered and remaining quantities by product/UoM. No mixed-unit headline, valued backlog or custom on-time percentage is required. |
| Inventory | Open current stock and stock at the balance cutoff. Compare quantities and native operational valuation by product. Check forecast/replenishment routes with existing stock rights. |
| Purchasing | Inspect awaiting-approval and native late-receipt worklists. Open a record and return. Viewing does not approve, receive or bill an order. |
| CRM and HR | Use existing native opportunity and workforce sources. Empty results remain explicit. Time Off is not installed in this staging database, so leave hours correctly show App not installed. |
| Access | Dashboard membership must not grant native accounting, HR, stock or export rights. Check each intended UAT user's existing permissions before granting access. |
| Search | Find posted invoices/bills and confirmed orders/draft-sent quotations by reference or party. Validate company/period, unavailable types, paging and the original native form. |
| Summary exports | Download CSV and use Print summary. Verify actual native values, units, dates, blank unavailable values, warning labels and native export rights. |
| Preferences | Save quotations and commercial margin, change both selectors, restore, and verify both selections and dates return with freshly loaded data. Native Odoo theme/language control appearance. |
| UI | Compare the supplied reference layout in English and Arabic, including mobile navigation, long mixed-script names, exact source values, negative signs, focus and table scrolling. |

## Record owner acceptance

Record the tester, native role, company, applied dates and language/theme for each
journey. For a defect, retain the exact action, expected native report result,
observed result and screenshot; do not edit accounting records to force a match.
Use the source-bound evidence in implementation-status.md as the engineering
baseline. A UAT-ready staging candidate still requires finance/owner signoff.

| Acceptance | Tester / date / result |
|---|---|
| Finance source and cutoff agreement | Pending owner UAT |
| Sales and operational journeys | Pending owner UAT |
| English/Arabic visual fit to supplied reference | Pending owner UAT |
| Intended users and native permissions | Pending owner UAT |
| Production release decision | Not authorized |

## Staging accounting observations

Native reports warn that unposted journal entries exist. They are excluded under
the owner's posted-only policy. A successful dashboard/native comparison is not
approval of the accounting data, closing process or unusual balances. Business
users should investigate those records in native Odoo during UAT; development
does not adjust financial records to make dashboard figures look conventional.

## Deployment and evidence boundaries

Only `adams_executive_dashboard` and `adams_dashboard_finance` are deployed to
staging. Disposable test addons are excluded. Existing staging code is preserved.
The pre-install staging backup is dated **2026-09-20 18:04:30 UTC**. Installation
preserved the recorded hashes of 1,047 accounting documents, six users' existing
company/group permissions and 250 native report expressions. Subsequent setup
added dashboard membership to the existing administrator and approved 13 mappings
against the inspected native definitions; it added no native financial rights.

Previous qualified addon source was `adbe2997718aad8ad57c341b071415a910f7a8f4`; historical staging
commit is `29121a55098acefcc9d55031c2dd0bb68942d4c9`. That historical native run
passed 58 tests and the final staging update preserves accounting/access/report/
mapping hashes. The staging environment expires on **19 October 2026**.

The private harness pin and unchanged qualification are reused. Native automated
checks, retained screenshots, current-company comparisons and owner acceptance
are distinct. Independent engineering review and owner UAT signoff must be recorded
before calling this an approved release. No main merge or production deployment
is authorized by this checklist.
