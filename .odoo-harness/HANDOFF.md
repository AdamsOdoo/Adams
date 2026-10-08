# Handoff

Active track only (at most 45 lines and 4 KB). Finished work goes in the build log and the status file (`docs/tracking/TASKS.md`); git keeps the history.

- Goal: the single module `executive_dashboard` ("Executive Dashboard"), plug and play on any Odoo 19 (Odoo.sh Enterprise) database.
- Read first: `docs/executive-dashboard/implementation-brief.md`, `docs/executive-dashboard/build-log.md` (phase notes, owner decisions, "Verify on Odoo.sh", and "Working notes": framework, local test setup, verification policy, tried and failed), `docs/executive-dashboard/ux-improvement-plan-20260925.md` (rev 3) and `docs/executive-dashboard/reference/executive-360-concept.html` (visual source of truth; Needs attention = `attention`, Definitions = drawer `definitions`).
- Branches: feature work on `feature/executive-dashboard-phase1`; integration branch `dev` (`base_branch`). Never push to main, staging or test. UAT branch `uat/executive-dashboard` is refreshed from the feature branch (build log, "UAT candidate").
- Harness and Odoo: odoo-harness 1.4.0 @ 256dd4ee7571; Odoo 19.0 @ 8d05257d83f9 (Community locally; Enterprise-only parts verified on Odoo.sh).
- State: Phases 1–5, owner feedback rounds 1–2 (19.0.1.8.0) and Key metrics (19.0.1.9.0, branch `claude/upbeat-fermat-k3eic8`) are done; see the build log. Open Odoo.sh checks are listed there.
- Next action (Phase 6, Needs attention): add `get_attention()` to `addons/executive_dashboard/models/dashboard.py` (public-method pattern: `_authorize()`, then `_elevated()`), returning items `{severity: crit|warn|info, title, sub, value, section, drawer: {key, args}}` ranked by severity then value, only from sections whose `_section_status` is `ok`, reusing existing helpers:
  - late deliveries `_inv_pickings_summary(scope, 'outgoing', 'late', 0)` (or `_key_otif_orders` for late orders); late receipts `_inv_pickings_summary(scope, 'incoming', 'late', 0)`;
  - POs to approve `_pro_orders_kpi(scope, _pro_approve_domain(scope))`;
  - receivables over 90 days and vendor bills due in 7 days from the Finance journal-item helpers in `models/sections/finance.py` (reuse the Expected/Aged buckets);
  - employees not checked in (active minus checked-in minus on time off today, only when `_ppl_can('attendance')`; new drawer `people.not_in`);
  - opportunities past `date_deadline` (`oh src "date_deadline = fields" --module crm`).
  Each item opens its section's existing drawer. Then the client side-panel (rail and topbar buttons), a test per item against the native count, one query-count limit.
- After that: Definitions (with the invoice-date line: Invoice Analysis uses the invoice date and can differ at month ends), search model list in Settings, performance tests (payload < 300 ms, drawer < 200 ms), Arabic review, phone check, final `odoo-reviewer` pass.
- Owner decisions still open: none for Phase 6.
