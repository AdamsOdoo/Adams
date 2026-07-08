# DEC-024 — Task 005 Connection Lifecycle Closure

## Status

**Accepted.**

## 1. Accepted outcome

**Task 005's connection-lifecycle substrate is complete and merged.** PR
#121 ("Task 005 connection lifecycle actions") merged into
`Shopify-connector` on 2026-07-08, merge commit
`8f2d7846fb70ecb62d2353c3f18ca3bbcbb96e82` (PR #121 head commit before
merge: `f2ce29c0422258f92877f6464b1746455d28dcb5`). Live Odoo.sh runtime
validation against a real Odoo 19 + PostgreSQL registry passed at that head
commit — focused `TestConnectionLifecycle` (`0 failed, 0 error(s) of 41
tests`) and the full `shopify_connector_core` module suite (`0 failed, 0
error(s) of 123 tests`). Full evidence is recorded in
[`../05-qa/task-005-validation-results.md`](../05-qa/task-005-validation-results.md).
This closure record accepts that outcome; it authorizes no new code.

Delivered scope, exactly as scoped by
[`DEC-022-task-005-scope.md`](./DEC-022-task-005-scope.md):

- `action_activate()`
- `action_disconnect()`
- `action_reconnect()`
- `action_mark_reconnect_needed()`
- Business-job enqueue-time gating and execution-time gating on store
  connection state
- Credential-service state invalidation (added during PR #121's own
  runtime-fix revisions; see "Lessons learned" below)
- Lifecycle and credential-service tests

## 2. Accepted lifecycle rules

The following rules, as implemented and validated in PR #121, are accepted
as the binding connection-lifecycle behavior for `shopify_connector_core`:

- **`action_activate()` succeeds only** when the store has a credential
  present, a credential row exists, `credential_last_verified_at` is
  truthy, the last test-connection result is `pass`, the last readiness
  result is `pass` or `warning`, and the last readiness check is fresh
  enough (`last_readiness_at` truthy and not older than
  `credential_last_verified_at`). Any failure raises `UserError` before any
  write; no audit job is created on rejection.
- **Setting or replacing a token on a `connected` store moves it to
  `reconnect_needed`** (`action_set_token()` / `action_replace_token()`),
  so a changed credential can never leave a store looking `connected` on
  stale verification evidence.
- **Clearing a token on a `connected` or `reconnect_needed` store moves it
  to `disconnected`** (`action_clear_token()`).
- **Business jobs can only be created and run when the owning store is in
  the `connected` state** — enforced at both enqueue time and execution
  time.

## 3. Explicit non-decisions

This closure record does **not** decide, resolve, authorize, or claim any
of the following:

- No OAuth implementation is authorized or claimed.
- No setup wizard is authorized or claimed.
- No UI is authorized or claimed (no views, menus, actions, wizards, or
  controllers).
- No product, customer, or order sync (or any other domain sync) is
  authorized or claimed.
- **No VAL-B2 pass is claimed.** No live Shopify Admin API connection was
  made or attempted by Task 005 or its validation. VAL-B2 remains
  deferred, not passed, per
  [`DEC-021-val-b2-deferral-for-task-004.md`](./DEC-021-val-b2-deferral-for-task-004.md).
- **No MBQ-05 full resolution is claimed.** The scalable
  many-unrelated-customer distribution/auth architecture remains
  undecided. MBQ-05 remains partially routed / open, per
  [`DEC-023-token-acquisition-and-val-b2.md`](./DEC-023-token-acquisition-and-val-b2.md)
  and the MBQ-05 row in
  [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
- **No TD-002 closure is claimed.** The `read_fulfillments` readiness-scope
  correctness concern is unaffected by Task 005 and remains Open, per the
  TD-002 row in
  [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md).
- No security/ACL change is made. The `perm_create` store/settings ACL
  posture decided in DEC-022 (remains closed) is unchanged.

## 4. Lessons learned from runtime failures

Odoo.sh runtime validation of PR #121 surfaced two real defects that no
static review, adversarial-review pass, or `py_compile` check across three
prior PR revisions had caught. Both are recorded here as binding lessons
for future task closures, in addition to their detailed record in
[`../05-qa/task-005-validation-results.md`](../05-qa/task-005-validation-results.md)
and the dated PR #121 revision entries in
[`../01-research/research-handoff.md`](../01-research/research-handoff.md):

- **Static review missed real Odoo ORM timestamp behavior.** A freshness
  guard comparing `credential.write_date` (an ORM-managed timestamp) against
  a manually-stamped field (`credential_last_verified_at`) passed every
  static check but failed 5 tests live on Odoo.sh, because it depended on
  actual Postgres `write_date` write-timing behavior that no static
  inspection exercises. **Any future freshness guard comparing an
  ORM-managed timestamp field (`write_date`, `create_date`) against a
  manually-stamped field should be treated as requiring actual
  Odoo-runtime validation before being trusted** — this mechanism is now a
  rejected approach for this codebase (see
  [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)).
- **Credential mutation must invalidate both the verification evidence and
  the derived `store.state`.** Clearing `credential_last_verified_at` alone
  was not sufficient: `action_replace_token()` initially left a `connected`
  store's `state` unchanged, which would have let business-job gating
  (keyed on `state == 'connected'`) treat an unverified changed credential
  as still connected — a real product risk, not a style nit. Fixed by
  adding lifecycle state invalidation inside the credential service itself,
  at the credential mutation's actual source.

## 5. Next task candidates (not selected by this decision)

The following are named as candidate next tasks for control-room
consideration. **This decision does not select or authorize any of
them** — the next implementation task remains a separate, later ChatGPT
act, per `CLAUDE.md` §9:

- **Task 006 — setup/readiness UX docs gate.**
- **Task 006 — sync engine skeleton gate.**
- **Task 006 — manual product import architecture gate.**
- **Task 006 — VAL-B2/token validation closure gate.**

## 6. Consequences

- **Positive:** unblocks the `connected` / `setup_incomplete` /
  `reconnect_needed` / `disconnected` state-gating mechanism that Task
  005's own scope decision (DEC-022) identified as a prerequisite for
  domain sync enqueue; closes out PR #121 with confirmed live-runtime
  evidence rather than static-only evidence.
- **Negative / trade-offs:** does not close VAL-B2, does not advance the
  token-acquisition decision, and does not fix TD-002; the setup wizard,
  readiness dashboard, and product sync all remain blocked on their own
  separate gates.
- **Follow-ups:** none created by this closure beyond the next-task
  candidates listed above (control-room selection only); no new technical
  debt introduced (docs-only session).

## 7. Review status

**Accepted.** This closure record's own PR must still be reviewed and
merged into `Shopify-connector` by ChatGPT/control-room instruction before
it is operative, mirroring the review precedent of prior task-gate and
task-closure documents (e.g. `DEC-022-task-005-scope.md` §10).

## Evidence / references

- PR #121 (merged), merge commit `8f2d7846fb70ecb62d2353c3f18ca3bbcbb96e82`
  — access: Accessible via this repository's own git history, observed
  2026-07-08.
- [`../05-qa/task-005-validation-results.md`](../05-qa/task-005-validation-results.md)
  — full live-validation evidence record.
- [`DEC-022-task-005-scope.md`](./DEC-022-task-005-scope.md) — the accepted
  Task 005 scope this closure record accepts the delivery of.
- [`DEC-021-val-b2-deferral-for-task-004.md`](./DEC-021-val-b2-deferral-for-task-004.md)
  — VAL-B2 deferred status, unchanged by this closure.
- [`DEC-023-token-acquisition-and-val-b2.md`](./DEC-023-token-acquisition-and-val-b2.md)
  — MBQ-05 partially-routed status, unchanged by this closure.
- [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md)
  — TD-002 Open status, unchanged by this closure.
