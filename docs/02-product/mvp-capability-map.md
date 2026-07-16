# MVP Capability Map — Current-State Snapshot (post-Wave-1)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** A factual
> current-state snapshot of every MVP capability after the Wave 1 merge
> (PR #172, merge commit `d18f9a9`), for product-owner orientation.
> Acceptance authority: product owner + Claude control room. **No
> implementation authorized.** This map classifies and points; it makes no
> new decisions. Source of truth for per-item release criteria:
> [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md)
> (23 MVP-contract items); for wave status:
> [`../07-implementation-plan/mvp-program-state.md`](../07-implementation-plan/mvp-program-state.md).

Status legend:
- **Merged-checkpoint** — implemented and runtime-proven at or before the
  protected checkpoint (`checkpoint/core-r2-readonly-uat-2026-07-15`).
- **Merged-Wave-1** — implemented/merged via PR #172 (2026-07-16).
- **Designed-this-mission-Proposed** — a canonical spec/policy doc was
  authored in this Fable gap-closure mission; Proposed, unaccepted.
- **Packet-exists-Proposed** — an implementation-ready planning packet exists
  (Proposed, gate not opened).
- **Not-started** — neither design doc nor packet at implementable fidelity.

Lite/Full column per accepted DEC-029: **Lite** = `core` + `product` + `sale`
(read-only into Odoo, zero Shopify mutations); **Full** = Lite +
`inventory` + `fulfillment` + `product_export`. Source:
[`./lite-full-packaging-final-proposal.md`](./lite-full-packaging-final-proposal.md).

## Capability map

| # (matrix) | Capability | Status | Owning wave | Canonical spec doc | Gating decisions | Lite / Full |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Store connection + lifecycle (backend) | Merged-Wave-1 (backend; UI remains) | 5 (UI) | [`../07-implementation-plan/task-005-connection-lifecycle-gate.md`](../07-implementation-plan/task-005-connection-lifecycle-gate.md) | DEC-022/024 | Lite |
| 2 | Secure credential storage/redaction | Merged-checkpoint (deployment posture remains) | 6 (posture evidence) | [`../07-implementation-plan/task-002-credential-storage-gate.md`](../07-implementation-plan/task-002-credential-storage-gate.md) | DEC-028 (Accepted; deployment evidence before real PII) | Lite |
| 3 | Test connection / readiness checks | Merged-Wave-1 (CORE-R1; live VAL-B2 remains) | 6 (live evidence) | [`../07-implementation-plan/task-core-r1-readiness-correction-packet.md`](../07-implementation-plan/task-core-r1-readiness-correction-packet.md) | DEC-034 | Lite |
| 4 | Guided setup wizard (U2) | Not-started (prototype only) | 5 | [`../09-ui-prototype/`](../09-ui-prototype/) setup-readiness; [`./ui-ux-final-design-spec.md`](./ui-ux-final-design-spec.md) | DEC-016 | Lite |
| 5 | Operational dashboard (U1) | Not-started (prototype only) | 5 | [`../09-ui-prototype/`](../09-ui-prototype/) dashboard; [`./ui-ux-final-design-spec.md`](./ui-ux-final-design-spec.md) | DEC-016; Area 6 (Wave 2+) | Lite |
| 6 | Product/variant import | Merged-checkpoint | — (re-confirm Wave 6) | [`../07-implementation-plan/task-010b-product-import-completeness-packet.md`](../07-implementation-plan/task-010b-product-import-completeness-packet.md) (Task 010/010B) | DEC-003/007 | Lite |
| 6 | Controlled product export/update + basic media export | Packet-exists-Proposed (Tasks 015/015B) + operating model designed this mission | 5 | [`./product-export-operating-model.md`](./product-export-operating-model.md); packets 015/015B | DEC-033 §1 (Accepted); **DEC-031 Layer 2 (undesigned)**; C-PROD-05 | Full (`product_export`; opt-in flag even in Full) |
| 7 | First-sync product matching + duplicate prevention | Merged-checkpoint | — (re-confirm Wave 6) | Task 010B packet; [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md) row 7 | DEC-006 | Lite |
| 8 | Customer import + matching (incl. 100k-partner benchmark) | Merged-checkpoint | — (re-confirm Wave 6) | Task 011/011B packets | DEC-006; AR-045 | Lite |
| 9 | Order import → Odoo sales orders, confirmation policy, COD | Packet-exists-Proposed (Task 012) + confirmation/COD policy designed this mission | 2 | [`./sales-order-lifecycle-and-confirmation-policy.md`](./sales-order-lifecycle-and-confirmation-policy.md); [`../07-implementation-plan/task-012-order-import-implementation-packet.md`](../07-implementation-plan/task-012-order-import-implementation-packet.md) | DEC-033/034; Wave 2 unauthorized until its own preflight | Lite |
| — | Abandoned checkouts (default policy: no import; optional workspace) | Designed-this-mission-Proposed (policy-only) | — (policy) / post-MVP (workspace) | [`./abandoned-checkout-policy.md`](./abandoned-checkout-policy.md) | PD-AC-1/2 (Proposed) | n/a in MVP (post-MVP visibility candidate) |
| 10 | Basic inventory synchronization | Packet-exists-Proposed (Task 013/013B) | 3 | [`../07-implementation-plan/task-013-inventory-sync-implementation-packet.md`](../07-implementation-plan/task-013-inventory-sync-implementation-packet.md) + 013B; [`../03-architecture/master-blueprint-inventory-fulfillment.md`](../03-architecture/master-blueprint-inventory-fulfillment.md) | DEC-010 (Accepted); **DEC-031 Layer 2**; RA-008 first-push guard | Full (`inventory`) |
| 11 | Bidirectional inventory behavior per accepted rules | Packet-exists-Proposed / research remaining (apply-mode MBQs) | 3 | Same as #10 | DEC-010/015; open MBQs | Full (`inventory`) |
| 12 | Fulfillment/tracking write-back (Mode 1) + fulfillment state model | Packet-exists-Proposed (Task 014, predates modes doc) + operating modes/state model designed this mission | 4 | [`./fulfillment-operating-modes.md`](./fulfillment-operating-modes.md); [`../07-implementation-plan/task-014-fulfillment-tracking-implementation-packet.md`](../07-implementation-plan/task-014-fulfillment-tracking-implementation-packet.md) (addendum needed per gap I-3) | DEC-011; D-014-2; **DEC-031 Layer 2**; scope correction noted in matrix row 12 | Full (`fulfillment`) |
| — | Fulfillment Mode 2 (exact bidirectional reconciliation, auto-validate) | Designed-this-mission-Proposed | 4 (required backend) / 5 (mode UI) | [`./fulfillment-operating-modes.md`](./fulfillment-operating-modes.md) §4/§10 | Mode-2 per-store enablement design (Proposed); Layer 2 | Full (`fulfillment`) |
| 13 | Scheduled synchronization (base crons merged; Area 6 triggers) | Merged-checkpoint (base) + Packet-exists-Proposed (Area 6) | 2+ | [`../07-implementation-plan/area-6-sync-triggers-implementation-packet.md`](../07-implementation-plan/area-6-sync-triggers-implementation-packet.md) | DEC-005/025 | Lite |
| 14 | Manual synchronization (operator-triggered) | Packet-exists-Proposed (Area 6) | 2+ (UI Wave 5) | Same Area 6 packet | DEC-005/025 | Lite |
| 15 | User-friendly job/sync logs (backend merged; UI remaining) | Merged-checkpoint (model) / Not-started (UI) | 5 (UI) | DEC-009; [`./screen-inventory-and-navigation-map.md`](./screen-inventory-and-navigation-map.md) | DEC-009/012/016 | Lite |
| 16 | Retry/recovery controls (JOB-ACTIONS backend) | Merged-Wave-1 (backend) / Not-started (UI) | 5 (UI) | [`../07-implementation-plan/task-job-actions-generic-core-packet.md`](../07-implementation-plan/task-job-actions-generic-core-packet.md) | DEC-009/034 | Lite |
| 17 | Duplicate prevention + idempotency controls | Merged-checkpoint (read/call safety, Layer 1 registry) / Not-started (mutation Layer 2) | 3–5 (per mutation domain) | [`../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md`](../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md) | DEC-006/009/031 | Lite (Layer 1) / Full (mutation domains) |
| 18 | Mapping/configuration screens (U3) | Not-started (backend models merged) | 5 | [`./screen-inventory-and-navigation-map.md`](./screen-inventory-and-navigation-map.md) | DEC-016 | Lite (store settings) / Full (location mapping) |
| 19 | Roles and permissions (SEC-1 backend; two-role product model) | Merged-Wave-1 (16/17/14 field guards) + two-role model designed this mission | 5 (roles UI) | [`./connector-roles-and-permissions.md`](./connector-roles-and-permissions.md); [`../07-implementation-plan/task-sec1-security-hardening-packet.md`](../07-implementation-plan/task-sec1-security-hardening-packet.md) | DEC-012/013/034; ruling `4988842625`; **two-role model (Proposed)** | Lite (roles ≠ editions per DEC-029) |
| 20 | Install/upgrade/configuration lifecycle + documentation | Merged-Wave-1 (LC-1 runtime-green) / guide remains | 6 (guide) | [`../03-architecture/module-lifecycle-uninstall-design.md`](../03-architecture/module-lifecycle-uninstall-design.md) | DEC-030 (Accepted) | Lite |
| — | Reconnect/backfill reconciliation (per-domain policy) | Designed-this-mission-Proposed (export side in the operating model; per-domain policy consolidation remains a named gap) | 2–5 (per domain) | [`./product-export-operating-model.md`](./product-export-operating-model.md) §10; gap row in [`../01-research/mvp-remaining-gap-inventory.md`](../01-research/mvp-remaining-gap-inventory.md) | Per-domain packets | Lite (read domains) / Full (mutation domains) |
| 21 | End-to-end test suite (full continuous run) | Merged-checkpoint/Wave-1 for existing domains (0/0/644 at build `34995642`) / Not-started (Waves 2–5 domains, CI) | 6 | [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md) row 21 | — | Both (edition-specific suites per DEC-029) |
| 22 | Dev-store UAT evidence (live Shopify) | Not-started (credentials not provisioned) | 6 | Matrix row 22; VAL-B2 | DEC-028 posture; human credential provisioning (program blocker 2) | Both |
| 23 | Release-readiness package | Partially complete (scaffolding only) | 6 | [`../08-release-readiness/`](../08-release-readiness/) | All matrix rows done + owner sign-off | Both |
| — | Premium UI (U1–U3 + PERF-1 performance criteria) | Not-started (prototypes + final design spec exist) | 5 | [`./ui-ux-final-design-spec.md`](./ui-ux-final-design-spec.md); [`../09-ui-prototype/`](../09-ui-prototype/) | DEC-016/033 | Lite (core screens) / Full (mutation-domain screens) |

Notes:
- Matrix item 6 spans two rows here (import vs export) because their statuses
  differ materially; both roll up to acceptance-matrix row 6.
- "Merged" statuses are [Fact] per the runtime-evidence log and Wave 1 merge
  record in [`../07-implementation-plan/mvp-program-state.md`](../07-implementation-plan/mvp-program-state.md).
- All "Designed-this-mission-Proposed" docs are Proposed and unaccepted;
  none authorizes implementation.

## MVP vs post-MVP boundary restatement

The boundary itself is unchanged from the accepted baseline: see
[`./mvp-scope.md`](./mvp-scope.md) (DEC-003 + DEC-007) for what is in, and
[`./non-mvp-and-later-phases.md`](./non-mvp-and-later-phases.md) for the
canonical out-list (unrestricted autonomous bidirectional catalog ownership,
customer export, accounting automation, App Store distribution, Markets/
metafields/SEO breadth, multi-store breadth, etc.).

Newly classified items from this mission (classification pointers only — the
underlying docs carry the proposals; no new decision is made here):

- **Abandoned-checkout workspace** — default remains *no import* of abandoned
  checkouts in MVP; an optional read-only per-store workspace is a **post-MVP
  visibility candidate** (PD-AC-1/2 in
  [`./abandoned-checkout-policy.md`](./abandoned-checkout-policy.md)).
- **COD courier integrations** (courier APIs, remittance reconciliation,
  cash-collection workflows) — **post-MVP**; MVP handles COD orders through
  the manual-gateway financial-evidence rules in
  [`./sales-order-lifecycle-and-confirmation-policy.md`](./sales-order-lifecycle-and-confirmation-policy.md).
- **Fulfillment Mode 2** (exact-conditions auto-validation of externally
  fulfilled deliveries) — **required MVP Wave 4 backend scope**, not optional,
  per [`./fulfillment-operating-modes.md`](./fulfillment-operating-modes.md)
  §10 and the product-owner direction. Both Mode 1 and Mode 2 backend behavior
  must be implemented, tested, and runtime-proven before Wave 4 closes (Wave 4
  may internally sequence Mode 1 before Mode 2). The Administrator selects the
  operating mode per store (Mode 1 default; Mode 2 explicit opt-in that fails
  closed to Mode 1 behavior). Wave 5 owns only the fulfillment/mode UI, never
  the Mode 2 backend.

Everything in the "Designed-this-mission-Proposed" and "Packet-exists-
Proposed" rows remains gated on its named decisions and waves; Wave 2 is the
next implementation wave and remains unauthorized until its own consolidated
Definition-of-Ready/preflight session
([`../07-implementation-plan/mvp-program-state.md`](../07-implementation-plan/mvp-program-state.md)).
