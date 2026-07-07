# Foundation Test Matrix

> QA planning matrix for the credential/connection/API-client/readiness
> foundation tasks (Task 001 through Task 006), part of the
> [MVP QA and Test Strategy](./mvp-qa-test-strategy.md) package. Baseline:
> `Shopify-connector` at `f74aaf204745ce0087733870fe56bdda74bfa79a` (PR #92
> merge). **Docs-only. No implementation. No gate opened.** Task 001 is
> the only merged/implemented task; Tasks 002–006 remain proposed/not
> authorized, per
> [`../07-implementation-plan/credential-connection-foundation-task-plan.md`](../07-implementation-plan/credential-connection-foundation-task-plan.md)
> and [`AR-024`](./architecture-review-log.md). This document defines what
> each future task's own PR must prove — it does not itself run, execute,
> or claim any test result.

## Status

**Proposed for ChatGPT review. Docs-only. No implementation. No gate
opened. Does not create tests.** Every row below describes a **future**
test/validation requirement for a task that has not yet started coding
(Tasks 002–006) or QA-closes a task that has already merged (Task 001, via
[`task-001-core-runtime-readiness.md`](./task-001-core-runtime-readiness.md),
already complete and not reopened here).

## How to read this matrix

Each task section below states: test objective; automated tests required;
manual validation required; security checks; data integrity checks;
negative/error cases; rollback checks; acceptance-blocker examples. All
detail is sourced from the accepted task specs
([`task-001-core-module-scaffold.md`](../07-implementation-plan/task-001-core-module-scaffold.md),
[`task-002-credential-storage-redaction-proposed.md`](../07-implementation-plan/task-002-credential-storage-redaction-proposed.md),
[`task-003-api-client-test-connection-proposed.md`](../07-implementation-plan/task-003-api-client-test-connection-proposed.md))
and the task-plan summaries for Task 004–006 in
[`credential-connection-foundation-task-plan.md`](../07-implementation-plan/credential-connection-foundation-task-plan.md).
Where a task spec does not yet exist as its own document (Tasks 004–006),
this matrix works from the task plan's own objective/acceptance-criteria/
test-requirements summary and flags anything still open as such — it does
not invent detail the task plan does not state.

---

## Task 001 — Core module scaffold (merged, QA-closed)

**Status:** Merged via PR #88 (merge commit
`b55490743fb1f5c9ea33831b94605b9ead4229c0`); QA-closed by
[`task-001-core-runtime-readiness.md`](./task-001-core-runtime-readiness.md)
("Task 001A"). This section summarizes that closure for matrix
completeness — it does not reopen or repeat the closure work.

- **Test objective.** Confirm the merged `shopify_connector_core` scaffold
  (six models, four groups, 20 ACL rows) is structurally correct and
  contains no out-of-scope content, to the extent verifiable without a
  live Odoo runtime.
- **Automated tests required.** None were added — Task 001A found no
  existing repo test convention and no runtime to validate against, and
  explicitly declined to invent a non-Odoo test harness. Static checks
  substituted: Python compile, manifest `ast.literal_eval`, XML
  well-formedness, CSV structural/referential integrity, out-of-scope grep
  sweep — all passed.
- **Manual validation required.** The 20-item checklist in Task 001A
  (install on a clean Odoo 19 database; confirm six models in `ir.model`;
  confirm no credential/token/secret fields exist; unique-constraint and
  `@api.constrains` checks; access-rights spot-check against AR-019) —
  not yet executed against a live runtime; remains open until a runtime
  is authorized.
- **Security checks.** Grep sweep for
  `credential|token|secret|password|api[_-]?key` found no field, only
  doc-string prose disclaiming such fields; grep for
  `http\.Controller|import requests|graphql|@http\.route` and `ir\.cron`
  found no matches; no menu/action/view/wizard found.
- **Data integrity checks.** CSV structural check confirmed every
  `(model, group)` pair among the 5×4=20 combinations is present exactly
  once, every `perm_*` value is 0 or 1, and every `group_id`/`model_id`
  resolves correctly.
- **Negative/error cases.** Not executable without a runtime — deferred to
  the manual checklist (e.g. duplicate `shop_domain` must raise a unique
  constraint; `job_source='odoo_event'` without `trigger_origin` must
  raise `ValidationError`).
- **Rollback checks.** Task 001A: rollback is a single revert of the
  scaffold PR before any dependent module exists; no downstream migration
  or data cleanup required.
- **Acceptance-blocker examples.** A credential/token/secret field
  appearing anywhere in the module; a webhook/controller/cron artifact
  appearing; any ACL row missing or duplicated; any menu/action/view/
  wizard file present.

---

## Task 002 — Credential storage, masking, redaction foundation (proposed, not authorized)

- **Test objective.** Prove the Admin-only `shopify.connector.store.credential`
  model, the non-secret status mirrors on `shopify.connector.store`, the
  set/replace/clear service methods, and the redaction utility behave
  exactly as specified, with **zero Shopify API calls, zero views, and
  zero UI** anywhere in the diff.
- **Automated tests required** (per the proposed spec's own "Tests
  required" section, to be written as Odoo `TransactionCase` tests under
  `addons/shopify_connector_core/tests/`):
  1. Access matrix: auditor/operator/reviewer each raise `AccessError` on
     read/write/create/unlink of the credential model; `fields_get()`/
     search expose nothing; Admin succeeds on read/write/create, denied on
     unlink.
  2. Field access: field-level `groups=` on `access_token` holds
     independently of model ACL.
  3. Redaction: key-based redaction (including `Authorization` header
     casing), `shpat_`/`shprt_` pattern hits inside longer strings,
     exact-value scrub of an arbitrary-format dummy token, nested
     dict/list, idempotence, non-string passthrough.
  4. Service behavior: set → mirrors flip correctly; replace → stamps and
     resets verification state; clear → value emptied and mirrors reset;
     one credential row per store enforced (duplicate create raises); the
     dummy token is absent from every persisted field except
     `access_token` itself; **no `job.log` row is created by any Task 002
     code path** (the merged ACL grants no group create on `job.log`).
  5. No-read-back (only if the compute-blank hardening variant is
     adopted): ORM read of `access_token` returns empty for every user
     including Admin; `_get_access_token()` still returns the value
     internally.
- **Manual validation required** (per the proposed spec, extending the
  Task 001A checklist): module upgrade shows the credential model in
  `ir.model` with exactly one new ACL row; each non-admin role denied on
  every operation; Admin can set/replace/clear a dummy token via the
  service with mirrors updating correctly; `ir.model.fields` shows
  `access_token` restricted to the Admin group with no view referencing
  it anywhere; a grep of database logs/audit surfaces for the dummy token
  returns zero hits outside the credential column; confirm no menu/
  action/view/wizard/controller/cron exists and no Shopify call is
  possible (no client exists yet).
- **Security checks.** The credential-security checklist
  ([`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md))
  sections A (no encryption claim anywhere), B (no read-back on any
  surface for any role), C (token never in logs/chatter/job logs/
  exceptions), D (shared redaction utility, key/value pattern coverage),
  and E (Admin-only ACL + field `groups=` + justified `sudo()` — the
  *only* sanctioned `sudo()` in this task is inside `_get_access_token()`)
  all apply as **[Gate]** items.
- **Data integrity checks.** `store_id` unique constraint on the
  credential model (one row per store); `credential_state` values
  restricted to `absent`/`present`/`invalid`; status mirrors on `store`
  stay consistent with the credential model's state after every service
  call (single-writer rule).
- **Negative/error cases.** Duplicate credential-row create for the same
  store raises; non-admin CRUD attempts raise `AccessError`; a malformed/
  arbitrary-format token still gets exact-value-scrubbed by redaction
  even though it doesn't match the `shpat_`/`shprt_` prefix patterns.
- **Rollback checks.** Single-PR revert; nothing depends on Task 002 yet;
  uninstalling/reverting drops the credential model and mirror fields —
  stored tokens are lost and re-enterable by the Admin; no business data
  is affected; a partially-failed deployment (ACL loaded but model not)
  recovers via module upgrade after revert, no migration needed either
  direction.
- **Acceptance-blocker examples.** Any view/menu/action/wizard artifact in
  the diff; any Shopify API call code; the dummy token appearing in any
  log/audit/mirror surface other than `access_token`; any `sudo()` outside
  the one sanctioned accessor; any encryption claim in code, docstring,
  comment, or copy.

---

## Task 003 — API client shell and test connection (proposed, not authorized)

- **Test objective.** Prove the single GraphQL transport boundary
  (`shopify.connector.api.client`) is structurally read-only, that
  dual-path error normalization maps correctly into the fixed 16-class
  registry, and that the test-connection service writes the correct
  store mirrors and job/log records with no token ever appearing in any
  output.
- **Automated tests required** (per the proposed spec):
  1. Transport fixtures via the injection seam: success; `ACCESS_DENIED`;
     `THROTTLED` (labelled unofficial); `MAX_COST_EXCEEDED` (official
     sample shape); `INTERNAL_SERVER_ERROR` + `requestId`; HTTP
     401/402/423/429/500; timeout; malformed JSON; version fall-forward —
     each asserting the mapped error class and plain-language reason.
  2. Redaction: a fixture whose body/headers embed a dummy token — assert
     the token is absent from the raised exception's `str()`/`args`, every
     `job.log` field, and every store mirror.
  3. Test-connection behavior: pass path writes all mirrors + scope
     snapshot + job/log rows; identity-mismatch path
     (`shop.myshopifyDomain` vs. `store.shop_domain`); the missing-
     credential precondition fails cleanly without an HTTP call
     (`shop_domain`/`api_version` are `required=True` by construction, so
     this is a unit-level guard test); auth-failure path sets
     `credential_state='invalid'`.
  4. Read-only guarantee: no emittable request body contains `mutation`;
     no Odoo business model is written.
  5. Job accounting: exactly one job per run; `job_source =
     'setup_readiness_check'`; the job reaches a terminal state; **a
     second run on the same store succeeds** (no
     `store_idempotency_key_uniq` collision — the per-run `payload_hash`
     nonce resolution must be proven).
- **Manual validation required** (per the proposed spec, on a live Odoo 19
  instance **with a development store, never a production shop**): a
  dummy-invalid token fails with the auth class and no token in any log;
  a valid development-store token passes with mirrors/scope snapshot
  populated and job/log rows present and redacted; the empirical answers
  to the open Shopify behaviors (actual HTTP status for an invalid token;
  actual THROTTLED body shape if reproducible; whether `shop`/
  `currentAppInstallation` needed any scope; actual missing-scope error
  shape) are recorded, not asserted, and filed as a follow-up research
  note; confirm read-only — no product/customer/order/inventory/
  fulfillment record changed on either side, no webhook appeared in the
  store.
- **Security checks.** Every exception, log line, `job.log` field, and
  store mirror passes through Task 002's `redact()` utility; request
  headers are never logged; the client never exposes a mutation method in
  this task; all six **[Gate]** items in
  [`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md)
  §G (test connection and readiness) apply.
- **Data integrity checks.** Dual-path normalization (HTTP status *and*
  200-OK `errors[].extensions.code`) never introduces a 17th error class;
  the `X-Shopify-API-Version` response header is compared to
  `store.api_version` on every call, with a mismatch surfaced as a
  fall-forward warning, never silent success.
- **Negative/error cases.** Every fixture in the transport-fixture list
  above; an officially-undocumented shape (THROTTLED body, invalid-token
  HTTP status, missing-scope shape) must be handled defensively and
  labelled unofficial, never asserted as confirmed platform behavior.
- **Rollback checks.** Single-PR revert; Task 002's model/utility
  untouched; store mirror fields simply stop refreshing (harmless stale
  data); no migration; no data cleanup; no Shopify-side artifacts exist to
  clean up given the read-only guarantee.
- **Acceptance-blocker examples.** Any request body the client can emit
  containing `mutation`; a token appearing in any output; an invented,
  unlabelled claim about undocumented Shopify error-shape behavior; a
  repeat test-connection run colliding on the job uniqueness constraint;
  any pacing/backoff policy implemented (MBQ-51 must remain untouched —
  the shell only surfaces the throttle signal).

---

## Task 004 — Readiness check substrate (proposed, not yet a standalone task spec)

- **Test objective.** Prove the readiness engine correctly separates
  essential ("must pass") from warning ("good to fix") checks per the
  accepted DEC-018 MBQ-06 split, runs as a `setup_readiness_check` job,
  and never yields an overall pass when an essential check fails.
- **Automated tests required** (per the task plan's summary — exact test
  file names are this task's own future spec detail, not fixed here):
  tier semantics (a failed essential check can never produce an overall
  pass; a warning never blocks); per-check result persistence in
  `job.log.payload_snapshot`; summary mirroring to
  `store.last_readiness_result/_at`; redaction of check detail; the
  domain-seam check-registration mechanism.
- **Manual validation required.** Not yet detailed beyond the task plan's
  summary — this is this task's own open detail, flagged here rather than
  invented. At minimum, a reviewer should confirm the nine accepted
  essential checks (credential validity/test connection; required scopes
  granted; API-version health; store identity confirmed; `web.base.url`
  reachability; webhook HMAC secret only if webhooks enabled; cron/queue
  health; ≥1 mapped Location where inventory/fulfillment enabled;
  intentional domain enablement) are each individually testable and each
  individually named in the readiness UI, per DEC-018.
- **Security checks.** Checks are read-only; redaction applies to
  per-check result text exactly as it does to job logs elsewhere.
- **Data integrity checks.** No new readiness-result model is introduced
  (avoids over-fragmentation per the accepted RA-012 pattern) — results
  live in `job.log.payload_snapshot`, structured JSON, redacted.
- **Negative/error cases.** Webhook-HMAC and mapped-location checks are
  registered as *pending slots*, not implemented, in this task — a test
  must confirm they do not silently report a false pass.
- **Rollback checks.** Single-PR revert; mirrors remain harmlessly stale.
- **Acceptance-blocker examples.** A dashboard/readiness surface reporting
  an overall pass while an essential check is failing; any check that is
  not read-only; any UI/view/menu/action artifact (this task remains
  models/tests only, per the task plan).

---

## Task 005 — Connection lifecycle actions (proposed, not yet a standalone task spec)

- **Test objective.** Prove every lifecycle transition (activate,
  disconnect, reconnect, the `reconnect_needed` auto-transition on auth
  failure) is audited, that disconnect preserves history while clearing
  the credential, and that reconnect always re-runs readiness before
  returning to `connected`.
- **Automated tests required** (per the task plan's summary): full
  transition matrix; history-preservation assertions on disconnect;
  credential-clear assertions on disconnect; enqueue-block assertions
  while the store is not `connected`.
- **Manual validation required.** Not yet detailed beyond the task plan's
  summary — flagged as this task's own open detail. At minimum: disconnect
  a store with existing jobs/logs/bindings and confirm all history remains
  queryable; reconnect and confirm readiness re-runs and business sync
  does not resume until it passes.
- **Security checks.** No new `sudo()` beyond what Tasks 002/003 already
  established; the store/settings `perm_create` ACL gap this package
  surfaced (§Security and permissions,
  [`credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md))
  is this task's own decision point, not resolved here.
- **Data integrity checks.** Disconnect clears `access_token`/
  `credential_present`/`credential_state` but never unlinks the store,
  credential row, settings, bindings, jobs, logs, audit, or mapping/error
  history (MBQ-08); reconnect is explicit and audited, never automatic.
- **Negative/error cases.** An in-flight job at disconnect must be
  cancelled with an audit reason or held in an accepted blocked state,
  never silently dropped (Part A §I.4 — exact disposition remains an open
  item this task's own spec must fix).
- **Rollback checks.** Single-PR revert; states remain valid data.
- **Acceptance-blocker examples.** Any automatic reconnect; any history
  loss on disconnect; any business job enqueued or executed while the
  store is not `connected`; any UI/wizard/webhook artifact (this task
  remains models/security/tests only).

---

## Task 006 — Setup wizard UI (horizon only, no UI gate open)

- **Test objective.** Not yet in scope for testing — Task 006 cannot start
  until a **separate, explicit ChatGPT UI-implementation-gate opening**
  exists (none does; AR-023 kept the UI gate closed), and until Tasks
  002–005 are merged. This row exists so the matrix names the eventual
  requirement rather than omitting it.
- **Automated/manual validation required (future).** The accepted
  [`ui-ux-design-review-checklist.md`](./ui-ux-design-review-checklist.md)
  gates in full, plus the accepted UI/UX task map's Group 3 criteria:
  exit-and-resume at every one of the 11 wizard steps; business sync
  provably blocked until Activate; an accurate final readiness summary.
- **Security checks (future).** Zero read-back of the credential value at
  any wizard step (masked entry only, per Step 3); no encryption claim in
  any wizard copy.
- **Data integrity checks (future).** Wizard state persists every choice
  on durable records so re-entering the wizard resumes rather than
  restarting; no domain sync/write job runs before the final Activate
  step.
- **Negative/error cases (future).** Test Connection failure keeps the
  operator on the step with a named cause + fix, no store-state change; an
  essential readiness check failure blocks Activate with the failing
  checks listed.
- **Rollback checks (future).** Revert of the future wizard PR; the
  wizard is UI over Tasks 002–005's services, so no data migration is
  implied.
- **Acceptance-blocker examples (future).** Any step that cannot be exited
  and resumed; any inventory first-push executed automatically during the
  wizard; any pre-selected default for domain direction, source-of-truth,
  or notification opt-in (none of these may default silently, per the
  accepted safety guards in
  [`../02-product/mvp-user-flows-and-state-models.md`](../02-product/mvp-user-flows-and-state-models.md)
  Flow 1).

---

## Detailed rows required by this sprint

### Credential access matrix

| Role | Read credential model | Write | Create | Unlink | `fields_get()` |
| --- | --- | --- | --- | --- | --- |
| Auditor | Denied (`AccessError`) | Denied | Denied | Denied | Empty (field stripped) |
| Operator | Denied | Denied | Denied | Denied | Empty |
| Reviewer | Denied | Denied | Denied | Denied | Empty |
| Admin | Allowed (service methods only — no view) | Allowed (service methods only) | Allowed (service methods only) | **Denied (no unlink for anyone, ever)** | Field-`groups`-restricted to Admin |

A future test must assert every non-Admin cell raises `AccessError` (not
merely returns empty), and that Admin's access is exercised only through
the named service methods (`action_set_token`/`action_replace_token`/
`action_clear_token`) since **no view is ever created** for this model.

### Token redaction

Covered in full detail in
[`security-redaction-test-plan.md`](./security-redaction-test-plan.md);
summarized here as a foundation-task acceptance item: every persisted or
emitted surface a foundation task can write (job logs, exceptions, store
mirrors, `credential_last_failure_reason`) must pass a dummy `shpat_…`
token through `redact()` and assert its absence, per Task 002/003's own
"Tests required" sections.

### No token read-back

No view is ever defined for the credential model in Task 002 (core
remains zero-UI); the only future entry surface (wizard Step 3 /
settings-band replacement, Task 006 horizon) is write-only: masked input,
submitted to the service method, cleared, never re-populated from
storage. This holds for **every role, including Admin** — the accepted
AR-023 binding-honesty rule. If ChatGPT adopts the compute-blank
hardening variant, a test must additionally assert that even a direct ORM
read of `access_token` returns empty for every user.

### API client error normalization

Every response signal — HTTP status *and* 200-OK GraphQL
`errors[].extensions.code` — must normalize into exactly one of the fixed
16 error classes (no 17th), per the dual-path mapping table in
[`credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md)
(§Test connection contract). A future test suite must cover every row of
that mapping table plus the "unparseable/unexpected" catch-all into
`unknown_system_error`.

### Test connection read-only guarantee

A future test must assert, structurally (not just by inspection), that no
method the Task 003 client shell exposes can emit a GraphQL `mutation`
string, and that the only Odoo-side writes are the named store mirrors,
`credential_state`, and job/job.log rows — never a business record.

### Readiness essential/warning split

A future test must assert the essential set (nine checks, DEC-018 MBQ-06)
each individually blocks `connected`/Activate on failure, and that every
other candidate check is warning-tier and **never** blocks setup
completion — the two tiers must be behaviorally, not just visually,
distinct.

### Disconnect clears credential but preserves history

A future test must create a store with credential, jobs, logs, and
bindings, disconnect it, and assert: `access_token` empty,
`credential_present=False`, `credential_state='absent'`, `store.state =
'disconnected'`, while every job, log, binding, and audit record remains
queryable and unmodified in content (only new disconnect-audit entries
are added).

### Reconnect re-runs readiness

A future test must assert that reconnecting a store transitions through
credential re-entry → test connection → readiness re-run → `connected`,
and that **skipping** the readiness re-run is structurally impossible
(not just discouraged by UI copy) — a reconnect that reaches `connected`
without a readiness result is a defect by definition (MBQ-08).

### Setup wizard exit/resume behavior

Per [`../02-product/mvp-user-flows-and-state-models.md`](../02-product/mvp-user-flows-and-state-models.md)
Flow 1: exiting the wizard at any of the 11 steps before Activate leaves
the store in `setup_incomplete`, lists the exact remaining steps, and
guarantees **no business sync/write job runs**; only read-only
`setup_readiness_check`/`export_preview_dry_run` jobs may run. Re-entering
the wizard must resume from the persisted choices, never restart from
Step 1. This is a Task 006-horizon test requirement, named here so the
foundation matrix does not omit it.

### No business sync before activation

A future test (spanning Task 004/005 and, later, every domain slice) must
assert that while `store.state != 'connected'`, no business (non-read-
only) job can be enqueued or executed — enforced at both enqueue time and
execution time, per the accepted queue-substrate rule
([`credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md)
§Connection lifecycle table).
