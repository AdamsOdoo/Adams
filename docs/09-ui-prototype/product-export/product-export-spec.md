# Product export flow — screen spec

> Prototype extension (Fable gap-closure mission, 2026-07-16), built on the
> accepted U0 visual baseline and the product-diff visual language. Design
> artifact only — no implementation is authorized by this file. Source of
> truth for behavior:
> [`../../02-product/product-export-operating-model.md`](../../02-product/product-export-operating-model.md).

## 1. Purpose

Make the controlled export contract visible end to end: the connector exports
**only explicitly selected products, only allowlisted fields, only after a
confirmed fresh-read diff**, and never trusts its own memory of Shopify's
state. Five wizard steps — Select → Preview → Confirm → Apply → Results —
with the stale-preview hold (changed-since-read gate) shown as its own state.

## 2. Primary role

- **Connector User** — selects products, runs previews (reads only), watches
  progress and results.
- **Connector Administrator** — confirms the previewed diff (the review act;
  the confirm screen carries an explicit role note) and resolves review
  cases. Confirm is the single gate between reads and writes.

## 3. Data shown

- **Selection list**: per-product export checkbox (opt-in, default off),
  binding status ("Bound — will update" / "Not on Shopify — will create as
  DRAFT" / "Held — more than 3 options"), freshness including the
  **"Changed on Shopify since last read — preview will re-read"** flag, and
  the price-authority note (prices included only because the store records
  Odoo as price authority; otherwise omitted from the payload entirely).
- **Preview diff** (product-diff visual language, 4 columns): exportable
  Odoo-owned rows as normal changed rows; **merchant-owned fields greyed with
  lock icons** (collections, metafields & SEO, publication/channels —
  "never in the export payload / structurally untouchable");
  **complete-variant-list guard notice** (full desired variant list verified;
  any remote-variant deletion must be explicitly enumerated and confirmed or
  the job blocks); **DRAFT/unpublished default notice** with 24-hour preview
  expiry.
- **Confirm summary**: counts (updates, creates-as-DRAFT, field changes,
  variant deletions = 0, checksum-proven images), merchant-field and
  publication guarantees, role note.
- **Progress**: per-record streaming rows — succeeded (verification read
  confirmed), in-progress (duplicate-safe create), waiting; throttle framed
  as pacing, not error.
- **Results**: summary chips 14 succeeded / 1 failed / 3 uncertain; band line
  **"3 uncertain — reconciliation reads scheduled"** with the three outcomes
  (adopt+bind / review / safe retry); per-record list including the
  >3-options failure ("never truncated") and the timed-out uncertain row;
  review CTA.

## 4. Actions per role

| Action | User | Administrator |
| --- | --- | --- |
| Select / deselect products for export | Yes | Yes |
| Run preview (fresh read, no writes) | Yes | Yes |
| Confirm previewed diff (starts writes) | No | Yes |
| Re-preview / skip a stale-held product | Yes | Yes |
| Open review queue / job log from results | Yes | Yes |

No auto-apply exists anywhere; review-then-apply is the only mode.

## 5. States in the gallery

1. **Selection** — info band, opt-in list, binding + freshness columns,
   primary action reads only ("Preview 3 products — reads only").
2. **Preview** — fresh-read diff, locked merchant rows, variant-list guard,
   DRAFT notice.
3. **Changed-since-read blocked** — warning band; timeline (previewed 10:32,
   remote changed 10:41, nothing written); re-preview or skip; no
   carry-over of the stale diff.
4. **Confirm** — summary counts + role note; single primary confirm.
5. **Apply / progress** — `aria-busy` band; streaming per-record rows.
6. **Results with uncertain** — warning band; honest counts; reconciliation
   reads scheduled; review CTA.

## 6. Tokens

Only `--sc-*` tokens. Diff table reuses the accepted `sc-diff` component:
`is-changed` for Odoo-owned changes, `is-protected` (warning tint + lock)
for merchant-owned rows, `sc-variant-row` for variant lines. Wizard chips
reuse `sc-steps`. Status families: info (preview/confirm bands, in-progress),
warning (stale hold, uncertain), danger (failed row, held >3-options
selection — reviewer-decision semantics via the hand icon), success
(confirmed writes). Counts use `sc-mono`. No new token introduced.

## 7. Accessibility

- Checkboxes carry explicit `aria-label`s naming the product.
- Wizard steps are text + numbered chips; the current step is a word, not a
  color change alone.
- Lock/clock/hand icons are `aria-hidden`; adjacent text states the meaning
  ("Kept — structurally untouchable", "Fresh preview required").
- Progress band uses `aria-busy="true"`; spinner has `role="img"` +
  "In progress" label.
- Diff and selection tables are real `<table>`s with `data-label` cells for
  the ≤640px stacked reflow; one primary button per screen.

## 8. Traceability

| Element | Source |
| --- | --- |
| Deliberate per-product opt-in; never a background mirror | product-export-operating-model.md §1 (PD-PX-1), §13.1 |
| Field-ownership matrix; merchant-owned fields structurally absent | §2 (PD-PX-2/3) |
| Price fields only when store is Odoo-authoritative | §6 (DEC-007 rule) |
| Complete-variant-list guard; enumerated deletions or block | §3–§4 (C-PROD-05, D-015-3/5) |
| >3 options → hold, never truncation | §4 |
| DRAFT on create, unpublished; publish = separate explicit step | §7 (PD-PX-5) |
| Preview = fresh read; 24 h expiry; changed-since-read abort to fresh preview | §8 (D-015-5/6) |
| Duplicate-safe create (upsert identity + SKU gate) | §3, §9 |
| Uncertain outcome → reconciliation read (adopt / review / retry), no blind retry | §9 (DEC-031 Layer 2, PD-PX-6) |
| Checksum-proven media ownership; detach-only | §5 (015B layer) |
| Throttle framed as pacing (cost-based limit) | §12 |
| Review-then-apply only; no auto-apply flag | §13 |
| Two-role confirm gating | ../../02-product/connector-roles-and-permissions.md |
| Diff visual language | ../product-diff/product-diff-spec.md |
