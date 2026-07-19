# Task 013B — Controlled Initial Shopify→Odoo Inventory Baseline: Implementation-Ready Planning Packet

> **Status: GATE B ACCEPTANCE CANDIDATE — NOT IMPLEMENTATION AUTHORIZED**
> (updated 2026-07-19, Wave 3 Gate B session, no contradiction found; see
> new §0 below and
> [`DEC-037`](../04-decisions/DEC-037-wave-3-inventory-gate-b.md) §8).
> **The locked prompt in §9 is superseded — use
> [`../06-prompts/sol-wave-3-task-013b-locked-prompt.md`](../06-prompts/sol-wave-3-task-013b-locked-prompt.md)
> (LOCKED, unissued) instead.** Task 013B implementation requires Gate B
> accepted and merged, Stage 0 merged and runtime-proven, **and** Task 013
> itself merged and runtime-proven (D-013B-8, unchanged). Originally
> produced 2026-07-11 by the PR #148 revision session, implementing
> review item 3 of ChatGPT's
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
> **Revised 2026-07-11 per final-convergence comment `4947866018`
> item 2:** the apply step now takes a **database-backed row lock**
> (`try_lock_for_update()`) on the dependent `stock.quant`/level-
> binding/location-mapping/variant-binding rows *before* its final
> re-read (re-reading alone is not a race guard — a competing Odoo
> transaction can change a quant/reservation in the TOCTOU window;
> `operation_scope_key` serializes only connector jobs, not ordinary
> stock moves), and a real concurrent-transaction test proves it
> (D-013B-4, §4, §6).

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

## 0. Layer 2 non-applicability [new, Gate B, 2026-07-19, DEC-037 §8]

Task 013B issues **zero** Shopify mutations and therefore does not
consume the DEC-036 Layer 2 mutation-safety substrate:

- Its only Shopify calls are **reads** —
  `inventoryLevel.quantities(names: ["available"])` (D-013B-1) — which
  the existing Layer 1 replay-policy registry already classifies
  `remote_read_replay_safe` (unchanged, unaffected by DEC-036).
- There is no `shopify.connector.mutation.attempt` row, no
  `mutation_domain` registration, no C1/C2/NET/C3 protocol, and no Layer
  2 wrapper call anywhere in this task's scope.
- Its safety contract is a **local Odoo transaction/locking** concern —
  database-backed row locking (`try_lock_for_update()`), a final re-read
  under lock, drift/topology abort, and post-write `free_qty`
  verification with rollback — fully specified below (D-013B-4) and
  unrelated to Shopify-mutation reconciliation.
- **No Layer 2 mutation wrapper is added to this task merely for
  symmetry** with Task 013: doing so would misrepresent a
  Shopify-read-plus-local-write flow as if it carried the Shopify-mutation
  risk Layer 2 exists to manage, which it structurally cannot have (there
  is no Shopify mutation to be uncertain about).
- Exact interaction with Task 013 (unchanged, restated): Task 013 must be
  installed and its own Gate B/Stage 0 dependencies accepted first; a
  baseline apply for a pair blocks any concurrent push job for that same
  pair via the shared `operation_scope_key` (D-013B-4); after a
  successful baseline, Odoo is the standing authority and the next Task
  013 push for that pair begins from the accepted baseline state
  (D-013B-8).

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

**D-013B-2 — Preview (mandatory, first phase) — quantity semantics
made explicit (re-review `4945129824` item 2).** Job type
`inventory_baseline_preview` (`job_source='export_preview_dry_run'` —
the merged read-only source, reused for this read-only run) produces a
per-pair table with the correct semantics: Shopify `available` is an
**available/free** quantity, matched to Odoo location-context
**`free_qty`** (the same quantity Task 013 pushes from), where — by
Odoo's model — `free_qty = on_hand − reserved` (RA-021's
recorded-equivalence rule, **corrected**: the equivalence is
`available`↔`free_qty`, **never** `available`↔on-hand). An inventory
adjustment sets **counted on-hand** (`stock.quant`), not `free_qty`,
so the preview records, per pair: Shopify `available`
(= `desired_free`, after the D-013B-4 negative clamp); current Odoo
`free_qty`; current Odoo on-hand; current **reserved** quantity; the
**counted-on-hand target** `target_on_hand = desired_free + reserved`
(D-013B-4); and the resulting on-hand delta the apply will book. It is
stored as the job-log payload and on a
`shopify.connector.inventory.baseline.run` record (store, state
`previewed/confirmed/applied/expired`, per-pair JSON **including the
reserved-quantity snapshot used to compute the target**, created_by/at,
confirmed_by/at, applied_by/at). Preview **expires** after 24 h or on
any mapping/binding change (write_date comparison); and — because the
target depends on reserved quantity — apply additionally re-reads and
**aborts on any quantity/reservation drift** (D-013B-4). Stale
previews cannot be confirmed.

**D-013B-3 — Operator confirmation (explicit, recorded).**
`action_confirm_baseline_run()` — reviewer/admin groups only —
records who/when against the unexpired preview. The apply handler
refuses any run not `confirmed` → `destructive_write_guard_blocked`
(the accepted six-sub-reason set; no new classes). No auto-apply path
exists; no flag bypasses the guard (merged invariant restated).

**D-013B-4 — Safe Odoo stock adjustment mechanism (re-review
`4945129824` item 2 — free/on-hand semantics corrected).** Apply job
type `inventory_baseline_apply`, one job **per pair**
(`res_model/res_id` → the level-binding row; `operation_scope_key`
serializes per pair; collision with Task 013 push jobs on the same
pair is intended — baseline and push for one pair never run
concurrently). Mechanism: the standard Odoo 19 inventory-adjustment
path on `stock.quant` sets **counted on-hand**, so the counted-on-hand
target that yields the desired free/available quantity is

    target_on_hand = desired_shopify_available + current_reserved_quantity

booked with a reference note "Shopify baseline import — job <id>".
After the adjustment the apply step **verifies**
`resulting_free_qty == desired_shopify_available` (recomputed from the
post-write quant state); if it does not hold, it rolls back the
savepoint and routes to `blocked_manual_review` / `binding_conflict`
with the full quantity breakdown — the connector never leaves a
baseline it cannot prove correct. **Named build-time verification:**
the exact 19.0 quant-adjustment API (counted-quantity field + apply
method) and the reserved-quantity read are verified against the 19.0
source in-session before use; STOP-and-report if either differs (no
improvisation; same rule as Task 010B's D-010B-3).

**Database-backed apply lock + re-read + drift abort (race protection —
re-review `4947866018` item 2).** Re-reading alone is **not** a race
guard: another Odoo transaction can change a quant or a reservation
*after* the re-read and *before/during* the adjustment (a TOCTOU
window), and the connector `operation_scope_key` serializes only
connector jobs — it does **not** serialize ordinary Odoo stock
moves/reservations. The apply contract is therefore **lock, then
re-read, then verify, then write**, all inside the job's savepoint:
1. **Acquire a database row lock** (`try_lock_for_update()` — Odoo 19's
   official row-locking primitive, the same one the merged dispatcher
   claims jobs with; the exact 19.0 method/equivalent is verified
   against source at gate time) on **every row the adjustment depends
   on**: the relevant `stock.quant` row(s) at the [product, location],
   the `inventory.level.binding`, the `location.mapping`, and the
   `variant.binding`. If **any** required row cannot be locked, the
   apply **fails closed** (`destructive_write_guard_blocked`) and the
   operator re-previews — the connector never proceeds on an
   un-lockable row.
2. **Re-read under the lock** every quantity it depends on — on-hand,
   reserved, the mapping, the binding, and the level binding's
   `write_date` — and **abort** (no write;
   `destructive_write_guard_blocked`) if any value **or the quant
   topology** (number/identity of quants at the pair) changed from the
   confirmed preview snapshot. Because the rows are now locked, no
   competing transaction can mutate them between this re-read and the
   write.
3. **No-existing-quant case (explicit):** when the pair has no
   `stock.quant` row yet, the lock is taken on the level
   binding/mapping/variant binding (the rows that exist) and the
   adjustment **creates** the quant through the standard inventory-
   adjustment API — the connector does **not** pre-insert a bare quant
   row to lock (which would itself be race-prone); a quant appearing
   concurrently is caught by the post-write `free_qty` verification
   (D-013B-4 above) and rolled back.
4. **Verify** `resulting_free_qty == desired_shopify_available` before
   commit (D-013B-4); on failure roll back the savepoint →
   `blocked_manual_review` / `binding_conflict`.
The locks release when the job's savepoint/transaction commits (or on
rollback). A reservation created between preview and apply is therefore
either blocked from committing until the baseline commits, or caught by
the under-lock re-read + topology check — never a silently wrong
baseline.

**Enumerated edge behavior (fail closed where a deterministic
adjustment is not provable):**
- **Existing reservations:** handled by the `+ reserved` term above;
  the reserved quantity is snapshotted at preview and re-read at apply.
- **Multiple quants at one [product, location]** (distinct
  lot/owner/package rows): a single free/available number is **not
  deterministically attributable** across them →
  `blocked_manual_review` / `binding_conflict` (fail closed), never a
  guessed split.
- **Owner/package quants:** any quant with a non-empty `owner_id` or
  `package_id` at the pair → fail closed (same reason); the connector
  does not adjust third-party-owned or packaged stock.
- **In-flight moves / reservation changes between preview and apply:**
  caught by the **row lock + under-lock re-read + drift/topology abort**
  above (a competing transaction cannot mutate the locked rows between
  the re-read and the write).
- **Lots/serials:** products with `tracking != 'none'` →
  `blocked_manual_review` / `binding_conflict` (adjusting lot-tracked
  stock needs operator judgement — named exclusion, unchanged).
- **Negative Shopify `available`:** **not** imported as a true
  negative — clamped to 0 with a note (mirror of Task 013's clamp;
  Odoo can represent negative counted quantities, but importing a
  remote oversell state as a negative baseline creates phantom debt;
  flagged call). With the clamp, `desired_free = max(0, available)`.

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
**free_qty vs on-hand vs reserved columns and the
`target_on_hand = desired_free + reserved` computation**;
absent-remotely rows; expiry on time and on mapping change; read-only
source guard — no mutation strings in the module additions);
`test_inventory_baseline_guard.py` (unconfirmed → blocked; stale
preview → blocked; permission matrix reviewer/admin; no-bypass source
scan; already-baselined pair excluded/refused without explicit
override); `test_inventory_baseline_apply.py` (**counted-on-hand
target = desired_available + reserved with post-write
`free_qty == desired_available` verification**; **reservation present →
target includes it, resulting free_qty correct**; **the apply lock:
dependent quant/level-binding/mapping/variant-binding rows are locked
with `try_lock_for_update()` before the final re-read; an un-lockable
required row → fail closed (`destructive_write_guard_blocked`)**; **a
real concurrent-transaction test — a competing transaction adds a
reservation / changes the quant against the same pair while the apply
runs → the baseline either serializes correctly or aborts on the
under-lock drift/topology check, never a silently wrong `free_qty`**;
**reservation created between preview and apply → drift abort
(`destructive_write_guard_blocked`), no write**; **quant topology change
(quant count/identity differs from preview) → abort**; **no-existing-
quant case → lock the existing binding/mapping rows, create the quant
via the adjustment API, post-write verification catches a concurrent
quant**; **multiple quants at one [product, location] → fail closed**;
**owner/package quant → fail closed**; quant adjustment with reference;
prior/on-hand/reserved/new/delta evidence logged; clamp-to-0 note;
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
re-inclusion-override (D-013B-6); 14 quantity semantics correct —
`available`↔`free_qty`, adjustment target
`on_hand = desired_free + reserved`, post-write verification + drift
abort ✅(D-013B-2/4, RA-021); 15 lot-tracked / multi-quant /
owner-package fail-closed routing explicit ✅(D-013B-4); 16 (added
`4947866018`) database-backed apply lock (`try_lock_for_update()` on
quant/binding/mapping rows before the final re-read) + real
concurrent-transaction test explicit ✅(D-013B-4, §4/§6).

## 6. Odoo.sh + live validation

Odoo.sh: full suites green (verbatim quote). Dev store: one full
preview → confirm → apply cycle over ≥2 mapped pairs including **one
pair carrying a live reservation (proving
`target_on_hand = desired_available + reserved` yields the correct
post-apply `free_qty`)**, one already-baselined replay refusal, one
clamp case, and **one deliberate concurrent-drift case (a reservation
added by a competing transaction between preview and apply → the apply
lock + under-lock re-read causes it to abort, no wrong baseline
written)**; evidence (redacted) in the validation record; explicit
recorded ChatGPT waiver is the only alternative.

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

**Lifecycle (LC-1) adoption (re-review `4945129824` item 7):**
`inventory_baseline_preview`/`inventory_baseline_apply` register their
`selection_add` `ondelete` with the LC-1 callable
`_reassign_to_historic_job_type` from the start (LC-1 precedes Task 012
— DEC-030 / lifecycle §7), so no later retrofit is needed.

## 9. Locked final implementation prompt (Task 013B)

> **SUPERSEDED (Gate B, 2026-07-19).** The current locked prompt is
> [`../06-prompts/sol-wave-3-task-013b-locked-prompt.md`](../06-prompts/sol-wave-3-task-013b-locked-prompt.md)
> (`ISSUED-NOT-EXECUTED: NO`, `LOCKED: YES`). The text below is retained
> verbatim for history; its content is not contradicted by Gate B (no
> Layer 2 changes apply to this task, §0), but the base-SHA/issuance
> discipline in the dedicated file governs.

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
  addons/shopify_connector_inventory/tests/__init__.py                               (import lines)
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
with a note; lot-tracked products -> blocked_manual_review; multiple
quants at a pair / owner or package quants -> fail closed
(blocked_manual_review); prior on-hand + reserved quantities recorded
for every write (the documented manual-undo path); quantity semantics
(re-review item 2): Shopify 'available' == location-context free_qty,
and because an inventory adjustment sets COUNTED ON-HAND the target is
on_hand = desired_available + current_reserved, verified after write by
resulting free_qty == desired_available (else roll back to manual
review); the apply takes a DATABASE ROW LOCK (try_lock_for_update() —
verify the exact 19.0 method against source before use) on the
dependent stock.quant / level-binding / location-mapping /
variant-binding rows BEFORE the final re-read, fails closed if any
required row cannot be locked, then re-reads on-hand/reserved/mapping/
binding UNDER THE LOCK and ABORTS on any value or quant-topology drift
from the confirmed preview (re-reading alone is NOT a race guard —
operation_scope_key serializes only connector jobs, not ordinary Odoo
stock moves); the no-existing-quant case locks the existing
binding/mapping rows and creates the quant via the adjustment API (never
pre-inserts a bare quant to lock); a REAL concurrent-transaction test
proves a competing reservation/quant change is either serialized or
aborted, never a silently wrong free_qty; committed never written or
read for writing (RA-018); concurrency caveat restated. Odoo.sh green + the §6 dev-store cycle
evidence (or recorded explicit ChatGPT waiver). Stop condition:
draft PR "Task 013B: controlled initial inventory baseline import";
gate closes on draft-open; no other work.
```
