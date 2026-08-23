# PR #206 release-closure finding disposition

This ledger binds the independent review to the single implementation baseline below. It is updated as each bounded work package lands; an entry marked `Verified — open` is not a release-readiness claim.

## Candidate identity

| Item | Exact value |
|---|---|
| Repository | `AdamsOdoo/Adams` |
| Reviewed branch | `codex/ui-restructure-implementation` |
| Reviewed SHA / tree | `6bb05c0cb0a91be856d9066451f292d5b1a7c791` / `a8cc1e7ad6d064f9569ecfa4454e7c2545423532` |
| Live-head delta retained | `6bb05c0c..deb87b8e` (fulfillment-webhook readiness/scope only) |
| Implementation baseline SHA / tree | `deb87b8e79146129d8f0b562fca12d880f0d6296` / `37a32e9f769df436bd149bd82650797376f88ebb` |
| Base SHA | `49cfffbd5ff0eca85d2b855d9ebd2e414680af8e` |
| Closure branch | `codex/pr206-release-closure-deb87b8e` |
| Draft PR | `#209` |
| Pinned Odoo SHA | `30bde9ff758834a4912c5ae55843d3a7dad849f1` |
| Shopify API / permitted store | `2026-07` / `testin-lzhbzhtc.myshopify.com` |

## Baseline evidence

The local execution host has Python 3.12.13 but no PostgreSQL server/client, Chromium, container engine, or pinned Odoo checkout. It therefore cannot truthfully execute the repository's full runner. Exact-head GitHub Actions run `32641472678` completed successfully at `deb87b8e`; its durable artifact is `connector-suite-deb87b8e79146129d8f0b562fca12d880f0d6296` (artifact `9494291649`, digest `sha256:52a43fd9afb19799f2666b61f9b11ebd4553717ab8f9e31239e0662de6092a9a`). A second exact-head run, `32657568528`, was triggered by draft PR #209 and was still executing when this ledger was created. Neither run contacts Shopify or replaces the required Odoo.sh gate.

## Release findings

`Owner` names the addon/service boundary, not an individual. Test, migration, UAT, commit, and gate references are populated with their intended trace now and replaced with exact evidence as work closes.

| Finding | Baseline disposition | Work package | Owner | Regression / migration | Backend / browser UAT | Commit | Final gate |
|---|---|---|---|---|---|---|---|
| A-1 | Verified — open: order documents still select `priceAfterAllDiscountsBeforeTaxesSet`; locked release contract requires the supported unit-price field/derivation. | WP-1 | Sale importer | Order schema + realistic import; no migration | D / Order lifecycle | Pending | G-10, G-2 |
| A-2 | Verified — open: `Order.fulfillments` is parsed as a cursor connection although 2026-07 exposes a list. | WP-1 | Fulfillment reader | List-shape reader + schema tests; no migration | E / Fulfillment lifecycle | Pending | G-11, G-2 |
| O-1 | Verified — open: refresh log can claim review without a review transition. | WP-2 | Sale importer | Audit/transition test | D / Needs Attention | Pending | G-10, G-14 |
| O-2 | Verified — open: cancellation and unsafe financial transitions do not set binding review state. | WP-2 | Sale importer | cancellation/void/expiry/refund transition tests | D / Order lifecycle | Pending | G-10 |
| O-4 | Already fixed on baseline: equal-`updatedAt` changed evidence fails closed as `ambiguous_match`; dedicated regression still required. | WP-2 | Sale importer/webhook | Same-second changed/unchanged tests | D, F | Pending | G-10, G-12 |
| O-5 | Verified — open: totals evidence does not prove line composition. | WP-2 | Sale binding/importer | Composition fingerprint + upgrade/idempotence | D | Pending | G-10 |
| O-6 | Verified — superseded by cursor-resumability correction; ceiling error will disappear rather than be renamed. | WP-6 | Sale scan | Above-10k synthetic continuation | D / Health | Pending | G-13, G-19 |
| PR-1 | Verified — open: imported product enables export without seeding remote status, leaving `draft`. | WP-2 | Product export seam | ACTIVE title-only + explicit status + migration repeat | B / Product lifecycle | Pending | G-8 |
| PR-2 | Verified — open: variant finalization iterates every template variant. | WP-3 | Product export service | Mixed existing/new variant tests | B / Product lifecycle | Pending | G-8 |
| PR-3 | Verified — open: post-write finalization failure can strand ownership and duplicate risk. | WP-3 | Product export Layer 2 consequence | fault/reconciliation/no-duplicate test | B, G | Pending | G-8, G-14 |
| PR-4 | Verified — supported-limit path: add safe product-delete observation or explicit Needs Attention/tombstone contract. | WP-5/WP-7 | Product webhook/importer | delete disposition test | B, F | Pending | G-8, G-12 |
| PR-5 | Verified — open: missing remote variants remain active locally. | WP-2/WP-7 | Product importer | deletion/stale binding safe-state test | B | Pending | G-8 |
| PR-6 | Verified — open: reused failed/cancelled/skipped/blocked jobs may falsely complete a delivery. | WP-5 | Webhook delivery | terminal disposition tests | F | Pending | G-12, G-14 |
| PR-8 | Verified — open: later imported variants can retain empty Odoo SKU/barcode identity. | WP-3 | Product importer | later-variant birth identity/non-overwrite tests | B | Pending | G-8 |
| I-1 | Verified — open: stock-move admission ignores first-push state. | WP-3 | Inventory service | stock move before preview | C / Inventory lifecycle | Pending | G-9 |
| I-2 | Verified — open: previewed/unconfirmed scans admit a permanently scope-owning blocked job. | WP-3 | Inventory service | pending/previewed scans + no blocked scope | C | Pending | G-9 |
| I-3 | Verified — open: manifest/onboarding language implies a Shopify-to-Odoo inventory import. | WP-4 | Inventory/setup UI | source/copy/tour tests | Fresh onboarding | Pending | G-9, G-21 |
| I-4 | Verified — open: first-push copy can imply a remote quantity was read before evidence exists. | WP-4 | Inventory UI | copy/state test | C, Journey 4 | Pending | G-9, G-21 |
| I-5 | Verified — open: confirmation does not compare current local quantity with preview quantity. | WP-3 | Inventory binding/service | stale-preview refusal/regeneration | C | Pending | G-9 |
| I-7 | Verified — deferred outside v1; warehouse tree-move risk will be an explicit known limit and post-v1 item. | WP-7 | Inventory | Documentation test | Journey 9 | Pending | G-23 |
| I-8 | Verified — open; same root as P-4. | WP-6 | Inventory scan | bounded checkpoint pass | C, G | Pending | G-19 |
| U-1 | Verified — open: Review Workspace menu is `active=False`. | WP-4 | Fulfillment UI | navigation/action access | Journey 6/8 | Pending | G-14, G-21 |
| U-2 | Verified — open: Sync Rules action exists, but route reachability must be proven for the four-pillar menu. | WP-4 | Core settings UI | clickable child-route tour | Journey 1/9 | Pending | G-21 |
| U-3 | Verified — open: activation copy says activation does not start a sync while server activation triggers producers. | WP-4 | Setup wizard | activation copy/producer test | Journey 1 | Pending | G-21 |
| U-4 | Verified — open: activation audit evidence can satisfy the current healthy derivation before real initial synchronization. | WP-4 | Health/readiness | initial-state derivation tests | Journey 7 | Pending | G-14, G-21 |
| U-6 | Verified — open: setup names “Store Settings” where the shipped editable route is “Sync Rules”. | WP-4 | Setup wizard | copy/route test | Journey 1 | Pending | G-21 |
| U-7 | Verified — open: superseded manual-review jobs remain on the attention surface. | WP-4/WP-6 | Core jobs/UI | retry supersession test | Journey 8 | Pending | G-14 |
| U-8 | Verified — open: generic order review lacks cause/action context. | WP-2/WP-4 | Sale/UI | cancellation context test | Journey 5/8 | Pending | G-14 |
| U-9 | Verified — open: degraded banner targets an inactive route. | WP-4 | Dashboard UI | banner navigation tour | Journey 7 | Pending | G-21 |
| U-10 | Verified — open: mutation decision view lacks business link, uncertainty/effect, and consequence text. | WP-4 | Core mutation UI | context/access tests | Journey 8 | Pending | G-14, G-21 |
| U-18 | Partially verified — backend/UI route inspection still required for `failed_clean`; must close if reproducible. | WP-4 | Inventory/core UI | failed-clean resolution test | Journey 4/8 | Pending | G-14 |
| S-1 | Runtime finding accepted and source-verified open: five privileged RPC entrypoints lack the established guard. | WP-5 | Core/inventory/product export | direct RPC role matrix | Journey 10 | Pending | G-15, G-16 |
| S-2 | Verified — open: no uninstall hook. | WP-5/WP-7 | Webhook/core lifecycle | uninstall cleanup/idempotence | Journey 12 | Pending | G-23 |
| S-3 | Verified — supported-limit disclosure: store permanence/archive behavior must be explicit; no broad store-management redesign. | WP-7 | Core store | documentation/behavior test | Journey 12 | Pending | G-23 |
| S-4 | Verified — retain Reviewer compatibility unless bounded removal proves safe; direct-RPC denial remains mandatory. | WP-5/WP-7 | Security roles | role matrix | Journey 10 | Pending | G-15, G-16 |
| S-5 | Accepted residual — disclose plain-at-rest credential storage without changing write-only read/RPC handling. | WP-7 | Security docs | docs/secret scan | Journey 1/10 | Pending | G-15, G-23 |
| W-2 | Verified — open: product/order windows restart and cap at 20k/10k. | WP-6 | Product/sale scans | cursor/restart/failure/boundary tests | B, D, G | Pending | G-13, G-19 |
| W-3 | Verified — open: product `failed_final` recovery is not automatic/obvious. | WP-5 | Product scan/UI | recovery admission test | B, F, G | Pending | G-12, G-14 |
| W-4 | Verified — open: app-uninstalled consumer is not generation-fenced. | WP-5 | Webhook lifecycle | stale uninstall test | A, F | Pending | G-12 |
| W-5 | Verified — open: retired reinstalled topic does not restore `expected=True`. | WP-5 | Webhook subscriptions | reinstall test | A, F | Pending | G-12 |
| W-6 | Verified — open; same root as P-1. | WP-6 | Fulfillment scan | bounded cursor/restart tests | E, G | Pending | G-13, G-19 |
| W-7 | Verified — open; same root as P-3. | WP-6 | Retention | inflow/preservation tests | G, Health | Pending | G-19 |
| W-8 | Verified — open: default throughput ceiling is neither published nor health-enforced. | WP-6/WP-7 | Queue/health/docs | supported-rate test | Journey 7/11 | Pending | G-18, G-20 |
| W-10 | Verified — same root/disposition as PR-4. | WP-5/WP-7 | Product webhook | delete discovery/safe-state | B, F | Pending | G-8, G-12 |
| P-1 | Verified — open: fulfillment reconciliation scans all bindings and performs per-binding reads. | WP-6 | Fulfillment scan | bounded pass/checkpoint test | E, G | Pending | G-19 |
| P-2 | Verified — open: `id asc` drain is sequential/unfair and enqueue has no wakeup. | WP-6 | Core queue | multistore fairness/wakeup/load | F, G, Journey 11 | Pending | G-18, G-19 |
| P-3 | Verified — open: evidence redaction is not terminal-row retention; delivery deletion is capped below supported inflow. | WP-6 | Core/webhook retention | >500/day + unresolved preservation | G | Pending | G-19 |
| P-4 | Verified — open: inventory scan is unbounded, UUID-admitted, and re-writes target state in the hot loop. | WP-6 | Inventory scan | singleton/bounded/checkpoint/unchanged tests | C, G | Pending | G-19 |
| P-5 | Verified — material only if supported-load target fails; targeted matching optimization is authorized in that case. | WP-6 | Product importer | query-bound benchmark | B, G | Pending | G-19 |
| P-6 | Verified — open: PII/attempt sweeps are unbounded. | WP-6 | Core retention | bounded progress test | G | Pending | G-19 |
| P-7 | Verified — defer unless upgrade/load gate proves it material; retain in post-v1 backlog otherwise. | WP-6/WP-7 | SEC-3 migration | upgrade query-bound test | Journey 12 | Pending | G-6, G-19 |
| P-8 | Verified — batch only as required for supported limits. | WP-6 | Product media poll | bounded poll test | G | Pending | G-19 |
| P-9 | Verified — batch only as required for supported limits. | WP-6 | Inventory stock hook | query-bound test | C, G | Pending | G-19 |

## P3/backlog register

The review's remaining P3 groups are not release scope unless a gate makes one material. They remain explicitly tracked: O-3 must be closed before the latent customer-import path is enabled; O-7 through O-10, PR-7 and PR-9 through PR-15, I-6 and I-9 through I-11, W-9 and W-11, U-5 and U-11 through U-20, S-6 and S-8 through S-10, and P-10 through P-15 are deferred to `docs/release/post-v1-backlog.md`. O-3's PII redaction is included in WP-5 despite the affected path remaining disabled. S-4 and S-5 have the explicit release dispositions above.

## Governance boundary

This branch implements and qualifies the product-owner-authorized closure. It does not merge, mark ready, or self-accept. The final candidate still requires exact-SHA CI, Odoo.sh and two-run UAT evidence plus independent acceptance under DEC-041.
