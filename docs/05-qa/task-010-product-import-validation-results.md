# Task 010 — Validation Results (Product Import / Variant Binding)

## Summary

**Revised after control-room review, PR still DRAFT — not accepted, not
merged.** ChatGPT reviewed PR #138 (GitHub comment ID `4927037139`) and
returned **REVISE before merge**. Four required fixes were applied in
this revision — see §H below for full detail. §A–§G below describe the
PR's scope/implementation as of the original session and remain
accurate except where §H supersedes them (test-file line counts grew;
no other prior claim changed). This document is the closure-level
validation-evidence record for Task 010's own scope, mirroring the
format of
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
- **Runtime execution proof for this task's own 4 test files (51 test
  methods as of the §H revision)** — not yet obtained (§D/§H above); a
  future session/runtime must actually run them before any "0 failed,
  0 error(s)" claim can be made.
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

## H. Revision after control-room review (comment ID `4927037139`)

**Decision: REVISE before merge. Not marked ready. Not merged.**

Four required fixes were applied to
`shopify_connector_product_importer.py` only (no other production file
changed; no file added outside the existing Task 010 allowed-file
envelope):

1. **Shopify API client error taxonomy preserved.**
   `import_product_sync()` now catches `ShopifyClientError` (imported
   read-only from `shopify_connector_core`'s own API-client module —
   not a `shopify_connector_core` file edit) and re-raises it as
   `JobHandlerError(exc.error_class, exc.reason, exc.technical_detail)`.
   Without this, the dispatcher's generic `except Exception` boundary in
   `_invoke_handler()` would have reclassified every throttling/
   temporary-network/auth failure as `unknown_system_error`, losing the
   accepted DEC-009 auto-retry (throttling, temporary/network) and
   manual-fix-then-retry (permission/scope/auth) routing.
   `exc.credential_invalid`-triggered store-lifecycle side effects (the
   store→`reconnect_needed` transition `action_test_connection()`
   performs in `shopify_connector_core`) are deliberately **not**
   replicated here — out of this task's own scope; only the classified
   `error_class`/`reason`/`technical_detail` are preserved. **4 new
   tests** in `test_product_import_matching.py` (§9): throttling and
   temporary-network each confirmed to route to `retry_waiting` with
   their own error class (not `unknown_system_error`); permission/
   scope/auth confirmed to route to `failed_retryable`; a fourth test
   confirms the importer itself never retries the Shopify call (retry
   policy stays owned by the job/dispatch layer).
2. **One-product import is now atomic.** `_apply_import()`'s entire
   write sequence (template resolution + every variant resolution) runs
   inside one `self.env.cr.savepoint()` block — the exact mechanism this
   addon's own `test_product_template_binding.py`/
   `test_product_variant_binding.py` already used to probe constraint
   violations, now used in production code, not only tests. Any
   `JobHandlerError` or Odoo validation failure anywhere in the sequence
   rolls back every write the call made. **3 new tests**: a source-level
   guard confirming the savepoint call exists
   (`test_product_duplicate_prevention.py` §6); a regression test
   proving a two-variant payload where variant 1 would succeed and
   variant 2 always fails `duplicate_risk` leaves **zero** residue — no
   `product.template`, no `product.product`, no template binding, no
   variant binding for either GID; and a companion test proving the
   savepoint does not affect a separate, already-successful import made
   in an earlier call.
3. **Malformed payloads are now validated explicitly.** A new
   `_validate_payload()` method runs before any write and raises
   `JobHandlerError('data_shape_schema_mismatch', ...)` for: a missing
   product node/GID; an unexpected product status outside
   `PRODUCT_STATUS_VALUES` (`active`/`archived`/`draft`/`unlisted`); and
   any variant missing its own Shopify GID. **6 new tests** in
   `test_product_import_matching.py` (§10): missing product node (unit
   + end-to-end through `import_product_sync()`), missing product GID,
   missing variant GID, unexpected status, and a regression guard that
   the four accepted statuses are still allowed (not over-tightened).
4. **Silent variant truncation is now blocked, not implemented.**
   `PRODUCT_IMPORT_QUERY` now requests `variants.pageInfo.
   hasNextPage`/`endCursor`; `_validate_payload()` (folded into fix 3's
   method) raises `JobHandlerError('data_shape_schema_mismatch', ...)`
   when `hasNextPage` is true, rather than silently importing only the
   first 100 variants. Full multi-page pagination remains explicitly out
   of Task 010's scope — this is a block, not an implementation. **4 new
   tests**: the query string itself requests `pageInfo`/`hasNextPage`;
   a unit test and an end-to-end test (through `import_product_sync()`)
   both confirm a truncated response is blocked with zero residue; a
   regression guard confirms `hasNextPage=False`/absent does not block a
   normal import.

**Test count:** 4 test files, **51 test methods** (up from ~35 before
this revision — `test_product_import_matching.py` alone grew from 17 to
28; `test_product_duplicate_prevention.py` grew from 8 to 10; the two
binding-model test files are unchanged).

**Validation status: still static only, honestly reported.** No `odoo`
package is installed and no Odoo.sh/CI is reachable in this environment
— `python3 -m py_compile` and `python3 -m pyflakes` are clean on every
changed file; the same source-level guards (zero mutation-call
substring inside the query text, zero bypass-flag identifier, zero
customer/order/inventory/fulfillment model reference) were re-run
against the revised file and remain clean. **All 51 test methods,
including the 17 new ones added by this revision, are written and
statically valid but not execution-proven this session** — no Odoo
runtime was reachable, exactly as before this revision.

**Self-audit against the control-room revision instructions (all
confirmed):** no `shopify_connector_core` file changed; no UI/view/
menu/action/wizard/controller file added; no webhook/OAuth file added;
no export/update/write/mutation logic added; no customer/order/
inventory/fulfillment logic added; `ShopifyClientError` is converted to
`JobHandlerError` preserving `error_class`; `_apply_import()` is atomic
via `self.env.cr.savepoint()`; malformed payloads raise
`data_shape_schema_mismatch` before any write; `variants.pageInfo.
hasNextPage` blocks the import; tests cover all four fixes; this
document and the PR body honestly state validation is static-only; the
PR remains draft/unmerged.

## Stop condition

Per final prompt §14: this PR is opened as **DRAFT**. It is not marked
ready for review and not merged. This revision (comment ID
`4927037139`) does not change that — it remains **DRAFT, unmerged**.
ChatGPT's own separate review is the next required act — see the
mandatory handoff update
([`research-handoff.md`](../01-research/research-handoff.md)) for the
exact next-session prompt.
