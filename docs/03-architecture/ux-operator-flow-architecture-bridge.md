# UX / Operator-Flow → Architecture Bridge

> Maps each of the ten operator-flow proposals in
> [`../02-product/ux-operator-flow.md`](../02-product/ux-operator-flow.md) to
> the accepted **DEC-003 through DEC-011** architecture/product decisions
> they draw on, names what each flow **routes to the Master Blueprint**
> rather than deciding, and names what **must not be implemented yet**.
> Companion proposed decision:
> [`../04-decisions/DEC-012-ux-operator-flow-strategy.md`](../04-decisions/DEC-012-ux-operator-flow-strategy.md)
> (status: **Proposed for ChatGPT review**). This bridge decides nothing by
> itself — it is a traceability aid for reviewing DEC-012.

## Status

**Documentation-only, no-code gate in force** (`CLAUDE.md` §4–§5). This
document does not itself carry a Status field for acceptance — it exists to
make DEC-012 independently checkable against DEC-003 through DEC-011 and is
reviewed alongside DEC-012.

## Purpose

`CLAUDE.md` §10 requires checking the rejected-approaches log before
proposing any design; the same discipline applies to accepted decisions — a
UX proposal must be traceable to what it draws on, not asserted as
free-standing. This bridge gives ChatGPT/Fable a single table per flow to
verify that [`ux-operator-flow.md`](../02-product/ux-operator-flow.md) does
not silently contradict, re-litigate, or exceed DEC-003 through DEC-011.

## How to read the tables

- **Source decisions** — the DEC file(s)/section(s) the flow is built on.
- **Routes to Master Blueprint** — implementation-level detail this flow
  names but explicitly does not decide (exact schema, exact mutation, exact
  copy, exact UI mechanism).
- **Must not be implemented yet** — a reminder that even where a flow is
  fully specified at the UX-structure level, no code, model, view, or
  security file exists or is authorized by this sprint.

---

## 1. Initial setup wizard

| Source decisions | What the flow uses |
| --- | --- |
| DEC-004 §"UX implications" | Guided custom-app credential flow, masked entry, test-connection/readiness check, least-privilege scope pre-selection |
| DEC-003 (MVP scope) | Single-store/single-company; per-domain direction choices bounded to what DEC-003 accepts |
| DEC-005 §"Decision summary" | Odoo.sh/on-prem hosting disclosure (Odoo Online excluded) |
| DEC-006 §"UX implications" | Explicit first-sync source-strategy choice for product matching |
| DEC-007 §3 | Explicit price source-of-truth choice |
| DEC-007 §4/§5; DEC-010; DEC-011 | Inventory first-push guard and fulfilment notification default scheduled/set at setup, never silently skipped |

**Routes to Master Blueprint:** exact readiness-check list; exact custom-app
creation surface and token-acquisition mechanics; exact
`odoo.conf`/queue-prerequisite handling for Odoo.sh/on-prem; exact wizard
screen/step implementation.

**Must not be implemented yet:** no setup wizard view, controller, or
credential-storage model exists or is authorized by this sprint.

## 2. Store settings

| Source decisions | What the flow uses |
| --- | --- |
| DEC-004 | Masked token status, reconnect/disconnect as first-class actions |
| DEC-008 §"What remains open" (feature-flag/config mechanism routing) | Enabled-domains display, aligned to the `core`/`product`/`sale`/`inventory`/`fulfillment` addon family |
| DEC-006 §3; DEC-007 §3/§5 | Editable source-of-truth and notification-default settings |

**Routes to Master Blueprint:** the feature-flag/per-store
capability-configuration **mechanism** itself (DEC-008 explicitly defers
this; this sprint proposes only the operator-facing experience, not the
technical mechanism); exact settings-model schema.

**Must not be implemented yet:** no settings view/model; no feature-flag
mechanism of any kind.

## 3. Dashboard / command center

| Source decisions | What the flow uses |
| --- | --- |
| `setup-ux-principles.md` Principle 5 (accepted product-UX input) | Command-center concept, single home surface |
| DEC-005 §"UX implications" | Honest freshness, per-domain last-sync, enqueue-not-inline quick actions |
| DEC-009 §"User-facing log requirements"; §"Error taxonomy" | Failed-job severity split, manual-review count, retry-waiting count |
| DEC-007 §4; DEC-010 | First-push-pending count |
| DEC-010; DEC-011 | Inventory/fulfillment exception counts |
| DEC-006; DEC-009 | Duplicate/matching exception count |

**Routes to Master Blueprint:** exact dashboard layout/widget design; exact
metric computation/query design; admin-vs-functional-user surface split
(open in `setup-ux-principles.md` itself).

**Must not be implemented yet:** no dashboard view or aggregation
model/query exists or is authorized.

## 4. Sync center / job monitor

| Source decisions | What the flow uses |
| --- | --- |
| DEC-009 §"Error taxonomy" (job sources, job states) | Job list, domain/trigger/status filters |
| DEC-009 §"Retry taxonomy" | Retry-eligibility distinction (automatic / safe manual / needs fix / needs verification) |
| DEC-009 §"Ambiguous-outcome rule"; DEC-011 §"Idempotency/retry posture" | "Verify current state" action, operator-safe operation-key reference |
| DEC-006 | "Open mapping" action |
| DEC-009 §"Audit requirements" | "Open source record" action |

**Routes to Master Blueprint:** exact job/log Odoo model shape (explicitly
named open in `phase1-domain-model-brief.md` Domain 8); exact retry-count
ceilings/backoff constants; reconciliation cadence/scope.

**Must not be implemented yet:** no job/queue model, no retry-execution
code, no cron job of any kind.

## 5. Error center / recovery flow

| Source decisions | What the flow uses |
| --- | --- |
| DEC-009 §"User-facing log requirements"; RA-016 | Human-readable reason as primary, technical detail secondary |
| DEC-009 §"Audit requirements" | Owner/action state, related Odoo/Shopify record, full audit trail |
| DEC-009 §"Error taxonomy" | Manual-review sub-reason display |
| DEC-011 §"Idempotency/retry posture" | Retry-policy explanation for ambiguous-outcome cases |

**Routes to Master Blueprint:** exact user-facing copy/wording (explicitly
named a UX/operator-flow-sprint concern in DEC-009 §"What remains open," and
this bridge confirms this sprint sets structure, not final copy).

**Must not be implemented yet:** no error-center view or log model exists or
is authorized.

## 6. Matching / duplicate-prevention flow

| Source decisions | What the flow uses |
| --- | --- |
| DEC-006 §"Decision summary" (match-key priority) | Binding-first → SKU → barcode → manual match order; name advisory only |
| DEC-006 §"UX implications" | Duplicate-prevention preview/diff before create/bind |
| DEC-006 §"Mitigations" #2 | Audit fields (matched-by/at, source strategy, match key, status) |
| DEC-009 §"Error taxonomy" | Ambiguous-match, binding-conflict, duplicate-risk states |
| RA-006 | Structural exclusion of name-only automatic matching |

**Routes to Master Blueprint:** exact binding schema (single polymorphic
table vs. per-domain tables — explicitly left open by DEC-006 and DEC-008).

**Must not be implemented yet:** no binding model, no matching algorithm
code.

## 7. Product import/export/update flow

| Source decisions | What the flow uses |
| --- | --- |
| DEC-003 (controlled bidirectional onboarding; no autonomous bidirectional catalog ownership) | Overall flow boundary |
| DEC-007 §1 | Variant export/update inclusion and boundary |
| DEC-007 §2 | Basic image/media inclusion and boundary |
| DEC-007 §3 | Price/compare-at inclusion and source-of-truth requirement |
| DEC-004 §"Data-safety implications" (`productSet` delete-on-omit) | Preview-before-write requirement |
| DEC-006 | Binding-keyed diff, duplicate-prevention preview |

**Routes to Master Blueprint:** exact `productSet` vs. bulk-variant-mutation
choice; exact draft/publish mechanism for draft-first export; whether
`productSet`'s delete-on-omit applies identically to media.

**Must not be implemented yet:** no export/import controller, no GraphQL
client, no product/variant binding model.

## 8. Inventory flow

| Source decisions | What the flow uses |
| --- | --- |
| DEC-010 §"Inventory source-of-truth posture" | Odoo-as-source posture; `available` default target; `on_hand` gated; `committed` excluded |
| DEC-007 §4; DEC-010 §"First-push guard posture" | Mapped location + preview + confirmation + recorded source-of-truth + skip/manual-match |
| DEC-010 §"Shopify/Odoo inventory mapping posture" | `(store, inventory_item_id, location_id)` identity |
| DEC-010 §"Location mapping posture" | Mapped-location requirement, "inventory location missing" block |
| DEC-010 §"Sync trigger posture" | Ongoing sync/reconciliation view |
| RA-018, RA-019, RA-020, RA-021 | Structural exclusions this flow must not reopen |

**Routes to Master Blueprint:** exact Odoo model/field names; exact
computed-quantity field/formula behind "Free to Use"; exact mutation choice
per trigger type; exact cron cadence; exact granularity of "first"; whether
ongoing writes need preview/confirmation on every write or only the first.

**Must not be implemented yet:** no inventory binding model, no location
mapping model, no inventory-write mutation code.

## 9. Fulfillment flow

| Source decisions | What the flow uses |
| --- | --- |
| DEC-011 §"Fulfillment source/target posture" | Validated `stock.picking` trigger; FulfillmentOrder-based mutations only |
| DEC-011 §"FulfillmentOrder posture" | Order→FulfillmentOrder→line/quantity/location matching |
| DEC-007 §5; DEC-011 §"Customer notification posture" | Default-off notification, persisted per job |
| DEC-011 §"Location/line matching posture" | Block-for-manual-review on mismatch |
| DEC-009 §"Ambiguous-outcome rule"; DEC-011 §"Idempotency/retry posture" | Verification read before retry; operation-level idempotency key |
| DEC-003 C-FUL-02; DEC-011 §"Partial/backorder posture" | Multi-location/multi-package deferral |
| RA-022, RA-023 | Structural exclusions this flow must not reopen |

**Routes to Master Blueprint:** exact tracking field source; exact
backorder-to-picking linkage; exact notification UI granularity; exact
retry constants; exact operation-level idempotency key schema; exact
fulfillment location-confirmation mechanism (core Location reference vs.
live `assignedLocation` read).

**Must not be implemented yet:** no fulfillment binding model, no
FulfillmentOrder mutation code, no tracking-update code.

## 10. Permissions / roles concept

| Source decisions | What the flow uses |
| --- | --- |
| `setup-ux-principles.md` Principle 10 (accepted product-UX input) | Admin vs. functional-user role split |
| `product-vision.md` personas P1–P4 (accepted product-vision input) | Conceptual role-to-persona mapping |
| DEC-004; DEC-005; DEC-006 (no `sudo()`-based boundary crossing) | Isolation-mechanism constraint (record rules, not `sudo()`) |
| DEC-009 §"Audit requirements" | Reviewer/Manual-Review-Owner role rationale (confirmations must record who acted) |

**Routes to Master Blueprint:** exact Odoo security groups; exact
`ir.model.access` rows; exact access-control CSVs; whether the four
conceptual roles map one-to-one to Odoo groups or finer-grained
combinations.

**Must not be implemented yet:** no security group, access right, or record
rule of any kind exists or is authorized.

---

## Cross-flow: what must not be implemented yet (summary)

None of the following exist, and none is authorized by
[`ux-operator-flow.md`](../02-product/ux-operator-flow.md) or
[`DEC-012`](../04-decisions/DEC-012-ux-operator-flow-strategy.md):

- Any Odoo module, manifest, model, view, controller, or security file.
- Any binding, job/log, or settings data model.
- Any GraphQL client, webhook receiver, or `ir.cron` job.
- Any inventory or fulfillment mutation code.
- Any security group, access right, or record rule.

The no-code gate (`CLAUDE.md` §4–§5) remains in force until ChatGPT approves
the full Phase 1 research-phase exit
(`../05-qa/quality-feedback-loop.md` §10) and separately opens a dedicated
implementation gate.

## What routes to the Master Blueprint (consolidated)

- Exact Odoo views/menus/wizards/widgets/field names for every flow.
- Exact data models: binding (schema shape, per DEC-006/008), job/log/error
  (per DEC-009/`phase1-domain-model-brief.md` Domain 8), inventory mapping
  (per DEC-010), fulfillment operation-key (per DEC-011), settings/
  feature-flag (per DEC-008).
- Exact security groups / access rights / record rules for the four
  conceptual roles.
- Exact copy/wording for setup steps, dashboard labels, error reasons, and
  suggested fixes.
- Exact mutation choices (`productSet` vs. bulk variant mutations;
  `inventorySetQuantities` vs. `inventoryAdjustQuantities`), cron cadence,
  and retry/backoff constants.
- Exact notification-UI and feature-flag-UI granularity.

## Review checklist for ChatGPT / Fable

1. Does every flow in `ux-operator-flow.md` cite the DEC section it draws on,
   with no unattributed new architecture claim?
2. Does any flow contradict a DEC-003 through DEC-011 "UX implications"
   section, safe default, or rejected approach (RA-006, RA-008, RA-009,
   RA-014, RA-015, RA-016, RA-017, RA-018 through RA-023)?
3. Does any flow decide something DEC-008 explicitly routed here (the
   feature-flag/config **mechanism**) versus merely describing the
   operator-facing experience of it?
4. Is every "routes to Master Blueprint" item in this bridge also listed in
   `ux-operator-flow.md`'s own "What this document does not decide" section
   or DEC-012's "What remains open" section (no silently dropped open item)?
5. Is anything here, even implicitly, authorizing code, a model, a view, or
   a security file?
