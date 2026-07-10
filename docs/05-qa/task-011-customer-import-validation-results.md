# Task 011 — Validation Results (Customer Import / Matching)

## Summary

**Revised twice, then closed out with green runtime evidence, per
ChatGPT control-room review of PR #145 (GitHub comment IDs
[`4934451381`](https://github.com/AdamsOdoo/Adams/pull/145#issuecomment-4934451381),
[`4934627954`](https://github.com/AdamsOdoo/Adams/pull/145#issuecomment-4934627954),
and
[`4934730895`](https://github.com/AdamsOdoo/Adams/pull/145#issuecomment-4934730895)).
Still draft PR, ready for ChatGPT's final merge review.** This is the
first implementation session for Task 011, executed under the explicit
gate opened by the customer-domain gate-opening act (GitHub comment
`4934249603`, PR #144, merge commit
`8b364aa360cb596dd584bbc8345b790cc7ad20ed`). The first submission of
this PR omitted the final prompt's required unresolved-country/state
informational job-log note; that omission was reviewed as **not
acceptable as-is** and was fixed -- see §H for that revision record. A
subsequent live Odoo.sh run (the first this PR has actually received)
then found exactly one runtime test failure -- a brittle, formatting-
dependent source-level assertion, not a functional importer defect --
now fixed; see §I for that revision record. **A second live Odoo.sh
run then came back green: `0 failed, 0 error(s) of 268 tests`** -- see
§J for the full runtime-green closure record, including the exact
quoted summary lines and the database/build identifier. No live Odoo/
PostgreSQL runtime is reachable in **this session's own environment**
(no `odoo` package installed, no Odoo.sh access, no external CI
configured for this repository); the green runtime evidence in §J was
provided by the operator (an Odoo.sh install log), not independently
run by Claude, and is recorded honestly as such, mirroring the format
of
[`task-010-product-import-validation-results.md`](./task-010-product-import-validation-results.md)'s
own "user-provided, not independently re-run by Claude" convention.
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
    matched partner; no child partner ever created. **When a provided
    country/state code cannot be resolved and this call runs through
    the dispatcher's job context, an informational `event_type='note'`
    job-log row is appended through the existing sanctioned
    `job.log._system_append()` path (§H)** -- direct
    `_apply_import(store, payload)` calls with no job continue to work
    with zero job context and simply skip the note; the field is left
    empty either way.
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
   -- **implemented**, per the control-room revision in §H below.
   `import_customer_sync()`/`_apply_import()`/`_create_partner()` each
   gained an optional `job=False` parameter, threaded through from
   `_handle_customer_import_sync(job)` only -- `_apply_import(store,
   payload)` remains fully direct-testable and requires no job context
   for its every other test. When a provided country or province/state
   code cannot be resolved by lookup, and a `job` is present,
   `_create_partner()` appends one informational `event_type='note'`
   row through the existing, sanctioned
   `job.log._system_append()` path -- no new field, no core edit, no
   server log write. The note's `message` is minimal/operator-safe
   (names only that a code-based lookup was skipped, never the
   specific code, partner, email, phone, or full address); the bare
   code itself lives only in `technical_detail`.

## D. Static validation

**Superseded by §J below for the runtime-execution question** (a live
Odoo.sh run has since come back green, `0 failed, 0 error(s) of 268
tests`) -- everything else in this section remains accurate as the
static-validation record.

No `odoo` package is installed in this environment and no external CI/
Odoo.sh is reachable from this session -- every check below is static
(re-run after the §H revision, not only at first submission):

- `python3 -m py_compile` -- clean on every changed Python file (the
  importer and `test_customer_import_matching.py`; the other 9 files
  from the first submission are unchanged).
- `python3 -m pyflakes` -- clean on the same changed files; the only
  "unused import" findings project-wide remain the four `__init__.py`
  aggregator files, the expected Odoo module-registration pattern
  (identical to every existing `__init__.py` in
  `shopify_connector_core`/`shopify_connector_product`).
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
  before merge** (SRR-06 standing practice, final prompt §12) and, at
  the time this section was written, had **not** been obtained.
  **Superseded by §J below: this run has since been obtained and came
  back green** (`0 failed, 0 error(s) of 268 tests`). This paragraph is
  kept verbatim as an accurate record of this PR's status prior to that
  run, per this project's own history-preservation convention (mirrors
  Task 010's own validation record).

## E. What is accepted

Nothing is accepted by this document. This is an honest evidence record
for ChatGPT's own separate review -- see the Stop condition below. (§J's
runtime-green result is likewise not a merge acceptance -- only
ChatGPT's own final merge review can accept and merge this PR.)

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
- **Runtime execution proof for this task's own test files** -- now
  **obtained** (§J: `0 failed, 0 error(s) of 268 tests`, database
  `adamsmen-claude-task-011-shopify-connector-solrrp-34736893`) --
  superseding the earlier "not yet obtained" status in §D. This does
  not by itself constitute ChatGPT's final merge review or a merge
  decision.
- **The four in-task decisions in §C** are conservative, documented
  choices, exercised only against fake/stub Shopify data in this
  runtime run (VAL-B2 remains untouched, no live Shopify data was
  involved), and not yet reviewed by ChatGPT.

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

## H. Revision after control-room review (comment ID `4934451381`)

**Decision: REVISE before runtime validation / merge review. Not
merged, kept draft.**

### H.1 What was found

ChatGPT's review confirmed the PR was largely within the accepted
Task 011 envelope (scope, allowed-file boundary, D1 recall-safety, and
the honest static-only validation status were all confirmed correct),
but found one required fix: the final prompt's §8.3 unresolved-
country/state behavior requires **four** guarantees, not three --
empty field, import succeeds, no country/state record invented, **and
an informational job-log line appended**. The first submission met
only the first three and explicitly did not implement the fourth,
reasoning that `_apply_import(store, payload)` had no `job` parameter
to log through. The review held that this reasoning was not
acceptable as-is, since the allowed importer file can carry an
optional job-context parameter without any core edit.

### H.2 Fix applied

`shopify_connector_customer_importer.py` only (no other production
file changed):

- `import_customer_sync(store, shopify_customer_gid, job=False)`,
  `_apply_import(store, payload, job=False)`,
  `_resolve_customer_binding(store, payload, job=False)`, and
  `_create_partner(shopify_gid, payload, job=False)` each gained an
  optional `job` parameter, defaulting to `False` and threaded through
  only -- no other behavior changes. Every existing direct test call
  (`Importer._apply_import(store, payload)` with no `job` argument)
  continues to work unmodified.
- `_handle_customer_import_sync(job)` (the dispatcher seam) now passes
  `job=job` into `import_customer_sync()` -- the only call site that
  ever supplies a job.
- A new `_log_unresolved_address_code(job, kind, code)` helper: a
  no-op when `job` is falsy (direct calls); otherwise appends exactly
  one `event_type='note'` row via the existing, unmodified
  `shopify.connector.job.log._system_append()` path -- no new field,
  no core edit, no server log write (`logging`/`_logger` is not used
  anywhere in this file). Called from `_create_partner()` when a
  provided `country_code` fails to resolve, and separately when a
  provided `province_code` fails to resolve under an already-resolved
  country -- mirroring the same two distinct failure points named in
  §8.3.
- **Message content, kept minimal and operator-safe:** the
  human-readable `message` names only that a country/province lookup
  was skipped (`"Customer import: an unresolvable country code left
  the corresponding partner field empty; ..."` / same for
  province/state) -- it never repeats the specific code, the partner's
  name/email, any street/city/zip value, or any phone value. The bare
  offending code (e.g. `country_code=ZZ`) lives only in
  `technical_detail`, the field this project's own convention already
  reserves for structured/diagnostic detail (mirroring the §8.2
  candidate-evidence payload's own message-vs-technical_detail split).

### H.3 Tests added/updated (`test_customer_import_matching.py`)

- `test_create_path_unresolvable_country_leaves_field_empty` (updated)
  -- now also asserts the direct, no-job call appends **zero** new
  `job.log` rows (proving `_apply_import(store, payload)` remains
  fully usable with no job context, per the review's own requirement).
- `test_create_path_unresolvable_state_leaves_field_empty` (new) --
  country resolves (`US`), province code does not (`ZZ`); `state_id`
  stays empty, `country_id` is set, import succeeds.
- `test_unresolved_country_logs_informational_note_via_job_path` (new)
  -- runs a `customer_import_sync` job end-to-end through
  `Dispatch.run_drain()` against a fake client returning an
  unresolvable `countryCodeV2`; asserts exactly one `job.log` row with
  `event_type='note'` exists, `technical_detail == 'country_code=ZZ'`,
  and the `message` contains neither the fake customer's phone number,
  street, city, nor email.
- `test_unresolved_state_logs_informational_note_via_job_path` (new) --
  same shape for an unresolvable `provinceCode` under a resolving
  country; asserts `technical_detail == 'province_code=ZZ'` and the
  `message` contains neither the street nor city value.

Test count: `test_customer_import_matching.py` gained 3 new test
methods (1 updated, 3 new) in this revision; the other three test
files are unchanged.

### H.4 Validation status after this revision

Still static only -- no Odoo runtime was reachable in this session
either time. `python3 -m py_compile` and `python3 -m pyflakes` are
clean on both changed files; a fresh local `docutils` 0.23 RST scan of
every docstring/manifest field across the whole addon (not only the
changed file) re-ran with **zero warnings**; the same source-level
guards (zero mutation, zero bypass identifier, zero forbidden-model
reference, zero `customer_fallback_partner_id` read, and a new check
confirming no `logging`/`_logger` call exists in the importer) were
re-run and remain clean. **A live Odoo.sh branch-database run of the
full suite is still mandatory before merge and has still not been
obtained** -- this revision does not change that requirement.

**Self-audit against the review's own instructions (all confirmed):**
no `shopify_connector_core`/`shopify_connector_product`/`adams_base`
file touched; no new model or field added; no server log write added;
only the existing job/job-log pathway used; `_apply_import(store,
payload)` remains directly testable and every pre-existing direct-call
test still passes unmodified (traced by hand -- no runtime available);
direct calls with no job continue to skip the note; the dispatch/job
path logs it; the message is minimal and operator-safe with no phone
data, no full address data, and no other Shopify-bound sensitive data;
no Shopify write added; no UI/webhook/OAuth/order/product/inventory/
fulfillment/next-task logic added; this document and the AR-040 row
both updated to record the actual patched behavior rather than the
prior "not implemented" framing; PR remains draft, unmerged.

## I. Live Odoo.sh run and runtime-failure fix (comment ID `4934627954`)

**Decision: REVISE -- one runtime test failure found. Not merged, kept
draft.**

### I.1 First live Odoo.sh runtime evidence (user/control-room-provided,
not independently run by Claude)

This is the **first actual Odoo 19 runtime execution evidence** this PR
has received -- everything reported as "static only" in §D/§H above is
now superseded for the one specific defect below; it is a real,
runtime-confirmed test-brittleness bug, not merely untested code.
Quoted verbatim from the control-room review (comment `4934627954`):

- `Module shopify_connector_sale: 1 failures, 0 errors of 48 tests`
- Final database summary: `1 failed, 0 error(s) of 268 tests`
- Failing test:
  `TestCustomerImportMatching.test_source_level_single_execute_call_uses_fixed_query_constant`

The review also confirmed, and this record restates without treating
either as a failure: the SQL `bad query` log lines for missing-
required-field/duplicate-uniqueness-constraint tests are expected
negative-test noise (the same class of expected noise Task 010's own
validation record already documented in its §K.3), and the build-log
docutils warning **did not fail this run**.

### I.2 Root cause

**Test-fixture-only bug, not a functional importer defect.** The
failing test asserted the exact source substring
`"CUSTOMER_IMPORT_QUERY, variables="`. The actual, correct production
code passes the fixed query constant across a cosmetic line break:

```python
self.env['shopify.connector.api.client'].execute(
    store, CUSTOMER_IMPORT_QUERY,
    variables={'id': shopify_customer_gid},
)
```

The substring the test looked for never appears verbatim once the call
is wrapped onto three lines -- a purely cosmetic formatting difference
with zero functional effect on the importer, which genuinely does issue
exactly one `execute()` call using the fixed constant. This is the
identical class of brittleness already logged against the equivalent
Task 010 assertion pattern in principle (a raw-substring source guard
tied to exact formatting), not a new kind of defect.

### I.3 Fix applied

`test_customer_import_matching.py` only (no production file changed):
`test_source_level_single_execute_call_uses_fixed_query_constant` is
rewritten to parse the importer source with Python's `ast` module
instead of matching a raw substring, per the review's own preferred
approach. The rewritten test:

1. Parses `shopify_connector_customer_importer.py` with `ast.parse()`.
2. Walks the tree for every `ast.Call` node whose function is an
   attribute access named `execute`, and asserts there is **exactly
   one** such call anywhere in the module.
3. Asserts that call's arguments (positional or keyword) contain a
   plain `ast.Name` reference to `CUSTOMER_IMPORT_QUERY` -- proving the
   fixed constant is used, independent of argument order, line
   placement, or wrapping.
4. Asserts none of that call's arguments is an `ast.JoinedStr`
   (f-string) or a literal string `ast.Constant` -- proving no
   dynamically-built or second, differently-sourced operation string
   could stand in for the query.
5. Re-asserts, directly against the imported `CUSTOMER_IMPORT_QUERY`
   constant, that it still starts with `query` and never contains
   `mutation` -- the query remains read-only.

This proves the identical safety property the original test intended
(one execute() call, always using the fixed, read-only query constant,
never a dynamic/second operation string) without depending on any
particular line-wrapping or whitespace choice in the production file.
Manually simulated against the actual current importer file before
committing: the rewritten logic finds exactly one `execute()` call,
confirms `CUSTOMER_IMPORT_QUERY` is referenced, and finds no literal-
string/f-string argument -- passes.

### I.4 Validation status after this fix

Still static only -- no Odoo/PostgreSQL runtime is reachable in this
session's own environment (unchanged from every prior session). `python3
-m py_compile` and `python3 -m pyflakes` are clean on the changed test
file; a fresh local `docutils` 0.23 RST scan of every docstring/
manifest field across the whole addon re-ran with **zero warnings**
(reconfirming the build-log docutils warning the review noted as
non-blocking is not attributable to any `shopify_connector_sale` file,
consistent with Task 010's own established conclusion that the
identical warning is pre-existing/unrelated build-log noise); the same
source-level guards (zero mutation, zero bypass identifier, zero
forbidden-model reference) were re-run and remain clean. The rewritten
test's own logic was additionally hand-simulated against the real
importer file (§I.3) and confirmed to pass.

**A new live Odoo.sh branch-database run has not been independently
obtained by this session** -- this session has no live Odoo.sh/CI
access, exactly as every prior session in this PR's history. The fix
is believed correct based on the root-cause trace above and the
manual AST-logic simulation against the real file, but **this session
does not, and cannot, claim a new green Odoo.sh build** -- that
requires an actual next Odoo.sh run, not performed by this session.

**Self-audit (review's own instructions, all confirmed):** only
`test_customer_import_matching.py` changed (no production file, no
manifest, no security file, no core/product/adams_base file); the
rewritten test proves the same four properties the review named
(exactly one `execute()` call; it uses `CUSTOMER_IMPORT_QUERY`; no
dynamic/second operation string; the query stays read-only, no
mutation); the SQL `bad query`/ACL-denial log noise was not
misclassified as a failure; the docutils warning was rechecked, found
not attributable to this PR's files, and not chased further per the
review's own routing instruction; PR remains draft, unmerged; no
Task 012/013/014/015, UI, webhook, OAuth, or MBQ-05 scope touched.

## J. Runtime-green closure -- live Odoo.sh run confirmed green

**Decision: runtime validation passed. PR #145 ready for final ChatGPT
merge review. Still not merged, kept draft.**

### J.1 Scope of this closure session

Docs-only. This session changed no production code, no test file, no
manifest, no security file, and no core/product/adams_base file --
only this validation record, the AR-040 log row, the research
handoff, and the PR #145 body were updated, per the operator's own
narrow closure-session scope.

### J.2 Green runtime evidence

- **PR head SHA at the time of this run:** `45d275c9c459db4d6696e3198472726eccdb6458`
  (the exact commit the §I fix produced -- unchanged by this
  docs-only closure session).
- **Odoo.sh database/build identifier** (from the install log's own
  connection and summary lines): `adamsmen-claude-task-011-shopify-connector-solrrp-34736893`
  (Postgres connection line: `database: p_adamsmen_claude_task_011_shopify_connector_solrrp_34736893@192.168.1.1:5432`).
- **Exact quoted final runtime summary lines** (verbatim from the
  Odoo.sh install log, `odoo.tests.stats`/`odoo.tests.result` logger
  lines, timestamp `2026-07-10 11:12:14,762`):

  ```
  odoo.tests.stats: shopify_connector_core: 187 tests 1.66s 3556 queries
  odoo.tests.stats: shopify_connector_product: 61 tests 1.60s 2485 queries
  odoo.tests.stats: shopify_connector_sale: 56 tests 0.74s 1067 queries
  odoo.tests.result: 0 failed, 0 error(s) of 268 tests when loading database 'adamsmen-claude-task-011-shopify-connector-solrrp-34736893'
  ```

  Per the OP-43 lesson (Task 010's own validation record): the
  per-module `odoo.tests.stats` counts (187 + 61 + 56 = 304) do not
  arithmetically reconcile with the final `odoo.tests.result` total
  (268) -- this discrepancy is **not resolved or explained by this
  session**, is quoted verbatim rather than synthesized, and does not
  change the green outcome: Odoo's own authoritative summary line is
  `0 failed, 0 error(s) of 268 tests`, with no ambiguity in that
  figure itself.
- **Module completion line:**
  `odoo.modules.loading: Module shopify_connector_sale loaded in 0.88s (incl. 0.74s test), 144 queries (+1067 test, +144 other)`.

### J.3 The previous brittle AST-test failure is no longer present

`TestCustomerImportMatching.test_source_level_single_execute_call_uses_fixed_query_constant`
starts (`Starting TestCustomerImportMatching.test_source_level_single_execute_call_uses_fixed_query_constant ...`)
and the log proceeds directly to the next test
(`Starting TestCustomerImportMatching.test_unresolved_country_logs_informational_note_via_job_path ...`)
with **zero `ERROR`-level or traceback lines in between** -- the
identical pattern every other passing test in this run shows. This is
independent, direct confirmation (not an inference from the aggregate
count alone) that the §I AST-based fix resolved the one failure
comment `4934627954` reported.

### J.4 SQL `bad query` lines are expected negative-test noise, not failures

Exactly five `ERROR`-level `odoo.sql_db: bad query` lines appear
during `shopify_connector_sale`'s test run, and they map one-to-one
onto this addon's own tests that intentionally assert database
constraints:

- `null value in column "partner_id" ... violates not-null constraint`
  -- `test_requires_partner_id`.
- `null value in column "shopify_gid" ... violates not-null constraint`
  -- `test_requires_shopify_gid`.
- `null value in column "store_id" ... violates not-null constraint`
  -- `test_requires_store_id`.
- `duplicate key value violates unique constraint "shopify_connector_customer_binding_store_shopify_gid_uniq"`
  and `..._store_partner_uniq` (two lines) --
  `test_direct_create_collisions_prove_uniqueness_backstop`.

No other `ERROR`-level line appears anywhere in `shopify_connector_sale`'s
test section. This is the same class of expected noise Task 010's own
validation record (§K.3) already documented for its own constraint/ACL
tests -- confirmed here, not merely assumed, by direct inspection of
this run's own log.

### J.5 The docutils warning did not fail the build, and is confirmed unrelated to this PR's files

The build log's docutils/RST warning --

```
<string>:38: (ERROR/3) Unexpected indentation.
<string>:43: (WARNING/2) Block quote ends without a blank line; unexpected unindent.
```

-- appears immediately after `odoo.models: Prepare computation of
res.partner.email_normalized`, during the **`mail`** module's own load
(module 23/44) -- a full ten modules and roughly five seconds after
`shopify_connector_sale` (module 13/44) already finished loading and
testing. It is not adjacent to, or plausibly sourced from, any
`shopify_connector_sale` file. This independently corroborates (via
direct log-position evidence, not renewed guesswork) Task 010's own
established conclusion that this exact warning is pre-existing/
unrelated build-log noise. It did not fail this build -- the final
result is still `0 failed, 0 error(s) of 268 tests` -- and, per the
review's own routing instruction, it is not chased further or fixed
in this PR, since it is not attributable to any Task 011 file.

### J.6 Final result

**Runtime validation passed.** `0 failed, 0 error(s) of 268 tests`,
verbatim from the Odoo.sh install log, database
`adamsmen-claude-task-011-shopify-connector-solrrp-34736893`, head SHA
`45d275c9c459db4d6696e3198472726eccdb6458`. Combined with the static
validation already recorded in §D/§H.4/§I.4 (unchanged, all clean),
Task 011's own validation requirements (final prompt §11/§12) are now
satisfied. **PR #145 is ready for ChatGPT's final merge review** -- it
remains **draft** and **unmerged**; this record does not itself
authorize merge, mark it ready for review, or start any further scope.

## Stop condition

Per final prompt §14: this PR is opened as **DRAFT**. It is not marked
ready for review and not merged. Neither this closure session, nor the
runtime-failure fix (comment ID `4934627954`), nor the revision before
it (comment ID `4934451381`), changes that -- it remains **DRAFT,
unmerged**. Runtime validation is now **green** (§J: `0 failed, 0
error(s) of 268 tests`) -- **ChatGPT's own final merge review is the
next required act**; only ChatGPT may merge or mark this PR ready for
review -- see the mandatory handoff update
([`research-handoff.md`](../01-research/research-handoff.md)) for the
exact next-session prompt.
