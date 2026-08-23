# V1 release evidence

## Candidate ledger

| Item | Value |
|---|---|
| Repository | `AdamsOdoo/Adams` |
| Closure branch / draft PR | `codex/pr206-release-closure-deb87b8e` / `#209` |
| Reviewed SHA / tree | `6bb05c0cb0a91be856d9066451f292d5b1a7c791` / `a8cc1e7ad6d064f9569ecfa4454e7c2545423532` |
| Implementation baseline | `deb87b8e79146129d8f0b562fca12d880f0d6296` / `37a32e9f769df436bd149bd82650797376f88ebb` |
| Qualification code head | `46203c2ba9007b58a0389bba5c2a450039019099` / `3f4cb08f1b023d7ef104fb26f5136d97303ec871` |
| Base | `49cfffbd5ff0eca85d2b855d9ebd2e414680af8e` |
| Pinned Odoo | `30bde9ff758834a4912c5ae55843d3a7dad849f1` |
| Shopify API / store | `2026-07` / `testin-lzhbzhtc.myshopify.com` |

This file is intentionally not a readiness claim. The final candidate SHA/tree is recorded only after documentation is committed and code is frozen.

## Commit register

| Commit | Purpose |
|---|---|
| `f123c04` | Baseline report and finding ledger |
| `3918e6b` | WP-1 Shopify 2026-07 order/fulfillment contract and conformance gate (48 documents after WP-6 batching) |
| `724862e` | WP-2 unsafe order lifecycle and product-status ownership |
| `0e0ab9f`, `0912773` | WP-3 variant finalization and inventory first-push wedges |
| `17a1467` | WP-4 truthful readiness, navigation, recovery context |
| `fefcc6d` | WP-5 RPC authorization, webhook disposition, uninstall/generation lifecycle |
| `2cc6b72` | WP-6 fair wakeable queue, durable scans, retention, limits and migrations |
| `6e1ac66` | WP-6 batched exact-identity fulfillment reconciliation reads |
| `1351947` | WP-7 public distribution, supported-scope, operations, recovery, security, upgrade and uninstall contract |
| `07a482c` | Align webhook suite version gates |
| `64e7559`, `19a935b`, `79a0f6a`, `bfee487`, `27164d8`, `e98b30d`, `d767588`, `2655c9a` | Exact-head fresh/warm/migration/full-suite qualification corrections |
| `46203c2` | Coalesce visible fulfillment-scan scope owners without weakening the database uniqueness authority |

## Automated evidence

- Pre-commit static gates at every package: Python compile/AST, manifest and XML parse, `git diff --check`, and secret-pattern scan passed.
- A diff scan from the release base through `46203c2` found zero non-fixture Shopify/GitHub/AWS/private-key patterns. Four Shopify-token-shaped matches are deliberately named `DUMMY`/`TOUR` test fixtures.
- Odoo.sh development build `36838556` tested exact SHA `46203c2` and reported **2,819 tests, 0 failed, 0 errors**. Its Odoo.sh result is `Test: Warning`, the platform's successful development-test terminal state; the log contains no unexplained `ERROR` or `CRITICAL` line after the visible-scope coalescing correction.
- A warm command-line update of all eleven connector addons on build `36838556` loaded 117 modules and exited `0` without a migration or registry failure.
- Exact build runtime: Odoo Server 19.0 at pinned source `30bde9ff758834a4912c5ae55843d3a7dad849f1`; Python 3.12.3; PostgreSQL client 16.14; Google Chrome for Testing 145.0.7632.116; Ubuntu 24.04.
- GitHub Actions run `32667325109`, job `97262721216`, is the exact-SHA supporting suite for `46203c2`; its final artifact and result remain pending at the time of this evidence update.
- The earlier implementation-baseline exact-head run `32641472678` passed and produced artifact `9494291649`, but it does not qualify later code.

## Installed addon versions on Odoo.sh build 36838556

| Addon | Version |
|---|---|
| `shopify_connector_core` | `19.0.1.27.0` |
| `shopify_connector_fulfillment` | `19.0.1.10.0` |
| `shopify_connector_fulfillment_webhook` | `19.0.0.1.0` |
| `shopify_connector_inventory` | `19.0.1.12.0` |
| `shopify_connector_inventory_webhook` | `19.0.0.4.0` |
| `shopify_connector_product` | `19.0.2.14.0` |
| `shopify_connector_product_export` | `19.0.1.6.0` |
| `shopify_connector_product_webhook` | `19.0.0.3.0` |
| `shopify_connector_sale` | `19.0.2.15.0` |
| `shopify_connector_sale_webhook` | `19.0.0.1.0` |
| `shopify_connector_webhook` | `19.0.1.3.0` |

## Exact-head runtime checks completed

- An isolated development Administrator opened the connector dashboard and all four pillars. `Fulfillment Review`, `Sync Rules`, and `Needs Attention` were directly reachable and rendered truthful empty states. No Odoo-origin browser-console error was observed; the only console entries came from the browser's own extension.
- Guided setup persisted the permanent authorized domain `testin-lzhbzhtc.myshopify.com`, saved at Credentials, exited, and resumed at Credentials after reopening. The write-only/plain-at-rest residual disclosure rendered before credential entry, and no credential was read or printed.
- No Access did not receive the connector app and a direct dashboard route rendered the explicit access-denied state. Auditor, Operator and Reviewer direct read routes rendered the bounded dashboard. Administrator received the full connector navigation.
- Direct server execution of job drain, PII retention, stale-owner sweep, inventory push scan, and media status poll returned `AccessError` for No Access, Auditor, Operator, and Reviewer. Administrator and true root execution were accepted. The probe transaction was rolled back.
- The original development database contains exactly one matching authorized-store record with a credential-present boolean. The exact-head database was intentionally not populated by extracting or printing that credential. A credential-preserving Odoo.sh development fork requires an interactive GitHub authorization before live backend UAT can begin.

These checks are partial qualification evidence, not complete browser or live-Shopify UAT. Backend gates A–G, all twelve journeys, supported-load timing, and both immutable UAT runs remain mandatory.

## Required immutable qualification attachments

Before a release verdict, append exact commands/counts/runtime and artifact links for: fresh install, warm update, every migration baseline and repeat, standard/non-standard concurrency suites, JavaScript/HOOT/tours, schema conformance including negative canary, secret scan, supported-load tests, exact-head CI, exact-head Odoo.sh build/module upgrade/logs, backend gates A–G, browser journeys 1–12, role RPC matrix, and two complete same-SHA/tree/build UAT runs.

Until every mandatory attachment exists, the only honest verdict is `NOT RELEASE READY` or `BLOCKED`; no merge is authorized.
