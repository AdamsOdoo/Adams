# MVP Program State — Live Tracker

> **Current live tracker — calibrated 2026-07-25.** The complete pre-calibration tracker is archived at [`archive/mvp-program-state-through-2026-07-22.md`](./archive/mvp-program-state-through-2026-07-22.md). That archive preserves the full dated audit trail. This file is intentionally concise and must remain the first current-state document a worker reads.
>
> Stable scope/sequencing: [`mvp-completion-program.md`](./mvp-completion-program.md). Review policy: [`../06-prompts/claude-mvp-wave-review-template.md`](../06-prompts/claude-mvp-wave-review-template.md). Acceptance evidence: [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md).
>
> **Canonical role/process governance — 2026-07-25.** [DEC-041](../04-decisions/DEC-041-evidence-first-process-reallocation.md) and the [role-model addendum](../04-decisions/2026-07-25-mvp-role-model-addendum.md) govern: ChatGPT control room; Sol/Codex implementation; Runtime Claude exact-SHA runtime; separate Claude independent review; product owner final authority. Gates are unchanged. Framework-dependent assumptions require upstream citations; pushes and runtime output require durable records; tiers are deterministic from diff paths and semantics.

## 1. Current program status

| Item | Current state |
| --- | --- |
| Program integration | `mvp/program-integration@a5bcfa63cfbe01b655b3a8172cbac72df26864e2` is the current live integration tip after PR #195. PR #189/#194 remain based on `dd0af5d94a7f730e738dca955971e00bb4cc9122`; this governance branch began there and reconciled the intervening `CHATGPT.md` change. Fetch live state before execution. |
| Wave 1 | Accepted, runtime-green, merged via PR #172 (`d18f9a9`); exact-head build `34986844`. |
| Wave 2 | Accepted, runtime-green, merged via PR #176 (`22bfb9a`); runtime-tested `63607dd`, build `35100725`, 728/728 and 86/86 Wave-2 methods green. |
| Wave 3 Stage 0 | Accepted, runtime-green, merged via PR #178 (`e48cfb1`); build `35145929`, 825/825. External process harness was explicitly infrastructure-deferred, not claimed executed. |
| Wave 3 inventory | Accepted, runtime-green, merged via PR #182 (`ab4f12f`); inventory 247/247, concurrent 9/9, sequential recovery 3/3. Live Shopify proof remains CV-013 issue #185. |
| U0 | Accepted, runtime-verified, merged via PR #192 (`8818c77`); exact head `a13f672`, build `35308219`, U0/Test Connection 67/67, sale 194/194, inventory 247/247. Driven browser/visual evidence remains deferred to UAT/release readiness. |
| Wave 4 Gate A | Accepted and merged via PR #188 (`01f072d`). |
| Wave 4 Gate B | PR #189 is open/draft/unmerged/mergeable at exact head `25639f17be14b30a52a8453f0813aa0b764de310`, base `dd0af5d`. Odoo.sh build `35422036` completed the safely executable exact-SHA matrix green, preserved in [runtime comment 5074529652](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5074529652). [Independent review comment 5077119326](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5077119326) accepted the runtime evidence with zero candidate-owned P0/P1/material-P2 findings. No further code correction or runtime rerun is required. The next gate is controlled Gate D/CV-013 on disposable Shopify resources; Delivered/A5 disposition, tracker closure, product-owner/control-room acceptance, ready-marking and merge remain. PR #189 is not finally accepted; UAT/release readiness are not claimed. |
| Wave 5 | U1 Gate-A PR #194 is open/draft/unmerged at `b38e687` and remains frozen pending accepted/merged Wave 4 and [SEC-2 #196](https://github.com/AdamsOdoo/Adams/issues/196). Its later authorized refresh must remove or suppress “Delivered” because no real backend seam exists, unless that seam is separately authorized, implemented, and independently proven. The current Delivered inconsistency is distinct from the historical A5 KeyError and is not a PR #189 candidate defect. No Wave-5 implementation is authorized here. |
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
| Wave 4 Gate B fulfillment implementation | **Tier 1** | Shopify mutations, Layer 2, concurrency, idempotency, security, data integrity | Exact-SHA runtime and exhaustive independent evidence review complete; Gate D/CV-013 and closure remain |
| U0 UI foundation | **Tier 2** with Tier 1 security/action checks | New operator information architecture on existing hardened actions; no UI-owned mutation logic | One normal independent review; Tier 3 polish fixed in-pass; Odoo.sh mandatory because this is code |
| PERF-0 baseline | **Tier 2**, escalating to Tier 1 for unsafe findings | Benchmark design/measurement; lock/network or destabilizing regression becomes blocking | One normal review; performance defect batch consolidated |
| Governance calibration | **Tier 2 — merged** | Program sequencing/review policy, no production code | One consolidated correction and one verification-only review completed through PR #191 |

## 5. Parallel execution and current boundaries — 2026-07-25

### Critical path: Wave 4 Gate D/CV-013 and closure

1. Treat [runtime comment 5074529652](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5074529652) and [independent review comment 5077119326](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5077119326) as the accepted exact-SHA evidence for `25639f17`; do not rebuild or rerun the already-complete matrix.
2. Execute controlled Gate D/CV-013 only on authorized disposable Shopify resources, with least-privilege credentials and durable sanitized evidence.
3. Apply the controlling Delivered/A5 disposition: this is not the historical A5 KeyError or a PR #189 defect; do not expose “Delivered” in U1/PR #194 until a real backend seam is separately authorized and independently proven.
4. Close the trackers, then obtain explicit product-owner/control-room acceptance.
5. Ready-mark and merge only under separate authorization after every remaining gate is closed.

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

- PR #189 code/body remains frozen except its authorized Gate D/CV-013 and closure sequence; no code correction or runtime rerun is required.
- PR #194 content remains frozen until Wave 4 merges and SEC-2 is available; its later authorized refresh must remove or suppress unsupported “Delivered”.
- No Wave 5 implementation, final Wave 4 acceptance, UAT authorization, release-readiness claim, ready-mark, approval, or merge occurs from this tracker update.

## 6. Realistic forward timeline

Assumptions: Odoo.sh remains accessible; a disposable Shopify development store and dedicated fixtures are available by early August; no new feature scope is added.

| Milestone | Expected window | Confidence / dependency |
| --- | --- | --- |
| Wave 3 residual live closure | 2026-07-23 to 2026-07-31 | Medium; depends on dev-store fixtures. Inventory code itself is already merged. |
| Wave 4 implementation candidate | Implemented on PR #189; exact-SHA runtime and independent evidence review completed 2026-07-25 | High for accepted runtime evidence; Gate D/CV-013 and closure remain |
| Wave 4 exact-SHA runtime + independent evidence review | Complete 2026-07-25 | Build `35422036`; comments [5074529652](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5074529652) and [5077119326](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5077119326); no rerun required |
| Wave 4 controlled Gate D/CV-013 validation | 2026-07-25 to 2026-08-18 | Low/medium until disposable store access is confirmed; next Wave 4 gate |
| U0 first usable UI slice | 2026-07-23 to 2026-08-06 | Medium/high; read-only/hardened surfaces can run in parallel |
| PERF-0 baseline + Wave 4 comparison | 2026-07-27 to 2026-08-10 | Medium/high if benchmark environment is available |
| Wave 5 full UI/export/SEC-2/PERF-1 | 2026-08-10 to 2026-09-08 | Medium; use separate UI/export workstreams with one integration gate |
| Wave 6 full UAT/release readiness | 2026-09-07 to 2026-09-23 | Medium/low; depends on all mutation/dev-store gates |

**Realistic release-candidate range:** 2026-09-14 to 2026-09-25.

**Accelerated credible range:** 2026-09-04 to 2026-09-11, only with parallel U0/PERF work, timely Shopify access, no new scope, and no Tier 3 review loops.

## 7. Critical path and levers

Critical path:

1. Wave 4 controlled Gate D/CV-013 and record closure;
2. Shopify disposable dev-store availability;
3. Wave 5 product export + remaining operator UI;
4. Wave 6 integrated UAT.

If schedule slips, use these levers in order:

1. eliminate Tier 3 gate ceremony;
2. parallelize UI, benchmark and export work with explicit file boundaries;
3. reject new feature additions until release;
4. defer only non-critical Task 013B or UI embellishment through an explicit product-owner scope decision;
5. never relax mutation safety, security, runtime or dev-store evidence.

## 8. Next actions

1. Provision or confirm the authorized disposable Shopify fixtures, then execute controlled Gate D/CV-013 for PR #189.
2. Close the Delivered/A5 and tracker records; obtain explicit product-owner/control-room acceptance before any ready-mark or merge.
3. Refresh PR #194 only after authorization, suppressing unsupported “Delivered” unless a real backend seam has been separately implemented and independently proven.
4. Continue PERF-0, SEC-2/SEC-3 and CI work on their separately owned scopes; escalate immediately if Shopify fixtures remain unavailable.

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