# Quality Control & Validation Layer

## Overview

Quality is enforced at three levels:
1. **Agent-level**: Each agent follows its own standards
2. **Gate-level**: Orchestrator validates outputs between phases
3. **System-level**: Cross-cutting concerns verified across all code

---

## 1. Code Quality Standards

### Python / Odoo Standards

| Rule | Enforcement | Agent |
|------|------------|-------|
| PEP 8 compliance | Code Reviewer checks | Code Reviewer |
| OCA import ordering (stdlib → third-party → odoo → local) | Code Reviewer checks | Code Reviewer |
| Max line length: 120 chars (OCA standard) | Code Reviewer checks | Code Reviewer |
| No `print()` — use `_logger` | Code Reviewer checks | Code Reviewer |
| All user strings wrapped in `_()` | Code Reviewer checks | Code Reviewer |
| No bare `except:` — always specify exception type | Code Reviewer checks | Code Reviewer |
| No `self.env.cr.execute()` without architect approval | Code Reviewer checks | Code Reviewer |
| Methods > 30 lines should be split | Code Reviewer checks | Code Reviewer |
| No hardcoded values — use constants or config | Code Reviewer checks | Code Reviewer |

### Odoo-Specific Standards

| Rule | Why | Enforcement |
|------|-----|------------|
| Use `_sql_constraints` for uniqueness | DB-level idempotency guarantee | Technical Architect design + Code Reviewer verify |
| Use `api.constrains` for business validation | ORM-level validation | Code Reviewer |
| Use `fields.Date.context_today()` | Timezone-aware dates | Code Reviewer |
| Use `self.with_context()` explicitly | Avoid implicit context pollution | Code Reviewer |
| Use `sudo()` only when justified | Principle of least privilege | Code Reviewer |
| Never modify `ir.*` models directly | System stability | Code Reviewer |
| Use `ensure_one()` before accessing single records | Prevents silent bugs | Code Reviewer |

### SOLID Principles Application

| Principle | Application in This Project |
|-----------|---------------------------|
| **Single Responsibility** | Each model has one purpose: `shopify.backend` = config, `shopify.product.binding` = link, sync/ = orchestration |
| **Open/Closed** | Binding base model (`shopify.binding`) is extended by entity-specific bindings, never modified |
| **Liskov Substitution** | All binding models share the same interface (sync, export, import methods) |
| **Interface Segregation** | Shopify API layer exposes only query/mutate/paginate — no Odoo dependencies |
| **Dependency Inversion** | Sync engine depends on abstract binding interface, not concrete models |

---

## 2. Idempotency Verification Checklist

Every sync operation MUST pass ALL of these checks:

```
□ BINDING EXISTS CHECK
  Before creating a new Shopify record, check if a binding already exists
  for (backend_id, odoo_record_id)

□ SHOPIFY ID DEDUP CHECK
  Before creating a new Odoo record from Shopify, check if a binding
  already exists for (backend_id, shopify_id)

□ DATABASE UNIQUE CONSTRAINT
  _sql_constraints on binding model: ('unique_binding', 'UNIQUE(backend_id, shopify_id)',
  'A binding for this Shopify record already exists')

□ CHECKSUM COMPARISON
  Before calling Shopify API, compute checksum of syncable fields.
  If checksum matches stored value, skip the API call.

□ INTEGRITY ERROR HANDLING
  If unique constraint violation occurs (race condition), catch IntegrityError,
  invalidate cache, read existing binding, and proceed with update.

□ WEBHOOK DEDUP
  Store webhook event IDs (X-Shopify-Webhook-Id header).
  Skip processing if event already seen.

□ DOUBLE-RUN TEST
  Testing Agent runs every sync operation twice.
  Second run must produce zero API calls and zero new records.
```

---

## 3. Security Review Checklist

```
□ ACCESS RIGHTS
  Every model in ir.model.access.csv with appropriate group restrictions
  - shopify.backend: admin only (base.group_system)
  - binding models: Shopify Manager group
  - log models: read for Shopify User, write for system

□ RECORD RULES
  Company-scoped rules for multi-company support
  Backend records scoped to company_id

□ FIELD-LEVEL SECURITY
  access_token field: groups="base.group_system"
  Webhook secret: groups="base.group_system"

□ WEBHOOK SECURITY
  HMAC-SHA256 verification on every webhook
  Timing-safe comparison (hmac.compare_digest)
  401 response for failed verification (no details leaked)

□ TOKEN HANDLING
  Access tokens never logged (even at DEBUG level)
  Tokens not included in error messages or sync logs
  Tokens stored with field-level group restriction

□ CSRF
  Webhook controller: csrf=False (verified by HMAC instead)
  All other controllers: default CSRF protection

□ INPUT VALIDATION
  Webhook payloads validated before processing
  GraphQL responses checked for expected structure
  User inputs sanitized (especially HTML from Shopify)
```

---

## 4. Performance Standards

| Metric | Target | How Verified |
|--------|--------|-------------|
| Single product export | < 2 seconds (excluding API latency) | Testing Agent benchmarks |
| Batch export (50 products) | < 30 seconds | Testing Agent benchmarks |
| Webhook processing | Return 200 in < 500ms | Testing Agent benchmarks |
| Cron job execution | < 5 min for full sync cycle | Testing Agent benchmarks |
| No N+1 queries | 0 N+1 patterns | Code Reviewer checks with `logging` |
| Memory usage | < 256MB for batch of 1000 | DevOps Agent monitors |

### N+1 Prevention Rules
```python
# BAD: N+1 query pattern
for binding in bindings:
    product = binding.odoo_id  # Triggers individual read per binding

# GOOD: Prefetch pattern
bindings = self.env['shopify.product.binding'].search([...])
bindings.mapped('odoo_id')  # Single prefetch query
for binding in bindings:
    product = binding.odoo_id  # Uses cache
```

---

## 5. Error Handling Standards

### Error Classification

| Level | Example | Action |
|-------|---------|--------|
| TRANSIENT | Shopify 429 (rate limit), network timeout | Retry with exponential backoff |
| RECOVERABLE | Invalid field value, missing required data | Log error, skip record, continue batch |
| FATAL | Invalid API credentials, module misconfigured | Stop sync, alert user, log error |
| DATA CORRUPTION | Binding points to deleted record | Log critical, flag for manual review |

### Retry Policy
```python
RETRY_CONFIG = {
    'max_retries': 3,
    'base_delay': 5,        # seconds
    'backoff_factor': 2,     # exponential: 5s, 10s, 20s
    'retry_on': [
        429,                 # Rate limited
        500,                 # Server error
        502,                 # Bad gateway
        503,                 # Service unavailable
        'ConnectionError',
        'Timeout',
    ],
    'no_retry_on': [
        400,                 # Bad request (our bug)
        401,                 # Auth failure
        404,                 # Not found
        422,                 # Validation error
    ],
}
```

### Logging Standards
```python
# Every sync operation must log:
_logger.info(
    "Shopify export [%s] %s %s → %s: %s",
    backend.name,           # Which backend
    'product',              # Entity type
    odoo_record.id,         # Odoo ID
    shopify_id or 'NEW',    # Shopify ID
    'success' or 'failed',  # Outcome
)

# Errors must include context:
_logger.error(
    "Shopify export failed [%s] product %s: %s",
    backend.name,
    odoo_record.id,
    str(error),
    exc_info=True,          # Include stack trace
)
```

---

## 6. Validation Gate Summary

| Gate | After | Checks | Blocks On |
|------|-------|--------|-----------|
| G1: Spec | Solution Architect | Completeness, consistency, testability | Missing mappings, untestable criteria |
| G2: Design | Technical Architect | Idempotency design, security model, Odoo compat | Missing bindings, no retry policy |
| G3: Code | Developers | Syntax, completeness, no cross-layer | Parse errors, missing methods |
| G4: Review | Code Reviewer | Full checklist (60+ items) | Any critical or major issue |
| G5: Test | Testing Agent | Coverage, all pass, no real API calls | Any test failure |
| G6: Package | DevOps Agent | Manifest, structure, clean install | Install failure |
