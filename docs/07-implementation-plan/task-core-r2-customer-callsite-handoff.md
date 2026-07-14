# CORE-R2 Slice 2B — Customer Call-Site Migration: Session Handoff

> **Session type:** one narrow customer-domain implementation session (Prompt C /
> RD-C). **Static validation only — NOT runtime-green.** SRR-03 OPEN. Prompt E
> BLOCKED. No live Shopify call. No merge.

**Model:** Opus 4.8.
**Date:** 2026-07-14.
**Branch:** `claude/core-r2-customer-callsite`.
**Draft PR base:** `claude/core-r2-slice-2b-integration`.
**Architecture:** AR-047. **Packet:** `task-core-r2-slice-2b-callsite-runtime-packet.md` §5.2/§5.6/§9.
**Companion:** `docs/05-qa/task-core-r2-customer-callsite-validation.md`.

**Revision 2 (2026-07-14) — control-room review `4695664662` (REVISE).** The
structurally-correct production migration is preserved (frozen). The correction
adds the missing **genuine independent-connection** lifecycle proofs (M1/M2
committed-lease visibility; Race A / M8 both orderings; Race B / M18) using real
`db_connect` connections, the real `action_disconnect`/admission lock protocol,
and the real `_run_disconnect_quiesce` controller; makes the concurrency cleanup
**fail-loud** on a lease leak; and corrects the evidence wording (a pre-set-state
test is **not** Race A; the PR is a **five-file** change). No production importer
change was needed (no genuine test surfaced a production defect). SRR-03 stays
OPEN; Prompt E stays blocked.

**Revision 3 (2026-07-14) — control-room review `4696393942` (REVISE).** The
production importer stays **frozen** (no runtime test proved a production defect;
16/16 AST invariants still pass). This revision (customer test file + these two
docs only) closes the remaining evidence issues:

1. **Primary lease-count M18 proof** — a new genuine test
   (`TestCustomerCallsiteRaceBGenuine.test_m18_lease_count_controller_observes_open_lease_then_finalizes`)
   parks the admitted call **before any FK write** via the allowed `_apply_import`
   observe-and-delegate barrier, so the worker holds **no store-row lock**. The real
   `_run_disconnect_quiesce` controller therefore genuinely **locks the store**,
   reaches the **lease-count branch**, writes `disconnect_open_lease_count=1`, moves
   to `quiescing`, and does not finalize/clear while the lease is open; a later pass
   finalizes `completed` + clears the credential after release. The prior
   binding-key-share `FOR UPDATE SKIP LOCKED` scenario is **retained, reclassified
   as lock-skip coverage** (`test_race_b_binding_keyshare_controller_skip_locked_coverage`).
2. **Scoped cron-trigger cleanup** — the globally-destructive whole-cron trigger
   delete is replaced with a **pre-test baseline + delete-only-delta** cleanup; no
   pre-existing trigger is ever deleted; zero-residue verifies the trigger delta.
3. **Cleanup-first threaded teardown** — the threaded genuine tests capture worker
   liveness as evidence, run cleanup only when no worker owns locks, and assert
   liveness fail-loud **after** cleanup (no cleanup-aborting pre-assert).
4. **Stale docstring corrected** — the module docstring now lists all runtime-only
   classes and the exact selection tag.

SRR-03 stays OPEN; Prompt E stays blocked; no live Shopify call; no runtime-green.

---

## 1. Heads

- **Starting head (required):** `4f2cd7e4e09c591d4b63dd77888dd22f355f5c79`
  (== the `claude/core-r2-slice-2b-integration` staging tip; == the working
  branch tip at session start).
- **Final head:** *(the documentation commit on `claude/core-r2-customer-callsite`
  — the last of the three commits below; recorded in the draft PR.)*
- **Post-Slice-2A Shopify-connector base:** `a3fd6cd…` (ancestor of `4f2cd7e`).
- **Accepted sources (both ancestors of `4f2cd7e`, both open/draft/unmerged):**
  PR #150 customer `10d0034…`, PR #151 product `e4669aa…`.

---

## 2. Exact changed files — the five-file PR scope

1. `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py` — production call-site migration (unchanged since Revision 1; frozen).
2. `addons/shopify_connector_sale/tests/test_customer_import_matching.py` — adapted transport-stub tests + rewritten AST guard + `TestCustomerCallsiteExecuteBusiness` (unit lease guards; the disconnected-store test reclassified as a **pre-admission refusal**, not Race A).
3. `addons/shopify_connector_sale/tests/test_customer_matching_scalability.py` — fail-loud lease-leak cleanup on the existing genuine race; genuine independent-connection lifecycle proofs (`_CustomerGenuineHelpers` + M1/M2/Race A/Race B classes) including the **primary lease-count M18 proof** (Rev 3) and the retained lock-skip coverage; **test-owned (baseline-delta) cron-trigger cleanup** (Rev 3); **cleanup-first threaded teardown** (Rev 3); corrected module docstring (Rev 3).
4. `docs/05-qa/task-core-r2-customer-callsite-validation.md` — validation record.
5. `docs/07-implementation-plan/task-core-r2-customer-callsite-handoff.md` — this handoff.

No core/product/manifest/XML/security/data/CI/shared-handoff file changed. (The
earlier "(3)" wording counted only the code/test files; corrected to the true
five-file PR scope per review `4695664662` #5.)

---

## 3. Old / new call-site shape

See `…/task-core-r2-customer-callsite-validation.md` §3. In one line: the
value-returning `execute()` → `normalize` → `apply` shape became a single
`with client.execute_business(job, store, CUSTOMER_IMPORT_QUERY, variables=…) as
result:` context wrapping `normalize` + `apply` + `flush_all` + `return`, with the
`ShopifyClientError → JobHandlerError` mapping around the `with`.

---

## 4. Lease boundary

One committed admission lease spans: Admin GraphQL call → API normalization →
`_normalize_payload` → full `_apply_import` reconciliation → `env.flush_all()`
(materialize-in-transaction, not commit) → return. Release on `with`-exit, after
reconciliation. No explicit commit. (Validation §4.)

---

## 5. Job thread-through

`_handle_customer_import_sync` already passes `job=job` to `import_customer_sync`
(unchanged). `import_customer_sync` now passes that `job` as the **first
positional** argument to `execute_business` — where it is the admission credential
(a business call is refused at admission without a valid job) **and** the existing
country/state note thread. Direct test callers now pass a real `job` accordingly.

---

## 6. Exception behaviour

`ShopifyClientError` (admission missing-credential / transport) →
`JobHandlerError(error_class, reason, technical_detail) from exc`, DEC-009 class
preserved. `ShopifyQuiescedError` propagates **uncaught** (the sole `except`
catches only `ShopifyClientError`) for the integrated Slice 2A dispatcher's
fail-closed `skipped` routing. Reconciliation `JobHandlerError`s propagate through
`__exit__` (lease released once) unchanged. (Validation §5.)

---

## 7. Matching-behaviour proof

Reconciliation code (`_apply_import` and everything below it) is byte-for-byte
unchanged — the diff touches only `import_customer_sync`'s transport/lease
boundary and three docstrings. Proven by: (a) the AST invariant scan (16/16); (b)
the unchanged Task 011/011B suites (`TestCustomerImportMatching`,
`TestCustomerDuplicatePrevention`, `TestCustomerFallbackPartner`,
`TestCustomerBinding`, `TestCustomerMatchingScalability`, + opt-in benchmark);
(c) 0 existing assertions removed/weakened (53 added). (Validation §6.)

---

## 8. Static results

**Revision 1 (migration):** py_compile OK; compileall OK; no conflict markers;
AST invariant scan 16/16 PASS; secret/PII scan clean; 0 assertions weakened.

**Revision 2 (correction):** py_compile OK; compileall OK; no conflict
markers; **four files changed** (the two customer test files + these two docs);
the **production importer is frozen** (unchanged — the 16/16 AST invariants still
pass); secret/PII scan clean (placeholder token + reserved `@…example` domains
only); the three new genuine classes are tagged
`-standard`/`shopify_connector_customer_callsite_lifecycle`. (Validation §7/§8.)

**Revision 3 (this correction):** py_compile OK (importer + both customer test
files); compileall OK (`addons/shopify_connector_sale`); **one test file + these
two docs changed** — the **production importer is frozen this session** (`git diff
e18e68f -- …customer_importer.py` is empty; 16/16 AST invariants still pass);
AST audit of the test file — every `patch.object` target is one of
`{_send, _apply_import, cursor, _lock}` (no `action_disconnect`/`_admit`/
`_release_lease`/`_run_disconnect_quiesce`/lease-ORM/`connection_generation`/store
state monkeypatch); the new `observing_apply` wrapper **delegates to the real
`_apply_import`** (`return real_apply(...)`, AST-verified); no
globally-destructive cron delete remains (`_trigger_baseline`/`_trigger_delta_ids`
present); secret/PII scan clean. **No Odoo runtime** (no `odoo` module; no
PostgreSQL server) — no test executed, no runtime-green claimed. (Validation
§7/§8.)

---

## 9. Adversarial self-review

**Revision 1 (migration).** A parallel five-lens adversarial review
(lease-boundary, exception-routing, matching-unchanged, test-correctness,
scope-contamination) with an independent verification pass returned **0 findings**.

**Revision 2 (this correction).** The genuine independent-connection tests were
verified by the author against the real production code and the PostgreSQL
row-lock conflict matrix; a subagent adversarial pass was also launched but was
**cut short by a session/API limit before completing** (an infrastructure
interruption, not a finding). The load-bearing lock reasoning was checked
directly:

- admission `FOR SHARE` does **not** conflict with the pause-holder's
  `FOR KEY SHARE` on the store → admission succeeds while the reconciliation is
  paused;
- `action_disconnect`'s `FOR NO KEY UPDATE` does **not** conflict with a
  `FOR KEY SHARE` → the disconnect returns without waiting for the paused
  reconciliation (Race B);
- the controller's `try_lock_for_update` is `FOR UPDATE SKIP LOCKED`, which
  **skips** a `FOR KEY SHARE`-locked in-flight store → genuine deferral, no
  premature `completed`; it finalizes only once the call releases its lease and
  key-share;
- `_finalize_disconnect_completed` → `_clear_token_under_store_lock` sets
  `credential_present=False` and `access_token=False` (verified in the credential
  model) → the M18 credential-cleared assertion holds;
- every genuine connection is bounded (statement+lock timeout); worker threads are
  daemon, bounded-joined, and `_assert_workers_dead`; cleanup is durable,
  fail-loud, and zero-residue (incl. leases).

**Revision 3 (this correction).** The new **primary lease-count M18** design was
verified directly against the production code, closing the exact gap the review
named (the SKIP-LOCKED scenario proves the skip path, not the lease-count branch):

- **The pause is before any store lock.** `execute_business.__enter__ → _admit`
  takes its store-row `FOR SHARE` on an **owned side cursor** and **commits+releases
  it together with the lease** before returning (api-client `_admit`: "`_send` runs
  *after* this returns, so no lock is ever held across the network call"). The
  `_apply_import` observe-and-delegate barrier parks **before** the reconciliation
  savepoint / binding INSERT — so the worker's main transaction holds the committed
  lease but **no** store-row lock. `_dispatch_one`/the job-start gate take **no**
  store-row lock either (grep: the dispatcher has zero `FOR UPDATE/SHARE/NO KEY`).
- **Therefore the controller reaches the lease-count branch.** With the store
  unlocked, `_run_disconnect_quiesce`'s `try_lock_for_update` (`FOR UPDATE SKIP
  LOCKED`) **succeeds**, `_process_disconnect_quiesce` counts the one committed
  lease, writes `disconnect_open_lease_count=1`, and (count>0, within timeout) sets
  `disconnect_status='quiescing'` **without** `_finalize_disconnect_completed` —
  credential preserved. After release (lease deleted by `_release_lease`), a later
  pass counts 0 → `_finalize_disconnect_completed` → `disconnected`/`completed` +
  `_clear_token_under_store_lock` clears the credential. Assertions match each step.
- **The barrier preserves real reconciliation** — `observing_apply` only signals +
  waits, then `return real_apply(self, store, payload, job=job)` (the unpatched
  method captured before the patch; AST-verified it delegates). Matching/create/bind
  behaviour is unchanged.
- **Controller selection robustness** — because the controller processes one
  `disconnecting` store per pass, the test drives it in a **bounded loop** until our
  store reaches the target status, so an unrelated `disconnecting` store cannot make
  the single pass miss ours (and a genuine miss fails loud, never hangs).
- **Cron scoping** — the baseline is captured **before `_fixture`** so any
  fixture/disconnect/controller-scheduled trigger is in the delta; `current−baseline`
  can never include a pre-existing id (set difference), so no pre-existing trigger is
  deletable; `= ANY(%s)` array binds are guarded (`if delta_ids`) against the empty
  case.
- **Cleanup-first** — liveness is evidence, not a pre-cleanup assert; cleanup runs
  only when `not worker_alive_final`; the fail-loud liveness assert is after cleanup.

A subagent adversarial pass was **not run** this revision (the Rev-2 attempt hit a
session limit); the load-bearing lock/branch reasoning above was checked directly
against the production sources cited.

Because these genuine proofs were **not executed** here (no Odoo runtime — §10),
their runtime confirmation is captured on the integration-staging host.

**Key adversarial checks — all clear:**

- No api result escapes the context (AST: `result` loads all inside the `with`).
- `flush_all` inside the context, before `return`; no commit.
- `job` never lost (first positional; dispatcher thread-through intact).
- `ShopifyQuiescedError` never remapped or broad-caught.
- Matching / candidate-search / fallback-partner / binding-uniqueness / savepoint
  unchanged (reconciliation code untouched).
- No product/core contamination; no legacy `execute()` fallback; no new file.

---

## 10. Runtime status

**Runtime pending.** No Odoo runtime this session. Integrated exact-head Odoo.sh
evidence is captured on the staging head after merge-back (packet §7 steps 5–7).
No runtime-green claimed.

---

## 11. Gates & rollback

- **Prompt E BLOCKED** (core-only public-`execute()` closure; runs after both
  call sites are migrated + merged to staging — packet §9c).
- **SRR-03 OPEN.**
- No merge, no live Shopify, no PR closure, no runtime-green claim.
- **Rollback:** normal revert of this child PR before integration; no schema/data
  migration; inherited Task 011B `import_customer_sync` restored intact.

---

## 12. Open questions

- **OQ (carried):** exact-head integrated Odoo.sh evidence + the deployed
  multi-worker proof are produced on the staging head, not here.
- **OQ-5 (packet):** `flush_all` materialize-not-commit semantics are asserted
  structurally here (AST) and behaviourally in `TestCustomerCallsiteExecuteBusiness`
  (binding materialized before lease release); final confirmation is the
  integrated Odoo 19 runtime.

---

## 13. Exact next-session prompt (proposed — for ChatGPT to authorise)

> Merge `claude/core-r2-customer-callsite` and `claude/core-r2-product-callsite`
> back into `claude/core-r2-slice-2b-integration` (packet §7 step 5), then run the
> integrated exact-head Odoo.sh validation on the staging head (fresh install +
> core/product/sale suites + CORE-R2 admission classes + both domains'
> call-site activation tests + the deployed multi-worker proof ×3). Do **not**
> start Prompt E until both call-site branches are merged back. SRR-03 stays OPEN.
