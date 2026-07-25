# Wave 5 U1 — Validation Results (fulfillment operator experience)

> **Status: Evidence record. Docs + evidence only — NOT an acceptance.**
> Produced 2026-07-25 on `fable/wave-5-completion`, branched from the bound base
> `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d`.
> This session implemented U1 and therefore **may not review, accept,
> ready-mark or merge it** (CLAUDE.md §13). Independent Claude review at the
> exact SHA is required, then a separate closure session.

## 1. Environment (recorded, not assumed)

`[Fact — captured by `tools/run_connector_suite.sh` into `ci-artifacts/summary.json`]`

| Item | Value |
| --- | --- |
| Odoo | `30bde9ff758834a4912c5ae55843d3a7dad849f1` — the exact commit pinned in `tools/odoo-pin.txt`, verified on every run |
| Odoo release | 19.0 |
| PostgreSQL | 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1) |
| Python | 3.12.3 |
| Browser | Chromium 141.0.7390.37 (Playwright, `/opt/pw-browsers/chromium-1194`) |
| Modules under test | `shopify_connector_core,_product,_sale,_inventory,_fulfillment` + `account,stock` |
| Shopify operations | **none** — no credential, request, mutation or webhook at any point |

**Evidence class `[Fact]`:** this is a **local reproduction on the same pinned
Odoo commit as the prior campaigns**, so the numbers are directly comparable. It
is **DEC-041 D8 supporting evidence**. It is **not** Odoo.sh, and the exact-SHA
**Odoo.sh run remains the Tier-1 acceptance authority**. Nothing here may be
recorded as wave acceptance.

## 2. Automated test results

### 2.1 Focused fulfillment suite (U1 batch)

| Run | Command | Result |
| --- | --- | --- |
| Fresh install + fulfillment tests | `odoo-bin -d u1_test -i shopify_connector_fulfillment,account,stock --test-enable --test-tags '/shopify_connector_fulfillment'` | **0 failed, 0 errors of 327 tests** (exit 0) |

### 2.2 Full connector suite (cross-wave regression, Waves 1–5)

Executed through the repository's own harness `tools/run_connector_suite.sh`, so
the same command reproduces on a laptop and in CI.

Run at the post-fix head `5e50aa1c0c29851c74fa8ea0d191f12b5fbc7889`, clean
worktree, Odoo pin verified:

| Pass | Result |
| --- | --- |
| Fresh install + standard suite | **0 failed, 0 errors of 1563 tests** |
| Warm `-u` update + standard suite | **0 failed, 0 errors of 1563 tests** |
| Non-standard tag suite (the eight `-standard` classes, incl. the four genuine concurrency proofs and the 100k-partner benchmark) | **0 failed, 0 errors of 18 tests** |

Fresh and warm are reported separately on purpose: issue #193 established that a
green fresh install says nothing about the warm-upgrade path. Both were run.

**Artifact identity `[Fact]`:** `connector_sha` = `5e50aa1c...`,
`connector_worktree_dirty` = `false`, `odoo_pin_verified` = `true`. Every commit
after `5e50aa1` on this branch is **docs-only**: the `addons/` tree is
byte-identical at `5e50aa1` and at the branch head
(`b301e577f5d10b3a000a48d421752114abd2fc1a`), so these results describe the code
in the current head exactly. A durable copy of the summary is committed at
[`evidence/u1-browser-2026-07-25/connector-suite-summary.json`](evidence/u1-browser-2026-07-25/connector-suite-summary.json).

Durable artifacts: `ci-artifacts/summary.json`, `ci-artifacts/fresh.log`,
`ci-artifacts/warm.log`, `ci-artifacts/nonstandard.log`. Each records the tested
checkout SHA, the declared source head, worktree cleanliness, the Odoo pin, and
the Python/PostgreSQL versions.

### 2.3 One regression found and fixed — SEC-2 invariant

`[Fact]` The first full-suite run at `35aba50` returned **1 failed of 1563** in
**both** the fresh and warm passes:

```
TestSec2Roles.test_connector_user_grants_no_acl_of_its_own
AssertionError: group_shopify_connector_user must own no ir.model.access row;
found ['shopify.connector.fulfillment.review.release.wizard']
```

**This was a real defect in the U1 batch, not a flaky test.** SEC-2's
purely-additive property requires that every right reach the customer-facing
roles through implied-group closure, never through a direct ACL grant on the
role itself — a direct grant would be a second, divergent source of truth.

**Fix (`5e50aa1`):** the release-wizard ACL was re-keyed from
`group_shopify_connector_user` to `group_shopify_connector_reviewer`, which is
what the server action already requires (Reviewer **or** Administrator). Both
customer-facing roles still reach it, because both imply Reviewer, so operator
behaviour is unchanged while the additive property is restored.

**Regression proof:** §2.2's numbers are the **post-fix** re-run. The failing
assertion is part of the standing suite and now passes.

### 2.4 Deterministic performance comparison — base vs head

`[Fact]` The existing `tools/perf0_baseline.py` harness was run **twice on the
same machine, same pinned Odoo, same PostgreSQL**: once against the base SHA
`87f1763a` (in a `git worktree`, its own fresh database) and once against the U1
head (its own fresh database). 15 scenarios, 1 warm-up discarded, 3 timed
repetitions.

Durable reports:
[`perf0-at-base-87f1763a.json`](evidence/u1-browser-2026-07-25/perf0-at-base-87f1763a.json)
and [`perf0-at-u1-head.json`](evidence/u1-browser-2026-07-25/perf0-at-u1-head.json).

**The deterministic result: query count per repetition is IDENTICAL on all 15
scenarios.**

| Scenario | queries/rep base → head | p50 ms base → head |
| --- | --- | --- |
| `job_enqueue` | 53 → 53 | 41.5 → 46.7 |
| `job_drain` | 1 → 1 | 0.57 → 0.66 |
| `layer2_intent` | 303 → 303 | 207.8 → 211.2 |
| `layer2_outcome` | 404 → 404 | 258.3 → 268.9 |
| `layer2_reconcile` | 1 → 1 | 0.46 → 0.52 |
| `order_binding_projection` | 7 → 7 | 4.12 → 6.28 |
| `inventory_pair_projection` | 7 → 7 | 4.41 → 3.94 |
| `fulfillment_evidence_projection` | 7 → 7 | 4.97 → 5.02 |
| `order_scan_admission` | 5 → 5 | 3.08 → 3.07 |
| `inventory_push_scan_admission` | 7 → 7 | 5.20 → 5.46 |
| `fulfillment_reconciliation_admission` | 12 → 12 | 7.37 → 6.48 |
| `fulfillment_ledger_reconcile` | 3 → 3 | 2.82 → 4.30 |
| `binding_lookup` | 50 → 50 | 16.9 → 20.2 |
| `lock_skiplocked` | 1 → 1 | 0.46 → 0.40 |
| `job_claim_contention` | 1 → 1 | 1.03 → 1.05 |

`residue_failures: []` and `shopify_operations: "none"` on **both** runs.

**How to read this.** Query count is deterministic and is the meaningful signal:
identical counts everywhere mean U1 adds **no backend query to any measured
path**, which matches the diff (U1 adds views, menus, two `TransientModel`
wizards that execute only while a dialog is open, and tests). The p50 deltas
scatter in **both** directions (−12.7% to +52.7%) on a shared machine that was
running CI and other work concurrently, with only 3 repetitions — that is
**noise, not signal**, and no latency delta here should be read as a regression
or an improvement.

**A false finding was caught and corrected during this work `[Fact]`.** The
first head run crashed part-way (`pg_stat_statements` was not preloaded) *after*
seeding, leaving **1 store** behind. Re-running against that same database
produced apparent regressions of up to **+68%** with *different* query counts on
the three per-store admission scenarios — because those scans iterate stores, so
the leftover row was extra work. Comparing against a genuinely fresh database
removed the difference entirely. The contaminated numbers are **not** reported
as a finding. This is the same failure mode the stabilization campaign recorded
for PERF-0 ("residue claims excluded business fixtures"): residue silently
becomes measurement.

**No number above is a guarantee, budget, threshold or SLA.** Every scenario
carries the harness's own `BASELINE ONLY -- no accepted threshold exists (issue
#199)` status, #199 stays open, and the harness records that the per-record
reconciliation **handlers** perform Shopify reads and are therefore **not
measured** — no fake transport was introduced.

## 3. Driven browser / render evidence — PRODUCED, NOT DEFERRED

`[Fact]` Real Chromium against a real Odoo 19 HTTP server rendering the real U1
screens on a seeded database. Harness output:
`ci-artifacts/u1-browser-evidence.json`. **34 checks, 0 failed, 13 screenshots.**

The U1 locked prompt forbids auto-deferring this class. **No browser class is
recorded as deferred, and none is recorded as passed without execution.**

### 3.1 Screenshot set — `ci-artifacts/u1-screenshots/`

| # | Screenshot | Role | Shows |
| --- | --- | --- | --- |
| 01 | `01-user-review-workspace.png` | Connector User | Review workspace, default "needs a decision" filter |
| 02 | `02-user-review-form.png` | Connector User | Review case form — the delivered-inconsistency case |
| 03 | `03-user-settings-no-mode.png` | Connector User | Fulfillment settings **without** any operating-mode field |
| 04 | `04-user-fulfillments.png` | Connector User | Fulfillment binding list with carrier |
| 05 | `05-user-fulfillment-jobs.png` | Connector User | Fulfillment job screen |
| 06 | `06-user-empty-state.png` | Connector User | Empty state |
| 07 | `07-user-review-mobile-390.png` | Connector User | 390 px viewport |
| 08 | `08-admin-settings-mode.png` | Administrator | Settings list with operating mode |
| 09 | `09-admin-settings-form.png` | Administrator | Settings form with the switch button |
| 10 | `10-admin-mode-switch-dialog.png` | Administrator | Mode-switch confirmation dialog |
| 11 | `11-admin-review-workspace.png` | Administrator | Review workspace |
| 12 | `12-admin-review-rtl.png` | Administrator | Same screen rendered RTL |
| 13 | `13-outsider-permission-denied.png` | No connector group | Refusal |

### 3.2 What the browser run proved

| Area | Check | Result |
| --- | --- | --- |
| Render | Every U1 screen builds and paints for both roles | PASS |
| Status layers | A4 and A7 render as **separate labelled layers**; the A7 column and group are labelled "display only" | PASS |
| Delivered | Every rendered "Delivered" string is qualified ("per carrier … the Odoo delivery is **not validated**") | PASS |
| A2 | No `FulfillmentOrderStatus` surface anywhere | PASS |
| Role visibility | A Connector User receives **no** operating-mode field and **no** switch button; an Administrator receives both | PASS |
| Permission state | A user outside every connector group is refused and sees no evidence data | PASS |
| **SEC-3 quarantine (live)** | The quarantined evidence row never appears in any list, and the wizard's "review cases currently open" reads **3** where **4** rows exist — the withheld row drops out of the count in the running UI | PASS |
| **Company isolation (live)** | The second company's name, order GID and fulfillment GID appear nowhere in any rendered page | PASS |
| Redaction | `shopify_idempotency_key`, `preconditions_snapshot`, `mode_switch_nonce`, `remote_mutation_intent` appear nowhere in rendered HTML | PASS |
| Empty state | Does not assert "there are none"; carries the withheld-records caveat | PASS |
| Wizard | Dialog opens with `role="dialog"`; consequences are static; counts are labelled "indicative … not a complete count" | PASS |
| Responsive | 390 px: `scrollWidth == clientWidth` (390) — no horizontal page overflow | PASS |
| RTL | `dir="rtl"`: `scrollWidth == clientWidth` (1440) — no horizontal overflow | PASS |
| A11y | `role="dialog"` on the modal, `role="status"` on alert regions, an `h1` per screen, severity carried by **words** (state and reason columns) not colour alone | PASS |

### 3.3 Browser classes NOT executed — stated honestly

- **Odoo HOOT / `tour` JS suites** were **not** executed. U1 adds no Owl or JS
  surface (PD-7 excludes fulfillment), so there is no tour bundle to run. This
  is recorded as **NOT APPLICABLE — NOT EXECUTED**, never as passed.
- **Formal automated axe/WCAG audit** was **not** executed. The accessibility
  checks above are structural assertions driven in a real browser, not a full
  WCAG conformance audit. Recorded as **PARTIAL — structural only**.

## 4. Acceptance matrix A1–A23 status

| Rows | Evidence | State |
| --- | --- | --- |
| Action wiring, sanctioned-surface, no-business-logic (incl. A6/A15/A21) | `test_ui_actions.py`, `test_ui_source_guards.py` | **Proven** |
| Two-role visibility + internal closure + negative direct-RPC (A4/A5) | `test_ui_visibility_matrix.py` + browser §3.2 | **Proven** |
| Package import structure (A20) | `test_ui_import_structure.py` | **Proven** |
| Status-badge layer correctness (A22) | `test_ui_source_guards.py` + browser §3.2 | **Proven** |
| SEC-3 closure (A23) | `test_ui_sec3_scope.py` — hooked into the authoritative `TestSec3InventoryCompleteness._durable_store_scoped_models` discovery, so U1 cannot drift from SEC-3's own definition | **Proven** |
| Whole-connector regression (A19) | §2.2 full suite | **Proven (D8 supporting)** |
| Premium fidelity / screenshot set | §3 | **Produced** |
| **Exact-SHA Odoo.sh runtime** | — | **NOT PRODUCED — required before U1 acceptance** |
| **Live-Shopify behaviour** | — | **DEFERRED and UNCLAIMED** (Gate D, CV-013 #185, #200) |

## 5. Declared deviations from the locked prompt

Both are declared here for the control room to ratify or reject. Neither was
made silently.

1. **A second wizard module.** The locked allowed-file list names one wizard
   (`..._mode_switch_wizard.py`), but task-breakdown S4 requires the review
   workspace to expose `action_release_fulfillment_review`, which takes a
   **mandatory** operator reason and therefore needs a transient form; the core
   job-cancel and mutation-resolution wizards are bound to their own models and
   cannot be reused. `wizards/shopify_connector_fulfillment_review_release_wizard.py`
   was added deliberately. **Assessment:** an omission in the packet's
   allowed-file list, not a decision to drop the action.
2. **The frozen test-file allowlist was extended.**
   `test_fulfillment_source_guards.py` pins an exhaustive test-file set; the six
   `test_ui_*` modules the locked prompt authorises had to be added or the batch
   would fail its own boundary guard. The set remains exhaustive and still fails
   on any file not named in it.

## 6. Scope limitation recorded honestly

**Carrier tracking chips are not rendered.** The canonical §12 matrix sources A5
carrier milestones from a **parsed** `tracking_snapshot`, but parsing requires a
computed field on `models/**`, which U1 must not add. Rather than dump raw JSON
(forbidden) or invent a badge without a backing field (forbidden), U1 renders
**only** the `delivered_inconsistency` case, which has a real scalar backing
field, and says so on the screen. A parsed tracking read seam is a **separate
backend task** for the control room to schedule.

## 6a. P3 findings from the rendered evidence — recorded, not fixed

Reviewing the screenshots rather than only the assertions surfaced one genuine
minor defect. It is **not** fixed here because fixing it would require a
forbidden path.

**P3-U1-1 — connector many2one columns render an unhelpful label.** In the
review workspace list (screenshot 01) the *Order* column shows
`shopify.connector.orde…` rather than a recognisable order reference, because
`shopify.connector.order.binding` declares no `_rec_name` and no
`_compute_display_name`, so Odoo falls back to the model name. The same applies
wherever U1 renders a connector binding as a many2one.

- **Impact:** cosmetic but operator-visible — the column is not useful for
  identifying a row at a glance. No data is wrong and nothing is misleading
  about status, security or stock.
- **Why it is not fixed here:** the fix belongs on the binding models in
  `shopify_connector_sale` / `_fulfillment` (`models/**`), which the U1 locked
  prompt forbids this batch from touching. Adding a UI-side workaround would
  mean duplicating a label rule in the view layer — exactly the
  business-logic-in-the-UI pattern U1 must not introduce.
- **Recommendation:** a small, separate backend task giving the connector
  bindings a `_rec_name` or `_compute_display_name` (e.g. the Shopify order
  name plus the store). It would improve U0 and U1 together.

## 7. Rollback

One revert of the single merge commit restores the exact prior behaviour. The
batch is additive: views, menus, one `wizards/` package, two ACL rows and test
files — **no schema change, no data migration, no new durable model, no change
to any existing model, field or selection**. A warm `-u` of
`shopify_connector_fulfillment` after the revert removes the U1 views and menus.
See `docs/07-implementation-plan/wave-5-u1-gate-a/u1-rollback-strategy.md`.

## 8. Not claimed

No gate accepted or opened · nothing self-reviewed, self-accepted, ready-marked
or merged · no issue action (#185, #186, #197, #199, #200 unchanged) · no
Shopify credential, request, mutation or webhook · **no Odoo.sh runtime
evidence** · no live-Shopify validation · no external UAT · no release-readiness
claim · no PERF-0 number restated as a guarantee · **"Delivered" remains
suppressed** as a supported state.
