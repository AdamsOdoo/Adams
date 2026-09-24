# Handoff

Current state of in-progress work, for the next session or the other model. Overwrite it; don't append history (git keeps it). Keep it under about 40 lines.

- Goal: finish the Odoo 19 Executive Dashboard to the approved HTML (Astra design + HR/branding addendum) for owner testing; PR #214 stays draft.
- Acceptance criteria: RC1–RC14 in `docs/executive-dashboard/completion-20260925/root-causes.md`, each with its regression test or browser/bounds check; ledger `coverage-inventory.csv` (718 rows, every one with a terminal disposition); deviations D01–D18.
- Branch and head commit: `feature/executive-dashboard-report-first`, the commit that carries this handoff (modules 19.0.1.8.0). Tested addon trees: adams_executive_dashboard `82158e2b`, adams_dashboard_finance `a72ce67e`, adams_dashboard_native_tests `47f5e842` (`git rev-parse HEAD:<path>` must match).
- Harness and Odoo: odoo-harness 1.2.1 @ 176f07317e5a (`.odoo-harness/lock.json`); Odoo 19.0 @ 8d05257d83f9 (Community, local).
- Uncommitted work: none.
- Done: RC1–RC14; frontend 92/92; native tests on a fresh database (see completion README); control sweep 360/360 and drawer/dialog sweep 112/112; browser checks 66/66; role journeys 12/12; reconciliation 53/53; bounds checks 0 spills (EN 390/768/1024/1440, AR 390/1440); 70 paired captures inspected; one independent read-only review, all findings fixed or recorded.
- Remaining: Enterprise-only verification on the Odoo.sh development build of this commit (finance addon figures and drawers, Planning, dark mode, native test run with Enterprise); owner promotion to staging; owner acceptance.
- Next action (exact command or step): owner confirms the Odoo.sh development build of this commit is green, takes a staging backup, then copies only the two addon trees to staging (commands in `docs/executive-dashboard/completion-20260925/README.md`, "Owner review").
- Blocked on (who or what): owner — Odoo.sh access and the staging push (the guard protects `staging`); owner decision on HR counts for users without HR rights.
- Evidence (`oh evidence`, candidate digest …): private bundle outside GitHub (screenshots, sweep journals, logs, reconciliation, scripts) with read-back SHA-256 checksums; sanitized summaries in `docs/executive-dashboard/completion-20260925/`.
- Review: independent (single read-only reviewer) on 68566a4 + working tree; re-checks confirmed every fix; residual: Arabic group headings keep −0.25 px tracking (no visible effect; approved HTML resets only h1).
- Tried and failed (don't repeat): Community `web.assets_web_dark` does not make the dashboard dark (only web_enterprise sets `$o-webclient-color-scheme`); `:dir(rtl)` never matches in the Odoo web client (it uses `body.o_rtl`); running the sweep in parallel with the Arabic checks corrupts both (they switch the admin language).
- Assumptions awaiting the user's confirmation: none beyond the open owner decisions in the completion README.
- Outcome so far: completed for local development qualification; Enterprise surfaces not verified.
