# Task 012 — Order Import: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §15 is NOT usable.**
> **Decision-closure update 2026-07-14 (Task 012 decision-closure session,
> docs-only, no gate/code/live-call):** the companion decision-closure
> [`../03-architecture/task-012-order-import-decision-closure.md`](../03-architecture/task-012-order-import-decision-closure.md)
> finalizes this packet against fresh official Shopify 2026-07 and Odoo 19.0
> sources and **supersedes this packet where they differ**. Three corrections
> are folded in below: **(1) money is stored losslessly as `Char` (exact
> Shopify `Decimal` string), never Odoo `Float`** — Shopify `MoneyV2.amount`
> is *"serialized as a string … arbitrary precision"* (D-012-1 revised);
> **(2) the three order-level connections (`lineItems`, `shippingLines`,
> `discountApplications`) are fully paginated with a bounded cursor loop, not
> rejected at one page** (§4 revised); **(3) the total-check tax-tolerance
> count `K` is derived from the company's actual
> `tax_calculation_rounding_method`, whose Odoo-19 default is `round_globally`**
> (D-012-2 revised). Divergent-currency routing (D-012-3) is confirmed as
> `skipped`-policy with **no** error class (never overloading
> `financial_total_mismatch`).
> **Correction round 2026-07-14 (control-room review `4690680028`, docs-only):**
> (a) **dependencies are now capability-based**, not direct-merge of PR #150/#151
> (revised CORE-R2 Slice-2B integration-staging strategy; CORE-R1 already merged)
> — §2, §15; (b) the total-check is a **canonical single-count ledger**
> `U_ex = M + H + T` with tax-inclusive handling and the **proven** tax bound
> `tol_tax_total = tax_delta_total + 0.5r(S+O)` (round-8; `tax_delta_total = Σ_σ
> tax_delta_bound(σ)` is the **actual** engine raw-base-delta term, carried in full;
> replacing the invalid `K=distinct groups`), with worked
> examples incl. a many-small-lines counterexample — D-012-2; (c) **pagination is
> Option A** (a header query + three independent per-connection cursor page
> queries) with `Order.id`/`updatedAt` verification, cursor-progress + node dedup,
> torn-read → `concurrency_race_conflict`, and no SO write until all connections
> are collected — §4; (d) **GraphQL page sizes are named provisional defaults**
> (no "well under the cap" claim; cost telemetry + dev-store live-read before
> tuning) — §4; (e) **tax-mapping safety**: company match to `order_company_id`,
> active/sale/percent/inclusion checks, fiscal-position validation, ambiguous
> (>1) → hold, first-never-silently — D-012-9; (f) the Decimal/string canonical
> key is the identity layer — `float_compare` is only the boundary to Odoo's
> existing Float `amount`, not a Decimal-precision guarantee — D-012-9; (g) the
> divergent-currency skip seam is **reconsidered and conditional** (recommended:
> a terminal-state-respect guard in the corrected CORE-R2 dispatcher; Task 012
> may need **no** core edit) — D-012-3/§15.
> **Round-3 correction (control-room review `4691067575`, docs-only):**
> (h) the **query contract is the four-query Option-A design everywhere** (no
> single `ORDER_IMPORT_QUERY`/API call) — §4, §15; (i) each product line's
> **exact** pre-tax net is the official `priceAfterAllDiscountsBeforeTaxesSet`
> field — **not** `quantity × discountedUnitPriceSet` (an *approximate* unit
> price) — D-012-2/-8; (j) **refunds/removed quantities are out of scope and fail
> closed** (`currentQuantity == quantity` + `totalPriceSet ==
> currentTotalPriceSet` → policy skip `refunded_or_removed_quantity`) — D-012-2/-8;
> (k) **mandatory per-tax-signature base reconciliation** before any tax tolerance
> (a global `amount_untaxed` match is not sufficient) and the tax bound reframed as
> a **proposed conditional** `tol_tax_total = tax_delta_total + 0.5r(S+O)` (round-8;
> `tax_delta_total` = the actual engine raw-base-delta term, carried in full) with
> its platform-rounding
> premise labelled an inference (fail-closed for undocumented-rounding currencies)
> — D-012-2; (l) the stale single-`execute()` AST guard is replaced by
> **`execute_business` guards** (no result escapes its context) — §6, §15; (m)
> dependencies reference the PR #158 Slice-2B strategy (review
> `4691064435`) — §2, §15.
> **Round-4 correction (control-room review `4691408835`, docs-only):** (n) the
> header query now contains **every current-state field the gates consume**
> (`currentTotalPriceSet`/`currentTotalTaxSet`/`currentShippingPriceSet`/
> `currentTotalAdditionalFeesSet`/`currentTotalDutiesSet`/
> `totalCashRoundingAdjustment`; and `additionalFees` detail — **later removed
> round-6**, the aggregate alone drives the skip) — §4/§15; (o) a fail-closed
> **shipping** refund/removal gate (`isRemoved`, `currentDiscountedPriceSet`) with
> **edge-cursor** pagination for the nullable `ShippingLine.id` — D-012-9/§4.2a;
> (p) **unsupported additional fees** and **cash rounding** are named policy skips,
> and duties route on a **nonzero amount** (not non-null) — D-012-10/§6.0; (q)
> **§6.4a hardened to exact currency-quantized per-signature base equality** (the
> round-3 tolerance withdrawn) with a rigorous `tax_delta_bound` — D-012-2; (r) PR
> #158 is **merged** and the branch is **base-aligned** onto `Shopify-connector`
> `1494b97` — §2.
> **Round-5 correction (control-room review `4691931971`, docs-only):** (s)
> **all three** GraphQL connections use one `edges{ cursor node }` shape (no
> `nodes`-only) — §4/§15; (t) **duty-first** fee/duty precedence so a duty-only
> order reaches `unsupported_duties` — D-012-10/§6.0.3; (u) `AdditionalFee.name`
> is **potentially-PII** (**round-6 goes further: the field is not queried at
> all**) — §6.0.3; (v) the rate-only tax key is replaced by the composite
> `shopify_tax_evidence_key` (rate+title+source+channelLiable+inclusion;
> collision → hold; **round-6 hashes the full untruncated tuple**) — §5.2a/D-012-9;
> (w) the residual/tax-base reconciliation is
> **rebuilt around the actual Odoo 19 tax engine** (`price_include_override` on
> `account.tax`; engine `total_excluded`; price-included via the engine not gross
> subtraction; binary-float honesty; engine-derived `tax_delta_bound`) — D-012-2/§6.2;
> (x) a **nonzero tip fails closed** (`unsupported_tip_tax_treatment`, no untaxed
> Tip line) — D-012-9/§6.0.6.
> **Round-6 correction (control-room review `4692656343`, docs-only):** (a6)
> **`Order.additionalFees` is NOT queried** — the aggregate
> `currentTotalAdditionalFeesSet`/`currentTotalDutiesSet` drives the skip;
> `AdditionalFee` official `id/name/price/taxLines` acknowledged but **no `name`
> requested/stored/logged** (supersedes round-5 (u)) — §4/§6.0.3; (b6) the tax
> identity is the **hash of the FULL untruncated normalized tuple** (evidence
> **fingerprint**), truncated-title-in-key withdrawn, redacted previews are
> display-only (supersedes round-5 (v)) — §5.2a/D-012-9; (c6) **explicit-mapping-only**
> — no automatic rate fallback (a same-rate tax is an operator **suggestion**) —
> D-012-8/§5.2; (d6) **tax auto-create removed from MVP** (no `order_tax_autocreate`)
> — §5.2b/D-012-9; (e6) **data-minimization** — `note`/`tags`/`sourceName`/
> `customAttributes`/`vendor`/`displayName`/`defaultAddress` removed (field-consumption
> matrix) — §4.4; (f6) **Decimal-numeric money equality** (`money_equal`: currency
> match + parsed-Decimal value, not lexical strings) — §3.1a; (g6) terminology
> reconciled to **"no custom connector tax engine; the standard Odoo 19
> `account.tax` engine is authoritative"** — §2. The decision-closure §4–§18 is
> authoritative where it and this packet differ.
> **Round-7 correction (control-room review `4693694894`, docs-only):** (a7)
> `Order.additionalFees` **factual fix** — the 2026-07 field **exposes
> list/pagination/filter arguments** (not an "unbounded no-arg plain list"); the
> MVP still does not query it, reason = **data minimization** — §4/D-012-10; (b7)
> **`Order.edited` fail-closed gate** — queried; `edited==true` →
> `unsupported_order_edit` before any SO write (catches price-only/offsetting
> edits) — D-012-2/§6.0.0; (c7) **nullable `totalTaxSet`** — null normalized to a
> canonical zero MoneyBag (shop+presentment) and `money_equal`'d to non-null
> `currentTotalTaxSet`, else fail closed; the "null OR equals" rule withdrawn —
> D-012-2/§6.0.1 *(the canonical-zero-from-null construction of (c7) is
> **superseded by round-8 (d8)** — a null `totalTaxSet` now fails closed
> `data_shape_schema_mismatch`)*; (d7) **versioned fold-free fingerprint** —
> `SHOPIFY_TAX_FINGERPRINT_VERSION=1`, fixed **SHA-256**, length-prefixed UTF-8
> incl. version, `v1:<hex>`; `title`/`source` **NFC-only** (case+whitespace
> preserved; no folding); migration posture — §5.2a/D-012-9; (e7) **data
> minimization completed** — `DiscountCodeApplication.code`/`ShippingLine.code`/
> `ShippingLine.custom` removed; `ShippingLine.title` retained as bounded merchant
> free text (SO description) — §4.4; (f7) **one supported-tax contract** — leaf
> `amount_type=='percent'` only; group/fixed/division/base-affecting compound
> **fail closed** (`unsupported_tax_structure`), advanced deferred — §5.5/D-012-9;
> (g7) **one global tax tolerance** — `tol_tax_total = Σ_σ tax_delta_bound(σ) +
> 0.5r(S+O)` with `tax_delta_bound(σ)=0` required for every admitted MVP signature
> (else fail closed), so `tax_delta_total ≡ 0` — D-012-2/§6.4a. *(The
> `tax_delta_bound(σ)=0` clause of (g7) is **superseded by round-8** below.)* The
> decision-closure §4–§18 remains authoritative where it and this packet differ.
> (Round-6 (a6)–(g6) and round-4 (n)/round-5 (u)(v) remain as recorded; round-7
> refines them.)
> **Round-8 correction (control-room review `4694311215`, docs-only):** (a8)
> **tax-engine contract honesty** — the claim that `special_mode='total_excluded'`
> is an **exact inverse** for price-included percentage taxes is **withdrawn**
> (Odoo 19 guarantees symmetry only with an unrounded `price_unit` + `round_globally`;
> `price_unit` is `Float`); it is a **seed** → bounded solver → **recompute through
> the actual engine** → read back `raw_total_excluded_currency`/
> `total_excluded_currency`/`raw_base_amount_currency`/`raw_tax_amount_currency`/
> `tax_amount_currency` → **accept only from engine outputs**, else fail closed —
> D-012-2/§6.2; (b8) **actual raw-base delta** — no longer claims `delta_engine==0`;
> records `base_delta(σ)=|base_odoo_raw(σ)−base_src(σ)|` and carries the **linear**
> `tax_delta_bound(σ)=base_delta(σ)×rate/100` (leaf percentages only) in
> `tax_delta_total`; `tol_tax_total = tax_delta_total + 0.5r(S+O)` used consistently,
> **not** reduced to `0.5r(S+O)` — D-012-2/§6.4a; (c8) **`O` corrected** —
> `amount_tax` comes from the SO tax-details computation, so `O` counts leaf-tax
> grouping keys (`round_globally`) / taxed-line×leaf-tax pairs (`round_per_line`),
> **never** invoice repartition rows — D-012-2/§6.4; (d8) **nullable `totalTaxSet`
> fails closed** — the round-7 canonical-zero-from-null construction is **withdrawn**;
> null → **no SO, no binding**, `data_shape_schema_mismatch` (Shopify does not
> document null==zero) — D-012-2/§6.0.1; (e8) **six gate families** — order edits,
> product refund/removal, shipping, duties & additional fees (duty-first), cash
> rounding, tip; §6.0.4 is a pointer into §6.0.3, not a seventh — D-012-2/§6.0. The
> decision-closure §4–§18 remains authoritative where it and this packet differ.
> **Round-9 correction (control-room review `4695589297`, docs-only; against the
> retrieved official Odoo 19.0 source — paths in closure §2):** (a9) **order-level
> financial acceptance** — the guard recomputes the **complete
> `sale.order._compute_amounts` batch** (all priced lines + EPD lines →
> `_add_tax_details_in_base_lines` → `_round_base_lines_tax_details` →
> `_get_tax_totals_summary`) and compares Shopify evidence to the **actual**
> `sale.order.amount_untaxed`/`amount_tax`/`amount_total` + batch tax evidence, never
> to summed line subtotals (which differ under `round_globally`); `O` = distinct
> batch grouping keys — D-012-2/closure §6.2a; (b9) **payment-term posture** — a
> proposed store setting `order_payment_term_id` the importer assigns **explicitly**
> (never inheriting the partner `property_payment_term_id`); readiness blocks when
> unset; a term that would add EPD base lines fails closed
> `odoo_validation_configuration` / `unsupported_early_payment_discount_payment_term`
> (never `financial_total_mismatch`) — D-012-2/closure §5.6; (c9)
> **implementation-exact solver** — the round-8 "bounded solver over currency-valid
> candidates" is replaced by the finite deterministic §6.2b contract on the
> Product-Price-precision grid (`price_unit` is an unrounded `Float`), full-order
> recompute per candidate, fail-closed on exhaustion/no-safe-grid — D-012-2/closure
> §6.2b; (d9) **five-doc consistency** — capability-based prerequisites (no
> "Task 010/011 merged"); ambiguous customer creates **no partial SO/binding** (job
> → `blocked_manual_review`, atomic retry); order `amount_tax` never attributed to
> the line-level compute. The decision-closure §4–§18 remains authoritative where it
> and this packet differ.
> Produced 2026-07-10 by the MVP
> planning-completion session (AR-042 candidate); **revised
> 2026-07-11** by the PR #148 revision session per ChatGPT's
> control-room review (comment `4942966937`, item 6): (a) the
> incorrect Lite/`sale_stock` assumption is removed — `sale_stock` is
> `auto_install: True` in official Odoo 19 (2026-07-11 captures §1,
> `../00-source-materials/odoo19-shopify-official-captures-2026-07-11.md`
> — "captures-11" below) so stock behavior derives from installed
> Odoo apps + explicit operator policy, never from connector edition
> (D-012-7 revised); (b) `order_tax_autocreate` defaults to **False**
> with explicit tax mapping preferred (D-012-9 revised; **the autocreate opt-in
> is fully removed in round-6 — explicit mapping is the only path, §5.2b**); (c) the
> total-check tolerance is now component-based (D-012-2 revised);
> (d) prerequisites (this 2026-07-11 list is **superseded by the 2026-07-14
> capability-based prerequisites** at the top of this header and in §2 —
> CORE-R1 is already merged; PR #150/#151 need not merge directly). **Further revised 2026-07-11 per re-review comment
> `4945129824` (items 4a/4b): the tax mapping is keyed on a canonical
> decimal-string rate (`shopify_rate_key`, never a Float — **superseded round-5
> by the composite `shopify_tax_evidence_key`, §5.2a/D-012-9**) with
> decimal-safe existing-tax matching (D-012-9); and the discount math
> drops the unsound `D_lines × 0.5r` term for a cap-free
> component-sum bound plus exact negative "Shopify Order Discount"
> adjustment lines (D-012-2/D-012-8).**
> **Final-convergence revision 2026-07-11 per comment `4947866018`
> item 3: (i) a residual discount adjustment for a *taxable* source
> line must PRESERVE that line's tax treatment — the negative
> adjustment line inherits the source line's `tax_ids` and price-
> inclusion (or is bucketed per tax signature), never a single
> universal no-tax residual line, because Shopify `TaxLine.priceSet`
> is the tax amount *after* discounts and a no-tax residual would leave
> Odoo's taxable base — and therefore its tax — too high (D-012-2/
> D-012-8); and (ii) the tax-rate unit is pinned exactly — the query
> requests both `rate` (decimal proportion) and `ratePercentage`
> (percentage), the canonical key derives from `ratePercentage`, and
> the connector verifies `rate × 100 == ratePercentage` within fixed
> precision, routing any mismatch/null to a schema/manual hold
> (D-012-9).**
> Original evidence: the 2026-07-10 captures
> (`../00-source-materials/shopify-orders-inventory-fulfillment-product-partner-captures-2026-07-10.md`
> §2/§8/§9 — "captures" below) and the final architecture
> (`../03-architecture/final-mvp-module-and-dependency-architecture.md`
> — "ARCH" below). Shared reliability contracts are per ARCH §5 and are
> not restated. API version posture: 2026-07 (ARCH PD-6).

## 1. Objective and business outcome

Import Shopify orders into confirmed Odoo sales orders — idempotent
(order binding is the sole anchor), financially guarded (total-check),
same-currency-only (DEC-020), evidence-capturing, never silently
mutating an already-imported order. Business outcome: the Lite
edition's core promise — every Shopify sale appears correctly and
recoverably in Odoo — becomes real; Task 014 gains the pickings it
needs.

## 2. Scope / non-goals / dependencies

**Scope:** `shopify_connector_sale` gains the order binding model, the
read-only single-order importer service + `order_import_sync` job
handler, the store-settings order-policy fields, and the
`sale.order.line.shopify_line_item_gid` traceability field. Manifest
depends becomes `['shopify_connector_core', 'shopify_connector_product',
'sale']` (ARCH PD-3).

**Explicit non-goals:** no payment/invoice creation (Domain 9 minimal
rule — `displayFinancialStatus` is stored as a snapshot only); no
refunds/returns (evidence fields exist on Order but are not imported);
**no order edits** (`Order.edited == true` → `unsupported_order_edit`
fail-closed skip, §6.0.0); **no advanced tax structures** (only leaf
`amount_type=='percent'` sale taxes; group/fixed/division/base-affecting
compound fail closed, §5.5); **no early-payment-discount payment terms**
(a store `order_payment_term_id` whose term would add EPD base lines via
`_add_base_lines_for_early_payment_discount` fails closed
`unsupported_early_payment_discount_payment_term`, §5.6 — representing the
discounted-base tax is deferred post-MVP); no fulfillment write-back (Task 014); no inventory logic (Task 013 —
SO confirmation's standard Odoo reservation is not connector inventory
logic); no presentment-currency orders; **no custom connector tax
engine — the standard Odoo 19 `account.tax` engine is authoritative for
excluded base, included total, tax breakdown, group and repartition
behaviour** (no manual tax override, no custom tax calculation, no
invoice/accounting automation; §5); no enumeration/scan triggers (Area 6);
no webhooks; no UI
beyond nothing (Error-Center extensions are UI-phase scope); no
`read_all_orders` (60-day default window is the MVP posture — historic
backfill is a documented setup limitation until a separately-approved
scope request).

**Dependency prerequisites — CAPABILITY-BASED (REVISED 2026-07-14, review
`4690680028`; supersedes the earlier direct-merge list):** Tasks 002/003
(client) and 006C (dispatch) merged [facts]; **plus the capabilities below in
`Shopify-connector`, delivered via the MERGED CORE-R2 Slice-2B
integration-staging strategy (PR #158, review `4691064435`; merged at
`Shopify-connector` tip `1494b97`)** — the current
unprotected PR #150/#151 heads are **not** directly mergeable; that strategy
stages #150/#151 heads, migrates their product/customer Shopify calls to
`execute_business`, closes the public generic `execute`, passes integrated suites
+ multi-worker evidence, then lands **one** controlled integration PR carrying the
net product + customer domains + both call-site migrations + the core `execute`
closure; #150/#151 then close as merged or subsumed (never individually merged):
(1) **SRR-03 CLOSED** (disconnect quiescence runtime-green — the register forbids
merging/enabling/live-validating any Shopify-calling domain handler until then);
(2) **protected/guarded product import + complete product/variant bindings**
present (order-line resolution; product Shopify calls guarded);
(3) **protected/guarded customer import + indexed normalized-email matching**
present (D-012-5 guest path reuses the indexed lookup at volume);
(4) **no unguarded product/customer Shopify call remains**;
(5) **Task LC-1 merged + DEC-030 accepted**.
**CORE-R1 is already merged (satisfied historical foundation, not a pending
dependency).** Gate prerequisites (ChatGPT acts): acceptance of this packet + the
decision-closure, the order-domain gate act, prompt issuance.

## 3. Decision closures (D-012-1 … D-012-12) — each Proposed, carried verbatim into the locked prompt

**D-012-1 — Order binding (MBQ-55 order portion; OP-14).** Model
`shopify.connector.order.binding` (class
`ShopifyConnectorOrderBinding`, file
`shopify_connector_order_binding.py`), `_name` + `_inherit
'shopify.connector.binding.mixin'`. New fields: `sale_order_id`
(Many2one `sale.order`, required, index, `ondelete='restrict'`);
readonly snapshots `shopify_order_name` (Char),
`shopify_legacy_resource_id` (Char — UnsignedInt64 must not use Odoo's
int4 Integer), `shopify_processed_at` (Datetime),
`shopify_updated_at_snapshot` (Datetime),
`shopify_currency_code`/`shopify_presentment_currency_code` (Char),
`shopify_taxes_included` (Boolean),
`shopify_financial_status_snapshot`/`shopify_fulfillment_status_snapshot`
(Char — raw enum strings; `displayFinancialStatus` is nullable, store
empty as False), `shopify_cancelled_at` (Datetime),
`shopify_cancel_reason` (Char); **money snapshots are `Char` holding the
exact Shopify decimal string, NEVER `Float` — REVISED 2026-07-14 (closure
§3.1): Shopify `MoneyV2.amount` is the `Decimal!` scalar "serialized as a
string" with arbitrary precision, so `Float` is lossy; guard math parses
these Char strings with `decimal.Decimal`.** Money fields:
`shopify_order_total_amount` (Char — `totalPriceSet.shopMoney.amount`),
`shopify_order_total_presentment` (Char —
`totalPriceSet.presentmentMoney.amount`, DEC-020 dual-currency audit),
`shopify_subtotal_amount`/`shopify_total_tax_amount`/
`shopify_total_discounts_amount`/`shopify_total_shipping_amount`/
`shopify_total_tip_amount` (Char, lossless component evidence);
`customer_resolution` (Selection: existing_binding / email_match /
created / guest_email_match / guest_created / fallback / manual —
readonly; the fallback audit marker), `shopify_last_imported_at`
(Datetime), `shopify_last_evidence_refresh_at` (Datetime). The binding
stores **no** customer PII (name/email/phone/address live on `res.partner`,
Task 011 — privacy boundary). Constraints (models.Constraint):
`UNIQUE(store_id, shopify_gid)` + `UNIQUE(store_id, sale_order_id)`.
`match_key` used: `existing_binding`/`manual` only — orders are never
auto-matched to pre-existing sale orders; import always creates.
**Order line identity:** no line binding model (DEC-013 bound
preserved); `sale.order.line` gains one indexed readonly Char
`shopify_line_item_gid` via `_inherit` — a traceability/audit field,
explicitly not a binding model (flagged per ARCH §3).

**D-012-2 — Total-check guard mechanics (MBQ-56; OP-16) — REVISED
2026-07-11 (review item 6c): component-based, currency-precision-
derived, strict cap.** Exact Shopify total field:
**`Order.totalPriceSet.shopMoney.amount`** (captures §2 — non-null,
includes taxes and discounts, before returns). After building the
full SO inside the savepoint, the guard evaluates **three component
checks plus the total check** — a real mismatch in one component can
no longer hide under aggregate slack:

**ORDER-LEVEL ACCEPTANCE (round-9, review `4695589297` item 1; closure §6.2a) —
authoritative.** The guard accepts or rejects **only after the complete
`sale.order._compute_amounts` batch is recomputed** (all priced lines + any
early-payment-discount base lines → `AccountTax._add_tax_details_in_base_lines` →
`_round_base_lines_tax_details` → `_get_tax_totals_summary`; official Odoo 19
`sale_order.py` L512–528). The comparison surface is the **actual order values**
`sale.order.amount_untaxed`/`amount_tax`/`amount_total` plus the batch tax evidence
— **never** summed line-level `price_subtotal`/`price_tax` (which differ from the
order totals under `round_globally`, `account_tax.py` L1896–1927). Line-level
`sale.order.line._compute_amount` produces one line's figures only; a candidate that
passes in isolation is **rejected** if the order-level recompute breaches any bound.
`O` is counted from the batch grouping keys `{tax, currency, is_refund,
is_reverse_charge, price_include, computation_key}` (`account_tax.py` L1907–1920),
never invoice repartition rows.

**PAYMENT TERM (round-9, review `4695589297` item 2; closure §5.6) — the store
setting `order_payment_term_id` is assigned EXPLICITLY (never inheriting
`partner_id.property_payment_term_id`, which `_compute_payment_term_id` would
otherwise do, `sale_order.py` L430–434); readiness blocks import when it is unset;
a term that would add EPD base lines through
`_add_base_lines_for_early_payment_discount` (`sale_order.py` L530–573, fires on
`early_discount and early_pay_discount_computation=='mixed' and discount_percentage`
— those ± lines alter `amount_tax`) FAILS CLOSED `odoo_validation_configuration` /
`unsupported_early_payment_discount_payment_term` BEFORE any SO/binding, NEVER
`financial_total_mismatch`.**

**PRICE-INCLUDED SOLVER (round-9, review `4695589297` item 3; closure §6.2b) — the
finite deterministic contract:** because `price_unit` is `fields.Float` with only
`min_display_digits='Product Price'` (`sale_order_line.py` L177–181, no storage
grid), candidates are drawn from the finite Product-Price-precision grid (≤ `2K+1`,
non-decreasing `|u−u₀|`, `u₀−d` before `u₀+d`, lower-wins tie-break), each recomputed
through the actual engine AND the full-order `_compute_amounts` batch for acceptance;
**fail closed** on grid exhaustion (`K`) or when the order cannot be represented on
the grid (narrowed MVP scope). The grid is **never** assumed equal to currency
rounding.

**REBUILT 2026-07-14 (review `4690680028` items 2 & 3, then review `4691067575`
items 2 & 3) — the canonical single-count ledger, per-tax-signature base
reconciliation, and conditional tax bound live in closure §6, authoritative.**
**Pre-creation gates (closure §6.0 — SIX fail-closed gate families, reviews
`4691408835` + `4691931971` + `4693694894` + `4694311215`; §6.0.4 is a pointer into
the duty-first §6.0.3 gate, not a seventh):** before any SO write — (0) **`Order.edited ==
true` → `unsupported_order_edit`** (order edits out of MVP; evaluated **first**;
quantity/total checks alone miss price-only and offsetting edits — review
`4693694894` item 2; evidence = order GID + `edited=true` + `updatedAt` only, no
edit-history reconstruction); (1) every line `currentQuantity == quantity` **and**
`money_equal(totalPriceSet, currentTotalPriceSet)` **and** the price⇄current-tax
rule — when `totalTaxSet` is **non-null**, `money_equal(totalTaxSet,
currentTotalTaxSet)`; when `totalTaxSet` is **null**, **fail closed — no SO, no
binding —** `data_shape_schema_mismatch` (Shopify documents `totalTaxSet` as
nullable but **not** that null means zero, so the round-7 canonical-zero-from-null
construction is **withdrawn** — review `4694311215` item 3; evidence = order GID +
`currentTotalTaxSet` amount/currency + absence of original tax; a later
evidence-backed decision may normalize null→zero, §18)
(`refunded_or_removed_quantity` for the non-null unequal case); (2) every shipping line
`isRemoved == false` and `currentDiscountedPriceSet == discountedPriceSet` (both
currencies) and consistent with `currentShippingPriceSet`
(`refunded_or_removed_shipping`); (3) **duty-first precedence** — if
`currentTotalDutiesSet != 0` → `unsupported_duties` (reachable for duty-only
orders; record whether fees also nonzero, no composition inferred, no subtraction
of duties from fees); **else if** `currentTotalAdditionalFeesSet != 0` →
`unsupported_additional_fees` (**the aggregate drives the skip**; review
`4692656343` item 1: Task 012 does **not** query `Order.additionalFees` and does
**not** request/store/log `AdditionalFee.name` — evidence is reason + aggregate
amount + currency only; `AdditionalFee.id:ID!` is acknowledged as the post-MVP
identifier); (4) **nonzero** `totalCashRoundingAdjustment` payment/refund
(`unsupported_cash_rounding` — its relation to `totalPriceSet` is undocumented,
fail closed); (5) **nonzero** `totalTipReceivedSet` → `unsupported_tip_tax_treatment`
(tip tax treatment undocumented; **no untaxed Tip line**, so `T = 0` in the ledger).
Each is a terminal policy **skip**, no SO/binding, **never**
`financial_total_mismatch`. **All money equality/zero tests above use the §3.1a
`money_equal`/`is_zero` rule — currency-code match + parsed-`Decimal` numeric
comparison (never lexical string equality), so `10.0` and `10.00` are equal and a
currency mismatch never is** (review `4692656343` item 6). For an eligible
order, in `Decimal` on `shopMoney` (no intermediate rounding until the single
write boundary, closure §6.2): product net **`M = Σ_i
priceAfterAllDiscountsBeforeTaxesSet_i.shopMoney`** — the **exact** per-line total
*"after all discounts… excluding refunded and removed quantities… doesn't include
taxes"* [Fact — official], **always pre-tax and current-quantity**, so **no `OC`
subtraction and no `quantity × discountedUnitPriceSet` assumption** (the round-2
approximate-unit-price construction is withdrawn; `discountedUnitPriceSet` is
*"approximate"* and excludes order-level discounts — display/audit only). Shipping
net **`H = Σ_s (discountedPriceSet_s − shipping taxLines_s if taxesIncluded else
0)`** (exact discounted shipping, tax backed out once only when inclusive). Tips
**`T = 0`** for every imported order — a **nonzero** tip is a fail-closed skip
`unsupported_tip_tax_treatment` (§6.0.6; tip tax treatment is undocumented, so
relying on the rounding tolerance would let a small taxed tip pass silently — the
round-4 untaxed-Tip-line posture is **withdrawn**, review `4691931971` item 6).

1. **Lines:** `|amount_untaxed − U_ex| ≤ tol_lines`, where **`U_ex = M + H + T`
   is always tax-exclusive** (`T = 0`; every term reported/derived pre-tax; **no
   global `G − totalTaxSet` back-out**). `tol_lines = 0.5 r L` (tax-excl) or
   `0.5 r (L + S_ship)` (tax-incl); `L` = Odoo untaxed-contributing lines (product
   + shipping + residual adjustments; **no tip line**). Each product line is
   represented **through the actual Odoo 19 tax engine** (closure §6.2, REBUILT
   review `4691931971` item 5): construct the candidate `sale.order.line`
   (`price_unit`, `discount`, `tax_ids` — **inclusion lives on `account.tax`'s
   `price_include_override`, NOT the SO line**), read the engine's actual
   `total_excluded`/`total_included`/tax breakdown, add a qty-1 residual carrying
   the same tax signature, **recompute through the engine**, and require the engine
   excluded base to reconcile; for tax-included taxes the residual **gross** is
   derived **through the engine** — `special_mode='total_excluded'` is a **seed,
   NOT an exact inverse** (Odoo 19 guarantees symmetry only with an unrounded
   `price_unit` + `round_globally`; `price_unit` is `Float` — review `4694311215`
   item 1), so the **finite deterministic §6.2b solver** over the
   Product-Price-precision grid recomputes through the actual engine and **accepts
   only from the engine readback** (`raw_total_excluded_currency`/`total_excluded_currency`/
   `raw_base_amount_currency`/`raw_tax_amount_currency`/`tax_amount_currency`),
   **never** by gross/pre-tax subtraction; **no valid candidate → fail closed**.
   Money fields are binary `float`, so the residual is **not** assumed to store a
   Decimal exactly — it is chosen so the engine result reconciles, read back and
   re-checked (closure §6.2).
2. **Per-tax-signature base — engine raw excluded base, quantized (closure §6.4a) —
   BEFORE any tax tolerance:** for each signature (the hashed `shopify_tax_evidence_key`
   fingerprint, §5.2a) require `res.currency.round(base_src(σ)) == res.currency.round(base_odoo_raw(σ))`,
   where `base_odoo_raw(σ)` is the **tax engine's returned `raw_base_amount_currency`**
   — **not** a hand `price_unit×qty×(1−discount)` formula and **not** the displayed
   `amount_untaxed`. A **global `amount_untaxed` match is NOT sufficient**; any
   nonzero quantized difference (a **full minor-unit** base error) →
   `financial_total_mismatch`. **Currency-quantized equality is necessary but not a
   proof of exact pre-rounding equality** — the **actual** raw residue
   `base_delta(σ) = |base_odoo_raw(σ) − base_src(σ)|` is **recorded**, and the tax
   check carries its linear leaf-percent impact `tax_delta_bound(σ) =
   base_delta(σ)×rate/100`, **not an assumed zero** (review `4694311215` items 1–2).
3. **Taxes (one global formula — reviews `4693694894` item 7, `4694311215` items
   1–2):** `|amount_tax − totalTaxSet.shopMoney| ≤ tol_tax_total`, where
   **`tol_tax_total = tax_delta_total + 0.5r(S + O)`** and **`tax_delta_total = Σ_σ
   tax_delta_bound(σ)`**. `tax_delta_bound(σ) = base_delta(σ)×rate/100` is the
   **actual** engine-derived raw-base-delta term (valid because MVP taxes are
   independent **leaf percentages**, §5.5 — never applied to a deferred complex
   structure); it is **not assumed zero**, and `tax_odoo(σ)` is compared using the
   engine's **actual `tax_amount_currency`** readback. It is `0` only when the raw
   base matches exactly (the clean 2-decimal case). A signature for which the §6.2b
   solver finds **no** grid candidate satisfying the base + tax checks
   **fails closed** (never widening the tolerance). The formula carries the
   `tax_delta_total` term **in full** so **no document reduces it to `0.5r(S+O)`
   while a nonzero delta is possible** (the linear `base_delta×rate/100` form is the
   MVP form for leaf percentages; a **non-linear** delta would arise only for a
   deferred group/compound/base-affecting structure, which is held/fails closed,
   §5.5 — the linear form is **never** applied to it). A **proposed conservative**
   rounding bound valid **only** under
   explicit assumptions (bases reconciled at the engine §6.4a; rates match; each
   Shopify/Odoo event rounds within `0.5r`; complete `O`). The **Shopify-event
   rounding premise is
   labelled separately (Inference, not an official guarantee** — the schema does
   not state the convention); undocumented-rounding currencies **fail closed**
   pending authorized dev-store evidence. `S` = Shopify per-line/per-shipping tax
   rounding events; `O` = **sale-order** tax rounding events under the actual
   `tax_calculation_rounding_method` (distinct **leaf-tax grouping keys** under
   `round_globally` [the Odoo-19 default], taxed-line×leaf-tax pairs under
   `round_per_line`) — **never** invoice repartition rows (review `4694311215`
   item 2). **Conditional proof (closure §6.5):** per signature the exact taxes
   differ by `tax_delta_bound(σ)` (leaf-percent × `base_delta`), and each system
   rounds within `0.5r` per event → summing gives `≤ tax_delta_total + 0.5r(S+O) =
   tol_tax_total`. The formula distinguishes the **actual base residue**
   (`tax_delta_bound`), **Shopify rounding** (`0.5r·S`) and **Odoo rounding**
   (`0.5r·O`). The old `K = distinct tax groups` bound **omitted `S`** and
   false-rejects a many-small-line order under `round_globally` (closure Example I).
   It is **not** described as "tight and correct."
4. **Total:** `|amount_total − totalPriceSet.shopMoney| ≤ tol_lines + tol_tax_total`
   (the `tax_delta_total` term is carried **in full** — the actual engine raw-base-
   delta term, `0` only when the raw base matches exactly), with **no** fixed or
   currency-relative cap. A mandatory **ledger self-check**
   requires `|Total_ex − totalPriceSet| ≤ tol_total` where `Total_ex = U_ex +
   totalTaxSet` (closure §6.1-F). A missing/wrong line shifts a subtotal/base far
   beyond `0.5r` and is rejected at the lines/§6.4a/total level.

Any component or total breach → roll back the savepoint (no SO
persists), classify `financial_total_mismatch` (existing class;
CONSERVATIVE_NEVER_SILENT → `failed_retryable`, never auto-retried),
full component breakdown (each Shopify money field, each computed
Odoo amount, each tolerance term) in `job.log.technical_detail` JSON.
The guard is mandatory and permanent; no flag bypasses it; tolerances
are formula-fixed (no per-store tolerance setting exists).
**Mandatory test matrix (review-required):** high line counts (100
lines); a **high-value, many-line discounted order** whose faithful
native-% representation would exceed `0.5r` — **accepted** via the
exact negative **tax-preserving** adjustment line (proving the withdrawn
`D_lines × 0.5r` term is not relied on); a **taxable-line order-level
discount** where the residual line carries the source line's `tax_ids`
so the recomputed Odoo tax still matches `totalTaxSet` — and its no-tax
counterpart on an untaxed line (review item 3: no universal no-tax
residual for taxable lines); a **mixed order** (taxed + untaxed lines,
two different tax rates) whose per-signature residual buckets each
reconcile; a **pathological allocation** spread across many lines (each
line's representation chosen by the faithfulness gate; total exact);
`taxesIncluded` true/false (included- and excluded-tax, residual
adjustment inheriting the same inclusion); line + order discounts;
accumulated small rounding drift inside bounds (accepted); a real
mismatch (missing line / wrong price — **rejected at component level
under the cap-free bound**); an **inconsistent allocation** (a residual
that cannot be attributed to a source line's tax signature) →
**rejected**, never absorbed by broadening tolerance;
zero-decimal (JPY, r=1.0) and three-decimal (BHD, r=0.001) currency
orders (ISO 4217 minor units — captures-11 §12). Shopify-side
three-decimal precision policy is officially undocumented
(captures-11 §11) → one named dev-store empirical check before any
three-decimal-currency store is onboarded (the `tol_tax_total` platform-rounding
premise fails closed until then). **Added 2026-07-14 (review `4691067575`):**
the **exact-line-total** source (`priceAfterAllDiscountsBeforeTaxesSet`) with a
fixture where `discountedUnitPriceSet × quantity ≠` the exact total (code
discount; closure Example J) and an allocation-rounding-remainder residual;
**fail-closed refund/removed fixtures** (fully/partially refunded line, removed
line, mixed eligible/ineligible order → whole order skipped before any SO write,
closure Example K); **per-tax-signature base reconciliation** (equal global
`amount_untaxed` but value shifted taxed↔untaxed or rate↔rate → rejected before
the tax tolerance, closure Example E/§6.4a). **Added earlier (review item 3):** an
**adversarial many-small-lines / one-group / `round_globally` counterexample**
(closure Example I) that the conditional `tol_tax_total = tax_delta_total +
0.5r(S+O)` (here `base_delta=0` so `tax_delta_total=0`) accepts while `K=distinct
groups` would false-reject; **fully
worked tax-inclusive** ordinary and order-discount cases (closure Examples G/H —
product source pre-tax, shipping back-out only); multiple taxes on one line;
multiple distinct percent taxes (round_globally buckets); shipping-tax
rounding; line-level allocation not double-subtracted; order-level allocation
already inside the exact field; shipping discount not double-subtracted; ambiguous
(>1) tax candidate → hold; tax company mismatch → rejected.

**D-012-3 — Divergent-currency routing (DEC-020 residual) + policy
skips.** A divergent order (`presentmentCurrencyCode !=
currencyCode`), detected **before any SO creation**, moves the job to
**`skipped`** (terminal, policy), with message "Automatic import not
supported: divergent presentment currency (DEC-020)" and both currency
codes + both `shopMoney`/`presentmentMoney` total sets captured in the
log payload. **Seam mechanics — RECONSIDERED 2026-07-14 (review
`4690680028` item on JobPolicySkip; closure §10):** reaching terminal
`skipped` from a handler needs core to provide a handler-reachable skip
path (the merged dispatcher unconditionally marks a normally-returning
handler `succeeded`). Two candidate core designs: **(1) RECOMMENDED —
terminal-state-respect guard:** `_invoke_handler` writes `succeeded`
**only if the job is still non-terminal**, so the handler calls the
existing `job._transition_skipped(skip_reason, …)` and returns; no new
class, composes with the CORE-R2 `ShopifyQuiescedError → _transition_skipped`
routing (no collision, distinct `skip_reason`); **(2) `JobPolicySkip`
exception + one `except` branch.** Because **CORE-R2 Slice 2A/2B is itself
correcting the dispatcher**, the exact seam is settled with the CORE-R2 owner
at integration; **if the corrected dispatcher already respects handler-set
terminal states, Task 012 needs NO core edit** (it just calls
`_transition_skipped`) — so the dispatcher edit in §15 is **conditional**.
Either way Task-012 behaviour is identical (terminal `skipped`, no error
class, `skip_reason` label; permitted skips are the closed set (closure §10):
`divergent_presentment_currency`, `unsupported_duties` (**nonzero** amount,
**duty-first precedence**), `test_order_excluded`, `order_pre_cancelled`,
`refunded_or_removed_quantity`, `refunded_or_removed_shipping`,
`unsupported_additional_fees` (only when duties are zero),
`unsupported_cash_rounding`, `unsupported_tip_tax_treatment` (nonzero tip)
(closure §6.0)). Rationale:
an eligibility/policy block is not a
failure — the 16-class error registry stays intact (no 17th class) and DEC-020's
"blocked … before SO creation, independent of the total-check outcome"
is honored. The same routing applies to: orders with a **nonzero**
`currentTotalDutiesSet` amount (not merely non-null — D-012-10),
**nonzero** `currentTotalAdditionalFeesSet`, **nonzero**
`totalCashRoundingAdjustment`, refunded/removed/modified **shipping** (D-012-9),
`test: true` orders when `order_import_include_test` is False (default), and
orders already cancelled at first import (D-012-7). Skipped-by-policy jobs are
visible in the Sync Center (UI packet adds the filter); the persisted
`idempotency_key` (payload_hash = `updatedAt`; verified: the key is
never cleared, incl. terminal states) prevents re-import storms — a
re-enqueue for the same order+`updatedAt` collides; a genuinely
updated order gets a new key and a fresh policy evaluation.

**D-012-4 — Ambiguous customer = pre-creation hold (whole job).**
`sale.order.partner_id` is required (captures §8), so an unresolved
customer cannot yield a partial SO. Path 3 of the accepted three-path
rule is implemented as: ambiguous customer → **no SO created**, job →
`blocked_manual_review` / `ambiguous_match` with the Task 011 §8.2
candidate-evidence JSON in `technical_detail` and full financial
evidence in `payload_snapshot` ("the rest of order import" that
survives a customer hold is the evidence capture, not a partial SO).
Operator resolves the customer in the matching flow (creating the
customer binding), then retries the job, which completes normally.
This interpretation is flagged for explicit ChatGPT confirmation.
**Skip-recovery note (red-team-added, applies to D-012-3):** a
skipped-by-policy job keeps its `idempotency_key`, so a fresh enqueue
for the same order+`updatedAt` collides by design; the operator
recovery path after a policy change (e.g. enabling test-order import)
is Area-6's `action_manual_retry`, whose allowed-from set includes
`skipped` for exactly this reason (requeues the same record — no
create collision).

**D-012-5 — Customer resolution sequence (consumes Task 011 paths).**
(1) `Order.customer` present → resolve via the customer binding:
existing binding → use partner (`customer_resolution =
existing_binding`); no binding → run the Task 011 D1 match sequence on
the embedded customer payload (recall-safe email match → bind /
confident-create → bind / ambiguous → D-012-4 / missing-email →
fall through to (2) using order-level data). (2) **Guest orders**
(`customer` null — captures §2) with non-null `Order.email`: recall-safe
normalized-email partner match via the **Task 011B indexed lookup**
(same semantics, no full scan — 011B is a prerequisite; no binding
row — no Customer GID exists): exactly one active → use
(`guest_email_match`); >1 → D-012-4 hold; none → create person
partner from billing/shipping name + email (`guest_created`, Task 011
§8.3/§8.4 mapping rules).
(3) **Genuinely no PII** (`customer` null AND `email` null):
`customer_fallback_partner_id` (the Posture A field — this task is its
sanctioned first consumer) → used with `customer_resolution =
fallback`; if the fallback is not configured →
`odoo_validation_configuration` (`failed_retryable` — operator sets
the fallback, retries). Archived-only email matches follow Task 011:
`duplicate_risk`, no un-archive.

**D-012-6 — Addresses.** `billingAddress`/`shippingAddress` (nullable
MailingAddress) map to child `res.partner` rows (`type='invoice'` /
`'delivery'`) under the resolved partner, created only when no
existing child (or the partner itself) matches on the normalized tuple
(name, street, street2, city, zip, country, state) — preventing
per-order duplicates; country/state resolution is lookup-only
(Task 011 rule). `partner_invoice_id`/`partner_shipping_id` are then
set explicitly (both stored-editable computes, captures §8 — a direct
write is supported Odoo behavior; `address_get` fallback covers absent
addresses). For fallback-partner orders the children carry the order
name in their `name` for traceability. Existing partners' own fields
are never mutated (Task 011 invariant).

**D-012-7 — Odoo order lifecycle — REVISED 2026-07-11 (review items
6a + 6d): stock behavior from installed apps + explicit operator
policy, never from connector edition.** `date_order = processedAt`
(UTC). **[Fact — captures-11 §1]** `sale_stock` is
`auto_install: True` with `depends: ['sale', 'stock_account']` in
official Odoo 19 — it is present in ANY database where those apps
are installed, **including a Lite-connector database**; on
`action_confirm()` it launches stock rules that create delivery
pickings. The prior claim that "Lite" implies no `sale_stock`/no
pickings is **withdrawn** (it inferred Odoo behavior from connector
packaging); the no-retroactive-pickings assumption is withdrawn with
it (whether and when pickings exist is standard Odoo behavior at
confirmation time, not connector logic). Lite is defined as "no
connector fulfillment write-back module" — packaging proposal §2,
revised the same session.
**Confirmation policy (operator-controlled, explicit):** store-settings
field `order_import_confirmation_policy` (Selection
`quotation`/`confirm`) — **no default**; the field is a required
setup decision: while unset, order import holds
(`odoo_validation_configuration`, `failed_retryable` — operator sets
the policy, retries), and the readiness surface carries a warning.
Setup/wizard copy states the consequence of each choice in plain
words: `confirm` → confirmed SO; **if your Odoo has inventory apps
installed (`sale_stock` present), Odoo will also create delivery
pickings — standard Odoo behavior the operator is opting into**;
`quotation` → draft SO, no stock documents, operator confirms
manually. The connector never suppresses, deletes, or fakes pickings
in either mode. Cancelled-at-import orders → D-012-3 skip.
Cancellation/closure detected on a later evidence refresh: snapshots
update + one job-log note — the SO is **never** auto-cancelled
(DEC-014 J); operator action is linked from the Error Center (UI
phase). `Order.closed`/`closedAt` → snapshot only.

**D-012-8 — Lines, discounts, custom items — REVISED 2026-07-14 (review
`4691067575` item 2): exact line-total source + fail-closed refund gate.**
**Eligibility (closure §6.0, fail closed BEFORE any SO):** each LineItem must
have `currentQuantity == quantity`; any mismatch (and any order where
`totalPriceSet != currentTotalPriceSet`) → policy skip
`refunded_or_removed_quantity`, no SO/binding — refunds/returns/removed
quantities are out of MVP scope; the historical `quantity` is **never** imported
against a current-state total; non-PII evidence (`quantity`/`currentQuantity`,
`total*`/`currentTotal*`) is captured; no refund reconstruction. For an eligible
line: one `sale.order.line`, `product_id` via the **variant binding** (template
binding alone is insufficient); `product_uom_qty = quantity` (`== currentQuantity`
by the gate). The line's **exact pre-tax net is
`priceAfterAllDiscountsBeforeTaxesSet.shopMoney`** (*"after all discounts…
excluding refunded and removed quantities… doesn't include taxes"* — captures §2 /
closure §6.1-A). It is reproduced in Odoo **through the actual Odoo 19 tax engine**
(closure §6.2, REBUILT review `4691931971` item 5): a candidate `sale.order.line`
(`price_unit`, `discount`, `tax_ids` — inclusion lives on the mapped
**`account.tax`'s `price_include_override`**, **NOT** the SO line) is run through
the engine; the residual uses the engine's `total_excluded` (for tax-included, the
residual gross is derived **through the engine**, never by gross/pre-tax
subtraction), is **recomputed through the engine**, and the engine excluded base
is **verified** to reconcile — fail closed if no §6.2b grid residual exists.
Money fields are binary `float`, so no residual is assumed to store a Decimal
exactly. **`quantity × discountedUnitPriceSet` is never assumed** equal to
any total (`discountedUnitPriceSet` is the *"approximate"* unit price excluding
order-level/code discounts — display/audit only). The **order-level/code discount
allocations** (from `discountAllocations`) are used for **tax-signature
attribution and audit only** (not the net amount); the line is represented by the
**faithful-representation rule (D-012-2):** a native `discount %`
(quantized to the Discount precision, 2 dp default) is used **only when** the
resulting Odoo `price_subtotal` reproduces the exact target
`priceAfterAllDiscountsBeforeTaxesSet` for the line to within `0.5r`; when it
cannot (typically high-value lines, where a 2-dp % cannot hit the minor unit), the
remaining **rounding remainder** is carried by an explicit negative **"Shopify
Order Discount"** service line (auto-provisioned per store,
`default_code SHOPIFY-ORDER-DISCOUNT`, `price_unit` = the exact negative residual
= `Odoo price_subtotal − priceAfterAllDiscountsBeforeTaxesSet`) so the SO subtotal
reconciles **exactly to the exact line-total field** rather than relying on
tolerance slack (closure Examples D/J — the residual is a small remainder, not the
whole order discount). **Tax treatment of the residual
line (review item 3, `4947866018`):** the residual line **inherits the
`tax_ids` and price-inclusion of the source line it discounts** — it is
*not* a no-tax line for a taxable source — because Shopify
`TaxLine.priceSet` is the tax amount *after* discounts, so the residual
must reduce the same taxable base Odoo taxes; only genuinely untaxed
source lines produce a no-tax residual. Residuals for lines sharing an
identical tax signature (same `tax_ids` + inclusion) may be combined
into **one negative adjustment line per tax signature/bucket**, with the
per-source-line allocation preserved in the evidence payload; a residual
that cannot be attributed to a source line's tax signature is a
**rejected** (inconsistent) allocation → `financial_total_mismatch`,
never absorbed by widening the tolerance.
`originalUnitPriceSet` and all
allocations preserved in the evidence payload; `shopify_line_item_gid`
set; `name` = LineItem `title` (+ `variantTitle`). **Unmatched product line** → whole-order-hold:
`mapping_missing` → `failed_retryable` (accepted rule) naming the
SKU/GID; binding arrives → retry completes. **Custom line items**
(null `variant` — captures §2 inference, flagged): imported via a
per-store auto-provisioned service product "Shopify Custom Item"
(`default_code SHOPIFY-CUSTOM`), title preserved in the line name —
they cannot block the guard since their price evidence is complete;
null-variant lines whose `sku` matches an Odoo product are still
resolved through the normal SKU path first. **Gift-card lines**
(`isGiftCard`) import as lines on the same rule with a job-log note
(no gift-card accounting). `requiresShipping=false` lines import
normally.

**D-012-9 — Shipping, tips, taxes (MBQ-27 closure; OP-17) — REVISED 2026-07-14
(review `4691067575`: exact shipping back-out + fail-closed tip; review
`4691408835`: shipping refund/removal gate + nullable-id pagination).**
**Shipping eligibility (closure §6.0.2, fail-closed BEFORE any SO):** for every
shipping line require `isRemoved == false` and `currentDiscountedPriceSet ==
discountedPriceSet` (both currencies) and consistency with
`Order.currentShippingPriceSet`; any mismatch → policy skip
`refunded_or_removed_shipping`, no SO/binding (refunded/removed/modified shipping
is out of MVP scope), **never** `financial_total_mismatch`. Pagination uses
`shippingLines{ edges{ cursor node{ id … } } }` because `ShippingLine.id` is
**nullable** — the edge cursor is the mandatory identity, non-null `id` secondary,
a null `id` is never a stable GID (closure §4.2a). For an eligible order: one SO
line per `shippingLines` node, service product "Shopify Shipping"
(auto-provisioned, per store); the **exact pre-tax shipping source** is
`discountedPriceSet.shopMoney` when `taxesIncluded=false` (already pre-tax [Fact —
official]) and `discountedPriceSet − Σ shipping taxLines.priceSet` (backed out
**once**) when `taxesIncluded=true`; its `taxLines` (the shipping **tax
signature**) are mapped per T-B and preserved. **Tips (REVISED 2026-07-14, review
`4691931971` item 6): a nonzero `totalTipReceivedSet` FAILS CLOSED** → skip
`unsupported_tip_tax_treatment`, **no SO, no "Shopify Tip" line** (tip tax
treatment is undocumented; the round-4 untaxed-tip-line + total-self-check posture
is **withdrawn** because a small taxed-tip difference can fall inside the rounding
envelope). Only a zero tip proceeds. Duties: D-012-3 skip. **Taxes — proposed
mechanism T-B ("explicit-mapping-only, under the standard Odoo tax engine + the
guard"), REBUILT 2026-07-14 (review `4691931971` item 4 + `4692656343` items 2/3/4):
hashed tax-evidence fingerprint, explicit mapping only, no auto-create.**
Resolution order for each distinct `TaxLine` on a line/shipping/order tax line:

1. **Explicit mapping — the only automatic resolution path (REBUILT 2026-07-14,
   review `4692656343` items 2 & 4; **versioned + fold-free** per `4693694894`
   item 4):** new model `shopify.connector.tax.mapping` (store_id;
   **`shopify_tax_evidence_key` Char** — a **versioned SHA-256 fingerprint**,
   format **`v1:<sha256 hex>`**, of the FULL normalized evidence tuple
   `(version, ratePercentage, title, source, channelLiable, inclusion)` (§5.2a);
   plus a stored `shopify_tax_fingerprint_version` integer). The identity is
   **fixed**: `SHOPIFY_TAX_FINGERPRINT_VERSION = 1`, algorithm **SHA-256** (not
   "e.g."), **deterministic length-prefixed UTF-8** serialization **including the
   version**. **`title`/`source` are normalized with Unicode NFC ONLY — case and
   whitespace are PRESERVED (no case-folding, no whitespace collapse, no
   truncation)** because Shopify does not define them as case-/whitespace-
   insensitive identifiers; `source` null uses an explicit sentinel distinct from
   empty string; `channelLiable` is tri-state. A rate-only key, any key that
   truncated free text before hashing, **and any case-folded/whitespace-collapsed
   key are withdrawn** (each could collapse genuinely distinct evidence);
   `account_tax_id` M2o `account.tax` required restrict; **UNIQUE(store_id,
   shopify_tax_evidence_key)**; the same `title`/`source`/`channelLiable` are
   queried on line/shipping/order tax lines. Separate **redacted/truncated**
   `title_preview`/`source_preview` display fields exist for the protected operator
   UI only and are **never** part of the identity or ordinary logs. **Migration
   posture:** changing normalization/algorithm requires a **new version** (`v2:`);
   old `v1:` rows stay interpretable and are never silently recomputed; `v1:`/`v2:`
   key spaces cannot collide. A changed evidence tuple hashes to a **new, unmapped
   fingerprint** (held until an operator maps it), never silently reused).
   **Rate-unit pinning +
   canonicalization (review item 4a `4945129824` + item 3
   `4947866018`):** Shopify exposes a tax rate two ways — `TaxLine.rate`
   (a **decimal proportion**, e.g. `0.05`) and `TaxLine.ratePercentage`
   (a **percentage**, e.g. `5.0`). The query requests **both** (§4). The
   **authoritative input is `ratePercentage`**: the connector parses it
   with `decimal.Decimal` (**never** `float`), quantizes to 6 decimal
   places, strips trailing zeros and any trailing separator, and stores
   the result as the key — so `ratePercentage` `5.0`, `5.00`, and `5.000`
   all canonicalize to the single key `"5"`, and `8.375` to `"8.375"`.
   **Cross-check (never accept an unlabelled unit):** the connector
   verifies `rate × 100 == ratePercentage` (both parsed as `Decimal`,
   compared within 6-dp precision) — this rejects the ambiguity where a
   bare `0.05` could mean 0.05 % or 5 %. If `rate` and `ratePercentage`
   disagree beyond precision, or either is null/empty, the tax line
   routes to a **schema/manual hold** (`data_shape_schema_mismatch`) — no
   key is produced from a single unverified field. Admin-maintained (rwc admin, read others, no
   unlink; settings-area UI in a later phase, shell/import until then).
   A mapping hit (same canonical key + `price_include`) resolves
   immediately.
2. **No automatic existing-tax fallback — a rate match is a SUGGESTION only
   (review `4692656343` item 3):** Odoo `account.tax` has **no** Shopify
   `source`/`channelLiable`/`title` fields, so a single same-rate Odoo tax is
   **not** proof of a whole-fingerprint match. The importer therefore **never**
   auto-selects an existing tax by rate. For an **unmapped** fingerprint the
   **readiness surface may present** same-rate, inclusion-compatible `account.tax`
   candidates (filter: `company_id == order_company_id`, `type_tax_use='sale'`,
   `active`, `amount_type='percent'`, `price_include_override` matching
   `Order.taxesIncluded`; `account.tax.amount` compared to the canonical
   `ratePercentage` via `float_compare(..., precision_digits=6)` — the boundary
   comparison to that existing Float, **not** a claim that it preserves Shopify
   Decimal precision) as a **non-binding operator suggestion**, labelled
   *"rate-only suggestion — confirm the jurisdiction/account before mapping."* The
   **operator**, not the importer, chooses; nothing imports until the mapping row
   exists. The **fiscal-position result is still validated** at resolution — after
   Odoo's `fiscal_position.map_tax(...)`, the mapped tax must still satisfy the
   rate/inclusion/company invariants, else the line holds.
   **Company-scope decision (documented):** the mapping model keeps `store_id`
   (no redundant `company_id` column); safety = an `@api.constrains` that
   `account_tax_id.company_id == store_id.order_company_id` at mapping
   create/write **+** `order_company_id` immutability once any order binding
   or tax mapping exists **+** the resolution-time company re-check —
   equivalent structural safety without duplicating derivable data.
3. **Zero or ambiguous mapping → hold, never guess, never create:**
   `odoo_validation_configuration` (`failed_retryable`) naming the **redacted**
   evidence (rate + inclusion + truncated title/source preview); the readiness
   surface carries a standing warning listing unmapped fingerprints observed in
   holds; the operator creates/verifies the tax, adds the mapping, and retries.
   **One fingerprint can never silently change its Odoo tax.**
4. **No tax auto-creation in MVP (REMOVED 2026-07-14, review `4692656343`
   item 4):** Task 012 MVP contains **no automatic `account.tax` creation path** —
   the `order_tax_autocreate` setting and the `"Shopify Tax {percent}%"` generator
   are **removed from scope**. Reasons (closure §5.2b): same-rate fingerprints can
   mean different jurisdictions/accounting; default repartition/accounts are not
   safe config; the generic name collides; **Odoo 19 enforces tax-name uniqueness**
   in the company/country/use scope (a repeated generated name raises a constraint
   error); accounting configuration is operator-owned. **Required operator flow:**
   create/verify the correct Odoo tax → create the explicit connector mapping →
   retry the held order. Automatic creation, if ever wanted, moves to a
   **separately-accepted post-MVP scope** with evidence-fingerprint-specific
   naming, explicit accounting confirmation, and collision tests.
5. **Supported tax structures — leaf percent ONLY (one MVP contract, review
   `4693694894` item 6):** a mapping/resolution target must be a **leaf
   `amount_type == 'percent'`** sale tax (correct company/inclusion, fiscal
   position revalidated). **Multiple independent mapped percentage taxes may apply
   to one line.** A target whose `amount_type ∈ {'group', 'fixed', 'division'}`, or
   any **base-affecting compound** structure (`include_base_amount` /
   `is_base_affected`, or a sequence the §6.2 engine solver cannot reconcile),
   **fails closed** — `odoo_validation_configuration` (`unsupported_tax_structure`),
   never imported and **never counted** in `O`. Advanced tax structures are
   **[Deferred / non-MVP]**, a separately accepted post-MVP scope. This resolves the
   prior contradiction (percent-required vs group-supported): group children are
   **not** claimed or counted. Consistent with this, the §6.4a per-signature check
   requires quantized base equality `q(base_src(σ))==q(base_odoo_raw(σ))` and records
   the **actual** engine raw-base delta `base_delta(σ)`, carrying its **linear**
   `tax_delta_bound(σ)=base_delta(σ)×rate/100` in `tol_tax_total` (valid for leaf
   percentages only; **not assumed zero** — review `4694311215` items 1–2), else
   fail closed (D-012-2 item 3). Odoo recomputes
amounts; agreement with Shopify's per-line math is enforced by the
D-012-2 guard, which is the accepted correctness backstop. Evidence for the ADR: Odoo 19
has **no supported order-level external-tax override**
(`sale.order.tax_totals` compute-only — captures §8), so
exact-amount forcing is impossible at SO level without core hacks
(rejected); **explicit-mapping resolution + the standard Odoo tax engine + the
guard** is the only mechanism that yields a correct, natively-behaving SO. Null-`rate` tax lines (rate nullable —
captures §2) → `data_shape_schema_mismatch` hold. `channelLiable`
tax lines import identically (evidence notes liability). This closes
MBQ-27 for order import; invoice-level exact-amount enforcement
(`account.move.tax_totals` inverse) is recorded as the Phase-2/3
accounting-module mechanism, not used here.

**D-012-10 — Duties, additional fees, cash rounding, currencies (REVISED
2026-07-14, review `4691408835` item 3).** **Duties:** route on the **nonzero
`currentTotalDutiesSet` amount** (a present-but-zero MoneyBag is **not** skipped)
→ `unsupported_duties` policy skip (closure §6.0.4). **Additional fees:** a
**nonzero `currentTotalAdditionalFeesSet`** → `unsupported_additional_fees` policy
skip, evidence = **reason + aggregate amount + currency only** — Task 012 does
**not** query `Order.additionalFees` and never requests/stores/logs
`AdditionalFee.name` (review `4692656343` item 1). **Factual correction (review
`4693694894` item 1):** `Order.additionalFees` in 2026-07 **exposes
list/pagination/filter arguments** (it is **not** an unbounded no-argument plain
list — that round-6 phrasing is withdrawn); the MVP still omits it, but the reason
is **data minimization** (no MVP consumer; extra cost/privacy), not unboundedness.
Duties are **not** assumed to cover every additional fee, so a duty-only order
still reaches the duty reason (closure §6.0.3). **Cash rounding:** a **nonzero**
`totalCashRoundingAdjustment.paymentSet`/`refundSet` → `unsupported_cash_rounding`
policy skip; its inclusion in `totalPriceSet`/`currentTotalPriceSet` is
**undocumented** [Open question], so it fails closed rather than surfacing as a
generic `financial_total_mismatch` (closure §6.0.5). All amounts imported are
**shopMoney** in the shop currency; the SO currency must equal the shop currency,
achieved via pricelist resolution (D-012-11); exchange rates are never applied by
the connector (same-currency-only). `presentmentMoney` values are evidence-only.

**D-012-11 — Company/store ownership & SO parameters.** `company_id`:
new required store-settings field `order_company_id` default
`env.company` (multi-company-safe single default). Pricelist: new
store-settings field `order_pricelist_id` (optional); resolution:
explicit setting → else any active pricelist whose currency matches
the shop currency → else `odoo_validation_configuration`
(failed_retryable; operator creates/activates the pricelist —
`currency_id` is pricelist-derived and not directly settable, captures
§8). Sales team: optional `order_sales_team_id` (unset → Odoo
default). **Payment term (round-9, review `4695589297` item 2; closure §5.6):
new store-settings field `order_payment_term_id` (Many2one `account.payment.term`,
NO default). The importer assigns `sale.order.payment_term_id` EXPLICITLY from it
and NEVER inherits `partner_id.property_payment_term_id` (which
`_compute_payment_term_id` would otherwise apply, `sale_order.py` L430–434).
Readiness BLOCKS order import while it is unset. A configured term that would add
early-payment-discount base lines through `_add_base_lines_for_early_payment_discount`
(`sale_order.py` L530–573) FAILS CLOSED `odoo_validation_configuration` /
`unsupported_early_payment_discount_payment_term` before any SO/binding (never
`financial_total_mismatch`); a matched customer's property term can never override
it.** Warehouse: never set by the connector — whenever
`sale_stock` is present (any database with sale + stock_account,
regardless of connector edition — captures-11 §1), Odoo's own
`warehouse_id` compute applies untouched; where it is absent the
field does not exist and nothing references it (revised 2026-07-11 —
edition-neutral wording). Fiscal position: Odoo's own compute
(no override). Timezone: all Shopify datetimes parsed as UTC (ISO
8601) into naive-UTC Odoo datetimes. Metadata: `origin` +
`client_order_ref` = `Order.name`. **`Order.note`, `Order.tags`, and
`Order.sourceName` are NOT queried or mapped (review `4692656343` item 5,
data-minimization §4.4)** — they are arbitrary free text with no MVP consumer, so
the SO note is left to Odoo's own default and no `crm.tag` is created; if a later
slice needs order note/tags it must re-add the field with a named consumer and
test.

**D-012-12 — Re-import/update & checkpoint hooks.**
`order_import_sync(store, order_gid)` with an existing binding →
evidence-refresh-only: update binding snapshots + one
`event_type='note'` log row (red-team-fixed: no job-state transition
occurs, so `state_change` would be semantically wrong — the merged
`_log_unresolved_address_code` `note` precedent applies) when
`displayFinancialStatus`/`displayFulfillmentStatus`/cancellation
changed; **zero writes to the SO or its lines** —
enforced by a source-level guard test (the strongest DEC-014 J
protection available pre-UI). Enumeration is Area 6's; this task pins
the posture only (ARCH PD-5: `sortKey: UPDATED_AT`,
`updated_at:>checkpoint−overlap`, `first:100`, cursors never
persisted) and adds the checkpoint field
`sale_order_last_import_checkpoint_at` (settings, written only by
Area 6 code later — inert here, mirroring the Posture-A precedent).

## 4. API surface (exact, version 2026-07)

**REVISED 2026-07-14 (Option A, closure §4.2): the single-constant
`ORDER_IMPORT_QUERY` is replaced by four query constants — `ORDER_HEADER_QUERY`
(the field set below, including the first page of each of the three
connections) plus `ORDER_LINE_ITEMS_PAGE_QUERY` /
`ORDER_SHIPPING_LINES_PAGE_QUERY` / `ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY`
(each advancing one connection by `after:$cursor`, re-fetching `id`+`updatedAt`
for verification).** The header field set — `order(id:)` requesting
exactly: `id name legacyResourceId createdAt processedAt updatedAt
edited test currencyCode presentmentCurrencyCode taxesIncluded confirmed
closed closedAt cancelledAt cancelReason displayFinancialStatus
displayFulfillmentStatus email customer { id
firstName lastName defaultEmailAddress { emailAddress }
defaultPhoneNumber { phoneNumber } } billingAddress {
firstName lastName company address1 address2 city zip provinceCode
countryCodeV2 phone } shippingAddress { …same… } totalPriceSet {
shopMoney { amount currencyCode } presentmentMoney { amount
currencyCode } } subtotalPriceSet { …both… } totalTaxSet { …both… }
totalDiscountsSet { …both… } totalShippingPriceSet { …both… }
totalTipReceivedSet { …both… }
currentTotalPriceSet { …both… } currentTotalTaxSet { …both… }
currentShippingPriceSet { …both… } currentTotalAdditionalFeesSet { …both… }
currentTotalDutiesSet { …both… }
totalCashRoundingAdjustment { paymentSet { …both… } refundSet { …both… } }
taxLines { title source rate ratePercentage priceSet { shopMoney {
amount } } channelLiable } shippingLines(first: 50) { edges { cursor node { id isRemoved title
discountedPriceSet { …both… } currentDiscountedPriceSet { …both… } taxLines {
title source rate ratePercentage priceSet { shopMoney { amount } } channelLiable } } } pageInfo {
hasNextPage endCursor } } discountApplications(first: 50) { edges { cursor node { __typename index allocationMethod
targetSelection targetType } } pageInfo { hasNextPage endCursor } } lineItems(first:
100) { edges { cursor node { id name title quantity currentQuantity sku isGiftCard
requiresShipping taxable variantTitle variant { id }
product { id } originalUnitPriceSet { shopMoney { amount } } originalTotalSet { shopMoney { amount } }
discountedUnitPriceSet { shopMoney { amount } } discountedTotalSet { shopMoney { amount } }
priceAfterAllDiscountsBeforeTaxesSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } } discountAllocations {
allocatedAmountSet { shopMoney { amount } } discountApplication {
__typename targetType targetSelection } } taxLines { title source rate ratePercentage priceSet { shopMoney { amount } }
channelLiable } } } pageInfo { hasNextPage
endCursor } }`. **All three connections use `edges{ cursor node }`
(`LineItem.id` non-null secondary; `ShippingLine.id` nullable; `DiscountApplication`
interface has no id → `__typename`+`index`) — review `4691931971` item 1. **Current-state guard fields (review `4691408835` items 1–3):**
the header also requests `currentTotalPriceSet`/`currentTotalTaxSet`/
`currentShippingPriceSet`/`currentTotalAdditionalFeesSet`/`currentTotalDutiesSet`
(all with both currencies; nullability per closure §2 — `currentTotalPriceSet`/
`currentTotalTaxSet`/`currentShippingPriceSet` are `MoneyBag!`, the fee/duty ones
nullable), and `totalCashRoundingAdjustment{paymentSet refundSet}`
(`CashRoundingAdjustment!`). **`Order.additionalFees` detail is NOT queried
(review `4692656343` item 1; factual fix `4693694894` item 1):** the aggregate
`currentTotalAdditionalFeesSet`/`currentTotalDutiesSet` drive the skip, and
`AdditionalFee` (`id:ID! name:String! price:MoneyBag! taxLines:[TaxLine!]!`)
carries **arbitrary merchant free text**. `Order.additionalFees` **exposes
list/pagination/filter arguments** in 2026-07 (it is **not** an unbounded no-arg
plain list — the round-6 phrasing is withdrawn); it is omitted for **data
minimization** (no MVP consumer; extra cost/privacy), so no `additionalFees`
selection appears in any of the four query constants and no fee `name`/`price`/
`taxLines` is requested. Each shipping node adds
`isRemoved`/`currentDiscountedPriceSet` (`ShippingLine.code`/`custom` **removed** —
no consumer; `ShippingLine.title` retained as bounded SO-description text); all tax
lines (line/shipping/order) carry `title`/`source`/`channelLiable` for the versioned
`shopify_tax_evidence_key`.
**Data-minimization (review `4692656343` item 5 + `4693694894` item 5; closure
§4.4):** `note`, `tags`, `sourceName`, line `customAttributes`, line `vendor`,
`customer.displayName`, `customer.defaultAddress`, **`DiscountCodeApplication.code`,
`ShippingLine.code`, and `ShippingLine.custom`** are **removed** — no MVP consumer,
PII/cost risk; the query requests only fields with a proven
gate/ledger/identity/resolution consumer.
**Every field the §6.0 eligibility gates consume is present in the query.** **Pagination — REBUILT
2026-07-14 (review `4690680028` item 4 + review `4691408835` item 2; closure
§4.2/§4.2a; review `4691931971` item 1), Option A: separate query constants with
independent cursors; **all three** connections — `lineItems`, `shippingLines`,
`discountApplications`, in the header first page **and** each page query — use one
executable `edges{ cursor node{…} }` shape (no `nodes`-only read anywhere).** `ORDER_HEADER_QUERY` fetches scalars + all money sets + order-level
`taxLines` + customer/addresses + the **first page** of each of the three
connections (with `pageInfo{hasNextPage endCursor}`), capturing `id` and the
initial `updatedAt` (`updatedAt₀`); `ORDER_LINE_ITEMS_PAGE_QUERY`,
`ORDER_SHIPPING_LINES_PAGE_QUERY`, `ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY`
advance **one connection each** by `after: endCursor` (the header first-pages
are never re-fetched → no first-page duplication). Every page (via
`execute_business`) verifies `Order.id == GID` and `updatedAt == updatedAt₀`
(a change → **torn read** → `concurrency_race_conflict` AUTO_RETRY, lease
released, no SO/binding), requires `pageInfo` (and `endCursor` when
`hasNextPage`), enforces **cursor progress** (repeated `endCursor` →
`data_shape_schema_mismatch`), **dedups by edge cursor (mandatory) then by the
typed secondary identity** (duplicate edge cursor / repeated `endCursor` /
conflicting secondary identity → `data_shape_schema_mismatch`; secondary =
`LineItem.id` non-null, `ShippingLine.id` nullable-when-present, `DiscountApplication`
`__typename`+`index` [no id]; a null id is never a stable GID — closure §4.2a),
and an **independent per-connection page ceiling**
(`LINE_ITEMS_PAGE_LIMIT` / `SHIPPING_LINES_PAGE_LIMIT` /
`DISCOUNT_APPLICATIONS_PAGE_LIMIT` — named provisional defaults) → exceed →
`data_shape_schema_mismatch` naming the ceiling. **No Odoo business write occurs
until all three connections are fully collected and validated.** Page sizes
(`first:100`/`first:50`) are **named provisional defaults — NOT asserted "well
under" the 1,000-point cap**; the importer captures `requestedQueryCost` /
`actualQueryCost` from `extensions` + `throttleStatus` (never the raw payload),
does not auto-expand, and requires authorized dev-store live-read cost evidence
before production tuning (closure §4.3). `discountAllocations`/`taxLines` and
`Order.taxLines` are plain lists (no nested pagination).
Cursors are never persisted. The total-check guard (D-012-2) is the backstop,
not the primary mechanism.
Read-only; zero mutations; scope: `read_orders` (already granted;
customer sub-object needs `read_customers`, also granted). Job type
`order_import_sync` via the three seams, gated `sale_domain_enabled`.
**Job targeting (red-team-corrected):** `res_model='shopify.connector.store'`,
`res_id=store`, `shopify_target_gid=<Order GID>` — a documented
deviation from the bind-row precedent, because on first import the
binding does not exist yet and the merged `operation_scope_key`
clears itself when `res_model` is empty, which would leave exactly
the SO-creating path unserialized (two racing first-import enqueues
would both run). With this targeting the scope key serializes
per-order from the first enqueue onward (mirrors Task 014's
picking-targeting deviation and Area-6's scan targeting).

## 5. Idempotency, atomicity, logging, permissions

Order binding = sole idempotency anchor; `operation_scope_key`
serializes same-order jobs; repeated webhook/scan enqueues collide on
`idempotency_key` (payload-hash = `updatedAt`). One savepoint per
order: partner/children + taxes + SO + lines + confirm + guard +
binding commit together or not at all. Logging: every transition;
PII-minimal messages. **Redaction mechanism (red-team-corrected):**
the merged core `redact()` extends only by secret-*values*
(`extra_secrets`), not by key names, so the order importer applies a
**module-local pre-redaction pass** (`REDACTION_EXTENSION`: email,
phone, name parts, address fields stripped/masked from any
message/technical_detail/payload_snapshot it composes) **before**
handing text to `_system_append` (which then applies the core
`redact()` as usual). The shared PII key list migrates into the core
tool at W1 (a core-owned task) — feeding Q23's list; until then it is
module-local by design. OP-43 verbatim-log rule in the validation
record. ACL:
`ir.model.access.csv` rows for the binding — auditor/operator/reviewer
read-only, admin rwc (no unlink), exactly the customer-binding
pattern; no new groups.

## 6. Tests (exact files) and validation

`tests/test_order_binding.py` (schema/constraints/mixin, dual
uniqueness, restrict FKs); `tests/test_order_import_mapping.py`
(happy path incl. confirm policy, lines/shipping/tip mapping, tax
rate-match + creation + reuse, addresses/dedup, metadata, guest
paths, custom/gift-card lines, UTC parsing);
`tests/test_order_totals_guard.py` (the full D-012-2 revised matrix:
per-component checks and formulas; tolerance boundary ± at each
component; 100-line high-count case; **high-value discounted order
accepted via the exact negative tax-preserving adjustment line**;
**taxable-line order-level discount → residual line inherits the source
`tax_ids`/inclusion so recomputed Odoo tax still matches `totalTaxSet`
(and its untaxed-line no-tax counterpart)**; **mixed taxed+untaxed,
two-rate order → per-signature residual buckets each reconcile**;
**an inconsistent allocation (residual not attributable to a source
line's tax signature) → rejected, not absorbed by tolerance**;
**pathological many-line allocation reconciles exactly**; line + order
discounts; accumulated in-bounds drift accepted; real mismatch
(missing line / wrong price) rejected at component level under the
**cap-free** bound; taxesIncluded (included/excluded) variants; JPY
zero-decimal and BHD three-decimal cases; **no fixed/currency-relative
cap relied upon**; **per-signature quantized base equality
(`q(base_src)==q(base_odoo_raw)`) on the tax-**engine** raw excluded base
(`raw_base_amount_currency`, not the displayed `amount_untaxed`) before the tax
tolerance; a **full minor-unit** base-delta adversarial case fails closed (Example
L)**; **round-5 engine cases (review `4691931971` item 5) — tax-excluded residual
via the engine; tax-included residual derived THROUGH the engine (seed + bounded
solver, **not** an exact-inverse claim), never gross/pre-tax subtraction;
binary-float boundary; multi-repartition **leaf percent** case where `O` counts the
grouping key **once** (never per repartition row); no-valid-candidate → fail closed;
same displayed subtotal but different engine base → engine base governs;
`price_include_override` on `account.tax` not the SO line**; **round-8
tax-engine/tolerance corrections (review `4694311215`) — `special_mode` is a
**seed** not an exact inverse (Odoo symmetry only with unrounded `price_unit` +
`round_globally`; `price_unit` is `Float`); every candidate recomputed through the
actual engine and accepted only from readback (`raw_base_amount_currency`/
`tax_amount_currency`), else fail closed; the **actual** `base_delta(σ)` is recorded
and its linear `tax_delta_bound(σ)=base_delta×rate/100` is carried in `tol_tax_total
= tax_delta_total + 0.5r(S+O)` (Example Q — nonzero delta admitted; NOT reduced to
`0.5r(S+O)`); `O` from SO tax-details grouping keys, never invoice repartition rows
(Example R); the same `tol_tax_total` in per-signature/`amount_tax`/`amount_total`
bounds; a full-minor-unit base mismatch or no-candidate signature FAILS CLOSED
(Example L)**); **round-9 order-level + payment-term + solver (review `4695589297`)
— acceptance uses the actual `sale.order.amount_untaxed`/`amount_tax`/`amount_total`
from the full `_compute_amounts` batch, NOT summed line subtotals (a `round_globally`
case where they differ is accepted only via the order value; a line-level candidate
rejected by the order recompute; multiple lines sharing a tax validated through the
batch; multiple invoice repartition rows keep `O=1`, fixtures 150–153); payment term
assigned explicitly from `order_payment_term_id`, never the partner default; unset
term BLOCKS at readiness; an EPD-mixed term (`_add_base_lines_for_early_payment_discount`)
FAILS CLOSED `unsupported_early_payment_discount_payment_term`; a non-EPD term
imports; a partner property EPD term cannot override the store term, fixtures
154–158; the §6.2b solver is finite/deterministic (≤`2K+1` Product-Price-precision
candidates, seed-passes / seed-adjusts / two-pass-tie / no-candidate-exhaustion /
no-safe-grid, tax-excl + tax-incl + JPY + BHD), fixtures 159–164**);
`tests/test_order_tax_resolution.py` (**explicit-mapping-only** resolution on the
**versioned `shopify_tax_evidence_key`** (`v1:<sha256 hex>`, full untruncated
tuple); **rate-unit pinning — the query carries both `rate` and `ratePercentage`;
the canonical rate derives from `ratePercentage`; `rate × 100 == ratePercentage`
verified; disagreement/null → schema hold**; **fingerprint collisions/versioning
(review `4691931971` item 4 + `4692656343` item 2 + `4693694894` item 4) — two 5%
taxes with different `title`; same title/rate different `source`; null `source` (∅
sentinel ≠ empty); `channelLiable` true/false/null tri-state; two long titles
sharing the same truncated preview → DIFFERENT hashes; **`GST` vs `gst` (case
preserved) → DIFFERENT keys; one space vs two spaces (whitespace preserved) →
DIFFERENT keys; NFC-equivalent Unicode → SAME key; `v1` deterministic
repeatability; a future `v2:` key never collides with any `v1:` key; stored `v1:`
rows never silently recomputed**; two tax lines that would have collided under the
old rate-only/truncated/case-folded key stay distinct; a source/title change → new
unmapped fingerprint**; **supported-tax-structure contract (review `4693694894`
item 6) — simple exclusive %; simple inclusive %; two independent % taxes on one
line — SUPPORTED; a mapped `amount_type='group'`, `'fixed'`, `'division'`, or
base-affecting compound target → HELD `unsupported_tax_structure` (fail closed,
never counted in `O`)**; **explicit-mapping-only (review `4692656343` items 3 & 4)
— an unmapped fingerprint holds; a same-rate existing tax is a non-binding operator
SUGGESTION, never auto-chosen; `>1` mapping → ambiguous hold; one fingerprint
never silently changes its Odoo tax; a correct-total-but-wrong-tax candidate is
never selected**; **no tax auto-create — no `order_tax_autocreate`, no generated
`account.tax`, so no Odoo duplicate-name risk (operator creates tax + mapping +
retries)**; **title/source NFC-only normalization (no case-fold/whitespace-collapse);
raw title/source never in ordinary logs, only the version+hash + redacted
previews**; unmapped → configuration hold; mapping model
schema/`UNIQUE(store_id, shopify_tax_evidence_key)`/`shopify_tax_fingerprint_version`/ACL);
`tests/test_order_duplicate_prevention.py` (re-import
no-dup, evidence-refresh-only incl. the **source-level
no-SO-write-on-refresh guard test**, idempotency-key collision,
divergent-currency/test/cancelled skips, **the round-7 order-edit skip** (review
`4693694894` item 2 — `Order.edited==true` → `unsupported_order_edit` before any SO
write, incl. a **price-only** edit and **two offsetting** edits with unchanged
total, and `edited==true` while every `currentQuantity==quantity`; bounded non-PII
evidence only), **the fail-closed refund/removed-quantity skip** (fully/partially
refunded line, removed line, mixed eligible/ineligible order → whole order skipped
before any SO write, `totalPriceSet != currentTotalPriceSet` cross-check, **plus
the round-8 fail-closed nullable-`totalTaxSet` rule** (review `4694311215` item 3 —
**null `totalTaxSet` → `data_shape_schema_mismatch` in ALL cases** (current-zero,
current-nonzero, currency-mismatch): the round-7 canonical-zero-from-null
construction is **withdrawn**, since Shopify does not document null==zero; non-null
`10.0` vs `10.00` equal; non-null unequal fails; evidence = order GID +
`currentTotalTaxSet` + absence of original tax)), **the round-4 fail-closed skips**
— refunded/partially-refunded/removed
**shipping** (`isRemoved`/`currentDiscountedPriceSet != discountedPriceSet`, product
qty unchanged), **nullable shipping-id + no-DiscountApplication-id** edge-cursor
pagination (all three connections edges/cursor; duplicate cursor / conflicting
secondary id / repeated endCursor → schema mismatch; null id never a stable GID;
header/page shape equality), and the **round-5 fail-closed skips** (review
`4691931971`) — **duty-first** (duty-only order reaches `unsupported_duties`;
duty+fee → duty wins; non-duty-fee-only → `unsupported_additional_fees`; both
present-zero import; duty-null/fee-null handling), **aggregate-only fee evidence**
(reason+aggregate amount+currency in logs; **`Order.additionalFees` not queried**,
so **no fee name/price/taxLines** anywhere; `additionalFees` list-args factual note),
**nonzero-tip → `unsupported_tip_tax_treatment`**, present-zero duty imports, zero
& nonzero cash-rounding, and **query-contains-every-guard-field** assertion
(incl. **`edited`**; and `DiscountCodeApplication.code`/`ShippingLine.code`/`custom`
absent from every query constant));
`tests/test_order_customer_resolution.py` (all D-012-5 paths incl.
fallback used/unset, ambiguous hold with candidate JSON, archived-only,
recall-safety reuse). Negative matrix: unmatched product hold+resume;
>100 lines; null tax rate; missing pricelist; sale-domain flag off.
**Source-level guards (AST) — REBUILT 2026-07-14 (review `4691067575` item 4):**
every header/page Admin GraphQL call goes through `execute_business`; **no**
generic public `execute()` call is reachable from the importer; every result is
consumed inside its `execute_business` context (no result escapes); no Odoo
business write begins until all four query phases complete; a disconnect between
pages blocks the next page; a torn read leaves no SO/binding; no explicit
main-cursor commit; zero mutation strings; zero core/product file edits.
Runtime: full three-suite Odoo.sh run green before merge (SRR-06);
concurrency caveat carried verbatim (ARCH §5.12). Live-Shopify: none
required (read-only; VAL-B2 remains independent).

## 7. Gate criteria (order domain — the 15-criteria pattern instantiated)

1 Task 011 closed runtime-green ✅(fact); 2 MBQ-55 order portion
accepted (= D-012-1 acceptance); 3 exact names in final prompt ✅(§3);
4 exact allowed/forbidden files ✅(§15); 5 dedup/thresholds fixed
✅(D-012-5/12); 6 no accounting/refund/payout scope ✅; 7 no
inventory/fulfillment/product-export scope ✅; 8 no
UI/webhook/OAuth ✅; 9 exact tests ✅(§6); 10 rollback ✅(single-PR
revert; SOs survive un-bound; no dependent domain); 11 no live-Shopify
dependency beyond the Task 003 client ✅; 12 blockers reconfirmed at
gate time (ChatGPT act); 13 fallback-partner consumption boundary
explicit ✅(D-012-5 path 3 — first sanctioned consumer); 14
address/company-person scoped ✅(D-012-6; person-only inherited); 15
ambiguous handling incl. exact evidence fields ✅(D-012-4).

## 8. Acceptance criteria / definition of done / rollback

Only §15 allowlist files changed; binding sole anchor (no duplicate SO
ever); **financial acceptance is the order-level `_compute_amounts` batch
(`amount_untaxed`/`amount_tax`/`amount_total`), not summed line subtotals (round-9)**;
guard blocks beyond tolerance, never silent/auto-retried; **`order_payment_term_id`
assigned explicitly, readiness blocks it unset, EPD-mixed term fails closed
`unsupported_early_payment_discount_payment_term` (round-9)**; **the §6.2b solver is
finite/deterministic and fails closed on grid exhaustion / no-safe-grid (round-9)**;
no divergent-currency/duties SO under any circumstance; evidence-refresh
never mutates an imported SO; **an ambiguous customer creates no partial SO/binding
(job → `blocked_manual_review`, atomic retry after resolution)**; zero
payout/refund/invoice/tax-engine/presentment logic in the diff; suites green locally
and on Odoo.sh; handoff + validation record + AR row appended; draft PR; gate closes on
draft-open. Rollback: revert the single PR — order bindings drop,
`sale.order` records survive as ordinary data; Tasks 013/014 are not
yet started so nothing depends on it. **No database, schema, Odoo module, Shopify
config, or runtime state is changed by this docs-only session; documentation
rollback is reverting the round-9 commit(s).** Upgrade note: the **three** settings
fields (`order_company_id`/`order_pricelist_id`/`order_payment_term_id` and the
others) and the SOL field are additive (no migration).

## 9–14. Cross-references

Sequencing/master plan: `../08-release-readiness/implementation-ready-master-plan.md`.
UAT scenarios 6/7/8 map to this task. Register impacts on acceptance:
OP-14/15/16/17 → Resolved-by-packet (proposed); MBQ-55 order portion →
proposed via D-012-1; MBQ-56/MBQ-27/DEC-020-residual → **proposed
resolution** in the decision-closure and this packet, **pending control-room
acceptance** (the MBQ register records proposed-resolution status only, not
acceptance).

**Lifecycle (LC-1) adoption (re-review `4945129824` item 7):** the
`order_import_sync` `job_type` `selection_add` `ondelete` uses the LC-1
callable `_reassign_to_historic_job_type` from the start (LC-1 precedes
Task 012 — DEC-030 / lifecycle §7), so no later retrofit is needed.
**SEC-1 override seam (item 6):** `shopify.connector.order.binding`
declares `_odoo_binding_field_name()` returning `sale_order_id`.

## 15. Locked final implementation prompt (Task 012)

```text
DO NOT USE UNTIL A SEPARATE CHATGPT CONTROL-ROOM GATE REVIEWS AND ACCEPTS
THIS PLANNING PACKAGE AND THE DECISION-CLOSURE, EXPLICITLY OPENS THE
ORDER-DOMAIN GATE, VERIFIES THE CURRENT BASE SHA, AND ISSUES THIS PROMPT.
This prompt is UNUSABLE until that gate act. Accepting this packet or the
closure does NOT open the gate.

CAPABILITY-BASED PRECONDITIONS — ALL must hold in Shopify-connector before
this prompt may be issued (CORRECTED 2026-07-14, reviews 4690680028 + 4691067575 +
4691408835; these are capabilities, not specific PR merges — the current
unprotected PR #150/#151 heads are NOT directly mergeable; they arrive via the
MERGED CORE-R2 Slice-2B integration-staging strategy, PR #158 / review 4691064435
(merged at Shopify-connector tip 1494b97), which subsumes them in one controlled
integration PR):
  1. SRR-03 CLOSED — CORE-R2 disconnect quiescence proven runtime-green (the
     register FORBIDS merging/enabling/live-validating any Shopify-calling
     domain handler until then; parallel development is allowed).
  2. Protected/guarded product import + complete product/variant bindings
     present (order-line resolution; product Shopify calls run through
     execute_business).
  3. Protected/guarded customer import + indexed normalized-email matching
     present (guest path reuses the indexed lookup at volume; customer Shopify
     calls guarded).
  4. No unguarded product/customer Shopify call remains (public generic
     execute entry closed).
  5. Task LC-1 merged (DEC-030 accepted) — so the core callable
     _reassign_to_historic_job_type exists for this job_type's ondelete.
  CORE-R1 is ALREADY MERGED (satisfied historical foundation — NOT a pending
  precondition; do not list it as unmet).
STOP if any capability is unmet or if the Shopify-connector tip does not
match the SHA ChatGPT states when issuing this prompt.

You are Claude Code implementing Task 012 — Shopify order import —
in AdamsOdoo/Adams, branch from the CURRENT verified Shopify-connector
tip. One session; draft PR; stop.

NO LIVE SHOPIFY REQUEST occurs during implementation or its tests: the
importer is read-only toward Shopify and every test uses fixtures/mocks at
the merged API seam (VAL-B2 live validation stays independent and is NOT
part of this task).

Read first: docs/03-architecture/task-012-order-import-decision-closure.md
(the finalized decisions — authoritative where it and this packet differ),
docs/07-implementation-plan/task-012-order-import-implementation-packet.md
(the D-012-1..12 decisions — binding once this packet is accepted),
docs/03-architecture/final-mvp-module-and-dependency-architecture.md
§3–§7, docs/00-source-materials/shopify-orders-inventory-fulfillment-product-partner-captures-2026-07-10.md
§2/§8, and the merged shopify_connector_sale/product/core code (esp.
execute_business, _transition_skipped, operation_scope_key, idempotency_key,
redact/_system_append).

ALLOWED FILES (exhaustive):
  addons/shopify_connector_sale/__manifest__.py           (depends += shopify_connector_product, sale; version bump)
  addons/shopify_connector_sale/models/__init__.py
  addons/shopify_connector_sale/models/shopify_connector_order_binding.py     (NEW — money snapshots are Char/exact-decimal-string, never Float; shop+presentment totals + component snapshots; no customer PII on the binding)
  addons/shopify_connector_sale/models/shopify_connector_order_importer.py    (NEW — importer service + job seams + REDACTION_EXTENSION)
  addons/shopify_connector_sale/models/shopify_connector_sale_order_line.py   (NEW — shopify_line_item_gid only)
  addons/shopify_connector_sale/models/shopify_connector_store_settings.py    (order_import_confirmation_policy — NO default, unset holds imports; order_import_include_test; order_company_id; order_pricelist_id; order_sales_team_id; order_payment_term_id — NO default, readiness BLOCKS import while unset, holds unsupported_early_payment_discount_payment_term if the term adds EPD base lines, review 4695589297 item 2; sale_order_last_import_checkpoint_at — inert checkpoint) — NO order_tax_autocreate (tax auto-create removed from MVP, review 4692656343 item 4)
  addons/shopify_connector_sale/models/shopify_connector_tax_mapping.py       (NEW — shopify.connector.tax.mapping per D-012-9 step 1)
  addons/shopify_connector_sale/security/ir.model.access.csv                  (binding + tax-mapping rows only)
  addons/shopify_connector_sale/tests/{__init__.py, test_order_binding.py, test_order_import_mapping.py, test_order_totals_guard.py, test_order_tax_resolution.py, test_order_duplicate_prevention.py, test_order_customer_resolution.py}  (NEW)
  addons/shopify_connector_core/models/shopify_connector_job_dispatch.py      (CONDITIONAL core seam, coordinated with CORE-R2 — IF the corrected CORE-R2 dispatcher already respects handler-set terminal states, DO NOT edit this file; ELSE add the minimal terminal-state-respect guard [recommended] or a JobPolicySkip exception + one except-branch calling the existing _transition_skipped; nothing else)
  addons/shopify_connector_core/tests/test_job_dispatch.py                    (append the skip-routing test ONLY if Task 012 adds the core seam, not if CORE-R2 provides it)
  docs/05-qa/task-012-order-import-validation-results.md                      (NEW)
  docs/05-qa/architecture-review-log.md                                       (append one AR row)
  docs/01-research/research-handoff.md                                        (top entry)
FORBIDDEN: every OTHER shopify_connector_core file and every
shopify_connector_product file; adams_base; any view/menu/wizard/
webhook/OAuth/controller/CI/workflow/requirements/Docker file; any
invoice/payment/refund/inventory/fulfillment model or logic; plain
dev; main.

IMPLEMENT exactly per the packet and closure: D-012-1 binding schema (explicit
_name+_inherit, models.Constraint, dual uniqueness; ALL money snapshots as
Char/exact Shopify decimal string parsed with decimal.Decimal, NEVER Float;
shop AND presentment total snapshots per DEC-020; no customer PII stored on
the binding); SIX FAIL-CLOSED PRE-CREATION GATE FAMILIES (closure §6.0; §6.0.4 is a
POINTER into the duty-first §6.0.3 gate, NOT a seventh gate — review 4694311215)
BEFORE any SO, each a terminal policy skip (never financial_total_mismatch): (0)
Order.edited==true
-> unsupported_order_edit (order edits out of MVP; evaluated FIRST; quantity/total
checks alone miss price-only/offsetting edits — review 4693694894 item 2; evidence =
order GID + edited=true + updatedAt only, no edit-history reconstruction); (1) every
line currentQuantity==quantity AND money_equal(totalPriceSet,currentTotalPriceSet)
AND the price⇄current-tax rule — if totalTaxSet is NON-NULL,
money_equal(totalTaxSet,currentTotalTaxSet); if totalTaxSet is NULL, FAIL CLOSED —
NO SO, NO binding — data_shape_schema_mismatch (Shopify documents totalTaxSet as
nullable but NOT that null means zero, so the round-7 canonical-zero-from-null
construction is WITHDRAWN — review 4694311215 item 3; evidence = order GID +
currentTotalTaxSet amount/currency + absence of original tax; NEVER reinterpret null
as zero; a later evidence-backed decision may normalize null->zero); the non-null
unequal case -> refunded_or_removed_quantity; (2) every shipping
line isRemoved==false AND currentDiscountedPriceSet==discountedPriceSet (both
currencies) AND consistent with currentShippingPriceSet ->
refunded_or_removed_shipping; (3) DUTY-FIRST PRECEDENCE — if currentTotalDutiesSet
!= 0 -> unsupported_duties (reachable for duty-only orders; additional fees CAN
include duties, so no subtraction, no composition inferred); ELSE IF
currentTotalAdditionalFeesSet != 0 -> unsupported_additional_fees (Order.additionalFees
is NOT QUERIED — the aggregate drives the skip; evidence = reason+aggregate
amount+currency ONLY, NO AdditionalFee.name/price/taxLines requested/stored/logged;
Order.additionalFees DOES expose list/pagination/filter args but is omitted for DATA
MINIMIZATION, review 4692656343 item 1 + 4693694894 item 1); (4) nonzero
totalCashRoundingAdjustment payment/refund -> unsupported_cash_rounding (inclusion in
totalPriceSet undocumented, fail closed); (5) NONZERO totalTipReceivedSet ->
unsupported_tip_tax_treatment (tip tax treatment undocumented; NO untaxed Tip line;
T=0 in the ledger — the round-4 untaxed-tip posture is WITHDRAWN, review 4691931971
item 6); no SO/binding, non-PII evidence, no refund reconstruction; ALL money
equality/zero tests use money_equal/is_zero (currency-code match + parsed-Decimal
value, never lexical strings; 10.0==10.00, currency mismatch never equal); D-012-2 REBUILT
guard (closure §6, authoritative) — the canonical single-count Decimal ledger U_ex
= M + H + T (T=0), with M =
Sum_i(priceAfterAllDiscountsBeforeTaxesSet_i.shopMoney) — the EXACT per-line total
after all discounts, pre-tax, current-quantity (NO OC subtraction, and NEVER
assume quantity × discountedUnitPriceSet == any total; discountedUnitPriceSet is
"approximate", display/audit only), H = Sum(shippingLines.discountedPriceSet −
shipping taxLines if taxesIncluded else 0) (exact shipping, back out tax once only
when inclusive); U_ex is ALWAYS tax-exclusive (NO global G−totalTaxSet back-out);
lines tol = 0.5r*L (tax-excl) or 0.5r*(L+S_ship) (tax-incl, only shipping back-out
roundings; no tip line in L); ORDER-LEVEL ACCEPTANCE (round-9, review 4695589297
item 1; closure §6.2a) — after constructing ALL candidate lines and assigning the
explicit payment term, RECOMPUTE the WHOLE sale.order via _compute_amounts (all
priced lines + EPD lines -> _add_tax_details_in_base_lines -> _round_base_lines_tax_details
-> _get_tax_totals_summary, sale_order.py L512-528) and compare Shopify evidence to
the ACTUAL sale.order.amount_untaxed/amount_tax/amount_total + batch tax evidence,
NEVER to summed line price_subtotal/price_tax (they differ under round_globally,
account_tax.py L1896-1927); a line candidate that passes in isolation is REJECTED by
the order recompute; O = distinct batch grouping keys, never repartition rows;
PAYMENT TERM (round-9, review 4695589297 item 2; closure §5.6) — assign
sale.order.payment_term_id EXPLICITLY from store.order_payment_term_id, NEVER inherit
partner_id.property_payment_term_id (sale_order.py L430-434); readiness BLOCKS import
while order_payment_term_id is unset; a term that would add EPD base lines via
_add_base_lines_for_early_payment_discount (fires on early_discount + 'mixed' +
discount_percentage, sale_order.py L530-573) FAILS CLOSED odoo_validation_configuration
/ unsupported_early_payment_discount_payment_term BEFORE any SO/binding, NEVER
financial_total_mismatch; TAX-INCLUDED RESIDUAL VIA SEED + FINITE §6.2b SOLVER, NOT
EXACT INVERSION (closure §6.2-C/§6.2b, reviews 4694311215 item 1 + 4695589297 item 3)
— special_mode='total_excluded' is a SEED, NOT an exact inverse (Odoo 19 guarantees
symmetry only with an unrounded price_unit + round_globally; sale.order.line.price_unit
is fields.Float with min_display_digits='Product Price' = a DISPLAY hint, NOT a storage
grid, sale_order_line.py L177-181), so a FINITE DETERMINISTIC solver over the
Product-Price-precision grid (<= 2K+1 candidates, non-decreasing |u-u0|, u0-d before
u0+d, lower-wins tie-break; grid NEVER assumed = currency rounding) RECOMPUTES each
candidate through the ACTUAL engine AND the full-order _compute_amounts batch,
ACCEPTS ONLY from the engine readback (raw_total_excluded_currency/total_excluded_currency/
raw_base_amount_currency/raw_tax_amount_currency/tax_amount_currency + order amounts),
else FAIL CLOSED on grid exhaustion (K) or no-safe-grid (narrowed MVP scope) ->
financial_total_mismatch; PER-TAX-SIGNATURE BASE — ENGINE RAW EXCLUDED BASE,
QUANTIZED (closure §6.4a) BEFORE the tax tolerance — for each signature (the
VERSIONED shopify_tax_evidence_key, v1:<sha256 hex>) require
res.currency.round(base_src(σ)) == res.currency.round(base_odoo_raw(σ)) where
base_odoo_raw = the tax ENGINE's returned raw_base_amount_currency (NOT a hand
price_unit×qty×(1−discount) formula, NOT the displayed amount_untaxed); a GLOBAL
amount_untaxed match is NOT sufficient; ANY nonzero quantized base diff (a FULL
minor-unit base error) -> financial_total_mismatch first; ONE GLOBAL TAX TOLERANCE
(reviews 4693694894 item 7 + 4694311215 items 1-2): tol_tax_total = tax_delta_total
+ 0.5r*(S+O), tax_delta_total = Σ_σ tax_delta_bound(σ); tax_delta_bound(σ) =
base_delta(σ)×rate/100 is the ACTUAL engine-derived raw-base-delta term
(base_delta(σ) = |base_odoo_raw(σ)−base_src(σ)|), NOT assumed zero — RECORD the
actual raw delta, CARRY its linear leaf-percent tax term in the bound, and compare
the FINAL ACTUAL engine tax_amount_currency with Shopify evidence; it is 0 only when
the raw base matches exactly (clean 2-decimal). The linear form is valid ONLY for
independent leaf percentages — NEVER applied to a deferred group/fixed/division/
base-affecting structure (those are HELD unsupported_tax_structure). A signature for
which the §6.2b solver finds NO grid candidate satisfying the base+tax checks
FAILS CLOSED (never widen the tolerance). State/use tol_tax_total WITH the
tax_delta_total term EVERYWHERE (per-signature/amount_tax/amount_total/examples/
tests) so NO doc reduces it to 0.5r(S+O) while a nonzero delta is possible; it is a
PROPOSED CONSERVATIVE bound under EXPLICIT assumptions (bases reconciled at the
engine via readback; rates match; each Shopify/Odoo event rounds ≤0.5r; complete O) — the
Shopify-event rounding premise is LABELLED SEPARATELY (Inference, not an official
guarantee; the schema does not state the convention), undocumented-rounding
currencies FAIL CLOSED pending authorized dev-store evidence; S = Shopify
per-line/per-shipping tax rounding events; O = SALE-ORDER tax rounding events under
the ACTUAL tax_calculation_rounding_method (amount_tax comes from the SO tax-details
computation, so O = distinct LEAF-TAX GROUPING KEYS under round_globally [Odoo-19
default] / taxed-line×leaf-tax pairs under round_per_line — NEVER invoice repartition
rows, review 4694311215 item 2; group children DEFERRED/fail-closed and NOT counted);
the old K=distinct-groups bound is WITHDRAWN (omits S); total tol = lines +
tol_tax_total, NO cap; a ledger self-check
(Total_ex==totalPriceSet) backstops; each product line reproduced THROUGH THE
ACTUAL ODOO 19 TAX ENGINE (price_include_override lives on account.tax NOT the SO
line; construct candidate sale.order.line, read engine total_excluded/total_included
+ tax breakdown, add qty-1 residual with the same tax signature, RECOMPUTE THROUGH
THE ENGINE; for tax-included derive the residual gross via the engine
[special_mode='total_excluded' seed + finite §6.2b solver], NEVER gross/pre-tax subtraction;
money fields are binary float so no residual is assumed to store a Decimal exactly;
no valid residual -> FAIL CLOSED), VERIFIED the engine excluded base reconciles;
residual INHERITS the source line's tax_ids (and thereby the mapped account.tax's
price_include_override — inclusion is on the tax, not the SO line) (or one per tax
signature) — never a
universal no-tax residual for a taxable line; an inconsistent allocation ->
REJECTED (financial_total_mismatch), never absorbed; do all source arithmetic in
Decimal, the Odoo side through the tax engine; test matrix incl. the
approximate-unit-price/code-discount divergence, refund/removed product AND
shipping skips, all-three-connections edges/cursor + header/page shape equality,
nullable-shipping-id + no-DiscountApplication-id pagination, duty-first precedence
(duty-only reachable), additionalFees-detail-not-queried + aggregate-only skip,
hashed-fingerprint collisions (full-title hash differs despite equal preview;
evidence change → new unmapped fingerprint), explicit-mapping-only (same-rate is a
suggestion, no auto-fallback), no-tax-auto-create/no-dup-name, Decimal 10.0==10.00
+ currency-mismatch-fails, minimized-fields-absent-from-query,
correct-total-wrong-tax rejected, tax-included residual via the
engine, rounded-equal-but-engine-different bases, nonzero-tip skip, present-zero
duty (imports), the per-signature base-delta adversarial case, the many-small-lines/
global-rounding counterexample, and the fully worked tax-inclusive cases;
D-012-3 skipped-by-policy routing (order edits [edited==true], divergent currency,
duty-first duties, nonzero additional fees, nonzero cash rounding, nonzero tip,
refunded/removed product & shipping, test orders, pre-cancelled — the closed
skip_reason set) via the CONDITIONAL core skip
seam coordinated with CORE-R2 (recommended: a terminal-state-respect guard so
the handler calls _transition_skipped and Task 012 needs NO core edit; else
JobPolicySkip) — never a new error class, terminal `skipped` with a
skip_reason label, no other core change;
D-012-4 ambiguous-customer pre-creation hold with Task 011 §8.2
candidate JSON; D-012-5 resolution sequence incl. guest paths and the
first sanctioned customer_fallback_partner_id consumption
(odoo_validation_configuration when unset); D-012-6 address children
with normalized-tuple dedup, explicit partner_invoice_id/
partner_shipping_id writes, never mutating existing partners; D-012-7
REVISED lifecycle: confirmation policy is an explicit operator
decision with NO default (unset -> odoo_validation_configuration
hold + readiness warning); stock behavior follows installed Odoo
apps (sale_stock is auto_install in Odoo 19 — captures-11 §1), never
connector edition — no Lite/no-picking assumption anywhere in code,
copy, or tests; date_order = processedAt UTC; never auto-cancelling
an SO on refresh; D-012-8 line mapping (variant-binding resolution,
whole-order-hold mapping_missing on unmatched, EXACT line total from
priceAfterAllDiscountsBeforeTaxesSet reproduced THROUGH THE ODOO TAX ENGINE
[candidate line + engine total_excluded + qty-1 residual recomputed through the
engine; never quantity × discountedUnitPriceSet, never a hand base formula],
custom-item service product, gift-card note); D-012-9
shipping/tips/taxes: SHIPPING ELIGIBILITY (closure §6.0.2) — every shipping line
isRemoved==false AND currentDiscountedPriceSet==discountedPriceSet (both
currencies) AND consistent with currentShippingPriceSet, else skip
refunded_or_removed_shipping before SO; shipping exact pre-tax source =
discountedPriceSet (back out its taxLines ONCE only when taxesIncluded=true),
preserve the shipping tax signature; NONZERO TIP FAILS CLOSED
(unsupported_tip_tax_treatment; no untaxed Tip line; T=0 in the ledger — undocumented
tip tax treatment, review 4691931971 item 6); taxes: RATE-UNIT PINNING — the query
requests BOTH TaxLine.rate (decimal proportion) and TaxLine.ratePercentage
(percentage) plus TaxLine.title/source/channelLiable; the CANONICAL rate derives
from ratePercentage (Decimal-parsed, 6 dp, never a Float); verify rate × 100 ==
ratePercentage, disagreement/null -> data_shape_schema_mismatch; EXPLICIT-MAPPING-ONLY
(review 4692656343 items 2/3/4; VERSIONED + FOLD-FREE per 4693694894 item 4): resolve
tax ONLY via a shopify.connector.tax.mapping row keyed by shopify_tax_evidence_key =
a VERSIONED SHA-256 FINGERPRINT, format v1:<sha256 hex>, of the FULL normalized tuple
(SHOPIFY_TAX_FINGERPRINT_VERSION=1 + ratePercentage + NFC-normalized title + null-safe
source + channelLiable tri-state + inclusion), fixed algorithm SHA-256, deterministic
LENGTH-PREFIXED UTF-8 serialization INCLUDING the version; title/source normalized
with UNICODE NFC ONLY — case AND whitespace PRESERVED (NO case-folding, NO whitespace
collapse, NO truncation); source-null sentinel ≠ empty string — an EVIDENCE
FINGERPRINT, not an officially stable identifier (UNIQUE(store_id,
shopify_tax_evidence_key) + stored shopify_tax_fingerprint_version; rate-only key,
truncated-title key, AND case-folded/whitespace-collapsed key ALL WITHDRAWN); DO NOT
truncate/fold before hashing; MIGRATION posture — a normalization/algorithm change
needs a NEW version (v2:), old v1: rows stay interpretable and are NEVER silently
recomputed, v1:/v2: spaces cannot collide; store separate redacted/truncated
title_preview/source_preview for protected operator display ONLY (raw title/source
NEVER in ordinary logs); the same identity queried on line/shipping/order tax lines;
a changed tuple -> NEW UNMAPPED fingerprint (held). SUPPORTED TAX STRUCTURES — LEAF
amount_type=='percent' ONLY (review 4693694894 item 6); group/fixed/division and
base-affecting compound targets FAIL CLOSED (unsupported_tax_structure), never
imported/counted; multiple independent mapped percent taxes may apply to one line.
NO automatic existing-tax fallback: a same-rate account.tax is a NON-BINDING
OPERATOR SUGGESTION ONLY (readiness surface may show candidates with
company_id==order_company_id, active, type_tax_use='sale', amount_type='percent',
price_include_override (on account.tax) matching inclusion; float_compare is ONLY
the boundary comparison to Odoo's existing Float amount — do NOT claim it preserves
Decimal precision) — the importer NEVER auto-selects by rate; validate the
fiscal-position map_tax result at resolution; ZERO mapping -> configuration hold,
>1 mapping -> AMBIGUOUS hold, one fingerprint NEVER silently changes its Odoo tax
(correct total with wrong tax is rejected); mapping model keeps store_id with
an @api.constrains that account_tax_id.company_id==store_id.order_company_id
plus order_company_id immutability once bindings/mappings exist; unmapped ->
configuration hold naming the redacted evidence; NO TAX AUTO-CREATE — there is NO
order_tax_autocreate and NO generated account.tax in MVP (same-rate meaning
collapse, unsafe default repartition, generic-name collision, Odoo tax-name
uniqueness constraint, operator-owned accounting — closure §5.2b); operator flow =
create/verify Odoo tax -> create mapping -> retry (null-rate -> hold);
D-012-10/11 currency/pricelist/company/team resolution and UTC parsing;
D-012-12 evidence-refresh-only re-import (note-type log rows) with the
source-level no-SO-write guard test + the module-local
REDACTION_EXTENSION pre-redaction pass. Pagination — Option A (closure §4.2),
read-only: ORDER_HEADER_QUERY + ORDER_LINE_ITEMS_PAGE_QUERY +
ORDER_SHIPPING_LINES_PAGE_QUERY + ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY, each
connection with its OWN cursor loop (header first-pages never re-fetched -> no
first-page duplication); every page verifies Order.id==GID and
updatedAt==updatedAt0 (change -> TORN READ -> concurrency_race_conflict
AUTO_RETRY, lease released normally, NO SO/binding), requires pageInfo
(endCursor when hasNextPage); ALL THREE connections (lineItems/shippingLines/
discountApplications) read as edges{ cursor node{…} } in header + page queries
(ONE executable shape, no nodes-only read; review 4691931971 item 1) — dedup by
EDGE CURSOR (mandatory) then by the typed secondary identity (LineItem.id non-null;
ShippingLine.id nullable-when-present; DiscountApplication has NO id -> __typename+
index); duplicate edge cursor / conflicting secondary identity / repeated endCursor
-> data_shape_schema_mismatch; a null id is NEVER a stable GID; enforce cursor progress + independent
per-connection page ceilings (LINE_ITEMS/SHIPPING_LINES/
DISCOUNT_APPLICATIONS_PAGE_LIMIT, named provisional defaults) -> exceed ->
data_shape_schema_mismatch naming the ceiling; NO Odoo write until all three
connections are collected+validated; every query result is consumed INSIDE its
execute_business context (no result escapes); cursors never persisted; the query
requests EVERY guard field — Order.edited (the order-edit gate), currentTotalPriceSet/
currentTotalTaxSet/currentShippingPriceSet/currentTotalAdditionalFeesSet/
currentTotalDutiesSet (both currencies), totalCashRoundingAdjustment{paymentSet
refundSet}, per-shipping isRemoved/currentDiscountedPriceSet, tax-line
title/source/channelLiable (for the versioned shopify_tax_evidence_key on
line/shipping/order tax lines), plus priceAfterAllDiscountsBeforeTaxesSet (the exact
per-line invariant), originalUnitPriceSet/originalTotalSet, and discountApplication
__typename/targetSelection for tax-signature attribution (no gate
references an unqueried field); Order.additionalFees is NOT queried (aggregate
currentTotal*Set drives the skip; AdditionalFee.id acknowledged, name never
requested/stored/logged; the field DOES expose list/pagination/filter args but is
omitted for DATA MINIMIZATION — review 4692656343 item 1 + 4693694894 item 1);
DATA-MINIMIZATION (review 4692656343 item 5 + 4693694894 item 5) — note/tags/
sourceName, line customAttributes, line vendor, customer.displayName,
customer.defaultAddress, AND DiscountCodeApplication.code / ShippingLine.code /
ShippingLine.custom are REMOVED (no MVP consumer); ShippingLine.title retained as
bounded SO-description free text (out of ordinary logs);
ALL money equality/zero tests use money_equal/is_zero — currencyCode match +
parsed decimal.Decimal numeric comparison, NEVER lexical string equality
(10.0==10.00; currency mismatch fails; review 4692656343 item 6); page sizes
(first:100/50) are NAMED PROVISIONAL DEFAULTS, NOT asserted under the
1000-point cap — capture requestedQueryCost/actualQueryCost + throttleStatus
from extensions (never the raw payload), do not auto-expand, dev-store
live-read cost evidence before any tuning; line-level lists and Order.taxLines
are plain lists (no nested pagination). Job type order_import_sync via the
three seams gated on sale_domain_enabled; job targeting
res_model='shopify.connector.store' + shopify_target_gid=<Order GID>
(packet §4 — the documented deviation that keeps operation_scope_key
populated on first import). One savepoint per order. Reuse the existing customer importer functions — do not
duplicate matching logic. All §6 test files with every named case,
incl. negative matrix and source-level guards.

HARD CONSTRAINTS: read-only toward Shopify — zero mutation anywhere, NO
live Shopify request in code or tests (fixtures/mocks only);
no blind retry of anything (RA-014); no new error class (the 16-class
registry is untouched; divergent-currency/duties/test/pre-cancelled route to
`skipped` policy with NO error class, never overloading
financial_total_mismatch); no force/bypass flag; every Shopify read runs
inside `with execute_business(job, store, query, variables)` and every result is
consumed inside that context (no result escapes; no generic public execute()
reachable; no Odoo write until all four query phases complete);
PII-minimal logs via redact() + REDACTION_EXTENSION; NO raw GraphQL payload
or token persisted anywhere; email remains the
sole automatic customer key (RA-006); existing partners' own fields never
mutated (only invoice/delivery child rows added); VAL-B2 / MBQ-05 / TD-002 /
SRR-03/04/09 / Lite-Full untouched; the claim/dispatch concurrency caveat and
the SRR-03/disconnect race are restated, not resolved (Task 012 does NOT wire
ShopifyQuiescedError->skipped — that is a later CORE-R2 slice). Runtime: full
Odoo.sh run must be green before merge
review (quote the result verbatim; OP-43 rule). Static: py_compile,
pyflakes, docutils-clean docstrings, AST guards proving every Admin GraphQL call
uses execute_business, no generic public execute() is reachable, and no result
escapes its execute_business context.

STOP CONDITION: open the PR as DRAFT titled "Task 012: Shopify order
import (shopify_connector_sale)", update handoff + validation record +
AR row, report per the packet's report format, and stop. The
order-domain gate closes the moment the draft PR opens. Do not start
Task 013/014/015, Area 6, UI, webhook, OAuth, packaging, or accounting
work under any circumstance.
```
