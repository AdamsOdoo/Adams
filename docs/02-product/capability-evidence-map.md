# Capability Evidence Map

> Compact traceability companion to
> [`feature-taxonomy.md`](./feature-taxonomy.md). One row per canonical
> capability, mapping it to its **evidence strength**, **strongest evidence**,
> **per-competitor coverage**, **official-platform dependency**, **architecture-
> review need**, and **MVP-review relevance**. Use it to answer "how well do we
> actually know this?" at a glance, and to route capabilities to the right gated
> review.

## Status

- **Sprint:** Research/Product Sprint D (RB-12). **Phase:** research/synthesis
  only — **no-code gate in force** (`CLAUDE.md` §4–§5). Decides nothing.
- **Evidence access date:** 2026-06-30 (Sprint C). **Session date:** 2026-07-01.
- **Discipline (DP-003/DP-004):** competitor claims ≠ facts; a configuration field
  ≠ demonstrated support; a market promise ≠ demonstrated bidirectionality; `✅`
  requires a demonstrated workflow/screenshot/dated release note/explicit doc.

## Purpose

Provide a **traceable, at-a-glance** index so later sprints (RB-13 MVP, RB-14
architecture) can weight each capability by **how strong its evidence is** and
**which platform/architecture constraints it carries** — without re-reading the
full taxonomy. This is an **input map**, not a scope or a decision.

## How to read this map

- **Capability ID / name / domain:** the canonical unit from the taxonomy.
- **Evidence strength (A–E):** the single strongest evidence class supporting the
  capability (see legend). Where a capability is both platform-required (A) and
  strongly demonstrated (B), **A wins** (platform authority outranks a vendor demo).
- **Strongest evidence:** the most authoritative source/actor.
- **Competitor coverage:** per-connector symbol (**WK TQ EM VT EC SH**). Omitted
  connectors are ⬜ (not found) unless stated. Symbols: **✅** demonstrated · **🟨**
  claim only · **⬜** not found · **🚫** explicitly absent · **🔒** blocked/unknown ·
  **➖** implied-only / config-field-only (not demonstrated — DP-004).
- **Official platform dependency:** Yes (+ topic) if a Shopify/Odoo fact makes it
  necessary/mandatory; else No.
- **Architecture review:** the AR row(s) it depends on (all **evidence-pending /
  not decided**), or No.
- **MVP review relevance:** `candidate` / `later` / `unknown` — an **input** for
  RB-13, never a decision.

> **Grouping over granularity.** Rows are the taxonomy's normalized capabilities
> (≈90), grouped by domain — not every tiny sub-toggle. This keeps traceability
> useful and readable (per the sprint's "no huge unreadable table" rule).

## Evidence strength legend

| Strength | Meaning | Typical basis |
| --- | --- | --- |
| **A** | Official platform requirement | Tier-1 Shopify/Odoo docs make it necessary/mandatory. |
| **B** | Demonstrated by strong competitor evidence | EM screenshots and/or VT dated release notes (or ≥2 demonstrated). |
| **C** | Multiple competitor claims / weak or partial demonstrations | Mixed 🟨 + partial ✅, or a synthesis no single competitor fully demonstrates. |
| **D** | Single competitor claim only | One vendor states it, not demonstrated. |
| **E** | Open question / blocked / whitespace | No competitor evidence; inference or blocked source only. |

**Competitor keys:** WK Webkul (R1) · TQ Teqstars (R2, docs 403 → claims only) ·
EM Emipro (R3, strong) · VT VentorTech (R4+R7, strong/dated) · EC ecommerce_shopify
(R6, no screenshots → weak) · SH sh_shopify_connector (R8, captions; no
ratings/changelog).

## Capability map

### Domain 1 — Store connection, authentication, and setup

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-CONN-01 | OAuth-first store connection | 1 | A | Shopify auth model + VT | VT✅ EM✅ WK✅ SH✅ TQ🟨 EC🟨 | Yes (OAuth/token) | AR-002 | candidate | Token-paste is the demonstrated default; OAuth-first is VT + App-Store req. |
| C-CONN-02 | Credential storage & masking | 1 | B | VT v2.1.3 | VT✅ TQ🟨 | No | No | candidate | Cheap, high-trust; pair with role-gating. |
| C-CONN-03 | Guided setup wizard | 1 | B | WK/EM screenshots | WK✅ EM✅ VT🟨 TQ🟨 EC🔒 | No | No | candidate | EC guide is the blocked Google Doc (R5) — anti-pattern. |
| C-CONN-04 | Test connection (pass/fail) | 1 | B | WK screenshots | WK✅ SH✅ VT🟨 EM➖ EC⬜ | No | No | candidate | Cheap high-value guardrail. |
| C-CONN-05 | Scope / readiness pre-flight check | 1 | C | VT scope-check + EM gotcha + inference | VT🟨 EM✅ (partial) | Yes (scopes/PII approval) | AR-003 | candidate | No competitor does a full readiness check — partial whitespace. |
| C-CONN-06 | Reconnect / re-authorise / disconnect | 1 | B | VT store-URL fix (dated) | VT✅ | No | No | candidate | Store-URL migration is a real evidenced failure mode. |

### Domain 2 — Dashboard, health, and command center

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-DASH-01 | Unified command center | 2 | C | Synthesis of SH + VT | SH✅ EM✅ TQ🟨 VT⬜ EC⬜ | No | AR-003 (light) | candidate | No competitor fuses monitoring + diagnostics — differentiator. |
| C-DASH-02 | Health indicators (traffic-light) | 2 | B | VT Confluence | VT✅ SH✅ | No | No | candidate | VT's is the best status-indicator pattern. |
| C-DASH-03 | Activity timeline / queue / failure counts | 2 | B | SH activity chart | SH✅ EM✅ VT➖ EC⬜ | No | AR-003 (light) | candidate | SH daily activity chart = best monitoring visual. |
| C-DASH-04 | Named-cause diagnostics + fix hints | 2 | B | VT yellow-status | VT✅ | No | No | candidate | Needs a named-cause taxonomy (open Q). |
| C-DASH-05 | Quick actions | 2 | B | EM/SH/VT | EM✅ SH✅ VT✅ WK✅ | No | AR-003 (light) | candidate | Must enqueue, not run heavy work inline. |
| C-DASH-06 | Empty states / first-run guidance | 2 | E | Inference (no competitor evidence) | ⬜ all | No | No | candidate | UX best-practice; classified by inference only. |

### Domain 3 — Product catalog sync

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-PROD-01 | Product import | 3 | B | EM/VT/SH screenshots | EM✅ VT✅ WK✅ SH✅ TQ🟨 EC🟨 | Yes (API) | AR-002, AR-005 | candidate | Incremental/filterable; idempotent upsert. |
| C-PROD-02 | Product export (draft-first) | 3 | B | VT draft-export | VT✅ EM✅ SH✅ WK✅ TQ🟨 EC⬜ | Yes (`productSet`) | AR-002, AR-005 | candidate | **EC export not found** — DP-004 example. |
| C-PROD-03 | Publish / unpublish & channel control | 3 | B | EM/SH | EM✅ SH✅ VT✅ WK⬜ EC⬜ | No | No | candidate | Ties to POS + sell-OOS. |
| C-PROD-04 | Exclude-from-sync | 3 | B | SH/EM | SH✅ EM✅ | No | No | candidate | EM logs exclusion reason. |
| C-PROD-05 | Draft/preview before destructive apply | 3 | A | `productSet` delete-on-omit + VT dry-run | VT✅ | Yes (`productSet`) | AR-002 | candidate | Data-loss prevention (A-IMP-1). |

### Domain 4 — Variants, options, images, and media

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-VAR-01 | Variant/option sync (2,048 model) | 4 | A | Shopify 2,048 model + EM/VT | EM✅ VT✅ TQ🟨 EC🟨 SH🟨 WK⬜ | Yes (product model) | AR-002 | candidate | VT fixed a 250-cap (v2.1.4). |
| C-VAR-02 | Image / media sync | 4 | B | EM/VT | EM✅ VT✅ TQ🟨 SH🟨 WK⬜ | No | No | candidate | pHash dedup (TQ) is claim-only. |
| C-VAR-03 | SEO / standard product taxonomy | 4 | B | VT (dated) | VT✅ | No | No | later | Only VT demonstrates. |
| C-VAR-04 | BoM / kit stock handling | 4 | B | VT (dated) | VT✅ | No | AR-007 | later | Manufacturing-aware; niche. |

### Domain 5 — Pricing, pricelists, compare-at, markets pricing

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-PRICE-01 | Price & compare-at sync | 5 | B | EM compare-at + VT | EM✅ VT✅ WK🟨 TQ🟨 EC⬜ SH⬜ | No | No | candidate | EC/SH did not show pricing. |
| C-PRICE-02 | Pricelist mapping | 5 | B | EM/VT | EM✅ VT✅ WK🟨 TQ🟨 | No | No (light) | candidate | Per-market → Markets (AR review). |
| C-PRICE-03 | Per-market (Catalogs) pricing + dry-run | 5 | B | VT Preview/Report | VT✅ EM✅ | No | AR review (Markets) | later | Dry-run is the reusable pattern. |

### Domain 6 — Inventory, stock quantities, and locations

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-INV-01 | Stock quantity sync | 6 | A | Shopify (`committed` read-only, `@idempotent`) + EM/VT | EM✅ VT✅ WK✅ SH✅ TQ🟨 EC🟨 | Yes (inventory model) | AR-007 | candidate | Write `available`/`on_hand` only; idempotent. |
| C-INV-02 | Quantity-field / source-quantity choice | 6 | B | EM formulas | EM✅ VT✅ WK✅ | No | AR-007 | candidate | Jargon needs inline help. |
| C-INV-03 | Multi-location inventory mapping | 6 | A | Shopify InventoryLevel + EM/VT | EM✅ VT✅ TQ🟨 EC🟨 SH🟨 WK⬜ | Yes (per-location) | AR-007 | candidate | SKU-only writes double-decrement (A-INV-2). WK single-location. |
| C-INV-04 | Import stock (auto-applied) | 6 | B | EM (manual — improve on) | EM✅ VT✅ SH✅ WK✅ | No | AR-007 | candidate | Auto-apply vs EM's manual adjustment. |

### Domain 7 — Customers, companies, and addresses

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-CUST-01 | Customer import | 7 | B | EM/VT/SH + Shopify PII rules | EM✅ VT✅ SH✅ WK🟨 EC🟨 | Yes (protected data) | No (light) | candidate | Handle no-PII plans (VT default-customer). |
| C-CUST-02 | Customer export (email dedup, link) | 7 | B | EM link-by-email | EM✅ SH✅ VT➖ WK⬜ EC⬜ | No | AR-005 | candidate | WK/EC import-only — DP-004. |
| C-CUST-03 | Multi-key matching (email/name/phone) | 7 | B | VT normalized matching | VT✅ EM✅ WK🟨 TQ🟨 EC🟨 SH🟨 | No | AR-005 | candidate | VT strongest matcher. |
| C-CUST-04 | Address & company mapping | 7 | C | EM/VT partial; mostly implied | EM✅ VT✅ others➖ | No | No (light) | candidate/later | Deep multi-address under-demonstrated. |

### Domain 8 — Orders and order lifecycle

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-ORD-01 | Order import (webhook + backfill + manual) | 8 | A | Shopify (reconcile) + VT/EM/SH | VT✅ EM✅ SH✅ WK✅ TQ🟨 EC🟨 | Yes | AR-003 | candidate | Webhook-only/cron-only both anti-patterns (A-SYNC-1). |
| C-ORD-02 | Historical / backfill import (60-day gate) | 8 | A | Shopify 60-day + EM/VT | EM✅ VT✅ EC🟨 WK✅ | Yes (`read_all_orders`) | AR-002 | candidate | Approval gate is real. |
| C-ORD-03 | Order / financial / fulfillment status mapping | 8 | B | SH matrix + VT | SH✅ VT✅ EM🟨 TQ🟨 EC🟨 | No | No (light) | candidate | Feeds the auto-workflow. |
| C-ORD-04 | Configurable order auto-workflow | 8 | B | VT pipeline + SH | VT✅ SH✅ EM🟨 TQ🟨 EC🟨 | No | AR-003 | candidate | Each step a retryable idempotent job. |
| C-ORD-05 | Order fraud / risk import | 8 | B | VT | VT✅ TQ🟨 | No | No | later | Demonstrated only by VT. |

### Domain 9 — Invoices, payments, gateways, and journals

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-PAY-01 | Invoice creation from orders | 9 | B | VT/SH | VT✅ SH✅ EM🟨 TQ🟨 EC🟨 | No | No (light) | candidate | Idempotent (no double-invoice on retry). |
| C-PAY-02 | Payment representation (multi-payment) | 9 | B | EM multi-payment lines | EM✅ VT✅ SH✅ TQ🟨 | No | No | candidate | Currency conversion / transaction-date (VT). |
| C-PAY-03 | Payment-gateway → journal mapping | 9 | B | SH matrix + VT | SH✅ VT✅ TQ🟨 EM🟨 | Yes (`OrderTransaction`) | No | candidate | `OrderTransaction` = cross-gateway ledger. |

### Domain 10 — Fulfillment, delivery, tracking, and shipment status

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-FUL-01 | Fulfillment (FulfillmentOrder) + tracking write-back | 10 | A | Shopify FulfillmentOrder + EM/VT/SH | EM✅ VT✅ SH✅ TQ🟨 EC🟨 WK🚫 | Yes | AR-008 | candidate | Legacy order-based endpoints = anti-pattern (A-FUL-1). WK: shipping-method import n/a. |
| C-FUL-02 | Multi-package / multi-location fulfillment | 10 | B | EM Put-in-Pack + VT | EM✅ VT✅ SH✅ | Yes | AR-008 | candidate | One fulfillment per order+location. |
| C-FUL-03 | Fulfillment scope granting / verification | 10 | A | Shopify scopes + EM walkthrough | EM✅ others➖ | Yes | No | candidate | Missing scope = silent failure. |

### Domain 11 — Refunds, returns, cancellations, and restocking

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-RET-01 | Refund sync (idempotent) | 11 | A | Shopify `@idempotent` (2026-04) + VT | EM✅ VT✅ SH✅ EC🟨 | Yes | AR-006 | candidate | Non-idempotent refunds double-refund (A-PAY-2). |
| C-RET-02 | Returns lifecycle (request→approve→process) | 11 | A | Shopify returns API + EM | EM✅ SH✅ VT✅ EC🟨 | Yes | AR-006, AR-008 | later | `returnRefund` deprecated → `returnProcess`. Distinct RMA is scarce. |
| C-RET-03 | Order cancellation (restock/notify) | 11 | B | VT two-step + EM | VT✅ EM✅ SH✅ WK🟨 | No | No | candidate | Irreversible-action warning (VT); EM never silently creates cancel order. |

### Domain 12 — Payouts and reconciliation

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-POUT-01 | Payout import (Shopify Payments) | 12 | A | Shopify (SP-only) + EM | EM✅ TQ🟨 | Yes (SP-only) | AR review | later | Gate to Shopify-Payments stores (A-PAY-1). |
| C-POUT-02 | Bank-statement generation & reconciliation | 12 | B | EM (only demo) | EM✅ | No | AR review | later | Rare whitespace; premium add-on. |

### Domain 13 — Webhooks, scheduled sync, manual sync, and reconciliation

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-SYNC-01 | Webhook subscription management | 13 | A | Shopify webhooks + VT/EM/SH | VT✅ EM✅ SH✅ TQ🟨 EC🚫 WK⬜ | Yes | AR-003 | candidate | Admin-API subs self-delete after 8 fails. EC cron-only. |
| C-SYNC-02 | Webhook HMAC verification (raw body) | 13 | A | Shopify (HMAC before processing) | VT🟨 others⬜ | Yes (security) | AR / security | candidate | Under-addressed across field; mandatory. |
| C-SYNC-03 | Webhook ID dedup + fast acknowledgement | 13 | A | Shopify (5s, dedupe on webhook-id) | VT✅ (partial) others⬜ | Yes | AR-003 | candidate | No competitor documents webhook-id dedup — whitespace. |
| C-SYNC-04 | Scheduled sync | 13 | B | EM per-process scheduler | EM✅ VT✅ SH✅ WK✅ EC✅ | No | AR-003 | candidate | Hide `ir.cron` internals (A-UX-2); off on Odoo.sh staging. |
| C-SYNC-05 | Manual / on-demand sync | 13 | B | Universal (WK/EM/VT/SH) | WK✅ EM✅ VT✅ SH✅ TQ🟨 EC🟨 | No | No (light) | candidate | Also the Odoo.sh-staging test path. |
| C-SYNC-06 | Scheduled + manual reconciliation (first-class) | 13 | A | Shopify (delivery not guaranteed) + EM partial | EM✅ (partial); none full | Yes | AR-003, AR-006 | candidate | The clearest correctness whitespace (O-REL-1). |
| C-SYNC-07 | Sync freshness indicators (last synced/reconciled) | 13 | E | Inference + latency-honesty | ⬜ all (WK/EC/SH overstate "real-time") | No | No | candidate | Honesty-as-a-feature; cheap, high-trust. |

### Domain 14 — Queue, jobs, retries, and recovery

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-JOB-01 | Async job / queue with per-record isolation | 14 | B | VT `queue_job` + EM queues | VT✅ EM✅ SH✅ WK✅ EC⬜ | No (Odoo has no core queue) | AR-003 | candidate | Queue framework = AR-003; `queue_job` non-core (A-MOD-3). |
| C-JOB-02 | Retry classification (auto-safe vs manual) | 14 | C | VT partial + inference | VT✅ others manual | No | AR-006 | candidate | Needs error taxonomy (open Q). |
| C-JOB-03 | Automatic retry with backoff (safe ops) | 14 | B | VT (only) | VT✅ EM/SH/WK/EC manual🟨 | No | AR-006 | candidate | Naive retry double-acts → needs idempotency. |
| C-JOB-04 | Idempotency key management | 14 | A | Shopify `@idempotent` (2026-04) + VT | VT✅ TQ🟨 others⬜ | Yes | AR-006 | candidate | Mandatory for inventory set/adjust + refunds. |
| C-JOB-05 | Rate-limit / GraphQL-cost-aware throttling | 14 | A | Shopify limits; **no competitor** | none (VT🟨 "avoid unnecessary") | Yes | AR-002, AR-006 | candidate | Biggest reliability whitespace (O-REL-2). |
| C-JOB-06 | Bulk operation handling | 14 | A | Shopify Bulk Ops; none describe it | none (EM batches partial) | Yes | AR-002 | later | Concurrency changed 2026-01. |
| C-JOB-07 | Resumable / restartable jobs | 14 | A | Odoo cron batching + VT restartable | VT✅ EM✅ SH✅ | Yes (Odoo limits) | AR-003 | candidate | Long syncs must not run in one HTTP request. |

### Domain 15 — Logs, errors, audit trail, and observability

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-OBS-01 | Reason-coded, in-app logs | 15 | B | EM Log Book / Mismatch Log | EM✅ SH✅ VT✅ WK✅ EC⬜ | No | No (light) | candidate | EC email-only is the floor (A-LOG-1). |
| C-OBS-02 | Audit trail of sync actions | 15 | B | VT "every action logged" | VT✅ SH✅ EM✅ WK✅ EC🟨 | No | No (light) | candidate | Retention policy. |
| C-OBS-03 | Recovery-first error center | 15 | C | Synthesis (EM+VT+SH, unified by none) | EM✅ VT✅ SH✅ (unified⬜) | No | AR-006 | candidate | Core operator-UX differentiator (O-PREM-2). |
| C-OBS-04 | Failed-job notifications to users | 15 | B | VT Failed Job Notifications | VT✅ EC🟨(email-only) | No | No | candidate | Alerts complement, don't replace, in-app log. |

### Domain 16 — Mapping, matching, and duplicate prevention

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-MAP-01 | External-ID / Shopify-GID binding model | 16 | A | Odoo `ir.model.data` + Shopify GID + EM/SH/VT | EM✅ SH✅ VT✅ others🟨 | Yes (GID/ID formats) | AR-005 | candidate | Deleted-binding handling undocumented across field. |
| C-MAP-02 | Duplicate prevention (documented keys) | 16 | B | EM/VT keys | EM✅ VT✅ others🟨 | No | AR-005 | candidate | Keys mostly implicit — document them. |
| C-MAP-03 | Directional, testable field mapping + dry-run | 16 | B | VT (direction+transforms+test) | VT✅ EM✅ SH✅ TQ🟨 | No | AR-004, AR-005 | candidate/later | Custom Python transforms = advanced. |
| C-MAP-04 | Deterministic routing (gateway/location/market) | 16 | B | EM country→currency→fallback | EM✅ SH✅ VT✅ | No | No (light) | candidate | Clean deterministic fallback pattern. |

### Domain 17 — Multi-store, multi-company, and permissions

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-MULTI-01 | Multi-store + per-store config isolation | 17 | B | VT ("as many stores…") | VT✅ SH🟨 TQ🟨 WK➖ EC⬜ | No | AR-004, AR-005 | candidate | MVP may start single-store (RB-13). |
| C-MULTI-02 | Multi-company isolation (record rules) | 17 | B | EM/VT + Odoo record rules | EM✅ VT✅ WK➖(DP-004) SH⬜ | Yes (record rules) | AR-004, security | later | WK default-Company field ≠ support (DP-004). |
| C-MULTI-03 | Role-based access (admin vs functional) | 17 | A | Odoo security + EM/SH | EM✅ SH✅ VT➖ | Yes | security | candidate | SH gates setup behind an access right. |
| C-MULTI-04 | Domain-isolated / per-store config model | 17 | C | VT tabbed config + inference | VT✅ EM/SH partial | No | AR-004 | candidate | Architecture input; **no final module names**. |

### Domain 18 — Shopify Markets, B2B, POS, gift cards, metafields, advanced

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-ADV-01 | Shopify Markets & Catalogs | 18 | B | EM/VT | EM✅ VT✅ TQ🟨 | No | AR review | later | Premium differentiator, not baseline. |
| C-ADV-02 | B2B (company accounts, VAT/VIES) | 18 | B | VT (only) | VT✅ TQ🟨 | No | No | later | Whitespace — only VT. |
| C-ADV-03 | POS order import | 18 | C | VT (Closed-status) + claims | VT✅ EM🟨 TQ🟨 | No | No | later | Partly demonstrated (VT). |
| C-ADV-04 | Gift cards | 18 | B | SH (only) | SH✅ EM🟨 TQ🟨 | No | No | later | Optional add-on; SH only. |
| C-ADV-05 | Metafields (directional, per-entity) | 18 | B | EM/VT/SH | EM✅ VT✅ SH✅ TQ🟨 | No | AR-004, AR-005 | later | Well-demonstrated; still advanced. |
| C-ADV-06 | Extended breadth (abandoned→CRM, recs, Buy-with-Prime) | 18 | B | SH (only) | SH✅ | No | No | later | Optional add-ons; SH-only evidence. |

### Domain 19 — Reporting, analytics, and operational insights

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-RPT-01 | Operational sync analytics | 19 | B | SH activity chart + EM graph | SH✅ EM✅ TQ🟨 | No | No | candidate/later | Overlaps command center. |
| C-RPT-02 | Financial / sales reporting | 19 | B | EM (analytic-per-channel, Net-Profit) | EM✅ SH✅ TQ🟨 | No | No | later | Net-Profit Enterprise-only (disclose). |

### Domain 20 — Documentation, support, demo, and maintenance transparency

| Capability ID | Capability name | Domain | Evidence strength | Strongest evidence | Competitor coverage | Official platform dependency | Architecture review needed | MVP review relevance | Notes |
| --- | --- | :--: | :--: | --- | --- | --- | --- | :--: | --- |
| C-DOCS-01 | Readable, screenshot-rich, non-gated docs | 20 | B | EM honest docs + VT KB | EM✅ VT✅ SH✅(captions) TQ🔒 EC🚫 | No | No | candidate | EC gated + TQ 403 = anti-patterns. |
| C-DOCS-02 | Dated, honest changelog | 20 | B | VT dated release notes | VT✅ EC✅ EM(stale) SH⬜ TQ🔒 | No | No | candidate | Cite current platform figures (A-DOC-3/DP-001). |
| C-DOCS-03 | Support, public demo, self-test | 20 | C | WK/EM support + TQ demo claim | WK✅ EM✅ VT✅ TQ🟨 EC🔒 | No | No | candidate/later | Built-in self-test ties to C-CONN-05. |
| C-DOCS-04 | App-Store / Built-for-Shopify readiness | 20 | A | Shopify App-Store reqs | none verified | Yes | AR-002 | unknown | Depends on distribution decision (open). |

---

## Roll-up (inputs, not decisions)

- **A (official platform requirement):** ~22 capabilities — the non-negotiable
  correctness/compliance spine (OAuth, HMAC, webhook dedup/ack, reconciliation,
  idempotency, rate-limit/bulk awareness, inventory model, FulfillmentOrder,
  refund idempotency, 60-day gate, GID binding, record-rule security, App-Store).
- **B (strong competitor demonstration):** ~45 capabilities — the demonstrated
  market baseline + several premium bests (EM/VT-led).
- **C (mixed/partial):** ~8 — syntheses no single competitor fully demonstrates
  (command center, error center, retry classification, readiness check, POS,
  address mapping, per-store config, support/demo).
- **E (whitespace / inference-only):** ~2 — freshness indicators, empty states
  (plus the many A-strength whitespaces where the *platform* requires it but **no
  competitor demonstrates** it — flagged in the Notes: reconciliation surface,
  rate-limit throttling, webhook-id dedup, bulk ops).
- **Architecture-review-bearing:** every AR-002…AR-008 row has ≥3 dependent
  capabilities; **all remain "Not decided / Evidence pending"** — see
  [`feature-taxonomy.md`](./feature-taxonomy.md) "Capabilities requiring
  architecture review" and
  [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).

> **This map decides nothing.** Evidence strength, competitor coverage, MVP
> relevance, and AR mapping are **inputs** for the gated RB-13 (MVP) and RB-14
> (architecture) reviews (`CLAUDE.md` §4–§5, §8–§10).
