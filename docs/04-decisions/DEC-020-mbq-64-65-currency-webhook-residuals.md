# DEC-020 — Proposed MBQ-64/MBQ-65 Currency and Product-Webhook Residuals

> **Proposed decision record** for the premium **Odoo 19 ↔ Shopify
> Connector**, prepared after ChatGPT accepted
> [`DEC-019`](./DEC-019-mbq-62-odoo-event-job-source.md) (MBQ-62,
> decision/semantic-classification level) on **2026-07-04**, and after PR #82
> (accepting DEC-019) merged into `Shopify-connector` at merge commit
> `94e3458e9ff6511f34f9abfe8944b4e0660c02b2`. `DEC-017` accepted **MBQ-64**
> and **MBQ-65** at **fact-verification level only** — not as full design
> decisions. `DEC-018` explicitly **excluded** MBQ-64 and MBQ-65 from MBQ
> Decision Batch 1, routing both to "a separate, dedicated currency/webhook
> residual decision sprint because they need tighter technical treatment than
> a posture-level batch review can safely give them." **This record is that
> dedicated sprint.** Companion documents:
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
> (MBQ-64/MBQ-65 rows),
> [`../03-architecture/master-blueprint-implementation-planning-bridge.md`](../03-architecture/master-blueprint-implementation-planning-bridge.md)
> (Part E §4/§5/§6, the routing that created MBQ-64/MBQ-65),
> [`../03-architecture/master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md)
> (§A.4, §A.14, §C.7–§C.9, the order-money/price sections this record
> complements without re-deciding),
> [`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md)
> and
> [`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md)
> (this session's residual research patch). Companion review-log entry:
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-017**, Proposed for ChatGPT review).

## Status

- **Proposed for ChatGPT review — NOT accepted.**
- **Documentation-only.**
- **Decision-preparation only.**
- **Does not authorize implementation.**
- **Does not open the implementation gate.**
- **Does not create implementation tasks.**
- **Implementation remains blocked.**
- **Built after DEC-019 acceptance** (2026-07-04), starting point PR #82
  merge commit `94e3458e9ff6511f34f9abfe8944b4e0660c02b2` into
  `Shopify-connector`.
- **This record does not modify DEC-003 through DEC-019, does not modify
  `../04-decisions/README.md`, and does not resolve MBQ-64 or MBQ-65** —
  it only proposes wording (§9) that a future, separate ChatGPT acceptance
  patch would apply, if and when ChatGPT accepts this record. **No other
  MBQ row is touched.** MBQ-62's own accepted state (DEC-019) is not
  reopened or weakened — the one MBQ-62-adjacent edit this record makes,
  if any, is limited to a tiny consistency note in the Part E bridge
  document's bridge table, per this sprint's own scope instruction (see
  §9/§10 and the Part E document itself).
- **Revised (2026-07-04) after ChatGPT's first review of this record
  returned REVISE for MBQ-64.** ChatGPT found the original MBQ-64 posture
  ("shop currency drives every Phase 1 order's `currency_id`; a
  presentment/shop divergence is caught only if the numeric total-check
  guard happens to fail") **not safe enough**: Shopify's own cited research
  already states shop-currency values are back-converted approximations
  whenever presentment differs, so a divergent order could pass the
  numeric guard while still misrepresenting the customer-facing order
  currency. §4/§5 below are corrected accordingly — **automatic Phase 1
  order import is now scoped to same-currency orders only**
  (`Order.presentmentCurrencyCode == Order.currencyCode`); a divergent
  order is never silently imported in shop currency under any outcome of
  the numeric total-check guard. **MBQ-65 (§6–§8) was found directionally
  acceptable by that same review and is unchanged in substance** — the
  enqueue-only, never-direct-write, follow-up-authoritative-read posture
  stands as originally proposed.

## 1. Purpose

`DEC-017` (2026-07-04) accepted the underlying **platform facts** for two
new open-questions-register rows — **MBQ-64** (Shopify's `MoneyBag`
shop/presentment order-money model vs. Odoo's single computed
`sale.order.currency_id`) and **MBQ-65** (Shopify product-domain webhook
topic strings `PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/`PRODUCTS_DELETE`) — but
explicitly left each row's own **design/selection question** (MBQ-64) and
**payload/subscription/Phase-1-scope residual** (MBQ-65) open, not decided.
`DEC-018` (MBQ Decision Batch 1) then explicitly **declined** to fold either
row into its posture-level ChatGPT batch, stating both "require a separate,
dedicated currency/webhook residual decision sprint... because they need
tighter technical treatment than a posture-level batch review can safely
give them" (`DEC-018` §6). `DEC-019` resolved the one other row DEC-018 had
split out (MBQ-62) and left MBQ-64/MBQ-65 "untouched."

This record is that dedicated sprint. Its purpose is narrow and specific:
propose **one** design/selection decision for MBQ-64 (which Shopify money
field drives the Odoo order currency, and how a shop/presentment divergence
is handled) and **one** design/selection decision for MBQ-65 (whether, and
how, product-domain webhooks are implemented in Phase 1) — each grounded in
fresh official-doc verification where the existing research corpus left a
question explicitly open, not asserted either way. It does not re-decide
anything DEC-003 through DEC-019 already fixed, does not touch MBQ-56 (the
sibling total-check-guard tolerance/field-selection question, still its own
residual), and does not open the implementation gate under any outcome.

## 2. Sources reviewed

### Existing repository sources

- [`master-blueprint-implementation-planning-bridge.md`](../03-architecture/master-blueprint-implementation-planning-bridge.md)
  — §3 (gate checklist), §4 (MBQ decision plan row for MBQ-56/64/65), §5/§6
  (the original MBQ-64/MBQ-65 fact-verification research and routing), §12
  (open risks).
- [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  — MBQ-56, MBQ-64, MBQ-65 rows in full, plus the DEC-017/018/019
  acceptance-patch notes.
- [`master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md)
  — §A.4 (product update flow), §A.14 (price/compare-at handling, DEC-007
  §3's Markets-pricing exclusion restated), §C.7 (financial-evidence
  capture), §C.8 (total-check guard / `financial total mismatch` class),
  §C.9 (tax/shipping/discount/payment evidence handling).
- [`DEC-007-phase1-scope-clarifications.md`](./DEC-007-phase1-scope-clarifications.md)
  §3 — explicit Phase 1 exclusion of "advanced pricelist mapping, Shopify
  Markets pricing, customer-specific pricing, B2B price lists, and any
  currency-/market-specific pricing strategy."
- [`DEC-017-master-blueprint-implementation-planning-bridge.md`](./DEC-017-master-blueprint-implementation-planning-bridge.md)
  — the fact-verification-level acceptance this record builds on.
- [`DEC-018-mbq-decision-batch-1.md`](./DEC-018-mbq-decision-batch-1.md) §6
  — the exclusion of MBQ-64/MBQ-65 from Batch 1 and the reason given.
- [`architecture-review-log.md`](../05-qa/architecture-review-log.md) —
  AR-014 (Part E), AR-015 (Batch 1), AR-016 (MBQ-62), all Accepted; read in
  full for the exact wording this record must not contradict.
- [`rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md) —
  read in full (RA-001 through RA-023). No row directly addresses
  order-currency selection or product-webhook write posture, but **RA-008**
  (blind first Odoo→Shopify inventory push, no preview/confirmation) and
  **RA-020** (autonomous bidirectional inventory conflict resolution)
  establish the project's standing rejection of the same root failure mode
  — writing without a confirming read/guard — that this record's rejected
  MBQ-65 Option D would repeat in the product domain. No existing rejected
  approach is reintroduced by any option adopted below.
- [`shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md)
  and
  [`odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md)
  — "Part E pre-implementation research patch" sections (2026-07-04),
  read in full as the baseline this session's residual research extends.

### Official Shopify sources (fetched this session, access date **2026-07-04**)

| Source | URL | Fact supported |
| --- | --- | --- |
| "About Shopify Markets" | https://shopify.dev/docs/apps/build/markets | Presentment currency is described as the checkout/refund/order-edit **"source of truth"**; shop currency is the merchant's analytics reference, **back-converted from presentment via the live exchange rate** when an order's presentment currency differs, and such back-converted values **"might not sum perfectly to totals"**; settlement currency (payout) may differ from both and is "most appropriate for accounting purposes." |
| `Order` object (GraphQL Admin API) | https://shopify.dev/docs/api/admin-graphql/latest/objects/Order | Re-verified `currencyCode` field description (unchanged). Re-verified `presentmentCurrencyCode` and found its description now includes an additional sentence beyond what was cited in the Part E patch: **"This may differ from the shop's base currency when serving international customers or using multi-currency pricing."** Confirmed verbatim against the page's raw source, not only a summarized fetch. |
| "About webhooks" | https://shopify.dev/docs/apps/build/webhooks | Verbatim, confirmed against raw page source: **"Shopify doesn't guarantee ordering within a topic, or across different topics for the same resource"** (e.g. `products/update` can arrive before `products/create`); **"Your app shouldn't rely on receiving data from Shopify webhooks. Webhook delivery isn't always guaranteed... For redundancy, use reconciliation jobs to periodically fetch data from Shopify"**; **"Verify HMAC signatures and ignore duplicate deliveries using `X-Shopify-Webhook-Id`"**; use `X-Shopify-Triggered-At` header or payload `updated_at` to order/organize webhooks; payload is the **full resource by default**, restrictable via a `fields`/`include_fields` parameter. |
| "Manage webhook subscriptions" | https://shopify.dev/docs/apps/build/webhooks/subscribe | Two subscription mechanisms exist: **app-config** (`shopify.app.toml`, "applied uniformly across every shop that installs your app," recommended default) and **shop-specific GraphQL** (`webhookSubscriptionCreate` mutation, "configuration can differ per shop"); "each topic you subscribe to requires a corresponding access scope." |
| `WebhookSubscriptionTopic` enum | https://shopify.dev/docs/api/admin-graphql/latest/enums/WebhookSubscriptionTopic | Re-confirmed, unchanged: `PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/`PRODUCTS_DELETE`, each requiring `read_products`. |

**Inconclusive / not confirmed this session:** a per-product **variant-count
payload-truncation** behavior (a claim, sourced only from third-party
developer aggregator guides surfaced by web search, that very-high-variant
products' webhook payloads omit full detail beyond a threshold, naming a
`variant_ids`/`truncated_fields`-style residual pointer) could **not** be
confirmed against any primary `shopify.dev` page directly fetched this
session — two candidate pages
(`https://shopify.dev/docs/apps/build/webhooks` and
`https://shopify.dev/docs/apps/build/webhooks/customize/modify-payloads`)
were fetched and neither page's retrieved content contained this claim.
Per `CLAUDE.md` §7 rule 5, this is logged as an **open, unverified
question**, not asserted as fact, and does not drive any option below.

### Official Odoo sources (fetched this session, access date **2026-07-04**)

| Source | URL | Fact supported |
| --- | --- | --- |
| `addons/sale/models/sale_order.py` (official `odoo/odoo`, branch `19.0`) | https://raw.githubusercontent.com/odoo/odoo/19.0/addons/sale/models/sale_order.py | Re-confirmed `currency_id` derivation (pricelist currency, else company currency) **and** newly confirmed it is declared `compute='_compute_currency_id', store=True, precompute=True` with **no `readonly=False`** — unlike `pricelist_id` (which is explicitly `readonly=False`) — meaning `currency_id` is not directly settable; it can only be influenced by setting `pricelist_id` (to a pricelist carrying the desired currency) or `company_id`. Newly confirmed `currency_rate` — a computed `Float` field (`compute='_compute_currency_rate'`, `store=True`, `precompute=True`) derived via `res.currency._get_conversion_rate(from_currency=order.company_id.currency_id, to_currency=order.currency_id, company=order.company_id, date=order.date_order)` — i.e. Odoo natively computes a company↔order exchange rate whenever an order's currency differs from its company's. Newly confirmed `amount_untaxed`/`amount_tax`/`amount_total` are computed by `_compute_amounts`, which calls `AccountTax._get_tax_totals_summary(..., currency=order.currency_id or order.company_id.currency_id, ...)` and reads `base_amount_currency`/`tax_amount_currency`/`total_amount_currency` — confirming every order-level total is computed in exactly the order's **one** `currency_id`, never split across two currencies. |

No official Odoo source was inaccessible or inconclusive this session.

## 3. MBQ-64 current accepted facts and unresolved question

**Accepted by DEC-017, at fact-verification level only:**

- Every Shopify order money/total field (`totalPriceSet`,
  `currentTotalPriceSet`, `totalOutstandingSet`, `totalDiscountsSet`,
  `totalTaxSet`, and the rest) is `MoneyBag`-typed, carrying **both**
  `shopMoney` ("Amount in shop currency") and `presentmentMoney` ("Amount in
  presentment currency") simultaneously, non-null.
- Odoo's `sale.order` carries exactly **one** computed `currency_id`
  (pricelist currency, else company currency).
- Odoo's `res.currency.round()`/`compare_amounts()` are verified,
  currency-aware rounding/tolerance-comparison primitives (a candidate
  mechanism for MBQ-56, not itself decided here).

**Not decided by DEC-017 — the question this record answers:** which
Shopify money field (`shopMoney` vs. `presentmentMoney`) drives Odoo's
single order `currency_id`, what must be captured for audit even if not
used as the order currency, and how a shop/presentment divergence is
itself classified/guarded — a **design/selection** question, not further
fact-finding, now that both platforms' single/dual-currency shapes are
verified (per DEC-017's own framing).

**This session's new facts sharpen, rather than change, that framing:**
Shopify's own official guidance now states presentment currency is the
checkout/refund/order-edit **source of truth**, while shop currency is a
**back-converted, potentially imprecise** analytics reference ("might not
sum perfectly to totals") whenever the two diverge; and Odoo's `currency_id`
is **not directly settable** — using presentment currency as the Odoo order
currency would require provisioning a currency-matched `pricelist_id` per
divergent currency, not merely writing a field. Both facts are decision
inputs for §5, not restatements of DEC-017.

## 4. MBQ-64 options considered

| Option | Description | Pros | Cons | Financial correctness impact | Odoo fit | MVP impact | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **A** | Use Shopify **shop currency** (`Order.currencyCode`) as Odoo `sale.order.currency_id` — **scoped to same-currency orders only**, i.e. only where `Order.presentmentCurrencyCode == Order.currencyCode`. Never used to automatically import a divergent-currency order in shop currency. | Single company-anchored currency matches Odoo's default posture with zero new pricelist/currency provisioning; aligns with DEC-007 §3's existing Markets/currency-specific-pricing exclusion; for the supported (same-currency) case, shop currency and presentment currency are, by definition, the same value, so there is no back-conversion imprecision to hide behind a numeric guard. | Only covers the same-currency subset — does **not** itself say what happens to a divergent order (that is Option C/D's job, below); must not be silently extended to cover divergent orders just because it is the simplest mechanism. | Good — restricting Option A to exactly the case where the two currencies are identical removes the FX-back-conversion risk the original (unrevised) proposal carried. | Very good — no new Odoo master data (pricelists/currencies) required for the supported subset. | Best — simplest, no per-currency setup, for the orders it actually covers. | **Adopt, but only for same-currency orders.** Does not apply to, and must not be stretched to cover, divergent orders — see Option C/D, now the **active** posture for that case. |
| **B** | Use Shopify **presentment currency** (`Order.presentmentCurrencyCode`) as Odoo `sale.order.currency_id` whenever it differs from shop currency. | Matches Shopify's own stated "source of truth" framing for what the customer actually agreed to pay; Odoo natively supports a non-company-currency sale order via `pricelist_id.currency_id`, with `currency_rate` auto-computed for company-currency accounting conversion — the mechanism exists in Odoo core, this is not a hypothetical capability. | `currency_id` is **compute-only, not directly settable** — this option requires provisioning (and maintaining) a currency-matched `pricelist_id` for every presentment currency a store's customers might use, before a single order in that currency could be imported; directly reopens the scope DEC-007 §3 already excluded ("any currency-/market-specific pricing strategy," "Shopify Markets pricing"); every downstream reporting/reconciliation view would need to handle N order currencies inside an MVP. | Best per-order fidelity to what was actually charged, but only if the pricelist-provisioning problem is solved first — undesigned today. | Technically supported by Odoo's ORM, but requires new master-data provisioning this sprint does not design. | Poor — reopens an already-closed MVP scope exclusion. | **Reject for Phase 1**; revisit only if ChatGPT explicitly reopens Markets/multi-currency-pricing scope (DEC-007 §3). Rejected regardless of whether the order would otherwise pass a numeric total-check. |
| **C** | Block automatic sale-order creation / route to manual review / treat as explicit unsupported-scope for **any** order where `Order.presentmentCurrencyCode != Order.currencyCode`, checked **before** SO creation and **independently of** whether the numeric total-check guard would otherwise pass. | Zero silent-mismatch risk — the currency-model divergence itself is the trigger, not a downstream numeric symptom that might happen not to fire; a divergent order can never slip through simply because its back-converted shop-currency total happened to reconcile within tolerance. | Blocks some orders whose shop-currency evidence might, in isolation, look numerically reconcilable — an accepted trade-off given Shopify's own guidance that presentment is the source of truth and a divergent order's shop-currency values are back-converted approximations, not independently verified facts, so "the numbers happen to match" is not a sufficient safety argument on its own. | Maximally safe — this is now the **primary**, not merely a companion, mechanism for the divergent-order case. | Good fit conceptually; **exact** error-class/sub-reason mapping (whether this reuses `financial total mismatch`, `blocked_manual_review`, or another existing Part A §D.8 shape) is evaluated in §5 and left as an explicit residual rather than forced. | Good — this is the enforcement mechanism for Option D's scope boundary, not an optional guard on top of Option A. | **Adopt as the active, primary posture for any divergent-currency order** — runs before SO creation, independent of the total-check guard's outcome. |
| **D** | Defer multi-currency/Shopify Markets orders from Phase 1 entirely; automatic import supports same-currency orders only. | Cleanest match to DEC-007 §3's existing Markets exclusion; simplest to state as a scope boundary. | As a documentation-only exclusion with no runtime guard, it would not actually prevent a divergent order from being silently imported — Shopify's own docs confirm presentment can differ from shop currency "when serving international customers or using multi-currency pricing," which can occur even without a merchant consciously enabling "Shopify Markets" as a named feature; **this option is only real when paired with Option C's runtime mechanism**, not as a standalone documentation-only statement. | N/A on its own — needs Option C's mechanism to be enforceable, not merely asserted. | N/A on its own. | Matches the already-accepted MVP boundary (DEC-007 §3). | **Adopt as the explicit scope statement**, jointly with Option C as the enforcement mechanism — same-currency orders are the only Phase 1 automatic-import scope; divergent orders are explicitly out of that scope, enforced by Option C, not merely declared. |

## 5. Proposed MBQ-64 decision

**Proposed decision: Option A, scoped to same-currency orders only + Option
D (explicit non-MVP scope boundary) + Option C (the active, primary
enforcement mechanism for any divergent-currency order, running before SO
creation and independent of the total-check guard's outcome). Option B
remains rejected for Phase 1.**

**Phase 1 automatic order import is same-currency only.** For orders where
`Order.presentmentCurrencyCode == Order.currencyCode`, the connector
proceeds as normal. For orders where `Order.presentmentCurrencyCode !=
Order.currencyCode`, the connector **must not** silently create/import a
normal Odoo sales order in shop currency — that case is out of Phase 1's
automatic-import scope and is handled per the blocking rule below,
regardless of what a numeric total-check would show.

- **Which currency drives `sale.order.currency_id` for supported
  same-currency orders:** Shopify's **shop currency** (`Order.currencyCode`)
  — which, for these orders, is by definition identical to the presentment
  currency. No new Odoo pricelist/currency provisioning is required; the
  order's currency continues to derive from the connector's existing
  pricelist/company-currency assignment exactly as Odoo's
  `_compute_currency_id` already works.
- **Divergent orders are not silently imported in shop currency:** when
  `Order.presentmentCurrencyCode != Order.currencyCode`, the connector does
  **not** proceed to create a normal Odoo sale order in shop currency under
  any circumstance — not even if the shop-currency total would otherwise
  reconcile against the Odoo total within MBQ-56's tolerance. The
  divergence itself (a currency-model mismatch between what Shopify
  recorded the order in and what Odoo would record it in) is the blocking
  condition — **it is not inferred from, or contingent on, a numeric
  total-check failure.** A back-converted shop-currency total that happens
  to reconcile is not evidence the order is safe to import automatically;
  per §2's cited official fact, such values are themselves approximations
  ("might not sum perfectly to totals") whenever the two currencies
  diverge, so "the numbers matched" is not a substitute for checking the
  currencies matched.
- **How a divergent order is handled before SO creation:** the job is
  **blocked from automatic sale-order creation** and routed to manual
  review / treated as an explicit unsupported-scope case — the connector
  does not silently drop the order, but it also does not silently create a
  normal Odoo sale order for it. The **exact** enforcement shape (a
  dedicated manual-review queue entry the operator can act on vs. a harder
  unsupported-scope block that requires a future, separately-designed
  path) is not fixed by this record — see "what remains implementation
  planning" below.
- **Existing error-class fit, evaluated explicitly (not forced):** the
  already-accepted **`financial total mismatch`** class (Part A §D.5.5,
  DEC-009) is a plausible but **not automatically correct** home for this
  case. In its favor: it is already conservative, "never silent, never
  auto-retried," and requires explicit human review — the right posture
  for this case. Against forcing it: `financial total mismatch`, as
  defined in §C.8, is triggered by a **numeric** comparison ("the connector
  computes the sum of imported line totals... and compares it against the
  Shopify order's own reported total") — a currency-model divergence
  blocked **before** SO creation is a different kind of failure, detected
  before any Odoo total exists to compare, not a discovered numeric
  discrepancy. Reusing the class as-is, without an explicit, named
  broadening of its trigger condition (in the same spirit as DEC-015 point
  J's accepted, explicit widening of `ambiguous match` to a new case,
  rather than a silent stretch), would risk exactly the loose-routing
  pattern DEC-014's Fable review (finding B1) already flagged and corrected
  once in this project. **This record does not force that broadening
  here.** Instead: **the accepted decision posture is that no automatic
  sale order is created for a divergent-currency order, under any
  circumstance** — the **exact final error-class/sub-reason mapping**
  (whether that is a defensible, explicitly-named broadening of
  `financial total mismatch`, a mapping onto an existing
  `blocked_manual_review` sub-reason, or another Part A §D.8 shape)
  **remains implementation planning**, to be decided with the same
  strictness DEC-018/DEC-019 applied to MBQ-62 rather than assumed here.
- **MBQ-56 is not the (sole) line of defense against divergence:** MBQ-56's
  total-check tolerance/comparison mechanism keeps its existing scope — the
  **numeric** guard for same-currency orders (and any other total-check
  use already accepted) — and **remains open**, unchanged and undecided by
  this record. It is explicitly **not** relied upon to catch a
  shop/presentment divergence; that is caught by the dedicated,
  independent currency-equality check above, which runs regardless of
  what MBQ-56's eventual tolerance value would compute.
- **What must be persisted conceptually for audit/reconciliation, in every
  case (same-currency or divergent):** the order's `presentmentCurrencyCode`,
  and — for at least the order-level total fields the total-check guard and
  financial-evidence capture already cover (§C.7–§C.9: `totalPriceSet`,
  `totalTaxSet`, `totalDiscountsSet`, `totalShippingPriceSet`, and the
  rest) — **both** the `shopMoney` and `presentmentMoney` amounts from each
  field's `MoneyBag`, not only `shopMoney`. This travels with the
  job/error/audit payload alongside the other financial-evidence fields
  already accepted in §C.7, so a divergent order's full evidence is always
  captured and reconstructable for the manual reviewer or a future
  reconciliation pass, even though no sale order is automatically created
  for it.
- **What is non-MVP:** Odoo sale orders denominated in a Shopify
  presentment currency (Option B), and any automatic-import path for a
  divergent-currency order generally, **unless and until** a later,
  explicit scope expansion designs the currency/pricelist provisioning
  Option B would require; per-market/per-currency Odoo pricelist
  provisioning; any Shopify-Markets-specific pricing (already excluded by
  DEC-007 §3); any automatic FX gain/loss reconciliation beyond Odoo's own
  native accounting mechanism (`currency_rate`, already part of core Odoo,
  not a connector-built feature).
- **What remains implementation planning:** the exact final
  error-class/sub-reason mapping for a blocked divergent-currency order
  (see above — not decided here); whether the divergent-order path lands
  in the existing manual-review queue or a distinct unsupported-scope
  classification; MBQ-56's exact tolerance value and exact Shopify total
  field(s) compared for same-currency orders (unchanged, not decided
  here); exact Odoo model/field names for persisting
  `presentmentCurrencyCode` and the `presentmentMoney` amounts (MBQ-01/02,
  the naming pass, unaffected by this record).
- **How this avoids silent financial mismatch:** no automatic sale order is
  ever created for an order whose presentment currency differs from its
  shop currency, regardless of whether a numeric total-check would have
  passed — so a back-converted, approximate shop-currency total can never
  be silently treated as sufficient evidence that a divergent order is
  safe to import. Both money representations are always captured as
  evidence, so an operator (or a future reconciliation pass) can always
  see what the customer actually paid, and the exact blocking mechanism
  being left as an implementation-planning residual does not weaken the
  posture itself: **no silent SO creation for divergent currencies**, fixed
  now, independent of how that posture is eventually wired into Part A's
  job/error taxonomy.

## 6. MBQ-65 current accepted facts and unresolved question

**Accepted by DEC-017, at fact-verification level only:** `PRODUCTS_CREATE`,
`PRODUCTS_UPDATE`, `PRODUCTS_DELETE` are confirmed against the official
`WebhookSubscriptionTopic` enum, each requiring the `read_products` scope —
the direct product-domain analog of MBQ-37's inventory-topic resolution.

**Not decided by DEC-017 — the residual this record answers:** the exact
payload shape, required subscription mechanics/scopes beyond
`read_products`, and whether webhook-driven product import is implemented
in Phase 1 at all (vs. scheduled/manual/reconciliation-only, mirroring the
already-accepted layered-sync posture), mirroring MBQ-63's inventory-webhook
residual treatment.

**This session's new facts:** two subscription mechanisms exist
(app-config `shopify.app.toml`, recommended default; or shop-specific
GraphQL `webhookSubscriptionCreate`); payload is the **full resource by
default**, restrictable via a `fields`/`include_fields` parameter; delivery
is **not guaranteed** and **ordering across topics is not guaranteed**
("it's possible that a `products/update` webhook might be delivered before
a `products/create` webhook"); Shopify's own guidance is explicit —
**"Your app shouldn't rely on receiving data from Shopify webhooks... For
redundancy, use reconciliation jobs"**; deduplication is via
`X-Shopify-Webhook-Id`; staleness/ordering is managed via
`X-Shopify-Triggered-At`/`updated_at`. A claimed variant-count payload
truncation behavior could **not** be confirmed against a primary
`shopify.dev` page this session (§2) and is not asserted as fact.

## 7. MBQ-65 options considered

| Option | Description | Pros | Cons | Data-safety impact | API/scope impact | MVP impact | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **A** | Implement `PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/`PRODUCTS_DELETE` in Phase 1 as **enqueue-only triggers**: the webhook never writes directly; it enqueues a job that performs a follow-up authoritative read (GraphQL) before any create/update/delete is applied to Odoo. | Fast propagation without ever trusting a possibly stale/out-of-order/truncated payload; matches the already-accepted DEC-005 sync-orchestration pattern (webhook triggers a job; the job does the authoritative work) and mirrors the already-accepted MBQ-37 inventory-webhook posture. | Requires a product-domain webhook controller (HMAC verification, `X-Shopify-Webhook-Id` dedup) not yet scoped in Part B beyond order/inventory mentions — additional, but reused, surface. | Safe — no direct writes; the follow-up read naturally absorbs the out-of-order-delivery and payload-completeness gaps Shopify's own docs warn about. | `read_products` already verified sufficient; subscription-mechanism choice (app-config vs. GraphQL) is implementation planning. | Moderate — reuses the existing job/log/error substrate (Part A §D); no new architecture pattern. | **Adopt as the Phase 1 posture.** |
| **B** | Subscribe to product webhooks but treat them **only** as drift/reconciliation signals — never enqueue an immediate import/update job, only prioritize the next reconciliation pass. | Even more conservative than A; avoids designing an immediate enqueue-then-fetch job path this sprint. | Shopify's own guidance frames reconciliation as the **backstop** to webhooks, not a replacement for their responsiveness; discards the propagation benefit webhooks exist to provide without a domain-specific reason found this session; inconsistent with the sibling order-webhook posture already accepted (DEC-014 §C.12, "evidence-refresh only," still a prompt refresh, not a delayed reconciliation-only cadence). | Safest in isolation, but arguably over-cautious relative to already-accepted sibling-domain postures. | Same scope needs as A. | Marginally simpler (no enqueue-then-fetch logic needed this phase), but a real posture inconsistency against order/inventory. | **Not adopted** — A already achieves the same safety (no direct writes) without discarding responsiveness; no evidence this session justifies treating product differently from order/inventory, unlike MBQ-63's inventory-specific signal-only treatment (which itself was not this conservative). |
| **C** | Do **not** implement product webhooks in Phase 1; rely on manual sync, scheduled sync, and reconciliation only. | Simplest — zero new webhook-controller surface for the product domain in Phase 1. | Loses near-real-time propagation entirely; no evidence in this corpus shows product data is less volatile than order data (webhook-driven evidence refresh already accepted, DEC-014 §C.12) or inventory (webhook-driven triggers already accepted, DEC-010/DEC-015) — singling out product for a webhook-free Phase 1 would be an unexplained domain-by-domain inconsistency. | Safe, but not meaningfully safer than A (A already never writes directly from a webhook payload either). | None needed. | Simplest to build, but a real feature-parity gap against sibling domains' accepted postures. | **Not adopted** — reserved only as a fallback if a future implementation-planning task finds a concrete blocking reason A does not anticipate. |
| **D** | Implement **direct** product mutation from webhook payloads — write immediately on receipt, no follow-up read. | Lowest possible latency. | Directly contradicts Shopify's own explicit guidance (delivery not guaranteed; ordering not guaranteed — "a `products/update` webhook might be delivered before a `products/create` webhook"); risks acting on stale, out-of-order, or incomplete data; repeats the same root failure mode this project has already rejected for a different domain (**RA-008** blind inventory push; **RA-020** autonomous bidirectional conflict resolution) — writing without a confirming read/guard. | High — silent destructive/incorrect product writes (e.g. processing a delayed delete after a legitimate recreate) are exactly the class of silent risk this project's correctness posture forbids. | Same scope needs as A, with none of A's safety benefit. | N/A — rejected regardless of MVP pressure. | **Reject.** Do not adopt under any Phase 1 configuration. |

## 8. Proposed MBQ-65 decision

**Proposed decision: Option A.**

- **Whether product create/update/delete webhooks are implemented in Phase
  1:** Yes — `PRODUCTS_CREATE`, `PRODUCTS_UPDATE`, and `PRODUCTS_DELETE` are
  implemented in Phase 1.
- **If implemented, what they are allowed to do:** **enqueue only.** A
  received webhook never writes directly to Odoo. It enqueues a job (Part A
  §D job/log/error substrate) that performs a **follow-up authoritative
  read** (GraphQL) of the current product state before any create, update,
  or delete is applied — reusing the existing binding/dedup mechanism
  (DEC-006) to resolve the affected Odoo record, exactly as the accepted
  order/inventory postures already do. This never trusts the webhook
  payload's content as sufficient on its own to write, sidestepping both
  the confirmed out-of-order-delivery risk and the unconfirmed
  payload-truncation question (§2) without needing to resolve that
  question first.
- **If deferred (not applicable — Option A is implemented), what remains
  the Phase 1 source:** N/A under this decision; manual sync, scheduled
  sync, and the DEC-005 layered-sync reconciliation pass remain the
  **backstop**, exactly as Shopify's own guidance recommends regardless of
  webhook health ("For redundancy, use reconciliation jobs to periodically
  fetch data from Shopify").
- **How this avoids silent destructive product updates:** a
  `PRODUCTS_DELETE` webhook never directly deletes or archives the bound
  Odoo product on receipt — it enqueues a job that re-verifies the
  product's current Shopify-side state via an authoritative read before
  applying any destructive action; any ambiguous or unconfirmable case
  routes to manual review, reusing the existing manual-review/error-class
  vocabulary (Part A §D.5/§D.8) rather than inventing a new one, and never
  defaults to a silent delete.
- **What payload/subscription/scope facts are verified, and what remains
  open:** verified this session — subscription mechanism choice
  (app-config `shopify.app.toml` vs. GraphQL `webhookSubscriptionCreate`),
  full-payload-by-default behavior with optional `fields`/`include_fields`
  restriction, `read_products` scope sufficiency (already from DEC-017),
  HMAC + `X-Shopify-Webhook-Id` duplicate-delivery handling, and
  `X-Shopify-Triggered-At`/`updated_at` staleness/ordering guidance.
  Remaining open: whether a variant-count payload-truncation behavior is
  real (inconclusive this session, §2) and, if so, how the follow-up read
  should account for it; the exact follow-up-read query shape; whether the
  product webhook controller is shared with order/inventory controllers or
  domain-specific (Part A extension-rules question, not decided here).
- **How this interacts with manual/scheduled/reconciliation product sync:**
  unchanged and additive — this decision does not alter or narrow the
  already-accepted manual/scheduled/reconciliation product-sync posture
  (DEC-003/DEC-005/DEC-014); webhooks add a faster propagation path on top
  of it, never a replacement for it.
- **What is non-MVP:** the `PRODUCT_LISTINGS_*`/`PRODUCT_PUBLICATIONS_*`/
  `SCHEDULED_PRODUCT_LISTINGS_*` topics (already logged, not required for
  Phase 1, per the DEC-017 research patch); Shopify's "Events" next-generation
  subscription mechanism (developer preview, a subset of topics only); direct
  webhook-driven mutation (Option D, rejected outright).

## 9. Register impact if accepted

**Draft only — not applied by this record.** If and only if ChatGPT accepts
this proposal, a future acceptance-patch session would apply the following
wording to `master-blueprint-open-questions.md`'s MBQ-64 and MBQ-65 rows
(and only those two rows):

**MBQ-64 (draft register wording):** "Proposed resolved by
[`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md)
(pending ChatGPT acceptance): Phase 1 **automatic order import is
same-currency only** — for orders where `Order.presentmentCurrencyCode ==
Order.currencyCode`, Odoo `sale.order.currency_id` is driven by the
connector's normal configured Odoo pricelist/company currency, aligned to
Shopify's shop currency (`Order.currencyCode`). For orders where
`Order.presentmentCurrencyCode != Order.currencyCode`, the connector does
**not** silently create/import a normal Odoo sales order in shop currency
under any circumstance, including when a numeric total-check would
otherwise reconcile — the job is blocked from automatic sale-order
creation and routed to manual review / treated as an explicit
unsupported-scope case before SO creation. Both `shopMoney` and
`presentmentMoney` amounts, plus `Order.presentmentCurrencyCode`, are
captured as audit/reconciliation evidence in every case, whether or not a
sale order is created. Presentment-currency-denominated Odoo orders
(Option B) remain non-MVP unless and until a later, explicit scope
expansion designs currency/pricelist provisioning. MBQ-56's total-check
tolerance/comparison mechanics remain its own open residual, unchanged and
not relied upon as the (sole) mechanism for catching a currency-model
divergence. The exact final error-class/sub-reason mapping for a blocked
divergent-currency order remains implementation planning, not decided by
this row. Formally remains `open` until ChatGPT accepts DEC-020."

**MBQ-65 (draft register wording):** "Proposed resolved by
[`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md)
(pending ChatGPT acceptance): `PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/
`PRODUCTS_DELETE` are implemented in Phase 1 as **enqueue-only triggers** —
never a direct write — each enqueued job performing a follow-up
authoritative read before any create/update/delete is applied to Odoo, with
the existing DEC-005 layered-sync reconciliation pass as the required
backstop regardless of webhook health. A `PRODUCTS_DELETE` webhook never
directly deletes/archives the bound Odoo product; ambiguous cases route to
manual review via existing error-class vocabulary, none invented.
Subscription-mechanism choice, full-payload-by-default behavior,
`read_products` scope sufficiency, HMAC/`X-Shopify-Webhook-Id` dedup, and
`X-Shopify-Triggered-At`/`updated_at` staleness-ordering guidance are
verified. A variant-count payload-truncation claim remains unconfirmed and
does not change this decision. Exact controller/job/query implementation
mechanics remain implementation planning. Formally remains `open` until
ChatGPT accepts DEC-020."

If accepted, a natural (separate, future) follow-up would be logging MBQ-65
Option D (direct webhook-driven product mutation) and MBQ-64 Option B (as a
Phase 1 mechanism) in `rejected-approaches-log.md` — that file is outside
this record's allowed-files scope and is **not** edited here; this is noted
as a recommendation for a future session, not performed.

## 10. Implementation gate impact

- **Even if DEC-020 is later accepted, the implementation gate remains
  closed** unless ChatGPT explicitly performs the separate, dedicated
  gate-opening act described in `master-blueprint.md`'s "Criteria for when
  implementation may later be opened" and
  [`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md)
  §10. Accepting a currency/webhook design decision is not that act.
- **No implementation task is created** by this record or by its
  acceptance, under any outcome.
- **No code follows directly** from this record or from its acceptance.
- **Exact implementation mechanics remain planning** in every case named
  above (§5, §8): MBQ-56's tolerance value; exact Odoo field/model names
  for presentment evidence (MBQ-01/02); the product-webhook controller's
  exact shape, job-source classification, and follow-up-read query; and
  the still-unconfirmed variant-truncation question, if it later proves
  real.

## 11. Recommendation to ChatGPT

**Recommendation: Accept as proposed (§5 and §8, §5 as revised), with three
named residuals explicitly carried forward, not silently closed:** MBQ-56's
own tolerance/field-selection mechanics (unaffected by this record, still
open, and explicitly not relied upon as the mechanism that catches a
currency-model divergence); the exact final error-class/sub-reason mapping
for a blocked divergent-currency MBQ-64 order (§5 evaluates
`financial total mismatch`'s fit explicitly and declines to force it
without a named, deliberate broadening — left to implementation planning);
and the unconfirmed variant-count payload-truncation claim (§2), which this
record recommends a future implementation-planning session verify directly
against primary `shopify.dev` payload/reference documentation before the
product webhook follow-up-read logic is written. None of these three block
accepting the underlying postures either way: MBQ-64's "no silent SO
creation for a divergent-currency order" and MBQ-65's enqueue-only,
never-direct-write posture are both fixed regardless of how their
respective residuals are eventually resolved.

Both proposed decisions are deliberately the **more conservative** of the
options considered — neither adopts the option this record's own research
found riskiest (MBQ-64 Option B's undesigned pricelist-provisioning
requirement and MVP-scope reopening; MBQ-65 Option D's silent-write risk)
even though each is technically the most "feature-rich" available option,
consistent with this sprint's own instruction to prefer safety and
auditability over feature scope. **MBQ-64's posture was itself made more
conservative in this revision**, after ChatGPT's first review found the
original proposal (shop currency for every Phase 1 order, divergence
caught only via the numeric total-check guard) not safe enough — automatic
import is now scoped to same-currency orders only, and a divergent order
is blocked before SO creation independent of the total-check guard's
outcome. If ChatGPT prefers a different balance — for example, accepting
MBQ-64 Option B as a deliberate, explicit Phase 1 scope expansion, adopting
a specific error-class mapping for the divergent-order block now rather
than leaving it to implementation planning, or MBQ-65 Option B/C instead of
A — that is a **reject and revise** or **accept with change** outcome this
record's tables (§4, §7) are structured to support without new research,
since the evidence for every option is already presented above.
