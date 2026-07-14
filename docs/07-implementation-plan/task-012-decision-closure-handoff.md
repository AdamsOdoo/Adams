# Task 012 — Order-Import Decision-Closure Handoff

> **Docs-only session handoff.** No gate opened, no code written, no live
> Shopify request. Produced by the Task 012 final pre-implementation
> decision-closure session, 2026-07-14. Follows
> [`session-handoff-template.md`](../06-prompts/session-handoff-template.md).
> The canonical `docs/01-research/research-handoff.md` top entry is a
> control-room action and is **not** modified here (that file is outside this
> session's allowed-files list).

## 0. Correction round — 2026-07-14 (control-room review `4690680028`)

The initial closure was REVISED (docs-only) for four load-bearing corrections
plus consistency items; PR #159 stays draft/unmerged:

1. **Dependency contract → capability-based** (not direct-merge of PR #150/#151):
   SRR-03 CLOSED; protected/guarded product import + complete variant bindings;
   protected/guarded customer import + indexed email matching; no unguarded
   product/customer Shopify call; LC-1 + DEC-030 — however they arrive
   (direct merge or a subsuming CORE-R2 Slice-2B integration PR). **CORE-R1 is
   already merged (satisfied, not pending).** (closure §0.1)
2. **Financial ledger rebuilt** into one canonical single-count equation
   `U_ex = M + H + T` (product/shipping/tip/discount each once; `OC` =
   order-level/code allocations only, proven no double subtraction), with
   **tax-inclusive** handling (`U_ex = G − totalTaxSet`) and a fully worked
   tax-inclusive example. (closure §6.1/§6.3)
3. **Tax bound proven** `tol_tax = 0.5r(S+O)` from both systems' rounding
   events, replacing the invalid `K = distinct groups`; added the
   many-small-lines / `round_globally` counterexample (Example I). (closure §6.4)
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
| Tax tolerance ignored Odoo-19 `round_globally` default | Corrected in the round-2 pass: **proven `tol_tax = 0.5r(S+O)`** from both systems' rounding events (the round-1 `K=distinct groups` was insufficient) + counterexample |
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

These arrive via direct merges of PR #150/#151 **or** a subsuming CORE-R2
Slice-2B integration PR. **CORE-R1 is already merged (satisfied, not pending).**

## 5. Open questions carried

- Verbatim GraphQL `THROTTLED` error-code string (docs show only `200 Throttled`).
- Shopify three-decimal-currency rounding policy (undocumented) → named
  dev-store empirical check before onboarding such a store.
- Empirical confirmation of the `OC` line-vs-order classification
  (`targetSelection==ALL`/code) on a real mixed-discount order → named
  dev-store check.
- `res.partner.company_name` as the sink for `MailingAddress.company` (confirm
  at build; `is_company` stays False regardless).
- The exact core skip seam (terminal-state-respect guard vs `JobPolicySkip`) is
  settled with the CORE-R2 owner; Task 012 may need **no** core edit.
- GraphQL requested/actual query cost for the chosen page sizes — dev-store
  measured before production tuning.

## 6. Files changed this session (docs-only)

- `docs/03-architecture/task-012-order-import-decision-closure.md` (round-1 new;
  round-2 rebuilt §0/§4/§5/§6/§7/§10/§14/§15/§17/§18)
- `docs/07-implementation-plan/task-012-decision-closure-handoff.md`
- `docs/07-implementation-plan/task-012-order-import-implementation-packet.md`
  (money→Char, canonical ledger + `tol_tax=0.5r(S+O)`, Option-A pagination,
  cost posture, tax-mapping safety, conditional skip seam, locked prompt)
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
(b) the canonical single-count ledger U_ex = M + H + T (incl. tax-inclusive
    U_ex = G − totalTaxSet) and the proven tax bound tol_tax = 0.5r(S+O);
(c) Option-A pagination (three independent cursors, torn-read handling) and the
    provisional page sizes + cost telemetry;
(d) MBQ-27 mapped/matched-account.tax-under-the-guard with the §5.5 tax-mapping
    safety (company match, ambiguous hold, fiscal-position validation);
(e) divergent currency → skipped policy via the conditional/coordinated core
    skip seam (terminal-state-respect guard recommended).

Do NOT open the order-domain gate or issue the locked prompt until the
CAPABILITY prerequisites (§0.1 / §4) hold in Shopify-connector — SRR-03 CLOSED;
protected/guarded product import + variant bindings; protected/guarded customer
import + indexed email matching; no unguarded product/customer Shopify call;
LC-1 + DEC-030 — however they arrive (direct #150/#151 merges or a subsuming
CORE-R2 Slice-2B integration PR). CORE-R1 is already merged. If accepting,
record it in architecture-review-log.md and mark the MBQ-27/56/64 rows
resolved; the locked prompt stays unusable until the separate gate act. Also
coordinate the core skip seam with the CORE-R2 owner (PR #158/#160).
```

## 9. Session completeness

Documentation-only; no code; no gate; no live Shopify request. The no-code gate
(CLAUDE.md §4–§5) remains in force. This handoff, plus the decision-closure and
the updated packet/proposed/register, constitute the deliverable.
