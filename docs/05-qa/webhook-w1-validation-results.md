# Shopify Connector W1 Webhook Validation Results

Date: 2026-08-18
Exact implementation base: `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8`
Independent-review correction base: `f6f4691e93a3f9ebd21f54f42362084b0bb1d3e7`
Second SOL correction base: `8da1c979eb1590917af0b5b4ab8579be1cb0dad3`
Branch: `codex/pr206-webhook-w1`
Scope: `addons/shopify_connector_webhook/**` plus this QA record and the dated
implementation-plan entry.

## Evidence status

| Check | Result | Evidence / limitation |
|---|---|---|
| Python syntax compilation | PASS | `python3 -m compileall -q addons/shopify_connector_webhook` |
| Raw-body HMAC helper | TEST ADDED | Odoo `TransactionCase`; exact bytes, pass, missing, tamper |
| Signature-before-JSON ordering | TEST ADDED | Source guard in `test_webhook_w1.py` |
| Exact shop/API/topic gating | TEST ADDED | Controller source and registry contracts; live HTTP not run |
| Delivery deduplication | IMPLEMENTED / NOT LIVE-EXECUTED | DB unique `(store_id, delivery_id)` plus savepoint duplicate path |
| No raw payload persistence | TEST ADDED | Strict identity allowlist and no `payload` field |
| Fast ACK / no inline business processing | TEST ADDED | Controller only verifies, persists envelope and enqueues |
| Durable processing/replay policy | IMPLEMENTED / NOT LIVE-EXECUTED | `webhook_delivery_process` handler and core dispatcher registry |
| Subscription list | IMPLEMENTED / NOT LIVE-EXECUTED | Core `execute_business` lease context; paginated, identity-checked |
| Subscription create/delete | IMPLEMENTED / NOT LIVE-EXECUTED | Core Layer-2 strategy, attempt evidence and read-before-retry |
| Expected-vs-actual reconciliation | IMPLEMENTED / NOT LIVE-EXECUTED | Bounded scheduled/manual jobs, URI digest and API-version evidence |
| Readiness and bootstrap lifecycle | IMPLEMENTED / NOT LIVE-EXECUTED | Pre-activation readiness is explicitly not-applicable; Bootstrap / reconcile queues a lifecycle-only read and never creates remote subscriptions until connected |
| App client-secret HMAC grace | IMPLEMENTED / NOT LIVE-EXECUTED | Sanctioned credential replacement captures the old secret in an addon-only ACL-hidden field for a conservative two-hour exact expiry; ingress tries current then unexpired previous, while readiness/health remain pending/degraded |
| Uninstall handling | IMPLEMENTED / NOT LIVE-EXECUTED | Existing fenced `action_mark_reconnect_needed` lifecycle service |
| 30-day retention | IMPLEMENTED / NOT LIVE-EXECUTED | Daily cron, terminal-state batch limit 500 |
| ACL/company isolation | IMPLEMENTED / NOT LIVE-EXECUTED | Addon ACL and global company rules; runtime RPC tests require Odoo |
| Live Shopify / Odoo.sh / HTTPS delivery | NOT RUN | Explicit W1 worker restriction; no credentials, mutation or live call |

## Focused test inventory

`addons/shopify_connector_webhook/tests/test_webhook_w1.py` covers the pure
HMAC contract, raw-byte tamper behavior, missing signature, active-vs-catalog
topic separation, strict non-PII identity extraction, absent raw payload field,
token digest uniqueness, retention/state vocabulary, and source-level guards
for no inline processing and business-lease subscription reads.

The Odoo test module is intentionally no-network. Exact duplicate concurrency,
ACL/RPC/company contexts, job dispatch, subscription GraphQL mocks, readiness
state transitions and retention deletion must be run by the Odoo.sh qualification
suite on an installed module. A queued or successful job is not remote-success
evidence; fresh Shopify read-back remains required before any UAT decision.

## Known limitations / follow-up gates

1. W1 subscribes only to `app/uninstalled`. Product, inventory, order,
   fulfillment, refund and cancellation domain handlers are not installed and
   therefore are not active webhook topics.
2. No live development-store endpoint, Shopify subscription, webhook delivery,
   remote read-back, retry, replay, conflict or cleanup evidence exists in this
   worker result.
3. The current connector's API constant is `2026-07`; Shopify's app-level
   webhook API version is recorded/read back and must be verified live.
4. The new addon must receive independent SOL review and complete install,
   upgrade, migration, uninstall, Odoo.sh fresh/warm and exact-head CI gates
   before it can be considered for controlled UI UAT.
5. Callback-token rotation is intentionally disabled: no endpoint token is
   rotated without an old/new callback overlap and Shopify subscription
   migration/read-back protocol. App client-secret replacement is separately
   covered by the addon-owned previous-secret field for a conservative two-hour
   HMAC grace; readiness is explicitly pending/degraded until its recorded
   expiry. The repository's existing secret storage is ACL-only/plaintext, not
   encrypted at rest, and that residual remains disclosed.
6. Scheduled reconciliation uses a bounded time-slot idempotency key and a
   per-store scheduling cursor so repeated cron/manual runs can create a new
   attempt after terminal evidence and progress fairly beyond the batch size.
