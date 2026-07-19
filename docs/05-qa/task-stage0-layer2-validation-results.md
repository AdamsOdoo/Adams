# Wave 3 Stage 0 — DEC-031 Layer 2 Validation Results

- **Status:** IMPLEMENTATION COMPLETE — WAITING FOR GATE B MERGE SYNC
- **Original base:** `mvp/program-integration@3a2043cb8d45a4b9bc7bdb3ea39b58515e706da9`
- **Branch:** `sol/wave-3-stage-0-layer2`
- **Draft PR:** #178
- **Runtime candidate:** NOT FROZEN
- **Gate B synchronization:** WAITING — PR #179 is proposed/draft, not accepted or merged
- **Real Shopify mutations issued:** ZERO

## 1. Identity gate

Verified before branch creation on 2026-07-19 and rechecked before this
checkpoint:

- PR #177 is merged at `3a2043cb8d45a4b9bc7bdb3ea39b58515e706da9`.
- `mvp/program-integration` is identical to that SHA.
- PR #177 comments `5015044226`, `5015174971`, and `5015231326`
  exist and authorize the locked Stage 0 scope.
- Protected refs remained at their authorized SHAs:
  - `main@a5d45432a9b60f724c1aff700f4b371ea019960e`
  - `Shopify-connector@dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b`
  - `checkpoint/core-r2-readonly-uat-2026-07-15@acd8c4691e72cf5590f2a56228b08f183b76cd9a`
  - `checkpoint/wave-2-order-import-2026-07-18@22bfb9a0e9b1e48b6a664351e2b321d134177110`
- The implementation remains on its own branch and draft PR.
- No merge, protected-ref edit, Odoo.sh action, credential read, Shopify call,
  or Shopify mutation was performed.

## 2. Mandatory pre-edit audit result

No contradiction with accepted DEC-036 was found. The existing Layer 1
non-mutation path remains intact; Stage 0 adds a registry-gated Layer 2 path.

| Decision area | Implemented seam | Evidence |
|---|---|---|
| D1–D4 durable identity/schema | exact job ownership fields and new durable `shopify.connector.mutation.attempt` | constraints, uniqueness, immutable identity/outcome tests |
| D5–D7 fingerprints/idempotency/evidence | canonical SHA-256, attempt-owned key with 23-hour boundary, allowlisted snapshots | fingerprint and boundary tests; terminal-evidence masking |
| D8–D18 disposition/reconciliation | shared effective disposition, one linked reconciliation job, inconclusive cap of three | applied/not-applied/inconclusive/manual-resolution tests |
| D19–D25 C1/C2/NET/C3 | durable C1 owner, independent committed C2 intent, transaction-free synthetic NET, token-checked C3 | dispatch, genuine-connection, concurrency, and process-death harnesses |
| D26 stale-owner recovery | bounded 30-minute, batch-20 `FOR UPDATE SKIP LOCKED` sweep and five-minute cron | C1-only safe requeue, C2 reconciliation, concurrent-sweep tests |
| D27–D29 disconnect/identity | unresolved evidence and reconciliation quiescence gates; reasoned Administrator force route | credential-preservation and force-disconnect tests |
| D30–D32 security/retention | four read-only ACLs; six named service write surfaces; no unlink; independent 180-day pass | per-role denial, source guard, immutability, and retention tests |
| D33–D38 lifecycle/registry/bypass/proof | additive registry, handler/replay lockstep, API-client fail-closed guard, synthetic-only domain | manifest/init/source-guard and zero-real-mutation checks |

### Sanctioned attempt write surfaces

The only named write surfaces are:

1. `_create_attempt_intent`
2. `_record_direct_outcome`
3. `_record_reconciliation_result`
4. `_record_inconclusive_reconciliation`
5. `action_resolve_mutation_attempt`
6. `_mask_terminal_evidence`

All require the closed service context and superuser execution. Direct create,
write, and every unlink are denied. Machine-observed outcomes and attempt
identity are immutable.

### Recovery behavior

- C1 without a committed C2 attempt is safely requeued without transport.
- Every committed C2 attempt is treated as transport-attempted.
- Exceptions, process death, token mismatch, serialization failure, stale
  ownership, and disconnect route committed attempts to read-only
  reconciliation or manual review; none replay transport.
- Only the synthetic `mutation_dispatch_selftest` domain is registered.
  Its transport is an in-process stub and cannot read a credential or perform
  HTTP.

## 3. Proof inventory and execution status

Exactly nine required Stage 0 test modules are present and registered:

- `test_mutation_attempt.py`
- `test_mutation_dispatch.py`
- `test_mutation_reconciliation.py`
- `test_mutation_recovery.py`
- `test_mutation_api_guard.py`
- `test_mutation_security.py`
- `test_mutation_retention.py`
- `test_mutation_concurrency.py`
- `test_mutation_source_guards.py`

The concurrency module contains genuine independent PostgreSQL-connection
proofs for C1 ownership, fresh-transaction visibility, C3 token mismatch,
attempt uniqueness, concurrent stale sweeps, the NET transaction/lock window,
reconciliation-count serialization, serialization-failure recovery, and
second-worker exclusion.

The recovery module includes an opt-in real child-process harness
(`SHOPIFY_LAYER2_RUN_PROCESS_DEATH=1`) for death after C1, after C2, during
synthetic NET, after NET, and during C3. The parent executes the real stale-owner
sweep and asserts recovery without transport replay.

### Checks executed in this workspace

| Check | Result |
|---|---|
| Python AST parse of all 20 changed Python files | PASS |
| XML parse of the changed cron file | PASS |
| Changed Python line-length scan (100 characters) | PASS |
| Required nine test modules present and registered | PASS |
| New cron registered in manifest | PASS |
| Mutation-attempt ACLs read-only for Auditor/Operator/Reviewer/Administrator | PASS |
| Production scan for Task 013/other real mutation operation names | PASS — none present |
| Changed-file scope | PASS — exactly 23 authorized files |
| Real credentials/HTTP/Shopify mutation execution | ZERO |

Odoo is not installed in this execution workspace, so the Odoo test suite,
independent PostgreSQL runtime tests, process-death harness, install/upgrade
test, and full connector regression were **not run here**. They remain required
in an Odoo-capable independent environment before runtime acceptance. No
runtime-pass claim is made by this document.

Proof-layer state:

- **Layer 1:** implementation and tests prepared; static checks passed; Odoo run pending.
- **Layer 2:** genuine-connection tests prepared; execution pending.
- **Layer 3:** process-death harness prepared; execution pending.
- **Independent Odoo.sh Layer 4:** explicitly outside Sol's authority.
- **Full connector regression:** pending an Odoo-capable environment.
- **Post-Gate-B synchronization regression:** blocked until the control room
  supplies the exact authorized integration SHA after Gate B acceptance/merge.

## 4. Zero-real-mutation evidence

- No production source contains `inventorySetQuantities`,
  `inventoryActivate`, `fulfillmentCreate`, `refundCreate`, or payout
  mutation registration/call sites.
- The sole GraphQL mutation literal is the allowlisted synthetic self-test
  request prepared by the Layer 2 dispatcher.
- The synthetic transport returns local evidence only and cannot perform HTTP.
- The API client rejects mutation documents lacking an exact durable
  job/attempt/token/domain context and registered reconciliation strategy.
- The existing core `requests.post` transport seam remains guarded; the
  accepted product-importer CDN `requests.get` bypass is unchanged.
- No Shopify credential was read and no Shopify request was made during this
  work.

## 5. Scope and synchronization gate

The branch changes exactly the 23 files authorized by the locked packet:
14 implementation/registration/security files, nine exact tests, and this
validation record. It changes no shared Wave 3 binding document and no Task
013/013B implementation.

Gate B PR #179 currently says `PROPOSED FOR CONTROL-ROOM GATE B ACCEPTANCE`
and is not merged. Therefore this branch has not incorporated Gate B and does
not infer an integration sync target. Work stops before synchronization until
the control room provides the exact post-Gate-B integration SHA.

SEC-2 remains a future re-key obligation: Stage 0 stores no new credential and
does not alter the accepted credential-storage boundary.

## 6. Recommendation

**IMPLEMENTATION COMPLETE — WAITING FOR GATE B MERGE SYNC**
