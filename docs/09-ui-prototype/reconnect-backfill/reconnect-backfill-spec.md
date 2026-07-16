# Reconnect, catch-up & backfill — screen spec

> Prototype extension (Fable gap-closure mission, 2026-07-16), built on the
> accepted U0 visual baseline. Design artifact only — no implementation is
> authorized by this file. Source of truth for behavior:
> [`../../02-product/reconnect-catchup-backfill-policy.md`](../../02-product/reconnect-catchup-backfill-policy.md).

## 1. Purpose

Show controlled re-entry after disconnection as the policy defines it:
reconnect is verify → new connection generation → historic work preserved
but never executed → **fresh domain scans** (the only source of
post-reconnect work); catch-up is per-domain, watermark-driven, with an
overlap window whose re-reads dedup absorbs; historic order import beyond
the automatic window is exclusively an **Administrator-controlled backfill
with a mandatory read-only preview** and honest 60-day / `read_all_orders`
messaging.

## 2. Primary role

- **Connector User** — may watch reconnect/catch-up progress and open the
  review queue.
- **Connector Administrator** — triggers reconnect and is the **only** role
  that sees/uses the backfill wizard (PD-RB-8). The wizard card carries an
  explicit "Connector Administrator only" owner chip.

## 3. Data shown

- **Reconnect checklist (8 steps)** — credentials verified; scopes verified
  per enabled domain; pinned API version 2026-07 confirmed; readiness re-run;
  new connection generation **#7** recognized; historic jobs preserved as
  evidence ("never an execution queue"); stale-generation jobs fenced at
  admission; fresh domain scans starting (in-progress spinner).
- **Per-domain catch-up table** — products / customers / orders / inventory /
  fulfillment with watermark timestamps (inventory and fulfillment show a
  freshness marker, not a filter — the policy's §4.4/§4.5 distinction),
  scan window (watermark − 30 min overlap; inventory = full read of mapped
  pairs), and counts found / enqueued / skipped / needs-review.
- **Backfill wizard** — created-date range, eligibility filters, the honesty
  banner ("Orders older than 60 days require Shopify read_all_orders
  approval — status: not granted") with the exact reachable sub-range and the
  approval path; **five preview counts**: new / changed / duplicate /
  skipped / needs review; sample records; consequence note (batch id,
  generation tag, lower priority, no policy bypass).
- **Scope-missing state** — disconnection longer than 60 days without
  `read_all_orders`: the unreachable order window is named and the catch-up
  is *not* reported complete.

## 4. Actions per role

| Action | User | Administrator |
| --- | --- | --- |
| View reconnect progress / catch-up counts | Yes | Yes |
| Open review queue from needs-review counts | Yes | Yes |
| Run backfill preview (read-only scan) | No | Yes |
| Confirm backfill enqueue | No | Yes |
| Cancel preview (nothing written) | — | Yes |
| Request read_all_orders (guidance link) | Yes | Yes |

The "Backfill missing window" button in the scope-missing state is rendered
`aria-disabled` until approval exists — the unavailable path is shown, not
hidden.

## 5. States in the gallery

1. **Reconnecting** — info band; steps 1–7 pass rows, step 8 spinner;
   reassurance-first copy (settings/mappings/history preserved).
2. **Catch-up complete** — success band; per-domain table; "what was not
   done" consequence note (no replay, no lifetime import, no push before the
   inventory reconciliation read).
3. **Backfill preview loaded** — info band ("read-only scan — no job and no
   record was created"); five counts; explicit confirm vs cancel.
4. **Backfill preview loading** — skeleton band + skeleton count chips +
   spinner line restating the no-write guarantee; never blank.
5. **Scope-missing warning** — warning band + degraded health chip
   ("limited history"); exact unreachable window; approval guidance.

## 6. Tokens

Only `--sc-*` tokens. Reconnect checklist reuses the readiness-row component
(`sc-ready`, pass = success family); in-progress uses the standard spinner.
Counts use `sc-chip` (needs-review chip = danger family, reviewer-decision
semantics). Honesty banners use the warning family; the consequence note uses
the info family. Timestamps/counts use `sc-mono`. No new token introduced.

## 7. Accessibility

- Every step outcome is a word + icon, never color alone; spinners carry
  `role="img"` with an "In progress" label.
- Skeleton regions use `aria-busy="true"` and keep a visible text line.
- The catch-up table is a real `<table>` with `data-label` cells for the
  ≤640px stacked reflow.
- One primary action per screen (Enqueue backfill); cancel is secondary and
  explicitly states "nothing was written".
- Disabled action uses `aria-disabled="true"` with an inline reason.

## 8. Traceability

| Element | Source |
| --- | --- |
| No blind replay; fresh scans as sole post-reconnect work | reconnect-catchup-backfill-policy.md §1–§2 (PD-RB-1/2) |
| 8-step sequence incl. generation, historic sink, stale fencing | §2 table |
| Per-store × domain timestamp watermarks; cursors never persisted | §3.1 (PD-RB-4) |
| 30-minute overlap window default | §3.2 |
| Skip logic → found/enqueued/skipped/needs-review counts | §3.4 (PD-RB-6) |
| Inventory = reconciliation read before any push; freshness marker | §4.4 |
| Fulfillment scan scoped to open bound orders | §4.5 |
| Administrator-only backfill; mandatory read-only preview; five counts | §5 (PD-RB-8) |
| 60-day / read_all_orders honesty, reachable sub-range, approval path | §4.3, §5.2 |
| Resumable batches; generation-fenced; same confirmation/COD policy | §5.6–5.7 |
| >60-day disconnect warning state | §4.3, §8 |
| Two-role terminology | ../../02-product/connector-roles-and-permissions.md |
