# Master Blueprint — Index

> Top-level index for the **Master Blueprint** of the premium **Odoo 19 ↔
> Shopify Connector**. The Master Blueprint converts the accepted decision
> records (DEC-003 through DEC-012) into detailed, implementation-ready
> **blueprints** — still documentation only. Started in **Master Blueprint
> Sprint A**; **Part A accepted via DEC-013**. Companion decision record:
> [`../04-decisions/DEC-013-master-blueprint-core-substrate.md`](../04-decisions/DEC-013-master-blueprint-core-substrate.md)
> (Status: **Accepted by ChatGPT**, 2026-07-03).

## Status

**Accepted through DEC-013 (Part A — core/common substrate only).**
Acceptance date: **2026-07-03.** Documentation only — the no-code gate
(`CLAUDE.md` §4–§5) is in force. **The Master Blueprint does not
authorize code**, and acceptance of Part A does not by itself open the
implementation gate (see *Implementation gate criteria* below). **Parts
B, C, D, and E remain Not started.**

## Relation to accepted decisions

The Master Blueprint is built strictly **on top of** — and must never
contradict, weaken, or re-litigate — the accepted records:

| Accepted record | What it fixed | How the blueprint uses it |
| --- | --- | --- |
| [DEC-003](../04-decisions/DEC-003-mvp-scope.md) | MVP product scope (correctness core + controlled bidirectional product onboarding) | Scope boundary for every blueprint part |
| [DEC-004](../04-decisions/DEC-004-distribution-api-auth-strategy.md) | Custom-app / GraphQL-first / offline-token distribution+API+auth | Transport, credential, and setup-wizard blueprints |
| [DEC-005](../04-decisions/DEC-005-sync-orchestration-strategy.md) | Webhook + `ir.cron` + internal queue + reconciliation substrate | Job/queue abstraction blueprint |
| [DEC-006](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) | Dedicated store-scoped binding model; match-key priority; no name-only matching | Binding/identity abstraction blueprint |
| [DEC-007](../04-decisions/DEC-007-phase1-scope-clarifications.md) | Variant/image/price boundaries; first-push guard; notification default; financial-evidence treatment | Guard semantics across setup/inventory/fulfillment/order blueprints |
| [DEC-008](../04-decisions/DEC-008-module-boundary-strategy.md) | Layered addon family + dependency DAG; substrate concentrated in `core` | Module-boundary and cross-module extension rules |
| [DEC-009](../04-decisions/DEC-009-error-retry-idempotency-strategy.md) | 16-class error taxonomy; classified retry; layered idempotency; audit/log requirements | Job/log/error/retry abstraction blueprint |
| [DEC-010](../04-decisions/DEC-010-inventory-architecture-strategy.md) | Inventory source-of-truth, identity, location mapping, first-push posture | Inventory domain blueprint (Sprint C) + core Location reference |
| [DEC-011](../04-decisions/DEC-011-fulfillment-architecture-strategy.md) | FulfillmentOrder-based fulfillment, notification posture, operation-level idempotency | Fulfillment domain blueprint (Sprint C) + core operation-key concept |
| [DEC-012](../04-decisions/DEC-012-ux-operator-flow-strategy.md) | Ten operator flows; conceptual four-role permissions model | Wizard/dashboard/sync-center/error-center/access blueprints |

AR-002 through AR-009 are all **Accepted**
([`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md));
RA-001 through RA-023 are **binding rejected approaches**
([`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md))
that no blueprint part may reintroduce.

## Blueprint scope

The Master Blueprint defines, at **blueprint level** (concepts, contracts,
rules, flows — not code, not schemas, not XML):

- module boundaries in implementable detail, per DEC-008;
- model **concepts** (purpose, conceptual fields, identity/uniqueness rules,
  access, audit) for every connector object;
- the shared substrate contracts (binding, job/log/error, configuration,
  access) every domain module builds on;
- operator-surface blueprints (setup wizard, dashboard, sync center, error
  center) per DEC-012;
- cross-module dependency and extension rules;
- a single open-questions register routing every unresolved item to its
  decision owner.

It does **not** produce: Odoo models/views/security files, manifests,
GraphQL operation bodies, Python method designs, tests, implementation
tickets, or retry/cadence constants.

## Blueprint parts / sprint structure

| Part | Sprint | Content | Status |
| --- | --- | --- | --- |
| **Index** (this file) | Sprint A | Structure, relation to decisions, gate criteria | **Accepted by ChatGPT via DEC-013** (2026-07-03) |
| **Part A — Core/common substrate** | Sprint A | [`master-blueprint-core-substrate.md`](./master-blueprint-core-substrate.md): `shopify_connector_core` boundary; store/credential/API-health/Location-reference/settings concepts; binding abstraction; job/log/error/retry abstraction; setup wizard; dashboard; sync center; error center; feature-flag mechanism; access blueprint; cross-module rules | **Accepted by ChatGPT via DEC-013** (2026-07-03) |
| **Open-questions register** | Sprint A (rolling) | [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md): every unresolved item, grouped, with owner and blocking status | **Accepted by ChatGPT via DEC-013** (2026-07-03); updated by every later part |
| **Part B — Product, Customer, Sale/Order domain blueprints** | Sprint B (recommended next) | Product import/export/update blueprint (variants, images, price, preview/diff, draft-first); customer import/matching blueprint; order import + financial-evidence blueprint (incl. order-import operator touchpoints, MBQ-26) | **Not started** |
| **Part C — Inventory and Fulfillment domain blueprints** | Sprint C | Inventory blueprint (location mapping, first-push guard granularity, apply mode, quantity source); fulfillment blueprint (FulfillmentOrder matching, tracking, notification granularity, location confirmation) | **Not started** |
| **Part D — UI/UX Screen Design Blueprint** | Sprint D | Screen-level design blueprint required before implementation of operator-facing screens (see *UI/UX Screen Design Blueprint* below); resolves MBQ-53 | **Not started** |
| **Part E — Implementation-planning bridge** | Sprint E | Consolidated verification pass; resolution/acceptance of implementation-blocking open questions; sequencing input for `docs/07-implementation-plan` | **Not started** |

*The Part B/C/D/E split is a **proposed structure**, accepted as the
proposed sequence by DEC-013 — ChatGPT may still re-cut it at a later
review. Sprint A deliberately does not start any domain
blueprint and does not create any screen layout or wireframe.*

## UI/UX Screen Design Blueprint (Part D — required before operator-facing implementation)

**Not started by Sprint A.** DEC-012 accepted ten operator flows and
promised a later, dedicated UI-design pass for exact copy/wording and
screen-level detail (`../02-product/ux-operator-flow.md` §5 "Open
questions"; DEC-012 "What remains open"). Sprint A's Part A blueprint
converts those flows into substrate/contract detail but does **not**
produce screen layouts, wireframes, or navigation design. A dedicated
**UI/UX Screen Design Blueprint** is required as its own Master Blueprint
part, after the domain blueprints (Parts B/C) and before any operator-facing
screen is implemented. It must cover:

- Screen inventory (every operator-facing screen implied by the ten
  DEC-012 flows and the Part A/B/C blueprints).
- Navigation / information architecture (menu structure, how screens
  relate, role-gated visibility per §J).
- Odoo-native interaction patterns (which Odoo widget/view conventions the
  connector reuses vs. where it needs a custom pattern, and why).
- Screen-level wireframe specs for: dashboard layout; setup wizard layout;
  store settings layout; sync center layout; error center layout; matching
  center layout; preview/review screens (product diff, inventory
  first-push, duplicate-prevention).
- Empty / loading / success / error / manual-review states for every
  screen above — no screen may be designed with only its "happy path"
  state.
- UX copy guidelines and error-message style (the copy DEC-009/DEC-012
  left as "not decided here, a UX/operator-flow-sprint concern").
- A premium UI/UX acceptance checklist — the bar this connector's
  operator-facing surfaces must clear before implementation, consistent
  with the product's premium-quality-bar intent (`../02-product/product-vision.md`).

This part is tracked as **MBQ-53** in
[`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
and **blocks implementation of operator-facing screens** until it exists
and is accepted. It does **not** block Part B/C domain-blueprint authoring,
which is concept/contract-level work, not screen design.

## Module family overview

Per accepted DEC-008 (restated for orientation only — DEC-008 is
authoritative):

```
shopify_connector_core
└── shopify_connector_product
    ├── shopify_connector_sale
    │   └── shopify_connector_fulfillment
    └── shopify_connector_inventory
```

- `core` — cross-cutting substrate (transport, webhook receiver, queue/job,
  binding contract, error registry, setup wizard, dashboard/log/error
  center, per-store settings/flags, minimal Shopify Location reference).
- `product` — product/variant import + controlled export/update; product/
  variant binding responsibility.
- `sale` — order import; customer import/matching (folded in for Phase 1);
  financial-evidence capture with the total-check guard.
- `inventory` — quantity write-back; Odoo↔Shopify location mapping
  (sole owner); first-push guard; inventory binding identity.
- `fulfillment` — fulfillment/tracking write-back; notification guard;
  never depends on `inventory`.

Later addon family (accounting, refund, payout, multi-store, markets,
metafield, POS, B2B, app-store) remains named-but-not-finalized per
DEC-008.

## Core/common substrate summary

[`master-blueprint-core-substrate.md`](./master-blueprint-core-substrate.md)
(Part A) defines: the `shopify_connector_core` boundary and extension seams;
seven core configuration-object concepts (store/connection, credential
posture, API version/health, Shopify Location reference, domain enablement,
source-of-truth settings, notification defaults); the binding abstraction
(store-scoped uniqueness, GID-explicit identity, status + audit fields,
stale/recreated handling, a proposed per-domain-concrete-on-core-contract
shape); the job/queue/log/error abstraction (6 sources, 10 states, 16 error
classes, classified retry, operation-level idempotency, ambiguous-outcome
and serialization rules, cancellation/supersede); blueprints for the setup
wizard, dashboard, sync center, and error center; the per-store
feature-flag mechanism with safe enable/disable semantics; a four-role
access blueprint (no CSVs); and ten cross-module extension rules.

## Domain blueprints still pending

**Not started, deliberately out of Sprint A scope:** product, customer,
sale/order, inventory, and fulfillment detailed domain blueprints (Parts
B/C). Their accepted architectural direction already exists
(DEC-003/006/007/010/011); the blueprint-level detail (per-domain flows,
concepts, and open-question resolution) is Sprint B/C work. Open questions
already routed to them are grouped in
[`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md).

## Implementation remains blocked

**The Master Blueprint does not authorize code.** No part of it — proposed
or accepted — creates or permits any Odoo module, model, view, controller,
security file, manifest, test, CI workflow, or dependency change. The
no-code gate (`CLAUDE.md` §4–§5) remains in force.

## Criteria for when implementation may later be opened

Implementation may be considered — never self-triggered — only after
**all** of the following, in order:

1. **ChatGPT accepts the required Master Blueprint parts** — at minimum
   Part A (DEC-013) and the domain blueprint part(s) covering whatever is
   to be implemented first; acceptance of Part A alone does not permit
   domain implementation whose blueprint part is unwritten. **Where the
   affected implementation includes any operator-facing screen, view, or
   UI flow, the accepted UI/UX Screen Design Blueprint (Part D, above) is
   also required** — accepted domain/substrate blueprints alone do not
   authorize screen-level implementation.
2. **Implementation-blocking open questions are resolved or consciously
   accepted** — every register row marked "Blocks implementation: Yes" for
   the affected scope is either resolved (with evidence, per `CLAUDE.md`
   §7) or explicitly accepted as an open risk by ChatGPT in writing.
3. **ChatGPT explicitly opens the implementation gate** per
   [`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md)
   §10 — a separate, explicit approval; blueprint acceptance is necessary
   but not sufficient.
4. **Every implementation task is written to the CLAUDE.md §9 template**
   (allowed/forbidden files, acceptance criteria, tests, rollback,
   definition of done) using
   [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md).
5. **No quality-gate escalation is open** — no defect-pattern category sits
   at its 3rd-occurrence pause without a prevention rule
   (`../05-qa/quality-feedback-loop.md` §8).
