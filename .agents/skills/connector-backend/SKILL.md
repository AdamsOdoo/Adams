---
name: connector-backend
description: Implement or repair this connector's Odoo models, schema, Shopify gateways, webhooks and durable sync workflows, preserving existing ownership and mutation safety.
---

Read root AGENTS.md and the handoff first. Route architecture to `docs/v2/02-target-architecture.md`, implementation to `06-backend-implementation-blueprint.md`, commands to `07-data-and-api-contracts.md`, migration to `08-migration-and-cutover-blueprint.md` (all in docs/v2). Read only the owning contract.

Identify the entrypoint, owning addon, persisted identities, actor/store/company scope, transaction boundary and observable outcome. Trace caller → service → gateway/job → readback, including failure. Distinguish a source defect from a stale fixture or unavailable environment.

For schema work, check Lite, Full and optional-owner combinations. Presence of product_template does not establish export ownership. A pre-init bridge must be narrow, idempotent, type-checked and aligned with the owning migration; do not fabricate future runtime tables for old-registry prefetch. Prove supported old-core compatibility or retain it as an open gate.

For I/O, verify the pinned GraphQL document and current official contract. Preserve separate HTTP, GraphQL and user-error classification; bound pagination/cost/backoff. HMAC uses the raw body; acknowledge after durable admission and process asynchronously. Reconcile duplicate/missing/reordered hints without repeating effects.

Preserve claim-token/generation checks, global lock order and durable mutation lineage. Free-text redaction must not corrupt closed-format server identities. After-send timeout remains uncertain until readback; manual review is a real result, not a retry loophole.

Extend existing native regressions for the changed failure mechanism. Pure checks cannot establish ORM, SQL, locks or migration correctness. Return paths, behavior, actual checks, open native/live proof and migration/rollback impact.
