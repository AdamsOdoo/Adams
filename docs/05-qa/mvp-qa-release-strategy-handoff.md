# MVP QA Release Strategy — Session Handoff

> Local handoff for this parallel QA/release-readiness planning sprint
> only. **This is not the central research handoff** —
> [`../01-research/research-handoff.md`](../01-research/research-handoff.md)
> is explicitly unchanged by this sprint (see [No conflict with other
> sessions](#no-conflict-with-other-sessions) below).

## Sprint objective

Produce a complete, docs-only QA and release-readiness package for the
Odoo 19 ↔ Shopify Connector MVP — test strategy, foundation and domain
end-to-end test matrices, security/redaction and data-integrity/
idempotency test plans, a go/no-go release-readiness checklist, and
business-readable UAT scenarios — so that when the Task 002 decision/
gate-pack session and the MVP domain-slicing session move forward, the
project already has a reviewed QA plan every future implementation PR can
be tested against, instead of inventing test strategy ad hoc per PR.

## Baseline commit

- Branch: `claude/mvp-qa-release-strategy-s8k3hq` (the session's
  designated branch; created from, and verified to sit exactly at, the
  latest `Shopify-connector`).
- Base commit: `f74aaf204745ce0087733870fe56bdda74bfa79a` — the PR #92
  merge commit ("Credential and connection foundation planning"),
  confirmed via `git rev-parse origin/Shopify-connector` and
  `git merge-base --is-ancestor` before any file was written.
- Confirmed before starting: PR #92 is merged (state `closed`,
  `merged: true`); Task 002 is explicitly "accepted... as the recommended
  next coding task — **not authorized**" per PR #92's own body and per
  [`AR-024`](./architecture-review-log.md); the limited core-only zero-UI
  gate ([`AR-021`](./architecture-review-log.md)) remains the only open
  gate, authorizing Task 001 only (merged, QA-closed).

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

- **Task 002 decision/gate-pack session.** This sprint did not touch, and
  its allowed-files list does not include, any Task 002 decision/gate-pack
  file: not
  [`../07-implementation-plan/task-002-credential-storage-redaction-proposed.md`](../07-implementation-plan/task-002-credential-storage-redaction-proposed.md),
  not
  [`../07-implementation-plan/task-003-api-client-test-connection-proposed.md`](../07-implementation-plan/task-003-api-client-test-connection-proposed.md),
  not
  [`../07-implementation-plan/credential-connection-foundation-task-plan.md`](../07-implementation-plan/credential-connection-foundation-task-plan.md),
  not
  [`../03-architecture/credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md),
  not
  [`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md),
  not [`architecture-review-log.md`](./architecture-review-log.md), and
  not any DEC file. This sprint only **read** those files (required
  by its own "Read first" list) to source accurate test-planning detail —
  it never opens the Task 002/003 implementation gate, never authorizes
  either task, and never proposes a decision on any of Task 003's named
  open points (job-type vocabulary, job-log write path, the
  `payload_hash` nonce, the `SHOP_INACTIVE`/402/423 mapping). Those
  remain exactly as open as the Task 002 session left them.
- **MVP domain-slicing session.** This sprint did not touch, and its
  allowed-files list does not include, any MVP domain-slicing file: not
  [`../04-decisions/DEC-014-master-blueprint-product-customer-sale.md`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md),
  not
  [`../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md`](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md),
  not
  [`../03-architecture/master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md),
  not
  [`../03-architecture/master-blueprint-inventory-fulfillment.md`](../03-architecture/master-blueprint-inventory-fulfillment.md),
  and not
  [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
  This sprint only **read** them to source accurate domain-behavior detail
  for the E2E test matrix — it does not slice, sequence, or scope any
  future domain implementation task, and it resolves no MBQ row (every
  MBQ reference in this package's deliverables quotes the register's
  existing status, never proposes a new one).
- **No overlapping deliverable.** Every file this sprint created is new
  (none existed before this session started) and lives entirely under
  this sprint's own allowed-files list — there is no file both this
  sprint and either of the other two sessions could plausibly write to,
  so a merge conflict at the file level is structurally impossible as
  long as all three sessions honor their own allowed-files lists.
- **No implementation-gate interaction.** This sprint neither opens nor
  advances the limited core-only zero-UI gate, the Task 002 gate, the
  Task 003 gate, or the future UI-implementation gate. It does not start
  Task 002 or Task 003. Confirmed by the validation steps recorded in this
  sprint's own PR description.

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

## Recommended next step

**For ChatGPT:** review this package (all eight files) against the
self-review checklist recorded in this sprint's own PR description, and
against [`pr-review-checklist.md`](./pr-review-checklist.md) §A. If
accepted, this package becomes the standing QA/release-readiness
reference every future implementation task (Task 002 onward, and each
domain slice) is reviewed against — no further action is required to
"activate" it; it is reference documentation, not a gate.

**Exact next-session prompt**, once this PR is reviewed:

> Review the merged MVP QA and release-readiness package
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
> is a QA-package review only, docs-only, no code, no gate opened.
