# V2 Continuous Execution Handoff

## Latest access checkpoint — GitHub write restored; public push review blocked

- GitHub now reports `push=true` and `admin=true` for AdamsOdoo/Adams. PR #212 was checked before and after the publication attempt and remains at `1c75c10288477b3a902193797360badc9d2aa06a`.
- Ordinary non-force push of the preserved development branch was rejected by automatic approval review: publishing local history/source to a public repository requires explicit authorization for that public disclosure. This is no longer a GitHub permission failure. Do not bypass via GitHub object APIs or an alternate push route.
- Prepared source checkpoint: `52d90d43c04c16d40027a6955c3f8d6d1302f0af`, seven preserved local commits / 36 changed files against the published head. Payload includes backend fixes, regression tests, AGENTS/skills, blueprint/handoff documents and the two parked design proposal files; publishing them would not constitute design approval. This documentation-only access checkpoint follows that source.
- Publication checks: Lite 289 and Full 444 distribution files validate on the prepared source; aggregate diff whitespace and change-size policy pass. The most recent 455-test local pass still applies to unchanged executable source. Native qualification remains pending. No remote ref or live environment changed.
- Exact next publication action requires explicit user approval of public publication of this preserved payload to `codex/v2-continuous-implementation` / draft PR #212. Then recheck the remote head, use a non-force update, verify the resulting source and inspect matching CI. PR #210/#211 and production/public-release promotion remain outside this action.

## Previous checkpoint — local-only recovery/webhook qualification repair

- User instruction: continue locally while the user resolves GitHub access. No repeated publication attempts or access prompts. UI remains parked. Source parent is `ae5f5b2f66284ff7c370160f8dcd4ff6b6501358`; resolve this local checkpoint with `git rev-parse HEAD`.
- Corrected operational activation fixtures in `TestV2RecoveryCommands`, `TestShopifyConnectorProductWebhookW2` and its independent-cursor generation-race fixture. The latter still commits its isolated fixture and uses the existing genuine two-connection barriers; no concurrency assertion was replaced with a mock. Source admission and lifecycle rules are unchanged.
- Added native regression checks that draft/paused/retired stores cannot enqueue read-only business jobs, with restored-active positive control, and that paused product-webhook delivery admits no product-import child. These new native tests are **not executed** locally.
- Evidence: reviewed the prior exact-head fresh CI failure traces for recovery setup and W2 deliveries entering manual review; traced current runtime enqueue through the P15 activation gate. The recovery RUN-format/translation defects were already fixed in the earlier checkpoint and were not repaired again. Current local dependency-free suite: **455 run, zero failures/errors/skips**; focused recovery contracts **7/7**, changed Python compilation, static policy and diff whitespace pass. Test-only changes do not claim a fresh packaging/native/live pass.
- Old-core W2 investigation: runner `tools/run_connector_suite.sh` deliberately installs origin `7443250ae42a0c3fadba9bf0ef9991e1826b77b5` then W2 alone without upgrading W1. The origin is locally available. Current W2 `pre_init.py` does not expand V2 activation/settings-generation/job-run schema or create the core runtime tables. Core owning post-migrations `19.0.1.31.0` and `19.0.1.32.0` assume ORM-expanded tables/columns. Adding only `activation_state` would advance to another missing-schema failure, not fix compatibility. Do not fabricate runtime tables, change the durable origin, or substitute a dependency upgrade and label it a W2-only pass. This supported mixed-version installation gate remains open for native proof; changing its promise is a material scope decision.
- Access recheck before this local continuation: GitHub repository metadata reported `pull=true`, `push=false`; available installation was NagyWoodCourt, not AdamsOdoo. PR #212 remote head remained `1c75c10288477b3a902193797360badc9d2aa06a`. No external source, database or shop changed.
- Next local work: remaining protected-facade/runtime fixture failures, scoped against raw CI and the current source. When access becomes available, the preceding install/recovery native gates must also include both product-webhook test classes above. Keep old-core migration, real concurrency, live business readback and release qualification explicitly pending.

## Previous checkpoint — bounded recovery and lifecycle repair; UI parked

- Source parent: `e12cfe123110293e2a2fbd5b19280bcadb82a221`, branch `codex/v2-continuous-implementation`. This checkpoint is locally committed only; resolve its hash with `git rev-parse HEAD`. Last verified published head remains `1c75c10288477b3a902193797360badc9d2aa06a`. Preserve all prior commits and PR #210/#211.
- Fixed stale V2 mutation-owner discovery: replace unsupported related-field ORM ordering with a narrow, flushed, parameterized core-owned SQL query. `EXISTS` counts jobs rather than attempts; deterministic `running_since, id` ordering precedes the batch limit. Durable attempt lineage still discovers jobs whose current run/type/token drifted. Existing job/attempt locking and reconciliation-only recovery remain intact. Legacy lock contention now retains the already-processed V2 count.
- Corrected `TestConnectionLifecycle` operational fixtures to represent both connected and active states through the lifecycle service; readiness mocks use the protected readiness service. Activation assertions cover both legitimate audit events. Added explicit negative admission checks for connected-but-draft/paused/retired stores; production admission was not weakened.
- Updated the stale runtime adapter fixture for the current handler registry argument, candidate shape and grouped parent queries. Three dependency-free tests execute the actual query-builder method for registered/removed handler status and missing attempt/settings parents. These are query-contract checks, not database lock proof.
- Verification: consolidated dependency-free suite **455 run / 0 failures / 0 errors / 0 skipped**, with a structured result printed by the lead after final integration (10.594 seconds). Static policy, core dependency policy, change-size policy, changed Python syntax and diff whitespace passed. Lite **289** and Full **444** distribution files passed package validation. Sol's focused mutation-seam suite passed **16/16**; the lead reviewed the actual diff. No native Odoo or real concurrency pass is claimed.
- Native regressions added for oldest-job-before-limit selection despite opposite attempt-ID order, recovery after run/type/token drift without transport replay, and processed-count preservation under legacy contention. Run the complete `/shopify_connector_core:TestMutationRecovery`, `/shopify_connector_core:TestConnectionLifecycle` and `/shopify_connector_core:TestV2RuntimeAdapter` classes on the checkpoint, not just the added tests.
- Still open: old-core W2 stored-schema bridge, remaining lifecycle/protected-facade fixture drift outside this bounded slice, native installation/upgrade/domain/concurrency/live qualification. F2/F3 are not complete. Read-only SQL doubles do not establish installation success or PostgreSQL concurrency behavior.
- External state unchanged: UI proposals remain parked and unapproved; no live store/database changes, no remote ref change. GitHub write was previously rejected with 403 and HTTPS credentials are unavailable; do not retry in a loop or bypass with historical secrets. This workspace has no pinned Odoo/PostgreSQL runtime. Prepared local commits require an authorized repository-write connection before publication and matching native CI/Odoo.sh execution.
- First next action when access is restored: publish the preserved branch checkpoint through the authorized connection, then run fresh Lite/Full installs and the three native classes above together with `/shopify_connector_core:TestV2RuntimeSchema` and `/shopify_connector_core:TestV2RecoveryCommands`. Fix the first native root; prove old-core W2 using its actual fixture and owning migrations. Continue blueprint 16 backend packets, leaving UI parked. Public/production promotion still needs separate authority.
- Rollback: reversible source-only changes on `e12cfe1`, with no database or Shopify effects to undo. Preserve this checkpoint and previous unpublished work; do not reset the branch.

## Previous checkpoint — backend resumed; UI parked

User instruction: keep UI proposals aside until told otherwise; proceed with the rest of development. No UI design or production UI changes are authorized by this continuation. Proposals remain unapproved and preserved.

- Branch: `codex/v2-continuous-implementation`. Published baseline remains `1c75c10288477b3a902193797360badc9d2aa06a`; prior local design checkpoint `4b0bf9d1820b` is unpublished. Resolve current local checkpoint with `git rev-parse HEAD`; the following coherent backend/docs commits carry this update.
- Completed: root AGENTS is the sole repository execution authority below user instructions; CLAUDE/CHATGPT/GPT_SOL compatibility routing updated; three validated repo skills created; delivery blueprint 16 and historical rebaseline/scope documents 14/15 integrated; older 36 UAT scenarios mapped to U1–U14. Read-only Sol forward review identified stale handoff wording, corrected by this checkpoint. Skills are locally committed only, not globally installed or published.
- Code corrections: closed-format RUN names avoid free-text PII redaction; explicit invalid attempt numbers reject while omission allocates; Lite hook skips product-export schema creation/seeding without the export-owned anchor; typed recovery context locals/parameters no longer collide with Odoo translation introspection. Production activation, identity/generation, claim/lock, redaction and uncertain-write fences remain unchanged.
- Tests: consolidated dependency-free suite **450 run / 0 failures / 0 errors / 0 skipped**; changed Python syntax, diff whitespace, static policy, core dependency policy and change-size policy passed. Three skill validators passed. Initial local full-log capture omitted its final summary, so a structured TestResult receipt established the exact count. The only correction during local checking was a source-contract assertion updated for the renamed recovery variable; its generation condition remains intact.
- Native regressions extended: exact RUN identity plus retained free-text redaction, invalid/omitted/duplicate attempt numbers, repeated W2 hook invocation and Lite absence of export columns. Existing native recovery scenarios remain the acceptance gate for translation behavior. None of these native tests has been executed here.
- Still open: old-core W2 stored-schema bridge; lifecycle fixture/service corrections; stale-owner relational ordering; remaining protected facade/adapter assertions; complete native/domain/concurrency/migration/live proof. Do not claim Lite installation or runtime qualification merely because cursor-dispatch tests pass.
- External blockers: GitHub write returns 403 and git HTTPS has no credentials; no remote ref changed. This environment lacks PostgreSQL and pinned Odoo. Matching native CI/Odoo.sh execution requires authorized write/test access. Do not retry publishing in a loop or use historical secrets to bypass missing access.
- Exact first next action: with native execution available, run fresh Lite and Full install plus `/shopify_connector_core:TestV2RuntimeSchema` and `/shopify_connector_core:TestV2RecoveryCommands` on the checkpoint, then fix the first remaining native root. Prove old-core W2 against its actual fixture/owning migrations before broadening the bridge. Continue F2/F3 and domain backend packets in blueprint 16; leave UI parked.
- Rollback: baseline executable source remains 1c75/880e700; new changes are reversible source edits with no live database/shop effects. Preserve all local commits. Production/public release remains frozen and needs separate final authority.

## Earlier September design checkpoint — historical


Latest user steering: proposal 01's visual quality was rejected and the user requested a premium, modern UI with a management dashboard. Proposal 02 (`docs/v2/design-review/proposal-02.html`) is now the current candidate: Management plus separate Operations, revised visual hierarchy, metrics with definitions and observed-data coverage. **Neither proposal is approved.** Read the proposal-02 section of document 17. This restores the August management/dashboard requirement; do not drop it again. DOM-adapter checks passed, native/browser qualification remains pending. GitHub write-access blocker remains unresolved; no remote source change is claimed.

Publication blocker: proposal checkpoint committed locally as `bc3d73c00884d78c39ca336a982880b35d750a48`. Ordinary git push failed because no HTTPS credentials were available; GitHub connector `create_tree` returned HTTP 403, `Resource not accessible by integration`. No remote ref was changed. The design can be reviewed inline now; GitHub write access is needed to publish the prepared checkpoint. Do not claim the proposal is already in GitHub. Subsequent local documentation records this blocker. No browser layout pass: remote preview URL was blocked and local Chromium download timed out. DOM-adapter interaction smoke checks passed; native/browser acceptance remains pending.

The user authorized starting the development program, then explicitly requested an Astra-owned UI redesign for approval. Read [17 Astra design review](./17-astra-ui-design-review.md) before any production UI redesign. The old prototype is historical input; do not interpret its previous approval as approval of the new proposal. Backend repair remains authorized while design is reviewed. No staging/production changes or PR #210/#211 changes are authorized by this update.

- Refreshed PR #212 source head: `1c75c10288477b3a902193797360badc9d2aa06a`, branch `codex/v2-continuous-implementation`; complete checkout verified. PR #210 remains `f77bfcc25e63615e6226dd9a9329f8f943593cb2`; PR #211 remains `3914004e27630b09b211e3d2ee92a8e6d9a0e55e`.
- Fresh local fast baseline: `python -m unittest discover -s tools/tests -p 'test_*.py'` — **448 passed**, 10.796 seconds. This is not a native Odoo runtime pass.
- Sol performed bounded, read-only diagnosis of exact-source native failures. Real roots: Lite hook accesses export-owned schema; old-core W2 bridge omits current stored fields; canonical RUN identifiers are passed through free-text PII redaction; explicit attempt number zero is mistaken for missing; typed recovery `context` collides with Odoo translation introspection. Many lifecycle failures instead come from legacy fixtures that set connected without active activation. Preserve the production admission gate and update sanctioned operational fixtures. Full/migration/native reruns remain required after fixes.
- Native CI evidence and its limitations remain as recorded in the rebaseline review; no correction or post-correction native pass has occurred in this checkpoint.
- Current material edits: proposal 01 and design review/continuity documentation only. Design outcomes are simulated. Baseline rollback remains the source head above.
- Historical next actions superseded by the latest backend checkpoint above. Do not resume design or repeat P10 recovery.
- External state: no fresh Odoo.sh database/source-pin proof or live Shopify journey performed in this checkpoint. Test-store boundary remains `testin-lzhbzhtc.myshopify.com`. Human UAT availability and usage budget remain unconfirmed; these do not block local diagnosis/design.

The August checkpoint below is retained as historical implementation detail. Its “publish P10” wording is stale: source and evidence were already published at the refreshed September head.

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

- Recorded at (UTC): `2026-08-31T23:04:09Z`
- Owner/model/chat: Codex GPT-5.6 Sol implementation owner with an independent local review pass
- Branch: `codex/v2-continuous-implementation`
- Accepted V1 implementation base SHA: `f77bfcc25e63615e6226dd9a9329f8f943593cb2`
- Approved V2 blueprint source SHA: `3914004e27630b09b211e3d2ee92a8e6d9a0e55e`
- Last completed remote source SHA: `880e70088922eb10dd44426678d578ee4ee7a73a`
- Exact source tree: `8ea4e799ea87953c187dc37f25af584b84e3c977`
- Equivalent reviewed local source commit: `24238008e3203760b464228433f6a358a75b8f41`
- Evidence SHA: this documentation-only checkpoint immediately following the remote source
  SHA; resolve its exact identity from the branch head to avoid a self-referential commit hash
- Current remote implementation-branch head: this evidence checkpoint after publication
- Candidate frozen: no
- Active wave/task: publish and qualify the Odoo 19 install-compatibility repair on top of P10,
  then continue P12-P16 domain/runtime and user-journey work in bounded vertical slices
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
- Published the P10 source and then exact repair source
  `880e70088922eb10dd44426678d578ee4ee7a73a`; every uploaded blob matched the
  reviewed local Git object and GitHub produced exact tree
  `8ea4e799ea87953c187dc37f25af584b84e3c977`.
- Corrected the two root failures found by the first full Odoo gate: the run search view now
  follows pinned Odoo 19 RelaxNG attributes, and SEC-3 init-time historic sweeps skip additive
  models whose tables correctly do not exist during the W2-only compatibility probe.
- Added dependency-free regressions for both Odoo 19 contracts, derived from pinned Odoo source
  `30bde9ff758834a4912c5ae55843d3a7dad849f1`.
- Regenerated the six repository baseline artifacts twice against that exact remote source;
  both runs were byte-identical and the baseline check passed.

### In progress

- Publish the regenerated exact-source evidence and handoff, then qualify the resulting remote
  head through one coherent GitHub policy and full Connector/Odoo 19 CI run.
- Continue the remaining backend domain runtime slices only after that checkpoint is coherent;
  do not mix new production code into the evidence commit.

### Changed/uncommitted files

- Production source and tests are clean at remote source `880e7008`; the reviewed local source
  tree is byte-identical.
- Only `docs/v2/13-continuous-execution-handoff.md`, `docs/v2/evidence/README.md`, the operation
  contract catalog and the six regenerated artifacts are intentionally uncommitted. Do not mix
  production edits into this evidence checkpoint.

### Verification completed

- Complete dependency-free suite: **448 tests passed** on the exact source tree.
- Python compilation and `git diff --check`: passed.
- Static policy, all seven addon dependency-direction policies and changed-production-file
  size policy: passed.
- Shopify GraphQL schema validation: **48 documents passed** against Admin API `2026-07`
  using pinned `graphql-core==3.2.6` in a temporary dependency directory.
- Independent diff review found no unsafe mutation path; it caught and closed the wall-clock
  scan-window inversion and source-size violations before publication.
- Deterministic evidence generation: two independent runs were byte-identical; repository
  baseline `--check` passed against exact remote source `880e7008`.
- The exact remote branch head and source tree were verified after a non-force fast-forward.
- The first evidence-head policy run passed 444 of 446 tests and exposed only two assertions for
  the same stale manual operation-catalog source reference. After updating that paired reference,
  the full **446-test** policy/static/dependency/size/baseline/GraphQL/compile/whitespace gate
  passed locally again.
- The repaired evidence head `ec7ff3e` passed the complete remote V2 policy workflow. Its full
  Connector/Odoo 19 run reached the pinned Odoo/PostgreSQL environment and exposed two root
  compatibility failures before normal test execution: invalid legacy search-group attributes
  and an init sweep querying an intentionally absent additive table. Downstream missing-tour and
  zero-migration reports were consequences, not independent defects. Both roots are fixed in
  source `880e7008`; the consolidated **448-test** cheap gate is green.

### Verification still required

- Re-execute the newly added two-connection Odoo/PostgreSQL barrier regressions in CI; local
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

- No known source-level blocker prevents publishing the repaired P10 checkpoint.
- Runtime qualification is an evidence gap, not an inferred pass: Odoo/PostgreSQL, browser,
  performance and live-Shopify results remain pending until executed on an exact remote SHA.
- Product completion is not release completion: P12-P16 integrations and every U1-U14
  end-to-end journey are still formally pending.
- Near-real-time mechanics exist by design (webhooks, immediate bounded worker drain, scheduled
  reconciliation and adaptive UI polling), but the 15/60-second SLO is unmeasured and must not
  be claimed until exact-SHA load and live-store evidence exists.

### Rollback

- Remote source checkpoint `880e70088922eb10dd44426678d578ee4ee7a73a` is the exact rollback
  point for this source wave; its tree is independently verified against the local checkpoint.
- Previous remote source rollback remains `9e1ca0f2cb6017b5031558e4528818090ad854f0`.

### First next action

- Publish and verify this repaired evidence checkpoint, observe the exact-head connector/policy CI gate,
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
