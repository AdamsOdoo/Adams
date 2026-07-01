# Avoid-List (Research Sprint C)

> Things our Odoo 19 ↔ Shopify Connector should **deliberately avoid**, derived
> from competitor mistakes/friction and grounded in evidence + Tier-1 facts. Each
> item: **what to avoid · evidence/reason · risk if ignored · prevention idea ·
> needs architecture review later?** These are **recommendations/inferences, not
> rejected-approach decisions** — items that bear on design route through
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md) and
> only become formal rejections after ChatGPT review (`CLAUDE.md` §10). Access
> date 2026-06-30. Connector keys WK/TQ/EM/VT/EC/SH.

## Avoid in UX/UI

- **A-UX-1 — "Real-time" labels on a cron/queue model.** *Evidence:* WK/EC/SH say
  "real-time" but sync is cron/queue + optional webhook (verification-downgraded).
  *Risk:* broken expectations, support load, mistrust. *Prevention:* honest
  per-data-type latency labels + "last synced" timestamps. *Arch review:* no.
- **A-UX-2 — Exposing raw Odoo internals to users.** *Evidence:* WK shows cron
  fields (Model, Scheduler User, Next Execution Date). *Risk:* confusion,
  misconfiguration. *Prevention:* friendly scheduling ("every N minutes"); hide
  `ir.cron` plumbing. *Arch review:* no.
- **A-UX-3 — Toggle-dense screens with unexplained jargon.** *Evidence:* EM/SH
  config (10+ toggles), WK ("Auto-evaluate", "API Record Limit"). *Risk:* errors,
  abandonment. *Prevention:* progressive disclosure + inline help + defaults.
  *Arch review:* no.
- **A-UX-4 — Opaque/binary status with no cause.** *Evidence:* counter-pattern to
  VT's named-cause traffic-light. *Risk:* users can't self-serve fixes. *Prevention:*
  status encodes cause + fix hint. *Arch review:* no.
- **A-UX-5 — Zero-screenshot product/UX with no proof.** *Evidence:* EC listing has
  no UI screenshots. *Risk:* low trust/evaluability. *Prevention:* screenshot-rich
  docs + an open demo. *Arch review:* no.

## Avoid in configuration

- **A-CFG-1 — Blind mappings with no preview/test.** *Evidence:* most map without a
  dry-run; VT's Preview/Report + test-against-live-data is the exception. *Risk:*
  bad data pushed to Shopify (hard to reverse). *Prevention:* dry-run/preview before
  any destructive apply. *Arch review:* no.
- **A-CFG-2 — Long manual scope/credential paste with silent failure.** *Evidence:*
  EM's full-scope-string paste + trailing-slash auth failure. *Risk:* failed setup,
  support tickets. *Prevention:* OAuth-first; auto scope check; validate inline.
  *Arch review:* no.
- **A-CFG-3 — Over-configuration as the only path.** *Evidence:* EM/SH require many
  toggles. *Risk:* onboarding drop-off. *Prevention:* opinionated defaults + an
  advanced tier. *Arch review:* no.

## Avoid in sync architecture

- **A-SYNC-1 — Webhook-only OR cron-only as the sole mechanism.** *Evidence:* EC is
  cron-only (no webhooks); webhook-only would drift; **Tier-1: webhook delivery is
  NOT guaranteed → reconciliation required.** *Risk:* silent data drift / missed
  events. *Prevention:* **webhooks + scheduled reconciliation + manual sync**,
  together. *Arch review:* **YES (AR-003).**
- **A-SYNC-2 — No reconciliation / backfill path.** *Evidence:* reconciliation is
  implicit at best (EM manual import); none is first-class. Tier-1 mandates it.
  *Risk:* permanent drift from missed/duplicate webhooks. *Prevention:* a scheduled
  + on-demand reconciliation job with a visible report. *Arch review:* **YES
  (AR-003/AR-006).**
- **A-SYNC-3 — Treating `ir.cron` as a job queue.** *Evidence:* WK/EM/EC lean on
  cron/staging; **Tier-1: Odoo core has no job queue; `ir.cron` is poll-based,
  `--max-cron-threads` default 2; `queue_job` is community.** VT uses `queue_job`.
  *Risk:* throughput/latency limits, coarse failure (cron auto-deactivates after 5
  failures). *Prevention:* a real async job layer (decide the `queue_job`
  dependency consciously) + per-record retry/backoff. *Arch review:* **YES
  (AR-003).**
- **A-SYNC-4 — Heavy work inside the webhook request.** *Evidence:* Tier-1: 5s
  webhook total timeout. *Risk:* timeouts → Shopify retries → auto-delete after 8
  failures. *Prevention:* ack fast, process out-of-band (queue/cron). *Arch review:*
  **YES (AR-003).**
- **A-SYNC-5 — No Shopify rate-limit / GraphQL-cost handling.** *Evidence:* **no
  competitor describes one**; Tier-1: leaky-bucket REST + calculated-cost GraphQL +
  429/`Retry-After`. *Risk:* 429 storms, throttling, failed large syncs.
  *Prevention:* cost-aware pacing off live `throttleStatus`, backoff on 429, Bulk
  Operations for big jobs. *Arch review:* **YES (AR-002/AR-006).**
- **A-SYNC-6 — Skipping HMAC webhook verification.** *Evidence:* only VT mentions
  HMAC-SHA256; Tier-1 requires HMAC of the raw body before processing + dedupe on
  `X-Shopify-Webhook-Id`. *Risk:* spoofed/forged events; duplicate processing.
  *Prevention:* verify HMAC on raw body; dedupe on webhook id. *Arch review:* YES
  (security).

## Avoid in logs / errors

- **A-LOG-1 — Email-only error handling.** *Evidence:* EC (email notifications, no
  in-app log/queue). *Risk:* no recovery surface; lost failures. *Prevention:*
  in-app reason-coded log as source of truth; alerts are secondary. *Arch review:*
  no.
- **A-LOG-2 — Failures that don't isolate.** *Evidence:* counter to EM's per-line
  isolation. *Risk:* one bad record blocks a batch. *Prevention:* per-record
  isolation + Failed/Cancelled states. *Arch review:* no.
- **A-LOG-3 — Logs without reasons.** *Evidence:* EM's reason-coded Log Book is the
  bar. *Risk:* unactionable errors. *Prevention:* every failure carries record +
  reason + suggested fix. *Arch review:* no.

## Avoid in retry / recovery

- **A-RET-1 — Manual-only recovery.** *Evidence:* WK/EM/EC/SH recover manually;
  only VT auto-retries. *Risk:* missed syncs when no one re-runs. *Prevention:*
  automatic retry/backoff for transient/idempotent-safe ops + a clear manual
  override. *Arch review:* YES (AR-006).
- **A-RET-2 — Irreversible "Force Done"-style actions without strong guards.**
  *Evidence:* EM "Force Done" cancels remaining lines irreversibly. *Risk:*
  accidental data loss / stuck queues. *Prevention:* strong confirmation,
  reversibility where possible, clear warnings. *Arch review:* no.
- **A-RET-3 — Naive retry that double-acts.** *Evidence:* Tier-1: `@idempotent`
  required (2026-04) precisely to prevent double refunds/inventory on retry. *Risk:*
  duplicate refunds/inventory changes. *Prevention:* idempotency keys on all
  writes. *Arch review:* **YES (AR-006).**

## Avoid in inventory

- **A-INV-1 — Manual post-import stock processing.** *Evidence:* EM Import Stock
  creates an Inventory Adjustment the user must process manually. *Risk:* stale
  stock, oversell. *Prevention:* auto-apply imported stock (optionally with review).
  *Arch review:* no.
- **A-INV-2 — Single-location-only inventory.** *Evidence:* WK has one default
  warehouse/location. *Risk:* wrong stock for multi-warehouse merchants;
  **double-decrement of multi-location SKUs** (quality-feedback-loop §5).
  *Prevention:* per-location mapping; write per `inventory_item_id`+`location_id`
  (Tier-1). *Arch review:* **YES (AR-007).**
- **A-INV-3 — Writing the `committed` quantity.** *Evidence:* Tier-1: `committed`
  is API-read-only (order-driven). *Risk:* API errors / wrong availability.
  *Prevention:* write `available`/`on_hand` only; let orders drive `committed`.
  *Arch review:* YES (AR-007).

## Avoid in fulfillment

- **A-FUL-1 — Legacy order-based fulfillment endpoints.** *Evidence:* Tier-1: legacy
  Order/Fulfillment workflow unsupported since 2022-07; use FulfillmentOrder.
  *Risk:* broken fulfillment on current API. *Prevention:* FulfillmentOrder-based
  mutations. *Arch review:* **YES (AR-008).**
- **A-FUL-2 — Ignoring multi-location/multi-package fulfillment.** *Evidence:* EM
  Put-in-Pack multi-package; VT per-warehouse transfers; Tier-1: one fulfillment per
  order+location. *Risk:* incorrect fulfillments for split orders. *Prevention:*
  per-location/per-package fulfillments. *Arch review:* YES (AR-008).
- **A-FUL-3 — Missing/incorrect Shopify fulfillment scopes.** *Evidence:* EM
  documents granting assigned/merchant-managed/third-party fulfillment scopes.
  *Risk:* fulfillment export fails. *Prevention:* request + verify the right scopes.
  *Arch review:* no.

## Avoid in payments / payouts / refunds

- **A-PAY-1 — Assuming payout data exists for all gateways.** *Evidence:* EM payouts
  "Shopify Payments only"; Tier-1: payouts/balance/disputes are Shopify-Payments
  only. *Risk:* broken reconciliation for non-Shopify-Payments stores. *Prevention:*
  use `OrderTransaction` as the cross-gateway ledger; gate payout features to
  Shopify Payments. *Arch review:* YES.
- **A-PAY-2 — Non-idempotent refunds.** *Evidence:* Tier-1: `refundCreate` requires
  `@idempotent` from 2026-04; VT added refund idempotency. *Risk:* double refunds.
  *Prevention:* idempotency keys on refunds. *Arch review:* **YES (AR-006).**
- **A-PAY-3 — Conflating payment status with money movement.** *Evidence:* Tier-1:
  the Refund exists independently of money; status is on its transactions. *Risk:*
  wrong financial state in Odoo. *Prevention:* model transactions explicitly.
  *Arch review:* YES.

## Avoid in documentation / support

- **A-DOC-1 — Bot-blocking or sign-in-gating evaluation docs.** *Evidence:* TQ docs
  403; EC setup guide behind a Google sign-in (R5). *Risk:* buyers can't evaluate;
  lost trust/sales. *Prevention:* public, crawlable, screenshot-rich docs + open
  demo. *Arch review:* no.
- **A-DOC-2 — No (or stale) changelog.** *Evidence:* SH has none; EM's v19 changelog
  is stale (to Apr 2024). *Risk:* users can't tell currency/maintenance. *Prevention:*
  a dated changelog that discloses fixes (VT-style). *Arch review:* no.
- **A-DOC-3 — Publishing stale platform figures.** *Evidence:* EM docs cite Shopify
  "19 retries/48h" (outdated; Tier-1: 8/4h). *Risk:* wrong guidance; mirrors our own
  DP-001. *Prevention:* cite current official Shopify limits; re-verify on each
  release. *Arch review:* no.
- **A-DOC-4 — Ambiguous provenance.** *Evidence:* EC "Odoo IN Pvt Ltd" — official vs
  partner unclear. *Risk:* buyer confusion. *Prevention:* state authorship/partner
  status clearly. *Arch review:* no.

## Avoid in modular architecture

- **A-MOD-1 — One giant connector module.** *Evidence:* `CLAUDE.md` §9 +
  AR-004; VT decomposes (queue / core / connector). *Risk:* poor isolation, hard
  maintenance, coupling to `adams_base`/customer code. *Prevention:* a layered addon
  family with link modules; isolate from `adams_base`. *Arch review:* **YES
  (AR-004).**
- **A-MOD-2 — Over-fragmentation.** *Evidence:* balance vs A-MOD-1. *Risk:*
  dependency-coupling overhead. *Prevention:* boundaries validated in RB-14, not
  pre-decided. *Arch review:* **YES (AR-004).**
- **A-MOD-3 — Assuming `queue_job` is core / an unmanaged hard dependency.**
  *Evidence:* VT requires manual `odoo.conf`/`queue_job` setup; Tier-1: `queue_job`
  is community, not core. *Risk:* install friction; non-core dependency surprises.
  *Prevention:* if adopted, make it turnkey; decide the dependency consciously.
  *Arch review:* **YES (AR-003/AR-004).**
- **A-MOD-4 — `_inherits` delegation for model extension.** *Evidence:* Tier-1: Odoo
  docs warn "avoid it if you can"; prefer in-place `_inherit`. *Risk:* instability.
  *Prevention:* in-place `_inherit` (no new `_name`); `@api.model_create_multi`;
  `@api.ondelete`; always `super()`. *Arch review:* YES (AR-004).

## Avoid in implementation (for when the gate opens)

- **A-IMP-1 — `productSet`-style delete-on-omit treated as a partial update.**
  *Evidence:* Tier-1 data-loss footgun (omitted list entries are deleted). *Risk:*
  destroying variants/collections/metafields. *Prevention:* full-state awareness;
  never send partial lists to `productSet`. *Arch review:* YES.
- **A-IMP-2 — Skipping idempotency keys / binding-key uniqueness.** *Evidence:*
  quality-feedback-loop §5; Tier-1 `@idempotent`. *Risk:* duplicate records /
  double-decrement. *Prevention:* binding-table uniqueness + idempotency keys +
  multi-location regression tests. *Arch review:* YES (AR-005/AR-006).
- **A-IMP-3 — Long syncs in an HTTP request; assuming crons run on Odoo.sh
  staging.** *Evidence:* Tier-1: worker time/memory limits; crons disabled on
  Odoo.sh staging/dev. *Risk:* killed workers; "broken in staging" confusion.
  *Prevention:* chunked queue/cron sync; manual triggers for non-prod tests.
  *Arch review:* YES (AR-003).
- **A-IMP-4 — Shipping without tests for the classic defects.** *Evidence:* VT's
  disclosed silent-skip/timezone bugs; `CLAUDE.md` §9 test requirements. *Risk:*
  duplicate orders, double-decrement, missed reconciliation, timezone/paging bugs.
  *Prevention:* mandatory regression tests (mapping unit, webhook/UI tours,
  multi-location, reconciliation, timezone). *Arch review:* no (gate at DoD).
- **A-IMP-5 — Bypassing ORM access controls with `sudo()`/raw SQL casually.**
  *Evidence:* Tier-1: `sudo()` bypasses access rights + record rules. *Risk:*
  security/permission holes. *Prevention:* `sudo()` only as a deliberate, audited
  bypass; explicit `ir.model.access.csv` + groups + record rules. *Arch review:*
  YES (security).

---

## Routing note (governance)

These are **competitor anti-patterns to avoid (recommendations/inferences)**, not
yet **rejected-approach decisions**. Items marked **"Arch review: YES"** are
seeded against the relevant **AR-002…AR-008** rows (all *evidence-pending, not
decided*) in
[`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md);
they become formal entries in
[`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)
**only after ChatGPT/architecture review** (`CLAUDE.md` §10, RB-14). No rejection
decision is made in this sprint.
