# Area 6 — Manual & Scheduled Sync Triggers: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §7 is NOT usable.** Produced 2026-07-10 (AR-042 candidate).
> Closes OP-28 at proposal level. Evidence: ARCH §5.5 (PD-5
> checkpoints), §7 (enqueue seam); merged core code. **Scope revision
> to the original Area-6 concept (flagged decision D-A6-1):** the Full
> modules (Tasks 013/014/015) ship their own triggers natively inside
> their packets; Area 6 is therefore the **retrofit task for the Lite
> trio** — enumeration/scan services, crons, manual service call
> sites, and the operator job-control services — for
> product/customer/order import. This makes the merged backend
> operator-invokable without waiting for (or requiring) any UI.

## 1. Objective, scope, non-goals

One implementation task ("Task 016 — sync triggers", working number)
touching `shopify_connector_product` and `shopify_connector_sale`
(+ their cron data files): scheduled incremental scans, manual sync
services, retry/cancel job services, duplicate-enqueue prevention.
**Non-goals:** no UI (services are called from shell/server actions
until the UI phase wires buttons to them); no webhooks; no full-sync/
backfill beyond the 60-day order window; no changes to import
mapping/matching logic of any kind; no core edits (the enqueue seam
and job model already provide everything — verified against merged
code).

## 2. Design (D-A6-1 … D-A6-6) — each Proposed

**D-A6-1 — Split (above).** Area 6 = Lite-trio retrofit; Full modules
own their triggers. The sequence document's Area-6 description is
superseded by this packet on acceptance (register note).

**D-A6-2 — Scan jobs (enumeration).** Per domain, a scan job type
(`product_import_scan`, `customer_import_scan`, `order_import_scan`)
whose handler enumerates changed remote objects and enqueues
single-entity import jobs (the merged `order_import_sync` /
`customer_import_sync` / `product_import_sync` handlers — untouched).
Enumeration posture per ARCH PD-5 (pinned in Tasks 010/011/012
packets): `products/customers/orders(first: 100, sortKey: UPDATED_AT,
query: "updated_at:>{checkpoint − overlap}")`, cursors in-run only,
overlap constant 10 min; per-domain checkpoint fields on store
settings (`product_last_import_checkpoint_at`,
`customer_last_import_checkpoint_at`, the Task-012-created
`sale_order_last_import_checkpoint_at`), advanced only after the scan
page's enqueues are committed. Scan jobs target the store
(`res_model='shopify.connector.store'`, `res_id=store`) so
`operation_scope_key` serializes **one active scan per domain per
store** — the overlap-prevention mechanism (a second scan while one
is non-terminal collides and is not created). Enqueue-side duplicate
prevention for entity jobs is the existing `idempotency_key`
(payload_hash = remote `updatedAt`): an unchanged object re-enqueued
collides silently → skipped (logged at scan level as a count, not per
item).

**D-A6-3 — Crons.** One `ir.cron` per domain scan (product/customer/
order), interval 15 min (adjustable, noupdate=1), each iterating
connected stores where the domain flag AND the new per-domain
`<domain>_scheduled_sync_enabled` settings Boolean (default False —
scheduling is opt-in per store) are set, enqueueing one scan job per
eligible store (collision-safe per D-A6-2). Cron handlers only
enqueue — never execute imports inline (accepted enqueue-never-inline
rule); they never raise (ir.cron auto-deactivates after 5 failures/7
days — captures §8 — so handlers catch-log-continue per store).
Maintenance window = disabling the store's scheduled flags or the
domain flags; no separate window mechanism in MVP.

**D-A6-4 — Manual sync services (operator+, backend).** On the store:
`action_sync_products_now()`, `action_sync_customers_now()`,
`action_sync_orders_now()` (enqueue a scan with
`job_source='manual_sync'`); selected-record sync:
`action_sync_selected()` on each binding model (re-enqueue that
entity's import job, `manual_sync`); all group-gated
(`group_shopify_connector_operator`+), all enqueue-only, all
collision-safe by the same keys.

**D-A6-5 — Job-control services (retry/cancel/requeue).** On
`shopify.connector.job`: `action_manual_retry()` — allowed from
`failed_retryable`/`failed_final`/`blocked_manual_review` →
re-queues (state `queued`, retry_count preserved, one `manual_action`
log row, actor recorded; reviewer/admin for `blocked_manual_review`
per the accepted role matrix, operator+ otherwise);
`action_cancel()` — allowed from non-terminal states → `cancelled`
with reason + log (operator+). Both refuse terminal-to-terminal
transitions. No force/bypass parameter exists. (These are the
services the UI's Error Center buttons later call — PD-2.)

**D-A6-6 — Progress visibility (backend).** Scan jobs log
enumerated/enqueued/collided counts per page in `technical_detail`;
the store gains computed helper fields (non-stored)
`pending_job_count`/`failed_job_count` for shell/UI use. No
dashboard work here.

## 3. Tests (exact files)

In product: `test_product_scan_triggers.py`; in sale:
`test_customer_scan_triggers.py`, `test_order_scan_triggers.py`,
`test_job_control_services.py` (placed in sale to avoid core edits?
— **no**: job-control services extend `shopify.connector.job` via
`_inherit` from… **decision:** job-control services are generic and
belong to core — but core edits are forbidden for domain tasks.
Resolution (flagged): `action_manual_retry`/`action_cancel` are
implemented in a small `shopify_connector_job.py` `_inherit`
extension **inside `shopify_connector_sale`**? Rejected — generic
services in a domain module is mis-ownership. **Final proposal: this
task's allowlist includes one NEW core file
`addons/shopify_connector_core/models/shopify_connector_job_actions.py`**
(pure additive `_inherit` extension of the job model, no existing
core file edited) plus `tests/test_job_actions.py` in core — an
explicitly-named additive core exception for generic operator
services, consistent with core owning the job substrate. Flagged for
ChatGPT.) Coverage: one-scan-per-store-domain collision; checkpoint
advance only after commit; overlap window applied; unchanged-object
collision counted; manual/scheduled/source labeling; cron
never-raises; retry/cancel state matrices incl. permission denials
and no-bypass; selected-record sync.

## 4. Acceptance criteria / DoD

Operator can (from shell/server action) trigger any Lite-domain sync,
retry any failed job, cancel any stuck job — with every path
audited, collision-safe, and permission-gated; zero mapping-logic
changes (diff-level check); suites + Odoo.sh green; validation record
+ AR row + handoff; draft PR; gate closes on draft-open. Rollback:
single-PR revert; no schema beyond settings fields + checkpoint
fields; jobs already enqueued remain valid.

## 5. Register impacts on acceptance

OP-28 → Resolved-by-packet (Lite trio; Full modules carry their own);
UAT blocker U-4 closes when this merges; the sequence doc's Area-6
description superseded (note).

## 6. Gate criteria

The 15-pattern applies with: 1 = Task 012 merged runtime-green
(order scan needs the order importer); 6/7 = no mapping-logic and no
Full-domain scope; 13 = the D-A6-5 core-additive exception explicitly
accepted; others as in prior packets.

## 7. Locked final implementation prompt (Area 6 / "Task 016")

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE TRIGGERS GATE, VERIFIES THE CURRENT BASE SHA,
AND ISSUES THIS PROMPT.

Implement the Area 6 trigger retrofit exactly per
docs/07-implementation-plan/area-6-sync-triggers-implementation-packet.md
(D-A6-1..6 binding). Branch from the verified current
Shopify-connector tip (STOP on drift). One session; draft PR; stop.

ALLOWED FILES (exhaustive):
addons/shopify_connector_product/models/{__init__.py,
shopify_connector_product_scan.py (NEW)},
addons/shopify_connector_product/data/shopify_connector_product_cron.xml (NEW),
addons/shopify_connector_product/models/shopify_connector_store_settings.py (NEW — product checkpoint + scheduled flag),
addons/shopify_connector_product/__manifest__.py (data entry only),
addons/shopify_connector_product/tests/test_product_scan_triggers.py (NEW),
addons/shopify_connector_sale/models/{__init__.py,
shopify_connector_customer_scan.py (NEW),
shopify_connector_order_scan.py (NEW)},
addons/shopify_connector_sale/models/shopify_connector_store_settings.py
(customer/order scheduled flags + customer checkpoint),
addons/shopify_connector_sale/data/shopify_connector_sale_cron.xml (NEW),
addons/shopify_connector_sale/__manifest__.py (data entry only),
addons/shopify_connector_sale/tests/{test_customer_scan_triggers.py,
test_order_scan_triggers.py} (NEW),
addons/shopify_connector_core/models/shopify_connector_job_actions.py
(NEW — additive _inherit only: action_manual_retry, action_cancel),
addons/shopify_connector_core/models/__init__.py (one import line),
addons/shopify_connector_core/tests/test_job_actions.py (NEW),
docs/05-qa/task-016-sync-triggers-validation-results.md (NEW),
docs/05-qa/architecture-review-log.md (append row),
docs/01-research/research-handoff.md (top entry).
FORBIDDEN: every EXISTING core model file (the job-actions file is
new+additive; no existing core file may change except the one-line
models/__init__.py import); all importer/matching logic files' logic
(scan services call them, never modify them); inventory/fulfillment/
product_export anything; UI/webhooks/OAuth/CI; adams_base.

HARD CONSTRAINTS: enqueue-only everywhere (no inline execution);
cursors in-run only; checkpoints advance post-commit with the 10-min
overlap; one active scan per store+domain via operation_scope_key;
scheduled sync opt-in per store; cron handlers never raise; job
services carry no bypass and full audit logs; concurrency caveat
restated. Odoo.sh green before merge review (verbatim quote). Stop
condition: draft PR "Task 016: manual and scheduled sync triggers";
gate closes on draft-open; no UI/webhook work.
```
