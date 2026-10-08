---
name: odoo-dev
description: Build, fix or extend Odoo 19 Enterprise modules for an Odoo.sh project end to end - models, views, security, reports, data, migrations, Owl/JavaScript and translations. Use for any Odoo development, bug fix or technical design task in this repository.
---

# Odoo development for Odoo.sh (Odoo 19 Enterprise)

Deliver a working, tested change the way a senior Odoo developer would: reuse standard Odoo first, keep the customization small and upgrade-safe, and prove it with tests and verified screens. `oh` means `.odoo-harness/oh`; its commands and options are in `references/testing.md`.

## 1. Frame the request

Write numbered acceptance criteria (A1, A2, …) with the roles, companies and languages that matter. A business rule you can't infer from the code, the data or existing behaviour is a question for the user: ask all of them in one message. Everything else is an assumption: state it, build it, and list it in the feature notes.

Size the work, because the size decides how much process it gets:

| Size | Typical change | Design | Tests | Documentation |
|---|---|---|---|---|
| S | label, field, view tweak, small fix | a line in the commit message | update or add the affected test | none, or a line in the feature notes |
| M | new rule, computed field, report, wizard, permission change | short notes: data model, rules, access | a test per criterion, plus a denied-access case when security is involved | feature notes |
| L | new app or flow, several modules, migrating existing data | `references/design.md` before coding | also an upgrade test, and at most one tour per main UI flow | feature notes, user guide in English and Arabic, upgrade notes |

A change that touches money, access rights or existing data is at least M, however small the diff.

For M and L, before coding: get every business decision and, for a new screen, the layout (a sketch, a mockup or an existing Odoo screen to follow) agreed in one message; map each criterion to the cheapest test that proves it (`references/testing.md`, "Plan the tests") and write the map next to the criteria in the feature notes; cut work that won't fit one session into milestones that each end with committed, passing work, building one of several similar parts end to end before the others.

## 2. Look before building

Search standard Odoo first (`oh src`): Enterprise apps such as Approvals, Documents, Sign, Planning, Helpdesk, Subscriptions or Accounting reports may already cover the need, and configuration, data records or a small inheritance beat a new model. Read the models you extend (fields, computes, `_inherit` chain, access rules). Read `references/odoo19.md` before writing Python or XML: Odoo 19 differs from what older examples show.

## 3. Implement

- One module per business capability, with the project's module prefix and style. Inherit, don't copy: `_inherit`, `inherit_id` with `xpath`, `super()`.
- Every new model needs access rights, plus a company record rule when it has `company_id` (`references/security.md`).
- User-facing strings need Arabic (`references/i18n-rtl.md`); figures come from the standard report that provides them (`references/reports.md`); views, menus, Owl and tours follow `references/views-ui.md`.
- A change to an installed module bumps `version` in `__manifest__.py`; transformed stored data needs a migration script and an upgrade test (`references/data-migrations.md`).

## 4. Test

Test business behaviour, not looks: button methods, computed values, `Form`, and access checks as real users. Looks are checked on screenshots, not asserted in tests (they break with every design change and find few defects).

- `oh check` runs static checks in seconds, by itself before every `oh test` and, in Claude Code, after every edit; fix what it reports before an Odoo run.
- While iterating, run one test (`--tags … --no-record`: a `--tags` run is recorded otherwise, as a partial record, which is the S route's one recorded run); once per milestone, run the module with the criteria's tests required (`--require`). **PASSED** means they all ran and passed; **NOT VERIFIED** lists what didn't run and is not a pass.
- M and L changes to a module other project modules build on also get `--with-dependents`. An S change runs only its affected tests with `--tags`, once. `oh test --all` and `--upgrade-from` runs belong to the delivery's merge step, once per delivery, not to each milestone (`references/delivery.md`).
- The local run matches an Odoo.sh test database (English only, demo data). A test that needs Arabic loads it itself.
- A test that fails because of your change means fixing the code, not the test; change a test only when the requirement changed, and say so. After three attempts at the same failure, stop, rethink the approach, and write down what you tried in the handoff.

## 5. Verify on Odoo.sh when needed

Local runs use Odoo Community, plus Enterprise when `project.json` points to its source. When `oh test` says **blocked**, or the behaviour depends on production data, push the feature branch: Odoo.sh builds it with a fresh database, demo data and the tests. One build per milestone at most; iterate locally and let the build confirm. Read the result from the commit status when the project reports it to GitHub, otherwise ask the user for the build status or the failing log lines (`references/odoo-sh.md`).

## 6. Review and deliver

- M and L changes get an independent review before they are done. In Claude Code, give the `odoo-reviewer` agent the acceptance criteria and the base branch; it reads the code and the evidence and can't change them. Fix what it finds in the same session, in one pass, and re-run only the changed module. A blocking finding (behaviour, security, data safety) gets a re-review of the fix: give the reviewer the commit of its first review so it reads only what changed since. Elsewhere, review in a fresh session with the `odoo-review` skill (independent, read-only not enforced: say so); a review in your own session is a self-review and is called that.
- `odoo-scout` answers a broad question about standard Odoo without filling your context. Subagents start without your context: don't use them for S changes or for implementation, and run one at a time.
- UI changes are checked on verified screenshots in English and Arabic (`references/views-ui.md`): only images marked `ok` count. Shoot only the screens whose view, layout or wording changed. Look at the contact sheet first, then open the full Arabic image of each changed screen (the English one only where its layout differs); don't claim a layout works without seeing it.
- Update the feature notes (`assets/feature.md` as the template, in proportion to the size of the change). Delivering into an integration branch (`base_branch`) follows the merge step in `references/delivery.md`, which also says where status is kept. Then commit the code, the notes and `.odoo-harness/evidence/` to the feature branch and push it. `oh evidence` must show each record intact and matching the committed source. Never push to or merge into the production or staging branch; the user promotes on Odoo.sh.
- Final report: what changed; the results (local and/or Odoo.sh, with counts and the evidence records); the review (independent, or self-review); the outcome (**completed**, **blocked** or **not verified**); and anything the user must do (merge, configure, check data).

## 7. Short sessions and handover

Work one milestone per session: a long session carries its whole history on every turn and uses up the user's limit. Hand over when a milestone is done, when the user asks, or when the session has grown long and a stopping point is near. In Claude Code a Stop hook holds a stop with uncommitted or unpushed work once: hand over before stopping, or say in one line why the work stays uncommitted.

1. Bring the work to a clean point: the tests for what you changed pass, or the failure is written down.
2. Overwrite the handoff (`.odoo-harness/HANDOFF.md`, or on a feature branch with an integration branch the `handoff.md` next to the feature notes; `references/delivery.md`). At most 45 lines and 4 KB, the active track only: milestones with their state, the exact next action, evidence, decisions the user gave that aren't in the feature notes yet, and what failed. Finished work belongs in the status file (`status_file`) and durable facts (gotchas, assumptions) in the feature notes, never in the handoff. The Stop hook holds a stop once when a handoff is over the limit.
3. Commit the code, the evidence and the handoff, and push the feature branch. `git status` is clean and `git rev-parse HEAD` equals `git rev-parse origin/<branch>`.
4. End your reply with the prompt for the next session in a code block, and put the same prompt in the handoff:
   ```
   Resume <owner/repo> on branch <branch> at <short commit> from <handoff path>.
   Milestone <n> of <total>: <name>. Next action: <exact step>.
   <anything the user must do or decide first; otherwise omit this line>
   ```
   Below it, tell the user in one or two lines: start the new session on that repository and branch, and the effort to use (`medium`; `high` only for a hard milestone or after a failed attempt).

When resuming: read the handoff named in the prompt, check that `git rev-parse --short HEAD` is the commit in the prompt (fetch the branch if it isn't; if it still differs, stop and tell the user), run `oh evidence`, then continue from the next action. What the handoff records as done is done; re-test it only when the next action needs it.

## References

| File | Read it when |
|---|---|
| `references/odoo19.md` | before writing Odoo 19 Python or XML |
| `references/testing.md` | every `oh` command and option; planning and writing tests; reading results |
| `references/security.md` | new models, groups, record rules, multi-company, `sudo`, controllers |
| `references/views-ui.md` | views, actions, menus, Owl/JavaScript, assets, tours, screenshots |
| `references/data-migrations.md` | changing a deployed module: stored fields, data files, migration scripts |
| `references/reports.md` | QWeb/PDF reports, dashboards, KPIs and any figure users will compare |
| `references/i18n-rtl.md` | user-facing text, Arabic translations, right-to-left layout |
| `references/delivery.md` | the end of a milestone, the merge into the integration branch, the handoff and the status file |
| `references/odoo-sh.md` | branches, builds, deployment, logs, verifying Enterprise-dependent code |
| `references/design.md` | L-size work or unclear business flows |
