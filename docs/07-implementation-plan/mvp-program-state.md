# MVP Program State — Live Tracker

> **Current live tracker — calibrated 2026-07-25.** The complete pre-calibration tracker is archived at [`archive/mvp-program-state-through-2026-07-22.md`](./archive/mvp-program-state-through-2026-07-22.md). That archive preserves the full dated audit trail. This file is intentionally concise and must remain the first current-state document a worker reads.
>
> Stable scope/sequencing: [`mvp-completion-program.md`](./mvp-completion-program.md). Review policy: [`../06-prompts/claude-mvp-wave-review-template.md`](../06-prompts/claude-mvp-wave-review-template.md). Acceptance evidence: [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md).
>
> **Canonical role/process governance — 2026-07-25.** [DEC-041](../04-decisions/DEC-041-evidence-first-process-reallocation.md) and the [role-model addendum](../04-decisions/2026-07-25-mvp-role-model-addendum.md) govern: ChatGPT control room; Sol/Codex implementation; Runtime Claude exact-SHA runtime; separate Claude independent review; product owner final authority. Gates are unchanged. Framework-dependent assumptions require upstream citations; pushes and runtime output require durable records; tiers are deterministic from diff paths and semantics.

## 1. Current program status

| Item | Current state |
| --- | --- |
| Program integration | `mvp/program-integration@dd0af5d94a7f730e738dca955971e00bb4cc9122` is the verified base of current PR #189/#194 work and of this governance branch. Fetch live state before execution. |
| Wave 1 | Accepted, runtime-green, merged via PR #172 (`d18f9a9`); exact-head build `34986844`. |
| Wave 2 | Accepted, runtime-green, merged via PR #176 (`22bfb9a`); runtime-tested `63607dd`, build `35100725`, 728/728 and 86/86 Wave-2 methods green. |
| Wave 3 Stage 0 | Accepted, runtime-green, merged via PR #178 (`e48cfb1`); build `35145929`, 825/825. External process harness was explicitly infrastructure-deferred, not claimed executed. |
| Wave 3 inventory | Accepted, runtime-green, merged via PR #182 (`ab4f12f`); inventory 247/247, concurrent 9/9, sequential recovery 3/3. Live Shopify proof remains CV-013 issue #185. |
| U0 | Accepted, runtime-verified, merged via PR #192 (`8818c77`); exact head `a13f672`, build `35308219`, U0/Test Connection 67/67, sale 194/194, inventory 247/247. Driven browser/visual evidence remains deferred to UAT/release readiness. |
| Wave 4 Gate A | Accepted and merged via PR #188 (`01f072d`). |
| Wave 4 Gate B | PR #189 is open/draft/unmerged/mergeable at exact head `25639f17be14b30a52a8453f0813aa0b764de310`, base `dd0af5d`. Runtime Correction 5 was green on a content-equivalent Odoo.sh working tree (build `35414211`, fulfillment 281/281), but exact-pushed-SHA evidence is not established: the attempted session deployed parent `aa295ef` and correctly hard-stopped. Rebuild at `25639f17`, then rerun the authorized matrix. Gate D, CV-013, independent review, tracker closure, acceptance and merge remain pending. |
| Wave 5 | U1 Gate-A PR #194 is open/draft/unmerged at `b38e687` and must be refreshed after Wave 4 because it was derived from an earlier candidate. [SEC-2 #196](https://github.com/AdamsOdoo/Adams/issues/196) and accepted Wave 4 block U1 implementation. No Wave-5 implementation is authorized here. |
| Release dependencies | [SEC-3 #197](https://github.com/AdamsOdoo/Adams/issues/197) before external UAT/RC; [inventory fixture residue #198](https://github.com/AdamsOdoo/Adams/issues/198); [PERF-0 #199](https://github.com/AdamsOdoo/Adams/issues/199); [Shopify dev-store provisioning #200](https://github.com/AdamsOdoo/Adams/issues/200); CI/first continuous full-suite run; final lifecycle/configuration docs; product-owner release sign-off. |
| Wave 6 / release | Not started; no UAT or release acceptance claim. |

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

## 5. Parallel execution and current boundaries — 2026-07-25

### Critical path: Wave 4 exact-SHA runtime

1. End the stale Runtime Claude session so Odoo.sh can rebuild.
2. Rebuild `claude/wave-4-fulfillment-gate-b` at exact `25639f17`.
3. Run the already-authorized consolidated matrix; preserve the sanitized report durably under DEC-041 D3.
4. If candidate-owned failures exist, collect all safe independent families and authorize one consolidated correction batch. Do not start another document chain.
5. If green, run independent Tier-1 review, then controlled Gate D/CV-013 on disposable Shopify resources, tracker closure, acceptance and merge.

This DEC-041 governance work proceeds in parallel and does not delay or modify PR #189.

### External dependency preparation

Shopify dev-store provisioning may proceed without a connector mutation: disposable development store, dedicated test location/product/variant, least-privilege credential, and matching Odoo bindings. Never paste the credential into chat, prompts, PRs, logs, or issues.

### Governance/quality work

The following may proceed on separate owned branches/issues without touching PR #189/#194 content:

- SEC-2 contract/implementation preparation, but U1 implementation waits for accepted Wave 4 and merged SEC-2;
- SEC-3 complete model-surface inventory and correction contract;
- inventory test-residue cleanup;
- PERF-0 benchmark definition/execution;
- minimal CI design/implementation under DEC-041 D8.

### Frozen until prerequisites close

- PR #189 code/body remains frozen except its authorized runtime/closure sequence.
- PR #194 content remains frozen until Wave 4 merges and SEC-2 is available.
- No Wave 5 implementation, UAT authorization, ready-mark, acceptance, or merge occurs from this tracker update.

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