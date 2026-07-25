# Screen spec — Tracking timeline

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Prototype
> extension of the accepted U0 visual baseline; not yet control-room accepted.
> Design artifact only — implementation remains separately gated and this spec
> authorizes no code. Source: `tracking-timeline.html` (shared stylesheet
> `../assets/prototype.css`, zero JavaScript, no external assets).
> Content contract: [`../../02-product/shopify-fulfillment-status-model.md`](../../02-product/shopify-fulfillment-status-model.md)
> (File B §1 four-layer fulfillment-state taxonomy, §5 the 11 `FulfillmentEventStatus`
> milestones + `trackingInfo`, §7 unknown-future-value contract, §8
> Delivered-inconsistency direction) and
> [`../../02-product/fulfillment-operating-modes.md`](../../02-product/fulfillment-operating-modes.md)
> (File A §3 class 4 `carrier_event_only`, §5 multi-package edge row).
> All strings illustrative (MBQ-22).

> **⚠ U1 backing reconciliation (Wave 5 U1 Gate A status-layer reset, 2026-07-23 —
> control-room ruling `5058042330`; non-destructive — this prototype stays
> `Proposed`).** This screen renders the **full status-model carrier-milestone (A5)
> vision**; the **U1 implementation binds only to what the accepted Wave 4 code backs
> at `2583081f`**, per the canonical status-source & badge matrix in
> [`../../07-implementation-plan/wave-5-u1-gate-a/u1-backend-ui-contract-inventory.md`](../../07-implementation-plan/wave-5-u1-gate-a/u1-backend-ui-contract-inventory.md)
> §12. At `2583081f` **A5 `FulfillmentEventStatus` is NOT stored as a normalized enum**,
> so a **full A5 milestone-enum timeline is deferred**; U1's tracking surface renders
> parsed `tracking_snapshot` (carrier/number/url) chips + the `delivered_inconsistency`
> case (the delivered-inconsistency case itself lives on the fulfillment workspace /
> review center — §8) and **never** derives A5 from the A7 `display_status_*` fields.
> The taxonomy strip's **"FulfillmentOrder state" (A2)** chip has **no U1 backing field
> → DEFERRED, no badge**. `carrier_event_only` is superseded origin vocabulary (no such
> code origin class; see the status-model annotation / TD-003). Layers are never
> merged (§12 / status model §1).
>
> **Unsupported "Delivered" is SUPPRESSED for U1 (binding).** Every "Delivered"
> milestone rendered on this prototype is **illustrative content only**. U1 must
> **not claim, display or offer** a "Delivered" outcome: no A5 `DELIVERED` milestone
> is backed by a stored enum, and `delivered_inconsistency` /
> `review_reason='delivered_not_validated'` are declared but **never written** at
> `2583081f`. The only permitted delivered-adjacent surface is the
> **delivered-inconsistency case when the backend actually sets the flag**, rendered
> as a warning, never as a delivery confirmation. This suppression stands until a
> real backend seam is separately authorized, implemented and independently proven.

> **Re-verified 2026-07-25** against the current integrated backend `2583081f`: the
> A5/A7/A2 dispositions above are unchanged (contract §0.1 Δ7).

## Purpose
Answer one question — *where is the parcel physically?* — as a vertical
carrier-milestone timeline for a single fulfillment, while making the
informational nature of concept 5 unmistakable: **a carrier milestone never
validates Odoo stock and never changes the connector reconciliation state**.
Every milestone shows a human label *and* the raw Shopify value it came from.

## Primary role
**Connector User** (read-only surface). The only action offered anywhere is
opening a review case on a critical carrier outcome; no Administrator-only
control exists on this screen.

## Data shown
- **Lead band** — the latest milestone as the single dominant answer
  (Delivered / In transit / Delayed / Failed / Unknown).
- **Taxonomy strip** (complete state) — one labeled chip per concept under the
  four-layer fulfillment-state taxonomy, side by side: Odoo delivery state
  (`Done`, Odoo-side) · Shopify order summary (`Fully shipped`) ·
  FulfillmentOrder state (`Completed`) · Fulfillment result
  (`Shipped (confirmed)`) · carrier milestone (`Delivered`) — the Shopify
  Layer-A enum families — · connector reconciliation state (`Applied`,
  connector-derived). File B §1: one badge each, never merged.
- **Carrier chip** — carrier name + tracking number (`trackingInfo`
  company/number).
- **Two-package tabs mock** — static `role="tablist"` showing Package 1 of 2
  (active) / Package 2 of 2 with distinct tracking numbers; File A §5:
  multi-package tracking is display/evidence only in MVP.
- **Timeline** — ordered list (`.sc-activity`), oldest → newest; each entry:
  milestone badge (File B §5 label + severity), the raw enum
  ("raw: IN_TRANSIT"), timestamp, and optional carrier note. Unreported
  future steps render as muted placeholders, never as promises.
- **Cadence line** — restates the display-only rule under every timeline.

## States rendered
| State | Behavior |
| --- | --- |
| **Complete** | LABEL_PURCHASED → CONFIRMED → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED with timestamps; success band notes the Odoo delivery was validated *separately*; taxonomy strip + two-package tabs shown. |
| **In progress** | Milestones through IN_TRANSIT; "Out for delivery / Delivered — not yet reported" as muted placeholders; info band with estimated delivery. |
| **Delayed** | Warning band; DELAYED ("carrier: weather hold") and ATTEMPTED_DELIVERY ("recipient absent, carrier will retry") as warning milestones; copy: awareness only, optional attention flag, no stock action. |
| **Failed** | Danger band "Delivery failed — a person must decide" with **Open review case** CTA + waiting-on-a-decision chips; FAILURE milestone; cadence notes re-ship/return is Odoo's manual return flow. |
| **Unknown schema** | File B §7 contract rendered: neutral chip "**Unknown status (raw: SOME_NEW_VALUE)**" with help icon; warning band = the schema warning naming family, raw value, store, API version, affected records; degraded health chip; copy asserts never-silently-success and paused dependent automation. |

## Actions per role
| Action | Role | Notes |
| --- | --- | --- |
| Open review case (failed state only) | Connector User | Routes to the External fulfillment review center; the decision (re-ship / return) is made there and in Odoo. |
| Switch package tab | Connector User | Presentation only in the prototype (static mock, no JS). |

Blocked by design: no milestone-driven stock validation (File B §8 — the
Delivered-but-Odoo-open critical case lives on the Fulfillment workspace and
review center, not here); no retry — milestones have no retry semantics.

## Tokens
Standard `--sc-*` set only; no new CSS and no new components — the timeline
reuses `.sc-activity`, badges reuse `.sc-status`, tabs reuse `.sc-tabs`.
Severity per File B §5/§9: calm milestones → neutral/success chips; info →
`--sc-info`; DELAYED / ATTEMPTED_DELIVERY → `--sc-warning`; FAILURE →
`--sc-danger`; unknown → neutral chip + help icon (the proposed
`badge-unknown` maps to the neutral family pending a design-system token —
flagged, not invented). Timeline markers inherit the same family colors.

## Accessibility
The timeline is a real `<ol>` (chronological order announced); every
milestone is label + raw value + timestamp in text — color never carries
meaning alone; the unknown value keeps its raw string visible on screen (not
tooltip-only); tabs carry `role="tablist"/"tab"` and `aria-selected`; the
review CTA is a real `<button>`; RTL-safe (logical properties inherited; no
directional styles introduced). Muted future steps are real list items, so
screen readers hear that later milestones are not yet reported.

## Traceability
- Milestone vocabulary, labels, severities (11 values): File B §5.
- Four-layer taxonomy strip: File B §1 (+§9 one-badge rule).
- Display-only rule / never validates stock: File B §5, §8; File A §3
  class 4 (`carrier_event_only`).
- Unknown-future-value contract (all five points rendered): File B §7.
- FAILURE → review case, manual return flow: File B §5 row `FAILURE`;
  File A §5 edge table.
- Multi-package tracking as display/evidence only: File A §5 edge table
  (deferred package auto-creation — C-FUL-02 posture).
- Two-role terminology: File A §1 (Connector User / Connector Administrator).
