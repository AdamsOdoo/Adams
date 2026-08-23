# V1 release evidence

## Candidate ledger

| Item | Value |
|---|---|
| Repository | `AdamsOdoo/Adams` |
| Closure branch / draft PR | `codex/pr206-release-closure-deb87b8e` / `#209` |
| Reviewed SHA / tree | `6bb05c0cb0a91be856d9066451f292d5b1a7c791` / `a8cc1e7ad6d064f9569ecfa4454e7c2545423532` |
| Implementation baseline | `deb87b8e79146129d8f0b562fca12d880f0d6296` / `37a32e9f769df436bd149bd82650797376f88ebb` |
| Latest implemented WP-6 head | `6e1ac66f3bc38ef345e17a64312db378241cd718` / `340282952b36169467d5adfbbcc05c8fd2fd362d` |
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
| Pending | WP-7 release contract and qualification-only evidence |

## Automated evidence

- Pre-commit static gates at every package: Python compile/AST, manifest and XML parse, `git diff --check`, and secret-pattern scan passed.
- The local host has Python 3.12.13 but no Odoo runtime, PostgreSQL, Chromium, or `graphql-core`; it cannot produce fresh-install, warm-update, HOOT/tour, browser, or GraphQL execution evidence.
- GitHub Actions run `32662162617` started at WP-6 head `2cc6b722…`; its result is supporting evidence for that intermediate head only. A new exact-head run is required after the batching/documentation commits.
- The earlier implementation-baseline exact-head run `32641472678` passed and produced artifact `9494291649`, but it does not qualify later code.

## Required immutable qualification attachments

Before a release verdict, append exact commands/counts/runtime and artifact links for: fresh install, warm update, every migration baseline and repeat, standard/non-standard concurrency suites, JavaScript/HOOT/tours, schema conformance including negative canary, secret scan, supported-load tests, exact-head CI, exact-head Odoo.sh build/module upgrade/logs, backend gates A–G, browser journeys 1–12, role RPC matrix, and two complete same-SHA/tree/build UAT runs.

Until every mandatory attachment exists, the only honest verdict is `NOT RELEASE READY` or `BLOCKED`; no merge is authorized.
