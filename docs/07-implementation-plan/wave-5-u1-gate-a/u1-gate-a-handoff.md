# Wave 5 U1 — Gate A Handoff

> **Status: Gate A planning artifact — Docs-only. NOT accepted. Not self-accepted,
> not ready-marked, not merged.** Produced 2026-07-23; **corrected 2026-07-23** per
> control-room comment `5056513213` (`REVISE — one consolidated docs-only
> correction`); then **status-layer synthesis reset 2026-07-23** per control-room
> ruling `5058042330` (resolving the confirmed material-P2 in independent review
> `5057796514`); then **re-anchored onto the current integration tip and reconciled
> against the final integrated backend on 2026-07-25** per the binding
> dependency-freeze ruling `5058829593`.
> **`RE-ANCHORED AND RECONCILED — FRESH INDEPENDENT GATE-A REVIEW STILL REQUIRED`.**
> **U1 implementation remains unauthorized.** Follows
> `docs/06-prompts/session-handoff-template.md` adapted to the macro-wave model.

## 1. Session objective (met)

Prepare the complete Wave 5 U1 Definition of Ready + implementation packet for the
**fulfillment operator experience**, entirely against the accepted Wave 4 backend,
while PR #189 proceeds through independent Tier 1 review. **Docs-only; no U1 code;
no Shopify operation.**

## 2. Identity gate

### 2.1 Present state — re-anchor identity gate (2026-07-25, all passed)

Repo `AdamsOdoo/Adams`. Verified live before any mutation:

| Check | Result |
|---|---|
| PR #194 | open, **draft**, unmerged; branch `claude/wave-5-u1-gate-a`; base `mvp/program-integration` |
| PR #194 frozen head before re-anchor | `b38e6874c45559dbf1219cfaec43f05ba5fc959a` (local = remote; no commit or force-push after it) |
| Historical merge-base | `dd0af5d94a7f730e738dca955971e00bb4cc9122`; branch exactly **3 commits ahead**, 70 behind |
| Changed paths before re-anchor | exactly **24**, all under `docs/**` |
| Current integration tip | `2583081f97c94428dfd10325589b1b891eea240b` (ordinary merge commit of PR #203; parents `3a1afa43` + `d282ab03`) |
| Last control-room ruling on PR #194 | comment `5058829593` — still the last |
| PR #189 | **merged**; head `e12145ce8bb88c099208f025d3cbb656bf0393ca`; merge commit `3a1afa43f8d07a7dae1799968273fa0ab8049490`; runtime candidate `25639f17be14b30a52a8453f0813aa0b764de310` |
| PR #203 | **merged** at `2583081f`; accepted head `d282ab03af6b27025f261788dd53dc354e1aa25e` |
| Issue #196 | **closed as completed** |
| Issues #197, #199 | **open** |
| Conflicts / blockers / later rulings | none unexpected |

### 2.2 Historical (2026-07-23 authoring session — superseded)

*Retained as the record of the original Gate-A session, not as current state:* repo
`AdamsOdoo/Adams`; `mvp/program-integration` = `dd0af5d94a7f730e738dca955971e00bb4cc9122`
(local + remote); PR #189 open/draft/unmerged, head `2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a`;
PR #192 merged/closed; U0 merge `8818c771…` ancestor of the tip; issue #185 (CV-013)
open/critical; issue #193 open; product-owner nine-process deferment recorded on
PR #189 (comment `5055372944`); clean tree; no merge/rebase/cherry-pick in progress.
**Every PR-#189-unmerged and `dd0af5d`-tip statement in this subsection is a
historical snapshot, superseded by §2.1.**

## 3. What was produced

The 13 outputs under `docs/07-implementation-plan/wave-5-u1-gate-a/**` (see
`README.md`), plus updates to `research-handoff.md`, `mvp-program-state.md`,
`architecture-review-log.md` and `technical-debt-register.md`. The **backend
UI-contract inventory** was originally built by directly reading the then-frozen
Wave 4 source at head `2d9cff0` *(historical)*, and was **re-verified in full
against the current integrated implementation `2583081f` on 2026-07-25**; every
referenced model/field/selection/action/group/record rule is source-verified there,
with the delta enumerated in that document's §0.1.

## 4. Key rulings (control-room comment `5056513213` applied — 2026-07-23 correction)

- **SEC-2:** defined sufficiently → Gate A planning **not blocked**; **D-P0-2
  resolved SEC-2-FIRST (binding)** — U1 implementation was blocked until SEC-2
  merged runtime-green. **That condition is satisfied as of 2026-07-25** (SEC-2
  merged; #196 closed); the binding content of the ruling is unchanged. No parallel four-internal-group path. U1 customer-facing UI
  **visibility** gates on the two SEC-2 roles (Connector User, Connector
  Administrator); the four internal groups remain server-side capability primitives.
- **Branch:** **Option A ACCEPTED (binding)** — wait for PR #189 (and SEC-2) merge;
  do not stack. **Both waiting conditions satisfied as of 2026-07-25**; the exact
  implementation base remains **unbound** until the control room binds it.
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
- **Overall (2026-07-23, historical):** `DOCS CORRECTED — AWAITING FRESH INDEPENDENT
  GATE-A REVIEW`. **Present:** `RE-ANCHORED AND RECONCILED — FRESH INDEPENDENT
  GATE-A REVIEW STILL REQUIRED`.

## 5. Decision status after the correction (control-room comment `5056513213`)

- **P0:** D-P0-1 (branch) **ACCEPTED — precondition now satisfied**; D-P0-2 (SEC-2
  sequencing) **RESOLVED SEC-2-first — condition now satisfied**; **D-P0-4 (SEC-3
  obligation for any new durable U1 model) NEW — open requirement, acceptance
  A23, issue #197 open**; D-P0-3 (load-bearing Proposed product/UX contracts)
  **NOT YET ACCEPTED — the one remaining open P0 decision** (independent acceptance required; the
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

- **Re-anchor learning (2026-07-25):** a docs package that pins itself to an exact
  source SHA ages in a specific, detectable way — every claim stays *true of that
  snapshot* while silently ceasing to describe the repository. The re-anchor found
  exactly one contract-changing drift (`review_reason` 20 → 21) and one whole new
  cross-cutting layer (SEC-3 ownership + quarantine) that no amount of re-reading the
  package could have surfaced; both were found only by re-reading the **code** at the
  new tip. The durable lesson: when a planning package is frozen behind a
  dependency, the unfreezing step must be a **source re-read**, never a document
  re-read, and its output must be an explicit delta table (§0.1) rather than
  in-place edits — otherwise nobody can tell what changed from what was merely
  restated. Second lesson: preserving the historical snapshot *labelled as
  historical* costs almost nothing and keeps the review trail intact, whereas
  silently overwriting `2d9cff0` with `2583081f` would have erased the reason the
  freeze existed.

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

## 7. Final-backend re-anchor & reconciliation (2026-07-25)

Performed under the binding dependency-freeze ruling
[`5058829593`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5058829593),
whose four conditions were: preserve the existing U1 package; wait for the corrected
Wave 4 source; perform **one** bounded backend-contract delta reconciliation; only
then run a fresh independent U1 Gate-A review. Conditions 1–3 are now discharged.
**Condition 4 is not: the fresh independent Gate-A review has not happened, and this
reconciliation session is not it.**

### 7.1 What was done

- **No-rewrite re-anchor.** The current integration tip `2583081f` was merged into
  the existing branch with an ordinary merge commit (first parent `b38e6874`, second
  parent `2583081f`). **No rebase, no force-push, no squash, no branch or PR
  created, no history rewritten.** The old head `b38e6874` is preserved in ancestry.
- **Conflicts** arose in exactly two authorized documentation paths and were resolved
  conservatively with integration as the baseline:
  `docs/01-research/research-handoff.md` (both sides prepended new entries to a
  reverse-chronological log → integration's 2026-07-23 block kept verbatim and first,
  the U1 Gate-A entry retained immediately after it, nothing dropped) and
  `docs/05-qa/technical-debt-register.md` (integration's newer **TD-002** row kept
  verbatim; the U1 package's **TD-003** row retained).
- **One bounded documentation reconciliation commit** followed. The PR's changed-path
  set is still exactly the same **24** `docs/**` paths; **no `addons/**`**,
  production, test, manifest, security, CI, XML, CSV or configuration file is in the
  diff; no path was added or deleted.

### 7.2 Backend-contract delta findings

The full enumerated delta is `u1-backend-ui-contract-inventory.md` **§0.1** (Δ1–Δ10).
Headlines:

- **Δ1 `review_reason` is 21, not 20** — `external_fulfillment_observed` was added by
  the Wave 4 Tier-1 correction (Theme H). The copy deck must map 21.
- **Δ2 SEC-2 merged** exactly as anticipated (Option M-A, additive `implied_ids`, no
  XML-ID rename); both role XML IDs now exist and are recorded in §8.1. Every server
  gate and every ACL row still resolves the four internal capability groups —
  unchanged.
- **Δ3/Δ4/Δ5/Δ6 SEC-3** introduced a stored related `company_id` and a readonly
  `sec3_scope_quarantined` on every U1-visible model, fail-closed global record
  rules, same-store ORM constraints, and one Administrator-gated remediation action
  that is **outside U1 scope**. Recorded in §8.2; new acceptance **A23**.
- **Δ7 the entire §12 status-source & badge matrix is unchanged** — re-verified
  field-by-field at `2583081f`. A2/A3/A6 still have no seam; `display_status_*` is
  still A7 display-only; `delivered_inconsistency` and
  `review_reason='delivered_not_validated'` are still **declared and never written**.
  Unsupported "Delivered" remains suppressed.
- **Δ8/Δ9/Δ10** — every other selection vocabulary, the six sanctioned actions and
  their gates, the admin field-level `groups=`, and the ACL matrix are **unchanged**.

### 7.3 Raised, not fixed

- **OQ-4** — two `ir.rule` XML IDs are declared twice inside
  `shopify_connector_fulfillment`; `[Inference]` the later declaration replaces the
  earlier domain rather than adding a rule. Raised for the control room / the SEC-3
  (#197) workstream. **No security file was touched here.**
- **OQ-5** — the shipped SEC-2 group `name` strings are `User`/`Administrator` under
  the `Shopify Connector` privilege, not the literal "Connector User"/"Connector
  Administrator" role concepts this package uses. A copy-deck decision.
- **Out-of-scope observation (not edited):** the base-branch **TD-002** row, which
  arrived through the authorized merge, still carries "PR #189 is still an open,
  unmerged draft" wording in its status cell. It is a stabilization/Wave-4 tracker
  row, not a U1 assertion, so correcting it here would be unrelated documentation
  modernization outside this bounded reconciliation. Flagged for the tracker owner.

### 7.4 What this reconciliation explicitly does NOT do

No U1 implementation. No independent Gate-A review, acceptance, ready-marking or
merge. No production, test, security, manifest, CI or configuration change. No
rebase or force-push. No issue action — **#196 stays closed; #197 and #199 stay
open**. No Shopify request, mutation or credential read. **No browser/render or
runtime evidence is supplied or claimed** — the premium-UI browser/render gate for
the future U1 implementation PR is untouched and still required, and neither the
browser tour nor a real process-death harness is claimed as proven. Live-Shopify
validation stays deferred until the Wave 5 implementation candidate is complete and
frozen; Gate D, CV-013 (#185), provisioning (#200), external UAT and release
readiness remain open and unclaimed.

## 8. Exact next-session prompt

```text
CLAUDE CODE — WAVE 5 U1 GATE A FRESH INDEPENDENT REVIEW (docs-only gate; post-re-anchor)

Run in a FRESH top-level Claude session (or a fresh subagent), memoryless of the
authoring/correction/reset/reconciliation sessions' reasoning but NOT
repository-blind. Independently review the RE-ANCHORED AND RECONCILED Wave 5 U1
Gate A package on branch claude/wave-5-u1-gate-a (draft PR #194 to
mvp/program-integration), at the exact current head SHA.

This is a DOCUMENTATION/GOVERNANCE-ONLY batch (DEC-040): verify by repository/diff/
path/link/consistency checks and by reading the ACTUAL production source — NO Odoo.sh
runtime campaign is required, and none may be fabricated.

Verify from scratch:
  1. Identity gate holds live: PR #194 open/draft/unmerged; base mvp/program-integration;
     base SHA 2583081f97c94428dfd10325589b1b891eea240b; old head b38e6874 preserved in
     ancestry; the merge commit has exactly two parents in the order (b38e6874,
     2583081f); the reconciliation commit's only parent is that merge commit; no
     rebase or force-push occurred. PR #189 merged (head e12145ce, merge 3a1afa43,
     runtime candidate 25639f17); PR #203 merged at 2583081f (head d282ab03); issue
     #196 CLOSED; issues #197 and #199 OPEN.
  2. The PR diff against integration is EXACTLY the same 24 docs/** paths — no 25th
     path, no deletion, no addons/**, production, test, manifest, security, CI, XML,
     CSV or configuration file.
  3. Every model, field, selection value, method, action, group XML id and record
     rule cited in u1-backend-ui-contract-inventory.md EXISTS at 2583081f — read the
     actual source, do not trust the document. In particular re-derive: review_reason
     = 21 values incl. external_fulfillment_observed; error_class = 19;
     manual_review_subreason = 9; job state = 10; job_type = 10; origin_class = 4;
     reconciled_state = 5; the six sanctioned actions and their exact server gates.
  4. §0.1 (Δ1–Δ10) is accurate and complete: each claimed delta is real, and each
     claimed "unchanged" really is unchanged. A missing delta is a finding.
  5. SEC-2 (§8.1): the two customer-facing role XML IDs, the privilege_id
     assignment, and the implied closure match core/security/shopify_connector_security.xml
     exactly; the four internal groups are unchanged and still the server-side
     primitives; SEC-2 added no ACL row; the customer-facing/internal distinction is
     preserved everywhere and no parallel role model was introduced.
  6. SEC-3 (§8.2) and acceptance A23: the ownership model, record rules, quarantine
     contract and the out-of-U1-scope disposition of action_sec3_release_scope_quarantine
     match the source. #197 is NOT marked complete anywhere.
  7. PERF-0: no baseline measurement is restated anywhere as a guarantee, budget,
     threshold or SLA. #199 is NOT marked complete anywhere.
  8. The canonical status-source & badge matrix (§12) still matches the source at
     2583081f: display_status_* = A7 display-only, never a carrier milestone; A5 only
     from delivered_inconsistency + parsed tracking_snapshot, never from A7, no full
     A5 enum timeline; A2 FulfillmentOrderStatus DEFERRED (no field, no badge); A4 =
     fulfillment_status_*; A1 only via order_binding_id.shopify_fulfillment_status_snapshot;
     A3/A6 outside U1. No layer merged, no phantom badge, no unsupported "Delivered"
     claimed/displayed/offered — in the package, the prototypes, the acceptance
     matrix (A22) or the locked prompt.
  9. The locked implementation prompt is executable-but-not-executed: it carries an
     UNBOUND <U1-IMPLEMENTATION-BASE-SHA> placeholder (2583081f is NOT used as the
     future implementation base), exact allowed/forbidden paths consistent with the
     task breakdown §4, exact roles/gates, precise fields/actions/status layers,
     install + warm-update + security + access + UI + browser/render + regression
     tests, rollback, no live Shopify unless separately authorized, the
     no-unsupported-Delivered prohibition, a definition of done and hard stops.
 10. Stale-reference sweep: no surviving present-tense claim that PR #189 is
     unmerged, that the accepted backend is 2d9cff0, that SEC-2 is unmerged, that
     integration is dd0af5d, that pre-Wave-5 stabilization is pending, that PR #194
     is ready for review, that #197 or #199 is closed, or that live-Shopify evidence
     is complete. Historical statements are acceptable ONLY where unmistakably
     labelled historical or superseded — check that the labels are honest.
 11. Markdown links and local relative references resolve; heading/anchor
     consistency; no conflict marker; no secret/credential/executable added; the
     AR-log has no duplicate AR number.
 12. Proposed product/UX documents remain Proposed (not silently accepted); browser/
     render evidence is still REQUIRED before U1 merge and is NOT claimed by this
     docs-only batch; the deferred live-Shopify sequencing is intact.
Post the verbatim review at the exact reviewed SHA. Do not accept/ready-mark/merge
if you are also the author. Recommend ACCEPT or REVISE (one consolidated correction).
```

### 8.1 Historical next-session prompt (2026-07-23 — superseded)

*Superseded by §8 above; retained so the review history is not erased.* It targeted
the pre-re-anchor head and asserted an identity gate of "integration tip dd0af5d…;
PR #189 head 2d9cff0 open/draft/unmerged", verified the contract against `2d9cff0`,
and required the error_class count to read 19 and the status-layer reset to be
complete. Those checks were correct for 2026-07-23 and are now replaced.

## 9. Stop

This session stops here. **No implementation occurred; no Shopify operation
occurred; no browser/render or runtime evidence was produced or claimed.** Await
the **fresh independent Claude Gate-A review** of the re-anchored head, then
control-room acceptance, before any acceptance, ready-marking, or merge. The
implementing/correcting/reset/reconciling sessions may not perform that review,
accept, ready-mark, or merge.

**`RE-ANCHORED AND RECONCILED — FRESH INDEPENDENT GATE-A REVIEW STILL REQUIRED.
PR #194 REMAINS DRAFT, UNACCEPTED AND UNMERGED. U1 IMPLEMENTATION REMAINS
UNAUTHORIZED.`**
