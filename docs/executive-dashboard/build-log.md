# Executive Dashboard — build log

One line per phase (date, commit, tests run, result), then that phase's notes.

| Phase | Date | Commit | Tests | Result |
|---|---|---|---|---|
| 1 | 2026-09-25 | `c1b9a3a2` | `oh test executive_dashboard`: 12 run, 12 passed (Community, demo). `oh shot /odoo/executive` EN + AR desktop: 2/2 ok. Extra local browser check at 1440 / 1024 / 390 px: no horizontal overflow | **completed** locally; dark mode not verified (Enterprise) |

## Phase 1 notes

- Client action path is `/odoo/executive` (`/odoo/executive-dashboard` belongs to the old module until Phase 6).
- The search RPC is `global_search`, not `search`: `search` would override the ORM method on the model.
- Section cache key also holds the user id (the brief lists groups only): record rules such as "own documents only" depend on the user, so users never share an entry.
- Year to date starts at the company's fiscal year start (`compute_fiscalyear_dates`).
- No `ir.model.access.csv`: the module adds no stored model (the dashboard is an AbstractModel; settings are fields on `res.company`).
- Welcome search is already live (name search, 5 per model, record rules); Phase 6 still owns the configured model list, Needs attention and Definitions.
- Report-line overrides in Settings are left for Phase 2 (Finance), where they are used.
- Not ported from the reference page: the language and theme switches (Odoo's user settings decide both), and the IBM Plex web font (no external font request; falls back to the web client font).
- Odoo runs rtlcss on the Arabic bundle, so the reference's `[dir=rtl]` overrides of physical properties (drawer slide, tab padding) were dropped; they would have flipped twice.
- An uninstall test is not written yet; the uninstall steps come in Phase 6.

## Verify on Odoo.sh (Enterprise)

- Dark mode (only `web_enterprise` builds the dark bundle).
