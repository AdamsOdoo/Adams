# Wave 4 — Definition of Ready (Fulfillment & Tracking)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16; Wave 4 Gate A
> reconciliation appended 2026-07-21. NOT accepted.**
> **Acceptance authority (Wave 4): ChatGPT control room** (scope governor,
> acceptance, merge-authorizing authority), with the product owner as ultimate
> business authority — per issue #186 comment `5038326525`, which supersedes the
> earlier DEC-032 "product owner + Claude control room" wording **only** where it
> assigned Claude sole control-room/merge authority (all worker-separation,
> independent-review, source-of-truth, and no-self-acceptance safeguards remain
> binding). This checklist gates the *opening* of Wave 4; it authorizes no
> implementation by itself. Structure follows
> [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)
> (acceptance preconditions → allowed/forbidden → acceptance criteria → tests →
> rollback → definition of done), adapted to the macro-wave model.
>
> **Current program state (2026-07-21):** Waves 1–3 are **merged** into
> `mvp/program-integration` (base `ab4f12f5…` = PR #182 / Task 013 merge commit);
> **SRR-03 CLOSED**; the **DEC-036/DEC-031 Layer 2 substrate is Accepted
> (2026-07-19) and runtime-proven** in Wave 3 (G4-1 satisfiable). Wave 4 Gate A
> decision reconciliation is
> [`../04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md`](../04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md)
> (Proposed) — its 41-item matrix + the 16-condition Mode 2 reconciliation (12
> preserve / 4 refine) + the **applied Q1–Q8 rulings** (PR #188 comment `5041620950`,
> 2026-07-22; no longer open) + the **P0 reconcile-only uncertain-outcome contract**
> (DEC-038 §7.1) are the binding input to this DoR
> and the Task 014 packet re-acceptance (G4-5). As a Shopify-mutation wave, Wave 4
> closure requires **genuine (not simulated) dev-store fulfillment mutation
> evidence**, and **CV-013 (#185) — carried forward as critical — must execute
> green before final acceptance / RC / UAT** (not downgraded).

## 1. Wave objective (one scoped outcome)

Implement the complete fulfillment/tracking domain **backend** as the new
`shopify_connector_fulfillment` module. **Both Mode 1 and Mode 2 backend
behavior are required MVP Wave 4 scope** — the Administrator selects the
fulfillment operating mode per store, and the per-store
`fulfillment_operating_mode` field ships live with **both** values:

- **Task 014 outbound flow (Mode 1 default)** (picking-validation →
  `fulfillmentCreate` with explicit FulfillmentOrder line lists →
  `fulfillmentTrackingInfoUpdate`), exactly per
  [`task-014-fulfillment-tracking-implementation-packet.md`](task-014-fulfillment-tracking-implementation-packet.md)
  D-014-1..8 **as amended by that packet's 2026-07-16 gap-closure addendum**.
- **Inbound reconciliation and Mode 1 review logic**: observation of every
  Shopify fulfillment, origin classification, inbound evidence records, review
  cases, tracking import, and explicit User validation of exact proposals — per
  [`../02-product/fulfillment-operating-modes.md`](../02-product/fulfillment-operating-modes.md)
  §2–§3, §5–§7.
- **Mode 2 auto-application backend**: the exact 16-condition Mode 2 engine,
  the mode-switch state machine, and disconnected-period reconciliation are
  implemented, tested, and runtime-proven in Wave 4. **Mode 2 is NOT optional /
  a stretch / a "Wave 5 backend" / "if shipped" / "Mode 1 only".** Wave 4 MAY
  internally sequence Mode 1 before Mode 2, but **Wave 4 cannot close until both
  Mode 1 and Mode 2 backend behavior is implemented, tested, and runtime-proven**
  (per-store mode field, the exact 16-condition engine, inbound observation/
  evidence/bindings, the mode-switch state machine, reconnect reconciliation,
  COD interplay, the complete fulfillment-state taxonomy, and genuine dev-store
  fulfillment mutation UAT). **Wave 5 owns only the premium UI** — the
  Administrator mode selector, the mode explanation/confirmation screen, the
  unresolved-external-fulfillment UI, the User review workspace, reconciliation
  visualizations, mode-switch history, and fulfillment dashboards/timelines.
  **Wave 5 does NOT own the Mode 2 backend.**

## 2. Gates — every box must be checked before the wave opens

- [ ] **G4-1 — Layer 2 accepted, implemented, and proven (from Wave 3).**
      [`../03-architecture/dec-031-layer-2-mutation-safety-design.md`](../03-architecture/dec-031-layer-2-mutation-safety-design.md)
      is accepted (its §14 decision list), implemented in Wave 3, and has
      genuine (not simulated) runtime/concurrency proof recorded in the Wave 3
      wave review. `fulfillmentCreate` is not `@idempotent` (Task 014 packet
      D-014-7), so no fulfillment mutation may ship without Layer 2 durable
      attempt identity + reconciliation-before-retry (program hard-stop 4).
- [ ] **G4-2 — Fulfillment operating-modes PDs accepted.** The proposed
      decisions in `fulfillment-operating-modes.md` §11 (Mode 1 default,
      review-only inbound, 16-condition Mode 2 checklist, lot/serial rule,
      mode-switch state machine, disconnected-period rule, and the binding
      **Mode 2 Wave-4-backend allocation** — both Mode 1 and Mode 2 backend are
      required Wave 4 scope; Wave 5 owns only the mode UI) are accepted or
      explicitly amended by the control room.
- [ ] **G4-3 — Fulfillment state-model PDs accepted.** The proposed
      decisions in
      [`../02-product/shopify-fulfillment-status-model.md`](../02-product/shopify-fulfillment-status-model.md)
      §11 (the **four-layer fulfillment-state taxonomy** separation — Layer A
      seven Shopify enum families, Layer B non-enum surfaces, Layer C
      connector-derived states, Layer D user-facing labels — per-value mapping
      tables, deprecated-value handling, unknown-future-value contract,
      Delivered-inconsistency rule, badge/severity vocabulary) are accepted.
      The former Open question 1 (`FulfillmentDisplayStatus` values) is now
      **verified** (all seven Layer-A enum families incl. `FulfillmentDisplayStatus`,
      18 values, re-verified 2026-07-16; mapped display-only).
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
      mapping coupling) is resolved **within Wave 4** (Mode 2 backend is Wave 4
      scope), using core's location cache rather than inventory's mapping
      table — it is not deferred.
- [ ] **G4-9 — Rejected-approaches check recorded.** RA-009, RA-014, RA-022,
      RA-023 (and the full log) re-checked against the amended packet; no
      rejected approach re-enters without its revisit condition
      (`../05-qa/rejected-approaches-log.md`, CLAUDE.md §10).

## 3. Allowed / forbidden paths (wave-level; the re-issued Task 014 prompt is exhaustive)

- **Allowed:** the new `addons/shopify_connector_fulfillment/` addon — **enumerated
  file-by-file (no `**` wildcard authorization)** in the re-issued locked prompt §2
  (that list is the exhaustive authority; nothing outside it without a control-room
  amendment); the one named core readiness-check edit + its test (D-014-2); the
  add-only Layer-2 registration entries the accepted Layer 2 design requires; Wave 4
  validation/evidence docs, AR-log rows, handoff, program state.
- **Forbidden:** any read of `shopify.connector.location.mapping`;
  `fulfillmentOrderMove`/hold mutations and `FULFILLMENT_ORDERS_*`
  subscriptions; legacy fulfillment endpoints (RA-022); refunds/returns
  automation; all fulfillment/mode UI — the mode selector, mode-explanation/
  confirmation screen, review workspace, and dashboards/timelines are Wave 5
  (Mode 2 *backend* auto-application IS in scope; only its UI is forbidden
  here); webhooks/OAuth/CI; every protected reference; `adams_base`.

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
4. **State-model badge storage with the unknown-value contract:** all seven
   Layer-A Shopify enum families (per the four-layer fulfillment-state
   taxonomy) are stored raw + labeled per the status-model tables;
   deprecated values stored-raw + normalized (§6); `FulfillmentDisplayStatus`
   (A7) is treated display-only, never an automation input; any unknown future
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
   §7); interrupted outbound work resumes **reconcile-only** (no resend from a read
   miss; DEC-038 §7.1), and all catch-up reads are **cursor-paginated to completion**
   (§7.4).
8. **Per-store mode field + Mode 2 auto-application engine:** the
   `fulfillment_operating_mode` field is live with **both** values, selectable
   by the Administrator; Mode 2 auto-applies an Odoo fulfillment **only** when
   all conditions of the exact 16-condition checklist hold, and otherwise
   routes to a review case — with a pass test and a fail-to-review test for
   **each** of the 16 conditions, and genuine dev-store proof of at least one
   Mode 2 auto-application.
9. **Mode-switch state machine + disconnected-period reconciliation:**
   switching a store between Mode 1 and Mode 2 (and back) follows the
   documented state machine; in-flight and disconnected-period items are
   reconciled per fulfillment-operating-modes §7 with no double-apply and no
   lost review case.
10. **Layer 2 compliance proven:** every fulfillment mutation runs under the
    accepted Layer 2 protocol (durable attempt record before the call;
    **once `transport_attempted=true` the job is reconcile-only** — the mutation is
    never re-sent; **read absence → INCONCLUSIVE**, only positive non-application
    evidence authorizes a replacement job; no resend-from-absence path exists —
    source-level test; DEC-038 §7.1). Notification side effects obey the same rule
    (a possible prior `notifyCustomer=true` is never repeated from absence).
11. Task 014 packet §5/§6 test files and criteria (as extended by the
    addendum) all green on Odoo.sh; **genuine dev-store fulfillment mutation
    evidence** for both Mode 1 and Mode 2 paths (any exception is a specific
    product-owner ruling on the record, never a routine control-room waiver).

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
(and the COD-affected rows) updated; handoff + program state updated. Both
Mode 1 and Mode 2 backend behavior is delivered and runtime-proven inside
Wave 4 — the only Mode 2 item carried forward is the Wave 5 **UI** (mode
selector, review workspace, dashboards), whose backend contract Wave 4
hands off intact.

## 7. Bounded control-room correction (2026-07-22)

Applied per PR #188 comment `5041620950` / issue #186 comment `5041623758`, the DoR
now carries these binding contracts (detail in DEC-038 §4/§7 + Task 014 packet §11 +
the locked prompt): **(P0)** uncertain remote outcomes are **reconcile-only** — read
absence is INCONCLUSIVE, only positive non-application evidence authorizes a
replacement, notifications fail closed (criteria #7/#10); **(Q1–Q8)** ruled and applied
(operation-scope literals, adopt `sale_stock` pickings, core location cache only,
`fulfillment_tracking_change` with `ondelete`, fulfillment-owned COD read, Q6 carrier
fail-closed, `store.api_version`, staff-permission NOT_PROVEN); the **complete
job/replay taxonomy**, **modular file + exact test allowlist**, **cursor pagination**,
**fixed error/review vocabulary** (no `over_fulfillment`/no new selection value),
**lifecycle `ondelete`**, and **staff-permission/API-version** policies are frozen.
These are binding inputs to G4-5 re-acceptance; the gate checkboxes above remain
**unchecked** (control-room acceptance is not self-granted here).
