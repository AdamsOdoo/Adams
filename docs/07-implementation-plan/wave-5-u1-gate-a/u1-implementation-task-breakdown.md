# Wave 5 U1 — Implementation Task Breakdown

> **Status: Gate A planning artifact — Docs-only. NOT accepted. Authorizes no
> implementation.** Produced 2026-07-23. Decomposes the future U1 code work into
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
| S3 | **Mode-switch confirmation wizard** — `TransientModel` (display-and-delegate) computing the consequences preview from bounded reads; calls `action_start_mode2_switch` / `action_rollback_to_mode1` | wizard → sanctioned actions; bounded reads of `job`/`inbound.evidence` |
| S4 | **Review workspace** — `inbound.evidence` list/search/form (evidence-left/decision-right); role-gated action buttons | `inbound.evidence` + `action_import_tracking`/`action_acknowledge_external`/`action_validate_proposed`; `fulfillment.binding.action_release_fulfillment_review` |
| S5 | **Binding + lineage views** — `fulfillment.binding` list/form with smart buttons to picking/order/jobs; job list filtered to the 10 fulfillment job types; mutation-attempt safe summary reuse | `fulfillment.binding`, `job`, `mutation.attempt` (read-only) |
| S6 | **Status/failure UX** — badge taxonomy (Layer A/C), manual-review-as-decision styling, delivered-inconsistency + unknown-status surfacing | evidence status/flag fields |
| S7 | **Copy deck** — `docs/06-prompts/ui-u1-copy-deck.md` mapping every code value → label (incl. contract §10 reconciliations) | — |
| S8 | **Tests** — PY visibility matrix + negative RPC + action wiring; XMLG source guards (no raw evidence / no business logic / no controller); TOUR primary flows; validation-results doc | all sanctioned actions + groups |

## 3. Ordered dependencies

S1→S2/S4/S5 (menus/actions first for load order); S3 depends on S2; S6 threads
through S4/S5; S7/S8 last. **Odoo-19 data load order:** wizard/actions defined
**before** views that reference them (U0 lesson).

## 4. Allowed / forbidden files (exact — carried into the locked prompt)

**Allowed (NEW/edited), all under `addons/shopify_connector_fulfillment/`:**
`views/shopify_connector_fulfillment_menus.xml`,
`views/shopify_connector_store_settings_fulfillment_views.xml`,
`views/shopify_connector_fulfillment_review_views.xml`,
`views/shopify_connector_fulfillment_binding_views.xml`,
`views/shopify_connector_job_fulfillment_views.xml`,
`wizards/__init__.py`,
`wizards/shopify_connector_fulfillment_mode_switch_wizard.py`,
`wizards/shopify_connector_fulfillment_mode_switch_wizard_views.xml`,
`security/ir.model.access.csv` (wizard TransientModel row only),
`__manifest__.py` (data/assets additions; add `web` explicitly only if not
transitively resolved),
`models/__init__.py` (only to import the wizard package if needed),
`tests/test_ui_visibility_matrix.py`, `tests/test_ui_actions.py`,
`tests/test_ui_source_guards.py`, `tests/test_ui_tours.py`,
`static/tests/**` (only if a tour bundle is needed),
`docs/06-prompts/ui-u1-copy-deck.md`,
`docs/05-qa/ui-u1-validation-results.md`,
plus AR-log append + handoff + program-state top entry.

**Forbidden:** any `models/**` business file except the new wizard; any file in
`shopify_connector_core`/`_sale`/`_product`/`_inventory`/`_product_export`/
`adams_base`; any new backend business logic, mutation path, Shopify request,
webhook/OAuth/controller, cron, or new job/error/selection value; any Owl
production surface; any external JS/font/CDN; product export; setup wizard;
mappings/config outside fulfillment operator scope; U0 redesign.

## 5. Prerequisites before this batch may start (control-room gated)

1. PR #189 merged; U1 branches from the new integration tip
   (`u1-branch-dependency-strategy.md`, Option A).
2. SEC-2 status resolved per `u1-sec2-preflight-ruling.md` (D-P0-2) — either SEC-2
   merged (DoR sequence) or explicit authorization to gate on the four internal
   capability groups.
3. Wave-5 gates G5-1 (master spec accepted), G5-3 (U1 fidelity baseline), G5-7
   (SEC-1 intact) satisfied; U1 gate opened by the control room.
4. Numbering reconciliation (D-P1-1) accepted so the fresh U1 locked prompt (not
   the packet's core-surface prompt) is used.

## 6. Estimated review posture

Tier 2 UI with **Tier 1 security/action checks** (matching U0's tier), because U1
wires to hardened mutation-adjacent actions. One exhaustive independent review;
one consolidated correction; runtime mandatory (it is code).
