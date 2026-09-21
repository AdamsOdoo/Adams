# ED-UI-20260921 — current-design visual consistency

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
