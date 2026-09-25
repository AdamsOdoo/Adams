# Handoff

Current state of in-progress work, for the next session or the other model. Overwrite it; don't append history (git keeps it). Keep it under about 40 lines.

- Goal: build the new single module `executive_dashboard` ("Executive Dashboard") to the agreed redesign, plug and play on any Odoo 19 (Odoo.sh Enterprise) database.
- Start by reading: `docs/executive-dashboard/implementation-brief.md` (what, how, phases), then `docs/executive-dashboard/ux-improvement-plan-20260925.md` (rev 3), then `docs/executive-dashboard/reference/executive-360-concept.html` (visual source of truth).
- Branch: create a feature branch from `feature/executive-dashboard-report-first` (docs live there). Never push to main, staging or test.
- Harness and Odoo: odoo-harness 1.2.1 @ 176f07317e5a; Odoo 19.0 @ 8d05257d83f9 (Community locally; Enterprise-only parts verified on Odoo.sh).
- Done: design and plan agreed with the owner (3 review rounds). No module code for the redesign yet.
- Next action: Phase 1 in the brief (module skeleton, security, shell, Welcome, side panel, get_section framework).
- Verification policy (owner): light. oh src before APIs; oh test per phase; one oh shot per phase (EN/AR); no ledgers, sweeps or evidence bundles; build-log line per phase; odoo-reviewer after Finance and at the end.
- Old modules `adams_executive_dashboard` and `adams_dashboard_finance` (19.0.1.8.0, draft PR #214) stay untouched until Phase 6 (data move + uninstall on a staging copy).
- Owner decisions still open: none for Phase 1.
- Tried and failed (don't repeat): Community `web.assets_web_dark` does not make pages dark (only web_enterprise sets the dark scheme); `:dir(rtl)` never matches in the Odoo web client (use `body.o_rtl` / `[dir=rtl]`); running browser checks in parallel with Arabic checks corrupts both (they switch the admin language).
