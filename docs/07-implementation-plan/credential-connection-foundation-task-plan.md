# Credential and Connection Foundation Task Plan

> Sequencing plan for the future implementation tasks that build the
> credential / connection / test-connection / API-client / readiness
> foundation, derived from
> [`../03-architecture/credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md)
> (the architecture package this plan executes). Companion proposed task
> specs: [`task-002-credential-storage-redaction-proposed.md`](./task-002-credential-storage-redaction-proposed.md),
> [`task-003-api-client-test-connection-proposed.md`](./task-003-api-client-test-connection-proposed.md).

## Status

**Proposed for ChatGPT review. Docs-only. No implementation.** This plan
creates no task authorization, opens no gate, and writes no code. Every
task below requires (a) ChatGPT acceptance of the architecture package,
(b) an explicit ChatGPT gate-opening act for its scope (per AR-021, each
later gate is its own separate act), and (c) its own final `CLAUDE.md` §9
task prompt.

## Why this plan exists

The accepted state after PR #90/#91 is: posture decided (MBQ-04 Option B,
AR-022), UX decided at design level (AR-023), core substrate merged (Task
001), and a hard dependency chain recorded in the accepted UI/UX task map
— Group 4 (credentials) "must not start before" the MBQ-04
implementation-planning task, and Group 4 "blocks Groups 3/5" (wizard,
readiness). This plan turns that recorded dependency into small,
reviewable coding tasks. It unlocks, in order:

- **credential code** (Task 002) — the storage/redaction substrate
  everything authenticated depends on;
- **API client + test connection** (Task 003) — the single transport
  boundary and the first real Shopify call;
- **readiness checks** (Task 004) — the essential/warning check engine;
- **connection lifecycle actions** (Task 005) — disconnect/reconnect/
  activation as audited service actions;
- **setup wizard UI** (Task 006 horizon) — buildable only after the UI
  gate opens, consuming Tasks 002–005 as its mechanics.

## Proposed implementation sequence

Global rules for every task: small PR; allowed/forbidden files named;
tests or an explicit justified exception; rollback notes; handoff update;
stop at the objective; no second task before ChatGPT reviews the first
(AR-021 §5). Nothing below touches `adams_base`, `main`, or plain `dev`.

### Task 002 — Credential storage, masking, redaction foundation

- **Objective:** create `shopify.connector.store.credential` (Admin-only),
  the store status mirrors, the credential service methods
  (set/replace/clear + internal accessor), and the redaction utility —
  exactly as specified in the architecture package.
- **Allowed files:** see the full proposed spec
  ([`task-002-credential-storage-redaction-proposed.md`](./task-002-credential-storage-redaction-proposed.md))
  — `shopify_connector_core` model/security/tools/test files only.
- **Forbidden files:** everything else — no API client, no views, no
  wizard, no controllers, no cron, no domain files, no CI.
- **Prerequisites:** ChatGPT acceptance of the architecture package
  (AR-024) including its open decision points (token_variant vocabulary,
  compute-blank variant yes/no, scope-snapshot placement); an explicit
  gate-opening act naming Task 002; a final §9 task prompt.
- **Acceptance criteria (summary):** model + mirrors + service + redaction
  exist; non-admin roles provably denied; token provably absent from all
  logs/exceptions in tests; no view/API-call/wizard artifact exists.
- **Test requirements (summary):** access-denial matrix (4 roles × CRUD),
  redaction unit tests (keys, `shpat_`/`shprt_` patterns, exact-value
  scrub, nesting, idempotence), service-method behavior
  (set/replace/clear, mirror consistency), no-value-in-audit tests.
- **Rollback notes:** single-PR revert; no dependents yet; dropped tokens
  are re-enterable; no business data affected.
- **Risks:** sudo misuse; accidental view exposure later (mitigated
  structurally by the dedicated model); redaction gaps (mitigated by
  belt-and-braces enforcement + tests).
- **Definition of done:** per `CLAUDE.md` §9 / template §7, plus the
  credential-security checklist
  ([`../05-qa/credential-security-redaction-review-checklist.md`](../05-qa/credential-security-redaction-review-checklist.md))
  passing, plus ChatGPT review.
- **Must not include:** API client, test connection, setup wizard, UI/
  views of any kind, webhooks, cron, domain logic, encryption claims.

### Task 003 — API client shell and test connection

- **Objective:** create the `shopify.connector.api.client` AbstractModel
  (GraphQL-only, read-only in this task), error normalization to the
  fixed 16 classes, throttle-signal surfacing, and the test-connection
  service writing store mirrors + `setup_readiness_check` job/logs.
- **Allowed/forbidden files, contracts, guarantees:** see the full
  proposed spec
  ([`task-003-api-client-test-connection-proposed.md`](./task-003-api-client-test-connection-proposed.md)).
- **Prerequisites:** Task 002 merged and reviewed; a gate-opening act that
  **for the first time authorizes outbound Shopify API calls** (AR-021
  explicitly forbade them — this is a real gate widening ChatGPT must
  perform consciously); resolution of the `core_test_connection`
  job-type vocabulary question; a final §9 prompt.
- **Acceptance criteria (summary):** client + test connection exist and
  are read-only; dual-path error normalization proven by fixtures; token
  never appears in any output; store mirrors update; empirical
  verification of the open Shopify behaviors recorded.
- **Test requirements (summary):** transport-injection fixtures for every
  signal class; redaction-in-exception tests; identity-mismatch,
  fall-forward, scope-snapshot tests; read-only guarantee test (no
  mutation string in any request the client can emit in this task).
- **Rollback notes:** single-PR revert; Task 002 unaffected; store mirror
  fields remain (empty/stale) without harm.
- **Risks:** invented Shopify error shapes (mitigated: fixtures labelled
  unofficial where docs are silent; empirical verification steps);
  accidental mutation surface (mitigated: no mutation API in the shell).
- **Definition of done:** §9 template + checklist + ChatGPT review.
- **Must not include:** domain sync, mutations, webhooks, cron, wizard,
  UI, dashboard, pacing policy (MBQ-51 stays open).

### Task 004 — Readiness check substrate

- **Objective:** the readiness engine: check registry (core-owned checks +
  domain seam), essential/warning tiers per DEC-018 MBQ-06, runs as
  `setup_readiness_check` jobs with per-check JSON results in
  `job.log.payload_snapshot`, summary mirrored to
  `store.last_readiness_result/_at`.
- **Allowed files:** `shopify_connector_core` models/tests only (a
  readiness service model/registry file; no views).
- **Forbidden files:** UI, webhooks, cron, domain modules, credential
  model changes beyond read-only use, CI.
- **Prerequisites:** Task 003 merged (needs test connection + scope
  snapshot); ChatGPT gate act + §9 prompt; MBQ-06 residual thresholds
  fixed in the task prompt for the checks it implements.
- **Acceptance criteria:** essential vs warning behavior provable (a
  failed essential check can never yield an overall pass; warnings never
  block); every check returns named reasons; checks are read-only;
  webhook-HMAC and mapped-location checks are registered as *pending
  slots*, not implemented.
- **Test requirements:** tier semantics, per-check result persistence,
  summary mirroring, redaction of check detail, seam registration test.
- **Rollback notes:** single-PR revert; mirrors remain harmlessly stale.
- **Risks:** dashboard false health (mitigated: honest timestamps,
  fail-closed summary aggregation — unknown = not passed).
- **Definition of done:** §9 template + checklists + ChatGPT review.
- **Must not include:** UI, scheduling/cron, webhook checks'
  implementation, domain checks' implementation.

### Task 005 — Connection lifecycle actions

- **Objective:** the audited service actions: activate (wizard-final
  semantics at service level), disconnect (clear credential value,
  preserve everything, cancel-or-hold in-flight jobs per the Part A §I.4
  disposition ChatGPT fixes in the task prompt), reconnect (re-enter →
  test → readiness → resume), `reconnect_needed` auto-transition on auth
  failure; plus the store/settings `perm_create` ACL decision this
  package surfaced.
- **Allowed files:** `shopify_connector_core` models/security/tests only.
- **Forbidden files:** UI/views/wizard, webhooks, cron, domain modules.
- **Prerequisites:** Tasks 002–004 merged; ChatGPT decisions on the §I.4
  in-flight disposition and the `perm_create` posture; gate act + §9
  prompt.
- **Acceptance criteria:** every transition audited (who/when + job.log
  trail); disconnect provably preserves history and clears the value;
  reconnect provably re-runs readiness before `connected`; no automatic
  reconnect exists.
- **Test requirements:** full transition matrix, history-preservation
  assertions, credential-clear assertions, enqueue-block while not
  `connected`.
- **Rollback notes:** single-PR revert; states remain valid data.
- **Risks:** silent history loss (blocked by tests + no-unlink ACLs);
  enqueue gate bypass (blocked by queue-substrate enforcement tests).
- **Definition of done:** §9 template + checklists + ChatGPT review.
- **Must not include:** UI, wizard, webhooks, notification logic, domain
  sync.

### Task 006 — Setup wizard UI (horizon only)

- **Objective (future):** the accepted 11-step wizard consuming Tasks
  002–005 as its mechanics (task map Group 3 integrating Groups 4–5).
- **Prerequisites:** **a separate, explicit ChatGPT UI-implementation-gate
  opening** (none exists; AR-023 kept it closed), MBQ-03 XML IDs, MBQ-05
  decision, MBQ-22 wizard copy, plus Tasks 002–005 and the shell (task
  map Group 1). **UI can only come after the UI gate — this plan neither
  schedules nor specifies it**; the accepted
  [`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md)
  governs it.
- Everything else about Task 006 is deliberately out of this plan's
  scope.

## Recommended next coding task

**Recommendation: Task 002 — credential storage, masking, redaction
foundation.** Justification: it is the recorded blocker for everything
else (task map: Group 4 first among the foundation groups, and "the
dedicated MBQ-04 implementation-planning task must be written and
accepted first" — which this package is); it needs **no** widening of the
external-API prohibition (Task 002 makes zero Shopify calls, so it is the
smallest possible gate step after AR-021); it is independently testable;
and its riskiest content (secret handling, redaction) benefits from being
reviewed alone rather than mixed with transport code.

**Not authorized here.** Task 002 requires ChatGPT acceptance of this
package, an explicit gate-opening act, and a separate final task prompt
written from
[`task-002-credential-storage-redaction-proposed.md`](./task-002-credential-storage-redaction-proposed.md)
after ChatGPT resolves its named decision points.

## Gate requirements

| Task | Gate that must be opened first (each a separate, explicit ChatGPT act) |
| --- | --- |
| Task 002 | Credential-storage gate: authorizes the credential model/fields/service/redaction **only**; keeps the no-external-API-call rule fully in force |
| Task 003 | API-client/test-connection gate: **first authorization of outbound Shopify API calls** (read-only), plus the client shell |
| Task 004 | Readiness-substrate gate (read-only checks engine) |
| Task 005 | Lifecycle-actions gate (incl. the §I.4 disposition and `perm_create` decisions) |
| Task 006 | The UI implementation gate (explicitly still closed per AR-023) + everything the accepted UI task map requires |

## Dependency map

```
AR-024 acceptance (this package)
        │
        ▼
Task 002  credential storage + redaction        (no API calls)
        │
        ▼
Task 003  API client shell + test connection    (first API calls, read-only)
        │
        ▼
Task 004  readiness substrate                   (consumes test connection + scopes)
        │
        ▼
Task 005  lifecycle actions                     (disconnect/reconnect/activate)
        │
        ▼   (+ UI gate + Group 1 shell + MBQ-03/05/22)
Task 006  setup wizard UI                       (accepted task map Group 3)
```

Credential storage → test connection → readiness → lifecycle → wizard:
each task consumes only merged predecessors; no task reaches forward.

## Risk register

| Risk | Where it bites | Containment in this plan |
| --- | --- | --- |
| Credential leakage (DB/backup/sudo) | Any time after Task 002 | Accepted Option B residual, stated honestly everywhere; Admin-only model; redaction; no-read-back; never claimed as encryption |
| Incorrect masking (value rendered) | Future UI tasks | No views in core tasks at all; dedicated model keeps the value off every rendered model; checklist gates on the entry widget |
| Sudo exposure | Tasks 002/003/005 | Single sanctioned elevation (client-internal read); per-`sudo()` justification required by checklist; DEC-004 boundary rule restated |
| Logs leaking token | Tasks 002–005 | Belt-and-braces redaction (source + job-log sink); mandatory tests proving absence |
| Test connection writing data | Task 003 | Read-only contract; no mutation API exists in the shell; guarantee test |
| Scope confusion (write-implies-read assumed) | Tasks 003/004 | Officially unconfirmed → explicit `read_` handles required; comparison uses the snapshot |
| API version mismatch / silent fall-forward | Task 003 onward | `X-Shopify-API-Version` comparison surfaces fall-forward as warning; pinned version per MBQ-52 |
| Dashboard false health | Task 004 onward | Fail-closed aggregation; honest timestamps; warnings carried, never hidden |
| UI implementation getting ahead of foundation | Any time | UI gate explicitly closed; Task 006 listed as horizon-only with its own gate; core tasks contain zero views |
| Invented platform behavior baked into code | Task 003 | Open questions (THROTTLED shape, 401 vs ACCESS_DENIED, missing-scope shape) carried as *configurable fixtures + empirical verification steps*, never asserted |
| Task creep (mutations/webhooks/cron sneaking in) | Tasks 002–005 | Explicit exclusions per task; allowed-files lists; AR-021-style per-task gates |
