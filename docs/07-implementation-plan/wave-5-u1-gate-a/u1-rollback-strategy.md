# Wave 5 U1 — Rollback Strategy

> **Status: Gate A planning artifact — Docs-only. NOT accepted.** Produced
> 2026-07-23. Rollback plan for the future U1 code batch and for this Gate A
> docs branch.

## 1. Why rollback is cheap for U1

U1 adds only **views/menus/actions + one display-and-delegate `TransientModel`
wizard + tests + docs** inside `shopify_connector_fulfillment`. It changes **no**
business model, **no** stored field, **no** ACL on a persistent business model
(only a wizard TransientModel row), and creates **no** job/mutation/selection
value. It therefore has no data-migration footprint and no irreversible effect.

## 2. Code-batch rollback (when U1 is implemented)

- **PR-level:** U1 lands as one draft PR — reverting the merge commit removes the
  entire U1 slice atomically (DEC-040 independently-revertable batch).
- **Module-level:** uninstalling/upgrading-down `shopify_connector_fulfillment`
  drops the U1 `ir.ui.view`/`ir.ui.menu`/`ir.actions.*`/wizard records (Odoo
  removes module-owned records). The **Wave 4 backend is unaffected**; the
  existing LC-1 job-type/trigger-origin uninstall normalization is untouched
  (U1 adds no job type).
- **No data loss:** business records (pickings, orders, bindings, evidence, jobs,
  logs, mutation attempts) are owned by Wave 4 / core models with
  `ondelete='restrict'` links; U1 views hold no data. Removing U1 removes screens,
  not records.
- **Partial rollback:** any single view file can be reverted independently; the
  wizard can be removed by dropping its file + manifest data entry + ACL row
  without touching the read-only views.

## 3. Failure-mode responses

| Failure | Response |
|---|---|
| A U1 view fails Odoo-19 validation on install | Revert that view file; re-apply after fixing the idiom (U0 lessons: plain `<group>` group-by, `id` not `active_id`, expression `invisible=`) |
| A button reaches a server call not denied for its role (UI/ACL disagreement) | Hard stop (wave-5 hard-stop 9); fix the `groups=`/gate; the server method remains the security control regardless |
| The wizard is found to compute a mode decision or mutate | Remove the offending logic — the wizard must delegate only; if unfixable, drop the wizard and fall back to a static `confirm=` button |
| Regression in the Wave 4 or U0 suites with U1 installed | Revert the PR; U1 must be additive-only |

## 4. This Gate A docs branch rollback

`claude/wave-5-u1-gate-a` is **docs-only**. Rollback = close the draft PR /
`git revert` the docs commit; nothing installs, migrates, or runs, so there is no
runtime or data effect. The read-only Wave 4 worktree used for inspection is a
scratch artifact outside the repo tree and leaves no trace in the branch.

## 5. Non-negotiables preserved on any rollback

- `checkpoint/core-r2-readonly-uat-2026-07-15` is never touched.
- CV-013 (#185) and the nine-process concurrency obligation remain open regardless
  of U1 state.
- No U1 rollback path performs a Shopify request or mutation.
