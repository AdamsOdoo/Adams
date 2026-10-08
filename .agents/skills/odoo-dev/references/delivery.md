# Delivery: milestones, the merge step and status

Read this at the end of a milestone and before merging into the integration branch. The integration branch is `base_branch` in `.odoo-harness/project.json` (for example `dev`): it doesn't deploy, and the user promotes it to staging and production on Odoo.sh. Without an integration branch, a delivery is the feature branch the user merges: run the merge step's tests there.

## During a milestone

- **Questions:** ask all of a milestone's business and layout questions, and the approval, in one round. Before building, check that the work the milestone depends on is in the integration branch; if it isn't, say so in your first reply and stop.
- **Tests:** iterate with `--tags … --no-record`. At the end of the milestone, run the changed module once with `--require` for its criteria, plus `--with-dependents` when other project modules build on it. `oh test --all` and upgrade runs belong to the merge step. The one exception is a milestone that adds a migration script: run `--upgrade-from` once on the changed module to check the script.
- **S changes** (a label, a translation, spacing, a straightforward view change): one recorded run of the affected tests with `--tags`. No `--with-dependents`, no upgrade run, no independent review. The record is partial: the module's other tests run in the merge step. A change to data, a stored field, a migration, money or access rights is at least M, however small the diff.
- **Screenshots:** only the screens whose view, layout or wording changed. Open the right-to-left image of each one; open the English image only where the layout differs or the change is about English wording. Keep every behaviour test (one per criterion, plus denied access): the budget is on repeated runs and images, not on tests.
- **Review (M and L):** one independent review after the tests pass. Fix every blocking and should-fix finding in the same session, in one pass, re-run the changed module once (not `--all`, no upgrade run), and ask for one re-review of the blocking fixes.

## Handoff and status

- **One status file.** `status_file` in `project.json` (a markdown table with a Status column) is the only place that says what is done and what is left. Other documents link to it instead of repeating it. `oh status` counts its rows by status; `oh status --html <path>` renders it as one page (light and dark) to publish or share. When the user wants that page, publish the rendered file; don't keep a second status page by hand.
- **The handoff is the active track only.** At most 45 lines and 4 KB: the milestones in flight, the exact next action, what failed, and decisions not yet written anywhere else. Finished work goes in the status file and the feature notes, never in the handoff; git keeps the history. The Stop hook holds a stop once when a handoff written in the session is over the limit.
- **Where the handoff goes.** With an integration branch, a feature branch hands over in a `handoff.md` next to its feature notes, and the next-session prompt says "from <that path>". `.odoo-harness/HANDOFF.md`, the status file and other shared status documents change only on the integration branch, in the merge step, so feature branches don't conflict on them. Without an integration branch, use `.odoo-harness/HANDOFF.md`.

## The merge step (one branch at a time)

1. Merge `origin/<integration>` into the feature branch.
2. Start `oh test --all` and the upgrade run(s) together, both in the background. `--all` takes up to 3 processes and an upgrade run one, which fills a 4-CPU machine, so the step takes about as long as the longer run. Run any further baseline after them, or lower `--jobs`.
   - Upgrade from `origin/<production>`. Upgrade from a staging branch too only when it differs from production in a changed module or in one of their project dependencies: `git diff --quiet origin/<production> origin/<staging> -- $(oh deps)` fails. Only use that check after `oh deps` has succeeded and printed paths. A branch that changes no module needs no upgrade run. Each record names its baseline (`upgrade-<modules>-from-origin-<branch>`).
3. Run `oh evidence --prune-stale`, check its verdict, and commit the deletions with the evidence, so the integration branch carries only the records that still prove something.
4. Update the shared status on the integration branch: the status file's rows, `.odoo-harness/HANDOFF.md` (what is active now, short), and the project's open questions. Then merge into the integration branch and push it straight away.
5. If the integration branch moved in the meantime, merge it again. Re-run `--all` only when the new commits change what the tests run against: `git diff --quiet <last merged>..origin/<integration> -- <addons paths> requirements.txt .odoo-harness/project.json` fails. A move made only of documents, evidence or other harness files doesn't invalidate the run.

**Conflicts in evidence records:** for the `test-…` record that the post-merge `--all` rewrites, keep the branch's side (`git checkout --ours -- <record and its folder>`). For any other record (`upgrade-…`, `shot-…`), keep the side with the later `finished` time. `git add` them; `oh evidence` must then show no problem.

**Harness updates** go into the integration branch only when no branch is in its merge step. Each branch takes them when it next merges the integration branch, not mid-milestone.
