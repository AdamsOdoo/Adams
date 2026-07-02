# DEC-006 — Binding / Deduplication / Identity Strategy (AR-005)

> **Proposed decision record for ChatGPT review.** This is a **recommendation**, not an
> acceptance. It does **not** self-authorize implementation and does **not** change
> DEC-003. If accepted, it resolves **AR-005** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).

## Status

**Proposed for ChatGPT review.** Not accepted. Not implementation-authorizing.

## Date

2026-07-02.

## Scope

**AR-005 only** — Phase 1 **binding/dedup source of truth**, **match-key priority**,
and **per-store uniqueness direction**. Does **not** design the concrete Odoo data
model/fields (deferred to a domain-model sprint), does **not** decide AR-004 (module
boundaries), and does **not** decide AR-007 inventory-identity detail beyond noting
that inventory must key off Shopify inventory/location identity later. Assumes
DEC-004's custom-app/GraphQL premise and DEC-005's orchestration substrate.

## Decision summary

The connector's source of truth for cross-system identity is a **dedicated connector
binding model (or a small family of them), scoped per Shopify store/instance** — not a
reuse of Odoo's `ir.model.data`. Each binding stores the **Shopify GID explicitly** and
the **Odoo model + record reference explicitly**, protected by **uniqueness
constraints** that prevent duplicate bindings per store. Product template, product
variant, customer, order, and inventory/fulfilment identity get **separate handling**
where their shapes differ (e.g. inventory needs `inventory_item_id` + `location_id`,
not just a product GID). Convenience reference fields on business records (e.g. a
Shopify-ID field visible on `product.template`) are allowed only as a **read
convenience**, never as the authoritative record. Matching priority for first-sync and
ongoing dedup is: **existing binding first**, then **SKU/internal reference**, then
**barcode**, then **email/customer keys** where relevant, then **manual match**; a
**name match is advisory only and never automatic**.

## Recommended option

**AR-005 Option E — hybrid: a dedicated binding model as the source of truth, with
selective convenience references** (per
[`ar-005-binding-dedup-framing.md`](../03-architecture/ar-005-binding-dedup-framing.md)
and the RB-14 Part 2 narrowing, which carries **both** Option A (dedicated per-domain)
and Option E as primary candidates — this record picks **E** because it keeps a single
authoritative model per domain while still allowing fast convenience lookups, provided
consistency discipline is enforced).

- **Source of truth:** one or a small family of **dedicated connector binding
  records** — not general business records, not `ir.model.data`.
- **Per-store scoping:** every binding is scoped to a **Shopify instance/store**
  (a `store_id`-equivalent dimension), so the keys are **multi-store-safe even in the
  single-store MVP** (DEC-003's architecture-safe rule).
- **Explicit identity fields:** each binding stores the **Shopify GID** and the
  **Odoo model + record reference** explicitly (not inferred, not looked up
  indirectly).
- **Uniqueness constraints:** per-store uniqueness on `(store, Shopify GID)` and on
  `(store, Odoo model, Odoo record)` — the exact constraint shape (single polymorphic
  table vs one table per domain) is **not decided here**; see *What remains blocked*.
- **Domain-specific handling where shapes differ:** product template/variant,
  customer, order, and inventory/fulfilment identity are **not** forced into one
  undifferentiated shape — inventory identity in particular needs
  `inventory_item_id` + `location_id`, which a plain product-GID binding cannot carry
  alone (full design deferred to AR-007).
- **Convenience references:** a business record **may** carry a read-only convenience
  field (e.g. "Shopify product ID") for fast display/lookup, but it is **never**
  the authoritative source and must stay consistent with the binding record (single
  source of truth discipline).
- **No reliance on `ir.model.data`** as the primary binding/dedup mechanism (see
  *Rejected/deferred options*).
- **No name-only automatic matching**, ever — name is **advisory only**.
- **Match-key priority:** existing binding → SKU/internal reference → barcode →
  email/customer keys (customers) → manual match. Ambiguous matches route to
  **manual review**, never an automatic guess.

## Rejected / deferred options

| Option | Disposition | Why |
| --- | --- | --- |
| **C — Reuse `ir.model.data` as the PRIMARY per-store binding/dedup mechanism** | **Rejected as primary** (proposed; see `rejected-approaches-log.md`) | `[Official source-code fact]` it has `UniqueIndex('(module, name)')` and is genuinely designed for third-party data sync **in principle** — but it has **no per-store/store-dimension column**, **no binding-status/audit fields** (who/when/which key matched), and its `module`/`noupdate` semantics are tied to **module-data lifecycle**, not runtime per-store binding |
| **D — Shopify-ID fields directly on Odoo records, as the sole mechanism** | **Rejected as sole mechanism**; kept as an optional convenience reference alongside the binding model | One record, many future stores → many IDs with no natural home; no audit trail; no clean deleted/recreated handling |
| **Name-only automatic matching** | **Rejected outright** | Directly contradicts DEC-003's mandatory "no automatic name-only matching" rule and the duplicate-prevention preview requirement; no evidence supports it as safe |
| **B — Generic single polymorphic binding table** | **Kept viable, not chosen as the sole shape** | Still must carry per-location inventory identity and a store dimension; whether Phase 1 uses one polymorphic table or one table per domain is a **schema-shape** question left to the domain-model sprint, not foreclosed here |

## Evidence used

Dated **2026-07-01** (RB-14 Part 2 source-code verification); no new fetch needed this
sprint (see
[`ar002-ar003-ar005-evidence-refresh.md`](../03-architecture/ar002-ar003-ar005-evidence-refresh.md)).

- `[Official source-code fact]` `ir.model.data` (`IrModelData`, `odoo/addons/base/models/ir_model.py`,
  19.0): fields `name/complete_name/model/module/res_id/noupdate/reference`;
  **`UniqueIndex('(module, name)')`**; docstring endorses **both** third-party
  data-sync **and** module-data-origin tracking; **`_allow_sudo_commands = False`**. No
  per-store column; no audit/status fields.
- `[Official source-code fact]` `sudo()` (`odoo/orm/models.py`, 19.0): "simply bypasses
  access rights checks" and "could cause data access to cross the boundaries of record
  rules" — per-store isolation must not be implemented by routing writes through
  `sudo()`; an explicit store dimension + record rules is the safer path.
- `[Official fact]` GIDs "uniquely identify" an object, but **permanence is not
  asserted** anywhere in the fetched Shopify docs — the binding must not assume GID
  stability and must handle deleted/recreated Shopify records defensively (mark
  stale, do not silently recreate or hijack).
- `[Official fact]`/`[Official limitation]` the `@idempotent` directive covers a
  **fixed list of 17 mutations** with a **24-hour** server-side dedup TTL; **no
  general/all-mutation idempotency** exists — the binding must carry
  **connector-designed idempotency keys** for everything outside that list (feeds
  AR-006, not decided here).
- `[Official limitation]` `productSet` reconciles list fields by **deleting omitted
  entries** — a wrong or missing binding turns a controlled export/update into
  **data loss**, making the binding a correctness requirement, not a convenience.
- `[Competitor demonstrated]` TeqStars binds via a dedicated **Listing/Listing Item**
  model, matching on **SKU/Barcode**; VentorTech matches by **SKU/barcode** (products)
  and **email/name/phone** (customers) before create, with manual mapping; Emipro
  dedups customers by **email** and blocks re-export via stored Shopify references —
  competitor evidence corroborating a dedicated-model + SKU/barcode/email match-key
  pattern, an **input**, not a fact.

## Risks

1. **Schema-shape mistake** — either over-fragmenting into too many per-domain tables
   (maintenance sprawl) or over-generalizing into one table that loses domain
   nuance (especially inventory's `inventory_item_id`+`location_id` shape). This
   record intentionally leaves the exact shape to the domain-model sprint to avoid
   guessing it here.
2. **Deleted/recreated Shopify records** — without disciplined stale-binding
   handling, a recreated "same" SKU could silently hijack or duplicate an existing
   binding.
3. **Convenience-reference drift** — if a business-record convenience field and the
   binding record disagree, "single source of truth" breaks down in practice unless
   consistency is actively enforced.
4. **Ambiguous first-sync matches mishandled** — if ambiguity resolution is rushed,
   duplicate records are created (the market's classic connector defect).
5. **Per-store isolation implemented incorrectly** (e.g. via `sudo()` or an implicit
   assumption) would defeat the multi-store-safety goal DEC-003 requires even in a
   single-store MVP.

## Mitigations

1. Defer the exact table/field shape to a dedicated **domain-model sprint** (see *What
   remains blocked*) rather than guessing it under this decision-prep sprint's
   non-goals.
2. Require every binding to carry **audit fields** (matched-by, matched-at, source
   strategy, match key used) and a **status** (active/stale/manually-overridden) so
   deleted/recreated handling and auditability are structural, not bolted on.
3. If a convenience reference is used, treat it as a **read cache only**, updated
   from the binding record, never written independently — a design rule for
   implementation planning, not a schema decision here.
4. Enforce **duplicate-prevention preview** (no blind create) and **ambiguous → manual
   review** as hard requirements (already DEC-003-mandatory; this record reaffirms
   them as the AR-005 mechanism).
5. Enforce per-store isolation via **explicit store scoping + record rules**, never
   `sudo()`-based bypass, in every binding read/write path.

## UX implications

- A **matching wizard** lets the operator choose the first-sync source strategy
  (Shopify-source / Odoo-source / both-match-first) and review SKU/barcode matches,
  resolving ambiguous matches manually.
- A **duplicate-prevention preview/diff** ("will create N, link M, N ambiguous")
  before any create/bind action — no blind create.
- **Manual match override** with a visible audit trail (who/when/which key).
- **Stale/recreated bindings surface as review items**, not silent duplicates.
- Each bound record shows its **Shopify link + last matched** status, reinforcing
  DEC-005's honest-freshness principle.

## Security implications

- Per-store isolation is enforced through **explicit store scoping + record rules**,
  never through `sudo()` — a shared rule with DEC-004 (credential access) and DEC-005
  (job-record scoping).
- Binding writes should be access-controlled consistently with the credential/scope
  model DEC-004 establishes.

## Data-safety implications

- The binding is **authoritative over volatile keys** — if a SKU/barcode changes
  after binding, the binding (not the key) remains authoritative, with the key
  change detected/reconciled rather than silently breaking the link.
- **No name-only automatic matching**, ever.
- **Deleted Shopify records:** a binding pointing at a deleted record is marked
  stale, not silently dropped or recreated.
- **Recreated Shopify records:** a new Shopify ID for a "same" SKU must not silently
  duplicate or hijack an existing binding — it requires review.
- The binding is the natural home for **connector-designed idempotency keys** needed
  beyond the 17-mutation `@idempotent` surface (ties to AR-006, not decided here).

## Performance implications

- Bindings need efficient indexed lookup by `(store, Shopify GID)` and
  `(store, Odoo model, Odoo record)` to avoid N+1 lookups during backfills,
  reconciliation, and webhook processing (DEC-005).
- Domain-specific shapes (e.g. inventory's per-location identity) must not force
  expensive joins across a generic table at reconciliation scale — a factor for the
  domain-model sprint to weigh when choosing table shape.

## What this unlocks

- A **domain-model sprint** can now design concrete binding fields/tables against a
  settled direction: dedicated/hybrid, per-store-scoped, GID-explicit,
  audit-carrying, no `ir.model.data`-as-primary, no name-only auto-match.
- AR-006 (idempotency keys), AR-007 (inventory identity), and AR-008
  (order/fulfilment linkage) can proceed assuming a binding substrate exists, instead
  of framing against an open reuse-vs-dedicated fork.
- DEC-004's `productSet` preview/diff mechanism has a concrete binding to key its
  diff off of.

## What remains blocked

- **Exact schema/fields** — one polymorphic binding table vs one table per domain,
  precise column list, and constraint DDL — deferred to the domain-model sprint.
- **AR-004 module boundaries** — where the binding model(s) live in the connector's
  addon layering — not decided here.
- **AR-007 inventory-identity detail** beyond noting it must key off Shopify
  inventory-item/location identity later.
- **AR-006 idempotency-key taxonomy** beyond noting the binding is where
  connector-designed keys live.
- **All implementation** — no code, no Odoo module, until ChatGPT opens the
  implementation gate.

## Revisit triggers

- Shopify officially asserts GID permanence/non-reuse (would simplify, not reverse,
  deleted/recreated handling design).
- Official Odoo evidence that `ir.model.data` gains a per-store/audit-capable shape
  (no realistic path is known; would require core changes) — absent that, Option C
  stays rejected as primary.
- A confirmed multi-store requirement lands sooner than expected — still compatible
  with this decision's per-store scoping; would accelerate, not change, the direction.

## No implementation authorized

**No implementation is authorized by this decision record until ChatGPT accepts it.**
This record does not create code, an Odoo module, or any file outside
`docs/03-architecture/**` and `docs/04-decisions/**`. The no-code gate
(`CLAUDE.md` §4–§5) remains in force.
