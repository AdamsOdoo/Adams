# ED-001 — authorized Enterprise database inspection

## Current feature environment — 20 September 2026

Signed-in access was verified in the feature branch, as Mitchell Admin in its
disposable demo database. Dashboard route:
https://adamsmen-feature-executive-dashboard-report-first-38327805.dev.odoo.com/odoo/action-497

Odoo.sh branch Settings reports:

- Application: `c6586cba771fec8a9c5a0901980486d98dce44ec` (build history).
- Community: `7bbce824a1897a912441a7f0511ffec505cbe1d5`.
- Enterprise: `c874ba3aab567f9b3c6a86dedabf7e76ceb8cef7`.
- Themes: `19fef81cdb35d44a2ad435c0e2996376708b1693`.

These build identities differ from the pinned disposable Community harness
campaign; both sets of evidence retain their original scope. Branch settings
install all repository modules with tests and demo data. Arabic was absent and
was added with the native wizard; the first Arabic browser check found missing
dashboard catalogue markers, now corrected in source pending fresh-build QA.

Enterprise `account_reports/models/account_report.py` is readable through the
authorized editor. Its `get_options(previous_options)` initializes report
selection and can reroute to a variant/section. A safe adapter must respect that
selection; merely calling a root report is not sufficient. Detailed mapping,
dated balances and independent parity fixtures remain pending. No proprietary
source was copied into this repository.

## Earlier onboarding environment (historical)

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

## Earlier access boundary (resolved authorization; retained provenance)

ED-B01 (unknown target database) is resolved. **ED-B02** remains: inspect licensed native code, exact build identities and a development build for the feature branch.

Automatic approval review rejected an attempted navigation to the separate Odoo.sh project-management site. Its reason was that the supplied database URL did not explicitly authorize access to private build/source controls on that separate origin. The navigation was not bypassed or retried by another route. Database-only inspection continued safely.

Historical clarification, subsequently granted: authorize access to the Adams Odoo.sh project's **development build/source tools**, limited to reading native source/build revisions and preparing/testing the dashboard feature branch. Production and staging remain excluded. This is the automatic review's boundary, not a new requirement to reapprove ordinary dashboard development.

Next: inspect the exact native report engine/options/actions and complete G0, then implement the receivables journey using the pinned harness. Do not rerun unchanged Community harness qualification or label it Enterprise/dashboard qualification.

## Login deferral and implementation

The owner subsequently authorized the separate Adams Odoo.sh development source
and build tools. GitHub authentication was not completed; the owner then explicitly
asked to defer login and start building. No additional login attempt is required now.
The standalone dashboard addon has begun; see `implementation-status.md`. The earlier
permission blocker is historical, while exact Enterprise source discovery remains open.

## Latest access check

During expanded implementation, the Odoo.sh tab remained at GitHub device
verification. The Enterprise source connector request still returned 404. Feature
commit status/check runs showed only the metadata workflow and no Odoo.sh build
link. The provided onboarding host is therefore not relabeled as a deployed
dashboard feature build. Authentication is required to proceed with the original
financial source and deployment gates. No new permission is being requested.
