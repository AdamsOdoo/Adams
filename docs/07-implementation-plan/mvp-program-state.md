# MVP Program State — Live Tracker

> **Current live tracker — calibrated 2026-07-22.** The complete pre-calibration tracker is archived at [`archive/mvp-program-state-through-2026-07-22.md`](./archive/mvp-program-state-through-2026-07-22.md). That archive preserves the full dated audit trail. This file is intentionally concise and must remain the first current-state document a worker reads.
>
> Stable scope/sequencing: [`mvp-completion-program.md`](./mvp-completion-program.md). Review policy: [`../06-prompts/claude-mvp-wave-review-template.md`](../06-prompts/claude-mvp-wave-review-template.md). Acceptance evidence: [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md).

## 1. Current program status

| Item | Current state |
| --- | --- |
| Program integration branch | `mvp/program-integration` |
| Current integration SHA | `01f072dd4d83b7b39737452a686244a3a8c00332` |
| Wave 1 | Merged and runtime-green |
| Wave 2 | Merged and runtime-green |
| Wave 3 / Task 013 | Inventory + Layer 2 implementation merged; runtime and genuine concurrency evidence accepted |
| Wave 3 residual | `CV-013` issue #185 open and critical; live Shopify inventory mutation validation still required before RC/UAT acceptance; Task 013B separately gated |
| Wave 4 Gate A | Accepted and merged through PR #188; merge SHA `01f072dd4d83b7b39737452a686244a3a8c00332` |
| Wave 4 Gate B | Formally issued on issue #186 comment `5043052341`; implementation branch/PR not yet reported in this tracker |
| Wave 5 | Full wave not started; early UI slice is now authorized to run in parallel within the calibrated boundary |
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
| Wave 4 Gate B fulfillment implementation | **Tier 1** | Shopify mutations, Layer 2, concurrency, idempotency, security, data integrity | One exhaustive review; one consolidated correction maximum; runtime failures collected into one batch |
| U0 UI foundation | **Tier 2** | New operator information architecture on existing hardened actions; no UI-owned mutation logic | One normal review; Tier 3 polish fixed in-pass |
| PERF-0 baseline | **Tier 2**, escalating to Tier 1 for unsafe findings | Benchmark design/measurement; lock/network or destabilizing regression becomes blocking | One normal review; performance defect batch consolidated |
| Calibration governance PR | **Tier 2** | Program sequencing/review policy, no production code | One review, no full runtime ceremony |

## 5. Parallel execution now authorized

### Wave 4 backend

Proceed with the issued Gate B prompt from the exact integration SHA. The late source/origin matrix is mandatory implementation/test acceptance criteria; it is not ignored and must be proven before Gate B acceptance.

### U0 — first UI slice

May start on a separate branch from the same integration base, limited to:

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
| Wave 4 implementation candidate | 2026-07-23 to 2026-08-07 | Medium; both modes and Layer 2 make this larger than prior backend waves. |
| Wave 4 runtime + consolidated correction + rerun | 2026-08-06 to 2026-08-14 | Medium; one complete Odoo.sh campaign and one correction batch. |
| Wave 4 dev-store + CV-013 validation | 2026-08-12 to 2026-08-18 | Low/medium until store access is confirmed. |
| U0 first usable UI slice | 2026-07-24 to 2026-08-06 | Medium/high; read-only/hardened surfaces can run in parallel. |
| PERF-0 baseline + Wave 4 comparison | 2026-07-27 to 2026-08-10 | Medium/high if benchmark environment is available. |
| Wave 5 full UI/export/SEC-2/PERF-1 | 2026-08-10 to 2026-09-08 | Medium; use separate UI/export workstreams with one integration gate. |
| Wave 6 full UAT/release readiness | 2026-09-07 to 2026-09-23 | Medium/low; depends on all mutation/dev-store gates. |

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

1. Complete and review this calibration PR as Tier 2.
2. Continue Wave 4 Gate B under issue #186 comment `5043052341` and the calibrated one-correction rule.
3. Open a bounded U0 UI-foundation task/branch from the current integration base.
4. Open PERF-0 benchmark definition/execution in parallel.
5. Confirm the Shopify development-store fixture date; if not available by early August, escalate the release-date dependency immediately.

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
