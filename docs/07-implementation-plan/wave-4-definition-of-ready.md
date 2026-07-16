# Wave 4 — Definition of Ready (Fulfillment & Tracking)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. NOT accepted.**
> Acceptance authority: product owner + Claude control room (per
> [`mvp-completion-program.md`](mvp-completion-program.md) §4 Wave 4 and the
> DEC-032 operating model). This checklist gates the *opening* of Wave 4; it
> authorizes no implementation by itself. Structure follows
> [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)
> (acceptance preconditions → allowed/forbidden → acceptance criteria → tests →
> rollback → definition of done), adapted to the macro-wave model.

## 1. Wave objective (one scoped outcome)

Implement the fulfillment/tracking domain as the new
`shopify_connector_fulfillment` module:

- **Task 014 outbound flow** (picking-validation → `fulfillmentCreate` with
  explicit FulfillmentOrder line lists → `fulfillmentTrackingInfoUpdate`),
  exactly per
  [`task-014-fulfillment-tracking-implementation-packet.md`](task-014-fulfillment-tracking-implementation-packet.md)
  D-014-1..8 **as amended by that packet's 2026-07-16 gap-closure addendum**.
- **Inbound reconciliation, Mode 1 in full**: observation of every Shopify
  fulfillment, origin classification, inbound evidence records, review cases,
  tracking import, and explicit User validation of exact proposals — per
  [`../02-product/fulfillment-operating-modes.md`](../02-product/fulfillment-operating-modes.md)
  §2–§3, §5–§7.
- The `fulfillment_operating_mode` setting fixed at **Mode 1**.
  **Mode 2 auto-application is NOT Wave 4 scope** — it is Wave 5 (optional,
  or a Wave 4 stretch only under the fulfillment-modes doc §10 conditions:
  Wave 4 lands early *and* the location-resolution prerequisite is proven).

## 2. Gates — every box must be checked before the wave opens

- [ ] **G4-1 — Layer 2 accepted, implemented, and proven (from Wave 3).**
      [`../03-architecture/dec-031-layer-2-mutation-safety-design.md`](../03-architecture/dec-031-layer-2-mutation-safety-design.md)
      is accepted (its §14 decision list), implemented in Wave 3, and has
      genuine (not simulated) runtime/concurrency proof recorded in the Wave 3
      wave review. `fulfillmentCreate` is not `@idempotent` (Task 014 packet
      D-014-7), so no fulfillment mutation may ship without Layer 2 durable
      attempt identity + reconciliation-before-retry (program hard-stop 4).
- [ ] **G4-2 — Fulfillment operating-modes PDs accepted.** The seven proposed
      decisions in `fulfillment-operating-modes.md` §11 (Mode 1 default,
      review-only inbound, 16-condition Mode 2 checklist, lot/serial rule,
      mode-switch state machine, disconnected-period rule, Mode 2 wave
      allocation) are accepted or explicitly amended by the control room.
- [ ] **G4-3 — Fulfillment state-model PDs accepted.** The six proposed
      decisions in
      [`../02-product/shopify-fulfillment-status-model.md`](../02-product/shopify-fulfillment-status-model.md)
      §11 (six-concept separation, per-value mapping tables, deprecated-value
      handling, unknown-future-value contract, Delivered-inconsistency rule,
      badge/severity vocabulary) are accepted, and its Open question 1
      (`FulfillmentDisplayStatus` values) is verified or explicitly deferred
      before the Wave 4 freeze.
- [ ] **G4-4 — Scope correction confirmed in the wave's contract.** The core
      readiness scope swap `read_fulfillments` →
      `read_merchant_managed_fulfillment_orders`, with
      `write_merchant_managed_fulfillment_orders` required conditionally
      (D-014-2 / TD-002), is carried into the wave prompt verbatim. Basis:
      the Wave 0 official-source refresh
      [`../01-research/wave-0-roles-permissions-and-fulfillment-scope-refresh.md`](../01-research/wave-0-roles-permissions-and-fulfillment-scope-refresh.md)
      (confirms `read_fulfillments` governs FulfillmentService apps, not this
      connector) and `mvp-completion-program.md` §3 item 12 / §4 Wave 4.
- [ ] **G4-5 — Task 014 re-acceptance with its addendum.** The Task 014
      packet plus its dated 2026-07-16 addendum ("[Proposed] Fable
      gap-closure requirements") is re-reviewed and re-accepted as one unit;
      the original D-014-1..8 closures stay intact, the addendum's inbound/
      mode/state-model/COD additions become binding, and the §8 locked prompt
      is re-issued against the amended packet. Acceptance of the packet
      *without* the addendum does not open this wave.
- [ ] **G4-6 — Wave 2 and Wave 3 merged runtime-green.** Order bindings +
      line GIDs (Task 012, D-014-4's matching chain input) and the inventory
      wave (Layer 2 host) are merged into `mvp/program-integration` with
      accepted wave reviews.
- [ ] **G4-7 — COD interplay scope confirmed.** The COD ↔ fulfillment
      interplay (scenarios 2–13 mechanics: partial validation, backorder
      semantics, return-picking linkage, fulfillment-dimension derivation) is
      confirmed as Wave 4 scope per
      [`../02-product/cod-lifecycle-and-reconciliation.md`](../02-product/cod-lifecycle-and-reconciliation.md)
      §9 (PD-COD-6), and the COD PDs it depends on (PD-COD-1..3) are accepted.
- [ ] **G4-8 — Module boundary re-confirmed.** Fulfillment depends on
      `core + sale (+ stock_delivery, sale_stock)` and never on
      `shopify_connector_inventory`; Mode-1 location display uses core's
      location cache, not inventory's mapping table
      ([`../03-architecture/modular-architecture-recommendation.md`](../03-architecture/modular-architecture-recommendation.md)
      §2.3). The fulfillment-modes doc §8 open question (Mode 2 ↔ location
      mapping coupling) is resolved or explicitly deferred to Wave 5 with the
      Mode 2 allocation.
- [ ] **G4-9 — Rejected-approaches check recorded.** RA-009, RA-014, RA-022,
      RA-023 (and the full log) re-checked against the amended packet; no
      rejected approach re-enters without its revisit condition
      (`../05-qa/rejected-approaches-log.md`, CLAUDE.md §10).

## 3. Allowed / forbidden paths (wave-level; the re-issued Task 014 prompt is exhaustive)

- **Allowed:** `addons/shopify_connector_fulfillment/**` (new); the one named
  core readiness-check edit + its test (D-014-2); Layer-2 registration
  entries the accepted Layer 2 design requires for the fulfillment mutations;
  Wave 4 validation/evidence docs, AR-log rows, handoff, program state.
- **Forbidden:** any read of `shopify.connector.location.mapping`;
  `fulfillmentOrderMove`/hold mutations and `FULFILLMENT_ORDERS_*`
  subscriptions; legacy fulfillment endpoints (RA-022); refunds/returns
  automation; Mode 2 auto-application code; UI beyond what the packet
  explicitly allows (screens are Wave 5); webhooks/OAuth/CI; every protected
  reference; `adams_base`.

## 4. Wave acceptance criteria (observable)

1. **Outbound `fulfillmentCreate` with FO line mapping:** every validated
   eligible picking produces exactly one Shopify fulfillment via explicit
   `lineItemsByFulfillmentOrder` line lists resolved through
   `shopify_line_item_gid` (D-014-4); never double, never merged across
   backorders; unmatched lines never fulfilled by guess (RA-023).
2. **Tracking updates:** post-fulfillment tracking changes flow through
   `fulfillmentTrackingInfoUpdate` in place (never a second fulfillment),
   including multi-number split and missing-ref creation-with-note (D-014-6).
3. **External-fulfillment detection + review cases:** every observed
   fulfillment is origin-classified per the evidence stack (own-GID ledger →
   service handle → event attribution → unknown-defaults-to-external,
   fulfillment-operating-modes §3); external fulfillments produce Mode 1
   review cases with tracking-import / acknowledge / explicit-validation
   actions and zero automatic stock mutation.
4. **State-model badge storage with the unknown-value contract:** all four
   Shopify state families are stored raw + labeled per the status-model
   tables; deprecated values stored-raw + normalized (§6); any unknown future
   value satisfies all five §7 contract points (preserved raw, displayed
   unknown, never silently success, unsafe automation halted, schema warning
   raised).
5. **Carrier-Delivered inconsistency case:** a `DELIVERED` milestone (or
   `deliveredAt`) with the Odoo picking not `done` raises the high-visibility
   critical review case of status-model §8; no milestone ever validates
   stock.
6. **COD fulfillment scenarios 4–13:** the COD lifecycle scenarios that
   depend on fulfillment mechanics (full rejection at the door, failed
   delivery, RTO, warehouse return via `stock.return.picking` as the only
   stock-restoration path, partial delivery/collection, remainder
   cancellation with Administrator confirmation, backorder creation/
   completion/cancellation — `cod-lifecycle-and-reconciliation.md`
   §3.4–§3.13) each have implemented state derivation and tests; stock is
   never restored on courier/report evidence (PD-COD-2).
7. **Reconnect catch-up:** on reconnect, the fulfillment watermark scan
   re-reads FOs/fulfillments since the gap; every external fulfillment from
   the disconnected period lands as a review case (fulfillment-operating-modes
   §7); interrupted outbound work resumes under
   verification-read-before-retry.
8. **Layer 2 compliance proven:** every fulfillment mutation runs under the
   accepted Layer 2 protocol (durable attempt record before the call;
   reconciliation read on ambiguous outcome; no blind retry path exists —
   source-level test).
9. Task 014 packet §5/§6 test files and criteria (as extended by the
   addendum) all green on Odoo.sh; dev-store mutation evidence or a recorded
   explicit control-room waiver (mutation task rule).

## 5. Hard stops (wave-local restatement of program §8)

- Layer 2 missing, unproven, or bypassed for any fulfillment mutation →
  stop (hard-stop 4).
- Official Shopify evidence at implementation time contradicts the captured
  state model or scope set → stop (hard-stop 2); never improvise a mapping.
- Any path found that would auto-mutate Odoo stock from inbound evidence in
  Mode 1 → stop (security/data-integrity, hard-stops 6/9).
- Dev-store credentials required but not provisioned → stop (hard-stop 5);
  no simulated "live" evidence.
- The re-issued locked prompt drifts from the amended packet, or the base SHA
  drifts → stop.

## 6. Definition of done (wave)

Claude control-room wave review
([`../06-prompts/claude-mvp-wave-review-template.md`](../06-prompts/claude-mvp-wave-review-template.md))
accepts and merges into `mvp/program-integration`; acceptance-matrix row 12
(and the COD-affected rows) updated; handoff + program state updated; Mode 2
disposition for Wave 5 explicitly recorded (in scope / stretch-consumed /
deferred).
