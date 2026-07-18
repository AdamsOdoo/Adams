# Task 012 / Area-6 — Wave 2 Campaign 4 exact-head runtime evidence (GREEN)

> **Status: GREEN — READY FOR FRESH CLAUDE FINAL WAVE REVIEW.**
> Independent authenticated Odoo.sh clean/full fresh-install runtime validation of the
> corrected Wave 2 order-import head. This document preserves Campaigns 1–3 (below and in
> the linked records) and records the fourth, final exact-head campaign, which is green.
>
> - **Runtime-tested SHA:** `63607dd87a8bfc253ee60ed00e0d761ee62c8776`
> - **Base:** `mvp/program-integration@234c0bb50b3f61b7681e18f0b28839dee619cdb9`
> - **Build:** `35100725` · **DB:** `adamsmen-sol-wave-2-order-import-35100725`
> - **Odoo:** 19.0 · **PostgreSQL:** 16.14 (16.14-0ubuntu0.24.04.1)
> - **Modules:** `shopify_connector_core 19.0.1.9.1` / `shopify_connector_product 19.0.2.1.2` /
>   `shopify_connector_sale 19.0.2.0.0` (`account 19.0.1.4`)
> - **Control-room authorization:** PR #176 comment `5011632937`
> - **Auditor discipline:** no production code changed; no test changed; no Shopify mutation;
>   PR #176 remains open, draft and unmerged; protected refs unchanged; Wave 3 unstarted.

## 1. Identity gate (verified before runtime)

| Check | Result |
| --- | --- |
| Branch head `sol/wave-2-order-import` = authorized SHA | ✅ `63607dd87a8bfc253ee60ed00e0d761ee62c8776` |
| No commit exists after the authorized SHA | ✅ branch tip = HEAD, no descendants |
| Base is `234c0bb50b3f61b7681e18f0b28839dee619cdb9` (ancestor) | ✅ `git merge-base --is-ancestor` true |
| PR changed-file count | ✅ exactly **29** files vs base |
| Correction commit `63607dd` scope | ✅ touches only `addons/shopify_connector_sale/tests/test_order_totals_guard.py` (+26/-1) |
| Fixture correction `6f32e4c` in ancestry | ✅ present |
| Campaign-3 evidence commit `31419b7` in ancestry | ✅ present |
| Protected checkpoint ref `checkpoint/core-r2-readonly-uat-2026-07-15` | ✅ `acd8c4691e72cf5590f2a56228b08f183b76cd9a` unchanged |
| Wave 3 | ✅ unstarted |

**PR/protected-ref limitation (stated honestly):** this runtime container has no `gh` CLI and no
GitHub token (the GitHub API returns `404` unauthenticated for the private repo). PR #176's
draft/unmerged state and the protected-ref state are therefore asserted from **local git only**.
The auditor performed no push to any protected ref, no merge, and no ready-marking.

## 2. Authoritative fresh install (build 35100725)

The Odoo.sh dev build for the exact head installs the three connector modules with tests enabled
during build; the build's own `install.log` is the authoritative clean/full fresh-install result:

```
odoo.tests.result: 0 failed, 0 error(s) of 728 tests when loading database
  'adamsmen-sol-wave-2-order-import-35100725'
```

Per-module test execution on the fresh install (`odoo.tests.stats`):

| Suite | Tests | Time | Result |
| --- | --- | --- | --- |
| `shopify_connector_core` | 414 | 4.56s | 0 failed / 0 error |
| `shopify_connector_product` | 202 | 9.61s | 0 failed / 0 error |
| `shopify_connector_sale` | 232 | 13.91s | 0 failed / 0 error |
| **Aggregate (`tests.result`)** | **728** | — | **0 failed / 0 error / 0 skipped** |

Registry loaded; all 23 connector models register; SQL constraints exist on every connector table
(order_binding 10, tax_mapping 6, job 7, store 5, credential 5, store_settings 10, product bindings
9/10, customer_binding 9, job_log 6, call_lease 5, location 5, attribute_lock 3); LC-1
ondelete/replay job policies load; exactly **one** order-scan cron
(`ir_cron_shopify_connector_order_scan`, active, 15-minute); exactly **twelve** sale ACL rows; no
duplicate XML IDs; store-setting defaults present; the only build warning is a single
test-induced negative-path scan warning (see §11).

## 3. Campaign-3 failure regression — CLOSED

Campaign 3 (build `35095228`, SHA `2525447`) recorded `0 failed / 3 error(s) of 728` — all three in
`TestOrderTotalsGuard`, an `account.tax` `tax_group_id`/`country_id` NOT-NULL violation raised by the
test's own `_map_tax()` helper, which built `account.tax` without a country-consistent tax group.
Commit `63607dd` mirrored the country-consistent tax + tax-group fixture (already fixed in
`test_order_tax_resolution.py` by `6f32e4c`) into `test_order_totals_guard.py._map_tax`.

Explicit targeted re-execution against the exact head
(`-u shopify_connector_sale --test-tags /shopify_connector_sale:TestOrderTotalsGuard,/shopify_connector_sale:TestOrderTaxResolution`):

```
odoo.tests.result: 0 failed, 0 error(s) of 19 tests
```

| Campaign-3 error test | Result |
| --- | --- |
| `TestOrderTotalsGuard.test_order_and_source_tax_fingerprints_must_reconcile` | ✅ PASS |
| `TestOrderTotalsGuard.test_tax_excluded_and_tax_included_orders_use_mapped_engine_taxes` (`included=False`) | ✅ PASS |
| `TestOrderTotalsGuard.test_tax_excluded_and_tax_included_orders_use_mapped_engine_taxes` (`included=True`) | ✅ PASS |

The engine-tax test loops `for included in (False, True)` under `subTest`, each asserting
`amount_untaxed=100.0 / amount_tax=5.0 / amount_total=105.0` through the country-consistent
`_map_tax()` fixture. **All three Campaign-3 errors are closed.**

### Tax-fixture country-consistency (finding #5) — both helpers verified

For every fixture-created `account.tax`, both helpers now guarantee (and self-assert):
`country_id` non-empty; `tax_group_id` non-empty; tax-group `country_id` non-empty;
`tax.company_id == tax.tax_group_id.company_id`; `tax.country_id == tax.tax_group_id.country_id`.

- **`TestOrderTaxResolution._tax()`** (`test_order_tax_resolution.py`): resolves company (exists-checked)
  and country via a fallback chain (explicit → company fiscal country → company country → env-company
  fiscal → env-company country → `base.us`), `ensure_one()`; creates `account.tax.group` with matching
  `company_id`/`country_id`; re-applies `company_id`/`country_id`/`tax_group_id` **after**
  `values.update(extra)` so kwargs cannot break consistency. `test_mapping_rejects_wrong_company_inactive_or_incompatible_tax`
  asserts the full contract per candidate.
- **`TestOrderTotalsGuard._map_tax()`** (`test_order_totals_guard.py`, lines 66–69): asserts
  `tax.country_id`, `tax.tax_group_id.country_id`, `tax.company_id == tax.tax_group_id.company_id`,
  `tax.country_id == tax.tax_group_id.country_id`; creates the **explicit** `shopify.connector.tax.mapping`
  (no `account.tax` production auto-creation anywhere in the pipeline).

## 4. Complete Wave 2 inventory — 86 methods, none silently excluded

The Wave-2 order-import inventory is **86 unique methods** across the 11 `test_order_*.py` files:

| File | Methods |
| --- | --- |
| `test_order_binding.py` | 4 |
| `test_order_cod_import_readmodel.py` | 4 |
| `test_order_confirmation_policy.py` | 7 |
| `test_order_customer_resolution.py` | 8 |
| `test_order_duplicate_prevention.py` | 6 (4 standard + 2 concurrency) |
| `test_order_import_mapping.py` | 12 |
| `test_order_manual_gateway_overlay.py` | 12 |
| `test_order_scan_triggers.py` | 7 |
| `test_order_tax_resolution.py` | 6 |
| `test_order_totals_guard.py` | 13 |
| `test_order_watermark_backfill.py` | 7 |
| **Total** | **86** |

- **84 standard methods** — executed inside the fresh-install and warm sale suites, 0 failed / 0 error.
- **2 custom-tag concurrency methods** — `TestOrderDiscoveryConcurrencyGenuine`
  (`@tagged('post_install','-at_install','-standard','shopify_connector_order_discovery_concurrency')`):
  `test_two_connections_return_one_scan_job`, `test_two_connections_create_one_permanent_binding_and_sale_order`
  — executed via the custom tag, 3/3 green (§8).

No method was skipped or silently excluded.

## 5. Full connector suites (per-suite)

**Authoritative result = the fresh-install result (§2): core 414 / product 202 / sale 232, all 0/0.**
Independent warm reruns (`odoo-bin -u <module> --test-enable`) were used **for diagnosis only**:

| Warm rerun | Reported | Notes |
| --- | --- | --- |
| `-u shopify_connector_sale` | `0 failed, 0 error of 194` | Wave-2 scope; fully green (194 standard sale tests) |
| `-u shopify_connector_product` | `0 failed, 2 error of 357` | 2 base-`account` warm artifacts (§ below); cascaded sale 194 = 0/0 |
| `-u shopify_connector_core` | `0 failed, 10 error of 586` | 10 base-`account` warm artifacts; sale 232 = 0/0 |

### Warm-only base-Odoo artifact — precisely attributed, NOT a connector defect

All warm-rerun errors are **`setUpClass` failures** creating a plain `res.users`/`res.partner`, hitting
`psycopg2.errors.NotNullViolation: null value in column "autopost_bills" of relation "res_partner"`.

- `autopost_bills` is defined **only** by the base **`account`** module
  (`account/models/partner.py:608`, `fields.Selection(default='ask', required=True)`, NOT-NULL DB column,
  no DB-level default). **Zero** connector references exist to `autopost_bills`.
- The failure occurs entirely in base/enterprise `res.partner` creation (through `enterprise/ai_fields`),
  **before any connector code runs**.
- The **fresh install ran every one of these classes green** (build `35100725`: 0/0/728, product 202,
  core 414). Each of the 10 warm `setUpClass` errors is a 1:1 `autopost_bills` NOT-NULL violation
  (verified: 10 `setUpClass` headers ↔ 10 `autopost_bills` root causes; no other cause).
- The Wave-2 sale suite hit **zero** `setUpClass` errors in both its isolated run and the cascade.

This is exactly the "warm-only base-Odoo artifact" §5 of the mandate anticipates: it is precisely
attributed to base `account.res_partner.autopost_bills` and it **does not mask a fresh-install
connector defect** (the identical classes are green on the authoritative fresh install). It is a
non-blocking base-platform warm-`-u` observation, not a Wave 2 defect and not a correction trigger.

## 6. All eleven original findings — PASS

| # | Finding | Representative passing test(s) |
| --- | --- | --- |
| 1 | account.payment AST guard | `test_source_contains_no_mark_paid_or_payment_creation`, `test_exact_sudo_inventory_and_dispatch_create_guard`, `test_no_tax_autocreate_or_shopify_mutation_surface` |
| 2 | COD snapshot | `test_cod_dimensions_initialize_without_accounting_side_effects`, `test_successful_manual_transaction_is_snapshot_only` |
| 3 | pending wait/expiry legal state | `test_pending_wait_and_expiry_use_existing_job_states` |
| 4 | address-company deferral | `test_customer_company_boundary_blocks_before_order_creation`, `test_addresses_are_child_records_and_deduplicate_on_refresh_path` |
| 5 | country-consistent Odoo-19 tax fixtures | `TestOrderTaxResolution._tax()` + `TestOrderTotalsGuard._map_tax()` (both, §3) |
| 6 | tax-fingerprint distinctions & NFC | `test_v1_fingerprint_is_full_tuple_versioned_and_fold_free`, `test_order_and_source_tax_fingerprints_must_reconcile` |
| 7 | Administrator backfill preview | `test_preview_classifies_all_buckets_and_creates_nothing` |
| 8 | atomic failed scan & retry | `test_partial_page_failure_holds_watermark_and_remains_resumable`, `test_atomic_rollback_when_audit_creation_fails` |
| 9 | Administrator confirmation | `test_confirm_requires_exact_current_preview_token_then_enqueues` |
| 10 | read-all-orders boundary | `test_read_all_orders_honesty_never_silently_truncates` |
| 11 | stale/Boolean token rejection & non-admin denial | `test_stale_or_boolean_confirmation_never_enqueues`, `test_manual_store_trigger_is_role_gated_enqueue_only_and_idempotent` |

All eleven map to tests that pass inside the green fresh-install suite.

## 7. Business contract

Validated green through the passing order suites: order-binding uniqueness; protected-field
classification and direct forge/write/clear refusal; no raw PII in bindings; paid-only confirmation
policy; manual-gateway behaviour; COD read-model-only behaviour; explicit tax mapping only; no
rate-only fallback; no `account.tax` production auto-creation; customer resolution; product
resolution; custom lines and gift cards; missing-product hold; totals and currency guards;
unsupported fee/tip/duty/cash-rounding handling; enqueue-only scan; scheduled-sync gates; watermark
30-minute overlap; preview zero-write; exact confirmation token; confirmed-backfill idempotency; page
and candidate limits; zero Shopify mutation (no network egress).

## 8. Concurrency — `TestOrderDiscoveryConcurrencyGenuine` ×3

| Repetition | Result |
| --- | --- |
| 1/3 | ✅ `0 failed, 0 error(s) of 2 tests` — both methods, no deadlock/leak |
| 2/3 | ✅ `0 failed, 0 error(s) of 2 tests` — both methods, no deadlock/leak |
| 3/3 | ✅ `0 failed, 0 error(s) of 2 tests` — both methods, no deadlock/leak |

Each repetition runs the two genuine independent-PostgreSQL-connection race tests, whose in-test
assertions verify exactly one job, exactly one binding, exactly one sale order, the losing quotation
cleaned, the losing conflict captured, the losing transaction still usable (`SELECT 1` succeeds and
commits), no deadlock, and no leaked session/cursor/thread/process. Post-run DB residue is clean (§10).

## 9. Security and ACL — four roles

Exactly 12 sale ACL rows (`ir.model.access`) across four roles and three models; permission bits:

| Model | Auditor | Operator | Reviewer | Administrator |
| --- | --- | --- | --- | --- |
| `shopify.connector.order.binding` | r | r c | r w | r w c |
| `shopify.connector.customer.binding` | r | r c | r w | r w c |
| `shopify.connector.tax.mapping` | r | r | r | r w c |

- **No row grants `unlink` to any role** (verified: 0 unlink grants) — no unlink by any role.
- Tax-mapping create/write is **Administrator-only**; Auditor/Operator/Reviewer read-only.
- Reviewer/Administrator manual-gateway approval vs Auditor/Operator denial, protected-field
  create/write/clear refusals, and Administrator-only backfill / non-admin denial are asserted by the
  passing ACL and manual-gateway tests; denied operations leave no partial state or audit residue
  (`test_atomic_rollback_when_audit_creation_fails`, `test_override_atomic_rollback_when_audit_fails`).

## 10. SRR-03, Wave-1 regressions, residue and redaction

Wave-1 / SRR-03 regressions executed green on the fresh install (within 728/0/0): `TestJobActions`
(JOB-ACTIONS, 9), `TestSecurityHardening` (SEC-1, 10), `TestConnectionLifecycle` (connection
generation / disconnect / reconnect, 43, incl. `test_no_secret_leakage_across_lifecycle_actions`),
`TestCredentialAccess`/`TestCredentialService` (credential redaction / two-phase disconnect, 4/24),
`TestReadinessSlotClosure` (20), `TestDrainOwnershipReplayGenuine` (replay registry, 10),
`TestGenuineRealAdmission` (lifecycle admission / quiescence, 9, incl.
`test_zero_residue_verifies_job_logs`), `TestApiClient` token-redaction. SRR-03 is a dispatch/replay
invariant referenced in `shopify_connector_job.py` / `shopify_connector_job_dispatch.py` /
`shopify_connector_customer_importer.py`; its smoke is covered by the passing dispatch/replay tests.

**Residue / resource audit (live DB, post-runs):** 0 idle-in-transaction sessions; 0 blocked/waiting
locks; 0 advisory locks; 0 orphan rows in `shopify_connector_store` / `_job` / `_order_binding` /
`_customer_binding` / `_tax_mapping`; no running or retry-waiting jobs; no orphan logs/audits/mappings/
stores; no stray workers; no temporary artifacts (the concurrency tests' real-commit paths clean up
fully).

**Credential / PII / log audit:** the full run logs contain **no** access tokens or Shopify token
prefixes (`shpat_`/`shpca_`/`shppa_`), **no** `Authorization`/`Bearer`/`x-shopify-access-token`
headers, **no** `access_token`/`password`/`client_secret` values, **no** connection strings, **no**
raw customer email/phone/address in connector logger lines, **no** full Shopify payload dumps, and
**no** approval-reason leakage.

## 11. Warning inventory

The authoritative fresh build emitted exactly **one** warning:

| Field | Value |
| --- | --- |
| Logger | `odoo.addons.shopify_connector_sale.models.shopify_connector_order_scan` |
| Module | `shopify_connector_sale` |
| Source | `models/shopify_connector_order_scan.py` |
| Message | `Order scan enqueue failed for store_id=97 error_type=UserError` |
| Expected? | Yes — emitted by a negative-path scan test asserting enqueue fails closed |
| Connector-attributable? | Yes (deliberate, test-induced) |
| Blocking? | No |

(The same warning recurs, test-induced, in the warm sale/product reruns for the corresponding
store ids; identical attribution.) No warning is dismissed without attribution.

## 12. Upgrade, lifecycle and dev-store — deferred (honest)

This Odoo.sh session is a single-injected-database container (AGENTS.md: one linked DB, no new-DB
creation). It **cannot** provide separate isolated baseline-upgrade (Environment B) or
uninstall/reinstall lifecycle (Environment C) databases. Per the mandate §12, these are classified as
**deferred release-readiness evidence — not a Campaign-4 blocker.** Read-only Shopify dev-store order
evidence remains **deferred to Wave 6** (no credentials available); **no Shopify mutation was
performed.**

## 13. Confirmations

- No production code changed. No test changed. (Documentation-only evidence commit.)
- No Shopify mutation; no network egress to Shopify.
- PR #176 remains open, draft and unmerged (asserted from local git; see §1 limitation).
- Protected refs unchanged (`checkpoint/core-r2-readonly-uat-2026-07-15` = `acd8c469…`).
- Wave 3 remains unstarted.

## 14. Recommendation

**READY FOR FRESH CLAUDE FINAL WAVE REVIEW.**

- Runtime-tested SHA: `63607dd87a8bfc253ee60ed00e0d761ee62c8776`
- Evidence commit SHA: recorded in the tracker (`docs/07-implementation-plan/mvp-program-state.md`)
  and the PR #176 report at commit time.

---

### Campaign history (preserved)

| Campaign | SHA | Build | Result |
| --- | --- | --- | --- |
| 1 (2026-07-17) | `2e1b1eb6…` | `35080469` | 5 failures / 6 errors (11 findings) |
| 2 (2026-07-18) | `d1af6d03…` | `35088811` | tax country fixture in `_tax()` still defective |
| 3 (2026-07-18) | `2525447c…` | `35095228` | 725 passed / 0 failed / 3 errors / 728 — three in `TestOrderTotalsGuard` |
| **4 (2026-07-18)** | **`63607dd8…`** | **`35100725`** | **0 failed / 0 error / 728 — GREEN** |
