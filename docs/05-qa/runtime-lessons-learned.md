# Connector Runtime Lessons Register

This register is a compact control list for runtime findings. A lesson marked
`enforced` has a static or test control in the repository; it is not runtime
green until a later campaign records `runtime-verified`.

| ID | Failure pattern | Root cause | Why pre-runtime review missed it | Permanent control | Enforcing test or checklist | Affected future waves | Status |
|---|---|---|---|---|---|---|---|
| LL-001 | Privileged action fixture fails before the intended assertion. | A generic user was substituted for the required role. | Static review checked the call, not the fixture's group membership. | Every privileged action uses an explicit real role-user fixture. | Security, retention, and manual-resolution role tests. | Task 013 onward. | runtime-verified |
| LL-002 | A test calls a removed method or masks exception precedence. | Test and production surfaces drifted. | Candidate freeze did not reconcile referenced methods and exception order. | Resolve every test-referenced production method and assert exact exception precedence before freeze. | Pre-runtime referenced-surface checklist and source guards. | All waves. | enforced |
| LL-003 | Foundation correction breaks an older regression guard. | Legacy tests retained superseded contracts. | The focused audit stopped at new Stage 0 modules. | Every foundation change includes a connector-wide legacy-test impact scan. | Campaign staged regression checklist. | All foundation and domain waves. | enforced |
| LL-004 | Raw strings or recursive AST walks misstate control flow. | Text matching and `ast.walk()` ignore statement ownership. | The assertion looked plausible without an adversarial nested branch. | Control-flow guards inspect direct AST owners and include adversarial fixtures. | Direct-C1 commit detector and nested-commit fixture. | Task 013 onward. | enforced; runtime-verified (Stage A2, build 35145929) |
| LL-005 | `TransactionCase` directly executes a production commit path. | The test cursor contract differs from a durable production cursor. | Static review did not classify commit-bearing methods by test case type. | Commit-bearing paths use independent durable cursors or a non-committing seam. | Cursor-boundary source audit. | All Layer 2 and lifecycle work. | enforced |
| LL-006 | Fresh ORM environments in standard-test worker threads stop at the process-global Registry lock. | `release_test_lock()` releases the test-cursor lock, not the ORM `Registry._lock` held by the main test execution. | The earlier review treated two independent Odoo locks as one. | In-process ORM threads are prohibited for production-concurrency proof; use separate spawned OS processes with independent Odoo registries. | External Layer 2 concurrency harness contract and runtime command. | Task 013 and every concurrent wave. | enforced; contract runtime-verified (build 35145929); genuine multiprocess execution infrastructure-deferred to a child-process-capable runner before release readiness (Wave 6) |
| LL-007 | A concurrency worker exits silently, remains alive, or contaminates later tests. | Shared state and in-process registry ownership hid worker outcomes. | Tests asserted aggregate results without isolated runtimes and one report per worker. | Spawned named processes use dedicated structured results, bounded termination, exact outcomes, and success/failure cleanup. | External harness supervisor, child-result contract, and zero-residue verification. | Task 013 onward. | enforced; contract runtime-verified (build 35145929); genuine multiprocess execution infrastructure-deferred to a child-process-capable runner before release readiness (Wave 6) |
| LL-008 | Raw-SQL attempt survives cleanup when a related store field is null. | Cleanup used a computed/stored-related field instead of primary ownership. | Fixture review assumed ORM-populated related values. | Clean through original job, attempt `job_id`, child attempt links, then store. | Concurrency fixture cleanup and residue diagnostics. | All raw-SQL concurrency fixtures. | enforced |
| LL-009 | Raw SQL cannot see preceding ORM resolution writes. | ORM state was not flushed before SQL. | Review treated ORM assignment as immediately durable to SQL. | Flush all ORM writes before dependent raw SQL, then invalidate changed fields. | Resolved-uncertain retention test. | Retention and migration waves. | enforced |
| LL-010 | Multiple sudo inventories disagree after a correction. | Flat filename/count copies had independent ownership. | Review updated the strongest inventory but not legacy duplicates. | One canonical method/receiver/ordinal/purpose-qualified inventory; local tests consume subsets. | Credential-service canonical inventory and legacy subset tests. | Security work in all waves. | enforced |
| LL-011 | Fresh install, same-SHA update, and live database results are conflated. | Evidence types were reported under one runtime label. | The validation record lacked proof-type separation. | Record each proof phase separately; only fresh-build at-install evidence is authoritative for install regression. | Runtime campaign reporting checklist. | Every runtime campaign. | recorded |
| LL-012 | One failed threaded test causes misleading later failures. | Surviving locks, rows, or workers contaminate the database. | Broader suites ran before known blockers were isolated. | Rerun known blockers first and stop before broader stages on failure. | Campaign 3 Stage A/B/C execution order. | Task 013 onward. | enforced |
| LL-013 | A safety-specific exception branch is unreachable. | `ValidationError` is a `UserError` subclass, so superclass-first handling consumed the specific failure. | Static review checked caught types but not their ordering hierarchy. | Order exception handlers from specific to general and reject superclass-first sequences with an AST guard. | Dispatcher exception-shadowing source guard and adversarial fixtures. | All production exception routing. | runtime-verified (Stage A1/A2, build 35145929) |
| LL-014 | A mandatory runtime proof cannot execute because the host lacks a required OS primitive. | Odoo.sh dev containers mount `/` (and `/dev/shm`) read-only, so Python multiprocessing semaphore creation raises `OSError`/EROFS before any child process, Registry, Environment, SQL operation, or transport is reached. | The gate declared the spawned-process proof mandatory on Odoo.sh without verifying that the target runtime supports multiprocessing semaphore primitives and child-process control. | Verify infrastructure capability (writable `/dev/shm`, semaphore/spawn support, child-process control) before making a multiprocessing proof mandatory; run the genuine spawned-process harness on a child-process-capable CI or local Docker runner; the deferred proof remains mandatory before final release readiness. | External harness OSError/EROFS reproduction and the infrastructure-capability checklist item. | All concurrency proofs; release readiness / Wave 6. | infrastructure-deferred; mandatory before release readiness (ruling 5020947103) |

## Mandatory pre-runtime checklist — Task 013 and later

- [ ] Resolve every test-referenced production method and exception contract.
- [ ] Scan all connector legacy tests affected by foundation changes.
- [ ] Use direct-owner AST checks with an adversarial nested-control fixture.
- [ ] Keep `TransactionCase` away from production commit paths unless an
  accepted test-cursor seam is explicit.
- [ ] Do not use standard in-process ORM threads as concurrency proof; use
  separate spawned OS processes whose children initialize Odoo independently.
- [ ] Require one named result per process, bounded termination, named retry
  reasons, and failure on every unapproved exception.
- [ ] Clean raw-SQL fixtures through primary ownership keys and assert zero
  stores, jobs, child jobs, attempts, logs, cursors, locks, and workers.
- [ ] Flush ORM writes before dependent SQL and invalidate SQL-mutated fields.
- [ ] Update the single canonical sudo inventory; never add a flat count copy.
- [ ] Separate fresh-install, same-SHA update, live-database, and process-death
  evidence in the validation record.
- [ ] Execute known blockers first, then the focused wave suite, then full
  regression; stop at the first failed stage and aggregate that stage's facts.
- [ ] Reconfirm zero credential-backed or real Shopify transport.
- [ ] Scan production try/except sequences for superclass-first shadowing.
- [ ] Verify host infrastructure capability (writable `/dev/shm`, semaphore /
  spawn support, child-process control) before declaring a multiprocessing
  proof mandatory; run the genuine spawned-process harness only on a
  child-process-capable runner and keep it mandatory before release readiness.
- [ ] Classify the `autopost_bills` reused-database `res_partner` not-null
  artifact as environment noise; rely on fresh-build at-install evidence where a
  targeted `-u --test-enable` is blocked solely by it, and never add `account`
  as a connector dependency.
