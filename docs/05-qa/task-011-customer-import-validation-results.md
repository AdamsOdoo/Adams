# Task 011 — Validation Results (Customer Import / Matching)

## Summary

**Draft PR opened, not yet reviewed by ChatGPT.** This is the first
implementation session for Task 011, executed under the explicit gate
opened by the customer-domain gate-opening act
(GitHub comment `4934249603`, PR #144, merge commit
`8b364aa360cb596dd584bbc8345b790cc7ad20ed`). No live Odoo/PostgreSQL
runtime was reachable in this session's own environment (no `odoo`
package installed, no Odoo.sh access, no external CI configured for
this repository) -- every validation check below is static, honestly
reported as such, mirroring the format of
[`task-010-product-import-validation-results.md`](./task-010-product-import-validation-results.md).
This record itself is **docs-only**: it does not modify any addon/code,
test, manifest, XML/security, migration, or CI file.

## A. Scope

- Base: `Shopify-connector` at commit `8b364aa360cb596dd584bbc8345b790cc7ad20ed`
  (PR #144 merge commit) -- confirmed as this session's actual tip via
  `git rev-parse` and GitHub `pull_request_read` before any code was
  written; no drift.
- New addon: `shopify_connector_sale` (manifest depends:
  `['shopify_connector_core']` only -- D6).
- **Explicitly out of scope for this PR** (unchanged, not implemented):
  - No customer export or any write back to Shopify of any kind --
    zero mutation call anywhere in the diff (§D below).
  - No order/product/inventory/fulfillment logic of any kind; no
    `sale.order` reference.
  - No consumption of `customer_fallback_partner_id` (Posture A --
    defined, never read by any importer code path).
  - No UI, view, menu, action, wizard, webhook, or OAuth file of any
    kind.
  - No edit to any `shopify_connector_core` or `shopify_connector_product`
    file -- the three seam registrations (job_type `selection_add`,
    `_domain_flag_for_job_type()` override, `_get_handlers()` override)
    are declared entirely inside
    `shopify_connector_customer_importer.py`, via classic Odoo
    inheritance.

## B. What was implemented

- **`shopify.connector.customer.binding`** -- extends
  `shopify.connector.binding.mixin`, declares explicit `_name` and
  `_inherit`, per the accepted MBQ-55 schema (final prompt §7.1). No
  `_sql_constraints` dict -- `models.Constraint(...)` throughout,
  matching the existing core/product convention.
- **`customer_fallback_partner_id`** -- a single inert
  `Many2one('res.partner', ondelete='restrict')` field on a
  `shopify.connector.store.settings` `_inherit` extension (final prompt
  §7.2, D5, Posture A). No default, no auto-creation, no constraint, no
  compute/onchange. No importer code path reads it (confirmed by
  source-level test and behavioral outcome-equivalence test).
- **`shopify.connector.customer.importer`** (`AbstractModel`) -- the
  read-only import/matching service:
  - `import_customer_sync(store, shopify_customer_gid)` -- the only
    method that calls the Shopify API client, always with a `query`
    operation (`CUSTOMER_IMPORT_QUERY`), never a `mutation`.
  - `_apply_import(store, payload)` -- the pure matching/creation logic
    (no Shopify call), directly unit-testable against a fake/stub
    payload dict, atomic via `self.env.cr.savepoint()`.
  - Match-key priority implemented exactly as final prompt §8.1 fixes
    it: existing binding -> email (recall-safe candidate discovery,
    no exact/`=ilike` prefilter -- `[('email', '!=', False)]` +
    mandatory Python-side `email_normalize()` comparison on both sides,
    applied identically to the active-candidate and the
    archived-inclusive search) -> exactly-one-active-candidate bind
    (guarded against `binding_conflict`) -> archived-match check
    (`duplicate_risk`, no create/bind/un-archive) -> confident no-match
    create, gated -> ambiguous (`ambiguous_match`, no row) /
    missing-email (`duplicate_risk`, no row), all routed to
    `blocked_manual_review` via the existing, unmodified
    `JobHandlerError`/`_route_failure()` mechanism.
  - Ambiguous-match and archived-match candidate evidence carried as the
    exact §8.2 JSON shape in `JobHandlerError.technical_detail`, which
    the dispatcher's own, unmodified `_route_failure()` passes straight
    through to `_transition_blocked_manual_review()`'s
    `technical_detail` parameter -- no new field, no core edit.
  - Address mapping on create only (§8.3): `defaultAddress` fields onto
    the new partner's own flat fields; country/state resolved by
    lookup only (never created); unresolvable codes leave the field
    empty without failing the import. Never written on an existing
    matched partner; no child partner ever created.
  - Person-only classification (§8.4): `is_company` is never set;
    `defaultAddress.company` (not even requested by the query) is never
    read, mapped, or stored.
- **Three extension seams**, all inside
  `shopify_connector_customer_importer.py` only:
  1. `job_type` `selection_add` -- `customer_import_sync`.
  2. `_domain_flag_for_job_type()` override -- maps
     `customer_import_sync` -> `sale_domain_enabled`, `super()` for
     every other `job_type`.
  3. `_get_handlers()` override -- registers
     `_handle_customer_import_sync`.
- **Security** -- `ir.model.access.csv` only (no new `security/*.xml`,
  no new group): 4 rows for the one binding model across the four
  existing groups (auditor read-only; operator read+create; reviewer
  read+write; admin read+write+create -- no group has `perm_unlink`,
  matching the existing core/product-wide convention).

## C. In-task decisions made (per final prompt §8/§9's own allowance)

Recorded here, not silently assumed, per this task's own governing
instructions:

1. **`res_model`/`res_id` targeting** -- not implemented by the
   dispatcher handler in this task, mirroring Task 010's own exact
   precedent (`task-010-product-import-validation-results.md` §C.1):
   the handler does not write `job.res_model`/`res_id` after a
   successful bind, since multi-customer enumeration/enqueue-trigger
   call sites are out of this job type's scope and every test in this
   PR constructs `shopify.connector.job` rows directly. The fixed
   choice for a future enqueue-trigger session (final prompt §9): target
   `res_model='shopify.connector.customer.binding'` -- the binding
   model, not the underlying `res.partner` -- for the same reason Task
   010 fixed it for the product domain (the connector-owned identity
   concept the job is really about, guaranteed to exist once a bind
   succeeds).
2. **Candidate-discovery recall-safety implementation choice (D1 rule
   2, the critical rule this task's own instructions singled out):**
   implemented via the "always-safe baseline" named in the final
   prompt -- `Partner.search([('email', '!=', False)])` (both the
   active search and the `with_context(active_test=False)`
   archived-inclusive search), with zero database prefilter narrowing
   by email value, followed by a mandatory Python-side
   `email_normalize()` comparison on both sides. The permitted
   alternative (an `('email', 'ilike', normalized_incoming)` substring
   prefilter) was considered and not chosen, since the always-safe
   baseline is simpler to verify correct by inspection and this task's
   own scope does not require it for performance -- a future
   optimization pass could introduce the substring prefilter without
   changing any test's expected outcome, since the Python-side
   comparison is unconditionally mandatory either way.
3. **Partner `name` mapping** -- not fixed by any cited accepted
   document (§7/§8 specify address and classification mapping, not the
   `name` field itself): `res.partner.name` is set to the incoming
   `displayName` (falling back to the Shopify GID only in the
   structurally-unreachable case `displayName` is itself empty, since
   Shopify's own `displayName` is non-null and already falls back
   through `firstName`/`lastName` -> email -> phone). This mirrors
   `shopify_connector_product_importer.py`'s identical `title or
   shopify_gid` pattern for `product.template.name`.
4. **Informational job-log line for unresolved country/state (§8.3)**
   -- not implemented. The final prompt's prose names this as desired
   behavior, but `_apply_import(store, payload)` -- mirroring Task
   010's own established signature convention -- has no `job`
   parameter to append a log line through, and introducing one would
   require either a new call-signature or a new job-lookup mechanism
   neither this task's allowed files nor any accepted document
   authorizes. The two behavioral guarantees the final prompt actually
   requires are met without it: an unresolvable country/state leaves
   the field empty, and the import never fails or invents a record.
   Flagged here as an honest, narrow scope gap, not silently omitted.

## D. Static validation

No `odoo` package is installed in this environment and no external CI/
Odoo.sh is reachable from this session -- every check below is static:

- `python3 -m py_compile` -- clean on every new Python file (11 files:
  4 `__init__.py`, 3 models, 4 tests).
- `python3 -m pyflakes` -- clean on all seven substantive new Python
  files (3 models, 4 tests); the only "unused import" findings are the
  four `__init__.py` aggregator files, the expected Odoo
  module-registration pattern (identical to every existing `__init__.py`
  in `shopify_connector_core`/`shopify_connector_product`).
- A local `docutils` 0.23 RST parse of every module/class/function
  docstring and the manifest `description`/`summary` fields across
  `shopify_connector_sale` -- **zero `system_message` (warning/error)
  nodes found** (per the OP-lesson from Task 010's own docutils/RST
  build-log investigation, checked proactively this time rather than
  reactively).
- **Zero Shopify mutation call anywhere in the diff** -- confirmed by
  inspection: exactly one GraphQL operation string exists in the new
  addon (`CUSTOMER_IMPORT_QUERY`), it starts with `query`, and the
  substring `mutation` does not appear inside it; a source-level check
  confirms `shopify.connector.api.client`'s `execute()` is called
  exactly once in the whole module, always with that fixed constant.
- **Only the pinned, non-deprecated `customer(id:)` field list** (§9)
  appears in the query -- confirmed by regex: no bare `\bemail\b`,
  `\bphone\b`, or `\baddresses\b` token (the deprecated fields) appears
  anywhere in the query string; every field named in §9 does appear.
- **No bypass/force/skip-gate identifier** anywhere in the importer's
  matching/creation logic (source-level grep, mirrors Part A §I.5's
  no-bypass rule).
- **No order/product/inventory/fulfillment model name** (`sale.order`,
  `product.template`, `product.product`, `stock.quant`,
  `stock.picking`, `stock.move`, `stock.location`, `account.move`,
  `account.payment`, `delivery.carrier`) anywhere in the three new
  production model files (source-level grep).
- **No reference to `customer_fallback_partner_id`** anywhere in
  `shopify_connector_customer_importer.py` (source-level grep, proving
  Posture A's "zero consumption" clause at the source level, not only
  behaviorally).
- Manifest/security CSV reviewed by hand against the exact
  `depends`/ACL-row requirements in final prompt §3/§6/D6.
- `git status`/`git diff --stat` confirm **only** the files in final
  prompt §3 changed (plus this document and the mandatory handoff/AR-log
  updates, also in §3) -- no file under `shopify_connector_core` or
  `shopify_connector_product` touched, no `adams_base` file touched.

**Not run, honestly stated:**

- No Odoo test runner (`--test-enable --test-tags`) was executed -- no
  Odoo/PostgreSQL runtime exists in this environment (PostgreSQL 16 is
  installed but not running, and no `odoo` Python package is
  installed). All 4 test files, covering every case named in final
  prompt §10, are written and statically valid but **not
  execution-proven** in this session.
- No live Shopify API call was made or attempted (explicitly out of
  scope, VAL-B2).
- **A live Odoo.sh branch-database run of the full suite is mandatory
  before merge** (SRR-06 standing practice, final prompt §12) and has
  **not** been obtained. This PR stays draft until it is.

## E. What is accepted

Nothing is accepted by this document. This is an honest evidence record
for ChatGPT's own separate review -- see the Stop condition below.

## F. What is NOT accepted / still open

Explicitly, none of the following are resolved, proven, or closed by
Task 011 or this PR -- restated from the final prompt's own hard
constraints, not weakened:

- **VAL-B2** (no live Shopify Admin API connection ever made) -- untouched.
- **MBQ-05** (both branches, including the branch B distribution/auth
  question) -- untouched; not decided by this task.
- **TD-002** (`read_fulfillments` readiness-scope correctness) --
  confirmed still `Open` in `technical-debt-register.md`, unaffected by
  this task.
- **MBQ-55's order-binding portion** -- untouched, remains fully open.
- The **fulfillment API model** decision -- untouched.
- **Lite/Full packaging** -- untouched.
- **Multi-server/concurrent-worker safety** (SRR-03/04/09) -- this task
  inherits the existing, already-merged Task 006C claim/dispatch
  mechanism unmodified; it neither closes nor claims to close any of
  these, and makes no claim that mechanism is proven safe under real
  concurrent-worker/multi-server execution.
- **Runtime execution proof for this task's own 4 test files** -- not
  yet obtained (§D above); a future session/runtime must actually run
  them before any "0 failed, 0 error(s)" claim can be made.
- **The four in-task decisions in §C** are conservative, documented
  choices, not yet exercised against real Shopify data or reviewed by
  ChatGPT.

## G. Release/UAT implication

- This PR is a **backend-only, read-import domain slice** -- no
  operator can trigger it yet (no enqueue-trigger call site exists;
  every test constructs job rows directly, mirroring
  `core_dispatch_selftest`/Task 010's own precedent).
- It is **not UAT-ready connector functionality** and must not be
  represented as such.
- Task 012/013/014, Task 015, any UI, webhook, OAuth, or Lite/Full
  packaging work remain unauthorized by this task -- the customer-domain
  gate **closes** the moment this PR opens as draft (accepted §4 rule,
  `customer-domain-gate-criteria-proposal.md`; final prompt §14) -- no
  further customer-domain work may start regardless of this PR's
  outcome.

## Stop condition

Per final prompt §14: this PR is opened as **DRAFT**. It is not marked
ready for review and not merged. Runtime validation is **pending an
Odoo.sh build** -- this session does not claim, and cannot independently
confirm, a green result. ChatGPT's own separate review is the next
required act -- see the mandatory handoff update
([`research-handoff.md`](../01-research/research-handoff.md)) for the
exact next-session prompt.
