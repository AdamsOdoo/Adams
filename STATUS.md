# STATUS.md

Updated: 2026-06-12 — green-build loop with Ahmed in progress

## Current goal (Ahmed, 2026-06-12): GREEN ODOO.SH BUILD
Everything else paused until a green Odoo.sh build of `review/full-audit`
exists. Governance simplified same day: all five overnight retroactive
GOs approved; money-path now under standing approval (consequence
statements recorded in FINALIZE.md); two touchpoints remain (Odoo.sh
relay, human test). MORNING_REVIEW.md retired.

## State
- Branch consolidation DONE: PR #16 merged the entire project into
  `review/full-audit` (13f28cf). Old branches (main/dev/staging/feat/
  hardening/design-*) verified contained or pre-reset; nothing to salvage.
- Odoo.sh build failure DIAGNOSED + FIXED: ENV-1, now 5 chart-provided
  pieces bootstrapped by the test mixins (company country, tax group,
  bank journal, company income account, ir.default partner
  receivable/payable). Commits 2d88344, e39aebc, 4888f38 + PR #17/#18.
- Build-log NOISE SWEEP done (4888f38 + residual commit): payment-path
  fixtures mock the Shopify boundary (_mock_backend_api_client),
  intentional-error tests mute their asserted loggers. Chartless
  install log now has ZERO ERROR-level lines from our modules;
  ~55 WARNING lines remain (asserted negative-test messages,
  documented expected class).
- Verification (core b4c7247f, after sweep): chartless fresh 0 failed,
  0 errors of 578; adams_strict1 0/0 of 578; adams_strict_vat 0/0
  of 578.
- Awaiting: Ahmed rebuilds review/full-audit on Odoo.sh, pastes log.
  Loop until green. Once green: run-down report (fixed-so-far in
  merchant terms, verified vs pending-Odoo.sh, milestone gaps M1-M3,
  zero-knowledge test script) + the 9 confirmation commands
  restructured into web-shell paste blocks (FINALIZE.md has them).

## Next work after green build
- Tier 2 remainder: positional variant-matching lead
  (product_sync.py:240 vs SKU path :449), concurrency pass.
- Open: AUD-009/010/014/026 (AUD-026 = payload PII decision, Ahmed).
