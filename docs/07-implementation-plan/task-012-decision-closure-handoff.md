# Task 012 — Order-Import Decision-Closure Handoff

> **Docs-only session handoff.** No gate opened, no code written, no live
> Shopify request. Produced by the Task 012 final pre-implementation
> decision-closure session, 2026-07-14. Follows
> [`session-handoff-template.md`](../06-prompts/session-handoff-template.md).
> The canonical `docs/01-research/research-handoff.md` top entry is a
> control-room action and is **not** modified here (that file is outside this
> session's allowed-files list).

## 1. What this session did

Produced a **decision-complete, evidence-backed Task 012 order-import packet**
so the locked prompt can be issued immediately after its prerequisites merge.
Specifically:

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
  (D-012-1 money→Char, D-012-2 tolerance-`K`, §4 full pagination, §15 locked
  prompt) and the proposed brief, and recorded **proposed-resolution status +
  links (not acceptance)** in the MBQ-27/56/64 register rows.

## 2. Corrections made (adversarial findings)

| Finding | Correction |
| --- | --- |
| Money stored as Odoo `Float` (lossy) | All binding money snapshots → **`Char`** (exact Shopify `Decimal` string), parsed via `decimal.Decimal`; shop + presentment + component snapshots |
| Line-item / nested-connection pagination could reject large orders | **Full cursor pagination** of `lineItems`/`shippingLines`/`discountApplications`; cursors never persisted; page-limit backstop; the "reject >100 lines" stance withdrawn |
| Tax tolerance ignored Odoo-19 `round_globally` default | Tolerance count `K` now **derived from the company's actual `tax_calculation_rounding_method`** |
| Divergent-currency routing risk of overloading `financial_total_mismatch` | Confirmed as terminal `skipped` **policy** (no error class); via the one named additive `JobPolicySkip` core seam |

## 3. Proposed decisions (all NOT accepted — control-room review required)

Order binding schema (§3); read-only GraphQL query contract + pagination/cost
(§4); MBQ-27 tax = mapped/matched `account.tax` under the guard, no external
tax-amount inverse at SO level (§5); MBQ-56 component tolerance with worked
examples (§6); discount representation (§7); customer/address resolution incl.
company/person + address-child gaps (§8); product/order-hold (§9); divergent
currency → `skipped` policy (§10); ORDERS_UPDATED evidence-refresh-only (§11);
job/failure + security/privacy contracts (§12–13); exact file map (§14); test
catalogue (§15).

## 4. Open dependencies (all currently unmet — this task cannot be gated until met)

1. **CORE-R2 full SRR-03 remediation** merged runtime-green (register forbids
   merging/enabling/live-validating any Shopify-calling domain handler until
   then; parallel development allowed).
2. **PR #151 — Task 010B** merged (variant bindings).
3. **PR #150 — Task 011B** merged (indexed email lookup).
4. **Task LC-1** merged / **DEC-030** accepted (the `_reassign_to_historic_job_type`
   ondelete callable).
5. **CORE-R1** merged (stores reach `connected`, for live validation).
6. Control-room acceptance of this closure + packet, the order-domain gate act,
   and prompt issuance.

## 5. Open questions carried

- Verbatim GraphQL `THROTTLED` error-code string (docs show only `200 Throttled`).
- Shopify three-decimal-currency rounding policy (undocumented) → named
  dev-store empirical check before onboarding such a store.
- `res.partner.company_name` as the sink for `MailingAddress.company` (confirm
  at build; `is_company` stays False regardless).
- `ShopifyQuiescedError → skipped` dispatcher wiring is a later CORE-R2 slice,
  not Task 012.

## 6. Files changed this session (docs-only)

- `docs/03-architecture/task-012-order-import-decision-closure.md` (**new**)
- `docs/07-implementation-plan/task-012-decision-closure-handoff.md` (**new**)
- `docs/07-implementation-plan/task-012-order-import-implementation-packet.md`
  (money→Char, tolerance-`K`, full pagination, locked prompt)
- `docs/07-implementation-plan/task-012-order-import-proposed.md` (proposed-resolution notes)
- `docs/03-architecture/master-blueprint-open-questions.md` (MBQ-27/56/64
  proposed-resolution status + links only — **not** marked accepted)

## 7. Learning feedback loop

- **Fresh official verification beats repo summaries.** The lossy-`Float`
  money bug survived earlier planning because prior captures did not force the
  `Decimal`-string consequence; a direct read of the 2026-07 `Decimal` scalar
  page made the fix unambiguous. *Lesson: for money/tax/precision, always read
  the scalar/type page, not only the object page.*
- **Odoo defaults drift between versions.** Odoo 19's tax rounding default
  flipped to `round_globally`; a fresh 19.0 source read caught it, sharpening
  the tolerance's `K`. *Lesson: re-verify version-sensitive defaults per major
  Odoo release.*
- **Reaching a terminal state from a handler needs a dispatcher seam.** The
  merged dispatcher marks any normally-returning handler `succeeded`, so a
  policy `skipped` needs the `JobPolicySkip` seam — a design constraint that
  must be encoded, not assumed. *Lesson: verify the dispatcher's success
  routing before designing any non-`succeeded` handler outcome.*

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
(b) full pagination of the three order-level connections;
(c) the component tolerance and its K-from-rounding-method derivation;
(d) MBQ-27 mapped/matched-account.tax-under-the-guard (no SO-level external
    tax-amount inverse);
(e) divergent currency → skipped policy via the JobPolicySkip seam.

Do NOT open the order-domain gate or issue the locked prompt until CORE-R2
full SRR-03 remediation, PR #151 (Task 010B), PR #150 (Task 011B), and
Task LC-1 are all merged runtime-green. If accepting, record the acceptance
in architecture-review-log.md and mark the MBQ-27/56/64 rows resolved; the
locked prompt remains unusable until the separate gate act.
```

## 9. Session completeness

Documentation-only; no code; no gate; no live Shopify request. The no-code gate
(CLAUDE.md §4–§5) remains in force. This handoff, plus the decision-closure and
the updated packet/proposed/register, constitute the deliverable.
