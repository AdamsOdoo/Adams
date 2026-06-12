# STATUS.md

Updated: 2026-06-12 end of overnight window (all FINALIZE items + first
Tier 2 pass landed)

## Resume here (fresh session)
1. MORNING FIRST: Ahmed reads MORNING_REVIEW.md — retroactive
   go/no-go on 3d, 3e, item 4, item 5, Tier 2 fixes (§1, each with
   revert command); relay the 9 Odoo.sh confirmation commands
   (FINALIZE.md batch); AUD-026 decision (§4).
2. Environment: check disk first (`ls /home/user/odoo`, `psql -l`) —
   a mid-window container restart KEPT the disk (only
   `pg_ctlcluster 16 main start` needed). Full rebuild recipe in
   CLAUDE.md Environment if fresh.
3. Current baselines (core b4c7247f): adams_strict1 0 failed,
   0 errors of 578; adams_strict_vat 0 failed, 0 errors of 578 —
   BOTH GREEN (first green strict_vat since 3e cleared AUD-001).
4. Next work: continue Tier 2 — (a) positional variant-matching lead
   (product_sync.py:240, Tier 1 deferral, needs call-context
   verification vs the SKU path at :449); (b) concurrency pass
   (parallel cron/webhook races beyond the advisory-lock surfaces
   already verified clean); then Tier 3 per the original tier plan.
5. SSH to Odoo.sh: IMPOSSIBLE from session containers (platform
   constraint, CLAUDE.md Environment) — never re-test.

## State
- Pushed on claude/determined-cori-glvysk through aabd0f0. Overnight
  commits (all PENDING RETROACTIVE GO): 3d b012e65+17a55bd,
  3e cd1bfd3+58af690, 3f 707cca9, item 4 52a268c+18fa21e,
  item 5 bd491b2+15ea94a, Tier 2 5bdfc40+db545cb.
- FINALIZE Phase-2 fix sequence (items 1-5, tax workstream 3a-3f):
  COMPLETE locally. GREEN BUILD local proxy: zero (a)-class.
- AUDIT: AUD-001..025 all fixed/closed except AUD-009/010/014/026 +
  ENV-1 (open, re-prioritized later); Tier 2 header lists verified-
  clean surfaces.

## Open questions for Ahmed
- MORNING_REVIEW.md §1 go/no-gos, §4 AUD-026, §5 SSH/setup-script.
