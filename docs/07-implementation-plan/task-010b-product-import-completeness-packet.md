# Task 010B — Product Import Completeness: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §10 is NOT usable.** Produced 2026-07-11 by the PR #148
> revision session, implementing review item 1 of ChatGPT's
> control-room review (PR #148 comment `4942966937`). Sequenced as the
> **first domain implementation task after CORE-R1** and **before
> Task 012** (orders resolve lines through variant bindings — an
> incomplete variant path starves order import). Evidence: merged
> `shopify_connector_product` code (re-read 2026-07-11), captures
> 2026-07-10 §5 and 2026-07-11 §5/§9
> (`../00-source-materials/odoo19-shopify-official-captures-2026-07-11.md`).
> API version 2026-07 (ARCH PD-6).

## 1. Why this task exists (verified Task 010 limitations vs accepted scope)

**[Fact — merged repository state]** The merged importer
(`shopify_connector_product_importer.py`) is intentionally narrower
than the accepted DEC-003 product-import scope:

1. `variants(first: 100)` with **no second page ever fetched**;
   `pageInfo.hasNextPage` → `data_shape_schema_mismatch` hold (lines
   300–307) — products with >100 variants are blocked.
2. **No Odoo attribute structure is ever created** (zero occurrences
   of `product.attribute` / attribute lines / variant generation): a
   brand-new multi-variant product creates a bare
   `product.template` (name only), binds the singleton to variant
   index 0, and **blocks on the second variant** (`duplicate_risk`,
   lines 605–636).
3. Options are flattened to a `Text` snapshot
   (`shopify_option_values`, `"Size: M / Color: Blue"`); prices and
   compare-at prices are `Float` snapshots on the binding; images are
   URL `Char` snapshots — **no** `list_price`, **no** attribute
   values, **no** image binary is ever written (grep-verified zero
   occurrences).
4. Remote deletion (`product: null`) is treated as a malformed
   payload → `failed_retryable`; ARCHIVED status is snapshot-only
   with no binding-state consequence.
5. Per-variant candidate search re-scans the **entire** variant
   binding table per variant (N+1; lines 650–674).

**[Fact — DEC-003, accepted]** MVP import scope includes: "product
import; variant / options import; basic image / media import; base
price / compare-at import". The merged slice satisfies none of the
last three for ordinary Shopify catalogs and satisfies variant import
only for singleton or pre-existing-variant products. **Task 010B
completes the accepted scope; the recommended outcome is completion,
not a DEC-003 narrowing** (no scope-change DEC is drafted — per the
review's recommended posture).

## 2. Objective, scope, non-goals

Extend `shopify_connector_product` so that an ordinary Shopify
catalog — multi-option, multi-variant, priced, with images — imports
into real, complete Odoo products, idempotently and atomically, with
safe refresh and archived/deleted-remote handling. **Non-goals:** no
export/mutation of any kind (Task 015's domain); no inventory
quantities; no publishing; no metafields; no gallery/media breadth
beyond the basic set (§D-010B-7); no enumeration/scan triggers
(Area 6); no full field-ownership matrix (DEC-003 defers it — only
the minimal ownership rules in D-010B-8); no UI.

## 3. Decision closures (D-010B-1 … D-010B-12) — each Proposed

**D-010B-1 — Extended query + variant pagination.**
`PRODUCT_IMPORT_QUERY` extends to: product `id title status
descriptionHtml vendor productType tags featuredImage { url }
options { id name position optionValues { id name } }` and
`variants(first: 100, after: $cursor)` requesting `id sku barcode
price compareAtPrice selectedOptions { name value } image { url }
inventoryItem { id }` + `pageInfo { hasNextPage endCursor }`. The
handler loops pages (cursors in-run only, never persisted — PD-5)
until exhausted. **[Fact]** platform ceiling is 2,048
variants/product (all merchants, changelog 2025-10-15; captures
2026-07-11 §9); ≤3 options. Defensive cap: >2,048 accumulated
variants → `data_shape_schema_mismatch` hold (unreachable by
platform; guards a schema change). `first` is always explicit
(no documented default page size — captures §9 open question 1).

**D-010B-2 — Options → attributes → values → lines (the real Odoo
structure), with an explicit existing-attribute compatibility rule
(re-review `4945129824` item 1).** For each Shopify option (in
`position` order): resolve `product.attribute` by **case-insensitive
exact name match**.

**Compatibility gate (deterministic — the review's blocker):** a
same-name attribute is **reused only when its `create_variant` mode is
compatible** with the sparse Shopify-variant strategy, i.e.
`create_variant == 'dynamic'`. Modes `'always'` (would cartesian-
generate phantom Odoo variants with no Shopify counterpart) and
`'no_variant'` (would create no variants at all, unable to represent
Shopify's set) are **incompatible**, and the mode is **immutable once
used** — so the connector **never** changes an existing attribute's
mode. Outcomes:
- **No same-name attribute:** create it with `create_variant='dynamic'`
  (D-010B-3 rationale) and use it.
- **Same-name, compatible (`dynamic`):** reuse it.
- **Same-name, incompatible (`always`/`no_variant`):** never reuse and
  never mutate it. The deterministic safe outcome is governed by the
  new per-store setting `product_import_attribute_conflict_mode`
  (§4, Selection, **default `manual_review`**):
  - `manual_review` (default, fail-closed): the product routes to
    `blocked_manual_review` / `binding_conflict` naming the option, the
    existing attribute, and its incompatible mode, so an operator maps
    the Shopify option to a compatible attribute (or authorizes the
    connector-owned path) — **no import proceeds on a guess**;
  - `connector_owned`: the connector creates and uses a clearly named,
    **connector-owned separate** attribute `"<name> (Shopify)"` with
    `create_variant='dynamic'` (recorded as connector-owned), leaving
    the merchant's same-name attribute untouched.
  Under **no** setting is the merchant's attribute's mode changed, and
  under **no** setting are phantom cartesian variants generated.

For each option value: resolve `product.attribute.value` under the
**resolved** attribute by case-insensitive exact name; create if
absent. Build one `product.template.attribute.line` per option on the
template with the used value set; on refresh, new remote values
**extend** the line (additive; values are never detached automatically
— a remote value disappearance is a review note, not a destructive
write).
**Special case (Shopify's default shape):** a product whose only
option is `Title` with sole value `Default Title` is a true
single-variant product → no attribute structure is created (bare
template + singleton, exactly today's clean path).
**Shared-master-data + concurrency note (flagged):**
`product.attribute`/`.value` are database-global; concurrent imports
could race duplicate creations (no uniqueness constraint exists
upstream). Mitigation: the case-insensitive get-or-create **and the
compatibility gate** run inside the product's savepoint (the mode is
read on the row the get-or-create resolves, so a concurrently-created
same-name attribute is evaluated for compatibility exactly like a
pre-existing one — never blindly reused); the named concurrency caveat
stands; a post-import reconciliation sweep is a release-hardening
candidate, not in-scope.

**D-010B-3 — Deterministic creation of ALL variants, `dynamic` mode.**
Every attribute used by this path is `create_variant='dynamic'` — new
ones are created that way and reused ones are guaranteed `dynamic` by
the D-010B-2 compatibility gate (an incompatible same-name attribute
never reaches this step) — so Odoo does **not** cartesian-generate
variants; the importer then **explicitly instantiates exactly the
variants Shopify has**: for each remote
variant, map its `selectedOptions` to the template's
`product.template.attribute.value` combination and get-or-create the
`product.product` for that combination via the template's dynamic
variant-creation mechanism, then bind `(store, variant GID)`.
*Why not `'always'` (flagged alternative, rejected):* Shopify variant
sets are routinely **sparse** (not every option-value combination
exists); `'always'` would generate phantom Odoo variants with no
Shopify counterpart — polluting stock, exports (Task 015 builds
full-set payloads from **all** Odoo variants), and operator screens.
`dynamic` keeps Odoo variants ≡ Shopify variants, which is exactly
the "deterministic creation of all variants" requirement. **[Fact]**
mode semantics per official 19.0 source (captures 2026-07-11 §5);
mode is immutable once used — set at attribute creation.
**Build-time verification (named):** the exact 19.0 internal API for
dynamic-combination instantiation (`_create_product_variant` on
`product.template`) is verified against the 19.0 source in-session
before use; if its signature differs, the implementer stops and
reports (no improvisation).
Pre-existing-Odoo-product matches (SKU/barcode paths) keep today's
behavior — bind, never restructure a merchant's existing attribute
setup; a structural mismatch (bound template's combination set cannot
represent the remote variant) routes to `blocked_manual_review` /
`binding_conflict` with both structures in the evidence payload.

**D-010B-4 — Base price import (real `list_price`).** Gated by the
merged per-store `price_source_of_truth` setting (verified merged
selection: `odoo_authoritative` / `shopify_authoritative`, no
default): prices are written into Odoo **only** when the store's
value is `shopify_authoritative`; when unset or `odoo_authoritative`,
snapshots-only (today's behavior).
Write mechanics: single-variant template → `list_price = price`.
Multi-variant → `list_price = min(variant prices)`; per-variant
deltas decomposed onto `product.template.attribute.value.price_extra`
**only when the additive model fits exactly** (delta consistent per
option value across all variants); non-decomposable pricing →
`list_price = min`, per-variant snapshots remain authoritative
evidence, one `price_undecomposable` job-log note (import completes —
not a hold; the snapshot fields keep full fidelity). Odoo "Product
Price" precision is 2dp by default (captures §6); sub-precision
remote prices round-trip through snapshots untouched.

**D-010B-5 — Compare-at price.** The `shopify_compare_at_price` field
(planned in the Task 015 packet on `product.product`) **moves to this
module/task** — import fills it (readonly=False, connector-maintained,
company-currency semantics documented as Shopify shop currency),
export (015) reads it. The Task 015 packet is revised accordingly
(its allowlist drops the field file; cross-reference note added).
Snapshot fields on the binding remain (audit trail).

**D-010B-6 — Basic image/media import.** Scope = **primary product
image + per-variant image** (the DEC-003 "basic" bar): download the
`featuredImage.url` / variant `image.url` binary over HTTPS
(content-type must be `image/*`; size cap constant 20 MB; timeout;
redirects followed only to https; failures → job-log note +
`shopify_temporary_server_network` retry class (the exact merged
registry name), never a hold) and write
`product.template.image_1920` / `product.product.image_variant_1920`
(both are core `product` fields — no new dependency). A checksum
(`shopify_image_checksum` Char on each binding) prevents re-download/
re-write when the URL content is unchanged; refreshed images
**overwrite only connector-written images** (checksum match against
the last connector write; a merchant-replaced image — checksum
mismatch with our record — is never overwritten: note + review flag).
Per-store off switch: `product_import_media_enabled` (Boolean,
default True). Gallery/extra media (`media(first:…)`) is **deferred
with a name** (010C candidate) — flagged, not silent; primary+variant
images satisfy "basic image/media import" (review call D-010B-6a if
ChatGPT wants the gallery in MVP).

**D-010B-7 — Safe refresh/update of previously imported products.**
New settings selection `product_import_refresh_mode`:
`snapshot_only` (**default** — Odoo fields written at first import
only; today's invariant that merchant edits are never overwritten) |
`shopify_fields` (opt-in: refresh re-applies the Shopify-owned
minimal set — price per D-010B-4, images per D-010B-6, attribute-line
**extensions**, new-variant creation). Structural **additions** (new
variants, new option values) apply in **both** modes — they are
additive and required for order import to keep resolving lines.
Payload-hash skip: the job's `payload_hash` becomes the remote
`updatedAt` (aligning with the Task 011/012 convention) so an
unchanged product re-enqueue collides on `idempotency_key` instead of
re-running; within a running job, unchanged snapshots short-circuit.
No imported Odoo field is ever written outside the declared minimal
set (source-guard test).

**D-010B-8 — Archived/deleted remote products.** GraphQL
`product: null` for a previously-bound GID = remote deletion →
binding `status='stale'` + one review-tagged log note; **never**
deletes/archives the Odoo product (sync-direction matrix row,
unchanged). `status=ARCHIVED` → binding `status='stale'` + note, Odoo
product untouched. A null product with **no** existing binding stays
`data_shape_schema_mismatch` (a first-import of a nonexistent GID is
a data error, not a deletion event). This corrects the merged
deletion-as-malformed behavior (§1.4).

**D-010B-9 — Binding & duplicate prevention.** Constraints unchanged
(dual uniqueness both models). New variants bind by `(store, variant
GID)`; deterministic-combination lookup replaces index-0 binding.
The **N+1 fix**: per-variant full-table exclusion scans are replaced
by (a) one prefetched map of the product's existing variant bindings
by GID, and (b) SKU/barcode candidate searches batched into one
`search` per product over the collected identifier set. No behavioral
change to match priority (binding → SKU → barcode → manual; RA-006
honored — no name matching).

**D-010B-10 — Atomicity.** One `env.cr.savepoint()` per product
(unchanged pattern) now covering: attributes/values/lines, template,
variants, images, prices, bindings — all or nothing; a later-variant
failure leaves no partial structure. Image downloads run **before**
the savepoint writes where practical (network out of transaction),
with byte payloads applied inside it.

**D-010B-11 — Performance & batch behavior.** Per-page processing
(≤100 variants per page) inside the one-product job; targeted
searches per D-010B-9; budget rows in
`../03-architecture/performance-budgets.md` §4: 100-variant product
import p95 ≤ 10 s excluding image downloads, ≤ 60 s including images
on the dev store (provisional; calibrated by the dev-store run).
A 2,048-variant import is exercised once on the dev store (§7) and
its wall-clock recorded (no budget asserted at that size in MVP —
recorded evidence for release hardening).

**D-010B-12 — Job/dispatch surface unchanged.** Same job type
(`product_import_sync`), same seams, same domain flag, same
targeting; the handler body grows, the contract does not. The
`JobPolicySkip` seam is NOT consumed here (nothing here is a policy
skip). No new error classes (fixed-16 registry intact).

## 4. Store settings added (module `_inherit` extension)

`product_import_media_enabled` (Boolean, default True);
`product_import_refresh_mode` (Selection snapshot_only/shopify_fields,
default snapshot_only);
`product_import_attribute_conflict_mode` (Selection
`manual_review`/`connector_owned`, **default `manual_review`** —
D-010B-2 incompatible same-name attribute handling).

## 5. Tests (exact files)

Updated: `test_product_import_matching.py` (the >100-variant
truncation-blocking tests become pagination tests: 250-variant fake
payload pages import completely; existing matching/ambiguity/gating
tests stay green unchanged), `test_product_duplicate_prevention.py`
(atomicity now covers attribute structure; re-import unchanged-skip
via payload-hash collision).
New: `test_product_attribute_import.py` (option→attribute/value/line
construction incl. case-insensitive reuse, position order,
Default-Title special case, additive value extension, dynamic mode
set at creation, structural-mismatch → binding_conflict; **existing
same-name `Color` with `create_variant='always'` → not reused, not
mutated → `manual_review` default routes to `binding_conflict`, and
under `connector_owned` creates `"Color (Shopify)"` dynamic; existing
`Size` with `no_variant` → same incompatible handling; a compatible
existing `dynamic` attribute → reused; concurrent
get-or-create/compatibility evaluation of a same-name attribute; a
brownfield database with a pre-existing `always` `Color` produces no
phantom cartesian variants**);
`test_product_variant_generation.py` (sparse-set determinism: Odoo
variants ≡ Shopify variants exactly, no phantom combinations; ≥1
case with 3 options; deterministic re-import idempotency; 150-variant
paginated fixture);
`test_product_price_import.py` (SoT gating both ways; single-variant
list_price; min+price_extra exact decomposition; undecomposable
fallback + note; 2dp interaction);
`test_product_media_import.py` (primary+variant image write;
checksum skip; merchant-image protection; size/content-type/network
failure routing; media flag off);
`test_product_refresh_and_stale.py` (snapshot_only vs shopify_fields
matrices; structural adds in both modes; deletion→stale with binding
vs data-error without; ARCHIVED→stale; no-write-outside-declared-set
source guard).
Source guards: query-only (no mutation strings); no name-matching;
no `search([('store_id','=',...)])` full-table exclusion pattern
remains (string scan).

## 6. Gate criteria (15-pattern, abbreviated)

1 CORE-R1 merged runtime-green (stores can reach `connected` for the
dev-store run); 2–3 exact names ✅(§3); 4 files ✅(§10); 5
thresholds/pagination/caps fixed ✅(D-010B-1); 6 no export/inventory/
publishing scope ✅; 7 no order/customer scope ✅; 8 no UI/webhook/
OAuth ✅; 9 tests ✅(§5); 10 rollback ✅(§8); 11 live dependency =
read-only dev-store validation (§7) — required, not waivable silently;
12 gate-act reconfirmation; 13 the three flagged calls explicit:
D-010B-2/3 dynamic-mode attribute strategy **incl. the
existing-attribute compatibility gate + `attribute_conflict_mode`
default `manual_review`**, D-010B-5 compare-at field relocation
(cross-packet), D-010B-6a gallery deferral; 14 refresh
ownership set explicit ✅(D-010B-7); 15 archived/deleted semantics
explicit ✅(D-010B-8).

## 7. Odoo.sh + live-Shopify validation (both required)

Odoo.sh: full three-suite run green before merge review (verbatim
quote, OP-43). Dev store (read-only): import (a) a 3-option sparse
multi-variant product, (b) a >100-variant product (pagination proof),
(c) the one-time 2,048-variant timing probe, (d) an image-bearing
product incl. refresh + merchant-image-protection check, (e) an
archived and a deleted product, **(f) a product whose option name
collides with a pre-existing incompatible-mode (`always`/`no_variant`)
Odoo attribute — proving the compatibility gate routes to
`manual_review` (or, under `connector_owned`, creates the distinctly
named attribute) and generates no phantom variants (the UAT fixture)**.
Redacted evidence in the validation
record; prerequisite is the CORE-R1 `connected` path + VAL-B2
credentials; if unavailable, ChatGPT explicitly waives at gate time
with the fact recorded (flagged option, not assumed).

## 8. Acceptance criteria / DoD / rollback

An ordinary multi-option Shopify product imports to a complete Odoo
product (attributes, values, lines, exactly-matching variants, price
per SoT, primary+variant images) atomically and idempotently; >100
variants paginate; refresh is safe per mode; **an existing
incompatible-mode same-name attribute is never reused or mutated and
never yields phantom variants (routes per `attribute_conflict_mode`)**;
deletion/archival → stale binding, Odoo data untouched; all suites +
Odoo.sh green + dev-store evidence; validation record + AR row +
handoff; draft PR; gate closes on draft-open. Rollback: revert the
single PR — the import **code path/behavior is removed**; the additive
binding table/columns may **remain inert/orphaned** in the database (a
normal code revert does **not** drop them — no destructive schema
cleanup is assumed; any cleanup is a separately tested migration, never
part of the revert); created products/attributes/values remain as
ordinary master data (documented, harmless — they are real catalog
records the merchant may keep or delete); no migration scripts in the
revert.

## 9. Register impacts on acceptance

The review's "Task 010 treated as complete" finding → closed by this
packet at planning level. **Re-review `4945129824` item 1
(existing-attribute compatibility) → closed by the D-010B-2
compatibility gate + `product_import_attribute_conflict_mode`.**
Task 012 packet prerequisite updated (010B before 012). Task 015
packet updated (compare-at field relocation D-010B-5).
`performance-budgets.md` §4 rows cite D-010B-11. Deferred-with-names:
010C media gallery.

## 10. Locked final implementation prompt (Task 010B)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE TASK-010B GATE, VERIFIES THE CURRENT BASE SHA,
AND ISSUES THIS PROMPT.

Implement Task 010B — product import completeness — exactly per
docs/07-implementation-plan/task-010b-product-import-completeness-packet.md
(D-010B-1..12 binding) and the cited captures. Branch from the
verified current Shopify-connector tip (STOP on drift). One session;
draft PR; stop.

ALLOWED FILES (exhaustive):
  addons/shopify_connector_product/models/shopify_connector_product_importer.py
  addons/shopify_connector_product/models/shopify_connector_product_template_binding.py   (image-checksum field only)
  addons/shopify_connector_product/models/shopify_connector_product_variant_binding.py    (image-checksum field only)
  addons/shopify_connector_product/models/shopify_connector_product_product.py            (NEW — _inherit product.product: shopify_compare_at_price)
  addons/shopify_connector_product/models/shopify_connector_store_settings.py             (NEW — the §4 settings fields incl. product_import_attribute_conflict_mode)
  addons/shopify_connector_product/models/__init__.py                                     (import lines)
  addons/shopify_connector_product/__manifest__.py                                        (version bump only)
  addons/shopify_connector_product/tests/{test_product_import_matching.py,
    test_product_duplicate_prevention.py}                                                 (named updates only)
  addons/shopify_connector_product/tests/{test_product_attribute_import.py,
    test_product_variant_generation.py, test_product_price_import.py,
    test_product_media_import.py, test_product_refresh_and_stale.py}                      (NEW)
  addons/shopify_connector_product/tests/__init__.py                                      (import lines for the new files)
  docs/05-qa/task-010b-validation-results.md                                              (NEW)
  docs/05-qa/architecture-review-log.md                                                   (append one AR row)
  docs/01-research/research-handoff.md                                                    (top entry)
FORBIDDEN: every core and sale file; any mutation toward Shopify
(query-only — source guard); inventory quantities; publishing;
metafields; gallery media beyond primary+variant images;
enumeration/scan triggers; UI/webhooks/OAuth/CI; adams_base; main;
plain dev.

IMPLEMENT exactly per the packet: D-010B-1 paginated extended query
(explicit first:100, cursors in-run only, 2048 defensive cap);
D-010B-2 case-insensitive get-or-create attributes/values with the
EXISTING-ATTRIBUTE COMPATIBILITY GATE (reuse only create_variant=
'dynamic'; an incompatible 'always'/'no_variant' same-name attribute
is never reused or mutated -> product_import_attribute_conflict_mode:
manual_review default routes to binding_conflict, connector_owned
creates a distinctly-named "<name> (Shopify)" dynamic attribute; never
change an attribute's mode; never generate phantom cartesian variants)
+ attribute lines + Default-Title special case; D-010B-3 dynamic-mode
deterministic variant instantiation (verify the 19.0 dynamic-creation
API against source before use — STOP and report if it differs; no
phantom variants; structural mismatch -> binding_conflict);
D-010B-4 price import gated on price_source_of_truth ==
'shopify_authoritative' (verified merged selection), min+price_extra
exact decomposition with undecomposable fallback note; D-010B-5
shopify_compare_at_price on product.product (import-filled);
D-010B-6 primary+variant image import with checksum skip,
merchant-image protection, 20MB/https/image-type caps, media flag;
D-010B-7 refresh modes (snapshot_only default; structural adds in
both modes; payload_hash = updatedAt); D-010B-8 deletion/ARCHIVED ->
binding stale + note, Odoo data untouched, no-binding null stays
data-error; D-010B-9 N+1 fix with unchanged match priority;
D-010B-10 one savepoint per product; D-010B-12 no new job types,
flags, or error classes. All §5 tests with every named case.

Runtime: full Odoo.sh run green before merge review (verbatim quote)
PLUS the §7 dev-store read-only validation evidence (or a recorded
explicit ChatGPT waiver). Stop condition: draft PR "Task 010B:
product import completeness (attributes, variants, prices, media)";
gate closes on draft-open. Do not start Task 011B/012, Area 6, export,
UI, or webhook work under any circumstance.
```
