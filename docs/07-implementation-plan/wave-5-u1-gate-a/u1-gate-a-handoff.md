# Wave 5 U1 — Gate A Handoff

> **Status: Gate A planning artifact — Docs-only. NOT accepted. Not self-accepted,
> not ready-marked, not merged.** Produced 2026-07-23. Follows
> `docs/06-prompts/session-handoff-template.md` adapted to the macro-wave model.

## 1. Session objective (met)

Prepare the complete Wave 5 U1 Definition of Ready + implementation packet for the
**fulfillment operator experience**, entirely against the accepted Wave 4 backend,
while PR #189 proceeds through independent Tier 1 review. **Docs-only; no U1 code;
no Shopify operation.**

## 2. Identity gate (all passed)

Repo `AdamsOdoo/Adams`; `mvp/program-integration` = `dd0af5d94a7f730e738dca955971e00bb4cc9122`
(local + remote); PR #189 open/draft/unmerged, head `2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a`;
PR #192 merged/closed; U0 merge `8818c771…` ancestor of the tip; issue #185 (CV-013)
open/critical; issue #193 open; product-owner nine-process deferment recorded on
PR #189 (comment `5055372944`); clean tree; no merge/rebase/cherry-pick in progress.

## 3. What was produced

The 13 outputs under `docs/07-implementation-plan/wave-5-u1-gate-a/**` (see
`README.md`), plus updates to `research-handoff.md`, `mvp-program-state.md`, and
`architecture-review-log.md`. The **backend UI-contract inventory** was built by
directly reading the Wave 4 source at exact head `2d9cff0` (via a read-only
worktree); every referenced model/field/selection/action was source-verified.

## 4. Key rulings (for the control room)

- **SEC-2:** defined sufficiently → **not a hard stop**; U1 implementation
  sequencing is a control-room decision (D-P0-2).
- **Branch:** Option A (wait for PR #189 merge; do not stack). U1 implementation
  should not start before the Wave 4 merge and its own gate.
- **Module:** inside `shopify_connector_fulfillment` (PD-2/DEC-016(A)); no `_ui`
  addon.
- **Numbering:** task-U1 (fulfillment experience) ≠ packet-U1 (core surface,
  delivered by U0); a **fresh** U1 locked prompt is supplied (D-P1-1).
- **Overall:** `U1 GATE A READY FOR CONTROL-ROOM REVIEW`.

## 5. Open decisions the control room must resolve before U1 code

- **P0:** D-P0-1 (branch), D-P0-2 (SEC-2 sequencing), D-P0-3 (accept load-bearing
  product specs / G5-1 / two-role direction).
- **P1:** D-P1-1 (numbering), D-P1-2 (module AR), D-P1-3 (SEC-2 fulfillment scope
  gap), D-P1-4 (Mode-2↔inventory boundary), D-P1-5 (confirmation wizard), D-P1-6
  (browser-evidence posture).
- **P2:** vocabulary reconciliation, tracking-timeline surface, mode-switch history,
  theme parity, consequences read-model. (Full detail: `u1-risks-and-open-questions.md`.)

## 6. Learning feedback loop (per CLAUDE.md §12)

- **What made this efficient:** reading the **exact Wave 4 source** rather than
  trusting product docs caught three vocabulary divergences (origin classes, review
  reasons, reconciled states) that would otherwise have produced invented values in
  the UI — the single most important correctness win. A read-only worktree at the
  frozen head enabled this without disturbing the docs branch.
- **Process signal:** the corpus carries **three non-identical definitions of "U1"**
  and several `Proposed — not accepted` UX contracts. Gate A's value was largely in
  *reconciling* these and surfacing the acceptances (G5-1, roles, DEC-038) as
  explicit P0 decisions rather than assuming them.
- **Rejected-approaches discipline:** module placement was checked against
  RA-011/012/013 (monolith / micro-module / duplication) and PD-2 before
  recommending in-module placement — no rejected approach re-proposed.
- **Debt logged:** doc↔code vocabulary divergence recorded as documentation TD
  (see technical-debt register update) with the copy-deck reconciliation as the fix.
- **Carry-forward:** U1 code must generate its own Odoo.sh runtime evidence once
  Wave 4 merges; U0's deferred browser/lifecycle evidence classes remain
  `DEFERRED — NOT PROVEN` and must not be represented as passed.

## 7. Exact next-session prompt

```text
CLAUDE CODE — WAVE 5 U1 GATE A INDEPENDENT REVIEW (docs-only gate)

Run in a FRESH top-level Claude session (or a fresh subagent), memoryless of this
authoring session's reasoning but NOT repository-blind. Independently review the
Wave 5 U1 Gate A package on branch claude/wave-5-u1-gate-a (draft PR to
mvp/program-integration).

This is a DOCUMENTATION/GOVERNANCE-ONLY batch (DEC-040): verify by repository/diff/
path/link/consistency checks — NO Odoo.sh runtime campaign is required or to be
fabricated.

Verify from scratch:
  1. Identity gate holds live (integration tip dd0af5d…; PR #189 head 2d9cff0
     open/draft/unmerged; PR #192 merged; issues #185/#193 open).
  2. NO addons/** file changed by this branch; diff is docs-only.
  3. Every model/field/selection/action cited in u1-backend-ui-contract-inventory.md
     EXISTS at exact Wave 4 head 2d9cff0 (spot-check against the source), and no
     invented selection/job/error/source value appears.
  4. The SEC-2 ruling, branch strategy, and module recommendation are consistent
     with wave-5-definition-of-ready.md, final-mvp-module-and-dependency-architecture.md
     (PD-2/PD-7), DEC-016/036/038/039/040, and the rejected-approaches log.
  5. The locked prompt's allowed/forbidden files are exact and internally consistent
     with the task breakdown and module recommendation.
  6. Markdown links resolve; no Shopify operation occurred; working tree clean.
Post the verbatim review at the exact reviewed SHA. Do not accept/ready-mark/merge
if you are also the author. Recommend ACCEPT or REVISE (one consolidated correction).
```

## 8. Stop

This session stops here. No implementation occurred; no Shopify operation occurred.
Await independent Claude review / control-room acceptance before any acceptance,
ready-marking, or merge.
