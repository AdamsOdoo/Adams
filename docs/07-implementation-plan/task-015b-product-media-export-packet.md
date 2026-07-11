# Task 015B — Basic Product Media/Image Export: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §9 is NOT usable.** Produced 2026-07-11 by the PR #148
> revision session, implementing review item 3 of ChatGPT's
> control-room review (PR #148 comment `4942966937`): the accepted
> DEC-003 capability "basic image / media update/export, where
> feasible" — deferred by Task 015's D-015-7 to an unnamed candidate —
> is now a **complete MVP packet**, sequenced after Task 015 and
> **before final UAT and release**. Feasibility is now
> evidence-established: the current, non-deprecated media/file API
> path is fully captured (captures 2026-07-11 §10;
> `../00-source-materials/odoo19-shopify-official-captures-2026-07-11.md`).
> Extends `shopify_connector_product_export` (PD-1 write-risk
> boundary preserved — all catalog mutations stay in one module).

## 1. Objective, scope, non-goals

Export the **basic media set** — the Odoo primary product image
(`image_1920`) and per-variant images (`image_variant_1920`),
including those imported by Task 010B — to Shopify for
export-enabled, bound templates, using only current non-deprecated
APIs, asynchronously, preview-first, and destructive-guarded.
**Non-goals:** no gallery/extra-media breadth (the 010C/015C
candidates); no video/3D models (images only); no media for unbound
or non-export-enabled products; no deletion of any remote media the
connector did not create (hard guard); no publishing; no
`productCreateMedia`/`productDeleteMedia` (both deprecated — captures
§10); no reordering beyond placing the primary image first.

## 2. API surface (exact, version 2026-07 — all current/non-deprecated)

- **Upload:** Odoo image binaries are not publicly reachable, so the
  path is `stagedUploadsCreate` → HTTP upload to the staged target →
  `fileCreate` with the staged resource URL ("Creates file assets for
  a store from external URLs or files that were previously uploaded
  using the `stagedUploadsCreate` mutation" — captures §10).
  `duplicateResolutionMode` left at APPEND_UUID; filenames are
  connector-generated (`odoo-<template_id>-<checksum8>.<ext>`) so
  ownership is recognizable and idempotency checkable.
- **Async processing:** "Files are processed asynchronously. You poll
  the `fileStatus` field until it's `READY`" (captures §10);
  media status enum UPLOADED/PROCESSING/READY/FAILED.
- **Association (only after the File reaches `READY` — D-015B-4):**
  product association via `productUpdate` media/files input (the
  documented `productCreateMedia` replacement) yields the
  **Product Media GID** (`shopify_product_media_gid`); variant
  association via `productVariantAppendMedia` /
  `productVariantDetachMedia` (both current). Primary-image ordering
  via `productReorderMedia` (async `Job`) only after association
  succeeds and only when the primary is not already first.
- **Replacement/removal of connector-owned media:** `fileDelete`
  (current) strictly limited to a **File GID** recorded in the
  connector's media binding (D-015B-2) **and** proven by a fresh
  reference/association read to carry no reference other than the
  connector-owned one being removed — after preview enumeration and
  confirmation. When exclusivity is not proven, the connector
  **detaches only its own association and retains the File**.
- Scopes: `write_products` (already required by Task 015's readiness
  check; `productVariantDetachMedia` documented `write_products` —
  captures §10). Staged upload target interaction is plain HTTPS to
  the returned URL (no new scopes; transport constraints mirror
  Task 010B's image-download rules: https-only, timeout, size cap).

## 3. Decision closures (D-015B-1 … D-015B-7) — each Proposed

**D-015B-1 — Ownership registry (media binding) — exact identities
(re-review `4945129824` item 3).** New model
`shopify.connector.product.media.binding` on the binding mixin. The
APIs use **distinct** identities, so the registry stores each
separately (the ambiguous phrase "Media/File GID" is removed):
- **`shopify_gid`** (mixin field) = the **File GID** — the
  `MediaImage`/File asset returned by `fileCreate` (the durable asset
  in the store's Files; the identity `fileDelete` targets and the proof
  the connector *created* it).
- **`shopify_product_media_gid`** (Char ro) = the **Product Media GID**
  — the product-level media reference created when the File is
  associated to the product; the identity `productReorderMedia` and
  product-scope detach operate on. Null until association succeeds
  (D-015B-4).
- **variant association identity** = the pair
  (`product_variant_binding_id`, `shopify_gid`) — the argument shape
  `productVariantAppendMedia`/`productVariantDetachMedia` require; no
  separate GID exists for it.
Plus `product_template_binding_id` (required, restrict),
`product_variant_binding_id` (optional, restrict — set for variant
images), `odoo_image_checksum` (Char required ro — SHA-256 of the
exported binary), `media_role` (Selection `primary`/`variant`),
`remote_status` (Selection uploaded/processing/ready/failed, ro),
`exported_at`/`last_verified_at` (Datetime ro). Uniqueness:
`(store_id, shopify_gid)` +
`(store_id, product_variant_binding_id, media_role)` where variant set,
and `(store_id, product_template_binding_id, media_role)` for primary
rows (one primary per template per store). **The registry is the
destructive-guard boundary, but registry membership proves only that
the connector *created* the File — not that the File is *exclusively*
used now (D-015B-2/6): every `fileDelete` requires a fresh reference
check.**

**D-015B-2 — Destructive-media guard.** Preview enumerates, per
template: adds (no registry row, Odoo image present), updates
(registry checksum ≠ current Odoo image checksum → replace = upload
new + detach/delete old **connector-owned** GID), and no-ops.
Merchant-uploaded media (remote media GIDs absent from the registry)
are **never** touched, deleted, reordered past, or counted as
replaceable — enumerated in the preview as "foreign media — left
untouched". Empty Odoo image with an existing registry row →
proposed removal of the connector-owned remote image, listed
explicitly and applied only on confirmation (never implicit).
**Fresh reference check before any `fileDelete` (re-review item 3):**
registry ownership proves the connector *created* the File, not that
it is *exclusively* used now — a merchant can reuse a connector-created
File on another product. Before deleting a File the apply step performs
a **fresh reference/association read** (the File's current
product/variant references) and deletes **only** when the File is
proven to have no reference other than the connector-owned association
being removed. When exclusive use cannot be proven, the safe default
is to **detach only the connector-owned association and retain the
File** (never delete), recording a "retained — shared/foreign
reference" note. This applies to both the preview enumeration and the
apply guard.

**D-015B-3 — Preview/confirm flow (reuse, not reinvent).** Media
export rides the Task 015 preview mechanism: the
`product_export_preview` diff gains a media section (adds/updates/
removals/foreign-untouched); `product_export_apply` continues to
refuse without a confirmed, unexpired preview. Media-only changes use
the same two job types — no new preview machinery. Review-then-apply
remains the only mode (MBQ-34).

**D-015B-4 — Asynchronous pipeline (two-phase, READY-gated —
re-review `4945129824` item 3).** The pipeline is explicitly split so
**no association is ever submitted before the File is `READY`**
(matching the captured official evidence: files are processed
asynchronously; poll `fileStatus` until `READY`, *then* associate the
file with products):
1. **Apply phase 1 (submit):** `stagedUploadsCreate` → HTTP upload →
   `fileCreate`; record the media-binding row with the returned
   **File GID** (`shopify_gid`) and `remote_status='uploaded'`; then
   **finish** (no in-job polling — enqueue-never-inline spirit). **No
   association mutation runs in phase 1.**
2. **Poll (module cron `media_export_status_poll`, 5 min, noupdate):**
   enqueues one `media_export_status_poll` job per store with
   non-terminal media rows; the handler reads `fileStatus`/
   `Media.status` and updates `remote_status`; `FAILED` →
   `blocked_manual_review` / `binding_conflict` with the remote error
   payload.
3. **On `READY` (phase 2 — association):** associate the File with the
   **product** (recording `shopify_product_media_gid`), then with the
   **variant** where applicable; **reorder** (primary first) only
   **after** association succeeds; and **detach/retire old media only
   after** the new association is proven (D-015B-6). Each step's
   outcome is recorded on the row; the row is terminal only once its
   role's association (and any needed reorder) has succeeded.
Poll jobs are nonce-hashed (repeat-run pattern) and stop enqueueing
when no non-terminal rows exist. Product/variant association is
**never** submitted before `READY`; the packet claims no exception,
and none is taken unless fresh official evidence explicitly proves
pre-`READY` association is supported and that evidence is recorded in
the captures packet.

**D-015B-5 — Retry/idempotency.** No media mutation is `@idempotent`
(captures 2026-07-10 §5 — zero product-write mutations carry it), so:
ambiguous outcomes (timeout on fileCreate/association) → verification
read first (files/media queried by the connector filename +
checksum), adopt-if-found, never blind-retry (RA-014 honored);
the checksum in the registry makes re-export of an unchanged image a
no-op by construction; `operation_scope_key` serializes per template
(same targeting as Task 015). Partial failure inside one template's
media set: per-media sub-results recorded; the job routes on the
worst outcome; already-successful uploads are kept and reconciled by
checksum on the next run (no duplicate uploads — verification read +
APPEND_UUID naming makes duplicates detectable).

**D-015B-6 — Update/replacement behavior (READY-gated,
delete-after-proven).** Replacement order: upload new → **poll until
`READY`** → associate new (product, then variant) → reorder (primary
first) if needed → **only then** detach the old connector-owned
association → **fresh reference check** on the old File →
`fileDelete` the old File **only if** it is proven to carry no other
reference (else detach-only + retain, D-015B-2). The product is never
left imageless by a mid-sequence failure, and a shared/foreign-
referenced File is never deleted; each step's outcome recorded.
Reorder is an async `Job` tracked like D-015B-4.

**D-015B-7 — Interplay with import (no loops).** Task 010B's
merchant-image protection uses checksums of connector **writes into
Odoo**; this task records checksums of connector **exports to
Shopify**. A store with both media import (010B) and media export
(015B) enabled would ping-pong; therefore: media export requires
`price_source_of_truth`-style explicit direction — new settings field
`media_source_of_truth` (Selection `odoo`/`shopify`, **no default —
required before first media export**; readiness-style hold
`odoo_validation_configuration` when unset). Export runs only under
`odoo`; Task 010B image refresh (`shopify_fields` mode) runs only
under `shopify` (010B packet cross-referenced; its media refresh
checks this field when the export module is installed). Flagged as
the one cross-module coordination rule this packet adds.

## 4. Store settings added

`media_source_of_truth` (Selection odoo/shopify, no default) — via
the settings seam; consumed per D-015B-7.

## 5. Tests (exact files)

`test_media_binding_model.py` (schema/uniqueness/ACL — **distinct
`shopify_gid` File GID vs `shopify_product_media_gid` Product Media
GID**; read-only for auditor/operator, reviewer confirm-path, admin
rwc, no unlink);
`test_media_export_guard.py` (foreign media never touched — including
the delete/detach/reorder code paths; removal only when enumerated +
confirmed; **`fileDelete` runs only after a fresh reference/association
check proves no other reference — a connector-created File reused on a
second product is RETAINED (detach-only)**; preview media section
completeness; source guards: `productCreateMedia`/`productDeleteMedia`
strings absent, `fileDelete` call sites reachable only through the
registry filter **and** the reference-check);
`test_media_export_pipeline.py` (**two-phase: no association mutation
before `READY`**; staged-upload → fileCreate (records File GID) →
poll → associate product (records Product Media GID) → associate
variant → reorder; replacement order leaves-no-imageless-gap and
deletes the old File only after the new association is proven; checksum
no-op; verification-read adoption on ambiguous outcome — never blind
retry; per-media partial-failure routing);
`test_media_export_async_poll.py` (poll cron enqueue conditions;
UPLOADED/PROCESSING/READY/FAILED transitions; FAILED → manual review
with payload; **READY-gated association: product then variant, never
before READY**; nonce payload_hash);
`test_media_source_of_truth.py` (unset → configuration hold; odoo vs
shopify gating both directions incl. the 010B interplay contract).

## 6. Gate criteria (15-pattern, abbreviated)

1 Task 015 merged runtime-green (preview machinery + module exist);
2–3 exact names ✅(§3); 4 files ✅(§9); 5 checksum/naming/idempotency
mechanics fixed ✅(D-015B-5); 6 no inventory/order scope ✅; 7 no
publishing/gallery/video ✅; 8 no UI/webhook/OAuth ✅; 9 tests
✅(§5); 10 rollback ✅(§7); 11 live validation required (§7 —
mutation task); 12 gate-act reconfirmation; 13 the flagged calls
explicit: `media_source_of_truth` coordination rule (D-015B-7),
connector-owned-only deletion boundary + fresh-reference check
(D-015B-2), and the File-GID vs Product-Media-GID identity split
(D-015B-1); 14 two-phase READY-gated pipeline + poll cadence explicit
✅(D-015B-4); 15 foreign-media protection + retain-if-not-exclusive
explicit ✅(D-015B-2).

## 7. Odoo.sh + live validation / rollback

Odoo.sh: full suites green (verbatim quote). Dev store (mandatory —
mutation task): one add + one replacement + one removal cycle on a
disposable product, including a FAILED-status simulation (bad file)
and proof that a manually-uploaded foreign image survives every
connector operation; redacted evidence in the validation record;
recorded explicit ChatGPT waiver is the only alternative. Rollback:
revert the single PR — the export **code path/capability is removed**;
the additive media-binding table/columns may **remain inert/orphaned**
in the database (a normal code revert does **not** drop them — no
destructive schema cleanup is assumed; any cleanup is a separately
tested migration, never part of the revert); remote media already
exported to Shopify remains (documented manual cleanup list in the
release plan, mirroring the existing Shopify-side rollback posture);
import side and business data untouched.

## 8. Register impacts on acceptance

D-015-7's deferral → superseded (015B is a named, fully-planned MVP
task before UAT/release); DEC-003 "basic image/media update/export
where feasible" → feasibility established + planning-complete;
release plan known-limitations row "no media export" is deleted in
the same revision; UAT gains scenario §UAT-26. Deferred-with-names:
015C gallery/video breadth.

**Lifecycle (LC-1) adoption (re-review `4945129824` item 7):** the
`media_export_status_poll` (and any media-export) `job_type`
`selection_add` `ondelete` uses the LC-1 callable
`_reassign_to_historic_job_type` from the start (LC-1 precedes Task 012
— DEC-030 / lifecycle §7), so no later retrofit is needed.

## 9. Locked final implementation prompt (Task 015B)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE TASK-015B GATE, VERIFIES THE CURRENT BASE SHA,
AND ISSUES THIS PROMPT. (Prerequisite: Task 015 merged runtime-green.)

Implement Task 015B — basic product media/image export — exactly per
docs/07-implementation-plan/task-015b-product-media-export-packet.md
(D-015B-1..7 binding) and captures 2026-07-11 §10. Branch from the
verified current Shopify-connector tip (STOP on drift). One session;
draft PR; stop.

ALLOWED FILES (exhaustive):
  addons/shopify_connector_product_export/models/shopify_connector_product_media_binding.py  (NEW)
  addons/shopify_connector_product_export/models/shopify_connector_media_export_service.py   (NEW — staged upload, fileCreate, association, poll handler, verification read)
  addons/shopify_connector_product_export/models/shopify_connector_product_export_service.py (preview diff media section + apply wiring only)
  addons/shopify_connector_product_export/models/shopify_connector_store_settings.py         (media_source_of_truth only)
  addons/shopify_connector_product_export/models/__init__.py                                 (import lines)
  addons/shopify_connector_product_export/data/shopify_connector_media_poll_cron.xml         (NEW, noupdate=1)
  addons/shopify_connector_product_export/__manifest__.py                                    (data entry + version bump)
  addons/shopify_connector_product_export/security/ir.model.access.csv                       (media-binding rows only)
  addons/shopify_connector_product_export/tests/{test_media_binding_model.py,
    test_media_export_guard.py, test_media_export_pipeline.py,
    test_media_export_async_poll.py, test_media_source_of_truth.py}                          (NEW)
  addons/shopify_connector_product_export/tests/__init__.py                                  (import lines)
  docs/05-qa/task-015b-validation-results.md                                                 (NEW)
  docs/05-qa/architecture-review-log.md                                                      (append one AR row)
  docs/01-research/research-handoff.md                                                       (top entry)
FORBIDDEN: every core/product/sale/inventory/fulfillment file;
productCreateMedia; productDeleteMedia; any deletion/detach/reorder
of media not in the connector registry; gallery/video/3D; publishing;
inventoryQuantities; UI/webhooks/OAuth/CI; adams_base; main; plain dev.

HARD CONSTRAINTS: TWO-PHASE, READY-GATED pipeline —
stagedUploadsCreate -> fileCreate (phase 1: record the File GID in
shopify_gid) -> poll fileStatus/Media.status via the cron-enqueued
poll job until READY (no in-job polling loops) -> ONLY THEN associate
product (record shopify_product_media_gid) -> associate variant ->
reorder -> detach/retire old media; NO association mutation before
READY (no exception unless fresh recorded official evidence proves it
supported); store distinct identities (File GID vs Product Media GID —
never the ambiguous "Media/File GID"); preview -> confirmation ->
apply only (Task 015 machinery reused); foreign media untouched under
all code paths (guard tests); fileDelete ONLY after a fresh
reference/association read proves the connector-owned File has no other
reference — else detach-only + retain the File; replacement order
upload-new-and-associate-before-remove-old; verification read before
any retry of an ambiguous mutation outcome (RA-014) — no blind retry,
no @idempotent assumption; checksum no-op idempotency;
media_source_of_truth required and enforced both directions (unset ->
odoo_validation_configuration hold); no new error classes; concurrency
caveat restated. Odoo.sh green + the §7
dev-store evidence (or recorded explicit ChatGPT waiver). Stop
condition: draft PR "Task 015B: basic product media export
(shopify_connector_product_export)"; gate closes on draft-open; no
other work.
```
