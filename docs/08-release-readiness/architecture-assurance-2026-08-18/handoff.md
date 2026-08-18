# Assurance handoff

**Prepared:** 2026-08-18

**Exact head/tree:** `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8` /
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

## Current control-room state

- PR #206 / `codex/ui-restructure-implementation` is not ready or approved.
- Exact-head Odoo.sh build `36553922` is reported successful.
- Actions run `32103926602` was in progress at the last check.
- Only `testin-lzhbzhtc.myshopify.com` is authorized.
- Prior build `36550325` had store 562 with the correct domain but no
  credential; historical record 555 was absent. Failed jobs 3186/3188 are
  wrong-domain evidence only.
- No live Shopify mutation, subscription or remote read is recorded on the
  exact head.
- Product/inventory and order/fulfillment UI UAT are blocked.

## What the source audit established

The current core is a useful foundation: store identity verification, company
boundaries, generation fencing, durable jobs, network leases, mutation
attempts, CAS/idempotency where supported, manual review, reconciliation and
bounded cron dispatch are present. The missing production webhook system is a
capability gap, not a test gap. Product/order scan caps and absent Bulk
Operations leave large-volume support unresolved.

## Next bounded assignments

1. **Luna Max Agent A:** implement the modular webhook/subscription/HTTPS
   ingress and reconciliation design; preserve the existing job/lease/attempt
   substrate. Do not touch production credentials during implementation.
2. **Luna Max Agent B:** prepare exact-head live Gates A–H on the correct store;
   record remote GIDs, job/attempt/subscription/delivery IDs, fresh read-backs,
   replay/no-op outcomes and cleanup. Do not treat jobs or HTTP 200 as remote
   success.
3. **SOL Medium Reviewer:** independently review the architecture and every
   changed webhook/scale/security path, then re-review material corrections.

## Safe resume sequence

Preserve this packet and the ledger → bounded implementation in isolated
worktree → focused tests → exact-head Actions → Odoo.sh fresh/warm/migration
qualification → independent review → live backend gates → only then UI UAT.

## Do not do

- Do not use `mqiu21-yz.myshopify.com`.
- Do not repurpose an immutable wrong-domain store row.
- Do not add a mock controller and call Gate E passed.
- Do not delete historical jobs or evidence before proving no valid bindings or
  merchant data depend on them.
- Do not merge, approve or mark PR #206 ready.
- Do not overwrite the webhook-owned packet files
  `docs/07-implementation-plan/webhook-implementation-packets.md` or
  `docs/05-qa/webhook-w1-validation-results.md` from this worktree.
