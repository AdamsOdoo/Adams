# DEC-013 — Master Blueprint Sprint A: Core / Common Substrate

> **Accepted decision record** for the premium **Odoo 19 ↔ Shopify
> Connector**, prepared in **Master Blueprint Sprint A** after DEC-012
> acceptance (2026-07-03) closed the last Phase 1 research-phase-exit
> criterion. Accepts the **Master Blueprint index** and the **core/common
> substrate blueprint (Part A)**. Companion documents:
> [`../03-architecture/master-blueprint.md`](../03-architecture/master-blueprint.md),
> [`../03-architecture/master-blueprint-core-substrate.md`](../03-architecture/master-blueprint-core-substrate.md),
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
> Resolves **AR-010** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> — see [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> for AR-010's acceptance entry.

## Status

**Accepted by ChatGPT.** Acceptance date: **2026-07-03**. Not
implementation-authorizing under any outcome — see *Accepted decision*
below.

> **PR #70 Fable revision (2026-07-03).** Fable reviewed PR #70 and
> returned **ACCEPT WITH MINOR CHANGES**. Applied: a UI/UX Screen Design
> Blueprint (Part D) added to the Master Blueprint sequence and to
> implementation-gate criterion 1 for operator-facing implementation;
> MBQ-53 (screen-level UI/UX design) and MBQ-54 (domain-module
> uninstall/disable data lifecycle) added to the open-questions register;
> the feature-flag execution-time re-check scoped to fail-safe enablement
> gating only (never altering enqueue-time notification/source-of-truth
> decisions); a cross-domain binding-enumeration seam and a binding
> granularity bound added to §C.8; several claim labels corrected
> (§C.4 manual-override extension, §D.13 source-of-truth persistence
> generalization); `ir.cron` wording clarified; credential no-read-back
> wording scoped to a connector-surface guarantee (MBQ-04 unchanged);
> a webhook-topic registration seam added to §A.5. This revision was
> applied before merge; a tiny consistency fix (AR-010's MBQ range) was
> also applied before merge.

> **DEC-013 Acceptance Patch (2026-07-03).** After **PR #70 merged into
> `Shopify-connector`** (merge commit
> `5c44971d1df84d5657da0164bf874b1125aee64f`) — carrying the Fable
> revision and the tiny consistency fix above — **ChatGPT formally
> accepts this record.** See *Accepted decision* below for the accepted
> package and the explicit acceptance points. **This acceptance does not
> open the implementation gate.** No accepted DEC-003 through DEC-012
> content changed; no code files changed; implementation remains
> blocked; **Master Blueprint Sprint B** (Product, Customer, and
> Sale/Order Domain Blueprint) is the next recommended sprint but has
> **not started**; **Part D — UI/UX Screen Design Blueprint — remains
> required before implementation of any operator-facing screen**
> (MBQ-53 stays open until that dedicated sprint is completed and
> accepted).

## Date

2026-07-03.

## Accepted decision

**ChatGPT accepts DEC-013** as the accepted Master Blueprint Sprint A
core/common substrate package.

**Accepted package** (the *Proposed decision* items below are now
accepted as the blueprint-level design):

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
12. UI/UX Screen Design Blueprint (Part D) requirement before
    operator-facing screen implementation.

**Explicit acceptance points:**

**A. Binding schema shape.** Accepts the Part A §C.8 direction:
per-domain concrete binding models extending a core abstract binding
contract; a cross-domain enumeration/registration seam; a
binding-model granularity bound; the single polymorphic table option
remains **not chosen**. This does not reintroduce **RA-005** or
**RA-013**. Resolves **MBQ-11**.

**B. Feature-flag mechanism.** Accepts the Part A §I.3 direction: a
store-scoped core settings record, extended by domain modules with
their own flags — not global `ir.config_parameter` storage, not
transient-only `res.config.settings` storage, not per-domain ad hoc
settings models. The execution-time re-check remains scoped to
fail-safe enablement gating only (§I.3); **no flag bypasses a safety
guard** (§I.5). Resolves **MBQ-07** at blueprint-direction level; exact
technical implementation detail remains open for implementation
planning.

**C. Roles / access blueprint.** Accepts the Part A §J proposed
hierarchy at blueprint level: Administrator implies Operator and
Reviewer rights; Operator and Reviewer are siblings; Auditor is
implied by all; Reviewer remains approval/manual-review focused
(resolves **MBQ-47**). No access CSVs or exact XML IDs are decided
(**MBQ-44** remains open). No connector UI/API surface exposes the
stored credential secret after entry (§J.2); the credential at-rest
mechanism remains **MBQ-04**, open.

**D. UI/UX.** Accepts that **Part D — UI/UX Screen Design Blueprint —
is required before implementation of operator-facing screens**.
**MBQ-53 remains open** until that dedicated sprint is completed and
accepted.

**E. Still open.** This acceptance does not resolve every MBQ. Kept
open where appropriate, especially: **MBQ-04** (credential
storage/encryption mechanism), **MBQ-08** (store-disconnect
data-retention posture), **MBQ-53** (screen-level UI/UX design
blueprint), **MBQ-54** (domain-module uninstall/disable data
lifecycle), exact model/field/view/security identifiers,
implementation-planning details, and domain blueprint questions routed
to Sprint B/C. **MBQ-45** is **partially resolved**: the proposed role
hierarchy is accepted; exact group decomposition, XML IDs, and the
admin-vs-functional-user screen split remain open.

**What this acceptance does NOT do:**

- Does **not authorize implementation** under any circumstance (see
  *No implementation authorized* below).
- Does **not start Sprint B** — Master Blueprint Sprint B (Product,
  Customer, and Sale/Order Domain Blueprint) is the next recommended
  sprint, not started.
- Does **not waive** the requirement that Part D — UI/UX Screen Design
  Blueprint — be completed and accepted before any operator-facing
  screen implementation.
- Does **not change** DEC-003 through DEC-012.

## Scope

**Master Blueprint Sprint A only** — the Master Blueprint **index/structure**
and the **core/common substrate blueprint** (`shopify_connector_core`
boundary and extension seams; core configuration-object concepts; binding
abstraction; job/queue/log/error abstraction; setup wizard; dashboard; sync
center; error center; configuration/feature-flag mechanism; blueprint-level
access design; cross-module dependency and extension rules; the central
open-questions register). Does **not** cover the product, customer,
sale/order, inventory, or fulfillment detailed domain blueprints (Sprints
B/C), exact GraphQL operation bodies, exact Python method design, Odoo
XML/CSV artifacts, tests, or implementation tickets. Does **not** modify
DEC-003 through DEC-012.

## Accepted context

- **DEC-003 through DEC-012** are all **Accepted by ChatGPT** (DEC-012 on
  2026-07-03, after PR #68; PR #69 acceptance patch merged as
  `305f396bcbd2656a4282ed18c5983540503b5502`).
- **AR-002 through AR-009** are all **Accepted**
  (`../05-qa/architecture-review-log.md`).
- **RA-001 through RA-023** are **binding rejected approaches**
  (`../05-qa/rejected-approaches-log.md`); this sprint checked the log and
  reintroduces none of them.
- All five Phase 1 research-phase-exit criteria in
  `../05-qa/quality-feedback-loop.md` §10 are satisfied; the
  **implementation gate itself remains closed** (a separate ChatGPT
  approval).
- DEC-008 explicitly routed the **feature-flag / per-store
  capability-configuration mechanism** to the Master Blueprint; DEC-010/
  DEC-011 routed the **core Shopify Location reference** invariants and the
  location-confirmation mechanism here; DEC-012 routed the conceptual
  four-role model here for blueprint-level access design.

## Proposed decision

Accept the **Master Blueprint index** and **Part A — core/common substrate
blueprint** as the blueprint-level design for `shopify_connector_core`,
namely:

1. **Module boundary** — `shopify_connector_core`'s owns / must-not-own
   lists and seven extension seams (Part A §A, including the webhook-topic
   registration seam added per Fable's PR #70 review), applying DEC-008
   without change.
2. **Core configuration objects** — blueprint-level concepts for
   store/connection, secure credential posture (masked, no-read-back,
   never logged), API version/health, the minimal Shopify Location
   reference (with the DEC-010/011 invariants), domain enablement,
   source-of-truth settings, and notification defaults (Part A §B).
3. **Binding abstraction** — the DEC-006 contract made blueprint-concrete
   (store-scoped uniqueness, GID-explicit identity, status vocabulary,
   audit/override fields, stale/recreated handling, structural exclusion of
   name-only matching), plus the **proposed schema-shape direction**:
   per-domain concrete binding models extending a core abstract contract
   (Part A §C.8) — resolving, at blueprint level, the fork DEC-006/DEC-008
   left to the Master Blueprint.
4. **Job/log/error abstraction** — the DEC-005/DEC-009 substrate made
   blueprint-concrete (6 sources, 10 states, 16-class registry owned by
   core, classified retry, generalized operation-level idempotency key
   concept, ambiguous-outcome and serialization rules, cancel/supersede,
   audit and log shapes) (Part A §D).
5. **Operator-surface blueprints** — setup wizard (11 steps, readiness
   checks, safe incomplete state, no business sync before setup complete,
   read-only readiness/preview jobs allowed during setup, first-push
   *scheduling* only), dashboard (exception-first, no vanity metrics,
   every count clickable), sync center (state/class-conditional retry,
   verify-current-state, operator-safe operation reference), and error
   center (human reason, expandable detail, suggested fix, owner state,
   sub-reasons, audit trail) (Part A §E–§H), applying DEC-012 without
   change.
6. **Configuration / feature-flag mechanism** — per-store enabled domains +
   per-domain capability flags with safe enable/disable semantics
   (disable never deletes history; re-enable re-enters the domain guard;
   **no flag bypasses a safety guard**), and the **preferred technical
   direction**: a store-scoped core settings record extended by domain
   modules (Part A §I).
7. **Blueprint-level access design** — the four DEC-012 roles as a
   capability matrix (view/configure/trigger/retry/approve-manual-review/
   masked-secrets-only/audit), a proposed role hierarchy, and proposed
   group-name directions only — **no access CSVs, no committed XML IDs**
   (Part A §J).
8. **Cross-module dependency and extension rules** — ten binding rules for
   all later domain blueprints (Part A §K).
9. **The open-questions register** as the single routing surface for every
   unresolved Master Blueprint / implementation-planning question
   (`master-blueprint-open-questions.md`, MBQ-01–MBQ-54).
10. **The blueprint sprint structure** — Part B (product/customer/
    sale-order), Part C (inventory/fulfillment), **Part D (UI/UX Screen
    Design Blueprint — required before implementation of any
    operator-facing screen, per Fable's PR #70 review)**, Part E
    (implementation-planning bridge) as the proposed sequence. **This is
    not an exhaustive list of every future Master Blueprint part** — later
    review may add, split, or re-cut parts as needed; DEC-013 does not
    foreclose that.

## What this decides

- The blueprint-level design of the core/common substrate (items 1–8
  above) as the binding basis for Sprint B/C/D domain and UI/UX blueprints
  and — after the separate gate — implementation planning.
- The two blueprint-level directions explicitly routed here by earlier
  decisions: the **binding schema shape** (per-domain concrete on a core
  abstract contract) and the **feature-flag mechanism direction**
  (store-scoped core settings record, domain-extended) — both subject to
  this record's review; ChatGPT may accept Part A while amending either
  direction.
- The Master Blueprint's structure and its implementation-gate criteria
  (index §"Criteria for when implementation may later be opened").

## What this does NOT decide

- **No implementation authorization** — under any outcome of this review.
- No product/customer/sale-order/inventory/fulfillment **domain blueprint**
  (Sprints B/C, not started).
- No exact Odoo model/field names, view/menu XML IDs, security groups,
  access CSV rows, or record rules (proposed names in Part A are
  directions only).
- No exact GraphQL operation bodies, Python method designs, retry/backoff
  constants, cron cadences, or reconciliation cadence/scope.
- No change to DEC-003 through DEC-012, to any RA row, or to any accepted
  product-scope file.
- No resolution of any open-question row except by explicitly recording it
  (the register routes; it does not decide).

## Open questions

Centralized in
[`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
(MBQ-01 through MBQ-54), grouped by core/setup/config, binding/dedup,
job/log/error/retry, product/customer/order, inventory, fulfillment,
permissions/security, deployment/operations, and UI/UX design — each with a
source, decision owner, and implementation-blocking status. Headline rows
for this record's review: MBQ-04 (credential storage mechanism), MBQ-07
(feature-flag mechanism confirmation), MBQ-08 (disconnect data retention),
MBQ-11 (binding schema-shape confirmation), MBQ-45 (roles→groups mapping),
MBQ-47 (Reviewer boundary), MBQ-53 (screen-level UI/UX design blueprint —
added per Fable's PR #70 review), MBQ-54 (domain-module uninstall/disable
data lifecycle — added per Fable's PR #70 review).

## Risks and mitigations

1. **Risk:** blueprint detail could be read as code-level commitment
   (model/field/group names). **Mitigation:** every name is explicitly a
   proposed direction; exact identifiers are MBQ-01/02/03/44, owned by
   implementation planning; Part A's naming-discipline note governs.
2. **Risk:** proposing the binding schema shape here could be seen as
   re-deciding DEC-006. **Mitigation:** DEC-006/DEC-008 explicitly left
   that fork to the Master Blueprint; Part A §C.8 proposes (not asserts)
   the per-domain shape, keeps the polymorphic option un-rejected, and
   routes confirmation through this record's review (MBQ-11).
3. **Risk:** the feature-flag direction could drift into deciding Odoo
   implementation detail. **Mitigation:** §I.3 fixes only the
   blueprint-level direction (store-scoped, core-owned, domain-extended,
   guard-safe); the exact mechanism remains MBQ-07 if ChatGPT does not
   confirm it.
4. **Risk:** the access matrix could be treated as a committed security
   model and turned into CSVs prematurely. **Mitigation:** §J creates no
   CSVs/XML IDs; MBQ-44/45/47 gate the artifacts; the no-code gate stands
   regardless.
5. **Risk:** blueprint-level generalizations (operation-key concept,
   serialization guard, enqueue+execution flag checks) could silently
   exceed what DEC-009/DEC-011 accepted. **Mitigation:** each
   generalization is labelled **[Blueprint proposal]** with its accepted
   source cited, and none weakens an accepted guard — they extend guards to
   more surfaces, never bypass them.
6. **Risk:** starting domain blueprints implicitly through core examples.
   **Mitigation:** domain specifics appear only where an accepted DEC
   already fixed them (e.g. inventory identity key); every domain design
   question is routed to Sprint B/C in the register.

## No implementation authorized

**This record does not authorize implementation.** Acceptance is a
documentation-level blueprint acceptance only. No code, Odoo module,
model, view, controller, security file, manifest, test, or CI change is
created or permitted by this record, and none may be created until
ChatGPT separately opens the implementation gate per the Phase 1
research-phase-exit criteria (`../05-qa/quality-feedback-loop.md` §10)
and `CLAUDE.md` §5 — **and, for any operator-facing screen/view/UI flow,
the accepted Part D — UI/UX Screen Design Blueprint** (see
`../03-architecture/master-blueprint.md` "Criteria for when
implementation may later be opened"). **Acceptance of this record alone
does not open that gate.**

## Next sprint recommendation

**Master Blueprint Sprint B — Product, Customer, and Sale/Order Domain
Blueprint** (Part B): convert DEC-003/006/007 (+ DEC-012 flows §6–§7) into
the product import/export/update, customer import/matching, and order
import + financial-evidence blueprints, resolving or routing MBQ-23 through
MBQ-31. **This is the next recommended sprint now that DEC-013 is
accepted — it has not started.** Sprint C (inventory/fulfillment), Sprint D
(UI/UX Screen Design Blueprint, resolving MBQ-53), and Sprint E
(implementation-planning bridge) follow per the index — this is the
currently proposed order, not an exhaustive or final list of every future
part.

## Review / change control

- **This record accepts Master Blueprint Part A only.** No accepted
  decision is re-litigated; no rejected approach is reintroduced.
- **Related:** AR-010 (`../05-qa/architecture-review-log.md`, **Accepted by
  ChatGPT via DEC-013**); the three companion blueprint documents above;
  DEC-003 through DEC-012 (accepted context, unmodified).
- **Changes** to this record after acceptance require ChatGPT review,
  mirroring the DEC-004 through DEC-012 change-control pattern.
