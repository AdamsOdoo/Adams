# Testing

## Plan the tests

Before coding an M or L change, give each acceptance criterion the cheapest kind of test that proves it:

| What the criterion is about | Test | Cost |
|---|---|---|
| Rules, computed values, figures, states, access, multi-company | Python `TransactionCase` (most criteria) | fast; one per criterion, plus a denied-access case when access matters |
| Behaviour of an Owl component (what it shows for given data, what a click calls) | JavaScript unit test (HOOT) | fast |
| A user flow across screens that must keep working | one tour per main flow, in an `HttpCase` | slow (a browser); L changes, or M when the flow is the point |
| Stored data after an update of a deployed module | `oh_upgrade` test with `--upgrade-from` | medium; only when stored data changes |
| Layout, spacing, colours, right-to-left, wording | `oh shot` in English and Arabic, then open the images | not a test; once per milestone |

Budget: S updates or adds 1 to 3 tests. M has one test per criterion plus the denied-access case. L has the M set, at most one tour per main flow and the upgrade test. If you need more, write the reason in the test plan.

Don't write tests that assert CSS classes chosen for styling, positions, sizes, colours, pixel comparisons or exact label text: they break on every design change and rarely catch a defect. Assert the data and the behaviour instead (the value, the domain of the action a click opens, the error raised).

Run order: `oh check` after edits (it also runs by itself); one test with `--tags` while iterating; the module with `--require` once per milestone (an S change: only the affected test, no dependents); `--with-dependents` when other project modules build on the changed one; `--upgrade-from` and, for L, `--all` once per delivery, started together in the merge step; an Odoo.sh build at most once per milestone, or when `oh test` says **blocked**.

## Static checks: `oh check`

`oh check [module ...|file ...]` takes seconds and needs no database: Python syntax, XML well-formedness, manifest data files that exist, access CSV columns, test files imported by `tests/__init__.py`, `.po` syntax, and the Odoo 19 forms that fail at install (`<tree>`, `attrs`, `states`, `_sql_constraints`). Without arguments it checks the modules changed against the base branch. Deprecated forms (`name_get`, `check_access_rights`, `type="json"`, `%` on a translated string), missing `author`/`license`, models without access rows and dependencies missing locally are warnings: reported, not failing (the Claude Code edit hook shows them without blocking). `oh test` runs the same checks first and fails before Odoo starts when one fails (`--no-check` runs Odoo anyway); the Claude Code PostToolUse hook runs them on every edited file.

On module targets `oh check` also runs pylint-odoo (a curated list: SQL injection, `cr.commit()`, missing `super` in `create`/`write`/`unlink`, `raise` in `unlink`, `write` in a compute, `default=self._x`, a `tests` folder imported by the module, removed or renamed APIs, `print`, and every way a term escapes translation: `%`, `.format` or an f-string inside `_()`, a variable in the term, an untranslated `UserError`). They are printed as `lint:` lines and are advice, never a failure: fix the ones that are real, say in the feature notes why the rest stay (an f-string SQL statement built from constants, for example). The lint runs only on `oh check <module>` (seconds; the first run builds its venv once), not in the edit hook and not in `oh test`; `--no-lint` skips it. Run it once before the review.

## Running tests with `oh`

| Command | Use |
|---|---|
| `oh test` | Test the modules changed against the base branch (all project modules when nothing changed). |
| `oh test mod_a mod_b` | Test specific project modules. |
| `oh test mod --tags /mod:TestClass.test_method` | Run one test or class. The record is **partial** (`test-<mod>-tags-<hash>`): it proves only the tests it ran, never supersedes a module record, and a newer module or full-suite record that covers it prunes it. The tag syntax is `[-][tag][/module][:class][.method]`. |
| `oh test mod --require TestX.test_a1 --require TestX.test_a2` | Also require these tests to run (the acceptance criteria's tests). Forms: `mod:Class.method`, `Class.method`, `Class`. |
| `oh test mod --upgrade-from origin/<prod-branch>` | Install the deployed version, run `prepare_upgrade(env)` there, update to your code, then test, including the `oh_upgrade` checks (`data-migrations.md`). |
| `oh test mod --with-dependents` | Also test the project modules that depend on `mod`. |
| `oh deps [mod ...]` | Print the changed modules (or the given ones) with the project modules they depend on, as paths: `git diff --quiet origin/main origin/staging -- $(oh deps)` fails when the two branches differ in any of them (whether the second upgrade run is needed). |
| `oh test --all` | Install every project module together, closer to an Odoo.sh development build. Runs in up to 3 parallel parts (each part installs every module and runs the tests of some of them; one merged record); `--jobs N` sets the number, `--jobs 1` runs one process. The default leaves one CPU free, for the upgrade run started alongside in the merge step. |
| `oh test mod --keep` | Keep the database, with every project language loaded, for `oh shell`, `oh serve`, `oh shot` and `oh i18n`. |
| `oh test mod --keep --seed path/to/seed.py` | Also run a seed script (records, users, settings for screens) in `odoo shell` on the kept database and commit it. The script sees `env`. |
| `oh test mod --langs all` / `--langs ar_001` | Load every project language, or the given ones, in a test run. By default a test run loads only English, like an Odoo.sh test database, so a test that needs Arabic must load it itself. |
| `oh test mod --no-demo` / `--fresh` | Without demo data (Odoo.sh staging and production have none) / without the cached template (slower). |
| `oh test mod --rerun` / `--no-record` | Run even if an identical run passed in the last 24 hours / don't write the evidence record. |

Results:
- **PASSED** (exit 0): tests ran and passed in every tested module, every `--require`d test ran, and after an upgrade that changed data an `oh_upgrade` check ran.
- **FAILED** (1): a test failed or errored, Odoo logged an error, or `oh check` found a static problem (then Odoo didn't run).
- Setup error (2).
- **BLOCKED** (3): modules missing locally, usually Enterprise.
- **NOT VERIFIED** (4): the summary lists what didn't run, for example no test ran, all tests were skipped, a module has no tests, a required test didn't run, or no upgrade check ran. A module's tests don't run when `tests/__init__.py` doesn't import the test file or the tags matched nothing.

The summary counts executed, skipped, failed and errored tests per module, with the test time and the slowest tests (a test over a few seconds usually sets up more than its criterion needs). Warnings are listed because Odoo.sh marks a build with warnings as "almost successful".

Each run writes `.odoo-harness/evidence/<test|upgrade>-<modules>[-from-<ref>][-tags-<hash>].json` (an upgrade record names its baseline, so the runs from `main` and from `staging` keep separate records; a `--tags` record is partial, see the table) and, next to it, a folder with the compressed Odoo log (and, for upgrades, the prior-version and `prepare_upgrade` logs). The record holds the source (a content id per tested module, submodules included, the HEAD commit, uncommitted changes), the Odoo and Enterprise commits, the installed Python packages, PostgreSQL and the browser, the command, per-module counts, failures, and each kept file's checksum. Failed runs are kept the same way. Commit the records and their folders with the change; `oh evidence` checks the files, re-reads each log to confirm the counts and the verdict, and says whether each record still matches the source. Records accumulate, one per selection: before a handover, `oh evidence --dry-run` lists the stale records, and the partial `--tags` records, that a newer passed whole record of the same kind covers, and `oh evidence --prune` deletes them (never a current whole record, a failure nothing newer covers, or a record with a problem); commit the deletions with the evidence. At a delivery (the merge step), `oh evidence --prune-stale` deletes every stale record, covered by a newer one or not: a record whose modules changed since proves nothing about the source any more, and git history keeps it. The repository then carries only the records that still prove something: the full-suite record, the delivery's upgrade records and the current screenshot records (the verified images live with the feature's docs).

When the same source, environment and selection passed on this machine in the last 24 hours and its log is still intact, `oh test` reuses that result instead of running again (`--rerun` runs it anyway). It never reuses when the source can't be identified exactly: unreadable module files, files git ignores inside a module, or an Enterprise copy outside git; the output says why.

The first run for a new set of dependencies builds a template database, which takes minutes for large apps. Later runs clone it and take seconds plus your module's install and tests.

## Writing tests (Odoo 19)

```python
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestFleetX(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="fx_user", groups="base.group_user,my_module.group_fleet_x_user")
        cls.record = cls.env["fleet.x"].create({"name": "A"})

    def test_user_cannot_approve(self):
        with self.assertRaises(AccessError):
            self.record.with_user(self.user).action_approve()

    def test_form_onchange(self):
        with Form(self.env["fleet.x"]) as form:
            form.name = "B"
            form.amount = 10
        self.assertEqual(form.record.total, 10)
```

- `TransactionCase` rolls back after each test; class-level data from `setUpClass` is shared by the tests of the class.
- Use `@tagged("post_install", "-at_install")` when the test needs other modules fully installed, or when it runs a tour. Plain `TransactionCase` tests run at install time by default.
- Test as real users: `new_test_user(env, login=..., groups="a.b,c.d")`, then `record.with_user(user)`. `@users("login1", "login2")` (from `odoo.tests.common`) runs a test once per user.
- `Form(record_or_model)` simulates the UI, including onchanges and the `required`, `readonly` and `invisible` modifiers.
- Freeze time with `from freezegun import freeze_time` (it's in Odoo's requirements).
- Assert business errors with `assertRaises(UserError)` or `assertRaises(ValidationError)`, and access errors with `AccessError`.
- Don't depend on demo record IDs or on data that other modules may change. Create what the test needs. Don't assert values Odoo.sh formats differently from a local run (phone numbers are reformatted there): assert the digits, or the record, not the formatted string.
- A test that needs Arabic activates it itself (`res.lang._activate_lang("ar_001")` and the module's terms), because Odoo.sh test databases, like the local run, have only English.
- Odoo's `assertRaises` doesn't roll back the failed statement inside a `TransactionCase` method: wrap the call in `with self.env.cr.savepoint():` when the test continues after it.
- Multi-company: create a second company in the test and check both visibility and cross-company rejection.

## Tours (UI flows)

A tour is a JavaScript file in `static/tests/tours/`, loaded through the `web.assets_tests` bundle in the manifest:

```js
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("fleet_x_tour", {
    steps: () => [
        { trigger: ".o_list_button_add", run: "click" },
        { trigger: ".o_field_widget[name=name] input", run: "edit Tour record" },
        { trigger: ".o_form_button_save", run: "click" },
        // End with a step whose trigger only matches once the expected outcome is visible.
    ],
});
```

Run it from Python in an `HttpCase` tagged post_install: `self.start_tour("/odoo/action-my_module.action_fleet_x", "fleet_x_tour", login="admin")`. `oh test` provides the headless Chromium that tours need. For current step syntax, look at `addons/sale/static/tests/tours/`.

## JavaScript unit tests

Frontend unit tests use HOOT (`import { describe, expect, test } from "@odoo/hoot";`) plus `@web/../tests/web_test_helpers`, and are registered in the `web.assets_unit_tests` bundle. Copy the structure of a nearby test in `addons/web/static/tests/`.
