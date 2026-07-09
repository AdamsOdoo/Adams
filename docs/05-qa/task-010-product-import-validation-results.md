# Task 010 — Validation Results (Product Import / Variant Binding)

## Summary

**Revised a third time after a second actual Odoo.sh runtime red
build, PR still DRAFT — not accepted, not merged.** ChatGPT reviewed
the first red-build evidence (GitHub comment ID `4927278355`) and
returned **REVISE**; the fix applied for that revision (§I) turned out
to be too broad and itself caused a second red build. ChatGPT reviewed
that second red-build evidence (GitHub comment ID `4927455927`) and
again returned **REVISE**: 2 failures / 0 errors of 53 Task 010 tests;
full database load 2 failed / 0 error(s) of 220 tests; the same
docutils/RST build-log warning as before, unchanged. One required
production-logic fix, plus a further docutils investigation, were
applied in this revision — see §J below for full detail. §A–§I below
describe the PR's scope/implementation as of the prior sessions and
remain accurate except where §J supersedes them (test count grew again;
the singleton-variant shortcut described in §I fix 1 is now correctly
scoped — see §J fix 1). This document is the closure-level
validation-evidence record for Task 010's own scope, mirroring the
format of
[`task-006c-sync-engine-skeleton-validation-results.md`](./task-006c-sync-engine-skeleton-validation-results.md).
Prior to this session, **no live Odoo/PostgreSQL runtime was reachable**
(no `odoo` package installed, no Odoo.sh access, no external CI
configured for this repository) — this session's own environment is
unchanged in that respect (still no local runtime), but the user has now
supplied a second round of real Odoo.sh build/test evidence, which §J
reports honestly, including its limits (evidence provided by the user,
not independently re-run by Claude this session).

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

## I. Odoo.sh red-build revision (comment ID `4927278355`)

**Decision: REVISE. Not merged. Kept draft.**

### I.1 Evidence (user-provided, not independently re-run by Claude)

- Module `shopify_connector_product`: **0 failures, 2 errors of 51
  tests.**
- Full database load: **0 failed, 2 error(s) of 218 tests.**
- Build-log docutils/RST warning:
  `<string>:38: (ERROR/3) Unexpected indentation.` and
  `<string>:43: (WARNING/2) Block quote ends without a blank line;
  unexpected unindent.`
- The two errored tests, named by the control-room review:
  `TestProductImportMatching.test_existing_binding_takes_priority_over_sku_barcode`
  and `TestProductVariantBinding.test_access_matrix_across_four_groups`.

This is the **first actual Odoo 19 runtime execution evidence** this PR
has received. Everything reported as "static only" in §D/§H above is
now superseded for these two specific defects — they are real,
runtime-confirmed bugs, not merely untested code.

### I.2 Fix 1 — existing-template-binding singleton-variant matching

**Root cause (confirmed real production bug, not a test-only defect):**
when an existing template binding was already resolved (found by
Shopify Product GID, not created fresh in this call), the variant
resolver had no path to bind a single incoming Shopify variant to that
template's own single, unbound Odoo variant — it only ever ran
SKU/barcode candidate search, scoped to that template's own variants.
When the incoming Shopify variant carried an SKU/barcode that did not
match the template's own singleton variant (e.g. because the Odoo
variant simply had no `default_code`/`barcode` set, or the Shopify SKU
was a coincidental decoy value unrelated to it), the importer raised
`duplicate_risk` even though there was exactly one Odoo record the
Shopify variant could possibly mean.

**Fix (production logic, not a test-only change):** a new
`_resolve_deterministic_variant()` method, called from `_apply_import()`
before each variant resolution, identifies two safe, non-guessing
cases where SKU/barcode candidate search can be skipped entirely: (1)
the pre-existing "brand-new template" case (Odoo-generated singleton of
a template this same call just created), unchanged from before; and (2)
the new case — an existing (not just-created) template binding, a
Shopify payload carrying exactly one variant, and that template having
exactly one Odoo `product.product` variant. `_resolve_variant_binding()`
still guards this candidate: if it is already bound, for this store, to
a *different* Shopify variant, the bind is blocked with a classified
`JobHandlerError('duplicate_risk', ...)` naming the conflicting Shopify
GID — never a silent rebind, never a guess between two competing
Shopify variants. A payload with more than one variant never takes this
shortcut for any index, so the conservative "no blind multi-variant
creation under an existing template" rule is completely unchanged.

**Tests added/updated** (`test_product_import_matching.py`):
- `test_existing_binding_takes_priority_over_sku_barcode` (updated,
  the previously-erroring test) — now asserts the import succeeds and
  the singleton Odoo variant is correctly bound, with `match_key`
  unset (deterministic association, not a candidate-search match).
- `test_existing_template_singleton_variant_already_bound_blocks_safely`
  (new) — the template's singleton variant already bound to a
  *different* Shopify variant blocks with `duplicate_risk`, no rebind,
  pre-existing binding left untouched.
- `test_existing_template_multi_variant_payload_still_conservative_and_atomic`
  (new) — a two-variant payload against an existing template: the
  first variant's SKU legitimately matches (would succeed on its own),
  but the second is unmatched and blocks the whole import;
  `self.env.cr.savepoint()` (fix 2 of the prior revision) rolls back
  the first variant's would-be-successful bind too — proving the
  singleton shortcut and the atomicity fix compose correctly together.

### I.3 Fix 2 — variant-binding ACL test fixture

**Root cause (test-fixture-only bug, confirmed by the control-room
review's own diagnosis, not a connector ACL defect):**
`test_access_matrix_across_four_groups` created its supporting
`product.template` record via
`self.env['product.template'].with_user(self.user_admin).create(...)`
— forcing the connector admin test user's own (real, non-superuser)
Odoo access context. The connector admin group is not, and must not
become, a member of Odoo's own Products/Create group — that would be an
unjustified widening of an Odoo application permission having nothing
to do with this module's own binding-model ACLs, which is exactly what
this test is supposed to verify. This is correct Odoo ACL enforcement
being exposed by a bug in the test's own fixture, not a defect in the
connector's ACL rows.

**Fix (test file only, `test_product_variant_binding.py`):** the
supporting `product.template` is now created via plain
`self.env['product.template'].create(...)` — the normal test
environment/setup (superuser) context, exactly matching the pattern
`_make_template_binding()` (used earlier in the very same test) and
`test_product_template_binding.py`'s own equivalent helper already use.
**No connector group ACL was touched** — `ir.model.access.csv` is
unchanged (confirmed by `git status`); no `product.template`/
`product.product` create right was granted to any
`shopify_connector_core.group_shopify_connector_*` group.

### I.4 Fix 3 — docutils/RST build-log warning

**Investigation:** installed `docutils` (0.23) locally and
systematically parsed every module/class/function docstring and both
manifest `description`/`summary` fields across
`shopify_connector_product` (and, to rule out a `shopify_connector_core`
source given "Do not edit `shopify_connector_core`" makes that
irrelevant to fix either way, checked there too) with
`docutils.parsers.rst.Parser` directly. **No exact reproduction of
`<string>:38`/`<string>:43` was found** — every current docstring/
manifest field in `shopify_connector_product` parsed cleanly under
strict RST parsing before this fix, and the one warning found in
`shopify_connector_core` (`shopify_connector_job.py::_claim_for_dispatch`,
an unrelated inline-literal warning at line 1) does not match either.
This is honestly reported as **inconclusive** — the exact Odoo.sh
rendering pipeline (which may differ from bare `docutils.core.
publish_string`, e.g. via `pypandoc` or a different settings profile)
was not available to reproduce locally.

**Fix applied per the final prompt's own explicit fallback instruction**
("if uncertain, simplify the manifest description and any long
RST-heavy model docstring... enough to eliminate blockquote/list
indentation issues"): both `__manifest__.py`'s `description` field and
`shopify_connector_product_importer.py`'s `ShopifyConnectorProductImporter`
class docstring (by far the longest, most RST/Markdown-flavored
docstring in the module — double-backtick literals, a bulleted list, a
section-title underline, numbered lists with bold lead-ins) were
rewritten as **plain prose paragraphs only** — no headers, no literal
markup, no bulleted or numbered lists, no bold/emphasis markers. This
removes every RST-sensitive construct regardless of the true root
cause, while preserving every substantive fact the original content
recorded (DEC-006/DEC-014/MBQ-55 citations, the four control-room-fix
summaries, the new singleton-variant design decision). **No functional
behaviour changed** — confirmed by `py_compile`/`pyflakes` clean, and by
the fact that only docstring/description string literals were edited,
no executable code. Both new versions were re-verified clean under the
same local `docutils` parse.

### I.5 Test count and validation status

4 test files, **53 test methods** (up from 51 — 2 new tests added in
`test_product_import_matching.py`; `test_product_variant_binding.py`'s
test count is unchanged, only its existing test's fixture was fixed).

**Validation status:** `py_compile`/`pyflakes` clean on every changed
file; the same source-level mutation/bypass/forbidden-model guards
re-run clean; the local `docutils` RST scan re-run clean on both
rewritten strings. **No Odoo runtime was available in this session's
own sandbox to re-execute the fixed tests** — the fixes are informed by
real, user-provided Odoo.sh failure evidence (§I.1) and are believed
correct based on careful tracing of the fixed code against that
evidence, but **this session does not, and cannot, claim a new green
Odoo.sh build** — that requires an actual next Odoo.sh run, not
performed by this session.

**Self-audit (control-room instructions, all confirmed):** no
`shopify_connector_core` file changed; no file added outside the Task
010 allowed-file envelope (only 4 pre-existing files modified, zero new
files); the existing-template + singleton-variant case now succeeds
(traced by hand against the fixed code, §I.2); an already-bound
singleton variant blocks safely and classified (`duplicate_risk`,
§I.2); the existing-template multi-variant case remains conservative
and atomic (§I.2, third new test); the variant-binding ACL test no
longer creates `product.template` as a connector-role user (§I.3); no
connector group received `product.template`/`product.product` create
rights (`ir.model.access.csv` unchanged); the docutils/RST source was
investigated and both plausible candidates simplified to plain prose
(§I.4, root cause not definitively confirmed, honestly reported as
such); no UI/webhook/OAuth/export/customer/order/inventory/fulfillment
scope added; no Shopify mutation logic added; tests updated (§I.2);
this document, AR-036, the handoff, and the PR body all updated; PR
remains draft/unmerged.

## J. Second Odoo.sh red-build revision (comment ID `4927455927`)

**Decision: REVISE. Not merged. Kept draft.**

### J.1 Evidence (user-provided, not independently re-run by Claude)

- Module `shopify_connector_product`: **2 failures, 0 errors of 53
  tests.**
- Full database load: **2 failed, 0 error(s) of 220 tests.**
- Build-log docutils/RST warning, **byte-for-byte identical to §I.1's**:
  `<string>:38: (ERROR/3) Unexpected indentation.` and
  `<string>:43: (WARNING/2) Block quote ends without a blank line;
  unexpected unindent.`
- The two failing tests, named by the control-room review:
  `TestProductImportMatching.test_sku_match_when_no_existing_binding`
  and `TestProductImportMatching.test_barcode_match_when_no_sku_match`
  (both `AssertionError: False != 'sku_reference'` /
  `AssertionError: False != 'barcode'` on `variant_bindings.match_key`).

### J.2 Fix 1 — narrow the singleton-variant shortcut to existing bindings only

**Root cause (confirmed real production bug, a regression introduced by
§I's own fix 1, not a test-only defect):** `_resolve_deterministic_variant()`
took the singleton shortcut whenever the *resolved* template (regardless
of *how* it was resolved) had exactly one `product.product` variant and
the payload carried exactly one variant. This correctly covered the
existing-binding case (§I fix 1's intended target) but also
incorrectly covered the SKU/barcode candidate-match case: when
`_resolve_template_binding()` matched an existing, unbound
`product.template` by its singleton variant's own SKU or barcode, that
same singleton-variant shape caused the shortcut to fire and skip
`_find_variant_candidates()` entirely — so the variant binding was
still created correctly, but its `match_key` was left unset (`False`)
instead of `sku_reference`/`barcode`, because the SKU/barcode match was
never actually performed at the variant level.

**Fix (production logic, not a test-only change):**
`_resolve_template_binding()` now returns a three-way
`template_resolution_source` string (`'existing_binding'`,
`'candidate_match'`, or `'created'`) as its second element, in place of
the previous `just_created` boolean. `_resolve_deterministic_variant()`
now keys its two shortcut cases off this explicit source: the
`'created'` case is unchanged (Odoo-generated singleton of a template
this same call just created); the singleton-match case now requires
`template_resolution_source == 'existing_binding'` specifically. A
template resolved via `'candidate_match'` never takes either shortcut,
at any index, regardless of how many variants the template or the
payload has — its variant(s) always go through the ordinary
`_find_variant_candidates()` match-key search, exactly as before §I's
fix was introduced. This preserves every behaviour §I fix 1 was meant
to add (the existing-binding singleton case, the already-bound-singleton
guard, the multi-variant conservative/atomic case) while removing the
unintended overreach into the candidate-match path.

**Tests added/updated** (`test_product_import_matching.py`):
- `test_sku_match_when_no_existing_binding` (docstring annotated as a
  regression test — this test's own fixture shape, a singleton template
  matched by SKU against a singleton-variant payload, *is* the exact
  regression scenario; no production-code change was needed in the test
  itself, since the fix is entirely in `_resolve_deterministic_variant()`/
  `_resolve_template_binding()`).
- `test_barcode_match_when_no_sku_match` (same annotation, for the
  barcode candidate-match path).
- The three tests added/updated for §I fix 1
  (`test_existing_binding_takes_priority_over_sku_barcode`,
  `test_existing_template_singleton_variant_already_bound_blocks_safely`,
  `test_existing_template_multi_variant_payload_still_conservative_and_atomic`)
  were re-traced by hand against the narrowed fix and confirmed to still
  pass unchanged — none of them needed edits, since all three exercise
  the `'existing_binding'` source, which keeps the exact same shortcut
  behaviour as §I.

### J.3 Fix 2 — docutils/RST build-log warning, re-investigated

**New evidence changes the conclusion from "inconclusive" (§I.4) to "not
from PR #138's files":** the second Odoo.sh build ran against commit
`636493e` — the exact commit that already contained §I fix 3's plain-prose
rewrite of both `__manifest__.py`'s `description` field and the
`ShopifyConnectorProductImporter` class docstring. Despite that
substantial content rewrite (a full removal of the section-underline,
bulleted/numbered lists, and double-backtick literals §I.4 identified as
RST-sensitive), the build-log warning reappeared at the **exact same
line numbers**, `<string>:38` and `<string>:43`, byte-for-byte identical
to the first red build. If either rewritten file were the true source,
changing their content would necessarily have shifted which line the
parser flagged. It did not shift at all. This is strong evidence the
warning does not originate from `shopify_connector_product`'s manifest
description or the importer's class docstring, and, by extension, is not
proven to originate from PR #138 at all.

**Further scan (PR #138 changed files only, all 12):** re-ran the same
local `docutils` 0.23 parse against every module/class/function
docstring and manifest field across all files this PR has ever touched
(models, tests, manifest, security CSV has no docstrings). Zero
`system_message` nodes found in any of them — every docstring/
description in `shopify_connector_product` parses cleanly under strict
RST parsing. The only construct that even superficially resembled the
reported warning shape was a bulleted list this session's own draft of
`_resolve_deterministic_variant()`'s docstring introduced — a **private
method** docstring, never rendered through Odoo's manifest-description
RST pipeline, so not a plausible source either way — and it was rewritten
as plain prose regardless, for consistency with this class's own stated
docstring style rule and to remove any doubt.

**Conclusion:** the docutils/RST warning is **not proven to be
introduced by PR #138**, and the identical-line-number evidence above is
a positive indication it is pre-existing/unrelated build-log noise (for
example, from another already-installed module's own manifest
description, or an unrelated log line interleaved from a parallel
worker during database setup — the log line immediately preceding the
warning, `Prepare computation of res.partner.email_normalized`, is
unrelated to any file in this addon). Per this revision's own
instruction, no further file was edited to chase this warning, and no
forbidden file was touched.

### J.4 Test count and validation status

4 test files, **53 test methods** (unchanged from §I — no new test
method was added this revision; two existing tests received docstring
annotations only, no assertion changes).

**Validation status:** `py_compile`/`pyflakes` clean on every changed
file; the same source-level mutation/bypass/forbidden-model guards
re-run clean; a fresh local `docutils` RST scan across all 12 PR-changed
files re-run clean (0 warnings). **No Odoo runtime was available in this
session's own sandbox to re-execute the fixed tests** — the fix is
informed by real, user-provided Odoo.sh failure evidence (§J.1) and is
believed correct based on careful hand-tracing of both previously-failing
tests and all five singleton/candidate-match tests from §I against the
narrowed fix, but **this session does not, and cannot, claim a new green
Odoo.sh build** — that requires an actual next Odoo.sh run, not
performed by this session.

**Self-audit (control-room instructions, all confirmed):** no
`shopify_connector_core` file changed; no file added outside the Task
010 allowed-file envelope (only 2 pre-existing files modified this
revision — the importer and its test file — zero new files); the
deterministic singleton shortcut no longer runs for SKU/barcode
candidate-template matches (§J.2, confirmed by hand-trace); SKU variant
`match_key` is `sku_reference` again (§J.2); barcode variant `match_key`
is `barcode` again (§J.2); the existing-template singleton shortcut
still works unchanged (§J.2, re-traced); the already-bound singleton
guard still works unchanged (§J.2, re-traced); the multi-variant
conservative/atomic case still works unchanged (§J.2, re-traced); the
atomic `self.env.cr.savepoint()` behaviour is untouched; no UI/webhook/
OAuth/export/customer/order/inventory/fulfillment scope added; no
Shopify mutation logic added; this document, AR-036, the handoff, and
the PR body all updated; PR remains draft/unmerged.

## Stop condition

Per final prompt §14: this PR is opened as **DRAFT**. It is not marked
ready for review and not merged. This revision (comment ID
`4927455927`, following the earlier revisions at comment IDs
`4927037139` and `4927278355`) does not change that — it remains
**DRAFT, unmerged**. Runtime validation is **pending the next Odoo.sh
build** — this session does not claim, and cannot independently
confirm, a green result. ChatGPT's own separate review is the next
required act — see the mandatory handoff update
([`research-handoff.md`](../01-research/research-handoff.md)) for the
exact next-session prompt.
