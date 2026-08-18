# Product-Export Pre-UAT Review Packet — `shopify_connector_product_export` at `f62db111`

> Independent adversarial pre-UAT review (DEC-042 reviewer role) of the
> riskiest merchant-write surface: product export (productSet create,
> productUpdate, productVariantsBulk*, media). No update/create mutation has
> ever fired against a real store. All 8 non-media GraphQL documents were
> validated against the live Shopify Admin 2026-07 schema (all valid); the
> defects below are payload/semantic, not syntactic. The previously recorded
> custom-ID first-run deadlock (w1 correction packet) is excluded here.
>
> **Standing precaution, effective immediately: no export preview may be
> CONFIRMED against any store — dev or otherwise — until P0-1 and P0-2 are
> fixed.** Preview-only operation remains safe (previews make no mutation).

## P0 — blocks any live export confirmation

- **P0-1 — every update silently emits `status: DRAFT`, unpublishing live
  merchant products.** `_desired_scalars`
  (`shopify_connector_product_export_service.py:296-300`) sends `status`
  unconditionally — the only scalar with **no managed flag and no
  omit-absent rule** — and `shopify_export_status` defaults to `'draft'`
  (`..._seams.py:227-239`) while the importer enables export on every
  imported template but **never seeds the status from the real remote
  value** (`..._seams.py:318-327`; the import captures remote status onto
  the binding only). First-run path: operator edits a title on an imported
  ACTIVE product → preview shows `status: ACTIVE → DRAFT` as a *neutral*
  detail row (severity machinery is tags-only) while the diff narrative
  says "nothing else in this export removes anything" → confirm →
  `productUpdate` **delists the live product from the storefront and all
  channels**. Fix: seed `shopify_export_status` from `binding.shopify_status`
  at import; put `status` behind a managed flag with omit-absent semantics;
  give status downgrades their own severity section beside `tag_replacement`.
- **P0-2 — `_bind_created_variants` cannot succeed on the direct path**
  (`:3090-3103`): it iterates **all** template variants but
  `productVariantsBulkCreate` returns only the **newly created** ones, so
  adding a variant to an exported product mutates Shopify successfully and
  then raises before any binding is written; the re-preview then offers a
  second create for the same variant → `VARIANT_ALREADY_EXISTS` → the Odoo
  variant is permanently unbindable. Zero test coverage on this function.
  Fix: bind only the variants named in the attempt's
  `preconditions_snapshot` (the reconcile path already scopes itself
  correctly — mirror it).

## P1 — fix in the same export correction

- **P1-3 — create-path duplicate gate is preview-time-only** (`:1179-1196`
  vs `:1881-1989`): the remote custom-ID check never re-runs pre-C2 despite
  the module's own "a guard evaluated once is a guard that can be raced"
  rule (`:1508-1510`) and a 24-hour preview validity. A `productSet` landing
  on an existing product is declaratively authoritative over its `variants`
  list (always sent, `:1942-1945`) and gambles on the unsettled
  omitted-list-field semantics the module header refuses to gamble on.
  Fix: re-run the custom-ID read inside `_prepare_preconditions_create`,
  fail closed on any hit.
- **P1-4 — no currency guard anywhere in export** (`_money` `:224-227`):
  a EUR Odoo company exporting to a USD store writes EUR magnitudes as USD
  prices, previewed as a clean number row; no store-vs-company currency
  assertion, no conversion, no disclosure; `lst_price` also lacks UoM
  context pinning. Fix: fail-closed currency identity check at preview and
  pre-C2 (conversion is out of scope for this iteration).
- **P1-5 — `productUpdate` rejections are unreportable**: 2026-07
  `ProductUpdatePayload.userErrors` carries `field`/`message` only (no
  `code`), and the shared classifier reads `code` → every rejection becomes
  "Shopify rejected the request (UNKNOWN)" with message/field discarded
  everywhere (`:1689-1705`). Fix: classifier falls back to
  `field + message`; persist both in evidence.
- **P1-6 — remote drift gate runs once per apply, before step 1 only**
  (`:1300-1327` vs `:1425-1439`): between apply and the update step a
  merchant-added tag (e.g. `bfcm-2026`) is silently removed by the
  complete-list tag write — a removal never shown in
  `tag_replacement.removed`. Fix: re-read/re-verify remote `updated_at`
  (and the tag list) pre-C2 in the update step, or at minimum for the
  tag-carrying mutation.

## P2 (same pass)

media poll cron loops forever on `pending:` placeholder GIDs, one failing
job per tick (`media_export_service.py:1073-1092`, `:1148-1175`);
re-preview of a partially-completed media export double-creates the File
and permanently poisons filename-based reconcile (`:261-280`, `:432-438`);
`_connector_filename` omits the media role → template+variant same-bytes
collision (`:176-185`); remote variant read `variants(first: 101)` has no
truncation detection unlike the media read (`:402-409`);
byte-for-byte scalar reconcile vs Shopify-normalized
`descriptionHtml`/`title` → false `not_applied` after successful writes and
never-converging previews (`:2560-2564`, `:913-924`); binding-definition
reconcile is namespace- and capability-blind — a merchant-owned
`custom.odoo_template_id` definition falsely opens the create path
(`:1809-1849`).

## P3

Stale `ProductSetInput.id` comment (`:2475-2478`, the field no longer
exists); tag comparison is case/trim-sensitive vs Shopify normalization →
never-converging diff rows; `_prepare_preconditions_update` can build an
empty `product_input` with no non-empty assertion (latent).

## Confirmed solid (preserve)

All 8 GraphQL documents schema-valid; `ProductVariantSetInput.sku`
top-level vs `ProductVariantsBulkInput.inventoryItem.sku` two-shape
distinction correctly implemented; `allowPartialUpdates: False` with
atomic classification (verified semantics — no partial-success hole);
decimal-string money with genuine `compareAtPrice` omission;
`assert_no_forbidden_keys` recursion on envelope and per-entry;
append-only media at the payload level (`referencesToAdd` only, no
`fileDelete` anywhere); the READY gate re-checked pre-request; preview
write-surface immutability; rigorous create-path variant matching;
tag-replacement disclosure design.

## OPEN QUESTIONS (live-store verification required first)

1. Does `productSet` with `identifier.customId` persist the metafield on
   the created product? The whole reconcile-by-custom-ID design depends on
   it — test with a deliberately-killed create.
2. Does the app-reserved namespace resolve identically for
   `metafieldDefinitionCreate` (omitted namespace) and
   `productByIdentifier`/`productSet` `customId` under this connector's
   custom-app token?
3. Is there a synchronous-mode variant cap on `productSet` at or below the
   module's `MAX_EXPORT_VARIANTS = 100`?
4. Does Shopify normalize `descriptionHtml` (sizes the false-`not_applied`
   defect)?
5. Title collision on create: silent handle-suffix success or userError?
   (No handle handling exists.)

## Definition of done

P0-1/P0-2 fixed with behavioral tests using imported-product fixtures
(status seeded from remote, direct-path variant binding); P1 set fixed;
P2 fixed inline; open questions resolved on the dev store with recorded
evidence; the export-confirmation freeze lifts only after the fixes are
runtime-qualified; first live confirmations then follow the ledger's
controlled-UAT format (preview → confirm → verified remote read →
idempotent repeat).
