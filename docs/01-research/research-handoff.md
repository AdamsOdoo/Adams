# Research Handoff (rolling)

> Continuity lives in GitHub, not chat. The **current entry (DEC-010/DEC-011 Acceptance
> Patch)** is immediately below, in the **compact handoff format**
> (`../06-prompts/session-handoff-template.md`); **AR-007 + AR-008 Decision Preparation**,
> **DEC-008/DEC-009 Acceptance Patch**,
> **AR-004 + AR-006 Decision Preparation**,
> **DEC-007 Acceptance Patch**, **Phase 1 Domain Model + DEC-003 Scope-Hole Closure**,
> **DEC-004/005/006 Acceptance Patch**, **Evidence Refresh + Combined AR-002/003/005
> Decision Preparation**, **Control-Room Reset Sprint 1**, **RB-14 Architecture Preparation
> — Part 2**, **RB-14 Part 1**, **Research Sprint C2**, **Product Sprint G**, **Sprint F**,
> **Sprint E**, **Sprint D**, **Sprint C**, **Sprint B**, and **Sprint A** handoffs are
> retained underneath as history. The running **Sprint checkpoint log** (one note per
> stage, all sprints) is at the very bottom. The **product-side** handoff lives at
> [`../02-product/product-research-handoff.md`](../02-product/product-research-handoff.md).

---

### DEC-010/DEC-011 Acceptance Patch — compact handoff (2026-07-02)

> **Documentation acceptance patch, not implementation.** Confirmed PR #66 merged into
> `Shopify-connector` (merge commit `14af2fb3becb47ba7c32a50715d85f6eaab0d855`) before
> editing; DEC-010 and DEC-011 confirmed `Proposed for ChatGPT review`; AR-007 and AR-008
> confirmed proposed only, not accepted; RA-018 through RA-023 confirmed `PROPOSED`;
> DEC-003 through DEC-009 confirmed accepted/unchanged; implementation confirmed still
> blocked. Branch `claude/accept-dec010-dec011-dxkuzi` (harness-assigned; the sprint's
> preferred name was `architecture/accept-dec010-dec011`, so this branch-name discrepancy
> is recorded here per the session rule) was already checked out based exactly on that
> merge commit — no re-basing needed.

- **Branch / PR:** `claude/accept-dec010-dec011-dxkuzi` → draft PR into `Shopify-connector`,
  opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/04-decisions/DEC-010-inventory-architecture-strategy.md`,
  `docs/04-decisions/DEC-011-fulfillment-architecture-strategy.md`,
  `docs/03-architecture/ar007-inventory-architecture-decision-brief.md`,
  `docs/03-architecture/ar008-fulfillment-architecture-decision-brief.md`,
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/01-research/research-handoff.md` (this
  file).
- **What changed:** DEC-010 Status changed from `Proposed for ChatGPT review` to
  **`Accepted by ChatGPT`**, acceptance date **2026-07-02**; DEC-011 Status changed the
  same way, same acceptance date. Both records got an acceptance note recording the PR #66
  merge and the Fable **ACCEPT WITH MINOR CHANGES** review, while preserving every
  documented caveat unchanged (exact Odoo ORM source for "Free to Use," exact first-push
  guard granularity, exact mutation choice per trigger, exact cron cadence, unverified
  webhook topic strings, feature-flag/config UI routing, `available` as the Phase 1
  default target with `on_hand` requiring Master Blueprint justification, `committed`
  never written; exact tracking field source, exact backorder linkage, exact notification
  UI granularity, exact retry constants, exact fulfillment location-confirmation
  mechanism, exact operation-level idempotency key schema, and the multi-package/
  multi-location deferral). Both records also got a compact **shared Shopify Location
  reference clarification** note recording that ChatGPT's acceptance ratifies the
  clarification against DEC-008: `shopify_connector_core` may hold a minimal Shopify-side
  Location reference/cache/list (never Odoo-location IDs or mapping decisions);
  `shopify_connector_inventory` keeps owning the Odoo↔Shopify mapping;
  `shopify_connector_fulfillment` never depends on inventory; DEC-008's dependency
  direction is unchanged and no new module is created. The AR-007 and AR-008 decision
  briefs were updated to state that AR-007/AR-008 are now accepted through DEC-010/DEC-011,
  while remaining evidence-backed briefs that authorize no implementation.
  `docs/04-decisions/README.md`'s DEC-010/DEC-011 entry moved from "Also present (not yet
  accepted)" to "Also accepted," citing the 2026-07-02 acceptance date and noting RA-018
  through RA-023 are now binding, and recording that all architecture decisions AR-002
  through AR-008 are now accepted. `architecture-review-log.md`'s AR-007 and AR-008 table
  rows moved from "Proposed for ChatGPT review" to "Accepted by ChatGPT," and a compact
  acceptance note was appended confirming the shared Location reference clarification is
  ratified against DEC-008, DEC-003/004/005/006/007/008/009 are unchanged, and
  implementation remains blocked. RA-018 through RA-023 in `rejected-approaches-log.md`
  had the `PROPOSED:` prefix removed and their "Related decision record" cells updated to
  cite DEC-010/DEC-011's `Accepted by ChatGPT, 2026-07-02` status — **these six rows are
  now binding final rejected approaches** (`CLAUDE.md` §10 applies in full).
- **Items deferred:** exact Odoo ORM sources, exact schemas, exact operation-key schema,
  exact fulfillment location-confirmation mechanism, exact feature-flag/config UI, exact
  notification UI, exact retry constants, and all Master Blueprint items; UX/operator-flow
  sprint; the Master Blueprint; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** none new (RA-018–023 finalized, not created). **New technical debt:** none
  (no code). **Architecture concerns:** AR-007/AR-008 now **Accepted** (via DEC-010/
  DEC-011) — all of AR-002 through AR-008 are now accepted; the shared Shopify Location
  reference clarification is ratified against DEC-008.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches finalized (RA-018–023) ·
  technical debt logged (none applicable — no code) · repeated-issue escalation applied
  (none at threshold) — all **YES**.
- **Next recommended session:** 1) **UX/operator-flow sprint**; 2) **Master Blueprint**,
  after that gate; 3) **Implementation only after a separate ChatGPT gate.**
- **Stop condition:** stopped after one commit + one **draft** PR into `Shopify-connector`
  (not merged). PR #66 merge confirmed first. DEC-003/DEC-004/DEC-005/DEC-006/DEC-007/
  DEC-008/DEC-009 not edited; no code files changed; implementation still not authorized;
  `main` and plain `dev` untouched. Awaiting further instruction.

---

### AR-007 + AR-008 Decision Preparation — compact handoff (2026-07-02)

> **Documentation / decision-preparation sprint, not implementation.** Confirmed PR #65
> merged into `Shopify-connector` (merge commit
> `dfb0199c9588ae600216ef549d160d0ced15034f`) before editing; DEC-003/004/005/006/007/008/009
> confirmed **Accepted by ChatGPT**; RA-001 through RA-017 confirmed **binding**;
> AR-002/AR-003/AR-004/AR-005/AR-006 confirmed **Accepted**; AR-007/AR-008 confirmed **Not
> decided**; implementation confirmed still blocked. Branch
> `claude/ar007-ar008-decision-prep-5tdwfv` (harness-assigned; the sprint's preferred name
> was `architecture/ar007-ar008-decision-prep`, so this branch-name discrepancy is recorded
> here per the session rule) was already checked out based exactly on that merge commit — no
> re-basing needed.

- **Branch / PR:** `claude/ar007-ar008-decision-prep-5tdwfv` → draft PR into
  `Shopify-connector`, opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/03-architecture/ar007-inventory-architecture-decision-brief.md`
  (new), `docs/03-architecture/ar008-fulfillment-architecture-decision-brief.md` (new),
  `docs/03-architecture/ar007-ar008-evidence-refresh.md` (new),
  `docs/04-decisions/DEC-010-inventory-architecture-strategy.md` (new),
  `docs/04-decisions/DEC-011-fulfillment-architecture-strategy.md` (new),
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/01-research/research-handoff.md` (this
  file), `docs/06-prompts/ar007-ar008-decision-prep-prompt.md` (new, archive).
- **What changed:** authored
  [`ar007-inventory-architecture-decision-brief.md`](../03-architecture/ar007-inventory-architecture-decision-brief.md)
  — Phase 1 inventory source-of-truth posture (Odoo as ongoing source, controlled
  first-sync import from Shopify, no autonomous bidirectional conflict resolution),
  Shopify inventory-object mapping (`(store, inventory_item_id, location_id)` binding
  identity), the Odoo quantity concept (Odoo's "Free to Use" as the directional Phase 1
  candidate, exact field open), location architecture (explicit non-inferred mapping;
  block on missing/ambiguous mapping; a clarified ownership principle — `core` may hold
  a minimal Shopify Location reference, `inventory` keeps owning the Odoo↔Shopify
  location mapping, `fulfillment` never depends on `inventory` — not a DEC-008
  amendment), sync trigger (layered:
  scheduled + manual + event-driven enqueue; webhook import flagged unverified), inventory
  operation style (`inventorySetQuantities` compare-and-set preferred, DEC-009 idempotency/
  ambiguous-outcome rules applied), conflict handling, user-facing log requirements, and
  module boundaries — and
  [`ar008-fulfillment-architecture-decision-brief.md`](../03-architecture/ar008-fulfillment-architecture-decision-brief.md)
  — validated `stock.picking` as the fulfillment trigger, FulfillmentOrder-based mutations
  only (`fulfillmentCreate`/`fulfillmentTrackingInfoUpdate`), matching via
  `lineItemsByFulfillmentOrder`, the DEC-007 no-notification-by-default guard applied with
  the setting persisted per job at enqueue time, single-fulfillment-location Phase 1
  posture with multi-package/multi-location deferred (existing C-FUL-02 boundary, not a new
  rejection), the DEC-009 ambiguous-outcome rule applied to both fulfillment mutations
  (neither is on Shopify's 17-mutation `@idempotent` list), and the same clarified
  shared-Shopify-Location-reference ownership principle mirrored from the AR-007 brief
  (not a DEC-008 amendment). Ran a **small,
  targeted official-source check** (`ar007-ar008-evidence-refresh.md`, access date
  2026-07-02) against official Odoo 19.0 documentation for inventory-quantity report
  concepts (On Hand / Free to Use / Forecasted), warehouse/location types, and third-party
  carrier tracking — needed because a repo-local extraction pass found
  `../01-research/odoo-official-architecture-notes.md` had **zero coverage** of
  `stock.quant`/`stock.picking`/delivery-carrier models; several gaps (exact `stock.quant`
  field names, exact tracking-reference field name, exact delivery-order backorder-wizard
  text, Shopify inventory/fulfillment webhook topic strings, the literal 17-mutation
  `@idempotent` list) remain **explicitly marked "Open question / must be verified before
  implementation"** rather than asserted. Proposed
  [`DEC-010`](../04-decisions/DEC-010-inventory-architecture-strategy.md) (AR-007) and
  [`DEC-011`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md) (AR-008), both
  `Status: Proposed for ChatGPT review`. Updated `architecture-review-log.md`: AR-007 and
  AR-008 rows move from "Not decided / Evidence pending" to "Proposed for ChatGPT review,"
  with a compact note confirming AR-002–AR-006 are unchanged and implementation remains
  blocked. Updated `rejected-approaches-log.md`: added **RA-018** (writing Shopify's
  read-only `committed` quantity), **RA-019** (single-location-only/SKU-only inventory
  writes without per-location binding identity), **RA-020** (autonomous bidirectional
  inventory conflict resolution in Phase 1), **RA-021** (treating Shopify/Odoo inventory
  quantities as equivalent without an explicit source-of-truth) tied to DEC-010, and
  **RA-022** (legacy fulfillment API flow), **RA-023** (fulfillment creation without
  FulfillmentOrder/line/quantity/location matching) tied to DEC-011 — all six tagged
  **PROPOSED**, non-binding until DEC-010/DEC-011 are accepted (checked against RA-001–017
  first; blind first inventory push, hidden/default-on notification, blind-retry-everything,
  and binding-alone idempotency were **not** re-logged — already RA-008/RA-009/RA-014/
  RA-017 respectively; multi-package/multi-location fulfillment automation was **not**
  logged — it is an existing deferral, not a rejection, under DEC-003/C-FUL-02).
  Updated `../04-decisions/README.md` to index DEC-010/DEC-011 as "Also present (not yet
  accepted)" and corrected the stale "AR-007 and AR-008 remain not decided" current-status
  line. Archived this sprint's prompt to `../06-prompts/ar007-ar008-decision-prep-prompt.md`.
- **Items deferred:** exact Odoo model/field/constraint design for inventory and
  fulfillment bindings/mappings/logs; exact computed quantity field/formula; exact
  `inventorySetQuantities`-vs-`inventoryAdjustQuantities` choice per trigger; exact cron
  cadence; exact feature-flag/config-model mechanism (already routed to UX/operator-flow
  and Master Blueprint per DEC-008); exact fulfillment mutation parameters; exact tracking
  field source; exact notification-UI granularity (DEC-007's own open fork); exact retry
  constants; the exact fulfillment location-confirmation mechanism (the ownership
  principle — `core` may hold a minimal Shopify Location reference, `inventory` keeps
  the mapping, `fulfillment` never depends on `inventory` — is clarified in DEC-010/
  DEC-011 as an interpretation consistent with DEC-008, not a DEC-008 amendment; only
  the exact mechanism/fields/models remain open); the Master Blueprint; all
  implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** RA-018 through RA-023 added (PROPOSED, non-binding). **New technical
  debt:** none (no code). **Architecture concerns:** AR-007 and AR-008 move to "Proposed
  for ChatGPT review" (not yet accepted); AR-002/AR-003/AR-004/AR-005/AR-006 unchanged
  ("Accepted"). A module-boundary ownership question was clarified (a minimal shared
  Shopify-Location reference may live in `core`; `inventory` keeps owning the Odoo↔
  Shopify location mapping; `fulfillment` never depends on `inventory`) as an
  **interpretation consistent with DEC-008**, not a DEC-008 amendment and not a
  contradiction — only the exact fulfillment location-confirmation mechanism remains
  open for the Master Blueprint.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches logged (RA-018–023, PROPOSED) ·
  technical debt logged (none applicable — no code) · repeated-issue escalation applied
  (none at threshold) — all **YES**.
- **Next recommended session:** 1) **ChatGPT/Fable review of DEC-010/DEC-011** (including
  verifying the clarified shared-Shopify-Location-reference ownership interpretation);
  2) **UX/operator-flow sprint**; 3) **Master Blueprint**, after those gates;
  4) **Implementation only after a separate ChatGPT gate.**
- **Stop condition:** stopped after three focused commits + one **draft** PR into
  `Shopify-connector` (not merged). PR #65 merge confirmed first. DEC-003/DEC-004/
  DEC-005/DEC-006/DEC-007/DEC-008/DEC-009 not edited; no code files changed; AR-007 and
  AR-008 are **proposed only, not accepted**; implementation still not authorized; `main`
  and plain `dev` untouched. Awaiting further instruction.

**PR #66 minor revision (2026-07-02):**
- ChatGPT reviewed PR #66 and requested minor cleanup before Fable review.
- Clarified shared Shopify Location reference ownership: `core` may own a
  minimal Shopify Location reference/cache; `inventory` keeps owning the
  Odoo↔Shopify inventory mapping; `fulfillment` must not depend on
  `inventory`; the exact fulfillment location-confirmation mechanism remains
  a Master Blueprint item.
- Strengthened the fulfillment operation-level idempotency key (conceptually)
  to include operation type, Shopify target ID, and a payload/version hash —
  not just the picking ID.
- De-overstated Odoo `stock.quant` wording — AR-007 chooses the semantic
  quantity concept ("Free to Use"), not a verified Odoo ORM source; the exact
  implementation source remains open.
- Clarified Shopify `available` as the Phase 1 default inventory write target;
  `on_hand` requires explicit Master Blueprint justification before use;
  `committed` is never written.
- Fixed the architecture-review-log wording ("Proposed for ChatGPT review").
- DEC-010/DEC-011 remain `Proposed for ChatGPT review`, not accepted.
- AR-007/AR-008 remain proposed only, not accepted.
- RA-018 through RA-023 remain PROPOSED, not finalized.
- DEC-003/004/005/006/007/008/009 untouched.
- No code files changed.
- Implementation remains blocked.

**PR #66 Fable revision (2026-07-02, ChatGPT + Fable review — ACCEPT WITH MINOR CHANGES):**
- Fable reviewed PR #66 and returned ACCEPT WITH MINOR CHANGES.
- Corrected DEC-008 attribution for the core Shopify Location reference: now
  framed as a proposed clarification/extension of DEC-008's `core`-owns list,
  ratified only if ChatGPT accepts DEC-010/DEC-011 — not something DEC-008
  already explicitly decided.
- Added dated official Shopify verification (access date 2026-07-02) for
  `FulfillmentInput.lineItemsByFulfillmentOrder` and FulfillmentOrder
  `assignedLocation`, recorded in `ar007-ar008-evidence-refresh.md`.
- Corrected the false "17-mutation list not itemized in repo docs" claim —
  the list is already itemized in `rb14-part2-open-question-resolution.md`
  (RQ-005-2); narrowed the remaining open item to `@idempotent`
  key-uniqueness scope and API-version-specific detail.
- Aligned DEC-010's first-push guard granularity wording so it no longer
  reads as deciding "per binding" — granularity remains open (per-store /
  per-binding / per-variant-location binding), no coarser than per-store.
- Added a fulfillment operation-serialization guard: a new/corrected
  operation must not dispatch while a prior ambiguous operation against the
  same `(store, picking, Shopify target)` is unresolved.
- Added core Location-reference invariants: no Odoo-location IDs or mapping
  decisions in the core reference; staleness/precedence vs. live
  `assignedLocation` left to the Master Blueprint.
- Cleaned small `04-decisions/README.md` residue, an RA-018 avoid-list
  citation, and RA-021/RA-023 revisit-condition wording.
- DEC-010/DEC-011 remain `Proposed for ChatGPT review`, not accepted.
- AR-007/AR-008 remain proposed only, not accepted.
- RA-018 through RA-023 remain PROPOSED, not finalized.
- DEC-003/004/005/006/007/008/009 untouched.
- No code files changed.
- Implementation remains blocked.

---

### DEC-008/DEC-009 Acceptance Patch — compact handoff (2026-07-02)

> **Documentation acceptance patch, not implementation.** Confirmed PR #64 merged into
> `Shopify-connector` (merge commit `e4c74abf0e3b4ad32e66413d27b40287ed4c5822`) before
> editing; DEC-008 and DEC-009 confirmed `Proposed for ChatGPT review`; RA-011 through
> RA-017 confirmed `PROPOSED`; AR-004 and AR-006 confirmed proposed only, not accepted;
> AR-007 and AR-008 confirmed not decided; DEC-003/004/005/006/007 confirmed
> accepted/unchanged; implementation confirmed still blocked. Branch
> `claude/accept-dec008-dec009-4aca6v` (harness-assigned; the sprint's preferred name was
> `architecture/accept-dec008-dec009`, so this branch-name discrepancy is recorded here per
> the session rule) was already checked out based exactly on that merge commit — no
> re-basing needed.

- **Branch / PR:** `claude/accept-dec008-dec009-4aca6v` → draft PR into `Shopify-connector`,
  opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/04-decisions/DEC-008-module-boundary-strategy.md`,
  `docs/04-decisions/DEC-009-error-retry-idempotency-strategy.md`,
  `docs/03-architecture/ar004-module-boundary-decision-brief.md`,
  `docs/03-architecture/ar006-error-retry-idempotency-decision-brief.md`,
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/01-research/research-handoff.md` (this
  file).
- **What changed:** DEC-008 Status changed from `Proposed for ChatGPT review` to
  **`Accepted by ChatGPT`**, acceptance date **2026-07-02**; DEC-009 Status changed the
  same way, same acceptance date. Both records got an acceptance note recording the PR #64
  merge and the Fable **ACCEPT WITH MINOR CHANGES** review, while preserving every
  documented caveat unchanged (DEC-008 does not decide AR-007/AR-008, concrete Odoo schema,
  or the DEC-006 polymorphic-vs-per-domain binding-schema fork, and does not decide the
  feature-flag/per-store capability-configuration mechanism; DEC-009 does not decide
  AR-007/AR-008, exact retry/backoff constants, exact reconciliation cadence/scope, or
  exact schema, and keeps the ambiguous-outcome non-`@idempotent` write rule as part of the
  accepted decision). The AR-004 and AR-006 decision briefs were updated to state that
  AR-004/AR-006 are now accepted through DEC-008/DEC-009, while remaining evidence-backed
  briefs that authorize no implementation and leave AR-007/AR-008 not decided.
  `docs/04-decisions/README.md`'s DEC-008/DEC-009 entry moved from "Also present (not yet
  accepted)" to "Also accepted," citing the 2026-07-02 acceptance date and noting RA-011
  through RA-017 are now binding. `architecture-review-log.md`'s AR-004 and AR-006 table
  rows moved from "Proposed for ChatGPT review" to "Accepted by ChatGPT," and a compact
  acceptance note was appended confirming AR-007/AR-008 remain not decided, DEC-003/004/
  005/006/007 are unchanged, and implementation remains blocked. RA-011 through RA-017 in
  `rejected-approaches-log.md` had the `PROPOSED:` prefix removed and their "Related
  decision record" cells updated to cite DEC-008/DEC-009's `Accepted by ChatGPT,
  2026-07-02` status — **these seven rows are now binding final rejected approaches**
  (`CLAUDE.md` §10 applies in full).
- **Items deferred:** AR-007 full inventory architecture; AR-008 full fulfilment
  architecture; the feature-flag / per-store capability-configuration mechanism (routed to
  UX/operator-flow and Master Blueprint / implementation planning); exact retry/backoff
  constants and reconciliation cadence/scope (implementation-planning defaults); exact Odoo
  model/field/constraint schema; the DEC-006 polymorphic-vs-per-domain binding-schema fork;
  the Master Blueprint; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** none new (RA-011–017 finalized, not created). **New technical debt:** none
  (no code). **Architecture concerns:** AR-007/AR-008 remain **Not decided / Evidence
  pending** — DEC-008/DEC-009 accept the module-boundary and error/retry/idempotency
  strategies but decide neither AR-007 nor AR-008 internal design; AR-002/AR-003/AR-005
  unchanged (**Accepted**); AR-004/AR-006 now **Accepted**.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches finalized (RA-011–017) ·
  technical debt logged (none applicable — no code) · repeated-issue escalation applied
  (none at threshold) — all **YES**.
- **Next recommended session:** 1) **AR-007 + AR-008 decision sprint**; 2) **UX/operator-
  flow sprint**; 3) **Master Blueprint**, after those gates; 4) **Implementation only after
  a separate ChatGPT gate.**
- **Stop condition:** stopped after one commit + one **draft** PR into `Shopify-connector`
  (not merged). PR #64 merge confirmed first. DEC-003/DEC-004/DEC-005/DEC-006/DEC-007 not
  edited; no code files changed; AR-007/AR-008 remain **not decided**; implementation still
  not authorized; `main` and plain `dev` untouched. Awaiting further instruction.

**PR #65 tiny revision (2026-07-02):**
- ChatGPT reviewed PR #65 and requested tiny cleanup before merge.
- Fixed decisions README current-status residue so AR-004/AR-006 are no longer described as
  not decided.
- Fixed AR-004/AR-006 brief classification wording so recommendation labels no longer imply
  DEC-008/DEC-009 are still not decisions.
- DEC-008/DEC-009 remain accepted.
- AR-004/AR-006 remain accepted.
- AR-007/AR-008 remain not decided.
- DEC-003/004/005/006/007 untouched.
- No code files changed.
- Implementation remains blocked.

---

### AR-004 + AR-006 Decision Preparation — compact handoff (2026-07-02)

> **Documentation / decision-preparation sprint, not implementation.** Confirmed PR #63
> merged into `Shopify-connector` (merge commit `3ca0cdec168b60cae6c4b1004fa6f7532333a0f9`
> per the session prompt; verified as commit `3ca0cde` present in `origin/Shopify-connector`
> history) before editing; DEC-003/DEC-004/DEC-005/DEC-006/DEC-007 confirmed **Accepted by
> ChatGPT**; RA-001 through RA-010 confirmed **binding**; AR-002/AR-003/AR-005 confirmed
> **Accepted**; AR-004/AR-006/AR-007/AR-008 confirmed **Not decided**; implementation
> confirmed still blocked. Branch `claude/ar004-ar006-decision-prep-y9t8j2`
> (harness-assigned; the sprint's preferred name was
> `architecture/ar004-ar006-decision-prep`, so this branch-name discrepancy is recorded here
> per the session rule) was already checked out based exactly on that merge commit — no
> re-basing needed.

- **Branch / PR:** `claude/ar004-ar006-decision-prep-y9t8j2` → draft PR into
  `Shopify-connector`, opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/03-architecture/ar004-module-boundary-decision-brief.md` (new),
  `docs/03-architecture/ar006-error-retry-idempotency-decision-brief.md` (new),
  `docs/04-decisions/DEC-008-module-boundary-strategy.md` (new),
  `docs/04-decisions/DEC-009-error-retry-idempotency-strategy.md` (new),
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/01-research/research-handoff.md` (this
  file), `docs/06-prompts/ar004-ar006-decision-prep-prompt.md` (new, archive). No
  `docs/03-architecture/ar004-ar006-evidence-refresh.md` was created — repo-local evidence
  (already-cited Tier-1 Shopify/Odoo facts) was sufficient for every AR-004/AR-006 claim;
  no fresh external fetch was performed.
- **What changed:** authored
  [`ar004-module-boundary-decision-brief.md`](../03-architecture/ar004-module-boundary-decision-brief.md)
  — options considered (one giant module, per-feature micro-module explosion,
  domain-per-Odoo-app mirroring, layered domain family with link modules), a recommended
  Phase 1 addon family (`shopify_connector_core`/`product`/`sale`/`inventory`/
  `fulfillment`), a strict dependency DAG (`core` → `product`; `sale` and `inventory` are
  siblings depending on `core` + `product`; `fulfillment` depends on `core` + `sale`, not
  on `inventory`), a link-module strategy (none needed yet for Phase 1), and an evaluated
  answer on customer/dashboard/payment-evidence placement (folded into `sale`/`core`/`sale`
  respectively for Phase 1, each with a revisit condition) — and
  [`ar006-error-retry-idempotency-decision-brief.md`](../03-architecture/ar006-error-retry-idempotency-decision-brief.md)
  — a classified retry policy (Option C: auto-retry only safe/transient error classes),
  a 6-job-source taxonomy, a 10-job-state machine, a 16-error-class table with default
  retry behaviour, an 11-layer idempotency mapping (platform `@idempotent` surface +
  connector-designed keys), and user-facing log/audit requirements. Proposed
  [`DEC-008`](../04-decisions/DEC-008-module-boundary-strategy.md) (AR-004) and
  [`DEC-009`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md) (AR-006), both
  `Status: Proposed for ChatGPT review`. Updated `architecture-review-log.md`: AR-004 and
  AR-006 rows move from "Not decided / Evidence pending" to "Proposed for ChatGPT review,"
  with a compact note confirming AR-007/AR-008 are untouched and implementation remains
  blocked. Updated `rejected-approaches-log.md`: added **RA-011** (one giant module),
  **RA-012** (per-feature micro-module explosion), **RA-013** (duplicated queue/job/log/
  binding abstractions per domain) tied to DEC-008, and **RA-014** (retry-everything
  automatically), **RA-015** (never-retry-automatically/manual-only recovery), **RA-016**
  (user-facing stack traces as primary error UX), **RA-017** (no connector-designed
  idempotency key / binding-alone retry strategy) tied to DEC-009 — all seven tagged
  **PROPOSED**, non-binding until DEC-008/DEC-009 are accepted (checked against RA-001–010
  first; no duplicates). Updated `../04-decisions/README.md` to index DEC-008/DEC-009 as
  "Also present (not yet accepted)." Archived this sprint's prompt to
  `../06-prompts/ar004-ar006-decision-prep-prompt.md`.
- **Items deferred:** AR-007 full inventory architecture; AR-008 full fulfilment
  architecture; exact Odoo model/field/constraint design for jobs/bindings/mappings; exact
  later-module names/boundaries (accounting/refund/payout/multi-store/markets/metafield/
  POS/B2B/app-store); exact retry-count/backoff constants (flagged
  `[Implementation-planning default]`); the Master Blueprint; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** RA-011 through RA-017 added (PROPOSED, non-binding). **New technical
  debt:** none (no code). **Architecture concerns:** AR-004 and AR-006 move to "Proposed
  for ChatGPT review" (not yet accepted); AR-007/AR-008 unchanged ("Not decided"); AR-002/
  AR-003/AR-005 unchanged ("Accepted").
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches logged (RA-011–017, PROPOSED) ·
  technical debt logged (none applicable — no code) · repeated-issue escalation applied
  (none at threshold) — all **YES**.
- **Next recommended session:** 1) **ChatGPT/Fable review of DEC-008/DEC-009**; 2) **AR-007
  + AR-008 decision sprint**, once AR-004/AR-006 are reviewed; 3) **UX/operator-flow
  sprint**; 4) **Master Blueprint**, after those gates.
- **Stop condition:** stopped after three focused commits + one **draft** PR into
  `Shopify-connector` (not merged). PR #63 merge confirmed first. DEC-003/DEC-004/
  DEC-005/DEC-006/DEC-007 not edited; no code files changed; AR-004 and AR-006 are
  **proposed only, not accepted**; AR-007/AR-008 remain **not decided**; implementation
  still not authorized; `main` and plain `dev` untouched. Awaiting further instruction.

**PR #64 minor revision (2026-07-02):**
- ChatGPT reviewed PR #64 and requested minor cleanup before Fable review.
- Corrected AR-006 taxonomy count from 15 to 16 error classes.
- Clarified AR-004 dependency notation so fulfillment depends on core + sale, not inventory.
- Normalized RA-011–RA-017 proposed formatting to keep stable RA IDs.
- DEC-008/DEC-009 remain Proposed for ChatGPT review.
- AR-004/AR-006 remain proposed only, not accepted.
- AR-007/AR-008 remain not decided.
- DEC-003/004/005/006/007 untouched.
- No code files changed.
- Implementation remains blocked.

**PR #64 Fable revision (2026-07-02):**
- Fable reviewed PR #64 and returned ACCEPT WITH MINOR CHANGES.
- Added DEC-006 binding-shape reconciliation so DEC-008 does not foreclose polymorphic vs per-domain binding schema.
- Added ambiguous-outcome non-idempotent-write retry rule to DEC-009 / AR-006.
- Corrected evidence/citation attributions: enable/disable attribution; customer fold-in quote/source; `committed` attribution; temporary/server/network evidence wording.
- Routed residual feature-flag/config-model scope to UX/operator-flow and Master Blueprint / implementation planning.
- Acknowledged reconciliation cadence handoff from DEC-005 and routed exact cadence to implementation planning.
- Cleaned small state-machine wording.
- Tightened RA-014 revisit condition.
- Added missing sprint checkpoint log line.
- DEC-008/DEC-009 remain Proposed for ChatGPT review.
- AR-004/AR-006 remain proposed only, not accepted.
- AR-007/AR-008 remain not decided.
- DEC-003/004/005/006/007 untouched.
- No code files changed.
- Implementation remains blocked.

---

### DEC-007 Acceptance Patch — compact handoff (2026-07-02)

> **Documentation acceptance patch, not implementation.** Confirmed PR #62 merged into
> `Shopify-connector` (merge commit `0d45d38bfe25d45a9d98bceb677fed2eab3c1e96`) before
> editing; DEC-007 confirmed `Proposed for ChatGPT review`; RA-008/RA-009/RA-010 confirmed
> `PROPOSED`; DEC-003/004/005/006 confirmed accepted/unchanged. Branch
> `claude/accept-dec007-2pjo9b` (harness-assigned; preferred branch name was
> `product/accept-dec007`, so this branch-name discrepancy is recorded here per the session
> rule) was already based exactly on that merge commit. Recorded ChatGPT's formal
> acceptance of DEC-007.

- **Branch / PR:** `claude/accept-dec007-2pjo9b` → draft PR into `Shopify-connector`,
  opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/04-decisions/DEC-007-phase1-scope-clarifications.md`,
  `docs/04-decisions/README.md`, `docs/03-architecture/phase1-domain-model-brief.md`,
  `docs/02-product/mvp-scope.md`, `docs/02-product/non-mvp-and-later-phases.md`,
  `docs/02-product/user-stories.md`, `docs/05-qa/rejected-approaches-log.md`,
  `docs/05-qa/architecture-review-log.md`, `docs/01-research/shopify-official-api-notes.md`,
  `docs/01-research/research-handoff.md` (this file).
- **What changed:** DEC-007 Status changed from `Proposed for ChatGPT review` to
  **`Accepted by ChatGPT`**, acceptance date **2026-07-02**; added an acceptance note
  recording the PR #62 merge, the Fable **ACCEPT WITH MINOR CHANGES** review, and the
  explicit caveat that DEC-007 also accepts three **Phase 1 safety guardrails** (price
  source-of-truth before export/update; first Odoo→Shopify inventory push guard;
  fulfilment customer-notification visibility/control) — not hidden as pure wording
  cleanup. "Proposed"/"if accepted"/"if not accepted"/"candidate"/"proposed for review"
  wording updated to reflect the accepted status throughout DEC-007, while historical
  proposal notes are preserved as history. Domain-model brief labels changed from
  `[Proposed clarification — DEC-007]` to `[Accepted clarification — DEC-007]`
  throughout; its status section now records the DEC-007 acceptance. Product docs
  (`mvp-scope.md`, `non-mvp-and-later-phases.md`, `user-stories.md`) DEC-007 notes updated
  from proposed to accepted, without rewriting DEC-003 or the surrounding product text.
  `docs/04-decisions/README.md` DEC-007 entry updated from "Also present (not yet
  accepted)" to "Also accepted," citing the 2026-07-02 acceptance date and noting
  RA-008/009/010 are now binding. RA-008/RA-009/RA-010 in `rejected-approaches-log.md`
  had the `PROPOSED:` prefix removed and their "Related decision record" cells updated to
  cite DEC-007's `Accepted by ChatGPT, 2026-07-02` status — **these three rows are now
  binding final rejected approaches** (`CLAUDE.md` §10 applies in full). Added a compact
  acceptance note to `architecture-review-log.md` confirming DEC-007 feeds AR-006/AR-007/
  AR-008 without deciding them, AR-004 is untouched, and AR-004/006/007/008 remain "Not
  decided / Evidence pending." Propagated the two newly verified Shopify fact groups from
  DEC-007 (Order tax/shipping/discount fields; `FulfillmentInput.notifyCustomer` /
  `fulfillmentTrackingInfoUpdate.notifyCustomer` defaults) into a new dated section of
  `shopify-official-api-notes.md`, citing the same URLs and access date (2026-07-02)
  already used in DEC-007 — no new external research performed.
- **Items deferred:** AR-004/AR-006/AR-007/AR-008 full architecture decisions; exact Odoo
  model/field/constraint design; exact GraphQL mutation strategy for variant writes; the
  Master Blueprint; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** none new (RA-008–RA-010 finalized, not created). **New technical debt:**
  none (no code). **Architecture concerns:** AR-006/AR-007/AR-008 remain **Not decided /
  Evidence pending** — DEC-007's guardrails remain scope-level statements, not
  AR-007/AR-008 mechanism decisions; AR-002/AR-003/AR-005 unchanged (**Accepted**);
  AR-004 unchanged (**Not decided**).
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches finalized (RA-008–RA-010) ·
  technical debt logged (none applicable — no code) · repeated-issue escalation applied
  (none at threshold) — all **YES**.
- **Next recommended session:** 1) **AR-004 + AR-006 decision sprint**; 2) **AR-007 +
  AR-008 decision sprint**; 3) **UX/operator-flow sprint**; 4) **Master Blueprint** after
  those gates.
- **Stop condition:** stopped after one commit + one **draft** PR into `Shopify-connector`
  (not merged). PR #62 merge confirmed first. DEC-003/DEC-004/DEC-005/DEC-006 not edited;
  no code files changed; AR-004/AR-006/AR-007/AR-008 remain **not decided**;
  implementation still not authorized; `main` and plain `dev` untouched. Awaiting further
  instruction.

---

### Phase 1 Domain Model + DEC-003 Scope-Hole Closure — compact handoff (2026-07-02)

> **Documentation / decision-preparation sprint, not implementation.** Confirmed PR #61
> merged into `Shopify-connector` (merge commit
> `26dc30109530e2566755fd93bd974284083c3922`) before editing; DEC-004/DEC-005/DEC-006
> confirmed **Accepted by ChatGPT**; AR-002/AR-003/AR-005 confirmed **Accepted**;
> AR-004/AR-006/AR-007/AR-008 confirmed **not decided**. Branch created from that exact
> commit (verified via `git merge-base`). Produced a Phase 1 domain-model brief and a
> proposed DEC-007 scope-clarification addendum closing five known DEC-003 scope holes.

- **Branch / PR:** `claude/domain-model-scope-closure-nv8ah9` (harness-assigned; the
  sprint's preferred name `product/domain-model-scope-closure` was not used — per the
  session's hard git rule, work proceeded on the harness-assigned branch, confirmed based
  exactly on `Shopify-connector`'s PR #61 merge commit before any edit; flagged as the
  branch-name discrepancy) → draft PR into `Shopify-connector`, opened immediately after
  this handoff commit, **not merged**.
- **Files changed:** `docs/03-architecture/phase1-domain-model-brief.md` (new),
  `docs/04-decisions/DEC-007-phase1-scope-clarifications.md` (new),
  `docs/02-product/mvp-scope.md`, `docs/02-product/non-mvp-and-later-phases.md`,
  `docs/02-product/user-stories.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/01-research/research-handoff.md` (this
  file).
- **What changed:** authored
  [`phase1-domain-model-brief.md`](../03-architecture/phase1-domain-model-brief.md) — a
  documentation-level (not schema-level) Phase 1 concept map across eight domains (store/
  connection, binding/identity, product, customer, order/sale, inventory, fulfilment,
  queue/log/error), each statement labelled accepted decision / proposed clarification /
  inference / open question. Proposed
  [`DEC-007`](../04-decisions/DEC-007-phase1-scope-clarifications.md)
  (`Status: Proposed for ChatGPT review`) closing five DEC-003 scope-hole wordings: (1)
  variant export/update is included, not optional, wherever product export/update is in
  MVP; (2) image/media "where feasible" replaced with an explicit
  included/excluded/deferred split (basic image sync in; advanced dedup/alt-text/CDN/
  media-governance out); (3) price/compare-at "where feasible" replaced the same way, plus
  an explicit price source-of-truth requirement; (4) a **first-inventory-push guard**
  (mapped location + preview + operator confirmation + recorded source-of-truth + skip/
  manual-match option) before any first Odoo→Shopify inventory write; (5) a **fulfilment
  customer-notification default** of "no notification unless explicitly enabled," grounded
  in newly verified Shopify API defaults; (6) a tax/shipping/discount/payment-evidence
  clarification requiring evidence preservation sufficient for reconcilable totals, with
  conservative-by-default invoice/payment creation (no silent accounting automation). Ran a
  **small, targeted official-source check** (per the sprint's external-research rule, since
  the tax-line/shipping-line/discount-line fields and the fulfilment notification defaults
  were not already grounded in repo docs): verified `Order.taxLines`/`shippingLines`/
  `discountApplications` and `FulfillmentInput.notifyCustomer` (defaults `false`) /
  `fulfillmentTrackingInfoUpdate`'s `notifyCustomer` (defaults to no notification) against
  `shopify.dev` official pages, access date 2026-07-02 — cited with URL in DEC-007 and the
  domain-model brief; **not** propagated into `../01-research/shopify-official-api-notes.md`
  (outside this sprint's allowed-files list — flagged as a follow-up). Added five new Phase
  1 user stories tied to the clarifications (`US-E2-07` variant export/update, `US-E2-08`
  product/variant export preview/dry-run, `US-E4-07` financial evidence mapping, `US-E5-06`
  first inventory push guard, `US-E6-04` fulfilment notification control) to
  `user-stories.md`. Added pointer notes (not rewrites, not acceptance claims) to
  `mvp-scope.md` and `non-mvp-and-later-phases.md` referencing the proposed DEC-007.
  Added a non-decision note to `architecture-review-log.md` confirming AR-006/AR-007/
  AR-008 stay "Not decided / Evidence pending" and are **fed, not decided**, by this
  sprint's guardrail-level clarifications; AR-002/AR-003/AR-005 remain **Accepted**,
  untouched. Added **RA-008** (blind first inventory push), **RA-009** (hidden/default-on
  fulfilment notification), and **RA-010** (automatic full accounting/payment
  reconciliation by default) to `rejected-approaches-log.md`, each tagged **PROPOSED**
  (non-binding until DEC-007 is accepted, mirroring the RA-002–RA-007 precedent);
  automatic name-only matching was **not** re-logged (already covered by the binding
  RA-006).
- **Items deferred:** AR-004/AR-006/AR-007/AR-008 full architecture decisions; exact Odoo
  model/field/constraint design; exact GraphQL mutation strategy for variant writes; the
  Master Blueprint; propagating the two newly verified Shopify facts into
  `shopify-official-api-notes.md`; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** RA-008/RA-009/RA-010, tagged **PROPOSED** (see
  `rejected-approaches-log.md`). **New technical debt:** none (no code). **Architecture
  concerns:** AR-006/AR-007/AR-008 remain **Not decided / Evidence pending** — this
  sprint's first-inventory-push guard and fulfilment-notification default are explicitly
  **scope-level guardrail statements**, not AR-007/AR-008 mechanism decisions; AR-002/
  AR-003/AR-005 unchanged (**Accepted**).
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches logged (RA-008–RA-010, tagged
  PROPOSED) · technical debt logged (none applicable — no code) · repeated-issue
  escalation applied (none at threshold) — all **YES**.
- **Next recommended session:** **ChatGPT/Fable review of DEC-007 and the Phase 1
  domain-model brief; if DEC-007 is accepted, a Master Blueprint sprint** (and/or a
  dedicated AR-006/AR-007/AR-008 architecture-decision sprint) **can follow.**
- **Stop condition:** stopped after three staged commits + one **draft** PR into
  `Shopify-connector` (not merged). PR #61 merge confirmed first. DEC-003/DEC-004/
  DEC-005/DEC-006 not edited; no code files changed; AR-002/AR-003/AR-005 remain
  **Accepted**; AR-004/AR-006/AR-007/AR-008 remain **not decided**; implementation still
  not authorized; `main` and plain `dev` untouched. Branch-name discrepancy flagged above.
  Awaiting ChatGPT/Fable review.

#### PR #62 revision (2026-07-02, ChatGPT review — REVISE MINOR before Fable review)

- ChatGPT reviewed PR #62 and requested minor wording cleanup before Fable review.
- Fixed five-vs-six clarification wording in DEC-007 (six clarification sections covering
  five known scope-hole themes; image/media and price split into separate sections).
- Made DEC-007 "What this unlocks" conditional on ChatGPT acceptance.
- Clarified that the phase-exit criterion is not satisfied until DEC-007 is accepted.
- Reworded the domain brief's schema-design deferral to "Master Blueprint /
  implementation-planning sprint."
- **DEC-007 remains `Proposed for ChatGPT review`.** No implementation authorized.
  DEC-003/004/005/006 untouched. No code files touched. Only
  `DEC-007-phase1-scope-clarifications.md`, `phase1-domain-model-brief.md`, and this
  handoff were edited — product docs, `architecture-review-log.md`, and
  `rejected-approaches-log.md` were not touched in this revision.

#### PR #62 Fable fix-up (2026-07-02, ChatGPT + Fable review — ACCEPT WITH MINOR CHANGES)

- Fable reviewed PR #62 and returned **ACCEPT WITH MINOR CHANGES**.
- Applied small fix-up: fixed `architecture-review-log.md` markdown italics (missing
  closing underscore on the DEC-004/005/006 acceptance-patch note; stray double
  underscore on the PR #62 sprint note); corrected/qualified the `shippingLines` quote
  (no longer presented as a complete verbatim quote) in DEC-007 and the domain-model
  brief; indexed DEC-007 in `docs/04-decisions/README.md` as `Proposed for ChatGPT
  review`, not accepted; added an open question for first-push-guard granularity
  (per-store vs. per-binding vs. another AR-007 unit) to DEC-007 and the domain-model
  brief; added an open question for how Shopify-computed tax is represented in Odoo
  without recomputation to DEC-007 and the domain-model brief; clarified wording so
  "AR-002 implementation planning" reads as "implementation planning under the accepted
  DEC-004 / AR-002 decision" (AR-002 itself is accepted; only mechanics remain open).
- **DEC-007 remains `Proposed for ChatGPT review`, not accepted.** DEC-003/004/005/006
  untouched. `rejected-approaches-log.md` untouched. Product docs untouched. No code
  files touched. No implementation authorized.

---

### DEC-004/005/006 Acceptance Patch — compact handoff (2026-07-02)

> **Architecture acceptance patch, not implementation.** Confirmed PR #60 merged into
> `Shopify-connector` (merge commit `7eb875e4ca29b80c4745bd8f5354450aa1e4d37b`) before
> editing. Branch created from latest `Shopify-connector` using the preferred name
> `architecture/accept-dec004-dec005-dec006` (no harness override observed this
> session). Recorded ChatGPT's formal acceptance of DEC-004, DEC-005, and DEC-006.

- **Branch / PR:** `architecture/accept-dec004-dec005-dec006` → draft PR into
  `Shopify-connector`, opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/04-decisions/DEC-004-distribution-api-auth-strategy.md`,
  `docs/04-decisions/DEC-005-sync-orchestration-strategy.md`,
  `docs/04-decisions/DEC-006-binding-dedup-identity-strategy.md`,
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`,
  `docs/01-research/research-handoff.md` (this file).
- **What changed:** DEC-004/005/006 Status changed from `Proposed for ChatGPT review`
  to **`Accepted by ChatGPT`**, acceptance date **2026-07-02**; opening notes reworded
  from "proposal, not an acceptance" to "accepted architecture decision record";
  no-implementation clauses kept but reworded (acceptance ≠ automatic implementation
  authorization — the separate Phase 1 research-phase-exit + implementation gate
  still applies, `../05-qa/quality-feedback-loop.md` §10). AR-002/AR-003/AR-005 Review
  decision + Status cells in `architecture-review-log.md` changed to **"Accepted by
  ChatGPT"** / **"Accepted"**, linked to the now-accepted DEC files. RA-002 through
  RA-007 in `rejected-approaches-log.md` had the `PROPOSED:` prefix removed and their
  "Related decision record" cells updated to cite each DEC file's `Accepted by
  ChatGPT` status — **these six rows are now binding final rejected approaches**
  (`CLAUDE.md` §10 applies in full); the prior "non-binding until acceptance"
  governance note is superseded, not deleted. `docs/04-decisions/README.md` now
  describes DEC-004/005/006 as accepted (the first accepted architecture ADRs in the
  repo), keeps the DEC-vs-ADR-NNNN naming note, and states implementation is not
  automatically authorized until the next implementation-gate/blueprint phase.
- **Items deferred:** none new this patch (decision-substance unchanged; only
  status/acceptance wording updated, per this sprint's explicit scope).
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new.
  **New rejected approaches:** none new (RA-002–RA-007 finalized, not created).
  **New technical debt:** none (no code). **Architecture concerns:** AR-002/AR-003/
  AR-005 now **Accepted**; AR-004/AR-006/AR-007/AR-008 **still not decided**.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked
  · learning captured (no new issues) · rejected approaches finalized (RA-002–RA-007)
  · technical debt logged (none applicable — no code) · repeated-issue escalation
  applied (none at threshold) — all **YES**.
- **Next recommended session:** **Phase 1 Domain Model + DEC-003 Scope-Hole
  Closure.**
- **Stop condition:** stopped after one commit + one **draft** PR into
  `Shopify-connector` (not merged). PR #60 merge confirmed first. DEC-003 untouched;
  no code files changed; AR-004/006/007/008 not decided; implementation still not
  authorized; `main` and plain `dev` untouched. Awaiting further instruction.

---

### Evidence Refresh + Combined AR-002/003/005 Decision Preparation — compact handoff (2026-07-02)

> **Decision-preparation sprint, not implementation.** Confirmed PR #59 merged into
> `Shopify-connector` (tip `85a230a`) before editing; the harness-assigned branch
> `claude/ar-decision-prep-p2wpo7` is based directly on that commit (the sprint's
> preferred name, `architecture/ar002-ar003-ar005-decision-prep`, was not used — the hard
> git rule designates the harness branch; flagged per instruction). Ran a **small,
> targeted official-source refresh** (Odoo.sh docs + OCA `queue_job` community evidence
> only — no broad web research, no competitor research redone) and produced **three
> proposed** (not accepted) architecture decision records for AR-002, AR-003, and AR-005.

- **Branch / PR:** `claude/ar-decision-prep-p2wpo7` (harness-assigned; preferred name
  `architecture/ar002-ar003-ar005-decision-prep` not available — see branch-name
  discrepancy note below) → draft PR into `Shopify-connector`, opened immediately after
  this handoff commit, **not merged**.
- **Files changed:** `docs/03-architecture/ar002-ar003-ar005-evidence-refresh.md` (new),
  `docs/01-research/odoo-official-architecture-notes.md`,
  `docs/04-decisions/DEC-004-distribution-api-auth-strategy.md` (new),
  `docs/04-decisions/DEC-005-sync-orchestration-strategy.md` (new),
  `docs/04-decisions/DEC-006-binding-dedup-identity-strategy.md` (new),
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/05-qa/defect-pattern-log.md`,
  `docs/01-research/research-handoff.md` (this file).
  `docs/01-research/shopify-official-api-notes.md` was **not** edited — no new Shopify
  fact needed re-verification (the RB-14 Part 1/2 refresh, 2026-07-01, remains current
  one day later; re-fetching the same pages would be token waste, DP category 17).
- **What changed / evidence refreshed:** targeted external check of **official Odoo.sh
  docs** — `server_wide_modules`/external-Jobrunner support is **not addressed** in any
  fetched page (absence of documentation, not a documented denial); production
  scheduled actions run on a **"best effort," ≥5-minute-interval, execution-time-limited**
  basis (new, sharper than the previously-known "staging crons disabled" fact); plus a
  **community-tier** check of **OCA `queue_job`** (repo renamed `OCA/queue`) confirming a
  19.0 PyPI release exists, its Jobrunner now runs as an Odoo **worker process** (not a
  separate external daemon) but still needs `server_wide_modules` + `--workers > 0`. Full
  record: `docs/03-architecture/ar002-ar003-ar005-evidence-refresh.md`.
- **Proposed decisions created (each `Status: Proposed for ChatGPT review`, none
  accepted, none implementation-authorizing):**
  - **DEC-004** (AR-002) — custom/Admin-created Shopify app (Early Access, no App
    Store), GraphQL Admin API primary/default, offline-token auth with masked
    storage/least-privilege scopes; public App Store/OAuth/Billing deferred.
  - **DEC-005** (AR-003) — HMAC-verified fast-ack webhook receiver + webhook-ID dedup →
    internal Odoo queue/job model → `ir.cron`-driven batch processing, on **Odoo.sh or
    on-premise** (not Odoo Online); manual sync + scheduled reconciliation always on;
    per-record isolation + retry counters + dead/final-failed state; **OCA `queue_job`
    deferred/optional, not the Phase 1 default** (Odoo.sh jobrunner feasibility
    unconfirmed).
  - **DEC-006** (AR-005) — dedicated/hybrid per-store connector binding model as the
    source of truth (Shopify GID + Odoo model/record stored explicitly, per-store
    uniqueness constraints); `ir.model.data` **rejected as the primary** mechanism (not
    for all uses); match priority existing-binding → SKU/internal-reference → barcode →
    email/customer keys → manual; **no name-only automatic matching**.
- **Rejected/deferred approaches logged (all tagged PROPOSED, tied to the DEC files'
  own "Proposed for ChatGPT review" status — not final rejections):** RA-002 REST-heavy
  API strategy; RA-003 public App Store/OAuth/Billing as a Phase 1 architecture
  requirement; RA-004 OCA `queue_job` as the Phase 1 **default** substrate (not rejecting
  `queue_job` itself); RA-005 `ir.model.data` as the **primary** binding mechanism (not
  rejecting all use of `ir.model.data`); RA-006 name-only automatic matching.
- **Items deferred:** exact binding/queue-table schema and field design (a future
  domain-model sprint); AR-006/007/008 (explicit non-goals this sprint); AR-004 module
  boundaries; the OAuth-vs-plain-token and token-expiry-variant sub-choice within
  DEC-004's offline-token model; MVP-scale throughput validation under
  `--max-cron-threads=2`; Odoo.sh `server_wide_modules` confirmation (open — carried
  forward as a DEC-005 revisit trigger).
- **Branch-name discrepancy (flagged per instruction):** the sprint's preferred branch
  name was `architecture/ar002-ar003-ar005-decision-prep`; per the session's hard git
  rule (never push to a different branch without explicit permission), work proceeded
  on the harness-assigned `claude/ar-decision-prep-p2wpo7`, which was confirmed based
  exactly on `Shopify-connector`'s PR #59 merge tip (`85a230a...`) before any edit.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new — DP-006
  (evidence-consistency gate) applied, not re-triggered (Odoo.sh silence kept as an
  open question, not read as denial; OCA evidence kept community-tier, never promoted
  to Odoo official fact). **New rejected approaches:** RA-002–RA-006 (see above),
  explicitly tagged **PROPOSED** — see the framing note added to
  `rejected-approaches-log.md` explaining why they precede full ChatGPT acceptance
  (per this sprint's explicit instruction) rather than following the RA-001 precedent
  of logging only after acceptance. **New technical debt:** none (no code). **Architecture
  concerns:** AR-002/AR-003/AR-005 move to **"Proposed for ChatGPT review"** in
  `architecture-review-log.md` — explicitly **not** "Accepted"; AR-004/006/007/008
  untouched.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (DP-log note, no new row) · rejected approaches logged (RA-002–
  RA-006, tagged PROPOSED) · technical debt logged (none applicable — no code) ·
  repeated-issue escalation applied (none at threshold) — all **YES**.
- **Next recommended session:** **ChatGPT/Fable review of proposed DEC-004/005/006,
  then Phase 1 Domain Model + DEC-003 Scope-Hole Closure sprint if accepted.**
- **Stop condition:** stopped after three staged commits + one **draft** PR into
  `Shopify-connector` (not merged). No connector code, no Odoo module, no forbidden
  files touched. DEC-003 body not edited; MVP scope unchanged; AR-002/003/005 marked
  **Proposed for ChatGPT review**, not Accepted; AR-004/006/007/008 not decided; `main`
  and plain `dev` untouched. Awaiting ChatGPT/Fable review.

#### PR #60 revision (2026-07-02, ChatGPT + Fable review — ACCEPT WITH MINOR CHANGES)

- Fable reviewed PR #60 and returned **ACCEPT WITH MINOR CHANGES**.
- Applied the required fixes and nits: added **RA-007** for external worker as the
  Phase 1 substrate (fixing DEC-005's dangling rejected-approaches pointer);
  reconciled DEC-004's non-public custom-app / app-creation-surface /
  token-acquisition wording (creation surface + token mechanics left to
  implementation planning, not hard-fixed); clarified RA-002–RA-007 are
  non-binding until the linked DEC is accepted (`rejected-approaches-log.md`
  governance clarifier); fixed the `04-decisions/README.md` naming wording
  (DEC-004/005/006 **follow** the DEC-003 precedent, do not **predate** the
  ADR-NNNN convention); changed DEC-005 Option 5's disposition to **"Weakened"**
  (no RA row exists for it).
- **DEC-004/005/006 remain `Proposed for ChatGPT review`** — not accepted by this
  revision.
- **No implementation authorized. DEC-003 untouched. No code files touched.**

---

### Control-Room Reset Sprint 1 — compact handoff (2026-07-02)

> **Documentation residue sweep, convergence gates, and anti-bloat maintenance
> rule.** A mechanical cleanup/convergence sprint (not research) run after PR #58
> (RB-14 Part 2) merged into `Shopify-connector`. No high-power mode used (repo-
> local reading/grep only). Full detail:
> [`../05-qa/documentation-residue-sweep.md`](../05-qa/documentation-residue-sweep.md).

- **Branch / PR:** `claude/ready-check-nb2y99` (harness-assigned) → draft PR
  into `Shopify-connector`, **not merged**.
- **Files changed:** `docs/04-decisions/README.md`, `docs/03-architecture/README.md`,
  `docs/05-qa/pr-review-checklist.md`, `docs/02-product/mvp-scope.md`,
  `docs/02-product/feature-taxonomy.md`, `docs/02-product/product-vision.md`,
  `docs/02-product/setup-ux-principles.md`,
  `docs/00-source-materials/screenshots/teqstars/README.md`,
  `docs/00-source-materials/source-access-notes.md`,
  `docs/01-research/research-backlog.md`,
  `docs/05-qa/rejected-approaches-log.md`,
  `docs/05-qa/documentation-residue-sweep.md` (new),
  `docs/05-qa/quality-feedback-loop.md`, `CLAUDE.md`,
  `docs/06-prompts/session-handoff-template.md`,
  `docs/01-research/research-handoff.md` (this file),
  `docs/05-qa/architecture-review-log.md`, `docs/05-qa/defect-pattern-log.md`.
- **What changed / residue fixed:** stale "MVP not finalized" / "Proposed —
  pending ChatGPT acceptance" statements corrected against the accepted
  DEC-003 baseline (`mvp-scope.md`, `feature-taxonomy.md`, `product-vision.md`,
  `setup-ux-principles.md`); TeqStars/TQ 403-blocked residue corrected against
  the Sprint C2 rebaseline (teqstars screenshot README, `source-access-notes.md`);
  `docs/04-decisions/README.md` and `docs/03-architecture/README.md` "Empty"
  claims corrected; `pr-review-checklist.md`'s MVP-finalization checkbox
  reworded (still blocks unauthorized architecture/implementation);
  `research-backlog.md`'s "Not started"/"Blocked" statuses corrected to `Done`
  for completed items (R5 / RB-02.6 correctly stays `Blocked`); DEC-003's
  Option C rejection logged as **RA-001** in `rejected-approaches-log.md`;
  added phase-exit criteria + a documentation-maintenance rule
  (`quality-feedback-loop.md` §10–§11, `[Recommendation — becomes binding when
  merged by ChatGPT]`, pointed to from `CLAUDE.md`); aligned
  `session-handoff-template.md` to a compact default (this entry uses it).
- **Items deferred:** off-allowed-list files with likely-already-fixed
  TeqStars residue (`ux-ui-benchmark.md`, `common-patterns.md`,
  `best-in-class-observations.md`, `avoid-list.md`, `competitor-deep-dives.md`,
  `competitor-screenshot-inventory.md` — not verified or edited this sprint);
  two stale TeqStars references inside **DEC-003 itself** (read-only this
  sprint — flagged for a future dated post-decision note, not added here); the
  `DEC-003` vs `ADR-NNNN-<slug>.md` naming/numbering inconsistency (flagged for
  ChatGPT, not resolved/invented).
- **Learning feedback loop:** new issue — **documentation residue: stale
  current-truth statements not updated when a later decision supersedes them,
  plus append-only handoff growth** — logged as **DP-007**
  (`defect-pattern-log.md`, category: unclear handoff #16, 1st occurrence;
  prevention = this sprint's phase-exit + documentation-maintenance rules).
  No repeated pattern at threshold. Rules updated:
  `quality-feedback-loop.md` §10–§11 (new). New rejected approach: RA-001
  (Option C, sourced from the existing DEC-003 decision, not newly rejected
  this sprint). No new technical debt (no code). Architecture concerns: none —
  no AR row touched; all stay "Not decided / Evidence pending" (non-decision
  note added to `architecture-review-log.md`). Should future prompts change?
  **Yes, minor** — future research/product sprints should correct a
  Status/Governance line **at the time** a later decision supersedes it,
  rather than leaving it for a dedicated cleanup sprint.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured (DP-007) · rejected approach logged (RA-001) ·
  technical debt logged (none applicable — no code) · repeated-issue
  escalation applied (none at threshold) — all **YES**.
- **Compact handoff deviation:** authorized by this sprint's prompt
  (Control-Room Reset Sprint 1, "Compact handoff authorization"); recorded per
  that authorization.
- **Next recommended sprint:** **Evidence Refresh + Combined AR-002/003/005
  Decision Preparation**, after ChatGPT/Fable review of this PR.
- **Stop condition:** stopped after one draft PR into `Shopify-connector`
  (not merged). No connector code, no Odoo module, no forbidden files touched.
  DEC-003 body not edited; MVP scope unchanged; no AR row decided. `main` and
  plain `dev` untouched. Awaiting ChatGPT/Fable review.

### Control-Room Reset Sprint 1 — PR #59 revision (2026-07-02, ChatGPT REVISE)

> ChatGPT reviewed PR #59: **REVISE** — stayed in scope, but the first pass
> missed several current-truth stale residues in allowed files. Full detail:
> [`../05-qa/documentation-residue-sweep.md`](../05-qa/documentation-residue-sweep.md)
> ("PR #59 revision" section).

- **Files updated (this revision only):** `docs/02-product/feature-taxonomy.md`,
  `docs/02-product/capability-evidence-map.md`,
  `docs/02-product/setup-ux-principles.md`, `docs/03-architecture/README.md`,
  `docs/05-qa/rejected-approaches-log.md`,
  `docs/05-qa/documentation-residue-sweep.md`,
  `docs/01-research/research-handoff.md` (this file),
  `docs/05-qa/defect-pattern-log.md` (addendum note, no new row).
- **Residue fixed:** missed TeqStars/TQ 403/claim-only wording in
  `feature-taxonomy.md` (evidence-weighting + "weak or blocked evidence"
  section, routing language, no new per-cell claims) and
  `capability-evidence-map.md` (competitor-keys line + `C-DOCS-01/02` rows,
  corrected against already-merged Sprint C2 evidence only); stale
  single-store/multi-store "not decided" wording in `feature-taxonomy.md`
  (3 locations) corrected against DEC-003; stale Odoo Online
  compatibility "open question" in `setup-ux-principles.md` (2 locations)
  corrected against RB-14 Part 2 (PR #58); `rejected-approaches-log.md`'s
  historical notes still implying no rejection existed, now marked
  superseded by RA-001; `docs/03-architecture/README.md`'s "What belongs
  here" line still naming the phantom `architecture-preparation.md`.
- **Learning feedback loop:** addendum to **DP-007** (`defect-pattern-log.md`)
  — same category/root cause, not a new occurrence; reinforces that a residue
  sweep must grep a pattern across *every* allowed file, not stop at the first
  hit per file. No new rejected approach; no new technical debt; no AR row
  touched.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured (DP-007 addendum) · no new rejected approach ·
  no new technical debt · no repeated-issue escalation needed — all **YES**.
- **Stop condition:** stopped after pushing one commit to the same PR #59
  branch (not merged, no new PR opened). DEC-003 body untouched; MVP scope
  unchanged; no architecture decision made; `main`/plain `dev` untouched.
  Awaiting ChatGPT/Fable re-review.

---

# RB-14 Architecture Preparation — Part 2 Handoff

> **RB-14 Part 2 — High-risk open-question resolution and decision-candidate refinement.** The
> architecture-preparation sprint after PR #57 (RB-14 Part 1) merged into `Shopify-connector`.
> Re-checked **only** the high-risk open questions from Part 1 against **official Shopify docs**,
> **official Odoo 19.0 docs**, and **official Odoo 19.0 source code** (`odoo/odoo` 19.0); resolved/
> narrowed **only where official evidence supports it**; kept the rest open. Produced a **decision-
> candidate brief** and narrowed **AR-002/AR-003/AR-005** — **deciding none**. No-code and
> no-architecture-decision gates in force (`CLAUDE.md` §4–§5). Session date 2026-07-01.

## Session summary

Confirmed the pre-conditions (PR #55/#56/#57 merged into `Shopify-connector` — the branch is at
`ec6f494`, the PR #57 merge; AR-002/003/005 framed-not-decided; DEC-003 unchanged; implementation
unauthorized), then ran a **scoped, documented high-power verification** of the ten enumerated
high-risk questions. **Four source-code / GID questions were verified directly** by reading the
official `odoo/odoo` 19.0 source (`ir_cron.py`, `ir_model.py`, `odoo/orm/models.py`) and the
Shopify GID page; **six official-doc questions were verified by a fan-out** (6 verifiers + 6
adversarial cross-verifiers). **All six cross-verifiers confirmed their verifier's status** with
no surviving overclaim (two minor quote fixes applied). **AR-002/AR-003/AR-005 are refined but
NOT decided**; no REST/GraphQL, distribution, OAuth/token, queue-framework, binding/data-model,
or module-boundary choice was made; DEC-003 and MVP scope unchanged.

## Branch and commits

**Working branch:** `claude/rb-14-architecture-part-2-ey2a69` (the harness-designated branch;
based on `Shopify-connector` @ `ec6f494`, the merged **PR #57** tip). **Branch-name note for
ChatGPT (flagged):** the RB-14 Part 2 prompt named
`architecture/rb14-part2-risk-resolution-decision-candidates`, but the session's hard git rule
designates the harness branch (`claude/rb-14-architecture-part-2-ey2a69`) and forbids pushing to
a different branch without explicit permission, so work proceeded on the harness-designated
branch; **the PR targets `Shopify-connector`**; `main` and plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `7e69111` | docs: resolve rb14 high-risk open questions |
| `fb00082` | docs: refine rb14 decision candidates |
| _(this commit)_ | docs: update rb14 part2 handoff and qa gates |

## High-power research mode used

**Yes — scoped to official-source / source-code verification only** (authorized by the prompt's
capability instruction + `CLAUDE.md` high-power section). **Plan (documented before launch):**
(a) **Why:** training cutoff is Jan 2026; the ten high-risk questions need live 2026-07-01
verification, four against actual 19.0 source. (b) **Workstreams:** four source-code/GID reads
done directly in the main loop; a 6-verifier + 6-adversarial-cross-verifier fan-out for the
remaining official-doc questions, each fetching a fixed official page set and returning
verbatim-quoted, claim-classified facts. (c) **Sources:** `shopify.dev` + official changelog;
`odoo.com/documentation/19.0` + official 19.0 raw RST; official `odoo/odoo` 19.0 source. **No
competitor/blog/forum.** (d) **Stop condition:** each question resolved only where official
evidence literally supports it; else kept open. (e) **Synthesis/verification:** worker-owned
classification + adversarial cross-verify (default to the more conservative status); source
findings labelled `[Official source-code fact]`; two quote-transcription fixes applied. (f)
**Unsupported-claim prevention:** absence ≠ opposite; negatives (e.g. "no async queue in core")
stay inferences; nothing promoted to a decision. **Result:** all statuses upheld by cross-verify;
~280k subagent tokens + the direct source reads.

## Files created or updated

**Architecture (`docs/03-architecture/`) — new:** `rb14-part2-open-question-resolution.md`,
`rb14-decision-candidate-brief.md`. **Updated:** `architecture-decision-framing.md`,
`ar-002-distribution-api-framing.md`, `ar-003-sync-orchestration-framing.md`,
`ar-005-binding-dedup-framing.md` (RB-14 Part 2 notes; Part 1 preserved; rows stay `[Not
decided]`).

**Research (`docs/01-research/`) — updated:** `shopify-official-api-notes.md` (RB-14 Part 2
section), `odoo-official-architecture-notes.md` (RB-14 Part 2 section incl. source-code facts),
`research-handoff.md` (this file).

**QA (`docs/05-qa/`) — updated:** `architecture-review-log.md` (RB-14 Part 2 non-decision note),
`defect-pattern-log.md` (RB-14 Part 2 no-new-defect note; no counter change).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/Docker; no
`addons/**`; no `docs/04|06|07|08`; no `.claude/**`). **DEC-003 not modified; MVP scope
unchanged.**

## Questions resolved / narrowed (official evidence)

- **Resolved (from source):** RQ-003-3 (`ir.cron` signatures + failure constants 3/5/7d);
  RQ-005-3 (`ir.model.data` fields + `UniqueIndex('(module, name)')`); RQ-005-4 (`sudo()`
  bypasses access rights **and** record rules).
- **Materially narrowed (Shopify docs):** RQ-005-2 (**24-hour** idempotency dedup TTL + fixed
  **17-mutation** `@idempotent` set; no general mechanism / `clientMutationId`); RQ-003-1 (**Odoo
  Online incompatible with custom modules** → substrate Odoo.sh/on-prem); RQ-002-1 (custom apps
  **not categorically forbidden from REST**; GraphQL sole long-term API; no REST EOL); RQ-002-2
  (protected-data access **"Always available"** for custom apps vs **"Requires review"** for
  public; compliance webhooks App-Store-scoped); RQ-002-3 (offline token model + 90-day rotating
  refresh).
- **Re-confirmed open:** RQ-005-1 (GID permanence **not asserted**); RQ-003-2 (`[Official
  source-code fact]` reviewed source confirms `ir.cron` + signatures/constants + `with_delay`
  absent; `[Inference]` a general async queue was not found in the reviewed docs/source; `[Open
  question]` whole-repo absence; OCA `queue_job` community).

## Questions still open (blocking a confident decision)

- **AR-002:** blanket custom/private GraphQL-mandate scope + REST EOL; whether custom apps **must
  implement** the compliance webhooks / are bound by L1/L2 obligations (**not assumed absent**).
- **AR-003:** Odoo.sh/on-prem `server_wide_modules` + jobrunner support (gates `queue_job`);
  MVP-scale throughput under `--max-cron-threads=2`.
- **AR-005:** `@idempotent` key-uniqueness scope; bulk-op idempotency; GID permanence/non-reuse;
  the per-store binding data-model decision itself.

## Candidate-narrowing summary (inputs, not decisions)

- **AR-002 [Decision candidate]:** custom app + GraphQL-first + offline token (lead); public app
  later; hybrid weak; REST-heavy avoid-candidate.
- **AR-003 [Decision candidate]:** internal cron-queue **or** `queue_job` (turnkey) primary;
  cron-only floor; external-worker + per-tier-hybrid weakened (Odoo Online excluded).
- **AR-005 [Decision candidate]:** dedicated per-domain **or** hybrid binding model primary;
  generic table viable; `ir.model.data` reuse weak/avoid; ID-on-record convenience-only.
- **All labelled `[Recommendation]`/`[Decision candidate]`; every AR row stays `[Not decided]`.**

## Learning feedback loop

- **New issues discovered:** none. **No new defect pattern; no new DP row; no counter change**
  (`../05-qa/defect-pattern-log.md` RB-14 Part 2 note). The sprint **applied** DP-001 (re-read the
  source — went to actual 19.0 source), DP-003/DP-004 (competitor evidence excluded from this
  official-only pass), DP-005 (options/candidates are inputs, not decisions), and the DP-006
  evidence-consistency gate (official fact / source-code fact / inference / open question kept
  distinct; conditional/absent items kept conditional/open, e.g. custom-app compliance obligations
  **not assumed absent**; the async-queue absence **kept an inference**).
- **Repeated issue patterns:** none at threshold.
- **Rules/checklists updated:** none new; reinforced (a) **verify load-bearing facts against
  actual source**, not just docs, when the docs are silent (four questions resolved this way);
  (b) the **adversarial cross-verify** default-to-conservative rule caught nothing to downgrade
  but confirmed no overclaim — a DP-003 application.
- **New rejected approaches:** none (narrowing only; weak/avoid-candidates are **not** formal
  rejections — `../05-qa/rejected-approaches-log.md` unchanged; formal rejection needs ChatGPT,
  `CLAUDE.md` §10).
- **New technical debt:** none (no code).
- **Architecture concerns:** AR-002/003/005 refined-not-decided; AR-004/006/007/008 remain
  later — non-decision note in `../05-qa/architecture-review-log.md`.
- **Should future prompts change? Minor:** architecture-prep prompts should keep authorizing
  **reading official source code** for load-bearing facts the docs don't state, and keep every
  narrowing an **input/`[Recommendation]`/`[Decision candidate]`** (never a decision). Branch
  reality remains the harness `claude/...` branch while the PR targets `Shopify-connector`.
- **Quality gate:** satisfied — allowed-files-only; no forbidden files; official facts +
  source-code facts cited + dated + classified; competitor evidence excluded from this pass;
  every candidate `[Not decided]`; DEC-003 and MVP scope unchanged; handoff + learning loop
  updated.

## What ChatGPT should review

1. **Open questions are resolved only where official evidence supports it** — spot-check the
   verbatim quotes + URLs/source paths in `rb14-part2-open-question-resolution.md`.
2. **Open questions remain open where evidence is missing** (custom-app compliance obligations;
   `@idempotent` key scope; bulk-op idempotency; GID permanence; whole-repo async-queue absence).
3. **Source-code facts are not turned into architecture decisions** — labelled `[Official
   source-code fact]`, routed as inputs.
4. **Decision candidates are not presented as decisions** — all `[Recommendation]`/`[Decision
   candidate]`; every AR row `[Not decided]`.
5. **No REST/GraphQL, queue, binding, data-model, module, or distribution choice is made.**
6. **MVP scope and DEC-003 remain unchanged; implementation remains blocked.**
7. **UX skill usage stays at the implications level** (no screens/wireframes).

## Stop condition

Stopped at the RB-14 Part 2 boundary: three stage commits on the harness-designated branch + one
**draft** PR targeting **`Shopify-connector`**, **not merged**. **No** connector code, Odoo
module, architecture decision, ADR, implementation plan, module boundary, or REST/GraphQL/
queue-framework/data-model/distribution choice. **DEC-003 and MVP scope unchanged.** `main` and
plain `dev` untouched; only RB-14 Part 2 allowed files changed. Awaiting ChatGPT review.

## Recommended next session

**RB-14 Part 3 — Architecture Decision Sprint for AR-002** (distribution + API + auth), **only if
ChatGPT accepts Part 2.** AR-002 is the most narrowed (custom + GraphQL-first + offline-token lead
candidate) and constrains AR-003 (hosting) and AR-005 (idempotency surface); then AR-003 + AR-005
in parallel, then AR-006/007/008, with AR-004 last. Keep the no-code gate; one scoped objective
per session. **The Part 3 prompt is not written here (not requested).**

## Quality gate confirmation (RB-14 Part 2)

- [x] Session handoff updated (this block).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (RB-14 Part 2 no-new-defect note in
  `defect-pattern-log.md`; RB-14 Part 2 non-decision note in `architecture-review-log.md`).
- [x] Any rejected approach logged (none — narrowing only; weak/avoid-candidates are not formal
  rejections).
- [x] Any accepted technical debt logged (none — no code).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-001/003/004/005/006
  applied, not re-triggered).

---

# RB-14 Architecture Preparation — Part 1 Handoff

> **RB-14 Part 1 — Official-source refresh and architecture decision framing.** The first
> architecture-preparation sprint after the research + MVP-scope baselines merged (PR #55 DEC-003,
> PR #56 TeqStars rebaseline). Produced the **first documents under `docs/03-architecture/`** — a
> current **official-source refresh** and **decision framing** for **AR-002** (distribution/API),
> **AR-003** (sync orchestration/queue), and **AR-005** (binding/dedup/identity). **Frames the
> decisions; decides none.** No-code gate and no-architecture-decision gate in force
> (`CLAUDE.md` §4–§5). Session date 2026-07-01.

## PR #57 revision (2026-07-01, ChatGPT review — REVISE)

ChatGPT reviewed PR #57 and returned **REVISE** for **source-classification and evidence-date
consistency** (the framing substance was accepted directionally — AR-002/003/005 framed-not-decided;
no code; no architecture decision; no implementation authorization). Corrected on the same branch
(`docs: clean rb14 classification and date caveats`) **without changing architecture scope or any
decision**: (1) the Shopify/Odoo official-notes "Source hierarchy and access date" sections now
distinguish the **Sprint B baseline (2026-06-30)** from the **RB-14 refresh (2026-07-01)** and
record GraphQL `latest` moving `2026-04`→`2026-07` (version-sensitive facts use the RB-14 refresh);
(2) **"Odoo core has no async job queue"** downgraded from **[Official fact] → [Inference from
official fact]** (docs document only `ir.cron`; `queue_job` community, not core; verify vs 19.0
source if load-bearing); (3) **secret/config storage** (`ir.config_parameter`/config-model/
encrypted-field) no longer implied as an official recommendation — **[Open question] + [Inference]**;
(4) **`ir.model.data` column list + `(module,name)` uniqueness** kept **[Open question]**;
(5) **custom-app compliance-webhook** wording made conservative — App-Store *review gate* may not
apply, but **non-App-Store privacy/data-deletion obligations left [Open question], not assumed
absent** (dropped "sidesteps"). **No architecture decision; DEC-003 and MVP scope unchanged; no
code; implementation still blocked.** Logged as a no-new-defect note in
`../05-qa/defect-pattern-log.md` (no counter change).

## Session summary

Confirmed the pre-conditions (PR #55 + PR #56 merged into `Shopify-connector`; DEC-003 accepts
controlled product import/export/update in MVP; customer export + full autonomous bidirectional
catalog management remain later; architecture undecided; implementation unauthorized), then ran a
**scoped, documented high-power official-source refresh** (13 Tier-1 verifiers, ~40 `shopify.dev`
/ `odoo.com/19.0` pages, verbatim-quoted and claim-classified, competitor sources excluded) and
authored the RB-14 framing set. **AR-002/AR-003/AR-005 are framed with candidate options,
evidence-for/against, risks, UX implications, required-evidence-before-decision, and recommended
decision criteria — every option labelled `[Not decided]`.** **AR-004/AR-006/AR-007/AR-008 remain
not framed and not decided.** No connector code, no Odoo module, no ADR, no implementation plan,
no module boundary, and **no REST/GraphQL, queue-framework, binding/data-model, or distribution
choice** was produced. DEC-003 and MVP scope are unchanged.

## Branch and commits

**Working branch:** `claude/rb-14-architecture-prep-lwaeeq` (the harness-designated branch; based
on `Shopify-connector` @ `5c27e60`, the merged **PR #56** tip, which includes the **PR #55**
DEC-003 baseline). **Branch-name note for ChatGPT (flagged):** the RB-14 prompt named
`architecture/rb14-part1-official-refresh-decision-framing`, but the session's hard git rule
designates the harness branch (`claude/rb-14-architecture-prep-lwaeeq`) and forbids pushing to a
different branch without explicit permission, so work proceeded on the harness-designated branch;
**the PR targets `Shopify-connector`**; `main` and plain `dev` untouched.

| Hash | Message |
| --- | --- |
| _(commit 1)_ | docs: refresh official architecture sources |
| _(commit 2)_ | docs: frame rb14 architecture decisions |
| _(commit 3)_ | docs: update rb14 handoff and qa gates |

## High-power research mode used

**Yes — focused and scoped to official-source verification only** (authorized by the prompt's
token-control instruction and `CLAUDE.md` high-power section). **Plan (documented before launch):**
(a) **Why:** training cutoff is Jan 2026, so a genuine 2026-07-01 refresh across ~40 official pages
for AR-002/003/005 requires live fetch. (b) **Workstreams:** 8 Shopify + 5 Odoo topic verifiers,
each fetching a fixed page set and returning classified facts with verbatim quotes. (c) **Sources:**
`shopify.dev` and `odoo.com/documentation/19.0` (+ the official `odoo/documentation` 19.0 raw RST
where the HTML was JS-nav-only) — **no competitor/blog/forum**. (d) **Stop condition:** load-bearing
facts re-verified current, deltas surfaced, framing written, no decisions. (e) **Synthesis/
verification:** worker-owned classification; not-on-page → open question; competitor evidence never
promoted. **Result:** 13/13 verifiers returned; facts largely **confirmed unchanged**, with a few
**version-sensitive deltas** flagged and several facts **conservatively downgraded to open
questions** (no over-claiming). ~300k subagent tokens; 102 tool calls.

## Files created or updated

**Architecture (`docs/03-architecture/`) — new:** `rb14-official-source-refresh.md`,
`architecture-decision-framing.md`, `ar-002-distribution-api-framing.md`,
`ar-003-sync-orchestration-framing.md`, `ar-005-binding-dedup-framing.md`.

**Research (`docs/01-research/`) — updated:** `shopify-official-api-notes.md` (RB-14 refresh
section + version-sensitive deltas), `odoo-official-architecture-notes.md` (RB-14 refresh section
+ sharpened caveats), `research-handoff.md` (this file).

**QA (`docs/05-qa/`) — updated:** `architecture-review-log.md` (RB-14 Part 1 non-decision note —
AR-002/003/005 framed-not-decided; AR-004/006/007/008 not framed/not decided; refresh completed;
implementation blocked), `defect-pattern-log.md` (RB-14 no-new-defect note; no counter change).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/Docker; no
`addons/**`; no `docs/04|07|08`; no `.claude/**`). **DEC-003 not modified; MVP scope unchanged.**

## Official sources refreshed (2026-07-01)

Shopify: API strategy/versioning; products/`productSet`/variants; inventory + `@idempotent`;
orders + protected customer data; webhooks + HMAC + reconciliation; rate limits + bulk ops; auth +
distribution + compliance webhooks; GIDs/identity. Odoo: `ir.cron` reliability; **async-queue
absence as an [Inference from official fact]** (docs document only `ir.cron`; `queue_job` is
community, not core); `--max-cron-threads`; ORM/external IDs/`ir.model.data`; security (access
rights/record rules); Odoo.sh
/on-prem hosting. **Confirmed unchanged** except the deltas below; full dated record in
`docs/03-architecture/rb14-official-source-refresh.md`.

## High-risk facts (for ChatGPT verification)

1. **Custom-vs-public GraphQL mandate** — GraphQL-only "must" is stated only for *new public
   apps*; custom/private scope is an open question (AR-002).
2. **GID permanence NOT asserted** — do not treat GID as an immutable uniqueness invariant yet
   (AR-005; deleted/recreated handling).
3. **No general mutation idempotency** beyond `@idempotent` — outbound write idempotency must be
   connector-designed (AR-005/AR-006).
4. **`@idempotent` required now** on inventory set/adjust (2026-04; `latest`=2026-07) — key-scope
   + dedup-TTL unstated (AR-005).
5. **`ir.model.data` `(module,name)` uniqueness/columns unconfirmed** in official docs — verify vs
   19.0 source before reusing it as a binding store (AR-005).
6. **`sudo()` bypass not literally on `security.rst`** — re-source before a credential-security
   design relies on it (AR-002/AR-005).
7. **Odoo Online feasibility open** — SaaS custom-module/worker support uncovered; gates the
   AR-003 substrate. **Hosting not finalized.**

## AR-002 / AR-003 / AR-005 framing status

- **AR-002 (distribution/API)** — **framed, not decided.** Options: public/OAuth/GraphQL-first;
  custom-app/GraphQL-first; hybrid; REST-heavy. Special attention: REST legacy + public-app
  GraphQL-only rule; `productSet` delete-on-omit (list fields); orders/inventory; bulk ops;
  protected customer data; custom-vs-public distribution; setup simplicity.
- **AR-003 (orchestration/queue)** — **framed, not decided.** Options: `ir.cron`-only; webhook +
  cron + internal queue model; webhook + OCA `queue_job`; webhook + external worker; hybrid by
  hosting tier. Special attention: no heavy sync inline; fast ack; per-record isolation; manual
  retry; reconciliation; idempotency hooks; user-friendly logs.
- **AR-005 (binding/dedup/identity)** — **framed, not decided.** Options: dedicated per-domain
  tables; generic binding table; `ir.model.data` reuse; Shopify-ID-on-record; hybrid. Special
  attention: per-store uniqueness; template-vs-variant; SKU/barcode changes; first-sync conflict;
  deleted/recreated Shopify records; manual override; multi-store future; auditability; no
  name-only auto-matching.
- **AR-004/AR-006/AR-007/AR-008** — **not framed, not decided** (AR-006/007/008 depend on
  AR-002/003/005; AR-004 recommended to wait). **Recommended decision order (a recommendation,
  not a decision):** AR-002 → AR-003 + AR-005 → AR-006/007/008; AR-004 last.

## Learning feedback loop

- **New issues discovered:** none. **No new defect pattern; no new DP row; no counter change**
  (`../05-qa/defect-pattern-log.md` RB-14 note). The refresh **applied** DP-001 (re-read the
  source — surfaced version deltas), DP-003/DP-004 (competitor evidence not promoted to official
  fact), DP-005 (options/order are inputs, not decisions), and the DP-006 evidence-consistency
  gate (facts/evidence/inference/recommendation/open-question kept distinct; conditional
  requirements stay conditional).
- **Repeated issue patterns:** none at threshold.
- **Rules/checklists updated:** none new; reinforced that **an official platform fact important
  to an architecture decision should be re-verified live before that decision** (the refresh
  found the `latest` alias moved and sharpened the `@idempotent` timeline within one day of the
  baseline) — a DP-001 application, not a new rule.
- **New rejected approaches:** none (framing only; `../05-qa/rejected-approaches-log.md` unchanged).
  Avoid-list items tagged "Arch review: YES" remain seeded against AR rows and become formal
  rejections **only after ChatGPT review** (`CLAUDE.md` §10).
- **New technical debt:** none (no code).
- **Architecture concerns:** AR-002/003/005 now framed (not decided); AR-004/006/007/008 not
  framed/not decided — non-decision note in `../05-qa/architecture-review-log.md`.
- **Tests or review gates needed:** none active; DP-006 evidence-consistency gate remains the
  standing pre-architecture review gate.
- **Should future prompts change? Minor:** architecture-framing prompts should keep every option
  and the decision order an **input/recommendation** (never a decision), and should **re-verify
  load-bearing official facts live** even against a recent baseline (version aliases + dated
  requirements drift). Branch reality remains the harness `claude/...` branch while the PR targets
  `Shopify-connector`.
- **Quality gate:** satisfied — allowed-files-only; no forbidden files; official facts cited +
  dated + classified; competitor evidence not promoted; every option `[Not decided]`; DEC-003 and
  MVP scope unchanged; handoff + learning loop updated.

## What ChatGPT should review

1. **Official facts are cited, current (2026-07-01), and classified** — spot-check the verbatim
   quotes + URLs in `rb14-official-source-refresh.md` and the version-sensitive deltas.
2. **Competitor evidence is not promoted to official fact** — the framing docs label
   `[Competitor demonstrated]`/`[Competitor claim]` separately from `[Official fact]`.
3. **AR-002/AR-003/AR-005 are framed but not decided** — no REST/GraphQL, queue, binding, data
   model, module, or distribution choice; every option carries evidence-for/against + open
   questions + required-evidence-before-decision.
4. **The recommended decision order is a recommendation, not a decision.**
5. **MVP scope and DEC-003 remain unchanged; implementation remains blocked.**
6. **UX implications stay at the implications level** (no screens/wireframes designed).
7. **High-risk open questions** (custom-vs-public GraphQL; GID permanence; mutation idempotency;
   `ir.model.data` uniqueness; `sudo()` bypass sourcing; Odoo Online feasibility) are surfaced for
   direction, not resolved.

## Stop condition

Stopped at the RB-14 Part 1 boundary: three stage commits on the harness-designated branch + one
**draft** PR targeting **`Shopify-connector`**, **not merged**. **No** connector code, Odoo module,
architecture decision, ADR, implementation plan, module boundary, or REST/GraphQL/queue-framework/
data-model/distribution choice. **DEC-003 and MVP scope unchanged.** `main` and plain `dev`
untouched; only RB-14 allowed files changed. Awaiting ChatGPT review.

## Recommended next session

**RB-14 Architecture Preparation — Part 2: ChatGPT review-driven revision or decision-candidate
refinement** (depending on ChatGPT's review of this framing) — e.g. resolving the high-risk open
questions (custom-vs-public distribution, Odoo Online feasibility, `ir.model.data`/GID
verification) and narrowing AR-002/AR-003/AR-005 candidate options toward decision candidates,
**still gated** (no decision, no code, until ChatGPT approves an architecture-decision sprint).
Keep the no-code gate; one scoped objective per session. **The Part 2 prompt is not written here
(not requested).**

## Quality gate confirmation (RB-14 Part 1)

- [x] Session handoff updated (this block).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (RB-14 no-new-defect note in
  `defect-pattern-log.md`; RB-14 non-decision note in `architecture-review-log.md`).
- [x] Any rejected approach logged (none — framing only).
- [x] Any accepted technical debt logged (none — no code).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-001/003/004/005/006
  applied, not re-triggered).

---

# Research Sprint C2 Handoff — TeqStars Rebaseline and Evidence Correction

> **Research Sprint C2 — TeqStars rebaseline and evidence correction.** A scoped research
> **correction** sprint after PR #55: the TeqStars competitor docs, recorded **403-blocked
> in Sprint C (2026-06-30)**, were **re-checked accessible on 2026-07-01** and rebaselined.
> Research/documentation only; **no-code gate in force** (`CLAUDE.md` §4–§5); **architecture
> stays blocked**, **implementation stays blocked**. Focused high-power research (one
> capture-already-done + a compact adversarial-verification workflow) used **only** for
> TeqStars documentation review — no unrelated competitors crawled. Session date 2026-07-01.

## Session summary

Re-accessed the **TeqStars Odoo 19.0 Shopify documentation** (blocked in Sprint C by an
HTTP-403 **bot/UA filter**, since found to return **HTTP 200 with a browser user-agent** —
**no login wall, no auth bypassed, public content**) and read **all 31 Shopify doc pages**
(~98 embedded screenshots) inside step-by-step procedures. Corrected the TeqStars source
status from **blocked/claim-only → accessible, page-classified evidence**, and propagated the
correction into the source notes, resource inventory, screenshot inventory, competitor deep
dive, feature matrix, and the research synthesis (UX benchmark, common patterns,
best-in-class, gaps/opportunities, avoid-list) **only where the new evidence materially
changes conclusions**. Evidence was gathered with **evidence discipline preserved**
(demonstrated ✅ vs vendor claim 🟨 vs implied ➖ vs not-found ⬜ vs blocked 🔒) and an
**adversarial capture→verify pass** (17 high-stakes items) that **downgraded 3 proposed
upgrades** (automatic-retry/backoff, first-class cross-object reconciliation, and a
metrics/chart dashboard → **⬜ not found**), so **nothing was over-upgraded**. Product docs
received a **reinforcing note only** (TeqStars now demonstrates the accepted controlled
product import/export/update baseline and corroborates "customer export = later"); **DEC-003
and the accepted MVP scope are unchanged**. QA logs received a source-availability note (no
new defect row) and an architecture non-decision note (all AR rows stay Not decided). **No
connector code, no Odoo module, no architecture doc/ADR, no implementation plan, no module
boundary, no REST/GraphQL/queue-framework/data-model/distribution decision** was produced.

## Branch and commits

**Working branch:** `claude/teqstars-evidence-rebaseline-2nppgq` (the harness-designated
branch; based on `Shopify-connector` @ `6d32412`, the merged **PR #55** MVP-scope baseline).
**Branch-name note for ChatGPT (flagged):** the Sprint C2 prompt named
`research/sprint-c2-teqstars-rebaseline`, but the session's hard git rule designated the
harness branch `claude/teqstars-evidence-rebaseline-2nppgq` ("never push to a different
branch without explicit permission"), so work proceeded on the harness-designated branch;
**the PR targets `Shopify-connector`**; `main` and plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `0aad508` | docs: start teqstars rebaseline correction |
| `f969df8` | docs: update teqstars competitor evidence |
| `5f49395` | docs: align research synthesis with teqstars evidence |
| _(this commit)_ | docs: finalize teqstars rebaseline handoff |

## High-power research mode used

**Yes — focused and scoped to TeqStars only** (per the prompt's token-control instruction:
"focused high-power research only where useful for TeqStars documentation review; do not
crawl unrelated competitors"). **Plan (documented before launch, `CLAUDE.md` high-power
section):** (a) **Why:** 31 TeqStars doc pages + ~33 required evidence checks had to be read
and classified from real primary-source evidence with over-upgrade the named hazard.
(b) **Capture:** the worker fetched all 31 pages (browser-UA curl → HTML→text) and read them
in full — capture stayed worker-owned so claim classification is centrally governed.
(c) **Verify:** a compact `parallel()` workflow of **17 adversarial verifiers** (one per
high-stakes/contested classification) re-read the local primary-source text and tried to
**downgrade** each proposed symbol (default to the more conservative symbol when uncertain).
(d) **Sources:** only `docs.teqstars.com/19.0/applications/shopify/*` (no other competitors).
(e) **Stop condition:** all 31 pages classified + high-stakes items verified + allowed docs
updated + handoff/QA updated. (f) **Unsupported-claim prevention:** strict claim symbols;
a comparison-table checkmark or marketing sentence is **not** demonstrated; the Sprint C
idempotency search-snippet stayed **unverified**. **Result:** 17/17 verified; **3 downgrades**
(auto-retry, cross-object reconciliation, metrics dashboard → ⬜); all other upgrades
confirmed by verbatim quote. **Reuses the DP-003 capture→verify discipline.**

## Source status correction (audit trail preserved)

- **Previous Sprint C status (2026-06-30):** TeqStars **docs 403-blocked** (whole
  `docs.teqstars.com` host, 19.0 + 16.0); deep dive was **Apps-listing claim-only**.
  **Retained as history** in `../00-source-materials/competitor-source-notes.md` (R2
  "Sprint C historical" subsections), `resource-inventory.md`, and the screenshot inventory.
- **Current re-check (2026-07-01):** **Accessible** — the 31 pages return **HTTP 200** with a
  browser UA (the proxy fetcher's default UA is still 403-filtered — a WAF/bot UA sniff,
  **not** a login wall; **no auth bypassed; public content**). This satisfies the Sprint C
  unblock path ("a browser-UA fetch of the 19.0 docs — no auth to bypass").
- **Framing:** a **source-availability correction**, **not** a criticism of Sprint C (whose
  refusal to treat blocked content as fact was correct). The historical **Blocked** fact and
  the 2026-06-30 Apps-listing facts are **not** erased.

## Files created or updated

**Source materials (`docs/00-source-materials/`)** — `competitor-source-notes.md`
(R2 restructured: Sprint C historical + Sprint C2 accessible subsections + verbatim quotes),
`competitor-screenshot-inventory.md` (TeqStars real per-page screenshot inventory; no
binaries saved; Sprint C captions retained as history).

**Research (`docs/01-research/`)** — `resource-inventory.md` (Sprint C2 access-change
section), `competitor-deep-dives.md` (TeqStars section rebuilt + cross-competitor row +
headline inference), `competitor-feature-matrix.md` (TQ column rebaselined + caveats),
`ux-ui-benchmark.md`, `common-patterns.md`, `best-in-class-observations.md`,
`gaps-opportunities.md`, `avoid-list.md` (synthesis aligned where TQ materially changes
conclusions), `research-handoff.md` (this file).

**Product (`docs/02-product/`)** — `mvp-scope.md` (Sprint C2 reinforcing evidence note),
`product-research-handoff.md` (Sprint C2 note). **No DEC-003 change; no scope change.**

**QA (`docs/05-qa/`)** — `defect-pattern-log.md` (Sprint C2 source-availability note; no new
row, no counter change), `architecture-review-log.md` (Sprint C2 non-decision note; all AR
rows stay Not decided).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/Docker; no
`addons/**`; no `docs/03|04|07|08`; no `.claude/**`). **DEC-003 not modified.**

## Key evidence corrections (page-classified)

- **Now demonstrated (✅):** store connection + OAuth custom-app + **Test Connection**;
  instance configuration (tabbed, toggle-dense); **product import/export/update**;
  **product matching** ("Sync Listings Based On" = SKU/Barcode/both); **duplicate
  prevention** (customer multi-field dedup + Create-Odoo guard + webhook link-existing +
  Skip-Sync); Listing/Listing-Item binding; **product webhooks create/update/delete**
  (fast-ack background thread); image sync; price import/export; inventory import/export;
  **multi-location** (combine + third-party exclusion); customer import + address;
  orders + workflow + **click&collect**; refunds; cancellations; **returns** (webhook
  lifecycle + Force-Restock); mark-as-paid; **payouts** (Shopify-Payments-only);
  metafields (Product/Variant bidirectional; Customer/Order import-only); collections;
  **catalogs/Markets/B2B pricing**; queue + typed logs + activity-on-failure;
  **controlled, draft-safe product export** (channels-optional = unpublished).
- **Vendor claim only (🟨):** pHash image dedup (comparison-table + `imagehash`/`PyWavelets`
  dependency; no workflow); "Centralized hub"/Reporting-Analytics (no metrics dashboard);
  GraphQL wire behaviour (doc-stated, not independently verified).
- **Implied (➖):** idempotency (adjacent guards only — no explicit `@idempotent`);
  permissions/security (scopes + access-rights mentioned; no role/record-rule model).
- **Not found (⬜):** **customer export** (import-only), **HMAC/webhook signature**,
  **rate-limit/GraphQL-cost throttling**, **automatic-retry/backoff taxonomy**, **first-class
  cross-object reconciliation**, **metrics/chart dashboard**, **multi-company** (vs
  multi-store). *(The Sprint C idempotency search-snippet stays unverified.)*

## Evidence discipline

**No over-upgrade.** Breadth is now demonstrated, but **reliability depth is scored
separately** and kept conservative: the 3 verifier downgrades (auto-retry, cross-object
reconciliation, dashboard) were honored; pHash and GraphQL-wire stayed claims; idempotency
stayed implied; rate-limit/HMAC/customer-export/multi-company stayed not-found. A page title
or a comparison-table checkmark was **never** treated as a demonstrated workflow (DP-003/
DP-004). The **whitespace claims are reinforced, not closed**: TeqStars **confirms** the
idempotency + reconciliation + automatic-retry + rate-limit gaps; it **narrows only the
payout-reconciliation** add-on (EM + TQ, both Shopify-Payments-only).

## Product impact (reinforces the accepted baseline; no scope change)

TeqStars now **demonstrates** the accepted **controlled product import/export/update** MVP
baseline (match key + create-guard + draft-safe export + publish/unpublish + per-listing
sync toggle) and **corroborates "customer export = later"** (no customer export; import-only).
**DEC-003 unchanged; MVP scope unchanged; customer export not moved into MVP.** No serious
contradiction to DEC-003 was found → **no open review note for ChatGPT required.**

## Architecture inputs, not decisions

The rebaseline adds **competitor inputs** to AR-002 (GraphQL doc-stated; controlled draft-safe
export pattern; `productSet`/REST-vs-GraphQL still open), AR-003 (webhooks + scheduled + manual
+ **cron-processed per-op queues** — a data point alongside VT's `queue_job`; framework open),
AR-005 (Listing/Listing-Item binding + SKU/Barcode match keys + create-guard; data model open),
AR-006 (adjacent guards only — reinforces the idempotency/retry/reconciliation/throttle
whitespace), AR-007 (multi-location + quantity-field choice + controlled apply), AR-008
(Update-in-Marketplace + tracking + click&collect). **No AR row is decided** — see the Sprint
C2 non-decision note in `../05-qa/architecture-review-log.md`.

## Open questions

Is TeqStars' **pHash** dedup real at runtime (dependency declared, no workflow)? Does any
**`@idempotent`-style directive** exist in code (not on the docs)? Is there a **monitoring
dashboard** beyond the Operations launcher (none documented)? **Multi-company** vs
multi-store? **HMAC / webhook-signature** verification (HTTPS only)? How are **rate limits**
handled at scale (no throttle documented)? (Unchanged field-wide whitespace: how competitors
surface rate-limit + first-class reconciliation to users — still none, TeqStars included.)

## Learning feedback loop

- **New issues discovered:** none. **No new defect pattern**; **no new DP row; no counter
  change.** Sprint C2 is a **source-availability correction**, logged as a note in
  `../05-qa/defect-pattern-log.md`.
- **Repeated issue patterns:** none at threshold. The **DP-003 capture→verify discipline was
  applied** to the new evidence (17-item adversarial pass → 3 downgrades), and **DP-004** (a
  config field / comparison checkmark ≠ demonstrated support) was **applied, not
  re-triggered** — no capability was over-upgraded.
- **Rules/checklists updated:** reinforced (not new) the standing rule that **an important
  source recorded Blocked must be re-checked before a final scope/architecture decision
  leans on it** — access can change (WAF/bot rules, vendor doc releases). Refines DP-001
  (re-read the source) and DP-003 (blocked-source handling); noted in the defect log and the
  resource inventory. The **browser-UA fetch** is now the recorded unblock method for
  UA-filtered (non-auth) docs.
- **New rejected approaches:** none (research-only).
- **New technical debt:** none (no code).
- **Architecture concerns:** TeqStars now **informs** AR-002…AR-008 (non-decision note in
  `architecture-review-log.md`); **all rows stay Not decided / Evidence pending.**
- **Tests or review gates needed:** none active (research). The DP-006 evidence-consistency
  gate remains the standing pre-MVP/architecture review gate.
- **Should future prompts change? Minor:** competitor-research prompts should state that a
  **UA/bot 403 is not an auth wall** and a **browser-UA re-fetch** is the correct,
  non-bypassing unblock for such sources; and that **blocked/weak sources important to a
  decision should be re-checked before that decision is finalized** (now encoded in the
  defect log + resource inventory + avoid-list). Branch reality remains the harness
  `claude/...` branch while the PR targets `Shopify-connector`.
- **Quality gate:** satisfied — allowed-files-only; no forbidden files; handoffs +
  learning loop updated; evidence page-classified and adversarially verified; DEC-003 and
  MVP scope unchanged; no architecture decided.

## What ChatGPT should review

1. **TeqStars is no longer globally blocked/claim-only** — the source-status correction is
   a source-availability change with the Sprint C blocked record preserved as audit trail.
2. **Evidence upgrades are justified by accessible page-level workflows/screenshots** — spot
   check the verbatim quotes in `competitor-source-notes.md` (R2 Sprint C2).
3. **Capabilities are not over-upgraded** — the 3 verifier downgrades (auto-retry,
   reconciliation, dashboard → ⬜) and the kept 🟨/➖/⬜ items (pHash, idempotency, HMAC,
   rate-limit, customer export, multi-company).
4. **MVP scope and DEC-003 remain unchanged** (product docs carry a reinforcing note only).
5. **No architecture row is decided** (Sprint C2 non-decision note; all AR rows Not decided).

## Recommended next session

Return to the gated **RB-14 architecture preparation** (AR-002 distribution/API, AR-003
orchestration/queue, AR-005 binding/dedup) with the TeqStars evidence now firmed up. Keep the
no-code gate; one scoped objective per session; **do not start RB-14 in this sprint.**

### Exact next-session prompt

> **Research Sprint (RB-14 framing — Part 1): Architecture decision framing and
> official-source refresh — DO NOT DECIDE.** Read `CLAUDE.md`, the latest
> `docs/01-research/research-handoff.md` (Sprint C2), and
> `docs/05-qa/architecture-review-log.md`. Confirm the no-code gate and that all AR rows are
> "Not decided / Evidence pending." Frame — **without deciding** — the evidence still needed
> to resolve **AR-002** (distribution/API strategy), **AR-003** (sync orchestration/queue),
> and **AR-005** (binding/dedup model), citing Tier-1 Shopify/Odoo facts and the now-complete
> competitor evidence (incl. the TeqStars Sprint C2 rebaseline). Allowed files:
> `docs/03-architecture/**` (framing docs only, if the folder is authorised) **or**
> `docs/01-research/**` synthesis + `docs/05-qa/architecture-review-log.md` if not; update the
> handoff. **Do not** write code, create modules, decide REST/GraphQL/queue/data-model/
> distribution, or open a PR into `main`/`dev`. Branch from `Shopify-connector`; PR into
> `Shopify-connector`. Stop after framing + handoff and await ChatGPT review.

## Stop confirmation

Stopped at the Sprint C2 boundary: four stage commits on the harness-designated branch + one
draft PR targeting **`Shopify-connector`**, **not merged**. **No** connector code, Odoo
module, architecture decision, architecture doc/ADR, implementation plan, module boundary, or
REST/GraphQL/queue-framework/data-model/distribution choice. **DEC-003 and MVP scope
unchanged.** `main` and plain `dev` untouched; only Sprint C2 allowed files changed. Awaiting
ChatGPT review.

## Quality gate confirmation (Sprint C2)

- [x] Session handoff updated (this block + product-research-handoff.md Sprint C2 note).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (source-availability note in
  `defect-pattern-log.md`; no new DP row / counter change).
- [x] Any rejected approach logged (none — research-only).
- [x] Any accepted technical debt logged (none — no code).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-003/DP-004 applied,
  not re-triggered; 3 over-upgrades caught and downgraded).

---

# Product Sprint G Handoff

> **Product Sprint G — MVP Scope Acceptance and Decision Baseline.** Records ChatGPT's
> accepted **RB-13 MVP scope** in GitHub and aligns the product documents to that accepted
> baseline. **Documentation/decision-recording sprint only** — no new sources, no research
> agents, no architecture. **No-code gate in force** (`CLAUDE.md` §4–§5). Maps to backlog
> item **RB-13 (MVP scope — now accepted as product scope)**, feeding RB-14 (architecture
> prep) — still gated. Session date 2026-07-01.

## Sprint G revision (PR #55 review — 2026-07-01)

ChatGPT reviewed PR #55 and returned **REVISE** — the first draft **over-deferred product
export**. Corrected on the same branch (`docs: revise mvp baseline for controlled product
export`), a **product-scope correction only** (no architecture, no code):

- **Controlled product export/update is now IN MVP** (Shopify→Odoo import **and**
  Odoo→Shopify export/update, with matching, binding, preview/dry-run, duplicate
  prevention, and draft/unpublished/channel-controlled safety) — **controlled bidirectional
  product onboarding**, not import-first.
- **Full autonomous bidirectional catalog management remains later**; **customer export
  remains later.**
- **Evidence:** product import/export/update is **market-baseline** (EM/VT/WK/SH
  demonstrated). **TeqStars docs** (403-blocked in Sprint C on 2026-06-30) were **re-checked
  by ChatGPT on 2026-07-01 and found accessible**; a **full TeqStars rebaseline is pending a
  later research sprint** and was **not** done here.
- **No architecture finalized; no implementation authorized.** Binding/data model → AR-005;
  API/destructive-apply → AR-002.

*(The Session summary and sections below were authored for the initial Sprint G recording;
apply the correction above — "import-first" is superseded by "controlled bidirectional
product onboarding," and product export is in MVP.)*

## Session summary

Recorded ChatGPT's RB-13 MVP scope decisions as the accepted baseline. Created
**`docs/04-decisions/DEC-003-mvp-scope.md`** (accepted MVP **product-scope** decision:
Option A correctness-core **with controlled bidirectional product onboarding**; product
import **and** controlled export/update + write-back direction; Domain 9
minimal-financial-evidence-only; refunds/cancellations deferred; bulk ops not user-facing;
single-store/single-company; P1-primary/P2-secondary; explicit "no architecture decided /
implementation blocked"). Aligned `mvp-scope.md`, `non-mvp-and-later-phases.md`, and
`user-stories.md` to the accepted baseline (former `open` forks resolved; deferrals with
revisit conditions; persona priority set). Updated both handoffs; applied the **DP-006
evidence-consistency gate**; added non-decision notes to the QA logs. **No connector code,
no Odoo module, no architecture doc/ADR, no implementation plan, no module boundary, no
REST/GraphQL/queue-framework/data-model/distribution decision** was produced.

## Files created or updated

- `docs/04-decisions/DEC-003-mvp-scope.md` (**new**).
- `docs/02-product/mvp-scope.md`, `docs/02-product/non-mvp-and-later-phases.md`,
  `docs/02-product/user-stories.md` (**updated** — aligned to accepted scope).
- `docs/02-product/product-research-handoff.md`, `docs/01-research/research-handoff.md`
  (**updated** — Sprint G sections + checkpoints).
- QA logs (non-decision notes only): `docs/05-qa/defect-pattern-log.md`,
  `architecture-review-log.md`, `rejected-approaches-log.md`, `technical-debt-register.md`.

## MVP acceptance summary

Accepted **Option A** — a correct, observable, recoverable **single-store** sync loop
across the core commerce objects with **controlled bidirectional product onboarding**
(product import **and** controlled export/update), plus **inventory + fulfilment/tracking
write-back**. **Not** unrestricted autonomous bidirectional catalog ownership.
Product-scope acceptance only; every *mechanism* stays gated (RB-14).

## Accepted MVP decisions

- **Direction:** Shopify→Odoo import (products, variants/options, basic images, base
  price/compare-at, customers + matching, orders, order status/lifecycle); **Odoo→Shopify
  controlled product export/update** (matched, bound, previewed, draft/channel-safe);
  Odoo→Shopify write-back (inventory multi-location-aware/idempotent; fulfilment +
  tracking). **Deferred:** customer export; unrestricted autonomous bidirectional catalog
  ownership.
- **Domain 9:** minimal financial **evidence** only (status/labels/references/flags-as-
  source-info/totals/tax/shipping/discount/currency + basic gateway-journal mapping as
  config input) — **no accounting automation.**
- **Inventory:** write-back in MVP; multi-location-aware; **never `committed`**; allowed
  quantity fields only; controlled initial-stock import; **auto-apply not default
  (AR-007).**
- **Reliability spine:** layered sync (webhooks + scheduled + manual + reconciliation);
  HMAC; webhook-ID dedup; fast ack; idempotency; duplicate prevention; per-record
  isolation; reason-coded logs; safe manual retry; retry classification concept; rate-limit
  awareness; resumable jobs; honest freshness.
- **UX:** guided setup; credential masking; test connection; readiness/self-test; basic
  command center; recovery-first error center (MVP); enqueue quick actions; essential
  mappings only; admin/functional roles; open docs + dated changelog + self-test.
- **Store/company:** single-store, single-company; architecture-safe keys.
- **Persona:** P1 primary; P2 secondary; P3/P4 important buyer/deployer personas.

## Deferred scope

**Unrestricted autonomous bidirectional catalog ownership** (all-field two-way conflict
resolution; field-ownership matrix; advanced publish/channel campaign management);
**customer export**; refund sync; cancellation reflection; returns/RMA; full Domain 9
accounting automation; payout/bank reconciliation; multi-package fulfilment; complex tax;
Markets/B2B/POS/gift cards/metafields/subscriptions/abandoned-checkout/recommendations/
Buy-with-Prime;
multi-store/multi-company logic; custom transforms; advanced analytics; public App-Store +
demo packaging + billing/compliance webhooks. **Bulk Operations = not a user-facing MVP
feature** (internal RB-14/AR-002 assessment only). *(**Controlled** product export/update —
matched, bound, previewed, draft/channel-safe — **is in MVP**, not deferred.)* Revisit
conditions in `non-mvp-and-later-phases.md`. **Mandatory future rule:** idempotent-refund /
no-double-refund regression is mandatory if refunds are later included.

## Architecture dependencies still open

AR-002…AR-008 all **Not decided / Evidence pending** (distribution/API + **destructive-apply
(`productSet`) mechanics** for controlled export + internal bulk; orchestration/queue +
Odoo-Online; module boundaries/config; binding/dedup data model + **product match keys
(SKU/barcode) + first-sync source strategy**; error/retry taxonomy + idempotency mechanism +
reconciliation cadence; inventory design + apply mode; fulfilment design). Also **later &
architecture-gated:** full autonomous bidirectional catalog management (all-field two-way
conflict resolution + field-ownership matrix). Plus the **Domain 9 draft-artifact exception**
(returns to ChatGPT if RB-14 finds a draft invoice/payment artifact is required). **DEC-003
feeds these; it decides none.**

## Evidence-consistency gate

**DP-006 gate applied; none discovered.** No claim→fact promotion; weak/claim-only evidence
stayed out of scope; WK Company field stayed a config field (DP-004); auto-apply stayed an
[Inference] → AR-007 (DP-006); "real-time" never asserted; scope acceptance kept separate
from any mechanism decision. **No new DP row; no counter change.**

## No-code / no-architecture confirmation

No connector code; no Odoo module; no `*.py`/`*.xml`/`*.csv`/manifest/controller/security/
data/migration/test files; no CI/Docker; no architecture doc; no architecture ADR; no
implementation-plan doc; no module boundary; no REST/GraphQL/queue-framework/data-model/
distribution decision. Only allowed docs changed. **Implementation remains blocked.**

## Branch reality

Prompt requested `product/sprint-g-mvp-acceptance`; the harness designated
`claude/sprint-g-mvp-scope-jxisgm`, and the session's hard git rule requires working on the
harness-designated branch ("never push to a different branch without explicit permission").
Work proceeds on `claude/sprint-g-mvp-scope-jxisgm`; **the PR still targets
`Shopify-connector`**; `main` and plain `dev` untouched.

## Recommended next sprint

**RB-14 Architecture Preparation — Part 1: Architecture decision framing and
official-source refresh**, starting with **AR-002** (distribution/API strategy), **AR-003**
(sync orchestration/queue), and **AR-005** (binding/dedup model). Keep the no-code gate;
one scoped objective per session. **Do not start RB-14 in this sprint.**

## Stop confirmation

Stopped at the Sprint G boundary. **No** connector code, Odoo module, architecture
decision, architecture doc/ADR, implementation plan, module boundary, or
REST/GraphQL/queue-framework/data-model/distribution choice. MVP **product scope accepted**
(DEC-003); architecture gated; implementation blocked. `main` and plain `dev` untouched;
only Sprint G allowed files changed. Awaiting ChatGPT review.

---

# Product Sprint F Handoff

> **Product Sprint F — MVP Scope Proposal, Non-MVP Boundaries, and User Stories.**
> MVP-proposal synthesis only; **no-code gate in force** (`CLAUDE.md` §4–§5). High-power
> mode **not required** (focused MVP synthesis of already-merged repo evidence — no new
> competitor crawling, no research fan-out). Maps to backlog item **RB-13 (MVP scope
> implications — not finalized)**, feeding RB-14 (architecture prep) — all gated.

## Sprint F revision (PR #54 review — 2026-07-01)

ChatGPT review returned **REVISE** — a small consistency patch (no new research, no scope
change). Corrected on the same branch (`docs: clarify refund acceptance principle in
sprint f`):

- **Refund sync remains open / lean defer** (C-RET-01, US-E4-06) — **not** turned into
  MVP.
- The **MVP acceptance principles** (`mvp-scope.md`) and the user-stories acceptance
  principles now clarify that the **idempotent-refund / no-double-refund regression
  scenario (A-IMP-4) applies only if refund handling is included in MVP; if refunds are
  deferred, it is carried forward as a mandatory acceptance principle for the first
  refund/refund-sync sprint** (never dropped).
- **No MVP scope finalized; no architecture decision made.** Consistency correction only
  (Sprint F revision note added to `../05-qa/defect-pattern-log.md`; not a new defect
  occurrence, no counter change). MVP remains **proposed, not final**.

## Session summary

Produced the **evidence-based MVP scope proposal**: `docs/02-product/mvp-scope.md` (main
deliverable), `docs/02-product/non-mvp-and-later-phases.md` (strict boundaries), and
`docs/02-product/user-stories.md` (10 MVP epics + 6 later-phase epics), consuming the
Sprint D taxonomy/evidence map and the Sprint E vision + setup/UX principles. Recommends
**Option A — "correctness core, import-first"**: a **single-store** connector that
imports products (variants + basic images + base price), customers (deduped), and orders
(basic lifecycle + minimal payment/journal representation), and writes back inventory
(multi-location-aware, idempotent) and fulfilment/tracking — on a full correctness engine
(layered webhooks + scheduled + first-class reconciliation + manual; idempotency; GID↔Odoo
binding + documented dedup keys; per-record isolation; retry classification with safe
manual retry; rate-limit awareness; resumable jobs) — with an operator experience
(guided setup + readiness self-test; command center; recovery-first error center; honest
freshness), role-based access, and open docs. Excludes/defers export, refunds/returns
lifecycle, payouts, Markets/B2B/POS/gift cards/metafields, multi-store & multi-company,
pricelists/per-market, custom transforms, bulk-ops-as-a-feature, and advanced analytics.
The **DP-006 evidence-consistency gate** (8 checks) was applied to every capability.
**No connector code, no Odoo module, no MVP finalization, no architecture decisions, no
ADRs, no implementation plan, no module boundaries, no queue/API/distribution/data-model
choices.** Synthesis was **worker-owned** (no fan-out).

## Branch and commits

**Working branch:** `claude/mvp-scope-user-stories-dms7s8` (the harness-designated
branch; based on `Shopify-connector` @ `6e73f82`, the merged **PR #53** Sprint E
baseline). **Branch-name note for ChatGPT (flagged):** the Sprint F prompt body named
`product/sprint-f-mvp-scope-proposal`, but the session's hard git rule designated the
harness branch `claude/mvp-scope-user-stories-dms7s8` ("never push to a different branch
without explicit permission"), so work proceeded on the harness-designated branch; **the
PR still targets `Shopify-connector`**; `main` and plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `880dda8` | docs: start sprint f mvp scope proposal |
| `1dbea92` | docs: add mvp scope proposal |
| `103a638` | docs: add non-mvp and later-phase boundaries |
| `fd4d131` | docs: add mvp user stories |
| _(this commit)_ | docs: finalize sprint f mvp handoff |

## Files created or updated

**Product (`docs/02-product/`)**
- `mvp-scope.md` (new — main deliverable), `non-mvp-and-later-phases.md` (new),
  `user-stories.md` (new), `product-research-handoff.md` (updated — Sprint F section).

**Research (`docs/01-research/`)**
- `research-handoff.md` (this file — Sprint F section + checkpoints).

**QA / quality memory (`docs/05-qa/`)**
- `defect-pattern-log.md` (updated — Sprint F note: DP-006 gate applied, not
  re-triggered; no new occurrence), `architecture-review-log.md` (updated — Sprint F
  non-decision note), `rejected-approaches-log.md` (updated — nothing rejected),
  `technical-debt-register.md` (updated — no debt).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/Docker;
no `addons/**`; no `docs/03|04|07|08`; no `.claude/skills|agents`).

## MVP proposal summary

- **Thesis:** *small but excellent = a correct, observable, recoverable single-store
  sync loop across the core objects — proven, not just claimed — wrapped in an operator
  experience a non-developer can run.* Win on demonstrated correctness + operator
  experience at the demonstrated object baseline for one store.
- **Recommended option:** Option A (correctness core, import-first), over Option B
  (bidirectional catalog — doubles complexity, forces destructive-apply safety +
  AR-002/005 early) and Option C (thin import-only pilot — violates correctness
  non-negotiables; small but not excellent).

## Recommended MVP scope

**Proposed for ChatGPT review — not final until accepted.** Store connection + creds +
guided setup + test-connection + readiness self-test (C-CONN-01…06, C-FUL-03);
product/variant/basic-image/base-price import + exclude-from-sync (C-PROD-01/04,
C-VAR-01/02, C-PRICE-01); customer import + multi-key matching + basic address
(C-CUST-01/03/04); order import + backfill (60-day gate) + status map + basic workflow
(C-ORD-01…04); inventory write-back (multi-location-aware, idempotent) + quantity default
+ controlled stock import (C-INV-01…04); fulfilment + tracking write-back (C-FUL-01/03);
layered sync + reconciliation + HMAC + id-dedup + freshness (C-SYNC-01…07); queue/job +
retry classification + safe retry + idempotency + rate-limit + resumable (C-JOB-01…05/07);
reason-coded logs + audit + recovery-first error center + notifications (C-OBS-01…04);
command center (C-DASH-01…06); essential mappings + binding/dedup keys + routing
(C-MAP-01…04); role-based access + multi-store-safe keys (C-MULTI-03, C-MULTI-01); open
docs + changelog + self-test (C-DOCS-01…03). **Open (ChatGPT direction call):**
product/customer export (C-PROD-02/05, C-CUST-02), Domain 9 minimum (C-PAY-01/02/03),
refunds/cancellations (C-RET-01/03), bulk ops (C-JOB-06).

## Recommended exclusions

Advanced refunds/returns lifecycle (C-RET-02), payouts (C-POUT-01/02), Markets/B2B/POS/
gift cards/metafields/extended (C-ADV-01…06), multi-company (C-MULTI-02), full multi-store
(C-MULTI-01), pricelists/per-market (C-PRICE-02/03), SEO/taxonomy + BoM/kit (C-VAR-03/04),
order risk (C-ORD-05), multi-package fulfilment (C-FUL-02), custom transforms (within
C-MAP-03), dedicated analytics/financial reporting (C-RPT-01/02), App-Store/Built-for-
Shopify + public demo packaging (C-DOCS-04; within C-DOCS-03 — distribution-gated).

## User story summary

10 MVP epics (store setup & readiness; product/catalog; customer import & matching; order
import & lifecycle; inventory & freshness; fulfilment & tracking; logs/errors/retries/
recovery; command center; mapping & configuration; permissions & roles) — persona-driven
(P1–P4), testable, product-level, each traced to capability IDs + evidence + AR gate —
plus 6 later-phase epics (bidirectional; financial depth; payouts; premium breadth;
multi-tenancy; scale & analytics). **Stories are not implementation tasks.**

## Evidence discipline

The **DP-006 evidence-consistency gate** was **applied, not re-triggered** (8 checks in
`mvp-scope.md`). Tier-1 facts labelled **[Fact]**; EM/VT-demonstrated weighted over
SH/WK/EC/TQ claims; competitor-claim-only items kept out or flagged (pHash image dedup,
TQ breadth); improvement opportunities labelled **[Inference]** (command center, error
center, freshness, empty states, **auto-apply C-INV-04 → AR-007, not decided**);
conditional items kept conditional (OAuth/distribution/queue/binding/taxonomy/inventory/
fulfilment/module-boundaries); WK multi-company stays a config field (➖, DP-004), WK
import-stock stays ⬜; "real-time" never asserted (C-SYNC-07 honesty). No claim was
promoted to a fact; no capability entered MVP as a decision; no weak evidence became
scope.

## MVP inputs, not final decisions

The scope, options, include/exclude/defer/open calls, MVP-critical spine, and acceptance
principles are **inputs for RB-13 acceptance**, not commitments. Every inclusion is
marked **"Proposed MVP inclusion — pending ChatGPT acceptance."** Documents are
banner-marked **proposed, not final**.

## Architecture inputs, not decisions

MVP commits **requirements/intent**, never mechanism. Architecture-dependent items map to
**AR-002…AR-008** (all Not decided / Evidence pending): AR-002 (distribution/API/bulk/
App-Store), AR-003 (orchestration/queue framework), AR-004 (module boundaries/config
model/feature flags), AR-005 (binding/dedup data model/keys), AR-006 (error-retry
taxonomy/idempotency/reconciliation cadence), AR-007 (inventory/apply mode), AR-008
(fulfilment). **No AR row is decided, proposed for active review, or re-litigated** —
logged as a Sprint F non-decision note in `architecture-review-log.md`.

## Open questions

Primary MVP persona (P1 vs P2); **direction** (export in MVP or Phase 2); **Domain 9
minimum**; **refunds/cancellations** (basic idempotent or deferred); **distribution
(AR-002)**; single- vs multi-store/company at MVP (proposed single-store, multi-store-safe
keys); reconciliation cadence + freshness granularity (AR-003/006); error/retry taxonomy
depth + auto-retry set (AR-006); essential mappings + dedup/match keys (AR-005); bulk-ops
need (C-JOB-06); readiness/self-test check set; Odoo edition/hosting (Odoo Online?
edition-gated report disclosure).

## Learning feedback loop

- **New issues discovered:** none. No new defect pattern. The **DP-006
  evidence-consistency gate** (3rd-occurrence, ESCALATED) was **applied, not
  re-triggered**: no competitor claim promoted to a fact, no capability entered MVP as a
  decision, weak/claim-only evidence kept out of scope, no architecture finalized.
  DP-003/DP-004/DP-005 applied throughout.
- **Repeated issue patterns:** none at threshold (no new occurrence added to any
  category).
- **Rules/checklists updated:** none required — existing rules sufficed and were applied.
  QA logs received non-decision / no-new-issue notes only.
- **New rejected approaches:** none — MVP exclusions are recommendations-against-MVP,
  **not** rejected architecture approaches (`CLAUDE.md` §10).
- **New technical debt:** none (no code).
- **Architecture concerns:** MVP proposal supplies capability-scope inputs to
  AR-002…AR-008 — non-decision note; all rows stay Not decided / Evidence pending.
- **Tests or review gates needed:** none active. The DP-006 gate remains the standing
  pre-MVP/architecture review gate; MVP acceptance principles reference the seeded
  regression scenarios (A-IMP-4).
- **Should future prompts change? No** (beyond Sprints D/E) — MVP-synthesis prompts
  should keep every scope call an **input** (MVP=RB-13 / architecture=RB-14 gated), keep
  synthesis worker-owned, keep conditional items conditional (DP-006), and keep
  exclusions as recommendations-against-MVP. Branch reality remains the harness `claude/…`
  branch while the PR targets `Shopify-connector`.
- **Quality gate:** satisfied — allowed-files-only; no forbidden files; handoffs +
  learning loop updated; DP-006 gate applied; MVP marked proposed-not-final.

## What ChatGPT should review

1. **Thesis & option choice** — is Option A right over B and C?
2. **Evidence-consistency gate (DP-006)** — 8-check review holds; nothing weak became
   scope; auto-apply (C-INV-04) stays inference.
3. **Include/exclude/defer/open** — especially the open direction forks (export, Domain 9
   minimum, refunds/cancellations, bulk ops).
4. **Architecture-dependent table** — MVP commits intent only; no AR row decided.
5. **MVP-critical spine + acceptance principles** — endorse/amend.
6. **Boundaries & stories** — boundaries strict enough; stories not implementation tasks.

## Recommended next session

Await ChatGPT's **RB-13 MVP acceptance/revision**. On acceptance, **RB-14 (architecture
preparation)** against AR-002…AR-008 — starting with **distribution (AR-002)** (unblocks
OAuth/GraphQL/App-Store), then **orchestration/queue (AR-003)** and **binding/dedup model
(AR-005)** that the correctness core depends on — all gated and ChatGPT-reviewed.
Optionally firm up weak/blocked evidence (TQ 403; EC/R5; 17 unread VT Confluence). Keep
the no-code gate; one scoped objective per session.

## Stop confirmation

Stopped at the Sprint F boundary as instructed. **No** connector code, **no** Odoo
module, **no** MVP finalization, **no** architecture decisions, **no** ADRs, **no**
implementation plan, **no** module boundaries, **no** REST/GraphQL/queue-framework/
distribution/data-model choices. MVP scope marked **proposed, not final**. `main` and
plain `dev` untouched; only the Sprint F allowed files changed. Awaiting ChatGPT review.

---

# Product Sprint E Handoff

> **Product Sprint E — Product Vision, Quality Bar, UX Principles, and
> Differentiation Strategy.** Product strategy / synthesis only; **no-code gate in
> force** (`CLAUDE.md` §4–§5). High-power mode **not required** (synthesis of
> already-merged repo evidence — no new competitor crawling, no research fan-out).
> Maps to backlog item **RB-11 (product vision draft)**, feeding RB-13 (MVP
> implications) and RB-14 (architecture prep) — all gated.

## Session summary

Created the **product vision** (`docs/02-product/product-vision.md`) and the
**setup/UX principles** (`docs/02-product/setup-ux-principles.md`) for the Odoo 19 ↔
Shopify Connector, consuming the Sprint C research baseline and the Sprint D
canonical feature taxonomy + capability evidence map. The vision positions the
connector as **correctness-first, UX-first, recovery-first, observable, honest,
modular/customizable, performance-aware, evidence-based, upgrade-safe, and premium
but not bloated** (simple for normal users, powerful for advanced users). It states
the product thesis, target personas (inference-level P1–P4), core customer problems,
ten product principles, a premium quality bar, a five-theme differentiation strategy,
per-domain strategies (UX / reliability / modularity / performance / security /
docs-trust), seven product non-negotiables, and explicit **MVP / later / architecture
inputs (not decisions)**. The UX doc defines a UX north star and 12 principles plus
per-area principle sets. **No connector code, no Odoo module, no MVP finalization, no
architecture decisions, no ADRs, no implementation plan, and no module boundaries**
were produced. Synthesis was **worker-owned** (no fan-out).

## Branch and commits

**Working branch:** `claude/sprint-e-product-strategy-gd2kfs` (the harness-designated
branch; based on `Shopify-connector` @ `9a744f7`, the merged **PR #52** Sprint D
baseline). **Branch-name note for ChatGPT (flagged):** the Sprint E prompt body named
`product/sprint-e-product-vision-quality-bar`, but the session's hard git rule
designated `claude/sprint-e-product-strategy-gd2kfs` ("never push to a different
branch without explicit permission"), so work proceeded on the harness-designated
branch; **the PR still targets `Shopify-connector`**; `main` and plain `dev`
untouched.

| Hash | Message |
| --- | --- |
| `ce36ffc` | docs: start sprint e product vision |
| `d3da053` | docs: add product vision |
| `5561db3` | docs: add setup ux principles |
| _(this commit)_ | docs: finalize sprint e product handoff |

## Files created or updated

**Product (`docs/02-product/`)**
- `product-vision.md` (new — main deliverable), `setup-ux-principles.md` (new),
  `product-research-handoff.md` (updated — Sprint E section).

**Research (`docs/01-research/`)**
- `research-handoff.md` (this file — Sprint E section + checkpoints).

**QA / quality memory (`docs/05-qa/`)**
- `defect-pattern-log.md` (updated — Sprint E note: DP-006 gate applied, not
  re-triggered; no new occurrence), `architecture-review-log.md` (updated — Sprint E
  non-decision note), `rejected-approaches-log.md` (updated — nothing rejected),
  `technical-debt-register.md` (updated — no debt).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/
Docker; no `addons/**`; no `docs/03|04|07|08`; no `.claude/skills|agents`).

## Product vision summary

- **What:** a best-in-class, modular, reliable Odoo 19 ↔ Shopify connector — a
  correct, observable sync core wrapped in an operator experience, delivered as an
  isolated, upgrade-safe addon family.
- **Positioning:** *correct by design, honest by default — and can prove both to the
  operator.*
- **Thesis:** breadth is table stakes; win on **demonstrated correctness** and the
  **operator experience**, ship the demonstrated breadth as a clean baseline, and
  offer premium breadth as **optional add-ons** on an honest, modular core.
- **Premium quality bar** = correctness / experience / trust, **not** feature count;
  seven **non-negotiables** form the quality contract.
- **Differentiation (inputs):** (1) demonstrated correctness (idempotency +
  reconciliation + rate-limit awareness), (2) command center + recovery-first errors
  together, (3) easy onboarding with real reliability, (4) honesty/transparency, (5)
  premium breadth as clean add-ons.

## UX principles summary

- **North star:** the operator always knows *is everything OK / what failed and why /
  what do I do next* and can act without reading source or filing a ticket.
- **12 principles:** guided setup; prove readiness before sync; progressive
  disclosure; honest status & freshness; command center over scattered menus;
  recovery-first errors; safe-by-default actions; human-readable logs; guided
  mappings; role-aware UX; modular feature visibility; documentation mirrors the
  product — plus per-area principle sets. **No screens or menus are designed.**

## Evidence discipline

- **DP-003 applied:** competitor UX/product statements stay claims; TQ (docs 403) and
  EC (no screenshots) stay claim-only/weak; SH ✅ rest on captions; EM/VT-demonstrated
  evidence is weighted highest.
- **DP-004 applied:** WK multi-company kept **config-field-only (➖)**; market promises
  not treated as demonstrated bidirectionality.
- **DP-005 applied:** every principle/candidate is an **input**, not a decision;
  MVP=RB-13 and architecture=RB-14/AR-002…AR-008 stay gated.
- **DP-006 evidence-consistency gate applied:** conditional platform items (OAuth,
  distribution, queue framework, REST/GraphQL, multi-company, module boundaries,
  payouts, data models) stay conditional/open; improvement opportunities (auto-apply,
  unified command center, freshness) labelled **inference**, not demonstrated
  competitor capability. **No claim promoted to a fact; no on-page detail invented.**

## MVP inputs, not decisions

Candidate core (input): connect+prove; core object sync at the demonstrated baseline;
the sync+correctness engine (webhooks + reconciliation + scheduled + manual,
idempotency, dedup/binding, retry/recovery); operator UX (command center +
recovery-first errors + honest freshness); role-based access. Explicitly later
(input): advanced breadth, payouts, financial reporting, per-market pricing,
custom-Python transforms, multi-company. **MVP is not finalized** — candidates for
**RB-13** only. Open: single/multi-store; single/multi-company; core vs optional
add-on grouping; **primary MVP persona (P1 vs P2)**.

## Architecture inputs, not decisions

The vision/UX principles supply **product-intent inputs** to **AR-002…AR-008** — all
remain **"Not decided / Evidence pending."** No distribution model, OAuth mandate,
REST/GraphQL choice, queue framework, binding data model, module boundary/name, or
inventory/fulfilment design is decided. A **non-decision note** was added to
`architecture-review-log.md`.

## Open questions

Distribution model (AR-002); primary MVP persona + single/multi-store & company
(RB-13); core vs add-on grouping / feature-flag model (RB-13/AR-004); reconciliation
cadence + per-object vs global freshness (AR-003/006); error/retry taxonomy (AR-006);
binding model + deleted-binding handling (AR-005); queue framework + Odoo-Online
(AR-003); non-Shopify-Payments payout modelling; Odoo edition gating disclosure;
whether firming up weak/blocked evidence (TQ 403, EC/R5, 17 unread VT Confluence)
changes any product framing; demo/docs hosting + self-test scope.

## Learning feedback loop

- **New issues discovered:** none. No new defect pattern emerged. The **DP-006
  evidence-consistency gate** (3rd-occurrence, ESCALATED) was **applied, not
  re-triggered**; DP-003/DP-004/DP-005 prevention rules were applied throughout (no
  claim-as-fact; config field ≠ demonstrated support; classification = input, not
  decision).
- **Repeated issue patterns:** none at threshold; no new occurrence added to any
  category. Escalation gates remain honoured by the no-code gate.
- **Rules/checklists updated:** none required — existing rules were sufficient and
  applied. QA logs received non-decision / no-new-issue notes only.
- **New rejected approaches:** none (nothing evaluated to rejection; noted in
  `rejected-approaches-log.md`).
- **New technical debt:** none (no code; noted in `technical-debt-register.md`).
- **Architecture concerns:** vision/UX principles now supply product-intent inputs to
  AR-002…AR-008 — recorded as a **non-decision note** in `architecture-review-log.md`;
  **all rows stay Not decided / Evidence pending.**
- **Tests or review gates needed:** none active (synthesis). The DP-006
  evidence-consistency gate remains the standing pre-MVP/architecture review gate.
- **Should future prompts change? No** (beyond what Sprint D encoded) — keep every
  principle/candidate an **input** with MVP=RB-13 / architecture=RB-14 gating, keep
  synthesis worker-owned, keep conditional platform items conditional (DP-006). Branch
  reality remains the harness-designated `claude/...` branch while the PR targets
  `Shopify-connector`.

## What ChatGPT should review

1. **Positioning & thesis** — is "correct by design, honest by default, prove both to
   the operator" right, and are the five differentiation themes correctly prioritised
   as inputs?
2. **Evidence discipline (DP-003/004/006)** — no claim-as-fact; EM/VT weighted over
   SH/WK/EC/TQ; conditional items stay conditional/open.
3. **No premature MVP/architecture (DP-005 guard)** — confirm nothing reads as a
   decision or final UI/menus; flag any hardening.
4. **Personas** — are P1–P4 reasonable inference-level inputs, with "primary MVP
   persona" left open?
5. **Non-negotiables** — endorse/amend the seven-item quality contract.
6. **Sequencing** — confirm RB-13 next, then RB-14, consuming this vision + UX
   principles.
7. **Branch-name discrepancy** — confirm working on
   `claude/sprint-e-product-strategy-gd2kfs` (PR → `Shopify-connector`) is acceptable.

## Recommended next session

**RB-13 (MVP scope implications — not finalized)** consuming this vision + UX
principles + the Sprint D taxonomy/evidence map under the DP-006 evidence-consistency
gate, then **RB-14 (architecture preparation)** against AR-002…AR-008 — all gated and
ChatGPT-reviewed. Optionally firm up weak/blocked evidence (TQ 403; EC/R5; 17 unread
VT Confluence). Keep the no-code gate; one scoped objective per session.

## Stop confirmation

Stopped at the Sprint E boundary as instructed: three stage commits on the
harness-designated working branch plus this handoff commit, **one draft PR** targeting
**`Shopify-connector`**, **not merged**. **No** code, **no** Odoo module, **no** MVP
finalization, **no** architecture decisions, **no** ADRs, **no** implementation plan,
**no** module boundaries. `main` and plain `dev` untouched. Awaiting ChatGPT review.

## Quality gate confirmation (Sprint E)

- [x] Session handoff updated (this block + product-research-handoff.md Sprint E).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (no new issue; DP-006 gate applied —
  noted in `defect-pattern-log.md`).
- [x] Any rejected approach logged (none — noted in `rejected-approaches-log.md`).
- [x] Any accepted technical debt logged (none — noted in `technical-debt-register.md`).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-006 gate
  applied, not re-triggered).

---

# Research/Product Sprint D Handoff

> **Research/Product Sprint D — Canonical Feature Taxonomy and Evidence-Based
> Capability Model.** Research/synthesis-only; no-code gate in force (`CLAUDE.md`
> §4–§5). High-power mode **not required** (focused synthesis of already-merged
> Sprint C evidence — no new competitor crawling). Maps to backlog item **RB-12
> (canonical feature taxonomy)**, feeding RB-11 (vision), RB-13 (MVP implications),
> and RB-14 (architecture prep) — all gated.

## Session summary

Converted the Sprint C competitor research into a **canonical feature taxonomy**
(`docs/02-product/feature-taxonomy.md`) and a **capability evidence map**
(`docs/02-product/capability-evidence-map.md`) for the Odoo 19 ↔ Shopify Connector,
and wrote the product-side handoff (`docs/02-product/product-research-handoff.md`).
The taxonomy normalizes the messy competitor feature matrix into **20 canonical
domains** and ≈90 **canonical capabilities**, each classified by evidence
status/strength, capability type (product-UX / reliability / configuration /
architecture), candidate class (baseline / premium / advanced-later / optional
add-on / unknown), MVP relevance (candidate / later / unknown), and
architecture-review dependency (AR-002…AR-008). Every classification is an
**input**, not a decision. **No connector code, no Odoo module, no MVP
finalization, no architecture decisions, no ADRs, no implementation plan, and no
module boundaries** were produced. No new competitor sources were crawled — the
sprint synthesises **already-merged repo evidence only**, preserving per-claim
classification and DP-003/DP-004 discipline. Synthesis was **worker-owned** (main
thread), not fanned out, so claim classification stayed centrally governed.

### Sprint D revision (PR #52 review — 2026-07-01)

ChatGPT review returned **REVISE** (small taxonomy precision patch); corrected on
the same branch (`docs: correct sprint d taxonomy precision`), logged as **DP-006**:

- **Removed the `SH` abbreviation collision** — `SH` = **only** sh_shopify_connector
  / Softhealer; Shopify official docs are keyed **SHOPIFY-OFFICIAL** (Odoo official
  = **ODOO-OFFICIAL**).
- **OAuth-first (C-CONN-01) official-platform dependency made conditional** — strong
  UX/security direction, competitor-demonstrated (VT), but a platform *requirement*
  **only if public/App-Store distribution is chosen**; custom/private flows may use
  token/custom-app access. AR-002 open; not a finalized decision. Evidence strength
  `A` → `B / A-if-public`.
- **Stock import (C-INV-04) reframed** as "Stock import with controlled apply/review"
  — auto-apply is an **improvement/inference, not demonstrated**; AR-007 still applies.
- **Webkul import-stock coverage corrected** to **⬜ (not found)** per matrix §3 (was
  ✅); matrix-consistent coverage EM✅ VT✅ SH✅ TQ🟨 EC🟨 WK⬜.
- **Escalation:** unsupported-assumption/weak-research reaches its **3rd occurrence**
  (DP-003, DP-004, DP-006) → an **evidence-consistency gate** was recorded in
  `defect-pattern-log.md` (implementation stays paused by the existing no-code gate;
  no capability may enter MVP/architecture as a decision until its evidence strength,
  conditionality, and competitor coverage are ChatGPT-reviewed). **No implementation
  task is set.**

## Branch and commits

**Working branch:** `claude/feature-taxonomy-sprint-d-t8d2t0` (the
harness-designated branch; based on `Shopify-connector` @ `e18ba8e`, the merged
**PR #51** Sprint C baseline). **Branch-name note for ChatGPT (flagged):** the
Sprint D prompt body named `product/sprint-d-feature-taxonomy`, but the session's
hard git rule designated `claude/feature-taxonomy-sprint-d-t8d2t0` ("never push to
a different branch without explicit permission"), so work proceeded on the
harness-designated branch; **the PR still targets `Shopify-connector`**; `main` and
plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `2e297ba` | docs: start sprint d feature taxonomy |
| `70391b9` | docs: add canonical feature taxonomy |
| `aa5d2c4` | docs: add capability evidence map |
| _(this commit)_ | docs: finalize sprint d taxonomy handoff |

## Files created or updated

**Product (`docs/02-product/`)**
- `feature-taxonomy.md` (new — main deliverable), `capability-evidence-map.md`
  (new), `product-research-handoff.md` (new).

**Research (`docs/01-research/`)**
- `research-handoff.md` (this file — Sprint D section + checkpoints).

**QA / quality memory (`docs/05-qa/`)**
- `defect-pattern-log.md` (updated — DP-005 + counter), `architecture-review-log.md`
  (updated — Sprint D non-decision note), `rejected-approaches-log.md` (updated —
  Sprint D "nothing rejected" note), `technical-debt-register.md` (updated —
  Sprint D "no debt" note).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/
Docker; no `addons/**`; no `docs/03|04|07|08`; no `.claude/skills|agents`).

## Taxonomy summary

- **20 domains:** (1) connection/auth/setup, (2) dashboard/command center, (3)
  product catalog, (4) variants/media, (5) pricing, (6) inventory/locations, (7)
  customers/companies/addresses, (8) orders/lifecycle, (9) invoices/payments/
  journals, (10) fulfillment/tracking, (11) refunds/returns/cancellations, (12)
  payouts/reconciliation, (13) webhooks/scheduled/manual/reconciliation, (14)
  queue/jobs/retries, (15) logs/errors/observability, (16) mapping/matching/dedup,
  (17) multi-store/company/permissions, (18) advanced Shopify (Markets/B2B/POS/gift
  cards/metafields), (19) reporting/analytics, (20) docs/support/demo.
- **≈90 canonical capabilities**, each with the required attribute block; **8
  cross-cutting groups** (idempotency-by-default, recovery-first ops, honesty/
  transparency, safe-by-default destructive actions, progressive disclosure,
  feature flags, modularity/extension points, multi-tenancy/permissions).
- **Required canonical capabilities represented:** idempotency, duplicate
  prevention, GID binding, HMAC verification, webhook-id dedup, fast-ack, scheduled
  + manual reconciliation, retry classification, auto-retry, manual retry,
  rate-limit/GraphQL-cost throttling, bulk ops, per-record isolation, resumable
  jobs, reason-coded logs, audit trail, recovery-first error center; setup wizard,
  OAuth-first, credential masking, test connection, scope/readiness check, health
  indicators, named-cause diagnostics, command center, activity timeline, queue
  status, failure counts, quick actions, dry-run/preview, guided mapping,
  progressive disclosure, inline help, empty states, recovery actions, sync
  freshness; feature flags, optional add-ons, domain-isolated/per-store config,
  per-company isolation, role-based access, extension points, mapping/transport
  extensibility (architecture inputs); payouts, advanced refunds, Markets, B2B, POS,
  gift cards, metafields, abandoned-checkout→CRM, recommendations, Buy-with-Prime,
  advanced analytics, app-store packaging, public demo/docs/changelog.

## Evidence discipline

- **DP-003 applied:** competitor claims stay claims; TQ (docs 403) and EC (no
  screenshots) support is marked **claim-only / weak**; SH ✅ marks rest on captions
  (medium-behaviour, low-trust).
- **DP-004 applied:** WK multi-company kept as a **config field only (➖)**; SH
  multi-company kept **not-found**; EC product export kept **not-found**; `✅`/
  "demonstrated" used only with a specific demonstrated workflow/screenshot/dated
  release note/explicit doc.
- **Evidence strength scale (A–E)** in the evidence map: **A** official-platform
  requirement (≈22 caps), **B** strong competitor demonstration (EM/VT-led, ≈45),
  **C** mixed/partial (≈8), **E** whitespace/inference (freshness, empty states,
  plus platform-required-but-undemonstrated items: reconciliation surface,
  rate-limit throttling, webhook-id dedup).
- **No competitor claim promoted to a Tier-1 fact; no on-page detail invented.**

## MVP inputs, not decisions

Capabilities tagged **MVP relevance: candidate** cluster around a **correct,
observable core** (connect+prove; core object sync; sync+correctness engine;
operator command center + recovery-first errors; role-based access). Advanced
breadth (Domain 18), payouts, financial reporting, per-market pricing, custom-Python
transforms, and multi-company are tagged **later**. **MVP is not finalized** — these
are candidates for **RB-13** review only. Open MVP-shaping questions: single- vs
multi-store; single- vs multi-company; core vs optional add-on grouping.

## Architecture inputs, not decisions

The taxonomy maps capabilities to **AR-002…AR-008** (API/distribution; sync
orchestration/queue; module boundaries; binding/dedup; error/retry/idempotency;
inventory; fulfillment) — **all remain "Not decided / Evidence pending."** No
queue framework, REST/GraphQL choice, data model, or module boundary/name is
decided. A **non-decision evidence note** was added to
`architecture-review-log.md`.

## Open questions

Distribution model (public vs custom → AR-002); single/multi-store & single/multi-
company at MVP (RB-13); reconciliation cadence/scope + per-object vs global
freshness; error/retry taxonomy; binding model (`ir.model.data` vs dedicated;
deleted-binding handling — AR-005); queue framework (`ir.cron` vs `queue_job`;
Odoo-Online implications — AR-003); core vs optional add-on grouping; firming up
weak/blocked evidence (Teqstars 403, EC/R5 setup guide, 17 unread VT Confluence);
non-Shopify-Payments payout modelling; Odoo edition gating disclosure.

## Learning feedback loop

- **New issues discovered:** one — **DP-005** (premature-decision risk, category
  #4 premature architecture): a feature taxonomy's *candidate / premium / later*
  labels and *architecture-dependency* tags could be **misread as MVP or
  architecture decisions**. **Prevented/Mitigated** by explicit "inputs, not
  decisions" framing throughout, dedicated "MVP-candidate inputs, not decisions"
  and "Capabilities requiring architecture review" sections, per-field gating
  language, and closing "decides nothing" notes; MVP=RB-13 and architecture=RB-14/
  AR-002…AR-008 remain gated.
- **Repeated issue patterns:** DP-005 is the **1st** occurrence of category #4
  (premature architecture) in the defect-pattern log — no 2×/3× escalation. The
  existing unsupported-assumption/weak-research thread (DP-003, DP-004) was **not**
  re-triggered: DP-004's prevention rule (config field ≠ demonstrated support;
  market promise ≠ demonstrated bidirectionality) was **applied throughout** this
  synthesis (WK multi-company ➖, SH multi-company not-found, EC export not-found,
  TQ claim-only), which is the intended anti-repetition behaviour.
- **Rules/checklists updated:** added **DP-005** + prevention rule to
  `defect-pattern-log.md` (a normalized taxonomy must label every candidate/
  classification as an **input**, not a decision; MVP and architecture stay gated).
- **New rejected approaches:** none (synthesis-only; noted in
  `rejected-approaches-log.md`).
- **New technical debt:** none (no code; noted in `technical-debt-register.md`).
- **Architecture concerns:** the taxonomy now supplies **capability-level inputs**
  to AR-002…AR-008 — recorded as a **non-decision note** in
  `architecture-review-log.md`. **All rows stay "Not decided / Evidence pending."**
- **Tests or review gates needed:** none active (synthesis). For implementation
  (gated), the regression-test set seeded in A-IMP-4 (duplicate orders,
  multi-location double-decrement, missed-webhook reconciliation, idempotent
  refunds, timezone/paging) now maps to specific capability IDs.
- **Should future prompts change? Yes** — product-synthesis prompts should (1)
  require every capability classification to be labelled an **input/candidate** with
  MVP=RB-13 / architecture=RB-14 gating stated (now encoded via DP-005), and (2)
  keep synthesis **worker-owned** (not fanned out) so claim classification stays
  centrally governed. Branch reality remains the harness-designated `claude/...`
  branch while the PR targets `Shopify-connector`.

## What ChatGPT should review

1. **Taxonomy completeness & naming** — are the 20 domains + ≈90 capabilities the
   right canonical decomposition (nothing missing/duplicated/mis-placed)?
2. **Evidence discipline** — spot-check DP-003/DP-004: no claim-as-fact; `✅` only
   where demonstrated; WK multi-company ➖, SH multi-company not-found, EC export
   not-found, TQ claim-only all reflected in both product files.
3. **Classification calibration** — are baseline/premium/advanced-later/optional
   and MVP candidate/later/unknown reasonable **as inputs**? Flag anything reading
   like a premature decision (DP-005 guard).
4. **Architecture routing** — confirm AR-002…AR-008 mapping is correct and that
   **no architecture is decided** (no queue framework, no REST/GraphQL, no module
   boundaries/names, no data models).
5. **Whitespace priorities** — endorse/re-rank the correctness whitespace
   (reconciliation, idempotency, rate-limit throttling, webhook-id dedup) and the
   operator-UX whitespace (command center + recovery-first errors) as leading
   differentiation inputs for RB-13/RB-14 — **without** locking MVP.
6. **Branch-name discrepancy** — confirm working on `claude/feature-taxonomy-sprint-d-t8d2t0`
   (PR → `Shopify-connector`) is acceptable.
7. **Next-sprint sequencing** — confirm RB-11 (vision) / RB-13 (MVP implications) as
   the next gated step, then RB-14 (architecture prep).

## Recommended next session

**RB-11 (product vision draft)** and/or **RB-13 (MVP scope implications — not
finalized)**, consuming this taxonomy + evidence map, then feeding **RB-14
(architecture preparation)** against AR-002…AR-008 — all gated and ChatGPT-reviewed.
Optionally firm up weak/blocked evidence (Teqstars 403; EC/R5 setup guide; 17 unread
VT Confluence) if ChatGPT wants firmer classification. Keep the no-code gate; one
scoped objective per session.

## Stop confirmation

Stopped at the Sprint D boundary as instructed: four stage commits on the
harness-designated working branch, **one draft PR** targeting **`Shopify-connector`**,
**not merged**. **No** code, **no** Odoo module, **no** MVP finalization, **no**
architecture decisions, **no** ADRs, **no** implementation plan, **no** module
boundaries. `main` and plain `dev` untouched. Awaiting ChatGPT review.

## Quality gate confirmation (Sprint D)

- [x] Session handoff updated (this block + product-research-handoff.md).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (DP-005 in `defect-pattern-log.md`).
- [x] Any rejected approach logged (none — noted in `rejected-approaches-log.md`).
- [x] Any accepted technical debt logged (none — noted in `technical-debt-register.md`).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-005 1st occurrence of #4; DP-004 prevention applied, not re-triggered).

---

# Research Sprint C Handoff

> **Research Sprint C — High-Power Competitor Deep Dives, Screenshot/UX Evidence,
> and Workflow Extraction.** Research-only; no-code gate in force (`CLAUDE.md`
> §5). High-power research mode **explicitly authorized** for this sprint. Maps to
> backlog items **RB-02.* (competitor deep dives)**, **RB-03.1 (feature matrix)**,
> **RB-04.1 (UX/UI benchmark)**, **RB-07.1 (common patterns)**, **RB-08.1
> (best-in-class)**, **RB-09.1 (gaps/opportunities)**, and **RB-10.1 (avoid-list)**.

## Session summary

Studied the **eight user-provided competitor resources (R1–R8)** from real
evidence and produced the full Sprint C research set: **source notes + an
analysed screenshot/visual inventory**, **six competitor deep dives** (Webkul,
Teqstars, Emipro, VentorTech, ecommerce_shopify, sh_shopify_connector + a
blocked-source record for the Google Doc), a **first cross-competitor feature
matrix**, a **UX/UI benchmark**, and the **common-patterns / best-in-class /
gaps-opportunities / avoid-list** synthesis. Evidence was gathered with a
**controlled high-power capture→verify fan-out** (one capture agent + one
adversarial verifier per source) and synthesised by the worker so claim
classification and the no-code/no-MVP/no-architecture gate stayed owned centrally.
**Every claim is cited and classified**; competitor capability statements remained
**competitor claims** unless a documented workflow/screenshot demonstrated them;
**no competitor claim was promoted to a Tier-1 fact**; blocked sources were
recorded, **never bypassed**. **No connector code, no Odoo module, no MVP scope,
and no architecture decisions** were produced.

## Branch and commits

**Working branch:** `claude/research-sprint-c-competitors-hgoo8t` (the
harness-designated branch; based on `Shopify-connector` @ `d6fbcdb`, the merged
**PR #50** Sprint B baseline). **Branch-name note for ChatGPT (flagged):** the
Sprint C prompt body named `research/sprint-c-competitor-deep-dives-ux-evidence`,
but the session's hard git rule designated `claude/research-sprint-c-competitors-hgoo8t`
("never push to a different branch without explicit permission"), so work proceeded
on the harness-designated branch; **the PR still targets `Shopify-connector`**;
`main` and plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `6b07fad` | docs: start sprint c high-power competitor research |
| `e1c5ec4` | docs: capture competitor source and screenshot evidence |
| `1e027a0` | docs: add competitor deep dives |
| `da93ba9` | docs: add competitor matrix and ux benchmark |
| `890ce0b` | docs: synthesize competitor patterns and opportunities |
| _(this commit)_ | docs: finalize research sprint c handoff |

## High-power research mode used

**Yes — explicitly authorized and documented before launch** (the
**Sprint C high-power research plan** below was committed in `6b07fad` before any
agent ran). **Workstreams:** a `pipeline()` workflow of **one capture agent per
source (R1–R8)** returning structured, cited, claim-classified evidence (access
status, feature claims, reconstructed workflows, visuals, reliability signals,
release notes, quotes, open questions), each followed by **one adversarial
verifier** that re-read the source and **downgraded anything not literally
supported** (16 agents, 137 tool calls). **Synthesis/verification:** the worker
read every source digest and wrote all deliverables, preserving per-claim
classification and citations. **Unsupported-claim prevention:** strict claim
classes on every line; competitor claims never elevated to facts; blocked/unknown
stated as such; no hidden-feature guessing. **Result:** all 8 sources captured;
the verifier produced material corrections (e.g. **R2 Teqstars Partial→Blocked**;
**ecommerce_shopify "real-time"→cron**; **sh_shopify_connector multi-company→
not-found**), logged as **DP-003**.

### Sprint C high-power research plan (as committed pre-launch)

- **Why high-power mode is needed:** eight competitor resources, several
  multi-page (Emipro ~35 sub-pages; VentorTech 28-article Confluence hub) and two
  previously gated (R2 403; R5 login wall), had to be studied from real evidence
  with verification in one controlled pass.
- **Workstreams / agents:** one capture agent per source (R1–R8) + one adversarial
  verifier per source; worker-owned synthesis.
- **Sources:** R1 Webkul · R2 Teqstars docs (+Apps listing) · R3 Emipro tree ·
  R4 VentorTech Confluence · R5 Google Doc · R6 ecommerce_shopify · R7 VentorTech
  site/ecosystem/Apps · R8 sh_shopify_connector. Tier-1 grounding only from the
  existing official baselines.
- **Screenshots / UI evidence:** analysed markdown inventory (proxy fetcher returns
  markdown/alt-text, not pixels); binaries not forced (sprint rule allows the
  fallback); no auth bypass for any visual.
- **Files to update:** the Sprint C allowed-files set only (listed below).
- **Stop condition:** all accessible sources captured+verified; blocked sources
  documented without bypass; nine deliverables + evidence written, cited,
  classified; QA logs + handoff updated; quality gate satisfied — then stop.
- **Verification method:** two-pass capture→verify; downgrade anything not literally
  on the page; reuse the DP-001 verification gate.
- **Unsupported-claim prevention:** strict claim classification; no claim→fact
  elevation; blocked/unknown stated; no hidden-feature guessing.

## Files created or updated

**Source materials (`docs/00-source-materials/`)**
- `competitor-source-notes.md` (new), `competitor-screenshot-inventory.md` (new),
  `screenshots/README.md` + `screenshots/{webkul,teqstars,emipro,ventortech,odoo-apps}/README.md` (new).

**Research (`docs/01-research/`)**
- `competitor-deep-dives.md` (new), `competitor-feature-matrix.md` (new),
  `ux-ui-benchmark.md` (new), `common-patterns.md` (new),
  `best-in-class-observations.md` (new), `gaps-opportunities.md` (new),
  `avoid-list.md` (new), `resource-inventory.md` (updated — Sprint C access
  changes), `research-handoff.md` (this file).

**QA / quality memory (`docs/05-qa/`)**
- `defect-pattern-log.md` (updated — DP-003 + counter), `architecture-review-log.md`
  (updated — non-decision Sprint C evidence note), `rejected-approaches-log.md`
  (updated — avoid-list-is-not-rejection note), `technical-debt-register.md`
  (updated — Sprint C no-debt note).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/
Docker; no `addons/**`; no `docs/02|03|04|07|08`; no `.claude/skills|agents`).

## Source access results

No auth was bypassed. **Accessible (5):** R1 Webkul, R3 Emipro, R6
ecommerce_shopify, R7 VentorTech site/ecosystem/Apps, R8 sh_shopify_connector —
**plus the Teqstars Odoo Apps listing** as an accessible R2 surrogate. **Partial
(1):** R4 VentorTech Confluence (anonymous banner; 11 of 28 child articles read).
**Blocked (2):** **R2 Teqstars docs host** (HTTP 403 bot-block on the whole
`docs.teqstars.com`, 19.0 **and** 16.0 — verifier downgraded R2 from Partial to
**Blocked**), **R5 Google Doc** (sign-in wall). **New cross-source findings:**
(a) the Teqstars **Apps Store listing is accessible** ($326.20, OPL-1, 83×5.0) and
supplied the R2 evidence; (b) **R5 is the "Get Started" guide for R6
`ecommerce_shopify`** (R6's CTA 301-redirects to that exact doc). Full evidence:
`docs/00-source-materials/competitor-source-notes.md` and the Sprint C section of
`resource-inventory.md`.

## Screenshots / UI evidence captured

Analysed visual inventory in `competitor-screenshot-inventory.md` (no binary files
saved — proxy fetcher returns markdown/alt-text; sprint rule allows the markdown
fallback). **Most demonstrative:** **Emipro** (~29 **real `.png`** screenshots of
queues/Log Book/config) and **VentorTech R4** (traffic-light webhook health,
External-Location mapping, Preview/Report dry-run). **Caption-only/weak:**
Teqstars (17 captions; **docs screenshots 403-blocked**), VentorTech R7 (alt-text
flows). **None:** **ecommerce_shopify (no UI screenshots at all)**; Google Doc
(blocked). sh_shopify_connector has the broadest caption walkthrough (~29 groups)
but no rendered-image verification.

## Competitor deep dives completed

All six in `competitor-deep-dives.md`: **Webkul, Teqstars, Emipro, VentorTech,
ecommerce_shopify, sh_shopify_connector**, plus a **blocked-source record** for the
Google Doc. Each separates competitor claims from facts and from demonstrated
workflows, with per-area feature classification, workflow reconstruction, UX,
reliability, maintenance, strengths/weaknesses, learn/do-better/avoid, and open
questions.

## Key feature findings

- **GraphQL is the converging API** (VentorTech migrated REST→GraphQL Jan 2026;
  all position on it) — consistent with Tier-1.
- **Webhooks + scheduled + manual** is the table-stakes sync shape; **staging/
  queues** are near-universal — **except ecommerce_shopify (cron-only, no
  webhooks, email-only errors)** and Webkul (no webhooks; Feeds staging).
- **Feature-breadth leaders:** sh_shopify_connector (gift cards, abandoned-
  checkout→CRM, recommendations, Buy-with-Prime), Teqstars-on-paper (Markets/B2B/
  payouts/queue — unverified), Emipro (payouts/Markets/metafields/analytic,
  demonstrated).
- **Whitespace (no competitor demonstrates well):** **named rate-limit/cost-aware
  throttling** (none), **first-class user-visible reconciliation** (none),
  **automatic retry** (only VentorTech), **B2B** (only VentorTech), **payout
  reconciliation** (only Emipro demonstrated).
- **Pricing (on-page 2026-06-30):** WK $170 · TQ $326.20 · EC $195.56 · SH
  $168.81 · VT €499 / $569.16; EM price not in docs.

## Key UX/UI findings

- **Best diagnostics — VentorTech:** traffic-light webhook health with a **named
  cause + fix hint**; Preview/Report dry-run; Failed-Job Notifications;
  irreversible-action warnings; honest PII disclosure.
- **Best observability — Emipro:** state-coloured queues + per-line reason-coded
  Log Lines + Log Book.
- **Best monitoring — sh_shopify_connector:** Integration Dashboard + **daily
  activity chart** + failure counts + re-export recovery flag; access-right-gated
  setup.
- **Frustrations to avoid:** "real-time" mislabelling (WK/EC/SH); raw cron
  internals exposed (WK); manual stock-adjustment (EM); email-only errors (EC);
  technical install (VT odoo.conf/queue_job; not Odoo Online); toggle-dense config;
  gated/blocked docs (EC/TQ).
- **No connector has a unified command center + recovery-first error center
  together** — a clear UX differentiator.

## Key reliability findings

- **VentorTech leads (demonstrated by dated release notes):** GraphQL
  **`@idempotent`** directives (Shopify 2026-04), **automatic retry** of safe
  ops, a real **`queue_job`** async queue, HMAC-SHA256 webhooks, and openly
  disclosed **CRITICAL silent-data-loss fixes** (paging, timezone).
- **Emipro:** strong observability (Log Book), email/SKU dedup, stored-reference
  re-export blocking, manual missed-webhook recovery — **but manual-only retry**
  and a **stale v19 changelog**, and its docs cite the **outdated Shopify
  "19 retries/48h"** figure (Tier-1: 8/4h).
- **Across the field:** idempotency is mostly implicit; **rate-limit handling is
  absent**; reconciliation is implicit; "real-time" is overstated. These map onto
  Tier-1 (webhook delivery not guaranteed → reconcile; `@idempotent` from 2026-04).

## Common patterns

Strongly common (≥2 demonstrate): custom-app connect; bidirectional core sync;
**staging/queue before commit**; scheduled + manual sync; SKU/barcode + email
dedup + Shopify-ID write-back; auto-workflow; fulfillment/tracking write-back;
reason-coded in-app logs; per-record failure isolation; GraphQL. Rare/
differentiating: automatic retry, idempotency directives, real job queue,
traffic-light health, dry-run, payouts, gift cards, B2B, abandoned-checkout→CRM.
**Missing across the field:** rate-limit/cost throttling, first-class
reconciliation, a unified command center, honest latency, documented HMAC.
(`common-patterns.md`.)

## Best-in-class observations

Onboarding (VT OAuth + scope/connection test; WK Test Connection), product sync
(EM incremental + CSV fallback; VT testable directional mapping), order flow (VT
auto-workflow pipeline; EM multi-payment fidelity), inventory (VT quantity-field
choice + multi-company; EM deterministic export), fulfillment (EM Put-in-Pack),
logs/errors (EM Log Book; VT diagnostics; SH monitoring), docs/maintenance (EM
honesty; VT dated changelog), security (SH access groups). (`best-in-class-observations.md`.)

## Gaps and opportunities

Top differentiation themes (recommendations, gated): **demonstrated correctness**
(idempotency + reconciliation + rate-limit throttling — the biggest whitespace and
Tier-1-mandated); **best operator UX** (unified command center + recovery-first
errors + named diagnostics + dry-runs); **effortless install with real
reliability** (the combo nobody has); **honesty/transparency** (latency labels,
dated changelog disclosing fixes, open docs/demo); **premium breadth as clean
add-ons** (payouts, B2B, gift cards, Markets). MVP-relevance is tagged
candidate/later/unknown per item — **not finalized**. (`gaps-opportunities.md`.)

## Avoid-list highlights

Webhook-only/cron-only sync; no reconciliation; `ir.cron`-as-a-queue; heavy work
in the webhook request; no rate-limit handling; skipping HMAC; email-only errors;
manual-only recovery; irreversible "Force Done"; single-location inventory;
writing `committed`; legacy fulfillment endpoints; non-idempotent refunds;
assuming payouts exist for all gateways; bot-blocked/gated/stale docs; one-giant-
module / `_inherits` delegation; `productSet` delete-on-omit as partial update.
Items tagged **"Arch review: YES"** route through AR-002…AR-008. (`avoid-list.md`.)

## What is still blocked

- **R2 Teqstars docs** (`docs.teqstars.com`, 19.0 + 16.0) — HTTP **403**
  bot-block on the whole host; no workflow/screenshot evidence. *(The Apps Store
  listing substituted as accessible vendor-claim evidence.)* **Unblock:** a
  browser-UA fetch of the 19.0 docs (no auth to bypass), **or** ChatGPT accepts the
  Apps-listing evidence as sufficient.
- **R5 Google Doc** — sign-in wall; **owner view-access or export required**; it
  is specifically **R6's setup guide**.
- **R4 VentorTech Confluence** — 17 of 28 child articles unread (not gated, just
  not fetched); optional for fuller coverage.

## Inferences, not decisions

All strengths/weaknesses, "do better", gaps/opportunities, avoid-list items, and
the architecture-evidence note are **inferences/recommendations**. **No MVP scope
and no architecture is decided.** Competitor claims are **claims**, not facts;
on-page price/license/version are **facts about the listing on 2026-06-30**. The
AR-002…AR-008 rows remain **"Not decided / Evidence pending."**

## Open questions

Teqstars: are the idempotency/queue-retry/Markets claims real (docs blocked)?
ecommerce_shopify: official vs partner provenance; does product export exist; what
is in the blocked setup doc (R5)? VentorTech: can install be Odoo-Online-friendly;
payout/POS/gift-card roadmap; connector permission model? sh_shopify_connector:
real adoption (no ratings) and currency (no changelog); multi-company; idempotency/
HMAC details? Field-wide: how do competitors surface rate-limit and reconciliation
to users (none observed)? (Per-source lists in the deep dives.)

## Risks

- **Evidence asymmetry:** TQ (docs blocked) and EC (no screenshots) are
  **vendor-claim-heavy** — their real capabilities may differ from the matrix;
  EM/VT carry the most demonstrated evidence (weight accordingly).
- **Vendor-claim drift:** marketing "real-time"/idempotency/queue claims can
  overstate; mitigated by classification + verification (DP-003).
- **Source volatility:** competitor pricing/pages/changelogs change; re-date on
  re-visit. Teqstars 403 may persist.
- **Synthesis temptation:** keep MVP/architecture gated; do not let
  gaps/opportunities harden into decisions before ChatGPT review.

## Learning feedback loop

- **New issues discovered:** one — **DP-003** (unsupported assumption #3 / weak
  research #1): competitor capability statements, **especially from a blocked docs
  site (Teqstars 403) or a screenshot-free listing (ecommerce_shopify)**, risk
  being recorded as facts; "real-time" marketing risks masking a cron/queue model.
  **Prevented** by the capture→verify two-pass + strict claim classification
  (which produced concrete downgrades: R2 Partial→Blocked, EC "real-time"→cron,
  SH multi-company→not-found).
- **Repeated issue patterns:** none at threshold. DP-003 is the **1st** occurrence
  of category #3/#1. Separately, Sprint C found **external confirmation of the
  DP-001 risk** — Emipro's docs cite the stale Shopify "19 retries/48h" figure
  (Tier-1: 8/4h); **not adopted** (the verification gate held). No 2×/3× escalation.
- **Rules/checklists updated:** added **DP-003** + its prevention rule (classify
  every line; never elevate a competitor claim to a fact; run an adversarial
  verifier that downgrades anything not literally on the page) and the occurrence
  counter in `defect-pattern-log.md`. The **per-cell evidence symbol +
  evidence-note** convention in the feature matrix is now the standard for future
  competitor matrices.
- **New rejected approaches:** none (research-only). The **avoid-list** holds
  competitor anti-patterns as **recommendations**, explicitly **not** rejected
  decisions; `rejected-approaches-log.md` notes they route through architecture
  review before any formal rejection.
- **New technical debt:** none (no code). Blocked sources are research gaps, not
  debt (noted in `technical-debt-register.md`).
- **Architecture concerns:** competitor evidence now **informs** AR-002…AR-008 —
  recorded as a **non-decision note** in `architecture-review-log.md` (GraphQL
  convergence; webhooks+cron+queue with `queue_job` as a real data point; SKU/
  email/ID-write-back binding; `@idempotent`+retry; multi-location; FulfillmentOrder).
  **All rows stay "Not decided / Evidence pending."**
- **Tests or review gates needed:** none active (research). For implementation
  (gated): regression tests for duplicate orders, multi-location double-decrement,
  missed-webhook reconciliation, idempotent refunds, timezone/paging — seeded in
  the avoid-list (A-IMP-4) for the definition-of-done.
- **Should future prompts change? Yes** — (1) for blocked/screenshot-free sources,
  prompts should **mandate the capture→verify two-pass and the claim-class
  symbols** (now encoded via DP-003); (2) competitor-research prompts should state
  that the **branch reality is the harness-designated `claude/...` branch** while
  the **PR targets `Shopify-connector`**, to avoid the Sprint C branch-name
  ambiguity.

### Sprint C revision (PR #51 review — 2026-07-01)

ChatGPT review returned **REVISE** for two evidence-classification overstatements;
corrected on the same branch (`docs: correct sprint c evidence classifications`):

- **Correction 1 — Webkul multi-company.** The Webkul default **Company** field was
  initially classified too strongly as **demonstrated multi-company support** (✅).
  True multi-company support/isolation was **not demonstrated**; a visible config
  field is not evidence of multi-company routing or record-rule handling. Downgraded
  to `⬜/➖` in `competitor-deep-dives.md` and to `➖` in `competitor-feature-matrix.md`
  (with an evidence note; EM/VT remain the demonstrated multi-company evidence).
- **Correction 2 — "bidirectional core sync" common pattern.** The strongly-common
  pattern claiming **bidirectional product/order/inventory/customer sync across all**
  connectors was **narrowed**: broad core-object coverage is a common *market promise*,
  but **directionality varies by object and evidence strength** (EC product export not
  found; WK customer export not found; TQ listing-claim only; EM/VT strongest
  directional evidence). Updated in `common-patterns.md`.
- **Category:** unsupported assumption (#3) / weak research classification (#1) — logged
  as **DP-004** in `defect-pattern-log.md`.
- **Prevention rule:** configuration fields must **not** be treated as demonstrated
  feature support unless the workflow/behaviour is shown; common-pattern wording must
  distinguish a **market promise** from **demonstrated bidirectionality**.

## What ChatGPT should review

1. **Claim discipline** — spot-check that competitor claims are not presented as
   facts, especially TQ (docs blocked) and EC (no screenshots), and that the
   verifier's downgrades (R2→Blocked, EC→cron, SH multi-company→not-found) are
   reflected everywhere.
2. **Matrix evidence** — confirm the per-cell symbols + evidence notes are fair
   and that 🟨/🔒 are used where evidence is listing-only/blocked.
3. **Blocked-source handling** — endorse recording R2 docs as Blocked (with the
   Apps-listing surrogate) and R5 as Blocked (= R6's setup guide); decide the
   unblock path for each.
4. **Gaps/opportunities & avoid-list** — confirm these stay **recommendations**
   (no MVP/architecture lock-in) and which opportunities to prioritise for RB-13/
   RB-14.
5. **Branch-name discrepancy** — confirm working on the harness-designated branch
   `claude/research-sprint-c-competitors-hgoo8t` (PR → `Shopify-connector`) is
   acceptable, or instruct otherwise.
6. **DP-003 + verification gate** — endorse making the capture→verify two-pass the
   standing rule for competitor research.

## Recommended next session

With competitor evidence in place, proceed to **RB-12 (canonical feature
taxonomy)** to normalize the matrix rows, then **RB-11 (product vision draft)** and
**RB-13 (MVP scope implications — not finalized)**, feeding **RB-14 (architecture
preparation)** against AR-002…AR-008 — all gated and ChatGPT-reviewed. In parallel,
resolve the **R2/R5 unblocks** (browser-UA fetch decision for Teqstars 19.0 docs;
owner access/export for the Google Doc) and optionally finish the **17 unread
VentorTech Confluence** articles. Keep the no-code gate; one scoped objective per
session.

## Stop confirmation

Stopped at the Sprint C boundary as instructed: five stage commits on the
harness-designated working branch, **one draft PR** to be opened targeting
**`Shopify-connector`**, **not merged**. **No** code, **no** Odoo module, **no**
MVP scope, **no** architecture decisions, **no** ADRs. `main` and plain `dev`
untouched. Blocked sources documented without bypass. Awaiting ChatGPT review.

## Quality gate confirmation (Sprint C)

- [x] Session handoff updated (this block).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (DP-003 in `defect-pattern-log.md`).
- [x] Any rejected approach logged (none — avoid-list is recommendations, noted in `rejected-approaches-log.md`).
- [x] Any accepted technical debt logged (none — noted in `technical-debt-register.md`).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-003 1st occurrence).

## Sprint C high-power research plan

- **Why high-power mode is needed:** Eight user-provided competitor resources
  (R1–R8) must be studied from **real evidence** — full documentation trees,
  on-page screenshots, configuration/setup flows, feature claims, release notes,
  pricing/support, and UX — so the connector is designed from knowledge, not
  guesses. Several sources are multi-page (Emipro doc tree, VentorTech Confluence
  hub with ~27 children) and two were previously gated (R2 Teqstars 403; R5
  Google Doc login wall). Covering this breadth with verification in one pass
  justifies a controlled parallel fan-out (per `CLAUDE.md` → High-power research
  mode; the policy is a capability, not a cap).
- **Workstreams / agents:** One **source-capture agent per resource** (R1 Webkul,
  R2 Teqstars, R3 Emipro + sub-pages, R4 VentorTech Confluence hub + children, R5
  Google Doc, R6 ecommerce_shopify, R7 VentorTech site, R8 sh_shopify_connector),
  each returning **structured, cited, claim-classified evidence** (access status,
  visible sections, feature claims, visuals/screenshots described, workflow steps,
  version context). Then a **verification workstream** that re-checks the
  highest-stakes claims (pricing, sync model, key features, access status) against
  the captured evidence and flags anything unsupported. Synthesis into the
  deliverable docs is performed by the worker (main thread) so governance
  (citation + claim classification + no-MVP/no-architecture gate) is owned
  centrally.
- **Sources to inspect:** R1 https://webkul.com/blog/odoo-multichannel-shopify-connector/ ·
  R2 https://docs.teqstars.com/19.0/applications/shopify/overview.html ·
  R3 https://docs.emiprotechnologies.com/shopify-odoo-connector/v19/installation.html (+ tree) ·
  R4 https://ventortech.atlassian.net/wiki/spaces/pd/pages/482639953/Shopify (+ children) ·
  R5 https://docs.google.com/document/d/1zIwRxp7cvLYeyjl8P_mvsjC-v8Tsd_ugC1JbfTznHC8/edit ·
  R6 https://apps.odoo.com/apps/modules/19.0/ecommerce_shopify ·
  R7 https://ventor.tech/solutions/odoo-shopify-connector/ ·
  R8 https://apps.odoo.com/apps/modules/19.0/sh_shopify_connector#features.
  Tier-1 grounding only from the existing official Shopify/Odoo baselines (these
  competitor sources are Tier 2–5 → **competitor claims**, not facts).
- **Screenshots / UI evidence approach:** Primary evidence is the **screenshot
  inventory markdown** (`competitor-screenshot-inventory.md` + per-vendor
  `screenshots/*/README.md`) analysing what each visual/figure on the source
  pages demonstrates (fields, buttons, tabs, workflow step, status/log surfaces,
  UX). Actual binary image capture is **attempted only where practical and
  high-value**; where impractical (JS-gated, heavy, or auth-gated) it is recorded
  as "no file saved" with the reason — the analysis (not the file's existence) is
  the deliverable. No authentication wall is bypassed to obtain any visual.
- **Files to update:** (research) `competitor-deep-dives.md`,
  `competitor-feature-matrix.md`, `ux-ui-benchmark.md`, `common-patterns.md`,
  `best-in-class-observations.md`, `gaps-opportunities.md`, `avoid-list.md`,
  `resource-inventory.md`, `research-handoff.md`; (source materials)
  `competitor-source-notes.md`, `competitor-screenshot-inventory.md`,
  `screenshots/README.md` + `screenshots/{webkul,teqstars,emipro,ventortech,odoo-apps}/README.md`;
  (QA) `defect-pattern-log.md`, `architecture-review-log.md`,
  `rejected-approaches-log.md`, `technical-debt-register.md`. **No other files.**
- **Stop condition:** All accessible sources captured + verified; blocked sources
  (R2/R5 if still gated, R4 gated children) documented without bypass; the nine
  research deliverables + source/screenshot evidence written with every claim
  cited and classified; QA logs and handoff updated; quality gate satisfied. Then
  **stop** — no MVP scope, no architecture decisions, no code, no merge.
- **Verification method:** Two-pass — topic capture, then an independent
  verification agent (and worker spot-checks) re-reading the canonical source for
  the highest-stakes claims; any figure/feature not literally supported on the
  page is downgraded to **open question / vendor claim**, never asserted as fact
  (reuses the DP-001 verification-pass gate).
- **How unsupported claims will be prevented:** Strict claim classification on
  every line (Fact / Competitor claim / Inference / Open question — `CLAUDE.md`
  §8); vendor capability statements stay **competitor claims** unless a concrete
  documented workflow/screenshot demonstrates them (then **visible demonstrated
  workflow**); blocked/unknown is stated as such; no hidden-feature guessing; no
  competitor claim is promoted to a Tier-1 fact (those come only from the existing
  official baselines).

---

# Research Sprint B Handoff

> **Research Sprint B — Dedicated Branch Setup + Source Access Validation +
> Official Shopify/Odoo Baseline.** Research-only; no-code gate in force
> (`CLAUDE.md` §5). Maps to backlog items **RB-01.1** (source validation),
> **RB-05.1** (official Shopify notes), **RB-06.1** (official Odoo notes), and
> **seeds RB-14** architecture questions.

## Session summary

Established the **dedicated project integration branch** (corrected by ChatGPT to
**`Shopify-connector`** — see Base branch below), then produced a controlled
**Tier-1 research baseline**: re-validated access for the 8 competitor resources;
created the **official Shopify API** and **official Odoo 19 architecture** notes
(every factual claim cited to an exact official URL, accessed 2026-06-30, with
**Fact / Inference / Open question** labels and a clear "constraints are
inferences, not decisions" boundary); captured supporting excerpts under
`docs/00-source-materials/`; and seeded **seven evidence-pending architecture
questions** (AR-002…AR-008, all "Not decided"). **No connector code, no Odoo
module, no competitor deep dives, no MVP scope, and no architecture decisions**
were produced — all gated. Facts were gathered topic-by-topic and then
**independently verified** on the highest-stakes pages (rate limits, versioning,
webhooks, Odoo security/manifest).

## Branch and commits

**Working branch:** `research/sprint-b-source-access-official-baseline` (based on
`Shopify-connector` @ `a5d4543`, the merged PR #49 governance foundation).

| Hash | Message |
| --- | --- |
| `54bd6f1` | docs: sprint b governance checkpoint and branch setup |
| `d05ab49` | docs: validate initial source access |
| `468efb6` | docs: add official shopify api baseline |
| `08b4c75` | docs: add official odoo architecture baseline |
| `21c460b` | docs: seed architecture research questions |
| _(this commit)_ | docs: finalize research sprint b handoff |

## Base branch and PR target

- **Dedicated project integration branch: `Shopify-connector`.** The original
  Sprint B prompt named `dev/Shopify-connector`; that branch **cannot exist on
  the remote** because a plain `dev` branch already exists (Git directory/file
  ref conflict — the push was rejected with `directory file conflict`). The
  blocker was reported, **not** worked around. **ChatGPT corrected the policy** to
  use the existing **`Shopify-connector`** branch; plain `dev` was left untouched.
- Before acting, verified `origin/Shopify-connector` was at the old `68007a9`,
  had **no** unique commits beyond `origin/main`, and was a clean fast-forward; it
  was **fast-forwarded to `origin/main` `a5d4543` and pushed normally (no force)**.
- **PR target: `Shopify-connector`** — **not** `main`, **not** plain `dev`, **not**
  `dev/Shopify-connector`. **`main` was not modified; plain `dev` was not modified.**

## Files created or updated

- `docs/00-source-materials/source-access-notes.md` (new) — per-resource access
  evidence for the 8 sources.
- `docs/01-research/resource-inventory.md` (updated) — Sprint B re-validation
  section + unblock decisions for ChatGPT.
- `docs/01-research/shopify-official-api-notes.md` (new) — Tier-1 Shopify baseline.
- `docs/00-source-materials/shopify-official.md` (new) — captured Shopify excerpts.
- `docs/01-research/odoo-official-architecture-notes.md` (new) — Tier-1 Odoo 19
  baseline.
- `docs/00-source-materials/odoo-official.md` (new) — captured Odoo excerpts.
- `docs/05-qa/architecture-review-log.md` (updated) — seeded AR-002…AR-008
  (evidence-pending only).
- `docs/05-qa/defect-pattern-log.md` (updated) — DP-001 (prevented stale-figure
  issue) + occurrence counter.
- `docs/01-research/research-handoff.md` (this file).

## Source access results

No status changed from Sprint A (both checked 2026-06-30; no auth bypassed).
**Accessible (5):** R1 Webkul, R3 Emipro, R6 ecommerce_shopify, R7 VentorTech
site, R8 sh_shopify_connector. **Partial (1):** R4 VentorTech Confluence
(anonymous-access banner; child pages to test individually). **Blocked (2):** R2
Teqstars 19.0 (HTTP 403 bot-block — needs an alternate fetch UA, or a ChatGPT
decision on the non-equivalent 16.0 mirror), R5 Google Doc (login wall — needs
owner-granted access or export). Full evidence:
`docs/00-source-materials/source-access-notes.md`.

## Shopify official facts captured

GraphQL Admin API is the primary API (REST legacy since 2024-10-01; new public
apps GraphQL-only from 2025-04-01); quarterly date-based versioning (`YYYY-MM`,
min 12-month support, ≥9-month overlap, fall-forward); OAuth + token-exchange,
online/offline/session tokens, least-privilege scopes, protected customer data
(60-day order window / `read_all_orders` approval); rate limits (REST 40/2
standard, 400/20 Plus; GraphQL calculated-cost restore 100/200/1000/2000 pts/s,
1000-point single-query cap) and the query-cost model; bulk operations (async
JSONL, concurrency change at 2026-01); webhooks (HMAC-SHA256 on raw body,
**8 retries/4h**, auto-delete after 8 failures, **delivery not guaranteed →
reconciliation required**, mandatory compliance webhooks); products/variants
(2048-variant model, `productSet` delete-on-omit); inventory (variant→item→level→
location, `committed` read-only, `@idempotent` from 2026-04); orders; fulfillment
(FulfillmentOrder-based, legacy unsupported since 2022-07); refunds/returns;
transactions (gateway-agnostic) vs payouts (Shopify Payments only); App Store /
Built-for-Shopify readiness. Full notes + citations:
`docs/01-research/shopify-official-api-notes.md`.

## Odoo official facts captured

Module/manifest structure (`name` only required key; full key list); modularity
via `depends` + `auto_install` link modules; ORM extension (in-place `_inherit`
preferred; `_inherits` delegation discouraged; `@api.model_create_multi`,
`@api.ondelete`, always `super()`); security (`ir.model.access.csv` deny-by-
default, `ir.rule` global=intersect/group=unify, field `groups`, `sudo()`/
superuser bypass); **`ir.cron` is the only documented background primitive**
(poll-based, `--max-cron-threads` default 2; failure rules 3-consecutive /
5-over-7-days→deactivate); **no official built-in job queue — `queue_job` is
community (Open question)**; external IDs / `ir.model.data` (binding-key
inference); performance (prefetch, N+1 → `_read_group`, batch `create`, selective
indexes); testing (`TransactionCase`, `HttpCase`/tours, tags); upgrade scripts
(`migrations/$version/{pre,post,end}`); logging (`ir.logging`/CLI, **no built-in
metrics — Open question**); Odoo.sh deployment (worker/time/memory limits;
**crons disabled on staging/dev**). Full notes + citations:
`docs/01-research/odoo-official-architecture-notes.md`.

## Inferences and constraints, not decisions

The "Architecture constraints implied by …" sections in both baselines are
**inferences only**, and AR-002…AR-008 are **evidence-pending, not decided**.
Key framing (not choices): a new public-app connector effectively needs GraphQL;
webhooks cannot be the sole source of truth (need reconciliation + idempotency);
background sync on stock Odoo is `ir.cron`-bound (queue_job is an explicit
dependency question); modular addon family over a giant module; external IDs as a
candidate binding key; inventory `committed` is order-driven; fulfillment must use
FulfillmentOrder mutations. **None of these is a decision.**

## Open questions

Carried into the baselines and AR rows: REST sunset / GraphQL-only scope for
custom apps; per-plan GraphQL bucket size & throttle error shape; connection-cost
formula; current max product options; REST product/fulfillment deprecation dates;
payout scope string; Pub/Sub & EventBridge retry semantics. Odoo: whether any
official job queue exists beyond `ir.cron`; `ir.cron`/`ir.model.data`/`ir.logging`
field schemas; manifest defaults; `create`-override signature; `read_group`
deprecation; Odoo.sh per-stage quotas; built-in metrics. **Source unblocks for
ChatGPT:** R2 Teqstars (alternate fetch vs 16.0 mirror) and R5 Google Doc (owner
access/export).

## Risks

Commonly-cited API numbers can be stale (see DP-001); version-independent Shopify
policy can drift without a version bump; `productSet` delete-on-omit is a
data-loss footgun; webhook-only designs risk silent drift; treating `ir.cron` as
a job queue (or assuming `queue_job` is core) is a design trap; some JS-rendered
Odoo pages required RST-source recovery (re-verify load-bearing wording).

## Learning feedback loop

- **New issues discovered:** one — **DP-001** (incorrect Shopify API assumption,
  #6): commonly-cited/training-data API figures were **stale vs current official
  docs** (webhook "19/48h" → actual 8/4h; REST Plus "80" → 400; `/rate-limits`
  moved to `/limits`, now GraphQL-only). **Prevented** by the independent
  verification pass.
- **Repeated issue patterns:** none at threshold — DP-001 is the **1st**
  occurrence of category #6 (counter updated; no 2×/3× escalation).
- **Rules/checklists updated:** added the DP-001 **prevention rule** — for
  high-stakes numeric/policy API facts, re-read and cite the **exact** official
  page; if a figure is not literally on the page, mark it **Open question**, never
  assert a remembered/forum figure. The **independent-verification-pass** gate is
  now the recommended method for future official-API research (RB-05/RB-06-style).
- **New rejected approaches:** none (research-only; no approaches evaluated to
  rejection — `rejected-approaches-log.md` unchanged).
- **New technical debt:** none (no code; blocked sources R2/R5 are research gaps,
  not debt — `technical-debt-register.md` unchanged).
- **Architecture concerns:** captured as **AR-002…AR-008 (evidence-pending)**, not
  decisions; the big ones are sync orchestration (cron vs webhook+reconciliation
  vs queue) and duplicate-prevention/binding.
- **Tests or review gates needed:** none active (research phase). For future API
  research, keep the verification-pass gate. The connector-side test stance
  (`TransactionCase` for mapping, `HttpCase`/tours for webhooks/UI) is recorded in
  the Odoo notes for the implementation phase.
- **Should future prompts change? Yes** — official-API research prompts should
  explicitly require an **independent verification pass** on high-stakes numeric
  facts and the "mark Open question if not literally on the page" rule (now
  encoded via DP-001). Also: the branch-policy reality is **`Shopify-connector`**
  (not `dev/Shopify-connector`), which future Sprint prompts should state.

**Revision patch (ChatGPT REVISE — branch policy + high-power research rules):**

- Branch policy was promoted into permanent governance files: `Shopify-connector`
  is the dedicated integration branch; `main` and plain `dev` remain untouched
  unless explicitly approved.
- New issue discovered: high-power research fan-out needs a persistent governance
  rule so large Claude workflows remain intentional, scoped, synthesized, and
  reviewable.
- Category: token waste (#17) / unclear handoff, first occurrence (logged as
  **DP-002**, Mitigated).
- Prevention rule: high-power research mode is allowed and encouraged for major
  research and architecture work, but the fan-out plan, workstreams, sources,
  stop condition, synthesis method, and verification method must be documented.
- **This rule does not limit Claude's capabilities.** It is a *capability,
  not a cap* — there is **no** fixed agent/token limit. Claude is expected to use
  maximum capability when justified to produce a top-tier, state-of-the-art
  connector; the only requirement is that large research be intentional, scoped
  to allowed files, documented, and reviewable (and that small patch sessions
  stay lightweight).
- Rules/checklists updated in this patch: `CLAUDE.md` (new **Branch governance**
  and **High-power research mode** sections), `README.md` (branch-governance +
  high-power research summary), `docs/06-prompts/claude-learning-rules.md`
  (pre-session checklist item 8 + High-power research mode section),
  `docs/06-prompts/claude-session-prompts.md` (default branch policy + High-power
  research mode in the standard preamble and as a section),
  `docs/05-qa/pr-review-checklist.md` (branch-target + capability-use checks),
  `docs/05-qa/defect-pattern-log.md` (DP-002 reframed + counter), and this
  handoff.

## What ChatGPT should review

1. **Branch governance** — confirm `Shopify-connector` is the intended dedicated
   integration branch and that leaving plain `dev` untouched is correct.
2. **Citation/classification rigor** — spot-check that Shopify/Odoo facts cite
   exact official URLs and that constraints are labelled inference, not decision.
3. **High-stakes facts** — the rate-limit, versioning, and webhook numbers
   (incl. the corrected 8-retries/4-hours and REST-Plus-400), and the Odoo
   "no official job queue" finding.
4. **Open questions / unblocks** — decide R2 (Teqstars alternate fetch vs 16.0
   mirror) and R5 (Google Doc access/export).
5. **AR-002…AR-008** — confirm these are the right architecture questions to
   carry (still evidence-pending), and which to prioritise for RB-14.
6. **DP-001 + verification gate** — endorse making the independent-verification
   pass a standing rule for API research.

## Recommended next session

With Tier-1 baselines in place, proceed to **competitor deep dives**
(`RB-02.1 Webkul`, `RB-02.3 Emipro`, `RB-02.5 Odoo Apps listings` — all
unblocked), running **RB-12 feature taxonomy** early for grounding, and revisit
**R2/R5** once ChatGPT decides the unblock path. Keep the no-code gate; one scoped
session per deep dive; follow `research-methodology.md` §11.

## Stop confirmation

Stopped at the Sprint B boundary as instructed: working branch pushed, **one
draft PR** opened targeting **`Shopify-connector`**, **not merged**. **No** code,
**no** Odoo module, **no** competitor deep dives, **no** MVP scope, **no**
architecture decisions. `main` and plain `dev` untouched. Awaiting ChatGPT review.

---

# Research Sprint A Handoff (history)

> Continuity record for **Research Sprint A — Governance, Research Workspace,
> Source Inventory, and Research Backlog.** Continuity lives in GitHub, not chat.
> The running **Sprint checkpoint log** (one note per stage) is at the bottom.

## ChatGPT review decision (Research Sprint A)

> ChatGPT review decision: Research Sprint A is the canonical governance
> foundation after this revision patch is accepted. The earlier branch
> `claude/odoo-shopify-research-setup-fs4wzi` is non-canonical and must not be
> used unless ChatGPT explicitly reopens it.

The Sprint A review returned **REVISE — small governance patch required before
merge.** This patch addresses those findings (modular addon-family wording,
canonical research output filenames, feature-taxonomy sequencing, the
non-canonical-branch warning, and this learning-loop update). See the
revision-patch entry at the bottom of the checkpoint log and the updated
**Learning feedback loop** section below.

## Session summary

Research Sprint A established the GitHub-based **governance and research
foundation** for the premium Odoo 19 ↔ Shopify Connector project, so ChatGPT
can review the repo directly and direct the next sprint. Work was done in six
documentation-only stages on a clean branch off `main`: workspace setup →
governance contract & templates → learning feedback loop → research workspace
(inventory, methodology, backlog) → placeholder READMEs → finalization. **No
connector code, no Odoo module, and no forbidden files were created.** No
competitor deep dives, MVP finalization, or architecture decisions were made —
those are explicitly out of scope and gated.

## Branch and commits

**Branch:** `docs/research-sprint-a-governance-inventory` (based on `origin/main`
@ `68007a9`).

| Hash | Message |
| --- | --- |
| `2e4c276` | docs: create connector governance workspace |
| `d143086` | docs: add governance and review templates |
| `1aba406` | docs: add quality feedback loop |
| `f4f3e7d` | docs: add research inventory and backlog |
| `8aa536b` | docs: add product architecture and claude placeholders |
| _(final)_ | docs: finalize research sprint a handoff |

## Files created or updated

**Root governance**
- `CLAUDE.md` (new) — governance contract (roles, source-of-truth,
  research-first, no-code-until-approved, scoped sessions, citation rules, claim
  classification, future implementation-task requirements, allowed/forbidden
  files, do-not-repeat-rejected rule, mandatory handoff).
- `AGENTS.md` (new) — six **proposed** future agents, marked proposed only.
- `README.md` (updated) — preserved existing content; added the project
  workspace map.

**Research (`docs/01-research/`)**
- `resource-inventory.md`, `research-methodology.md`, `research-backlog.md`,
  `research-handoff.md` (this file).

**QA / quality memory (`docs/05-qa/`)**
- `quality-feedback-loop.md`, `defect-pattern-log.md`,
  `architecture-review-log.md`, `rejected-approaches-log.md`,
  `technical-debt-register.md`, `pr-review-checklist.md`.

**Prompts/templates (`docs/06-prompts/`)**
- `claude-session-prompts.md`, `claude-learning-rules.md`,
  `implementation-task-template.md`, `pr-review-template.md`,
  `session-handoff-template.md`.

**Decisions** — `docs/04-decisions/decision-record-template.md` + `README.md`.

**Placeholder READMEs** — `docs/00-source-materials/README.md`,
`docs/02-product`, `docs/03-architecture`, `docs/07-implementation-plan`,
`docs/08-release-readiness`, and `.claude`, `.claude/skills`, `.claude/agents`.

## What changed

The repository went from a bare Odoo SH scaffold (`addons/adams_base`,
`README.md`, `.gitignore`) to a full **research/governance workspace**: a
governance contract, a learning feedback loop with four logs, a research
methodology, a registered source inventory of 8 resources, a 14-section research
backlog, and review/handoff/decision templates — all documentation. The Odoo
addon scaffold under `/addons` was left untouched.

## Evidence and citations added

Initial **access status** for the 8 sources was verified on **2026-06-30** (no
auth bypass): **Accessible** — Webkul (R1), Emipro (R3), Odoo Apps
ecommerce_shopify (R6), VentorTech website (R7), Odoo Apps sh_shopify_connector
(R8); **Partial** — VentorTech Confluence (R4, anonymous-access banner);
**Blocked** — Teqstars docs (R2, HTTP 403 bot-block, not a login wall), project
Google Doc (R5, login wall). On-page pricing recorded as facts-on-date: R6
$195.56 (OPL-1), R8 $168.81 (OPL-1), R7 EUR 499. No detailed feature claims were
asserted — only registration/triage. Full detail in `resource-inventory.md`.

## Assumptions

- The connector must be **isolated from `adams_base`/customer code**; its final
  structure may be a **modular connector addon family** under `/addons` — exact
  module boundaries are **not final** and will be validated through research +
  architecture review. `adams_base` is unrelated company/base code (inference
  from repo layout + README).
- "Initial value" / "Evidence strength" in the inventory are **triage
  inferences**, not vendor facts.
- The default research order in the backlog is reasonable but adjustable once
  blocked sources are resolved.

## Open questions

- R2 Teqstars: will an alternate fetch (different UA / browser / cache) work, or
  is the 16.0 doc the fallback?
- R5 Google Doc: can the owner grant view access or provide an export? What is
  its actual content?
- R6 ecommerce_shopify: is the listing Odoo S.A. official or a partner module
  (author shown as "Odoo IN Pvt Ltd")?
- R4 VentorTech Confluence: which child pages/screenshots require login?

## Risks

- **Access risk:** two blocked + one partial source could delay specific deep
  dives (RB-02.2, RB-02.6); the backlog isolates these so they don't stall the
  rest.
- **Source bias:** all 8 sources are vendor-published; technical facts must come
  from official Shopify/Odoo docs (RB-05, RB-06), not competitor claims.
- **Scope creep risk:** strong guardrails (allowed/forbidden files, no-code
  gate) are in place; future sessions must honour them.
- **Pricing/feature drift:** vendor pages change; deep dives must re-date and
  capture excerpts.

## Learning feedback loop

- **New issue discovered:** Governance wording could **bias Claude toward one
  giant connector addon/module** — the "self-contained addon" phrasing in
  `CLAUDE.md` §9 and `README.md`. Surfaced by ChatGPT's Sprint A review (REVISE).
- **Category:** premature architecture / weak modularity (first occurrence;
  count = 1).
- **Repeated issue patterns:** None — this is the first occurrence of this
  category; no escalation threshold reached.
- **Prevention rule:** Use **"modular connector addon family"** language and
  state that exact module boundaries are **not final** until validated through
  research + architecture review; never imply a single giant module. Keep the
  isolation-from-`adams_base`/customer-code rule.
- **Rules/checklists updated:** (1) `CLAUDE.md` §9 and `README.md` reworded to
  the modular-family principle; (2) `research-backlog.md` and
  `claude-session-prompts.md` updated to the canonical research output filenames,
  single-file competitor deep dives (`competitor-deep-dives.md`), and the
  provisional→canonical feature-taxonomy sequencing rule; (3)
  `architecture-review-log.md` row **AR-001** added recording this branch as the
  canonical foundation. (No `defect-pattern-log.md` row: this was a pre-merge
  review finding on governance docs, not a shipped defect — captured here and in
  the architecture-review log.)
- **New rejected approaches:** None logged formally; the "one giant connector
  module" bias is prevented by wording. Revisit/log if it recurs.
- **New technical debt:** None.
- **Architecture concerns:** Module-boundary design is explicitly **deferred**
  to research + architecture review (RB-06, RB-14); do not pre-decide it.
- **Tests or review gates needed:** None active in the research phase; the
  implementation checklist (section C) is staged for later.
- **Should future prompts change? Yes/No:** **Yes** — prompt templates now use
  the canonical research output filenames and the modular-family wording, and
  encode the provisional→canonical taxonomy sequencing.
- **Final cleanup:** removed remaining "self-contained addon" wording from
  implementation-phase governance templates so future implementation prompts
  preserve modular addon-family language. Files updated:
  `docs/05-qa/pr-review-checklist.md` (§C) and
  `docs/06-prompts/implementation-task-template.md`.

## What ChatGPT should review

1. **Governance correctness** — does `CLAUDE.md` capture the intended
   Claude/ChatGPT operating model, gates, and claim-classification scheme?
2. **Learning loop sufficiency** — are the escalation thresholds (2×/3×), issue
   taxonomy, and log schemas adequate to prevent repeated mistakes?
3. **Research methodology** — is the source hierarchy, claim classification, and
   extraction method rigorous enough for trustworthy deep dives?
4. **Resource inventory** — accuracy of access triage; is the
   official-vs-partner provenance flag for R6 handled correctly?
5. **Research backlog** — are sequencing, dependencies, and acceptance criteria
   right? Anything missing before deep dives start?
6. **Proposed agents** — approve/adjust the six proposed agents (still inactive).
7. **Blocked sources** — decide the unblock path for R2 (Teqstars) and R5
   (Google Doc) before their backlog items.

## Recommended next session

**RB-01.1 — Validate and unblock sources** (resolve R2/R5 access), then begin
deep dives with **RB-02.1 — Webkul** (accessible, no blockers). Run
`RB-12` (feature taxonomy) early and `RB-05`/`RB-06` (official Shopify/Odoo
notes) in parallel. Use the prompts in `docs/06-prompts/claude-session-prompts.md`.

## Stop confirmation

Stopped at the Research Sprint A boundary as instructed: branch pushed, one
**draft** PR opened for ChatGPT review, not merged. **No** deep competitor
research, **no** architecture, **no** implementation was started. Awaiting
ChatGPT review.

## Sprint self-review

- **Scope respected:** Yes — governance/research documentation only.
- **No coding performed:** Yes — no `.py`/`.xml`/`.csv`, no module, no manifest.
- **Forbidden files untouched:** Yes — forbidden-pattern scan clean; `addons/`
  untouched (verified via `git diff --name-only origin/main`).
- **Research inventory complete:** Yes — all 8 resources registered with the
  required schema and verified access status.
- **Governance files complete:** Yes — CLAUDE.md, AGENTS.md, README, templates,
  checklist.
- **Learning loop complete:** Yes — feedback-loop doc + four logs + learning
  rules.
- **Handoff updated:** Yes — this file (all required sections + checkpoint log).
- **Ready for ChatGPT review:** Yes — draft PR opened.

---

## Sprint checkpoint log

> One short note per stage (most recent last).

- **Stage 1 — Repo inspection & safe setup (2026-06-30):** Confirmed remote
  default branch is `main` at `68007a9` (clean Odoo scaffold:
  `addons/adams_base`, `README.md`, `.gitignore`; no `docs/`, no `CLAUDE.md`).
  Created the clean branch `docs/research-sprint-a-governance-inventory` from
  `origin/main` (deliberately not from the prior research branch, so this PR
  contains exactly this governance foundation). Created the `/docs/00..08` and
  `/.claude/{skills,agents}` directory structure. No code touched. Next: Stage 2
  governance files.
- **Stage 2 — Governance files (2026-06-30):** Created `CLAUDE.md` (roles:
  Claude=execution/research/docs worker, ChatGPT=strategy/control-room/reviewer;
  GitHub source-of-truth; research-first; no-code-until-approved; small scoped
  sessions; mandatory handoff; citation rules; the fact/competitor-claim/
  inference/recommendation/decision/open-question classification; future
  implementation-task requirements incl. allowed/forbidden files, acceptance
  criteria, tests, rollback, definition of done; and the hard do-not-repeat-
  rejected-approaches rule). Created `AGENTS.md` listing six **proposed** agents
  (competitor-research, shopify-api-research, odoo-architecture-research,
  ux-benchmark, qa-review, prompt-control) — none active. Updated `README.md`
  (preserved existing title/description; added the project workspace map).
  Added `decision-record-template.md`, `pr-review-checklist.md`,
  `implementation-task-template.md`, `pr-review-template.md`, and
  `session-handoff-template.md`. Docs only; no forbidden files. Next: Stage 3
  learning feedback loop.
- **Stage 3 — Learning feedback loop (2026-06-30):** Created
  `quality-feedback-loop.md` (review-decision categories; 17-type issue
  taxonomy; 2×→update-rule / 3×→pause-implementation escalation; concrete-lesson
  rule; end-of-session review; quality + acceptance gates; routing table) and
  the four logs with the exact required columns — `defect-pattern-log.md`,
  `architecture-review-log.md`, `rejected-approaches-log.md`,
  `technical-debt-register.md` (all initialized empty with instructions). Created
  `claude-learning-rules.md` with the mandatory 7-item pre-session checklist
  (previous handoff, defect log, rejected log, architecture-review log, decision
  records, current phase, allowed/forbidden files). Next: Stage 4 research
  workspace + source inventory.
- **Stage 4 — Research workspace + source inventory (2026-06-30):** Created
  `00-source-materials/README.md` (capture rules; empty until deep dives).
  Created `resource-inventory.md` registering all 8 sources with the required
  schema (ID, name, URL, source type, competitor/category, initial value,
  evidence strength, current access status, what-to-extract-later, open
  questions, notes); access verified 2026-06-30 (5 Accessible, 1 Partial — R4
  VentorTech, 2 Blocked — R2 Teqstars 403/bot-block & R5 Google Doc login);
  Google Doc marked private/user-provided/access-dependent; no detailed feature
  claims asserted. Created `research-methodology.md` (source hierarchy; citation;
  competitor-evidence; claim-classification; screenshot/pricing/feature/UX/
  reliability/technical-risk extraction; deep-dive procedure; MVP/Phase2/Advanced/
  Optional/Avoid disposition rules). Created `research-backlog.md` (14 sections,
  RB-01..RB-14, each item with Objective/Inputs/Output file/Acceptance criteria/
  Dependencies/Status + sequencing). Next: Stage 5 placeholder READMEs.
- **Stage 5 — Placeholder READMEs (2026-06-30):** Created concise READMEs for
  `docs/02-product`, `docs/03-architecture`, `docs/04-decisions`,
  `docs/07-implementation-plan`, `docs/08-release-readiness`, and `.claude`,
  `.claude/skills`, `.claude/agents` — each stating purpose, what belongs, what
  does not belong yet, and current status. The `.claude/skills` and
  `.claude/agents` READMEs explicitly recommend **deferring** active skills/
  agents until the research workflow stabilizes (premature automation may encode
  weak assumptions). Next: Stage 6 final self-review, handoff, push, draft PR.
- **Stage 6 — Final self-review, handoff, push, draft PR (2026-06-30):** Added
  `claude-session-prompts.md` to complete the prompt library (whitelisted file;
  goal #7). Ran final checks: `git diff --name-only origin/main` shows only
  allowed docs/governance files; forbidden-pattern scan clean; `addons/`
  untouched. Filled all required handoff sections + the sprint self-review.
  Pushed the branch and opened one **draft** PR for ChatGPT review. Stopped.
- **Revision patch — address Sprint A review findings (2026-06-30):** ChatGPT
  returned **REVISE**. Applied a small governance patch to the same branch /
  PR #49 (no new PR, no merge): (1) replaced "self-contained addon" wording in
  `CLAUDE.md` §9 and `README.md` with the **modular connector addon family**
  principle (kept the isolation rule); (2) aligned future research output
  filenames in `research-backlog.md` and `claude-session-prompts.md` to the
  canonical names and consolidated competitor deep dives into one file
  `competitor-deep-dives.md` with per-competitor sections; (3) added the
  **provisional→canonical** feature-taxonomy sequencing rule (first 1–2 deep
  dives may use provisional groups; RB-12 normalizes); (4) added the
  non-canonical-branch warning + AR-001 in `architecture-review-log.md`; (5)
  updated this Learning feedback loop. Allowed files only; no code touched.
  **Deferred follow-up:** `docs/05-qa/pr-review-checklist.md` (§C) and
  `docs/06-prompts/implementation-task-template.md` still contain the phrase
  "self-contained addon"; both are **outside this patch's allowed-files scope**,
  so the reword to "modular connector addon family" is deferred to a future
  ChatGPT-approved patch rather than edited out of scope here. **(Resolved in the
  final cleanup patch — both files reworded.)**

### Research Sprint B checkpoints

- **Sprint B / Stage 0 — Dedicated branch setup + governance correction
  (2026-06-30):** Started Research Sprint B (research-only; no-code gate
  confirmed via `CLAUDE.md` §5; allowed/forbidden files reconfirmed). The
  original Sprint B prompt named `dev/Shopify-connector` as the dedicated project
  integration branch. **Blocker (fact):** that branch cannot be created on the
  remote — a plain `dev` branch already exists, and Git cannot hold both `dev`
  and `dev/Shopify-connector` (a directory/file ref conflict; the push was
  rejected with `directory file conflict`). The blocker was reported, not
  worked around (no `dev` deletion, no force-push). **ChatGPT branch-policy
  correction (decision, by ChatGPT):** use the existing remote branch
  **`Shopify-connector`** as the dedicated project integration branch; leave
  plain `dev` untouched; do not use `dev/Shopify-connector` or
  `dev-Shopify-connector`. Sprint branches now branch from `Shopify-connector`
  and Sprint PRs target `Shopify-connector` (not `main`, not `dev`). Verified
  before acting: `origin/Shopify-connector` was at the old commit `68007a9`, had
  **no** unique commits beyond `origin/main` (empty `main..Shopify-connector`),
  and `68007a9` is a direct ancestor of `origin/main` (clean fast-forward). Then
  fast-forwarded `Shopify-connector` to `origin/main` `a5d4543` (the merged PR
  #49 Sprint A governance foundation) and pushed normally (`68007a9..a5d4543`,
  no force). All seven governance-foundation files are present on the branch.
- **Sprint B / Stage 1 — Pre-session governance check (2026-06-30):** Read
  `CLAUDE.md`, this handoff, `claude-learning-rules.md`, `quality-feedback-loop.md`,
  `research-methodology.md`, `resource-inventory.md`, `research-backlog.md`.
  Confirmed: current phase is **research only**; the no-code gate applies; the
  Sprint B allowed/forbidden file lists are understood; `Shopify-connector` is
  the dedicated integration branch; the Sprint B working branch
  `research/sprint-b-source-access-official-baseline` is based on
  `Shopify-connector`; the Sprint B PR will target `Shopify-connector`; the old
  branch `claude/odoo-shopify-research-setup-fs4wzi` remains non-canonical.
  Sprint B maps to backlog items RB-01.1 (source validation), RB-05.1 (official
  Shopify notes), RB-06.1 (official Odoo notes), and seeds RB-14 architecture
  questions. Added this checkpoint note. Next: Stage 2 source validation.
- **Sprint B / Stage 2 — Source access validation (2026-06-30):** Re-ran a normal
  anonymous access check on all 8 resources (no auth bypass). No status changed
  from Sprint A: 5 Accessible, 1 Partial (R4), 2 Blocked (R2 403 bot-block, R5
  login wall). Created `docs/00-source-materials/source-access-notes.md`
  (per-resource: date, URL, result, visible sections, block reason, unblock
  action, extraction path, deep-dive readiness) and added a Sprint B
  re-validation section + ChatGPT unblock decisions to `resource-inventory.md`.
  Commit `d05ab49`. Next: Stage 3 Shopify baseline.
- **Sprint B / Stage 3 — Official Shopify API baseline (2026-06-30):** Created
  `docs/01-research/shopify-official-api-notes.md` (all required sections; every
  fact cited to an exact shopify.dev URL + access date; Fact/Inference/Open
  question labelled; "Architecture constraints implied" marked inference, no
  decisions) and `docs/00-source-materials/shopify-official.md` (captured
  quotes/paraphrases). Reconciled the verification pass: REST limits cited to the
  REST-specific page (40/2 std, 400/20 Plus), general `/usage/limits` is now
  GraphQL-only; webhook retry corrected to 8/4h. Commit `468efb6`. Next: Stage 4
  Odoo baseline.
- **Sprint B / Stage 4 — Official Odoo 19 baseline (2026-06-30):** Created
  `docs/01-research/odoo-official-architecture-notes.md` (all required sections;
  every fact cited to an exact odoo.com/19.0 URL; queue/async marked Open question
  — only `ir.cron` is official, `queue_job` is community; constraints marked
  inference, no decisions) and `docs/00-source-materials/odoo-official.md`. Commit
  `08b4c75`. Next: Stage 5 architecture seeds.
- **Sprint B / Stage 5 — Architecture review seeds (2026-06-30):** Added
  AR-002…AR-008 to `architecture-review-log.md` (API strategy, sync orchestration,
  module boundaries, mapping/dedup, error handling/retries, inventory,
  fulfillment) — all Review decision "Not decided", Status "Evidence pending",
  with evidence-required/risks/follow-up; updated the log's explanatory note.
  Commit `21c460b`. Next: Stage 6 handoff + learning loop.
- **Sprint B / Stage 6 — Handoff + quality loop (2026-06-30):** Wrote the full
  Sprint B handoff (above) with the learning feedback loop; logged **DP-001**
  (prevented stale-figure issue, category #6, Mitigated) and updated the
  occurrence counter in `defect-pattern-log.md`; `rejected-approaches-log.md` and
  `technical-debt-register.md` left unchanged (none warranted). Ran the
  end-of-session quality gate (all items satisfied). Next: push branch, open one
  draft PR targeting `Shopify-connector`, then stop.

### Research Sprint C checkpoints

- **Sprint C / Stage 1 — Setup + high-power plan (2026-06-30):** Started Research
  Sprint C (research-only; no-code gate confirmed via `CLAUDE.md` §5; high-power
  mode **explicitly authorized** in the prompt). Fetched remote branches and
  verified preconditions: **PR #50 is merged into `Shopify-connector`** (the
  branch tip `d6fbcdb` *is* the PR #50 merge commit), the working branch is based
  on `Shopify-connector` (identical to it at start), and all seven required files
  are present. **Branch-name note (flagged for ChatGPT):** the harness designated
  the working branch **`claude/research-sprint-c-competitors-hgoo8t`** (already
  checked out, based on `Shopify-connector`), whereas the Sprint C prompt body
  named `research/sprint-c-competitor-deep-dives-ux-evidence`; per the
  session's hard git rule ("never push to a different branch without explicit
  permission") the work proceeds on the harness-designated branch and the **PR
  still targets `Shopify-connector`** — `main`/`dev` untouched. Read the required
  governance/research files (CLAUDE.md, this handoff, learning rules, methodology,
  resource inventory, backlog, both official baselines, all QA logs). Wrote the
  **Sprint C high-power research plan** (above) and committed it. Next: Stage 2
  source + screenshot evidence capture (controlled parallel fan-out).
- **Sprint C / Stage 2 — Source + screenshot evidence (2026-06-30):** Ran the
  documented capture→verify fan-out (16 agents, 137 tool calls) over R1–R8;
  verified each source adversarially. Wrote `competitor-source-notes.md`,
  `competitor-screenshot-inventory.md`, and the `screenshots/` READMEs (root +
  webkul/teqstars/emipro/ventortech/odoo-apps); updated `resource-inventory.md`
  with Sprint C access changes (**R2 docs still 403-blocked but Teqstars Apps
  listing accessible; R5 = R6's setup guide; pricing resolved**). No binaries saved
  (proxy returns markdown/alt-text; sprint rule allows the fallback). No auth
  bypassed. Commit `e1c5ec4`. Next: Stage 3 deep dives.
- **Sprint C / Stage 3 — Competitor deep dives (2026-06-30):** Wrote
  `competitor-deep-dives.md` — six competitors (Webkul, Teqstars, Emipro,
  VentorTech, ecommerce_shopify, sh_shopify_connector) + a blocked-source record
  for the Google Doc; each with feature classification, workflow reconstruction,
  UX, reliability, maintenance, strengths/weaknesses, learn/do-better/avoid, open
  questions; verifier downgrades reflected (R2→Blocked, EC→cron, SH multi-company→
  not-found). Commit `1e027a0`. Next: Stage 4 matrix + UX benchmark.
- **Sprint C / Stage 4 — Matrix + UX benchmark (2026-06-30):** Wrote
  `competitor-feature-matrix.md` (grouped tables, per-cell ✅/🟨/⬜/🚫/🔒 symbols +
  evidence notes + implications) and `ux-ui-benchmark.md` (evidence base, per-area
  comparisons, best patterns, gaps, principles — benchmark only, no UI designed).
  Commit `da93ba9`. Next: Stage 5 synthesis.
- **Sprint C / Stage 5 — Patterns/best-in-class/gaps/avoid (2026-06-30):** Wrote
  `common-patterns.md`, `best-in-class-observations.md`, `gaps-opportunities.md`
  (candidate/later/unknown MVP relevance — not finalized), `avoid-list.md` (each
  item with evidence/risk/prevention/arch-review flag). Updated QA logs:
  **DP-003** + counter (`defect-pattern-log.md`); a non-decision competitor-
  evidence note (`architecture-review-log.md`); avoid-list-is-not-rejection note
  (`rejected-approaches-log.md`); Sprint C no-debt note
  (`technical-debt-register.md`). Commit `890ce0b`. Next: Stage 6 handoff + PR.
- **Sprint C / Stage 6 — Handoff + quality loop (2026-06-30):** Wrote the full
  Sprint C handoff (above) with the learning feedback loop (DP-003; external
  DP-001 confirmation; future-prompt updates) and the quality-gate confirmation
  (all items satisfied). Ran final allowed/forbidden-file checks. Next: push the
  working branch and open one draft PR targeting `Shopify-connector`, then stop.

### Research/Product Sprint D checkpoints

- **Sprint D / Stage 1 — Setup + evidence read (2026-07-01):** Started
  Research/Product Sprint D (canonical feature taxonomy + capability evidence
  map). Research/synthesis-only; **no-code gate confirmed** (`CLAUDE.md` §4–§5);
  high-power mode **not required** for this sprint (focused synthesis of
  already-merged Sprint C evidence — no new competitor crawling). Fetched remote
  branches and verified preconditions: **PR #51 is merged into `Shopify-connector`**
  (branch tip `e18ba8e` *is* the PR #51 merge commit); the working branch is based
  on `Shopify-connector` (identical to it at start); all required Sprint C outputs
  present (`competitor-deep-dives.md`, `competitor-feature-matrix.md`,
  `ux-ui-benchmark.md`, `common-patterns.md`, `best-in-class-observations.md`,
  `gaps-opportunities.md`, `avoid-list.md`, `competitor-source-notes.md`,
  `competitor-screenshot-inventory.md`). **Branch-name note (flagged for ChatGPT):**
  the harness designated the working branch **`claude/feature-taxonomy-sprint-d-t8d2t0`**
  (already checked out, based on `Shopify-connector`), whereas the Sprint D prompt
  body named `product/sprint-d-feature-taxonomy`; per the session's hard git rule
  ("never push to a different branch without explicit permission") the work
  proceeds on the harness-designated branch and the **PR still targets
  `Shopify-connector`** — `main`/plain `dev` untouched. Read the required
  governance/research files (CLAUDE.md, README, this handoff, learning rules,
  methodology, resource inventory, both official baselines, all Sprint C evidence,
  all QA logs). Confirmed DP-003/DP-004 prevention rules (competitor claim ≠ fact;
  configuration field ≠ demonstrated support; market promise ≠ demonstrated
  bidirectionality; ✅ requires demonstrated workflow/explicit evidence). Next:
  Stage 2 — draft the canonical feature taxonomy in `docs/02-product/feature-taxonomy.md`.
- **Sprint D / Stage 2 — Canonical taxonomy (2026-07-01):** Wrote
  `docs/02-product/feature-taxonomy.md` — the main deliverable: 20 canonical
  domains, ≈90 canonical capabilities (each with the required attribute block:
  ID/name/description/user-value/evidence-status/evidence-references/competitor-
  examples/UX/reliability/config implications/architecture-dependency/candidate-
  classification/MVP-relevance/notes), 8 cross-cutting groups, a classification
  summary, MVP-candidate + later-phase inputs (not decisions), a capabilities-
  requiring-architecture-review map to AR-002…AR-008, a weak/blocked-evidence
  register, open questions, and ChatGPT review notes. DP-003/DP-004 discipline
  applied throughout (claims stay claims; WK multi-company ➖; SH multi-company
  not-found; EC export not-found; `✅` only where demonstrated). Synthesis was
  worker-owned (no fan-out). Commit `70391b9`. Next: Stage 3 evidence map.
- **Sprint D / Stage 3 — Capability evidence map (2026-07-01):** Wrote
  `docs/02-product/capability-evidence-map.md` — compact per-capability
  traceability with evidence strength (A official / B strong-competitor / C
  mixed / D single-claim / E open-whitespace), strongest evidence, per-competitor
  coverage (WK/TQ/EM/VT/EC/SH with ✅/🟨/⬜/🚫/🔒/➖), official-platform dependency,
  architecture-review need (AR-002…AR-008), and MVP-review relevance. Grouped by
  domain for readability (no giant unreadable table). Commit `aa5d2c4`. Next:
  Stage 4 handoffs + QA loop.
- **Sprint D / Stage 4 — Product handoff + QA loop (2026-07-01):** Wrote
  `docs/02-product/product-research-handoff.md` (product-side handoff); wrote the
  full Sprint D section of this rolling handoff (above) with the learning feedback
  loop (DP-005 premature-decision risk, Mitigated) and the quality-gate
  confirmation; updated QA logs (**DP-005** + counter in `defect-pattern-log.md`;
  Sprint D non-decision note in `architecture-review-log.md`; nothing-rejected note
  in `rejected-approaches-log.md`; no-debt note in `technical-debt-register.md`).
  Ran final allowed/forbidden-file checks. Next: push the working branch and open
  one draft PR targeting `Shopify-connector`, then stop.

### Product Sprint E checkpoints

- **Sprint E / Stage 1 — Setup + evidence read (2026-07-01):** Started **Product
  Sprint E** (product vision, premium quality bar, differentiation strategy, and
  setup/UX principles). Product strategy / synthesis only; **no-code gate confirmed**
  (`CLAUDE.md` §4–§5); high-power mode **not required** (focused product synthesis of
  already-merged repo evidence — no new competitor crawling, no research fan-out).
  Fetched remote branches and verified preconditions: **PR #52 is merged into
  `Shopify-connector`** (confirmed via GitHub API — `merged: true`, merged 2026-07-01;
  branch tip `9a744f7` *is* the PR #52 merge commit); the working branch is based on
  `Shopify-connector` (identical to it at start); all required Sprint D outputs present
  (`feature-taxonomy.md`, `capability-evidence-map.md`, `product-research-handoff.md`);
  the **DP-006 evidence-consistency gate** is present in `defect-pattern-log.md`.
  **Branch-name note (flagged for ChatGPT):** the harness designated the working branch
  **`claude/sprint-e-product-strategy-gd2kfs`** (already checked out, based on
  `Shopify-connector`), whereas the Sprint E prompt body named
  `product/sprint-e-product-vision-quality-bar`; per the session's hard git rule
  ("never push to a different branch without explicit permission") the work proceeds on
  the harness-designated branch and the **PR still targets `Shopify-connector`** —
  `main`/plain `dev` untouched. Read the required governance/product/research files
  (CLAUDE.md, README, this handoff, research methodology, both official baselines,
  competitor deep dives + matrix, UX/UI benchmark, common patterns, best-in-class,
  gaps/opportunities, avoid-list, feature taxonomy, capability evidence map, product
  handoff, all QA logs, learning rules). Confirmed the phase is still **no-code**, that
  Sprint E is **product vision / strategy only** (no MVP finalization, no architecture
  finalization, no ADRs, no module boundaries), and the **DP-003/DP-004/DP-006**
  prevention + evidence-consistency rules (competitor claim ≠ fact; config field ≠
  demonstrated support; market promise ≠ demonstrated bidirectionality; conditional
  platform requirements stay conditional; improvement opportunities are inference, not
  demonstrated evidence; no capability enters MVP/architecture as a decision until
  ChatGPT-reviewed). Next: Stage 2 — draft `docs/02-product/product-vision.md`.
- **Sprint E / Stage 2 — Product vision (2026-07-01):** Wrote
  `docs/02-product/product-vision.md` — the main deliverable: status/purpose/evidence
  base, what we are building, product thesis, target personas (P1–P4, inference-level),
  core customer problems, ten product principles, premium quality bar, five-theme
  differentiation strategy, per-domain strategies (UX / reliability & correctness /
  modularity & customizability / performance / security & permissions / docs-support-
  trust), what we do better than competitors, what we avoid, seven product
  non-negotiables, and explicit **MVP / later / architecture inputs (not decisions)** +
  open questions + ChatGPT review notes. Claim labels ([Fact]/[Competitor claim]/
  [Demonstrated]/[Inference]/[Recommendation]/[Open question]) applied throughout;
  competitor claims kept as claims (EM/VT-demonstrated weighted over SH/WK/EC/TQ);
  conditional items (OAuth, distribution, queue, REST/GraphQL, multi-company, module
  boundaries, payouts, data models) kept conditional/open (DP-006). Worker-owned (no
  fan-out). Commit `d3da053`. Next: Stage 3 — setup/UX principles.
- **Sprint E / Stage 3 — Setup & UX principles (2026-07-01):** Wrote
  `docs/02-product/setup-ux-principles.md` — a UX north star + 12 principles (guided
  setup; prove readiness; progressive disclosure; honest status & freshness; command
  center over scattered menus; recovery-first errors; safe-by-default actions;
  human-readable logs; guided mappings; role-aware UX; modular feature visibility;
  docs mirror the product) + per-area principle sets (setup flow, config screens,
  dashboard, sync operations, logs/retries/recovery, mapping screens,
  multi-store/permissions, advanced features) + anti-patterns + open questions +
  ChatGPT review notes. Grounded in Sprint C UX benchmark / best-in-class / avoid-list
  + Sprint D taxonomy; DP-003/004/006 discipline applied; **no screens or menus
  designed**. Commit `5561db3`. Next: Stage 4 — handoffs + QA loop.
- **Sprint E / Stage 4 — Handoffs + QA loop (2026-07-01):** Wrote the Sprint E section
  of `docs/02-product/product-research-handoff.md` and of this rolling handoff (above),
  each with the learning feedback loop (no new issue; DP-006 gate applied, not
  re-triggered) and, here, the quality-gate confirmation. Updated QA logs with
  non-decision / no-new-issue notes: `defect-pattern-log.md` (Sprint E note — DP-006
  gate applied, not re-triggered, no counter change), `architecture-review-log.md`
  (Sprint E non-decision note — vision/UX principles supply product-intent inputs to
  AR-002…AR-008, all still Not decided / Evidence pending), `rejected-approaches-log.md`
  (nothing rejected), `technical-debt-register.md` (no debt). Ran final allowed/
  forbidden-file checks. Next: push the working branch and open one draft PR targeting
  `Shopify-connector`, then stop.

### Product Sprint F checkpoints

- **Sprint F / Stage 1 — Setup + evidence read (2026-07-01):** Started **Product
  Sprint F** (MVP scope proposal, non-MVP/later-phase boundaries, and user stories —
  backlog item **RB-13**). MVP-proposal synthesis only; **no-code gate confirmed**
  (`CLAUDE.md` §4–§5); high-power mode **not required** (focused product/MVP synthesis
  of already-merged repo evidence — no new competitor crawling, no research fan-out).
  Fetched remote branches and verified preconditions: **PR #53 is merged into
  `Shopify-connector`** (confirmed via GitHub API — `merged: true`, merged 2026-07-01
  10:17Z; branch tip `6e73f82` *is* the PR #53 merge commit); the working branch
  `claude/mvp-scope-user-stories-dms7s8` is based on `Shopify-connector` (identical to
  it at start, merge-base `6e73f82`). All required inputs present:
  `feature-taxonomy.md`, `capability-evidence-map.md`, `product-vision.md`,
  `setup-ux-principles.md`, `product-research-handoff.md`, and the **DP-006
  evidence-consistency gate** in `defect-pattern-log.md`. **Branch-name note for
  ChatGPT (flagged):** the Sprint F prompt body named
  `product/sprint-f-mvp-scope-proposal`, but the session's hard git rule designated
  the harness branch `claude/mvp-scope-user-stories-dms7s8` ("never push to a
  different branch without explicit permission"), so work proceeds on the
  harness-designated branch; **the PR still targets `Shopify-connector`**; `main` and
  plain `dev` untouched. Read `CLAUDE.md`, the required research/product/QA files, and
  confirmed: current phase is still no-code; Sprint F is MVP **proposal** only;
  architecture stays gated (AR-002…AR-008 all Not decided / Evidence pending);
  implementation stays gated; DP-003/004/005/006 prevention rules understood. Added
  this checkpoint. Commit `880dda8`. Next: Stage 2 — draft `docs/02-product/mvp-scope.md`.
- **Sprint F / Stage 2 — MVP scope proposal (2026-07-01):** Wrote
  `docs/02-product/mvp-scope.md` — the main deliverable: status/purpose/evidence base,
  a scope decision rule, MVP thesis (*small but excellent = a correct, observable,
  recoverable single-store loop, import-first*), MVP quality bar, the recommended scope,
  a full **MVP-scope-by-domain** with per-item blocks (Capability ID / Recommendation
  include·exclude·defer·open / Evidence strength / Evidence source / User value / Risk if
  included / Risk if excluded / Architecture dependency / MVP rationale / ChatGPT decision
  needed) for all 20 domains (~90 capabilities), the MVP-critical reliability/UX/config/
  security lists, **three options considered** (A correctness-core-import-first
  [recommended], B bidirectional catalog, C thin import-only pilot), excluded
  capabilities, an **Architecture-dependent MVP items** table (AR-002…AR-008, intent not
  mechanism), the **DP-006 evidence-consistency review** (8 checks), MVP acceptance
  principles, and open questions/review notes. Every inclusion marked *Proposed MVP
  inclusion — pending ChatGPT acceptance*; architecture-sensitive items marked
  *Architecture-dependent — must be resolved in RB-14 before implementation*. Worker-owned
  (no fan-out). Commit `1dbea92`. Next: Stage 3 — non-MVP/later boundaries.
- **Sprint F / Stage 3 — Non-MVP/later boundaries (2026-07-01):** Wrote
  `docs/02-product/non-mvp-and-later-phases.md` — a strict non-MVP rule; explicitly
  non-MVP items (export, full payments/refunds/returns/cancellations, payouts,
  multi-package fulfilment, order risk, SEO/BoM/pricelists/per-market, analytics) with
  per-item blocks (Capability ID / Category / Why not MVP / Evidence / Risk of including
  too early / What must be true before including); later-phase candidates (Phase 2–4);
  optional premium add-ons (Markets/B2B/POS/gift cards/metafields/extended); architecture-
  dependent later items; items blocked by weak evidence (pHash, TQ/EC/SH breadth, WK
  multi-company ➖ DP-004), by the distribution decision (App-Store/demo, C-DOCS-04), and
  by Odoo edition/hosting (Enterprise-only reports; Odoo Online / staging cron
  constraints); and a **"what not to accidentally pull into MVP"** anti-bloat contract.
  Exclusions framed as recommendations-against-MVP, not rejected approaches. Commit
  `103a638`. Next: Stage 4 — user stories.
- **Sprint F / Stage 4 — User stories (2026-07-01):** Wrote
  `docs/02-product/user-stories.md` — persona assumptions (P1–P4, primary MVP persona
  left open), a story format, **10 MVP epics** (store setup & readiness; product/catalog;
  customer import & matching; order import & lifecycle; inventory & freshness; fulfilment
  & tracking; logs/errors/retries/recovery; command center; mapping & configuration;
  permissions & roles) with persona-driven, testable, product-level stories (each: Persona
  / Story / Capability IDs / MVP relevance proposed·later·open / Evidence strength /
  Acceptance notes / Failure-recovery notes / Architecture dependency / Open questions),
  **6 later-phase epics**, product-level acceptance principles, and open questions/review
  notes. **No implementation tasks, no code-level acceptance criteria, no screens/
  modules.** Commit `fd4d131`. Next: Stage 5 — handoffs + QA loop.
- **Sprint F / Stage 5 — Handoffs + QA loop (2026-07-01):** Wrote the Sprint F section of
  `docs/02-product/product-research-handoff.md` and of this rolling handoff (above), each
  with the learning feedback loop (no new issue; DP-006 gate applied, not re-triggered)
  and, here, the branch/commit table and quality-gate confirmation. Updated QA logs with
  non-decision / no-new-issue notes: `defect-pattern-log.md` (Sprint F — DP-006 gate
  applied, not re-triggered; no counter change; MVP proposal did not finalize architecture
  or turn weak evidence into scope), `architecture-review-log.md` (Sprint F non-decision
  note — MVP proposal supplies capability-scope inputs to AR-002…AR-008, all still Not
  decided / Evidence pending), `rejected-approaches-log.md` (nothing rejected; MVP
  exclusions are recommendations-against-MVP), `technical-debt-register.md` (no debt). Ran
  final allowed/forbidden-file checks. Next: push the working branch and open one draft PR
  targeting `Shopify-connector`, then stop.
- **Sprint G / Stage 1 — Setup & start handoff (2026-07-01):** Confirmed **PR #54 merged**
  into `Shopify-connector` (merge commit `1d5e774`, merged 2026-07-01); confirmed the
  latest `Shopify-connector` contains `docs/02-product/{mvp-scope,non-mvp-and-later-phases,
  user-stories,product-research-handoff}.md` and the **DP-006 evidence-consistency gate** in
  `docs/05-qa/defect-pattern-log.md`. Working branch is the **harness-designated**
  `claude/sprint-g-mvp-scope-jxisgm` (the prompt requested `product/sprint-g-mvp-acceptance`;
  branch-name discrepancy recorded here and in the Sprint G handoff), based on latest
  `Shopify-connector` (HEAD `1d5e774`, clean base); **PR targets `Shopify-connector`**;
  `main` and plain `dev` untouched. Read `CLAUDE.md`, the required research/product/QA files,
  and the decision-record template; confirmed: current phase is still **no-code**; Sprint G
  records **MVP acceptance only** (product scope, not architecture); architecture stays gated
  (AR-002…AR-008 all Not decided / Evidence pending); implementation stays gated;
  DP-003/004/005/006 prevention rules and the evidence-consistency gate understood; allowed/
  forbidden files understood. Added this checkpoint. Next: Stage 2 — create
  `docs/04-decisions/DEC-003-mvp-scope.md` recording ChatGPT's accepted RB-13 MVP baseline.
- **Sprint G / Stage 2 — MVP decision record (2026-07-01):** Created
  `docs/04-decisions/DEC-003-mvp-scope.md` — the **accepted MVP product-scope baseline** with
  the prompt-specified structure (Status accepted 2026-07-01; **Decision type: product scope,
  not architecture**; Context; Decision; Accepted MVP option = Option A correctness-core/
  import-first; Accepted MVP scope; Deferred from MVP; Domain 9 minimal-financial-evidence
  decision; Refund/cancellation deferral; Bulk-ops not-user-facing decision; Store/company
  single-store/single-company decision; P1-primary/P2-secondary persona decision; Architecture
  dependencies feeding AR-002…AR-008 with none decided; Evidence basis; Consequences;
  Non-goals; Open architecture questions; and a **Review/change-control** clause stating no
  architecture/API/queue/data-model/module-boundary decision is made and implementation stays
  blocked). Recorded ChatGPT's accepted decisions exactly. Commit `595c4c9`. Next: Stage 3 —
  align the product scope docs.
- **Sprint G / Stage 3 — Product doc alignment (2026-07-01):** Updated `mvp-scope.md`
  (title/status → **accepted baseline**; added a **ChatGPT RB-13 acceptance** section near the
  top; resolved every former `open` fork inline as **RB-13 accepted/decision** — product/
  customer export DEFERRED, Domain 9 INCLUDE-minimal-evidence-only, refunds/cancellations
  DEFERRED, bulk ops NOT-user-facing/internal-only, single-store/single-company CONFIRMED,
  App-Store OUT; split Open questions into resolved vs still-open; updated the
  evidence-consistency review check #8, options, excluded list, acceptance principle #1, and
  the closing banner), `non-mvp-and-later-phases.md` (status → **accepted boundary**;
  export/customer-export/refunds-cancellations/Domain-9-accounting/bulk-ops/App-Store/
  multi-store-company confirmed non-MVP with revisit conditions; resolved Open questions), and
  `user-stories.md` (persona → P1-primary/P2-secondary; US-E2-05/US-E3-04/US-E4-06 → **later**;
  US-E4-05 Domain 9 → **MVP minimal-evidence-only**; bulk-ops mentions → internal-only; later
  epics + acceptance principle #2 + Open questions aligned). Kept architecture-dependent items
  marked architecture-dependent; did not pretend architecture is solved. Commit `16ec244`.
  Next: Stage 4 — handoffs + QA loop.
- **Sprint G / Stage 4 — Handoffs + QA loop (2026-07-01):** Wrote the Sprint G section of
  `docs/02-product/product-research-handoff.md` and of this rolling handoff (above), each with
  the required subsections (session summary; files; MVP acceptance summary; accepted decisions;
  deferred scope; architecture dependencies still open; evidence-consistency gate; no-code/
  no-architecture confirmation; recommended next sprint = **RB-14 Architecture Prep Part 1**
  (AR-002/AR-003/AR-005); stop confirmation) plus the learning feedback loop and branch-reality
  note. Updated QA logs with non-decision / no-new-issue notes: `architecture-review-log.md`
  (**required** Sprint G non-decision note — DEC-003 accepts product MVP scope only, feeds
  AR-002…AR-008, no AR row decided), `defect-pattern-log.md` (Sprint G — DP-006 gate applied,
  not re-triggered; no new row, no counter change; product-scope acceptance kept separate from
  architecture), `rejected-approaches-log.md` (none — deferrals are product-scope boundary
  decisions, not rejected approaches), `technical-debt-register.md` (none — no code). Ran final
  allowed/forbidden-file checks. Next: push the working branch and open one draft PR targeting
  `Shopify-connector`, then stop.
- **Sprint G / revision — controlled product export into MVP (PR #55 review, 2026-07-01):**
  ChatGPT reviewed PR #55 and returned **REVISE**: the first draft **over-deferred product
  export**. Corrected on the same branch/PR (no new PR, no merge). **Product-scope correction
  only** — **controlled product export/update is now IN MVP** (Shopify→Odoo import **and**
  Odoo→Shopify export/update, with first-sync matching, binding, preview/dry-run, duplicate
  prevention, and draft/unpublished/channel-controlled safety = **controlled bidirectional
  product onboarding**); **full autonomous bidirectional catalog management** and **customer
  export** stay later. Updated only the 10 PR #55 files: `DEC-003-mvp-scope.md` (revised
  Decision/Accepted-option/direction/Deferred/Non-goals + new **Product direction decision**
  section + AR-002/005 rows + Status revision note), `mvp-scope.md` (RB-13 acceptance corrected
  + new **Product onboarding and duplicate-prevention baseline** section + C-PROD-02/03/05
  blocks + options + excluded + evidence-consistency + TeqStars accessibility correction),
  `non-mvp-and-later-phases.md` (product export removed from non-MVP; new **Full autonomous
  bidirectional catalog management** boundary; customer export kept later), `user-stories.md`
  (US-E2-05 → controlled MVP export/update; new **US-E2-06** first-sync matching; customer
  export later), both handoffs (this revision note), and QA logs (`defect-pattern-log.md`
  Sprint G revision note — over-deferral corrected, TQ source availability changed, product-scope
  correction not an implementation defect, no new DP row; `architecture-review-log.md` — controlled
  product export/update now feeds AR-002/AR-005, full bidirectional conflict-resolution later, no
  AR row decided). **TeqStars docs re-checked accessible 2026-07-01; full rebaseline pending a
  later sprint.** No rejected approaches; no technical debt; no architecture decided; no
  implementation authorized. Commit `docs: revise mvp baseline for controlled product export`.
  Next: push the same branch/PR #55; do not merge; await ChatGPT re-review.
- **Phase 1 Domain Model + DEC-003 Scope-Hole Closure (2026-07-02):** confirmed PR #61
  merged into `Shopify-connector` (merge commit `26dc30109530e2566755fd93bd974284083c3922`)
  and DEC-004/005/006 Accepted / AR-002/003/005 Accepted / AR-004/006/007/008 not decided
  before editing. Authored `phase1-domain-model-brief.md` (eight Phase 1 domains, concept
  level only) and proposed `DEC-007-phase1-scope-clarifications.md`
  (`Status: Proposed for ChatGPT review`) closing five DEC-003 scope holes: variant
  export/update, image/media + price "where feasible" wording, a first-inventory-push
  guard, a fulfilment customer-notification default (grounded in a small, targeted
  official-source check of `FulfillmentInput.notifyCustomer`/
  `fulfillmentTrackingInfoUpdate`, both defaulting to no notification), and
  tax/shipping/discount/payment-evidence treatment. Added five new user stories and
  pointer-only notes to `mvp-scope.md`/`non-mvp-and-later-phases.md`; added a non-decision
  note to `architecture-review-log.md` (AR-006/007/008 fed, not decided); added
  RA-008/009/010 (tagged PROPOSED) to `rejected-approaches-log.md`. No code; no DEC-003/
  004/005/006 edit; no AR row decided. Next: push branch, open one draft PR into
  `Shopify-connector`, stop for ChatGPT/Fable review.
- **AR-004 + AR-006 Decision Preparation (2026-07-02):** confirmed PR #63 merged into
  `Shopify-connector` (merge commit `3ca0cde`) and DEC-003/004/005/006/007 Accepted /
  RA-001–010 binding / AR-002/003/005 Accepted / AR-004/006/007/008 not decided before
  editing. Authored `ar004-module-boundary-decision-brief.md` and
  `ar006-error-retry-idempotency-decision-brief.md`; proposed `DEC-008-module-boundary-
  strategy.md` and `DEC-009-error-retry-idempotency-strategy.md` (both
  `Status: Proposed for ChatGPT review`), moving AR-004/AR-006 from "Not decided" to
  "Proposed for ChatGPT review" in `architecture-review-log.md`. Added RA-011–017 (tagged
  PROPOSED) to `rejected-approaches-log.md`. Opened draft PR #64 into `Shopify-connector`.
  Two follow-up revision rounds on the same PR (not a new PR): a minor self-revision
  (error-class count 15→16, DAG notation clarity, RA formatting), then a Fable
  ACCEPT-WITH-MINOR-CHANGES round (DEC-006 binding-schema-fork reconciliation,
  ambiguous-outcome non-idempotent-write retry rule, evidence-wording and citation-
  attribution corrections, feature-flag/config-model scope routed onward, DEC-005
  reconciliation-cadence handoff acknowledged, state-machine wording cleanup, RA-014
  revisit condition tightened). No code; no DEC-003/004/005/006/007 edit; AR-007/AR-008
  untouched. Next: push branch, keep PR #64 open (not merged), await ChatGPT/Fable
  re-review.
- **DEC-008/DEC-009 Acceptance Patch (2026-07-02):** confirmed PR #64 merged into
  `Shopify-connector` (merge commit `e4c74abf0e3b4ad32e66413d27b40287ed4c5822`) and
  DEC-003/004/005/006/007 Accepted / RA-001–010 binding / AR-002/003/005 Accepted /
  DEC-008/DEC-009 Proposed / AR-004/AR-006 proposed-only / AR-007/AR-008 not decided before
  editing. Changed DEC-008 and DEC-009 Status from `Proposed for ChatGPT review` to
  `Accepted by ChatGPT`, acceptance date 2026-07-02, citing the PR #64 merge and Fable's
  ACCEPT WITH MINOR CHANGES review while preserving every documented caveat. Updated the
  AR-004 and AR-006 decision briefs, `04-decisions/README.md`, and
  `architecture-review-log.md` (AR-004/AR-006 rows move to "Accepted by ChatGPT"; AR-007/
  AR-008 untouched). Removed the `PROPOSED:` prefix from RA-011–017 and cited each DEC
  file's accepted status — now binding final rejected approaches. No code; no
  DEC-003/004/005/006/007 edit; AR-007/AR-008 remain not decided; implementation remains
  blocked. Next: push branch, open one draft PR into `Shopify-connector`, stop for ChatGPT
  review.
- **AR-007 + AR-008 Decision Preparation (2026-07-02):** confirmed PR #65 merged into
  `Shopify-connector` (merge commit `dfb0199c9588ae600216ef549d160d0ced15034f`) and
  DEC-003/004/005/006/007/008/009 Accepted / RA-001–017 binding / AR-002/003/004/005/006
  Accepted / AR-007/AR-008 not decided before editing. Authored
  `ar007-inventory-architecture-decision-brief.md` and
  `ar008-fulfillment-architecture-decision-brief.md`; ran a small, targeted official-source
  check (`ar007-ar008-evidence-refresh.md`) against Odoo 19.0 docs (On Hand/Free to Use/
  Forecasted, location types, carrier tracking) since the existing Odoo research notes had
  zero coverage of `stock.quant`/`stock.picking`/delivery-carrier models; proposed
  `DEC-010-inventory-architecture-strategy.md` and
  `DEC-011-fulfillment-architecture-strategy.md` (both `Status: Proposed for ChatGPT
  review`), moving AR-007/AR-008 from "Not decided" to "Proposed for ChatGPT review" in
  `architecture-review-log.md`. Added RA-018–023 (tagged PROPOSED) to
  `rejected-approaches-log.md`; checked against RA-001–017 first, referenced RA-008/009/
  014/017 instead of duplicating, and treated multi-package/multi-location fulfillment as
  an existing deferral (not a rejection). Flagged one open architecture issue (a shared
  Shopify-Location reference for `inventory`/`fulfillment` without violating DEC-008's
  no-inventory-dependency rule for `fulfillment`) and routed it to architecture review
  rather than deciding it unilaterally. No code; no DEC-003/004/005/006/007/008/009 edit;
  AR-007/AR-008 are proposed only, not accepted; implementation remains blocked. Next: push
  branch, open one draft PR into `Shopify-connector`, stop for ChatGPT/Fable review.
- **DEC-010/DEC-011 Acceptance Patch (2026-07-02):** confirmed PR #66 merged into
  `Shopify-connector` (merge commit `14af2fb3becb47ba7c32a50715d85f6eaab0d855`) and
  DEC-003/004/005/006/007/008/009 Accepted / RA-001–017 binding / AR-002/003/004/005/006
  Accepted / DEC-010/DEC-011 Proposed / AR-007/AR-008 proposed-only / RA-018–023 PROPOSED
  before editing. Changed DEC-010 and DEC-011 Status from `Proposed for ChatGPT review` to
  `Accepted by ChatGPT`, acceptance date 2026-07-02, citing the PR #66 merge and Fable's
  ACCEPT WITH MINOR CHANGES review while preserving every documented caveat, and recorded
  the shared Shopify Location reference clarification as ratified against DEC-008. Updated
  the AR-007 and AR-008 decision briefs, `04-decisions/README.md`, and
  `architecture-review-log.md` (AR-007/AR-008 rows move to "Accepted by ChatGPT"; all of
  AR-002 through AR-008 now accepted). Removed the `PROPOSED:` prefix from RA-018–023 and
  cited each DEC file's accepted status — now binding final rejected approaches. No code;
  no DEC-003/004/005/006/007/008/009 edit; implementation remains blocked. Next: push
  branch, open one draft PR into `Shopify-connector`, stop for ChatGPT review.
