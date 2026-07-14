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
> historical foundation, not a pending dependency). These capabilities are
> delivered via the **accepted CORE-R2 Slice-2B integration-staging strategy
> (PR #158, review `4691064435`)**, which subsumes PR #150 / #151 in one
> controlled integration PR — **the current unprotected PR #150 / #151 heads are
> not directly mergeable**; Task 012 depends on the *capabilities*, not on any
> specific PR merge. Producing this closure changes the state of no PR (#150,
> #151, #158, #160) and opens no gate.
>
> Companion files: the implementation packet
> [`../07-implementation-plan/task-012-order-import-implementation-packet.md`](../07-implementation-plan/task-012-order-import-implementation-packet.md)
> (carries the D-012-1…12 decisions and the locked prompt) and the
> proposed-scope brief
> [`../07-implementation-plan/task-012-order-import-proposed.md`](../07-implementation-plan/task-012-order-import-proposed.md).
> This closure **supersedes** the packet where they differ; the packet is
> updated in the same PR to match (money-storage type, four-query Option-A
> contract, the **exact per-line source `priceAfterAllDiscountsBeforeTaxesSet`**,
> the **fail-closed refund/removed eligibility gate**, the financial ledger,
> **per-tax-signature base reconciliation**, the **conditional** tax-rounding
> bound, pagination design, GraphQL-cost posture, tax-mapping safety,
> divergent-currency skip seam, and the `execute_business` AST guards).
>
> **Round-3 correction (control-room review `4691067575`, 2026-07-14):**
> reconciled the query contract to the four-query Option-A design (no single
> `ORDER_IMPORT_QUERY`); replaced the approximate-unit-price construction with the
> exact per-line-total field; defined a fail-closed refund/removed-quantity MVP
> posture; added mandatory per-tax-signature base reconciliation and reframed the
> tax bound as a proposed conditional bound with explicit, separately-labelled
> platform-rounding premises; and replaced the stale single-`execute()` guard with
> `execute_business` guards.
>
> **Round-4 correction (control-room review `4691408835`, 2026-07-14):** completed
> the header query with every current-state field the eligibility gates consume
> (`currentTotalPriceSet`/`currentTotalTaxSet`/`currentShippingPriceSet`/
> `currentTotalAdditionalFeesSet`/`currentTotalDutiesSet`/
> `totalCashRoundingAdjustment`; and the `additionalFees` detail — later **removed
> in round-6**, since the aggregate `currentTotal*Set` alone drives the skip);
> added a fail-closed shipping
> refund/removal gate (`isRemoved`, `currentDiscountedPriceSet`) with edge-cursor
> pagination for the **nullable** `ShippingLine.id`; classified unsupported
> **additional fees** and **cash rounding** as named policy skips and fixed the
> duties rule to route on a **nonzero amount** (not non-null); **hardened §6.4a to
> exact currency-quantized per-signature base equality** (resolving the base-vs-Θ
> inconsistency) with a rigorously-defined `tax_delta_bound`; and **base-aligned**
> the branch onto the merged PR #158 `Shopify-connector` tip.
>
> **Round-5 correction (control-room review `4691931971`, 2026-07-14):** converged
> **all three** GraphQL connections (`lineItems`/`shippingLines`/
> `discountApplications`) to one executable `edges{ cursor node }` shape (no
> `nodes`-only reads); made duty/additional-fee routing **duty-first** so a
> duty-only order reaches `unsupported_duties`; reclassified `AdditionalFee.name`
> as **potentially-PII** (redacted/truncated/bounded, out of ordinary logs);
> replaced the rate-only tax key with a **composite `shopify_tax_evidence_key`**
> (rate+title+source+channelLiable+inclusion, collision → hold); **rebuilt the
> residual/tax-base reconciliation around the actual Odoo 19 tax engine** (engine
> `total_excluded`; `price_include_override` on `account.tax`; price-included via
> the engine, not gross subtraction; binary-float honesty; engine-derived
> `tax_delta_bound`, 0 only when engine-proven); and made a **nonzero tip
> fail-closed** (`unsupported_tip_tax_treatment`, no untaxed Tip line).
>
> **Round-6 correction (control-room review `4692656343`, 2026-07-14):** corrected
> the `AdditionalFee` contract (official `id`/`name`/`price`/`taxLines`) and chose
> the **minimal** design — Task 012 **does not query `Order.additionalFees` at
> all**; the aggregate `currentTotalAdditionalFeesSet`/`currentTotalDutiesSet`
> drives the skip and **no fee `name` is requested/stored/logged**. Rebuilt the tax
> identity as a **cryptographic hash of the full, untruncated** normalized evidence
> tuple (an **evidence fingerprint**), with separate redacted/truncated
> display-only previews (no truncated free text in the uniqueness key). Made the tax
> policy **explicit-mapping-only** (no automatic rate fallback — a same-rate Odoo
> tax is an operator **suggestion**, never auto-chosen). **Removed tax
> auto-creation** (`order_tax_autocreate` and the generator) from MVP (relocated to
> a separately-accepted post-MVP scope, §5.2b). Ran a **data-minimization** sweep
> (field-consumption matrix §4.4; removed `note`/`tags`/`sourceName`/
> `customAttributes`/`vendor`/`displayName`/`defaultAddress`). Replaced lexical
> money-string equality with **Decimal-numeric** equality + currency-code match
> (§3.1a). Reconciled the tax-engine terminology to *"no custom connector tax
> engine; the standard Odoo 19 `account.tax` engine is authoritative."*
>
> **Round-7 correction (control-room review `4693694894`, 2026-07-14):** one
> narrow final consistency pass. (1) Corrected the **`Order.additionalFees`
> factual description** — the 2026-07 field **does** expose list/pagination/filter
> arguments, so the reason to omit it is **data minimization**, not "unbounded
> plain list"; the MVP still does not query it. (2) Added a **fail-closed
> order-edit gate** — `Order.edited` is queried and `edited == true` → terminal
> `unsupported_order_edit` skip **before any SO write** (quantity/total checks can
> miss price-only or offsetting edits). (3) Fixed **nullable `totalTaxSet`** — a
> null original tax is normalized to a canonical zero MoneyBag in the order
> currencies and must `money_equal` the (non-null) `currentTotalTaxSet`, else fail
> closed; null no longer silently bypasses the current-vs-original tax check.
> *(This canonical-zero-from-null construction is **superseded by round-8** below —
> a null `totalTaxSet` now fails closed `data_shape_schema_mismatch`.)*
> (4) **Versioned, fold-free tax fingerprint** — `SHOPIFY_TAX_FINGERPRINT_VERSION
> = 1`, fixed **SHA-256**, deterministic length-prefixed UTF-8 serialization
> including the version, output `v1:<hex>`; `title`/`source` are **NFC-only**
> (case **and** whitespace preserved — no case-folding, no whitespace collapse);
> migration posture recorded. (5) **Completed data minimization** — removed
> `DiscountCodeApplication.code`, `ShippingLine.code`, and `ShippingLine.custom`
> (no MVP consumer); retained `ShippingLine.title` reclassified as bounded
> merchant free text. (6) **One supported-tax contract** — explicit mapping to
> **leaf `amount_type == 'percent'` sale taxes only**; `group`/`fixed`/`division`
> and base-affecting compound structures **fail closed** (deferred). (7) **One
> global tax-tolerance formula** — `tol_tax_total = Σ_σ tax_delta_bound(σ) +
> 0.5r(S+O)`, and the MVP requires `tax_delta_bound(σ) = 0` for every admitted
> signature (else fail closed), so `tax_delta_total ≡ 0` and no document calls
> `0.5r(S+O)` "complete" while a nonzero delta is allowed. *(The `tax_delta_bound(σ)
> = 0` clause of this round-7 item is **superseded by round-8**, which records the
> **actual** engine raw-base delta rather than forcing it to zero — see below.)*
>
> **Round-8 correction (control-room review `4694311215`, 2026-07-14):** four
> implementation-safety corrections plus a gate-count fix. (1) **Tax-engine
> contract honesty** — the claim that `special_mode='total_excluded'` is an
> **exact inverse** for every price-included percentage tax is **withdrawn**; Odoo
> 19 guarantees symmetrical accuracy **only** with an unrounded `price_unit` and
> `round_globally`, and `sale.order.line.price_unit` is a **`Float`**, so
> `special_mode` yields a **candidate/seed, not proof of exact representation**.
> The design now: seed → **deterministic bounded solver** (refined in round-9 to
> the finite Product-Price-precision grid contract §6.2b — **not** an open
> "currency-valid" search) → **recompute through the actual Odoo tax engine** (real
> company rounding method, real `account.tax`, real inclusion, real base
> preparation) → **read back** the engine outputs (`raw_total_excluded_currency`,
> `total_excluded_currency`, per-tax `raw_base_amount_currency`,
> `raw_tax_amount_currency`, final rounded `tax_amount_currency`) → **accept only
> from actual engine outputs**, else **fail closed**. (2) **Actual raw-base
> delta** — the MVP no longer claims `delta_engine == 0` for every admitted
> signature; it records the **actual** engine raw-base delta `base_delta(σ) =
> |base_odoo_raw(σ) − base_src(σ)|` and, because MVP taxes are **independent leaf
> percentages only**, includes a **linear** `tax_delta_bound(σ) = base_delta(σ) ×
> rate(σ) / 100` in the bound; `tax_delta_total = Σ_σ tax_delta_bound(σ)` and
> `tol_tax_total = tax_delta_total + 0.5r(S+O)` are used **consistently** (this
> linear term is **never** applied to a deferred complex structure). (3) **`O`
> rounding-event count** — **repartition-line counting is removed**; the tax-engine
> tax details (not invoice/accounting repartition rounding) drive the amounts, so
> `round_per_line` `O =` taxed-line × leaf-tax pairs and `round_globally` `O =`
> distinct leaf-tax grouping keys whose tax is rounded — **not** multiplied by
> invoice repartition rows. *(Round-9 §6.2a: the **order** `amount_tax` comes from
> `sale.order._compute_amounts`/`_get_tax_totals_summary` over the batch, not from
> the line-level `_compute_amount`; `O` is counted from that batch.)* (4) **Nullable
> `totalTaxSet` fails closed** — the round-7
> canonical-zero-from-null construction is **withdrawn**; Shopify does not document
> that null means zero, so a **null** original tax → **no SO, no binding**, fail
> closed as `data_shape_schema_mismatch` (a future dev-store obligation may later
> justify a documented tax-free normalization). (5) **Six eligibility-gate
> families** — the structure is **six** (order edits, product refund/removal,
> shipping refund/removal/modification, duties & additional fees [duty-first],
> cash rounding, tip tax treatment); §6.0.4 is a **clarification pointer** into the
> duty-first §6.0.3 gate, **not** a seventh gate. Then base-aligned onto the
> current `Shopify-connector` tip `a3fd6cd` with a **normal merge commit** (PR #160
> merged).
>
> **Round-9 correction (control-room review `4695589297`, 2026-07-14):** four
> blockers, resolved against the **retrieved official Odoo 19.0 source** (not a
> paraphrase — exact paths recorded in §2). (1) **Order-level financial
> acceptance** — the guard now accepts/rejects **only after the complete
> `sale.order._compute_amounts` batch is recomputed** (new §6.2a). Line-level
> `sale.order.line._compute_amount` computes one line's `price_subtotal`/`price_tax`;
> the **order** amounts come from `_compute_amounts`, which gathers every priced
> line, **adds early-payment-discount base lines**, runs
> `AccountTax._add_tax_details_in_base_lines` → `_round_base_lines_tax_details` →
> `_get_tax_totals_summary`, and assigns `amount_untaxed = base_amount_currency`,
> `amount_tax = tax_amount_currency`, `amount_total = total_amount_currency` — so
> summed line subtotals can differ from the order total under `round_globally`. The
> comparison surface is `sale.order.amount_untaxed`/`amount_tax`/`amount_total` plus
> the batch tax evidence; `O` is defined from the batch grouping keys. (2)
> **Payment-term posture** (new §5.6) — a proposed store setting
> **`order_payment_term_id`** the importer assigns **explicitly** (never inheriting
> the matched partner's `property_payment_term_id`); readiness blocks import when
> it is unset; a term that would add EPD base lines through
> `_add_base_lines_for_early_payment_discount()` **fails closed**
> (`odoo_validation_configuration` / `unsupported_early_payment_discount_payment_term`,
> never `financial_total_mismatch`). (3) **Implementation-exact solver** (new §6.2b)
> — replaces "bounded solver over currency-valid candidates" with a finite,
> deterministic, source-supported contract; because `price_unit` is an **unrounded
> `Float`** (`min_display_digits='Product Price'` is a display hint, **not** a
> storage grid), the solver restricts candidates to a finite **Product-Price-precision
> grid** in a bounded window and **fails closed** (narrowed MVP scope) when no
> candidate reconciles the **order-level** amounts. (4) **Five-document
> consistency** — capability-based prerequisites (no "Task 010/011 merged"), the
> ambiguous-customer path creates **no partial SO/binding** (job →
> `blocked_manual_review`, atomic retry after resolution), no stale "mappings open"
> where the closure proposes them, and no statement attributes the **order**
> `amount_tax` to the line-level compute. `Shopify-connector` tip unchanged at
> `a3fd6cd`; no base-alignment merge needed this round.

---

## 0. Verified state at closure time (2026-07-14)

| Item | Required | Verified state | Class |
| --- | --- | --- | --- |
| `Shopify-connector` **merge-base (round-8)** | current tip `a3fd6cd` | after the **round-8 base-alignment merge** (§0.2), this branch's merge-base with `origin/Shopify-connector` is now exactly `a3fd6cdfcb6f3654ae81a48a7f4e694994d4762b` and the branch is **zero commits behind**; the PR #159 three-dot diff is computed against it and is exactly the five docs files | [Fact — repo] |
| `Shopify-connector` **live tip** | `a3fd6cd` | `origin/Shopify-connector` HEAD is `a3fd6cd` (**PR #160 CORE-R2 Slice 2A merged** at review `4693862195`, 2026-07-14); round-8 **merged that tip into this branch with a normal merge commit** (no rebase/squash/force), so the branch now carries the full PR #160/Slice-2B history and is `mergeable_state: clean`, zero-behind | [Fact — repo] |
| PR #159 (this PR) | open, draft, unmerged | `state:open, draft:true, merged:false`, `mergeable_state:clean`; base `Shopify-connector` (merge-base `a3fd6cd`, branch **zero behind** — the tip did **not** advance this round, so **no base-alignment merge was needed** in round-9); round-9 correction (reviews `4690680028` + `4691067575` + `4691408835` + `4691931971` + `4692656343` + `4693694894` + `4694311215` + `4695589297`); head per PR body | [Fact — repo] |
| PR #150 (Task 011B) | not modified | left as-is (open/draft) — **not a direct-merge prerequisite**; subsumed by the merged Slice-2B strategy | [Fact — repo] |
| PR #151 (Task 010B) | not modified | left as-is (open/draft) — **not a direct-merge prerequisite** | [Fact — repo] |
| CORE-R2 / SRR-03 | remediation open | Foundation Slice 1 merged; **SRR-03 remains OPEN**; **Slice-2B call-site-activation packet (PR #158) is MERGED** (review `4691064435`; merge base `1494b97`); **Slice 2A (PR #160) is now MERGED** (review `4693862195`) as the accepted dormant foundation — neither modified by this PR | [Fact — repo] |
| CORE-R1 | already merged | **satisfied historical foundation** (stores reach `connected`) — not a pending dependency | [Fact — repo] |
| Task LC-1 | not merged | design-only; DEC-030 unaccepted | [Fact — repo] |
| Working tree | clean | clean | [Fact — repo] |

### 0.1 Corrected dependency contract (capability-based)

**[Accepted decision — control-room review `4690680028`]** The earlier
"PR #150 and PR #151 must be **merged directly** into `Shopify-connector`
before Task 012" requirement is **withdrawn**. The corrected CORE-R2
Slice-2B strategy does **not** permit those unguarded domain handlers to
enter `Shopify-connector` first. **Task 012 does not invent its own merge
sequence** — the authoritative integration-staging strategy is the **merged
CORE-R2 Slice-2B call-site-activation packet, PR #158 (control-room review
`4691064435`; merged at `Shopify-connector` tip `1494b97`)**: CORE-R2 Slice 2A
becomes runtime-green and merges; the PR #150/
#151 heads are integrated on a dedicated **staging branch**; their
product/customer Shopify calls are migrated to `execute_business`; the public
generic `execute` entry is closed; the integrated core/product/sale suites and
the deployed multi-worker evidence pass; **one controlled integration PR** enters
`Shopify-connector` carrying the complete net product + customer domains + both
call-site migrations + the core `execute` closure; and PR #150/#151 are then
**closed as merged or subsumed** (never marked individually merged). See PR #158
§7/§7.3 for the exact steps and review decomposition.

**Task 012 prerequisites are therefore capability-based (however the
capabilities arrive — the current unprotected PR #150/#151 heads are NOT
directly mergeable into `Shopify-connector`):**

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

### 0.2 Base alignment (round-4, review `4691408835` item 5)

**[Fact — repo]** PR #158 (CORE-R2 Slice-2B call-site-activation packet, docs
only) is **merged**; `Shopify-connector` advanced to `1494b97…c2c3`. After the
round-4 documentation corrections, this branch is **base-aligned** onto that tip
with a **normal merge commit** (no rebase, no squash, no force-push), preserving
the complete Task 012 decision history **and** the merged PR #158 Slice-2B packet.
PR #158 was docs-only (three Markdown files; no `addons/**` change), so the merge
touches no code and no `addons/**` conflict arises; **SRR-03 remains OPEN** and no
implementation gate is opened. The merge-base with `Shopify-connector` is exactly
`1494b97`.

**Round-7 note (2026-07-14):** after that base alignment, `Shopify-connector`
advanced again to `a3fd6cd` when **PR #160 (CORE-R2 Slice 2A) merged** (an
unrelated `addons/**` change). During round-7 the branch was **deliberately not
rebased** (the round-7 correction started from the required head `8f33b8e` on the
`1494b97` merge-base), and base re-alignment was left to a later step.

**Round-8 base alignment (2026-07-14, review `4694311215` item 4):** after the
round-8 documentation corrections, this branch is **base-aligned onto the current
`Shopify-connector` tip `a3fd6cd`** with a **normal merge commit** (no rebase, no
squash, no force-push), preserving the full five-file Task-012 Round-1–8 history
**plus** the merged PR #160/Slice-2A and PR #158/Slice-2B history and issue #157
separation. PR #160's advance is `addons/**` + CORE-R2 QA docs only, so **no
`addons/**` conflict arises** and the merge touches no Task 012 content; the
branch is now **zero commits behind** `Shopify-connector`, the **merge-base is now
`a3fd6cd`**, and the PR #159 three-dot diff is still exactly the five docs-only
files. **SRR-03 remains OPEN** and no implementation gate is opened.

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
| shopify.dev …/2026-07/objects/LineItem (re-verified 2026-07-14) | Accessible | **`priceAfterAllDiscountsBeforeTaxesSet:MoneyBag!`** *"The total price of the line item… after all discounts are applied and excluding refunded and removed quantities. This value doesn't include taxes."* (canonical exact per-line pre-tax net, current-quantity — §6); **`discountedUnitPriceSet:MoneyBag!`** *"The **approximate** unit price… It doesn't include order-level or code-based discounts"* (display only); **`discountedTotalSet:MoneyBag!`** *"including refunded and removed quantities… doesn't include order-level discounts. Code-based discounts aren't included by default"*; **`originalTotalSet`/`originalUnitPriceSet`** = pre-discount at order creation; **`quantity`** *"including refunded and removed units"* vs **`currentQuantity`** *"excluding refunded and removed units"* (drive the §6.0 eligibility gate); no LineItem field distinguishes refunded from removed; `discountAllocations`/`taxLines`/`customAttributes` are plain lists |
| shopify.dev …/2026-07/interfaces/DiscountApplication + /objects/DiscountAllocation (re-verified 2026-07-14) | Accessible | `allocationMethod`(ACROSS/EACH), `targetSelection`(ALL/ENTITLED/EXPLICIT), `targetType`(LINE_ITEM/SHIPPING_LINE); code-based = `DiscountCodeApplication`; used for tax-signature/`OC` **attribution** (§7), not net-amount computation; `DiscountAllocation.allocatedAmountSet:MoneyBag!` |
| shopify.dev …/2026-07/objects/ShippingLine + /connections/ShippingLineConnection (re-verified 2026-07-14) | Accessible | `discountedPriceSet:MoneyBag!` (original/before-refund post-discount, incl. cart-level as of 2024-07); **`currentDiscountedPriceSet:MoneyBag!`** *"the current shipping price after applying refunds, after applying discounts"*; **`isRemoved:Boolean!`** *"whether the shipping line has been removed"*; **`id:ID` (nullable — a shipping line may have no GID)**; `taxLines:[TaxLine!]!`; the connection supports `edges{ cursor node }` (`ShippingLineEdge.cursor:String!`) |
| shopify.dev …/2026-07/objects/Order (tips + current/original totals + fees + cash rounding, re-verified 2026-07-14) | Accessible | `totalTipReceivedSet:MoneyBag!` (**no `TipLine`; tip tax undocumented** — §6.1-C inference); `totalPriceSet:MoneyBag!`/`totalTaxSet:MoneyBag`(nullable) are *"before returns"*; **`currentTotalPriceSet:MoneyBag!`**/**`currentTotalTaxSet:MoneyBag!`** *"after returns and refunds"*; **`currentShippingPriceSet:MoneyBag!`** *"current shipping price after applying refunds and discounts"*; **`currentTotalAdditionalFeesSet:MoneyBag`(nullable)** *"…duties, import fees, and special handling"*; **`currentTotalDutiesSet:MoneyBag`(nullable)** *"current total duties… after any returns or modifications"*; **`totalCashRoundingAdjustment:CashRoundingAdjustment!`** (`paymentSet`/`refundSet:MoneyBag!`, *"0 if no rounding, or non-cash"*, applied to `totalReceived`/`totalRefunded`); **`additionalFees`** returns `[AdditionalFee!]!` and **exposes list/pagination/filter arguments** in Shopify 2026-07 (it is **not** an unbounded no-argument field) [Fact — official, per review `4693694894`]; each `AdditionalFee{id:ID! name:String! price:MoneyBag! taxLines:[TaxLine!]!}` — has a **stable `id:ID!`**; `name` is arbitrary merchant free text, **not** a safe category label; **Task 012 does not query this field** — the reason is **data minimization** (the aggregate `currentTotal*Set` already drives the skip, so per-fee detail has no MVP consumer and would add cost/privacy exposure), §4.1/§6.0.3) |
| shopify.dev …/usage/limits, /access-scopes, /pagination-graphql | Accessible | leaky-bucket cost model; single-query cap **1,000 points**; `throttleStatus{maximumAvailable,currentlyAvailable,restoreRate}`; `200 Throttled`; `read_orders`+`read_customers`; `read_all_orders` approval-gated; **last-60-days** default order window; page size max **250** |
| shopify.dev changelog: 60-day order access | Accessible | *"public apps will no longer be able to access a merchant's orders older than 60 days with the current `read_orders` or `write_orders` access scopes"* |
| raw.githubusercontent.com/odoo/odoo/19.0 addons/sale/models/sale_order.py, sale_order_line.py | Accessible | `partner_id` required; `partner_invoice_id`/`partner_shipping_id` writable computes; `currency_id` compute-only (pricelist→company); `fiscal_position_id` + line `tax_ids` via `map_tax`; `discount` = "Discount (%)"; `price_tax` compute-only |
| **raw.githubusercontent.com/odoo/odoo/19.0 addons/sale/models/sale_order.py (retrieved 2026-07-14, round-9)** | Accessible | **`amount_untaxed`/`amount_tax`/`amount_total` = `fields.Monetary(compute='_compute_amounts', store=True)` (L232–234); `_compute_amounts` (L512–528, `@api.depends('order_line.price_subtotal','currency_id','company_id','payment_term_id')`): `base_lines = [line._prepare_base_line_for_taxes_computation() for line in order._get_priced_lines()] + order._add_base_lines_for_early_payment_discount()`; `AccountTax._add_tax_details_in_base_lines` → `_round_base_lines_tax_details` → `_get_tax_totals_summary`; `amount_untaxed = tax_totals['base_amount_currency']`, `amount_tax = ['tax_amount_currency']`, `amount_total = ['total_amount_currency']`. `_compute_payment_term_id` (L430–434, `@api.depends('partner_id')`): `payment_term_id = partner_id.property_payment_term_id`. `_add_base_lines_for_early_payment_discount` (L530–573): fires when `payment_term_id.early_discount and early_pay_discount_computation=='mixed' and discount_percentage`; adds ± base lines that alter the taxed base** |
| **raw.githubusercontent.com/odoo/odoo/19.0 addons/sale/models/sale_order_line.py (retrieved 2026-07-14, round-9)** | Accessible | **`price_unit = fields.Float(compute='_compute_price_unit', min_display_digits='Product Price', store=True, …)` (L177–181) — `min_display_digits` is a **display** hint, NOT a storage-rounding `digits=` grid, so the stored value is an unrounded binary float. `_compute_amount` (L852–862, `@api.depends('product_uom_qty','discount','price_unit','tax_ids')`): per-line `AccountTax._add_tax_details_in_base_line` → `_round_base_lines_tax_details([base_line])`; `price_subtotal = tax_details['total_excluded_currency']`, `price_total = ['total_included_currency']` — LINE-LEVEL only. `_prepare_base_line_for_taxes_computation` (L824–845)** |
| raw.githubusercontent.com/odoo/odoo/19.0 addons/account/models/account_tax.py, company.py | Accessible | `amount_type∈{group,fixed,percent,division}`, `amount:Float(16,4)`; `price_include_override∈{tax_included,tax_excluded}` writable, `price_include` compute-only; `res.company.tax_calculation_rounding_method` default **`round_globally`** |
| **raw.githubusercontent.com/odoo/odoo/19.0 addons/account/models/account_tax.py (retrieved 2026-07-14, round-9)** | Accessible | **`_get_tax_details` docstring (L1138–1170): "accurate symmetrical taxes computation with **not rounded `price_unit`** as input and **`round_globally`**… Otherwise, it's not guaranteed." `_add_tax_details_in_base_line` (L1739–1811): `rounding_method = … or company.tax_calculation_rounding_method`; emits `raw_total_excluded_currency`/`raw_tax_amount_currency`/`raw_base_amount_currency` (unrounded), rounds only under `round_per_line`. `_add_tax_details_in_base_lines` (L1813, batch). `_round_tax_details_tax_amounts` (L1896–1927): `round_globally` **grouping key = {tax, currency, is_refund, is_reverse_charge, price_include, computation_key}**, aggregate-then-round-then-distribute-delta. `_round_base_lines_tax_details` (L2184+). `_get_tax_totals_summary` (L2715+): returns `base_amount_currency`/`tax_amount_currency`/`total_amount_currency`** |
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

### 3.1a Money equality rule — Decimal-numeric, never lexical (review `4692656343` item 6)

**[Proposed Task 012 decision]** Every `MoneyV2`/`MoneyBag` comparison in Task 012
— totals and current totals, tax totals, shipping original/current values,
presentment evidence, and the **zero/nonzero gates** for duty, additional fee,
tip, and cash rounding — uses this one rule, `money_equal(a, b)`:

1. **`a.currencyCode == b.currencyCode`** (exact ISO-4217 string match) — a
   currency mismatch is **never** equal, regardless of amount;
2. parse **both** amounts with `decimal.Decimal(amount_string)` (arbitrary
   precision; **never** through `float`);
3. compare the parsed **Decimal values numerically** — so
   `Decimal("10.0") == Decimal("10.00")` is **equal** (same numeric value,
   different lexical form);
4. the **original amount strings are preserved as lossless evidence** (the Char
   snapshots, §3.1) — they are kept for audit, **not** used as the equality test.

A **zero test** (`is_zero`) is `Decimal(amount) == 0` on the parsed value (again
never lexical, so `"0"`, `"0.00"`, `"0.000"` are all zero); a **nonzero gate**
(duty/fee/tip/cash-rounding, §6.0.3/§6.0.5/§6.0.6) fires when the parsed Decimal
is `!= 0`. **Lexical/byte string equality of money amounts is forbidden** — it
would wrongly reject numerically-equal representations such as `10.0` vs `10.00`.
Currency-quantization for the reconciliation tolerance (§6) is a separate,
explicitly-documented step and does not change this exact-value rule. Fixtures
§15 cover `10.0 == 10.00` (equal) and `10.00 USD` vs `10.00 EUR` (**not** equal).

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

**[Proposed Task 012 decision — Option A, four query constants (reconciled
2026-07-14 per review `4691067575` item 1; there is NO single
`ORDER_IMPORT_QUERY` and NO single API call anywhere in Task 012):]** the order
read is expressed as **four** module-level constants, all **read-only, zero
mutations**, scope `read_orders` + `read_customers` (both already granted), each
issued **only** through the merged `execute_business(job, store, query,
variables)` admission context-manager (§0):

- **`ORDER_HEADER_QUERY(gid)`** — order scalar/header fields, currency, **all**
  required money/status/customer/address evidence, order-level `taxLines`, and
  the **first page** of each of the three connections
  (`lineItems`/`shippingLines`/`discountApplications`), each with
  `pageInfo{hasNextPage endCursor}`. Captures `Order.id` and the initial
  `updatedAt` (`updatedAt₀`).
- **`ORDER_LINE_ITEMS_PAGE_QUERY(gid, after)`**,
  **`ORDER_SHIPPING_LINES_PAGE_QUERY(gid, after)`**,
  **`ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY(gid, after)`** — each advances
  **exactly one** connection by `after:$cursor` and **re-verifies** `Order.id`,
  `updatedAt`, `pageInfo`, cursor progress, and node identity (§4.2).

The field list in §4.1 is the **union** of fields these four queries request;
§4.2 fixes which query carries which page. **No statement in this closure, the
packet, or any companion doc describes Task 012 as issuing one query or one API
call.**

### 4.1 Fields requested (exact — distributed across the four queries)

- **Identity / metadata:** `id`, `name`, `legacyResourceId`, `createdAt`,
  `processedAt`, `updatedAt`, `cancelledAt`, `cancelReason`, `test`,
  `confirmed`, `closed`, `closedAt`, `displayFinancialStatus`,
  `displayFulfillmentStatus`, **`edited`** (`Boolean!` [Fact — official] —
  *"whether the order has had any edits applied"*). [Fact — official:
  types/nullability per §2] **`edited` is consumed by the fail-closed order-edit
  gate (§6.0.0):** order edits are out of Task 012 MVP, and `edited == true` →
  terminal `unsupported_order_edit` skip **before any SO write**, because
  quantity/total comparisons alone can miss a **price-only** edit or two
  **offsetting** edits that leave the aggregate total unchanged.
  **Data-minimization (review `4692656343` item 5 — see the field-consumption
  matrix §4.4):** `note`, `tags`, and `sourceName` are **removed** — no Task 012
  gate/ledger/test consumes them, and they are arbitrary free text that can carry
  PII and add GraphQL cost. "Request only fields with a proven MVP consumer" is a
  hard rule here, not a preference.
- **Currency:** `currencyCode`, `presentmentCurrencyCode`, `taxesIncluded`.
- **Order-total money sets** (each `{ shopMoney{amount currencyCode}
  presentmentMoney{amount currencyCode} }` unless noted): original **"before
  returns"** — `totalPriceSet` (**`MoneyBag!`** non-null), `subtotalPriceSet`,
  `totalTaxSet` (**`MoneyBag` nullable** [Fact — official]), `totalDiscountsSet`
  (nullable), `totalShippingPriceSet` (`MoneyBag!`), `totalTipReceivedSet`
  (`MoneyBag!`); **current "after returns/refunds/modifications"** —
  `currentTotalPriceSet` (**`MoneyBag!`**), `currentTotalTaxSet` (**`MoneyBag!`**),
  `currentShippingPriceSet` (**`MoneyBag!`** — *"the current shipping price after
  applying refunds and discounts"* [Fact — official]),
  `currentTotalAdditionalFeesSet` (**`MoneyBag` nullable** — *"the current total
  of all additional fees… after any returns or modifications… duties, import
  fees, and special handling"* [Fact — official]), `currentTotalDutiesSet`
  (**`MoneyBag` nullable** — *"the current total duties amount… after any returns
  or modifications"* [Fact — official]). These current-state fields are
  **consumed by the §6.0 eligibility gates** (refund/removal, additional fees,
  duties). **Every field named by a gate is present in this query.**
- **Cash rounding** (`totalCashRoundingAdjustment` — **`CashRoundingAdjustment!`**
  non-null [Fact — official]): `{ paymentSet{shopMoney{amount currencyCode}
  presentmentMoney{amount currencyCode}} refundSet{shopMoney{amount currencyCode}
  presentmentMoney{amount currencyCode}} }` (both `MoneyBag!`; *"0 if there's no
  rounding, or for non-cash"* [Fact — official]) — consumed by the §6.0
  cash-rounding fail-closed rule.
- **Additional fees — aggregate only, detail NOT queried; omitted for data
  minimization (review `4693694894` item 1).** Official Shopify 2026-07
  `Order.additionalFees` returns **`[AdditionalFee!]!`** and **exposes
  list/pagination/filter arguments** (it is **not** an unbounded field with no
  `first:` argument) [Fact — official, per review `4693694894` — the round-6
  "unbounded plain list" phrasing is **withdrawn**]. Each `AdditionalFee` carries
  **`id: ID!`**, **`name: String!`**, **`price: MoneyBag!`**, **`taxLines:
  [TaxLine!]!`** [Fact — official]. `name` is **arbitrary merchant-provided free
  text (potentially PII)** — **not** a safe/bounded category label and **not** the
  "only differentiator". **Task 012 MVP does not query `Order.additionalFees` at
  all — the reason is *data minimization*, not unboundedness:** the **aggregate**
  `currentTotalAdditionalFeesSet` / `currentTotalDutiesSet` already drive the
  policy skip (§6.0.3), so per-fee detail has **no MVP consumer** and querying it
  would add **unnecessary GraphQL cost and privacy exposure**. Concretely: no
  `additionalFees` selection appears in any of the four query constants, and **no
  `AdditionalFee.name`, `price` payload, or `taxLines` is requested, stored, or
  logged.** The unsupported-fee evidence is **only** the `skip_reason`, the
  aggregate amount, and the currency (§6.0.3). `AdditionalFee.id` (`ID!`) is
  **acknowledged** as the stable technical identifier that any post-MVP per-fee
  feature would key on — but the MVP need is fully served by the aggregate, so
  **no per-fee detail is fetched**.
- **Order-level `taxLines`** (plain list, no pagination): `{ title rate
  ratePercentage priceSet{shopMoney{amount} presentmentMoney{amount}}
  channelLiable source }`.
- **Customer:** `customer { id firstName lastName
  defaultEmailAddress{emailAddress} defaultPhoneNumber{phoneNumber} }`
  (nullable — guest orders), plus order-level `email`. **Data-minimization §4.4:**
  `displayName` is **removed** (derived free text; the partner is resolved by
  indexed **email** matching against the already-imported customer, with
  `firstName`/`lastName` as the SO partner-contact evidence — `displayName` adds
  nothing a consumer reads); `customer.defaultAddress` is **removed** (the SO's
  invoice/delivery addresses come from the **order's** `billingAddress`/
  `shippingAddress`, not the customer's default — no consumer).
- **Addresses:** `billingAddress` and `shippingAddress` (nullable
  `MailingAddress`) `{ firstName lastName name company address1 address2 city
  zip provinceCode countryCodeV2 phone }`.
- **Line items** (connection — paginate via **edges/cursor**, §4.2):
  `lineItems(first: 100){ edges{ cursor node{
  id name title variantTitle quantity currentQuantity sku isGiftCard
  requiresShipping taxable variant{ id } product{ id }
  originalUnitPriceSet{shopMoney{amount}} originalTotalSet{shopMoney{amount}}
  discountedUnitPriceSet{shopMoney{amount}} discountedTotalSet{shopMoney{amount}}
  priceAfterAllDiscountsBeforeTaxesSet{shopMoney{amount currencyCode}
  presentmentMoney{amount currencyCode}}
  discountAllocations{ allocatedAmountSet{shopMoney{amount} presentmentMoney{amount}}
  discountApplication{ __typename index targetType allocationMethod targetSelection } }
  taxLines{ title source rate ratePercentage priceSet{shopMoney{amount}} channelLiable }
  } } pageInfo{ hasNextPage endCursor } }`
  (`vendor`, `customAttributes`, **and the `... on DiscountCodeApplication { code }`
  selection** are **removed** — data-minimization §4.4: no Task 012 consumer;
  `customAttributes` is arbitrary key/value free text that can carry PII, and the
  discount `code` is free text not required for exact amount/tax attribution — the
  `OC` order-level/code partition is decided from `__typename` +
  `targetSelection`, not from the code string.)
  (`LineItem.id` is non-null [Fact — official] — the immutable **secondary**
  business identity behind the edge cursor).
  **`priceAfterAllDiscountsBeforeTaxesSet` is the canonical exact per-line
  financial target** — *"The total price of the line item… after all discounts
  are applied and excluding refunded and removed quantities. This value doesn't
  include taxes."* [Fact — official]. It is a line **total** (not a unit price),
  is **after both line-level and order-level/code discounts**, is **always
  tax-exclusive**, and reflects **current (net-of-refund/edit) quantity** — so
  it is the ledger's product invariant (§6.1-A). By contrast
  `discountedUnitPriceSet` is *"the **approximate** unit price… It doesn't
  include order-level or code-based discounts"* [Fact — official] — **display
  evidence only, never a financial invariant** (do **not** assume `quantity ×
  discountedUnitPriceSet == discountedTotalSet`); and `discountedTotalSet`
  *"includes refunded and removed quantities"* and excludes order-level
  discounts [Fact — official], so it is **not** a net current-quantity total.
  `quantity` (*"including refunded and removed units"*) and `currentQuantity`
  (*"excluding refunded and removed units"*) [Fact — official] drive the
  fail-closed refund/removed eligibility gate (§6.0). The
  `discountApplication.__typename`/`targetSelection` drive the tax-signature/`OC`
  **attribution** (§7), not the net-amount computation. The line-level
  `discountAllocations` and `taxLines` are **plain lists** [Fact — official] — no
  nested pagination needed.
- **Shipping lines** (connection — paginate via **edges/cursor** because
  `ShippingLine.id` is **nullable** [Fact — official], §4.2a):
  `shippingLines(first: 50){ edges{ cursor node{
  id isRemoved title
  discountedPriceSet{shopMoney{amount currencyCode} presentmentMoney{amount currencyCode}}
  currentDiscountedPriceSet{shopMoney{amount currencyCode} presentmentMoney{amount currencyCode}}
  taxLines{ title source rate ratePercentage priceSet{shopMoney{amount} presentmentMoney{amount}} channelLiable } } }
  pageInfo{ hasNextPage endCursor } }`. **`isRemoved`** (`Boolean!`) and
  **`currentDiscountedPriceSet`** (`MoneyBag!` — *"the current shipping price after
  applying refunds, after applying discounts"*) drive the §6.0 shipping
  eligibility gate; `discountedPriceSet` is the **original/before-refund**
  post-discount price [Fact — official]. (`ShippingLine.code` and
  `ShippingLine.custom` are **removed** — data-minimization §4.4: neither has a
  named ledger/gate consumer.) **`ShippingLine.title`** is retained **only** as the
  Odoo `sale.order.line` **shipping-line description** — its sole consumer; it is
  classified as **merchant-provided free text**, bounded at the Odoo field
  boundary, and kept **out of ordinary technical logs** (§13).
- **Discount applications** (connection — paginate via **edges/cursor**):
  `discountApplications(first: 50){ edges{ cursor node{
  __typename index allocationMethod targetSelection targetType } } pageInfo{
  hasNextPage endCursor } }` (evidence/reconciliation; per-line money comes from
  each line's `discountAllocations`). **`DiscountApplication` is an interface with
  no `id`/GID** [Fact — official] — its **secondary** identity is
  `__typename`+`index` behind the edge cursor.

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
  lineItems(first:100, after:$after){ edges{ cursor node{…} } pageInfo{hasNextPage endCursor} } }`.
- `ORDER_SHIPPING_LINES_PAGE_QUERY(gid, after)` — same shape for `shippingLines`
  (**edges/cursor** — see §4.2a, `ShippingLine.id` is nullable).
- `ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY(gid, after)` — same for
  `discountApplications`.

Every connection — in the header first page **and** each page query — is read as
`edges{ cursor node{…} } pageInfo{hasNextPage endCursor}`, so the **edge cursor**
is the mandatory pagination identity (§4.2a); a non-null `node.id` is a
**secondary business identity** used only when present. Each connection has its
**own** cursor loop and accumulator; only the connection being advanced re-fetches
(the header's first pages are **not** re-fetched, so **no first-page
duplication**). Every page (header first-pages included) is validated:

- run the page **through `execute_business`** (§0 admission);
- **verify `Order.id == requested GID`** (else `data_shape_schema_mismatch`);
- **verify `updatedAt == updatedAt₀`** — if it changed, this is a **torn read**
  (§4.2.1);
- **require `pageInfo` present**; if `hasNextPage == true`, **require a non-empty
  `endCursor`** (else `data_shape_schema_mismatch`);
- **require cursor progress** — the new `endCursor` must differ from the prior
  page's cursor and the page must add ≥1 edge (a repeated `endCursor` while
  `hasNextPage` → `data_shape_schema_mismatch`, preventing an infinite loop);
- **deduplicate by edge cursor (mandatory), then by the connection's secondary
  identity** (§4.2a): a **duplicate edge cursor** → `data_shape_schema_mismatch`;
  a **repeated `endCursor`** → `data_shape_schema_mismatch`; a **conflicting
  secondary identity** → `data_shape_schema_mismatch`. The secondary identity is:
  **`LineItem.id`** (non-null [Fact — official], the immutable business identity);
  **`ShippingLine.id`** (nullable — used only when present, never as a stable GID
  when null); **`DiscountApplication.__typename`+`index`** (the interface has **no
  `id`** [Fact — official]). No node is accumulated twice;
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

#### 4.2a Shipping-line pagination identity (nullable `ShippingLine.id`) (task §5)

**[Fact — official]** `ShippingLine.id` is **`ID` (nullable)** — a shipping line
may have **no** GID. **[Proposed Task 012 decision]** A "dedup all nodes by GID"
rule is therefore unsafe for shipping. The connection is read as
`shippingLines(first:…, after:…){ edges{ cursor node{ id … } } pageInfo{
hasNextPage endCursor } }` (the `ShippingLineConnection` supports
`edges{ cursor node }` with `ShippingLineEdge.cursor: String!` [Fact — official]).
Identity rules:

- the **edge `cursor`** is the **mandatory** pagination identity — accumulate by
  cursor; a **duplicate edge cursor** → `data_shape_schema_mismatch`;
- a **repeated `pageInfo.endCursor`** while `hasNextPage` → `data_shape_schema_mismatch`;
- a **non-null `node.id`** is a **secondary** business identity — a **conflicting
  duplicate non-null id** (same id, different node, or the same id under two
  distinct cursors) → `data_shape_schema_mismatch`;
- a **null `node.id`** is **never** silently treated as a stable GID (it is used
  only as `False`/absent business identity; the cursor still governs
  accumulation);
- **no shipping node is accumulated twice.**

The **same cursor discipline is applied consistently to the header first page and
the shipping page query** (both use `edges{ cursor node }`), so a node appearing
in the header first page and again in a page query is caught by cursor identity.

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

### 4.4 Field-consumption matrix + data minimization (task §7, review `4692656343` item 5)

**[Proposed Task 012 decision]** Every requested field must have a **named MVP
consumer** (a gate, the ledger, a mapping/identity, an idempotency/checkpoint
key, or a validation). **Arbitrary free text is not requested "in case it is
useful later."** Query constants: **H** = `ORDER_HEADER_QUERY`, **LI** =
`ORDER_LINE_ITEMS_PAGE_QUERY`, **SL** = `ORDER_SHIPPING_LINES_PAGE_QUERY`, **DA** =
`ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY` (H carries each connection's first page).

| Field(s) | Query | Consumer / decision | Persistence / validation purpose | Privacy class | Why necessary |
| --- | --- | --- | --- | --- | --- |
| `id` | H, LI, SL, DA | idempotency + per-page `Order.id` verify (§4.2) | binding `external_id`; GID match | non-PII (GID) | primary key / anti-forgery |
| `name`, `legacyResourceId` | H | operator-facing order ref; REST cross-ref | evidence + binding cross-map | low (order number) | traceability |
| `createdAt`, `processedAt`, `updatedAt` | H, LI, SL, DA | checkpoint ordering; **`updatedAt` torn-read** (§4.2.1) | checkpoint/evidence | non-PII | required by gate |
| `cancelledAt`, `cancelReason`, `confirmed`, `closed`, `closedAt`, `displayFinancialStatus`, `displayFulfillmentStatus` | H | eligibility gates (cancelled/closed/financial-state) | evidence | non-PII | required by gate |
| `edited` | H | **order-edit fail-closed gate** (§6.0.0) — `edited==true` → `unsupported_order_edit` | evidence (`edited`, GID, `updatedAt`) | non-PII (boolean) | required by gate |
| `test` | H | test-order filter (`order_import_include_test`) | — | non-PII | required by gate |
| `currencyCode`, `presentmentCurrencyCode`, `taxesIncluded` | H | currency guard; inclusion posture | ledger/tax | non-PII | required by ledger/tax |
| all order money sets (`totalPriceSet`…`current*`, `totalCashRoundingAdjustment`) | H | canonical ledger + §6.0 gates | lossless money evidence | non-PII (amounts) | required by ledger/gate |
| `currentTotalAdditionalFeesSet`, `currentTotalDutiesSet` | H | **fee/duty skip** (§6.0.3) — aggregate drives the skip | evidence (amount+currency) | non-PII (amounts) | required by gate |
| order-level `taxLines{title source rate ratePercentage priceSet channelLiable}` | H | tax **evidence fingerprint** (§5.2a) + reconciliation (§6) | mapping identity + tolerance | `title`/`source` **potentially-sensitive** → hashed/redacted (§5.2a) | required by tax identity |
| `customer.id` | H | customer match / binding | binding | non-PII (GID) | required by resolution |
| `customer.defaultEmailAddress`, order `email` | H | **indexed email match** to the imported customer | resolution key | contact PII | required matching key |
| `customer.firstName`, `customer.lastName`, `customer.defaultPhoneNumber` | H | SO partner-contact fields on match | SO partner contact | contact PII | consumed by SO partner |
| `billingAddress`, `shippingAddress` | H | SO invoice/delivery address | SO addresses | address PII | required by SO |
| line: `id` | LI | secondary dedup identity (§4.2) | — | non-PII | required by pagination |
| line: `name`, `title`, `variantTitle`, `sku` | LI | SO line description; product-resolution evidence | SO line + evidence | low | consumed by SO line |
| line: `quantity`, `currentQuantity` | LI | **refund/removed gate** (§6.0.1) | evidence | non-PII | required by gate |
| line: `isGiftCard`, `requiresShipping`, `taxable` | LI | line flags (tax/shipping treatment) | ledger/tax | non-PII | consumed by ledger/tax |
| line: `variant{id}`, `product{id}` | LI | Odoo product/variant resolution (prereq binding) | SO line product | non-PII (GID) | required by resolution |
| line price sets + `priceAfterAllDiscountsBeforeTaxesSet` | LI | canonical exact line net (§6.1-A) | ledger | non-PII (amounts) | required by ledger |
| line: `discountAllocations` + `discountApplication{__typename index targetType allocationMethod targetSelection}` | LI | discount **attribution** (§7) — `OC` partition from `__typename`+`targetSelection` | evidence | non-PII (no free-text `code`) | required by attribution |
| line: `taxLines{…}` | LI | tax fingerprint + reconciliation | mapping identity | `title`/`source` potentially-sensitive → hashed | required by tax identity |
| shipping: `id`, `isRemoved`, `discountedPriceSet`, `currentDiscountedPriceSet`, `taxLines{…}` | SL | **shipping refund/removal gate** (§6.0.2) + ledger + fingerprint | evidence/ledger | non-PII (amounts) / hashed titles | required by gate/ledger |
| shipping: `title` | SL | Odoo SO shipping-line **description** (sole consumer) | SO line text | merchant free text → bounded at Odoo field, out of ordinary logs (§13) | consumed by SO line |
| discount app: `__typename`, `index`, `allocationMethod`, `targetSelection`, `targetType` | DA | discount attribution evidence + DA secondary identity | evidence | non-PII | required by attribution |

**Removed fields (no MVP consumer — review `4692656343` item 5):**

| Removed field | Was in | Why removed |
| --- | --- | --- |
| `Order.note` | H | arbitrary merchant free text (PII risk), no consumer/test |
| `Order.tags` | H | arbitrary free text (PII risk), no consumer/test |
| `Order.sourceName` | H | audit-only free text, no MVP gate/ledger consumer |
| `LineItem.customAttributes` | LI | arbitrary key/value free text (PII risk), no consumer |
| `LineItem.vendor` | LI | free text; product is resolved by variant/product GID, not vendor |
| `customer.displayName` | H | derived free text; email + given/family name suffice |
| `customer.defaultAddress` | H | SO uses the **order's** billing/shipping addresses, not the customer default |
| `DiscountCodeApplication.code` | LI | free text; **not** required for exact amount/tax attribution (the `OC` partition uses `__typename`+`targetSelection`), PII/cost risk (review `4693694894` item 5) |
| `ShippingLine.code` | SL | no named ledger/gate consumer (review `4693694894` item 5) |
| `ShippingLine.custom` | SL | no named ledger/gate consumer (review `4693694894` item 5) |

If a later slice needs one of these, it must be **re-added with a named consumer
and test**, not carried speculatively. The **query-cost fixtures (§15)** assert
none of the removed fields appears in any of the four query constants.
`ShippingLine.title` is **retained** (SO shipping-line description — its named
consumer) but classified as **merchant free text**, bounded at the Odoo field
boundary and excluded from ordinary technical logs (§13).

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

**[Proposed Task 012 decision — EXPLICIT-MAPPING-ONLY, review `4692656343`
items 3 & 4]** For each distinct `TaxLine` on a line or shipping line, the
importer resolves an `account.tax` **only** through an explicit operator mapping
keyed by the tax **evidence fingerprint** (§5.2a). Ordinary order import
**never** silently creates accounting configuration and **never** auto-selects a
tax from a bare rate match:

1. **Explicit mapping — the only automatic resolution path.** Connector model
   `shopify.connector.tax.mapping` (`store_id`; **`shopify_tax_evidence_key`
   Char** — the **version-prefixed SHA-256 hash of the full normalized evidence
   tuple**, format `v1:<sha256 hex>`, §5.2a; a separate stored
   `shopify_tax_fingerprint_version` integer; `account_tax_id` M2o `account.tax`
   required `restrict`; **`UNIQUE(store_id, shopify_tax_evidence_key)`**). A hit
   resolves **only after**
   the resolved `account_tax_id` passes the §5.5 validations (company / `sale` /
   active / percent / inclusion / **fiscal-position revalidation**). Because the
   key is the fingerprint **hash**, **one fingerprint maps to exactly one Odoo
   tax** and it **can never silently change** — a mapping row is a deliberate,
   audited operator action. The round-1..4 rate-only key
   (`UNIQUE(store_id, shopify_rate_key, price_include)`) **and** any earlier
   composite key that placed **truncated** free text into the identity are
   **withdrawn** — a rate-only key collapses distinct same-rate taxes, and a
   truncated-title key can collide two different long titles (§5.2a).
2. **No automatic existing-tax fallback — a rate match is a SUGGESTION only.**
   Odoo `account.tax` has **no** Shopify `source`/`channelLiable`/`title` fields,
   so a single same-rate Odoo tax is **not** proof of a whole-fingerprint match
   [Fact — repo/official]. The importer therefore **never** auto-selects an
   existing tax by rate. For an **unmapped** fingerprint the **readiness surface
   may present** any same-rate, inclusion-compatible `account.tax` candidates as a
   **non-binding operator suggestion** (to speed creating the mapping), clearly
   labelled *"rate-only suggestion — confirm this is the correct
   jurisdiction/account before mapping."* The **operator**, not the importer,
   chooses; nothing is imported until the mapping row exists.
3. **Zero or ambiguous mapping → hold, never guess, never create.** **Zero**
   mapping rows for a fingerprint → `odoo_validation_configuration`
   (`failed_retryable`) naming the **redacted** evidence (rate + inclusion +
   truncated title/source **preview**, §5.2a). **More than one** mapping
   resolving for a fingerprint (a configuration defect the `UNIQUE` constraint
   should prevent, re-checked at resolution) → **ambiguous configuration hold**.
   The readiness surface lists every unmapped/ambiguous fingerprint seen in
   holds; the operator creates/verifies the Odoo tax, adds the mapping, and
   retries (the §5.2b operator flow). **One fingerprint can never silently change
   its Odoo tax.**
4. **No tax auto-creation in MVP (removed — review `4692656343` item 4).** Task
   012 MVP contains **no automatic `account.tax` creation path**: the
   `order_tax_autocreate` setting and the `"Shopify Tax {percent}%"` generator
   are **removed from scope** (rationale + relocation in §5.2b). The required
   operator flow is always **create/verify the correct Odoo tax → create the
   explicit connector mapping → retry the held order.**

**Rate-unit pinning + canonicalization [Proposed Task 012 decision]:** the
query requests **both** `TaxLine.rate` (decimal proportion, e.g. `0.06`) and
`TaxLine.ratePercentage` (percentage, e.g. `6.0`) [Fact — official]. The
**authoritative rate input is `ratePercentage`**, parsed with `decimal.Decimal`
(never `float`), quantized to 6 dp, trailing zeros stripped — so `6.0`, `6.00`,
`6.000` → the single canonical `"6"`, and `8.375` → `"8.375"`. The connector
verifies `rate × 100 == ratePercentage` within 6-dp precision; disagreement, or a
null/empty `rate`/`ratePercentage`, → `data_shape_schema_mismatch` hold. This
rejects the ambiguity where a bare `0.06` could mean 0.06 % or 6 %.

### 5.2b Why tax auto-creation is removed from MVP (review `4692656343` item 4)

**[Proposed Task 012 decision]** Automatic `account.tax` creation is **removed
from Task 012 MVP** (the `order_tax_autocreate` opt-in and the `"Shopify Tax
{percent}% ({incl|excl})"` generator no longer exist in scope). Recorded reasons:

- **Same-rate evidence fingerprints can mean different jurisdictions or
  accounting treatment.** Two distinct 5 % taxes (state vs city, different
  `source`/liability) share a rate; auto-creating "one 5 % tax" would **collapse
  accounting meaning** and route both to the same account.
- **Default repartition/accounts are not safe accounting configuration.** A
  generated tax uses default tax/base repartition lines and no chosen accounts —
  which is an accounting decision the connector must **not** make silently.
- **The generic name collides.** `"Shopify Tax 5% (excl)"` is one name for many
  different real taxes, so distinct fingerprints would map onto one generated
  tax.
- **Odoo 19 enforces tax-name uniqueness** in the applicable
  company/country/type-of-use scope [Fact — official], so a repeated generated
  name can raise a **constraint error** at create time — an ugly failure mode
  inside an import.
- **Accounting configuration requires operator ownership.** Which ledger account
  a tax posts to is the accountant's decision, not the importer's.

**Required operator flow (the only supported path):**

1. the operator **creates or verifies** the correct Odoo `account.tax` (right
   rate, inclusion, company, accounts, repartition);
2. the operator **creates the explicit connector mapping**
   (`shopify.connector.tax.mapping` row: fingerprint → that tax);
3. the operator **retries the held order** — resolution now succeeds via §5.2
   step 1.

Automatic tax creation, **if ever wanted**, is relocated to a **separately
accepted post-MVP scope** and must there carry evidence-fingerprint-specific
naming, explicit accounting confirmation, and name-collision tests before it can
be proposed **[Deferred / non-MVP]**.

### 5.2a `shopify_tax_evidence_key` — versioned full-tuple SHA-256 evidence **fingerprint** (review `4692656343` item 2; `4693694894` item 4)

**[Proposed Task 012 decision]** Because `TaxLine` has **no `id`/GID** [Fact —
official] — and `title`/`source` are **not officially stable identifiers**, only
**observed evidence** — a Shopify tax is identified by an **evidence
fingerprint**: a deterministic hash of the **full, untruncated** normalized
evidence tuple. Changed evidence is treated as a **new, unmapped fingerprint**
(it holds until an operator maps it), **not** as "the same tax with a new label."

**Versioned identity contract (review `4693694894` item 4 — fixed version,
algorithm, serialization; case/whitespace preserved):**

The fingerprint is a **versioned** contract so future normalization/algorithm
changes migrate cleanly:

- **Fixed version:** `SHOPIFY_TAX_FINGERPRINT_VERSION = 1` (a module constant,
  also stored on each mapping/hold row as `shopify_tax_fingerprint_version`).
- **Fixed algorithm:** **SHA-256** (hex-encoded) — **not** "for example a hash";
  the algorithm is pinned to version 1.
- **Fixed serialization:** a **deterministic length-prefixed UTF-8** encoding of
  the ordered fields **including the version**, so no field's content can forge a
  delimiter boundary.

1. **Normalize the FULL values — preserving case and whitespace** (no length
   bound, **no case-folding, no whitespace collapse** — Shopify does **not** define
   `title`/`source` as case-insensitive or whitespace-insensitive identifiers, so
   folding them could collapse genuinely distinct observed evidence):
   - `version` — the integer `SHOPIFY_TAX_FINGERPRINT_VERSION` (= `1`), serialized
     first;
   - `rate_key` — canonical `ratePercentage` (above; a numeric quantity, safe to
     canonicalize);
   - `title_norm` — **full** `TaxLine.title` (`String!`): **Unicode NFC only** —
     **case preserved**, **all leading/trailing/internal whitespace preserved**,
     **not truncated**, **not case-folded**, **not whitespace-collapsed**;
   - `source_norm` — **full** `TaxLine.source` (`String`, **nullable**): **Unicode
     NFC only** (same case/whitespace preservation), with an **explicit null
     marker distinct from the empty string** (null → reserved sentinel, so a null
     source and an empty-string source are **different** fingerprints);
   - `liable_key` — `channelLiable` (`Boolean`, **nullable**) as a **tri-state**
     (`true`/`false`/`null` are three distinct values — `null` = *"unknown
     liability"* [Fact — official], not `false`);
   - `inclusion_key` — the order's effective inclusion posture
     (`Order.taxesIncluded` → the mapping's `account_tax_id.price_include_override`).
2. **Serialize** `(version, rate_key, title_norm, source_norm, liable_key,
   inclusion_key)` into one **deterministic length-prefixed UTF-8** byte string
   (each field length-prefixed so content cannot forge a boundary).
3. **Hash** that byte string with **SHA-256** (hex-encoded) and **prefix the
   version** → **`shopify_tax_evidence_key = "v1:" + sha256_hex`**.
4. Use the **version-prefixed key** in **`UNIQUE(store_id, shopify_tax_evidence_key)`**.

**Because Unicode NFC is the *only* normalization — case and whitespace are
preserved — `"GST"` and `"gst"`, or one space vs two spaces, produce DIFFERENT
fingerprints; and because the full title/source are hashed (not truncated) before
identity, two long titles sharing a displayed prefix also produce DIFFERENT
fingerprints** (fixtures §15). NFC-equivalent Unicode spellings of the same
characters produce the **same** fingerprint (canonical equivalence only).

**Migration posture (versioned).** Changing the normalization rules or the hash
algorithm **requires a new `SHOPIFY_TAX_FINGERPRINT_VERSION`** (`v2:` …). Existing
`v1:` mapping rows remain **interpretable and matchable as v1** — the connector
**never silently recomputes** a stored key under a different version; a version
bump is an explicit, migration-guarded step, and `v1:` and a future `v2:` key
space **cannot collide** (the version prefix and the version-inside-the-hash both
differ).

**Separate stored/display fields (never the identity):** alongside the key, each
mapping/hold row stores, distinctly:

- `shopify_tax_fingerprint_version` — the integer version (= `1`);
- the SHA-256 hash (inside the `v1:<hex>` key);
- `title_preview` — **redacted + truncated** title (`TAX_TITLE_PREVIEW_MAX_LEN`)
  — display only;
- `source_preview` — **redacted + truncated** source — display only;
- `rate`, `channelLiable` (liability), and the inclusion posture (non-free-text).

**Raw `title`/`source` never enter ordinary logs** — only the version+hash and the
redacted previews do; the previews are for protected display and are **not** used
in the uniqueness key. **The same evidence fields (`title`, `source`,
`channelLiable`, `rate`, `ratePercentage`) are queried on product-line
`taxLines`, shipping-line `taxLines`, and the order-level `taxLines`** (§4.1), so
the fingerprint is computed identically everywhere. Normalization/serialization
rules are the mapping model's `@api.depends` for the stored key. No `TaxLine` GID
is assumed (there is none). **Do not describe `title`/`source`/`channelLiable` as
officially stable identifiers** — they are a versioned evidence fingerprint.

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
| `account.tax` auto-create (any form, incl. admin opt-in) | **Removed from MVP** | Collapses same-rate accounting meaning, unsafe default repartition, generic-name collision, Odoo tax-name-uniqueness constraint, accounting is operator-owned (§5.2b); relocated to a separately-accepted post-MVP scope |
| Auto-select an existing same-rate `account.tax` | **Removed from MVP** | Odoo tax has no Shopify source/liability/title; a rate match is not a whole-fingerprint match — presented only as a non-binding operator **suggestion**, never chosen by the importer (§5.2 step 2) |
| Truncated free text inside the uniqueness key | Rejected | Two long titles sharing a prefix could collide — the identity now hashes the **full** normalized tuple (§5.2a) |
| Float rate key / raw float equality | Rejected | Precision-unsafe; canonical decimal-string key + `float_compare(precision_digits=6)` required |

### 5.4 Exact safety limitations, readiness, operator config, test matrix

- **Safety limitations:** Odoo may compute a tax amount that differs from
  Shopify's by a legitimate rounding step; the guard (§6) bounds this and
  **rejects** anything beyond it. The connector never overrides Odoo's computed
  tax. Three-decimal-currency Shopify rounding is undocumented **[Open
  question]** → a named dev-store empirical check precedes onboarding any
  three-decimal store.
- **Readiness requirements:** the readiness surface warns (a) while any tax
  **evidence fingerprint** is **unmapped** (holds pending — no automatic rate
  fallback exists), and (b) when the company's `tax_calculation_rounding_method`
  is `round_per_line` vs `round_globally`, because that determines the tolerance's
  `O` term and how closely Odoo's tax will match Shopify's per-line tax (§6.4) —
  the connector **reads** this setting, never changes it. For an unmapped
  fingerprint it **may** list same-rate `account.tax` candidates as a
  **non-binding suggestion** to speed mapping creation. A **dev-store validation
  obligation** is also recorded for **nullable `totalTaxSet`** — the MVP fails
  closed on null (§6.0.1); whether Shopify emits null for a legitimate tax-free
  case must be confirmed on an authorized dev store before any null→zero
  normalization is even proposed (§18, review `4694311215` item 3). **(c) Readiness
  BLOCKS order import while `order_payment_term_id` is unset** (§5.6), and holds
  (`odoo_validation_configuration` / `unsupported_early_payment_discount_payment_term`)
  when the configured term would add early-payment-discount base lines
  (`_add_base_lines_for_early_payment_discount`) — the connector reads the term's
  `early_discount`/`early_pay_discount_computation`/`discount_percentage`, never
  changes them (round-9, review `4695589297` item 2).
- **Operator configuration:** operators map each fingerprint in
  `shopify.connector.tax.mapping` (shell/import until the settings-area UI phase).
  **There is no `order_tax_autocreate` and no automatic tax creation** — the
  operator creates/verifies the Odoo tax, adds the mapping, and retries (§5.2b).
- **Test matrix:** taxes-included vs excluded; single rate; two rates on one
  order; mixed taxed + untaxed lines; a fractional rate (`8.375%`); `5.0`/`5.00`/
  `5.000` canonical-rate equivalence; `rate`/`ratePercentage` disagreement →
  schema hold; null rate → schema hold; **explicit mapping hit**; **unmapped
  fingerprint → configuration hold (no automatic fallback)**; **same-rate
  existing tax is a suggestion only, never auto-chosen**; **no tax auto-create,
  so no Odoo duplicate-name risk**; two long titles with an equal truncated
  preview → **different fingerprints**; a source/title change → **new unmapped
  fingerprint**; `round_globally` vs `round_per_line` tolerance (§6); **>1 mapping
  → ambiguous hold**; **company-mismatch mapping rejected**. **No acceptance is
  claimed** — these are the fixtures the implementation must pass.

### 5.5 Tax-mapping safety and the company-scope decision (task §9)

**[Proposed Task 012 decision]** The **explicit-mapping path (§5.2 step 1)** is
the only path that resolves a tax, and it resolves **only** when every one of
these holds (otherwise it holds, never guesses); the same invariants also gate
whether a same-rate tax may even be **suggested** to the operator:

- `account_tax_id.company_id == order_company_id` (the store-settings company);
- `type_tax_use == 'sale'`;
- `active == True`;
- **`amount_type == 'percent'` — leaf percentage taxes ONLY (one MVP contract,
  review `4693694894` item 6).** The mapping target must be a **leaf percent**
  `account.tax`. A tax whose `amount_type ∈ {'group', 'fixed', 'division'}`, or any
  **base-affecting compound** structure (`include_base_amount == True` /
  `is_base_affected` behaviour, or a sequence whose base cannot be reconciled by
  the §6.2 engine solver), is **NOT supported in MVP**: the mapping/resolution
  **fails closed** with `odoo_validation_configuration`
  (`unsupported_tax_structure`) rather than importing. **Multiple independent
  mapped percentage taxes may apply to one line** (each a distinct signature,
  §6.4a). Advanced tax structures (group/compound/fixed/division/base-affecting)
  are **[Deferred / non-MVP]**, a separately accepted post-MVP scope — this
  closure makes **no** claim that group children are counted or that group/compound
  taxes are supported;
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
mapping's `UNIQUE(store_id, shopify_tax_evidence_key)` (§5.2a) therefore also
uniquely determines the company** (via the store), so it cannot yield two taxes
in different companies for one evidence key.

### 5.6 Payment-term posture — explicit, no silent early-payment discount (round-9, review `4695589297` item 2)

**Why this matters [Fact — Odoo 19 source].** `sale.order._compute_payment_term_id`
(`sale_order.py` L430–434, `@api.depends('partner_id')`) sets `payment_term_id =
partner_id.property_payment_term_id` — so **a matched customer's default payment term
would silently apply**. And `sale.order._compute_amounts` **adds early-payment-discount
base lines** via `_add_base_lines_for_early_payment_discount()` (`sale_order.py`
L530–573) whenever the term has `early_discount and early_pay_discount_computation ==
'mixed' and discount_percentage`; those ± base lines **change the taxed base and hence
`amount_tax`** (`_get_tax_totals_summary` runs over them). A silently-inherited EPD
term would therefore make Odoo's `amount_tax` diverge from Shopify's — a financial
error masquerading as tolerance.

**[Proposed Task 012 decision] MVP payment-term contract:**

1. **Proposed store setting `order_payment_term_id`** (an `account.payment.term`
   reference on the store settings, company-scoped like `order_company_id`).
2. The importer **explicitly assigns** `sale.order.payment_term_id =
   store.order_payment_term_id` on every imported order.
3. It **never silently inherits** the matched partner's `property_payment_term_id`
   (the default compute is explicitly overridden by the connector's assignment).
4. **Readiness blocks order import** while `order_payment_term_id` is **unset** (a
   readiness surface warning, §5.4) — no order is imported without an explicit term.
5. The selected term **must produce no early-payment-discount base lines** through
   `sale.order._add_base_lines_for_early_payment_discount()` — i.e. it must **not**
   satisfy (`early_discount and early_pay_discount_computation == 'mixed' and
   discount_percentage`). The connector checks the configured term's fields at
   readiness/assignment time.
6. A term that **would** add such base lines **fails closed before any `sale.order`
   or binding is created**, using the existing error class
   **`odoo_validation_configuration`** with the single sub-reason
   **`unsupported_early_payment_discount_payment_term`**.
7. This is **never** routed as `financial_total_mismatch` (it is a configuration
   hold, not a totals defect) and is **not** one of the six §6.0 order-scope gate
   families — it is a **configuration/readiness** hold, analogous to §5.5's
   `unsupported_tax_structure`.
8. **A matched customer's `property_payment_term_id` can never override the
   configured store term** (the importer's explicit assignment wins; fixture 158).

The field is **[Proposed Task 012 decision]** — not implemented in this docs-only
session; it appears in the exact file map (§14), readiness (§5.4), the locked prompt
(packet §15), fixtures (§15), rollback, and definition of done.

---

## 6. MBQ-56 — financial total-check guard: canonical ledger + tax bound (task §7)

The guard is **mandatory, permanent, non-configurable, never silent, never
auto-retried** [Accepted decision — DEC-014 §F, DEC-007 §6, DEC-009]. **REBUILT
2026-07-14 (review `4690680028` items 2 & 3, then review `4691067575` items 2 &
3):** the round-1 formula was internally inconsistent (`shopify_lines_expected`
excluded shipping/tips) and used an invalid `K = distinct tax groups` bound; the
round-2 rebuild fixed both but still constructed each product line from the
**approximate** `discountedUnitPriceSet` and assumed `quantity ×
discountedUnitPriceSet == discountedTotalSet` — which Shopify does **not**
guarantee — and proved the tax bound over an *assumed* common base. This section
now (a) gates out refunded/removed/modified and unsupported-fee/duty/cash-rounding
orders **before** any construction (§6.0), (b) takes the **exact** per-line
pre-tax total from `priceAfterAllDiscountsBeforeTaxesSet` as the financial
invariant (§6.1), (c) requires **exact per-tax-signature base equality** before
any tax-tolerance comparison (§6.4a), and (d) reframes the tax bound as a
**proposed conservative bound with explicit, separately-labelled assumptions**
(§6.5). **§6.0 = six fail-closed eligibility-gate families (order edits, product
refund/removed, shipping refund/removal, additional fees & duties [duty-first],
cash rounding, tip tax treatment);
§6.1 = canonical exact ledger; §6.2 = single Decimal→Odoo boundary + exact Odoo
line representation via the tax engine; §6.3 = tax-inclusive; §6.4 = tolerances;
§6.4a = exact
per-tax-signature base equality; §6.5 = tax-bound assumptions + proof; §6.6 =
worked examples.**

### 6.0 Pre-creation eligibility gates (fail closed, before any SO write)

**[Proposed Task 012 decision]** **Six independent gate families** run on the
header/first-page data **before any Odoo write** (review `4694311215` gate-count
correction). Each unsupported-scope condition is a terminal **policy `skipped`** (no
error class, no partial SO, no binding), never a `financial_total_mismatch`. The
permitted `skip_reason` values are the closed set (§10). The six families are:

1. **order edits** — §6.0.0;
2. **product refund/removal** — §6.0.1;
3. **shipping refund/removal/modification** — §6.0.2;
4. **duties & additional fees (duty-first precedence)** — §6.0.3;
5. **cash rounding** — §6.0.5;
6. **tip tax treatment** — §6.0.6.

**§6.0.4 is NOT a seventh gate** — it is a **clarification pointer** into the
duty-first §6.0.3 gate (the duty branch is evaluated *inside* §6.0.3), retained only
for cross-reference.

#### 6.0.0 Order edits (fail closed) (review `4693694894` item 2)

**Order edits are out of Task 012 MVP scope.** Shopify order editing can change
line quantities, **prices only**, or add/remove lines — and **quantity and total
comparisons alone can miss** a **price-only** edit (unit price changed, quantity
unchanged) or **two offsetting** edits (one line up, another down) that leave the
aggregate `totalPriceSet`/`currentTotalPriceSet` **unchanged**. Relying on §6.0.1's
quantity/total checks is therefore **insufficient**. The order-edit gate is
**fail-closed on the dedicated flag**:

- **`Order.edited` is queried** in `ORDER_HEADER_QUERY` (`Boolean!` [Fact —
  official], §4.1). **Before any Odoo write, require `edited == false`.**
- **`edited == true`** → **no SO, no order binding**, terminal `skipped` with
  `skip_reason = "unsupported_order_edit"` (added to the closed skip set, §10),
  decided from the header data **before any SO write**.
- **Evidence is bounded and non-PII:** only the **order GID**, `edited = true`,
  and `updatedAt`. **No edit history is reconstructed** and no per-edit detail is
  queried.

This gate runs **first** (before §6.0.1), so an edited order is held on the
explicit flag regardless of whether its quantities/totals happen to look
unchanged.

#### 6.0.1 Product refund/removed quantities

Refunds, returns, and removed (order-edited-out) quantities are **out of Task 012
MVP scope**. Because `priceAfterAllDiscountsBeforeTaxesSet` reflects **current**
(net-of-refund/edit) quantity while `discountedTotalSet`, `quantity`, and the
*"before returns"* order totals reflect the **original** order [Fact — official],
mixing them would import a historical quantity against a current-state total:

- **Per-line gate:** for **every** line item, require `currentQuantity ==
  quantity` (*"excluding"* vs *"including refunded and removed units"* [Fact —
  official]). Any line with `currentQuantity != quantity` → **no SO, no binding**.
- **Order-level cross-check (with a fail-closed nullable-`totalTaxSet` rule —
  reviews `4693694894` item 3, `4694311215` item 3):** additionally require
  `money_equal(totalPriceSet, currentTotalPriceSet)` **and** the **price ⇄
  current-price** tax check below. `totalPriceSet`/`currentTotalPriceSet` are
  non-null `MoneyBag!` [Fact — official]; **`totalTaxSet` is nullable** while
  **`currentTotalTaxSet` is non-null** `MoneyBag!` [Fact — official]. The old
  *"`totalTaxSet` null OR equals `currentTotalTaxSet`"* rule **and** the round-7
  *"normalize null to a canonical zero MoneyBag"* rule are **both withdrawn** —
  **Shopify documents `totalTaxSet` as nullable but does NOT document that null
  means zero** [Open question], so the connector must **not** invent zero semantics
  from null (review `4694311215` item 3). Instead:
  - when **`totalTaxSet` is non-null**: require `money_equal(totalTaxSet,
    currentTotalTaxSet)` (§3.1a — currency-code match + parsed-Decimal value; a
    `10.0`/`10.00` formatting difference is equal, an unequal value or currency
    mismatch fails);
  - when **`totalTaxSet` is null**: **create no SO, create no binding — fail
    closed** as `data_shape_schema_mismatch`. **Null is never reinterpreted as
    zero.** Preserve bounded non-PII evidence: the **order GID**, the
    `currentTotalTaxSet` amount/currency, and the **absence of an original
    `totalTaxSet`**. (A **future dev-store validation obligation** — §5.4/§18 — is
    recorded to determine whether Shopify uses null for a specific legitimate
    tax-free case; **only a later accepted decision, backed by official or live
    evidence, may normalize null to zero.**)
  This applies the **same Decimal/currency semantics to both shop and presentment
  money** for the non-null case. It is a belt-and-suspenders catch for any
  refund/edit a per-line check might miss, and **null fails closed** rather than
  bypassing it.
- **Routing:** a failed gate is an **unsupported-scope policy outcome**, not a
  defect: terminal `skipped` with `skip_reason = "refunded_or_removed_quantity"`
  (added to the closed skip set, §10), evaluated from the header/first-page data
  **before any Odoo write**. Preserve **non-PII** evidence explaining the hold —
  per-line `quantity`/`currentQuantity` and the order `total*` vs `currentTotal*`
  pairs (numbers and GIDs only). **No refund reconstruction is attempted**, and
  the historical quantity is **never** imported against a current-state total.
- **No refunded-vs-removed distinction needed:** no LineItem field separates
  refunded from removed units [Fact — official] and the gate does not require the
  distinction — it fails closed on the aggregate `currentQuantity != quantity`.

#### 6.0.2 Shipping refund / removal / modification

Shopify exposes both the original and current per-shipping-line price and a
removal flag [Fact — official]: `ShippingLine.discountedPriceSet` is the
**original/before-refund** post-discount price, `currentDiscountedPriceSet` is the
*"current shipping price after applying refunds, after applying discounts"*, and
`isRemoved` (`Boolean!`) marks a removed line. Refunded/removed/modified shipping
is **out of MVP scope**. Before any SO write, for **every** shipping line require:

- `isRemoved == false`;
- `money_equal(currentDiscountedPriceSet, discountedPriceSet)` in **both**
  `shopMoney` and `presentmentMoney` (the §3.1a **Decimal-numeric** equality —
  currency-code match + parsed-Decimal value equality, no tolerance; `10.0` and
  `10.00` are equal, a currency mismatch is not);
- current shipping evidence **internally consistent** with
  `Order.currentShippingPriceSet` (the sum of current shipping-line pre-tax/net
  values reconciles to the order-level current shipping figure under the same
  tax-inclusion back-out as §6.1-B).

Any mismatch means the order carries refunded, removed, or modified shipping →
terminal `skipped` with `skip_reason = "refunded_or_removed_shipping"` (§10),
**before SO creation**, **never** reaching `financial_total_mismatch` as an
unexplained total defect. Non-PII evidence: per-line `discountedPriceSet` vs
`currentDiscountedPriceSet`, `isRemoved`, and `totalShippingPriceSet` vs
`currentShippingPriceSet` (numbers + shipping-line ids/cursors only).

#### 6.0.3 Unsupported additional fees & duties — deterministic precedence (duty-first)

The canonical ledger (§6.1) is merchandise + shipping + tip + tax **only**; it
does **not** represent Shopify **additional fees** or **duties**. Official Shopify
semantics state additional fees *"can include duties"* [Fact — official], so
`currentTotalAdditionalFeesSet` and `currentTotalDutiesSet` are **not** disjoint
and must **not** be subtracted from one another (no official rule proves they are
directly composable). The gate therefore evaluates a **deterministic, duty-first
precedence** on the **parsed Decimal amounts** (both nullable `MoneyBag`; **null →
zero**; the nonzero test is the §3.1a `is_zero`/nonzero rule — parsed Decimal `!=
0`, never a lexical string test, so `"0.00"` is zero):

1. parse `d = currentTotalDutiesSet` amount; parse `f =
   currentTotalAdditionalFeesSet` amount (both with `decimal.Decimal`, §3.1a);
2. **if `d != 0`** → terminal `skipped` `skip_reason = "unsupported_duties"`
   ([Deferred / non-MVP]); **record whether `f` is also nonzero**, but do **not**
   claim any non-duty portion is known (the composition is not officially
   decomposable);
3. **else if `f != 0`** → terminal `skipped` `skip_reason =
   "unsupported_additional_fees"`;
4. **else** (both zero / present-zero) → **pass**;
5. **both nonzero** is handled by step 2 (duty reason wins) — the operator
   evidence states *duties are present and the remaining fee composition is not
   automatically inferred*.

This makes **`unsupported_duties` reachable for a duty-only order** (the earlier
"any nonzero additional fees first" ordering made it unreachable — review
`4691931971` item 2). Neither is ever `financial_total_mismatch`.

**Aggregate-only, privacy-safe fee evidence (review `4692656343` item 1 —
supersedes round-5's "bounded retained names").** The skip fires **entirely from
the aggregate** `currentTotalAdditionalFeesSet` / `currentTotalDutiesSet`, so
Task 012 MVP **does not query `Order.additionalFees` at all** (§4.1) and there is
**no per-fee payload to redact**:

- **`AdditionalFee.name` is never requested, stored, or logged** — it is
  arbitrary merchant free text (potentially PII); `Order.additionalFees` **does**
  expose list/pagination/filter arguments in 2026-07 (it is not an unbounded
  no-argument field — §4.1), but the MVP still **does not fetch it** purely for
  **data minimization** (no MVP consumer; extra cost/privacy exposure), since the
  aggregate already drives the skip;
- **ordinary job/log messages and technical evidence carry only** the
  `skip_reason`, the **aggregate** fee/duty amount, and the `currency` — no fee
  names, no fee `price` payloads, no fee `taxLines`;
- **`AdditionalFee.id` (`ID!`)** is acknowledged as the stable technical
  identifier a **post-MVP** per-fee feature would use, but the MVP need is fully
  met by the aggregate, so no fee detail (and therefore no
  `ADDITIONAL_FEE_NAME_MAX_LEN` / `ADDITIONAL_FEES_EVIDENCE_LIMIT` retention
  bound) is needed. No raw order/customer payload is persisted.

#### 6.0.4 Unsupported duties — clarification pointer into §6.0.3 (not a separate gate)

**This subsection is a cross-reference, not a seventh gate** (review `4694311215`
gate-count correction): the duty branch is one arm of the **duty-first §6.0.3**
gate family, evaluated inside it. The duty gate is evaluated **first** in §6.0.3
(`d != 0` →
`skip_reason = "unsupported_duties"`, before the additional-fee reason). Routing
is on the **nonzero Decimal amount**, not on the field being non-null — a
present-but-zero `currentTotalDutiesSet` is **not** a hold (correcting the earlier
"non-null → skip"). Evidence: duties amount + currency.

#### 6.0.5 Unsupported cash rounding

`Order.totalCashRoundingAdjustment` is `CashRoundingAdjustment!` (always present)
with `paymentSet`/`refundSet` MoneyBags, each *"0 if there's no rounding, or for
non-cash"* [Fact — official]. The docs establish only that the adjustment applies
to `totalReceived`/`totalRefunded` (payment/refund settlement); **whether a
nonzero adjustment is included in `totalPriceSet`/`currentTotalPriceSet` is
undocumented** [Open question — cannot be proven from official docs]. Until the
relationship is proven representable in Task 012, the gate **fails closed**: a
**nonzero** `paymentSet` **or** `refundSet` (either currency) → **no SO, no
binding**, terminal `skipped` with `skip_reason = "unsupported_cash_rounding"`
(§10) — **never** allowed to surface only as a generic `financial_total_mismatch`.
A zero adjustment (the common case) passes silently. Evidence: the payment/refund
rounding amounts + currency. *[Inference: the adjustment is payment/refund-side,
separate from the order price — evidence: the `paymentSet`/`refundSet`
descriptions target `totalReceived`/`totalRefunded`, and `totalPriceSet` documents
only "taxes and discounts."]*

#### 6.0.6 Unsupported tip tax treatment

**Tip tax treatment is undocumented** in the Admin GraphQL API (no `TipLine`, no
tip `taxLines`) [Fact — official], so importing a tip as untaxed and relying on
the total/tax tolerance is unsafe — a small taxed-tip difference can fall **inside**
the rounding envelope (§6.1-C). MVP: a **nonzero `totalTipReceivedSet`** (either
currency) → **no SO, no binding**, terminal `skipped` with `skip_reason =
"unsupported_tip_tax_treatment"` (§10). `totalTipReceivedSet == 0` proceeds; no
"Shopify Tip" line is ever constructed in MVP. Evidence: tip amount + currency
(no PII). A future separately-accepted store policy may lift this once tip tax
treatment is proven and mapped (§6.1-C).

**Consequence for the ledger:** every order that reaches §6.1 has, on every line,
`currentQuantity == quantity` and unmodified shipping, and carries **no** nonzero
tip, additional fees, duties, or cash rounding — so
`priceAfterAllDiscountsBeforeTaxesSet` (current-net) equals the full original line
total, `T = 0`, the ledger's three active components (merchandise + shipping +
tax) fully account for `totalPriceSet`, and the self-check is exact. This is what
makes the exact per-line construction below sound. `Refund`/order-edit objects are
**not** queried; the current-state fields above are sufficient.

### 6.1 The canonical Shopify source ledger (each component once)

All source arithmetic is `decimal.Decimal` on `shopMoney` amounts (the lossless
Char snapshots), with **no** intermediate rounding until the boundary in §6.2.
Let `r = order_currency.rounding` (Odoo `res.currency.rounding`; `0.01` default;
JPY `1.0`; three-decimal `0.001`; `decimal_places = ceil(log10(1/r))`) [Fact —
official].

**A. Product merchandise net `M` — from the exact line-total field.** For each
line item `i`:
- `source_line_untaxed_exact_i = priceAfterAllDiscountsBeforeTaxesSet_i.shopMoney.amount`
  — *"The total price of the line item… after all discounts are applied and
  excluding refunded and removed quantities. This value doesn't include taxes."*
  [Fact — official]. It is the **exact** per-line net **after all discounts
  (line-level AND order-level/code)**, **before tax**, at **current quantity**
  (equal to `quantity` by the §6.0 gate). It is the financial **invariant** —
  taken as reported, not derived.
- `M = Σ_i source_line_untaxed_exact_i`.

**Why not `discountedUnitPriceSet` or `discountedTotalSet`.** `discountedUnitPriceSet`
is *"the **approximate** unit price"* and *"doesn't include order-level or
code-based discounts"* [Fact — official]; so `quantity × discountedUnitPriceSet`
is **not** guaranteed to equal any exact line total, and it omits order-level
allocations entirely. `discountedTotalSet` *"includes refunded and removed
quantities"* and excludes order-level discounts [Fact — official]; so it is
neither current-quantity nor all-discounts. Only
`priceAfterAllDiscountsBeforeTaxesSet` is simultaneously exact, all-discounts,
pre-tax, and current-quantity. **No order-level `OC` subtraction is performed in
the ledger** — it is already inside the field — so the round-2 double-count risk
in the `OC` classification cannot affect `M`. (`discountedTotalSet`,
`originalTotalSet`, `originalUnitPriceSet`, `discountedUnitPriceSet`, and the
`discountAllocations` are still requested — for the Odoo representation, tax-
signature attribution, and audit, §6.2/§7 — but never as the net-amount source.)

**B. Shipping net `H` — exact, tax backed out only when inclusive.** For each
shipping line `s`:
- `source_shipping_untaxed_exact_s = discountedPriceSet_s.shopMoney.amount −
  (Σ_t shippingLine_s.taxLines[t].priceSet.shopMoney if taxesIncluded else 0)`.
  `discountedPriceSet` is *"the shipping price after applying discounts… If the
  parent order.taxesIncluded field is true, then this price includes taxes… As
  of API version 2024-07… including cart level discounts"* [Fact — official]. So
  when `taxesIncluded=false` it is already **pre-tax**; when `taxesIncluded=true`
  the shipping `TaxLine` amounts are subtracted **exactly once** to reach the
  pre-tax shipping source. The shipping **tax signature** (its `taxLines`) is
  preserved for §6.4a and §7.
- `H = Σ_s source_shipping_untaxed_exact_s`.
- Shipping discounts are **not** re-subtracted (`discountedPriceSet` already nets
  them, including cart-level/free-shipping). Order-level discounts with
  `targetType == SHIPPING_LINE` are already reflected here; they never appear on a
  product line.

**C. Tips `T` — nonzero tips FAIL CLOSED (MVP, review `4691931971` item 6).**
`T = totalTipReceivedSet.shopMoney`. **Tip tax treatment is undocumented in the
Admin GraphQL API** — there is **no `TipLine` object** and no tip-level `taxLines`
[Fact — official]; a Help-Center page states the tip is *"calculated on the cart's
subtotal before taxes and shipping"* but does **not** state tips are tax-exempt.
The round-3/4 posture (import the tip as an **untaxed** line and rely on the total
self-check) is **withdrawn**: a small *taxed*-tip difference can fall **inside**
the permitted `tol_tax`/total rounding envelope and be silently accepted. **New
MVP rule (§6.0.6): a nonzero `totalTipReceivedSet` is a pre-creation fail-closed
policy skip** (`unsupported_tip_tax_treatment`) — **no SO, no binding, no untaxed
"Shopify Tip" line is constructed**. Only `totalTipReceivedSet == 0` proceeds, so
in the ledger **`T = 0` for every imported order**. A future, separately accepted
store policy may support tips only after (i) official or live evidence establishes
their tax treatment, (ii) the correct tax signature is mapped, and (iii) the exact
Odoo representation and total guard are validated. Evidence on skip: tip amount +
currency (no customer PII).

**D. Discounts — attribution, not the net-amount source.** Because `M` and `H`
are taken from exact all-discounts-applied fields, **no ledger term subtracts a
discount**. The `discountAllocations` (`OC` = order-level/code, `targetSelection
== ALL` or `DiscountCodeApplication`) are used only to **attribute** each line's
net to a **tax signature** and to choose the Odoo representation (§7); they do
**not** compute the net amount. No ledger formula depends on the allocation
classification perfectly reconstructing any total — the exact line-total field is
the backstop (review `4691067575` item 2).

**E. Untaxed source expectation `U_ex` — always tax-exclusive, no global
back-out.** `U_ex = M + H + T`, and **`T = 0`** for every imported order (a
nonzero tip is skipped upstream, §6.0.6), so effectively `U_ex = M + H`. Every
term is already **tax-exclusive**: `priceAfterAllDiscountsBeforeTaxesSet` is
pre-tax by definition (both modes) and shipping tax is backed out per-line when
inclusive (part B). **There is no `U_ex = G − totalTaxSet` global back-out** — the
round-2 global subtraction (which the review flagged as not proving identical
per-signature bases) is **withdrawn**; each component is independently pre-tax.
The independent **total** expectation is `Total_ex = U_ex +
totalTaxSet.shopMoney`.

**F. Final total + self-check.** `Total_ex` is compared **independently** to
`totalPriceSet.shopMoney`. A mandatory **ledger self-check** requires `|Total_ex
− totalPriceSet.shopMoney| ≤ tol_total` (§6.4) *before* the order is trusted; a
breach → `financial_total_mismatch`. Because the §6.0 gates guarantee no
refunds/removals/modifications, `totalPriceSet` (*"includes taxes and discounts,
before returns"*) equals `currentTotalPriceSet` for every in-scope order [Fact —
official], and duties/additional-fees/cash-rounding are excluded (a **nonzero**
`currentTotalDutiesSet`/`currentTotalAdditionalFeesSet`/`totalCashRoundingAdjustment`
→ policy skip, §6.0.3–§6.0.5), so this identity holds.

**Odoo construction — see §6.2** (exact per-line representation with residual
adjustments; `quantity × discountedUnitPriceSet` is never assumed equal to any
total).

### 6.2 Exact Odoo line representation through the actual Odoo 19 tax engine (task §7)

**REBUILT 2026-07-14 (review `4691931971` item 5).** The earlier text made five
false claims, now **withdrawn**: (i) "an Odoo Float stores the Decimal residual
exactly" — Odoo money fields are Python **binary `float`** (`sale.order.line.price_unit`
is `fields.Float`, `price_subtotal` is `fields.Monetary`; `res.currency.round`
returns a `float_round` float) [Fact — Odoo 19 source], so a Decimal is **not**
stored exactly; (ii) "currency-rounded base equality proves exact pre-rounding
equality" — it does not (§6.4a); (iii) "`price_include_override` is written on
`sale.order.line`" — it is an **`account.tax`** field, **not** a sale-order-line
field [Fact — Odoo 19 source]; (iv) "a price-included residual is a pre-tax target
subtracted from a gross line amount" — for price-included taxes Odoo backs tax out
**through the tax engine**, not by subtraction; (v) "`tax_delta_bound` is
automatically zero after currency rounding" — only an actual engine calculation
can prove zero (§6.4a).

**Field ownership [Fact — Odoo 19 source].** `account.tax` carries
`price_include_override` (`tax_included`/`tax_excluded`/blank→company default);
`sale.order.line` carries `tax_ids` (M2m `account.tax`), `price_unit`
(`fields.Float`, `min_display_digits='Product Price'` — a **display** hint, **not**
a storage `digits=` grid, so the stored value is an **unrounded binary float**),
`product_uom_qty`, and `discount` (Float, "Discount (%)"). `sale.order.line`
computes `price_subtotal`/`price_total`/`price_tax` via `_compute_amount`
(`sale_order_line.py` L852–862) — `_prepare_base_line_for_taxes_computation()` →
`AccountTax._add_tax_details_in_base_line()` → `AccountTax._round_base_lines_tax_details([base_line])`,
with `price_subtotal = tax_details['total_excluded_currency']` [Fact — Odoo 19
source]. The engine applies the `discount` and, for a price-included tax, **derives
the tax-excluded base internally** (e.g. 121 at 10% incl → excluded base 110).

**Line-level is NOT the acceptance surface (round-9, review `4695589297` item 1).**
`sale.order.line._compute_amount` computes **one line's** `price_subtotal`/`price_tax`.
The **order** figures `amount_untaxed`/`amount_tax`/`amount_total` are computed by
`sale.order._compute_amounts` (`sale_order.py` L512–528) over the **complete batch**
of base lines (all priced lines + any early-payment-discount lines) and can **differ
from the sum of line subtotals** under `round_globally` (the batch aggregates raw
amounts per grouping key, rounds once per key, and distributes the delta —
`_round_tax_details_tax_amounts`, `account_tax.py` L1896–1927). The mandatory guard
therefore reconciles against the **order-level batch result** (§6.2a), never against
summed line-level values. Each line's construction below (A–D) produces the
candidate line; **final acceptance is order-level (§6.2a).**

**Exact per-line representation [Proposed Task 012 decision] (task §6).** For each
eligible product line `i` the target is `source_line_untaxed_exact_i =
priceAfterAllDiscountsBeforeTaxesSet_i` (a **tax-excluded** amount). The importer
uses the **actual mapped `account.tax` records** (§5) whose `price_include_override`
already encodes inclusion — inclusion lives on the tax, never on the SO line.

**A. Candidate line computation (via the engine, not by hand).** Construct the
candidate `sale.order.line` (`price_unit = originalUnitPriceSet_i`,
`product_uom_qty = quantity_i` (`= currentQuantity_i` by §6.0), native `discount`
%, resolved `tax_ids`); run it through the **same engine `sale.order.line` uses**
and read the engine's actual `total_excluded_currency`, `total_included_currency`,
the per-tax breakdown (`base_amount`/`tax_amount` per mapped tax), and the
repartition/group evidence. **No `price_unit × qty × (1−discount)` hand formula is
used as the base** — the engine's `total_excluded_currency` is the base.

**B. Tax-excluded signatures.** Compute the residual from the **engine-returned
excluded base**: `residual = source_line_untaxed_exact_i − engine_total_excluded`.
Add a **quantity-1 adjustment line carrying the same tax signature** (same
`tax_ids`), **recompute through the engine**, and require the resulting engine
excluded base for the (line + residual) to reconcile with the Shopify source
(§6.4a). The residual's own `price_unit` is a `float`; it is chosen so the engine
result reconciles, not assumed to store a Decimal exactly.

**C. Tax-included signatures — seed + finite §6.2b solver, no exact-inversion claim
(reviews `4694311215` item 1, `4695589297` item 3).** **Do not** subtract the pre-tax `PAAD` target from
a gross line amount, **and do not treat `special_mode='total_excluded'` as an exact
inverse.** `special_mode='total_excluded'` is an **analytic computation mode**;
Odoo 19 explicitly warns that **symmetrical accuracy is guaranteed only with an
unrounded `price_unit` and `round_globally`** [Fact — Odoo 19 source, per review
`4694311215`], and `sale.order.line.price_unit` is a **`Float`** [Fact — Odoo 19
source] — so the analytic net→gross path yields a **candidate/seed**, **not proof
of an exactly representable gross `price_unit`**. The construction is therefore:

1. **Seed** — generate an initial gross-residual candidate through the mapped
   leaf-percent Odoo tax engine (the analytic `total_excluded` seed).
2. **Finite, source-supported solver (§6.2b)** — where the seed does not reconcile,
   search the **finite Product-Price-precision candidate grid** in a **bounded
   window** around the seed exactly as specified in **§6.2b** (not an open search
   over "currency-valid" values — `price_unit` has no source-guaranteed storage
   grid, §6.2b).
3. **Recompute through the actual engine** — recompute **every** candidate through
   the real Odoo tax engine using the **store company's actual
   `tax_calculation_rounding_method`**, the **actual `account.tax` records**, the
   **actual inclusion posture** (`price_include_override`), and the **actual
   sale-order-line base preparation** (`_prepare_base_line_for_taxes_computation`).
4. **Read back the engine outputs** — `raw_total_excluded_currency`,
   `total_excluded_currency`, per-tax `raw_base_amount_currency`,
   `raw_tax_amount_currency`, and the final rounded `tax_amount_currency`.
5. **Accept only from actual engine outputs** — never from the analytic seed alone;
   the reconciliation quantities of §6.4a are the **engine-returned** values, and
   **final acceptance is the order-level batch (§6.2a)**.
6. **Fail closed** (`financial_total_mismatch`) when the §6.2b solver **exhausts its
   bounded grid** without a candidate satisfying the base check (§6.4a) **and** the
   order-level tax/total check (§6.2a/§6.4/§6.5). Platform exactness is **never**
   claimed merely because `special_mode` exists.

**D. Post-computation verification (mandatory).** After the engine recomputes the
final (line + attributable residual), require the reconciliation of §6.4a
(quantized excluded-base equality **plus** the recorded actual raw-base delta)
**and** `|engine_total_included − (source_line_untaxed_exact_i + its tax)| ≤` the
§6.4/§6.5 bound. Acceptance is **only** from the actual engine readback (part C
step 5); a line/signature for which no §6.2b grid candidate reconciles →
`financial_total_mismatch`, never absorbed by widening a tolerance.

`quantity × discountedUnitPriceSet` is **never** assumed equal to any target.
Every residual preserves traceability to its **source Shopify line GID, tax
signature, allocation evidence, and exact Decimal amount**. Shipping lines are
represented the same way against `source_shipping_untaxed_exact_s` (with the
shipping tax signature). **No tip line is constructed** (a nonzero tip is skipped
upstream, §6.0.6).

### 6.2a Order-level financial acceptance — the `sale.order._compute_amounts` batch (round-9, review `4695589297` item 1)

**[Proposed Task 012 decision]** The per-line construction of §6.2 produces
**candidate lines only**. Financial acceptance is decided **only after the complete
`sale.order` batch is recomputed** — never from isolated line calculations.

**What the order-level computation actually does [Fact — Odoo 19 source,
`sale_order.py` L512–528].** `sale.order._compute_amounts`
(`@api.depends('order_line.price_subtotal','currency_id','company_id','payment_term_id')`):

1. **gathers every priced order line** — `order._get_priced_lines()`;
2. builds `base_lines = [line._prepare_base_line_for_taxes_computation() for line in
   order_lines]`;
3. **adds any early-payment-discount base lines** —
   `base_lines += order._add_base_lines_for_early_payment_discount()` (§5.6; the MVP
   requires this to return `[]`, else fail closed);
4. **computes and rounds taxes across the complete batch** —
   `AccountTax._add_tax_details_in_base_lines(base_lines, company)` then
   `AccountTax._round_base_lines_tax_details(base_lines, company)` (aggregate raw
   amounts per grouping key → round once per key → distribute the delta across lines);
5. **obtains the tax summary** — `tax_totals =
   AccountTax._get_tax_totals_summary(base_lines, currency, company)`;
6. **assigns** `amount_untaxed = tax_totals['base_amount_currency']`, `amount_tax =
   tax_totals['tax_amount_currency']`, `amount_total = tax_totals['total_amount_currency']`.

**Consequence.** Under `round_globally` (the Odoo-19 default) the order `amount_tax`
is **not** `Σ_i round(line_i tax)` — it is `round(Σ_i raw tax per grouping key)` with
the delta redistributed, so **summed line-level `price_subtotal`/`price_tax` can
differ from the order totals** (`account_tax.py` L1896–1927 worked example: two 23%
lines, `round(33.79)+round(33.79)=67.58` vs order `round(67.57)=67.57`). Isolated
line calculations therefore **cannot** substitute for the final order recomputation.

**Acceptance surface (mandatory).** After constructing **all** candidate lines
(products + shipping + any attributable residual adjustment lines) and setting the
explicitly-configured `payment_term_id` (§5.6), the importer recomputes the **whole
`sale.order`** and compares the Shopify evidence against the **actual order values**:

- `sale.order.amount_untaxed` ↔ `U_ex` (lines bound, §6.4);
- `sale.order.amount_tax` ↔ `totalTaxSet` (tax bound `tol_tax_total`, §6.4/§6.4a/§6.5);
- `sale.order.amount_total` ↔ `totalPriceSet` (total bound, §6.4);

plus the **actual batch tax evidence** generated by that recomputation (the
per-grouping-key `raw_base_amount_currency`/`raw_tax_amount_currency` and rounded
`base_amount_currency`/`tax_amount_currency` from `_round_base_lines_tax_details` /
`_get_tax_totals_summary`) for the §6.4a per-signature check. A line-level candidate
that passed in isolation **is rejected** if the **order-level** recomputation breaches
any bound → `financial_total_mismatch`, rolled back, never absorbed by widening a
tolerance.

**`O` is defined from this order-level computation (round-9 refinement of §6.4).**
Under `round_globally`, `O` = the number of **distinct batch grouping keys** rounded
by `_round_base_lines_tax_details` — the grouping key is `{tax, currency, is_refund,
is_reverse_charge, price_include, computation_key}` [Fact — Odoo 19 source,
`account_tax.py` L1907–1920] — i.e. one rounding event per distinct mapped leaf tax
in the batch (multiple lines sharing a tax collapse to **one** key). Under
`round_per_line`, `O` = the taxed-line × leaf-tax rounding events actually performed
by `_add_tax_details_in_base_line` across the batch. **`O` never counts
invoice/accounting repartition rows** (repartition is an `account.move` concept, not
part of this `sale.order` computation).

### 6.2b Implementation-exact bounded solver contract (round-9, review `4695589297` item 3)

**[Proposed Task 012 decision]** The round-8 phrase "bounded solver over
currency-valid `price_unit` candidates" is **replaced** by the following executable
contract. **Motivation:** `sale.order.line.price_unit` is `fields.Float` with only
`min_display_digits='Product Price'` (a display hint) — Odoo 19 does **not** round
the stored value to any grid [Fact — Odoo 19 source, `sale_order_line.py` L177–181],
so there is **no source-proven finite storage grid** and the candidate grid **must
not** be assumed equal to currency rounding. The contract is therefore a **finite,
deterministic search on the operator-facing Product-Price precision, with fail-closed
narrowing**:

1. **Canonical Decimal source representation** — the target is the exact Decimal
   `source_line_untaxed_exact_i` (from the lossless Char snapshot, §3.1), and the
   order targets are the exact Decimal `U_ex`/`totalTaxSet`/`totalPriceSet`.
2. **Verified `price_unit` precision/grid** — candidates are drawn from the finite
   grid `G = { k · 10^(−p) : k ∈ ℤ }` where **`p = decimal precision of the
   'Product Price' `decimal.precision`** (the operator-facing unit-price precision
   the field references via `min_display_digits`; read at runtime, not hard-coded).
   This is a **deliberate scope restriction**, not a claim that Odoo enforces it.
3. **Decimal→Float conversion boundary** — each grid candidate is a Decimal quantized
   to `p`; it is converted to Python `float` **once**, at the single write boundary
   (§6.2), when assigned to `price_unit`. No Decimal exactness is assumed to survive
   in the stored Float.
4. **Seed generation** — the seed `u₀ ∈ G` is the analytic `special_mode='total_excluded'`
   value (§6.2-C step 1) quantized to `p`.
5. **Candidate ordering** — candidates are enumerated by **non-decreasing absolute
   distance `|u − u₀|`** on `G`.
6. **Positive/negative search sequence** — at each distance `d = m · 10^(−p)`
   (`m = 0,1,2,…`), evaluate `u₀` first (`d=0`), then `u₀ − d` **before** `u₀ + d`
   (a fixed, deterministic order).
7. **Maximum distance from the seed** — `d ≤ D_max = K · 10^(−p)` with a **named,
   small `K`** (proposed default `K = 8`, provisional pending fixtures); the seed's
   analytic proximity makes a small window sufficient for admitted orders.
8. **Maximum candidate count** — at most `2K + 1` candidates per line; the search is
   **finite by construction**.
9. **Deterministic tie-breaker** — if two candidates at the same distance both pass
   (only possible for `u₀ ± d`), the **`u₀ − d` (lower) candidate wins** (fixed rule).
10. **Exact engine functions invoked per candidate** — construct the candidate
    `sale.order.line`, then run the **line** engine (`_prepare_base_line_for_taxes_computation`
    → `_add_tax_details_in_base_line` → `_round_base_lines_tax_details`) to read the
    line evidence, **and then the full-order `_compute_amounts` batch** (§6.2a) for
    acceptance.
11. **Exact raw and rounded outputs read** — per candidate: `raw_base_amount_currency`,
    `raw_tax_amount_currency`, `raw_total_excluded_currency`, `total_excluded_currency`,
    `tax_amount_currency`; and the **order** `amount_untaxed`/`amount_tax`/`amount_total`.
12. **Line-level rejection conditions** — a candidate is discarded (search continues)
    if its line `q(base_src(σ)) ≠ q(base_odoo_raw(σ))` (§6.4a) for the line's signature.
13. **Mandatory full-order recomputation after constructing every line** — a candidate
    that passes the line check is accepted **only** if, with all other lines fixed,
    the **order-level** batch (§6.2a) satisfies every §6.4 bound. The order recompute
    is authoritative.
14. **Behavior when two candidates pass** — the deterministic tie-breaker (9) selects
    one; the result is **not** ambiguous.
15. **Behavior when no candidate passes** — the line, and therefore the order, **fails
    closed** `financial_total_mismatch`; no SO/binding persists.
16. **Bound-exhaustion behavior** — reaching `D_max` without a passing candidate is a
    **fail-closed** outcome (identical to 15), logged with the exhausted `K`, seed,
    and per-candidate order-level deltas (numbers only).
17. **Behavior when a safe finite grid cannot be justified** — if the store's
    'Product Price' precision or currency makes the finite grid unable to represent
    the exact order targets (e.g. a source amount finer than `10^(−p)`), the order
    **fails closed** `financial_total_mismatch` — the MVP is **narrowed** to
    grid-representable orders rather than inventing an unbounded/continuous search.
18. **No grid == currency-rounding assumption** — the contract never claims `G`
    equals `res.currency.round`; `G` is the operator-facing unit-price grid and the
    **order-level engine recomputation** is the sole acceptance authority.

This is a **finite (≤ `2K+1` candidates/line), deterministic, source-supported**
algorithm; where it cannot reconcile, it **fails closed**. It does not invent an
algorithm unsupported by the Float/precision behaviour above.

### 6.3 Tax-inclusive orders (`taxesIncluded = true`) (task §5)

Because the product invariant `priceAfterAllDiscountsBeforeTaxesSet` is **pre-tax
in both modes** [Fact — official], tax-inclusivity affects only two places — **no
global `G − totalTaxSet` back-out is needed**:

- **Shipping source (part B):** `discountedPriceSet` is tax-**inclusive** when
  `taxesIncluded=true` [Fact — official], so `source_shipping_untaxed_exact_s`
  subtracts the shipping `TaxLine.priceSet` amounts **exactly once**; when
  `false`, it subtracts nothing. This is a **source-side** Decimal computation,
  independent of Odoo.
- **Odoo side:** the mapped `account.tax` has `price_include_override =
  'tax_included'` (**on the tax**, not the line), so the **engine** derives the
  tax-excluded base internally (§6.2-C); the importer never subtracts tax on the
  Odoo side by hand. The comparison is **engine `total_excluded` ↔
  `source_*_untaxed_exact`** — like-against-like in both modes, and tax is **never
  removed twice** (source removes shipping tax at most once; the product source
  never carried tax).

The **tax component** (`|amount_tax − totalTaxSet|`) and the **total** are
compared identically in both modes. The only inclusive-mode tolerance change is
the shipping back-out's rounding, carried as the `S_ship` term in the lines
bound (§6.4).

### 6.4 Tolerances — derived from both systems' rounding events

Rounding-event counts:
- **`L`** = number of Odoo SO lines contributing to `amount_untaxed` (product
  lines + shipping lines + any residual adjustment lines; **no tip line** — a
  nonzero tip is skipped, §6.0.6). Odoo rounds each line's `price_subtotal` to `r`
  → each contributes ≤ `0.5r`.
- **`S_ship`** = number of **Shopify shipping** tax events backed out in part B
  when `taxesIncluded=true` (`Σ_s |shipping taxLines_s|`), else `0`. Each is a
  reported `TaxLine.priceSet` rounded to `r` → ≤ `0.5r`.
- **`S`** = number of **Shopify** per-line/per-shipping tax rounding events
  represented by `TaxLine.priceSet`: `S = Σ_i |taxLines_i| + Σ_s |taxLines_s|`.
- **`O`** = number of **Odoo sale-order** tax rounding events in the **complete
  `_compute_amounts` batch** (§6.2a) under the *configured*
  `res.company.tax_calculation_rounding_method` [Fact — official]. **`O` is counted
  from the actual order-level tax computation, NOT from invoice/accounting
  repartition lines** (reviews `4694311215` item 2, `4695589297` item 1): the
  order amounts come from `_get_tax_totals_summary` over the batch (not from summed
  line subtotals), and accounting **repartition lines do not create additional
  sale-order `amount_tax` rounding events** (repartition is an `account.move`
  concept) [Fact — Odoo 19 source]:
  - `round_per_line` → `O = number of final taxed Odoo-line × supported-leaf-tax
    rounding events contributing to the order result` = Σ over the batch's taxed
    lines of (number of applied leaf taxes on that line) (adjustment and shipping
    lines included; tip untaxed contributes 0);
  - `round_globally` (the **Odoo-19 default**) → `O = number of distinct batch
    tax-engine grouping keys rounded` by `_round_base_lines_tax_details`, where the
    grouping key is `{tax, currency, is_refund, is_reverse_charge, price_include,
    computation_key}` [Fact — Odoo 19 source, `account_tax.py` L1907–1920] — so
    **multiple lines sharing a mapped leaf tax collapse to ONE key** (normally one
    event per distinct mapped leaf tax). **`O` is NEVER multiplied by the number of a
    tax's invoice/accounting repartition rows.** Group/compound/base-affecting
    structures are deferred and fail closed (§5.5), so they never contribute to `O`
    in an admitted order — this closure does **not** count group children (round-6
    "group tax counts its children" clause **withdrawn**) and does **not** count
    repartition rows (round-7 "multiple tax repartition lines each round" clause
    **withdrawn**, review `4694311215` item 2).

**Tolerances (no fixed or currency-relative money cap anywhere).** The single
global tax tolerance is **`tol_tax_total = tax_delta_total + 0.5 r (S + O)`**,
where **`tax_delta_total = Σ_σ tax_delta_bound(σ)`** (§6.4a) and each
**`tax_delta_bound(σ) = base_delta(σ) × rate(σ) / 100`** is the **actual
engine-derived** linear leaf-percent tax impact of the recorded raw-base delta
`base_delta(σ) = |base_odoo_raw(σ) − base_src(σ)|` (§6.4a). This term is **not
assumed zero** — the MVP records the actual engine raw base (`raw_base_amount_currency`)
and carries its linear tax delta in the bound (review `4694311215` items 1–2); it is
`0` only when the engine's raw base equals the source base exactly. The linear form
is valid **only because** MVP taxes are **independent leaf percentages** (§5.5) —
it is **never** applied to a deferred group/fixed/division/base-affecting structure.
`tol_tax_total` is used **consistently** everywhere (per-signature, aggregate
`amount_tax`, total, packet, locked prompt, tests, examples); **no document reduces
it to `0.5r(S+O)`** while a nonzero `tax_delta_total` is possible. `tol_lines` is
the lines component below.

| Component | `taxesIncluded=false` | `taxesIncluded=true` |
| --- | --- | --- |
| Lines: `|amount_untaxed − U_ex|` ≤ `tol_lines` = | `0.5 r L` | `0.5 r (L + S_ship)` |
| Taxes: `|amount_tax − totalTaxSet|` ≤ `tol_tax_total` = | `tax_delta_total + 0.5 r (S + O)` | `tax_delta_total + 0.5 r (S + O)` |
| Total: `|amount_total − totalPriceSet|` ≤ | `tol_lines + tol_tax_total` | `tol_lines + tol_tax_total` |

**Lines bound (exact).** `U_ex = M + H + T` is exact `Decimal` when
`taxesIncluded=false` (every term reported pre-tax, no back-out), so
`|amount_untaxed − U_ex| ≤ 0.5 r L`. When `taxesIncluded=true`, only the shipping
back-out introduces reported-tax roundings, so `|amount_untaxed − U_ex| ≤ 0.5 r
(L + S_ship)` — **tighter** than the round-2 `0.5r(L+S)`, because the product
source no longer carries any tax back-out. ∎

**Total bound.** `amount_total = amount_untaxed + amount_tax`, so `|amount_total
− totalPriceSet| ≤ tol_lines + tol_tax_total` (using `totalPriceSet = U_ex +
totalTaxSet`). The `tax_delta_total` term is carried **in full** — it is a real,
engine-derived quantity, generally small (bounded by `Σ_σ 0.5r·rate(σ)/100 < 0.5r`
for admitted leaf-percent orders) and often zero for clean 2-decimal arithmetic,
but **not assumed zero** — so **no document calls `0.5 r (S + O)` the complete tax
tolerance** (reviews `4693694894` item 7, `4694311215` items 1–2). ∎

### 6.4a Per-tax-signature base reconciliation — EXACT quantized equality (mandatory, before any tax tolerance) (task §8)

**[Proposed Task 012 decision — REBUILT 2026-07-14 (review `4691408835` item 4):
exact equality, not a tolerance]** A **global** `amount_untaxed ≈ U_ex` match does
**not** prove the two systems tax the same base per rate — value shifted from a
taxed to an untaxed signature, or between two rates, nets to zero globally while
each signature's base is wrong. And the earlier `|base_src(σ) − base_odoo(σ)| ≤
0.5r(L_σ + S_ship_σ)` **tolerance was mathematically inconsistent** with the §6.5
proof, which assumes both systems round the **same** exact tax `Θ`: a nonzero base
difference means Shopify taxes `base_src` while Odoo taxes `base_odoo`, so
`Θ_Shopify ≠ Θ_Odoo` and the rounding-only proof does not hold. **The tolerance
is withdrawn; §6.4a now requires exact per-signature base equality after a single
currency quantization.**

Define a **tax signature** `σ` = the resolved `account.tax` set for that mapped
Shopify tax (its inclusion posture lives on the tax's `price_include_override`),
keyed by the **hashed evidence fingerprint `shopify_tax_evidence_key` (§5.2a)** —
so two same-rate Shopify taxes with different title/source/liability are
**distinct** signatures —
plus a distinguished **untaxed** signature. Five quantities are tracked
**separately** per `σ` (currency-rounded equality of one does **not** imply
equality of another):

- **`base_src(σ)`** (source target base) = Σ of the exact pre-tax sources
  (`priceAfterAllDiscountsBeforeTaxesSet_i`, `source_shipping_untaxed_exact_s`)
  mapped to `σ`. Each summand is a reported MoneyV2 (or an exact Decimal
  difference of such), so `base_src(σ)` is exact.
- **`base_odoo_raw(σ)`** (**engine raw excluded base**) = Σ of the tax engine's
  **`raw_base_amount_currency`** for `σ` over the candidate lines + attributable
  residuals (§6.2-A/B/C) — the **unrounded** base Odoo's engine actually taxes,
  read back from the actual engine (part C step 4), **not** a hand
  `price_unit×qty×(1−discount)` formula and **not** the displayed `amount_untaxed`
  (a sum of *rounded* subtotals). For a price-included tax the engine has already
  de-grossed to this excluded base.
- **`base_odoo(σ)`** (**engine rounded excluded base**) = Σ of the engine's
  **`total_excluded_currency`** for `σ` — the currency-rounded excluded base, used
  for the quantized display equality below.
- **`base_delta(σ)`** (**actual recorded raw-base delta**) = `abs(base_odoo_raw(σ)
  − base_src(σ))` — the **actual** sub-minor-unit residue the engine carries versus
  the exact source base. It is **recorded**, not assumed zero (review `4694311215`
  items 1–2). Because MVP taxes are **independent leaf percentages** (§5.5), its
  linear tax impact is **`tax_delta_bound(σ) = base_delta(σ) × rate(σ) / 100`**
  (rate as a percentage; e.g. 10% → `× 0.10`). This linear form is valid **only
  because** group/fixed/division/base-affecting structures are already rejected
  (§5.5) — it is **never** used for a deferred complex structure.
- **`sub_display(σ)`** (currency-rounded display subtotal) = Σ of the engine's
  rounded `price_subtotal` for `σ` — reported for audit only, **not** the
  reconciliation quantity.
- **`tax_odoo(σ)`** = the engine's final **rounded `tax_amount_currency`** for `σ`
  (its unrounded `raw_tax_amount_currency` is read back too, part C step 4);
  **`tax_src(σ)`** = Σ `TaxLine.priceSet` for `σ`.

Let **`q(x) = res.currency.round(x)`** (Odoo's real `res_currency.round`, a
`float_round` at precision `r` — returning a **float**, [Fact — Odoo source]).

**Base requirement (mandatory, before any tax tolerance):** for **every** `σ`,

    q(base_src(σ)) == q(base_odoo_raw(σ))       (engine raw excluded base, quantized)

**Any** nonzero quantized difference → `financial_total_mismatch` **immediately**
(a full minor-unit base error is never absorbed). This currency-quantized equality
is **necessary but not by itself a proof of exact pre-rounding equality** —
`q(base_src)==q(base_odoo_raw)` can hold while the raw bases differ sub-minor-unit
(binary `float`). That residue is exactly what `base_delta(σ)` records, and its
linear tax impact `tax_delta_bound(σ)` is **carried in the bound** (below) rather
than assumed zero.

**Achieving reconciliation (via the engine, §6.2).** The residual mechanism adds
a quantity-1 adjustment carrying `σ` and **recomputes through the tax engine**
until the engine's excluded base for `σ` reconciles to `base_src(σ)` within `q(·)`
**and** `delta_engine(σ)` is within the engine's own rounding residue. Because
`price_unit` is a binary `float`, the residual is **not** assumed to store a
Decimal exactly — it is chosen so the **engine result** reconciles, and the
result is **read back from the engine** and re-checked. If **no §6.2b grid
residual** makes the engine reconcile (tax-included/rounded/mixed cases), the
line **fails closed** (§6.2-C/D/§6.2b).

**Tax check — one global formula carrying the actual engine delta (review
`4694311215` items 1–2).** The per-signature check is

    |tax_odoo(σ) − tax_src(σ)| ≤ tax_delta_bound(σ) + 0.5r·S_σ + 0.5r·O_σ

and the aggregate check uses **`tol_tax_total = tax_delta_total + 0.5r(S + O)`**
with **`tax_delta_total = Σ_σ tax_delta_bound(σ)`** (§6.4). The `tax_delta_bound(σ)`
term distinguishes **actual base residue** (`base_delta(σ) × rate(σ)/100`) from
**Shopify rounding** (`0.5r·S_σ`) and **Odoo rounding** (`0.5r·O_σ`). `tax_odoo(σ)`
is the engine's **actual** final rounded `tax_amount_currency` (read back, §6.2-C
step 4) — the comparison is always against the real engine tax result, never an
analytic prediction.

**MVP contract (chosen — and justified): record the actual engine delta; do NOT
claim `delta_engine(σ) = 0`.** The round-7 claim that every admitted leaf-percent
signature proves `delta_engine == 0` (because `special_mode='total_excluded'` is an
exact inverse) is **withdrawn** — Odoo 19 guarantees symmetrical accuracy only with
an unrounded `price_unit` and `round_globally`, and `price_unit` is a `Float`
(§6.2-C, review `4694311215` item 1). The MVP instead requires, for **every**
admitted signature (all independent leaf percentages, §5.5):

1. **currency-quantized base equality** — `q(base_src(σ)) == q(base_odoo_raw(σ))`
   (a full minor-unit base error fails closed);
2. **the actual raw delta recorded** — `base_delta(σ) = |base_odoo_raw(σ) −
   base_src(σ)|`, read from the engine's `raw_base_amount_currency`, stored as
   evidence (never silently discarded);
3. **the actual linear leaf-percent tax delta included in the bound** —
   `tax_delta_bound(σ) = base_delta(σ) × rate(σ)/100`, summed into
   `tax_delta_total` and hence `tol_tax_total`;
4. **the final actual Odoo tax result compared with Shopify evidence** —
   `|tax_odoo(σ) − tax_src(σ)|` against the per-signature bound above, using the
   engine's real `tax_amount_currency`.

A signature for which the §6.2b solver **cannot find any grid
`price_unit` candidate** satisfying (1) and (4), or an unsupported
group/compound/base-affecting structure that §5.5 already holds, **fails closed**
(`financial_total_mismatch`, or the §5.5 `unsupported_tax_structure` hold). The
tolerance is **never widened** beyond the actual engine-derived `tax_delta_bound(σ)`
to absorb a base error. `tax_delta_total` is therefore **generally small but not
assumed zero**; it is `0` only when the engine's raw base equals the source base
exactly (the clean 2-decimal case). *(The linear `base_delta(σ) × rate/100` form is
valid **only** for independent leaf percentages, §5.5 — for any deferred
group/compound/included-multi-repartition structure the delta would be non-linear,
so that path is **not admitted** and fails closed rather than using this formula.)*

Only after every signature satisfies (1)–(3) does the guard compare `amount_tax`
to `totalTaxSet` under §6.5 using `tol_tax_total` (which carries `tax_delta_total`).

### 6.5 Tax-rounding bound — proposed conservative bound with explicit assumptions (task §9)

**[Proposed Task 012 decision — conservative bound, explicit premises]** The tax
tolerance is **`tol_tax_total = tax_delta_total + 0.5 r (S + O)`** (§6.4), where
`tax_delta_total = Σ_σ tax_delta_bound(σ)` is the **actual engine-derived**
raw-base-delta term (§6.4a) — carried **in full**, **not** reduced to `0.5 r (S +
O)` (review `4694311215` items 1–2). It is a **proposed conservative bound**, valid
**only** under the following stated assumptions — it is **not** presented as an
official Shopify guarantee:

1. **Bases reconciled at the engine; actual raw delta bounded** —
   `q(base_src(σ)) == q(base_odoo_raw(σ))` on the **engine raw excluded base** for
   every signature (a **full minor-unit** base error fails closed), **and** the
   actual raw residue `base_delta(σ)` is **recorded** and its linear tax impact
   `tax_delta_bound(σ) = base_delta(σ)×rate(σ)/100` is **carried** in
   `tax_delta_total` (§6.4a). *(Discharged by §6.4a via the actual engine readback;
   **no exact inversion is assumed** — the round-7 zero-delta premise is withdrawn.)*
2. **Rates match** — the mapped Odoo tax's rate equals the Shopify rate for each
   signature (composite-evidence mapping §5.2a + `rate × 100 == ratePercentage`
   cross-check), and the composite key prevents a same-rate/different-tax
   collision. *(Discharged.)*
3. **Shopify-event rounding premise `[Platform-rounding premise — Inference, not
   an official guarantee]`:** each counted Shopify tax event (`TaxLine.priceSet`)
   is a rounding of its exact tax to within `0.5r`. **The Admin GraphQL schema
   does not state Shopify's rounding convention** [Open question], so this premise
   is **labelled separately**, validated by deterministic fixtures, and — for any
   currency/case whose convention is undocumented (e.g. three-decimal currencies)
   — requires **authorized dev-store empirical evidence before onboarding**; the
   importer **fails closed** (holds such a store's orders behind the
   onboarding/empirical prerequisite) until that evidence exists.
4. **Odoo-event rounding** — each counted Odoo event rounds to within `0.5r` via
   `float_round(precision_rounding=r)` [Fact — official].
5. **Complete `O`** — every relevant **sale-order tax-computation** rounding event
   (distinct leaf-tax grouping key, §6.4) is counted in `O`; `O` counts **no**
   invoice/accounting repartition rows (review `4694311215` item 2).

**Conditional proof.** Under 1–5, for each signature `σ` let `Θ_src(σ) =
rate(σ)·base_src(σ)/100` be the exact tax Shopify rounds and `Θ_odoo(σ) =
rate(σ)·base_odoo_raw(σ)/100` the exact tax Odoo's engine rounds (both leaf
percentages, §6.4a). Their exact difference is `|Θ_odoo(σ) − Θ_src(σ)| =
rate(σ)·base_delta(σ)/100 = tax_delta_bound(σ)`. Shopify's `tax_src(σ) = Σ
round_r(·)` over `S_σ` events ⇒ `|tax_src(σ) − Θ_src(σ)| ≤ 0.5r·S_σ` (assumption 3);
Odoo's `tax_odoo(σ) = Σ round_r(·)` over `O_σ` events ⇒ `|tax_odoo(σ) − Θ_odoo(σ)|
≤ 0.5r·O_σ` (assumptions 4–5). Triangle inequality ⇒ `|tax_odoo(σ) − tax_src(σ)| ≤
tax_delta_bound(σ) + 0.5r·S_σ + 0.5r·O_σ`. Summing over signatures ⇒ `|amount_tax −
totalTaxSet| ≤ tax_delta_total + 0.5 r (S + O) = tol_tax_total`. ∎ The bound carries
the **actual** `tax_delta_total`; a **full minor-unit** base mismatch is **not**
admitted (assumption 1 / §6.4a fails it closed), and a deferred non-leaf structure
never uses the linear delta (it fails closed at §5.5). (Conditional on the premises
— not a claim about undocumented platform behaviour, and **not** an exact-inversion
claim.)

The round-1 `K = distinct tax groups` bound is **withdrawn**: it omitted `S`
entirely, so under `round_globally` (Odoo rounds once per group, `O` small) while
Shopify rounds per line (`S` possibly large) it **false-rejects** legitimate
many-small-line orders (Example I). This bound is **not** described as "tight and
correct"; it is the smallest conservative envelope consistent with the labelled
premises.

**Why a conservative `tol_tax_total` does not hide a structural error.** A missing
or mis-priced line shifts a **per-signature base** by a **full minor unit or more**,
caught by §6.4a's quantized base equality and the tight lines component (`0.5 r L`)
**before** `tol_tax_total` is even applied; a wrong **rate** is blocked by §5. What
`tol_tax_total` absorbs is only (a) legitimate per-line-vs-aggregate rounding
divergence (`0.5 r (S+O)`) and (b) the **actual, sub-minor-unit** engine raw-base
residue (`tax_delta_total`, itself bounded by `Σ_σ 0.5r·rate(σ)/100 < 0.5r` for
admitted leaf-percent orders) — never a full base error, which fails closed.

**Properties (task §7/§9):** the tolerance derives only from legitimate rounding
events under labelled premises; **no** arbitrary money cap; the exact line-total
field makes discounts exact by construction; per-signature bases reconcile first;
undocumented-rounding cases fail closed pending dev-store evidence; a mismatch is
never silent and never auto-retried; the formula is mandatory and
non-configurable.

### 6.6 Worked examples (illustration only — not acceptance)

Every example uses the §6.1/§6.2/§6.3 equations verbatim. `PAAD_i` denotes the
exact per-line source `priceAfterAllDiscountsBeforeTaxesSet_i.shopMoney.amount`.
Comparands are the lossless Char `shopMoney` snapshots parsed as `Decimal`; Odoo
figures are read back. All lines pass the §6.0 gate (`currentQuantity ==
quantity`) unless the example states otherwise. **In the clean 2-decimal examples
below the engine's raw excluded base equals the source base exactly
(`base_delta(σ) = 0`), so `tax_delta_bound(σ) = 0`, `tax_delta_total = 0`, and
`tol_tax_total = tax_delta_total + 0.5r(S+O) = 0.5r(S+O)` for those orders; the
shorthand `tol_tax` written below denotes `tol_tax_total`** (§6.4/§6.4a). This is
**not assumed** — it holds because the actual engine `raw_base_amount_currency`
matches (verified by readback, §6.2-C). Where the engine's raw base carries a
sub-minor-unit residue, `tax_delta_bound(σ) = base_delta(σ)×rate(σ)/100` is a real
term **admitted** in `tol_tax_total` (Example Q), and a repartition-heavy tax does
**not** widen the bound (Example R). Only a **full minor-unit** base mismatch, or a
solver that finds **no** §6.2b grid candidate, fails closed (Example L).

**Example A — ordinary 2-decimal (USD, `r = 0.01`), `taxesIncluded=false`, no
discounts.** Line1 `PAAD = 20.00` (8%); Line2 `PAAD = 15.00` (8%); Shipping
`discountedPriceSet = 5.00` (8%, `taxesIncluded=false` → pre-tax, `S_ship=0`).
`M = 20.00 + 15.00 = 35.00`; `H = 5.00`; `T = 0`; `U_ex = 40.00`;
`Total_ex = 40.00 + 3.20 = 43.20 = totalPriceSet` ✓ (self-check). §6.4a: one 8%
signature, `base_src = 40.00 = base_odoo` ✓. Odoo: `amount_untaxed = 40.00`,
`amount_tax = 3.20`, `amount_total = 43.20`. `L = 3`, `tol_lines = 0.015`; lines
`|40−40| = 0` ✓. `S = 3`, `round_globally` `O = 1`, `tol_tax = 0.5·0.01·4 =
0.02`; `|3.20−3.20| = 0` ✓. **PASS.**

**Example B — JPY (`r = 1.0`), `taxesIncluded=false`.** Line `PAAD = 3000` (10%,
qty 3); Shipping 500 (10%). `M = 3000`, `H = 500`, `U_ex = 3500`; `Total_ex =
3500 + 350 = 3850 = totalPriceSet` ✓. §6.4a: 10% signature `base_src = 3500 =
base_odoo` ✓. Odoo untaxed 3500, tax 350. `L = 2`, `tol_lines = 1.0` ✓. `S = 2`,
`O = 1`, `tol_tax = 1.5`; `|350−350| = 0` ✓. **PASS.**

**Example C — BHD (`r = 0.001`), `taxesIncluded=false`.** Line `PAAD = 10.000`
(5%). `M = U_ex = 10.000`; `Total_ex = 10.500` ✓. Odoo untaxed 10.000, tax
0.500. `L = 1`, `tol_lines = 0.0005` ✓. `S = 1`, `O = 1`, `tol_tax = 0.001` ✓.
**PASS.** *Fail-closed note (§6.5 premise 3):* a 12.345 base at 10% = 1.2345 whose
3-dp rounding is **undocumented** on Shopify's side [Open question]; the
`tol_tax` premise for such a currency is **not** assumed — a three-decimal-
currency store is **held (fails closed)** until a **named authorized dev-store
empirical check** confirms Shopify's rounding convention. The guard bounds it;
the onboarding evidence licenses it.

**Example D — high-value order discount, taxable (USD, `r = 0.01`) — exact source,
small residual.** `originalUnitPriceSet = 1000.00` (qty 1, 10%); one order-level
allocation 333.33 (`targetSelection = ALL`) → **`PAAD = 666.67`** (the field is
already net of all discounts). `M = U_ex = 666.67` (**no `OC` subtraction** — it
is inside `PAAD`); `Total_ex = 666.67 + 66.67 = 733.34 = totalPriceSet` ✓. Odoo
(§6.2 strategy): `price_unit = 1000.00`, native `discount % = (1000−666.67)/1000
= 33.333 %` → 2-dp `33.33 %` → subtotal `666.70` (off 0.03 > `0.5r`) → **not
faithful** → exact **−0.03 tax-preserving** residual (inherits 10% + inclusion)
so subtotal + residual `= 666.67 = PAAD` ✓ (verification, §6.2 step 3). Note the
residual is now a **0.03 rounding remainder**, not the whole 333.33 discount.
§6.4a: 10% signature `base_src = 666.67 = base_odoo` ✓. `amount_untaxed = 666.67`,
`amount_tax = 66.67`. `L = 2`, `tol_lines = 0.01` ✓. `S = 1`, `O = 1`, `tol_tax =
0.01`; `|66.67−66.67| = 0` ✓. **PASS.**

**Example E — mixed tax signatures + §6.4a base guard (USD, `r = 0.01`).** Line1
`PAAD = 90.00` (10%), Line2 `PAAD = 45.00` (untaxed), Line3 `PAAD = 185.00`
(20%) — each an exact after-all-discounts net. `M = U_ex = 320.00`; `Total_ex =
320 + 46 = 366 = totalPriceSet` ✓. Odoo (native % faithful): nets 90/45/185.
§6.4a buckets: `10% → base_src 90 = base_odoo 90`; `20% → 185 = 185`; `untaxed →
45 = 45` ✓. `amount_tax = 9.00 + 37.00 = 46.00`. `L = 3`, `tol_lines = 0.015` ✓.
`S = 2`, `O = 2`, `tol_tax = 0.02`; `|46−46| = 0` ✓. **PASS.**
*§6.4a in action (equal global untaxed, wrong per-signature base):* if a **no-tax**
residual of 5.00 were mistakenly placed reducing Line1 (10%) and a +5.00 untaxed
line added, `amount_untaxed` would still be 320 (global match!) but `base_odoo(10%)
= 85 ≠ base_src(10%) = 90` → §6.4a **rejects before the tax tolerance is applied**
(`financial_total_mismatch`). A global check alone would have passed it.

**Example J — approximate unit price ≠ exact line total, code discount (USD,
`r = 0.01`) (task §7).** `originalUnitPriceSet = 4.00`, qty 3 (gross 12.00); an
order-level **code** discount of 2.00 → **`PAAD = 10.00`**. But
`discountedUnitPriceSet = 4.00` (it *"doesn't include order-level or code-based
discounts"* [Fact — official]), so `quantity × discountedUnitPriceSet = 12.00 ≠
PAAD 10.00` — using the approximate unit price would **silently drop the 2.00
code discount**. Correct construction: `M = PAAD = 10.00`; Odoo `price_unit =
4.00`, `discount % = (12−10)/12 = 16.667 %` → 2-dp `16.67 %` → subtotal `9.9996 →
10.00` (faithful within `0.5r`; if it were not, a small residual would close the
`0.00…` remainder). Verify subtotal `= 10.00 = PAAD` ✓. This is the fixture proving
`quantity × discountedUnitPriceSet` is **never** the invariant and that the exact
residual (when needed) reproduces the correct Odoo subtotal. **PASS.**

**Example G — tax-inclusive, ordinary (USD, `r = 0.01`, `taxesIncluded=true`).**
Line 10% included; **`PAAD = 100.00`** (the field is pre-tax in **both** modes,
so **no back-out is needed on the product source**); `TaxLine.priceSet = 10.00`,
`totalTaxSet = 10.00`, `totalPriceSet = 110.00`. `M = U_ex = 100.00`; `Total_ex =
100.00 + 10.00 = 110.00 = totalPriceSet` ✓. Odoo
— the **mapped `account.tax`** has `price_include_override='tax_included'` (on the
tax, not the SO line), `price_unit = originalUnitPriceSet = 110.00 incl`: the
**engine** de-grosses → `total_excluded = price_subtotal = 100.00 = PAAD` ✓,
`tax_amount = 10.00`. §6.4a: 10%-incl signature engine `base_odoo = 100.00 = base_src` ✓. `L = 1`,
`S_ship = 0` → `tol_lines = 0.005`; `|100−100| = 0` ✓. `O = 1`, `tol_tax = 0.01`;
`|10−10| = 0` ✓. **PASS** — tax removed once (by Odoo), the product source never
carried it.

**Example H — tax-inclusive with order discount (USD, `r = 0.01`,
`taxesIncluded=true`).** Line orig incl 110.00 (10% incl); order-level allocation
11.00 incl → net incl 99.00 → **`PAAD = 99.00 / 1.1 = 90.00`** (pre-tax, exact);
`TaxLine.priceSet = 9.00`; `totalTaxSet = 9.00`; `totalPriceSet = 99.00`. `M =
U_ex = 90.00`; `Total_ex = 90 + 9 = 99 = totalPriceSet` ✓. Odoo: `price_unit =
110.00 incl`, `discount % = 11/110 = 10 %` faithful → net incl 99.00 → backed out
`price_subtotal = 90.00 = PAAD` ✓, `amount_tax = 9.00`. §6.4a: `base_src(10%-incl)
= 90 = base_odoo` ✓. `L = 1`, `S_ship = 0`, `tol_lines = 0.005` ✓. `O = 1`,
`tol_tax = 0.01`; ✓. **PASS** — no global `G − totalTaxSet`; tax not removed twice.

**Example I — adversarial many-small-lines, one group, global rounding (USD,
`r = 0.01`, `taxesIncluded=false`) — conditional-bound demonstration.** `n = 40`
lines, each `PAAD = 1.00` at 1.4 % (one signature). Exact per-line tax 0.014.
**Shopify** per line `round_r(0.014) = 0.01` × 40 → `totalTaxSet = 0.40`;
`S = 40`. **Odoo** `round_globally`: 40.00 × 1.4 % = 0.56 → `O = 1`; `amount_tax =
0.56`. `M = U_ex = 40.00`; §6.4a: 1.4% signature `base_src = 40.00 = base_odoo_raw` (raw engine base, `base_delta = 0`)
✓; `L = 40`, `tol_lines = 0.20`; lines `0` ✓. Tax diff `|0.56 − 0.40| = 0.16`.
- **Withdrawn** `tol_tax = 0.5r·K` (`K = 1` group) `= 0.005` → `0.16 ≫ 0.005` →
  **FALSE REJECTION**.
- **Proposed conditional bound** `tol_tax_total = tax_delta_total + 0.5r(S + O) =
  0 + 0.205 = 0.205` (one leaf 1.4 % signature; `base_delta = 0` here — raw engine
  base matches — so `tax_delta_bound = 0`; premises §6.5 hold for USD 2-dp;
  validated by fixture) → `0.16 ≤ 0.205` → **ACCEPTED**.
Drop one line: `amount_untaxed = 39.00` vs `U_ex = 40.00` → `|1.00| ≫ tol_lines
(0.195)` and §6.4a base mismatch → **rejected by the lines/base guard**, not the
tax tolerance. So the conditional `tol_tax` absorbs legitimate rounding while the
missing line is still caught. *(Operators needing Shopify-matching tax may set
`round_per_line`; the guard accepts either and records both totals — §5.)*

**Example F — deliberate missing line (USD, `r = 0.01`, `taxesIncluded=false`).**
Example A with Line2 (`PAAD 15.00`) dropped. `U_ex` (full order) = 40.00; Odoo
`amount_untaxed = 25.00` → `|25 − 40| = 15.00 ≫ tol_lines 0.015` → **LINE fails**;
§6.4a 8% base mismatch; total 27.00 vs 43.20 → **TOTAL fails**. Rolled back,
`financial_total_mismatch`. **Never silent.**

**Example K — refunded/removed line held (task §5, `taxesIncluded=false`).** Order
with Line1 (`quantity = 1, currentQuantity = 1`) and Line2 (`quantity = 2,
currentQuantity = 1` — one unit refunded or removed). §6.0 per-line gate:
`currentQuantity != quantity` on Line2 → the **whole order is skipped** with
`skip_reason = "refunded_or_removed_quantity"` **before any SO/line/binding is
written**; the order-level cross-check independently sees `totalPriceSet
(before returns) ≠ currentTotalPriceSet (after returns)`. Non-PII evidence
(per-line `quantity`/`currentQuantity`, the `total*` vs `currentTotal*` pair, GIDs)
is captured. **No** financial construction is attempted and the historical
quantity is **never** imported against a current-state total. No refunded-vs-
removed distinction is needed. **HELD (policy skip), no SO.**

**Example L — adversarial per-signature base delta, engine-framed (USD, `r =
0.01`, `round_globally`).** One 10% signature, 100 product lines, `base_src(σ) =
100.00` (each line 1.00). Suppose a **defective** representation left each line's
**engine raw excluded base** (`raw_base_amount_currency`, read from the tax engine
— not a hand formula) at `1.004`; each rounded `price_subtotal` displays `1.00`, so the
**displayed** `amount_untaxed = 100.00` looks fine, but the engine taxes the
excluded base it actually carries — under `round_globally`, `Σ 1.004 = 100.40` →
`tax_odoo = round_r(100.40 × 10%) = 10.04` vs `tax_src = 10.00`, diff 0.04.
- **Old §6.4a tolerance** `|base_src − base_odoo| ≤ 0.5r·L_σ = 0.50` plus the
  rounding envelope `0.5r(S+O) = 0.505` **would accept** the 0.04 — masking a
  **base error** as rounding (review `4691408835` item 4).
- **Corrected §6.4a** compares the **engine raw excluded bases**: `q(base_src) =
  100.00` vs `q(base_odoo_raw) = 100.40` → **not equal** (a **full minor-unit**
  base error, `base_delta = 0.40 ≥ r`) → `financial_total_mismatch`, fail closed,
  before any tax tolerance. This is the boundary the round-8 rule enforces: a
  **sub-minor-unit** raw residue (`base_delta < r`) is **admitted** via
  `tax_delta_bound(σ) = base_delta(σ)×rate/100` (Example Q), but a **full
  minor-unit** discrepancy like 0.40 fails the quantized base equality.
For a **supported** order the §6.2b solver recomputes through the actual
engine and reads back `raw_base_amount_currency`; if **no** §6.2b grid
`price_unit` candidate makes `q(base_odoo_raw)` equal `q(base_src)`, the line
**fails closed** (§6.2-C step 6) — acceptance is never assumed from the analytic
`special_mode` seed, and `tax_delta_bound(σ)` is **never** computed as a naive
`rate × base_difference` for a grouped/compound/included tax (review `4694311215`
items 1–2).

**Example Q — admitted sub-minor-unit raw-base delta, price-included (USD, `r =
0.01`, `taxesIncluded=true`, `round_globally`) (review `4694311215` items 1–2).**
One line, 10 % **included**, `price_unit = 100.00` incl. Shopify reports the exact
pre-tax `PAAD = 90.91`, `TaxLine.priceSet = 9.09`, `totalTaxSet = 9.09`,
`totalPriceSet = 100.00`. The Odoo engine de-grosses (§6.2-C) and its readback is
`raw_base_amount_currency = 90.909091` (unrounded), `total_excluded_currency =
90.91` (rounded), `raw_tax_amount_currency = 9.090909`, `tax_amount_currency =
9.09`. §6.4a: `q(base_src) = 90.91 = q(base_odoo_raw)` ✓ (quantized base equality
holds); **`base_delta = |90.909091 − 90.91| = 0.000909`** is **recorded** (a real
sub-cent residue of price-inclusion, **not** assumed zero), so **`tax_delta_bound =
0.000909 × 10/100 ≈ 0.0000909`** is **admitted** in the bound. `S = 1`, `O = 1`
(one leaf tax), `tol_tax_total = tax_delta_total + 0.5r(S+O) = 0.0000909 + 0.01 =
0.0100909`. Tax diff `|9.09 − 9.09| = 0 ≤ tol_tax_total` ✓. **PASS** — with a
**nonzero** `tax_delta_bound` carried honestly (the round-7 "delta ≡ 0" framing
would have mis-described this order). The §6.2b solver's readback confirmed the
engine result; nothing was accepted from the analytic seed alone.

**Example R — one percent tax with multiple invoice repartition rows (USD, `r =
0.01`, `taxesIncluded=false`, `round_globally`) (review `4694311215` item 2).** One
line `PAAD = 100.00` mapped to a **single leaf 10 % percent** `account.tax` whose
accounting configuration splits the tax across **three tax repartition rows**
(e.g. 50 % / 30 % / 20 % to three accounts). `M = U_ex = 100.00`; `Total_ex =
100.00 + 10.00 = 110.00 = totalPriceSet` ✓. §6.4a: one 10 % signature, `base_src =
100.00 = base_odoo_raw`, `base_delta = 0` ✓. Odoo `amount_tax = 10.00` (the
`sale.order.line` tax-details computation rounds the leaf tax **once**, §6.4).
`S = 1`; **`O = 1`** — the distinct global leaf-tax grouping key, **not** 3 — because
`amount_tax` is derived from tax details, **not** from the three invoice repartition
rows. `tol_tax_total = 0 + 0.5·0.01·(1 + 1) = 0.01`; `|10.00 − 10.00| = 0` ✓.
**PASS.** *Contrast (withdrawn round-7 clause):* counting the three repartition rows
would have set `O = 3` → `tol_tax = 0.5·0.01·(1 + 3) = 0.02`, a needlessly loose
bound. **The sale-order tolerance does not grow because accounting distribution has
multiple rows.**

**Example M — shipping refund with unchanged product (task §4).** Product lines
all `currentQuantity == quantity` (product gate §6.0.1 **passes**). Shipping line:
`discountedPriceSet = 10.00`, but `currentDiscountedPriceSet = 4.00` (partial
shipping refund) — or `isRemoved = true`. §6.0.2 shipping gate: `4.00 ≠ 10.00`
(or removed) → the **whole order is skipped** `refunded_or_removed_shipping`
**before any SO write**, even though product quantities are unchanged (§6.0.1
alone would have missed it). `Order.currentShippingPriceSet` independently differs
from the before-refund shipping. **HELD, no SO** — never a `financial_total_mismatch`.

**Example N — nonzero additional fee / duty / cash rounding (task §6/§7).**
(a) `currentTotalAdditionalFeesSet.shopMoney = 3.50` (duties zero) → `skipped`
`unsupported_additional_fees`, evidence **`3.50 USD` (aggregate amount + currency
only — `Order.additionalFees` detail is not queried, so there is no fee name)**.
(b) `currentTotalDutiesSet.shopMoney = 0.00` (present but zero) → **not** skipped,
import proceeds (§6.0.4). (c) `totalCashRoundingAdjustment.paymentSet = −0.02` →
`skipped` `unsupported_cash_rounding` (its relationship to `totalPriceSet` is
undocumented, fail closed). Each is decided **before** SO creation and never
surfaces as a generic total mismatch.

**Example O — order edit, price-only / offsetting (task §5, review `4693694894`
item 2).** `Order.edited = true`. Case (a): a **price-only** edit raised Line1's
unit price but left every `currentQuantity == quantity` and — because a
compensating discount was added — `totalPriceSet == currentTotalPriceSet`. Case
(b): two **offsetting** line edits (one +10.00, one −10.00) leave
`totalPriceSet == currentTotalPriceSet`. In **both** cases the §6.0.1
quantity/total checks would see nothing wrong, but §6.0.0 holds on the flag:
`edited == true` → **whole order skipped** `unsupported_order_edit` **before any SO
write**; evidence = order GID + `edited=true` + `updatedAt` only (no edit-history
reconstruction). **HELD, no SO.**

**Example P — null original `totalTaxSet` fails closed (task §5, reviews
`4693694894` item 3, `4694311215` item 3).** `totalTaxSet = null`;
`currentTotalTaxSet` non-null. Because **Shopify does not document that a null
`totalTaxSet` means zero**, the round-7 canonical-zero construction is **withdrawn**
and **every** null case fails closed the same way. Case (a):
`currentTotalTaxSet.shopMoney = currentTotalTaxSet.presentmentMoney = 0.00` →
**still fails closed** `data_shape_schema_mismatch` (the connector does **not**
assume null == zero even when current tax is zero). Case (b):
`currentTotalTaxSet.shopMoney = 4.00` (nonzero) → **fails closed**
`data_shape_schema_mismatch`. Case (c): `currentTotalTaxSet` currency `EUR` while
the order is `USD` → **fails closed** `data_shape_schema_mismatch`. In **all**
cases: **no SO, no binding**; bounded non-PII evidence = order GID +
`currentTotalTaxSet` amount/currency + **absence of original `totalTaxSet`**. **No
null-to-zero path exists** — a future dev-store validation obligation (§5.4/§18)
may later justify a documented tax-free normalization. **HELD, no SO.**

---

## 7. Discount representation and role (task §8)

**[Fact — official]** `discountedUnitPriceSet` is the *"approximate"* unit price
and *"doesn't include order-level or code-based discounts"*; `discountedTotalSet`
*"includes refunded and removed quantities"* and excludes order-level discounts;
`priceAfterAllDiscountsBeforeTaxesSet` is the exact after-**all**-discounts,
pre-tax, current-quantity line total; `TaxLine.priceSet` is the tax *"after
discounts and before returns"*.

**Role of discount allocations after adopting the exact line-total field
(REBUILT 2026-07-14, review `4691067575` item 2):** the net line amount now comes
from `priceAfterAllDiscountsBeforeTaxesSet` (§6.1-A), **not** from any discount
computation. Discount allocations (`discountAllocations`, with
`discountApplication{__typename targetType targetSelection allocationMethod ...
on DiscountCodeApplication{code}}`) are therefore required for **representation,
audit, and tax-signature attribution** — **no longer the sole source of the
canonical net line amount**, and **no ledger formula depends on the allocation
classification perfectly reconstructing any total**. The **exact line-total field
is the financial backstop**; a signature-base mismatch is caught by §6.4a before
any tolerance is applied. The `OC` = order-level/code partition
(`targetSelection == ALL` **or** `DiscountCodeApplication`) is still computed —
to decide which tax signature a residual belongs to and how the Odoo line is
represented — but never to add/subtract a net amount.

**[Proposed Task 012 decision]** Representation rules (§6.2 is authoritative):

- **The line net is the exact `PAAD_i`**, reproduced in Odoo by
  `originalUnitPriceSet` + native `discount %` when faithful to `0.5r`, else plus
  an **exact per-tax-signature residual adjustment** (§6.2 strategy 2). The
  residual is the difference between the chosen faithful representation and
  `PAAD_i` — a **rounding remainder**, not the whole order-level discount
  (Example D shows a 0.03 residual, not 333.33).
- **`quantity × discountedUnitPriceSet` is never assumed** equal to
  `discountedTotalSet` or to `PAAD_i` (Example J: a code discount makes them
  differ; using the approximate unit price would drop the discount).
- **No double subtraction:** line-level discounts are already inside `PAAD_i`;
  order-level/code allocations are already inside `PAAD_i`; shipping discounts are
  already inside `discountedPriceSet` (§6.1-B) — **nothing is subtracted twice**
  because nothing is subtracted at all in the ledger.
- **Tax inheritance for taxable residuals:** a residual against a **taxable**
  source line **inherits that line's `tax_ids`** (and thereby the mapped
  `account.tax`'s `price_include_override` — inclusion lives on the tax, not the
  SO line) — never a no-tax line for a taxable source — so the engine reduces the
  same taxable base Shopify taxed (Example E).
- **Separate buckets by tax signature:** residuals sharing an identical signature
  (same `tax_ids` + inclusion) may be combined into **one negative line per
  signature/bucket**, per-source-line allocation preserved in evidence.
- **No universal no-tax discount line:** there is never a single universal no-tax
  residual across taxable and untaxed lines (§6.4a would reject the shifted base,
  Example E).
- **Inconsistent allocation → reject:** a residual that cannot be attributed to a
  source line's tax signature → `financial_total_mismatch`, **never** absorbed by
  widening a tolerance.

**Exact rounding / allocation rules:** all math in `decimal.Decimal`; the
faithfulness test uses `float_compare(precision_rounding = r)`; the residual is
the exact Decimal difference to `PAAD_i`; the raw `allocatedAmountSet` values,
each line's chosen representation, and the source GID/tax-signature attribution
are preserved in the evidence payload. Fixtures include: `discountedUnitPriceSet
× quantity ≠ PAAD`; a code discount producing that difference; an allocation
rounding remainder carried by an exact residual; and the residual producing the
correct Odoo subtotal (§15).

---

## 8. Customer and address resolution (task §9)

**[Accepted decision — DEC-014 §C/§E, Task 011]** Email is the **sole automatic
customer match key** beyond an existing binding (RA-006 forbids name/fuzzy
matching — revisit condition unmet); existing partners' own fields are **never**
mutated by import. **An ambiguous or unresolved customer holds the WHOLE job**
(`sale.order.partner_id` is `required=True`, so no partial SO can exist): remote
customer evidence is **collected and validated**, but **no partial `sale.order` and
no order binding is created** (§8.1, round-9 review `4695589297` item 4). This
closure does **not** redesign Task 011B's accepted email-matching policy.

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
[Fact — official], so an unresolved customer cannot yield a partial SO. On any
ambiguous/unresolved customer (path-1 or path-2 `>1`, or path-3 fallback
unconfigured): **collect and validate the remote customer evidence, but create NO
partial `sale.order` and NO order binding**; the job enters
`blocked_manual_review` / sub-reason `ambiguous_match`, carrying the **exact Task
011 §8.2 candidate-evidence JSON** (`{"kind":"customer_ambiguous_match_candidates",
…, "candidates":[…first 20 by partner_id…], "candidate_count": true_total}`) in
`technical_detail`, plus the financial evidence in `payload_snapshot` (evidence
only — **not** a partial SO). **The rest of order import does NOT proceed** while a
customer is held. **After the operator resolves the customer** (creating the
binding) and retries, the **complete order creation runs atomically** (all lines +
totals guard + binding in one savepoint) — nothing is created before resolution.
This **removes** the earlier "the rest of order import proceeds" phrasing.

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
exactly — (1) divergent presentment currency (`skip_reason =
"divergent_presentment_currency"`); (2) **nonzero** `currentTotalDutiesSet`
**amount** (`unsupported_duties`, [Deferred / non-MVP] — evaluated **first** in the
duty/fee precedence, routes on the Decimal amount, **not** on the field being
non-null; a present-but-zero duties MoneyBag is **not** skipped, §6.0.3/§6.0.4);
(3) `test: true` when `order_import_include_test` is
`False` (`test_order_excluded`); (4) order already cancelled at first import
(`order_pre_cancelled`); (5) any line where `currentQuantity != quantity`, or an
order where `totalPriceSet != currentTotalPriceSet` / `totalTaxSet !=
currentTotalTaxSet` (`refunded_or_removed_quantity`, §6.0.1); (6) any shipping
line with `isRemoved == true` or `currentDiscountedPriceSet != discountedPriceSet`
or shipping inconsistent with `currentShippingPriceSet`
(`refunded_or_removed_shipping`, §6.0.2); (7) **nonzero**
`currentTotalAdditionalFeesSet` amount **when duties are zero**
(`unsupported_additional_fees`, §6.0.3 — duty-first precedence);
(8) **nonzero** `totalCashRoundingAdjustment.paymentSet`/`refundSet`
(`unsupported_cash_rounding`, §6.0.5); (9) **nonzero** `totalTipReceivedSet`
(`unsupported_tip_tax_treatment`, §6.0.6); (10) **`Order.edited == true`**
(`unsupported_order_edit`, §6.0.0 — order edits are out of MVP; evaluated
**first**, catching price-only/offsetting edits that quantity/total checks miss).
No other policy skip exists; all ten are decided by the handler from the
header/first-page data **before any Shopify mutation or SO write** (there are none
— the importer is read-only).

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
  lines — enforced by a **source-level guard test** (the §15 `execute_business`
  AST guards + a zero-SO-write assertion on the refresh path; the strongest
  DEC-014 §J protection available pre-UI).
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
| `addons/shopify_connector_sale/models/shopify_connector_order_importer.py` | NEW — importer service + job seams + the **four** query constants (`ORDER_HEADER_QUERY`, `ORDER_LINE_ITEMS_PAGE_QUERY`, `ORDER_SHIPPING_LINES_PAGE_QUERY`, `ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY`) + `REDACTION_EXTENSION` |
| `addons/shopify_connector_sale/models/shopify_connector_sale_order_line.py` | NEW — `shopify_line_item_gid` only |
| `addons/shopify_connector_sale/models/shopify_connector_store_settings.py` | order-policy settings fields (§8/§10; incl. `order_import_confirmation_policy` no-default, `order_import_include_test`, `order_company_id`, `order_pricelist_id`, `order_sales_team_id`, **`order_payment_term_id`** (Many2one `account.payment.term`, no default — §5.6; readiness blocks import while unset, holds `unsupported_early_payment_discount_payment_term` if the term adds EPD base lines), `sale_order_last_import_checkpoint_at` inert) — **no `order_tax_autocreate`** (tax auto-create removed from MVP, §5.2b) |
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
**invoice**, **payment**, or **refund** model/logic; any **custom connector tax
engine** (the standard Odoo 19 `account.tax` engine is authoritative for excluded
base, included total, tax breakdown, group and repartition behaviour — Task 012
adds no tax-calculation engine and no manual tax override); any
**presentment-currency SO** or per-currency pricelist
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
| 13 | taxes included | mapped **`account.tax`** carries `price_include_override='tax_included'` (not the SO line); engine de-grosses; guard passes |
| 14 | taxes excluded | `price_include_override='tax_excluded'`; guard passes |
| 15 | multiple tax rates | each distinct **leaf percent** tax explicitly mapped; one `O` rounding bucket per distinct tax under `round_globally`; guard passes |
| 16 | mixed taxed/untaxed | per-signature residual buckets reconcile; tax component passes |
| 17 | line discounts | baked into `price_unit`; not double-subtracted |
| 18 | order discounts | native % if faithful else exact adjustment line; total exact |
| 19 | high-value discount | faithful-% fails → exact tax-preserving adjustment line; guard passes (Example D) |
| 20 | tax-preserving residual line | residual inherits source `tax_ids`/inclusion; recomputed tax matches `totalTaxSet` |
| 21 | shipping | one SO line per shipping node; its `taxLines` mapped; counted in `L` |
| 22 | nonzero tip fails closed | `totalTipReceivedSet != 0` → `skipped` `unsupported_tip_tax_treatment`; **no SO, no "Shopify Tip" line**; zero tip proceeds (§6.0.6) |
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
| 38 | taxesIncluded=true ordinary | product `PAAD` is pre-tax (no product back-out); mapped **`account.tax`** has `price_include_override='tax_included'`; engine de-grosses; guard passes (Example G) |
| 39 | taxesIncluded=true + order discount | `PAAD` already after discount + pre-tax; residual (if any) inherits inclusion; tax not removed twice (Example H) |
| 40 | many-small-lines global-rounding counterexample | Example I: conditional `tol_tax=0.5r(S+O)` accepts `0.16` divergence; `K=#groups` would false-reject; missing line still caught by lines/§6.4a |
| 41 | multiple taxes on one line | each `TaxLine` = an `S` event; each Odoo tax = an `O` event; guard passes |
| 42 | multiple distinct percent taxes (round_globally buckets) | `O = #distinct mapped leaf percent taxes` under `round_globally` (each its own rounding bucket — **not** Odoo `amount_type='group'` children, which are deferred §5.5); per-bucket reconcile |
| 43 | tax repartition (multi tax-repartition line) | `O` counts the leaf-tax **grouping key once**, **not** each invoice repartition line (`amount_tax` comes from the SO tax-details computation, not repartition rounding — round-7 clause withdrawn, review `4694311215` item 2); tolerance does not grow; guard passes (Example R) |
| 44 | shipping-tax rounding | shipping `taxLines` counted in `S`; shipping tax reconciles |
| 45 | line-level allocation not double-subtracted | line-level discount already inside `priceAfterAllDiscountsBeforeTaxesSet`; never subtracted again; total exact |
| 46 | order-level allocation already in the exact field | `OC` (targetSelection=ALL/code) is inside `priceAfterAllDiscountsBeforeTaxesSet`; used for tax-signature attribution only, never subtracted in the ledger; total exact |
| 47 | shipping discount not double-subtracted | `discountedPriceSet` nets it; shipping allocations not re-subtracted |
| 48 | independent line/shipping/discount pagination | three separate cursor loops; all nodes collected; no first-page dup |
| 49 | one connection advances, other two unchanged | advancing `lineItems` does not re-page/duplicate `shippingLines`/`discountApplications` |
| 50 | repeated `endCursor` (no progress) | cursor-progress check → `data_shape_schema_mismatch`; no infinite loop |
| 51 | duplicate node across pages | node-id dedup → `data_shape_schema_mismatch`; never silently merged |
| 52 | changed `updatedAt` between pages | torn read → `concurrency_race_conflict` (AUTO_RETRY); no SO/binding; lease released |
| 53 | GraphQL requested-cost near/over threshold | `requestedQueryCost`/`actualQueryCost` captured; page size not auto-expanded; live-tuning deferred |
| 54 | ambiguous tax fallback (>1 candidate) | `odoo_validation_configuration` ambiguous hold; first candidate never chosen |
| 55 | tax company mismatch | candidate with `company_id ≠ order_company_id` rejected; hold, not import |
| 56 | exact line total from `priceAfterAllDiscountsBeforeTaxesSet` | product line net = the exact field; `quantity × discountedUnitPriceSet` **never** used as invariant |
| 57 | `discountedUnitPriceSet × quantity ≠ PAAD` (code discount) | approximate-unit-price divergence detected; exact residual reproduces the Odoo subtotal (Example J) |
| 58 | allocation rounding remainder | exact per-tax-signature residual carries the remainder; subtotal + residual == `PAAD` within `0.5r` |
| 59 | fully refunded line (`currentQuantity 0 ≠ quantity`) | order **skipped** `refunded_or_removed_quantity`; no SO/binding; non-PII evidence |
| 60 | partially refunded line (`currentQuantity < quantity`) | order **skipped** `refunded_or_removed_quantity` before any SO write |
| 61 | removed (order-edited-out) line | same fail-closed skip; no refunded-vs-removed distinction required |
| 62 | mixed eligible/ineligible order + order-level cross-check | one ineligible line holds the **whole** order; `totalPriceSet ≠ currentTotalPriceSet` independently triggers the skip; **no partial SO ever written** |
| 63 | per-signature base shift (equal global untaxed) | value shifted taxed→untaxed / rate→rate → §6.4a **rejects before** the tax tolerance; global `amount_untaxed` match is not sufficient (Example E) |
| 64 | shipping tax-inclusive back-out | `taxesIncluded=true` shipping `discountedPriceSet` backs out its `taxLines` once → exact pre-tax shipping source; `S_ship` counted |
| 65 | zero-tip proceeds / nonzero-tip skip | `totalTipReceivedSet == 0` imports normally; nonzero → `unsupported_tip_tax_treatment` (no reliance on the rounding tolerance to hide a taxed tip) |
| 66 | query contains every guard field | AST/schema check: the header query requests `currentTotalPriceSet`, `currentTotalTaxSet`, `currentShippingPriceSet`, `currentTotalAdditionalFeesSet`, `currentTotalDutiesSet`, `totalCashRoundingAdjustment`, **`edited`**, and per-shipping `isRemoved`/`currentDiscountedPriceSet` — no gate references an unqueried field; **the aggregate fee/duty totals are present but `Order.additionalFees` detail is NOT queried** (round-6) |
| 67 | fully refunded shipping | `currentDiscountedPriceSet == 0 ≠ discountedPriceSet` → `skipped` `refunded_or_removed_shipping`; no SO |
| 68 | partially refunded shipping | `currentDiscountedPriceSet < discountedPriceSet` → `skipped` `refunded_or_removed_shipping`; no SO |
| 69 | removed shipping line | `isRemoved == true` → `skipped` `refunded_or_removed_shipping`; no SO |
| 70 | shipping changed, product qty unchanged | product `currentQuantity==quantity` but shipping current/original differs → order still **skipped** (§6.0.1 alone would miss it) |
| 71 | product totals unchanged, shipping evidence differs | `Order.currentShippingPriceSet != totalShippingPriceSet`-consistent → `refunded_or_removed_shipping`; never `financial_total_mismatch` |
| 72 | nullable shipping-line id across pages | `ShippingLine.id` null on a paged node → cursor is the identity; null id never treated as stable GID; no double-accumulation |
| 73 | duplicate shipping edge cursor | repeated edge `cursor` → `data_shape_schema_mismatch` |
| 74 | conflicting duplicate non-null shipping id | same non-null `id`, different node/cursor → `data_shape_schema_mismatch` |
| 75 | null additional-fee total | `currentTotalAdditionalFeesSet == null` → treated as zero; import proceeds |
| 76 | zero additional-fee total | present but `amount == 0` → import proceeds (not skipped) |
| 77 | nonzero non-duty additional fee | aggregate `currentTotalAdditionalFeesSet` nonzero (duties zero) → `skipped` `unsupported_additional_fees`; evidence = reason+aggregate amount+currency only; **no fee name** (detail not queried) |
| 78 | nonzero duty | `currentTotalDutiesSet` amount > 0 → `skipped` `unsupported_duties`; no SO |
| 79 | present-but-zero duties | `currentTotalDutiesSet` non-null but `amount == 0` → **not** skipped; import proceeds |
| 80 | duties included vs excluded | zero/nonzero duty under `taxesIncluded` true and false; routing by amount unaffected by inclusion |
| 81 | zero cash rounding | `paymentSet == refundSet == 0` → import proceeds (common case) |
| 82 | nonzero cash rounding | `paymentSet` or `refundSet` != 0 → `skipped` `unsupported_cash_rounding`; never a generic `financial_total_mismatch` |
| 83 | per-signature base-delta adversarial | base_src(σ) and base_odoo(σ) differ within the old §6.4a allowance but `S`/`O` rounding terms alone are insufficient (base error, not rounding); the old tolerance would wrongly accept; **exact quantized equality (§6.4a) fails closed** (Example L) |
| 84 | all three connections edges/cursor | header first page + all three page queries use `edges{cursor node}` for `lineItems`/`shippingLines`/`discountApplications`; header/page shapes identical; dedup by edge cursor |
| 85 | header/page shape equality | the same connection read in the header first page and a page query yields identical node shape; a node re-appearing across the two is caught by edge-cursor identity |
| 86 | duty-only order reaches duty reason | `currentTotalDutiesSet != 0`, `currentTotalAdditionalFeesSet == d` (fees include the duty) → `unsupported_duties` (duty-first precedence — reachable) |
| 87 | non-duty fee only | duties zero, `currentTotalAdditionalFeesSet != 0` → `unsupported_additional_fees` |
| 88 | duties + additional fees together | both nonzero → `unsupported_duties` (wins), evidence states duties present + composition not inferred; no subtraction |
| 89 | both fee totals present-zero | duties 0 and fees 0 → import proceeds |
| 90 | duty nonzero, additional total null | duty amount routes `unsupported_duties`; null fee total treated as zero |
| 91 | additional total nonzero, duty null | fees route `unsupported_additional_fees`; null duty treated as zero |
| 92 | fee-detail not queried | `Order.additionalFees` absent from all four query constants; the skip fires from the aggregate; no `AdditionalFee.name`/`price`/`taxLines` requested, stored, or logged (evidence = reason+aggregate amount+currency) |
| 93 | two 5% taxes, different titles | distinct `shopify_tax_evidence_key` (title differs) → not collapsed; each maps independently or holds |
| 94 | same title/rate, different source | distinct key (source differs); null source uses the `∅` sentinel, distinct from empty string |
| 95 | channelLiable true/false/null | tri-state key component; null (unknown liability) never equals false |
| 96 | rate-collision under old key | two Shopify tax lines that collided under `(rate, price_include)` now stay distinct under the composite key → correct Odoo tax each |
| 97 | correct total, wrong Odoo tax candidate | a same-rate different-tax candidate is **ambiguous → held**; never silently mapped (right total, wrong account rejected) |
| 98 | tax-excluded residual via engine | engine `total_excluded` drives the residual; qty-1 adjustment recomputed through the engine; base reconciles |
| 99 | tax-included residual via engine | residual gross derived through the mapped engine (`special_mode='total_excluded'` seed + finite §6.2b solver), **not** gross/pre-tax subtraction; engine recompute verifies excluded base + tax |
| 100 | binary-float boundary | a Decimal target not representable exactly as a float is handled via the engine reconcile + `tax_delta_bound`, never assumed stored exactly |
| 101 | sub-minor-unit pre-rounding delta, equal rounded bases | `q(base_src)==q(base_odoo)` but `delta_engine(σ) != 0` → the engine-derived `tax_delta_bound` is applied, not zero |
| 102 | multi-repartition **leaf percent** tax (supported) | a leaf percent tax with multiple invoice tax-repartition rows reconciles via the actual engine; `O` counts the **grouping key once** (round_globally `O=1`), **not** each repartition row; `tax_delta_bound` is the actual raw-base-delta term, never `rate × base_delta` of a full mismatch; guard passes (Example R) |
| 103 | no valid residual solution | inclusive/rounded case where no §6.2b grid residual yields the required excluded base + tax (order-level recompute) → `financial_total_mismatch`, fail closed |
| 104 | same displayed subtotal, different engine base | two candidates with equal rounded `price_subtotal` but different engine `total_excluded` → the engine base (not the display) governs; base error caught |
| 105 | exact engine recomputation success | supported order: engine recompute of (line+residual) reconciles excluded base + tax; guard passes |
| 106 | AdditionalFee.id acknowledged, detail not queried | no `additionalFees` selection in any of the four query constants; `AdditionalFee.id` noted only as the post-MVP identifier; skip still fires from the aggregate (no SO) |
| 107 | aggregate additional-fee skip without names | nonzero aggregate → `unsupported_additional_fees`; evidence carries reason+aggregate amount+currency; **zero fee names** anywhere |
| 108 | no arbitrary free text in logs | `Order.note`/`Order.tags`/`LineItem.customAttributes`/`AdditionalFee.name`/`DiscountCodeApplication.code`/`ShippingLine.code`/`ShippingLine.custom` never appear in any log/evidence (not requested at all); retained `ShippingLine.title` stays out of ordinary technical logs (§13) |
| 109 | full-title hash differs despite equal preview | two long `TaxLine.title`s sharing the same `TAX_TITLE_PREVIEW_MAX_LEN` prefix but differing later → **different** `shopify_tax_evidence_key` (full tuple hashed, not truncated); previews may look alike, keys do not |
| 110 | evidence change → new unmapped fingerprint | a changed `title`/`source`/`channelLiable` yields a **new** hash → treated as a new, unmapped fingerprint → `odoo_validation_configuration` hold until the operator maps it (never silently reused) |
| 111 | same-rate tax requires explicit mapping | unmapped fingerprint with a same-rate existing `account.tax` → **held**; the same-rate tax may be shown as a non-binding operator **suggestion**, but the importer never auto-selects it |
| 112 | no automatic rate fallback | zero mapping rows for a fingerprint → configuration hold; the importer does **not** resolve a tax from rate alone |
| 113 | no tax auto-create | a held order **never** creates an `account.tax`; there is no `order_tax_autocreate` setting/path; resolution only succeeds after the operator adds a mapping |
| 114 | Odoo duplicate-name risk absent | because the importer creates no tax, Odoo 19's tax-name-uniqueness constraint is never exercised by Task 012 (the whole class of collision is out of scope) |
| 115 | Decimal 10.0 vs 10.00 equality | `money_equal("10.0" USD, "10.00" USD)` → **equal** (same currency, parsed-Decimal numeric equality; original strings kept only as evidence) |
| 116 | currency mismatch still fails | `money_equal("10.00" USD, "10.00" EUR)` → **not equal** (currency-code check fails regardless of amount) |
| 117 | minimized fields absent from query | AST/schema check: `note`, `tags`, `sourceName`, line `customAttributes`, line `vendor`, `customer.displayName`, `customer.defaultAddress`, **`DiscountCodeApplication.code`**, **`ShippingLine.code`**, **`ShippingLine.custom`** appear in **none** of the four query constants |
| 118 | order edit — quantity edit | `edited == true` (a quantity edit) → `skipped` `unsupported_order_edit`; **no SO, no binding**; evidence = order GID + `edited=true` + `updatedAt` only (§6.0.0) |
| 119 | order edit — price-only edit | `edited == true` with **quantities unchanged** and a unit-price change → `skipped` `unsupported_order_edit`; the quantity/total checks alone would miss it; no SO/binding |
| 120 | order edit — two offsetting edits, unchanged total | `edited == true` where one line's increase offsets another's decrease so `totalPriceSet == currentTotalPriceSet` → still `skipped` `unsupported_order_edit` (the flag, not the totals, governs); no SO |
| 121 | edited=true while every `currentQuantity == quantity` | the order-edit gate runs **first** and holds on `edited == true` even though no line shows a refund/removal → `unsupported_order_edit`; no SO/binding |
| 122 | null original tax + current zero → FAIL CLOSED | `totalTaxSet` null with `currentTotalTaxSet == 0` → **fail closed** `data_shape_schema_mismatch`; **no SO, no binding** (null is **not** reinterpreted as zero even when current tax is zero — review `4694311215` item 3, §6.0.1) |
| 123 | null original tax + current nonzero → FAIL CLOSED | `totalTaxSet` null with `currentTotalTaxSet != 0` → **fail closed** `data_shape_schema_mismatch`; no SO/binding; evidence = order GID + `currentTotalTaxSet` amount/currency + absence of original `totalTaxSet` |
| 124 | null original tax + currency mismatch → FAIL CLOSED | `totalTaxSet` null (any `currentTotalTaxSet`) → **fail closed** `data_shape_schema_mismatch`; the round-7 canonical-zero construction is **withdrawn**; only a later evidence-backed accepted decision may normalize null→zero (§18) |
| 125 | non-null tax formatting-equivalent | `totalTaxSet "10.0"` vs `currentTotalTaxSet "10.00"` (same currency) → `money_equal` **passes** (parsed-Decimal value); import proceeds |
| 126 | non-null tax unequal values | `totalTaxSet "10.00"` vs `currentTotalTaxSet "9.00"` → `money_equal` fails → `skipped` `refunded_or_removed_quantity` |
| 127 | fingerprint case-sensitive (`GST` vs `gst`) | two tax lines differing only by title case → **different** `shopify_tax_evidence_key` (NFC-only, case preserved — no case-folding) |
| 128 | fingerprint whitespace-sensitive (one vs two spaces) | titles `"State Tax"` vs `"State  Tax"` → **different** keys (whitespace preserved — no collapse) |
| 129 | fingerprint NFC-equivalent Unicode | two NFC-equivalent spellings of the same characters → **same** key (Unicode canonical normalization only) |
| 130 | fingerprint v1 deterministic repeatability | recomputing the same evidence yields the **identical** `v1:<sha256 hex>` key every time (length-prefixed serialization incl. version) |
| 131 | future version cannot collide with v1 | a `v2:` key space (hypothetical) never equals any `v1:` key (version prefix + version-inside-hash both differ); stored `v1:` rows are matched as v1, never silently recomputed |
| 132 | additionalFees list-args factual | the field description records that `Order.additionalFees` **exposes list/pagination/filter arguments** (not "unbounded no-arg"); the MVP still does **not** query it, reason = data minimization (§4.1) |
| 133 | simple exclusive percentage tax | leaf `amount_type='percent'`, `price_include_override='tax_excluded'` mapped → supported; engine `raw_base_amount_currency` == source base → `base_delta=0` → `tax_delta_bound=0` here; guard passes |
| 134 | simple inclusive percentage tax | leaf percent, `price_include_override='tax_included'` → engine de-grosses; a **sub-minor-unit** `base_delta` may be recorded → `tax_delta_bound` admitted in `tol_tax_total` (not assumed zero); guard passes |
| 135 | two independent percentage taxes on one line | two distinct mapped leaf percent taxes both apply → two signatures; each reconciles; guard passes |
| 136 | mapped group tax held | mapping/resolution target `amount_type='group'` → **held** `odoo_validation_configuration`/`unsupported_tax_structure`; no import; no group children counted |
| 137 | fixed tax held | `amount_type='fixed'` → held `unsupported_tax_structure`; no import |
| 138 | division tax held | `amount_type='division'` → held `unsupported_tax_structure`; no import |
| 139 | base-affecting compound structure held | `include_base_amount`/`is_base_affected` or unreconcilable sequence → held `unsupported_tax_structure`; fail closed, never widened tolerance |
| 140 | removed discount/shipping text absent | AST check: `DiscountCodeApplication.code`, `ShippingLine.code`, `ShippingLine.custom` in **none** of the four query constants; `ShippingLine.title` present but bounded and out of logs |
| 141 | global tax-tolerance formula consistency | `tol_tax_total = tax_delta_total + 0.5r(S+O)` with `tax_delta_total = Σ_σ tax_delta_bound(σ)` (actual engine raw-base-delta term, `0` only when the raw base matches exactly) is used **identically** in per-signature, `amount_tax`, and `amount_total` bounds; **no** path reduces it to `0.5r(S+O)` while a nonzero `tax_delta_total` is possible (reviews `4693694894` item 7, `4694311215` items 1–2) |
| 142 | special_mode is a seed, not an exact inverse | no doc/AST claims `special_mode='total_excluded'` is an exact inverse; the design seeds from the analytic mode, runs the bounded solver, **recomputes through the actual engine**, and accepts **only** from readback (`raw_total_excluded_currency`, `total_excluded_currency`, `raw_base_amount_currency`, `raw_tax_amount_currency`, `tax_amount_currency`); no candidate reconciling → **fail closed** (§6.2-C, review `4694311215` item 1) |
| 143 | admitted sub-minor-unit raw-base delta | price-included line where `q(base_src)==q(base_odoo_raw)` but `base_delta = |base_odoo_raw − base_src|` is a sub-cent residue → `tax_delta_bound = base_delta×rate/100` is **admitted** in `tol_tax_total`; guard passes (Example Q) — round-7 "delta≡0" framing rejected |
| 144 | full minor-unit base error fails closed | `q(base_src) != q(base_odoo_raw)` (`base_delta ≥ r`) → `financial_total_mismatch`, before any tax tolerance; never absorbed by widening (Example L) |
| 145 | O from tax details, not repartition rows | one leaf `percent` tax with **three** invoice tax-repartition rows → `round_globally` `O = 1` (distinct leaf-tax grouping key), **not** 3; `tol_tax_total` does **not** grow because accounting distribution has multiple rows (Example R, review `4694311215` item 2) |
| 146 | O under round_per_line | `round_per_line`: `O = number of taxed Odoo-line × applied-leaf-tax pairs`; a 2-line, 1-tax order → `O = 2`; repartition rows never multiply `O` |
| 147 | tax_odoo is the actual engine result | the `amount_tax`/per-signature comparison uses the engine's real `tax_amount_currency` readback (§6.2-C step 4), never an analytic prediction from the seed |
| 148 | six eligibility-gate families | §6.0 enumerates **exactly six** independent gate families (order edits, product refund/removal, shipping, duties & additional fees [duty-first], cash rounding, tip); §6.0.4 is a **pointer** into §6.0.3, not a seventh gate (review `4694311215`) |
| 149 | linear delta never used for deferred structures | a group/fixed/division/base-affecting structure is **held** `unsupported_tax_structure` (§5.5) — the linear `base_delta×rate/100` term is **never** computed for it; the linear form is valid only for independent leaf percentages |
| 150 | line-level cannot substitute for order recompute | acceptance uses `sale.order.amount_untaxed`/`amount_tax`/`amount_total` from `_compute_amounts` (batch), **not** summed line `price_subtotal`/`price_tax`; a case where `round_globally` makes the order `amount_tax` differ from `Σ round(line tax)` is accepted only via the order-level value (§6.2a) |
| 151 | multiple lines sharing a tax validated through the batch | two+ lines with the same mapped leaf tax → **one** `round_globally` grouping key; the guard reconciles `amount_tax` from the batch summary, and `O` counts the key **once** (§6.2a/§6.4) |
| 152 | order-level recompute rejects a line-level candidate | a `price_unit` candidate that passes its **line** §6.4a check but breaks the **order** `amount_tax`/`amount_total` bound after full `_compute_amounts` → **rejected**, search continues / fails closed (§6.2a/§6.2b step 13) |
| 153 | repartition rows do not widen O (order-level) | a supported leaf percent tax with multiple invoice tax-repartition rows keeps `round_globally` `O = 1` at the **order** batch grouping key; tolerance does not grow (§6.2a/§6.4, Example R) |
| 154 | payment term explicitly assigned, never inherited | importer sets `payment_term_id = store.order_payment_term_id`; the compute default `partner_id.property_payment_term_id` is overridden (§5.6) |
| 155 | readiness blocks unset payment term | `order_payment_term_id` unset → **order import blocked at readiness**; no order imported (§5.4/§5.6) |
| 156 | EPD-mixed term fails closed | configured term with `early_discount and early_pay_discount_computation=='mixed' and discount_percentage` → `_add_base_lines_for_early_payment_discount()` would add base lines → **fail closed** `odoo_validation_configuration` / `unsupported_early_payment_discount_payment_term` **before** any SO/binding; **never** `financial_total_mismatch` (§5.6) |
| 157 | non-EPD term imports normally | a plain term (no early discount, or non-'mixed' computation, or zero `discount_percentage`) adds **no** EPD base lines → import proceeds (§5.6) |
| 158 | partner property term cannot override store term | a matched customer whose `property_payment_term_id` is an EPD-mixed term does **not** apply — the importer's explicit `order_payment_term_id` assignment wins; if the **store** term is EPD-mixed it fails closed (§5.6) |
| 159 | solver is finite + deterministic | §6.2b search enumerates ≤ `2K+1` Product-Price-precision candidates by non-decreasing `|u−u₀|`, `u₀−d` before `u₀+d`; two-pass tie → lower candidate; determinate result (§6.2b 5–9/14) |
| 160 | solver: seed passes immediately | seed `u₀` reconciles line + order → accepted at `d=0` (tax-excluded and tax-included cases) (§6.2b) |
| 161 | solver: seed needs adjustment | seed fails, a candidate within `D_max` reconciles the order → accepted; readback from actual engine (§6.2b) |
| 162 | solver: no candidate / bound exhaustion | no candidate within `D_max = K·10^(−p)` reconciles the order → **fail closed** `financial_total_mismatch`, logged with `K`/seed/deltas (§6.2b 15–16) |
| 163 | solver: no safe finite grid | source amount finer than `10^(−p)` (Product-Price precision) cannot be represented on the grid → **fail closed** (narrowed MVP scope, §6.2b 17); grid is **never** assumed equal to currency rounding (§6.2b 18) |
| 164 | solver covers currency shapes | tax-excluded, tax-included, zero-decimal (JPY), three-decimal (BHD) currencies each exercised through §6.2b + order-level acceptance |
| 165 | ambiguous customer creates no partial SO | ambiguous/unresolved customer → remote evidence captured/validated, **no partial `sale.order`, no binding**; job → `blocked_manual_review`; after operator resolution, the complete order creates **atomically** on retry (§8/§8.1) |

Source-level guards (AST) — **REBUILT 2026-07-14 (review `4691067575` item 4;
Task 012 has four query constants and multiple paginated calls, not one
`execute()`):** every header/page Admin GraphQL call is issued through
`execute_business`; **no** generic public `execute()` call is reachable from the
importer; every query **result is consumed inside its `execute_business`
context** (no result escapes the `with` body); **no Odoo business write begins
until all four query phases complete**; a disconnect between pages blocks the
next page; a torn read leaves no SO/binding; **no explicit main-cursor commit**
occurs; **all three connections use the `edges{ cursor node }` shape** (no
`nodes`-only connection read; the header first page and page query for each of
`lineItems`/`shippingLines`/`discountApplications` have identical shape — review
`4691931971` item 1). Plus: zero mutation strings; zero core/product file edits.
Runtime: full three-suite Odoo.sh run green before merge (SRR-06), concurrency
caveat carried verbatim (architecture §5.12).
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
(CORE-R1 already satisfied) — delivered via the **accepted CORE-R2 Slice-2B
integration-staging strategy (PR #158, review `4691064435`)**; the current
unprotected PR #150/#151 heads are **not** directly mergeable. The prompt also
states that **no live Shopify request occurs during implementation or its tests**
(read-only + fixtures). This closure does **not** open the gate.

---

## 17. Adversarial self-critic (task §13/§18) — re-run after each correction round

Strict adversarial review re-run against the review-`4690680028`,
`4691067575`, `4691408835`, `4691931971`, `4692656343`, `4693694894` **and**
`4694311215` vectors; each confirmed problem is corrected. Rows 1–21 = round-2
vectors (updated where later rounds superseded the mechanism); rows 22–30 =
round-3; rows 31–39 = round-4; rows 40–49 = round-5 (review `4691931971`); rows
50–56 = round-6 (review `4692656343`); rows 57–64 = round-7 (review `4693694894`);
rows 65–73 = round-8 (review `4694311215` — special-mode inversion, Float
losslessness, solver recomputation, repartition-widening, null-tax acceptance,
gate-count, linear-delta leakage, stale ancestry, authorization re-check); rows
74–80 = round-9 (review `4695589297` — line-vs-order acceptance, silent EPD payment
term, vague solver, ambiguous-customer partial import, stale prerequisites,
line-attributed order tax, authorization re-check).

| # | Risk | Verdict | Resolution |
| --- | --- | --- | --- |
| 1 | double-counted / omitted shipping / tip / discount | **CONFIRMED → FIXED** | canonical `U_ex = M + H + T` with each component **once**; `M` from exact `priceAfterAllDiscountsBeforeTaxesSet` (no `OC` subtraction); shipping via `discountedPriceSet`; tips once; self-check vs `totalPriceSet` (§6.1) |
| 2 | tax-inclusive gross/net mismatch | **CONFIRMED → FIXED** | product source is pre-tax in both modes (no global back-out); only shipping backs out its `taxLines` once when inclusive; Odoo uses `price_include_override` so `price_subtotal` is tax-excluded (§6.3, Examples G/H) |
| 3 | double-subtracted discounts | **CONFIRMED → FIXED** | nothing is subtracted in the ledger — the exact field is already all-discounts; allocations are attribution-only; proof of no double subtraction (§6.1-A/D, §7) |
| 4 | global-rounding false rejection | **CONFIRMED → FIXED** | `tol_tax_total = tax_delta_total + 0.5r(S+O)` (with `tax_delta_total = Σ_σ tax_delta_bound(σ)` the **actual** engine raw-base-delta term, carried in full) as a **conditional** bound (labelled premises §6.5) proven on quantized-equal per-signature bases (§6.4a); `K=#groups` withdrawn; many-small-lines counterexample (Example I) |
| 5 | tolerance so loose it hides a missing line/base | NOT-A-PROBLEM | the **lines** component (`0.5rL`, tight) **and** §6.4a **exact** per-signature base equality catch merchandise/base shifts before `tol_tax`; a wrong rate is blocked by the canonical-key mapping (§6.4a, §6.5, Examples I/L) |
| 6 | cursor duplication | **CONFIRMED → FIXED** | Option-A separate cursor loops; header first-pages not re-fetched; **edge-cursor** dedup + non-null-id secondary (§4.2a); cursor-progress check (§4.2) |
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
| 22 | approximate unit price causing a financial mismatch | **CONFIRMED → FIXED** | invariant is the exact `priceAfterAllDiscountsBeforeTaxesSet`; `discountedUnitPriceSet` is display-only; `quantity × discountedUnitPriceSet` never assumed = any total (§6.1-A, Example J) |
| 23 | refunded quantity paired with original financial totals | **CONFIRMED → FIXED** | §6.0 fail-closed gate (`currentQuantity == quantity` per line + `totalPriceSet == currentTotalPriceSet`) → policy skip `refunded_or_removed_quantity` before any SO; historical qty never imported against current-state total (§6.0, Example K) |
| 24 | discount remainder lost by unit-price rounding | **CONFIRMED → FIXED** | exact per-tax-signature residual carries the remainder; verify subtotal + residual == `PAAD` within `0.5r` (§6.2, Examples D/J) |
| 25 | taxable residual assigned to the wrong signature | **CONFIRMED → FIXED** | residual inherits source line `tax_ids`+inclusion; unattributable residual → `financial_total_mismatch`; §6.4a re-checks per-signature base (§6.2, §6.4a, §7) |
| 26 | equal global untaxed totals hiding wrong per-rate bases | **CONFIRMED → FIXED** | §6.4a per-tax-signature base reconciliation runs **before** the tax tolerance; a global `amount_untaxed` match alone is explicitly not sufficient (§6.4a, Example E) |
| 27 | tax tolerance absorbing a structural tax-base defect | **CONFIRMED → FIXED** | **full minor-unit** base defects fail at §6.4a/lines **before** `tol_tax_total`; reframed as a conditional bound with labelled premises + fail-closed undocumented-rounding; only a sub-minor-unit engine residue is carried via the actual `tax_delta_total` (§6.4a, §6.5) |
| 28 | stale single-`execute()` / query-contract / platform-rounding claims | **CONFIRMED → FIXED** | four-query Option-A everywhere (no single query/API call); `execute_business` AST guards replace the single-`execute()` guard; platform-rounding premise labelled Inference, not a Shopify guarantee (§4, §6.5, §15) |
| 29 | pagination result escaping `execute_business` | **CONFIRMED → FIXED** | every result consumed inside its `with execute_business` body; no result escapes; no write until all four phases complete; disconnect blocks next page (§15 guards) |
| 30 | unproven "tips are untaxed" claim | **CONFIRMED → FIXED** | tip-tax treatment labelled **Inference** (undocumented in the API, no `TipLine`); total self-check is the fail-closed backstop for a taxed tip (§6.1-C, fixture 65) |
| 31 | gate using an unqueried field | **CONFIRMED → FIXED** | the header query requests `currentTotalPriceSet`/`currentTotalTaxSet`/`currentShippingPriceSet`/`currentTotalAdditionalFeesSet`/`currentTotalDutiesSet`/`totalCashRoundingAdjustment` and per-shipping `isRemoved`/`currentDiscountedPriceSet`; the aggregate fee/duty totals drive the skip so `Order.additionalFees` detail is **not** queried (round-6); fixture 66 asserts no gate references an absent field (§4.1) |
| 32 | refunded shipping imported as original shipping | **CONFIRMED → FIXED** | §6.0.2 requires `currentDiscountedPriceSet == discountedPriceSet` (both currencies) + `isRemoved==false` + consistency with `currentShippingPriceSet` → else `refunded_or_removed_shipping` before SO (Example M) |
| 33 | removed shipping node accumulated | **CONFIRMED → FIXED** | `isRemoved==true` → policy skip; and edge-cursor accumulation (§4.2a) never double-counts a shipping node |
| 34 | nullable shipping id treated as stable | **CONFIRMED → FIXED** | `ShippingLine.id` is nullable [Fact]; edge `cursor` is the mandatory identity, non-null id secondary; null id never a stable GID (§4.2a, fixtures 72–74) |
| 35 | additional fee hidden as total mismatch | **CONFIRMED → FIXED** | nonzero `currentTotalAdditionalFeesSet` → `unsupported_additional_fees` policy skip before SO, bounded non-PII evidence; never `financial_total_mismatch` (§6.0.3) |
| 36 | zero duty incorrectly skipped | **CONFIRMED → FIXED** | duties route on the **nonzero amount**, not on the field being non-null; a present-but-zero duties MoneyBag imports (§6.0.4, fixture 79) |
| 37 | cash rounding omitted | **CONFIRMED → FIXED** | `totalCashRoundingAdjustment` queried; nonzero payment/refund → `unsupported_cash_rounding` fail-closed; inclusion in `totalPriceSet` logged as undocumented/Open (§6.0.5, fixture 82) |
| 38 | tax-base difference absorbed by rounding tolerance | **CONFIRMED → FIXED** | §6.4a requires quantized `q(base_src)==q(base_odoo_raw)` per signature before any rounding bound (a full minor-unit error fails closed); the round-3 `≤0.5r(L+S_ship)` tolerance withdrawn (Example L) |
| 39 | compound/group-tax delta calculated naively | **CONFIRMED → FIXED** | `tax_delta_bound(σ)` is defined via the **actual mapped Odoo tax function**, never `rate × base_difference`, for grouped/compound/included/multi-repartition taxes (§6.4a) |
| 40 | query shape that cannot support the dedup assertions | **CONFIRMED → FIXED** | **all three** connections (lineItems/shippingLines/discountApplications) use `edges{cursor node}` in header + page queries; dedup keys on edge cursor + typed secondary identity (§4.1/§4.2) |
| 41 | duty reason unreachable | **CONFIRMED → FIXED** | duty-first precedence: `d != 0 → unsupported_duties` **before** the additional-fee reason; duty-only order reaches the duty reason (§6.0.3) |
| 42 | merchant free text (`AdditionalFee.name`) leaking to logs | **CONFIRMED → FIXED (hardened round-6)** | round-5 redacted/truncated retained names; **round-6 removes the whole vector** — `Order.additionalFees` is not queried at all, so there is no `name` to leak; the skip fires from the aggregate (§4.1/§6.0.3, fixtures 92/106–108) |
| 43 | same-rate distinct taxes silently collapsed | **CONFIRMED → FIXED (hardened round-6)** | evidence **fingerprint** hashes the **full untruncated** normalized tuple (rate+title+source+channelLiable+inclusion); rate-only key **and** truncated-title key withdrawn; collision → hold (§5.2a) |
| 44 | correct total with wrong Odoo tax/account | **CONFIRMED → FIXED (hardened round-6)** | explicit-mapping-only: a same-rate tax is a non-binding operator **suggestion**, never auto-chosen; unmapped fingerprint holds; one fingerprint can never silently change its Odoo tax (§5.2, fixtures 97/111/112) |
| 45 | price-included residual using the wrong basis | **CONFIRMED → FIXED** | inclusive residual derived **through the mapped tax engine** (`special_mode='total_excluded'` **seed** + bounded solver — **not** an exact-inverse claim), never gross/pre-tax subtraction; engine recompute + readback verifies (§6.2-C) |
| 46 | rounded base equality hiding a tax delta | **CONFIRMED → FIXED** | `q(base_src)==q(base_odoo_raw)` is necessary but not sufficient; the engine-derived `tax_delta_bound(σ) = base_delta(σ)×rate/100` (from the actual `raw_base_amount_currency`) is **recorded and carried**, `0` only when the raw base matches exactly — never assumed (§6.4a) |
| 47 | Odoo Float described as exact Decimal storage | **CONFIRMED → FIXED** | money fields are binary `float`; the residual is chosen so the **engine result** reconciles (read back + re-checked), never assumed to store a Decimal exactly (§6.2) |
| 48 | small taxed tip accepted inside tolerance | **CONFIRMED → FIXED** | nonzero `totalTipReceivedSet` → `unsupported_tip_tax_treatment` fail-closed; no untaxed Tip line; `T=0` in the ledger (§6.0.6/§6.1-C) |
| 49 | accidental implementation authorization | NOT-A-PROBLEM | closure + packet deny gate/code/live-call; prompt unusable-until-gate; SRR-03 OPEN; capability prerequisites unmet (§0/§16/§19) |
| 50 | truncated title collides two long titles in the key | **CONFIRMED → FIXED** | identity hashes the **full** normalized tuple before any truncation; truncation exists only in display-only previews; two long titles sharing a prefix → different keys (§5.2a, fixture 109) |
| 51 | same-rate Odoo tax auto-selected as a whole-evidence match | **CONFIRMED → FIXED** | Odoo `account.tax` has no Shopify source/liability/title; a rate match is a **suggestion only**; explicit mapping required; importer never auto-chooses (§5.2 step 2, fixtures 111/112) |
| 52 | tax auto-create with wrong accounts/repartition or name collision | **CONFIRMED → FIXED** | auto-create **removed from MVP** (default repartition unsafe; same-rate meaning collapse; Odoo tax-name-uniqueness collision); operator creates the tax + mapping + retries (§5.2b, fixtures 113/114) |
| 53 | Odoo duplicate tax-name constraint error during import | **CONFIRMED → FIXED** | no tax is created by the importer, so the uniqueness constraint is never exercised by Task 012 (§5.2b, fixture 114) |
| 54 | arbitrary order text (`note`/`tags`/`customAttributes`) entering logs | **CONFIRMED → FIXED** | data-minimization: those fields (plus `sourceName`/`vendor`/`displayName`/`defaultAddress`) are **removed from every query** — no consumer, so nothing to log (§4.4, fixtures 108/117) |
| 55 | numerically-equal Decimal money values falsely rejected | **CONFIRMED → FIXED** | `money_equal` parses `decimal.Decimal` and compares **values** + currency code; `10.0 == 10.00`; original strings kept only as evidence; no lexical string equality (§3.1a, fixtures 115/116) |
| 56 | custom-tax-engine wording contradicting engine authority | **CONFIRMED → FIXED** | terminology reconciled to *"no custom connector tax engine; the standard Odoo 19 `account.tax` engine is authoritative for excluded base/included total/breakdown/group/repartition"* across all five docs (§14, packet §2) |
| 57 | price-only order edit imported | **CONFIRMED → FIXED** | `Order.edited` queried; `edited==true` → `unsupported_order_edit` **before any SO write**; a unit-price-only edit (quantities/totals unchanged) is caught by the flag, not the totals (§6.0.0, fixtures 118/119) |
| 58 | offsetting edits bypassing total checks | **CONFIRMED → FIXED** | two offsetting edits that net to an unchanged `totalPriceSet` still trip `edited==true` → `unsupported_order_edit`; the gate governs on the flag, not the aggregate total (§6.0.0, fixtures 120/121) |
| 59 | null original tax bypassing current tax | **CONFIRMED → FIXED (re-hardened round-8)** | null `totalTaxSet` **fails closed** `data_shape_schema_mismatch` (no SO/binding); the round-7 canonical-zero-from-null normalization is **withdrawn** because Shopify does not document null==zero (review `4694311215` item 3); evidence = order GID + `currentTotalTaxSet` + absence of original tax (§6.0.1, fixtures 122–126) |
| 60 | case/whitespace fingerprint collision | **CONFIRMED → FIXED** | fingerprint normalization is **NFC only** — case and whitespace preserved (no case-folding, no collapse); `GST`≠`gst`, one space≠two; length-prefixed SHA-256 (§5.2a, fixtures 127–129) |
| 61 | fingerprint algorithm migration ambiguity | **CONFIRMED → FIXED** | `SHOPIFY_TAX_FINGERPRINT_VERSION=1`, fixed SHA-256, deterministic length-prefixed serialization incl. version, output `v1:<hex>`; changing normalization/algorithm requires a new version; old `v1:` rows stay interpretable; no silent recomputation; version spaces cannot collide (§5.2a, fixtures 130/131) |
| 62 | group/compound tax claimed supported but rejected by validation | **CONFIRMED → FIXED** | one MVP contract — **leaf percent only**; `group`/`fixed`/`division`/base-affecting compound **fail closed** (`unsupported_tax_structure`), never counted or claimed supported; group-children `O` clause withdrawn (§5.5/§6.4, fixtures 136–139) |
| 63 | nonzero engine delta omitted from total tolerance | **CONFIRMED → FIXED (re-framed round-8)** | one global `tol_tax_total = Σ_σ tax_delta_bound(σ) + 0.5r(S+O)`, carried **in full**; `tax_delta_total` is the **actual** engine raw-base-delta term (`0` only when the raw base matches exactly), **not** forced to zero; no doc reduces it to `0.5r(S+O)` while a nonzero delta is possible (§6.4/§6.4a/§6.5, Examples Q/L, fixtures 141/143) |
| 64 | arbitrary discount/shipping text queried without a consumer | **CONFIRMED → FIXED** | `DiscountCodeApplication.code`, `ShippingLine.code`, `ShippingLine.custom` **removed** (no MVP consumer); retained `ShippingLine.title` reclassified as bounded merchant free text (SO description only, out of ordinary logs) (§4.1/§4.4/§13, fixtures 108/117/140) |
| 65 | `special_mode='total_excluded'` treated as an exact inverse | **CONFIRMED → FIXED (round-8)** | the exact-inversion claim is **withdrawn** — Odoo 19 guarantees symmetry only with an unrounded `price_unit` + `round_globally`, and `price_unit` is `Float`; `special_mode` is a **seed**, the bounded solver recomputes through the actual engine and accepts only from readback, else fails closed (review `4694311215` item 1; §6.2-C, fixture 142) |
| 66 | Float `price_unit` described as lossless | **CONFIRMED → FIXED (round-8)** | `sale.order.line.price_unit` is `Float` [Fact]; no candidate is accepted as an exact representation — acceptance is only from the engine's actual `raw_base_amount_currency`/`tax_amount_currency` readback, and the sub-minor-unit residue is carried as `tax_delta_bound` (§6.2-C/§6.4a, fixtures 142/143) |
| 67 | solver result accepted without engine recomputation | **CONFIRMED → FIXED (round-8)** | every candidate is recomputed through the real engine (real rounding method, real `account.tax`, real inclusion, real base prep) and read back before acceptance; no analytic-seed shortcut (§6.2-C steps 3–5, fixture 147) |
| 68 | repartition rows widening the SO tax tolerance | **CONFIRMED → FIXED (round-8)** | `O` counts sale-order tax-computation grouping keys, **not** invoice repartition rows; a leaf tax with 3 repartition rows keeps `O=1` under `round_globally` and does not widen `tol_tax_total` (review `4694311215` item 2; §6.4, Example R, fixtures 145/146) |
| 69 | null original tax silently accepted | **CONFIRMED → FIXED (round-8)** | null `totalTaxSet` **fails closed** `data_shape_schema_mismatch` (no null→zero invention); recorded dev-store obligation before any future normalization (review `4694311215` item 3; §6.0.1/§18, fixtures 122–124) |
| 70 | wrong eligibility-gate count (seven vs six) | **CONFIRMED → FIXED (round-8)** | the structure is **six** independent gate families; §6.0.4 is a clarification pointer into duty-first §6.0.3, not a seventh gate; headings/summary/tables/prompt reconciled (review `4694311215`; §6.0, fixture 148) |
| 71 | linear base-delta formula leaking into complex taxes | **CONFIRMED → FIXED (round-8)** | `tax_delta_bound = base_delta×rate/100` is applied **only** to independent leaf percentages; group/fixed/division/base-affecting structures are held `unsupported_tax_structure` and never receive the linear term (§5.5/§6.4a, fixture 149) |
| 72 | stale branch ancestry after PR #160 merged | **CONFIRMED → FIXED (round-8)** | branch base-aligned onto `Shopify-connector` tip `a3fd6cd` with a **normal merge commit** (no rebase/squash/force); five-file net PR scope + full Task-012 history preserved; zero commits behind after merge (review `4694311215` item 4; §0/§0.2) |
| 73 | accidental implementation authorization (re-checked round-8) | NOT-A-PROBLEM | closure + packet still deny gate/code/live-call; prompt unusable-until-gate; SRR-03 OPEN; capability prerequisites unmet; only the five docs changed (§0/§16/§19) |
| 74 | financial acceptance from isolated line computation | **CONFIRMED → FIXED (round-9)** | acceptance is the **order-level `_compute_amounts` batch** (`amount_untaxed`/`amount_tax`/`amount_total` from `_get_tax_totals_summary`), never summed line subtotals; under `round_globally` the two differ (`account_tax.py` L1896–1927); a line candidate is rejected by the order recompute (review `4695589297` item 1; §6.2a, fixtures 150–153) |
| 75 | silently-inherited early-payment-discount payment term altering `amount_tax` | **CONFIRMED → FIXED (round-9)** | importer assigns `payment_term_id` explicitly from `order_payment_term_id`, never the partner default; an EPD-mixed term (which `_add_base_lines_for_early_payment_discount` would expand) **fails closed** `unsupported_early_payment_discount_payment_term` before any SO; readiness blocks an unset term (review `4695589297` item 2; §5.6, fixtures 154–158) |
| 76 | vague "bounded solver over currency-valid candidates" | **CONFIRMED → FIXED (round-9)** | replaced by the finite, deterministic §6.2b contract on the Product-Price-precision grid (`price_unit` is an unrounded `Float`; no grid==currency-rounding assumption); ≤`2K+1` candidates, deterministic order/tie-break, full-order recompute per candidate, **fail closed** on exhaustion / no-safe-grid (review `4695589297` item 3; §6.2b, fixtures 159–164) |
| 77 | ambiguous customer yielding a partial import | **CONFIRMED → FIXED (round-9)** | ambiguous/unresolved customer → evidence captured/validated, **no partial SO, no binding**; job → `blocked_manual_review`; after operator resolution the whole order creates **atomically** on retry; the "rest of order import proceeds" phrasing removed (review `4695589297` item 4; §8/§8.1, fixture 165) |
| 78 | stale PR-based prerequisites ("Task 010/011 merged") | **CONFIRMED → FIXED (round-9)** | prerequisites are **capability-based** (SRR-03 closed; protected product/customer import + bindings + indexed matching present on `Shopify-connector`; no unguarded product/customer calls; delivered via the accepted CORE-R2 Slice-2B strategy) across all five docs; no direct-merge PR prerequisite remains (review `4695589297` item 4; §0.1) |
| 79 | order `amount_tax` attributed to `sale.order.line._compute_amount` | **CONFIRMED → FIXED (round-9)** | every statement attributing the **order** `amount_tax` to the line-level compute is corrected: line `_compute_amount` sets one line's `price_subtotal`/`price_tax`; the order `amount_tax` is from `_compute_amounts`/`_get_tax_totals_summary` (§6.2a) |
| 80 | accidental implementation authorization (re-checked round-9) | NOT-A-PROBLEM | closure + packet still deny gate/code/live-call; `order_payment_term_id`/solver are `[Proposed Task 012 decision]`, not implemented; SRR-03 OPEN; capability prerequisites unmet; only the five docs changed (§0/§16/§19) |

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

These capabilities arrive via the **accepted CORE-R2 Slice-2B integration-staging
strategy (PR #158, review `4691064435`)** — the current unprotected PR #150/#151
heads are **not** directly mergeable; they are subsumed by the one controlled
integration PR (§0.1). **CORE-R1 is already merged (satisfied, not pending).**

**Open questions (logged, not resolved):**
- Verbatim GraphQL `THROTTLED` error-code string (docs show only `200 Throttled`).
- Shopify three-decimal-currency storage/rounding policy (undocumented) → the
  `tol_tax_total` platform-rounding premise (§6.5) **fails closed** for such a store
  until a named authorized dev-store empirical check confirms the convention.
- **Advanced Odoo tax structures** (`amount_type ∈ {group, fixed, division}`,
  base-affecting compound) are **[Deferred / non-MVP]** — the MVP supports only
  explicitly-mapped **leaf percent** sale taxes and **fails closed**
  (`unsupported_tax_structure`) on the rest (§5.5). Admitting any of them (and the
  **non-linear** engine `tax_delta_bound(σ)` a complex structure would require —
  the MVP's linear `base_delta×rate/100` term applies only to leaf percentages) is
  a **separately-accepted post-MVP scope**, not opened here.
- **`special_mode='total_excluded'` symmetry is conditional** — Odoo 19 guarantees
  symmetrical net→gross accuracy **only** with an unrounded `price_unit` and
  `round_globally`; with a `Float` `price_unit` it is a candidate/seed, so the MVP
  recomputes through the actual engine and reads back
  `raw_base_amount_currency`/`tax_amount_currency`, failing closed if no candidate
  reconciles (review `4694311215` item 1; §6.2-C). Any future reliance on the
  analytic mode as an exact inverse is **out of scope** and would need engine-level
  evidence.
- **Order-level acceptance is authoritative [round-9]** — financial acceptance uses
  the actual `sale.order._compute_amounts` batch (`amount_untaxed`/`amount_tax`/
  `amount_total` from `_get_tax_totals_summary`), **not** summed line subtotals
  (§6.2a). The isolated-iteration bound `K` for the §6.2b solver and the exact
  order-level reconciliation on real many-line `round_globally` orders are
  **build-time fixtures**, validated before onboarding.
- **`price_unit` has no source-guaranteed finite grid [round-9]** — it is
  `fields.Float(min_display_digits='Product Price')`; the §6.2b solver **restricts**
  candidates to the operator-facing Product-Price precision grid and **fails closed**
  (narrowed MVP scope) when an order cannot be represented on it — the grid is
  **never** assumed equal to currency rounding (review `4695589297` item 3). Whether
  the default `K`/precision suffices for a given store is a dev-store confirmation.
- **Payment-term posture [round-9]** — the MVP requires an explicit store
  `order_payment_term_id` that produces **no** early-payment-discount base lines
  (`_add_base_lines_for_early_payment_discount`); an EPD-mixed term fails closed
  (`unsupported_early_payment_discount_payment_term`, §5.6). Supporting EPD terms
  (representing the discounted-base tax) is deferred post-MVP.
- **Nullable `totalTaxSet` semantics** — Shopify documents `totalTaxSet` as nullable
  but **not** that null means zero. The MVP **fails closed** on null
  (`data_shape_schema_mismatch`, §6.0.1). A **dev-store validation obligation** is
  recorded to determine whether Shopify emits null for a specific legitimate
  tax-free case; **only a later accepted decision backed by official or live
  evidence may normalize null→zero** (review `4694311215` item 3).
- **Order edits** are **[Deferred / non-MVP]** — `edited == true` fails closed
  (`unsupported_order_edit`, §6.0.0). Representing edited orders (edit history
  reconstruction) is future scope, not attempted here.
- The exact byte-serialization details of the versioned tax fingerprint
  (delimiter/length-prefix encoding of `v1`) are pinned to
  `SHOPIFY_TAX_FINGERPRINT_VERSION = 1` (§5.2a); a future normalization/algorithm
  change is a **versioned migration** (`v2:`), logged so the contract is explicit.
- **Tip tax treatment is undocumented in the Admin GraphQL API** (no `TipLine`);
  "tips are untaxed" is an **[Inference]** backstopped by the total self-check
  (§6.1-C) — a dev-store check with a taxed-tip configuration (if one exists)
  confirms the posture before onboarding such a store.
- **No LineItem field distinguishes refunded from removed units** [Fact —
  official] — not needed (the §6.0 gate fails closed on the aggregate), but logged
  so the fail-closed rationale is explicit.
- Empirical confirmation of the per-tax-signature base reconciliation (§6.4a) and
  the `OC` attribution on a real mixed line-level + order-level + code discount
  order → named dev-store check before a discount-heavy store.
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
