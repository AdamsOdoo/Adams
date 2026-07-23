# Screen spec — Fulfillment workspace

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Prototype
> extension of the accepted U0 visual baseline; not yet control-room accepted.
> Design artifact only — implementation remains separately gated and this spec
> authorizes no code. Source: `fulfillment.html` (shared stylesheet
> `../assets/prototype.css`, zero JavaScript, no external assets).
> Content contracts: [`../../02-product/fulfillment-operating-modes.md`](../../02-product/fulfillment-operating-modes.md)
> (File A — Modes 1/2, origin classification, review posture) and
> [`../../02-product/shopify-fulfillment-status-model.md`](../../02-product/shopify-fulfillment-status-model.md)
> (File B — badge vocabulary, the four-layer fulfillment-state taxonomy, §8 Delivered-inconsistency
> rule). Both are `[Proposed]` documents; this screen renders them, it does not
> extend them. All on-screen strings are illustrative (MBQ-22).

> **⚠ U1 backing reconciliation (Wave 5 U1 Gate A status-layer reset, 2026-07-23 —
> control-room ruling `5058042330`; non-destructive — this prototype stays
> `Proposed`).** This screen renders the **full status-model taxonomy vision**; the
> **U1 implementation binds only to layers backed by the accepted Wave 4 code at
> `2d9cff0`**, per the canonical status-source & badge matrix in
> [`../../07-implementation-plan/wave-5-u1-gate-a/u1-backend-ui-contract-inventory.md`](../../07-implementation-plan/wave-5-u1-gate-a/u1-backend-ui-contract-inventory.md)
> §12. Two columns shown here are **not backed for U1** and are illustrative-only /
> deferred: the **"FulfillmentOrder work-state" (A2 `FulfillmentOrderStatus`)** column
> has **no backing field at `2d9cff0` → DEFERRED, no U1 badge**; the **"Carrier
> milestone" (A5)** column is **not** a normalized enum in code — U1 shows carrier
> evidence only from parsed `tracking_snapshot` + the `delivered_inconsistency` case,
> **never from the A7 `display_status_*` fields**. Backed for U1: Odoo picking state,
> A4 fulfillment result (`fulfillment_status_*`), A7 display status
> (`display_status_*`, display-only), and connector reconciliation state. Layer-C
> reconciliation vocabulary (e.g. "under review") follows **TD-003** (code value:
> `review`). Layers are never merged (§12 / status model §1).

## Purpose
Give the **Connector User** one honest working view of delivery/fulfillment
condition without opening Shopify: what must ship, what is moving, what
arrived, and what is waiting on a person. The screen's key design assertion is
File B §1's **four-layer fulfillment-state taxonomy**, rendered as **one badge
per concept, never merged** — the Odoo delivery state (`stock.picking.state`,
Odoo-side), the Shopify Layer-A enum families (order summary, FulfillmentOrder
work state, Fulfillment result, carrier milestone), and the connector
reconciliation state (connector-derived).

## Primary role
- **Connector User** — works the list, retries failed sends, opens review
  cases. All row actions are User actions.
- **Connector Administrator** — the only role that may use the mode chip's
  **Change** action (File A §1/§6: per-store mode selection is
  Administrator-only, audited). The chip itself is visible to both roles.

## Data shown (all from accepted/proposed contracts — nothing invented)
- **Stat chips:** to ship · in transit · delivered today · needs review
  (danger family) · holds (warning family). Quiet `sc-chip`s; loud only when
  non-zero danger/warning (U0 dashboard rule).
- **Mode chip:** current operating mode ("Mode 1 — Odoo-controlled", default —
  File A §1) + Administrator-only Change + "Administrator only" owner chip.
- **Table columns:** Odoo picking ref + state (`stock.picking.state`,
  concept 1) · Shopify order · FulfillmentOrder work-state badge (concept 3,
  File B §3.1 labels) · Fulfillment result badge (concept 4, File B §4) ·
  tracking (carrier + number, `trackingInfo`) · latest carrier milestone badge
  (concept 5, File B §5) · connector reconciliation state (concept 6, File A
  §5: observed / under review / applied …).
- **ON_HOLD row:** the Held badge carries a companion **hold-reason chip**
  ("Awaiting payment" ← raw `AWAITING_PAYMENT`, File B §3.3); copy notes sends
  are blocked while held (D-014-5 read-only-toward-holds posture).

## States rendered
| State | Behavior |
| --- | --- |
| **Loaded** | Chips + mode chip + 6 rows spanning the badge families: Delivered/Applied; In transit/Applied; Ready (nothing sent); **ON_HOLD + hold-reason chip**; **DELAYED** milestone; external 3PL fulfillment **Under review** (danger row). Footnote restates one-badge-per-concept and that a milestone never changes Odoo stock. |
| **Critical banner** | File B §8 case: danger band "**Carrier reports Delivered — Odoo delivery not validated**" naming order, fulfillment GID, tracking, milestone timestamp, and the open picking, with a **Review this case** CTA. Copy states nothing was changed and the case never auto-resolves by stock mutation. The attention table beneath shows the inconsistent row plus: **outbound-failure row** (`fulfillmentCreate` failed — semantic error, **Retry send** secondary button, no fulfillment exists remotely) and **uncertain-outcome row** ("Verifying remote result…", neutral — the D-014-7/DEC-031 verification-read-before-any-retry posture, never a blind resend). |
| **Loading** | Skeleton chips + skeleton table + "Loading deliveries…" line; never a blank region. |
| **Empty** | Calm empty state; explains Mode 1 in one sentence; navigation to Sync Center. |

## Actions per role
| Action | Role | Notes |
| --- | --- | --- |
| Retry failed outbound send | User | Only on a confirmed semantic/transport failure; uncertain outcomes show verification, not a retry button. |
| Review this case (critical banner / under-review rows) | User | Routes to the External fulfillment review center. |
| Change operating mode | **Administrator only** | Opens the audited mode-switch confirmation (File A §6) — not rendered here; the chip asserts visibility + gating only. |
| Open Sync Center (empty state) | User | Navigation only. |

Blocked by design: no action ever validates Odoo stock from this list; holds
are read-only; the connector never cancels fulfillments (File A).

## Tokens
Standard `--sc-*` set only. Severity mapping per File B §9: calm →
neutral/success chips; info → `--sc-info`; warning (holds, DELAYED) →
`--sc-warning`; critical (send failed, Delivered-inconsistency, under review)
→ `--sc-danger`. Manual-review/waiting-on-a-decision uses the **danger family
+ hand icon + owner chip** (accepted U0 token map), distinguished from
technical failure by icon/owner/copy, not color. Exception rows use the
existing `.sc-list tr.has-exception` danger tint. No new CSS was added.

## Accessibility
Real `<th scope="col">` headers; every state is a word + icon, never color
alone; the raw hold enum is exposed via `title` while the label stays
human-readable; buttons meet the 36px min height; the banner CTA is a real
`<button>`; RTL-safe (logical properties inherited from the shared
stylesheet; no left/right styles introduced). At ≤ 640px the shared sheet
hides the optional tracking column (`col-ref`) and keeps the compact shell.

## Traceability
- Four-layer fulfillment-state taxonomy (one badge per concept), badge labels, severities: File B §1–§5, §9.
- Hold vocabulary + read-only posture: File B §3.3; File A §5 edge table.
- Critical Delivered-inconsistency case (copy, severity, pinning, resolution
  paths): File B §8.
- Outbound failure vs uncertain outcome (verification read before retry):
  File A §2.1, D-014-7, DEC-031 Layer 2, DEC-009 taxonomy.
- Mode chip + Administrator-only switching: File A §1, §6, §8.
- Two-role terminology (Connector User / Connector Administrator): File A §1
  and `wave-0-roles-permissions-and-fulfillment-scope-refresh.md`.
- Unknown future enum values are handled on the tracking-timeline surface
  (File B §7); this list would show the same `badge-unknown` treatment.
