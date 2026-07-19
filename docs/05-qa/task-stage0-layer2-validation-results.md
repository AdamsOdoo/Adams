# Wave 3 Stage 0 — DEC-031 Layer 2 Validation Results

- **Status:** IMPLEMENTATION IN PROGRESS — PRE-EDIT AUDIT COMPLETE
- **Original base:** `mvp/program-integration@3a2043cb8d45a4b9bc7bdb3ea39b58515e706da9`
- **Branch:** `sol/wave-3-stage-0-layer2`
- **Runtime candidate:** NOT FROZEN
- **Gate B synchronization:** WAITING
- **Real Shopify mutations issued:** ZERO

## 1. Identity gate

Verified before branch creation on 2026-07-19:

- PR #177 is merged at `3a2043cb8d45a4b9bc7bdb3ea39b58515e706da9`.
- `mvp/program-integration` is identical to that SHA.
- The Stage 0 branch and an open PR for it did not exist.
- PR #177 comments `5015044226`, `5015174971`, and `5015231326` exist.
- `main`, `Shopify-connector`, and both named checkpoint refs match the authorized SHAs.
- No other Wave 3 Stage 0 implementation branch or open PR was found.

## 2. Mandatory pre-edit audit

No contradiction with accepted DEC-036 was found.

| Decision area | Current owner / seam | Stage 0 implementation target | Proof target |
|---|---|---|---|
| D1–D4 durable identity/schema | `shopify_connector_job.py`; new attempt model | exact job fields; durable attempt row; immutable outcomes | schema, upgrade, immutability, uniqueness |
| D5–D7 fingerprints/idempotency/evidence | new attempt model; dispatcher wrapper | canonical SHA-256; attempt-owned key; allowlisted snapshots | canonicalization, boundary, masking |
| D8–D18 disposition/reconciliation | dispatcher registries and job transitions | shared disposition helper; linked reconciliation jobs; cap | applied/not-applied/inconclusive matrix |
| D19–D25 C1/C2/NET/C3 and crash recovery | `_drain_one`, `_recover_after_concurrency_conflict`; call-lease side-cursor precedent | mutation-only transaction path; committed C2; token-checked C3 | pooled-cursor concurrency and process-death harness |
| D26 stale-owner recovery | new dedicated sweep model and cron | bounded SKIP LOCKED recovery | duplicate-prevention and concurrent sweeps |
| D27–D29 disconnect and identity | store controller and credential clear paths | unresolved-attempt/reconciliation quiescence gate | credential preservation and force-disconnect audit |
| D30–D32 security/retention | four-role ACLs; protected writes; existing retention service | read-only ACLs; closed named write surface; mask-in-place | per-role denial; source guard; no unlink |
| D33–D38 lifecycle, registry, bypass and proof | manifest/init/test conventions; dispatcher extension seams | clean additive registration; fail-closed registry/API/AST guards | install/upgrade, regressions, zero-real-mutation proof |

### Verified current-code facts

- Job state and protected-field enforcement live in `shopify_connector_job.py`.
- Claiming uses row locks; dispatcher recovery currently assumes claimable rows and requires a mutation-aware running-owner branch.
- `_get_handlers()` and `_get_replay_policies()` are add-only extension seams in `shopify_connector_job_dispatch.py`.
- Non-mutation jobs currently execute under one per-job transaction and must remain unchanged.
- `execute_business()` is the guarded business-call surface; `_send()` is the only core HTTP POST site.
- The call-lease implementation proves a dedicated side cursor + fresh Environment + commit-before-network pattern.
- Disconnect completion/timed-out finalizers currently clear credentials based on leases only and require narrow mutation awareness.
- Generic manual-review and retry actions are owned by `shopify_connector_job.py` and `shopify_connector_job_actions.py`.
- The monthly PII retention service already exposes `run_sweep()`; mutation evidence masking will be an independent pass.
- Current ACLs use Auditor, Operator, Reviewer, and Administrator.
- Tests are registered through `tests/__init__.py`; real independent-connection patterns already exist in lifecycle/quiescence tests.

## 3. Planned proof layers

- **Layer 1:** pending.
- **Layer 2:** pending.
- **Layer 3 harness:** pending.
- **Independent Odoo.sh Layer 4:** explicitly out of scope for Sol.
- **Full connector regression:** pending.
- **Post-Gate-B synchronization regression:** blocked until control-room-authorized integration SHA.

## 4. Zero-real-mutation evidence

At this checkpoint:

- no production code changed;
- no Shopify credential was read;
- no Shopify request was made;
- no real mutation domain was registered;
- no real mutation call site was added.
