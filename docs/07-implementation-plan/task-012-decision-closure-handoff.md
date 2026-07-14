# Task 012 — Order-Import Decision-Closure Handoff

> **Docs-only session handoff.** No gate opened, no code written, no live
> Shopify request. Produced by the Task 012 final pre-implementation
> decision-closure session, 2026-07-14. Follows
> [`session-handoff-template.md`](../06-prompts/session-handoff-template.md).
> The canonical `docs/01-research/research-handoff.md` top entry is a
> control-room action and is **not** modified here (that file is outside this
> session's allowed-files list).

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
- **Tip tax treatment is undocumented in the Admin API** (no `TipLine`); "tips
  untaxed" is an inference backstopped by the total self-check → dev-store
  confirmation before a taxed-tip store.
- **No LineItem field distinguishes refunded from removed units** — not needed
  (the §6.0 gate fails closed on the aggregate), logged for rationale.
- Empirical confirmation of the per-tax-signature base reconciliation (§6.4a) and
  the `OC` attribution on a real mixed-discount order → named dev-store check.
- `res.partner.company_name` as the sink for `MailingAddress.company` (confirm
  at build; `is_company` stays False regardless).
- The exact core skip seam (terminal-state-respect guard vs `JobPolicySkip`) is
  settled with the CORE-R2 owner; Task 012 may need **no** core edit.
- GraphQL requested/actual query cost for the chosen page sizes — dev-store
  measured before production tuning.

## 6. Files changed this session (docs-only)

- `docs/03-architecture/task-012-order-import-decision-closure.md` (round-1 new;
  round-2 rebuilt §0/§4/§5/§6/§7/§10/§14/§15/§17/§18; **round-3** four-query §4,
  exact-source + refund gate §6.0/§6.1/§6.2, per-signature §6.4a, conditional
  bound §6.5, tip/shipping §6.1-B/C, guards §15, deps §0.1)
- `docs/07-implementation-plan/task-012-decision-closure-handoff.md`
- `docs/07-implementation-plan/task-012-order-import-implementation-packet.md`
  (money→Char, canonical ledger, Option-A pagination, cost posture, tax-mapping
  safety, conditional skip seam, locked prompt; **round-3** exact-line-total
  source, refund gate, per-signature reconciliation, conditional `tol_tax`,
  `execute_business` guards, PR-#158 deps)
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
    quantity × discountedUnitPriceSet), the canonical ledger U_ex = M + H + T
    (always tax-exclusive; shipping tax backed out once when inclusive), the
    fail-closed refund/removed gate (currentQuantity==quantity), the
    per-tax-signature base reconciliation (§6.4a), and the conditional bound
    tol_tax = 0.5r(S+O) with its labelled platform-rounding premise;
(c) the four-query Option-A contract + pagination (three independent cursors,
    torn-read handling), the `execute_business` AST guards, and the provisional
    page sizes + cost telemetry;
(d) MBQ-27 mapped/matched-account.tax-under-the-guard with the §5.5 tax-mapping
    safety (company match, ambiguous hold, fiscal-position validation);
(e) divergent currency / refunds-removed / duties / test / pre-cancelled →
    skipped policy via the conditional/coordinated core skip seam
    (terminal-state-respect guard recommended).

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
