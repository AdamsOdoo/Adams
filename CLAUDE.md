# Adams Shopify Connector Pro — Project Instructions

## Module Overview

This repository contains `adams_shopify` (Shopify Connector Pro) and `adams_shopify_manager_dashboard`.
These are production-grade, public-facing Odoo App Store modules used by thousands of users.
Every change must be treated as a release to paying customers.

## Critical Development Rules

### 1. Odoo Test Accounting Setup (MANDATORY)

**This is the #1 source of recurring test failures.** Every review and code generation session
MUST enforce these rules when tests involve invoicing, payments, or accounting operations.

When a test calls `_create_invoices()`, `action_post()` on an `account.move`, or any operation
that creates `account.move.line` records, the test setUp **MUST** configure:

#### a) Receivable + Payable Accounts on Partners

```python
# ALWAYS do this for any partner used in invoice/payment tests
receivable_account = self.env['account.account'].search([
    ('account_type', '=', 'asset_receivable'),
    ('company_ids', 'in', [self.env.company.id]),
], limit=1)
if not receivable_account:
    receivable_account = self.env['account.account'].create({
        'name': 'Test Receivable',
        'code': 'TREC',
        'account_type': 'asset_receivable',
        'reconcile': True,
        'company_ids': [(6, 0, [self.env.company.id])],
    })
payable_account = self.env['account.account'].search([
    ('account_type', '=', 'liability_payable'),
    ('company_ids', 'in', [self.env.company.id]),
], limit=1)
if not payable_account:
    payable_account = self.env['account.account'].create({
        'name': 'Test Payable',
        'code': 'TPAY',
        'account_type': 'liability_payable',
        'reconcile': True,
        'company_ids': [(6, 0, [self.env.company.id])],
    })

self.partner = self.env['res.partner'].create({
    'name': 'Test Partner',
    'property_account_receivable_id': receivable_account.id,
    'property_account_payable_id': payable_account.id,
})
```

#### b) Income Account on Products

```python
income_account = self.env['account.account'].search([
    ('account_type', '=', 'income'),
    ('company_ids', 'in', [self.env.company.id]),
], limit=1)
if not income_account:
    income_account = self.env['account.account'].create({
        'name': 'Test Income Account',
        'code': 'TINC',
        'account_type': 'income',
        'company_ids': [(6, 0, [self.env.company.id])],
    })
self.product.categ_id.property_account_income_categ_id = income_account
self.product.product_tmpl_id.property_account_income_id = income_account
```

#### c) Sales Journal

```python
if not self.env['account.journal'].search(
    [('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], limit=1,
):
    self.env['account.journal'].create({
        'name': 'Test Sales Journal',
        'type': 'sale',
        'code': 'TSHP',
        'company_id': self.env.company.id,
    })
```

**Why this matters:** The `account_move_line_check_accountable_required_fields` DB constraint
requires `account_id IS NOT NULL` on invoice lines with `display_type` in (`product`,
`payment_term`). Without proper account setup, `_create_invoices()` will crash at the SQL
level. This error is **silent at the Python level** — it only appears as a psycopg2
`CheckViolation`, making it hard to diagnose.

### 2. Test Review Checklist (for /review and /ultrareview)

When reviewing test files, ALWAYS verify:

- [ ] **Partners with invoices** have `property_account_receivable_id` AND `property_account_payable_id`
- [ ] **Products with invoices** have an income account (via category or product template)
- [ ] **Sales journals** exist for the test company
- [ ] **Bank journals** exist if testing payments or payouts
- [ ] **Unique constraint tests** use `self.assertRaises(Exception)` or `IntegrityError`
- [ ] **Webhook/API tests** mock external calls (never hit real Shopify endpoints)
- [ ] **TransactionCase** tests that modify accounting properties understand these are
      company-dependent fields in Odoo 19+
- [ ] **No hardcoded IDs** — always search or create test records dynamically
- [ ] **Multi-company isolation** — tests creating backends set `company_id`

### 3. Code Quality Standards

- All models must have proper `_description`
- All fields visible to users must have `string=` and `help=`
- Security: `ir.model.access.csv` entry for every new model
- Record rules: multi-company isolation for every model with `backend_id` or `company_id`
- No `sudo()` without explicit security justification
- No raw SQL (`cr.execute`) — use the ORM
- All sync operations wrapped in savepoints for error isolation
- Webhook handlers must verify HMAC before processing

### 4. Before Committing

- Run the full test suite: `odoo-bin -u adams_shopify --test-enable --stop-after-init --no-http`
- Verify 0 failures, 0 errors
- Check the install.log for SQL-level errors that tests may swallow (grep for `ERROR:`)
- Review `psycopg2.errors` in logs — these indicate constraint violations even if tests "pass"

### 5. Module Architecture

```
addons/adams_shopify/
├── models/          # Odoo models (bindings, extensions)
├── sync/            # Business logic (importers, exporters)
├── shopify_api/     # GraphQL client, rate limiter, queries
├── controllers/     # Webhook endpoint
├── views/           # XML views
├── wizards/         # Transient models for UI actions
├── security/        # Access rules, record rules
├── data/            # Cron jobs
├── tests/           # Test suite (20 files, 79+ tests)
└── doc/             # Documentation
```

**Layer rule:** Models never call the API directly. The sync layer always mediates.

### 6. Shopify API

- API version: `2026-01` (GraphQL Admin API only)
- REST API is deprecated — never use it
- Rate limiting: cost-based token bucket (adaptive from Shopify response headers)
- Circuit breaker: opens after 5 consecutive failures, recovers after 300s

### 7. Version & Release

- Current version: `19.0.1.0.0`
- License: OPL-1 (Odoo Proprietary License)
- Target: Odoo App Store (public release, thousands of users)
- Every change must be backward-compatible or include migration scripts
