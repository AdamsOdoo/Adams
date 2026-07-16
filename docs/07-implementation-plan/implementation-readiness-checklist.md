# Implementation-Readiness Checklist (Waves 2–6)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** The single
> per-wave gate checklist the control room runs before authorizing any wave.
> Companion to the per-wave Definitions of Ready and
> [`waves-2-6-dependency-and-gate-map.md`](waves-2-6-dependency-and-gate-map.md);
> decision references resolve via
> [`../04-decisions/fable-proposed-decision-pack.md`](../04-decisions/fable-proposed-decision-pack.md).
> Planning only; no gate is opened by this file.

## How to use

Before authorizing Wave N, the control room checks every row for that wave.
Any unchecked row = the wave stays unauthorized. A row is satisfied only by
a recorded act (acceptance note in the decision/architecture-review logs, a
merged PR, a provisioned credential confirmed by the product owner), never
by intention.

## Universal preconditions (every wave)

- [ ] Previous wave MERGED and recorded in `mvp-program-state.md`.
- [ ] Protected refs verified unchanged (checkpoint / `Shopify-connector` / `main`).
- [ ] The wave's Definition of Ready reviewed and accepted.
- [ ] The wave's packet(s) re-accepted **with** their 2026-07-16 addenda.
- [ ] Allowed/forbidden file lists confirmed against current tree (no drift).
- [ ] Rejected-approaches log (RA-001..024) re-checked against the wave design.
- [ ] QA matrices for the wave adopted as the binding test/UAT basis.
- [ ] Wave review will use `../06-prompts/claude-mvp-wave-review-template.md`.

## Wave 2 — Order import (Task 012 + Area-6 order-scan)

- [ ] Decision Group B accepted: ORD-1..5, PD-COD-1..3 (import subset), PD-AC-1, reconnect order-domain subset.
- [ ] PD-E default-policy vs packet "no default" tension resolved at re-acceptance.
- [ ] Confirmed: no DEC-031 Layer 2 dependency (`remote_read_replay_safe` per DEC-033).
- [ ] `wave-2-definition-of-ready.md` NOT-YET list cleared.
- [ ] Dev-store read credentials provisioning plan confirmed (hard-stop 5 aware).

## Wave 3 — Inventory (Layer 2 Stage 0 + Task 013/013B)

- [ ] DEC-031 Layer 2 design **Accepted** (Group E) — then implemented as Stage 0 and runtime-proven (multi-worker, real 40001/lock-timeout, crash-injection) before any mutation domain code.
- [ ] Inventory operating-model PDs accepted (Group D subset).
- [ ] **CAS field name re-verified against the raw 2026-07 schema** (`compareQuantity` vs D-013-3 `changeFromQuantity`) — hard stop until resolved.
- [ ] Modular-architecture decisions (Group F) accepted for the inventory module.
- [ ] Location-mapping model accepted; `write_inventory` scope path confirmed.

## Wave 4 — Fulfillment (Task 014 + inbound reconciliation, Mode 1)

- [ ] Fulfillment decision family accepted: FUL-1, FUL-3, FUL-4, FUL-5 (FUL-2/Mode 2 may defer to Wave 5).
- [ ] COD PD-COD fulfillment subset (scenarios 4–13) accepted.
- [ ] Readiness scope correction `read_fulfillments` → `read_merchant_managed_fulfillment_orders` scheduled inside the wave.
- [ ] Layer 2 proven in production use by Wave 3 (evidence cited).
- [ ] State-model fixtures (56) present in the test plan.

## Wave 5 — Premium experience (SEC-2, U1–U3, PERF-1, Task 015/015B, optional Mode 2)

- [ ] Group A (ROLE-1..5) accepted; SEC-2 packet accepted; **SEC-2 sequenced before U1**.
- [ ] Group G accepted: premium UX master spec + prototype visual review of the twelve new surfaces.
- [ ] U1, then U2/U3 locked prompts issued only per phase acceptance; prototype-fidelity criteria attached.
- [ ] PD-PX-1..7 accepted; export uncertainty path wired to Layer 2.
- [ ] PERF-1 calibration plan confirmed against `../05-qa/performance-slo-benchmark-plan.md`.
- [ ] If Mode 2 in scope: FUL-2 accepted + Mode 2 UAT matrix adopted.

## Wave 6 — E2E, UAT, release

- [ ] Waves 2–5 merged; `wave-6-definition-of-ready.md` gates green.
- [ ] Dev-store UAT credentials provisioned by the product owner (hard stop — zero live Shopify calls have ever occurred).
- [ ] CI enablement decision made explicitly (workflows are otherwise phase-forbidden).
- [ ] All UAT matrices executable (COD 16, fulfillment-mode, reconnect/backfill) and acceptance matrix rows mapped.
- [ ] Release decision reserved to the product owner (never self-executed).

## Standing rules

Every box requires recorded evidence. No wave authorizes the next. No
decision in the pack is accepted by checking a box here — acceptance happens
in the decision records/logs first; this checklist only verifies it happened.
