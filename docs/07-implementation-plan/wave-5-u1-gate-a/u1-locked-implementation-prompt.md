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
  2. SEC-2 sequencing is resolved (D-P0-2): either SEC-2 is merged runtime-green,
     OR the control room has explicitly authorized U1 to gate on the four internal
     capability groups (auditor/operator/reviewer/admin) in parallel with SEC-2.
  3. Wave-5 gates G5-1 (premium UX master spec accepted), G5-3 (U1 fidelity
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

ALLOWED FILES (all NEW/edited under addons/shopify_connector_fulfillment/):
  views/shopify_connector_fulfillment_menus.xml
  views/shopify_connector_store_settings_fulfillment_views.xml
  views/shopify_connector_fulfillment_review_views.xml
  views/shopify_connector_fulfillment_binding_views.xml
  views/shopify_connector_job_fulfillment_views.xml
  wizards/__init__.py
  wizards/shopify_connector_fulfillment_mode_switch_wizard.py   (TransientModel;
      display-and-delegate ONLY: reads consequences via bounded ACL-safe searches,
      calls action_start_mode2_switch / action_rollback_to_mode1; NO mode decision,
      NO mutation, NO Shopify call, NO protected/snapshot write)
  wizards/shopify_connector_fulfillment_mode_switch_wizard_views.xml
  security/ir.model.access.csv                (edit: wizard TransientModel row ONLY)
  models/__init__.py                          (edit: import wizards pkg if needed)
  __manifest__.py                             (edit: data + optional test assets;
      add 'web' explicitly ONLY if not resolved transitively via core)
  tests/test_ui_visibility_matrix.py
  tests/test_ui_actions.py
  tests/test_ui_source_guards.py              (AST/source guards: no raw evidence
      field on any template; no business logic in the wizard; no controller/
      webhook/OAuth; no Shopify call)
  tests/test_ui_tours.py
  static/tests/**                             (ONLY if a tour bundle is needed)
  docs/06-prompts/ui-u1-copy-deck.md          (code->label map incl. contract §10)
  docs/05-qa/ui-u1-validation-results.md      (RUN evidence + a11y + PB + WALK)
  docs/05-qa/architecture-review-log.md       (append one AR row)
  docs/01-research/research-handoff.md        (top entry)
  docs/07-implementation-plan/mvp-program-state.md (Wave 5/U1 row)

FORBIDDEN FILES / ACTIONS:
  - ANY models/** business file except the new wizard package.
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
  - Every action button gated by the SAME group that its server method enforces
    (UI/ACL agreement; a hidden button is NEVER the security control). Non-admin
    reaching an admin action → server AccessError with zero side effects.
  - NEVER render remote_mutation_intent / preconditions_snapshot / *_fingerprint /
    shopify_idempotency_key / remote_evidence_refs / mode_switch_nonce / tokens.
    Parse JSON snapshots; never dump raw. No raw traceback/payload/credential.
  - Mode display + change on the Store form; review workspace + lineage as standard
    Odoo list/form/search views; consequences via the TransientModel wizard.
  - Five states per surface; bounded/paginated lists; word+icon never colour alone;
    role=dialog + aria-modal on the wizard; focus-visible; reduced-motion; RTL via
    CSS logical properties; platform FontAwesome (P9).
  - No live Shopify request or mutation anywhere. Never present live fulfillment
    mutation as proven (CV-013 / #185 open).

EVIDENCE (DEC-040): ship PY tests + genuine Odoo.sh RUN (build id, fresh-install,
fulfillment/U0/sale/inventory regressions) + a driven WALK before independent
review. Execute TOUR/HOOT/SHOT where the environment supports them; otherwise
record DEFERRED BY PRODUCT OWNER — NOT PROVEN (never "passed").

STOP CONDITION: draft PR "UI Phase U1: fulfillment operator experience" targeting
mvp/program-integration; gate closes on draft-open; no U2/U3/export/SEC-2/PERF-1
work. Then STOP and await independent Claude review.
```

---

**Locked-prompt provenance:** the allowed/forbidden lists above are the exact ones
in `u1-implementation-task-breakdown.md` §4; every referenced action/field exists at
Wave 4 head `2d9cff0` per `u1-backend-ui-contract-inventory.md`.
