# Hardening Summary — Shopify Connector Pro

This document summarizes the hardening work performed on the `hardening/core-workflows` branch. It covers three missions: core workflow hardening, UI/UX improvements, and extended workflow hardening.

## Overview

| Metric | Value |
|--------|-------|
| Total bugs fixed | 18 (6 core + 1 side finding core + 10 extended + 1 side finding extended) |
| Tests added | ~80 (14 core + 25 business flows + ~44 extended/field-mapping/reconciliation) |
| Total test methods | 226 |
| Files modified | 30+ |
| Production files fixed | 15 |

## Mission 1: Core Workflow Hardening

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

## Mission 1.5: UI/UX Improvements

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

## Mission 2: Extended Workflow Hardening

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

## Side Finding Fix

**Commit:** `ef8cb82 fix: env.with_company crash — 13 occurrences across 3 files`

| Bug | Severity | Description | Fix |
|-----|----------|-------------|-----|
| EW Side Finding | Critical | `self.env.with_company()` crashes — `with_company()` is a Model method in Odoo 19, not Environment | Changed all 13 occurrences to `self.with_company(company).env` across 3 files |

Affected files:
- `wizards/shopify_bulk_export_wizard.py` (4 occurrences)
- `models/shopify_backend.py` (6 occurrences — all cron methods)
- `models/shopify_import_job.py` (3 occurrences)

## Running the Test Suite

```bash
python3 odoo-bin \
  -d <database> \
  --test-tags /shopify_connector_pro \
  -u shopify_connector_pro \
  --stop-after-init --no-http \
  --addons-path=addons,<path-to-odoo>/addons
```

Current count: 226 test methods across 24 test files, 205 executed (some share setup).

## Deferred Features (Not Implemented)

These were identified during the extended workflow audit but explicitly deferred:

| ID | Feature | Priority | Notes |
|----|---------|----------|-------|
| DEF-EW-15a | Abandoned cart recovery emails | Medium | `recovery_email_sent` field exists, UI field hidden, email logic not built |
| DEF-EW-15b | Abandoned cart auto-matching | Low | Match recovered carts to orders by email/amount |
| DEF-EW-06a | Location-to-warehouse auto-mapping | Low | Currently only maps primary location |
| DEF-EW-10 | Multi-currency rate sync from Shopify | Low | Uses Odoo rates; Shopify rates ignored |
| DEF-EW-13 | Sync log email digest | Low | Log finalization works; scheduled digest not built |

## Known Limitations

| ID | Description | Impact |
|----|-------------|--------|
| BUG-F1 | Inbound fulfillment partial receipt not fully handled | Low — partial receipts create full receipt |
| ARCH-1 | Field mapping only covers product and customer entities | Medium — order/inventory mappings not wired |
| ARCH-2 | Export wizard `with_company` fix applied but export methods themselves not integration-tested beyond product dispatch | Low |

## Recommended Next Steps (Priority Order)

1. **Wire field mappings to order/inventory importers** — same pattern as product/customer, ~30 min each
2. **Implement abandoned cart recovery emails** — model field exists, needs email template + action
3. **Add integration tests for all export wizard entity types** — customer, inventory, discount dispatch
4. **Build sync log email digest** — cron + email template summarizing daily sync results
5. **Location-to-warehouse mapping UI** — wizard to let users map Shopify locations to Odoo warehouses
