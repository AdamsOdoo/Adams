# Archived Prompt — UX / Operator-Flow Decision Preparation

> Archived verbatim per this sprint's own instruction ("Archive this prompt").
> This is the session prompt used to run the **UX / Operator-Flow Decision
> Preparation** sprint (2026-07-02), executed on branch
> `claude/ux-operator-flow-prep-d12g04` (harness-assigned; preferred branch
> name was `product/ux-operator-flow-decision-prep`). See
> [`../01-research/research-handoff.md`](../01-research/research-handoff.md)
> for the compact handoff produced by this session.

---

You are Claude, an AI assistant designed to help with GitHub issues and pull
requests. Think carefully as you analyze the context and respond appropriately.

You are the GitHub execution worker.
ChatGPT is the strategic control room and final decision-maker.

Sprint:
UX / Operator-Flow Decision Preparation

This is a documentation-only sprint.
Do not write code.
Do not create Odoo modules.
Do not create models, fields, XML views, security files, manifests, tests, or implementation plans.
Do not start the Master Blueprint.
Do not merge.

Current required base:
Latest `Shopify-connector` after PR #67 merge.

Expected PR #67 merge commit:
8798a2454924fd241c8052e2556ea8bca21a7c20

Before editing, confirm:

1. `Shopify-connector` contains merge commit:
   8798a2454924fd241c8052e2556ea8bca21a7c20
2. DEC-003 through DEC-011 are accepted.
3. AR-002 through AR-008 are accepted.
4. RA-001 through RA-023 are binding rejected approaches.
5. Implementation is still blocked.

If any check fails, stop and report the exact blocker.

Branch:
Create a new branch from latest `Shopify-connector`.

Preferred branch name:
product/ux-operator-flow-decision-prep

If the harness assigns a different `claude/...` branch, use it and record the discrepancy in the handoff.

Objective:
Prepare the Phase 1 UX/operator-flow decision package.

The goal is to define how a non-technical Odoo operator will safely configure, run, monitor, recover, and audit the Shopify connector.

Focus on user flows, safe defaults, blocked states, preview/confirmation, logs, retry visibility, manual review, and recovery.

Do not decide exact technical implementation details.

Read first:

- CLAUDE.md
- README.md
- docs/01-research/research-handoff.md
- docs/02-product/product-vision.md
- docs/02-product/setup-ux-principles.md
- docs/02-product/mvp-scope.md
- docs/02-product/non-mvp-and-later-phases.md
- docs/02-product/user-stories.md
- docs/02-product/feature-taxonomy.md
- docs/02-product/capability-evidence-map.md
- docs/03-architecture/phase1-domain-model-brief.md
- docs/03-architecture/ar007-inventory-architecture-decision-brief.md
- docs/03-architecture/ar008-fulfillment-architecture-decision-brief.md
- docs/04-decisions/DEC-003-mvp-scope.md
- docs/04-decisions/DEC-004-distribution-api-auth-strategy.md
- docs/04-decisions/DEC-005-sync-orchestration-strategy.md
- docs/04-decisions/DEC-006-binding-dedup-identity-strategy.md
- docs/04-decisions/DEC-007-phase1-scope-clarifications.md
- docs/04-decisions/DEC-008-module-boundary-strategy.md
- docs/04-decisions/DEC-009-error-retry-idempotency-strategy.md
- docs/04-decisions/DEC-010-inventory-architecture-strategy.md
- docs/04-decisions/DEC-011-fulfillment-architecture-strategy.md
- docs/05-qa/architecture-review-log.md
- docs/05-qa/rejected-approaches-log.md
- docs/05-qa/quality-feedback-loop.md
- docs/06-prompts/session-handoff-template.md

Do not browse the web unless a decision-critical UX fact is missing.
If something is not verified, mark it as:
Open question / must be verified before implementation.

Define UX/operator flows for:

1. Initial setup wizard
   - store connection
   - credentials / OAuth or custom app token posture from DEC-004
   - test connection
   - readiness checks
   - sync direction choices
   - source-of-truth choices
   - fulfillment notification default
   - inventory first-push mode
   - final readiness summary
   - safe incomplete setup state

2. Store settings
   - connection status
   - API health display
   - token status without exposing secrets
   - enabled domains: product, sale/order, inventory, fulfillment
   - source-of-truth settings
   - notification defaults
   - safe defaults

3. Dashboard / command center
   - connection health
   - last successful sync by domain
   - failed jobs by severity
   - manual review count
   - retry waiting count
   - first-push pending count
   - inventory exceptions
   - fulfillment exceptions
   - duplicate/matching exceptions
   - clear next action
   - avoid vanity-only metrics

4. Sync center / job monitor
   - job list
   - domain filter
   - trigger filter: manual, scheduled, webhook, reconciliation
   - status: queued, running, retry_waiting, blocked_manual_review, failed, done, cancelled
   - error class
   - retry eligibility
   - operator-safe idempotency/operation key visibility
   - actions: retry when safe, verify current state, open mapping, open source record, cancel/supersede
   - no blind retry for unsafe cases

5. Error center / recovery flow
   - human-readable reason
   - expandable technical details
   - suggested fix
   - owner/action state
   - related Odoo record
   - related Shopify record if available
   - retry policy explanation
   - manual review reason
   - audit trail

6. Matching / duplicate-prevention flow
   - binding-first match
   - SKU/internal reference
   - barcode
   - manual match
   - name advisory only
   - preview before create/export
   - unmatched / ambiguous / duplicate states
   - operator approval for manual binding
   - audit trail
   - store-scoped uniqueness

7. Product import/export/update flow
   - Shopify to Odoo import
   - Odoo to Shopify export
   - update existing
   - variants/options
   - basic images/media
   - price/compare-at
   - source-of-truth selection
   - preview of creates/updates/skips
   - draft-first export
   - skip/manual-review for ambiguous records
   - no autonomous bidirectional conflict ownership

8. Inventory flow
   - source-of-truth selection
   - Shopify first-sync import preview
   - Odoo to Shopify first-push preview
   - mapped location requirement
   - SKU/variant/location/quantity preview
   - operator confirmation
   - recorded source-of-truth
   - skip/manual-review
   - Shopify `available` as default target
   - `on_hand` warning and Master Blueprint justification requirement
   - `committed` never shown as write target
   - ongoing sync/reconciliation view
   - inventory mismatch handling

9. Fulfillment flow
   - validated picking trigger
   - fulfillment candidate preview
   - matched Shopify order / FulfillmentOrder / line / quantity / location
   - tracking number/carrier display
   - customer notification default off
   - explicit confirmation/enablement for notification
   - notification decision persisted per job
   - block if ambiguous/mismatched
   - verification read before retry for ambiguous outcome
   - no double fulfillment
   - multi-location/multi-package deferred/manual-review posture

10. Permissions / roles concept
   Define conceptually only:
   - Connector Administrator
   - Connector Operator
   - Connector Reviewer / Manual Review Owner
   - Read-only Auditor

Do not define exact Odoo security groups or access CSVs.

Required outputs:

1. Create:
   docs/02-product/ux-operator-flow.md

This is the main UX/operator-flow proposal.

It must:
- define the 10 flows above
- separate accepted decisions, proposed UX decisions, inference, and open questions
- include safe defaults and blocked states
- explicitly say no implementation is authorized

2. Create:
   docs/04-decisions/DEC-012-ux-operator-flow-strategy.md

Status must be:
Proposed for ChatGPT review

It must include:
- status
- date 2026-07-02
- scope
- accepted context
- proposed decision
- setup UX posture
- dashboard posture
- sync/error/retry UX posture
- matching/dedup UX posture
- product flow posture
- inventory flow posture
- fulfillment flow posture
- permissions posture
- what remains open
- risks and mitigations
- no implementation authorization statement

3. Create:
   docs/03-architecture/ux-operator-flow-architecture-bridge.md

Purpose:
Map each UX flow to DEC-003 through DEC-011.
Identify what routes to Master Blueprint.
Identify what must not be implemented yet.

4. Update:
   docs/04-decisions/README.md

Index DEC-012 as:
Proposed for ChatGPT review

Do not mark accepted.

5. Update:
   docs/05-qa/architecture-review-log.md

Add a new row:
AR-009 — UX/operator-flow strategy

Status:
Proposed for ChatGPT review

Do not mark accepted.

6. Update:
   docs/05-qa/rejected-approaches-log.md

Only add new rejected approaches if truly needed.

Do not duplicate existing RA rows:
- RA-008 already rejects blind first inventory push
- RA-009 already rejects hidden/default-on fulfillment notification
- RA-014 already rejects retry-everything automatically
- RA-016 already rejects raw stack trace as primary user error
- RA-023 already rejects fulfillment without proper matching
- DEC-006 already rejects name-only automatic matching

Any new RA rows must be marked:
PROPOSED:

7. Update:
   docs/01-research/research-handoff.md

Add compact handoff entry at the top.

8. Create:
   docs/06-prompts/ux-operator-flow-decision-prep-prompt.md

Archive this prompt.

Allowed files only:

- docs/02-product/ux-operator-flow.md
- docs/03-architecture/ux-operator-flow-architecture-bridge.md
- docs/04-decisions/DEC-012-ux-operator-flow-strategy.md
- docs/04-decisions/README.md
- docs/05-qa/architecture-review-log.md
- docs/05-qa/rejected-approaches-log.md
- docs/01-research/research-handoff.md
- docs/06-prompts/ux-operator-flow-decision-prep-prompt.md

Optional only if useful:
- docs/02-product/ux-flow-checklist.md

Do not modify anything else.

Forbidden:

- Do not modify DEC-003 through DEC-011.
- Do not modify accepted product scope files.
- Do not modify code files.
- Do not create implementation files.
- Do not create tests.
- Do not start Master Blueprint.
- Do not merge.

Validation before PR:

Confirm:
1. Branch is based on latest `Shopify-connector` containing PR #67 merge commit:
   8798a2454924fd241c8052e2556ea8bca21a7c20
2. DEC-012 is Proposed for ChatGPT review, not Accepted.
3. AR-009 is Proposed for ChatGPT review, not Accepted.
4. DEC-003 through DEC-011 were not edited.
5. RA additions, if any, are PROPOSED and non-duplicative.
6. No code files changed.
7. Implementation remains blocked.
8. Handoff updated.
9. Prompt archived.

Commit with two commits:

1. docs: propose ux operator flow strategy
2. docs: align ux flow logs and handoff

Open one draft PR into:
Shopify-connector

PR title:
Propose UX operator-flow strategy

PR body:

Purpose:
Prepare the proposed Phase 1 UX/operator-flow strategy after all AR-002 through AR-008 architecture decisions were accepted.

Outputs:
- UX/operator-flow proposal
- Proposed DEC-012 UX/operator-flow strategy
- Architecture bridge from UX flows to DEC-003 through DEC-011
- AR-009 review-log entry
- Rejected-approaches log update if applicable
- Handoff update
- Prompt archive

Explicit non-goals:
- No connector code
- No Odoo model/view/security implementation
- No implementation authorization
- No DEC-003 through DEC-011 edit
- No Master Blueprint
- No merge

Quality checks:
- PR targets Shopify-connector
- PR based on latest Shopify-connector
- PR #67 merge confirmed first
- DEC-012 status is Proposed for ChatGPT review
- AR-009 proposed only, not accepted
- DEC-003 through DEC-011 not edited
- RA additions, if any, are PROPOSED and non-duplicative
- No code files changed
- Implementation remains blocked
- Handoff updated
- Prompt archived

Final response only:

UX/operator-flow decision-prep sprint completed.

Branch:
<actual branch>

Draft PR:
<PR URL>

PR target:
Shopify-connector

Commits:
- <hash> docs: propose ux operator flow strategy
- <hash> docs: align ux flow logs and handoff

Files changed:
- <list>

DEC-012 status:
Proposed for ChatGPT review

AR-009 accepted:
No

DEC-003/004/005/006/007/008/009/010/011 edited:
No

RA additions proposed only:
Yes / N/A

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
