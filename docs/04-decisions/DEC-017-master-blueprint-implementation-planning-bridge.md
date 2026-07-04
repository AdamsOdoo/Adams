# DEC-017 — Master Blueprint Part E: Implementation-Planning Bridge

> **Accepted decision record** for the premium **Odoo 19 ↔ Shopify
> Connector**, accepting the **Master Blueprint Part E — Implementation-
> Planning Bridge** as a **documentation-only** implementation-planning
> bridge. Companion documents:
> [`../03-architecture/master-blueprint.md`](../03-architecture/master-blueprint.md),
> [`../03-architecture/master-blueprint-implementation-planning-bridge.md`](../03-architecture/master-blueprint-implementation-planning-bridge.md),
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
> Companion review-log entry:
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-014**, Accepted by ChatGPT via DEC-017).

## Status

**Accepted by ChatGPT.** Acceptance date: **2026-07-04**. Starting point:
PR #80 ("Propose Master Blueprint Part E implementation-planning bridge"),
head commit `e4e1fd5b2d2c4fafdaa57c4b025d5234611b44b6`, confirmed as the base
before this acceptance patch was applied. **This acceptance is
documentation-only.** It does not create or modify any Odoo module, model,
view, controller, security file, manifest, test, migration, or CI file. It
does **not** authorize implementation, does **not** open the implementation
gate, and does **not** create any implementation task.

## Context

Part E was proposed (PR #80) after PR #79 merged into `Shopify-connector`
(merge commit `77ee511036a98db36262bdbc9b4ae4371a2d85f8`), directly executing
the PR #78 Master Blueprint Integrity & Competitor Advantage Audit's own §10
"Required Part E focus areas" as its scoped work. The proposal:

- Built an **MBQ decision plan** routing every implementation-blocking open
  question (MBQ-01 through MBQ-63) to a decision owner, decision type, and
  recommended timing — a routing/sequencing plan, not a set of decisions.
- Closed two of the three currently-untracked official-doc gaps the PR #78
  audit flagged: Shopify's `MoneyBag`/presentment-currency order-money model
  vs. Odoo's single computed `sale.order.currency_id` (folded into new
  register row **MBQ-64**), and Shopify's product-domain webhook topic
  strings (folded into new register row **MBQ-65**) — both verified against
  official Shopify (`shopify.dev`) and official Odoo 19.0
  documentation/source, accessed 2026-07-04.
- Proposed a module-by-module implementation sequence following the
  already-accepted DEC-008 dependency DAG, a first-safe-implementation-slice
  recommendation, test/rollback strategy at planning level, and a restated
  no-code-to-code gate checklist.

ChatGPT reviewed PR #80 and **accepts its substance** — the planning-bridge
document, AR-014, and the two official fact-verification findings — while
explicitly **not** deciding the MBQ decision plan's own ChatGPT-batch items,
**not** resolving MBQ-64's design/selection mechanism, and **not** resolving
MBQ-65's payload/subscription/scope residual. This record (DEC-017) is the
acceptance patch that carries that decision into the repository.

## Decision

**ChatGPT accepts Master Blueprint Part E as a documentation-only
implementation-planning bridge.** Specifically:

1. **The Part E document**
   ([`../03-architecture/master-blueprint-implementation-planning-bridge.md`](../03-architecture/master-blueprint-implementation-planning-bridge.md))
   is now the **accepted implementation-planning bridge** — its MBQ decision
   plan, proposed implementation sequence, first-safe-slice recommendation,
   test/rollback strategy, and gate checklist are accepted **as planning
   guidance**, not as implementation authorization.
2. **AR-014** moves to **Accepted by ChatGPT**
   (`../05-qa/architecture-review-log.md`).
3. **The official fact-verification findings for MBQ-64 and MBQ-65 are
   accepted** at fact-verification level only (see *Official facts accepted
   at fact-verification level* below) — the underlying platform facts are
   now settled; the design/selection and residual questions each row still
   carries are **not** decided by this acceptance.
4. **The index (`master-blueprint.md`) Part E row** moves to **Accepted by
   ChatGPT via DEC-017**.

## Accepted scope

- **MBQ decision plan** — accepted **as a routing/sequencing plan only**.
  No individual MBQ decision within it (the "ChatGPT batch," the
  "implementation planning" bucket, or the naming pass) is made by this
  record; the plan's routing (who decides what, and roughly when) is
  accepted as the right shape for that future work.
- **Official-doc gap closure for currency and product-webhook-topic facts**
  — accepted (see *Official facts* below).
- **New MBQ rows MBQ-64 and MBQ-65** — accepted as **register additions**,
  each partially/fact-level resolved only as stated below; neither fully
  resolved.
- **Proposed implementation sequence** — accepted **as planning guidance
  only**, not as a locked, final task order; it may still be adjusted once
  the MBQ decision plan's ChatGPT-batch items are actually decided.
- **First safe implementation-slice recommendation** (the job/log/error
  abstraction skeleton, MBQ-19/20/21) — accepted **as a recommendation
  only**; it is not thereby authorized to start.
- **Test strategy and rollback strategy** — accepted **as planning guidance
  only**; no test file, migration script, or feature-flag mechanism is
  created by this acceptance.
- **Implementation-task-template enforcement** — accepted **as planning
  guidance**; confirms
  [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)
  needs no redesign, nothing more.
- **No-code-to-code gate checklist** — accepted as the current, correct
  statement of gate status (2 of 5 criteria satisfied); this acceptance does
  not itself change that count except to confirm criterion 1 (Parts A–D
  and, now, Part E's planning content) remains satisfied.

## What this acceptance does NOT authorize

- **No implementation.** No Odoo module, model, view, controller, security
  file, manifest, test, migration, or CI file is created or authorized.
- **No code.**
- **No Odoo modules.**
- **No implementation-gate opening.** Opening the gate remains a separate,
  explicit ChatGPT act per `master-blueprint.md`'s "Criteria for when
  implementation may later be opened" and
  [`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md)
  §10 — this record does not perform that act.
- **No implementation-task creation.** No task is written to the CLAUDE.md
  §9 / implementation-task-template.md template by this acceptance.
- **No security/model/view/XML/manifest/test/CI files.**
- **No change to DEC-003 through DEC-016** — all remain unchanged, unedited,
  and unweakened by this record.
- **No weakening of accepted Parts A–D** — Part A (DEC-013), Part B
  (DEC-014), Part C (DEC-015), and Part D (DEC-016, at screen-design
  blueprint level) all stand exactly as previously accepted.
- **No pixel-level UI approval.** Part D's screen-design-only acceptance
  boundary (DEC-016) is unaffected and unchanged by this record.
- **No final implementation-sequence lock.** The proposed sequence (Part E
  §7) remains subject to adjustment once the MBQ decision plan's ChatGPT-
  batch items are actually decided — this acceptance does not freeze it.

## MBQ impact

- **MBQ-64** (Shopify `MoneyBag`/presentment-currency order-money model vs.
  Odoo's single computed `sale.order.currency_id`):
  - **Accepted at fact-verification level**: Shopify order-money fields use
    `MoneyBag` with `shopMoney` and `presentmentMoney` (both non-null on
    every order-total field); Odoo's `sale.order` has a single computed
    `currency_id`, derived from the pricelist's currency if a pricelist is
    set, else the order's company currency; Odoo's `res.currency.round()`
    and `res.currency.compare_amounts()` are verified, currency-aware
    tolerance-comparison primitives.
  - **Not resolved by this acceptance**: the design/selection mechanism —
    **which** Shopify money field (`shopMoney` vs. `presentmentMoney`) the
    total-check guard and price-sync mechanism compare against Odoo's single
    `currency_id`, and how a shop-currency-vs-order-currency mismatch is
    itself classified/guarded.
  - **Remains open** for that design/selection decision (ChatGPT +
    Implementation planning, complementing MBQ-56), exactly as the Part E
    document itself stated.
- **MBQ-65** (Shopify product-domain webhook topic strings):
  - **Accepted at fact-verification level**: `PRODUCTS_CREATE`,
    `PRODUCTS_UPDATE`, and `PRODUCTS_DELETE` are confirmed against the
    official `WebhookSubscriptionTopic` enum, the direct product-domain
    analog of MBQ-37's inventory-topic resolution.
  - **Not resolved by this acceptance**: the exact **payload shape**; the
    **required subscription scopes** beyond the verified `read_products`
    requirement; and **whether webhook-driven product import is implemented
    in Phase 1 at all** (vs. scheduled/manual/reconciliation-only).
  - **Residual remains open**, mirroring MBQ-63's inventory-webhook residual
    treatment.
- **Existing MBQ rows remain unchanged** — no row other than MBQ-64/MBQ-65's
  own status wording is touched by this acceptance; every row previously
  open (per the DEC-013 through DEC-016 acceptance notes) remains exactly as
  open as before.
- **No ChatGPT-batch MBQ is decided by this acceptance** — MBQ-06, MBQ-08,
  MBQ-17 (posture), MBQ-33, MBQ-34, MBQ-41, MBQ-45 (surface split), MBQ-52,
  MBQ-54, MBQ-60, and MBQ-62 (the Part E document's own "ChatGPT batch," §4)
  all remain exactly as open as the register already states; this record
  accepts the **plan to decide them**, not the decisions themselves.

## Official facts accepted at fact-verification level

Accepted as verified, cited facts (no new research performed by this
record — the facts were already verified and cited in
[`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md)
and
[`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md),
both accessed 2026-07-04, neither file touched by this acceptance patch):

- **Shopify `MoneyBag` / `shopMoney` / `presentmentMoney`** — `MoneyBag` has
  exactly two non-null `MoneyV2` fields, `shopMoney` ("Amount in shop
  currency") and `presentmentMoney` ("Amount in presentment currency");
  every Shopify order money/total field (`totalPriceSet`,
  `currentTotalPriceSet`, `totalOutstandingSet`, and the rest) is
  `MoneyBag`-typed.
- **Odoo `sale.order` single `currency_id`** — computed, stored,
  precomputed `Many2one` to `res.currency`, deriving from
  `pricelist_id.currency_id` if set, else `company_id.currency_id`; exactly
  one document currency per order. `res.currency.rounding`/`round()`/
  `compare_amounts()` are Odoo's own currency-aware rounding/tolerance-
  comparison primitives.
- **Shopify product webhook topic strings** — `PRODUCTS_CREATE`,
  `PRODUCTS_UPDATE`, `PRODUCTS_DELETE`, confirmed against the official
  `WebhookSubscriptionTopic` enum.

Accepting these facts does **not** resolve MBQ-64's design/selection
question or MBQ-65's payload/subscription/scope residual — see *MBQ impact*
above.

## Implementation gate status

**Still closed.** Parts A through E are now all accepted (Part E as a
documentation-only planning bridge; Part D at screen-design blueprint level
only), but implementation remains blocked because:

1. **Blocking MBQs are not resolved or accepted-as-risk** — the ~45
   implementation-blocking rows the Part E MBQ decision plan routes remain
   open; this acceptance decides none of them.
2. **No explicit ChatGPT implementation-gate-opening act has occurred** —
   opening the gate is a separate act from accepting the planning bridge,
   per `master-blueprint.md`'s gate criteria and
   `../05-qa/quality-feedback-loop.md` §10; this record does not perform it.
3. **No implementation tasks have been written** to the CLAUDE.md §9 /
   `../06-prompts/implementation-task-template.md` template — none exists.

## Risks / follow-ups

- **The MBQ decision plan's ChatGPT-batch items remain the largest lever**
  before the gate can meaningfully be considered for opening — this
  acceptance does not decide them; a dedicated MBQ decision-batch session is
  the recommended next step.
- **MBQ-64's design/selection mechanism** and **MBQ-65's payload/
  subscription/scope residual** both remain open and must not be silently
  read as resolved because their underlying facts are now accepted.
- **The proposed implementation sequence (Part E §7) is not locked** — it
  may need adjustment once first-push-guard granularity (MBQ-33), apply-mode
  (MBQ-34), and other ChatGPT-batch items are actually decided.
- **No accepted Part A–D content was reopened, re-litigated, or weakened**
  by this acceptance — DEC-003 through DEC-016 stand exactly as before.
- **Pixel-level UI design remains a later, separate pass** — unaffected by
  this record.

## Review / change control

- **This record accepts Master Blueprint Part E as a documentation-only
  implementation-planning bridge and AR-014.** No accepted decision
  (DEC-003–016) is re-litigated; no rejected approach is reintroduced;
  checked against `../05-qa/rejected-approaches-log.md` before this patch
  (unchanged, not touched).
- **Related:** AR-014 (`../05-qa/architecture-review-log.md`, Accepted by
  ChatGPT via DEC-017); the companion Part E document above; DEC-003
  through DEC-016 (accepted context, unmodified).
- **Further changes** to this record require ChatGPT review, mirroring the
  DEC-013/014/015/016 change-control pattern.
