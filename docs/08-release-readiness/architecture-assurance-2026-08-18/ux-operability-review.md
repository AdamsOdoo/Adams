# UX and operability review

**Date:** 2026-08-18

**Exact head/tree:** `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8` /
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

**Status:** source review only; no decisive exact-head browser screenshots or
live remote-success screenshots are in the evidence ledger.

## Information architecture

The current organization follows the accepted principle in code/views:

- first-time setup under Configuration (`shopify_connector_setup_wizard.py`;
  twelve durable setup steps);
- daily work under Operations (product/inventory/order/fulfillment operations,
  jobs and recovery);
- commercial reporting in the sales dashboard;
- integration reliability in Connector Health rather than Sales Dashboard;
- related settings grouped by store/domain.

This is a good foundation. It must not be treated as UAT evidence until an
operator completes the workflows against the exact build and remote shop.

## Workflow review

| Workflow | Code/UI evidence | Good control | UAT concern or required correction |
| --- | --- | --- | --- |
| Onboarding/store creation | `setup_wizard.py:SETUP_STEPS`, `save_store_identity()` | Bare domain validation; duplicate refusal; immutable identity; active-company assignment | Correct store must be newly created, not historical row 555. No live credential/identity proof yet. |
| Credential entry | `save_credential()` and credential model | Write-only/masked handling; no token echo; admin boundary | Verify direct RPC/URL and logs cannot reveal the secret; at-rest encryption policy remains open. |
| Connection test | `store.action_test_connection()` / `_run_connection_probe()` | Fixed purpose, remote identity/scope/API verification, generation fencing and audit | UI must only show pass after remote identity; no exact-head live screenshot/evidence. |
| Location mapping | Inventory location wizard/views | Explicit GID mapping; no name inference; company/store scope | Must prove exact location and InventoryItem bindings against live shop. |
| Readiness | `run_readiness()` and readiness check views | Rechecks stored evidence; blocking/waiting checks prevent activation | `webhook_hmac` displays Not required because no intake exists; this is accurate for current code but not acceptable for a near-real-time release. |
| Sync ownership | `SETUP_DOMAINS` and settings | Direction choices are visible and activation triggers only selected producers | Inventory copy promises Shopify→Odoo baseline although stock write is deferred; correct before UAT. |
| Webhook health | `store.webhook_ready`, readiness placeholder | Honest N/A for absent capability | No subscription status, delivery health, HMAC outcome, backlog or dead-letter view exists. |
| Scheduled reconciliation | Cron records and Connector Health | Jobs, retries and local health are visible; scans are bounded | 15–60 minute domain cadences must be presented as reconciliation, not real-time. |
| Product operations | Product import/export views, preview/apply | Import matching review; export confirmation; omission-safe writes | No live remote read-back or duplicate/no-op evidence. |
| Inventory operations | Inventory pair/preview/recovery views | First push preview; CAS conflict and manual release path | Must not imply Shopify inbound quantity synchronization. |
| Orders and customers | Sale scans/import/review/dashboard | Duplicate binding protection, tax/payment review, conservative lifecycle | Order freshness is 15-minute polling today; no webhook evidence. |
| Fulfillment/tracking | Fulfillment operations, Mode 1/Mode 2 review | Outbound confirmation/reconciliation and inbound review states | Setup copy says no read-back while Mode 2 does read/reconcile; clarify. |
| Jobs/errors/retry/recovery | Core jobs/logs/attempts/health and domain views | Actionable state ladder, bounded retries, manual review, evidence retention | No live failure/recovery proof; ensure merchant-facing labels do not expose internal classes. |
| Permissions | Security XML/ACLs/company rules and UI actions | Server-side boundaries and role-aware menus/actions | Dedicated-user, direct RPC/URL and multi-company runtime matrix still required. |
| Dashboards/reports | Connector Health and Sales Dashboard code/views | Reliability is separated from commercial operations | Verify counts are based on proven state, not only local job completion. |

## Field/button acceptance checklist

Before UI UAT each visible field/action must have:

- a merchant-language label and purpose;
- a safe default and documented consequence;
- server-side authorization independent of visibility;
- immediate, actionable feedback and a predictable next step;
- correct disabled/hidden behavior when a capability is unsupported;
- a success message tied to remote verification where a Shopify mutation is
  claimed;
- no raw stack trace, credential, payload or internal-only terminology.

## Findings

1. **[P1] Inventory direction copy is inconsistent with backend authority.**
   `SETUP_DOMAINS` says “Shopify to Odoo, then Odoo to Shopify” and “Stock
   levels are read in as a baseline”; the inventory manifest says Shopify→Odoo
   stock write and reviewed baseline import are deferred. This can lead to an
   operator believing quantities were reconciled when they were not.
2. **[P2] Fulfillment Mode 2 is under-described.** The module documents
   conservative inbound reconciliation, while setup copy says fulfillments are
   never read back to create Odoo deliveries. State the exact eligible inbound
   effects and review-only cases.
3. **[P1] Webhook status is honest but incomplete.** “Not required” accurately
   describes the absent module; it cannot satisfy a release that requires
   near-real-time inbound signals. Add subscription/delivery/reconciliation
   health after implementation.
4. **[P1] Success language must wait for live read-back.** A queued/succeeded
   local job, HTTP 200 or screenshot cannot substitute for a fresh remote read.
5. **[P2] Internal source comments drift.** The GraphQL client docstring calls
   the business context dormant although production call sites use it; stale
   comments should be corrected to preserve operator/developer trust.

## UAT status

- Product/inventory UI UAT: **blocked** until backend Gates A–E and D have
  live exact-head evidence, plus direction-copy correction.
- Order/fulfillment UI UAT: **blocked** until Gate F and webhook/reconciliation
  readiness are proven; Mode 2 copy must be clarified.
- Screenshots currently demonstrate presentation only; none are decisive
  backend correctness evidence.
