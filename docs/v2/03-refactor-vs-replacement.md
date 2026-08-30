# Staged Refactor vs Internal Replacement Assessment

> **Verdict:** staged refactor with bounded subsystem replacement. Confidence: **high for the direction, medium for the exact migration duration** until Stage 0 measurements are complete.

## 1. Why not a ground-up rewrite

The current connector already contains costly, safety-critical assets: installed Odoo data, entity bindings, migration history, module contracts, concurrency controls, mutation admission/readback behavior, retry/error vocabulary, webhook deduplication, company and generation fences, and extensive tests. Recreating those together would enlarge the defect surface and delay user value without improving the product by itself.

A blank rewrite would also collide with binding rejected approaches: it tends toward either a new giant module, micro-module proliferation, external-worker complexity, or re-litigation of accepted identity/retry/source-of-truth decisions.

## 2. Why ordinary cleanup is insufficient

The current implementation shows concentration risk: core client, setup/store/credential/dispatch services and setup UI files are unusually large; infrastructure, orchestration and presentation responsibilities are harder to change independently; domain webhook packaging is fragmented; and the production experience does not yet express the simpler V2 navigation and read models.

Therefore “keep everything and restyle it” will not produce the target. Several internal components should be replaced behind stable contracts while customer data and behavioral invariants remain in place.

## 3. Decision matrix

| Area | Preserve | Refactor/extract | Replace | Reason |
| --- | --- | --- | --- | --- |
| Bindings and identity | Yes | Only additive fields/indexes | No | High migration and duplicate risk; accepted model |
| Store/company/generation fences | Yes | Centralize enforcement | No | Proven safety boundary |
| Retry/error taxonomy | Yes | Separate policy from execution | No | Stable operator and audit language |
| Job history | Yes | Project into run/job/attempt read model | Schema only if proven | Audit/upgrade value |
| API client | Behavior only | Split immediately | Internal implementation | Oversized responsibility boundary |
| Dispatch/runtime | Safety semantics | Extract coordinator/executor/verification | Internals where parity proven | Enables priority, observability and isolated testing |
| Setup/store services | Data and lifecycle | Command/query split | Orchestration implementation | Current concentration blocks UX evolution |
| Webhook receiver/dedup | Yes | Generic inbox + registry | Domain packaging selectively | Existing safety; packaging fragmentation |
| Domain mapping policies | Yes | Move toward pure services | Only failing algorithms | Accepted authority rules |
| Production UI | Accepted visual principles | Reuse standard views | Custom composed surfaces | V2 IA/read models differ materially |
| Addon names/dependencies | Yes initially | Fold webhook satellites only with proof | No wholesale rename | Odoo lifecycle and upgrade risk |

## 4. Delivery stages

### Stage 0 — Baseline and characterization

- Freeze supported V1 behavior and database contracts.
- Measure query count, latency, API cost, memory, queue age, failure/retry mix and UI task completion.
- Build golden Shopify fixtures and production-shaped anonymized database fixtures.
- Add characterization tests around the large client, dispatch, setup, credential and store services.
- Create an architecture dependency map and identify cycles/private imports.

**Exit:** representative baseline is reproducible; critical behavior has tests; rollback database snapshot and restore are proven.

### Stage 1 — Contracts and read models

- Define versioned application command/query DTOs and V2 state vocabulary.
- Introduce Overview, Attention and Run projections over existing models without changing execution.
- Add server-side aggregation and query budgets.
- Validate the approved prototype against real DTO fixtures and Odoo-shell feasibility; do not wire production frontend yet.

**Exit:** stable read contracts can render every required state from V1 execution fixtures; no duplicate source of truth. Production UI waits for the Shopify boundary/runtime foundation.

### Stage 2 — Shopify gateway extraction

- Place a compatibility facade in front of the current API client.
- Extract transport, GraphQL executor, cost governor and domain gateways one operation family at a time.
- Run old/new gateway contract tests and shadow read comparisons; never shadow mutations.

**Exit:** all operations use normalized DTOs; raw GraphQL envelopes do not escape the adapter; latency/cost do not regress beyond approved budgets.

### Stage 3 — Runtime replacement behind the job contract

- Separate run coordination, attempt execution, retry policy and verification.
- Project existing jobs into run/job/attempt semantics; migrate schema only through expand/backfill/dual-read.
- Introduce priority lanes and bounded aging after concurrency proof.
- Cut over one read-only workflow, then one idempotent inventory mutation, then non-idempotent fulfillment only after readback tests pass.

**Exit:** no duplicate/ambiguous silent side effect; recovery and throughput meet the pilot SLO; old execution remains switchable during soak.

### Stage 4 — Store lifecycle and V2 UI

- Replace setup orchestration with application commands and readiness registry.
- Implement Overview, Needs Attention, operation launcher and run timeline using the Stage 1 contracts.
- Migrate matching/diff flows and contextual record panels; retain standard Odoo lists/forms.
- Run moderated usability, accessibility, RTL, responsive and permission tests.

**Exit:** core journeys meet the experience measures; V1 operational navigation can be retired without removing technical evidence.

### Stage 5 — Packaging cleanup and contraction

- Evaluate folding domain webhook addons into their owning domains.
- Remove compatibility facade and dead paths only after two release cycles or the agreed soak window.
- Contract obsolete columns/models in a later migration with backup/restore evidence.

**Exit:** one supported path remains; install/upgrade/uninstall matrices pass for all edition combinations.

## 5. When deeper replacement becomes necessary

Escalate from bounded replacement to a deeper internal replacement only if Stage 0–2 produce evidence for one or more of these conditions:

1. Critical behavior cannot be characterized without relying on uncontrolled global state or private cross-domain mutation.
2. The existing job schema cannot represent attempt/readback/audit semantics additively without breaking retention or uniqueness.
3. Dependency cycles prevent extracting transport/runtime without simultaneous changes across most addons.
4. A production-shaped upgrade cannot preserve binding identity and store lifecycle safely.
5. Performance profiling proves the ORM model—not query implementation—is the bottleneck at target volume.
6. Security review finds credential or tenant isolation cannot be repaired behind the current persistent contracts.

Even then, replace internals using coexistence and data migration. Do not discard bindings or force reconnection unless a separate, explicit migration decision accepts that customer impact.

## 6. Program controls

The stages execute continuously after program authorization. They are automatic evidence
checkpoints, not separate user approval cycles. Each coherent implementation unit records:

- explicit allowed/forbidden files and dependency direction;
- invariant checklist tied to accepted ADRs and rejected approaches;
- before/after performance and API-cost evidence;
- migration, downgrade/rollback and uninstall notes;
- feature flag owner, expiry and removal issue;
- threat-model delta and PII/log review;
- contract, concurrency, mutation-safety, UI and upgrade evidence as applicable;
- release canary by store, with automated halt on duplicate-risk, cross-company or uncertain-mutation thresholds.

No stage is accepted merely because tests are green; the proof must cover the failure mode introduced by that stage.

## 7. Delivery posture

The user has selected one continuous implementation program. Stage 0 still measures the
unknowns and may refine internal effort estimates, but it does not force a new authorization
request before every subsystem. Work proceeds foundation → gateway/runtime → domains/setup →
complete UI → qualification whenever the owning evidence gate passes. Use coherent commits,
targeted tests and rollback points; keep post-release contraction/packaging outside the critical
path. Stop only on a defined safety, evidence or external-authority condition.
