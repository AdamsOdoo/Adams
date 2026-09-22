# Qualification checkpoint — active working tree

**NOT YET READY FOR OWNER UAT.** Development candidate `f0fe542be27bec15c121db1d0e8fa5abb90ae614` passed its native suite. Results below are source-bound observations, not qualification of subsequent edits or the final staging candidate. Final visual, performance, deployment and evidence gates remain pending.

## First integrated candidate: native failures reproduced

Candidate `236f63bd36aa7939b9074a2c2d73c9ad4174edf2`, development build **38459297**:
29 post-tests, 101.31 seconds, 16,515 queries; **3 failures, 2 errors**. Odoo stopped at its failure limit, so later finance/HR/inventory cases were not qualified.

- LibSass rejected two lowercase mixed-unit `min()` expressions. Replaced with equivalent width/max-width; local LibSass now compiles both bright and dark styles.
- Odoo 19 exposes company context through `@web/core/user`, not the former company service. Dashboard startup now uses `user.activeCompany` and the `ACTIVE_COMPANIES_CHANGED` event. The test service mock now rejects nonexistent services, and a company event regression covers invalid draft dates and clearing old records.
- The company identity test referenced an absent fixture. It now creates and authorizes a rollback-isolated second company.
- Independent follow-up fixed the HR unassigned-department selector transition. Inventory review identified missing sorting, unreachable replenishment/history header actions, hidden validation errors and an inaccurate valuation caption; corrections have focused regressions but still require native/performance qualification.

These changes are fixes under test, not passed owner-UAT gates. Staging remains at `9af98d4248090f2be3ceefb5d59bca36258b7c3a`.

## Follow-up candidate: native execution resumed

Candidate `b679bb39732dacaafe1dea884975c0ccfabefbba` first encountered platform error build **38491096**. A supported rebuild on the same source, **38491213**, reached **69 post-tests in 95.88 seconds / 51,468 queries**, then stopped with **1 failure and 4 errors**. Startup/company integration and Sass errors no longer occur. Remaining observed defects: narrow applied-date fragments and translation-function shadowing in denied HR action/profile paths. Corrections preserve the original negative assertions. A related shadowed-name path in fulfillment validation was corrected with its own regression.

Independent review found an avoidable full-catalog scan in default stock name sorting. The corrected name path uses native database order and bounded windows/prefixes, with an additional mixed-script ordering/read-volume regression. Quantity sorting uses native computed quantities and still needs representative timing. Controller suite: **51/51 pass** on the follow-up working tree; no native/visual all-pass claim.

## Third candidate: failures and follow-up scope

Candidate `eb5a6528eab98041067fe63b1fdf642333570459`, development build **38491683**, stopped at **76 tests: 2 failures / 3 errors**. The full suite remains unqualified.

- Native view metadata contains immutable mappings: copy only the top-level result and independently parse/serialize the quantity-only architecture; strengthen native-view noncontamination coverage.
- Stock source expected-domain fixture omitted archived internal locations while the documented source explicitly includes them. Independent expected scope now includes archived internal locations and excludes external supplier locations.
- Odoo 19 uses Boolean `requires_allocation`; the historical string `no` enabled allocation in the new leave fixtures. Use the supported Boolean setting, retaining native validity checks.
- Browser screenshot capture referenced a removed Sales wrapper. Capture actual orders, quotations and fulfillment panels through their controls; retain strict target assertions.

The follow-up also adds independent HR draft/applied dates across worklists, profiles, sources, refresh and saved return selections; current snapshots remain current. Approved leave headlines count distinct authorized employees while request worklists retain request counts. HR panels/cards follow the selected reference more closely. Controller suite: **56/56 pass**. The native browser fixture now includes authorized attendance, leave, assigned/unassigned Planning records and retained profile screenshots. These changes await native execution and visual review.

**Historical UI32 deviation at the third checkpoint (resolved by the fifth candidate below):** the no-check-in-today summary slot displays unavailable. Open-session employee counts cannot safely establish the whole active workforce's lack of check-in under partial attendance record rules. No subtraction, zero, absence or lateness inference is presented. A source-authorized whole-cohort definition and reconciliation are required to enable this slot.

## Fourth candidate: full suite completed, corrections still required

Candidate `3dcf3cf55c1e5b02a9989695b0bf828510fb5c6b`, development build **38492329**: **103 post-tests, 181.58 seconds, 74,574 queries; 2 failures / 2 errors**. Unlike earlier halted runs, this run reached stock, native operational and workspace-detail tests. The browser matrix failed in the English/light 1440 case at saved-view restoration; earlier cases are partial observations, not retained full-matrix qualification. The timing-sensitive menu helper is being replaced with observed open/close states and stable action selectors. HR fixtures are corrected to use valid hourly requests and assign the attendance officer only in its intended role case.

Follow-up implementation closes source-confirmed gaps: posted invoice/credit-note document tab; product/UoM fulfillment actions; native aging bucket actions; named saved-view dialog; section-level Sales ranking controls; Procurement three-card/paired-table layout and CRM two-card layout. These are new changes requiring native and visual qualification.

The UI32 unavailable placeholder is now replaced, where authorized, by the installed standard employee `last_check_in` snapshot. It uses active selected-company employees and native field/record access, not subtraction from visible attendance sessions. Matching employee actions reuse the exact domain. This **stored native snapshot** can lag chronological session corrections; the interface identifies the snapshot and does not infer absence or lateness.

**Unresolved source-dependent parity:** bank/cash split cannot be inferred safely from the single `asset_cash` account type or ambiguous journal associations; retain the native total/directory until an approved native split definition exists. Procurement approval/late worklists display authoritative order counts rather than invent monetary sums. Both differences require explicit final disposition, not silent parity acceptance.

## Fifth candidate: first all-pass native development checkpoint

Exact application source: [`f0fe542be27bec15c121db1d0e8fa5abb90ae614`](https://github.com/AdamsOdoo/Adams/commit/f0fe542be27bec15c121db1d0e8fa5abb90ae614). Odoo.sh development build **38492934**. The observed native log at **2026-09-22T19:41:52Z** reports **107 tests, 383.00 seconds, 100,550 queries, zero failures and zero errors**. Earlier failures above remain historical evidence and are not relabelled as passes.

The completed suite includes native finance/operational/HR reconciliation and negative cases, source-action validation, and the English/Arabic × light/dark × seven-viewport browser matrix. Its browser assertions cover named saved-view save/restore/reset, source return, posted invoice/credit-note documents, stock pagination, populated HR tabs and employee profiles. Successful assertion/evidence-capture execution does not replace human-readable side-by-side screenshot review or actual staging data reconciliation. The complete suite's query count and runtime are **not** per-operation performance results.

UI32 is now backed by the installed employee `last_check_in` stored snapshot, with model/field/record access and explicit selected-company/local-midnight scope. `test_no_check_in_today_uses_authorized_native_employee_snapshot` reconciles the matching employee source domain and tests prior-day open sessions, future-only entries, timezone boundaries, field denial and missing capability. This is not an absence/lateness calculation or a subtraction from a partially visible attendance list.

Read-only independent review of this candidate found no Critical/High/Medium defect in the scoped aging-bucket permission/domain/export paths, HR snapshot authorization, invoice/refund scope, fulfillment product/UoM actions, and shared company/HR-period/saved-view response guards. It was a focused code review, not a blanket security or final qualification claim.

**Candidate delta remains open:** subsequent palette/panel/Arabic-layout refinements and reserved-stock/performance work are not covered by the f0fe542 pass. Freeze and publish the next source, run its affected native/browser/performance gates, and bind the actual deployed addon identities before final qualification. Staging was not upgraded by this checkpoint; the last inspected staging application source remains `9af98d4248090f2be3ceefb5d59bca36258b7c3a`, with optional Attendance, Time Off and Planning absent. No production/main action or PR draft-status change is authorized by this result.

| Check | Observed status | Limit / next evidence |
|---|---|---|
| External harness adapter check | PASS: exact pinned clean resources and eight skills | Toolkit runtime qualification is historical; it does not qualify dashboard edits. |
| Attached selected HTML checksum | PASS: matches manifest | Prototype identity only; no Odoo parity assertion. |
| Initial controller regression run reported by coordinating implementation agent | 37 discovered; 36 passed; one existing continuous-scroll expectation failed | Department navigation is changing to the approved single-workspace behavior. Review/replace the obsolete expectation with meaningful active-workspace coverage and retain fresh raw output. This is not an all-pass run. |
| Native Odoo backend/frontend tests | PASS for f0fe542 / build 38492934: 107 tests, zero failures/errors | Final changed candidate, deployed identity, raw-log retention and affected reruns pending. |
| Changed metric/source reconciliation | PARTIAL: cited native fixture tests passed | Final/staging standard-source reconciliation, exact filters/signs/date/company/UoM and evidence index pending. |
| HR capabilities, role rules, durations, overnight shifts and employee profiles | PARTIAL: native HR and populated browser fixtures passed on f0fe542 | Final HR paired visuals and staging capability/role disposition pending; absent optional apps are not silently installed. |
| Company branding, cross-company races and exports | PENDING | Authorized multi-company fixtures; no previous-company records/results after switch. |
| HTML/Odoo paired visual and interaction campaign | PARTIAL: native bilingual/theme/viewport assertions passed on f0fe542; final parity PENDING | Pair and review actual screenshots at equal widths/zoom; requalify changed palette/panels and close deviations. |
| Export CSV and real PDF/print output | PENDING | Downloaded bytes/output inspection, exact scope and safe content. |
| Performance | PENDING | Fixed dataset and scopes, browser/RPC/backend timing and request/query counts; at least three fresh repetitions. |
| Final independent review and private evidence retention | PENDING | Exact candidate review, hashes and archive read-back required. |

No historical test counts or earlier staging acceptance close any changed behavior automatically. Where implementation changes after a test, rerun the affected acceptance gate. Preserve successful unrelated evidence with its source identity.
