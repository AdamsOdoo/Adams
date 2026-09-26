# Testing

## Running tests with `oh`

| Command | Use |
|---|---|
| `oh test` | Test the modules changed against the base branch (all project modules when nothing changed). |
| `oh test mod_a mod_b` | Test specific project modules. |
| `oh test mod --tags /mod:TestClass.test_method` | Run one test while iterating (not recorded as evidence). The tag syntax is `[-][tag][/module][:class][.method]`. |
| `oh test mod --require TestX.test_a1 --require TestX.test_a2` | Also require these tests to run (the acceptance criteria's tests). Forms: `mod:Class.method`, `Class.method`, `Class`. |
| `oh test mod --upgrade-from origin/<prod-branch>` | Install the deployed version, run `prepare_upgrade(env)` there, update to your code, then test, including the `oh_upgrade` checks (`data-migrations.md`). |
| `oh test mod --with-dependents` | Also test the project modules that depend on `mod`. |
| `oh test --all` | Install every project module together, closer to an Odoo.sh development build. |
| `oh test mod --keep` | Keep the database for `oh shell`, `oh serve` and `oh shot`. |
| `oh test mod --no-demo` / `--fresh` | Without demo data (Odoo.sh staging and production have none) / without the cached template (slower). |
| `oh test mod --rerun` / `--no-record` | Run even if an identical run passed in the last 24 hours / don't write the evidence record. |

Results:
- **PASSED** (exit 0): tests ran and passed in every tested module, every `--require`d test ran, and after an upgrade that changed data an `oh_upgrade` check ran.
- **FAILED** (1): a test failed or errored, or Odoo logged an error.
- Setup error (2).
- **BLOCKED** (3): modules missing locally, usually Enterprise.
- **NOT VERIFIED** (4): the summary lists what didn't run, for example no test ran, all tests were skipped, a module has no tests, a required test didn't run, or no upgrade check ran. A module's tests don't run when `tests/__init__.py` doesn't import the test file or the tags matched nothing.

The summary counts executed, skipped, failed and errored tests per module. Warnings are listed because Odoo.sh marks a build with warnings as "almost successful".

Each run without `--tags` writes `.odoo-harness/evidence/<test|upgrade>-<modules>.json` and, next to it, a folder with the compressed Odoo log (and, for upgrades, the prior-version and `prepare_upgrade` logs). The record holds the source (a content id per tested module, submodules included, the HEAD commit, uncommitted changes), the Odoo and Enterprise commits, the installed Python packages, PostgreSQL and the browser, the command, per-module counts, failures, and each kept file's checksum. Failed runs are kept the same way. Commit the records and their folders with the change; `oh evidence` checks the files, re-reads each log to confirm the counts and the verdict, and says whether each record still matches the source.

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
- Don't depend on demo record IDs or on data that other modules may change. Create what the test needs.
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
