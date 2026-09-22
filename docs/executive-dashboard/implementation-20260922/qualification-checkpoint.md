# Qualification checkpoint — active working tree

**NOT YET READY FOR OWNER UAT.** Results below are scoped observations, not qualification of the evolving candidate. Native and visual gates remain PENDING.

## First integrated candidate: native failures reproduced

Candidate `236f63bd36aa7939b9074a2c2d73c9ad4174edf2`, development build **38459297**:
29 post-tests, 101.31 seconds, 16,515 queries; **3 failures, 2 errors**. Odoo stopped at its failure limit, so later finance/HR/inventory cases were not qualified.

- LibSass rejected two lowercase mixed-unit `min()` expressions. Replaced with equivalent width/max-width; local LibSass now compiles both bright and dark styles.
- Odoo 19 exposes company context through `@web/core/user`, not the former company service. Dashboard startup now uses `user.activeCompany` and the `ACTIVE_COMPANIES_CHANGED` event. The test service mock now rejects nonexistent services, and a company event regression covers invalid draft dates and clearing old records.
- The company identity test referenced an absent fixture. It now creates and authorizes a rollback-isolated second company.
- Independent follow-up fixed the HR unassigned-department selector transition. Inventory review identified missing sorting, unreachable replenishment/history header actions, hidden validation errors and an inaccurate valuation caption; corrections have focused regressions but still require native/performance qualification.

These changes are fixes under test, not passed owner-UAT gates. Staging remains at `9af98d4248090f2be3ceefb5d59bca36258b7c3a`.

| Check | Observed status | Limit / next evidence |
|---|---|---|
| External harness adapter check | PASS: exact pinned clean resources and eight skills | Toolkit runtime qualification is historical; it does not qualify dashboard edits. |
| Attached selected HTML checksum | PASS: matches manifest | Prototype identity only; no Odoo parity assertion. |
| Initial controller regression run reported by coordinating implementation agent | 37 discovered; 36 passed; one existing continuous-scroll expectation failed | Department navigation is changing to the approved single-workspace behavior. Review/replace the obsolete expectation with meaningful active-workspace coverage and retain fresh raw output. This is not an all-pass run. |
| Current native Odoo backend/frontend tests | PENDING | Exact final source, discovered IDs, raw logs and outcome required. |
| Changed metric/source reconciliation | PENDING | Independent standard sources and exact filters, signs, date/company/UoM scope required. |
| HR capabilities, role rules, durations, overnight shifts and employee profiles | PENDING | Installed source identities and non-admin behavior required. |
| Company branding, cross-company races and exports | PENDING | Authorized multi-company fixtures; no previous-company records/results after switch. |
| HTML/Odoo paired visual and interaction campaign | PENDING | All six departments/five HR tabs; English/Arabic; light/dark; exact 1920×1080, 1440×900, 1366×768 plus narrow/zoom. |
| Export CSV and real PDF/print output | PENDING | Downloaded bytes/output inspection, exact scope and safe content. |
| Performance | PENDING | Fixed dataset and scopes, browser/RPC/backend timing and request/query counts; at least three fresh repetitions. |
| Final independent review and private evidence retention | PENDING | Exact candidate review, hashes and archive read-back required. |

No historical test counts or earlier staging acceptance close any changed behavior automatically. Where implementation changes after a test, rerun the affected acceptance gate. Preserve successful unrelated evidence with its source identity.
