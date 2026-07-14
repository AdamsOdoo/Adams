# Task 012 — Order Import: Final Pre-Implementation Decision Closure

> **Status: Proposed for ChatGPT control-room review. NOT accepted.
> Documentation and architecture only.** This document opens **no gate**,
> authorizes **no code**, and describes **no live Shopify request**. It
> exists to make Task 012 (Shopify order import into Odoo `sale.order`)
> *decision-complete* so that a separate control-room gate can issue the
> locked prompt (packet §15) immediately after its prerequisites merge.
>
> **Prerequisites that must merge first (none is merged as of this
> session — see §0):** CORE-R2 full SRR-03 remediation, PR #150 (Task
> 011B), PR #151 (Task 010B), and Task LC-1. Producing this closure does
> **not** change any of their states.
>
> Companion files: the implementation packet
> [`../07-implementation-plan/task-012-order-import-implementation-packet.md`](../07-implementation-plan/task-012-order-import-implementation-packet.md)
> (carries the D-012-1…12 decisions and the locked prompt) and the
> proposed-scope brief
> [`../07-implementation-plan/task-012-order-import-proposed.md`](../07-implementation-plan/task-012-order-import-proposed.md).
> This closure **supersedes** the packet where they differ; the packet is
> updated in the same PR to match (money-storage type, pagination,
> tolerance derivation, divergent-currency routing).

---

## 0. Verified state at closure time (2026-07-14)

| Item | Required | Verified state | Class |
| --- | --- | --- | --- |
| `Shopify-connector` tip | `912801508155c6358e8f5f1a7a0aaf01ae573675` | `origin/Shopify-connector` HEAD = `9128015…573675` (this branch is based on it) | [Fact — repo] |
| PR #150 (Task 011B) | accepted, draft/unmerged | `state:open, draft:true, merged:false`; base `912801…573675` | [Fact — repo] |
| PR #151 (Task 010B) | accepted, draft/unmerged | `state:open, draft:true, merged:false`; base `912801…573675` | [Fact — repo] |
| CORE-R2 / SRR-03 | remediation open | Foundation Slice 1 merged (PR #156, `c0d4559`); **SRR-03 remains OPEN**; disconnect controller / epoch bump / call-site migration deferred | [Fact — repo] |
| Task LC-1 | not merged | design-only; DEC-030 unaccepted; merged `job.py` has no `historic_domain_job`, no `original_job_type`, no `_reassign_to_historic_job_type` | [Fact — repo] |
| Working tree | clean | clean | [Fact — repo] |

**Consequence [Accepted decision / CLAUDE.md §5]:** Task 012 code cannot be
written or its live validation run until the four prerequisites above are
merged runtime-green. This closure is *planning* work permitted under the
research/governance phase; it is not an implementation authorization.

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
| shopify.dev …/2026-07/objects/LineItem | Accessible | `quantity`(ordered incl. refunded/removed) vs `currentQuantity`(excl.); `variant`/`product` nullable; `discountedUnitPriceSet` excludes order-level/code discounts; `discountAllocations`/`taxLines`/`customAttributes` are plain lists |
| shopify.dev …/2026-07/interfaces/DiscountApplication + /objects/DiscountAllocation | Accessible | `allocationMethod`(ACROSS/EACH), `targetType`(LINE_ITEM/SHIPPING_LINE); `DiscountAllocation.allocatedAmountSet:MoneyBag!` |
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
  originalUnitPriceSet{shopMoney{amount}} discountedUnitPriceSet{shopMoney{amount}}
  discountAllocations{ allocatedAmountSet{shopMoney{amount} presentmentMoney{amount}}
  discountApplication{ index targetType allocationMethod targetSelection } }
  taxLines{ title rate ratePercentage priceSet{shopMoney{amount}} channelLiable }
  customAttributes{ key value } } pageInfo{ hasNextPage endCursor } }`. The
  line-level `discountAllocations`, `taxLines`, `customAttributes` are **plain
  lists** [Fact — official] — no nested pagination needed.
- **Shipping lines** (connection — paginate): `shippingLines(first: 50){ nodes{
  id title code custom discountedPriceSet{shopMoney{amount}}
  taxLines{ title rate ratePercentage priceSet{shopMoney{amount}} } }
  pageInfo{ hasNextPage endCursor } }`.
- **Discount applications** (connection — paginate): `discountApplications(first:
  50){ nodes{ index allocationMethod targetSelection targetType } pageInfo{
  hasNextPage endCursor } }` (evidence/reconciliation; per-line money comes from
  each line's `discountAllocations`).

### 4.2 Pagination (task §5 — resolves adversarial findings #9 and the packet's
100-line rejection)

**[Fact — official]** `Order.lineItems`, `Order.shippingLines`, and
`Order.discountApplications` are **connections** (`…Connection!`) with page size
max **250**; `pageInfo.hasNextPage` signals more pages; `endCursor` positions
the next page. `Order.taxLines` and every line-level list are **not**
connections.

**[Proposed Task 012 decision — revises the packet's earlier "hold on
`hasNextPage`" stance]:** the importer **fully paginates** each of the three
order-level connections with a bounded cursor loop, because a large legitimate
order (e.g. 150 lines) is **not** a malformed payload and must not be rejected
as one:

- **Page size:** `first: 100` for line items; `first: 50` for shipping lines
  and discount applications (well under the 250 ceiling and the 1,000-point
  single-query cost cap, §4.3).
- **Loop:** while `pageInfo.hasNextPage`, re-request the same connection with
  `after: endCursor`, accumulating `nodes`; **cursors are used only within this
  single order read and are never persisted** ([Fact — official: cursor
  durability undocumented] ⇒ no cross-session reuse).
- **Bounded:** a hard page-count ceiling (`ORDER_PAGE_LIMIT`, default 50 pages
  = up to 5,000 line items) prevents an unbounded loop; exceeding it →
  `data_shape_schema_mismatch` hold **with a log line naming the ceiling** (no
  silent truncation — architecture §5 "no silent caps").
- **Malformed-page handling:** a page missing `pageInfo`, or a non-null field
  returning null, or a node failing shape validation → `data_shape_schema_mismatch`
  (`failed_retryable`) — this is reserved for genuinely malformed shapes, **not**
  for large-but-valid orders.
- **Backstop:** the total-check guard (§6) is the mathematical backstop — a
  truncated read can never reconcile and would be caught anyway — but
  pagination is the primary mechanism, not the guard.

The `100 lines` fixture (single page) and the `paginated line items` fixture
(multi-page) in §15 test both paths.

### 4.3 Cost, throttling, deleted/missing, 60-day scope, schema mismatch

- **Cost / throttle [Fact — official]:** GraphQL is metered by calculated query
  cost (leaky bucket; single query ≤ **1,000 points**; connection `first:N`
  inflates cost). The merged client surfaces `throttleStatus{maximumAvailable,
  currentlyAvailable, restoreRate}` verbatim; a `200 Throttled` response →
  existing `ERROR_THROTTLE` class → **AUTO_RETRY** with backoff (merged
  behaviour, DEC-009). Task 012 adds **no** new pacing constant; page sizes are
  chosen to stay well under the cost cap.
- **Deleted / missing order [Proposed Task 012 decision]:** `order(id:)`
  returning `null` (order deleted/not visible) → `data_shape_schema_mismatch`
  (`failed_retryable`) naming the GID; never a partial import, never a silent
  success.
- **60-day scope [Fact — official]:** apps see only the **last 60 days** of
  orders without the approval-gated `read_all_orders` scope. Task 012 is
  **`read_orders`-only** — the 60-day window is a documented setup limitation,
  not a design defect; historic backfill is out of scope until a separately
  approved `read_all_orders` request (`read_all_orders` is a **[Deferred /
  non-MVP]** forbidden capability, §14).
- **Schema-mismatch routing [Accepted decision — DEC-009]:** any unexpected
  shape (null where non-null expected, unknown enum that blocks mapping,
  over-ceiling pagination) → `data_shape_schema_mismatch` (`failed_retryable`,
  "manual fix then retry"). **No mutation** ever occurs on any path.

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
   price_include)`). A hit resolves immediately.
2. **Existing-tax rate match.** Decimal-safe match on `(company_id,
   type_tax_use='sale', amount_type='percent', price-inclusion per
   `Order.taxesIncluded` via `price_include_override`)` where the candidate
   `account.tax.amount` canonicalizes (same rule as the key) to the Shopify
   canonical key — compared with `float_compare(…, precision_digits=6) == 0`,
   **never** raw float equality. Attach via `tax_ids`.
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
  `round_globally`, because that determines the tolerance's `K` (§6) — the
  connector **reads** this setting, never changes it.
- **Operator configuration:** operators map rates in `shopify.connector.tax.mapping`
  (shell/import until the settings-area UI phase); `order_tax_autocreate` stays
  `False` unless an admin deliberately enables it with the warning shown.
- **Test matrix:** taxes-included vs excluded; single rate; two rates on one
  order; mixed taxed + untaxed lines; a fractional rate (`8.375%`); `5.0`/`5.00`/
  `5.000` canonical-key equivalence; `rate`/`ratePercentage` disagreement →
  schema hold; null rate → schema hold; mapping hit; existing-tax match;
  unmatched → configuration hold; `order_tax_autocreate` default-False (no
  create) and opt-in create + audit line + dedup; `round_globally` vs
  `round_per_line` tolerance (§6). **No acceptance is claimed** — these are the
  fixtures the implementation must pass.

---

## 6. MBQ-56 — financial total-check guard (task §7)

The guard is **mandatory, permanent, non-configurable, never silent, never
auto-retried** [Accepted decision — DEC-014 §F, DEC-007 §6, DEC-009]. This
section fixes its exact comparison mechanism. **Formulas (§6.1) are separated
from worked examples (§6.2).**

### 6.1 Formulas

Let `r = order_currency.rounding` (Odoo `res.currency.rounding`; default `0.01`;
JPY `1.0`; three-decimal `0.001`) [Fact — official]. Odoo derives
`decimal_places = ceil(log10(1/r))` and all comparisons use
`float_compare(precision_rounding=r)` [Fact — official].

After building the full SO inside one savepoint, the guard evaluates **four
checks** (three components + the total); **a breach in any one** rolls back the
savepoint (no SO persists) and classifies `financial_total_mismatch`
(CONSERVATIVE_NEVER_SILENT → `failed_retryable`, never auto-retried), with the
full component breakdown in `job.log.technical_detail` JSON.

1. **Lines:** `|odoo_untaxed_lines_sum − shopify_lines_expected| ≤ tol_lines`,
   where
   `shopify_lines_expected = Σ_line (discountedUnitPriceSet.shopMoney × quantity)
   − Σ order-level discountAllocations`, and
   **`tol_lines = r × 0.5 × L`**, `L` = count of Odoo SO lines contributing to
   the untaxed sum (product lines + shipping + tip + any explicit negative
   discount-adjustment line). Each such line's `price_subtotal` is Odoo-rounded
   to `r`, contributing at most `0.5r`. **There is no separate per-discount
   tolerance term** (the unsound `D_lines × 0.5r` term is withdrawn — a 2-dp
   `discount %` error scales with the line base and can exceed `0.5r`, so
   discounts are made **exact by construction** instead — §7).
2. **Taxes:** `|odoo_amount_tax − totalTaxSet.shopMoney| ≤ tol_tax`, where
   **`tol_tax = r × 0.5 × K`** and **`K` is the number of independent Odoo
   tax-rounding events, read from the company's actual
   `tax_calculation_rounding_method`:** `K = (number of distinct tax groups on
   the order)` when `round_globally` (the 19.0 default), or `K = (number of
   taxed line × tax-line pairs)` when `round_per_line`. Deriving `K` from the
   *configured* method (not a guess) keeps the bound tight and correct under
   both — this is the refinement forced by Odoo 19's `round_globally` default
   [Fact — official].
3. **Shipping + tip:** carried as SO lines (already counted in `L`); each is
   exact to one rounding step (`≤ 0.5r`, single lines, no accumulation).
4. **Total:** `|amount_total − totalPriceSet.shopMoney| ≤ tol_lines + tol_tax`
   — the bound is **exactly the sum of the legitimately-derived per-line and
   per-tax rounding tolerances**, with **no additional fixed or currency-relative
   cap** (both the original `1.00`-unit cap and the interim `10×r` cap are
   withdrawn — any cap either hides a material mismatch when loose or rejects a
   legitimate high-value order when tight). Because discounts are exact by
   construction (native-if-faithful else the exact negative line, §7), a
   high-value discounted order stays inside this bound, while a missing or wrong
   line shifts a subtotal by far more than `0.5r` and is rejected.

**Properties the guard satisfies (task §7):** the tolerance derives only from
legitimate currency rounding; it has **no arbitrary money cap**; it never grows
from unsupported discount assumptions (discounts are exact, not tolerated); it
detects missing/wrong lines at the component level; a total mismatch can never
complete silently; and it is mandatory and non-configurable (no per-store
tolerance setting exists).

### 6.2 Worked examples (illustration only — not acceptance)

All comparands are the **lossless Char** Shopify snapshots parsed as `Decimal`;
Odoo figures are read back from the built SO.

**Example A — ordinary 2-decimal (USD, `r = 0.01`), `taxesIncluded=false`.**
Line 1: 2 × 10.00 = 20.00 (8%); Line 2: 1 × 15.00 = 15.00 (8%); Shipping 5.00
(8%). Shopify: subtotal 35.00, tax 3.20, shipping 5.00, `totalPriceSet` 43.20.
Odoo: untaxed sum = 40.00; `amount_tax` = 3.20; `amount_total` = 43.20.
`L = 3`, `tol_lines = 0.01×0.5×3 = 0.015`; `|40.00−40.00| = 0 ≤ 0.015` ✓.
`round_globally` ⇒ `K = 1` (one 8% group), `tol_tax = 0.005`; `|3.20−3.20| = 0`
✓. Total bound `0.02`; `|43.20−43.20| = 0` ✓. **PASS.**

**Example B — JPY (`r = 1.0`, 0 decimals), `taxesIncluded=false`.**
Line: 3 × 1000 = 3000 (10%); Shipping 500 (10%). Shopify: subtotal 3000, tax
350, shipping 500, total 3850. Odoo: untaxed 3500, tax 350, total 3850.
`L = 2`, `tol_lines = 1.0×0.5×2 = 1.0` ✓; `K = 1`, `tol_tax = 0.5` ✓; total
bound `1.5`; `|3850−3850| = 0` ✓. **PASS** (rounding step is a whole yen).

**Example C — BHD (three-decimal, `r = 0.001`), `taxesIncluded=false`.**
Clean case: line 1 × 10.000 (5%) → tax 0.500, total 10.500. Odoo: untaxed
10.000, tax 0.500, total 10.500. `tol_lines = 0.001×0.5×1 = 0.0005`,
`tol_tax = 0.0005` ✓. **PASS.** *Risk case (why the empirical check exists):* a
line of 12.345 at 10% gives 1.2345, whose 3-decimal rounding is officially
undocumented on Shopify's side [Open question, captures §11]; if Shopify
reported `1.234` while Odoo computed `1.235`, `|0.001| > tol_tax (0.0005)` →
**correctly flagged** `financial_total_mismatch`, never silently absorbed. This
is why a **named dev-store empirical check precedes onboarding any three-decimal
store** — the guard's conservatism is the safety net, not the cure.

**Example D — high-value discounted taxable order (USD, `r = 0.01`).**
Line: 1 × 1000.00 (10% tax); order-level discount allocation 333.33 to this
line. Native `discount %` = 333.33/1000 = 33.333 % → quantized to 2-dp Discount
precision = 33.33 % → 333.30 (off by 0.03 > `0.5r`), so native is **not
faithful** → carry the residual as an **exact −333.33 tax-preserving adjustment
line inheriting the 10% `tax_ids` + inclusion** (§7). Odoo: untaxed = 1000.00 −
333.33 = 666.67; `amount_tax` = 10% of 666.67 = 66.67; total 733.34. Shopify:
discounted base 666.67, tax 66.67, total 733.34. `L = 2`,
`tol_lines = 0.01`; `|666.67−666.67| = 0` ✓; `K = 1`, `tol_tax = 0.005`;
`|66.67−66.67| = 0` ✓; total bound `0.015`; `0 ≤ 0.015` ✓. **PASS** — and the
withdrawn `D_lines × 0.5r` term is provably **not** relied on.

**Example E — mixed tax signatures (USD, `r = 0.01`).**
Line 1: 100.00 (10%); Line 2: 50.00 (untaxed); Line 3: 200.00 (20%);
order-level discount 30.00 spread ACROSS as 10 / 5 / 15. Residual buckets by
signature: −10.00 (10%), −5.00 (untaxed, no-tax residual), −15.00 (20%). Odoo:
untaxed sum = 90 + 45 + 185 = 320; `amount_tax` = 9.00 (10% of 90) + 37.00 (20%
of 185) = 46.00; total 366.00. Shopify: `shopify_lines_expected` = 350 − 30 =
320; `totalTaxSet` = 46.00; total 366.00. `L = 6` (3 product + 3 residual),
`tol_lines = 0.03`; ✓. `round_globally` ⇒ `K = 2` (10% and 20% groups),
`tol_tax = 0.01`; `|46.00−46.00| = 0` ✓; total bound `0.04`; ✓. **PASS.** A
**no-tax** residual on Lines 1/3 would leave taxable bases at 100/200 → tax
10+40 = 50 ≠ 46 → the **tax component fails**, proving the tax-preserving
residual is required (§7).

**Example F — deliberate missing line (USD, `r = 0.01`).**
Example A with Line 2 (15.00, tax 1.20) dropped by a mapping/logic error. Odoo
untaxed = 25.00; `shopify_lines_expected` = 35.00; `|25.00 − 35.00| = 10.00 ≫
tol_lines 0.015` → **LINE component fails**; and total `27.00` vs `43.20` →
`|16.20| ≫ 0.02` → **TOTAL fails**. Rolled back, `financial_total_mismatch`,
manual review. **Never silent.**

---

## 7. Discount representation (task §8)

**[Fact — official]** `discountedUnitPriceSet` already includes **line-level**
discounts but **excludes order-level and code-based** discounts, which surface
per line as `discountAllocations[].allocatedAmountSet`. `TaxLine.priceSet` is
the tax *"after discounts"*.

**[Proposed Task 012 decision]** Final discount rules:

- **Line-level discounts** are baked into `price_unit =
  discountedUnitPriceSet.shopMoney.amount` — never double-subtracted.
- **When a native Odoo line `discount %` is faithful:** an order-level
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
- **Line-level vs order-level:** line-level discounts → `price_unit`;
  order-level/code discounts → per-line `discount %` (if faithful) else the
  exact negative adjustment line, keyed off `discountAllocations`,
  `discountApplication.targetType = LINE_ITEM` (shipping-line discounts are
  already reflected in `shippingLines[].discountedPriceSet`).

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

**Mechanism [Proposed Task 012 decision]:** reaching `skipped` from inside a
handler requires **one named additive core seam** — a `JobPolicySkip(message,
technical_detail)` exception in `shopify_connector_job_dispatch.py` plus one
`except JobPolicySkip` branch in `_invoke_handler()` calling the existing
`job._transition_skipped(...)`. This is necessary because the merged dispatcher
**unconditionally** marks a normally-returning handler `succeeded` [Fact — repo
code], so no handler-reachable `skipped` path exists otherwise. It is one of
exactly **two** sanctioned core edits in the MVP tail (architecture §7; mirrors
Task 014's TD-002 edit), reused verbatim by Task 013's `tracked=false` skip.
The **same** `skipped`-policy routing applies to: `currentTotalDutiesSet`
non-null (duties — [Deferred / non-MVP]), `test: true` orders when
`order_import_include_test` is `False` (default), and orders already cancelled
at first import.

**Why not `blocked_manual_review` or a failure class:** none of the six fixed
`blocked_manual_review` sub-reasons fits a currency-model divergence, and no
error class describes "out of automatic-import scope" (the closest,
`odoo_validation_configuration`, wrongly implies an operator can *fix* it into
scope). `skipped` (policy) is the only routing that honours DEC-020 without
inventing a class or a sub-reason, or overloading `financial_total_mismatch`.

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
| `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py` | **THE ONE named additive core edit** — `JobPolicySkip` class + one `except` branch → `_transition_skipped` (§10); nothing else |
| `addons/shopify_connector_core/tests/test_job_dispatch.py` | append the `JobPolicySkip` routing test only |
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
| 15 | multiple tax rates | each rate mapped/matched; per-group `K`; guard passes |
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

Source-level guards (AST): single `execute()` call; zero mutation strings; zero
core/product file edits. Runtime: full three-suite Odoo.sh run green before
merge (SRR-06), concurrency caveat carried verbatim (architecture §5.12).
**Live-Shopify: none required** (read-only; VAL-B2 independent).

---

## 16. Locked-prompt status (task §17)

The authoritative locked implementation prompt lives in **packet §15**, updated
in this PR to be **file-exact, decision-complete, dependency-complete,
test-complete, and rollback-complete**. It states explicitly that it is
**unusable until a separate control-room gate** issues it, that **CORE-R2 (full
SRR-03), PR #150 (Task 011B), PR #151 (Task 010B), and Task LC-1 must be merged
first**, and that **no live Shopify request occurs during implementation tests**
(read-only + fixtures). This closure does **not** open the gate.

---

## 17. Adversarial self-critic (task §18)

Strict adversarial review of every named risk vector; each confirmed problem is
corrected in this closure (and the packet).

| # | Risk | Verdict | Resolution in this closure |
| --- | --- | --- | --- |
| 1 | money in lossy Float | **CONFIRMED → FIXED** | packet stored `shopify_order_total` as `Float`; corrected to **Char** (exact Decimal string) for all snapshots + Decimal math (§3.1) |
| 2 | double tax computation | NOT-A-PROBLEM | Shopify tax is evidence; Odoo recomputes from `tax_ids` only; the guard reconciles — no amount is applied twice (§5) |
| 3 | no-tax residual lowers taxable base | MITIGATED | taxable residuals inherit source `tax_ids`/inclusion; no universal no-tax line; inconsistent → rejected (§7, Example E) |
| 4 | arbitrary tolerance / fixed money cap | MITIGATED | tolerance derives only from `r` and rounding-event counts `L`/`K`; **no cap** (§6) |
| 5 | high-value discount error hidden by tolerance | MITIGATED | discounts made **exact** (native-if-faithful else exact adjustment line); not tolerated (§6/§7, Example D) |
| 6 | divergent currency enters Odoo | MITIGATED | blocked **before** SO creation → `skipped` (policy), independent of the guard (§10) |
| 7 | customer/address duplication | MITIGATED | binding/email anchor + normalized-tuple child dedup; parent never mutated (§8) |
| 8 | silent mutation of imported order | MITIGATED | evidence-refresh-only + source-level zero-SO-write guard test (§11, DEC-014 §J) |
| 9 | line-item / nested pagination omission | **CONFIRMED → FIXED** | full cursor pagination of all three order-level connections; the packet's "reject >100 lines" stance is replaced (§4.2) |
| 10 | raw PII/token/GraphQL-body log leak | MITIGATED | `REDACTION_EXTENSION` pre-redaction + no raw payload/token persistence (§13) |
| 11 | binding not sole idempotency anchor | MITIGATED | dual uniqueness + `operation_scope_key` + `idempotency_key`; store-targeted job keeps scope populated on first import (§3.3/§12) |
| 12 | accidental accounting/refund scope | NOT-A-PROBLEM | forbidden categories exhaustive; RA-010 unmet; evidence-only (§14) |
| 13 | dependence on unmerged code | **CONFIRMED (by design) → CONTAINED** | prerequisites (CORE-R2/SRR-03, PR #150/#151, LC-1) named; the locked prompt is gate-locked until they merge (§0/§16); the `ShopifyQuiescedError→skipped` wiring is CORE-R2's, not Task 012's |
| 14 | unsupported official-source claims | MITIGATED | every platform claim carries a URL + access status (§2); undocumented items logged as [Open question], not asserted |
| 15 | implementation-authorization language | NOT-A-PROBLEM | this closure and the packet header explicitly deny gate/code/live-call; the prompt is marked unusable-until-gate (§16/§19) |
| + | tax-rounding method mismatch (Odoo 19 `round_globally`) | **CONFIRMED → FIXED** | tolerance `K` derived from the company's actual `tax_calculation_rounding_method`; readiness warns on the setting (§6) |
| + | `read_all_orders` / 60-day scope creep | NOT-A-PROBLEM | `read_orders`-only; 60-day window documented; `read_all_orders` forbidden (§4.3/§14) |

**Rejected-approach guardrails re-checked (all revisit conditions UNMET, none
re-proposed):** RA-006 (name/fuzzy matching — email-only kept), RA-010
(accounting automation — evidence-only kept), RA-014/RA-015/RA-017 (blind
retry / never-retry / binding-alone — class-conditional retry + per-operation
`idempotency_key` kept), RA-005 (`ir.model.data` dedup — binding model kept),
RA-021 (assumed equivalence without documented semantics — the guard has an
explicit tolerance + documented rounding).

---

## 18. Remaining dependencies and open questions

**Hard merge-order dependencies (all currently unmet — §0):**
1. CORE-R2 full SRR-03 remediation merged runtime-green (the register forbids
   merging/enabling/live-validating any Shopify-calling domain handler until
   then; parallel *development* is allowed).
2. PR #150 (Task 011B) merged — the indexed `shopify_connector_email_normalized`
   lookup the guest path reuses.
3. PR #151 (Task 010B) merged — complete variant bindings so order lines resolve.
4. Task LC-1 merged (DEC-030 accepted) — so `_reassign_to_historic_job_type`
   exists for the new `job_type`'s `ondelete`.
5. Acceptance of this closure + the packet (D-012 decisions, PD-3/4/5/6) and the
   order-domain gate act, then the control-room issues the prompt.

**Open questions (logged, not resolved):**
- Verbatim GraphQL `THROTTLED` error-code string (docs show only `200 Throttled`).
- Shopify three-decimal-currency storage/rounding policy (undocumented) →
  named dev-store empirical check before onboarding such a store.
- Whether `res.partner.company_name` is the right sink for `MailingAddress.company`
  (confirm at build time; is_company stays False regardless).
- `ShopifyQuiescedError → skipped` dispatcher wiring ownership (a later CORE-R2
  slice, not Task 012).

---

## 19. Confirmation

This session produced **documentation only**. It wrote **no code**, created **no
Odoo module/model/view/manifest/test**, opened **no gate**, granted **no
implementation authorization**, and made **no live Shopify request** (all
platform facts came from official documentation/source reads, not from any
merchant store). Every proposed choice is **[Proposed Task 012 decision]**,
pending ChatGPT control-room review. The no-code gate (CLAUDE.md §4–§5) remains
in force.
