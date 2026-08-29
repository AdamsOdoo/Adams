# Shopify Connector V2 — Product and Architecture Gate

> **Status:** Recommendation for review — docs only, 2026-08-29.  
> **Base:** `Shopify-connector` at `dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b`.  
> **Current implementation evidence:** draft release PR #210 at `44da1e006eb19f93e685bc9993935153292b84f7`.  
> **Authority:** this package does not authorize implementation or supersede accepted ADRs. It proposes the V2 product contract and an evidence-based delivery strategy.

## Outcome

**Recommendation:** build V2 through **staged refactoring with bounded internal replacement**, not a ground-up rewrite and not cosmetic renovation of V1.

Preserve the proven safety assets: Odoo records and bindings, stable model/XML identifiers, module installation data, job history, idempotency and serialization rules, mutation admission/readback safeguards, webhook deduplication, company/store-generation fences, retry taxonomy, and accepted domain authority rules.

Replace behind compatibility seams: the oversized API client, store/setup orchestration, job-dispatch internals, duplicated webhook packaging, read-model aggregation, and the production UI shell. A deeper replacement becomes justified only if the proof gates in the delivery assessment fail.

## Package

| Document | Purpose |
| --- | --- |
| [V2 product experience](./01-product-experience.md) | Product promise, navigation, screens, journeys, states, roles, visual and accessibility contract |
| [V2 target architecture](./02-target-architecture.md) | Runtime layers, bounded contexts, contracts, data safety, observability, testing, deployment constraints |
| [Refactor vs replacement assessment](./03-refactor-vs-replacement.md) | Evidence, decision matrix, staged route, replacement triggers, gates and rollback |
| [Evidence and competitor decisions](./04-evidence-and-competitor-decisions.md) | Current-product inputs, official references, competitor patterns and explicit learn/avoid decisions |

## V2 north star

The operator should be able to answer four questions within seconds:

1. Is each store safe and operational?
2. What needs human attention now?
3. What changed, why, and what will happen next?
4. Can I act without creating duplicates, overwriting authority, or guessing the result of a remote write?

The product is a calm Odoo-native control plane, not a generic synchronization dashboard and not a second ERP.

## Non-negotiable guardrails

- Shopify GraphQL Admin API remains behind a single integration boundary.
- Webhooks are hints: verify, deduplicate, enqueue, reconcile.
- Every mutation passes admission, idempotency/serialization, observation and terminal-result gates.
- Ambiguous mutation outcomes are read back before retry; never blind-retried.
- Shopify/Odoo source-of-truth is explicit per field or operation.
- Standard Odoo list/form/search views remain the default; Owl is reserved for the few interaction-dense surfaces.
- No new SPA router, global browser state store, external worker, giant addon, or per-feature addon explosion.
- No internal refactor may force a customer to reconnect a store or discard existing bindings/job evidence.

## Approval gates

This package asks reviewers to approve three things separately:

1. **Product gate:** the information architecture, journeys, states and screen contracts are the desired V2 experience.
2. **Architecture gate:** the layer boundaries and compatibility contracts are the target internal design.
3. **Delivery gate:** proceed with Stage 0/1 proof work; do not approve the full migration until compatibility, performance and rollback evidence passes.

No V2 production code should begin before those three review outcomes are recorded.
