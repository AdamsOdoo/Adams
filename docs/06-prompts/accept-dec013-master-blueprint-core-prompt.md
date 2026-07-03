# Archived Sprint Prompt — DEC-013 Master Blueprint Core Substrate Acceptance Patch

> Archived verbatim per the sprint's own instruction ("Archive this
> prompt"). Executed 2026-07-03 on branch
> `claude/accept-dec013-master-blueprint-nh6ouq` (harness-assigned; the
> prompt's preferred name was
> `product/accept-dec013-master-blueprint-core` — discrepancy recorded in
> `../01-research/research-handoff.md`).

---

```
You are Sonnet 5 working in repository:

AdamsOdoo/Adams

You are the GitHub execution worker.
ChatGPT is the strategic control room and final decision-maker.

Sprint:
DEC-013 Acceptance Patch — Master Blueprint Sprint A Core/Common Substrate

This is documentation-only.
Do not write code.
Do not create Odoo modules.
Do not create Python, XML, CSV, security, manifest, test, or workflow files.
Do not start Sprint B.
Do not start implementation.
Do not merge.

Current required base:
Latest `Shopify-connector` after PR #70 merge.

Expected PR #70 merge commit:
5c44971d1df84d5657da0164bf874b1125aee64f

Before editing, confirm:

1. `Shopify-connector` contains PR #70 merge commit:
   5c44971d1df84d5657da0164bf874b1125aee64f
2. PR #70 is merged into `Shopify-connector`.
3. DEC-013 currently exists and is `Proposed for ChatGPT review`.
4. AR-010 currently exists and is `Proposed for ChatGPT review`.
5. Master Blueprint Part A exists.
6. MBQ-53 and MBQ-54 exist.
7. DEC-003 through DEC-012 are still accepted and must not be edited.
8. Implementation is still blocked.
9. Sprint B has not started.

If any check fails, stop and report the exact blocker.

Create a new branch from latest `Shopify-connector`.

Preferred branch name:
product/accept-dec013-master-blueprint-core

If the harness assigns a different `claude/...` branch, use it and record the discrepancy in the handoff.

Objective:
Accept DEC-013 and AR-010 after ChatGPT review, Fable review, Fable revision, tiny consistency fix, and PR #70 merge.

This patch must record acceptance only.
It must not change architecture substance beyond accepted-status wording and explicit acceptance notes.

Acceptance decision to record:

ChatGPT accepts DEC-013 as the accepted Master Blueprint Sprint A core/common substrate package.

Accepted package includes:

1. Master Blueprint index and sprint structure.
2. Part A core/common substrate blueprint.
3. `shopify_connector_core` module boundary and extension seams.
4. Core configuration-object concepts.
5. Binding abstraction.
6. Job/log/error/retry abstraction.
7. Setup wizard, dashboard, sync center, and error center blueprints.
8. Configuration / feature-flag mechanism direction.
9. Permissions/access blueprint at blueprint level.
10. Cross-module extension rules.
11. Open-questions register MBQ-01 through MBQ-54.
12. UI/UX Screen Design Blueprint requirement before operator-facing screen implementation.

Explicit acceptance points:

A. Binding schema shape:
Accept the Part A §C.8 direction:
- per-domain concrete binding models extending a core abstract binding contract
- cross-domain enumeration / registration seam
- binding-model granularity bound
- single polymorphic table remains not chosen
- this does not reintroduce RA-005 or RA-013

B. Feature-flag mechanism:
Accept the Part A §I.3 direction:
- store-scoped core settings record
- domain modules extend it with their own flags
- not global `ir.config_parameter` storage
- not transient-only `res.config.settings` storage
- not per-domain ad hoc settings models
- execution-time re-check is scoped to fail-safe enablement gating only
- no flag bypasses safety guards

C. Roles / access blueprint:
Accept the Part A §J proposed hierarchy at blueprint level:
- Administrator implies Operator and Reviewer rights
- Operator and Reviewer are siblings
- Auditor is implied by all
- Reviewer remains approval/manual-review focused
- no access CSVs or exact XML IDs are decided
- no connector UI/API surface exposes the stored credential secret after entry
- credential at-rest mechanism remains MBQ-04

D. UI/UX:
Accept that Part D — UI/UX Screen Design Blueprint — is required before implementation of operator-facing screens.
MBQ-53 remains open until that dedicated sprint is completed and accepted.

E. Still open:
Do not resolve all MBQs.
Keep unresolved items open where appropriate, especially:
- MBQ-04 credential storage/encryption mechanism
- MBQ-08 store-disconnect data-retention posture
- MBQ-53 screen-level UI/UX design blueprint
- MBQ-54 domain-module uninstall / disable data lifecycle
- exact model/field/view/security identifiers
- implementation planning details
- domain blueprint questions for Sprint B/C

Required file updates:

1. Update:
docs/04-decisions/DEC-013-master-blueprint-core-substrate.md

Required meaning:
- Status becomes:
  Accepted by ChatGPT
- Acceptance date:
  2026-07-03
- Record that acceptance happened after:
  - PR #70 merged into `Shopify-connector`
  - merge commit `5c44971d1df84d5657da0164bf874b1125aee64f`
  - Fable review returned ACCEPT WITH MINOR CHANGES
  - Fable revision and tiny consistency fix were applied before merge
- Add or update an `Accepted decision` section.
- Preserve no-implementation language.
- Make clear acceptance of DEC-013 does not open implementation.
- Make clear Sprint B is next recommended but not started.
- Make clear Part D UI/UX Screen Design Blueprint is required before operator-facing implementation.

2. Update:
docs/03-architecture/master-blueprint.md

Required meaning:
- Status becomes accepted through DEC-013.
- Replace only relevant status text from `Proposed for ChatGPT review` to accepted wording.
- Preserve implementation blocked.
- Preserve Part B/C/D/E not started.
- Preserve the rule that blueprint acceptance does not authorize code.
- Do not create new architecture substance.

3. Update:
docs/03-architecture/master-blueprint-core-substrate.md

Required meaning:
- Status becomes accepted through DEC-013.
- Replace only relevant status text from `Proposed for ChatGPT review` to accepted wording.
- Keep claim labels clear:
  - accepted prior DEC content remains accepted
  - blueprint proposals accepted by DEC-013 can be marked as accepted via DEC-013 where appropriate, but do not over-edit the entire document mechanically
- Preserve open questions.
- Preserve implementation blocked.

4. Update:
docs/03-architecture/master-blueprint-open-questions.md

Do not delete questions.

Update only rows that are now resolved or partially resolved by DEC-013 acceptance:

- MBQ-07:
  Mark the blueprint-level direction as resolved by DEC-013 acceptance:
  store-scoped core settings record, domain-extended.
  Keep exact technical implementation details for implementation planning if needed.

- MBQ-11:
  Mark resolved by DEC-013 acceptance:
  per-domain concrete binding models extending a core abstract contract, with cross-domain enumeration/registration seam and binding granularity bound.

- MBQ-45:
  Mark partially resolved by DEC-013 acceptance:
  proposed role hierarchy accepted.
  Keep exact group decomposition / XML IDs / admin-vs-functional-user screen split open if still needed.

- MBQ-47:
  Mark resolved by DEC-013 acceptance:
  Reviewer remains approval/manual-review focused, not a general retry/trigger role.

Do not mark MBQ-04, MBQ-08, MBQ-53, or MBQ-54 resolved.

5. Update:
docs/04-decisions/README.md

Required meaning:
- DEC-013 moves from Proposed to Accepted by ChatGPT.
- Date:
  2026-07-03
- No changes to DEC-003 through DEC-012.

6. Update:
docs/05-qa/architecture-review-log.md

Required meaning:
- AR-010 becomes Accepted by ChatGPT via DEC-013.
- Acceptance date:
  2026-07-03
- Preserve AR-002 through AR-009.
- Update status column and notes consistently.
- Keep no-implementation language if present.

7. Update:
docs/01-research/research-handoff.md

Add compact handoff entry at top.

Required meaning:
- PR #70 merged into `Shopify-connector`.
- Merge commit:
  5c44971d1df84d5657da0164bf874b1125aee64f
- DEC-013 accepted by ChatGPT.
- AR-010 accepted by ChatGPT.
- Master Blueprint Part A accepted.
- Binding schema shape accepted as per-domain concrete models on core abstract contract with enumeration seam and granularity bound.
- Feature-flag direction accepted as store-scoped core settings record, domain-extended.
- Role hierarchy accepted at blueprint level; Reviewer remains manual-review approval focused.
- UI/UX Screen Design Blueprint remains required before operator-facing implementation.
- MBQ-53 and MBQ-54 remain open.
- No code files changed.
- Implementation remains blocked.
- Sprint B not started.
- Next recommended sprint:
  Master Blueprint Sprint B — Product, Customer, and Sale/Order Domain Blueprint

Also append a compact Sprint checkpoint log note at the bottom.

8. Create:
docs/06-prompts/accept-dec013-master-blueprint-core-prompt.md

Archive this prompt.

Allowed files only:

- docs/04-decisions/DEC-013-master-blueprint-core-substrate.md
- docs/03-architecture/master-blueprint.md
- docs/03-architecture/master-blueprint-core-substrate.md
- docs/03-architecture/master-blueprint-open-questions.md
- docs/04-decisions/README.md
- docs/05-qa/architecture-review-log.md
- docs/01-research/research-handoff.md
- docs/06-prompts/accept-dec013-master-blueprint-core-prompt.md

Do not modify anything else.

Forbidden:
- Do not modify DEC-003 through DEC-012.
- Do not modify product/customer/sale/inventory/fulfillment domain blueprint files.
- Do not create Sprint B files.
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

1. Branch is based on latest `Shopify-connector` containing PR #70 merge commit:
   5c44971d1df84d5657da0164bf874b1125aee64f
2. DEC-013 is accepted by ChatGPT.
3. DEC-013 acceptance date is 2026-07-03.
4. AR-010 is accepted by ChatGPT.
5. AR-010 acceptance date is 2026-07-03.
6. Master Blueprint Part A status is accepted through DEC-013.
7. MBQ-07 is resolved at blueprint-direction level, with implementation detail still open if needed.
8. MBQ-11 is resolved by DEC-013.
9. MBQ-45 is partially resolved, with exact group/surface details still open if needed.
10. MBQ-47 is resolved by DEC-013.
11. MBQ-04 remains open.
12. MBQ-08 remains open.
13. MBQ-53 remains open.
14. MBQ-54 remains open.
15. DEC-003 through DEC-012 were not edited.
16. No code files changed.
17. No product/customer/sale/inventory/fulfillment detailed domain blueprint started.
18. Implementation remains blocked.
19. Sprint B has not started.
20. Handoff updated.
21. Prompt archived.

Commit:

Use one commit:
docs: accept dec013 master blueprint core substrate

Open one draft PR into:
Shopify-connector

PR title:
Accept DEC-013 Master Blueprint core substrate

PR body:

Purpose:
Accept DEC-013 after ChatGPT/Fable review and PR #70 merge.

Outputs:
- DEC-013 accepted by ChatGPT
- AR-010 accepted by ChatGPT
- Master Blueprint Part A accepted
- Binding schema shape accepted
- Feature-flag direction accepted
- Role hierarchy / Reviewer boundary accepted at blueprint level
- UI/UX Screen Design Blueprint remains required before operator-facing implementation
- MBQ statuses updated only where DEC-013 resolves or partially resolves them
- Handoff updated
- Prompt archived

Explicit non-goals:
- No connector code
- No Odoo model/view/security implementation
- No implementation authorization
- No DEC-003 through DEC-012 edit
- No Sprint B
- No product/customer/sale/inventory/fulfillment detailed domain blueprint
- No merge

Quality checks:
- PR targets Shopify-connector
- PR based on latest Shopify-connector
- PR #70 merge confirmed first
- DEC-013 accepted by ChatGPT
- AR-010 accepted by ChatGPT
- DEC-003 through DEC-012 not edited
- No code files changed
- Implementation remains blocked
- Sprint B not started
- Handoff updated
- Prompt archived

Final response only:

DEC-013 acceptance patch completed.

Branch:
<actual branch>

Draft PR:
<PR URL>

PR target:
Shopify-connector

Commit:
<hash> docs: accept dec013 master blueprint core substrate

Files changed:
- <list>

DEC-013 accepted:
Yes

DEC-013 acceptance date:
2026-07-03

AR-010 accepted:
Yes

AR-010 acceptance date:
2026-07-03

Master Blueprint Part A accepted:
Yes

MBQ-07 resolved/partially resolved:
Yes

MBQ-11 resolved:
Yes

MBQ-45 partially resolved:
Yes

MBQ-47 resolved:
Yes

MBQ-04 remains open:
Yes

MBQ-08 remains open:
Yes

MBQ-53 remains open:
Yes

MBQ-54 remains open:
Yes

DEC-003/004/005/006/007/008/009/010/011/012 edited:
No

Code files changed:
No

Implementation authorized:
No

Sprint B started:
No

Main modified:
No

Plain dev modified:
No

Stopped as instructed:
Yes
```
