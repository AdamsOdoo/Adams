# Inventory workspace — screen spec

> Prototype extension (Fable gap-closure mission, 2026-07-16), built on the
> accepted U0 visual baseline. Design artifact only — no implementation is
> authorized by this file. Source of truth for behavior:
> [`../../02-product/inventory-operating-model.md`](../../02-product/inventory-operating-model.md).

## 1. Purpose

One workspace answering, in order: *is inventory export healthy, what is
about to be pushed, and what needs a human?* It presents the accepted
operating model honestly: Odoo per-mapped-location free quantity (`free_qty`)
is the exported figure; every push is a read → compare → set
(compareQuantity CAS) cycle; pending pushes coalesce last-value-wins per
item × location; the Shopify→Odoo direction is read/verify only — divergences
become review cases, never automatic writes.

## 2. Primary role

- **Connector User** — sees everything, resolves divergence review cases,
  triggers manual preview-first pushes, opens Odoo stock.
- **Connector Administrator** — everything above, plus the only role that can
  confirm the **first-push baseline** for a mapped pair and manage location
  mappings. The confirm button on the baseline screen carries an explicit
  "Connector Administrator only" owner chip.

## 3. Data shown (illustrative values, real vocabulary)

- Stat chips: mapped items, pending pushes, pushed last hour, divergences
  (danger when non-zero), unmapped items ("N not synced" — warning, never a
  silent drop).
- Location-mapping table: Odoo location ↔ Shopify location, status
  (Active / **Needs review — pushes suspended** for a deactivated Shopify
  location), last push.
- Pending-push table: product/variant, location, current Odoo free qty, last
  pushed value + age, coalescing note (**"superseded ×3"** = three newer
  stock events replaced the pending target; only the latest absolute value is
  sent), CAS status (Queued / Compare mismatch — retry n of 3 / Sent —
  confirmed / **Verifying remote result…**).
- Divergence review case: the three values (Shopify read, last pushed, Odoo
  now) plus a suggested explanation explicitly framed as interpretation
  ("our interpretation, not a verified fact") — never asserted.
- Negative-quantity warning: true Odoo value (−4) alongside the clamped 0
  pushed to Shopify.

## 4. Actions per role

| Action | User | Administrator |
| --- | --- | --- |
| View chips, mappings, queue, logs | Yes | Yes |
| Resolve divergence (push Odoo value / adjust in Odoo / dismiss with note) | Yes | Yes |
| Map / remap / re-confirm locations | No | Yes |
| Confirm first-push baseline | No | Yes |
| Cancel baseline preview (writes nothing) | Yes | Yes |

No action anywhere force-writes past the compare check or replays an
uncertain mutation blind.

## 5. States in the gallery

1. **Loaded / healthy** — success band, chips, mappings (incl. one suspended
   inactive-location row), pending pushes, divergence review, unmapped count.
2. **First-push guard — baseline preview** — info band; Shopify-current vs
   Odoo-computed vs push-target per pair; consequence note; Administrator
   confirm gate; cancel writes nothing.
3. **Loading** — skeletons plus a text loading line; never blank.
4. **Empty / setup** — neutral band + setup CTA ("Map locations") and the
   three-step path; states that nothing moves until mapping + confirmed
   baseline.
5. **Uncertain after mutation** — warning band; queue row shows
   "Verifying remote result…"; copy explains the verification read decides
   applied / not-applied before any retry (fails closed to review otherwise).
6. **Negative-quantity clamp** — warning band + case card: pushed 0, true
   −4 kept visible.

## 6. Tokens

Only `--sc-*` tokens from `../assets/prototype.css`. Status families per the
accepted map: success (healthy band, confirmed sends, active mappings), info
(queued CAS, baseline preview band, consequence note), warning (coalesce/CAS
retry, clamp warning, unmapped count, uncertain verification), danger
(divergence review + suspended mapping — reviewer-decision family, told apart
from technical failure by the hand icon and copy, not color). Numbers use
`sc-mono` (tabular numerals). No new token introduced.

## 7. Accessibility

- State words always accompany color (chips, `sc-status` badges).
- Icons are `aria-hidden` inline-SVG placeholders (P9); adjacent text carries
  meaning.
- Loading regions use `aria-busy="true"` plus a visible text line.
- Tables are real `<table>` elements with `<th>` headers and `data-label`
  attributes so the ≤640px stacked-card reflow keeps row labels.
- One primary button per screen (baseline confirm); destructive/none here.
- Focus-visible and reduced-motion behavior inherited from the shared
  stylesheet.

## 8. Traceability

| Element | Source |
| --- | --- |
| `free_qty` per mapped location as exported figure; forecast opt-in only | inventory-operating-model.md §1 |
| Location mapping uniqueness / inactive location → "pushes suspended" + review | §2, §7 |
| First-push guard: preview + explicit confirm + recorded source of truth (MBQ-33/34, RA-008) | §3 |
| Last-value-wins coalescing ("superseded ×n"), absolute sets | §4.2 |
| Read→compare→set CAS, bounded 3 retries, never ignoreCompareQuantity | §4.4 |
| Divergence review case with three values + [Inference]-labelled explanation | §5 |
| Uncertain outcome → reconciliation read before retry (DEC-031 Layer 2) | §6 |
| Negative free qty → clamp to 0 + warning carrying true value | §7 |
| Unmapped items skipped with surfaced count | §7 |
| Audit line (old → new value, compare basis, idempotency key) | §8 |
| Two-role gating (Administrator confirm) | ../../02-product/connector-roles-and-permissions.md |
