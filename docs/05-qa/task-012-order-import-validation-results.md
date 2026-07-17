# Task 012 — Order Import Validation Results

## Status

**Implementation and static/source validation assembled; exact-head Odoo.sh runtime not run.**

- Date: 2026-07-17
- Branch / PR: `sol/wave-2-order-import`; draft PR #176 → `mvp/program-integration`
- Verified base: `234c0bb50b3f61b7681e18f0b28839dee619cdb9`
- Task 012 commit: `92cab4c532e03102473a04cb2f2b23d7f307a480`
- Combined code head before this docs-only handoff: `a9e1d61a6655d6b46b53057e372115c02ba0bdfd`
- Runtime build / database: **not available**
- Hard stop: **condition 5 — no authenticated Odoo.sh capability in this session**

This record does not claim an Odoo test pass, install/upgrade success, runtime integration, residue result, or live Shopify call. The PR remains draft and cannot pass its wave gate until the matrix below is executed at the then-current exact PR head.

## Implemented scope

- PII-free `shopify.connector.order.binding` with permanent per-store Shopify GID and sale-order uniqueness, complete fail-closed stored-field classification, manual-gateway approval provenance, and Reviewer/Administrator audited approval action.
- `sale.order.line.shopify_line_item_gid` trace field.
- Four read-only GraphQL operations: header plus complete line-item, shipping-line and discount-application pagination. Every transport uses `execute_business`; no network call occurs in scan classification or local readiness.
- Atomic whole-order creation and binding; existing bindings refresh evidence without rewriting commercial lines.
- Product variant/template binding-chain resolution; custom-line and connector service products are idempotent and store-scoped.
- Existing customer binding/import sequence, guest email match/create, fallback partner and child-address deduplication.
- Decimal money validation; equal-currency shop/presentment checks; unsupported edit/refund/duty/fee/tip/cash-rounding gates; bounded whole-order reconciliation.
- Versioned exact tax fingerprint and explicit Administrator-maintained mapping; no automatic `account.tax` creation.
- Paid/authorized/pending/partial/terminal confirmation policies; manual gateway policies and approval refresh; COD read model only.
- `order_import_sync` handler, `sale_domain_enabled` gate, LC-1 historic conversion and `remote_read_replay_safe` policy.

## Static and source evidence actually executed

- Exact 20 Wave-2 Python files parsed successfully.
- Sale cron XML, manifest and ACL CSV parsed; manifest version is `19.0.2.0.0`; final ACL inventory is 12 rows.
- The four importer operations start with `query`, contain complete cursor/pageInfo pagination, and contain no mutation.
- AST guard confirms `execute_business` is present and raw `.execute()` / `with_context` bypasses are absent.
- Job types register exact LC-1 `selection_add` / `ondelete` conversion and `remote_read_replay_safe`; dispatch extensions create no job directly.
- Order binding asserts the exact 50 protected fields: 9 shared fields, `sale_order_id`, and 40 concrete system/snapshot/provenance fields; `_pii_snapshot_fields()` is empty.
- Exact production sudo inventory: order binding 1 (approval provenance write); importer 2 (binding create and evidence refresh); scan 1 (checkpoint advance); tax mapping 0.
- Negative source scan found no `orderMarkAsPaid`, `orderCreateManualPayment`, connector mutation, account-tax auto-create, context bypass, TODO or FIXME.
- 86 test methods are authored across the exact 11 locked order test files. They are **not described as passing** because no Odoo runtime was available.

## Bounded behavior

| Boundary | Value |
| --- | --- |
| Line items | 100/page × 100 pages = 10,000 |
| Shipping lines | 50/page × 100 pages = 5,000 |
| Discount applications | 50/page × 100 pages = 5,000 |
| Solver | K=2; at most 2 dependent lines; at most 25 vectors |
| Tax suggestions | 20 non-binding candidates |
| Sale-line description | 512 characters |
| Pending-payment recheck | 15 minutes |
| Currency posture | rounding finer than 0.01 fails closed pending named dev-store evidence |

## Official-source compatibility refresh

Accessed 2026-07-17:

- Accessible — Shopify Admin GraphQL 2026-07 `OrderSortKeys.UPDATED_AT`: https://shopify.dev/docs/api/admin-graphql/2026-07/enums/OrderSortKeys
- Accessible — Odoo 19 sale-order tax calculation helpers: https://github.com/odoo/odoo/blob/19.0/addons/sale/models/sale_order.py
- Accessible — Odoo 19 account-tax `price_include_override`: https://github.com/odoo/odoo/blob/19.0/addons/account/models/account_tax.py

These checks confirm compatibility of the accepted implementation shape; they are not runtime evidence.

## Mandatory exact-head Odoo.sh operator matrix

Run on an Odoo 19 dev build checked out at the then-current PR #176 head and record the build, database, exact SHA, clean worktree, module versions, command forms, tags, counts and warnings.

1. Fresh install `shopify_connector_core,shopify_connector_product,shopify_connector_sale` with tests.
2. Upgrade from the inherited `mvp/program-integration@234c0bb...` module state.
3. All Task 012 and SEC-1/PII focused classes in the 11 order test files.
4. Full standard core, product and sale suites.
5. `shopify_connector_order_discovery_concurrency` with both the enqueue and permanent-binding/SO races; repeat for stability.
6. LC-1 install/disable/uninstall/reinstall, selection removal, historic conversion and no-orphan checks.
7. JOB-ACTIONS, CORE-R1, SEC-1 and one combined SRR-03 smoke regression.
8. Residue audit: connector jobs/logs/leases/stores/credentials/bindings/orders/products/mappings created by tests; cron triggers; temporary files; workers.
9. Database audit: sessions, idle transactions, cursors, locks, leases and cron triggers.
10. Security scan: credentials, access tokens, Authorization headers, raw PII and temporary paths.
11. If issue #157 reproduces exactly, apply only the accepted temporary `notification_type` and `color_scheme` defaults, rerun, then drop and verify both defaults are restored.
12. Read-only Shopify dev-store order evidence is preferred but may be deferred honestly to Wave 6 if credentials are unavailable.

Representative command forms (the operator must substitute the Odoo.sh checkout's actual binary/config/database):

```text
odoo-bin -d <db> -i shopify_connector_core,shopify_connector_product,shopify_connector_sale --test-enable --stop-after-init
odoo-bin -d <db> -u shopify_connector_core,shopify_connector_product,shopify_connector_sale --test-enable --test-tags /shopify_connector_sale --stop-after-init
odoo-bin -d <db> -u shopify_connector_sale --test-enable --test-tags shopify_connector_order_discovery_concurrency --stop-after-init
```

## Rollback

Pre-production: restore the database backup taken immediately before module upgrade and deploy a source revert. Production: set `order_scheduled_sync_enabled=False`, quiesce non-terminal jobs through existing actions, and preserve imported sale orders, bindings and tax mappings. Do not uninstall the sale addon as rollback; it also owns the merged customer domain.

## Proven / not proven

Proven statically: allowed-file scope, registration, read-only query posture, fail-closed field protection, replay/lifecycle declarations, explicit caps and exact sudo inventory.

Not proven: Odoo model setup, install/upgrade/uninstall/reinstall, functional tests, concurrency at runtime, full regression, residue/security runtime, dev-store behavior. No exactly-once remote-effect or DEC-031 Layer 2 claim is made.
