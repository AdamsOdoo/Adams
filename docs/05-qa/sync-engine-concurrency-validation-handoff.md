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
- Disposable databases `pbtest` (baseline), `pbscen` (scenarios), and
  `pbscen6` (Scenario-6 faithful rerun), all dropped at cleanup.
- **No** Shopify credential, token, shop connection, or Admin API call.

## Topology actually available

> **Corrected terminology (review `4950314052`).**

- **A** (single in-process instance) — used for Scenarios 1/4/5/7.
- **Process-level concurrency harness, B-like (NOT a deployed `--workers`
  Topology B)** — independent Odoo-library processes, separate PostgreSQL
  connections, one shared DB. Used for Scenarios 2/3/6/9.
- **C** (two independent `odoo-bin` server daemons, one shared DB) —
  genuinely available and used for Scenario 8, **single host only** (not
  multi-VM/Odoo.sh).

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
| 6 | Disconnect between start & handler (real `action_disconnect`) | **FAIL vs plan expectation** |
| 7 | `blocked_manual_review` cancellation | PASS |
| 8 | Multi-server drain (topology C, single host; 5 probe + 35 concurrent) | PASS |
| 9 | Crash/interruption | OBSERVATION ONLY |

**Scenarios not executed:** none — all nine were genuinely executed on a
qualifying runtime. Scenario 6 was **rerun** with the real
`action_disconnect()` after review `4950314052`.

## Defects

- **DEF-PB-1 (Scenario 6, CORRECTED after faithful rerun):** with the real
  `store.action_disconnect()`, a concurrent operator disconnect does **not**
  skip/cancel an in-flight business job. Worker B's cancellation sweep
  **blocks on the job's row lock** (held by the drain); the handler runs and
  the job `succeeds`; on unblock B hits `could not serialize access due to
  concurrent update` — the library call rolls back (store stays connected),
  the RPC call is retried by Odoo's `retrying()` and completes, cancelling
  0 jobs. **The first submission's "checkpoint-3 misses a *committed*
  disconnect" framing used a direct `store.write` substitute and is
  corrected** — retained only as a narrow snapshot OBSERVATION. Latent today
  (no-op handler); real once a domain handler does a live write. **Confirms
  SRR-03 open.** **No fix applied.** Evidence: results doc §10/§14 +
  `scenario-06-real-*`.

## Proposed risk classifications (ChatGPT decides)

- **SRR-03:** remains **OPEN** (faithful `action_disconnect` rerun: in-flight
  job not stopped by a concurrent disconnect).
- **SRR-04:** propose **REDUCED** (Scenarios 2/3 process-level harness +
  Scenario 8 two-instance: disjoint claims, no double-processing, no
  deadlock) — not closed (no deployed `--workers` server, single host,
  small scale).
- **SRR-09:** propose **REDUCED** (single-host two-instance topology C) —
  **not closed** (no multi-node/Odoo.sh evidence).

## Unresolved questions

- **Q7 (checkpoint/resume ownership):** Scenario 9a shows no recovery for a
  job stuck in `running`; needed before any per-job-commit (PERF-1) rework.
- Whether SRR-03 warrants a remediation gate before the first live-write
  domain handler (ChatGPT to decide).
- Multi-node / sustained-load / throughput (PB-19) evidence not gathered.

## Cleanup status

- All server daemons stopped (Scenario-8 pair + Scenario-6-rerun RPC
  server); no `odoo-bin` process remains; held locks released; crash
  workers killed; 0 idle-in-transaction backends.
- Shipped cron unmodified and never auto-fired (`--max-cron-threads=0`);
  all three disposable DBs dropped → no scheduled job armed, no synthetic
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
