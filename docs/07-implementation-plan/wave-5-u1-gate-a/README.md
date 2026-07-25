# Wave 5 U1 — Gate A / Definition of Ready (package index)

> **Status: Gate A planning package — Docs-only. NOT accepted. Authorizes no
> implementation.** Produced 2026-07-23 by the Wave 5 U1 Gate A
> product/UX/architecture session; **corrected 2026-07-23** per control-room comment
> [`5056513213`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5056513213)
> (`REVISE — one consolidated docs-only correction`); then **status-layer synthesis
> reset 2026-07-23** per control-room ruling
> [`5058042330`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5058042330)
> (resolving the confirmed material-P2 in independent review
> [`5057796514`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5057796514)
> — see the canonical status-source & badge matrix in
> `u1-backend-ui-contract-inventory.md` §12); then **re-anchored onto the current
> integration tip and reconciled against the final integrated backend on
> 2026-07-25** per the binding dependency-freeze ruling
> [`5058829593`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5058829593).
> **`RE-ANCHORED AND RECONCILED — FRESH INDEPENDENT GATE-A REVIEW STILL REQUIRED`.**
> Not self-accepted, not ready-marked, not merged. **U1 implementation remains
> unauthorized.**

**U1 = the fulfillment operator experience** (the re-based UI phase after the
merged U0 core surface — see `u1-product-scope.md` §0). Built entirely against the
**merged Wave 4 fulfillment backend as it now exists on
`mvp/program-integration@2583081f`**, consumed read-only / via sanctioned actions,
with **no UI-owned mutation or business logic**.

### Present authoritative state (2026-07-25)

| Item | State |
|---|---|
| Wave 4 fulfillment backend (PR #189) | **MERGED** — merge commit `3a1afa43`; accepted head `e12145ce`; runtime-tested candidate `25639f17` |
| SEC-2 customer-facing roles (#196) | **MERGED**; issue #196 **closed as completed** |
| Current-backend SEC-3 (#197) | **MERGED**; issue **#197 remains OPEN** — narrowed to future Wave-5-added surfaces + external multi-user UAT / RC confirmation |
| PERF-0 baseline (#199) | Admission-path + local-ledger baseline **MERGED**; issue **#199 remains OPEN** — Shopify-read reconciliation handlers + release thresholds. Baseline values are **baseline-only, never guarantees** |
| Pre-Wave-5 stabilization (PR #203) | **MERGED** — accepted head `d282ab03`, merge commit `2583081f` (the current integration tip) |
| This PR (#194) | **Re-anchored onto `2583081f` and reconciled**; still **draft, unaccepted, unmerged**; a **fresh independent Gate-A review is still required** |
| U1 implementation | **NOT AUTHORIZED** |
| Live-Shopify validation (Gate D, CV-013 #185, provisioning #200, external UAT, release readiness) | **DEFERRED and UNCLAIMED** until the Wave 5 implementation candidate is complete and frozen |
| Premium-UI browser/render evidence | **STILL REQUIRED** before any future U1 implementation PR can be accepted. This docs-only reconciliation supplies **none** of it |

## 1. Package contents (the 13 required Gate A outputs)

| # (prompt §12) | Output | File |
|---|---|---|
| 1 | U1 resource inventory | this README §3 |
| 2 | U1 product scope | `u1-product-scope.md` |
| 3 | Exact backend UI-contract inventory | `u1-backend-ui-contract-inventory.md` |
| 4 | SEC-2 preflight ruling | `u1-sec2-preflight-ruling.md` |
| 5 | UX / information architecture | `u1-ux-information-architecture.md` |
| 6 | Modular architecture recommendation | `u1-modular-architecture-recommendation.md` |
| 7 | Branch / dependency strategy | `u1-branch-dependency-strategy.md` |
| 8 | Acceptance & test matrix | `u1-acceptance-and-test-matrix.md` |
| 9 | Implementation task breakdown | `u1-implementation-task-breakdown.md` |
| 10 | Rollback strategy | `u1-rollback-strategy.md` |
| 11 | Risks & open questions | `u1-risks-and-open-questions.md` |
| 12 | Locked-candidate implementation prompt | `u1-locked-implementation-prompt.md` |
| 13 | U1 handoff | `u1-gate-a-handoff.md` |

Cross-cutting canonical files updated by this session: `docs/01-research/research-handoff.md`
(top entry), `docs/07-implementation-plan/mvp-program-state.md` (Wave 5/U1 row),
`docs/05-qa/architecture-review-log.md` (AR row for module placement + branch
strategy).

## 2. Headline rulings (control-room comment `5056513213` applied)

- **SEC-2:** `SEC-2 MERGED (#196 CLOSED)` — the SEC-2-first sequencing condition
  (D-P0-2) is **satisfied**. The shipped model is exactly Option M-A (additive
  `implied_ids`, no XML-ID rename): the **new** customer-facing
  `group_shopify_connector_user` and the **existing**
  `group_shopify_connector_admin` carry the `Shopify Connector` privilege; the four
  internal capability groups (`auditor`/`operator`/`reviewer`/`admin`) persist,
  hidden, as the **server-side** authorization primitives those roles resolve to.
  Exact IDs and the implied closure: contract `§8.1`. U1 customer-facing UI
  **visibility** still gates on the two roles, never directly on the internal
  groups; both layers are still tested separately.
- **SEC-3 (new, Δ3):** every U1-visible model is now **store-rooted** with a stored
  related `company_id` and a `sec3_scope_quarantined` flag, behind fail-closed
  global record rules. U1 counts are never authoritative, quarantined rows are
  invisible, and any new durable store-scoped U1 model/relation must join the
  inventory-driven SEC-3 guard (acceptance **A23**). Contract `§8.2`.
- **Branch strategy:** **Option A ACCEPTED (binding)** — its precondition (PR #189
  **and** SEC-2 merged) is now **satisfied**; the future U1 implementation branches
  from the integration tip the control room binds when it opens the U1 gate. No
  stacked branch.
- **Module architecture:** **ACCEPTED** — U1 UI lives inside
  `shopify_connector_fulfillment` (PD-2 / DEC-016(A)); no separate `_ui` addon.
- **Mode-switch wizard:** **ACCEPTED CONDITIONALLY** — a `TransientModel` frozen as
  **display-and-delegate only** (no eligibility/blocker/review-required decision;
  informational counts are bounded, ACL-safe, non-authoritative).
- **Package import:** the addon **root `__init__.py`** imports `wizards` (once);
  `models/__init__.py` must **not** import the sibling wizards package.
- **Browser/render evidence:** **REQUIRED before U1 merge** (premium UI gate); not
  auto-inherited from U0 deferments.
- **Product/UX contracts (D-P0-3):** **NOT YET ACCEPTED** — still-Proposed;
  independent acceptance required before U1 implementation (see the Gate-A
  prerequisite & status table, §4).
- **Status-layer & badge taxonomy (synthesis reset, ruling `5058042330`;
  re-verified at `2583081f` 2026-07-25):** the single **canonical status-source &
  badge matrix** is `u1-backend-ui-contract-inventory.md` **§12** (dependent
  docs/prototypes link to it, never re-derive it). `display_status_*` = **A7**
  (display-only, never a carrier milestone); **A5** carrier milestones only from
  `delivered_inconsistency` + parsed `tracking_snapshot`; **A2
  `FulfillmentOrderStatus` DEFERRED — no backing seam, no badge**; layers never
  merged; acceptance **A22** verifies per-layer correctness. **Unsupported
  "Delivered" is never claimed, displayed or offered.** The final-backend
  re-verification found **no change** to any A-family binding (Δ7).
- **Review-reason vocabulary (Δ1):** the evidence `review_reason` selection is now
  **21 values**, not 20 — `external_fulfillment_observed` was added by the Wave 4
  Tier-1 correction. The U1 copy deck must map 21.
- **Overall:** `RE-ANCHORED AND RECONCILED — FRESH INDEPENDENT GATE-A REVIEW STILL
  REQUIRED`.

## 3. U1 resource inventory (existing U1-related documentation found)

Inventoried before authoring; **reused/cited** rather than duplicated.

### Governance / decisions
- `CLAUDE.md` (§13 MVP program control-room); `docs/04-decisions/DEC-016` (UI/UX
  screen-design blueprint — single-shared-surface rule A), `DEC-031`/`DEC-036`
  (Layer 2 + four-role model + SEC-2 re-key anchor D30/D31), `DEC-038` (Wave 4
  fulfillment backend contract), `DEC-039`/`DEC-040` (Claude builder+reviewer,
  large-batch, UI-priority, evidence rules).
- `docs/07-implementation-plan/mvp-completion-program.md`, `mvp-program-state.md`,
  `wave-5-definition-of-ready.md` (binding sequence SEC-2→PERF-1→U1; gates),
  `wave-4-definition-of-ready.md`, `wave-4-gate-a-handoff.md`.
- `docs/05-qa/mvp-acceptance-matrix.md`, `architecture-review-log.md`,
  `rejected-approaches-log.md` (RA-009/011/012/013/016/022/023),
  `technical-debt-register.md`.

### UI phase & SEC-2 packets
- `docs/07-implementation-plan/ui-implementation-phases-packet.md` (U0/U1/U2/U3
  locked prompts — **numbering pre-dates the U0 merge**; its §6 U1 prompt is for the
  core surface, superseded here — D-P1-1).
- `docs/07-implementation-plan/task-sec2-two-role-and-pii-simplification-packet.md`;
  `task-sec1-security-hardening-packet.md`; `task-014-fulfillment-tracking-implementation-packet.md`.
- `docs/03-architecture/final-mvp-module-and-dependency-architecture.md` (PD-2/PD-7);
  `premium-ui-ux-design-system.md`; `modular-architecture-recommendation.md`.

### Product / UX
- `docs/02-product/fulfillment-operating-modes.md`, `shopify-fulfillment-status-model.md`,
  `connector-roles-and-permissions.md` (two-role/SEC-2), `ux-operator-flow.md`,
  `mvp-user-flows-and-state-models.md`, `screen-inventory-and-navigation-map.md`,
  `premium-ux-master-specification.md`, `ui-u0-copy-deck.md`.

### Prototypes (accepted U0 baseline + Proposed gap-closure fulfillment surfaces)
- `docs/09-ui-prototype/` — accepted U0 five surfaces (dashboard, setup-readiness,
  matching-center, product-diff, odoo-native-exemplar) + **Proposed** fulfillment
  surfaces (`fulfillment/`, `external-fulfillment-review/`, `tracking-timeline/`,
  `order-review/`, `jobs-diagnostics/`, `settings-permissions/`, `stores/`),
  `assets/prototype.css` (shared token layer), `traceability-matrix.md`.

### QA / evidence
- `docs/05-qa/ui-u0-validation-results.md` (U0 patterns + deferments),
  `fulfillment-mode-uat-matrix.md`, `cod-uat-matrix.md`,
  `ui-ux-design-review-checklist.md`.
- `docs/05-qa/task-014-fulfillment-tracking-validation-results.md` — **now PRESENT**
  on the integration tip (arrived with the Wave 4 merge). *(Historical note: this
  entry previously read "ABSENT — Wave 4 not merged"; that statement is superseded.)*
  It records the Wave 4 **backend** runtime campaign; it is **not** operator-surface
  (U1) runtime evidence, which does not exist and must be generated by the future U1
  implementation batch.

### Exact backend source (authoritative)
- `addons/shopify_connector_fulfillment/**` and the consumed core surfaces at the
  **current integrated implementation `2583081f97c94428dfd10325589b1b891eea240b`** —
  the basis of `u1-backend-ui-contract-inventory.md`. *(Historical: the original
  2026-07-23 pass read the earlier PR #189 head `2d9cff0`; that snapshot is
  superseded — the delta is enumerated in the contract inventory §0.1.)*

**No pre-existing canonical "U1 Gate A" file existed**, so this package is new;
cross-cutting canonical files were updated in place rather than duplicated.

## 4. Gate-A prerequisite & status table (control-room comment `5056513213`)

This table separates what is settled from what U1 implementation still needs. **The
U1 implementation gate is `CLOSED` until every prerequisite below is satisfied.**
This control-room comment accepts the **SEC-2-first sequencing decision only**; it
does **not** accept any still-Proposed product/UX document, and the Wave-5 gates
G5-1…G5-9 all remain **unchecked**.

### 4.1 Accepted / merged architecture & backend facts (source-verified)

| Item | Source | Status |
|---|---|---|
| Wave 4 fulfillment backend (models/fields/actions/selections/groups) | Verified at `2583081f` (current integration tip); `u1-backend-ui-contract-inventory.md` §0/§0.1 | **Accepted and MERGED** — merge commit `3a1afa43`, accepted head `e12145ce`, runtime-tested candidate `25639f17`. Now present on the integration tip |
| SEC-2 customer-facing role layer (`group_shopify_connector_user` + `group_shopify_connector_admin`, Option M-A additive closure) | `core/security/shopify_connector_security.xml` at `2583081f`; contract §8.1 | **Implemented, independently accepted, MERGED**; issue #196 **closed as completed** |
| Current-backend SEC-3 store-rooted ownership (stored related `company_id`, `sec3_scope_quarantined`, fail-closed global rules, same-store ORM constraints) | `core/models/shopify_connector_scope_mixin.py` + `*_company_rules.xml` at `2583081f`; contract §8.2 | **MERGED for the current backend**; issue **#197 remains OPEN** for future Wave-5-added surfaces + external multi-user UAT/RC confirmation |
| PERF-0 admission-path / local-ledger baseline | PR #203 evidence | **MERGED — baseline-only values, never performance guarantees**; issue **#199 remains OPEN** for the Shopify-read reconciliation handlers and release thresholds |
| Module placement (inside `shopify_connector_fulfillment`) | PD-2, DEC-016(A), **AR-083** (renumbered from AR-079 on 2026-07-25 — the merge brought a different, already-merged AR-079 onto the branch) | **Accepted** (D-P1-2) |
| Design system (tokens/scales/a11y/screenshot criteria) | `premium-ui-ux-design-system.md` §4–§7/§12–§14 | **Accepted** |
| UI/UX design-review checklist | `ui-ux-design-review-checklist.md` (AR-023) | **Accepted**, but still encodes the **four-role** model — the two-role SEC-2 acceptance must land first so U1 is built two-role |
| Four internal capability groups (server) | `core/security/shopify_connector_security.xml` | **Exist / enforced, unchanged by SEC-2** (`group_shopify_connector_{auditor,operator,reviewer,admin}`; now hidden primitives with `privilege_id = False`). Every Wave 4 server gate and every ACL row still resolves them |

### 4.2 Decisions accepted by control-room comment `5056513213`

| Decision | Disposition |
|---|---|
| D-P0-1 branch | **Option A** — binding; **precondition satisfied 2026-07-25** (PR #189 merged). The future U1 implementation branches from the integration tip the control room binds when it opens the U1 gate |
| D-P0-2 SEC-2 sequencing | **SEC-2-FIRST** — binding; **condition satisfied 2026-07-25** (SEC-2 merged, #196 closed). No parallel four-internal-group path; UI visibility still gates on the two roles, server still enforces the internal groups |
| D-P1-1 numbering | **ACCEPTED**; old packet §6 U1 prompt retired as superseded |
| D-P1-2 module | **ACCEPTED** (inside fulfillment addon) |
| D-P1-3 SEC-2 fulfillment scope | Final UI = two roles; backend retains internal groups; U1 does not rewrite Wave 4 security |
| D-P1-4 inventory boundary | **ACCEPTED** — display only; no new fulfillment→inventory dependency |
| D-P1-5 wizard | **ACCEPTED CONDITIONALLY** — display-and-delegate only |
| D-P1-6 browser evidence | **REQUIRED before merge** |
| D-P2-2 tracking timeline | **ACCEPTED** — native Odoo views |
| D-P2-3 mode-switch history | **ACCEPTED** — no history model in U1 (scalars + Job/JobLog lineage) |
| D-P2-4 dark mode | **OUTSIDE U1** |
| D-P2-1 vocabulary | **Code authoritative**; product docs carry a non-destructive superseded-vocabulary note + pending-edit table (TD-003) |
| D-P2-5 consequences read-model | Display-only in U1; an authoritative dynamic preflight is a **separate backend task** |
| Package import structure | Root `__init__.py` imports `wizards` (once); `models/__init__.py` must **not** import the sibling wizards package |

### 4.3 Proposed product/UX contracts still requiring independent acceptance (load-bearing subset — D-P0-3)

| Document / load-bearing sections | Status | Gate |
|---|---|---|
| `premium-ux-master-specification.md` — §1.2, §2 (IA/nav/screen inventory + two-role nav visibility), §3 (S3 Dashboard, S15/S2 Stores, S4 Sync center, S23 review shell), §4 (11-state contract), §5 (motion/microcopy/density), §7 (U1 packet scope), §8 (PD-UX-1..6) | **Proposed — Not accepted** | **G5-1** |
| `connector-roles-and-permissions.md` — §1 (two-role model), §3 (no-masking), §4 (Option M-A migration incl. §4.2 implied_ids, §4.5 ACL impact), §5 (wave allocation blocker), §6 (proposed-decision block) | **Proposed — Not accepted** | **G5-2** |
| `task-sec2-two-role-and-pii-simplification-packet.md` — §A/§C/§D/§G/§H/§J (technical method TA-C5 Decided 2026-07-17 = method only, no code; wave placement + packet acceptance still pending) | **Proposed — Not accepted** | **G5-2** |
| `fulfillment-operating-modes.md` — §3–§5 (detection/review), §4 (16 conditions), §8/§10 (mode switch) | **Proposed — Not accepted** (superseded-vocabulary annotated) | — |
| `shopify-fulfillment-status-model.md` — §1 (four-layer taxonomy), §2–§5 (label/badge/severity), §7 (unknown), §8 (delivered-inconsistency), §9 (badge vocabulary) | **Proposed — Not accepted** (superseded-vocabulary annotated) | — |
| `fulfillment-mode-uat-matrix.md` — UAT-FM-1.x / 2.0–2.18 / 3.1–3.5 / 4.1 | **Proposed — Not accepted** | wave acceptance criterion 6 |
| `cod-uat-matrix.md` — UAT-COD-01..16 + N1–N5 (role-gate N4/N2/N3; feed S18) | **Proposed — Not accepted** (Wave 6 executable) | — |
| Prototype-fidelity / design-system acceptance set — U0 prototype baseline; tokens/states/a11y/screenshots/tours as the U1 fidelity bar | **Proposed as U1 fidelity bar — Not fixed** | **G5-3** |

### 4.4 Pending Wave-5 gates (all UNCHECKED)

G5-1 (premium UX spec accepted) · G5-2 (two-role + no-masking + SEC-2 packet accepted)
· G5-3 (U1 prototype-fidelity criteria fixed) · G5-4 (PERF-1 budgets) · G5-5 (export
PDs) · G5-6 (Layer 2 in place) · G5-7 (SEC-1 intact) · G5-8 (Mode 2 backend delivered)
· G5-9 (rejected-approaches check). **The SEC-2-first sequence became binding via
comment `5056513213`; every other unchecked G5 gate remains pending — the term
"binding Wave-5 DoR" applies only to that one accepted sequencing decision, not to
the still-Proposed DoR as a whole.**

### 4.5 Deferred release/UAT evidence (preserve `NOT PROVEN`)

| Evidence | Status |
|---|---|
| CV-013 live Shopify inventory mutation (issue #185) | **OPEN / CRITICAL — NOT PROVEN**; U1 must never present live fulfillment mutation as proven |
| Fulfillment dev-store UAT | **NOT PROVEN** — release/UAT blocker |
| Wave 4 nine-process concurrency campaign (PR #189) | **DEFERRED — NOT PROVEN** (not U1's obligation) |
| U1 browser/render evidence | **REQUIRED before U1 merge** — deferment only after a concrete attempt + separate control-room ruling. **This docs-only reconciliation supplies none of it, and does not claim the browser tour or the real process-death harness as proven** |
| Live-Shopify validation sequencing | **DEFERRED** until the Wave 5 implementation candidate is complete and frozen (2026-07-25 product-owner ruling). Gate D, CV-013 #185, provisioning #200, external UAT and release readiness are **open and unclaimed** — the deferral is not a waiver |

### 4.6 U1 implementation gate

**`CLOSED`.** Satisfied as of 2026-07-25: PR #189 **merged**; SEC-2 accepted,
implemented, independently reviewed and **merged** (#196 closed); pre-Wave-5
stabilization **merged** (PR #203). Still outstanding, and each on its own
sufficient to keep the gate closed:

1. **This Gate-A package has not been independently reviewed since the re-anchor** —
   a fresh independent Gate-A review of the reconciled head is required, and this
   reconciliation session is not it.
2. **D-P0-3** — the load-bearing Proposed product/UX contracts (§4.3) are still
   **Proposed, not accepted**.
3. The Wave-5 **G5-1…G5-9** gates remain **unchecked** (§4.4).
4. The control room has **not** opened the U1 gate and has **not** bound the exact
   implementation base SHA. The locked prompt therefore carries an unbound
   `<U1-IMPLEMENTATION-BASE-SHA>` placeholder — `2583081f` is the *reconciliation*
   anchor of this docs PR, **not** a pre-authorized implementation base.

**U1 implementation remains unauthorized.**
