# DEC-033 — MVP Wave 0 Reconciliation and Dependency Closure

- **Status:** Accepted by Claude control room, with minor corrections (Wave 1 internal sub-stage note and hard-stop 11 rewording, applied on this same PR). Control-room review: Claude MVP Wave 0 macro-review, PR #169, 2026-07-15. Accepted PR head: recorded in the control-room review comment on PR #169 and in the Wave 0 closure comment on issue #167 (this record cannot state its own resulting commit SHA).
- **Date:** 2026-07-15 (proposed); accepted 2026-07-15.
- **Decision owner:** Claude control room under DEC-032; product owner for any commercial override.
- **Scope:** Program reconciliation and dependency ordering only. No addon code is authorized by this record.
- **Related:** DEC-003, DEC-027, DEC-028, DEC-029, DEC-030, DEC-031, issue #165, `mvp-completion-program.md`, Task 012/014/015/015B packets.

## Context

Wave 0 was opened to reconcile six explicitly recorded questions and two known research gaps before implementation waves proceed. The protected checkpoint and live references were verified first. The research refresh is recorded in `../01-research/wave-0-roles-permissions-and-fulfillment-scope-refresh.md`.

## Proposed decision

### 1. Product export remains in the MVP

**[Decision proposed]** Do not amend or narrow DEC-003. Controlled product export/update (Task 015) and basic product media export (Task 015B) remain part of the frozen MVP and are assigned to Wave 5 after Wave 3 has delivered accepted DEC-031 Layer 2.

- This is plan reconciliation with an existing accepted scope, not new scope.
- Task 015/015B retain their own proposed packets, safety gates, module boundary, tests, Odoo.sh evidence, and dev-store mutation evidence.
- Wave 5 may be executed in reviewable internal stages, but it remains one macro-wave gate into `mvp/program-integration`.

### 2. SRR-03 remains OPEN and is not DEC-031 Layer 2

**[Decision proposed]** Reconcile every conflicting statement to the strict evidence-backed status:

- SRR-03 remains **OPEN**. Issue #165 and the exact-head checkpoint validation are authoritative.
- DEC-031 Layer 2 is a separate durable mutation-ownership/reconciliation gate. Task 012 performs Shopify reads and local Odoo writes; it must register its own `remote_read_replay_safe` policy and does not require Layer 2.
- Parallel Task 012 development is allowed only after Wave 1's code prerequisites are present.
- No Task 012 wave PR may merge, be enabled, or receive live Shopify validation until SRR-03's accepted closure criteria are proven and recorded.
- Wave 1 gains an explicit SRR-03 closure sub-gate: validate the checkpointed CORE-R2 disconnect/in-flight behavior against the accepted criteria; correct an owned core defect if required and within the Wave 1 core allowlist; otherwise trigger hard-stop 6/10. Wave 2 cannot complete while the risk remains open.

This replaces stale Task 012 wording that simultaneously said “SRR-03 CLOSED” and “SRR-03 OPEN.”

### 3. PR #150 and PR #151

**[Decision proposed]** Their code is already checkpoint-integrated, so their GitHub PR entities should be closed as **superseded by the checkpoint/integration-staging path**, never marked individually merged.

- Sol does not edit or close either protected PR.
- After this decision is accepted, Claude control room or the product owner may add one administrative explanation and close them.
- Their branches and commits remain intact as historical evidence.

### 4. DEC-027 through DEC-030 timing

**[Decision proposed]**

| Record | Wave 0 disposition | Hard prerequisite |
| --- | --- | --- |
| DEC-027 — pilot/private-customer count | Explicitly defer | Before onboarding a second simultaneous production private customer or proposing public distribution; not required for a single dev-store MVP/UAT. |
| DEC-028 — credential/PCD posture | Accept in Wave 0 | Before any real-customer PII dev-store UAT or production deployment. Synthetic/fixture-only implementation tests may proceed first. |
| DEC-029 — Lite/Full packaging | Accept in Wave 0 | Before Wave 3 creates write-back modules and before Wave 5 creates the separate product-export module/UI. No pricing, billing, or licensing is decided. |
| DEC-030 — lifecycle/uninstall | Accept in Wave 0 | Task LC-1 must implement it in Wave 1 and be runtime-green before Wave 2. |

The control room must apply the corresponding status/acceptance notes to DEC-028/029/030 before declaring Wave 0 complete. DEC-027 remains Proposed/Deferred with the revisit condition above.

### 5. Stray branch and empty requirements file

**[Decision proposed]**

- Leave `claude/task-012-decision-closure-mb88sn` untouched. Do not branch from, merge, delete, or cite it. Revisit only on explicit product-owner cleanup authorization.
- Leave the inert, pre-existing `addons/requirements.txt` untouched. Revisit only if a real dependency requirement or an explicit repository-cleanup instruction appears.

### 6. Research-gap closure

**[Decision proposed]**

- Roles/permissions research is sufficient for MVP: the shared four-group hierarchy stands; SEC-1 owns server-side hardening and dedicated effective-permission tests; Wave 5 owns the explanatory/assignment UI.
- Accept Task 014 D-014-2: `read_fulfillments` is a valid FulfillmentService scope but the wrong readiness proof for FulfillmentOrder. Wave 4 replaces it with `read_merchant_managed_fulfillment_orders` and conditionally requires `write_merchant_managed_fulfillment_orders`.

## Consequences

- Wave 1 scope becomes CORE-R1 + SEC-1 + LC-1 + the SRR-03 closure gate, all within the existing core foundation boundary.
- Wave 2 may be developed after Wave 1 but cannot complete or merge while SRR-03 remains open.
- Wave 5 completes DEC-003 instead of silently shipping an import-only product MVP.
- Wave 6 requires genuine DEC-028 deployment evidence before real PII UAT.
- No protected ref, addon file, PR #150/#151, hazardous branch, or requirements file is changed by Wave 0.

## Rejected or deferred alternatives

- **Defer product export by silently narrowing the MVP:** rejected; conflicts with DEC-003 and RA-001.
- **Treat DEC-031 Layer 2 as required for read-only order import:** rejected for Task 012; DEC-031 explicitly reserves Layer 2 for Shopify mutation domains.
- **Treat SRR-03 as closed because Layer 1 is green:** rejected; issue #165 and the checkpoint validation explicitly keep it open.
- **Duplicate domain-local security groups:** rejected as unnecessary duplication of the accepted shared-core role substrate.
- **Delete the hazardous branch now:** deferred; no authorization and no program benefit.
- **Request broad assigned/third-party fulfillment scopes:** deferred/out of MVP; the accepted Phase-1 flow is merchant-managed.

## Acceptance effect

**Accepted 2026-07-15 (Claude control-room Wave 0 review, PR #169).** This record is now binding: SRR-03 remains OPEN with the Wave 1 closure sub-gate in force; DEC-028, DEC-029, and DEC-030 are Accepted (status notes applied to each record in this same commit); DEC-027 remains Proposed/Deferred with its stated revisit condition; Task 015/015B are confirmed Wave 5 scope after accepted Layer 2; PR #150/#151 administrative closure as superseded is authorized to proceed after this PR merges, per the control-room review; the hazardous branch and the empty requirements file remain untouched; no addon code or protected reference is authorized or changed by this record. Wave 1 is authorized to begin only after this PR merges into `mvp/program-integration`.
