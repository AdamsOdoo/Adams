# CLAUDE.md — Shopify Connector Project Governance

> **Status:** V2 product/architecture correction and implementation preparation.
> Production connector code remains gated until the user explicitly authorizes the
> implementation run. Once that run is authorized, the implementation owner proceeds
> continuously through the accepted execution program without requesting approval at
> every internal checkpoint.

## 1. Objective

Build a premium Odoo 19 ↔ Shopify connector that is reliable, responsive,
understandable to non-technical operators, modular without fragmentation, and safe to
extend with later domains such as refunds, returns and payouts.

The connector must outperform market alternatives through operational clarity,
failure recovery, mutation safety, installation simplicity and Odoo-native user
experience. Feature-count claims are not a substitute for proven behavior.

## 2. Authority and source of truth

Authority is resolved in this order:

1. the user's latest explicit instruction and authorization boundary;
2. this file and repository-root `AGENTS.md`;
3. accepted V2 contracts under `docs/v2/`;
4. accepted ADRs and `docs/05-qa/rejected-approaches-log.md`;
5. the current implementation work item.

If two authorities materially conflict, stop at a safe checkpoint and report the
exact conflict. Do not silently select the easier interpretation.

GitHub is the project source of truth. Decisions, code, tests, evidence, handoffs and
release verdicts must be committed. Chat output alone is not a deliverable.

## 3. Current program state

- V1 release qualification remains separate from V2 design work.
- PR #211 is the docs-only V2 product, architecture and execution blueprint.
- PR #210 is implementation evidence/current V1 reference and must not be modified by
  V2 documentation work.
- V2 production code begins only after explicit user authorization.
- Authorization to start the V2 implementation program authorizes continuous progress
  through its already-approved internal gates. Repeated confirmation is not required
  unless a stop condition or new external authority is encountered.

## 4. Execution model

Use one continuous delivery program, not twenty-one separate conversations or approval
cycles. The program is organized into five evidence checkpoints in
`docs/v2/10-implementation-roadmap.md`:

1. V1 baseline and contracts;
2. shared backend foundation: Shopify boundary, runtime, security, migration, store lifecycle and settings;
3. domain workflow reliability and mutation readback;
4. complete Odoo-native product experience;
5. exact-candidate qualification and controlled rollout.

Internal task IDs remain useful for traceability, tests and rollback, but they are not
mandatory standalone PRs or reasons to pause. Use a program branch, coherent commits
and one final candidate PR unless a technically independent change genuinely benefits
from separate review.

Only one implementation owner edits an overlapping subsystem at a time. Specialist
review lenses may operate in parallel when they do not mutate overlapping files.

## 5. Foundation-first rule

Production UI must not be built on guessed behavior. Before production frontend wiring:

- characterize V1 behavior and database compatibility;
- establish typed Shopify gateways and normalized errors;
- establish command/query contracts, authorization and tenant fences;
- prove the job/run/attempt/mutation-certainty runtime;
- prove install, upgrade, rollback, concurrency, throttling and failure recovery;
- expose stable read DTOs and allowed-action contracts.

Visual component scaffolding may use contract fixtures, but it cannot become production
truth until the owning backend contract passes its gate.

## 6. Architecture invariants

- Remain an Odoo modular monolith; do not add a broker, external worker, cache service
  or microservice without measured evidence and a new ADR.
- Preserve stable addon/model/table/XML IDs, binding identity, store identity, jobs,
  logs, mutation evidence and customer data through additive migration.
- Keep Shopify I/O behind typed, versioned domain gateways.
- Keep HTTP requests, claims and database transactions short; never hold broad Odoo
  business locks across network calls.
- Use durable idempotency, operation scopes and readback verification. Never blindly
  replay a mutation whose remote outcome may have occurred.
- Treat webhooks as fast hints; verify HMAC/delivery identity and reconcile missed,
  duplicate and out-of-order events.
- Enforce active-company, exact-store and configuration-generation checks at admission
  and immediately before side effects.
- Keep credentials write-only and redact secrets, raw payloads and PII.
- Prefer standard Odoo views/services/components; use Owl only where composition or
  live interaction materially improves the task.
- Matching never guesses from names. Inventory first push and fulfillment notification
  remain explicit, previewed and audited.

## 7. Simplicity and engineering discipline

Reliability does not justify speculative infrastructure.

- Add an abstraction only when it isolates an external side effect, enforces a domain
  boundary, or has at least two concrete consumers.
- Do not create generic repositories, event buses, caches, state machines or plugin
  frameworks for hypothetical future use.
- Extend through small typed registries for real operations, readiness providers,
  attention providers and gateway handlers.
- Batch ORM work, bound pagination and searches, prefetch deliberately, index measured
  hot paths and remove N+1 behavior.
- Prefer Odoo ORM and framework primitives; use reviewed SQL only after profiling proves
  the ORM path cannot meet an accepted budget.
- Keep methods cohesive, state transitions explicit and error codes stable.
- No unrelated cleanup or formatting inside a behavioral change.

Implementation follows official Shopify and Odoo 19 documentation plus the actual
pinned code/schema. Refresh any version-sensitive platform fact before the owning work.

## 8. Testing efficiently

Testing is continuous but economically ordered:

1. syntax, import, lint and structural checks for touched files;
2. focused policy/contract/ORM tests;
3. affected domain integration and fault tests;
4. lifecycle, concurrency, browser and performance gates when triggered;
5. the complete connector suite and exact-SHA qualification once the candidate freezes.

Do not run the most expensive suite after every small edit. Do not defer all testing to
the end. A failed cheap gate stops the expensive gate. A candidate change reopens only
the affected gate and its downstream dependencies.

## 9. Complete user journeys

Every advertised workflow must be proven end to end across backend, Odoo UI and live
Shopify readback where applicable. The authoritative journey matrix is in
`docs/v2/09-test-observability-release-blueprint.md` and includes setup, multi-store,
products/variants, customers/orders, inventory, fulfillment/tracking, manual and
scheduled work, webhooks/reconciliation, failure recovery, permissions, disconnect,
upgrade and rollback.

A backend test or attractive screen alone does not complete a journey.

## 10. Branch and change governance

- Never commit directly to `main`.
- Keep plain `dev` untouched unless the user explicitly changes policy.
- `Shopify-connector` is the integration base; implementation branches start from its
  accepted exact SHA.
- Preserve unrelated user changes and inspect the worktree/branch before editing.
- Record exact base/head SHA, changed files, tests, external effects and rollback.
- Do not merge, publish broadly or modify staging/production unless explicitly within
  the authorized execution boundary.

Each coherent implementation unit records allowed paths, forbidden paths, acceptance
criteria, tests, migration impact and rollback. These may be sections of one continuous
program rather than separate PRs.

## 11. Research and competitor evidence

- Platform facts use official Shopify/Odoo sources and state the relevant version.
- Competitor features are vendor claims unless independently exercised.
- Screen observations identify the exact public page, screenshot or video.
- Facts, competitor claims, inferences, recommendations and accepted decisions remain
  distinguishable.
- Do not repeat a rejected approach unless its documented revisit condition is met.

Competitor research informs product decisions; it never overrides platform safety or
actual repository behavior.

## 12. Stop conditions

Stop and preserve evidence only when:

- the exact base or predecessor contract is missing or contradictory;
- migration cannot preserve identity/data/history;
- a remote mutation has no deterministic admission/idempotency/readback strategy;
- official Shopify/Odoo behavior contradicts the design;
- security requires broader access, exposed credentials or weakened tenant isolation;
- a test must be weakened or a safety invariant bypassed;
- staging/production/customer authority outside the granted boundary is required;
- overlapping user changes cannot be preserved safely;
- an automatic release halt condition fires.

Ordinary test failures, implementation defects and expected refactoring decisions are
work to resolve, not reasons to request repeated authorization.

## 13. Continuous chat/session handoff

The implementation may span multiple work chats. Continuity is mandatory:

- update `docs/v2/13-continuous-execution-handoff.md` after every material checkpoint,
  before a context-heavy chat approaches its limit, and before switching chats;
- commit and push a safe checkpoint before handoff whenever the tree is coherent;
- record exact branch/base/head, current wave/task, completed work, active changes,
  tests, environment/external state, blockers deferred to the end, rollback and the
  first next action;
- never copy credentials or raw PII into the handoff;
- the next chat reads this file, the latest commit and relevant evidence before acting;
- do not repeat completed work or rely on chat memory when GitHub evidence exists;
- never claim work continues in the background after the active turn ends.

Handoff happens early enough to preserve reasoning and state, not after context is
already exhausted.

## 14. Start-of-work checklist

1. Read this file, `AGENTS.md`, `docs/v2/README.md`, the current execution handoff and
   the documents routed to the active wave.
2. Confirm exact base SHA, branch, authorization boundary and preserved user changes.
3. Confirm the backend predecessor and cheap test gate are green.
4. Implement only the active coherent scope while continuing autonomously through the
   program when its gate passes.
5. Update tests, evidence, traceability and the continuity handoff before publishing a
   checkpoint.
