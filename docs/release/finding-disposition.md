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
| A-1 | Implemented — qualification pending: 2026-07 discounted unit price is selected and explicitly derived to a line total. | WP-1 | Sale importer | Schema, realistic multi-unit projection, full suite | D / Order lifecycle | `3918e6b` | G-10, G-2 |
| A-2 | Implemented — qualification pending: fulfillment reader consumes the 2026-07 list and fails closed on malformed/boundary shapes. | WP-1 | Fulfillment reader | List-shape reader, 47-document schema gate, negative canary | E / Fulfillment lifecycle | `3918e6b` | G-11, G-2 |
| O-1 | Implemented — qualification pending: audit says “routed” only on a real active-to-review transition. | WP-2 | Sale importer | Audit/transition test | D / Needs Attention | `724862e` | G-10, G-14 |
| O-2 | Implemented — qualification pending: cancellation, void, expiry, refund and partial refund set review with shipment-stop guidance; fulfillment admission and pre-C2 mutation both refuse reviewed orders. | WP-2 | Sale importer/fulfillment | lifecycle matrix + admission refusal | D / Order lifecycle | `724862e` | G-10 |
| O-3 | Implemented — qualification pending: customer ambiguity technical detail now retains only Shopify/partner IDs, active flags, counts and a one-way email fingerprint; names and email addresses are absent. | WP-5 | Sale customer importer | PII-free ambiguity evidence test | D, G | Current WP-5 commit | G-15 |
| O-4 | Already fixed on baseline and regression-bound: equal-`updatedAt` changed webhook evidence fails closed as `ambiguous_match`. | WP-2 | Sale importer/webhook | Same-second changed-body test | D, F | `724862e` | G-10, G-12 |
| O-5 | Implemented — qualification pending: PII-free line identity/quantity fingerprint detects price-neutral composition changes; legacy rows seed on their next complete read. | WP-2 | Sale binding/importer | Composition change + migration repeat | D | `724862e` | G-10 |
| O-6 | Verified — superseded by cursor-resumability correction; ceiling error will disappear rather than be renamed. | WP-6 | Sale scan | Above-10k synthetic continuation | D / Health | Pending | G-13, G-19 |
| PR-1 | Implemented — qualification pending: import seeds remote status but disables status ownership; title-only previews omit status until an explicit status edit re-enables it. | WP-2 | Product export seam | ACTIVE title-only + explicit status + two-baseline/idempotent migration | B / Product lifecycle | `724862e` | G-8 |
| PR-2 | Implemented — qualification pending: finalization is restricted to confirmed create IDs and ignores unrelated existing siblings. | WP-3 | Product export service | Mixed existing/new and SKU-less sibling tests | B / Product lifecycle | `0912773` | G-8 |
| PR-3 | Implemented — qualification pending: fresh remote SKU preflight plus idempotent same-GID adoption prevents duplicate create after uncertain/finalization outcomes; conflicting ownership fails closed. | WP-3 | Product export Layer 2 consequence | pre-C2 collision + repeated/conflicting finalization tests | B, G | `0912773` | G-8, G-14 |
| PR-4 | Implemented — qualification pending: products/delete is HMAC/dedup/generation fenced, admits the authoritative read-first importer, and a missing node marks bindings stale without deleting or archiving the Odoo product. | WP-5/WP-7 | Product webhook/importer | delete admission + stale disposition tests | B, F | Current WP-5 commit | G-8, G-12 |
| PR-5 | Already fixed on the implementation baseline: a bound product missing from Shopify marks its template and variant bindings stale while leaving all Odoo products intact; WP-7 documents the manual-review contract. | WP-5/WP-7 | Product importer | deletion/stale binding safe-state test | B | Current WP-5 commit | G-8 |
| PR-6 | Implemented — qualification pending: product and inventory webhook handlers distinguish succeeded duplicates from failed/cancelled/skipped/blocked or otherwise unsafe jobs and retain unsafe deliveries for manual review. | WP-5 | Webhook delivery | failed-final/unsafe disposition tests | F | Current WP-5 commit | G-12, G-14 |
| PR-8 | Implemented — qualification pending: every newly observed variant runs one-time SKU/barcode birth initialization without overwriting non-empty local identity. | WP-3 | Product importer | later-variant birth identity/non-overwrite tests | B | `0912773` | G-8 |
| I-1 | Implemented — qualification pending: stock-move and manual admission route every unconfirmed pair to preview and admit no push. | WP-3 | Inventory service | stock move before preview | C / Inventory lifecycle | `0912773` | G-9 |
| I-2 | Implemented — qualification pending: scans refresh all unconfirmed pairs through preview; defensive legacy push jobs terminally skip before admitting preview, clearing pair scope. | WP-3 | Inventory service | pending/previewed scans + no blocked scope | C | `0912773` | G-9 |
| I-3 | Implemented — qualification pending: onboarding states Odoo authority, comparison-only Shopify reads, reviewed first push, and no Shopify-to-Odoo inventory import. | WP-4 | Inventory/setup UI | source/copy/tour tests | Fresh onboarding | Current WP-4 commit | G-9, G-21 |
| I-4 | Implemented — qualification pending: first-push copy distinguishes the Odoo write target from Shopify comparison evidence and makes no baseline-read claim. | WP-4 | Inventory UI | copy/state test | C, Journey 4 | Current WP-4 commit | G-9, G-21 |
| I-5 | Implemented — qualification pending: service-produced previews carry durable freshness evidence; confirmation re-derives Odoo available quantity and refuses stale evidence. Legacy previews remain confirmable until refreshed. | WP-3 | Inventory binding/service | stale-preview refusal/regeneration + idempotent migration | C | `0912773` | G-9 |
| I-7 | Verified — deferred outside v1; warehouse tree-move risk will be an explicit known limit and post-v1 item. | WP-7 | Inventory | Documentation test | Journey 9 | Pending | G-23 |
| I-8 | Verified — open; same root as P-4. | WP-6 | Inventory scan | bounded checkpoint pass | C, G | Pending | G-19 |
| U-1 | Implemented — qualification pending: Fulfillment Review is an active, direct Operations route for Connector Users. | WP-4 | Fulfillment UI | navigation/action access | Journey 6/8 | Current WP-4 commit | G-14, G-21 |
| U-2 | Implemented — qualification pending: Inventory Safeguards was re-parented, leaving Sync Rules as a real action-bearing leaf route. | WP-4 | Core/inventory settings UI | active leaf-route test | Journey 1/9 | Current WP-4 commit | G-21 |
| U-3 | Implemented — qualification pending: activation states that selected read/import scans start immediately while all Shopify writes remain protected. | WP-4 | Setup wizard | activation copy/producer test | Journey 1 | Current WP-4 commit | G-21 |
| U-4 | Implemented — qualification pending: Connected is distinct from Ready; readiness requires enabled-domain completion anchors, normal API health, fresh evidence, valid inventory mapping/first-push decisions, and no blocking work. | WP-4 | Health/readiness | pending/running/ready derivation tests | Journey 7 | Current WP-4 commit | G-14, G-21 |
| U-6 | Implemented — qualification pending: user-facing copy names Sync Rules or the guided Setup route that actually owns the choice. | WP-4 | Setup wizard/product UI | copy/route test | Journey 1 | Current WP-4 commit | G-21 |
| U-7 | Implemented — qualification pending: Needs Attention excludes superseded jobs in the action domain as well as its counts. | WP-4 | Core jobs/UI | action population test | Journey 8 | Current WP-4 commit | G-14 |
| U-8 | Implemented — qualification pending: reviewed order jobs enter Needs Attention and project order, Shopify/Odoo states, reason, stop action and consequence. | WP-2/WP-4 | Sale/UI | cancellation context + handler transition tests | Journey 5/8 | Current WP-4 commit | G-14 |
| U-9 | Implemented — qualification pending: reconnect/backfill is active and the degraded banner provides a direct action button. | WP-4 | Product export UI | action/menu navigation test | Journey 7 | Current WP-4 commit | G-21 |
| U-10 | Implemented — qualification pending: mutation evidence shows the affected object, Shopify/Odoo effects, certainty, stop reason, cause-specific action/consequence, re-read plan, and business-record link. | WP-4 | Core mutation UI | context/business-link/access tests | Journey 8 | Current WP-4 commit | G-14, G-21 |
| U-18 | Verified and closed pending qualification: failed-clean inventory evidence routes from Needs Attention to the immutable attempt and onward to the inventory pair's existing Verify Now recovery action. | WP-4 | Inventory/core UI | failed-clean two-hop resolution test | Journey 4/8 | Current WP-4 commit | G-14 |
| S-1 | Implemented — qualification pending: job drain, PII retention, stale-owner sweep, inventory scan and media poll allow only root cron or Connector Administrator; all lower roles and no-role are denied before side effects. | WP-5 | Core/inventory/product export | direct RPC role matrix | Journey 10 | Current WP-5 commit | G-15, G-16 |
| S-2 | Implemented — qualification pending: a read-first uninstall-preparation job retires exact remote subscriptions through Layer 2; webhook and full connector hooks block unsafe uninstall until remote identities, active work, credentials and uncertain evidence are cleared. | WP-5/WP-7 | Webhook/core lifecycle | uninstall boundary/cleanup tests | Journey 12 | Current WP-5 commit | G-23 |
| S-3 | Verified — supported-limit disclosure: store permanence/archive behavior must be explicit; no broad store-management redesign. | WP-7 | Core store | documentation/behavior test | Journey 12 | Pending | G-23 |
| S-4 | Deferred outside v1: Reviewer is retained as a compatibility capability primitive; WP-5 explicitly denies it at privileged cron RPC boundaries and WP-7 documents that it is not a customer-facing role. | WP-5/WP-7 | Security roles | role matrix | Journey 10 | Current WP-5 commit | G-15, G-16 |
| S-5 | Accepted residual — disclose plain-at-rest credential storage without changing write-only read/RPC handling. | WP-7 | Security docs | docs/secret scan | Journey 1/10 | Pending | G-15, G-23 |
| W-2 | Verified — open: product/order windows restart and cap at 20k/10k. | WP-6 | Product/sale scans | cursor/restart/failure/boundary tests | B, D, G | Pending | G-13, G-19 |
| W-3 | Partially closed pending WP-7 documentation: failed-final product imports are visible on Needs Attention with the sanctioned retry route; automatic blind replay remains forbidden. | WP-5/WP-7 | Product scan/UI | recovery action visibility | B, F, G | Current WP-5 commit | G-12, G-14 |
| W-4 | Implemented — qualification pending: app-uninstalled processing locks the store and compares the delivery job generation/company/domain/API identity before fencing. | WP-5 | Webhook lifecycle | stale uninstall test | A, F | Current WP-5 commit | G-12 |
| W-5 | Implemented — qualification pending: an existing retired topic is restored to `expected=True`, `state=expected`, with stale error cleared when its registry handler returns. | WP-5 | Webhook subscriptions | reinstall test | A, F | Current WP-5 commit | G-12 |
| W-6 | Verified — open; same root as P-1. | WP-6 | Fulfillment scan | bounded cursor/restart tests | E, G | Pending | G-13, G-19 |
| W-7 | Verified — open; same root as P-3. | WP-6 | Retention | inflow/preservation tests | G, Health | Pending | G-19 |
| W-8 | Verified — open: default throughput ceiling is neither published nor health-enforced. | WP-6/WP-7 | Queue/health/docs | supported-rate test | Journey 7/11 | Pending | G-18, G-20 |
| W-10 | Implemented — qualification pending; same read-first deletion-as-stale-binding path as PR-4. | WP-5/WP-7 | Product webhook | delete discovery/safe-state | B, F | Current WP-5 commit | G-8, G-12 |
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
