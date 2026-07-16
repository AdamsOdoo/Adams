# Screen spec — Orders workspace

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Static
> prototype extension only; implementation stays gated (UI-U1/U2/U3 CLOSED).
> Source: `orders.html` (+ `../assets/prototype.css`, unchanged). All copy is
> illustrative (MBQ-22); no backend method, field, or XML ID is asserted.

## Purpose
Answer, for every Shopify order the connector tracks: *what did Shopify say
about the money and the shipment, what did the connector do about it, and does
anything need a person?* — one row per order, all state families visible as
separate badges, never merged into a single status.

## Primary role
**Connector User** — works the list, opens rows, resolves review items.
The **Connector Administrator** appears only through consequences: the footer
names the active `order_confirmation_policy` (P1) and `manual_gateway_policy`
(Require User approval), which the Administrator sets in Configuration
(policy inventory: sales-order lifecycle doc §1.1/§7).

## Data shown (read model only)
- **Header**: store selector (per-store scoping) + four stat chips — imported
  today, awaiting payment (PENDING/AUTHORIZED wait states), needs review
  (danger), failed (danger).
- **Filter row**: financial status, fulfillment status, policy result, COD
  only, date window, plus search. Active filters render as removable facets.
- **Table columns**: Shopify order name · customer (**masked** variant —
  initialled name + masked email, credential/PII posture) · financial badge ·
  fulfillment badge · connector state (plain words, never a raw token) ·
  total (`sc-mono`, shop currency) · policy outcome.
- The loaded state exercises **all 8 financial states** across rows:
  PAID, PENDING (×2: card wait + approved-COD), AUTHORIZED, PARTIALLY_PAID,
  PARTIALLY_REFUNDED, REFUNDED, VOIDED, EXPIRED.

## Badge mapping (traceable, per row)
| Family | Value → label → family | Basis |
| --- | --- | --- |
| Financial | Paid→success · Authorized — capture pending→info · Payment pending→neutral · Partially paid→warning · Partially refunded→warning · Refunded/Voided/Authorization expired→danger | `sales-order-lifecycle-and-confirmation-policy.md` §2.1 (last column) |
| Fulfillment | Not shipped→neutral · Partially shipped→info · Fully shipped→success · (unknown value→neutral + help icon) | `shopify-fulfillment-status-model.md` §2, §7, §9 |
| Policy outcome | Confirmed→success · Quotation / Waiting — no order yet / No action — surfaced→neutral · Review — …→**danger + hand icon** | lifecycle doc §2.1 matrix; manual review = danger family per the accepted U0 token map |
| COD marker | `sc-owner` chip "COD — manual gateway" on the row | COD classification by `manualPaymentGateway` + approved list, never PENDING alone (lifecycle §1.1; COD doc §2.3) |

REFUNDED/VOIDED/EXPIRED rows appear only because they were **already
imported** ("Bound earlier · surface only") — first-import of those states is
a policy skip with no Odoo record (lifecycle §2.1).

## Actions per role
- **Connector User**: open a row (→ order-review surface), filter/search,
  "Check now" (enqueue-only), "Try again" on error, "View affected order" on
  the schema warning. No inline mutation, no confirm/approve from the list.
- **Connector Administrator**: nothing extra on this surface; policy changes
  live in Configuration (referenced, not rendered here).

## States shown (gallery order)
1. **Loaded** — chips + filters + 9-row table covering the 8 financial states.
2. **Loading** — skeleton chips + skeleton rows + honest loading line; never blank.
3. **Empty** — CSS-only illustration (layered inline-SVG order + sync glyphs in
   `--sc-border-strong`), education copy about the 30-day import window /
   15-minute scan, one quiet "Check now" action.
4. **Error** — danger band, plain reason (rate limit), "nothing was lost",
   last-successful-load line, Try again + Error Center link; health chip degraded.
5. **Manual-review emphasis** — danger band + hand icon ("4 orders are waiting
   on a decision — not system failures"), facet filter applied, all rows
   `has-exception` with a "Why it waits" column.
6. **Unknown-schema warning** — warning band naming family, raw value, store,
   API version, affected count (the §7 five-point contract of the fulfillment
   status model: preserve raw, display unknown, never success, pause
   automation, actionable warning); affected row shows
   "Unknown status (READY_FOR_HANDOFF)".

## Tokens / components used
`sc-topbar` / `sc-appbar` / `sc-breadcrumb` shell; `sc-band`
(danger/warning); `sc-chip` (+`is-danger`); `sc-listbar`, `sc-search`,
`sc-facet`; `sc-list` (+`has-exception`, `col-source` responsive hiding);
`sc-status` all five families; `sc-owner`; `sc-btn` secondary/quiet;
`sc-empty`; `sc-skel` + `sc-loadingline`; inline-SVG icon sprite (P9
placeholders). Type/spacing per accepted scale; totals in
`font-variant-numeric: tabular-nums` via `sc-mono`. `badge-unknown` has no
dedicated token in the accepted set — the prototype renders it with the
neutral family + help-circle icon and flags the token as a follow-up for the
design system (fulfillment model §9).

## Accessibility
- Every state word is text; color only reinforces (WCAG 1.4.1). Manual review
  is distinguished from technical failure by **hand icon + decision language**,
  not color.
- All color pairs reuse verified `accessibility/contrast-table.md` pairs — no
  new pair introduced.
- Error band `role="alert"`; loading region `aria-busy="true"`; icon SVGs
  `aria-hidden="true"`; pager buttons carry `aria-label`s; table headers use
  `scope="col"`.
- RTL-safe: logical properties only (inherited from the shared stylesheet);
  no left/right inline styles. At ≤900px the compact Menu shell applies; at
  ≤640px the optional `col-source` column hides so order · badges · total ·
  outcome stay visible.

## Traceability
- Financial states, 3 policies, manual-gateway overlay, wait/skip/review
  semantics: [`../../02-product/sales-order-lifecycle-and-confirmation-policy.md`](../../02-product/sales-order-lifecycle-and-confirmation-policy.md) §1.1, §2.1–2.3, §7, §8.
- Fulfillment badge vocabulary + unknown-value contract:
  [`../../02-product/shopify-fulfillment-status-model.md`](../../02-product/shopify-fulfillment-status-model.md) §2, §7, §9.
- COD identification: [`../../02-product/cod-lifecycle-and-reconciliation.md`](../../02-product/cod-lifecycle-and-reconciliation.md) §2.3.
- Visual system: `../../03-architecture/premium-ui-ux-design-system.md`;
  accepted U0 baseline conventions in `../README.md`.
