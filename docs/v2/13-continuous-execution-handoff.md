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

## 3. Current checkpoint

| Field | Value |
| --- | --- |
| Program | V2 product/architecture correction — docs only |
| Pull request | #211 `codex/v2-product-architecture-gate` → `Shopify-connector` |
| Accepted planning base | `dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b` |
| Input head for this correction | `c395101c498ea6d2ba8fc1d263537a2c32bd17ee` |
| Current code implementation | none; PR #210 remains untouched |
| Active wave | pre-implementation architecture/governance correction |
| External mutations | none |
| Release status | no V2 release candidate; V1 public release remains separately frozen until qualified |

### Completed before this checkpoint

- V2 product experience, target architecture, visual prototype and backend/data/migration/
  test blueprint drafted.
- Competitor public screens, documentation and demonstrations reviewed with vendor claims
  kept separate from verified platform facts.
- Staged refactor with bounded internal replacement selected over a blank rewrite.

### Correction being published

- replace stale research-only root governance;
- convert P00–P20 from mandatory separate PR/approval stops into traceable work items inside
  one continuous five-wave program;
- make foundation-first backend proof mandatory before production frontend wiring;
- add V1 lessons, full end-to-end journeys, exact Administrator settings, multi-store UX,
  near-real-time responsiveness targets and refund/payout extension seams;
- make efficient tiered testing and proactive chat-to-chat continuity binding.

### First next action after approval

Start Wave 1 from the user-approved exact `Shopify-connector` head: freeze compatibility,
characterize V1 and prove restore/security/contract baselines. Continue automatically into
later waves only when their evidence checkpoint passes. Do not modify PR #210 or any
staging/production environment merely because this docs package is approved.

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

