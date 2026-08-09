# UI restructure implementation evidence — 2026-08-02

> **Evidence discipline.** This record contains only commands and results that
> actually ran. GitHub Actions is supporting evidence, not an Odoo.sh gate.
> No live Shopify mutation is authorized or claimed by this mission.

## Mission identity

| Item | Exact value |
| --- | --- |
| Repository | `AdamsOdoo/Adams` |
| Required base branch | `fable/wave-5-completion` |
| Required base SHA | `49cfffbd5ff0eca85d2b855d9ebd2e414680af8e` |
| Working branch | `codex/ui-restructure-implementation` |
| Signed-contract provenance commits on this branch | `971e6ed` (audit + contract capture); `55ffb6f` (product-owner sign-off + mission prompt) |
| Draft PR | [#206](https://github.com/AdamsOdoo/Adams/pull/206), open and draft, targeting `fable/wave-5-completion` |
| Native Odoo.sh exact-head campaign | Not run in this environment |
| Live Shopify calls or mutations | Not run |

## Batch 0 — signed design delta and implementation wireframes

**Scope.** Align the premium UX specification and prototype notes to C1, C4,
C5, C6, and C7 before production code: four-pillar navigation, distinct Sales
and Connector Health pages, five onboarding phases over twelve durable steps,
recoverable mode-switch panel, export acknowledgement component, shared states,
responsive/RTL/accessibility constraints, and visible-action consequence copy.

**Scope commit.** `bf8d80a08dd62ef18405373dc045bc74dffc8ce9`
(`docs(ui): lock restructure delta and screen wireframes`).

**Commands and results.** All commands ran from the repository root at the
scope commit's worktree state before commit:

| Command | Real result |
| --- | --- |
| `python3 -c '<relative Markdown-link existence checker>'` over the four Batch 0 files | `checked 4 Markdown files; missing local links: 0`; exit 0 |
| `rg -F -q` contract-term loop for the four pillars, both dashboard names, review disclosure, mode fields, stale state, and five onboarding phases | All required terms found; exit 0 |
| `git diff --cached --check` | Exit 0; no whitespace errors |
| `python3 -c '<12-condition C1/C2/C3/C4/C5/C6/C7/UI/action-effect assertion set>'` | `Batch 0 contract-adversarial checks: 12/12 passed`; exit 0 |

**CI.** Exact-head GitHub Actions run
[#153](https://github.com/AdamsOdoo/Adams/actions/runs/30760560925)
completed successfully for `72bbdcf01873ee6b6f664b817991d1e0a95817f1`.
The workflow verified both `connector_sha` and `source_head_sha` as that exact
commit and verified the pinned Odoo 19 source SHA as
`30bde9ff758834a4912c5ae55843d3a7dad849f1`. Real results from the run log:

| Campaign | Real result |
| --- | --- |
| Fresh install | `0 failed, 0 error(s) of 2511 tests`; 37 tour success markers; all 36 required tour tests attributed |
| Warm update | `0 failed, 0 error(s) of 2511 tests`; 37 tour success markers; all 36 required tour tests attributed |
| Migration from `50b770a3…` | `0 failed, 0 error(s) of 2511 tests`; all 36 required tours; second update also `0 failed, 0 error(s) of 2511 tests` |
| Migration from `0a15b176…` | `0 failed, 0 error(s) of 2511 tests`; all 36 required tours; second update also `0 failed, 0 error(s) of 2511 tests` |
| Nonstandard/concurrency/performance/HOOT campaign | `0 failed, 0 error(s) of 62 tests` |
| Browser evidence | `verified` by the workflow summary |

This is supporting CI evidence only. It is not the native Odoo.sh exact-head
gate and made no Shopify request.

**Adversarial pass.** The pass challenged the most likely documentation
regressions: leaving the old seven/eight-peer IA apparently authoritative;
mixing health with sales; hiding Configuration from the contract rather than
making it Administrator-only; dropping a durable onboarding step behind the
five-phase presentation; equating Accepted with Verified; omitting stale-job
mode recovery; combining currencies; and omitting mobile/RTL/action-consequence
states. The 12-condition assertion set passed. The old IA is retained only as
clearly superseded provenance behind a prominent signed-delta link. No rendered
browser run was performed or claimed because this batch contains low-fidelity
Markdown wireframe notes rather than HTML/CSS production or prototype changes.

**Revert boundary.** Revert `bf8d80a08dd62ef18405373dc045bc74dffc8ce9`
and its evidence-only successor
`72bbdcf01873ee6b6f664b817991d1e0a95817f1`, leaving the two signed provenance
commits in place. Both commits contain documentation and wireframe notes only.

**Deviations.** None currently recorded.

## Batch A — release-blocking correctness repairs (F-01, F-02, F-03)

**Scope.** The setup client follows the exact admitted location-refresh job to
terminal and exposes retryable failure evidence; fulfillment mode switching now
has durable requested/effective state, terminal cleanup, retry and normal-UI
rollback; reconciled sales totals exclude unresolved review orders and disclose
them separately. Existing job-state, mutation-evidence, company/store and
readiness contracts remain intact.

**Scope commits on the draft PR.** `242580a0fdd0620eae6ae4f855d5a4da3476d6bc`,
`5f757f8679d81ad8561015da481e834def61fb70`, and
`94bd5a69cdc2e8cadb279108f13bcf2cc7b5e614`; additive CI corrections
`78035c7daa0b963d95c6bdea115e4533339a7c9f` and
`d053a65c86954c348f51557f9aafd87484128a14`, followed by the test-only
`2f854d8c4691b0d67ec024e15ef9d11d4c4d53d5`.

**Exact-head CI history.** Failures are retained here rather than overwritten:

| Run / exact head | Real result | Disposition |
| --- | --- | --- |
| [#168](https://github.com/AdamsOdoo/Adams/actions/runs/31282086646) / `94bd5a69cdc2e8cadb279108f13bcf2cc7b5e614` | Fresh, warm and both migration paths: `3 failed, 0 error(s) of 2536 tests`; nonstandard: `1 failed, 0 error(s) of 62 tests`; browser evidence `FAILED` | Four real regression gaps: the location-refresh handler erased `ShopifyClientError` taxonomy; the mode recovery test asserted transaction state rolled back by `assertRaises`; the source guard omitted the new retry action; the dashboard HOOT fixture omitted `awaiting_review`. Corrected additively. |
| [#170](https://github.com/AdamsOdoo/Adams/actions/runs/31285148468) / `78035c7daa0b963d95c6bdea115e4533339a7c9f` | Fresh and both migration paths failed before registry load with `SyntaxError`; warm: `12 failed, 7 error(s) of 1417`; nonstandard: `1 failed, 15 error(s) of 51`; browser evidence `FAILED` | Publication defect, not accepted product evidence: the large inventory-service blob was truncated and contained the tool's truncation marker. Restored from the verified local Git blob in the next additive commit; the contaminated downstream counts are not treated as product regressions. |
| [#172](https://github.com/AdamsOdoo/Adams/actions/runs/31286024589) / `d053a65c86954c348f51557f9aafd87484128a14` | Fresh, warm, both genuine migrations and both second updates: `0 failed, 0 error(s) of 2537 tests`; nonstandard: `1 failed, 0 error(s) of 62 tests`; browser evidence `FAILED` | The restored production source is clean. The sole residual was a HOOT assertion: Batch A intentionally added the fifth “Awaiting data review” KPI but the healthy-fixture assertion still expected four cards. Corrected test-only, with an explicit zero-value assertion for the review card. |
| [#174](https://github.com/AdamsOdoo/Adams/actions/runs/31287636609) / `2f854d8c4691b0d67ec024e15ef9d11d4c4d53d5` | Fresh, warm, both genuine migrations and both second updates: `0 failed, 0 error(s) of 2537 tests`; nonstandard: `0 failed, 0 error(s) of 62 tests`; browser evidence `verified` | **Batch A exact-head gate passed.** The artifact binds checkout, connector and source-head to the exact commit, verifies the required base and Odoo pin, and records a clean worktree and zero Shopify operations. |

All three completed artifacts verify source base
`49cfffbd5ff0eca85d2b855d9ebd2e414680af8e`, exact source/head identity,
clean connector worktree, and pinned Odoo
`30bde9ff758834a4912c5ae55843d3a7dad849f1`; both record
`shopify_operations: none`. Run #174 independently repeats and passes those
checks.

**Test-count identity.** The first Batch A candidate reports 2,536 standard
tests versus Batch 0's 2,511; the corrected candidate reports 2,537 after the
error-taxonomy regression was added: a real +26 identity change from the added
correctness regressions and async browser journeys. The required tour count
moves from 36 to 38. The final mission count is recorded in Batch F; it is not
extrapolated from a failed candidate.

**Adversarial pass.** Refused admissions, duplicate refresh clicks, retryable
and final refresh failures, browser reload/resume, unexpected terminal mode
scan failure, retry, explicit Return to Mode 1, and review-flagged sales orders
were exercised by the new and existing suites. The CI correction also protects
the operator-visible error taxonomy instead of allowing a generic dispatcher
failure to hide the recoverable reason.

**Revert boundary.** Revert the six Batch A scope/correction commits above as
one unit. The final correction only restores the complete intended inventory
service source after the publication defect; reverting it alone would restore
syntactically invalid Python and is not a valid product rollback.

**Deviations.** No live Shopify or native Odoo.sh campaign was run. The first
repair publication was truncated by the remote object-publication path; that
failed head and its CI artifact are preserved above, and every later large-file
publication is byte-for-byte checked against the local Git blob before any ref
update.
