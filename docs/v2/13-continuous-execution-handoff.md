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

- Recorded at (UTC): `2026-08-31T22:48:39Z`
- Owner/model/chat: Codex GPT-5.6 Sol implementation owner with an independent local review pass
- Branch: `codex/v2-continuous-implementation`
- Accepted V1 implementation base SHA: `f77bfcc25e63615e6226dd9a9329f8f943593cb2`
- Approved V2 blueprint source SHA: `3914004e27630b09b211e3d2ee92a8e6d9a0e55e`
- Last completed remote source SHA: `9e1ca0f2cb6017b5031558e4528818090ad854f0`
- Exact source tree: `b6ac802ff462a82057f86b81a33b9ceff2fe17d3`
- Equivalent reviewed local source commit: `91cdefb0272dc73b95615f7c24923041f125130b`
- Evidence SHA: this documentation-only checkpoint immediately following the remote source
  SHA; resolve its exact identity from the branch head to avoid a self-referential commit hash
- Current remote implementation-branch head: this evidence checkpoint after publication
- Candidate frozen: no
- Active wave/task: publish and qualify the exact P10 evidence checkpoint, then continue the
  remaining P12-P16 domain/runtime and user-journey implementation in bounded vertical slices
- Authorization/environment boundary: continuous dev-branch implementation and controlled
  server-to-server test-store use authorized; PR #210, PR #211, staging and production remain
  untouched unless explicitly routed by the implementation program

### Completed

- Preserved accepted V1 data, identifiers, safety fences, retry semantics, webhook
  deduplication, mutation evidence and audit history; PR #210 and PR #211 remain untouched.
- Completed the deterministic P00 repository analyzer, P01 contracts/registries/policies,
  named 48 GraphQL operations, and exact operation, journey, setup and guideline evidence.
  Runtime-only evidence remains explicitly pending rather than inferred.
- Implemented substantial P02 Overview/Needs Attention/Run projections and P15 store/setup/
  settings controls, including independent multi-store configuration capped at ten stores.
- Hardened command replay against generation drift and centralized configuration-generation
  ownership so accepted policy changes increment exactly once while scan progress does not.
- Separated durable mutation lineage from mutable job projections; mutation admission validates
  job/attempt/run/store/settings lineage before credential access and again under lock before
  lease creation. Uncertain mutations remain query-only until reconciled.
- Extracted P06/P07 domain reads and mutation providers behind typed, purpose-authorized
  contracts while preserving the accepted V1 error taxonomy and legacy routes.
- Implemented the production P10 product-scan handler with claim-aware page reads, immutable
  workflow/operation binding, durable per-page progress, safe continuation and monotonic
  checkpoints. Configuration drift rejects the page before local effects.
- Closed the independent P1 findings: cancellation/finalization lock inversion, cross-run
  multi-job batch deadlock, stale-handler retry, missing handler/run binding and regressing
  product-scan checkpoints.
- Added the V1/V2 claim fence: runless legacy jobs remain claimable, while run-linked V2 jobs
  require an explicit registered job type both before and under the claim lock.
- Stale read jobs whose handler disappeared now enter manual review as
  `unregistered_read_handler`; mutation attempts remain excluded from this recovery path.
- Added focused dependency-free tests and real two-connection Odoo/PostgreSQL barrier
  regressions for opposite cross-run batches, claim/cancellation ordering and stale handlers.
- Published remote source `9e1ca0f2cb6017b5031558e4528818090ad854f0`; all 64 uploaded blob
  hashes matched the reviewed local Git objects and GitHub produced exact tree
  `b6ac802ff462a82057f86b81a33b9ceff2fe17d3`.
- Regenerated the six repository baseline artifacts twice against that exact remote source;
  both runs were byte-identical and the baseline check passed.

### In progress

- Publish the one-file operation-catalog provenance repair identified by the first evidence-head
  CI run, then qualify the resulting exact remote head through one coherent GitHub CI run.
- Continue the remaining backend domain runtime slices only after that checkpoint is coherent;
  do not mix new production code into the evidence commit.

### Changed/uncommitted files

- Production source and tests are clean at remote source `9e1ca0f2`; the reviewed local source
  tree is byte-identical.
- Only `docs/v2/13-continuous-execution-handoff.md`, `docs/v2/evidence/README.md` and the six
  regenerated evidence artifacts are intentionally uncommitted. Do not mix production edits
  into this evidence checkpoint.

### Verification completed

- Complete dependency-free suite: **446 tests passed** on the exact source tree.
- Python compilation and `git diff --check`: passed.
- Static policy, all seven addon dependency-direction policies and changed-production-file
  size policy: passed.
- Shopify GraphQL schema validation: **48 documents passed** against Admin API `2026-07`
  using pinned `graphql-core==3.2.6` in a temporary dependency directory.
- Independent diff review found no unsafe mutation path; it caught and closed the wall-clock
  scan-window inversion and source-size violations before publication.
- Deterministic evidence generation: two independent runs were byte-identical; repository
  baseline `--check` passed against exact remote source `9e1ca0f2`.
- The exact remote branch head and source tree were verified after a non-force fast-forward.
- The first evidence-head policy run passed 444 of 446 tests and exposed only two assertions for
  the same stale manual operation-catalog source reference. After updating that paired reference,
  the full **446-test** policy/static/dependency/size/baseline/GraphQL/compile/whitespace gate
  passed locally again.

### Verification still required

- Execute the newly added two-connection Odoo/PostgreSQL barrier regressions in CI; local
  scratch has neither Odoo nor PostgreSQL.
- Odoo-backed registry/ORM/security tests, fresh install, warm update, migrations,
  backup/restore, uninstall and measured performance require the coherent remote gate.
- P12 inventory, P13 product export and P14 fulfillment runtime integrations remain before the
  backend foundation is complete.
- V2/P16 production assets remain deliberately unmanifested/inert. Products, Orders,
  Inventory, Fulfillment and Settings production surfaces, all-store health, responsive/RTL/
  accessibility browser proof and U1-U14 end-to-end journeys remain pending.
- Live Shopify server-to-server readback, latency/SLO measurement, frozen-candidate P17
  qualification, App Store metadata/screenshots/archive scan and P18 rollout remain pending.

### External state (no secrets)

- Odoo build/database alias: no exact-source build result recorded yet; qualification begins
  after this evidence checkpoint is published.
- Shopify test-store alias: no external mutation made in this source/evidence checkpoint.
- Store UI/gateway/runtime modes: V2/P16 production assets remain unmanifested/inert; cumulative
  runtime modes exist in source but are not release-qualified.
- Running/queued/uncertain work: none created.

### Defects and blockers

- No known source-level blocker prevents publishing this P10 checkpoint.
- Runtime qualification is an evidence gap, not an inferred pass: Odoo/PostgreSQL, browser,
  performance and live-Shopify results remain pending until executed on an exact remote SHA.
- Product completion is not release completion: P12-P16 integrations and every U1-U14
  end-to-end journey are still formally pending.
- Near-real-time mechanics exist by design (webhooks, immediate bounded worker drain, scheduled
  reconciliation and adaptive UI polling), but the 15/60-second SLO is unmeasured and must not
  be claimed until exact-SHA load and live-store evidence exists.

### Rollback

- Remote source checkpoint `9e1ca0f2cb6017b5031558e4528818090ad854f0` is the exact rollback
  point for this source wave; its tree is independently verified against the local checkpoint.
- Previous remote rollback remains `96114438da1eac7a1f61b8711ccfcb197d6df262`.

### First next action

- Publish and verify this evidence checkpoint, observe the exact-head connector/policy CI gate,
  then continue the next backend vertical slice without rerunning expensive suites prematurely.

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
