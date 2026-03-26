# 5) Repo Structure Adjustment (Incremental, Not Rewrite)

## Keep

- Existing `addons/` root and `adams_base` bootstrap module.

## Add (recommended)

- `addons/shopify_connector/`
  - `models/` (instance config, mapping state, sync state)
  - `services/` (GraphQL client, sync services)
  - `controllers/` (webhook endpoints)
  - `data/` (cron jobs, security defaults)
  - `security/` (ACL, record rules)
  - `tests/` (unit/integration contract tests)
- `docs/ai-agents/` (this governance package)
- `docs/adr/` (architecture decisions)
- `docs/runbooks/` (ops + incident handling)

## Why this structure

- Keeps functional code in Odoo module conventions.
- Separates governance artifacts from runtime code.
- Supports scale (new sync domains) without restructuring later.

## Migration Path

1. Create connector module skeleton.
2. Move integration code by domain slice (products, customers, orders).
3. Add tests and runbooks per slice.
4. Retire temporary scripts once services are stable.
