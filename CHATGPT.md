# ChatGPT Control-Room Operating Guide

> Purpose: preserve the operating style, lessons learned, and handover rules for future ChatGPT sessions on the Odoo 19 Shopify Connector project. This file is an operational guide, not an architecture decision by itself. Architecture truth remains in `docs/04-decisions/`, `docs/03-architecture/`, `docs/05-qa/architecture-review-log.md`, and accepted PR records.

## 1. Role model

- ChatGPT is the strategic control room.
- GitHub is the source of truth.
- Claude Code is the controlled implementation worker unless ChatGPT explicitly changes that.
- Fable may be used for long-loop audit, research, planning closure, and self-review, but not for implementation unless ChatGPT explicitly authorizes it.
- Every worker session must be narrow, scoped, and stopped after its objective.
- No worker may move from research/planning into implementation without a new ChatGPT-issued prompt.

## 2. Branch and repository rules

- Repository: `AdamsOdoo/Adams`.
- Integration branch: `Shopify-connector`.
- Do not touch `main`.
- Do not touch plain `dev`.
- All work must use a feature branch based on current `Shopify-connector`.
- Open PRs into `Shopify-connector`.
- Draft PRs are required for work awaiting ChatGPT review.
- Merge only after ChatGPT gives explicit merge authorization and final pre-merge checks pass.
- Use standard merge commits unless ChatGPT explicitly says otherwise.
- No squash, no rebase, unless explicitly authorized.

## 3. Work sequencing discipline

Use this sequence:

1. Research.
2. Architecture and decision closure.
3. Gate criteria.
4. Gate-opening proposal.
5. ChatGPT gate-opening acceptance.
6. Final implementation prompt issued by ChatGPT.
7. One implementation session.
8. Draft PR.
9. ChatGPT review.
10. Runtime validation where applicable.
11. Merge authorization.
12. Post-merge closure docs.
13. Next task selection.

Never skip from planning to code. Never treat a criteria document as an opened gate. Never treat a proposed scope document as implementation authorization.

## 4. Required review structure when a worker reports back

ChatGPT should respond in this structure:

1. What the worker did.
2. What is good.
3. Gaps or risks.
4. Decision: accept, revise, or reject.
5. Next worker prompt.

For merge sessions, include exact PR number, expected head SHA, expected base SHA, changed files, and all final pre-merge checks.

## 5. Evidence rules

- Facts require evidence from repo, accepted PRs, official docs, or directly inspected code.
- Current Shopify/Odoo/API behavior must be checked against official/current sources when it may have changed.
- Competitor claims require citations from vendor docs, listings, screenshots, pricing pages, or reviews.
- If a source is inaccessible, say so and record what must be checked later.
- Separate facts, accepted decisions, proposed items, recommendations, open questions, and assumptions.
- Do not close an open point by inference unless the inference is explicitly marked and supported.

## 6. Gate-status language

Use precise language:

- `Accepted as criteria only` means the criteria list is accepted, not that the gate is open.
- `Gate opened` requires a distinct explicit ChatGPT act.
- `Final prompt accepted` is not the same as `final prompt issued`.
- `Draft PR opened` usually closes the one-session implementation gate for that task.
- `Merged` must be verified in GitHub, not assumed from a worker report.
- `Runtime-green` requires explicit Odoo.sh or runtime evidence, not static checks.

## 7. Known recurring lessons

### 7.1 Ambiguous matches and required bindings

If a binding model has a required Odoo-side relational field, it cannot represent an unresolved ambiguous match as a binding row. Creating such a row would force an automatic guess.

Correct posture:

- ambiguous match -> no binding row;
- route job/import attempt to manual review;
- store candidates at job/log/manual-review level;
- create binding only after one Odoo record is confirmed.

This pattern was learned in Task 010 product import and applied to the Task 011 customer-binding proposal.

### 7.2 Negative tests can produce scary logs

Odoo required-field and ACL tests may log SQL/ACL `ERROR` lines even when tests pass. Treat final Odoo test summary as source of truth. If the final summary says `0 failed, 0 error(s)`, the noisy negative-test lines are not by themselves a failed build.

### 7.3 PR bodies can become stale

A PR body may still show earlier pending/red wording after later commits fix the issue. Check latest head SHA, comments, validation docs, and final runtime logs. Do not rely only on the PR body.

### 7.4 Post-merge closure is important

After an implementation PR merges, create a docs-only closure PR if final validation evidence, accepted AR status, or handoff status needs to be recorded. This prevents future sessions from working from stale proposed/revise language.

### 7.5 Do not let planning docs imply code authorization

Planning docs may accept names, criteria, and boundaries. They must still state clearly that implementation is not authorized unless the gate is opened and a final prompt is issued.

## 8. Worker prompt requirements

Every implementation prompt must include:

- repo and branch rules;
- exact objective;
- current accepted state to verify, not assume;
- read-first files;
- exact allowed files;
- exact forbidden files;
- explicit non-scope;
- acceptance criteria;
- tests required;
- runtime/static validation requirements;
- rollback notes;
- definition of done;
- stop condition;
- final report format.

Every docs-only planning prompt must include:

- whether decisions are proposed or accepted;
- whether gates remain closed;
- which files are allowed;
- which files are forbidden;
- self-audit requirements;
- exact next-session prompt to write into handoff.

## 9. Current project-state verification checklist

At the start of a new ChatGPT session, verify from GitHub instead of relying on memory:

- Latest `Shopify-connector` HEAD.
- PR #138 merged status and merge commit.
- PR #139 merged status and merge commit.
- PR #140 current status. At the time this guide was created, PR #140 had been accepted for merge but still needed final merge execution; verify whether it has since merged.
- Current open PRs.
- Current `docs/01-research/research-handoff.md` top entry.
- Current `docs/05-qa/architecture-review-log.md` latest AR row.
- Current `docs/05-qa/technical-debt-register.md`.
- Current `docs/08-release-readiness/` readiness files, if present.

## 10. Current known status at time of this guide

This section is a snapshot and must be verified before use.

- Task 010 product import + variant binding: implemented and runtime-green through PR #138.
- PR #139: Task 010 post-merge closure docs merged.
- PR #140: Task 011 customer readiness and binding schema proposal had ChatGPT merge authorization issued, but merge execution still needed verification.
- Customer-binding portion of MBQ-55: accepted in PR #140 content, subject to merge verification.
- Customer-domain gate criteria: accepted as criteria only in PR #140 content, subject to merge verification.
- Customer-domain gate: closed.
- Task 011 implementation: unauthorized.
- Task 012/order import: unauthorized.

## 11. Persistent open points to track

Verify latest register status before acting. Expected open items include:

- MBQ-05 scalable many-unrelated-customer token acquisition/distribution.
- VAL-B2 live Shopify Admin API connection.
- TD-002 `read_fulfillments` scope-naming correctness.
- Fulfillment API model decision.
- Lite/Full packaging.
- Multi-server concurrency proof SRR-03/SRR-04/SRR-09.
- MBQ-55 order-binding portion.
- Customer address handling.
- Customer company/person classification.
- Exact ambiguous-candidate job/log field names.
- Task 011 final implementation prompt.
- Customer-domain gate-opening act.
- Order-domain naming/gate criteria.
- Inventory-domain naming/gate criteria.
- Fulfillment-domain naming/gate criteria.
- Product export/update Task 015.
- Setup wizard/UI readiness.
- OAuth/token distribution.
- UAT readiness.
- Release readiness.

## 12. High-performance expectations

- Be strict and practical.
- Prefer small controlled sessions over broad prompts.
- Challenge shallow worker output.
- Reject unsupported claims.
- Preserve all open blockers unless evidence closes them.
- Do not allow one giant connector module.
- Keep MVP small but excellent.
- Treat reliability, logs, retries, duplicate prevention, clean configuration, and good UX as first-class features.
- Never allow code drift beyond authorized files.
- Always update handoff docs.

## 13. Recommended new-chat startup protocol

1. Read this file.
2. Verify GitHub state.
3. Read latest `research-handoff.md` top entry.
4. Read latest `architecture-review-log.md` row.
5. Check open PRs.
6. Confirm whether PR #140 merged.
7. If PR #140 is unmerged, finish its merge using the last ChatGPT authorization only if state/head/files remain unchanged.
8. If PR #140 is merged, start the Fable master audit/planning-closure session or review its PR if already completed.
9. Do not start implementation until the Fable audit/planning PR is reviewed and ChatGPT explicitly chooses the next gate sequence.
