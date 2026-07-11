# Final MVP UAT Plan — Executable Scenario Catalogue, Entry/Exit Criteria, Evidence Rules

> **Status: Proposed for ChatGPT review. NOT accepted. No scenario has
> been executed; nothing here claims a pass.** Produced 2026-07-10
> (AR-042 candidate); **revised 2026-07-11** by the PR #148 revision
> session per ChatGPT's control-room review (comment `4942966937`,
> item 11): severity rules now split cosmetic copy defects from
> functional UX/accessibility/performance defects (§5 — the latter
> can block release); twelve experience/coverage scenarios added
> (§1.1, 25–36) with pass/fail criteria tied to
> `../03-architecture/premium-ui-ux-design-system.md` ("DESIGN
> SYSTEM") and `../03-architecture/performance-budgets.md` (PB rows);
> §7's no-numeric-pass/fail posture is superseded. Supersedes-in-function
> the historical `mvp-uat-scenarios.md` scenario *plan* (that file's
> 15 scenarios are preserved by number and extended here; the file
> itself stays unedited as the historical record) and advances
> `uat-readiness-gap-analysis.md` from a 0/15 baseline re-baseline to
> the executable end-state plan. Execution remains
> **[External validation required]** — human reviewer + interactive
> runtime + live store (blockers U-1..U-4; U-4 closes at Area 6, U-3
> at U1/U3, U-2 at VAL-B2, and U-1 — no interactive runtime available
to sessions — closes only when the human-operated Odoo.sh branch
database session is actually convened for execution: an
organizational act carried by the §6 entry criteria, not a merge).

## 1. Scenario catalogue (final: 36 scenarios)

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

### 1.1 Experience & coverage scenarios (added 2026-07-11, review item 11)

| # | Scenario | Covers | Pass criteria (numeric/checkable) |
| --- | --- | --- | --- |
| 25 | Controlled inventory baseline: preview → confirm → apply; replay refused; audit complete | Task 013B | Run record + per-pair prior/new evidence; second run excluded/refused; unconfirmed apply provably blocked |
| 26 | Basic media export: add + replace on a disposable product; foreign media survives everything | Task 015B | Foreign image untouched (before/after screenshots); replacement never leaves product imageless; FAILED status routes to review |
| 27 | Dashboard performance + hierarchy | DESIGN SYSTEM §9; PB-2/PB-3 | First useful render ≤ 1.5 s p75 (RD-1) / ≤ 2.5 s (RD-2); interactions ≤ 200 ms p75; lead answer + ≤3-exception region present; no nine-card grid |
| 28 | Long lists: Sync Center + Error Center at 10k and 100k jobs/logs | PB-4/PB-5/PB-9/PB-11 | Loads within budget at both scales; server pagination verified (no full-table fetch); filters responsive |
| 29 | Keyboard & accessibility walkthrough | DESIGN SYSTEM §12; WCAG 2.2 rows (captures-11 §13) | Every primary flow completable keyboard-only; focus visible everywhere; contrast table pass; targets ≥ 24px |
| 30 | Responsive layout + RTL smoke | DESIGN SYSTEM §10 | Usable at 375/768/1366 px, no horizontal scroll; primary answer visible at 360 px; Arabic-locale dashboard mirrors without breakage |
| 31 | Reduced motion | DESIGN SYSTEM §8 | With prefers-reduced-motion: non-essential animation gone; state changes instant; spinners remain |
| 32 | High-fidelity setup flow (wizard end-to-end) | U2; D-012-7 policy choice | Operator completes connect→readiness→policy choices without documentation; confirmation-policy is demanded (import provably holds while unset); no dishonest state shown |
| 33 | Error Center recovery usability | Error contract; Area-6/SEC-1 services | An operator (not the developer) recovers each planted failure class from the screen alone: reason+fix+owner understood, retry/cancel/resolve round trips incl. `skipped` recovery; zero dead ends |
| 34 | Large matching datasets | Task 011B; PB-13/14; U3 matching center | Match latency ≤ 50 ms p95 at 100k partners; matching center list behavior at 5k pending matches within PB-4-equivalent budget; ambiguity resolution round trip |
| 35 | Visual consistency audit | DESIGN SYSTEM §13 checklist | V-1..V-12 executed against every shipped surface; zero violations or each explicitly waived with reason |
| 36 | Lite/Full menus & permission behavior (extends 23/24) | Packaging §5; SEC-1 | Menus exactly match installed modules; flags-off empty states explain themselves; SEC-1 negative spot checks from the UI context (direct RPC state write denied) |

Per-scenario specification rule (applies to 16–36; 1–15 keep their
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
| 4 (experience) | 27, 28, 29, 30, 31, 33 after U1; 32 after U2; 34, 35, 36 after U3; 25 after 013B; 26 after 015B | Rolling — each scenario unlocks with its named prerequisite; all must complete before exit (§6) |

(Wave 1/2 split is scheduling convenience — both unlock together;
kept separate so order scenarios can be deferred if the reviewer's
session is short. Wave 4 interleaves with 1–3 as prerequisites land.)

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

## 5. Defect severity and gating (REVISED 2026-07-11 — UX failures can block release)

- **S1** — data loss/corruption/duplicate business record:
  release-blocking, immediate stop.
- **S2** — guard bypassed or silent failure: release-blocking.
- **S2-UX (new class, release-blocking on the same footing as S2):**
  functional experience failures for a product whose premium
  operator experience is a primary differentiator —
  (a) misleading health/status display (dashboard or readiness says
  healthy when it is not, or vice versa);
  (b) a primary action inaccessible (unreachable, permanently
  disabled without explanation, or keyboard-unreachable);
  (c) an unusable recovery flow (a planted failure an operator cannot
  recover from the screen — scenario 33's bar);
  (d) broken responsive layout (scenario 30's bar violated);
  (e) severe performance degradation (a PB budget missed by > 2× with
  no accepted waiver);
  (f) broken keyboard operation or focus loss (scenario 29);
  (g) contrast/accessibility failure against the DESIGN SYSTEM §12
  acceptance rows;
  (h) a misleading destructive-action preview (preview shows less
  than the apply would do).
- **S3** — wrong classification/status, missing audit trail, or a PB
  budget missed by ≤ 2×: blocking unless ChatGPT explicitly waives
  with reason.
- **S4** — **cosmetic copy/label/visual-polish issues with no
  functional or comprehension impact**: recorded, non-blocking.
  (The old rule classed *all* UX issues S4 — superseded; only
  genuinely cosmetic ones remain here.)

Any S1/S2/S2-UX → the owning task reopens via a new gate act (never
patched ad hoc).

## 6. Entry / exit criteria

**Entry:** all wave-required merges runtime-green; VAL-B2 passed
(recorded); concurrency plan §13 executed at topology A minimum
(recorded) — or an explicit dated ChatGPT waiver naming what UAT is
allowed to proceed without; fixture set seeded; reviewer briefed on
the evidence rule. **Exit (UAT complete):** every scenario in the
executed waves has a recorded verdict; zero open S1/S2; S3s waived
explicitly or fixed; evidence archive complete; UAT summary appended
to the release checklist run.

## 7. Performance & concurrency measurements (REVISED 2026-07-11 — numeric pass/fail)

Scenarios 27/28/34 carry numeric pass/fail against the named PB rows
of `../03-architecture/performance-budgets.md` (the
"no numeric pass/fail in UAT" posture is superseded — a missed budget
is an S3, > 2× an S2-UX, per §5). The Wave-1 session additionally
records: scan-to-imported latency for a 50-order batch (vs PB-18/19),
drain throughput (PB-19), dashboard load at RD-1/RD-2 (PB-2).
Concurrency: UAT runs after (or alongside) the concurrency plan's
scenarios — UAT itself adds the two-operator double-retry case (same
failed job retried by two users — one wins, one no-ops, audit shows
both). All measurements land in the budgets file's calibration
column (its §5 recalibration rule).
