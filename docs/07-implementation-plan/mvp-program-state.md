# MVP Program State — Live Tracker

> This is the single live status tracker for the MVP completion program (`DEC-032`). Update this file at the start and end of every Sol session and every Claude control-room review — it is the first thing any new session should read. The relatively stable contract (scope, waves, authority) lives in `mvp-completion-program.md`; this file is the frequently-changing status. Do not duplicate the contract's content here — link to it.

## Current status

**WAVE 0 ACCEPTED BY CLAUDE CONTROL ROOM — PENDING MERGE (2026-07-15).** DEC-033 is Accepted with two minor corrections applied on PR #169 (Wave 1 internal sub-stage note; hard-stop 11 rewording). DEC-028/029/030 are Accepted; DEC-027 remains Proposed/Deferred. PR #150/#151 administrative closure as superseded is authorized to proceed once PR #169 merges. The exact merge commit and resulting `mvp/program-integration` SHA are recorded in the control-room review comment on PR #169 and in the Wave 0 closure comment on issue #167 — not restated here, to avoid this table going stale the moment it is committed.

Freeze/resume status: **the issue #165 implementation freeze is lifted only for work authorized by DEC-032 and the master Sol mission, on branches descending from `mvp/program-integration`.** The product owner launched Sol on 2026-07-15 by issuing the complete master mission. Wave 0 is documentation/research only; no addon code is authorized in this wave. **Wave 1 is authorized to begin once PR #169 merges** (CORE-R1, SEC-1, LC-1, and the SRR-03 closure sub-gate, per `mvp-completion-program.md` §4). Wave 2 remains unauthorized and may not merge, be enabled, or receive live Shopify validation while SRR-03 remains OPEN.

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

**Wave 0 — Current-state reconciliation and research closure — ACCEPTED, PENDING MERGE.** Working branch: `sol/wave-0-reconciliation-research`; PR [#169](https://github.com/AdamsOdoo/Adams/pull/169) targets `mvp/program-integration`. Scope remained `docs/**` only. Wave 1 becomes the active wave once this PR merges.

## Wave status

| Wave | Status | Branch/PR | Notes |
| --- | --- | --- | --- |
| 0 — Reconciliation & research closure | Accepted by Claude control room, pending merge | `sol/wave-0-reconciliation-research`; PR [#169](https://github.com/AdamsOdoo/Adams/pull/169) | DEC-033 accepted with minor corrections; DEC-028/029/030 accepted; DEC-027 deferred; no addon/protected changes. |
| 1 — Read-only foundation integration (CORE-R1, SEC-1, LC-1, SRR-03 closure) | Authorized upon Wave 0 merge | — | Requires Odoo.sh runtime access. Recommended internal sub-stages: CORE-R1, SEC-1, LC-1, then SRR-03 closure. |
| 2 — Order import (Task 012) | Not started / unauthorized | — | SRR-03 is OPEN; blocked on Wave 1 prerequisites/closure evidence and packet gate. May not merge, be enabled, or receive live Shopify validation while SRR-03 remains open. |
| 3 — Inventory synchronization (Task 013/013B) | Not started | — | Blocked on Wave 2 and DEC-031 Layer 2 design+acceptance. |
| 4 — Fulfillment and tracking (Task 014) | Not started | — | Blocked on Wave 3 (Layer 2 proven). |
| 5 — Premium operator experience (UI U1–U3, PERF-1, Task 015/015B) | Not started / unauthorized | — | Proposed scope includes product export after Layer 2; pending DEC-033 acceptance and Waves 1–4. |
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

1. **PR #169 merge** — Accepted by Claude control room; merge into `mvp/program-integration` completes Wave 0.
2. **Wave 1 runtime access** — Odoo.sh dev-build access is required for CORE-R1/SEC-1/LC-1/SRR-03-closure evidence once Wave 1 opens.
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

Wave 1 macro-wave review (CORE-R1, SEC-1, LC-1, SRR-03 closure), once Sol opens that wave's PR into `mvp/program-integration` and it reaches its own definition of done, per `mvp-completion-program.md` §4 and `../06-prompts/claude-mvp-wave-review-template.md`.

## Sprint checkpoint log

- **Wave 0 acceptance (2026-07-15):** Claude control-room review accepted DEC-033 with two minor documentation corrections (Wave 1 internal sub-stage note; hard-stop 11 rewording), applied directly on PR #169. DEC-028/029/030 accepted; DEC-027 confirmed Proposed/Deferred. PR #150/#151 administrative closure as superseded authorized to proceed post-merge. Full review recorded as a PR #169 review comment and an issue #167 closure comment. Wave 1 authorized upon merge; Wave 2 remains blocked on SRR-03 closure.

- **Wave 0 submission (2026-07-15):** Docs-only PR #169 opened. DEC-033, official-source refresh, contract/matrix/risk/Task-012 alignment, and session QA/handoff were prepared. No runtime evidence or addon/protected change. Awaiting Claude control-room review; Wave 1 unauthorized.

- **Wave 0 start (2026-07-15):** Product-owner launch received; protected refs verified; `sol/wave-0-reconciliation-research` created from `mvp/program-integration`; Wave 0 docs/research work opened. No addon code authorized or changed.
- **MVP Program Bootstrap (2026-07-15):** Established the control-room governance framework (this file and its siblings). Verified checkpoint integrity, created `mvp/program-integration`, audited the full repository, froze the MVP contract, and prepared Sol's launch prompt. Implementation remains frozen pending product-owner launch. Next: product owner reviews the bootstrap PR, then launches Sol with `../06-prompts/gpt56-sol-master-mvp-mission.md` at XHigh reasoning effort.
