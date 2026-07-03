# Archived Sprint Prompt — Master Blueprint Sprint A: Core/Common Substrate

> Archived verbatim per the sprint's own instruction ("Archive this
> prompt"). Executed 2026-07-03 on branch
> `claude/master-blueprint-core-substrate-azhp4s` (harness-assigned; the
> prompt's preferred name was `architecture/master-blueprint-core-substrate`
> — discrepancy recorded in `../01-research/research-handoff.md`).

---

```
You are Sonnet 5 working in repository:

AdamsOdoo/Adams

You are the GitHub execution worker.
ChatGPT is the strategic control room and final decision-maker.

Sprint:
Master Blueprint Sprint A — Core/Common Substrate

This is documentation-only.
Do not write code.
Do not create Odoo modules.
Do not create Python, XML, CSV, security, manifest, test, or workflow files.
Do not start implementation.
Do not merge.

Current required base:
Latest `Shopify-connector` after PR #69 merge.

Expected PR #69 merge commit:
305f396bcbd2656a4282ed18c5983540503b5502

Before editing, confirm:

1. `Shopify-connector` contains merge commit:
   305f396bcbd2656a4282ed18c5983540503b5502
2. DEC-003 through DEC-012 are accepted.
3. AR-002 through AR-009 are accepted.
4. Implementation is still blocked.
5. Master Blueprint has not already been started.

If any check fails, stop and report the exact blocker.

Create a new branch from latest `Shopify-connector`.

Preferred branch name:
architecture/master-blueprint-core-substrate

If the harness assigns a different `claude/...` branch, use it and record
the discrepancy in the handoff.

Objective:
Create the first Master Blueprint package for the connector's core/common
substrate.

This sprint must convert accepted decisions into a detailed
implementation-ready blueprint, but still no code.

Scope of this sprint:
- Master Blueprint index and structure
- Core/common module blueprint
- Store connection blueprint
- Credential/security posture blueprint
- Setup wizard blueprint
- Dashboard / command center blueprint
- Sync center / job monitor blueprint
- Error center / recovery blueprint
- Binding/dedup abstraction blueprint
- Job/log/error/retry abstraction blueprint
- Configuration / feature-flag mechanism blueprint
- Conceptual roles converted into blueprint-level access design, but no
  access CSV
- Cross-module dependency and extension rules
- Open questions routed to later domain blueprints or implementation
  planning

Out of scope for this sprint:
- Product domain blueprint
- Customer domain blueprint
- Sale/order domain blueprint
- Inventory domain blueprint
- Fulfillment domain blueprint
- Exact GraphQL operation bodies
- Exact Python method implementation
- Odoo XML view code
- Odoo security CSV code
- Tests
- Implementation tickets
- PR merge

Read first:

- CLAUDE.md
- README.md
- docs/01-research/research-handoff.md
- docs/04-decisions/README.md
- docs/04-decisions/DEC-003-mvp-scope.md
- docs/04-decisions/DEC-004-distribution-api-auth-strategy.md
- docs/04-decisions/DEC-005-sync-orchestration-strategy.md
- docs/04-decisions/DEC-006-binding-dedup-identity-strategy.md
- docs/04-decisions/DEC-007-phase1-scope-clarifications.md
- docs/04-decisions/DEC-008-module-boundary-strategy.md
- docs/04-decisions/DEC-009-error-retry-idempotency-strategy.md
- docs/04-decisions/DEC-010-inventory-architecture-strategy.md
- docs/04-decisions/DEC-011-fulfillment-architecture-strategy.md
- docs/04-decisions/DEC-012-ux-operator-flow-strategy.md
- docs/02-product/ux-operator-flow.md
- docs/03-architecture/ux-operator-flow-architecture-bridge.md
- docs/03-architecture/phase1-domain-model-brief.md
- docs/03-architecture/README.md
- docs/05-qa/architecture-review-log.md
- docs/05-qa/quality-feedback-loop.md
- docs/05-qa/rejected-approaches-log.md
- docs/05-qa/defect-pattern-log.md
- docs/06-prompts/session-handoff-template.md

Do not browse the web unless a decision-critical Odoo 19 official-doc fact
is missing.

If you cannot verify something, mark it:

Open question / must be verified before implementation

Required outputs:

1. Create:
docs/03-architecture/master-blueprint.md

Purpose:
The top-level Master Blueprint index.

Must include:
- status: Proposed for ChatGPT review
- date: 2026-07-03
- relation to accepted DEC-003 through DEC-012
- blueprint scope
- blueprint parts / future sprint structure
- module family overview
- core/common substrate summary
- domain blueprints still pending
- implementation still blocked
- Master Blueprint does not authorize code
- criteria for when implementation may later be opened

2. Create:
docs/03-architecture/master-blueprint-core-substrate.md

Purpose:
Detailed blueprint for the core/common substrate.

Must define, at blueprint level:

A. Module boundary
- Proposed module name:
  shopify_connector_core
- Responsibilities
- What it owns
- What it must not own
- Which modules depend on it later
- Extension rules

B. Core configuration objects
Define blueprint-level model concepts, not code:
- Store / connection
- Credential/token record or secure credential posture
- Shopify API version / health status
- Shopify Location reference/cache
- Feature/domain enablement settings
- Source-of-truth settings
- Notification default settings

For each concept, define:
- purpose
- key fields conceptually
- uniqueness / identity rules
- who can view/edit
- audit/logging expectations
- open questions

C. Binding / identity abstraction
Define:
- common binding purpose
- store-scoped uniqueness
- Shopify GID fields
- Odoo model/res_id link concept
- binding status
- match key used
- manual override fields
- audit fields
- stale/deleted counterpart handling
- why not `ir.model.data` as primary
- how domain modules extend or reuse binding
- no name-only automatic matching

D. Job / queue / log / error abstraction
Define:
- internal cron-backed queue posture from DEC-005/009
- job sources
- job states
- error classes
- retry eligibility concept
- operation-level idempotency concept
- ambiguous outcome handling
- manual review state
- cancellation/supersede concept
- audit requirements
- user-facing log shape
- technical detail shape
- retry safety rules

E. Setup wizard blueprint
Define:
- steps
- readiness checks
- test connection
- setup incomplete state
- no business sync/write before setup complete
- readiness/test/preview jobs allowed during setup if
  read-only/preview-only
- scope list presentation and verification
- source-of-truth choices
- notification default
- inventory first-push scheduling, not execution

F. Dashboard / command center blueprint
Define:
- cards/metrics conceptually
- data source from job/log/error abstraction
- exception-first design
- clickable next actions
- no vanity-only metrics
- role visibility

G. Sync center / job monitor blueprint
Define:
- filters
- list columns
- actions
- retry button rules
- verify-current-state action
- open source record
- open mapping
- cancel/supersede
- operator-safe operation reference

H. Error center / recovery blueprint
Define:
- human reason
- technical detail expandable
- suggested fix
- owner/action state
- related Odoo record
- related Shopify record
- audit trail
- manual review sub-reasons

I. Configuration / feature-flag mechanism blueprint
DEC-008 routed the mechanism itself to Master Blueprint.
Define:
- per-store enabled domains
- per-domain capability flags
- safe enable/disable behavior
- disabling must not delete history
- enabling a domain re-enters domain guard
- no feature toggle should bypass safety guards
- exact technical mechanism may remain open if needed, but propose a clear
  preferred blueprint-level direction

J. Permissions / access blueprint
Convert DEC-012 conceptual roles into blueprint-level access design:
- Connector Administrator
- Connector Operator
- Connector Reviewer / Manual Review Owner
- Read-only Auditor

For each:
- can view
- can configure
- can trigger
- can retry
- can approve manual review
- can see secrets or only masked status
- can audit

Do not create access CSVs.
Do not create exact Odoo group XML IDs unless clearly marked as proposed
names only.

K. Cross-module extension rules
Define how product/sale/inventory/fulfillment modules will use core:
- dependency direction
- no duplicate job/log/binding system per module
- domain-specific extensions allowed
- core must not depend on domain modules
- fulfillment must not depend on inventory
- inventory owns Odoo↔Shopify location mapping
- core may own Shopify Location reference/cache only
- no one giant module

L. Open questions
Must include at least:
- exact Odoo model names
- exact field names
- exact access CSV/group XML IDs
- exact view/menu XML IDs
- exact credential encryption/storage mechanism
- exact cron cadence and throughput limits
- exact technical feature-flag implementation if not finalized
- order-import operator touchpoints
- store-disconnect data-retention posture

3. Create:
docs/03-architecture/master-blueprint-open-questions.md

Purpose:
Central list of unresolved Master Blueprint / implementation-planning
questions.

Must group by:
- core/setup/config
- binding/dedup
- job/log/error/retry
- product/customer/order
- inventory
- fulfillment
- permissions/security
- deployment/operations

Each question must include:
- source document / decision
- why it matters
- decision owner: ChatGPT / later implementation / official-doc
  verification
- whether it blocks implementation

4. Create:
docs/04-decisions/DEC-013-master-blueprint-core-substrate.md

Status:
Proposed for ChatGPT review

Purpose:
Propose acceptance of Master Blueprint Sprint A core/common substrate.

Must include:
- status
- date 2026-07-03
- scope
- accepted context
- proposed decision
- what it decides
- what it does not decide
- open questions
- risks and mitigations
- explicit no-implementation authorization
- next sprint recommendation:
  Master Blueprint Sprint B — Product, Customer, and Sale/Order Domain
  Blueprint

5. Update:
docs/04-decisions/README.md

Index DEC-013 as:
Proposed for ChatGPT review

Do not mark accepted.

6. Update:
docs/05-qa/architecture-review-log.md

Add:
AR-010 — Master Blueprint core/common substrate

Status:
Proposed for ChatGPT review

Do not mark accepted.

7. Update:
docs/01-research/research-handoff.md

Add compact handoff entry at top.

Required meaning:
- PR #69 merged into Shopify-connector with merge commit:
  305f396bcbd2656a4282ed18c5983540503b5502
- DEC-012 accepted
- AR-009 accepted
- Master Blueprint Sprint A started
- Created core/common substrate blueprint package
- DEC-013 proposed only
- AR-010 proposed only
- No code files changed
- Implementation remains blocked
- Next recommended sprint is Master Blueprint Sprint B

8. Create:
docs/06-prompts/master-blueprint-core-substrate-prompt.md

Archive this prompt.

Allowed files only:

- docs/03-architecture/master-blueprint.md
- docs/03-architecture/master-blueprint-core-substrate.md
- docs/03-architecture/master-blueprint-open-questions.md
- docs/04-decisions/DEC-013-master-blueprint-core-substrate.md
- docs/04-decisions/README.md
- docs/05-qa/architecture-review-log.md
- docs/01-research/research-handoff.md
- docs/06-prompts/master-blueprint-core-substrate-prompt.md

Optional only if genuinely needed:
- docs/05-qa/rejected-approaches-log.md
- docs/05-qa/quality-feedback-loop.md

Do not modify anything else.

Forbidden:
- Do not modify DEC-003 through DEC-012.
- Do not modify accepted product scope files.
- Do not modify code files.
- Do not create Odoo module files.
- Do not create Python files.
- Do not create XML files.
- Do not create CSV/security files.
- Do not create manifests.
- Do not create tests.
- Do not start implementation.
- Do not merge.

Validation before PR:

Confirm:
1. Branch is based on latest `Shopify-connector` containing PR #69 merge
   commit:
   305f396bcbd2656a4282ed18c5983540503b5502
2. DEC-013 is Proposed for ChatGPT review, not accepted.
3. AR-010 is Proposed for ChatGPT review, not accepted.
4. DEC-003 through DEC-012 were not edited.
5. No code files changed.
6. Implementation remains blocked.
7. Master Blueprint Sprint A does not authorize implementation.
8. Product/customer/sale/inventory/fulfillment detailed domain blueprints
   are not started.
9. Handoff updated.
10. Prompt archived.

Commit:

Use one commit:
docs: propose master blueprint core substrate

Open one draft PR into:
Shopify-connector

PR title:
Propose Master Blueprint core substrate

PR body:

Purpose:
Create Master Blueprint Sprint A for the Shopify Connector core/common
substrate after DEC-012 acceptance.

Outputs:
- Master Blueprint index
- Core/common substrate blueprint
- Master Blueprint open questions register
- Proposed DEC-013
- AR-010 review-log entry
- Decisions README update
- Handoff update
- Prompt archive

Explicit non-goals:
- No connector code
- No Odoo model/view/security implementation
- No implementation authorization
- No DEC-003 through DEC-012 edit
- No product/customer/sale/inventory/fulfillment detailed domain blueprint
- No merge

Quality checks:
- PR targets Shopify-connector
- PR based on latest Shopify-connector
- PR #69 merge confirmed first
- DEC-013 status is Proposed for ChatGPT review
- AR-010 proposed only, not accepted
- DEC-003 through DEC-012 not edited
- No code files changed
- Implementation remains blocked
- Handoff updated
- Prompt archived
```
