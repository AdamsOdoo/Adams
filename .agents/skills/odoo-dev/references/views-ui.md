# Views, actions, frontend and screenshots

Keep the standard Odoo look unless the user asked for a custom design. Extend standard views instead of replacing them.

## Inheriting views

```xml
<record id="view_order_form_inherit_fleet_x" model="ir.ui.view">
    <field name="name">sale.order.form.fleet.x</field>
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="sale.view_order_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='partner_id']" position="after">
            <field name="fleet_x_id" invisible="state == 'cancel'" readonly="state != 'draft'"/>
        </xpath>
    </field>
</record>
```

- Anchor xpaths on stable things such as `@name` of fields, buttons and pages, not on positions like `//group[2]`. `position` is one of `after`, `before`, `inside`, `replace` or `attributes`, and `move` is also allowed inside another xpath.
- Use `position="attributes"` with `<attribute name="invisible">…</attribute>` to change a modifier instead of replacing the element.
- Modifiers are Python expressions over the record's fields: `invisible`, `readonly`, `required`, plus `column_invisible` in lists. `attrs` and `states` fail at install (see `odoo19.md`).
- Lists are `<list>`. For editable lists use `editable="bottom"`, for totals `sum="Total"`, and for badges `widget="badge"` with `decoration-success="state == 'done'"`.
- A field that is only needed by a modifier can be added with `column_invisible="True"` in lists or `invisible="1"` in forms.
- Field-level `groups="module.group_xmlid"` hides the element; the model's access rules still decide what the user may read or write.

## Actions and menus

```xml
<record id="action_fleet_x" model="ir.actions.act_window">
    <field name="name">Fleet X</field>
    <field name="res_model">fleet.x</field>
    <field name="view_mode">list,form</field>
    <field name="context">{'search_default_my': 1}</field>
</record>
<menuitem id="menu_fleet_x" name="Fleet X" parent="fleet.menu_root" action="action_fleet_x" sequence="50"/>
```

Menus are visible only if the user can read the action's model. Restrict a menu with `groups="…"`. Search views (`<search>` with `<filter name="my" domain="[('user_id', '=', uid)]"/>`) provide the default filters used in the context.

## Owl and JavaScript (only when views can't do it)

- Files go in `static/src/`, registered in the manifest: `"assets": {"web.assets_backend": ["my_module/static/src/**/*"]}`.
- Import paths used by the 19.0 addons: `import { Component, useState } from "@odoo/owl";`, `import { registry } from "@web/core/registry";`, `import { useService } from "@web/core/utils/hooks";`, `import { patch } from "@web/core/utils/patch";`, `import { _t } from "@web/core/l10n/translation";`.
- Add a field widget with `registry.category("fields").add("my_widget", { component: MyWidget, supportedTypes: ["char"] })`, then use it in views as `widget="my_widget"`. Before writing one, check the existing widgets in `addons/web/static/src/views/fields/`.
- Change existing components with `patch(Component.prototype, { … })` and keep the patch small.
- Server calls: `this.orm = useService("orm")`, then `await this.orm.call(model, method, args)` or `this.orm.searchRead(...)`. Access rules apply as usual.
- Styles: prefer Bootstrap utility classes and Odoo variables. Custom SCSS in the same assets bundle gets flipped for right-to-left languages by rtlcss; mark exceptions with `/*rtl:ignore*/`.
- Tests: tours for flows (`testing.md`), HOOT unit tests for component logic.

## Checking the result: screenshots in both languages

1. `oh test my_module --keep` keeps the test database, with demo data and both languages loaded. After editing the modules, keep a new one: `oh shot` doesn't accept a database built before your latest changes.
2. Optionally add realistic records or a user for a role: `oh shell -c "env['fleet.x'].create({...}); env.cr.commit()"`.
3. `oh shot /odoo/action-my_module.action_fleet_x --out docs/features/<id>/screens --expect '.o_list_view' --expect '[name=fleet_code]'` captures each page in English and Arabic on this project's database (`--db` picks another kept one, `--login`/`--password` a role, `--mobile` a phone viewport).
4. Each image is checked before it counts: the right database, user and language, right-to-left for Arabic, a rendered view, no error dialog or error notification, no loading indicator, and every `--expect` element present. The database must be one `oh test --keep` built in this project from the current source and environment; a database of unknown origin (restored, renamed, built before the latest change) is shown but never accepted. Verified images go to `--out`, or into the record's folder next to `.odoo-harness/evidence/shot-*.json`; `DIAG` images go to its `diagnostic/` folder with the reason, the run is **not verified**, and an older accepted image of the same screen in `--out` is removed. The record lists every image with its checksum.
5. Open the verified images and check them: layout, mirroring, translated labels, overflow, empty states. The checks prove the screen, database, user, language and direction; they don't prove the layout, the labels or the data are right.

A screenshot shows appearance only; the behaviour still needs tests.
