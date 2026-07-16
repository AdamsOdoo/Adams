# MVP Program State — Live Tracker

> This is the single live status tracker for the MVP completion program (`DEC-032`). Update this file at the start and end of every Sol session and every Claude control-room review — it is the first thing any new session should read. The relatively stable contract (scope, waves, authority) lives in `mvp-completion-program.md`; this file is the frequently-changing status. Do not duplicate the contract's content here — link to it.

## Current status

**WAVE 0 MERGED (2026-07-15).** PR #169 merged into `mvp/program-integration` (merge commit `a1e83a09678537ac6db8959f5ed0c76a5bcc0d1c`, per the Wave 0 closure comment on issue #167). DEC-033 is Accepted with two minor corrections applied on PR #169 (Wave 1 internal sub-stage note; hard-stop 11 rewording). DEC-028/029/030 are Accepted; DEC-027 remains Proposed/Deferred. PR #150/#151 administrative closure as superseded is authorized to proceed.

**WAVE 1 SUBSTANTIVE RUNTIME CRITERIA SATISFIED; TEST-ONLY EXACT-HEAD VERIFICATION PENDING (2026-07-16).** Draft PR [#172](https://github.com/AdamsOdoo/Adams/pull/172) remains open/draft/unmerged on `sol/wave-1-readonly-foundation`. Odoo.sh 19 build `34985521` at exact SHA `d9d2dd018470054944db064cdd553160232713cd` produced fresh `1 failed / 0 errors / 634 tests`, with the only failure being the stale enqueue AST helper; focused Wave 1 `0/0/105`, product `0/0/176`, sale `0/0/107`, and lifecycle `0/0/9` were green. All 11 genuine SRR-03 classes passed across three distinct OS-process repetitions, and residue/security scans were clean under the accepted exact issue #157 accommodation. Product-owner ruling [comment 4988098888](https://github.com/AdamsOdoo/Adams/pull/172#issuecomment-4988098888) accepts the substantive SRR-03 runtime criteria. Test-only correction `b42042d641ce2d02cad9559a03fcb268ceaac3bc` changes no production behavior. **SRR-03 remains authoritatively OPEN pending the corrected exact-head verification only; Wave 2 remains unauthorized and unstarted.**

Freeze/resume status: **the issue #165 implementation freeze is lifted only for work authorized by DEC-032 and the master Sol mission, on branches descending from `mvp/program-integration`.** The product owner launched Sol on 2026-07-15 by issuing the complete master mission. Wave 0 is documentation/research only; no addon code was authorized in that wave. **Wave 1 is active for implementation** on `sol/wave-1-readonly-foundation` — CORE-R1, LC-1, JOB-ACTIONS, SEC-1, then SRR-03 closure, in that corrected order, per DEC-034. **Wave 2 remains unauthorized** and may not merge, be enabled, or receive live Shopify validation while **SRR-03 remains OPEN**.

## Checkpoint / integration identity

| Field | Value |
| --- | --- |
| Checkpoint SHA | `acd8c4691e72cf5590f2a56228b08f183b76cd9a` |
| Checkpoint branch | `checkpoint/core-r2-readonly-uat-2026-07-15` |
| Program integration branch | `mvp/program-integration` |
| Bootstrap governance merge SHA | `f7950e68ff4bb085deaef82563aff25bda6b8545` (PR #166 merge; checkpoint + governance bootstrap only) |
| Tracker-upkeep commit | `06600811d664f5e1fee9ee2cb86e6c81f9c8a83e` (routine tracker upkeep recording PR #166/#167; not new governance content) |
| Bootstrap branch / PR | `claude/mvp-control-room-bootstrap-39nip0` → PR [#166](https://github.com/AdamsOdoo/Adams/pull/166), merged |
| Master program issue | [#167](https://github.com/AdamsOdoo/Adams/issues/167) |

> **No SHA in this table is the live tip.** `mvp/program-integration` advances with every merge — including routine tracker-upkeep commits to this file — so any "current SHA" recorded here becomes stale the moment it is committed. Every new session must verify the live `mvp/program-integration` tip directly from GitHub before relying on it.

## Active wave

**Wave 1 — Existing read-only foundation integration — FINAL TEST-ONLY VERIFICATION PENDING.** Draft PR [#172](https://github.com/AdamsOdoo/Adams/pull/172) remains open/draft. Build `34985521` validates all production and substantive SRR-03 criteria; the sole fresh-install failure was the stale test-only AST helper. Correction `b42042d641ce2d02cad9559a03fcb268ceaac3bc` changes only `test_job_dispatch.py`. SRR-03 remains OPEN and no Wave 1 completion is claimed until the corrected exact-head verification passes; Wave 2 is unauthorized.

## Wave status

| Wave | Status | Branch/PR | Notes |
| --- | --- | --- | --- |
| 0 — Reconciliation & research closure | **Merged** | `sol/wave-0-reconciliation-research`; PR [#169](https://github.com/AdamsOdoo/Adams/pull/169) (merged, `a1e83a09678537ac6db8959f5ed0c76a5bcc0d1c`) | DEC-033 accepted with minor corrections; DEC-028/029/030 accepted; DEC-027 deferred; no addon/protected changes. |
| 1 — Read-only foundation integration (CORE-R1, LC-1, JOB-ACTIONS, SEC-1, SRR-03 closure) | **Active — final test-only verification pending** | `sol/wave-1-readonly-foundation`; draft PR [#172](https://github.com/AdamsOdoo/Adams/pull/172) | Build 34985521 satisfied production/SRR-03 criteria; one AST guard corrected test-only; SRR-03 OPEN pending exact-head verification. |
| 2 — Order import (Task 012) | Not started / unauthorized | — | SRR-03 is OPEN; blocked on Wave 1 prerequisites/closure evidence and packet gate. May not merge, be enabled, or receive live Shopify validation while SRR-03 remains open. |
| 3 — Inventory synchronization (Task 013/013B) | Not started | — | Blocked on Wave 2 and DEC-031 Layer 2 design+acceptance. |
| 4 — Fulfillment and tracking (Task 014) | Not started | — | Blocked on Wave 3 (Layer 2 proven). |
| 5 — Premium operator experience (UI U1–U3, PERF-1, Task 015/015B) | Not started / unauthorized | — | Proposed scope includes product export after Layer 2 (DEC-033 accepted); pending Waves 1–4. |
| 6 — E2E integration, UAT, release readiness | Not started | — | Blocked on Waves 1–5. |

## Active Sol session (Wave 1 runtime correction — 2026-07-16)

- Re-verified the live base before branching: `mvp/program-integration` matched the product-owner-authorized tip; checkpoint `acd8c4691e72cf5590f2a56228b08f183b76cd9a`, `Shopify-connector`, and `main` remained unchanged.
- Confirmed PR #170/DEC-034 and PR #171 normalized the Wave 1 packets without introducing addon implementation.
- Created `sol/wave-1-readonly-foundation` from the verified integration tip. Opened the single early draft PR [#172](https://github.com/AdamsOdoo/Adams/pull/172) into `mvp/program-integration`; it remains draft and carries the frozen five-stage execution plan.
- Stage 1 CORE-R1: inherited accepted code/test slice re-verified; prior build evidence retained; final exact-head rerun pending.
- Stage 2 LC-1: implementation, focused tests, migration, manifests, validation record, AR-050, and handoff pushed; Python syntax checks passed; Odoo.sh install/upgrade/uninstall/reinstall proof pending.
- Product-owner ruling comment `4982429209` validated the omission and authorized the exact one-field completeness correction. D-SEC1-2/D-SEC1-7 and the LC-1 sanctioned-writer statement were amended in commit `a4a370b5378366e719c59c01b1bbd5febe0a868b`; no architecture or scope changed.
- Stage 3 JOB-ACTIONS: the additive two-action model, nine-method role/state/audit suite, version/import wiring, validation record, AR-051, and handoff are pushed; both new Python sources compile. Odoo.sh remains pending.
- Product-owner ruling comment `4982750956` validated and resolved the Stage 4 pre-edit hard-stop: binding/PII audit uses the existing lifecycle maintenance job helper with narrow protected-site sudo and original actor preservation; company validation uses caller-context records plus `env.company`, without a store field. Packet and validation record updated.
- Stage 4 exact-head runtime: build `34985521` at `d9d2dd018470054944db064cdd553160232713cd` produced one test-only AST failure among 634 fresh tests; all focused Wave 1, product, sale, lifecycle, genuine concurrency, residue, and security criteria in ruling `4988098888` were green.
- Stage 5 closure gate: all 11 genuine SRR-03 classes passed across three OS-process repetitions. Test-only correction `b42042d641ce2d02cad9559a03fcb268ceaac3bc` updates only the AST helper/coverage and is statically green. SRR-03 remains OPEN until final exact-head verification; Wave 2 and all excluded domains remain unstarted.

## Prior completed work (bootstrap governance)

- Verified all protected references match the task's expected state (checkpoint SHA, issue #165, PR #163 merge target, `Shopify-connector`, `main`, PR #150/#151 heads) — no drift found.
- Created `mvp/program-integration` from the exact checkpoint SHA.
- Ran a 10-workstream evidence-based repository audit (addons/manifests, architecture/decisions, research, QA/runtime evidence, PR #150, PR #151, issues/risk register, operator UX, tests/CI, implementation-plan/prompt history).
- Produced `mvp-completion-program.md` (frozen MVP contract + macro-waves + Sol authority + hard-stops), this state file, `../05-qa/mvp-acceptance-matrix.md`, `DEC-032-mvp-autonomous-execution-model.md`, `../06-prompts/gpt56-sol-master-mvp-mission.md`, `../06-prompts/claude-mvp-wave-review-template.md`, a `CLAUDE.md` addendum, and root `GPT_SOL.md`.
- Merged the governance bootstrap via PR [#166](https://github.com/AdamsOdoo/Adams/pull/166) and opened the master program issue [#167](https://github.com/AdamsOdoo/Adams/issues/167).
- No addon code created or modified. No macro-wave opened. No live Shopify/Odoo runtime call made.

## Blockers

1. **Wave 1 final test-only exact-head verification** — build `34985521` satisfied the production and substantive SRR-03 matrix but retained one stale AST-guard failure. Run the targeted guard, one fresh all-module run, one full core run after the accepted #157 accommodation, one combined genuine-class smoke run, residue/security audits, and restore both temporary DB defaults. Until green evidence is recorded, SRR-03 remains OPEN and Wave 1 is incomplete.
2. **Dev-store access provisioning** — Wave 6 and mutation-domain UAT require human-provisioned Shopify Partner/dev-store credentials; Sol cannot self-provision them (hard-stop 5).

## Open decisions (full list: `mvp-completion-program.md` §9) — resolved by Wave 0 acceptance

1. Task 015/015B retained in MVP Wave 5 after Layer 2 — Accepted (DEC-033 §1).
2. SRR-03 reconciled to OPEN with a Wave 1 closure sub-gate — Accepted (DEC-033 §2); build 34985521 satisfies the substantive runtime criteria, but authoritative closure awaits the corrected exact-head verification.
3. PR #150/#151 administrative closure as superseded — Accepted (DEC-033 §3); action to proceed once PR #169 merges.
4. DEC-027 explicitly deferred; DEC-028/029/030 Accepted with the prerequisites in DEC-033 §4 — applied to each record on this PR.
5. Hazard branch left untouched — confirmed; remains untouched.
6. Empty requirements file left untouched — confirmed; remains untouched.

## Runtime evidence log

| Date | Wave | Evidence | Odoo.sh build | Result |
| --- | --- | --- | --- | --- |
| 2026-07-15 | Checkpoint (pre-program) | `../05-qa/task-core-r2-validation-results.md` §IS2 | `34935129` | Fresh install 0/0 across core/product/sale; issue #157 artifact only known failure class. |
| 2026-07-16 | Wave 1 diagnostic (pre-correction SHA `62b2645`) | SEC-1 and CORE-R2 validation records | `34968318` | Upgrade/focused/lifecycle partial passes; transition regression in fresh/full/drain-recovery suites; residue and security scans clean; issue #157 exact artifact only; no Wave 1 pass. |
| 2026-07-16 | Wave 1 corrected production/SRR proof (SHA `d9d2dd0`) | SEC-1 and CORE-R2 validation records; ruling `4988098888` | `34985521` | Fresh 1/0/634, sole test-only AST guard failure; focused 0/0/105, product 0/0/176, sale 0/0/107, lifecycle 0/0/9; all 11 genuine classes ×3 green; clean residue/security; substantive SRR criteria satisfied, closure pending final test-only verification. |

## Next control-room gate

The next action is the limited final verification authorized by ruling `4988098888`: targeted AST guard, fresh all-module run, full core after the accepted #157 accommodation, one combined genuine-class smoke run, final residue/security audit, and restoration of both temporary DB defaults. The full three-process matrix need not repeat because no production code changed. PR #172 remains draft/unmerged.

## Sprint checkpoint log

- **Wave 1 build 34985521 accepted / test-only AST correction (2026-07-16):** Exact SHA `d9d2dd018470054944db064cdd553160232713cd` ran fresh `1 failed / 0 errors / 634`, with only the stale enqueue create-target AST receiver helper failing. Focused Wave 1 `0/0/105`, product `0/0/176`, sale `0/0/107`, lifecycle `0/0/9`, all 11 genuine SRR classes ×3 OS-process repetitions, residue, and security checks were green. Ruling `4988098888` accepts substantive SRR-03 criteria. Test-only commit `b42042d641ce2d02cad9559a03fcb268ceaac3bc` unwraps only the five approved wrappers and changes no production file. SRR-03 remains OPEN pending the limited final exact-head verification; Wave 2 remains unstarted.

- **Wave 1 runtime correction pushed (2026-07-16):** Build `34968318` at pre-correction SHA `62b2645f69280aadc68a56045a26bef2063c5821` found that D-SEC1-1 rejected five accepted CORE-R2 recovery outcomes after a PostgreSQL rollback returned the exact job to committed `queued`/due-`retry_waiting`. Product-owner ruling `4984719237` authorized only those edges. Commit `2b6d9d8259fada252abca19407d1df53bed9e66f` implements the narrow correction and tests both states across safe retry, exhaustion, conservative and undeclared policy, exact re-lock and no handler replay. Static guards are green; corrected runtime is not yet run; SRR-03 OPEN; Wave 2 unstarted.


- **Wave 1 Stage 4 implementation / runtime-access hard-stop (2026-07-15):** SEC-1 implementation commit `60ac4165a0fa9babc070f892bfdeb6dc0a2e48b5` applies D-SEC1-1..7 and both product-owner rulings across 32 packet-owned addon/test files. Static proof: 31 Python parses green, cron XML parses, exact sudo inventories guarded, 9 core security + 12 PII focused tests encoded. No Odoo.sh status/workflow, local Odoo runtime, authenticated build, or database is available; hard-stop 5 is active. Stage 5/SRR-03 runtime proof is unstarted; SRR-03 OPEN; Wave 2 unauthorized.

- **Wave 1 Stage 4 resumed under binding ruling (2026-07-15):** PR #172 comment `4982750956` validated the prior hard-stop and bound the existing lifecycle maintenance job as the per-action/per-store atomic audit carrier, with narrow protected-site sudo and original actor preservation. It also bound the single-company `env.company` comparison without adding `company_id` to the store. The SEC-1 packet and validation scaffold record identifiers/counts/reasons-only audit content, exact carrier counts, redaction, company-neutral behavior, refusal/no-audit cases, and rollback-on-audit-failure proof. Stage 4 resumed on the same branch and draft PR; SRR-03 remains OPEN; Wave 2 unauthorized.

- **Wave 1 hard-stop before SEC-1 implementation (2026-07-15):** After Stage 3, Sol inventoried every current SEC-1 model/writer before editing. The accepted packet requires binding overrides and PII masking/sweeps to emit audited `manual_action`/summary rows, but the only connector audit-row model requires a `shopify.connector.job` and the packet names neither an audit-job carrier/creation door nor another audit model. It also requires binding-store/company consistency although the store model has no company field. Selecting a carrier or ownership source would alter security architecture and sudo inventory, so hard-stop 10 triggered before any SEC-1 production/test edit. Stage 3 remains implemented/syntax-clean; Odoo.sh and SRR-03 remain pending; Wave 2 unauthorized.

- **Wave 1 Stage 3 JOB-ACTIONS implemented (2026-07-15):** Implemented accepted D-JA-1 as a pure additive core extension: manual retry across the four approved recovery states, cancel across the four approved non-terminal work states, exact role/reason/audit contracts, and no force/bypass or pre-SEC-1 sudo. Added a nine-method focused matrix, version/import wiring, validation record, AR-051, and compact handoff. Both new Python sources compile; exact-head Odoo.sh remains pending. Stage 4 SEC-1 is active; SRR-03 remains OPEN; Wave 2 unauthorized.

- **Wave 1 resumed under product-owner ruling (2026-07-15):** PR #172 comment `4982429209` validated the LC-1/SEC-1 completeness hard-stop and approved the narrow one-field correction. The SEC-1 packet now protects `original_job_type`, adds four-role direct-write denial coverage, and preserves the LC-1 conversion helper as a named sanctioned writer; the packet amendment is isolated in commit `a4a370b5378366e719c59c01b1bbd5febe0a868b`. Stage 3 resumed on the same branch and draft PR. SRR-03 remains OPEN; Wave 2 remains unauthorized.

- **Wave 1 hard-stop after LC-1 (2026-07-15):** CORE-R1 was found already inherited byte-for-byte from the checkpoint, re-verified without duplicate code, and recorded as Stage 1. LC-1 was implemented on PR #172 (historic job sink, original-type preservation/backfill, audited cancellation/retyping, two domain `ondelete` callables, dispatcher refusal, focused tests, version bumps); Python sources compile, Odoo.sh pending. Before JOB-ACTIONS, cross-checking the accepted SEC-1 field list exposed a security/integrity gap: LC-1's new `original_job_type` is not in D-SEC1-2's exact protected set, so implementing Stage 4 verbatim would leave that audit identity generically writable under the existing ACLs. Hard-stop 9 triggered; no Stage 3+, runtime closure, or Wave 2+ work started.

- **Wave 1 execution start (2026-07-15):** Re-verified the exact authorized integration tip and all protected references, confirmed no conflicting Wave 1 branch/PR or later-wave implementation, created `sol/wave-1-readonly-foundation`, and recorded the five-stage execution order. This is a state-only bootstrap commit; no addon/test implementation or runtime claim is included. SRR-03 remains OPEN and Wave 2 remains unauthorized.

- **Wave 1 gate normalization (2026-07-15):** Independently re-verified the live baseline before touching anything (`mvp/program-integration` = `88f2dcaaa9ec0ad01fdabec766cdcd819b859e9e`, matching PR #170's merge commit exactly; checkpoint/`Shopify-connector`/`main` unchanged at their recorded SHAs; no Wave 1 implementation branch or PR exists; SRR-03 remains OPEN; Wave 2 remains unauthorized). Read the complete current text of DEC-034, DEC-030, the CORE-R1/LC-1/JOB-ACTIONS/SEC-1 packets, this file, the completion program, and the acceptance matrix, and confirmed PR #170/DEC-034 (plus the earlier Wave 0 closure comment) intended full implementation authorization for all four Wave 1 stages, not merely sequencing. Found a real defect: DEC-034, CORE-R1, the lifecycle design doc, JOB-ACTIONS, and SEC-1 each still carried an active "Proposed"/"NOT accepted"/"DO NOT USE UNTIL..." header or locked-prompt gate line dating from before acceptance, and DEC-030 contained an internal contradiction (top-of-file note said Accepted, its own `## Status` section still said NOT accepted) — any of these would cause a fresh Sol session to read the already-accepted Wave 1 packets as unauthorized. Corrected each packet's active status header and locked-prompt gate preamble to state the gate is open (CORE-R1 Stage 1, LC-1 Stage 2, JOB-ACTIONS Stage 3, SEC-1 Stage 4, each under DEC-034/issue #167), fixed DEC-030's internal contradiction, normalized this file's and `mvp-completion-program.md`'s stale "reconciliation active"/"DEC-033 pending" wording, updated the acceptance matrix's authorization cells, and corrected `research-handoff.md`'s stale draft-PR entry. No architecture, requirement, allowed-file list, test requirement, or implementation mechanism changed; no `addons/**` or test file touched; no protected reference touched; no Wave 1 implementation began.

- **Wave 1 packet reconciliation (2026-07-15):** Sol's first Wave 1 launch hard-stopped before any branch/PR/code (issue #167 comment `4980808811`) on three packet conflicts (SEC-1's Area-6/action-doors dependency; SEC-1's nonexistent order-binding allowlist entry; LC-1-vs-SEC-1 sequencing). Claude control room independently re-verified all three against primary sources (packet text line-by-line, live `git grep`/`git ls-tree`) and confirmed each. Produced `DEC-034` (corrected Wave 1 order: CORE-R1 → LC-1 → JOB-ACTIONS → SEC-1 → SRR-03 closure), a new `task-job-actions-generic-core-packet.md` extracting D-A6-5, and corrections to the SEC-1, Area 6, lifecycle-design, DEC-030, program-contract, program-state, acceptance-matrix, and Task 012 documents. Docs-only; no addon code, protected reference, or implementation branch created. Opened as a draft PR into `mvp/program-integration`, pending control-room adversarial consistency check before merge.

- **Wave 0 acceptance (2026-07-15):** Claude control-room review accepted DEC-033 with two minor documentation corrections (Wave 1 internal sub-stage note; hard-stop 11 rewording), applied directly on PR #169. DEC-028/029/030 accepted; DEC-027 confirmed Proposed/Deferred. PR #150/#151 administrative closure as superseded authorized to proceed post-merge. Full review recorded as a PR #169 review comment and an issue #167 closure comment. Wave 1 authorized upon merge; Wave 2 remains blocked on SRR-03 closure.

- **Wave 0 submission (2026-07-15):** Docs-only PR #169 opened. DEC-033, official-source refresh, contract/matrix/risk/Task-012 alignment, and session QA/handoff were prepared. No runtime evidence or addon/protected change. Awaiting Claude control-room review; Wave 1 unauthorized.

- **Wave 0 start (2026-07-15):** Product-owner launch received; protected refs verified; `sol/wave-0-reconciliation-research` created from `mvp/program-integration`; Wave 0 docs/research work opened. No addon code authorized or changed.
- **MVP Program Bootstrap (2026-07-15):** Established the control-room governance framework (this file and its siblings). Verified checkpoint integrity, created `mvp/program-integration`, audited the full repository, froze the MVP contract, and prepared Sol's launch prompt. Implementation remains frozen pending product-owner launch. Next: product owner reviews the bootstrap PR, then launches Sol with `../06-prompts/gpt56-sol-master-mvp-mission.md` at XHigh reasoning effort.
