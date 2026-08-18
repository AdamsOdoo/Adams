# W1 Webhook Correction Packet — definition-of-done for the REVISE at `f62db111`

> Reviewer's acceptance contract for the consolidated correction of the W1
> webhook REVISE ([PR #206 comment 5328283841](https://github.com/AdamsOdoo/Adams/pull/206#issuecomment-5328283841)).
> This is the bar the correction must clear to flip REVISE → ACCEPT. It is the
> first concrete work order under [DEC-042](../04-decisions/DEC-042-one-iteration-completion-program.md);
> whoever implements (GPT-5.6 Sol per the program) works to these criteria and
> re-posts `READY-FOR-CLAUDE-REVIEW` at the new head. One consolidated pass, no
> dribble. Preserve the delegation architecture, HMAC discipline, evidence
> model, and ACL/service-context model exactly.

## Blocking corrections (each row must be fully satisfied)

### B-1 — Product acceleration must survive every update, not just the first
- **Allowed files:** `shopify_connector_product_webhook/models/shopify_connector_product_webhook.py`, its tests; if the subscription-health contract changes, `shopify_connector_webhook/models/shopify_connector_webhook_subscription.py`.
- **Required change:** the per-event job identity must vary per real event. Either (a) add `updated_at` and `id` to `include_fields` and make the subscription-health check *enforce* their presence (a filtered-out `updated_at` must read as `filtered`/unhealthy, not `active`), or (b) stop deriving `payload_hash`/idempotency from the payload and key admission on the delivery/scope instead — preferred, as it matches read-first.
- **Acceptance criteria:** a second `products/update` for a product whose first import already reached a **terminal** state enqueues a *new* read job (or is provably coalesced only while the prior job is non-terminal), and the delivery is never marked `processed` while dropping a real change.
- **Mandatory tests:** a behavioral test using the **production payload shape** — no injected `source_updated_at`, digest derived from the real body — that drives event 1 → terminal → event 2 and asserts a second import is admitted. The existing W2 fixture that injects a unique digest must be corrected, not relied upon.
- **Live/doc gate:** OQ-1 below resolved.

### B-2 — `app/uninstalled` must be generation-fenced and read-first
- **Allowed files:** `shopify_connector_webhook/models/shopify_connector_webhook_registry.py`, `..._delivery.py`, `..._controller`, tests.
- **Required change:** before fencing a store, require `delivery.job_id.expected_connection_generation == store.connection_generation` under the lifecycle lock (mirror `_handle_product_webhook`), and confirm uninstall with an authoritative Shopify read rather than trusting the unsigned topic header. Add a secondary dedup dimension on signed material `(store, topic, payload_digest)` and reject deliveries whose `X-Shopify-Triggered-At` is older than a bounded skew.
- **Acceptance criteria:** a stale/replayed `app/uninstalled` delivery arriving after a reconnect (generation advanced) does **not** fence the healthy store; a store is only fenced when an authoritative read confirms uninstall.
- **Mandatory tests:** generation-mismatch delivery → no state change; a forged-topic replay of a captured body → rejected/no-op; a genuine current-generation uninstall confirmed by a mocked authoritative read → fenced.
- **Live/doc gate:** OQ-2 (delivery-id stability across retries) resolved.

### B-3 — `expected` must be restored on re-materialization
- **Allowed files:** `shopify_connector_webhook/models/shopify_connector_webhook_subscription.py`, `..._readiness.py`, tests, a migration if needed for already-broken rows.
- **Required change:** include `not record.expected` in the `changed` predicate and add `'expected': True` to the `_service_write` in `_ensure_expected_for_store`.
- **Acceptance criteria:** uninstall a domain webhook addon (sets `expected=False`) → reinstall → readiness returns to `RESULT_PASS`, with no DB edit; a stale queued `webhook_subscription_delete` for a re-materialized topic must not delete the live subscription.
- **Mandatory tests:** an uninstall→reinstall behavioral test over a registry-extension addon asserting `expected=True` is restored and readiness recovers.

### B-4 — The route and lifecycle must have behavioral tests
- **Allowed files:** test files in both addons.
- **Required change:** replace the `read_text()` source-grep assertions with behavior. Rule: a test that still passes if the function body is replaced with `pass` does not count.
- **Acceptance criteria / mandatory tests:** an `HttpCase` (or `receive()` against a constructed request) covering the full status matrix — 404 unknown token, 401 bad/missing HMAC, 400 shop-mismatch / api-version / missing headers / malformed JSON, 200 on duplicate delivery, and the raw-bytes-survive-dispatcher path; behavioral tests for `run_scheduled_reconciliation` (fairness cursor, no-secret skip, IntegrityError swallow), the `_reconcile_store` branch matrix (active/filtered/wrong_uri/missing), `_classify_subscription_mutation` + `_reconcile_subscription_mutation` including the `duplicate_risk`→`block_manual_review` fences, `_handle_app_uninstalled`, HMAC grace-window expiry, and the B-1 terminal-child dedup path.
- **Live/doc gate:** OQ-3 (dispatcher/stream ordering) resolved and encoded as a test.

### B-5 — Callback token must be rotatable/revocable
- **Allowed files:** `shopify_connector_webhook/models/shopify_connector_webhook_secret.py`, `..._subscription.py`, views, tests.
- **Required change:** implement the overlap rotation the docstring defers to — mint a second secret, subscribe the new callback URL, verify by read-back, then deactivate the old row — plus an Administrator action to trigger it.
- **Acceptance criteria:** a leaked token can be rotated entirely in-product with no gap in verifiable deliveries and no raw SQL; the old token stops verifying only after the new one is confirmed live.
- **Mandatory tests:** rotation lifecycle test (both secrets valid during overlap; old rejected after cutover; readiness stays green throughout).

### B-HIGH (fold in) — product-export custom-ID first-run deadlock
- **Allowed files:** `shopify_connector_product_export/models/shopify_connector_product_export_service.py`, tests.
- **Required change:** skip the `productByIdentifier` custom-ID lookup (or force the definition bootstrap first) when `product_export_binding_namespace_ready` is False, so a store's first-ever create preview cannot hard-fail on a definition that doesn't exist yet.
- **Acceptance criteria / test:** first create preview on a store with no unique metafield definition succeeds and bootstraps the definition; a live canary on a definition-less dev store confirms it.

## P2 set (same consolidated pass)
Body read before token resolution + JSON content-type allowlist; non-ASCII HMAC header → 401 not 500; drop the `X-Forwarded-Proto` fallback (document `proxy_mode`); add `job_source` to the setup recovery search; exception-isolate the reconciliation cron and advance the cursor on every outcome; use the `FOR SHARE` admission lock (not the lifecycle writer lock) in the delivery hot path; narrow the broad `except Exception` over that lock so concurrency errors retry; reuse core's `_concurrency_retry_supported()` for the `_commit_progress` gate; document the W2-install full-catalog re-import as a deliberate migration; document reconcile-to-empty before module uninstall.

## Open questions — resolve live/against docs before re-posting (do not assert)
- **OQ-1:** does `webhookSubscriptionCreate` accept `updated_at`/`id` (and reject `admin_graphql_api_id`) in `includeFields` for `PRODUCTS_UPDATE`? Confirm the exact valid field names on a live store; a `userError` here means no subscription is created at all.
- **OQ-2:** is `X-Shopify-Webhook-Id` stable across retries of the same event? B-2's dedup and replay reasoning depends on it.
- **OQ-3:** exact Odoo 19 `HttpDispatcher` ordering w.r.t. `httprequest.form` vs `request.stream`, encoded as the B-4 raw-body test.

## Definition of done
All blocking rows satisfied with their mandatory tests green; P2 set addressed; three open questions resolved with evidence; exact-head Actions **and** Odoo.sh green; ledger §10 updated; `READY-FOR-CLAUDE-REVIEW — W1 correction — <new SHA>` posted. Rollback: the correction is an independently revertable commit stack on the PR branch; reverting it restores `f62db111` behavior.
