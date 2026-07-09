# Task 010 — Product Import / Variant Binding (Proposed)

> Planning-only future implementation task spec, part of the MVP domain
> implementation-slicing sequence
> ([`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md),
> Area 1). This document does **not** reach the exact file/field
> precision of the `CLAUDE.md` §9 template because
> [MBQ-55](../03-architecture/master-blueprint-open-questions.md) (exact
> Odoo model/field names for the product-template and product-variant
> binding models) is still open — it describes scope, boundary, and
> approach only. A future final §9 task prompt must fix exact model/field
> names and allowed files before this task may start.
>
> **Revision note (ChatGPT REVISE on PR #93):** this task is scoped to
> **product import and variant binding only** — Shopify → Odoo, read-only
> against Shopify. Controlled product/variant **export, update, and any
> write back to Shopify** (including `productSet` and the bulk-variant
> mutations) is **not** part of Task 010. It is deferred to a separate,
> not-yet-authorized future candidate task (proposed working name: **Task
> 015 — Product Write/Update/Export Safety**), which would require its
> own separate ChatGPT decision/gate before it is even proposed at
> §9-template precision. Everywhere this document previously described
> export/update/write behavior, that material has been narrowed to
> forward-looking risk documentation only — never a Task 010 acceptance
> criterion.

## Status

**Proposed only. Not authorized.** Scope: product import and variant
binding (Shopify → Odoo) only — **no product export, update, or write
back to Shopify of any kind.** Depends on: Task 002 (credential
storage/redaction) and Task 003 (API client/test connection) merged and
gate-opened — no domain job handler may perform any outbound Shopify
call, read or write, until Task 003's own gate opens; the not-yet-defined
"product domain gate" named as a prerequisite in
[`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md)
Group 10 (its own triggering conditions are not specified in any research
note read for this sprint); and a dedicated, documentation-only domain
naming/schema planning pass resolving MBQ-55 for the product-template and
product-variant binding models. This document does not authorize, start,
or imply authorization of any of the above, and does not itself resolve
MBQ-55 or any other open question.

## Objective

Import Shopify products and their variants into Odoo as controlled,
audited **read-only** bindings — matching existing Odoo catalog records
where possible, creating new ones where safe, and never silently creating
duplicates — establishing the product/variant identity foundation that
the customer, order, inventory, and fulfillment domains all resolve
*through* rather than duplicate (`shopify_connector_sale` and later
`inventory` resolve product/variant bindings through `product` —
"sibling reuse via `product`," Part A §K.9, restated Part B §A.8). This
task **imports and binds only** — it does not create, update, or delete
any Shopify-side product/variant data.

## Preconditions

- Foundation Tasks 002 and 003 merged, ChatGPT-reviewed, and separately
  gate-opened (per the dependency chain in
  [`credential-connection-foundation-task-plan.md`](./credential-connection-foundation-task-plan.md)).
- The product domain gate named in `ui-ux-implementation-task-map.md`
  Group 10 explicitly opened by ChatGPT.
- MBQ-55 (exact Odoo model/field names for product-template binding and
  product-variant binding) resolved via the dedicated documentation-only
  domain naming/schema planning pass that
  `master-blueprint-open-questions.md`'s own MBQ-55 row calls for "before
  the product/customer/order slice starts."
- [DEC-014](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md)
  / [Part B](../03-architecture/master-blueprint-product-customer-sale.md)
  remain the accepted design baseline; nothing in this document
  reinterprets them.

## Allowed future module/files (boundary only)

Future `shopify_connector_product` module — name accepted per
[DEC-008](../04-decisions/DEC-008-module-boundary-strategy.md);
[`core-naming-schema-planning.md`](./core-naming-schema-planning.md) §3/§13
confirms domain modules are expected to continue the
`shopify_connector_<domain>` / `shopify.connector.<entity>` naming
convention. Once authorized, Task 010's own files would be limited to:
its own manifest and init files; model file(s) implementing the
product-template binding and the product-variant binding as two separate
concrete models extending `shopify.connector.binding.mixin` (Part B
§A.1); its own security/access CSV entries scoped to those new models
only, reusing the four existing groups (no new group); its own job-type
registration via `selection_add` on the core `job_type` field (import job
types only); its own tests directory. No exact file names are fixed here
— that is MBQ-55, still open. **No file implementing a write/export/mutation
code path belongs to Task 010** — that is future Task 015's boundary, not
this one's, and is not fixed here either.

## Forbidden files/scope

Any file under `shopify_connector_core` other than the accepted
`selection_add`/extension seams (job-type registration, error-class
mapping, settings `_inherit`); any file under `shopify_connector_sale`,
`_inventory`, `_fulfillment`, or any other domain module; any
credential/API-client file (owned by Tasks 002/003); any
view/menu/action/wizard/controller/cron file; any file under
`addons/adams_base`; any CI/workflow/Dockerfile/requirements file; any
`docs/04-decisions/*` file or `docs/04-decisions/README.md`;
`docs/03-architecture/master-blueprint-open-questions.md`;
`docs/01-research/research-handoff.md` (other than a mandatory handoff
update once this task actually runs). **Also forbidden to Task 010
specifically:** any product/variant export, update, or write-mutation
code path (including any `productSet` or bulk-variant mutation call) —
that scope belongs only to a future, separately-authorized product-write
task (proposed working name: Task 015), not to this task.

## Product/variant import boundary

Two separate concrete bindings, not one — Shopify Product ↔ Odoo product
template, and Shopify ProductVariant ↔ Odoo product variant — held
separately because Shopify assigns independent GIDs to each (Part B
§A.1, §A.7). A template binding does not stand in for its variants'
bindings. **Scope: import (Shopify → Odoo) of product/variant catalog
data and its binding/matching only.** No customer, order, inventory
quantity, or fulfillment data is touched by this task, and — per the
ChatGPT REVISE on PR #93 — **no product/variant export, update, or write
back to Shopify of any kind is in scope for Task 010.** Product
export/update (including the variant-level diff, delete-on-omit
avoidance, and any controlled write path) is exclusively a future
product-write/export task's concern (proposed working name: Task 015),
not authorized or scoped by this document.

## Binding approach

Both binding models extend the accepted abstract
`shopify.connector.binding.mixin` (`store_id`, `shopify_gid`, `status`,
`match_key`, `matched_by_uid`/`matched_at`, override-tracking fields)
rather than inventing a new binding shape or a polymorphic table, per
DEC-013's "one concrete binding model per synchronized root entity" rule.
Match-key priority (Decision — DEC-003; DEC-006; RA-006, restated Part B
§A.6): **existing binding → SKU/internal reference → barcode → manual
match.** Name is advisory only, never automatic. More than one plausible
candidate routes to manual review; a duplicate-risk create is blocked
pending confirmation.

## Duplicate prevention approach

Two paths (Part B §A.2/§A.9, MBQ-59 "accepted at blueprint-policy
level"), both applying to **import creates only**: (1)
**interactive/batch path** — any interactive or batch create/bind action
always shows a blocking preview before the operator confirms; (2)
**automated path** (webhook/scheduled/reconciliation-triggered) — a
pre-create duplicate check runs before creating/binding, gated by a
two-tier gate (eligibility conditions, then match-quality conditions).
Retrospective sync-center/dashboard visibility alone does **not** satisfy
the no-blind-create requirement. No feature flag/setting/config may allow
an automated import to skip either check (Part A §I.5 no-bypass rule).
Exact eligibility-check/match-confidence thresholds remain open for this
task's own final §9 prompt (MBQ-59 residual). This is a no-blind-**create**
guard — it has no write/export counterpart in Task 010, because Task 010
performs no write.

## Manual review cases

- Ambiguous product/variant match (more than one plausible candidate) →
  `ambiguous match` → `blocked_manual_review`.
- Duplicate-risk create → `duplicate risk` → `blocked_manual_review`.
- Unsupported/malformed product payload shape → `data shape/schema
  mismatch` → `failed_retryable`.

Destructive-write guard blocking (a `productSet`/bulk-variant write that
would delete-by-omission an existing field/media, Part B §I) is **not**
a Task 010 manual-review case, because Task 010 never issues a write —
see "Future product-write/export task concern" below.

## Future product-write/export task concern (out of scope for Task 010)

Documented here strictly as forward-looking risk material for whichever
future task eventually takes on product export/update — **not** a Task
010 acceptance criterion, and **not authorized by this document**:

- `productSet` and the bulk-variant mutations
  (`productVariantsBulkUpdate`, `productVariantsBulkCreate`) carry a
  documented delete-on-omit risk at the variant level (Part B §A.7);
  neither mutation is documented to carry an idempotency guarantee (Part
  B §A.5.2, verified against the official Shopify reference page, access
  date 2026-07-03).
- The variant-write mutation strategy is only "partially resolved"
  (MBQ-23 — direction accepted, exact batching/error-handling open).
- The `destructive-write guard blocked` error class (Part B §I) exists in
  the accepted error taxonomy for this future write path, but Task 010
  never triggers it, since Task 010 makes no write call.
- **Requires a separate ChatGPT decision/gate** before any future task
  (proposed working name: Task 015) may be proposed at §9-template
  precision, let alone authorized.

## API calls required

**Reads only.** Product/variant queries needed for import and matching.
Exact GraphQL query/field list is **Open** — not yet confirmed by
accepted architecture docs at the field level, and is for this task's
own final §9 prompt to fix. **No write/mutation call of any kind
(`productSet`, `productVariantsBulkUpdate`, `productVariantsBulkCreate`,
or any other mutation) is part of Task 010** — those belong only to the
future product-write/export task described above, not to this one.

## UI dependencies

Yes, for the Matching center (S6) screen
(`ui-ux-implementation-task-map.md` Group 10) — requires the UI
implementation gate (currently closed) plus the product domain gate. Per
the Task 001 "core-only, zero-UI" precedent, the underlying binding/import
backend logic is not necessarily gated on the UI implementation gate
itself — but no repo document states a general policy on this either way
(**Open — not yet decided in the repo**). The **Product preview/diff
(S7)** screen renders the export/update diff and therefore belongs to the
future product-write/export task's UI dependency, not Task 010's — Task
010 does not require it and it is not a blocker for product import.

## Tests required

Per the accepted `pr-review-checklist.md` §C pattern: import/matching
correctness across the existing-binding → SKU/internal-reference →
barcode → manual match-key priority; the MBQ-59 pre-create
duplicate-check/two-tier gate; ambiguous-match and duplicate-risk
manual-review routing; access-control matrix across the four existing
groups; confirmation that this module's code never constructs a Shopify
request itself (it consumes the core API client only) and never issues
any write/mutation call. Exact test names/fixtures are for this task's
own final §9 prompt. Per the Task 001A precedent, if no Odoo runtime
exists at coding time, tests must still be written and syntax-validated,
and the manual-validation checklist below becomes mandatory review
evidence — inventing a non-Odoo test harness is not acceptable.

## Manual validation

On a live Odoo 19 + PostgreSQL instance once a runtime exists: install the
module alongside `shopify_connector_core`; confirm no view/menu/action/
controller/cron artifact exists; confirm the two binding models appear
with correct `store_id`/`shopify_gid` uniqueness; confirm a simulated
ambiguous match routes to manual review; confirm no direct Shopify HTTP
call exists outside the core API client, and specifically that no
write/mutation request is ever constructed anywhere in the module.

## Rollback

Single-PR revert; per the accepted domain-boundary DAG only `sale` and
`inventory` depend on `product`, and neither is authorized to start
before this task per the proposed MVP domain sequence, so no dependent
domain logic is affected. Reverting drops the two binding models; any
already-imported product/variant Odoo records remain as ordinary Odoo
data, simply un-bound.

## Acceptance criteria

- Only allowed files changed (per this task's own future final §9
  prompt).
- Two concrete binding models exist, both extending `binding.mixin`, no
  polymorphic table.
- Match-key priority and manual-review routing behave exactly as
  specified above.
- No import create ever proceeds without either a blocking preview
  (interactive/batch) or a passed two-tier gate (automated).
- **Zero product export/update/write code of any kind in the diff** —
  no `productSet` call, no `productVariantsBulkUpdate`/
  `productVariantsBulkCreate` call, no other mutation call.
- Zero customer/order/inventory/fulfillment logic in the diff.
- Zero direct Shopify HTTP/GraphQL code outside read-only calls made
  through the accepted core API client.
- Zero views/menus/actions/wizard/controller/cron artifacts unless the UI
  gate has separately opened and this task's own §9 prompt explicitly
  includes them.

## Definition of done

Per `CLAUDE.md` §9 / `implementation-task-template.md` §7: code + tests
written (and passing where a runtime exists); `pr-review-checklist.md` §C
satisfied; only allowed files (as fixed by this task's own final §9
prompt) changed; handoff updated; technical debt logged; ChatGPT reviews
and accepts the implementation before any next task starts.

## Explicit exclusions

- **No product export.**
- **No product update back to Shopify.**
- **No `productSet` mutation.**
- **No `productVariantsBulkUpdate`/`productVariantsBulkCreate` mutation.**
- **No destructive catalog write handling** except as the future-risk
  documentation captured above — Task 010 issues no write, so it
  triggers no destructive-write guard.
- **No customer/order/inventory/fulfillment logic** of any kind.
- **No payouts/refunds.**
- **No webhooks unless separately authorized** — product webhooks
  (`PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/`PRODUCTS_DELETE`) are a distinct,
  separately-decided posture (DEC-020/MBQ-65: enqueue-only triggers,
  never direct Odoo writes, follow-up authoritative read required,
  reconciliation remains the backstop) — not built by this task unless a
  future §9 prompt explicitly includes it.
- **No direct Shopify write outside the approved API client** — moot for
  Task 010 since Task 010 makes no write call at all; restated for
  clarity against any future task built on top of it.
- **No UI beyond separately-gated screens** (Matching center S6 only for
  Task 010; Product preview/diff S7 belongs to the future
  product-write/export task, Group 10, both requiring their own future
  gate act).

## MBQ-55 product binding schema accepted — Task 010 gate still closed

A documentation-only naming/schema closure proposal for this task's two
binding models,
[`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md),
is **Accepted by ChatGPT** for the product-template/product-variant portion
of MBQ-55 (control-room review, GitHub comment ID `4924917266`, PR #136):
exact model names (`shopify.connector.product.template.binding`,
`shopify.connector.product.variant.binding`), file names, class names, and
fields. **The customer-binding and order-binding portions of MBQ-55 remain
separately open** — a future, separate naming pass is still required
before Tasks 011/012.

The companion
[`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md)
is **Accepted, as criteria only**, via the same acceptance act. Accepting
the criteria list does not confirm every criterion is satisfied, and does
not open the gate.

**The Task 010 gate — and the product domain gate named in this document's
own Preconditions section above — both remain closed.** Both gates open
only via their own future, distinct, explicit ChatGPT gate-opening act,
performed once every relevant criterion (§3 of the companion gate-criteria
document) is confirmed satisfied. This linkage note does not itself open
either gate, does not change this task's Status/Preconditions sections
above, and does not authorize any implementation of any kind. Task 010
still needs a future final implementation prompt that fixes exact
file/allowed/forbidden lists and dedup thresholds, using the now-accepted
names above.
