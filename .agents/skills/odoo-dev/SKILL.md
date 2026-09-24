---
name: odoo-dev
description: Build, fix or extend Odoo 19 Enterprise modules for an Odoo.sh project end to end - models, views, security, reports, data, migrations, Owl/JavaScript and translations. Use for any Odoo development, bug fix or technical design task in this repository.
---

# Odoo development for Odoo.sh (Odoo 19 Enterprise)

Deliver a working, tested change the way a senior Odoo developer would: reuse standard Odoo first, keep the customization small and upgrade-safe, and prove it with tests. `oh` means `.odoo-harness/oh`.

## 1. Frame the request

Restate the goal in a sentence or two, then write numbered acceptance criteria (A1, A2, …). Include the roles, companies and languages involved when they matter. If a business rule is missing and you can't infer it from the code, data or existing behaviour, ask once, with all your questions together. For anything else, state an assumption and continue.

Size the work; the size decides how much process it needs.

| Size | Typical change | Design | Tests | Documentation |
|---|---|---|---|---|
| S | label, field, view tweak, small fix | a line in the commit message | update or add the affected test | none, or a line in the feature notes |
| M | new rule, computed field, report, wizard, permission change | short notes: data model, rules, access | a test per criterion, including a denied-access case when security is involved | feature notes |
| L | new app or flow, several modules, migrating existing data | `references/design.md` before coding | also an upgrade test and a tour when a UI flow matters | feature notes, user guide in English and Arabic, upgrade notes |

A change that touches money, access rights or existing data is at least M, however small the diff.

## 2. Look before building

- Search standard Odoo first: `oh src "<regex>"` (add `--module sale` or `--glob '*.xml'` to narrow it, `--where sale` to locate a module). Enterprise apps may already cover the need, for example Approvals, Documents, Sign, Planning, Helpdesk, Subscriptions or Accounting reports. Prefer configuration, data records or a small inheritance over new models.
- Read the models you will extend: their fields, compute methods, `_inherit` chain and access rules.
- Read `references/odoo19.md` before writing Python or XML; it lists the Odoo 19 changes that break older habits.

## 3. Implement

- One module per business capability. Inherit, don't copy: `_inherit`, `inherit_id` with `xpath`, `super()`. Match the project's existing module prefix and style.
- Every new model needs access rights, plus a company record rule if it has `company_id`: see `references/security.md`.
- User-facing strings need Arabic translations in `i18n/ar.po`: see `references/i18n-rtl.md`.
- When an installed module's data, fields or views change, bump `version` in `__manifest__.py`. Add a migration script when existing records must be transformed: see `references/data-migrations.md`.
- Figures, dashboards and reports: use the standard report's result when one provides the figure; a custom calculation needs a written reason and explicit filters. See `references/reports.md`.
- Views, menus, Owl components, assets and tours: see `references/views-ui.md`.

## 4. Test: fast loop first, then broaden

- Write or update tests alongside the code (`references/testing.md`). Test observable behaviour: button methods, `Form`, and access checks run as a real user. Give each acceptance criterion a test and note it (A1 → `TestX.test_a1`).
- While iterating, run one test: `oh test <module> --tags /<module>:<TestClass>.<test_method>`. It takes seconds and isn't recorded as evidence.
- Then run the module's tests and require the criteria's tests: `oh test <module> --require TestX.test_a1 --require TestX.test_a2`. **PASSED** means they all ran and passed. **NOT VERIFIED** lists what didn't run (no tests, skipped tests, a missing required test): fix that; it is not a pass.
- An identical run (same source, environment and selection) that passed on this machine in the last 24 hours, with its log intact, is reused instead of repeated; `--rerun` forces a run. The output says when a run can't be reused.
- For a change to a module that is already deployed, also run `oh test <module> --upgrade-from origin/<production-branch>`. It installs the deployed version first, then updates to yours, like Odoo.sh does on staging and production. When the change alters stored data, add `prepare_upgrade(env)` and an `oh_upgrade` test that checks the migrated records (`references/data-migrations.md`); without them the run is **not verified**.
- For M and L changes to modules that other project modules build on, add `--with-dependents`. Before delivering an L change, also run `oh test --all`.
- Read the summary it prints. Open the log it names only when the summary isn't enough.
- If a test fails because of your change, fix the code, not the test. Change a test only when the requirement changed, and say so.
- After three attempts at the same failure, stop, rethink the approach, and write down what you tried in the handoff.

## 5. Verify on Odoo.sh when needed

Local runs use Odoo Community, plus Enterprise when `project.json` points to its source. When `oh test` says **blocked**, or the behaviour depends on production data, push the feature branch; Odoo.sh builds it as a development build (fresh database, demo data, tests). Read the result from the commit status on GitHub if the project has enabled that; otherwise ask the user for the build status or the failing log lines. See `references/odoo-sh.md`.

## 6. Review and deliver

- For M and L changes, get an independent review. In Claude Code, give the `odoo-reviewer` agent the acceptance criteria and the base branch; it reads the code and the evidence but can't change them. Elsewhere, review in a fresh session with the `odoo-review` skill; that is independent but not enforced read-only, so say so. Reviewing your own work in the same session is a self-review: call it that. Fix what the review finds; while a finding about behaviour, security or data safety is open, the outcome is not **completed**.
- For UI changes, check the changed screens in English and Arabic: `oh test <module> --keep`, then `oh shot /odoo/action-<module>.<action_id> --out docs/features/<id>/screens --expect '<css of the new element>'`. Add `--login <user> --password <password>` to see a role's view (create the user with `oh shell`). Only images marked `ok` count; `DIAG` images show a loading screen, an error, a database of unknown or outdated origin, or the wrong screen, user or language. Open the verified images and check them; don't claim a layout works without seeing it.
- Update the feature notes, using `assets/feature.md` as the template, in `docs/features/<id>.md` or wherever the project keeps them. Keep them in proportion to the size of the change.
- Commit the code, the feature notes and `.odoo-harness/evidence/` (records with their logs and screenshots) to the feature branch, then push it. `oh evidence` must show each record intact and matching the committed source. Never push to or merge into the production or staging branch; the user promotes on Odoo.sh.
- Final report: what changed; the results (local and/or Odoo.sh, with counts and the evidence records); the review (independent, or self-review); the outcome (**completed**, **blocked** or **not verified**); and anything the user must do (merge, configure, check data).

## References

| File | Read it when |
|---|---|
| `references/odoo19.md` | before writing Odoo 19 Python or XML |
| `references/security.md` | new models, groups, record rules, multi-company, `sudo`, controllers |
| `references/views-ui.md` | views, actions, menus, Owl/JavaScript, assets, tours, screenshots |
| `references/testing.md` | writing tests, `oh test` options, reading results |
| `references/data-migrations.md` | changing a deployed module: stored fields, data files, migration scripts |
| `references/reports.md` | QWeb/PDF reports, dashboards, KPIs and any figure users will compare |
| `references/i18n-rtl.md` | user-facing text, Arabic translations, right-to-left layout |
| `references/odoo-sh.md` | branches, builds, deployment, logs, verifying Enterprise-dependent code |
| `references/design.md` | L-size work or unclear business flows |
