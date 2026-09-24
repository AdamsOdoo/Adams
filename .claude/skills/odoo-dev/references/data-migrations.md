# Changing deployed modules without losing data

On Odoo.sh, production and staging run a module update only when that module's manifest `version` increases (see `odoo-sh.md`). If the update fails, Odoo.sh keeps the previous build running. Plan every change to an installed module as an update of existing data, not only as a fresh install.

## The version

`"version": "19.0.1.2.0"`, where the digits after the series are yours. Bump it whenever models, fields, XML data, views, security or assets of an installed module change. `oh test` warns when a module changed against the production branch without a version bump.

## What changes existing data

| Change | What happens on update | What to do |
|---|---|---|
| New stored field | Column added; computed stored fields are computed for every existing record | Fine. For large tables with an expensive compute, fill the column in a `pre-` script (SQL) so Odoo doesn't recompute it. |
| Rename a field | Odoo sees a new field; the old column and its data stay unused | `pre-` script: `ALTER TABLE ... RENAME COLUMN old TO new` (and fix references). |
| Change a field type | The column may be converted or recreated | `pre-` script to copy or convert the values; test with `--upgrade-from`. |
| Remove a selection value | Existing records keep an invalid value | `pre-` or `post-` script to map old values to new ones. |
| Remove a field or model | Columns and tables remain, but the data is orphaned | Decide explicitly; migrate the data you need first. |
| XML record with `noupdate="1"` (rules, sequences, mail templates, cron jobs) | **Not updated**; the installed version keeps its old values | Change it in a `post-` script (`env.ref(...).write({...})`) or tell the user to change it in the UI. |
| XML record without `noupdate` | Overwritten from the file; UI edits are lost | Put records users customise under `noupdate="1"`. |
| New required field | Existing rows need a value | Give it a `default` or fill it in a `pre-` script. |

## Migration scripts

```
my_module/
  migrations/
    19.0.1.2.0/            # the new version; runs when updating from an older one
      pre-migrate.py       # before the module's models and data load (SQL only)
      post-migrate.py      # after the module is loaded (ORM available)
      end-migrate.py       # after all modules are updated
    0.0.0/                 # runs on every version change
```

Each file defines `migrate(cr, version)`, where `version` is the previously installed version (`odoo/modules/migration.py`).

```python
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["fleet.x"].search([("state", "=", "old")]).write({"state": "draft"})
```

- In `pre-` scripts use SQL only: the new Python fields don't exist in the database yet.
- Make scripts idempotent (`WHERE new_col IS NULL`, `IF EXISTS`) and fast on large tables. Work in SQL where the ORM would load millions of records.
- Log what you changed (`_logger.info`) so it shows in the Odoo.sh update log.
- Test with `oh test my_module --upgrade-from origin/<production-branch>` and check the result (next section). The summary lists the migrations that ran.

## Check the upgraded data, not only that the update ran

A migration that runs without errors can still write wrong values or break old records. When an update changes stored data, prepare records on the deployed version and check them after the update:

```python
# my_module/tests/test_upgrade.py, imported in tests/__init__.py
from odoo.tests import TransactionCase, new_test_user, tagged


def prepare_upgrade(env):
    """Runs on the deployed version before the update (oh test --upgrade-from). Use env and the ORM only."""
    partner = env["res.partner"].create({"name": "Upgrade check partner"})
    env["fleet.x"].create({"name": "Upgrade check", "state": "old", "partner_id": partner.id})


@tagged("oh_upgrade", "-standard", "post_install", "-at_install")
class TestFleetXUpgrade(TransactionCase):
    """Runs only in `oh test --upgrade-from`, after the update, on the records prepared above."""

    def test_old_record_migrated(self):
        record = self.env["fleet.x"].search([("name", "=", "Upgrade check")])
        self.assertEqual(record.state, "draft")  # transformed as intended
        self.assertEqual(record.partner_id.name, "Upgrade check partner")  # relation kept

    def test_old_record_still_usable(self):
        record = self.env["fleet.x"].search([("name", "=", "Upgrade check")])
        user = new_test_user(self.env, login="upgrade_user", groups="base.group_user,my_module.group_fleet_x_user")
        self.assertTrue(record.with_user(user).has_access("write"))  # access rules still apply
        record.action_confirm()  # the next workflow step works on an old record
        self.assertEqual(record.state, "confirmed")
```

- `oh test my_module --upgrade-from origin/<production-branch>` installs the deployed version, runs every `prepare_upgrade(env)` found in the module's `tests/*.py` there and commits, updates to your code (the migration scripts run), then runs the module's tests plus the ones tagged `oh_upgrade`.
- `prepare_upgrade` runs with the deployed code, so it may use only models and fields that exist there. The file's absolute imports are copied with it; relative imports are not.
- `-standard` keeps these checks out of normal runs and Odoo.sh builds, where the prepared records don't exist. `post_install` runs them after all migration scripts, including `end-` scripts.
- Check both sides: what the change must transform (values, selection mappings, recomputed fields) and what it must keep (relations, amounts, access for the roles involved, the next workflow step).
- When a migration script ran, or a `prepare_upgrade` exists, and no `oh_upgrade` test ran, the result is **not verified**. A migration line in the log is not proof that the data is right.

## Before merging to production

- A staging build runs your code against a neutralized copy of the production database, so modules are updated, not installed fresh. Confirm the update and the data there before production.
- Mention in the feature notes: the version bump, the scripts, what data they change, and anything the user must do by hand.
