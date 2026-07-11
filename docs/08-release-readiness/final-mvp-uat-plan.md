# Final MVP UAT Plan — Executable Scenario Catalogue, Entry/Exit Criteria, Evidence Rules

> **Status: Proposed for ChatGPT review. NOT accepted. No scenario has
> been executed; nothing here claims a pass.** Produced 2026-07-10
> (AR-042 candidate). Supersedes-in-function the historical
> `mvp-uat-scenarios.md` scenario *plan* (that file's 15 scenarios are
> preserved by number and extended here; the file itself stays
> unedited as the historical record) and advances
> `uat-readiness-gap-analysis.md` from a 0/15 baseline re-baseline to
> the executable end-state plan. Execution remains
> **[External validation required]** — human reviewer + interactive
> runtime + live store (blockers U-1..U-4; U-4 closes at Area 6, U-3
> at U1/U3, U-2 at VAL-B2, and U-1 — no interactive runtime available
to sessions — closes only when the human-operated Odoo.sh branch
database session is actually convened for execution: an
organizational act carried by the §6 entry criteria, not a merge).

## 1. Scenario catalogue (final: 24 scenarios)

Scenarios 1–15 stand as written in `mvp-uat-scenarios.md` (titles
recapped in the wave table §2). New scenarios added by this plan:

| # | Scenario | Domain | Covers |
| --- | --- | --- | --- |
| 16 | Product ambiguous match routed to manual review and resolved by a Reviewer (blocked → matching center → bind → retry → succeeded) | product | The shipped Task-010 manual-review path (gap-analysis item 2) |
| 17 | Ambiguous customer match resolved via candidate evidence (order held pre-creation → customer bound → retry → SO created) | sale | Task 011/012 D-012-4 (gap-analysis item 3) |
| 18 | Divergent-currency and duties orders are skipped by policy with complete evidence and operator visibility | sale | DEC-020 / D-012-3 |
| 19 | Whole-order-hold on unmatched product line resumes automatically after the product is bound | sale | Accepted hold rule end-to-end |
| 20 | Inventory first-push guard: preview → confirm → push; unconfirmed pair provably blocked | inventory | D-013-4 (destructive_write_guard_blocked) |
| 21 | Fulfillment ambiguous outcome: simulated timeout → verification read adopts the created fulfillment, no duplicate | fulfillment | D-014-7 (RA-014 mechanics) |
| 22 | Controlled export: preview enumerates a would-be-deleted Shopify variant; apply blocked until explicitly confirmed | product_export | D-015-3/5 |
| 23 | Lite/Full boundary: Lite install has no write surface (menus, jobs, scopes); installing Full modules on a populated Lite database adds them cleanly; flags-off disables enqueue | packaging | Packaging proposal §6 matrix (`../02-product/lite-full-packaging-final-proposal.md`, the DEC-029 carrier) |
| 24 | Permission matrix: Auditor read-only everywhere; Operator cannot resolve manual-review; Reviewer cannot edit settings; Admin only sees credential entry (masked, no read-back) | cross | MBQ-44/45 enforcement |

Per-scenario specification rule (applies to 16–24; 1–15 keep their
written steps): each is executed from the written Given/When/Then in
its packet section (cross-referenced), with **prerequisites** (module
set, store state, seeded data), **test data** (named fixtures below),
**expected Odoo results** (records/states/logs — field-level),
**expected Shopify results** (admin-visible state — screenshot),
**negative variant** (at least one per scenario: the same flow with
the guard/permission/duplicate condition triggered), and **evidence**
per §4.

## 2. Waves and blockers (updated)

| Wave | Scenarios | Executable after |
| --- | --- | --- |
| 1 | 1, 2, 3, 4, 5, 12, 13, 14, 15, 24 | Task 012 + Area 6 + UI-U1 merged; VAL-B2 passed; interactive runtime session |
| 2 | 6, 7, 8, 17, 18, 19 | (same — order scenarios need Task 012 which Wave 1 already requires) |
| 3 | 9, 10, 11, 16, 20, 21, 22, 23 | Tasks 013/014/015 + U3 screens merged (16 moved here from Wave 1 — its resolution step runs through the U3 matching center, which U1 alone does not ship) |

(Wave 1/2 split is scheduling convenience — both unlock together;
kept separate so order scenarios can be deferred if the reviewer's
session is short.)

## 3. Test data (named fixture set, seeded on the dev store + Odoo)

`UAT-P1` simple product (SKU UAT-SIMPLE-001); `UAT-P2` 3-option/6-variant
product; `UAT-P3` product with duplicate SKU on two Shopify products
(ambiguity source); `UAT-C1` customer with unique email; `UAT-C2/C3`
two customers sharing a normalized email (ambiguity); `UAT-O1` simple
paid order (P1×2, C1); `UAT-O2` order with line discount + order
discount + shipping + tax; `UAT-O3` guest order (no customer, email
present); `UAT-O4` presentment≠shop currency order; `UAT-O5` order
containing an unmatched SKU; `UAT-O6` order with tip; multi-location
store layout (2 Shopify locations, 1 mapped); `UAT-F1` partial
delivery + backorder flow. Seeding steps are operator instructions in
the execution session (dev store, Bogus Gateway), not code.

## 4. Evidence template (per scenario)

```text
Scenario #<n> — <title>   Date/operator: …
Environment: Odoo.sh branch db <…> · Shopify dev store <…> · API 2026-07
Preconditions verified: <list>
Steps executed: <as written / deviations>
Odoo evidence: <record ids, states, job ids + verbatim log lines>
Shopify evidence: <admin screenshot refs / GraphQL read results>
Negative variant result: <…>
Verdict: PASS / FAIL (reason) / BLOCKED (blocker id)
Defects raised: <ids or none>
```

Pass rule: the reviewer executes the steps as written; a pass may only
be recorded by the executing reviewer (unchanged rule). Evidence files
land under `docs/05-qa/uat-evidence/` (created at execution time).

## 5. Defect severity and gating

S1 data loss/corruption/duplicate business record — release-blocking,
immediate stop; S2 guard bypassed or silent failure — release-blocking;
S3 wrong classification/status or missing audit trail — blocking
unless ChatGPT explicitly waives with reason; S4 UX/copy/label —
recorded, non-blocking. Any S1/S2 → the owning task reopens via a new
gate act (never patched ad hoc).

## 6. Entry / exit criteria

**Entry:** all wave-required merges runtime-green; VAL-B2 passed
(recorded); concurrency plan §13 executed at topology A minimum
(recorded) — or an explicit dated ChatGPT waiver naming what UAT is
allowed to proceed without; fixture set seeded; reviewer briefed on
the evidence rule. **Exit (UAT complete):** every scenario in the
executed waves has a recorded verdict; zero open S1/S2; S3s waived
explicitly or fixed; evidence archive complete; UAT summary appended
to the release checklist run.

## 7. Performance & concurrency observations (during UAT, not gates)

Wave-1 session records: scan-to-imported latency for a 50-order
batch; drain throughput (jobs/pass); dashboard load with 1k jobs.
Concurrency: UAT runs after (or alongside) the concurrency plan's
scenarios — UAT itself adds the two-operator double-retry case
(same failed job retried by two users — one wins, one no-ops, audit
shows both). These feed release-hardening budgets (ARCH §5.11); no
numeric pass/fail in UAT.
