# V2 Lighter-Model Execution Handoff

> **Purpose:** let a lower-cost implementation model execute the authorized five-wave program continuously without reconstructing product or architecture decisions or pausing after every internal work item.  
> **Authority:** this file routes work; the referenced contracts remain authoritative.

## 1. Before touching code

Read completely, in this order:

1. repository-root `AGENTS.md` and `CLAUDE.md`;
2. `docs/v2/README.md`;
3. `docs/v2/11-decision-and-traceability-register.md`;
4. `docs/v2/13-continuous-execution-handoff.md` and its current checkpoint;
5. the active wave and work-item IDs in `docs/v2/10-implementation-roadmap.md`;
6. the active work’s primary blueprint documents from the map below;
7. relevant current `docs/01-research/research-handoff.md` entries only when platform/research facts are implicated;
8. current source/tests at the exact implementation base.

Do not implement directly on the docs branch. Create the single V2 integration branch from the accepted `Shopify-connector` implementation head recorded at the gate. Verify the exact SHA and clean scope before editing; all later chats continue from the recorded exact head.

## 2. Document routing map

| Work | Must read |
| --- | --- |
| Product behavior/navigation/copy | `01-product-experience.md`, `05-ux-design-blueprint.md` |
| Architecture/addon/layer ownership | `02-target-architecture.md`, `06-backend-implementation-blueprint.md` |
| Model fields/DTOs/commands/errors/authority | `07-data-and-api-contracts.md` |
| Migration/flags/canary/rollback | `08-migration-and-cutover-blueprint.md` |
| Tests/performance/SLO/release | `09-test-observability-release-blueprint.md` |
| Exact wave/work-item scope/order | `10-implementation-roadmap.md` |
| Locked/rejected choices and traceability | `11-decision-and-traceability-register.md` |
| Platform/competitor evidence | `04-evidence-and-competitor-decisions.md` |
| Refactor-vs-replace escalation | `03-refactor-vs-replacement.md` |
| Cross-chat checkpoint and resume | `13-continuous-execution-handoff.md` |

## 3. Continuous work-item operating procedure

### Step 1 — Establish facts

Record:

- active wave plus selected work-item ID(s)/title;
- exact base branch and SHA;
- current integration branch/candidate PR/issue if any;
- changed/dirty files before work;
- relevant current model/method/XML IDs and tests;
- accepted decisions/rejected approaches implicated;
- external official documentation that must be revalidated.

Never assume the old snapshot in these docs is the current implementation head. Use it as migration evidence, then inspect the actual base.

### Step 2 — Write the work contract in the plan/handoff

Copy and fill:

```markdown
Wave/work: Wn / Pxx[, Pyy] — <title>
Outcome: <one sentence>
Base SHA: <exact>
Depends on: <green checkpoint/SHA>
Allowed files: <exact paths/globs>
Forbidden files: <exact paths/globs>
Preserved invariants: <decision IDs>
Characterization tests first: <tests>
New behavior tests: <tests>
Performance/security/lifecycle gates: <gates>
Rollback: <exact mode/code path>
Evidence files updated: <paths>
```

P IDs may be combined only under the roadmap’s same-boundary rule. If the requested outcome materially exceeds the authorized wave, changes locked architecture or requires new external authority, stop with evidence. Otherwise refine it into smaller coherent commits and continue without seeking permission for each commit.

### Step 3 — Inspect before modifying

- Search with `rg`; map every caller/import/test of the intended seam.
- Read complete relevant files, not snippets around one method.
- Identify existing accepted behavior and failure modes.
- Add/confirm a characterization test that fails if the behavior changes unexpectedly.
- Check for user-owned dirty changes and avoid them.

### Step 4 — Implement smallest vertical change

- Use the existing compatibility seam or create the active-work-specified seam first.
- Keep old/new local paths switchable where migration requires it.
- Do not perform drive-by formatting, renaming or abstraction.
- Do not change tests solely to accept a different result unless the blueprint explicitly changes that result.
- Add production code, behavior tests and evidence together.
- Keep secrets and merchant/customer data out of output.

### Step 5 — Verify in increasing cost

1. syntax/import/lint for touched files;
2. focused unit/contract/ORM tests;
3. relevant addon/module suite;
4. dependency/security/concurrency/fault tests required by the active work;
5. fresh/warm/lifecycle tests when triggered;
6. browser/visual/a11y tests when triggered;
7. full connector suite;
8. performance/evidence comparison;
9. exact-SHA environment/UAT only where the authorized wave requires it.

Do not skip a cheaper failure and continue to expensive qualification.

### Step 6 — Self-review against invariants

Answer every RA-V2 check in `11`. Also confirm:

- no direct Shopify I/O outside the adapter;
- no network call in a broad DB transaction;
- no `sudo()`/context-flag authorization shortcut;
- no blind mutation retry;
- no changed binding/model/XML identity;
- no new source of truth/cache/persistent generic attention table;
- no raw payload/secret/PII exposure;
- no N+1/unbounded scan;
- no permanent flag/facade without removal issue.

### Step 7 — Checkpoint and continue

Commit each coherent work item on the integration branch, update traceability/evidence and refresh `13-continuous-execution-handoff.md`. Update the single candidate PR with exact evidence, risks, rollback and remaining blockers. When the current gate is green, advance to the next work item/wave automatically.

Before the current chat approaches its context limit—or whenever tool output starts truncating, the active state becomes hard to restate exactly, or a long gate will outlive the chat—create and verify a safe checkpoint, then hand off according to document `13`. The next chat verifies branch/SHA/dirty state and resumes the first named action; it does not restart research or repeat completed work.

Do not merge or deploy outside the authorization already granted. Final ready-for-review status follows the exact-candidate gate; broad production rollout still follows the bounded cohort authority and safety controls.

## 4. Stop conditions

Stop implementation and report evidence if any of these occur:

- actual base/governance conflicts with the active work contract;
- required predecessor is not merged/accepted;
- a stable model/XML ID/constraint must change to proceed;
- current behavior cannot be characterized;
- dependency cycle forces changes across unrelated addons;
- migration cannot preserve binding/store/job evidence;
- mutation has no exact readback strategy;
- Shopify official schema contradicts a planned operation;
- security requires permission broadening/secret exposure;
- target performance budget is impossible on the recorded environment;
- existing user changes overlap and cannot be safely preserved;
- a test must be weakened or a safety check bypassed to proceed;
- production/staging/customer credentials or broader authority are required;
- any automatic halt condition occurs.

The correct output is a bounded blocker report and a proposed decision update—not speculative code.

## 5. Evidence-based deviation procedure

If evidence shows a blueprint decision must change:

1. stop the affected work before dependent implementation;
2. state the conflicting fact with file/test/official-source evidence;
3. identify affected V2 decision IDs, requirements, DTOs, tests, packets and migration path;
4. propose the smallest alternatives with tradeoffs;
5. update architecture docs only after review acceptance;
6. resume from the revised work contract.

Never reinterpret “implementation-ready” as permission to ignore new facts.

## 6. Work checkpoint/completion report template

```markdown
## Outcome
<what now works>

## Identity
- Wave/work: Wn / Pxx[, Pyy]
- Base: <sha>
- Head: <sha>
- Integration branch/candidate PR: <name/url>

## Changed
- <bounded changes>

## Preserved
- <decision/invariant IDs and how proven>

## Verification
- Focused: <commands/results>
- Full suite: <command/result>
- Security/concurrency/migration/UI/performance: <evidence paths>

## Runtime and external effects
- Shopify reads: <none/bounded>
- Shopify writes: <none/exact authorized test operations>
- Deployment: <none/environment>

## Rollback
<mode/code path and in-flight handling>

## Remaining
<next exact work item, none, or exact blocker; do not hide deferred work>

## Continuity
- Handoff updated: <path/commit>
- Receiving action: <one exact first action>
```

## 7. Suggested implementation prompt

Use this once to start or resume the implementation model, filling only bracketed values:

```text
Execute the authorized V2 implementation program from active Wave [Wn], beginning with [Pxx — title], in AdamsOdoo/Adams. Continue automatically through the remaining work items and waves while their evidence gates pass; P IDs are traceability units, not approval stops.

Before acting, read AGENTS.md, CLAUDE.md, docs/v2/README.md, docs/v2/11-decision-and-traceability-register.md, this handoff, docs/v2/13-continuous-execution-handoff.md, the complete active wave/work items, and every blueprint document routed to them. Inspect the actual integration branch [branch] at exact SHA [sha]; preserve user changes and verify the current checkpoint instead of repeating finished work.

Scope is the active wave and bounded work-item contracts. Treat forbidden files, V2 decisions, accepted repository ADRs and rejected approaches as hard constraints. Build and qualify the shared backend foundation before production UI wiring. Add characterization tests before extracting behavior. Use the specified compatibility seam, DTO/state vocabulary, security checks, migration modes, performance budgets and rollback. Do not add external services, change stable model/XML/binding identity, perform blind mutation retries, persist raw payloads, expose secrets/PII, broaden permissions, or weaken tests.

Verify in the order defined in this handoff and run every active-work/wave gate. Update evidence, traceability and the continuous handoff. Fix and retest ordinary failures without asking for renewed permission. If facts conflict with locked architecture, authority or a stop condition occurs, stop and return an evidence-backed blocker instead of improvising.

Commit coherent checkpoints to the single integration branch and keep one candidate PR current. When context approaches its limit, checkpoint and hand over before losing state; the receiving chat verifies exact SHA and continues the first named action. Do not merge or deploy outside granted authority. End only at a blocker or completed exact-candidate/rollout gate, using the checkpoint report with exact base/head SHA, tests/evidence, rollback and next action.
```

## 8. Review prompts by specialty

Use after implementation; these are reviews, not permission to mutate unrelated scope.

### Backend/runtime reviewer

```text
Review work item(s) Pxx for transaction boundaries, claims/locks, idempotency, generation/store fences, state transitions, retry/readback certainty, evidence durability and rollback. Trace every remote call and possible failure point. Report findings by severity with exact file/behavior evidence; do not implement fixes unless asked.
```

### Security reviewer

```text
Review work item(s) Pxx for ACL/record-rule plus service authorization, active-company/same-store isolation, direct-RPC bypass, secret/PII/redaction, webhook/GraphQL input handling and count/aggregate leakage. Test every role and forged identifier. Report findings and required gates; do not broaden access.
```

### Frontend/UX reviewer

```text
Review work item(s) Pxx against docs/v2/05-ux-design-blueprint.md and the live reference. Verify hierarchy, copy, every response state, keyboard/focus/screen-reader behavior, 375/768/1366/1440, RTL, permissions, RPC/query count and no console/overflow. Do not trade required evidence or Odoo-native behavior for visual similarity.
```

### Migration/release reviewer

```text
Review work item(s) Pxx on a production-shaped copy for expand/backfill/dual-read/switch/rollback, fresh/warm/uninstall lifecycle, row/constraint/XML identity, interruption/resume, locks, exact-SHA evidence and canary halt conditions. No remote mutation during migration.
```

## 9. Orchestrator checklist

Before starting/resuming a wave:

- predecessor evidence gate green;
- exact base SHA supplied;
- integration branch/candidate PR and single integration owner identified;
- required official platform fact refreshed;
- test environment/data profile available;
- mutation test store/authority explicitly bounded if applicable;
- independent review lens available for security/mutation/release work;
- no overlapping work-item conflicts on the same models/contracts/store;
- expected evidence and decision deadline stated.

After each coherent checkpoint:

- changed files match allowlist;
- tests/evidence match the work contract, not only author summary;
- decisions/traceability/continuous handoff updated;
- flags/facades have owner/removal issue;
- candidate PR remains draft until exact-candidate qualification;
- next work item/chat receives the verified exact head, never an assumed branch tip;
- green gate advances automatically; blocker gate records the stop condition and affected downstream work.

## 10. What the implementation model must not decide

The following are already decided and must not be relitigated inside an implementation work item:

- refactor versus blank rewrite;
- modular monolith versus microservices/external queue;
- addon/model/XML/binding compatibility posture;
- Odoo-native plus selective Owl frontend;
- navigation and primary user journeys;
- Shopify adapter/gateway boundary;
- run/job/execution-attempt/mutation distinction;
- attention provider projection;
- source-of-truth/matching/first-push/notification rules;
- uncertain mutation readback;
- migration modes/order/soak and automatic halt conditions;
- accessibility/performance/security/release gates.
- foundation-first production UI order;
- the one-program/five-wave execution and proactive handoff protocol;

Only new repository or official-platform evidence can reopen one through the deviation procedure.
