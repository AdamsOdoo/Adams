# MVP Program State — Live Tracker

> This is the single live status tracker for the MVP completion program (`DEC-032`). Update this file at the start and end of every Sol session and every Claude control-room review — it is the first thing any new session should read. The relatively stable contract (scope, waves, authority) lives in `mvp-completion-program.md`; this file is the frequently-changing status. Do not duplicate the contract's content here — link to it.

## Current status

**WAVE 0 IN PROGRESS — SOL LAUNCHED BY PRODUCT OWNER (2026-07-15).**

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

**Wave 0 — Current-state reconciliation and research closure — IN PROGRESS.** Working branch: `sol/wave-0-reconciliation-research`; PR not yet opened. Scope is limited to `docs/**`. See `mvp-completion-program.md` §4 and §9.

## Wave status

| Wave | Status | Branch/PR | Notes |
| --- | --- | --- | --- |
| 0 — Reconciliation & research closure | In progress | `sol/wave-0-reconciliation-research`; PR pending | Product-owner launch received 2026-07-15; docs/research only. |
| 1 — Read-only foundation integration (CORE-R1, SEC-1) | Not started | — | Blocked on Wave 0 only where a decision affects it (e.g. DEC-028). |
| 2 — Order import (Task 012) | Not started | — | Blocked on Wave 0 decision #2 (SRR-03 reconciliation) and Wave 1. |
| 3 — Inventory synchronization (Task 013/013B) | Not started | — | Blocked on Wave 2 and DEC-031 Layer 2 design+acceptance. |
| 4 — Fulfillment and tracking (Task 014) | Not started | — | Blocked on Wave 3 (Layer 2 proven). |
| 5 — Premium operator experience (UI U1–U3, PERF-1) | Not started | — | Blocked on Wave 1 (SEC-1) + relevant domain waves per screen. |
| 6 — E2E integration, UAT, release readiness | Not started | — | Blocked on Waves 1–5. |

## Active Sol session (Wave 0 start — 2026-07-15)

- Re-verified live protected references before branching: checkpoint `acd8c4691e72cf5590f2a56228b08f183b76cd9a`; integration tip `283e0512aa5f819444ff2ea28c25eae9a5d95065` (checkpoint plus governance bootstrap/tracker upkeep only); `Shopify-connector` `dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b`; `main` `a5d45432a9b60f724c1aff700f4b371ea019960e`; PR #150/#151 heads unchanged.
- Read DEC-032, the program contract, this live state, the acceptance matrix, `GPT_SOL.md`, `CLAUDE.md` including §13, and all 24 binding rejected-approach rows.
- Created `sol/wave-0-reconciliation-research` from the live `mvp/program-integration` tip.
- No addon code, protected reference, PR #150/#151, issue #165, or hazardous branch was modified.

## Prior completed work (bootstrap governance)

- Verified all protected references match the task's expected state (checkpoint SHA, issue #165, PR #163 merge target, `Shopify-connector`, `main`, PR #150/#151 heads) — no drift found.
- Created `mvp/program-integration` from the exact checkpoint SHA.
- Ran a 10-workstream evidence-based repository audit (addons/manifests, architecture/decisions, research, QA/runtime evidence, PR #150, PR #151, issues/risk register, operator UX, tests/CI, implementation-plan/prompt history).
- Produced `mvp-completion-program.md` (frozen MVP contract + macro-waves + Sol authority + hard-stops), this state file, `../05-qa/mvp-acceptance-matrix.md`, `DEC-032-mvp-autonomous-execution-model.md`, `../06-prompts/gpt56-sol-master-mvp-mission.md`, `../06-prompts/claude-mvp-wave-review-template.md`, a `CLAUDE.md` addendum, and root `GPT_SOL.md`.
- Merged the governance bootstrap via PR [#166](https://github.com/AdamsOdoo/Adams/pull/166) and opened the master program issue [#167](https://github.com/AdamsOdoo/Adams/issues/167).
- No addon code created or modified. No macro-wave opened. No live Shopify/Odoo runtime call made.

## Blockers

1. **SRR-03 status contradiction** (`mvp-completion-program.md` §2 finding 7, §9 item 2) — must be reconciled before Wave 2 starts.
2. **Product export scope question** (§9 item 1) — must be decided before Wave 5 (or a scope amendment recorded) so Sol doesn't have to guess.
3. **Odoo.sh / dev-store access provisioning** — every wave needs a manually-invoked Odoo.sh dev-build session for runtime evidence (no CI exists); Wave 6 additionally needs live dev-store Shopify credentials for VAL-B2, which have never been provisioned in this repository's history. This is a product-owner-provisioning item, not something Sol can self-serve (hard-stop condition 5).

## Open decisions (full list: `mvp-completion-program.md` §9)

1. Product export (Task 015/015B) scope disposition.
2. SRR-03 "CLOSED" vs. "OPEN" reconciliation.
3. PR #150/#151 administrative disposition (recommend: close/mark superseded; requires explicit sign-off).
4. DEC-027/028/029/030 acceptance timing.
5. `claude/task-012-decision-closure-mb88sn` disposition (recommend: leave untouched).
6. `addons/requirements.txt` literal-compliance nuance (informational; no action recommended).

## Runtime evidence log

| Date | Wave | Evidence | Odoo.sh build | Result |
| --- | --- | --- | --- | --- |
| 2026-07-15 | Checkpoint (pre-program) | `../05-qa/task-core-r2-validation-results.md` §IS2 | `34935129` | Fresh install 0/0 across core/product/sale; issue #157 artifact only known failure class. |

*(No runtime evidence has been generated by this program yet — the row above is the inherited checkpoint evidence, carried forward for context.)*

## Next control-room gate

Wave 0 completion review, once Sol closes or explicitly defers every item in `mvp-completion-program.md` §9 and opens the docs-only wave PR.

## Sprint checkpoint log

- **Wave 0 start (2026-07-15):** Product-owner launch received; protected refs verified; `sol/wave-0-reconciliation-research` created from `mvp/program-integration`; Wave 0 docs/research work opened. No addon code authorized or changed.
- **MVP Program Bootstrap (2026-07-15):** Established the control-room governance framework (this file and its siblings). Verified checkpoint integrity, created `mvp/program-integration`, audited the full repository, froze the MVP contract, and prepared Sol's launch prompt. Implementation remains frozen pending product-owner launch. Next: product owner reviews the bootstrap PR, then launches Sol with `../06-prompts/gpt56-sol-master-mvp-mission.md` at XHigh reasoning effort.
