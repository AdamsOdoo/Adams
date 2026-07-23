# Wave 5 U1 — Gate A Handoff

> **Status: Gate A planning artifact — Docs-only. NOT accepted. Not self-accepted,
> not ready-marked, not merged.** Produced 2026-07-23; **corrected 2026-07-23** per
> control-room comment `5056513213` (`REVISE — one consolidated docs-only
> correction`); then **status-layer synthesis reset 2026-07-23** per control-room
> ruling `5058042330` (resolving the confirmed material-P2 in independent review
> `5057796514`). **`STATUS-LAYER SYNTHESIS RESET COMPLETE — AWAITING FRESH
> INDEPENDENT REVIEW`.** Follows `docs/06-prompts/session-handoff-template.md`
> adapted to the macro-wave model.

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

## 4. Key rulings (control-room comment `5056513213` applied — 2026-07-23 correction)

- **SEC-2:** defined sufficiently → Gate A planning **not blocked**; **D-P0-2
  resolved SEC-2-FIRST (binding)** — U1 implementation blocked until SEC-2 merges
  runtime-green. No parallel four-internal-group path. U1 customer-facing UI
  **visibility** gates on the two SEC-2 roles (Connector User, Connector
  Administrator); the four internal groups remain server-side capability primitives.
- **Branch:** **Option A ACCEPTED (binding)** — wait for PR #189 (and SEC-2) merge;
  do not stack.
- **Module:** inside `shopify_connector_fulfillment` (PD-2/DEC-016(A)); no `_ui`
  addon — ACCEPTED.
- **Numbering:** task-U1 (fulfillment experience) ≠ packet-U1 (core surface,
  delivered by U0); a **fresh** U1 locked prompt is supplied (D-P1-1 ACCEPTED; old
  prompt retired).
- **Wizard:** `TransientModel` **display-and-delegate only** (D-P1-5 ACCEPTED
  CONDITIONALLY) — no eligibility/blocker/review-required decision.
- **Package import:** addon root `__init__.py` imports `wizards` (once);
  `models/__init__.py` must **not** import the sibling wizards package.
- **Browser/render evidence:** **REQUIRED before U1 merge** (D-P1-6); not
  auto-inherited from U0 deferments.
- **Product/UX contracts (D-P0-3):** **NOT YET ACCEPTED** — still-Proposed; see the
  Gate-A prerequisite & status table (`README.md` §4).
- **Overall:** `DOCS CORRECTED — AWAITING FRESH INDEPENDENT GATE-A REVIEW`.

## 5. Decision status after the correction (control-room comment `5056513213`)

- **P0:** D-P0-1 (branch) **ACCEPTED**; D-P0-2 (SEC-2 sequencing) **RESOLVED
  SEC-2-first**; D-P0-3 (load-bearing Proposed product/UX contracts) **NOT YET
  ACCEPTED — the one remaining open P0** (independent acceptance required; the
  Wave-5 gates G5-1…G5-9 all remain unchecked).
- **P1:** D-P1-1…D-P1-6 all **resolved** by the control-room comment (numbering
  accepted; module accepted; SEC-2 fulfillment scope = two-role UI + internal-group
  server; inventory boundary display-only; wizard display-and-delegate; browser
  evidence required before merge).
- **P2:** D-P2-1 (vocabulary — code authoritative, product docs annotated),
  D-P2-2 (native tracking timeline), D-P2-3 (no mode-switch history model),
  D-P2-4 (dark mode outside U1), D-P2-5 (consequences = display-only; dynamic
  preflight is a separate backend task) — all **resolved**; **D-P2-6 (status-layer
  & badge taxonomy) — `RESET`** by control-room ruling `5058042330` (this session):
  the canonical status-source & badge matrix (`u1-backend-ui-contract-inventory.md`
  §12) fixes the confirmed material-P2 — A7 (`display_status_*`, display-only, not a
  carrier milestone), A5 only from `delivered_inconsistency` + `tracking_snapshot`,
  **A2 deferred (no seam, no badge)**, layers never merged, acceptance A22. (Full
  detail: `u1-risks-and-open-questions.md`; status table: `README.md` §4.)

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
  Wave 4 (and SEC-2) merge; U1 is a **premium UI gate** whose browser/render
  evidence is **required before merge** (not auto-inherited from U0's deferments) —
  a browser class may be deferred only after a concrete attempt + a separate
  control-room ruling, and a deferred class is never represented as passed.
- **Correction-cycle learning (2026-07-23, control-room comment `5056513213`):** the
  most valuable catch was that a role-sequencing model can be *locally* plausible in
  each file yet *globally* contradictory across the package — the SEC-2-first
  intent lived in one doc while a "parallel four-internal-group" alternative
  survived in the locked prompt and risk log. Fix: bind customer-facing UI
  **visibility** to the two SEC-2 roles and keep the four internal groups strictly
  server-side, then sweep every file for the removed alternative. Second lesson: an
  Odoo **package-import boundary** (root `__init__.py` imports `wizards`;
  `models/__init__.py` must not) is easy to state loosely and get wrong — pin it
  with structural tests. Both are now enforced by acceptance rows A20/A21 and the
  consistency sweep.
- **Synthesis-reset learning (2026-07-23, control-room ruling `5058042330`):** a
  status *badge taxonomy* can pass a field-existence check yet still bind the wrong
  **layer** — UX/IA §8 mapped the real fields `display_status_*` to the wrong Shopify
  family (A5 instead of A7) and asserted an A2 badge with **no backing field at all**.
  Two lessons: (a) verify not just that a field exists but *which layer it carries*,
  by reading the exact population site (`inbound.py` → `display_status_* =
  node['displayStatus']` = A7) and the field's own code comment; and (b) **never
  infer a badge from a Shopify enum the connector does not persist** (A2/A3/A6 have no
  seam → deferred, no badge). Fix: one **canonical status-source & badge matrix**
  (contract §12) that every dependent doc/prototype links to instead of re-deriving,
  plus an acceptance criterion (A22) that proves per-layer label/icon/severity
  correctness and the A5≠A7, no-phantom-A2 invariants. Also surfaced a genuine
  backend-completeness item: `delivered_inconsistency` /
  `review_reason='delivered_not_validated'` are declared but never written at
  `2d9cff0` — recorded honestly rather than papered over.

## 7. Exact next-session prompt

```text
CLAUDE CODE — WAVE 5 U1 GATE A FRESH INDEPENDENT REVIEW (docs-only gate; post-correction)

Run in a FRESH top-level Claude session (or a fresh subagent), memoryless of the
authoring/correction sessions' reasoning but NOT repository-blind. Independently
review the CORRECTED Wave 5 U1 Gate A package on branch claude/wave-5-u1-gate-a
(draft PR #194 to mvp/program-integration), at the new corrected head SHA.

This is a DOCUMENTATION/GOVERNANCE-ONLY batch (DEC-040): verify by repository/diff/
path/link/consistency checks — NO Odoo.sh runtime campaign is required or to be
fabricated.

Verify from scratch:
  1. Identity gate holds live (integration tip dd0af5d…; PR #189 head 2d9cff0
     open/draft/unmerged unless legitimately merged; PR #192 merged; issues
     #185/#193 open).
  2. NO addons/** file changed by this branch; diff is docs-only.
  3. Every model/field/selection/action cited in u1-backend-ui-contract-inventory.md
     EXISTS at exact Wave 4 head 2d9cff0 (spot-check against the source), and no
     invented selection/job/error/source or group XML id appears.
  4. The SEC-2 ruling, branch strategy, and module recommendation are consistent
     with wave-5-definition-of-ready.md, final-mvp-module-and-dependency-architecture.md
     (PD-2/PD-7), DEC-016/036/038/039/040, and the rejected-approaches log.
  5. The locked prompt's allowed/forbidden files are exact and internally consistent
     with the task breakdown and module recommendation.
  6. Markdown links resolve; no Shopify operation occurred; working tree clean.
  7. SEC-2 sequencing is coherent everywhere: SEC-2-first is binding, NO parallel
     four-internal-group implementation path survives; U1 customer-facing UI
     visibility = the two SEC-2 roles (Connector User = new group_shopify_connector_user,
     Connector Administrator = existing group_shopify_connector_admin), server
     authorization = the four internal groups; both layers are tested.
  8. The package-import allowlist is correct: addon root __init__.py imports wizards
     (once); wizards/__init__.py imports the wizard model; models/__init__.py does
     NOT import the sibling wizards package; import-structure tests are required.
  9. The mode-switch wizard is frozen display-and-delegate: no eligibility/blocker/
     review-required decision, no target-mode/argument choice, no Job/mutation; any
     count is bounded, ACL-safe, and labelled non-authoritative.
 10. Proposed product/UX documents remain Proposed (not silently accepted); the
     Gate-A prerequisite & status table (README §4) is accurate; browser/render
     evidence is required before U1 merge (not silently waived); superseded
     vocabulary is annotated non-destructively (docs unchanged).
 11. AR-079, TD-003, mvp-program-state.md, research-handoff.md, and the handoff all
     agree with the corrected package.
 12. STATUS-LAYER SYNTHESIS RESET is correct and complete: the canonical
     status-source & badge matrix (u1-backend-ui-contract-inventory.md §12) matches
     the exact Wave 4 source at 2d9cff0 — display_status_* = A7 (display-only, never
     a carrier milestone); A5 only from delivered_inconsistency + parsed
     tracking_snapshot (never from A7; no full A5 enum timeline); A2
     FulfillmentOrderStatus DEFERRED (no backing field, no badge); A4 =
     fulfillment_status_* (automation authority + display); A1 only via
     order_binding_id.shopify_fulfillment_status_snapshot; A3/A6 outside U1. No
     A5/A7 merge, no phantom A2, no layer-merging survives anywhere in the package,
     the prototypes, the acceptance matrix (A22), or the locked prompt. The
     error_class count reads 19; the ALLOWED FILES headers are unambiguous about the
     repo-root docs/ paths; the delivered-inconsistency data-inert caveat is
     recorded honestly.
Post the verbatim review at the exact reviewed SHA. Do not accept/ready-mark/merge
if you are also the author. Recommend ACCEPT or REVISE (one consolidated correction).
```

## 8. Stop

This session stops here. No implementation occurred; no Shopify operation occurred.
Await independent Claude review / control-room acceptance before any acceptance,
ready-marking, or merge.
