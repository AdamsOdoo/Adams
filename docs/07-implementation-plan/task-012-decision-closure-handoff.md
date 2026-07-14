# Task 012 — Order-Import Decision-Closure Handoff

> **Docs-only session handoff.** No gate opened, no code written, no live
> Shopify request. Produced by the Task 012 final pre-implementation
> decision-closure session, 2026-07-14. Follows
> [`session-handoff-template.md`](../06-prompts/session-handoff-template.md).
> The canonical `docs/01-research/research-handoff.md` top entry is a
> control-room action and is **not** modified here (that file is outside this
> session's allowed-files list).

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
   conditional* bound with explicit assumptions; the Shopify-event rounding
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
   `round_globally` counterexample (Example I). *(Reframed in round-3, §0-b, as a
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
| Tax tolerance ignored Odoo-19 `round_globally` default | Round-2: `tol_tax = 0.5r(S+O)` from both systems' rounding events (the round-1 `K=distinct groups` was insufficient) + counterexample. Round-3: reframed as a **proposed conditional** bound with a labelled platform-rounding premise + mandatory per-tax-signature base reconciliation first |
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
- Shopify three-decimal-currency rounding policy (undocumented) → the `tol_tax`
  platform-rounding premise fails closed until a named authorized dev-store
  empirical check confirms the convention.
- **Tip tax treatment is undocumented in the Admin API** (no `TipLine`) → round-5
  makes a **nonzero tip fail closed** (`unsupported_tip_tax_treatment`); a future
  store policy needs official/live evidence + an explicit mapping before tips
  import.
- **Inclusive-tax residual solver bound:** Odoo 19's engine gives an exact
  analytic net→gross path for percentage price-included taxes
  (`special_mode='total_excluded'`); the rounded/mixed-tax case needs a bounded
  deterministic solver whose exact iteration bound is a build-time detail (fail
  closed if no currency-valid residual reconciles).
- **No LineItem field distinguishes refunded from removed units** — not needed
  (the §6.0 gate fails closed on the aggregate), logged for rationale.
- **Whether a nonzero `totalCashRoundingAdjustment` is included in
  `totalPriceSet`/`currentTotalPriceSet` is UNDOCUMENTED** [Open question] — the
  docs establish only that it applies to `totalReceived`/`totalRefunded`; Task 012
  **fails closed** on any nonzero adjustment (`unsupported_cash_rounding`) until
  the relationship is proven representable.
- **`AdditionalFee` has no category enum** — duty-vs-import-fee is only the
  free-text `name` [Fact]; the fee gate holds on the **nonzero amount** regardless
  of kind, recording `name` as bounded non-PII evidence.
- Empirical confirmation of the per-tax-signature **exact base equality** (§6.4a)
  and the `OC` attribution on a real mixed-discount order → named dev-store check.
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
  40–49)
- `docs/07-implementation-plan/task-012-decision-closure-handoff.md`
- `docs/07-implementation-plan/task-012-order-import-implementation-packet.md`
  (money→Char, canonical ledger, Option-A pagination, cost posture, tax-mapping
  safety, conditional skip seam, locked prompt; round-3 exact-line-total
  source/refund gate/per-signature/conditional `tol_tax`/`execute_business`
  guards; round-4 current-state query fields, shipping gate + edge-cursor,
  fee/duty/cash-rounding gates, exact base equality, MERGED PR-#158 deps;
  **round-5** all-three edges/cursor, duty-first + fee-privacy, composite tax key,
  tip fail-closed, tax-engine residual rebuild, locked prompt)
- `docs/07-implementation-plan/task-012-order-import-proposed.md`
- `docs/03-architecture/master-blueprint-open-questions.md` (MBQ-27/56/64
  proposed-resolution status + links only — **not** marked accepted)

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
    total_excluded; price_include_override on account.tax; inclusive residual via
    the engine, not gross subtraction; binary-float honesty), the per-signature
    reconciliation on the **engine excluded base** with the **engine-derived
    `tax_delta_bound`** (0 only when engine-proven), and the conditional tol_tax =
    0.5r(S+O) with its labelled platform-rounding premise;
(c) the four-query Option-A contract with **all three connections in one
    `edges{ cursor node }` shape**, every current-state/tax-evidence guard field in
    the query, the shipping refund/removal gate, the `execute_business` AST guards,
    and provisional page sizes + cost telemetry;
(d) MBQ-27 mapped/matched-account.tax under the guard with the §5.5 safety **and
    the composite `shopify_tax_evidence_key`** (rate+title+source+channelLiable+
    inclusion; collision → hold — a rate-only key gives correct total/wrong tax);
(e) the closed policy-skip set — divergent currency; refunded/removed **product**;
    refunded/removed/modified **shipping**; **duty-first** duties then additional
    fees (fee-name potentially-PII); **nonzero** cash rounding; **nonzero tip**
    (`unsupported_tip_tax_treatment`); test; pre-cancelled — via the
    conditional/coordinated core skip seam (terminal-state-respect guard recommended).

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
