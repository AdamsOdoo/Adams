# LEGACY_NOTES.md — Salvaged Content from Pre-Finalization AI Working Files

> Created 2026-06-10 during the v1 finalization reset (see CLAUDE.md).
> Sources, all deleted in the same commit that created this file:
> - `HARDENING.md` (root) — hardening-mission summary
> - old root `CLAUDE.md` — project instructions for the build phase
> - `docs/ai-agents/security-performance-checklist.md`
> - `addons/shopify_simulator/doc/PHASE_CONTINUATION.md`
>
> Content marked "carried in full" is verbatim from the source, not summarized.
> Counts and claims herein date from the hardening branch era and have NOT been
> re-verified against current source; the Phase 1 audit treats them as leads,
> not facts.

---

## 1. Regression checklist — fixed-bug ledger (carried in full from HARDENING.md)

**Audit usage:** every bug below was caught and fixed before this reset. Tier 1/2
of the full-coverage audit should (a) confirm the fix is still present at the
cited behavior, (b) confirm a test still exercises it through the production
path, and (c) derive from each financial bug the DB condition that surfaced it,
to build the local "strict profile" (see CLAUDE.md Environment).

### Overview (from HARDENING.md)

| Metric | Value |
|--------|-------|
| Total bugs fixed | 18 (6 core + 1 side finding core + 10 extended + 1 side finding extended) |
| Tests added | ~80 (14 core + 25 business flows + ~44 extended/field-mapping/reconciliation) |
| Total test methods | 226 |
| Files modified | 30+ |
| Production files fixed | 15 |

### Mission 1: Core Workflow Hardening

**Commit:** `6ced0d4 fix: core workflow hardening — BUG-R1/R2/O1/O2/C1/CU1 + tests`

Fixed 6 bugs across core sync workflows, plus 1 side finding:

| Bug ID | Severity | Description | Fix |
|--------|----------|-------------|-----|
| BUG-R1 | High | Refund sync crashed on missing order binding | Added None-guard before accessing `order_binding.odoo_id` |
| BUG-R2 | Medium | Refund line matching failed on variant ID format | Normalized `gid://` prefix stripping |
| BUG-O1 | High | Order import silently dropped tax lines | Added rate-based fallback tax resolution |
| BUG-O2 | Medium | Duplicate order bindings on re-import | Added `search()` before `create()` |
| BUG-C1 | Medium | Collection export failed on missing checksum | Initialized `sync_checksum` field |
| BUG-CU1 | Medium | Customer dedup merged across backends | Added `backend_id` to dedup domain |

**Test file:** `test_core_workflow_hardening.py` — 14 tests

### Mission 1.5: UI/UX Improvements

**Commits:**
- `aa6bceb ux: UI/UX improvements — notifications, missing buttons, menu restructure, inventory views, error readability`
- `563d18f ux: onboarding and friction improvements from Phase 4 audit`

21 UI improvements + 5 friction fixes including:
- Added missing sync buttons on form views
- Restructured menu hierarchy for better navigation
- Added inventory operation views (transfers, adjustments)
- Improved error message readability in sync logs
- Added onboarding wizard improvements
- Fixed notification display timing

### Mission 2: Extended Workflow Hardening

**Commit:** `023962c fix: extended workflow hardening — 10 bugs fixed + 43 tests`

Audited 15 extended workflows (EW-01 through EW-15), fixed 10 production bugs:

| Bug ID | Severity | Description | Fix |
|--------|----------|-------------|-----|
| BUG-EW-08 | High | Field mapping engine was dead code — records existed but sync never read them | Added `_apply_import_mappings()` and `_apply_export_mappings()` to base importer/exporter with dotted-path traversal, direction filtering, field validation |
| BUG-EW-12a | High | Reconciliation retry only covered products (1 of 5 binding types) | Refactored to iterate all 5 binding models |
| BUG-EW-12b | Medium | Reconciliation retry reset retry_count to 0 | Changed to increment |
| BUG-EW-14a | Medium | Tag split failed on spaces: `"a, b".split(", ")` missed `"a,b"` | Changed to `[t.strip() for t in tags.split(',') if t.strip()]` |
| BUG-EW-01a | Medium | Collection export falsely marked existing collections as synced | Removed false `_mark_synced()` call, skip with debug log |
| BUG-EW-02a | Medium | Metafield bool/float serialization corrupted values | Added type-aware `_serialize_metafield_value()` |
| BUG-EW-04a | Medium | Gift card sync produced no sync log | Added sync log creation and `_finalize()` call |
| BUG-EW-07 | Low | Tax resolution failures were silent | Added descriptive warning logs |
| BUG-EW-09 | Low | Product image re-import created duplicates | Added stale image cleanup before re-import |
| BUG-EW-05a | Low | Invalid payout transaction types crashed Selection field write | Added validation with fallback to False |

**Test files:**
- `test_field_mapping.py` — 10 tests (import/export field mapping engine)
- `test_reconciliation.py` — 4 tests (retry across binding types, increment behavior)
- `test_extended_workflows.py` — 30 tests (locations, discounts, collections, wizards, multi-currency, abandoned carts, sync log digest)

### Side Finding Fix

**Commit:** `ef8cb82 fix: env.with_company crash — 13 occurrences across 3 files`

| Bug | Severity | Description | Fix |
|-----|----------|-------------|-----|
| EW Side Finding | Critical | `self.env.with_company()` crashes — `with_company()` is a Model method in Odoo 19, not Environment | Changed all 13 occurrences to `self.with_company(company).env` across 3 files |

Affected files:
- `wizards/shopify_bulk_export_wizard.py` (4 occurrences)
- `models/shopify_backend.py` (6 occurrences — all cron methods)
- `models/shopify_import_job.py` (3 occurrences)

---

## 2. Deferred features — not implemented (carried in full from HARDENING.md)

These were identified during the extended workflow audit but explicitly deferred:

| ID | Feature | Priority | Notes |
|----|---------|----------|-------|
| DEF-EW-15a | Abandoned cart recovery emails | Medium | `recovery_email_sent` field exists, UI field hidden, email logic not built |
| DEF-EW-15b | Abandoned cart auto-matching | Low | Match recovered carts to orders by email/amount |
| DEF-EW-06a | Location-to-warehouse auto-mapping | Low | Currently only maps primary location |
| DEF-EW-10 | Multi-currency rate sync from Shopify | Low | Uses Odoo rates; Shopify rates ignored |
| DEF-EW-13 | Sync log email digest | Low | Log finalization works; scheduled digest not built |

---

## 3. Known limitations (carried in full from HARDENING.md)

| ID | Description | Impact |
|----|-------------|--------|
| BUG-F1 | Inbound fulfillment partial receipt not fully handled | Low — partial receipts create full receipt |
| ARCH-1 | Field mapping only covers product and customer entities | Medium — order/inventory mappings not wired |
| ARCH-2 | Export wizard `with_company` fix applied but export methods themselves not integration-tested beyond product dispatch | Low |

---

## 4. Recommended next steps from the hardening era (carried in full from HARDENING.md)

> These are leads for FINALIZE.md / ROADMAP.md, not commitments.

1. **Wire field mappings to order/inventory importers** — same pattern as product/customer, ~30 min each
2. **Implement abandoned cart recovery emails** — model field exists, needs email template + action
3. **Add integration tests for all export wizard entity types** — customer, inventory, discount dispatch
4. **Build sync log email digest** — cron + email template summarizing daily sync results
5. **Location-to-warehouse mapping UI** — wizard to let users map Shopify locations to Odoo warehouses

---

## 5. Test invocation (carried in full from HARDENING.md)

```bash
python3 odoo-bin \
  -d <database> \
  --test-tags /shopify_connector_pro \
  -u shopify_connector_pro \
  --stop-after-init --no-http \
  --addons-path=addons,<path-to-odoo>/addons
```

Current count (hardening era): 226 test methods across 24 test files, 205 executed
(some share setup). NOTE: the current tree has 29 connector test files plus 17
simulator test files; re-count during STEP 0.

---

## 6. Odoo test accounting setup — MANDATORY recipe (carried in full from old CLAUDE.md §1)

**This is the #1 source of recurring test failures.** Every review and code generation session
MUST enforce these rules when tests involve invoicing, payments, or accounting operations.

When a test calls `_create_invoices()`, `action_post()` on an `account.move`, or any operation
that creates `account.move.line` records, the test setUp **MUST** configure:

### a) Receivable + Payable Accounts on Partners

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

### b) Income Account on Products

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

### c) Sales Journal

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

---

## 7. Test review checklist (carried in full from old CLAUDE.md §2)

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

---

## 8. Other facts asserted by the old CLAUDE.md (UNVERIFIED — re-verify against source before citing)

- Run-before-commit habit: check install logs for `ERROR:` and `psycopg2.errors`
  even when tests "pass" — SQL-level constraint violations can be swallowed.
- Layer rule: models never call the API directly; the sync layer mediates.
- Shopify API: GraphQL Admin API `2026-01` only; REST is deprecated and never used.
- Rate limiting: cost-based token bucket, adaptive from Shopify response headers.
- Circuit breaker: opens after 5 consecutive failures, recovers after 300s.
- License: OPL-1; old version string `19.0.1.0.0` (a `migrations/19.0.1.1.0/` dir
  now exists in-tree — reconcile during Tier 6).

---

## 9. Connector-specific items from the deleted security/performance checklist

(From `docs/ai-agents/security-performance-checklist.md`; generic ORM/API hygiene
dropped — these are the items worth re-checking explicitly during Tiers 2–3.)

- Webhooks: HMAC validated *before* any payload parsing; replay window + unique
  event ID storage; fast ACK with heavy work offloaded; idempotent handlers;
  dead-letter failed events with triage metadata.
- Idempotency keys by resource type (orders: shop+order+version/updated_at;
  products: shop+product+updated_at; fulfillments: shop+fulfillment+status
  revision); persisted processing status (received/processing/done/failed);
  retries safe — never assume exactly-once delivery.
- Rate limiting: shared cost budget per Shopify instance; webhook-triggered work
  prioritized over bulk backfills; exponential backoff with jitter; circuit
  breaker on sustained throttle/error bursts.
- Observability: webhook lag / job throughput / retry counts / throttle events;
  structured logs with correlation IDs.

---

## 10. Simulator phase status (summarized from deleted PHASE_CONTINUATION.md)

- Phase 1 (complete): simulator module scaffold, `_make_api_client()` factory on
  `shopify.backend` (20+ call sites), core models/handlers (shop, product,
  customer, order, inventory, location), cursor pagination, error modes,
  production safeguard, regex dispatch (17 query + 22 mutation patterns),
  `demo_store.py` fixtures. 112 tests at the time.
- Phase 2 (complete at last record): fulfillment/refund/webhook models and
  handlers, full order lifecycle (PENDING → PAID → FULFILLED → REFUNDED),
  outbound webhook delivery with real HMAC-SHA256 signing, 58 new tests
  (170 simulator total at the time), ACLs for all new models.
- Authoritative simulator docs that remain in-tree:
  `addons/shopify_simulator/doc/DESIGN.md` and
  `addons/shopify_simulator/doc/shopify_simulator_user_guide.md`.
