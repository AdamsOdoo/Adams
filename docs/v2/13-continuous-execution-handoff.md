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

- Recorded at (UTC): `2026-08-31T10:35:00Z`
- Owner/model/chat: Codex GPT-5.6 Sol implementation owner; bounded GPT-5.6 Luna implementation and independent-review lenses
- Branch: `codex/v2-continuous-implementation`
- Accepted V1 implementation base SHA: `f77bfcc25e63615e6226dd9a9329f8f943593cb2`
- Approved V2 blueprint source SHA: `3914004e27630b09b211e3d2ee92a8e6d9a0e55e`
- Last completed source SHA: `78f2a09c984a78bd85db2c6b0bdde69c6630e428`
- Evidence SHA: this documentation-only checkpoint immediately following the source SHA;
  resolve its exact identity from the branch head to avoid a self-referential commit hash
- Current remote implementation-branch head: this evidence checkpoint after publication
- Candidate frozen: no
- Active wave/task: close the W2 safety checkpoint, publish exact-source evidence, then integrate P06/P10 reads
- Authorization/environment boundary: continuous dev-branch implementation and controlled
  server-to-server test-store use authorized; PR #210, PR #211, staging and production remain
  untouched unless explicitly routed by the implementation program

### Completed

- Preserved the accepted V1 data, identifiers, safety fences, retry semantics, webhook
  deduplication, mutation evidence and audit history; PR #210 and PR #211 remain untouched.
- Completed the deterministic P00 repository analyzer, P01 contracts/registries/policies,
  named 48 GraphQL operations, and created exact operation, journey, setup and guideline
  evidence. Runtime-only evidence remains explicitly pending.
- Implemented substantial P02 Overview/Needs Attention/Run projections and P15 store/setup/
  settings controls, including independent multi-store configuration capped at ten stores.
- Hardened command replay against generation drift and made async P15/V2 reads and commands
  fail closed when navigation, company, store, selection or component context changes.
- Separated durable mutation lineage from mutable job projections; every mutation admission
  validates job/attempt/run/store/settings lineage before credential access and again under
  lock before lease creation.
- Closed retry/reconciliation resend hazards: valid C2 evidence creates or reuses one query-
  only reconciliation child, malformed evidence blocks, and uncertain writes are never
  blindly replayed.
- Standardized lock order as original job then attempt, removed the manual-resolution lock
  cycle, and made P11 run projections flush and lock before reporting evidence.
- Closed all independent V2 UI audit findings: exact current-surface authority, durable
  uncertain-command retry, selection/poll fencing, bounded-projection warnings, safe
  pagination, and exact affected-record targets.
- Created remote source checkpoint `78f2a09c984a78bd85db2c6b0bdde69c6630e428` with exact
  tree `6e3a5f69be2b36cf9f66958718923992efad7ec9`, identical to the reviewed local source
  subset; regenerated the six repository artifacts twice with byte-identical output.
- Kept generated JSON complete while changing it to canonical compact, top-level-line output,
  reducing the largest artifact from 880 KB to 606 KB and keeping provenance diffs reviewable.

### In progress

- Commit this exact-source evidence and handoff, push the two coherent checkpoints once, and
  qualify the resulting exact remote head through GitHub CI.
- Close W2 by integrating P06 product/sale read gateways and registering real P10 read
  handlers; then qualify P05/P07/P09/P15 in an Odoo/PostgreSQL environment.

### Changed/uncommitted files

- Source and tests are clean at remote source `78f2a09c`; the local source subset has the
  identical tree.
- Only `docs/v2/13-continuous-execution-handoff.md` and the exact-source evidence ledger are
  intentionally uncommitted. Do not mix new production edits into this evidence checkpoint.

### Verification completed

- Complete dependency-free suite: 386 tests passed on the source tree.
- Python compilation, JavaScript syntax, two changed XML parses and `git diff --check`: passed.
- Static policy, all seven addon dependency-direction policies and changed-production-file
  size policy: passed.
- Deterministic evidence generation: two independent runs were byte-identical; repository
  baseline `--check` passed against the exact source tree at `78f2a09c`.
- Independent UI review found 16 actionable issues across two passes; every finding was fixed
  and the focused activation suite passed 23 tests.
- Independent backend safety audit found no concrete blocker; its 28 focused tests passed.
- Existing remote connector suite `33331564061` and V2 policy `33331564058` passed at the
  previous remote checkpoint `7fa08b8`; the new evidence head still requires CI.

### Verification still required

- Odoo-backed ORM/security/concurrency tests, fresh install, warm update, migrations, backup/
  restore, uninstall and measured performance require CI/Odoo.sh because local Odoo and
  PostgreSQL are unavailable.
- P06/P10 production read integration, cumulative P11 modes, P12 inventory, P13 product export
  and P14 fulfillment integration remain before the backend foundation is complete.
- V2/P16 production asset activation, Products/Orders/Inventory/Fulfillment/Settings surfaces,
  all-store health, responsive/RTL/accessibility browser proof and U1–U14 remain pending.
- Live Shopify test-store readback, latency/SLO measurement, frozen-candidate P17 qualification,
  App Store metadata/screenshots/archive scan and P18 rollout remain pending.

### External state (no secrets)

- Odoo build/database alias: no new build created for source `78f2a09c`; remote qualification
  begins after the evidence checkpoint is pushed.
- Shopify test-store alias: no external mutation made in this checkpoint.
- store UI/gateway/runtime modes: V2/P16 sources remain deliberately unmanifested/inert.
- running/queued/uncertain work: none created.

### Defects and blockers

- No source-level blocker remains in this checkpoint.
- Product completion is not release completion: P06/P10/P12–P16 integrations and every U1–U14
  end-to-end journey are still formally pending.
- Near-real-time mechanics exist (post-response webhook dispatch, immediate worker wake-up,
  one-minute fallback and 5/15/30-second UI polling), but the 15/60-second SLO is unmeasured.
- Local scratch lacks PostgreSQL/Odoo and `graphql-core`; unavailable runtime evidence must stay
  pending rather than being inferred from dependency-free tests.

### Rollback

- Remote source checkpoint `78f2a09c984a78bd85db2c6b0bdde69c6630e428` is the first
  post-publication rollback point; the local source subset has the identical tree.
- Previous remote rollback remains `7fa08b8146b1489c4feba978b88bd6e014ec0923`.

### First next action

- Verify PR #212 exact-head CI, then begin the P06/P10 integration chunk without rerunning
  expensive gates prematurely.

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
