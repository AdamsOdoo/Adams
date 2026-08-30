# V2 Target Architecture

> **Classification:** implementation-ready target for architecture-gate review. Existing accepted ADRs remain authoritative until a reviewed ADR explicitly changes them.

## 1. Architectural objective

V2 should be a modular monolith inside Odoo: cohesive domain addons, one shared runtime, explicit application services, small Shopify gateways and projection-driven UI. It avoids both rejected extremes—one giant connector and a micro-addon/microservice explosion.

```mermaid
flowchart TB
    UI["Odoo views + selective Owl"] --> APP["Application commands and queries"]
    APP --> DOM["Domain policies and mappings"]
    APP --> RUN["Shared operation runtime"]
    DOM --> PORT["Shopify gateway ports"]
    RUN --> PORT
    PORT --> SH["Shopify GraphQL Admin API"]
    DOM --> ODOO["Odoo business models"]
```

Dependency direction is enforced: presentation → application → domain/runtime ports → adapters. Domain code never imports controllers, UI components or raw HTTP transport.

## 2. Bounded contexts and addon posture

Preserve the accepted domain-aligned addon family and stable technical names during migration:

| Context | Owns | Does not own |
| --- | --- | --- |
| Core/runtime | stores, credential handle, capabilities, runs/jobs/execution attempts/mutation evidence, redacted logs, transport, throttle budget, webhook inbox, handler registry, shared binding contract, readiness registry | product/order/inventory/fulfillment mappings |
| Product | product/variant import, bindings, matching and evidence | catalog mutations |
| Product export | preview, approval and controlled catalog mutations | import matching |
| Sale | customer/order import, bindings, total evidence | inventory or fulfillment execution |
| Inventory | location mapping, first-push guard, Odoo-authoritative quantity commands, drift evidence | fulfillment location selection |
| Fulfillment | picking-triggered FulfillmentOrder orchestration, tracking updates, verification | inventory mapping ownership |

The four domain-specific webhook addons in the current implementation are candidates to fold into their owning domain addons **only after** install/upgrade/uninstall and XML-ID migration proof. The generic receiver and inbox remain core. This is packaging cleanup, not a new webhook architecture.

## 3. Internal layering

### Presentation

- Standard Odoo actions/views for stores, attention items, bindings, runs and settings.
- Selective Owl clients for Overview, setup/readiness, matching and product diff.
- No direct GraphQL calls and no business mutation from component code.
- Typed, versioned query DTOs and command payloads; components do not depend on ORM record shape by accident.

### Application

Commands represent user/system intent: `ConnectStore`, `ActivateStore`, `StartImport`, `ApproveCatalogChange`, `ResolveMatch`, `PushInventory`, `CreateFulfillment`, `RetryAttempt`, `ReconcileScope`.

Every command performs authorization, company/store scope validation, configuration-generation check, admission policy, idempotency/operation-scope allocation and audit creation before dispatch.

Queries build read models for screens. They aggregate server-side in bounded queries; the browser does not reconstruct health from multiple low-level endpoints.

### Domain

Pure policy services decide authority, mapping, eligibility, matching, totals, quantity interpretation and allowed state transitions. Domain handlers accept normalized Shopify DTOs and return explicit outcomes. They do not parse raw GraphQL envelopes.

### Integration/runtime

Split the current broad client/dispatch responsibilities into cohesive internal services:

| Service | Responsibility |
| --- | --- |
| Transport | HTTPS, timeout, headers, redaction boundary, correlation ID |
| GraphQL executor | variables, error envelope normalization, API-version metadata |
| Cost governor | per-store available-cost observation, admission delay, bounded jitter |
| Domain gateway | small query/mutation methods returning normalized DTOs |
| Webhook inbox | HMAC, canonical store resolution, webhook-ID dedup, fast acknowledgement, enqueue |
| Run coordinator | command→jobs, priority lane, scope serialization, cancellation/pause |
| Attempt executor | lease/claim, savepoint, heartbeat, exception normalization, retry scheduling |
| Verification service | mutation readback and uncertain-outcome resolution |
| Reconciler | checkpoint + overlap-window enumeration, drift detection and repair routing |

These are Python boundaries inside the accepted addon family first. They are not independent services or new deployables.

## 4. Runtime model

```mermaid
stateDiagram-v2
    [*] --> Requested
    Requested --> Admitted: policy passes
    Requested --> Blocked: action required
    Admitted --> Running
    Running --> Succeeded
    Running --> Retryable: classified transient failure
    Retryable --> Running: scheduled attempt
    Running --> Verifying: mutation outcome uncertain
    Verifying --> Succeeded: remote state confirms
    Verifying --> Review: result remains ambiguous
    Running --> Review: human decision required
    Running --> Terminal: non-recoverable
```

Keep request/run, job, execution attempt and remote mutation intent distinct. A retry creates an execution attempt, not a duplicate business request; the existing `shopify.connector.mutation.attempt` remains the durable certainty record for one remote-write intent. Append-only observations preserve throttle, error, readback and actor evidence. Existing job rows are projected through opaque `job:<id>` run references before additive run/execution-attempt schema is introduced.

Priority lanes are explicit: interactive recovery and webhook admission outrank scheduled reconciliation; bounded aging prevents starvation. Per-store operation-scope keys serialize conflicting writes. Workers claim with database-safe locking and short transactions; network calls are never made while holding broad business-record locks.

## 5. Data and compatibility contracts

- Existing binding identity and uniqueness remain the idempotency anchor for entities.
- Existing model names, XML IDs and external IDs are compatibility APIs unless a migration ADR proves otherwise.
- Store/company and configuration-generation fences are checked at admission and immediately before side effects.
- Domain-owned checkpoints advance only after a fully committed page; cursors are run-local.
- Payload snapshots are minimized, redacted and retention-controlled; business records remain canonical in Odoo.
- Schema changes use expand → backfill/project → dual-read → switch → contract. No big-bang table replacement.
- Upgrade and uninstall tests must prove preservation or intentional disposition of bindings, jobs, mappings and credentials.

## 6. Shopify interaction contract

- One pinned API-version policy and documented upgrade cadence.
- GraphQL variables only; no string interpolation of business input.
- Cost-aware pagination and bounded batches, with per-store throttling.
- Explicit user errors and top-level GraphQL errors normalized into the connector taxonomy.
- Webhook acknowledgement is fast and side-effect free after durable inbox/dedup recording.
- Reconciliation covers missed, duplicate and out-of-order webhooks.
- Use Shopify-supported idempotency where available; connector keys plus verification everywhere else.
- Mutation timeout or lost response enters verification, never automatic blind replay.

## 7. Security and privacy

- Credential writes are isolated from ordinary store forms and never returned to the client.
- Least-privilege Shopify scopes are validated and displayed; missing and excess scopes are reviewable.
- Odoo ACLs/record rules are paired with application-service authorization and company/store scoping.
- Logs, exceptions, payload samples and notifications pass a single redaction policy.
- Webhook HMAC uses the raw request body and constant-time comparison before parsing or enqueueing.
- Audit events record actor, reason, authority, configuration generation and affected scope.
- Data retention, disconnect and uninstall behavior are explicit and tested.

## 8. Observability and service levels

Metrics must drive operations rather than vanity:

- admission-to-start and end-to-end latency by workflow/priority;
- success, retry, manual-review and terminal-failure rates;
- oldest actionable item and queue age;
- Shopify cost budget and throttle delay;
- webhook acknowledgement latency, duplicate rate and reconciliation drift;
- uncertain-mutation count and verification resolution time;
- freshness per store/workflow.

Proposed initial SLOs for pilot validation, not promises: webhook acknowledgement p95 < 2 s; interactive command admission p95 < 3 s; no silent ambiguous mutation; zero cross-company processing; 100% of terminal/manual-review outcomes have an operator-facing action or explicit “no safe action”. Tune volume-based SLOs after production baselining.

## 9. Testing architecture

| Layer | Required evidence |
| --- | --- |
| Policy unit tests | state transitions, authority, matching, retry classification, quantity and total rules |
| Contract tests | gateway DTOs against versioned Shopify fixtures; GraphQL variables/errors/cost extensions |
| ORM/integration | constraints, savepoints, ACLs, record rules, multi-company and upgrade behavior |
| Concurrency | duplicate admission, lease contention, priority aging, operation-scope serialization |
| Mutation safety | timeout-before/after-commit simulations, readback resolution, idempotency TTL |
| Webhook | HMAC, duplicate/out-of-order delivery, invalid store, fast acknowledgement, reconciliation |
| UI | Owl unit tests, tours for core journeys, accessibility and responsive/RTL visual regression |
| Migration | production-shaped database copy, expand/backfill/switch/rollback, module lifecycle |
| Performance | query budgets, batch bounds, memory, API cost and queue latency at representative volume |

Every architecture seam needs a characterization test before extraction. New and legacy paths run from the same golden fixtures until parity is demonstrated.

## 10. Engineering rules

- Keep files and classes small enough to own one reason to change; enforce complexity and dependency checks in CI.
- No domain-specific conditional ladder in the transport or generic dispatcher; use registries/ports.
- No hidden context flags for security or authority decisions.
- No unbounded ORM scans, N+1 screen aggregations or unbounded payload/log retention.
- Feature flags are store-scoped, auditable and fail-safe; they are migration controls, not permanent architecture.
- The backend contract precedes visual implementation. Mocked UI prototypes use the same DTO/state vocabulary that production services will expose.
