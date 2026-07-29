# Wave 5 — merchant-operability closure batch, 2026-07-29

> **Status: implementing-session record. NOT an acceptance, NOT a review, NOT
> a ready-mark.** Written by the session that implemented the change, under
> CLAUDE.md §13's no-self-acceptance rule. Every claim below is local evidence
> only: the remaining gates are independent merchant-journey/security review,
> exact-head Odoo.sh qualification, controlled live-Shopify validation,
> business UAT, and control-room acceptance/merge authorization.

## 1. What this batch is

The first executable slice of the unified merchant-operability closure
campaign (control-room prompt of 2026-07-29, "Wave 5 unified
merchant-operability closure"), on PR #204 (`fable/wave-5-completion` →
`mvp/program-integration`). The campaign's two **mandatory, explicitly
non-retained starting-head gaps** are closed here:

1. **§11 — a current-Shopify authentication path.** A merchant creating a
   Shopify app in July 2026 does it in the Dev Dashboard, which shows no
   permanent Admin API token to copy; the connector could not authenticate
   that merchant at all. Closed by the `dev_dashboard_client_credentials`
   credential mode beside the fully-compatible `offline_access_token` mode.
2. **§17 — TD-020 and the 200-item location cut.** A confirmed first push
   made location remap permanently impossible, and the setup step's bounded
   location lists made every eligible location past the first page
   unmappable from the step. Closed by the governed first-push-decision
   withdrawal and the bounded server-side location search.

The rest of the campaign (canonical Store Settings, production import
admission routes, tax/customer flow completion, per-domain dashboard
liveness, attention/recovery consolidation, §26's full journey-regression
families A–K) is **NOT in this batch** and is recorded in §6 below as the
remaining scope, not silently dropped.

## 2. Commits and paths

| Commit | Scope |
|---|---|
| `b223a0e` | Authentication: `auth_mode` on the credential row; `shopify.connector.store.access.token` (no-ACL token cache, SEC-3 covered); `_exchange_client_credentials`/`_send_token_exchange` at the single transport boundary; `_ensure_access_token` before every admission lock; advisory-lock refresh coalescing; identity-based probe revalidation; migration `19.0.1.16.0`; the setup credential step's two-path chooser; the granted-scopes JSON parse fix; `test_client_credentials.py`; guard-inventory updates. |
| `cad932f` | Inventory: `withdraw_first_push_decision` + `shopify.connector.first.push.withdraw.wizard` + the pair-form control (TD-020); `search_location_options` over the new `_setup_search_locations` seam, its inventory implementation, the setup step's search UI; `TestFirstPushWithdrawal`, `TestSetupLocationSearch`, the withdrawal browser tour, S1 location-tour search steps. |

Production paths touched: `addons/shopify_connector_core/**`,
`addons/shopify_connector_inventory/**`, one HOOT-count line in
`addons/shopify_connector_product_export/tests/test_u3_hoot_suite.py`, and
the tour inventory in `tools/run_connector_suite.sh`. No other module, no
protected branch, no rejected-approach reintroduction.

## 3. The authentication mode, precisely

* **Modes.** `offline_access_token` (unchanged, byte-for-byte compatible;
  every pre-existing row migrated onto it explicitly, no stored token ever
  reinterpreted) and `dev_dashboard_client_credentials` (client-credentials
  grant, same-Shopify-organization apps, 24-hour token, automatic refresh).
  Facts verified against
  <https://shopify.dev/docs/apps/build/dev-dashboard/get-api-access-tokens>
  (accessed 2026-07-29): POST `/admin/oauth/access_token`,
  `application/x-www-form-urlencoded`, `grant_type=client_credentials`,
  response `access_token`/`scope`/`expires_in` ("Always 86399").
* **Storage.** Client ID/secret live on the credential row behind the same
  Administrator-only, write-only, not-encrypted-at-rest discipline as the
  token (the honest AR-022/AR-024/AR-025 residual, restated in the UI). The
  ephemeral token lives in `shopify.connector.store.access.token`, which
  carries **no ACL row at all** — no group, Administrator included, can read
  it over RPC; it is reachable only through the credential model's
  store-scoped sanctioned seam.
* **Why a separate table is load-bearing.** Odoo cursors run REPEATABLE
  READ. A refresh side-transaction write to the credential row would (a)
  collide with the same request's later `FOR NO KEY UPDATE` revalidation
  lock — a manufactured serialization failure — and (b) advance the
  `write_date` the probe's version check reads as "credential changed", a
  false supersession once a day. The probe revalidation therefore compares
  the credential **identity** (offline token, or the client pair), never
  whichever 24-hour token is current.
* **Refresh.** `_ensure_access_token` runs before any admission lock, never
  inside one; refresh serializes per store on a PostgreSQL advisory lock
  (leader exchanges once, waiters poll committed state and reuse it, a
  waiter that never sees a token gives up with the retryable taxonomy); the
  margin is 900 s; a still-valid token keeps serving while a refresh fails.
  A failed exchange writes nothing from the side transaction — the probe's
  own transaction records the store mirrors, flips `credential_state` and
  routes to reconnect; a business call fails into the dispatcher's existing
  auth (manual-fix-then-retry) family.
* **Not implemented, on purpose:** authorization-code OAuth, callbacks,
  controllers, billing, compliance webhooks, any public-distribution
  architecture. The source guards that forbid controller/OAuth surfaces are
  unchanged and still pass.

## 4. TD-020 and the location search, precisely

See the updated TD-020 register row (docs/05-qa/technical-debt-register.md)
for the full statement. In one line each:

* `withdraw_first_push_decision`: Administrator-only, explicit-consequence,
  reason-audited, row-locked with an expected-state (stale-dialog) check,
  refused outside a proven safe terminal state; returns the pair to
  `pending`; the untouched D-013-4 gate then forces a complete new
  preview + confirmation. The remap guard itself is not weakened — its
  refusal copy now names the working route.
* `search_location_options` (setup RPC) → `_setup_search_locations` (core
  seam, inventory implementation): indexed, paginated (50/page),
  case-insensitive server-side search across **all** eligible cached
  Shopify locations and internal Odoo locations; store/company filters
  structural on every page and query; honest Showing-X-of-Y counts; Load
  more pages through the full eligible set. The first-page bound stays; the
  unreachability is gone.

## 5. Evidence (local, this session)

* Baseline at the starting head `50b770a`: fresh-install standard pass, **0
  failed, 0 error(s) of 2131 tests** (ci-artifacts summary retained).
* Focused runs during the batch (all green at their heads): credential/core
  guard classes (85 and 99 tests), setup-wizard server classes (80 → 34
  re-run), S1 tours (6), U2 action tours incl. the new withdrawal tour,
  HOOT (setup-wizard suite now 20 client assertions), TD-020 + search
  classes (67).
* **Definitive three-pass run** (`tools/run_connector_suite.sh`, no
  arguments) at the final executable head
  `cad932f33f6c87c4ac55b6be1a8c5a8a12909434`, clean worktree, source head
  verified, Odoo pin `30bde9ff` verified, Python 3.12.3, PostgreSQL 16.13,
  Chromium 141.0.7390.37, 2026-07-29 21:20–21:35 UTC:
  - fresh install + standard suite: **pass — 0 failed, 0 error(s) of 2189
    tests**, 24/24 required tour success markers (baseline at `50b770a3`
    was 2131 tests / 23 tours: **+58 tests, +1 tour**);
  - warm `-u` update + standard suite (migration `19.0.1.16.0` executed):
    **pass — 0 failed, 0 error(s) of 2189 tests**, 24/24 tours;
  - complete non-standard tag suite (concurrency proofs, benchmarks, HOOT,
    visual evidence): **pass — 0 failed, 0 error(s) of 42 tests**, all
    three HOOT suites verified (`dashboard`, `export diff`,
    `setup wizard` — the last now at 20 client assertions);
  - the single sanctioned skip in each standard pass remains
    `TestMutationRecovery.test_real_process_death_harness`, exactly as at
    the baseline.
* Zero live Shopify contact anywhere: every test patches
  `_send`/`_send_lifecycle`/`_send_token_exchange`; no real credential
  exists in the repository or the test environment.

## 6. Remaining campaign scope (explicitly not in this batch)

The control-room prompt's remaining mandatory areas, untouched here and
still open: canonical Store Settings (§13) — no Store Settings screen
exists yet and the wizard's "change this later in Store Settings" copy
still points at a screen that is only the rerun-setup route; feature-derived
scope catalogue consumption (§12) beyond the existing display catalogue;
product import production admission + matching workspace reachability
(§14); customer import discovery route (§15); order-scan enablement,
tax-discovery flow completion (§16); export `Prepare changed products`
(§18); fulfillment settings surface (§19); per-domain operating-mode
declarations (§20); per-store/per-domain dashboard liveness replacing the
aggregate green (§21); the consolidated attention entry point (§22);
reconnect/disconnect surfaces (§23); and §26's journey families C, D, F, G,
H, J in their full vertical form. Each remains a P0/P1 operability gap per
the pre-edit audit; none was silently deferred — this record is the
deferral, for the control room to re-scope into the next bounded batch.
