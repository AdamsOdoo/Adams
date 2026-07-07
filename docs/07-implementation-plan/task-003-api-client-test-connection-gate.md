# Task 003 API Client / Test Connection Implementation Gate

> The separate, explicit ChatGPT gate-opening act named as still
> outstanding by
> [`task-003-decision-closure.md`](./task-003-decision-closure.md)
> (AR-027, accepted 2026-07-07) and
> [`task-003-gate-opening-proposal.md`](./task-003-gate-opening-proposal.md)
> (AR-028) and scoped exactly by
> [`task-003-final-implementation-prompt.md`](./task-003-final-implementation-prompt.md).
> This document performs that act, following the AR-021/AR-026
> precedent (`limited-core-implementation-gate.md`,
> `task-002-credential-storage-gate.md`): a gate exists only once its
> opening document is merged into `Shopify-connector`.

## Status

- **Accepted gate-opening act.**
- **Docs-only.** No code, no model, no field, no view, no XML, no
  Python is created by this document or this PR.
- **Opens the Task 003 implementation gate only once this PR is merged
  into `Shopify-connector`** — not before, and not by drafting this
  document.
- **Does not implement Task 003.**
- **Does not create code.**
- **Does not call Shopify.** No external network call is made by this
  document or this PR.
- **Does not issue the final implementation prompt yet** — issuing it
  is the action that starts the Task 003 coding session, and that
  action happens in a separate turn/session, after this PR merges, not
  inside this PR.
- **Authorizes exactly one future coding session after merge:** Task
  003 — API Client Shell and Test Connection.
- **This is the first conscious widening of the AR-021 no-external-API
  -call rule** — every prior gate (AR-021, AR-026) explicitly forbade
  any outbound Shopify call; this gate is the one, deliberate act that
  authorizes read-only outbound calls, and only for the exact scope
  named below.

## AR-028 acceptance (applied by this act)

[`task-003-gate-opening-proposal.md`](./task-003-gate-opening-proposal.md)
and
[`task-003-final-implementation-prompt.md`](./task-003-final-implementation-prompt.md)
were merged into `Shopify-connector` via PR #99 (merge commit
`756b88eca79f2ef56ff752b6ba82ab266a782724`) while still marked
**"Proposed for ChatGPT review — NOT YET ACCEPTED"** in their own text
and in the AR-028 row of
[`architecture-review-log.md`](../05-qa/architecture-review-log.md) —
unlike the AR-025/PR #94 convention, where the acceptance patch landed
in the same PR before merge. **This gate-opening act formally applies
that acceptance now, as its precondition:** ChatGPT accepts AR-028 —
the final Task 003 implementation prompt as gate-ready and binding, and
the gate-opening proposal as the proposed gate scope — effective as of
this document. Neither the final prompt's content nor the proposal's
scope is altered by this acceptance; only their status changes from
Proposed to Accepted (reflected in the register update accompanying
this PR). **The gate itself is still not open merely because AR-028 is
now accepted** — it opens only when this document is merged (see
§Gate opening decision).

## Preconditions confirmed

Confirmed on-disk and via GitHub before this document was written:

- **PR #97 merged into `Shopify-connector`** — merge commit
  `7498ba181a01e571204e471d6880ea0c2068fd87` (Task 002 implementation:
  credential model, `_get_access_token`, `redact()` utility, four
  service methods, one Admin-only ACL row — all exist in the
  repository today).
- **PR #98 merged into `Shopify-connector`** — merge commit
  `2e51cf02cd54527ff9dc817b6be1e1189f001a83` — **AR-027 accepted by
  ChatGPT, with an F1 revision to Decision 4:** `core_test_connection`
  confirmed as the `job_type` value; `SHOP_INACTIVE`/402/423/
  403-fraudulent confirmed mapped to `shopify_permission_scope_auth`
  with `credential_state`-gating and mandatory distinct plain-language
  reasons per condition; the sanctioned internal `sudo()`-wrapped
  job-log system-append method confirmed over ACL widening; the per-run
  UUID4 `payload_hash` nonce confirmed **for `core_test_connection` job
  creation only** — `core_readiness_check`'s identical latent
  idempotency-collision exposure explicitly excluded from Task 003's
  scope and tracked as
  [`TD-001`](../05-qa/technical-debt-register.md).
- **PR #99 merged into `Shopify-connector`** — merge commit
  `756b88eca79f2ef56ff752b6ba82ab266a782724` — **AR-028**, packaging
  [`task-003-final-implementation-prompt.md`](./task-003-final-implementation-prompt.md)
  (the complete, copy-paste final `CLAUDE.md` §9 prompt applying the
  four AR-027 decisions) and
  [`task-003-gate-opening-proposal.md`](./task-003-gate-opening-proposal.md)
  (the proposed gate scope); **accepted by this document** (see
  §AR-028 acceptance above).
- **`Shopify-connector` confirmed** (via `git merge-base
  --is-ancestor`) to contain all three merge commits above as of this
  branch's creation.
- **Task 002 is implemented and merged.** The credential model, six
  store status mirrors, redaction utility, four service methods, and
  one Admin-only ACL row exist in the repository as of this branch;
  `shopify_connector_store_credential.py` is unmodified by anything in
  this document.
- **Task 003 is not started.** No `shopify.connector.api.client` model,
  no `action_test_connection()` method, no `core_test_connection`
  `job_type` value, no job-log system-append method, and no
  `payload_hash` nonce logic exist in the repository as of this branch
  (confirmed by direct inspection of `shopify_connector_job.py` and
  `shopify_connector_job_log.py`, both still exactly as merged by PR
  #97/#98 — no service method, no `sudo()`, and no `job_type` value
  beyond the original two).

## Gate opening decision

- **ChatGPT opens the narrow Task 003 API-client / test-connection
  implementation gate.**
- **The gate opens only after this gate document is merged into
  `Shopify-connector`** — not on draft, not on review approval alone,
  not on any earlier commit.
- **The gate authorizes only the exact final prompt already accepted
  in
  [`task-003-final-implementation-prompt.md`](./task-003-final-implementation-prompt.md).**
  Nothing in this document supersedes, restates with variation, or
  duplicates that prompt's content — it is referenced by exact path,
  not copied.
- **Any deviation from that final prompt requires a new ChatGPT
  decision** — the implementer may not improvise a different model
  shape, error-class mapping, `sudo()` site, or test list.
- **This gate authorizes read-only outbound calls only.** No mutation,
  no Bulk Operation, no REST call, and no Shopify write of any kind is
  authorized by this act or by the final prompt it references.

## Authorized task

**Authorize exactly:** Task 003 — API Client Shell and Test Connection.

**Authorized after merge only** (per the final prompt's exact
contracts — restated here as a scope summary, not a re-specification):

- the read-only `shopify.connector.api.client` AbstractModel (`execute`
  / `_send`, transport-injection seam, dual-path error normalization,
  no mutation-capable method);
- the `action_test_connection()` entry point on
  `shopify.connector.store` (no field changes — every field it writes
  already exists);
- the one-line `core_test_connection` addition to the base `job_type`
  Selection in `shopify_connector_job.py`, plus a documentation-only
  comment on `payload_hash`'s dual use;
- the accepted error-class mapping (`SHOP_INACTIVE`/402/423/
  403-fraudulent → `shopify_permission_scope_auth`, with
  `credential_state` gated to a genuine token-invalid signal only, and
  five mandatory distinct plain-language reasons);
- the internal `_system_append` job-log system-append method on
  `shopify.connector.job.log` — the one new sanctioned `sudo()` site in
  the diff (the pre-existing `_get_access_token` remains the only
  other one; no other `sudo()` anywhere);
- the per-run UUID4 `payload_hash` nonce for **`core_test_connection`
  job creation only**;
- the 32 enumerated test cases in the final prompt;
- a manifest version bump (`19.0.1.2.0`);
- the mandatory research-handoff update.

## Still forbidden

Explicitly, and without exception, until their own separate,
explicitly-named gate acts:

- **`core_readiness_check`'s identical latent idempotency-collision
  defect (`TD-001`)** — not fixed, not touched, no behavior change of
  any kind; remains tracked in
  [`technical-debt-register.md`](../05-qa/technical-debt-register.md)
  for a future gate that names it explicitly, or its own tiny follow-up
  patch;
- setup wizard;
- UI of any kind — views/menus/actions/wizards/XML (zero XML in this
  task);
- webhooks/controllers/cron;
- product/customer/order/inventory/fulfillment logic;
- any domain module;
- migrations (none is justified by this task's scope; a future gate
  that needs one must say so by name);
- any change to `shopify_connector_store_credential.py` (read-only
  consumer in this task — no new method, no field, no `sudo()` added
  there);
- any change to `security/ir.model.access.csv` or
  `security/shopify_connector_security.xml` (the job-log write path is
  the sanctioned system-append method, not an ACL widening);
- **any GraphQL mutation, Bulk Operation, or REST call** — the client
  shell is structurally read-only; no method capable of sending a
  mutation may exist;
- any Shopify write operation of any kind;
- any `sudo()` beyond the exactly two sites named above;
- any pacing/backpressure policy (MBQ-51 stays untouched — the throttle
  signal is surfaced, never acted on);
- **any second task after Task 003 before ChatGPT reviews Task 003's
  implementation PR** — this gate authorizes one coding session, not a
  standing implementation mandate.

## Binding implementation prompt

- **The only implementation prompt authorized by this gate is:**
  [`docs/07-implementation-plan/task-003-final-implementation-prompt.md`](./task-003-final-implementation-prompt.md).
- **It must be issued verbatim after this PR merges** — as its own
  session/turn, not folded into this gate-opening PR.
- **The implementation PR must remain draft** until ChatGPT reviews it
  — matching this gate document's own draft-until-reviewed posture and
  the AR-021/AR-026 precedent.
- **ChatGPT must review the implementation PR before any next task
  starts** — no further domain-task gate act, and no
  `core_readiness_check`/`TD-001` follow-up gate, may be prepared or
  opened on the assumption that Task 003 will pass review; each waits
  for the actual review outcome.

## Conditions

Restated from
[`task-003-gate-opening-proposal.md`](./task-003-gate-opening-proposal.md)
§Gate conditions (all seven, now satisfied and reconfirmed at the
moment this gate opens):

1. **AR-027 accepted** — the four Task 003-specific decision closures
   (`core_test_connection`; error-class mapping with `credential_state`
   gating; job-log system-append method; per-run `payload_hash` nonce
   for `core_test_connection` only) are accepted Decisions. **Confirmed
   satisfied** — AR-027 is Accepted (2026-07-07, PR #98).
2. **AR-028 accepted** — the final implementation prompt and the
   gate-opening proposal are accepted as binding and as the proposed
   gate scope, respectively. **Confirmed satisfied by this document**
   (see §AR-028 acceptance above).
3. **The gate is Task-003-only** and closes again at Task 003's draft
   PR: no follow-on coding is authorized by it, and any
   `core_readiness_check` fix requires its own separate, explicitly
   named authorization. **Restated as binding by this document's
   §Closure rule.**
4. **The no-UI, no-webhook/controller/cron, no-mutation, no-domain
   -logic prohibitions remain in force**; only outbound, read-only
   GraphQL test-connection calls are newly authorized. **Restated as
   binding by this document's §Still forbidden.**
5. **Runtime caveat acknowledged:** the repository still has no Odoo
   runtime/test framework/CI (Task 001A). Tests will be written and
   syntax-validated; if no runtime is provisioned separately, they will
   not be executed before the PR, and the manual validation checklist
   (against a development store, never a production shop) becomes
   mandatory review evidence. Provisioning infrastructure is **not**
   part of this gate. **Confirmed unchanged** — no runtime has been
   provisioned since Task 001A.
6. **Review path fixed:** the Task 003 PR is reviewed against
   [`../05-qa/task-003-pre-implementation-review-checklist.md`](../05-qa/task-003-pre-implementation-review-checklist.md)
   §B and
   [`../05-qa/credential-security-redaction-review-checklist.md`](../05-qa/credential-security-redaction-review-checklist.md);
   ChatGPT review of that PR is required before any next task.
   **Confirmed satisfied** — both checklists exist and are Accepted.
7. **The gate opens only when the gate-opening act itself is merged
   into `Shopify-connector`** (AR-021/AR-026 precedent), not when this
   document is only drafted, reviewed, or approved in conversation.
   **This is the operative condition of this document itself.**

## Risks and controls

| Risk | Accepted control (per AR-027/AR-028 / this gate) |
| --- | --- |
| **Accidental mutation capability** | The client shell is structurally read-only — no mutation-capable method exists; the one call site uses a fixed query string; a source-inspection test (final prompt item 18) proves no code path can emit a request body containing `mutation` |
| **`sudo()` misuse / creeping elevation** | Exactly two sanctioned `sudo()` sites in the entire diff (the pre-existing, untouched `_get_access_token`, and the one new `_system_append` job-log site); a source-level grep test (final prompt item 31) proves the count; the credential model file is explicitly forbidden from any change |
| **`core_readiness_check` silently touched** | Hard rule forbidding any behavior change to it; a dedicated test (final prompt item 28) proves its pre-existing collision behavior is unchanged, documenting rather than fixing `TD-001` |
| **False official-behavior claims** | Mandatory `[Requires external validation before implementation]` labelling for THROTTLED body shape, invalid-token HTTP status, missing-scope shape, and scope requirements; the manual-validation step requires the empirically-observed answers to be recorded, never asserted without observation |
| **Credential/token leakage via new transport code** | Every exception and log write in the client passes through the existing, unmodified `redact()`; dummy-token leak-sweep tests (final prompt items 17, 19, 27, 32); reuse of the already-reviewed `_get_access_token` without modification |
| **Ambiguous `credential_state` flips** | The `credential_invalid` gating in the error-normalization table: only a genuine token-invalid signal (401/`ACCESS_DENIED`) flips it; the four shop-account-state conditions (402/423/403-fraudulent/`SHOP_INACTIVE`) never do, each carrying its own distinct, mandatory reason text |
| **Insufficient tests / runtime caveat** | The final prompt enumerates all 32 required test cases exactly; the Task 001A applicability rule requires tests to be written and syntax-validated even with no runtime, with the manual validation checklist (development store only) becoming mandatory review evidence when execution isn't possible |
| **Premature pacing/backpressure policy** | MBQ-51 stays untouched; the client only surfaces `extensions.cost.throttleStatus`, never acts on it; no bucket size is ever hard-coded |

## Closure rule

- **This gate closes after the future Task 003 implementation PR is
  opened as draft.** Opening that PR consumes the gate; it does not
  remain open for repeated or follow-on use.
- **No follow-on coding is authorized by this gate.** Once the Task 003
  PR exists, any further change beyond fixing review feedback on that
  same PR requires its own separate ChatGPT decision and, if it touches
  new forbidden territory, its own separate gate act.
- **`core_readiness_check`'s follow-up fix (`TD-001`) requires its own
  separate, explicitly-named authorization** — either a future gate
  that names it by name in its own scope section, or its own tiny
  follow-up patch (candidate name: "Task 001B — job-framework
  target-less idempotency patch"); neither is performed or shortcut by
  this document.
- **Every future domain task** (product/customer/order/inventory/
  fulfillment, setup wizard, UI, webhooks) requires its own separate
  decision-closure package and gate-opening act, mirroring this Task
  002 → Task 003 pattern; none of it is authorized, implied, or
  shortcut by this document.
