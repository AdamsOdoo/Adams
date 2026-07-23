# Wave 5 U1 — Gate A / Definition of Ready (package index)

> **Status: Gate A planning package — Docs-only. NOT accepted. Authorizes no
> implementation.** Produced 2026-07-23 by the Wave 5 U1 Gate A
> product/UX/architecture session; **corrected 2026-07-23** per control-room comment
> [`5056513213`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5056513213)
> (`REVISE — one consolidated docs-only correction`). **`DOCS CORRECTED — AWAITING
> FRESH INDEPENDENT GATE-A REVIEW`.** Not self-accepted, not ready-marked, not
> merged.

**U1 = the fulfillment operator experience** (the re-based UI phase after the
merged U0 core surface — see `u1-product-scope.md` §0). Built entirely against the
**already-accepted Wave 4 backend** (PR #189 head `2d9cff0`), consumed read-only /
via sanctioned actions, with **no UI-owned mutation or business logic**.

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

- **SEC-2:** `SEC-2 DEFINED — U1 GATE A PLANNING NOT BLOCKED; U1 IMPLEMENTATION
  BLOCKED UNTIL SEC-2 MERGES` — **D-P0-2 resolved SEC-2-FIRST (binding)**. No
  parallel four-internal-group path. U1 customer-facing UI **visibility** gates on
  the two SEC-2 roles (Connector User = new `group_shopify_connector_user`;
  Connector Administrator = existing `group_shopify_connector_admin`); the four
  internal groups remain the **server-side** capability primitives those roles
  resolve to.
- **Branch strategy:** **Option A ACCEPTED (binding)** — wait for PR #189 merge (and
  SEC-2 merge), then branch U1 from the new integration tip. No stacked branch.
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
- **Overall:** `DOCS CORRECTED — AWAITING FRESH INDEPENDENT GATE-A REVIEW`.

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
- **ABSENT:** `docs/05-qa/task-014-fulfillment-tracking-validation-results.md` — no
  runtime operator-surface record exists yet (Wave 4 not merged). *(Note: the Wave
  4 branch carries a task-014 validation file; it is not present on the integration
  tip until PR #189 merges.)*

### Exact backend source (authoritative)
- `addons/shopify_connector_fulfillment/**` and consumed core surfaces at Wave 4
  head `2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a` — the basis of
  `u1-backend-ui-contract-inventory.md`.

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
| Wave 4 fulfillment backend (models/fields/actions/selections/groups) | `2d9cff0` (PR #189 head); `u1-backend-ui-contract-inventory.md` | **Accepted at Wave 4 Gate A / candidate runtime-green**, but **not on the integration tip until PR #189 merges** |
| Module placement (inside `shopify_connector_fulfillment`) | PD-2, DEC-016(A), AR-079 | **Accepted** (D-P1-2) |
| Design system (tokens/scales/a11y/screenshot criteria) | `premium-ui-ux-design-system.md` §4–§7/§12–§14 | **Accepted** |
| UI/UX design-review checklist | `ui-ux-design-review-checklist.md` (AR-023) | **Accepted**, but still encodes the **four-role** model — the two-role SEC-2 acceptance must land first so U1 is built two-role |
| Four internal capability groups (server) | `core/security/shopify_connector_security.xml` | **Exist / enforced** (`group_shopify_connector_{auditor,operator,reviewer,admin}`) |

### 4.2 Decisions accepted by control-room comment `5056513213`

| Decision | Disposition |
|---|---|
| D-P0-1 branch | **Option A** — wait for PR #189 merge; no stacked branch (binding) |
| D-P0-2 SEC-2 sequencing | **SEC-2-FIRST** — binding; **no** parallel four-internal-group path |
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
| U1 browser/render evidence | **REQUIRED before U1 merge** — deferment only after a concrete attempt + separate control-room ruling |

### 4.6 U1 implementation gate

**`CLOSED`** until **all** hold: PR #189 merged; **SEC-2 accepted / implemented /
independently reviewed / Odoo.sh runtime-green / merged** into
`mvp/program-integration`; D-P0-3 load-bearing Proposed contracts independently
accepted; the Wave-5 G5 gates satisfied; and the control room opens the U1 gate on a
verified base SHA.
