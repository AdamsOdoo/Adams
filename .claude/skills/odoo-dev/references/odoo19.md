# Odoo 19 API notes

Every item below was checked in the `odoo/odoo` 19.0 source; the source path is given so you can re-check with `oh src`. Examples from blogs and older modules often use the removed forms.

## Models and fields

- **SQL constraints and indexes are class attributes.** `_sql_constraints` is ignored with a warning (`odoo/orm/model_classes.py`). Use the objects from `odoo/orm/table_objects.py`:
  ```python
  _name_company_uniq = models.Constraint("UNIQUE(name, company_id)", "The name must be unique per company.")
  _state_date_idx = models.Index("(state, date_order)")
  ```
  `models.UniqueIndex` also exists. Python-level rules stay `@api.constrains`.
- **`display_name`** is computed. Override `_compute_display_name` instead of the removed `name_get`, and set `_rec_names_search = ["name", "code"]` to make other fields searchable in many2one lookups (`odoo/orm/models.py`).
- **`create` takes a list.** Decorate overrides with `@api.model_create_multi` and loop over `vals_list`.
- **`self.env.cr`, `self.env.uid`, `self.env.context`.** `self._cr`, `self._uid` and `self._context` are deprecated (`odoo/upgrade_code/18.5-00-deprecated-properties.py`).
- **`aggregator="sum"`** on a field replaces `group_operator` (`odoo/orm/fields.py`).
- **`index=`** accepts `True` (btree), `"btree_not_null"` or `"trigram"` (for `ilike` searches on large tables).
- **Multi-company consistency:** `_check_company_auto = True` on the model, plus `check_company=True` on relational fields that point to company-restricted models.
- **Domains:** `from odoo.fields import Domain`, then `Domain("state", "=", "sale") & Domain("company_id", "in", company_ids)`, `Domain.AND([...])`, `Domain.OR([...])`, `~domain` (`odoo/orm/domains.py`). List domains still work.
- **x2many commands:** `from odoo.fields import Command`: `Command.create(vals)`, `Command.link(id)`, `Command.set(ids)`, `Command.unlink(id)`, `Command.update(id, vals)`, `Command.delete(id)`, `Command.clear()`. `Command` also works inside XML `eval` (`odoo/tools/convert.py`).
- **Aggregation:** `_read_group(domain, groupby, aggregates)` returns tuples:
  ```python
  for partner, total in self.env["sale.order"]._read_group(domain, ["partner_id"], ["amount_total:sum"]):
      ...
  ```
  `read_group` is deprecated; `formatted_read_group` is the web-client format (`addons/web/models/models.py`).
- **Access checks:** `records.check_access("write")` raises `AccessError`; `records.has_access("read")` returns a bool. `check_access_rights` and `check_access_rule` are deprecated since 18.0.
- **Environment helpers:** `self.env.is_superuser()`, `self.env.is_admin()`, `self.env.is_system()`, and `self.env.user.has_group("module.group_xmlid")`.
- **Raw SQL** only when the ORM can't express the query, and always through `odoo.tools.SQL`:
  ```python
  from odoo.tools import SQL
  self.env.cr.execute(SQL("SELECT id FROM %s WHERE state = %s", SQL.identifier("sale_order"), state))
  ```
  Never format values into SQL strings. Before reading stored fields that were written earlier in the same transaction, call `self.env.flush_all()` or pass `to_flush=` to `SQL`.
- **Translations in Python:** `self.env._("Order %(name)s is locked", name=order.name)`. `from odoo import _` still works (`odoo/orm/environments.py`). Keep variables out of the source string and use named placeholders.
- **Deletion rules:** use `@api.ondelete(at_uninstall=False)` for "cannot delete when …" checks instead of overriding `unlink` (`odoo/orm/decorators.py`).
- **Batch crons:** call `self.env["ir.cron"]._commit_progress(processed, remaining=n)` inside the job loop; it commits, reports progress and returns the remaining time budget. `_notify_progress` is deprecated (`odoo/addons/base/models/ir_cron.py`).
- **Controllers:** use `@http.route("/x", type="jsonrpc", auth="user")`; the old `type="json"` was renamed (`odoo/upgrade_code/18.1-02-route-jsonrpc.py`). `type="http"` routes that change data keep CSRF protection on.

## Users, groups and privileges

- `res.users.group_ids` holds the explicit groups and `all_group_ids` includes implied ones. `groups_id` no longer exists (`odoo/addons/base/models/res_users.py`).
- A group belongs to a privilege (`res.groups.privilege`, with a `category_id`) through `privilege_id`. Its members are `user_ids`. This is the pattern used in `addons/sales_team/security/`:
  ```xml
  <record id="res_groups_privilege_fleet_x" model="res.groups.privilege">
      <field name="name">Fleet X</field>
      <field name="sequence">10</field>
      <field name="category_id" ref="base.module_category_services"/>
  </record>
  <record id="group_fleet_x_user" model="res.groups">
      <field name="name">User</field>
      <field name="sequence">10</field>
      <field name="privilege_id" ref="res_groups_privilege_fleet_x"/>
      <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
  </record>
  ```
  Pick a real `ir.module.category` for the privilege (`oh src 'module_category_' --glob '*.xml' --module base`).

## Views and web client

- List views are `<list>`; `<tree>` is gone, and actions use `view_mode` `list,form` (`odoo/upgrade_code/17.5-01-tree-to-list.py`).
- `attrs` and `states` are rejected at install since 17.0 (`odoo/addons/base/models/ir_ui_view.py`). Write Python expressions directly: `invisible="state != 'draft'"`, `readonly="is_locked"`, `required="type == 'service'"`. In a list, hide a whole column with `column_invisible="..."`.
- Web client URLs are `/odoo/...`, for example `/odoo/action-<module>.<action_xmlid>` and `/odoo/action-<module>.<action_xmlid>/<record_id>` (`addons/web/static/src/core/browser/router.js`).

## Tooling in `odoo-bin`

- `odoo-bin upgrade_code --addons-path <path> --from 17.0 --dry-run` rewrites old idioms (tree to list, SQL constraints, json routes, deprecated properties, domain dates). Its scripts are in `odoo/upgrade_code/`. Use it when porting modules from older versions.
- `odoo-bin i18n export -d <db> -l ar_001 <module>` writes `<module>/i18n/ar.po`; `-l pot` writes the template (`odoo/cli/i18n.py`).
- `odoo-bin module install|upgrade|uninstall` subcommands exist; the classic `-i` and `-u` still work.
- Demo data is **off** by default; `--with-demo` loads it (`odoo/tools/config.py`). Odoo.sh development builds load demo data, and so does `oh test`.

When something here seems wrong for your case, trust the source (`oh src`) over this file.
