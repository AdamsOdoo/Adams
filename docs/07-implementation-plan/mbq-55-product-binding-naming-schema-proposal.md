# MBQ-55 — Product-Template / Product-Variant Binding Naming & Schema Proposal

> **Documentation-only naming/schema proposal**, prepared per the route MBQ-55's
> own row names: *"a dedicated, documentation-only domain naming/schema
> planning pass (PR #85 pattern, extending the accepted `shopify.connector.*`
> conventions and binding-mixin contract), to be accepted before the
> product/customer/order slice starts"*
> ([`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
> MBQ-55 row). This document mirrors the structural pattern of
> [`core-naming-schema-planning.md`](./core-naming-schema-planning.md) (the
> PR #85 pass that resolved MBQ-01/02 for the six core models), applied here
> to the **product-template and product-variant binding models only**.
>
> **Scope note:** MBQ-55 as registered covers four Sprint-B-defined binding
> models — product-template binding, product-variant binding, customer
> binding, and order binding
> ([`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
> MBQ-55 row). This document addresses **only the product-template and
> product-variant portion**, per this session's explicit objective. The
> customer-binding and order-binding portions of MBQ-55 **remain fully open**
> and are not addressed, narrowed, or implied resolved by this document — a
> future, separate naming pass is required before Tasks 011 (customer
> import/matching) or 012 (order import) can reach the same precision.

## 1. Status

- **Proposed / Under review.**
- **Not accepted.** No ChatGPT acceptance of this document exists anywhere in
  this repository as of this session.
- **Does not authorize implementation of any kind.**
- **Does not open the Task 010 implementation gate.**
- **Does not open the product-domain gate** (see the companion document,
  [`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md),
  which only proposes criteria for that future, separate act).
- **Does not create any product module, file, model, or code.** Every model
  name, file name, class name, and field name below is a **proposal**, not a
  committed artifact — nothing in this document exists in the addon tree.
- **Does not mark MBQ-55 (product portion or otherwise) as Resolved.** MBQ-55
  remains **Open** until ChatGPT explicitly accepts this proposal (or a
  revision of it).

## 2. Purpose

This document proposes a closure path for **only** the product-template and
product-variant portion of MBQ-55:

- Exact Odoo model names for the two product/variant binding models.
- Exact future file names for the module that would implement them.
- Exact class names, as design only (no code).
- Exact binding fields, separated into inherited-from-mixin, new relational,
  identity, imported-snapshot, out-of-scope, and deferred buckets.
- The relationship between the two proposed models and the existing core
  `shopify.connector.binding.mixin` abstract contract.
- The relationship between the two proposed models and Odoo's own
  `product.template` and `product.product` models.

It does not propose customer-binding or order-binding names (see the scope
note above), does not decide any architecture question DEC-003 through
DEC-025 has not already decided, and does not re-litigate the accepted
product-domain blueprint (DEC-014). It only converts already-accepted
*directions* into *exact* proposed identifiers, exactly as
`core-naming-schema-planning.md` did for the six core models.

## 3. Accepted source constraints

Every constraint below is cited from an already-accepted source. This
proposal does not reinterpret or weaken any of them.

- **Module boundary strategy** — `shopify_connector_product` owns
  product/variant import, export, update, and binding responsibility
  **[Accepted — DEC-008]**; `shopify_connector_core` remains domain-agnostic
  substrate only (transport, queue/job abstraction, binding *abstraction*,
  error-class registry) — product/variant concepts are explicitly **out of
  scope** for `core`
  ([`core-naming-schema-planning.md`](./core-naming-schema-planning.md) §2,
  "Product/customer/order/inventory/fulfillment domain models... explicitly
  out of scope for a core-only pass").
- **One concrete binding model per synchronized root entity** — *"to avoid
  binding-model explosion, the default is one concrete binding model per
  synchronized root entity (product template, product variant, customer,
  order, inventory level, FulfillmentOrder/Fulfillment... Any additional
  sub-entity binding model... requires explicit architecture review"*
  **[Accepted — DEC-013, part of the binding schema shape acceptance]**
  ([`master-blueprint-core-substrate.md`](../03-architecture/master-blueprint-core-substrate.md)
  §"Binding-model granularity bound").
- **Shopify product and variant have separate GIDs** — *"Shopify assigns
  independent GIDs to each"* the Product and the ProductVariant
  **[Accepted — DEC-006; phase1-domain-model-brief.md Domain 3]**
  ([`master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md)
  §A.1, §A.7).
- **Product-template binding does not replace variant binding** — *"Template
  and variant identity are held separately... a template binding does not
  stand in for its variants' bindings, and a variant's identity (SKU,
  barcode, Shopify ProductVariant GID) is independent of its parent
  template's identity"* **[Accepted — DEC-006; phase1-domain-model-brief.md
  Domain 3]** (same source, §A.7).
- **The core binding mixin must be reused** — *"Each domain module defines
  its own concrete binding model extending that contract: product-template
  binding and product-variant binding in `product`..."*
  **[Accepted — DEC-013]** (`master-blueprint-core-substrate.md`
  §"core defines an abstract binding contract"). The mixin itself
  (`addons/shopify_connector_core/models/shopify_connector_binding_mixin.py`,
  read directly, read-only, this session) is an `AbstractModel` with **no
  table of its own** — its own docstring states composite uniqueness on
  `(store_id, shopify_gid)` "is enforced per concrete model, not here."
- **No polymorphic binding table** — *"The single polymorphic table option
  (DEC-006 Option B) is not chosen, per DEC-013's acceptance... per-domain
  concrete tables extending one core abstract contract are the accepted
  direction. MBQ-11 is resolved by DEC-013's acceptance of this direction."*
  **[Accepted — DEC-013; resolves MBQ-11]** (same source). Note precisely:
  the polymorphic option was **not chosen**, but DEC-013 explicitly records
  it as "not entered as a rejected approach" — this proposal does not treat
  it as formally rejected in `rejected-approaches-log.md`, only as not the
  accepted direction.
- **No product export/update in Task 010** — *"this task is scoped to
  product import and variant binding only — Shopify → Odoo, read-only
  against Shopify. Controlled product/variant export, update, and any write
  back to Shopify... is not part of Task 010"* **[Accepted scope narrowing —
  ChatGPT REVISE on PR #93]**
  ([`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md),
  revision note).
- **No customer/order/inventory/fulfillment scope in Task 010** — Task 010's
  own proposed document states this explicitly and repeatedly (Explicit
  exclusions section) — restated, not altered, here.

## 4. Proposed module and files

**Proposed only. Nothing below is created by this document.**

- **Addon/module name:** `shopify_connector_product` — already named by
  DEC-008 and `task-010-product-import-proposed.md`; this document does not
  change it.
- **Manifest:** `addons/shopify_connector_product/__manifest__.py`
  (proposed name only — no content is drafted here; `depends: ['shopify_connector_core']`
  per DEC-008's one-directional dependency DAG).
- **Model init:** `addons/shopify_connector_product/models/__init__.py`
- **Model files (proposed names):**
  - `addons/shopify_connector_product/models/shopify_connector_product_template_binding.py`
  - `addons/shopify_connector_product/models/shopify_connector_product_variant_binding.py`
- **Security expectation (only if a future implementation creates the
  concrete models):** `addons/shopify_connector_product/security/ir.model.access.csv`,
  reusing the four **existing** groups — `shopify_connector_core.group_shopify_connector_auditor`
  /`_operator`/`_reviewer`/`_admin` (confirmed present in
  `addons/shopify_connector_core/security/shopify_connector_security.xml`,
  read directly, read-only, this session) — **no new group is proposed.**
  Access-row naming would mirror the existing core convention exactly, e.g.
  `access_shopify_connector_product_template_binding_operator`.
- **Test init:** `addons/shopify_connector_product/tests/__init__.py`
- **Test files (proposed names, mirroring the existing `test_<concept>.py`
  convention confirmed in `addons/shopify_connector_core/tests/`):**
  - `addons/shopify_connector_product/tests/test_product_template_binding.py`
  - `addons/shopify_connector_product/tests/test_product_variant_binding.py`
  - `addons/shopify_connector_product/tests/test_product_import_matching.py`
  - `addons/shopify_connector_product/tests/test_product_duplicate_prevention.py`
- **No UI files** — no views, no menus, no actions.
- **No wizard files.**
- **No controller files.**
- **No webhook files.**
- **No OAuth files.**

None of the files above are created by this document. They are named here
only so a future, separately-authorized Task 010 final implementation prompt
does not have to invent names from nothing.

## 5. Proposed Odoo model names

### 5.1 `shopify.connector.product.template.binding`

| Aspect | Proposal |
| --- | --- |
| Model technical name | `shopify.connector.product.template.binding` |
| Purpose | The concrete binding record linking one Shopify Product to one Odoo `product.template`, extending the core binding contract |
| Odoo model it binds to | `product.template` |
| Shopify resource/GID it binds to | Shopify `Product` (its `id`/GID) |
| Why this name follows convention | Matches the `shopify.connector.<entity>` prefix every existing model uses (`shopify.connector.store`, `.store.settings`, `.location`, `.job`, `.job.log`) and the explicit expectation that "later domain modules... are expected to continue this convention for their own concrete binding models" (`core-naming-schema-planning.md` §3) |
| Why alternatives were rejected | See §11 |

### 5.2 `shopify.connector.product.variant.binding`

| Aspect | Proposal |
| --- | --- |
| Model technical name | `shopify.connector.product.variant.binding` |
| Purpose | The concrete binding record linking one Shopify ProductVariant to one Odoo `product.product`, extending the core binding contract |
| Odoo model it binds to | `product.product` |
| Shopify resource/GID it binds to | Shopify `ProductVariant` (its own, independent `id`/GID — never the parent Product's GID) |
| Why this name follows convention | Same `shopify.connector.<entity>` convention as §5.1; parallels the template-binding name so the pair is visually and structurally symmetric |
| Why alternatives were rejected | See §11 |

## 6. Proposed Python class names (design only, no code)

- `ShopifyConnectorProductTemplateBinding` — in
  `shopify_connector_product_template_binding.py`, following the exact
  PascalCase convention already used (`ShopifyConnectorStore`,
  `ShopifyConnectorStoreSettings`, `ShopifyConnectorBindingMixin`, read
  directly this session).
- `ShopifyConnectorProductVariantBinding` — in
  `shopify_connector_product_variant_binding.py`, same convention.

Both classes are proposed to declare `_inherit = 'shopify.connector.binding.mixin'`
(classic Odoo inheritance onto the abstract contract, adding the fields in
§7 below), consistent with how `shopify.connector.store.settings` already
extends nothing itself but is designed to be `_inherit`-extended by domain
modules (`shopify_connector_store_settings.py`'s own docstring).

## 7. Proposed fields

### 7.1 `shopify.connector.product.template.binding`

**A. Inherited from `shopify.connector.binding.mixin`** (confirmed field set,
read directly from
`addons/shopify_connector_core/models/shopify_connector_binding_mixin.py`
this session):

- `store_id` (Many2one → `shopify.connector.store`, required, index,
  `ondelete='restrict'`)
- `shopify_gid` (Char, required, index, readonly) — holds the Shopify
  **Product** GID for this concrete model
- `status` (Selection: `active`/`stale`/`manually_overridden`/`review`,
  required, index, default `active`)
- `match_key` (Selection: `existing_binding`/`sku_reference`/`barcode`/
  `email`/`manual`, readonly) — for product matching, only
  `existing_binding`/`sku_reference`/`barcode`/`manual` apply; `email` is a
  customer-binding value, inherited unchanged from the shared mixin
  vocabulary, simply never populated by this model
- `matched_by_uid` (Many2one → `res.users`, readonly)
- `matched_at` (Datetime, readonly)
- `override_uid` (Many2one → `res.users`, readonly)
- `override_at` (Datetime, readonly)
- `override_previous_candidate` (Char, readonly)

**B. Required new relational fields:**

- `product_template_id` (Many2one → `product.template`, required, index,
  `ondelete='restrict'`) — the Odoo side of this binding.

**C. Shopify identity fields not already inherited:** none required beyond
the inherited `shopify_gid` — no additional identity field is proposed at
template level.

**D. Imported snapshot fields allowed in Task 010** (read-only, informational/
audit only — **never** a second source of truth for matching, per DEC-006's
"convenience reference fields... never written independently" rule):

- `shopify_title` (Char, readonly) — the Shopify product title as of the
  last import, for audit/drift-detection display only; matching never uses
  title/name (`DEC-006 "Match-key priority"`; RA-006 — "name is advisory
  only, never automatic").
- `shopify_status` (Selection: `active`/`archived`/`draft`/`unlisted`,
  readonly) — the Shopify `Product.status` enum snapshot **[Official
  fact, cited via `master-blueprint-product-customer-sale.md` §A.10]**.
  Import-only, informational; does **not** drive any Odoo
  publish/archive side effect in Task 010 (see F).
- `shopify_primary_image_url` (Char, readonly) — a minimal snapshot of the
  primary Shopify image URL at last import, per the accepted "basic image
  import (Shopify → Odoo)" scope
  (`master-blueprint-product-customer-sale.md` §A.2, §A.13; DEC-007 §2).
  Deliberately minimal — see F for what is **not** proposed here.
- `shopify_last_imported_at` (Datetime, readonly).

**E. Fields explicitly out of scope for Task 010:**

- Any price/compare-at price field — Shopify prices are set at the
  **ProductVariant** level, not Product level; see §7.2 instead.
- Any inventory-quantity field — owned by the future
  `shopify_connector_inventory` module (DEC-008).
- Any fulfillment field — owned by the future `shopify_connector_fulfillment`
  module (DEC-008).
- Any customer/order reference — owned by `shopify_connector_sale`
  (DEC-008).
- Any write/export-tracking field (e.g. a "pending export" or "last exported
  at" marker) — belongs to the future product-write/export task (working
  name Task 015), not Task 010.

**F. Fields deferred to later tasks:**

- Richer media modeling (multiple images, alt text, ordering, per-image
  Shopify media GID) — a single `shopify_primary_image_url` snapshot is the
  narrowest defensible design for Task 010's own import-only scope; anything
  richer is deferred to a future media-specific task or to Task 015, and is
  **not** decided here (MBQ-24's own delete-on-omit question is
  export-side, and remains equally open).
- Any field that would drive an Odoo `active`/archive side effect from
  `shopify_status` — Task 010 is import-only and must not invent Odoo-side
  write behavior; this is deferred, not decided, by this proposal.
- Draft-first export-safety fields (`master-blueprint-product-customer-sale.md`
  §A.10) — export-side only, belongs to Task 015.

### 7.2 `shopify.connector.product.variant.binding`

**A. Inherited from `shopify.connector.binding.mixin`:** identical field set
to §7.1.A. Here `shopify_gid` holds the Shopify **ProductVariant** GID —
**independent of, and never substituted for,** the parent Product's GID
(DEC-006/§A.7).

**B. Required new relational fields:**

- `product_variant_id` (Many2one → `product.product`, required, index,
  `ondelete='restrict'`) — the Odoo side of this binding.
- `product_template_binding_id` (Many2one →
  `shopify.connector.product.template.binding`, required, index,
  `ondelete='restrict'`) — the **"product binding relation from variant
  binding to template binding"** required by this session's scope. This
  link lets a variant binding traverse to its parent template binding for
  audit/enumeration purposes **without** collapsing the two identities into
  one record — consistent with DEC-006/§A.7's explicit rule that a template
  binding "does not stand in for its variants' bindings."

**C. Shopify identity fields not already inherited:** none beyond the
inherited `shopify_gid` (holding the ProductVariant GID, per B above).

**D. Imported snapshot fields allowed in Task 010:**

- `shopify_option_values` (Char or Text, readonly) — a snapshot of the
  Shopify variant's option-value combination (e.g. "Size: M / Color: Blue")
  at last import, for audit/display only. Odoo's own
  `product_template_attribute_value_ids` on `product.product` remains the
  authoritative, live representation once bound; this snapshot is never a
  second source of truth for matching or display.
- `shopify_price_snapshot` (Monetary or Float, readonly) — the last-imported
  Shopify variant price, per the accepted "base price/compare-at travels
  with import" scope (`master-blueprint-product-customer-sale.md` §A.2,
  §A.14; DEC-007 §3). **Read-only snapshot only** — Task 010 performs no
  price *write-back* and does not itself enforce the `price_source_of_truth`
  posture already carried on `shopify.connector.store.settings` (confirmed
  present, read directly this session) — that enforcement belongs to the
  future export/update path (Task 015).
- `shopify_compare_at_price_snapshot` (Monetary or Float, readonly) — same
  posture as above, for the compare-at (strike-through) price.
- `shopify_last_imported_at` (Datetime, readonly).
- `shopify_primary_image_url` (Char, readonly) — same minimal posture as
  §7.1.D, for a variant-level image override where Shopify exposes one.

**SKU / barcode — deliberately not duplicated as new fields.** Matching
reads the incoming Shopify SKU/barcode and compares it against Odoo's own
`product.product.default_code`/`product.product.barcode` fields (reached via
`product_variant_id`) directly. No redundant snapshot field is proposed —
this keeps the schema conservative (§13's rationale for the six core models
applies equally here: avoid a shadow copy of data Odoo's own model already
holds authoritatively once bound).

**Title / name — deliberately not duplicated.** Odoo's own
`product.product.display_name` (template name + attribute values) is
derived automatically; no separate "Shopify variant title" field is
proposed, since no Task 010 behavior needs it (name/title is never an
automatic match key — DEC-006/RA-006).

**E. Fields explicitly out of scope for Task 010:**

- Any inventory-quantity field — owned by `shopify_connector_inventory`.
- Any fulfillment field — owned by `shopify_connector_fulfillment`.
- Any customer/order reference — owned by `shopify_connector_sale`.
- Any write/export-tracking field — belongs to the future Task 015.

**F. Fields deferred to later tasks:**

- Richer media modeling — same posture as §7.1.F.
- Variant-level publish/draft status — **not applicable**: Shopify's
  `status` enum is a **Product**-level field, not a ProductVariant-level
  field (`master-blueprint-product-customer-sale.md` §A.10); no such field
  is proposed on the variant binding, deferred or otherwise.

## 8. Constraints and indexes (conceptual only — no SQL syntax invented)

Proposed, not implemented. **Odoo 19 uses `models.Constraint`, not the
deprecated `_sql_constraints` dict** — confirmed directly from this
session's read-only inspection of the merged code
(`shopify_connector_store.py`'s `_shop_domain_uniq`,
`shopify_connector_location.py`'s `_store_location_gid_uniq`, both using
`models.Constraint('UNIQUE(...)', 'message')`). Any future implementation
should follow this same pattern; this document does not invent or confirm
exact PostgreSQL constraint DDL syntax beyond what the existing merged code
already demonstrates.

- **Uniqueness per store and Shopify GID** — one constraint per concrete
  model, mirroring the existing `shopify.connector.location` pattern
  exactly:
  - `product.template.binding`: conceptually `UNIQUE(store_id, shopify_gid)`.
  - `product.variant.binding`: conceptually `UNIQUE(store_id, shopify_gid)`.
  This is exactly what the binding mixin's own docstring anticipates:
  "Composite uniqueness on `(store_id, shopify_gid)` is enforced per
  concrete model, not here."
- **Uniqueness per store and Odoo product/template relation** — prevents one
  Odoo record from being bound twice within the same store (a store-scoped
  uniqueness, not global, consistent with this connector's multi-store
  architecture already evidenced by `store_id` on every core model):
  - `product.template.binding`: conceptually `UNIQUE(store_id, product_template_id)`.
  - `product.variant.binding`: conceptually `UNIQUE(store_id, product_variant_id)`.
- **`product_template_binding_id` on the variant binding** — indexed, **not**
  unique (many variant bindings legitimately share one template binding).
- **`operation_scope_key`/idempotency interaction** — these fields live on
  `shopify.connector.job`, not on the binding models themselves; the binding
  models are pure identity/audit records, never job records. Which entity a
  future product-import job's `res_model`/`res_id` targets (the binding
  model itself, or the underlying `product.template`/`product.product`) is
  **not decided by this document** — it is a residual design point for
  Task 010's own future final implementation prompt to fix, consistent with
  how every other domain-specific job-targeting detail in
  `task-010-product-import-proposed.md` is already marked open for that same
  future prompt.
- **Duplicate-prevention expectation** — the uniqueness constraints above are
  a **backstop**, not the primary duplicate-prevention mechanism; the
  primary mechanism is the match-key sequence + two-tier gate described in
  §9 below, evaluated **before** any create/bind attempt. A unique-constraint
  violation should never be the first line of defense against a duplicate
  create.

## 9. Matching and duplicate-prevention implications

The proposed schema is built to carry, without modification, the already-
accepted matching/duplicate-prevention policy:

- **Existing-binding match** — a `product.template.binding` or
  `product.variant.binding` row already present for `(store_id,
  shopify_gid)` is checked first, per the accepted match-key priority
  **existing binding → SKU/internal reference → barcode → manual match**
  (DEC-003; DEC-006 "Match-key priority"; RA-006).
- **SKU/internal reference match** — read from the incoming Shopify payload,
  compared against `product.product.default_code` (variant level only —
  Shopify SKUs are variant-scoped); a confident match records
  `match_key = 'sku_reference'`.
- **Barcode match** — same mechanism, `product.product.barcode`, records
  `match_key = 'barcode'`.
- **Manual review for ambiguous matches** — more than one plausible
  candidate sets `status = 'review'` (the mixin's own vocabulary — this
  proposal does not invent a new status value) and `match_key` is left
  unset pending operator resolution, consistent with the accepted
  `ambiguous match` → `blocked_manual_review` job-level routing
  (`task-010-product-import-proposed.md` §"Manual review cases"). The
  binding row itself is created in `status = 'review'`; the **job** that
  attempted the create/bind is what transitions to `blocked_manual_review`
  (Part A §D job/log abstraction) — the binding record and the job record
  are two distinct, already-accepted concepts, not conflated here.
- **No blind create** — the pre-create duplicate check (the same match-key
  sequence above) runs **before** any binding row is created for an
  automated (webhook/scheduled/reconciliation) import, gated by the
  accepted two-tier eligibility + match-quality gate
  (`master-blueprint-product-customer-sale.md` §A.2, §A.9; MBQ-59, accepted
  at blueprint-policy level by DEC-014). Exact eligibility-check/
  match-confidence thresholds remain open — **this document does not fix
  them** (see §12).
- **Product-template + variant binding integrity** — the required
  `product_template_binding_id` relation on every variant binding (§7.2.B)
  guarantees a variant binding can never exist as an orphan disconnected
  from its parent template binding, while still preserving the two
  identities separately, per DEC-006/§A.7.

## 10. Product import flow implication (design level only)

This section describes the **intended future** Task 010 flow at design
level only. It does not authorize, schedule, or start any implementation.

1. **Import a Shopify product** — read-only GraphQL query against the
   existing Task 003 API client (no new transport code; exact query/field
   list remains open, per `task-010-product-import-proposed.md` §"API calls
   required").
2. **Map/create/bind `product.template`** — run the match-key sequence
   (§9) against `shopify.connector.product.template.binding`; on a
   confident match, bind to the existing `product.template`; on a
   confident no-match, create a new `product.template` and a new binding
   row (gated by §9's no-blind-create policy for automated imports).
3. **Import variants** — for each Shopify ProductVariant under the
   product, read-only, in the same job or a related job (exact job/task
   sequencing is open, deferred to Task 010's own final prompt).
4. **Map/create/bind `product.product` variants** — same match-key
   sequence, against `shopify.connector.product.variant.binding`, always
   populating `product_template_binding_id` to the template binding
   resolved in step 2.
5. **Preserve separate GIDs** — the template binding's `shopify_gid` (the
   Product GID) and each variant binding's `shopify_gid` (that variant's own
   GID) are never conflated, never shared, and never used to infer one
   from the other.
6. **No Shopify write** — no mutation call of any kind is made anywhere in
   this flow; every step above is a read + an Odoo-side create/bind only.
7. **No export/update** — this flow never writes back to Shopify; that is
   exclusively the future Task 015's concern.
8. **Image/price** — imported as read-only snapshot fields only (§7.1.D,
   §7.2.D), per the already-accepted "basic image import"/"base
   price/compare-at travels with import" scope; not synced back, not
   treated as a second source of truth once bound.

## 11. Alternatives rejected

| Alternative | Reason rejected |
| --- | --- |
| **One combined product/variant binding model** | Shopify assigns **independent GIDs** to the Product and each ProductVariant (DEC-006/§A.7); a combined model would have to either duplicate the GID column per variant slot (schema explosion) or lose the ability to key on the variant's own identity independently of its template — directly contradicting the accepted "held separately" rule. |
| **Polymorphic binding model** (one shared table for every domain's bindings) | **Not the accepted direction** — DEC-013's acceptance chose per-domain concrete tables extending one core abstract contract instead (resolves MBQ-11). Reintroducing a shared polymorphic table here would contradict that already-accepted direction without a fresh architecture review, which this document is not. |
| **Storing the variant GID only on `product.product`, without a binding model** | Would have no place to carry `status`, `match_key`, `matched_by_uid`/`matched_at`, or override-tracking — the entire audit/status contract every other domain binding already carries via the mixin. It would also violate DEC-006's "convenience reference fields... never written independently" rule by turning a bare field on `product.product` into an ungoverned second source of truth. |
| **`product.template` binding only, no separate variant binding** | Directly contradicts DEC-006/§A.7: "a template binding does not stand in for its variants' bindings." Without a variant binding, there is no anchor for variant-level ambiguous-match detection, variant-level audit history, or the future variant-level export diff (Task 015) that must operate below the template. |
| **Reusing `shopify.connector.binding.mixin` directly as a concrete, shared table** | The mixin is deliberately an `AbstractModel` with **no table of its own** (confirmed directly from its own docstring, read this session) — this is the DEC-013-accepted per-domain-concrete-on-core-contract shape. Turning it into one shared concrete table would reintroduce the not-chosen polymorphic-table direction through the back door. |
| **Adding product fields directly to `shopify.connector.store` or `shopify.connector.job`** | Violates DEC-008's module-boundary rule — product/variant binding responsibility belongs to `shopify_connector_product`, not `shopify_connector_core`. It would also violate `core-naming-schema-planning.md`'s explicit "Product/customer/order/inventory/fulfillment domain models... explicitly out of scope for a core-only pass," and the already-merged Task 006C skeleton's own accepted posture that core makes no Shopify sync/domain calls. |
| **Putting product binding code inside `shopify_connector_core`** | Same DEC-008 module-boundary rationale as above — `core` is domain-agnostic substrate; `product` is where product/variant binding responsibility is assigned. |

## 12. Impact on Task 010 readiness

- **If this proposal is accepted by ChatGPT**, it would close **only the
  product-template/product-variant portion** of MBQ-55. It would **not**
  close MBQ-55 as a whole — the customer-binding and order-binding portions
  (needed for Tasks 011/012) remain open and require their own, separate
  naming pass.
- **What would still remain before the Task 010 gate can open**, even after
  this proposal's acceptance:
  1. The **product-domain gate** itself must still be opened by a distinct,
     explicit ChatGPT act — this document does not open it. See the
     companion [`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md),
     which proposes criteria for that act only.
  2. **Product first-sync dedup thresholds** (the MBQ-59 residual — exact
     eligibility-check/match-confidence thresholds) still need to be fixed,
     either in Task 010's own future final implementation prompt or
     explicitly scoped there as an in-task design decision — **not fixed by
     this document**.
  3. The **cross-domain enumeration/registration seam** every concrete
     binding model is expected to expose to `core` (count / list-by-store /
     status-by-store, per `master-blueprint-core-substrate.md`'s own
     "Cross-domain enumeration / registration seam" section) is accepted
     architecture but **not yet implemented anywhere in the merged core
     code** (confirmed by this session's read-only inspection). This
     document proposes model/field names only — it does not design or
     implement that seam's exact method signatures. That remains open for
     Task 010's own final implementation prompt, or a preceding, separately
     authorized core-extension note.
  4. Whether a future product-import job's `res_model`/`res_id` targets the
     binding models themselves or the underlying `product.template`/
     `product.product` records remains open (§8) — to be fixed in Task
     010's own final implementation prompt.
- **Product-domain gate criteria still need acceptance** — yes, explicitly.
  See the companion document.
- **Product first-sync dedup thresholds still need to be fixed in the final
  Task 010 prompt** — yes, unchanged from `task-010-product-import-proposed.md`'s
  own existing statement; this document does not weaken or resolve that
  requirement.

## 13. Non-authorizations

This document does not:

- Authorize any code, module, model, view, controller, security file,
  manifest, test, or CI file of any kind.
- Open the Task 010 implementation gate.
- Open the product-domain implementation gate.
- Start Task 010 or any other domain-sync task.
- Authorize any product export or update of any kind.
- Authorize any customer, order, inventory, or fulfillment logic of any
  kind.
- Authorize any UI, wizard, webhook, or OAuth/token-acquisition file or
  behavior of any kind.
- Mark MBQ-55 — in whole or in the product portion addressed here — as
  Accepted or Resolved. MBQ-55 remains Open until ChatGPT explicitly
  accepts this proposal (or a revision of it) via a recorded acceptance
  act, mirroring how `core-naming-schema-planning.md` required its own
  explicit ChatGPT acceptance (AR-019) before MBQ-01/02 closed for the
  core models.
- Claim ChatGPT accepted anything in this session.

---

## Evidence / references

- [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  MBQ-55 row — access: Accessible, this repository, observed 2026-07-09.
- [`master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md)
  §A.1, §A.2, §A.6, §A.7, §A.8, §A.9, §A.10, §A.12, §A.13, §A.14, §J, §K —
  access: Accessible, this repository, observed 2026-07-09.
- [`master-blueprint-core-substrate.md`](../03-architecture/master-blueprint-core-substrate.md)
  §"core defines an abstract binding contract", §"Binding-model granularity
  bound" — access: Accessible, this repository, observed 2026-07-09.
- [`DEC-013-master-blueprint-core-substrate.md`](../04-decisions/DEC-013-master-blueprint-core-substrate.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`DEC-014-master-blueprint-product-customer-sale.md`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`DEC-008-module-boundary-strategy.md`](../04-decisions/DEC-008-module-boundary-strategy.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`core-naming-schema-planning.md`](./core-naming-schema-planning.md) —
  structural pattern this document mirrors — access: Accessible, this
  repository, observed 2026-07-09.
- [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`master-implementation-readiness-checkpoint.md`](./master-implementation-readiness-checkpoint.md) —
  access: Accessible, this repository, observed 2026-07-09.
- `addons/shopify_connector_core/models/shopify_connector_binding_mixin.py`,
  `shopify_connector_store.py`, `shopify_connector_store_settings.py`,
  `shopify_connector_location.py`, `shopify_connector_job.py` — read
  directly (not modified) this session to ground every field name and
  constraint style in the actual merged code — access: Accessible, this
  repository, observed 2026-07-09.
- `addons/shopify_connector_core/security/shopify_connector_security.xml`,
  `security/ir.model.access.csv` — read directly (not modified) this
  session to confirm the four existing groups and access-row naming
  convention — access: Accessible, this repository, observed 2026-07-09.
- `addons/shopify_connector_core/tests/` (file listing and
  `test_job_enqueue.py` header) — read directly (not modified) this
  session to confirm the test-file naming convention — access: Accessible,
  this repository, observed 2026-07-09.

**Next step:** ChatGPT review of this proposal and the companion
[`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md).
