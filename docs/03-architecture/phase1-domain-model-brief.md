# Phase 1 Domain Model Brief

> **Documentation-level domain-model brief, not a schema.** Produced for the **Phase 1
> Domain Model + DEC-003 Scope-Hole Closure** sprint, after PR #61 merged DEC-004/005/006
> (accepted architecture decisions for AR-002/AR-003/AR-005) into `Shopify-connector`. It
> is a companion to the proposed
> [`../04-decisions/DEC-007-phase1-scope-clarifications.md`](../04-decisions/DEC-007-phase1-scope-clarifications.md)
> and to the accepted
> [`DEC-003`](../04-decisions/DEC-003-mvp-scope.md) /
> [`DEC-004`](../04-decisions/DEC-004-distribution-api-auth-strategy.md) /
> [`DEC-005`](../04-decisions/DEC-005-sync-orchestration-strategy.md) /
> [`DEC-006`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) records.

## Status

- **Sprint:** Phase 1 Domain Model + DEC-003 Scope-Hole Closure. **Phase:** documentation
  only — the **no-code gate is in force** (`CLAUDE.md` §4–§5).
- **Precondition confirmed before authoring:** `Shopify-connector` contains PR #61's merge
  commit `26dc30109530e2566755fd93bd974284083c3922`; DEC-004/DEC-005/DEC-006 are **Accepted
  by ChatGPT** (2026-07-02); AR-002/AR-003/AR-005 are **Accepted**;
  AR-004/AR-006/AR-007/AR-008 remain **Not decided / Evidence pending**.
- **This document decides nothing** and **is not itself a decision record.** It is a
  **domain-model brief at the concept level** — it names the Phase 1 concepts, ties each to
  the accepted decisions that already govern it, and flags where the proposed
  [DEC-007](../04-decisions/DEC-007-phase1-scope-clarifications.md) clarification applies.
  It does **not** define exact Odoo model names, field lists, database constraints, GraphQL
  operations, or an implementation sequence (those remain for a later, ChatGPT-gated
  Master Blueprint / domain-model-implementation sprint).
- **This document must not become a code-level schema.** Any table below is a **concept
  map**, not a migration. Where a concrete field name is used for illustration, it is
  explicitly marked **[Illustrative — not a schema commitment]**.

## Claim classification used throughout

Per `CLAUDE.md` §8, every substantive statement below is one of:

| Label | Meaning |
| --- | --- |
| **[Accepted decision]** | Already decided by DEC-003/004/005/006, cited by section — not restated in full, not re-litigated. |
| **[Proposed clarification]** | New in this sprint, carried by the proposed [DEC-007](../04-decisions/DEC-007-phase1-scope-clarifications.md) — **not yet accepted**. |
| **[Inference]** | Our reasoning drawn from an accepted decision or cited evidence — not itself a decision. |
| **[Official fact]** | A verified Shopify/Odoo platform fact, cited with a URL and access date. |
| **[Open question]** | Unresolved; routed to a later AR row or the Master Blueprint sprint — **must be verified before implementation** if unverified. |

## What this brief explicitly does not decide

Per the sprint's boundaries, this brief does **not** decide or finalize:

- **AR-004** module boundaries/config model, **AR-006** full retry/error/idempotency
  taxonomy, **AR-007** full inventory architecture, or **AR-008** full fulfilment
  architecture (all remain **[Not decided] / Evidence pending**,
  [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)).
- Exact Odoo model names/fields, database constraints, or GraphQL operations.
- Exact implementation sequence or a Master Blueprint.
- Any change to DEC-003, DEC-004, DEC-005, or DEC-006 (all remain as accepted, unedited).

---

## 1. Store / connection domain

### Purpose

Represent one connected Shopify store/instance and prove the connection is usable, per
the accepted DEC-004 distribution/API/auth model and the DEC-003 single-store MVP scope.

### Phase 1 included concepts

- **Shopify store / instance** — the single connected store for Phase 1
  **[Accepted decision — DEC-003]** (single-store, single-company MVP; keys stay
  multi-store-safe).
- **Credential reference and masking concept** — a masked, access-controlled credential
  reference behind the non-public custom-app / offline-token model
  **[Accepted decision — DEC-004]**. Concept only: "a masked credential reference exists
  per store connection" — **[Illustrative — not a schema commitment]**: e.g. a
  `shopify_credential_ref` concept, never the raw token, never logged.
- **Scopes / readiness state** — a concept for "which scopes are granted" and "is the
  environment ready" (HTTPS/`web.base.url`, webhook reachability, worker/queue presence)
  **[Accepted decision — DEC-003 UX spine + C-CONN-05]**. Exact required-scope list is
  **[Open question]** (routed to AR-002 implementation planning).
- **Webhook readiness state** — a concept for "are the required webhook subscriptions
  registered and healthy," feeding the layered sync model **[Accepted decision — DEC-005]**.
- **Last connection test result** — a concept for "pass/fail + timestamp + reason" from the
  test-connection action **[Accepted decision — DEC-003 UX spine + C-CONN-04]**.

### Explicitly deferred

- Multi-store / multi-instance UI or logic (keys stay multi-store-safe only)
  **[Accepted decision — DEC-003]**.
- Public App-Store / OAuth-public-app flow; Billing API **[Accepted decision — DEC-004]**.
- Exact custom-app creation surface and token-acquisition mechanics (Admin-created vs.
  Partner/Dev-Dashboard) — **[Accepted decision — DEC-004]**, left to implementation
  planning.

### Binding / identity implications

The store is the **scoping dimension** every DEC-006 binding is keyed against — every
binding concept in Domain 2 below carries a store reference, even though Phase 1 has
exactly one store **[Accepted decision — DEC-006]**.

### Queue / log implications

Connection-test and readiness-check results are user-visible log/error-center entries
(Domain 8); queued jobs (Domain 8) carry the store reference so job scoping is enforced by
**explicit store scoping + record rules, never `sudo()`** **[Accepted decision — DEC-005 /
DEC-006]**.

### Data safety guardrails

- Credential masked, never logged, access-controlled by field-level `groups`
  **[Accepted decision — DEC-004]**.
- No AR-002/DEC-004 credential-handling design may rely on `sudo()` to cross store/record-
  rule boundaries **[Official fact — sourced in DEC-004/006]**.

### Open questions for later sprint

- Exact minimal-vs-full readiness-check list (AR-003-adjacent) — **[Open question]**.
- Exact custom-app creation surface / token-acquisition mechanics — **[Open question]**
  (DEC-004, left to implementation planning).
- Exact Odoo model/field shape for the connection record — **[Open question]** (Master
  Blueprint sprint).

---

## 2. Binding / identity domain

### Purpose

Give every cross-system record a single, auditable, store-scoped source of truth for
identity, per the accepted DEC-006 binding/dedup/identity strategy.

### Phase 1 included concepts

- **Store-scoped binding concept (DEC-006)** — a dedicated connector binding model (or a
  small family of them), scoped per store, storing the **Shopify GID explicitly** and the
  **Odoo model + record reference explicitly**, with per-store uniqueness constraints
  **[Accepted decision — DEC-006]**.
- **Product template binding** — Shopify product ↔ Odoo product template.
- **Product variant binding** — Shopify product variant ↔ Odoo product variant, held
  **separately** from the template binding because variants have their own Shopify GID and
  their own MVP export/update path (see Domain 3 and the
  [DEC-007 variant clarification](../04-decisions/DEC-007-phase1-scope-clarifications.md)).
- **Customer / partner binding** — Shopify customer ↔ Odoo partner, matched per DEC-003's
  match-key priority (existing binding → SKU/ref n/a for customers → email/customer keys →
  manual).
- **Order binding** — Shopify order ↔ Odoo sale order.
- **Inventory identity placeholder** — a concept only: inventory identity needs
  `inventory_item_id` **+** `location_id`, not a single product-GID binding
  **[Accepted decision — DEC-006, explicitly deferring the exact shape to AR-007]**.
- **Fulfillment / tracking identity placeholder** — a concept only: fulfilment/tracking
  identity ties to the order binding and a Shopify FulfillmentOrder/Fulfillment identity;
  exact shape is **[Open question — AR-008]**.
- **Stale / deleted / recreated handling** — a binding pointing at a deleted Shopify record
  is marked **stale**, not silently dropped; a new Shopify ID for a "same" SKU/entity must
  not silently hijack or duplicate an existing binding — it requires review
  **[Accepted decision — DEC-006]**, because **[Official fact]** GID permanence is not
  asserted by Shopify.
- **Manual match audit concept** — every binding carries **matched-by, matched-at, source
  strategy, and match key used**, plus a **status** (active/stale/manually-overridden)
  **[Accepted decision — DEC-006]**.

### Explicitly deferred

- The exact schema shape — one polymorphic binding table vs. one table per domain, precise
  column list, and constraint DDL — **[Open question — AR-005 implementation detail,
  explicitly left to the domain-model/Master Blueprint sprint by DEC-006]**.
- `AR-004` module placement of the binding model(s) — **[Not decided]**.

### Binding / identity implications

This domain **is** the binding/identity concept map; every other domain below references
it rather than restating it.

### Queue / log implications

Binding audit fields (matched-by/at/source-strategy/match-key/status) are the source for
the **duplicate-prevention preview** and the **manual-match review** surfaces
**[Accepted decision — DEC-003 / DEC-006]**; ambiguous matches route to a user-visible
review queue, never a silent auto-match.

### Data safety guardrails

- **No name-only automatic matching, ever** — name is advisory only
  **[Accepted decision — DEC-003 / DEC-006]**.
- **No blind create** — duplicate-prevention preview precedes every create/update/export
  **[Accepted decision — DEC-003]**.
- Per-store isolation enforced through explicit store scoping + record rules, never
  `sudo()` **[Accepted decision — DEC-006]**.

### Open questions for later sprint

- Exact schema shape (polymorphic vs. per-domain tables) — **[Open question — AR-005]**.
- `@idempotent` key-uniqueness scope; bulk-operation idempotency — **[Open question —
  AR-005/AR-006]**.
- GID permanence/non-reuse — **[Open question]** (not asserted by Shopify).

---

## 3. Product domain

### Purpose

Represent the Phase 1 controlled bidirectional product-onboarding path — product import
**and** controlled export/update — safely, per the accepted DEC-003 product direction and
the proposed DEC-007 variant/image/price clarifications.

### Phase 1 included concepts

- **Product template** — the Shopify product ↔ Odoo product template concept (Domain 2
  binding applies).
- **Variant** — the Shopify product variant ↔ Odoo product variant concept, **included in
  both import and controlled export/update** —
  **[Proposed clarification — DEC-007]**: variant export/update is **not optional** if
  product export/update is in MVP; see the DEC-007 variant clarification for the full
  statement.
- **Option / option value** — Shopify product options/values ↔ Odoo attribute/attribute
  value concept, imported with the variant and honouring the current Shopify variant model
  (up to 2,048 variants) **[Accepted decision — DEC-003 / C-VAR-01]**.
- **SKU / barcode / internal reference** — the MVP match-key set for product/variant
  matching (SKU/internal-reference first, then barcode; ambiguous → manual review)
  **[Accepted decision — DEC-003 / DEC-006]**.
- **Image / media MVP handling** — **[Proposed clarification — DEC-007]**: Phase 1 supports
  basic product image import/export/update at product/variant level where Shopify/Odoo
  standard fields support it; no advanced dedup/transformation/alt-text
  enrichment/CDN-optimization/media governance; preview required before destructive
  replacement/removal. Replaces the DEC-003/mvp-scope.md "where feasible" wording with an
  explicit included/excluded/deferred split — see the DEC-007 image/media clarification.
- **Price / compare-at price MVP handling** — **[Proposed clarification — DEC-007]**: Phase
  1 supports core price sync and compare-at price where available; no advanced
  pricelist/Markets/customer-specific/B2B pricing; the source-of-truth (Odoo-authoritative
  vs. Shopify-authoritative per product) must be explicit before export/update. Replaces
  the same "where feasible" wording for price — see the DEC-007 price/compare-at
  clarification.
- **Shopify status / draft export safety** — export can create drafts / stay unpublished /
  respect explicit sales-channel selection **[Accepted decision — DEC-003]**.
- **`productSet` full-state-write risk** — **[Official fact — DEC-004]** `productSet`
  reconciles **list fields** (variants, collections, metafields) by **deleting omitted
  entries**; this is the load-bearing reason the preview/dry-run guardrail is mandatory,
  not optional, for the controlled export/update path.
- **Preview / dry-run requirement** — mandatory before any destructive/full-state write on
  the product/variant export path, keyed off the Domain 2 binding
  **[Accepted decision — DEC-003 / DEC-004]**.

### Explicitly deferred

- **Unrestricted autonomous bidirectional catalog ownership** — automatic all-field
  two-way conflict resolution, a complex field-ownership matrix, advanced
  publish/channel campaign management **[Accepted decision — DEC-003, Phase 2+]**.
- Shopify Markets pricing, pricelists, per-market/customer-specific/B2B pricing, SEO/
  taxonomy, custom transforms **[Accepted decision — DEC-003, deferred]**.
- Advanced media dedup (e.g. perceptual-hash), automated alt-text enrichment, CDN/media
  optimization, media governance workflows — **[Proposed clarification — DEC-007]**,
  explicitly out of Phase 1 (weak/claim-only evidence per
  [`../02-product/non-mvp-and-later-phases.md`](../02-product/non-mvp-and-later-phases.md)).

### Binding / identity implications

Template and variant bindings are held **separately** (Domain 2) because Shopify assigns
independent GIDs to each and the controlled export/update path must diff at the variant
level, not just the template level, to avoid `productSet` delete-on-omit data loss.

### Queue / log implications

Every export/update job references its preview/diff and its binding; a failed
export/update is isolated per product (never a partial list sent to a full-state
mutation) **[Accepted decision — DEC-003 / DEC-004]**.

### Data safety guardrails

- No full-state destructive write without a rendered preview/dry-run diff.
- No blind create; binding written only after confirmation.
- Draft/unpublished/explicit-channel safety on every export.
- Image/media replacement or removal that could be destructive (e.g. omitting an existing
  image from a list-field write) requires the same preview treatment as any other
  full-state write — **[Proposed clarification — DEC-007]**.

### Open questions for later sprint

- Exact `productSet`/mutation strategy and diff-rendering mechanism — **[Open question —
  AR-002 implementation planning]**.
- Whether `productSet`'s list-field delete-on-omit behaviour extends to product/variant
  media in the exact same way as variants/collections/metafields — **[Open question — must
  be verified before implementation]**.
- Exact price source-of-truth configuration surface — **[Open question — Master Blueprint
  sprint]**.

---

## 4. Customer domain

### Purpose

Bring Shopify customers into Odoo as matched, deduplicated partners, without a second
(export) direction in Phase 1, per the accepted DEC-003 scope.

### Phase 1 included concepts

- **Customer import only in Phase 1** — Shopify → Odoo import and matching
  **[Accepted decision — DEC-003]**.
- **Customer export deferred** — Odoo → Shopify customer export stays Phase 2
  **[Accepted decision — DEC-003]**; this brief does **not** revisit that deferral.
- **Matching keys** — existing binding first, then **email** as the primary automated key;
  **name/phone are advisory/manual only**, never a sole automatic match key
  **[Accepted decision — DEC-003 / DEC-006]**.
- **Manual match** — ambiguous customer matches route to manual review, same as products
  **[Accepted decision — DEC-003]**.
- **Partner creation/update boundaries** — a customer import creates/updates a matched Odoo
  partner record only within the import direction; it does not push partner data back to
  Shopify **[Accepted decision — DEC-003]**.

### Explicitly deferred

- **Customer export (Odoo → Shopify)** — Phase 2, per DEC-003
  ([`../02-product/non-mvp-and-later-phases.md`](../02-product/non-mvp-and-later-phases.md)).
- Deep multi-address and company/B2B mapping — basic billing/shipping address only in
  Phase 1 **[Accepted decision — DEC-003]**.

### Binding / identity implications

Customer binding is a distinct binding kind in Domain 2, matched by the DEC-006 priority
(existing binding → email/customer keys → manual); it does not share a table shape
decision with product bindings (that shape question is AR-005, not decided here).

### Queue / log implications

A failed customer import is isolated and reason-coded; the linked order still reconciles
via matching, so one bad customer record does not block order import
**[Accepted decision — DEC-003 UX spine]**.

### Data safety guardrails

- No name-only automatic matching (name is advisory only).
- Protected-customer-data / PII rules respected; a no-PII-plan fallback (default customer)
  concept exists **[Accepted decision — DEC-003]**.

### Open questions for later sprint

- Default-customer fallback exact behaviour for no-PII Shopify plans — **[Open question]**.
- Final MVP match-key set (email-only vs. multi-key) — **[Open question — AR-005]**.

---

## 5. Order / sale domain

### Purpose

Import Shopify orders into Odoo sale orders as a correct, actionable representation —
preserving enough financial evidence to be useful — without silently implying full
accounting automation, per the accepted DEC-003 Domain 9 decision and the proposed DEC-007
financial-treatment clarification.

### Phase 1 included concepts

- **Shopify order import into Odoo sale order** — layered (webhook + scheduled +
  reconciliation + manual), idempotent, per DEC-005's orchestration model
  **[Accepted decision — DEC-003 / DEC-005]**.
- **Order line mapping** — Shopify order line items map to Odoo sale-order lines
  **[Accepted decision — DEC-003]**.
- **Tax line treatment** — **[Proposed clarification — DEC-007]**: Shopify order
  **`taxLines`/`currentTaxLines`/`totalTaxSet`** are preserved as evidence/lines on the
  imported order (sufficient to keep totals reconcilable); Phase 1 does **not** implement a
  general tax-computation/reconciliation engine. **[Official fact]** Shopify exposes
  `taxLines` ("A list of all tax lines applied to line items on the order, before
  returns"), `currentTaxLines`, and `totalTaxSet` on `Order`
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/Order — accessed 2026-07-02).
- **Shipping line treatment** — **[Proposed clarification — DEC-007]**: Shopify
  **`shippingLines`/`shippingLine`** are preserved as evidence/lines on the imported order.
  **[Official fact]** `shippingLines` = "The shipping methods applied to the order. Each
  shipping line represents a shipping option chosen during checkout"
  (same source, accessed 2026-07-02).
- **Discount treatment** — **[Proposed clarification — DEC-007]**: Shopify
  **`discountApplications`/`cartDiscountAmountSet`/`currentCartDiscountAmountSet`** are
  preserved as evidence/amounts on the imported order. **[Official fact]**
  `discountApplications` = "A list of discounts that are applied to the order, excluding
  order edits and refunds" (same source, accessed 2026-07-02).
- **Payment evidence treatment** — Shopify financial status, payment status,
  gateway/method label, and **`OrderTransaction`** reference(s) where available are
  preserved as source information only **[Accepted decision — DEC-003 Domain 9]**.
  **[Official fact]** `OrderTransaction` is gateway-agnostic (exists for all gateways)
  (`../01-research/shopify-official-api-notes.md`).
- **Invoice policy / payment creation boundary** — **[Proposed clarification — DEC-007]**:
  no automatic posted invoice or payment by default; if any draft-artifact creation is
  offered at all, it is opt-in, behind explicit configuration, and behind a total-check
  guard — see the DEC-007 financial-treatment clarification. This reaffirms, and does not
  loosen, the existing DEC-003 Domain 9 exclusions (no automatic posted invoices/payments,
  no bank/payout reconciliation, no full accounting workflow).
- **Cancellations / refunds / returns boundaries** — **not in Phase 1**
  **[Accepted decision — DEC-003, deferred]**; this brief does not revisit that deferral.

### Explicitly deferred

- Full accounting automation, bank reconciliation, payout reconciliation, gateway-specific
  accounting depth **[Accepted decision — DEC-003]**.
- Refund sync, cancellation reflection, returns/RMA lifecycle
  **[Accepted decision — DEC-003, deferred; idempotent-refund regression carried forward
  as a mandatory principle for the first refund/refund-sync sprint]**.
- Any general/automatic tax-computation engine — **[Proposed clarification — DEC-007]**,
  explicit non-goal.

### Binding / identity implications

Order binding (Domain 2) is the anchor for idempotent order creation — a repeated webhook
or reconciliation pass must not create a duplicate sale order
**[Accepted decision — DEC-005 / DEC-006]**.

### Queue / log implications

Order import is a queued job per DEC-005; a failed order import is isolated and retryable
without blocking other orders **[Accepted decision — DEC-003 UX spine]**; financial-evidence
fields (tax/shipping/discount/payment) travel with the order-import job payload so a
partial/failed import can be retried without re-deriving totals.

### Data safety guardrails

- Idempotent order creation — a re-processed webhook/reconciliation pass never
  double-creates an order **[Accepted decision — DEC-003]**.
- Any invoice/payment creation (if ever enabled) must be **idempotent** (no double-invoice/
  double-payment on retry) and **conservative-by-default**
  **[Proposed clarification — DEC-007]**.
- Totals-preservation is a correctness requirement: taxes + shipping + discounts + line
  totals must reconcile against the Shopify order total on import
  **[Proposed clarification — DEC-007]**.

### Open questions for later sprint

- Whether any **draft** invoice/payment artifact is absolutely required for a valid Odoo
  order flow (the DEC-003 "Domain 9 guard") — **[Open question]**, architecture-dependent,
  returns to ChatGPT before implementation if triggered.
- Exact gateway → Odoo journal mapping configuration surface — **[Open question]**.
- AR-006 idempotency-key taxonomy for order-import writes — **[Not decided]**.

---

## 6. Inventory domain

### Purpose

Write back Odoo stock levels to Shopify safely — including a guard against the very first
write ever overwriting live Shopify stock — per the accepted DEC-003 inventory scope and
the proposed DEC-007 first-push-guard clarification. Full inventory architecture stays
AR-007, not decided here.

### Phase 1 included concepts

- **Basic inventory sync in MVP** — inventory write-back is in MVP, multi-location-aware
  enough to avoid a wrong single-location design, never writing `committed`
  **[Accepted decision — DEC-003]**.
- **Direction and safety boundaries** — Odoo → Shopify write-back is the primary direction;
  Shopify → Odoo initial stock **import** is controlled/reviewed, not blind
  **[Accepted decision — DEC-003]**.
- **First-push guard** — **[Proposed clarification — DEC-007]**: before Odoo writes
  inventory to Shopify for the **first time** for a given binding, the connector requires a
  **mapped Shopify location**, a **preview of SKU/variant/location quantities**, **explicit
  operator confirmation**, a **recorded source-of-truth**, and the **ability to skip or
  manual-match ambiguous items** — see the DEC-007 first-inventory-push-guard clarification
  for the full statement.
- **Shopify location / inventory-item identity as a later AR-007 detail** — the exact
  `inventory_item_id` + `location_id` binding shape (Domain 2) is **not** decided in this
  brief; it is explicitly routed to AR-007.

### Explicitly deferred

- Auto-apply as a decided default MVP behaviour — remains an **[Inference]** routed to
  AR-007, **not** accepted as default **[Accepted decision — DEC-003 / DP-006]**.
- Full multi-location architecture beyond "location-aware enough" — **[Not decided —
  AR-007]**.

### Binding / identity implications

Inventory identity is a **placeholder concept** (Domain 2) — `inventory_item_id` +
`location_id`, not a single product-GID binding — with its exact shape explicitly deferred
to AR-007 **[Accepted decision — DEC-006]**.

### Queue / log implications

The first-push guard's preview/confirmation step is itself a logged, user-visible action
(who confirmed, when, against what source-of-truth) — **[Proposed clarification —
DEC-007]** — feeding Domain 8's audit trail.

### Data safety guardrails

- **No blind first inventory push** — the guard above is mandatory before any first write
  **[Proposed clarification — DEC-007]**.
- **`committed` must never be written**; only allowed Shopify quantity fields
  **[Accepted decision — DEC-003]**.
- Writes must be idempotent (compare-and-set / `@idempotent`-aware) per the 2026-04
  Shopify requirement on `inventorySetQuantities`/`inventoryAdjustQuantities`
  **[Official fact — DEC-003/004]**.

### Open questions for later sprint

- Default quantity field (Forecast vs. Free-to-Use vs. On-Hand) — **[Open question —
  AR-007]**.
- Auto-apply vs. review-then-apply for ongoing (post-first-push) syncs — **[Open question —
  AR-007]**; the DEC-007 first-push guard applies specifically to the **first** write, not
  a decision about steady-state apply mode.
- Full multi-location mapping mechanism — **[Not decided — AR-007]**.

---

## 7. Fulfillment domain

### Purpose

Write fulfilment/tracking updates from Odoo back to Shopify, with the customer-facing
notification side effect visible and controllable by the operator, per the accepted
DEC-003 fulfilment scope and the proposed DEC-007 notification clarification. Full
fulfilment architecture stays AR-008, not decided here.

### Phase 1 included concepts

- **Basic fulfillment/tracking update back to Shopify** — Odoo fulfilment/delivery →
  Shopify FulfillmentOrder-based mutations, single-package **[Accepted decision — DEC-003]**.
- **Tracking number / carrier / URL concept** — written via
  `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate`
  **[Official fact — `../01-research/shopify-official-api-notes.md`]**.
- **Customer-notification side effect** — **[Proposed clarification — DEC-007]**: Phase 1
  fulfilment/tracking write-back to Shopify is in scope; the customer-notification side
  effect must be **visible and operator-controllable**; the **safe default is no customer
  notification unless explicitly enabled or confirmed**. This is grounded in
  **[Official fact]**: Shopify's `FulfillmentInput.notifyCustomer` field — "Whether the
  customer is notified. If `true`, then a notification is sent when the fulfillment is
  created" — **defaults to `false`**
  (https://shopify.dev/docs/api/admin-graphql/latest/input-objects/FulfillmentInput —
  accessed 2026-07-02); and `fulfillmentTrackingInfoUpdate`'s `notifyCustomer` argument —
  "If this field is left blank, then notifications won't be sent to the customer when the
  fulfillment is updated" — also defaults to no notification
  (https://shopify.dev/docs/api/admin-graphql/latest/mutations/fulfillmentTrackingInfoUpdate
  — accessed 2026-07-02). The proposed Phase 1 default (no notification unless explicit)
  **matches** Shopify's own API default — it is a conservative default, not a deviation
  from platform behaviour.

### Explicitly deferred

- Multi-package / multi-location fulfilment split shipments
  **[Accepted decision — DEC-003, deferred to a named later phase — C-FUL-02]**.
- Full AR-008 fulfilment architecture (FulfillmentOrder orchestration design,
  accept/reject flows for fulfilment-service apps) — **[Not decided]**.

### Binding / identity implications

Fulfilment/tracking identity is a **placeholder concept** (Domain 2), tied to the order
binding; its exact shape (e.g. FulfillmentOrder/Fulfillment identity vs. order-level
identity) is **[Open question — AR-008]**.

### Queue / log implications

Every fulfilment write-back job records **whether customer notification was requested**
(true/false) as a first-class, user-visible field on the job/log entry — **[Proposed
clarification — DEC-007]** — so the operator can see and audit what was sent, not just
that a write succeeded.

### Data safety guardrails

- **Safe default: no customer notification unless explicitly enabled or confirmed**
  **[Proposed clarification — DEC-007]**.
- The operator must be able to see and control the notification setting per write-back (or
  per a documented default-configuration surface) — **[Proposed clarification — DEC-007]**;
  exact configuration granularity (global default vs. per-store vs. per-order override) is
  **[Open question — Master Blueprint sprint / AR-008]**.
- Fulfilment writes must be idempotent — no duplicate fulfilment record from a retried
  write **[Accepted decision — DEC-003]**.

### Open questions for later sprint

- Exact configuration granularity for the notification default (global vs. per-store vs.
  per-order) — **[Open question]**.
- Full AR-008 fulfilment design (FulfillmentOrder orchestration, multi-package/location) —
  **[Not decided]**.

---

## 8. Queue / log / error domain

### Purpose

Give every Phase 1 sync action (product, customer, order, inventory, fulfilment) a
minimum, uniform job/log concept, per the accepted DEC-005 orchestration model. Full
retry/error taxonomy stays AR-006, not decided here.

### Phase 1 included concepts

- **Minimum job concept (DEC-005)** — every unit of sync work (webhook-triggered, manual,
  scheduled, or reconciliation-triggered) is represented as a queued job/record, never
  processed inline in a request **[Accepted decision — DEC-005]**.
- **Job source** — webhook / manual / scheduled / reconciliation, recorded on every job
  **[Accepted decision — DEC-005]**.
- **Job state** — a concept for queued/processing/done/failed/dead-final-failed
  **[Accepted decision — DEC-005]**.
- **Retry count** — every job record carries a retry counter
  **[Accepted decision — DEC-005]**.
- **Error class / message** — a reason-coded, human-readable failure description, not a
  raw stack trace **[Accepted decision — DEC-003 UX spine]**; the **full taxonomy** of
  error classes is **[Not decided — AR-006]**.
- **Related store / binding / record** — every job references its store (Domain 1), its
  binding if applicable (Domain 2), and the business record it acted on, so a failure can
  be traced and retried in context **[Accepted decision — DEC-005 / DEC-006]**.
- **User-visible log / error-center concept** — a recovery-first surface where every
  failure shows its record, reason, and a safe retry action
  **[Accepted decision — DEC-003 UX spine]**.

### Explicitly deferred

- Full AR-006 retry/error/idempotency taxonomy (which error classes auto-retry vs. need a
  human, backoff schedule, idempotency-key mechanism beyond the binding) —
  **[Not decided — AR-006, explicitly out of scope for this brief]**.
- Full reconciliation cadence/scope design — **[Not decided — AR-003 implementation
  planning / AR-006]**.

### Binding / identity implications

Job records reference the Domain 2 binding they act on (where applicable), so the
duplicate-prevention preview, the first-inventory-push guard (Domain 6), and the
fulfilment-notification setting (Domain 7) are all **traceable through the same job/log
concept**, not separate ad hoc mechanisms.

### Queue / log implications

This domain **is** the queue/log/error concept map; every other domain above references
it rather than restating it.

### Data safety guardrails

- Per-record isolation — one failed record never blocks a batch
  **[Accepted decision — DEC-005]**.
- A **dead/final-failed state** prevents a job from retrying forever or silently vanishing
  **[Accepted decision — DEC-005]**.
- `ir.cron`'s own coarse deactivation is **not** the retry mechanism — the connector's job
  model owns retry/backoff itself **[Accepted decision — DEC-005]**.

### Open questions for later sprint

- Full retry/error-class taxonomy — **[Not decided — AR-006]**.
- Reconciliation cadence and scope (per-object vs. global) — **[Open question — AR-003
  implementation planning / AR-006]**.
- Exact job/log Odoo model shape — **[Open question — Master Blueprint sprint]**.

---

## Review notes for ChatGPT / Fable

Please review specifically:

1. **Altitude** — does each domain section stay at the documentation/concept level, or does
   any part read as a code-level schema (field names, table names, constraints)? Every
   concrete name used is marked **[Illustrative — not a schema commitment]**; flag any that
   is not.
2. **Classification discipline** — does every clarification-carrying statement correctly
   cite **[Accepted decision]** vs. **[Proposed clarification]** vs. **[Inference]** vs.
   **[Open question]**, with no proposed clarification presented as already accepted?
3. **Scope-hole coverage** — do Domains 3 (product), 6 (inventory), 7 (fulfilment), and 5
   (order/sale) correctly carry the five known MVP-scope holes (variant export; image/media
   + price wording; first inventory push guard; fulfilment customer-notification default;
   tax/shipping/discount/payment treatment) without silently deciding AR-002/006/007/008?
4. **New Shopify facts** — the `taxLines`/`shippingLines`/`discountApplications` and
   `FulfillmentInput.notifyCustomer`/`fulfillmentTrackingInfoUpdate.notifyCustomer` facts
   are newly verified this sprint (2026-07-02) via a small, targeted official-source check
   (per the sprint's external-research rule) and are **not yet propagated** into
   `../01-research/shopify-official-api-notes.md` (out of this sprint's allowed-files
   list) — confirm whether a future sprint should do that propagation.
5. **No AR-004/006/007/008 decision** — confirm nothing above reads as deciding module
   boundaries, the full retry taxonomy, the full inventory architecture, or the full
   fulfilment architecture.

> **This brief decides nothing.** Every domain concept is an **input** for the gated
> Master Blueprint sprint, subject to ChatGPT review (`CLAUDE.md` §4–§5, §8–§10).
> **Implementation remains blocked.**
