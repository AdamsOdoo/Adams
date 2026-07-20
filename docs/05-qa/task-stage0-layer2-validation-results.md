# Wave 3 Stage 0 — DEC-031 Layer 2 Validation Results

- **Status:** CAMPAIGN 3 DIAGNOSIS CORRECTED — FINAL RUNTIME CLOSURE REQUIRED
- **Original Stage 0 base:** `mvp/program-integration@3a2043cb8d45a4b9bc7bdb3ea39b58515e706da9`
- **Pre-synchronization head:** `644853a68b3497c134ee648ce7399e50d30ff397`
- **Accepted Gate B integration:** `8e2e707ff7025a7a2e9e0207a8886399a24b889c`
- **Synchronization merge:** `61b1812a75add912103a13b9c2619afe162ac785`
- **Branch / draft PR:** `sol/wave-3-stage-0-layer2` / #178
- **Bounded correction starting head:**
  `8915a2c36738d76e73723c003204b97b0b2f4e24`
- **Binding control-room review:** PR #178 comment `5016571203`
- **Runtime Campaign 1 tested SHA:**
  `033858b8cab5761d1c7959dd4e2e194b819856ff`
- **Runtime Campaign 1 build / database:** `35125006` /
  `adamsmen-sol-wave-3-stage-0-layer2-35125006`
- **Runtime-correction ruling:** PR #178 comment `5016941832`
- **Final adversarial review:** PR #178 comment `5017091126`
- **Runtime Campaign 2 tested SHA:**
  `42ef28e36be89754a4d2042eae7637a06cefd89a`
- **Runtime Campaign 2 build / database:** `35127417` /
  `adamsmen-sol-wave-3-stage-0-layer2-35127417`
- **Runtime Campaign 2 ruling:** PR #178 comment `5018637342`
- **Campaign 3 diagnostic tested SHA:**
  `a0d4f927f195158edd95dca3f4f56d1cb8b15e1c`
- **Campaign 3 diagnostic build / database:** `35135587` /
  `adamsmen-sol-wave-3-stage-0-layer2-35135587`
- **Campaign 3 diagnostic ruling:** PR #178 comment `5020095555`
- **Frozen candidate:** the commit containing this record; its exact SHA is
  recorded in the final PR body and control-room report because a Git commit
  cannot embed its own SHA.
- **Real Shopify mutations or credential-backed requests issued:** ZERO

## 1. Identity and synchronization

The historical pre-synchronization identity gate verified PR #178 open, draft,
unmerged, at its then-current 23-path scope. The pre-correction Campaign 2
identity gate found 27 paths; this correction brings the current cumulative
scope to 31 paths. PR #179 was closed and merged at the accepted Gate B
integration SHA.
Binding comments `5016117207`, `5016274358`, and `5016306005` existed and were
read in full.

The exact integration commit was merged with a normal two-parent merge commit.
The branch was then zero commits behind `mvp/program-integration`. All 15
accepted Gate B documents were byte-identical to the integration version after
the merge. No conflict, rebase, force push, history rewrite, protected-ref
change, or Gate B document edit occurred.

Protected refs remained:

- `main@a5d45432a9b60f724c1aff700f4b371ea019960e`
- `Shopify-connector@dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b`
- `checkpoint/core-r2-readonly-uat-2026-07-15@acd8c4691e72cf5590f2a56228b08f183b76cd9a`
- `checkpoint/wave-2-order-import-2026-07-18@22bfb9a0e9b1e48b6a664351e2b321d134177110`

## 2. Post-sync pre-edit audit

The synchronized audit found the complete correction campaign was required:
the old implementation allowed more than one attempt per job, let the create
surface authorize writes, exposed a four-key strategy, normalized transport
requests incorrectly, routed clean/not-applied outcomes to same-job retry,
overwrote direct evidence, retained stale owners after C3, excluded resolved
uncertainty from retention, caught `BaseException` in the Layer 2 wrapper, and
did not preserve historic reconciliation links or block every generic action.

The audit also covered dispatcher and replay registries, C1/C2/NET/C3 ordering,
API admission, stale sweep, reconciliation, manual resolution, disconnect,
retention, uninstall conversion, ACLs, cron loading, source guards, and all
nine Stage 0 test modules. No contradiction among DEC-036, DEC-037, the binding
ruling, and synchronized source required a hard stop.

## 2A. Bounded pre-runtime correction at 8915a2c

Control-room review `5016571203` found that the synchronized candidate could
create a reconciliation job while its committed C2 attempt was still
`pending`. That state could not be consumed by the reconciliation handler.
Recovery evidence also lacked its own bounded section, and several test
fixtures used invalid job types, illegal setup transitions, incomplete store
identity snapshots, or a store lifecycle state that could not admit a
reconciliation business job.

The bounded correction adds `_record_recovery_uncertain`, a locked private
attempt service with the only sanctioned `pending -> uncertain` recovery
transition. It is idempotent for unresolved uncertainty, refuses terminal or
resolved attempts, leaves `resolved_at` and the resolution tuple empty, and
records only bounded, redacted route metadata. The dispatcher now combines
that transition, exactly-one reconciliation admission, and owner cleanup under
the existing job/attempt locks. This applies when pre-C2 cleanup discovers a
C2 row, during Layer 2 owner recovery, after serialization recovery, and from
the stale-owner sweep. A pending attempt is rejected by the reconciliation
handler and malformed recovery fails closed on the original mutation job.

`remote_evidence_refs` now has four independent bounded sections: `direct`,
`recovery`, `reconciliation`, and `manual_resolution`. Direct evidence is
preserved. Recovery and reconciliation are independently capped. Manual
resolution appends one safe entry containing actor UID, disposition,
timestamp, and a redacted reason while preserving the other sections. The
existing retention operation masks the complete structure without deleting
the attempt or changing identity, fingerprint, outcome, or resolution fields.

All nine Stage 0 test modules were audited. Persisted job types are registered
selection values; `setup_readiness_check` is used only as a job source. C2
refusal fixtures are independent and legal. C3, API, reconciliation, and
durable recovery fixtures carry matching generation/identity snapshots, and
stores which execute reconciliation are connected. Exception scopes now
contain the intended operation. Callback rollback creates a valid child in the
callback and proves rollback of attempt resolution, original-job state, job
log, and child. The inconclusive cap proof now drives its final consequence
through the production reconciliation handler.

For `after_c1` and `during_precondition`, the prepared harness proves no
attempt, no transport, bounded pre-C2 retry, and no reconciliation job. For
`after_c2`, `during_net`, `after_net`, and rolled-back `during_c3`, it proves
pending-to-uncertain recovery, empty pre-verdict `resolved_at`, recovery
evidence, no transport replay, one reconciliation job, owner cleanup,
successful applied/not-applied recording, original-job consequence, and the
explicit reconciliation-job state.

## 2B. Runtime Campaign 1 and consolidated correction

Independent Runtime Campaign 1 executed exact SHA `033858b8` on Odoo 19 build
`35125006`. Clean installation, registry, model, fields, indexes, ACL loading,
cron loading, and zero-real-Shopify proof passed. The focused Stage 0 suite and
full regression were not green. The child-process death harness and a separate
baseline-to-candidate upgrade were not executed.

Control-room ruling `5016941832` classified the deterministic findings before
correction. The synthetic classifier was a production defect: idempotency
concurrency and throttling now route to uncertainty and reconciliation with
their exact registered error classes, while parameter mismatch and previous
attempt failure block as idempotency-contract violations. Redispatch evidence
preflight was extracted without changing its commit boundary, allowing a
TransactionCase unit proof plus a genuine post-install owned-cursor proof.

The remaining deterministic failures were stale or invalid test contracts.
API and lifecycle guards now preserve read-only `execute()` and lifecycle
probes while recognizing only guarded Layer 2 mutation admission through
`execute_business(..., mutation_context=...)`. Dispatcher creation is limited
to `_ensure_reconciliation_job` creating one linked reconciliation job. The
repository sudo inventory is method-, receiver-, ordinal-, and
purpose-qualified. Mutation-literal and attempt-write guards use target-aware
AST analysis and include adversarial detector fixtures.

The success sequence is proven by control-flow AST and a post-install genuine
cursor fixture: `prepare_local -> C1 commit -> prepare_preconditions -> C2
commit -> NET -> fresh C3`. Historic conversion uses
`_reassign_to_historic_job_type`; manual-resolution fixtures use a real
connector Administrator; service-level `ValidationError` and structural SQL
uniqueness are proven separately.

The reused-database `res_partner.autopost_bills` failures are recorded as
environment artifacts and caused no dependency or product-scope change. The
shared-live-database concurrency cluster and scheduled-drain transport count
remain unresolved pending an isolated, quiesced fresh-build rerun. Separate
upgrade proof is deferred to Wave 6. The process-death harness remains pending
safe child-process control; neither deferred item is reported passed.

## 2C. Final bounded adversarial correction at 4f4c124

Control-room review `5017091126` found three proof defects and one metadata
defect. A duplicate test method caused Python to discard the weaker definition;
the concurrent uniqueness test treated every exception as a valid loser; and
the attempt-write guard authorized same-named methods outside the mutation
attempt model. The PR body and this record also retained stale current-scope
references to 23 paths although GitHub reported 27.

The duplicate definition was removed while preserving the stronger test and
its `REASON_TEMPORARY` assertion. A repository-wide AST scan now inspects each
test class body directly across `shopify_connector_*/tests/**/*.py`, reports
duplicate direct method definitions, and is proven by a synthetic class with
two same-named test methods.

The concurrent database proof now requires exactly one committed insertion and
one `psycopg2.IntegrityError` loser whose SQLSTATE is
`psycopg2.errorcodes.UNIQUE_VIOLATION` (`23505`). Unexpected exceptions are
reported as failures, both threads must terminate within the bounded timeout,
each thread must report exactly one outcome, and exactly one attempt row must
survive. The separate service-level friendly `ValidationError` proof remains.

Attempt create/write authorization now requires both the exact mutation-attempt
model file and an accepted closed-surface owner method. Adversarial fixtures
prove that external models cannot borrow `_record_direct_outcome`,
`action_resolve_mutation_attempt`, or `_create_attempt_intent` to bypass the
guard. Existing attempt/attempts write/unlink, direct environment lookup, and
forged `_surface` detection remains, while unrelated store/job `self.write`
continues to be ignored.

## 2D. Runtime Campaign 2 and bounded test-harness correction

Runtime Campaign 2 tested exact SHA
`42ef28e36be89754a4d2042eae7637a06cefd89a` on fresh Odoo.sh build
`35127417`, database
`adamsmen-sol-wave-3-stage-0-layer2-35127417`. Clean install passed,
same-SHA update passed, runtime was **not green**, the prior scheduled-drain
failure passed, process-death produced the expected environment skip, and the
zero-real-Shopify proof passed.

Control-room ruling `5018637342` classified the deterministic findings as
test-harness or stale-test defects: the dispatch AST selector counted nested
commits; independent-cursor threads omitted Odoo 19 `release_test_lock()`;
coordination could strand workers; outcomes and exceptions were inconsistently
reported; uniqueness cleanup depended on nullable related `attempt.store_id`;
retention SQL ran before ORM resolution flush; and two legacy tests duplicated
obsolete raw sudo-count contracts.

The corrected harness uses a direct-expression AST selector with an adversarial
nested-commit fixture, one named-worker runner with dedicated channels and
`release_test_lock()`, exact retry classification, bounded joins, and
ownership-key cleanup with zero-residue diagnostics. Retention now flushes and
proves eligibility before masking. Credential service owns one canonical
filename/method/receiver/ordinal/purpose sudo inventory; job-log and readiness
tests consume exact local subsets.

The bounded correction commits are:

1. `240484b8c29275db40e6316e7ccc5913a324bec0` — dispatch, concurrency,
   cleanup, and retention harness corrections;
2. `9243dc6c3a5d94620981516bdc0a97d8809bbbdd` — canonical sudo inventory
   and legacy-test corrections;
3. the commit containing this record — lessons, Campaign 2 evidence, and
   candidate freeze; its exact SHA is recorded in the PR body and final
   control-room report.

`autopost_bills` remains an environment/module-ordering artifact: fresh
install/build-phase tests did not show it, while early-module
`-u --test-enable` did. Campaign 3 authoritative at-install evidence must come
from the fresh build phase; a same-SHA update is registry/update evidence, not
authoritative at-install regression evidence. No `account` dependency or
production change was made.

C1 ownership, stale-owner recovery, concurrent inconclusive counting, and
invalid-state recovery remain **not yet proven production defects**. Campaign 3
must determine them with the corrected isolated harness. The permanent controls
are recorded in `runtime-lessons-learned.md`.

### Campaign 3 execution order

**Stage A — known blockers:** run only the dispatch sequence test, the complete
`TestMutationConcurrency` class, resolved-uncertain masking, job-log sudo
inventory, and readiness sudo inventory tests. If Stage A fails, stop and
return complete Stage A evidence.

**Stage B — focused Stage 0:** run all nine Stage 0 modules only after Stage A
passes. If Stage B fails, stop before full regression.

**Stage C — full connector regression:** run only after Stages A and B pass.

## 2E. Campaign 3 diagnosis and final bounded correction

Campaign 3 tested exact SHA
`a0d4f927f195158edd95dca3f4f56d1cb8b15e1c` on build `35135587`, database
`adamsmen-sol-wave-3-stage-0-layer2-35135587`. Clean install and same-SHA
update passed. Stage A was **RED**; Stages B and C were not started. Retention
and the sudo inventory passed in the fresh-build phase. The SQL uniqueness
proof passed independently with one committed attempt and one SQLSTATE `23505`
loser. Process death produced the expected environment limitation, and the
zero-real-Shopify proof passed.

Ruling `5020095555` established that the C1 race, concurrent inconclusive
increment, and concurrent stale sweep never reached connector code. Their
worker threads stopped while constructing `api.Environment` at the
process-global Odoo Registry lock. They are invalid standard-test designs, not
production failures. Their proof now lives in the non-discovered external
`runtime_layer2_concurrency_harness.py`, using spawned OS processes whose
children initialize their own Odoo configuration, cursor, Registry, and
Environment.

The same diagnosis proved one production defect: `ValidationError` is a
`UserError` subclass, so the superclass-first handler made invalid committed
attempt recovery return without blocking the original job. Handler order is
now specific-to-general. Succeeded and failed-clean attempts preserve their
state, resolution timestamp, and evidence; the running original job blocks as
`blocked_manual_review / data_shape_schema_mismatch / duplicate_risk`; no
reconciliation job is created. Pending and unresolved-uncertain recovery, plus
the genuine temporary `UserError` ownership refusal, retain their prior
contracts.

The bounded correction commits are:

1. `fe3eb18860500f900a0ea51cb618be360c3b83e7` — invalid-recovery exception
   routing and exception-shadowing source guard;
2. `be687bcd028b6046de0bc2fd946f78aaf27586a0` — spawned-process harness,
   standard-test migration, behavioral recovery proofs, and structural commit
   detector correction;
3. the commit containing this record — lessons, Campaign 3 evidence, and
   final candidate freeze; its exact SHA is recorded in the PR body and final
   control-room report.

### Final runtime execution order

1. Invalid-recovery targeted regression.
2. AST and exception-shadowing targeted tests.
3. External multiprocess concurrency harness.
4. All nine Stage 0 standard modules.
5. Full connector regression.

## 3. Binding A–N traceability

| Binding | Production method(s) | Exact test evidence | Runtime proof | Rollback / fail-closed behavior |
|---|---|---|---|---|
| A | attempt unique indexes; `_create_attempt_intent`; `_drain_mutation_one` | attempt/concurrency/dispatch: different tokens, concurrent insert, evidence redispatch | one durable row; no second C1/NET | pre-C2 bounded retry only; post-C2 blocks/reconciles |
| B | `create`, `write`, `_check_resolution_consistency` | attempt: create-surface write refusal, all-surface identity immutability, tuple/timestamp | rejected ORM writes and constraints | invalid tuple/identity write rolls back |
| C | seven-key registry; `_drain_mutation_one` | dispatch/source/recovery: exact keys/order and precondition death window | local → C1 → precondition → C2 → NET → C3 | pre-C2 Exception clears owner; BaseException leaves C1 |
| D | `_validate_job_consequence`; `_apply_validated_consequence` | dispatch/reconciliation: vocabulary, no retry action, callback success/failure | atomic job/domain consequence | callback failure rolls back outcome, job, log, child |
| E | `_validate_reconciliation_result`; reconciliation handler | reconciliation: applied/not-applied/inconclusive, malformed/missing, explicit read-job terminal | normalized verdict plus explicit read-job state | original job blocks; no resend; read retry only when inconclusive |
| F | fixed registry; C3 identity check; reconciliation identity check | concurrency/reconciliation: generation, local identity, remote identity | `store_identity_mismatch` on original job | evidence retained, disposition withheld, no child |
| G | API `_validate_graphql_operation`, `_admit_mutation`, `_send` | API/source: exact operation/variables, expiry/state/token/domain, no direct send | owned side transactions and exact SHA-256 | stale/mismatched request refused before HTTP |
| H | direct/reconciliation evidence recorders; redaction | attempt/reconciliation/security | bounded `direct` plus ordered reconciliation entries | direct evidence never overwritten; unsafe text redacted |
| I | retention search; `_mask_terminal_evidence` | retention: resolved uncertainty positive, unresolved uncertainty negative | rows retained with identity/outcome metadata | unresolved evidence untouched; no unlink |
| J | Layer 2 wrapper Exception boundary | source/recovery: BaseException source proof and six real-death windows | opt-in child-process harness | stale sweep recovers durable C1/C2; API lease behavior unchanged |
| K | owner cleanup; C3; stale sweep | concurrency/recovery: terminal, uncertain, mismatch, crash-side ownership | owner fields empty after committed C3 | pre-C3 death retains owner for sweep |
| L | reconciliation-link constraint; historic conversion | reconciliation historic-link test | historic job retains attempt FK and evidence | no attempt/job deletion |
| M | manual retry/review and generic cancel guards | security: duplicate-risk and identity-mismatch refusal | UserError before state mutation | mutation-attempt resolution remains sole generic progression |
| N | nine modules; audits below | exact obligation coverage across all nine modules | independent Odoo/PostgreSQL run pending | no unvalidated runtime-green claim |

## 4. Final contract

One mutation job owns exactly one immutable attempt for its lifetime. C2 is
side-cursor-only and proves running state, owner token, domain, and attempt
absence. Existing evidence blocks redispatch before C1.

Every strategy has exactly:

1. `reconciliation_job_type`
2. `prepare_local`
3. `prepare_preconditions`
4. `transport`
5. `classify_direct_result`
6. `reconcile`
7. `apply_consequence`

The execution sequence is `prepare_local → C1 commit → prepare_preconditions →
C2 commit → NET → fresh C3`. No main transaction or owner lock spans the
precondition read or transport.

Post-C2 consequences use registered vocabulary only and contain no same-job
retry action. Direct uncertainty routes to read-only reconciliation. Resolved
reconciliation invokes the domain callback in the same transaction as the
attempt resolution, original-job transition, audit record, and any child
creation. The reconciliation job receives an explicit terminal or retry state.

The API hashes the exact transmitted operation string and canonical variables;
it does not collapse whitespace. Mutation admission validates the pending
attempt in owned side transactions and returns a plain transport snapshot.
Read-only API behavior and the intentional API context-manager
`BaseException` lease-release behavior remain unchanged.

## 5. Correction commits before this validation record

1. `8e849a8def0bd7ca64b699a8875360bdad18b4b5` — structural one-attempt
   lifetime and consequence protocol.
2. `a8eacaac916aa06cbf57689fa6897eb850687278` — exact mutation-request
   admission and main-cursor isolation.
3. `de5bfb14cc08ffbdf571c5c4d0ae1d1de44ca8c0` — evidence retention,
   disconnect redaction, and committed-owner cleanup.
4. `53ac0e146310c86612f57b1713f51dfd80f25ec0` — consolidated nine-module
   correction proof.
5. `60ecc658b6dbfc71e24c84653675630a4d0f6bd8` — final reconciliation
   routing and completeness-audit corrections.
6. `9b05a712dc4cd0219399ef762ef240c635bb586c` — locked post-C2 recovery
   transition, atomic reconciliation admission, and evidence normalization.
7. `5c2b6996f60d13eac56ac258f05572d013bc5f23` — complete nine-module
   fixture audit and end-to-end recovered reconciliation proofs.
8. `15adde70c81ff9254ad9a338e23eeaf028aecb90` — classifier and redispatch
   preflight correction.
9. `30185c06d29b72d74ca48d330f95957fa6c8ebff` — valid mutation API
   admission proof.
10. `d04450618b3cb51d5a29d9f53fb1e5e1b7754438` — classifier and transaction
    sequence proof.
11. `776827c555edd6d1e21903ab4e3c86c31bd9618f` — target-aware mutation
    source guards.
12. `8833885060c02cef94fe509e2daab36123c9361f` — owned-cursor runtime
    boundary proofs.
13. `4e77aa4c10c897653faf5f7116791652af2950b9` — service/index uniqueness
    separation.
14. `baa8182b59e3884b359470ce3ece968dcc6aac0f` — lifecycle historic
    conversion proof.
15. `e10c68375a79a17acbae5d1ec399ac04eabe8a84` — administrator retention
    fixture.
16. `4b82c3d26ae6f41c4c25b82bc82b9aa7a9e1d0d3` — manual resolution role
    matrix.
17. `700eefaad336ce47faf0cccdf021c1439d314fed` — API legacy guard correction.
18. `62890dcd122135660d757b4aa966a358ddde275a` — dispatcher create/sudo
    guard correction.
19. `5dd5323848c0607333fdabbee0b10258371a3d90` — complete qualified sudo
    inventory.
20. `d58005e5a756461bd3040ded745b299a662477a7` — lifecycle legacy guard
    correction.

The earlier consolidated correction modified 17 of the then-authorized paths:
eight model files and the nine existing Stage 0 test modules. No new
production, test, or documentation path was introduced in that historical
campaign.

The bounded campaign after `8915a2c` modifies exactly 13 authorized paths:
three production models, all nine existing Stage 0 test modules, and this
validation record. It creates no file.

Runtime Campaign 1 correction after `033858b8` modified exactly 14 authorized
paths: one production dispatcher, eight Stage 0 test modules, the four
authorized legacy regression modules, and this validation record. At that
historical candidate the cumulative PR contained 27 existing paths.

## 6. Static validation actually executed

| Check | Result |
|---|---|
| Python compile/AST parse of all 32 available addon Python files | PASS |
| XML parse of the stale-owner cron | PASS |
| Manifest literal parse and model/ACL/cron registration audit | PASS |
| CSV parse of 26 ACL rows | PASS |
| 88-character line scan of the five corrected Python files | PASS |
| Legacy marker/strategy/call literal scans | PASS |
| GraphQL/raw-transport/source-guard audit | PASS (static source inspection; Odoo test execution pending) |
| Credential, token, real-domain, and PII/logging audit | PASS — no real value or call |
| Git patch trailing-whitespace / diff-check audit | PASS |
| Integration comparison | PASS — zero behind; candidate scope exactly 31 PR paths |
| Gate B byte-preservation audit | PASS |
| Recovery-state/admission AST ownership audit | PASS |
| Nine-module job-type/job-source fixture audit | PASS |
| Six-window harness source and assertion audit | PASS |
| Invalid `job_type='setup_readiness_check'` search | PASS — absent |
| Runtime Campaign 1 deterministic/stale finding traceability | PASS |
| Exact dispatcher create-site inventory | PASS — one sanctioned site |
| Exact method/receiver/purpose sudo inventory | PASS — 48 sites |
| Canonical sudo inventory against all model ASTs | PASS — exact 48-site match |
| Legacy job-log/readiness sudo subsets | PASS — exact owner-qualified subsets |
| Thirteen-file fixture and tag audit | PASS |
| Repository-wide duplicate test-method AST scan | PASS — no duplicates |
| Synthetic duplicate-method detector fixture | PASS — duplicate reported |
| Attempt-write positive/negative fixtures | PASS |
| External same-name attempt-write bypass fixtures | PASS — all rejected |
| Direct-statement commit detector adversarial proof | PASS — nested commits ignored |
| Standard SQL-thread AST audit | PASS — only the `23505` runner starts/joins threads |
| Concurrent uniqueness source audit | PASS — exact `23505`; arbitrary failures rejected |
| Ownership-key cleanup source audit | PASS — job/attempt/child/log/store residue checked |
| Resolved-retention source audit | PASS — ORM flush and eligibility precede masking |
| Dispatcher exception-handler hierarchy audit | PASS — no shadowed handlers |
| Synthetic exception-shadowing fixtures | PASS — invalid rejected; valid accepted |
| External harness CLI/import audit | PASS — no scenario executed |
| Process-model audit | PASS — spawn; independent child Registry/Environment |
| Standard-thread audit | PASS — SQL-only; no worker ORM Environment |
| Runtime lessons register/checklist audit | PASS — LL-001 through LL-013 present |
| Current cumulative changed-file comparison | PASS — zero behind, exactly 31 paths |

Odoo and PostgreSQL executables are unavailable in this workspace. Therefore
install/upgrade, ORM constraints, ACL runtime, cron execution, all Odoo tests,
genuine PostgreSQL multi-connection tests, full regression, and the opt-in real
process-death harness were **not executed**. No unexecuted test is classified
as passed and no runtime-green claim is made.

## 7. Independent runtime obligations

Independent exact-head Odoo.sh verification must execute install and upgrade,
all nine Stage 0 modules, full connector regression, genuine concurrent
different-token insertion, C1/C2/C3 serialization and stale-owner recovery,
ACLs, cron registration/execution, disconnect/force-disconnect, retention,
historic conversion, redaction/residue checks, and read-only regressions.

The Layer 3 harness is prepared for:

- after C1;
- during the post-C1/pre-C2 precondition window;
- after C2;
- during NET;
- after NET;
- during C3.

It remains opt-in with `SHOPIFY_LAYER2_RUN_PROCESS_DEATH=1` and pending an
environment with Odoo, PostgreSQL, and child-process control.

## 8. Zero-real-mutation and scope proof

Only `mutation_dispatch_selftest` is registered. Its transport is an
in-process synthetic stub with no HTTP or credential read. Production source
contains no inventory, fulfillment, refund, or payout mutation implementation.
No Shopify token was read, no credential-backed request was made, and no real
Shopify mutation was executed.

The PR changes exactly these 31 authorized paths:

1. `addons/shopify_connector_core/__manifest__.py`
2. `addons/shopify_connector_core/data/shopify_connector_stale_owner_sweep_cron.xml`
3. `addons/shopify_connector_core/models/__init__.py`
4. `addons/shopify_connector_core/models/shopify_connector_api_client.py`
5. `addons/shopify_connector_core/models/shopify_connector_job.py`
6. `addons/shopify_connector_core/models/shopify_connector_job_actions.py`
7. `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`
8. `addons/shopify_connector_core/models/shopify_connector_mutation_attempt.py`
9. `addons/shopify_connector_core/models/shopify_connector_pii_retention.py`
10. `addons/shopify_connector_core/models/shopify_connector_stale_owner_sweep.py`
11. `addons/shopify_connector_core/models/shopify_connector_store.py`
12. `addons/shopify_connector_core/security/ir.model.access.csv`
13. `addons/shopify_connector_core/tests/__init__.py`
14. `addons/shopify_connector_core/tests/test_api_client.py`
15. `addons/shopify_connector_core/tests/test_credential_service.py`
16. `addons/shopify_connector_core/tests/test_disconnect_quiescence.py`
17. `addons/shopify_connector_core/tests/test_job_dispatch.py`
18. `addons/shopify_connector_core/tests/test_mutation_api_guard.py`
19. `addons/shopify_connector_core/tests/test_mutation_attempt.py`
20. `addons/shopify_connector_core/tests/test_mutation_concurrency.py`
21. `addons/shopify_connector_core/tests/test_mutation_dispatch.py`
22. `addons/shopify_connector_core/tests/test_mutation_reconciliation.py`
23. `addons/shopify_connector_core/tests/test_mutation_recovery.py`
24. `addons/shopify_connector_core/tests/test_mutation_retention.py`
25. `addons/shopify_connector_core/tests/test_mutation_security.py`
26. `addons/shopify_connector_core/tests/test_mutation_source_guards.py`
27. `docs/05-qa/task-stage0-layer2-validation-results.md`
28. `addons/shopify_connector_core/tests/test_job_log_system_append.py`
29. `addons/shopify_connector_core/tests/test_readiness_slot_closure.py`
30. `docs/05-qa/runtime-lessons-learned.md`
31. `addons/shopify_connector_core/tests/runtime_layer2_concurrency_harness.py`

The final diagnosis-driven campaign changed production only by reversing the
two diagnosed exception handlers in `shopify_connector_job_dispatch.py`. No
other production behavior, Gate B document, decision record, inventory addon,
other addon, CI/workflow, Wave 3 handoff, or Task 013/013B implementation
changed. PR #178 remains open, draft, and unmerged. Odoo/PostgreSQL runtime
remains pending independent fresh-build execution; runtime green is not
claimed.

## 9. Recommendation

**CAMPAIGN 3 DIAGNOSIS CORRECTED — READY FOR FINAL RUNTIME CLOSURE**
