# Wave 5 U1 — Branch & Dependency Strategy (recommendation)

> **Status: Gate A planning artifact — Docs-only. NOT accepted.** Produced
> 2026-07-23; **corrected 2026-07-23** — **Option A is ACCEPTED (binding) by
> control-room comment `5056513213`** (D-P0-1). Recommends exactly one branch
> strategy for the **future** U1 implementation session. This Gate A (docs-only)
> session itself already uses `claude/wave-5-u1-gate-a` branched from the
> integration tip `dd0af5d94a7f730e738dca955971e00bb4cc9122`.

## 1. The dependency fact that drives everything

U1 is UI for the **already-accepted Wave 4 fulfillment backend**. The models,
fields, selection values and actions U1 binds to
(`u1-backend-ui-contract-inventory.md`) exist **only on the Wave 4 branch
`claude/wave-4-fulfillment-gate-b` at `2d9cff0`** — they are **not** on
`mvp/program-integration@dd0af5d9` yet, because PR #189 is open/draft/unmerged.

Therefore any U1 **implementation** (views/actions/tests) that must install,
compile, and runtime-test against real Wave 4 fields **requires a base that
contains Wave 4 code**. Docs (this Gate A) do not, which is why this session
branches cleanly from the integration tip.

## 2. Current state of the Wave 4 dependency (as of 2026-07-23)

- PR #189 head `2d9cff0` is a **frozen candidate**; the reconciled base merge is
  accepted (comment `5055035975`); exact-SHA Odoo.sh runtime is **substantively
  green** (build `35313169`: install `1348/1348`, fulfillment `203/203`, U0/Test
  Connection `67/67`, sale `194/194`, inventory `247/247`).
- The **nine-process concurrency campaign is `DEFERRED BY PRODUCT OWNER — NOT
  PROVEN` for PR #189 merge only** (comment `5055372944`); PR #189 is
  `READY FOR INDEPENDENT TIER 1 REVIEW`, still draft/unmerged.
- A Tier-1 independent review has **not yet accepted** the head; under the
  DEC-040 one-correction rule a single consolidated **REVISE** correction to
  `2d9cff0` remains possible before merge.

## 3. Options evaluated

### Option A — Wait for PR #189 merge, branch U1 from the new integration tip **[RECOMMENDED]**

Create the U1 implementation branch from `mvp/program-integration` **after** PR #189
merges; the tip then contains Wave 4 code, so U1 installs/tests against real fields.

### Option B — Stacked U1 branch from `2d9cff0`, draft PR based on the Wave 4 branch, retarget after #189 merges

Branch U1 off the exact Wave 4 head; open the U1 draft PR against
`claude/wave-4-fulfillment-gate-b`; retarget to `mvp/program-integration` once #189
merges.

### Option C — U1 from current integration, don't compile against Wave 4 until later

Branch U1 from `dd0af5d9` and defer any compile/test against Wave 4 fields.

## 4. Decision matrix

| Criterion | A (wait) | B (stacked) | C (current tip) |
|---|---|---|---|
| Governance / wave-5 DoR sequence (SEC-2 → PERF-1 → U1) | **Aligned** — U1 isn't the immediate next step anyway | Tolerated but front-runs sequence | Front-runs sequence |
| Review independence (DEC-040) | **Best** — U1 diff is purely U1 | Poor — Wave 4's 11k-line diff shows in U1's PR until retarget | Good |
| Merge-history clarity | **Best** — linear, U1 lands on a Wave-4-containing tip | Retarget churn; risk of Wave 4 commits in U1 history | Clean but U1 can't build |
| Rollback simplicity | **Best** | Coupled to Wave 4 branch state | N/A (can't ship) |
| Conflict risk | Low | Medium (rebase if #189 is corrected) | Low |
| Odoo.sh: can test real Wave 4 fields | **Yes** (post-merge tip) | Yes (Wave 4 head) | **No** — fields absent |
| If PR #189 gets a correction | **Unaffected** (wait) | Must rebase onto corrected head | Unaffected but still can't build |
| Fastest safe route to a *reviewable, buildable* U1 | **Yes** | Faster start, slower/ riskier finish | Blocked |

## 5. Decision — **Option A (ACCEPTED, binding — control-room comment `5056513213`)**

**Option A is the accepted, binding branch strategy (D-P0-1). Option B is a
contingency the control room did NOT authorize.** Additionally, because D-P0-2 is
resolved **SEC-2-first**, U1 implementation must also wait for **SEC-2** to merge
runtime-green (and PERF-1 per the DoR sequence), not only PR #189.

**Wait for PR #189 to merge, then branch the U1 implementation session from the new
`mvp/program-integration` tip.** Rationale:

1. **U1 genuinely cannot install or runtime-test without Wave 4 code** — Option C
   is not viable, and every code batch requires genuine Odoo.sh runtime evidence
   (CLAUDE.md §13), which needs Wave 4 fields present.
2. **Review independence and clean history are DEC-040 priorities.** Option B
   entangles U1's diff and history with Wave 4 until retarget; Option A keeps
   U1's PR a clean docs+`shopify_connector_fulfillment` UI diff on a stable base.
3. **PR #189 may still receive one consolidated correction.** Option B would then
   force a rebase of the U1 stack onto the corrected head; Option A sidesteps this
   entirely.
4. **The wait is effectively free.** The wave-5 DoR binds the sequence **SEC-2 →
   PERF-1 → U1**; U1 implementation is not authorised to start until SEC-2 (and
   PERF-1) land and the control room opens the U1 gate. PR #189 is at its review
   gate now, so it is expected to merge well before the U1 gate opens.

**Answer to the Gate A question "may U1 production implementation safely start
before PR #189 merges, using a stacked branch?" → No, not recommended.** Gate A
planning proceeds now; U1 implementation waits for the Wave 4 merge (and its own
gate). Option B is retained only as a contingency if the control room later
decides U1 must begin in parallel and explicitly accepts the retarget/rebase and
diff-entanglement costs.

## 6. Concrete plan for the U1 implementation session (when authorised)

1. Confirm PR #189 merged; fetch `mvp/program-integration`; verify the tip
   contains the U0 merge and the Wave 4 merge.
2. Confirm SEC-2 status per `u1-sec2-preflight-ruling.md` and the control-room
   gate for U1 is open.
3. `git checkout -B claude/wave-5-u1-implementation <new-integration-tip>` (a new
   branch; **not** this Gate A branch).
4. Implement strictly per `u1-locked-implementation-prompt.md` (allowed/forbidden
   files exact); one draft PR to `mvp/program-integration`; stop for independent
   review. No self-accept/ready-mark/merge.

## 7. Non-negotiables carried forward

- CV-013 (issue #185) stays open/critical — U1 must never present live-mutation
  qualification as proven, and U1 ships **no** Shopify request/mutation.
- The nine-process concurrency obligation remains a release/UAT gate (not U1's).
- Checkpoint `checkpoint/core-r2-readonly-uat-2026-07-15` is never touched.
