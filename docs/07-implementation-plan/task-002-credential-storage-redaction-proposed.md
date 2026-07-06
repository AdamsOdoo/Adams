# Task 002 — Credential Storage, Masking, and Redaction Foundation (PROPOSED)

> Written to the `CLAUDE.md` §9 implementation-task structure (see
> [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)),
> derived from the architecture package
> [`../03-architecture/credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md).

## Status

**Proposed only. Not authorized.** This document authorizes nothing. Task
002 may start only after: (1) ChatGPT accepts AR-024 (the architecture
package) and resolves its decision points; (2) ChatGPT performs an
explicit gate-opening act naming Task 002 (the AR-021 gate does **not**
cover it — it explicitly forbids credential fields); (3) ChatGPT issues a
separate final task prompt. Until all three happen, creating any file
below is a governance violation.

**Acceptance note (2026-07-06, PR #92 acceptance patch;
[`AR-024`](../05-qa/architecture-review-log.md)):** this task plan is
**accepted by ChatGPT as the recommended next coding task plan — not
authorized**. Starting it still requires (1) a separate, explicit
credential-storage implementation-gate-opening act, and (2) a separate
final `CLAUDE.md` §9 task prompt. The compute-blank no-read-back
hardening variant, the `token_variant` vocabulary, and the
scope-snapshot placement all remain decisions for that final prompt, not
decided by this acceptance.

## Objective

Create the credential storage, status-mirror, service-method, and
redaction foundation in `shopify_connector_core`, exactly as specified in
the architecture package: the Admin-only
`shopify.connector.store.credential` model, the non-secret status mirrors
on `shopify.connector.store`, the set/replace/clear service methods with
audit trail, and the redaction utility — **with zero Shopify API calls,
zero views, and zero UI.**

## Preconditions

- AR-024 accepted, including ChatGPT's resolution of: the compute-blank
  no-read-back hardening variant (adopt/drop); `token_variant` vocabulary
  (default `offline_custom_app` stands unless the MBQ-05 direction says
  otherwise); scope-snapshot placement (`store` as proposed, or moved).
- Task 001 merged (it is — PR #88) and the Task 001A QA closure noted:
  there is still no Odoo runtime/test framework/CI in this repository, so
  the Tests section's fallback applies unless infrastructure has been
  separately authorized by then.
- PR #90/#91 merged (they are).

## Allowed files

- `addons/shopify_connector_core/models/shopify_connector_store_credential.py` (new)
- `addons/shopify_connector_core/models/shopify_connector_store.py` (add
  the six status-mirror fields only; no other change)
- `addons/shopify_connector_core/models/__init__.py` (import line)
- `addons/shopify_connector_core/tools/__init__.py` (new)
- `addons/shopify_connector_core/tools/redaction.py` (new)
- `addons/shopify_connector_core/__init__.py` (only if a `tools` import
  line is required)
- `addons/shopify_connector_core/security/ir.model.access.csv` (add the
  single credential-model Admin row)
- `addons/shopify_connector_core/__manifest__.py` (version bump only)
- `addons/shopify_connector_core/tests/__init__.py`,
  `addons/shopify_connector_core/tests/test_credential_access.py`,
  `addons/shopify_connector_core/tests/test_redaction.py`,
  `addons/shopify_connector_core/tests/test_credential_service.py`
  (per the Tests section's applicability rule)
- `docs/01-research/research-handoff.md` (mandatory handoff update)

## Forbidden files

Everything else. Explicitly: any view/menu/action/wizard XML; any
controller; any cron/data file; `security/shopify_connector_security.xml`
(no new groups); any other core model file (`job`, `job_log`, `location`,
`binding_mixin`, `store_settings` untouched); anything under
`addons/adams_base`; any domain module; any CI/workflow/Dockerfile/
requirements file; any file under `docs/` other than the handoff; any
migration.

## Exact proposed model/fields

Per the architecture package's field tables (authoritative; restated in
brief):

**New model `shopify.connector.store.credential`** —
`_name = 'shopify.connector.store.credential'`, `_description = 'Shopify
Connector Store Credential'`, no views, no `mail.thread`:

- `store_id`: Many2one → `shopify.connector.store`, required, index,
  readonly, `ondelete='restrict'`; SQL unique constraint (one credential
  row per store).
- `access_token`: Char, not required,
  `groups='shopify_connector_core.group_shopify_connector_admin'`;
  written only via the service methods. (If ChatGPT adopts the
  compute-blank variant, this becomes the stored field behind a
  compute-blank public read — final shape fixed in the task prompt.)
- `token_variant`: Selection `[('offline_custom_app', 'Offline Custom App
  Token')]`, default `offline_custom_app` (extensible later via
  `selection_add`).
- `credential_state`: Selection `[('absent','Absent'), ('present',
  'Present'), ('invalid','Invalid')]`, required, default `absent`,
  readonly (service-written).

**Status mirrors on `shopify.connector.store`** (all readonly,
system-written by the credential service only): `credential_present`
(Boolean, default False), `credential_last_verified_at` (Datetime),
`credential_last_replaced_at` (Datetime), `credential_last_failure_reason`
(Char; must be written through the redaction utility),
`granted_scopes` (Text, serialized JSON array), `granted_scopes_checked_at`
(Datetime). *(The last two move to the credential model instead if
ChatGPT overrules the proposed placement.)*

**Service methods on the credential model** (names proposed):
`action_set_token(store, value)` (create-or-update + stamps + mirrors),
`action_replace_token(store, value)` (same, stamps
`credential_last_replaced_at`, resets verification state),
`action_clear_token(store)` (empties value, `credential_state='absent'`,
mirrors; used by the future disconnect), and the internal-only
`_get_access_token(store)` accessor (documented `sudo()` justification;
never returns the value to logs/exceptions/callers outside the future
client). Test connection is **not** implemented here — verification
stamps are written by Task 003 later; this task only creates the fields.
**Audit in this task is stamps-based only** (standard
`create_uid/write_uid/create_date/write_date` plus the explicit
`credential_last_*` stamps): Task 002 writes **no `job.log` rows** — the
merged ACL deliberately grants no group create on `job.log`
(system-appended rows), and the system-append write path plus
parent-job mechanics are a named Task 003 decision point in the
architecture package.

## Exact security/access posture

- ACL: **one** new row —
  `access_shopify_connector_store_credential_admin` granting
  `group_shopify_connector_admin` `perm_read=1, perm_write=1,
  perm_create=1, perm_unlink=0`. **No row for auditor/operator/reviewer**
  (Odoo default-deny), documented with a CSV-adjacent comment in the
  model docstring.
- Field-level `groups=` on `access_token` as the second layer.
- No record rules (Phase 1 single-store posture unchanged).
- The **only** sanctioned `sudo()` is inside `_get_access_token`; any
  other `sudo()` in this task's diff is a review failure.
- The store/settings `perm_create` gap is **not** touched by this task.

## Redaction contract

`tools/redaction.py` implements `redact(value)` (str/dict/list,
recursive, idempotent), `SENSITIVE_KEYS` (case-insensitive:
`access_token`, `token`, `secret`, `password`, `authorization`,
`x-shopify-access-token`, `api_key`, `apikey`, `client_secret`,
`refresh_token`, `hmac`) and `SENSITIVE_VALUE_PATTERNS`
(`shpat_[A-Za-z0-9]+`, `shprt_[A-Za-z0-9]+`), plus an exact-match scrub
hook for a known current token value. Replacement marker: `***`.
Enforcement in this task: the credential service passes every message it
writes (including `credential_last_failure_reason` and any audit log
text) through `redact()`; the job-log sink enforcement point is wired
when Task 003 first writes API-derived logs, but the utility ships —
fully tested — now. No Python `logging` call in this task's code may
interpolate the token.

## Tests required

Written as Odoo `TransactionCase` tests under
`addons/shopify_connector_core/tests/`:

1. **Access matrix:** for each of auditor/operator/reviewer demo users:
   read, write, create, unlink on the credential model each raise
   `AccessError`; `fields_get`/search expose nothing. Admin: read/write/
   create succeed; unlink denied.
2. **Field access:** a non-admin user (if ever granted model access in a
   future regression) cannot read/write `access_token` (field-`groups`
   layer holds independently).
3. **Redaction:** key-based redaction (incl. `Authorization` header
   casing), `shpat_`/`shprt_` pattern hits inside longer strings,
   exact-value scrub of an arbitrary-format dummy token, nested
   dict/list, idempotence, non-string passthrough. All test tokens are
   dummies (e.g. `shpat_DUMMYDUMMYDUMMY`).
4. **Service behavior:** set → mirrors flip
   (`credential_present=True`, `credential_state='present'`); replace →
   `credential_last_replaced_at` stamped, verification state reset;
   clear → value emptied, `absent`, `credential_present=False`; one row
   per store enforced (duplicate create raises); the stamps-based audit
   trail (`create_uid`/`write_uid`/`write_date` + `credential_last_*`
   stamps) reflects each action and **contains no token value** (assert
   the dummy token string is absent from every persisted char/text field
   except `access_token` itself). No `job.log` row is created by any
   Task 002 code path (assert none exists after the service calls).
5. **No-read-back (if compute-blank variant adopted):** ORM read of
   `access_token` returns empty for every user including Admin;
   `_get_access_token` still returns the stored value internally.

**Applicability rule (per Task 001A precedent):** this repository has no
Odoo runtime; if that is still true at coding time, the tests must still
be written and syntax-validated, the PR must state they were not
executed, and the Manual validation checklist below becomes mandatory
review evidence. Inventing a non-Odoo test harness is forbidden.

## Manual validation

On a live Odoo 19 + PostgreSQL instance (extends the Task 001A checklist):

1. Upgrade module; credential model appears in `ir.model`; exactly one
   new ACL row.
2. As each non-admin role: the credential model is invisible/denied
   (read/search/create/write all fail).
3. As Admin: set a dummy token via the service; mirrors update; replace
   and clear behave as specified.
4. `ir.model.fields` shows `access_token` with the Admin group
   restriction; no view references the field anywhere.
5. Grep the database logs/audit surfaces for the dummy token: zero hits
   outside the credential column itself.
6. Confirm no menu/action/view/wizard/controller/cron was added; no
   Shopify call is possible (no client exists).

## Rollback

Revert the Task 002 PR (single commit-set; nothing depends on it yet).
Data note: uninstalling/reverting drops the credential model and mirror
fields — stored tokens are lost and re-enterable by the Admin; no
business data is affected. A partially-failed deployment (e.g. ACL loaded
but model not) is recovered by module upgrade after revert; no migration
is needed in either direction.

## Acceptance criteria

- Only allowed files changed; module installs/upgrades cleanly.
- Credential model + mirrors + services + redaction utility exist exactly
  as specified (or as amended by ChatGPT's resolutions of the named
  decision points).
- Access matrix proven (tests and/or manual evidence).
- The dummy token provably absent from every log/audit/mirror surface.
- Zero views, zero API calls, zero wizard/controller/cron artifacts in
  the diff.
- No encryption claim anywhere in code, docstrings, comments, or copy.
- [`../05-qa/credential-security-redaction-review-checklist.md`](../05-qa/credential-security-redaction-review-checklist.md)
  gates all pass.
- Handoff updated; rollback notes in the PR.

## Definition of done

Per `CLAUDE.md` §9 / `implementation-task-template.md` §7: code + tests
written (and passing where a runtime exists), lint/format clean;
`pr-review-checklist.md` §C satisfied; shortcuts logged in
`technical-debt-register.md`; only allowed files changed; handoff updated;
quality gate confirmed; **ChatGPT reviews and accepts the implementation
against this task before any next task starts.**

## Explicit exclusions

- **No API client** (no HTTP code, no `requests` import, no GraphQL
  strings).
- **No test connection** (no verification writes; Task 003 owns them).
- **No setup wizard** (no TransientModel, no step logic).
- **No UI gate** opened or presumed — zero views/menus/actions.
- **No domain logic** of any kind.
- **No webhooks/controllers/cron.**
- **No product/customer/order/inventory/fulfillment** anything.
