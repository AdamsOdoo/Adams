# Wave 5 U1 — Implementation Task Breakdown

> **Status: Gate A planning artifact — Docs-only. NOT accepted. Authorizes no
> implementation.** Produced 2026-07-23; **reconciled 2026-07-25** against the final
> integrated backend at `2583081f`. Decomposes the future U1 code work into
> one coherent, independently-revertable batch (DEC-040 large-batch cadence), with
> internal steps. **No code is written by this document.**

## 1. Batch shape (DEC-040)

U1 is **one large, coherent, independently-revertable slice** — a full navigable
fulfillment operator surface in one pass, not piecemeal screens. All files live in
`shopify_connector_fulfillment` (per `u1-modular-architecture-recommendation.md`).
Tier-3 polish is fixed inline. One draft PR; one independent review; one
consolidated correction max.

## 2. Internal steps (single batch)

| Step | Work | Backend surface consumed |
|---|---|---|
| S1 | **Menu + actions** — `Fulfillment` branch under core root; 3 act_windows (review/bindings/jobs) | core `menu_shopify_connector_root`; `inbound.evidence`, `fulfillment.binding`, `job` |
| S2 | **Store form mode section** — mode display (statusbar/chip), switch buttons (admin), Mode-2 readiness surfacing | `fulfillment_operating_mode` + switch-state fields; readiness checks |
| S3 | **Mode-switch confirmation wizard** — `TransientModel` (display-and-delegate) showing current/requested mode, STATIC consequences, the switch-in-progress flag, and bounded, ACL-safe, **non-authoritative informational** counts (never deciding eligibility, blockers, review-required, target mode, or action arguments); on confirm calls `action_start_mode2_switch` / `action_rollback_to_mode1` | wizard → sanctioned actions; bounded, labelled-informational reads of `job`/`inbound.evidence` |
| S4 | **Review workspace** — `inbound.evidence` list/search/form (evidence-left/decision-right); role-gated action buttons | `inbound.evidence` + `action_import_tracking`/`action_acknowledge_external`/`action_validate_proposed`; `fulfillment.binding.action_release_fulfillment_review` |
| S5 | **Binding + lineage views** — `fulfillment.binding` list/form with smart buttons to picking/order/jobs; job list filtered to the 10 fulfillment job types; mutation-attempt safe summary reuse | `fulfillment.binding`, `job`, `mutation.attempt` (read-only) |
| S6 | **Status/failure UX** — badge taxonomy **per the canonical `u1-backend-ui-contract-inventory.md` §12 matrix** (A4=A4, A7=A7 display-only never carrier-milestone, A5 only from `tracking_snapshot`+`delivered_inconsistency`, **no A2 badge** — deferred, one badge per layer never merged), manual-review-as-decision styling, delivered-inconsistency + unknown-status surfacing (acceptance A22) | evidence status/flag fields per §12 |
| S7 | **Copy deck** — `docs/06-prompts/ui-u1-copy-deck.md` mapping every code value → label (incl. contract §10 reconciliations). **All 21 `review_reason` values** (Δ1, incl. `external_fulfillment_observed`), 19 `error_class`, 9 `manual_review_subreason`, 10 job states, 10 job types, 4 origin classes, 5 reconciled states; plus the shipped role labels `User`/`Administrator` under the `Shopify Connector` privilege (OQ-5) | — |
| S8 | **Tests** — two-role UI visibility matrix (Connector User vs Connector Administrator affordances, against the **effective** runtime record-rule set — OQ-4) + internal implied-group closure + negative direct-RPC (server denial through the internal groups, zero side effects, no privilege escalation) + **SEC-3 closure (A23): cross-company and quarantined rows absent from every U1 read shape while the owning company's user sees the same row, and the inventory-driven completeness guard proves U1 adds no new durable store-scoped model or relation** + action wiring; **import-structure tests** (root imports `wizards` once; wizard model registered after install; no circular/duplicate import); XMLG source guards (no raw evidence / no business logic / wizard is display-and-delegate only — no eligibility/blocker/review-required determination, no Job creation, no mutation / no controller); TOUR primary flows; validation-results doc | all sanctioned actions + two-role/internal groups + package `__init__` structure |

## 3. Ordered dependencies

S1→S2/S4/S5 (menus/actions first for load order); S3 depends on S2; S6 threads
through S4/S5; S7/S8 last. **Odoo-19 data load order:** wizard/actions defined
**before** views that reference them (U0 lesson).

## 4. Allowed / forbidden files (exact — carried into the locked prompt)

**Allowed (NEW/edited)** — the view/wizard/security/test files below are under
`addons/shopify_connector_fulfillment/`; the four `docs/…` deliverables at the end
are **repo-root** paths (not under the addon):
`views/shopify_connector_fulfillment_menus.xml`,
`views/shopify_connector_store_settings_fulfillment_views.xml`,
`views/shopify_connector_fulfillment_review_views.xml`,
`views/shopify_connector_fulfillment_binding_views.xml`,
`views/shopify_connector_job_fulfillment_views.xml`,
`__init__.py` (addon ROOT — add `from . import wizards`; keep the existing
`from . import models`; this is the ONLY place the wizards package is registered),
`wizards/__init__.py` (NEW — `from . import shopify_connector_fulfillment_mode_switch_wizard`, once),
`wizards/shopify_connector_fulfillment_mode_switch_wizard.py`,
`wizards/shopify_connector_fulfillment_mode_switch_wizard_views.xml`,
`security/ir.model.access.csv` (wizard TransientModel row only),
`__manifest__.py` (data/assets additions; add `web` explicitly only if not
transitively resolved),
`tests/test_ui_visibility_matrix.py`, `tests/test_ui_actions.py`,
`tests/test_ui_import_structure.py`, `tests/test_ui_source_guards.py`,
`tests/test_ui_sec3_scope.py` (NEW — SEC-3 closure per acceptance **A23**),
`tests/test_ui_tours.py`, `static/tests/**` (only if a tour bundle is needed),
`docs/06-prompts/ui-u1-copy-deck.md`,
`docs/05-qa/ui-u1-validation-results.md`,
plus AR-log append + handoff + program-state top entry.

**Forbidden:** any `models/**` business file (the mode-switch wizard is a NEW
`wizards/**` TransientModel, not a `models/**` file, and `models/__init__.py` must
NOT import the sibling `wizards` package); any file in
`shopify_connector_core`/`_sale`/`_product`/`_inventory`/`_product_export`/
`adams_base`; any new backend business logic, mutation path, Shopify request,
webhook/OAuth/controller, cron, or new job/error/selection value; any Owl
production surface; any external JS/font/CDN; product export; setup wizard;
mappings/config outside fulfillment operator scope; U0 redesign.

## 5. Prerequisites before this batch may start (control-room gated)

0. **NOT SATISFIED — exact base bound.** The control room has replaced the locked
   prompt's `<U1-IMPLEMENTATION-BASE-SHA>` placeholder with a specific
   `mvp/program-integration` commit, after PR #194 was accepted and merged.
   `2583081f` is PR #194's docs reconciliation anchor, **not** an implementation
   base.
1. **SATISFIED 2026-07-25.** PR #189 merged (merge commit `3a1afa43`; accepted head
   `e12145ce`; runtime candidate `25639f17`) — the Wave 4 backend is on the
   integration tip (`u1-branch-dependency-strategy.md`, Option A).
2. **SATISFIED 2026-07-25.** SEC-2 accepted, implemented, independently reviewed and
   **merged**; issue #196 **closed as completed** (D-P0-2 resolved **SEC-2-first**,
   binding via control-room comment 5056513213). There is **no** parallel
   four-internal-group path. U1 customer-facing view/button **visibility** gates on
   the two SEC-2 roles — exact XML IDs
   `shopify_connector_core.group_shopify_connector_user` /
   `...group_shopify_connector_admin` (contract §8.1) — while the four internal
   groups remain the **server-side** capability primitives they resolve to.
2b. **OPEN — not a blocker, a constraint.** Current-backend SEC-3 is merged but
   issue **#197 remains open**: any new durable store-scoped U1 model or
   connector-to-connector relation must join the inventory-driven SEC-3 guard
   (acceptance **A23**, contract §8.2). PERF-0 baseline is merged but issue **#199
   remains open**: PERF-0 numbers stay baseline-only, never guarantees.
3. **NOT SATISFIED.** The load-bearing Proposed product/UX contracts (D-P0-3)
   independently accepted, and Wave-5 gates G5-1 (master spec accepted), G5-3 (U1
   fidelity baseline), G5-4 (PERF-1 budgets) and G5-7 (SEC-1 intact) satisfied; U1
   gate opened by the control room.
4. **NOT SATISFIED.** This Gate-A package independently reviewed **since the
   2026-07-25 re-anchor** and accepted, including the numbering reconciliation
   (D-P1-1) so the fresh U1 locked prompt (not the packet's core-surface prompt) is
   used.

## 6. Estimated review posture

Tier 2 UI with **Tier 1 security/action checks** (matching U0's tier), because U1
wires to hardened mutation-adjacent actions. One exhaustive independent review;
one consolidated correction; runtime mandatory (it is code).
