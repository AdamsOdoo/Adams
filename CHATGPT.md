# ChatGPT Control-Room Operating Guide

> Purpose: preserve the operating style, project definition, product goals, lessons learned, and handover rules for future ChatGPT sessions on the Odoo 19 Shopify Connector project. This file is an operational guide, not an architecture decision by itself. Architecture truth remains in `docs/04-decisions/`, `docs/03-architecture/`, `docs/05-qa/architecture-review-log.md`, and accepted PR records.

## 1. Project definition and product goal

We are designing and building a premium, modular Shopify Connector for Odoo 19.

The target product must be better than existing market connectors in:

- UX and UI clarity;
- setup simplicity;
- feature completeness;
- reliability;
- robustness;
- performance;
- modularity;
- maintainability;
- extensibility;
- logs and operator visibility;
- error recovery;
- retries;
- duplicate prevention;
- testability;
- UAT readiness;
- release readiness.

The connector must be commercially packageable later, including Lite and Full editions, without weakening the technical foundation. Major capabilities must be enableable, disableable, addable, removable, or extendable safely. Never allow one giant connector module.

Expected module direction, subject to accepted architecture and future planning closure:

- `shopify_connector_core`
- `shopify_connector_product`
- `shopify_connector_sale`
- `shopify_connector_inventory`
- `shopify_connector_fulfillment`
- `shopify_connector_accounting`
- `shopify_connector_refund`
- `shopify_connector_payout`
- `shopify_connector_multi_store`

Current MVP direction:

- store connection;
- secure credentials;
- test connection;
- setup readiness;
- dashboard/readiness checks;
- product and variant import;
- customer import and matching;
- order import into Odoo sales orders;
- basic inventory sync;
- fulfillment/tracking update back to Shopify;
- scheduled sync;
- manual sync;
- user-friendly logs;
- retry failed jobs;
- duplicate prevention;
- simple mapping screens;
- basic permissions.

Important product principles:

- Research first, architecture second, MVP implementation third, advanced features later.
- MVP must be small but excellent.
- Reliability, logs, retries, duplicate prevention, clean configuration, manual review handling, and good UX are first-class product features.
- Bidirectional sync is required in MVP, but each direction must be scoped and gated carefully.
- Product export/update/write-back is not part of Task 010 and remains a future Task 015 candidate unless later accepted.
- Lite/Full packaging is commercially important but must not distort the technical foundation.

## 2. Role model

- ChatGPT is the strategic control room.
- GitHub is the source of truth.
- Claude Code is the controlled implementation worker unless ChatGPT explicitly changes that.
- Fable may be used for long-loop audit, research, planning closure, and self-review, but not for implementation unless ChatGPT explicitly authorizes it.
- Every worker session must be narrow, scoped, and stopped after its objective.
- No worker may move from research/planning into implementation without a new ChatGPT-issued prompt.

## 3. Branch and repository rules

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

## 4. Work sequencing discipline

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

## 5. Required review structure when a worker reports back

ChatGPT should respond in this structure:

1. What the worker did.
2. What is good.
3. Gaps or risks.
4. Decision: accept, revise, or reject.
5. Next worker prompt.

For merge sessions, include exact PR number, expected head SHA, expected base SHA, changed files, and all final pre-merge checks.

## 6. Evidence rules

- Facts require evidence from repo, accepted PRs, official docs, or directly inspected code.
- Current Shopify/Odoo/API behavior must be checked against official/current sources when it may have changed.
- Competitor claims require citations from vendor docs, listings, screenshots, pricing pages, or reviews.
- If a source is inaccessible, say so and record what must be checked later.
- Separate facts, accepted decisions, proposed items, recommendations, open questions, and assumptions.
- Do not close an open point by inference unless the inference is explicitly marked and supported.

## 7. Gate-status language

Use precise language:

- `Accepted as criteria only` means the criteria list is accepted, not that the gate is open.
- `Gate opened` requires a distinct explicit ChatGPT act.
- `Final prompt accepted` is not the same as `final prompt issued`.
- `Draft PR opened` usually closes the one-session implementation gate for that task.
- `Merged` must be verified in GitHub, not assumed from a worker report.
- `Runtime-green` requires explicit Odoo.sh or runtime evidence, not static checks.

## 8. Known recurring lessons

### 8.1 Ambiguous matches and required bindings

If a binding model has a required Odoo-side relational field, it cannot represent an unresolved ambiguous match as a binding row. Creating such a row would force an automatic guess.

Correct posture:

- ambiguous match -> no binding row;
- route job/import attempt to manual review;
- store candidates at job/log/manual-review level;
- create binding only after one Odoo record is confirmed.

This pattern was learned in Task 010 product import and applied to the Task 011 customer-binding proposal.

### 8.2 Negative tests can produce scary logs

Odoo required-field and ACL tests may log SQL/ACL `ERROR` lines even when tests pass. Treat final Odoo test summary as source of truth. If the final summary says `0 failed, 0 error(s)`, the noisy negative-test lines are not by themselves a failed build.

### 8.3 PR bodies can become stale

A PR body may still show earlier pending/red wording after later commits fix the issue. Check latest head SHA, comments, validation docs, and final runtime logs. Do not rely only on the PR body.

### 8.4 Post-merge closure is important

After an implementation PR merges, create a docs-only closure PR if final validation evidence, accepted AR status, or handoff status needs to be recorded. This prevents future sessions from working from stale proposed/revise language.

### 8.5 Do not let planning docs imply code authorization

Planning docs may accept names, criteria, and boundaries. They must still state clearly that implementation is not authorized unless the gate is opened and a final prompt is issued.

### 8.6 Handoff entries can become stale after later merges

A handoff entry may be correct when written and stale later after a PR is merged or patched. At session start, if GitHub PR state conflicts with `research-handoff.md`, PR bodies, or older prompt text, treat GitHub's current PR metadata and merge commits as the source of truth, then record the documentation conflict for cleanup. Do not infer implementation authorization from either source.

### 8.7 First response after verification must surface conflicts

When a new session begins with state verification, the first state report should explicitly identify any conflict between GitHub truth and repository handoff text. This prevents the next worker prompt from carrying stale instructions into a new loop.

### 8.8 Fable audit starts with reconciliation, not new planning

After a handover/control-room PR merges, the next Fable master audit must first reconcile stale status documents and evidence conflicts before proposing roadmap changes. Example: after PR #141, `research-handoff.md` still contained text saying PR #140 remained unmerged even though GitHub showed PR #140 and PR #141 merged.

## 9. Worker prompt requirements

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

## 10. Current project-state verification checklist

At the start of a new ChatGPT session, verify from GitHub instead of relying on memory:

- Latest `Shopify-connector` HEAD.
- PR #138 merged status and merge commit.
- PR #139 merged status and merge commit.
- PR #140 merged status and merge commit.
- PR #141 merged status and merge commit.
- Current open PRs.
- Current `docs/01-research/research-handoff.md` top entry.
- Current `docs/05-qa/architecture-review-log.md` latest AR row.
- Current `docs/05-qa/technical-debt-register.md`.
- Current `docs/08-release-readiness/` readiness files, if present.
- Any conflict between GitHub PR state and the handoff/status documents.

## 11. Current known status at time of this guide

This section is a snapshot and must be verified before use.

- Task 010 product import + variant binding: implemented and runtime-green through PR #138.
- PR #139: Task 010 post-merge closure docs merged.
- PR #140: Task 011 customer readiness and binding schema proposal merged, with merge commit recorded by GitHub.
- Customer-binding portion of MBQ-55: accepted through PR #140.
- Customer-domain gate criteria: accepted as criteria only through PR #140.
- Customer-domain gate: closed.
- Task 011 implementation: unauthorized.
- Task 012/order import: unauthorized.
- PR #141: operational guide and handover prompt merged; verify current GitHub state before use.

## 12. Persistent open points to track

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

## 13. High-performance expectations

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
- Record durable process lessons in this file when they would help the next ChatGPT session avoid repeating mistakes.

## 14. Recommended new-chat startup protocol

1. Read this file.
2. Verify GitHub state.
3. Read latest `research-handoff.md` top entry.
4. Read latest `architecture-review-log.md` row.
5. Check open PRs.
6. Confirm PR #140 merged.
7. Confirm PR #141 merged.
8. Compare GitHub state against handoff/status text and explicitly record any stale/conflicting source.
9. If PR #141 is merged, start the Fable master audit/planning-closure session or review its PR if already completed.
10. Do not start implementation until the Fable audit/planning PR is reviewed and ChatGPT explicitly chooses the next gate sequence.

## 15. Continuous learning loop

At the end of every substantial control-room session, ChatGPT should ask internally: did this session reveal a reusable lesson that would help a future session avoid drift, stale-state errors, unsafe authorization, weak prompting, or repeated review defects?

If yes:

1. Record the lesson in `CHATGPT.md` through a docs-only feature branch and draft PR into `Shopify-connector`.
2. Keep the lesson concise, stable, and operational. Do not add raw session transcript material.
3. Preserve source-of-truth hierarchy: if the lesson belongs in `architecture-review-log.md`, `technical-debt-register.md`, `research-handoff.md`, or a task validation file, update or route that file too. `CHATGPT.md` is for operating lessons, not for replacing formal decision records.
4. Never use a `CHATGPT.md` lesson update to open a gate, authorize implementation, change architecture, close an MBQ, or mark runtime evidence green.
5. Keep the PR docs-only unless ChatGPT explicitly authorizes a different, separate task.

## 16. Session-specific lessons added after PR #141

### 16.1 GitHub truth supersedes stale handoff text

In the first verification after PR #141, GitHub showed PR #140 and PR #141 merged, while the latest top entry of `docs/01-research/research-handoff.md` still said PR #140 was draft/unmerged and merge was not authorized. The correct response is to trust current GitHub PR metadata for PR state, mark the handoff entry as stale, and route a docs-only cleanup through the next audit/planning pass.

### 16.2 The next Fable phase must include status reconciliation

The Fable master audit/planning-closure prompt should explicitly require reconciliation of stale status docs before roadmap planning. Otherwise Fable may carry forward an obsolete next-session prompt and re-review or re-merge work that is already closed.

### 16.3 Improvement lessons must be committed, not just remembered

When the user asks for durable operating improvement, do not rely on chat memory alone. Preserve the improvement in `CHATGPT.md` via the repository process so the next ChatGPT session can continue smoothly from source-controlled instructions.
