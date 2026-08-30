# V2 Lighter-Model Execution Handoff

> **Purpose:** let a lower-cost implementation model execute one bounded packet without reconstructing product or architecture decisions.  
> **Authority:** this file routes work; the referenced contracts remain authoritative.

## 1. Before touching code

Read completely, in this order:

1. repository-root `AGENTS.md` and `CLAUDE.md`;
2. `docs/v2/README.md`;
3. `docs/v2/11-decision-and-traceability-register.md`;
4. the selected packet in `docs/v2/10-implementation-roadmap.md`;
5. the packet’s primary blueprint documents from the map below;
6. current rolling `docs/01-research/research-handoff.md` entries relevant to the touched subsystem;
7. current source/tests at the exact implementation base.

Do not implement directly on the docs branch. Create the packet branch from the accepted `Shopify-connector` implementation head recorded at the gate. Verify the exact SHA and clean scope before editing.

## 2. Document routing map

| Work | Must read |
| --- | --- |
| Product behavior/navigation/copy | `01-product-experience.md`, `05-ux-design-blueprint.md` |
| Architecture/addon/layer ownership | `02-target-architecture.md`, `06-backend-implementation-blueprint.md` |
| Model fields/DTOs/commands/errors/authority | `07-data-and-api-contracts.md` |
| Migration/flags/canary/rollback | `08-migration-and-cutover-blueprint.md` |
| Tests/performance/SLO/release | `09-test-observability-release-blueprint.md` |
| Exact PR scope/order | `10-implementation-roadmap.md` |
| Locked/rejected choices and traceability | `11-decision-and-traceability-register.md` |
| Platform/competitor evidence | `04-evidence-and-competitor-decisions.md` |
| Refactor-vs-replace escalation | `03-refactor-vs-replacement.md` |

## 3. One-packet operating procedure

### Step 1 — Establish facts

Record:

- selected packet ID/title;
- exact base branch and SHA;
- current PR/issue if any;
- changed/dirty files before work;
- relevant current model/method/XML IDs and tests;
- accepted decisions/rejected approaches implicated;
- external official documentation that must be revalidated.

Never assume the old snapshot in these docs is the current implementation head. Use it as migration evidence, then inspect the actual base.

### Step 2 — Write the packet contract in the PR/plan

Copy and fill:

```markdown
Packet: Pxx — <title>
Outcome: <one sentence>
Base SHA: <exact>
Depends on: <merged packet/SHA>
Allowed files: <exact paths/globs>
Forbidden files: <exact paths/globs>
Preserved invariants: <decision IDs>
Characterization tests first: <tests>
New behavior tests: <tests>
Performance/security/lifecycle gates: <gates>
Rollback: <exact mode/code path>
Evidence files updated: <paths>
```

If the task cannot be expressed inside one roadmap packet, stop and ask the orchestrator to split or revise the roadmap. Do not improvise a broader packet.

### Step 3 — Inspect before modifying

- Search with `rg`; map every caller/import/test of the intended seam.
- Read complete relevant files, not snippets around one method.
- Identify existing accepted behavior and failure modes.
- Add/confirm a characterization test that fails if the behavior changes unexpectedly.
- Check for user-owned dirty changes and avoid them.

### Step 4 — Implement smallest vertical change

- Use existing compatibility seam or create the packet-specified seam first.
- Keep old/new local paths switchable where migration requires it.
- Do not perform drive-by formatting, renaming or abstraction.
- Do not change tests solely to accept a different result unless the blueprint explicitly changes that result.
- Add production code, behavior tests and evidence together.
- Keep secrets and merchant/customer data out of output.

### Step 5 — Verify in increasing cost

1. syntax/import/lint for touched files;
2. focused unit/contract/ORM tests;
3. relevant addon/module suite;
4. dependency/security/concurrency/fault tests required by packet;
5. fresh/warm/lifecycle tests when triggered;
6. browser/visual/a11y tests when triggered;
7. full connector suite;
8. performance/evidence comparison;
9. exact-SHA environment/UAT only where the packet authorizes it.

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

### Step 7 — Publish only complete evidence

Commit a coherent packet on its branch. Update the rolling research handoff without deleting history. Open/update a draft PR with exact evidence, risks, rollback and remaining blockers. Do not mark ready, merge, deploy broadly or advance a canary unless the user explicitly authorizes that stage and its gate passes.

## 4. Stop conditions

Stop implementation and report evidence if any of these occur:

- actual base/governance conflicts with the packet;
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

1. stop the packet before dependent implementation;
2. state the conflicting fact with file/test/official-source evidence;
3. identify affected V2 decision IDs, requirements, DTOs, tests, packets and migration path;
4. propose the smallest alternatives with tradeoffs;
5. update architecture docs only after review acceptance;
6. resume from a revised packet.

Never reinterpret “implementation-ready” as permission to ignore new facts.

## 6. Packet completion report template

```markdown
## Outcome
<what now works>

## Identity
- Packet: Pxx
- Base: <sha>
- Head: <sha>
- PR: <url>

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
<none, or exact blocker; do not hide deferred work>
```

## 7. Suggested implementation prompt

Use this with the implementation model, filling only bracketed values:

```text
Implement exactly packet [Pxx — title] from docs/v2/10-implementation-roadmap.md in AdamsOdoo/Adams.

Before acting, read AGENTS.md, CLAUDE.md, docs/v2/README.md, docs/v2/11-decision-and-traceability-register.md, this handoff, the complete selected packet, and every blueprint document routed to that packet. Inspect the actual current base [branch] at exact SHA [sha]; preserve user changes.

Scope is only the packet's allowed files and outcome. Treat its forbidden files, V2 decisions, accepted repository ADRs and rejected approaches as hard constraints. Add characterization tests before extracting behavior. Use the specified compatibility seam, DTO/state vocabulary, security checks, migration modes, performance budgets and rollback. Do not add external services, change stable model/XML/binding identity, perform blind mutation retries, persist raw payloads, expose secrets/PII, broaden permissions, or weaken tests.

Verify in the order defined in docs/v2/12-lighter-model-execution-handoff.md and run every packet-specific gate. Update evidence, traceability and the rolling research handoff. If facts conflict with the packet or a stop condition occurs, stop and return an evidence-backed blocker instead of improvising.

Do not merge, mark ready, deploy broadly or advance rollout without explicit authorization. End with the packet completion report including exact base/head SHA, tests/evidence and rollback.
```

## 8. Review prompts by specialty

Use after implementation; these are reviews, not permission to mutate unrelated scope.

### Backend/runtime reviewer

```text
Review packet Pxx for transaction boundaries, claims/locks, idempotency, generation/store fences, state transitions, retry/readback certainty, evidence durability and rollback. Trace every remote call and possible failure point. Report findings by severity with exact file/behavior evidence; do not implement fixes unless asked.
```

### Security reviewer

```text
Review packet Pxx for ACL/record-rule plus service authorization, active-company/same-store isolation, direct-RPC bypass, secret/PII/redaction, webhook/GraphQL input handling and count/aggregate leakage. Test every role and forged identifier. Report findings and required gates; do not broaden access.
```

### Frontend/UX reviewer

```text
Review packet Pxx against docs/v2/05-ux-design-blueprint.md and the live reference. Verify hierarchy, copy, every response state, keyboard/focus/screen-reader behavior, 375/768/1366/1440, RTL, permissions, RPC/query count and no console/overflow. Do not trade required evidence or Odoo-native behavior for visual similarity.
```

### Migration/release reviewer

```text
Review packet Pxx on a production-shaped copy for expand/backfill/dual-read/switch/rollback, fresh/warm/uninstall lifecycle, row/constraint/XML identity, interruption/resume, locks, exact-SHA evidence and canary halt conditions. No remote mutation during migration.
```

## 9. Orchestrator checklist

Before assigning a packet:

- predecessor gate accepted;
- exact base SHA supplied;
- issue/PR and single owner assigned;
- required official platform fact refreshed;
- test environment/data profile available;
- mutation test store/authority explicitly bounded if applicable;
- independent reviewer named for security/mutation/release packet;
- no parallel packet conflicts on the same models/contracts/store;
- expected evidence and decision deadline stated.

After a packet:

- changed files match allowlist;
- tests/evidence match packet, not only author summary;
- decisions/traceability/handoff updated;
- flags/facades have owner/removal issue;
- PR remains draft until gate review;
- next packet receives the accepted exact head, never an assumed branch tip.

## 10. What the implementation model must not decide

The following are already decided and must not be relitigated inside a packet:

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

Only new repository or official-platform evidence can reopen one through the deviation procedure.

