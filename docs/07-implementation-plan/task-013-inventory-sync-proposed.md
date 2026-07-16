# Task 013 — Inventory Sync (Proposed)

> **Superseded (2026-07-16, Fable gap-closure mission):** this early scope
> proposal is retained as history only. The canonical, decision-closed
> specification is `task-013-inventory-sync-implementation-packet.md` (plus its dated
> gap-closure addendum). Do not use this file as an implementation source.

> Planning-only future implementation task spec, part of the MVP domain
> implementation-slicing sequence
> ([`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md),
> Area 4). Describes scope/boundary/approach only — MBQ-32/MBQ-33/MBQ-34
> remain open or only partially resolved.

## Status

**Proposed only. Not authorized.** Depends on Task 010 (product
import/variant binding) existing — inventory depends on `core` +
`product` only and is a sibling of `sale`, never depended on by
`fulfillment` (Part C, module-ownership section) — plus foundation Tasks
002/003 and the not-yet-defined "inventory domain gate"
(`ui-ux-implementation-task-map.md` Group 13). This document does not
authorize, start, or imply authorization of any of the above.

## Objective

Synchronize Odoo stock quantities to Shopify as the standing
Odoo-is-source-of-truth direction, through an explicit, non-inferred
Odoo-location ↔ Shopify-Location mapping, with a mandatory first-push
safety guard and no autonomous bidirectional conflict resolution.

## Preconditions

- Task 010 merged and reviewed (product-variant binding must already
  resolve — the only prerequisite shared with fulfillment, per the
  accepted "product's product-variant binding" cross-domain rule).
- Foundation Tasks 002/003 merged and gate-opened.
- The inventory domain gate explicitly opened.
- MBQ-33 (first-push guard granularity) and MBQ-34 (ongoing apply-mode)
  resolved by ChatGPT for this task's own final §9 prompt. Both remain
  formally open per
  [DEC-015](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md)
  as "recommendation only," even though later cross-cutting research
  cites DEC-018 as having decided them — this task's own final prompt
  must confirm the register's current state directly rather than rely on
  either snapshot.

## Inventory source-of-truth boundary

Ongoing, Odoo is the source of truth for Shopify inventory — Odoo→Shopify
write-back is the standing direction (Decision — DEC-010, Part C §A.3). A
controlled, reviewed, one-time import from Shopify may establish the
initial Odoo baseline where relevant; this is explicitly not a standing
bidirectional sync. No autonomous bidirectional conflict resolution
(RA-020, unweakened, rechecked and not revisited by DEC-015) — ambiguous
drift cases route to manual review.

## Location mapping dependency

`shopify_connector_inventory` owns an explicit, non-inferred
Odoo-location ↔ Shopify-Location mapping (sole owner) — each Odoo
location maps to exactly one Shopify Location; no name-based inference is
permitted (Decision — DEC-010, Part C §A.2). At least one mapped pair is
required before any write; the mapping mechanism must be structurally
multi-location-capable even for a single-location Phase 1 merchant.
Missing mapping triggers `inventory location missing`; ambiguous
multi-mapping candidates trigger `ambiguous match`. Fulfillment never
depends on this mapping table (a repeatedly emphasized boundary rule,
Part C §C.1).

## First-push safety

Fixed, unweakened guard (Decision — DEC-007 §4; DEC-010, Part C §A.5):
before the first Odoo→Shopify inventory write for a given store/binding,
requires **all** of: a mapped Shopify location; a preview of
SKU/variant/location quantities to be written; explicit operator
confirmation of that preview; a recorded source-of-truth decision; the
ability to skip or manual-match ambiguous items rather than force a
guess. **Granularity is not decided (MBQ-33 — still open)** — Part C
recommends firing per mapped Odoo-location ↔ Shopify-Location pair, but
this is a recommendation only; this task's own final §9 prompt must carry
ChatGPT's actual decision, not the recommendation, as settled.

## Manual vs scheduled sync

Layered, never webhook-only (Decision — DEC-005; DEC-010): manual sync is
explicit operator-triggered, enqueued, never inline (`job_source =
manual_sync`); scheduled sync/reconciliation cadence remains open
(MBQ-17, shared across every domain); an Odoo-side stock-change event
triggers a push job recorded as `job_source = odoo_event` with
`trigger_origin = 'inventory_stock_change'`
([DEC-019](../04-decisions/DEC-019-mbq-62-odoo-event-job-source.md) /
MBQ-62 — the accepted seventh job-source value, added specifically to
avoid the earlier Fable-corrected error of inventing a new job-source
value for event-driven enqueue). `INVENTORY_LEVELS_UPDATE` is a candidate
webhook trigger for detecting Shopify-side drift only, never the sole
mechanism.

## Stock quantity source open/accepted points

**Accepted:** Phase 1 default write target is Shopify `available`;
`committed` is never written under any circumstance (Decision — DEC-010;
RA-018). **Open (MBQ-32, partially resolved):** which Odoo source is
authoritative for the pushed quantity — `product.product.free_qty` and
`stock.quant.available_quantity` are verified as **not equivalent** (they
diverge whenever expired unreserved stock exists — Fable finding C1), and
the exact source-selection/aggregation mechanism, plus whether a
configurable Forecast/On-Hand/Free-to-Use default is offered, remain
unresolved. This task's own final §9 prompt must fix this before any
write code is authorized — it is a substantive, not cosmetic, choice.

## Duplicate prevention/idempotency

Per-location identity, never SKU-alone, keyed `(store, inventory_item_id,
location_id)` — prevents double-decrementing a multi-location SKU
(RA-019, unweakened). Compare-and-set (`inventorySetQuantities`) is the
preferred default mutation, reducing stale-read race risk. No flag
bypasses any of the above safety guards (Part A §I.5).

## Retry/error handling

Reconciliation is the mandatory correctness backstop — a scheduled pass
re-verifies previously-pushed quantity against Shopify's current state
and flags drift, reusing the same DEC-005 layered-sync pattern applied to
order totals. Concurrency/race conflicts (a compare-and-set mismatch)
auto-retry with backoff after a fresh read. `inventory location missing`,
`ambiguous match`, `destructive-write guard blocked` (an unconfirmed
first-push), and `binding conflict` (stale/recreated Shopify Location or
inventory-item ID) all route through the existing Part A error-class
registry — no domain-specific manual-review mechanism is invented.

## Tests required

First-push guard enforcement (no write without mapping, preview, and
confirmation); per-location identity correctness preventing
multi-location double-decrement; compare-and-set concurrency handling;
`committed`-never enforcement; location-mapping ambiguity/no-inference
enforcement; reconciliation drift detection. Exact fixtures for this
task's own final §9 prompt. If no Odoo runtime exists at coding time,
tests must still be written and syntax-validated per the Task 001A
precedent.

## Manual validation

On a live Odoo 19 + PostgreSQL instance once a runtime exists: confirm a
write is blocked without a mapped location; confirm the first-push
preview/confirmation flow fires before any write; confirm a second, later
write for the same mapped pair does not re-trigger first-push; confirm
`committed` is never referenced anywhere in write code; confirm
reconciliation flags an induced drift.

## Rollback

Single-PR revert; per the accepted dependency DAG, `fulfillment` never
depends on `inventory`, so a revert of this task does not affect Task
014. Reverting drops the inventory-level binding and location-mapping
model; live Shopify stock levels are unaffected by the revert itself (no
automatic corrective write is triggered).

## Acceptance criteria

- Only allowed files changed (per this task's own future final §9
  prompt).
- No write occurs without a mapped Shopify Location.
- First-push guard fires before the very first write per its decided
  granularity (MBQ-33 resolved in the final prompt, not merely
  recommended).
- `committed` never appears as a write target anywhere in the diff.
- No autonomous bidirectional conflict-resolution logic exists anywhere
  in the diff (RA-020 respected).
- Zero product/fulfillment logic in the diff.

## Explicit exclusions

- **No product import** (Task 010's scope).
- **No fulfillment** (Task 014's scope — inventory and fulfillment are
  independent siblings, neither gates the other, Part C §C item 4).
- **No inventory webhooks unless separately authorized** — MBQ-63:
  webhook-driven inventory import is decided by conservative exclusion,
  not implemented in Phase 1; this task does not revisit that.
- **No advanced warehouse complexity** (multi-location aggregation/
  warehouse-level rules beyond the accepted per-mapped-pair model are
  open-question territory, not this task's scope).
- **No Shopify Markets complexity.**
