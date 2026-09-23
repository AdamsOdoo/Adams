# UX v2 visual fidelity — blocking acceptance gate

## Approved HTML implementation gate — open, 23 September 2026

The current owner instruction supersedes all readiness language below. **Finance/Inventory parity is not yet accepted.** The immutable reference hash is `36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a`. Reference and actual captures are separate; the comparator produces overlays/diffs without changing baselines or masking defects.

Development `762f0bfd941392e53d71a63a6cda97a767dece49` /38545131 passed122 native tests. Its private pairs identify residual inherited button borders and forecast source-button minimum height; follow-up fixes and Finance drawer comparisons are in progress. `08e01c68c017390e6e5a1db1df33443f150a7254` is the subsequent development candidate, pending qualification. No staging visual pass is claimed.

Representative controlled cases cover1920×1080,1440×900,1366×768 and768×1080; Light, Dark and Arabic/RTL; loaded cards/tables, Finance account/source drawers, Inventory empty state and narrow expanded rows. These are being added to the native harness and remain pending execution/review. Real-data authorization and final staging validation are separate required gates.

## Historical technical visual gate — 22 September 2026

Exact successor `948a006a`, build38418408, passes the full 240-image bilingual,
native-theme, six-width matrix. A separate reviewer inspected all 40 contact sheets
and selected full-resolution originals, closed RTL stock identity clipping and
the Arabic 390px cutoff-date split, and found no remaining Critical/High/Medium
rendered-development issue. Staging desktop Light/Dark and English/Arabic were
also inspected. See [final evidence and owner boundaries](uat-handoff-20260922.md).
Owner visual acceptance remains pending; this is not pixel-identical certification.

## Historical checkpoint — superseded by the handoff above

## Current polish gate — 21 September, not closed

Live staging review and the retained 793059d4 matrix (240 actual screenshots across
EN/AR × native Light/Dark ×320/390/768/1024/1440/1920) identified typography, spacing,
Sales panel-height, pagination, source-dialog and date-wrap defects. The implemented
shared corrections preserve UX v2 composition and authoritative Odoo sources.
Independent inspection of all40 contact sheets and selected full-resolution originals
found one remaining Medium RTL stock identity clipping issue. c17dd27e fixes its
layout cause, with geometry/scroll regressions; corrected rendering is pending after
build38415574 Platform error and Cloud Browser transport loss. This current gate
supersedes readiness impressions in historical records below. No final approval or
post-polish staging visual pass is claimed. See the independent review and current
implementation-status for exact continuation.


The supplied `Odoo_Executive_Dashboard_UX_v2.html` and Finance/Sales/Mobile PNGs
are the design authority. Their hashes are recorded in `requirements/input-manifest.json`.
The contract supersedes fictional data/calculations, not the visual hierarchy.

The initial generic card grid did not implement the supplied design closely enough.
The user raised this on 20 September 2026. The correction is implemented with
native Odoo data integration and preserved branch work. Final source adbe2997
has twelve actual EN/AR captures at 320/390/768/1024/1440/1920. Current staging
English/Arabic desktop captures also confirm the heading-contrast correction
inside the native dark theme. Evidence is linked in implementation-status.md.
Owner visual signoff against the reference remains part of UAT.

## Required comparison

| Area | Reference requirement | Acceptance evidence still required |
|---|---|---|
| Workspace | White desktop sidebar, six departments, plum active navigation, compact owner header | Current-candidate desktop screenshot comparison |
| Profitability | Four primary cards, margin context, chart left/performance context right | Correct hierarchy at 1440/1920; authorized native data and missing-data states |
| Liquidity/working capital | Dark cash card, separate cash/forecast/aging/bank detail | Native sources stay distinct; no fabricated outlook or totals |
| Sales | Commercial cards, orders/quotes and rankings, fulfillment/customer panels | Current-candidate Sales screenshot comparison; full design still under review |
| Supporting departments | Separate CRM/Inventory/Procurement/HR panels, compact by default | Navigation, expansion, returned report scope and permissions |
| Mobile | Compact header/filter bar, horizontal tabs, two-column cards, one column below 370px | 320/390 actual browser screenshots and visual inspection |
| Arabic | Mirrored layout, complete localization, readable mixed-script references | Same comparison in RTL, including opened details/tables |
| Interaction | Source definitions, report navigation, chart table alternative, keyboard focus | Functional runner checks plus manual visual/interaction review |

The native Odoo global toolbar remains provided by Odoo. Prototype-only sample
badges, fictional user/company identity, scenario controls, unapproved targets and
unsupported branch policies must not be rendered as real application facts.
Any further necessary visual departure must be explicit and reviewed, not silently
substituted by a generic design. Passing a reflow assertion alone does not close
this gate.

## Liquidity and working-capital correction

Source 397557b positions the native Cash Flow Statement bridge beside the
bank/cash account directory under three liquidity cards. The bridge reads the
native opening_balance/net_increase/closing_balance rows directly, without
recalculating their values. Bank rows retain native balance, account currency,
archive status, pagination and scoped native GL routes. A ready approved cash
mapping loads the directory automatically; unavailable access never becomes zero.

Receivable/payable cards expose the existing native due-date buckets as signed
values and magnitude bars. The full native aging action is explicit; individual
buckets are not advertised as scoped drilldowns. Daily cash-plan/minimum cash
remain visibly unconfigured until their distinct business definition is approved.
Native browser fixtures now configure cash and both aging reports to exercise the
actual layout and automatic directory loading in EN/AR, instead of only revenue.
Build 38347354 passed 53 native tests with zero failures/errors. Twelve source-matched
EN/AR captures are retained in the private evidence linked in implementation-status.md.
The 1024px liquidity screens were inspected in both languages. Full visual parity
and the remaining Sales/mobile/department interactions are not yet accepted.

## Current interaction checkpoint

67a6d655/build 38348614 passes EN/AR all-department expansion/navigation at all
six widths. Explicit ARIA expansion, mobile close/Escape/focus restoration and
native P&L breadcrumb return are verified. Earlier source-bound captures remain
retained; screenshots generated by this latest run could not be found at retrieval
time. The live current Finance desktop was inspected after module update: four
profitability cards, white sidebar, plum active navigation, chart/context split and
three-card liquidity structure remain in place. Restricted/unconfigured values
are deliberately distinct from the prototype's fictional approved figures.
This evidence does not represent full visual signoff or all-reference-state parity.


## Recovered reference interaction audit — 21 September 2026

The original HTML was inspected for its click, keyboard, input and saved-view
handlers, including the v2 overrides. Its file URL was rejected by the cloud
browser, so this is a source audit plus native Odoo checks, not an interactive
HTML-browser pass. Original reference images remain unchanged.

| Reference behavior | Odoo continuation and remaining evidence |
|---|---|
| Six department links, active section, expand/collapse | Existing implementation retained; native EN/AR/light/dark six-width fixture recovered at d59b5d57. |
| Native dark mode | Existing native Sass theme support retained. Manual Odoo Preferences switch verified the dark workspace and card surfaces at build 38354024; original System preference restored. |
| Save/restore/reset view | Existing dates/company/layout retained. Corrected missing Sales list and ranking measure; restored selections reload authorized current data, with late-response protection. New native saved-view regression added. |
| Sales orders/quotations and ranking choice | Existing controls and full-ranking drawer retained. Manual commercial-margin switch and full-ranking drawer verified on d59b5d57, preserving negative values. |
| Clickable cards, source drawer, chart/table drilldowns | Existing routes retained; native scoped report/return and source focus checks remain source-bound. Full current-source visual review is still required. |
| Mobile attention expansion and keyboard tabs | Already implemented; no duplicate redesign. Full manual mobile interaction acceptance is not claimed from source inspection. |
| Prototype branch selector, scenario switch, RTL switch | Company permissions and native language/theme govern the application. Prototype-only scenario fixtures and fictional branch identities are not deployed. |
| Prototype sample-record search, summary print/export | Native report/list search and existing scoped native exports are available; the prototype's unified sample-record search and whole-dashboard summary export are not equivalent implemented features. Exact scope/parity remains open. |
| Approved forecast/delivery/inventory exclusions | Owner decisions 4 and 6–9 remain authoritative; do not silently restore excluded custom calculations to imitate sample numbers. |

The theme and saved-view continuation does not close the entire 1:1 visual and
interaction acceptance gate. Record remaining differences explicitly and retain
the original 58-test evidence instead of reclassifying it as final visual signoff.

Current continuation evidence: 9d9ae4ef/build 38363622 passed 58 native tests,
zero failures/errors. Staging c6b8ad3e reports Success. Paired native light/dark
Finance desktop screens were inspected after the module update; saved quotations
and commercial margin restore correctly. All 19 displayed metric values match
the pre-update snapshot. These bounded checks do not close the open parity gate.


## Intermediate UAT candidate — c97b80f2

The next candidate closes the previously recorded global-search and summary-export
gaps using native documents/reports. Search remains inside the selected company,
period and native rights. Unlike the fictional reference, bills are searched by
posted invoice date rather than a demo-only outstanding-list composition; the scope
is stated in the drawer. Search supports each document type and bounded paging.
CSV and print summary share fresh server-provided values and native export rights.
The printable output is a compact readable summary, with full supporting records
available from native report exports. It does not copy prototype fictional values.

Mobile workspace anchors close the menu and open attention details. Restricted
finance correctly says Access restricted in management attention. Slow initial
Sales loading no longer replaces a user's earlier selection. Local controller
checks: 25 passing. Native qualification and final paired screenshots are pending.

The original HTML cannot be interactively opened through the current browser's
file route. That environment limitation remains recorded; source event-handler
inspection and the unchanged Finance/Sales/Mobile PNGs are the comparison reference.
This limitation is not a reason to label an untested interaction as passed.


## UAT feature completion — feca7e2d / ef01fbe6

Search, CSV and print/PDF preview close the missing functional counterparts noted
in the recovered audit. The reference layout remains the comparison authority;
Odoo's native top bar, active company/theme/language and authorized source values
are intentional integration differences. Printing is a readable executive table,
not a screenshot of the prototype's fictional dashboard. Source warnings, missing
budgets and absent apps remain explicit instead of copying prototype sample KPIs.

Native search reflow runs at all six widths in both languages and themes. The
print preview runs at 1440 in both languages/themes; this is not a claim of every
printer's PDF pagination. Current staging captures are identified in the final
implementation evidence. Earlier captures remain tied to their earlier revisions.
The Arabic review corrected actual attention-link and inline-count translation
lookup defects, not merely the presence of translation strings in source.

Owner visual signoff remains part of UAT. The HTML reference's interactive file
route was blocked, so direct interactive HTML validation and pixel-exact parity
are not claimed. Full customer zoom/accessibility and printer-specific acceptance
remain recorded in the UAT/release matrix, not silently relabelled as passed.

Live staging review subsequently found English server-generated print labels; ef01fbe6 fixes their Python translation registration and asserts actual Arabic CSV and preview content. Earlier preview evidence is explicitly retained as a defect, not a pass.

Final live staging 06a5274b: inspected retained English light/dark, Arabic dark, Arabic print, native search, Finance chart/context and Sales screenshots. Native preference changes control the workspace theme; English/Dark restored. Both previews render 27 rows without horizontal overflow. These current visual checks support owner UAT readiness; they do not claim the blocked HTML-browser pass or owner pixel/visual signoff.


### 23 September controlled header normalization

The reference company menu now contains the disposable user's actual authorized company names and selected company, rather than the prototype's three unrelated company profiles. This corrects an unmatched content state that changed the native select's intrinsic width; the approved select CSS and baseline HTML remain unchanged. Current source/capture manifests must be used to qualify this adjustment. No implementation pixels replace reference captures.


### UI27 Arabic integration required by the implementation contract

The contract expressly requires completed Odoo Arabic and native locale behavior instead of the prototype's partial translation. The existing approved Arabic dictionary is retained in the application. Missing frontend catalog markers are corrected. For Arabic controlled comparison, the reference's text and date content is normalized through that completed catalog and native date formatter; no HTML structure, style, width, masking or baseline pixels are replaced. The manifest records the catalog SHA256 and this content-only adjustment. Arabic geometry, sign ordering, arrows and chart chronology remain acceptance requirements, not translation waivers. The Finance chart now explicitly retains chronological left-to-right ordering under Odoo's RTL asset processing.

The UI27 content normalizer translates only complete labels or fully covered compound captions; it must not translate fragments inside source definitions/business names. The reference chart month/axis labels use the native locale formatter, with original markup and geometry intact. The application translation import uses Odoo19's module-aware transpilation, verified by a native regression test, so another application's global vocabulary cannot override dashboard terms. Earlier Arabic captures with mixed English/Arabic definitions remain failed evidence, not baselines to reuse.
