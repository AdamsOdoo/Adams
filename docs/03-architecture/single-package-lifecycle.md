# Single-package lifecycle: verified facts, derivation, and proof

> Companion to [`DEC-042`](../04-decisions/DEC-042-single-package-lifecycle.md).
> That file records the decision; this file records the evidence it rests on.
> Every claim below is labelled **[Fact]** (cited against the pinned Odoo 19
> source or this repository), **[Inference]** (our reasoning from those
> facts), or **[Open question]**.

## 1. Repository/pin identity this record is based on

- Repository: `AdamsOdoo/Adams`, PR #204, branch `fable/wave-5-completion`.
- Odoo pin verified against `tools/odoo-pin.txt` and the actual `.odoo-src`
  checkout: `30bde9ff758834a4912c5ae55843d3a7dad849f1` — **[Fact]**, verified
  by `git -C .odoo-src rev-parse HEAD` matching the pin file, both before any
  file in this change was touched and again at the final head.

## 2. Verified manifest graph (Section 5)

Read directly from each module's `__manifest__.py` at the starting head
(`4ac4ce2a5144907673fea1b753764823857916aa`), before any change in this PR —
**[Fact]**:

| Module | `depends` (direct) | `application` (before) |
| --- | --- | --- |
| `shopify_connector_core` | `base`, `web` | `True` |
| `shopify_connector_product` | `shopify_connector_core`, `product` | `False` |
| `shopify_connector_product_export` | `shopify_connector_core`, `shopify_connector_product` | `False` |
| `shopify_connector_sale` | `shopify_connector_core`, `shopify_connector_product`, `sale` | `False` |
| `shopify_connector_inventory` | `shopify_connector_core`, `shopify_connector_product`, `stock` | `False` |
| `shopify_connector_fulfillment` | `shopify_connector_core`, `shopify_connector_sale`, `stock_delivery`, `sale_stock` | `False` |

This matches the task prompt's expected direct relationships exactly.
`shopify_connector_core` was `application: True` before this change — i.e. a
second, unintended customer-facing app card alongside whatever the eventual
umbrella would be. Flipped to `False` in this change (Section 7).

### 2.1 Full transitive standard-dependency closure

Computed programmatically (`.odoo-src/_closure.py`, a disposable script, not
shipped) by parsing every reachable manifest's `depends` list, starting from
the six technical modules — **[Fact]**, 29 standard Odoo modules plus the six
connector modules:

```
account, account_payment, analytic, auth_signup, barcodes,
barcodes_gs1_nomenclature, base, base_setup, bus, delivery, digest,
html_editor, http_routing, mail, onboarding, payment, payment_custom,
portal, product, resource, sale, sale_stock, sales_team, stock,
stock_account, stock_delivery, uom, utm, web, web_tour
```

`account` **is** a transitive dependency (via `sale -> account_payment ->
account`) — **[Fact]**, confirmed rather than assumed per the task's own
caution. It is a verified dependency, not an implemented connector feature:
this package implements no invoicing/accounting domain logic of any kind.

### 2.2 Platform foundations vs. removable business apps

- **Platform foundations** (never realistically uninstalled by an
  administrator without breaking the whole instance): `base`, `web`.
  **[Inference]**, not independently re-verified per-module here, but
  consistent with these being the two modules `shopify_connector_core`
  already depended on before any connector domain module existed.
- **Removable business apps** an administrator can normally uninstall through
  ordinary Odoo Apps behaviour: `product`, `sale`, `stock`, `stock_delivery`,
  `account`, and everything transitively required only by one of those
  (`sales_team`, `account_payment`, `stock_account`, `sale_stock`,
  `barcodes_gs1_nomenclature`, `digest`, ...). **[Inference]** from the
  closure above; not independently tested for every single one of the 29 —
  the disposable-database harness (§5 below) directly proves the three
  representative cascades the task requires (`stock`, `product`, and by
  extension anything `product`/`stock`/`sale` pull in).

## 3. The crux fact: `downstream_dependencies()` is transitive and unconditional

Verified directly against `.odoo-src/odoo/addons/base/models/ir_module.py` at
the pinned commit — **[Fact]**:

```python
# ir_module.py:532-555
def downstream_dependencies(self, known_deps=None,
                            exclude_states=('uninstalled', 'uninstallable', 'to remove')):
    """ Return the modules that directly or indirectly depend on the modules
    in `self`, and that satisfy the `exclude_states` filter.
    """
    if not self:
        return self
    ...
    query = """ SELECT DISTINCT m.id
                FROM ir_module_module_dependency d
                JOIN ir_module_module m ON (d.module_id=m.id)
                WHERE
                    d.name IN (SELECT name from ir_module_module where id in %s) AND
                    m.state NOT IN %s AND
                    m.id NOT IN %s """
    ...
    new_deps = self.browse([row[0] for row in self.env.cr.fetchall()])
    missing_mods = new_deps - known_deps
    known_deps |= new_deps
    if missing_mods:
        known_deps |= missing_mods.downstream_dependencies(known_deps, exclude_states)
    return known_deps
```

`ir_module_module_dependency` row semantics, from the model itself
(`ir_module.py` around the dependency model definition): `module_id` = "the
module that depends on it"; `name` = "the dependency name". So the query finds
every module `m` that declares one of `self`'s names in its own `depends`, and
the recursion (`missing_mods.downstream_dependencies(known_deps, ...)`) walks
this **all the way up** the dependency chain — if `A` depends on `B` depends
on `C`, uninstalling `C` finds `B` in round 1 and `A` in round 2 (searching for
who depends on `B`, now that `B` is itself in the removal set).

`button_uninstall` uses this directly and unconditionally — **[Fact]**:

```python
# ir_module.py:669-681
def button_uninstall(self):
    ...
    deps = self.downstream_dependencies()
    (self + deps).write({'state': 'to remove'})
```

There is no per-row "soft dependency" or "does not cascade" marker anywhere in
`ir.module.module.dependency` — its only fields are `name`, `module_id`,
`depend_id` (computed), `state` (computed), `auto_install_required`. None of
those express "depend on this but do not be removed when it is removed."

`module_uninstall()` (the execution step, run for every module whose state
reaches `'to remove'`) physically tears down that module's own data —
**[Fact]**:

```python
# ir_module.py:507-517
def module_uninstall(self):
    """... including the deletion of all database structures created by the
    module: tables, columns, constraints, etc."""
    modules_to_remove = self.mapped('name')
    self.env['ir.model.data']._module_data_uninstall(modules_to_remove)
    self.with_context(prefetch_fields=False).write({'state': 'uninstalled', 'latest_version': False})
    return True
```

**[Inference], the load-bearing conclusion:** "A depends on B" means "A is
force-uninstalled, with full data teardown, whenever B is uninstalled" —
unconditionally, with no opt-out at the ORM level. A package that depends
(directly or through any chain) on a module that could be uninstalled is
itself at risk of exactly this fate. This is why a simple manifest umbrella
cannot satisfy the persistence requirement (DEC-042 Context), and why the
dependency direction in this design is deliberately inverted (six technical
modules depend on the package; the package depends on nothing removable).

## 4. `post_init_hook` orchestration for one-action install

Two supporting facts, both verified against the pinned source:

**(a) `button_immediate_install` cannot run mid-load.** —**[Fact]**:

```python
# ir_module.py:599-609 (_button_immediate_function)
def _button_immediate_function(self, function):
    if not self.env.registry.ready or self.env.registry._init:
        raise UserError(_('The method _button_immediate_install cannot be '
                           'called on init or non loaded registries. '
                           'Please use button_install instead.'))
    if modules.module.current_test:
        raise RuntimeError("Module operations inside tests are not "
                            "transactional and thus forbidden. ...")
```

`post_init_hook` runs while the registry is still loading (`_init` is still
`True`), so `_post_init_install_full_suite` uses the deferred `button_install`
(which only marks rows `to install` and recurses through `depends` via
`_state_update`) — never `button_immediate_install`.

**(b) Odoo's own loader re-scans for newly-marked modules mid-run.** —
**[Fact]**, `odoo/modules/loading.py::load_modules`:

```python
# loading.py:450-468 (STEP 3, comment verbatim)
# loop this step in case extra modules' states are changed to 'to install'/'to update' during loading
while True:
    ...
    env.cr.execute("SELECT name from ir_module_module WHERE state IN %s", [states])
    module_list = [name for (name,) in env.cr.fetchall() if name not in graph]
    if not module_list:
        break
    graph.extend(module_list)
    ...
    load_module_graph(env, graph, update_module=update_module, ...)
    if len(registry.updated_modules) == updated_modules_count:
        break
```

**[Inference]:** marking the six technical modules `to install` from
`shopify_connector`'s own `post_init_hook` is therefore sufficient for the
SAME `-i shopify_connector` invocation to install all six (and, through their
own existing `depends`, every standard Odoo application they need) — no
second manual step, no monkey-patched loader, no unsupported registry
recursion.

## 5. Disposable-database proof (Section 6 A-K, Section 24C)

Manifest inspection alone is not proof. Every invariant below was reproduced
in a real, disposable PostgreSQL database via real Odoo module operations
(never simulated), using `tools/shopify_connector_package_lifecycle_check.sh`
(repeatable; the exact stages and assertions are in that script) plus, for the
initial exploratory pass, ad hoc `odoo-bin`/`odoo-bin shell` sessions. All
seven stages of the script currently **PASS**:

| # | Stage | Proves |
| - | --- | --- |
| 1 | Fresh one-action install (`-i shopify_connector` alone) | All 6 technical modules + every standard Odoo app installed; exactly one `application=True` connector module |
| 2 | Warm adoption of a pre-Wave-5 database (six modules installed under the OLD manifests, then `-u`'d to this change) | `shopify_connector` is adopted as a new dependency with zero data loss on a pre-existing store row |
| 3 | Standard-dependency loss (`stock` uninstalled) | `shopify_connector_inventory`/`shopify_connector_fulfillment` cascade away; `shopify_connector` and `shopify_connector_core` remain `installed`; `assert_healthy()` detects and reports the pause with the correct missing-application names |
| 4 | Restore / explicit resume | Reinstalling `stock` alone does not resume; `action_recheck_dependencies` -> `action_restore_suite` -> `action_confirm_resume` is required, and the state remains `dependency_paused` until the final explicit call |
| 5 | Direct component-uninstall refusal | A bare `button_immediate_uninstall()` on a technical module, the `base.module.uninstall` wizard path, AND a crafted co-selection with a legitimate standard app (`{stock, shopify_connector_core}`) are all refused with an actionable message naming the package |
| 6 | Complete package uninstall | Uninstalling `shopify_connector` cascades, through Odoo's own `downstream_dependencies()`, to remove all six technical modules; `product`/`sale`/`stock`/`account` remain installed |
| 7 | Wider transitive cascade (`product` uninstalled) | Even the worst-case cascade (bringing down `account`, `sale`, `stock`, and effectively all five domain technical modules) leaves the package and core installed |

Evidence artifacts land under `${ARTIFACT_DIR}` (default
`ci-artifacts/lifecycle-check`) each run: `1_fresh_install.log`,
`2a_old_install.log`/`2b_seed_store.log`/`2c_warm_upgrade.log`,
`3_uninstall_stock.log`, `4a_reinstall_stock.log`/`4b_restore_resume.log`,
`5_guard_probes.log`, `6_full_uninstall.log`, `7a_fresh_install.log`/
`7b_uninstall_product.log`.

### 5.1 A genuinely dangerous variant explored and confirmed refused

Section 9 explicitly calls for testing "a crafted RPC intended to make a
component appear to be part of an authorized cascade." Stage 5 tests exactly
this: selecting `{stock, shopify_connector_core}` together (a legitimate
standard-app root alongside a technical module, attempting to piggyback the
technical module's removal on the standard app's) is refused, because the
guard inspects the caller's root selection directly (is a protected technical
module present without the package also being present?) rather than "is some
standard app also present" — the latter would have been fooled by exactly
this trick.

## 6. Why the package's own state write needs an independent side cursor

Discovered empirically, not merely reasoned about: an early version of
`assert_healthy()` wrote the newly-detected `dependency_paused` state through
`self.sudo().write(...)` on the caller's own environment, then raised
`UserError` in the same call. Two distinct real bugs followed from this,
found by two different kinds of evidence:

1. **The Odoo TransactionCase test suite** caught that the write was rolled
   back the instant the exception propagated (`TransactionCase.assertRaises`
   takes a savepoint before its body and rolls it back on the expected
   exception — a faithful simulation of what a real HTTP/RPC request's
   top-level exception handling does to its own transaction). Fixed by moving
   the write to an independent, immediately-committing side cursor
   (`_commit_via_side_cursor`, the same established pattern
   `shopify_connector_api_client.py::_admit_lifecycle` already uses).
2. **The disposable-database harness** then caught a second, more subtle bug
   the TransactionCase suite structurally cannot see (registry test mode
   makes every `registry.cursor()` share the same underlying transaction,
   masking it): under Postgres's REPEATABLE READ isolation (Odoo's default —
   verified via `SHOW transaction_isolation` in a live `odoo-bin shell`
   session), the calling transaction's snapshot is fixed at its own start and
   can **never** observe the side cursor's later commit — a genuinely
   different transaction — for the rest of its own lifetime, no matter how
   thoroughly the ORM cache is invalidated. The very first pause detection
   would durably write `dependency_paused` and then immediately read back
   `healthy` in the same call, never raising. Fixed by tracking the
   `effective_state` in plain Python at the point of detection instead of
   re-reading the record afterward — see `shopify_connector_package.py`'s
   `_apply_detected_state`/`assert_healthy` docstrings for the full
   reasoning.

This is recorded here because it is the kind of subtlety a future maintainer
extending this gate (or writing a similar one elsewhere) needs to know about
up front, not rediscover the hard way.

## 7. Requirement-to-proof matrix (excerpt — see PR body for the full matrix)

| Requirement | Entry point | Test/evidence |
| --- | --- | --- |
| One customer-facing app | `addons/shopify_connector/__manifest__.py` | Harness stage 1; `test_package_lifecycle.py` |
| One-action full-suite install | `_post_init_install_full_suite` | Harness stages 1, 2 |
| Package survives standard-dependency loss | Reverse `depends` direction (DEC-042 §Decision 3) | Harness stages 3, 7 |
| Direct component-uninstall refused | `IrModuleModuleUninstallGuard.button_uninstall` | Harness stage 5; `test_uninstall_guard.py` |
| Full package uninstall removes the suite | Reverse `depends` direction + Odoo's own cascade | Harness stage 6 |
| Global pause blocks admission/dispatch/network/actions | `assert_healthy()` instrumented at 7 seams | `test_package_pause_gates.py` |
| Never auto-resumes | `action_confirm_resume` is the only healing path | `test_package_lifecycle.py` |
| Restore is staged, not atomic | `action_recheck_dependencies`/`action_restore_suite`/`action_confirm_resume` | Harness stage 4 |

## 8. Remaining limitations (honestly disclosed, not silently narrowed)

- **Per-store granular resume selection.** This package-level gate is a
  global circuit breaker layered on top of the existing per-store
  readiness/activation state machine (`shopify_connector_core`, unchanged by
  this work). A store that was disconnected before a pause remains
  disconnected after resume; a store's own existing readiness requirements
  are unaffected either way. What is **not** built is a dedicated,
  wizard-driven "select which stores resume, see each one's readiness
  inline" screen distinct from the existing per-store mechanisms — Section
  13 points 10-14's nuance is satisfied by composition with the existing
  machinery, not by a new UI surface.
- **Automatic version-upgrade reconciliation.** `action_restore_suite`
  reinstalls missing components but does not also force-upgrade
  already-installed ones on every call (to avoid an unconditional
  commit+registry-reload even when nothing needs restoring). Reconciling a
  component whose code moved ahead of its installed version is left to
  Odoo's ordinary Apps "Upgrade" action.
- **The full 29-module standard-dependency closure is not individually
  cascade-tested.** The harness proves the three representative cascades the
  task specifies (`stock`, `product`, and the full package uninstall); it
  does not uninstall each of the other 26 standard modules individually.
