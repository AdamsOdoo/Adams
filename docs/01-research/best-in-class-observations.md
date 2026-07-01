# Best-in-Class Observations (Research Sprint C)

> The **strongest observed practices** across the competitor connectors, with the
> evidence that supports each, so we can **adapt the lessons** (not copy blindly).
> **Inference/recommendation only — no MVP/architecture decided** (`CLAUDE.md`
> §4–§5). Access date 2026-06-30. Each "best observed" names the connector, what
> it does, and why it sets a quality bar; the evidence is consolidated at the end.

## Best observed setup / onboarding

- **VentorTech — OAuth-first connect with an up-front scope check + connection
  test.** "OAuth authentication — no manual API tokens"; an automatic check of
  required scopes and a connection test "before you continue". *Bar:* the user
  proves the connection works (and has the right scopes) **before** any sync —
  fewer mid-sync auth surprises.
- **Webkul — an explicit "Test Connection" button** as a discrete validation
  step after credential entry. *Bar:* a single, obvious pass/fail gate.
- **Emipro — honest setup gotchas.** Docs warn that "any mismatch — including a
  trailing slash — will cause the authorization to fail." *Bar:* pre-empt the
  most common failure in the docs/UI, not in a support ticket.
- *Adapt:* OAuth-first + early scope/connection test + inline warnings for known
  pitfalls — **without** VT's heavy `odoo.conf`/`queue_job`/worker install
  burden.

## Best observed product sync handling

- **Emipro — incremental, filterable product import + a CSV/XLSX mapping
  fallback.** Create/Update date ranges, "Do not update existing products",
  "Import Draft products", From-Date defaults to last execution; non-SKU catalogs
  map via an exported CSV (named columns) then re-upload. *Bar:* handles messy
  catalogs and large incremental syncs.
- **VentorTech — bidirectional product sync with draft-export-for-review +
  per-field directional mapping + custom Python transforms + test-against-live-
  data.** *Bar:* safe, controllable, testable catalog sync; respects the Tier-1
  2048-variant model (fixed a 250-variant cap in v2.1.4).

## Best observed order flow

- **VentorTech — webhook order import "within seconds" + a configurable
  auto-workflow ("up to 5 steps: confirm → ship → invoice → send → pay") shown as
  a visual pipeline, each step a background job, with fraud-score thresholding and
  auto-create of missing products/carriers/taxes.** *Bar:* near-real-time intake
  with transparent, rule-based downstream automation.
- **sh_shopify_connector — Payment Gateway Workflow Matrix** routing order
  processing per gateway, plus an Auto Sale Workflow (auto invoice/validate/
  register/force-transfer). *Bar:* correct per-gateway invoice/payment handling.
- **Emipro — multi-payment orders modelled as multiple payment lines** (gift card
  + stripe → two lines). *Bar:* faithful representation of real Shopify payments.

## Best observed inventory handling

- **VentorTech — quantity-field choice (Free/On-Hand/Forecasted), real-time on
  stock-move OR scheduled, multi-location mapping, BoM-based available stock, and
  multi-company inventory with correct company context.** *Bar:* flexible,
  multi-warehouse, manufacturing-aware inventory.
- **Emipro — deterministic stock export** (only-synced products, only-changed-
  since-last-run else last 30 days, per Shopify Location) + an explicit
  **Forecast vs Free-to-Use** choice with formulas. *Bar:* predictable, efficient
  stock export. *(But avoid EM's manual Inventory-Adjustment step on import.)*
- **VentorTech (R4) — "External Location" mapping grid with a default fallback.**
  *Bar:* low-error multi-location mapping.

## Best observed fulfillment / tracking handling

- **Emipro — Put-in-Pack multi-package fulfillment export + explicit Shopify
  fulfillment-scope granting walkthrough.** *Bar:* multi-package shipments and
  correct Shopify scopes (aligns with Tier-1 FulfillmentOrder scopes).
- **sh_shopify_connector — delivery validation → queue "done" with a fulfillment
  ID written back.** *Bar:* a clear, auditable fulfillment-ID link.
- **VentorTech — carrier tracking export + per-warehouse transfers** (with
  `sale_sourced_by_line`). *Bar:* tracking write-back + split-warehouse correctness.

## Best observed logs / error handling

- **Emipro — state-coloured Data Queues (Draft/Failed/Cancelled/Done) + per-line
  Log Lines + a reason-coded Log Book / Mismatch Log** ("SKU not found", "tax not
  found", "customer missing in order"). Failures are isolated from successes; a
  "processed" ribbon signals completion. *Bar:* the best **observability** in the
  survey — users can see exactly what failed and why.
- **VentorTech — traffic-light webhook health (green/yellow/red) where yellow =
  "callback URL mismatch — check `web.base.url`", + Failed Job Notifications +
  per-line "internal info" + automatic retry of safe operations.** *Bar:* the
  best **diagnostics + recovery** — the status encodes the fix.
- **sh_shopify_connector — queue failure counts + a daily activity chart + audit
  logs + a "Needs Shopify Re-Export" recovery flag.** *Bar:* the best
  **monitoring** visualization.

## Best observed documentation

- **Emipro — rich, screenshot-heavy, honest docs** that state limitations plainly
  (Markets-no-multi-warehouse; Net-Profit Enterprise-only; payouts Shopify-
  Payments-only; manual inventory adjustment). *Bar:* readable, demonstrative,
  trustworthy. *(Weakness to avoid: its published v19 changelog is stale.)*
- **VentorTech — dated, mechanism-level release notes** (1.13.0 → 2.1.6) that
  openly disclose CRITICAL bug fixes (silent order-skip on paging; timezone
  filter). *Bar:* transparent maintenance history that builds trust.

## Best observed UX/UI

- **VentorTech — diagnostics-first UX** (traffic-light health, Preview/Report
  dry-run before export, failed-job notifications, irreversible-action warnings,
  honest PII disclosure). *Bar:* the most polished operational UX.
- **sh_shopify_connector — a real command center** (Integration Dashboard +
  activity chart + queue dashboards) with **access-right-gated** setup. *Bar:* the
  best monitoring surface + a sound security default.
- **Webkul — stage-before-commit "Feeds" with a fixable error queue.** *Bar:* a
  simple, teachable resilience model for non-developers.

## Best observed support / maintenance

- **VentorTech — priority support while subscribed + automatic git-repo updates +
  frequent dated releases (incl. Shopify API 2026-04 compliance).** *Bar:* active,
  current maintenance with a clear support SLA.
- **ecommerce_shopify — fast recent dated cadence** (5 releases in ~1 month).
  *Bar:* responsiveness — though scope is small and adoption unproven.
- **Teqstars — 83 reviews / 5.0 (Apps listing) + claimed free install session; a
  documented Support Policy** (60-day free bug-fix, scope/exclusions, 24h target).
  *Bar:* strong social-proof claim **plus** (Sprint C2) a **now-demonstrated,
  screenshot-rich doc set** with an explicit support policy — onboarding depth is
  no longer purely claimed.
- **Teqstars — controlled, draft-safe product onboarding (Sprint C2, now
  demonstrated).** SKU/Barcode/both match key + Create-Odoo-Products guard +
  **draft-safe export** (leave Sales Channels empty → unpublished) + Publish/
  Unpublish + a per-listing **Allowed/Not-Allowed-Sync** switch. *Bar:* a clean,
  safe bidirectional-*product* pattern (directly relevant to the accepted DEC-003
  MVP baseline).
- **Teqstars — click&collect order status + Force-Restock divergence warning +
  Shopify-Payments payout reconciliation with reason-coded line warnings (Sprint
  C2, demonstrated).** *Bar:* first-class pickup lifecycle and honest divergence
  handling.

## Best ideas worth adapting (synthesis — gated recommendations)

1. **Idempotency by default** (VT) — `@idempotent` on inventory/refund writes per
   Shopify 2026-04; persist idempotency keys.
2. **Automatic retry of safe operations + clear manual override** (VT).
3. **A real async job queue** for throughput/isolation (VT `queue_job`) — *but
   decide the dependency consciously (Tier-1: not in Odoo core; AR-003).*
4. **Reason-coded, per-record, in-app logs + isolated failures + completion
   signals** (EM).
5. **Traffic-light health with a named cause + fix hint** (VT) — generalize to all
   connection/webhook/sync health.
6. **Dry-run / Preview before any destructive apply** (VT catalogs).
7. **A unified command center**: connection health + queue status + activity
   timeline + quick actions (combine SH + VT).
8. **OAuth-first connect + early scope/connection test + credential masking** (VT)
   — minus the heavy install.
9. **Incremental/filterable imports + CSV mapping fallback** (EM).
10. **Honest docs + dated changelog + disclosed limitations** (EM + VT).
11. **Access-right-gated setup; admin vs functional-user separation** (SH/EM).
12. **Payout reconciliation done robustly** (EM) — and **demonstrably**.
13. **Multi-payment fidelity, per-gateway journal mapping, deterministic market
    routing** (EM/SH).

## What evidence supports each observation

| Observation | Connector | Evidence (cited in deep dives / source notes) | Class |
| --- | --- | --- | --- |
| OAuth + scope check + connection test | VT | apps.odoo.com/.../integration_shopify; ecosystem | 🟨 claim |
| Test Connection button | WK | webkul.com blog (screenshots S5–S7) | ✅ demonstrated |
| Trailing-slash auth warning | EM | docs…/generate-token-direct-store-admin-app.html | ✅ demonstrated |
| Incremental import + CSV mapping fallback | EM | docs…/import-product.html, /map-product.html | ✅ demonstrated |
| Per-field directional mapping + Python transforms + test | VT | apps.odoo.com/.../integration_shopify | 🟨 claim |
| Webhook order import "within seconds" + 5-step auto-workflow | VT | apps.odoo.com/.../integration_shopify | 🟨 claim |
| Payment Gateway Workflow Matrix | SH | apps.odoo.com/.../sh_shopify_connector (V11) | ✅ demonstrated (caption) |
| Multi-payment lines | EM | docs…/import-shipped-order.html | ✅ demonstrated |
| Quantity-field choice / multi-location / BoM / multi-company inv. | VT | ecosystem release notes 2.1.2/2.1.3 | ✅ demonstrated (dated) |
| Forecast vs Free-to-Use; deterministic stock export | EM | docs…/stock-information.html, /export-stock.html | ✅ demonstrated |
| External Location mapping grid | VT | confluence pages/521732182 | ✅ demonstrated |
| Put-in-Pack multi-package; grant fulfillment scopes | EM | docs…/update-order-shipping-status.html, /grant-access-right-export-shipment.html | ✅ demonstrated |
| Fulfillment-ID write-back | SH | apps.odoo.com/.../sh_shopify_connector (V28) | ✅ demonstrated (caption) |
| State-coloured queues + Log Book | EM | docs…/queue.html, /sales-report-and-log-book.html | ✅ demonstrated |
| Traffic-light webhook health (named cause) | VT | confluence pages/521928707 | ✅ demonstrated |
| Activity chart + failure counts + re-export flag | SH | apps.odoo.com/.../sh_shopify_connector (V13, V21, V27) | ✅ demonstrated (caption) |
| Idempotency directives (2026-04); auto-retry; silent-skip fixes | VT | ecosystem release notes 2.1.4/2.1.6/1.13.0/2.1.2 | ✅ demonstrated (dated) |
| Payout reconciliation (Shopify Payments) | EM, **TQ** | EM docs…/shopify-payouts.html; **TQ .../order_management/payout_report.html** | ✅ demonstrated |
| Controlled draft-safe product export (channels-optional) + per-listing sync toggle | **TQ** | **.../product_management/product_export.html, product_update.html, shopify_faq.html** | ✅ demonstrated |
| Click&collect (Ready-for-Pickup / Picked-Up) + Force-Restock divergence warning | **TQ** | **.../order_management/update_order_status.html, order_return.html** | ✅ demonstrated |
| Honest limitation disclosure | EM, VT | EM docs (multiple); VT confluence pages/866943004 (PII) | ✅ demonstrated |
| Dated, transparent changelog | VT | ecosystem release-notes page | ✅ demonstrated |
| Access-right-gated setup | SH | apps.odoo.com/.../sh_shopify_connector (V01) | ✅ demonstrated (caption) |
| 83×5.0 reviews; install session/sandbox | TQ | apps.odoo.com/.../shopify | on-page fact / 🟨 claim |

> **Caution (claim vs demonstrated):** *(Sprint C2)* **TQ docs are now accessible**,
> so several TQ items above are **demonstrated** (draft-safe export, click&collect,
> payout reconciliation) — but its **reliability depth stays partly claim/not-found**
> (pHash 🟨; no explicit idempotency/auto-retry/reconciliation/rate-limit/HMAC — kept
> ➖/⬜, not "best"). The **83×5.0 reviews / install-session** items remain **listing
> claims**. EC contributes no "best" (no screenshots); SH "✅" rest on captions. The
> most robustly demonstrated bests come from **EM (screenshots)**, **VT (dated release
> notes)**, and **now TQ (step-by-step docs)** — weight adaptation accordingly, and
> **do not adopt TQ's asserted-but-unshown reliability claims as demonstrated**.
