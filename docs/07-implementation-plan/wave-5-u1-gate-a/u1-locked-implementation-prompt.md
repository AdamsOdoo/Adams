# Wave 5 U1 — Locked Implementation Prompt (candidate)

> **Status: Gate A planning artifact — Docs-only. NOT accepted. This prompt is
> NOT usable until control-room acceptance and the explicit prerequisites in its
> DO-NOT-USE gate are met.** Produced 2026-07-23; **revalidated against the current
> integrated implementation `2583081f` on 2026-07-25.** This is a **fresh** U1
> locked prompt for the **fulfillment operator experience** — it replaces the
> `ui-implementation-phases-packet.md` §6 U1 prompt, which is for the core surface
> already delivered by the merged U0 (see `u1-product-scope.md` §0; D-P1-1).
>
> **EXACT BASE IS UNBOUND.** The prompt below carries the placeholder
> **`<U1-IMPLEMENTATION-BASE-SHA>`**. It is bound by the **control room**, once,
> after PR #194 Gate-A acceptance and merge — never by the implementing session and
> never by this document. **`2583081f` is the reconciliation anchor of the docs PR
> #194; it is explicitly NOT the authorized U1 implementation base.** A session that
> starts from an unbound or self-chosen base is out of scope by construction.
>
> **DO NOT EXECUTE THIS PROMPT.** It is published for review, not for use.

---

```text
DO NOT USE UNTIL ALL OF THESE HOLD:
  0. EXACT BASE BOUND. The control room has replaced <U1-IMPLEMENTATION-BASE-SHA>
     with a specific mvp/program-integration commit, in writing, after PR #194 was
     accepted and merged. Verify the fetched tip equals that exact SHA and STOP on
     any drift. Do NOT substitute "the current tip", "the latest integration", or
     2583081f (that is PR #194's docs reconciliation anchor, not an implementation
     base).
  1. [SATISFIED 2026-07-25] PR #189 (Wave 4 fulfillment backend) is MERGED into
     mvp/program-integration — merge commit 3a1afa43f8d07a7dae1799968273fa0ab8049490,
     accepted head e12145ce8bb88c099208f025d3cbb656bf0393ca, runtime-tested
     candidate 25639f17be14b30a52a8453f0813aa0b764de310. Re-verify at the bound base.
  2. [SATISFIED 2026-07-25] SEC-2 is ACCEPTED, implemented, independently reviewed
     and MERGED into mvp/program-integration; issue #196 is CLOSED as completed
     (D-P0-2 resolved SEC-2-FIRST, binding via control-room comment 5056513213).
     There is NO parallel path. U1 customer-facing view/menu/button VISIBILITY is
     gated on the two SEC-2 customer-facing roles, whose EXACT XML IDs now exist and
     are:
         shopify_connector_core.group_shopify_connector_user   (Connector User)
         shopify_connector_core.group_shopify_connector_admin  (Connector Administrator)
     The four internal capability groups (group_shopify_connector_auditor /
     _operator / _reviewer / _admin) remain the SERVER-side authorization primitives
     those two roles resolve to via the additive implied-group closure
     (Administrator -> User -> {Operator, Reviewer} -> Auditor). Use these exact IDs;
     invent none; rename none. NOTE the shipped group `name` strings are "User" and
     "Administrator" within the "Shopify Connector" privilege — match the shipped
     label wherever copy names a group (OQ-5).
  3. NOT SATISFIED. The load-bearing Proposed product/UX contracts (D-P0-3 — see the
     Gate-A prerequisite & status table in the package README §4.3) are independently
     accepted, and Wave-5 gates G5-1 (premium UX master spec accepted), G5-3 (U1
     fidelity baseline), G5-4 (PERF-1 budgets) and G5-7 (SEC-1 intact) are satisfied.
  4. NOT SATISFIED. This Gate A package (docs/07-implementation-plan/wave-5-u1-gate-a/**)
     has been INDEPENDENTLY REVIEWED SINCE THE 2026-07-25 RE-ANCHOR and accepted,
     including the re-based numbering (D-P1-1), module placement (D-P1-2, AR row) and
     the final-backend reconciliation (contract §0.1).
Branch from the exact bound base <U1-IMPLEMENTATION-BASE-SHA>. One large coherent
batch; draft PR; stop. Never self-review, self-accept, ready-mark, or merge.

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
      webhook/OAuth; no Shopify call; no `sec3_scope_quarantined` control and no
      call to `action_sec3_release_scope_quarantine` anywhere in U1)
  tests/test_ui_sec3_scope.py                 (SEC-3 closure per acceptance A23:
      proves U1 adds NO new durable store-scoped model or connector-to-connector
      relation — asserted by the inventory-driven completeness guard, not assumed;
      and proves cross-company + quarantined rows are absent from every U1 read
      shape while the owning company's user sees the same row)
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
    UI-contract inventory (verified at the current integrated implementation
    2583081f; re-verify at the bound base before writing a line). Do NOT use
    superseded product-doc vocabulary (external_service, carrier_event_only,
    over_fulfillment, under_review, auto_matched, rejected) — see contract §10.
  - review_reason has TWENTY-ONE values, including external_fulfillment_observed
    (contract §5.4 / §0.1 Δ1). The copy deck maps all 21; no value may render as an
    unmapped raw string. error_class has 19; manual_review_subreason 9; job state 10;
    job_type 10; origin_class 4; reconciled_state 5.
  - SEC-3 (contract §8.2) — every U1-visible model now carries a stored related
    company_id and a readonly sec3_scope_quarantined flag behind fail-closed global
    record rules. U1: displays company read-only and NEVER as a selector; renders NO
    quarantine control and NEVER calls action_sec3_release_scope_quarantine; labels
    EVERY count/facet non-authoritative (quarantined rows are excluded from every
    interactive read shape, so no U1 count is a complete count); introduces NO new
    durable store-scoped model or connector-to-connector relation — and PROVES that
    via the SEC-3 completeness guard rather than asserting it. Issue #197 is OPEN;
    do NOT mark it complete. Visibility tests assert the EFFECTIVE runtime rule set,
    not the union of declared rules (OQ-4).
  - PERF-0 numbers are BASELINE-ONLY (issue #199 OPEN). Never restate one as a
    performance guarantee, budget, threshold or SLA in copy, docs or acceptance.
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
  - No live Shopify request or mutation anywhere, and no Shopify credential is read.
    Never present live fulfillment mutation as proven (CV-013 / #185 open). ALL
    live-Shopify validation is DEFERRED until the Wave 5 implementation candidate is
    complete and frozen; Gate D, CV-013 #185, provisioning #200, external UAT and
    release readiness are OPEN and UNCLAIMED, and this batch closes none of them.
  - "Delivered" must NOT be claimed, displayed or offered as supported. The
    delivered_inconsistency field and review_reason='delivered_not_validated' exist
    but are NEVER written by any code path at 2583081f: render the case when the
    backend populates it, and NEVER synthesize it from the A7 display_status_* fields.

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

ROLLBACK: this batch is one-revert. The whole U1 surface is additive views/menus +
one wizards/ package + test files inside shopify_connector_fulfillment, with NO
schema change, NO data migration, NO new durable model, and NO change to any
existing model/field/selection/security file — so reverting the single merge commit
restores the exact prior behaviour, and a warm -u of the module removes the U1 views
and menus. See u1-rollback-strategy.md for the exact procedure and its limits.

DEFINITION OF DONE: every acceptance row A1-A23 in u1-acceptance-and-test-matrix.md
proven with its stated evidence class; browser/render evidence PRESENT (never
auto-deferred; a class may be recorded DEFERRED — NOT PROVEN only after a concrete
execution attempt, exact environment-limitation evidence and a separate control-room
ruling, and NEVER as "passed"); handoff + learning loop updated per CLAUDE.md §12;
no forbidden path touched; independent Claude review posts a verbatim report at the
exact SHA; a SEPARATE closure session ready-marks/merges.

HARD STOPS — halt and report rather than proceed: the bound base SHA does not match
the fetched tip; any allowed-file list conflicts with what the work needs; any
sanctioned action or field named in the contract inventory is absent at the bound
base; a badge would need a backing field that does not exist; SEC-3 would require a
new durable store-scoped model; any Shopify request, mutation or credential read
would be needed; or browser/render evidence cannot be produced at all.

STOP CONDITION: draft PR "UI Phase U1: fulfillment operator experience" targeting
mvp/program-integration; gate closes on draft-open; no U2/U3/export/SEC-2/PERF-1
work. Then STOP and await independent Claude review.
```

---

**Locked-prompt provenance:** the allowed/forbidden lists above are the exact ones
in `u1-implementation-task-breakdown.md` §4; every referenced action/field/selection
and both role XML IDs were re-verified at the current integrated implementation
`2583081f97c94428dfd10325589b1b891eea240b` on 2026-07-25 per
`u1-backend-ui-contract-inventory.md` §0/§0.1. *(Historical: the original provenance
line cited Wave 4 head `2d9cff0`; that snapshot is superseded.)* The prompt's exact
implementation base remains **unbound** — see the `<U1-IMPLEMENTATION-BASE-SHA>`
placeholder and DO-NOT-USE gate item 0.
