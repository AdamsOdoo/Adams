# Task CORE-R1 — Capability-Aware Readiness Correction: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §8 is NOT usable.** Produced 2026-07-11 by the PR #148
> revision session, implementing review item 5 of ChatGPT's control-room
> review (PR #148 comment `4942966937`): the critical readiness
> correction formerly bundled as Area-6 design item D-A6-7 is split out
> as its own tiny, independently gated core task, sequenced **before**
> Task 010B/011B/012 live use. The Area-6 packet
> (`area-6-sync-triggers-implementation-packet.md`) is revised in the
> same PR to hand this ownership over and keep only the
> trigger/enumeration/job-action scope. Evidence: merged core code
> (read 2026-07-10 and re-read 2026-07-11) and the 2026-07-11 captures
> (`../00-source-materials/odoo19-shopify-official-captures-2026-07-11.md`).

## 1. The defect being corrected (verified against merged code, 2026-07-11)

**[Fact — merged repository state]** The merged core registers nine
readiness checks, all ESSENTIAL
(`shopify_connector_readiness_check.py`, `_get_checks()` lines
163–183). Three of them are placeholders that return `not_proven`
unconditionally (lines 320–352): `webhook_hmac`, `mapped_location`,
`cron_queue_health`. The aggregate is fail-closed — any ESSENTIAL
check `!= pass` forces overall `fail` (`_aggregate`, lines 132–157) —
and `action_activate` / `action_reconnect` require
`last_readiness_result in ('pass','warning')`
(`shopify_connector_store.py` lines 305–310, 432–435). Consequence:
**no store can ever reach `connected` on the merged code**, so no
dev-store validation, no VAL-B2 connected-state evidence, and no live
validation of Tasks 010B/011B/012 can occur. This is the red-team
BLOCKER finding recorded in `mvp-planning-completion-audit.md` §7.1
item 1, now given its own minimal task per the review.

## 2. Objective, scope, non-goals

Make readiness **capability-aware**: a check may require only what the
installed module set and per-store enabled domains actually provide;
no unrelated capability may prevent store activation; and the
cron/queue slot verifies **real** scheduler/queue health instead of
returning a permanent `not_proven`. **Non-goals:** no trigger/scan/
cron additions (Area 6); no new checks beyond the three named slots;
no change to the aggregate algorithm, activation rules, store
lifecycle, job model, dispatcher, ACLs, or any other core file; no UI;
no Shopify calls added to any check.

## 3. Decision closures (D-R1-1 … D-R1-4) — each Proposed

**D-R1-1 — `cron_queue_health` becomes a real, capability-aware
check.** Pass conditions, evaluated with no Shopify call and no
secret: (a) the merged core drain cron
(`ir_cron_shopify_connector_job_dispatch_drain`, the only cron that
exists today — `data/shopify_connector_cron_drain.xml`) exists and is
`active` — **read via a named, narrow `sudo()` elevation
(red-team-added 2026-07-11 round 2): connector groups hold no
`ir.cron` ACL (base grants it to `base.group_erp_manager` only —
re-verify at gate), and readiness runs as the invoking user, so the
cron-record read raises `AccessError` without elevation; this is a
new sanctioned read-only sudo site, itemized for the release plan
§2.8 inventory and flagged as part of this packet's acceptance**;
(b) no `queued` job for the store is older than the stall threshold
(`READINESS_QUEUE_STALL_MINUTES = 60`, module constant, adjustable)
that has never started — **exact discriminator (red-team-corrected
round 2): `state='queued' AND NOT started_at`** (`retry_count` counts
scheduled retries, not attempts, and stays 0 after a first failed
attempt — it must not be used; boundary stated honestly: a job
re-queued by Area-6 manual retry keeps its historical `started_at`
and is deliberately NOT flagged by this check — stalls of re-queued
jobs surface through the Sync Center age columns, not readiness).
Fail with a named reason otherwise (`drain cron missing/inactive` or
`N queued job(s) stalled > 60 min`). **Capability-aware rule:** the check verifies
only crons that are actually registered — it must NOT require the
Area-6 domain scan crons (they do not exist yet); when Area 6 later
ships them, its packet may extend this check via `_inherit` to also
verify the scan crons of enabled domains (the Area-6 packet §2 now
records that as its follow-on, not its ownership).

**D-R1-2 — `mapped_location` becomes conditionally applicable.** When
the store's `inventory_domain_enabled` settings flag is False: pass
with reason "not applicable — inventory domain not enabled for this
store" (reads the same core settings flag
`_check_domain_flag_enablement` already reads; no domain-model
dependency). When True and no inventory module has overridden the
check: remain `not_proven` (fail-closed — an inventory-enabled store
without the inventory module must not activate). Task 013 replaces
the evaluation via `_inherit` override with the real mapped-location
verification (its packet already cites this baseline).

**D-R1-3 — `webhook_hmac` becomes conditionally applicable, same
pattern.** The accepted MVP trigger architecture is pull-based; W1 is
the MVP tail. Core check passes with reason "not applicable — webhook
intake is not installed; scheduled/manual sync is the active trigger
mechanism"; the W1 packet owns replacing it (via `_inherit`) with the
real HMAC-configuration + subscription-state verification when the
webhook module installs. **Flagged prominently for ChatGPT
(unchanged from D-A6-7): this relaxes a fail-closed pending slot to a
not-applicable pass.** Rejecting this sub-proposal means no store
activates until W1 ships — a sequencing decision ChatGPT must make
explicitly, not inherit silently.

**D-R1-4 — No-unrelated-capability invariant, stated as a testable
rule.** After this task, the set of ESSENTIAL checks evaluated against
a store must be exactly: the six real merged checks
(credential/scopes/api-version/identity/base-url/domain-flag) plus
`cron_queue_health` (real, D-R1-1) plus any conditional check whose
capability is installed **and** enabled for that store. A Lite store
(core+product+sale, no inventory/fulfillment/export/webhook modules)
with verified credential, granted read scopes, healthy API version,
https base URL, ≥1 enabled domain, active drain cron, and no stalled
queue **must aggregate to `pass`** and must be able to reach
`connected` via `action_activate` — **with real merged behavior, not
test-fixture force-writes**. This is the mandatory regression test
(§5) — the review's "eligible Lite store can reach `connected`"
requirement made executable.

**D-R1-5 — The fourth never-passable slot: `api_version_health`
(red-team round-2 BLOCKER fix — without this, D-R1-4 is
unsatisfiable on real behavior).** **[Fact — merged code]**
`_check_api_version_health` passes only on
`api_health_state == 'normal'` and returns `not_proven` when unset
(`shopify_connector_readiness_check.py` lines 264–284), but **no
merged code path ever writes `'normal'`** — the only writer sets
`'degraded'` on fall-forward (`shopify_connector_store.py` lines
193–201) and the field has no default; a fully successful test
connection leaves it NULL, so real readiness still aggregates `fail`
even after D-R1-1..3. **Fix (one named store-file write site,
flagged):** `action_test_connection` sets
`api_health_state = 'normal'` on a fully successful, non-fallforward
test connection (the state a healthy store is in); the `'degraded'`
path is untouched. *Alternative considered (named, rejected as
primary):* a readiness-file-only inference (pass when unset AND
`last_test_connection_result == 'pass'`) — rejected because it makes
the mirror field permanently meaningless; ChatGPT may choose it at
acceptance if the store-file edit is judged out of bounds for this
task.

## 4. Allowed / forbidden files (exhaustive)

**Allowed:**
- `addons/shopify_connector_core/models/shopify_connector_readiness_check.py`
  — ONLY the three named placeholder check methods
  (`_check_webhook_hmac`, `_check_mapped_location`,
  `_check_cron_queue_health`) plus the one stall-threshold constant;
  nothing else in the file (the file's own docstrings describe the
  slots as "registered pending check slot only", i.e. designed to be
  filled).
- `addons/shopify_connector_core/models/shopify_connector_store.py`
  — ONLY the one D-R1-5 write site inside `action_test_connection`
  (`api_health_state='normal'` on full success without fall-forward);
  nothing else in the file (red-team round-2 addition, flagged).
- `addons/shopify_connector_core/tests/test_readiness_slot_closure.py` (NEW)
  + `addons/shopify_connector_core/tests/__init__.py` (one import line)
- `docs/05-qa/task-core-r1-validation-results.md` (NEW)
- `docs/05-qa/architecture-review-log.md` (append one AR row)
- `docs/01-research/research-handoff.md` (top entry)

**Forbidden:** every other file — explicitly including
`_get_checks()`, `_aggregate()`, `run_for_store()`, every other store
lifecycle method and line, the job/dispatch/log models, ACL files,
cron data files, all domain modules, all views, `adams_base`,
CI/workflows, `main`, plain `dev`.

## 5. Tests (exact file: `test_readiness_slot_closure.py`)

1. `cron_queue_health` passes with active drain cron + empty queue;
   fails with named reason when the cron record is deactivated; fails
   when a `queued` job older than the threshold with `started_at`
   unset exists; passes again when that job is dispatched or
   cancelled; the sudo-elevated cron read works for a
   connector-admin (non-ERP-manager) user; a re-queued job with
   historical `started_at` is not flagged (documented boundary).
2. `mapped_location`: not-applicable pass when
   `inventory_domain_enabled=False`; `not_proven` (fail-closed) when
   True without an inventory override.
3. `webhook_hmac`: not-applicable pass with the exact reason string.
4. **BLOCKER regression (D-R1-4):** a fully configured Lite store —
   whose `api_health_state` became `'normal'` through the real
   D-R1-5 test-connection path, not a fixture force-write —
   aggregates `pass` and reaches `connected` via `action_activate`;
   negative variant: the same store with a failing essential check
   (e.g. missing scope) still cannot activate — fail-closed behavior
   preserved.
5. **D-R1-5:** successful non-fallforward test connection writes
   `api_health_state='normal'`; the fall-forward path still writes
   `'degraded'`; `_check_api_version_health` behavior itself is
   unchanged (its file is not edited).
6. Source-level guards: no Shopify call and no credential read inside
   any of the three check methods (string/AST scan; the D-R1-1 cron
   read is the one named sudo); no change to any other method in
   either edited file (diff-scope test note in the validation
   record).

## 6. Gate criteria (15-pattern instantiated, abbreviated)

1 merged core runtime-green ✅(fact); 2–3 exact names ✅(§3);
4 files ✅(§4); 5 thresholds fixed ✅(D-R1-1); 6–8 no
trigger/UI/webhook/domain scope ✅; 9 tests ✅(§5); 10 rollback ✅
(single-PR revert returns the three placeholders — documented, no
data loss; stores return to cannot-activate); 11 no live-Shopify
dependency ✅ (checks read local state only); 12 gate-act
reconfirmation (ChatGPT); 13 the three flagged calls explicitly
accepted: the webhook_hmac relaxation (D-R1-3), the D-R1-5
`api_health_state` write site (or its named readiness-inference
alternative), and the D-R1-1 sudo-elevated cron read; 14 the
capability-aware invariant stated ✅(D-R1-4); 15 fail-closed cases
enumerated ✅(§5.2/§5.4).

## 7. Acceptance criteria / DoD / rollback / sequencing

Only §4 files changed; all §5 tests green locally and on Odoo.sh
(verbatim quote, OP-43); the D-R1-4 regression green; no other
readiness behavior changed; validation record + AR row + handoff;
draft PR; gate closes on draft-open. Rollback: revert the single PR.
**Sequencing (binding once accepted):** CORE-R1 is step 1 of the
revised critical path (`../08-release-readiness/implementation-ready-master-plan.md`
§2) — before Task 010B, because 010B's dev-store validation and every
later live validation require a store that can reach `connected`.

## 8. Locked final implementation prompt (Task CORE-R1)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE CORE-R1 GATE, VERIFIES THE CURRENT BASE SHA, AND
ISSUES THIS PROMPT.

Implement Task CORE-R1 — capability-aware readiness correction —
exactly per
docs/07-implementation-plan/task-core-r1-readiness-correction-packet.md
(D-R1-1..5 binding). Branch from the verified current
Shopify-connector tip (STOP if it does not match the SHA ChatGPT
states when issuing this prompt). One session; draft PR; stop.

ALLOWED FILES (exhaustive):
  addons/shopify_connector_core/models/shopify_connector_readiness_check.py
    (ONLY _check_webhook_hmac, _check_mapped_location,
    _check_cron_queue_health + the READINESS_QUEUE_STALL_MINUTES
    constant — nothing else in the file)
  addons/shopify_connector_core/models/shopify_connector_store.py
    (ONLY the D-R1-5 api_health_state='normal' write inside
    action_test_connection on full non-fallforward success —
    nothing else in the file)
  addons/shopify_connector_core/tests/test_readiness_slot_closure.py (NEW)
  addons/shopify_connector_core/tests/__init__.py (one import line)
  docs/05-qa/task-core-r1-validation-results.md (NEW)
  docs/05-qa/architecture-review-log.md (append one AR row)
  docs/01-research/research-handoff.md (top entry)
FORBIDDEN: everything else — incl. _get_checks/_aggregate/
run_for_store, every other store method/line, job/dispatch/log
models, ACLs, crons, domain modules, views, adams_base, CI, main,
plain dev.

IMPLEMENT exactly: D-R1-1 real cron_queue_health (drain cron active —
read via the ONE named sudo elevation — + no stalled queued job
> 60 min using the exact discriminator state='queued' AND NOT
started_at, named fail reasons, no scan-cron requirement); D-R1-2
mapped_location not-applicable pass when inventory_domain_enabled is
False, not_proven when True without an inventory override; D-R1-3
webhook_hmac not-applicable pass with the exact packet reason string;
D-R1-5 api_health_state='normal' on full non-fallforward
test-connection success (degraded path untouched); D-R1-4
regression: a fully configured Lite store — via real behavior, no
fixture force-writes — aggregates pass and reaches connected via
action_activate, and fail-closed behavior is preserved for every
real failure. No Shopify call, no credential read, in any check.
All §5 tests.

Runtime: full Odoo.sh run green before merge review (verbatim quote;
OP-43 rule). Stop condition: open the PR as DRAFT titled "Task
CORE-R1: capability-aware readiness correction", update handoff +
validation record + AR row, and stop. The CORE-R1 gate closes the
moment the draft PR opens. Do not start Task 010B/011B/012, Area 6,
UI, webhook, or any other work under any circumstance.
```
