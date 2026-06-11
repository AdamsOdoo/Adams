# STATUS.md

Updated: 2026-06-11 (session end: 3b + 3c committed; next = GREEN BUILD)

## Resume here (fresh session)
1. FIRST: verify SSH — `ODOO_SH_SSH_KEY` env var should now exist
   (write it to ~/.ssh/id_ed25519, chmod 600) and outbound 22 should be
   open (policy changed; applies to new containers). Connect line:
   `ssh 33403099@adamsmen.dev.odoo.com` (build id may have changed —
   it's the build of claude/admiring-bell-e9g6qp). No ssh client in
   the container image: install openssh-client or use paramiko.
2. If SSH works: run the 5 batched Odoo.sh confirmation commands in
   FINALIZE.md (items 1, 2, 3a+guard, 3b, 3c) — expect 0/0 of
   3 / 6 / 6 / 2 / 13 — and report literal counts to Ahmed.
3. Then run the GREEN BUILD item (FINALIZE.md, full spec there):
   pull build log via SSH, classify ERROR/WARNING a/b/c, fix all (a)
   under rules 1-6, NEVER suppress/filter logs, money-path fixes need
   touchpoint-2 go. Local prep allowed: fresh-install log proxy.
4. Then resume tax workstream: 3d (rate-fallback amount_type +
   deterministic ordering + dropped-tax visible activity), 3e
   (taxesIncluded/VAT-inclusive core — clears the 2 strict_vat baseline
   failures), 3f (docs sweep + final matrix). Touchpoint-2 statement
   before each commit.

## State
- Committed+pushed: items 1, 2, 3a, 3b, 3c (all pending Odoo.sh
  confirmation). Working tree clean.
- Local baselines (2026-06-11): adams_strict1 0 failed, 0 errors of
  552; adams_strict_vat 2 failed, 0 errors of 552 (known AUD-001 pair:
  TestOrderImport.test_import_taxed_order_creates_invoice_with_tax_lines,
  TestTaxedRefundE2E.test_taxed_partial_refund_e2e_through_simulator —
  both clear at 3e).
- PostgreSQL stops between sessions: `pg_ctlcluster 16 main start`.

## Open questions for Ahmed
- None blocking; Odoo.sh confirmations report when SSH verified.
