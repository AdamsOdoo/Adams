# Task 002 Gate-Opening Proposal

> Companion to [`task-002-decision-closure.md`](./task-002-decision-closure.md)
> (AR-025) and [`task-002-final-implementation-prompt.md`](./task-002-final-implementation-prompt.md).
> Follows the AR-021 pattern: a gate exists only when ChatGPT performs
> an explicit, documented gate-opening act and that act is merged into
> `Shopify-connector`.

## Status

**Proposed for ChatGPT review. Docs-only. This document does not open
the gate.** It is a *proposal* for a future, separate, explicit ChatGPT
gate-opening act. Until that act happens and is merged, the only open
implementation gate remains the limited core-only zero-UI gate
(AR-021), which explicitly forbids credential fields — and Task 002
remains recommended-but-not-authorized (AR-024). This PR changes none
of that.

## Proposed gate

Open a **limited credential-storage implementation gate for Task 002
only**: the `shopify.connector.store.credential` model, the six
non-secret status mirrors on `shopify.connector.store`, the credential
service methods, the redaction utility, one Admin-only ACL row, the
Task 002 test files, a manifest version bump, and the handoff update —
executed exactly per the final implementation prompt, and nothing else.

## Why now

- **PR #92 is merged and AR-024 is accepted** (2026-07-06,
  implementation-planning level): the architecture package, Option C
  credential model, and the redaction contract are accepted; Task 002
  is the accepted recommended next coding task. The only items AR-024
  left open for Task 002 — compute-blank, `token_variant`/MBQ-05
  direction, scope-snapshot placement — are closed at proposal level by
  AR-025 (decision-closure document).
- **Task 002 is the smallest safe next coding step:** it needs **no
  widening of the external-API prohibition** (zero Shopify calls — the
  AR-021 no-external-API rule stays fully in force), **no UI** (zero
  views/XML), and no new group. It is one small model, six mirror
  fields, four service methods, one utility module, one ACL row, and
  tests.
- **Credential/redaction safety should be reviewed in isolation,
  before API-client work:** Task 003's client consumes
  `_get_access_token` and `redact()`. Reviewing the secret-handling and
  redaction substrate alone — with its full denial-matrix and leak-sweep
  test evidence — is materially safer than reviewing it mixed with
  transport/error-normalization code.

## Gate scope

**Allowed only** (exhaustively; file-exact list in the final prompt):

- the credential model (`shopify.connector.store.credential`);
- the six credential status mirrors on `shopify.connector.store`
  (including the two scope-snapshot fields, per AR-025 Decision 3);
- the redaction utility (`tools/redaction.py`);
- the service methods (`action_set_token` / `action_replace_token` /
  `action_clear_token` / `_get_access_token`);
- one Admin-only ACL row (no rows for auditor/operator/reviewer; no
  unlink);
- the three Task 002 test modules (+ `tests/__init__.py`);
- manifest version bump (`19.0.1.1.0`);
- the mandatory research-handoff update.

**Forbidden (the gate does not authorize):**

- API client of any kind (no HTTP, no `requests`, no GraphQL strings);
- test connection;
- setup wizard;
- UI of any kind — views/menus/actions/wizards/XML;
- webhooks, controllers, cron;
- domain logic (product/customer/order/inventory/fulfillment);
- Task 003 or any part of it;
- **any external network call** — the AR-021 no-external-API rule is
  explicitly not widened by this gate;
- `job.log` writes, ACL changes beyond the one new row, new groups,
  raw SQL, `ir.config_parameter` secret storage, migrations,
  `adams_base`, CI files;
- any second task before ChatGPT reviews the Task 002 PR.

## Gate conditions

Conditions ChatGPT must explicitly accept before the gate opens (the
gate-opening act should restate them):

1. **AR-025 accepted** — the three decision closures (compute-blank
   rejected for Task 002; `token_variant` single value
   `offline_custom_app`; scope snapshot on `store`) are accepted as
   Decisions, and the register acceptance patch is applied (MBQ-04/05/44
   notes; no premature resolution).
2. **The final implementation prompt is accepted as binding** —
   [`task-002-final-implementation-prompt.md`](./task-002-final-implementation-prompt.md)
   is the exact §9 prompt to issue; any deviation requires a new
   ChatGPT decision, not implementer judgment.
3. **The gate is Task-002-only** and closes again at Task 002's draft
   PR: no follow-on coding is authorized by it, and Task 003 requires
   its own separate gate act (first authorization of outbound API
   calls) plus its own decision round (job-type value; shop-state
   mapping; job-log write path; `payload_hash` nonce).
4. **The no-external-API, no-UI, no-webhook/controller/cron
   prohibitions remain in force** throughout the gate.
5. **Runtime caveat acknowledged:** the repository still has no Odoo
   runtime/test framework/CI (Task 001A). Tests will be written and
   syntax-validated; if no runtime is provisioned separately, they will
   not be executed before the PR, and the manual validation checklist
   becomes mandatory review evidence. Provisioning infrastructure is
   **not** part of this gate.
6. **Review path fixed:** the Task 002 PR is reviewed against
   [`../05-qa/credential-security-redaction-review-checklist.md`](../05-qa/credential-security-redaction-review-checklist.md)
   and
   [`../05-qa/task-002-pre-implementation-review-checklist.md`](../05-qa/task-002-pre-implementation-review-checklist.md);
   ChatGPT review of that PR is required before any next task.
7. **The gate opens only when the gate-opening act itself is merged
   into `Shopify-connector`** (AR-021 precedent), not when this
   proposal or the AR-025 package is merged.

## Gate risks

- **Credential leakage** (DB/backup/`sudo()` residual; accidental log
  or exception exposure) — contained by the Admin-only default-deny
  model, field `groups`, the redaction utility with mandatory tests,
  the leak-sweep assertion, and the honest-residual documentation; the
  residual itself is accepted MBQ-04 Option B reality and is stated,
  not solved.
- **False security claims** — the largest reputational risk; contained
  by the hard no-encryption-claim rules, the honest-residual docstring
  requirement, and checklist §A gates.
- **Read-back misunderstanding** — reviewers or future copy treating
  "no connector-surface read-back" as "cannot be read at all";
  contained by AR-025 Decision 1's explicit residual statement (Admin
  ORM/RPC read remains technically possible) and the rejected
  compute-blank variant being recorded with its revisit condition.
- **`sudo()` misuse** — contained by the one-sanctioned-`sudo()` rule
  (only `_get_access_token`), the no-`sudo()`-in-write-paths rule, the
  source-level test/grep, and checklist §E.
- **Overbuilding MBQ-05** — adding client-credentials fields/refresh
  machinery prematurely; contained by Decision 2 (one secret value, one
  `token_variant` value, deliberate-absence docstring) and checklist
  items.
- **Accidental API call** — contained by the zero-HTTP/zero-import hard
  rule and the manual grep step (no `requests`/`urllib`/GraphQL strings
  in the module).
- **Insufficient tests / untested-in-runtime code** — the repository
  has no Odoo runtime; contained by the Task 001A applicability rule
  (honest not-executed statement + mandatory manual checklist), and by
  the tests being written to the exact enumerated list (21 cases)
  rather than implementer discretion.

## Recommended ChatGPT decision

If satisfied, ChatGPT should, **in this order and as separate acts**:

1. **Accept AR-025** (decision closure): compute-blank **rejected** for
   Task 002; `token_variant` = `offline_custom_app` only; scope
   snapshot on `store`; the final Task 002 boundary as specified —
   applying the acceptance patch (AR-025 row → Accepted; MBQ-04/05/44
   register notes per the decision-closure §Register impact proposal;
   status labels unchanged).
2. **Perform the explicit gate-opening act** for the Task 002
   credential-storage gate exactly as scoped above (a docs-only
   gate-opening document in the AR-021 pattern, merged into
   `Shopify-connector`), restating the seven gate conditions.
3. **Issue the final task prompt** — the verbatim contents of
   [`task-002-final-implementation-prompt.md`](./task-002-final-implementation-prompt.md)
   — as the Task 002 session prompt.

If not satisfied, return this package for revision (AR-025 stays
Proposed; no gate opens; Task 002 stays not-started).
