# Operator UI — Implementation Phases Packet (Groups 1–15 → Phases U1–U3)

> **Status: Proposed for ChatGPT review. NOT accepted. No UI is
> implemented or authorized by this packet; the U1 prompt in §6 is NOT
> usable.** Produced 2026-07-10 (AR-042 candidate). Consumes the
> accepted design corpus (DEC-012/DEC-016/AR-023: S1–S14 surfaces,
> 24-row inventory, 11-step wizard, 9-card dashboard, error-center
> contract, visibility matrix, copy style guide) and ARCH PD-2 (views
> live in owning modules). Closes at proposal level: MBQ-03 (XML-ID
> scheme + exact U1 IDs), MBQ-44 residual (per-surface ACL plan), and
> regroups the task-map's 15 groups into three implementation phases.
> MBQ-22 (final copy) is planned as a phase deliverable with the
> accepted voice rules — the copy deck itself is written inside each
> UI phase and reviewed by ChatGPT there.

## 1. Phase grouping (task-map Groups → phases)

| Phase | Contents (groups) | Module(s) owning the views | Prerequisite gates |
| --- | --- | --- | --- |
| **U1 — Core operator surface** | Group 1 shell/menus; Group 2 dashboard (9 cards, no chart); Group 8 sync center; Group 9 error center (+ manual-review queue incl. the skipped-by-policy filter from D-012-3); Group 15 logs; Group 6 settings screens (store form + settings incl. domain flags, schedule flags, order policy fields); S14 roles page (informational) | core (all), + tiny sale/product view additions for binding list views | Area 6 merged (buttons call its services); U1 gate act |
| **U2 — Setup & readiness** | Group 3 wizard (11 steps, branch-A token-paste path; OAuth step = Phase 2+ placeholder per DEC-026); Group 4 credentials UX; Group 5 readiness screens | core | U1 merged; VAL-B2 recommended first (honest connect step); U2 gate act |
| **U3 — Domain screens** | Group 10 product matching center (S6); Group 11 customer matching (S8); Group 12 order error-center extensions (S9: inline financial-evidence breakdown + matching links); Groups 13/14 inventory (S10–S12) & fulfillment (S13) screens — ship only where their modules are installed; Group 7 mapping screens consolidation; product-export preview screen (S7) with Task 015 | each domain module | U1 merged + the domain's backend merged; per-phase gate act |

Wizard OAuth step, App Store packaging screens, billing: **Phase 2+**
(DEC-026/RA-003 — untouched).

## 2. XML-ID scheme (MBQ-03 closure proposal) + exact U1 IDs

Convention (extends the accepted AR-019 naming): every UI record ID is
`<owning_module>.<type>_shopify_connector_<surface>[_<detail>]`, types
`menu_`, `action_`, `view_..._form/list/kanban/search`. Exact U1 set
(core):

- Root: `menu_shopify_connector_root` ("Shopify Connector", web_icon
  per copy pass), children in order:
  `menu_shopify_connector_dashboard`, `_sync_center`, `_error_center`,
  `_catalog` (placeholder parent for U3), `_configuration`.
- Dashboard: `action_shopify_connector_dashboard`,
  `view_shopify_connector_dashboard_kanban` (the 9 fixed cards — no
  tenth without a DEC).
- Sync center: `action_shopify_connector_job_sync_center`,
  `view_shopify_connector_job_list`, `_form`, `_search` (filters:
  7 sources, 10 states, 16 classes, 6 sub-reasons, skipped-by-policy,
  per-domain job types — fixed vocabularies, never free-typed).
- Error center: `action_shopify_connector_job_error_center`
  (same model, domain-filtered; 9-element entry contract in the form
  view; retry/cancel buttons → the Area-6 job services; reviewer-gated
  resolution affordances).
- Logs: `action_shopify_connector_job_log`,
  `view_shopify_connector_job_log_list/_form/_search`.
- Store/settings: `action_shopify_connector_store`,
  `view_shopify_connector_store_form/_list`,
  `view_shopify_connector_store_settings_form` (embedded);
  credential widget masked, **no read-back, no encryption wording**
  (accepted rules restated).
- Roles: `action_shopify_connector_roles_info`,
  `view_shopify_connector_roles_info_form` (static informational).
- U3 pattern (declared now, created then):
  `shopify_connector_product.menu_shopify_connector_matching_center`,
  `shopify_connector_sale.action_shopify_connector_customer_matching`,
  `shopify_connector_inventory.action_shopify_connector_location_mapping`,
  `shopify_connector_inventory.action_shopify_connector_first_push`,
  `shopify_connector_fulfillment.view_*` extensions,
  `shopify_connector_product_export.action_shopify_connector_export_preview`.

## 3. ACL/visibility plan (MBQ-44 residual closure proposal)

No new groups (accepted — the four merged groups). Menus/actions carry
`groups=`: everything visible to `group_shopify_connector_auditor`+
read-only; action buttons gated per the accepted matrix (operator:
manual syncs/safe retries; reviewer: confirmation-required
resolutions; admin: settings/credentials/disconnect). Record rules:
none in MVP (single-store-per-record model; per-store isolation is
structural) — re-evaluated at multi-store add-on time. Enforcement
tests per phase: menu/action visibility matrix + button-permission
denials (mirroring the merged ACL-matrix test pattern).

## 4. UX invariants carried into every phase (accepted, restated)

Lead answer band; fixed vocabularies with text labels (never color
alone); reason+fix+owner on every error entry; no raw tokens/stack
traces as primary labels; enqueue-only quick actions; empty states
with first-run guidance for every list (copy pass); "premium
simplicity" checklist at phase review; responsive: standard Odoo
backend views only (list/form/kanban — no custom SPA), which are
responsive by platform; onboarding copy voice rules per the accepted
style guide; Lite/Full: menus appear only when their owning module is
installed (PD-2 — no hidden surfaces), domain screens additionally
respect domain flags (empty-state explains "domain disabled").

## 5. Phase deliverables & tests

Each phase ships: views/menus/actions per §2; the phase copy deck
(MBQ-22 slice) as a reviewable md file; visibility-matrix tests;
button→service wiring tests (server-action level; no browser
automation in MVP — flagged limitation); screenshots in the
validation record from the Odoo.sh runtime. U1 additionally: the
dashboard card queries (count fields — read-only compute on store).

## 6. Locked prompt — Phase U1 only (U2/U3 prompts are drafted post-U1 by design — their exact view inheritance targets depend on U1's merged arch; recorded in the signoff as an intentional two-step)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE UI-U1 GATE, VERIFIES THE CURRENT BASE SHA, AND
ISSUES THIS PROMPT.

Implement UI Phase U1 (core operator surface) exactly per
docs/07-implementation-plan/ui-implementation-phases-packet.md §1–§5
and the accepted design corpus (ui-ux-final-design-spec.md,
screen-inventory-and-navigation-map.md — design-level guidance;
Part D DEC-016 contract). Branch from the verified current tip (STOP
on drift). One session; draft PR; stop.

ALLOWED FILES: addons/shopify_connector_core/views/*.xml (NEW files
per §2 ID list), addons/shopify_connector_core/__manifest__.py (data
entries), addons/shopify_connector_core/models/
shopify_connector_store_dashboard.py (NEW — count computes only),
addons/shopify_connector_core/tests/test_ui_visibility_matrix.py
(NEW), docs/06-prompts/ui-u1-copy-deck.md (NEW — every string, per
the voice rules, for ChatGPT review),
docs/05-qa/ui-u1-validation-results.md (NEW), AR-log append row,
handoff top entry. FORBIDDEN: all business-logic model files (except
the new count-compute file); all domain modules' logic; wizard
(U2); domain screens (U3); webhooks/OAuth; controllers; assets/JS
beyond standard view XML; adams_base.

HARD CONSTRAINTS: nine dashboard cards exactly (no chart, no tenth);
fixed vocabularies as selection filters with text labels; retry/
cancel buttons call ONLY the merged Area-6 job services; credentials
masked, no read-back, the word 'encrypt' must not appear anywhere;
every list has an empty state; groups= per §3, no new groups; Odoo.sh
green + screenshots in the validation record. Stop condition: draft
PR "UI Phase U1: core operator surface"; gate closes on draft-open;
no U2/U3/domain-screen work.
```
