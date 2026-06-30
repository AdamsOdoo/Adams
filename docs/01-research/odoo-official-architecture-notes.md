# Odoo Official Architecture Notes

> Tier-1 technical baseline for the Odoo side of the Odoo 19 ↔ Shopify Connector.
> **Every factual claim is sourced from official Odoo 19.0 documentation**
> (`odoo.com/documentation/19.0`) with its exact URL. Where official docs do not
> cover a needed fact, it is logged as an **Open question / requires codebase
> verification later** — **not assumed**. This document makes **no architecture
> decisions**; the "Architecture constraints implied by Odoo facts" section is
> **inference**, and module-boundary/queue choices remain **gated** pending
> ChatGPT review (`CLAUDE.md` §4–§5, §9).

## Status

- **Sprint:** Research Sprint B (RB-06.1). **Phase:** research only; no-code gate
  applies.
- **Classification key (per `CLAUDE.md` §8):** **Fact** = stated on an official
  Odoo 19.0 page; **Inference** = our deduction; **Open question** = not in
  official 19.0 docs / needs codebase verification. No **Decisions** here.
- **Version:** all facts are for **Odoo 19.0** unless noted. Several ORM/manifest/
  security statements are long-stable across Odoo versions but were read from the
  **/19.0/** pages.
- **Confidence note:** some odoo.com pages are JavaScript-rendered and the proxy
  fetcher sometimes returned only navigation; in those cases the agents recovered
  the body via raw HTML / official 19.0 RST source and flagged it. The
  highest-stakes pages (manifest keys, security model) were re-read in an
  **independent verification pass**.

## Source hierarchy and access date

- **Tier 1 (used here):** official Odoo 19.0 documentation — the **Developer →
  Reference (backend)** pages, the **Server framework 101** tutorials, and the
  **Administration** (deploy / Odoo.sh / upgrade) pages.
- **Access date for all claims:** **2026-06-30.**
- **Out of scope as Tier 1:** the OCA `queue_job` module and any Apps-Store
  module are **community**, not official Odoo — they are referenced only to mark
  what is *not* in core (see "Queue or async work").

---

## Facts from official Odoo 19 documentation

### Module structure and manifests

- **Fact —** An Odoo module is a directory (Python package) that must contain at
  least **`__manifest__.py`** and **`__init__.py`**; `__init__.py` imports the
  module's Python files and may start empty.
  (https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/01_architecture.html)
- **Fact —** The manifest is a single Python dict of metadata. **`name` is the
  only required key.** Documented keys include: `name`, `version` (semantic
  versioning), `description`, `author`, `website`, `license` (default **LGPL-3**;
  values incl. GPL-2/3, AGPL-3, LGPL-3, OEEL-1, **OPL-1**, Other proprietary),
  `category` (default *Uncategorized*; freeform; `/`-separated hierarchy),
  `depends`, `data`, `demo`, `auto_install` (bool **or list**, default False),
  `external_dependencies` (`{'python': [...], 'bin': [...]}`), `application`
  (default False), `assets`, `installable` (default True), `maintainer`,
  `{pre_init,post_init,uninstall}_hook`, `sequence` (default 100), and `active`
  (**deprecated**, replaced by `auto_install`).
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html)
- **Fact —** **`data` files are loaded sequentially** in listed order, so
  elements must be ordered by dependency (a model before its fields, fields before
  views). Data may be **CSV** (simple/long lists) or **XML** (more flexible),
  listed together in `data`. `demo` data loads only in demo mode and must not be
  required for the module to function.
  (https://www.odoo.com/documentation/19.0/developer/tutorials/define_module_data.html)
- **Fact —** Conventional module layout uses subdirectories: `models/`, `views/`,
  `security/` (e.g. `ir.model.access.csv`, `<module>_groups.xml`,
  `<model>_security.xml`), `data/`, `demo/`, `controllers/`, `static/`; none of
  these elements are mandatory (a module may add only data, or only models).
  (https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/01_architecture.html)

### Dependencies and modularity

- **Fact —** **`depends`** lists modules that must be loaded before this one
  (because it uses or alters their resources); installing a module installs all
  dependencies first. **`base` is always installed** but should still be declared
  so the module updates when `base` updates.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html)
- **Fact —** **`auto_install`** makes a module install automatically once its
  dependencies are present; it is used for **"link modules"** that integrate two
  otherwise-independent modules. The canonical example is **`sale_crm`** (depends
  on `sale` + `crm`, `auto_install`). A **list** value auto-installs once a named
  subset of dependencies is present (and installs the rest); an **empty list**
  always auto-installs.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html)
- **Fact —** Odoo's docs teach modularity explicitly: to add an optional
  cross-app feature (e.g. invoicing from a real-estate module), create a separate
  **link module** (`estate_account`) that **depends on both** modules and holds
  the integration logic, so each app stays independently installable and the
  feature activates only when both are installed.
  (https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/13_other_module.html)
- **Inference —** A connector extending business apps (`sale`, `stock`,
  `product`, `account`, `delivery`) does so by declaring them in `depends`; the
  specific extend-targets beyond `account`/`sale`/`crm` are illustrated by example
  rather than enumerated on one official page (see Open questions).

### ORM extension and model integration

- **Fact —** Models inherit one of three base classes: **`Model`** (DB-persisted),
  **`TransientModel`** (temporary, auto-vacuumed; default idle lifetime
  `_transient_max_hours = 1.0`), **`AbstractModel`** (no table). Key attributes:
  `_name`, `_description`, `_inherit`, `_inherits`, `_order` (default `id`),
  `_rec_name` (default `name`), `_auto` (default True → table created).
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html)
- **Fact —** **Three extension mechanisms:** (1) **classical** — `_inherit` **and**
  `_name` set → a *new* model based on the existing one; (2) **extension
  (in-place)** — `_inherit` **without** `_name` → replaces/extends the existing
  model (add fields/methods, override, reconfigure) — *"by far the most used"*;
  (3) **delegation** — `_inherits = {'parent.model': 'fk_field'}` → composition
  ("has-a"), exposing the parent's **fields but not methods**. Official docs warn
  `_inherits` is *"more or less implemented, avoid it if you can"* and chained
  `_inherits` is *"essentially not implemented."*
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html;
  https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/12_inheritance.html)
- **Fact —** To add a field to an existing model from another module: define a
  class with **`_inherit = "existing.model"` and no new `_name`**, then declare
  the field (conventionally one inherited model per Python file). Overrides must
  **call `super()`** and **return a value consistent with the parent** (e.g. a
  dict if the parent returns a dict).
  (https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/12_inheritance.html)
- **Fact —** Decorators: **`@api.depends`** (compute dependencies; dotted paths
  allowed), **`@api.constrains`** (validation; **simple field names only — dotted
  ignored**; fires **only if the declared fields are in the create/write call**),
  **`@api.onchange`** (form-level; simple names only), **`@api.model`**,
  **`@api.model_create_multi`** (batch create taking a list of dicts),
  **`@api.ondelete(at_uninstall=False)`** (preferred over overriding `unlink` for
  uninstall safety), `@api.autovacuum`, `@api.depends_context`, `@api.private`.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html)
- **Inference —** For batch-safe create overrides the canonical decorator is
  **`@api.model_create_multi`** (list of dicts); the Chapter-12 tutorial's
  `@api.model def create(self, vals)` example is single-record — integration code
  should prefer `model_create_multi`. *(The two pages differ; the precise
  current-recommended create signature is an open question below.)*

### Security: access rights, record rules, field access

- **Fact —** Two data-driven mechanisms, both attached to **groups**: **Access
  Rights** (`ir.model.access`) grant **model-level** CRUD; **Record Rules**
  (`ir.rule`) impose **row-level** conditions. *"If no access rights match … the
  user doesn't have access."* Access rights are **additive** (union across a
  user's groups).
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)
- **Fact —** Access rights are usually defined in **`ir.model.access.csv`** with
  columns **`id, name, model_id:id, group_id:id, perm_read, perm_write,
  perm_create, perm_unlink`**. The `perm_*` flags **grant** the operation when set
  and are **all unset by default**; an **empty `group_id` = global access** (all
  users).
  (https://www.odoo.com/documentation/19.0/developer/tutorials/restrict_data_access.html;
  https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)
- **Fact —** **Record rules** are **evaluated record-by-record, after access
  rights**, and are **default-allow** (if access rights grant and no rule applies,
  access is granted). An `ir.rule` has a model, `groups`, a **`domain_force`**
  predicate, and per-operation flags. **In `ir.rule`, the `perm_*` flags mean
  *which operation the rule applies to*** — opposite semantics from
  `ir.model.access`.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)
- **Fact —** **Global rules intersect** (all must pass → always restrict
  further); **group rules unify** (any can pass → can widen, but not beyond global
  bounds). *"The first group rule added to a given global ruleset will restrict
  access."* Creating multiple global rules is risky (non-overlapping rulesets can
  remove all access).
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)
- **Fact —** **Field-level access:** a Field's **`groups`** attribute
  (comma-separated group XML-ids) restricts the column — restricted fields are
  removed from views and `fields_get()`, and explicit read/write raises an access
  error.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html;
  https://www.odoo.com/documentation/19.0/developer/tutorials/restrict_data_access.html)
- **Fact —** **Superuser mode / `sudo()` bypass both access rights and record
  rules** (though hard-coded group/user checks still apply) and must be used with
  extreme caution. Using the raw cursor (`self.env.cr.execute`) instead of the
  ORM bypasses ORM features **including access rights** and is discouraged.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)

### Scheduled actions / cron

- **Fact —** Scheduled actions are backed by **`ir.cron`**. By default a cron runs
  **the next time the cron worker wakes up**; an optional **`at`** argument delays
  execution with **precision down to 1 minute**. Programmatic triggering uses
  **`ir.cron._trigger(at=None)`** (runs soon, independent of `nextcall`); cron
  functions must **not** be called directly.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html)
- **Fact —** **Failure handling:** if a scheduled action errors/times out **three
  consecutive times** it skips the current run and is considered failed; if it
  **fails five consecutive times over ≥ 7 days** it is **deactivated and the DB
  admin is notified**. A database-level hard limit can kill the cron process.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html)
- **Fact —** Cron functions should **batch** (each call a single batch, a few
  seconds); the framework **commits after each batch** and re-calls the function
  until done — **do not reschedule yourself**. **`ir.cron._commit_progress(...)`**
  commits/logs progress and returns the remaining time (0 → return ASAP).
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html)
- **Fact —** In the UI (developer mode → Settings ▸ Technical ▸ Scheduled
  Actions), a record exposes **Execute Every** (interval), **Next Execution
  Date**, **Number of Calls**, **Active**, and **Run Manually**.
  (https://www.odoo.com/documentation/19.0/applications/sales/subscriptions/scheduled_actions.html)
- **Fact —** **Automation rules** (`base_automation` / Studio) react to triggers
  (Values Updated, Email Events, Timing Conditions, Custom, External/webhook).
  **Time-based triggers are driven by a scheduled action** ("Automation Rules:
  check and execute scheduled action", **default every 4 hours**) — so
  `base_automation` is an event/condition layer **on top of `ir.cron`**.
  (https://www.odoo.com/documentation/19.0/applications/studio/automated_actions.html)

### Queue or async work

> **This is the key "do not assume" topic.** Conclusion: Odoo 19 core's only
> documented background/deferred-execution primitive is **`ir.cron`**.

- **Fact —** The **only** background/deferred-execution framework in the official
  Odoo 19 developer reference is **Scheduled Actions (`ir.cron`)**. `ir.cron` with
  `_trigger()` is **poll-based** (runs when a cron worker next wakes; minute-level
  precision), not an event-driven message/job queue.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html)
- **Fact —** Cron throughput is bounded by **`--max-cron-threads` (default 2)** —
  threads in multi-threading mode, separate processes in multi-processing mode.
  In WSGI deployments crons are **not** handled by the WSGI server; a separate
  cron-only Odoo process must run (`--no-http`).
  (https://www.odoo.com/documentation/19.0/developer/reference/cli.html;
  https://www.odoo.com/documentation/19.0/administration/on_premise/deploy.html)
- **Open question —** Odoo 19 **does not appear to ship an official, built-in,
  general-purpose async job queue** (named jobs, priorities, retries/backoff,
  `with_delay()`-style dispatch, dependency graphs). **No such framework is
  documented** in the official Odoo 19 docs — only `ir.cron`. (Absence of
  documentation is not absolute proof none exists internally; treat a true job
  queue as **not available in core** until verified against the 19.0 codebase.)
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html)
- **Fact (community, for contrast) —** The widely-used async job queue
  (`with_delay()`, Jobrunner, job dependency graphs, automatic re-queuing) is the
  **OCA `queue_job`** module — **community-maintained, NOT part of official Odoo
  or its documentation** (it requires its own Jobrunner deployment).
  (https://apps.odoo.com/apps/modules/19.0/queue_job — Apps Store listing, not
  official docs)

### External IDs and mapping

- **Fact —** An **external identifier (XML ID)** is a string in **`ir.model.data`**
  that refers to a record **independently of its database id**, in the form
  **`module.name`** (the `module.` prefix may be omitted within a module).
  `ir.model.data` stores the name (xml_id), the module, the model, and the record
  id.
  (https://www.odoo.com/documentation/19.0/developer/glossary.html;
  https://www.odoo.com/documentation/19.0/developer/tutorials/define_module_data.html)
- **Fact —** In data files, `<record>`'s `id` is the external id; `<field
  ref="...">` and the eval `ref(...)` helper resolve external ids; CSV files use
  an `id` column and a **`field:id`** suffix (e.g. `country_id:id`) to reference
  another record by external id. Data files run **sequentially** — references must
  resolve to previously-loaded ids.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/data.html)
- **Fact —** **`noupdate`** (`<data noupdate="1">` or the record flag) means the
  record **won't be overwritten on module update**, but **will still be created if
  missing** (`forcecreate` defaults to True). `odoo-bin -i module` reloads data,
  bypassing `noupdate`. **User-created data can always be deleted by the user**, so
  module code must be defensive.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/data.html;
  https://www.odoo.com/documentation/19.0/developer/tutorials/define_module_data.html)
- **Inference —** Because an external id maps (via `ir.model.data`) to exactly one
  `(model, record)`, a stable external id is a natural **connector binding key**
  for idempotent upsert/dedup (the same upstream Shopify record always resolves to
  the same Odoo record). This is **our inference**, not Odoo-prescribed connector
  guidance, and must handle the external id resolving to a deleted record. *(A
  dedicated mapping/binding model vs reusing `ir.model.data` is an architecture
  question, not decided here.)*

### Performance guidance

- **Fact —** Odoo maintains a **record-field cache** and **prefetches**: reading a
  field on one record reads it for the whole prefetched recordset (usually the set
  being iterated). The documented example: looping 1000 partners reading two
  fields is **1 query with prefetching vs 2000 without**; reading a relational
  field prefetches the related records too.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html)
- **Fact —** **Do not run SQL-issuing methods inside a loop over a recordset**
  (the **N+1** anti-pattern). The documented fix replaces a per-record
  `search_count` with **one `_read_group(domain, ['related_id'], ['__count'])`**
  over `self.ids`. **Batch creation:** accumulate dicts and call **`create()`
  once** with the list rather than in a loop.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html)
- **Fact —** **Indexes** via **`index=True`** accelerate search; values are
  `btree`/True (default for many2one), `btree_not_null` (mostly-NULL columns),
  `trigram` (full-text), None/False (no index). **Don't index every field** —
  indexes cost space and slow INSERT/UPDATE/DELETE. Cache **flush/invalidate**
  should be **as specific as possible**. Odoo ships an integrated **profiler**.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html;
  https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html)

### Testing guidance

- **Fact —** **`TransactionCase`**: all methods run in one transaction, **each
  method in a savepoint sub-transaction**, cursor **closed without committing**.
  Shared setup goes in **`setUpClass`**. (`SingleTransactionCase` runs all methods
  in one transaction without per-method rollback — referenced but exact 19.0
  wording not captured.)
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html)
- **Fact —** Tests are **tagged**; default tags are **`standard` + `at_install`**.
  **`@tagged(...)`** adds/removes tags (a leading `-` removes; tags are inherited).
  **`at_install`** runs right after the module installs; **`post_install`** runs
  after **all** modules install (*"what you want for HttpCase tests most of the
  time"*).
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html)
- **Fact —** **`HttpCase`** runs web tests; **`browser_js`** runs JS tests in
  **headless Chrome**; **tours** (integration UI tests) run via **`start_tour`**.
  **`--test-tags`** selects tests (implies `--test-enable`, defaults to
  `+standard`) with the spec `[-][tag][/module][:class][.method]`. Tests live in a
  module's **`tests/`** dir (with `__init__.py`), conventionally `test_*.py`.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html;
  https://www.odoo.com/documentation/19.0/developer/tutorials/unit_tests.html)

### Upgrade and migration considerations

- **Fact —** Odoo distinguishes **updating** (latest revision/bugfixes, no data
  change) from **upgrading** (moving the DB to a newer major version).
  (https://www.odoo.com/documentation/19.0/administration/upgrade.html)
- **Fact —** Module upgrade scripts live at **`$module/migrations/$version/
  {pre,post,end}-*.py`** (since Odoo 13 the folder may also be **`upgrades/`**).
  Each defines **`migrate(cr, version)`**. **Phases:** `pre-` (before the module
  loads — ORM **not** available, use raw SQL), `post-` (after the module + deps
  load — ORM available via `from odoo.upgrade import util; env = util.env(cr)`),
  `end-` (after all modules for that version). Within a phase, files run in
  **lexical order**. Scripts run **only on update** (the `$version` dir must be
  higher than the installed version).
  (https://www.odoo.com/documentation/19.0/developer/reference/upgrades/upgrade_scripts.html;
  https://www.odoo.com/documentation/19.0/developer/reference/upgrades/upgrade_utils.html)
- **Fact —** A DB with **custom modules cannot be upgraded** until those modules
  have a version for the target Odoo version; the Upgrade Team migrates **standard**
  module data, while **customers own their custom-code migration**. Odoo provides
  **standard support for 3 years** per major version (helpdesk, bugfix, security),
  with paid **extended support** beyond that and a 6-month grace period to use the
  last unsupported version as an upgrade target.
  (https://www.odoo.com/documentation/19.0/administration/upgrade.html;
  https://www.odoo.com/documentation/19.0/administration/standard_extended_support.html)

### Logging and observability

- **Fact —** Odoo code logs via the **standard Python `logging`** module:
  `import logging; _logger = logging.getLogger(__name__)`. By default Odoo logs
  **INFO/WARNING/ERROR to stderr**.
  (https://www.odoo.com/documentation/19.0/developer/reference/upgrades/upgrade_scripts.html;
  https://www.odoo.com/documentation/19.0/developer/reference/cli.html)
- **Fact —** Logging is redirected/tuned by CLI: **`--logfile`**, **`--syslog`**,
  **`--log-db <db>`** (writes to the **`ir.logging`** model / `ir_logging` table),
  **`--log-handler {LOGGER}:{LEVEL}`** (e.g. `odoo.models:DEBUG`, repeatable),
  **`--log-level`**, `--log-web`, `--log-sql`. On conflict, `--log-handler` wins
  over `--log-level`.
  (https://www.odoo.com/documentation/19.0/developer/reference/cli.html)
- **Open question —** Odoo 19 core appears to have **no built-in metrics/telemetry
  endpoint** (e.g. Prometheus `/metrics`, OpenTelemetry). The official 19.0 docs
  cover logging and a profiler but no built-in observability stack; metrics
  exporters exist only as **third-party Apps Store modules**. (Absence of
  documentation; confirm against the codebase/hosting docs if needed.)
  (https://www.odoo.com/documentation/19.0/developer/reference/cli.html)

### Odoo.sh / deployment notes

- **Fact —** Odoo's **default server is multi-threaded** (`--workers` 0/omitted;
  dev/demo/Windows, limited by the GIL). The **multi-processing server**
  (production; `--workers` non-null, recommended `--workers=-1` on Linux) avoids
  the GIL and spawns separate HTTP and **cron** worker processes
  (**`--max-cron-threads`**, default 2). Rule of thumb: `(#CPU * 2) + 1` workers.
  (https://www.odoo.com/documentation/19.0/administration/on_premise/deploy.html)
- **Fact —** Per-request limits recycle/kill workers: **`--limit-time-cpu`**,
  **`--limit-time-real`** (wall-clock), **`--limit-memory-soft`** (recycle after
  request), **`--limit-memory-hard`** (kill immediately). A **gevent** worker
  handles websockets on **`--gevent-port`** (default 8072); behind a proxy, run
  with **`--proxy-mode`** and route `/websocket/` to the gevent worker.
  (https://www.odoo.com/documentation/19.0/administration/on_premise/deploy.html)
- **Fact —** **Odoo.sh** has three branch stages — **production** (only one),
  **staging**, **development**. Pushing to production restarts the server and
  builds a revision that must **load the existing production DB** to go live.
  **Staging** builds are **neutralized duplicates** of production data:
  **scheduled actions (crons) are disabled** and outgoing mail is intercepted by a
  mail catcher.
  (https://www.odoo.com/documentation/19.0/administration/odoo_sh/getting_started/branches.html;
  https://www.odoo.com/documentation/19.0/administration/odoo_sh/getting_started/builds.html)

---

## Architecture constraints implied by Odoo facts

> **Inferences**, not decisions. They seed architecture-review questions
> (`../05-qa/architecture-review-log.md`); none chooses a design.

- **Inference —** The connector should be a **modular addon family** (link
  modules over a giant module): isolate connector logic from `adams_base`/customer
  code, extend `sale`/`stock`/`product`/`account`/`delivery` via `depends` +
  in-place `_inherit`, and use `auto_install` link modules for optional glue —
  consistent with Odoo's documented modularity pattern (`CLAUDE.md` §9). *(Exact
  boundaries remain undecided — RB-14.)*
- **Inference —** Add connector fields/behaviour to existing models with **in-place
  `_inherit` (no new `_name`)**; **avoid `_inherits` delegation** (official docs
  discourage it). Override `create` with **`@api.model_create_multi`** and guard
  deletion with **`@api.ondelete`**, always calling `super()`.
- **Inference —** With **no official job queue in core**, background sync on stock
  Odoo 19 must be built on **`ir.cron`** (batched, idempotent, `_commit_progress`,
  `_trigger` for near-term dispatch). This is **poll-based and minute-precision**,
  bounded by `--max-cron-threads` (default 2) — not event-driven. Whether to adopt
  the community **OCA `queue_job`** to get true queueing is an **explicit
  architecture/dependency question**, not a default (it adds a Jobrunner and a
  non-core dependency).
- **Inference —** Cron's coarse failure model (auto-deactivate after 5 failures /
  ≥7 days) means the connector must implement **its own per-record retry/backoff
  and error isolation** (e.g. savepoints) rather than rely on cron-level retries.
- **Inference —** **External IDs / `ir.model.data`** give an idempotent,
  db-id-independent **binding key** for dedup, but a dedicated mapping/binding
  model may be warranted; either way the design must handle users deleting bound
  records.
- **Inference —** Performance discipline is mandatory at sync scale: **batch
  reads/writes**, use **`_read_group`** instead of per-record queries, **bulk
  `create`**, and **index** mapping/lookup fields (selectively) — to avoid N+1
  across large catalogs/orders.
- **Inference —** **Long syncs must not run in a single HTTP request** (worker
  time/memory limits recycle/kill workers mid-request); they should be **chunked
  and cron-driven**. On **Odoo.sh staging/development, crons are disabled**, so
  cron-driven sync **won't auto-run** in non-production environments — test plans
  must trigger them manually.
- **Inference —** **Security must be explicit:** ship `ir.model.access.csv` (deny
  by default — unset perms deny), scope connector config/credentials behind
  groups, use **record rules** for multi-store/company isolation (mind global=AND
  / group=OR semantics), and treat **`sudo()` as a deliberate, audited bypass**.
- **Inference —** **Test for sync correctness:** `TransactionCase` for ORM/mapping
  logic and `HttpCase`/tours for webhook controllers and config UX; tag webhook/UI
  tests `post_install`.
- **Inference —** **Custom modules gate the whole DB upgrade**, so connector
  modules need maintained per-version **`migrations/`** scripts and clean
  installability to keep customers upgradeable.

## Open questions requiring codebase verification later

1. **Job queue:** does Odoo 19 (Community/Enterprise) ship any official internal
   async job/queue/message-bus beyond `ir.cron`? (Not in official docs — verify
   against the 19.0 codebase before assuming none.)
2. **`ir.cron` field schema/defaults** (`interval_number`, `interval_type`,
   `numbercall`, `nextcall`, `priority`, `doall`, `user_id`, whether Python `code`
   lives on `ir.cron` or a linked `ir.actions.server`) — UI labels documented,
   field-level schema not captured verbatim from 19.0 prose.
3. **`ir.model.data` column schema** (`name`, `module`, `model`, `res_id`,
   `noupdate`) and whether `(module, name)` is a DB uniqueness constraint — not
   stated verbatim; relevant to a binding/dedup design.
4. **Manifest defaults** (`installable`, `application`, `auto_install`) and the
   exact `assets` syntax — not all captured verbatim from the 19.0 manifest page.
5. **Recommended `create` override signature** in 19.0 (`@api.model` single vs
   `@api.model_create_multi`) — the two official pages differ.
6. **`read_group` deprecation** in favour of `_read_group` — only `_read_group`
   appears in 19.0 examples; an explicit deprecation statement was not found.
7. **Per-stage Odoo.sh resource quotas** (HTTP/cron worker counts, CPU/RAM/time
   limits, max build duration) — not published on the 19.0 pages; deploy.html
   sizing is for self-hosted.
8. **`ir.logging` schema and retention** when using `--log-db`, and any built-in
   health/metrics endpoint — not documented.

## Risks for future architecture

- **Treating `ir.cron` as a job queue** is a design trap: no named jobs,
  priorities, retry/backoff, or dependency graphs, and it auto-deactivates after
  repeated failures.
- **Assuming OCA `queue_job` is "standard Odoo"** is a material error — it is a
  community module with its own deployment (Jobrunner) and no official support.
- **`_inherits` delegation** carries a documented stability warning ("avoid it if
  you can"; chained delegation "essentially not implemented").
- **`productSet`-style "set the whole state" thinking on the Odoo side** and
  `noupdate` semantics can cause unexpected create/overwrite; data idempotency
  must be designed, not assumed.
- **Cron disabled on Odoo.sh non-prod** means a sync can look "broken" in
  staging/dev when crons simply aren't firing — a testing footgun.
- **Doc-rendering caveat:** some 19.0 pages are JS-rendered; a few facts were
  recovered from 19.0 RST source — re-verify load-bearing exact wording against the
  live page before implementation.

## Research gaps

- Exact **method signatures** (`search_read`, `_read_group`, `browse`, `read`),
  `ir.cron`/`ir.model.data`/`ir.logging` **model schemas**, and verbatim
  manifest-default values were listed by name but not all captured field-by-field
  — confirm via the live reference or the 19.0 source at implementation time.
- **18.0 → 19.0 breaking-change list** is not enumerated on the upgrade pages;
  custom-module compatibility surfaces during the test-upgrade phase.
- **OCA modules** relevant to connectors (`queue_job`, `connector`,
  `connector_extension`) are out of this Tier-1 sprint and need a separate,
  clearly-labelled community-source evaluation (not as official facts).

## Sources

All accessed **2026-06-30**, all `odoo.com/documentation/19.0` (Tier 1):

- Modules/manifest: `/developer/reference/backend/module.html`,
  `/developer/tutorials/define_module_data.html`,
  `/developer/tutorials/server_framework_101/01_architecture.html`,
  `/…/13_other_module.html`
- ORM/inheritance: `/developer/reference/backend/orm.html`,
  `/developer/tutorials/server_framework_101/12_inheritance.html`
- Security: `/developer/reference/backend/security.html`,
  `/developer/tutorials/restrict_data_access.html`
- Cron/automation: `/developer/reference/backend/actions.html`,
  `/applications/sales/subscriptions/scheduled_actions.html`,
  `/applications/studio/automated_actions.html`
- External IDs/data: `/developer/reference/backend/data.html`,
  `/developer/glossary.html`
- Performance: `/developer/reference/backend/performance.html`,
  `/developer/reference/backend/orm.html`
- Testing: `/developer/reference/backend/testing.html`,
  `/developer/tutorials/unit_tests.html`
- Upgrade: `/developer/reference/upgrades/upgrade_scripts.html`,
  `/…/upgrade_utils.html`, `/administration/upgrade.html`,
  `/administration/standard_extended_support.html`,
  `/administration/on_premise/update.html`
- Logging/CLI/deploy: `/developer/reference/cli.html`,
  `/administration/on_premise/deploy.html`,
  `/administration/odoo_sh/getting_started/branches.html`, `/…/builds.html`,
  `/administration/odoo_sh/advanced/frequent_technical_questions.html`
- Community reference (NOT official; for contrast only):
  `apps.odoo.com/apps/modules/19.0/queue_job`

Captured excerpts: [`../00-source-materials/odoo-official.md`](../00-source-materials/odoo-official.md).
