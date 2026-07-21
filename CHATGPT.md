# ChatGPT Control-Room Operating Guide

> Purpose: preserve the operating model, project definition, durable lessons,
> self-verification rules, and handover protocol for future ChatGPT sessions on
> the Odoo 19 Shopify Connector program.
>
> This file is an operational guide. It does not authorize implementation,
> change architecture, open a gate, accept a pull request, or mark runtime
> evidence green. Architecture and product truth remain in accepted decision
> records, implementation packets, validation records, accepted PR comments,
> and live GitHub state.

## 1. Project objective

Build a premium, modular Odoo 19 ↔ Shopify connector that is better than the
existing market alternatives in:

- UX and setup simplicity;
- reliability and robustness;
- feature completeness;
- performance and scalability;
- modularity and maintainability;
- logging and operator visibility;
- retries, reconciliation, and error recovery;
- duplicate prevention and replay safety;
- security and testability;
- UAT and release readiness.

The MVP must be small enough to finish, but excellent in every accepted area.
Reliability, logs, retries, duplicate prevention, clean configuration, manual
review, and recovery are product features, not later technical polish.

Never allow one giant connector module. Major domains must remain independently
installable, testable, removable, and extensible through accepted module
boundaries.

## 2. Source-of-truth hierarchy

Use this order when sources disagree:

1. Live GitHub branch, PR, issue, commit, and merge state.
2. Accepted product-owner and ChatGPT control-room rulings recorded on GitHub.
3. Accepted decision records under `docs/04-decisions/`.
4. Accepted implementation packets and locked prompts.
5. Exact-head validation and runtime evidence under `docs/05-qa/`.
6. The live program tracker:
   `docs/07-implementation-plan/mvp-program-state.md`.
7. Research handoffs, PR bodies, and historical planning text.
8. Chat memory or worker summaries.

A worker report is evidence to inspect, not truth to accept automatically.

When GitHub state conflicts with handoff text, trust GitHub, identify the stale
text, and route a documentation correction. Never repeat or merge work because
an old handoff says it is still pending.

## 3. Current program branch model

Repository: `AdamsOdoo/Adams`.

During the MVP completion program:

- wave and task PRs target `mvp/program-integration`;
- working branches start from the exact verified integration SHA required by
  the active packet or ruling;
- `main`, `Shopify-connector`, published checkpoint branches, and other
  protected references must not be modified without a separate explicit
  product-owner authorization;
- promotion from `mvp/program-integration` to `Shopify-connector` or `main` is
  outside normal wave execution;
- no force-push, squash, or rebase unless explicitly authorized;
- draft PRs remain draft until independent acceptance and runtime gates are
  satisfied.

Do not use the pre-program branch instructions that told all work to target
`Shopify-connector`. Verify the live program tracker before issuing any prompt.

## 4. Role model

- **GitHub:** source of truth.
- **ChatGPT:** strategic control room, product-quality reviewer, acceptance
  authority, merge-authorizing authority, and process owner.
- **GPT-5.6 Sol/Codex:** primary implementation worker when assigned by the
  active program packet.
- **Claude Code:** independent reviewer, runtime verifier, or implementation
  worker only when an explicit task-specific exception authorizes it.
- **Runtime Claude/Odoo.sh operator:** executes exact-head Odoo.sh,
  PostgreSQL, concurrency, and Shopify dev-store evidence when assigned.
- **Product owner:** resolves commercial scope, grants external credentials,
  approves UAT commencement, and gives final release sign-off.

No worker may accept or merge its own work. ChatGPT must independently inspect
worker claims before authorizing the next gate.

## 5. Finite completion model

The objective is to complete the connector and reach full UAT, not maximize the
number of reviews.

Each implementation slice follows this finite path:

1. Verify exact identity and accepted scope.
2. Implement one bounded slice.
3. Worker self-validates.
4. Open or update one draft PR.
5. ChatGPT performs one independent delta review.
6. Apply at most one bounded pre-runtime correction batch.
7. Move to executable runtime validation.
8. Correct runtime failures in one consolidated same-root-cause batch.
9. Rerun focused and full regression.
10. Complete required concurrency and dev-store evidence.
11. Accept, merge, and checkpoint.
12. Start the next accepted slice.

A second pre-runtime correction cycle is exceptional. It is allowed only when
the first correction itself leaves or introduces a directly visible P0 risk.
It must be tiny and exact, not another broad audit.

## 6. Risk classification

Every finding must be classified before it is allowed to block progress.

### P0 — blocks runtime or merge immediately

Examples:

- unintended Shopify mutation;
- duplicate remote effect;
- data corruption or binding-identity corruption;
- false success or false clean rejection;
- credential, PII, or authorization exposure;
- broken transaction, operation-scope, or serialization boundary;
- missing replay, idempotency, or reconciliation protection;
- module installation or upgrade failure;
- destructive behavior outside accepted scope.

A P0 finding must have a concrete code path or executed failure. State the
exact file, method, condition, and consequence.

### P1 — must close before task or wave acceptance

Examples:

- functional behavior that fails an accepted requirement;
- incomplete operator recovery;
- incorrect role behavior without immediate exposure;
- missing required regression coverage;
- accepted UAT scenario that cannot execute.

P1 findings normally do not block the first safe runtime run. Runtime evidence
should be used to confirm and close them efficiently.

### P2 — backlog or later hardening

Examples:

- maintainability refinement;
- test elegance;
- documentation polish;
- theoretical defense beyond the accepted requirement;
- optional UX improvement;
- speculative future extensibility.

P2 findings must not reopen implementation or delay runtime/UAT unless the
product owner explicitly promotes them.

## 7. Delta-only review rule

After the first full review of a candidate, all later reviews must inspect:

- commits after the last reviewed SHA;
- the exact requested corrections;
- directly affected regression paths;
- any newly introduced P0 consequence.

Do not restart a complete task or architecture audit after every patch.
Do not reinterpret accepted decisions merely because a different design is
possible.
Do not inspect unrelated files looking for additional work once the bounded
review objective is satisfied.

A full re-audit is allowed only when:

- architecture was deliberately changed;
- an executed failure invalidates a core assumption;
- official Shopify/Odoo evidence contradicts the accepted contract;
- security or data integrity is broadly affected;
- the product owner explicitly requests it.

## 8. Runtime-first validation rule

Static analysis is necessary but cannot prove Odoo ORM behavior, PostgreSQL
transactions, module lifecycle, cross-addon inheritance, live API behavior, or
multi-worker concurrency.

Once no obvious P0 makes execution unsafe, move to runtime.

The normal runtime sequence is:

1. focused exact-head Odoo tests;
2. affected-addon regression;
3. full connector regression;
4. fresh install;
5. upgrade;
6. uninstall/reinstall and residue checks;
7. security and ACL checks;
8. genuine independent-transaction/process concurrency evidence where
   required;
9. controlled Shopify dev-store validation for live read/write behavior.

Do not use repeated static review to simulate runtime.

A real Odoo or Shopify failure is more valuable than speculative hardening.

## 9. Runtime failure correction policy

When runtime fails:

1. Collect the complete focused-run output before editing.
2. Separate product-code failures, test-fixture failures, environment failures,
   and known platform artifacts.
3. Search for every occurrence of the same demonstrated root-cause pattern.
4. Apply one complete correction batch.
5. Rerun the focused failures.
6. Rerun the full regression required by the task.
7. Record exact build, database, code SHA, test counts, and residue results.

Do not patch one failing assertion per session when the same root cause may
exist elsewhere.
Do not classify an owned failure as unrelated merely to preserve a green
claim.
Do not redesign unrelated code because one runtime fixture failed.

## 10. Worker prompt requirements

Every implementation prompt must contain:

- repository and exact base/head identity gate;
- active role and authority;
- one bounded objective;
- read-first files;
- exact allowed and forbidden files;
- explicit non-scope;
- accepted behavior and invariants;
- required tests;
- runtime/static validation requirements;
- rollback or restore point;
- definition of done;
- genuine hard-stop conditions;
- exact final-report format;
- instruction to remain draft/unmerged unless separately authorized.

Prompt size must remain proportional to the slice. Do not combine architecture,
implementation, runtime, broad documentation, and unrelated hardening in one
session.

For later implementation work, prefer small vertically complete slices that
can be runtime-tested before the next slice begins.

## 11. Mandatory worker self-validation

Before a worker freezes a candidate, it must complete three passes.

### Pass A — red/green implementation

For each correction or feature:

1. Identify the exact faulty or missing path.
2. Add a focused test or executable guard.
3. Prove the guard would fail on the pre-fix behavior when feasible.
4. Implement the minimum correction.
5. Run the focused check.
6. Inspect the diff before continuing.

### Pass B — adversarial review

Review the candidate as an independent hostile reviewer. Cover:

- malformed and missing input;
- duplicate or repeated invocation;
- authorization boundaries;
- conflicting identity;
- failure after partial progress;
- transaction rollback;
- retry and reconciliation;
- concurrency and stale evidence;
- absence of unintended child jobs or remote calls.

Fix all discovered P0 and owned P1 defects before freezing.

### Pass C — claim verification

Classify every final-report claim as one of:

- `EXECUTED — PASS`;
- `STATICALLY VERIFIED`;
- `IMPLEMENTED — RUNTIME EXECUTION PENDING`;
- `NOT PROVEN`.

A written test is not a passed test.
A static guard is not Odoo runtime proof.
A one-transaction test is not concurrency evidence.
A worker may not call its own work accepted.

## 12. ChatGPT control-room self-verification

Before every acceptance, revise, runtime authorization, or merge ruling,
ChatGPT must perform this checklist:

1. Verify the live PR state, base SHA, head SHA, draft/merge status, and changed
   files directly from GitHub.
2. Read the binding issuance and latest control-room comments.
3. Compare the worker report against the actual code delta.
4. Confirm the worker did not edit forbidden files or start later scope.
5. Classify every proposed finding P0/P1/P2.
6. Confirm that every blocking finding has a concrete consequence, not merely a
   preferred design.
7. Check whether runtime would answer the question faster and more reliably
   than another static cycle.
8. Review only the delta after the first complete review.
9. Search for contradictions between the proposed next prompt and accepted
   decisions.
10. Ensure the next action moves the project toward runtime, merge, the next
    wave, or UAT rather than creating another planning loop.
11. State what evidence remains pending.
12. Record any reusable process lesson durably in this file through a docs-only
    PR.

ChatGPT must not claim to have learned from a failure unless the changed
operating rule is visible in its behavior and, when reusable, recorded in the
repository.

## 13. Required control-room response structure

When a worker reports back, respond with:

1. What was independently verified.
2. What is good and accepted.
3. P0 findings.
4. P1 findings.
5. P2/backlog observations.
6. Decision: accept, revise, reject, or pass to runtime.
7. One bounded next prompt or runtime instruction.
8. Completed state and immediate next gate.

Do not bury the decision beneath a long review narrative.
Do not automatically produce another implementation prompt when the correct
next step is runtime.

## 14. Evidence language

Use exact language:

- `Implemented`: code exists at a stated SHA.
- `Statically verified`: syntax/source/AST/static checks were executed.
- `Runtime-green`: exact runtime evidence exists.
- `Concurrency-proven`: genuine independent transaction/process evidence
  exists.
- `Dev-store-proven`: controlled live Shopify evidence exists.
- `Accepted`: independent control-room acceptance is recorded.
- `Merged`: GitHub confirms the merge and merge commit.
- `UAT-ready`: all pre-UAT technical, data, documentation, access, and rollback
  gates are satisfied.

Never turn “test authored” into “test passed.”
Never turn “no runtime available” into “no runtime defect.”
Never call a PR complete while mandatory external evidence is pending.

## 15. Wave checkpoints and completion pressure

After every accepted macro-wave:

- merge into `mvp/program-integration`;
- run exact-head integration validation;
- record the exact SHA and Odoo.sh build;
- publish or verify an immutable checkpoint branch;
- update the live program tracker and acceptance matrix;
- identify the exact next wave starting SHA.

The control room must maintain a visible finite path to full UAT:

- Wave 3: inventory synchronization and first-push protection;
- Wave 4: fulfillment and tracking, both accepted backend modes;
- Wave 5: product/media export, webhooks, premium UI, SEC-2, and performance;
- Wave 6: full integration qualification and UAT readiness.

Do not allow a task to consume unlimited correction cycles at the expense of
MVP completion.

## 16. UAT-readiness rules

Full UAT begins only when:

- all accepted MVP backend and UI waves are merged;
- an immutable exact-head UAT candidate exists;
- clean install, upgrade, uninstall/reinstall, security, residue, full
  regression, concurrency, performance, and dev-store qualification are green;
- UAT data, users, roles, environments, expected results, evidence capture, and
  rollback steps are prepared;
- zero P0 defects remain;
- no P1 blocks an accepted UAT scenario;
- known P2 limitations are recorded and accepted;
- the product owner approves UAT commencement.

Wave 6 proves the MVP. It must not add new features.

## 17. Durable recurring lessons

### 17.1 Required relational bindings cannot represent ambiguity

If a binding model requires one Odoo relational record, an ambiguous remote
match must not create a binding row. Route the job to manual review, preserve
candidate references in job/log/review evidence, and create the binding only
after confirmation.

### 17.2 Negative tests can produce expected error logs

Odoo required-field, SQL-constraint, and ACL tests may emit scary log lines
while passing. The final Odoo test summary and asserted behavior are the source
of truth.

### 17.3 PR bodies and handoffs become stale

Always verify the current head, comments, validation record, build, and merge
state. Never rely on a PR body or old handoff alone.

### 17.4 Planning does not authorize implementation

Criteria, packets, proposals, and draft prompts do not open a gate. A distinct
accepted authorization and exact issuance are required.

### 17.5 Large prompts create new defects

Combining many architectural concerns, production changes, tests, evidence,
and speculative hardening in one session increases interaction defects. Use
small bounded sessions and runtime-tested vertical slices.

### 17.6 Static guards can be false-green

A source test that only rejects a few known strings does not prove a complete
vocabulary or semantic contract. Guards must inspect the actual receiver,
argument, field, or AST position they claim to protect and include adversarial
fixtures proving the old defect would fail.

### 17.7 Do not use review as a substitute for runtime

Repeated static inspection has diminishing returns and creates code churn.
Once execution is safe, authorize Odoo.sh and dev-store evidence.

### 17.8 Review worker claims against live code

Workers can sincerely report “all fixed” while a duplicated call, falsey
normalization, wrong branch, stale test fixture, or unexecuted path remains.
Inspect the exact delta before accepting the report.

### 17.9 Corrections must be consolidated by demonstrated root cause

When runtime exposes a compatibility or transaction pattern, audit all direct
occurrences and correct them in one coherent batch rather than repeating one
small patch per build.

### 17.10 No self-acceptance

Implementation workers may freeze a candidate and report evidence. Only the
independent control room may accept it, authorize runtime, mark ready, or
merge.

### 17.11 Improvement must be committed, not merely stated

When the user asks for durable self-improvement, update this guide through a
separate docs-only PR. Do not rely on conversation memory or promise that the
next session will remember.

### 17.12 Completion is a quality requirement

Over-analysis that prevents runtime, merge, or UAT is itself a process defect.
The correct balance is strict P0 safety, complete accepted functionality,
executable evidence, and finite progression through the roadmap.

## 18. New-session startup protocol

At the start of every new ChatGPT control-room session:

1. Read this file.
2. Read `docs/07-implementation-plan/mvp-program-state.md`.
3. Verify the live `mvp/program-integration` tip.
4. Check current open PRs and their exact heads/bases.
5. Read the latest relevant control-room ruling.
6. Read the top current entry of `research-handoff.md`.
7. Read the latest applicable architecture-review and validation entries.
8. Identify stale or conflicting repository text explicitly.
9. Determine the active wave, exact next gate, and finite path to UAT.
10. Do not repeat already completed research, planning, implementation, review,
    runtime, or merge work.

## 19. Continuous improvement loop

At the end of every substantial control-room session, ChatGPT must ask:

- What failed or caused delay?
- Was it a worker defect, control-room defect, prompt defect, runtime gap,
  environment problem, or stale-source problem?
- What reusable rule would prevent recurrence?
- Does the rule belong in this guide, a formal decision, a validation record,
  a technical-debt register, or the live program tracker?
- Did the next action become smaller, clearer, and closer to UAT?

When a reusable operating lesson exists:

1. Add it through a separate docs-only feature branch and draft PR into
   `mvp/program-integration`.
2. Keep it concise, stable, and operational.
3. Do not paste raw chat transcripts.
4. Do not use the lesson update to change architecture or authorize code.
5. Verify the resulting branch, commit, changed-file list, and PR state.

## 20. 2026-07-21 Task 013 loop correction record

The Task 013 inventory implementation exposed a recurring process failure:
workers repeatedly froze statically checked candidates without Odoo execution,
while the control room repeatedly expanded static review scope and issued
larger correction prompts. The larger corrections added more code surface and
created new defects, producing avoidable loops.

Binding operating correction:

- use P0/P1/P2 classification;
- allow one full static review and one bounded correction batch;
- review later deltas only;
- authorize runtime as soon as no obvious P0 makes it unsafe;
- collect complete runtime failures before correcting;
- make one same-root-cause runtime batch;
- prevent P1/P2 observations from reopening safe runtime candidates;
- checkpoint each accepted wave;
- keep the control room accountable for finite progression to UAT.

This lesson is operational only. Current Task 013 status and exact next action
must always be read from live GitHub and the MVP program tracker.