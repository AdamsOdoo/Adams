# ED-UI-20260921 — current-design visual consistency

## Final continuation — 22 September 2026

See [the final UAT handoff](uat-handoff-20260922.md) for the complete diagnosis,
successor identities, independent visual review, staging upgrade and unchanged-value
comparison. The corrected feature is `948a006a`; development build38418408 passes
65 tests with 240 retained screenshots. Staging is `9af98d42` / build38419464.
The later date correction changes three summary date wrappers, the shared no-wrap
selector and one rendered assertion. No report or business logic changed.
Historical failed/passing builds below retain their original attribution.

## Scope and baseline

Owner-authorized visual correction of PR #214, preserving the existing UX v2
composition and report-first sources. Baseline feature d7f159f51316085cb7cb17c38b563c9921ebba14;
staging 65ccfa9c73effc133b2dfda5d89fe50e78e3ac7a/build38409525. The preserved local
handoff a26a45b has the same tree as the remote feature baseline. No work discarded.
Harness remains pinned to10ec1d059b5ddc5d422875f68e0726cc500487ce; adapter check passes.
Original HTML SHA256 ac8278b8baae7fd401011ff8b0b5e4a2ec03b97d02eb90e88c106897d290ed0c
matches the input manifest; original Sales/Finance/Mobile references are retained.

## Observed rendered defects and correction

- Live Sales stretched a two-person ranking to the height of21 order rows. Shared
  grids now align panels to their own content; recent orders have a bounded scroll
  area and sticky headings, retaining every record and the existing pagination.
- Helper/date/footer text was9–11px; custom font and overlapping SCSS overrides
  produced inconsistent hierarchy. Consolidated12/13/14px shared text tokens,
  inherited Odoo font, common card/panel/field/table spacing and radii.
- Numbered stock pages spread across the entire width; shared pager layout now
  keeps controls adjacent. Inventory quantity toggles stay grouped.
- Top5/10 affected rankings above its own control; move the control before Sales
  panels. Display invoice/customer ranking currency consistently with other rows.
- Source drawers consumed almost a full desktop width and foregrounded field codes.
  Source-only drawers are560px; analysis/search/print retain appropriate widths.
  Technical codes remain in a collapsed disclosure; business explanation stays visible.
- Equivalent empty/error states had different padding and retry behavior. Reuse
  shared states and existing retry handlers; keep unavailable states truthful.

## Permitted changes and verification

Only dashboard frontend, its Arabic catalog/version, browser evidence instrumentation
and this dossier. No accounting/source/permission/mapping/company/business-data change.
Core version19.0.1.4.2; finance remains19.0.1.4.0. No schema migration.
37 controller tests pass; XML/Python parsing, PO format checks and diff checks pass.
Existing Odoo/browser suite must qualify exact candidate. Capture all24 combinations
of EN/AR × Odoo Light/Dark ×320/390/768/1024/1440/1920, with additional actual section
captures for semantic review. Live staging must verify filters, source/return,
rankings, pagination, search, print and unchanged critical displayed values.
No production/main changes; retain draft PR. Final independent review and actual
post-upgrade screenshots are required before an owner-UAT-ready handoff.

## Deployment and recovery

Before staging: record current revision, verify backup and before values. Replace only
qualified dashboard addon trees on current staging; exclude disposable tests and all
unrelated paths. Upgrade installed dashboard addons. If recovery is required, restore
only their prior trees from65ccfa9c and upgrade, preserving business data and other code.
Final identities/results/evidence are recorded in implementation-status.md when observed.

## Follow-up visual findings and qualification history

**Status: qualification in progress; not yet owner-UAT-ready.** The final source,
build, staging identity, screenshot evidence and independent review must be filled
from observed results in the handoff fields below. Earlier passes do not qualify a
later corrected candidate.

### Date wrapping and representative populated views

Actual Arabic rendering at 390px and 768px exposed ISO dates breaking at hyphens.
Each metric/supplier-card date now has a scoped no-wrap span, while a date range
can wrap between its two dates. The existing LTR date direction, source values and
cutoff/period selection logic are unchanged.

The disposable browser qualification uses **27 product fixtures within a
rollback-only test transaction** to exercise populated stock tables and multiple
pages. These are test records only; no staging business records are created or
changed to populate screenshots. Test addons are excluded from deployment.

### Evidence retention and reviewed results

The capture workflow retains the complete **240-capture** set beyond temporary
build-directory cleanup. Final durable delivery must identify its archive,
manifest and checksums; temporary screenshots or contact sheets alone are not an
adequate handoff. Contact sheets support systematic visual review and do not
replace the original captures or prove data/security correctness.

Candidate prefixes below are historical identifiers supplied with the verified
build results; the final handoff requires full immutable SHA/tree identities.

| Candidate | Odoo.sh build | Observed result and evidence boundary |
|---|---|---|
| `90f4` | 38413084 | 65 Odoo tests passed; 120 captures retained. Subsequent actual visual review required the date-wrap correction and broader populated views. |
| `9134` | 38413845 | Qualification failed on a browser selector for the stock entry action. This is not a passing candidate. |
| `0459` | 38414070 | 65 Odoo tests passed; temporary cleanup lost the 240-capture set. A pass without retained visual evidence did not complete the gate. |
| `7930` | 38414698 | 65 Odoo tests passed; 240 captures retained. Visual review of 40 contact sheets found Medium RTL stock-table clipping; correction is in progress. |

**Open visual issue:** RTL stock-table clipping remains Medium and **unresolved**
until a new candidate is rendered and its evidence is reviewed. Do not close the
issue or declare the follow-up UAT-ready based on the `7930` test pass.

### Final handoff fields — fill only after verification

| Field | Result |
|---|---|
| Final source SHA / tree | Pending corrected candidate |
| Dashboard addon versions | Pending confirmation against final candidate |
| Qualification build / Odoo and controller results | Pending final exact-candidate evidence |
| Final 24-combination visual matrix | Pending corrected-candidate review |
| Durable original captures / archive / manifest / checksum | Pending final evidence retention and readback |
| RTL stock-table clipping disposition | Open; awaiting corrected rendering evidence |
| Pre-upgrade staging revision / backup / critical values | Pending fresh verification |
| Dashboard-only staging revision / upgrade build | Pending deployment and module-load confirmation |
| Staging interactions / values / restored preferences | Pending actual application verification |
| Independent final review / remaining findings | Pending separate review |
| Owner UAT | Pending; PR #214 remains draft |

No main merge or production deployment is authorized. Preserve the earlier
qualified staging state until the intended dashboard-only change and its backup
are verified; record the exact rollback source when final deployment is performed.

## Corrected stock candidate and execution interruption

Candidate `c17dd27e4eb982eee995f547d93e5e44de19b6a1`, tree
`d74f08108ad3e7a2da1a4b16dc6e906ce2975f7d`, removes the shared reserved scrollbar
gutter and gives stock identity/location columns readable minimum widths. Numeric
cells stay together and the existing wrapper scrolls horizontally. The native matrix
now checks initial product-edge visibility, text containment and horizontal access
to Source data without page overflow, restoring its origin before capture.
37 frontend checks and static checks pass. Independent code review found no new
Critical/High issue. Visual closure remains pending: build38415574 reported Platform
error, then Cloud Browser transport disconnected. Reconnect/reset attempts did not
return. No staging deployment occurred. Backup18:56:40UTC preserves clean staging
65ccfa9c; 21 metric values and 21 cash-account rows are retained for comparison.
The latest actual retained native evidence remains 793059d4, not c17dd27e.
