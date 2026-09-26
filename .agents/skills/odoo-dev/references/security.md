# Security and multi-company

Enforce every rule on the server. Hiding a button or field in a view is presentation, not security: users can call model methods through RPC.

## Access rights (every new model)

`security/ir.model.access.csv`, listed in the manifest `data` after the XML file that defines the groups:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_fleet_x_user,fleet.x user,model_fleet_x,group_fleet_x_user,1,1,1,0
access_fleet_x_manager,fleet.x manager,model_fleet_x,group_fleet_x_manager,1,1,1,1
```

A model without access rows logs "The models … have no access rules", and Odoo.sh reports the build as almost successful. Transient models (wizards) need access rows too.

## Groups

Groups belong to a privilege in Odoo 19; see the `res.groups.privilege` example in `odoo19.md`. Chain the levels with `implied_ids` (manager implies user, user implies `base.group_user`). Check membership in code with `self.env.user.has_group("module.group_xmlid")`, and restrict fields or view elements with `groups="module.group_xmlid"`. Remember that restricting a field in a view doesn't stop RPC access to it; use `groups=` on the field definition to restrict the field itself.

## Record rules

```xml
<record id="rule_fleet_x_company" model="ir.rule">
    <field name="name">Fleet X: allowed companies</field>
    <field name="model_id" ref="model_fleet_x"/>
    <field name="domain_force">[('company_id', 'in', company_ids)]</field>
</record>
```

- A rule without `groups` is global: it applies to everyone and combines with other global rules using AND. Rules with groups combine using OR within the user's groups.
- If `company_id` can be empty: `['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]`.
- An "own documents only" rule: `[('user_id', '=', user.id)]` on the basic group, and `[(1, '=', 1)]` on the "all documents" group.
- The evaluation context has only `user`, `company_ids` (the companies enabled in the company switcher) and `company_id` (the current company) (`odoo/addons/base/models/ir_rule.py`). Older examples that use `time` in a rule fail in Odoo 19.

## Multi-company

- Give company-specific models `company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)`, set `_check_company_auto = True`, and add `check_company=True` on relations to company-specific models so that cross-company links are rejected.
- Use `self.env.company` (the current company) and `self.env.companies` (the allowed ones). Don't assume a single company.
- Use `record.with_company(company)` when computing in another company's context, for example with company-dependent fields or taxes.
- Test with two companies: records of company B must be invisible to a user of company A, and a cross-company link must raise.

## sudo()

`sudo()` bypasses access rights and record rules. Use it only for a specific technical read or write that the user is entitled to indirectly, keep it narrow (`record.sudo().field`), and never return sudo-ed records to the user. Before calling `sudo()` on user-provided IDs, check access with `records.check_access("read")`. Prefer `with_user()` to act as a specific user.

## Controllers and external access

- `auth="user"` for backend routes; `auth="public"` only for data that is really public. Validate every parameter.
- Browse records as the user, not with `sudo()`, unless you check access explicitly.
- JSON routes are `type="jsonrpc"` in Odoo 19. CSRF protection stays on for `type="http"` POST routes.
- Keep secrets (API keys, tokens) in `ir.config_parameter` or fields restricted with `groups="base.group_system"`, never in code or the repository.

## Tests that prove security

For each permission rule, write a test that the allowed user succeeds and the denied user gets `AccessError` (or `UserError` for business rules), running as a real user created with `new_test_user(...)`. See `testing.md`.
