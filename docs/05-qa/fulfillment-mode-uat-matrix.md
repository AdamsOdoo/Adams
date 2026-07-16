# Fulfillment Operating-Mode UAT Matrix

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. Planning only;
> no test executed; no gate opened.** Companion QA deliverable of
> [`../02-product/fulfillment-operating-modes.md`](../02-product/fulfillment-operating-modes.md)
> (File A) and
> [`../02-product/shopify-fulfillment-status-model.md`](../02-product/shopify-fulfillment-status-model.md)
> (File B). **[Product-direction update — 2026-07-16] Both Mode 1 and Mode 2
> are required MVP Wave 4 backend scope** (File A §10/§11). Mode 1, Mode 2, and
> mode-switch backend cases all execute with **Wave 4** — Wave 4 may internally
> sequence Mode 1 before Mode 2 but cannot close until both are implemented,
> tested, and runtime-proven; the Administrator mode-selection UI is Wave 5, and
> Wave 5 does **not** own the Mode 2 backend. All live runs are Wave 6 dev-store
> UAT. Fixture names reference File B §10 where a
> fixture exists; live UAT cases create the equivalent condition on the dev
> store.

## Shared conventions

- **Environment:** Odoo.sh build + dev store with merchant-managed
  fulfillment (`read/write_merchant_managed_fulfillment_orders` scopes —
  D-014-2), a mapped location (for Mode 2 condition 8), bound orders with
  open pickings, and a lot-tracked product for the lot/serial cases.
- **Roles:** Administrator selects/switches modes; User works review cases,
  imports tracking, and explicitly validates proposals.
- **Universal pass criteria (every case):** no Odoo stock change occurs
  except via a validated picking (connector-proposed validations require
  explicit User confirmation in Mode 1, or a full 16/16 checklist pass in
  Mode 2); every automated decision leaves audit evidence; notification
  default stays off (RA-009); no new error class or manual-review sub-reason
  appears.

---

## 1. Mode 1 UAT (Odoo-controlled)

| ID | Case | Steps | Pass criteria |
| --- | --- | --- | --- |
| UAT-FM-1.1 | Outbound full fulfillment | Validate an eligible delivery picking (D-014-3) with carrier + tracking set | Exactly one Shopify fulfillment created via explicit `lineItemsByFulfillmentOrder`; tracking company/number/url present; `notifyCustomer=false` (default); binding + own-GID ledger entry recorded |
| UAT-FM-1.2 | Outbound partial fulfillment | Validate a picking for part of the demand, create backorder; later validate the backorder | Two distinct fulfillments matching the two pickings; each maps only its own quantities; FO `remainingQuantity` consistent after each; backorder split is its own event |
| UAT-FM-1.3 | Multi-package / multi-tracking | Validate with multiple tracking references | All tracking numbers captured on the fulfillment (`numbers[]`); packages remain display/evidence only — no Odoo package auto-creation |
| UAT-FM-1.4 | Tracking-only update | After UAT-FM-1.1, change `carrier_tracking_ref` on the picking | `fulfillmentTrackingInfoUpdate` runs in place; **no second fulfillment is ever created**; visibly distinct event in the log |
| UAT-FM-1.5 | Notify-off proof | Run UAT-FM-1.1 against an order with a real (test) customer email | No Shopify customer notification is sent; the persisted-at-enqueue notification decision is visible on the job; recipient names never logged |
| UAT-FM-1.6 | External fulfillment detection → review | Manually fulfill an order in Shopify admin (external origin) | Inbound record created; origin classified `external_merchant` via the §3 evidence stack (own-GID ledger miss + `service.handle`/event attribution); a User review case opens stating order, items/quantities, location, actor, tracking, and the exact proposed Odoo action; **zero stock change** |
| UAT-FM-1.7 | Mode 1 User actions on the review case | From UAT-FM-1.6: (a) import tracking; (b) acknowledge; (c) explicitly validate the exact proposal | (a) writes only `carrier_tracking_ref`/URL (non-stock); (b) closes the case "handled outside Odoo", audited; (c) shows precise picking/lines/quantities/lots/locations and validates only on deliberate confirmation — the proposal equals the §4 evaluation output |
| UAT-FM-1.8 | Connector-created fulfillment observed inbound | Let the webhook/scan re-observe the UAT-FM-1.1 fulfillment | Classified `connector` via own-GID ledger; snapshots refreshed; **never validates Odoo again**; no review case |
| UAT-FM-1.9 | Uncertain outbound outcome | Simulate timeout on `fulfillmentCreate` (network fault injection) | Verification read (FO remaining quantities + own-GID ledger) precedes any retry; applied → adopt; not-applied → retry; inconclusive → `blocked_manual_review`; never a blind retry ([Fact] no idempotency key — capture §6.5) |
| UAT-FM-1.10 | Held / scheduled / declined FO states | Create `ON_HOLD` (each hold reason where reproducible), `SCHEDULED`, `REQUEST_DECLINED` conditions | Connector sends blocked per File B §2–3 rows; picking validation attempts route to review with the hold `displayReason` surfaced; connector never places/releases holds (D-014-5) |
| UAT-FM-1.11 | Cancelled/failed inbound fulfillment | Cancel a connector-created fulfillment in Shopify (`ful_cancelled`); produce an `ERROR`/`FAILURE` result (`ful_error`/`ful_failure`) | Cancellation never auto-reverses Odoo stock; Odoo-already-validated → high-visibility review case; `ERROR`/`FAILURE` never reconciled as shipped |
| UAT-FM-1.12 | Unknown status value (each Layer-A enum family) | Fixture-level (`unknown_ful_status` etc.) or replayed synthetic payload, one per Layer-A enum family (all seven, incl. `FulfillmentDisplayStatus`) | All five File B §7 unknown-value contract points hold for every Layer-A family: raw preserved, unknown badge, never success, unsafe automation stopped, schema warning raised |

## 2. Mode 2 UAT (bidirectional exact reconciliation)

### 2.1 Pass case

| ID | Case | Steps | Pass criteria |
| --- | --- | --- | --- |
| UAT-FM-2.0 | Full-checklist auto-reconcile | Mode 2 enabled; externally fulfill (Shopify admin) an order whose single open Odoo picking exactly matches lines/quantities/location, all bindings intact, untracked product | All 16 File A §4 conditions evaluated and pass; the deterministic picking is validated automatically with exact quantities; full checklist evidence snapshot audited; per-line reconciled quantities recorded; re-observing the same Fulfillment GID does nothing (condition 12) |

### 2.2 The 16 negative cases — each condition individually violated

Method: construct the UAT-FM-2.0 setup, then break exactly **one** condition
per case. Universal pass criteria for every row: evaluation stops at the
first failing condition; a User review case opens carrying the **named
reason** below; **zero Odoo stock change**; the case is workable via the
Mode 1 actions (UAT-FM-1.7).

| ID | Condition violated (File A §4 #) | How to violate | Expected review reason |
| --- | --- | --- | --- |
| UAT-FM-2.1 | 1 — exact order binding | External fulfillment on an order never imported/bound | `order_binding_missing` |
| UAT-FM-2.2 | 2 — fulfillment `SUCCESS` | Inbound fulfillment with status `ERROR`/`FAILURE`/`CANCELLED` | `fulfillment_state_not_success` |
| UAT-FM-2.3 | 3 — FO identity | Fulfillment line whose FO/FO-line GID cannot be resolved | `fulfillment_order_unresolved` |
| UAT-FM-2.4 | 4 — product/variant binding | Unbind (or archive the binding of) one line's variant | `product_binding_missing` |
| UAT-FM-2.5 | 5 — line/quantity mapping | Sale line missing `shopify_line_item_gid` / UoM mismatch | `line_mapping_ambiguous` |
| UAT-FM-2.6 | 6 — no over-fulfillment | External fulfillment quantity exceeds ordered−already-fulfilled | `over_fulfillment` |
| UAT-FM-2.7 | 7 — exact remaining Odoo quantity | Picking pending demand differs and does not deterministically split | `quantity_mismatch` |
| UAT-FM-2.8 | 8 — location mapping | Fulfill from a Shopify location with no Odoo mapping | `location_unmapped` |
| UAT-FM-2.9 | 9 — deterministic picking | Two candidate open pickings both covering the lines | `picking_ambiguous` |
| UAT-FM-2.10 | 10 — valid reservations | Candidate picking not `assigned` and not reservable (stock consumed elsewhere) | `reservation_invalid` |
| UAT-FM-2.11 | 11 — lot/serial | Lot-tracked product whose reserved move lines do not uniquely cover quantities (two candidate lots) | `lot_serial_ambiguous` |
| UAT-FM-2.12 | 12 — no duplicate application | Re-deliver the same Fulfillment GID after it was applied (replayed webhook/scan) | `already_reconciled` (or silent no-op with audit — must never apply twice) |
| UAT-FM-2.13 | 13 — no conflicting binding | Candidate picking already bound to a different Fulfillment GID | `binding_conflict` |
| UAT-FM-2.14 | 14 — live re-check | Cancel the fulfillment in Shopify between observation and application (stale webhook) | `remote_state_changed` |
| UAT-FM-2.15 | 15 — confirmed external | Origin classification unresolved/pending (own-GID ledger unavailable in fixture, no service handle, no attribution) | `origin_unconfirmed` |
| UAT-FM-2.16 | 16 — Mode 2 enabled | Deliver the external fulfillment while the store is in Mode 1 / mid-switch / scan-suspended | `mode_not_enabled` (Mode 1 review path) |

### 2.3 Split/decomposition cases

| ID | Case | Pass criteria |
| --- | --- | --- |
| UAT-FM-2.17 | Deterministic split | External partial fulfillment covered-with-surplus by one picking: only the fulfilled quantities validate; a native backorder carries the remainder (`create_backorder` forced explicitly, never the `ask` wizard); the next external fulfillment re-runs the full checklist against the backorder chain |
| UAT-FM-2.18 | Multi-location decomposition | A fulfillment spanning FOs at two mapped locations decomposes into per-picking applications each passing the checklist independently — or fails whole as `picking_ambiguous`; never a partial application of an ambiguous decomposition |

## 3. Mode-switch UAT

| ID | Case | Steps | Pass criteria |
| --- | --- | --- | --- |
| UAT-FM-3.1 | Switch with unresolved externals | With ≥2 open external-fulfillment review cases, Administrator switches Mode 1→2 | Confirmation step lists the unresolved cases in plain language; after the switch they **remain review cases** — never auto-applied (no history replay); switch audited (who/when/from→to/confirmation text version) |
| UAT-FM-3.2 | Safe reconciliation scan gating | Observe the switch-in-progress state | Scan re-reads FOs/fulfillments since the watermark **read-only** (zero stock writes during the scan); Mode 2 evaluation starts only after the scan completes clean; scan blockers abort back to Mode 1 |
| UAT-FM-3.3 | Rollback | Switch Mode 2→1 while a Mode 2 evaluation is in flight | Always allowed; future auto-application stops; evidence records, applied reconciliations, bindings, audit untouched; in-flight evaluations cancelled back to `under_review` — no state corruption |
| UAT-FM-3.4 | Idempotent re-scan / re-confirm | Re-confirm the current mode; retry a switch job (simulated duplicate) | No-op: no duplicate scan effects, no duplicate audit generation (per-run nonce per D-014-8); User attempting a mode change is refused server-side (Administrator-only) |
| UAT-FM-3.5 | Disconnected-period externals (both modes) | Disconnect; externally fulfill an order; reconnect in Mode 2 | The gap-period external fulfillment lands as a **review case even in Mode 2** (File A §7); reconnect banner counts it; condition-14 recheck never retroactively authorizes gap-period interleavings |

## 4. Carrier-Delivered inconsistency case

| ID | Case | Steps | Pass criteria |
| --- | --- | --- | --- |
| UAT-FM-4.1 | Delivered per carrier, Odoo not validated | Produce a `DELIVERED` fulfillment event (or `deliveredAt`) for an order whose Odoo picking is not `done` (`evt_delivered` fixture condition, live where the dev store permits) | **The milestone never validates stock** (File B §8); a critical, pinned "Delivered per carrier — Odoo delivery not validated" review case opens listing fulfillment, tracking, milestone timestamp, and the exact open picking(s); resolution only via User explicit validation, linkage correction, or reasoned acknowledgement; in Mode 2 it may auto-resolve only if the underlying fulfillment independently passes the full 16-condition checklist — the milestone contributes nothing |

## Evidence to capture (all sections)

Per case: the review case screenshot with its named reason; the inbound
evidence record (origin class + evidence used); Odoo picking states
before/after (proving zero change for negative cases); the audit entries;
for Mode 2 applications, the persisted checklist evidence snapshot; for
switches, the confirmation dialog and audit record.

## Open items

- [Open question] Cases UAT-FM-2.15 and the origin-classification fixtures
  depend on whether fulfillment webhooks expose the originating API client
  (File A §12.1) — until verified, classification tests must not rely on it.
- [Open question] Some FO states (`INCOMPLETE`, `REQUEST_DECLINED`, several
  hold reasons) may not be reproducible on a dev store without a fulfillment
  service; those rows fall back to fixture-level tests (File B §10 fixtures)
  with the live case recorded as not-reproducible in the UAT evidence.
