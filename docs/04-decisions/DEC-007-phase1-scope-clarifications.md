# DEC-007 — Phase 1 Scope Clarifications

> **Proposed decision record for ChatGPT review.** This record **clarifies** five known
> scope-level gaps left after [DEC-003](./DEC-003-mvp-scope.md) (accepted MVP product
> scope) and the accepted [DEC-004](./DEC-004-distribution-api-auth-strategy.md) /
> [DEC-005](./DEC-005-sync-orchestration-strategy.md) /
> [DEC-006](./DEC-006-binding-dedup-identity-strategy.md) architecture decisions. It does
> **not** rewrite DEC-003, and it does **not** authorize implementation. Companion:
> [`../03-architecture/phase1-domain-model-brief.md`](../03-architecture/phase1-domain-model-brief.md).

## Status

**Proposed for ChatGPT review.**

## Date

2026-07-02.

## Scope

**Six clarification sections, covering the five known DEC-003 scope-hole themes. Image/
media and price are split into separate sections because they need different
boundaries.**

1. Variant export/update inclusion and boundary.
2. Image/media Phase 1 handling (replacing vague "where feasible" wording).
3. Price / compare-at price Phase 1 handling (replacing the same wording).
4. A first-inventory-push guard before Odoo ever writes inventory to Shopify.
5. The customer-notification side effect of fulfilment/tracking write-back.
6. Tax / shipping / discount / payment-evidence / invoice-policy treatment on order
   import.

This record does **not** decide AR-004 (module boundaries), AR-006 (full retry/error/
idempotency taxonomy), AR-007 (full inventory architecture), AR-008 (full fulfilment
architecture), exact Odoo model fields, exact database constraints, exact GraphQL
operations, the exact implementation sequence, or the Master Blueprint. It does not touch
DEC-003's, DEC-004's, DEC-005's, or DEC-006's own text.

## Relationship to DEC-003

- **This record clarifies DEC-003. It does not rewrite DEC-003.**
- **It does not authorize implementation.**
- **If accepted**, it becomes the **scope-clarification addendum** for Phase 1 — read
  alongside DEC-003, not in place of it.
- **If not accepted**, DEC-003 remains the **only accepted MVP scope record**, and the five
  gaps below remain open exactly as DEC-003 left them.

## Context

DEC-003 accepted **controlled bidirectional product onboarding** as MVP scope but left
several practical wording gaps that this record closes:

- Product export/update was accepted "controlled," but variant-level export/update was
  never explicitly stated as included or bounded — leaving room to read "product export" as
  template-only.
- Image/media and price/compare-at update/export were both qualified **"where feasible"** —
  vague wording that does not say what is included, excluded, or deferred.
- Inventory write-back was accepted in MVP with "initial Shopify stock import is
  controlled/reviewed," but no guard was stated for the **first Odoo→Shopify** inventory
  write specifically (the direction most likely to overwrite live Shopify stock).
- Fulfilment/tracking write-back was accepted in MVP, but whether it triggers a Shopify
  customer notification — and who controls that — was never stated.
- Order import was accepted with "minimal financial evidence only," but tax, shipping,
  discount, payment-evidence, and invoice/payment-creation treatment were not spelled out
  at the field/mechanism level.

Per `../05-qa/quality-feedback-loop.md` §10 (Phase-exit criteria, `[Recommendation —
becomes binding when merged by ChatGPT]`), a "DEC-003 scope-hole amendment accepted" is one
of the criteria for the Phase 1 research-phase exit. This record is that amendment,
proposed for review.

**Evidence basis.** DEC-003/004/005/006 (all accepted); the Shopify official-API facts
already recorded in `../01-research/shopify-official-api-notes.md`; a **small, targeted**
official-source check run this sprint (per the sprint's external-research rule, since the
tax/shipping/discount line fields and the fulfilment customer-notification default were not
already grounded in repo docs) — see *Newly verified facts* below.

## Newly verified facts (this sprint, 2026-07-02)

Per the sprint's external-research rule, these facts were **not** already grounded in
`../01-research/shopify-official-api-notes.md` and were checked against official Shopify
docs only (no competitor/vendor/forum source):

- **[Official fact]** `Order.taxLines` = "A list of all tax lines applied to line items on
  the order, before returns"; `Order.currentTaxLines`, `Order.totalTaxSet`;
  `Order.shippingLines`/`shippingLine` represent the shipping methods applied to the
  order, including checkout shipping option / carrier / service / cost details
  (paraphrase — the fetched summary of this field was a partial excerpt, not confirmed as
  the complete official field description; treat the exact full wording as **[Open
  question — must be verified before implementation]** if a verbatim quote is needed);
  `Order.discountApplications` = "A list of discounts that are applied to the order,
  excluding order edits and refunds"; `cartDiscountAmountSet`/`currentCartDiscountAmountSet`.
  Source: `https://shopify.dev/docs/api/admin-graphql/latest/objects/Order`. Access status:
  **Accessible**. Access date: **2026-07-02**.
- **[Official fact]** `FulfillmentInput.notifyCustomer` — "Whether the customer is
  notified. If `true`, then a notification is sent when the fulfillment is created." —
  **defaults to `false`**. Source:
  `https://shopify.dev/docs/api/admin-graphql/latest/input-objects/FulfillmentInput`.
  Access status: **Accessible**. Access date: **2026-07-02**.
- **[Official fact]** `fulfillmentTrackingInfoUpdate`'s `notifyCustomer` argument — "If
  this field is left blank, then notifications won't be sent to the customer when the
  fulfillment is updated." Source:
  `https://shopify.dev/docs/api/admin-graphql/latest/mutations/fulfillmentTrackingInfoUpdate`.
  Access status: **Accessible**. Access date: **2026-07-02**.

Per this sprint's allowed-files list, these facts are cited here and in the domain-model
brief only; propagating them into `../01-research/shopify-official-api-notes.md` is **not**
done in this sprint (that file is outside the allowed-files list) and is flagged as a
follow-up in the handoff.

## Clarifications proposed for review

### 1. Variant export/update clarification

**Proposed:** Phase 1 controlled product export/update **includes variant export/update**.
Variant export/update is **not optional** if product export/update is in MVP — DEC-003's
"product export/update" is not read as template-only.

- Variant export/update follows the **same controlled-export rules** DEC-003 already
  requires for product export/update: matching + binding before write, preview/dry-run
  before any destructive/full-state write, draft/unpublished/channel-controlled safety, no
  name-only automatic matching.
- Variant export/update is bounded to the **current Shopify product/variant model** (up to
  2,048 variants) — no attempt to support a deprecated/legacy variant model.
- The **exact `productSet`/mutation strategy** for writing variants (e.g. whether via
  `productSet`, `productVariantsBulkCreate`/`productVariantsBulkUpdate`, or a combination)
  remains **implementation planning under the accepted DEC-004 / AR-002 decision**
  (GraphQL-first, custom app, offline token are already decided by DEC-004; only the
  specific mutation choice for variant writes is an **[Open question]**, not decided
  here).
- This clarification does **not** expand MVP scope — DEC-003 already listed "variant /
  options import" (Shopify → Odoo) and "product export; product update" (Odoo → Shopify);
  this closes the ambiguity about whether "product update" covers the variant level. It
  does **not** add a new capability beyond what DEC-003 already accepted.

### 2. Image / media clarification

**Proposed:** Phase 1 supports **basic product image import/export/update** at
product/variant level, **where Shopify's and Odoo's standard image/media fields support
it**. Explicitly:

- **Included:** basic image import (Shopify → Odoo) and basic image export/update
  (Odoo → Shopify) at product and variant level, using standard image fields on both
  sides; preview before any destructive replacement or removal of an existing image (the
  same preview/dry-run guardrail DEC-003 already requires for full-state writes).
- **Excluded from Phase 1:** advanced image deduplication (e.g. perceptual-hash/pHash),
  automated alt-text enrichment, CDN-level image transformation/optimization, and any
  dedicated media-governance workflow.
- **Deferred:** none beyond what is already excluded above — image/media handling either
  ships at the basic level described or is out of scope; there is no separate "Phase 2
  image/media" carve-out beyond the excluded advanced items, which fold into the existing
  DEC-003 "unrestricted autonomous bidirectional catalog ownership" deferral if ever
  reconsidered.
- This replaces the DEC-003/`mvp-scope.md` **"where feasible"** wording for image/media with
  the explicit included/excluded split above. It does not add scope beyond what "basic
  image sync" (C-VAR-02, already a DEC-003 MVP item) already covered — it removes ambiguity
  about what "feasible" meant.
- **[Open question — must be verified before implementation]:** whether Shopify's
  `productSet` list-field delete-on-omit behaviour applies to product/variant media in
  exactly the same way it applies to variants/collections/metafields. This affects the
  exact mechanism, not the scope decided here.

### 3. Price / compare-at price clarification

**Proposed:** Phase 1 supports **core price sync and compare-at price** where available on
both systems. Explicitly:

- **Included:** base selling price and compare-at (strike-through) price, both directions
  (import and controlled export/update), travelling with the product/variant record.
- **Excluded from Phase 1:** advanced pricelist mapping, Shopify Markets pricing,
  customer-specific pricing, B2B price lists, and any currency-/market-specific pricing
  strategy — all already named as deferred in DEC-003 / `non-mvp-and-later-phases.md`; this
  clarification does not change that deferral, it only removes the "where feasible"
  ambiguity for the **base price/compare-at** item that **is** in MVP.
- **Source-of-truth requirement:** before any price export/update, the connector must make
  the **price source-of-truth explicit** per product (Odoo-authoritative vs.
  Shopify-authoritative) — this is a **new explicit requirement** this clarification adds,
  consistent with DEC-003's existing "explicit first-sync source strategy" requirement for
  product matching, extended here to price specifically because price is high-churn data
  that can silently drift if source-of-truth is left implicit.
- This replaces the DEC-003/`mvp-scope.md` **"where feasible"** wording for price/compare-at
  with the explicit split above. It does not expand price scope beyond C-PRICE-01 (already
  a DEC-003 MVP item).

### 4. First inventory push guard

**Proposed:** Phase 1 must **not** perform a **blind first inventory push** from Odoo to
Shopify. Before Odoo writes inventory quantities to Shopify for the **first time** for a
given store/binding, the connector requires **all** of:

- a **mapped Shopify location** (or an explicit "no location mapped yet, cannot push"
  block) — this is a documentation-level guardrail statement, not an AR-007 location-model
  decision;
- a **preview of SKU/variant/location quantities** that will be written, before any write
  occurs;
- **explicit operator confirmation** of that preview;
- a **recorded source-of-truth** decision (which system's quantity wins for this first
  push) — mirroring the existing DEC-003 first-sync source-strategy pattern for products;
- the **ability to skip or manual-match** ambiguous items (unmapped SKU/variant/location
  combinations) rather than forcing a guess.

This is a **scope-level guardrail statement**, not implementation code and not an AR-007
inventory-architecture decision. It sits alongside DEC-003's existing "initial Shopify
stock **import** is controlled/reviewed" statement, which covers the Shopify → Odoo
direction; this clarification adds the symmetric guard for the **Odoo → Shopify** direction
specifically, because that direction risks overwriting **live** Shopify stock (a customer-
facing storefront), which the Shopify → Odoo import direction does not.

- **Does not decide:** the exact quantity-field default (Forecast/On-Hand/Free-to-Use),
  the exact multi-location mapping mechanism, or auto-apply vs. review-then-apply for
  **ongoing** (post-first-push) syncs — all remain AR-007, not decided here.
- **Scope boundary:** this guard applies specifically to the **first** write per
  store/binding; whether every subsequent write also requires preview/confirmation, or only
  the first, is an AR-007 apply-mode question, not decided here.
- **[Open question]** The exact **granularity of "first"** is not decided by this
  clarification — candidates include first **per store**, first **per product/variant
  binding**, first **per variant/location binding**, or another AR-007-defined unit. This
  clarification requires the guard to exist at **some** granularity no coarser than
  per-store; it does **not** decide which unit, and it does **not** weaken the guard —
  whichever unit is chosen, the guard still applies before that unit's first write. Routed
  to **AR-007 / the Master Blueprint sprint**; it also does not decide ongoing (post-first-
  push) inventory apply mode, which stays a separate AR-007 question (see above).

### 5. Fulfillment customer-notification clarification

**Proposed:** Phase 1 fulfilment/tracking write-back to Shopify **is** in MVP (as DEC-003
already states), and the **customer-notification side effect must be visible and
operator-controllable**. The **default-safe behaviour is: no customer notification unless
explicitly enabled or confirmed by the operator.**

- This default is **grounded in, and consistent with, Shopify's own API default**:
  `FulfillmentInput.notifyCustomer` defaults to `false`, and
  `fulfillmentTrackingInfoUpdate`'s `notifyCustomer` argument sends no notification if left
  blank (see *Newly verified facts* above). The proposed Phase 1 default does **not**
  deviate from platform behaviour — it makes explicit, at the product-scope level, a
  default that Shopify's own API already applies, so the connector does not need to
  override the platform default to be safe.
- **Operator control requirement:** the operator must be able to see and control whether a
  given fulfilment/tracking write-back requests a customer notification — at minimum via a
  documented default-configuration surface; the exact granularity (global default vs.
  per-store vs. per-order override) is **[Open question]**, left to the Master Blueprint
  sprint / AR-008.
- **Does not decide:** the full AR-008 fulfilment architecture (FulfillmentOrder
  orchestration, multi-package/location design).

### 6. Tax / shipping / discount / payment / order-accounting clarification

**Proposed:** Phase 1 order import creates an Odoo sale order with lines, and **preserves**
tax, shipping, discount, and payment evidence **sufficiently to keep totals reconcilable**
— it does **not** silently imply full accounting automation. Explicitly:

- **Taxes:** Shopify `taxLines`/`currentTaxLines`/`totalTaxSet` are preserved as
  evidence/lines/amounts on the imported order. Phase 1 does **not** implement a general
  tax-computation or tax-reconciliation engine — Shopify-computed tax amounts are imported
  as-is, not recalculated by Odoo tax rules.
- **Shipping:** Shopify `shippingLines`/`shippingLine` are preserved as evidence/lines on
  the imported order.
- **Discounts:** Shopify `discountApplications`/`cartDiscountAmountSet` are preserved as
  evidence/amounts on the imported order.
- **Payment evidence:** Shopify financial status, payment status, gateway/method label, and
  `OrderTransaction` reference(s) where available are preserved as **source information
  only** — this reaffirms, and does not change, the existing DEC-003 Domain 9 scope.
- **Invoice policy / payment creation:** **conservative by default** —
  - **either** no automatic invoice/payment creation by default,
  - **or**, if any invoice/payment draft-artifact creation is offered at all, it is
    **opt-in**, gated behind **explicit configuration**, and behind a **total-check guard**
    (the created artifact's total must reconcile against the imported order total before
    creation proceeds).
  - Automatic posted invoices, automatic posted payments, bank reconciliation, payout
    reconciliation, full accounting workflow, gateway-specific accounting depth, and
    automatic refund accounting remain **excluded**, exactly as DEC-003 already states —
    this clarification does **not** loosen that exclusion.
- **Explicit non-goal:** this clarification does **not** authorize a general tax engine, a
  payout reconciliation feature, or automatic bank reconciliation in Phase 1.
- **Unchanged:** the existing DEC-003 "Domain 9 guard" — if RB-14/implementation planning
  finds that some draft invoice/payment artifact is **absolutely required** for a valid
  Odoo order flow, that remains architecture-dependent and returns to ChatGPT before
  implementation. This clarification does not pre-empt that guard; it only makes the
  **conservative-by-default rule** explicit for whichever mechanism is eventually chosen.
- **[Open question]** This clarification decides **that** Shopify-computed tax amounts are
  preserved as evidence/lines/amounts and are **not** silently recalculated by Odoo tax
  rules — it does **not** decide **how**: the exact mechanism for representing
  Shopify-computed tax on an Odoo sale order (e.g. how a tax line is held so Odoo's own
  tax engine does not recompute or override the imported amount), how totals stay
  reconcilable end-to-end, and how any Odoo-side recomputation is avoided or reconciled
  against the imported total are all left to the **Master Blueprint / implementation
  planning** sprint. This does **not** authorize a tax-computation engine or any
  accounting automation.

## What remains deferred

Unchanged from DEC-003 (this record does not alter any of these):

- Unrestricted autonomous bidirectional catalog ownership; customer export.
- Advanced pricelist/Markets/customer-specific/B2B pricing.
- Advanced image dedup, automated alt-text enrichment, CDN media optimization, media
  governance.
- Refund sync, cancellation reflection, returns/RMA lifecycle.
- Full accounting automation, bank reconciliation, payout reconciliation.
- Bulk Operations as a user-facing feature.
- Multi-store/multi-company UI/logic.
- Multi-package/multi-location fulfilment.

## What this unlocks

> **Conditional on acceptance — nothing below is unlocked while DEC-007 stays `Proposed
> for ChatGPT review`.**

- **If accepted**, DEC-007 lets the **Master Blueprint / implementation-planning sprint**
  design the variant-export, image/media, price-source-of-truth,
  first-inventory-push-guard, fulfilment-notification-control, and
  financial-evidence-mapping concepts against **explicit, closed** scope wording instead
  of "where feasible" ambiguity.
- The Phase 1 research-phase-exit criterion "a DEC-003 scope-hole amendment accepted"
  (`../05-qa/quality-feedback-loop.md` §10) **now has a concrete, reviewable candidate; it
  is not satisfied until ChatGPT accepts this record.**
- **If accepted**, product-doc alignment (`mvp-scope.md`, `non-mvp-and-later-phases.md`,
  `user-stories.md`) can point to a single, dated clarification record instead of leaving
  five separate ambiguities implicit — until then, those docs' existing pointer-only notes
  (added in this same sprint) stand as written, not as accepted amendments.

## What remains blocked

- **AR-004** module boundaries, **AR-006** full retry/error/idempotency taxonomy,
  **AR-007** full inventory architecture, and **AR-008** full fulfilment architecture —
  none is decided by this record.
- Exact Odoo model fields, exact database constraints, exact GraphQL operations, exact
  implementation sequence, and the Master Blueprint itself.
- **All implementation** — no code, no Odoo module, until ChatGPT opens the implementation
  gate (`CLAUDE.md` §5; `../05-qa/quality-feedback-loop.md` §10).

## Risks and mitigations

1. **Risk:** "Variant export/update is included" could be over-read as authorizing an
   unbounded write mechanism. **Mitigation:** the clarification explicitly bounds it to the
   same controlled-export rules as product-level export (preview, binding, no name-only
   match) and explicitly leaves the exact mutation mechanism to **implementation planning
   under the accepted DEC-004 / AR-002 decision** (GraphQL-first is already decided; only
   the specific variant-write mutation choice remains open).
2. **Risk:** Removing "where feasible" wording could be read as widening image/media or
   price scope. **Mitigation:** each clarification explicitly restates the excluded/deferred
   items so the net capability boundary is unchanged from DEC-003's intent — only the
   ambiguous qualifier is replaced.
3. **Risk:** A first-inventory-push guard could be read as deciding AR-007 apply-mode for
   all future syncs. **Mitigation:** the clarification is explicitly scoped to the **first**
   write only; ongoing apply-mode stays an open AR-007 question.
4. **Risk:** A fulfilment-notification default could be read as a Shopify-behaviour
   assumption without evidence. **Mitigation:** the default is grounded in two newly
   verified official facts (`FulfillmentInput.notifyCustomer` defaults to `false`;
   `fulfillmentTrackingInfoUpdate`'s `notifyCustomer` defaults to no notification), cited
   with URL and access date.
5. **Risk:** The tax/shipping/discount/payment clarification could be read as silently
   authorizing invoice/payment automation. **Mitigation:** the clarification explicitly
   requires conservative-by-default (no auto-creation, or opt-in + config + total-check
   guard) and explicitly reaffirms the existing DEC-003 accounting-automation exclusions.

## No implementation authorized

**This record does not authorize implementation.** It creates no code, no Odoo module, and
no file outside `docs/03-architecture/**`, `docs/04-decisions/**`, and the other
documentation files listed in this sprint's allowed-files list. The no-code gate
(`CLAUDE.md` §4–§5) remains in force. If this record is accepted by ChatGPT, it becomes the
Phase 1 scope-clarification addendum to DEC-003 — implementation still requires the
separate Phase 1 research-phase-exit approval and a dedicated implementation gate
(`../05-qa/quality-feedback-loop.md` §10).

## Review / change control

- **This record clarifies DEC-003's product scope wording only.** It does not decide
  architecture, does not decide AR-004/006/007/008, and does not authorize implementation.
- **If accepted:** it becomes the scope-clarification addendum for Phase 1, read alongside
  DEC-003.
- **If not accepted:** DEC-003 remains the only accepted MVP scope record, and the five
  scope holes remain exactly as DEC-003 left them (i.e. this record is withdrawn, not
  partially adopted, unless ChatGPT explicitly accepts specific sections).
- **Related:** [`DEC-003`](./DEC-003-mvp-scope.md) (the record this clarifies);
  [`DEC-004`](./DEC-004-distribution-api-auth-strategy.md) /
  [`DEC-005`](./DEC-005-sync-orchestration-strategy.md) /
  [`DEC-006`](./DEC-006-binding-dedup-identity-strategy.md) (accepted architecture this
  record assumes and does not change);
  [`../03-architecture/phase1-domain-model-brief.md`](../03-architecture/phase1-domain-model-brief.md)
  (companion domain-model brief); `../05-qa/quality-feedback-loop.md` §10 (the phase-exit
  criterion this record targets).
