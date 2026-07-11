# Operator UI — Implementation Phases Packet (Prototype Gate U0 + Phases U1–U3)

> **Status: Proposed for ChatGPT review. NOT accepted. No UI is
> implemented or authorized by this packet; the prompts in §6/§7 are
> NOT usable.** Produced 2026-07-10; **revised 2026-07-11** by the
> PR #148 revision session per ChatGPT's control-room review (comment
> `4942966937`, item 4): the ordinary-XML-only posture is replaced by
> the premium architecture in
> `../03-architecture/premium-ui-ux-design-system.md` ("DESIGN
> SYSTEM" below — PD-7 selective-Owl, §9 dashboard hierarchy, §12
> accessibility gates, §13/§14 visual/screenshot acceptance), a
> **visual-design prototype gate (U0)** now precedes U1, browser-level
> testing (Odoo 19 tours + HOOT — captures 2026-07-11 §3) is
> mandatory, and **Task SEC-1 must merge before U1** (buttons wire to
> a hardened backend only). Consumes the accepted design corpus —
> exact paths, both verified present 2026-07-11:
> `../02-product/ui-ux-final-design-spec.md` and
> `../02-product/screen-inventory-and-navigation-map.md` (DEC-012/
> DEC-016/AR-023: S1–S14 surfaces, flows, error-center contract,
> visibility matrix, copy style guide) and ARCH PD-2 (views live in
> owning modules). Closes at proposal level: MBQ-03 (XML-ID scheme),
> MBQ-44 residual (ACL plan); MBQ-22 copy decks remain per-phase
> deliverables.

## 1. Phase grouping (revised)

| Phase | Contents | Owner modules | Prerequisite gates |
| --- | --- | --- | --- |
| **U0 — Visual design / prototype (NEW — blocking gate)** | Static mockups + token/contrast evidence for: §9-hierarchy dashboard; setup/readiness experience; matching center; product diff/preview; one exemplar list+form treatment. Deliverables per DESIGN SYSTEM §13–§15 | none (docs/design artifacts only) | This package accepted; **ChatGPT accepts the prototype — U1 stays locked until then** |
| **U1 — Core operator surface** | Shell/menus; **dashboard per DESIGN SYSTEM §9** (Owl client action — lead band, exception region, secondary chips, activity, optional sparkline); sync center; error center (+ manual-review queue incl. skipped-by-policy filter; buttons → the SEC-1-hardened sanctioned services incl. `action_resolve_manual_review`); logs; settings screens (domain flags, schedule flags, order-policy fields); roles page. Lists/forms/filters/settings are standard Odoo views; the dashboard is the only U1 Owl surface | core (+ tiny sale/product binding list views) | Area 6 **and SEC-1** merged; **U0 prototype accepted**; U1 gate act |
| **U2 — Setup & readiness** | Wizard (11 steps, branch-A token-paste; OAuth step Phase 2+ placeholder per DEC-026) with the U0-accepted setup/readiness Owl presentation; credentials UX; readiness screens | core | U1 merged; VAL-B2 strongly recommended first; U2 gate act |
| **U3 — Domain screens** | Matching centers (S6/S8 — Owl per U0), order error-center extensions (S9), inventory (S10–S12) & fulfillment (S13) screens, mapping consolidation, export preview/diff (S7 — Owl per U0); ship only where owning modules are installed | each domain module | U1 + the domain's backend merged; per-phase gate acts |

Owl scope is **exhaustively** the PD-7 list (dashboard, setup/
readiness, matching, diff/preview) — everything else Odoo-native;
large tables server-paginated (PB-9/PB-10); **no SPA** (DESIGN
SYSTEM §2.3).

## 2. XML-ID scheme (MBQ-03 closure proposal) + exact U1 IDs

Convention unchanged: `<owning_module>.<type>_shopify_connector_<surface>[_<detail>]`,
types `menu_`, `action_`, `view_..._form/list/kanban/search`, plus
`client_action_` for the PD-7 Owl surfaces. Exact U1 set (core):
root `menu_shopify_connector_root` with children `_dashboard`,
`_sync_center`, `_error_center`, `_catalog` (U3 placeholder parent),
`_configuration`; dashboard `action_shopify_connector_dashboard` →
`client_action_shopify_connector_dashboard` (Owl; replaces the old
`view_..._dashboard_kanban` nine-card plan); sync center
`action_shopify_connector_job_sync_center`,
`view_shopify_connector_job_list/_form/_search` (filters: 7 sources,
10 states, 16 classes, 6 sub-reasons, skipped-by-policy, per-domain
job types — fixed vocabularies, never free-typed); error center
`action_shopify_connector_job_error_center` (9-element entry
contract; retry/cancel/resolve buttons → sanctioned services only);
logs `action_shopify_connector_job_log` + views; store/settings
`action_shopify_connector_store`, `view_shopify_connector_store_form/_list`,
`view_shopify_connector_store_settings_form` (credential widget
masked, no read-back, no encryption wording — accepted rules
restated); roles `action_shopify_connector_roles_info` + form. U3
pattern declared as before (domain-module-owned IDs).

## 3. ACL/visibility plan (MBQ-44 residual closure proposal)

Unchanged from the 2026-07-10 proposal (no new groups; menus/actions
carry `groups=`; auditor+ read-only everywhere; action buttons per
the accepted matrix; no record rules in MVP) — with one addition:
every button wires **only** to the SEC-1 sanctioned methods; the
visibility-matrix tests extend with SEC-1's negative cells (a
UI-visible button whose service call is denied server-side for that
group is a test failure — UI and ACL must agree).

## 4. UX invariants carried into every phase

The accepted invariants stand (lead answer band; fixed vocabularies
with text labels; reason+fix+owner on errors; no raw tokens/stack
traces; enqueue-only quick actions; empty states everywhere; copy
voice rules; Lite/Full menus per installed modules + domain-flag
empty-states) — now **plus, binding:** DESIGN SYSTEM tokens/scales
only (§4–§6); five states per surface (§11); accessibility rules
(§12); performance budgets PB-1..PB-12; the §13 visual checklist at
every phase review. The old "standard Odoo backend views only — no
custom SPA" line is superseded by PD-7 (selective Owl, still no SPA).

## 5. Phase deliverables & tests (revised — browser tests now mandatory)

Each phase ships: views/actions per §2; the phase copy deck (MBQ-22
slice, md file); visibility-matrix + button→service wiring tests;
**browser-level tests via the official Odoo 19 mechanisms** —
`web_tour` tours driven from `odoo.tests.HttpCase.start_tour` for the
primary operator flows (U1: dashboard→error-center→retry round trip;
U2: wizard walk; U3: matching resolve, preview confirm) and **HOOT**
unit tests for every Owl component (captures 2026-07-11 §3 — HOOT is
the 19.0 JS framework; QUnit is not planned anywhere); the DESIGN
SYSTEM §14 screenshot set (five states × required widths, from the
Odoo.sh runtime); the §12 accessibility evidence (keyboard
walkthrough, contrast table, reduced-motion check); PB measurements
per `../03-architecture/performance-budgets.md` §5. Server-only
visibility tests are explicitly **insufficient** for acceptance
(review correction — the prior "no browser automation in MVP"
limitation is withdrawn).

## 6. Locked prompt — Phase U1 (revised; U2/U3 prompts drafted post-U1 by design)

```text
DO NOT USE UNTIL: THIS PACKAGE IS ACCEPTED, THE U0 VISUAL PROTOTYPE
IS EXPLICITLY ACCEPTED BY CHATGPT, AREA 6 AND TASK SEC-1 ARE MERGED
RUNTIME-GREEN, CHATGPT OPENS THE UI-U1 GATE, VERIFIES THE CURRENT
BASE SHA, AND ISSUES THIS PROMPT.

Implement UI Phase U1 (core operator surface) exactly per
docs/07-implementation-plan/ui-implementation-phases-packet.md §1–§5,
docs/03-architecture/premium-ui-ux-design-system.md (tokens, scales,
§9 dashboard hierarchy, §12 accessibility, §13/§14 acceptance), the
accepted design corpus (docs/02-product/ui-ux-final-design-spec.md,
docs/02-product/screen-inventory-and-navigation-map.md), and the
ACCEPTED U0 prototype (fidelity to it is an acceptance criterion).
Branch from the verified current tip (STOP on drift). One session;
draft PR; stop.

ALLOWED FILES: addons/shopify_connector_core/views/*.xml (NEW, per §2
IDs), addons/shopify_connector_core/static/src/** (NEW — the
dashboard Owl client action + SCSS token layer ONLY; no other Owl
surface), addons/shopify_connector_core/__manifest__.py (data +
assets entries), addons/shopify_connector_core/models/
shopify_connector_store_dashboard.py (NEW — read-only aggregate
endpoints: read_group/counts with explicit limits, PB-10),
addons/shopify_connector_core/tests/test_ui_visibility_matrix.py (NEW),
addons/shopify_connector_core/tests/test_ui_tours.py (NEW — HttpCase
start_tour), addons/shopify_connector_core/static/tests/** (NEW —
HOOT unit tests for the dashboard components),
docs/06-prompts/ui-u1-copy-deck.md (NEW), docs/05-qa/ui-u1-validation-results.md
(NEW, incl. §14 screenshots + §12 accessibility evidence + PB-1..8
measurements), AR-log append row, handoff top entry.
FORBIDDEN: business-logic model files (except the aggregate-endpoint
file); any mutation path not a sanctioned SEC-1/Area-6 service; any
Owl surface beyond the dashboard (setup/matching/diff are U2/U3);
wizard; domain screens; webhooks/OAuth; external JS/font/CDN assets;
adams_base.

HARD CONSTRAINTS: dashboard per DESIGN SYSTEM §9 exactly (lead band;
max-3 exception region; quiet chips; activity; the optional sparkline
ONLY if U0 accepted it) — no nine-card grid; tokens/scales only —
no ad-hoc colors/spacing (checklist V-2/V-3); fixed vocabularies as
text labels; retry/cancel/resolve buttons call ONLY the sanctioned
services; credentials masked, no read-back, the word 'encrypt' must
not appear; every list has an empty state; five states per surface;
keyboard + focus + reduced-motion per §12; tours + HOOT green in the
Odoo.sh run (verbatim quote) + full screenshot set. Stop condition:
draft PR "UI Phase U1: core operator surface"; gate closes on
draft-open; no U2/U3/domain-screen work.
```

## 7. Locked prompt — U0 visual-design/prototype session (NEW)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE
AND EXPLICITLY AUTHORIZES THE U0 SESSION (INCLUDING ITS ALLOWED
FILES). THIS SESSION PRODUCES DESIGN ARTIFACTS ONLY — NO ODOO CODE,
NO addons/ CHANGES OF ANY KIND.

You are Fable running the dedicated visual-design/prototype session
for the premium Odoo 19 <-> Shopify connector operator UI. Read
first: docs/03-architecture/premium-ui-ux-design-system.md (binding
for this session), docs/02-product/ui-ux-final-design-spec.md,
docs/02-product/screen-inventory-and-navigation-map.md, and
docs/07-implementation-plan/ui-implementation-phases-packet.md.

PRODUCE, under docs/09-ui-prototype/ (this path is authorized for
this session only, by the ChatGPT act issuing this prompt):
  1. Mockups of: the §9 dashboard (all five states incl. first-run
     empty and degraded/error), setup/readiness (token-paste connect
     step + readiness results), the matching center (candidate
     evidence + decision actions), the product diff/preview, and one
     exemplar Odoo-native list+form treatment showing the token layer
     applied. DEFAULT FORMAT: PNG images + one markdown spec per
     screen (annotated regions, exact tokens used, state inventory).
     Self-contained static HTML/CSS mockups are permitted ONLY if the
     issuing act explicitly says so.
  2. The contrast table: every §6 token pair with computed ratios
     against WCAG 2.2 SC 1.4.3/1.4.11 thresholds; adjust token values
     if any pair fails and record the change.
  3. The completed §13 visual checklist for the mockups.
  4. docs/09-ui-prototype/README.md indexing everything, stating what
     is proposed vs accepted-corpus-inherited, and listing the exact
     decisions ChatGPT must accept (incl. the §9.5 sparkline call).
CONSTRAINTS: light mode; platform font stack; §7 icon catalogue only;
no external assets; no vanity metrics; copy per the accepted voice
rules (draft copy marked as draft — MBQ-22 owns final copy). Update
the handoff and stop. UI-U1 REMAINS BLOCKED until ChatGPT accepts
this prototype in a recorded act.
```
