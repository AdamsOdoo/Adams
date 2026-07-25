# Wave 5 U1 — Branch & Dependency Strategy (recommendation)

> **Status: Gate A planning artifact — Docs-only. NOT accepted.** Produced
> 2026-07-23; **corrected 2026-07-23** — **Option A is ACCEPTED (binding) by
> control-room comment `5056513213`** (D-P0-1); **re-anchored 2026-07-25** onto the
> current integration tip `2583081f97c94428dfd10325589b1b891eea240b`, at which point
> **Option A's precondition became satisfied**. Recommends exactly one branch
> strategy for the **future** U1 implementation session. This Gate A (docs-only)
> branch `claude/wave-5-u1-gate-a` was originally cut from `dd0af5d9…` *(historical)*
> and has since been merged forward — without rebase or force-push — onto
> `2583081f`.

## 1. The dependency fact that drove everything — **now satisfied**

U1 is UI for the Wave 4 fulfillment backend. The models, fields, selection values
and actions U1 binds to (`u1-backend-ui-contract-inventory.md`) **now exist on
`mvp/program-integration@2583081f`**: PR #189 merged (merge commit `3a1afa43`), and
PR #203 merged on top of it (merge commit `2583081f`).

*(Historical, superseded: this section previously read "they exist only on the Wave
4 branch `claude/wave-4-fulfillment-gate-b` at `2d9cff0` … because PR #189 is
open/draft/unmerged." That statement described 2026-07-23 and is no longer true.)*

A U1 **implementation** that must install, compile and runtime-test against real
Wave 4 fields therefore no longer lacks a base. What it still lacks is
**authorization** — see §5.

## 2. Current state of the Wave 4 dependency (present tense, 2026-07-25)

- **PR #189 is MERGED.** Runtime-tested implementation candidate
  `25639f17be14b30a52a8453f0813aa0b764de310`; accepted PR head
  `e12145ce8bb88c099208f025d3cbb656bf0393ca` (only the accepted documentation
  reconciliation sits above the runtime candidate); Wave 4 merge commit
  `3a1afa43f8d07a7dae1799968273fa0ab8049490`
  ([merge record](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5077385366)).
- **SEC-2 (#196) is MERGED and the issue is closed as completed.**
- **Current-backend SEC-3 is MERGED**; issue **#197 remains OPEN** (future
  Wave-5-added surfaces + external multi-user UAT/RC confirmation).
- **PERF-0 baseline is MERGED**; issue **#199 remains OPEN** (Shopify-read
  reconciliation handlers + release thresholds). Baseline numbers are
  **baseline-only** and are never restated as performance guarantees.
- **Pre-Wave-5 stabilization PR #203 is MERGED** — accepted head `d282ab03`,
  merge commit `2583081f` = the current integration tip.
- **All live-Shopify validation remains DEFERRED** until the Wave 5 implementation
  candidate is complete and frozen (2026-07-25 product-owner sequencing ruling).
  Gate D, CV-013 (#185), provisioning (#200), external UAT and release readiness
  are **open and unclaimed**; the deferral is not a waiver.

*(Historical, superseded: the earlier text here described `2d9cff0` as a frozen
candidate awaiting Tier-1 review, quoted the build `35313169` suite counts
`1348/203/67/194/247`, and recorded the nine-process campaign as deferred for PR
#189 merge only. Those were true of 2026-07-23; the accepted Wave 4 runtime record
is the one attached to PR #189 at `25639f17`, and the current integrated suite
baseline is the PR #203 record.)*

## 3. Options evaluated

### Option A — Wait for PR #189 merge, branch U1 from the new integration tip **[ACCEPTED — precondition now satisfied]**

Create the U1 implementation branch from `mvp/program-integration` **after** PR #189
merges; the tip then contains Wave 4 code, so U1 installs/tests against real fields.

### Option B *(historical — not authorized, and now moot: PR #189 is merged)* — Stacked U1 branch from `2d9cff0`, draft PR based on the Wave 4 branch, retarget after #189 merges

Branch U1 off the exact Wave 4 head; open the U1 draft PR against
`claude/wave-4-fulfillment-gate-b`; retarget to `mvp/program-integration` once #189
merges.

### Option C *(historical — never viable, and now moot)* — U1 from the then-current integration, don't compile against Wave 4 until later

Branch U1 from the then-current integration tip `dd0af5d9` *(historical)* and defer any compile/test against Wave 4 fields.

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

## 5. Decision — **Option A (ACCEPTED, binding — control-room comment `5056513213`); precondition SATISFIED, authorization still MISSING**

**Option A is the accepted, binding branch strategy (D-P0-1). Option B is a
contingency the control room did NOT authorize.** Its two waiting conditions — PR
#189 merged, and SEC-2 merged runtime-green (D-P0-2) — are **both satisfied as of
2026-07-25**. Option C was never viable and is now moot.

**Satisfying the branch precondition does not authorize U1 implementation.** What
still blocks it: this Gate-A package has not been independently reviewed since the
re-anchor; **D-P0-3** is unresolved; the Wave-5 **G5-1…G5-9** gates are unchecked;
and the control room has neither opened the U1 gate nor **bound the exact
implementation base SHA**. The locked implementation prompt therefore carries an
unbound `<U1-IMPLEMENTATION-BASE-SHA>` placeholder — **`2583081f` is this docs PR's
reconciliation anchor, not a pre-authorized implementation base.**

**When authorized: branch the U1 implementation session from the exact
`mvp/program-integration` tip the control room binds at that moment.** Rationale:

1. **U1 genuinely cannot install or runtime-test without Wave 4 code** — Option C
   was never viable, and every code batch requires genuine Odoo.sh runtime evidence
   (CLAUDE.md §13), which needs Wave 4 fields present. Those fields are now on the
   tip.
2. **Review independence and clean history are DEC-040 priorities.** Option B
   entangles U1's diff and history with Wave 4 until retarget; Option A keeps
   U1's PR a clean docs+`shopify_connector_fulfillment` UI diff on a stable base.
3. **PR #189 did in fact receive further correction cycles before merging.** Option
   B would have forced repeated rebases of a U1 stack onto each corrected head;
   Option A sidestepped this entirely. *(This is now a settled outcome, not a
   forecast.)*
4. **The wait cost nothing.** The wave-5 DoR binds the sequence **SEC-2 → PERF-1 →
   U1**; SEC-2 landed inside PR #203 alongside the pre-Wave-5 stabilization, well
   before the U1 gate opened — and the U1 gate is still not open.

**Answer to the original Gate A question "may U1 production implementation safely
start before PR #189 merges, using a stacked branch?" → No, and the question is now
moot: PR #189 is merged.** The live question is the different one answered above —
the base exists, the **authorization** does not. Option B is retained only as a
historical contingency and is not applicable.

## 6. Concrete plan for the U1 implementation session (when authorised)

1. Fetch `mvp/program-integration` and verify the tip the control room has bound
   as the implementation base — do **not** assume `2583081f`; it is this docs PR's
   reconciliation anchor and integration may have moved. Verify the tip contains
   the U0 merge, the Wave 4 merge (`3a1afa43`) and the PR #203 merge.
2. Confirm SEC-2 (merged) and current-backend SEC-3 (merged, **#197 still open**)
   per `u1-sec2-preflight-ruling.md`, and that the control-room gate for U1 is
   **open** and this Gate-A package has been independently reviewed and accepted.
3. `git checkout -B claude/wave-5-u1-implementation <new-integration-tip>` (a new
   branch; **not** this Gate A branch).
4. Implement strictly per `u1-locked-implementation-prompt.md` (allowed/forbidden
   files exact); one draft PR to `mvp/program-integration`; stop for independent
   review. No self-accept/ready-mark/merge.

## 7. Non-negotiables carried forward

- CV-013 (issue #185) stays open/critical — U1 must never present live-mutation
  qualification as proven, and U1 ships **no** Shopify request/mutation. All
  live-Shopify validation stays deferred until the Wave 5 implementation candidate
  is complete and frozen.
- Issue **#197** (SEC-3, narrowed) and issue **#199** (PERF-0, narrowed) remain
  **open**; neither is closed or claimed complete by U1.
- The external-multiprocessing/concurrency obligation remains a release/UAT gate
  (not U1's) and is never represented as passed.
- Checkpoint `checkpoint/core-r2-readonly-uat-2026-07-15` is never touched.
