# Task 013B — Controlled Initial Shopify→Odoo Inventory Baseline: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §9 is NOT usable.** Produced 2026-07-11 by the PR #148
> revision session, implementing review item 3 of ChatGPT's
> control-room review (PR #148 comment `4942966937`): the accepted
> DEC-003 capability "Initial Shopify stock import is controlled /
> reviewed" — deferred by Task 013's D-013-8 to an unnamed candidate —
> is now a **complete MVP packet**, sequenced after Task 013 and
> **before final UAT and release**. Evidence: captures 2026-07-10 §3
> (inventory APIs) and 2026-07-11 §5 (quantity-state model re-verified);
> the Task 013 packet (whose module this extends). DEC-010 explicitly
> allows this one-time reviewed import as the sole standing-direction
> exception. Checked against `../05-qa/rejected-approaches-log.md`:
> RA-008 (blind first push) and RA-021 (assumed quantity equivalence)
> are honored — preview + explicit confirmation + recorded
> source-of-truth are mandatory here in the import direction too;
> RA-020 is untouched (this is one-time and operator-driven, not
> autonomous bidirectional logic).

## 1. Objective, scope, non-goals

One-time, per-store, operator-confirmed import of Shopify `available`
quantities into Odoo stock for **mapped locations and bound variants
only**, executed as reviewed inventory adjustments with full audit
evidence. This exists for onboarding: a merchant whose stock truth
currently lives in Shopify gets a correct Odoo starting point, after
which DEC-010's standing direction (Odoo → Shopify) takes over.
**Non-goals:** no standing Shopify→Odoo pull (one run per pair, replay
guarded); no `on_hand`/`committed` semantics (`available` only); no
location creation/mapping changes; no unmapped-location import; no
lot/serial support (named exclusion — tracked products with lots
route to manual review); no UI beyond the backend service methods the
S11-family screens later call (PD-2).

## 2. Decision closures (D-013B-1 … D-013B-8) — each Proposed

**D-013B-1 — Read surface.** Per store: for each
`shopify.connector.inventory.level.binding` row (Task 013's model —
variant binding × location mapping), read
`inventoryLevel.quantities(names: ["available"])` via the
`inventoryItem.inventoryLevel(locationId:)` path (captures 2026-07-10
§3; quantity-state list re-verified 2026-07-11 §5 — `available` is a
documented state name). Read-only; scope `read_inventory` (already in
the Lite baseline set). Variants without a level binding (item not
stocked at the mapped location) are enumerated in the preview as
"absent remotely — no action" rows, never invented.

**D-013B-2 — Preview (mandatory, first phase).** Job type
`inventory_baseline_preview` (`job_source='export_preview_dry_run'` —
the merged read-only source, reused for this read-only run): produces
a per-pair table — Shopify `available`, current Odoo quantity for the
mapped location (same `free_qty`-with-location-context read Task 013
pushes from, so both directions use one recorded quantity semantic —
RA-021's recorded-equivalence rule), the delta, and the resulting
adjustment — stored as the job-log payload and on a
`shopify.connector.inventory.baseline.run` record (store, state
`previewed/confirmed/applied/expired`, per-pair JSON, created_by/at,
confirmed_by/at, applied_by/at). Preview **expires** after 24 h or on
any mapping/binding change (write_date comparison) — stale previews
cannot be confirmed.

**D-013B-3 — Operator confirmation (explicit, recorded).**
`action_confirm_baseline_run()` — reviewer/admin groups only —
records who/when against the unexpired preview. The apply handler
refuses any run not `confirmed` → `destructive_write_guard_blocked`
(the accepted six-sub-reason set; no new classes). No auto-apply path
exists; no flag bypasses the guard (merged invariant restated).

**D-013B-4 — Safe Odoo stock adjustment mechanism.** Apply job type
`inventory_baseline_apply`, one job **per pair** (`res_model/res_id` →
the level-binding row; `operation_scope_key` serializes per pair;
collision with Task 013 push jobs on the same pair is intended —
baseline and push for one pair never run concurrently). Mechanism:
the standard Odoo 19 inventory-adjustment path on `stock.quant`
(set the counted quantity for [product, location], apply with a
reference note "Shopify baseline import — job <id>") — **named
build-time verification:** the exact 19.0 quant-adjustment API
(counted-quantity field + apply method) is verified against the 19.0
source in-session before use; STOP-and-report if it differs (no
improvisation; same rule as Task 010B's D-010B-3). Products with
`tracking != 'none'` (lots/serials) → `blocked_manual_review` /
`binding_conflict` with a named reason (adjusting lot-tracked stock
needs operator judgement). Negative Shopify `available` values import
as the true negative? **No** — clamped to 0 with a note (mirror of
Task 013's clamp; Odoo can represent negative counted quantities but
importing a remote oversell state as a negative baseline creates
phantom debt; flagged call).

**D-013B-5 — Audit evidence.** Every applied pair logs: prior Odoo
quantity, Shopify value, adjustment delta, quant reference, actor,
run id — in `job.log.technical_detail` and summarized on the baseline
run record. The run record is the release-plan evidence artifact
(UAT scenario §UAT-25 consumes it).

**D-013B-6 — Duplicate/replay behavior.** One baseline per pair:
applying stamps `baseline_applied_at`/`baseline_run_id` on the level
binding; a second preview **shows** already-baselined pairs as
excluded-by-default (re-inclusion requires an explicit per-pair
operator override in the confirmation — recorded), and the apply
handler refuses a pair whose stamp doesn't match the confirmed run →
`destructive_write_guard_blocked`. Job-level replay is guarded by
`idempotency_key` (payload_hash = run id + pair + quantities) and the
per-pair scope key.

**D-013B-7 — Rollback.** Technical: revert the single PR (schema:
run model + two stamp fields — additive). Operational (documented in
the run record and release plan): every adjustment is reversible by a
counter-adjustment from the recorded prior quantities; the run record
contains the exact per-pair prior values, so "undo the baseline" is a
documented manual procedure with complete data — never an automatic
write.

**D-013B-8 — Sequencing.** After Task 013 (needs its models,
mappings, and first-push guard vocabulary), before final UAT/release
(the review's placement). Onboarding-order note for operators: run
the baseline **before** confirming first pushes (a push after
baseline sees consistent numbers); the readiness of both is an
operator-doc item in the release plan, not a code gate.

## 3. Store settings / model additions

`shopify.connector.inventory.baseline.run` (per D-013B-2); level
binding gains `baseline_applied_at` (Datetime ro) +
`baseline_run_id` (M2o ro). Job types map to
`inventory_domain_enabled` via the existing seam.

## 4. Tests (exact files)

`test_inventory_baseline_preview.py` (per-pair table math incl.
absent-remotely rows; expiry on time and on mapping change; read-only
source guard — no mutation strings in the module additions);
`test_inventory_baseline_guard.py` (unconfirmed → blocked; stale
preview → blocked; permission matrix reviewer/admin; no-bypass source
scan; already-baselined pair excluded/refused without explicit
override); `test_inventory_baseline_apply.py` (quant adjustment with
reference; prior/new/delta evidence logged; clamp-to-0 note;
lot-tracked → manual review; stamp written; replay collides;
per-pair serialization vs push jobs); `test_inventory_baseline_run_model.py`
(schema/states/ACL — auditor/operator read, reviewer confirm, admin
rwc, no unlink).

## 5. Gate criteria (15-pattern, abbreviated)

1 Task 013 merged runtime-green; 2–3 exact names ✅(§2/§3); 4 files
✅(§9); 5 clamp/expiry/one-time thresholds fixed ✅; 6 no standing
pull, no push changes ✅; 7 no fulfillment/product scope ✅; 8 no
UI/webhook ✅; 9 tests ✅(§4); 10 rollback ✅(D-013B-7); 11 live
validation required (§6); 12 gate-act reconfirmation; 13 the two
flagged calls explicit: negative-clamp (D-013B-4) and
re-inclusion-override (D-013B-6); 14 quantity semantics recorded
✅(D-013B-2, RA-021); 15 lot-tracked routing explicit ✅(D-013B-4).

## 6. Odoo.sh + live validation

Odoo.sh: full suites green (verbatim quote). Dev store: one full
preview → confirm → apply cycle over ≥2 mapped pairs including one
already-baselined replay refusal and one clamp case; evidence
(redacted) in the validation record; explicit recorded ChatGPT waiver
is the only alternative.

## 7. Acceptance criteria / DoD

No Odoo stock write without a confirmed, unexpired run; every write
audited with prior values; replay provably refused; `committed`
never touched anywhere (RA-018 source guard re-run over the module);
suites + Odoo.sh green + dev-store evidence; validation record + AR
row + handoff; draft PR; gate closes on draft-open.

## 8. Register impacts on acceptance

D-013-8's deferral → superseded by this packet (013B is now a named,
fully-planned MVP task, not a candidate); DEC-003 C-INV "controlled
initial stock import" → planning-complete; release plan §2 and UAT
plan gain the corresponding rows/scenarios (updated this session).

## 9. Locked final implementation prompt (Task 013B)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE TASK-013B GATE, VERIFIES THE CURRENT BASE SHA,
AND ISSUES THIS PROMPT. (Prerequisite: Task 013 merged runtime-green.)

Implement Task 013B — controlled initial Shopify->Odoo inventory
baseline — exactly per
docs/07-implementation-plan/task-013b-initial-inventory-baseline-packet.md
(D-013B-1..8 binding). Branch from the verified current
Shopify-connector tip (STOP on drift). One session; draft PR; stop.

ALLOWED FILES (exhaustive):
  addons/shopify_connector_inventory/models/shopify_connector_inventory_baseline.py  (NEW — run model + preview/confirm/apply services + job seams)
  addons/shopify_connector_inventory/models/shopify_connector_inventory_level_binding.py (the two stamp fields only)
  addons/shopify_connector_inventory/models/__init__.py                              (import line)
  addons/shopify_connector_inventory/security/ir.model.access.csv                    (run-model rows only)
  addons/shopify_connector_inventory/tests/{test_inventory_baseline_preview.py,
    test_inventory_baseline_guard.py, test_inventory_baseline_apply.py,
    test_inventory_baseline_run_model.py}                                            (NEW)
  docs/05-qa/task-013b-validation-results.md                                         (NEW)
  docs/05-qa/architecture-review-log.md                                              (append one AR row)
  docs/01-research/research-handoff.md                                               (top entry)
FORBIDDEN: every core/product/sale/fulfillment/product_export file;
every existing Task-013 push/mapping/first-push file beyond the two
named stamp fields; any Shopify mutation (this task is read-only
toward Shopify — source guard); any standing pull/cron for baseline;
lot/serial adjustment logic; UI/webhooks/OAuth/CI; adams_base; main;
plain dev.

HARD CONSTRAINTS: preview -> explicit reviewer/admin confirmation ->
apply, no other path, no auto-apply, no bypass; one baseline per pair
with recorded re-inclusion override only; verify the 19.0
stock.quant counted-quantity/apply API against source before use —
STOP and report if it differs; clamp negative remote values to 0
with a note; lot-tracked products -> blocked_manual_review; prior
quantities recorded for every write (the documented manual-undo
path); quantity semantics: Shopify 'available' vs the same
location-context free_qty read Task 013 uses (RA-021 recorded
equivalence); committed never written or read for writing (RA-018);
concurrency caveat restated. Odoo.sh green + the §6 dev-store cycle
evidence (or recorded explicit ChatGPT waiver). Stop condition:
draft PR "Task 013B: controlled initial inventory baseline import";
gate closes on draft-open; no other work.
```
