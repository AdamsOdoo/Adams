# Finance / Inventory component propagation gate

Status: **reviewed for presentation reuse; not production acceptance**.

24 September continuation: the earlier archive-download blocker below is resolved.
Paired archives were retrieved, checksum/integrity checked and reviewed. Candidate
`e962e671` completed native build 38589101 with zero failures/errors in 126 cases
(283.47s; 109852 queries); optional Manufacturing cases were skipped.
The corrected English HR previews/profile/attendance and Sales count were reviewed
on 94b54982; the final Arabic HR link translations were reviewed on e962e671.
See the current implementation status for staging and acceptance boundaries.
Historical pending statements below describe their original checkpoint.

Reviewed source: `9d35f078bc09cfb78e5352ce246214b092d6a45e`, development build
`38567302`; application code is unchanged from `238445032bf053bab18255c794097f87d42ecfd2`.
Both dashboard modules are `19.0.1.7.0`. The approved HTML hash remains
`36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a`.

## Review completed

- 1440 light English navigation overlay and unmasked diff: the former wrapped
  quick-access labels are resolved; this region's diff is entirely black.
- 768 dark English profitability, stock filters and expanded stock row: inspected
  overlays show matching typography, card/control geometry and alignment.
- 1440 dark Arabic profitability, stock table and navigation: inspected overlays
  preserve RTL hierarchy, numeric direction, density and row alignment.
- These complete the last-state review left open by the environment interruption.
  The preceding 1920/1366 light and 1440 drawer/table reviews are recorded in the
  September 23 continuation record. No baseline was replaced, no implementation
  difference masked, and no similarity percentage used as acceptance.

Current private evidence directories under the build's
`data/adams_dashboard_reference_evidence/`: `finance-dkm1gcbl` (1440 English),
`finance-pvlgaozl` (768 dark), `finance-o7oh08q6` (1440 Arabic).
Reference and actual manifests/captures remain separate, with paired overlays/diffs.

## Explicitly still open

- The native result is 126 post-tests, zero failed/errors, completed at
  2026-09-23 19:51:17 UTC; the Odoo.sh Failed badge has a separate unresolved cause.
  Do not represent that build as cleanly qualified.
- Private ZIP download from the build editor timed out again in the restored
  browser. Durable retrieval is **not complete**, despite server-side ZIPs existing.
- Real staging is still the earlier 1.6.0 candidate. Source/module/asset identity,
  deployed visual regression and real authorized journeys must be rechecked after
  the final dashboard-only staging upgrade.
- Sales, Procurement, CRM and all HR tabs still require approved-reference parity.

## Next implementation batch

Sales now reuses the approved header, cards and navigation. Its existing ranking
services feed a shared Owl ranking template; recent documents use six-row pages,
server-clamped offsets and a truthful total/page caption. The quotation document
count uses `sale.report.order_reference:count_distinct` with the exact monetary
report domain and normal source permissions. Delivery remains directly visible.

The native reference harness adds Sales populated cards, both ranking pairs,
document tabs/page two, margin and both quantity-unit states at 1440 light English
and dark Arabic. These new captures require review; implementation is not parity.
Local controller checks: 71 passed; XML/light-dark SCSS/Arabic format checks passed.
No production/main changes, business-app installs or PR merge/readiness change.
