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

- Recorded at (UTC): `2026-08-31T13:14:43Z`
- Owner/model/chat: Codex GPT-5.6 Sol implementation owner; bounded GPT-5.6 Luna
  implementation and independent-review lenses
- Branch: `codex/v2-continuous-implementation`
- Accepted V1 implementation base SHA: `f77bfcc25e63615e6226dd9a9329f8f943593cb2`
- Approved V2 blueprint source SHA: `3914004e27630b09b211e3d2ee92a8e6d9a0e55e`
- Last completed remote source SHA: `96114438da1eac7a1f61b8711ccfcb197d6df262`
- Exact source tree: `7883b0f519b79043cb966ffcf72b45b2e1213477`
- Equivalent reviewed local source commit: `dc2b0bea3b240103372ceef706c316fb2114175e`
- Evidence SHA: this documentation-only checkpoint immediately following the remote source
  SHA; resolve its exact identity from the branch head to avoid a self-referential commit hash
- Current remote implementation-branch head: this evidence checkpoint after publication
- Candidate frozen: no
- Active wave/task: qualify the exact evidence head once, then implement the first real P10
  product-scan handler over the completed P06/P07 read and claim-fence foundations
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
- Hardened command replay against generation drift and made async P15/V2 reads and commands
  fail closed when navigation, company, store, selection or component context changes.
- Separated durable mutation lineage from mutable job projections; mutation admission validates
  job/attempt/run/store/settings lineage before credential access and again under lock before
  lease creation. Uncertain mutations remain query-only until reconciled.
- Extracted P06 product and sale read documents/gateways and P07 inventory, fulfillment and
  webhook providers behind domain-owned contracts; core no longer dynamically imports optional
  domain Python modules.
- Routed typed P06/P07 calls through purpose-authorized reads, added exact product/sale purpose
  mappings, and preserved the accepted V1 error taxonomy at the integration boundaries.
- Replaced product money floats with validated exact decimal strings.
- Implemented the P10 read-claim transport fence with typed immutable snapshots, ordered
  `job -> attempt -> run -> store -> settings` locks, credential access only after claim proof,
  fresh locked endpoint use and a final proof before lease creation. No lock spans Shopify I/O.
- Closed P11 cumulative-mode, global-blocker, callback-ownership, registry-order and exception-
  classification source defects. P11 runtime qualification still requires Odoo/PostgreSQL.
- Published remote source `96114438da1eac7a1f61b8711ccfcb197d6df262`; its GitHub tree
  `7883b0f519b79043cb966ffcf72b45b2e1213477` is byte-identical to the tested local tree.
- Regenerated the six repository baseline artifacts twice against that exact remote source;
  both runs were byte-identical and the baseline check passed.

### In progress

- Publish this exact-source evidence/handoff as a fast-forward checkpoint and qualify the exact
  remote evidence head through one coherent GitHub CI run.
- Implement the first production P10 product-scan slice: claim-aware page reads, durable
  per-page checkpointing, safe child idempotency and same-run continuation after parent scope
  release. The legacy V1 route must remain unchanged.

### Changed/uncommitted files

- Production source and tests are clean at remote source `96114438`; the reviewed local source
  tree is identical.
- Only `docs/v2/13-continuous-execution-handoff.md` and the six regenerated
  `docs/v2/evidence/` artifacts are intentionally uncommitted at this point. Do not mix new
  production edits into the evidence checkpoint.

### Verification completed

- Complete dependency-free suite: **415 tests passed** on the exact source tree.
- Python compilation and `git diff --check`: passed.
- Static policy, all seven addon dependency-direction policies and changed-production-file
  size policy: passed.
- Shopify GraphQL schema validation: **48 documents passed** against Admin API `2026-07`
  using pinned `graphql-core==3.2.6` in a temporary dependency directory.
- Focused corrected-claim review: 43 tests passed; no remaining claim-fence lock-order,
  endpoint-snapshot, MRO/import-order, schema, credential-before-authorization or tenant-
  isolation defect was found.
- Deterministic evidence generation: two independent runs were byte-identical; repository
  baseline `--check` passed against exact remote source `96114438`.
- Existing remote connector suite `33331564061` and V2 policy `33331564058` passed at the
  earlier checkpoint `7fa08b8`; the new exact evidence head still requires CI.

### Verification still required

- The first real P10 domain handler is not implemented. The claim fence is intentionally
  dormant until a handler propagates immutable claimed work through each remote read and local
  page commit; do not describe P10 as end-to-end complete before that proof.
- Odoo-backed registry/ORM/security/concurrency tests, fresh install, warm update, migrations,
  backup/restore, uninstall and measured performance require CI/Odoo.sh because local Odoo and
  PostgreSQL are unavailable.
- P10 production reads plus P12 inventory, P13 product export and P14 fulfillment runtime
  integrations remain before the backend foundation is complete.
- V2/P16 production assets remain deliberately unmanifested/inert. Products, Orders,
  Inventory, Fulfillment and Settings production surfaces, all-store health, responsive/RTL/
  accessibility browser proof and U1-U14 end-to-end journeys remain pending.
- Live Shopify server-to-server readback, latency/SLO measurement, frozen-candidate P17
  qualification, App Store metadata/screenshots/archive scan and P18 rollout remain pending.

### External state (no secrets)

- Odoo build/database alias: no new build created for source `96114438`; exact-head remote
  qualification begins after the evidence checkpoint is published.
- Shopify test-store alias: no external mutation made in this checkpoint.
- Store UI/gateway/runtime modes: V2/P16 production assets remain unmanifested/inert; cumulative
  runtime modes exist in source but are not release-qualified.
- Running/queued/uncertain work: none created.

### Defects and blockers

- No known source-level blocker prevents publishing this extraction/safety checkpoint.
- The absence of a real P10 product handler is a deliberate next-gate functional gap, not a
  completed capability. Product/sale claim propagation must be proven end to end there.
- Product completion is not release completion: P10/P12-P16 integrations and every U1-U14
  end-to-end journey are still formally pending.
- Near-real-time mechanics exist by design (webhooks, immediate bounded worker drain, scheduled
  reconciliation and adaptive UI polling), but the 15/60-second SLO is unmeasured and must not
  be claimed until exact-SHA load and live-store evidence exists.
- Local scratch lacks PostgreSQL/Odoo. Unavailable runtime evidence must stay pending rather
  than being inferred from dependency-free tests.

### Rollback

- Remote source checkpoint `96114438da1eac7a1f61b8711ccfcb197d6df262` is the exact rollback
  point for this source wave; its tree is independently verified against the local checkpoint.
- Previous remote rollback remains `5cc812296b26e81deaa5fb0c41c7626485fe4e83`.

### First next action

- Publish and verify this evidence checkpoint, observe one exact-head connector/policy CI gate,
  then implement the P10 product-scan slice without rerunning expensive suites prematurely.

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
