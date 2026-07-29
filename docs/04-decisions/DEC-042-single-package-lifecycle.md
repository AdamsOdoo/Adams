# DEC-042: Single customer-facing Shopify Connector package with dependency-loss pause

- **Status:** Proposed (implemented, awaiting independent Claude review per DEC-040 — this session may not self-accept)
- **Date:** 2026-07-29
- **Deciders:** Proposed by the Wave 5 pre-campaign-onboarding implementation session (fable/wave-5-completion, PR #204); pending independent-review acceptance per DEC-040/DEC-041.
- **Phase:** Implementation (mvp/program-integration)
- **Related:** PR #204; `docs/03-architecture/single-package-lifecycle.md` (full feasibility proof and dependency-graph derivation); `tools/shopify_connector_package_lifecycle_check.sh` (disposable-database evidence)

## Context

Before this change, the connector shipped as six separately-installable technical
addons (`shopify_connector_core`, `_product`, `_product_export`, `_sale`,
`_inventory`, `_fulfillment`), with `shopify_connector_core` marked
`application: True` — i.e. two customer-visible surfaces existed in embryo
(core's own app card, and no single "Shopify Connector" product at all), and a
customer installing the connector had to select all six manually with no
guarantee of completeness, and no defined behavior if a standard Odoo
dependency (Sales, Inventory, ...) was later removed.

**[Fact]**, verified directly against the pinned Odoo 19 source
(`odoo/addons/base/models/ir_module.py` at commit
`30bde9ff758834a4912c5ae55843d3a7dad849f1`):
`ir.module.module.downstream_dependencies()` is a transitive, unconditional
cascade. `button_uninstall(self)` computes
`deps = self.downstream_dependencies()` and marks `(self + deps)` `'to
remove'`; `downstream_dependencies` recursively finds every module that
declares any module in `self` in its own `depends`, with no per-dependency
"soft"/non-cascading marker anywhere in `ir.module.module.dependency`. Any
module whose state flips to `'to remove'` has `module_uninstall()` run against
it (`ir_module.py:507-517`), which drives `ir.model.data._module_data_uninstall`
to physically delete every one of that module's own tracked records, tables and
columns (`odoo/addons/base/models/ir_model.py:2462-2634`).

**[Inference]**, drawn directly from that fact: a package that `depends` on the
six connector technical modules the ordinary way would itself be swept into
that same cascade the moment any technical module lost its own standard Odoo
dependency (e.g. `shopify_connector_inventory` depends on `stock`; if the
package depended on `shopify_connector_inventory`, uninstalling `stock` would
recursively also remove the package). A simple manifest-dependency umbrella
therefore cannot satisfy "the connector survives a standard-dependency loss and
shows a paused state" — the umbrella would not exist to show anything.

## Decision

Ship one customer-facing application, `addons/shopify_connector`, that:

1. Depends on nothing but `base`/`web` (modules that are never realistically
   uninstalled) — so it can never be found by any `downstream_dependencies()`
   walk rooted at a standard business app, and therefore can never be
   cascade-removed by losing one.
2. Is made the sole `application: True` module in the connector family;
   `shopify_connector_core`'s flag flips to `False`.
3. Is depended upon, in the REVERSE direction, by each of the six technical
   modules (each adds `shopify_connector` to its own `depends`, alongside its
   existing dependencies). This is what makes Odoo's own
   `downstream_dependencies()` correctly sweep all six away when the
   *package itself* is deliberately uninstalled (Section 14), entirely through
   Odoo's native mechanism, with no custom uninstall-cascade code required.
4. Achieves "one action installs the complete suite" via a `post_init_hook`
   (`_post_init_install_full_suite`) that marks the six technical modules
   `to install` via the deferred `button_install` (not
   `button_immediate_install`, which the pinned Odoo source will not run
   before the registry is ready — verified against
   `ir_module.py::_button_immediate_function`'s guard). Odoo's own loader
   (`odoo/modules/loading.py::load_modules`, the `STEP 3` loop) re-scans
   `ir_module_module` for any newly-`to install` row not yet in its graph
   after every pass and keeps looping until none remain — so the whole suite,
   and every standard Odoo application the six technical modules need, installs
   within the SAME `-i shopify_connector` action.
5. Owns a persistent `shopify.connector.package` singleton that detects a
   standard-dependency loss (any of the six technical modules no longer
   `installed`) and transitions to a durable `dependency_paused` state — the
   ONLY automatic transition; the reverse (`dependency_paused -> healthy`) is
   reachable only through an explicit, administrator-gated three-stage
   restore/resume workflow (recheck dependencies -> restore suite -> confirm
   resume), never automatically.
6. Refuses a direct root-selection uninstall of any of the six technical
   modules (via an `ir.module.module` override on `button_uninstall`) unless
   the package itself is also part of that same root selection — derived
   solely from the verified identity of the caller's root selection (which
   Odoo's own source proves is never mutated by a legitimate standard-app
   cascade), never from a caller-supplied context flag.

Full derivation, the verified manifest/dependency-closure tables, and the
disposable-database proof of every invariant (A-K) are in
`docs/03-architecture/single-package-lifecycle.md`.

## Consequences

- **Positive:**
  - Exactly one Apps-view application card for the entire connector family,
    satisfying "no connector component is optional/independently managed."
  - A standard-dependency loss (Sales, Inventory, ...) durably pauses the
    connector instead of leaving it partially, silently broken; the pause
    survives dashboard reloads and is only lifted by explicit administrator
    action.
  - A full package uninstall correctly removes the whole technical family
    through Odoo's own native cascade, with no custom uninstall code to
    maintain; standard Odoo applications are never removed merely because the
    connector depended on them.
  - Proven, not merely argued: a standalone disposable-database harness
    (`tools/shopify_connector_package_lifecycle_check.sh`) exercises fresh
    install, warm adoption of a pre-Wave-5 database, standard-dependency loss
    + package survival, restore/resume, direct-uninstall refusal (including a
    crafted co-selection), complete package uninstall, and the wider
    transitive `product` cascade, end to end, with real Odoo module
    operations (never simulated).
- **Negative / trade-offs:**
  - The reverse dependency direction is unusual and must be understood by
    anyone extending the six technical modules; each new technical module
    added to the family must remember to add `shopify_connector` to its own
    `depends` and register itself in `REQUIRED_TECHNICAL_MODULES`.
  - The package-lifecycle gate's state write must go through an independent,
    immediately-committing side cursor (`_commit_via_side_cursor`) rather than
    an ordinary `write()`, because the same call typically raises `UserError`
    right after — a subtlety with a real, verified failure mode (a caller can
    never observe its own side cursor's commit within its own still-open
    REPEATABLE READ transaction; `effective_state` is tracked in Python
    specifically to avoid relying on a stale re-read). Documented at length in
    `shopify_connector_package.py`.
  - Per-store granular resume selection/evidence (a store-by-store "select
    which stores resume" UI, beyond the existing per-store readiness/
    activation machinery this package-level gate layers on top of) is not
    built in this pass; logged as a remaining limitation.
  - Restoring the suite currently only reinstalls missing components; it does
    not also force-upgrade already-installed ones (deliberately, to avoid an
    unconditional commit+reload on every restore call) — reconciling a
    component whose code moved ahead of its installed version is left to
    Odoo's own ordinary Apps "Upgrade" action.

## Alternatives considered

| Alternative | Why not chosen | Logged as rejected? |
| --- | --- | --- |
| Simple manifest umbrella depending on all six technical modules | Provably cascade-removed the moment any technical module lost its own standard dependency (see Context) — defeats the entire persistence requirement | Not previously proposed/logged; recorded here as the disproven starting point |
| A durable, versioned recovery snapshot taken before an authorized cascade (Pattern B in the task's own guidance) | Not needed: the reverse-dependency direction means the package and its own data are never touched by the cascade at all, so there is nothing to snapshot and restore — simpler and strictly safer | N/A — a snapshot pattern remains available if a future domain module's OWN data (not the package's) ever needs it |
| Auto-installing the technical modules via `auto_install` triggers keyed to the package | Only fires if the standard app is ALREADY installed at the moment the package installs; cannot guarantee "every required standard Odoo dependency" is installed on a fresh instance that doesn't yet have Sales/Inventory | Not logged separately — superseded by the `post_init_hook` mechanism, which is unconditional |

## Evidence / references

- Odoo 19 source, pinned commit `30bde9ff758834a4912c5ae55843d3a7dad849f1` (this
  repository's `.odoo-src` checkout, `tools/odoo-pin.txt`) —
  `odoo/addons/base/models/ir_module.py` (`button_install`,
  `button_immediate_install`, `button_uninstall`, `button_immediate_uninstall`,
  `_button_immediate_function`, `downstream_dependencies`, `module_uninstall`),
  `odoo/addons/base/models/ir_model.py` (`_module_data_uninstall`),
  `odoo/modules/loading.py` (`load_modules`, `load_module_graph`,
  `post_init_hook`/`uninstall_hook` dispatch), `odoo/addons/base/wizard/
  base_module_uninstall.py`, `odoo/addons/base/wizard/base_module_upgrade.py`,
  `odoo/addons/base/tests/test_uninstall.py` — accessed 2026-07-29,
  Accessible (local checkout).
- Disposable-database evidence: `tools/shopify_connector_package_lifecycle_check.sh`
  run at this PR's head, all 7 stages passing — see the PR evidence comment for
  the exact run transcript.
