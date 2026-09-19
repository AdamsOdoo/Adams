# ED-001 — authorized Enterprise database inspection

Observed 19 September 2026. This updates the initial environment blocker in [README](README.md); it does not qualify a dashboard implementation.

## Verified access and changes

- The user supplied `https://adamsmen-harness-onboard-work-20260919-38320135.dev.odoo.com/odoo` for this dashboard development.
- Browser sign-in completed through user takeover of the secure authentication flow. A signed-in Odoo page was observed. No credentials were read, stored in this repository or entered through scripts.
- Settings identifies **Odoo 19.0+e (Enterprise Edition)**. The application warns this is a temporary Odoo.sh development database.
- Initial Settings showed one company and one active language. Its initial company configuration was United States; no production localization policy is inferred from it.
- Native Accounting (`accountant`) was activated through Apps in this development database. Installation completed: Accounting appeared in the app menu and its dashboard/reporting screens opened. Standard demo transactions were present after installation. No manual posting, payment, message or report-definition modification was performed.
- Odoo.sh build number `38320135` is present in the supplied host identity. Exact application, Community and Enterprise Git revisions are **not yet independently verified**. The URL identifies the onboarding branch; it is not a claim that the feature branch is deployed.

## Native financial report discovery

The installed Reporting menu exposes Balance Sheet, Profit and Loss, Cash Flow Statement, Trial Balance, General Ledger, Partner Ledger, Aged Receivable, Aged Payable, Invoice Analysis, Analytic Report and Executive Summary.

Configuration > Accounting Reports shows 27 definitions. It includes United States Balance Sheet and Profit and Loss variants, and Customer Statement / Follow-Up Report variants rooted in Partner Ledger. Configuration also exposes Financial Budgets. Menu/definition presence is not proof that every required metric has been mapped or tested.

### Receivables observations

Verified native route: `https://adamsmen-harness-onboard-work-20260919-38320135.dev.odoo.com/odoo/aged-receivable`.

- Report opens with an as-of date, Receivable account scope, partner filter, Due Date basis, 30-day buckets, Posted Entries and currency display control.
- The current report displays an unposted-journal-entry warning. This must remain distinguishable from successful evaluation/completeness in the future dashboard.
- Native column configuration uses `invoice_date`, `amount_currency`, `currency`, `account_name`, `period0`, `period1`, `period2`, `period3`, `period4`, `period5` and `total`. Some configured metadata columns are not visible in the default rendered report: displayed column positions are not safe mapping identities.
- The report line groups by `partner_id, id`. Its expressions use native Custom Python Function `_report_custom_engine_aged_receivable` and corresponding subformula keys. The configuration explicitly warns that report-specific code drives this report. The function's implementation/signature is not yet inspected, so this is not permission to invent its calling contract.
- Native partner unfolding reveals invoices, credit notes and miscellaneous entries with signed bucket amounts. Individual detail rows can omit a total while the native partner/grand-total row supplies one. Missing displayed cells must not become zero.
- The detail-row menu provides **View Journal Entry**, which opened the original posted customer invoice with an **Aged Receivable** breadcrumb. Return navigation was exercised. No transactional button was used.
- PDF and XLSX export controls are present; export contents and scope parity are not yet tested.

These are live native UI observations using standard demo records, not independently specified fixture tests, adapter parity, role-isolation proof or dashboard UAT evidence. No financial values or customer records are copied into this public dossier.

## Remaining access boundary

ED-B01 (unknown target database) is resolved. **ED-B02** remains: inspect licensed native code, exact build identities and a development build for the feature branch.

Automatic approval review rejected an attempted navigation to the separate Odoo.sh project-management site. Its reason was that the supplied database URL did not explicitly authorize access to private build/source controls on that separate origin. The navigation was not bypassed or retried by another route. Database-only inspection continued safely.

Required clarification: authorize access to the Adams Odoo.sh project's **development build/source tools**, limited to reading native source/build revisions and preparing/testing the dashboard feature branch. Production and staging remain excluded. This is the automatic review's boundary, not a new requirement to reapprove ordinary dashboard development.

Next: inspect the exact native report engine/options/actions and complete G0, then implement the receivables journey using the pinned harness. Do not rerun unchanged Community harness qualification or label it Enterprise/dashboard qualification.

## Login deferral and implementation

The owner subsequently authorized the separate Adams Odoo.sh development source
and build tools. GitHub authentication was not completed; the owner then explicitly
asked to defer login and start building. No additional login attempt is required now.
The standalone dashboard addon has begun; see `implementation-status.md`. The earlier
permission blocker is historical, while exact Enterprise source discovery remains open.
