# Task 010 — Validation Results (Product Import / Variant Binding)

## Summary

**Implementation session complete, PR opened as DRAFT — not accepted,
not merged.** This document is the closure-level validation-evidence
record for Task 010's own scope, mirroring the format of
[`task-006c-sync-engine-skeleton-validation-results.md`](./task-006c-sync-engine-skeleton-validation-results.md).
Unlike Task 006C, **no live Odoo/PostgreSQL runtime was reachable in
this session** (no `odoo` package installed, no Odoo.sh access, no
external CI configured for this repository) — every check below is
**static only**, reported honestly per this task's own final prompt
§11/§12 and the Task 001A precedent it restates.

This record itself is **docs-only**: it does not modify any addon/code,
test, manifest, XML/security, migration, or CI file.

## A. Scope

- Base: `Shopify-connector` at commit `431b4bf` (PR #137 merge commit —
  confirmed as this session's actual tip; no drift since the final
  prompt's "Current base placeholder" `c171d8f9…` was written, since
  `c171d8f9…` is itself an ancestor of `431b4bf` reached only by the
  final-prompt/gate-opening-proposal documentation commits themselves).
- New addon: `shopify_connector_product` (manifest depends:
  `['shopify_connector_core', 'product']`).
- **Explicitly out of scope for this PR** (unchanged, not implemented):
  - No product/variant export, update, or write back to Shopify of any
    kind — zero mutation calls anywhere in the diff (§D below).
  - No customer, order, inventory, or fulfillment logic of any kind.
  - No UI, view, menu, action, wizard, webhook, or OAuth file of any
    kind.
  - No edit to any `shopify_connector_core` file — the three seam
    registrations (job_type `selection_add`,
    `_domain_flag_for_job_type()` override, `_get_handlers()` override)
    are declared entirely inside
    `shopify_connector_product_importer.py`, via classic Odoo
    inheritance.

## B. What was implemented

- **`shopify.connector.product.template.binding`** and
  **`shopify.connector.product.variant.binding`** — both extend
  `shopify.connector.binding.mixin`, both declare explicit `_name` and
  `_inherit`, per the accepted MBQ-55 schema (final prompt §7). No
  `_sql_constraints` dict — `models.Constraint(...)` throughout, matching
  the existing core convention.
- **`shopify.connector.product.importer`** (`AbstractModel`) — the
  read-only import/matching service:
  - `import_product_sync(store, shopify_product_gid)` — the only method
    that calls the Shopify API client, always with a `query` operation
    (`PRODUCT_IMPORT_QUERY`), never a `mutation`.
  - `_apply_import(store, payload)` — the pure matching/creation logic
    (no Shopify call), directly unit-testable against a fake/stub
    payload dict, mirroring `shopify_connector_readiness_check.py`'s own
    `_aggregate()`/orchestration split.
  - Match-key priority implemented exactly as final prompt §8 fixes it:
    existing binding → SKU (`default_code`) → barcode → confident
    no-match (create, gated) → ambiguous/blind (never create, routes to
    `blocked_manual_review` via the existing, unmodified
    `JobHandlerError`/`_route_failure()` mechanism).
- **Three extension seams**, all inside
  `shopify_connector_product_importer.py` only:
  1. `job_type` `selection_add` — `product_import_sync`.
  2. `_domain_flag_for_job_type()` override — maps
     `product_import_sync` → `product_domain_enabled`, `super()` for
     every other `job_type`.
  3. `_get_handlers()` override — registers
     `_handle_product_import_sync`.
- **Security** — `ir.model.access.csv` only (no new `security/*.xml`, no
  new group): 8 rows across the two binding models × the four existing
  groups (auditor read-only; operator read+create; reviewer read+write;
  admin read+write+create — no group has `perm_unlink`, matching the
  existing core-wide convention that no ACL grants delete).

## C. In-task decisions made (per final prompt §8/§9's own allowance)

Recorded here, not silently assumed, per this task's own governing
instructions:

1. **`res_model`/`res_id` targeting** (final prompt §9, explicitly left
   open as "pick one of the two already-named candidates and document
   the choice"): a future enqueue-trigger session should target
   `res_model='shopify.connector.product.template.binding'` — the
   binding model, not the underlying `product.template` — because the
   binding is the connector-owned identity concept the job is actually
   about, and it is guaranteed to exist by the time a second job for the
   same Shopify product could be enqueued (the underlying
   `product.template` may not exist yet at enqueue time). **Task 010
   itself does not build any enqueue-trigger call site** — per final
   prompt §9's own explicit deferral, multi-product enumeration/
   pagination is out of this job type's scope; every test in this PR
   constructs `shopify.connector.job` rows directly, exactly mirroring
   how the existing `core_dispatch_selftest` tests do.
2. **Ambiguous/blind matches never create a binding row** (a narrowing
   of MBQ-55 §9's own "the binding row itself is created in
   `status = 'review'`" language, for a documented, structural reason):
   both binding models declare `product_template_id`/
   `product_variant_id` as `required=True` (per the accepted MBQ-55
   schema, final prompt §7 — unchanged, not reopened). An ambiguous or
   blind match has, by definition, no single confirmed Odoo record to
   point a "pending review" binding at; picking one of several candidates
   arbitrarily would be exactly the "automatic guess" DEC-006 forbids.
   The outcome is instead represented entirely at the **job** level
   (`blocked_manual_review` + the matching `manual_review_subreason`),
   which is what every required test in final prompt §10 actually
   asserts — no binding row, no product/variant record, is ever created
   for these two cases. This does not reopen or contradict DEC-006/
   DEC-014 point H; it resolves a genuine schema-vs-blueprint-text tension
   the final prompt itself did not spell out, conservatively, without
   adding a field or weakening a gate.
3. **New `product.product` creation is scoped to the first variant of a
   brand-new template only** (a documented, conservative narrowing, not
   a schema change): Odoo auto-generates exactly one singleton variant
   when `product.template.create()` is called with no attribute lines;
   the importer binds that Odoo-generated variant to the payload's first
   variant. Any additional variant in the same payload, or any variant
   that would need a fresh `product.product` under an *already-existing*
   template, routes to `blocked_manual_review` /`duplicate_risk` instead
   of attempting to synthesize Odoo variant-attribute structure from
   Shopify option data — no accepted document in this project specifies
   that mapping (MBQ-55 §7.2.F explicitly defers "richer" variant
   modeling). **This means a genuinely new, multi-variant Shopify
   product will have its first variant bound automatically and every
   other variant routed to manual review, not silently dropped and not
   automatically created.** Every required §10 test passes with
   single-variant fixtures; this narrowing does not affect any of them.
4. **GraphQL query field list** (`PRODUCT_IMPORT_QUERY`) — not fixed by
   any accepted document (`task-010-product-import-proposed.md` itself
   states this is "Open"; the final prompt does not fix it either) and
   **not verified against a live Shopify endpoint this session** (VAL-B2
   remains explicitly out of Task 010's scope). Shaped conservatively
   after the Product/ProductVariant fields already cited elsewhere in
   this project's accepted architecture docs. Confirmed, at the source
   level, to be a `query` operation, never a `mutation` (§D below).

## D. Static validation

No `odoo` package is installed in this environment and no external CI/
Odoo.sh is reachable from this session — every check below is static:

- `python3 -m py_compile` — clean on every new Python file.
- `python3 -m pyflakes` — clean (no unused imports, no undefined names)
  on all seven substantive new Python files (three models, four tests);
  the only "unused import" findings are the four `__init__.py`
  aggregator files, which is the expected Odoo module-registration
  pattern (identical to every existing `__init__.py` in
  `shopify_connector_core`).
- **Zero Shopify mutation call anywhere in the diff** — confirmed by
  inspection: exactly one GraphQL operation string exists in the entire
  new addon (`PRODUCT_IMPORT_QUERY`), it starts with `query`, and the
  substring `mutation` does not appear inside it (every other occurrence
  of the word "mutation" in the diff is inside a comment/docstring/test
  assertion explaining its *absence* — verified with a repository-wide
  grep across `addons/shopify_connector_product/`).
- **No bypass/force/skip-gate identifier** anywhere in the importer's
  matching/creation logic (source-level grep, mirrors Part A §I.5's
  no-bypass rule).
- **No customer/order/inventory/fulfillment model name** (`sale.order`,
  `res.partner`, `stock.quant`, `stock.picking`, `stock.move`,
  `stock.location`, `account.move`, `account.payment`,
  `delivery.carrier`) anywhere in the three new production model files
  (source-level grep).
- Manifest/security CSV reviewed by hand against the exact
  `depends`/ACL-row requirements in final prompt §3.
- `git status`/`git diff --stat` confirm **only** the files in final
  prompt §3 changed (plus this document and the mandatory handoff/AR-log
  updates, also in §3) — no file under `shopify_connector_core` touched.

**Not run, honestly stated:**

- No Odoo test runner (`--test-enable --test-tags`) was executed — no
  Odoo/PostgreSQL runtime exists in this environment. All 4 test files,
  ~35 test methods, are written and statically valid but **not
  execution-proven** in this session.
- No live Shopify API call was made or attempted (explicitly out of
  scope, VAL-B2).

## E. What is accepted

Nothing is accepted by this document. This is an honest evidence record
for ChatGPT's own separate review — see the Stop condition below.

## F. What is NOT accepted / still open

Explicitly, none of the following are resolved, proven, or closed by
Task 010 or this PR — restated from the final prompt's own hard
constraints, not weakened:

- **VAL-B2** (no live Shopify Admin API connection ever made) — untouched.
- **MBQ-05** (many-unrelated-customer token-acquisition architecture) —
  untouched.
- **TD-002** (`read_fulfillments` readiness-scope correctness) —
  confirmed still `Open` in `technical-debt-register.md`, unaffected by
  this task.
- The **fulfillment API model** decision — untouched.
- **Lite/Full packaging** — untouched.
- **Multi-server/concurrent-worker safety** (SRR-03/04/09) — this task
  inherits the existing, already-merged Task 006C claim/dispatch
  mechanism unmodified; it neither closes nor claims to close any of
  these.
- **Runtime execution proof for this task's own 4 new test files** — not
  yet obtained (§D above); a future session/runtime must actually run
  them before any "0 failed, 0 error(s)" claim can be made.
- **The three in-task narrowings in §C** (ambiguous/blind create a
  binding row; multi-variant new-product creation) are conservative,
  documented decisions, not yet exercised against real Shopify data or
  reviewed by ChatGPT.

## G. Release/UAT implication

- This PR is a **backend-only, read-import domain slice** — no operator
  can trigger it yet (no enqueue-trigger call site exists; every test
  constructs job rows directly, mirroring `core_dispatch_selftest`).
- It is **not UAT-ready connector functionality** and must not be
  represented as such.
- Task 011/012/013/014, Task 015, any UI, webhook, OAuth, or Lite/Full
  packaging work remain unauthorized by this task, per the gate's own
  closure rule (product-domain-gate-criteria-proposal.md §4; task-010
  gate-opening-proposal.md §9).

## Stop condition

Per final prompt §14: this PR is opened as **DRAFT**. It is not marked
ready for review and not merged. ChatGPT's own separate review is the
next required act — see the mandatory handoff update
([`research-handoff.md`](../01-research/research-handoff.md)) for the
exact next-session prompt.
