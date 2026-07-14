# Task 012 — Order Import: Final Pre-Implementation Decision Closure

> **Status: Proposed for ChatGPT control-room review. NOT accepted.
> Documentation and architecture only.** This document opens **no gate**,
> authorizes **no code**, and describes **no live Shopify request**. It
> exists to make Task 012 (Shopify order import into Odoo `sale.order`)
> *decision-complete* so that a separate control-room gate can issue the
> locked prompt (packet §15) immediately after its prerequisites merge.
>
> **Prerequisites are capability-based, not PR-merge-based (corrected
> 2026-07-14 per control-room review `4690680028` and the revised CORE-R2
> Slice-2B integration-staging strategy — see §0):** SRR-03 CLOSED; the
> protected, `execute_business`-guarded product import + complete
> product/variant bindings present in `Shopify-connector`; the protected,
> guarded customer import + indexed normalized-email matching present in
> `Shopify-connector`; no unguarded product/customer Shopify call remaining;
> LC-1 merged and DEC-030 accepted. CORE-R1 is **already merged** (satisfied
> historical foundation, not a pending dependency). Whether PR #150 / #151
> land as direct merges or are subsumed by a single controlled CORE-R2
> integration PR is **immaterial** to Task 012 — Task 012 depends on the
> *capabilities*, however they arrive. Producing this closure changes the
> state of no PR (#150, #151, #158, #160) and opens no gate.
>
> Companion files: the implementation packet
> [`../07-implementation-plan/task-012-order-import-implementation-packet.md`](../07-implementation-plan/task-012-order-import-implementation-packet.md)
> (carries the D-012-1…12 decisions and the locked prompt) and the
> proposed-scope brief
> [`../07-implementation-plan/task-012-order-import-proposed.md`](../07-implementation-plan/task-012-order-import-proposed.md).
> This closure **supersedes** the packet where they differ; the packet is
> updated in the same PR to match (money-storage type, financial ledger,
> tax-rounding bound, pagination design, GraphQL-cost posture,
> tax-mapping safety, divergent-currency skip seam).

---

## 0. Verified state at closure time (2026-07-14)

| Item | Required | Verified state | Class |
| --- | --- | --- | --- |
| `Shopify-connector` tip | `912801508155c6358e8f5f1a7a0aaf01ae573675` | `origin/Shopify-connector` HEAD = `9128015…573675` (this branch is based on it) | [Fact — repo] |
| PR #159 (this PR) | open, draft, unmerged | `state:open, draft:true, merged:false`; head `62234c9…`; base `912801…573675` | [Fact — repo] |
| PR #150 (Task 011B) | not modified | left as-is (open/draft) — **not a direct-merge prerequisite** (see below) | [Fact — repo] |
| PR #151 (Task 010B) | not modified | left as-is (open/draft) — **not a direct-merge prerequisite** | [Fact — repo] |
| CORE-R2 / SRR-03 | remediation open | Foundation Slice 1 merged; **SRR-03 remains OPEN**; Slice 2A (PR #160) and Slice-2B packet (PR #158) draft/unmerged & under correction | [Fact — repo] |
| CORE-R1 | already merged | **satisfied historical foundation** (stores reach `connected`) — not a pending dependency | [Fact — repo] |
| Task LC-1 | not merged | design-only; DEC-030 unaccepted | [Fact — repo] |
| Working tree | clean | clean | [Fact — repo] |

### 0.1 Corrected dependency contract (capability-based)

**[Accepted decision — control-room review `4690680028`]** The earlier
"PR #150 and PR #151 must be **merged directly** into `Shopify-connector`
before Task 012" requirement is **withdrawn**. The corrected CORE-R2
Slice-2B strategy does **not** permit those unguarded domain handlers to
enter `Shopify-connector` first. The integration sequence is:

1. CORE-R2 **Slice 2A** becomes runtime-green and merges.
2. The PR #150 and PR #151 heads are integrated into a **dedicated staging
   branch**.
3. Their product/customer Shopify calls are **migrated to `execute_business`**.
4. The public generic `execute` entry point is **closed**.
5. Integrated core/product/sale suites **and** three-run deployed
   multi-worker evidence pass.
6. **One controlled integration PR** enters `Shopify-connector`.
7. PR #150 / #151 may then be **closed as merged or subsumed**.

**Task 012 prerequisites are therefore capability-based (however the
capabilities arrive):**

- **SRR-03 CLOSED** (disconnect quiescence proven runtime-green; register
  forbids merging/enabling/live-validating any Shopify-calling domain handler
  until then — parallel *development* is allowed);
- **protected product import + complete product/variant bindings merged into
  `Shopify-connector`** (order lines resolve; product Shopify calls guarded);
- **protected customer import + indexed normalized-email matching merged into
  `Shopify-connector`** (guest path reuses the indexed lookup at volume;
  customer Shopify calls guarded);
- **no unguarded product/customer Shopify call remains** (the public generic
  `execute` entry is closed; all domain Shopify calls go through
  `execute_business`);
- **LC-1 merged and DEC-030 accepted** (the `job_type` `ondelete`
  reassignment callable exists in core).

**CORE-R1 is already merged** and is recorded as a **satisfied historical
foundation**, not an unmet prerequisite.

**Consequence [Accepted decision / CLAUDE.md §5]:** Task 012 code cannot be
written or its live validation run until the capability prerequisites above
hold in `Shopify-connector`. This closure is *planning* work permitted under
the research/governance phase; it is not an implementation authorization, and
it modifies no other PR (#150, #151, #158, #160).

**Merged CORE-R2 primitives Task 012 may rely on [Fact — repo code]:**
`execute_business(job, store, query, variables=None)` context-manager
admission (`shopify_connector_api_client.py`); the `shopify.connector.call.lease`
row; the `expected_connection_generation` gate captured at enqueue
(`shopify_connector_job_enqueue.py:51`); `job._transition_skipped(...)` and the
terminal `skipped` state (`shopify_connector_job.py`); `operation_scope_key`
and `idempotency_key` (`shopify_connector_job.py`); `redact()` + `extra_secrets`
(`tools/redaction.py`); `JobLog._system_append` (`shopify_connector_job_log.py`).
**Merged CORE-R2 gaps Task 012 must NOT assume closed [Fact — repo code]:**
no `disconnecting` state; `connection_generation` is never bumped yet (all
stores stay at generation 0, so the generation gate cannot fire live); the
dispatcher does **not** map `ShopifyQuiescedError` to `skipped` (a bare one
routes to `unknown_system_error`). These belong to later CORE-R2 slices, not
to Task 012.

---

## 1. Claim-classification legend (applied throughout)

Every load-bearing statement is labelled with exactly one class (CLAUDE.md §8):

- **[Fact — official]** — verified against a cited official Shopify or Odoo
  source (URL + access status in §2).
- **[Fact — repo code]** — verified against merged code or an accepted
  decision record in this repository.
- **[Accepted decision]** — an accepted DEC/AR already binding on the project.
- **[Proposed Task 012 decision]** — a choice this closure proposes; it
  becomes binding only on control-room acceptance. **Never treat these as
  accepted.**
- **[Recommendation]** — a suggested course tied to facts, weaker than a
  proposed decision.
- **[Open question]** — unresolved; logged so it is not lost.
- **[Deferred / non-MVP]** — explicitly out of Phase 1 scope.

A **[Recommendation]** is never silently promoted to a **[Proposed Task 012
decision]**, and a **[Proposed Task 012 decision]** is never presented as an
**[Accepted decision]**.

---

## 2. Official sources used (all accessed 2026-07-14)

| Source | Access | Key facts drawn |
| --- | --- | --- |
| shopify.dev …/2026-07/objects/Order | Accessible | Order field types + nullability; `taxesIncluded`, `currencyCode`/`presentmentCurrencyCode` (non-null); `displayFinancialStatus` nullable; `taxLines` is a plain list |
| shopify.dev …/2026-07/objects/MoneyBag, /MoneyV2 | Accessible | `MoneyBag{shopMoney:MoneyV2!, presentmentMoney:MoneyV2!}`; `MoneyV2{amount:Decimal!, currencyCode:CurrencyCode!}` |
| shopify.dev …/2026-07/scalars/Decimal | Accessible | *"A signed decimal number, which supports arbitrary precision and is serialized as a string."* |
| shopify.dev …/2026-07/scalars/UnsignedInt64 | Accessible | *"…values between 0 and 2^64 − 1 encoded as a string of base-10 digits."* |
| shopify.dev …/2026-07/objects/TaxLine | Accessible | `rate:Float`(decimal proportion, nullable), `ratePercentage:Float`(percentage, nullable), `priceSet:MoneyBag!` = tax *"after discounts and before returns"*, `channelLiable:Boolean`(nullable) |
| shopify.dev …/2026-07/objects/LineItem (re-verified 2026-07-14) | Accessible | `quantity`(ordered incl. refunded/removed) vs `currentQuantity`(excl.); `variant`/`product` nullable; **`originalTotalSet`** = gross line total, no discounts; **`discountedTotalSet`** *"doesn't include order-level discounts. Code-based discounts aren't included by default"*; `discountedUnitPriceSet` excludes order-level/code discounts; `discountAllocations`/`taxLines`/`customAttributes` are plain lists |
| shopify.dev …/2026-07/interfaces/DiscountApplication + /objects/DiscountAllocation (re-verified 2026-07-14) | Accessible | `allocationMethod`(ACROSS/EACH), `targetSelection`(ALL/ENTITLED/EXPLICIT), `targetType`(LINE_ITEM/SHIPPING_LINE); code-based = `DiscountCodeApplication`; used for the `OC` line-vs-order classification (§6.1-A/§7); `DiscountAllocation.allocatedAmountSet:MoneyBag!` |
| shopify.dev …/2026-07/objects/ShippingLine, /MailingAddress | Accessible | ShippingLine `discountedPriceSet`, own `taxLines`; MailingAddress fields (all nullable String except `countryCodeV2:CountryCode`) |
| shopify.dev …/usage/limits, /access-scopes, /pagination-graphql | Accessible | leaky-bucket cost model; single-query cap **1,000 points**; `throttleStatus{maximumAvailable,currentlyAvailable,restoreRate}`; `200 Throttled`; `read_orders`+`read_customers`; `read_all_orders` approval-gated; **last-60-days** default order window; page size max **250** |
| shopify.dev changelog: 60-day order access | Accessible | *"public apps will no longer be able to access a merchant's orders older than 60 days with the current `read_orders` or `write_orders` access scopes"* |
| raw.githubusercontent.com/odoo/odoo/19.0 addons/sale/models/sale_order.py, sale_order_line.py | Accessible | `partner_id` required; `partner_invoice_id`/`partner_shipping_id` writable computes; `currency_id` compute-only (pricelist→company); `fiscal_position_id` + line `tax_ids` via `map_tax`; `discount` = "Discount (%)"; `price_tax` compute-only |
| raw.githubusercontent.com/odoo/odoo/19.0 addons/account/models/account_tax.py, company.py | Accessible | `amount_type∈{group,fixed,percent,division}`, `amount:Float(16,4)`; `price_include_override∈{tax_included,tax_excluded}` writable, `price_include` compute-only; `res.company.tax_calculation_rounding_method` default **`round_globally`** |
| raw.githubusercontent.com/odoo/odoo/19.0 odoo/addons/base/models/res_currency.py | Accessible | `rounding:Float(12,6) default 0.01`; `decimal_places = ceil(log10(1/rounding))`; `round/compare_amounts/is_zero` use `float_round/float_compare/float_is_zero(precision_rounding=rounding)` |
| raw.githubusercontent.com/odoo/odoo/19.0 addons/sale_stock/__manifest__.py | Accessible | `depends:['sale','stock_account']`, `auto_install:True` |
| raw.githubusercontent.com/odoo/odoo/19.0 odoo/addons/base/models/res_partner.py | Accessible | `type∈{contact,invoice,delivery,other}`; `parent_id`/`child_ids`/`commercial_partner_id`; `address_get()` DFS |
| Repo captures (`../00-source-materials/…captures-2026-07-10.md`, `…-2026-07-11.md`) | N/A (repo) | Corroborating prior official captures (money, tax, currency, sale_stock, ISO 4217 minor units) |

**Blocked / undocumented (logged, not asserted):** the verbatim GraphQL
error code string `THROTTLED` in `errors[].extensions.code` (docs show only
`200 Throttled`) — **[Open question]**; Shopify's storage/rounding policy for
three-decimal currencies (BHD/KWD/OMR/TND) is officially undocumented
(captures §11) — **[Open question]**, mitigated by a named dev-store empirical
check (§5, §6); Shopify GraphQL cursor durability across sessions is
undocumented — **[Fact — official, by absence]** ⇒ cursors are never persisted.

---

## 3. Order-binding schema — final proposed field table (task §4)

**[Proposed Task 012 decision — revises packet D-012-1].** Model
`shopify.connector.order.binding` (class `ShopifyConnectorOrderBinding`, file
`shopify_connector_order_binding.py`), `_name` + `_inherit
'shopify.connector.binding.mixin'`, following the merged binding precedent
(`../03-architecture/final-mvp-module-and-dependency-architecture.md` §3).

### 3.1 The lossless-money decision (resolves adversarial finding #1)

**[Fact — official]** Shopify `MoneyV2.amount` is the `Decimal!` scalar,
*"serialized as a string"* with *"arbitrary precision"*; `legacyResourceId`
is `UnsignedInt64` (*"encoded as a string of base-10 digits"*). **[Proposed
Task 012 decision]** Therefore **every Shopify money snapshot stored on the
binding is a `Char` holding the exact Shopify decimal string**, never an Odoo
`Float` (IEEE-754 double is lossy for decimal fractions) and never a
`Monetary` (which rounds to a paired currency's `decimal_places` on write and
so conflates *"what Shopify reported"* with *"what Odoo would round it to"*).
All guard arithmetic parses these Char strings with Python `decimal.Decimal`.
`legacyResourceId` is likewise `Char`. The **operational** money lives on the
real `sale.order` in Odoo's native `Monetary`/`Float` fields (Odoo owns those);
the guard reconciles Odoo's rounded operational figures against the lossless
Shopify evidence within the currency-rounding tolerance (§6). This is the
single most important correction to packet D-012-1, which stored
`shopify_order_total` as `Float`.

Both `shopMoney` and `presentmentMoney` totals are captured **in every case**
(DEC-020 mandatory audit), so the binding carries paired snapshots for the
order total.

### 3.2 Final field table

| Field | Odoo type | Req | RO | Index | Precision | ondelete | Shopify source | Purpose | Privacy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `store_id` (mixin) | Many2one `shopify.connector.store` | ✔ | — | ✔ | — | cascade | — | store scope / isolation | Low |
| `shopify_gid` (mixin) | Char | ✔ | ✔ | ✔ | — | — | `Order.id` (GID) | Shopify order identity; sole idempotency anchor half | Low |
| `sale_order_id` | Many2one `sale.order` | ✔ | — | ✔ | — | **restrict** | (Odoo link) | the imported SO | Low |
| `shopify_order_name` | Char | — | ✔ | — | — | — | `Order.name` | human order no. (e.g. `#1001`) | Low |
| `shopify_legacy_resource_id` | Char | — | ✔ | ✔ | string int | — | `Order.legacyResourceId` (`UnsignedInt64`) | legacy REST id — Char, never Integer (2^64 range) | Low |
| `shopify_processed_at` | Datetime | — | ✔ | — | — | — | `Order.processedAt` | processed time (naive-UTC) | Low |
| `shopify_updated_at_snapshot` | Datetime | — | ✔ | — | — | — | `Order.updatedAt` | last-updated snapshot; `idempotency_key` payload source | Low |
| `shopify_created_at` | Datetime | — | ✔ | — | — | — | `Order.createdAt` | order creation time (audit) | Low |
| `shopify_currency_code` | Char (3) | — | ✔ | — | ISO 4217 | — | `Order.currencyCode` | shop currency | Low |
| `shopify_presentment_currency_code` | Char (3) | — | ✔ | — | ISO 4217 | — | `Order.presentmentCurrencyCode` | presentment currency; divergence check + audit | Low |
| `shopify_taxes_included` | Boolean | — | ✔ | — | — | — | `Order.taxesIncluded` | tax-inclusive pricing flag | Low |
| `shopify_financial_status_snapshot` | Char | — | ✔ | — | raw enum | — | `Order.displayFinancialStatus` (nullable → `False`) | financial status snapshot | Low |
| `shopify_fulfillment_status_snapshot` | Char | — | ✔ | — | raw enum | — | `Order.displayFulfillmentStatus` (non-null) | fulfillment status snapshot | Low |
| `shopify_cancelled_at` | Datetime | — | ✔ | — | — | — | `Order.cancelledAt` (nullable) | cancellation time; null = not cancelled | Low |
| `shopify_cancel_reason` | Char | — | ✔ | — | raw enum | — | `Order.cancelReason` (nullable) | cancel reason (audit) | Low |
| `shopify_order_total_amount` | **Char** | — | ✔ | — | exact decimal string | — | `Order.totalPriceSet.shopMoney.amount` | **lossless** total (shop) — guard comparand | Low |
| `shopify_order_total_presentment` | **Char** | — | ✔ | — | exact decimal string | — | `Order.totalPriceSet.presentmentMoney.amount` | **lossless** total (presentment) — DEC-020 audit | Low |
| `shopify_subtotal_amount` | Char | — | ✔ | — | exact decimal | — | `Order.subtotalPriceSet.shopMoney.amount` (nullable) | lossless subtotal evidence | Low |
| `shopify_total_tax_amount` | Char | — | ✔ | — | exact decimal | — | `Order.totalTaxSet.shopMoney.amount` (nullable) | lossless tax total — guard comparand | Low |
| `shopify_total_discounts_amount` | Char | — | ✔ | — | exact decimal | — | `Order.totalDiscountsSet.shopMoney.amount` (nullable) | lossless discount total evidence | Low |
| `shopify_total_shipping_amount` | Char | — | ✔ | — | exact decimal | — | `Order.totalShippingPriceSet.shopMoney.amount` | lossless shipping total evidence | Low |
| `shopify_total_tip_amount` | Char | — | ✔ | — | exact decimal | — | `Order.totalTipReceivedSet.shopMoney.amount` | lossless tip total evidence | Low |
| `customer_resolution` | Selection | — | ✔ | — | — | — | (audit) | how the partner was resolved (values below) | Low (audit) |
| `shopify_last_imported_at` | Datetime | — | ✔ | — | — | — | (audit) | first successful import timestamp | Low |
| `shopify_last_evidence_refresh_at` | Datetime | — | ✔ | — | — | — | (audit) | last `ORDERS_UPDATED` evidence-refresh timestamp | Low |

`customer_resolution` Selection values (readonly audit marker, exactly as Task
011 consumption requires): `existing_binding` / `email_match` / `created` /
`guest_email_match` / `guest_created` / `fallback` / `manual`.

### 3.3 Constraints, ondelete posture, isolation, line traceability

- **Uniqueness [Proposed Task 012 decision]:** `models.Constraint`
  `UNIQUE(store_id, shopify_gid)` (mixin) **and** `UNIQUE(store_id,
  sale_order_id)`. Dual uniqueness = the sole idempotency anchor (§9); a
  repeated webhook/scan collides on `(store, order GID)` and never re-creates.
- **`match_key` values used:** `existing_binding` / `manual` **only** — orders
  are never auto-matched to a pre-existing `sale.order`; import always creates
  a new SO (DEC-014 sync matrix: *"Never auto-matched to pre-existing SOs"*).
- **ondelete posture [Proposed Task 012 decision]:** `sale_order_id
  ondelete='restrict'` — the business `sale.order` is never dropped by deleting
  a binding, and a bound SO cannot be silently removed. `store_id` cascades
  (mixin default). On module uninstall Odoo deletes the binding rows (platform
  behaviour, DEC-030) but every `sale.order` survives as ordinary Odoo data,
  simply un-bound (§14, rollback).
- **Store / company isolation [Proposed Task 012 decision]:** all reads/writes
  are `store_id`-scoped; the SO's `company_id` is the store-settings
  `order_company_id` (§8) — no cross-store or cross-company leakage.
- **Order-line traceability [Accepted decision — DEC-013 granularity bound]:**
  **no** order-line binding model. `sale.order.line` gains one indexed readonly
  `Char shopify_line_item_gid` via `_inherit` — a reference/audit field, *not* a
  binding model (flagged per architecture §3). Line→product resolution goes
  through the **product-variant binding**, not a line binding.
- **Privacy boundary [Proposed Task 012 decision]:** the binding stores **no
  customer name, email, phone, or address** — customer PII lives on
  `res.partner` (Task 011). The binding holds only order metadata, money
  strings, currency codes, and status snapshots. This keeps the binding at the
  **Low** privacy tier and confines PII to the partner records SEC-1 will
  harden.

**Field-by-field challenge (task §4) — every field survives:** money → Char
(lossless, §3.1); `UnsignedInt64` legacy id → Char; currency codes → Char(3);
processed/updated/created timestamps → Datetime (naive-UTC); nullable financial
status → Char stored `False` when null; fulfillment status → Char (non-null
source); cancelled state → `shopify_cancelled_at` + `shopify_cancel_reason`;
order-name snapshot → Char; customer-resolution audit → Selection; total
evidence → the shop+presentment Char pair plus component Char snapshots; import
timestamps → two Datetimes; uniqueness → dual `models.Constraint`; store/company
isolation → `store_id` scope + `order_company_id`; ondelete → `restrict` on the
SO link; order-line GID traceability → `shopify_line_item_gid` Char. **No field
loses Shopify decimal precision.**

---

## 4. Read-only Shopify Order GraphQL query contract (task §5)

**[Proposed Task 012 decision]** One module-level constant `ORDER_IMPORT_QUERY`
(a single `order(id: $gid)` query), **read-only, zero mutations**, scope
`read_orders` + `read_customers` (both already granted). Issued **only** through
the merged `execute_business(job, store, query, variables)` admission
context-manager (§0).

### 4.1 Fields requested (exact)

- **Identity / metadata:** `id`, `name`, `legacyResourceId`, `createdAt`,
  `processedAt`, `updatedAt`, `cancelledAt`, `cancelReason`, `test`,
  `confirmed`, `closed`, `closedAt`, `displayFinancialStatus`,
  `displayFulfillmentStatus`, `note`, `tags`, `sourceName`. [Fact — official:
  types/nullability per §2]
- **Currency:** `currencyCode`, `presentmentCurrencyCode`, `taxesIncluded`.
- **Order-total money sets** (each `{ shopMoney{amount currencyCode}
  presentmentMoney{amount currencyCode} }`): `totalPriceSet` (non-null),
  `subtotalPriceSet`, `totalTaxSet`, `totalDiscountsSet` (nullable),
  `totalShippingPriceSet`, `totalTipReceivedSet` (non-null),
  `currentTotalDutiesSet` (nullable — used only to detect duties → §10 skip).
- **Order-level `taxLines`** (plain list, no pagination): `{ title rate
  ratePercentage priceSet{shopMoney{amount} presentmentMoney{amount}}
  channelLiable source }`.
- **Customer:** `customer { id firstName lastName displayName
  defaultEmailAddress{emailAddress} defaultPhoneNumber{phoneNumber}
  defaultAddress{ address1 address2 city zip provinceCode countryCodeV2 } }`
  (nullable — guest orders), plus order-level `email`.
- **Addresses:** `billingAddress` and `shippingAddress` (nullable
  `MailingAddress`) `{ firstName lastName name company address1 address2 city
  zip provinceCode countryCodeV2 phone }`.
- **Line items** (connection — paginate, §4.2): `lineItems(first: 100){ nodes{
  id name title variantTitle vendor quantity currentQuantity sku isGiftCard
  requiresShipping taxable variant{ id } product{ id }
  originalUnitPriceSet{shopMoney{amount}} originalTotalSet{shopMoney{amount}}
  discountedUnitPriceSet{shopMoney{amount}} discountedTotalSet{shopMoney{amount}}
  discountAllocations{ allocatedAmountSet{shopMoney{amount} presentmentMoney{amount}}
  discountApplication{ __typename index targetType allocationMethod targetSelection
  ... on DiscountCodeApplication { code } } }
  taxLines{ title rate ratePercentage priceSet{shopMoney{amount}} channelLiable }
  customAttributes{ key value } } pageInfo{ hasNextPage endCursor } }`. The
  `originalTotalSet`/`discountedTotalSet` are the **exact** line totals the
  ledger uses (§6.1-A); the `discountApplication.__typename`/`targetSelection`
  drive the line-vs-order `OC` classification (§7). The line-level
  `discountAllocations`, `taxLines`, `customAttributes` are **plain lists**
  [Fact — official] — no nested pagination needed.
- **Shipping lines** (connection — paginate): `shippingLines(first: 50){ nodes{
  id title code custom discountedPriceSet{shopMoney{amount}}
  taxLines{ title rate ratePercentage priceSet{shopMoney{amount}} } }
  pageInfo{ hasNextPage endCursor } }`.
- **Discount applications** (connection — paginate): `discountApplications(first:
  50){ nodes{ __typename index allocationMethod targetSelection targetType } pageInfo{
  hasNextPage endCursor } }` (evidence/reconciliation; per-line money comes from
  each line's `discountAllocations`).

### 4.2 Pagination — implementation-exact, three independent cursors (task §7)

**[Fact — official]** `Order.lineItems`, `Order.shippingLines`, and
`Order.discountApplications` are **connections** (`…Connection!`) with page size
max **250**; `pageInfo.hasNextPage`/`endCursor` position the next page. Cursor
durability across sessions is undocumented ⇒ cursors are **never persisted**.
`Order.taxLines` and every line-level list are **not** connections.

**[Proposed Task 012 decision — Option A, separate query constants (chosen over
one multi-cursor query for clear cursor ownership and simpler cost accounting):]**

- `ORDER_HEADER_QUERY(gid)` — order scalars, currency, all money sets,
  `taxesIncluded`, order-level `taxLines`, `customer`, addresses, **plus the
  first page** of each connection (`lineItems(first:100)`,
  `shippingLines(first:50)`, `discountApplications(first:50)`), each with
  `pageInfo{hasNextPage endCursor}`. Captures the initial `updatedAt`
  (`updatedAt₀`) and `id`.
- `ORDER_LINE_ITEMS_PAGE_QUERY(gid, after)` — `order(id:gid){ id updatedAt
  lineItems(first:100, after:$after){ nodes{…} pageInfo{hasNextPage endCursor} } }`.
- `ORDER_SHIPPING_LINES_PAGE_QUERY(gid, after)` — same shape for `shippingLines`.
- `ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY(gid, after)` — same for
  `discountApplications`.

Each connection has its **own** cursor loop and accumulator; only the connection
being advanced re-fetches (the header's first pages are **not** re-fetched, so
**no first-page duplication**). Every page (header first-pages included) is
validated:

- run the page **through `execute_business`** (§0 admission);
- **verify `Order.id == requested GID`** (else `data_shape_schema_mismatch`);
- **verify `updatedAt == updatedAt₀`** — if it changed, this is a **torn read**
  (§4.2.1);
- **require `pageInfo` present**; if `hasNextPage == true`, **require a non-empty
  `endCursor`** (else `data_shape_schema_mismatch`);
- **require cursor progress** — the new `endCursor` must differ from the prior
  page's cursor and the page must add ≥1 node (a repeated/empty cursor while
  `hasNextPage` → `data_shape_schema_mismatch`, preventing an infinite loop);
- **deduplicate node identities** — line-item `id`, shipping-line `id`, discount
  `index`; a duplicate or a conflicting repeat of an already-seen node →
  `data_shape_schema_mismatch` (never silently merged);
- **enforce an independent per-connection page ceiling**
  (`LINE_ITEMS_PAGE_LIMIT`, `SHIPPING_LINES_PAGE_LIMIT`,
  `DISCOUNT_APPLICATIONS_PAGE_LIMIT` — named provisional defaults, §4.3);
  exceeding → `data_shape_schema_mismatch` **naming the ceiling** (no silent
  truncation);
- **no Odoo business write occurs** until **every** connection is fully
  collected and validated — the savepoint SO build (§6) begins only afterward.

A large legitimate order (150 lines) is **valid**, fully paginated, and imported
— never rejected as malformed. The `100 lines` (single page) and `paginated line
items` (multi-page) fixtures (§15) cover both, plus a fixture where one
connection advances while the other two stay on their first page.

#### 4.2.1 Torn-read protection

**[Proposed Task 012 decision]** If `updatedAt` changes between the header and
any later page (or between pages), the read is **torn** (the order was edited
mid-pagination): **stop immediately**, let `execute_business.__exit__` **release
the lease normally**, create **no** SO and **no** binding, and route the job to
the approved retryable torn-read classification `concurrency_race_conflict`
(AUTO_RETRY family — a re-read gets a consistent snapshot). No partial state is
ever written; cursors are discarded.

### 4.3 GraphQL cost posture, throttling, deleted/missing, 60-day scope (task §8)

- **Cost [Proposed Task 012 decision — corrected: no unsupported "well under"
  claim]:** `first:100`/`first:50` are **named provisional defaults**
  (`LINE_ITEMS_PAGE_SIZE`, `SHIPPING_LINES_PAGE_SIZE`,
  `DISCOUNT_APPLICATIONS_PAGE_SIZE`), **not** asserted to be under Shopify's
  1,000-point single-query cap without evidence. The importer **captures
  `requestedQueryCost` and `actualQueryCost` from the response `extensions`** and
  the `throttleStatus{maximumAvailable, currentlyAvailable, restoreRate}` via the
  merged client, logs them (never the raw payload), and **must not auto-expand**
  page size. **Authorized dev-store live-read cost evidence** is required before
  any production tuning; page size is **reduced** if real cost evidence requires
  it. The implementation test suite uses **fixtures only**; live cost validation
  is a **separate gate** (VAL-B2-adjacent), not part of this task.
- **Throttle [Fact — official]:** a `200 Throttled` response → the merged
  `ERROR_THROTTLE` class → **AUTO_RETRY** with backoff (DEC-009). Task 012 adds
  no new pacing constant.
- **Deleted / missing order [Proposed Task 012 decision]:** `order(id:)`
  returning `null` → `data_shape_schema_mismatch` (`failed_retryable`) naming the
  GID; never a partial import.
- **60-day scope [Fact — official]:** apps see only the **last 60 days** without
  the approval-gated `read_all_orders` scope. Task 012 is `read_orders`-only; the
  60-day window is a documented setup limitation; `read_all_orders` is a
  **[Deferred / non-MVP]** forbidden capability (§14).
- **Schema-mismatch routing [Accepted decision — DEC-009]:** any unexpected
  shape (null where non-null expected, unknown enum that blocks mapping,
  over-ceiling pagination, torn read is separately `concurrency_race_conflict`)
  → `data_shape_schema_mismatch` (`failed_retryable`, "manual fix then retry").
  **No mutation** ever occurs on any path.

---

## 5. MBQ-27 — Odoo tax representation (task §6)

### 5.1 The platform constraint (why this is hard)

**[Fact — official, re-verified against odoo/odoo 19.0 2026-07-14]:**

- `sale.order.line.tax_ids` is a `Many2many` to `account.tax` (writable
  compute); it controls **which** taxes apply. `sale.order.line.price_tax`,
  `price_subtotal`, `price_total` are `compute='_compute_amount'` with **no
  `readonly=False`** ⇒ **read-only**. There is **no supported field to inject
  or force an external tax *amount* on a sale order or line** — Odoo recomputes
  from `tax_ids` + `price_include_override` + the company rounding method.
- The only first-class "force the external tax amount" surface in 19.0 is the
  `manual_tax_amounts` input to the tax-computation engine, wired into
  **`account.move` (invoice)** flows (e-invoice UBL/CII import, withholding,
  down-payments) — **not** reachable on `sale.order`.
- Line taxes are further remapped by the order's fiscal position via
  `fiscal_position.map_tax(taxes)` [Fact — official].
- Price inclusion in 19.0 is the **writable Selection `price_include_override`**
  (`tax_included`/`tax_excluded`/blank = company default); the legacy
  `price_include` Boolean is **compute-only** [Fact — official].
- **`res.company.tax_calculation_rounding_method` default is `round_globally`**
  ("Round per Tax") in 19.0 — a change from earlier Odoo's `round_per_line`
  [Fact — official]. Shopify computes tax **per line**; this is the concrete
  reconciliation-mismatch risk MBQ-56 must bound (§6).

**Conclusion [Fact — official]:** exact-amount tax forcing at SO level is
impossible without unsupported core hacks (rejected — routes through
architecture review per DEC-007 §6, not the RA log; there is **no** RA row for
external-tax injection, so this is a novel constraint honoured, not a rejected
approach re-proposed).

### 5.2 Chosen proposal — T-B "mapped-or-matched Odoo taxes under the guard"

**[Proposed Task 012 decision]** For each distinct `TaxLine` on a line or
shipping line, resolve an `account.tax` in this order; ordinary order import
**never silently creates accounting configuration**:

1. **Explicit tax mapping (preferred).** New connector model
   `shopify.connector.tax.mapping` (`store_id`; **`shopify_rate_key` Char** =
   canonical decimal-string percentage key, never a Float; `price_include`
   Boolean = the connector's own key component; `account_tax_id` M2o
   `account.tax` required `restrict`; `UNIQUE(store_id, shopify_rate_key,
   price_include)`). A hit resolves immediately **only after** the resolved
   `account_tax_id` passes the §5.5 validations.
2. **Existing-tax rate match.** Candidate filter: `account.tax` with
   `company_id == order_company_id`, `type_tax_use == 'sale'`, `active == True`,
   `amount_type == 'percent'`, and `price_include_override` matching
   `Order.taxesIncluded`. Rate identity is decided by the **canonical
   decimal-string key** (the authoritative evidence layer): the candidate's
   `account.tax.amount` (an Odoo `Float(16,4)` field) is canonicalized by the
   same rule and compared to the Shopify canonical key. **This comparison
   crosses the Decimal→Float boundary** — the Odoo `amount` is genuinely a
   `Float`, so `float_compare(tax.amount, rate_percent, precision_digits=6) == 0`
   is the correct *boundary* comparison against that existing Float field.
   **It does NOT "preserve Shopify Decimal precision"** — the Decimal/string
   canonicalization is the identity/evidence layer; `float_compare` is only the
   comparison at the boundary to Odoo's existing Float column (correction per
   review). **Ambiguity rule (§5.5):** zero candidates → configuration hold; more
   than one → **ambiguous** configuration hold; the first candidate is **never**
   chosen silently.
3. **Unmatched → hold, never create.** `odoo_validation_configuration`
   (`failed_retryable`) naming the exact rate/inclusion pair; the readiness
   surface carries a standing warning listing unmapped rates seen in holds; the
   operator adds a mapping (or the tax) and retries.
4. **Auto-creation only as an explicit admin opt-in.** Store-settings Boolean
   `order_tax_autocreate`, **default `False`**, admin-gated; when `True`, step 3
   instead creates `"Shopify Tax {percent}% ({incl|excl})"` (`amount_type=percent`,
   `price_include_override` per inclusion, default repartition, no custom
   accounts), each creation emitting a `manual_action`-grade audit line naming
   the enabling setting. The release-plan docs tell accountants these taxes
   exist. Account/repartition mapping remains a named input to the Phase-2/3
   accounting module.

**Rate-unit pinning + canonicalization [Proposed Task 012 decision]:** the
query requests **both** `TaxLine.rate` (decimal proportion, e.g. `0.06`) and
`TaxLine.ratePercentage` (percentage, e.g. `6.0`) [Fact — official]. The
**authoritative input is `ratePercentage`**, parsed with `decimal.Decimal`
(never `float`), quantized to 6 dp, trailing zeros stripped — so `6.0`, `6.00`,
`6.000` → the single key `"6"`, and `8.375` → `"8.375"`. The connector verifies
`rate × 100 == ratePercentage` within 6-dp precision; disagreement, or a
null/empty `rate`/`ratePercentage`, → `data_shape_schema_mismatch` hold. This
rejects the ambiguity where a bare `0.06` could mean 0.06 % or 6 %.

Odoo recomputes tax amounts from the resolved `tax_ids`; agreement with
Shopify's per-line math is enforced by the **total-check guard (§6)**, the
accepted correctness backstop. `channelLiable` tax lines import identically
(liability noted in evidence). This closes **MBQ-27** for **order import**;
invoice-level exact-amount enforcement (`account.move` `manual_tax_amounts` /
`_inverse_tax_totals`) is recorded as the **Phase-2/3 accounting-module**
mechanism, not used here **[Deferred / non-MVP]**.

### 5.3 Alternatives considered (and why rejected)

| Alternative | Verdict | Reason |
| --- | --- | --- |
| Force Shopify tax amount onto the SO | Rejected | No supported SO-level inverse [Fact — official §5.1]; would need a core hack (architecture-review-only, not attempted) |
| Build a connector tax engine | Rejected | DEC-003 non-goal "complex tax engine"; DEC-007 §6 evidence-only |
| Represent tax at invoice level now (`manual_tax_amounts`) | Deferred | Invoices are non-MVP (DEC-003); recorded as the Phase-2/3 mechanism |
| Silent `account.tax` auto-create by default | Rejected | Pollutes accounting config; PR #148 review item 6b — default `False`, admin-gated only |
| Float rate key / raw float equality | Rejected | Precision-unsafe; canonical decimal-string key + `float_compare(precision_digits=6)` required |

### 5.4 Exact safety limitations, readiness, operator config, test matrix

- **Safety limitations:** Odoo may compute a tax amount that differs from
  Shopify's by a legitimate rounding step; the guard (§6) bounds this and
  **rejects** anything beyond it. The connector never overrides Odoo's computed
  tax. Three-decimal-currency Shopify rounding is undocumented **[Open
  question]** → a named dev-store empirical check precedes onboarding any
  three-decimal store.
- **Readiness requirements:** the readiness surface warns (a) while any
  `TaxLine` rate is unmapped and unmatched (holds pending), and (b) when the
  company's `tax_calculation_rounding_method` is `round_per_line` vs
  `round_globally`, because that determines the tolerance's `O` term and how
  closely Odoo's tax will match Shopify's per-line tax (§6.4) — the connector
  **reads** this setting, never changes it.
- **Operator configuration:** operators map rates in `shopify.connector.tax.mapping`
  (shell/import until the settings-area UI phase); `order_tax_autocreate` stays
  `False` unless an admin deliberately enables it with the warning shown.
- **Test matrix:** taxes-included vs excluded; single rate; two rates on one
  order; mixed taxed + untaxed lines; a fractional rate (`8.375%`); `5.0`/`5.00`/
  `5.000` canonical-key equivalence; `rate`/`ratePercentage` disagreement →
  schema hold; null rate → schema hold; mapping hit; existing-tax match;
  unmatched → configuration hold; `order_tax_autocreate` default-False (no
  create) and opt-in create + audit line + dedup; `round_globally` vs
  `round_per_line` tolerance (§6); **ambiguous (>1) candidate → hold**;
  **company-mismatch candidate rejected**. **No acceptance is claimed** — these
  are the fixtures the implementation must pass.

### 5.5 Tax-mapping safety and the company-scope decision (task §9)

**[Proposed Task 012 decision]** Both the explicit-mapping path (step 1) and the
existing-tax rate-match path (step 2) resolve a tax **only** when every one of
these holds; otherwise they hold, never guess:

- `account_tax_id.company_id == order_company_id` (the store-settings company);
- `type_tax_use == 'sale'`;
- `active == True`;
- `amount_type == 'percent'` (the canonical rate key applies to percent taxes;
  group taxes are matched only when explicitly mapped);
- `price_include_override` matches `Order.taxesIncluded`
  (`'tax_included'` ⇔ true, `'tax_excluded'` ⇔ false);
- the **fiscal-position result is validated**: after Odoo maps the line's taxes
  via `fiscal_position.map_tax(...)`, the connector re-checks that the mapped tax
  still satisfies the rate/inclusion/company invariants; if the fiscal position
  remaps to a different rate or drops the tax, the line **holds**
  (`odoo_validation_configuration`) rather than importing a silently different
  tax;
- **zero candidates → configuration hold**; **more than one candidate →
  ambiguous configuration hold** (message names all candidates); **the first
  candidate is never chosen silently.**

**Company-scope decision (explicitly documented, per review):** the tax mapping
model carries `store_id` (not a redundant `company_id` column). A store resolves
to **exactly one** `order_company_id` (single-default field, §8-equivalent
D-012-11). Safety is provided by (a) a Python `@api.constrains` on
`shopify.connector.tax.mapping` asserting `account_tax_id.company_id ==
store_id.order_company_id` **at mapping create/write** (so a mapping can never
point at a foreign-company tax), **plus** (b) **immutability of `order_company_id`
once any order binding or tax mapping exists for the store** (a `@api.constrains`
/ write guard on the store-settings field), **plus** (c) the resolution-time
`company_id == order_company_id` re-check above. This gives **equivalent
structural safety** to a stored `company_id` column without duplicating derivable
data; the choice — *store-scoped mapping + constrained tax company + immutable
`order_company_id` + resolution-time re-check* — is the recorded decision. **The
mapping's `UNIQUE(store_id, shopify_rate_key, price_include)` therefore also
uniquely determines the company** (via the store), so it cannot yield two taxes
in different companies for one key.

---

## 6. MBQ-56 — financial total-check guard: canonical ledger + tax bound (task §7)

The guard is **mandatory, permanent, non-configurable, never silent, never
auto-retried** [Accepted decision — DEC-014 §F, DEC-007 §6, DEC-009]. **REBUILT
2026-07-14 (review `4690680028` items 2 & 3):** the earlier formula was
internally inconsistent (`shopify_lines_expected` excluded shipping/tips while
`L` and the examples included them) and the `K = distinct tax groups` tax bound
was invalid for `round_globally`. This section defines **one canonical Shopify
source ledger with every component counted exactly once**, proves the tax bound
from **both** systems' rounding events, and rewrites every example to use the
written equations. **§6.1 = ledger; §6.2 = the single Decimal→Odoo boundary;
§6.3 = tax-inclusive; §6.4 = tolerances + proof; §6.5 = worked examples.**

### 6.1 The canonical Shopify source ledger (each component once)

All source arithmetic is `decimal.Decimal` on `shopMoney` amounts (the lossless
Char snapshots), with **no** intermediate rounding until the boundary in §6.2.
Let `r = order_currency.rounding` (Odoo `res.currency.rounding`; `0.01` default;
JPY `1.0`; three-decimal `0.001`; `decimal_places = ceil(log10(1/r))`) [Fact —
official].

**A. Product merchandise net `M`.** For each line item `i`:
- `discountedTotalSet_i` = the line total **after line-level discounts**, which
  by official definition *"doesn't include order-level discounts. Code-based
  discounts aren't included by default."* [Fact — official]. So it already nets
  line-level discounts and **must not** have them subtracted again.
- `OC_i` = the **order-level/code allocations only**, i.e. the
  `discountAllocations_i` whose `discountApplication` has `targetSelection == ALL`
  (order-wide) **or** is code-based (`__typename == DiscountCodeApplication`) —
  precisely the discounts that `discountedTotalSet` *excludes*. Line-level
  allocations (already inside `discountedTotalSet`) are **not** in `OC_i`.
- `M = Σ_i ( discountedTotalSet_i − OC_i )`.

**No double subtraction (proof).** Line-level discounts appear once — folded
into `discountedTotalSet`; they are never in `OC_i` (whose members are exactly
what `discountedTotalSet` excludes). Order-level/code discounts appear once — in
`OC_i`; they are never in `discountedTotalSet` (which excludes them by
definition). Equivalently, since `discountedTotalSet_i = originalTotalSet_i −
(line-level_i)` and `line-level_i = originalTotalSet_i − discountedTotalSet_i`
is derivable from exact fields, `M = Σ_i originalTotalSet_i − Σ_i (line-level_i
+ OC_i)` — every discount on every line subtracted exactly once from the gross
`originalTotalSet`. The line-vs-order **distinction is explicit** (`targetSelection`/
`__typename`) and affects only how Odoo *represents* the discount (§7), not the
ledger value.

**B. Shipping net `H`.** `H = Σ_s shippingLine_s.discountedPriceSet.shopMoney`
— the shipping price **after** shipping discounts [Fact — official]. Shipping
lines carry their **own** `discountAllocations`; because `discountedPriceSet`
already nets them, they are **not** subtracted again. Order-level discounts with
`targetType == SHIPPING_LINE` land on shipping lines (netted here), and those
with `targetType == LINE_ITEM` land in `OC_i` (part A) — **no overlap**.

**C. Tips `T`.** `T = totalTipReceivedSet.shopMoney` — counted **exactly once**;
tips carry no tax.

**D. Discounts.** Discounts enter the ledger **only** through the subtractions
in A (`OC_i`) and B (shipping `discountedPriceSet`). The Odoo-side
representation of an order-level allocation — a native line `discount %` when
faithful, else a per-tax-signature negative adjustment line (§7) — changes the
**Odoo** ledger only; it creates **no** second Shopify source component. (A
negative adjustment line is `−OC` re-expressed, not an additional discount.)

**E. Untaxed source expectation `U_ex`** (tax-**exclusive**; the tax-inclusive
form is §6.3). Let `G = M + H + T`.
- **`taxesIncluded = false`:** `U_ex = G` (prices are already tax-exclusive).
- The independent **total** expectation is `Total_ex = U_ex + totalTaxSet.shopMoney`.

**F. Final total.** `Total_ex` is compared **independently** to
`totalPriceSet.shopMoney`. A mandatory **ledger self-check** (catches any
`OC`-classification error) requires `|Total_ex − totalPriceSet.shopMoney| ≤
tol_total` (§6.4) *before* the order is trusted; a breach → `financial_total_mismatch`.
Because `totalPriceSet` *"includes taxes and discounts, before returns"* [Fact —
official] and duties are excluded (a non-null `currentTotalDutiesSet` → policy
skip, §10), this identity holds for every in-scope order.

**Odoo construction that reproduces the ledger.** Product line `i`:
`price_unit = discountedUnitPriceSet_i` (line-level discount baked in, same
basis as `discountedTotalSet_i`), `product_uom_qty = quantity_i`; `OC_i`
represented as a native `discount %` (when faithful) or a per-tax-signature
negative adjustment line (§7). Shipping line `s`: `price_unit =
discountedPriceSet_s`. Tip line: `price_unit = totalTipReceivedSet`. Then Odoo's
`amount_untaxed = M + H + T = G` (tax-exclusive) by construction, so the lines
component compares like against like.

### 6.2 The single Decimal→Odoo rounding boundary

There is **exactly one** place where lossless `Decimal` source values enter
Odoo's `Float`/`Monetary` fields: when the importer **writes** each SO line's
`price_unit` (and `discount %`, and adjustment-line `price_unit`). Every ledger
figure above (`M`, `H`, `T`, `OC_i`, `U_ex`, `Total_ex`) is computed in
`Decimal` **before** that write. After the write, Odoo computes `price_subtotal`,
`amount_tax`, `amount_total` and rounds them to `r` using its own
`float_round(precision_rounding=r)`. The guard then reads those Odoo figures
back and compares them, in `Decimal`, to the `Decimal` ledger. No guard
arithmetic is done in binary `float`; the only `Float` values are Odoo's own
post-write computed fields, which is exactly the boundary this rule pins.

### 6.3 Tax-inclusive orders (`taxesIncluded = true`) (task §5)

When `taxesIncluded = true`, `discountedTotalSet`, `discountedUnitPriceSet`, and
shipping `discountedPriceSet` are **tax-inclusive**, so `M`, `H`, and hence `G`
are tax-inclusive; but Odoo's `amount_untaxed` is tax-**exclusive**. Therefore:

- **Untaxed expectation:** `U_ex = G − totalTaxSet.shopMoney` — subtract the
  reported tax **exactly once** to obtain the tax-exclusive base to compare with
  Odoo's `amount_untaxed`. (Do **not** compare tax-inclusive Shopify prices
  directly to Odoo `price_subtotal`.)
- **Total expectation:** `Total_ex = U_ex + totalTaxSet = G` — for tax-inclusive
  orders the tax is internal, so `totalPriceSet = G` and the total identity
  still holds (`U_ex + totalTaxSet = G`).
- **Odoo side:** each taxed line is written with `price_include_override =
  'tax_included'`, so Odoo **backs out** the tax once per line; `amount_untaxed`
  = the tax-excluded base, `amount_tax` = the backed-out tax. **Adjustment lines
  preserve the source line's price-inclusion and tax signature** (§7), so the
  back-out is applied to the same base Shopify discounted, and tax is **never
  removed twice**. Untaxed lines have no tax to back out; mixed taxed/untaxed
  orders work because `totalTaxSet` is exactly the tax on the taxed lines and
  `U_ex = G − totalTaxSet` removes precisely that.

The **tax component** (`|amount_tax − totalTaxSet|`) and the **total** are
compared identically in both modes; only the **lines** expectation changes
(subtract `totalTaxSet` when inclusive), which also changes the lines tolerance
(§6.4, the `S` term).

### 6.4 Tolerances — derived from both systems' rounding events, with proof

Define three rounding-event counts:
- **`L`** = number of Odoo SO lines contributing to `amount_untaxed` (product
  lines + shipping lines + tip line + any negative adjustment lines). Odoo
  rounds each line's `price_subtotal` to `r` → each contributes ≤ `0.5r`.
- **`S`** = number of **Shopify** per-line/per-shipping-line tax rounding events
  actually represented by `TaxLine.priceSet`: `S = Σ_i |taxLines_i| + Σ_s
  |taxLines_s|`. Each `TaxLine.priceSet` is a Shopify per-line tax rounded to
  `r` → each contributes ≤ `0.5r`.
- **`O`** = number of **Odoo** tax rounding events under the *configured*
  `res.company.tax_calculation_rounding_method` [Fact — official]:
  - `round_per_line` → `O = Σ over Odoo lines of (number of applied taxes on
    that line)` = the taxed-line × tax pairs (adjustment and shipping lines
    included; tip untaxed contributes 0);
  - `round_globally` (the **Odoo-19 default**) → `O = number of distinct global
    tax/repartition groups Odoo rounds once` — one per distinct mapped tax for
    simple percent taxes with default single tax-repartition; a **group tax**
    (`amount_type='group'`) counts its children, and a tax with **multiple tax
    (not base) repartition lines that each round** counts each such line.

**Tolerances:**

| Component | `taxesIncluded=false` | `taxesIncluded=true` |
| --- | --- | --- |
| Lines: `|amount_untaxed − U_ex|` ≤ | `0.5 r L` | `0.5 r (L + S)` |
| Taxes: `|amount_tax − totalTaxSet|` ≤ | `0.5 r (S + O)` | `0.5 r (S + O)` |
| Total: `|amount_total − totalPriceSet|` ≤ | `tol_lines + tol_tax` | `tol_lines + tol_tax` |

There is **no fixed or currency-relative money cap** anywhere.

**Proof of the tax bound `tol_tax = 0.5 r (S + O)`.** Let `Θ` be the exact,
un-rounded total tax on the (guard-verified) taxable bases. Shopify's
`totalTaxSet = Σ_{k=1..S} round_r(t_k)` for `S` per-line/per-shipping tax events
`t_k` with `Σ t_k = Θ`, so `|totalTaxSet − Θ| ≤ 0.5 r S`. Odoo's `amount_tax =
Σ_{o=1..O} round_r(g_o)` for `O` rounding events (per-line or per-group) with
`Σ g_o = Θ` (the same taxable bases, since the lines component already binds
them and the mapped rates match), so `|amount_tax − Θ| ≤ 0.5 r O`. By the
triangle inequality, `|amount_tax − totalTaxSet| ≤ |amount_tax − Θ| + |Θ −
totalTaxSet| ≤ 0.5 r O + 0.5 r S = 0.5 r (S + O)`. ∎ The earlier
`K = distinct tax groups` bound omitted the `S` term entirely: under
`round_globally` Odoo rounds once per group (`O` small) while Shopify rounded
per line (`S` possibly large), so the legitimate difference can accumulate up to
`0.5 r S` beyond `0.5 r O` and `K` false-rejects (see the counterexample,
Example I).

**Proof of the lines bounds.** Tax-exclusive: `U_ex = G` is exact `Decimal`
(no tax rounding); `amount_untaxed` sums `L` Odoo-rounded lines, so
`|amount_untaxed − U_ex| ≤ 0.5 r L`. Tax-inclusive: `U_ex = G − totalTaxSet`
carries `totalTaxSet`'s `S` roundings, and `amount_untaxed` carries its own
`L` line roundings, so `|amount_untaxed − U_ex| ≤ 0.5 r (L + S)`. ∎

**Proof of the total bound.** `amount_total = amount_untaxed + amount_tax`, so
`|amount_total − totalPriceSet| ≤ |amount_untaxed − U_ex| + |amount_tax −
totalTaxSet| = tol_lines + tol_tax` (using `totalPriceSet = U_ex + totalTaxSet`).
∎ This is a conservative (never-false-rejecting) bound; for tax-inclusive orders
the true total error is only ≤ `0.5 r L` (tax is internal), so the components,
not the total, do the discriminating work.

**Why a loose `tol_tax` does not hide a missing/wrong line.** A missing or
mis-priced line shifts **merchandise**, caught by the **lines** component
(`0.5 r L`, tight); a wrong **rate** is prevented upstream by the canonical-key
tax mapping (§5) and its `rate × 100 == ratePercentage` cross-check. `tol_tax`
only has to absorb legitimate per-line-vs-global rounding divergence — which is
exactly `≤ 0.5 r (S + O)` — while structural errors surface in the tight lines
component. Each component guards its own integrity.

**Properties (task §7):** the tolerance derives only from legitimate currency
rounding events; **no** arbitrary money cap; discounts are exact by construction
(not tolerated); missing/wrong lines are caught at the lines/total level; a
mismatch is never silent and never auto-retried; the formula is mandatory and
non-configurable.

### 6.5 Worked examples (illustration only — not acceptance)

Every example uses the §6.1/§6.3 equations verbatim. Comparands are the lossless
Char `shopMoney` snapshots parsed as `Decimal`; Odoo figures are read back.

**Example A — ordinary 2-decimal (USD, `r = 0.01`), `taxesIncluded=false`, no
discounts.** Line1: qty 2 × `discountedTotalSet` 20.00 (8%); Line2: qty 1 ×
15.00 (8%); Shipping `discountedPriceSet` 5.00 (8%). `OC_i = 0`.
`M = 20.00 + 15.00 = 35.00`; `H = 5.00`; `T = 0`; `G = 40.00`; `U_ex = 40.00`;
`Total_ex = 40.00 + 3.20 = 43.20 = totalPriceSet` ✓ (self-check).
Odoo: `amount_untaxed = 40.00`, `amount_tax = 3.20`, `amount_total = 43.20`.
`L = 3`, `tol_lines = 0.015`; lines `|40−40| = 0` ✓. `S = 3` (three line/shipping
tax events), `round_globally` `O = 1` (one 8% group), `tol_tax = 0.5·0.01·4 =
0.02`; `|3.20−3.20| = 0` ✓. Total bound `0.035`; `|43.20−43.20| = 0` ✓. **PASS.**

**Example B — JPY (`r = 1.0`), `taxesIncluded=false`.** Line: qty 3 ×
`discountedTotalSet` 3000 (10%); Shipping 500 (10%). `M = 3000`, `H = 500`,
`G = U_ex = 3500`; `Total_ex = 3500 + 350 = 3850 = totalPriceSet` ✓. Odoo:
untaxed 3500, tax 350, total 3850. `L = 2`, `tol_lines = 1.0` ✓. `S = 2`,
`O = 1`, `tol_tax = 0.5·1·3 = 1.5`; `|350−350| = 0` ✓. Total bound `2.5` ✓.
**PASS.**

**Example C — BHD (`r = 0.001`), `taxesIncluded=false`.** Clean: line qty 1 ×
10.000 (5%). `M = U_ex = 10.000`; `Total_ex = 10.000 + 0.500 = 10.500` ✓. Odoo
untaxed 10.000, tax 0.500. `L = 1`, `tol_lines = 0.0005` ✓. `S = 1`, `O = 1`,
`tol_tax = 0.001` ✓. **PASS.** *Risk note:* a 12.345 base at 10% = 1.2345 whose
3-dp rounding is officially undocumented on Shopify's side [Open question]; if
Shopify reported 1.234 while Odoo computed 1.235 with `S = O = 1`,
`tol_tax = 0.001` **admits** the 0.001 gap — so a **named dev-store empirical
check** confirms Shopify's three-decimal rounding **before** onboarding such a
store (the guard bounds it; the empirical check pins the convention).

**Example D — high-value order discount, taxable (USD, `r = 0.01`).** Line qty
1 × `discountedTotalSet` 1000.00 (10%); one order-level allocation
`OC = 333.33` (`targetSelection = ALL`). `M = 1000.00 − 333.33 = 666.67`,
`U_ex = 666.67`; `Total_ex = 666.67 + 66.67 = 733.34 = totalPriceSet` ✓.
Odoo: native `%` = 333.33/1000 = 33.333 % → 2-dp quantize → 333.30 (off 0.03 >
`0.5r`), **not faithful** → exact **−333.33 tax-preserving** adjustment line
(inherits 10% + inclusion). `amount_untaxed = 1000.00 − 333.33 = 666.67`,
`amount_tax = 66.67`, total 733.34. `L = 2`, `tol_lines = 0.01`; ✓. `S = 1`,
`O = 1`, `tol_tax = 0.01`; ✓. **PASS** — the withdrawn `D_lines × 0.5r` term is
not relied on.

**Example E — mixed tax signatures (USD, `r = 0.01`).** Line1 100.00 (10%),
Line2 50.00 (untaxed), Line3 200.00 (20%); order discount 30.00 ACROSS →
`OC` = 10/5/15. `M = (100+50+200) − (10+5+15) = 320`; `U_ex = 320`;
`Total_ex = 320 + 46 = 366 = totalPriceSet` ✓. Odoo (native % faithful:
10/100=10 %, 5/50=10 %, 15/200=7.5 %): product nets 90/45/185, `amount_untaxed =
320`, `amount_tax = 9.00 + 37.00 = 46.00`. `L = 3`, `tol_lines = 0.015` ✓.
`S = 2` (two taxed lines), `O = 2` (10 % and 20 % groups), `tol_tax = 0.02`; ✓.
Total bound `0.035` ✓. **PASS.** A no-tax residual on Lines 1/3 would raise the
taxable base (100/200) → tax 50 ≠ 46 → tax component **fails** (the
tax-preserving residual is required, §7).

**Example G — tax-inclusive, ordinary (USD, `r = 0.01`, `taxesIncluded=true`).**
Line qty 1 × `discountedTotalSet` 110.00 (10% included; `TaxLine.priceSet =
10.00`), `totalTaxSet = 10.00`, `totalPriceSet = 110.00`. `M = 110.00`,
`G = 110.00`; **inclusive** ⇒ `U_ex = G − totalTaxSet = 110.00 − 10.00 =
100.00`; `Total_ex = U_ex + totalTaxSet = 110.00 = totalPriceSet` ✓. Odoo
(`price_include_override='tax_included'`): backs out → `amount_untaxed = 100.00`,
`amount_tax = 10.00`, `amount_total = 110.00`. `L = 1`, `S = 1`, tax-incl
`tol_lines = 0.5·0.01·(1+1) = 0.01`; `|100−100| = 0` ✓. `O = 1`, `tol_tax =
0.01`; `|10−10| = 0` ✓. **PASS** — tax removed once on each side.

**Example H — tax-inclusive with order discount (USD, `r = 0.01`,
`taxesIncluded=true`).** Line qty 1 × `discountedTotalSet` 110.00 (10% incl);
order-level `OC = 11.00`; net incl = 99.00; `TaxLine.priceSet = 99 − 99/1.1 =
9.00`; `totalTaxSet = 9.00`; `totalPriceSet = 99.00`. `M = 110.00 − 11.00 =
99.00`, `G = 99.00`; `U_ex = 99.00 − 9.00 = 90.00`; `Total_ex = 99.00 =
totalPriceSet` ✓. Odoo: native % = 11/110 = 10 % faithful → line incl net 99.00;
back out → `amount_untaxed = 90.00`, `amount_tax = 9.00`, total 99.00. `L = 1`,
`S = 1`, `tol_lines = 0.01`; ✓. `O = 1`, `tol_tax = 0.01`; ✓. **PASS** — the
order discount inherits tax-inclusion; tax not removed twice.

**Example I — adversarial many-small-lines, one group, global rounding (USD,
`r = 0.01`, `taxesIncluded=false`).** `n = 40` lines, each qty 1 ×
`discountedTotalSet` 1.00 at rate 1.4 % (one tax group). Exact per-line tax =
0.014. **Shopify** rounds per line: `round_r(0.014) = 0.01` × 40 → `totalTaxSet =
0.40`; `S = 40`. **Odoo** `round_globally`: base 40.00 × 1.4 % = 0.56 →
`round_r = 0.56`; `O = 1`; `amount_tax = 0.56`. `M = U_ex = 40.00`;
`amount_untaxed = 40.00`; `L = 40`, `tol_lines = 0.20`; lines `|40−40| = 0` ✓.
Tax difference `|0.56 − 0.40| = 0.16`.
- **Old bound** `tol_tax = 0.5r·K` with `K = 1` group `= 0.005` → `0.16 ≫ 0.005`
  → **FALSE REJECTION** of a legitimate order.
- **Proven bound** `tol_tax = 0.5r(S + O) = 0.5·0.01·(40 + 1) = 0.205` → `0.16 ≤
  0.205` → **correctly ACCEPTED.**
Now drop **one** of the 40 lines (base 1.00): `amount_untaxed = 39.00` vs
`U_ex = 40.00` → `|1.00| ≫ tol_lines (0.195)` → **LINE component rejects** the
missing line. So the loose `tol_tax` accepts the legitimate per-line-vs-global
rounding **and** the missing line is still caught — by the tight lines
component, not the tax tolerance. *(Operators who need Shopify-matching tax may
set the company to `round_per_line`; the guard accepts either method and the
evidence records both totals — §5 readiness note.)*

**Example F — deliberate missing line (USD, `r = 0.01`, `taxesIncluded=false`).**
Example A with Line2 (15.00, tax 1.20) dropped. `U_ex` (full order) = 40.00;
Odoo `amount_untaxed = 25.00` → `|25 − 40| = 15.00 ≫ tol_lines 0.015` → **LINE
fails**; total 27.00 vs 43.20 → `|16.20| ≫ 0.035` → **TOTAL fails**. Rolled back,
`financial_total_mismatch`, manual review. **Never silent.**

---

## 7. Discount representation (task §8)

**[Fact — official]** `discountedUnitPriceSet`/`discountedTotalSet` **include
line-level** discounts but **exclude order-level and code-based** discounts,
which surface per line as `discountAllocations[].allocatedAmountSet`.
`TaxLine.priceSet` is the tax *"after discounts"*.

**Line-level vs order-level classification (the `OC` partition, §6.1-A)
[Proposed Task 012 decision]:** an allocation `a ∈ discountAllocations_i` is
**order-level/code** (member of `OC_i`, subtracted in the ledger and represented
in Odoo) **iff** `a.discountApplication.targetSelection == ALL` **or**
`a.discountApplication.__typename == DiscountCodeApplication`; these are exactly
the discounts `discountedTotalSet` excludes. All other allocations are
**line-level**, already inside `discountedTotalSet`/`discountedUnitPriceSet`, and
are **never** re-subtracted. The query therefore requests, per allocation,
`discountApplication { __typename targetType targetSelection allocationMethod }`
(with `... on DiscountCodeApplication { code }`). **No `discountAllocations`
field is assumed to be order-level by default** — the classification is explicit,
and the §6.1-F ledger self-check (`Total_ex == totalPriceSet`) catches any
misclassification before the order is trusted; a named dev-store empirical check
with a mixed line-level + order-level + code order confirms the rule before
onboarding a discount-heavy store.

**[Proposed Task 012 decision]** Final discount rules:

- **Line-level discounts** are baked into `price_unit =
  discountedUnitPriceSet.shopMoney.amount` — **never** re-subtracted (they are
  not in `OC`).
- **When a native Odoo line `discount %` is faithful:** an `OC` order-level
  allocation is written to the SOL `discount` (%) field **only when** that
  percentage, quantized to the Discount decimal precision (2 dp default),
  reproduces the exact allocated amount for the line **to within `0.5r`**.
- **When an exact negative adjustment line is required:** otherwise (typically
  high-value lines where a 2-dp % cannot hit the minor unit) the allocation is
  carried by an explicit negative **"Shopify Order Discount"** service line
  (auto-provisioned per store, `default_code SHOPIFY-ORDER-DISCOUNT`,
  `price_unit` = the exact negative residual) so the total reconciles exactly
  rather than on tolerance slack.
- **Tax inheritance for taxable residuals:** because `TaxLine.priceSet` is
  post-discount, a residual line against a **taxable** source line **inherits
  that line's `tax_ids` and `price_include_override`** — it is *not* a no-tax
  line — so Odoo reduces the same taxable base Shopify taxed (Example E).
- **Separate buckets by tax signature:** residuals sharing an identical tax
  signature (same `tax_ids` + inclusion) may be combined into **one negative
  line per signature/bucket**, with the per-source-line allocation preserved in
  evidence.
- **Genuinely untaxed residuals:** only a genuinely untaxed source line
  produces a **no-tax** residual line.
- **No universal no-tax discount line:** there is never a single universal
  no-tax residual across taxable and untaxed lines (it would raise the taxable
  base and break the tax component, Example E).
- **Inconsistent allocation rejection:** a residual that cannot be attributed
  to a source line's tax signature is a **rejected** (inconsistent) allocation →
  `financial_total_mismatch`, **never** absorbed by widening tolerance.
- **Line-level vs order-level vs shipping:** line-level allocations → already in
  `price_unit`; **`OC` order-level/code** allocations (targetSelection==ALL or
  code-based, with `targetType == LINE_ITEM`) → per-line `discount %` (if
  faithful) else the exact negative adjustment line; **shipping** discounts
  (`targetType == SHIPPING_LINE`) are already reflected in
  `shippingLines[].discountedPriceSet` and are **not** re-subtracted (§6.1-B).
  No allocation is counted twice.

**Exact rounding / allocation rules:** all allocation math is done in
`decimal.Decimal`; the faithfulness test uses `float_compare(precision_rounding
= r)`; residual amounts are the exact `allocatedAmountSet` values (lossless
Char parsed to Decimal); each line's chosen representation (native % vs
adjustment line) and the raw allocation are preserved in the evidence payload.

---

## 8. Customer and address resolution (task §9)

**[Accepted decision — DEC-014 §C/§E, Task 011]** Email is the **sole automatic
customer match key** beyond an existing binding (RA-006 forbids name/fuzzy
matching — revisit condition unmet); existing partners' own fields are **never**
mutated by import; a bad/ambiguous customer does **not** hold the whole order
(unlike an unmatched product line). This closure does **not** redesign Task
011B's accepted email-matching policy.

**[Proposed Task 012 decision]** Order-import consumption of Task 011/011B
(sequence D-012-5):

1. **`Order.customer` present** → resolve via the **customer binding**: existing
   binding → use its partner (`existing_binding`); no binding → run the Task 011
   D1 match on the embedded customer payload — recall-safe **normalized-email**
   match via the **Task 011B indexed `shopify_connector_email_normalized`
   lookup** → single active hit → bind + use (`email_match`); confident no-match
   → create + bind (`created`, MBQ-59 gate); ambiguous (>1) → **hold** (§8.1);
   missing email → fall through to (2).
2. **Guest order** (`customer` null [Fact — official]) with non-null
   `Order.email` → recall-safe normalized-email partner match via the **011B
   indexed lookup** (no binding row — no Customer GID exists): exactly one active
   → use (`guest_email_match`); >1 → hold (§8.1); none → create a **person**
   partner from billing/shipping name + email (`guest_created`, Task 011
   §8.3/§8.4 mapping).
3. **Genuinely no PII** (`customer` null **and** `email` null) →
   `customer_fallback_partner_id` (the Posture-A field — Task 012 is its first
   sanctioned consumer) with `customer_resolution = fallback`; if the fallback
   is unconfigured → `odoo_validation_configuration` (`failed_retryable` —
   operator sets it, retries).
4. **Archived-only email match** → `duplicate_risk` (`blocked_manual_review`),
   **no un-archive** (Task 011 rule).

### 8.1 Ambiguous customer = pre-creation hold (whole job, not partial SO)

**[Proposed Task 012 decision]** `sale.order.partner_id` is `required=True`
[Fact — official], so an unresolved customer cannot yield a partial SO. Path-3
ambiguity → **no SO created**; job → `blocked_manual_review` / sub-reason
`ambiguous_match`, carrying the **exact Task 011 §8.2 candidate-evidence JSON**
(`{"kind":"customer_ambiguous_match_candidates", …, "candidates":[…first 20 by
partner_id…], "candidate_count": true_total}`) in `technical_detail`, plus full
financial evidence in `payload_snapshot`. "The rest of order import that
survives a customer hold" is the **evidence capture**, not a partial SO
(clarifies the earlier packet phrasing). Operator resolves the customer in the
matching flow (creating the binding), then retries — the job completes normally.

### 8.2 Addresses — resolving the address-child and company/person gaps

**[Fact — official]** `partner_invoice_id`/`partner_shipping_id` are writable
computes (fall back via `partner_id.address_get(['invoice'|'delivery'])`);
`res.partner.type ∈ {contact, invoice, delivery, other}`; `address_get()` does a
company-bounded DFS selecting typed children; `res.partner` is person-only when
`is_company=False` (Task 011 §8.4).

**[Proposed Task 012 decision]** `billingAddress`/`shippingAddress` (nullable
`MailingAddress`) map to child `res.partner` rows (`type='invoice'` /
`'delivery'`) under the resolved parent, **created only when no existing child
(or the parent itself) matches** on the normalized tuple `(name, street,
street2, city, zip, country, state)` — preventing per-order duplicates.
Country/state resolution is **lookup-only** (Task 011 rule; never creates a
country/state). `partner_invoice_id`/`partner_shipping_id` are then written
explicitly (writable — [Fact — official]); `address_get` fallback covers absent
addresses. For fallback-partner orders, the children carry the order name for
traceability. **Existing partners' own fields are never mutated** (Task 011
invariant) — the importer only *adds* child rows, never edits the resolved
parent.

**Company/person gap resolution [Proposed Task 012 decision]:** order import
stays **person-only** — `is_company` is never set and no separate company
partner is created (B2B is [Deferred / non-MVP], RA guardrail). A non-empty
`MailingAddress.company` is **captured in evidence** and MAY be written to the
child partner's `company_name` Char (the Odoo field for an individual's company
label) **[Recommendation — confirm the field exists at build time]**; it never
promotes a partner to a company. This resolves the DEC-014 "customer
company/person classification" open item for order import **at proposal level**,
without touching Task 011B's email policy.

**What may update an existing partner:** nothing on the resolved parent — only
the **addition** of `type='invoice'`/`'delivery'` child rows that did not
already exist. **What must never overwrite existing Odoo data automatically:**
the parent's name/email/phone/address/company/tax fields, any existing child's
fields, and country/state master data.

---

## 9. Product and order-hold policy (task §10)

**[Proposed Task 012 decision]**

- **Product-variant binding lookup:** each `LineItem` resolves `product_id`
  through the **variant binding** — a read-only
  `env['shopify.connector.product.variant.binding'].search([('store_id','=',store.id),
  ('shopify_gid','=',variant_gid)]).product_variant_id` (the merged model;
  `UNIQUE(store_id, shopify_gid)` guarantees ≤1 hit) [Fact — repo code]. The
  **template** binding alone is insufficient. This is a cross-module **read**
  (sale→product edge, DEC-008), not an edit of any product-module file (§14).
- **Unmatched product line → whole-order hold:** `mapping_missing` →
  `failed_retryable` ("manual fix then retry", **not** `blocked_manual_review`)
  naming the exact SKU/GID [Accepted decision — DEC-014 §I]. The **whole** order
  is held (no partial SO — a partial order cannot pass the guard) [Accepted
  decision — DEC-014 §C.5].
- **Retry after mapping is created:** once the variant binding exists, the job
  returns to `queued` and resumes automatically (loop-back state).
- **Duplicate-order risk:** the **order binding is the sole idempotency anchor**
  (§3.3) — a repeated webhook/scan collides on `(store, order GID)`; a genuine
  duplicate-risk signal → `duplicate_risk` (`blocked_manual_review`).
- **No placeholder product, no dropped line:** neither is permitted (either
  would break the guard) [Accepted decision — DEC-014 §C.5]. **Custom line
  items** (null `variant` [Fact — official]) import via a per-store
  auto-provisioned service product `"Shopify Custom Item"`
  (`default_code SHOPIFY-CUSTOM`) with complete price evidence — a real product,
  not a placeholder for a *matchable* item. Null-variant lines whose `sku`
  matches an Odoo product resolve through the SKU path first. **Gift-card lines**
  (`isGiftCard`) import as ordinary lines with a job-log note (no gift-card
  accounting).
- **No pre-existing SO auto-match:** import always creates a new SO; `match_key`
  is `existing_binding`/`manual` only (§3.3).

---

## 10. Divergent-currency routing (DEC-020 residual) (task §11)

**[Accepted decision — DEC-020]** For `presentmentCurrencyCode != currencyCode`,
the connector **must not** silently create a normal Odoo SO in shop currency,
**independent of the total-check outcome**; the order is blocked **before any SO
creation**; both `shopMoney` + `presentmentMoney` and both currency codes are
captured as evidence in every case; presentment-currency Odoo orders are
[Deferred / non-MVP]. The exact error-class/sub-reason mapping was left OPEN by
DEC-020 as implementation-planning.

**[Proposed Task 012 decision] — the exact routing (resolves the DEC-020
residual; does NOT overload `financial_total_mismatch`):**

| Element | Decision | Rationale |
| --- | --- | --- |
| **Job state** | `skipped` (terminal, policy) | A policy/eligibility block is **not** a failure; DEC-009: `skipped` is *"an outcome available from any class"*. `skipped` is a merged terminal state. |
| **Error class** | **none assigned** | The 16-class registry stays intact — **no 17th class**, and `financial_total_mismatch` is **not** overloaded (its trigger is numeric; a currency-model divergence is blocked *before* any Odoo total exists). |
| **Sub-reason** | `skip_reason = "divergent_presentment_currency"` in `technical_detail` (a data label, **not** a new `blocked_manual_review` enum) | The fixed six-item `blocked_manual_review` sub-reason vocabulary is **not** widened (DEC-014 §I); a `skipped` job carries no such enum. |
| **Operator message** | *"Automatic import not supported: divergent presentment currency (presentmentCurrencyCode ≠ currencyCode) — DEC-020."* | Plain-words unsupported-scope framing. |
| **Retry posture** | Terminal policy skip; **not** auto-retried; re-evaluated only when the order genuinely changes (new `updatedAt` → new `idempotency_key` → fresh policy evaluation) or via Area-6 `action_manual_retry` (whose allowed-from set includes `skipped`). | DEC-020 "blocked … before SO creation." |
| **Evidence payload** | both `currencyCode` + `presentmentCurrencyCode`, and both `shopMoney` + `presentmentMoney` for `totalPriceSet` (and the other total sets), as lossless Char. | DEC-020 mandatory capture in every case. |
| **Audit behaviour** | one job-log row on the skip transition via `job._transition_skipped(...)` → `_system_append` (redacted). | Merged mechanism. |

**Permitted policy skips (closed, enumerated set) [Proposed Task 012 decision]:**
exactly — divergent presentment currency (`skip_reason
= "divergent_presentment_currency"`); non-null `currentTotalDutiesSet`
(`unsupported_duties`, [Deferred / non-MVP]); `test: true` when
`order_import_include_test` is `False` (`test_order_excluded`); order already
cancelled at first import (`order_pre_cancelled`). No other policy skip exists;
all four are decided by the handler from the header data **before any Shopify
mutation or SO write** (there are none — the importer is read-only).

**Mechanism — reconsidered against the corrected CORE-R2 dispatcher (task §10)
[Proposed Task 012 decision — smaller design; keep proposed, coordinate with
CORE-R2]:** reaching a terminal `skipped` from inside a handler needs core to
provide a **handler-reachable skip path**, because the *currently merged*
dispatcher **unconditionally** marks a normally-returning handler `succeeded`
[Fact — repo code]. Two candidate core designs exist:

1. **Terminal-state-respect guard (RECOMMENDED — smallest, most general):** after
   `handler(job)` returns, `_invoke_handler` writes `succeeded` **only if the job
   is still non-terminal** (`if job.state not in TERMINAL_JOB_STATES`). The
   handler then simply calls the **existing** `job._transition_skipped(skip_reason,
   …)` and returns normally. This adds **no** new exception class, is a one-guard
   change, lets any handler self-terminalize, and **composes cleanly** with the
   final CORE-R2 slice that routes `ShopifyQuiescedError → _transition_skipped`
   (both produce a terminal state the guarded dispatcher respects — **no
   collision**, distinct `skip_reason` namespaces).
2. **`JobPolicySkip` exception (alternative):** a new `JobPolicySkip(message,
   technical_detail)` class + one `except` branch → `_transition_skipped`. Typed
   and explicit, but adds a public core exception that competes with
   `ShopifyQuiescedError` routing.

**Because CORE-R2 Slice 2A/2B is itself correcting the dispatcher**, the exact
mechanism is a **core-design decision the control room and the CORE-R2 owner
settle at integration time** — Task 012 adopts whichever the corrected dispatcher
standardizes; either yields **identical** Task-012 behaviour (terminal `skipped`,
no error class, `skip_reason` label). Crucially, if the corrected CORE-R2
dispatcher **already** respects handler-set terminal states (design 1), Task 012
needs **no core edit at all** — it only calls `job._transition_skipped(...)`.
The Task 012 dispatcher edit is therefore **conditional** (§14) and coordinated,
not unilaterally fixed here. Skips never collide with the CORE-R2
`ShopifyQuiescedError` (store-quiescence) routing: order-policy `skip_reason`
values are disjoint from the quiescence reason.

**Operator visibility / discoverability:** skipped jobs are terminal but
**visible and filterable in the Sync Center** (state `skipped`, filter on
`skip_reason`); the Error Center may surface the divergent-currency evidence.
Recovery is **Area-6 `action_manual_retry`** (allowed-from set includes
`skipped`) — re-evaluates policy; a genuinely changed order (new `updatedAt` →
new `idempotency_key`) gets a fresh evaluation automatically. Audit: one
`_transition_skipped` → `_system_append` row carrying `skip_reason` + evidence.

**Why `skipped` over `failed_final` / `blocked_manual_review`:** it is **not** a
failure (`failed_final` would misclassify an out-of-scope order as a defect and
imply retry-budget exhaustion); it is **not** an ambiguity a human can *match*
(none of the six fixed `blocked_manual_review` sub-reasons fits, and DEC-014 §I
forbids widening that vocabulary); and `odoo_validation_configuration` wrongly
implies the operator can *fix* it into scope. `skipped` (policy) is the only
routing that honours DEC-020 without inventing an error class or a
`blocked_manual_review` sub-reason, and without overloading
`financial_total_mismatch`.

---

## 11. ORDERS_UPDATED and reconciliation posture (task §12)

**[Accepted decision — DEC-014 §J, verbatim]:** an `ORDERS_UPDATED` webhook (or
reconciliation-detected change) for an already-imported order *"may refresh
Shopify-side evidence/audit data only. It must **never** silently update the
existing Odoo sale order's line quantities, prices, taxes, shipping, discounts,
invoices, payments, refunds, or fulfillment state, under any trigger."* The
webhook and reconciliation paths behave identically; neither auto-applies.

**[Proposed Task 012 decision] (D-012-12):** when `order_import_sync(store,
order_gid)` runs with an **existing** binding:

- **Evidence refresh:** update **only** the binding's snapshot fields
  (`shopify_financial_status_snapshot`, `shopify_fulfillment_status_snapshot`,
  `shopify_cancelled_at`/`shopify_cancel_reason`, timestamps, and — for audit —
  the money Char snapshots) and stamp `shopify_last_evidence_refresh_at`.
- **Permitted updates:** timestamp/status snapshots and money-evidence
  snapshots on the **binding** only. **Zero writes** to the `sale.order` or its
  lines — enforced by a **source-level guard test** (single-`execute` AST check
  + zero-SO-write assertion; the strongest DEC-014 §J protection available
  pre-UI).
- **Divergence detection:** if a refresh changes financial/fulfillment status or
  cancellation, write **one** `event_type='note'` job-log row (no job-state
  transition is semantically implied for a pure refresh; the job itself succeeds)
  and, when the divergence is **financial**, route it through the same
  total-check guard / `financial_total_mismatch` / human-review posture — never
  an auto-mutation.
- **Audit snapshot + manual-review route:** the note row is the audit; the Error
  Center links the operator to review; the SO is **never** auto-cancelled or
  auto-edited (a Shopify cancellation → snapshot + note only; operator acts).
- **Repeated-event idempotency:** a repeat `ORDERS_UPDATED` for the same
  `updatedAt` collides on `idempotency_key` (payload_hash = `updatedAt`) [Fact —
  repo code]; a genuinely changed order gets a new key and a fresh evidence
  refresh. `operation_scope_key` serializes concurrent same-order jobs and
  clears on terminal (so a completed refresh never blocks the next).

The connector never silently mutates quantities, unit prices, taxes, discounts,
shipping, customer, invoices, payments, refunds, or fulfillment state — the full
DEC-014 §J list.

---

## 12. Job and failure contract (task §13)

**[Proposed Task 012 decision] / [Fact — repo code]:**

- **`job_type`:** `order_import_sync` (registered via `job_type` `selection_add`),
  gated on `sale_domain_enabled`.
- **Job source:** one of `webhook`, `manual_sync`, `scheduled_sync`,
  `reconciliation` (four of the six fixed sources; DEC-018) with the DEC-019
  `trigger_origin` sub-classification.
- **Trigger origin:** `ORDERS_CREATE`/`ORDERS_UPDATED` webhook, scheduled sync,
  manual sync, or reconciliation — never webhook-only (DEC-005 layered sync).
- **Idempotency key:** `payload_hash = Order.updatedAt`; `idempotency_key =
  store|job_type|res_model|res_id|shopify_target_gid|payload_hash`, `UNIQUE(store,
  idempotency_key)`, **persists into terminal states** (dedup/history).
- **Operation-scope key:** `store|res_model|res_id|shopify_target_gid`,
  `UNIQUE(store, operation_scope_key)`, **cleared on terminal / superseded /
  no-res_model** — serializes concurrent non-terminal same-order jobs.
- **Job targeting:** `res_model='shopify.connector.store'`, `res_id=store.id`,
  `shopify_target_gid=<Order GID>` (documented deviation from the bind-row
  precedent, because on first import the binding does not yet exist and the
  merged `operation_scope_key` clears itself when `res_model` is empty — this
  targeting keeps it populated and serializes per-order from the first enqueue)
  [Fact — repo code].
- **`expected_connection_generation`:** captured at enqueue from
  `store.connection_generation` [Fact — repo code]; the admission gate refuses a
  stale generation (though it cannot fire live until a later CORE-R2 slice bumps
  the generation — §0).
- **CORE-R2 `execute_business` requirement:** every Shopify-touching read runs
  inside `with execute_business(job, store, query, variables) as result:` —
  the merged admission context-manager (lease + state/generation gate) — with
  the caller's reconciliation inside the `with` body [Fact — repo code].
- **LC-1 job-type ondelete:** the `order_import_sync` `selection_add` registers
  `ondelete = lambda recs: recs._reassign_to_historic_job_type()` **from day
  one** (LC-1 precedes Task 012) so no retrofit is needed [Accepted-plan —
  DEC-030; **LC-1 not yet merged**, §0].
- **Error classes used** (all from the fixed 16; **no 17th class**): `mapping_missing`
  (unmatched product → `failed_retryable`), `ambiguous_match` (→
  `blocked_manual_review`), `duplicate_risk` (→ `blocked_manual_review`),
  `financial_total_mismatch` (→ `failed_retryable`, CONSERVATIVE_NEVER_SILENT),
  `data_shape_schema_mismatch` (→ `failed_retryable`),
  `odoo_validation_configuration` (unconfigured fallback/pricelist/tax, unset
  confirmation policy → `failed_retryable`), plus read-path
  throttle/temporary-network → **AUTO_RETRY**, and `unknown_system_error` →
  single safety-net retry.
- **States:** the merged 10-state model — non-terminal `draft`/`queued`/`running`;
  loop-back `retry_waiting`/`failed_retryable`/`blocked_manual_review`; terminal
  `succeeded`/`failed_final`/`skipped`/`cancelled`.
- **Retryable vs manual vs policy skip:** AUTO_RETRY = throttle/network reads,
  concurrency; MANUAL_FIX_THEN_RETRY = `mapping_missing`,
  `data_shape_schema_mismatch`, `odoo_validation_configuration`;
  CONSERVATIVE_NEVER_SILENT = `financial_total_mismatch`; MANUAL_REVIEW =
  `ambiguous_match`, `duplicate_risk`; **policy skip** = divergent
  currency/duties/test/pre-cancelled → `skipped` (§10). **No blind retry**
  (RA-014) of anything.
- **Technical-detail payload + PII redaction:** every transition logs via
  `_system_append` (→ `redact()`); the importer applies a **module-local
  `REDACTION_EXTENSION` pre-redaction pass** (email/phone/name/address masked)
  **before** composing any `message`/`technical_detail`/`payload_snapshot`,
  because `_system_append` applies only the default `redact()` patterns and not
  `extra_secrets` [Fact — repo code]. The shared PII key list migrates into the
  core tool at W1.
- **Financial-evidence payload:** the full component breakdown (each Shopify
  money Char, each computed Odoo amount, each tolerance term, per-tax buckets,
  per-line discount representation) in `technical_detail` on a
  `financial_total_mismatch` — feeding the Error-Center inline breakdown
  (DEC-014 §C).

**No implementation occurs here** — this fixes the contract only.

---

## 13. Security and privacy (task §14)

**[Proposed Task 012 decision], aligned with future SEC-1 without depending on
unimplemented SEC-1 code:**

- **Groups (ACL, `ir.model.access.csv`):** binding + tax-mapping rows —
  auditor/operator/reviewer **read-only**, admin **rwc (no unlink)**, exactly
  the merged customer-binding pattern; **no new security groups**.
- **Who may run/import/review:** operators run/retry order-import jobs;
  reviewers/auditors read bindings and financial evidence; admins manage tax
  mappings and settings. Financial-evidence visibility follows the same
  read tier (auditor/operator/reviewer).
- **Protected customer fields:** customer PII (name/email/phone/address) lives on
  `res.partner` (Task 011), **not** on the order binding (§3.3) — a deliberate
  privacy boundary. Odoo's own partner ACLs govern PII visibility; the connector
  adds none of it to its own tables.
- **No raw GraphQL response persistence:** the raw Order payload is **never**
  stored; only the mapped snapshot Char fields + the redacted evidence JSON are
  persisted.
- **No token persistence / no secret in logs:** credentials never leave the
  merged credential service; a handler with an in-flight secret passes it as
  `extra_secrets` for value-level scrubbing (default `_system_append` uses
  `redact()` only).
- **No full address/customer payload in logs:** the `REDACTION_EXTENSION`
  pre-redaction pass strips email/phone/name/address from any composed log text
  (§12).
- **Company isolation:** all binding/tax-mapping rows are `store_id`-scoped and
  the SO `company_id` is store-driven — no cross-company data flow.
- **`sudo` inventory:** the only sanctioned `sudo()` is inside the merged
  `_system_append` (log write); the importer performs **no** other `sudo()`.
- **Audit requirements:** every state transition and every evidence refresh
  writes an append-only `shopify.connector.job.log` row (`ondelete='restrict'`);
  binding audit fields record `customer_resolution` and import/refresh
  timestamps.
- **RPC boundaries:** the binding and tax-mapping models expose no custom public
  RPC method beyond standard ORM ACL-gated access; the importer service is not
  RPC-exposed to portal/public users.
- **SEC-1 seam (no dependency):** the binding declares `_odoo_binding_field_name()
  → 'sale_order_id'` so a future SEC-1 pass can harden it uniformly — a
  **declaration**, not a runtime dependency on SEC-1.

---

## 14. Exact implementation file map (task §15)

**[Proposed Task 012 decision] — exhaustive future allowed-file list** (the
locked prompt, packet §15, carries the authoritative copy):

| Allowed file | Nature |
| --- | --- |
| `addons/shopify_connector_sale/__manifest__.py` | depends += `shopify_connector_product`, `sale`; version bump |
| `addons/shopify_connector_sale/models/__init__.py` | register new models |
| `addons/shopify_connector_sale/models/shopify_connector_order_binding.py` | NEW — order binding (§3) |
| `addons/shopify_connector_sale/models/shopify_connector_order_importer.py` | NEW — importer service + job seams + `ORDER_IMPORT_QUERY` + `REDACTION_EXTENSION` |
| `addons/shopify_connector_sale/models/shopify_connector_sale_order_line.py` | NEW — `shopify_line_item_gid` only |
| `addons/shopify_connector_sale/models/shopify_connector_store_settings.py` | order-policy settings fields (§8/§10; incl. `order_import_confirmation_policy` no-default, `order_import_include_test`, `order_tax_autocreate` default False, `order_company_id`, `order_pricelist_id`, `order_sales_team_id`, `sale_order_last_import_checkpoint_at` inert) |
| `addons/shopify_connector_sale/models/shopify_connector_tax_mapping.py` | NEW — `shopify.connector.tax.mapping` (§5) |
| `addons/shopify_connector_sale/security/ir.model.access.csv` | binding + tax-mapping ACL rows only |
| `addons/shopify_connector_sale/tests/{__init__,test_order_binding,test_order_import_mapping,test_order_totals_guard,test_order_tax_resolution,test_order_duplicate_prevention,test_order_customer_resolution}.py` | NEW test suite (§15) |
| `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py` | **CONDITIONAL, coordinated-with-CORE-R2 core seam (§10)** — the handler-reachable skip path. **If** the corrected CORE-R2 dispatcher already respects handler-set terminal states, Task 012 edits **nothing here** and just calls `job._transition_skipped(...)`; **else** Task 012 adds the minimal terminal-state-respect guard (recommended) or the `JobPolicySkip` exception + one `except` branch → `_transition_skipped`, and nothing else |
| `addons/shopify_connector_core/tests/test_job_dispatch.py` | append only the skip-routing test (only if the core seam is added by Task 012, not by CORE-R2) |
| `docs/05-qa/task-012-order-import-validation-results.md` | NEW validation record |
| `docs/05-qa/architecture-review-log.md` | append one AR row |
| `docs/01-research/research-handoff.md` | top entry |

**Forbidden categories (exhaustive) [Proposed Task 012 decision]:** every
**other** `shopify_connector_core` file and every `shopify_connector_product`
file; `adams_base`; any **inventory** model/logic (Task 013); any **fulfillment**
write-back (Task 014); any **product export** (Task 015); any **webhook**
receiver/controller (W1); any **UI** view/menu/wizard/client-action (UI phase;
the Error-Center extensions are UI-phase scope); any **accounting entry**,
**invoice**, **payment**, or **refund** model/logic; any **tax engine**
(rate-matching only); any **presentment-currency SO** or per-currency pricelist
provisioning; any use of **`read_all_orders`** or all-orders enumeration; any
enumeration/scan **trigger** (Area 6); any OAuth/credential/CI/workflow/
Dockerfile/`requirements*.txt`; `plain dev`; `main`.

---

## 15. Test fixture catalogue and acceptance criteria (task §16)

**[Proposed Task 012 decision]** Every fixture below must exist with the stated
acceptance criterion. Fixtures map to the §14 test files. **No runtime
acceptance is claimed here** — this is the required matrix.

| # | Fixture | Acceptance criterion |
| --- | --- | --- |
| 1 | basic order | one SO + lines + binding created; guard passes; `succeeded` |
| 2 | repeat import (same GID) | no duplicate SO; binding matched; evidence-refresh only |
| 3 | duplicate webhook (same `updatedAt`) | `idempotency_key` collision; no second job effect |
| 4 | unmatched product | whole-order hold `mapping_missing`/`failed_retryable`; SKU/GID named; no partial SO |
| 5 | product mapping later resolved | on retry the held job completes; one SO |
| 6 | existing customer (binding) | partner reused; `customer_resolution=existing_binding`; parent unmutated |
| 7 | created customer | new person partner + binding; `created`; MBQ-59 gate honoured |
| 8 | fallback customer (no PII) | `customer_fallback_partner_id` used; `fallback`; unset → `odoo_validation_configuration` |
| 9 | ambiguous customer | no SO; `blocked_manual_review`/`ambiguous_match`; exact §8.2 candidate JSON |
| 10 | protected / no-PII order | fallback path; no invented PII; audit marker |
| 11 | separate billing/shipping addresses | two child partners (`invoice`/`delivery`); normalized-tuple dedup; parent unmutated |
| 12 | company customer | person-only; `is_company` unset; `company` captured, no company partner created |
| 13 | taxes included | `price_include_override='tax_included'`; guard passes |
| 14 | taxes excluded | `price_include_override='tax_excluded'`; guard passes |
| 15 | multiple tax rates | each rate mapped/matched; per-group `O`; guard passes |
| 16 | mixed taxed/untaxed | per-signature residual buckets reconcile; tax component passes |
| 17 | line discounts | baked into `price_unit`; not double-subtracted |
| 18 | order discounts | native % if faithful else exact adjustment line; total exact |
| 19 | high-value discount | faithful-% fails → exact tax-preserving adjustment line; guard passes (Example D) |
| 20 | tax-preserving residual line | residual inherits source `tax_ids`/inclusion; recomputed tax matches `totalTaxSet` |
| 21 | shipping | one SO line per shipping node; its `taxLines` mapped; counted in `L` |
| 22 | tip | one `"Shopify Tip"` line when `totalTipReceivedSet>0`; no tax |
| 23 | zero-decimal currency (JPY) | `r=1.0`; guard passes (Example B) |
| 24 | three-decimal currency (BHD) | `r=0.001`; clean case passes; risk case flagged; empirical-check note |
| 25 | divergent currency | `skipped` (policy); no SO; both currencies+moneys captured; not `financial_total_mismatch` |
| 26 | malformed money | `data_shape_schema_mismatch` hold; no SO |
| 27 | rate/ratePercentage mismatch | `data_shape_schema_mismatch` hold; never keyed from one field |
| 28 | total mismatch | `financial_total_mismatch`; rolled back; never silent/auto-retried (Example F) |
| 29 | missing line | LINE + TOTAL components fail; rejected (Example F) |
| 30 | 100 lines (single page) | all lines imported; guard passes; performance within budget |
| 31 | paginated line items (>100) | full cursor loop; all lines imported; no truncation; cursors not persisted |
| 32 | ORDERS_UPDATED divergence | evidence refresh only; zero SO writes (source-level guard test); note row |
| 33 | rollback / idempotency | savepoint rollback leaves no partial SO; binding sole anchor |
| 34 | generation mismatch / disconnecting | admission refusal path exercised (per merged behaviour); no live disconnect assumed |
| 35 | permissions | ACL matrix (read tiers; admin rwc no unlink) |
| 36 | PII / token leak | `REDACTION_EXTENSION` masks email/phone/name/address; no token/GraphQL body in logs |
| 37 | performance budget | order-import job within the cited `performance-budgets.md` row |
| + | custom line item (null variant) | `"Shopify Custom Item"` service product; guard unaffected |
| + | gift-card line | imports as line + note; no gift-card accounting |
| + | duties (currentTotalDutiesSet) | `skipped` (policy); no SO |
| + | test order (`test:true`) | `skipped` unless `order_import_include_test`; no SO |
| + | unset confirmation policy | `odoo_validation_configuration` hold; readiness warning |
| 38 | taxesIncluded=true ordinary | `U_ex = G − totalTaxSet`; back-out once; guard passes (Example G) |
| 39 | taxesIncluded=true + order discount | inclusive `OC` residual inherits inclusion; tax not removed twice (Example H) |
| 40 | many-small-lines global-rounding counterexample | Example I: `tol_tax=0.5r(S+O)` accepts `0.16` divergence; `K=#groups` would false-reject; missing line still caught by lines component |
| 41 | multiple taxes on one line | each `TaxLine` = an `S` event; each Odoo tax = an `O` event; guard passes |
| 42 | multiple global tax groups | `O = #groups` under `round_globally`; per-group reconcile |
| 43 | tax repartition (multi tax-repartition line) | `O` counts each rounding repartition line; guard passes |
| 44 | shipping-tax rounding | shipping `taxLines` counted in `S`; shipping tax reconciles |
| 45 | line-level allocation not double-subtracted | line-level discount stays in `price_unit`; never in `OC`; total exact |
| 46 | order-level allocation correctly subtracted | `OC` (targetSelection=ALL/code) subtracted once; total exact |
| 47 | shipping discount not double-subtracted | `discountedPriceSet` nets it; shipping allocations not re-subtracted |
| 48 | independent line/shipping/discount pagination | three separate cursor loops; all nodes collected; no first-page dup |
| 49 | one connection advances, other two unchanged | advancing `lineItems` does not re-page/duplicate `shippingLines`/`discountApplications` |
| 50 | repeated `endCursor` (no progress) | cursor-progress check → `data_shape_schema_mismatch`; no infinite loop |
| 51 | duplicate node across pages | node-id dedup → `data_shape_schema_mismatch`; never silently merged |
| 52 | changed `updatedAt` between pages | torn read → `concurrency_race_conflict` (AUTO_RETRY); no SO/binding; lease released |
| 53 | GraphQL requested-cost near/over threshold | `requestedQueryCost`/`actualQueryCost` captured; page size not auto-expanded; live-tuning deferred |
| 54 | ambiguous tax fallback (>1 candidate) | `odoo_validation_configuration` ambiguous hold; first candidate never chosen |
| 55 | tax company mismatch | candidate with `company_id ≠ order_company_id` rejected; hold, not import |

Source-level guards (AST): single `execute()` call; zero mutation strings; zero
core/product file edits. Runtime: full three-suite Odoo.sh run green before
merge (SRR-06), concurrency caveat carried verbatim (architecture §5.12).
**Live-Shopify: none required** (read-only; VAL-B2 independent).

---

## 16. Locked-prompt status (task §17)

The authoritative locked implementation prompt lives in **packet §15**, updated
in this PR to be **file-exact, decision-complete, dependency-complete,
test-complete, and rollback-complete**. It states explicitly that it is
**unusable until a separate control-room gate** issues it, that the
**capability prerequisites (§0.1) must hold in `Shopify-connector`** — SRR-03
CLOSED; protected/guarded product import + complete variant bindings; protected/
guarded customer import + indexed normalized-email matching; no unguarded
product/customer Shopify call remaining; LC-1 merged + DEC-030 accepted
(CORE-R1 already satisfied) — **however those capabilities arrive** (direct
merge of #150/#151 or a subsuming CORE-R2 integration PR), and that **no live
Shopify request occurs during implementation or its tests** (read-only +
fixtures). This closure does **not** open the gate.

---

## 17. Adversarial self-critic (task §13/§18) — re-run after the correction round

Strict adversarial review re-run against the review-`4690680028` vectors; each
confirmed problem is corrected in this closure (and the packet).

| # | Risk (this correction round) | Verdict | Resolution |
| --- | --- | --- | --- |
| 1 | double-counted / omitted shipping / tip / discount | **CONFIRMED → FIXED** | one canonical ledger `U_ex = M + H + T` (tax-excl) with each component **once**; `OC` = order-level/code only; shipping via `discountedPriceSet` (allocations not re-subtracted); tips once; ledger self-check vs `totalPriceSet` (§6.1) |
| 2 | tax-inclusive gross/net mismatch | **CONFIRMED → FIXED** | tax-inclusive `U_ex = G − totalTaxSet`; Odoo backs out via `price_include_override='tax_included'`; adjustment lines inherit inclusion; tax removed once each side (§6.3, Examples G/H) |
| 3 | double-subtracted discounts | **CONFIRMED → FIXED** | line-level stays in `price_unit`/`discountedTotalSet`, never in `OC`; explicit `targetSelection==ALL`/code classification; proof of no double subtraction (§6.1-A, §7) |
| 4 | global-rounding false rejection | **CONFIRMED → FIXED** | `tol_tax = 0.5r(S+O)` proven via triangle inequality on both systems' rounding events; `K=#groups` withdrawn; many-small-lines counterexample (Example I) |
| 5 | tolerance so loose it hides a missing line | NOT-A-PROBLEM | the **lines** component (`0.5rL`, tight) catches merchandise shifts; a wrong rate is blocked by the canonical-key mapping; `tol_tax` only absorbs legitimate rounding (§6.4 proof + Example I) |
| 6 | cursor duplication | **CONFIRMED → FIXED** | Option-A separate cursor loops; header first-pages not re-fetched; node-id dedup; cursor-progress check (§4.2) |
| 7 | torn reads | **CONFIRMED → FIXED** | `updatedAt` verified on every page; change → `concurrency_race_conflict` (AUTO_RETRY), lease released, no SO/binding (§4.2.1) |
| 8 | partial SO creation before pagination completes | **CONFIRMED → FIXED** | **no** Odoo business write until all three connections fully collected + validated; then one savepoint (§4.2, §6) |
| 9 | tax from the wrong company | **CONFIRMED → FIXED** | `account_tax_id.company_id == order_company_id` enforced at mapping create, resolution, and via `order_company_id` immutability (§5.5) |
| 10 | ambiguous tax selected silently | **CONFIRMED → FIXED** | >1 candidate → ambiguous configuration hold; zero → hold; first never chosen silently (§5.2/§5.5) |
| 11 | stale CORE-R2 dependency sequence | **CONFIRMED → FIXED** | prerequisites now capability-based; #150/#151 direct-merge requirement withdrawn; CORE-R1 recorded satisfied; staging strategy documented (§0.1) |
| 12 | unsupported query-cost claim | **CONFIRMED → FIXED** | "well under the cap" removed; page sizes are named provisional defaults; cost telemetry + dev-store live-read before tuning (§4.3) |
| 13 | `float_compare` "preserves Decimal precision" claim | **CONFIRMED → FIXED** | Decimal/string canonicalization is the identity layer; `float_compare` is only the boundary comparison to Odoo's existing Float `amount` (§5.2, §6.2) |
| 14 | money in lossy Float | **CONFIRMED (round 1) → FIXED** | Char/exact-decimal-string snapshots + Decimal math; single Decimal→Odoo write boundary (§3.1, §6.2) |
| 15 | divergent currency enters Odoo | MITIGATED | blocked before SO creation → `skipped` policy, no error class (§10) |
| 16 | customer/address duplication | MITIGATED | email/binding anchor + normalized-tuple child dedup; parent never mutated (§8) |
| 17 | silent mutation of imported order | MITIGATED | evidence-refresh-only + source-level zero-SO-write guard (§11) |
| 18 | raw PII/token/GraphQL-body log leak | MITIGATED | `REDACTION_EXTENSION` + no raw payload/token persistence (§13); cost telemetry logs numbers only |
| 19 | order binding not sole idempotency anchor | MITIGATED | dual uniqueness + `operation_scope_key` + `idempotency_key` (§3.3/§12) |
| 20 | accidental accounting/refund/payment scope | NOT-A-PROBLEM | forbidden categories exhaustive; RA-010 unmet; evidence-only (§14) |
| 21 | accidental implementation authorization | NOT-A-PROBLEM | closure + packet deny gate/code/live-call; prompt unusable-until-gate; capability prerequisites unmet (§0/§16/§19) |

**Rejected-approach guardrails re-checked (all revisit conditions UNMET, none
re-proposed):** RA-006 (name/fuzzy matching — email-only kept), RA-010
(accounting automation — evidence-only kept), RA-014/RA-015/RA-017 (blind
retry / never-retry / binding-alone — class-conditional retry + per-operation
`idempotency_key` kept), RA-005 (`ir.model.data` dedup — binding model kept),
RA-021 (assumed equivalence without documented semantics — the guard has an
explicit, proven tolerance + documented rounding).

---

## 18. Remaining dependencies and open questions

**Capability prerequisites (all currently unmet — §0.1; PR-merge-agnostic):**
1. **SRR-03 CLOSED** — CORE-R2 disconnect quiescence proven runtime-green (the
   register forbids merging/enabling/live-validating any Shopify-calling domain
   handler until then; parallel *development* is allowed).
2. **Protected/guarded product import + complete product/variant bindings** in
   `Shopify-connector` (order lines resolve; product Shopify calls run through
   `execute_business`).
3. **Protected/guarded customer import + indexed normalized-email matching** in
   `Shopify-connector` (guest path reuses the indexed lookup at volume; customer
   Shopify calls guarded).
4. **No unguarded product/customer Shopify call remains** — the public generic
   `execute` entry is closed.
5. **Task LC-1 merged (DEC-030 accepted)** — so `_reassign_to_historic_job_type`
   exists for the new `job_type`'s `ondelete`.
6. Acceptance of this closure + the packet (D-012 decisions, PD-3/4/5/6) and the
   order-domain gate act, then the control-room issues the prompt.

These capabilities may arrive as direct merges of PR #150/#151 **or** as a single
subsuming CORE-R2 Slice-2B integration PR (§0.1) — Task 012 is indifferent to
which. **CORE-R1 is already merged (satisfied, not pending).**

**Open questions (logged, not resolved):**
- Verbatim GraphQL `THROTTLED` error-code string (docs show only `200 Throttled`).
- Shopify three-decimal-currency storage/rounding policy (undocumented) →
  named dev-store empirical check before onboarding such a store.
- Empirical confirmation that the `OC` classification (`targetSelection==ALL` /
  code-based) reproduces `totalPriceSet` on a real mixed line-level + order-level
  + code discount order → named dev-store check before a discount-heavy store.
- Whether `res.partner.company_name` is the right sink for `MailingAddress.company`
  (confirm at build time; `is_company` stays False regardless).
- The exact core skip seam (terminal-state-respect guard vs `JobPolicySkip`) is
  settled with the CORE-R2 owner at integration; Task 012 adopts the standardized
  one and may need **no** core edit (§10/§14).
- GraphQL requested/actual query cost for the chosen page sizes — measured on an
  authorized dev store before production tuning (§4.3).

---

## 19. Confirmation

This session produced **documentation only**. It wrote **no code**, created **no
Odoo module/model/view/manifest/test**, opened **no gate**, granted **no
implementation authorization**, and made **no live Shopify request** (all
platform facts came from official documentation/source reads, not from any
merchant store). Every proposed choice is **[Proposed Task 012 decision]**,
pending ChatGPT control-room review. The no-code gate (CLAUDE.md §4–§5) remains
in force.
