# Implementation-Readiness Checklist (Waves 2–6)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** The single
> per-wave gate checklist the control room runs before authorizing any wave.
> Companion to the per-wave Definitions of Ready and
> [`waves-2-6-dependency-and-gate-map.md`](waves-2-6-dependency-and-gate-map.md);
> decision references resolve via
> [`../04-decisions/fable-proposed-decision-pack.md`](../04-decisions/fable-proposed-decision-pack.md).
> Planning only; no gate is opened by this file.
>
> **Current program state (2026-07-16):** Wave 1 is **merged** (PR #172) and
> **SRR-03 is CLOSED**; the QA matrices and premium UX master specification
> exist. Both fulfillment Mode 1 and Mode 2 **backend** are Wave 4 scope; Wave 5
> owns only the Mode 2 UI. SEC-2 (Wave 5) removes PII masking; the MVP has no
> PII masking (both roles read raw operational PII; redaction stays mandatory).

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

- [ ] Order-import decisions accepted: ORD-1..5, PD-COD-1..3 (import subset), PD-AC-1, reconnect order-domain subset.
- [ ] PD-E default-policy vs packet "no default" tension resolved at re-acceptance.
- [ ] Confirmed: no DEC-031 Layer 2 dependency (`remote_read_replay_safe` per DEC-033).
- [ ] Confirmed: no new PII-masking fields introduced (the MVP has no PII masking).
- [ ] Odoo.sh runtime evidence is the mandatory closure evidence (fresh install, upgrade, focused + full regression, security/duplicate tests, uninstall/reinstall, no-PII-leak).
- [ ] Read-only dev-store order evidence is **preferred but not a merge blocker**; if credentials are unavailable it defers to Wave 6 with no product-scope waiver (VAL-B2 not marked complete).
- [ ] `wave-2-definition-of-ready.md` NOT-YET list cleared (Wave 1 merged + SRR-03 closed already satisfied).

## Wave 3 — Inventory (Layer 2 Stage 0 + Task 013/013B)

- [ ] Wave 2 accepted and merged (Wave 3's wave-order dependency; Wave 1 is already merged and is not a Wave 3 blocker).
- [ ] DEC-031 Layer 2 design **Accepted** — then implemented as Stage 0 and runtime-proven (multi-worker, real 40001/lock-timeout, crash-injection) before any mutation domain code.
- [ ] Inventory operating-model PDs accepted.
- [ ] **CAS field-name empirical preflight** against the raw 2026-07 schema (`compareQuantity` vs D-013-3 `changeFromQuantity`) — fail-closed hard stop until resolved.
- [ ] Modular-architecture decisions accepted for the inventory module.
- [ ] Location-mapping model accepted; `write_inventory` scope path confirmed.
- [ ] Confirmed: no new PII-masking fields (inventory bindings carry no customer PII).
- [ ] Genuine dev-store mutation evidence required for closure (first mutation wave); exception = product-owner ruling only.

## Wave 4 — Fulfillment (Task 014 + inbound reconciliation, Mode 1 + Mode 2 backend)

- [ ] Fulfillment decision family accepted: FUL-1..FUL-5 **including FUL-2** — both Mode 1 and Mode 2 backend are required Wave 4 scope; Mode 2 is not optional/deferred.
- [ ] Mode 2 backend planned: per-store `fulfillment_operating_mode` field (both values), the exact 16-condition auto-application engine, the mode-switch state machine, and disconnected-period reconciliation.
- [ ] COD PD-COD fulfillment subset (scenarios 4–13) accepted.
- [ ] Readiness scope correction `read_fulfillments` → `read_merchant_managed_fulfillment_orders` scheduled inside the wave.
- [ ] Layer 2 proven in production use by Wave 3 (evidence cited).
- [ ] State-model fixtures for all seven Layer-A enum families (four-layer taxonomy) present in the test plan.
- [ ] Genuine dev-store fulfillment mutation evidence for **both** Mode 1 and Mode 2 required for closure (exception = product-owner ruling only).

## Wave 5 — Premium experience (SEC-2, U1–U3, PERF-1, Task 015/015B, fulfillment Mode UI)

- [ ] Role decisions (ROLE-1..5) accepted; **SEC-2 packet accepted (two-role migration + PII-masking removal)**; **SEC-2 sequenced before U1**.
- [ ] Confirmed: SEC-2 removes the Wave-1 PII masking — both roles read raw operational PII per permitted ops; no masked-PII surface, no unmask toggle, no separate PII tier; log/audit/credential/header redaction stays mandatory.
- [ ] Premium UX master spec (exists) accepted + prototype visual review of the twelve new surfaces.
- [ ] U1, then U2/U3 locked prompts issued only per phase acceptance; prototype-fidelity criteria attached.
- [ ] PD-PX-1..7 accepted; export uncertainty path wired to Layer 2.
- [ ] PERF-1 calibration plan confirmed against `../05-qa/performance-slo-benchmark-plan.md`.
- [ ] Fulfillment **Mode UI** (mode selector, confirmation screen, review workspace, dashboards) wired to the **already-delivered Wave 4 Mode 1 + Mode 2 backend**; no Mode 2 backend logic is built or deferred in Wave 5.

## Wave 6 — E2E, UAT, release

- [ ] Waves 2–5 merged; `wave-6-definition-of-ready.md` gates green.
- [ ] Dev-store UAT credentials provisioned by the product owner (hard stop — no live Shopify call has occurred yet).
- [ ] The read-only dev-store order UAT deferred from Wave 2 (if any) is executed here.
- [ ] CI enablement decision made explicitly (workflows are otherwise phase-forbidden).
- [ ] All UAT matrices executable (COD 16, fulfillment-mode covering **Mode 1 and Mode 2**, reconnect/backfill, security/PII, cross-domain) and acceptance matrix rows mapped; all mutation-domain UAT has genuine dev-store evidence.
- [ ] Two-role UAT and no-PII-masking UAT pass (no masked surface, no unmask toggle, no separate PII tier); raw-PII role access verified; log/audit/credential/header redaction verified in force.
- [ ] Visual-fidelity, performance/SLO, and release-readiness proof recorded.
- [ ] Release decision reserved to the product owner (never self-executed).

## Standing rules

Every box requires recorded evidence. No wave authorizes the next. No
decision in the pack is accepted by checking a box here — acceptance happens
in the decision records/logs first; this checklist only verifies it happened.
