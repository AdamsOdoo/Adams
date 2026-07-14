# Task 012 — Order Import into Odoo Sales Orders (Proposed)

> Planning-only future implementation task spec, part of the MVP domain
> implementation-slicing sequence
> ([`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md),
> Area 3). Describes scope/boundary/approach only.
> **Decision-closure update 2026-07-14 (docs-only, no gate/code/live-call):**
> MBQ-27, MBQ-56, and the DEC-020 divergent-currency residual now have a
> **proposed** resolution in
> [`../03-architecture/task-012-order-import-decision-closure.md`](../03-architecture/task-012-order-import-decision-closure.md)
> and the implementation packet — **pending ChatGPT control-room acceptance**
> (not accepted here). **Prerequisites are CAPABILITY-BASED (corrected
> 2026-07-14, review `4690680028`), not direct PR merges:** SRR-03 CLOSED;
> protected/guarded product import + complete variant bindings; protected/
> guarded customer import + indexed normalized-email matching; no unguarded
> product/customer Shopify call remaining; LC-1 merged + DEC-030 accepted —
> **however those capabilities arrive** (direct merges of PR #150/#151 or a
> subsuming CORE-R2 Slice-2B integration PR). **CORE-R1 is already merged**
> (satisfied, not pending).

## Status

**Proposed only. Not authorized.** Depends on Task 010 (product
import/variant binding) and Task 011 (customer import/matching) domain
planning existing, plus foundation Tasks 002/003, per the cross-domain
sequencing fixed in Part B §D: product binding must be available before
order-line creation; customer binding/import must occur before order
finalization; the total-check guard is evaluated before the order is
marked complete. This document does not authorize, start, or imply
authorization of any of the above, and does not resolve MBQ-27, MBQ-55,
or MBQ-56.

## Objective

Import Shopify orders into Odoo `sale.order` records as an audited,
idempotent, evidence-capturing operation — never a duplicate create,
never a silent post-import mutation of an already-imported order, and
never an automatic import of a currency-divergent order — using the order
binding as the sole idempotency anchor.

## Preconditions

- Task 010 and Task 011 merged and reviewed (product and customer
  bindings must already resolve).
- Foundation Tasks 002/003 merged and gate-opened.
- The "sale domain gate" (also named by
  [`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md)
  Group 12 for the order-touchpoint UI extensions) explicitly opened.
- MBQ-55 (order binding model/field names) resolved via the naming/schema
  planning pass; MBQ-56 (total-check tolerance/comparison mechanism) and
  MBQ-27 (Odoo-side tax-representation mechanism) fixed or explicitly
  scoped by this task's own final §9 prompt — both are named in
  `master-blueprint-open-questions.md` as blocking the order-import task
  specifically.

## Order import boundary

`shopify_connector_sale` owns order import and financial-evidence capture
(Decision — DEC-008). Scope: Shopify Order → Odoo `sale.order`
create-or-update only. Trigger: webhook (`ORDERS_CREATE`/`ORDERS_UPDATED`),
scheduled sync, manual sync, reconciliation — never webhook-only (DEC-005
layered sync). Apps see orders from the last 60 days by default; all-orders
backfill/reconciliation requires the `read_all_orders` scope and Shopify
approval — a setup-readiness concern, not a design defect (Part B §C.2).

## Odoo Sales Order creation rules

The order binding (Shopify Order ↔ Odoo `sale.order`) is the sole
idempotency anchor for order creation — a repeated webhook or
reconciliation pass matches the existing binding and updates, never
re-creates (Part B §C.1, §C.3). Shopify order line items map to Odoo
`sale.order.line` records, each carrying at minimum a matched
product/variant reference (via the product binding), quantity, unit
price, and tax/discount evidence contribution — exact field mapping is
open (MBQ-02/55).

## Product/customer dependency handling

**Unmatched product on an order line — the whole-order-hold rule** (Part
B §C.5): the connector does not silently create a placeholder product and
does not silently drop the line (either would break the total-check
guard). Instead the whole order import is held, routed `failed_retryable`
with error class `mapping missing` (not `blocked_manual_review` — the
DEC-014 point I / Fable B1 routing correction), naming the specific
unmatched SKU/product; once bound, the job returns to `queued` and
resumes automatically. **Customer resolution follows the three-path
rule** (Part B §C.6): (1) genuinely no PII available → fallback partner
used, order imports normally, flagged; (2) PII available, confident match
or eligible auto-create (MBQ-59 gate) → proceeds as part of the
order-import job; (3) PII available but ambiguous → only the customer
assignment is held (`ambiguous match` → `blocked_manual_review`) — this
does **not** block the rest of order import, since a bad customer match
does not affect the total-check guard's math the way an unmatched product
line does.

## Shipping/discount/tax handling (planning level only)

Evidence capture only, never a tax-computation/reconciliation engine or
accounting automation (Decision — DEC-007 §6, restated Part B §C.7/§C.9):
`taxLines`/`currentTaxLines`/`totalTaxSet`, `shippingLines`/`shippingLine`,
and `discountApplications`/`cartDiscountAmountSet` are preserved as
evidence/lines/amounts only. This task does not design a tax engine. The
Odoo-side mechanism for holding a pre-computed tax figure without Odoo's
engine recomputing it is genuinely open (**MBQ-27**) — an official-doc
check against Odoo 19 accounting/taxes documentation found no documented
supported mechanism for externally-supplied tax amounts on `sale.order`;
the register states this "requires a dedicated ADR + ChatGPT decision"
and explicitly blocks the order-import slice, not the core gate.
**Proposed resolution 2026-07-14** (decision-closure §5 / packet D-012-9):
because Odoo 19 `sale.order`/`sale.order.line` have no supported external
tax-amount inverse (`price_tax` is compute-only; the `manual_tax_amounts`
override exists only in `account.move`/invoice flows — re-verified against
odoo/odoo 19.0), Shopify tax is represented by **mapping/matching an
`account.tax`** (canonical decimal-string rate key; `price_include_override`
per `taxesIncluded`; `order_tax_autocreate` default False), letting Odoo
recompute under the total-check guard — **proposed, pending control-room
acceptance**. A
gateway → Odoo `account.journal` classification mapping is a
partially-resolved, classification-only concept (MBQ-30) — it triggers no
automatic journal entry, posting, or reconciliation.

## Total-check guard

Mandatory and permanent — no flag/config may bypass it (Part A §I.5; Part
B §C.8). Before an order-import job completes: sum of imported line
totals + tax evidence + shipping evidence − discount evidence, compared
against Shopify's own reported order total. A mismatch beyond a
to-be-defined tolerance is classified `financial total mismatch` —
conservative, never silent, never auto-retried, requires explicit human
review. **Exact tolerance mechanism and Shopify total field — proposed
resolution 2026-07-14** in the decision-closure §6 / packet D-012-2:
`totalPriceSet.shopMoney.amount` is the total comparand; the tolerance is a
canonical single-count ledger (`U_ex = M + H + T`, each of product/shipping/
tip/discount counted once, tax-inclusive handled by `U_ex = G − totalTaxSet`)
with a currency-rounding-derived bound (`tol_lines = 0.5r·L` or `0.5r·(L+S)`
tax-incl; **proven `tol_tax = 0.5r·(S+O)`** from both systems' rounding events,
replacing the invalid `K=distinct groups`), with **no** money cap. This is
**proposed, pending control-room acceptance** (MBQ-56 stays open in the
register until then).

## Same-currency-only rule (DEC-020 / MBQ-64)

Accepted, decision-level
([DEC-020](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md),
revised after an initial ChatGPT REVISE): Phase 1 automatic order import
is same-currency only, defined as `Order.presentmentCurrencyCode ==
Order.currencyCode`. For divergent orders, the connector must not
silently create a normal Odoo sale order in shop currency **under any
circumstance** — the order is blocked from automatic sale-order creation,
independent of the total-check guard's numeric outcome (a reconciling
shop-currency total is explicitly not accepted as evidence the order is
safe to import, since Shopify's own cited research states back-converted
shop-currency values "might not sum perfectly to totals"). Both
`shopMoney` and `presentmentMoney` amounts, plus
`Order.presentmentCurrencyCode`, are captured as audit/reconciliation
evidence in every case, whether or not a sale order is created.
Presentment-currency-denominated Odoo orders remain non-MVP. **Exact
error-class/sub-reason mapping — proposed resolution 2026-07-14**
(decision-closure §10 / packet D-012-3): a divergent order routes to the
terminal `skipped` state as a **policy skip with NO error class**
(`skip_reason="divergent_presentment_currency"` in `technical_detail`),
reached via the one named additive `JobPolicySkip` core seam — so it never
overloads `financial_total_mismatch` and adds no 17th error class. Both
currencies and both `shopMoney`/`presentmentMoney` totals are captured. This
is **proposed, pending control-room acceptance**.

## Manual review/blocking cases

- Unmatched product line → `mapping missing` → `failed_retryable` (whole-order
  hold).
- Ambiguous customer match → `ambiguous match` → `blocked_manual_review`
  (customer assignment only, order still reconciles).
- Duplicate order risk → `duplicate risk` → `blocked_manual_review`.
- Financial total mismatch → its own conservative, always-manual,
  never-auto-retried posture.
- Divergent-currency order → blocked pre-SO-creation, exact class/sub-reason
  open (DEC-020 residual).
- Unsupported/malformed order payload shape → `data shape/schema mismatch`
  → `failed_retryable`.

## Idempotency and duplicate prevention

Order binding is the sole idempotency anchor (as above). GID permanence
is not asserted by Shopify for any object (MBQ-12, accepted-open risk,
non-blocking); stale/recreated-binding handling applies uniformly.
`ORDERS_UPDATED` (or an equivalent reconciliation-detected change) may
refresh Shopify-side evidence/audit data only — it must never silently
update the existing Odoo sale order's line quantities, prices, taxes,
shipping, discounts, invoices, payments, refunds, or fulfillment state,
under any trigger (DEC-014 point J, the Fable B2 correction). Any
divergence routes through the same total-check guard / `financial total
mismatch` / human-review posture — webhook and reconciliation paths
behave identically, neither auto-applies.

## Logs/audit

Every state transition writes a `shopify.connector.job.log` row
(append-only, `ondelete='restrict'`); order binding records carry their
own audit fields (matched-by, matched-at, source strategy, match key,
override history). No dedicated order-import screen exists or is
proposed (Decision — DEC-014 point C / MBQ-26, restated DEC-016) —
instead, the existing Error Center gains two accepted extensions: an
inline financial-evidence breakdown on `financial total mismatch`
entries, and a direct link from `mapping missing`/ambiguous-customer
entries into the matching flow.

## Tests required

Total-check guard math across multiple evidence components;
same-currency-only enforcement including the divergent-currency block
path; the three-path customer-resolution rule; whole-order-hold retry
loop (product binding arrives, job resumes); strict non-mutation of
already-imported order lines on `ORDERS_UPDATED`; duplicate-order-risk
detection; access-control matrix. Exact fixtures for this task's own
final §9 prompt. If no Odoo runtime exists at coding time, tests must
still be written and syntax-validated per the Task 001A precedent.

## Manual validation

On a live Odoo 19 + PostgreSQL instance once a runtime exists: simulate
an order with an unmatched product line and confirm the whole order holds
and later resumes; simulate an ambiguous customer and confirm only the
customer assignment holds while the rest proceeds; simulate a
divergent-currency order and confirm no sale order is created; simulate
an `ORDERS_UPDATED` line-quantity change and confirm the existing sale
order line is never silently mutated.

## Rollback

Single-PR revert; Task 013 (inventory) and Task 014 (fulfillment) are
downstream/sibling domains and, per the proposed MVP domain sequence, are
not authorized to start before this task, so no dependent domain logic is
affected by a revert. Reverting drops the order-binding model; any
already-created `sale.order` records remain as ordinary Odoo data, simply
un-bound.

## Acceptance criteria

- Only allowed files changed (per this task's own future final §9
  prompt).
- Order binding is the sole idempotency anchor; no duplicate sale order
  ever created for a repeated webhook/reconciliation pass.
- Total-check guard blocks on mismatch beyond the fixed tolerance, always
  manual, never silent, never auto-retried.
- No divergent-currency order automatically creates a sale order under
  any circumstance.
- `ORDERS_UPDATED` never silently mutates an already-imported order's
  lines/prices/taxes/shipping/discounts/invoices/payments/refunds/
  fulfillment state.
- Zero payout/refund/tax-engine/presentment-currency-order logic in the
  diff.

## Definition of done

Per `CLAUDE.md` §9 / `implementation-task-template.md` §7: code + tests
written (and passing where a runtime exists); `pr-review-checklist.md` §C
satisfied; MBQ-56/MBQ-27 either fixed in this task's own final §9 prompt
or explicitly scoped as a named, tracked residual; only allowed files
changed; handoff updated; ChatGPT reviews and accepts before any next
task starts.

## Explicit exclusions

- **No payouts.**
- **No advanced refunds.**
- **No presentment-currency Odoo orders** (divergent-currency orders are
  blocked from automatic import, not specially supported).
- **No complex tax engine** (evidence capture only).
- **No subscription/gift-card/POS/B2B scope.**
