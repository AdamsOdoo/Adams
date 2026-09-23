# Qualification checkpoint — final staged candidate and historical evidence

## Final implementation candidate and staged testing

**STAGING AVAILABLE FOR OWNER HANDS-ON TESTING — NOT YET READY FOR FORMAL OWNER UAT.** Final published application feature **`b9461b76f3b1a1e1085fda87d55f6ef66ecca9b9`** has dashboard addon trees `adams_executive_dashboard` **`78710c2fc2334379aedc44939968d9a4e818f8ab`** and `adams_dashboard_finance` **`a01fdad4fcc866e02093c3c115d4c71432902313`**. Development build **38514095** passed **120/120 native post-tests** (403.75s, 118,807 queries), **65/65 focused frontend tests**, and its native browser matrix completed **28 English/Arabic × light/dark × seven-viewport cases**, retaining **532 actual Odoo screenshots and four actual dashboard PDFs**. The native PDF/browser output was captured; screenshot count is not by itself a full pixel parity sign-off.

The exact staged application is **`28b37d90d77571383b37e70212681e9730d5cf40`**, running build **38326320** with matching two addon trees and installed versions **19.0.1.5.0**. The final dashboard-only upgrade succeeded at **2026-09-23 06:16:25 UTC** after the manual **05:34:26 UTC** backup. Its translation-and-test-only change followed backend candidate `efcf40aa` / staging `44fdbe43`; the underlying calculation code stayed the same. The earlier staged **34/34 independent read-only probes** therefore support that unchanged backend, while the final published/deployed tree identities and browser/Arabic behavior are separately qualified on the final source. Do not label the old probe archive as a 34-check rerun on `28b37d`.

| Evidence boundary | Observed result and limit |
|---|---|
| Exact source and native/browser tests | Feature `b9461b76` / build38514095 120/120 native pass; 65/65 frontend pass; 28 bilingual/theme/viewport native browser cases, 532 PNGs/four PDFs captured. Staging `28b37d90`/build38326320 clean matching addon trees and both installed versions19.0.1.5.0 after a backed-up dashboard-only upgrade. |
| Independent report/data checks | Prior identical backend candidate `44fdbe43` passed **34/34 source-guarded read-only probes**: Finance9, Procurement/CRM5, Inventory/HR5, preservation/performance12, stock prefilter3. They reconcile selected real measures and preservation, not every record, permission, or the later Arabic-only code change. The native Aged Receivable signed bridge to dashboard totals and actual PDF/XLSX were inspected. |
| Live final dashboard journeys | All six departments and five HR tabs were navigated on staged final source. Real Partner Ledger and other native source actions, scope-labelled exports and XLSX/PDF, desktop Inventory Category plus functional `Source data` column, native valuation/forecast links, and authorized employee work-profile source were exercised. The earlier intercepted Partner Ledger link, Inventory Category omission and HR Owl crash are closed on this source. |
| HR capability limit | Attendance, Time Off and Planning are **uninstalled** on staging; those tabs show distinct missing-app states while Overview/Employees use permitted real data. Native fixtures cover populated optional-app records and source-specific rules. A live installed-app workflow cannot be claimed for this staging database. |
| Retained backend performance | On identical backend source and matched three-repeat ORM context, current stock page one **10.818→1.116s / 4,391→694 queries**, page two **11.205→1.068s / 4,404→672**, historical **21.745→1.918s / 4,379→662**; cash directory **0.110→0.103s / 84→84**. Cache invalidated between ORM repeats, DB buffers uncontrolled. Exact final staged RPC sample: Inventory **0.772s / 716 queries median (n=3)** and bootstrap **0.009s / 4 queries median (n=6)**. RPC/backend timing does not imply browser paint/network latency. Private raw final probe/browser records are indexed separately. |
| Remaining business and staging limits | UI07 comparable-period definition, UI08 bank-versus-cash classification and UI20 prototype monetary amounts versus approved native order-count worklists need explicit owner disposition. Only one company is authorized on this staging account, so live company-switch isolation is covered by native fixtures rather than a fabricated second staging company. Final owner visual/financial acceptance and production approval remain separate. |

Selected approved six-department/five-HR-tab HTML SHA-256: `36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a`. Private customer values, workforce records, Enterprise code and raw screenshots stay outside this repository; the evidence index binds them to the exact source and build. PR #214 remains draft. Main and production remain untouched.

The owner can start hands-on testing at [Adams For Men staging](https://adamsmen-staging-38326320.dev.odoo.com/odoo/action-1004). Treat the three source-definition decisions and the limits above as open; do not record formal owner acceptance or production release from a technical test pass.

### Open business-definition dispositions

| Surface | Existing approved source behavior | Specific remaining decision |
|---|---|---|
| UI07 comparison | Native report/budget results and warnings are shown. The approved budget is never replaced by actual revenue. | Define the comparable period for custom ranges, partial months, YTD and zero/negative baselines, or accept an explicit “comparison not configured” state. No percentage is calculated solely to match prototype fixtures. |
| UI08 cash | The signed native `asset_cash` total and permitted account directory remain available, including zero/negative balances and excluded archived accounts. | Identify an authoritative, stable bank-versus-cash classification and handling of ambiguous journal/account associations, or explicitly retain the combined total/directory. |
| UI20 purchase attention | Owner Decision 8 authorizes native approval and late-receipt **worklists**. The dashboard shows their source-backed order counts and exact records. | Explicitly accept count-labelled worklists in place of the prototype’s monetary amounts, or approve a source-defined monetary formula, currency and period before implementation. |

These are decisions about new measure definitions or an explicit prototype deviation, not a request to reapprove the accepted HTML design. Technical fixes and all other authorized qualification continue independently.

### Preliminary HTML-to-staging visual distinctions

These observations help interpret the 15 retained HTML/Odoo pairs; they do **not** certify pixel parity for every responsive width, menu or error state or accept an unapproved business definition. The private index identifies final source, language, appearance and matched content widths for each pair.

| Surface | Selected HTML reference | Observed staged Odoo behavior | Disposition |
|---|---|---|---|
| Host shell | Prototype simulates Odoo's top controls and review environment. | Odoo supplies the real top bar, company/profile menu and a staging environment banner. The dashboard draws only its own content. | Host-owned controls/banner are excluded from dashboard pixel parity; keep dashboard content widths equal in pairs. |
| Company identity | Fixture company identity/logo. | Standard active-company name and original-aspect logo appear through the Odoo context; fallback is part of the dashboard. | Authorized actual company identity supersedes fixture branding; final company-switch, long-name/fallback and light/dark pairs remain pending. |
| Finance context/chart | Illustrative chart history and prototype context. | Actual report-warning/date banner and a chart spanning only the real authorized month/data. | Real report scope and native warning take priority over fictional series; verify spacing, warning readability, axes and actions at equal content width. UI07 comparison formula remains undecided. |
| Inventory table at 1365×936 | Category is a separate table column alongside product and quantity. | An earlier stage folded Category into the product sublabel. Final `28b37d90` has a dedicated desktop Category column and a working native `Source data` drilldown. Real stock contains valid negative quantities and more rows than prototype fixtures. Valuation, forecast, history and replenishment use native source labels. | **Earlier UI17 desktop difference corrected and paired.** Seven-width native matrix includes narrow/RTL cases; owner may examine scrolling/zoom and signs in the retained captures and staging. |
| HR workspaces | Populated prototype Attendance, Time Off, Shifts and employee examples. | Real authorized workforce appears; three optional applications are absent and show missing-app states. All five tabs, Overview/Employees and its work-profile source link render on final `28b37d90`. | Missing apps are a capability state, not grounds for installing unrelated applications. Fifteen pairs cover all HR tabs/profile and selected Arabic/dark variants, but installed-app live attendance/leave/shift records cannot be demonstrated here. |
| Financial split/purchase attention | Prototype displays bank-versus-cash figures and monetary approval/late values. | Report-first combined cash/account directory and native approval/late order-count worklists. | UI08 classification and UI20 amount-versus-count require explicit source definition/disposition; do not substitute fixture amounts. |

## Historical checkpoints (superseded by final staged candidate above)

### First integrated candidate: native failures reproduced

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

## Historical complete checkpoint: 170cf53 (superseded by current status above)

Exact application source [`170cf53faf57e4a499a4086f9daa287f9d5963dc`](https://github.com/AdamsOdoo/Adams/commit/170cf53faf57e4a499a4086f9daa287f9d5963dc), development build **38495339**, native log **2026-09-22T20:26:22Z**: **113 post-tests, 404.23 seconds, 116,093 queries, zero failures/errors**. The full browser campaign retained **532 PNGs / 28 cases**, with **four actual PDFs** checked structurally and for nonblank content. These checks do not establish PDF visual correctness or paired HTML/Odoo parity. Focused standard company logo/name and live native company-switch coverage passed. Local controller regressions: **58/58 passed**.

Intervening development candidate `d18bd6e1babcece81883aaa80ffd9870ba4a02b6` / build **38494458** completed 112 tests in 395.80 seconds / 110,357 queries with zero failures and one reservation fixture error (uncategorized product indexed as a category pair); its 28-case browser matrix passed. Test-only successor `bf4d18f6cc5b3bd0fff83688506ccf81441ddeb7` corrected that fixture and added PDF/company checks. The subsequent 170cf53 pass is the latest complete result; earlier failures remain historical evidence.

170cf53 corrects the Revenue target label/value to use an approved budget rather than actual revenue, and refines compact KPI footer/date treatment and purple source buttons. A remaining three-line CSS text/chart/trust-link palette change is **not covered** by this pass. Final native qualification and paired/PDF visual review remain pending. Staging is unchanged at the previously verified clean `9af98d4248090f2be3ceefb5d59bca36258b7c3a`; backup **2026-09-22T19:54:14Z** and baseline remain private. **NOT YET READY FOR OWNER UAT.**

| Check | Observed status | Limit / next evidence |
|---|---|---|
| External harness adapter check | PASS: exact pinned clean resources and eight skills | Toolkit runtime qualification is historical; it does not qualify dashboard edits. |
| Attached selected HTML checksum | PASS: matches manifest | Prototype identity only; no Odoo parity assertion. |
| Initial controller regression run reported by coordinating implementation agent | 37 discovered; 36 passed; one existing continuous-scroll expectation failed | Department navigation is changing to the approved single-workspace behavior. Review/replace the obsolete expectation with meaningful active-workspace coverage and retain fresh raw output. This is not an all-pass run. |
| Native Odoo backend/frontend tests | Final b9461b76 / build38514095: 120 tests, zero failures/errors; frontend65/65; native browser28 cases/532 PNGs/four PDFs. Earlier 9a2/94a failed campaigns remain historical. | Formal owner UI07/UI08/UI20 definition and paired visual/financial acceptance pending. |
| Changed metric/source reconciliation | PARTIAL: cited native fixture tests passed | Final/staging standard-source reconciliation, exact filters/signs/date/company/UoM and evidence index pending. |
| HR capabilities, role rules, durations, overnight shifts and employee profiles | PARTIAL: native HR and populated browser fixtures passed on f0fe542 | Final HR paired visuals and staging capability/role disposition pending; absent optional apps are not silently installed. |
| Company branding, cross-company races and exports | PARTIAL: native standard logo/name and live company-switch checks passed on 170cf53 | Final visual evidence/exports and exact staging company validation pending. |
| HTML/Odoo paired visual and interaction campaign | PARTIAL: native bilingual/theme/viewport assertions passed on f0fe542; final parity PENDING | Pair and review actual screenshots at equal widths/zoom; requalify changed palette/panels and close deviations. |
| Export CSV and real PDF/print output | PASS for actual final-source dashboard PDF capture (four EN/AR × light/dark) and exact staged native Aged Receivable XLSX/PDF/signed bridge; real exports/source actions opened. | Owner visual/content review of dashboard print and other scoped exports remains distinct. |
| Performance | PASS for retained backend-identical three-repeat stock ORM/query improvement and final-stage Inventory/Bootstrap RPC samples | Browser paint/network, navigation and user-perceived loading remain a separate owner journey; no invented performance target. |
| Final independent review and private evidence retention | PENDING | Exact candidate review, hashes and archive read-back required. |

No historical test counts or earlier staging acceptance close any changed behavior automatically. Where implementation changes after a test, rerun the affected acceptance gate. Preserve successful unrelated evidence with its source identity.
