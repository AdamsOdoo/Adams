# Screen spec — Order review detail

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Static
> prototype extension only; implementation stays gated (UI-U1/U2/U3 CLOSED).
> Source: `order-review.html` (+ `../assets/prototype.css`, unchanged). All
> copy and record names (S00342 etc.) are illustrative (MBQ-22); no backend
> method, field, or XML ID is asserted.

## Purpose
Explain one Shopify order end-to-end — what Shopify says, what the connector
did and why, and exactly what a person must do (or that nothing is needed).
Layout: **two columns** — left = evidence (summary card, line items, connector
timeline); right = decision (required-action card, audit trail, related
records). The required-action card is the single place actions live.

## Primary role
**Connector User** — owns every decision on this surface (COD approval,
duplicate resolution, mismatch follow-up, divergence reconciliation). The
**Connector Administrator** is present only as the author of the referenced
policies (approved manual-gateway list, `require_approval` overlay).

## Data shown
- **Summary card**: order name + store; badge row = Shopify financial badge,
  Shopify fulfillment badge, connector-state badge (three separate concepts,
  never merged); key/value block — masked customer, total with the
  same-currency note, gateway (with a "Manual gateway — on the approved list"
  `sc-owner` chip for COD), placement/discovery source, active policy.
- **Line items**: qty / unit / line total (tabular numerals) + a **per-line
  binding status** badge (Bound → success).
- **Connector timeline**: imported → policy applied → outcome (confirmed /
  waiting / review opened), each with a plain-language reason and relative
  timestamp — no raw tokens, no bare log lines.
- **Right panel**: required-action card (owner chip names the role), audit
  trail (append-only, actor + timestamp), related records (Odoo SO, Odoo
  customer, COD workspace); absent records are stated honestly ("No Odoo
  sales order yet — created only when the payment resolves").

## States shown (gallery order)
1. **Waiting — PENDING card payment.** Neutral badges; the required-action
   card is an info consequence note: "waiting; no action needed", automatic
   re-check + 7-day wait-expiry tracking. No buttons — a wait state is not a
   decision (lifecycle doc §2.1: card PENDING = Wait, never confirm).
2. **COD approval required.** Danger band + hand icon; quotation S00342
   already exists with its permanent binding; action card offers
   **Approve & confirm order** (primary) vs **Decline — keep as quotation**
   (secondary), with the stock consequence spelled out and the decision
   recorded with actor + timestamp (manual-gateway overlay,
   `require_approval` — lifecycle §1.1/§2.2).
3. **Blocked — manual review (duplicate risk).** Danger band + hand icon,
   "not a system failure" language; an unbound Odoo SO carries this order's
   reference → fail closed, nothing created (binding-conflict sub-reason,
   lifecycle §3/§4). Single action: **Compare side by side**; link/import
   choices live behind the comparison so decisions are evidence-based.
4. **Financial mismatch — fail closed.** Danger band; receipt-style
   `sc-evidence` breakdown (merchandise / shipping / tax / total, Shopify vs
   calculated, Δ 4.50 on the tax row); "mandatory and unbypassable" total
   check, no SO created (DEC-007 via lifecycle §4). Actions: Re-check totals,
   View technical detail — no override exists.
5. **Order-edited divergence.** Shopify `orders/edited` after confirmation:
   evidence refreshed with prior snapshot retained, Odoo SO **never silently
   rewritten**; before/after table + review actions (Compare, Acknowledge
   with reason) (lifecycle §2.3/§3 "evidence refresh only").

## Actions per role
- **Connector User**: Approve & confirm / Decline (state 2); Compare side by
  side (state 3); Re-check totals, View technical detail (state 4); Compare
  before/after, Acknowledge with reason (state 5). At most one primary button
  per state (state 2 only).
- **Connector Administrator**: no direct action here; changing the policies
  that produce these states happens in Configuration.

## Tokens / components used
Shell (`sc-topbar`/`sc-appbar`/`sc-breadcrumb` with a 4-level breadcrumb);
`sc-cols` (2fr/1fr, stacks at ≤900px); `sc-band--danger`; `sc-card` /
`sc-card--compact`; `sc-status` (success/neutral/danger/info); `sc-owner`;
`sc-kv`; `sc-list` (line items); `sc-evidence` + `sc-match--same/--no`
(breakdown tables — reflow to labelled stacked cards at ≤640px via
`data-label`); `sc-activity` (timeline + audit); `sc-consequence` (the
no-action wait note); `sc-ready--fail` (why-held explainer); `sc-btn`
primary/secondary/quiet. Manual review uses the **danger family + hand icon +
decision language**, per the accepted U0 token map.

## Accessibility
- Badges always carry text + icon; color never the sole signal (WCAG 1.4.1);
  manual review vs technical failure distinguished by icon/owner/copy.
- Only verified contrast pairs are used (`../accessibility/contrast-table.md`);
  no new color pair.
- Tables use `scope="col"`; every `sc-evidence` cell carries `data-label` for
  the mobile card reflow; decorative SVGs are `aria-hidden="true"`; button
  targets ≥ 36px block-size.
- RTL-safe: logical properties only, no directional inline styles; the
  two-column grid mirrors automatically under `dir="rtl"`.

## Traceability
- Wait/confirm/review semantics, manual-gateway overlay, transition and edit
  handling, duplicate binding rule, financial gate:
  [`../../02-product/sales-order-lifecycle-and-confirmation-policy.md`](../../02-product/sales-order-lifecycle-and-confirmation-policy.md) §1.1, §2.1–2.3, §3, §4.
- COD classification and downstream collection tracking:
  [`../../02-product/cod-lifecycle-and-reconciliation.md`](../../02-product/cod-lifecycle-and-reconciliation.md) §2.3, §7.
- Badge severity vocabulary:
  [`../../02-product/shopify-fulfillment-status-model.md`](../../02-product/shopify-fulfillment-status-model.md) §9.
- Visual system + manual-review-danger convention: `../README.md`,
  `../../03-architecture/premium-ui-ux-design-system.md`.
