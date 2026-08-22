# 2026-08-22 control-room addendum

This addendum preserves the 2026-08-18 packet and records the next exact-code
checkpoint. It is not a retroactive upgrade of the earlier decision.

## Candidate and environment

- PR: #206 (open, draft, not merged, not marked ready)
- Branch: `codex/ui-restructure-implementation`
- Last verified remote head before publication: `d89f4120473477b39b9e543bf1a613698286ca18`
- Integrated local code head: `e076fea76f174c0c8dd885e37194dad2afff85b9`
- Integrated local code tree: `1a515401e16784ea03269ee7b727858e58d949dd`
- Qualified predecessor build: Odoo.sh development build `36787681`, Odoo 19
- Development database: `adamsmen-codex-ui-restructure-implementation-36787681`
- Authorized shop: `testin-lzhbzhtc.myshopify.com`
- Store record: `shopify.connector.store,575`, company `My Company (San Francisco)`
- API version: `2026-07`
- Credential: present, masked/restricted, last connection test **Pass** at
  2026-08-22 11:26 local database time. No secret is reproduced here.

The code checkpoint above still requires GitHub Actions and an exact-head
Odoo.sh build before its live backend journeys can resume.

## Live predecessor-build evidence

| Gate / control | Evidence | Result |
| --- | --- | --- |
| A identity | Production setup service exchanged the credential and accepted the connection only after the returned `shop.myshopifyDomain` exactly matched `testin-lzhbzhtc.myshopify.com`; the store records API `2026-07`, a credential-present mirror, verified timestamp, and passing connection result. | **Pass on predecessor build**; repeat on the new exact head is required. |
| Location read | Production location-refresh job `3239` succeeded first attempt and returned `Shop location`, `test`, and `testt`. | **Pass on predecessor build**. |
| Location mapping | Mapping `94` binds Shopify location `gid://shopify/Location/90389938361` to Odoo `WH/Stock`, store/company scoped, active and push-enabled. A Chicago-company target was refused. | **Pass with a UI/server company-fence defect discovered and corrected in the new code checkpoint**. |
| Webhook bootstrap | Job `3241` ran through the real dispatcher, retried twice with bounded backoff, and ended `Failed (Final)` rather than falsely succeeding. | **Fail on predecessor build**. Shopify returned HTTP 200 plus GraphQL `selectionMismatch` because `WebhookSubscription.apiVersion` was queried as a scalar. |
| Activation fence | Activation refused because no passing/warning readiness record existed. | **Pass (fail closed)**. |
| Setup rerun | Rerunning setup required credential replacement despite a valid stored credential. | **Fail on predecessor build; corrected and independently reviewed in the new checkpoint**. |

No predecessor-build result is treated as exact-head qualification for the new
code checkpoint. A completed Odoo job is not treated as remote business success.

## Architecture corrections in the code checkpoint

1. Shopify webhook subscription list/create queries now select the official
   `ApiVersion` object (`handle`, `displayName`, `supported`) and retain only the
   handle as comparison evidence. GraphQL selection/schema mismatch remains in
   the existing `data_shape_schema_mismatch` taxonomy.
2. Stored-credential reuse is a non-secret, action-time server operation. It is
   serialized under the established store-then-credential lifecycle lock order;
   concurrent clear or mode replacement causes safe refusal without advancing
   setup progress. Client-secret inputs are cleared even on local validation
   failure.
3. Location creation, remap, resolver, generic binding, inventory pair bootstrap,
   and level-binding constraints use the selected store's company rather than
   the browser's active company. Active-other-allowed-company and true-foreign
   paths have production-path regression coverage.
4. A modular inventory webhook observation add-on provides store-scoped durable
   observation, composite InventoryLevel/InventoryItem/Location validation,
   strict timestamps, stale-event protection, bounded fair reconciliation, and
   dispatcher retry/replay coverage.
5. Modular order and fulfillment webhook add-ons provide read-first acceleration.
   Cancellation remains an evidence signal, stale connection generations fail to
   manual review, equal-timestamp changed evidence fails closed, only proven
   succeeded duplicates are reusable, and fulfillment replay admits observations
   without creating outbound fulfillment/tracking mutations.
6. The connector suite explicitly installs and selects all three new domain
   webhook add-ons. Static compilation, diff checks, runner syntax and runner
   fail-closed self-tests pass locally. Full Odoo/PostgreSQL/HOOT execution is
   pending exact-head CI/Odoo.sh qualification.

## Independent review record

- Inventory webhook final reviewed tree `1309f088b45d2baa8c42f8b02c582b5db0cca8ed`:
  **ACCEPT**, no open material finding.
- Order/fulfillment webhook final reviewed tree
  `50bf886ea3d9c4590f9a274efacaec5c4b766f11`: **ACCEPT**, no open material
  finding.
- Onboarding/API/company-fence final reviewed tree
  `d883c82fa200b96fc053466ada53931e192776b9`: **ACCEPT**, no P0-P3 finding.

No implementation worker was the sole reviewer of its own change.

## Official baseline used

Accessed 2026-08-22:

- Shopify webhooks, verification, subscription lifecycle, Admin GraphQL limits,
  Bulk Operations, and idempotent requests documentation.
- Shopify Admin GraphQL 2026-07 `WebhookSubscription`, `ApiVersion`, and
  `webhookSubscriptionCreate` schema documentation.
- Odoo 19 backend security and performance documentation.
- Odoo.sh frequent technical questions, including the practical five-minute
  scheduled-action interval and small-batch operational guidance.

The architecture decision remains hybrid: near-real-time webhook signals plus
scheduled reconciliation. Webhook delivery is never described as synchronous or
complete on its own. Refund ingestion remains unsupported in the accepted MVP;
no `refunds/create` subscription may be activated until a refund ledger/credit
note contract exists. Privacy topics remain a distribution decision, not an
implicitly tested feature.

## Current gate decision

**NOT ASSURED — CORE ARCHITECTURE GAPS** remains the operative decision at this
checkpoint because the corrected code has not yet been published, CI-qualified,
deployed, or exercised live. Gates B-D and F-H remain incomplete; Gate E must be
rerun against an actual Shopify subscription and delivery on the corrected exact
head. Product/inventory UI UAT, order/fulfillment UI UAT, and production-release
planning remain blocked until a later dated addendum records those results.

