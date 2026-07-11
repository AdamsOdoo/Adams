# Task CORE-R1 — Capability-Aware Readiness Correction: Validation Results

> **Status: implementation session record for the CORE-R1 draft PR into
> `Shopify-connector`.** Nothing here accepts a decision, opens a gate,
> or merges anything. Produced 2026-07-11 by the CORE-R1 implementation
> session authorized by ChatGPT's gate act (PR #148 comment
> `4948225529`), on branch
> `claude/task-core-r1-readiness-correction-trxl43`.

## 1. Base verification (prerequisite gate)

| Item | Required | Observed | Result |
| --- | --- | --- | --- |
| `Shopify-connector` tip | `2bdb07cf33045a696311c420e577cbbb09cdfb38` | `2bdb07cf33045a696311c420e577cbbb09cdfb38` | ✅ match |
| Working branch base | required base SHA | branch cut from that SHA (no drift) | ✅ |
| PR #148 | merged into `Shopify-connector` | `merged: true`, merged 2026-07-11T18:08:27Z | ✅ |
| Gate comment `4948225529` | CORE-R1 OPEN, one session, D-R1-1..5 | read and honored | ✅ |

Read-first files consulted: `CLAUDE.md`, `CHATGPT.md`,
`docs/07-implementation-plan/task-core-r1-readiness-correction-packet.md`,
`docs/01-research/research-handoff.md` (top entry).

## 2. Exact changed files (this session)

| File | Kind | Change |
| --- | --- | --- |
| `addons/shopify_connector_core/models/shopify_connector_readiness_check.py` | prod | `READINESS_QUEUE_STALL_MINUTES=60` constant; real `_check_cron_queue_health` (D-R1-1) + one new named read-only `sudo()` helper `_drain_cron_active_state`; capability-aware `_check_mapped_location` (D-R1-2); capability-aware `_check_webhook_hmac` (D-R1-3) |
| `addons/shopify_connector_core/models/shopify_connector_store.py` | prod | D-R1-5: one `else` branch writing `api_health_state='normal'` on full non-fall-forward `action_test_connection` success |
| `addons/shopify_connector_core/tests/test_readiness_slot_closure.py` | test (new) | 16-case suite (§5) |
| `addons/shopify_connector_core/tests/__init__.py` | test | one import line |
| `docs/05-qa/task-core-r1-validation-results.md` | docs (new) | this file |
| `docs/05-qa/architecture-review-log.md` | docs | AR-043 row appended |
| `docs/01-research/research-handoff.md` | docs | new top handoff entry |

`git diff --stat` (code): `shopify_connector_readiness_check.py` (+130/−18),
`shopify_connector_store.py` (+9), `tests/__init__.py` (+1), plus the new
test file. **Every changed path is on the packet's exhaustive
allowlist.**

### Forbidden-file confirmation

- No `*.xml`, `*.csv`, `__manifest__.py`, `security/*`, `data/*`,
  `controllers/*`, `migrations/*`, `.github/workflows/*` changed
  (`git diff --name-only` filter returned NONE).
- No `adams_base`, no product/sale/inventory module file changed.
- Inside `shopify_connector_readiness_check.py`: `_get_checks()`,
  `_aggregate()`, `run_for_store()`, and every non-target check method
  (`_check_credential_test_connection`, `_check_required_scopes`,
  `_check_api_version_health`, `_check_store_identity`,
  `_check_web_base_url`, `_check_domain_flag_enablement`) are
  **byte-untouched** — the only added `def` in the diff is
  `_drain_cron_active_state`; the three edited check methods kept their
  signatures (bodies only).
- Inside `shopify_connector_store.py`: the only change is the D-R1-5
  `else` write; no other method, condition, state transition,
  credential, scope, identity, or lifecycle behavior changed (verified
  by full-file diff — the single hunk is the `else` branch).

## 3. Decision-by-decision implementation

**D-R1-1 — real `cron_queue_health`.** Passes only when (a) the merged
drain cron `ir_cron_shopify_connector_job_dispatch_drain` exists and (b)
is `active` — read through the one narrow, read-only `sudo()` elevation
`_drain_cron_active_state` (connector groups hold no `ir.cron` ACL; base
grants it to `base.group_erp_manager` only) — and (c) no queued job for
the store is stalled. Exact stall discriminator:
`state='queued' AND started_at is not set AND create_date older than
READINESS_QUEUE_STALL_MINUTES (60)`. `retry_count` is deliberately not
used. Named fail reasons: "The job-dispatch drain cron is missing.",
"The job-dispatch drain cron is inactive.", "N queued job(s) have
stalled longer than 60 minutes without starting." Area-6 scan crons are
**not** required (they do not exist). A re-queued job with a historical
`started_at` is deliberately **not** flagged.

**D-R1-2 — capability-aware `mapped_location`.** Reads only the core
`shopify.connector.store.settings.inventory_domain_enabled` flag (no
inventory-model dependency). `inventory_domain_enabled = False` (or no
settings record) → not-applicable **pass**; `= True` without an
inventory-module override → fail-closed **not_proven**.

**D-R1-3 — capability-aware `webhook_hmac`.** Returns a not-applicable
**pass** with the packet's exact reason string:
`Not applicable — webhook intake is not installed; scheduled/manual sync
is the active trigger mechanism.` No webhook model/subscription/secret/
HMAC/config implemented or read.

**D-R1-5 — healthy API state write.** `action_test_connection` writes
`api_health_state='normal'` only on a fully successful, non-fall-forward
test connection (the new `else` of the existing fall-forward branch).
The fall-forward path still writes `'degraded'`. The
`_check_api_version_health` readiness check itself is unchanged. No
change to the test-connection request, credentials, scopes, shop
identity, or lifecycle transitions.

**D-R1-4 — required regression.** `test_readiness_slot_closure.py`
provisions an eligible Lite store (core+product+sale, no inventory)
entirely through real merged behavior — credential set via the Task 002
service, https `web.base.url`, product/sale domain flags, and a real
(mocked-transport) successful non-fall-forward `action_test_connection`
that records the granted scopes and `api_health_state='normal'` — then
runs the real `run_for_store` (no readiness/state force-writes) and
proves it aggregates `pass` and reaches `connected` via
`action_activate()`. The negative case (a genuine missing required
scope) still aggregates `fail` and `action_activate()` raises
`UserError`, leaving the store not `connected`.

## 4. Tests (`tests/test_readiness_slot_closure.py`) — 18 methods, mapping the §5 mandatory list

| # | Mandatory case | Test method |
| --- | --- | --- |
| 1 | Active cron + empty queue → pass | `test_cron_queue_health_active_cron_empty_queue_passes` |
| 2 | Missing drain cron → named failure | `test_cron_queue_health_missing_cron_named_failure` |
| 3 | Inactive drain cron → named failure (real sudo read) | `test_cron_queue_health_inactive_cron_named_failure` |
| 4 | Queued > 60 min, no `started_at` → named failure | `test_cron_queue_health_stalled_queued_job_named_failure` |
| 4b | Recent queued job (< 60 min) not stalled | `test_cron_queue_health_recent_queued_job_not_stalled` |
| 5 | Dispatched/cancelled/succeeded no longer blocks | `test_cron_queue_health_dispatched_or_cancelled_job_does_not_block` |
| 6 | Re-queued w/ historical `started_at` not stalled | `test_cron_queue_health_requeued_job_with_history_not_stalled` |
| 7 | Connector-admin (no ERP-manager) runs via sudo | `test_cron_queue_health_connector_admin_runs_via_sudo_elevation` |
| 8 | Inventory disabled → not-applicable pass | `test_mapped_location_inventory_disabled_passes_not_applicable` |
| 9 | Inventory enabled, no override → not_proven | `test_mapped_location_inventory_enabled_without_override_not_proven` |
| 10 | Webhook absent → not-applicable pass, exact reason | `test_webhook_hmac_not_applicable_pass_exact_reason` |
| 11 | Non-fall-forward success → `api_health_state='normal'` | `test_non_fallforward_success_sets_api_health_normal` |
| 12 | Fall-forward → `api_health_state='degraded'` | `test_fallforward_success_still_sets_api_health_degraded` |
| 13 | Eligible Lite store aggregates `pass` | `test_eligible_lite_store_aggregates_pass` |
| 14 | Eligible Lite store reaches `connected` | `test_eligible_lite_store_reaches_connected` |
| 15 | Genuine essential failure still blocks activation | `test_genuine_essential_failure_still_blocks_activation` |
| 16 | Source-level guards (no Shopify call / no cred read / one named sudo / store diff scope) | `test_source_level_checks_add_no_shopify_call_or_credential_read`, `test_source_level_single_named_sudo_in_readiness_helper`, `test_source_level_store_change_is_only_the_health_write` |

## 5. Validation actually executed (honest scope)

**No Odoo runtime exists in this session's environment**
(`python3 -c "import odoo"` → `ModuleNotFoundError`), exactly as every
prior implementation session recorded. The following ran locally and
passed:

```text
$ python3 -m py_compile \
    addons/shopify_connector_core/models/shopify_connector_readiness_check.py \
    addons/shopify_connector_core/models/shopify_connector_store.py \
    addons/shopify_connector_core/tests/test_readiness_slot_closure.py \
    addons/shopify_connector_core/tests/__init__.py
# → clean (exit 0)
```

Standalone AST replication of every source-level guard (a Python script,
not Odoo) confirmed:

- the three new source-level guards pass: no Shopify call / no credential
  read inside the three edited check methods; exactly one `.sudo()` in
  the readiness model and it is inside `_drain_cron_active_state`; the
  store diff is exactly one `api_health_state='normal'` occurrence with
  the `degraded` write intact and no `.sudo()` in the store file;
- the pre-existing `test_readiness_check.py::
  test_source_level_no_check_method_mutates_state` guard **stays green**
  (no `_check_*` method contains write/create/unlink/execute/sudo — the
  sudo is isolated in the non-`_check_` helper);
- the pre-existing two "exactly two sudo sites" guards now observe three
  files → they **will fail** until updated (see §7).

The full runtime suite (this new file + the entire pre-existing core
suite + product/sale suites) has **NOT** been executed locally — it can
only run on the platform build.

### Odoo.sh runtime result

**Not available in this session** — this environment has no Odoo/Odoo.sh
or CI access. The live run executes on the Odoo.sh build the draft PR
triggers and **must be quoted verbatim before merge** (OP-43). I make no
runtime claim I did not execute. Expected outcome, stated honestly:
**green except for the two flagged sudo-count guards (§7), which will
report failures until the authorized 2→3 update lands.**

## 6. No-Shopify-call / single-sudo confirmations

- **No Shopify API call added to any readiness check.** The three edited
  check methods reference no `shopify.connector.api.client`, call no
  `.execute(...)`, and read no secret/credential (AST-verified §16
  tests + diff grep: NONE added). They read only local state (settings
  flag, this store's jobs, the drain cron record).
- **The cron read is the only new `sudo()` site.** Diff grep + AST scan:
  the single new `.sudo()` in the whole change is
  `_drain_cron_active_state`'s `cron.sudo().active`.

## 7. Flagged, not silently resolved: the two pre-existing sudo-count guards

**This is the one load-bearing conflict of the task, surfaced for
ChatGPT rather than silently worked around.**

The packet's D-R1-1 mandates a new `sudo()` site in the readiness model
(*"read through one narrow, read-only `sudo()` elevation … the only new
sudo site in the task"*; audit §8.6 records it as *"named, flagged
read-only sudo elevation added to D-R1-1 and the release-plan §2.8
inventory"*). Adding it raises the `models/` directory `.sudo()` count
from two to three. Two pre-existing AST guards hard-code "exactly two
sudo sites" and are **outside the packet's exhaustive allowlist**:

1. `tests/test_job_log_system_append.py::test_source_level_two_sudo_sites_total`
2. `tests/test_credential_service.py::test_source_level_sanctioned_sudo_sites_guard`

Both assert exactly
`['shopify_connector_job_log.py', 'shopify_connector_store_credential.py']`
and comment *"Any third site is a review failure — this guard must not
be weakened."* They therefore go stale/red the moment D-R1-1 is
implemented.

**Why this could not be resolved in-scope:**

- Editing those two guard files is a forbidden-file change (exhaustive
  allowlist; *"do not modify a forbidden file even to clean up"*;
  CHATGPT.md §13 *"never allow code drift beyond authorized files"*).
- Dropping the cron read would violate D-R1-1's pass conditions and make
  the check raise `AccessError` for the real connector-admin user.
- Reaching the elevation via `with_user(SUPERUSER_ID)`/`with_env(su=True)`
  to dodge the counter was rejected as deceptive: it contradicts the
  packet's explicit `sudo()` instruction and defeats the guard's stated
  purpose of enumerating elevation sites.

**Consequence:** the DoD is internally unsatisfiable as written for
D-R1-1 ("only allowed files changed" vs "all pre-existing core tests
remain green"). Per the project's own precedent — Task 003's handoff
records that when it added the *second* sudo site and made a
then-single-site guard stale, it *"flagged, not silently resolved"* the
conflict and *"deliberately left [the forbidden file] untouched"* — this
session did the same: implemented D-R1-1 correctly, isolated the sudo in
a named helper (so only these two count-guards, not the `_check_*`
mutation guard, are affected — minimal blast radius), left both forbidden
guard files untouched, and flags them here.

**Requested ChatGPT ruling (one of):**

1. **Recommended** — authorize the trivial 2→3 update: add
   `test_job_log_system_append.py` + `test_credential_service.py` to the
   CORE-R1 allowlist so both guards list all three files
   (`…job_log.py`, `…readiness_check.py`, `…store_credential.py`),
   restoring green; or
2. accept the flagged-stale posture and update the guards in a follow-up
   authorized patch; or
3. amend the packet (e.g. a different sanctioned elevation mechanism).

Until then, the two guards are the *only* pre-existing core tests this
change disturbs; all other pre-existing readiness/store/dispatch tests
remain green by construction (see §5 and the AST analysis).

## 8. Rollback

Revert the single implementation PR. That restores the three readiness
slots to their former permanent-`not_proven` placeholder behavior and
removes the `api_health_state='normal'` write (stores return to the
pre-CORE-R1 cannot-reach-`connected` state). No business data, bindings,
jobs, credentials, or logs are created or destroyed by this change or its
rollback (all check methods are read-only; the D-R1-5 write only sets an
existing status field on an already-successful test connection).

## 9. Definition-of-done status

| # | DoD item | Status |
| --- | --- | --- |
| 1 | Only allowed files changed | ✅ (see §2) |
| 2 | D-R1-1..5 implemented exactly | ✅ (see §3) |
| 3 | Every mandatory test present | ✅ (see §4; runtime execution pending platform build) |
| 4 | All pre-existing core tests green | ⚠️ **blocked by §7** — two count-guards go 2→3; needs ChatGPT ruling |
| 5 | Odoo.sh green, quoted verbatim | ⏳ pending platform build (no CI in this env; §5) |
| 6 | Validation record complete | ✅ (this file) |
| 7 | Architecture-review log appended | ✅ (AR-043) |
| 8 | Handoff has a new top entry | ✅ |
| 9 | Draft PR opened into `Shopify-connector` | ✅ (on session close) |
| 10 | Session stops immediately after draft PR | ✅ |

All other implementation gates (Task 010B, 011B, LC-1, 012, Area 6,
SEC-1, UI, webhook, PERF-1, and every other task) remain **closed** — none
is started, authorized, or advanced by this session.
