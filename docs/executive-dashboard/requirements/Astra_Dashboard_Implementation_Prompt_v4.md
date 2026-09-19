# Astra implementation prompt — report-first Odoo executive dashboard

Version 4.0 · 19 September 2026

**Use:** place this file, `Dashboard_Report_First_Contract_v4.md`, and `Odoo_Executive_Dashboard_UX_v2.html` in the target coding workspace. Give Astra the task below. Screenshots and the prototype test report are supporting references, not proof of a live Odoo implementation.

---

## Outcome

Implement the attached executive dashboard as a maintainable, native Odoo 19 add-on. Use the HTML as the approved visual and interaction reference and `Dashboard_Report_First_Contract_v4.md` as the data and acceptance contract. Deliver a running, inspected, development-qualified application ready for owner/finance UAT—not another mockup, a scaffold, or an untested code dump.

The owner must understand profitability, cash, receivables/payables, sales performance and delivery risk, then navigate to the exact supporting report and original record without losing context. **Data accuracy is priority number one.** Native report calculation fidelity, permissions, clarity, responsiveness and maintainability take priority over adding features. This version supersedes the previous prompt/data-source policy; the v2 HTML remains the UI reference only.

## Establish the actual environment

Inspect the workspace, relevant existing `AGENTS.md`, project profile and latest handoff. Identify the authorized repository, branch/worktree, Odoo build, hosting, installed modules/localization, available licensed Enterprise code, database and existing test harness. Preserve unrelated/unpublished work. Do not infer the target from an old chat or attach this feature to the Adams/Shopify project.

Reuse the existing Odoo development harness when applicable, but verify its present capabilities and qualification instead of treating old checkpoints as current evidence. Do not rebuild the harness or weaken a protected verifier to make this feature pass. If the target is not resolvable from connected resources, request the one missing project identity; continue safe, environment-independent preparation.

Inspect the HTML in a browser and the relevant contract sections before implementation. Verify actual model fields, report APIs, XML action IDs and module dependencies in the installed Odoo source. Do not guess them. The sample fixture calculations, historical data, taxes, targets and branch allocation are not production accounting rules.

## Implementation scope

Preserve Finance first, Sales second, and less prominent CRM, Inventory, Procurement and HR. Finance contains Profitability, Liquidity and Working Capital. Sales contains Commercial Performance and Fulfillment. Retain source/definition details, explicit dates, meaningful alerts, report/record drill-downs, saved presentation preferences and mobile disclosures.

Build an Owl client action with reusable components and Python metric/report adapters. Retain native Odoo navigation and use standard lists, forms and financial-report actions for the supporting journeys. Do not paste the self-contained HTML/fixture engine into an Odoo view or duplicate the whole Odoo shell. Remove prototype controls, fictional figures and simulated authorization from production. Local fixtures belong only in development/test assets.

Centralize each approved metric's allowed filters, native report/variant/line/expression/column mapping and action resolver. For a measure already available from a standard Odoo report, use its evaluated numeric output through the installed report engine. Do not write a second financial calculation from account.move.line, invoices or payments and merely compare it afterwards. No independent P&L, Balance Sheet, Cash Flow Statement or aging algorithm in Python or JavaScript. The relevant native reports are the calculation authority across all departments, not just reconciliation references. The policy covers existing operational measures as well as Finance.

Resolve mappings using verified technical identities, never translated labels, row positions or hardcoded database IDs/account codes. Use native effective options and comparison columns. Do not scrape rendered HTML/PDF/XLSX or parse formatted monetary strings. Do not infer zero from a missing/hidden/paged row. Related cards/charts share report evaluations; drill-downs and exports carry the same options and provenance. Discover exact licensed report APIs instead of inventing method names. Missing report/module/mapping/access must be visible, never replaced by a homegrown or sample fallback.

Make a source catalog for every planned widget before coding its calculation. Explicitly inspect Partner Ledger and statements/follow-up, Aged Receivable/Payable, P&L/Balance Sheet/Cash Flow/General Ledger/Trial Balance/Executive Summary/budgets, Inventory Stock/valuation/Forecast/Locations/Moves/Replenishment, Sales Analysis, Invoice Analysis, Purchase Analysis and installed vendor/receipt reports, plus applicable CRM/HR reports. Section 2.6 is mandatory. Record each exact native measure or demonstrated gap with its actual action, backend, options/domain, measure, aggregation, date field, grouping and unit/currency. Do not add every report to the home screen; retain the approved executive hierarchy.

Use the real native backend for each report. Accounting handlers are not interchangeable with `sale.report`, `purchase.report`, `account.invoice.report`, or specialized Inventory services. Standard grouping/aggregation of native report measures is preferred to new transaction-level SQL or copied report formulas. Inspect installed methods and permissions; do not invent a universal report API. Confirm count versus distinct orders, sum versus average, native quantity/currency treatment, and the event actually used by timing measures. A label such as Days to Receive is not proof of actual receipt timing; inspect the source and extensions before promising that KPI.

Partner Ledger supplies partner account movements/balances; native aging supplies maturity buckets and historical open items. Keep customer/vendor roles, opening amounts, contact hierarchy and effective scope explicit. Operational inventory valuation and the Balance Sheet inventory account are not forced to match; explain differences using native review. Sales Analysis, Invoice Analysis and P&L measure different stages; purchase commitments, posted payables and actual payments also remain distinct. Each widget must match its own approved native source.

Implement dynamic bank/cash account discovery as mandatory functionality, not a later enhancement. Discover authorized bank/cash journals, linked ledger accounts and eligible unlinked CoA accounts; read amounts from native Balance Sheet account detail or aligned General Ledger/Trial Balance. Do not limit the balance to entries in the bank journal. New eligible accounts, including native-confirmed zero balances, appear on the next completed refresh without code or dashboard-list configuration changes. Renames, archived historical accounts, company scope, currencies, negative balances, report-scope exclusions and configuration errors are handled explicitly. Deduplicate by ledger-account identity, not name/journal count. A first-page list does not define the headline total. Do not confuse customer/vendor bank details, credit-card debt, suspense or outstanding-payment balances with company cash. Verify Odoo 19 fields and company relationships.

Inspect standard Executive Summary ratios/short-term forecast, budgets, Invoice Analysis, Sales Analysis and installed operational reports before creating additional formulas. Standard Invoice Analysis margin is not necessarily posted P&L gross profit; verify and accurately label the cost basis. All genuinely additional logic needs the section 2.5 register: native gap, sources, exact formula, dates, exclusions, currency, owner, support records, expected tests and material business-definition approval. Propose this clearly to the owner before enabling it. A scheduled daily cash plan is separate from the standard Cash Flow Statement and native short-term forecast. Preserve the standard value when only presentation is changing.

Discover other report dimensions dynamically as well: partners, vendors, products/categories, warehouses/locations, salespeople/teams, stages and departments. Use authorized native report groups/configuration, not sample lists. New eligible records appear in the appropriate scope on refresh; preserve inactive history and unassigned groups when the native report includes them. Source completeness is not limited to the visible top-five or paged results.

Return structured values, source class and provenance. The browser formats and presents results; it does not calculate accounting totals. The same report-based contract governs cards, charts, supporting actions, exports and future read-only agent access.

Use the contract's source lineage and reconciliation rules. Distinguish accounting revenue, net invoiced sales, order value, outstanding debt and forecast cash. Historical receivables/payables use the native report's dated settlement results, not a newly written settlement calculation. Bank ledger balance is not necessarily bank-available funds. Forecasts require explicit inputs and assumptions. Where configuration or history is missing, expose that limitation rather than inventing values.

Implement real server-side authorization for aggregates, drill-downs, records and exports. Validate company/branch scope and request parameters; respect underlying access and field restrictions. No blanket `sudo()`, broad arbitrary model-query endpoint, or cross-user/company cache reuse. Keep financial/HR details out of unauthorized responses and logs.

Load sections independently, reuse native financial-report evaluations and appropriate native operational report/ORM grouping, paginate detail records on the server and prevent old filter responses from replacing newer results. Use bounded queries and measured caching only where justified. Do not add a data warehouse, custom generic analytics engine, external chatbot or streaming infrastructure without a demonstrated need.

Design for English and Arabic, true translated RTL production UI, keyboard use, readable labels and signed financial values. Preserve navigation context, browser-back behavior where supported by Odoo, record/report back navigation, applicable filters and scroll position. Charts need textual/table alternatives. Distinguish zero, no activity, missing configuration, restricted, stale and failed states. Never show a failure as zero or a refresh as proof of source completeness.

## Delivery sequence

Start with a complete receivables journey: secured native aging evaluation at the selected cut-off → total and overdue figures → aging → scoped native report → original records → export → back navigation. Prove it against known expected cases and the native report in actual Odoo.

Then complete Finance, including Partner Ledger-based customer/vendor journeys, dynamic cash-account discovery and standard Cash Flow Statement results; then Sales and the supporting departments using the same components/contracts. Prove adding a zero-balance bank/cash account, posting a bank/general-journal entry to it, renaming it, checking historical balances and switching company without editing any dashboard code. Missing optional modules must produce a truthful unavailable/not-installed state without breaking Finance. Keep incomplete optional scope visible in the handoff; do not silently call it delivered.

Run targeted checks while changing a slice, then relevant integration/browser/security/performance tests at stable milestones. Do not repeatedly run an unchanged expensive campaign. Diagnose failures and rerun what the correction affects; broaden coverage when risk or evidence justifies it. A skipped/blocked test is not a pass, and zero discovered tests is not success.

## Autonomy and working method

Proceed through inspection, implementation, disposable development fixtures, testing, browser inspection, defect correction and documentation without requesting repeated approval for those reversible steps. Choose reasonable technical defaults and record them. Clarify only material business/accounting decisions or missing authorization that cannot be resolved from the project; keep unblocked work moving.

Do not deploy to production, alter real accounting records, send customer communications, execute payments, merge/release, discard someone else's work or use another project's authorization. Prepare reviewable changes within the verified development boundary; external writes must follow that project's actual authorization.

Keep `AGENTS.md` concise and use relevant skills/documents when needed, not a mandatory reread of the entire repository before each edit. Keep one implementation owner. Use bounded parallel review/research only where it avoids shared-file conflicts and reduces effort. Use greater reasoning effort for difficult accounting, security and architecture decisions where the runtime supports it; do not maximize orchestration by default.

Maintain a concise checkpoint after coherent milestones: branch/commit, working-tree state, exact environment, completed requirements, evidence, defects, blocked checks and next action. Preserve it before context becomes difficult to manage; do not assume chat history is durable project state.

## Definition of done

Complete the acceptance matrix in `Dashboard_Report_First_Contract_v4.md` on the exact candidate source/build. Provide a working install and upgrade path, reconciled financial results, actual role/company isolation, passing applicable tests, measured performance, real desktop/mobile English/Arabic Odoo screenshots and an independent review when available. Do not label your own second pass independent if no separate reviewer was available.

Provide the add-on, configuration guidance, compact metric/action registry, test commands/results, known limitations and owner/finance UAT checklist. Identify the exact source commit and test environment. No unresolved Critical/High defects, misleading financial states, duplicated native financial or operational calculations, failed dynamic-account/dimension scenarios, or unexplained differences outside documented native currency/rounding precision may be accepted as UAT-ready. Test native UI/report outputs for every enabled department independently of the dashboard adapter and include signed known expected cases; comparing a helper to itself is not evidence. Report lower-severity findings explicitly.

Distinguish implemented, development-verified, ready for business UAT and release-approved. No universal “error-free” guarantee: demonstrate what passed and disclose what remains unverified. Stop at the agreed development/UAT handoff, not after first code generation, and not at production deployment.

Begin with a brief verified environment summary and a small execution plan, then perform the work.

---

## Prompt design references

The project-specific business/data requirements are in the companion contract. This task uses concise repository instructions, verified context, bounded execution, runnable tests and an explicit evidence-based definition of done; these are working practices, not a product certification.

- [OpenAI: repository instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [OpenAI: coding-agent best practices](https://developers.openai.com/codex/learn/best-practices)

These OpenAI references are retained from the v3 prompt and were not revalidated for this report-coverage-only revision; verify the target runtime and tools rather than assuming a model-specific feature exists. Do not claim a live Odoo test passed until it was executed on the identified build.
