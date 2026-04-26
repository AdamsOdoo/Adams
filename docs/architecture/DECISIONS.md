# Architecture Decisions Log

| ID | Date | Decision | Rationale | Made By | Status |
|----|------|----------|-----------|---------|--------|
| DEC-001 | 2026-03-26 | Use binding model pattern for all synced entities | Industry standard for Odoo connectors (OCA connector framework pattern), supports idempotency, allows per-record sync state tracking | Technical Architect | Active |
| DEC-002 | 2026-03-26 | Use Shopify GraphQL Admin API (not REST) | Better performance (request only needed fields), native support for bulk operations, Shopify's recommended and most maintained API | Technical Architect | Active |
| DEC-003 | 2026-03-26 | Use checksum-based change detection for exports | Prevents unnecessary API calls, reduces Shopify rate limit consumption, makes sync truly idempotent without relying on write_date alone | Technical Architect | Active |
| DEC-004 | 2026-03-26 | Process webhooks asynchronously | Shopify requires 200 response within 5 seconds; complex processing (record creation, validation) exceeds this; async processing via cron/queue ensures reliable webhook acknowledgment | Technical Architect | Active |
| DEC-005 | 2026-03-26 | Verify all webhooks with HMAC-SHA256 | Shopify standard for webhook security; prevents forged webhook attacks; uses timing-safe comparison | Technical Architect | Active |
| DEC-006 | 2026-03-26 | Orders are import-only (Shopify→Odoo) for MVP | Bidirectional order sync requires complex state machine (fulfillment, payment, refund states); MVP focuses on reliable order capture into Odoo for fulfillment | Solution Architect | Active |
| DEC-007 | 2026-03-26 | Exponential backoff for API retry with jitter | Shopify uses leaky bucket throttling; exponential backoff with jitter prevents thundering herd on rate limit recovery | Technical Architect | Active |
| DEC-008 | 2026-03-26 | Separate Shopify API layer from Odoo models | Clean architecture principle; API layer has no Odoo ORM dependency; testable in isolation; replaceable if Shopify changes API format | Technical Architect | Active |
| DEC-009 | 2026-03-26 | Use abstract binding model as base | DRY principle; common fields (backend_id, shopify_id, sync_checksum, last_sync_date, sync_status) defined once, inherited by all entity bindings | Technical Architect | Active |
| DEC-010 | 2026-03-26 | Company-scoped backends with record rules | Multi-company support from day one; prevents data leakage between companies; required for Odoo marketplace acceptance | Technical Architect | Active |
