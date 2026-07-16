# Task 015 — Controlled Product Export/Update: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §8 is NOT usable.** Produced 2026-07-10 (AR-042 candidate).
> Closes OP-21 (Task 015 proposal + naming/criteria) and the MBQ-23/
> MBQ-24 residuals at proposal level. Evidence: captures §5/§9; ARCH
> §1.1 (PD-1 — own module), §3–§7. API 2026-07 (ARCH PD-6). This is
> accepted MVP scope (DEC-003 as corrected by PR #55) — the write-back
> half of the product domain.

## 1. Objective, scope, non-goals

Create `shopify_connector_product_export` (new module, Full edition;
depends `['shopify_connector_core', 'shopify_connector_product']`):
preview-first, allowlisted, guard-protected Odoo→Shopify product
create and update via `productSet`. **Non-goals:** no inventory
quantities of any kind in export payloads (`inventoryQuantities` never
supplied — the inventory ownership boundary; Task 013's domain); no
media/image export in **this** task (D-015-7, revised 2026-07-11:
`productCreateMedia` is deprecated and the current `fileCreate`+attach
path is an async pipeline of its own — media export is **fully
planned as Task 015B**, `task-015b-product-media-export-packet.md`,
locked packet, sequenced after this task and before final
UAT/release, per the PR #148 review item 3; the accepted DEC-003
media scope is completed, not narrowed); no metafields authoring (only the PD-1
`customId` binding metafield, D-015-4); no publishing/sales-channel
management (`publishablePublish`/`write_publications` deferred with
media — exported new products are created `DRAFT`, MBQ-25's accepted
lever); no deletes (`productDelete` never called; archive = status
write); no Markets/B2B/SEO/taxonomy; no UI (S7 preview/diff screen is
UI-phase; preview runs are backend jobs).

## 2. Decision closures (D-015-1 … D-015-8) — each Proposed

**D-015-1 — Export selection & bindings.** Export operates only on
explicitly selected `product.template` records (per-template opt-in
flag `shopify_export_enabled` on a template `_inherit` extension in
this module, default False). Bound templates → update path; unbound
selected templates → create path (D-015-4). Bindings reuse the merged
product/variant binding models (no new binding models; this module
writes binding rows through the same models after create).

**D-015-2 — Field allowlist (MBQ-23 closure).** The ONLY exported
fields, assembled declaratively into one `productSet` input per
template: product — `title`, `descriptionHtml`, `vendor`,
`productType`, `tags`, `status` (ACTIVE/DRAFT/ARCHIVED mapped from a
per-template selection `shopify_export_status`, default DRAFT on
create; UNLISTED unused); options — `productOptions` from Odoo
attribute lines (≤3 options, else pre-send hold — captures §5 limit);
variants — full desired set (D-015-3) with `optionValues`, `price`,
`compareAtPrice` (per-variant, sourced from the `product.product`
field `shopify_compare_at_price` — **created by Task 010B, not this
task** (D-010B-5 relocation, 2026-07-11): import fills it, this task
reads it; unset → omitted), `barcode`,
`inventoryItem: {sku}` (SKU lives on InventoryItem for writes —
captures §5; weight/measurement **not** exported in MVP). Price
export requires the merged `price_source_of_truth =
'odoo_authoritative'` store setting, else price fields are omitted
from the payload entirely (per-store price ownership, accepted
DEC-007 rule). `productVariantsBulkUpdate`/`BulkCreate` are **not
used** (single declarative `productSet` — one mutation shape,
MBQ-23's strategy choice made: fewer non-idempotent surfaces).

**D-015-3 — Delete-on-omit containment (MBQ-24 closure).**
`productSet`'s list fields delete omitted entries (verbatim capture
§5), so: the variants list is ALWAYS the complete desired set built
from ALL of the template's Odoo variants; pre-send guard compares the
current Shopify variant GID set (fresh read) against the bound
variant GID set — any Shopify-side variant that would be deleted
(present remotely, absent from the payload) triggers
`destructive_write_guard_blocked` unless the preview explicitly
enumerated that deletion and the operator confirmed (D-015-5).
`collections` and `metafields` list fields are **never included** in
the input (omitted non-list fields stay unchanged; but omitted LIST
fields would delete — verified nuance: the delete-on-omit semantics
apply to entries within a supplied list; lists not supplied at all
are not modified per the "Updates only the included fields" rule for
non-included fields — this exact boundary is a named empirical
verification item in §5's dev-store run, never assumed). MBQ-24's
media question resolves by exclusion: media is never in the payload,
so `productSet` cannot delete media through this module (empirically
re-verified in the same dev-store run).

**D-015-4 — Create path + mutation idempotency.** New products are
created via `productSet(synchronous: true, identifier: {customId:
{namespace: "$app:binding", key: "odoo_template_id", value:
<template id>}})` — the identifier makes create retry-safe
(upsert-by-custom-id), compensating for `productSet` not being
`@idempotent` (captures §5). The metafield definition
(`$app`-reserved namespace, unique values) is created once per store
at first export (`metafieldDefinitionCreate` — the module's only
metafield surface). **Pre-create duplicate gate (MBQ-59 two-tier,
automated path):** before any create, `products(query: "sku:<...>")`
search for each variant SKU; any hit → `duplicate_risk` review, never
a blind create. Empirical caveat flagged: the customId upsert path
must be proven on the dev store before first production use (§5);
fallback if it fails verification: preview + verification-read-by-
custom-metafield before any create retry (design remains valid).
Async mode (`synchronous: false` + `productOperation` polling) is
**not** used in MVP — inputs are bounded (≤100 variants per export
job; larger templates → hold with note; the 2048 ceiling and
50k-inventory-quantities limits are unreachable by construction).

**D-015-5 — Preview/apply flow (the destructive-write guard made
mechanical).** Two job types: `product_export_preview`
(`job_source='export_preview_dry_run'` — the merged read-only
source): fresh-reads the bound product, computes a field-level diff
(adds/changes/deletes incl. any variant deletions), stores it as the
job-log payload and on a preview record
(`shopify.connector.product.export.preview` model: template binding
ref, diff JSON, state previewed/confirmed/expired, confirmed_by/at;
previews expire after 24h or on any source-data change —
`write_date` comparison); `product_export_apply` refuses to run
without a matching confirmed, unexpired preview →
`destructive_write_guard_blocked`. Confirmation service
`action_confirm_export_preview()` (reviewer/admin). Review-then-apply
is the only mode (MBQ-34's accepted default applied to catalog);
no auto-apply flag exists.

**D-015-6 — Conflict policy & refresh interplay.** Between preview
and apply, apply re-reads and aborts to a fresh-preview requirement if
the remote `updatedAt` changed (stale-preview guard). Shopify-side
edits to non-allowlisted fields are never touched; edits to
allowlisted fields are overwritten by design (Odoo-authoritative for
the allowlist, per-store price rule above) — always visible in the
diff first. The import side (Task 010) continues to refresh snapshots;
binding `status`/`manually_overridden` semantics unchanged.

**D-015-7 — Deferred-from-015 register (revised 2026-07-11).**
Media/images → **Task 015B, fully planned** (no longer a candidate);
publishing (`publishablePublish`), metafields beyond the binding key,
weight/measurement, Markets, deletes remain deferred with names. None
silently absorbed.

**D-015-8 — Job/targeting.** `res_model/res_id` → template binding
(existing rows) or `product.template` (create path, pre-binding) —
documented dual targeting; `operation_scope_key` serializes per
template either way. Job types gated on a new settings flag
`product_export_domain_enabled` (Boolean default False — exports are
opt-in even inside Full) — note: this is a fifth domain flag added via
the settings seam by this module, mirroring the accepted flag pattern;
`_domain_flag_for_job_type()` maps both job types to it.

## 3. Gate criteria (product-export domain, 15-pattern)

1 Tasks 010 (bindings) **and 010B (complete variant structures +
the `shopify_compare_at_price` field this packet reads — added
2026-07-11)** merged runtime-green + this packet's module boundary
(ARCH PD-1) accepted; 2 naming: no new binding models — preview model name
accepted (=D-015-5); 3 exact names ✅; 4 files ✅(§8); 5
duplicate-gate + identifier idempotency fixed ✅(D-015-4); 6 no
inventory quantities ✅ (structural + source guard); 7 no
order/customer/fulfillment scope ✅; 8 no UI/webhook/OAuth/publishing
✅; 9 tests ✅(§5); 10 rollback ✅ (single-PR revert; exported Shopify
products remain, bindings survive in `shopify_connector_product`);
11 live-dependency controlled (mutation task — dev-store evidence
mandatory incl. the two named empirical checks, or recorded explicit
waiver); 12 gate-act reconfirmation; 13 preview/confirm guard flow
explicit ✅(D-015-5); 14 field allowlist + price-ownership rule
explicit ✅(D-015-2); 15 destructive-delete containment explicit
✅(D-015-3).

## 3.1 Scopes & readiness (red-team-added — previously unstated)

Every mutation in this packet (`productSet`,
`metafieldDefinitionCreate`) requires **`write_products`**; the SKU
pre-search and fresh reads require `read_products` (already in
`REQUIRED_MVP_SCOPES`). `write_products` is deliberately NOT added to
`REQUIRED_MVP_SCOPES` (that set stays the Lite read baseline);
instead this module appends (via the `_get_checks()` seam, the
Task-013 pattern) one essential readiness check active only when
`product_export_domain_enabled`: `write_products` present in
`granted_scopes`. Hold-outcome classification (red-team-added): >3
options and >100 variants → `data_shape_schema_mismatch`
(`failed_retryable`, the Task-012 precedent); stale/expired preview
at apply time → `destructive_write_guard_blocked`
(`blocked_manual_review` — the guard refused). Logging: module-local
pre-redaction is not needed (catalog data, no PII), all free text via
`_system_append`.

## 4. Store settings added

`product_export_domain_enabled` (Boolean default False),
`product_export_binding_namespace_ready` (Boolean ro — metafield
definition created marker).

Job-type → flag map: `product_export_preview` and
`product_export_apply` both map to `product_export_domain_enabled`.

## 5. Tests (exact files) + dev-store validation

`test_export_allowlist.py` (payload builder emits exactly the
D-015-2 fields; price omitted unless odoo_authoritative; >3 options
hold; >100 variants hold; **source guards: `inventoryQuantities`,
`publishablePublish`, `productDelete`, `productCreateMedia`,
`productVariantsBulk` strings absent from the module**);
`test_export_preview_guard.py` (apply refuses without
confirmed/unexpired preview; expiry on source change; stale-remote
abort; permission matrix); `test_export_delete_on_omit_guard.py`
(remote-extra-variant → guard block unless enumerated+confirmed;
full-set construction); `test_export_create_dedup.py` (SKU
pre-search → duplicate_risk; customId identifier present on create;
binding rows written post-create; retry-safety by identifier);
`test_export_apply_mechanics.py` (update path diff→payload fidelity;
status mapping; DRAFT-on-create; job gating on the new flag).
Dev-store validation (mandatory before merge review, mutation task):
one create round-trip proving customId upsert retry-safety; one
update proving list-not-supplied ≠ deleted for media/collections
(the D-015-3 named checks); redacted evidence in the validation
record; explicit recorded ChatGPT waiver is the only alternative.

## 6. Acceptance criteria / DoD / rollback

No mutation without confirmed preview; no variant deletion without
enumerated confirmation; no inventory/media/publishing surface in the
diff; duplicate gate proven; suites + Odoo.sh green; validation
record + AR row + handoff; draft PR; gate closes on draft-open.
Rollback: single-PR revert — export capability disappears entirely
(the PD-1 payoff); import domain untouched.

## 7. Register impacts on acceptance

OP-21 → Resolved-by-packet; MBQ-23 → Resolved (single-`productSet`
strategy + allowlist); MBQ-24 → Resolved (exclusion + named empirical
check); MBQ-25 residual → Resolved (DRAFT-on-create, publishing
withheld); 015B (media) → **fully planned successor packet**
(revised 2026-07-11), sequenced before UAT/release.

**Lifecycle (LC-1) adoption (re-review `4945129824` item 7):** the
product-export job-type `selection_add` `ondelete`(s) use the LC-1
callable `_reassign_to_historic_job_type` from the start (LC-1 precedes
Task 012 — DEC-030 / lifecycle §7), so no later retrofit is needed.

## 8. Locked final implementation prompt (Task 015)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE PRODUCT-EXPORT GATE, VERIFIES THE CURRENT BASE
SHA, AND ISSUES THIS PROMPT. (Prerequisite: Task 010B merged
runtime-green — this task reads its variant structures and
shopify_compare_at_price field.)

Implement Task 015 — controlled product export/update — as the NEW
module addons/shopify_connector_product_export, exactly per
docs/07-implementation-plan/task-015-product-export-implementation-packet.md
(D-015-1..8 binding) and ARCH §1.1/§3–§7. Branch from the verified
current Shopify-connector tip (STOP on drift). One session; draft PR;
stop.

ALLOWED FILES (exhaustive): addons/shopify_connector_product_export/**
(NEW: __init__.py, __manifest__.py [depends shopify_connector_core,
shopify_connector_product], models/{__init__.py,
shopify_connector_product_export_preview.py,
shopify_connector_product_export_service.py [payload builder, preview/
apply handlers, seams, metafield-definition bootstrap],
shopify_connector_product_template.py [shopify_export_enabled,
shopify_export_status], shopify_connector_store_settings.py}
(NOTE — revised 2026-07-11: shopify_compare_at_price lives on
product.product in shopify_connector_product, created by Task 010B;
this task READS it and creates no product.product extension),
security/ir.model.access.csv, tests/{__init__.py + the five §5
files}); docs/05-qa/task-015-product-export-validation-results.md
(NEW); docs/05-qa/architecture-review-log.md (append row);
docs/01-research/research-handoff.md (top entry).
FORBIDDEN: every core/product/sale/inventory/fulfillment file;
inventoryQuantities anywhere; media/file mutations; publishablePublish;
productDelete; productVariantsBulk*; metafieldsSet beyond the one
binding-definition bootstrap; UI/webhooks/OAuth/CI; adams_base.

HARD CONSTRAINTS: productSet only, synchronous, with the customId
identifier on creates; full-variant-set payloads always; preview ->
explicit confirmation -> apply, no other path, no auto-apply, no
bypass; price fields only under odoo_authoritative; SKU pre-search
duplicate gate before any create; DRAFT on create; write_products
readiness check per packet §3.1 and hold classes per §3.1;
concurrency caveat restated; Odoo.sh green + the two named dev-store empirical checks
(customId retry-safety; list-not-supplied != deleted) or a recorded
explicit ChatGPT waiver. Stop condition: draft PR "Task 015:
controlled product export/update (shopify_connector_product_export)";
gate closes on draft-open; no UI/webhook/media work.
```

---

## 9. Addendum (2026-07-16) — [Proposed] Fable gap-closure requirements

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. NOT accepted.**
> Appended; nothing above this line is rewritten. **Every D-015 closure
> (D-015-1..8) remains intact** — this addendum maps the export operating
> model
> ([`../02-product/product-export-operating-model.md`](../02-product/product-export-operating-model.md),
> PD-PX-1..7) and the accepted DEC-031 Layer 2 design onto this packet.
> **Re-acceptance required:** packet + addendum re-reviewed as one unit and
> the §8 locked prompt re-issued before Task 015 starts inside Wave 5 (see
> [`wave-5-definition-of-ready.md`](wave-5-definition-of-ready.md) gate G5-5).

1. **Field-ownership matrix is binding (PD-PX-2/3).** The operating model §2
   matrix becomes part of this packet's acceptance surface: the D-015-2
   allowlist is the Odoo-owned set; everything else is merchant-owned by
   definition and structurally absent from `productSet` input. Tests assert
   the payload builder cannot emit a non-allowlisted field (extends
   `test_export_allowlist.py`).
2. **Changed-since-read gate (operating model §8).** D-015-6's stale-preview
   guard is confirmed and tightened: preview is always a fresh read; apply
   re-reads and compares `updatedAt` against the preview capture, aborting to
   a fresh-preview requirement on any change; preview expiry (24h /
   source-`write_date`) closes the Odoo-side staleness direction. OQ-PX-5
   (`updatedAt` sensitivity to sub-resource edits) is a named Wave 5
   preflight dev-store verification — if it fails, the gate widens to
   comparing the previewed sub-resources themselves.
3. **Destructive-list guard (C-PROD-05 mechanical; operating model §3–§4).**
   Confirmed as stated in D-015-3, restated as binding: always the complete
   desired variant set or fail closed; fresh-read GID-set comparison before
   send; any would-be deletion must have been enumerated in the confirmed
   preview (`destructive_write_guard_blocked` otherwise); `collections`/
   `metafields` list inputs never supplied. The omitted-list-field boundary
   stays a named dev-store empirical check.
4. **Uncertainty reconciliation via Layer 2 (PD-PX-6; operating model §9).**
   This packet's mutations (`productSet`, `metafieldDefinitionCreate`) run
   only under the accepted DEC-031 Layer 2 protocol: durable attempt record
   before the network call; ambiguous outcome → reconciliation read by
   identifier (binding GID; `customId`/SKU search on the create path);
   found-and-matching → adopt+bind, found-divergent → manual review, not
   found → retry-eligible. The D-015-4 customId upsert remains the
   convergence mechanism; Layer 2 supplies the execution-ownership,
   fingerprint, and no-blind-retry machinery. New test family: the Layer 2
   suite rows for both mutations (attempt-before-call; all three
   reconciliation outcomes; source-level no-blind-retry).
5. **Reconnect reconciliation pass (PD-PX-7).** Exports stay blocked for a
   reconnected store until the full binding reconciliation pass completes
   (exists / variant GID set / media checksums); deleted-or-archived remote →
   review, never silent re-create. New acceptance row + test.
6. **Publication posture (PD-PX-5).** Restated: publication is a separate
   explicit operator step, never a side effect; DRAFT/unpublished default on
   create stands (D-015-2/MBQ-25).
7. **Wave anchoring.** Task 015 executes inside **Wave 5** after SEC-2 and
   under Layer 2 (DEC-033; `mvp-completion-program.md` §4 Wave 5); the §8
   prompt's "ChatGPT opens the gate" language is superseded by the DEC-032
   control-room model — gate authority is product owner + Claude control
   room within the Wave 5 wave gate.
