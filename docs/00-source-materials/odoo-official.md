# Captured Source Material — Official Odoo 19 Documentation

> High-value excerpts from official Odoo 19.0 documentation
> (`odoo.com/documentation/19.0`), captured so the research survives link rot.
> **All captured 2026-06-30; all Odoo 19.0.** Each block marks **quote** vs
> **paraphrase** and cites the exact URL. These are **Tier-1 facts** (per
> `../01-research/research-methodology.md` §1). Analysis lives in
> [`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md);
> this file is evidence only. Some odoo.com pages are JS-rendered; a few excerpts
> were recovered from the official 19.0 RST source and are noted as paraphrase —
> verify verbatim against the live page if exact wording is load-bearing.

## Module structure and manifests

- **[quote]** "The manifest file … is a file called `__manifest__.py` and
  contains a single Python dictionary, where each key specifies a module
  metadatum."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html
- **[quote]** "Module `base` is always installed in any Odoo instance. But you
  still need to specify it as dependency to make sure your module is updated when
  `base` is updated."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html
- **[quote]** "`auto_install` … If True, this module will automatically be
  installed if all of its dependencies are installed. It is generally used for
  'link modules' implementing synergetic integration between two otherwise
  independent modules. For instance `sale_crm` depends on both `sale` and `crm`
  and is set to `auto_install` … If it is a list, it must contain a subset of the
  dependencies … If the list is empty, this module will always be automatically
  installed."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html
- **[quote]** "`active` (bool) Deprecated. Replaced by `auto_install`."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html
- **[paraphrase]** Data files are read sequentially, so elements must be defined
  in the right order (a model before a field on it, fields before they're added to
  a view); files in `data` should be listed in order of dependency. Data may be
  CSV or XML.
  — https://www.odoo.com/documentation/19.0/developer/tutorials/define_module_data.html

## Dependencies and modularity

- **[quote]** "`depends` (list(str)) Odoo modules which must be loaded before this
  one, either because this module uses features they create or because it alters
  resources they define. When a module is installed, all of its dependencies are
  installed before it. Likewise dependencies are loaded before a module is loaded."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html
- **[quote]** "The common approach for such use cases is to create a 'link'
  module. In our case, the module would depend on `estate` and `account` and would
  include the invoice creation logic … This way the real estate and the accounting
  modules can be installed independently. When both are installed, the link module
  provides the new feature."
  — https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/13_other_module.html

## ORM extension and inheritance

- **[quote]** "`_inherits` … implements composition-based inheritance: the new
  model exposes all the fields of the inherited models but stores none of them: the
  values themselves remain stored on the linked record."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html
- **[quote]** "When using `_inherit` but leaving out `_name`, the new model
  replaces the existing one, essentially extending it in-place… When `_inherit` is
  set to a string, then `_name` is set to the same value, unless `_name` is
  explicitly set."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html
- **[paraphrase]** `@constrains` is triggered only if the declared fields are
  included in the create or write call (so fields not present in a view won't
  trigger it during creation — an override of `create` is needed to always
  trigger); `@constrains` and `@onchange` ignore dotted (relational) field names.
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html
- **[quote]** "It is very important to always call `super()` to avoid breaking the
  flow… Make sure to always return data consistent with the parent method. For
  example, if the parent method returns a `dict()`, your override must also return
  a `dict()`."
  — https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/12_inheritance.html

## Security: access rights, record rules, field access

- **[quote]** "Each access right is associated with a model, a group (or no group
  for global access) and a set of permissions: create, read, write and unlink.
  Such access rights are usually defined in a CSV file named `ir.model.access.csv`."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html
- **[paraphrase]** The `ir.model.access.csv` columns are `id, name, model_id:id,
  group_id:id, perm_read, perm_write, perm_create, perm_unlink`.
  — https://www.odoo.com/documentation/19.0/developer/tutorials/restrict_data_access.html
- **[quote]** "Record rules are evaluated record-by-record, following access
  rights. Record rules are default-allow: if access rights grant access and no rule
  applies to the operation and model for the user, the access is granted."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html
- **[paraphrase]** Global rules intersect (both must be satisfied → adding global
  rules always restricts access); group rules unify (either can be satisfied →
  adding group rules can expand access but not beyond the global bounds); the first
  group rule added to a given global ruleset will restrict access.
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html
- **[paraphrase]** A Field's `groups` attribute (comma-separated group external
  ids) restricts the field; restricted fields are removed from requested views and
  from `fields_get()`, and explicit read/write raises an access error.
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html
- **[paraphrase]** `sudo()` creates a recordset in sudo mode that ignores all
  access rights and record rules, although hard-coded group and user checks may
  still apply; Superuser mode similarly circumvents record rules and access rights
  and must be used with extreme caution.
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html

## Scheduled actions / cron

- **[quote]** "By default, the cron is scheduled to be executed the next time the
  cron worker wakes up, but the optional 'at' argument may be given to delay the
  execution later, with a precision down to 1 minute. The method may be called with
  a datetime or an iterable of datetime."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html
- **[quote]** "If a scheduled action encounters an error or a timeout three
  consecutive times, it will skip its current execution and be considered as
  failed. If a scheduled action fails its execution five consecutive times over a
  period of at least seven days, it will be deactivated and will notify the DB
  admin."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html
- **[quote]** "When running a scheduled action, it's recommended that you try to
  batch the progress in order to avoid blocking a worker for a long period of time
  and possibly run into timeout exceptions … Work is committed by the framework
  after each batch … Do not reschedule yourself the job."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html
- **[paraphrase]** Timing-condition automation rules rely on the scheduled action
  "Automation Rules: check and execute scheduled action" (default every 4 hours),
  so `base_automation` timing triggers are driven by `ir.cron`.
  — https://www.odoo.com/documentation/19.0/applications/studio/automated_actions.html

## Queue / async work

- **[paraphrase]** The only background/deferred-execution framework documented in
  the Odoo 19 developer reference is Scheduled Actions (`ir.cron`); `_trigger()`
  schedules a job to run the next time the cron worker wakes up, with minute-level
  precision — poll-based, not an event-driven job queue.
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html
- **[quote]** "`--max-cron-threads`: number of workers dedicated to cron jobs.
  Defaults to 2. The workers are threads in multi-threading mode and processes in
  multi-processing mode. For multi-processing mode, this is in addition to the HTTP
  worker processes."
  — https://www.odoo.com/documentation/19.0/developer/reference/cli.html
- **[paraphrase]** The `queue_job` async job queue (`with_delay()`, Jobrunner, job
  dependency graphs, automatic re-queuing) is distributed on the Apps Store as an
  OCA (community) module — it is **not** part of official Odoo or its
  documentation. — https://apps.odoo.com/apps/modules/19.0/queue_job (community
  listing, for contrast only)

## External IDs and mapping

- **[quote]** "string identifier stored in `ir.model.data`, can be used to refer
  to a record regardless of its database identifier during data imports or
  export/import roundtrips. … in the form `module.id` (e.g. `account.invoice_graph`)."
  — https://www.odoo.com/documentation/19.0/developer/glossary.html
- **[quote]** "Because we don't want a column `xml_id` in every single SQL table of
  the database, we need a mechanism to store it. This is done with the
  `ir.model.data` model. It contains the name of the record (the `xml_id`) along
  with the module in which it is defined, the model defining it, and the id of it."
  — https://www.odoo.com/documentation/19.0/developer/tutorials/define_module_data.html
- **[quote]** "The records created with the `noupdate` flag won't be updated when
  upgrading the module that created them, but it will be created if it didn't exist
  yet."
  — https://www.odoo.com/documentation/19.0/developer/tutorials/define_module_data.html

## Performance

- **[quote]** "Odoo maintains a cache for the fields of the records, so that not
  every field access issues a database request, which would be terrible for
  performance."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html
- **[paraphrase]** Don't call a method that runs SQL queries while looping over a
  recordset (it runs per record); the documented fix replaces a per-record
  `search_count` with a single `_read_group(domain, ['related_id'], ['__count'])`
  over `self.ids`.
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html
- **[quote]** "Be careful not to index every field as indexes consume space and
  impact on performance when executing one of INSERT, UPDATE, and DELETE."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html

## Testing

- **[paraphrase]** `TransactionCase`: all test methods run in a single
  transaction, each method in a savepoint sub-transaction, and the cursor is closed
  without committing; shared setup goes in `setUpClass`.
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html
- **[quote]** "`post_install` means that the test will be executed after all the
  modules are installed. This is what you want for HttpCase tests most of the time."
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html
- **[paraphrase]** `--test-tags` selects/filters tests on the command line, implies
  `--test-enable`, and defaults to `+standard`; a filter spec has the format
  `[-][tag][/module][:class][.method]`.
  — https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html

## Upgrade / migration

- **[quote]** "The structure of an upgrade script path is
  `$module/migrations/$version/{pre,post,end}-*.py`, where `$module` is the module
  the script will run for, `$version` is the full version of the module (including
  Odoo's major version and the module's minor version) and `{pre|post|end}-*.py` is
  the file that needs to be executed."
  — https://www.odoo.com/documentation/19.0/developer/reference/upgrades/upgrade_scripts.html
- **[paraphrase]** The upgrade process has three phases per version per module:
  pre- (before the module loads), post- (after the module and its dependencies load
  and update), end- (after all modules for that version); within a phase, files run
  in lexical order.
  — https://www.odoo.com/documentation/19.0/developer/reference/upgrades/upgrade_scripts.html
- **[paraphrase]** A database with custom modules cannot be upgraded until a
  version of those custom modules is available for the target Odoo version; the
  Upgrade Team handles standard modules, while customers own their custom-code
  migration. Standard support is 3 years per major version, with paid extended
  support beyond.
  — https://www.odoo.com/documentation/19.0/administration/upgrade.html;
  https://www.odoo.com/documentation/19.0/administration/standard_extended_support.html

## Logging / CLI

- **[quote]** "By default, Odoo displays all logging of level INFO, WARNING and
  ERROR. All logs independently of the level are output on stderr."
  — https://www.odoo.com/documentation/19.0/developer/reference/cli.html
- **[quote]** "`--log-db <dbname>`: logs to the `ir.logging` model (`ir_logging`
  table) of the specified database. The database can be the name of a database in
  the current PostgreSQL, or a PostgreSQL URI for e.g. log aggregation."
  — https://www.odoo.com/documentation/19.0/developer/reference/cli.html

## Deployment / Odoo.sh

- **[paraphrase]** The multi-processing server is the production server (not
  subject to the GIL); it is opt-in via `--workers` set to a non-null integer, and
  in multi-processing mode extra cron worker processes are spawned in addition to
  HTTP workers.
  — https://www.odoo.com/documentation/19.0/administration/on_premise/deploy.html
- **[paraphrase]** Staging branches create neutralized duplicates of the
  production database: emails are not sent but intercepted by a mail catcher, and
  scheduled actions are not triggered as long as the database is not in use.
  — https://www.odoo.com/documentation/19.0/administration/odoo_sh/getting_started/branches.html
- **[paraphrase]** The first build of a production branch creates a database from
  scratch; subsequent pushes create builds that attempt to load the existing
  database on a server running the new revision, and the build runs production only
  if it is successful or almost successful.
  — https://www.odoo.com/documentation/19.0/administration/odoo_sh/getting_started/builds.html
