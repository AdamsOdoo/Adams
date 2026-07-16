# Task CORE-R1 — Capability-Aware Readiness Correction: Validation Results

> **Status: implementation session record for the CORE-R1 draft PR #149
> into `Shopify-connector`.** Nothing here accepts a decision or merges
> anything. Produced 2026-07-11 by the CORE-R1 implementation session
> (initial draft PR) and its focused correction session (ChatGPT review
> `4678631974` + gate amendment `4948368039`), on branch
> `claude/task-core-r1-readiness-correction-trxl43`.

## Wave 1 integration re-verification (2026-07-15)

**[Fact]** The complete accepted CORE-R1 production change, its focused
20-method suite, both amended exact-sudo guards, AR-043, and this validation
record are already present byte-for-byte in the protected checkpoint and in the
authorized Wave 1 base. Wave 1 therefore does not duplicate or rewrite the
inherited implementation. The live base was checked at the exact
product-owner-authorized integration identity recorded in PR #172, and the
following inherited content was re-read against D-R1-1..5:

- the actual registered drain cron plus the exact 60-minute
  `state='queued' AND started_at=False` stall boundary;
- inventory-disabled and pull-based-webhook not-applicable passes, with
  inventory-enabled/no-override remaining fail-closed;
- successful non-fall-forward test connection recording
  `api_health_state='normal'` while fall-forward remains `degraded`;
- the eligible Lite-store real-behavior activation and essential-failure
  regressions;
- the source guards prohibiting readiness-time Shopify calls and credential
  reads and enforcing the narrow cron-read sudo inventory.

**[Fact]** The inherited implementation was previously Odoo.sh-green at exact
implementation head `e262738696dc18f775fcc42b5de0ef98c7b722ee`, build
`34779589`, with `0 failed, 0 error(s) of 288 tests` as recorded below.
**[Fact, updated 2026-07-16]** The mandatory final Wave 1 exact-head Odoo.sh
rerun has since completed: corrected-head build `34995642` (runtime-tested SHA
`95db3db`) ran `TestReadinessCheck` (31) and `TestReadinessSlotClosure` (20)
green as part of the full `0 failed / 0 errors / 644` standard suite recorded
in `task-sec1-validation-results.md`. This record's own §2–§7 detail below was
not re-verified against that later build and, per Wave 1's Claude control-room
review, carries known staleness in two places: §4's citation of two test
method names later renamed by the SEC-1 commit, and §6's now-superseded "exact
three sanctioned sudo sites" claim (see the note at each location). Neither
staleness reflects a code defect — the tests exist under their current names
and pass; the sudo inventory simply grew when SEC-1 added its own sanctioned
sites.

No CORE-R1 production or test code changed in this Wave 1 stage because
reimplementation would violate the repository's “do not re-implement existing
code” rule and the packet's narrow diff contract. This stage commit updates only
this packet-owned validation record.

## 1. Base verification (prerequisite gate)

| Item | Required | Observed | Result |
| --- | --- | --- | --- |
| `Shopify-connector` tip | `2bdb07cf33045a696311c420e577cbbb09cdfb38` | `2bdb07cf33045a696311c420e577cbbb09cdfb38` | ✅ match |
| Working branch base | required base SHA | branch cut from that SHA (no drift) | ✅ |
| PR #148 | merged into `Shopify-connector` | `merged: true`, 2026-07-11T18:08:27Z | ✅ |
| Gate comment `4948225529` | CORE-R1 OPEN, one session, D-R1-1..5 | read and honored | ✅ |
| Gate amendment `4948368039` | +2 sudo-guard test files, two→three sites | **consumed** (see §2, §7) | ✅ |

Read-first files consulted: `CLAUDE.md`, `CHATGPT.md`,
`docs/07-implementation-plan/task-core-r1-readiness-correction-packet.md`,
`docs/01-research/research-handoff.md`, review `4678631974`, amendment
`4948368039`.

## 2. Exact changed files (nine — packet allowlist + gate amendment `4948368039`)

| # | File | Kind | Change |
| --- | --- | --- | --- |
| 1 | `addons/shopify_connector_core/models/shopify_connector_readiness_check.py` | prod | `READINESS_QUEUE_STALL_MINUTES=60`; real `_check_cron_queue_health` (D-R1-1) + one named read-only `sudo()` helper `_drain_cron_active_state` (docstring now records the consumed amendment); capability-aware `_check_mapped_location` (D-R1-2) and `_check_webhook_hmac` (D-R1-3) |
| 2 | `addons/shopify_connector_core/models/shopify_connector_store.py` | prod | D-R1-5: `else` branch writes `api_health_state='normal'` **and** `api_health_reason=False` on full non-fall-forward `action_test_connection` success (clears stale degradation evidence on recovery) |
| 3 | `addons/shopify_connector_core/tests/test_readiness_slot_closure.py` | test (new) | 20-method suite: the 16 mandatory cases + the D-R1-5 recovery regression |
| 4 | `addons/shopify_connector_core/tests/__init__.py` | test | one import line |
| 5 | `addons/shopify_connector_core/tests/test_job_log_system_append.py` | test (amendment `4948368039`) | sudo guard renamed `…two_sudo_sites_total` → `…three_sudo_sites_total`; comment two→three; expected list now the three-site set |
| 6 | `addons/shopify_connector_core/tests/test_credential_service.py` | test (amendment `4948368039`) | `test_source_level_sanctioned_sudo_sites_guard` preserved; comment/history updated to the CORE-R1 three-site inventory; expected list now the three-site set |
| 7 | `docs/05-qa/task-core-r1-validation-results.md` | docs (new) | this record |
| 8 | `docs/05-qa/architecture-review-log.md` | docs | AR-043 row (resolved) |
| 9 | `docs/01-research/research-handoff.md` | docs | new top handoff entry |

**Final changed-file count: nine.** Files 5 and 6 are the exact two test
files newly authorized by gate amendment `4948368039`; all original
production-file restrictions are unchanged.

### Forbidden-file confirmation

- No `*.xml`, `*.csv`, `__manifest__.py`, `security/*`, `data/*`,
  `controllers/*`, `migrations/*`, `.github/workflows/*` changed
  (`git diff --name-only` filter → NONE).
- No `adams_base`, no product/sale/inventory module, no UI/webhook file.
- `_get_checks()`, `_aggregate()`, `run_for_store()`, and every
  non-target check method in the readiness model are **byte-untouched**
  (the only added `def` is `_drain_cron_active_state`).
- In `shopify_connector_store.py`, the only change is the D-R1-5 `else`
  write (now two keys); no other method, condition, state transition,
  credential, scope, identity, or lifecycle behavior changed.
- In the two guard test files, only the two global model-layer sudo AST
  guards and their directly associated names/comments/expected-lists
  changed — no fixture, credential test, job-log behavior test, ACL
  expectation, redaction test, or unrelated assertion touched (verified
  by diff: files 5/6 changed only inside the guard blocks).

## 3. Decision-by-decision implementation

**D-R1-1 — real `cron_queue_health`.** Passes only when the merged drain
cron `ir_cron_shopify_connector_job_dispatch_drain` exists and is
`active` (read through the one narrow read-only `sudo()` elevation
`_drain_cron_active_state`; connector groups hold no `ir.cron` ACL) and
no queued job for the store is stalled. Exact discriminator:
`state='queued' AND started_at is not set AND create_date older than
READINESS_QUEUE_STALL_MINUTES (60)`. `retry_count` unused. Named fail
reasons (missing / inactive / N-stalled). Area-6 scan crons not required.
Re-queued-with-history boundary honored.

**D-R1-2 — capability-aware `mapped_location`.** Reads only the core
`inventory_domain_enabled` settings flag. Disabled (or no settings) →
not-applicable **pass**; enabled without an inventory override →
fail-closed **not_proven**.

**D-R1-3 — capability-aware `webhook_hmac`.** Not-applicable **pass**
with the packet's exact reason: `Not applicable — webhook intake is not
installed; scheduled/manual sync is the active trigger mechanism.`

**D-R1-5 — healthy API state write + stale-reason clear.**
`action_test_connection` writes `{'api_health_state': 'normal',
'api_health_reason': False}` only on a fully successful, non-fall-forward
test connection. Clearing `api_health_reason` prevents a recovered store
from retaining a prior fall-forward degradation reason (contradictory
operator-facing evidence). The `'degraded'` fall-forward path, the
test-connection request, credentials, scopes, identity, and lifecycle
transitions are untouched; `_check_api_version_health` itself is
unchanged.

**D-R1-4 — required regression.** An eligible Lite store, provisioned
entirely through real merged behavior (credential service, https base
URL, product/sale flags, a real mocked-transport non-fall-forward test
connection recording scopes + `api_health_state='normal'`), runs the
real `run_for_store` (no readiness/state force-writes), aggregates
`pass`, and reaches `connected` via `action_activate()`. The negative
case (genuine missing scope) still aggregates `fail` and blocks
activation.

## 4. Tests (`tests/test_readiness_slot_closure.py`) — 20 methods

| # | Mandatory case | Test method(s) |
| --- | --- | --- |
| 1 | Active cron + empty queue → pass | `test_cron_queue_health_active_cron_empty_queue_passes` |
| 2 | Missing drain cron → named failure | `test_cron_queue_health_missing_cron_named_failure` |
| 3 | Inactive drain cron → named failure (real sudo read) | `test_cron_queue_health_inactive_cron_named_failure` |
| 4 | Queued > 60 min, no `started_at` → named failure | `test_cron_queue_health_stalled_queued_job_named_failure` |
| — | Recent queued job (< 60 min) not stalled | `test_cron_queue_health_recent_queued_job_not_stalled` |
| 5 | Dispatched/cancelled/succeeded no longer blocks | `test_cron_queue_health_dispatched_or_cancelled_job_does_not_block` |
| 6 | Re-queued w/ historical `started_at` not stalled | `test_cron_queue_health_requeued_job_with_history_not_stalled` |
| 7 | Connector-admin (no ERP-manager) runs via sudo | `test_cron_queue_health_connector_admin_runs_via_sudo_elevation` |
| 8 | Inventory disabled → not-applicable pass | `test_mapped_location_inventory_disabled_passes_not_applicable` |
| 9 | Inventory enabled, no override → not_proven | `test_mapped_location_inventory_enabled_without_override_not_proven` |
| 10 | Webhook absent → not-applicable pass, exact reason | `test_webhook_hmac_not_applicable_pass_exact_reason` |
| 11 | Non-fall-forward success → `normal` | `test_non_fallforward_success_sets_api_health_normal` |
| 12 | Fall-forward → `degraded` | `test_fallforward_success_still_sets_api_health_degraded` |
| 12b | **Recovery**: `degraded`(+reason) → `normal`, reason cleared | `test_degraded_recovers_to_normal_and_clears_reason` |
| 13 | Eligible Lite store aggregates `pass` | `test_eligible_lite_store_aggregates_pass` |
| 14 | Eligible Lite store reaches `connected` | `test_eligible_lite_store_reaches_connected` |
| 15 | Genuine essential failure still blocks activation | `test_genuine_essential_failure_still_blocks_activation` |
| 16 | Source-level guards (no Shopify call / no cred read / one named sudo / store diff scope) | `test_source_level_checks_add_no_shopify_call_or_credential_read`, `test_source_level_sec1_sudo_inventory_in_readiness` *(renamed from `test_source_level_single_named_sudo_in_readiness_helper` by SEC-1 commit `60ac416`)*, `test_source_level_store_health_and_sec1_sudo_inventory` *(renamed from `test_source_level_store_change_is_only_the_health_write`, same commit)* |

## 5. Validation actually executed (honest scope)

**No Odoo runtime exists in this session's environment**
(`python3 -c "import odoo"` → `ModuleNotFoundError`), so no Odoo
`TransactionCase` was executed locally. The following ran locally and
passed:

```text
$ python3 -m py_compile \
    addons/shopify_connector_core/models/shopify_connector_readiness_check.py \
    addons/shopify_connector_core/models/shopify_connector_store.py \
    addons/shopify_connector_core/tests/test_readiness_slot_closure.py \
    addons/shopify_connector_core/tests/test_job_log_system_append.py \
    addons/shopify_connector_core/tests/test_credential_service.py \
    addons/shopify_connector_core/tests/__init__.py
# → clean (exit 0)
```

Standalone AST replication (a Python script, not Odoo) of every
source-level guard:

- **Both updated global sudo guards** — `test_source_level_three_sudo_
  sites_total` (job-log) and `test_source_level_sanctioned_sudo_sites_
  guard` (credential): the actual sorted `.sudo()` inventory across
  `shopify_connector_core/models/*.py` was, **at this CORE-R1 correction
  commit only**, exactly
  `['shopify_connector_job_log.py',
  'shopify_connector_readiness_check.py',
  'shopify_connector_store_credential.py']` → **exact-list match (green)**.
  Exact-list equality was preserved at that commit (no `>= 3`, substring,
  wildcard, or count-only relaxation); any fourth site would have failed
  both. *(Superseded note, 2026-07-16: the subsequent SEC-1 commit
  `60ac4165a0fa9babc070f892bfdeb6dc0a2e48b5` legitimately expanded the
  sanctioned sudo surface across `shopify_connector_core/models/*.py` — e.g.
  `shopify_connector_store.py` alone now has 8 sanctioned sites — and renamed/
  re-scoped these two guard tests accordingly
  (`test_source_level_sec1_sudo_inventory_in_readiness`,
  `test_source_level_store_health_and_sec1_sudo_inventory`) rather than
  leaving them silently broken. `task-sec1-validation-results.md`'s "Exact
  core sudo inventory" entry is the current authoritative full-repo count;
  this file's three-site claim below describes CORE-R1's own commit in
  isolation, not the current shipped state.)*
- The three CORE-R1 source guards pass (no Shopify call / no credential
  read in the three edited check methods; exactly one `.sudo()` in the
  readiness model, inside `_drain_cron_active_state`; the store change is
  exactly one `api_health_state='normal'` write with the `degraded`
  write intact). *(At CORE-R1's original commit, `shopify_connector_store.py`
  had no `.sudo()` sites; SEC-1 subsequently added 8 sanctioned sudo sites to
  that file for job-state transitions unrelated to CORE-R1's own change — see
  the §6 note below.)*
- The pre-existing `test_readiness_check.py::test_source_level_no_check_
  method_mutates_state` guard **stays green** (no `_check_*` method calls
  write/create/unlink/execute/sudo).
- `test_job_dispatch.py::test_source_level_no_sudo_in_new_files` is
  unaffected (it scans only the two Task-006C files, both still sudo-free).

Static test-method inventory (`grep -cE "^\s+def test_"`), for reference
— **not** Odoo runtime counts, and superseded by the runtime totals in
the Odoo.sh section below: `test_readiness_slot_closure.py` = 20;
`test_job_log_system_append.py` = 4; `test_credential_service.py` = 15.

*(Citation correction, 2026-07-16: §4 below previously named two
`test_readiness_slot_closure.py` methods —
`test_source_level_single_named_sudo_in_readiness_helper` and
`test_source_level_store_change_is_only_the_health_write` — that SEC-1 commit
`60ac4165a0fa9babc070f892bfdeb6dc0a2e48b5` renamed to
`test_source_level_sec1_sudo_inventory_in_readiness` and
`test_source_level_store_health_and_sec1_sudo_inventory` respectively (same
underlying assertions, expanded scope). The old names no longer exist in the
test file; this note records the rename rather than restating removed lines,
since neither this file's original allowlist nor CORE-R1's own commit may be
edited retroactively.)*

### Odoo.sh runtime result — GREEN

Runtime evidence is now available (ChatGPT runtime review `4678716995`).
The Odoo.sh platform build ran the accepted implementation head
`e262738696dc18f775fcc42b5de0ef98c7b722ee` on build database
`adamsmen-claude-task-core-r1-readiness-correction-t-34779589`. Verbatim
test statistics:

```text
shopify_connector_core: 209 tests 1.61s 4046 queries
shopify_connector_product: 61 tests 1.39s 2485 queries
shopify_connector_sale: 56 tests 0.67s 1067 queries
0 failed, 0 error(s) of 288 tests when loading database 'adamsmen-claude-task-core-r1-readiness-correction-t-34779589'
```

All **209** reported `shopify_connector_core` tests completed with **no
failure and no error**; the final database result was **0 failed and 0
error(s) of 288 tests** across the three connector modules. This
satisfies OP-43 (Odoo.sh green, quoted verbatim). The build log
explicitly executed:

- `TestReadinessSlotClosure.test_eligible_lite_store_aggregates_pass` — the eligible Lite store aggregates readiness `pass`;
- `TestReadinessSlotClosure.test_eligible_lite_store_reaches_connected` — that store reaches `connected` via `action_activate()`;
- `TestReadinessSlotClosure.test_degraded_recovers_to_normal_and_clears_reason` — the D-R1-5 recovery regression (degraded→normal, `api_health_reason` cleared);
- `TestJobLogSystemAppend.test_source_level_three_sudo_sites_total` — the three-site sudo guard;
- `TestCredentialService.test_source_level_sanctioned_sudo_sites_guard` — the sanctioned sudo-sites guard;
- the complete pre-existing `shopify_connector_core` test suite.

So the Lite-store activation regression, the API-health recovery
regression, and both exact-three-site sudo guards all executed and passed
at runtime — confirming what §3–§4 describe. The `e262738…`
implementation content is unchanged by the documentation-only closure
that records this evidence.

**Non-blocking pre-existing warning.** The build emits a documentation
warning — `Unexpected indentation.` / `Block quote ends without a blank
line; unexpected unindent.` — that is non-blocking (final result 0 failed
/ 0 error) and is **not** attributed to any CORE-R1 file absent evidence;
it is not addressed here (out of CORE-R1 scope).

## 6. Confirmations required by the review

- **No Shopify API call added to any readiness check** — the three edited
  check methods reference no `shopify.connector.api.client`, call no
  `.execute(...)`, read no secret/credential (AST §16 guards + diff grep:
  NONE added). They read only local state (settings flag, this store's
  jobs, the drain cron record).
- **Sudo inventory at CORE-R1's own commit (exact, three sanctioned sites):**
  `shopify_connector_job_log.py` (`_system_append`),
  `shopify_connector_store_credential.py` (`_get_access_token`),
  `shopify_connector_readiness_check.py` (`_drain_cron_active_state`, the
  narrow read-only CORE-R1 drain-cron read). Both global guards enforced
  this exact list at that commit. **This is no longer the full-repo sudo
  inventory** — SEC-1 (commit `60ac4165a0fa9babc070f892bfdeb6dc0a2e48b5`)
  subsequently added further sanctioned sudo sites elsewhere in
  `shopify_connector_core/models/*.py` under its own guard tests; see
  `task-sec1-validation-results.md`'s "Exact core sudo inventory" entry for
  the current authoritative count. No unguarded/unaccounted site exists at
  either commit — each addition is asserted by an exact-list test.
- **Eligible Lite store reaches `connected` through real behavior** — see
  §3 D-R1-4 and tests 13/14 (no readiness/state force-writes; the
  `api_health_state='normal'` that makes readiness pass is set by the
  real test-connection path).
- **A degraded API state recovers to `normal` with its stale reason
  cleared** — the D-R1-5 write now clears `api_health_reason`, proven by
  the real-behavior recovery test (§4 12b).

## 7. Gate amendment `4948368039` — consumed (resolved)

The original packet allowlist omitted the two pre-existing "exactly two
sudo sites" AST guards, which D-R1-1's new sanctioned sudo site
invalidates. The initial draft PR flagged this rather than silently
editing forbidden files or dodging the guard. ChatGPT issued gate
amendment `4948368039`, **narrowly expanding the CORE-R1 allowlist** to
add exactly `test_job_log_system_append.py` and `test_credential_service.py`
for the two→three update. This correction session **consumed** that
amendment:

- both guards now enforce the exact three-site inventory
  (`job_log`, `readiness_check`, `store_credential`), preserving AST
  enumeration across `models/*.py`, exact-list equality, and the
  no-fourth-site invariant;
- the readiness helper docstring, this record, the AR-043 row, the
  handoff top entry, and the PR body no longer describe the guards as
  unresolved/expected-red and no further ChatGPT ruling on this point is
  outstanding.

**Out-of-scope cosmetic note (honest, not a test failure):** two
docstrings in files outside the amended allowlist still mention the old
method name in prose — `test_readiness_check.py:245` and
`test_job_dispatch.py:470`. These are non-executing references (nothing
imports/calls the renamed method by name); both files are forbidden to
edit, so they were left untouched. Neither affects any test outcome.

## 8. Rollback

Revert the single implementation PR. That restores the three readiness
slots to their former permanent-`not_proven` placeholders, removes the
`api_health_state='normal'`/`api_health_reason=False` recovery write, and
returns both sudo guards to the two-site contract. No business data,
bindings, jobs, credentials, or logs are created or destroyed by the
change or its rollback (checks are read-only; the D-R1-5 write only sets
status fields on an already-successful test connection).

## 9. Definition-of-done status

| # | DoD item | Status |
| --- | --- | --- |
| 1 | Only allowed files changed (nine; packet allowlist + amendment `4948368039`) | ✅ |
| 2 | D-R1-1..5 implemented exactly (incl. D-R1-5 stale-reason clear) | ✅ |
| 3 | Every mandatory test present + recovery regression | ✅ — executed green on the Odoo.sh build (Lite activation + recovery + both sudo guards named in §5) |
| 4 | All pre-existing core tests green | ✅ — the Odoo.sh build ran the full `shopify_connector_core` suite (209 tests) with 0 failed / 0 error; the two updated sudo guards executed and passed |
| 5 | Odoo.sh green, quoted verbatim | ✅ — build DB `adamsmen-…-34779589`: `0 failed, 0 error(s) of 288 tests`; verbatim in §5 |
| 6 | Validation record complete | ✅ (this file) |
| 7 | Architecture-review log appended/updated | ✅ (AR-043) |
| 8 | Handoff has a new top entry | ✅ |
| 9 | Draft PR opened into `Shopify-connector` | ✅ (#149) |
| 10 | Session stops after pushing the focused correction | ✅ |

All other implementation gates (Task 010B, 011B, LC-1, 012, Area 6,
SEC-1, UI, webhook, PERF-1, and every other task) remain **closed** —
none is started, authorized, or advanced by this session.
