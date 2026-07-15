# MVP Program State — Live Tracker

> This is the single live status tracker for the MVP completion program (`DEC-032`). Update this file at the start and end of every Sol session and every Claude control-room review — it is the first thing any new session should read. The relatively stable contract (scope, waves, authority) lives in `mvp-completion-program.md`; this file is the frequently-changing status. Do not duplicate the contract's content here — link to it.

## Current status

**WAVE 0 SUBMITTED — AWAITING CLAUDE CONTROL-ROOM REVIEW (2026-07-15).**

Freeze/resume status: **the issue #165 implementation freeze is lifted only for work authorized by DEC-032 and the master Sol mission, on branches descending from `mvp/program-integration`.** The product owner launched Sol on 2026-07-15 by issuing the complete master mission. Wave 0 is documentation/research only; no addon code is authorized in this wave.

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

**Wave 0 — Current-state reconciliation and research closure — SUBMITTED / GATE PENDING.** Working branch: `sol/wave-0-reconciliation-research`; draft PR [#169](https://github.com/AdamsOdoo/Adams/pull/169) targets `mvp/program-integration`. Scope remained `docs/**` only.

## Wave status

| Wave | Status | Branch/PR | Notes |
| --- | --- | --- | --- |
| 0 — Reconciliation & research closure | Awaiting control-room review | `sol/wave-0-reconciliation-research`; draft PR [#169](https://github.com/AdamsOdoo/Adams/pull/169) | DEC-033 and official-source refresh submitted; no addon/protected changes. |
| 1 — Read-only foundation integration (CORE-R1, SEC-1, LC-1, SRR-03 closure) | Not started / unauthorized | — | Blocked on Wave 0 acceptance; requires Odoo.sh runtime access. |
| 2 — Order import (Task 012) | Not started / unauthorized | — | SRR-03 is OPEN; blocked on accepted DEC-033, Wave 1 prerequisites/closure evidence, and packet gate. |
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

1. **Wave 0 control-room decisions** — DEC-033 is Proposed; Claude must accept/revise it and align DEC-027/028/029/030 before Wave 0 completes.
2. **Wave 1 authorization/runtime access** — no Wave 1 work may start before PR #169's gate; Odoo.sh dev-build access is required for its definition of done.
3. **Dev-store access provisioning** — Wave 6 and mutation-domain UAT require human-provisioned Shopify Partner/dev-store credentials; Sol cannot self-provision them (hard-stop 5).

## Open decisions (full list: `mvp-completion-program.md` §9)

1. DEC-033 proposes retaining Task 015/015B in MVP Wave 5 after Layer 2; pending Claude acceptance.
2. DEC-033 reconciles SRR-03 to OPEN and proposes a Wave 1 closure sub-gate; pending Claude acceptance and later runtime proof.
3. PR #150/#151 administrative closure as superseded is recommended; Sol took no action; control-room/product-owner decision pending.
4. DEC-027 explicit deferral and DEC-028/029/030 acceptance timing are proposed in DEC-033; status changes pending Claude.
5. Hazard branch: proposed leave untouched; it remains untouched.
6. Empty requirements file: proposed leave untouched; it remains untouched.

## Runtime evidence log

| Date | Wave | Evidence | Odoo.sh build | Result |
| --- | --- | --- | --- | --- |
| 2026-07-15 | Checkpoint (pre-program) | `../05-qa/task-core-r2-validation-results.md` §IS2 | `34935129` | Fresh install 0/0 across core/product/sale; issue #157 artifact only known failure class. |

*(No runtime evidence has been generated by this program yet — the row above is the inherited checkpoint evidence, carried forward for context.)*

## Next control-room gate

Claude control-room review of draft PR [#169](https://github.com/AdamsOdoo/Adams/pull/169): accept/revise DEC-033, apply the DEC-027/028/029/030 status effects if accepted, confirm the Wave 1/2 gates, and merge only if the Wave 0 definition of done is met.

## Sprint checkpoint log

- **Wave 0 submission (2026-07-15):** Docs-only PR #169 opened. DEC-033, official-source refresh, contract/matrix/risk/Task-012 alignment, and session QA/handoff were prepared. No runtime evidence or addon/protected change. Awaiting Claude control-room review; Wave 1 unauthorized.

- **Wave 0 start (2026-07-15):** Product-owner launch received; protected refs verified; `sol/wave-0-reconciliation-research` created from `mvp/program-integration`; Wave 0 docs/research work opened. No addon code authorized or changed.
- **MVP Program Bootstrap (2026-07-15):** Established the control-room governance framework (this file and its siblings). Verified checkpoint integrity, created `mvp/program-integration`, audited the full repository, froze the MVP contract, and prepared Sol's launch prompt. Implementation remains frozen pending product-owner launch. Next: product owner reviews the bootstrap PR, then launches Sol with `../06-prompts/gpt56-sol-master-mvp-mission.md` at XHigh reasoning effort.
