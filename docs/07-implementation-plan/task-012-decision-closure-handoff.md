# Task 012 — Order-Import Decision-Closure Handoff

> **Docs-only session handoff.** No gate opened, no code written, no live
> Shopify request. Produced by the Task 012 final pre-implementation
> decision-closure session, 2026-07-14. Follows
> [`session-handoff-template.md`](../06-prompts/session-handoff-template.md).
> The canonical `docs/01-research/research-handoff.md` top entry is a
> control-room action and is **not** modified here (that file is outside this
> session's allowed-files list).

## 0-g. Round-8 correction — 2026-07-14 (control-room review `4694311215`)

An eighth REVISE (docs-only, same five files; PR #159 stays draft/unmerged). After
the content correction the branch was **base-aligned onto the current
`Shopify-connector` tip `a3fd6cd`** (PR #160 merged) with a **normal merge commit**
(no rebase/squash/force-push), preserving the full five-file Task-012 history plus
PR #160/Slice-2B history; the branch is **zero commits behind** `Shopify-connector`
after the merge.

1. **Tax-engine contract honesty** — the claim that `special_mode='total_excluded'`
   is an **exact inverse** for every price-included percentage tax is **withdrawn**.
   Odoo 19 guarantees symmetrical accuracy **only** with an unrounded `price_unit`
   and `round_globally`, and `sale.order.line.price_unit` is a **`Float`**, so
   `special_mode` gives a **candidate/seed, not proof**. The design: seed →
   **deterministic bounded solver** over currency-valid `price_unit` values →
   **recompute through the actual engine** (real rounding method, real `account.tax`,
   real inclusion, real base prep) → **read back** `raw_total_excluded_currency` /
   `total_excluded_currency` / `raw_base_amount_currency` / `raw_tax_amount_currency`
   / `tax_amount_currency` → **accept only from engine outputs**, else **fail closed**.
   (closure §6.2-C; packet D-012-2)
2. **Actual raw-base delta** — the MVP no longer claims `delta_engine == 0`. It
   requires quantized base equality `q(base_src(σ)) == q(base_odoo_raw(σ))` (a full
   minor-unit error fails closed), **records** the actual `base_delta(σ) =
   |base_odoo_raw(σ) − base_src(σ)|`, and carries its **linear** leaf-percent tax
   term `tax_delta_bound(σ) = base_delta(σ) × rate/100` in the bound.
   `tax_delta_total = Σ_σ tax_delta_bound(σ)` and `tol_tax_total = tax_delta_total +
   0.5r(S+O)` are used **consistently** — never reduced to `0.5r(S+O)` while a
   nonzero delta is possible; the linear form is **never** applied to a deferred
   complex structure. (closure §6.4/§6.4a/§6.5; packet D-012-2; Examples Q/L)
3. **`O` rounding-event count corrected** — repartition-line counting is **removed**.
   `sale.order.line._compute_amount` derives `amount_tax` from the engine's tax
   details, not from invoice/accounting repartition rounding, so `round_per_line`
   `O =` taxed-line × leaf-tax pairs and `round_globally` `O =` distinct global
   leaf-tax grouping keys whose tax is rounded — **never** multiplied by invoice
   repartition rows. (closure §6.4; packet D-012-2; Example R)
4. **Nullable `totalTaxSet` fails closed** — the round-7 canonical-zero-from-null
   construction is **withdrawn**; Shopify documents `totalTaxSet` as nullable but
   **not** that null means zero, so a **null** original tax → **no SO, no binding**,
   fail closed `data_shape_schema_mismatch` (evidence = order GID + `currentTotalTaxSet`
   + absence of original tax). A future dev-store obligation is recorded; only a later
   evidence-backed accepted decision may normalize null→zero. (closure §6.0.1; packet
   D-012-2; Example P)
5. **Six eligibility-gate families** — the structure is **six** (order edits, product
   refund/removal, shipping, duties & additional fees [duty-first], cash rounding,
   tip); §6.0.4 is a **clarification pointer** into the duty-first §6.0.3 gate, **not**
   a seventh gate. (closure §6.0; packet D-012-2)

Fixtures 122–124/133/134/141 updated + **142–149** added; §17 adversarial rows
57/59/63 re-framed + **65–73** added (special-mode inversion, Float losslessness,
solver recomputation, repartition-widening, null-tax acceptance, gate-count,
linear-delta leakage, stale ancestry, authorization re-check). Examples Q (admitted
sub-minor-unit raw-base delta) and R (repartition rows don't widen `O`) added; P
(null tax) and L (base-delta) re-framed.

## 0-f. Round-7 correction — 2026-07-14 (control-room review `4693694894`)

A seventh REVISE (docs-only, same five files; PR #159 stays draft/unmerged). Note:
`Shopify-connector` advanced to `a3fd6cd` because **PR #160 (CORE-R2 Slice 2A)
merged** (review `4693862195`); the branch's merge-base is still exactly `1494b97`,
GitHub reports `mergeable_state: clean`, and the round-7 correction is **not rebased**
(it starts from the required head `8f33b8e` on the `1494b97` merge-base).

1. **AdditionalFee factual correction** — `Order.additionalFees` in 2026-07 **does
   expose list/pagination/filter arguments**; the round-6 "unbounded no-arg plain
   list" phrasing is **withdrawn**. The MVP still does not query it, but the reason
   is **data minimization** (no MVP consumer; extra cost/privacy), not unboundedness.
   (closure §2/§4.1/§6.0.3; packet D-012-10)
2. **Order-edit fail-closed gate** — `Order.edited` is queried; `edited == true` →
   terminal `unsupported_order_edit` skip **before any SO write** (quantity/total
   checks alone miss price-only and offsetting edits); evidence = order GID +
   `edited=true` + `updatedAt` only, no edit-history reconstruction. New gate §6.0.0;
   closed skip set now ten. (closure §6.0.0/§10; packet D-012-2)
3. **Nullable `totalTaxSet` policy** — the "`totalTaxSet` null OR equals
   `currentTotalTaxSet`" rule is **withdrawn**. Null original tax is normalized to a
   **canonical zero MoneyBag** in the order's shop+presentment currencies and must
   `money_equal` the non-null `currentTotalTaxSet` (both legs), else the gate fails;
   missing/contradictory currency → `data_shape_schema_mismatch`. Null never
   bypasses the current-vs-original tax check. **(Superseded by round-8 §0-g item 4:
   the canonical-zero-from-null construction is withdrawn; a null `totalTaxSet` now
   fails closed `data_shape_schema_mismatch`.)** (closure §6.0.1; packet D-012-2)
4. **Versioned, fold-free tax fingerprint** — `SHOPIFY_TAX_FINGERPRINT_VERSION = 1`;
   fixed **SHA-256** (not "e.g."); deterministic **length-prefixed UTF-8**
   serialization **including the version**; output `v1:<sha256 hex>`. `title`/`source`
   are **Unicode-NFC only** — **case and whitespace preserved** (no case-folding, no
   whitespace collapse, no truncation); null-source sentinel ≠ empty string.
   Migration posture: a normalization/algorithm change needs a new version; old `v1:`
   rows stay interpretable and are never silently recomputed; `v1:`/`v2:` spaces
   cannot collide. (closure §5.2a; packet D-012-9)
5. **Data-minimization completed** — `DiscountCodeApplication.code`,
   `ShippingLine.code`, and `ShippingLine.custom` removed (no MVP consumer); retained
   `ShippingLine.title` reclassified as bounded merchant free text (SO shipping-line
   description; out of ordinary logs). (closure §4.1/§4.4; packet §4)
6. **One supported-tax contract** — explicit mapping to **leaf `amount_type ==
   'percent'`** sale taxes only; `group`/`fixed`/`division` and base-affecting
   compound structures **fail closed** (`unsupported_tax_structure`); the round-6
   "group tax counts its children" `O`-clause is withdrawn; advanced structures are
   deferred (post-MVP). (closure §5.5/§6.4; packet D-012-9)
7. **One global tax-tolerance formula** — `tol_tax_total = Σ_σ tax_delta_bound(σ) +
   0.5r(S+O)`, and the MVP requires `tax_delta_bound(σ) = 0` for every admitted
   signature (a leaf percent tax's engine excluded base reconciles exactly, else fail
   closed), so `tax_delta_total ≡ 0` — no document calls `0.5r(S+O)` "complete" while
   a nonzero delta is permitted; the nonzero-delta path fails closed (Example L).
   **(Superseded by round-8 §0-g items 1–2: the `tax_delta_bound(σ)=0` / exact-inverse
   premise is withdrawn; the MVP records the actual engine raw-base delta and carries
   `tax_delta_total = Σ_σ tax_delta_bound(σ)` in full.)** (closure §6.4/§6.4a/§6.5;
   packet D-012-2)

Fixtures 118–141; §17 adversarial rows 57–64 (+ a round-7 authorization re-check).

## 0-e. Round-6 correction — 2026-07-14 (control-room review `4692656343`)

A sixth REVISE (docs-only, same five files; PR #159 stays draft/unmerged):

1. **AdditionalFee contract + minimal-privacy design** — official schema corrected
   to `AdditionalFee{ id:ID! name:String! price:MoneyBag! taxLines:[TaxLine!]! }`;
   every "name is the only differentiator / safe non-PII category label" statement
   removed. Task 012 MVP **does not query `Order.additionalFees` at all** — the
   aggregate `currentTotalAdditionalFeesSet`/`currentTotalDutiesSet` drives the
   skip; no `AdditionalFee.name`/price/`taxLines` is requested, stored, or logged;
   evidence = reason + aggregate amount + currency. `AdditionalFee.id` is
   acknowledged as the post-MVP identifier. (closure §4.1/§6.0.3; packet §4)
2. **Collision-safe hashed evidence fingerprint** — `shopify_tax_evidence_key` is
   now a **cryptographic hash of the FULL, untruncated** normalized tuple
   (`ratePercentage`, `title`, null-safe `source`, `channelLiable` tri-state,
   inclusion), serialized deterministically; **no truncation before hashing**.
   Separate **redacted/truncated** `title_preview`/`source_preview` display fields
   exist for the protected operator UI only; raw title/source never enter ordinary
   logs. `title`/`source`/`channelLiable` are called an **evidence fingerprint**,
   not officially stable identifiers; changed evidence → a new, unmapped
   fingerprint. (closure §5.2a)
3. **Explicit-mapping-only tax policy** — automatic rate-only resolution removed.
   Every distinct fingerprint requires an explicit `shopify.connector.tax.mapping`
   row (zero → hold; >1 → defect/hold; must resolve to one active `sale` tax in the
   correct company; fiscal-position revalidated; one fingerprint can never silently
   change its Odoo tax). A same-rate Odoo tax may be shown as a **non-binding
   operator suggestion**, never auto-chosen. (closure §5.2 step 2; packet D-012-8)
4. **Tax auto-creation removed from MVP** — `order_tax_autocreate` and the
   `"Shopify Tax {percent}%"` generator deleted from scope. Reasons recorded
   (same-rate fingerprints ≠ same jurisdiction/accounting; unsafe default
   repartition/accounts; generic-name collision; Odoo tax-name uniqueness;
   operator-owned accounting). Operator flow: create/verify tax → create mapping →
   retry. Auto-create relocated to a separately-accepted post-MVP scope. (closure
   §5.2b; packet D-012-9)
5. **GraphQL data-minimization** — a field-consumption matrix (query constant,
   consumer, persistence/validation purpose, privacy class, necessity) justifies
   every requested field; `note`, `tags`, `sourceName`, line `customAttributes`,
   line `vendor`, `customer.displayName`, `customer.defaultAddress` are removed (no
   MVP consumer). (closure §4.4; packet §4)
6. **Decimal-numeric money equality** — every `MoneyV2`/`MoneyBag` equality/zero
   test uses `money_equal`/`is_zero`: currency-code match + parsed `decimal.Decimal`
   value comparison (never through `float`, never lexical strings), original strings
   kept only as evidence; `Decimal("10.0") == Decimal("10.00")`, a currency
   mismatch is never equal. Applied to totals/current totals, tax totals, shipping
   original/current, presentment evidence, and the duty/fee/tip/cash-rounding gates.
   (closure §3.1a)
7. **Standard-Odoo-tax-engine terminology** — "no tax engine (rate-matching only)"
   replaced everywhere with *"No custom connector tax engine. The standard Odoo 19
   `account.tax` engine is authoritative for excluded base, included total, tax
   breakdown, group and repartition behaviour."* (closure §14; packet §2)

Fixtures 106–117; §17 adversarial rows 50–56.

## 0-d. Round-5 correction — 2026-07-14 (control-room review `4691931971`)

A fifth REVISE (docs-only, same five files; PR #159 stays draft/unmerged):

1. **One executable connection shape** — `lineItems`/`shippingLines`/
   `discountApplications` all use `edges{ cursor node }` in the header first page
   and every page query (no `nodes`-only). Secondary identity: `LineItem.id`
   (non-null), `ShippingLine.id` (nullable), `DiscountApplication` `__typename`+
   `index` (interface has no id). (closure §4.1/§4.2/§4.2a)
2. **Duty-first fee/duty precedence** — additional fees can include duties, so
   `currentTotalDutiesSet != 0 → unsupported_duties` is evaluated **before** the
   additional-fee reason; a duty-only order now reaches the duty reason; no
   subtraction of duties from fees; both-present → duty reason with "composition
   not inferred". (closure §6.0.3)
3. **`AdditionalFee.name` is potentially-PII** — not a safe category label:
   ordinary logs carry only count/amount/currency/reason; names are
   redacted/truncated (`ADDITIONAL_FEE_NAME_MAX_LEN`), capped
   (`ADDITIONAL_FEES_EVIDENCE_LIMIT`), SEC-1-tiered; the list is a plain
   `[AdditionalFee!]!` (no `first:`), read whole and bounded application-side.
   (closure §6.0.3)
4. **Composite `shopify_tax_evidence_key`** — rate + normalized title + null-safe
   source + `channelLiable` tri-state + inclusion, keyed `UNIQUE(store_id,
   shopify_tax_evidence_key)`; the rate-only key is withdrawn (it collapsed
   distinct same-rate taxes → correct total, wrong tax/account); the same identity
   is queried on line/shipping/order tax lines; collisions/ambiguity hold.
   (closure §5.2a)
5. **Residual/tax-base rebuilt around the actual Odoo 19 tax engine** — five false
   claims withdrawn (Float stores Decimal exactly; rounded==pre-rounding;
   `price_include_override` on the SO line; inclusive residual by gross
   subtraction; `tax_delta_bound` auto-zero). Now: `price_include_override` on
   `account.tax`; candidate line + engine `total_excluded`/`total_included`/
   breakdown; excluded-signature residual from the engine base; **inclusive
   residual derived through the engine** (`special_mode='total_excluded'`/bounded
   solver, never gross subtraction); per-signature reconciliation on the **engine
   excluded base**; `tax_delta_bound` **0 only when the engine proves it**, else
   engine-derived or fail closed; binary-float honesty. (closure §6.2/§6.4a)
6. **Nonzero tip fails closed** — `unsupported_tip_tax_treatment`; the untaxed
   Tip line is removed from MVP (`T = 0`), because a small taxed-tip difference
   could hide inside the rounding envelope. (closure §6.0.6/§6.1-C)

## 0-c. Round-4 correction — 2026-07-14 (control-room review `4691408835`)

A fourth REVISE (docs-only, same five files; PR #159 stays draft/unmerged),
followed by a normal base-alignment merge:

1. **Header query completed** — added every current-state field the eligibility
   gates consume (`currentTotalPriceSet`/`currentTotalTaxSet`/
   `currentShippingPriceSet`/`currentTotalAdditionalFeesSet`/
   `currentTotalDutiesSet`, all `MoneyBag`/`MoneyBag!` per verified nullability),
   plus `totalCashRoundingAdjustment` and `additionalFees`. No gate references an
   unqueried field. (closure §4.1)
2. **Shipping refund/removal gate** — `isRemoved` + `currentDiscountedPriceSet ==
   discountedPriceSet` (both currencies) + consistency with
   `currentShippingPriceSet` → else policy skip `refunded_or_removed_shipping`
   before SO. (closure §6.0.2)
3. **Nullable shipping-id pagination** — `ShippingLine.id` is nullable [Fact];
   switched to `edges{ cursor node }`; the edge cursor is the mandatory identity,
   non-null id secondary, null id never a stable GID. (closure §4.2a)
4. **Unsupported additional fees / duties-nonzero / cash rounding** — nonzero
   `currentTotalAdditionalFeesSet` → `unsupported_additional_fees`; duties route on
   the **nonzero amount** (not non-null; present-zero imports); nonzero
   `totalCashRoundingAdjustment` → `unsupported_cash_rounding` (its inclusion in
   `totalPriceSet` is undocumented — fail closed). (closure §6.0.3–§6.0.5)
5. **Tax-base math repaired** — §6.4a now requires **exact** currency-quantized
   per-signature base equality (`q(base_src)==q(base_odoo)`, on the exact tax-engine
   base); the round-3 `≤0.5r(...)` tolerance (inconsistent with the same-Θ proof)
   is withdrawn; a rigorous `tax_delta_bound(σ)` (0 in MVP) is defined via the
   actual mapped Odoo tax function, never `rate × base_diff`. (closure §6.4a/§6.5,
   Example L)
6. **Base alignment** — PR #158 merged; `Shopify-connector` at `1494b97`; this
   branch base-aligned via a **normal merge commit** (no rebase/squash/force);
   SRR-03 stays OPEN, no gate opened. (closure §0.2)

## 0-b. Round-3 correction — 2026-07-14 (control-room review `4691067575`)

A second REVISE (docs-only, same five files; PR #159 stays draft/unmerged)
corrected the remaining decision-packet defects review `4691067575` flagged:

1. **Query contract reconciled to four-query Option-A** across all five docs —
   there is no single `ORDER_IMPORT_QUERY` and no single API call anywhere
   (`ORDER_HEADER_QUERY` + three per-connection page queries). (closure §4)
2. **Exact per-line financial source** — the product-line invariant is the
   official `priceAfterAllDiscountsBeforeTaxesSet` (exact, after all discounts,
   pre-tax, current-quantity); the approximate `discountedUnitPriceSet × quantity`
   construction is withdrawn (Shopify documents that unit price as *approximate*).
   (closure §6.1-A/§6.2)
3. **Fail-closed refund/removed-quantity posture** — `currentQuantity == quantity`
   per line + `totalPriceSet == currentTotalPriceSet` cross-check; any mismatch →
   policy skip `refunded_or_removed_quantity` before any SO, non-PII evidence, no
   refund reconstruction. (closure §6.0)
4. **Per-tax-signature base reconciliation** before any tax tolerance — a global
   `amount_untaxed` match is not sufficient; a signature-base mismatch fails first.
   (closure §6.4a)
5. **Honest tax bound** — `tol_tax = 0.5r(S+O)` reframed as a *proposed
   conditional* bound with explicit assumptions (round-7: unified as
   `tol_tax_total = Σ_σ tax_delta_bound(σ) + 0.5r(S+O)`; **round-8: `tax_delta_total`
   is the actual engine raw-base-delta term, carried in full — the round-7
   `≡ 0` premise is superseded**, §6.4); the Shopify-event rounding
   premise labelled separately (inference, not an official guarantee);
   undocumented-rounding currencies fail closed. (closure §6.5)
6. **Shipping/tip precision** — exact shipping pre-tax source (tax backed out once
   only when inclusive); tip untaxed labelled an inference, fail-closed via the
   total self-check. (closure §6.1-B/C)
7. **`execute_business` AST guards** replace the stale single-`execute()` guard
   (every call via `execute_business`, no generic public `execute()` reachable, no
   result escapes its context). (closure §15)
8. **Dependency reference** aligned to the **accepted** PR #158 Slice-2B
   integration-staging strategy (review `4691064435`); the current unprotected
   PR #150/#151 heads are not directly mergeable. (closure §0.1)

## 0. Correction round — 2026-07-14 (control-room review `4690680028`)

The initial closure was REVISED (docs-only) for four load-bearing corrections
plus consistency items; PR #159 stays draft/unmerged:

1. **Dependency contract → capability-based** (not direct-merge of PR #150/#151):
   SRR-03 CLOSED; protected/guarded product import + complete variant bindings;
   protected/guarded customer import + indexed email matching; no unguarded
   product/customer Shopify call; LC-1 + DEC-030 — delivered via the accepted
   CORE-R2 Slice-2B integration-staging strategy (PR #158, review `4691064435`;
   the unprotected #150/#151 heads are not directly mergeable — round-3, §0-b).
   **CORE-R1 is already merged (satisfied, not pending).** (closure §0.1)
2. **Financial ledger rebuilt** into one canonical single-count equation
   `U_ex = M + H + T` (product/shipping/tip each once). *(Superseded by round-3,
   §0-b: `M` now comes from the exact `priceAfterAllDiscountsBeforeTaxesSet` field,
   there is no global `U_ex = G − totalTaxSet` back-out, and a per-tax-signature
   base reconciliation was added.)* (closure §6.1/§6.3)
3. **Tax bound** `tol_tax = 0.5r(S+O)` from both systems' rounding events,
   replacing the invalid `K = distinct groups`; added the many-small-lines /
   `round_globally` counterexample (Example I). *(Round-7 §0-f unified this as
   `tol_tax_total = Σ_σ tax_delta_bound(σ) + 0.5r(S+O)`; **round-8 §0-g carries
   `tax_delta_total` as the actual engine raw-base-delta term — the `≡ 0` premise is
   superseded**.) (Reframed in round-3, §0-b, as a
   proposed **conditional** bound with an explicitly-labelled platform-rounding
   premise.)* (closure §6.4/§6.5)
4. **Pagination made implementation-exact** (Option A — a header query + three
   independent per-connection cursor page queries; `Order.id`/`updatedAt`
   verification; cursor progress; node dedup; torn-read →
   `concurrency_race_conflict`; no SO write until all connections collected).
   (closure §4.2)
5. **GraphQL-cost claim corrected** — page sizes are named provisional defaults;
   `requestedQueryCost`/`actualQueryCost` + `throttleStatus` telemetry; dev-store
   live-read before tuning. (closure §4.3)
6. **Tax-mapping safety** — company match to `order_company_id`, active/sale/
   percent/inclusion checks, fiscal-position validation, ambiguous(>1) → hold,
   first-never-silently; the Decimal/string key is the identity layer,
   `float_compare` only the Odoo-Float boundary. (closure §5.2/§5.5)
7. **JobPolicySkip seam reconsidered** — recommended the smaller
   terminal-state-respect dispatcher guard; the Task-012 core edit is now
   **conditional** and coordinated with CORE-R2; may be **no** core edit.
   (closure §10/§14)

## 1. What this session did

Produced a **decision-complete, evidence-backed Task 012 order-import packet**
so the locked prompt can be issued immediately after its **capability**
prerequisites hold. Specifically:

- Verified repository state: `Shopify-connector` tip
  `912801508155c6358e8f5f1a7a0aaf01ae573675`; PR #150 (Task 011B) and PR #151
  (Task 010B) accepted but open/draft/unmerged; CORE-R2 SRR-03 **open**
  (Foundation Slice 1 only); LC-1 **not merged**; working tree clean.
- Ran a high-power research fan-out (11 workstreams + a completeness pass):
  repo decisions/interfaces (DEC-003/007/008/009/014/018/020, Task 010B/011B,
  CORE-R2, LC-1, rejected-approaches, captures) **and** fresh official Shopify
  Admin GraphQL 2026-07 + Odoo 19.0 source verification, every platform claim
  cited with a URL + access status.
- Wrote the decision-closure
  [`../03-architecture/task-012-order-import-decision-closure.md`](../03-architecture/task-012-order-import-decision-closure.md)
  covering the order-binding schema, GraphQL query contract, MBQ-27 tax
  representation, MBQ-56 total-check (formulas + worked examples), discount
  representation, customer/address resolution, product/order-hold, DEC-020
  divergent-currency routing, ORDERS_UPDATED posture, job/failure and
  security/privacy contracts, the exact file map, the test catalogue, and a
  strict adversarial self-critic.
- Updated the packet
  [`task-012-order-import-implementation-packet.md`](./task-012-order-import-implementation-packet.md)
  (D-012-1 money→Char, D-012-2 total-check, §4 pagination, §15 locked prompt —
  all further corrected in the round-2 pass, §0) and the proposed brief, and
  recorded **proposed-resolution status + links (not acceptance)** in the
  MBQ-27/56/64 register rows.

## 2. Corrections made (adversarial findings)

| Finding | Correction |
| --- | --- |
| Money stored as Odoo `Float` (lossy) | All binding money snapshots → **`Char`** (exact Shopify `Decimal` string), parsed via `decimal.Decimal`; shop + presentment + component snapshots |
| Line-item / nested-connection pagination could reject large orders | **Full cursor pagination** of `lineItems`/`shippingLines`/`discountApplications`; cursors never persisted; page-limit backstop; the "reject >100 lines" stance withdrawn |
| Tax tolerance ignored Odoo-19 `round_globally` default | Round-2: `tol_tax = 0.5r(S+O)` from both systems' rounding events (the round-1 `K=distinct groups` was insufficient) + counterexample. Round-3: reframed as a **proposed conditional** bound with a labelled platform-rounding premise + mandatory per-tax-signature base reconciliation first. Round-7: unified as `tol_tax_total = Σ_σ tax_delta_bound(σ) + 0.5r(S+O)`. **Round-8: `tax_delta_bound(σ)=base_delta(σ)×rate/100` is the actual engine raw-base-delta term (`special_mode` is a seed, not an exact inverse); `tax_delta_total` is carried in full, `O` counts SO tax-details grouping keys not repartition rows** |
| Approximate unit price / refunds not addressed (round-3) | `M` now from the exact `priceAfterAllDiscountsBeforeTaxesSet` field (never `quantity × discountedUnitPriceSet`); refunds/removed quantities fail closed (`currentQuantity == quantity`); four-query Option-A everywhere; `execute_business` AST guards replace the single-`execute()` guard |
| Divergent-currency routing risk of overloading `financial_total_mismatch` | Confirmed as terminal `skipped` **policy** (no error class); the core skip seam is now **conditional/coordinated with CORE-R2** (recommended: terminal-state-respect guard; may be no core edit) |

## 3. Proposed decisions (all NOT accepted — control-room review required)

Order binding schema (§3); read-only GraphQL query contract + pagination/cost
(§4); MBQ-27 tax = mapped/matched `account.tax` under the guard, no external
tax-amount inverse at SO level (§5); MBQ-56 component tolerance with worked
examples (§6); discount representation (§7); customer/address resolution incl.
company/person + address-child gaps (§8); product/order-hold (§9); divergent
currency → `skipped` policy (§10); ORDERS_UPDATED evidence-refresh-only (§11);
job/failure + security/privacy contracts (§12–13); exact file map (§14); test
catalogue (§15).

## 4. Capability prerequisites (all currently unmet — PR-merge-agnostic; §0.1)

1. **SRR-03 CLOSED** (CORE-R2 disconnect quiescence runtime-green; register
   forbids merging/enabling/live-validating any Shopify-calling domain handler
   until then; parallel development allowed).
2. **Protected/guarded product import + complete product/variant bindings** in
   `Shopify-connector`.
3. **Protected/guarded customer import + indexed normalized-email matching** in
   `Shopify-connector`.
4. **No unguarded product/customer Shopify call remains** (public generic
   `execute` closed).
5. **Task LC-1** merged / **DEC-030** accepted (the
   `_reassign_to_historic_job_type` ondelete callable).
6. Control-room acceptance of this closure + packet, the order-domain gate act,
   and prompt issuance.

These arrive via the **accepted CORE-R2 Slice-2B integration-staging strategy
(PR #158, review `4691064435`)** — the current unprotected PR #150/#151 heads are
**not** directly mergeable. **CORE-R1 is already merged (satisfied, not pending).**

## 5. Open questions carried

- Verbatim GraphQL `THROTTLED` error-code string (docs show only `200 Throttled`).
- Shopify three-decimal-currency rounding policy (undocumented) → the `tol_tax_total`
  platform-rounding premise fails closed until a named authorized dev-store
  empirical check confirms the convention.
- **Tip tax treatment is undocumented in the Admin API** (no `TipLine`) → round-5
  makes a **nonzero tip fail closed** (`unsupported_tip_tax_treatment`); a future
  store policy needs official/live evidence + an explicit mapping before tips
  import.
- **Inclusive-tax residual solver bound [corrected round-8]:** Odoo 19's
  `special_mode='total_excluded'` is a **seed, NOT an exact inverse** — symmetrical
  accuracy is guaranteed only with an unrounded `price_unit` and `round_globally`,
  and `price_unit` is a `Float` (review `4694311215` item 1). So the design seeds
  from the analytic mode, runs a **deterministic bounded solver** over currency-valid
  `price_unit` values, **recomputes through the actual engine**, and accepts only
  from the engine readback (`raw_base_amount_currency`/`tax_amount_currency`), failing
  closed if no candidate reconciles. The exact iteration bound is a build-time
  detail; any future reliance on the analytic mode as an exact inverse is out of
  scope and would need engine-level evidence.
- **No LineItem field distinguishes refunded from removed units** — not needed
  (the §6.0 gate fails closed on the aggregate), logged for rationale.
- **Whether a nonzero `totalCashRoundingAdjustment` is included in
  `totalPriceSet`/`currentTotalPriceSet` is UNDOCUMENTED** [Open question] — the
  docs establish only that it applies to `totalReceived`/`totalRefunded`; Task 012
  **fails closed** on any nonzero adjustment (`unsupported_cash_rounding`) until
  the relationship is proven representable.
- **`AdditionalFee.name` is arbitrary merchant free text (potentially PII), not a
  category label** [Fact — round-6]; **`Order.additionalFees` in 2026-07 exposes
  list/pagination/filter arguments** [Fact — round-7, per review `4693694894`] — so
  the field is **not** unbounded, but Task 012 still **does not query it at all** for
  **data minimization** (evidence = reason + aggregate amount + currency; no name).
  If a post-MVP feature ever needs per-fee detail it keys on the stable
  `AdditionalFee.id`.
- **Tax-evidence fingerprint — versioned + fold-free [resolved round-7].** The hash
  is pinned: `SHOPIFY_TAX_FINGERPRINT_VERSION = 1`, **SHA-256**, deterministic
  length-prefixed UTF-8 (incl. the version), output `v1:<hex>`; `title`/`source`
  are **NFC-only, case + whitespace preserved** (no folding). A future
  normalization/algorithm change is a **versioned migration** (`v2:`). Still a
  build-time confirmation: the precise company/country/type-of-use scope of Odoo
  19's tax-name uniqueness constraint (relevant only to the deferred auto-create,
  which MVP does not do).
- **Advanced Odoo tax structures deferred [round-7].** MVP supports only leaf
  `amount_type=='percent'` sale taxes; `group`/`fixed`/`division`/base-affecting
  compound **fail closed** (`unsupported_tax_structure`). Admitting them — and the
  **non-linear** engine `tax_delta_bound(σ)` a complex structure would need (the
  MVP's linear `base_delta×rate/100` term applies only to leaf percentages) — is a
  separately-accepted post-MVP scope.
- **Nullable `totalTaxSet` semantics [round-8].** Shopify documents `totalTaxSet` as
  nullable but **not** that null means zero; MVP **fails closed** on null
  (`data_shape_schema_mismatch`, §6.0.1). A **dev-store validation obligation** is
  recorded to determine whether Shopify emits null for a legitimate tax-free case;
  only a later accepted decision backed by official/live evidence may normalize
  null→zero (review `4694311215` item 3).
- **`O` counts sale-order tax-computation events, not repartition rows [round-8].**
  `amount_tax` comes from the SO tax-details computation; the round-7 clause that
  counted invoice tax-repartition lines in `O` is withdrawn (review `4694311215`
  item 2).
- **Order edits deferred [round-7].** `Order.edited == true` fails closed
  (`unsupported_order_edit`); representing edited orders is future scope.
- Empirical confirmation of the per-tax-signature **quantized base equality** (§6.4a,
  on the engine `raw_base_amount_currency`) and the `OC` attribution on a real
  mixed-discount order → named dev-store check.
- `res.partner.company_name` as the sink for `MailingAddress.company` (confirm
  at build; `is_company` stays False regardless).
- The exact core skip seam (terminal-state-respect guard vs `JobPolicySkip`) is
  settled with the CORE-R2 owner; Task 012 may need **no** core edit.
- GraphQL requested/actual query cost for the chosen page sizes — dev-store
  measured before production tuning.

## 6. Files changed this session (docs-only)

- `docs/03-architecture/task-012-order-import-decision-closure.md` (round-1 new;
  round-2 rebuilt §0/§4/§5/§6/§7/§10/§14/§15/§17/§18; round-3 four-query §4,
  exact-source + refund gate §6.0/§6.1/§6.2, per-signature §6.4a, conditional
  bound §6.5, tip/shipping §6.1-B/C, guards §15, deps §0.1; **round-4** current-
  state query fields §4.1, shipping gate §6.0.2 + edge-cursor §4.2a, fees/duties/
  cash-rounding gates §6.0.3–§6.0.5, exact base equality §6.4a, Examples L/M/N,
  fixtures 66–83, §17 rows 31–39, base alignment §0.2; **round-5** all-three
  edges/cursor §4.1/§4.2, duty-first + fee-privacy §6.0.3, composite tax key
  §5.2a, tip gate §6.0.6, tax-engine rebuild §6.2/§6.4a, fixtures 84–105, §17 rows
  40–49; **round-6** additionalFees-detail-not-queried §4.1/§6.0.3, field-consumption
  matrix §4.4, hashed fingerprint §5.2a, explicit-mapping-only §5.2, auto-create
  removed §5.2b, Decimal-numeric equality §3.1a, tax-engine terminology §14,
  fixtures 106–117, §17 rows 50–56; **round-7** additionalFees list-args fact
  §2/§4.1/§6.0.3, order-edit gate §6.0.0 + skip set §10, nullable-`totalTaxSet`
  §6.0.1, versioned/NFC-only fingerprint §5.2a, `code`/`ShippingLine.code`/`custom`
  removed §4.1/§4.4, leaf-percent-only tax contract §5.5/§6.4, one `tol_tax_total`
  formula §6.4/§6.4a/§6.5, Examples O/P, fixtures 118–141, §17 rows 57–64;
  **round-8** engine-seed-not-exact-inverse §6.2-C, actual raw-base delta
  §6.4/§6.4a/§6.5, `O`-not-repartition §6.4, nullable-`totalTaxSet` fail-closed
  §6.0.1, six-gate count §6.0/§6.0.4, Examples Q/R + P/L re-framed, fixtures
  122–124/133/134/141 updated + 142–149 added, §17 rows 57/59/63 re-framed + 65–73,
  §5.4/§18 dev-store obligations)
- `docs/07-implementation-plan/task-012-decision-closure-handoff.md` (**round-6**
  §0-e; **round-7** §0-f + §5/§6/§7/§8 refresh; **round-8** §0-g + §5/§6/§7/§8
  refresh)
- `docs/07-implementation-plan/task-012-order-import-implementation-packet.md`
  (money→Char, canonical ledger, Option-A pagination, cost posture, tax-mapping
  safety, conditional skip seam, locked prompt; round-3 exact-line-total
  source/refund gate/per-signature/conditional `tol_tax`/`execute_business`
  guards; round-4 current-state query fields, shipping gate + edge-cursor,
  fee/duty/cash-rounding gates, exact base equality, MERGED PR-#158 deps;
  **round-5** all-three edges/cursor, duty-first + fee-privacy, composite tax key,
  tip fail-closed, tax-engine residual rebuild, locked prompt; **round-6** §2
  terminology, D-012-2 Decimal-numeric gates, D-012-8/9 hashed fingerprint +
  explicit-mapping-only + auto-create removed, query minimization + additionalFees
  removed, §6 test list, locked prompt; **round-7** header a7–g7, §2 non-goals
  (order edits + advanced tax), D-012-2 order-edit gate + nullable-`totalTaxSet` +
  `tol_tax_total`, D-012-9 versioned/NFC fingerprint + leaf-percent-only structure,
  D-012-10 additionalFees list-args fact, query text (`edited` added;
  `code`/`ShippingLine.code`/`custom` removed), §6 test list, locked prompt gates +
  tolerance + fingerprint + query fields; **round-8** header a8–e8, D-012-2
  seed+solver+readback / actual raw-base delta / `O`-not-repartition / six gates /
  nullable-tax fail-closed, D-012-9 tax structure delta, §6 test list, locked prompt
  gates + tolerance + engine contract)
- `docs/07-implementation-plan/task-012-order-import-proposed.md` (**round-6**
  MBQ-27 resolution + total-check note: hashed fingerprint, explicit-mapping-only,
  no auto-create, data-minimization, Decimal-numeric equality, standard tax engine;
  **round-7** MBQ-27 versioned/NFC fingerprint + leaf-percent-only; total-check
  order-edit gate + nullable-`totalTaxSet` + additionalFees list-args +
  `code`/shipping-field removal + `tol_tax_total`; review list; **round-8** MBQ-27
  seed+solver recompute, total-check six-gate/seed-not-inverse/nullable-fail-closed/
  actual-raw-base-delta/`O`-not-repartition, review list)
- `docs/03-architecture/master-blueprint-open-questions.md` (MBQ-27/56/64
  proposed-resolution status + links only — **not** marked accepted; **round-6**
  note refresh; **round-7** MBQ-27/56 note refresh — versioned fingerprint,
  order-edit gate, nullable-tax, leaf-percent tax, one `tol_tax_total`, review list;
  **round-8** MBQ-27/56 note refresh — seed-not-inverse, actual raw-base delta,
  `O`-not-repartition, nullable-tax fail-closed, six gates, review list)

## 7. Learning feedback loop

- **Fresh official verification beats repo summaries.** The lossy-`Float`
  money bug survived earlier planning because prior captures did not force the
  `Decimal`-string consequence; a direct read of the 2026-07 `Decimal` scalar
  page made the fix unambiguous. *Lesson: for money/tax/precision, always read
  the scalar/type page, not only the object page.*
- **Odoo defaults drift between versions.** Odoo 19's tax rounding default
  flipped to `round_globally`; a fresh 19.0 source read caught it — but the
  round-1 `K=distinct groups` bound was still wrong because Shopify rounds
  **per line**. *Lesson: a rounding bound must count BOTH systems' rounding
  events (`S+O`), proven by triangle inequality, and be tested with an
  adversarial many-small-lines counterexample — not asserted "tight".*
- **A financial ledger must count each component exactly once.** The round-1
  `shopify_lines_expected` excluded shipping/tips while examples included them.
  *Lesson: write one canonical source equation and make every example/test use
  it verbatim; prove no double subtraction; distinguish line-level vs
  order-level discounts explicitly.*
- **Reaching a terminal state from a handler needs a dispatcher seam — but
  design it as the smallest general primitive.** A terminal-state-respect guard
  (write `succeeded` only if still non-terminal) is smaller than a bespoke
  `JobPolicySkip` exception and composes with CORE-R2's own skip routing.
  *Lesson: when a sibling task is correcting the same core file, make the seam
  conditional and coordinate, rather than fixing a competing mechanism.*
- **Dependencies are capabilities, not PR numbers.** A staging/integration
  strategy can subsume the very PRs an earlier plan named as merge
  prerequisites. *Lesson: express cross-task prerequisites as required
  capabilities in the integration branch, indifferent to which PR delivers
  them.*
- **Use the exact official field, not a plausible derivation.** The round-2
  ledger multiplied an *approximate* unit price (`discountedUnitPriceSet`) by
  quantity and assumed it equalled the discounted total — which Shopify does not
  guarantee. The API has an exact all-discounts-before-tax line-total field
  (`priceAfterAllDiscountsBeforeTaxesSet`); reading the field descriptions
  verbatim (it also *excludes refunded/removed quantities*) surfaced both the
  exact invariant and the refund/removed eligibility gate at once. *Lesson: for a
  financial invariant, find the exact field and read its full description — do not
  reconstruct it from unit-price × quantity.*
- **A rounding bound is conditional on premises the schema may not state.** The
  `0.5r(S+O)` bound is only valid once the per-signature bases reconcile and each
  platform rounds within `0.5r` — and Shopify's rounding convention is
  undocumented. *Lesson: label the platform-rounding premise separately as an
  inference, discharge the base-equality assumption with an explicit
  per-signature reconciliation step, and fail closed where the premise is
  unverified.*
- **A gate may only reference a queried field.** The round-3 eligibility gate
  compared `totalPriceSet == currentTotalPriceSet` but the query fetched only the
  originals — the gate referenced fields the query never requested. *Lesson: when
  a gate is added, add its fields to the exact query in the same change and assert
  it with a "query-contains-every-guard-field" test.*
- **A reconciliation *tolerance* can silently contradict the *proof* it feeds.**
  §6.4a allowed `|base_src−base_odoo| ≤ 0.5r(...)` while §6.5 proved the tax bound
  assuming one exact `Θ` — a nonzero base delta breaks that assumption. *Lesson:
  when a proof assumes exact equality, the preceding step must enforce exact
  (currency-quantized) equality, not a tolerance; and a base-delta term for
  group/compound/included taxes must follow the actual tax function, never a
  single-rate multiplication.*
- **"Non-null" is not "nonzero," and current ≠ original.** Duties were skipped on
  a non-null field (wrong — a present-zero MoneyBag is fine); refund/removal
  needed the `current*` and per-shipping-line fields, not just the originals.
  *Lesson: for money gates, test the Decimal amount, and read current-state vs
  before-returns semantics from the field descriptions.*
- **One executable query shape, everywhere.** The field list and the pagination
  contract drifted apart (`nodes` in one, `edges{cursor}` in the other). *Lesson:
  pick the shape the dedup rules require (edge cursor) and write it identically in
  the header first page and every page query — a mixed shape is not runnable.*
- **Reconcile against the real engine, not a hand formula.** The base/residual
  math assumed `price_include_override` on the SO line, exact Decimal storage in a
  Float, and net→gross by subtraction — all false. Reading the Odoo 19 tax-engine
  source (`_add_tax_details_in_base_line`, `total_excluded`, the price-included
  de-grossing, `special_mode='total_excluded'`) replaced guesses with the actual
  API. *Lesson: when reconciling to another system's computed value, drive that
  system's own engine and read its returned base/tax back — never re-derive it.*
- **A rate is not a tax identity; free text is not a category.** A rate-only tax
  key collapsed distinct taxes (right total, wrong account); `AdditionalFee.name`
  was treated as a safe label though it is arbitrary merchant text. *Lesson: key on
  all stable evidence (title/source/liability), fail closed on collisions, and
  treat merchant free text as potentially-PII (redact/bound).*
- **Don't lean on a tolerance to cover an unknown.** A nonzero tip was imported
  untaxed, trusting the rounding envelope to catch a taxed tip — but a small taxed
  difference fits inside it. *Lesson: when a component's tax treatment is unproven,
  fail closed rather than hoping the total guard absorbs it.*
- **Don't fetch what you don't consume — especially free text.** The packet queried
  `Order.additionalFees` (an unbounded plain list of arbitrary `name` text), plus
  `note`/`tags`/`customAttributes`/`vendor`/`displayName`/`defaultAddress`, none of
  which any gate or ledger read; an aggregate field already drove the skip. *Lesson:
  build a field-consumption matrix — every requested field needs a named consumer;
  remove the rest; retention limits do not bound what the API returns.*
- **Hash the whole identity; never truncate before the key.** The evidence key
  truncated the title before constructing uniqueness, so two long titles sharing a
  prefix could collide. *Lesson: normalize and hash the FULL tuple for identity;
  keep truncation only for human-readable display fields, never in the key.*
- **A single-attribute match is not a whole-evidence match; auto-create is an
  accounting decision.** Odoo `account.tax` has no Shopify source/liability, so a
  same-rate match can't prove the right tax/account, and generating taxes by
  `percent` collides names and picks unsafe repartition. *Lesson: require explicit
  operator mapping for anything non-trivial; offer same-rate taxes only as a
  suggestion; keep accounting-config creation operator-owned and out of MVP.*
- **Compare money by value, not by string.** Lexical equality of Shopify's
  arbitrary-precision decimal strings would reject `10.0` vs `10.00`. *Lesson:
  parse both amounts with `decimal.Decimal`, require a currency-code match, compare
  values, and keep the raw string only as evidence.*
- **Name the boundary you own vs the engine that's authoritative.** Calling the
  design "no tax engine (rate-matching only)" contradicted the fact that the
  standard Odoo `account.tax` engine does all base/breakdown/repartition work.
  *Lesson: state precisely "no CUSTOM connector tax engine; the standard Odoo 19
  engine is authoritative" so the boundary is unambiguous.*
- **State a field's real shape, then justify omission on the right grounds.** The
  round-6 rationale omitted `Order.additionalFees` by calling it an "unbounded
  plain list" — but the 2026-07 field exposes list/pagination/filter arguments. The
  omission is still correct; the *reason* was wrong. *Lesson: describe the official
  shape accurately, then omit on a defensible ground (no consumer / data
  minimization), so the rationale survives a schema re-read.*
- **A totals check can miss an edit that nets to zero — gate on the explicit flag.**
  Quantity/total comparisons pass a price-only edit or two offsetting edits.
  *Lesson: when a dedicated boolean exists (`Order.edited`), fail closed on it
  directly rather than inferring the condition from derived amounts.*
- **"Null" is a value with a policy, not a free pass — and don't invent the policy.**
  The gate first let a null `totalTaxSet` bypass the tax check; round-7 then
  *normalized null to a canonical zero* — but Shopify never documents that null means
  zero, so that too was an invented semantic. *Lesson: when the platform documents a
  field as nullable but not what null means, **fail closed** and record a dev-store
  obligation; do not manufacture zero (or any) semantics the docs don't state.*
  (round-8 corrects the round-7 canonical-zero lesson)
- **Don't fold what the platform doesn't define as fold-insensitive.** The
  fingerprint case-folded and whitespace-collapsed `title`/`source`, collapsing
  genuinely distinct evidence. *Lesson: preserve case and whitespace (Unicode NFC
  only), pin the algorithm (SHA-256) and a length-prefixed serialization, and
  **version** the contract so a future change migrates instead of silently
  recomputing keys.*
- **One contract per concept — no self-contradiction across sections.** One section
  required `amount_type=='percent'` while others claimed group/compound support and
  counted group children; and `0.5r(S+O)` was called the complete tax tolerance
  while a nonzero `tax_delta_bound` was allowed elsewhere. *Lesson: pick the safe
  MVP contract (leaf percent only), state one global formula
  (`tol_tax_total = tax_delta_total + 0.5r(S+O)`, carried in full), and sweep every
  section/example/test to the single contract.*
- **Don't claim a platform inverts exactly when its own docs hedge.** Round-7 called
  `special_mode='total_excluded'` an exact inverse for price-included percentage
  taxes and concluded `delta_engine == 0`; but Odoo 19 guarantees that symmetry only
  with an unrounded `price_unit` + `round_globally`, and `price_unit` is a `Float`.
  *Lesson: treat an analytic mode as a **seed**, recompute through the real engine,
  read back the actual `raw_base_amount_currency`/`tax_amount_currency`, accept only
  from that, fail closed otherwise — and carry the **actual** engine delta in the
  bound rather than asserting it is zero.* (round-8)
- **Count rounding events where the amount is actually computed.** `O` counted a
  tax's invoice/accounting repartition rows, but `sale.order` `amount_tax` comes from
  the tax-engine tax details, not repartition rounding — so a multi-repartition tax
  would have needlessly widened the tolerance. *Lesson: derive a rounding-event count
  from the computation that actually produces the figure being compared (SO
  tax-details grouping keys), not from a downstream accounting artifact.* (round-8)

## 8. Exact next-session prompt (control-room to issue)

```text
Docs-only control-room review session (NOT implementation).

Review the Task 012 order-import decision-closure PR (branch
claude/task-012-decision-closure-mb88sn → Shopify-connector):
- docs/03-architecture/task-012-order-import-decision-closure.md
- the updated packet §15 locked prompt and D-012-1/2/3/9
- the MBQ-27/56/64 proposed-resolution notes.

Decide per D-012 item: accept / revise / reject. In particular rule on:
(a) money snapshots as Char/exact-decimal-string (not Float/Monetary);
(b) the exact per-line source `priceAfterAllDiscountsBeforeTaxesSet` (not
    quantity × discountedUnitPriceSet), the canonical ledger U_ex = M + H (T=0),
    the Odoo representation **through the actual tax engine** (engine
    total_excluded; price_include_override on account.tax; inclusive residual via a
    **seed + bounded solver recomputed through the actual engine** —
    `special_mode='total_excluded'` is a **seed, NOT an exact inverse**, accept only
    from the engine readback `raw_base_amount_currency`/`tax_amount_currency`, else
    fail closed; binary-float honesty), **SIX** fail-closed pre-creation gate
    families (§6.0.4 is a pointer into duty-first §6.0.3, not a seventh), the
    per-signature quantized reconciliation on the **engine RAW excluded base**
    (`raw_base_amount_currency`; a full minor-unit error fails closed), the
    **order-edit gate** (`Order.edited==true` → `unsupported_order_edit`) and the
    **fail-closed nullable-`totalTaxSet` rule** (null `totalTaxSet` →
    `data_shape_schema_mismatch`, no SO/binding — Shopify does not document null==zero;
    the round-7 canonical-zero construction is withdrawn), and the **one global
    `tol_tax_total = tax_delta_total + 0.5r(S+O)`** where `tax_delta_total = Σ_σ
    tax_delta_bound(σ)` is the **actual** engine raw-base-delta term
    (`tax_delta_bound(σ)=base_delta(σ)×rate/100`, leaf percentages only) — **carried
    in full, not assumed zero, not reduced to `0.5r(S+O)`**; `O` counts SO tax-details
    grouping keys, never invoice repartition rows — and its labelled
    platform-rounding premise;
(c) the four-query Option-A contract with **all three connections in one
    `edges{ cursor node }` shape**, every current-state/tax-evidence guard field in
    the query (**including `Order.edited`**), the shipping refund/removal gate, the
    `execute_business` AST guards, provisional page sizes + cost telemetry, and the
    **data-minimized** field set (field-consumption matrix §4.4;
    `note`/`tags`/`sourceName`/`customAttributes`/`vendor`/`displayName`/
    `defaultAddress`/**`DiscountCodeApplication.code`/`ShippingLine.code`/
    `ShippingLine.custom`** removed; retained `ShippingLine.title` bounded; **`Order.additionalFees`
    detail NOT queried** — it exposes list/pagination/filter args but is omitted for
    **data minimization**; the aggregate drives the fee skip, no `AdditionalFee.name`);
(d) MBQ-27 **explicit-mapping-only, leaf `amount_type=='percent'`-only** account.tax
    resolution under the standard Odoo tax engine + the guard, with the §5.5 safety
    **and the versioned SHA-256 evidence fingerprint `shopify_tax_evidence_key`**
    (`v1:<hex>`, `SHOPIFY_TAX_FINGERPRINT_VERSION=1`, full untruncated
    rate+title+source+channelLiable+inclusion tuple, **NFC-only — case+whitespace
    preserved, no folding**; zero/>1/collision → hold; a same-rate tax is an operator
    suggestion only, never auto-chosen; group/fixed/division/base-affecting compound
    **fail closed** (`unsupported_tax_structure`, deferred); **no
    `order_tax_autocreate` / no tax auto-create** — operator creates tax + mapping +
    retries); and **Decimal-numeric money equality** (`money_equal`: currency match +
    parsed-Decimal value, not lexical strings);
(e) the closed policy-skip set — **order edits (`unsupported_order_edit`)**;
    divergent currency; refunded/removed **product**; refunded/removed/modified
    **shipping**; **duty-first** duties then additional fees (**aggregate-only
    evidence, no fee name queried**); **nonzero** cash rounding; **nonzero tip**
    (`unsupported_tip_tax_treatment`); test; pre-cancelled — via the
    conditional/coordinated core skip seam (terminal-state-respect guard
    recommended).

Do NOT open the order-domain gate or issue the locked prompt until the
CAPABILITY prerequisites (§0.1 / §4) hold in Shopify-connector — SRR-03 CLOSED;
protected/guarded product import + variant bindings; protected/guarded customer
import + indexed email matching; no unguarded product/customer Shopify call;
LC-1 + DEC-030 — delivered via the accepted CORE-R2 Slice-2B integration-staging
strategy (PR #158, review 4691064435; the unprotected #150/#151 heads are NOT
directly mergeable). CORE-R1 is already merged. If accepting,
record it in architecture-review-log.md and mark the MBQ-27/56/64 rows
resolved; the locked prompt stays unusable until the separate gate act. Also
coordinate the core skip seam with the CORE-R2 owner (PR #158/#160).
```

## 9. Session completeness

Documentation-only; no code; no gate; no live Shopify request. The no-code gate
(CLAUDE.md §4–§5) remains in force. This handoff, plus the decision-closure and
the updated packet/proposed/register, constitute the deliverable.
