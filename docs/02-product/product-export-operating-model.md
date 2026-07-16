# Product Export Operating Model — Controlled Export/Update + Basic Media Export

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** This document
> defines the product-level operating model for controlled product export/update
> and basic media export (MVP Wave 5, after DEC-031 Layer 2 is designed,
> accepted, and implemented). Acceptance authority: product owner + Claude
> control room. **No implementation authorized.** This document layers a
> product/operating view on top of the already-proposed implementation packets
> [`../07-implementation-plan/task-015-product-export-implementation-packet.md`](../07-implementation-plan/task-015-product-export-implementation-packet.md)
> (D-015-1…8) and
> [`../07-implementation-plan/task-015b-product-media-export-packet.md`](../07-implementation-plan/task-015b-product-media-export-packet.md)
> (D-015B-1…7); where those packets have closed a decision, this document
> respects the closure and does not reopen it.

Evidence base: Shopify official captures (Accessible, 2026-07-16) in
[`../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md`](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)
§10 (productSet, productCreate, variants, publishablePublish) and §11 (rate
limits, bulk operations, versioning); accepted scope in
[`./mvp-scope.md`](./mvp-scope.md) (DEC-003 + PR #55 correction, DEC-007
clarifications); competitor failure evidence in
[`../00-source-materials/competitor-refresh-2026-07-16.md`](../00-source-materials/competitor-refresh-2026-07-16.md).

---

## 1. Scope statement

[Fact — accepted scope] The accepted MVP baseline (DEC-003, revised by the
PR #55 correction) includes **controlled product export/update** with matching,
binding, preview, and draft/unpublished/channel-controlled safety, and marks
destructive-apply safety (**C-PROD-05**) as **mandatory** for this path. What
stays deferred is *unrestricted autonomous bidirectional catalog ownership*
(all-field two-way conflict resolution, advanced publish/channel management,
Markets/metafields/SEO breadth). Customer export remains deferred. Source:
[`./mvp-scope.md`](./mvp-scope.md) (RB-13 acceptance + Domain rows).

The operating model in one sentence:

> The connector exports **only explicitly selected products**, **only the
> allowlisted fields**, **only after an operator has seen and confirmed a
> field-level diff**, and **never trusts its own memory of Shopify's state** —
> every mutation is preceded by a fresh read and followed by a verification
> read.

[Proposed product decision — PD-PX-1] The connector is never the autonomous
owner of the Shopify catalog in MVP. Export is a **deliberate, reviewed,
per-product operator action** (batchable), not a background catalog mirror.
This restates the accepted DEC-003 boundary; it is listed here so the Wave 5
UI and tests treat it as a product requirement, not an implementation detail.

Out of scope for this document (deferred with names per D-015-7): publishing
campaigns beyond the single controlled publish step (§7), metafields beyond
the binding key, weight/measurement export, Markets, product deletion,
collection management.

## 2. Field-ownership matrix

The central overwrite-prevention concept: **every exported field family has an
explicit owner while a binding exists**, and the connector may only write
fields it owns under the current settings. Overwrite prevention is the
combination of (a) this ownership matrix, (b) the mandatory preview diff
(§8, D-015-5), and (c) the changed-since-read gate (§8, D-015-6). No single
mechanism is trusted alone.

[Proposed product decision — PD-PX-2] Ownership matrix for a bound product
(Odoo `product.template` ↔ Shopify Product):

| Field family | Exported? | Owner while bound (export enabled) | Notes / guardrails |
| --- | --- | --- | --- |
| Title | Yes | Odoo-authoritative for allowlisted fields (D-015-2/6) | Shopify-side edits are overwritten **by design, but always visible in the preview diff first** |
| Description (`descriptionHtml`) | Yes | Odoo-authoritative | Same as title |
| Vendor / product type / tags | Yes | Odoo-authoritative | D-015-2 allowlist |
| Options (≤3) | Yes | Odoo-authoritative (attribute lines) | >3 options → pre-send hold, never truncation (D-015-2; Shopify 3-option limit) |
| Variants (set membership + optionValues, barcode, SKU) | Yes | Odoo-authoritative **with destructive-delete containment** (§3–§4, D-015-3) | Variant deletion requires explicit enumerated confirmation |
| Price / compare-at price | Conditional | Owned by whichever system the per-store `price_source_of_truth` setting names (§6, accepted DEC-007 rule) | If Shopify-authoritative: price fields **omitted from the payload entirely** |
| Images / media | Yes (015B layer) | Odoo-authoritative **only for connector-exported media** proven by checksum registry (§5, D-015B-1/2) | Merchant-added Shopify media is **never deleted**; detach-only, enumerated in preview |
| Status (ACTIVE/DRAFT/ARCHIVED) | Yes | Odoo per-template selection (`shopify_export_status`, default DRAFT on create) | §7 |
| Publication / sales channels | Not in the export payload | Merchant-owned; changed only via the separate explicit publish step (§7) | `publishablePublish` is a distinct scope (`write_publications`) and a distinct operator action |
| Collections, metafields (beyond binding key), SEO, Markets | No | Merchant-owned — connector never includes these list fields in `productSet` input | D-015-3: omitted-list boundary is a named empirical verification item |
| Inventory quantities | No (inventory domain, Wave 3) | Out of this domain entirely | First-push guard per DEC-007/RA-008 |

[Inference] This matrix is the product-domain analog of the Wave 1 SEC-1
posture on the import side: SEC-1 (merged, PR #172) protects binding
identity/structure/provenance fields against uncontrolled writes inside Odoo;
this matrix protects merchant-owned Shopify surfaces against uncontrolled
writes by the connector. Both implement the same principle — **no write
without a declared owner and a controlled door** (see
[`../07-implementation-plan/task-sec1-security-hardening-packet.md`](../07-implementation-plan/task-sec1-security-hardening-packet.md)).

[Proposed product decision — PD-PX-3] Fields not on the D-015-2 allowlist are
**merchant-owned by definition** and structurally untouchable: they are never
present in the mutation input, so the connector cannot overwrite them even in
a defect scenario, subject to the omitted-list-field empirical verification
named in D-015-3.

## 3. Create vs update

[Fact] `productSet` supports **upsert by `identifier`** (`ProductSetIdentifiers`:
`id`, `handle`, or `customId`) — built-in duplicate prevention on the create
path; `synchronous` defaults to true, async returns a `ProductSetOperation`
polled via `productOperation` (captures §10).

[Fact — the destructive semantic that shapes everything] `productSet` list
fields are declarative/destructive: "Creates new entries, updates existing
entries, and **deletes existing entries that aren't included in the mutation's
input**" (variants/collections/metafields; captures §10, direct quote).
Omitted *non-list* fields are unchanged.

Operating rules:

- **Update path (bound product):** mutate by `id` from the binding — never by
  handle guess, never by title match (RA-006 analog: no name-only identity).
- **Create path (selected, unbound product):** `productSet` with a
  `customId` identifier carrying the Odoo template identity (D-015-4), making
  the create retry-safe by upsert. A pre-create SKU search
  (`products(query: "sku:…")`) gates against colliding with an existing
  Shopify product → any hit is a `duplicate_risk` review, never a blind
  create (D-015-4, MBQ-59).
- **Mandatory destructive-list guard (C-PROD-05 made mechanical):** because
  omitted variants are *deleted*, the connector **always sends the complete
  desired variant list assembled from binding + Odoo evidence, or fails
  closed**. It never sends a partial variant list as an "update just this
  variant" shortcut. Before send, the current remote variant GID set (fresh
  read) is compared against the payload; any remote variant that would be
  deleted must have been explicitly enumerated in the confirmed preview, else
  the job blocks (`destructive_write_guard_blocked`, D-015-3/5).
- **Never-included lists:** `collections` and `metafields` list inputs are
  never supplied (D-015-3), so `productSet` cannot delete merchant collections
  or metafields through this connector.

[Open question — OQ-PX-1, carried from captures §10/§13] The synchronous-mode
variant-count threshold (historic 100) and handle-uniqueness/auto-suffix
behavior are unverified this pass; the customId upsert path must be proven on
the dev store before first production use (D-015-4 empirical caveat, with a
named verification-read fallback).

## 4. Variants

- [Fact] Product variant ceiling: **2048 variants per product** (confirmed on
  both `productSet` and `productVariantsBulkCreate` pages, captures §10);
  variant-creation throttle beyond 50,000 store variants: max "1,000 new
  product variants … per day" (quote, captures §10).
- [Fact — packet closure, respected] D-015-4 bounds MVP export jobs to ≤100
  variants per job; larger templates → hold with an operator-readable note.
  Async `productSet` is not used in MVP; the 2048 ceiling is unreachable by
  construction. §12 records the post-MVP relief valve.
- **Variant identity lives in the binding, nowhere else.** Each Odoo
  `product.product` maps to a Shopify variant GID through the merged binding
  models (D-015-1); option-value strings are display data, not identity.
  Re-deriving identity from option values or SKU at apply time is forbidden
  (it reintroduces the RA-006 name-matching failure mode at variant level).
- Options come from Odoo attribute lines; >3 options is a pre-send hold
  (Shopify limit), surfaced as a review case, never silent truncation or
  option-flattening.
- Variant *deletion* (an Odoo variant removed while bound) is the highest-risk
  diff class: it is rendered in the preview as an explicit "will DELETE on
  Shopify" line, and apply refuses unless that exact deletion set was
  confirmed (D-015-3/5).

## 5. Images / media export (the 015B layer)

Media export is a **separate, sequenced layer** on top of field export —
never mixed into the `productSet` payload (D-015-3 resolves MBQ-24's media
question by exclusion: media is never in the field-export input).

Respected D-015B closures, summarized as operating rules:

- **Pipeline [Fact-based, captures §10 + packet §2]:** `stagedUploadsCreate` →
  HTTP upload to the staged target → `fileCreate` → associate with the product
  **only after the File reaches `READY`** (two-phase, READY-gated, D-015B-4).
- **Ownership by checksum proof:** a media binding registry records the File
  GID, product-media GID, and `odoo_image_checksum` (SHA-256 of the exported
  image). The connector may detach/replace **only** media whose current
  checksum matches its own registry entry — i.e., media it can *prove* it
  exported. This mirrors the existing import-side merchant-image protection
  (`shopify_image_checksum` mechanics from Task 010B), with D-015B-7 keeping
  the two checksum registries distinct so import protection and export
  ownership can never feed each other a loop.
- **Detach-only, never auto-delete (D-015B-2/6):** merchant-added or
  unproven media is never touched; replaced connector media is detached, with
  the orphan File retained (`detached_orphan_candidate`) for later reviewed
  cleanup; the product is never left imageless mid-replacement.
- **Idempotency without platform help (D-015B-5):** no media mutation is
  `@idempotent`; retry safety = deterministic connector filename
  (`odoo-<template_id>-<checksum8>.<ext>`) + verification-read + adopt-if-found,
  never blind retry (RA-014 honored). An unchanged image (same checksum) is a
  no-op — no duplicate uploads.

[Open question — OQ-PX-2, carried from captures §10/§13] `productCreateMedia`
vs `fileCreate` deprecation status in 2026-07, and the variant-bulk `strategy`
enum, remain unverified; 015B currently plans on the `fileCreate` path per its
§2 capture basis — re-verify at Wave 5 preflight before locking the mutation
surface.

## 6. Prices

- **Per-store `price_source_of_truth` setting (accepted DEC-007 rule,
  operationalized by D-015-2):** price and compare-at fields are exported
  **only** when the store is configured `odoo_authoritative`; otherwise they
  are omitted from the payload entirely, so a Shopify-priced store can never
  have prices clobbered by a product-field export.
- Compare-at price per variant sources from `shopify_compare_at_price`
  (created by Task 010B; import fills it, export reads it — D-015-2).
- [Fact] Prices written via the Admin API are in the **shop currency**;
  presentment/multi-currency prices are Shopify Markets territory.
  [Proposed product decision — PD-PX-4] MVP export writes shop-currency
  prices only; Markets/presentment pricing and pricelist-driven pricing are
  post-MVP (consistent with
  [`./non-mvp-and-later-phases.md`](./non-mvp-and-later-phases.md)).
- [Open question — OQ-PX-3] Which Odoo price field is authoritative when
  `odoo_authoritative` is set (list price vs a pricelist evaluation) is a
  Wave 5 packet-level confirmation item; the Task 015 packet currently reads
  the variant `price` directly, and this document does not reopen that — the
  open question is only whether a pricelist-aware option is offered as a
  labeled post-MVP extension.

## 7. Status and publication

Two deliberately separate controls:

1. **Product status** (in the export payload): `ACTIVE` / `DRAFT` / `ARCHIVED`
   [Fact, captures §10], mapped from the per-template
   `shopify_export_status` selection, **default `DRAFT` on create**
   (D-015-2). This implements the accepted "draft/unpublished/channel-
   controlled safety" of [`./mvp-scope.md`](./mvp-scope.md): a freshly
   exported product is not customer-visible by default.
2. **Publication** (never in the export payload): [Fact] products created via
   the API are **unpublished by default**; publishing is `publishablePublish`,
   a separate mutation under the separate `write_publications` scope, and an
   active status is required for visibility (captures §10).

[Proposed product decision — PD-PX-5] Publication is a **separate, explicit
operator step** after export — its own action, its own confirmation, its own
job/log trail — never a side effect of exporting fields or media. Default
posture: export as DRAFT/unpublished; the operator publishes when ready.
Channel-campaign management beyond this single publish step stays deferred
(D-015-7). [Open question — OQ-PX-4] Whether the MVP publish step targets
Online Store only or offers channel selection is Wave 5 UX scope; scheduled
publishing is online-store-only per captures §10.

## 8. Conflicts and changed-since-read behavior

The connector never mutates on stale knowledge:

- **Preview is a fresh read.** The preview job re-reads the bound Shopify
  product and computes the field-level diff against it — not against a cached
  snapshot (D-015-5).
- **Changed-since-read gate at apply.** Before mutating, apply re-reads the
  remote product and compares `updatedAt` against the value captured at
  preview time. Any change → the apply **aborts to a fresh-preview
  requirement** (stale-preview guard, D-015-6). The operator re-previews and
  re-confirms; the connector never blind-overwrites a product a merchant
  edited between preview and apply.
- **Preview expiry:** previews expire after 24h or on any Odoo source-data
  change (`write_date` comparison, D-015-5), closing the symmetric staleness
  direction (Odoo changed since preview).
- **Within-ownership conflicts:** for allowlisted fields the diff *is* the
  conflict resolution — Odoo wins by declared ownership (§2), but only ever
  through a visible, confirmed diff. For merchant-owned fields there is no
  conflict possible: they are absent from the payload.

[Inference] This is deliberately stricter than optimistic concurrency alone:
Shopify offers no product-level compare-and-set on `productSet` (unlike
`inventorySetQuantities`' `compareQuantity`, captures §9), so the
read–compare–gate sequence in the connector is the only available equivalent.
[Open question — OQ-PX-5] Whether `updatedAt` changes for every relevant
sub-resource edit (e.g. a media reorder) needs dev-store verification; if not,
the gate widens to comparing the previewed sub-resources themselves.

## 9. Duplicate prevention and uncertainty after mutation

Two distinct failure classes, two distinct answers:

**Identity duplication (the classic competitor defect).** [Competitor claim /
review evidence] Duplicate records are the top recurring real-world complaint
across the refreshed competitor corpus — duplicate customer contacts, and
cross-market "duplicate orders … recurring complaint themes"
([`../00-source-materials/competitor-refresh-2026-07-16.md`](../00-source-materials/competitor-refresh-2026-07-16.md)).
The classic mechanism: a create request times out or errors ambiguously, the
connector retries blind, and the store now has two products. Our answer:
- create is upsert-by-`customId` [Fact, §3] — a replayed create converges on
  the same product;
- the pre-create SKU duplicate gate (D-015-4) catches pre-existing products;
- bindings are written immediately after create, so the next run takes the
  update path.

**Operation uncertainty after mutation (the DEC-031 Layer 2 contract).**
[Fact — accepted decision] DEC-031 defers mutation hardening to Layer 2 and
names **product export** as an explicit reopening trigger: before any Shopify
mutation handler ships, Layer 2 must provide durable execution ownership,
persisted attempt identity, transport-ambiguity tracking, idempotency-key
persistence, and **reconciliation-before-retry**
([`../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md`](../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md)).
Applied to product export:
- every apply attempt is durably recorded **before** the network call
  (attempt record with identity);
- an ambiguous outcome (timeout, connection reset, 5xx after send) never
  triggers a blind retry — the connector first performs a **reconciliation
  read by identifier** (binding id if bound; `customId`/SKU search on the
  create path) to detect an applied-but-unacknowledged mutation;
- reconciliation outcomes: found-and-matching → adopt + bind + mark applied;
  found-but-divergent → manual review; not found → safe to retry;
- media follows the same discipline via checksum + verification read
  (D-015B-5).

[Proposed product decision — PD-PX-6] No product-export apply job may run
except under the accepted Layer 2 execution-ownership protocol. This is not
new — it restates DEC-031's trigger — but it is the single hardest gate on
this capability and is stated here as a product requirement.

## 10. Reconnect reconciliation

After a store reconnects (credential rotation, long disconnect, backfill):

[Proposed product decision — PD-PX-7] Before any export job is allowed to
resume, the connector runs a **reconnect reconciliation pass over all
previously exported bindings**: read each bound product by GID, verify it
exists, verify the bound variant GID set, and verify media-registry checksums.
Outcomes: intact → binding refreshed; remotely deleted/archived → review case
(never silent re-create); remotely diverged → flagged so the next preview
shows the full drift. Exports stay blocked for the store until the pass
completes. [Inference] This is the export-side counterpart of the
review-then-apply reconnect posture already accepted for imports, and closes
the market gap the refresh capture names: "Safe reconnect/backfill with
preview and reconciliation reports … nobody documents duplicate-safe
re-import"
([`../00-source-materials/competitor-refresh-2026-07-16.md`](../00-source-materials/competitor-refresh-2026-07-16.md)).

## 11. Manual review triggers

An export job routes to manual review (never auto-resolves) when:

1. Pre-create SKU search hits an existing Shopify product (`duplicate_risk`).
2. The apply would delete remote variants not enumerated in the confirmed
   preview (`destructive_write_guard_blocked`).
3. Remote `updatedAt` changed between preview and apply (fresh preview
   required — strictly, a re-review trigger).
4. Reconciliation after an ambiguous mutation finds a divergent remote state
   (§9).
5. Reconnect reconciliation finds a deleted/archived/diverged bound product
   (§10).
6. >3 options, >100 variants per job, or any Shopify limit hold (§4).
7. Media pipeline failures after upload (File never reaches `READY`;
   verification read fails) — the two-phase state is preserved for review,
   not rolled forward (D-015B-4).
8. Price export requested while `price_source_of_truth` is not
   `odoo_authoritative` (configuration conflict surfaced, fields omitted).

Review cases carry operator-language reasons (DEC-009 recovery-first UX;
RA-016: no raw stack traces as primary message).

## 12. Performance

- [Fact] Cost-based leaky bucket: mutations cost 10 points; restore rates
  100/200/1000/2000 points/s by plan; single-query cap 1,000 points; throttle
  = `THROTTLED` + `throttleStatus`, recommended backoff one second
  (captures §11).
- Batch shape: one `productSet` per template (D-015-2's single-mutation-shape
  choice), throttle-aware pacing via the existing core client, backoff on
  `THROTTLED` per DEC-009 transient classification.
- [Fact] For large exports, Shopify offers **bulk mutations**: JSONL of inputs
  → `stagedUploadsCreate` → `bulkOperationRunMutation`; up to 5 concurrent
  bulk operations per shop since 2026-01; `@idempotent` applies per row
  (captures §11). [Recommendation] Keep bulk-mutation export as the named
  **post-MVP relief valve** for catalog-scale exports (thousands of
  templates), together with async `productSet` + `ProductSetOperation`
  polling for very-high-variant templates — both deliberately unused in MVP
  (D-015-4 bounds inputs instead), both requiring their own Layer-2-aware
  ambiguity handling before adoption.
- [Fact] Pin API version 2026-07; Shopify "falls forward" to the oldest
  accessible stable version if an app targets an inaccessible one — a
  silent-behavior-change risk to monitor (captures §11).

## 13. UX summary

Wave 5 flow (visual design deferred to the Wave 5 UI packets; screens slot
into [`./screen-inventory-and-navigation-map.md`](./screen-inventory-and-navigation-map.md)):

1. **Select** — operator opts templates in (`shopify_export_enabled`,
   default off; exports also gated by the store-level
   `product_export_domain_enabled` flag — opt-in even inside Full, D-015-8).
2. **Preview** — read-only dry run produces a field-level diff per product:
   creates, changes, and — highlighted separately — deletions (variants,
   detached media). Nothing has touched Shopify yet.
3. **Confirm** — reviewer/admin confirms the exact previewed diff
   (`action_confirm_export_preview`, two-role model per
   [`./connector-roles-and-permissions.md`](./connector-roles-and-permissions.md)).
4. **Apply + progress** — apply jobs run under Layer 2 ownership; progress
   and throttling visible through the standard job/log surfaces.
5. **Results** — per-product outcome (applied / review / blocked) with
   operator-language reasons; media outcomes reported per image.

Review-then-apply is the only mode; no auto-apply flag exists (D-015-5).

## 14. Tests and UAT summary

- **Unit (packet-owned, exact files in the two packets §5):** allowlist
  fidelity (nothing beyond D-015-2 in the payload); price omission unless
  `odoo_authoritative`; complete-variant-list construction; destructive-guard
  blocking on unconfirmed deletions; preview expiry/staleness; upsert-create
  retry convergence; media two-phase READY gating, checksum no-op idempotency,
  detach-only behavior, never-imageless replacement.
- **Layer 2 suite:** attempt-record-before-call; ambiguous-outcome →
  reconciliation-read (all three outcomes); no blind retry path exists.
- **Dev-store empirical verifications (named, must run before production):**
  customId upsert behavior; omitted-list-field boundary (lists not supplied
  are not modified); media cannot be deleted by field-only `productSet`;
  `updatedAt` sensitivity (OQ-PX-5).
- **UAT scenarios (Wave 6):** first controlled export of a small selected set
  (create, DRAFT, unpublished); update with visible diff; a deliberate
  variant-deletion confirmation; a deliberate mid-flight merchant edit
  (stale-preview abort); a simulated timeout with reconciliation adoption;
  reconnect reconciliation pass; publish step as a separate action. Rows 6
  and 17 of [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md)
  carry the release criteria.

## 15. Wave allocation

[Fact — program state] Task 015/015B are retained in **MVP Wave 5** (DEC-033
§1, accepted), explicitly **after DEC-031 Layer 2** is designed, accepted, and
implemented (Wave 3 dependency chain), per the wave table in
[`../07-implementation-plan/mvp-program-state.md`](../07-implementation-plan/mvp-program-state.md).
Sequence: Wave 1 (merged, PR #172) → Wave 2 orders → Wave 3 inventory + Layer 2
→ Wave 4 fulfillment → **Wave 5: premium operator UI + product export/media
export** → Wave 6 E2E/UAT/release. Nothing in this document is authorized for
implementation before that gate opens.

## 16. Proposed product decisions (consolidated)

| ID | Decision | Class |
| --- | --- | --- |
| PD-PX-1 | Export is a deliberate, reviewed, per-product operator action; never autonomous catalog ownership (restates DEC-003 boundary) | Proposed product decision |
| PD-PX-2 | The §2 field-ownership matrix is the binding overwrite-prevention contract for Wave 5 | Proposed product decision |
| PD-PX-3 | Non-allowlisted fields are merchant-owned by definition and structurally absent from mutations | Proposed product decision |
| PD-PX-4 | MVP exports shop-currency prices only; Markets/presentment/pricelist pricing post-MVP | Proposed product decision |
| PD-PX-5 | Publication is a separate explicit operator step; default export posture DRAFT/unpublished | Proposed product decision |
| PD-PX-6 | No export apply runs outside the accepted DEC-031 Layer 2 ownership protocol | Proposed product decision |
| PD-PX-7 | Reconnect blocks exports until a full binding reconciliation pass completes | Proposed product decision |

Acceptance authority: product owner + Claude control room; these become
binding only via an accepted decision record.

## 17. Open questions (consolidated)

| ID | Question | Where it resolves |
| --- | --- | --- |
| OQ-PX-1 | productSet synchronous variant threshold; handle uniqueness/auto-suffix; customId upsert empirical proof | Dev-store verification at Wave 5 preflight (D-015-4 caveat) |
| OQ-PX-2 | `productCreateMedia` vs `fileCreate` status in 2026-07; variant-bulk `strategy` enum | Official-source re-verification at Wave 5 preflight (captures §13 item 9) |
| OQ-PX-3 | Pricelist-aware price source as a labeled post-MVP extension | Product-owner review of this document |
| OQ-PX-4 | Publish step: Online Store only vs channel selection in MVP | Wave 5 UX packet |
| OQ-PX-5 | `updatedAt` sensitivity to sub-resource edits (gate width) | Dev-store verification |
| OQ-PX-6 | Bulk-mutation/async-productSet adoption criteria for catalog-scale exports | Post-MVP architecture review |
