# V2 Continuous Execution Handoff

> **Purpose:** preserve exact implementation state across long work chats, model changes,
> context compaction and deliberate session switches without restarting or repeating work.

## 1. Continuity rule

The repository, not chat memory, carries execution state. The active implementation owner
updates this file:

- after every material checkpoint or published commit;
- before a work chat becomes context-constrained;
- before switching to another chat/model/owner;
- before pausing on an external dependency;
- immediately after recovering from a failed or interrupted attempt.

Do not wait until the conversation is nearly unusable. Prefer an early coherent handoff
with preserved evidence over a late compressed summary.

## 2. Safe checkpoint procedure

1. Stop admitting new changes and finish or explicitly revert the current atomic edit.
2. Run the cheapest checks needed to prove the checkpoint is internally coherent.
3. Commit and push when the tree is safe; otherwise record every uncommitted file and why.
4. Capture exact branch, accepted base, last code/evidence commit and current remote head.
5. Record external state without secrets: environment/build IDs, Shopify test-store alias,
   active store/workflow modes, running/uncertain work and candidate freeze status.
6. Record completed work, active work, deferred blockers, tests run, tests still required,
   rollback point and the exact first next action.
7. Start the next chat by verifying the remote head and reading this file before acting.

No credential, token, customer payload or raw PII is copied into the handoff. Reference the
approved secret location or connection mechanism instead.

## 3. Current implementation checkpoint

- Recorded at (UTC): `2026-08-30T19:33:41Z`
- Owner/model/chat: Codex GPT-5.6 Sol implementation owner; six GPT-5.6 Luna read-only audit lenses active
- Branch: `codex/v2-continuous-implementation`
- Accepted V1 implementation base SHA: `f77bfcc25e63615e6226dd9a9329f8f943593cb2`
- Approved V2 blueprint source SHA: `3914004e27630b09b211e3d2ee92a8e6d9a0e55e`
- Last completed code/evidence SHA: `985d4c977d49e05e1087e6dde996b4998d2ee9b3`
- Current remote head: not yet published at this checkpoint
- Candidate frozen: no
- Active wave/task: W1 / P00 repository compatibility evidence; runtime characterization next
- Authorization/environment boundary: continuous dev-branch implementation and controlled
  server-to-server test-store use authorized; PR #210, PR #211, staging and production remain
  untouched unless explicitly routed by the implementation program

### Completed

- Started the implementation branch from the latest V1 release candidate rather than the
  older `Shopify-connector` pointer, preserving all current V1 safety, domain, migration and
  test work.
- Integrated the approved V2 blueprint/governance without changing PR #210 or PR #211.
- Added a dependency-free P00 repository analyzer and four pure unit tests.
- Froze all six required evidence artifacts; runtime-only fields are honestly marked pending.
- Added a sub-10-minute static policy workflow for deterministic compatibility and GraphQL
  schema checks.
- Proved two consecutive repository evidence generations byte-identical and the current
  compatibility self-check green.

### In progress

- Review read-only specialist audits against repository evidence.
- Add isolated database/restore/profile collection and behavior counterfactual fixtures.
- Execute the first coherent expensive install/update/concurrency baseline through CI/Odoo.sh,
  then defer its repetition until the next backend-foundation chunk.

### Changed/uncommitted files

- `tools/v2_repository_baseline.py`: remove two trailing spaces found by the patch check.
- this handoff update.

### Verification completed

- `python3 -m unittest tools.tests.test_v2_repository_baseline -v`: 4 passed.
- repository baseline generation twice: identical SHA-256 digests for all six artifacts.
- `python3 tools/v2_repository_baseline.py --source-ref HEAD --check`: passed.
- Python compilation, workflow YAML parse and XML/AST parsing inside the analyzer: passed.
- `tools/validate_shopify_graphql.py`: not executed locally because `graphql-core` is absent;
  the new CI lane installs the pinned addon requirements before this check.

### Verification still required

- GitHub V2 policy lane and existing connector install/update/full-suite baseline.
- isolated fresh/warm registry profile, database backup/restore identity proof and PERF-0 run.
- selected golden behavior counterfactuals around API, setup, store, credentials, dispatch and
  domain hotspots.

### External state (no secrets)

- Odoo build/database alias: none created by this checkpoint.
- Shopify test-store alias: no call made.
- store UI/gateway/runtime modes: not introduced.
- running/queued/uncertain work: none created.

### Defects and blockers

- No implementation blocker. Local scratch lacks PostgreSQL/Odoo and `graphql-core`; use the
  existing reproducible CI/Odoo.sh lanes rather than weakening or fabricating runtime proof.

### Rollback

- Revert `985d4c9` to remove P00 analysis-only files. V1 product data/behavior is unchanged.

### First next action

- Commit the patch-check correction and this handoff, publish the implementation branch, then
  inspect exact-SHA policy/full-suite results while continuing the P00 runtime collector and
  characterization work.

## 4. Implementation checkpoint template

Replace the section below at each implementation checkpoint; keep important previous
checkpoints in Git history rather than appending an unbounded log.

```markdown
## Current implementation checkpoint

- Recorded at (UTC):
- Owner/model/chat:
- Branch:
- Accepted base SHA:
- Last completed code/evidence SHA:
- Current remote head:
- Candidate frozen: yes/no + exact SHA
- Active wave/task:
- Authorization/environment boundary:

### Completed
-

### In progress
-

### Changed/uncommitted files
- none / exact paths and state

### Verification completed
- command/suite/result/evidence path

### Verification still required
-

### External state (no secrets)
- Odoo build/database alias:
- Shopify test-store alias:
- store UI/gateway/runtime modes:
- running/queued/uncertain work:

### Defects and blockers
- issue, severity, owner, deferred-to-end yes/no

### Rollback
- exact safe SHA/mode/runbook

### First next action
- one exact action the next chat can execute immediately
```

## 5. Receiving-chat verification

The next chat must:

1. fetch PR/branch state and compare it with this handoff;
2. inspect any uncommitted/overlapping changes before editing;
3. verify the last stated test/evidence result when it controls the next step;
4. continue from “First next action” rather than recreate a plan;
5. update this handoff again before its own context becomes constrained.

If branch state contradicts the handoff, branch state and committed evidence win; record the
discrepancy before continuing.
