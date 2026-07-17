# Screen spec — COD reconciliation workspace

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Static
> prototype extension only; implementation stays gated (UI-U1/U2/U3 CLOSED;
> the workspace itself is a Wave 5 deliverable per the COD product doc §9).
> Source: `cod-reconciliation.html` (+ `../assets/prototype.css`, unchanged).
> All copy, names, and amounts are illustrative (MBQ-22); no backend method,
> field, or XML ID is asserted.

## Purpose
Answer the operational COD questions Odoo and Shopify cannot answer alone:
*was the cash collected at the door, how much, by whom, and does it match what
was delivered?* Every order is described by **three independent dimensions**
(commercial / fulfillment / collection — PD-COD-1, never a merged status) and
carries the **five-value ledger** (original / fulfilled / collected /
outstanding / cancelled — PD-COD-3).

## Primary role
**Connector User** — records collection events, works the outstanding queue,
opens return flows. **Connector Administrator** — the only role that resolves
discrepancies, approves remainder cancellation, curates the approved
manual-gateway list, and picks the authoritative evidence source per store.
The gallery labels every Administrator-only region explicitly.

## Data shown
- **Stat chips**: open COD orders · collected today · outstanding total
  (warning when non-zero) · discrepancies (danger when non-zero).
- **Queue table**: one row per COD order with **three dimension badges**
  (commercial / fulfillment / collection), outstanding amount (`sc-mono`),
  and outstanding age; defaults to actionable collection states, sortable by
  outstanding age (COD doc §7). Discrepancy rows are `has-exception` and the
  discrepancy queue always renders above the table.
- **Value-ledger card** (selected order): outstanding leads as the dominant
  figure (warning band), the other four values in a quiet 2-column grid, an
  honest cadence line ("recomputed on every delivery validation and
  collection event… append-only"), and the combined collection/delivery
  timeline (validated picking, collection event with amount + source + actor
  + reference, aging note).
- **Partial-collection entry drawer** (static `sc-dialog` mock): amount
  pre-filled with the due amount (override requires a reason), evidence
  source (Shopify transaction / User entry / Manual reconciliation — the
  fourth source, courier integration, is reserved future scope, OQ-COD-4),
  optional note/reference, Record collection (primary) + Cancel. Explicit
  footer: append-only event; **no "mark fully paid" shortcut for partial
  amounts** (rule L-3).
- **Discrepancy review card**: "#1038 — Courier reported return · stock NOT
  restored · awaiting warehouse validation" — calm, high-visibility danger
  exception with the stock-truth explanation and a deep link to the Odoo
  return flow (PD-COD-2).

## Badge mapping (per dimension)
| Dimension | Value → family | Basis |
| --- | --- | --- |
| Commercial | Confirmed→success · Remainder cancelled→neutral | COD doc §2.1 |
| Fulfillment | Dispatched / Partially delivered→info · Fully delivered→success · Return to origin — in transit→warning · Returned — validated→success | COD doc §2.2; severity words per fulfillment model §9 |
| Collection | Nothing collected→neutral · Partially collected→warning · Fully collected→success · Discrepancy→danger · Refunded→neutral | COD doc §2.3 |

## Actions per role
- **Connector User**: record a collection event (drawer), open an order,
  open the return flow for the warehouse, filter/sort. No resolution actions.
- **Connector Administrator**: resolve discrepancies (Review evidence —
  accept adjusted amount / reassign authoritative evidence / write off, each
  with a mandatory reason, resolutions recorded as decisions, originals never
  edited — COD doc §3.14, §5); open gateway settings from the empty state.
- Nothing on this surface creates accounting entries — the RA-010 boundary
  (COD doc §6) keeps the ledger operational only.

## States shown (gallery order)
1. **Loaded** — chips, discrepancy card pinned first, 5-row queue exercising
   all three dimensions (including the legitimate closed state
   *remainder cancelled + partially delivered + fully collected*, scenario
   3.10), ledger card, timeline, and the static collection drawer.
2. **Empty (education)** — CSS-only cash+truck illustration; copy teaches the
   precondition: COD appears only after the Administrator approves a manual
   gateway, and COD is classified by transaction evidence, never by a
   pending status alone (COD doc §2.3 inference; lifecycle doc §1.1).
3. **Loading** — skeleton chips + card + honest loading line; never blank.
4. **Discrepancy-heavy** — danger band "4 collection discrepancies need the
   Administrator"; queue of danger exceptions: stock-not-restored return,
   short courier remittance (Δ shown), reconnect divergence (Shopify Paid vs
   ledger outstanding — scenario 3.16: nothing auto-applied); footer restates
   the append-only resolution rule.

## Tokens / components used
Shell (`sc-topbar`/`sc-appbar`/`sc-breadcrumb`); `sc-chip`
(+`is-warning`/`is-danger`); `sc-band` (warning for the ledger lead figure,
danger for the discrepancy state); `sc-exception sc-exception--danger` +
`sc-owner` (discrepancy cards); `sc-list` (+`has-exception`, `col-age`
responsive hiding); `sc-status` all five families with icons; `sc-card`,
`sc-grid--2`, `sc-ro` (ledger values); `sc-activity` + `sc-cadence`
(timeline); `sc-dialog` + `sc-field`/`sc-label`/`sc-input`/`sc-help`
(drawer mock — inputs are `readonly` since the prototype has zero JS);
`sc-empty`; `sc-skel` + `sc-loadingline`; `sc-mono` tabular numerals on all
amounts. Icons are inline-SVG P9 placeholders.

## Accessibility
- All three dimensions are worded badges with icons; color never the only
  signal (WCAG 1.4.1). Danger is reserved for discrepancy/decision states;
  the calm-but-unmissable treatment uses position (pinned first) + icon +
  language, not louder color.
- Only verified contrast pairs from `../accessibility/contrast-table.md`;
  no new pair introduced.
- Drawer inputs have visible `sc-label`s plus `aria-label`s where the label
  needs expansion; the drawer group carries `role="group"` with an
  accessible name; loading regions are `aria-busy="true"`; decorative SVGs
  `aria-hidden="true"`; table headers `scope="col"`.
- RTL-safe: logical properties only; monetary strings render with tabular
  numerals and no directional styling. ≤900px compact shell; ≤640px hides
  the optional `col-age` column so order · dimensions · outstanding survive
  at 375px.

## Traceability
- Three-dimension model, 16 scenarios, five-value ledger, rule L-3,
  evidence-source policy, discrepancy resolution, stock-restoration rule,
  reconnect behaviour, workspace requirements:
  [`../../02-product/cod-lifecycle-and-reconciliation.md`](../../02-product/cod-lifecycle-and-reconciliation.md) §1–§5, §7 (PD-COD-1..5; scenarios 3.8, 3.10, 3.14, 3.16).
- Manual-gateway approval + COD policy overlay:
  [`../../02-product/sales-order-lifecycle-and-confirmation-policy.md`](../../02-product/sales-order-lifecycle-and-confirmation-policy.md) §1.1, §2.2, §7.
- Badge severity vocabulary:
  [`../../02-product/shopify-fulfillment-status-model.md`](../../02-product/shopify-fulfillment-status-model.md) §9.
- Visual system: `../README.md`,
  `../../03-architecture/premium-ui-ux-design-system.md`.
