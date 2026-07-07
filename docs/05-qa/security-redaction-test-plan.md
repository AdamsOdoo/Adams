# Security and Redaction Test Plan

> Docs-only test-planning package covering credential security and
> redaction, part of the [MVP QA and Test Strategy](./mvp-qa-test-strategy.md).
> **Historical drafting baseline:** `Shopify-connector` at
> `f74aaf204745ce0087733870fe56bdda74bfa79a`. Builds directly on the
> accepted
> [`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md)
> (AR-024) and the redaction contract in
> [`credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md)
> §Redaction and no-logging contract. **Docs-only. No implementation. No
> gate opened by this document. No credential model/field/service/
> redaction utility is created by this document.** **Freshness note
> (2026-07-07 revision):** at this plan's original drafting, Task 002
> (which would create the credential model/redaction utility) was
> proposed, not authorized. `Shopify-connector` has since also merged PR
> #93 (`ac250f7fd2f242df7b69f78dc619b0a71680c664`), PR #94 (Task 002
> decision closure — AR-025, `03ffcb4dc949cd5137b589a6cdc33da9105de31d`),
> and PR #96 (Task 002 credential-storage gate — AR-026,
> `02b159a39c58a3396c1c249e80896a05c97bb757`). **The Task 002
> credential-storage gate is now open**; implementation may proceed only
> through
> [`task-002-final-implementation-prompt.md`](../07-implementation-plan/task-002-final-implementation-prompt.md)
> in its own coding session, entirely outside this plan. Task 003 remains
> proposed, not authorized.

## Status

**Proposed for ChatGPT review. Docs-only. No implementation. No gate
opened by this document. Does not create tests, code, or a redaction
utility.** This plan defines the tests Task 002's (now gate-opened, not
yet implemented) and later tasks' redaction utility and credential model
must pass — it does not implement or execute any of them, and it did not
open the Task 002 gate (that happened independently via AR-026/PR #96).

## Scope

This plan covers, per the accepted credential-security checklist:
credential model access; field groups; ACLs; no read-back; the redaction
utility; job logs; technical detail; exceptions; Python logging; chatter;
request/response traces; store mirrors; failure summaries; setup wizard
copy; UI copy; and the manual validation grep strategy a reviewer without
a live runtime can still perform in principle (though actually running it
requires the runtime this repository does not yet have — see
[`mvp-qa-test-strategy.md`](./mvp-qa-test-strategy.md) §Runtime limitation
strategy).

## A. Credential model access

- **[Gate]** ACL: exactly one row, granting
  `group_shopify_connector_admin` `perm_read=1, perm_write=1,
  perm_create=1, perm_unlink=0` on `shopify.connector.store.credential`.
  **No row for auditor/operator/reviewer** — Odoo's default-deny behavior
  must hold (confirmed at 19.0 source level: `_has_field_access()` denies
  by default absent an ACL row).
- **[Gate]** No unlink for **any** role, including Admin — matching the
  project-wide no-unlink-by-users posture already enforced on every core
  model.
- A future test must assert each of auditor/operator/reviewer raises
  `AccessError` on read/write/create/unlink, and that `fields_get()`/
  search expose nothing to them (the model is effectively invisible, not
  merely access-denied on individual operations).

## B. Field groups

- **[Gate]** `access_token` carries field-level
  `groups='shopify_connector_core.group_shopify_connector_admin'` as a
  **second, independent** layer beyond the model ACL — so a future
  regression that accidentally widens the model ACL still cannot expose
  the value to a non-admin role.
- A future test must prove this independence directly: simulate a
  (hypothetical, regression-only) broadened model ACL and confirm the
  field-level `groups=` still blocks non-admin read/write of
  `access_token` specifically.
- **Known, honestly-stated residual (not a defect to "fix," a fact to
  test-document):** `sudo()`/superuser mode bypasses field-level `groups`
  at the Odoo 19.0 source level (`_has_field_access()` returns `True`
  immediately for superuser). A future test suite should assert that
  **no** code path in the credential/client/lifecycle modules invokes
  `sudo()` other than the one sanctioned internal accessor
  (`_get_access_token()`), because this bypass is real and unmitigated
  by field `groups` alone.

## C. ACLs

- Covered jointly with §A above. A future test suite's access-matrix test
  is the authoritative proof point; this plan does not duplicate the
  matrix here — see
  [`foundation-test-matrix.md`](./foundation-test-matrix.md) §"Credential
  access matrix" for the full role × operation table.

## D. No read-back

- **[Gate]** No view/field/report/export renders the stored credential
  value on **any** surface, for **any** role, including Admin. No form,
  list, search, wizard, band, log, error, export, or report ever shows
  it after save.
- **[Gate]** No reveal/preview toggle; no full or partial value display
  (including "last 4 characters" — this is unverified-historical Shopify
  behavior per the accepted research, and is display-inviting regardless
  of whether it were true).
- Only `credential_present` / `credential_last_verified_at` (status, never
  value) may be rendered on any connector surface.
- A future test suite must assert: (a) the credential model has **zero**
  views defined anywhere in the module (a structural/manifest-level
  check, not just a behavioral one); (b) the entry widget (once it exists,
  Task 006 horizon) is write-only — value submitted, input cleared, never
  re-populated from storage; (c) if the compute-blank hardening variant is
  adopted, an ORM read of `access_token` returns empty for every user
  including Admin.

## E. Redaction utility

- **[Gate]** One shared utility (`redact(value)`, proposed location
  `shopify_connector_core/tools/redaction.py`) is the **only** redaction
  mechanism — no ad-hoc per-call-site string handling anywhere in the
  codebase.
- **[Gate]** Enforced at **both** layers — belt-and-braces: (1) at
  source — the credential service and the future API client pass every
  outbound log/exception payload through `redact()` before raising/
  writing; (2) at sink — the core job-log writing choke point defensively
  re-applies `redact()` to `message`, `technical_detail`, and
  `payload_snapshot`. **Neither layer alone is sufficient** — a future
  test suite must exercise a payload that would only be caught by the
  sink layer (e.g. a hypothetical future caller that forgets source-side
  redaction) to prove the belt-and-braces design actually holds, not just
  the happy path where both layers agree.
- **Sensitive key patterns (case-insensitive substring match):**
  `access_token`, `token`, `secret`, `password`, `authorization`,
  `x-shopify-access-token`, `api_key`, `apikey`, `client_secret`,
  `refresh_token`, `hmac`.
- **Sensitive value patterns (regex):** `shpat_[A-Za-z0-9]+` and
  `shprt_[A-Za-z0-9]+` (officially-confirmed Shopify token prefixes),
  plus an exact-match scrub of the current stored token value wherever the
  redaction context can access it internally — covering unknown/future
  token formats the prefix patterns would miss.

## F. Job logs

- **[Gate]** The token never appears in any `job.log` field —
  `message`, `technical_detail`, or `payload_snapshot` — under any
  circumstance, at any log level.
- Task 002 itself writes **no** `job.log` rows (the merged ACL grants no
  group create on `job.log`); the sink-layer redaction enforcement point
  is wired when Task 003 first writes API-derived logs. A future test
  suite must confirm Task 002's stamps-based audit trail (create_uid/
  write_uid/create_date/write_date + the explicit `credential_last_*`
  stamps) independently contains no token value, since Task 002 has no
  job-log surface to test against yet.

## G. Technical detail

- **[Gate]** Technical detail (HTTP status, `extensions.code`,
  `extensions.requestId`, cost/throttle data) lives only behind an
  explicit expand, post-redaction — never as primary copy (RA-016).
- Safe to show in technical detail (per the accepted redaction contract):
  shop domain, API version, scope handles, HTTP status codes, GraphQL
  `extensions.code` values, `extensions.requestId`, cost/throttle numbers,
  plain-language reasons, check names, timestamps.
- Unsafe to show anywhere, including behind the expand: anything matching
  the key/value patterns in §E; raw request headers; full raw request
  bodies of credential-bearing calls; a stack trace as primary copy
  (allowed only inside the redacted technical-detail expand).

## H. Exceptions

- **[Gate]** The token never appears in any exception message or
  `args` raised by the credential service, the future API client, test
  connection, readiness, or rollback/error-handling paths — including a
  constraint-violation message that must not echo submitted values.
- A future test must construct a fixture whose body/headers embed a dummy
  token, force an exception, and assert the token is absent from the
  exception's `str()` and `.args` both.

## I. Python logging

- **[Gate]** The token never appears in Python `logging` output at any
  level, including DEBUG, in any environment. No `logging` call in
  credential/client code may interpolate the raw token value — every such
  call must pass its payload through `redact()` first.

## J. Chatter

- **[Gate]** The token never appears in chatter. No core model has
  `mail.thread` today (confirmed by the Task 001A static sweep); this
  rule pre-commits any future adoption of `mail.thread` on a credential-
  adjacent model to the same redaction requirement, so a future test
  suite should include a placeholder/regression test that fails loudly if
  `mail.thread` is ever added to the credential model without an
  accompanying redaction-contract update.

## K. Request/response traces

- **[Gate]** Raw request headers are **never** logged — the
  `X-Shopify-Access-Token` header specifically must never appear in any
  logged request dump, because it *is* the token itself, not merely a
  reference to it.
- Response excerpts are redacted before persistence — `redact()` applied
  to any response body/technical-detail excerpt before it is written
  anywhere.

## L. Store mirrors

- **[Gate]** No store mirror field (`credential_present`,
  `credential_last_verified_at`, `credential_last_replaced_at`,
  `credential_last_failure_reason`, `granted_scopes`,
  `granted_scopes_checked_at`) ever contains the token value —
  `credential_last_failure_reason` in particular carries a content rule:
  it must be written **through** the redaction utility, plain-language,
  no token, no raw response.
- `granted_scopes` (scope handles, e.g. `read_products`) is non-secret by
  design (permission names, not secrets) and is explicitly **not**
  subject to the token redaction rule itself — a future test should
  confirm this distinction is intentional, not an oversight (i.e. scope
  handles are allowed to appear in the clear; only credential values and
  the other sensitive-key patterns are redacted).

## M. Failure summaries

- **[Gate]** `credential_last_failure_reason` and any test-connection/
  readiness failure summary must be plain-language, redacted, and free of
  raw response content — matching the accepted "named cause + fix" UX
  rule, not a raw HTTP code or `extensions.code` token as primary copy.

## N. Setup wizard copy

- **[Gate]** No wizard copy claims encryption, at-rest security, or any
  padlock-implying-encryption iconography (Task 006 horizon — flagged
  here so the eventual wizard implementation inherits this test
  requirement rather than rediscovering it).
- Allowed copy: "stored with restricted access and never shown again," or
  equivalent language describing masking + access restriction only.

## O. UI copy

- **[Gate]** The same forbidden-phrase list applies to every connector
  surface, not only the wizard: "encrypted," "encryption," "bank-level
  encryption," "encrypted at rest," any at-rest security claim, any claim
  that Odoo.sh/Odoo Online/on-premise hosting encrypts the value (hosting
  scope is explicitly unconfirmed per the accepted AR-022 research), any
  reveal/preview toggle, any display of full or partial token value
  (including "last 4").
- **[Gate]** No copy anywhere may claim the view-arch `password="1"`
  attribute (or the `password=True` widget more generally) encrypts the
  field — it is UI-display masking only, confirmed at the Odoo 19.0
  source level (no `Char` field parameter named `password`; no
  occurrence of "encrypt" in `fields.py`/`fields_textual.py`/`models.py`
  on branch 19.0). No copy anywhere may claim `ir.config_parameter` is
  secure secret storage — it is plain, unencrypted key-value storage
  under a single `group_system`-only ACL, per the accepted AR-022
  research. A future review must scan every credential-touching PR's
  code, docstrings, comments, and copy for both of these specific
  phrasings, not only the broader "encryption" keyword, since neither
  mechanism is used by this connector's design but a future contributor
  unfamiliar with AR-022 could plausibly reach for either as a
  shorthand explanation and inadvertently overstate it.
- Token *status* (present / last verified) is the only credential-derived
  content ever rendered, and it must be honest — real timestamps, no
  implied-live freshness.
- **Honestly-stated residual (database/backup readability).** Beyond the
  `sudo()`/superuser bypass already named in §B, anyone with direct
  database or backup access can read the stored token regardless of any
  Odoo-level access control or copy choice — this is the same residual
  every official Odoo credential field carries (AR-022) and must be
  stated plainly in customer-facing documentation (see
  [`../08-release-readiness/mvp-release-readiness-checklist.md`](../08-release-readiness/mvp-release-readiness-checklist.md)
  "Acceptable known limitations"), never glossed over in UI copy.

## P. Manual validation grep strategy

For a reviewer with a live Odoo 19 + PostgreSQL instance (the runtime
this repository does not yet have — see
[`mvp-qa-test-strategy.md`](./mvp-qa-test-strategy.md) §Runtime limitation
strategy), the following closes the gap no static/unit test can close
alone:

1. Set a dummy token (e.g. `shpat_DUMMYDUMMYDUMMY`) via the credential
   service.
2. Trigger every code path that could plausibly log or raise on it: a
   forced test-connection failure, a forced readiness-check failure, a
   deliberately malformed API response (once Task 003 exists), a
   constraint violation on the credential model.
3. Grep the Odoo server log file, the `job.log` table contents, the
   `ir.logging` table (if used), and every store-mirror field's actual
   stored value for the literal dummy-token string.
4. Confirm **zero hits** outside the `access_token` column itself.
5. Repeat with an arbitrary-format dummy value (not matching the
   `shpat_`/`shprt_` prefix patterns) to prove the exact-value-scrub path,
   not just the prefix-pattern path, is exercised.
6. Confirm no menu/action/view/wizard/controller exists that could render
   the value (a structural check, independent of the grep).

## Required test cases

The following test cases are **required** of Task 002's (and later
tasks') redaction utility and credential-handling code, matching the
proposed spec's own "Tests required" sections:

1. **Dummy `shpat_` token never appears outside the credential field.**
   Set `shpat_DUMMYDUMMYDUMMY`; assert absence from every other
   persisted char/text field, every log line, and every exception across
   the full set of code paths exercised in this task.
2. **Dummy arbitrary-format token exact scrub.** Set a token that does
   **not** match `shpat_`/`shprt_` (e.g. a hypothetical future token
   format); assert the exact-value-scrub mechanism still redacts it
   wherever the redaction context can access the stored value internally.
3. **Nested dict/list redaction.** `redact()` applied to a nested
   structure (e.g. `{"headers": {"Authorization": "..."}, "body":
   {"errors": [{"extensions": {"token": "..."}}]}}`) redacts every
   matching key/value at every nesting depth.
4. **Header key redaction.** `X-Shopify-Access-Token`,
   `Authorization` (any casing) are redacted as keys, independent of
   whether their value also matches a value pattern.
5. **Exception redaction.** A fixture forcing an exception with a
   token-bearing message/args is redacted before the exception is raised
   or, if raised unredacted internally, before it reaches any logged or
   persisted surface.
6. **Job log redaction.** Once a job-log-writing task exists (Task 003
   onward), every `job.log` row written from a token-bearing failure
   contains no token in `message`, `technical_detail`, or
   `payload_snapshot`.
7. **Technical detail redaction.** The technical-detail expand's content
   is drawn only from the safe-to-show list (§G) — never a raw header
   dump or unredacted response body.
8. **Failure summary redaction.** `credential_last_failure_reason` (and
   any later readiness/test-connection failure summary) never contains
   the token, verified by both the prefix-pattern and exact-value-scrub
   paths.
9. **No encryption claims.** A grep-style test (or manual review checklist
   item, until a runtime exists) confirms none of the forbidden phrases in
   §O appears anywhere in code, docstrings, comments, or copy across the
   full diff of any credential-touching PR.
10. **No padlock-implied encryption.** A design/copy review checklist item
    (UI/UX review, Task 006 horizon) confirms no icon or visual treatment
    implies encryption where none exists.
11. **No Odoo.sh/Odoo Online/on-prem encryption claims.** Same grep/review
    discipline as item 9, specifically scanning for hosting-scope
    encryption claims (which the accepted AR-022 research found
    unconfirmed for this project's applicable hosting scenarios).
12. **`sudo()` use reviewed.** Every `sudo()` call in the diff of any
    credential/client/lifecycle-touching PR is individually justified in
    writing in the PR description, is minimal in scope, never crosses a
    store/record-rule boundary, and matches one of the two sanctioned
    elevations named by the architecture package (the client's internal
    credential read; the core job-log system-append write choke point) —
    any other `sudo()` in the diff is a review failure, to be caught by
    this checklist item before merge, not discovered later.
13. **No `password=True`/`ir.config_parameter` security-mechanism
    claims.** Same grep/review discipline as item 9, specifically
    scanning for a claim that the view-arch `password` attribute
    encrypts a field, or that `ir.config_parameter` is secure secret
    storage — neither mechanism is used by this connector's design, and
    neither may be cited as if it provided security beyond access
    control (§A/§O).

## Redaction test-idempotence requirement

Per the accepted redaction contract, `redact()` must be **idempotent**:
`redact(redact(x)) == redact(x)`. A future test suite must assert this
directly (not just informally expect it), since a non-idempotent
redaction function could silently double-mask or, worse, fail to
re-redact a value that leaks through a secondary code path that calls
`redact()` on an already-redacted payload.
