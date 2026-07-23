# MVP Program State — Live Tracker

> **Current live tracker — calibrated 2026-07-22.** The complete pre-calibration tracker is archived at [`archive/mvp-program-state-through-2026-07-22.md`](./archive/mvp-program-state-through-2026-07-22.md). That archive preserves the full dated audit trail. This file is intentionally concise and must remain the first current-state document a worker reads.
>
> Stable scope/sequencing: [`mvp-completion-program.md`](./mvp-completion-program.md). Review policy: [`../06-prompts/claude-mvp-wave-review-template.md`](../06-prompts/claude-mvp-wave-review-template.md). Acceptance evidence: [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md).
>
> **Role/cadence governance active — 2026-07-22.** [`DEC-039`](../04-decisions/DEC-039-mvp-claude-implementation-worker-expansion.md) and [`DEC-040`](../04-decisions/DEC-040-mvp-cadence-claude-builder-reviewer-ui-priority.md) were merged through PR #191 at governance baseline `ba4ccc2ce3c809e6168f95de63ebc5277c4c6fbb`. **Claude is the default implementation worker and default independent gate reviewer** (Sol remains an authorized secondary builder). **ChatGPT is the strategic control room** for scope, priority, timeline and hard-stop escalation, not the routine line reviewer. Iterations target a full wave or large independently-revertable slice; review scrutiny scales up with batch size. An implementing Claude session never reviews, accepts, ready-marks or merges its own PR.
>
> **PR #191 closure status.** Independent verification-only review accepted exact head `53c4197970c0bb2cd441c409f92bf069785dc16f` in PR comment `5044408909`; separate closure marked the PR ready and merged it at `ba4ccc2ce3c809e6168f95de63ebc5277c4c6fbb`. **U0 and the existing Wave 4 PR #189 continuation are now unblocked.** Wave 4 PR #189 (`claude/wave-4-fulfillment-gate-b`) originally branched from `01f072dd4d83b7b39737452a686244a3a8c00332`, remains open/draft at head `702d083262b08bc1180be642579ba41144af6c18`, and must merge the latest `mvp/program-integration` tip before correcting its two known P2 findings and starting Odoo.sh runtime. This tracker-only closure commit may sit above the PR #191 merge; workers must fetch the live branch tip rather than assume the governance merge SHA is the current ref tip.

## 1. Current program status

| Item | Current state |
| --- | --- |
| Program integration branch | `mvp/program-integration` |
| Latest accepted governance baseline | `ba4ccc2ce3c809e6168f95de63ebc5277c4c6fbb` (PR #191 merge; fetch the live branch tip for new work because tracker-only closure commits may sit above it) |
| Wave 1 | Merged and runtime-green |
| Wave 2 | Merged and runtime-green |
| Wave 3 / Task 013 | Inventory + Layer 2 implementation merged; runtime and genuine concurrency evidence accepted |
| Wave 3 residual | `CV-013` issue #185 open and critical; live Shopify inventory mutation validation still required before RC/UAT acceptance; Task 013B separately gated |
| Wave 4 Gate A | Accepted and merged through PR #188; merge SHA `01f072dd4d83b7b39737452a686244a3a8c00332` |
| Wave 4 Gate B | Odoo.sh runtime campaign executed 2026-07-22 (build `35279596`, Odoo 19.0, PG 16.14). Initial candidate `be528f2` failed 26+17 of 187 — the frozen fulfillment suite had never run on Odoo 19 (pre-19 API). **One consolidated allowlist-only correction** (13 test files + 1 prod file) → fulfillment **0/200**, sale **0/194**, inventory **0/247** green; head `bfb29d799533d1056ec68ca56fb99ef85a0b2d65`, tracker-only commit `ac122d0f8d128c53ccedadda532e87e97109d307`. **Control room accepted this as Stage R1 evidence (PR #189 comment `5045580551`) and disclosed a new P1**: the out-of-band concurrency harness's `run_concurrent_inconclusive_increment`/`run_operation_scope_serialization` scenarios were hard-coded `ok: True` stubs. **Stage R2A correction (this batch):** both stubs replaced with genuine spawned-process/independent-transaction scenarios; six further frozen-concurrency-family scenarios added (duplicate picking/tracking admission, reconciliation-replacement race, review-release race, mode-switch interaction, rollback-injection recovery); the static no-fake-success guard strengthened (AST-only, verified to reject the disclosed stub shape and the pre-correction file, and to accept genuine orchestration). Classification `IMPLEMENTED — EXACT-SHA ODOO.SH EXECUTION PENDING`; no scenario executed against a live DB this session (no Odoo runtime available here). Core/product out-of-allowlist regression classification and the exact-head Odoo.sh rerun remain open from Stage R1. Draft/unmerged; no self-review/ready-mark/merge; no live Shopify mutation. Gate D / CV-013 (#185) remain `NOT PROVEN` / open. Evidence: `docs/05-qa/task-014-fulfillment-tracking-validation-results.md` § STAGE R2A. Awaiting a fresh exact-head Odoo.sh build and independent Claude Tier 1 review **Base reconciliation (2026-07-22):** the U0-advanced integration tip `dd0af5d94a7f730e738dca955971e00bb4cc9122` (containing U0 merge commit `8818c7714f46eefe51c6b452b5e3f24d155f26fb`) has been merged into `claude/wave-4-fulfillment-gate-b` via one normal (`--no-ff`) merge commit, per control-room ruling PR #189 comment `5050760923`. The prior exact head `151e4f408c50a55188cbc618c60efc3135c3459b` is now historical and is **not** a runtime candidate; the new reconciled merge head is the only future Odoo.sh candidate for PR #189. Only static/source validation was performed in the reconciliation session — **no Odoo.sh runtime was executed or is claimed** for the reconciled head. Issue #193 (baseline warm-update fixture defect) remains the separate owner of the baseline errors; issue #185 (CV-013) remains open and critical. No Shopify request or mutation occurred; PR #189 remains draft/unmerged with no final acceptance. **Independent Tier-1 review (2026-07-23) of exact head `2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a` returned `REVISE`** (PR #189 comment `5058257403`) — 2 confirmed P0s (tracking-write transaction poisoning; Mode-2 partial-fulfillment whole-picking over-validation), 9 P1s, 13 material P2s. Control room accepted the `REVISE` verdict and ordered a synthesis reset before any correction (comment `5058826143`). **Synthesis reset complete (2026-07-23, docs-only):** all 24 findings independently re-verified against exact source, count discrepancy (24 vs. reviewer's own 25/26 headline mentions) resolved, 13 root-cause themes built, one locked (not-yet-authorized) correction prompt drafted. See `docs/05-qa/wave-4-tier1-findings-ledger.md`, `docs/07-implementation-plan/wave-4-tier1-correction-synthesis.md`, `docs/06-prompts/wave-4-tier1-correction-locked-candidate.md`, `docs/07-implementation-plan/wave-4-tier1-synthesis-handoff.md`. **`TIER-1 FINDINGS SYNTHESIZED — CORRECTION NOT YET AUTHORIZED.`** No correction implemented; no Odoo.sh runtime executed; no Shopify operation; PR #189 remains draft/unmerged, not self-accepted. PR #194 (Wave 5 U1 Gate A) is dependency-frozen pending a corrected Wave 4 head. |
| Wave 5 | Full wave not started. **U0 (first usable operator UI) implementation candidate** on branch `claude/u0-operator-ui-foundation` from base `1e2e5c25` (DEC-039/040 builder authority): navigation, read-only aggregate dashboard, stores/readiness, Sync Center, Error & Review Center, logs, mutation evidence, safe retry/cancel/review/resolve actions. Static-validation green. **Stage R1 Odoo.sh runtime campaign (PR #192) EXECUTED on the corrected working tree, `EXECUTED — PASS — PRE-REBUILD`:** found + fixed an install-blocking Odoo-19 view-validation P0 (5 constructs: `<group expand>` ×4 search views + `active_id` job stat-button); reproduced then fixed the known Test Connection direct-RPC P1 (unfixed: non-admin roles not denied, create job+2 logs; fixed: `AccessError`, zero side effects) via one Administrator boundary guard on `action_test_connection`/`activate`/`disconnect`/`reconnect` (existing `group_shopify_connector_admin`, `env.su`-exempt); fixed 4 owned U0 test defects surfaced by genuine runtime (dashboard-as-superuser, `ir.ui.menu.group_ids`, source-guard self-inspection, non-existent mutation domain). U0 suite 63/0/0; core 368 tests 0 failed (11 environmental `autopost_bills` at_install setUpClass errors, not connector logic); leak scan clean. Browser tours + HOOT pending Stage R2 (container `can't start new thread` limit); corrected SHA needs a fresh Odoo.sh build for Stage R2 exact-build proof. Draft PR, not self-accepted/ready-marked/merged; awaiting DEC-040 independent review. Evidence: [`ui-u0-validation-results.md`](../05-qa/ui-u0-validation-results.md) §1a; decisions AR-073..AR-076. **Stage R2 correction (2026-07-22, exceptional P1 reopen):** independent review of the exact Stage R1 head `0fa512d` (comment `5049668193`) returned `REVISE` — confirmed P1: `action_mark_reconnect_needed` had no Administrator boundary, allowing a non-admin caller to create an unauthorized `sudo()`-backed audit Job/JobLog on a disconnecting/disconnected store with zero denial. Control room accepted the verdict (`5049734472`) and authorized one consolidated correction, now applied: the guard added to `action_mark_reconnect_needed`; the five-action zero-side-effect security matrix, mutation-resolution-wizard refusal proof, AST-based whole-tree controller/OAuth guard, and sparkline non-colour distinction all added/hardened; `ui-u0-validation-results.md` §11/§12 corrected. `IMPLEMENTED — EXACT-SHA ODOO.SH VERIFICATION PENDING`; no runtime executed this session; no independent re-review has run against the corrected SHA yet; PR #192 remains draft/unmerged, not self-accepted. Evidence: [`ui-u0-validation-results.md`](../05-qa/ui-u0-validation-results.md) §12; decision AR-077. **FINAL CLOSURE (2026-07-22): U0 is ACCEPTED, RUNTIME-VERIFIED, and MERGED.** Fresh independent delta review of exact head `a13f67210269277826e78b23be1fab5e0caffec5` returned `ACCEPT` (PR #192 comment `5050387258`; no P0/P1/material P2); the control room accepted that verdict and the exact-SHA runtime evidence (build `35308219`, U0/Test Connection `67/67`, sale `194/194`, inventory `247/247`) in comment `5050525557`. A separate closure session merged PR #192 into `mvp/program-integration` via merge commit `8818c7714f46eefe51c6b452b5e3f24d155f26fb`. Deferred browser/lifecycle evidence (HOOT, browser tours, driven walkthrough/screenshots, browser accessibility/render/memory evidence, additional disposable-database install, isolated upgrade, isolated uninstall/reinstall) remains `DEFERRED BY PRODUCT OWNER — NOT PROVEN`, carried forward to UAT/release readiness. Evidence: [`ui-u0-validation-results.md`](../05-qa/ui-u0-validation-results.md) §13. |
| PERF-1 | Full acceptance remains Wave 5/6; PERF-0 baseline is pulled forward into Wave 4 |
| Wave 6 | Not started |
| Shopify development store | Critical external dependency for CV-013 and Wave 4 final validation |

## 2. Product-owner calibration — effective 2026-07-22

The product owner directed the control room to preserve full rigor for load-bearing risks while stopping uniform maximum-ceremony review. The governing files now implement:

- Tier 1 full rigor for mutation logic, concurrency, idempotency, security, credentials, data integrity, runtime production defects and destabilizing performance risks;
- Tier 2 normal review for architecture/design/domain contracts, with one consolidated correction iteration expected;
- Tier 3 light-touch treatment for wording, cross-references, terminology and document structure unless they change a real contract;
- a third same-day revision as a synthesis/reset signal rather than routine incremental correction;
- early UI and performance work in parallel with Wave 4;
- mandatory wave-boundary calibration.

Mutation-safety architecture, Odoo.sh runtime requirements, citation discipline and checkpoint protections are unchanged.

## 3. Control-room self-audit — Wave 3 and Wave 4 correction rounds

### Counting method

A **round** means one control-room revise/correction cycle requiring a worker response and re-review. Multiple commits inside one coherent correction batch count as one round. This avoids inflating the audit because Task 013 used many commits to preserve reviewable checkpoints.

### Round classification

| # | Wave / gate | Round | Primary classification | Honest assessment |
| ---: | --- | --- | --- | --- |
| 1 | Wave 3 Gate A | Consolidated DEC-036 correction after independent source + architecture audits | **Load-bearing** — safety/data integrity/concurrency | Resolved eight blocking Layer 2 decisions, cursor placement, network/transaction separation, disconnect interaction, fingerprints, error routing and proof environments. Full rigor was justified. |
| 2 | Wave 3 Gate A | Two clerical merge-closure conditions | **Tier 3 polish** | DoR/table/addendum wording. These should have been fixed in-pass and should not have carried an independent full identity/review cycle. |
| 3 | Wave 3 Gate B | Revision 2 | **Load-bearing** — mutation ownership/idempotency | Corrected the unsafe same-job/two-attempt design and activation sequencing. Full rigor was justified. |
| 4 | Wave 3 Gate B | Revision 3 | **Load-bearing** — job lifetime/atomic handoff/error taxonomy | Corrected repeated-attempt risk, non-atomic handoff, undefined blocked-review behavior, invented error values and inverted freshness logic. Full rigor was justified. |
| 5 | Wave 3 Gate B | Merge-closure normalization | **Mixed; Tier 2 contract semantics with Tier 3 volume** | Several terms were implementation-significant, but the round bundled eleven wording/state-taxonomy corrections after substantive acceptance. This should have been absorbed into the prior consolidated correction/acceptance pass. |
| 6 | Wave 3 Stage 0 | Runtime/diagnostic correction | **Load-bearing** — production behavior/test validity | Corrected exception shadowing, fail-closed behavior and invalid concurrency methodology. Full rigor was justified. |
| 7 | Wave 3 Task 013 | First genuine runtime correction | **Load-bearing** — P0/P1 production/data integrity | Runtime exposed operation-scope release, review-state, exception-classification and permission defects plus fixtures. One consolidated runtime correction was correct and necessary. |
| 8 | Wave 3 Task 013 | Track B guard/concurrency closure | **Load-bearing** — test integrity/concurrency proof | Corrected a false-positive source guard and added genuine simultaneous-process concurrency proof. Necessary, though it should have been planned before the first runtime acceptance claim. |
| 9 | Wave 4 prompt preparation | Dual-review prompt reconciliation | **Tier 2 design/governance** | Canonical-output, authority, source, phase and handoff controls were materially useful, but the prompt review was oversized and should have used a focused Tier 2 checklist. |
| 10 | Wave 4 Gate A | First bounded correction | **Load-bearing** — P0 retry safety + architecture | Removed unsafe uncertain-outcome resend, fixed pagination, modularity, vocabulary, lifecycle, permissions and API-version contracts. Necessary. |
| 11 | Wave 4 Gate A | Final micro-correction | **Load-bearing** — mutation safety/operation scope/lifecycle | Closed post-C2 resend authority, shared reconciliation scope and trigger lifecycle defects. Necessary, but the findings should have been discovered in round 10's complete review. |
| 12 | Wave 4 Gate A | Late source/trigger-origin finding | **Load-bearing technical finding, inefficiently handled** | The core ORM invariant was real. Requiring another documentation round was not efficient; the issue was correctly carried as a mandatory Gate B implementation/test criterion before merge acceptance. |

### Actual ratio

- **Round-level:** 9/12 load-bearing (75%), 2/12 mixed/Tier 2 (17%), 1/12 pure Tier 3 polish (8%).
- **Strict binary by dominant trigger:** 10/12 load-bearing or contract-significant (**83%**) versus 2/12 polish-dominant (**17%**).

The audit does **not** support a blanket conclusion that most revisions were trivial. Most caught real architecture, mutation-safety, runtime or test-integrity defects. The process drift was still real for two reasons:

1. Tier 3 work consumed the same ceremony as Tier 1 work.
2. Several load-bearing findings were discovered serially across delta reviews instead of together in the first exhaustive review.

The corrective action is risk-tiering plus one consolidated correction, not weaker safety review.

## 4. Current review tier and correction count

| Active work | Tier | Reason | Correction budget |
| --- | --- | --- | --- |
| Wave 4 Gate B fulfillment implementation | **Tier 1** | Shopify mutations, Layer 2, concurrency, idempotency, security, data integrity | One exhaustive independent review; one consolidated correction maximum; runtime failures collected into one batch |
| U0 UI foundation | **Tier 2** with Tier 1 security/action checks | New operator information architecture on existing hardened actions; no UI-owned mutation logic | One normal independent review; Tier 3 polish fixed in-pass; Odoo.sh mandatory because this is code |
| PERF-0 baseline | **Tier 2**, escalating to Tier 1 for unsafe findings | Benchmark design/measurement; lock/network or destabilizing regression becomes blocking | One normal review; performance defect batch consolidated |
| Governance calibration | **Tier 2 — merged** | Program sequencing/review policy, no production code | One consolidated correction and one verification-only review completed through PR #191 |

## 5. Parallel execution now authorized

### Wave 4 backend

Continue existing PR #189. Merge the live integration tip normally into its branch, preserve its implementation history, correct the two recorded P2 findings, run the full Odoo.sh campaign, collect any runtime failures into one consolidated correction and submit the exact candidate SHA to an independent Claude reviewer.

### U0 — first UI slice

May start on a separate branch from the live integration tip, limited to:

- navigation/menu/actions;
- store/readiness summary;
- dashboard shell using real read-only metrics;
- job/error/retry/manual-review views and already accepted actions;
- responsive/accessibility baseline and perceived-performance instrumentation.

No fulfillment-mode UI until Wave 4 fields/actions stabilize. No UI-owned business logic or mutation path.

### PERF-0 — early benchmark

May start on a separate benchmark branch or evidence-only harness, measuring current integration and later the Wave 4 candidate:

- admission/drain throughput;
- Layer 2 local overhead;
- scan/reconciliation throughput;
- lock duration/contention;
- p50/p95/p99 latency;
- query counts and memory behavior.

## 6. Realistic forward timeline

Assumptions: Odoo.sh remains accessible; a disposable Shopify development store and dedicated fixtures are available by early August; no new feature scope is added.

| Milestone | Expected window | Confidence / dependency |
| --- | --- | --- |
| Wave 3 residual live closure | 2026-07-23 to 2026-07-31 | Medium; depends on dev-store fixtures. Inventory code itself is already merged. |
| Wave 4 implementation candidate | Already implemented on PR #189; synchronization/P2/runtime continuation begins now | High for code availability; runtime risk remains |
| Wave 4 runtime + consolidated correction + rerun | 2026-07-23 to 2026-08-14 | Medium; one complete Odoo.sh campaign and one correction batch |
| Wave 4 dev-store + CV-013 validation | 2026-08-12 to 2026-08-18 | Low/medium until store access is confirmed |
| U0 first usable UI slice | 2026-07-23 to 2026-08-06 | Medium/high; read-only/hardened surfaces can run in parallel |
| PERF-0 baseline + Wave 4 comparison | 2026-07-27 to 2026-08-10 | Medium/high if benchmark environment is available |
| Wave 5 full UI/export/SEC-2/PERF-1 | 2026-08-10 to 2026-09-08 | Medium; use separate UI/export workstreams with one integration gate |
| Wave 6 full UAT/release readiness | 2026-09-07 to 2026-09-23 | Medium/low; depends on all mutation/dev-store gates |

**Realistic release-candidate range:** 2026-09-14 to 2026-09-25.

**Accelerated credible range:** 2026-09-04 to 2026-09-11, only with parallel U0/PERF work, timely Shopify access, no new scope, and no Tier 3 review loops.

## 7. Critical path and levers

Critical path:

1. Wave 4 backend correctness and runtime;
2. Shopify dev-store availability for Wave 4 and CV-013;
3. Wave 5 product export + remaining operator UI;
4. Wave 6 integrated UAT.

If schedule slips, use these levers in order:

1. eliminate Tier 3 gate ceremony;
2. parallelize UI, benchmark and export work with explicit file boundaries;
3. reject new feature additions until release;
4. defer only non-critical Task 013B or UI embellishment through an explicit product-owner scope decision;
5. never relax mutation safety, security, runtime or dev-store evidence.

## 8. Next actions

1. Continue Wave 4 PR #189 from the live integration tip under issue #186 comment `5044031518` and the calibrated one-correction rule.
2. Start U0 UI foundation from the live integration tip as one large usable slice.
3. Open PERF-0 benchmark definition/execution in parallel.
4. Confirm the Shopify development-store fixture date; if not available by early August, escalate the release-date dependency immediately.

## 9. Wave-boundary calibration template

At every wave boundary append a compact entry:

- tier and reason;
- initial review count and correction count;
- substantive/Tier 3 finding count;
- cycle-cap compliance;
- elapsed time vs forecast;
- UI/PERF status;
- next milestone/date/dependency;
- process adjustment, or `none` with evidence.