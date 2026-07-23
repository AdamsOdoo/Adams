# Wave 5 U1 — Risks & Open Questions

> **Status: Gate A planning artifact — Docs-only. NOT accepted.** Produced
> 2026-07-23. Consolidates the P0/P1/P2 decisions the control room must resolve
> before U1 **implementation**, plus standing risks. Gate A (this planning) is not
> blocked by these; U1 *code* is.

## P0 decisions (block U1 implementation start)

**D-P0-1 — Branch/dependency strategy.** Recommendation (Option A): wait for PR
#189 to merge, then branch U1 from the new integration tip. U1 cannot install or
runtime-test without Wave 4 code; a stacked branch (Option B) entangles diffs and
risks a rebase if #189 is corrected. **Decision:** confirm Option A, or authorize
Option B with accepted retarget/rebase cost. (See `u1-branch-dependency-strategy.md`.)

**D-P0-2 — SEC-2 sequencing.** The wave-5 DoR §3 binds **SEC-2 → PERF-1 → U1** and
rejected U1-first. SEC-2 (Option M-A) is additive and keeps the four internal
groups, so a U1 that gates on those four capability groups is order-independent.
**Decision:** either (a) land SEC-2 before U1 per the DoR, or (b) explicitly
authorize U1 to gate on the four internal capability groups in parallel with
SEC-2. Not a definitional hard stop (SEC-2 is fully defined). (See
`u1-sec2-preflight-ruling.md`.)

**D-P0-3 — Load-bearing product acceptances.** Nearly every product/UX doc U1
depends on is **Proposed — not accepted**: `fulfillment-operating-modes.md`,
`shopify-fulfillment-status-model.md`, `connector-roles-and-permissions.md`, the
UAT matrices, `premium-ux-master-specification.md` (wave-5 gate **G5-1**), and
DEC-038's file banner. The Wave 4 **backend** is accepted/runtime-green, but the
**UX contracts** and the **two-role direction** are not yet control-room accepted.
**Decision:** accept G5-1 (master spec) + the roles/two-role direction + the modes/
status UX contracts, or U1 builds against un-ratified specs. (Confirms wave-5 DoR
gates before the U1 gate opens.)

## P1 decisions (resolve before or during U1 implementation)

**D-P1-1 — UI phase numbering reconciliation.** The older
`ui-implementation-phases-packet.md` numbers U1 = core surface (delivered by the
merged **U0**), U2 = domain (incl. fulfillment) workspaces. This task's "U1 =
fulfillment operator experience" maps to that packet's **U2 fulfillment slice** +
wave-5 DoR §1.2/§5.6. The packet's §6 U1 locked prompt is **not reusable**; this
Gate A supplies a fresh one. **Decision:** ratify the re-based numbering and the
fresh U1 locked prompt (`u1-locked-implementation-prompt.md`); optionally annotate
the packet as superseded.

**D-P1-2 — Module-placement ADR.** Recommendation: U1 UI lives inside
`shopify_connector_fulfillment` (PD-2, DEC-016(A), RA-013). This overrides no
accepted decision but should be recorded in the architecture-review log as an AR
row (done: AR entry appended by this Gate A session). **Decision:** confirm the AR.

**D-P1-3 — SEC-2 fulfillment-ACL scope gap.** SEC-2's allowed-files list predates
Wave 4 and excludes fulfillment. Under Option M-A this is harmless (the four groups
persist), but if the two-role model should be reflected in fulfillment security
wording, SEC-2's scope must be extended. **Decision:** confirm fulfillment keeps
relying on the four internal groups (no SEC-2 fulfillment edit), or extend SEC-2.

**D-P1-4 — Mode-2 ↔ inventory location-mapping boundary.** `fulfillment-operating-
modes.md` §8/§12 asks whether enabling Mode 2 should hard-require the inventory
domain (location mapping, condition 8), given fulfillment's no-inventory-dependency
rule. **Decision (backend-boundary, not U1's to make):** U1 only surfaces the
`location_unmapped` review reason + readiness checks; it must not create a new
coupling.

**D-P1-5 — Confirmation wizard as `TransientModel`.** Recommendation: a
display-and-delegate wizard (like U0's cancel/mutation wizards) renders the
consequences and calls the accepted mode-switch actions. **Decision:** confirm this
is not "UI-owned business logic" (it computes no decision, mutates nothing), or
require the weaker static `confirm=` button (which cannot show dynamic consequences).

**D-P1-6 — Browser-evidence posture for U1.** U0 deferred HOOT/tours/driven
walkthrough/screenshots/browser-a11y "BY PRODUCT OWNER — NOT PROVEN". U1 has the
same environment constraints. **Decision:** whether U1 must execute these (and in
which environment) or inherit the same deferment; U1 must never mark a deferred
class passed.

## P2 decisions (material, resolve pragmatically)

**D-P2-1 — Doc↔code vocabulary reconciliation.** Product docs use superseded values
(`external_service`/`carrier_event_only`, `over_fulfillment`, `under_review`/
`auto_matched`/`rejected`) not present in code. U1 binds to **code** values; the
copy deck maps them; the product docs should carry a "superseded vocabulary" note.
(Logged as documentation TD — see technical-debt register.) The over-fulfillment
case renders `quantity_overrun` (evidence) and persists `ambiguous_match` (core job).

**D-P2-2 — Tracking-timeline surface.** Owl vs native for the carrier-milestone
timeline is not control-room-ruled for the gap-closure surfaces. Recommendation:
native form section over `state_snapshot`/`tracking_snapshot` (PD-7 excludes
fulfillment from Owl). **Decision:** confirm native.

**D-P2-3 — Mode-switch history model.** Only scalar `fulfillment_last_mode_switch_*`
fields exist; a per-switch history requires either surfacing the mode-switch-scan
job log (U1 scope) or a new backend history model (out of U1 scope). Recommendation:
surface scalars + job log in U1; defer any history model.

**D-P2-4 — Dark-mode/theme parity.** U0 is light-only (single committed look). U1
inherits this; a theme-parity decision is deferred.

**D-P2-5 — Consequences read-model.** The mode-switch consequences summary is
composed by U1 from bounded ACL-safe reads. If a single accepted read-only aggregate
endpoint is later preferred, it belongs to a separate backend task — not U1.

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
  for the shared surfaces it extends.
- OQ-2: Exact XML/menu/view IDs (MBQ-03 open) — U1 proposes IDs following U0's
  scheme; final scheme is a copy/ID decision.
- OQ-3: Whether Mode-2 enablement UI should show an inventory-domain prerequisite
  banner (tied to D-P1-4).
