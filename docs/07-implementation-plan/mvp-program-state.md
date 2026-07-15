# MVP Program State — Live Tracker

> This is the single live status tracker for the MVP completion program (`DEC-032`). Update this file at the start and end of every Sol session and every Claude control-room review — it is the first thing any new session should read. The relatively stable contract (scope, waves, authority) lives in `mvp-completion-program.md`; this file is the frequently-changing status. Do not duplicate the contract's content here — link to it.

## Current status

**WAVE 0 MERGED (2026-07-15).** PR #169 merged into `mvp/program-integration` (merge commit `a1e83a09678537ac6db8959f5ed0c76a5bcc0d1c`, per the Wave 0 closure comment on issue #167). DEC-033 is Accepted with two minor corrections applied on PR #169 (Wave 1 internal sub-stage note; hard-stop 11 rewording). DEC-028/029/030 are Accepted; DEC-027 remains Proposed/Deferred. PR #150/#151 administrative closure as superseded is authorized to proceed.

**WAVE 1 PACKET RECONCILIATION MERGED; WAVE 1 RE-AUTHORIZED (2026-07-15).** Sol's first Wave 1 launch correctly stopped before creating any branch, PR, code, or test, per issue #167 comment `4980808811`: the pre-reconciliation Wave 1 order (CORE-R1 → SEC-1 → LC-1 → SRR-03 closure) could not be implemented exactly as packaged — SEC-1 depended on Area 6's unauthorized Wave 2+ `action_manual_retry`/`action_cancel`; SEC-1's allowlist named a nonexistent Task 012 order-binding file; and LC-1's accepted design assumed it lands before SEC-1, contradicting the stated order. Claude control room independently re-verified all three findings against primary sources (packet text, live code `git grep`, live `git ls-tree`) and confirmed each is real. **[`DEC-034`](../04-decisions/DEC-034-wave-1-packet-dependency-reconciliation.md) — Accepted —** records the resolution and is merged into `mvp/program-integration` via PR [#170](https://github.com/AdamsOdoo/Adams/pull/170) (merge commit `88f2dcaaa9ec0ad01fdabec766cdcd819b859e9e`): Wave 1 is re-frozen to CORE-R1 → LC-1 → Task JOB-ACTIONS (new, extracted from Area 6's D-A6-5) → SEC-1 (rescoped to the current-surface baseline) → SRR-03 closure. **Wave 1 implementation is re-authorized, effective on PR #170's merge. No Wave 1 implementation branch exists yet.** The next action is a fresh Sol launch, verified against the live `mvp/program-integration` tip, using the corrected CORE-R1 → LC-1 → JOB-ACTIONS → SEC-1 → SRR-03-closure packets.

Freeze/resume status: **the issue #165 implementation freeze is lifted only for work authorized by DEC-032 and the master Sol mission, on branches descending from `mvp/program-integration`.** The product owner launched Sol on 2026-07-15 by issuing the complete master mission. Wave 0 is documentation/research only; no addon code was authorized in that wave. **Wave 1 is authorized for implementation** — CORE-R1, LC-1, JOB-ACTIONS, and SEC-1, in that corrected order, per DEC-034 — implementation has not started; a fresh Sol Wave 1 launch is the next action. **Wave 2 remains unauthorized** and may not merge, be enabled, or receive live Shopify validation while **SRR-03 remains OPEN**.

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

**Wave 1 — Existing read-only foundation integration — RE-AUTHORIZED, IMPLEMENTATION NOT STARTED.** Wave 0 merged (PR #169, merge commit `a1e83a09678537ac6db8959f5ed0c76a5bcc0d1c`). Sol's first Wave 1 launch hard-stopped before any branch/PR/code (issue #167 comment `4980808811`). The packet-dependency reconciliation merged via PR [#170](https://github.com/AdamsOdoo/Adams/pull/170) (merge commit `88f2dcaaa9ec0ad01fdabec766cdcd819b859e9e`), carrying [`DEC-034`](../04-decisions/DEC-034-wave-1-packet-dependency-reconciliation.md) — Accepted — plus the corrected CORE-R1/LC-1/JOB-ACTIONS/SEC-1/Area-6/Task-012 packet text. **No Wave 1 implementation branch exists yet.** Wave 1 implementation begins with a fresh Sol launch from the verified live `mvp/program-integration` tip — always re-verify the tip directly from GitHub; do not trust any SHA recorded in this file as current.

## Wave status

| Wave | Status | Branch/PR | Notes |
| --- | --- | --- | --- |
| 0 — Reconciliation & research closure | **Merged** | `sol/wave-0-reconciliation-research`; PR [#169](https://github.com/AdamsOdoo/Adams/pull/169) (merged, `a1e83a09678537ac6db8959f5ed0c76a5bcc0d1c`) | DEC-033 accepted with minor corrections; DEC-028/029/030 accepted; DEC-027 deferred; no addon/protected changes. |
| 1 — Read-only foundation integration (CORE-R1, LC-1, JOB-ACTIONS, SEC-1, SRR-03 closure) | **Re-authorized** (DEC-034 accepted, PR #170 merged); Sol's first launch hard-stopped on the pre-reconciliation packet conflicts (issue #167 comment `4980808811`), now resolved; **no implementation branch exists yet** | PR [#170](https://github.com/AdamsOdoo/Adams/pull/170) (merged, `88f2dcaaa9ec0ad01fdabec766cdcd819b859e9e`) | Requires Odoo.sh runtime access. Corrected internal sub-stages (DEC-034), each authorized/not yet implemented: CORE-R1 → LC-1 → JOB-ACTIONS → SEC-1 → SRR-03 closure. |
| 2 — Order import (Task 012) | Not started / unauthorized | — | SRR-03 is OPEN; blocked on Wave 1 prerequisites/closure evidence and packet gate. May not merge, be enabled, or receive live Shopify validation while SRR-03 remains open. |
| 3 — Inventory synchronization (Task 013/013B) | Not started | — | Blocked on Wave 2 and DEC-031 Layer 2 design+acceptance. |
| 4 — Fulfillment and tracking (Task 014) | Not started | — | Blocked on Wave 3 (Layer 2 proven). |
| 5 — Premium operator experience (UI U1–U3, PERF-1, Task 015/015B) | Not started / unauthorized | — | Proposed scope includes product export after Layer 2 (DEC-033 accepted); pending Waves 1–4. |
| 6 — E2E integration, UAT, release readiness | Not started | — | Blocked on Waves 1–5. |

## Active Sol session (Wave 0 submission — 2026-07-15)

- Re-verified protected references before branching: checkpoint `acd8c4691e72cf5590f2a56228b08f183b76cd9a`; integration tip `283e0512aa5f819444ff2ea28c25eae9a5d95065`; `Shopify-connector` `dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b`; `main` `a5d45432a9b60f724c1aff700f4b371ea019960e`; PR #150/#151 heads unchanged.
- Created the docs-only branch and draft PR [#169](https://github.com/AdamsOdoo/Adams/pull/169).
- Added DEC-033 with recorded dispositions for all six Wave 0 agenda items. It remains Proposed and non-binding pending Claude review.
- Closed the roles/permissions and fulfillment-scope research gaps with dated official Shopify/Odoo evidence. Updated the MVP contract, acceptance matrix, SRR-03 register narrative, architecture-gate status, and stale Task 012 prerequisite banners.
- No addon code, runtime session, protected reference, PR #150/#151, issue #165, hazardous branch, or requirements file was modified.
- Wave boundary reached: Sol stopped; Wave 1 remains unauthorized.

## Prior completed work (bootstrap governance)

- Verified all protected references match the task's expected state (checkpoint SHA, issue #165, PR #163 merge target, `Shopify-connector`, `main`, PR #150/#151 heads) — no drift found.
- Created `mvp/program-integration` from the exact checkpoint SHA.
- Ran a 10-workstream evidence-based repository audit (addons/manifests, architecture/decisions, research, QA/runtime evidence, PR #150, PR #151, issues/risk register, operator UX, tests/CI, implementation-plan/prompt history).
- Produced `mvp-completion-program.md` (frozen MVP contract + macro-waves + Sol authority + hard-stops), this state file, `../05-qa/mvp-acceptance-matrix.md`, `DEC-032-mvp-autonomous-execution-model.md`, `../06-prompts/gpt56-sol-master-mvp-mission.md`, `../06-prompts/claude-mvp-wave-review-template.md`, a `CLAUDE.md` addendum, and root `GPT_SOL.md`.
- Merged the governance bootstrap via PR [#166](https://github.com/AdamsOdoo/Adams/pull/166) and opened the master program issue [#167](https://github.com/AdamsOdoo/Adams/issues/167).
- No addon code created or modified. No macro-wave opened. No live Shopify/Odoo runtime call made.

## Blockers

1. **A fresh Sol Wave 1 launch** — the packet-reconciliation PR (#170) has merged and DEC-034 is accepted; Sol's next launch must independently verify the live `mvp/program-integration` tip and proceed against the corrected CORE-R1 → LC-1 → JOB-ACTIONS → SEC-1 → SRR-03-closure packets.
2. **Wave 1 runtime access** — Odoo.sh dev-build access is required for CORE-R1/LC-1/JOB-ACTIONS/SEC-1/SRR-03-closure evidence once Wave 1 implementation opens.
3. **Dev-store access provisioning** — Wave 6 and mutation-domain UAT require human-provisioned Shopify Partner/dev-store credentials; Sol cannot self-provision them (hard-stop 5).

## Open decisions (full list: `mvp-completion-program.md` §9) — resolved by Wave 0 acceptance

1. Task 015/015B retained in MVP Wave 5 after Layer 2 — Accepted (DEC-033 §1).
2. SRR-03 reconciled to OPEN with a Wave 1 closure sub-gate — Accepted (DEC-033 §2); runtime closure proof remains outstanding, owned by Wave 1.
3. PR #150/#151 administrative closure as superseded — Accepted (DEC-033 §3); action to proceed once PR #169 merges.
4. DEC-027 explicitly deferred; DEC-028/029/030 Accepted with the prerequisites in DEC-033 §4 — applied to each record on this PR.
5. Hazard branch left untouched — confirmed; remains untouched.
6. Empty requirements file left untouched — confirmed; remains untouched.

## Runtime evidence log

| Date | Wave | Evidence | Odoo.sh build | Result |
| --- | --- | --- | --- | --- |
| 2026-07-15 | Checkpoint (pre-program) | `../05-qa/task-core-r2-validation-results.md` §IS2 | `34935129` | Fresh install 0/0 across core/product/sale; issue #157 artifact only known failure class. |

*(No runtime evidence has been generated by this program yet — the row above is the inherited checkpoint evidence, carried forward for context.)*

## Next control-room gate

The Wave 1 macro-wave review (CORE-R1, LC-1, JOB-ACTIONS, SEC-1, SRR-03 closure), once a freshly launched Sol opens that wave's implementation PR into `mvp/program-integration` and it reaches its own definition of done, per `mvp-completion-program.md` §4 and `../06-prompts/claude-mvp-wave-review-template.md`.

## Sprint checkpoint log

- **Wave 1 gate normalization (2026-07-15):** Independently re-verified the live baseline before touching anything (`mvp/program-integration` = `88f2dcaaa9ec0ad01fdabec766cdcd819b859e9e`, matching PR #170's merge commit exactly; checkpoint/`Shopify-connector`/`main` unchanged at their recorded SHAs; no Wave 1 implementation branch or PR exists; SRR-03 remains OPEN; Wave 2 remains unauthorized). Read the complete current text of DEC-034, DEC-030, the CORE-R1/LC-1/JOB-ACTIONS/SEC-1 packets, this file, the completion program, and the acceptance matrix, and confirmed PR #170/DEC-034 (plus the earlier Wave 0 closure comment) intended full implementation authorization for all four Wave 1 stages, not merely sequencing. Found a real defect: DEC-034, CORE-R1, the lifecycle design doc, JOB-ACTIONS, and SEC-1 each still carried an active "Proposed"/"NOT accepted"/"DO NOT USE UNTIL..." header or locked-prompt gate line dating from before acceptance, and DEC-030 contained an internal contradiction (top-of-file note said Accepted, its own `## Status` section still said NOT accepted) — any of these would cause a fresh Sol session to read the already-accepted Wave 1 packets as unauthorized. Corrected each packet's active status header and locked-prompt gate preamble to state the gate is open (CORE-R1 Stage 1, LC-1 Stage 2, JOB-ACTIONS Stage 3, SEC-1 Stage 4, each under DEC-034/issue #167), fixed DEC-030's internal contradiction, normalized this file's and `mvp-completion-program.md`'s stale "reconciliation active"/"DEC-033 pending" wording, updated the acceptance matrix's authorization cells, and corrected `research-handoff.md`'s stale draft-PR entry. No architecture, requirement, allowed-file list, test requirement, or implementation mechanism changed; no `addons/**` or test file touched; no protected reference touched; no Wave 1 implementation began.

- **Wave 1 packet reconciliation (2026-07-15):** Sol's first Wave 1 launch hard-stopped before any branch/PR/code (issue #167 comment `4980808811`) on three packet conflicts (SEC-1's Area-6/action-doors dependency; SEC-1's nonexistent order-binding allowlist entry; LC-1-vs-SEC-1 sequencing). Claude control room independently re-verified all three against primary sources (packet text line-by-line, live `git grep`/`git ls-tree`) and confirmed each. Produced `DEC-034` (corrected Wave 1 order: CORE-R1 → LC-1 → JOB-ACTIONS → SEC-1 → SRR-03 closure), a new `task-job-actions-generic-core-packet.md` extracting D-A6-5, and corrections to the SEC-1, Area 6, lifecycle-design, DEC-030, program-contract, program-state, acceptance-matrix, and Task 012 documents. Docs-only; no addon code, protected reference, or implementation branch created. Opened as a draft PR into `mvp/program-integration`, pending control-room adversarial consistency check before merge.

- **Wave 0 acceptance (2026-07-15):** Claude control-room review accepted DEC-033 with two minor documentation corrections (Wave 1 internal sub-stage note; hard-stop 11 rewording), applied directly on PR #169. DEC-028/029/030 accepted; DEC-027 confirmed Proposed/Deferred. PR #150/#151 administrative closure as superseded authorized to proceed post-merge. Full review recorded as a PR #169 review comment and an issue #167 closure comment. Wave 1 authorized upon merge; Wave 2 remains blocked on SRR-03 closure.

- **Wave 0 submission (2026-07-15):** Docs-only PR #169 opened. DEC-033, official-source refresh, contract/matrix/risk/Task-012 alignment, and session QA/handoff were prepared. No runtime evidence or addon/protected change. Awaiting Claude control-room review; Wave 1 unauthorized.

- **Wave 0 start (2026-07-15):** Product-owner launch received; protected refs verified; `sol/wave-0-reconciliation-research` created from `mvp/program-integration`; Wave 0 docs/research work opened. No addon code authorized or changed.
- **MVP Program Bootstrap (2026-07-15):** Established the control-room governance framework (this file and its siblings). Verified checkpoint integrity, created `mvp/program-integration`, audited the full repository, froze the MVP contract, and prepared Sol's launch prompt. Implementation remains frozen pending product-owner launch. Next: product owner reviews the bootstrap PR, then launches Sol with `../06-prompts/gpt56-sol-master-mvp-mission.md` at XHigh reasoning effort.
