# Task 002 — Final Implementation Prompt (gate-ready, not yet issued)

> **Acceptance (2026-07-07, PR #94 acceptance patch;
> [`AR-025`](../05-qa/architecture-review-log.md)):** **Accepted by
> ChatGPT as the binding final Task 002 implementation prompt.** It
> remains **NOT ISSUED and NOT AUTHORIZED**: it may only be issued
> after the separate Task 002 gate-opening act
> ([`task-002-gate-opening-proposal.md`](./task-002-gate-opening-proposal.md))
> is explicitly accepted by ChatGPT and merged into
> `Shopify-connector`. Precondition (1) below — AR-025 acceptance — is
> now satisfied; preconditions (2) and (3) are not. The prompt content
> below is binding as accepted; any deviation requires a new ChatGPT
> decision.
>
> **Status: prepared 2026-07-06 via AR-025 — NOT ISSUED, NOT AUTHORIZED.**
> This document is the complete, copy-paste final `CLAUDE.md` §9 task
> prompt for **Task 002 — Credential Storage, Masking, and Redaction
> Foundation**. It may be issued to Claude Code **only after ChatGPT has
> (1) accepted AR-025 (the decision closure in
> [`task-002-decision-closure.md`](./task-002-decision-closure.md)) and
> (2) performed the separate, explicit gate-opening act proposed in
> [`task-002-gate-opening-proposal.md`](./task-002-gate-opening-proposal.md),
> and that gate-opening act is merged into `Shopify-connector`.** Until
> both happen, executing anything below is a governance violation. The
> decisions baked in below: compute-blank **rejected** (stored Char
> behind two access layers); `token_variant` = single value
> `offline_custom_app`; scope snapshot on `shopify.connector.store`.
>
> Everything between the markers below is the prompt to issue verbatim.

---

**BEGIN FINAL TASK PROMPT**

Execute **Task 002 — Credential Storage, Masking, and Redaction
Foundation** for the Odoo 19 ↔ Shopify Connector.

Read first: `CLAUDE.md`; the latest entry of
`docs/01-research/research-handoff.md`;
`docs/07-implementation-plan/task-002-final-implementation-prompt.md`
(this prompt's committed copy);
`docs/07-implementation-plan/task-002-decision-closure.md`;
`docs/07-implementation-plan/task-002-credential-storage-redaction-proposed.md`;
`docs/03-architecture/credential-connection-api-client-planning.md`;
`docs/05-qa/credential-security-redaction-review-checklist.md`;
`docs/05-qa/task-002-pre-implementation-review-checklist.md`;
`addons/shopify_connector_core/` (all existing files).

## Repo / branch

- **Repository:** AdamsOdoo/Adams
- **Base branch:** `Shopify-connector` (never `main`, never plain `dev`)
- **Working branch:** create `claude/task-002-credential-storage` from
  latest `Shopify-connector`.
- **Expected baseline:** latest `Shopify-connector` **must contain** (1)
  PR #92's merge commit `f74aaf204745ce0087733870fe56bdda74bfa79a`, (2)
  the merged AR-025 acceptance patch, and (3) the merged Task 002
  gate-opening act. Verify all three before writing anything. If any is
  missing, **stop and report** — do not proceed.

## Gate scope (what is authorized)

Exactly and only: the `shopify.connector.store.credential` model, the
six status-mirror fields on `shopify.connector.store`, the credential
service methods, the redaction utility, the single credential ACL row,
the tests below, a manifest version bump, and the mandatory handoff
update. **Nothing else.** The AR-021 prohibitions on external API
calls, UI, webhooks, controllers, cron, setup wizard, and test
connection remain fully in force.

## Hard rules

- Do not touch `main` or plain `dev`.
- Zero Shopify/external API calls: no HTTP code, no `requests`/`urllib`
  import, no GraphQL strings, no network access of any kind.
- Zero UI: no views, menus, actions, wizards, TransientModels, or XML
  other than nothing — this task adds **no XML file at all**.
- No webhooks, controllers, or cron.
- No domain logic (product/customer/order/inventory/fulfillment).
- No `mail.thread` / chatter on any model.
- No new security group; `security/shopify_connector_security.xml` must
  not change.
- No change to any existing ACL row; the store/settings `perm_create`
  gap and the `job.log` no-create posture stay as merged.
- No `job.log` writes from any Task 002 code path.
- Exactly **one** `sudo()` in the entire diff: inside
  `_get_access_token`. Any other `sudo()` is a review failure.
- No raw SQL anywhere in the diff.
- No `ir.config_parameter` reads/writes.
- No encryption claim anywhere (code, docstrings, comments, tests,
  handoff): never "encrypted"/"encryption"; never claim `password=True`
  encrypts; never claim `ir.config_parameter` is secure secret storage;
  never claim Odoo.sh/Odoo Online/on-premise encryption coverage. State
  the honest residual instead (see model docstring requirement).
- No real credential values anywhere: every token in tests/docs is a
  dummy (e.g. `shpat_DUMMYDUMMYDUMMY0000000000000000`).
- No migrations (none are needed: all additions are new
  model/fields with safe defaults).
- Do not modify DEC-003 through DEC-020, `docs/04-decisions/README.md`,
  `docs/05-qa/defect-pattern-log.md`, or
  `docs/03-architecture/master-blueprint-open-questions.md`.
- Do not start Task 003 or any other task. Stop after opening the draft
  PR.

## Allowed files (exhaustive)

- `addons/shopify_connector_core/models/shopify_connector_store_credential.py` (new)
- `addons/shopify_connector_core/models/shopify_connector_store.py`
  (add the six mirror fields only; no other change)
- `addons/shopify_connector_core/models/__init__.py` (one import line)
- `addons/shopify_connector_core/tools/__init__.py` (new)
- `addons/shopify_connector_core/tools/redaction.py` (new)
- `addons/shopify_connector_core/__init__.py` (only if a `tools` import
  line is required)
- `addons/shopify_connector_core/security/ir.model.access.csv` (append
  the single credential row only)
- `addons/shopify_connector_core/__manifest__.py` (version bump only:
  `19.0.1.0.0` → `19.0.1.1.0`)
- `addons/shopify_connector_core/tests/__init__.py` (new)
- `addons/shopify_connector_core/tests/test_credential_access.py` (new)
- `addons/shopify_connector_core/tests/test_redaction.py` (new)
- `addons/shopify_connector_core/tests/test_credential_service.py` (new)
- `docs/01-research/research-handoff.md` (mandatory handoff update)

## Forbidden files

Everything else, explicitly including: any XML file; any controller/
webhook/cron/data file; `security/shopify_connector_security.xml`; the
`job`, `job_log`, `location`, `binding_mixin`, and `store_settings`
model files; anything under `addons/adams_base`; any domain module; any
CI/workflow/Dockerfile/requirements file; any file under `docs/` other
than the handoff; any migration directory.

## Implementation requirements (exact)

### 1. Model `shopify.connector.store.credential`

`_name = 'shopify.connector.store.credential'`,
`_description = 'Shopify Connector Store Credential'`. No `_inherit`,
no `mail.thread`, no views. The model docstring must state: (a) the
Admin-only default-deny posture (no ACL row for auditor/operator/
reviewer is deliberate, not an omission); (b) that the value is stored
plain behind access control — **not encrypted** — and remains readable
to `sudo()`-context code, direct database access, and backups (honest
residual, per AR-022/AR-024/AR-025); (c) that client-credentials fields
(`client_id`, `client_secret`, token cache, expiry) are deliberately
absent pending the MBQ-05 decision (the model is the seam that will
absorb them); (d) that the only sanctioned `sudo()` is inside
`_get_access_token`.

Fields:

- `store_id = fields.Many2one('shopify.connector.store', required=True,
  index=True, readonly=True, ondelete='restrict')`
- `access_token = fields.Char(copy=False,
  groups='shopify_connector_core.group_shopify_connector_admin')` — not
  required (empty = cleared/absent); written only via the service
  methods below; **no compute, no inverse, no related, no default**.
- `token_variant = fields.Selection(
  [('offline_custom_app', 'Offline Custom App Token')],
  default='offline_custom_app')` — exactly one value; extension happens
  later via `selection_add` in a future gated task, not now.
- `credential_state = fields.Selection(
  [('absent', 'Absent'), ('present', 'Present'), ('invalid', 'Invalid')],
  required=True, default='absent', readonly=True)` — service-written;
  nothing in Task 002 sets `invalid` (that is a Task 003+ transition;
  the value exists so the vocabulary is complete and tested).

SQL constraint: `('store_id_uniq', 'unique(store_id)', 'Only one
credential record is allowed per store.')` — mirroring the
`store.settings` pattern.

### 2. Status mirrors on `shopify.connector.store` (add exactly six fields)

All `readonly=True`, written only by the credential service in this
task (single-writer rule; Task 003's test connection joins later):

- `credential_present = fields.Boolean(default=False, readonly=True)`
- `credential_last_verified_at = fields.Datetime(readonly=True)`
- `credential_last_replaced_at = fields.Datetime(readonly=True)`
- `credential_last_failure_reason = fields.Char(readonly=True)` — every
  write to this field, from any code path, must pass through
  `redact()` first.
- `granted_scopes = fields.Text(readonly=True)` — serialized JSON array
  of scope handles (e.g. `["read_products"]`); **no writer in Task 002**
  (Task 003 writes it); created now so Task 003 adds behavior only.
- `granted_scopes_checked_at = fields.Datetime(readonly=True)` — same.

No other change to the store model file: no method, no constraint, no
reordering.

### 3. Service methods (on `shopify.connector.store.credential`)

All four are model-level methods (`@api.model`), taking the store
record as first argument. Write paths run **as the calling user with no
`sudo()`** so the ACL layer stays live (a non-admin caller must fail
with `AccessError` from the ORM itself). All writes of one action
happen in the same transaction (single `create()`/`write()` calls; no
partial states). No method ever returns, logs, or embeds the token
value; every string any of them writes to any mirror passes through
`redact()`.

- `action_set_token(store, value)` — validates `value` is a non-empty
  `str` (raise `ValidationError` with a message that **does not echo
  the value**); creates the store's credential row if absent, else
  updates it; writes `access_token=value`,
  `credential_state='present'`; mirrors: `credential_present=True`.
  Returns `None`.
- `action_replace_token(store, value)` — same validation and
  create-or-update; additionally stamps
  `credential_last_replaced_at=now` and resets the verification state:
  `credential_last_verified_at=False`. (It does **not** touch
  `last_test_connection_*` — those belong to Task 003.) Returns `None`.
- `action_clear_token(store)` — empties the value
  (`access_token=False`), sets `credential_state='absent'`; mirrors:
  `credential_present=False`, `credential_last_verified_at=False`,
  `credential_last_failure_reason=False`. Preserves the row and
  `credential_last_replaced_at` (history is never deleted — MBQ-08).
  Idempotent when no credential row exists (no error, no row created).
  Returns `None`.
- `_get_access_token(store)` — internal-only accessor; the **only**
  `sudo()` in the diff, scoped to reading the single credential row of
  the given store (`.sudo()` on the credential model search/browse for
  `store_id = store.id` only). Its docstring must carry the written
  justification (DEC-004: the elevation never crosses store/record-rule
  boundaries; it reads one store's own secret for a caller already
  operating on that store). Returns the raw value or `False`; never
  logs it; never places it in an exception; no caller in Task 002's
  shipped code invokes it outside tests (its consumer is Task 003's
  client).

### 4. Redaction utility `tools/redaction.py`

Pure module, no Odoo imports, no logging, no side effects:

- `SENSITIVE_KEYS` — case-insensitive **substring** match on dict keys:
  `access_token`, `token`, `secret`, `password`, `authorization`,
  `x-shopify-access-token`, `api_key`, `apikey`, `client_secret`,
  `refresh_token`, `hmac`.
- `SENSITIVE_VALUE_PATTERNS` — compiled regexes:
  `shpat_[A-Za-z0-9]+`, `shprt_[A-Za-z0-9]+`. (Historical `shpca_`/
  `shppa_` prefixes are **not** asserted — the exact-match scrub covers
  arbitrary formats.)
- `REDACTED = '***'` — the replacement marker.
- `redact(value, extra_secrets=None)`:
  - `str` → apply every value pattern; then exact-match scrub each
    non-empty string in `extra_secrets` (iterable of currently-known
    secret values, e.g. the stored token, passed by callers that hold
    it); overlapping/repeated occurrences all replaced with `***`.
  - `dict` → for each item: if the key (stringified, lowercased)
    contains any sensitive key, replace the entire value with `***`;
    otherwise recurse into the value. Key matching must catch header
    casing variants (`Authorization`, `X-Shopify-Access-Token`).
  - `list`/`tuple` → recurse per element, preserving the container
    type.
  - any other type → returned unchanged (non-string passthrough).
  - **Idempotent** (`redact(redact(x)) == redact(x)`); never raises on
    odd input; returns the same shape it was given; never mutates its
    input in place.

### 5. ACL — append exactly one row to `security/ir.model.access.csv`

```
access_shopify_connector_store_credential_admin,shopify.connector.store.credential.admin,model_shopify_connector_store_credential,shopify_connector_core.group_shopify_connector_admin,1,1,1,0
```

No row for auditor/operator/reviewer (Odoo default-deny — deliberate);
`perm_unlink=0` for everyone (history rule). No other CSV line may
change.

### 6. Manifest

Version bump only: `'version': '19.0.1.1.0'`. No dependency, data, or
description change.

## Tests required (exact)

Odoo `TransactionCase` tests under
`addons/shopify_connector_core/tests/`. Every token literal is a dummy.
Create four demo users (one per group) in `setUpClass` using the four
existing groups.

**`test_credential_access.py`:**

1. For each of auditor/operator/reviewer users: `read`, `write`,
   `create`, `unlink`, and `search` on
   `shopify.connector.store.credential` raise `AccessError`;
   `fields_get()` on any accessible model context exposes nothing of
   the credential model to them.
2. Admin user: `read`/`write`/`create` succeed; `unlink` raises
   `AccessError`.
3. Field-`groups` second layer, proven independently of the model ACL:
   inside the test transaction, create a temporary test-only
   `ir.model.access` row granting the operator group read on the
   credential model (simulating a future ACL-widening regression), then
   assert that for the operator user `access_token` is still absent
   from `fields_get()` and an explicit read of `access_token` still
   raises an access error. The temporary row exists only inside the
   rolled-back test transaction — the shipped CSV is untouched.
4. `display_name` of a credential record never contains the token
   value.

**`test_redaction.py`:**

5. Key-based redaction, including header-casing variants
   (`Authorization`, `X-Shopify-Access-Token`) and every
   `SENSITIVE_KEYS` entry.
6. Value-pattern hits: `shpat_…`/`shprt_…` inside longer strings.
7. Exact-match scrub via `extra_secrets` of an arbitrary-format dummy
   (no `shpat_` prefix) — proving unknown formats are covered.
8. Nested dict/list/tuple structures, shape preserved.
9. Idempotence: `redact(redact(x)) == redact(x)`.
10. Non-string passthrough (int/float/None/bool unchanged).
11. Input not mutated in place.

**`test_credential_service.py`:**

12. `action_set_token`: row created (one per store),
    `credential_state='present'`, `credential_present=True`.
13. `action_replace_token`: `credential_last_replaced_at` stamped,
    `credential_last_verified_at` reset to `False`, value replaced.
14. `action_clear_token`: value emptied, `credential_state='absent'`,
    `credential_present=False`, failure reason cleared, row preserved,
    `credential_last_replaced_at` preserved; idempotent with no row.
15. Duplicate credential row for the same store raises (SQL unique
    constraint).
16. Empty/non-string value to set/replace raises `ValidationError`
    whose message does not contain the submitted value.
17. Stamps-based audit: `create_uid`/`write_uid`/`write_date` reflect
    the acting admin user for each action.
18. **Leak sweep:** after set/replace/clear with the dummy token, the
    dummy string is absent from every persisted char/text field on
    `store` and the credential row **except** `access_token` itself
    (iterate `fields_get`/`read` as admin and assert).
19. **No job/log writes:** `shopify.connector.job` and
    `shopify.connector.job.log` row counts are unchanged by every
    service call.
20. `_get_access_token` returns the stored value internally; the
    non-admin service-call paths still raise `AccessError` (no hidden
    elevation in write paths).
21. Source-level guard: the diff's Python files contain exactly one
    `sudo(` occurrence (in `_get_access_token`) — assert via a source
    scan of the module's model files in a test, or document the grep in
    the PR body if a source-scan test is judged too brittle.

**Applicability rule (Task 001A precedent, restated):** if the
repository still has no Odoo runtime at coding time, write the tests
anyway, `py_compile`-validate them, state plainly in the PR that they
were **not executed**, and make the manual validation below mandatory
review evidence. Do not invent a non-Odoo test harness. Do not install
Odoo/PostgreSQL/CI — infrastructure remains unauthorized.

## Manual validation (live Odoo 19 + PostgreSQL; extends the Task 001A checklist)

1. Upgrade the module; `shopify.connector.store.credential` appears in
   `ir.model`; exactly one new ACL row exists; exactly six new fields
   on the store model.
2. As each non-admin role: the credential model is invisible/denied
   (read/search/create/write all fail; no `fields_get` exposure).
3. As Admin: set a dummy token via the service; mirrors update; replace
   stamps and resets as specified; clear empties and preserves history.
4. `ir.model.fields` shows `access_token` with the Admin group
   restriction; no `ir.ui.view` anywhere references the credential
   model or any mirror field.
5. Grep the database (`pg_dump` of the test DB) and the server log for
   the dummy token: zero hits outside the credential column itself.
6. Confirm no menu/action/view/wizard/controller/cron exists; no
   Shopify call is possible (no client exists; no HTTP import in the
   module).

## Rollback

Revert the single Task 002 PR (nothing depends on it). Uninstalling or
reverting drops the credential model and the six mirror fields — stored
tokens are lost and re-enterable by the Admin; no business data is
affected. A partially-failed deployment (e.g. ACL loaded but model not)
is recovered by module upgrade after revert. No migration in either
direction.

## Acceptance criteria

- Only allowed files changed; module installs/upgrades cleanly.
- Model + mirrors + services + redaction utility exist **exactly** as
  specified above (the three AR-025 decisions applied; no deviation
  without a new ChatGPT decision).
- Access matrix proven (tests, and manual evidence if no runtime).
- The dummy token provably absent from every persisted/logged surface
  except the credential column.
- Zero XML, zero views, zero API calls, zero wizard/controller/cron
  artifacts, zero `job.log` writes in the diff.
- Exactly one `sudo()` (in `_get_access_token`); no raw SQL.
- No encryption claim anywhere; the honest-residual docstring present.
- Every gate item in
  `docs/05-qa/credential-security-redaction-review-checklist.md` §A–§F
  and every item in
  `docs/05-qa/task-002-pre-implementation-review-checklist.md` §B
  passes.
- Handoff updated; rollback notes in the PR body.

## Definition of done

Per `CLAUDE.md` §9 / `implementation-task-template.md` §7: code + tests
written (and passing where a runtime exists; execution status stated
honestly otherwise); lint/format clean; `pr-review-checklist.md` §C
satisfied; shortcuts logged in `technical-debt-register.md`; only
allowed files changed; handoff updated with the learning-loop section;
quality gate confirmed; **ChatGPT reviews and accepts the
implementation against this prompt before any next task starts.**

## PR requirements

- Draft PR from `claude/task-002-credential-storage` into
  `Shopify-connector`. Title: `Task 002: credential storage, masking,
  and redaction foundation`.
- Body must include: objective; base/head SHA; the gate-authorization
  references (AR-025 acceptance + gate-act merge commit); files
  changed; the three applied decisions (compute-blank rejected;
  `token_variant='offline_custom_app'`; scope snapshot on `store`);
  test list + execution status (run vs. written-only, stated
  honestly); manual-validation status; rollback notes; explicit
  confirmations (no API call, no UI, no XML, no webhook/controller/
  cron, no domain logic, no encryption claim, one `sudo()`, no
  `job.log` writes, no real token anywhere); risks; next step (ChatGPT
  review).
- Leave the PR as **draft**. Do not merge. Do not mark ready. Stop.

## Final response format

Return only: 1. Branch name. 2. Commit SHA(s). 3. PR URL/number.
4. Files changed. 5. Test execution status (run/not run + why).
6. Confirmation the three AR-025 decisions were applied exactly.
7. Confirmation only allowed files changed. 8. Confirmation of every
hard-rule (each stated explicitly). 9. Rollback summary. 10. Risks or
uncertainties. 11. Recommended next step (ChatGPT review; Task 003
remains blocked).

**END FINAL TASK PROMPT**
