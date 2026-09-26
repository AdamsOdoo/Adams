# Odoo.sh: branches, builds and verification

Source: the Odoo 19 documentation in `odoo/documentation` (`content/administration/odoo_sh/`).

## Branch stages

| Stage | Database on each push | Tests | Module updates |
|---|---|---|---|
| Development | New database, **demo data**, the branch's modules installed (configurable) | Run by default; a failing test fails the build | n/a (fresh install) |
| Staging | Neutralized **copy of production**: scheduled actions and IAP disabled, outgoing emails caught by the mail catcher, payment providers and shipping connectors in test mode. Depending on the branch setting, each push makes a new copy or updates the previous staging build. | Not run (no demo data) | Modules whose manifest version increased |
| Production | The live database | Not run | Modules whose manifest version increased; if the update fails, the previous build keeps running |

- Only the user promotes code: they merge the feature branch into staging, then staging into production, from the Odoo.sh UI or with git. Agents push feature branches only.
- That rule is enforced by GitHub, not by the agent: a ruleset on the production and staging branches lets only repository admins update them (`oh protect` prints it; `oh doctor` checks it when a GitHub token is available). Without it, any agent or person with write access can deploy by pushing.
- Development databases last about three days. Staging databases are deleted after a month. Only production is backed up automatically.
- Branch settings can limit which modules install on development builds and which test tags run (for example `/my_module`). A full install of all modules can take up to an hour.
- Build status: **successful** (green), **almost successful** (yellow: warnings in the log), **failed** (red: errors or failed tests). Treat new warnings from your modules as defects.

## Getting the build result

- **GitHub commit status.** When the Odoo.sh project has a GitHub token with the "commit statuses (write)" permission (project settings, "GitHub commit statuses"), each build reports its status on the pushed commit. Read it with the GitHub tools (the commit's status or check runs, or the pull request status). This lets an agent follow builds without an Odoo.sh login.
- **Build logs** (`install.log` on development builds, `update.log`, `odoo.log`, `pip.log`) are in the Odoo.sh UI and in the build container under `~/logs/`. Every project role can see development build logs; the Developer role can't see staging or production logs. If you can't read them, ask the user for the failing lines.
- On a development build, the Odoo.sh shell offers `odoo-bin shell`, `odoo-update`, `psql` and `lnav ~/logs/odoo.log`. Running `odoo-bin -i my_module --test-enable --log-level=test --stop-after-init` in the build's shell runs a module's tests on that build.

## Build environment

- Ubuntu container with Odoo's dependencies. Extra Python packages go in `requirements.txt` at the repository root (submodules' `requirements.txt` files are read too).
- Source layout: `~/src/user` (your repository), `~/src/enterprise`, `~/src/themes` and `~/src/odoo`. The addons path lists your repository before Enterprise and Community.
- Git submodules are added to the addons path automatically. Private submodules need a deploy key configured in the Odoo.sh settings.
- With the default "Latest" revision setting, Odoo.sh updates its Odoo sources weekly. `oh env --update` moves the local copy to the latest 19.0 too.

## Using this with `oh`

1. Iterate locally with `oh test` until it passes.
2. If `oh test` is **blocked** (Enterprise modules missing locally), or when a dependency's own tests might break, push the feature branch and read the development build status.
3. For changes to deployed modules, `oh test --upgrade-from origin/<production-branch>` locally, then the user validates on staging with a copy of production data.
4. Report which of these ran. A local pass doesn't prove the Odoo.sh build passed.
