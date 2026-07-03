# Master Blueprint — Part B: Product, Customer, and Sale/Order Domain Blueprint

> **Master Blueprint Sprint B deliverable** for the premium **Odoo 19 ↔
> Shopify Connector**. Detailed, implementation-ready **blueprint** for the
> product, customer, and sale/order domains — still **documentation only, no
> code**. Companion index: [`master-blueprint.md`](./master-blueprint.md).
> Companion core substrate (Part A):
> [`master-blueprint-core-substrate.md`](./master-blueprint-core-substrate.md).
> Companion open-questions register:
> [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md).
> Companion decision record:
> [`../04-decisions/DEC-014-master-blueprint-product-customer-sale.md`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md)
> (Status: **Accepted by ChatGPT**, 2026-07-03).

## Status

**Accepted by ChatGPT via DEC-014.** Acceptance date: **2026-07-03**.
Documentation only — the no-code gate (`CLAUDE.md` §4–§5) is in force.
**This blueprint does not authorize implementation.** It builds on the
**accepted** Part A core/common substrate (DEC-013) and the **accepted**
DEC-003, DEC-006, DEC-007, DEC-012 decisions. See
[`DEC-014`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md)
"Accepted decision" for the accepted package and the explicit acceptance
points (including the Fable B1/B2 routes and the MBQ-23/25/26/29/30/31/59
outcomes, §J below).

## Claim labels used throughout

Same discipline as Part A (`master-blueprint-core-substrate.md` "Claim
labels used throughout"):

- **[Accepted — DEC-0XX]** — restates an already-accepted decision, cited.
  Not re-litigated here.
- **[Accepted — DEC-013]** — restates a Part A design point DEC-013 already
  accepted.
- **[Accepted — DEC-014]** — a design detail this document introduced that
  DEC-014 explicitly accepted (blueprint level or blueprint-policy level,
  as stated); see DEC-014 "Accepted decision" points A–J for the full
  list. **[Blueprint proposal]** items not explicitly named in DEC-014's
  accepted package (item 1–6) or explicit acceptance points remain design
  detail this document introduces at blueprint level, accepted as part of
  the whole-document acceptance but with no exact implementation choice
  fixed — MBQ/implementation-planning open questions cited alongside each
  remain open regardless of label.
- **[Blueprint proposal]** — a design detail this sprint introduces, now
  part of the accepted Part B blueprint (DEC-014), unless a specific
  paragraph is explicitly still open (an **[Open question — MBQ-nn]**
  tag) or is one of DEC-014's "still open" items (§J below).
- **[Official fact]** — a verified Shopify/Odoo platform fact, cited with a
  URL and access date. New facts verified for this sprint are dated
  **2026-07-03**.
- **[Inference]** — reasoning from cited accepted decisions/evidence.
- **[Open question — MBQ-nn]** — unresolved; carried in
  [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md).

**Naming discipline (unchanged from Part A):** all model/field/group names
below are **proposed naming directions only** — not committed Odoo
identifiers. Exact model/field names remain **[Open question —
MBQ-01/02/55]** for implementation planning.

---

## Scope and non-goals

**In scope:** the product, customer, and sale/order domain blueprints —
detailed enough for later implementation planning, converting **accepted**
DEC-003 (MVP scope), DEC-006 (binding/dedup), DEC-007 (Phase 1 scope
clarifications), DEC-012 (UX/operator-flow), and the **accepted** DEC-013
core substrate into domain-level flows, concepts, job types, and error/retry
mappings.

**Explicit non-goals (per the sprint prompt and `CLAUDE.md` §5):**

- No connector code, Odoo module, model, view, controller, security file,
  manifest, test, or CI file.
- No exact GraphQL mutation body is finalized unless official-doc evidence
  is verified and cited (see *Newly verified facts* under each domain); any
  unverified mutation behaviour stays an **MBQ**, never an assertion.
- No autonomous bidirectional catalog conflict ownership; no name-only
  matching; no blind create; no destructive write without preview — all
  **unchanged, non-negotiable** guards from DEC-003/DEC-006/DEC-007.
- No Shopify Markets, metafields, SEO/taxonomy, subscriptions, gift cards,
  POS, or B2B in Phase 1 (unchanged DEC-003 deferral).
- No customer export in Phase 1 (unchanged DEC-003 deferral) unless
  explicitly re-decided later.
- No invoice/payment posting automation in Phase 1 (unchanged DEC-003/
  DEC-007 §6 exclusion) unless a later DEC explicitly changes it.
- No accounting, refund, payout, or inventory/fulfillment blueprinting —
  those remain Sprint C (inventory/fulfillment, not started) and out of
  scope here entirely.
- No screen-level UI/UX design or wireframes — Part D (UI/UX Screen Design
  Blueprint, MBQ-53) remains a separate, not-started sprint. Domain
  concept/contract-level blueprinting (this document) does not require
  Part D first, per `master-blueprint.md`'s "does not block Part B/C
  domain-blueprint authoring" rule.
- **Implementation remains blocked** under every outcome of this review
  (see *Implementation remains blocked* below).

## Relation to accepted decisions

| Accepted record | What it fixed | How this blueprint uses it |
| --- | --- | --- |
| [DEC-003](../04-decisions/DEC-003-mvp-scope.md) | Controlled bidirectional product onboarding; customer import-only; order import with minimal financial evidence; no blind create; no name-only matching; no autonomous bidirectional catalog ownership | Scope boundary for every section below |
| [DEC-006](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) | Store-scoped binding source of truth; match-key priority (existing binding → SKU/internal reference → barcode → email/customer keys → manual); no name-only automatic matching | Product/variant/customer/order binding and matching sections |
| [DEC-007](../04-decisions/DEC-007-phase1-scope-clarifications.md) | Variant export/update boundary; image/media boundary; price/compare-at boundary + source-of-truth requirement; first-inventory-push guard (not this domain); fulfilment notification default (not this domain); tax/shipping/discount/payment-evidence treatment; conservative invoice/payment policy | Product §A.5/§A.13/§A.14; Order §C.7–§C.11 |
| [DEC-012](../04-decisions/DEC-012-ux-operator-flow-strategy.md) | Product flow (§7): mandatory preview, draft-first export, source-of-truth visibility; Matching flow (§6): binding→SKU→barcode→email/customer-key→manual, duplicate-prevention preview | Product §A.9/§A.10/§A.16; Customer §B.3/§B.9; cross-cutting manual-review posture |
| [DEC-013](../04-decisions/DEC-013-master-blueprint-core-substrate.md) | Accepted Part A core substrate: binding contract (§C.8), job/log/error abstraction (§D), error-class registry (16 classes), operator surfaces (§E–§H), feature-flag mechanism (§I), access blueprint (§J), cross-module rules (§K) | Every domain section below builds on, and does not duplicate, this substrate — see §E "Job/log/error/retry usage through core" |

AR-002 through AR-010 are all **Accepted**
([`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md));
RA-001 through RA-023 are **binding rejected approaches**
([`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md))
— checked before drafting; none is reintroduced by this blueprint.

## Module ownership (restated for orientation, DEC-008-authoritative)

Per the accepted DEC-008 module family, restated at
[`master-blueprint.md`](./master-blueprint.md) "Module family overview"
**[Accepted — DEC-008; DEC-013]**:

- **`shopify_connector_product`** owns the **product and variant** domain —
  product/variant import, controlled export/update, product/variant binding
  responsibility (§A.8).
- **`shopify_connector_sale`** owns **both** the **customer** domain
  (import/matching, folded in for Phase 1 — §B.8) **and** the **order**
  domain (import, financial-evidence capture, total-check guard). `sale`
  resolves product/variant bindings **through** `product` (§K.9 in Part A:
  "sibling reuse via `product`"), never duplicating product-matching logic,
  but owns its **own** customer and order bindings directly.
- Neither module depends on `inventory` or `fulfillment` (Sprint C,
  siblings on `core` + `product`/`sale`); this sprint does not touch either.

---

## A. Product domain blueprint

### A.1 Module and binding ownership

`shopify_connector_product` owns product/variant import, export, update,
and binding responsibility **[Accepted — DEC-008]**. Per the accepted Part
A binding shape (§C.8, resolving MBQ-11), `product` defines **two**
concrete binding models extending the core abstract binding contract:
**product-template binding** (Shopify Product ↔ Odoo product template) and
**product-variant binding** (Shopify ProductVariant ↔ Odoo product
variant), held **separately** because Shopify assigns independent GIDs to
each and the controlled export/update path must diff at the variant level,
not just the template level, to avoid `productSet` delete-on-omit data loss
**[Accepted — DEC-006; phase1-domain-model-brief.md Domain 3]**. Exact
Odoo model/field names: **[Open question — MBQ-01/02/55]**.

### A.2 Product import (Shopify → Odoo)

- **Trigger:** webhook (product create/update webhook topics — exact
  topic strings are **not verified/cited this sprint**; any illustrative
  topic name is not an official-doc claim; exact topic-string
  verification and registration is a `core` seam, §A.5.7 of Part A, and
  is routed to implementation planning), scheduled sync, manual sync, or
  reconciliation — never webhook-only **[Accepted — DEC-005 layered
  sync]**.
- **Flow:** for each new/changed Shopify product, the matching flow (§A.6)
  runs binding-first, then SKU/internal-reference, then barcode
  **[Accepted — DEC-003; DEC-006]**. A confident match links to the
  existing Odoo product/variant; a confident no-match candidate is
  eligible to create a new Odoo product template + variant(s). **That
  product import creates/matches records at all is the accepted DEC-003/
  DEC-006 capability — but whether and how that create/bind happens
  automatically, without a synchronous per-record preview, is the
  proposed MBQ-59 policy below, not itself already accepted.** See the
  "Automated create/bind policy" bullet for the gate that must pass
  before an automated create/bind proceeds.
- **What travels with the import:** template/variant identity, options/
  variant structure (§A.5), SKU/barcode, basic image/media (§A.13), base
  price/compare-at (§A.14) **[Accepted — DEC-003 "Shopify → Odoo
  (import)"]**.
- **First-sync source strategy:** the operator's recorded choice (Shopify-
  source / Odoo-source / both-match-first, §B.6 of Part A) governs how
  import behaves when Odoo already has a product that could match — this
  is a **setup-time** decision, not decided per-import
  **[Accepted — DEC-003; DEC-006; Part A §B.6]**.
- **Automated create/bind policy — accepted at blueprint-policy level by
  DEC-014, tracked as MBQ-59:** retrospective sync-center/dashboard
  visibility (Part A §F/§G) is **audit/log visibility only** — it is not
  a preview,
  and it does **not** by itself satisfy DEC-003/DEC-006's "duplicate-
  prevention preview... precedes every create/bind action; no blind
  create" requirement. This document's earlier wording read retrospective
  visibility as satisfying that requirement; that reading is withdrawn.
  Instead, for an automated (webhook/scheduled/reconciliation-triggered)
  import, the connector runs a **pre-create duplicate check** (the
  ordinary match-key sequence, §A.6) *before* creating or binding
  anything, gated by two distinct condition groups — using **accepted
  Part A per-class routing**, not a single blanket `blocked_manual_review`
  fallback:

  **Eligibility conditions** (must all hold before the job is even
  considered for auto-create; a failure here means the job is not
  eligible to run at all, not that it needs operator confirmation of a
  candidate):
  1. store setup is complete (Part A §E.4/§E.5 — a business sync/write
     job is **not enqueueable** for a store whose setup is incomplete;
     this is an enqueue-time block, not a manual-review state);
  2. the product domain is enabled for the store (Part A §I.1/§I.3/§I.4 —
     a disabled domain blocks new jobs from enqueue/execution; an
     already-queued job for a disabled domain is either **cancelled**
     with an audit reason, per the accepted `cancelled` job state
     (§D.3/§D.9), or held in an accepted blocked state per implementation
     planning — not, by this alone, a `blocked_manual_review` case);
  3. the recorded first-sync source strategy permits import-side creation
     for this record (Part A §B.6 — if the strategy forbids import-side
     creation, the create simply does not proceed; a configuration
     outcome, not a manual-review sub-reason).

  **Match-quality conditions** (govern whether the specific candidate is
  safe to auto-create/auto-bind):
  4. the candidate is either a **confident, unambiguous match to an
     existing Odoo record**, or a **confident no-match creation
     candidate** (the pre-create duplicate check found no plausible
     existing candidate, so creating a new record is safe) — in either
     case there is no second plausible candidate under consideration;
  5. no `ambiguous match`, `binding conflict`, `duplicate risk`, or
     `destructive-write guard blocked` condition is triggered (Part A
     §D.4) — **these four are exactly the confirmation-required classes
     this create/bind path can hit**, and only these route the job to
     `blocked_manual_review` with the matching sub-reason (Part A
     §D.5.4/§D.8);
  6. the create/bind action, once it proceeds, is logged with full
     before/after detail via the job/log audit trail (Part A §D.10) and,
     for the binding itself, the binding audit fields — matched-by,
     matched-at, source strategy, match key used, status (Part A §C.4).

  **Routing on failure — per-class, not collapsed into one state:** a
  failed **eligibility** condition (1–3) means the job is not run at all
  — not enqueued (§E.5), or an already-queued job cancelled with an
  audit reason or held per the accepted domain-disable mechanics (§I.4) —
  **never** presented as a `blocked_manual_review` confirmation case,
  since nothing here needs an operator's confirmation of a *specific
  candidate*. A failed **match-quality** condition (5) is exactly one of
  the six accepted `blocked_manual_review` confirmation-required
  sub-classes (§D.5.4/§D.8) and routes there with its specific sub-reason,
  unchanged from the already-accepted taxonomy. **This document does not
  widen Part A §D.8's confirmation-required sub-reason vocabulary** —
  every routing above uses an existing, already-accepted class and state.

  This **pre-create check**, gated and routed as above — not the
  sync-center's later display of the outcome — is what satisfies "no
  blind create" for the automated path. **[Accepted — DEC-014, at
  blueprint-policy level; MBQ-59 — the gate mechanism and its Part A
  per-class routing are accepted; exact eligibility-check/match-
  confidence implementation detail remains open for implementation
  planning]**. This policy applies identically to Customer §B.2, stated
  once here and cross-referenced there. **Interactive/batch import and
  export (a manual matching session, a bulk catalog-onboarding pass, or
  any operator-triggered export/update, §A.3/§A.9) are unaffected — they
  still require a blocking, synchronous preview before the operator
  confirms any create/bind/write.**

### A.3 Product export (Odoo → Shopify)

- **Trigger:** manual export action (Phase 1 default — an explicit operator
  action, not an automatic Odoo-write-triggered push, since DEC-003 scopes
  product export as "controlled," not autonomous) **[Inference — DEC-003
  "controlled bidirectional product onboarding," never "autonomous"]**.
  Whether a later, still-controlled trigger (e.g. an explicit per-product
  "keep in sync" flag checked at Odoo-side save) is offered is
  **[Open question — implementation planning, not decided here]** — it
  would still require the same preview/guard treatment below, so it is a
  trigger-mechanism question, not a scope question.
- **Flow:** duplicate-prevention preview → destructive-write preview/diff
  (§A.11) → draft-first write (§A.10) → binding created/confirmed after
  the write succeeds **[Accepted — DEC-003; DEC-004; DEC-006]**.
- **Scope:** product export, product update, variant export/update
  (§A.5), basic image/media export/update (§A.13), base price/compare-at
  export/update (§A.14) **[Accepted — DEC-003; DEC-007 §1–§3]**.
- **What export never does:** silently decide "which side wins" for a
  field both systems changed (autonomous bidirectional conflict
  resolution) — explicitly out of Phase 1 **[Accepted — DEC-003
  non-goals]**.

### A.4 Product update flow after first binding

- A bound product/variant becomes **eligible** for an update job only
  after an **explicit operator action** — the same manual export/update
  trigger as §A.3 — or, if a later sprint/implementation-planning phase
  accepts a specific controlled trigger mechanism (e.g. an explicit
  per-product "keep in sync" opt-in checked at Odoo-side save — still an
  **[Open question — implementation planning, not decided here]**, see
  §A.3), that accepted mechanism. **Ordinary Odoo record writes do not,
  by themselves, queue a Shopify update job** — this section does not
  imply autonomous Odoo-write-triggered pushing, and this wording
  corrects any earlier reading of this section that it did
  **[Inference — DEC-003's "controlled," never "autonomous," product-
  export scope, restated from §A.3; the trigger table in §D.7 is
  unaffected and already states product export/update is manual-only]**.
- Once an update job is triggered (by whichever mechanism above applies),
  it renders a diff (what will change: fields, images, price) before
  writing, keyed off the binding **[Accepted — DEC-004 UX implications;
  DEC-012 §7.3]**.
- **Mutation choice for updates** follows the same strategy fork as export
  (§A.5.2) — a template/list-field-only change may use a narrower mutation
  than a full resync; both remain gated by the same preview
  **[Blueprint proposal, extending §A.5.2]**.
- A binding whose Shopify counterpart is deleted or recreated is handled
  per Part A §C.6 (marked stale / routed to review, never silently
  re-created or hijacked) **[Accepted — DEC-006]**.

### A.5 Variant and option handling

1. **Scope [Accepted — DEC-007 §1]:** variant export/update **is included**
   in Phase 1 controlled export/update — not optional if product
   export/update is in MVP. Bounded to the current Shopify product/variant
   model (up to 2,048 variants); no legacy/deprecated variant model
   support. Options/option values map to Odoo attribute/attribute values,
   imported with the variant **[Accepted — DEC-003; phase1-domain-model-
   brief.md Domain 3]**.
2. **Mutation strategy — newly verified evidence and proposed direction
   (partially resolving MBQ-23):**
   - **[Official fact]** `productSet`'s reference page states it is used
     "to sync information from an external data source into Shopify,
     manage large product catalogs, and perform batch updates," and its
     `ProductSetInput` accepts a `variants` field — `productSet` **can**
     create/update variants as part of a whole-product write.
     (`https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet`,
     accessed 2026-07-03.)
   - **[Official fact]** `productSet` reconciles **list fields** — creating,
     updating, and **deleting entries not included in the mutation's
     input** — and its documentation names `collections`, `metafields`,
     and `variants` as "common examples" of list fields.
     (Same source, accessed 2026-07-03.) This confirms, at the official-doc
     level, that a `productSet` write **omitting** a variant deletes it —
     the exact risk DEC-004's "Data-safety implications" already treats as
     load-bearing for the mandatory preview guard.
   - **[Official fact]** `productVariantsBulkCreate` "creates multiple
     product variants for a single product in one operation"
     (`https://shopify.dev/docs/api/admin-graphql/latest/mutations/productVariantsBulkCreate`,
     accessed 2026-07-03). **[Official fact]** `productVariantsBulkUpdate`
     "updates multiple product variants for a single product in one
     operation," and can run "directly or as part of a bulk operation for
     large-scale catalog updates"; it also exposes an `allowPartialUpdates`
     argument (default `false`) governing per-variant error tolerance
     ("valid variant changes may be persisted even if some of the
     variants updated have invalid data") — an error-handling behaviour,
     not a field-reconciliation or idempotency behaviour
     (`https://shopify.dev/docs/api/admin-graphql/latest/mutations/productVariantsBulkUpdate`,
     accessed 2026-07-03). **Neither mutation's reference page states a
     list-field/delete-on-omit reconciliation behaviour, and neither
     states an idempotency guarantee** — both pages were checked and are
     silent on both topics. **Absence of a stated behaviour is not a
     confirmed absence of the behaviour** — this is not asserted as "safe
     from delete-on-omit" or "idempotent," only as "not documented to
     have either."
   - **[Accepted — DEC-014, partially resolving MBQ-23 — direction only,
     not implementation-final]:**
     prefer `productVariantsBulkCreate`/`productVariantsBulkUpdate` for
     **variant-only** additions/updates after first export (narrower
     blast radius than a whole-product `productSet` write); use
     `productSet` for the **first-time combined** product+variant export
     and for any **explicit, operator-confirmed full-state resync** (where
     Odoo is meant to become fully authoritative, including deletion of
     Shopify-side list-field entries absent from Odoo). Both paths remain
     gated by the same destructive-write preview (§A.11) regardless of
     which mutation is chosen — the guard does not depend on resolving
     this question. Exact implementation choice, batching, and error
     handling remain **[Open question — MBQ-23, partially resolved]**.
3. **No unsupported direction:** the setup wizard (Part A §E.7) never
   offers a sync direction DEC-003 does not accept.

### A.6 SKU/internal reference and barcode matching

Match-key priority for product/variant matching: **existing binding →
SKU/internal reference → barcode → manual match**; name is advisory only,
never automatic **[Accepted — DEC-003; DEC-006 "Match-key priority"; RA-006]**.
Ambiguous matches (more than one plausible candidate) route to manual
review; a duplicate-risk create is blocked pending confirmation
**[Accepted — DEC-006; DEC-009 error taxonomy]**. This is the product-side
instance of the general binding/dedup abstraction in Part A §C — nothing
here weakens or reinterprets it.

### A.7 Product template vs. product variant identity

Template and variant identity are **held separately** (§A.1) — a template
binding does not stand in for its variants' bindings, and a variant's
identity (SKU, barcode, Shopify ProductVariant GID) is independent of its
parent template's identity. This separation is the reason the export/update
diff must be rendered **at the variant level**, not only the template level
— a template-only diff would miss a variant-level `productSet` delete-on-
omit risk **[Accepted — DEC-006; phase1-domain-model-brief.md Domain 3]**.

### A.8 Product binding responsibility

Binding responsibility for both product-template and product-variant
identity rests with `shopify_connector_product` **[Accepted — DEC-008;
master-blueprint.md module family overview]**. `sale` and `inventory`
(Sprint C) resolve product/variant bindings **through** `product` — neither
duplicates product-matching logic (Part A §K.9) **[Accepted — DEC-008]**.

### A.9 Duplicate-prevention preview

An interactive or batch create/bind action (e.g. first-sync review, a
manual matching session, a bulk catalog-onboarding pass) always shows a
**blocking preview** ("will create N, link M, N ambiguous") *before* the
operator confirms the create/bind — this is unweakened DEC-003/DEC-006
behaviour **[Accepted — DEC-003; DEC-006]**. For an **automated**
(webhook/scheduled/reconciliation-triggered) create/bind, the §A.2
pre-create policy (the eligibility + match-quality gate, routed per
Part A's accepted per-class mechanisms — not a single collapsed state) is
the mechanism that satisfies "no blind create" — **not** the sync-center/
dashboard's later display of the job's outcome, which is **audit/log
visibility only**, shown *after* the action, and is never a substitute
for a preview **[Accepted — DEC-014, at blueprint-policy level — see
§A.2 for the full policy; MBQ-59]**. No blind create, under either path.

### A.10 Draft-first export safety

- **Scope decision [Accepted — DEC-003; DEC-012 §7.9]:** where Shopify
  supports a draft/unpublished product state, a first-time export defaults
  to draft/unpublished rather than immediately live, so the operator can
  review on Shopify before the product goes live.
- **Mechanism — newly verified evidence, resolving MBQ-25 at
  blueprint-direction level:**
  - **[Official fact]** `Product.status` is an enum with values `active`
    (the default filter value), `archived`, `draft`, and `unlisted`; Shopify
    "only displays products with an `ACTIVE` status in online stores, sales
    channels, and apps."
    (`https://shopify.dev/docs/api/admin-graphql/latest/objects/Product`,
    accessed 2026-07-03.)
  - **[Official fact]** "The `productCreate` mutation creates products in
    an unpublished state by default, so you must perform a separate
    operation to publish the product." Publishing is a distinct action —
    the
    [`publishablePublish`](https://shopify.dev/docs/api/admin-graphql/latest/mutations/publishablePublish)
    mutation — "used to publish the product and make it available to
    customers," tied to the `publishedAt` field and the product's
    `resourcePublications` (the list of sales-channel publications a
    product is published to). (Same source, accessed 2026-07-03.)
  - **[Accepted — DEC-014, partially resolving MBQ-25 at
    blueprint-direction level]:**
    a first-time controlled export creates the product with **`status:
    DRAFT`** (or relies on `productCreate`'s unpublished-by-default
    behaviour) and **does not** call `publishablePublish` — the product
    exists in Shopify admin but is not live on any sales channel until the
    operator explicitly confirms and the connector calls
    `publishablePublish` for the operator-selected channel(s). This
    matches DEC-003's "draft/unpublished/channel-controlled safety"
    wording precisely: **draft** (`status: DRAFT`) and **unpublished**
    (no `publishablePublish` call) are two distinct, composable
    mechanisms, both available. **Exact channel-selection UX and whether
    `status` or publication-state (or both) is the primary safety lever
    for a given export** remain **[Open question — MBQ-25, implementation
    planning]**.

### A.11 Destructive-write preview / guard

Mandatory before any destructive/full-state write on the product/variant
export path, keyed off the binding **[Accepted — DEC-003; DEC-004]**. This
is the product-domain instance of Part A §I.5's structural rule ("no
feature flag, setting, or configuration combination may bypass... the
destructive-write preview"). The preview renders, before any write: fields
that will change, images that will be replaced/removed, price changes, and
— per §A.5.2's newly verified evidence — which variants (if any) a
`productSet` write would **delete** by omission **[Accepted — DEC-004
"Data-safety implications"; newly verified §A.5.2 evidence]**.

### A.12 Source-of-truth choices

| Field | Source-of-truth requirement | Basis |
| --- | --- | --- |
| Product attributes / variant structure | Follows the setup-time first-sync source strategy (Shopify-source / Odoo-source / both-match-first) — no separate per-field source-of-truth for variant structure itself | **[Accepted — DEC-006; Part A §B.6]** |
| Product title / name | Follows the first-sync source strategy; name is never an automatic match key regardless of source strategy | **[Accepted — DEC-006; RA-006]** |
| SKU / barcode | Authoritative match keys once bound; if a SKU/barcode changes after binding, the **binding** remains authoritative and the key change is detected/reconciled, not silently re-matched | **[Accepted — DEC-006 "Data-safety implications"]** |
| Price / compare-at price | **Explicit, per-product, before any export/update** — Odoo-authoritative or Shopify-authoritative; export/update **blocks** rather than assumes a default when not yet set | **[Accepted — DEC-007 §3; DEC-012 §7.6]** |
| Image / media | No separate source-of-truth setting; follows the same preview-gated basic import/export/update boundary as §A.13 | **[Accepted — DEC-007 §2]** |

Every source-of-truth choice is persisted (Part A §B.6), auditable (Part A
§D.10), and — per Part A §D.13 — preserved across retries (a retried job
never silently re-reads a since-changed source-of-truth).

### A.13 Product media/image basic handling

**[Accepted — DEC-007 §2]** — basic product image import/export/update at
product/variant level, where Shopify's and Odoo's standard image/media
fields support it. **Included:** basic import (Shopify → Odoo) and basic
export/update (Odoo → Shopify), preview before any destructive replacement
or removal. **Excluded from Phase 1:** advanced image dedup (pHash),
automated alt-text enrichment, CDN-level transformation/optimization, any
dedicated media-governance workflow — none of these is introduced by this
sprint. **Mechanism (carried forward, open — MBQ-24, unchanged from register):**
whether `productSet`'s list-field delete-on-omit behaviour extends to
media the same way it applies to `variants`/`collections`/`metafields` is
**still not confirmed** — this sprint's official-doc check
(`productSet` reference page, accessed 2026-07-03) found media **not
named** among the page's "common examples" of list fields, but the page
also does not exclude media. **Blueprint safety posture (does not depend on
resolving the mechanism):** every product/variant media write that could
omit an existing image from a list-field-shaped write is treated with the
**same destructive-write preview** (§A.11) DEC-007 §2 already mandates for
"any destructive replacement or removal of an existing image," regardless
of whether `productSet`'s platform-level reconciliation applies to media —
belt-and-suspenders, not conditional on the open platform fact
**[Blueprint proposal]**.

### A.14 Product price / compare-at-price handling

**[Accepted — DEC-007 §3]** — core price sync and compare-at price, both
directions, where available on both systems. **Included:** base selling
price and compare-at (strike-through) price. **Excluded from Phase 1:**
advanced pricelist mapping, Shopify Markets pricing, customer-specific
pricing, B2B price lists. **Mandatory requirement:** the price
source-of-truth (§A.12) must be explicit per product before any price
export/update — this sprint does not weaken or reinterpret that
requirement.

### A.15 Product publish/draft/status safety

See §A.10 — the mechanism identified there (`status` enum + unpublished-
by-default `productCreate` + explicit `publishablePublish`) is the safety
lever for both **first-time export** (draft-first) and **ongoing updates**
(an update to an already-live product does not implicitly change its
publish state; publish-state changes are their own explicit action, never
a side effect of a field update) **[Blueprint proposal, extending the
newly verified §A.10 mechanism]**.

### A.16 Product preview/review states

Per DEC-012 §7.8/§7.10, every export/update run shows, before writing: how
many records will be created, how many updated (with a diff), and how many
skipped (with why) — **not** a full UI wireframe (deferred to Part D,
MBQ-53), but the **states** an implementation must support:

1. **To create** — no candidate found; will create pending guard checks.
2. **To update** — bound; diff rendered (fields/images/price/variants).
3. **To skip** — ambiguous or unresolved; reason shown, never guessed.
4. **Blocked** — destructive-write guard would delete/omit data without
   confirmation, or price source-of-truth is unset.
5. **Draft-pending-publish** — created/updated in Shopify but not yet
   published to any sales channel (§A.10).

**[Accepted — DEC-012 §7; Blueprint proposal for the explicit five-state
list]**.

### A.17 Product job types

Per Part A §A.5.2 (domain modules register job types against the fixed
job-source list, Part A §D.2), `shopify_connector_product` registers, at
blueprint level **[Blueprint proposal]**:

- `product_import` — Shopify → Odoo product/variant create-or-link, any
  source (`webhook`/`scheduled_sync`/`manual_sync`/`reconciliation`).
- `product_export_create` — first-time Odoo → Shopify product+variant
  export (draft-first, §A.10).
- `product_export_update` — update to an already-bound product/variant.
- `product_export_preview` — a rendered diff/dry-run with no write (maps
  to the core `export_preview_dry_run` job **source**, Part A §D.2/§E.6;
  may run during setup).

Exact job/log Odoo model shape: **[Open question — MBQ-19, unchanged,
implementation planning]**.

### A.18 Product logs, errors, retry, and manual-review touchpoints

Every product job flows through the Part A §D job/log/error abstraction —
no parallel product-specific error system is created (Part A §K.2; RA-013).
See §I "Error classes / retry classes mapping at blueprint level" below for
the full product-relevant mapping; headline touchpoints:

- **`mapping missing`** — a Shopify product/variant with no resolvable Odoo
  binding candidate and no confident auto-create path (rare for product
  import, since product import normally creates; more relevant when export
  targets a product whose binding went stale).
- **`ambiguous match`** — more than one plausible SKU/barcode candidate.
- **`binding conflict` / `duplicate risk`** — stale/recreated Shopify
  product ID; a create that would likely duplicate an existing product.
- **`destructive-write guard blocked`** — a `productSet`/bulk-variant write
  would delete/omit data without a rendered, confirmed preview.
- **`Shopify userErrors/validation`** — a Shopify GraphQL mutation returns
  `userErrors` (e.g. invalid SKU format, option-limit exceeded).
- **`data shape/schema mismatch`** — an unexpected/malformed product
  payload shape.

### A.19 Product-specific open questions

See §J for the consolidated resolved/partially-resolved/carried-forward
table. Headline: **MBQ-23** (variant-write mutation strategy) — partially
resolved by DEC-014, direction accepted. **MBQ-24** (media delete-on-omit) —
carried forward, safety posture unaffected. **MBQ-25** (draft/publish
mechanism) — partially resolved by DEC-014, mechanism identified, cited,
and accepted. **MBQ-59** (automated import create/bind policy, §A.2) —
accepted at blueprint-policy level by DEC-014.

---

## B. Customer domain blueprint

### B.1 Module and binding ownership

Customer import/matching is **folded into `shopify_connector_sale`** for
Phase 1 — there is no separate `shopify_connector_customer` module
**[Accepted — DEC-008; master-blueprint.md module family overview:
"`sale` — order import; customer import/matching (folded in for Phase 1);
financial-evidence capture with the total-check guard"]**. `sale` defines
its own concrete **customer binding** model (Shopify Customer ↔ Odoo
`res.partner`) extending the core abstract binding contract (Part A §C.8)
**[Accepted — DEC-006; DEC-013]**. This directly answers scope item B.7
("customer binding responsibility and relation to `sale` module").

### B.2 Customer import (Shopify → Odoo)

- **Direction:** Shopify → Odoo import and matching **only** in Phase 1
  **[Accepted — DEC-003]**. A customer import creates/updates a matched
  Odoo partner record **only** within the import direction; it never
  pushes partner data back to Shopify **[Accepted — DEC-003;
  phase1-domain-model-brief.md Domain 4]**.
- **Trigger:** most commonly arrives **as part of order import**
  (Shopify orders carry customer data), but may also run standalone (a
  dedicated customer sync/reconciliation pass) — both paths use the same
  matching logic below **[Inference — DEC-003 lists customer import as a
  Shopify → Odoo capability independent of order import scope]**.
- **Automated create/bind policy — accepted at blueprint-policy level by
  DEC-014, tracked as MBQ-59:** applies identically to §A.2's accepted
  policy, substituting the customer domain — a **pre-create duplicate
  check**
  (the §B.3 match-key sequence) runs *before* any automated customer
  create/bind, gated by the same two condition groups as §A.2:
  **eligibility conditions** (setup complete, customer/sale domain
  enabled, source strategy permits creation — routed via Part A's
  accepted enqueue/cancel mechanisms, §E.5/§I.3/§I.4, never
  `blocked_manual_review`) and **match-quality conditions** (a confident
  match to an existing partner, or a confident no-match creation
  candidate, with no `ambiguous match`/`binding conflict`/`duplicate
  risk` condition triggered — routed via Part A's accepted
  confirmation-required classes, §D.5.4/§D.8, when a match-quality
  condition fails). **This document does not widen Part A §D.8's
  confirmation-required sub-reason vocabulary.** Retrospective
  sync-center/dashboard visibility is **audit/log visibility only** — it
  does not by itself satisfy "no blind create" **[Accepted — DEC-014, at
  blueprint-policy level; MBQ-59 — see §A.2 for the full policy]**.

### B.3 Matching priority

**Existing binding → email/customer key → manual review** — the
customer-specific instance of DEC-006's match-key priority, confirmed
explicitly by DEC-012's Fable-review addition: "Customer email/customer-key
matching — for customer records only, after the binding-first check... the
connector matches on email/customer keys before falling back to manual
match; name is advisory only here too, never automatic"
**[Accepted — DEC-006 "Decision summary"; DEC-012 §6.4, Fable review
addition]**. This is the **product-vs-customer distinction** DEC-006
itself draws ("email/customer keys (customers)" as a distinct step from
SKU/barcode for products) — nothing here reinterprets DEC-006, it restates
the already-accepted customer-specific ordering.

### B.4 No customer export in Phase 1

**Unchanged deferral [Accepted — DEC-003].** This blueprint does not
revisit it; it is not re-decided, re-proposed, or routed as an open
question by this sprint. If a future sprint reconsiders it, that is a new
ChatGPT-reviewed decision, not an implicit consequence of this document.

### B.5 No name-only automatic matching

**Structural exclusion, unchanged [Accepted — DEC-003; DEC-006; RA-006].**
A name/email-adjacent similarity may be **shown as an advisory hint**
during manual match, but is never used to auto-bind a customer, exactly as
for products (§A.6).

### B.6 Missing email / no-PII Shopify customer data

- **Protected-customer-data posture:** orders (and their customer PII —
  name/address/email/phone) are Shopify **protected customer data**;
  accessing them requires Shopify approval and data-protection controls
  (Level 1 for any protected data, Level 2 for the protected fields);
  without approval, production stores return no such data
  **[Official fact — `../01-research/shopify-official-api-notes.md`,
  citing `https://shopify.dev/docs/apps/launch/protected-customer-data`]**.
- **Consequence:** a store/app configuration that has not been granted
  protected-data access, or a Shopify plan/checkout path that genuinely
  withholds PII, must not cause order import to fail or to invent PII —
  this is this document's own paraphrase of
  `master-blueprint-open-questions.md`'s MBQ-29 "Why it matters" framing,
  grounded in the accepted DEC-003 posture that "a no-PII-plan fallback
  (default customer) concept exists"
  **[Accepted decision — DEC-003; phase1-domain-model-brief.md Domain 4
  "Data safety guardrails"]**. (Corrected in this revision: earlier
  wording presented "must not fail or invent PII" as a direct quote from
  the domain brief; it is this document's own paraphrase, not a verbatim
  domain-brief quote.)
- **Do not invent PII (repeated for emphasis, per this sprint's explicit
  instruction):** no field is ever synthesized, guessed, or defaulted to a
  plausible-looking value. See §B.7 for the fallback mechanism when data
  is genuinely absent — accepted by DEC-014 at direction level, MBQ-29
  partially resolved (exact granularity remains open).

### B.7 Default customer fallback posture (partially resolves MBQ-29)

- **[Accepted — DEC-014, partially resolving MBQ-29]:** a single,
  deliberately-created, clearly-flagged **fallback partner per store**
  (proposed name direction: a "Shopify — No Customer Data" partner record)
  is used **only** when Shopify genuinely withholds all customer PII for
  an order (a no-PII plan/scope scenario, §B.6) — never as a default for
  an ordinary matching failure, which instead creates a **new**, properly
  matched partner (§B.2) or routes to manual review if ambiguous.
- **Distinct flag, never silent:** every order bound to the fallback
  partner carries a visible, auditable marker ("no customer data
  available — fallback used") on the order/binding record (Part A §D.10
  audit requirements) — the fallback is never indistinguishable from a
  real matched customer in any report or view.
- **What remains open:** whether **one shared fallback partner per store**
  is sufficient, or whether **per-order anonymous identity** is required
  for order-level traceability (e.g. to avoid conflating unrelated no-PII
  orders under one partner's order history) — **[Open question — MBQ-29,
  partially resolved]**, direction proposed, exact granularity for
  ChatGPT/implementation planning.

### B.8 Customer binding responsibility and relation to `sale` module

Answered in §B.1: customer binding responsibility rests with
`shopify_connector_sale`, which owns the customer binding model directly
(not routed through `product`, unlike product/variant bindings which
`sale` resolves through `product` per Part A §K.9) **[Accepted — DEC-008;
Blueprint proposal for the explicit "not routed through product"
statement, since customers have no product-domain counterpart]**.

### B.9 Duplicate-prevention preview for customers

Same structural requirement as products (§A.9): an interactive/batch
matching session always shows a **blocking** "will create N, link M, N
ambiguous" preview *before* any create/bind action **[Accepted — DEC-006;
DEC-012 §6.7]**. For automated per-order customer creation, the §A.2/§B.2
pre-create policy (eligibility + match-quality gate, per-class routed) is
what satisfies "no blind create" — retrospective sync-center/dashboard
visibility is **audit/log visibility only**, never a preview substitute
**[Accepted — DEC-014, at blueprint-policy level — see §A.2 for the full
policy; MBQ-59]**.

### B.10 Customer privacy and protected-data minimization

- Only the fields the accepted DEC-003/DEC-006 matching and order-
  representation requirements actually need are imported — this blueprint
  does **not** propose importing any additional Shopify customer field
  beyond what matching (email/customer keys, §B.3), basic partner
  creation, and order-representation (Domain C) require
  **[Inference — CLAUDE.md §7 "no unsupported claims"; DEC-003 minimal-
  scope discipline applied to PII fields]**.
- **Do not create unsafe partner duplicates:** the match-key priority
  (§B.3) and duplicate-prevention preview (§B.9) are the structural
  mechanism preventing this — restated, not re-designed, here.
- Exact Odoo partner field mapping is **not decided** by this sprint (per
  the sprint's explicit instruction) — field-level mapping remains
  **[Open question — MBQ-02/55, implementation planning]**.

### B.11 Customer-specific logs/errors/manual-review states

Flows through the same Part A §D abstraction as every domain (no parallel
system, Part A §K.2). Headline mapping (full table in §I):
`ambiguous match` (multiple email/customer-key candidates), `binding
conflict` (stale/recreated Shopify customer ID), `duplicate risk` (a
create that would likely duplicate an existing partner), `data shape/
schema mismatch` (malformed customer payload — e.g. missing email on a
non-no-PII store, which is a data-quality signal, not a no-PII case).

### B.12 Customer-specific job types

`shopify_connector_sale` registers, for the customer sub-domain
**[Blueprint proposal]**:

- `customer_import` — Shopify → Odoo partner create-or-link (standalone or
  as part of order import).
- `customer_match_review` — the manual-review resolution action for an
  ambiguous/duplicate-risk customer match (a Reviewer-role action, Part A
  §J.2).

### B.13 Customer-specific open questions

See §J. Headline: **MBQ-29** (default-customer fallback) — partially
resolved, direction accepted, granularity open. **MBQ-31** (final
match-key set) — accepted at blueprint level below. **MBQ-59** (automated
import create/bind policy, §B.2) — accepted at blueprint-policy level by
DEC-014.

**Accepted resolution for MBQ-31 (final customer match-key set):**
**[Accepted — DEC-014, at blueprint level — ChatGPT's direct decision as
MBQ-31's named decision owner, "ChatGPT (Sprint B)"]** — **email is the
sole automatic match key** (beyond an existing binding) for Phase 1;
phone and name stay advisory/manual-only, never automatic. Rationale:
DEC-006's existing evidence base shows competitor multi-key matching
(VentorTech: email/name/phone) but also shows **name** is structurally
excluded everywhere in this connector (RA-006) and **phone**
reliability/availability is itself gated by the same protected-customer-
data approval as email (§B.6) with no demonstrated additional dedup value
cited in the existing evidence base — adding phone as a second automatic
key would introduce a second point of match-key drift (a changed phone
number silently breaking or double-matching) without a cited,
demonstrated safety benefit over email alone, which the DP-006
evidence-consistency gate (`../05-qa/defect-pattern-log.md`) required
before accepting this capability as decided.

---

## C. Sale/order domain blueprint

### C.1 Module and binding ownership

`shopify_connector_sale` owns order import and financial-evidence capture
**[Accepted — DEC-008]**. Per Part A §C.8, `sale` defines a concrete
**order binding** model (Shopify Order ↔ Odoo `sale.order`) extending the
core abstract contract; the order binding is the anchor for idempotent
order creation — a repeated webhook or reconciliation pass must not create
a duplicate sale order **[Accepted — DEC-005; DEC-006;
phase1-domain-model-brief.md Domain 5]**.

### C.2 Shopify order import into Odoo sale orders

- **Trigger:** layered — webhook (`ORDERS_CREATE`/`ORDERS_UPDATED` topics
  **[Official fact — `../01-research/shopify-official-api-notes.md`,
  citing `https://shopify.dev/docs/api/admin-graphql/latest/enums/WebhookSubscriptionTopic`]**),
  scheduled sync, manual sync, and reconciliation — never webhook-only
  **[Accepted — DEC-005]**.
- **Scope constraint:** apps see orders from the last 60 days by default;
  all-orders access requires the `read_all_orders` scope **and** Shopify
  approval **[Official fact — same source]** — this bounds what an
  unapproved app's backfill/reconciliation can see; a store without that
  approval cannot reconcile older orders, which is a **setup-readiness**
  concern (Part A §E.6 readiness checks), not a defect in this blueprint's
  design.
- **Order line mapping:** Shopify order line items map to Odoo
  `sale.order.line` records **[Accepted — DEC-003; phase1-domain-model-
  brief.md Domain 5]** — see §C.4.

### C.3 Order identity and duplicate prevention

The order binding (§C.1) is the sole idempotency anchor for order
creation — a re-processed webhook or reconciliation pass matches the
existing binding and updates, never re-creates
**[Accepted — DEC-005; DEC-006]**. GID permanence is not asserted by
Shopify for any object (Part A §C.3) — the same stale/recreated handling
(Part A §C.6) applies to order bindings as to product/customer bindings; no
new mechanism is invented for orders. Whether Shopify's order identity has
any order-specific stability nuance (e.g. test-mode orders, draft orders
later converted) beyond the general GID-non-permanence caveat is
**[Open question — MBQ-58, new row, official-doc verification, not
blocking — the existing binding-based defensive design already covers the
general case]**.

### C.4 Order line mapping

Each Shopify order line item maps to one Odoo `sale.order.line`, carrying
at minimum: matched product/variant reference (via the product binding,
§C.5), quantity, unit price, and the line's contribution to the order's
tax/discount evidence (§C.7) **[Accepted — DEC-003; phase1-domain-model-
brief.md Domain 5]**. Exact field mapping: **[Open question — MBQ-02/55,
implementation planning]**.

### C.5 Product binding prerequisite / fallback handling for unmatched products

**[Blueprint proposal]** — an order line whose Shopify product/variant has
**no resolvable Odoo product binding** does not silently create a
placeholder product (that would be a "blind create" of catalog data
outside the accepted product-import flow, contradicting DEC-003/DEC-006)
and does not silently drop the line (that would break the total-check
guard, §C.8, since the dropped line's value could never reconcile against
the Shopify order total). Instead: **the whole order import is held**,
using **Part A's accepted per-class routing** — `mapping missing` is one
of Part A §D.5.3's "manual fix then retry" classes, **not** one of the
six confirmation-required `blocked_manual_review` sub-classes (§D.5.4/
§D.8) — so the job sits in the `failed_retryable` state (§D.3, "return
to queued once their condition resolves") with error class `mapping
missing`, naming the specific unmatched SKU/product, until the product is
bound (via the ordinary product-matching flow, §A.6, or a manual match) —
at which point the job returns to `queued` and the order import
resumes/retries through the normal job path **[Accepted — DEC-009 error
taxonomy ("mapping missing"), Part A §D.5.3/§D.3; Blueprint proposal for
the whole-order-hold rule and its correct state/class routing]**.
**Rationale:** any partial order (missing a line) cannot pass the
mandatory, permanent total-check guard (§C.8) either, so holding the
whole order is the guard-consistent behaviour, not an arbitrary
conservatism choice — a partial-create-then-reconcile alternative was
considered and rejected because it would require either a temporary/
incomplete sale order (audit and reporting risk) or a second "top-up"
write path duplicating the total-check logic. **Operator visibility is
unchanged** by this correction — the job still surfaces in the sync
center/error center (Part A §G/§H) with a human-readable reason and a
direct link to the matching flow (§C.14); only the underlying state/class
label is corrected to match Part A's accepted taxonomy.

### C.6 Customer binding/import prerequisite / fallback handling for unmatched customers

**Three** distinct paths, not conflated **[Blueprint proposal]**:

1. **Genuinely no PII available (§B.6)** — the recorded fallback partner
   (§B.7, accepted by DEC-014 at direction level, MBQ-29 partially
   resolved) is used; the order imports normally, flagged.
2. **PII available, no confident automatic match, not ambiguous** — that
   customer import creates/matches a new Odoo partner in this situation
   at all is the **accepted "customer import" capability** (§B.2,
   DEC-003) — this is **not** a "fallback" or an error state. **Whether
   that create/bind happens automatically, without a synchronous
   per-record preview, is governed by the §A.2/§B.2 MBQ-59 gate —
   accepted at blueprint-policy level by DEC-014.** If the
   MBQ-59 gate's conditions hold, the partner is created and bound as
   part of the order-import job; if a match-quality condition fails, the
   create does not proceed automatically and the relevant Part A
   per-class routing applies (§C.13).
3. **PII available, ambiguous (multiple plausible candidates)** — the
   **order's customer assignment specifically** is held pending
   resolution, with error class `ambiguous match` — one of Part A
   §D.5.4/§D.8's six confirmation-required `blocked_manual_review`
   sub-classes, same pattern as §C.5's guard classes, until resolved.
   **This does not block the rest of order import.** Per the accepted
   domain-brief posture: "a failed customer import is isolated and
   reason-coded; the linked order still reconciles via matching, so one
   bad customer record does not block order import"
   (phase1-domain-model-brief.md Domain 4, "Queue / log implications" —
   **[Accepted decision — DEC-003 UX spine]**). This differs from §C.5's
   unmatched-product case: an unmatched product line breaks the
   total-check guard's total-reconciliation math (§C.8) and so must hold
   the whole order, but an ambiguous customer does not affect that math
   at all — the order's lines and financial evidence can still be
   captured and reconciled while customer assignment itself waits for
   operator resolution. **The exact Odoo-record mechanism for capturing
   order evidence while customer assignment is pending** (e.g. a staged/
   draft representation not yet linked to a finalized `sale.order`, vs. a
   `sale.order` created with the ambiguity flagged and a provisional/
   reviewable customer placeholder) is **[Open question — implementation
   planning]**, not decided here — this document commits only to the
   behavioural rule that a customer ambiguity does not block financial-
   evidence capture/reconciliation, not to a specific record mechanism
   achieving it.

Unlike an unmatched **product** (§C.5), an unmatched-but-unambiguous
**customer** does not need to block the order, because customer import is
already an accepted, expected creation path (§B.2, subject to the
§A.2/§B.2 MBQ-59 gate) and does not carry the same delete-on-omit/
catalog-pollution risk product auto-create would.

### C.7 Financial-evidence capture from Shopify order data

**[Accepted — DEC-003 Domain 9; DEC-007 §6]** — Shopify financial status,
payment status, gateway/method label, and `OrderTransaction` reference(s)
where available are preserved as **source information only**. `[Official
fact]` `OrderTransaction` is gateway-agnostic — it exists for all gateways
(`../01-research/shopify-official-api-notes.md`). Financial-evidence
fields (tax/shipping/discount/payment) travel with the order-import job
payload so a partial/failed import can be retried without re-deriving
totals **[Accepted — phase1-domain-model-brief.md Domain 5]**.

### C.8 Total-check guard / reconciliation posture

**Mandatory and permanent — this sprint does not weaken it under any
configuration or feature flag** (Part A §I.5 already lists it among the
guards no flag may bypass) **[Accepted — DEC-007 §6; Part A §I.5]**.

- **[Blueprint proposal, defining the guard at blueprint level]:** before
  an order import job completes (creates or finalizes the Odoo sale
  order), the connector computes the sum of imported line totals + tax
  evidence + shipping evidence − discount evidence and compares it against
  the Shopify order's own reported total (`totalPriceSet` or equivalent —
  exact field **[Open question — implementation planning]**). A mismatch
  beyond a to-be-defined tolerance (currency rounding; exact tolerance
  value **[Open question — MBQ-56, new row]**) is classified with the
  existing DEC-009 error class **`financial total mismatch`** —
  **conservative, never silent, never auto-retried, requiring explicit
  human review/resolution** (Part A §D.5.5). This is its **own** retry
  posture, distinct from Part A §D.5.4's six confirmation-required
  `blocked_manual_review` sub-classes — this document does not label a
  total mismatch as one of those six, and does not widen §D.8's
  sub-reason vocabulary to include it. The job is held awaiting explicit
  operator review and resolution (a Part A §D.3 loop-back state,
  `failed_retryable` — **[Blueprint proposal/Inference]**, since Part A
  does not itself name a specific job-state for this class beyond its
  §D.5.5 retry posture) — never silently re-queued by a timer/backoff the
  way an ordinary auto-retryable class might be.
- **This guard is the mechanism**, not merely a principle — it is the
  concrete blueprint-level answer to the sprint's Scope C requirement
  "Total-check guard / reconciliation posture."
- **Reconciliation backstop:** the same DEC-005 layered-sync
  reconciliation pass that covers products/customers also covers orders —
  a reconciliation run re-verifies a previously-imported order's total
  against Shopify's current state and flags drift (e.g. a later Shopify-
  side edit) using the same `financial total mismatch` class, not a new
  mechanism **[Accepted — DEC-005; Blueprint proposal for applying it to
  orders explicitly]**.

### C.9 Tax/shipping/discount/payment evidence handling

**[Accepted — DEC-007 §6]**, restated for this blueprint's domain
structure, **not re-decided:**

- **Taxes:** `taxLines`/`currentTaxLines`/`totalTaxSet` preserved as
  evidence/lines/amounts; **no** general tax-computation/reconciliation
  engine.
- **Shipping:** `shippingLines`/`shippingLine` preserved as evidence/
  lines.
- **Discounts:** `discountApplications`/`cartDiscountAmountSet` preserved
  as evidence/amounts.
- **Payment evidence:** financial status, payment status, gateway/method
  label, `OrderTransaction` reference(s) — source information only.
- This is treated as **evidence capture**, never accounting automation —
  the sprint's Scope C explicitly forbids inventing Odoo accounting
  automation here, and this blueprint does not.

### C.10 Gateway → Odoo journal mapping (partially resolves MBQ-30)

**[Accepted — DEC-014, partially resolving MBQ-30]** — a per-store
configuration concept: a mapping from Shopify's free-text gateway/payment-
method label (e.g. `"shopify_payments"`, `"manual"`, `"bogus"`) to an Odoo
`account.journal` **reference**, contributed via the core §I settings-
extension seam (Part A §A.5.4). This mapping is used **only** to
pre-populate/suggest a journal classification on the imported order's
financial-evidence record (§C.7/§C.9) for later human/accounting
workflows — it triggers **no** automatic journal entry, posting, or
reconciliation of any kind, per this sprint's explicit "classification/
routing input only" instruction. Exact schema/fields: **[Open question —
MBQ-30, partially resolved — direction proposed; not blocking, per the
existing register row]**.

### C.11 No invoice/payment posting automation in Phase 1

**Unchanged [Accepted — DEC-003; DEC-007 §6].** No automatic posted
invoices, automatic posted payments, bank reconciliation, payout
reconciliation, or full accounting workflow — this blueprint does not
loosen that exclusion, and does not decide the Domain 9 draft-artifact
guard (§C.12) preemptively.

### C.12 Handling order edits/cancellations/refunds

**Deferred, unchanged [Accepted — DEC-003 "Refund/cancellation
decision"].** Order edits, cancellations, refunds, and return processing
**all** remain deferred — this sprint does not build any order-edit/
cancellation/refund/return-processing handling, and does not narrow that
deferral to only "processing workflows" while quietly allowing the
underlying sale order to change.

**[Accepted — DEC-014, point I — the Fable B2 route, narrowed in the PR
#72 Fable revision and accepted as final]:** for an already-imported
order, an `ORDERS_UPDATED` webhook (or the equivalent
reconciliation-detected change) may **refresh Shopify-side evidence/audit
data only** — the raw financial-evidence fields captured at import
(§C.7/§C.9) and their audit trail. It must **not** silently update the
existing Odoo sale order's line quantities, prices, taxes, shipping,
discounts, invoices, payments, refunds, or fulfillment state — none of
those is written by this path, under any trigger. If the refreshed
Shopify-side evidence no longer matches the existing Odoo sale order
representation (e.g. a line quantity or amount changed on the Shopify
side after import), that divergence is **not auto-applied** — it routes
through the same total-check guard / `financial total mismatch` /
human-review posture already defined in §C.8, exactly as any other total
divergence would, so the operator sees and resolves the discrepancy
rather than the connector silently rewriting a possibly-already-confirmed
or already-fulfilled sale order.

**Webhook/reconciliation consistency:** the webhook path and the
reconciliation path must behave the same way for the same underlying
Shopify-side change — a webhook-delivered order edit is **not** auto-
applied to the Odoo sale order any more than a reconciliation-detected
one is; both only refresh evidence and, on divergence, flag via the
total-check guard. Neither path silently writes to sale-order lines,
totals, or fulfillment state.

**What remains open:** the exact mechanism for "refreshing evidence only"
without ever touching sale-order lines (e.g. a separate evidence-snapshot
record vs. an evidence-only field group on the existing evidence capture,
§C.7) is an **[Open question — implementation planning]**, not decided
here. This narrowed wording is accepted as DEC-014 point I (the Fable B2
route) and does not expand what DEC-014 accepts beyond the existing
deferred posture already named in its "Proposed decision" item 3.

The mandatory idempotent-refund regression principle (DEC-003) remains
carried forward for the first refund/refund-sync sprint, unaffected by
this note.

### C.13 Manual review triggers

**[Accepted — DEC-014, point H — the Fable B1 route, corrected in the PR
#72 Fable revision and accepted as final]:** every trigger below maps to
an existing Part A §D.4 error class — no new class is introduced (Part A
§A.5.3: domain modules map into the fixed registry, they do not fork
it). **Not every trigger is a `blocked_manual_review` confirmation-
required case** — Part A's per-class routing (§D.5) distinguishes
"manual fix then retry" (§D.5.3, `failed_retryable`), "operator
confirmation required" (§D.5.4, `blocked_manual_review`, six sub-classes
only), and "conservative, never silent" (§D.5.5, its own posture) — this
table uses that accepted routing, not a single collapsed state. **Part A
§D.8's confirmation-required sub-reason vocabulary is not widened** by
this table or by any routing in §A.2/§C.5/§C.8/§G/§I:

| Trigger | Error class (Part A §D.4) | Routing (Part A §D.5) |
| --- | --- | --- |
| Unmatched product (§C.5) | `mapping missing` | Manual fix then retry (§D.5.3) — `failed_retryable`, **not** `blocked_manual_review` |
| Unmatched customer (ambiguous case only, §C.6.3) | `ambiguous match` | Operator confirmation required (§D.5.4) — `blocked_manual_review` |
| Duplicate order risk (binding suggests a possible duplicate) | `duplicate risk` | Operator confirmation required (§D.5.4) — `blocked_manual_review` |
| Total mismatch (§C.8) | `financial total mismatch` | Conservative, never silent (§D.5.5) — **not** one of `blocked_manual_review`'s six sub-classes; requires explicit human review/resolution |
| Unsupported data shape (malformed/unexpected order payload) | `data shape/schema mismatch` | Manual fix then retry (§D.5.3) — `failed_retryable`, **not** `blocked_manual_review` |
| Missing mapping (a required field's mapping configuration absent, e.g. no gateway→journal mapping and one is required for a downstream step) | `mapping missing` | Manual fix then retry (§D.5.3) — `failed_retryable`, **not** `blocked_manual_review` |

### C.14 Order-import operator touchpoints (accepted at blueprint level, MBQ-26)

**[Accepted — DEC-014, at blueprint level — ChatGPT's direct decision as
MBQ-26's named decision owner, "ChatGPT (Sprint B)"]:**

The core error center + manual-review flow (Part A §H) is **sufficient**
for Phase 1 order-import operator touchpoints, **provided** it carries two
order-specific additions, both of which are extensions of the *existing*
error-center contract (Part A §H.8 "manual review sub-reasons... never a
generic 'needs review'"), not a new surface:

1. The `financial total mismatch` entries (§C.8) render with the
   **specific evidence breakdown** (Shopify total vs. computed Odoo total,
   per-component: lines/tax/shipping/discount) inline in the error-center
   detail — not just a pass/fail flag — so the operator can see *why* it
   mismatched without leaving the error center.
2. The `mapping missing` entries for order-blocked-on-product (§C.5) and
   order-blocked-on-customer-ambiguity (§C.6.3) link directly to the
   relevant matching flow (§A.6/§B.3) so resolving the underlying binding
   and retrying the order is a two-click path, not a manual hunt.

**A separate, dedicated order-import screen is not authorized or
required** — the existing sync-center (Part A §G, filterable by domain)
and error-center (Part A §H) surfaces, extended as above, are accepted as
sufficient. This acceptance is conditioned on, and requires, the two
order-specific extensions above (inline financial-evidence breakdown;
direct matching-flow links) — both are accepted as part of this same
DEC-014 acceptance, not deferred to a separate future requirement (see
§J).

### C.15 Order-specific job types

`shopify_connector_sale` registers, for the order sub-domain
**[Blueprint proposal]**:

- `order_import` — Shopify → Odoo sale-order create-or-update, any source.
- `order_reconciliation_check` — the reconciliation-pass verification
  described in §C.8, distinct from a fresh import.

### C.16 Order-specific logs/errors/retry/manual-review states

Flows through Part A §D, same as every domain (§I has the full table).
Headline: `financial total mismatch` is **always** manual/never auto-
retried (Part A §D.5.5) — this is the one class where "conservative,
never silent" is the rule, restated here because it is the order domain's
signature guard.

### C.17 Order-specific open questions

See §J. Headline: **MBQ-26** (operator touchpoints) — proposed resolution
above. **MBQ-27** (tax representation mechanism) — carried forward, open
(see *Newly attempted evidence check* below). **MBQ-28** (Domain 9
draft-artifact guard) — not triggered by this sprint, carried forward
unchanged. **MBQ-30** (gateway→journal mapping) — partially resolved,
concept proposed.

**Newly attempted evidence check for MBQ-27 (inconclusive, does not
resolve the row):** an official-doc check was made against Odoo 19's
accounting/taxes documentation
(`https://www.odoo.com/documentation/19.0/applications/finance/accounting/taxes.html`,
accessed 2026-07-03). The page confirms Odoo has a **"Tax Included"**
price mode ("Prices can be changed to Tax Included to treat all taxes as
tax included by default") but does **not** address manual/externally-
supplied tax amounts, a `price_include`-style override, or any mechanism
for holding a pre-computed tax figure without Odoo's own tax engine
recomputing it — the page explicitly routes deeper mechanism detail to a
separate tax-computation page not fetched this sprint (per the sprint's
"only targeted checks" instruction, a second-level fetch was not pursued).
**This does not resolve MBQ-27** — the exact mechanism for representing
Shopify-computed tax on an Odoo sale order without Odoo recomputing it
remains **[Open question — MBQ-27, unchanged, official-doc verification
+ implementation planning]**. This blueprint decides only **that** the
amounts are preserved as evidence (§C.9, already DEC-007 §6), not **how**.

---

## D. Cross-domain sequencing

1. **Product binding availability before order import line creation.**
   An order line cannot create/attach a `sale.order.line` referencing an
   unbound product — §C.5's whole-order-hold rule is the enforcement
   mechanism **[Blueprint proposal, restated from §C.5]**.
2. **Customer binding/import before order customer assignment.** An order
   cannot be **finalized** without a customer assignment (matched, newly
   created, or the recorded fallback, §C.6) — the order-import job
   sequences customer resolution before finalization, though (per §C.6.3)
   an ambiguous customer holds only that assignment step, not the
   order's line/evidence capture **[Blueprint proposal, restated from
   §C.6]**.
3. **Order import preview or validation before create.** The total-check
   guard (§C.8) is evaluated **before** the order is marked
   complete/finalized, not as a post-hoc audit — a failing check holds the
   job (classified `financial total mismatch`, Part A §D.5.5's own
   "conservative, never silent" posture — **not** a `blocked_manual_review`
   confirmation-required case) rather than creating a suspect order
   **[Blueprint proposal, restated from §C.8]**.
4. **Manual review if product/customer/mapping is missing.** Uniformly
   routed through the existing Part A §D.4 error-class registry (§C.13) —
   no domain-specific manual-review mechanism is invented.
5. **Reconciliation backstop through accepted core substrate.** Product,
   customer, and order reconciliation all use the same DEC-005 layered-
   sync reconciliation mechanism (Part A §D.1) — order reconciliation
   additionally re-runs the total-check guard (§C.8), not a separate
   check.
6. **How product/customer/order domain jobs use the core job/log/error/
   binding substrate.** Every job type in §A.17/§B.12/§C.15 is a
   registered job **type** within the fixed job **sources** (Part A §D.2);
   every binding in §A.1/§B.1/§C.1 is a concrete model extending the core
   abstract binding contract (Part A §C.8); every error routes through the
   fixed 16-class registry (§I below) — see §E/§F for the consolidated
   view.
7. **Which actions are manual, scheduled, webhook-driven, or
   reconciliation-driven:**

   | Domain action | Manual | Scheduled | Webhook | Reconciliation |
   | --- | --- | --- | --- | --- |
   | Product import | Yes (manual sync) | Yes | Yes (product create/update webhook topics — exact strings not verified/cited this sprint, §A.2) | Yes |
   | Product export/update | Yes (explicit action, §A.3) | No — controlled, not autonomous | No | No |
   | Product export preview/dry-run | Yes | No | No | No |
   | Customer import | Yes | Yes | Yes, as part of order webhooks (`ORDERS_CREATE`/`ORDERS_UPDATED`, cited §C.2) | Yes |
   | Order import | Yes | Yes | Yes (`ORDERS_CREATE`/`UPDATED`) | Yes |
   | Order reconciliation check | No (system-triggered) | Yes | No | Yes (this *is* the reconciliation action) |
   | Manual-review resolution (any domain) | Yes (Reviewer role, Part A §J.2) | No | No | No |

   **[Blueprint proposal, synthesizing §A–§C's individual trigger
   statements into one table]**. Product export is deliberately **not**
   webhook/scheduled/reconciliation-driven — an Odoo-side product change
   never autonomously pushes to Shopify without an explicit operator
   action, consistent with DEC-003's "controlled," not "autonomous,"
   product-export scope (§A.3). **Customer import may occur as part of
   order webhooks, scheduled sync, manual sync, or reconciliation.
   Standalone customer import (not triggered by an order webhook) is
   sync/reconciliation/manual only — this document does not assert a
   standalone customer-only webhook topic, since none is verified/cited;
   if official customer webhook topics are verified later, this row can
   be revisited.**

---

## E. Job/log/error/retry usage through core

No product/customer/order-specific job, log, error, or retry system is
introduced — every job type registered in §A.17/§B.12/§C.15 flows through
the single Part A §D abstraction (queue posture §D.1, job sources §D.2,
job states §D.3, the fixed error-class registry §D.4, retry-eligibility
concept §D.5, operation-level idempotency §D.6, ambiguous-outcome/
serialization rules §D.7, manual-review state §D.8, cancellation/
supersede §D.9, audit requirements §D.10, log shapes §D.11–§D.12, retry
safety rules §D.13) **[Accepted — DEC-013; Blueprint proposal only for
the domain-specific job-type names themselves, §A.17/§B.12/§C.15]**. This
satisfies Part A §K.2 ("no domain module may implement its own job/queue,
log, error-class registry, or binding-audit system," RA-013 binding) —
checked and not violated by this sprint.

## F. Binding/dedup usage through core

Product-template, product-variant, customer, and order bindings are each a
**concrete model extending the core abstract binding contract** (Part A
§C.8) — store-scoped uniqueness (§C.2 of Part A), explicit GID + Odoo
record identity (§C.3), status/audit fields (§C.4), the fixed match-key
priority per domain shape (§C.5, this document's §A.6/§B.3), and stale/
recreated handling (§C.6) apply uniformly. No new binding shape, no
polymorphic table, and no per-domain audit variant is introduced — this
sprint reuses MBQ-11's accepted direction (Part A §C.8, DEC-013) without
modification.

## G. Manual review and operator touchpoints

Every domain's human-review-requiring trigger (§A.18, §B.11, §C.13) maps
into an **existing Part A §D.4/§D.5 class and its accepted routing** — no
new state and no new class is introduced. **Not every such trigger is a
`blocked_manual_review` confirmation-required case:** `mapping missing`
and `data shape/schema mismatch` are Part A §D.5.3's "manual fix then
retry" classes (`failed_retryable`); `financial total mismatch` is Part A
§D.5.5's own "conservative, never silent" posture; only `ambiguous
match`, `binding conflict`, `duplicate risk`, and `destructive-write
guard blocked` — four of Part A's six confirmation-required sub-classes,
the ones relevant to this sprint's domains — route to
`blocked_manual_review` with a specific sub-reason (Part A §D.5.4/§D.8).
**This document does not widen that six-sub-class vocabulary.** Every
case still surfaces to the operator with a human-readable reason, a
related-record link, and (where applicable) a resolution action, via the
same sync-center/error-center surfaces (Part A §G/§H) regardless of which
class/state it sits in — operator visibility and safety outcome are
unchanged from the previous draft; only the underlying state/class label
is now precise. The single new operator-facing recommendation this
sprint makes is §C.14's proposed order-import touchpoint extension
(evidence-breakdown detail + direct matching-flow links inside the
existing error center) — not a new screen, pending ChatGPT acceptance.

## H. Source-of-truth decisions and open questions

Product source-of-truth choices are enumerated in §A.12 (attributes/
variant structure, title, SKU/barcode, price/compare-at, media). Customer
and order domains do not introduce new source-of-truth **settings** —
customer identity is resolved by match-key priority (§B.3), not a
source-of-truth toggle, and order import is inherently one-directional
(Shopify → Odoo), so no source-of-truth choice applies **[Inference — a
source-of-truth setting only has meaning where both systems could
originate the same field; DEC-003 keeps customer/order strictly
import-direction in Phase 1]**.

## I. Error classes / retry classes mapping at blueprint level

Consolidated view of §A.18/§B.11/§C.13/§C.16 against the fixed Part A §D.4
registry — **no new error class is added**. The "Retry posture" column
below uses Part A §D.5's exact per-class routing, and this table was
already accurate — the fix in this revision is to the **prose** in
§A.2/§C.5/§C.8/§C.13/§G, which had incorrectly described some of these
rows as `blocked_manual_review` cases; that prose now matches this table.
**Only** "Operator confirmation required" rows are `blocked_manual_review`
cases (Part A §D.5.4/§D.8's six confirmation-required sub-classes, four
of which are relevant to this sprint's domains: ambiguous match, binding
conflict, duplicate risk, destructive-write guard blocked); "Manual fix
then retry" rows (mapping missing, data shape/schema mismatch, and the
other non-confirmation classes) sit in `failed_retryable` (§D.3);
"Conservative, never silent" (financial total mismatch, §D.5.5) is its
**own** posture, distinct from both:

| Error class (Part A §D.4) | Product instance | Customer instance | Order instance | Retry posture (Part A §D.5) |
| --- | --- | --- | --- | --- |
| Shopify throttling/rate-limit | Any product mutation/query | Any customer mutation/query | Any order mutation/query | Auto-retry with backoff |
| Shopify temporary/server/network | Transient product API failure | Transient customer API failure | Transient order API failure | Auto-retry (reads/`@idempotent`); ambiguous-outcome rule otherwise |
| Shopify permission/scope/auth | Missing product-write scope | Missing protected-customer-data approval (§B.6) | Missing required order read scope / protected-customer-data approval | Manual fix then retry |
| Shopify userErrors/validation | Invalid SKU/option/price payload | Invalid partner-field payload | Invalid order-line payload | Manual fix then retry |
| Odoo validation/configuration | Odoo-side product validation failure | Odoo-side partner validation failure | Odoo-side sale-order validation failure | Manual fix then retry |
| Mapping missing | Stale export-target binding | — | Unmatched product on an order line (§C.5) | Manual fix then retry |
| Ambiguous match | Multiple SKU/barcode candidates | Multiple email/customer-key candidates (§B.3) | Ambiguous customer on order (§C.6.3) | Operator confirmation required |
| Binding conflict | Stale/recreated Shopify product ID | Stale/recreated Shopify customer ID | Stale/recreated Shopify order ID | Operator confirmation required |
| Duplicate risk | Create would likely duplicate a product | Create would likely duplicate a partner | Binding suggests a possible duplicate order | Operator confirmation required |
| Destructive-write guard blocked | Unconfirmed `productSet`/bulk-variant write (§A.11) | — (no destructive customer write in Phase 1) | — (no destructive order write; import only) | Operator confirmation required |
| Inventory location missing | — (Sprint C) | — | — | n/a to this sprint |
| Fulfillment notification confirmation missing | — (Sprint C) | — | — | n/a to this sprint |
| **Financial total mismatch** | — | — | **§C.8 total-check guard failure** | Conservative, never silent — always manual |
| Data shape/schema mismatch | Malformed product payload | Malformed customer payload | Malformed order payload | Manual fix then retry |
| Concurrency/race conflict | Two concurrent writes to same binding | Two concurrent writes to same binding | Two concurrent writes to same binding | Auto-retry with backoff |
| Unknown/system error | Any unclassified failure | Any unclassified failure | Any unclassified failure | Single safety-net auto-retry, then human |

**Scope-name caveat (Shopify permission/scope/auth row):** the exact
Shopify access-scope names required for product, customer/protected-data,
and order reads/writes are **not decided or verified by this sprint** —
the table above names the *class* of failure, not a committed scope
string. Exact scope names remain implementation planning / official-doc
verification, already covered by the existing register rows **MBQ-06**
(readiness-check list, explicitly including "scopes") and **MBQ-09**
(whether custom apps are bound by Level 1/2 protected-data obligations) —
no new MBQ row is added for this caveat.

---

## J. Open questions: resolved / partially resolved / carried forward

Full register: [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
§4. **Accepted by ChatGPT via DEC-014 on 2026-07-03** — see the
claim-label note at the top of this document and DEC-014's "Accepted
decision" section for the full explicit acceptance points (A–J).
"Partially resolved" means direction accepted, exact detail still open;
"accepted at blueprint level"/"accepted at blueprint-policy level" means
ChatGPT's decision is final at that level, with any named residual detail
still open as stated.

| MBQ | Sprint B outcome | Where |
| --- | --- | --- |
| MBQ-23 | **Partially resolved by DEC-014** — mutation-strategy direction accepted (bulk-variant mutations for variant-only updates; `productSet` for first export/full resync); exact implementation choice stays open | §A.5.2 |
| MBQ-24 | **Carried forward, open** — official docs checked; media not confirmed either way; safety posture (preview) already covers the risk regardless | §A.13 |
| MBQ-25 | **Partially resolved by DEC-014** — mechanism identified, cited, and accepted (`status` enum + unpublished-by-default `productCreate` + `publishablePublish`); exact channel-selection UX stays open | §A.10 |
| MBQ-26 | **Accepted at blueprint level by DEC-014** — existing error/sync-center surfaces, extended with two order-specific details (inline financial-evidence breakdown; direct matching-flow links), accepted as sufficient; no dedicated screen authorized or required | §C.14 |
| MBQ-27 | **Carried forward, open** — official-doc check attempted (Odoo tax docs), inconclusive; mechanism unresolved | §C.17 |
| MBQ-28 | **Carried forward, unchanged** — not triggered by this sprint | §C.11/§C.17 |
| MBQ-29 | **Partially resolved by DEC-014** — single shared fallback-partner direction accepted; per-order-vs-shared granularity stays open | §B.7 |
| MBQ-30 | **Partially resolved by DEC-014** — gateway→journal config-surface concept accepted; exact schema stays open | §C.10 |
| MBQ-31 | **Accepted at blueprint level by DEC-014** — email-only automatic match key accepted; phone/name stay advisory | §B.13 |
| MBQ-59 | **Added in PR #72 revision; revised again in the Fable-review revision; accepted at blueprint-policy level by DEC-014** — automated (webhook/scheduled/reconciliation) import create/bind policy: a pre-create duplicate check plus a two-tier gate (eligibility conditions — setup complete, domain enabled, source strategy permits creation — routed via Part A's accepted enqueue/cancel mechanisms, never `blocked_manual_review`; match-quality conditions — confident match or confident no-match-creation candidate, no ambiguous-match/binding-conflict/duplicate-risk/destructive-write-guard condition — routed via Part A's accepted confirmation-required classes when failed; fully logged per Part A §D.10/§C.4); retrospective sync-center/dashboard visibility is audit only, not preview. The policy itself is accepted; exact eligibility-check/match-confidence implementation detail remains open for implementation planning | §A.2/§B.2/§C.6 |

**New rows added (next available number after MBQ-54):** MBQ-55 through
MBQ-59 — see [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
§4 for the full entries. Summary: MBQ-55 (exact Odoo model/field names for
the four new binding models this sprint defines conceptually — product-
template, product-variant, customer, order), MBQ-56 (exact total-check
guard tolerance/comparison mechanism, §C.8), MBQ-57 (whether an unmatched-
product order-line should ever have an alternative to the whole-order-hold
rule in §C.5, for future reconsideration), MBQ-58 (Shopify order-identity
stability nuances beyond general GID-non-permanence, §C.3), **MBQ-59**
(automated import create/bind policy and preview semantics — added in
the PR #72 revision, replacing the withdrawn "retrospective visibility
satisfies preview" reading in §A.2/§A.9/§B.2/§B.9; revised again in the
Fable-review revision to use accepted Part A per-class routing instead of
collapsing every gate failure into `blocked_manual_review` — **accepted
at blueprint-policy level by DEC-014**; exact implementation detail
remains open).

**MBQ-24, MBQ-27, MBQ-28, MBQ-55, MBQ-56, MBQ-57, and MBQ-58 remain
open** — carried forward or added this sprint, not resolved. **MBQ-04,
MBQ-08, MBQ-53, and MBQ-54 are unchanged and remain open** — not
addressed, not resolved, not touched by this sprint or by DEC-014's
acceptance.

## K. What this does not decide

- No exact Odoo model/field/view/security identifiers for any product,
  customer, or order concept (**MBQ-01/02/03/44/55**, implementation
  planning).
- No final GraphQL mutation body for variant writes, media writes, or
  publish calls (**MBQ-23/24/25**, direction proposed only, per the
  sprint's "no exact GraphQL mutation finalization unless official-doc
  evidence is verified" instruction).
- No exact tax-representation mechanism on the Odoo side (**MBQ-27**).
- No Sprint C inventory or fulfillment domain content of any kind.
- No UI/UX screen-level design, wireframe, or navigation structure
  (Part D, **MBQ-53**, unchanged, not started).
- No change to DEC-003 through DEC-013, to any accepted AR row, or to any
  RA row.
- No implementation authorization under any outcome of this review.

## L. Implementation remains blocked

**This blueprint's acceptance via DEC-014 does not authorize
implementation.** No code, Odoo module, model, view, controller, security
file, manifest, test, or CI file is created or permitted by this
document. The no-code gate (`CLAUDE.md` §4–§5) remains in force. Per
`master-blueprint.md`'s "Criteria for when implementation may later be
opened," implementation of the product/customer/order domains
additionally requires: (1) ChatGPT acceptance of this Part B blueprint
(via DEC-014) — **satisfied, 2026-07-03**; (2) resolution or conscious
acceptance of every "Blocks implementation: Yes" row this sprint
touches — **not satisfied**, several such rows remain open (MBQ-04,
MBQ-08, MBQ-23–25 detail, MBQ-27, MBQ-29–30 detail, MBQ-53–59); (3) a
separate, explicit ChatGPT implementation-gate approval — **not
satisfied**; (4) every implementation task written to the `CLAUDE.md` §9
template — **not applicable, no implementation task written**; (5) no
open quality-gate escalation. **Condition (1) alone is satisfied by this
acceptance; conditions (2)–(5) are not, so implementation remains
blocked.**

## Next recommended sprint after ChatGPT review

**Master Blueprint Sprint C — Inventory and Fulfillment Domain Blueprint**
(Part C): convert DEC-010/DEC-011 into the inventory and fulfillment
domain blueprints, resolving or routing the Sprint-C-owned MBQ rows
(§5/§6 of the register). Not started by this sprint.
