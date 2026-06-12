# COVERAGE.md — Coverage Scaffold

> **SCAFFOLD — population is Goal 6.**

Purpose: **unmapped = untested = not done**.

This file will become the coverage map for workflows, buttons, crons, webhooks, negative paths, security paths, accounting paths, and UI paths. Goal 0 creates only the scaffold; no rows should be fabricated.

Button enumeration must come from XML views, not memory.

## Coverage Table Schema

| Surface | Type: workflow/button/cron/webhook/negative/security/accounting/ui | Test file::method | Profile | Status | Evidence |
|---|---|---|---|---|---|

No coverage rows are populated yet because Goal 6 owns verified population.

## Goal 1 identified coverage debt

Population remains Goal 6; this list only flags Goal 1 contract paths where no direct test citation was found during code reading.

- Setup → onboarding wizard connection/backend/webhook/import error visibility needs direct tests.
- Initial product import → SKU match, option/index variant matching, image failure, and binding idempotency need direct tests.
- Product update Odoo → Shopify → productSet/productUpdate/variant bulk update and export error marking need direct tests.
- Inventory sync → location/warehouse mapping, compareQuantity stale failure, and binding update need direct tests.
- Product deleted/archived → archive/delete lifecycle not specified or tested.
- Settings changed after go-live → DEC-020 lock/unlock/validation gap needs tests after implementation.
- Unpaid/pending Shopify order → transition table and activity/error behavior need direct tests.
- Missing product on order import → unresolved product-line policy needs direct tests after decision.
- Missing tax mapping → dropped-tax activity and guard interaction need direct tests.
- Currency/rate missing → visible error-state binding and retry path need direct tests.
- Payouts → payout import, transaction type fallback, missing currency, and accounting decision need tests.
- Reconciliation → mismatch sync-log creation and retry reset need tests.
- Shopify fulfillment → Odoo delivery → inbound modes, partial fulfillment limitation, and auto-validation failure need tests.
- Shopify refund → Odoo credit note → refund GID recovery, currency mismatch, over-refund, and tax fallback need direct tests.
- Odoo credit note → Shopify refund → reverse refund push, failure activity, and idempotency policy need tests.
- Abandoned cart → quotation → quote creation, unresolved product note line, currency pricelist fallback, and tag gap need tests.
- Gift cards → import/update/error handling and future liability behavior need tests.
- Promoters/discounts → discount export/import and promoter linkage need tests.
- Metafields → mapping import/export and conflict behavior need tests.
- Multi-store → backend-scoped binding/webhook isolation needs tests.
- Multi-company → company context and record-rule behavior needs tests.
- Shopify Markets/B2B → presentment currency behavior and B2B-specific gaps need tests.
- Duplicate webhook → per-backend webhook ID dedup, fingerprint fallback, stale payload, and dead-letter retry need tests.
- API throttling → rate limiter adaptation, Retry-After, circuit breaker, and sanitized errors need tests.
