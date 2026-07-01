# AR-005 — Binding, Deduplication & Identity Strategy (Decision Framing)

> **RB-14 Architecture Preparation — Part 1.** This document **frames** the AR-005
> decision; it **does not decide it.** No binding model, data model, match-key set, or
> deduplication mechanism is chosen. AR-005 stays **[Not decided] / Evidence pending**
> in [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).
>
> **Classification:** `[Official fact]` · `[Official limitation]` ·
> `[Competitor demonstrated]` · `[Competitor claim]` · `[Inference]` ·
> `[Recommendation]` · `[Open question]` · `[Decision — existing]` · `[Not decided]`.

## Decision question

**How does the connector identify, bind, and de-duplicate records across Shopify and
Odoo so that nothing is duplicated, double-written, or mis-matched — now and as
multi-store arrives later?** Concretely:

1. **Binding model:** where and how a Shopify record (product/variant/inventory/order/
   customer) is linked to its Odoo counterpart.
2. **Match keys:** which keys drive first-sync matching (SKU / internal reference /
   barcode / email) and how ambiguity and manual overrides are handled.
3. **Identity edge cases:** SKU/barcode changes after binding, deleted/recreated
   Shopify records, per-store uniqueness, and auditability.

## Why it matters

- **[Inference]** Binding/identity is the **substrate for correctness**: idempotency
  keys (AR-006), inventory `inventory_item_id`+`location_id` mapping (AR-007), and
  order/fulfilment linkage (AR-008) all rest on it.
- **[Official limitation]** `productSet` is **delete-on-omit** (full-state) — a wrong
  or missing binding turns a controlled export/update into **data loss**, so the
  binding + preview/dry-run is a **correctness** requirement (DEC-003 mandatory
  guardrail).
- **[Inference]** Duplicate records and double-decrement are the **classic connector
  defects** (quality-feedback-loop §5); AR-005 is where they are prevented by design.

## MVP scope inputs from DEC-003 (`[Decision — existing]`)

- **Controlled product import/export/update** with **product/variant matching before
  first sync** and an explicit **first-sync source strategy** (Shopify-source /
  Odoo-source / **both systems already have products — match first**).
- **Binding requirement** between Shopify product/variant IDs and Odoo
  product/template/variant records; **binding created after confirmation**.
- **SKU / internal reference and barcode-based matching**; **ambiguous matches require
  manual review**; **no automatic name-only matching**.
- **Duplicate-prevention preview** before creating records (**no blind create**).
- **Customer import + matching** (deduplicated; email primary, multi-key allowed).
- **Order import idempotency** (webhook-ID dedup; idempotent order intake).
- **Inventory and fulfilment write-back** identity (multi-location-aware; idempotent).
- **Single-store MVP but architecture-safe keys** — **per-store-safe** binding keys
  that must **not** block future multi-store; Webkul's default Company field is **not**
  multi-company evidence (DP-004).

## Shopify official identity facts (`[Official fact]`)

Refreshed 2026-07-01 (see [`rb14-official-source-refresh.md`](./rb14-official-source-refresh.md);
citations in [`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md)).

- **[Official fact]** GraphQL uses **global IDs (GID)** (e.g.
  `gid://shopify/Product/…`); REST numeric IDs must be **converted to the GID** to run
  equivalent operations — the connector must store a **stable Shopify identity** and
  know its format. (shopify.dev/docs/apps/build/graphql/migrate)
- **[Official fact]** Identity chain for catalog/inventory:
  **Product → options/variants; ProductVariant → InventoryItem (1:1) → InventoryLevel
  (one per Location) → Location.** `ProductVariant.sku` is **case-sensitive**.
  (…/objects/Product; …/objects/ProductVariant; …/objects/InventoryItem)
- **[Official fact]** **Orders** and **Customers** are objects with their own IDs;
  orders/customers are **protected customer data** (Level 1/2 + 60-day default window).
  (…/objects/Order; …/launch/protected-customer-data)
- **[Official fact]** Webhooks carry **`X-Shopify-Webhook-Id`** for **deduplication**;
  duplicate deliveries are possible, so processing must be **idempotent**.
  (…/webhooks/verify-deliveries; …/webhooks/best-practices)
- **[Official fact]** `inventorySetQuantities` / `inventoryAdjustQuantities` /
  `refundCreate` require **`@idempotent`** (2026-04) — idempotency keys are part of the
  write path, not just the binding table.
- **[Open question]** Whether Shopify exposes any **client-mutation-id / general
  mutation idempotency** beyond the `@idempotent` directive on specific mutations is
  not confirmed on the fetched pages — relevant to how binding keys and idempotency
  keys relate.

## Odoo identity facts (`[Official fact]` / `[Open question]`)

Citations in [`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md).

- **[Official fact]** An **external identifier (XML ID)** is stored in
  **`ir.model.data`** as `module.name` and refers to a record **independent of its
  database id**; `ir.model.data` stores name/module/model/`res_id`. This is a natural,
  db-id-independent handle. (glossary; data.rst)
- **[Official fact]** **`noupdate`** keeps a record from being overwritten on module
  update but still creates it if missing; **user-created data can be deleted by the
  user**, so binding code must be **defensive** about a binding resolving to a deleted
  record. (data.rst)
- **[Official fact]** Connector fields are added to existing models with **in-place
  `_inherit` (no new `_name`)**; **avoid `_inherits` delegation** (official docs warn
  against it). Batch-safe writes use `@api.model_create_multi`; deletion guarded with
  `@api.ondelete`. (orm.rst)
- **[Official fact]** Connector-relevant Odoo models: **`product.template` /
  `product.product`**, **`res.partner`**, **`sale.order`**, **`stock.quant` /
  `stock.move` / `stock.picking`**, **`stock.location` / warehouse**; **`account.move`**
  only as minimal order-flow evidence (DEC-003 Domain 9), not accounting automation.
- **[Official fact]** **Access rights + record rules** (global=AND / group=OR) enforce
  isolation; relevant to **per-store** binding visibility and a future multi-company
  model. Selective **`index=True`** accelerates binding lookups.
- **[Open question]** Whether **`(module, name)` on `ir.model.data`** is a DB
  uniqueness constraint is **not stated verbatim** in the 19.0 docs — load-bearing for
  reusing `ir.model.data` as the binding store; **verify against the 19.0 codebase**
  before any decision.

## Competitor evidence inputs (`[Competitor demonstrated]` / `[Competitor claim]`)

From Sprint C/C2 (evidence, not facts):

- **[Competitor demonstrated]** **TeqStars** binds via **Listing / Listing Item**
  entities to Odoo products/variants, matches on **"Sync Listings Based On" = SKU /
  Barcode / both**, dedups customers on a **multi-field search** (Name/City/State/
  Country/Zip/Street/Street2/Email/Parent-Id), and **guards product creation**
  (Create-Odoo-Products) — a **dedicated binding model + SKU/barcode match keys +
  first-sync guard**.
- **[Competitor demonstrated]** **VentorTech** matches contacts/products by
  **SKU/barcode** and **email/name/phone (normalized)** before create, ships **manual
  mapping**, and (v2.1.4/2.1.6) **GraphQL idempotency directives** to prevent double
  refunds / duplicate inventory; B2B duplicate-contact prevention (v2.1.6).
- **[Competitor demonstrated]** **Emipro** dedups customers by **email (links, not
  duplicates)**, keys products by **SKU** (plus CSV/XLSX upload-and-map fallback), and
  **blocks re-export** via stored Shopify references ("order already exported").
- **[Competitor claim / demonstrated]** **Webkul** claims **SKU + Barcode "Avoid
  Duplicity"** (config toggle; not shown end-to-end).
- **[Competitor demonstrated]** **Softhealer** writes the **Shopify ID back** onto Odoo
  records (ID write-back implies linking) and uses a **"Needs Shopify Re-Export"** flag;
  **[Competitor claim]** no explicit dedup-key/idempotency statement.
- **[Inference]** Across the market, binding is via **SKU/barcode (products) + email
  (customers) + Shopify-ID write-back**, and **no connector clearly documents
  bound-record-deletion handling** — a whitespace AR-005 must resolve (O-DUP-1).

## Candidate options (framing only — none selected)

> Options for the **where/how** of binding. None is selected; each notes evidence,
> risks, and implications.

### Option A — Dedicated binding tables per domain (per-store)

- **Evidence for:** `[Competitor demonstrated]` TQ's Listing/Listing-Item is a
  dedicated-model pattern; `[Inference]` per-domain tables give explicit keys, indexes,
  per-store uniqueness, audit fields, and clean deleted-binding handling.
- **Evidence against:** `[Inference]` more models/migrations to maintain; must keep
  bindings consistent with the records they point at.
- **Risks:** schema sprawl if over-fragmented; consistency on record deletion.
- **UX / migration / multi-store / dedup implications:** best **per-store uniqueness**
  and **auditability**; cleanest multi-store-safe keys; supports manual match override
  and first-sync conflict handling explicitly.
- **Open questions:** one binding model with a `model`/`res_id` shape vs one table per
  domain (product/customer/order/inventory).

### Option B — Generic single binding table (Shopify GID ↔ model + res_id)

- **Evidence for:** `[Inference]` one model, uniform API, easy to index and audit;
  `[Official fact]` mirrors the `ir.model.data` `(model, res_id)` shape without its
  module-data semantics.
- **Evidence against:** `[Inference]` a generic table can blur domain-specific keys
  (e.g. inventory needs `inventory_item_id`+`location_id`, not just a product GID);
  polymorphic references are less type-safe.
- **Risks:** domain nuances (variants, per-location inventory) forced into a generic
  shape; weaker constraints.
- **UX / migration / multi-store implications:** simple to reason about; per-store
  uniqueness via a `store_id` column; may need domain-specific side tables anyway.
- **Open questions:** can one table carry per-location inventory identity cleanly?

### Option C — Reuse `ir.model.data` external IDs as bindings

- **Evidence for:** `[Official fact]` external IDs are a **db-id-independent** handle
  designed for stable references; no new model.
- **Evidence against:** `[Official fact]` `ir.model.data` is **module-data machinery**
  (`noupdate`, module ownership, reload semantics) not designed as a per-store runtime
  binding store; `[Open question]` `(module,name)` uniqueness unconfirmed; user
  deletion of records/bindings must be handled.
- **Risks:** overloading framework machinery; conflicts with module data lifecycle;
  weak fit for per-store keys and rich audit.
- **UX / migration / multi-store implications:** low build cost but likely **poor
  multi-store fit** and limited audit — an **avoid-candidate**, but **not rejected**
  here (routes through ChatGPT/architecture review, `CLAUDE.md` §10).
- **Open questions:** is any part of `ir.model.data` (e.g. for static config anchors)
  still useful alongside a real binding model?

### Option D — Shopify ID fields directly on Odoo records

- **Evidence for:** `[Competitor demonstrated]` SH/EM/VT store Shopify references on
  records (ID write-back); simplest lookup.
- **Evidence against:** `[Inference]` fields-on-record struggle with **per-store**
  bindings (one record, many stores → many IDs), audit history, and deleted/recreated
  Shopify records; couples identity to business models.
- **Risks:** multi-store dead-end; no natural place for binding metadata (status, last
  matched, source strategy).
- **UX / migration / multi-store implications:** fine for single-store MVP but
  **architecture-unsafe** for the DEC-003 "keys must not block multi-store" rule unless
  combined with a store dimension.
- **Open questions:** could a hybrid keep a convenience field **plus** a real binding
  table as source of truth?

### Option E — Hybrid (dedicated binding model as source of truth + selective
convenience references)

- **Evidence for:** `[Inference]` combines Option A's per-store uniqueness/audit with
  Option D's fast lookups; `[Competitor demonstrated]` TQ (Listing model) + SH (ID
  write-back) each show a half of this.
- **Evidence against:** `[Inference]` must keep the convenience reference and the
  binding table **consistent** (single source of truth discipline).
- **Risks:** duplication of truth if not carefully governed.
- **UX / migration / multi-store implications:** likely the most flexible for
  multi-store future + auditability + performance — **but explicitly not chosen here.**
- **Open questions:** which references are convenience vs authoritative; consistency
  enforcement.

## Identity edge cases the decision must cover (`[Open question]` unless noted)

- **Per-store uniqueness:** bindings must be unique **per store** (DEC-003
  architecture-safe keys) — how is the store dimension modelled?
- **Product template vs variant mapping:** Shopify Product/Variant ↔ Odoo
  `product.template`/`product.product` — which level owns the binding, and how are
  single-variant products handled?
- **SKU/barcode changes after binding:** if a key changes post-binding, the binding
  (not the key) must remain authoritative — how is a key change detected/reconciled?
- **First-sync conflict handling:** Shopify-source / Odoo-source / both-match-first —
  how are conflicts surfaced for **manual review** (no name-only auto-match)?
- **Deleted Shopify records:** a binding pointing at a deleted Shopify record must be
  handled (mark stale, not silently recreate).
- **Recreated Shopify records:** a new Shopify ID for a "same" SKU must not silently
  duplicate or hijack an existing binding.
- **Manual match override:** operators must be able to correct/override a match
  (auditable).
- **Auditability:** who matched what, when, by which key/source strategy — a binding
  record should carry this. **[Recommendation]** treat auditability as a first-class
  requirement.
- **Deleted **Odoo** bindings:** `[Official fact]` users can delete records → binding
  code must be defensive (`@api.ondelete`).

## UX implications (support only — no screens designed)

Grounded in [`../02-product/setup-ux-principles.md`](../02-product/setup-ux-principles.md)
and [`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md):

- **First-sync matching UX:** a **matching wizard** must let the operator pick the
  first-sync source strategy, review **SKU/barcode** matches, and resolve **ambiguous**
  matches manually — **no blind create**, **no name-only auto-match** (DEC-003).
- **Duplicate-prevention preview:** before creating records, show a **preview/diff**
  ("will create N, link M, N ambiguous") so the operator confirms before binding
  (O-DUP-1; TQ Create-Odoo guard; EM re-export block).
- **Destructive-action safeguards:** because `productSet` is delete-on-omit, the export
  path must show a **dry-run diff** keyed off the binding before any full-state write.
- **Manual match override + auditability:** operators can correct a match; the binding
  records **who/when/which key** for trust and support.
- **Deleted/recreated safety:** the UI must surface **stale bindings** and **recreated
  records** as review items, not silently duplicate — protecting first-sync confidence.
- **Honest identity status:** each bound record should show its Shopify link + last
  matched, reinforcing honest freshness (AR-003).

## Required evidence before an AR-005 decision

- **[Open question]** Confirm **`ir.model.data` `(module,name)` uniqueness** and
  runtime-binding suitability against the Odoo 19 codebase.
- **[Open question]** Confirm **GID stability** and whether recreated Shopify records
  always get new GIDs (affects deleted/recreated handling).
- **[Open question]** Confirm whether Shopify offers **general mutation idempotency /
  client-mutation-id** beyond `@idempotent` (affects how binding + idempotency keys
  relate — ties to AR-006).
- **[Open question]** Decide the **per-store store dimension** model (single table with
  `store_id` vs per-store scoping) consistent with future multi-store.
- **[Open question]** Decide **template-vs-variant** binding ownership and inventory
  identity (`inventory_item_id`+`location_id`) shape (ties to AR-007).
- **[Open question]** Decide the **customer** match-key set and normalization (email
  primary; multi-key) and **order** idempotency keying (webhook-ID + order GID).

## Recommended decision criteria (recommendation, not a decision)

- **[Recommendation]** Prefer a model that gives **explicit, documented, per-store-safe
  binding keys** with **auditability** and **safe deleted/recreated handling** —
  because duplicate/double-write defects are the market's classic failure and DEC-003's
  duplicate-prevention is mandatory.
- **[Recommendation]** Require **no name-only auto-matching**, **ambiguous → manual
  review**, and a **duplicate-prevention preview before create/bind** (DEC-003).
- **[Recommendation]** Ensure the binding supports **idempotency keys** and the
  **`productSet` dry-run diff** (AR-002/AR-006 hooks).
- **[Recommendation]** Keep keys **multi-store-safe even in the single-store MVP** so
  the future is not designed out (DEC-003 architecture-safe rule).

> **No decision is made in this document.** AR-005 remains **[Not decided] / Evidence
> pending**. The options, edge cases, criteria, and open questions above are **inputs**
> for a future ChatGPT-approved architecture-decision sprint (`CLAUDE.md` §4–§5;
> RB-14).
