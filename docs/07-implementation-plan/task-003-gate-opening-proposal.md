# Task 003 Gate-Opening Proposal

> Companion to [`task-003-decision-closure.md`](./task-003-decision-closure.md)
> (AR-027, accepted) and
> [`task-003-final-implementation-prompt.md`](./task-003-final-implementation-prompt.md)
> (AR-028, proposed). Follows the AR-021 / AR-025→AR-026 pattern: a gate
> exists only when ChatGPT performs an explicit, documented gate-opening
> act and that act is merged into `Shopify-connector`.

## Status

**Proposed 2026-07-07 for ChatGPT review, on branch
`claude/task-003-gate-opening-no0tw4`. Docs-only. This document does not
open the gate.** It is a *proposal* for a future, separate, explicit
ChatGPT gate-opening act (its own merged document, mirroring
[`task-002-credential-storage-gate.md`](./task-002-credential-storage-gate.md)
for AR-026). Until that act happens and is merged, the only implementation
gate open today remains the narrow Task 002 credential-storage gate
(AR-026) — it authorizes no API client, no test connection, and no
outbound Shopify call of any kind. Task 003 remains recommended
(AR-024) and decision-closed (AR-027), but **not authorized**. This
document changes none of that.

**Not a decision-closure document.** The four Task 003-specific
decisions (`core_test_connection` job-type value; `SHOP_INACTIVE`/402/
423/403-fraudulent error-class mapping; job-log system-append write
path; per-run `payload_hash` nonce) are already closed — accepted by
ChatGPT via **AR-027** (PR #98, 2026-07-07, with an F1 revision scoping
the nonce to `core_test_connection` only). This document does not
re-litigate any of them; it proposes only the gate act and packages the
companion final implementation prompt that applies them.

## Proposed gate

Open a **limited API-client / test-connection implementation gate for
Task 003 only**: the `shopify.connector.api.client` AbstractModel
(read-only), the `action_test_connection()` entry point on
`shopify.connector.store`, the `core_test_connection` addition to
`job_type`, the job-log system-append method, the per-run `payload_hash`
UUID4 nonce for `core_test_connection` job creation only, the Task 003
test files, a manifest version bump, and the handoff update — executed
exactly per
[`task-003-final-implementation-prompt.md`](./task-003-final-implementation-prompt.md),
and nothing else. **This is the first conscious widening of the AR-021
no-external-API-call rule** — the gate authorizes outbound, read-only
Shopify Admin GraphQL calls for the first time in this project.

## Why now

- **AR-027 is accepted** (2026-07-07, PR #98, merge commit
  `2e51cf02cd54527ff9dc817b6be1e1189f001a83`): the four Task
  003-specific decision points AR-024 left open are closed. Nothing
  about Task 003's scope remains undecided at the decision level.
- **Task 002 is merged and implemented** (PR #97): the credential model,
  `_get_access_token`, and `redact()` exist and are the only things
  Task 003's client consumes for secret handling — reviewing
  credential/redaction safety in isolation, before API-client work, is
  already done.
- **Task 003 is the smallest safe next widening:** it needs **no UI**
  (zero views/XML), **no new group**, **no mutation capability**
  (structurally read-only), and touches exactly three existing files
  plus one new one. The widening it does require — outbound HTTP to
  Shopify — is narrowly bounded to one read-only query, with a
  transport-injection seam so tests never need real network access.

## Gate scope

**Allowed only** (exhaustive; file-exact list in the final prompt):

- the API client (`shopify_connector_api_client.py`, new);
- the `action_test_connection()` entry point on
  `shopify_connector_store.py` (no field changes — every field it
  writes already exists);
- the one-line `core_test_connection` addition to `job_type` in
  `shopify_connector_job.py`, plus a documentation-only comment on
  `payload_hash`'s dual use;
- the `_system_append` job-log system-append method in
  `shopify_connector_job_log.py` (exactly one new `sudo()` call site);
- the three Task 003 test modules;
- manifest version bump (`19.0.1.2.0`);
- the mandatory research-handoff update.

**Forbidden (the gate does not authorize):**

- any GraphQL mutation, Bulk Operation, or REST call;
- the `core_readiness_check` fix — its identical latent
  idempotency-collision defect stays tracked as
  [`TD-001`](../05-qa/technical-debt-register.md) and is **explicitly
  excluded** from this gate; a future gate may include it **only if
  ChatGPT names it explicitly** in that gate's own scope section, which
  this document does not do;
- setup wizard;
- UI of any kind — views/menus/actions/wizards/XML;
- webhooks, controllers, cron;
- product/customer/order/inventory/fulfillment logic or any domain
  module;
- migrations (none are justified — this task adds no schema requiring
  one; if a future revision of this gate needs one, it must say so by
  name);
- any change to `shopify_connector_store_credential.py`,
  `security/ir.model.access.csv`, or
  `security/shopify_connector_security.xml`;
- any `sudo()` beyond the exactly-two sites named in the final prompt
  (the pre-existing, untouched `_get_access_token`, and the one new
  `_system_append` site);
- any pacing/backpressure policy (MBQ-51 stays untouched);
- any second task before ChatGPT reviews the Task 003 PR.

## Gate conditions

Conditions ChatGPT must explicitly accept before the gate opens (the
gate-opening act should restate them):

1. **AR-027 accepted** — already done; restated here as a precondition,
   not re-decided.
2. **AR-028 accepted** — this proposal and
   [`task-003-final-implementation-prompt.md`](./task-003-final-implementation-prompt.md)
   are accepted as the binding scope and prompt; the final prompt is
   accepted as gate-ready and binding but **not issued** by that
   acceptance alone.
3. **The gate is Task-003-only** and closes again at Task 003's draft
   PR: no follow-on coding is authorized by it, and any
   `core_readiness_check` fix requires its own separate, explicitly
   named authorization (per `TD-001`'s routing).
4. **The no-UI, no-webhook/controller/cron, no-mutation, no-domain-logic
   prohibitions remain in force** throughout the gate; only outbound
   read-only GraphQL test-connection calls are newly authorized.
5. **Runtime caveat acknowledged:** the repository still has no Odoo
   runtime/test framework/CI (Task 001A). Tests will be written and
   syntax-validated; if no runtime is provisioned separately, they will
   not be executed before the PR, and the manual validation checklist
   (against a development store, never a production shop) becomes
   mandatory review evidence. Provisioning infrastructure is **not**
   part of this gate.
6. **Review path fixed:** the Task 003 PR is reviewed against
   [`../05-qa/task-003-pre-implementation-review-checklist.md`](../05-qa/task-003-pre-implementation-review-checklist.md)
   §B and
   [`../05-qa/credential-security-redaction-review-checklist.md`](../05-qa/credential-security-redaction-review-checklist.md);
   ChatGPT review of that PR is required before any next task.
7. **The gate opens only when the gate-opening act itself is merged
   into `Shopify-connector`** (AR-021/AR-026 precedent), not when this
   proposal or the AR-028 package is merged.

## Gate risks

- **Accidental mutation capability** — contained by the structurally
  read-only client design (no mutation-capable method exists at all),
  the source-inspection test, and the fixed query string used by the
  one call site.
- **`sudo()` misuse / creeping elevation** — contained by the
  exactly-two-sites rule, the source-level grep test, and the explicit
  ban on adding any `sudo()` to the credential model file.
- **`core_readiness_check` silently touched** — contained by the hard
  rule forbidding any behavior change to it, and by a dedicated test
  (final prompt item 28) that proves its pre-existing collision
  behavior is unchanged, not fixed, by this task.
- **False official-behavior claims** — contained by the mandatory
  `[Requires external validation before implementation]` labelling for
  THROTTLED shape, invalid-token HTTP status, missing-scope shape, and
  scope requirements, plus the manual-validation empirical-recording
  step.
- **Credential/token leakage via the new transport code** — contained
  by mandatory `redact()` wrapping on every exception and log write in
  the client, the dummy-token leak-sweep tests, and reuse of the
  already-reviewed Task 002 `_get_access_token`/`redact()` substrate
  without modification.
- **Ambiguous `credential_state` flips** — contained by the
  `credential_invalid` gating in the error-normalization table
  (Decision 2): only a genuine token-invalid signal flips it; the four
  shop-account-state conditions never do, each with its own distinct
  reason text.
- **Insufficient tests / untested-in-runtime code** — the repository
  has no Odoo runtime; contained by the Task 001A applicability rule
  (honest not-executed statement + mandatory manual checklist) and by
  tests written to the exact enumerated list (32 cases) in the final
  prompt rather than implementer discretion.
- **Premature pacing/backpressure policy** — contained by the explicit
  MBQ-51 exclusion; the client only surfaces `throttleStatus`, never
  acts on it.

## Recommended ChatGPT decision

If satisfied, ChatGPT should, **in this order and as separate acts**:

1. **Accept AR-028** (this proposal and the companion final
   implementation prompt): the gate scope above; the final Task 003
   boundary as specified in
   [`task-003-final-implementation-prompt.md`](./task-003-final-implementation-prompt.md).
2. **Perform the explicit gate-opening act** for the Task 003
   API-client/test-connection gate exactly as scoped above (a docs-only
   gate-opening document in the AR-021/AR-026 pattern, merged into
   `Shopify-connector`), restating the seven gate conditions and
   explicitly stating whether `core_readiness_check` (`TD-001`) is
   folded in by name (it is not, by default) or left for its own
   follow-up patch.
3. **Issue the final task prompt** — the verbatim contents of
   [`task-003-final-implementation-prompt.md`](./task-003-final-implementation-prompt.md)
   — as the Task 003 session prompt.

If not satisfied, return this package for revision (AR-028 stays
Proposed; no gate opens; Task 003 stays not-started).
