# STATUS.md

Updated: 2026-06-12 overnight window (3d committed; 3e in progress)

## Resume here (fresh session)
1. Read MORNING_REVIEW.md (overnight governance: retroactive
   touchpoint 2, consequence statements queued there).
2. Environment is EPHEMERAL — rebuild per CLAUDE.md Environment recipe
   (~20 min: clone odoo 19.0, pip quirks incl. cffi, PG role root,
   profiles adams_strict1 + adams_strict_vat). Baselines on rebuilt env
   (core b4c7247f): strict1 0/0 of 557, strict_vat 2/0 of 557 (known
   AUD-001 pair).
3. SSH to Odoo.sh: IMPOSSIBLE from session containers (platform
   HTTP/HTTPS-only proxy) — never re-test; all Odoo.sh checks relay
   through Ahmed (6 batched commands in FINALIZE.md).
4. Current item: 3e — taxesIncluded/VAT-inclusive core (clears the 2
   strict_vat baseline failures). Design settled (see MORNING_REVIEW.md
   §3): fetch Order.taxesIncluded (verified Boolean! in 2026-01 API) in
   both GraphQL queries + simulator emission; flavor-aware fallback
   (prefer tax whose effective price_include matches store semantics);
   generic price_unit flavor-alignment at line creation (convert price
   when ALL resolved taxes are percent + uniform flavor ≠ store
   semantics; else leave — guard backstops); legacy payloads without
   the flag = exclusive (Shopify default). Then 3f docs sweep, then
   FINALIZE items 4, 5, then Tier 2.

## State
- Committed+pushed on claude/determined-cori-glvysk: items 1, 2, 3a,
  3b, 3c (have Ahmed's go) and 3d (b012e65+17a55bd, PENDING RETROACTIVE
  GO). All pending Odoo.sh confirmation (Ahmed relays).
- GREEN BUILD: local proxy complete, zero (a)-class (FINALIZE.md);
  Odoo.sh leg queued for Ahmed.
- PostgreSQL stops between sessions: `pg_ctlcluster 16 main start`.

## Open questions for Ahmed
- Morning: retroactive go/no-go per MORNING_REVIEW.md §1; relay the 6
  Odoo.sh confirmation commands; consider an environment setup script
  (MORNING_REVIEW.md §5 step 5).
