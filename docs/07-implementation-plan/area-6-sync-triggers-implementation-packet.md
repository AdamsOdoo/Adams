# Area 6 — Manual & Scheduled Sync Triggers: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §7 is NOT usable.** Produced 2026-07-10 (AR-042 candidate);
> **revised 2026-07-11** by the PR #148 revision session per ChatGPT's
> control-room review (comment `4942966937`, item 5): **D-A6-7 (the
> readiness pending-slot closure) is split out of this task** into its
> own tiny, independently gated core task —
> `task-core-r1-readiness-correction-packet.md` (Task CORE-R1),
> sequenced before Task 010B/012 live use. This packet keeps only the
> trigger/enumeration/job-action scope; §2's D-A6-7 text is preserved
> below as the historical design record with a superseded marker, and
> the §7 prompt no longer touches the readiness file.
> Closes OP-28 at proposal level. Evidence: ARCH §5.5 (PD-5
> checkpoints), §7 (enqueue seam); merged core code. **Scope revision
> to the original Area-6 concept (flagged decision D-A6-1):** the Full
> modules (Tasks 013/014/015) ship their own triggers natively inside
> their packets; Area 6 is therefore the **retrofit task for the Lite
> trio** — enumeration/scan services, crons, manual service call
> sites, and the operator job-control services — for
> product/customer/order import. This makes the merged backend
> operator-invokable without waiting for (or requiring) any UI.
> **Follow-on (2026-07-11):** when this task ships the three scan
> crons, it MAY extend CORE-R1's real `cron_queue_health` check via
> `_inherit` to also verify the scan crons of enabled domains
> (CORE-R1 D-R1-1's capability-aware rule) — an additive check
> extension, part of this packet's core-additive allowance.
>
> **D-A6-5 ownership transferred 2026-07-15
> ([`DEC-034`](../04-decisions/DEC-034-wave-1-packet-dependency-reconciliation.md),
> Wave 1 packet reconciliation, resolving Sol's hard-stop, issue #167
> comment `4980808811`): the generic job-control services
> (`action_manual_retry()`/`action_cancel()`) are extracted from this
> packet into their own independently gated, generic, core-owned Wave 1
> task —
> [`task-job-actions-generic-core-packet.md`](./task-job-actions-generic-core-packet.md)
> (Task JOB-ACTIONS).** This resolves the ownership question §3 of this
> packet originally left "Flagged for ChatGPT" ("job-control services
> are generic and belong to core... an explicitly-named additive core
> exception for generic operator services"). D-A6-5's text below is
> preserved as the historical design record (mechanics unchanged,
> carried forward verbatim into the new packet); **this packet no
> longer owns or implements `action_manual_retry`/`action_cancel` in
> any future implementation** — it depends on Task JOB-ACTIONS's
> already-merged services (§7 prompt corrected accordingly). This
> packet retains D-A6-1..4/6 (scan jobs, crons, manual domain-sync
> services, progress visibility) and remains unauthorized Wave 2+
> scope, gated on Task 012 merging, exactly as before.

## 1. Objective, scope, non-goals

One implementation task ("Task 016 — sync triggers & operability",
working number) — **a core-plus-Lite-trio task, stated plainly
(red-team-corrected: an earlier draft of this section claimed "no
core edits," contradicting the allowlist)**. It touches
`shopify_connector_product` and `shopify_connector_sale` (scan
services + cron data files) **and core, by design, in one named
additive piece (revised 2026-07-15, DEC-034 — the former second piece,
D-A6-5's generic job-control services, moved to Task JOB-ACTIONS,
Wave 1; the former third piece, the D-A6-7 readiness closure, had
already moved to Task CORE-R1 in the 2026-07-11 revision)**: the
optional D-R1-1 scan-cron check extension
(`_inherit`, additive) to `core/models/__init__.py`. **Non-goals:** no
readiness placeholder edits (CORE-R1's scope, already merged by this
task's gate time); no generic job-control actions (Task JOB-ACTIONS's
scope, already merged by this task's gate time — this task calls
`action_manual_retry`/`action_cancel`, e.g. from `action_sync_selected()`'s
re-enqueue path where applicable, it does not implement them); no UI
(services are called from shell/server actions until the UI phase
wires buttons to them); no webhooks; no full-sync/backfill beyond
the 60-day order window; no changes to import mapping/matching logic
of any kind; no dispatcher/job-model logic changes beyond the named
additive files.

## 2. Design (D-A6-1 … D-A6-7) — each Proposed

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
(`res_model='shopify.connector.store'`, `res_id=store`) **with
`shopify_target_gid` set to the synthetic per-domain marker
`scan:<domain>`** (red-team-corrected: the merged
`operation_scope_key` is `store|res_model|res_id|shopify_target_gid`
and does NOT include `job_type` — without the marker, scans of
different domains for one store would collide with each other; with
it, the key serializes **one active scan per domain per store**, and
the merged key-compute clears on terminal states so the next scan can
run). A second same-domain scan while one is non-terminal collides
and is not created — the overlap-prevention mechanism. Enqueue-side duplicate
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

**D-A6-5 — Job-control services (retry/cancel/requeue) — OWNERSHIP
TRANSFERRED 2026-07-15: moved to Task JOB-ACTIONS
(`task-job-actions-generic-core-packet.md`), its own independently
gated Wave 1 task, per DEC-034. The text below is preserved as the
historical design record — the mechanics are unchanged and carried
forward verbatim; Task JOB-ACTIONS's packet is the operative version.
This task (Area 6) does not implement, and its future allowlist must
not include, either method — see §7's corrected allowed/forbidden
lists.** On
`shopify.connector.job`: `action_manual_retry()` — allowed from
`failed_retryable`/`failed_final`/`blocked_manual_review`/**`skipped`**
(red-team addition: `skipped` is a terminal state a policy-skipped
job lands in — Task 012's D-012-3 JobPolicySkip path and its packet's
skip-recovery note depend on manual retry being the documented
recovery route out of it) → re-queues (state `queued`, **retry_count
reset to 0** — a manual retry grants a fresh automatic-retry budget;
an earlier draft preserved the count, which would make a retry from
`failed_final` re-exhaust immediately — one `manual_action` log row,
actor recorded; reviewer/admin for `blocked_manual_review` per the
accepted role matrix, operator+ otherwise). Retrying from a terminal
state deliberately does **not** violate the terminal-state contract:
the merged model clears `operation_scope_key` on terminal entry and
recomputes it on re-queue, and `idempotency_key` is never cleared —
the retry is the same logical operation, which is exactly what that
key exists to assert. `action_cancel()` — allowed from non-terminal
states → `cancelled` with reason + log (operator+). Both refuse every
other terminal-to-terminal transition. No force/bypass parameter
exists. (These are the services the UI's Error Center buttons later
call — PD-2.)

**D-A6-6 — Progress visibility (backend).** Scan jobs log
enumerated/enqueued/collided counts per page in `technical_detail`;
the store gains computed helper fields (non-stored)
`pending_job_count`/`failed_job_count` for shell/UI use. No
dashboard work here.

**D-A6-7 — Readiness pending-slot closure — SUPERSEDED 2026-07-11:
moved to Task CORE-R1 (`task-core-r1-readiness-correction-packet.md`,
D-R1-1..5), its own independently gated task sequenced before Task
010B/012 live use, per the PR #148 review item 5. The text below is
preserved as the historical design record; CORE-R1's packet is the
operative version (differences: `cron_queue_health` verifies the
merged drain cron + queue stall — NOT the Area-6 scan crons, which do
not exist at CORE-R1 time; this task may later extend that check per
the header follow-on note).** The merged core registers three placeholder readiness checks
(`webhook_hmac`, `mapped_location`, `cron_queue_health`), all
ESSENTIAL tier and permanently `not_proven`; the merged aggregate is
fail-closed (an essential `not_proven` forces overall `fail`) and
`action_activate` requires `last_readiness_result in
('pass','warning')` — so **today no store can ever reach
`connected`**, which blocks every mutation task's dev-store
validation. The red-team review found this slot set orphaned (no
packet owned `cron_queue_health` at all). Area 6 owns the closure
because it is the task that makes the answer to each slot true or
knowable:

- **`cron_queue_health` — implemented for real here** (this task
  introduces the crons it verifies). Pass when the three scan crons
  exist and are active (xml-id lookup on the noupdate cron records)
  AND no `queued` job for the store is older than a stall threshold
  (constant, proposed 60 min) without ever having been attempted;
  fail with a named reason otherwise. Reads `ir.cron` and the job
  table only — no Shopify call, no secret.
- **`mapped_location` — becomes conditionally applicable in core.**
  When the store's `inventory_domain_enabled` settings flag is False:
  pass with reason "not applicable — inventory domain not enabled for
  this store" (reads the same core settings flag
  `_check_domain_flag_enablement` already reads; no domain-model
  dependency). When the flag is True and no inventory module has
  overridden the check: stays `not_proven` (fail-closed — an
  inventory-enabled store without the inventory module must not
  activate). Task 013 replaces the evaluation via `_inherit` override
  with the real mapped-location verification when
  `shopify_connector_inventory` is installed (its packet cites this
  design as its baseline).
- **`webhook_hmac` — becomes conditionally applicable in core, same
  pattern.** The accepted MVP trigger architecture is pull-based
  (these scans/crons); webhook intake is the W1 tail phase. Core
  check passes with reason "not applicable — webhook intake is not
  installed; scheduled/manual sync is the active trigger mechanism";
  the W1 packet owns replacing it (via `_inherit`) with the real
  HMAC-configuration verification when the webhook module installs.
  **Flagged prominently for ChatGPT: this relaxes a fail-closed
  pending slot to a not-applicable pass.** The justification is that
  the slot was fail-closed only because no trigger architecture
  existed yet; with pull-based MVP accepted, "webhook HMAC not
  verifiable" is not a defect of a deployment that has no webhook
  endpoint. Rejecting this sub-proposal means no store activates
  until W1 ships — a sequencing decision ChatGPT must make
  explicitly, not inherit silently.

This is the one Area-6 piece that **edits an existing core file**
(`shopify_connector_readiness_check.py` — only the three named
placeholder check methods plus the stall-threshold constant; the
file's own docstrings describe the slots as "registered pending check
slot only", i.e. designed to be filled). Sequencing consequence: Area
6 must merge (or at minimum D-A6-7 must be split out and merged)
**before any mutation task's dev-store validation**, because those
validations require a `connected` store. The alternative — activating
a store for validation by manual override — does not exist in the
merged code (no bypass parameter, deliberately), so the slot closure
is the only honest path.

## 3. Tests (exact files)

In product: `test_product_scan_triggers.py`; in sale:
`test_customer_scan_triggers.py`, `test_order_scan_triggers.py`.
**Resolved 2026-07-15, DEC-034 (this section's original "Flagged for
ChatGPT" ownership question — job-control services are generic and
belong to core, but core edits were forbidden for domain tasks — is
now answered):** `action_manual_retry`/`action_cancel` and their test
coverage belong to Task JOB-ACTIONS
(`addons/shopify_connector_core/models/shopify_connector_job_actions.py`,
`addons/shopify_connector_core/tests/test_job_actions.py`), a separate,
independently gated, generic Wave 1 core task — **not** this task's
allowlist. This task's own test coverage is therefore: one-scan-per-store-domain
collision; checkpoint advance only after commit; overlap window
applied; unchanged-object collision counted; manual/scheduled/source
labeling; cron never-raises; selected-record sync (`action_sync_selected()`
is enqueue-only, per D-A6-4 — it does not call `action_manual_retry`/
`action_cancel`; this task's dependency on Task JOB-ACTIONS is that
those two methods already exist for the later UI wave to wire buttons
to, not a call-graph dependency inside this task's own services).
(Readiness-slot tests moved to CORE-R1's
`test_readiness_slot_closure.py` — 2026-07-11; if this task extends
`cron_queue_health` with the scan-cron verification, it appends the
scan-cron pass/fail cases to that same core test file.)

## 4. Acceptance criteria / DoD

Operator can (from shell/server action) trigger any Lite-domain sync
and re-sync a selected record — with every path audited,
collision-safe, and permission-gated; zero mapping-logic changes
(diff-level check); retry/cancel of a failed, skipped, or stuck job is
Task JOB-ACTIONS's already-merged scope (`action_manual_retry`/
`action_cancel`), not re-proven here; suites + Odoo.sh green;
validation record + AR row + handoff; draft PR; gate closes on
draft-open. (The store-reaches-`connected` regression is CORE-R1's —
already merged by this task's gate time — 2026-07-11.) Rollback:
single-PR revert; no schema beyond settings fields + checkpoint
fields; jobs already enqueued remain valid.

## 5. Register impacts on acceptance

OP-28 → Resolved-by-packet (Lite trio; Full modules carry their own);
UAT blocker U-4 closes when this merges; the sequence doc's Area-6
description superseded (note); the red-team architecture BLOCKER
"no store can reach `connected`" → owned and closed by **Task
CORE-R1** (revised 2026-07-11 — no longer this packet's; every
mutation task's dev-store validation depends on CORE-R1, which
precedes this task in the revised critical path).

**Lifecycle (LC-1) adoption (re-review `4945129824` item 7):** every
Area-6 scan/enumeration `job_type` `selection_add` `ondelete` uses the
LC-1 callable `_reassign_to_historic_job_type` from the start (LC-1
precedes Task 012 — DEC-030 / lifecycle §7), so no later retrofit is
needed.

## 6. Gate criteria

The 15-pattern applies with: 1 = Task 012 merged runtime-green
(order scan needs the order importer) AND CORE-R1 merged (readiness
already corrected) AND Task JOB-ACTIONS merged (this task depends on,
never reimplements, `action_manual_retry`/`action_cancel` — DEC-034,
2026-07-15); 6/7 = no mapping-logic and no Full-domain scope; 13 =
**superseded 2026-07-15 (DEC-034) — the D-A6-5 core-additive exception
no longer applies to this task; it was resolved by transferring D-A6-5
to Task JOB-ACTIONS.** The readiness edits remain CORE-R1's own
accepted scope (revised 2026-07-11); others as in prior packets.

## 7. Locked final implementation prompt (Area 6 / "Task 016")

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE TRIGGERS GATE, VERIFIES THE CURRENT BASE SHA,
AND ISSUES THIS PROMPT.

Implement the Area 6 trigger retrofit exactly per
docs/07-implementation-plan/area-6-sync-triggers-implementation-packet.md
(D-A6-1..4/6 binding; D-A6-5 is Task JOB-ACTIONS's merged scope — do
NOT reimplement action_manual_retry/action_cancel; D-A6-7 is Task
CORE-R1's merged scope — do not touch the readiness file). Prerequisites:
Task 012 AND CORE-R1 AND Task JOB-ACTIONS merged runtime-green. Branch
from the verified current mvp/program-integration tip (STOP on drift).
One session; draft PR; stop.

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
addons/shopify_connector_core/models/shopify_connector_scan_cron_health.py
(NEW, OPTIONAL — additive _inherit extension of the CORE-R1
cron_queue_health check adding scan-cron verification for enabled
domains, per the packet header follow-on note; nothing else),
addons/shopify_connector_core/tests/test_readiness_slot_closure.py
(append scan-cron cases ONLY, if the optional extension is built),
docs/05-qa/task-016-sync-triggers-validation-results.md (NEW),
docs/05-qa/architecture-review-log.md (append row),
docs/01-research/research-handoff.md (top entry).
FORBIDDEN: every other EXISTING core model file — explicitly
including shopify_connector_readiness_check.py (CORE-R1's merged
scope; this task extends via _inherit only, never edits) AND
shopify_connector_job_actions.py (Task JOB-ACTIONS's merged scope,
2026-07-15 DEC-034 — action_manual_retry/action_cancel already exist;
this task must not create, edit, or duplicate them); all
importer/matching logic files' logic (scan services call them, never
modify them); inventory/fulfillment/product_export anything;
UI/webhooks/OAuth/CI; adams_base.

HARD CONSTRAINTS: enqueue-only everywhere (no inline execution);
cursors in-run only; checkpoints advance post-commit with the 10-min
overlap; one active scan per store+domain via operation_scope_key
with shopify_target_gid='scan:<domain>' (the merged key excludes
job_type — the marker is mandatory);
scheduled sync opt-in per store; cron handlers never raise; this
task's own services (scans/crons/manual-sync/selected-record-sync)
carry no bypass and full audit logs; job-level manual retry/cancel is
Task JOB-ACTIONS's already-merged, already-tested scope — not
reimplemented or re-tested here; the readiness file is NEVER edited
(CORE-R1 scope — the optional scan-cron check extension is
_inherit-additive only); concurrency caveat restated. Odoo.sh green
before merge review (verbatim quote). Stop
condition: draft PR "Task 016: manual and scheduled sync triggers";
gate closes on draft-open; no UI/webhook work.
```
