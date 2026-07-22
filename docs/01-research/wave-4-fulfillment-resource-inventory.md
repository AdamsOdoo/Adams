# Wave 4 Fulfillment — Resource Inventory & Authority Map (Gate A)

> **Status: CANDIDATE — Gate A Phase 1 output, pending independent control-room
> (ChatGPT) acceptance.** Produced by Claude as the explicitly-assigned Wave 4
> Gate A governance/research worker (issue #186 comment `5038326525`), on branch
> `claude/wave-4-gate-a-review-0nbhdw`, base
> `mvp/program-integration@ab4f12f5a6857b2f3318ffc3b3f5f371307938bc`.
> This file authorizes no implementation. It maps the current fulfillment
> contract vs history so the later phases can distinguish accepted rulings from
> proposals and supersessions.
>
> **Verification basis.** Every classification below was produced by reading the
> file in full and cross-checking status/lineage; version-sensitive Shopify
> claims embedded in these docs were independently re-verified against current
> official shopify.dev Admin GraphQL docs (Admin API version **2026-07**,
> accessed **2026-07-21**) — see the companion
> [`wave-4-shopify-official-fulfillment-notes.md`](wave-4-shopify-official-fulfillment-notes.md).

**Access date for all repo/GitHub facts:** 2026-07-21.

---

## 1. Canonical-output mapping (the 16 Gate A functions → canonical file)

Per the locked prompt §16, the Gate A package must provide 16 functions. This
table records which existing canonical file carries each (reuse, do not fork);
"NEW (this session)" marks a Gate A default-path artifact created here.

| # | Gate A function | Canonical carrier |
|---|---|---|
| 1 | Resource inventory & authority map | **this file** (`docs/01-research/wave-4-fulfillment-resource-inventory.md`) — NEW |
| 2 | Official Shopify fulfillment source refresh | `docs/01-research/wave-4-shopify-official-fulfillment-notes.md` — NEW |
| 3 | Official Odoo 19 fulfillment architecture notes | `docs/01-research/wave-4-odoo19-fulfillment-architecture-notes.md` — NEW |
| 4 | Actual merged-code integration audit | `docs/03-architecture/wave-4-fulfillment-current-code-audit.md` — NEW |
| 5 | Decision reconciliation record | `docs/04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md` — NEW (next unused DEC; see §4) |
| 6 | Wave 4 Definition of Ready | `docs/07-implementation-plan/wave-4-definition-of-ready.md` — **REUSE/UPDATE** |
| 7 | Task 014 implementation packet | `docs/07-implementation-plan/task-014-fulfillment-tracking-implementation-packet.md` — **REUSE/UPDATE** |
| 8 | Modular architecture & Layer 2 contract | carried in DEC-038 §arch + the Task 014 packet + this file §2; Layer 2 source of record = `docs/04-decisions/DEC-036-wave-3-layer-2-gate.md` (+ design `dec-031-layer-2-mutation-safety-design.md`) |
| 9 | Exact allowed/forbidden file lists | `docs/06-prompts/sol-wave-4-fulfillment-locked-prompt.md` (NEW) + DoR §3 |
| 10 | Complete test & evidence matrix | `docs/05-qa/fulfillment-mode-uat-matrix.md` — **REUSE/UPDATE** |
| 11 | Wave 4 dev-store validation plan | `docs/05-qa/fulfillment-mode-uat-matrix.md` (same canonical carrier) |
| 12 | Rollback plan | `docs/06-prompts/sol-wave-4-fulfillment-locked-prompt.md` + DoR §5 + DEC-038 |
| 13 | Locked, unissued implementation prompt | `docs/06-prompts/sol-wave-4-fulfillment-locked-prompt.md` — NEW, marked `LOCKED CANDIDATE — NOT ISSUED` |
| 14 | Live program-state + acceptance-matrix updates | `docs/07-implementation-plan/mvp-program-state.md`, `docs/05-qa/mvp-acceptance-matrix.md` — **REUSE/UPDATE** |
| 15 | Research/architecture-review/risk/handoff updates | `docs/01-research/research-handoff.md`, `docs/05-qa/architecture-review-log.md`, `docs/05-qa/sync-engine-risk-register.md`, `docs/07-implementation-plan/wave-4-gate-a-handoff.md` — **REUSE/UPDATE** |
| 16 | Quality-feedback-loop review recorded in research-handoff | `docs/01-research/research-handoff.md` (Learning feedback loop) — **REUSE/UPDATE** |

**Anti-duplication rule honored:** no near-name replacement of an existing
canonical DoR, Task 014 packet, or UAT matrix is created (adjudication PR #187
comment `5038405915` P1-3). The superseded `task-014-fulfillment-tracking-proposed.md`
is retained as history and NOT edited.

---

## 2. Fulfillment authority map — accepted contract vs proposal vs history

### 2.1 ACCEPTED (binding today)

| Record | What it binds for Wave 4 | Acceptance |
|---|---|---|
| **DEC-011** (fulfillment architecture strategy, AR-008) | FulfillmentOrder-based mutations only (`fulfillmentCreate`/`fulfillmentTrackingInfoUpdate`); `lineItemsByFulfillmentOrder` matching; notification default-off; operation-level idempotency key + DEC-009 verify-before-retry; no dependency on `shopify_connector_inventory` mapping; live `assignedLocation` authoritative. **Leaves OPEN:** exact fields, partial/backorder linkage, idempotency-key schema, location-confirmation mechanism, retry constants, notification-UI granularity. | ChatGPT, 2026-07-02 (PR #66) |
| **DEC-036** (Wave 3 Gate A: DEC-031 Layer 2 acceptance, L2-D1…L2-D38) + **DEC-031** (Layer 1 + Layer 2) | The accepted Layer 2 mutation-safety protocol every fulfillment mutation must run under (durable attempt identity, C1/C2/NET/C3, two-hash fingerprints, operation-scope serialization, reconciliation-before-retry, no-false-success, no unsupported exactly-once claim). Design companion = `dec-031-layer-2-mutation-safety-design.md`. | Product owner + Claude control room, 2026-07-19 (PR #177 comment `5015044226`) |
| **DEC-033** §6 (Wave 0 reconciliation) | ACCEPTS the readiness scope correction `read_fulfillments` → `read_merchant_managed_fulfillment_orders` + fulfillment-domain-conditional `write_merchant_managed_fulfillment_orders` (Task 014 D-014-2); delegates implementation to Wave 4. | Claude control room, 2026-07-15 (PR #169) |
| **DEC-008** (module boundary, AR-004) | Dependency DAG: fulfillment depends on core+sale, **never** on inventory; inventory is sole owner of the location-mapping table. Exact Odoo-addon refinement (adds `stock_delivery` + `sale_stock`) lives in DEC-018 + `modular-architecture-recommendation.md` §2.3. | ChatGPT, 2026-07-02 (PR #64) |
| **DEC-015** (master blueprint inventory+fulfillment) | Blueprint-level fulfillment internal design (Part C §B): core-owned Shopify-Location reference vs inventory-owned mapping; live-`assignedLocation` resolution. Named-open rows: MBQ-41 (notif UI), MBQ-60 (`stock_delivery` — now decided DEC-018), MBQ-61 (FO lifecycle subs excluded), MBQ-62 (job-source). | 2026-07-03 |
| **RA-009 / RA-014 / RA-017 / RA-022 / RA-023** (rejected-approaches-log) | Binding do-not-re-propose bars: notification hidden/default-on (RA-009); retry-everything (RA-014); binding-alone idempotency (RA-017); legacy Order/Fulfillment API (RA-022); fulfillment by order-ID / without exact FO-line-qty-location matching (RA-023). All accepted 2026-07-02 (PR #66). | ChatGPT, 2026-07-02 |

### 2.2 PROPOSED — not accepted (Gate A must reconcile / escalate; do not treat as settled law)

| Record | What it proposes | Note |
|---|---|---|
| **Task 014 implementation packet** (`task-014-…-implementation-packet.md`) | D-014-1…8 closures + 2026-07-16 Fable gap-closure addendum (§9: operating modes, inbound evidence model, state-model storage, COD interplay, Layer 2 supersession of D-014-7, new settings/tests). AR-042 (Proposed). | Re-acceptance required as one unit (DoR G4-5). Its §8 "locked prompt" targets the **wrong base** (`Shopify-connector`) and must be re-issued (see DEC-038 + the NEW locked prompt). |
| **fulfillment-operating-modes.md** | Mode 1 (default, review-only inbound) + Mode 2 (the **16-condition** exact-conditions engine §4), §4.1 deterministic picking selection, inbound reconciliation model §5, mode-switch state machine §6, reconnect §7, wave allocation §10 (both modes = Wave 4 backend; Wave 5 = UI only). | The 16-condition engine is **PROPOSED**; preserve exactly where evidence supports, escalate line-level corrections where it conflicts (adjudication P1-2). |
| **shopify-fulfillment-status-model.md** | Four-layer taxonomy; 7 Layer-A enum families; deprecated handling §6; unknown-future-value contract §7; Delivered-inconsistency rule §8. **Content independently re-verified EXACT-MATCH vs official 2026-07 docs (2026-07-21).** | Authoritative-by-content; governance status still "Proposed". |
| **cod-lifecycle-and-reconciliation.md** | COD ↔ fulfillment scenarios 2–13, PD-COD-1…6, `stock.return.picking` as the only stock-restoration path (PD-COD-2), backorder ask/always/never, remainder cancellation gating, `orderMarkAsPaid` deferred to Wave 5+. | Wave 4 owns scenarios 4–13 fulfillment mechanics (DoR G4-7). |
| **reconnect-catchup-backfill-policy.md** | Per-domain reconnect/catch-up/backfill (watermarks, quiescence, catch-up ordering); Wave 4 fulfillment catch-up + external-fulfillment review-landing. | §4.5 wording "(Mode-dependent)" vs modes-doc §7 "review in both modes" — reconcile in DEC-038. |
| **wave-4-definition-of-ready.md** | 9 gates (G4-1…G4-9), allowed/forbidden paths, 11 acceptance criteria, hard stops, DoD. | REUSE/UPDATE. Still cites the superseded DEC-032 "Claude control room" authority — reconcile to comment `5038326525`. |
| **modular-architecture-recommendation.md** §2.3 | Current Odoo dep contract `core+sale+stock_delivery+sale_stock`; fulfillment module-boundary validation. | Proposed-supporting. |
| **security-pii-matrix-waves-2-6.md** §3/§4 | Fulfillment address/tracking logging + Layer-2 attempt-record redaction; 2026-07-16 no-masking ruling. | Proposed planning. |
| **waves-2-6-dependency-and-gate-map.md** | Cross-wave dependency/decision-gate map. **Contains NO "Wave 4 Gate A–E" lettered structure** — that model lives only in issue #186. | §2 status column stale (shows Accepted Wave-2/3 gates as Proposed-blocking). |

### 2.3 SUPERSEDED / HISTORICAL (do not use as implementation source)

| Record | Disposition |
|---|---|
| `task-014-fulfillment-tracking-proposed.md` | **SUPERSEDED** 2026-07-16; canonical successor = the implementation packet. Retain unchanged as history. |
| `disconnect-quiescence-remediation-analysis.md` | Current-supporting mechanism-design reference behind DEC-031; its "SRR-03 stays OPEN" header is superseded (SRR-03 **CLOSED** 2026-07-16). |
| `ar008-fulfillment-architecture-decision-brief.md` | Evidence brief behind DEC-011 (accepted); its "proposed core-Location reference" framing is now resolved/accepted. |
| `master-blueprint-inventory-fulfillment.md` §B.1 "core+sale only" | Coarser/earlier than the canonical `core+sale+stock_delivery+sale_stock` (DEC-018 + modular-arch §2.3). No content revision; readers consult the refined contract. |

---

## 3. Full resource inventory table

Legend — **Class**: A=authoritative, S=current-supporting, X=superseded, H=historical.
Status abbreviations: Acc=Accepted, Prop=Proposed.

| Path | Title | Date | Status | Class | Gate A relevance / revision |
|---|---|---|---|---|---|
| `docs/04-decisions/DEC-011-…strategy.md` | Fulfillment architecture strategy (AR-008) | 2026-07-02 | Acc (ChatGPT) | A | Accepted posture; open items → DEC-038. |
| `docs/04-decisions/DEC-036-wave-3-layer-2-gate.md` | Layer 2 acceptance (L2-D1…D38) | 2026-07-19 | Acc | A | Layer-2 decision of record for fulfillment mutations. |
| `docs/04-decisions/DEC-031-…replay-safety.md` | Replay-safety L1+L2 (AR-048) | L1 2026-07-15 / L2 2026-07-19 | Acc | A | Add a top status banner (L2 ACCEPTED) — cosmetic. |
| `docs/03-architecture/dec-031-layer-2-mutation-safety-design.md` | Layer 2 design (C1/C2/NET/C3) | reg 2026-07-16; acc 2026-07-19 | Acc | S | Reconcile residual "Proposed" prose + stale §14 L2-D7/L2-D13 rows (cosmetic). |
| `docs/04-decisions/DEC-033-…wave-0-reconciliation.md` | Wave 0 reconciliation | 2026-07-15 | Acc (Claude CR) | A | §6 accepts scope correction. |
| `docs/04-decisions/DEC-008-module-boundary-strategy.md` | Module boundary (AR-004) | 2026-07-02 | Acc | A | Dependency DAG; addon set refined by DEC-018. |
| `docs/04-decisions/DEC-015-…inventory-fulfillment.md` | Master-blueprint inventory+fulfillment | 2026-07-03 | Acc | A | Blueprint-level fulfillment design. |
| `docs/07-implementation-plan/task-014-…implementation-packet.md` | Task 014 packet + §9 addendum | 2026-07-10 / add 2026-07-16 | Prop (AR-042) | A | REUSE/UPDATE; re-acceptance as one unit; §8 prompt re-issue. |
| `docs/02-product/fulfillment-operating-modes.md` | Operating modes (16-cond Mode 2) | 2026-07-16 | Prop | A | Reconcile 16-condition engine in DEC-038. |
| `docs/02-product/shopify-fulfillment-status-model.md` | State model (4-layer taxonomy) | 2026-07-16 | Prop | A | Content EXACT-MATCH vs 2026-07 official; acceptance only. |
| `docs/02-product/cod-lifecycle-and-reconciliation.md` | COD lifecycle | 2026-07-16 | Prop | A | Lift OQ-COD-2 (`orderMarkAsPaid` input now verified). |
| `docs/02-product/reconnect-catchup-backfill-policy.md` | Reconnect/catch-up policy | 2026-07-16 (§4.4 2026-07-19) | Prop | A | Reconcile "(Mode-dependent)" vs "review in both modes". |
| `docs/07-implementation-plan/wave-4-definition-of-ready.md` | Wave 4 DoR | 2026-07-16 | Prop | A | REUSE/UPDATE; authority-model reconcile. |
| `docs/03-architecture/modular-architecture-recommendation.md` | Module-family validation §2.3 | 2026-07-16 | Prop | S | Current Odoo dep contract. |
| `docs/00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md` | Tier-1 Shopify captures | 2026-07-16 | Capture | S | Update §2 L44 `orderMarkAsPaid`; §9 L201 `compareQuantity`→`changeFromQuantity` (inventory, non-fulfillment). |
| `docs/05-qa/rejected-approaches-log.md` | Rejected approaches | 2026-07-02 (RA-024 07-07) | Acc | A | Refresh stale "17 @idempotent" note (RA-014/RA-017). |
| `docs/05-qa/architecture-review-log.md` | Architecture review log | AR-008 2026-07-02; AR-059 2026-07-19 | Acc | A | Append Gate A row; refresh AR-008 stale "17" evidence cell. |
| `docs/05-qa/sync-engine-risk-register.md` | Risk register | SRR-03 CLOSED 2026-07-16 | Research | S | Add fulfillment-mutation risk if demonstrated. |
| `docs/05-qa/quality-feedback-loop.md` | Quality loop §10/§11 | 2026-07-10 | Recommendation | S | End-of-session learning-review procedure. |
| `docs/05-qa/security-pii-matrix-waves-2-6.md` | Security/PII Waves 2–6 §3/§4 | 2026-07-16 | Prop | S | Fulfillment logging/redaction surface. |
| `docs/07-implementation-plan/mvp-completion-program.md` | MVP program (frozen contract) | 2026-07-15 (upd 2026-07-16) | Acc | A | §9: record completed PR #150/#151 closure. |
| `docs/07-implementation-plan/mvp-program-state.md` | Live program state | live (top 2026-07-21) | Live | A | UPDATE Wave 4 Gate A row; refresh "Active wave" heading. |
| `docs/05-qa/mvp-acceptance-matrix.md` | Acceptance matrix | living (2026-07-19) | Living | S | UPDATE row 12; re-sync stale row 9. |
| `docs/07-implementation-plan/waves-2-6-dependency-and-gate-map.md` | Dependency/gate map | 2026-07-16 | Prop | S | No lettered Wave 4 gates (issue #186 owns them). |
| `docs/03-architecture/master-blueprint-inventory-fulfillment.md` | Master blueprint Part C | 2026-07-03 | Acc (DEC-015) | A | Odoo dep set refined by DEC-018. |
| `docs/03-architecture/ar008-fulfillment-architecture-decision-brief.md` | AR-008 brief | 2026-07-02 | Evidence | S | Historical evidence behind DEC-011. |
| `docs/01-research/wave-0-roles-permissions-and-fulfillment-scope-refresh.md` | Wave 0 scope refresh | 2026-07-15 | Acc via DEC-033 §6 | S | Scope-correction basis. |
| `docs/07-implementation-plan/task-014-fulfillment-tracking-proposed.md` | Task 014 (early proposed) | superseded 2026-07-16 | X | Do NOT edit/use. |

Additional referenced records: DEC-009 (error/retry/idempotency — accepted), DEC-018 (module/dependency architecture — names `stock_delivery`+`sale_stock`), DEC-019 (job-source/trigger-origin vocabulary), DEC-030 (module lifecycle/uninstall), `final-mvp-module-and-dependency-architecture.md` §1 (exact Odoo addon set). UI prototypes under `docs/09-ui-prototype/**` are **Wave 5 scope** (out of Wave 4 backend).

---

## 4. Next unused decision identifier

Highest existing decision record = **DEC-037** (`DEC-037-wave-3-inventory-gate-b.md`).
No `DEC-038`+ file exists (repo-verified 2026-07-21). **Next unused = `DEC-038`**,
used here for the Gate A decision-reconciliation record
`docs/04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md`
(remains **Proposed** until control-room acceptance).

---

## 5. Contradictions & revision-required register (feeds Phase 4 / DEC-038)

Material contradictions/gaps surfaced during inventory (each dispositioned in
DEC-038):

1. **`@idempotent` "17 mutations" count — CORRECTED (not stale).** This item was
   initially flagged as stale; **Phase 2 direct verification of the live official
   idempotency page (dated 2026-02-02, accessed 2026-07-21) confirms the list is
   still exactly 17 mutations, with `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate`
   absent** — corroborated by the 2026-01 changelog. The only 2026-04 change is that
   supplying an `@idempotent` key became *mandatory* for those 17 (inventory/refund)
   mutations; fulfillment is unaffected. So the "17-mutation" wording in RA-014,
   RA-017, AR-008, and DEC-011 is **accurate** (a clarifying refresh, not a
   correction, is warranted). The **decision-critical consequence is confirmed and
   unchanged:** fulfillment mutations have **no native idempotency** → verify-before-
   retry + operation-scope serialization under Layer 2 remains the **primary**
   duplicate-prevention control (see Shopify notes §4.1, DEC-038 item 27).
2. **Authority model drift** — DoR, modes doc, status model, COD doc, program
   files still cite the DEC-032 "product owner + Claude control room" acceptance
   model. Superseded for Wave 4 by issue #186 comment `5038326525` (ChatGPT =
   control room/acceptance; Claude = independent reviewer/authorized governance
   worker). Reconcile wording, preserve the no-self-acceptance/worker-separation
   safeguards.
3. **Task 014 packet §8 locked prompt targets the wrong base** (`Shopify-connector`,
   omits Layer 2 + modes). Must be re-issued as the NEW candidate locked prompt
   against `mvp/program-integration@ab4f12f5` — Phase 6.
4. **Reconnect "(Mode-dependent)" vs "review in both modes"** — modes doc §7 is
   the stricter, safer rule (disconnected-period external fulfillments → review
   in both modes); reconnect policy §4.5 wording should align to it.
5. **PR #150/#151** — mvp-completion-program §1/§2 still lists them as "live/open
   draft"; they are in fact **closed unmerged (2026-07-15, pre-Wave-4), heads
   unchanged, not merged**. This is a program-acknowledged administrative
   closure-as-superseded (§9), NOT an unexpected protected-reference change — no
   hard stop. Recommend a §9/§1 note recording the completed closure.
6. **Tracker staleness (non-fulfillment)** — `mvp-program-state.md` "Active wave"
   heading + acceptance-matrix row 9 lag behind the merged Wave-2 Campaign-4
   state. Out of Wave 4 scope to fix beyond the Wave 4 rows; noted for the
   control room.
7. **Odoo dependency-set layering** — DEC-008 "stock/delivery apps directly" →
   refined to `stock_delivery` + `sale_stock` (DEC-018 + modular-arch §2.3);
   consistent, not a conflict. Module-name correctness (`stock_delivery` vs
   `delivery`) verified against Odoo 19 source — see Odoo notes.
8. **`orderMarkAsPaid` OQ-COD-2** — input shape now live-verified
   (`OrderMarkAsPaidInput!{id:ID!}`); the COD doc + capture hedge can be lifted.
   `orderMarkAsPaid` remains **out of Wave 4** (Wave 5+, Layer-2-gated).

**Phase 1 completion criterion met:** the authority map above is sufficient to
distinguish the current fulfillment contract (accepted DEC-011 + DEC-036/031
Layer 2 + DEC-033 scope + DEC-008/015 boundaries + RA bars) from the proposed
candidates (Task 014 packet, modes, status model, COD, reconnect, DoR) and the
superseded/historical records.
