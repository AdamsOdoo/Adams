# Task 010B — Product Import Completeness: Validation Results

> **Status: draft-PR validation record. Implementation session output,
> awaiting ChatGPT review.** Produced 2026-07-11 by the Task 010B
> implementation session against the OPEN gate (PR #149 comment
> `4948723366`). **Revised 2026-07-12** per control-room static review
> `4950202231` (see §0). Odoo.sh and live/dev-store evidence are **not**
> part of this session (no Odoo runtime and no Shopify credentials are
> available here) and remain mandatory before merge acceptance (§10 below).

---

## 0. Revision 1 — control-room static review `4950202231` (2026-07-12)

The first control-room static review (PR stayed draft) found several
overclaimed decisions at head `1065cdf`. This revision corrects them on
the same PR (files: the importer, the template-binding model, and four
test files; docs). Corrections, each honestly scoped:

1. **Pagination now strictly shape-validated.** `_fetch_product_with_all_
   variant_pages` requires `data`/`product`/`variants`/`pageInfo` to be
   mappings, `nodes` a list, `hasNextPage` a real Boolean, and `endCursor`
   a non-empty string when `hasNextPage` is true. A missing/null/wrong-type
   `pageInfo` is **never** treated as a completed single page (that risked
   silent truncation). All violations → `data_shape_schema_mismatch`; no
   product/binding is written (validated before `_apply_import`). New tests
   cover every malformed shape.
2. **Real `updatedAt` short-circuit** (was fetched but unused). New readonly
   `shopify_updated_at` (Char) on the template binding; an active binding
   recording the exact non-empty remote `updatedAt` short-circuits the
   import **before** any media download or product/attribute/price/image/
   binding write, returning an `unchanged` indicator. The stamp is written
   **only after** a complete success (rolled back on any failure).
   Enqueue-level `payload_hash = updatedAt` is recorded as an **Area-6
   integration obligation** — this task has no enqueue call site and never
   mutates a running job's payload hash. The prior "manual duplicate-job"
   test (which only proved the core idempotency constraint) is replaced by
   real importer tests.
3. **Same-URL image ownership fixed.** The skip decision now compares the
   **current Odoo image checksum** against the recorded connector checksum
   (not URL + recorded-checksum alone). Same URL + merchant-replaced image
   → protected + note (no download); same URL + cleared image → preserved
   under `snapshot_only`, restored under `shopify_fields`. Covers both
   `image_1920` and `image_variant_1920`.
4. **SVG / spoofed bodies rejected.** `image/svg+xml`/`image/svg`/any
   `svg` content-type is rejected; downloaded bytes are validated as a
   supported raster image via Pillow (`Image.verify()` + format
   whitelist), so SVG markup or junk labelled `image/png` is rejected
   (`shopify_temporary_server_network`), never exposing the body. Global
   Pillow config is untouched.
5. **Bounded aggregate media memory.** Each image streams into a
   `SpooledTemporaryFile` (in-memory up to 1 MB, then disk); an `ExitStack`
   closes every staged file on success, download failure, validation
   failure, DB failure, and classified failure. No dict of full image byte
   strings is retained; at most one staged image is read fully into memory
   for its Odoo write. The 20 MB cap, HTTPS/redirect restrictions, and the
   "downloads before the savepoint, DB writes inside it" split are kept.
6. **`connector_owned` refresh fixed.** Refresh resolves the one template
   line whose attribute name is exactly the Shopify option name OR exactly
   `"<name> (Shopify)"`; no candidate → `binding_conflict`; both present →
   `binding_conflict` (fail closed); the merchant attribute is never
   modified. New value/new variant on refresh now extends the connector
   attribute in both refresh modes.
7. **Concurrency proof strengthened to the real import path.** The prior
   test exercised the lock + direct attribute resolver only. The new
   `test_real_concurrent_full_imports_create_one_global_attribute` runs the
   REAL `_apply_import` for two products (same new option) across two
   genuinely independent PostgreSQL connections (`odoo.sql_db.db_connect`),
   with committed synthetic stores visible to both: B holds the lock via
   its uncommitted transaction, A's concurrent full import gets
   `concurrency_race_conflict`, and after B commits A retries and reuses
   B's committed attribute (exactly one attribute; both products bound;
   durable cleanup). `TransactionCase`'s `registry.cursor()` (a shared
   `TestCursor`) is **not** presented as independent concurrency.
8. **Documentation corrected** (this file, AR-044, handoff, PR body) to
   remove the prior overclaims.

---

## 1. Base verification (hard prerequisite)

- **Required base SHA:** `f9c3c5fd25af3f94ee71cc2ead3821e7da85443d`.
- **`Shopify-connector` tip at session start:**
  `f9c3c5fd25af3f94ee71cc2ead3821e7da85443d` — **exact match, no drift.**
- **PR #149** (CORE-R1) verified **merged** via GitHub
  (`merged_at 2026-07-11T20:50:22Z`); its merge commit is the branch tip.
- **Gate comment `4948723366`** read verbatim: *"Task 010B implementation
  gate opened by ChatGPT. Required base:
  `f9c3c5fd25af3f94ee71cc2ead3821e7da85443d`. One draft implementation PR
  only. All other task gates remain closed."*
- **Branch:** `claude/product-import-completeness-010b-5l07ci` (the
  session's designated branch, created from the verified base SHA).
- No STOP condition triggered: the packet does not conflict with the
  merged implementation, every Odoo 19 API named in the packet was
  verified against the actual 19.0 source (matches — §3), every Shopify
  2026-07 field was verified (§4), and the allowed-files list is
  structurally sufficient (§7).

## 2. Exact changed files (21, all inside the packet allowlist)

**Production/model:**
1. `addons/shopify_connector_product/models/shopify_connector_product_importer.py` (rewrite: D-010B-1..12)
2. `addons/shopify_connector_product/models/shopify_connector_product_template_binding.py` (+`shopify_image_checksum`)
3. `addons/shopify_connector_product/models/shopify_connector_product_variant_binding.py` (+`shopify_image_checksum`)
4. `addons/shopify_connector_product/models/shopify_connector_product_product.py` (NEW — `_inherit product.product`: `shopify_compare_at_price`)
5. `addons/shopify_connector_product/models/shopify_connector_store_settings.py` (NEW — `_inherit`: the 3 §4 settings)
6. `addons/shopify_connector_product/models/shopify_connector_attribute_lock.py` (NEW — singleton lock model)
7. `addons/shopify_connector_product/models/__init__.py` (import lines)

**Data/security/manifest:**
8. `addons/shopify_connector_product/data/shopify_connector_attribute_lock.xml` (NEW — one `noupdate=1` lock row)
9. `addons/shopify_connector_product/security/ir.model.access.csv` (one row for the lock model only)
10. `addons/shopify_connector_product/__manifest__.py` (data entry + version bump `19.0.1.0.0`→`19.0.2.0.0`)

**Tests:**
11. `addons/shopify_connector_product/tests/test_product_import_matching.py` (pagination updates)
12. `addons/shopify_connector_product/tests/test_product_duplicate_prevention.py` (structured atomicity/idempotency)
13. `addons/shopify_connector_product/tests/test_product_attribute_import.py` (NEW)
14. `addons/shopify_connector_product/tests/test_product_variant_generation.py` (NEW)
15. `addons/shopify_connector_product/tests/test_product_price_import.py` (NEW)
16. `addons/shopify_connector_product/tests/test_product_media_import.py` (NEW)
17. `addons/shopify_connector_product/tests/test_product_refresh_and_stale.py` (NEW)
18. `addons/shopify_connector_product/tests/__init__.py` (import lines)

**Documentation:**
19. `docs/05-qa/task-010b-validation-results.md` (this file, NEW)
20. `docs/05-qa/architecture-review-log.md` (one AR row appended)
21. `docs/01-research/research-handoff.md` (one top entry added)

**No forbidden file changed:** no `shopify_connector_core` or
`shopify_connector_sale` file; no `adams_base`; no inventory/stock model;
no Shopify mutation; no cron/migration/CI/UI/webhook/OAuth file; `main`
and plain `dev` untouched.

## 3. Odoo 19.0 internal-API verification (actual source, not memory)

All facts below were read from the **actual Odoo 19.0 source** this
session (raw `odoo/odoo@19.0` files) and match the packet's assumptions.

| API | Verified fact | Source |
| --- | --- | --- |
| `product.attribute.create_variant` | Selection `[('always','Instantly'),('dynamic','Dynamically'),('no_variant','Never')]`, default `'always'`. `write()` **raises `UserError`** if `create_variant` changes while `number_related_products` is set — mode is immutable once used. | `addons/product/models/product_attribute.py` |
| `product.template._create_product_variant` | `def _create_product_variant(self, combination, log_warning=False)`; arg is a `product.template.attribute.value` recordset; returns the `product.product`; *"possible to create only if the template has dynamic attributes and the combination itself is possible"*; reactivates an archived variant. | `addons/product/models/product_template.py` |
| dynamic variant generation | `_create_variant_ids()` with dynamic attributes **skips** cartesian auto-generation; variants are made on-demand via `_create_product_variant`. Also `_get_variant_for_combination(combination)` resolves an existing variant. | `addons/product/models/product_template.py` |
| `product.template.attribute.line` | create() calls `_update_product_template_attribute_values()` and triggers `_create_variant_ids()`; `value_ids` (m2m `product.attribute.value`) generates `product_template_value_ids` (the PTAV set). | `addons/product/models/product_template_attribute_line.py` |
| `product.template.attribute.value.price_extra` | `fields.Float(string="Extra Price", default=0.0, min_display_digits='Product Price', ...)`; uniqueness `unique(attribute_line_id, product_attribute_value_id)`. | `addons/product/models/product_template_attribute_value.py` |
| `product.attribute.value` | `name` (Char, required, translate), `attribute_id` (required, cascade); **no** name/attribute SQL uniqueness → get-or-create by search is correct. `_order='attribute_id, sequence, id'`. | `addons/product/models/product_attribute_value.py` |
| `product.template.image_1920` | `product.template` `_inherit` includes `image.mixin` → `image_1920`. | `addons/product/models/product_template.py` |
| `product.product.image_variant_1920` | `image_variant_1920 = fields.Image("Variant Image", max_width=1920, max_height=1920)`. | `addons/product/models/product_product.py` |
| `BaseModel.try_lock_for_update` | `def try_lock_for_update(self, *, allow_referencing=False, limit=None) -> Self`: issues `SELECT ... FOR UPDATE SKIP LOCKED` (deliberately **not** NOWAIT); *"Skip locked records and browse the records that could be locked"*; returns the recordset of rows it could lock (**empty if already locked** by another transaction); lock held to transaction end. `lock_for_update()` raises `LockError` if not all rows lock. | `odoo/orm/models.py` |
| Product-Price precision | `decimal.precision` "Product Price" defaults to **2** digits; `res.currency` carries per-currency `rounding`/`decimal_places`. | `addons/product/data/product_data.xml`; captures §6 |

**Lock-design consequence (key finding):** `try_lock_for_update()` is
**non-blocking (SKIP LOCKED)**. This *supports the accepted D-010B-2
design as written*: the packet requires "never proceed with unprotected
creation when the lock is unavailable", which is only meaningful for a
non-blocking primitive. The importer acquires the singleton lock, and if
the recordset comes back empty (another transaction holds it) it raises
`concurrency_race_conflict` (an auto-retry class), so the import backs off
and, on a later attempt, acquires the lock, re-resolves, and reuses the
first transaction's committed attribute. No architecture change was
needed; no STOP was triggered.

## 4. Shopify Admin GraphQL 2026-07 verification

From the accepted captures (`../00-source-materials/odoo19-shopify-
official-captures-2026-07-11.md` §9/§11) and the official references they
cite:

- `Product.options { id name position optionValues { id name } }`, ≤3
  options; variant pagination via `variants(first: N, after: $cursor)` +
  `pageInfo { hasNextPage endCursor }`; **no documented default page
  size** → `first` is always explicit; a single product at the root can
  return up to 2,048 variants; the **2,048 variants/product** ceiling is
  GA for all merchants (changelog 2025-10-15).
- `ProductVariant.compareAtPrice`: *"The compare-at price of the variant
  in the default shop currency."*, type `Money`. `Money` is a decimal
  string ("19.99"); zero-decimal display currencies exist (formatting,
  not API-precision).
- Product deletion surfaces as a **null product node**; archival as
  `Product.status = ARCHIVED`.
- **Deprecation noted (honest):** `ProductVariant.image` is **Deprecated**
  in favour of `ProductVariant.media`; the accepted packet D-010B-1
  nevertheless names `image { url }` for a read, so this task uses the
  packet-named field and records the deprecation. A future task may
  migrate the variant-image read to `media`. `inventoryItem { id }` is
  requested per D-010B-1 but **never stored or acted on** (no inventory
  model is touched).

## 5. Implementation summary (D-010B-1 … D-010B-12)

- **D-010B-1 (query + pagination):** `PRODUCT_IMPORT_QUERY` extended to
  `id title status descriptionHtml vendor productType tags updatedAt
  featuredImage{url} options{id name position optionValues{id name}}` and
  `variants(first:100, after:$cursor){ nodes{ id sku barcode price
  compareAtPrice selectedOptions{name value} image{url} inventoryItem{id}
  } pageInfo{hasNextPage endCursor} }`. `import_product_sync` loops pages
  (cursor in-run only) until `hasNextPage` is false; `first` always
  explicit; accumulated cap 2,048 → `data_shape_schema_mismatch`;
  malformed pageInfo / missing endCursor with `hasNextPage` →
  `data_shape_schema_mismatch`. Never a mutation; client error taxonomy
  preserved.
- **D-010B-2 (attributes/values/lines + compatibility gate + lock):** for
  each option in position order, `product.attribute` resolved
  case-insensitively; reused **only** when `create_variant=='dynamic'`;
  incompatible `always`/`no_variant` same-name attribute → per
  `product_import_attribute_conflict_mode` (default `manual_review` →
  `binding_conflict`; `connector_owned` → distinct `"<name> (Shopify)"`
  dynamic attribute). Existing modes never changed. Values get-or-created
  under the resolved attribute; one line per option; `Title`/`Default
  Title` → no structure. Global serialization via
  `shopify.connector.attribute.lock._acquire_or_raise()`
  (`try_lock_for_update()`) before any global attribute resolve/create;
  unavailable lock → `concurrency_race_conflict`; a **real full-import
  two-connection test** (§0.7) proves exactly one attribute is created and
  the second import reuses it. Refresh resolves the exact Shopify-name or
  exact `"<name> (Shopify)"` line and fails closed if both exist (§0.6).
- **D-010B-3 (sparse variants):** every used attribute is dynamic; each
  Shopify variant's `selectedOptions` maps to the template PTAV
  combination and `product.template._create_product_variant` instantiates
  exactly that variant. Odoo variants ≡ Shopify variants; no cartesian
  phantoms; no index-0 fallback for multi-variant; structural mismatch on
  a merchant product → `binding_conflict`.
- **D-010B-4 (base price):** written only when
  `price_source_of_truth=='shopify_authoritative'` and the path may write
  (first import, or `shopify_fields` refresh). Single variant →
  `list_price=price`; multi → `list_price=min`; per-value deltas
  decomposed onto `price_extra` **only when the additive model fits
  exactly** (verified with `float_compare` at Product-Price precision),
  else `list_price=min` + one `price_undecomposable` note, snapshots keep
  fidelity. No binary-float equality.
- **D-010B-5 (compare-at):** `shopify_compare_at_price` on
  `product.product`, connector-maintained, populated during import,
  shop-currency semantics documented; no export; binding snapshots
  unchanged.
- **D-010B-6 (images):** primary product + per-variant only; HTTPS-only,
  redirects followed manually and only to HTTPS, content-type `image/*`
  and **never SVG**, 20 MB streamed cap, bounded timeouts, **no
  credential/token on the media request**; downloaded bytes **validated as
  a supported raster image via Pillow** (SVG markup / junk labelled
  `image/png` rejected, never exposing the body); writes
  `image_1920`/`image_variant_1920`; **checksum ownership compares the
  current Odoo image checksum against the recorded connector checksum**
  (§0.3) so a same-URL merchant edit/clear is protected, not silently
  skipped; each image streams into a `SpooledTemporaryFile` with
  `ExitStack` cleanup (§0.5); per-store `product_import_media_enabled`
  (default True). Any fetch/validation failure →
  `shopify_temporary_server_network`, never a hold.
- **D-010B-7 (safe refresh):** `product_import_refresh_mode`
  (`snapshot_only` default | `shopify_fields`). snapshot_only never
  overwrites merchant-editable Odoo fields; shopify_fields re-applies the
  Shopify-owned set (SoT price, connector images). Structural additions
  (new variants, additive values) apply in **both** modes. A real
  `updatedAt` short-circuit (§0.2) skips an unchanged product before any
  media/DB write via the new readonly `shopify_updated_at` binding field
  (stamped only after a complete success). Enqueue-level `payload_hash =
  updatedAt` is an **Area-6 obligation**, not implemented here (this task
  has no enqueue call site; a running job's payload hash is never
  mutated).
- **D-010B-8 (archived/deleted):** null product for a bound GID →
  binding+variant bindings `stale` + note, Odoo master untouched;
  `ARCHIVED` → binding `stale` + note, no master writes; null product with
  no binding → `data_shape_schema_mismatch`.
- **D-010B-9 (duplicate prevention + N+1):** match priority unchanged
  (binding→SKU→barcode→manual; no name matching). Per-variant full-table
  scans replaced by one prefetched binding map + batched SKU/barcode
  candidate searches per product. Both uniqueness constraints intact; no
  bypass flag.
- **D-010B-10 (atomicity):** one `self.env.cr.savepoint()` per product
  covers all writes; Shopify reads and image downloads run before the
  savepoint. A later-variant failure leaves no partial structure
  (including no orphan attribute).
- **D-010B-11 (performance):** N+1 removed; page-at-a-time processing;
  budgets not measured here (no runtime — §10).
- **D-010B-12 (job contract):** same job type `product_import_sync`, same
  handler/domain-flag/target, same error taxonomy, same retry behaviour.
  No new job type/flag/error class; no mutation.

## 6. Commands executed and local/static results

- `git fetch` state verified; branch at base SHA; working tree clean at start.
- `python3 -m compileall -q addons/shopify_connector_product/` → **clean**
  (all production and test files compile).
- Per-file `python3 -m py_compile` on every changed Python file → clean.
- XML well-formedness check on `data/shopify_connector_attribute_lock.xml`
  → well-formed.
- Source-guard greps (see §7).
- **No Odoo runtime is available in this environment** (`import odoo` →
  `ModuleNotFoundError`, same as the CORE-R1 session), so the test suite
  was **not executed here**; Odoo.sh execution is the runtime gate (§10).

## 7. Test inventory (static method counts, not Odoo test counts)

| File | `def test_*` methods |
| --- | --- |
| test_product_template_binding.py (unchanged) | 7 |
| test_product_variant_binding.py (unchanged) | 6 |
| test_product_import_matching.py | 41 |
| test_product_duplicate_prevention.py | 12 |
| test_product_attribute_import.py | 16 |
| test_product_variant_generation.py | 8 |
| test_product_price_import.py | 9 |
| test_product_media_import.py | 22 |
| test_product_refresh_and_stale.py | 14 |
| **Total** | **135** (110 at head `1065cdf`; 61 at CORE-R1) |

Coverage maps to every §21 named case: pagination (250 across pages, 150
fixture, 2,048 cap, malformed pageInfo, missing endCursor, no mutation);
attributes (ci dynamic reuse, new dynamic, Default-Title, position,
additive values, existing-`always`→manual-review, existing-`no_variant`→
manual-review, connector_owned `"Color (Shopify)"`, merchant unchanged, no
phantom, brownfield, **real concurrent transactions → one attribute**);
variants (sparse 2- and 3-option, exact equality, no cartesian,
deterministic re-import, structural mismatch → binding_conflict,
later-variant rollback); price (SoT both ways, unset, single list_price,
min, exact `price_extra`, undecomposable note, decimal precision);
images (primary, variant, unchanged skip, merchant protection, switch off,
HTTPS-only, redirect-to-non-HTTPS rejection, wrong content-type, oversized,
timeout/network, no secret); refresh/stale (snapshot_only, shopify_fields,
structural adds in both, unchanged-updatedAt idempotency collision,
archived→stale, deleted-bound→stale, deleted-unbound→data-error, no Odoo
deletion, source-level declared-write guard).

## 8. Source-level guards, sudo inventory, network behaviour

- **Query-only / no mutation:** `PRODUCT_IMPORT_QUERY` starts with `query`
  and contains no `mutation` (grep + test asserted).
- **No bypass flags:** none of `bypass`/`force_create`/`skip_gate`/
  `skip_duplicate`/`ignore_duplicate`/`allow_blind` appear (test asserted).
- **No customer/order/inventory/fulfilment models:** no `sale.order`,
  `res.partner`, `stock.*`, `account.*`, `delivery.carrier` in the model
  files (grep + test asserted).
- **Savepoint:** `self.env.cr.savepoint()` present (test asserted).
- **`list_price` write locality:** every `list_price` assignment lives
  inside `_apply_prices` (source-level test asserted).
- **Sudo inventory:** **zero new `sudo()` sites** in any
  `shopify_connector_product` file (grep clean). Job-log notes are emitted
  through the sanctioned core `job.log._system_append()` path (which
  itself holds the one authorized job-log sudo) — no new elevated context.
- **Media request carries no secret:** `_fetch_image` attaches no headers
  and no auth; the importer file contains neither `X-Shopify-Access-Token`
  nor `_get_access_token` (test asserted). HTTPS-only, redirect-HTTPS-only,
  content-type `image/*`, 20 MB streamed cap, bounded timeouts.

## 9. Performance evidence

Not measured in this session (no Odoo runtime, no dev store). The N+1
per-variant full-table scans are removed by construction (one prefetch +
batched candidate searches per product). The p95 budgets (100-variant
≤10 s excl. images; ≤60 s incl. images) and the 2,048-variant timing probe
are dev-store measurements deferred to the runtime validation session
(§10). No optimization weakened duplicate protection, merchant-edit
protection, or atomicity.

## 10. Mandatory runtime/live evidence still outstanding (honest)

Not obtained this session and **required before merge acceptance**:

- **Odoo.sh:** full three-suite run (`shopify_connector_core`,
  `shopify_connector_product`, `shopify_connector_sale`) with exact
  verbatim totals, **0 failed / 0 error**.
- **Live/dev-store (read-only):** three-option sparse product; a >100-
  variant product; the one 2,048-variant timing probe; product + variant
  images with refresh + merchant-image-protection; an archived product; a
  deleted bound product; an incompatible same-name Odoo attribute.

These are **not faked and not waived**. The PR is kept **draft**; a later
validation-only session (or an explicit ChatGPT waiver recorded at gate
time) closes them.

**Concurrency-test isolation note (honest):** the real concurrent-
transaction test opens a genuinely independent PostgreSQL connection with
`odoo.sql_db.db_connect(...).cursor()` — **not** `self.registry.cursor()`,
which in a `TransactionCase` returns a `TestCursor` layered on the same
underlying connection (one PG session, no real `FOR UPDATE SKIP LOCKED`
contention). With the independent connection the two backends genuinely
contend on the singleton lock row, proving exactly one attribute is
created. The committed attribute is cleaned up durably via a third
independent connection. `TransactionCase` still cannot exercise true
multi-worker/multi-server execution; that named caveat stands and is the
subject of the dev-store validation.

## 11. Rollback

Rollback is the single-PR revert. It removes the new import behaviour but
does **not** drop the additive columns
(`shopify_image_checksum` ×2, `shopify_compare_at_price`) or the lock
table/row, and does **not** delete imported products, attributes, values,
images, or bindings — those remain as ordinary Odoo master data. Any
optional schema cleanup is a separately tested migration, never part of
the revert. No destructive migration is part of this task.

## 12. Definition-of-done checklist

- [x] Base SHA verified (`f9c3c5f…`); PR #149 merged; gate `4948723366` read.
- [x] Only allowed files changed (21; no forbidden file).
- [x] D-010B-1 … D-010B-12 implemented.
- [x] Odoo 19 internals verified against actual 19.0 source before use.
- [x] Shopify 2026-07 fields verified (variant-`image` deprecation noted).
- [x] All required tests exist (135 methods; every §21 case + review
      `4950202231` items 1-8).
- [x] All locally executable checks pass (compileall, py_compile, XML,
      source guards).
- [x] No Shopify mutation; no phantom Odoo variants; import atomic;
      merchant images protected; price writes respect SoT; archived/deleted
      never delete Odoo master data.
- [x] Concurrent attribute creation proven to yield one attribute (real
      two-transaction test).
- [x] Validation record (this file) + AR row + handoff entry.
- [x] Draft PR opened into `Shopify-connector`; session stops after.
- [ ] **Odoo.sh green (verbatim)** — outstanding (§10).
- [ ] **Live/dev-store evidence** — outstanding (§10).

All other task gates (011B, LC-1, 012, Area 6, SEC-1, inventory,
fulfillment, product export, UI/Owl, webhooks, OAuth, PERF-1) stayed
**closed**; no other task was started or prepared.
