# Sync-Engine Concurrency Validation — Dedicated Handoff (Session P-B)

> Dedicated handoff for the **P-B** parallel evidence-only session. Used
> instead of editing the shared `research-handoff.md`, so this branch
> cannot conflict with the other authorized parallel sessions (A = Task
> 010B, B = Task 011B, C = U0). ChatGPT reviews the draft PR and makes the
> final risk classification.

## Authorization

- Gate comment: **PR #148 comment `4948925313`** — P-B concurrency
  validation execution gate, OPEN for one parallel evidence-only session.

## Verified base

- Required `Shopify-connector` tip: **`f9c3c5fd25af3f94ee71cc2ead3821e7da85443d`**
- Confirmed: `origin/Shopify-connector` == working-branch HEAD ==
  required SHA (no drift).
- Branch: **`claude/sync-engine-concurrency-validation-92r4nc`** (branched
  from the verified base; the session's designated branch).

## Runtime environment

- Disposable local install in this session's ephemeral container (NOT
  production/staging, NO customer data).
- Odoo **19.0** (`odoo/odoo` @ `c5f1a963`), Python 3.11.15,
  PostgreSQL 16.14 (`127.0.0.1:5433`, initdb'd this session), `nproc=4`.
- Disposable databases `pbtest` (baseline) and `pbscen` (scenarios),
  dropped at cleanup.
- **No** Shopify credential, token, shop connection, or Admin API call.

## Topology actually available

- **A** (single instance) and **B** (multiple separate OS processes,
  shared DB) — genuinely available and used.
- **C** (two independent `odoo-bin` server daemons, one shared DB) —
  genuinely available and used, **single host only** (not multi-VM/Odoo.sh).

## Baseline automated-test result

- `shopify_connector_core: 209 tests 1.75s` / **`0 failed, 0 error(s) of
  187 tests`**; exit code 0; no install/registry failure.
- Only `shopify_connector_core` tests ran (`--test-tags`); **no
  branch/domain modules installed** (product/sale/adams_base all
  `uninstalled`).

## Scenarios executed / classification

| # | Scenario | Result |
| --- | --- | --- |
| 1 | Single drain baseline | PASS |
| 2 | Concurrent cron workers | PASS |
| 3 | Skipped locked rows | PASS |
| 4 | `retry_waiting` due jobs | PASS |
| 5 | Disconnect before claim | PASS |
| 6 | Disconnect between start & handler | **FAIL (defect DEF-PB-1)** |
| 7 | `blocked_manual_review` cancellation | PASS |
| 8 | Multi-server drain (topology C, single host) | PASS |
| 9 | Crash/interruption | OBSERVATION ONLY |

**Scenarios not executed:** none — all nine were genuinely executed on a
qualifying runtime.

## Defects

- **DEF-PB-1 (Scenario 6):** checkpoint-3's `store.invalidate_recordset();
  store.state` re-check does **not** observe a concurrently-committed
  disconnect, because every Odoo 19 cursor runs at REPEATABLE READ
  (`odoo/sql_db.py:373`) and the drain is one snapshot. The job is not
  skipped and the (no-op) handler runs → `succeeded`. Latent today
  (no live-write handler); real once a domain handler writes to Shopify.
  Consistent with the docstring's "narrows, never closes"; **confirms
  SRR-03 is open**. **No fix applied** (forbidden). Full evidence in the
  results doc §10/§14.

## Proposed risk classifications (ChatGPT decides)

- **SRR-03:** remains **OPEN**, now runtime-confirmed (see DEF-PB-1).
- **SRR-04:** propose **REDUCED** (Scenarios 2/3/8: disjoint claims, no
  double-processing, no deadlock) — not closed (single host, small scale).
- **SRR-09:** propose **REDUCED** (single-host two-instance topology C) —
  **not closed** (no multi-node/Odoo.sh evidence).

## Unresolved questions

- **Q7 (checkpoint/resume ownership):** Scenario 9a shows no recovery for a
  job stuck in `running`; needed before any per-job-commit (PERF-1) rework.
- Whether SRR-03 warrants a remediation gate before the first live-write
  domain handler (ChatGPT to decide).
- Multi-node / sustained-load / throughput (PB-19) evidence not gathered.

## Cleanup status

- Both server daemons stopped; no `odoo-bin` process remains; held lock
  released; crash workers killed; 0 idle-in-transaction backends.
- Shipped cron unmodified and never auto-fired (`--max-cron-threads=0`);
  both disposable DBs dropped → no scheduled job armed, no synthetic
  store/token/credential anywhere.

## Confirmations

- **No shared files changed.** Only three new paths were added:
  `docs/05-qa/sync-engine-concurrency-validation-results.md`,
  `docs/05-qa/evidence/sync-engine-concurrency/**`, and this handoff. No
  existing repo file was edited; the shared `research-handoff.md` was
  **not** touched.
- **Sessions A (Task 010B), B (Task 011B), and C (U0) were not touched** —
  no branch, cherry-pick, or dependency on their work; no unmerged
  domain handler was tested; only the already-merged core dispatcher was
  validated.
- **All implementation gates remain closed.** This session authorizes no
  domain sync, no code change (including any DEF-PB-1 fix), and opens no
  gate. The draft PR is evidence/documentation only.

## Next step

ChatGPT reviews the draft PR (`QA: execute sync-engine concurrency
validation`, base `Shopify-connector`), classifies SRR-03/04/09, and
decides whether DEF-PB-1 warrants a separate remediation gate. Do not
merge or mark ready without ChatGPT review.
