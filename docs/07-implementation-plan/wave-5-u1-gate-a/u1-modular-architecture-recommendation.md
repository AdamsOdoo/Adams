# Wave 5 U1 — Modular Architecture Recommendation

> **Status: Gate A planning artifact — Docs-only. NOT accepted. Authorizes no
> implementation.** Produced 2026-07-23. Proposes the smallest safe module/file
> map for the U1 fulfillment operator UI.

## 1. The governing rule (already decided at planning level)

`docs/03-architecture/final-mvp-module-and-dependency-architecture.md` **PD-2**:
*"there is **no separate UI module** — views/menus/actions live in the module
that owns their models … each domain module contributes its own
screens/extensions (… fulfillment: S13 sub-surfaces) by inheriting the shared
surfaces … A separate UI module would invert the DAG (it would need every domain)
— rejected here for that reason."* **PD-7** keeps standard Odoo views as the
default and reserves Owl client actions for exactly dashboard / setup-readiness /
matching / diff-preview — **not** fulfillment.

The U0 precedent confirms the pattern: U0's operator surface lives **inside
`shopify_connector_core`** (the module that owns the shared job/store/dashboard
models), not in a separate UI addon.

## 2. Options evaluated (Gate A prompt §10)

| Option | Description | Verdict |
|---|---|---|
| **A. Entirely inside `shopify_connector_fulfillment`** | All U1 views/actions/menus (+ one confirmation wizard) added to the existing fulfillment module | **RECOMMENDED** |
| B. Partly in core UI extensions | Put some fulfillment screens in core | **Rejected** — puts domain UI in the substrate; violates PD-2's "domain logic never migrates into core"; core must not know fulfillment vocabularies |
| C. Separate `shopify_connector_fulfillment_ui` addon | New addon depending on fulfillment | **Rejected** — PD-2 explicitly rejects a separate UI module (DAG inversion); adds a module boundary + dependency with no packaging/security payoff; over-fragmentation pattern flagged in `rejected-approaches-log.md` |

## 3. Recommendation — **Option A: inside `shopify_connector_fulfillment`**

U1 fulfillment operator UI is added to the **existing** `shopify_connector_fulfillment`
addon, alongside the backend it surfaces. This preserves:

- **Optional module boundaries** — fulfillment is `installable, application:False,
  auto_install:False`; its UI installs/uninstalls **with** it (one unit).
- **Uninstall safety** — no cross-addon UI orphan; the module's existing LC-1
  uninstall normalization already handles its job-type/trigger-origin residue;
  views are removed with the module.
- **No circular dependency** — fulfillment already depends on `core` + `sale` +
  `stock_delivery` + `sale_stock`; adding views needs no new **connector** edge.
  The only manifest additions are Odoo view/menu/security data files and (for the
  confirmation wizard) nothing beyond `web` which arrives transitively via core.
- **No giant UI file** — split by surface (see §5); each view file is one concern.
- **Independent testing** — U1 tests live in the fulfillment `tests/` package and
  run with the module.
- **Future U2/U3 extensibility** — U2/U3 domain workspaces likewise land in their
  owning modules; U1's menu root/parent (contributed by fulfillment under the core
  connector menu root) is the anchor U2/U3 extend.
- **Clean backend/UI separation** — views call only the §6 sanctioned actions of
  `u1-backend-ui-contract-inventory.md`; no business logic in the UI layer.

### 3.1 The mode-switch confirmation surface

U1 needs a "confirm + show consequences" step before `action_start_mode2_switch`.
Two Odoo-native mechanisms:

- a button `confirm=` attribute (static text) — too weak to render *dynamic*
  consequences (blocked/running work, unresolved-external count); **and**
- a small **`TransientModel` wizard** that reads consequences (bounded ACL-safe
  searches) and, on confirm, **delegates to the accepted backend action**
  (`action_start_mode2_switch` / `action_rollback_to_mode1`).

**Recommendation:** a display-and-delegate `TransientModel` wizard (mirrors U0's
already-shipped `job_cancel_wizard` / `mutation_resolution_wizard` pattern). It is
**not** "UI-owned business logic": it performs no mutation, computes no mode-switch
decision, and only reads records + calls the sanctioned action. This wizard is
**not** the forbidden "setup wizard" (that is the U2 11-step connect wizard).

## 4. Proposed manifest deltas (`shopify_connector_fulfillment/__manifest__.py`)

- `depends`: **unchanged** (`shopify_connector_core`, `shopify_connector_sale`,
  `stock_delivery`, `sale_stock`). `web` (needed for backend assets/tours) arrives
  transitively via core (U0 added `web` to core). *Preflight must confirm `web`
  resolves transitively; if not, add `web` explicitly — a base Odoo module, no new
  connector edge.*
- `data`: add the new view/menu/action/security-visibility XML + wizard view.
- `assets`: only if a browser tour/HOOT bundle is added under `static/tests/**`
  (test assets). **No production Owl surface** (PD-7).

## 5. Proposed file map (smallest safe set)

**Allowed (NEW/edited) — all inside `addons/shopify_connector_fulfillment/`:**

| Path | Purpose |
|---|---|
| `views/shopify_connector_fulfillment_menus.xml` | Fulfillment menu items under the core connector root (`menu_shopify_connector_root`) |
| `views/shopify_connector_store_settings_fulfillment_views.xml` | Store-settings form inherit: mode display + mode-change buttons (admin-gated) |
| `views/shopify_connector_fulfillment_review_views.xml` | `inbound.evidence` list/form/search (review workspace) + review-action buttons |
| `views/shopify_connector_fulfillment_binding_views.xml` | `fulfillment.binding` list/form (lineage) + release-review button |
| `views/shopify_connector_job_fulfillment_views.xml` | Job list/search filters for the 10 fulfillment job types (lineage) — inherit core job views |
| `wizards/shopify_connector_fulfillment_mode_switch_wizard.py` + `.xml` | `TransientModel` confirm-consequences-and-delegate wizard |
| `security/ir.model.access.csv` (edit) | ACL row(s) for the wizard TransientModel only |
| `__manifest__.py` (edit) | register the new `data` (+ test `assets`) |
| `tests/test_ui_visibility_matrix.py` | four-group (SEC-2-aware) visibility + button→action wiring tests |
| `tests/test_ui_source_guards.py` | AST/source guards: no `env.cr`, no Shopify call, no protected-field write, no raw-payload template |
| `tests/test_ui_tours.py` + `static/tests/**` | `HttpCase.start_tour` browser tours + (only if any Owl) HOOT — *note browser-evidence deferment, see acceptance matrix* |
| `docs/06-prompts/ui-u1-copy-deck.md` | U1 copy deck (code→label mapping incl. §10 reconciliation) |
| `docs/05-qa/ui-u1-validation-results.md` | U1 validation evidence |

**Forbidden (no-scope-creep):**

- Any change to a fulfillment **model/business** `.py` file (`models/**` except
  the wizard file, which is a new UI-orchestration TransientModel), any
  strategy/scan/mode2/dispatch/reader logic.
- Any file in `shopify_connector_core`, `_sale`, `_product`, `_inventory`,
  `_product_export`, or `adams_base` (fulfillment contributes its screens without
  editing other modules — the "contribute, never fork" rule).
- Any new backend business logic, mutation path, Shopify request, webhook/OAuth/
  controller, cron, or new job/error/selection value.
- Any Owl production surface (PD-7 excludes fulfillment); no external JS/font/CDN.
- Product export, setup wizard, mappings/configuration outside fulfillment
  operator scope, U0 redesign.

## 6. Uninstall behaviour

Uninstalling `shopify_connector_fulfillment` removes all U1 views/menus/wizard
with the module (Odoo drops module `ir.ui.view`/`ir.ui.menu`/`ir.actions.*`
records). The backend's existing LC-1 job-type/trigger-origin uninstall
normalization is unchanged by U1 (U1 adds no job type). No U1 record outlives the
module; business data (pickings, orders) is untouched (`ondelete='restrict'`
links on the models, not the views).

## 7. Open module-boundary question carried to the control room

`fulfillment-operating-modes.md` §8/§12 asks whether **Mode 2 enablement should
hard-require the inventory domain** (location mapping, condition 8) given
fulfillment's structural no-inventory-dependency rule. U1 must **not** create a
new coupling; it should **surface** the existing `location_unmapped` review reason
and the `fulfillment_write_scope`/`fulfillment_api_version`/
`fulfillment_staff_permission` readiness checks, and leave the boundary decision
to the control room (logged in `u1-risks-and-open-questions.md`).
