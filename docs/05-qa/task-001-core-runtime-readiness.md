# Task 001A — Core Runtime Readiness

## Status

This is a **post-merge QA closure session for Task 001** (the
`shopify_connector_core` module scaffold, merged into `Shopify-connector` via
PR #88, merge commit `b55490743fb1f5c9ea33831b94605b9ead4229c0`). It
re-validates the merged scaffold as thoroughly as this environment allows and
records exactly what could and could not be verified without a live Odoo
runtime. **This session does not start Task 002 and does not touch
credentials, the setup wizard, the Shopify API client, webhooks, controllers,
cron execution, the dashboard, sync center, error-center UI, or any
product/customer/order/inventory/fulfillment/accounting/refund/payout/
multi-store domain module.** No operator-facing views, menus, actions, or
wizard XML are created. No migrations are created. DEC-003 through DEC-020,
`docs/04-decisions/README.md`, and `defect-pattern-log.md` are unchanged.

Branch: `claude/task-001a-core-runtime-readiness`, created from
`Shopify-connector` at `b55490743fb1f5c9ea33831b94605b9ead4229c0` (confirmed
via `git rev-parse origin/Shopify-connector` before any edit — see
[Static checks performed](#static-checks-performed)).

## Scope

**In scope:**

- Runtime-readiness review of the merged `addons/shopify_connector_core`
  module (six models, security groups, access-rights CSV).
- Static validation: Python compile, manifest parse, XML parse, CSV
  structural checks, and a targeted grep sweep for out-of-scope content.
- An explicit, documented answer on whether an Odoo runtime exists in this
  environment, and what would be needed to run one.
- A decision on whether to add automated (Odoo `TransactionCase`) tests,
  made against the repo's actual test conventions rather than invented from
  scratch.
- A manual Odoo 19 validation checklist a reviewer with a live Odoo instance
  can execute to close the remaining runtime gap.

**Out of scope (not touched, not started):**

- Credentials, tokens, secrets, or any field that would store them.
- The Shopify API client, GraphQL/REST calls, or webhook handling.
- The setup wizard or "test connection" flow.
- Any controller, `ir.cron` job, dashboard, sync center, or error-center UI.
- Any menu, action, view, or wizard XML.
- Product, customer, order, inventory, fulfillment, accounting, refund,
  payout, or multi-store domain modules.
- Database migrations.
- Task 002 or any task beyond this QA closure of Task 001.

## Static checks performed

All checks were run directly against the merged, on-disk
`addons/shopify_connector_core` tree in this container. Commands and results:

1. **Python compile** — `python3 -m py_compile` against all nine `.py` files
   in the module (`__init__.py`, `__manifest__.py`, `models/__init__.py`, and
   the six model files). **Result: OK, no syntax errors.**
   `__pycache__/` artifacts produced by the compile step were removed after
   the check (already covered by the repo's `.gitignore`; nothing new is
   committed).

2. **Manifest parse** — `ast.literal_eval()` on `__manifest__.py`, asserting
   it evaluates to a `dict` with `installable=True`, `application=False`,
   `depends=['base']`, and a `data` list containing exactly the two security
   files. **Result: OK** — `{'name': 'Shopify Connector Core', 'version':
   '19.0.1.0.0', 'depends': ['base'], 'installable': True, 'application':
   False, 'data': ['security/shopify_connector_security.xml',
   'security/ir.model.access.csv']}`.

3. **XML parse** — `xml.dom.minidom.parse()` on
   `security/shopify_connector_security.xml`, confirming well-formedness,
   exactly one `ir.module.category` record, and exactly four `res.groups`
   records (`group_shopify_connector_auditor`, `_operator`, `_reviewer`,
   `_admin`). **Result: OK**, all four groups present with the expected IDs.

4. **CSV structural check** — parsed `security/ir.model.access.csv` with
   `csv.DictReader` and asserted: exactly 20 rows; every `group_id:id`
   resolves to one of the four groups defined in the security XML; every
   `model_id:id` is one of the five **concrete** accepted models
   (`shopify_connector_store`, `_store_settings`, `_location`, `_job`,
   `_job_log`); every `(model, group)` pair among the 5×4=20 combinations is
   present exactly once; every `perm_read`/`perm_write`/`perm_create`/
   `perm_unlink` value is `0` or `1`. **Result: OK.** As expected, the
   abstract `shopify.connector.binding.mixin` has no access row (abstract
   models have no table and cannot be granted CRUD).

5. **Grep sweep for out-of-scope content** — targeted, case-insensitive
   searches across `addons/shopify_connector_core/` for:
   - `credential|token|secret|password|api[_-]?key` → only doc-string/manifest
     prose stating that **no** such field exists (e.g. "No credential/token/
     secret field is defined here"). **No actual field, no matches in code.**
   - `webhook` → only the `job_source` Selection **label** `('webhook',
     'Webhook')` (a classification value for *why a job was created*, not a
     webhook receiver) and the `webhook_ready` readiness **Boolean** field on
     the store (a status flag, not webhook logic), plus doc-string/manifest
     prose disclaiming webhook handling. **No webhook receiver, controller,
     or HTTP endpoint.**
   - `http\.Controller|import requests|graphql|@http\.route` → **no matches.**
   - `ir\.cron` → **no matches.**
   - `ir\.ui\.menu|ir\.actions|<menuitem|TransientModel` → **no matches.**
   - Directory search for `*views*`/`*wizard*` paths under the module →
     **none found.**

6. **File-scope validation** — confirmed the module tree is unchanged from
   what PR #88 merged (only the six model files, `security/*.csv`/`*.xml`,
   and the two `__init__.py` files exist under
   `addons/shopify_connector_core/`); no new `data/`, `views/`,
   `controllers/`, `wizard/`, or `migrations/` directories were created by
   this or any prior session.

**Not run — and not claimed:** no `odoo-bin -i shopify_connector_core`
install, no ORM shell session, no ir.model/ir.model.fields query, no database
of any kind. See [Odoo runtime availability](#odoo-runtime-availability).

## Odoo runtime availability

**No Odoo runtime exists in this environment.** Specifically, verified before
writing this document:

- `python3 -c "import odoo"` → `ModuleNotFoundError: No module named 'odoo'`.
  The Odoo Python package is not installed.
- `pip3 show odoo` → not found. `pip3 list` has no `psycopg2`/`psycopg2-binary`
  either, so there is no PostgreSQL driver available for an ORM session even
  if the Odoo package were present.
- No `odoo-bin` (or `odoo`) executable on `PATH`.
- No Dockerfile, `docker-compose*.yml`, or any container definition anywhere
  in the repository (`find` for `Docker*`/`docker-compose*` returns nothing).
- `addons/requirements.txt` exists but is **empty** — no pinned Odoo/psycopg2/
  test dependency is declared anywhere in the repo.
- No `.github/workflows/` directory and no other CI configuration file
  (`*.yml`/`*.yaml`) exists anywhere in the repository.
- No PostgreSQL server/service is available in this container.

This matches exactly what the Task 001 handoff already recorded (see
`docs/01-research/research-handoff.md`, "Task 001 — Core Module Scaffold
implemented" entry): this repository has never had a runnable Odoo instance,
test framework, or CI pipeline. Nothing changed on that front between Task
001 and this session.

**What would be needed to close this gap:** an Odoo 19 Python package (or a
full Odoo 19 source checkout on `PYTHONPATH`), `psycopg2`, a running
PostgreSQL server, and either an `odoo-bin` invocation or a test runner
configured against them — none of which this task is authorized to install or
configure (provisioning that infrastructure would itself be a scope decision
beyond "QA closure of Task 001," so it is left as an explicit recommendation,
not performed here).

## Automated tests decision

**No test files were added.** Per the task's own guardrail — "Do not create
tests if no safe Odoo test pattern exists or if they cannot be reasonably
validated. Do not invent a custom non-Odoo test framework" — the pre-change
inspection found:

- **No existing repo test convention.** There is no `tests/` directory
  anywhere in this repository (checked both `addons/shopify_connector_core`
  and the only other module, `addons/adams_base`, which is itself an empty
  scaffold with `.gitkeep` placeholders and no models). There is no prior
  Odoo `TransactionCase`/`common.py` pattern to follow.
- **No runtime to validate against.** As established above, there is no
  Odoo package, no `psycopg2`, no PostgreSQL server, and no `odoo-bin` in
  this environment. Any `odoo.tests.common.TransactionCase` subclass written
  here could be reviewed for syntax only — it could not actually be
  **run**, and a constraint/compute test that has never executed against a
  real ORM is not meaningfully verified.
- **Inventing a non-Odoo test harness is explicitly forbidden** by this
  task's instructions, and would not exercise the real Odoo constraint
  machinery (`@api.constrains`, SQL `UNIQUE` constraints, `ondelete`
  behavior) that most needs verification here — a hand-rolled mock would
  test the mock, not the model.

Writing untested, unrunnable `TransactionCase` files would create a false
sense of coverage without adding real verification, so none were added. This
mirrors the same conclusion the Task 001 handoff already reached ("a future
session should add real Odoo-runtime tests once a test framework/CI is
authorized"): that authorization still has not happened, so the conclusion is
unchanged. The gap is instead closed, to the extent possible without a
runtime, by the static checks above and the manual checklist below.

## Manual Odoo 19 validation checklist

For a reviewer with access to a live Odoo 19 + PostgreSQL instance, the
following steps close the runtime-verification gap this session could not
close directly:

1. Install `shopify_connector_core` on clean Odoo 19 database.
2. Confirm module installs without manifest/security/model errors.
3. Confirm six models appear in `ir.model`.
4. Confirm no credential/token/secret fields exist in `ir.model.fields`.
5. Create a store and verify required fields.
6. Duplicate `shop_domain` raises unique constraint.
7. Create one settings row per store.
8. Duplicate settings row raises unique constraint.
9. Create location record and duplicate `(store_id, shopify_location_gid)`
   raises unique constraint.
10. Create job with valid core values.
11. `job_source='odoo_event'` without `trigger_origin` raises
    `ValidationError`.
12. Non-`odoo_event` with `trigger_origin` raises `ValidationError`.
13. `state='blocked_manual_review'` without `manual_review_subreason` raises
    `ValidationError`.
14. Non-`blocked_manual_review` with `manual_review_subreason` raises
    `ValidationError`.
15. Two non-terminal jobs with the same operation scope collide.
16. Terminal job clears `operation_scope_key`.
17. Superseded job clears `operation_scope_key`.
18. Job log uses `ondelete='restrict'`; deleting a job with logs is blocked.
19. Auditor/operator/reviewer/admin access rights match AR-019.
20. No menus/actions/views/wizards exist.

Steps 6, 8, 9, 15–17 exercise the `_sql_constraints` and the
`_compute_operation_scope_key` supersede fix (the F1 correction already
merged in PR #88); steps 11–14 exercise the two `@api.constrains` methods on
`shopify.connector.job`; step 19 should be checked directly against the 20
rows validated by the CSV structural check in this document (§ Static checks
performed, item 4) and the four-group definitions in
`security/shopify_connector_security.xml`.

## Acceptance recommendation

**Task 001 is recommended as runtime-ready for the next implementation gate,
with the caveats below.** Every check performable without a live Odoo
instance — Python syntax, manifest structure, XML well-formedness, CSV
structural/referential integrity, and an out-of-scope-content sweep — passed
cleanly, and the module tree matches exactly what PR #88 merged (no drift).
The scaffold contains no credential, API-client, webhook, controller, cron,
or UI code, consistent with its stated purpose as a domain-agnostic core
substrate. The remaining gap is entirely a live-runtime verification gap
(constraint/compute behavior under a real ORM, actual module installability),
not a static-correctness gap — closing it requires the manual checklist above
to be executed once an Odoo 19 + PostgreSQL environment is available, which
this environment does not have and this task is not authorized to provision.

## Remaining risks

- **Live Odoo install not executed.** No `odoo-bin -i shopify_connector_core`
  run has ever occurred against this scaffold in any session to date,
  because no Odoo runtime has ever been available in this environment.
  Manifest/dependency/security-file correctness has been checked
  structurally, but only a real install proves the module loads cleanly.
- **Constraints not ORM-tested.** The two `_sql_constraints` pairs on
  `shopify.connector.store`, `.store.settings`, `.location`, and
  `.job`, and the two `@api.constrains` validators on
  `shopify.connector.job`, have been read and reasoned about but never
  executed against a live PostgreSQL database — their behavior under
  concurrent writes, cascading `ondelete='restrict'` deletes, and the
  supersede-clears-`operation_scope_key` fix (F1, already merged) remain
  unverified by execution, only by static reading and the manual checklist
  above.
- **Field-level `readonly=True` is not write-time immutability.** As already
  flagged in the Task 001 handoff, several fields marked `readonly=True` are
  intended to be immutable after first save, but Odoo's `readonly` attribute
  only affects UI/default `write()` access, not a hard ORM-level "cannot be
  changed after create" guard. A determined `write()` call (e.g. from
  trusted server-side code with `sudo()`) could still mutate them; stricter
  enforcement (e.g. an `@api.constrains` or overridden `write()` guard) would
  need its own architecture decision and is out of scope for this QA closure.
