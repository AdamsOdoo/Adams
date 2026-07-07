# MVP Domain Implementation Slicing — Session Handoff

> Local handoff for this parallel planning sprint only. This document does
> **not** update the central
> [`../01-research/research-handoff.md`](../01-research/research-handoff.md)
> — that file is explicitly out of scope for this session (see
> "Collision warning" below).

## Sprint objective

Prepare a detailed, implementation-ready MVP domain task-slicing package
for the business-connector features that come after the credential/API/
setup foundation (Tasks 002–006): product import, variant import,
customer import/matching, order import into Odoo Sales Orders, inventory
sync, fulfillment/tracking update, scheduled/manual sync behavior, and
dashboard/sync/error-center dependency boundaries — as **proposed future
task specs only**, docs-only, no code, no gate opened, no domain
implementation authorized or started.

## Revision note (PR #93, ChatGPT REVISE)

ChatGPT reviewed this package and returned **REVISE, not reject**. Main
finding: Task 010 over-scoped the first product task by mixing product
import/variant binding with product export/update/write concerns.

Changes made in response:

- **Task 010 narrowed to product import and variant binding only**
  (Shopify → Odoo, read-only against Shopify). All product/variant
  **export, update, and write-back-to-Shopify** content — including
  `productSet`, `productVariantsBulkUpdate`/`productVariantsBulkCreate`,
  the destructive-write guard, and the Product preview/diff (S7) screen
  — was removed from Task 010's scope, acceptance criteria, test
  requirements, and API-call requirements, and replaced with an explicit
  "Future product-write/export task concern" section that documents the
  same risk material strictly as forward-looking, not-authorized
  reference material.
- **Product write/export moved to a separate future candidate task**
  (proposed working name: **Task 015 — Product Write/Update/Export
  Safety**), referenced consistently in
  `mvp-domain-implementation-sequence.md` (Area 1, the
  `shopify_connector_product` domain-boundary bullet, and a new "Future
  task candidates within MVP scope, not yet sliced by this package"
  note under "MVP vs later"), in `task-010-product-import-proposed.md`,
  and in this handoff.
- **`mvp-domain-preimplementation-checklist.md`** gained two new
  `[Gate]` items under Section B: a product-import task must not
  smuggle in export/update/write scope, and any Shopify catalog write
  requires its own separate product-write gate and final §9 task
  prompt.
- Task 011–014 were checked for any dependency on product write/export
  being part of Task 010; none was found, so none of the four were
  changed.
- **No code or gate was opened by this revision.** Every document still
  states "Proposed only. Not authorized." Task 015 is named only as a
  proposed working title for a future candidate task — it is not itself
  proposed at task-spec precision, not authorized, and requires its own
  separate ChatGPT decision/gate before it can even be drafted at that
  level.

## Baseline

- Branch: `claude/mvp-domain-implementation-slicing-2q8pnu`, branched from
  and currently equal to `origin/Shopify-connector` at merge commit
  `f74aaf204745ce0087733870fe56bdda74bfa79a` (PR #92, "Credential and
  connection foundation planning" — confirmed merged before this sprint
  started).
- Note on branch name: the task prompt requested a new branch literally
  named `claude/mvp-domain-implementation-slicing`. This session's
  harness-assigned working branch is
  `claude/mvp-domain-implementation-slicing-2q8pnu` (already present
  locally and on `origin`, already equal to `origin/Shopify-connector`
  HEAD at session start). Per this session's git-operations instructions
  ("never push to a different branch without explicit permission"), this
  session developed and pushed on the assigned branch rather than
  creating a second, separately-named branch. Flagging this explicitly so
  ChatGPT/reviewers are not confused by the branch-name mismatch against
  the literal prompt text.
- Task 002 confirmed **not authorized** at session start (PR #92's own
  body: "Task 002 ... is accepted as the recommended next coding task —
  not authorized by this acceptance") and remains unauthorized throughout
  this session — this session did not touch Task 002/003's files or
  status.

## Files created (8, all within the allowed list)

1. `docs/07-implementation-plan/mvp-domain-implementation-sequence.md`
2. `docs/07-implementation-plan/task-010-product-import-proposed.md`
3. `docs/07-implementation-plan/task-011-customer-import-matching-proposed.md`
4. `docs/07-implementation-plan/task-012-order-import-proposed.md`
5. `docs/07-implementation-plan/task-013-inventory-sync-proposed.md`
6. `docs/07-implementation-plan/task-014-fulfillment-tracking-proposed.md`
7. `docs/05-qa/mvp-domain-preimplementation-checklist.md`
8. `docs/07-implementation-plan/mvp-domain-slicing-handoff.md` (this file)

No other file was created or modified. Confirmed by `git diff
--name-only` / `git status --porcelain` before commit.

## Method note (research grounding)

Six parallel research passes were run over the "read first" file set
(DEC-014/015/016/018/019/020; the corresponding Part B/C/D architecture
docs; `master-blueprint-open-questions.md`; the UI/UX final design spec,
screen inventory, user-flows, and implementation task map; the
credential/API-client architecture package, foundation task plan, Task
002/003 proposed specs, and core-naming-schema-planning; and the four
existing QA checklists), each producing detailed, cited research notes
with no invented Shopify/Odoo platform facts and no MBQ resolved. The
eight deliverables above were then drafted directly from those notes,
citing file/section/DEC/MBQ identifiers throughout rather than asserting
anything not already established in the repository. All research notes
and intermediate drafts are preserved in this session's scratchpad for
traceability; only the eight documents above were committed.

## Key recommendations

- **Proposed MVP domain order:** product/variant binding → customer
  import/matching → order import → inventory sync → fulfillment/tracking
  → manual/scheduled sync hooks → dashboard/sync/error-center operational
  views → MVP release hardening. Rationale, dependencies, risks, and open
  MBQs for each area are in `mvp-domain-implementation-sequence.md`.
- **Foundation dependency is asymmetric, not monolithic:** Task 002/003/004/005
  block *all* domain work; Task 006 (and the UI implementation gate more
  broadly) blocks only UI; Task 003 specifically is the sole blocker on
  *any* outbound Shopify call; a meaningful amount of planning
  (boundary/naming/sequencing work, exactly what this sprint did) can
  proceed today without any of Tasks 002–006 merging.
- **Domain module boundaries** (planning-only proposal, not code
  authorization): `shopify_connector_product`, `shopify_connector_sale`
  (owns **both** order and customer, per DEC-008 — there is no separate
  `shopify_connector_customer` module in the accepted Phase 1 design),
  `shopify_connector_inventory`, `shopify_connector_fulfillment`. Later
  accounting/refund/payout/multi-store modules are explicitly not
  designed by this sprint.
- **MBQ-55** (exact Odoo model/field names for every new binding model
  this sprint's task specs describe by role only) is the single most
  load-bearing open item blocking any of Task 010–014 from reaching
  file-exact §9 precision — the register itself calls for "a dedicated,
  documentation-only domain naming/schema planning pass ... before the
  product/customer/order slice starts."
- **Order import (Task 012) carries the two hardest open residuals**:
  MBQ-56 (total-check tolerance/exact Shopify total field) and MBQ-27
  (no documented Odoo 19 mechanism found for externally-computed tax on
  `sale.order`, verified against official Odoo docs) — both explicitly
  named in the register as blocking the order-import task specifically,
  not merely general open items.

## Proposed task order (also see the sequence document)

1. Task 010 — Product import / variant binding
2. Task 011 — Customer import / matching
3. Task 012 — Order import into Odoo Sales Orders
4. Task 013 — Inventory sync
5. Task 014 — Fulfillment / tracking update
6. (Not yet spec'd this sprint) Manual/scheduled sync hooks — largely a
   cross-domain verification pass over the already-accepted
   `job_source`/`trigger_origin` vocabulary rather than new per-domain
   model work; a candidate for its own future task spec.
7. (Not yet spec'd this sprint) Dashboard/sync/error-center operational
   views — a core/shared UI surface once Areas 1–5 (and their own
   domain-gate + UI-gate acts) exist.
8. (Not yet spec'd this sprint) MVP release hardening — a cross-cutting
   closure pass once Areas 1–7 are merged and reviewed.

Task specs for areas 6–8 were not drafted as standalone documents this
sprint (not in the deliverable list); `mvp-domain-implementation-sequence.md`
covers all eight areas at sequencing/dependency/risk level so a future
session can slice areas 6–8 into their own proposed task specs the same
way this sprint did for 010–014.

## Open questions surfaced or re-confirmed (not resolved by this sprint)

- MBQ-55 (domain binding model/field names) — blocks file-exact task
  specs for every domain area.
- MBQ-56 (order total-check tolerance/exact field) and MBQ-27 (Odoo tax
  representation mechanism) — block Task 012 specifically.
- MBQ-33 (first-push guard granularity) and MBQ-34 (ongoing apply-mode)
  — block Task 013; this sprint found conflicting snapshots across
  research notes about whether DEC-018 already decided these (DEC-015
  itself still labels them "recommendation only") and did not reconcile
  the conflict — a future session should confirm the register's current
  state directly.
- MBQ-32 residual (exact inventory quantity source-selection/aggregation
  mechanism) — blocks Task 013's write code.
- Address handling and company-vs-person (`res.partner.is_company`)
  classification for customers — both genuinely unaddressed gaps in
  DEC-014/Part B, not yet even numbered as MBQs; flagged as new candidate
  open items in the sequence document's "Proposed register impact"
  section (not created as actual register rows by this sprint).
- The "product domain gate" / "sale domain gate" / "inventory domain
  gate" / "fulfillment domain gate" referenced by
  `ui-ux-implementation-task-map.md` as prerequisites are named but their
  own triggering act/conditions are not defined anywhere in the docs read
  for this sprint — flagged as a candidate new open item, not resolved.
- MBQ-29 (fallback-partner granularity) — different research-note
  snapshots describe it differently over time ("partially resolved" vs.
  "resolved via AR-020, naming only open"); not reconciled by this
  sprint.
- **Product write/export scope (new, from the PR #93 revision):** now
  explicitly deferred to a future candidate task (proposed working name
  Task 015), not yet proposed at task-spec precision, and not part of
  this package. Its own open items (MBQ-23 variant-write mutation
  strategy, MBQ-24 `productSet` delete-on-omit-for-media) travel with it
  rather than with Task 010, and remain unresolved.

## Collision warning

This session was scoped and executed to avoid any overlap with the
separate, parallel **Task 002 decision/gate-pack session**:

- No file in the Task 002/003 decision or gate-pack chain was read for
  editing purposes (only read for context, per the "Read first" list) —
  `task-002-credential-storage-redaction-proposed.md`,
  `task-003-api-client-test-connection-proposed.md`,
  `credential-connection-api-client-planning.md`,
  `credential-connection-foundation-task-plan.md`, and
  `credential-security-redaction-review-checklist.md` are all **unchanged**
  by this session (`git diff --stat` confirms zero changes to any of
  them).
- No DEC file (DEC-003 through DEC-020), `docs/04-decisions/README.md`,
  `docs/05-qa/defect-pattern-log.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`, or
  `docs/01-research/research-handoff.md` was touched.
- This sprint does not claim Task 002 or Task 003 is authorized, does not
  start either, and does not open any implementation gate — every new
  document explicitly states "Proposed only. Not authorized."
- If the Task 002 decision/gate-pack session lands a PR before this one
  merges, nothing in this sprint's eight files needs to change — they
  reference Task 002/003 only by their already-recorded status language,
  not by inventing new claims about them.

## Recommended next step

Route this package to ChatGPT for review under the same acceptance
pattern used for AR-023 (UI/UX) and AR-024 (credential/API foundation):
review the proposed MVP domain sequence and the five task specs against
`mvp-domain-preimplementation-checklist.md`, and — if accepted — record
the acceptance at planning level only (no gate opened) in
`architecture-review-log.md`, leaving the actual domain-gate-opening acts
for Task 010–014 as separate, later, explicit acts, exactly as was done
for Task 002/003.
