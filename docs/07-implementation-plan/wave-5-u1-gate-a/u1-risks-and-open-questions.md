# Wave 5 U1 — Risks & Open Questions

> **Status: Gate A planning artifact — Docs-only. NOT accepted.** Produced
> 2026-07-23; **corrected 2026-07-23** to record the control-room dispositions
> (comment `5056513213`). Consolidates the P0/P1/P2 decisions — **most now resolved
> by the control room** (dispositions inline below) — plus standing risks. The one
> item **still open** is **D-P0-3** (independent acceptance of the load-bearing
> Proposed product/UX contracts; the Wave-5 G5-1…G5-9 gates all remain unchecked).
> Gate A (this planning) is not blocked; U1 *code* is (SEC-2-first).

## P0 decisions (block U1 implementation start)

**D-P0-1 — Branch/dependency strategy. `ACCEPTED` (control-room comment
`5056513213`).** **Option A** is binding: wait for PR #189 to merge, then branch U1
from the new integration tip. There is **no** stacked U1 implementation branch
(Option B not authorized). (See `u1-branch-dependency-strategy.md`.)

**D-P0-2 — SEC-2 sequencing. `RESOLVED — SEC-2-FIRST` (control-room comment
`5056513213`, binding).** SEC-2 must be accepted, implemented, independently
reviewed, Odoo.sh runtime-green, and **merged** before U1 production implementation.
There is **no** parallel four-internal-group path. U1 customer-facing UI
**visibility** gates on the two SEC-2 roles (Connector User = new
`group_shopify_connector_user`; Connector Administrator = existing
`group_shopify_connector_admin`); the four internal capability groups remain the
**server-side** authorization primitives the two roles resolve to. Tests prove both
layers (two-role visibility + direct-RPC server denial). (See
`u1-sec2-preflight-ruling.md`.)

**D-P0-3 — Load-bearing product acceptances. `NOT YET ACCEPTED` (control-room
comment `5056513213`).** The load-bearing product/UX contracts U1 depends on remain
**Proposed — not accepted** and must be independently accepted before U1
implementation: `premium-ux-master-specification.md` (G5-1),
`connector-roles-and-permissions.md` (two-role direction, G5-2),
`fulfillment-operating-modes.md`, `shopify-fulfillment-status-model.md`, the SEC-2
packet, the fulfillment-mode + COD UAT matrices, and the
prototype-fidelity/design-system acceptance set (G5-3). The Wave 4 **backend** is
accepted/runtime-green; the **UX contracts** and the **two-role direction** are
**not**. The exact load-bearing subset and the accepted/proposed/pending split is
enumerated in the **Gate-A prerequisite & status table** (package `README.md` §4).
This control-room comment accepts the **SEC-2-first sequencing decision only** — it
does **not** accept the still-Proposed product/UX documents, and the Wave-5 G5 gates
(G5-1…G5-9) all remain **unchecked**.

## P1 decisions (resolve before or during U1 implementation)

**D-P1-1 — UI phase numbering reconciliation. `ACCEPTED` (comment `5056513213`).**
The older `ui-implementation-phases-packet.md` numbers U1 = core surface (delivered
by the merged **U0**), U2 = domain (incl. fulfillment) workspaces. This task's "U1 =
fulfillment operator experience" maps to that packet's **U2 fulfillment slice** +
wave-5 DoR §1.2/§5.6. The control room ratified the re-based numbering and the
**fresh** U1 locked prompt (`u1-locked-implementation-prompt.md`); the packet's §6
U1 prompt is **retired as superseded** and must not be reused.

**D-P1-2 — Module-placement ADR. `ACCEPTED` (comment `5056513213`).** U1 UI lives
inside `shopify_connector_fulfillment` (PD-2, DEC-016(A), RA-013), recorded in the
architecture-review log (AR-079). No separate `_ui` addon.

**D-P1-3 — SEC-2 fulfillment-ACL scope gap. `RESOLVED` (comment `5056513213`).**
Final customer UI uses the two SEC-2 roles; Wave 4 server methods retain the four
internal groups as implied capability primitives. **U1 does not rewrite Wave 4
backend security**, and fulfillment continues relying on the four internal groups by
design (no SEC-2 fulfillment edit forced by U1).

**D-P1-4 — Mode-2 ↔ inventory location-mapping boundary. `ACCEPTED` (comment
`5056513213`).** U1 only **displays** existing location/readiness/review outcomes
(the `location_unmapped` review reason + readiness checks); it introduces **no**
fulfillment→inventory addon dependency and **no** new mapping business logic.

**D-P1-5 — Confirmation wizard as `TransientModel`. `ACCEPTED CONDITIONALLY`
(comment `5056513213`).** Use a small `TransientModel`, but **frozen as
display-and-delegate only** under the boundary in
`u1-modular-architecture-recommendation.md` §3.1 (no eligibility/blocker/
review-required decision, no target-mode choice, no argument alteration, no Job
creation, no mutation, no Shopify call; informational counts are bounded, ACL-safe,
and labelled non-authoritative). Source guards + negative tests enforce this.

**D-P1-6 — Browser-evidence posture for U1. `REQUIRED BEFORE MERGE` (comment
`5056513213`).** U1 is a premium UI gate: browser/render evidence (driven
walkthrough, screenshot set, browser-level visibility/action, accessibility/render,
responsive-width, RTL) is **required before U1 merge** and is **not** auto-inherited
from U0's deferments. A product-owner deferment of any browser class may be
requested **only after** a concrete execution attempt, exact environment-limitation
evidence, and a **separate control-room ruling**; a deferred class is never marked
"passed".

## P2 decisions (material, resolve pragmatically)

**D-P2-1 — Doc↔code vocabulary reconciliation. `CODE AUTHORITATIVE` (comment
`5056513213`).** Product docs use superseded values (`external_service`/
`carrier_event_only`, `over_fulfillment`, `under_review`/`auto_matched`/`rejected`)
not present in code. U1 binds to the **code** values; the copy deck maps them. Per
this correction, `fulfillment-operating-modes.md` and `shopify-fulfillment-status-
model.md` now carry a **non-destructive superseded-vocabulary note + section-anchored
pending-edit table** (the docs stay **Proposed**; the section values are left
unchanged pending a separate product-doc reconciliation). Logged as documentation
**TD-003**. The over-fulfillment case renders `quantity_overrun` (evidence) and
persists `ambiguous_match` (core `manual_review_subreason`).

**D-P2-2 — Tracking-timeline surface. `ACCEPTED — NATIVE` (comment `5056513213`).**
Use native Odoo views (a form section over `state_snapshot`/`tracking_snapshot`);
PD-7 excludes fulfillment from Owl. No production Owl surface.

**D-P2-3 — Mode-switch history model. `ACCEPTED — NO HISTORY MODEL IN U1` (comment
`5056513213`).** U1 uses the existing scalar `fulfillment_last_mode_switch_*` fields
and the Job/JobLog lineage; **no** mode-switch history model is created in U1.

**D-P2-4 — Dark-mode/theme parity. `OUTSIDE U1` (comment `5056513213`).** U0 is
light-only; dark-mode parity remains outside U1 unless separately added to accepted
scope.

**D-P2-5 — Consequences read-model. `SEPARATE BACKEND TASK` (comment `5056513213`).**
The mode-switch consequences display is composed by U1 from bounded, ACL-safe,
**non-authoritative** reads only (display-and-delegate). An **authoritative dynamic
preflight** read-model is a **separate backend task**, recorded for later — never
implemented in U1.

## Standing risks

- **CV-013 (#185) open/critical** — live fulfillment mutation qualification unproven
  (`fulfillment_staff_permission` NOT_PROVEN); U1 must surface this and never claim
  live mutation is proven; blocks release/UAT.
- **Nine-process concurrency campaign** `DEFERRED` (PR #189) — a release/UAT gate,
  not U1's, not to be represented as passed.
- **Webhooks forbidden in Wave 4** — U1 must not imply webhook-driven inbound; the
  sources are `odoo_event`/`scheduled_sync`/`reconciliation`/`manual_sync`.
- **No Task-014 validation-results file yet** — no runtime record of operator
  surfaces; U1 acceptance must generate its own runtime evidence once Wave 4 merges.

## Open questions (non-blocking, track)

- OQ-1: Whether U1 should pick up any of U0's deferred browser/lifecycle evidence
  for the shared surfaces it extends. *(Largely resolved by D-P1-6: U1's own
  surfaces require browser/render evidence before merge; the same
  required-then-deferrable-only-after-a-concrete-attempt posture applies to any U0
  shared surface U1 extends — never auto-deferred.)*
- OQ-2: Exact XML/menu/view IDs (MBQ-03 open) — U1 proposes IDs following U0's
  scheme; final scheme is a copy/ID decision.
- OQ-3: Whether Mode-2 enablement UI should show an inventory-domain prerequisite
  banner (tied to D-P1-4).
