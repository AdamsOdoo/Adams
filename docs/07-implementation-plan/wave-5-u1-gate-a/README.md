# Wave 5 U1 — Gate A / Definition of Ready (package index)

> **Status: Gate A planning package — Docs-only. NOT accepted. Authorizes no
> implementation.** Produced 2026-07-23 by the Wave 5 U1 Gate A
> product/UX/architecture session. Independent Claude review / control-room
> acceptance pending. Not self-accepted, not ready-marked, not merged.

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

## 2. Headline rulings

- **SEC-2:** `SEC-2 DEFINED — U1 GATE A NOT BLOCKED BY SEC-2` (not a hard stop).
  SEC-2 is a Wave-5 obligation; U1 implementation sequencing is a control-room
  decision (D-P0-2), not a definitional gap.
- **Branch strategy:** **Option A** — wait for PR #189 merge, then branch U1 from
  the new integration tip. U1 implementation should **not** start before #189
  merges.
- **Module architecture:** **Option A** — U1 UI lives inside
  `shopify_connector_fulfillment` (PD-2 / DEC-016(A)); no separate `_ui` addon.
- **Overall:** `U1 GATE A READY FOR CONTROL-ROOM REVIEW`.

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
