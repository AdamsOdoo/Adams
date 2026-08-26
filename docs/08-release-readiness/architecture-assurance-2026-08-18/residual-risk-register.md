# Residual-risk register

**Date:** 2026-08-18

**Exact head/tree:** `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8` /
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

These are risks remaining after the code controls currently visible in the
checkout. They are not accepted production risks; each needs an owner and
closure evidence.

| ID | Risk | Current control | Residual exposure | Owner / closure condition |
| --- | --- | --- | --- | --- |
| RR-001 | Shopify webhook delivery can be delayed, duplicated, reordered or missed | Scheduled scans/reconciliation exist; no webhook path yet | Near-real-time workflows cannot be assured and inbound updates can be stale | Luna webhook writer; subscription/HMAC/delivery ID/async/watermark plus live Gate E and reconciliation repair |
| RR-002 | Remote mutation response is uncertain after timeout/crash | Durable attempt, lease, manual-review and remote reconciliation substrate | Live transport and crash boundary behavior not proven on target shop/API | Luna live validator; Gate G with fresh remote reads and no-blind-retry proof |
| RR-003 | Large catalog/order window exceeds hard cap | Fail-closed finite page caps | Product/order scan can repeat same window indefinitely; no Bulk/resumable implementation | Architecture owner; selected scale design and >cap recovery test |
| RR-004 | Shopify cost/throttle varies by app/store/plan | Cost metadata persisted; local backpressure and retry classification | Actual query costs, restore behavior, fairness and backlog recovery unmeasured | Live/performance owner; controlled sampling and multi-store test |
| RR-005 | Odoo.sh scheduled actions have bounded execution slots | 5-minute drain, small batches, `_commit_progress`, per-job commits | 15–60 minute inbound scans cannot meet freshness expectations; backlog may grow | Operations owner; webhook path plus measured capacity and configured limits |
| RR-006 | Credential compromise or database disclosure | Admin-only ACL, masked/write-only UI, redacted logs, no token echo | Credential database representation has no encryption-at-rest claim | Security owner; policy decision and direct RPC/log audit |
| RR-007 | Company/allowed-company isolation defect in a newly changed UI path | Company record rules, binding constraints and ACL matrix in source/tests | External multi-user/multi-company runtime evidence absent on exact head | Security reviewer; Gate H with dedicated users and role restoration |
| RR-008 | Stale/ambiguous remote data may overwrite local state | GID bindings, snapshots, `updatedAt` checks, CAS/manual review | Every supported domain’s conflict and watermark behavior is not live-proven; webhook path absent | Domain owners; matrix-driven Gate C–F journeys |
| RR-009 | Fulfillment Mode 2 semantics are misunderstood | Conservative reconciliation/review states | Setup wording may lead operators to expect no inbound read-back | Fulfillment owner; copy correction and explicit UAT scenarios |
| RR-010 | Unsupported returns/privacy topics may be omitted from production deployment | Current modules fail closed for unsupported/ambiguous cases | Distribution/compliance requirements could impose additional webhook topics and data-retention behavior | Product/security owner; decide scope before subscription registration |
| RR-011 | Historical wrong-domain data may be mistaken for valid evidence | Correct-domain onboarding refuses immutable rehome; historical jobs preserved separately | Record 555 / jobs 3186/3188 are easy to misread in an operator review | Control room; mark historical evidence and prove correct-store identity first |
| RR-012 | Build/CI state may drift while live evidence is collected | Exact HEAD/tree recorded in packet | Actions run `32103926602` was in progress at last check; build/database URL linkage incomplete | Control room; recheck final run and publish exact DB URL/qualification |

## Release treatment

RR-001 through RR-005 and RR-012 are release-blocking for this assurance
request. RR-006 through RR-011 require explicit policy/product decisions and
targeted evidence before production planning. None is silently accepted by this
packet.
