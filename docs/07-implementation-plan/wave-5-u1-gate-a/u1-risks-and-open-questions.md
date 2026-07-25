# Wave 5 U1 — Risks & Open Questions

> **Status: Gate A planning artifact — Docs-only. NOT accepted.** Produced
> 2026-07-23; **corrected 2026-07-23** to record the control-room dispositions
> (comment `5056513213`); **reconciled 2026-07-25** against the final integrated
> backend at `2583081f`. Consolidates the P0/P1/P2 decisions — **most resolved by
> the control room** (dispositions inline below) — plus standing risks. The one
> decision **still open** is **D-P0-3** (independent acceptance of the load-bearing
> Proposed product/UX contracts; the Wave-5 G5-1…G5-9 gates all remain unchecked).
>
> **Dependency state (present tense, 2026-07-25):** Wave 4 backend **merged**;
> SEC-2 **merged** (#196 closed); current-backend SEC-3 **merged** (**#197 still
> open**, narrowed); PERF-0 baseline **merged** (**#199 still open**, narrowed);
> pre-Wave-5 stabilization **merged** (PR #203). Gate A planning is not blocked;
> **U1 code remains unauthorized** — no longer for SEC-2 reasons, but because this
> re-anchored package has not been independently reviewed, D-P0-3 is unresolved,
> the G5 gates are unchecked, and the control room has not opened the U1 gate on a
> bound base SHA.

## P0 decisions (block U1 implementation start)

**D-P0-1 — Branch/dependency strategy. `ACCEPTED — PRECONDITION SATISFIED`
(control-room comment `5056513213`).** **Option A** is binding. Its waiting
condition (PR #189 merged) is **satisfied as of 2026-07-25**; there is **no**
stacked U1 implementation branch (Option B not authorized, and now moot). The
future U1 implementation branches from the exact tip the control room binds when it
opens the U1 gate — **not** automatically from `2583081f`. (See
`u1-branch-dependency-strategy.md`.)

**D-P0-2 — SEC-2 sequencing. `RESOLVED — SEC-2-FIRST; CONDITION SATISFIED`
(control-room comment `5056513213`, binding).** SEC-2 **is** accepted, implemented,
independently reviewed and **merged**; issue #196 is **closed as completed**. There
is **no** parallel four-internal-group path. U1 customer-facing UI **visibility**
gates on the two SEC-2 roles (Connector User = the now-existing
`group_shopify_connector_user`; Connector Administrator = the existing
`group_shopify_connector_admin`); the four internal capability groups remain the
**server-side** authorization primitives the two roles resolve to — verified
unchanged at `2583081f`. Tests prove both layers (two-role visibility + direct-RPC
server denial). (See `u1-sec2-preflight-ruling.md`; exact XML IDs in the contract
inventory §8.1.)

**D-P0-4 — SEC-3 obligation for any new durable U1 model. `NEW — OPEN
REQUIREMENT` (2026-07-25 reconciliation; issue #197 open).** Current-backend SEC-3
is merged, but **#197 remains open** for future Wave-5-added surfaces and external
multi-user UAT / RC confirmation. Every **new durable store-scoped U1 model or
connector-to-connector relation** the U1 implementation might introduce must be
added to the inventory-driven SEC-3 guard, carry a stored related `company_id`,
declare its parent scope relations, receive a fail-closed global company rule, and
be covered by the SEC-3 matrix tests — acceptance **A23**, contract §8.2. U1's own
design introduces no new durable model (only a non-store-scoped `TransientModel`
wizard), so the expected outcome is "no new SEC-3 entry required" — **proven, not
assumed**. **#197 must not be marked complete.**

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
architecture-review log (**AR-083**, renumbered from AR-079 on 2026-07-25 — the merge brought a different, already-merged AR-079 onto the branch). No separate `_ui` addon.

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

**D-P2-7 — Review-reason vocabulary count. `RECONCILED` (2026-07-25).** The
evidence `review_reason` selection is **21 values**, not the 20 recorded at the
historical `2d9cff0` snapshot: the Wave 4 Tier-1 correction (Theme H) added
`external_fulfillment_observed` ("External Fulfillment Observed"), written as the
baseline reason when an observed external fulfillment's origin **is** confirmed
(`models/shopify_connector_fulfillment_inbound.py:192`), as distinct from
`origin_unconfirmed`. The U1 copy deck must map **21** reasons. (Contract §5.4 /
§0.1 Δ1.)

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

**D-P2-6 — Status-layer & badge taxonomy. `RESET` (control-room synthesis-reset
ruling, PR #194 comment `5058042330`; independent review `5057796514`);
**re-verified unchanged at `2583081f` on 2026-07-25** (contract §0.1 Δ7).** A
confirmed material P2 (UX/IA §8 mapped `display_status_*` to A5 and asserted a
phantom A2 badge) was re-derived from the exact Wave 4 source and reset. The single
**canonical Authoritative status-source & badge matrix** now lives in
`u1-backend-ui-contract-inventory.md` §12; every dependent doc/prototype links to it.
Bindings (originally source-verified at `2d9cff0` *(historical)*; **re-verified unchanged at `2583081f` on 2026-07-25**): **A7** = `display_status_*`
(`Fulfillment.displayStatus`, display-only, never a carrier milestone); **A5** carrier
milestones are represented **only** from `delivered_inconsistency` + parsed
`tracking_snapshot`, never from A7, and never as a full A5 enum timeline (deferred —
no backing enum); **A2 `FulfillmentOrderStatus`** = **DEFERRED — BACKEND READ SEAM NOT
AVAILABLE** (no field; no badge); **A4** = `fulfillment_status_*` (automation authority
+ display); A1 available only indirectly via
`order_binding_id.shopify_fulfillment_status_snapshot`; A3/A6 outside U1. Layers are
never merged; acceptance A22 verifies label/icon/severity correctness per layer.

## Standing risks

- **CV-013 (#185) open/critical** — live fulfillment mutation qualification unproven
  (`fulfillment_staff_permission` NOT_PROVEN); U1 must surface this and never claim
  live mutation is proven; blocks release/UAT.
- **All live-Shopify validation is DEFERRED** until the Wave 5 implementation
  candidate is complete and frozen (2026-07-25 product-owner sequencing ruling).
  **Gate D, CV-013 (#185), provisioning (#200), external UAT and release readiness
  are open and unclaimed.** The deferral is **not a waiver**: any candidate-owned
  P0/P1 found later must still be corrected before external UAT or release
  acceptance. No U1 document may present any of these as complete.
- **SEC-3 / issue #197 remains OPEN** — current-backend SEC-3 is merged, but #197 is
  narrowed to future Wave-5-added surfaces and external multi-user UAT / RC
  confirmation. See **D-P0-4** and acceptance **A23**. Two second-order U1 risks
  follow from the shipped design: (a) **quarantined rows are invisible to every
  interactive read shape**, so no U1 count or facet is a complete count — U1 must
  never present one as authoritative; (b) U1 must never attempt to unhide, re-home
  or work around a quarantine, nor surface `sec3_scope_quarantined` as an actionable
  control. (Contract §8.2.)
- **PERF-0 / issue #199 remains OPEN** — the admission-path and local-ledger
  baseline is merged, but the per-record reconciliation **handlers** perform Shopify
  reads and remain unmeasured, and no release thresholds are accepted. **Every
  PERF-0 number is baseline-only and must never be restated as a performance
  guarantee, budget or SLA** in any U1 document, view copy, or acceptance claim.
  The Wave-5 **G5-4 (PERF-1 budgets)** gate is unchecked.
- **External-multiprocessing / concurrency campaign** — a release/UAT gate, not
  U1's, not to be represented as passed. The `test_real_process_death_harness` and
  the browser navigation tour are **runtime pending** and are **not** claimed as
  proven by this or any U1 Gate-A document.
- **Webhooks forbidden in Wave 4** — U1 must not imply webhook-driven inbound; the
  sources are `odoo_event`/`scheduled_sync`/`reconciliation`/`manual_sync`.
- **Operator-surface runtime evidence still does not exist.** *(Historical,
  superseded: this risk previously read "No Task-014 validation-results file yet".
  That file **is** now on the integration tip — it arrived with the Wave 4 merge and
  records the **backend** campaign.)* There is still **no U1 operator-surface runtime
  record**; the future U1 implementation batch must generate its own, including the
  premium-UI browser/render evidence, which this docs-only reconciliation supplies
  none of.
- **A5 delivered-inconsistency seams are declared but data-inert — re-verified at
  `2583081f`** —
  the `delivered_inconsistency` Boolean field and the
  `review_reason='delivered_not_validated'` selection value both **exist** on the
  evidence model but are **never written by any code path** at the current
  integrated implementation (re-grepped at `2583081f`, 2026-07-25).
  The badge/case is therefore contract-ready but currently unpopulated: U1 renders it
  when the backend sets it and must **never** synthesize the A5 case from the A7
  `display_status_*` fields. Populating these seams is a **backend-completeness item
  (not U1's to implement)** — flagged for the control room / a future Wave-4 backend
  follow-up, and captured in the canonical §12 matrix invariants.

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
- **OQ-4 (NEW, 2026-07-25) — duplicate `ir.rule` XML IDs in
  `shopify_connector_fulfillment`. `[Open question — for the control room; NOT a U1
  defect and NOT fixed here]`.** `fulfillment_inbound_evidence_company_rule` and
  `fulfillment_inbound_evidence_line_company_rule` are each declared **twice inside
  the same module** — in `security/shopify_connector_fulfillment_security.xml`
  (`noupdate="1"`, the older order-binding-/sale-line-derived domains) and again in
  `security/shopify_connector_fulfillment_company_rules.xml` (`noupdate="0"`, the
  SEC-3 store-company + quarantine domains). The manifest loads the former first.
  `[Inference]` the later declaration updates the same `ir.model.data` row and
  **replaces** the earlier `domain_force` rather than adding a second global rule,
  so the evidence and evidence-line models end up with the store-company +
  quarantine domain **only**. (The binding is unaffected — its two files use
  different XML IDs, so all three binding rules coexist, with
  `fulfillment_binding_picking_company_rule` duplicating
  `fulfillment_binding_company_rule`'s domain.) **U1 consequence:** the A4/A23
  visibility tests must assert against the **effective** rule set observed at
  runtime, never against the union of the two declarations. **Raised for the control
  room / the SEC-3 (#197) workstream to confirm or correct in the backend — this
  docs-only reconciliation changes no security file and proposes no code change.**
  Recorded in the contract inventory §8.2.
- **OQ-5 (NEW, 2026-07-25) — group label vs role concept.** The shipped SEC-2 group
  `name` strings are `User` and `Administrator` **within the `Shopify Connector`
  privilege**, not the literal "Connector User" / "Connector Administrator" used as
  role concepts throughout this package. The U1 copy deck must decide, explicitly,
  which string each surface shows — and must never rename a group to match a
  document. (Contract §8.1.)
