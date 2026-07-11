# Task 012 — Order Import: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §15 is NOT usable.** Produced 2026-07-10 by the MVP
> planning-completion session (AR-042 candidate); **revised
> 2026-07-11** by the PR #148 revision session per ChatGPT's
> control-room review (comment `4942966937`, item 6): (a) the
> incorrect Lite/`sale_stock` assumption is removed — `sale_stock` is
> `auto_install: True` in official Odoo 19 (2026-07-11 captures §1,
> `../00-source-materials/odoo19-shopify-official-captures-2026-07-11.md`
> — "captures-11" below) so stock behavior derives from installed
> Odoo apps + explicit operator policy, never from connector edition
> (D-012-7 revised); (b) `order_tax_autocreate` defaults to **False**
> with explicit tax mapping preferred (D-012-9 revised); (c) the
> total-check tolerance is now component-based with a
> currency-relative cap (D-012-2 revised); (d) prerequisites now
> include **CORE-R1, Task 010B, and Task 011B** (complete variant
> bindings + scalable customer matching precede order import).
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
no fulfillment write-back (Task 014); no inventory logic (Task 013 —
SO confirmation's standard Odoo reservation is not connector inventory
logic); no presentment-currency orders; no tax engine (rate-matching
only, §5); no enumeration/scan triggers (Area 6); no webhooks; no UI
beyond nothing (Error-Center extensions are UI-phase scope); no
`read_all_orders` (60-day default window is the MVP posture — historic
backfill is a documented setup limitation until a separately-approved
scope request).

**Dependency prerequisites:** Tasks 002/003 (client), 006C
(dispatch), 010 (product/variant bindings), 011 (customer
binding/importer) merged and runtime-green [facts]; **plus (added
2026-07-11, revised critical path): CORE-R1 (stores can reach
`connected` — required for live validation), Task 010B (complete
variant bindings for ordinary multi-variant catalogs — order-line
resolution starves without them), and Task 011B (indexed customer
matching — this packet's D-012-5 guest path reuses it at
order-import volume).** Gate prerequisites (ChatGPT acts): acceptance
of this packet (incl. the D-012 decisions and ARCH PD-3/PD-4), the
order-domain gate act, prompt issuance.

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
`shopify_financial_status_snapshot`/`shopify_fulfillment_status_snapshot`
(Char — raw enum strings; `displayFinancialStatus` is nullable, store
empty as False), `shopify_cancelled_at` (Datetime),
`shopify_order_total` (Float — `totalPriceSet.shopMoney.amount`),
`customer_resolution` (Selection: existing_binding / email_match /
created / guest_email_match / guest_created / fallback / manual —
readonly; the fallback audit marker), `shopify_last_imported_at`
(Datetime). Constraints (models.Constraint):
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

1. **Lines:** `|odoo_untaxed_lines_sum − shopify_lines_expected|
   ≤ tol_lines`, where `shopify_lines_expected` = Σ per-line
   `discountedUnitPriceSet × quantity` minus order-level
   `discountAllocations`, and `tol_lines = r × (0.5 × N_lines +
   D_lines × 0.5)` — `r` = the order currency's `res.currency.rounding`
   (captures-11 §6: rounding drives `decimal_places`; default 0.01;
   JPY 1.0; three-decimal currencies 0.001), `N_lines` = SO line
   count, `D_lines` = lines carrying an Odoo `discount` % (each %
   quantized at 2 dp contributes ≤ 0.5r allocation residual).
2. **Taxes:** `|odoo_amount_tax − totalTaxSet.shopMoney| ≤ tol_tax =
   r × 0.5 × N_tax_lines` (per-tax-group rounding bounded by r/2).
3. **Shipping + tip:** exact to one rounding step each
   (`≤ r` per component — single lines, no accumulation).
4. **Total:** `|amount_total − totalPriceSet.shopMoney| ≤
   min(tol_lines + tol_tax + 2r, CAP)` with **CAP = 10 × r —
   currency-relative** (0.10 in 2 dp currencies, 10 JPY, 0.010 BHD),
   replacing the old fixed 1.00-currency-unit cap, which could hide a
   material mismatch (review finding — accepted).

Any component or total breach → roll back the savepoint (no SO
persists), classify `financial_total_mismatch` (existing class;
CONSERVATIVE_NEVER_SILENT → `failed_retryable`, never auto-retried),
full component breakdown (each Shopify money field, each computed
Odoo amount, each tolerance term) in `job.log.technical_detail` JSON.
The guard is mandatory and permanent; no flag bypasses it; tolerances
are formula-fixed (no per-store tolerance setting exists).
**Mandatory test matrix (review-required):** high line counts (100
lines at cap), `taxesIncluded` true/false, line + order discounts,
accumulated small rounding drift inside bounds (accepted), a real
mismatch (missing line / wrong price — rejected at component level),
zero-decimal (JPY, r=1.0) and three-decimal (BHD, r=0.001) currency
orders (ISO 4217 minor units — captures-11 §12). Shopify-side
three-decimal precision policy is officially undocumented
(captures-11 §11) → one named dev-store empirical check before any
three-decimal-currency store is onboarded.

**D-012-3 — Divergent-currency routing (DEC-020 residual) + policy
skips.** A divergent order (`presentmentCurrencyCode !=
currencyCode`), detected **before any SO creation**, moves the job to
**`skipped`** (terminal, policy), with message "Automatic import not
supported: divergent presentment currency (DEC-020)" and both currency
codes + both `shopMoney`/`presentmentMoney` total sets captured in the
log payload. Mechanics (red-team-corrected against the merged
dispatcher, which unconditionally marks a normally-returning handler
`succeeded`): this task adds **one named additive core seam** — a
`JobPolicySkip(message, technical_detail)` exception class in
`shopify_connector_job_dispatch.py` plus one `except JobPolicySkip`
branch in `_invoke_handler()` that calls the existing
`job._transition_skipped(...)` — making policy-skip a first-class
dispatcher outcome (reused verbatim by Task 013's `tracked=false`
skip). This is an explicitly-flagged core edit (mirrors Task 014's
TD-002 edit pattern; master plan §1 review call), with its own core
test. Rationale: an eligibility/policy block is not a failure — the
16-class error registry stays intact (no 17th class) and DEC-020's
"blocked … before SO creation, independent of the total-check outcome"
is honored. The same routing applies to: orders with non-null
`currentTotalDutiesSet` (D-012-10), `test: true` orders when
`order_import_include_test` is False (default), and orders already
cancelled at first import (D-012-7). Skipped-by-policy jobs are
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

**D-012-8 — Lines, discounts, custom items.** One `sale.order.line`
per LineItem: `product_id` via the **variant binding** (template
binding alone is insufficient); `product_uom_qty = quantity`
(`currentQuantity` is refund-adjusted — refunds are out of scope, the
ordered quantity is imported; both captured in evidence);
`price_unit = discountedUnitPriceSet.shopMoney.amount` (line-level
discounts baked in — captures §2); order-level/code discounts (from
`discountAllocations`) land in the Odoo `discount` % field computed at
its 2-dp precision, residual drift absorbed by the D-012-2 tolerance;
`originalUnitPriceSet` and all allocations preserved in the evidence
payload; `shopify_line_item_gid` set; `name` = LineItem `title` (+
`variantTitle`). **Unmatched product line** → whole-order-hold:
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

**D-012-9 — Shipping, tips, taxes (MBQ-27 closure; OP-17).**
Shipping: one SO line per `shippingLines` node (paginated connection —
read `first: 10`, >10 → `data_shape_schema_mismatch`), service product
"Shopify Shipping" (auto-provisioned, per store), `price_unit =
discountedPriceSet.shopMoney.amount`, its `taxLines` mapped per T-B.
Tips: `totalTipReceivedSet > 0` → one line, service product "Shopify
Tip", no taxes. Duties: D-012-3 skip. **Taxes — proposed mechanism
T-B ("mapped-or-matched Odoo taxes under the guard") — REVISED
2026-07-11 (review item 6b): ordinary order import must never
silently create accounting configuration.** Resolution order for
each distinct `TaxLine` on a line/shipping line:

1. **Explicit tax mapping (preferred):** new model
   `shopify.connector.tax.mapping` (store_id; `shopify_rate_percent`
   Float; `price_include` Boolean; `account_tax_id` M2o `account.tax`
   required restrict; UNIQUE(store_id, shopify_rate_percent,
   price_include)) — admin-maintained (rwc admin, read others, no
   unlink; settings-area UI in a later phase, shell/import until
   then). A mapping hit resolves immediately.
2. **Existing-tax rate match:** exact match on (company,
   `type_tax_use='sale'`, `amount_type='percent'`,
   `amount = rate×100`, price inclusion per `Order.taxesIncluded`
   via `price_include_override`, the 19.0-correct field — captures
   §8); attach via `tax_ids`.
3. **Unmatched → hold, never create:**
   `odoo_validation_configuration` (`failed_retryable`) naming the
   exact rate/inclusion pair; the readiness surface carries a
   standing warning listing unmapped rates observed in holds; the
   operator adds a mapping (or the tax) and retries.
4. **Auto-creation exists only as an explicit administrator opt-in:**
   settings Boolean `order_tax_autocreate`, **default False**,
   admin-gated, with warning copy stating plainly that enabling it
   creates persistent `account.tax` master records with default
   repartition (no custom accounts). When True, step 3 instead
   creates "Shopify Tax {percent}% ({incl/excl})" as before, each
   creation logged with a `manual_action`-grade audit line naming the
   enabling admin setting. The release-plan documentation tells
   accountants these taxes exist. The account/repartition mapping
   remains a named input to the Phase-2/3 accounting module. Odoo recomputes
amounts; agreement with Shopify's per-line math is enforced by the
D-012-2 guard, which is the accepted correctness backstop. Evidence for the ADR: Odoo 19
has **no supported order-level external-tax override**
(`sale.order.tax_totals` compute-only — captures §8), so
exact-amount forcing is impossible at SO level without core hacks
(rejected); rate-matching + guard is the only mechanism that yields a
correct, natively-behaving SO. Null-`rate` tax lines (rate nullable —
captures §2) → `data_shape_schema_mismatch` hold. `channelLiable`
tax lines import identically (evidence notes liability). This closes
MBQ-27 for order import; invoice-level exact-amount enforcement
(`account.move.tax_totals` inverse) is recorded as the Phase-2/3
accounting-module mechanism, not used here.

**D-012-10 — Duties, tips, currencies, exchange rates.** Duties → D-012-3.
All amounts imported are **shopMoney** in the shop currency; the SO
currency must equal the shop currency, achieved via pricelist
resolution (D-012-11); exchange rates are never applied by the
connector (same-currency-only). `presentmentMoney` values are
evidence-only.

**D-012-11 — Company/store ownership & SO parameters.** `company_id`:
new required store-settings field `order_company_id` default
`env.company` (multi-company-safe single default). Pricelist: new
store-settings field `order_pricelist_id` (optional); resolution:
explicit setting → else any active pricelist whose currency matches
the shop currency → else `odoo_validation_configuration`
(failed_retryable; operator creates/activates the pricelist —
`currency_id` is pricelist-derived and not directly settable, captures
§8). Sales team: optional `order_sales_team_id` (unset → Odoo
default). Warehouse: never set by the connector — whenever
`sale_stock` is present (any database with sale + stock_account,
regardless of connector edition — captures-11 §1), Odoo's own
`warehouse_id` compute applies untouched; where it is absent the
field does not exist and nothing references it (revised 2026-07-11 —
edition-neutral wording). Fiscal position: Odoo's own compute
(no override). Timezone: all Shopify datetimes parsed as UTC (ISO
8601) into naive-UTC Odoo datetimes. Metadata: `origin` +
`client_order_ref` = `Order.name`; `Order.note` → SO note (plain-text
sanitized); tags/sourceName → binding/evidence only (no crm.tag
creation).

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

Single query constant `ORDER_IMPORT_QUERY` — `order(id:)` requesting
exactly: `id name legacyResourceId createdAt processedAt updatedAt
test currencyCode presentmentCurrencyCode taxesIncluded confirmed
closed closedAt cancelledAt cancelReason displayFinancialStatus
displayFulfillmentStatus note tags sourceName email customer { id
firstName lastName displayName defaultEmailAddress { emailAddress }
defaultPhoneNumber { phoneNumber } defaultAddress { address1 address2
city zip provinceCode countryCodeV2 } } billingAddress {
firstName lastName company address1 address2 city zip provinceCode
countryCodeV2 phone } shippingAddress { …same… } totalPriceSet {
shopMoney { amount currencyCode } presentmentMoney { amount
currencyCode } } subtotalPriceSet { …both… } totalTaxSet { …both… }
totalDiscountsSet { …both… } totalShippingPriceSet { …both… }
totalTipReceivedSet { …both… } currentTotalDutiesSet { shopMoney {
amount } } taxLines { title rate ratePercentage priceSet { shopMoney {
amount } } channelLiable } shippingLines(first: 10) { nodes { id title
code custom discountedPriceSet { shopMoney { amount } } taxLines {
title rate priceSet { shopMoney { amount } } } } pageInfo {
hasNextPage } } discountApplications(first: 20) { nodes { allocationMethod
targetSelection targetType } pageInfo { hasNextPage } } lineItems(first:
100) { nodes { id name title quantity currentQuantity sku isGiftCard
requiresShipping taxable variantTitle vendor variant { id }
product { id } originalUnitPriceSet { shopMoney { amount } }
discountedUnitPriceSet { shopMoney { amount } } discountAllocations {
allocatedAmountSet { shopMoney { amount } } discountApplication {
targetType } } taxLines { title rate priceSet { shopMoney { amount } }
channelLiable } customAttributes { key value } } pageInfo { hasNextPage
} }` — >100 line items or >10 shipping lines → hold
(`data_shape_schema_mismatch`), never truncate (Task 010 precedent).
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
component; 100-line high-count case; line + order discounts;
accumulated in-bounds drift accepted; real mismatch rejected at
component level; taxesIncluded variants; JPY zero-decimal and BHD
three-decimal cases; currency-relative cap);
`tests/test_order_tax_resolution.py` (mapping-first resolution;
rate-match second; unmatched → configuration hold naming the pair;
autocreate default-False; opt-in creation + audit line + dedup;
mapping model schema/uniqueness/ACL); `tests/test_order_duplicate_prevention.py` (re-import
no-dup, evidence-refresh-only incl. the **source-level
no-SO-write-on-refresh guard test**, idempotency-key collision,
divergent-currency/duties/test/cancelled skips);
`tests/test_order_customer_resolution.py` (all D-012-5 paths incl.
fallback used/unset, ambiguous hold with candidate JSON, archived-only,
recall-safety reuse). Negative matrix: unmatched product hold+resume;
>100 lines; null tax rate; missing pricelist; sale-domain flag off.
Source-level guards: single `execute()` call via AST (Task 011
pattern); zero mutation strings; zero core/product file edits.
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
ever); guard blocks beyond tolerance, never silent/auto-retried; no
divergent-currency/duties SO under any circumstance; evidence-refresh
never mutates an imported SO; zero payout/refund/invoice/tax-engine/
presentment logic in the diff; suites green locally and on Odoo.sh;
handoff + validation record + AR row appended; draft PR; gate closes on
draft-open. Rollback: revert the single PR — order bindings drop,
`sale.order` records survive as ordinary data; Tasks 013/014 are not
yet started so nothing depends on it. Upgrade note: the two settings
fields and the SOL field are additive (no migration).

## 9–14. Cross-references

Sequencing/master plan: `../08-release-readiness/implementation-ready-master-plan.md`.
UAT scenarios 6/7/8 map to this task. Register impacts on acceptance:
OP-14/15/16/17 → Resolved-by-packet; MBQ-55 order portion → Accepted;
MBQ-56/MBQ-27/DEC-020-residual → Resolved at decision level.

## 15. Locked final implementation prompt (Task 012)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE ORDER-DOMAIN GATE, VERIFIES THE CURRENT BASE SHA,
AND ISSUES THIS PROMPT. (Prerequisites: CORE-R1, Task 010B, and
Task 011B merged runtime-green — the revised critical path.)

You are Claude Code implementing Task 012 — Shopify order import —
in AdamsOdoo/Adams, branch from the CURRENT verified Shopify-connector
tip (STOP if it does not match the SHA ChatGPT states when issuing
this prompt). One session; draft PR; stop.

Read first: docs/07-implementation-plan/task-012-order-import-implementation-packet.md
(the D-012-1..12 decisions — binding once this packet is accepted),
docs/03-architecture/final-mvp-module-and-dependency-architecture.md
§3–§7, docs/00-source-materials/shopify-orders-inventory-fulfillment-product-partner-captures-2026-07-10.md
§2/§8, and the merged shopify_connector_sale/product/core code.

ALLOWED FILES (exhaustive):
  addons/shopify_connector_sale/__manifest__.py           (depends += shopify_connector_product, sale; version bump)
  addons/shopify_connector_sale/models/__init__.py
  addons/shopify_connector_sale/models/shopify_connector_order_binding.py     (NEW)
  addons/shopify_connector_sale/models/shopify_connector_order_importer.py    (NEW — importer service + job seams + REDACTION_EXTENSION)
  addons/shopify_connector_sale/models/shopify_connector_sale_order_line.py   (NEW — shopify_line_item_gid only)
  addons/shopify_connector_sale/models/shopify_connector_store_settings.py    (order_import_confirmation_policy — NO default, unset holds imports; order_import_include_test; order_tax_autocreate — default False; order_company_id; order_pricelist_id; order_sales_team_id; sale_order_last_import_checkpoint_at — inert checkpoint)
  addons/shopify_connector_sale/models/shopify_connector_tax_mapping.py       (NEW — shopify.connector.tax.mapping per D-012-9 step 1)
  addons/shopify_connector_sale/security/ir.model.access.csv                  (binding + tax-mapping rows only)
  addons/shopify_connector_sale/tests/{__init__.py, test_order_binding.py, test_order_import_mapping.py, test_order_totals_guard.py, test_order_tax_resolution.py, test_order_duplicate_prevention.py, test_order_customer_resolution.py}  (NEW)
  addons/shopify_connector_core/models/shopify_connector_job_dispatch.py      (THE ONE NAMED ADDITIVE CORE EDIT — JobPolicySkip exception class + one except-branch in _invoke_handler calling the existing _transition_skipped; nothing else in the file)
  addons/shopify_connector_core/tests/test_job_dispatch.py                    (append the JobPolicySkip routing test only)
  docs/05-qa/task-012-order-import-validation-results.md                      (NEW)
  docs/05-qa/architecture-review-log.md                                       (append one AR row)
  docs/01-research/research-handoff.md                                        (top entry)
FORBIDDEN: every OTHER shopify_connector_core file and every
shopify_connector_product file; adams_base; any view/menu/wizard/
webhook/OAuth/controller/CI/workflow/requirements/Docker file; any
invoice/payment/refund/inventory/fulfillment model or logic; plain
dev; main.

IMPLEMENT exactly per the packet: D-012-1 binding schema (explicit
_name+_inherit, models.Constraint, dual uniqueness); D-012-2 REVISED
component-based guard (lines/taxes/shipping+tip component checks with
the packet's exact tolerance formulas derived from
res.currency.rounding, total check capped at 10 × rounding —
currency-relative, never a fixed unit; rollback +
financial_total_mismatch; JPY and BHD cases in the test matrix);
D-012-3 skipped-by-policy routing (divergent currency, duties, test
orders, pre-cancelled) via the ONE named additive core seam
(JobPolicySkip + except-branch → _transition_skipped) — never a new
error class, no other core change;
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
whole-order-hold mapping_missing on unmatched, discountedUnitPrice +
discount%, custom-item service product, gift-card note); D-012-9
REVISED taxes: mapping-model-first, existing-rate-match second,
unmatched -> configuration hold naming the rate (never silent
creation), order_tax_autocreate default False and admin-gated with
audited creations when explicitly enabled (price_include_override,
null-rate hold);
D-012-10/11 currency/pricelist/company/team resolution and UTC parsing;
D-012-12 evidence-refresh-only re-import (note-type log rows) with the
source-level no-SO-write guard test + the module-local
REDACTION_EXTENSION pre-redaction pass. Single ORDER_IMPORT_QUERY
constant exactly as packet §4 (query-only, first:100 lines / first:10
shipping, hold on hasNextPage). Job type order_import_sync via the
three seams gated on sale_domain_enabled; job targeting
res_model='shopify.connector.store' + shopify_target_gid=<Order GID>
(packet §4 — the documented deviation that keeps operation_scope_key
populated on first import). One savepoint per order. Reuse the existing customer importer functions — do not
duplicate matching logic. All §6 test files with every named case,
incl. negative matrix and source-level guards.

HARD CONSTRAINTS: read-only toward Shopify — zero mutation anywhere;
no blind retry of anything; no new error class; no force/bypass flag;
PII-minimal logs via redact() + REDACTION_EXTENSION; email remains the
sole automatic customer key; VAL-B2 / MBQ-05 / TD-002 / SRR-03/04/09 /
Lite-Full untouched; the claim/dispatch concurrency caveat is restated,
not resolved. Runtime: full Odoo.sh run must be green before merge
review (quote the result verbatim; OP-43 rule). Static: py_compile,
pyflakes, docutils-clean docstrings, AST single-execute guard.

STOP CONDITION: open the PR as DRAFT titled "Task 012: Shopify order
import (shopify_connector_sale)", update handoff + validation record +
AR row, report per the packet's report format, and stop. The
order-domain gate closes the moment the draft PR opens. Do not start
Task 013/014/015, Area 6, UI, webhook, OAuth, packaging, or accounting
work under any circumstance.
```
