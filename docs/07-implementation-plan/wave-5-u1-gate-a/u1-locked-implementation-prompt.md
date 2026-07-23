# Wave 5 U1 — Locked Implementation Prompt (candidate)

> **Status: Gate A planning artifact — Docs-only. NOT accepted. This prompt is
> NOT usable until control-room acceptance and the explicit prerequisites in its
> DO-NOT-USE gate are met.** Produced 2026-07-23. This is a **fresh** U1 locked
> prompt for the **fulfillment operator experience** — it replaces the
> `ui-implementation-phases-packet.md` §6 U1 prompt, which is for the core surface
> already delivered by the merged U0 (see `u1-product-scope.md` §0; D-P1-1).

---

```text
DO NOT USE UNTIL ALL OF THESE HOLD:
  1. PR #189 (Wave 4 fulfillment backend) is MERGED into mvp/program-integration,
     and this session branches from the NEW integration tip (STOP on drift).
  2. SEC-2 is ACCEPTED, implemented, independently reviewed, Odoo.sh runtime-green,
     and MERGED into mvp/program-integration (D-P0-2 resolved SEC-2-FIRST, binding
     via control-room comment 5056513213). There is NO parallel path: U1 production
     implementation is NOT authorized before SEC-2 lands. U1 customer-facing
     view/menu/button VISIBILITY is gated on the two SEC-2 customer-facing roles
     (Connector User, Connector Administrator); the four internal capability groups
     (auditor/operator/reviewer/admin) remain the SERVER-side authorization
     primitives those two roles resolve to via SEC-2 implied-group closure. SEC-2
     defines the final two-role group XML IDs — do NOT invent them.
  3. The load-bearing Proposed product/UX contracts (D-P0-3 — see the Gate-A
     prerequisite & status table in the package README) are independently accepted,
     Wave-5 gates G5-1 (premium UX master spec accepted), G5-3 (U1 fidelity
     baseline), G5-7 (SEC-1 intact) are satisfied, and the control room OPENS the
     U1 gate and verifies the current base SHA.
  4. This Gate A package (docs/07-implementation-plan/wave-5-u1-gate-a/**) is
     accepted, including the re-based numbering (D-P1-1) and module placement
     (D-P1-2, AR row).
Branch from the verified current tip. One large coherent batch; draft PR; stop.
Never self-review, self-accept, ready-mark, or merge.

TASK: Implement Wave 5 U1 — the fulfillment operator experience — exactly per
docs/07-implementation-plan/wave-5-u1-gate-a/** (product scope, backend UI-contract
inventory, UX/IA, module recommendation, acceptance & test matrix, task breakdown),
docs/03-architecture/premium-ui-ux-design-system.md (tokens/scales, §12 a11y,
§13/§14 acceptance), the accepted premium UX master spec, and the accepted U0
prototypes (docs/09-ui-prototype/**, fidelity is an acceptance criterion). Reuse
the U0 design token layer, copy principles, and Odoo-19 view idioms VERBATIM.
Wire EVERY button ONLY to the sanctioned Wave 4 actions listed in the backend
UI-contract inventory §6. Introduce NO business logic.

ALLOWED FILES (addon files are under addons/shopify_connector_fulfillment/; the
five docs/... deliverables at the end are repo-root paths, NOT under the addon):
  views/shopify_connector_fulfillment_menus.xml
  views/shopify_connector_store_settings_fulfillment_views.xml
  views/shopify_connector_fulfillment_review_views.xml
  views/shopify_connector_fulfillment_binding_views.xml
  views/shopify_connector_job_fulfillment_views.xml
  __init__.py                                 (addon ROOT package — edit: add
      `from . import wizards`; the existing `from . import models` stays. This is
      the ONLY place the wizards package is registered. `models/__init__.py` must
      NOT import the sibling wizards package.)
  wizards/__init__.py                         (NEW: exactly `from . import
      shopify_connector_fulfillment_mode_switch_wizard` — one import, once)
  wizards/shopify_connector_fulfillment_mode_switch_wizard.py   (TransientModel;
      display-and-delegate ONLY: shows current mode, requested mode, STATIC
      consequences, the switch-in-progress flag, and bounded, ACL-safe,
      non-authoritative informational counts labelled as such; on confirm calls
      action_start_mode2_switch / action_rollback_to_mode1. NO mode decision, NO
      eligibility/blocker/review-required determination, NO prediction of switch
      success, NO target-mode choice, NO action-argument alteration, NO Job
      creation, NO mutation, NO Shopify call, NO protected/snapshot write. See the
      display-and-delegate boundary in UX/IA §6 and the acceptance matrix.)
  wizards/shopify_connector_fulfillment_mode_switch_wizard_views.xml
  security/ir.model.access.csv                (edit: wizard TransientModel row ONLY)
  __manifest__.py                             (edit: data + optional test assets;
      add 'web' explicitly ONLY if not resolved transitively via core)
  tests/test_ui_visibility_matrix.py          (two-role UI visibility + internal
      implied-group closure + negative direct-RPC server denial)
  tests/test_ui_actions.py
  tests/test_ui_import_structure.py           (root imports wizards exactly once;
      wizard model registered after install; no circular/duplicate import)
  tests/test_ui_source_guards.py              (AST/source guards: no raw evidence
      field on any template; wizard is display-and-delegate only — no eligibility/
      blocker/review-required decision, no Job creation, no mutation; no controller/
      webhook/OAuth; no Shopify call)
  tests/test_ui_tours.py
  static/tests/**                             (ONLY if a tour bundle is needed)
  docs/06-prompts/ui-u1-copy-deck.md          (code->label map incl. contract §10)
  docs/05-qa/ui-u1-validation-results.md      (RUN evidence + a11y + PB + WALK)
  docs/05-qa/architecture-review-log.md       (append one AR row)
  docs/01-research/research-handoff.md        (top entry)
  docs/07-implementation-plan/mvp-program-state.md (Wave 5/U1 row)

FORBIDDEN FILES / ACTIONS:
  - ANY models/** business file (the mode-switch wizard is a NEW wizards/**
    TransientModel, not a models/** file; models/__init__.py must NOT import the
    sibling wizards package).
  - ANY file in shopify_connector_core / _sale / _product / _inventory /
    _product_export / adams_base.
  - ANY new backend business logic, mutation path, Shopify request or mutation,
    webhook / OAuth / controller, cron, or new job_type / error_class / selection
    value.
  - ANY Owl production surface (PD-7 excludes fulfillment); external JS/font/CDN.
  - Product export; setup wizard; mappings/config outside fulfillment operator
    scope; U0 redesign; chatter/mail; renaming any legacy group XML id.

HARD CONSTRAINTS:
  - Use ONLY the exact model/field/selection/action values in the backend
    UI-contract inventory (verified at Wave 4 head 2d9cff0). Do NOT use superseded
    product-doc vocabulary (external_service, carrier_event_only, over_fulfillment,
    under_review, auto_matched, rejected) — see contract §10.
  - UI VISIBILITY gates on the two SEC-2 customer-facing roles (Connector User,
    Connector Administrator); the SERVER method enforces its internal capability
    group (auditor/operator/reviewer/admin), which the two roles resolve to via
    implied-group closure. A hidden button is NEVER the security control: a
    non-authorized caller (a Connector User reaching an Administrator-only action,
    or a direct RPC by any role the server denies) gets a server AccessError with
    zero side effects. Tests MUST prove BOTH layers — (a) two-role UI affordance
    visibility (Connector User vs Connector Administrator), and (b) direct-RPC
    server authorization/denial through the internal implied groups, with no
    privilege escalation and no UI/ACL disagreement. SEC-2 defines the final
    two-role group XML IDs; do NOT invent group XML IDs.
  - NEVER render remote_mutation_intent / preconditions_snapshot / *_fingerprint /
    shopify_idempotency_key / remote_evidence_refs / mode_switch_nonce / tokens.
    Parse JSON snapshots; never dump raw. No raw traceback/payload/credential.
  - STATUS-BADGE TAXONOMY is FROZEN to the canonical matrix in the backend
    UI-contract inventory §12 (and UX/IA §8): one badge per layer, layers never
    merged. display_status_raw/_normalized are A7 FulfillmentDisplayStatus
    (display-only) — NEVER render them as an A5 carrier milestone. A5 carrier
    evidence comes ONLY from parsed tracking_snapshot + the delivered_inconsistency
    case — NEVER from the A7 fields, and NEVER as a full A5 enum timeline. There is
    NO A2 FulfillmentOrderStatus badge (deferred — no backing field). A4 success is
    not Odoo stock completion; A7 roll-up is not carrier delivery; only
    stock.picking.state=done proves stock movement. Every badge maps to an exact
    §12 backing field; no badge without backing evidence (acceptance A22).
  - Mode display + change on the Store form; review workspace + lineage as standard
    Odoo list/form/search views; consequences via the TransientModel wizard.
  - Five states per surface; bounded/paginated lists; word+icon never colour alone;
    role=dialog + aria-modal on the wizard; focus-visible; reduced-motion; RTL via
    CSS logical properties; platform FontAwesome (P9).
  - No live Shopify request or mutation anywhere. Never present live fulfillment
    mutation as proven (CV-013 / #185 open).

EVIDENCE (DEC-040; U1 is a PREMIUM UI gate). Before independent review AND before
any U1 merge, ship: PY tests + genuine Odoo.sh RUN (build id; fresh-install and
warm-upgrade; fulfillment/U0/sale/inventory regressions) + import-structure tests
(root package imports `wizards` exactly once; wizard model registered after install;
no circular or duplicate import) + a driven, Odoo-RENDERED WALK-through + the agreed
SCREENSHOT set covering key roles/states + browser-level visibility/action-behaviour
verification + accessibility/render checks + responsive-width checks + RTL checks
where applicable — with NO sensitive evidence or credential leakage. U1 does NOT
automatically inherit U0's browser deferments: browser/render evidence is REQUIRED,
not automatically deferred. HOOT/TOUR may be classified separately based on actual
environment support, but their deferment is NOT pre-authorized here. A product-owner
deferment of any browser class may be requested ONLY after a concrete execution
attempt, exact environment-limitation evidence, and a separate control-room ruling;
never record a deferred class as "passed". Server tests and XML/source guards alone
are NOT sufficient for U1 acceptance.

STOP CONDITION: draft PR "UI Phase U1: fulfillment operator experience" targeting
mvp/program-integration; gate closes on draft-open; no U2/U3/export/SEC-2/PERF-1
work. Then STOP and await independent Claude review.
```

---

**Locked-prompt provenance:** the allowed/forbidden lists above are the exact ones
in `u1-implementation-task-breakdown.md` §4; every referenced action/field exists at
Wave 4 head `2d9cff0` per `u1-backend-ui-contract-inventory.md`.
