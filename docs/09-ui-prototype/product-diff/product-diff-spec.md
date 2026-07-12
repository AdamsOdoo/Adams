# Screen spec — Product diff / preview (S7)

> **Status: U0 prototype spec. Proposed, not accepted.** Inherits S7 / DEC-007
> / Part B §A / Part D §12 (the five-state preview; destructive-write diff;
> draft-first export; price source-of-truth gate) from
> `../../02-product/ui-ux-final-design-spec.md`. Source: `product-diff.html`.
> **Visual prototype only — no RPC method, field contract, or mutation logic is
> invented.** Copy illustrative (MBQ-22).

## Purpose
Always show “what will happen to what” before it happens. The preview is the
screen’s center of gravity, not an interstitial.

## Elements (all present in `product-diff-update-1366.png`)
- A four-column diff table: **Field · Odoo value · Shopify value · Result /
  source of truth**.
- **Source-of-truth indicator** per changed field (“Odoo is the price
  authority”), so the connector never appears to guess which system wins.
- **Changed fields ranked by importance** (price, compare-at, title, status
  first); **unchanged fields de-emphasized** (“No change”, secondary color).
- **Protected merchant-owned fields** clearly flagged (warning-tint row + lock
  + “Kept — merchant-owned”) and **never overwritten**.
- **Variant-level differences** (indented variant rows, e.g. Brass/Large price).
- **Price & compare-at-price** differences shown explicitly.
- **Image ownership / protection** status (connector-owned vs merchant-owned;
  a merchant image is “left as-is, never deleted by omission”).
- **Validation warnings** (`.sc-ready--warn`).
- **Explicit consequence summary** before the action; draft-first stated
  (publish is a separate explicit step).
- **One confirm + one cancel**; destructive/high-impact changes are **never
  silently pre-selected**.

## States rendered
| State (five-state preview) | File | Behavior |
| --- | --- | --- |
| To update (success path) | `product-diff-update-1366.png` (+ `-768`, `-375`) | Full diff; 4 changes + 1 protected kept; confirm = “Confirm 4 changes”. |
| Blocked | `product-diff-blocked-1366.png` | Price source-of-truth unset → danger band. The Result column **asserts no authority and computes no outcome**: price/compare-at/variant-price rows read “Choose a price authority to calculate this”; the other changed rows read “Held until a price authority is chosen”; the table still shows the current Odoo & Shopify values for comparison. **No “Odoo is the price authority”, no resulting price, no source-of-truth check, no struck-through price, and no Confirm button** — the only primary action is the **fixer** (“Set price source of truth”); Cancel is secondary. No high-impact change is pre-selected (review `4950255482` §3). |
| Loading | `product-diff-loading-1366.png` | Skeleton rows + “Computing the diff…”. |
| Empty | `product-diff-empty-1366.png` | “Nothing staged to preview” + the next useful action. |
| Manual review | (behavior defined) | Ambiguous items route to the matching center (S6); the diff itself is not a reviewer queue — stated, not invented. |

“To create”, “To skip”, and “Draft-pending-publish” from the accepted
five-state preview are represented within the update view (status row =
draft-pending-publish; skip/blocked reasons shown, never guessed).

## Tokens
`--sc-info` for the normal preview band, `--sc-danger` for blocked; changed
values in `--sc-text-primary`/500 with struck-through old value (**never in the
blocked state**); protected rows in `--sc-warning-bg`; **blocked rows in
`--sc-danger-bg` with a `--sc-danger-text` “Authority not set” marker**; variant
rows on `--sc-surface-0`; one `--sc-accent` primary.

## Accessibility
Column-header associations; changed state conveyed by struck old value + new
value + labelled source-of-truth, not color alone; protected rows carry a text
label; a confirm dialog (UI-U1) traps focus and focuses the non-destructive
control first. See `../accessibility/keyboard-and-focus-notes.md` §2.

## Performance (mapped)
PB-10 the diff reads bounded field sets/aggregates; large catalogs paginate
(PB-9); no unbounded recordset is fetched to render a preview.

## Proposed vs inherited
- **Inherited:** the five-state preview; destructive-write-by-omission
  highlighting; draft-first + explicit publish; price-SoT gate; protected fields.
- **Proposed:** the exact four-column table layout; ranked-changed / dimmed-
  unchanged ordering; the inline source-of-truth chips; the consequence-summary
  wording.
- **Not invented:** field names shown are illustrative; no export RPC, no
  variant-mutation contract, and no media-delete behavior is asserted (media is
  detach-only / left-as-is per the accepted posture).
