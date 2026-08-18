# PR #206 architecture assurance packet

**Status:** dated control-room evidence packet; not release sign-off

**Prepared:** 2026-08-18

**Exact implementation head:** `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8`

**Exact tree:** `7da2d8c678eeabd0325c6c7c892a019bcc657cee`

**Pull request / branch:** PR #206 / `codex/ui-restructure-implementation`

**Odoo.sh:** exact-head build `36553922` reported successful. The exact-head
database is fresh; its URL is retained in the control-room runtime ledger and
is intentionally not duplicated here because this writer did not receive the
URL. No Shopify secret is stored in this packet.

**Shopify identity:** the only authorized development shop is
`testin-lzhbzhtc.myshopify.com`. `mqiu21-yz.myshopify.com` is historical and
must not be used.

## Provisional decision

**NOT ASSURED — CORE ARCHITECTURE GAPS.** This is not a final release
decision. The Odoo-side job, lease, mutation-attempt and recovery substrate is
substantial, but production webhooks are absent and no live Shopify mutation
has been proven on this exact head. Product/inventory UI UAT and
order/fulfillment UI UAT are both blocked.

The current state is best described as a controlled-refactor candidate: retain
the durable core and add a modular webhook/reconciliation ingress plus
large-volume synchronization capability. Do not merge or mark PR #206 ready.

## Plain answers

| Question | Exact-head answer |
| --- | --- |
| Is the underlying architecture sound? | The durable Odoo-side substrate is promising and modular; the requested hybrid inbound architecture is incomplete. |
| Does it function live against Shopify? | Not proven. No live Shopify mutation or fresh remote read is recorded for this exact head. |
| Is synchronization near-real-time where required? | No. Current inbound work is scan/reconciliation based. |
| Are webhooks and reconciliation both reliable? | Reconciliation code exists; webhooks do not exist, so the combined capability is not available or tested. |
| Can it recover safely from failures? | Code-level recovery controls are present; live transport, timeout and crash recovery remain unproven. |
| Can it scale to the intended workload? | Not established. Product/order scan caps and absent Bulk Operations leave large-volume capacity unresolved. |
| Are permissions secure? | ACL/company/boundary controls are substantial; exact-head external multi-user runtime evidence remains open. |
| Is the UX understandable? | The organization is coherent, but setup direction copy and webhook status currently overstate or under-specify behavior. |
| What remains before production? | Webhook capability, live Gates A–H, representative performance evidence, exact-head independent review, and UAT. |
| Build, refactor, or replace? | Controlled refactor: preserve core job/mutation/recovery substrate; add bounded ingress and scale paths. |

## Evidence classification

- **[Official]** — statement from an official Odoo or Shopify source.
- **[Code fact]** — behavior observed in the exact checkout.
- **[Inference]** — consequence of code facts and the requested contract.
- **[Recommendation]** — proposed correction or acceptance condition.
- **[Decision]** — control-room release/UAT ruling.
- **[Not proven]** — no live, exact-head or independent evidence exists.

## Contents

- [Production-path inventory](./production-path-inventory.md)
- [Synchronization ownership matrix](./synchronization-ownership-matrix.md)
- [Official conformance matrix](./official-conformance-matrix.md)
- [Webhook and reconciliation decision](./webhook-reconciliation-decision.md)
- [Backend-first test plan](./backend-first-test-plan.md)
- [Live backend evidence ledger](./live-backend-evidence-ledger.md)
- [Scalability report](./scalability-report.md)
- [UX and operability review](./ux-operability-review.md)
- [Defect register](./defect-register.md)
- [Residual-risk register](./residual-risk-register.md)
- [Final UAT readiness decision](./final-uat-readiness-decision.md)
- [Handoff](./handoff.md)

## Current gate state

| Gate | State on this packet | Reason |
| --- | --- | --- |
| A Authentication and identity | **Not live-passed** | No exact-head credential exchange and identity evidence in the ledger. |
| B Read connectivity | **Not live-passed** | No exact-head fresh remote reads recorded. |
| C Product lifecycle | **Not live-passed** | No exact-head remote create/update/read-back evidence. |
| D Inventory lifecycle | **Not live-passed** | No exact-head remote InventoryItem/location/CAS evidence. |
| E Webhook delivery | **Blocked by implementation** | No controller, subscription or delivery pipeline exists. |
| F Order/fulfillment | **Not live-passed** | No exact-head order/fulfillment remote evidence. |
| G Failure/recovery | **Not live-passed** | Unit/runtime tests do not prove live transport outcomes. |
| H Security | **Not live-passed** | Code controls exist; exact-head dedicated-user runtime proof is absent. |

## Assignment and review ownership

- **Luna Max Agent A:** architecture and production-path audit; this packet
  records its read-only findings. It did not author addon changes.
- **Luna Max Agent B:** live backend validation and evidence ledger. It must
  use only `testin-lzhbzhtc.myshopify.com` and must not convert jobs or HTTP
  200 responses into remote-success claims.
- **SOL Medium Reviewer:** independent review of this packet and every future
  webhook/scale correction. No worker may be the sole reviewer of its own
  implementation.
