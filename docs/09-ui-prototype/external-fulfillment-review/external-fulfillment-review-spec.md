# Screen spec — External fulfillment review center

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Prototype
> extension of the accepted U0 visual baseline; not yet control-room accepted.
> Design artifact only — implementation remains separately gated and this spec
> authorizes no code. Source: `external-fulfillment-review.html` (shared
> stylesheet `../assets/prototype.css`, zero JavaScript, no external assets).
> Content contracts: [`../../02-product/fulfillment-operating-modes.md`](../../02-product/fulfillment-operating-modes.md)
> (File A §2.2 Mode 1 review posture, §3 origin classification, §4 the
> 16-condition checklist + deterministic selection, §5 lot/serial rule) and
> [`../../02-product/shopify-fulfillment-status-model.md`](../../02-product/shopify-fulfillment-status-model.md)
> (File B badge vocabulary). Honors RA-022/RA-023 (never fulfill/reconcile by
> guess) and the fail-closed philosophy. All strings illustrative (MBQ-22).

## Purpose
Handle Shopify fulfillments the connector did not create. The screen renders
File A's central safety claim: **Mode 1 manual approval and Mode 2 automation
share one evaluation engine** — the proposal a Connector User confirms in
Mode 1 is exactly the output the 16-condition checklist would auto-apply in
Mode 2, and any single condition failure lands here as a named review reason
with **zero Odoo stock modification**.

## Primary role
**Connector User** — owns the queue and every case decision. The Connector
Administrator appears only indirectly (Mode 2 is an Administrator opt-in,
shown as context on the auto-reconciled case; condition 16). Review cases use
the accepted "waiting on a decision" presentation: danger family + hand icon
+ User owner chip — a decision, not a technical failure.

## Data shown
- **Queue:** case id, Shopify order, **origin chip** — *Shopify admin*
  (service handle `manual` + staff attribution), *3PL or other app* (service
  handle), *Unknown origin* (no evidence resolves — File A §3 rule: never
  assume connector-created) — items summary, observed age, case state.
  Footnote states the evidence-stacked classification order (own-GID ledger →
  service handle → event attribution).
- **Case detail:** Shopify **fulfillment identity** (Fulfillment GID, status
  badge "Shipped (confirmed)" = `SUCCESS`), **FulfillmentOrder identity**
  (FO GID + location), order/sale binding, recorded-by attribution, tracking,
  observed-at (webhook + live re-read); **lines & quantities comparison
  table** (Shopify fulfilled vs Odoo remaining, per-row Exact match /
  Mismatch verdicts); **location-mapping check** row; **proposed Odoo action
  panel** ("Validate picking WH/OUT/00042 for exactly these 3 lines", full
  demand → no backorder, tracking written).
- **Mode 2 variants:** the 16-condition checklist rendered per case — all-16
  green list (auto-applied), or stopped-at-first-failure with the failed
  condition expanded as a danger row + raw reason chip
  (`quantity_mismatch`, `lot_serial_ambiguous`) and later conditions marked
  "Not evaluated".

## States rendered
| State | Behavior |
| --- | --- |
| **Queue loaded** | Danger band with case count; 3 waiting cases spanning all three origin chips + 1 acknowledged case (neutral). |
| **Queue empty** | Calm empty state; explains what would appear. |
| **Case detail (Mode 1)** | Evidence left, proposal right. Primary action **Confirm — validate WH/OUT/00042** with an explicit disclaimer: the connector never validates stock on its own in Mode 1; confirming moves real inventory and is audit-recorded. Secondary: Import tracking only (non-stock write) · Acknowledge — handled outside Odoo · Leave for later. |
| **Mode 2 auto-reconciled** | Success band ("every exact condition passed"); "Applied automatically" + "Done by the connector" chips; the 16 conditions as an all-green two-column list; audit consequence; navigation-only actions. |
| **Mode 2 ambiguous** | Danger band; checklist passes 1–6, **condition 7 failed and highlighted** (quantity mismatch, no deterministic split — the connector never chooses an allocation), 8–16 not evaluated; the mismatching quantity row shown; User actions offered. |
| **Lot/serial ambiguity** | Danger band; reason `lot_serial_ambiguous`; evidence shows Shopify carries no serials while Odoo has 4 reserved for 2 shipped — **no proposal is offered in either mode**; the user resolves in Odoo then acknowledges. |

## Actions per role
| Action | Role | Effect |
| --- | --- | --- |
| Confirm proposed validation | User | The only path that moves Odoo stock in Mode 1; executes exactly the displayed proposal; audited. |
| Import tracking only | User | Writes `carrier_tracking_ref`/URL on the picking — never stock. |
| Acknowledge — handled outside Odoo | User | Closes the case with a reason; audited; no change. |
| Leave for later | User | No change; case stays in the queue. |
| Enable/disable Mode 2 | **Administrator** (not on this screen) | Context only — condition 16 and the mode chips reference it. |

Blocked by design: no auto-apply on any failed condition; no lot/serial
choice by the connector; unknown-origin fulfillments never treated as
connector-created; no stock reversal from here.

## Tokens
Standard `--sc-*` set only; no new CSS. Review cases = danger family + hand
icon + User owner (accepted U0 token map for `blocked_manual_review`);
auto-applied = success family + connector owner (mirrors the matching
center's automatic-outcome presentation); origin chips = info/neutral;
raw review reasons appear as neutral `sc-status` chips (`sc-mono`-adjacent
copy) so the raw token is visible but quiet; checklist verdicts reuse
`sc-match--yes/--no/--adv`; the failed condition reuses `.sc-ready--fail`.

## Accessibility
Comparison tables use real `<th>` headers and `data-label` attributes so the
shared ≤ 640px reflow renders labelled stacked cards; verdicts are words +
icons, never color alone; exactly one primary button per screen; the confirm
button names its exact effect ("Confirm — validate WH/OUT/00042"); RTL-safe
(logical properties only, inherited). Ordered checklist uses a real `<ol>` so
the 16 conditions are announced in order.

## Traceability
- Mode 1 review-only inbound posture + the three User actions: File A §2.2.
- Origin classification evidence order + unknown-origin rule: File A §3.
- 16 exact conditions, first-failure-stops, named reasons: File A §4 (table
  rows 1–16 verbatim, condensed labels).
- Deterministic picking selection / no allocation choice: File A §4.1.
- Lot/serial rule (connector never chooses a lot): File A §5.
- One-engine claim (Mode 1 proposal = Mode 2 evaluation output): File A §2.2.
- Badge vocabulary and severities: File B §4, §9.
- Rejected approaches honored: RA-022, RA-023 (`rejected-approaches-log.md`).
