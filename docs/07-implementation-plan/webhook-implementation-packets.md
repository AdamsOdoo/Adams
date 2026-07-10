# Webhook Implementation Plan — Phases W1–W5 (Layered Posture)

> **Status: Proposed for ChatGPT review. NOT accepted. No webhook code
> exists or is authorized; the W1 prompt in §6 is NOT usable.**
> Produced 2026-07-10 (AR-042 candidate). Closes OP-27's per-domain
> planning, Q23/OP-36 (payload PII redaction list) at proposal level.
> Evidence: captures §7 (all webhook mechanics re-verified
> 2026-07-10). The accepted rule stands verbatim: **webhooks
> accelerate synchronization but do not replace scheduled
> reconciliation** (DEC-005; Shopify's own text: "Your app shouldn't
> rely on receiving data from Shopify webhooks… use reconciliation
> jobs"). Consequence carried into the master plan: **DEC-003's
> C-SYNC-01/02/03 webhook items are MVP scope, sequenced after the
> Lite import chain + Area 6 + UI-U1 and before MVP release** — W1+W2
> are MVP-tail; W3+ are post-MVP/Phase-2+.

## 1. Phases

| Phase | Contents | MVP? | Gate prerequisites |
| --- | --- | --- | --- |
| **W1 — Core receiver + subscription management** | One HTTPS controller in core (`/shopify/webhook/<store>`), raw-body HMAC-SHA256 verify (401 on mismatch), fast-ack 200 within the 1 s/5 s budget (enqueue-only), `X-Shopify-Webhook-Id` dedup table, `X-Shopify-Event-Id` correlation logging, topic-registration seam (domains declare topic→job_type), shop-specific subscriptions via `webhookSubscriptionCreate` (branch A has no TOML pipeline — app-specific subscriptions become the Phase-2+ B-1 mechanism), subscription-state readiness check (webhook_ready flag finally populated), delivery log with PII redaction (§3) | Yes (MVP tail) | Area 6 + U1 merged; W1 gate act |
| **W2 — Order + product topics** | `ORDERS_CREATE`/`ORDERS_UPDATED` → enqueue `order_import_sync` (evidence-refresh semantics already merged); `PRODUCTS_CREATE`/`UPDATE`/`DELETE` → enqueue-only + authoritative re-read (accepted DEC-020/MBQ-65 posture; DELETE never deletes) | Yes (MVP tail) | W1 merged; W2 gate act |
| **W3 — Inventory drift detection** | `INVENTORY_LEVELS_UPDATE` → drift-note job only (never a write trigger; MBQ-63 exclusion preserved) | No — post-MVP option | Task 013 merged; own act |
| **W4 — Customer topics** | `CUSTOMERS_CREATE/UPDATE` → enqueue `customer_import_sync` | No — post-MVP option (scheduled scan suffices) | own act |
| **W5 — Compliance webhooks** | `customers/data_request`, `customers/redact`, `shop/redact` + `app/uninstalled` — required only for App-Store distribution; TOML-configured (cannot use Admin API); 30-day response obligations; DEC-028 Rung-2 item (b) | No — Phase 2+ (B-1) | RA-003 lift + B-1 gate |

## 2. Mechanics contract (fixed by the 2026-07-10 captures — the facts every W-phase builds on)

HMAC over **raw body** with the app client secret
(`X-Shopify-Hmac-SHA256`; rotation grace ≤1 h); duplicates possible →
dedup on `X-Shopify-Webhook-Id` (persisted, unique-constrained, 30-day
retention); ordering NOT guaranteed → handlers never assume sequence
(the enqueue-then-authoritative-re-read posture makes ordering
irrelevant by design); retry = 8 attempts over 4 h; **shop-specific
(Admin-API-created) subscriptions are auto-deleted after 8 consecutive
failures** → W1's readiness check re-verifies subscription existence
every readiness run and re-creates missing ones (self-healing,
logged — this is the concrete consequence of branch A using
shop-specific subscriptions); payload version pinned to the store's
`api_version`; `X-Shopify-API-Version` recorded per delivery.

## 3. Payload PII redaction list (Q23/OP-36 closure proposal)

Webhook delivery logs store headers + topic + IDs, **never raw
payloads by default**; when payload capture is enabled for debugging
(admin-only, per-store, auto-expiring flag), the stored copy passes
`redact()` extended with: `email`, `phone`, `first_name`, `last_name`,
`name`, `address1/2`, `city`, `zip`, `province`, `country`,
`company`, `latitude/longitude`, `browser_ip`, `customer_locale`,
`note`, `payment_details`, plus any key matching `*_email`/`*_phone`/
`*address*`. The same extension list feeds the Task-012
REDACTION_EXTENSION (one shared definition, core-owned at W1 time).

## 4. Reconciliation interplay & tests strategy

Webhooks only ever enqueue the same idempotent jobs the scans enqueue —
a missed webhook is corrected by the next scan (checkpoint overlap);
a duplicate webhook collides on `idempotency_key`. Test strategy per
phase: unit — HMAC pass/fail/tamper, dedup collision, fast-ack
timing (no inline work — source-level guard), topic routing,
subscription re-creation; integration — end-to-end
webhook→job→import on Odoo.sh with synthetic signed payloads; W5
adds the 401-on-invalid-HMAC compliance contract tests. Live-store
webhook delivery is an [External validation required] item folded
into the VAL-B2 follow-up appendix (needs a reachable HTTPS endpoint —
an infrastructure prerequisite recorded in the release plan; not
satisfiable by any planning session).

## 5. Register impacts on acceptance

OP-27 → Resolved-by-plan (phased, posture preserved); Q23/OP-36 →
Resolved at proposal level (§3 list); MBQ-63/MBQ-61 exclusions
restated untouched; MBQ-65 residual (controller/subscription
mechanics) → Resolved-by-W1/W2-design.

## 6. Locked prompt — Phase W1 (W2 prompt drafted after W1 merges; W3–W5 have no prompts by design — post-MVP/Phase-2+ gates)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE W1 GATE, VERIFIES THE CURRENT BASE SHA, AND
ISSUES THIS PROMPT. (Additionally: do not schedule this gate before
Area 6 and UI-U1 are merged.)

Implement webhook Phase W1 exactly per
docs/07-implementation-plan/webhook-implementation-packets.md §1–§4.
Branch from the verified current tip (STOP on drift). One session;
draft PR; stop.

ALLOWED FILES: addons/shopify_connector_core/controllers/{__init__.py,
shopify_connector_webhook.py} (NEW), addons/shopify_connector_core/
models/{shopify_connector_webhook_delivery.py (NEW — dedup/delivery
log), shopify_connector_webhook_subscription.py (NEW — registration
seam + webhookSubscriptionCreate service + readiness re-verify)},
addons/shopify_connector_core/models/__init__.py (import lines),
addons/shopify_connector_core/__manifest__.py (controllers),
addons/shopify_connector_core/security/ir.model.access.csv (new-model
rows only), addons/shopify_connector_core/tests/{test_webhook_hmac.py,
test_webhook_dedup_and_ack.py, test_webhook_subscriptions.py} (NEW),
docs/05-qa/webhook-w1-validation-results.md (NEW), AR-log append row,
handoff top entry. FORBIDDEN: every domain module; every existing
core model file except __init__/manifest/ACL as listed; any topic
handler that does domain work inline; compliance topics (W5);
UI beyond nothing; OAuth; CI; adams_base.

HARD CONSTRAINTS: verify HMAC on the RAW body before parsing; 401 on
mismatch; 200 fast-ack with enqueue-only (source-level no-inline-work
guard test); dedup unique constraint on webhook id; no payload stored
unless the auto-expiring debug flag is on, and then only through the
shared redaction extension (§3); subscription re-creation logged and
idempotent; the layered rule restated: reconciliation remains
mandatory, webhooks are acceleration only. Odoo.sh green (verbatim
quote). Stop condition: draft PR "W1: webhook receiver and
subscription management"; gate closes on draft-open; no W2 topic
handlers.
```
