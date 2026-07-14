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
> `tol_tax = 0.5r(S+O)` (replacing the invalid `K=distinct groups`), with worked
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
> may need **no** core edit) — D-012-3/§15. The decision-closure §4–§18 is
> authoritative where it and this packet differ.
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
> with explicit tax mapping preferred (D-012-9 revised); (c) the
> total-check tolerance is now component-based (D-012-2 revised);
> (d) prerequisites (this 2026-07-11 list is **superseded by the 2026-07-14
> capability-based prerequisites** at the top of this header and in §2 —
> CORE-R1 is already merged; PR #150/#151 need not merge directly). **Further revised 2026-07-11 per re-review comment
> `4945129824` (items 4a/4b): the tax mapping is keyed on a canonical
> decimal-string rate (`shopify_rate_key`, never a Float) with
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
no fulfillment write-back (Task 014); no inventory logic (Task 013 —
SO confirmation's standard Odoo reservation is not connector inventory
logic); no presentment-currency orders; no tax engine (rate-matching
only, §5); no enumeration/scan triggers (Area 6); no webhooks; no UI
beyond nothing (Error-Center extensions are UI-phase scope); no
`read_all_orders` (60-day default window is the MVP posture — historic
backfill is a documented setup limitation until a separately-approved
scope request).

**Dependency prerequisites — CAPABILITY-BASED (REVISED 2026-07-14, review
`4690680028`; supersedes the earlier direct-merge list):** Tasks 002/003
(client) and 006C (dispatch) merged [facts]; **plus the capabilities below in
`Shopify-connector`, however they arrive** (direct merges of PR #150/#151 **or**
a single subsuming CORE-R2 Slice-2B integration PR — the corrected CORE-R2
strategy stages #150/#151 heads, migrates their product/customer Shopify calls
to `execute_business`, closes the public generic `execute`, passes integrated
suites + three-run multi-worker evidence, then lands one controlled integration
PR; #150/#151 may then close as merged or subsumed):
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

**REBUILT 2026-07-14 (review `4690680028` items 2 & 3) — the canonical
single-count ledger + proven tax bound live in closure §6, authoritative.** In
`Decimal` on `shopMoney` (no intermediate rounding until the single write
boundary, closure §6.2): product merchandise net `M = Σ_i (discountedTotalSet_i
− OC_i)` where `OC_i` = **order-level/code allocations only**
(`discountApplication.targetSelection == ALL` or code-based — exactly what
`discountedTotalSet` excludes; line-level allocations already inside it are
NEVER re-subtracted — no double subtraction, closure §6.1-A/§7); shipping net
`H = Σ_s discountedPriceSet_s` (shipping discounts already netted, not
re-subtracted); tips `T = totalTipReceivedSet` (once). `G = M + H + T`.

1. **Lines:** `|amount_untaxed − U_ex| ≤ tol_lines`, where `U_ex = G` when
   `taxesIncluded=false` and **`U_ex = G − totalTaxSet`** when `taxesIncluded=true`
   (tax-inclusive prices → back out the reported tax exactly once; closure §6.3).
   `tol_lines = 0.5 r L` (tax-excl) or `0.5 r (L + S)` (tax-incl, since `U_ex`
   carries `totalTaxSet`'s `S` roundings); `L` = Odoo untaxed-contributing lines
   (product + shipping + tip + adjustment). Discounts are **exact by
   construction** — native `discount %` only when faithful to `0.5r`, else an
   exact negative **tax-preserving** adjustment line inheriting the source line's
   `tax_ids` + `price_include_override` (or one per tax signature); a no-tax
   residual only for genuinely untaxed lines; an inconsistent allocation →
   `financial_total_mismatch` (closure §7).
2. **Taxes:** `|amount_tax − totalTaxSet.shopMoney| ≤ tol_tax = 0.5 r (S + O)`.
   **REBUILT (review item 3):** `S` = Shopify per-line/per-shipping tax rounding
   events (`Σ|taxLines_i| + Σ|taxLines_s|`); `O` = Odoo tax rounding events under
   the actual `res.company.tax_calculation_rounding_method` — distinct global
   tax/repartition groups under `round_globally` (the Odoo-19 default), or taxed
   line×tax pairs under `round_per_line`. **Proof (closure §6.4):** both
   `totalTaxSet` and `amount_tax` are roundings of the same exact tax `Θ`, so by
   the triangle inequality `|amount_tax − totalTaxSet| ≤ 0.5rS + 0.5rO`. The old
   `K = distinct tax groups` bound **omitted the `S` term** and false-rejects a
   many-small-line order under `round_globally` (closure Example I). A loose
   `tol_tax` cannot hide a missing/wrong line — merchandise shifts are caught by
   the tight `tol_lines`, and wrong rates by the canonical-key mapping.
3. **Total:** `|amount_total − totalPriceSet.shopMoney| ≤ tol_lines + tol_tax`
   — the **sum of the proven per-component bounds**, with **no** fixed or
   currency-relative cap. A mandatory **ledger self-check** also requires
   `|Total_ex − totalPriceSet| ≤ tol_total` where `Total_ex = U_ex + totalTaxSet`
   (catches any `OC`-classification error before the order is trusted; closure
   §6.1-F). A missing/wrong line shifts a subtotal far beyond `0.5r` and is
   rejected at the lines and total level.

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
three-decimal-currency store is onboarded. **Added 2026-07-14 (review
item 3):** an **adversarial many-small-lines / one-group / `round_globally`
counterexample** (closure Example I) that the proven `tol_tax = 0.5r(S+O)`
accepts while `K=distinct groups` would false-reject — and a missing line in
the same order still rejected by the tight lines component; **fully worked
tax-inclusive** ordinary and order-discount cases (closure Examples G/H);
multiple taxes on one line; multiple global groups; shipping-tax rounding;
line-level allocation not double-subtracted; order-level allocation subtracted
once; shipping discount not double-subtracted; ambiguous (>1) tax candidate →
hold; tax company mismatch → rejected.

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
class, `skip_reason` label; permitted skips are the closed set:
`divergent_presentment_currency`, `unsupported_duties`, `test_order_excluded`,
`order_pre_cancelled`). Rationale: an eligibility/policy block is not a
failure — the 16-class error registry stays intact (no 17th class) and DEC-020's
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
discounts baked in — captures §2); **order-level/code discount
allocations** (from `discountAllocations`) are applied per line by the
**faithful-representation rule (D-012-2):** the allocation is written
to the Odoo `discount` % field **only when** that percentage,
quantized to the Discount precision (2 dp default), reproduces the
exact allocated amount for the line to within `0.5r`; when it cannot
(typically high-value lines, where a 2-dp % cannot hit the cent), the
allocation is instead carried by an explicit negative **"Shopify Order
Discount"** service line (auto-provisioned per store,
`default_code SHOPIFY-ORDER-DISCOUNT`, `price_unit` = the exact
negative residual amount) so the SO total reconciles exactly
rather than relying on tolerance slack. **Tax treatment of the residual
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

**D-012-9 — Shipping, tips, taxes (MBQ-27 closure; OP-17).**
Shipping: one SO line per `shippingLines` node (paginated connection —
`first: 50`, fully looped on `hasNextPage`/`endCursor` per §4, never
truncated), service product
"Shopify Shipping" (auto-provisioned, per store), `price_unit =
discountedPriceSet.shopMoney.amount`, its `taxLines` mapped per T-B.
Tips: `totalTipReceivedSet > 0` → one line, service product "Shopify
Tip", no taxes. Duties: D-012-3 skip. **Taxes — proposed mechanism
T-B ("mapped-or-matched Odoo taxes under the guard") — REVISED
2026-07-11 (review item 6b): ordinary order import must never
silently create accounting configuration.** Resolution order for
each distinct `TaxLine` on a line/shipping line:

1. **Explicit tax mapping (preferred):** new model
   `shopify.connector.tax.mapping` (store_id; **`shopify_rate_key`
   Char** — the **canonical decimal-string percentage key, not a
   Float**; `price_include` Boolean; `account_tax_id` M2o `account.tax`
   required restrict; **UNIQUE(store_id, shopify_rate_key,
   price_include)** on the canonical key). **Rate-unit pinning +
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
2. **Existing-tax rate match:** candidate filter (**SAFETY — REVISED
   2026-07-14, review `4690680028`; closure §5.5**): `account.tax` with
   **`company_id == order_company_id`**, `type_tax_use='sale'`,
   **`active`**, `amount_type='percent'`, and `price_include_override`
   matching `Order.taxesIncluded` (the 19.0-correct inclusion field —
   `price_include` is compute-only). **Ambiguity is never resolved
   silently:** **zero** candidates → configuration hold; **more than one**
   → **ambiguous** configuration hold naming all candidates; the first is
   **never** chosen. The **fiscal-position result is validated** — after
   Odoo's `fiscal_position.map_tax(...)`, the connector re-checks the mapped
   tax still satisfies the rate/inclusion/company invariants, else holds.
   **Decimal framing (correction):** the canonical **decimal-string** key is
   the identity/evidence layer; the candidate's `account.tax.amount` is a
   genuine Odoo `Float(16,4)`, so `float_compare(tax.amount, rate_percent,
   precision_digits=6) == 0` is only the **boundary comparison to that
   existing Float field** — it does **not** "preserve Shopify Decimal
   precision." Attach via `tax_ids`.
   **Company-scope decision (documented):** the mapping model keeps `store_id`
   (no redundant `company_id` column); safety = an `@api.constrains` that
   `account_tax_id.company_id == store_id.order_company_id` at mapping
   create/write **+** `order_company_id` immutability once any order binding
   or tax mapping exists **+** the resolution-time company re-check above —
   equivalent structural safety without duplicating derivable data.
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

**REVISED 2026-07-14 (Option A, closure §4.2): the single-constant
`ORDER_IMPORT_QUERY` is replaced by four query constants — `ORDER_HEADER_QUERY`
(the field set below, including the first page of each of the three
connections) plus `ORDER_LINE_ITEMS_PAGE_QUERY` /
`ORDER_SHIPPING_LINES_PAGE_QUERY` / `ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY`
(each advancing one connection by `after:$cursor`, re-fetching `id`+`updatedAt`
for verification).** The header field set — `order(id:)` requesting
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
amount } } channelLiable } shippingLines(first: 50) { nodes { id title
code custom discountedPriceSet { shopMoney { amount } } taxLines {
title rate ratePercentage priceSet { shopMoney { amount } } } } pageInfo {
hasNextPage endCursor } } discountApplications(first: 50) { nodes { __typename index allocationMethod
targetSelection targetType } pageInfo { hasNextPage endCursor } } lineItems(first:
100) { nodes { id name title quantity currentQuantity sku isGiftCard
requiresShipping taxable variantTitle vendor variant { id }
product { id } originalUnitPriceSet { shopMoney { amount } } originalTotalSet { shopMoney { amount } }
discountedUnitPriceSet { shopMoney { amount } } discountedTotalSet { shopMoney { amount } } discountAllocations {
allocatedAmountSet { shopMoney { amount } } discountApplication {
__typename targetType targetSelection ... on DiscountCodeApplication { code } } } taxLines { title rate ratePercentage priceSet { shopMoney { amount } }
channelLiable } customAttributes { key value } } pageInfo { hasNextPage
endCursor } }`. **Pagination — REBUILT 2026-07-14 (review `4690680028` item 4;
closure §4.2), Option A: separate query constants with independent cursors.**
`ORDER_HEADER_QUERY` fetches scalars + all money sets + order-level `taxLines`
+ customer/addresses + the **first page** of each of the three connections
(with `pageInfo{hasNextPage endCursor}`), capturing `id` and the initial
`updatedAt` (`updatedAt₀`); `ORDER_LINE_ITEMS_PAGE_QUERY`,
`ORDER_SHIPPING_LINES_PAGE_QUERY`, `ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY`
advance **one connection each** by `after: endCursor` (the header first-pages
are never re-fetched → no first-page duplication). Every page (via
`execute_business`) verifies `Order.id == GID` and `updatedAt == updatedAt₀`
(a change → **torn read** → `concurrency_race_conflict` AUTO_RETRY, lease
released, no SO/binding), requires `pageInfo` (and `endCursor` when
`hasNextPage`), enforces **cursor progress** (repeated/empty cursor →
`data_shape_schema_mismatch`), **dedups node ids/indexes** (duplicate →
`data_shape_schema_mismatch`), and an **independent per-connection page ceiling**
(`LINE_ITEMS_PAGE_LIMIT` / `SHIPPING_LINES_PAGE_LIMIT` /
`DISCOUNT_APPLICATIONS_PAGE_LIMIT` — named provisional defaults) → exceed →
`data_shape_schema_mismatch` naming the ceiling. **No Odoo business write occurs
until all three connections are fully collected and validated.** Page sizes
(`first:100`/`first:50`) are **named provisional defaults — NOT asserted "well
under" the 1,000-point cap**; the importer captures `requestedQueryCost` /
`actualQueryCost` from `extensions` + `throttleStatus` (never the raw payload),
does not auto-expand, and requires authorized dev-store live-read cost evidence
before production tuning (closure §4.3). `discountAllocations`/`taxLines`/
`customAttributes` and `Order.taxLines` are plain lists (no nested pagination).
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
cap relied upon**);
`tests/test_order_tax_resolution.py` (mapping-first resolution;
rate-match second via **decimal-safe comparison**; **rate-unit pinning —
the query carries both `rate` and `ratePercentage`; the canonical key
derives from `ratePercentage`; `rate × 100 == ratePercentage` is
verified and a deliberate `rate`/`ratePercentage` disagreement → schema
hold; a bare-`0.05` ambiguity never silently keyed**; **canonical-key
equivalence — `ratePercentage` `5.0`, `5.00`, `5.000` all resolve to one
mapping row; a fractional / `>2`-decimal percentage (`8.375`) keys and
matches exactly; included- vs excluded-tax (`price_include`) variants
key and resolve independently**; **null/empty `rate` or `ratePercentage`
→ `data_shape_schema_mismatch` hold**; unmatched → configuration hold
naming the pair; autocreate default-False; opt-in creation + audit line +
dedup; mapping model schema/uniqueness/ACL on the canonical key);
`tests/test_order_duplicate_prevention.py` (re-import
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
this prompt may be issued (CORRECTED 2026-07-14, review 4690680028; these are
capabilities, not specific PR merges — they may arrive via direct merges of
PR #150/#151 OR via one subsuming CORE-R2 Slice-2B integration PR):
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
  addons/shopify_connector_sale/models/shopify_connector_store_settings.py    (order_import_confirmation_policy — NO default, unset holds imports; order_import_include_test; order_tax_autocreate — default False; order_company_id; order_pricelist_id; order_sales_team_id; sale_order_last_import_checkpoint_at — inert checkpoint)
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
the binding); D-012-2 REBUILT guard (closure §6, authoritative) — the
canonical single-count Decimal ledger U_ex = M + H + T, with M =
Sum_i(discountedTotalSet_i - OC_i) where OC_i is order-level/code allocations
ONLY (targetSelection==ALL or DiscountCodeApplication — exactly what
discountedTotalSet excludes; line-level allocations are NEVER re-subtracted =
no double subtraction), H = Sum shippingLines.discountedPriceSet (shipping
discounts not re-subtracted), T = totalTipReceivedSet once;
taxesIncluded=true -> U_ex = G - totalTaxSet (back out tax exactly once);
lines tol = 0.5r*L (tax-excl) or 0.5r*(L+S) (tax-incl); TAX tol = 0.5r*(S+O),
PROVEN via triangle inequality (S = Shopify per-line tax rounding events; O =
Odoo tax rounding events under the ACTUAL tax_calculation_rounding_method:
distinct groups under round_globally [Odoo-19 default], line×tax pairs under
round_per_line) — the old K=distinct-groups bound is WITHDRAWN (omits S,
false-rejects the many-small-lines counterexample); total tol = lines+tax,
NO cap; a ledger self-check (Total_ex==totalPriceSet) catches OC
misclassification; order-level allocations -> native discount % only when
faithful to 0.5r, else an exact negative TAX-PRESERVING adjustment line that
INHERITS the source line's tax_ids and price_include_override (or one per tax
signature) — never a universal no-tax residual for a taxable line; an
inconsistent allocation -> REJECTED (financial_total_mismatch), never
absorbed; do all source arithmetic in Decimal with ONE Decimal->Odoo write
boundary; test matrix incl. the many-small-lines/global-rounding
counterexample and the fully worked tax-inclusive cases;
D-012-3 skipped-by-policy routing (divergent currency, duties, test orders,
pre-cancelled — the closed skip_reason set) via the CONDITIONAL core skip
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
whole-order-hold mapping_missing on unmatched, discountedUnitPrice +
discount%, custom-item service product, gift-card note); D-012-9
REVISED taxes: RATE-UNIT PINNING — the query requests BOTH TaxLine.rate
(decimal proportion) and TaxLine.ratePercentage (percentage); the
CANONICAL key derives from ratePercentage (Decimal-parsed, quantized to
6 dp, never a Float); the connector verifies rate × 100 ==
ratePercentage within 6-dp precision and routes any disagreement or
null/empty to a data_shape_schema_mismatch hold (never key a bare
0.05 whose unit is ambiguous); mapping-model-first on shopify_rate_key
(UNIQUE(store_id, shopify_rate_key, price_include)),
existing-rate-match second with SAFETY (closure §5.5): candidate must have
company_id==order_company_id, active, type_tax_use='sale',
amount_type='percent', price_include_override matching taxesIncluded; validate
the fiscal-position map_tax result; ZERO candidates -> configuration hold,
>1 -> AMBIGUOUS configuration hold, first never chosen silently; the
Decimal/string canonical key is the IDENTITY layer and float_compare is ONLY
the boundary comparison to Odoo's existing Float amount (do NOT claim
float_compare preserves Decimal precision); mapping model keeps store_id with
an @api.constrains that account_tax_id.company_id==store_id.order_company_id
plus order_company_id immutability once bindings/mappings exist; unmatched ->
configuration hold naming the rate (never silent creation),
order_tax_autocreate default False and admin-gated with audited
creations when explicitly enabled (price_include_override, null-rate
hold);
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
(endCursor when hasNextPage), enforces cursor progress + node-id/index dedup,
independent per-connection page ceilings (LINE_ITEMS/SHIPPING_LINES/
DISCOUNT_APPLICATIONS_PAGE_LIMIT, named provisional defaults) -> exceed ->
data_shape_schema_mismatch naming the ceiling; NO Odoo write until all three
connections are collected+validated; cursors never persisted; the query also
requests originalTotalSet, discountedTotalSet and discountApplication
__typename/targetSelection (+ code) for the OC classification; page sizes
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
inside `with execute_business(job, store, query, variables)`;
PII-minimal logs via redact() + REDACTION_EXTENSION; NO raw GraphQL payload
or token persisted anywhere; email remains the
sole automatic customer key (RA-006); existing partners' own fields never
mutated (only invoice/delivery child rows added); VAL-B2 / MBQ-05 / TD-002 /
SRR-03/04/09 / Lite-Full untouched; the claim/dispatch concurrency caveat and
the SRR-03/disconnect race are restated, not resolved (Task 012 does NOT wire
ShopifyQuiescedError->skipped — that is a later CORE-R2 slice). Runtime: full
Odoo.sh run must be green before merge
review (quote the result verbatim; OP-43 rule). Static: py_compile,
pyflakes, docutils-clean docstrings, AST single-execute guard.

STOP CONDITION: open the PR as DRAFT titled "Task 012: Shopify order
import (shopify_connector_sale)", update handoff + validation record +
AR row, report per the packet's report format, and stop. The
order-domain gate closes the moment the draft PR opens. Do not start
Task 013/014/015, Area 6, UI, webhook, OAuth, packaging, or accounting
work under any circumstance.
```
