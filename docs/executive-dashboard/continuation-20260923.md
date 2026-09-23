# Presentation continuation checkpoint — 23 September 2026

Status: **incomplete; Finance/Inventory gate blocked and unpassed**.

## Source and environment

Recovered HEAD: `91bbf98877b63892a4d6483c63ab9611a15f1b0d`, clean checkout.
Current application change: `638af7eabd0186612856b7df8d9b59fd0c3d7506`,
Subsequent Finance geometry fixes are at `b9a9cbb076700c4210b2143696c0336a216974a7`; later context/caption edits in this checkpoint also require native/rendered verification. Both dashboard manifests19.0.1.7.0. This preserves the later fixes preceding the
session. PR214 is open, draft, unmerged. Main/production were not changed.

| Candidate | Development build | Observed outcome |
|---|---|---|
| `9bfeb484` | 38532237 | One native browser failure: obsolete arrow selector after Finance information-icon change. |
| `f9479bad` | 38533011 | Odoo.sh done/Warning, not Failed. Revenue value drilldown assertion corrected, including real hit-target check. Actual restricted-role chart Retry recovered to an explicit unavailable state; no application console errors observed in that check. |
| `ed16c0b9` | 38533796 | Odoo.sh Platform error; no usable paired capture. |
| `638af7ea` | 38534410 | Odoo.sh Platform error. |
| `b1d92f77` | 38534772 | Initial populated Finance captures produced. One native print-label assertion failed. |
| `08c8d486` | 38535653 | Corrected reference crop produced. Equivalent PDF-label assertion failed. Both label assertions corrected in b9a9cbb0. |

Staging remains `af0d2327184e96dfb3eecd65de3a79c4747d6045`, installed
core/finance19.0.1.6.0, upgrade build38524406, live hostname38326320:
https://adamsmen-staging-38326320.dev.odoo.com/odoo/action-1004.
No staging upgrade occurred in this continuation. Optional Attendance, Time Off
and Planning applications were not installed on staging to populate screenshots.

## Implemented in existing components

Finance source information icons, report action on the chart, local chart Retry,
warning placement, approved dark-green cash card, full signed main values (with
meaningful decimals retained), Revenue naming, margin/budget notes, and the
approved grid/bar chart structure. Bars remain bound to existing report-series
values and scoped report navigation, with negative/zero/missing observations
preserved. Unavailable cash-flow cards now show their source state instead of a
blank value. No accounting calculation, report definition, source permission,
company authorization or business-app installation was changed.

The exact approved HTML is preserved outside addon assets, with its SHA-256 and
explicit reference-adjustment record. Comparison tooling keeps independent
baselines, validates matched metadata and image hashes, and emits pairs,
overlays and diffs without percentage-based acceptance. The initial native
Finance capture fixture is test-transaction-only; it produced private images in both38534772 and38535653. Completed state normalization and accepted comparison remain outstanding. It is not a deployed mock dashboard.

Local checks on the application changes:65/65 frontend tests; XML parse; Python
compile; whitespace check. Comparator checks covered identical images, a visible
difference, and rejection of mismatched states. These checks do not replace
visual or real-data acceptance. Build38536432 at b9a9cbb0 completed with Odoo.sh done/Warning, not Failed. Application source ea4d1ab4c33cb24f3e394ae23014c17c6ebb9575/build38536975 contains the later context/caption edits; its native verification was still pending at this checkpoint.

## Unresolved deviations and delivery limits

| Area | Unresolved requirement |
|---|---|
| Finance controlled parity | No qualified paired captures/diffs yet. Populated cards/chart, empty/unavailable states, expanded chart/aging tables and drawers remain unaccepted. |
| Finance visible differences | Group/date captions, partial-month indication, performance-context labels/pill/explanation and lower card/drawer geometry still require direct reference matching. No waiver. |
| Shared shell-owned content | Dashboard toolbar/filter geometry and missing approved icons require controlled comparison; real Odoo outer shell must remain. Shared propagation is held behind the Finance/Inventory gate. |
| Inventory | Populated matched filters/table/pagination/scrolling and filter-shrink journeys remain open. Existing wider native table/source controls must be reconciled with approved geometry without hiding columns. |
| Sales/Procurement/CRM | Earlier implementation retained. Current candidate has no completed paired visual review or fresh end-to-end acceptance. UI20 remains deferred with truthful worklists. |
| HR | All five tabs/profile remain in scope. No current-candidate paired review. Missing staging applications must remain honest states; populated synthetic coverage cannot establish installed-app staging behavior. |
| Appearance/size | No new accepted1920×1080,1440×900,1366×768,narrow,light/dark,Arabic/RTL comparison matrix. Historical screenshots are not current acceptance. |
| Data and navigation | Presentation changes preserve backend calculations, but current-candidate report reconciliation, permissions and retained-context journeys still need native/live execution. |
| Deployment/package | No verified19.0.1.7.0 staging candidate or final installable package. Do not package or present an unqualified build as the finished deliverable. |

Continue with the existing native build harness; inspect the next Finance pair, fix differences and repeat. The earlier platform errors no longer explain the current acceptance gap. Complete Inventory
before propagating shared changes. Do not rerun the historical audit, reset to an
old SHA, broaden the backlog, or reopen UI07/UI08/UI20 decisions. Use the short
current owner guide at the top of `uat-checklist.md` only after qualification and
deployment. Business screenshots/raw logs remain outside this public repository.

## Latest rendered findings

Private diagnostic pairs for b1d92f77 and08c8d486 were opened and inspected. The first reference crop used viewport rather than document coordinates;08c8d486 fixes that. The comparison remains unaccepted: component heights/spacing and source-state text differ, and complete content-width/state normalization is not yet verified. Finance-only heading line heights, footer padding and margin notes were corrected in b9a9cbb0. Later edits port the context panel, keep a real source-scope action, and add a date-derived partial-month marker/currency caption.

Specific data/presentation conflict: the service exposes a boolean for report warnings; it cannot truthfully identify every warning as the prototype's “Draft entries exist.” The implementation uses “Report warnings”/“No report warnings” or the restricted/unavailable state. This is recorded as an unresolved reference-state qualification issue, not silently waived or relabelled as draft entries. Native report options explicitly retain posted entries only.

No final package was generated from this unqualified candidate. The owner guide remains conditional on Finance/Inventory parity and source-bound staging deployment.

The capture helper now takes an unchanged-viewport image before cropping the measured dashboard region. It refuses a region outside the viewport instead of trimming overflow. This addresses a suspected screenshot-induced scrollbar/layout-width change; the revised capture still requires its own native run. No comparison is accepted on that assumption alone.
