# DEC-016 — Master Blueprint Sprint D: UI/UX Screen Design Blueprint

> **Accepted decision record** for the premium **Odoo 19 ↔ Shopify
> Connector**, prepared in **Master Blueprint Sprint D** after DEC-015
> acceptance (2026-07-03) closed Master Blueprint Part C, and **accepted
> by ChatGPT on 2026-07-04** — at **screen-design blueprint level only**
> — after duplicate-PR reconciliation (PR #75 closed as superseded), a
> competitor screenshot UX benchmark traceability audit, the Fable Sprint
> D review fixes (F1–F7), and final ChatGPT verification were completed
> on PR #77. Accepts the **UI/UX Screen Design Blueprint** (Part D),
> which **partially resolves MBQ-53** at screen-design level, with the
> sibling/detail rows still open (see *Accepted decision* below).
> Companion documents:
> [`../03-architecture/master-blueprint.md`](../03-architecture/master-blueprint.md),
> [`../03-architecture/master-blueprint-ui-ux-screen-design.md`](../03-architecture/master-blueprint-ui-ux-screen-design.md),
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
> Companion review-log entry:
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-013**, Accepted by ChatGPT via DEC-016).

## Status

**Accepted by ChatGPT.** Acceptance date: **2026-07-04**. **Accepted at
screen-design blueprint level only** — this acceptance is **not
implementation-authorizing** under any outcome (see *No implementation
authorized* below) and is **not a final pixel-level UI approval**;
pixel-level visual design / final wireframe polish is explicitly **not
accepted here**. Starting point: PR #74 merged into `Shopify-connector`,
merge commit `b6199f78064ae4e1934bccee630a14b3d7eef438` (Accept Master
Blueprint Sprint C Inventory and Fulfillment — DEC-015), with the Part D
proposal then prepared and revised across six commits on PR #77 (the
proposal commit; a pre-review strengthening commit; a duplicate-PR
salvage-reconciliation commit; a duplicate-PR-history-correction commit;
a competitor screenshot UX benchmark audit + Fable Sprint D review-fixes
commit; and this acceptance-patch commit), confirmed as the base before
editing. PR #77 head at commit `b1f1ac9da3893b0d62fb803f0e588f889f8c1ab5`
confirmed before this acceptance patch was applied.

> **Acceptance note (2026-07-04).** Accepted after: **(1) duplicate-PR
> reconciliation** — a duplicate Sprint D proposal, PR #75 (branch
> `claude/master-blueprint-sprint-d-ui-ux-screen-design`, head
> `27d521ef322f76472cb69e71fa5e9302b829d0df`), was confirmed to exist; a
> small salvage audit merged four safe, additive completeness items from
> it into this PR (#77); PR #75 was then **closed as superseded by PR
> #77, not merged**; **(2) a competitor screenshot UX benchmark
> traceability audit** — re-verifying six of eight minimum-audit sources
> and adding a direct "Screenshot-evidence lineage" citation to Part D,
> resolving a ChatGPT concern that Part D's grounding in the competitor
> screenshot evidence (`../01-research/ux-ui-benchmark.md`,
> `../00-source-materials/competitor-screenshot-inventory.md`) was only
> **transitive** (via `setup-ux-principles.md`/`product-vision.md`), not
> directly cited; **(3) the Fable Sprint D review fixes (F1–F7)** — all
> applied, documentation-only (governance-attribution and
> cross-reference corrections; no architecture substance changed);
> **(4) final ChatGPT verification** of the resulting PR #77 head commit
> `b1f1ac9da3893b0d62fb803f0e588f889f8c1ab5`. **This acceptance is
> screen-design-blueprint-level only.** **MBQ-53 is partially resolved
> at screen-design level only** — its sibling/detail rows **MBQ-03**
> (exact XML/view/menu IDs), **MBQ-22** (exact copy), **MBQ-44** (exact
> groups/security), **MBQ-45** (admin-vs-functional surface split), and
> **MBQ-06** (readiness split) all **remain open**. **MBQ-33, MBQ-34,
> MBQ-41, MBQ-35, and MBQ-32 remain open recommendations**, not decided
> by this acceptance. **MBQ-60 through MBQ-63 remain open.** **The
> competitor screenshot audit is accepted as sufficient traceability for
> blueprint-level acceptance — it is not a pixel-level visual-design
> review.** Pixel-level visual design / final wireframe polish —
> including the `sh_shopify_connector` "Daily Queue Activity Tracking"
> chart idea flagged during the audit — **remain deferred to a later
> pixel-design pass and are not adopted into the accepted
> screen/dashboard-card set by this acceptance.** **Implementation
> remains blocked; Part E (implementation-planning bridge) remains not
> started.** See *Accepted decision* below for the full accepted package
> and explicit acceptance points.

## Date

2026-07-04 (acceptance). Originally proposed 2026-07-03.

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
XML, exact model/field/group names, exact user-facing copy, tests,
implementation tickets, or **pixel-level visual design / final wireframe
polish** (explicitly out of scope for this acceptance). Does **not** modify
DEC-003 through DEC-015.

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
  this sprint partially resolves it at screen-design level; its sibling
  rows remain open (see acceptance note above).
- **Implementation is still blocked** — confirmed before editing, unaffected
  by this acceptance.

## Accepted decision

**ChatGPT accepts DEC-016** as the accepted **Master Blueprint UI/UX
Screen Design Blueprint (Part D)** package, **at screen-design blueprint
level only**:

1. **The Part D blueprint document**
   ([`../03-architecture/master-blueprint-ui-ux-screen-design.md`](../03-architecture/master-blueprint-ui-ux-screen-design.md))
   — all 22 sections, every statement labelled per `CLAUDE.md` §8, is now
   the **accepted screen-design contract** for the connector's
   operator-facing surfaces.
2. **The open-questions register update** — **MBQ-53 marked partially
   resolved by DEC-016 at screen-design blueprint level**; its sibling
   rows (MBQ-03, MBQ-22, MBQ-44, MBQ-45, MBQ-06) remain open; no other MBQ
   row decided; no new MBQ row added.
3. **The index update** — `master-blueprint.md` Part D row moved to
   **Accepted by ChatGPT via DEC-016**; Part E preserved as Not started;
   the implementation-gate criteria unchanged.
4. **AR-013** moved to **Accepted by ChatGPT**.

Explicit acceptance points (each accepted **at screen-design blueprint
level only**, per this record):

- **(A)** **Single-shared-surface screen inventory — accepted.** One
  role-gated dashboard/sync-center/error-center/manual-review queue;
  domain modules contribute, never fork (RA-013; DEC-008 §K rule 2).
- **(B)** **MBQ-53 — accepted, partially resolved at screen-design level
  only.** The screen-design layer is now accepted complete, but MBQ-53's
  full closure additionally depends on its still-open sibling rows
  (**MBQ-03** exact XML IDs, **MBQ-22** exact copy, **MBQ-44** exact
  groups, **MBQ-45** surface split, **MBQ-06** readiness split), which
  this part **accommodates but does not decide**. Hence *partially*, not
  fully, resolved by this acceptance.
- **(C)** **Order-import remains screen-less (MBQ-26, DEC-014) —
  restated, not re-decided.** The blueprint delivers the two required
  error-center extensions (inline per-component financial-evidence
  breakdown; direct matching-flow links for two-click resolve+retry) as
  extensions of the existing contract, not a new surface.
- **(D)** **Open recommendations remain open — not decided by this
  acceptance.** **MBQ-33** (first-push guard granularity), **MBQ-34**
  (ongoing apply-mode), **MBQ-41** (per-order notification override),
  **MBQ-35/MBQ-32** (`on_hand` exposure / quantity source), **MBQ-45**
  (surface split / roles→groups), **MBQ-06** (readiness split): the
  screens are designed to **accommodate either resolution**; **none is
  decided by this acceptance.**
- **(E)** **No new MBQ row added — confirmed.** The screen design
  consumes existing open questions rather than surfacing new ones;
  MBQ-60 through MBQ-63 remain new and open, unchanged.
- **(F)** **Premium acceptance checklist — accepted as the
  pre-implementation bar.** Grounded in `product-vision.md` /
  `setup-ux-principles.md` as **recommendation-level inputs** (both
  "decide nothing"; both predate DEC-003 and are reconciled against it).
  **Screenshot-audit addendum, accepted:** a pre-acceptance audit found
  the Part D document itself did not directly cite the screenshot
  evidence behind those two documents
  ([`../01-research/ux-ui-benchmark.md`](../01-research/ux-ui-benchmark.md),
  [`../00-source-materials/competitor-screenshot-inventory.md`](../00-source-materials/competitor-screenshot-inventory.md)),
  even though it inherited that grounding transitively. Part D now carries
  an explicit "Screenshot-evidence lineage" traceability note citing both
  directly. **This acceptance treats the competitor screenshot audit as
  sufficient traceability for blueprint-level acceptance** — it is a
  documentation-traceability correction, not a pixel-level visual-design
  review, and it changes no accepted architecture content.
- **(G)** **Pixel-level visual design deferred — not accepted here.**
  This acceptance is a **screen-design blueprint** acceptance only.
  Pixel-level visual design and final wireframe polish are explicitly
  **out of scope** and **not accepted** by this record. One specific gap
  identified during the screenshot audit — `sh_shopify_connector`'s
  demonstrated "Daily Queue Activity Tracking" chart, which has no
  counterpart in Part D's nine-card dashboard — is **explicitly logged as
  a deferred candidate premium visualization idea for a later pixel-design
  pass (Part E)** and is **not adopted into the accepted dashboard
  card set** by this acceptance.

## What remains open

- **MBQ-53** is **partially resolved** by this acceptance at
  screen-design blueprint level only; the sibling rows below remain fully
  open.
- **MBQ-03/MBQ-22/MBQ-44/MBQ-45/MBQ-06** — exact XML IDs, copy, groups,
  surface split, readiness split — all **open**.
- **MBQ-33/MBQ-34/MBQ-41/MBQ-35/MBQ-32** — open recommendations the
  screens accommodate but do not decide; **not decided by this
  acceptance**.
- **MBQ-04/MBQ-05/MBQ-07/MBQ-08/MBQ-13/MBQ-23/MBQ-24/MBQ-25/MBQ-54/MBQ-55/
  MBQ-56/MBQ-60/MBQ-61/MBQ-62/MBQ-63** — screen-relevant but owned elsewhere;
  routed, not decided.
- **Primary MVP persona** (RB-13, `product-vision.md`) — open.
- **Pixel-level visual design / final wireframe polish** — deferred, not
  accepted here; recommended for a later pixel-design pass (Part E).
- **Part E** (implementation-planning bridge) — not started.

## No implementation authorized

This record **does not authorize implementation.** It creates no Odoo
module, model, view, menu, controller, security file, manifest, test, CI
workflow, or dependency change. The no-code gate (`CLAUDE.md` §4–§5)
remains in force. Per `master-blueprint.md` *Criteria for when
implementation may later be opened*, implementation of any
operator-facing screen requires **this Part D acceptance** (now
satisfied at screen-design level) and, even then, a **separate** explicit
ChatGPT implementation-gate approval, which this record does **not**
grant.

## Consequences

- **Now that this is accepted:** MBQ-53 is partially resolved at
  screen-design level; Part D is the accepted screen-design contract
  every operator-facing implementation must follow; the premium UI/UX
  acceptance checklist (§19) is the pre-implementation bar; Part E
  becomes the next recommended sprint. AR-013 moves to Accepted.
  Implementation stays blocked pending a separate gate. Pixel-level
  visual design remains a later, separate pass.
- **If later revised:** any further blueprint amendment requires a new
  ChatGPT review on a new decision record, per the DEC-013/014/015/016
  change-control pattern.

## Alternatives considered

- **Fold screen design into Part E (implementation-planning bridge)** —
  rejected: `master-blueprint.md` requires Part D as its own part, before any
  operator-facing implementation, and MBQ-53 is explicitly routed to a
  dedicated UI/UX Screen Design Blueprint sprint.
- **Design a dedicated order-import screen** — rejected: MBQ-26 is already
  decided (DEC-014) as *no dedicated screen*, conditional on the two
  error-center extensions, which this part delivers instead.
- **Decide the open recommendations (MBQ-33/34/41/45/06/35) to simplify the
  screens** — rejected: those are ChatGPT/implementation-planning decisions;
  the screens accommodate either resolution rather than pre-empting them.
- **Adopt the `sh_shopify_connector` activity-chart idea into the accepted
  dashboard card set now** — rejected: would change accepted architecture
  substance (the nine-card dashboard) without a dedicated review; logged
  instead as a deferred premium candidate for a later pixel-design pass.

## Review / change control

- **This record accepts Master Blueprint Part D at screen-design
  blueprint level only.** No accepted decision is re-litigated; no
  rejected approach is reintroduced; checked against
  `rejected-approaches-log.md` before this patch.
- **Related:** AR-013 (`../05-qa/architecture-review-log.md`, Accepted by
  ChatGPT via DEC-016); the companion Part D blueprint document above;
  DEC-003 through DEC-015 (accepted context, unmodified).
- **Further changes** to this record require ChatGPT review, mirroring
  the DEC-013/014/015 change-control pattern.
