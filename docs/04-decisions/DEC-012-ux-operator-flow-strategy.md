# DEC-012 — UX / Operator-Flow Strategy

> **Proposed decision record.** This record proposes the Phase 1
> **UX/operator-flow strategy** for the premium Odoo 19 ↔ Shopify Connector,
> prepared after **AR-002 through AR-008** were all accepted (via DEC-004
> through DEC-011) and **DEC-003 through DEC-011** were accepted by ChatGPT.
> Companion evidence-backed proposal:
> [`../02-product/ux-operator-flow.md`](../02-product/ux-operator-flow.md).
> Companion architecture bridge:
> [`../03-architecture/ux-operator-flow-architecture-bridge.md`](../03-architecture/ux-operator-flow-architecture-bridge.md).
> **This record does not authorize implementation and does not change
> DEC-003 through DEC-011.**

## Status

**Proposed for ChatGPT review.**

## Date

2026-07-02.

## Scope

**UX/operator-flow only** — how a non-technical Odoo operator safely
configures, runs, monitors, recovers, and audits the connector, across ten
flows: initial setup wizard, store settings, dashboard/command center, sync
center/job monitor, error center/recovery flow, matching/duplicate-prevention
flow, product import/export/update flow, inventory flow, fulfillment flow,
and a conceptual permissions/roles model. Does **not** decide exact Odoo
views, menus, wizards, widgets, field names, security groups/access CSVs,
copy/wording, or the feature-flag/per-store capability-configuration
**mechanism** (DEC-008 explicitly routes that mechanism here for the
operator-facing experience only, and to the Master Blueprint for the
technical mechanism). Does **not** modify DEC-003/004/005/006/007/008/009/
010/011 — it applies their already-accepted "UX implications" sections into
concrete operator flows, and closes the last-named Phase 1
research-phase-exit criterion in
[`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md) §10
("a UX/operator-flow sprint accepted, or explicitly parallelized").

## Accepted context

- **DEC-003 (MVP scope):** single-store/single-company MVP; controlled
  bidirectional product onboarding; inventory write-back in MVP with a
  controlled/reviewed initial import; fulfilment/tracking write-back in MVP;
  order import with minimal financial evidence only; no unrestricted
  autonomous bidirectional catalog ownership; no customer export; the
  recovery-first UX spine (reason-coded logs, safe manual retry, honest
  freshness) is mandatory.
- **DEC-004 (distribution/API/auth):** non-public custom-app/offline-token
  model; masked credential storage; least-privilege scopes; inline
  test-connection/readiness check; mandatory preview/dry-run diff before any
  `productSet` write.
- **DEC-005 (sync orchestration):** layered sync (webhook + `ir.cron` +
  manual + scheduled reconciliation, never one mechanism alone); jobs shown
  as queued/processing/done, never raw `ir.cron` fields; honest freshness;
  recovery-first error center.
- **DEC-006 (binding/dedup/identity):** dedicated, store-scoped bindings;
  match priority existing binding → SKU/internal reference → barcode →
  manual; name is advisory only, never automatic; duplicate-prevention
  preview before any create/bind; manual match with a visible audit trail.
- **DEC-007 (Phase 1 scope clarifications):** variant export/update included;
  basic image/media handling; price/compare-at with an explicit
  source-of-truth requirement; the first-inventory-push guard (mapped
  location + preview + confirmation + recorded source-of-truth +
  skip/manual-match); the fulfilment customer-notification default-off
  guard.
- **DEC-008 (module boundaries):** layered domain-aligned addon family
  (`core`/`product`/`sale`/`inventory`/`fulfillment`); cross-cutting
  substrate (transport, queue/job, binding abstraction, error registry,
  setup wizard, dashboard) concentrated in `core`; the feature-flag/config
  mechanism explicitly routed to this sprint (UX) and the Master Blueprint
  (technical mechanism).
- **DEC-009 (error/retry/idempotency):** 16-class error taxonomy; classified
  retry policy (auto-retry only safe/transient classes); the ambiguous-outcome
  rule (verification read before retry, or manual review — never blind
  retry); human-readable reason as the primary error message; full audit
  requirements.
- **DEC-010 (inventory architecture):** Odoo as ongoing source of truth;
  Shopify `available` as the Phase 1 default write target; `on_hand` allowed
  but not default without explicit Master Blueprint justification;
  `committed` never written; inventory identity keyed on `(store,
  inventory_item_id, location_id)`; no autonomous bidirectional conflict
  resolution.
- **DEC-011 (fulfillment architecture):** validated `stock.picking` as
  trigger; FulfillmentOrder-based mutations only; matched order/
  FulfillmentOrder/line/quantity/location; notification default off,
  persisted per job; multi-location/multi-package deferred to manual review.
- **`setup-ux-principles.md` (accepted product-UX-principles input):** 12
  principles (guided setup, prove readiness, progressive disclosure, honest
  freshness, command center, recovery-first errors, safe-by-default actions,
  human-readable logs, guided mappings, role-aware UX, modular feature
  visibility, docs mirror the product) — this record is the first place
  those principles are applied against the now-accepted architecture.
- **`product-vision.md` (accepted product-vision input):** personas P1
  (operations/e-commerce user), P2 (Odoo administrator/implementation
  consultant), P3 (business owner/finance stakeholder), P4 (Odoo
  partner/integrator).

## Decision proposed

Adopt the ten operator-flow proposals set out in
[`ux-operator-flow.md`](../02-product/ux-operator-flow.md) as the Phase 1
UX/operator-flow strategy: a guided setup wizard that never lets sync start
before setup is complete and never silently completes the first-inventory-push
or notification-default guards on the operator's behalf; store settings that
expose connection/token/domain/source-of-truth/notification state without
exposing secrets; a dashboard that surfaces only actionable, non-vanity
metrics with a clear next action per metric; a sync center/job monitor built
directly on DEC-009's job-state and error-class taxonomy, with retry never
offered where it would be unsafe; an error center that leads with a
human-readable reason, a suggested fix, and a full audit trail; a
matching/duplicate-prevention flow built directly on DEC-006's match-key
priority and preview-before-create rule; a product flow with mandatory
preview and draft-first export; an inventory flow that structurally excludes
`committed` as a write target and never skips the first-push guard; a
fulfillment flow that never double-fulfills and never sends a surprise
notification; and a conceptual four-role permissions model (Administrator,
Operator, Reviewer/Manual Review Owner, Read-only Auditor) mapped to the
already-accepted P1–P4 personas.

## Setup UX posture

The initial setup wizard is a **guided, multi-step custom-app credential
flow** (not one-click OAuth, per DEC-004), ending in an explicit readiness
summary and a **safe incomplete-setup state** (no sync runs until setup is
marked complete). Sync-direction, source-of-truth, and notification-default
choices are made explicitly during setup, never defaulted silently. The
inventory first-push guard may be scheduled for after initial setup but must
never be silently skipped or auto-completed. Full flow:
[`ux-operator-flow.md`](../02-product/ux-operator-flow.md) §1–§2.

## Dashboard posture

A single command center answers "is everything OK, what failed, what do I do"
using only metrics that map to either a health signal or a clickable next
action — no vanity-only counters. Per-domain freshness/last-sync labels are
honest (no "real-time" overstatement); quick actions enqueue work, never run
inline. Full flow: [`ux-operator-flow.md`](../02-product/ux-operator-flow.md)
§3.

## Sync/error/retry UX posture

The job monitor is built directly on DEC-009's job-source/job-state/
error-class taxonomy; retry is never a single generic button — it is state-
and class-conditional, and ambiguous-outcome cases always offer a
verification read before any retry action. The error center leads with a
human-readable reason (never a raw stack trace as the primary message),
shows technical detail on demand, names a suggested fix, and carries the
full DEC-009 audit trail (attempted/written/skipped/confirmed-by). Full
flow: [`ux-operator-flow.md`](../02-product/ux-operator-flow.md) §4–§5.

## Matching/dedup UX posture

Matching follows DEC-006's priority exactly (binding → SKU/internal reference
→ barcode → manual; name advisory only), with a mandatory duplicate-
prevention preview before any create/bind action and a full audit trail
(matched-by/at/source-strategy/match-key) per binding. Ambiguous and
duplicate-risk states are distinct, both routing to manual review rather
than an automatic guess. Full flow:
[`ux-operator-flow.md`](../02-product/ux-operator-flow.md) §6.

## Product flow posture

Product import/export/update carries a mandatory preview of creates/updates/
skips before any write, a draft-first posture for first-time export where
Shopify supports it, and no autonomous bidirectional conflict ownership.
Variant, image/media, and price/compare-at handling follow DEC-007's
included/excluded boundaries exactly, with price export/update blocked
until a source-of-truth choice is on record. Full flow:
[`ux-operator-flow.md`](../02-product/ux-operator-flow.md) §7.

## Inventory flow posture

The inventory flow structurally excludes `committed` as a write target under
any configuration, pre-selects `available` (not `on_hand`) as the default
write target, and never allows a first Odoo→Shopify write without the full
DEC-007 guard (mapped location + preview + confirmation + recorded
source-of-truth + skip/manual-match). Inventory mismatches surface as a
distinct exception category, never auto-resolved. Full flow:
[`ux-operator-flow.md`](../02-product/ux-operator-flow.md) §8.

## Fulfillment flow posture

The fulfillment flow only triggers from a validated picking, only creates
Shopify fulfillments via FulfillmentOrder-based matching (order → open
FulfillmentOrder → matched lines/quantities/location), defaults customer
notification to off with an explicit opt-in persisted per job, blocks
unmatched/ambiguous pickings for manual review, and requires a verification
read before any retry of an ambiguous-outcome write. Multi-location/
multi-package automation stays deferred to manual review in Phase 1. Full
flow: [`ux-operator-flow.md`](../02-product/ux-operator-flow.md) §9.

## Permissions posture

Four roles are proposed **conceptually only** (no Odoo groups/access CSVs
decided here): Connector Administrator (setup, credentials, settings),
Connector Operator (day-to-day sync/retry/log access), Connector Reviewer /
Manual Review Owner (resolves `blocked_manual_review` items specifically),
and Read-only Auditor (view-only, no action rights). These map conceptually
to personas P2, P1, (no single persona — a narrower cut of P1/P2), and P3
respectively. Full flow:
[`ux-operator-flow.md`](../02-product/ux-operator-flow.md) §10.

## What remains open

- Exact Odoo views, menus, wizards, widgets, and field names for every flow
  above — Master Blueprint.
- Exact Odoo security groups / `ir.model.access` rows / access-control CSVs
  for the four conceptual roles — Master Blueprint.
- Exact copy/wording for setup steps, dashboard labels, error reasons, and
  suggested fixes — a later UI-design pass, structured by this record but not
  written by it.
- The feature-flag/per-store capability-configuration **mechanism** (DEC-008)
  — this record proposes only the operator-facing experience (§2, §3 of the
  companion UX doc), not the technical mechanism.
- Which readiness checks are essential vs. nice-to-have (setup wizard §1).
- Exact granularity of "first" for the inventory first-push guard, and
  whether ongoing writes require preview/confirmation on every write or only
  the first (inventory flow §8; unchanged open question from DEC-007/010).
- Exact notification-UI granularity — global/per-store/per-order
  (fulfillment flow §9; unchanged open question from DEC-007/011).
- Whether `on_hand` is ever exposed as a Phase 1 UI choice at all (inventory
  flow §8; DEC-010 unchanged).
- Exact draft/publish mechanism to key draft-first export off of (product
  flow §7).
- Admin vs. functional-user dashboard/settings split — one role-gated
  surface, or two (dashboard §3; unchanged open question from
  setup-ux-principles.md).
- **Order-import operator touchpoints** — whether order-import operator
  touchpoints are fully covered by the error center/manual-review flow (UX
  doc §5), especially financial evidence mismatch and total-check issues
  (DEC-007 §6), or whether a separate order-import operator flow is needed
  (raised in Fable's review of PR #68).
- **Store disconnect data-retention posture** — what happens to bindings,
  logs, jobs, and audit records after a store is disconnected (UX doc §2)
  (raised in Fable's review of PR #68).

## Risks and mitigations

1. **Risk:** a UX proposal this detailed could be read as pre-deciding
   Odoo-level implementation (views, models, security groups).
   **Mitigation:** every flow section is explicitly scoped to operator-
   visible behaviour and states, not screens; a dedicated "What this document
   does not decide" section and this record's own "What remains open" section
   name every implementation-level item left to the Master Blueprint.
2. **Risk:** the ten-flow structure could drift from the already-accepted
   architecture decisions (DEC-004 through DEC-011) if written independently
   of them. **Mitigation:** every proposed UX step is either labelled
   **[Accepted]** with a direct citation to the DEC file/section it restates,
   or labelled **[Proposed UX decision]**/**[Inference]** where it is new —
   nothing here contradicts a DEC-003–011 "UX implications" section; the
   companion architecture bridge
   ([`ux-operator-flow-architecture-bridge.md`](../03-architecture/ux-operator-flow-architecture-bridge.md))
   maps every flow to its source decisions explicitly, so drift is
   independently checkable.
3. **Risk:** the permissions/roles concept could be read as a committed
   Odoo security model. **Mitigation:** §10 of the companion document is
   explicitly labelled conceptual only, with an "Explicitly out of scope"
   subsection naming security groups/access CSVs as Master Blueprint items.
4. **Risk:** proposing a four-role model not directly named in any prior
   accepted decision could be seen as introducing new scope.
   **Mitigation:** each role is explicitly derived from the already-accepted
   `setup-ux-principles.md` Principle 10 (admin vs. functional-user split)
   and `product-vision.md`'s P1–P4 personas — it is a synthesis of already-
   accepted inputs, not a new capability, and remains conceptual pending
   Master Blueprint schema work.
5. **Risk:** the dashboard's "avoid vanity-only metrics" rule and the error
   center's structure could be under-specified relative to what a real UI
   needs. **Mitigation:** both are intentionally structural (what must be
   true of any metric/error shown) rather than a fixed screen layout,
   leaving room for the Master Blueprint to design the actual screen while
   still being bound by the structural rule.

## No implementation authorized

**This record does not authorize implementation.** It proposes a
UX/operator-flow strategy for ChatGPT (and Fable's advisory) review only.
This record creates no code, no Odoo module, no view, no model, no security
file, and no file outside `docs/02-product/**`, `docs/03-architecture/**`,
`docs/04-decisions/**`, `docs/05-qa/**`, `docs/01-research/**`, and
`docs/06-prompts/**`. The no-code gate (`CLAUDE.md` §4–§5) remains in force.
Implementation of any part of these flows remains blocked until: (1) ChatGPT
accepts this record (or a revised version of it), and (2) ChatGPT separately
opens the implementation gate per the Phase 1 research-phase-exit criteria
(`../05-qa/quality-feedback-loop.md` §10) and `CLAUDE.md` §5. Acceptance of
this record alone does not open that gate, and does not itself constitute
the Master Blueprint.

## Review / change control

- **This record decides UX/operator-flow strategy only.** No API strategy,
  binding-schema-shape, module-boundary, inventory/fulfilment-architecture,
  or MVP-scope decision is re-litigated (all already decided by
  DEC-003/004/005/006/007/008/009/010/011).
- **Related:** the companion evidence-backed proposal
  ([`../02-product/ux-operator-flow.md`](../02-product/ux-operator-flow.md));
  the architecture bridge
  ([`../03-architecture/ux-operator-flow-architecture-bridge.md`](../03-architecture/ux-operator-flow-architecture-bridge.md));
  DEC-003 through DEC-011 (accepted context, unmodified);
  `../05-qa/quality-feedback-loop.md` §10 (the phase-exit criterion this
  record targets).
- **Changes** to this proposed record before acceptance are expected through
  normal review; once accepted, changes require ChatGPT review, mirroring the
  DEC-004 through DEC-011 change-control pattern.
