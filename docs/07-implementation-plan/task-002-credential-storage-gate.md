# Task 002 Credential Storage Implementation Gate

> The separate, explicit ChatGPT gate-opening act named as still
> outstanding by
> [`task-002-decision-closure.md`](./task-002-decision-closure.md)
> (AR-025, accepted 2026-07-07) and scoped exactly by
> [`task-002-gate-opening-proposal.md`](./task-002-gate-opening-proposal.md)
> (accepted as the proposed gate scope, gate not opened by that
> document). This document performs that act, following the AR-021
> precedent (`limited-core-implementation-gate.md`): a gate exists only
> once its opening document is merged into `Shopify-connector`.

## Status

- **Accepted gate-opening act.**
- **Docs-only.** No code, no model, no field, no view, no XML, no
  Python is created by this document or this PR.
- **Opens the Task 002 implementation gate only once this PR is merged
  into `Shopify-connector`** — not before, and not by drafting this
  document.
- **Does not implement Task 002.**
- **Does not create code.**
- **Does not issue the final implementation prompt yet** — issuing it
  is the action that starts the Task 002 coding session, and that
  action happens in a separate turn/session, after this PR merges, not
  inside this PR.
- **Authorizes exactly one future coding session after merge:** Task
  002 — Credential Storage, Masking, and Redaction Foundation.

## Preconditions confirmed

Confirmed on-disk and via GitHub before this document was written:

- **PR #94 merged into `Shopify-connector`** — merge commit
  `03ffcb4dc949cd5137b589a6cdc33da9105de31d`; `Shopify-connector`
  confirmed (via `git merge-base --is-ancestor`) to contain that commit
  as of this branch's creation.
- **AR-025 accepted by ChatGPT on 2026-07-07** — row status
  **Accepted** in
  [`architecture-review-log.md`](../05-qa/architecture-review-log.md),
  at decision/gate-preparation level only.
- **Compute-blank no-read-back hardening rejected for Task 002** —
  `access_token` remains a plain stored `fields.Char` (`copy=False`,
  Admin-only `groups=`), behind the Admin-only default-deny model ACL;
  no compute, no inverse, no raw SQL, no hand-managed column, no
  companion stored field; the honest residual (Admin-group ORM/RPC
  read technically possible outside connector surfaces;
  `sudo()`/database/backup reads the plaintext; no encryption claim)
  is documented and binding.
- **`token_variant = offline_custom_app` accepted for Task 002** —
  exactly one Selection value; no `client_id`/`client_secret`/token
  cache/expiry/refresh machinery; MBQ-05 remains open for the MVP
  acquisition-path decision and setup-wizard copy.
- **Scope snapshot on `shopify.connector.store` accepted** —
  `granted_scopes` + `granted_scopes_checked_at` created by Task 002 as
  readonly mirrors with no writer; Task 003 writes them later.
- **The final Task 002 implementation prompt
  ([`task-002-final-implementation-prompt.md`](./task-002-final-implementation-prompt.md))
  is accepted as gate-ready and binding** — not issued until this gate
  opens.
- **The gate-opening proposal
  ([`task-002-gate-opening-proposal.md`](./task-002-gate-opening-proposal.md))
  is accepted as the proposed gate scope** — the gate itself was not
  opened by that document; this document is the act that opens it.
- **Task 002 is not started.** No credential model, field, service
  method, or redaction utility exists in the repository as of this
  branch.
- **Task 003 is not started.** No API client, test-connection code, or
  related model change exists in the repository as of this branch.

## Gate opening decision

- **ChatGPT opens the narrow Task 002 credential-storage implementation
  gate.**
- **The gate opens only after this gate document is merged into
  `Shopify-connector`** — not on draft, not on review approval alone,
  not on any earlier commit.
- **The gate authorizes only the exact final prompt already accepted
  in
  [`task-002-final-implementation-prompt.md`](./task-002-final-implementation-prompt.md).**
  Nothing in this document supersedes, restates with variation, or
  duplicates that prompt's content — it is referenced by exact path,
  not copied.
- **Any deviation from that final prompt requires a new ChatGPT
  decision** — the implementer may not improvise a different field
  shape, ACL row, service-method signature, or test list.

## Authorized task

**Authorize exactly:** Task 002 — Credential Storage, Masking, and
Redaction Foundation.

**Authorized after merge only** (per the final prompt's exact
contracts — restated here as a scope summary, not a re-specification):

- the credential model (`shopify.connector.store.credential`);
- six status mirrors on `shopify.connector.store`;
- the redaction utility (`tools/redaction.py`);
- four service methods:
  - `action_set_token`
  - `action_replace_token`
  - `action_clear_token`
  - `_get_access_token`
- one Admin-only ACL row;
- tests (the 21 enumerated cases in the final prompt);
- a manifest version bump (`19.0.1.1.0`);
- the mandatory research-handoff update.

## Still forbidden

Explicitly, and without exception, until their own separate gate acts:

- API client (any HTTP/`requests`/GraphQL code);
- test connection;
- setup wizard;
- UI/views/menus/actions/wizards (zero XML of any kind);
- webhooks/controllers/cron;
- product/customer/order/inventory/fulfillment;
- domain modules;
- external network calls;
- **Task 003** (its four decision points — `core_test_connection`
  job-type value; `SHOP_INACTIVE`/402/423/403-fraudulent error-class
  mapping; job-log system-append write path vs. ACL widening; per-run
  `payload_hash` nonce — all remain open and are not touched by this
  gate);
- any code outside the final Task 002 prompt;
- **any second task after Task 002 before ChatGPT reviews Task 002's
  implementation PR** — this gate authorizes one coding session, not a
  standing implementation mandate.

## Binding implementation prompt

- **The only implementation prompt authorized by this gate is:**
  [`docs/07-implementation-plan/task-002-final-implementation-prompt.md`](./task-002-final-implementation-prompt.md).
- **It must be issued verbatim after this PR merges** — as its own
  session/turn, not folded into this gate-opening PR.
- **The implementation PR must remain draft** until ChatGPT reviews it
  — matching this gate document's own draft-until-reviewed posture and
  the AR-021 precedent.
- **ChatGPT must review the implementation PR before any next task
  starts** — no Task 003 gate act, and no further domain-task gate act,
  may be prepared or opened on the assumption that Task 002 will pass
  review; each waits for the actual review outcome.

## Conditions

Restated from
[`task-002-gate-opening-proposal.md`](./task-002-gate-opening-proposal.md)
§Gate conditions (all seven, now satisfied and reconfirmed at the
moment this gate opens):

1. **AR-025 accepted** — the three decision closures (compute-blank
   rejected; `token_variant = offline_custom_app`; scope snapshot on
   `store`) are accepted Decisions; the register acceptance patch
   (MBQ-04/05/44 notes) is applied. **Confirmed satisfied** — AR-025 is
   Accepted (2026-07-07).
2. **The final implementation prompt is accepted as binding** — any
   deviation requires a new ChatGPT decision, not implementer
   judgment. **Confirmed satisfied.**
3. **The gate is Task-002-only** and closes again at Task 002's draft
   PR: no follow-on coding is authorized by it, and Task 003 requires
   its own separate gate act (first authorization of outbound API
   calls) plus its own decision round. **Restated as binding by this
   document's §Closure rule.**
4. **The no-external-API, no-UI, no-webhook/controller/cron
   prohibitions remain in force** throughout this gate. **Restated as
   binding by this document's §Still forbidden.**
5. **Runtime caveat acknowledged:** the repository still has no Odoo
   runtime/test framework/CI (Task 001A). Tests will be written and
   syntax-validated; if no runtime is provisioned separately, they will
   not be executed before the PR, and the manual validation checklist
   becomes mandatory review evidence. Provisioning infrastructure is
   **not** part of this gate. **Confirmed unchanged** — no runtime has
   been provisioned since Task 001A or the AR-025 sprint.
6. **Review path fixed:** the Task 002 PR is reviewed against
   [`../05-qa/credential-security-redaction-review-checklist.md`](../05-qa/credential-security-redaction-review-checklist.md)
   and
   [`../05-qa/task-002-pre-implementation-review-checklist.md`](../05-qa/task-002-pre-implementation-review-checklist.md);
   ChatGPT review of that PR is required before any next task.
   **Confirmed satisfied** — both checklists exist and are Accepted.
7. **The gate opens only when the gate-opening act itself is merged
   into `Shopify-connector`** (AR-021 precedent), not when this
   document is only drafted, reviewed, or approved in conversation.
   **This is the operative condition of this document itself.**

## Risks and controls

| Risk | Accepted control (per AR-025 / this gate) |
| --- | --- |
| **Credential leakage** (DB/backup/`sudo()` residual; accidental log or exception exposure) | Admin-only default-deny model ACL + field-level `groups=` (two independent layers); the shared `redact()` utility enforced at source and sink with mandatory tests (key hits, value-pattern hits, exact-value scrub, nesting, idempotence); the leak-sweep test asserting the dummy token is absent from every persisted surface except the credential column; the residual itself is accepted MBQ-04 Option B reality, stated honestly, not solved |
| **False security claims** | Hard no-encryption-claim rule (code, docstrings, comments, tests, PR body, handoff); the model docstring is required to carry the honest-residual statement; `credential-security-redaction-review-checklist.md` §A gates block acceptance on any violation |
| **Read-back misunderstanding** (treating "no connector-surface read-back" as "cannot be read at all") | AR-025 Decision 1's explicit residual statement (Admin ORM/RPC read remains technically possible) is carried verbatim into the final prompt's model docstring requirement; the rejected compute-blank variant is recorded with a named revisit condition, not silently dropped |
| **`sudo()` misuse** | Exactly one sanctioned `sudo()` in the entire diff (`_get_access_token`, with written justification); write paths run as the calling user with no `sudo()`; a source-level test/grep proves the single-occurrence rule; any other `sudo()` in the diff is a review failure per checklist §E |
| **Overbuilding MBQ-05** | AR-025 Decision 2 fixes exactly one `token_variant` value and one secret field; the deliberate absence of `client_id`/`client_secret`/token-cache/expiry/refresh fields is a docstring requirement, not an implementer option; MBQ-05 itself stays open, routed to a future task, not smuggled into Task 002 |
| **Accidental API call** | Zero-HTTP/zero-`requests`-import/zero-GraphQL-string hard rule; the manual validation checklist's grep-for-network-code step; the AR-021 no-external-API-call rule is explicitly not widened by this gate |
| **Insufficient tests / runtime caveat** | The final prompt enumerates all 21 required test cases exactly (access matrix, field-`groups` independence, redaction suite, service behavior, leak sweep, no-job-log assertion, single-`sudo()` guard); the Task 001A applicability rule requires tests to be written and syntax-validated even with no runtime, with the manual validation checklist becoming mandatory review evidence when execution isn't possible |

## Closure rule

- **This gate closes after the future Task 002 implementation PR is
  opened as draft.** Opening that PR consumes the gate; it does not
  remain open for repeated or follow-on use.
- **No follow-on coding is authorized by this gate.** Once the Task 002
  PR exists, any further change beyond fixing review feedback on that
  same PR requires its own separate ChatGPT decision and, if it touches
  new forbidden territory, its own separate gate act.
- **Task 003 requires its own separate decision/gate act** — its four
  named decision points (`core_test_connection` job-type value;
  `SHOP_INACTIVE`/402/423/403-fraudulent mapping; job-log system-append
  write path vs. ACL widening; per-run `payload_hash` nonce) must be
  resolved, a Task 003 decision-closure package prepared and accepted
  (mirroring this Task 002 pattern), and a separate, explicit
  gate-opening act performed and merged — none of which this document
  performs or shortcuts.
