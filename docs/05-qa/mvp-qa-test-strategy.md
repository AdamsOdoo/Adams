# MVP QA and Test Strategy

> Docs-only QA/test-strategy package for the Odoo 19 ↔ Shopify Connector
> MVP, prepared on branch `claude/mvp-qa-release-strategy-s8k3hq` from
> `Shopify-connector` at `f74aaf204745ce0087733870fe56bdda74bfa79a` (PR #92
> merge — "Credential and connection foundation planning"). Companion
> documents in this same sprint:
> [`foundation-test-matrix.md`](./foundation-test-matrix.md),
> [`domain-e2e-test-matrix.md`](./domain-e2e-test-matrix.md),
> [`security-redaction-test-plan.md`](./security-redaction-test-plan.md),
> [`data-integrity-idempotency-test-plan.md`](./data-integrity-idempotency-test-plan.md),
> [`../08-release-readiness/mvp-release-readiness-checklist.md`](../08-release-readiness/mvp-release-readiness-checklist.md),
> [`../08-release-readiness/mvp-uat-scenarios.md`](../08-release-readiness/mvp-uat-scenarios.md),
> and this sprint's own
> [`mvp-qa-release-strategy-handoff.md`](./mvp-qa-release-strategy-handoff.md).
> This package runs **parallel to, and does not touch,** the Task 002
> decision/gate-pack session or the MVP domain-slicing session — see the
> handoff document's "No conflict" section for the exact boundary.

## Status

- **Proposed for ChatGPT review.**
- **Docs-only.** No code, no fields, no models, no views, no Python, no
  XML, no CSV, no manifest, no test file, and no CI file is created by
  this package.
- **No implementation.** Nothing in this package implements, starts, or
  advances Task 002, Task 003, or any other coding task.
- **Does not open any gate.** The only currently open implementation gate
  remains the limited, core-only, zero-UI gate
  ([`../07-implementation-plan/limited-core-implementation-gate.md`](../07-implementation-plan/limited-core-implementation-gate.md),
  [`AR-021`](./architecture-review-log.md)), which authorized exactly one
  task (Task 001, merged via PR #88, QA-closed by
  [`task-001-core-runtime-readiness.md`](./task-001-core-runtime-readiness.md)).
  Task 002 (credential storage/redaction) and Task 003 (API client/test
  connection) remain **proposed only, not authorized** — confirmed by the
  [`AR-024`](./architecture-review-log.md) acceptance note and by PR #92's
  own body ("Task 002 ... is accepted as the recommended next coding
  task — not authorized by this acceptance").
- **Does not create tests.** Every test named in this package and its
  companions is a **future requirement** for the implementation PR that
  will eventually satisfy it — none exists yet, and this package does not
  claim otherwise.
- **Defines QA strategy for future implementation PRs** — Task 002 onward,
  and the product/customer/order/inventory/fulfillment domain slices once
  their own gates open.

## QA principles

1. **Test small tasks independently.** Each implementation task
   (Task 002, Task 003, Task 004, Task 005, Task 006, and each future
   domain slice) is reviewed and tested on its own allowed-files scope,
   matching the one-task-per-PR, small-PR discipline already binding on
   this project
   ([`limited-core-implementation-gate.md`](../07-implementation-plan/limited-core-implementation-gate.md)
   §5: "No second task may start until ChatGPT reviews the first
   implementation PR"). A QA pass never waits for a bundle of unrelated
   changes to accumulate.
2. **No broad untested PRs.** A PR that changes more than its task's
   named allowed files, or that lacks tests/manual-validation evidence for
   its own acceptance criteria, fails review by definition
   ([`pr-review-checklist.md`](./pr-review-checklist.md) §C).
3. **Every implementation PR must prove access/security/data integrity.**
   Not merely assert it — access-denial matrices, redaction assertions,
   and uniqueness/idempotency assertions must be exercised by a test or,
   where no runtime exists, a manual checklist (see
   [Runtime limitation strategy](#runtime-limitation-strategy)).
4. **Every sync task must prove idempotency and duplicate prevention.**
   A re-run of the same operation (retry, repeated webhook, reconciliation
   pass) must not create a duplicate record or double-apply a write — see
   [`data-integrity-idempotency-test-plan.md`](./data-integrity-idempotency-test-plan.md).
5. **Every API task must prove redaction and safe failure handling.** No
   Shopify credential value may appear in any log, exception, job record,
   or store mirror; every failure must classify into the fixed 16-class
   error registry with no invented 17th class — see
   [`security-redaction-test-plan.md`](./security-redaction-test-plan.md).
6. **Every UI task must prove the Premium Simplicity Standard.** Smooth
   guided flows, clean visual hierarchy, minimal cognitive load,
   progressive disclosure, business-friendly copy, no clutter, and no
   generic-connector feel — the same eight gate items in
   [`ui-ux-design-review-checklist.md`](./ui-ux-design-review-checklist.md)
   §L — apply to every future operator-facing screen, not only the wizard.
7. **Every manual validation must be reproducible.** A manual checklist
   item must name the exact record/action/expected-result triple an
   independent reviewer (ChatGPT, or a future human QA reviewer) can
   re-execute without guessing intent — following the pattern already set
   by [`task-001-core-runtime-readiness.md`](./task-001-core-runtime-readiness.md)'s
   20-item manual validation checklist.

## Test layers

The connector's future test coverage is expected across the following
layers, from cheapest/fastest to most expensive/slowest. A given
implementation task is not expected to exercise every layer — its own
task spec fixes which layers apply, per [Acceptance evidence by task
type](#acceptance-evidence-by-task-type) below.

1. **Static validation.** Python syntax (`py_compile`), manifest literal
   structure (`ast.literal_eval`), XML well-formedness, CSV structural/
   referential integrity, and targeted grep sweeps for out-of-scope
   content — the exact method [`task-001-core-runtime-readiness.md`](./task-001-core-runtime-readiness.md)
   already used and validated as sufficient for a no-runtime environment.
2. **Manifest/module install validation.** Confirms the module is
   installable (dependencies, data-file list, `installable`/`application`
   flags correct) — statically checkable without a runtime today; only a
   live install can confirm it actually loads cleanly (see [Runtime
   limitation strategy](#runtime-limitation-strategy)).
3. **Model/security/access tests.** `ir.model.access.csv` structural
   checks (every group/model pair present, no unintended blank rows) plus,
   once a runtime exists, `TransactionCase` access-denial assertions per
   role.
4. **Service/unit tests.** Pure-Python or ORM-light behavior — e.g. the
   redaction utility's `redact()` function, which needs no live Shopify
   call and can be unit-tested in isolation.
5. **Job/idempotency tests.** Assertions against `shopify.connector.job`'s
   `idempotency_key`/`operation_scope_key` uniqueness constraints and
   state-transition rules — requires a runtime to execute, but the test
   code itself can be written and syntax-validated now.
6. **API client fixture tests.** Transport-injection-seam tests (the
   proposed `_send()` override point in Task 003) that feed canned
   Shopify responses (success, `ACCESS_DENIED`, `THROTTLED`,
   `MAX_COST_EXCEEDED`, timeouts, malformed JSON) without any network call.
7. **Integration tests with mocked Shopify responses.** End-to-end job
   flows (e.g. "test connection pass path writes all mirrors + job/log
   rows") exercised against the fixture set above, still with no real
   Shopify call.
8. **Manual live Odoo validation.** A reviewer with a live Odoo 19 +
   PostgreSQL instance executes a named checklist that closes the gap no
   automated test can close without a runtime — the same pattern as
   [`task-001-core-runtime-readiness.md`](./task-001-core-runtime-readiness.md)'s
   20-item checklist and the Task 002/003 "Manual validation" sections.
9. **Optional development Shopify store validation.** For any task that
   makes a real outbound Shopify call (Task 003 onward), a **development
   store only, never a production shop** — matching Task 003's own
   proposed spec ("On a live Odoo 19 instance **with a development
   store** (never a production shop)") — is used to empirically verify
   the officially-unconfirmed behaviors this project has logged as open
   questions (THROTTLED body shape, invalid-token HTTP status, etc.).
10. **UAT/business scenario validation.** Business-readable end-to-end
    scenarios a non-technical reviewer can execute and judge pass/fail —
    see [`../08-release-readiness/mvp-uat-scenarios.md`](../08-release-readiness/mvp-uat-scenarios.md).
11. **Release-readiness validation.** The go/no-go gate itself — see
    [`../08-release-readiness/mvp-release-readiness-checklist.md`](../08-release-readiness/mvp-release-readiness-checklist.md).

## Runtime limitation strategy

[`task-001-core-runtime-readiness.md`](./task-001-core-runtime-readiness.md)
("Task 001A") established, and re-verified as still true at this sprint's
baseline commit, that **this repository has no Odoo runtime**: no `odoo`
Python package, no `psycopg2`, no PostgreSQL server, no `odoo-bin`, no
Dockerfile/`docker-compose*`, an empty `addons/requirements.txt`, and no
`.github/workflows/` or other CI configuration. Task 001A's own
conclusion — "a future session should add real Odoo-runtime tests once a
test framework/CI is authorized... that authorization still has not
happened" — is unchanged at this sprint's baseline and this package does
not alter that finding. Both proposed task specs already build this
constraint in explicitly: Task 002's and Task 003's "Tests required"
sections each carry an **"Applicability rule (per Task 001A precedent)"**
stating that tests must still be written and syntax-validated even
without a runtime, and that inventing a non-Odoo test harness is
forbidden.

This QA strategy adopts the same rule project-wide, made explicit here so
every future implementation task inherits it without re-deriving it:

- **What must still be written as Odoo tests.** Every implementation task
  that touches ORM behavior (constraints, access rights, computed fields,
  service methods) must still write real `odoo.tests.common.TransactionCase`
  (or equivalent) test files under its module's `tests/` directory, named
  in its own task spec's "Allowed files" list. Writing no test file because
  "it can't be run" is not an acceptable substitute — Task 002 and Task
  003's own specs already commit to this.
- **What can only be syntax/static checked today.** Given no runtime,
  today's actual verification ceiling for any written test is: Python
  syntax compiles; the test imports the model/module correctly; the
  test's logic is reviewable by a human/ChatGPT reviewer for correctness
  against the task's accepted field/constraint schema. No test can
  actually execute, and no PR may claim otherwise.
- **What must be manually validated later.** Every behavior a test
  exercises but cannot run must have a corresponding item in that task's
  "Manual validation" checklist (following the Task 001A / Task 002 /
  Task 003 pattern) so a reviewer with a live Odoo 19 + PostgreSQL
  instance can close the gap without re-deriving what to check.
- **How PRs must disclose unexecuted runtime tests honestly.** Every
  implementation PR must state plainly, in its own description (mirroring
  Task 001A's "Not run — and not claimed" section): (a) which tests were
  written but not executed, (b) the exact runtime dependency missing
  (Odoo package / `psycopg2` / PostgreSQL server / `odoo-bin`), and (c)
  that the manual checklist is the only closure path until that
  infrastructure is separately authorized. A PR that presents an
  unexecuted test as passing, or omits this disclosure, fails
  [`pr-review-checklist.md`](./pr-review-checklist.md) review on that
  basis alone. **No claim that "tests pass" may be made unless the tests
  were actually executed against a real runtime** — this package commits
  every future PR reviewed against it to that standard, extending this
  sprint's own "do not claim tests exist if they are only planned" rule
  to execution status as well as existence.
- **Provisioning the runtime is out of this sprint's scope.** Task 001A
  already named what would be needed (an Odoo 19 package or source
  checkout, `psycopg2`, a running PostgreSQL server, and a test-runner
  invocation) and explicitly declined to provision it as a scope decision
  beyond its own task. This sprint does not change that: provisioning a
  test runtime/CI pipeline remains a distinct, separately-authorized
  future decision, not something a QA-strategy document can authorize by
  writing about it.

## Acceptance evidence by task type

Every future implementation PR must supply the evidence below **in
addition to** its own task spec's named acceptance criteria. This section
does not restate each task spec's full detail (see
[`foundation-test-matrix.md`](./foundation-test-matrix.md) and
[`domain-e2e-test-matrix.md`](./domain-e2e-test-matrix.md) for the
per-task/per-domain breakdown) — it fixes the minimum evidence class per
task family so no future PR can omit a category by oversight.

| Task type | Must prove |
| --- | --- |
| **Credential/security PRs** (Task 002 and any later credential-touching change) | Full 4-role × CRUD access-denial matrix on the credential model; field-level `groups=` holds independently of model ACL; the dummy test token is provably absent from every persisted char/text field except the credential field itself, from every log line, and from every exception; no encryption claim anywhere in code, docstrings, comments, or copy; redaction utility unit tests (keys, `shpat_`/`shprt_` patterns, exact-value scrub, nesting, idempotence) pass. |
| **API client PRs** (Task 003 and any later transport change) | The client shell is structurally read-only (no emittable request body contains `mutation`); dual-path error normalization (HTTP status **and** 200-OK `errors[].extensions.code`) maps into the fixed 16-class registry with no 17th class; every officially-unconfirmed Shopify behavior used in a fixture is labelled unofficial and carries an empirical-verification step; the token never appears in any output (assert via fixture with a dummy token); a second run of the same target-less job type does not collide with the `(store_id, idempotency_key)` uniqueness constraint. |
| **Readiness/lifecycle PRs** (Task 004, Task 005) | Essential-vs-warning tier semantics hold (a failed essential check can never yield an overall pass; a warning never blocks); every state transition (`setup_incomplete`/`connected`/`reconnect_needed`/`disconnected`) is audited with who/when; disconnect provably preserves store/bindings/jobs/logs/audit/mapping/error history while clearing the credential value; reconnect provably re-runs readiness before returning to `connected`; no automatic reconnect exists; no new business job is enqueued or executed while not `connected`. |
| **Product import PRs** | The MBQ-59 pre-create gate (eligibility conditions, then match-quality conditions) is provably enforced before any automated create/bind; match-key priority (existing binding → SKU/internal reference → barcode → manual; name advisory-only) holds; an ambiguous/binding-conflict/duplicate-risk case routes to `blocked_manual_review` with the correct sub-reason; the destructive-write guard blocks a variant write that would delete/omit data without a rendered, confirmed preview; retrospective sync-center visibility is never substituted for the required blocking preview on interactive/batch creates. |
| **Customer import PRs** | Email is the sole automatic match key (phone/name are advisory-only, never automatic); the single flagged fallback partner is used only for genuine no-PII orders, never for ordinary matching failures; an ambiguous customer match holds only the customer-assignment step, never the rest of order import; no customer export path exists (Phase 1 is import-only). |
| **Order import PRs** | An unmatched product line holds the **whole order** (`mapping missing` → `failed_retryable`, never a partial order); the total-check guard (computed evidence sum vs. Shopify's reported total) is mandatory, unbypassable by any flag, and routes any mismatch to `financial total mismatch` (conservative, never silent, never auto-retried); a divergent-currency order (`presentmentCurrencyCode != currencyCode`) is never auto-imported as a normal Odoo sale order in shop currency and is blocked before SO creation, independent of whether the numeric total-check guard happens to reconcile; an `ORDERS_UPDATED` webhook or reconciliation-detected change never silently rewrites an existing sale order's lines/prices/taxes/shipping/discounts/invoices/payments/refunds/fulfillment state. |
| **Inventory sync PRs** | No write occurs without an explicit, non-inferred Odoo-location ↔ Shopify-Location mapping; the first-push guard (preview, explicit confirmation, confirmation record, skip/manual-match for ambiguous items) is satisfied once per mapped pair before that pair's first write; `committed` is never a write target under any circumstance; `inventorySetQuantities` (compare-and-set) behavior is proven safe under a concurrent-write/race scenario; a re-processed event updates the existing inventory-level binding rather than duplicating it. |
| **Fulfillment/tracking PRs** | A fulfillment is created only from a validated `stock.picking` (never guessed, never any other trigger); an unmatched picking (does not resolve to exactly one FulfillmentOrder's open lines) blocks for manual review rather than being force-matched; a live `assignedLocation` read is authoritative over the cached core Location reference for a specific operation, with a mismatch routed to the widened `ambiguous match` class; the notification decision is persisted at enqueue time and never re-read on retry; a tracking-only update never creates a second fulfillment. |
| **UI/wizard/dashboard PRs** | Every screen has empty/loading/success/warning/error/manual-review states (no happy-path-only screen); the setup wizard supports exit-and-resume at every step with no business sync/write job running before Activate; the dashboard renders exactly the nine accepted cards (no tenth card, no chart) with no raw technical logs as primary experience; every error type leads with plain-language reason + suggested fix + owner state, with technical detail only behind an explicit expand; retry affordance is exactly one of the four accepted cases (auto-retry in progress / safe to retry now / fix first / verify before retry) — never an unconditional retry button. |

## Test data policy

- **Dummy credentials only.** Every credential-shaped test value (e.g.
  `shpat_DUMMYDUMMYDUMMY`, matching Task 002's own proposed test-data
  convention) is a clearly-fake string that cannot resolve against any
  real Shopify shop. No real, expired, or revoked Shopify access token may
  appear in any test, fixture, doc, or commit.
- **No real tokens.** This applies to every artifact this project
  produces — code, tests, fixtures, documentation, and chat/PR text alike.
  A real token appearing anywhere is treated as a security incident per
  [`security-redaction-test-plan.md`](./security-redaction-test-plan.md),
  not an ordinary defect.
- **No production Shopify stores.** Any live-Shopify verification step
  (Task 003 onward) uses a **development store only** — the exact
  constraint Task 003's own proposed "Manual validation" section already
  states ("never a production shop").
  Automated/CI fixture tests use canned responses via the transport-
  injection seam and make no live call at all.
  No customer-facing production Shopify store is ever used for testing at
  any layer.
- **No customer PII in fixtures.** Test customer records use synthetic
  names/emails/addresses that resemble real data structurally but are not
  drawn from any real customer, consistent with the accepted protected-
  customer-data minimization posture (Part B §B.10 of
  `master-blueprint-product-customer-sale.md`).
- **Realistic but synthetic products/customers/orders.** Fixtures should
  exercise real-shaped edge cases (multi-variant products up to the
  officially-documented 2,048-variant ceiling class of scenario,
  divergent-currency orders, orders with missing customer PII) without
  using any real store's actual catalog/order data.
- **Deterministic IDs.** Fixture Shopify GIDs, order numbers, and SKUs are
  fixed, reproducible values (not randomly generated at test-run time) so
  a failing test's exact reproduction steps are stable across runs and
  across reviewers. (Per this repository's environment constraints,
  workflow/test scripting must not rely on `Math.random()`/`Date.now()`
  for fixture identity — a concern this policy generalizes for any future
  test-generation tooling.)
- **Clean rollback data.** Every test's fixtures must be creatable and
  destroyable without leaving orphaned records — matching the project-wide
  no-unlink-by-users ACL posture: automated tests running as a test
  runner (not as a connector role) may create and roll back their own
  fixtures inside a transaction, but no fixture may depend on a manual
  cleanup step a future test run would otherwise inherit.

## Quality gates

The following each **block merge** of an implementation PR, regardless of
how much other work the PR contains correctly:

- **Token leak.** Any Shopify credential value appearing in a log,
  exception, job record, store mirror, chatter entry, or any other
  persisted or emitted surface.
- **Duplicate creation.** A re-run of an import/sync operation (retry,
  repeated webhook, reconciliation pass) creating a second Odoo record for
  the same Shopify entity instead of updating the existing binding.
- **Incorrect access rights.** Any role other than Admin gaining read,
  write, create, or `fields_get()` access to the credential model or
  field; any group gaining `perm_unlink` on any core model; any access
  matrix diverging from the accepted AR-019 four-group design.
- **Failed idempotency.** A duplicate/concurrent operation against the
  same `(store, target)` tuple producing two applied writes instead of one
  detected-as-same operation.
- **Unsafe retry.** A blind retry of an ambiguous-outcome operation
  (timeout/connection-loss with unknown result) instead of a verification
  read first, per the accepted ambiguous-outcome rule (DEC-009); or any
  flag/setting/role-based "force retry" affordance that bypasses a job's
  classified retry case.
- **Raw technical error as primary UX.** An HTTP status code,
  `extensions.code` token, stack trace, or raw response body shown as the
  primary copy of any error surface instead of a plain-language reason +
  fix, with technical detail confined to an explicit expand (RA-016).
- **Silent data loss.** Any operation that unlinks, overwrites, or
  discards a prior state (job/log history, credential-clear-on-disconnect
  exceptions aside, matching records, financial evidence) without an
  audit trail or without the explicit, accepted rule that permits it.
- **Unsupported platform assumption.** Any code, comment, or copy that
  asserts an unverified Shopify/Odoo behavior as fact instead of labelling
  it an open question with an empirical-verification step (per this
  project's official-source rule).
- **Unreviewed scope expansion.** Any file changed outside the task's own
  named allowed-files list, or any mechanism (model, field, group, job
  type, error class, manual-review sub-reason) introduced beyond what an
  accepted decision already authorizes.
