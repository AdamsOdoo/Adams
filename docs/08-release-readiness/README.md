# 08 — Release Readiness

**Purpose:** release criteria, QA/test gates, and go-live checklists for the
connector.

**What belongs here:** the definition of "done and shippable" — test-coverage
targets, idempotency/duplicate-prevention verification, error-handling and
retry/recovery validation, rate-limit behaviour, security/permission review,
performance under realistic catalog/order volumes, and rollback plans. Ties back
to `../05-qa/pr-review-checklist.md` (section C) and the
`../05-qa/technical-debt-register.md`.

**What does not belong here yet:** release sign-off content — there is nothing
to release during the research phase.

**Current status (refreshed 2026-07-10, OP-25 docs-maintenance — the
previous "Empty" status was stale):** Populated. This directory holds the
UAT/release planning layer: `mvp-uat-scenarios.md` and
`mvp-release-readiness-checklist.md` (planning baselines, merged via
PR #95), plus the post-PR #140 audit package (PR #143, AR-038 Accepted):
`project-readiness-master-audit.md`, `open-points-closure-register.md`,
`implementation-readiness-map.md`, `final-pre-implementation-roadmap.md`,
`uat-readiness-gap-analysis.md`, and this session's
`pre-implementation-readiness-signoff.md` (Proposed, AR-039). **No UAT
scenario has been executed and nothing is releasable yet** (0/15 scenarios
executable per the gap analysis); these are planning/readiness documents
only. Authoritative statuses live in each file's own Status section; this
note refreshes the stale index text only and decides nothing.
