# Exact-head assurance addendum — PR #206 (current qualification candidate)

**Prepared:** 2026-08-18

**Status:** control-room evidence addendum; not release sign-off and not UAT
authorization. The earlier packet in this directory is preserved as
historical evidence and is not rewritten by this addendum.

## Candidate identity and decision

| Item | Verified value |
| --- | --- |
| Pull request / branch | PR #206 / `codex/ui-restructure-implementation` |
| Published PR HEAD | `2b8108b9b69ca70b20a3b705a82e167ea13bb98a` |
| Published tree | `522bcd01035cb44d241ff56c3deff3de272701c2` |
| Odoo source pin exercised by CI | `30bde9…` |
| Documentation base before this evidence refresh | `4fcc296cf76ce30ce8c002ac814ffeeb64b91580`, tree `d6e506852ed879b3f764bb1667daf9da83ba96bb` |
| PR state | Draft and unmerged; do not merge, approve or mark ready |
| Authorized Shopify development store | `testin-lzhbzhtc.myshopify.com` only |
| Forbidden historical domain | `mqiu21-yz.myshopify.com` |
| GitHub Actions | [run `32152200822`](https://github.com/AdamsOdoo/Adams/actions/runs/32152200822), job `95760574305`: **SUCCESS; accepted exact-head CI evidence** |
| Odoo.sh exact-head qualification | **Inaccessible**: cloud-browser auto-review denied Odoo.sh access; no workaround was available |

### Primary assurance verdict

**NOT ASSURED — CORE ARCHITECTURE GAPS.**

The durable Odoo job, lease, mutation-attempt, generation, reconciliation and
recovery substrate remains a useful foundation. W1 and W2 add bounded webhook
capability, but the supported near-real-time contract is still incomplete:
only the generic lifecycle signal and product create/update domain slice have
handlers. Inventory, order, refund and fulfillment near-real-time paths remain
unimplemented. Exact-head live Gates A–H also remain open.

### External qualification blocker

**BLOCKED BY EXTERNAL INFRASTRUCTURE** is recorded as a secondary status for
the current qualification attempt. The Odoo.sh environment could not be
reached through the permitted cloud browser because automatic review denied the
Odoo.sh action. This prevents exact-head build/database and live qualification
evidence; it does not convert the primary architecture verdict into an
assurance pass.

**Product/inventory UI UAT: not authorized.** **Order/fulfillment UI UAT: not
authorized.** Production-release planning is not ready.

### CI qualification correction

The prior exact-head Actions run `32126803040` failed before Odoo tests: the
browser-probe cleanup raced a late Chromium profile writer. The accepted
correction is published as `f62db111…` (local equivalent `423bbc9c…`); it
bounds browser-profile cleanup and does not change connector production
synchronization behavior. New exact-head run `32127509348` completed
**cancelled after the configured 180-minute timeout**. Its `fresh.log` artifact
(artifact `9326736197`) stopped at `sale core_dispatch_selftest` after earlier
deterministic core/W2 thread harness failures, an illegal W2 transition
fixture, and a quoted static guard failure. The resulting store/worker
contamination caused a later cascade; the cancelled run is therefore not
acceptance evidence and is not treated as a production synchronization
failure.

The bounded test correction was published as
`6805a1d88d3046f43acfc9ae24e68ef27668f1cf`, tree
`60cb328ebec8f6ced7fcf80c7f1167f1d88c1038`. Its exact-head Actions run
`32144921687` completed **failure after approximately 48 minutes**:

- fresh and warm each reported `0 failed, 2 error(s)` from an
  unauthorized-admin actor fixture and a non-ISO webhook timestamp fixture;
- the W2-only schema install reached tests and failed only the same timestamp
  fixture;
- migration reported `0 failed, 0 error(s)`, but the exact optional-W1
  capability skip was initially rejected; and
- non-standard reported `0 failed, 0 error(s)`.

These are qualification-fixture/runner failures, not live Shopify evidence and
not proof of production synchronization correctness. Luna Max corrections
`0c7a064e2e8f27381b61b7eb64c6fb7bbfaeb0d6` and
`daf6fd39246d0ebe6bb312e313a22a0e5e16038b` were composed and published as the
**test-only** head `2b8108b9b69ca70b20a3b705a82e167ea13bb98a`, tree
`522bcd01035cb44d241ff56c3deff3de272701c2`. SOL Medium initially found a
trailing-space mismatch in the migration-skip guard, then accepted the amended
correction.

Exact-head Actions run `32152200822`, job `95760574305`, completed
**SUCCESS** and is accepted CI evidence for source head `2b8108b9…` with Odoo
pin `30bde9…`:

- fresh: 2,682 tests, `0 failed, 0 error(s)`, 40 tour markers with all 39
  required markers present;
- warm: 2,682 tests, `0 failed, 0 error(s)`, and zero same-version migrations;
- W2-only: legacy W1 `19.0.1.0.0` remained unchanged while W2
  `19.0.0.2.0` installed, with both required JSONB columns present;
- migration `50b…`: 2,647 tests, `0 failed, 0 error(s)` on first and second
  pass, five scripts first pass and zero second pass;
- migration `0a15…`: 2,647 tests, `0 failed, 0 error(s)` on first and second
  pass, four scripts first pass and zero second pass;
- the optional-W1 skip is narrowly sanctioned in migration qualification only;
  and
- non-standard: 62 tests, `0 failed, 0 error(s)`, plus three HOOT suites.

Artifact `9332374635` has digest
`sha256:54edee9f0f733d8c4ddda3a6908a45b7b26de1c16556b924cf199827027a1e87`.
This acceptance is bounded to exact-head CI; it is not an Odoo.sh build, live
Shopify evidence, or Gate A–H proof.

## What changed since the preserved packet

The published tree contains two independently reviewed webhook slices:

### W1 generic webhook foundation — [Code fact]

- HTTPS callback routing with bounded raw-body reads and HMAC verification.
- Store-scoped callback tokens, exact shop resolution, delivery-ID
  deduplication and payload-free delivery evidence.
- Fast acknowledgement followed by durable asynchronous processing.
- Subscription expected/actual reconciliation, lifecycle fencing, retry and
  manual-review evidence, retention and operator health views.
- `app/uninstalled` is the only generic active topic. The generic catalog also
  records assessed product, inventory, order, refund and fulfillment topics,
  but cataloguing a topic does not subscribe to it or process it.
- Scheduled reconciliation/scans remain the loss-recovery backstop. W1 does
  not claim real-time delivery or processing.

### W2 product read-first webhook slice — [Code fact]

`addons/shopify_connector_product_webhook` activates exactly:

- `products/create`
- `products/update`

The handler trusts only Shopify's explicit Product GID, checks store/company
scope and connection generation, coalesces duplicate child work, and queues
the existing product importer for the authoritative Shopify read. It does not
perform a Shopify request inline. Product deletion is intentionally inactive:
`products/delete` is catalogued but not subscribed. Scheduled product scans
remain the fallback for missed, delayed or out-of-order events.

The following domain webhook topics remain **not implemented / not active**:

| Domain | Topics | Current contract |
| --- | --- | --- |
| Inventory | `inventory_levels/update` | Scheduled scan/reconciliation only |
| Orders | `orders/create`, `orders/updated`, `orders/cancelled` | Scheduled order scan only |
| Refunds | `refunds/create` | Existing sale/reconciliation paths; no domain webhook handler |
| Fulfillment | `fulfillments/create`, `fulfillments/update` | Scheduled fulfillment/reconciliation only |
| Product deletion | `products/delete` | Explicitly inactive; no silent delete assumption |

This is a bounded incremental architecture, not a complete hybrid connector.

## Exact-head live evidence boundary

No exact-`2b8108b9b69ca70b20a3b705a82e167ea13bb98a` live Shopify Gate E or
Gate A–H proof is recorded. In particular, there is no exact-head evidence of
an actual subscription, Shopify webhook delivery, raw-body HMAC verdict,
delivery-ID replay, asynchronous domain processing, remote read-back, or
reconciliation repair.

The following evidence is valid but belongs to an earlier exact-head and must
not be promoted to current-head qualification:

| Earlier source | Evidence retained | Why it does not qualify `2b8108b…` |
| --- | --- | --- |
| `b136b4ecd23efff0967fc0accb841004fed77d09`, earlier published-era tree `85edb706a45ebdb7c68762a5ceb343cab64195c` | Correct-store record `562` for `testin-lzhbzhtc.myshopify.com`; production-form credential entry; remote identity/read evidence; eleven scopes | Earlier tree; credential and database state are not evidence of the published W1/W2 head |
| Same earlier UAT lineage | Product import job `3196`; Product GID `gid://shopify/Product/8650641047737`; Variant GID `gid://shopify/ProductVariant/48603042840761`; InventoryItem GID `gid://shopify/InventoryItem/50769579835577`; Odoo template `951`, variant `1401`, bindings `948`/`862`; duplicate-free re-import | Valid historical product/inventory evidence, not exact-head webhook or Gate C/D evidence |
| Same earlier UAT lineage | Location mapping `94`; inventory-level binding `164`; mutation attempt `170`; Shopify quantity `7 → 5`; fresh reconciliation read; immediate repeat with no second effective mutation | Valid historical live mutation evidence, not current-head evidence |
| Same earlier UAT lineage | Product export preflight false-positive diagnosis and correction path | The diagnosis informed `productByIdentifier`; it does not prove current-head remote behavior |

The authoritative historical detail remains in
[`pr-206-coherent-repair-ledger-2026-08-17.md`](../../07-implementation-plan/pr-206-coherent-repair-ledger-2026-08-17.md),
especially its correct-store section. No secret is copied into this addendum.

## Gate status at this exact head

| Gate | Status | Exact-head interpretation and closure requirement |
| --- | --- | --- |
| A — Authentication and identity | **Not live-passed** | Re-run credential exchange against the exact published head; verify shop identity, scopes, API version, masked storage and generation fencing. Earlier store-562 evidence is historical only. |
| B — Read connectivity | **Not live-passed** | Fresh exact-head shop/location/product/variant/InventoryItem/order reads, pagination and throttle metadata remain absent. |
| C — Product lifecycle | **Not live-passed** | W2 product handlers are source/test reviewed; no exact-head live delivery → child job → authoritative read → Odoo binding evidence exists. |
| D — Inventory lifecycle | **Not live-passed** | Prior 7→5 inventory mutation is earlier-head evidence; no exact-head inventory webhook or full CAS/replay/conflict proof exists. |
| E — Webhook delivery | **Not live-passed / externally blocked** | W1/W2 code exists, but no exact-head Shopify subscription, delivery, HMAC, dedupe, async processing or reconciliation-repair evidence exists. |
| F — Order/fulfillment | **Not live-passed** | Domain webhook handlers are absent and no exact-head live order, refund, fulfillment, tracking, partial or backorder evidence exists. |
| G — Failure and recovery | **Not live-passed** | Automated failure taxonomy and recovery tests are not live transport, timeout, uncertain-outcome or restart evidence on this head. |
| H — Security | **Not live-passed** | ACL/company/source controls are reviewed, but the exact-head dedicated-user, direct-URL, RPC and multi-company runtime matrix is absent. |

## Architecture, scale and operability conclusion

| Area | Current finding | Decision |
| --- | --- | --- |
| Identity and duplicates | Stable Shopify GIDs, store/company boundaries, delivery IDs, generation fencing and product read-first coalescing are present in source/tests. | Retain and extend; exact-head live replay evidence remains required. |
| Transaction/failure integrity | Durable jobs, leases, attempts, uncertain outcomes and reconciliation are present; W2 keeps remote reads out of the webhook request. | Promising foundation; live Gate G/Gate E still open. |
| Near-real-time synchronization | Generic `app/uninstalled` and product create/update signals only. Inventory/order/refund/fulfillment still rely on scheduled work. | Core capability gap; do not claim complete near-real-time sync. |
| Scale | Existing finite scan caps and no Shopify Bulk Operations path remain; no exact-head cost/backlog/capacity measurements exist. | Pre-release scale work required; publish supported volumes or add resumable/bulk paths. |
| Security | HMAC/raw-body verification, callback-token isolation, ACLs, company rules and secret redaction are source-level controls. | Exact-head Gate H and credential-at-rest policy remain open. |
| Operator UX | Setup correctly distinguishes pending webhook proof from an operator-action refusal in the source/test contract. | Do not begin UI UAT until exact-head backend gates and environment qualification pass. |

Known scale constraints remain material: product/order scan windows are finite
and Shopify Bulk Operations are not implemented. Shopify GraphQL cost metadata
and bounded backpressure are useful controls, but measured cost, throttle
recovery, queue fairness, multi-store throughput and backlog recovery have not
been established for this head.

## Assignments and independent review loops

- **Review chronology:** W1 was introduced in `331feae2`; W2 product
  read-first handling in `7de1c79e`. Subsequent bounded correction loops
  include `e4372733`, `161555b4`, `b509dd80`, `a7b712ba` and the exact-tree
  qualification repairs `4ff9b914`, `423bbc9c`, `6805a1d8` and the Luna
  `0c7a064e` / `daf6fd39` corrections composed as `2b8108b9`. These commit
  identities are source history, not substitutes for current-head runtime
  evidence.
- **Luna Max Agent A — architecture/production path:** mapped W1 and W2
  modules, topic ownership, read-first boundaries, lifecycle/retry behavior and
  inactive topics. The implementation remained modular and did not widen the
  generic registry to unhandled business events.
- **Luna Max Agent B — live backend/evidence:** owns the next exact-head Gates
  A–H run against `testin-lzhbzhtc.myshopify.com`, including remote subscription
  IDs, delivery IDs, job/attempt IDs, fresh Shopify reads, replay/no-op results
  and cleanup. It must not treat a job state or HTTP 200 as remote business
  success.
- **SOL Medium Reviewer:** independently reviewed W1, W2 and their correction
  loops, including qualification-test repairs and product read-first scope.
  The reviews accepted the bounded W1/W2 slices; acceptance does not close the
  missing domain handlers or absent exact-head live evidence. Any new domain or
  qualification correction must be independently re-reviewed.

Exact-head Actions is now accepted. The remaining safe sequence is: Odoo.sh
fresh/warm/migration qualification → independent review of any material
correction → live backend Gates A–H → only then product/inventory UI UAT and
later order/fulfillment UI UAT.

## Material changed paths in the W1/W2 delta

The current published code correction is `2b8108b9b69ca70b20a3b705a82e167ea13bb98a`
with tree `522bcd01035cb44d241ff56c3deff3de272701c2`. Relative to the accepted
pre-W1 head used for integration review, the material production delta is the
W1/W2 list below; the `2b8108…` correction is test-only and does not alter
production synchronization behavior:

```text
addons/shopify_connector_core/static/src/js/tours/shopify_connector_s1_setup_tour.js
addons/shopify_connector_core/tests/test_disconnect_quiescence.py
addons/shopify_connector_core/tests/test_ui_setup_tours.py
addons/shopify_connector_product_export/tests/test_export_sec3_and_permissions.py
addons/shopify_connector_product_webhook/README.md
addons/shopify_connector_product_webhook/__init__.py
addons/shopify_connector_product_webhook/__manifest__.py
addons/shopify_connector_product_webhook/models/__init__.py
addons/shopify_connector_product_webhook/models/shopify_connector_product_importer_guard.py
addons/shopify_connector_product_webhook/models/shopify_connector_product_webhook.py
addons/shopify_connector_product_webhook/tests/__init__.py
addons/shopify_connector_product_webhook/tests/test_product_webhook_w2.py
addons/shopify_connector_webhook/__init__.py
addons/shopify_connector_webhook/__manifest__.py
addons/shopify_connector_webhook/controllers/__init__.py
addons/shopify_connector_webhook/controllers/shopify_connector_webhook.py
addons/shopify_connector_webhook/data/shopify_connector_webhook_cron.xml
addons/shopify_connector_webhook/models/__init__.py
addons/shopify_connector_webhook/models/shopify_connector_webhook_credential.py
addons/shopify_connector_webhook/models/shopify_connector_webhook_delivery.py
addons/shopify_connector_webhook/models/shopify_connector_webhook_dispatch.py
addons/shopify_connector_webhook/models/shopify_connector_webhook_job.py
addons/shopify_connector_webhook/models/shopify_connector_webhook_readiness.py
addons/shopify_connector_webhook/models/shopify_connector_webhook_registry.py
addons/shopify_connector_webhook/models/shopify_connector_webhook_secret.py
addons/shopify_connector_webhook/models/shopify_connector_webhook_subscription.py
addons/shopify_connector_webhook/security/ir.model.access.csv
addons/shopify_connector_webhook/security/shopify_connector_webhook_company_rules.xml
addons/shopify_connector_webhook/tests/__init__.py
addons/shopify_connector_webhook/tests/test_webhook_w1.py
addons/shopify_connector_webhook/views/shopify_connector_webhook_views.xml
docs/05-qa/webhook-w1-validation-results.md
docs/07-implementation-plan/webhook-implementation-packets.md
addons/shopify_connector_product_webhook/pre_init.py
addons/shopify_connector_webhook/migrations/19.0.1.1.0/post-migrate.py
addons/shopify_connector_core/tests/test_suite_runner_fails_closed.py
tools/run_connector_suite.sh
```

The exact test-only `2b8108…` correction changes these four paths:

```text
addons/shopify_connector_core/tests/test_suite_runner_fails_closed.py
addons/shopify_connector_core/tests/test_ui_setup_tours.py
addons/shopify_connector_product_webhook/tests/test_product_webhook_w2.py
tools/run_connector_suite.sh
```

The addendum itself is documentation-only; no production code is changed by
this documentation commit.

## Publication correction transparency

The control-room publication record retains the failed transfer history. The
malformed `14edd…` transfer was not treated as a candidate. It was superseded
by the hash-verified `eed…` tree; the subsequent accepted browser-cleanup
correction superseded the prior published `45ad…`/`fd248270…` candidate. The
authoritative current code identity is `2b8108b9…` with tree `522bcd01…`. The
earlier `f62db111…` browser-cleanup candidate, the cancelled run, and failed
`6805a1d8…` qualification remain historical evidence. This prevents
a malformed object-transfer artifact or stale published head from being
mistaken for the reviewed source.

## Official documentation baseline

The following official pages were consulted on **2026-08-18**. Shopify Admin
GraphQL behavior was assessed against the connector's configured API version
`2026-07`; the Shopify pages are current documentation pages rather than
immutable release snapshots. Odoo references are the Odoo **19.0** developer
and administration documentation.

| Authority | Version/baseline | Accessed | Relevance |
| --- | --- | --- | --- |
| [Shopify webhooks](https://shopify.dev/docs/apps/build/webhooks) | Current webhook guidance; configured Admin GraphQL `2026-07` | 2026-08-18 | Near-real-time notification plus reconciliation safety net |
| [Shopify webhook verification](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries) | Current delivery verification guidance | 2026-08-18 | Raw-body HMAC and delivery identity/deduplication |
| [Shopify webhook subscriptions](https://shopify.dev/docs/apps/build/webhooks/subscribe) | Current subscription lifecycle guidance | 2026-08-18 | Registration, reconciliation and lifecycle management |
| [Shopify API limits](https://shopify.dev/docs/api/usage/limits) | Admin GraphQL cost/throttle guidance | 2026-08-18 | Backpressure, retry and scale assessment |
| [Shopify Bulk Operations queries](https://shopify.dev/docs/api/usage/bulk-operations/queries) | Current bulk-query guidance | 2026-08-18 | Large-volume gap assessment |
| [Shopify idempotent requests](https://shopify.dev/docs/api/usage/idempotent-requests) | Current mutation guidance | 2026-08-18 | Retry/uncertain mutation assessment |
| [Odoo 19 security](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html) | Odoo 19.0 | 2026-08-18 | ACL, record-rule and public-method review |
| [Odoo 19 performance](https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html) | Odoo 19.0 | 2026-08-18 | ORM/query/batching review |
| [Odoo.sh technical FAQ](https://www.odoo.com/documentation/19.0/administration/odoo_sh/advanced/frequent_technical_questions.html) | Odoo 19.0 administration | 2026-08-18 | Scheduled-action and operational-limit review |

## Final control-room statement

Build on the current foundation through a controlled refactor/extension. Do
not replace the durable core and do not declare the connector assured. Finish
the remaining domain webhook slices or explicitly accept scheduled-only
latency per domain, make scale limits measurable, qualify the exact published
head, and produce fresh live evidence before any UI UAT or production-release
planning.
