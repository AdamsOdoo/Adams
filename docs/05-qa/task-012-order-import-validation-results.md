# Task 012 — Order Import Validation Results

## Status

**CORRECTED-HEAD RUNTIME CAMPAIGN 3 EXECUTED — CORRECTION REQUIRED (2026-07-18, build `35095228`, under revised control-room ruling [`5010851668`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5010851668)).** The sole authorized runtime candidate `2525447cee2d8a3371b1f4e669f61bcd50b20162` (the documentation head that reconciles fixture correction `6f32e4c8a2e6eac44bfb32e2cca0ea2bea3b1ea4`) was independently runtime-validated on authenticated Odoo.sh build `35095228` (DB `adamsmen-sol-wave-2-order-import-35095228`, Odoo 19.0, PostgreSQL 16.14). **The clean/full fresh install with tests enabled is NOT green:** the build's own install-with-tests (`install.log`) recorded `0 failed, 3 error(s) of 728 tests` — all three in `TestOrderTotalsGuard` (`test_order_and_source_tax_fingerprints_must_reconcile`; and the parametrised `test_tax_excluded_and_tax_included_orders_use_mapped_engine_taxes` sub-cases `included=False` and `included=True`), each an `account_tax.tax_group_id` (and `country_id`) NOT-NULL violation raised by the test's own `_map_tax()` helper (`shopify_connector_sale/tests/test_order_totals_guard.py:34-45`), which creates `account.tax` without an explicit country-consistent tax group. **This is the identical country-consistent-tax-fixture defect class that correction `6f32e4c` closed in `test_order_tax_resolution.py` but did NOT apply to the sibling `test_order_totals_guard.py`** (that commit changed only `test_order_tax_resolution.py`, +47/-3). `TestOrderTaxResolution` now passes at fresh install — finding #5 is closed there — but finding #5 (Odoo 19 country-consistent tax fixture) is **NOT fully closed**: it is OPEN in `test_order_totals_guard.py`. Under the revised ruling, isolated baseline-upgrade (B) and uninstall/reinstall lifecycle (C) databases are **no longer Wave 2 blockers** and are recorded as **deferred release-readiness evidence — NOT ENVIRONMENT BLOCKED**; the Wave 2 acceptance gate is now the complete authenticated Odoo.sh clean/full matrix, which is not green. Genuine independent-connection concurrency passed **3/3**; residue, security/redaction and registry checks are clean; the warm `-u` reruns surfaced only base-`account` `res_partner.autopost_bills` NOT-NULL artifacts that are **absent from the authoritative fresh install** and are not connector-attributable. **Recommendation: CORRECTION REQUIRED** — Sol test-fixture scope: apply the `6f32e4c` country-consistent tax + tax-group pattern to `test_order_totals_guard.py._map_tax` (and audit every remaining fixture that creates `account.tax` without an explicit `country_id`/`tax_group_id`). No production code and no test was changed by this audit. Runtime-tested SHA `2525447cee2d8a3371b1f4e669f61bcd50b20162`; documentation-only evidence commit recorded in "Corrected-head runtime validation campaign 3 — 2026-07-18 (build `35095228`)" below and in the session handoff. PR #176 remains open, draft and unmerged; SRR-03 remains CLOSED; Wave 3 remains unstarted.

**TAX FIXTURE CORRECTED — POST-CORRECTION RUNTIME PENDING — ENVIRONMENTS B/C NOT YET CONFIRMED (2026-07-18, HISTORICAL — SUPERSEDED BY CAMPAIGN 3 ABOVE, WHICH RUNTIME-VALIDATED THE CORRECTED HEAD AND FOUND THE CORRECTION INCOMPLETE).** The second corrected-head runtime campaign below (SHA `d1af6d03e3c51b9fa3d12dad00fd7c7766ec8bd5`, Odoo.sh build `35088811`, database `adamsmen-sol-wave-2-order-import-35088811`) closed ten of the eleven original findings (#1–4, #6–11) at runtime; finding #5 remained because the `_tax` test helper still omitted the Odoo-19-required `country_id`. The first campaign (SHA `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8`, build `35080469`, 5 failures / 6 errors, 11 unique findings) remains preserved below unchanged. **Accepted correction:** `6f32e4c8a2e6eac44bfb32e2cca0ea2bea3b1ea4` (`test(wave2): provide country-consistent Odoo 19 tax fixtures`), per control-room ruling [`5010554056`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5010554056) — deterministic country resolution; explicit country on the tax group; explicit country on the tax; identical tax/group company; identical tax/group country; the wrong-company fixture retained; all unsafe-mapping denials retained. **No production tax behavior changed and no importer behavior changed** (`shopify_connector_tax_mapping.py` `d114615553950d4322632767a1bed7d06d7edb85`; `shopify_connector_order_importer.py` `8b32f1cba5870588dae23c1cb3b426c41f1c7a75`, both unchanged). The authored Wave 2 method count remains **86**; no method was removed, renamed, skipped or weakened. **No post-correction Odoo pass is claimed.** This is a Claude documentation-only reconciliation per ruling [`5010654351`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5010654351). **Environment A** (clean/full) exists from the campaigns below and must not be spent alone again. **Environment B** (isolated baseline-upgrade) remains unproven: this session's capability audit found no reachable multi-database PostgreSQL 16.14 server and no usable Odoo 19 runner in this checkout. **Environment C** (isolated lifecycle) remains unproven for the same reason — no separate usable runner exists in this session. See "Environment B/C readiness audit — 2026-07-18 (this session)" below for the exact evidence. PR #176 remains open, draft and unmerged; Wave 3 remains unstarted.

**CORRECTED-HEAD RUNTIME CAMPAIGN EXECUTED — CORRECTION REQUIRED (2026-07-18, HISTORICAL — SUPERSEDED BY THE TAX-FIXTURE-CORRECTED ADDENDUM ABOVE).** The corrected runtime candidate `d1af6d03e3c51b9fa3d12dad00fd7c7766ec8bd5` was runtime-validated on authenticated Odoo.sh build `35088811` (DB `adamsmen-sol-wave-2-order-import-35088811`, Odoo 19.0, PostgreSQL 16.14). **The clean/full fresh install with tests enabled is NOT green:** it fails with `account_tax.country_id` NOT-NULL errors from `TestOrderTaxResolution` — i.e. prior **finding #5 (Odoo 19 tax fixtures) is only partially closed** (the correction added `tax_group_id` but the `_tax` test helper still omits the Odoo-19-required `country_id`). Ten of the eleven prior findings (#1–4, #6–11) are confirmed closed at runtime. Isolated **baseline-upgrade (B)** and **isolated-lifecycle (C)** environments **could not be prepared** in this single-injected-database container (ENVIRONMENT BLOCKED). See "Corrected-head runtime validation campaign — 2026-07-18" below for the full evidence. **Recommendation: CORRECTION REQUIRED.** PR #176 remains open, draft and unmerged; SRR-03 remains CLOSED; Wave 3 remains unstarted. This entry does not overwrite or reclassify the first (2026-07-17, build `35080469`) campaign, which is retained verbatim below.

**CORRECTIONS COMPLETE — CORRECTED-HEAD RUNTIME PENDING (2026-07-17).** See the "Correction addendum — 2026-07-17 (current status)" section below for the full current-facing record; all eleven runtime findings from the first campaign are dispositioned and committed, no corrected-head Odoo.sh pass exists yet, and PR #176 remains open, draft and unmerged.

**Exact-head Odoo.sh runtime validation campaign EXECUTED (2026-07-17, build `35080469`); outcome at that time: CORRECTION REQUIRED — 11 sale-module test failures; `shopify_connector_core` and `shopify_connector_product` green. (Historical — first-campaign record; superseded by the Correction addendum below: all eleven findings are now dispositioned and the correction batch is committed; corrected-head runtime remains pending.)** (The pre-runtime source-validation history below is retained and remains accurate. No source or test code was changed by the runtime operator.)

- Date: 2026-07-17
- Branch / PR: `sol/wave-2-order-import`; draft PR #176 → `mvp/program-integration`
- Verified base / merge base: `234c0bb50b3f61b7681e18f0b28839dee619cdb9`
- Audit starting head supplied by the product owner: `c62303611e7c5337e08d1632d0541be55df248ba`
- First audit freeze: `d348b9a180578992317840dc0e99b5349b89eada`
- Post-freeze discrepancy corrections: stronger dispatcher-commit concurrency proof and restoration of the complete research-handoff history
- Runtime build / database: **not available**
- Hard stop: **condition 5 — no authenticated Odoo.sh capability in this session**

This record's pre-runtime section does not claim an Odoo test pass; the runtime campaign section immediately below now supplies the executed runtime evidence.

## Corrected-head runtime validation campaign 3 — 2026-07-18 (build `35095228`)

> Independent control-room runtime audit of the sole authorized runtime candidate under revised control-room ruling
> [`5010851668`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5010851668). No source or test file was modified before, during, or as a
> result of this campaign. The runtime-tested SHA is recorded separately from the documentation-only evidence commit.
> Correction of the finding below is Sol implementation/test scope (DEC-032 / CLAUDE.md §13); the auditor made no code or
> test change. This campaign does not overwrite or reclassify the two earlier campaigns, both retained below.

### 1. Exact identity (verified before runtime)

- Runtime-tested SHA (== detached build head == branch tip `sol/wave-2-order-import` == `origin/sol/wave-2-order-import`): `2525447cee2d8a3371b1f4e669f61bcd50b20162`
- Base / merge-base (`mvp/program-integration`): `234c0bb50b3f61b7681e18f0b28839dee619cdb9` — confirmed ancestor of head
- Fixture correction `6f32e4c8a2e6eac44bfb32e2cca0ea2bea3b1ea4` confirmed in head ancestry; documentation reconciliation `2525447` is the current tip
- Changed files vs base: **29** (matches the authorized changeset); no commit exists after the authorized SHA at campaign start; working tree clean
- Build: `35095228`; Database: `adamsmen-sol-wave-2-order-import-35095228`; Odoo **19.0**; PostgreSQL **16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)**
- Module versions: `shopify_connector_core` `19.0.1.9.1`; `shopify_connector_product` `19.0.2.1.2`; `shopify_connector_sale` `19.0.2.0.0` (all `installed`)
- **PR/protected-ref limitation (recorded honestly):** this container has no `gh` CLI and no GitHub token; the GitHub API returns `404` unauthenticated. PR #176 draft/open/unmerged state and protected-ref state (`checkpoint/core-r2-readonly-uat-2026-07-15`, `main`, `Shopify-connector`, `mvp/program-integration`) **cannot be authenticated from this session** and are asserted only from local git (all four protected refs are untouched locally; the auditor performed no push to any of them, no merge, no ready-marking, and no Shopify mutation). Wave 3 remains unstarted (no Wave 3 branch/commit in local history).

### 2. Fresh install + registry (authoritative)

The build's own fresh install-with-tests (`install.log`, build `35095228`, exact head `2525447`) recorded the authoritative clean/full matrix:

- **`0 failed, 3 error(s) of 728 tests`** overall; **`Module shopify_connector_sale: 0 failures, 3 errors of 194 tests`**; `shopify_connector_core` and `shopify_connector_product` logged **no** failure/error tally (i.e. 0 errors each).
- Registry facts (verified in the running DB): exactly **one** order-scan cron (`Shopify Connector: Enqueue Order Scans`, active); the sale module `ir.model.access.csv` carries exactly **12** ACL rows (order.binding ×4, tax.mapping ×4, plus scan/importer/line rows); **no duplicate XML IDs** across the three connector modules (`SELECT module||'.'||name … HAVING count(*)>1` returns empty); LC-1 `ondelete` job types and replay policies load; store-setting defaults present.
- The only `autopost_bills` occurrence in the fresh-install log is a benign XML-load line (`loading account/wizard/account_autopost_bills_wizard.xml`), **not** a test error.

### 3. The genuine finding — finding #5 only partially closed (CORRECTION REQUIRED)

The three fresh-install errors are all in `TestOrderTotalsGuard`:

1. `TestOrderTotalsGuard.test_order_and_source_tax_fingerprints_must_reconcile`
2. `TestOrderTotalsGuard.test_tax_excluded_and_tax_included_orders_use_mapped_engine_taxes` (sub-case `included=False`)
3. `TestOrderTotalsGuard.test_tax_excluded_and_tax_included_orders_use_mapped_engine_taxes` (sub-case `included=True`, cascade `InFailedSqlTransaction`)

Exact database error (verbatim from `install.log`):

```
INSERT INTO "account_tax" (... "country_id" ... "tax_group_id" ...) VALUES (... NULL ... NULL ...) RETURNING "id"
ERROR: null value in column "tax_group_id" of relation "account_tax" violates not-null constraint
DETAIL:  Failing row contains (11, 1, 1, null, null, null, ... tax_group_id=null ..., "Order guard VAT 5 excluded", ...).
… SELECT "account_tax_group"."id" FROM "account_tax_group"
  WHERE ("account_tax_group"."company_id" IN (1) AND "account_tax_group"."country_id" IS NULL) …  LIMIT 1
```

**Root cause (Fact).** `TestOrderTotalsGuard._map_tax()` (`test_order_totals_guard.py:34-45`) creates `account.tax` with `company_id` but **no `country_id` and no `tax_group_id`**, relying on Odoo 19's default tax-group resolution. On a clean install the default lookup (`company_id IN (1) AND country_id IS NULL`) finds nothing — the DB holds only `account_tax_group` rows scoped to `company_id=1, country_id=233` (United States) and **none with `country_id IS NULL`** — so `tax_group_id` stays NULL and the Odoo-19 NOT-NULL constraint rejects the insert.

**Classification (Fact).** This is a **connector test-fixture defect** (test files under `addons/`, not production code) — the *same* anti-pattern that correction `6f32e4c` fixed in the sibling `test_order_tax_resolution.py` by creating an explicit country-consistent tax group and passing explicit `country_id` on both the tax and the group. That correction was **not** applied to `test_order_totals_guard.py`. Finding #5 (Odoo 19 country-consistent tax fixture) is therefore **closed in `test_order_tax_resolution.py` and OPEN in `test_order_totals_guard.py`** → **CORRECTION REQUIRED**. Per §5 of the mission and the "do not hide a connector-attributable failure behind an environment classification" rule, this failure is reported as the authoritative fresh-install result and is **not** reclassified as an environment artifact.

### 4. Full-suite matrix (authoritative fresh install vs warm reruns)

| Suite | Authoritative fresh install (`install.log`, build `35095228`) | Warm `-u … --test-enable` rerun (this session) |
| --- | --- | --- |
| `shopify_connector_sale` | **0 failed, 3 errors of 194** (all `TestOrderTotalsGuard`) | `0 failed, 0 error(s) of 194` |
| `shopify_connector_core` | 0 errors | `0 failed, 8 errors of 198` — all base-`account` `res_partner.autopost_bills` NOT-NULL warm-`-u` artifacts |
| `shopify_connector_product` | 0 errors | `0 failed, 2 errors of 163` — same `autopost_bills` warm-`-u` artifact class |
| **Total** | **0 failed, 3 errors of 728** | (cascade `-u` core run: `0 failed, 10 error(s) of 586`) |

**Warm-rerun artifact classification (Inference, evidenced).** The warm `res_partner.autopost_bills` NOT-NULL errors (10×, in unrelated tests such as `TestReadinessCheck`, `TestApiClient`, `TestJobEnqueue`, `TestProductRefreshAndStale`, `TestSourceGuardDetectors`) come from the base `account` module's `res_partner` extension during partial `-u` module updates. They do **not** appear anywhere in the authoritative fresh-install log and are **not** connector-attributable. The warm sale rerun reports `0/0/194` because the warm DB's `account_fiscal_country_id` is set (=233), so `account.tax`'s default tax group resolves — masking the fresh-install fixture defect. Per §5, the failing **fresh install is authoritative**; the passing warm sale rerun is the environment-sensitive artifact, not vice-versa.

### 5. Genuine concurrency — 3/3 PASS

`TestOrderDiscoveryConcurrencyGenuine` is `@tagged('post_install','-at_install','-standard','shopify_connector_order_discovery_concurrency')` — deliberately excluded from the standard suite and selected by its custom tag. Run three times (`-u shopify_connector_sale --test-enable --test-tags shopify_connector_order_discovery_concurrency`): each repetition reported **`0 failed, 0 error(s) of 2 tests`**. One job / one permanent binding / one sale order; losing transaction remains usable and commits; no deadlock; no leaked lock/session. These 2 `-standard` methods plus the 84 standard methods reconcile to the **86** authored Wave 2 methods.

### 6. Residue, security/redaction, resources — clean

- **Residue (post-campaign):** 0 idle-in-transaction sessions; 0 advisory locks; 0 orphan running jobs; 0 bindings with null store; 0 orphan tax mappings; 0 leftover `Genuine Order Discovery Race` stores (concurrency cleanup verified); 0 stray `odoo-bin` worker processes beyond the persistent background process. A single transient `ShareLock` waiter was observed once and cleared (not connector-attributable, no deadlock).
- **Security/redaction:** connector runtime logs contain no `Authorization: Bearer`, `access_token`, `x-shopify-access-token`, `shpat_`/`shpca_`, password, api-key/secret assignment, or `postgres://` connection string; no raw email/phone in connector log lines. The only `apikeys` hits are base Odoo's routine `res.users.apikeys` GC (0 entries).
- **SRR-03:** remains **CLOSED** — no genuine regression proven; core Wave 1 regression is clean at fresh install; the warm artifacts are base-`account` environment noise.

### 7. Eleven original findings (this campaign)

| # | Finding | Status at head `2525447` |
| --- | --- | --- |
| 1 | `account.payment` AST guard | PASS (fresh install, 0 sale errors outside #5 class) |
| 2 | COD snapshot | PASS |
| 3 | legal pending wait/expiry state | PASS |
| 4 | address-company deferral | PASS |
| 5 | Odoo 19 country-consistent tax fixture | **NOT FULLY CLOSED** — closed in `test_order_tax_resolution.py`, OPEN in `test_order_totals_guard.py` (3 fresh-install errors) |
| 6 | tax fingerprint pairwise distinctions and NFC | PASS (`TestOrderTaxResolution` green at fresh install) |
| 7 | Administrator backfill preview | PASS |
| 8 | atomic failed scan and retry | PASS |
| 9 | Administrator confirmation | PASS |
| 10 | read-all-orders boundary | PASS |
| 11 | stale/Boolean token rejection and non-admin denial | PASS |

### 8. Upgrade/lifecycle (B/C) and dev-store (§11/§12) under the revised ruling

- **Environments B (isolated baseline-upgrade) and C (isolated uninstall/reinstall lifecycle):** this Odoo.sh dev container is linked to a single injected database and cannot provision a second/disposable database. Per revised ruling `5010851668`, these are **deferred release-readiness evidence — NOT Wave 2 blockers and NOT ENVIRONMENT BLOCKED**. They remain to be executed in a multi-database-capable environment before final release readiness, but do not gate Wave 2 acceptance.
- **Dev-store (read-only):** no dev-store credentials were provisioned; no live Shopify call was made and no live Shopify claim is asserted. Deferred to Wave 6. Read-only dev-store access is not a Wave 2 blocker.

### Recommendation — CORRECTION REQUIRED (current-facing for campaign 3)

The authorized head `2525447` is **not green**: the authoritative clean/full fresh install fails with **3 `TestOrderTotalsGuard` errors** (`account_tax.tax_group_id`/`country_id` NOT-NULL), because the accepted fixture correction `6f32e4c` fixed the country-consistent-tax-fixture defect in `test_order_tax_resolution.py` only and left the identical pattern unpatched in `test_order_totals_guard.py`. The fix is Sol test-fixture scope (mirror the `6f32e4c` country-consistent tax + tax-group construction into `test_order_totals_guard.py._map_tax`, and audit any other fixture creating `account.tax` without explicit `country_id`/`tax_group_id`); the auditor changed no source or test. The B/C and dev-store environments are deferred release-readiness evidence, not Wave 2 blockers, under revised ruling `5010851668`. PR #176 remains open, draft and unmerged; SRR-03 remains CLOSED; Wave 3 remains unstarted.

## Environment B/C readiness audit — 2026-07-18 (this session, capability audit only)

> Documentation-only capability audit; no Odoo, PostgreSQL, or destructive lifecycle action was executed in this session.

- **Environment B (isolated baseline-upgrade — baseline `234c0bb50b3f61b7681e18f0b28839dee619cdb9` sale `19.0.1.2.1` → candidate sale `19.0.2.0.0`):** **BLOCKED.** No reachable PostgreSQL server in this checkout (`localhost:5432` connection refused; no cluster running); no way to install the baseline into a preserved database or upgrade it to the candidate.
- **Environment C (isolated lifecycle — historic-fixture conversion, uninstall, cleanup, reinstall, zero-residue proof):** **BLOCKED.** Same absence of a usable PostgreSQL/Odoo runtime; no way to create a second disposable database, install the corrected head, run LC-1 conversion, uninstall/reinstall `sale`, or verify residue.
- **Missing capability (concrete, verified, not assumed):** no running Docker daemon (`docker` binary is present but `/var/run/docker.sock` does not exist and there is no init system to start one — `systemctl` reports "not booted with systemd as init system"); no reachable PostgreSQL 16.14 server (`psql` connection to `localhost:5432` refused); no Odoo package or `odoo-bin` source present in this checkout (`python3 -c 'import odoo'` raises `ModuleNotFoundError`). This session is a normal authenticated git/shell/GitHub checkout with commit/push access, not a multi-database-capable Odoo 19/PostgreSQL 16.14 runner.
- **Result: B BLOCKED / C BLOCKED.** Neither environment is classified READY on documentation or assumption alone — both are BLOCKED on verified, concrete tooling absence in this session. Exact next infrastructure needed: a multi-database-capable Odoo 19 + PostgreSQL 16.14 runner (an Odoo.sh isolated dev/staging build that permits a second database, or a containerized runner with a live Docker daemon and a PostgreSQL 16.14 service) reachable from an authorized session, before B/C validation can be attempted.

## Corrected-head runtime validation campaign — 2026-07-18 (build `35088811`)

> Independent control-room runtime audit of the corrected candidate. No source or test file was modified before, during, or as a result of this campaign. The runtime-tested SHA is recorded here separately from any documentation-only evidence commit. Correction of the finding below is Sol implementation/test scope (DEC-032 / CLAUDE.md §13); the auditor made no code or test change.

### Environment (recorded)

- Runtime-tested SHA (== branch tip `sol/wave-2-order-import` == PR #176 head): `d1af6d03e3c51b9fa3d12dad00fd7c7766ec8bd5`
- Verified base / merge base (`mvp/program-integration`): `234c0bb50b3f61b7681e18f0b28839dee619cdb9` (ancestor of head; 29 changed files: 23 addon/test + 6 docs)
- Correction commits present in head history: `5897396`, `e4a75fc`, `6624028`, `3223741`, `7bd6df9`, `d1af6d0`
- Build: `35088811`; Database: `adamsmen-sol-wave-2-order-import-35088811`
- Odoo 19.0; PostgreSQL 16.14; modules: core `19.0.1.9.1`, product `19.0.2.1.2`, sale `19.0.2.0.0`
- Protected refs unchanged: `main=a5d4543`, `Shopify-connector=dd6ecb8`, checkpoint `acd8c46`
- Failure cap: `ODOO_TEST_MAX_FAILED_TESTS` unset in the operator shell (default = no early halt); the build's own install ran with the Odoo.sh default cap of `5`.

### Environment-preparation gate

- **A. Clean/full exact-head:** available (single injected DB) — **completed**.
- **B. Isolated baseline-upgrade (start at `234c0bb`, sale `19.0.1.2.1` → upgrade to `19.0.2.0.0`):** **BLOCKED.** This container is linked to a single injected database and forbids creating/connecting to a second one (AGENTS.md); PostgreSQL role privileges are restricted (`pg_roles` read denied). No second DB at the baseline SHA could be prepared.
- **C. Isolated lifecycle (separate disposable DB for uninstall/reinstall/residue):** **BLOCKED** for the same single-DB reason. Per the campaign rule, the destructive lifecycle scenario must not be run on the shared clean/full DB, so it was not performed.

### 1. Fresh install with tests enabled — NOT green (authoritative build evidence)

The build's own install-with-tests (`install.log`, corrected head `d1af6d0`) recorded:

- `shopify_connector_core`: 369 tests, **0 errors**; `shopify_connector_product`: 202 tests, **0 errors**.
- `shopify_connector_sale`: **0 failures, 5 errors of 160** — all in `TestOrderTaxResolution`, all `psycopg2.errors.NotNullViolation: null value in column "country_id" of relation "account_tax"`; the suite **halted at the build cap of 5** (`odoo.tests.result: Test suite halted: max failed tests already reached (5)`), so more of that class's `_tax`-using methods may be masked.
- Combined: `0 failed, 5 error(s) of 663 tests`; `odoo-bin` exit code 1 ("At least one test failed").

Registry/constraints/crons/ACLs/defaults verified on the live DB: 4 new models registered (`order.binding`, `order.importer`, `order.scan`, `tax.mapping`; `sale.order.line` extended); **all three permanent unique constraints** present (`order_binding_store_shopify_gid_uniq`, `order_binding_store_sale_order_uniq`, `tax_mapping_store_evidence_key_uniq`); **exactly one** sale-module `ir.cron`; **12 ACL rows** (customer.binding ×4 + order.binding ×4 + tax.mapping ×4; tax-mapping = Administrator write/create only, no role unlink); **no duplicate XML IDs**; store-setting defaults confirmed via `default_get` (`order_import_window=30`, `order_confirmation_policy=paid_only`, `manual_gateway_policy=require_approval`, `pending_wait_expiry=24`, `order_company_id=env.company`, include-test/scheduled-sync `False`).

### 2. Focused Wave 2 + full sale suite (no halt) — 1 genuine error

`--test-tags '/shopify_connector_sale'` and `-u shopify_connector_sale --test-enable` (failure cap lifted) both returned **`0 failed, 1 error of 194`** — the single error is:

- **`TestOrderTaxResolution.test_mapping_rejects_wrong_company_inactive_or_incompatible_tax`** → `NotNullViolation: null value in column "country_id" of relation "account_tax"`.

The 86 authored Wave 2 order-test methods are all discovered and (except the one above) pass. The other `null value` log signatures (`store_id`/`partner_id`/`shopify_gid` on bindings) are **expected constraint-assertion tests** (deliberately triggered, caught) and contribute 0 to the failure count.

### 3. The genuine finding — finding #5 only partially closed (CORRECTION REQUIRED)

- **Root cause:** the `_tax` test helper (`tests/test_order_tax_resolution.py:23–42`) creates `account.tax` with `tax_group_id` (the prior correction) but **without `country_id`**. In Odoo 19 `account.tax.country_id` is `required=True` (computed/precompute from company, → NULL for a freshly-created second company with no fiscal country). `test_mapping_rejects_wrong_company_...` (line 184) builds a tax for exactly such a second company → NOT-NULL violation.
- **Why 5 at cold install but 1 warm:** at at_install the main company's fiscal country is not yet resolvable, so multiple `_tax`-using methods fail; on a warmed DB only the deliberate second-company fixture fails. The count varies (1–5+) but the defect is one and the same and is confined to `TestOrderTaxResolution`.
- **Classification:** **test-fixture / Odoo-19-compatibility defect** — this is prior **finding #5 ("Odoo 19 tax fixtures")** incompletely closed (the correction added `tax_group_id` but did not add `country_id`).
- **Production is unaffected:** `ShopifyConnectorTaxMapping.account_tax_id` only *references* `account.tax` (`required=True, ondelete='restrict'`); the order importer only `.browse()/.search()`/reads taxes — **no `account.tax` auto-creation** (the explicit-mapping-only contract holds). But the module's test suite still fails a clean fresh install with tests enabled, so the head is not green.
- **Suggested fix (Sol scope, not applied here):** have `_tax` pass an explicit `country_id` (e.g. the target company's fiscal country) so multi-company fixtures satisfy Odoo 19's NOT-NULL constraint.

### 4. Core/product warm re-run — base-Odoo environment artifact (NOT a Wave 2 defect)

Re-running the core/product suites on the already-built DB surfaced `setUpClass` errors dominated by `null value in column "autopost_bills" of relation "res_partner"`. `autopost_bills` is a **standard `account`-module** field (`account/models/partner.py`), `character varying NOT NULL` with no DB default in this build; the connector never references it. This is the **same base-Odoo NOT-NULL-without-default family as issue #157** (`res_users.notification_type`/`color_scheme`, still present) and did **not** occur at the build's fresh sequential install (core/product 0 errors). Classification: **environment/infrastructure artifact**, not attributable to this PR.

### 5. Correction-regression proof — 10 of 11 prior findings CLOSED

Passing at runtime (their tests are green in the no-halt sale run): **#1** account.payment AST guard (`TestCustomerDuplicatePrevention`), **#2** COD snapshot read-model-only (`TestOrderCodImportReadModel`), **#3** pending wait/expiry legal transitions (`TestOrderConfirmationPolicy`), **#4** address-company deferral (`TestOrderCustomerResolution`), **#6** tax-fingerprint distinctness/NFC (`TestOrderTaxResolution` fingerprint methods), **#7/#9/#10/#11** Administrator backfill preview/confirm/read-all/stale-token (`TestOrderWatermarkBackfill`), **#8** partial-scan atomic rollback (`TestOrderWatermarkBackfill`). **Only #5 (tax fixtures / `country_id`) is not fully closed.**

### 6. Concurrency, ACL, residue, PII/credential, egress

- **Concurrency:** `TestOrderDiscoveryConcurrencyGenuine` (custom tag `shopify_connector_order_discovery_concurrency`) run **×3 → `0 failed, 0 errors of 2` each**; the genuine independent-connection race resolves via the permanent `order_binding_store_shopify_gid_uniq` constraint (losing connection hits a duplicate-key violation and is cleaned up) — exactly one binding survives.
- **ACL four-role matrix:** 12 rows, no unlink for any role; tax-mapping Administrator-write/create-only; order/customer-binding Auditor `r` / Operator `rc` / Reviewer `rw` / Admin `rwc` — matches the contract.
- **Residue (post-campaign):** 0 idle-in-transaction, 0 blocked locks, 0 advisory locks, 0 orphan bindings/jobs/mappings/settings/stores; 4 by-design connector crons; only the operator's own psql session active.
- **Credential/PII/egress:** no access tokens, Authorization headers, connection strings, or raw customer email/phone/address in any runtime log (the two credential-pattern matches are an ACL-denial line and a `TestCredentialService` test name — no secret values); **network-free** — no `myshopify.com/admin` egress, **no Shopify mutation**.
- **Warnings inventory:** the recurring docutils `<string>:38: (ERROR/3) Unexpected indentation.` is emitted at `install.log` line 660 **during `shopify_connector_core` loading** (core starts line 108, product line 900, sale line 1640) — i.e. inherited from core, **not introduced by Wave 2** (this PR changes zero core files). The only Wave-2 WARNING is `shopify_connector_order_scan: Order scan enqueue failed ... error_type=UserError`, a **test-induced, handled** fail-closed path.

### Recommendation — CORRECTION REQUIRED (historical — superseded by the tax-fixture-correction addendum at the top of this document)

The corrected head `d1af6d0` is **not green**: a clean fresh install with tests enabled fails on `TestOrderTaxResolution`'s `account_tax.country_id` NOT-NULL fixture (prior finding #5 only partially closed). This is a Sol test-fixture correction (add `country_id` to `_tax`); the auditor changed no source or test. Independently, the mandatory **isolated baseline-upgrade (B)** and **isolated-lifecycle (C)** environments **could not be prepared** in this single-injected-DB container and must be run in a multi-database-capable environment before PR #176 can be considered merge-ready. PR #176 remains open, draft and unmerged; SRR-03 remains CLOSED; Wave 3 remains unstarted.

## Correction addendum — 2026-07-17 (current status)

**CORRECTIONS COMPLETE — CORRECTED-HEAD RUNTIME PENDING.**

This addendum is the current-facing record for Task 012 / order import. The complete first-campaign evidence in "Exact-head runtime validation campaign — 2026-07-17" below is retained verbatim as historical evidence; its "CORRECTION REQUIRED" recommendation is superseded by this addendum.

- Failed implementation SHA: `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8`
- Build: `35080469`
- Database: `adamsmen-sol-wave-2-order-import-35080469`
- Evidence commit: `936cdf9ebc44c1655ffd2ad46b44d7f7619f895b`
- Failed result: **5 failures / 6 errors** (11 unique findings)
- Binding control-room comments: [`5006941549`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5006941549), [`5007682381`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5007682381), [`5008012338`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5008012338), [`5008123769`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5008123769)
- Correction commits: `589739667e0e575ee434cd541277bfdbcc54c5e5`, `e4a75fc49af622ba908d5a9f15e7272030c2379b`, `662402849401df604f048afd78953c06a6d956a0`, `32237410b45c37f92f80fc07d43ddd6541d6134d`
- All eleven findings (8 test-harness defects + 3 production-vs-test adjudication items) are resolved in source/tests per the binding rulings above; none remains unresolved or partially resolved.
- Whole-scan atomic rollback is the accepted and committed behavior (ruling `5006941549` item 3): a failed scan persists no child job or checkpoint change, and a successful retry re-enumerates and advances only after full pagination.
- Shopify address-`company` mapping to child-address `company_name` is removed and deferred to a post-MVP/B2B enhancement (ruling `5006941549` item 1; commit `662402849401df604f048afd78953c06a6d956a0`).
- Tax-fingerprint production code, version and NFC-normalization semantics are unchanged; only the defective set-cardinality test was replaced with explicit pairwise assertions (ruling `5006941549` item 2).
- All 86 authored Wave 2 order-import test methods remain; no test was removed, skipped, renamed, dynamically excluded or weakened by the correction batch.
- No corrected-head Odoo.sh pass exists yet. The next independent runtime campaign requires: a clean/full install environment; an isolated baseline-upgrade environment; and an isolated uninstall/reinstall lifecycle environment.
- PR #176 remains open, draft and unmerged.
- Wave 3 remains unstarted.

## Exact-head runtime validation campaign — 2026-07-17 (historical — first campaign; superseded by the Correction addendum above)

> Operator runtime campaign run against the frozen runtime candidate in an authenticated Odoo.sh dev build. No source or test file was modified before, during, or as a result of this campaign; the SHA below is the exact frozen head. Correction of the failures found is implementation/test work reserved to the Sol worker (DEC-032 / CLAUDE.md §13) and was **not** performed by the control-room operator.

### Environment (recorded)

- Tested SHA (== branch tip `sol/wave-2-order-import`): `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8`
- Merge base: `234c0bb50b3f61b7681e18f0b28839dee619cdb9` (direct ancestor; exactly 28 changed files; 25 commits since base)
- Odoo.sh build id `35080469`; database `adamsmen-sol-wave-2-order-import-35080469`
- Odoo `19.0` (base module `19.0.1.3`); PostgreSQL `16.14`
- Installed module versions: core `19.0.1.9.1`, product `19.0.2.1.2`, sale `19.0.2.0.0`
- Checkout clean, detached at the frozen head; protected checkpoint `acd8c4691e72cf5590f2a56228b08f183b76cd9a` unchanged; Wave 3 unstarted; SRR-03 remains CLOSED. (`gh`/PR-API state is not queryable in-container — PR status asserted from git-level evidence only.)

### Fresh install with tests enabled — green install, clean registry

Verified in the live DB: five Wave-2 models registered; `shopify_connector_order_binding` and `shopify_connector_tax_mapping` physical tables present (importer/scan are AbstractModel services, no table); three live `UNIQUE` constraints — order `(store_id, shopify_gid)`, order `(store_id, sale_order_id)`, tax `(store_id, shopify_tax_evidence_key)`; both job types `order_import_sync` and `order_import_scan` registered with LC-1 `ondelete` reassignment and `remote_read_replay_safe` replay policy; order-scan cron loaded exactly once (15-minute, active); twelve ACL rows resolve for the four roles (tax-mapping = Administrator write/create only, no role unlink; order-binding = no role unlink); zero duplicate XML IDs; documented store-settings defaults present (`paid_only`, `require_approval`, empty allowlist, window 30, expiry 24, include-test False, scheduled-sync False, company = `env.company`). No migrations directory (none required).

### Test execution (failure cap lifted: `ODOO_TEST_MAX_FAILED_TESTS` raised from the build's `5`)

| Suite | Command | Result |
|---|---|---|
| `shopify_connector_core` (own tests) | `-u shopify_connector_core --test-enable` | **0 failed / 0 errors** (green; 291 tests / 198 at-install) |
| `shopify_connector_product` (own tests) | `-u shopify_connector_product --test-enable` | **0 failed / 0 errors** (green; 183 tests) |
| `shopify_connector_sale` (standard) | `-u shopify_connector_sale --test-enable` | **5 failed / 6 errors of 194** (232 methods, 13.8 s) |
| Order-discovery concurrency (genuine independent PG connections) | `--test-tags shopify_connector_order_discovery_concurrency` ×3 | **3/3 repetitions 0 failed / 0 errors of 2** |

The 86 authored order-import methods = 76 pass / 10 fail (the 2 genuine-connection order tests are `-standard`, excluded from the 194 and run/green separately). The eleventh failure is an inherited Wave-1 customer test.

> Cascade-attribution note: a `-u shopify_connector_core` run cascades to dependents, so Odoo's per-module lines report "0 failures, 8 errors (core)" and "0 failures, 2 errors (product)". These are **double-counting of the same 11 sale failures** during dependents' post_install — verified by extracting the full FAIL/ERROR header set: exactly **11 unique headers, all `shopify_connector_sale`**; zero core-own or product-own test failed.

### Complete sale-module failure inventory (5 FAIL + 6 ERROR) with classification

| # | Class.method | Verdict | Root cause | Classification |
|---|---|---|---|---|
| 1 | `TestCustomerDuplicatePrevention.test_source_level_no_order_product_inventory_fulfillment_models` | FAIL | `assertNotIn('account.payment', src)` matches the legitimate `account.payment.term` (order payment term) added to `store_settings.py` | Wave-2 test defect (over-broad inherited Wave-1 source guard; production correct) |
| 2 | `TestOrderCodImportReadModel.test_successful_manual_transaction_is_snapshot_only` | ERROR | searches `account.payment` by field `ref`, which does not exist on that model in Odoo 19 | Wave-2 test defect / Odoo-19 compatibility |
| 3 | `TestOrderConfirmationPolicy.test_pending_wait_and_expiry_use_existing_job_states` | ERROR | `expired` job fixture built with `state='queued'`; handler calls `_transition_skipped` → `queued→skipped` illegal. Matrix allows `running→skipped`; real dispatch runs handlers on `running` jobs | Wave-2 test-fixture defect (production expiry path correct) |
| 4 | `TestOrderCustomerResolution.test_addresses_are_child_records_and_deduplicate_on_refresh_path` | FAIL | child address `company_name != 'Example Co'` | **Needs production-vs-test adjudication** (does the importer map Shopify address `company` → `res.partner.company_name` on child addresses?) |
| 5 | `TestOrderTaxResolution.test_mapping_rejects_wrong_company_inactive_or_incompatible_tax` | ERROR | `_tax()` helper creates `account.tax` without `tax_group_id`, which is NOT NULL in Odoo 19 (surfaced when the fixture targets a second company with no resolvable default group) | Wave-2 test defect / Odoo-19 compatibility |
| 6 | `TestOrderTaxResolution.test_v1_fingerprint_is_full_tuple_versioned_and_fold_free` | FAIL | expects 8 distinct fingerprints, gets 7 — two evidence variants collide (most likely `source=None` vs `source=''`) | **Needs production-vs-test adjudication** (financial tax-fingerprint contract: are None and empty source intended to be distinct?) |
| 7 | `TestOrderWatermarkBackfill.test_confirm_requires_exact_current_preview_token_then_enqueues` | ERROR | `preview_backfill`/`confirm_backfill` invoked from the default `SUPERUSER` env, which is not in `group_shopify_connector_admin`; `_assert_admin` raises `AccessError` | Wave-2 test defect (production `_assert_admin` gate correct) |
| 8 | `TestOrderWatermarkBackfill.test_partial_page_failure_holds_watermark_and_remains_resumable` | FAIL | expected 1 enqueued `order_import_sync` job after a mid-scan failure, found 0 | **Needs production-vs-test adjudication** (resumable-partial-page contract vs. whole-scan transactional rollback) |
| 9 | `TestOrderWatermarkBackfill.test_preview_classifies_all_buckets_and_creates_nothing` | ERROR | positive-path `preview_backfill` from default env (not Administrator) | Wave-2 test defect (admin context) |
| 10 | `TestOrderWatermarkBackfill.test_read_all_orders_honesty_never_silently_truncates` | FAIL | expected `UserError('Partner Dashboard')`; admin gate raised `AccessError` first (default env not Administrator) | Wave-2 test defect (admin context) |
| 11 | `TestOrderWatermarkBackfill.test_stale_or_boolean_confirmation_never_enqueues` | ERROR | `preview_backfill` from default env (not Administrator) | Wave-2 test defect (admin context) |

Summary: **8 Wave-2 test-harness defects** (including 3 with an Odoo-19-compatibility flavour and 4 sharing the single "backfill positive path not invoked as Administrator" root cause) + **3 items requiring production-vs-test adjudication** (#4 address `company` mapping, #6 tax-fingerprint collision, #8 partial-page resumability). **No confirmed production defect was found**; the three adjudication items could resolve either way and touch financial-fingerprint correctness, the address data model, and a resumability guarantee — they must be routed through architecture review rather than "fixed to make the test pass".

### Business-contract evidence that PASSED at runtime

Protected-field forge/clear guard; complete 50-field stored-field classification; empty PII snapshot / no-customer-PII contract; tax-mapping ACL (Administrator write/create only, no role unlink); manual-gateway approval permissions (Reviewer/Administrator allowed, Auditor/Operator denied) with reason redaction; the full 8-financial-state × 3-confirmation-policy matrix; all manual-gateway policies + COD read-model; scan enumerates/enqueues only and never imports inline; genuine two-connection binding race → exactly one permanent binding, one sale order, one active job, losing path cleaned up (3 independent OS-process repetitions).

### Residue / credential / PII / log audit — clean

0 idle-in-transaction and 0 leaked non-self sessions on the DB; 0 advisory locks; 0 running / 0 retry-waiting jobs; 0 call-leases; 0 leftover order bindings / tax mappings / test stores after all suites; no Shopify access-token, `Authorization`/`Bearer`, connection-string, or raw customer PII in any runtime log; evidence-redaction machinery active; the order-binding table exposes only identifier columns (`shopify_order_name`, `manual_gateway_name`) — no customer email/phone/address/name column. No outbound Shopify HTTP occurred (network-free via patched `execute_business`); no Shopify mutation.

### Not runtime-exercised — environment-constrained / deferred

- **§4 baseline-upgrade** (`19.0.1.2.1 → 19.0.2.0.0`) and **§10 isolated uninstall/reinstall lifecycle**: the container is bound to a single injected database (`-d` is auto-injected) and the scoped PostgreSQL role cannot create a second database; these were not performed rather than mutate/destroy the frozen-head build. Structural upgrade-safety indicators are green (no migrations directory; fresh-install of the new columns is green; new NOT-NULL settings columns rely on the standard ORM `default=` backfill during `-u`; `ondelete`/`selection_add` register cleanly). The live upgrade-replay and uninstall/reinstall remain deferred to an environment that permits a second database.
- **Issue #157 accommodation**: NOT applied — the `notification_type`/`color_scheme` defect did not reproduce.
- **Read-only dev-store evidence (§15)**: no authenticated Shopify credentials are available in this session; no live-evidence claim is made; deferred to Wave 6.

### Recommendation — CORRECTION REQUIRED (historical; superseded by the Correction addendum above)

The frozen runtime candidate `2e1b1eb…` is **not green**. Failed SHA: `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8`. The corrected SHA is to be recorded by the corrector alongside a corrected-head rerun. Correcting the 8 test-harness defects and adjudicating the 3 production-vs-test contract questions is implementation/test work reserved to the Sol worker under DEC-032 / CLAUDE.md §13; the control-room operator made no code or test change. PR #176 remains draft, open and unmerged; Wave 3 remains unstarted. This recommendation reflects the first campaign only; see the Correction addendum near the top of this document for the current, corrected-head-runtime-pending status.

## Implemented scope

- PII-free `shopify.connector.order.binding` with permanent per-store Shopify GID and sale-order uniqueness, complete fail-closed stored-field classification, manual-gateway approval provenance, and Reviewer/Administrator audited approval action.
- `sale.order.line.shopify_line_item_gid` trace field.
- Four read-only importer GraphQL operations: header plus complete line-item, shipping-line and discount-application pagination. Every transport uses `execute_business`; no network call occurs in scan classification or local readiness.
- One read-only order-scan GraphQL operation. Scan enumerates and enqueues only; it never imports inline.
- Atomic whole-order creation and binding; existing bindings refresh evidence without rewriting commercial lines.
- Product variant/template binding-chain resolution; custom-line and connector service products are idempotent and store-scoped.
- Existing customer binding/import sequence, guest email match/create, fallback partner and child-address deduplication.
- Decimal money validation; equal-currency shop/presentment checks; unsupported edit/refund/duty/fee/tip/cash-rounding gates; bounded whole-order reconciliation.
- Versioned exact tax fingerprint and explicit Administrator-maintained mapping; no automatic `account.tax` creation.
- Paid/authorized/pending/partial/terminal confirmation policies; manual-gateway policies and approval refresh; COD read model only.
- `order_import_sync` and `order_import_scan` handlers, `sale_domain_enabled` gate, LC-1 historic conversion and `remote_read_replay_safe` policy.

## Static and source evidence

The complete audit at `d348b9a...` recorded:

- exact 20 Wave-2 changed Python files parsed successfully;
- sale cron XML, manifest and ACL CSV parsed; manifest version `19.0.2.0.0`; ACL inventory 12 rows;
- five GraphQL operation constants, all `query`, zero `mutation`;
- `execute_business` present; raw `.execute()` and `with_context` transport bypasses absent;
- five new models and eleven tests imported exactly once;
- both job types registered once with LC-1 `ondelete` conversion and `remote_read_replay_safe`;
- exact 50-field protected order-binding set and empty `_pii_snapshot_fields()`;
- no Shopify mutation, `account.tax` auto-create, TODO, FIXME, `NotImplemented`, skipped test or broad `assertRaises(Exception)`;
- duplicate XML ID, ACL ID, model, job-type and selection-value scans clean;
- query/parser field coverage reconciled, including explicitly retained evidence-only fields;
- 86 unique test methods across the exact 11 locked order test files.

The post-freeze test correction did not add, remove, skip or rename a test method; the exact count remains 86. No Odoo runtime result is inferred from these source checks.

## Explicit bounds

| Boundary | Value |
| --- | --- |
| Line items | 100/page × 100 pages = 10,000 |
| Shipping lines | 50/page × 100 pages = 5,000 |
| Discount applications | 50/page × 100 pages = 5,000 |
| Order scan / preview | 100/page × 100 pages = 10,000 candidates |
| Solver | K=2; at most 2 dependent lines; at most 25 vectors |
| Tax suggestions | 20 non-binding candidates |
| Sale-line description | 512 characters |
| Pending-payment recheck | 15 minutes |
| Watermark overlap | 30 minutes |
| Currency posture | rounding finer than 0.01 fails closed pending named dev-store evidence |

## Contract-to-code-to-test traceability

Legend: **S** = implemented and statically proven; **R** = implemented, with runtime-only proof remaining; **N/A** = not applicable. No requirement is unclassified.

| Contract requirement | Exact production symbol | Positive proof | Negative / fail-closed proof | Security / concurrency | Runtime | Status |
| --- | --- | --- | --- | --- | --- | --- |
| DoR registration: five models, eleven tests, dependency/data order | `models/__init__.py`; `tests/__init__.py`; `__manifest__.py` | `test_all_five_model_files_are_registered_exactly_once`; `test_manifest_dependency_graph_and_registration_contract` | duplicate/import-count assertions | N/A | fresh install/upgrade | R |
| D-012-1 permanent binding and dual uniqueness | `ShopifyConnectorOrderBinding`; `_store_shopify_gid_uniq`; `_store_sale_order_uniq` | required-field/uniqueness and repeat-import tests | direct duplicate constraints | four-role protected-field matrix; two-connection binding race | DB constraints | R |
| D-012-1 PII-free binding | `_pii_snapshot_fields`; `_additional_protected_binding_fields` | identity/PII and exact-classification tests | excluded-field/query and redaction guards | direct create/write/clear denial | model setup | R |
| D-012-2 read-only header/detail retrieval | `import_order_sync`; four importer query constants; `execute_business` | query-minimization and pagination tests | mutation/raw-execute/torn-page/duplicate-node guards | N/A | mocked transport execution | R |
| D-012-2 explicit pagination bounds | `_collect_connection`; `ShopifyConnectorOrderScan._enumerate` | 100-line and multi-page tests | page-ceiling/repeated-cursor failures | N/A | Odoo execution | R |
| D-012-3 atomic whole-order import | `_apply_import`; outer and nested savepoints | happy-path and repeat import | financial mismatch/null status/race rollback | genuine two-connection race | transaction behavior | R |
| D-012-3 rediscovery refreshes evidence, never rewrites lines | `_refresh_existing`; `_binding_financial_evidence_matches` | authorized-to-paid and repeat import | changed-money stale-quotation guard | binding uniqueness | runtime ORM | R |
| D-012-4 bounded/redacted review evidence | `_redact_evidence`; `_safe_evidence`; `_safe_gateway_evidence`; job transitions | preview/redaction tests | PII string-surface assertions | audit/log scan | runtime logs | R |
| D-012-5 customer resolution reuses accepted paths | `_resolve_customer`; existing customer importer/matcher | eight customer-resolution tests | ambiguity/company/no-PII fallback holds | inherited binding ACLs | ORM matching | R |
| D-012-6 product/custom/gift-card resolution | `_resolve_line_product`; connector service-product helpers | service-product, custom and gift-card imports | missing product holds then exact retry | inherited product bindings | ORM products | R |
| D-012-7 exact decimal/totals policy | money validators; `_precreation_gates`; `_solve_and_assert_totals`; bounded solver | exact tax-free/tax-included/discount/high-value/zero-decimal tests | currency/original/current/tip/duty/fee/rounding failures | N/A | Odoo tax engine | R |
| D-012-8 financial-state and confirmation policy | `_confirmation_outcome`; `_handle_order_import_sync` | complete 8-state × 3-policy matrix | null/reversal/partial/pending/expiry routes | protected snapshots | job transitions | R |
| D-012-9 explicit tax mapping only | `ShopifyConnectorTaxMapping`; `_resolve_tax` | explicit mapped-tax reuse | no auto-create/rate fallback; company/inactive/incompatible rejection | four-role ACL matrix | ACL/constraint setup | R |
| D-012-10 source-tax fingerprint | `build_tax_fingerprint`; `canonical_tax_rate`; preview helpers | full-tuple/version/case/NFC tests | collision/shape/uniqueness tests | Administrator-only create/write | DB uniqueness | R |
| D-012-11 COD read model only | binding COD fields; `_binding_snapshot_vals`; `_manual_collected_amount` | four COD tests | source guard forbids payment/mark-paid behavior | protected fields | ORM initialization | R |
| D-012-12 handler/gating/replay | `ShopifyConnectorJobOrderExtension`; `ShopifyConnectorJobDispatchOrderExtension`; `_handle_order_import_sync` | handler/replay/source guards | disabled/stale store refusal | inherited JOB-ACTIONS | dispatcher regression | R |
| DEC-035 equal-currency/MoneyBag policy | `_validate_money_bag_shape`; `_validate_money_bag_currency`; `_money_equal`; `_precreation_gates` | exact amount/currency tests | both-side mismatch failures | N/A | Decimal/currency runtime | R |
| DEC-035 taxes/discounts/shipping/tips/duties/fees/rounding | parser, mapping and solver helpers | mapped taxes, all-discount and shipping tests | unsupported-component gates | N/A | Odoo tax engine | R |
| DEC-035 three confirmation policies | settings + `_confirmation_outcome` | 8×3 matrix | changed evidence/no stale confirm | protected policy evidence | runtime | R |
| DEC-035 three manual-gateway policies | `_classify_manual_gateway`; `_confirmation_outcome` | all-policy/COD matrix | unapproved/card-PENDING/mixed/malformed guards | N/A | runtime | R |
| Manual approval authorization/reason/provenance | `action_approve_manual_gateway_order` | Reviewer success + Administrator path | Auditor/Operator, empty reason, policy/gateway/evidence/state/company refusals | exact two-field quotation read sudo | ACL/action | R |
| Manual approval authoritative refresh/idempotency | approval enqueue + `_refresh_existing` | refresh-confirm and repeated approval | stale/changed evidence remains draft/review | one active job | job/runtime | R |
| Manual approval atomic audit/enqueue | action savepoint; `_create_lifecycle_audit_job`; enqueue service | exact actor/timestamp/one audit | audit and enqueue failure rollbacks | redacted reason | transaction/log | R |
| DoR order defaults/readiness | settings fields; `_settings_for_store`; `_resolve_pricelist`; `_validate_payment_term` | exact company/pricelist/payment-term/team tests | missing configuration failures | inherited Administrator settings ACL | upgrade/defaults | R |
| D-A6-2 enqueue-only manual/selected/scan | `_enqueue_order_scan`; `action_sync_orders_now`; `action_sync_selected`; `_enqueue_order` | trigger/enumeration tests | importer-not-called and collision tests | Operator/Administrator gates | cron/job | R |
| D-A6-3 opt-in scheduled cron | `_cron_enqueue_order_scans`; cron XML | both flags + connected store | disabled/disconnected refusal; per-store error continuation | internal cron | XML/cron | R |
| D-A6-4 30-minute watermark and safe checkpoint | `_incremental_start`; `run_scan`; `_enumerate` | overlap/complete-page advance | partial failure holds checkpoint | one exact settings checkpoint sudo | DB/cron | R |
| D-A6-6 stale generation/replay refusal | enqueue service + inherited generation/domain contracts | fresh-generation paths | stale/disconnected/disabled tests | replay-policy guard | dispatcher | R |
| PD-RB preview has zero writes | `preview_backfill`; `_enumerate(enqueue=False)` | bucket classification | non-admin and zero business/job effects | Administrator gate | ORM/cache | R |
| PD-RB token binds exact evidence | `_preview_token`; `confirm_backfill` | valid token enqueue/idempotency | Boolean/stale/generation-changed token refusal | Administrator gate | ORM | R |
| 60-day/read-all-orders honesty and bounds | `_assert_access_window`; `_validate_backfill_range`; `_enumerate` | in-window preview/confirm | over-window and truncation refusal | Administrator gate | Shopify fixture/runtime | R |
| LC-1 historic conversion | both `selection_add` `ondelete` handlers | source-registration test | inherited immutable `original_job_type` guard | inherited SEC-1 | uninstall/reinstall | R |
| No Wave 3+, mutation, UI, webhook or Layer-2 scope | complete Wave-2 production source | negative AST/source guards | forbidden-symbol scan | N/A | N/A | S |

## Complete 86-test inventory

The category shown is primary; many tests cover multiple acceptance criteria.

| Class | Category | Exact methods |
| --- | --- | --- |
| `TestOrderBinding` | schema/model; protected fields; ACL/security | `test_identity_and_pii_contract`; `test_every_stored_connector_field_is_classified`; `test_required_fields_and_uniqueness`; `test_all_roles_cannot_forge_or_clear_protected_fields` |
| `TestOrderImportMappingStatic` | source/AST guard; schema/model; lifecycle | `test_all_five_model_files_are_registered_exactly_once`; `test_four_graphql_operations_are_read_only_and_minimal`; `test_execute_business_only_and_no_context_bypass`; `test_exact_sudo_inventory_and_dispatch_create_guard`; `test_manifest_dependency_graph_and_registration_contract`; `test_job_types_have_lc1_ondelete_and_replay_policy`; `test_no_tax_autocreate_or_shopify_mutation_surface`; `test_redaction_extension_covers_direct_order_pii`; `test_connection_pagination_collects_once_and_detects_torn_reads`; `test_duplicate_node_across_pages_fails_closed` |
| `TestOrderImportMappingFunctional` | customer/product resolution; totals; regression | `test_connector_service_products_are_idempotent_and_store_scoped`; `test_one_hundred_line_order_imports_without_truncation` |
| `TestOrderTotalsGuard` | totals; tax; financial state | `test_null_financial_status_is_fatal_schema_mismatch`; `test_null_original_tax_is_schema_mismatch_even_when_current_zero`; `test_edit_refund_and_shipping_gates_hold_whole_order`; `test_duty_first_fee_cash_rounding_and_tip_gates`; `test_currency_gate_checks_both_moneybag_sides`; `test_original_and_current_money_amounts_must_match`; `test_basic_tax_free_order_reconciles_exactly`; `test_exact_all_discount_line_is_not_double_subtracted`; `test_financial_mismatch_rolls_back_order_and_binding`; `test_tax_excluded_and_tax_included_orders_use_mapped_engine_taxes`; `test_order_and_source_tax_fingerprints_must_reconcile`; `test_high_value_discount_uses_exact_negative_tax_preserving_residual`; `test_zero_decimal_currency_imports_but_three_decimal_is_held` |
| `TestOrderTaxResolution` | tax; ACL/security | `test_v1_fingerprint_is_full_tuple_versioned_and_fold_free`; `test_previews_are_bounded_and_redacted`; `test_mapping_acl_is_admin_write_create_only_and_no_unlink`; `test_mapping_rejects_wrong_company_inactive_or_incompatible_tax`; `test_explicit_mapping_only_resolution`; `test_mapping_key_shape_and_uniqueness` |
| `TestOrderDuplicatePrevention` | duplicate prevention | `test_repeat_import_refreshes_one_permanent_binding_and_order`; `test_every_discovery_source_collides_on_same_entity_identity`; `test_overlapping_windows_and_repeated_pages_do_not_duplicate`; `test_database_binding_constraints_are_the_last_race_anchor` |
| `TestOrderDiscoveryConcurrencyGenuine` | concurrency | `test_two_connections_return_one_scan_job`; `test_two_connections_create_one_permanent_binding_and_sale_order` |
| `TestOrderCustomerResolution` | customer/product resolution | `test_existing_customer_binding_has_priority_and_parent_is_unchanged`; `test_embedded_customer_reuses_indexed_email_match`; `test_embedded_customer_confident_no_match_creates_person_binding`; `test_guest_email_match_and_no_pii_fallback`; `test_ambiguous_customer_holds_whole_order_and_redacts_evidence`; `test_customer_company_boundary_blocks_before_order_creation`; `test_addresses_are_child_records_and_deduplicate_on_refresh_path`; `test_abandoned_checkouts_never_enter_order_pipeline` |
| `TestOrderConfirmationPolicy` | confirmation policy; financial state | `test_complete_eight_state_by_three_policy_matrix`; `test_authorized_to_paid_refresh_confirms_without_line_rewrite`; `test_post_confirmation_cancellation_is_evidence_only`; `test_post_confirmation_payment_evidence_loss_is_note_only`; `test_changed_money_never_confirms_stale_quotation`; `test_pending_wait_and_expiry_use_existing_job_states`; `test_null_status_routes_failed_final_without_handler_replay` |
| `TestOrderManualGatewayOverlay` | manual gateway; COD; ACL/security | `test_gateway_diagnostic_evidence_redacts_every_string_surface`; `test_all_manual_gateway_policies_and_cod_read_model`; `test_unapproved_and_card_pending_never_take_manual_path`; `test_mixed_transaction_imports_review_draft`; `test_malformed_transaction_authority_is_review_never_confirmation`; `test_approval_permissions_reason_provenance_and_redaction`; `test_approval_refreshes_before_confirm_and_is_idempotent`; `test_changed_evidence_supersedes_approval_without_confirming`; `test_later_paid_evidence_reuses_binding_without_pending_approval`; `test_paid_change_after_recorded_approval_stays_review_draft`; `test_atomic_rollback_when_audit_creation_fails`; `test_policy_or_gateway_change_refuses_without_audit` |
| `TestOrderWatermarkBackfill` | watermark/backfill; ACL/security | `test_watermark_uses_thirty_minute_overlap`; `test_watermark_advances_only_after_complete_pagination`; `test_partial_page_failure_holds_watermark_and_remains_resumable`; `test_preview_classifies_all_buckets_and_creates_nothing`; `test_confirm_requires_exact_current_preview_token_then_enqueues`; `test_stale_or_boolean_confirmation_never_enqueues`; `test_read_all_orders_honesty_never_silently_truncates` |
| `TestOrderCodImportReadModel` | COD; source/AST guard | `test_cod_dimensions_initialize_without_accounting_side_effects`; `test_successful_manual_transaction_is_snapshot_only`; `test_non_cod_order_does_not_acquire_cod_flag`; `test_source_contains_no_mark_paid_or_payment_creation` |
| `TestOrderScanTriggers` | scan; source/AST guard; regression | `test_manual_store_trigger_is_role_gated_enqueue_only_and_idempotent`; `test_selected_binding_trigger_is_enqueue_only_and_collision_safe`; `test_cron_requires_both_flags_and_connected_store`; `test_scan_enumerates_and_enqueues_but_never_imports_inline`; `test_pagination_and_duplicate_edge_fail_closed`; `test_store_progress_helpers_are_nonstored_and_state_accurate`; `test_disconnected_store_and_disabled_domain_refuse_manual_scan` |

There are exactly 86 unique methods: no duplicate names, skips, dynamically excluded methods, placeholder assertions or broad `assertRaises(Exception)`.

## Concurrency structural proof

Both tagged tests open independent `db_connect(dbname).cursor()` connections, set bounded statement/lock timeouts, commit fixtures before racing, and use a start barrier plus a second barrier at the exact production seam.

- The scan race delegates to the real enqueue service. Every worker captures its outcome, closes its cursor in `finally`, and the parent fails on live threads, missing outcomes, unexpected error types or a row count other than one.
- The permanent-binding race delegates to the real precreation gates and real importer. The winner commits normally. The `concurrency_race_conflict` loser intentionally executes `SELECT 1` and commits in the same transaction after catching `JobHandlerError`, matching the dispatcher's continuation posture; therefore the test fails if the importer's outer savepoint did not restore transaction usability.
- Final SQL asserts exactly one binding, one distinct bound `sale_order_id`, and exactly one sale order with the race's unique Shopify-origin marker. An orphan losing quotation therefore fails the test instead of being hidden by a full worker rollback or by a query limited to bound orders.
- Cleanup deletes both bound orders and any same-origin orphan candidate, then closes every connection.

Actual overlap, PostgreSQL lock timing and Odoo registry behavior remain runtime-only until the exact-head Odoo.sh repetitions run.

## Install, upgrade and migration precheck

- Baseline sale version: `19.0.1.2.1`; Wave-2 version: `19.0.2.0.0`.
- No migration directory is required. The order binding and tax mapping are new tables; their required fields are populated by sanctioned create services. `sale.order.line.shopify_line_item_gid` is nullable.
- Existing settings rows receive ORM/database-safe defaults: confirmation `paid_only`, manual policy `require_approval`, gateways empty, window 30, pending expiry 24, include-test False, scheduled False, and company from the active company. Optional pricelist/team/payment-term/checkpoint remain null; importer readiness fails closed until required operational mappings exist.
- Existing customer bindings and partners receive no new field. Order snapshot/provenance/COD fields are on a new table and have no legacy-row backfill risk. The tax fingerprint version default applies only to new tax-mapping rows.
- Both new job selections have LC-1 `ondelete` historic conversion. Cron XML is `noupdate=1`; ACL and model/XML IDs are unique. Uninstall selection cleanup, historic conversion, cron/ACL removal and reinstall remain runtime proof.
- Rollback is database backup restoration plus source revert before production, or forward-disable with preserved imported records in production. Uninstalling `shopify_connector_sale` is not an authorized rollback because it also owns customer history.

## Security, data minimization and exact sudo inventory

The ACL CSV has 12 rows. Order binding follows the accepted Auditor `r`, Operator `rc`, Reviewer `rw`, Administrator `rwc` pattern. Tax mapping is read-only for Auditor/Operator/Reviewer and `rwc` for Administrator. No row grants unlink.

The exact 50 protected order-binding fields comprise nine common binding fields, `sale_order_id`, and all 40 concrete snapshot/provenance/COD fields. All four approval-provenance fields are protected; direct create/write/clear attempts are denied.

| File:line | Symbol | Narrow justification |
| --- | --- | --- |
| `shopify_connector_order_importer.py:530` | `_apply_import` | sanctioned creation of the complete protected order binding |
| `shopify_connector_order_importer.py:2393` | `_refresh_existing` | sanctioned evidence/snapshot refresh only |
| `shopify_connector_order_binding.py:189` | `action_approve_manual_gateway_order` | read only linked quotation `company_id` and `state`; connector roles intentionally do not inherit Sales ACLs |
| `shopify_connector_order_binding.py:234` | same action | write only the four protected approval-provenance fields after caller-role/company/evidence checks |
| `shopify_connector_order_scan.py:73` | `run_scan` | advance only the protected per-store checkpoint after complete pagination |

There is no tax-mapping sudo, public context bypass, broad public-method sudo or job creation outside the enqueue service. Job payloads contain identifiers, hashes and bounded non-PII evidence only. Preview tokens and tax fingerprints use canonicalized non-PII evidence; they never hash raw customer PII, credentials, access tokens, Authorization headers or full Shopify payloads. Runtime log/residue inspection remains mandatory.

## Documentation-accuracy corrections

The final discrepancy pass corrected the following source-document mismatches:

1. restored the complete 18,000+ line `research-handoff.md` history after the first audit publication accidentally replaced it with a compact 23-line snapshot;
2. replaced stale/nonexistent traceability aliases (`_execute_query`, `_paginate_connection`, `_refresh_existing_binding`, `_confirmation_decision`, `_manual_gateway_decision`, `_scan_since`, `_run_order_scan_job`, `preview_order_backfill`, `confirm_order_backfill`, `build_tax_evidence_key`) with the exact current symbols listed above;
3. corrected the sudo inventory names from `_refresh_existing_binding`/`_run_order_scan_job` to `_refresh_existing`/`run_scan`;
4. strengthened the permanent-binding race test so a full worker rollback can no longer mask an ineffective importer savepoint or orphan quotation;
5. required the PR body to name only the final post-correction runtime-candidate SHA.

## Mandatory exact-head Odoo.sh matrix

Run only against the exact frozen SHA recorded in PR #176:

1. Fresh install `shopify_connector_core,shopify_connector_product,shopify_connector_sale` with tests.
2. Upgrade from `mvp/program-integration@234c0bb50b3f61b7681e18f0b28839dee619cdb9`.
3. All Task 012, Area-6, SEC-1 and PII-focused classes in the 11 order test files.
4. Full standard core, product and sale suites.
5. `shopify_connector_order_discovery_concurrency`, both tests, repeated for stability; prove registry-lock restoration, first collision, loser transaction usability and no orphan sale order.
6. LC-1 disable/uninstall/reinstall, selection removal, historic conversion and no-orphan checks.
7. CORE-R1, JOB-ACTIONS, SEC-1 and one combined SRR-03 smoke.
8. Residue audit: jobs/logs/leases/stores/credentials/bindings/orders/products/mappings, cron triggers, temporary files and workers.
9. Database audit: sessions, idle transactions, cursors, locks, leases and cron triggers.
10. Security scan: credentials, access tokens, Authorization headers, raw PII and temporary paths.
11. If issue #157 reproduces exactly, use only the accepted temporary `notification_type` and `color_scheme` defaults, rerun, then drop and verify both defaults are restored.
12. Read-only Shopify dev-store order evidence is preferred but may be deferred honestly to Wave 6 if credentials are unavailable.

Representative command forms:

```text
odoo-bin -d <db> -i shopify_connector_core,shopify_connector_product,shopify_connector_sale --test-enable --stop-after-init
odoo-bin -d <db> -u shopify_connector_core,shopify_connector_product,shopify_connector_sale --test-enable --test-tags /shopify_connector_sale --stop-after-init
odoo-bin -d <db> -u shopify_connector_sale --test-enable --test-tags shopify_connector_order_discovery_concurrency --stop-after-init
```

## Proven / not proven

**Proven statically:** allowed-file scope, registration, read-only query posture, fail-closed field protection, exact symbol traceability, replay/lifecycle declarations, explicit caps, exact sudo inventory, and structural concurrency-test intent.

**Not proven:** Odoo model setup, install/upgrade/uninstall/reinstall, functional test execution, actual concurrency behavior, full regression, runtime residue/security, or dev-store behavior. No Odoo.sh build, Odoo test pass, exactly-once remote-effect claim, Shopify mutation or DEC-031 Layer 2 claim is made.
