# PR #204 — Odoo.sh qualification correction: activation readiness test (2026-07-31)

**Scope: test-only.** This record documents a single candidate-owned test
defect and its correction. No production code changed.

| Field | Value |
| --- | --- |
| Starting head | `a2822a32664e4c5dfc7f4daaab56b0fa4d950625` (`fable/wave-5-completion`) |
| Required base ancestor | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (verified ancestor after deepening a shallow clone) |
| Odoo pin | `30bde9ff758834a4912c5ae55843d3a7dad849f1`, cloned and verified this session |
| Odoo.sh build/database that reproduced the failure | `adamsmen-fable-wave-5-completion-35739600` |
| Odoo.sh candidate | `a2822a32664e4c5dfc7f4daaab56b0fa4d950625` |
| Odoo.sh platform Odoo | `19.0 @ f7d322a7c3d27467f997e63fcb1d9b952373ff2b` |
| Shopify | `shopify_operations = none` — no store, credential, request, mutation or webhook |

## The reproduced failure

`TestSetupWizardActivation.test_activation_is_refused_before_readiness_has_run`
failed three times on the genuine Odoo.sh build/database above:

```
AssertionError: UserError not raised
```

## Root cause — exact source references

`addons/shopify_connector_core/models/shopify_connector_setup_wizard.py`,
`activate()` (lines ~1622–1637): whenever `store.credential_present` is true,
activation unconditionally reruns
`shopify.connector.readiness.check.run_for_store(store)` *before* checking
`readiness['ran']` / `blocking` / `waiting`. This is intended and
safety-preserving: the review step can be sat on across tabs/sessions, and
production must re-prove readiness against the live configuration rather than
trust a stale operator action.

`addons/shopify_connector_core/models/shopify_connector_readiness_check.py`,
`_check_web_base_url()` (lines ~415–433): the essential `web_base_url` check
passes only when `web.base.url` starts with `https://`.

The old test built a store via `_ready_store()` (credential saved, Test
Connection passed) but **never called `_make_readiness_passable()`**, so
`web.base.url` was whatever the test server's default is:

- **Locally (bare test server):** default `web.base.url` is plain HTTP. The
  essential `web_base_url` check fails, `activate()`'s rerun produces a
  blocking result, and `UserError` is raised — the test passed, but for a
  reason that has nothing to do with whether the `final_readiness` step had
  run.
- **On genuine Odoo.sh:** `web.base.url` is a real HTTPS address. That
  essential check passes, the rerun's other essential checks also pass
  (credential test-connection, granted scopes, API health, store identity —
  all satisfied by `_ready_store()`'s own fixture), the only failing check is
  `domain_flag_enablement` which is **WARNING tier, not essential** (no
  domain was enabled) — so the aggregate is `warning`, not `fail`,
  `readiness['blocking']` is empty, and `activate()` proceeds to
  `action_activate()`. No `UserError` is raised. The old assertion was wrong
  on the accepted production invariant, not the other way around.

**Accepted production invariant (unchanged, not modified by this session):**
activation always re-runs readiness server-side from real stored evidence
when a credential is present, and may proceed if that rerun genuinely passes
— regardless of whether the operator explicitly executed the `final_readiness`
wizard step beforehand.

## Exact test-only change

File: `addons/shopify_connector_core/tests/test_setup_wizard.py` (only file
changed, besides this record).

Replaced `test_activation_is_refused_before_readiness_has_run` with
`test_activation_re_runs_readiness_when_the_step_was_not_run`, in
`TestSetupWizardActivation`. The replacement:

1. Calls `_make_readiness_passable()` (existing helper — sets a real HTTPS
   `web.base.url`) and builds a store via the real `_ready_store()` fixture
   (real `save_store_identity` / `save_credential` / `run_test_connection`
   wizard routes).
2. Asserts, from real stored state and *before* activation — not a fabricated
   payload — that the `final_readiness` step has not run:
   `settings.setup_wizard_step_key != 'final_readiness'` and
   `store.last_readiness_at` is falsy.
3. Invokes the real `shopify.connector.setup.wizard.activate(store.id)`.
4. Wraps the call in a strict guard on the lowest existing transport seam
   (`Client._send`, the same seam the rest of the suite already uses) that
   raises `AssertionError` if Shopify is contacted at all. `activate()`,
   `run_for_store()`, the readiness payload and the pass/fail decision are
   never patched.
5. Asserts genuine readiness evidence was produced through the real
   `run_for_store` route: `store.last_readiness_at` is now truthy, and one
   new `core_readiness_check` job exists for the store.
6. Asserts the store reached `connected` only because the resulting checks
   passed (`last_readiness_result` in `('pass', 'warning')`), and that no
   queued/running domain job was admitted.
7. **Load-bearing without editing production code:** if `activate()`'s
   server-side rerun were removed, `last_readiness_at` would still be falsy
   at call time, `readiness['ran']` would be `False`, and `activate()` would
   raise `UserError` at the (unwrapped) call site — failing this test at that
   line rather than downstream.

All other tests in `TestSetupWizardActivation` and the rest of the file are
untouched: essential-check blocking
(`test_activation_is_refused_while_an_essential_check_fails`), waiting-checks
blocking (`test_activation_is_refused_while_readiness_is_waiting`,
`TestSetupWizardReadinessPresentation`), no-sync-on-activation
(`test_activation_starts_no_sync_and_writes_nothing_to_shopify`),
connect-only activation
(`test_a_genuine_connect_only_store_can_activate`), and completion audit
(`test_completion_is_audited_with_the_actor`) all still exist and pass.

## Validation

Odoo pin `30bde9ff758834a4912c5ae55843d3a7dad849f1`, Python 3.12.3,
PostgreSQL 16.13, Chromium 141.0.7390.37 (headless, `--no-sandbox`). All runs
against a shallow clone of `odoo/odoo` fetched to the exact pin and verified
before use.

**Caveat, stated honestly:** these four passes ran against the working tree
containing exactly the test-only diff described above, immediately before it
was committed unchanged — the driver script correctly flags this as
`connector_worktree_dirty: true` / "not exact-SHA evidence" against the
starting head, because the diff is not yet a commit at run time. No further
edit was made to the tested file between validation and the commit below, so
the committed content is byte-identical to what these results describe.

| # | Command | Result |
| --- | --- | --- |
| 1. Replacement test alone | `odoo-bin -c odoo.conf -d connector_focus_base -i shopify_connector_core,shopify_connector_product,shopify_connector_sale,shopify_connector_inventory,shopify_connector_fulfillment,shopify_connector_product_export,account,stock --stop-after-init --log-level=test --test-tags "/shopify_connector_core:TestSetupWizardActivation.test_activation_re_runs_readiness_when_the_step_was_not_run"` (fresh install) | **0 failed, 0 error(s) of 1 tests** |
| 2. Complete `TestSetupWizardActivation` | `odoo-bin -c odoo.conf -d connector_focus_base -u shopify_connector_core --stop-after-init --log-level=test --test-tags "/shopify_connector_core:TestSetupWizardActivation"` | **0 failed, 0 error(s) of 6 tests** (all 6 methods ran) |
| 3. Complete `test_setup_wizard.py` (all 10 classes) | same, `--test-tags` = comma-separated `/shopify_connector_core:ClassName` for `TestSetupWizardShape,TestSetupWizardAuthorization,TestSetupWizardSteps,TestSetupWizardProgress,TestSetupWizardActivation,TestSetupWizardRerun,TestSetupWizardSemanticProgress,TestSetupWizardConditionalLocationStep,TestSetupWizardReadinessPresentation,TestSetupWizardSourceGuards` | **0 failed, 0 error(s) of 80 tests** |
| 4. Standard connector-suite pass, all six module selectors | `PGHOST=/var/run/postgresql PGPORT=5432 PGUSER=root ODOO_SRC=.../.odoo-src ARTIFACT_DIR=.../ci-artifacts-full SOURCE_HEAD_SHA=a2822a3266... bash tools/run_connector_suite.sh --fresh-only` (fresh install of `shopify_connector_core,shopify_connector_product,shopify_connector_sale,shopify_connector_inventory,shopify_connector_fulfillment,shopify_connector_product_export` + `account,stock`) | **0 failed, 0 error(s) of 2436 tests**; **36/36 required tour success markers reconciled**; **1 sanctioned skip** (`TestMutationRecovery.test_real_process_death_harness`, matching the documented allowance) and **no unexpected skip**; script exit code 0; `docs/05-qa/evidence` not touched — full machine-readable summary at the run's own `summary.json` (not committed; local artifact only) |

Per the instruction's explicit carve-outs for a test-only session: no
migration pass was run (`--fresh-only` sets `RUN_WARM=0 RUN_NONSTANDARD=0
RUN_MIGRATION=0`), no visual-evidence regeneration, and no HOOT /
non-standard performance or concurrency campaign (`browser_evidence: "partial:
tours verified, HOOT not executed; single-pass mode"` in the run's
`summary.json` — expected and correct for this scope, not a defect).

**Evidence class: local/CI-grade supporting evidence only — NOT Odoo.sh
exact-SHA qualification (DEC-041 D8), NOT live-Shopify validation, NOT UAT.**

## Git action

- Changed paths: `addons/shopify_connector_core/tests/test_setup_wizard.py`
  and this record only.
- No production code changed: no model, service, job, transport, security,
  migration, JavaScript, XML, CSS or manifest file is in the diff.
- `tools/run_connector_suite.sh` and `tools/odoo-pin.txt` untouched.
- Final commit/head: recorded in the commit that accompanies this file; see
  the pushed `fable/wave-5-completion` branch tip.
- Zero live Shopify contact: `shopify_operations = none`.

## What remains — explicitly not started or authorized here

Odoo.sh requalification of the exact head this correction produces, and
Shopify UAT, were **not started and are not authorized by this session**.
This record is a test-only qualification-blocker correction; it does not
review, accept, ready-mark, self-accept, or merge PR #204, and it does not
advance any later gate (X-EXPORT-0, M-EXP-1–20, UAT, or any deferred
architecture reopening).
