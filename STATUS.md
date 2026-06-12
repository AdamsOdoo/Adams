# STATUS.md

Updated: 2026-06-12 overnight window (items 3d, 3e, 3f, 4 committed;
item 5 verification in flight)

## Resume here (fresh session)
1. Read MORNING_REVIEW.md (overnight governance: retroactive
   touchpoint 2, consequence statements queued there) and the item
   table in FINALIZE.md.
2. Environment: container restarts may keep the disk (check before
   rebuilding: /home/user/odoo + pip deps + PG cluster with
   adams_strict1/adams_strict_vat survived the 2026-06-12 ~21:00
   restart; only `pg_ctlcluster 16 main start` was needed). Full
   rebuild recipe in CLAUDE.md Environment if the disk is fresh.
3. IF item 5 is still uncommitted (check `git status`): the fixes are
   complete in the working tree (refund_sync.py, account_move.py +
   docs); fail-before bd491b2 is pushed; pass-after was 0/0 of 11
   (TestRefundIdempotency, TestOverRefundGuard, TestRefundCreditNote,
   strict1). Re-run BOTH full suites (expect 0/0 of 576 each), fill
   counts in FINALIZE.md item-5 trail + MORNING_REVIEW.md, commit
   "fix(P2-item5): ... — PENDING RETROACTIVE GO", push.
4. Then: Tier 2 (data integrity & security audit) — findings to
   AUDIT.md, fixes under standing approval, money-path into the
   retroactive flow (until Ahmed returns).
5. SSH to Odoo.sh: IMPOSSIBLE from session containers (platform
   HTTP/HTTPS-only proxy) — never re-test; 9 batched confirmation
   commands in FINALIZE.md for Ahmed to relay.

## State
- Pushed on claude/determined-cori-glvysk: items 1, 2, 3a-3c (have
  go), 3d (b012e65+17a55bd), 3e (cd1bfd3+58af690), 3f (707cca9),
  item 4 (52a268c+18fa21e), item-5 fail-before (bd491b2). 3d/3e/4
  PENDING RETROACTIVE GO; all pending Odoo.sh confirmation.
- MILESTONE: both strict profiles fully green since 3e (562/562 → 572
  with item 4) — first-ever green strict_vat (AUD-001 pair cleared).
- GREEN BUILD: local proxy complete, zero (a)-class; Odoo.sh leg
  queued for Ahmed (MORNING_REVIEW.md §5).
- Local baselines (rebuilt env, core b4c7247f): pre-overnight
  strict1 0/0 of 552, strict_vat 2/0 of 552; current expected 0/0 of
  576 both after item 5.

## Open questions for Ahmed
- Morning: retroactive go/no-go per MORNING_REVIEW.md §1 (3d, 3e,
  item 4, item 5); relay the 9 Odoo.sh confirmation commands; consider
  an environment setup script (MORNING_REVIEW.md §5 step 5).
