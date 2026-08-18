# PR #206 architecture assurance packet

**Status:** dated control-room evidence packet; not release sign-off

**Prepared:** 2026-08-18

**Current qualification head:** `2b8108b9b69ca70b20a3b705a82e167ea13bb98a`

**Current tree:** `522bcd01035cb44d241ff56c3deff3de272701c2`

**Pull request / branch:** PR #206 / `codex/ui-restructure-implementation`

**Odoo.sh:** exact-head qualification is blocked: permitted cloud-browser
access was denied by automatic review, so no exact-head build/database or live
Shopify qualification may be claimed. No Shopify secret is stored in this
packet.

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
the durable core and extend the bounded W1/W2 webhook foundation with the
remaining domain ingress and large-volume synchronization capability. Do not
merge or mark PR #206 ready.

Actions run `32144921687` completed failure after approximately 48 minutes.
Fresh and warm each reported `0 failed, 2 error(s)` from an unauthorized-admin
actor fixture and a non-ISO webhook timestamp fixture. The W2-only schema
install reached tests and failed only the same timestamp fixture. Migration
reported `0 failed, 0 error(s)`, but the exact optional-W1 capability skip was
initially rejected; non-standard reported `0 failed, 0 error(s)`.

Luna Max corrections `0c7a064e…` and `daf6fd39…` were composed and published
as test-only head `2b8108b9b69ca70b20a3b705a82e167ea13bb98a`, tree
`522bcd01035cb44d241ff56c3deff3de272701c2`. SOL Medium initially found a
trailing-space mismatch in the migration-skip guard, then accepted the amended
correction. Exact-head Actions run `32152200822` / job `95760574305` then
completed **success** against Odoo pin `30bde9…`: fresh and warm each ran 2,682
tests with `0 failed, 0 error(s)`; fresh recorded 40 tour markers with all 39
required, and warm ran zero same-version migrations. W2-only validated the old
W1 `19.0.1.0.0` → W2 `19.0.0.2.0` schema bridge with both JSONB columns and W1
unchanged. Migration bases `50b…` and `0a15…` each ran 2,647 tests twice with
`0/0`, applying five and four scripts respectively on the first pass and zero
on the second. Non-standard ran 62 tests `0/0` plus three HOOT suites. The
narrow optional-W1 skip is permitted only in migration qualification.

This is accepted exact-head CI evidence only. It does not supply an Odoo.sh
build/database, live Shopify result, or Gate A–H proof.

## Plain answers

| Question | Exact-head answer |
| --- | --- |
| Is the underlying architecture sound? | The durable Odoo-side substrate is promising and modular; the requested hybrid inbound architecture is incomplete. |
| Does it function live against Shopify? | Not proven. No exact-head live mutation or fresh remote read is recorded. |
| Is synchronization near-real-time where required? | Only the bounded `app/uninstalled` and product create/update code paths are present; inventory, order, refund and fulfillment paths remain scheduled/reconciliation based. |
| Are webhooks and reconciliation both reliable? | W1/W2 provide source-level webhook and reconciliation controls, but exact-head delivery, deduplication and repair are not live-passed; required domain slices remain incomplete. |
| Can it recover safely from failures? | Code-level recovery controls are present; live transport, timeout and crash recovery remain unproven. |
| Can it scale to the intended workload? | Not established. Product/order scan caps and absent Bulk Operations leave large-volume capacity unresolved. |
| Are permissions secure? | ACL/company/boundary controls are substantial; exact-head external multi-user runtime evidence remains open. |
| Is the UX understandable? | The organization is coherent and the W1/W2 setup contract is source-reviewed, but exact-head backend qualification is still required before UI UAT. |
| What remains before production? | Remaining domain webhooks, Odoo.sh/live Gates A–H, representative performance evidence, security proof, and UAT. |
| Build, refactor, or replace? | Controlled refactor: preserve core job/mutation/recovery substrate; add bounded ingress and scale paths. |

## Evidence classification

- **[Official]** — statement from an official Odoo or Shopify source.
- **[Code fact]** — behavior observed in the exact checkout.
- **[Inference]** — consequence of code facts and the requested contract.
- **[Recommendation]** — proposed correction or acceptance condition.
- **[Decision]** — control-room release/UAT ruling.
- **[Not proven]** — no live, exact-head or independent evidence exists.

## Contents

- [Exact-head assurance addendum — current qualification candidate](./exact-head-addendum-2026-08-18-f62.md)
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
| E Webhook delivery | **Not live-passed / externally blocked** | W1/W2 source paths exist, but no exact-head Shopify subscription, delivery, HMAC, async-processing or reconciliation-repair evidence is available; Odoo.sh access is blocked. |
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
