# Executive Dashboard — build log

One line per phase (date, commit, tests run, result), then that phase's notes.

| Phase | Date | Commit | Tests | Result |
|---|---|---|---|---|
| 1 | 2026-09-25 | `c1b9a3a2` | `oh test executive_dashboard`: 12 run, 12 passed (Community, demo). `oh shot /odoo/executive` EN + AR desktop: 2/2 ok. Extra local browser check at 1440 / 1024 / 390 px: no horizontal overflow | **completed** locally; dark mode not verified (Enterprise) |
| 2 | 2026-09-25 | `e8fa1abc` | `oh test executive_dashboard`: 23 run, 23 passed (Community, demo). `oh shot /odoo/executive` EN + AR: 2/2 ok. Local browser check of Finance at 1440 / 1024 / 390 px, EN + AR: no console errors, no horizontal overflow, drawers and Open in Odoo work. Independent `odoo-reviewer` pass + re-check | **completed** locally; Enterprise report path **not verified** (see below) |

## Phase 1 notes

- Client action path is `/odoo/executive` (`/odoo/executive-dashboard` belongs to the old module until Phase 6).
- The search RPC is `global_search`, not `search`: `search` would override the ORM method on the model.
- Section cache key also holds the user id (the brief lists groups only): record rules such as "own documents only" depend on the user, so users never share an entry.
- Year to date starts at the company's fiscal year start (`compute_fiscalyear_dates`).
- No `ir.model.access.csv`: the module adds no stored model (the dashboard is an AbstractModel; settings are fields on `res.company`).
- Welcome search is already live (name search, 5 per model, record rules); Phase 6 still owns the configured model list, Needs attention and Definitions.
- Report-line overrides in Settings are left for Phase 2 (Finance), where they are used.
- Not ported from the reference page: the language and theme switches (Odoo's user settings decide both), and the IBM Plex web font (no external font request; falls back to the web client font).
- Odoo runs rtlcss on the Arabic bundle, so the reference's `[dir=rtl]` overrides of physical properties (drawer slide, tab padding) were dropped; they would have flipped twice.
- An uninstall test is not written yet; the uninstall steps come in Phase 6.

## Phase 2 notes

- Finance is one `get_section` call. Community: 10 queries (`_read_group` on posted journal items). With `account_reports`: Profit and Loss, the Balance Sheet line "Bank and Cash Accounts" expanded by account, and Aged Receivable/Payable, each in a savepoint; on any error or scope mismatch the figure falls back to journal items. On Community no `account_reports` xml id is looked up.
- Revenue = `income` accounts; gross profit = revenue − `expense_direct_cost`; net profit = all P&L account types. Other companies' amounts are converted to the dashboard company's currency (the KPI at the period end date, the chart per month, open items and bank at today).
- The monthly chart and the Expected view always use posted journal items (their captions say so). Due-date buckets use the entry date when the due date is missing.
- Access: `account.group_account_readonly` or `account.group_account_manager` (an Invoicing-only admin has only the manager group). Invoicing users see "restricted".
- The native Aged report's columns (`period0`–`period5`, 30-day interval) open the same due-date ranges in the drawer. The native Aged total is used only when it equals the journal-items total up to its sign; otherwise journal items are used.
- Settings → Executive Dashboard → Finance report lines: override lines for Revenue / Gross profit / Net profit (period reports only) and Bank and cash (as-of reports only).
- Odoo's asset minifier dropped the spaces inside nested template literals (SVG paths broke in the minified bundle only); chart code builds strings by concatenation.
- Shell fix: the grid columns were on the high-specificity `.o_action_manager > .ed-app.o_action` selector, so the tablet/phone breakpoints never applied (244 px rail kept at 390 px). Now only `display` uses that selector.
- Review: independent `odoo-reviewer` (read-only). Blocking: native Aged buckets could not be opened; drawer totals not converted across currencies. Should-fix: aged payable sign guess, no savepoint around engine SQL, date mode not checked for override lines, bank override accounts not openable, query-count tests on Enterprise. All fixed with tests where testable locally.

## Verify on Odoo.sh (Enterprise)

- Dark mode (only `web_enterprise` builds the dark bundle).
- Finance with `account_reports` installed (install it on the development build; the module does not depend on it): the KPIs show the P&L values for the period (compare with Accounting › Reporting › Profit and Loss); Bank & Cash equals the Balance Sheet line "Bank and Cash Accounts" per account; Receivables/Payables totals and Aged columns equal Aged Receivable / Aged Payable as of today; each "Open in Odoo" opens the report with the same dates. Check the server log for "Executive Dashboard: … engine not used" warnings: each one means that figure fell back to journal items.
- The standard Net profit expression is looked up as `account_reports.account_financial_report_net_profit0_balance`, then line code `NEP`; if neither exists in this version, set the line in Settings.
- Aged Payable sign convention (the native total is accepted only when it matches the journal-items total up to sign).
