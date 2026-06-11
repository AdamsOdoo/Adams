# STATUS.md

Updated: 2026-06-11 (session: items 3b, 3c + GREEN BUILD intake)

## Done this session
- ITEM 3b (AUD-016 explicit zero-tax lines): committed + pushed on go.
- ITEM 3c (AUD-015 shipping tax resolution): fail-before committed
  (4f/0e of 13), fix implemented and verified (pass-after 0/0 of 24;
  strict1 full 0/0 of 552; strict_vat 2/0 of 552 = unchanged AUD-001
  baseline). Fix diff HELD uncommitted (order_sync.py +
  queries/order.py) awaiting touchpoint-2 go.
- Simulator: shipping lines emit taxLines; fidelity guard extended.
- GREEN BUILD standalone item recorded in FINALIZE.md; tier-checkpoint
  build-log rule added to CLAUDE.md. Sequenced 3c → GREEN BUILD → 3d.
- SSH verified still BLOCKED from this container (TCP timeout to
  adamsmen.dev.odoo.com:22; DNS ok). Policy changes + ODOO_SH_SSH_KEY
  env var reach NEW session containers only — retest at next session
  start. Odoo.sh confirmations (5 batched commands in FINALIZE.md)
  still pending.

## Next
- On go: commit 3c, then GREEN BUILD (local install-log proxy first;
  SSH log pull when available), then 3d (rate fallback flavor +
  dropped-tax visibility), 3e (taxesIncluded/VAT-inclusive core), 3f
  (docs sweep). Then items 4-5, then Tier 2 resume.

## Open questions for Ahmed
- Go/no-go on 3c consequence statement (in chat).
- SSH: confirm network policy allows outbound 22 + ODOO_SH_SSH_KEY env
  var is set in the environment config, then next session verifies.
