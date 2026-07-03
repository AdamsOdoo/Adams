# DEC-016 — Master Blueprint Sprint D: UI/UX Screen Design Blueprint

> **Proposed decision record** for the premium **Odoo 19 ↔ Shopify
> Connector**, prepared in **Master Blueprint Sprint D** after DEC-015
> acceptance (2026-07-03) closed Master Blueprint Part C. Proposes
> acceptance of the **UI/UX Screen Design Blueprint** (Part D), which
> resolves **MBQ-53** at screen-design level. Companion documents:
> [`../03-architecture/master-blueprint.md`](../03-architecture/master-blueprint.md),
> [`../03-architecture/master-blueprint-ui-ux-screen-design.md`](../03-architecture/master-blueprint-ui-ux-screen-design.md),
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
> Companion review-log entry:
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-013**, Proposed for ChatGPT review).

## Status

**Proposed for ChatGPT review — NOT accepted.** This record proposes, it
does not decide; ChatGPT is the acceptance authority. Not
implementation-authorizing under any outcome — see *No implementation
authorized* below. Starting point: PR #74 merged into `Shopify-connector`,
merge commit `b6199f78064ae4e1934bccee630a14b3d7eef438` (Accept Master
Blueprint Sprint C Inventory and Fulfillment — DEC-015), confirmed as the
base before editing.

> **Proposal note (2026-07-03).** Master Blueprint Part D (UI/UX Screen
> Design Blueprint) was **Not started** before this sprint and is now
> **proposed** as
> [`../03-architecture/master-blueprint-ui-ux-screen-design.md`](../03-architecture/master-blueprint-ui-ux-screen-design.md).
> It converts the ten accepted DEC-012 operator flows and the accepted
> Part A/B/C blueprints into a screen inventory, navigation/information
> architecture, Odoo-native interaction patterns, blueprint-level screen
> specs, per-screen empty/loading/success/error/manual-review states, a
> UX-copy/error-message style guide, and a premium UI/UX acceptance
> checklist. **Until ChatGPT accepts this record, MBQ-53 remains open** and
> operator-facing screen implementation remains blocked. **DEC-003 through
> DEC-015 are unchanged. Part E (implementation-planning bridge) remains
> not started. Implementation remains blocked.**

## Date

2026-07-03.

## Scope

**Master Blueprint Sprint D only** — the **UI/UX Screen Design Blueprint**
(Part D): screen inventory under the single-shared-surface rule;
navigation / information architecture (proposed menu tree + inter-screen
routing + role-gated visibility); Odoo-native interaction patterns (reused
vs custom, at blueprint level); a global screen-state model; blueprint-level
screen specs for the setup wizard, store settings, dashboard/command center,
sync center, error center + manual-review queue, matching/duplicate-
prevention center, product preview/diff, customer matching/review,
order-import touchpoints (no dedicated screen, per MBQ-26), inventory
location-mapping/first-push/settings, fulfillment log/notification/mismatch,
and the conceptual permissions/roles visibility; a UX-copy/error-message
**style guide** (not final copy); cross-screen consistency rules; and a
premium UI/UX acceptance checklist. Does **not** cover Part E
(implementation-planning bridge, not started), exact Odoo view/menu/action
XML, exact model/field/group names, exact user-facing copy, tests, or
implementation tickets. Does **not** modify DEC-003 through DEC-015.

## Accepted context (confirmed before editing)

- **DEC-003 through DEC-015 are all Accepted by ChatGPT** and are unchanged
  by this sprint. Part A (DEC-013), Part B (DEC-014), and Part C (DEC-015)
  are reused as binding inputs, not re-derived.
- **DEC-012 (ten operator flows) is Accepted** and is the behavioural spine
  this part gives screens to.
- **AR-002 through AR-012 are all Accepted**
  (`../05-qa/architecture-review-log.md`).
- **RA-001 through RA-023 are binding rejected approaches**
  (`../05-qa/rejected-approaches-log.md`); this sprint checked the log and
  reintroduces none — the acceptance checklist explicitly encodes the
  UX-facing ones (RA-006/008/009/013/014/015/016) as negative checks.
- **PR #74 merged into `Shopify-connector`**, merge commit
  `b6199f78064ae4e1934bccee630a14b3d7eef438` — confirmed as this sprint's
  required base before editing.
- **Master Blueprint Part D was Not started** before this sprint — confirmed
  before editing.
- **MBQ-53 was open** and blocks operator-facing screen implementation —
  this sprint proposes to resolve it at screen-design level; it stays open
  until this record is accepted.
- **Implementation is still blocked** — confirmed before editing, unaffected
  by this proposal.

## Proposed decision

Propose that ChatGPT accept the **Master Blueprint UI/UX Screen Design
Blueprint (Part D)** package:

1. **The Part D blueprint document**
   ([`../03-architecture/master-blueprint-ui-ux-screen-design.md`](../03-architecture/master-blueprint-ui-ux-screen-design.md))
   — all 22 sections, every statement labelled per `CLAUDE.md` §8.
2. **The open-questions register update** — MBQ-53 marked **Proposed
   partially resolved by DEC-016 (Sprint D)**; no other MBQ row decided; no
   new MBQ row added.
3. **The index update** — `master-blueprint.md` Part D row moved to
   **Proposed via DEC-016**; Part E preserved as Not started; the
   implementation-gate criteria unchanged.
4. **AR-013** logged as **Proposed for ChatGPT review**.

Explicit proposal points (each **proposed**, not decided by this record):

- **(A)** **Single-shared-surface screen inventory** — one role-gated
  dashboard/sync-center/error-center/manual-review queue; domain modules
  contribute, never fork (RA-013; DEC-008 §K rule 2). *Proposed.*
- **(B)** **MBQ-53 proposed partially resolved** — the screen-design layer
  is proposed complete, but MBQ-53's full closure additionally depends on
  its still-open sibling rows (**MBQ-03** exact XML IDs, **MBQ-22** exact
  copy, **MBQ-44** exact groups, **MBQ-45** surface split, **MBQ-06**
  readiness split), which this part **accommodates but does not decide**;
  and on this record's acceptance. Hence *partially*, not fully, resolved.
- **(C)** **Order-import remains screen-less (MBQ-26, DEC-014)** — the
  blueprint delivers the two required error-center extensions (inline
  per-component financial-evidence breakdown; direct matching-flow links for
  two-click resolve+retry) as extensions of the existing contract, not a new
  surface. *Restated from DEC-014, not re-decided.*
- **(D)** **Open recommendations left open** — **MBQ-33** (first-push guard
  granularity), **MBQ-34** (ongoing apply-mode), **MBQ-41** (per-order
  notification override), **MBQ-35/MBQ-32** (`on_hand` exposure / quantity
  source), **MBQ-45** (surface split / roles→groups), **MBQ-06** (readiness
  split): the screens are designed to **accommodate either resolution**;
  **none is decided here.** *Proposed to remain open.*
- **(E)** **No new MBQ row added** — the screen design consumes existing open
  questions rather than surfacing new ones; MBQ-60 through MBQ-63 remain new
  and open, unchanged. *Proposed.*
- **(F)** **Premium acceptance checklist** grounded in `product-vision.md` /
  `setup-ux-principles.md` as **recommendation-level inputs** (both "decide
  nothing"; both predate DEC-003 and are reconciled against it). *Proposed as
  the pre-implementation bar for ChatGPT to ratify or amend.*

## What remains open

- **MBQ-53** stays **open** until ChatGPT accepts this record; even then, it
  is only *partially* resolved, with the sibling rows above still open.
- **MBQ-03/MBQ-22/MBQ-44/MBQ-45/MBQ-06** — exact XML IDs, copy, groups,
  surface split, readiness split — all **open**.
- **MBQ-33/MBQ-34/MBQ-41/MBQ-35/MBQ-32** — open recommendations the screens
  accommodate but do not decide.
- **MBQ-04/MBQ-05/MBQ-07/MBQ-08/MBQ-13/MBQ-23/MBQ-24/MBQ-25/MBQ-54/MBQ-55/
  MBQ-56/MBQ-60/MBQ-61/MBQ-62/MBQ-63** — screen-relevant but owned elsewhere;
  routed, not decided.
- **Primary MVP persona** (RB-13, `product-vision.md`) — open.
- **Part E** (implementation-planning bridge) — not started.

## No implementation authorized

This record, whether or not it is accepted, **does not authorize
implementation.** It creates no Odoo module, model, view, menu, controller,
security file, manifest, test, CI workflow, or dependency change. The
no-code gate (`CLAUDE.md` §4–§5) remains in force. Per `master-blueprint.md`
*Criteria for when implementation may later be opened*, implementation of any
operator-facing screen requires **this Part D to be accepted** and, even
then, a **separate** explicit ChatGPT implementation-gate approval.

## Consequences

- **If accepted:** MBQ-53 becomes partially resolved; Part D becomes the
  accepted screen-design contract every operator-facing implementation must
  follow; the premium UI/UX acceptance checklist (§19) becomes the
  pre-implementation bar; Part E becomes the next recommended sprint. AR-013
  moves to Accepted. Implementation stays blocked pending a separate gate.
- **If revised:** the blueprint is amended per ChatGPT/Fable findings on the
  same branch/PR before acceptance, as with DEC-013/014/015.
- **If rejected:** MBQ-53 stays fully open; no screen-design contract exists;
  the file remains a proposal only.

## Alternatives considered

- **Fold screen design into Part E (implementation-planning bridge)** —
  rejected: `master-blueprint.md` requires Part D as its own part, before any
  operator-facing implementation, and MBQ-53 is explicitly routed to a
  dedicated UI/UX Screen Design Blueprint sprint.
- **Design a dedicated order-import screen** — rejected: MBQ-26 is already
  decided (DEC-014) as *no dedicated screen*, conditional on the two
  error-center extensions, which this part delivers instead.
- **Decide the open recommendations (MBQ-33/34/41/45) to simplify the
  screens** — rejected: those are ChatGPT/implementation-planning decisions;
  the screens accommodate either resolution rather than pre-empting them.
