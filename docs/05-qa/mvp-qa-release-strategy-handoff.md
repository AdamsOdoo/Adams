# MVP QA Release Strategy — Session Handoff

> Local handoff for this parallel QA/release-readiness planning sprint
> only. **This is not the central research handoff** —
> [`../01-research/research-handoff.md`](../01-research/research-handoff.md)
> is explicitly unchanged by this sprint (see [No conflict with other
> sessions](#no-conflict-with-other-sessions) below).

## Freshness revision (2026-07-07)

ChatGPT's review of PR #95 returned **REVISE, not reject**: the package
is useful, but it was drafted from the older PR #92 baseline and had
accumulated stale governance/status wording once `Shopify-connector`
moved on. This revision (commit message `docs: refresh QA release
strategy status`) updates status/freshness wording across all 8 files in
this sprint's allowed-files list to reflect that, since the original PR
#95 baseline, `Shopify-connector` has additionally merged:

1. **PR #93** — MVP domain implementation slicing (merge commit
   `ac250f7fd2f242df7b69f78dc619b0a71680c664`) — proposes Tasks 010–014
   for the product/customer/order/inventory/fulfillment domains; does not
   itself gate-open any of them.
2. **PR #94** — Task 002 decision closure / AR-025 accepted (merge commit
   `03ffcb4dc949cd5137b589a6cdc33da9105de31d`) — closed Task 002's three
   remaining decision points and accepted the gate-ready final
   implementation prompt, but did not itself open the gate.
3. **PR #96** — Task 002 credential-storage gate / AR-026 accepted (merge
   commit `02b159a39c58a3396c1c249e80896a05c97bb757`) — **opens** the
   Task 002 credential-storage implementation gate, effective from this
   merge.

**Resulting current state:** Task 002 is no longer merely proposed/not
authorized — its credential-storage implementation gate is **open**, and
the accepted
[`task-002-final-implementation-prompt.md`](../07-implementation-plan/task-002-final-implementation-prompt.md)
may now be issued verbatim in its own coding session. Task 003 remains
**not started and not authorized**. **This revision, like the original
PR #95, still opens no gate and implements no code** — it only refreshes
status wording so the package accurately describes the project's current
state; see [Files created](#files-created) for the unchanged file list
and [No conflict with other sessions](#no-conflict-with-other-sessions)
for why this revision does not touch the Task 002 gate/session files.

## Sprint objective

Produce a complete, docs-only QA and release-readiness package for the
Odoo 19 ↔ Shopify Connector MVP — test strategy, foundation and domain
end-to-end test matrices, security/redaction and data-integrity/
idempotency test plans, a go/no-go release-readiness checklist, and
business-readable UAT scenarios — so that as the Task 002 decision/
gate-pack session and the MVP domain-slicing session move forward
(both now further along, per the freshness revision above), the
project already has a reviewed QA plan every future implementation PR can
be tested against, instead of inventing test strategy ad hoc per PR.

## Baseline commit

- Branch: `claude/mvp-qa-release-strategy-s8k3hq` (the session's
  designated branch; created from, and verified to sit exactly at, the
  latest `Shopify-connector`).
- **Historical original baseline** (PR #95's first commit): base commit
  `f74aaf204745ce0087733870fe56bdda74bfa79a` — the PR #92 merge commit
  ("Credential and connection foundation planning"), confirmed via
  `git rev-parse origin/Shopify-connector` and
  `git merge-base --is-ancestor` before any file was written. Confirmed
  at that time: PR #92 is merged (state `closed`, `merged: true`); Task
  002 was explicitly "accepted... as the recommended next coding task —
  **not authorized**" per PR #92's own body and per
  [`AR-024`](./architecture-review-log.md); the limited core-only zero-UI
  gate ([`AR-021`](./architecture-review-log.md)) was the only open gate,
  authorizing Task 001 only (merged, QA-closed).
- **Current state** (as of this 2026-07-07 freshness revision, confirmed
  via `git merge-base --is-ancestor` against `origin/Shopify-connector`
  before editing): the original baseline commit above remains an ancestor
  of `Shopify-connector`, which has additionally merged PR #93
  (`ac250f7fd2f242df7b69f78dc619b0a71680c664`), PR #94
  (`03ffcb4dc949cd5137b589a6cdc33da9105de31d`), and PR #96
  (`02b159a39c58a3396c1c249e80896a05c97bb757`). **The Task 002
  credential-storage implementation gate is now open** via
  [`AR-026`](./architecture-review-log.md); Task 003 remains **not
  started and not authorized**. This revision's own PR #95 head commit
  before this patch was `9961d421ab250d06d9314be463ba1f62cfcb4f26`.

## Files created

All eight deliverables, all within this sprint's allowed-files list:

1. [`mvp-qa-test-strategy.md`](./mvp-qa-test-strategy.md)
2. [`foundation-test-matrix.md`](./foundation-test-matrix.md)
3. [`domain-e2e-test-matrix.md`](./domain-e2e-test-matrix.md)
4. [`security-redaction-test-plan.md`](./security-redaction-test-plan.md)
5. [`data-integrity-idempotency-test-plan.md`](./data-integrity-idempotency-test-plan.md)
6. [`../08-release-readiness/mvp-release-readiness-checklist.md`](../08-release-readiness/mvp-release-readiness-checklist.md)
7. [`../08-release-readiness/mvp-uat-scenarios.md`](../08-release-readiness/mvp-uat-scenarios.md)
8. This file, `mvp-qa-release-strategy-handoff.md`.

No other file was created or modified. No addon/code file, no Python/XML/
CSV/manifest/test/CI file, and no file outside this exact list was
touched — verified by `git diff --name-only` against the base commit
before commit (see the sprint's own self-review and validation sections
below, reflected in the PR description).

## Key recommendations

- **Adopt the acceptance-evidence-by-task-type table** in
  [`mvp-qa-test-strategy.md`](./mvp-qa-test-strategy.md) as the minimum
  evidence bar for every future implementation PR, in addition to that
  PR's own task-spec acceptance criteria — it exists so no PR can omit an
  entire evidence category (e.g. redaction proof, idempotency proof) by
  oversight.
- **Treat the target-less job repeat-run collision as a release-blocking
  test, not a documentation footnote.** The latent
  `(store_id, idempotency_key)` uniqueness collision for a second
  `setup_readiness_check`/`core_test_connection` run on the same store is
  a named ChatGPT decision point for Task 003 in the accepted architecture
  package; this sprint's
  [`data-integrity-idempotency-test-plan.md`](./data-integrity-idempotency-test-plan.md)
  and
  [`foundation-test-matrix.md`](./foundation-test-matrix.md) both write
  the exact test ("a second run on the same store succeeds") that proves
  Task 003's resolution actually works, so the test exists before the
  code does.
- **Adopt the nine-item release-readiness "must-pass" list literally as a
  merge gate for the MVP release PR**, not as an aspirational checklist —
  each item names concrete evidence a reviewer can demand, mirroring the
  project's existing "no unsupported claims" discipline applied to release
  readiness specifically.
- **Run the 15 UAT scenarios in order 1→15 once a runtime and
  implementation exist**, since later scenarios (12–15) depend on state
  earlier scenarios establish (a connected store with import history) —
  they are written as an ordered sequence, not 15 independent, order-free
  checks.

## Known limitations

- **This package could not execute a single test.** Every test/checklist
  item in this sprint's deliverables is a **future requirement**, not a
  verified result — this repository has no Odoo runtime, no `psycopg2`,
  no PostgreSQL server, and no CI pipeline (re-confirmed unchanged from
  [`task-001-core-runtime-readiness.md`](./task-001-core-runtime-readiness.md)
  at this sprint's baseline). See
  [`mvp-qa-test-strategy.md`](./mvp-qa-test-strategy.md) §Runtime
  limitation strategy.
- **Three of nine planned research extraction passes hit a session usage
  limit mid-sprint** (covering the foundation task specs, the UI/UX final
  design spec, and the MVP user-flows document as parallel-agent
  extractions). All three source documents were subsequently read
  directly instead (in full for the foundation task specs and user-flows
  document; via targeted, cited excerpts for the 1,701-line UI/UX spec,
  covering the Premium Simplicity Standard, the nine-card dashboard, the
  error-center contract, and the 11-step wizard structure). No claim in
  the eight deliverables rests on an unread source — every citation
  traces to a file actually read in this session.
- **Several exact mechanism choices remain genuinely open** at the
  architecture level, and this package deliberately does not resolve
  them: the divergent-currency order's exact error-class/sub-reason
  mapping (DEC-020 residual); the `core_test_connection` job-type
  vocabulary question and its job-log write-path decision (Task 003
  decision points); the exact first-push confirmation-record schema
  (MBQ-38). Where a test description depends on one of these, the test
  is written to assert the *invariant that must hold regardless of which
  option is chosen* (e.g. "the order is blocked before SO creation,"
  not "the order lands in exactly this queue"), so the test plan does not
  need rewriting once ChatGPT decides the mechanism.
- **The four retry UI cases and the nine dashboard cards were sourced from
  two different documents that had to agree with each other** (the UI/UX
  design review checklist's summary and the MVP user-flows document's own
  restatement) — both were checked and found consistent; a future reader
  should still treat
  [`../02-product/ui-ux-final-design-spec.md`](../02-product/ui-ux-final-design-spec.md)
  as the authoritative source if a future discrepancy is ever found,
  since this package only excerpted it rather than reading it in full.

## No conflict with other sessions

- **Task 002 decision/gate-pack session — including its now-merged PR #94
  and PR #96.** Neither the original PR #95 sprint nor this 2026-07-07
  freshness revision touched, or has in its allowed-files list, any Task
  002 decision/gate-pack file: not
  [`../07-implementation-plan/task-002-credential-storage-redaction-proposed.md`](../07-implementation-plan/task-002-credential-storage-redaction-proposed.md),
  not
  [`../07-implementation-plan/task-002-decision-closure.md`](../07-implementation-plan/task-002-decision-closure.md),
  not
  [`../07-implementation-plan/task-002-final-implementation-prompt.md`](../07-implementation-plan/task-002-final-implementation-prompt.md),
  not
  [`../07-implementation-plan/task-002-gate-opening-proposal.md`](../07-implementation-plan/task-002-gate-opening-proposal.md),
  not
  [`../07-implementation-plan/task-002-credential-storage-gate.md`](../07-implementation-plan/task-002-credential-storage-gate.md)
  (PR #96's own gate-opening document), not
  [`task-002-pre-implementation-review-checklist.md`](./task-002-pre-implementation-review-checklist.md),
  not
  [`../07-implementation-plan/task-003-api-client-test-connection-proposed.md`](../07-implementation-plan/task-003-api-client-test-connection-proposed.md),
  not
  [`../07-implementation-plan/credential-connection-foundation-task-plan.md`](../07-implementation-plan/credential-connection-foundation-task-plan.md),
  not
  [`../03-architecture/credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md),
  not
  [`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md),
  not [`architecture-review-log.md`](./architecture-review-log.md), and
  not any DEC file. This sprint (both its original commit and this
  revision) only **read** those files (required by its own "Read first"
  list, and, for this revision, to confirm current gate status) to source
  accurate test-planning detail. **This PR did not open or widen the Task
  002 gate — the Task 002 credential-storage gate opened independently,
  via PR #96/AR-026, a separate session's own merged act.** This revision
  only updates this package's status wording to accurately *reflect* that
  independent gate-opening — it does not perform, repeat, or extend it.
  This QA package remains docs-only throughout and does not start Task
  002: no credential model, field, service method, or redaction utility
  is created by any commit in this PR, including this revision. Task 003
  remains exactly as open (not started, not authorized, its four decision
  points unresolved) as the Task 002 session left it.
- **MVP domain-slicing session — including its now-merged PR #93.**
  Neither the original PR #95 sprint nor this revision touched, or has in
  its allowed-files list, any MVP domain-slicing file: not
  [`../04-decisions/DEC-014-master-blueprint-product-customer-sale.md`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md),
  not
  [`../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md`](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md),
  not
  [`../03-architecture/master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md),
  not
  [`../03-architecture/master-blueprint-inventory-fulfillment.md`](../03-architecture/master-blueprint-inventory-fulfillment.md),
  not
  [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md),
  and not any of PR #93's five new task-spec files (`task-010` through
  `task-014`, `mvp-domain-implementation-sequence.md`,
  `mvp-domain-slicing-handoff.md`,
  `mvp-domain-preimplementation-checklist.md`). This sprint only **read**
  the pre-existing architecture docs to source accurate domain-behavior
  detail for the E2E test matrix — it does not slice, sequence, or scope
  any domain implementation task (PR #93 already did that, independently,
  in its own session), and it resolves no MBQ row (every MBQ reference in
  this package's deliverables quotes the register's existing status,
  never proposes a new one).
- **No overlapping deliverable.** Every file this sprint created is new
  (none existed before the original PR #95 session started) and lives
  entirely under this sprint's own allowed-files list — there is no file
  this sprint and either of the other two sessions could plausibly write
  to, so a merge conflict at the file level is structurally impossible as
  long as all three sessions honor their own allowed-files lists. This
  revision confirms that remains true: PR #93/#94/#96 touched zero files
  from this sprint's allowed-files list, and this revision touches zero
  files from theirs.
- **No implementation-gate interaction, by this PR, at any point.** This
  sprint — neither its original commit nor this freshness revision —
  opens, advances, or widens the limited core-only zero-UI gate, the Task
  002 gate, the Task 003 gate, or the future UI-implementation gate. The
  Task 002 gate that is now open opened via a **different** PR (#96) in a
  **different** session. This PR does not start Task 002 or Task 003.
  Confirmed by the validation steps recorded in this revision's own PR
  description update.

## Learning feedback loop

Per `CLAUDE.md` §12, this section records this session's own learning
observations for
[`quality-feedback-loop.md`](./quality-feedback-loop.md) purposes,
without editing that file (it is not in this sprint's allowed-files
list):

- **Observation.** A 9-agent parallel research fan-out is well-suited to
  extracting facts from a large, already-accepted documentation corpus
  (10,000+ lines across the remaining "read first" files) without
  consuming this session's own context budget reading every line
  directly — but it is exposed to a shared session usage limit that can
  fail a subset of agents mid-run. The recovery path (reading the failed
  agents' source files directly, targeting the specific facts still
  needed via `Grep` for very large files) worked without materially
  affecting the deliverables' accuracy, but cost extra tool calls.
  **Suggested refinement for a future similar sprint:** front-load the
  largest files (the 1,700-line UI/UX spec in this case) as direct reads
  early, rather than delegating them last in a fan-out, since they are
  the most expensive to recover manually if their agent fails.
- **No new defect-pattern-log or rejected-approaches-log entry is
  proposed** — this sprint did not encounter a recurring issue type
  (per the feedback loop's own "count ≥ 2" escalation threshold); the
  session-limit interruption above is an environment/tooling event, not
  a content-quality defect.
- **Observation (2026-07-07 freshness revision).** A docs-only QA
  package with an explicit baseline commit is straightforward to keep
  fresh: because every file already named its baseline SHA and labelled
  every open-item claim, this revision could locate every stale
  "proposed/not authorized" phrase precisely (via targeted `grep`) and
  correct it without re-deriving the whole package from scratch or
  re-reading unrelated source documents. **Suggested refinement:** a
  future long-lived QA package could adopt a single, centrally-cited
  "current state" line (rather than repeating the baseline/status prose
  in each of the 8 files independently) so a future freshness revision
  needs one edit instead of eight — flagged as a possible structural
  improvement for a future sprint, not applied here since it would be a
  substantive restructuring beyond this revision's freshness-only scope.

## Recommended next step

**For ChatGPT:** review this revised package (all eight files) against
the self-review checklist recorded in the original PR #95 description,
this revision's updated PR description, and
[`pr-review-checklist.md`](./pr-review-checklist.md) §A. If accepted,
this package becomes the standing QA/release-readiness reference every
future implementation task is reviewed against — including the now-
gate-opened Task 002 implementation PR (once issued from
[`task-002-final-implementation-prompt.md`](../07-implementation-plan/task-002-final-implementation-prompt.md)
in its own session), Task 003 once its own gate opens, and each PR #93
domain slice once its own gate opens — no further action is required to
"activate" it; it is reference documentation, not a gate.

**Exact next-session prompt**, once this revision is reviewed:

> Review the revised MVP QA and release-readiness package
> (`docs/05-qa/mvp-qa-test-strategy.md`,
> `docs/05-qa/foundation-test-matrix.md`,
> `docs/05-qa/domain-e2e-test-matrix.md`,
> `docs/05-qa/security-redaction-test-plan.md`,
> `docs/05-qa/data-integrity-idempotency-test-plan.md`,
> `docs/08-release-readiness/mvp-release-readiness-checklist.md`,
> `docs/08-release-readiness/mvp-uat-scenarios.md`) against
> `docs/05-qa/pr-review-checklist.md` §A and record the outcome in
> `docs/05-qa/architecture-review-log.md` as a new AR row. Do not start
> Task 002, Task 003, or any domain-slicing work in this session — this
> is a QA-package review only, docs-only, no code, no gate opened. Note
> that the Task 002 credential-storage gate is already open via a
> separate, independent act (AR-026/PR #96) — this review does not open,
> close, or otherwise touch that gate.
