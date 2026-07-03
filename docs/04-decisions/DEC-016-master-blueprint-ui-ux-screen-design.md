# DEC-016 — Master Blueprint Sprint D: UI/UX Screen Design Blueprint

> **Proposed decision record** for the premium **Odoo 19 ↔ Shopify
> Connector**, prepared in **Master Blueprint Sprint D** after DEC-015
> acceptance (2026-07-03) closed Master Blueprint Part C. Proposes to accept
> the **UI/UX Screen Design Blueprint** (Part D). **Proposed for ChatGPT
> review — not accepted.** Companion documents:
> [`../03-architecture/master-blueprint.md`](../03-architecture/master-blueprint.md),
> [`../03-architecture/master-blueprint-ui-ux-screen-design.md`](../03-architecture/master-blueprint-ui-ux-screen-design.md),
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
> Companion review-log entry:
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-013**, Proposed for ChatGPT review).

## Status

- **Status:** **Proposed → for ChatGPT review.** Not accepted. Not
  implementation-authorizing under any outcome — see *No implementation
  authorized* below.
- **Date:** 2026-07-03.
- **Deciders:** Proposed by Claude (Master Blueprint Sprint D). Approver:
  **ChatGPT** (pending). This record does **not** accept anything on
  ChatGPT's behalf.
- **Phase:** Architecture (Master Blueprint, documentation only).
- **Related:** AR-013 (`../05-qa/architecture-review-log.md`, Proposed for
  ChatGPT review); the companion Part D blueprint document above; DEC-003
  through DEC-015 (accepted context, **unmodified**); MBQ-53 (open-questions
  register).
- **Starting point:** PR #74 merged into `Shopify-connector`, merge commit
  `b6199f78064ae4e1934bccee630a14b3d7eef438` (Accept Master Blueprint Sprint
  C — Inventory and Fulfillment, DEC-015), confirmed as the base before
  editing.

## Part D is documentation-only

**This sprint and this record are documentation-only.** The no-code gate
(`CLAUDE.md` §4–§5) is in force. Part D produces **no** Odoo modules,
models, views, XML, security files, manifests, tests, or CI, and **no**
exact model/field/view/menu/action XML IDs, security group IDs, or access
CSV rows (those remain **MBQ-01/02/03/44**, open). It is a screen-design
blueprint — screen inventory, navigation/information architecture,
Odoo-native interaction patterns, per-screen specs, per-screen states,
microcopy patterns, and a premium acceptance checklist — **not** wireframe
artwork and **not** code.

## Scope

**Master Blueprint Sprint D only** — the **UI/UX Screen Design Blueprint**
(Part D): the operator-facing screen inventory and its grouping;
app-entry/navigation and information architecture; the setup wizard screens;
the store settings surface; the dashboard/command center; the sync
center/job monitor; the error center/recovery + manual-review queue; the
matching/duplicate-prevention center; the product, customer, order,
inventory, and fulfillment screens; the permissions/roles visibility model;
the shared states & microcopy patterns; cross-screen consistency; and a
premium UI/UX acceptance checklist. Does **not** cover: exact user-facing
copy strings (**MBQ-22**), exact Odoo identifiers (**MBQ-01/02/03/44**),
wireframe artwork, implementation tickets, Part E (implementation-planning
bridge), or any change to DEC-003 through DEC-015.

## Accepted context (reused, not re-derived)

- **DEC-003 through DEC-015 are all Accepted by ChatGPT** (DEC-015 on
  2026-07-03) — reused as fixed inputs; **none is modified by this record.**
- **AR-002 through AR-012 are all Accepted**
  (`../05-qa/architecture-review-log.md`).
- **RA-001 through RA-023 are binding rejected approaches**
  (`../05-qa/rejected-approaches-log.md`); this sprint checked the log and
  reintroduces none — notably **RA-013** (no parallel per-domain dashboards)
  shapes the single-command-center navigation.
- **Master Blueprint Part A (DEC-013), Part B (DEC-014), and Part C
  (DEC-015)** are accepted and are the substrate/domain contracts this
  screen blueprint renders — reused, not re-derived.
- **PR #74 merged into `Shopify-connector`**, merge commit
  `b6199f78064ae4e1934bccee630a14b3d7eef438` — confirmed as this sprint's
  required base before editing.
- **Master Blueprint Part D was Not started** before this sprint — confirmed
  before editing.
- **MBQ-53 was open** and blocks operator-facing screen implementation —
  confirmed before editing; this record proposes to partially resolve it.
- **Part E (implementation-planning bridge) was Not started** — unchanged.
- **Implementation was blocked** — confirmed before editing, unchanged.

## Proposed decision

**This record proposes that ChatGPT accept the Master Blueprint Sprint D
UI/UX Screen Design Blueprint** package. **Master Blueprint Part D — UI/UX
Screen Design Blueprint**
([`master-blueprint-ui-ux-screen-design.md`](../03-architecture/master-blueprint-ui-ux-screen-design.md))
is proposed as the blueprint-level screen design for the operator experience,
namely:

1. **Screen inventory (§0)** — fourteen operator-facing surfaces (S1–S14)
   mapped to the ten DEC-012 flows and the Part A/B/C surfaces, under the
   **single-shared-surface rule** (one dashboard, one sync center, one error
   center; domains contribute via the Part A §A.5 seams, never parallel
   dashboards — DEC-008 §K rule 2 / RA-013).
2. **App entry & navigation (§1)** — a dedicated top-level connector app with
   five separated regions (operations, recovery, matching/mappings, setup,
   settings), a persistent connection-health indicator, and a single-store
   store-context slot designed multi-store-safe without deciding MBQ-46.
3. **Setup wizard (§2)** — the accepted 11-step sequence (Part A §E) rendered
   as an Odoo guided flow, with credential masking (never re-shown),
   visible/re-runnable readiness checks, and the accepted guardrails before
   enabling sync (no business write before setup complete; first-push guard
   never silently skipped; notification default never pre-checked).
4. **Store settings (§3)** — a domain-segmented settings surface over the
   seven Part A §B config concepts plus feature flags (§I), the DEC-014
   gateway→journal mapping placeholder (MBQ-30), and the inventory/fulfillment
   posture — presenting concepts and accepted posture, **not** turning open
   technical questions into accepted implementation fields.
5. **Dashboard/command center (§4)** — the nine accepted cards (Part A §F),
   exception-first, every count clickable, no vanity metrics, with designed
   empty/first-run states.
6. **Sync center/job monitor (§5)** — filters/columns over the six job
   sources, ten states, and sixteen error classes; state-conditional retry;
   verify-current-state; cancel/supersede; source-classification visibility
   that surfaces only accepted sources (MBQ-62 left open, no fabricated
   seventh source).
7. **Error center/recovery (§6)** — the nine required elements (Part A §H),
   grouping by the fixed error classes and manual-review sub-reasons,
   human-readable reason first (no raw stack trace as primary UX), retry
   eligibility, and confirmation-required flows; the order-import touchpoints
   handled here per DEC-014 §C.14 (no dedicated order screen).
8. **Matching/duplicate-prevention center (§7)** — structural match-key
   priority, mandatory blocking duplicate-prevention preview, product/customer/
   order resolution, manual binding review, and the DEC-014 create/bind policy
   visibility (interactive-preview vs automated-pre-create-gate).
9. **Product screens (§8)** — import/export/update previews and diffs, the
   five preview states (Part B §A.16), variant/media/price visibility,
   draft-first/publish control, and the mandatory destructive-write guard.
10. **Customer screens (§9)** — email-only automatic matching (DEC-014,
    MBQ-31), the clearly-flagged no-PII fallback (MBQ-29 direction), and
    manual review — never inventing PII.
11. **Order surfaces (§10)** — via the sync/error centers (no dedicated
    screen, MBQ-26), with the financial-evidence breakdown, the permanent
    total-check guard, product/customer resolution, gateway→journal
    visibility, and the evidence-refresh-only order-edit posture (DEC-014
    point J).
12. **Inventory screens (§11)** — location mapping (inventory-owned),
    guarded first-push preview + confirmation record, quantity-source
    explanation (MBQ-32 residual), apply-mode and first-push-granularity
    **recommendation visibility without deciding MBQ-34/MBQ-33**, and sync/
    reconciliation status.
13. **Fulfillment screens (§12)** — FulfillmentOrder-based queue/detail,
    tracking write-back (`carrier_tracking_ref`/`carrier_tracking_url`/
    `carrier_id`), notification-default visibility, location-mismatch review
    (`assignedLocation` authoritative; `ambiguous match` widening per
    DEC-015), backorder linkage, and MBQ-60/61/62 residual visibility (not
    resolution).
14. **Permissions/roles UX (§13)** — the conceptual four-role model (Part A
    §J) rendered as role-conditional visibility/affordances, with **no exact
    security CSV/group XML IDs** (MBQ-44) and the admin-vs-functional surface
    split left open (MBQ-45).
15. **States & microcopy patterns (§14)** and **cross-screen consistency
    (§15)** — one shared state catalog (empty/loading/success/warning/
    blocked-manual-review/failed-retryable/failed-terminal/confirmation/
    destructive-write/notification/financial-mismatch/location-mismatch),
    shared components/status-badges/actions/audit access, and the operator
    journey continuity (dashboard → error → fix → retry → verify).
16. **Premium UI/UX acceptance checklist** — twelve criteria derived from the
    product-vision premium quality bar and non-negotiables and the setup-ux 12
    principles, proposed as the Part D acceptance gate.

## MBQ-53 disposition — proposed partially resolved

**This record proposes to mark MBQ-53 (screen-level UI/UX design blueprint)
`Proposed partially resolved` — it remains open until this record is
accepted.**

**Justification.** The Part D blueprint proposes to satisfy the screen-design
*layer* MBQ-53 requires: the screen inventory; navigation/information
architecture; Odoo-native interaction patterns; screen-level specs (purpose,
users, entry points, information, actions, blocked states, links, decision/MBQ
dependencies) for the dashboard, setup wizard, store settings, sync center,
error center, matching center, and preview/review screens (product diff,
inventory first-push, duplicate-prevention); empty/loading/success/error/
manual-review states for every screen; UX copy **guidelines** and error-message
**style**; and a premium UI/UX acceptance checklist. It is proposed as
**partially** resolved (not full) because MBQ-53's own text spans "UX copy
guidelines" whose **exact strings are the separate open MBQ-22**, and screen
implementation still requires the exact identifiers of **MBQ-01/02/03/44** and
a resolution of the admin-vs-functional-user surface split (**MBQ-45**); pixel
wireframe artwork is out of this screen-blueprint's scope. Marking MBQ-53
anything stronger would over-claim against those live rows and against the fact
that this record is not yet accepted. **Per the register vocabulary note, a
sprint whose companion decision record is still `Proposed` yields a `Proposed
partially resolved` label that stays open until acceptance.**

## MBQs that remain open (explicitly not resolved by this record)

This record resolves **no** implementation-level or domain open question. The
following remain **open**, carried forward untouched (this is the explicit
list required for a Part D record):

- **Screen/UX residuals of MBQ-53:** **MBQ-22** (exact user-facing copy),
  **MBQ-01/02** (model/field names), **MBQ-03** (view/menu/action XML IDs),
  **MBQ-44** (security groups/access CSVs/record rules), **MBQ-45**
  (roles→groups mapping + admin-vs-functional surface split).
- **Core/setup/config:** **MBQ-04** (credential storage-at-rest), **MBQ-05**
  (custom-app creation surface/token mechanics), **MBQ-06** (readiness-check
  essential-vs-nice), **MBQ-07** (feature-flag exact implementation — direction
  accepted via DEC-013), **MBQ-08** (store-disconnect data retention),
  **MBQ-09** (protected-data obligations), **MBQ-10** (turnkey install),
  **MBQ-54** (module uninstall/disable lifecycle).
- **Binding/job/log/error:** **MBQ-13** (stale/recreated review detail),
  **MBQ-16** (retry ceilings/backoff), **MBQ-19** (job/log model shape),
  **MBQ-20** (operation-key schema), **MBQ-21** (serialization guard),
  **MBQ-22** (copy, above).
- **Product/customer/order:** **MBQ-24** (media delete-on-omit), **MBQ-27**
  (Odoo tax representation), **MBQ-28** (draft-artifact guard), **MBQ-55**
  (binding model/field names), **MBQ-56** (total-check tolerance), **MBQ-57**
  (whole-order-hold alternative), **MBQ-58** (order-identity nuances),
  **MBQ-59** (exact eligibility/match-confidence detail — policy accepted via
  DEC-014, detail open).
- **Inventory/fulfillment:** **MBQ-33** (first-push granularity — recommendation
  only), **MBQ-34** (apply-mode — recommendation only), **MBQ-35** (`on_hand`
  exposure), **MBQ-41** (notification granularity — recommendation only),
  **MBQ-60** (`stock_delivery`/`delivery` dependency), **MBQ-61**
  (FulfillmentOrder lifecycle events), **MBQ-62** (Odoo-event job-source
  classification), **MBQ-63** (inventory-webhook payload/subscription/Phase-1
  scope). MBQ-32/36/38/40/42/43 keep their DEC-015 partially-resolved status;
  MBQ-37/39 keep their DEC-015 fact-verification-resolved status — **unchanged
  by this record.**
- **Deployment/perf/permissions:** **MBQ-17, MBQ-18, MBQ-46, MBQ-49, MBQ-51,
  MBQ-52** and any remaining implementation-planning / official-doc-verification
  rows.

**This record does not decide MBQ-33, MBQ-34, MBQ-41, MBQ-60, MBQ-61, MBQ-62,
or MBQ-63.** Where the screen blueprint shows a posture for an open row (e.g.
review-then-apply for MBQ-34, per-mapped-pair for MBQ-33, global/per-store for
MBQ-41), it is presented as a **recommendation** with the decision owner
(ChatGPT) preserved and the screen designed to accommodate the recommended
posture without deciding it.

## What this proposal decides (if accepted)

- The blueprint-level screen design of the operator experience (items 1–16
  above) as the binding basis for later operator-facing implementation
  planning — subject to ChatGPT review.
- The proposed partial resolution of **MBQ-53** (screen-design layer proposed
  complete; exact copy/identifiers/surface-split residuals carried forward).

## What this proposal does NOT decide

- **No implementation authorization** — under any outcome of this review.
- **No start of Part E** (implementation-planning bridge) — remains Not
  started.
- **No exact Odoo model/field names, view/menu/action XML IDs, security
  groups, access CSV rows, or record rules** — MBQ-01/02/03/44 stay open.
- **No exact user-facing copy strings** — MBQ-22 stays open.
- **No resolution of any domain open question** (MBQ-33/34/41/60/61/62/63 and
  all others above stay open); **no change to DEC-003 through DEC-015**, to any
  AR row, or to any RA row.
- **No new error class, job source, guard, guard bypass, or scope** — the fixed
  Part A registries (six sources, ten states, sixteen error classes) are
  reused, never extended.

## Alternatives considered

| Alternative | Why not chosen | Logged as rejected? |
| --- | --- | --- |
| Defer screen design to implementation (design screens ad hoc during coding) | Would risk an inconsistent, non-premium operator experience and violate `master-blueprint.md` criterion 1 (accepted Part D required before operator-facing implementation); MBQ-53 exists precisely to prevent this | No — this is the status quo MBQ-53 blocks, not a design approach to log |
| Per-domain dashboards/sync/error centers (one per module) | Reintroduces **RA-013** (binding rejected) and violates DEC-008 §K rule 2 | Already logged — RA-013 |
| A dedicated order-import screen | Contradicts accepted DEC-014 §C.14 / MBQ-26 (error+sync center sufficient) | No — the accepted decision already forecloses it |
| Fully resolving MBQ-53 (marking it closed) | Over-claims against open MBQ-22 (exact copy) and MBQ-01/02/03/44 (identifiers) and MBQ-45; and this record is only Proposed | No — a labelling choice, not a rejected design |
| Deciding MBQ-33/34/41 within the screen blueprint | Out of scope; these are ChatGPT-owned domain decisions, not screen-design decisions | No — carried forward per the register |

> Every genuinely rejected design alternative is (or already is) recorded in
> `../05-qa/rejected-approaches-log.md` with a revisit condition (`CLAUDE.md`
> §10). This record introduces no new rejected approach.

## No implementation authorized

**This record does not authorize implementation, and is not accepted.** Even
if ChatGPT later accepts it, acceptance is a documentation-level blueprint
acceptance only: no code, Odoo module, model, view, controller, security file,
manifest, test, or CI change is created or permitted, and none may be created
until ChatGPT (1) accepts the required blueprint parts (Part A + the relevant
domain part(s) **and** this accepted Part D for any operator-facing screen),
(2) resolves or consciously accepts the implementation-blocking open questions
for the affected scope, and (3) **separately opens the implementation gate**
per `../05-qa/quality-feedback-loop.md` §10 and `CLAUDE.md` §5 — see
[`../03-architecture/master-blueprint.md`](../03-architecture/master-blueprint.md)
"Criteria for when implementation may later be opened". **Acceptance of this
record alone does not open that gate. Part E remains Not started.**

## Next sprint recommendation

**Master Blueprint Part E — implementation-planning bridge** (Sprint E), a
consolidated verification pass resolving/accepting the implementation-blocking
open questions and sequencing input for `docs/07-implementation-plan` — **only
after ChatGPT review of this Part D**, and per ChatGPT's preference. **Part E
is not started by this sprint.** No implementation is recommended or authorized.

## Evidence / references

- Master Blueprint Part D blueprint —
  [`../03-architecture/master-blueprint-ui-ux-screen-design.md`](../03-architecture/master-blueprint-ui-ux-screen-design.md)
  (this sprint) — access: Accessible — 2026-07-03.
- Master Blueprint Part A/B/C —
  [`../03-architecture/master-blueprint-core-substrate.md`](../03-architecture/master-blueprint-core-substrate.md),
  [`../03-architecture/master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md),
  [`../03-architecture/master-blueprint-inventory-fulfillment.md`](../03-architecture/master-blueprint-inventory-fulfillment.md)
  — accepted context (DEC-013/014/015) — access: Accessible — 2026-07-03.
- DEC-012 operator flows + `ux-operator-flow.md`; `setup-ux-principles.md`
  (P1–P12); `product-vision.md` (premium quality bar, non-negotiables,
  differentiation theme 2) — accepted product/UX inputs — access: Accessible —
  2026-07-03.
- No new external (Shopify/Odoo) research was performed this sprint; all
  platform identifiers referenced are existing, previously-cited facts carried
  from Part A/B/C.

## Review / change control

- **This record proposes Master Blueprint Part D only.** No accepted decision
  is re-litigated; no rejected approach is reintroduced; checked against
  `rejected-approaches-log.md` before drafting.
- **Related:** AR-013 (`../05-qa/architecture-review-log.md`, Proposed for
  ChatGPT review); the companion Part D blueprint document above; DEC-003
  through DEC-015 (accepted context, unmodified).
- **Acceptance procedure:** on ChatGPT acceptance, this record's Status moves
  from `Proposed → for ChatGPT review` to `Accepted by ChatGPT` with the
  acceptance date, AR-013 is promoted to Accepted, `master-blueprint.md` Part
  D status moves to Accepted, and MBQ-53's `Proposed partially resolved` label
  drops its `Proposed` qualifier — mirroring the DEC-013/014/015 acceptance
  pattern. **None of that has happened; this record is Proposed only.**
- **Further changes** to this record require ChatGPT review.
