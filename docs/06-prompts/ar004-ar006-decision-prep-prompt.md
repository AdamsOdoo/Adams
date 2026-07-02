# Archived Prompt — AR-004 + AR-006 Decision Preparation

> Archived verbatim per this sprint's own instruction ("Archive this prompt").
> This is the session prompt used to run the **AR-004 + AR-006 Decision
> Preparation** sprint (2026-07-02), executed on branch
> `claude/ar004-ar006-decision-prep-y9t8j2` (harness-assigned; preferred
> branch name was `architecture/ar004-ar006-decision-prep`). See
> [`../01-research/research-handoff.md`](../01-research/research-handoff.md)
> for the compact handoff produced by this session.

---

You are Claude, an AI assistant designed to help with GitHub issues and pull
requests. Think carefully as you analyze the context and respond appropriately.
Your task is to complete the request described in the task description.

Instructions:
1. For questions: Research the codebase and provide a detailed answer
2. For implementations: Make the requested changes, commit, and push

## Session rule

Start a fresh Sonnet session.
Do not rely on previous chat context.
Read the required repo files listed below.
Work only through GitHub files.
Stop after opening one draft PR.
Do not merge.

This is a documentation / architecture-decision-preparation sprint.
It is not an implementation sprint.

## Current repo status

PR #63 has been merged into `Shopify-connector`.

Expected PR #63 merge commit:
3ca0cdec168b60cae6c4b1004fa6f7532333a0f9

Before editing:

1. Confirm latest `Shopify-connector` contains merge commit:
   3ca0cdec168b60cae6c4b1004fa6f7532333a0f9
2. Confirm DEC-003, DEC-004, DEC-005, DEC-006, and DEC-007 are accepted.
3. Confirm RA-001 through RA-010 are binding rejected approaches.
4. Confirm AR-002, AR-003, and AR-005 are accepted.
5. Confirm AR-004 and AR-006 are still not decided.
6. Confirm AR-007 and AR-008 remain not decided.
7. Confirm implementation is still blocked.

If PR #63 is not merged into `Shopify-connector`, stop and report exactly:

Blocked: PR #63 is not merged into Shopify-connector.

Do not continue on a stale branch.

## Branch policy

- `main` is stable only.
- Plain `dev` must not be touched.
- `Shopify-connector` is the dedicated project integration branch.
- Create this sprint branch from latest `Shopify-connector`.
- PR target must be `Shopify-connector`.
- Do not open a PR into `main`.
- Do not open a PR into plain `dev`.
- Do not merge.

Preferred branch name:

architecture/ar004-ar006-decision-prep

If the harness assigns a `claude/...` or `sonnet/...` branch, use that branch and record the branch-name discrepancy in the handoff.

## Objective

Prepare proposed architecture decisions for:

1. AR-004 — module boundaries / addon family strategy.
2. AR-006 — error handling, retry, idempotency, and failure taxonomy.

This sprint should create decision-ready documentation that lets ChatGPT and Fable review whether AR-004 and AR-006 can be accepted.

Do not implement anything.
Do not create Odoo modules.
Do not write Python/XML/CSV/security/manifest files.
Do not create implementation tasks.
Do not authorize implementation.

## Accepted decisions to respect

- DEC-003 — accepted MVP scope.
- DEC-004 — accepted API / auth / distribution strategy.
- DEC-005 — accepted sync orchestration strategy.
- DEC-006 — accepted binding / dedup / identity strategy.
- DEC-007 — accepted Phase 1 scope-clarification addendum.

You may reference these decisions.
Do not rewrite them.

## Decisions still open

- AR-004 — module boundaries.
- AR-006 — full retry/error/idempotency taxonomy.
- AR-007 — full inventory architecture.
- AR-008 — full fulfillment architecture.

This sprint may propose decisions for AR-004 and AR-006 only.

Do not decide AR-007 or AR-008.
Do not create DEC records for AR-007 or AR-008.
Do not start Master Blueprint.

## Required read before editing

Read these first:

- CLAUDE.md
- README.md
- docs/01-research/research-handoff.md
- docs/05-qa/quality-feedback-loop.md
- docs/05-qa/defect-pattern-log.md
- docs/05-qa/architecture-review-log.md
- docs/05-qa/rejected-approaches-log.md
- docs/05-qa/pr-review-checklist.md
- docs/06-prompts/session-handoff-template.md
- docs/06-prompts/claude-learning-rules.md

Accepted decisions:

- docs/04-decisions/DEC-003-mvp-scope.md
- docs/04-decisions/DEC-004-distribution-api-auth-strategy.md
- docs/04-decisions/DEC-005-sync-orchestration-strategy.md
- docs/04-decisions/DEC-006-binding-dedup-identity-strategy.md
- docs/04-decisions/DEC-007-phase1-scope-clarifications.md
- docs/04-decisions/README.md

Architecture and product context:

- docs/03-architecture/README.md
- docs/03-architecture/architecture-decision-framing.md
- docs/03-architecture/phase1-domain-model-brief.md
- docs/03-architecture/ar002-ar003-ar005-evidence-refresh.md
- docs/03-architecture/rb14-decision-candidate-brief.md
- docs/02-product/mvp-scope.md
- docs/02-product/non-mvp-and-later-phases.md
- docs/02-product/user-stories.md
- docs/02-product/product-vision.md
- docs/02-product/setup-ux-principles.md
- docs/02-product/feature-taxonomy.md
- docs/02-product/capability-evidence-map.md

Research context:

- docs/01-research/shopify-official-api-notes.md
- docs/01-research/odoo-official-architecture-notes.md
- docs/01-research/competitor-feature-matrix.md
- docs/01-research/common-patterns.md
- docs/01-research/best-in-class-observations.md
- docs/01-research/gaps-opportunities.md
- docs/01-research/avoid-list.md

## External research rule

Default: repo-local only.

Do not browse broadly.

You may do a small targeted official-source check only if a decision-critical AR-004 or AR-006 claim cannot be grounded in existing repo docs.

Allowed official checks only:

- Odoo official docs or source for addon/module dependency behavior, manifest dependency behavior, link-module conventions, transaction/savepoint/error behavior, cron behavior, and logging behavior.
- Shopify official docs for rate limits/throttling, webhook delivery, webhook IDs, idempotent mutations, GraphQL userErrors, and retry-related behavior.

No competitor/vendor re-research.
No marketplace research.
No forum/blog reliance.
No broad web research.

If you do not verify a fact, mark it:

Open question / must be verified before implementation

## AR-004 focus — module boundaries / addon family

Prepare a proposed module-boundary strategy for a premium Odoo 19 Shopify connector.

The proposal must respect:

- No one giant connector module.
- No premature over-fragmentation.
- Features must be modular, enableable, disableable, removable, and extendable safely.
- Phase 1 must remain small but excellent.
- Reliability, logs, retries, duplicate prevention, clean setup, and UX are first-class.
- No dependency on `adams_base` unless explicitly justified and accepted later.
- Odoo.sh / on-prem are the target substrate; Odoo Online custom modules are excluded.
- Public App Store packaging is not Phase 1.

Evaluate and propose:

1. Minimum Phase 1 addon family.
2. Later addon family.
3. Dependency direction.
4. Which capabilities belong in core vs product vs sale/order vs inventory vs fulfillment vs accounting/refund/payout/multi-store later.
5. Link-module strategy if needed.
6. Where queue/job/log/binding abstractions live.
7. Where setup wizard/readiness/dashboard live.
8. Where Shopify API client / GraphQL transport lives.
9. Where mapping configuration lives.
10. How to avoid circular dependencies.
11. How to keep inventory and fulfillment architecture open while still allowing module boundaries to be proposed.
12. How to keep future app-store/public packaging path open without making it Phase 1.

Expected direction to evaluate, not blindly accept:

Phase 1 likely includes:
- `shopify_connector_core`
- `shopify_connector_product`
- `shopify_connector_sale`
- `shopify_connector_inventory`
- `shopify_connector_fulfillment`

Possible Phase 1 inclusion or split to evaluate:
- `shopify_connector_customer`
  - Is customer import/matching better inside sale for Phase 1, or a separate module?
- `shopify_connector_dashboard`
  - Is dashboard/log UX inside core, or separate?
- `shopify_connector_payment_evidence`
  - Is financial evidence inside sale, or separate from accounting?

Likely later:
- `shopify_connector_accounting`
- `shopify_connector_refund`
- `shopify_connector_payout`
- `shopify_connector_multi_store`
- `shopify_connector_markets`
- `shopify_connector_metafield`
- `shopify_connector_pos`
- `shopify_connector_b2b`
- `shopify_connector_app_store`

Do not treat this list as final unless the analysis supports it.

## AR-006 focus — error/retry/idempotency taxonomy

Prepare a proposed retry/error/idempotency strategy that works with accepted DEC-005 and DEC-006.

The proposal must respect:

- Webhooks fast-ack then enqueue.
- Internal queue/job model.
- `ir.cron` workers.
- Manual sync.
- Scheduled reconciliation.
- Per-record isolation.
- User-friendly logs.
- Retry failed jobs.
- Dead/final-failed handling.
- Binding/dedup identity model.
- No duplicate creation.
- No double inventory adjustment.
- No double fulfillment.
- No double invoice/payment artifact.
- No hidden destructive writes.

Define a Phase 1 taxonomy for:

1. Job sources:
   - webhook
   - manual sync
   - scheduled sync
   - reconciliation
   - setup/readiness check
   - export preview/dry-run

2. Job states:
   - draft / queued / running / succeeded / retry_waiting / failed_retryable / failed_final / skipped / cancelled / blocked_manual_review
   - adjust names if needed, but define clearly.

3. Error classes:
   - Shopify throttling/rate-limit
   - Shopify temporary/server/network
   - Shopify permission/scope/auth
   - Shopify userErrors / validation errors
   - Odoo validation/configuration
   - mapping missing
   - ambiguous match
   - binding conflict
   - duplicate risk
   - destructive-write guard blocked
   - inventory location missing
   - fulfillment notification confirmation missing
   - financial total mismatch
   - data shape/schema mismatch
   - concurrency/race conflict
   - unknown/system error

4. Retry behavior:
   - automatic retry
   - no automatic retry
   - manual fix then retry
   - skip
   - dead/final failed
   - operator confirmation required

5. Idempotency layers:
   - webhook dedup by Shopify webhook ID
   - Shopify object identity / GID
   - store-scoped binding key
   - internal job idempotency key
   - Shopify `@idempotent` mutation key where official docs require it
   - reconciliation safety
   - manual retry safety
   - preview/dry-run no-write safety
   - total-check guard for financial artifacts
   - first-inventory-push confirmation record
   - fulfillment notification setting record

6. Retry limits and backoff:
   - propose conceptual behavior, not code constants unless source-supported.
   - Avoid claiming exact numbers unless verified.
   - Use "implementation-planning default" where exact constants are not yet decided.

7. User-facing log requirements:
   - readable error reason
   - related store / Shopify object / Odoo record / binding / job source
   - suggested fix
   - retry action
   - skip/manual-match action where applicable
   - technical details available but not primary
   - no stack trace as the user-facing message

8. Audit requirements:
   - what was attempted
   - what was written
   - what was skipped
   - who confirmed destructive/first-push/notification actions
   - source-of-truth record
   - before/after where needed for destructive operations

Do not create code.
Do not define database DDL.
Do not define exact Python classes.
Conceptual model is okay.
Exact schema remains later.

## Required outputs

Create these files:

1. `docs/03-architecture/ar004-module-boundary-decision-brief.md`

Purpose:
- Evidence-backed decision brief for AR-004.
- Must separate accepted decision, proposed decision, inference, official fact, and open question.
- Must include options considered.
- Must include recommended proposed approach.
- Must include rejected or weakened alternatives.
- Must explain Phase 1 modules and later modules.
- Must explain dependency direction.
- Must explain what remains open.

2. `docs/03-architecture/ar006-error-retry-idempotency-decision-brief.md`

Purpose:
- Evidence-backed decision brief for AR-006.
- Must separate accepted decision, proposed decision, inference, official fact, and open question.
- Must include taxonomy tables.
- Must include options considered.
- Must include recommended proposed approach.
- Must include rejected or weakened alternatives.
- Must explain what remains open.

3. `docs/04-decisions/DEC-008-module-boundary-strategy.md`

Purpose:
- Proposed decision record for AR-004.
- Status must be:

`Proposed for ChatGPT review`

DEC-008 must include:
- Status
- Date: 2026-07-02
- Scope
- Accepted context
- Decision proposed
- Phase 1 addon family
- Later addon family
- Dependency rules
- Link-module strategy
- Why this is not one giant module
- Why this is not over-fragmented
- What remains open
- Risks and mitigations
- Explicit statement: no implementation authorized until ChatGPT accepts this decision and later opens the implementation gate

4. `docs/04-decisions/DEC-009-error-retry-idempotency-strategy.md`

Purpose:
- Proposed decision record for AR-006.
- Status must be:

`Proposed for ChatGPT review`

DEC-009 must include:
- Status
- Date: 2026-07-02
- Scope
- Accepted context
- Decision proposed
- Error taxonomy
- Retry taxonomy
- Idempotency layers
- User-facing log requirements
- Audit requirements
- What remains open
- Risks and mitigations
- Explicit statement: no implementation authorized until ChatGPT accepts this decision and later opens the implementation gate

5. `docs/04-decisions/README.md`

Update only to index DEC-008 and DEC-009 as Proposed.
Do not mark them accepted.

6. `docs/05-qa/architecture-review-log.md`

Update AR-004 and AR-006 to Proposed for ChatGPT review if and only if DEC-008 and DEC-009 are created.

Do not change AR-007 or AR-008 status.

Add a compact note explaining:
- AR-004 is now proposed via DEC-008.
- AR-006 is now proposed via DEC-009.
- AR-007 and AR-008 remain not decided.
- Implementation remains blocked.

7. `docs/05-qa/rejected-approaches-log.md`

Only add proposed rejected approaches if the decision briefs truly reject an option.

Potential rejected approaches to evaluate:
- One giant `shopify_connector` module.
- Per-feature micro-module explosion for Phase 1.
- Putting queue/log/binding in each domain module separately.
- Retry-everything automatically.
- Never-retry-anything/manual-only recovery.
- User-facing stack traces as primary error UX.
- No idempotency key / binding-first retry strategy.

Mark new rejected approaches as:

`PROPOSED:`

They are not binding until DEC-008 / DEC-009 are accepted by ChatGPT.

Do not duplicate existing RA rows.

8. `docs/01-research/research-handoff.md`

Add compact handoff entry at the top.

9. `docs/06-prompts/ar004-ar006-decision-prep-prompt.md`

Archive this prompt.

## Optional supporting output

Only if needed, create:

- `docs/03-architecture/ar004-ar006-evidence-refresh.md`

Use this only if you perform a small targeted official-source check.

Do not create this file if repo-local evidence is enough.

## Boundaries

This sprint must not:

- decide AR-007 inventory architecture
- decide AR-008 fulfillment architecture
- create exact model fields
- create database constraints
- create Python class names
- create Odoo modules
- create code
- create tests
- start Master Blueprint
- authorize implementation
- modify DEC-003/004/005/006/007
- mark DEC-008/009 accepted
- merge the PR

## Allowed files

Modify only:

- docs/03-architecture/ar004-module-boundary-decision-brief.md
- docs/03-architecture/ar006-error-retry-idempotency-decision-brief.md
- docs/03-architecture/ar004-ar006-evidence-refresh.md only if needed
- docs/04-decisions/DEC-008-module-boundary-strategy.md
- docs/04-decisions/DEC-009-error-retry-idempotency-strategy.md
- docs/04-decisions/README.md
- docs/05-qa/architecture-review-log.md
- docs/05-qa/rejected-approaches-log.md
- docs/05-qa/defect-pattern-log.md only if a real new defect pattern is found
- docs/05-qa/technical-debt-register.md only if real technical debt is introduced
- docs/01-research/research-handoff.md
- docs/06-prompts/ar004-ar006-decision-prep-prompt.md

Do not modify any file outside this list.

## Forbidden files

Do not modify:

- docs/04-decisions/DEC-003-mvp-scope.md
- docs/04-decisions/DEC-004-distribution-api-auth-strategy.md
- docs/04-decisions/DEC-005-sync-orchestration-strategy.md
- docs/04-decisions/DEC-006-binding-dedup-identity-strategy.md
- docs/04-decisions/DEC-007-phase1-scope-clarifications.md
- docs/02-product/mvp-scope.md
- docs/02-product/non-mvp-and-later-phases.md
- docs/02-product/user-stories.md
- docs/01-research/shopify-official-api-notes.md unless creating the optional evidence refresh is impossible without modifying it
- any code file
- any Odoo module file
- any Python/XML/CSV/security/manifest file
- GitHub workflows
- requirements files
- Docker files

## Validation before PR

Confirm:

1. Branch is based on latest `Shopify-connector` containing PR #63 merge commit:
   3ca0cdec168b60cae6c4b1004fa6f7532333a0f9
2. DEC-003/004/005/006/007 were not edited.
3. DEC-008 status is `Proposed for ChatGPT review`, not Accepted.
4. DEC-009 status is `Proposed for ChatGPT review`, not Accepted.
5. AR-004 and AR-006 are proposed only, not accepted.
6. AR-007 and AR-008 remain not decided.
7. RA additions, if any, are marked PROPOSED.
8. No code files changed.
9. Implementation remains blocked.
10. Handoff updated.
11. Prompt archived.

## Commit

Use focused commits:

1. `docs: prepare ar004 module boundary decision`
2. `docs: prepare ar006 reliability decision`
3. `docs: align ar004 ar006 logs and handoff`

Do not squash.

## Draft PR

Open one draft PR into `Shopify-connector`.

PR title:

Propose AR-004 module boundaries and AR-006 reliability strategy

PR body:

## Purpose

Prepare proposed architecture decisions for AR-004 module boundaries and AR-006 error/retry/idempotency strategy after DEC-007 acceptance.

## Base branch

This PR targets `Shopify-connector`, not `main` and not plain `dev`.

## Outputs

- AR-004 module-boundary decision brief
- AR-006 error/retry/idempotency decision brief
- Proposed DEC-008 module-boundary strategy
- Proposed DEC-009 error/retry/idempotency strategy
- Architecture review log update
- Rejected-approaches log update if applicable
- Handoff update
- Prompt archive

## Explicit non-goals

- No connector code
- No Odoo module creation
- No implementation authorization
- No DEC-003/004/005/006/007 edit
- No AR-007 decision
- No AR-008 decision
- No Master Blueprint
- No merge

## Quality checks

- [ ] PR targets `Shopify-connector`
- [ ] PR based on latest `Shopify-connector`
- [ ] PR #63 merge confirmed first
- [ ] DEC-008 status is Proposed for ChatGPT review
- [ ] DEC-009 status is Proposed for ChatGPT review
- [ ] AR-004 proposed only, not accepted
- [ ] AR-006 proposed only, not accepted
- [ ] AR-007/AR-008 not decided
- [ ] DEC-003/004/005/006/007 not edited
- [ ] No code files changed
- [ ] Implementation remains blocked
- [ ] Handoff updated
- [ ] Prompt archived

## Notes for ChatGPT / Fable review

Please review:

1. Does DEC-008 avoid both one-giant-module and over-fragmentation?
2. Are Phase 1 module boundaries commercially useful, maintainable, and realistic?
3. Does DEC-008 preserve AR-007 and AR-008 as open architecture decisions?
4. Does DEC-009 provide a strong enough error/retry/idempotency taxonomy?
5. Does DEC-009 avoid retry-everything and manual-only anti-patterns?
6. Does DEC-009 protect against duplicate products/orders/customers, double inventory writes, double fulfillment, and double financial artifacts?
7. Are the proposed rejected approaches valid and non-duplicative?
8. Is this enough to proceed later to AR-007/AR-008 and UX/operator-flow sprint?

## Final response

After opening the draft PR, respond only:

AR-004 + AR-006 decision-prep sprint completed.

Branch:
<actual branch>

Draft PR:
<PR URL>

PR target:
Shopify-connector

Commits:
- <hash> docs: prepare ar004 module boundary decision
- <hash> docs: prepare ar006 reliability decision
- <hash> docs: align ar004 ar006 logs and handoff

Files changed:
- <list>

DEC-008 status:
Proposed for ChatGPT review

DEC-009 status:
Proposed for ChatGPT review

AR-004 accepted:
No

AR-006 accepted:
No

AR-007/AR-008 decided:
No

DEC-003/004/005/006/007 edited:
No

Code files changed:
No

Implementation authorized:
No

Main modified:
No

Plain dev modified:
No

Stopped as instructed:
Yes
