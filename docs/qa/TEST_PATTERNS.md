# Test Patterns

Source: active durable QA knowledge extracted from archived `docs/archive/LEGACY_NOTES.md` during Goal 0. Do not treat historical counts or hardening-era claims as current coverage without re-verification.

## Accounting Setup Recipe

When tests involve invoicing, payments, or accounting operations, configure accounting prerequisites in `setUp` before calling `_create_invoices()`, `action_post()` on an `account.move`, or any operation that creates `account.move.line` records.

### Receivable + Payable Accounts on Partners

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

### Income Account on Products

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

### Sales Journal

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

Why this matters: the `account_move_line_check_accountable_required_fields` database constraint requires `account_id IS NOT NULL` on invoice lines with `display_type` in (`product`, `payment_term`). Without proper account setup, `_create_invoices()` can fail at SQL constraint level.

## Test Review Checklist

When reviewing test files, verify:

- [ ] Partners with invoices have `property_account_receivable_id` and `property_account_payable_id`.
- [ ] Products with invoices have an income account via category or product template.
- [ ] Sales journals exist for the test company.
- [ ] Bank journals exist if testing payments or payouts.
- [ ] Unique constraint tests use `self.assertRaises(Exception)` or `IntegrityError`.
- [ ] Webhook/API tests mock external calls and never hit real Shopify endpoints.
- [ ] `TransactionCase` tests that modify accounting properties account for company-dependent fields in Odoo 19+.
- [ ] No hardcoded IDs; tests search or create records dynamically.
- [ ] Multi-company tests creating backends set `company_id`.

## Reusable QA Rules

- Check install logs for `ERROR:` and `psycopg2.errors` even when tests pass, because SQL-level constraint failures can be missed in high-level summaries.
- Re-verify Odoo and Shopify claims against source/schema before citing them.
- Preserve layer boundaries in tests: tests should exercise connector paths and mock only external Shopify boundaries where needed.
