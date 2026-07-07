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

## Status

**Proposed only. Not authorized.** Depends on: Task 002 (credential
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
audited bindings — matching existing Odoo catalog records where possible,
creating new ones where safe, and never silently creating duplicates or
silently overwriting catalog data on the controlled export/update path —
establishing the product/variant identity foundation that the customer,
order, inventory, and fulfillment domains all resolve *through* rather
than duplicate (`shopify_connector_sale` and later `inventory` resolve
product/variant bindings through `product` — "sibling reuse via
`product`," Part A §K.9, restated Part B §A.8).

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
convention. Once authorized, its files would be limited to: its own
manifest and init files; model file(s) implementing the product-template
binding and the product-variant binding as two separate concrete models
extending `shopify.connector.binding.mixin` (Part B §A.1); its own
security/access CSV entries scoped to those new models only, reusing the
four existing groups (no new group); its own job-type registration via
`selection_add` on the core `job_type` field; its own tests directory. No
exact file names are fixed here — that is MBQ-55, still open.

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
update once this task actually runs).

## Product/variant import boundary

Two separate concrete bindings, not one — Shopify Product ↔ Odoo product
template, and Shopify ProductVariant ↔ Odoo product variant — held
separately because Shopify assigns independent GIDs to each, and the
controlled export/update diff must render at the variant level to avoid
`productSet`'s delete-on-omit data loss (Part B §A.1, §A.7). A template
binding does not stand in for its variants' bindings. Scope: import
(Shopify → Odoo) and controlled export/update (Odoo → Shopify) of
product/variant catalog data only — no customer, order, inventory
quantity, or fulfillment data is touched by this task.

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
level"): (1) **interactive/batch path** — any interactive or batch
create/bind action always shows a blocking preview before the operator
confirms; (2) **automated path** (webhook/scheduled/reconciliation-triggered)
— a pre-create duplicate check runs before creating/binding, gated by a
two-tier gate (eligibility conditions, then match-quality conditions).
Retrospective sync-center/dashboard visibility alone does **not** satisfy
the no-blind-create requirement. No feature flag/setting/config may allow
an automated import to skip either check (Part A §I.5 no-bypass rule).
Exact eligibility-check/match-confidence thresholds remain open for this
task's own final §9 prompt (MBQ-59 residual).

## Manual review cases

- Ambiguous product/variant match (more than one plausible candidate) →
  `ambiguous match` → `blocked_manual_review`.
- Duplicate-risk create → `duplicate risk` → `blocked_manual_review`.
- Destructive-write guard blocked (a `productSet`/bulk-variant write that
  would delete-by-omission an existing field/media) →
  `destructive-write guard blocked` → `blocked_manual_review`
  (product-only in the accepted error table, Part B §I).
- Unsupported/malformed product payload shape → `data shape/schema
  mismatch` → `failed_retryable`.

## API calls required

**Open** — not yet confirmed by accepted architecture docs at the exact
field/mutation level. Research notes indicate: reads (product/variant
queries) are needed for import and matching; controlled writes for
export/update are expected to use `productSet` and/or the bulk-variant
mutations (`productVariantsBulkUpdate`, `productVariantsBulkCreate`),
with the variant-write mutation strategy only "partially resolved"
(MBQ-23 — direction accepted, exact batching/error-handling open) and
neither mutation documented to carry an idempotency guarantee (Part B
§A.5.2, verified against the official Shopify reference page, access date
2026-07-03). None of this is final until Task 003's API client exists and
this task's own final §9 prompt fixes the exact calls.

## UI dependencies

Yes, for the Matching center (S6) and Product preview/diff (S7) screens
(`ui-ux-implementation-task-map.md` Group 10) — both require the UI
implementation gate (currently closed) plus the product domain gate. Per
the Task 001 "core-only, zero-UI" precedent, the underlying binding/import
backend logic is not necessarily gated on the UI implementation gate
itself — but no repo document states a general policy on this either way
(**Open — not yet decided in the repo**).

## Tests required

Per the accepted `pr-review-checklist.md` §C pattern: variant-level diff
correctness against `productSet` delete-on-omit risk; the MBQ-59
pre-create duplicate-check/two-tier gate; ambiguous-match and
duplicate-risk manual-review routing; destructive-write guard blocking;
access-control matrix across the four existing groups; confirmation that
this module's code never constructs a Shopify request itself (it consumes
the core API client only). Exact test names/fixtures are for this task's
own final §9 prompt. Per the Task 001A precedent, if no Odoo runtime
exists at coding time, tests must still be written and syntax-validated,
and the manual-validation checklist below becomes mandatory review
evidence — inventing a non-Odoo test harness is not acceptable.

## Manual validation

On a live Odoo 19 + PostgreSQL instance once a runtime exists: install the
module alongside `shopify_connector_core`; confirm no view/menu/action/
controller/cron artifact exists; confirm the two binding models appear
with correct `store_id`/`shopify_gid` uniqueness; confirm a simulated
ambiguous match routes to manual review and a simulated destructive write
is blocked; confirm no direct Shopify HTTP call exists outside the core
API client.

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
- No destructive catalog write ever proceeds without either a blocking
  preview (interactive/batch) or a passed two-tier gate (automated).
- Zero customer/order/inventory/fulfillment logic in the diff.
- Zero direct Shopify HTTP/GraphQL code outside calls made through the
  accepted core API client.
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

- **No customer/order/inventory/fulfillment logic** of any kind.
- **No payouts/refunds.**
- **No webhooks unless separately authorized** — product webhooks
  (`PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/`PRODUCTS_DELETE`) are a distinct,
  separately-decided posture (DEC-020/MBQ-65: enqueue-only triggers,
  never direct Odoo writes, follow-up authoritative read required,
  reconciliation remains the backstop) — not built by this task unless a
  future §9 prompt explicitly includes it.
- **No direct Shopify write outside the approved API client**
  (`shopify.connector.api.client` in `shopify_connector_core`).
- **No UI beyond separately-gated screens** (Matching center S6, Product
  preview/diff S7 — Group 10, both requiring their own future gate act).
