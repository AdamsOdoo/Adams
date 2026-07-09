# MBQ-55 — Customer Binding Naming & Schema Proposal

> **Documentation-only naming/schema proposal**, prepared per the route MBQ-55's
> own row names: *"a dedicated, documentation-only domain naming/schema
> planning pass (PR #85 pattern, extending the accepted `shopify.connector.*`
> conventions and binding-mixin contract), to be accepted before the
> product/customer/order slice starts"*
> ([`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
> MBQ-55 row). This document mirrors the structural pattern of
> [`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md)
> (the accepted product-template/product-variant portion of MBQ-55, PR #136),
> applied here to the **customer-binding portion only**.
>
> **Scope note:** MBQ-55 as registered covers four Sprint-B-defined binding
> models — product-template binding, product-variant binding, customer
> binding, and order binding. The product-template/product-variant portion is
> **already Accepted** (`mbq-55-product-binding-naming-schema-proposal.md`,
> PR #136, comment `4924917266`). This document addresses **only the
> customer-binding portion**. The **order-binding portion of MBQ-55 remains
> fully open** and is not addressed, narrowed, or implied resolved by this
> document — a future, separate naming pass is required before Task 012
> (order import) can reach the same precision.

## 1. Status

- **Proposed only. Not yet reviewed or accepted by ChatGPT.** This document
  is drafted in the same session as, and for review alongside,
  [`task-011-customer-import-proposed.md`](./task-011-customer-import-proposed.md),
  [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md),
  and
  [`task-011-customer-import-gate-readiness.md`](./task-011-customer-import-gate-readiness.md),
  mirroring exactly how the product-template/product-variant naming proposal
  and the product-domain gate-criteria proposal were drafted together and
  later accepted together in PR #136 (AR-034).
- **Does not by itself close any portion of MBQ-55.** Closure requires a
  distinct, explicit ChatGPT acceptance act, as happened for the product
  portion.
- **Does not authorize implementation of any kind.**
- **Does not open the Task 011 implementation gate.**
- **Does not open the customer-domain gate** (see the companion document,
  [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md)
  — its criteria are proposed only; the gate itself would remain closed even
  if this proposal and that one were both accepted, until a distinct, future,
  explicit ChatGPT gate-opening act confirms every criterion satisfied).
- **Does not create any module, file, model, or code.** Every model name,
  file name, class name, and field name below is a **proposed name only**,
  not a committed artifact — nothing in this document exists in the addon
  tree; a future, separately-authorized implementation session still has to
  create the actual files.
- **Does not authorize any customer export, order/inventory/fulfillment
  logic, or any UI/wizard/webhook/OAuth file or behavior.**

## 2. Purpose

This document proposes a closure path for **only** the customer-binding
portion of MBQ-55:

- Exact Odoo model name for the customer binding model.
- Exact future file names for the module that would implement it.
- Exact class name, as design only (no code).
- Exact binding fields, separated into inherited-from-mixin, new relational,
  identity, imported-snapshot, out-of-scope, and deferred buckets.
- The relationship between the proposed model and the existing core
  `shopify.connector.binding.mixin` abstract contract.
- The relationship between the proposed model and Odoo's own `res.partner`
  model.
- The fallback-partner configuration concept's proposed home (a store-settings
  field, not a binding-model field — see §7.3).

It does not propose order-binding names (see the scope note above), does not
decide any architecture question DEC-003 through DEC-025 has not already
decided, and does not re-litigate the accepted customer-domain blueprint
(DEC-014 §B). It only converts already-accepted *directions* into *exact*
proposed identifiers, exactly as `mbq-55-product-binding-naming-schema-proposal.md`
did for the two product-domain models.

## 3. Accepted source constraints

Every constraint below is cited from an already-accepted source. This
proposal does not reinterpret or weaken any of them.

- **Module boundary strategy** — customer import/matching is **folded into
  `shopify_connector_sale`** for Phase 1; there is **no** separate
  `shopify_connector_customer` module **[Accepted — DEC-008;
  `master-blueprint-product-customer-sale.md` §B.1: "Customer import/
  matching is folded into `shopify_connector_sale` for Phase 1... `sale`
  defines its own concrete customer binding model... extending the core
  abstract binding contract"]**. A future promotion of customer to its own
  module was evaluated and classified "weakened/deferred, not rejected" — this
  document does not propose promoting it
  (`ar004-module-boundary-decision-brief.md`, cited in
  `task-011-customer-import-matching-proposed.md` §Preconditions).
- **Customer binding is not routed through `product`** — unlike order lines
  (which resolve product/variant bindings through `product`, "sibling reuse
  via `product`"), the customer binding model is defined directly by `sale`,
  since customers have no product-domain counterpart **[Accepted — DEC-008;
  Blueprint proposal, `master-blueprint-product-customer-sale.md` §B.8]**.
- **One concrete binding model per synchronized root entity** — customer is
  its own synchronized root entity, distinct from product/variant/order/
  inventory-level/FulfillmentOrder **[Accepted — DEC-013, binding-model
  granularity bound, `master-blueprint-core-substrate.md`]**.
- **The core binding mixin must be reused** — the customer binding model
  extends `shopify.connector.binding.mixin` directly (an `AbstractModel` with
  no table of its own; composite `(store_id, shopify_gid)` uniqueness "is
  enforced per concrete model, not here," per the mixin's own docstring, read
  directly and unchanged this session) **[Accepted — DEC-013]**.
- **No polymorphic binding table** — the single polymorphic table option
  (DEC-006 Option B) is not chosen; per-domain concrete tables extending one
  core abstract contract are the accepted direction (resolves MBQ-11)
  **[Accepted — DEC-013]**.
- **Matching priority: existing binding → email → manual review** — the
  customer-specific instance of DEC-006's match-key priority; name is
  advisory only, never automatic; phone is advisory/manual-only, never
  automatic **[Accepted — DEC-006 "Decision summary"; DEC-012 §6.4; DEC-014
  point E (MBQ-31, "email is the sole automatic customer match key... phone
  and name stay advisory/manual-only, never automatic"); RA-006]**.
- **No customer export in Phase 1** — Shopify → Odoo import/matching only,
  never pushed back **[Accepted — DEC-003; `master-blueprint-product-customer-sale.md`
  §B.4, "unchanged deferral"]**.
- **No name-only automatic matching** — structural exclusion, unchanged
  **[Accepted — DEC-003; DEC-006; RA-006; `master-blueprint-product-customer-sale.md`
  §B.5]**.
- **Single fallback partner per store, no per-order anonymous identity** —
  MBQ-29 is **Resolved** (not merely partially resolved) as of the Final MBQ
  closure pass: *"one single, clearly-flagged fallback partner per store (the
  DEC-014-accepted direction) is the Phase 1 answer; per-order anonymous
  identity is explicitly non-MVP. Fallback use only for genuine no-PII
  orders, never matching failures; audit marker mandatory. Exact partner
  naming = task-spec detail."* **[Accepted — ChatGPT via AR-020 /
  `final-mbq-closure-plan.md`, 2026-07-05, resolving MBQ-29;
  `master-blueprint-open-questions.md` MBQ-29 row]**. This document records
  that resolution explicitly because the older
  [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md)
  §"Fallback partner rules" (drafted 2026-07-XX, before the AR-020 closure
  pass) reported MBQ-29 as unreconciled between a "partially resolved" and a
  "Resolved via AR-020" characterization and asked a future session to
  confirm the register's current state directly. This session did: the
  register's current, final state is **Resolved**, per the row text quoted
  above, read directly this session.
- **Protected-customer-data posture** — orders (and their customer PII —
  name/address/email/phone) are Shopify protected customer data; accessing
  them requires Shopify approval and data-protection controls; without
  approval, production stores return no such data; a store/config lacking
  that access must not fail order import or invent PII **[Official fact —
  `../01-research/shopify-official-api-notes.md`, citing
  `https://shopify.dev/docs/apps/launch/protected-customer-data`;
  `master-blueprint-product-customer-sale.md` §B.6]**.
- **Minimal-field-import discipline** — only the fields the accepted DEC-003/
  DEC-006 matching and order-representation requirements actually need are
  imported; no additional Shopify customer field is proposed beyond what
  matching, basic partner creation, and order-representation require
  **[Inference — CLAUDE.md §7 "no unsupported claims"; DEC-003 minimal-scope
  discipline; `master-blueprint-product-customer-sale.md` §B.10]**.

## 4. Proposed module and files

**Proposed only. Nothing below is created by this document.**

- **Addon/module name:** `shopify_connector_sale` — already named by DEC-008
  and `task-011-customer-import-matching-proposed.md`; this document does not
  change it. The same module will later also own order import (Task 012),
  per DEC-008 — this document does not design, name, or propose anything for
  the order-binding side.
- **Manifest:** `addons/shopify_connector_sale/__manifest__.py` (proposed
  name only — no content is drafted here). **Open item, not fixed by this
  document:** whether Task 011's own manifest declares
  `depends: ['shopify_connector_core']` only (sufficient for customer-only
  scope, since a customer binding never references `product.product`/
  `product.template`), or already declares
  `depends: ['shopify_connector_core', 'shopify_connector_product']` per
  DEC-008's full module-level dependency (`core → product → {sale,
  inventory}`, needed once order-line code referencing product bindings is
  added in Task 012). Both are structurally safe — Odoo manifests may be
  amended when new code is added — and this is a narrow, named in-task
  design decision for Task 011's own future final implementation prompt to
  make explicitly, consistent with `CLAUDE.md` §9's own allowance for this,
  mirroring how Task 010 left its own `res_model`/`res_id` targeting choice
  as a recorded in-task decision rather than guessing it here.
- **Model init:** `addons/shopify_connector_sale/models/__init__.py`
- **Model file (proposed name):**
  `addons/shopify_connector_sale/models/shopify_connector_customer_binding.py`
- **Security expectation (only if a future implementation creates the
  concrete model):**
  `addons/shopify_connector_sale/security/ir.model.access.csv`, reusing the
  four **existing** groups —
  `shopify_connector_core.group_shopify_connector_auditor`/`_operator`/
  `_reviewer`/`_admin` (confirmed present in
  `addons/shopify_connector_core/security/shopify_connector_security.xml`) —
  **no new group is proposed.** Access-row naming would mirror the existing
  core/product convention exactly, e.g.
  `access_shopify_connector_customer_binding_operator`.
- **Test init:** `addons/shopify_connector_sale/tests/__init__.py`
- **Test files (proposed names, mirroring the existing
  `test_<concept>.py` convention confirmed in
  `addons/shopify_connector_core/tests/` and
  `addons/shopify_connector_product/tests/`):**
  - `addons/shopify_connector_sale/tests/test_customer_binding.py`
  - `addons/shopify_connector_sale/tests/test_customer_import_matching.py`
  - `addons/shopify_connector_sale/tests/test_customer_duplicate_prevention.py`
  - `addons/shopify_connector_sale/tests/test_customer_fallback_partner.py`
- **No UI files** — no views, no menus, no actions.
- **No wizard files.**
- **No controller files.**
- **No webhook files.**
- **No OAuth files.**
- **No order-import file of any kind** — order binding, order import, and
  financial-evidence capture are Task 012's future, separately-authorized
  scope, not proposed, named, or started by this document.

None of the files above are created by this document. They are named here
only so a future, separately-authorized Task 011 final implementation prompt
does not have to invent names from nothing.

## 5. Proposed Odoo model name

### 5.1 `shopify.connector.customer.binding`

| Aspect | Proposal |
| --- | --- |
| Model technical name | `shopify.connector.customer.binding` |
| Purpose | The concrete binding record linking one Shopify Customer to one Odoo `res.partner`, extending the core binding contract |
| Odoo model it binds to | `res.partner` |
| Shopify resource/GID it binds to | Shopify `Customer` (its `id`/GID) |
| Why this name follows convention | Matches the `shopify.connector.<entity>` prefix every existing model uses (`shopify.connector.store`, `.store.settings`, `.location`, `.job`, `.product.template.binding`, `.product.variant.binding`) and the explicit expectation that later domain modules continue this convention for their own concrete binding models |
| Why alternatives were rejected | See §11 |

## 6. Proposed Python class name (design only, no code)

- `ShopifyConnectorCustomerBinding` — in
  `shopify_connector_customer_binding.py`, following the exact PascalCase
  convention already used (`ShopifyConnectorStore`,
  `ShopifyConnectorProductTemplateBinding`,
  `ShopifyConnectorBindingMixin`).

Proposed to declare `_inherit = 'shopify.connector.binding.mixin'` (classic
Odoo inheritance onto the abstract contract, adding the fields in §7 below).

## 7. Proposed fields

### 7.1 `shopify.connector.customer.binding`

**A. Inherited from `shopify.connector.binding.mixin`** (confirmed field set,
read directly from
`addons/shopify_connector_core/models/shopify_connector_binding_mixin.py`
this session — unchanged since the product naming pass read it):

- `store_id` (Many2one → `shopify.connector.store`, required, index,
  `ondelete='restrict'`)
- `shopify_gid` (Char, required, index, readonly) — holds the Shopify
  **Customer** GID for this concrete model
- `status` (Selection: `active`/`stale`/`manually_overridden`/`review`,
  required, index, default `active`)
- `match_key` (Selection: `existing_binding`/`sku_reference`/`barcode`/
  `email`/`manual`, readonly) — for customer matching, only
  `existing_binding`/`email`/`manual` apply; `sku_reference`/`barcode` are
  product-binding values, inherited unchanged from the shared mixin
  vocabulary, simply never populated by this model
- `matched_by_uid` (Many2one → `res.users`, readonly)
- `matched_at` (Datetime, readonly)
- `override_uid` (Many2one → `res.users`, readonly)
- `override_at` (Datetime, readonly)
- `override_previous_candidate` (Char, readonly)

**B. Required new relational fields:**

- `partner_id` (Many2one → `res.partner`, required, index,
  `ondelete='restrict'`) — the Odoo side of this binding.

**C. Shopify identity fields not already inherited:** none required beyond
the inherited `shopify_gid` — no additional identity field is proposed.

**D. Imported snapshot fields allowed in Task 011** (read-only, informational/
audit only — **never** a second source of truth for matching, per DEC-006's
"convenience reference fields... never written independently" rule):

- `shopify_display_name` (Char, readonly) — the Shopify customer's display
  name as of the last import, for audit/drift-detection display only;
  matching never uses name (RA-006; `master-blueprint-product-customer-sale.md`
  §B.5, "a name/email-adjacent similarity may be shown as an advisory hint
  during manual match, but is never used to auto-bind").
- `shopify_email_snapshot` (Char, readonly) — a snapshot of the Shopify
  customer's email at last import, for audit/drift-detection only. **Live
  matching always re-reads the current incoming payload's email against
  Odoo's own `res.partner.email` (reached via `partner_id`) at match time —
  never against this snapshot** — mirroring exactly how the product-variant
  binding proposal deliberately does not treat its own snapshot fields as a
  second source of truth for SKU/barcode matching (`mbq-55-product-binding-naming-schema-proposal.md`
  §7.2).
- `shopify_phone_snapshot` (Char, readonly) — a snapshot of the Shopify
  customer's phone at last import, for **advisory-hint display only** during
  manual review (DEC-014 point E: "phone... stay advisory/manual-only,
  never automatic"). Never used to auto-bind, never a fallback automatic key
  if email is absent.
- `shopify_last_imported_at` (Datetime, readonly).

**Name / email — deliberately not duplicated as the authoritative field.**
Matching reads the incoming Shopify email and compares it against Odoo's own
`res.partner.email` (reached via `partner_id`) directly. The
`shopify_email_snapshot` field in D above is an audit/drift-detection
convenience only, never read by the matching logic itself — this keeps the
schema conservative, mirroring §13 of the product naming proposal's own
rationale (avoid a shadow copy of data Odoo's own model already holds
authoritatively once bound).

**E. Fields explicitly out of scope for Task 011:**

- Any order/order-line reference — owned by the future order-binding model
  under `shopify_connector_sale` (Task 012, not this document's scope).
- Any write/export-tracking field — moot, not merely deferred: no customer
  export exists in Phase 1 at all (DEC-003, unchanged).
- Any product/inventory/fulfillment reference — owned by their own domain
  modules (DEC-008).
- Any marketing-consent field — no accepted decision establishes a
  marketing-consent posture anywhere in this project's research; treated as
  out of scope unless a future document states otherwise
  (`task-011-customer-import-matching-proposed.md` §"Explicit exclusions").
- Any company/person (`is_company`) classification field — **open, not
  decided in the repo** (see §12).
- Any address field (shipping/billing) — **open, not decided in the repo**
  (see §12).

**F. Fields deferred to later tasks:**

- A per-order anonymous-identity mechanism — **not deferred, actually
  rejected as a Phase 1 direction**: MBQ-29 is Resolved (§3 above) with
  per-order anonymous identity "explicitly non-MVP." Recorded here as
  "deferred" only in the sense that a future phase could revisit it via a
  new, ChatGPT-reviewed architecture decision — not as an open Task 011
  design question.
- Multi-key automatic matching (phone as a second automatic key) — evaluated
  and **rejected** by DEC-014 point E, not merely deferred (§3 above); no
  revisit condition is named in DEC-014 itself.

### 7.2 Relation to `res.partner`

- **One binding per Odoo partner, per store** (§8 uniqueness). The binding
  model is the authoritative cross-system identity link; `res.partner`
  itself carries no required Shopify-specific field — consistent with
  DEC-006's "convenience reference fields... never the authoritative source"
  rule and with the product-binding proposal's identical posture toward
  `product.template`/`product.product`.
- **No `is_company`/address logic is proposed or assumed.** This document
  does not decide how an ordinary Shopify customer becomes a `res.partner`
  record (company vs. individual, `is_company` semantics, contact
  hierarchies, or address child-contact creation) — see §12, "Open, not yet
  decided in the repo," restated unchanged from
  `task-011-customer-import-matching-proposed.md` §"Company/person
  handling" and §"Address handling."

### 7.3 Fallback-partner configuration — proposed home: `shopify.connector.store.settings`, not the binding model

The single, clearly-flagged fallback partner per store (§3; DEC-014 §B.7;
MBQ-29 Resolved) is **not** a `shopify.connector.customer.binding` row —
there is no Shopify Customer GID to bind it to, since it exists precisely
for the case where Shopify withholds all customer data. Proposed instead,
mirroring the pattern DEC-014 §C.10 already uses for the gateway → journal
mapping (a per-store configuration field contributed via the core
settings-extension seam):

- **Proposed field:** `customer_fallback_partner_id` (Many2one →
  `res.partner`) on `shopify.connector.store.settings`, contributed by
  `shopify_connector_sale` via the accepted `_inherit` settings-extension
  seam (confirmed present and already used this way by
  `shopify.connector.store.settings`'s own docstring, read directly this
  session; the same seam DEC-014 §C.10 names for the order-domain gateway
  mapping).
- **Why store-settings, not a binding-model or `res.partner` field:** the
  fallback partner is a single, per-store configuration concept, not a
  per-Shopify-record identity link — `shopify.connector.store.settings` is
  already the accepted, store-scoped home for comparable per-store
  configuration concepts (DEC-013 §I.3; the already-proposed gateway→journal
  mapping, DEC-014 §C.10). A field directly on `res.partner` (e.g. an
  `x_shopify_is_fallback_customer` boolean) was considered and not proposed,
  because it would not be store-scoped in a future multi-store world, and
  DEC-006 only permits business-record convenience fields as a **read**
  convenience, never as the primary configuration mechanism.
- **The order-level audit marker** ("no customer data available — fallback
  used," DEC-014 §B.7) that must appear on every order bound to the fallback
  partner is an **order-binding-model field**, not a field on
  `shopify.connector.customer.binding` or on `shopify.connector.store.settings`
  — **out of scope for this document**, deferred to the future Task 012
  order-binding naming pass (the order-binding portion of MBQ-55, which
  remains fully open per the scope note at the top of this document).
- **Exact field type/default and the exact partner-creation mechanism**
  (whether the fallback partner record is auto-created on first
  domain-enablement, or must be manually configured before Task 011 can run)
  remain **open for Task 011's own future final implementation prompt** —
  this document proposes the field's name and home model only.

## 8. Constraints and indexes (conceptual only — no SQL syntax invented)

Proposed, not implemented. Odoo 19 uses `models.Constraint`, not the
deprecated `_sql_constraints` dict (confirmed directly from the merged core
code this session, unchanged since the product naming pass's own inspection).

- **Uniqueness per store and Shopify GID** — conceptually
  `UNIQUE(store_id, shopify_gid)`, mirroring the existing
  `shopify.connector.location` and product-binding pattern exactly. This is
  exactly what the binding mixin's own docstring anticipates.
- **Uniqueness per store and Odoo partner relation** — conceptually
  `UNIQUE(store_id, partner_id)` — prevents one `res.partner` from being
  bound twice within the same store (store-scoped, not global, consistent
  with this connector's multi-store architecture).
- **`operation_scope_key`/idempotency interaction** — lives on
  `shopify.connector.job`, not on the binding model itself, mirroring the
  product-binding proposal's identical posture. Whether a future
  customer-import job's `res_model`/`res_id` targets the binding model
  itself or the underlying `res.partner` record is **not decided by this
  document** — a residual design point for Task 011's own future final
  implementation prompt, mirroring exactly how Task 010 resolved the
  equivalent question in-task (product-import validation results §C.1) —
  this document does not pre-empt that choice for customer import.
- **Duplicate-prevention expectation** — the uniqueness constraints above
  are a **backstop**, not the primary duplicate-prevention mechanism; the
  primary mechanism is the match-key sequence + two-tier gate described in
  §9 below, evaluated **before** any create/bind attempt.

## 9. Matching and duplicate-prevention implications

The proposed schema is built to carry, without modification, the already-
accepted matching/duplicate-prevention policy:

- **Existing-binding match** — a `shopify.connector.customer.binding` row
  already present for `(store_id, shopify_gid)` is checked first, per the
  accepted match-key priority **existing binding → email → manual review**
  (DEC-006; DEC-012 §6.4; DEC-014 point E).
- **Email match** — read from the incoming Shopify payload, compared
  against `res.partner.email`; a confident match records
  `match_key = 'email'`. Email is the **sole** automatic match key — phone
  and name are advisory-hint-only, never automatic (DEC-014 point E; §3
  above).
- **Manual review for ambiguous matches** — more than one plausible
  candidate sets `status = 'review'` (the mixin's own vocabulary — this
  proposal invents no new status value) and `match_key` is left unset
  pending operator resolution, consistent with the accepted `ambiguous
  match` → `blocked_manual_review` job-level routing. The binding row
  itself is created in `status = 'review'`; the **job** that attempted the
  create/bind is what transitions to `blocked_manual_review` — the binding
  record and the job record are two distinct, already-accepted concepts,
  not conflated here (mirrors the product-binding proposal's identical
  distinction, §9).
- **No blind create** — the pre-create duplicate check (the same match-key
  sequence above) runs **before** any binding row is created for an
  automated (webhook/scheduled/reconciliation) import, gated by the accepted
  two-tier eligibility + match-quality gate (`master-blueprint-product-customer-sale.md`
  §B.2, §B.9; MBQ-59, accepted at blueprint-policy level by DEC-014,
  "applies identically to Customer §B.2, substituting the customer domain").
  Exact eligibility-check/match-confidence thresholds remain open — **this
  document does not fix them** (see §12).
- **No-PII fallback is a separate path, never a matching outcome** — the
  fallback partner (§7.3) is used only when Shopify genuinely withholds all
  customer PII for an order; it is never a routing outcome of the match-key
  sequence above, and it never substitutes for the manual-review outcome of
  an ordinary ambiguous match (DEC-014 §B.7: "never as a default for an
  ordinary matching failure, which instead creates a new, properly matched
  partner or routes to manual review if ambiguous"). This document keeps
  these two concepts structurally separate: the binding model (§7.1) governs
  registered-customer matching; the store-settings fallback field (§7.3)
  governs the distinct no-PII case.

## 10. Customer import flow implication (design level only)

This section describes the **intended future** Task 011 flow at design
level only. It does not authorize, schedule, or start any implementation.

1. **Receive Shopify customer data** — most commonly as part of order
   import (Shopify orders carry customer data), but may also run standalone
   as a dedicated customer sync/reconciliation pass (`master-blueprint-product-customer-sale.md`
   §B.2) — both paths use the same matching logic below. Read-only against
   the existing Task 003 API client; exact GraphQL query/field list remains
   open (§12).
2. **Run the match-key sequence** (§9) against
   `shopify.connector.customer.binding`: existing binding first, then email,
   then manual review.
3. **On a confident match** — bind to the existing `res.partner`.
4. **On a confident no-match** — create a new `res.partner` and a new
   binding row, gated by §9's no-blind-create policy for automated imports
   (§9, MBQ-59).
5. **On an ambiguous match** — create the binding row in `status = 'review'`,
   populate no `match_key`, and route the job to `blocked_manual_review`.
6. **On genuine no-PII data** — resolve to the store's configured
   `customer_fallback_partner_id` (§7.3) instead of running the match-key
   sequence at all; this path never creates or touches a
   `shopify.connector.customer.binding` row, since there is no Shopify
   Customer GID to bind.
7. **No Shopify write** — no mutation call of any kind is made anywhere in
   this flow; every step above is a read + an Odoo-side create/bind only,
   consistent with the unchanged DEC-003 "no customer export" deferral.
8. **No order logic** — this flow never creates, matches, or touches a sale
   order; that is exclusively Task 012's future, separately-authorized
   scope.

## 11. Alternatives rejected

| Alternative | Reason rejected |
| --- | --- |
| **A separate `shopify_connector_customer` module** | **Not the accepted direction** — DEC-008 explicitly folds customer import/matching into `shopify_connector_sale` for Phase 1; `ar004-module-boundary-decision-brief.md` classifies a future split as "weakened/deferred, not rejected," which this document does not propose promoting. |
| **Routing the customer binding through `shopify_connector_product`** | Directly contradicts `master-blueprint-product-customer-sale.md` §B.8: customer binding responsibility rests with `sale` directly, "not routed through `product`, unlike product/variant bindings which `sale` resolves through `product`... since customers have no product-domain counterpart." |
| **Polymorphic binding model** (one shared table for every domain's bindings) | **Not the accepted direction** — DEC-013's acceptance chose per-domain concrete tables extending one core abstract contract instead (resolves MBQ-11). Reintroducing a shared polymorphic table here would contradict that already-accepted direction without a fresh architecture review, which this document is not. |
| **Storing the Shopify Customer GID only on `res.partner`, without a binding model** | Would have no place to carry `status`, `match_key`, `matched_by_uid`/`matched_at`, or override-tracking — the entire audit/status contract every other domain binding already carries via the mixin. It would also violate DEC-006's "convenience reference fields... never written independently" rule by turning a bare field on `res.partner` into an ungoverned second source of truth. |
| **A single "customer or fallback" boolean/state on `res.partner` itself** | Conflates a per-store configuration concept (which partner is the fallback) with a per-Shopify-record identity concept (the binding model); would not be store-scoped in a future multi-store world; DEC-006 permits business-record convenience fields only as a read convenience, never as the primary mechanism. See §7.3 for the proposed store-settings home instead. |
| **Reusing `shopify.connector.binding.mixin` directly as a concrete, shared table** | The mixin is deliberately an `AbstractModel` with **no table of its own** — this is the DEC-013-accepted per-domain-concrete-on-core-contract shape. Turning it into one shared concrete table would reintroduce the not-chosen polymorphic-table direction through the back door. |
| **Adding customer fields directly to `shopify.connector.store` or `shopify.connector.job`** | Violates DEC-008's module-boundary rule — customer binding responsibility belongs to `shopify_connector_sale`, not `shopify_connector_core`. `core` remains domain-agnostic substrate only. |
| **Making phone a second automatic match key** | Evaluated and **rejected** by DEC-014 point E: phone reliability/availability is gated by the same protected-customer-data approval as email, with no demonstrated additional dedup value over email alone — would introduce a second point of match-key drift without a cited safety benefit. |
| **Per-order anonymous fallback identity instead of one shared fallback partner** | Evaluated and **resolved against** by MBQ-29's Final MBQ closure (AR-020, 2026-07-05): "per-order anonymous identity is explicitly non-MVP." A single, clearly-flagged fallback partner per store is the accepted Phase 1 answer. |

## 12. Impact on Task 011 readiness

- **This proposal is not yet Accepted by ChatGPT.** It closes nothing by
  itself — see
  [`task-011-customer-import-gate-readiness.md`](./task-011-customer-import-gate-readiness.md)
  for the full readiness assessment this proposal feeds into.
- **What would still remain before a Task 011 gate could open, even after
  this proposal's eventual acceptance:**
  1. The **customer-domain gate** (the customer-import-scoped portion of the
     "sale domain gate" named in `ui-ux-implementation-task-map.md` Group 11)
     must still be opened by a distinct, explicit ChatGPT act — this
     document does not open it. See the companion
     [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md).
  2. **Customer first-sync dedup/match-confidence thresholds** (the MBQ-59
     residual, customer-domain instance) still need to be fixed, either in
     Task 011's own future final implementation prompt or explicitly scoped
     there as an in-task design decision — **not fixed by this document**.
  3. The **cross-domain enumeration/registration seam** every concrete
     binding model is expected to expose to `core` is accepted architecture
     but **not yet implemented anywhere in the merged core code** (same
     finding as the product naming pass) — remains open for Task 011's own
     final implementation prompt.
  4. Whether a future customer-import job's `res_model`/`res_id` targets the
     binding model itself or the underlying `res.partner` record remains
     open (§8) — to be fixed in Task 011's own final implementation prompt.
  5. The manifest product-dependency question (§4) — an explicit, named
     in-task decision, not fixed here.
  6. **Address handling** and **company/person (`is_company`) classification**
     remain **open — not yet decided anywhere in this repository** (restated
     unchanged from `task-011-customer-import-matching-proposed.md`) — must
     be explicitly scoped (resolved, or explicitly excluded/deferred) in
     Task 011's own future final implementation prompt before code, not
     silently assumed either way.

## 13. Non-authorizations

This document does not:

- Authorize any code, module, model, view, controller, security file,
  manifest, test, or CI file of any kind.
- Open the Task 011 implementation gate.
- Open the customer-domain gate.
- Start Task 011 or any other domain-sync task.
- Authorize any customer export of any kind.
- Authorize any order, product, inventory, or fulfillment logic of any kind.
- Authorize any UI, wizard, webhook, or OAuth/token-acquisition file or
  behavior of any kind.
- Mark MBQ-55 **as a whole** as Accepted or Resolved. Only the
  product-template/product-variant portion is Accepted (already, via PR
  #136). This document proposes closure for the **customer-binding**
  portion only, and does not itself accept it. The **order-binding** portion
  of MBQ-55 remains Open, requiring its own future, separate naming pass.
- Overstate this proposal as authorizing Task 011, opening the Task 011
  implementation gate, or opening the customer-domain gate — none of those
  follow from drafting this proposal; each remains its own distinct,
  separate, future ChatGPT act.

---

## Evidence / references

- [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  MBQ-55, MBQ-29, MBQ-31 rows — access: Accessible, this repository, observed
  2026-07-09.
- [`master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md)
  §B.1–§B.13 — access: Accessible, this repository, observed 2026-07-09.
- [`DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md),
  [`DEC-008-module-boundary-strategy.md`](../04-decisions/DEC-008-module-boundary-strategy.md),
  [`DEC-013-master-blueprint-core-substrate.md`](../04-decisions/DEC-013-master-blueprint-core-substrate.md),
  [`DEC-014-master-blueprint-product-customer-sale.md`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md) —
  structural pattern this document mirrors — access: Accessible, this
  repository, observed 2026-07-09.
- [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md) —
  prior scope draft, cited and updated, not edited, by this document —
  access: Accessible, this repository, observed 2026-07-09.
- `addons/shopify_connector_core/models/shopify_connector_binding_mixin.py`,
  `shopify_connector_store.py`, `shopify_connector_store_settings.py` — read
  directly (not modified) this session to ground every field name and
  constraint style in the actual merged code — access: Accessible, this
  repository, observed 2026-07-09.
- `addons/shopify_connector_core/security/shopify_connector_security.xml` —
  read directly (not modified) this session to confirm the four existing
  groups — access: Accessible, this repository, observed 2026-07-09.
- `../01-research/shopify-official-api-notes.md` (protected-customer-data
  citation) — access: Accessible, this repository, observed 2026-07-09.

**Next step:** ChatGPT review of this proposal alongside
[`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md),
mirroring the PR #136 review pattern. If accepted, a future session may draft
Task 011's file-exact final implementation prompt and a customer-domain
gate-opening proposal using the accepted names — the customer-domain gate
itself still requires its own separate, explicit ChatGPT gate-opening act,
confirming every criterion in the gate-criteria document satisfied, before it
opens or Task 011 is authorized.
