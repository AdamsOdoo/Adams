# Task 003 — Final Implementation Prompt (gate-ready, not yet issued)

> **Acceptance (2026-07-07, applied by the AR-029 gate-opening act,
> [`task-003-api-client-test-connection-gate.md`](./task-003-api-client-test-connection-gate.md);
> [`AR-028`/`AR-029`](../05-qa/architecture-review-log.md)):** **Accepted
> by ChatGPT as the binding final Task 003 implementation prompt.** It
> remains **NOT ISSUED** until
> [`task-003-api-client-test-connection-gate.md`](./task-003-api-client-test-connection-gate.md)
> is merged into `Shopify-connector` — precondition (2) below (AR-028
> acceptance) is now satisfied; precondition (3) (the gate-opening act
> merged) is not yet satisfied while this document is in draft. The
> prompt content below is binding as accepted; any deviation requires a
> new ChatGPT decision.
>
> **Status: prepared 2026-07-07 via AR-028 — PROPOSED, NOT ACCEPTED, NOT
> ISSUED, NOT AUTHORIZED.** This document is the complete, copy-paste
> final `CLAUDE.md` §9 task prompt for **Task 003 — API Client Shell and
> Test Connection**. It applies the four decisions ChatGPT already
> accepted via **AR-027** (PR #98, with the F1 revision to Decision 4) to
> the contracts already fixed in
> [`task-003-api-client-test-connection-proposed.md`](./task-003-api-client-test-connection-proposed.md).
> It may be issued to Claude Code **only after all three of the following
> are true:**
>
> 1. **AR-027 accepted** — done (2026-07-07, PR #98, merge commit
>    `2e51cf02cd54527ff9dc817b6be1e1189f001a83`, now the tip of
>    `Shopify-connector`).
> 2. **AR-028 accepted** — ChatGPT accepts this document (as the binding
>    final Task 003 prompt) and the companion
>    [`task-003-gate-opening-proposal.md`](./task-003-gate-opening-proposal.md)
>    (as the proposed gate scope). **Not yet done** — this document and
>    its companion are proposed only, prepared on branch
>    `claude/task-003-gate-opening-no0tw4`.
> 3. **A separate, explicit Task 003 gate-opening act is merged into
>    `Shopify-connector`** — a further, later document (mirroring
>    [`task-002-credential-storage-gate.md`](./task-002-credential-storage-gate.md)
>    for AR-026), **not created by this document**. This is the **first**
>    authorization of any outbound Shopify Admin API call in this
>    project — a conscious widening of the AR-021 no-external-API rule,
>    not a formality.
>
> Until all three are true, executing anything below is a governance
> violation. The decisions baked in below (all accepted, AR-027, F1
> revision): `job_type` gains `core_test_connection`;
> `SHOP_INACTIVE`/HTTP 402/423/403-fraudulent map to
> `shopify_permission_scope_auth` with `credential_state`-gating and
> mandatory distinct plain-language reasons per condition; the job-log
> write path is a single internal `sudo()`-wrapped system-append method,
> no ACL widening; `payload_hash` gets a per-run UUID4 nonce for
> `core_test_connection` job creation **only** — `core_readiness_check`
> is untouched and remains tracked as
> [`TD-001`](../05-qa/technical-debt-register.md).
>
> Everything between the markers below is the prompt to issue verbatim,
> once authorized.

---

**BEGIN FINAL TASK PROMPT**

Execute **Task 003 — API Client Shell and Test Connection** for the Odoo
19 ↔ Shopify Connector.

Read first: `CLAUDE.md`; the latest entry of
`docs/01-research/research-handoff.md`;
`docs/07-implementation-plan/task-003-final-implementation-prompt.md`
(this prompt's committed copy);
`docs/07-implementation-plan/task-003-decision-closure.md`;
`docs/07-implementation-plan/task-003-api-client-test-connection-proposed.md`
(the authoritative contract for everything this prompt does not
override);
`docs/03-architecture/credential-connection-api-client-planning.md`;
`docs/05-qa/credential-security-redaction-review-checklist.md`;
`docs/05-qa/task-003-pre-implementation-review-checklist.md`;
`docs/05-qa/technical-debt-register.md` (`TD-001`);
`addons/shopify_connector_core/` (all existing files).

## Repo / branch

- **Repository:** AdamsOdoo/Adams
- **Base branch:** `Shopify-connector` (never `main`, never plain `dev`)
- **Working branch:** create `claude/task-003-api-client-test-connection`
  from latest `Shopify-connector`.
- **Expected baseline:** latest `Shopify-connector` **must contain** (1)
  PR #97's merge commit `7498ba181a01e571204e471d6880ea0c2068fd87` (Task
  002 implementation), (2) PR #98's merge commit
  `2e51cf02cd54527ff9dc817b6be1e1189f001a83` (AR-027 decision closure,
  accepted with the F1 revision), (3) the merged AR-028 acceptance (this
  prompt + the gate-opening proposal accepted), and (4) the merged Task
  003 gate-opening act (the separate document required by precondition 3
  above). Verify all four before writing anything. If any is missing,
  **stop and report** — do not proceed.

## Gate scope (what is authorized)

Exactly and only: the `shopify.connector.api.client` AbstractModel
(read-only in this task); the `action_test_connection()` entry point on
`shopify.connector.store`; the `core_test_connection` addition to
`job_type`; the job-log system-append method; the per-run
`payload_hash` UUID4 nonce for `core_test_connection` job creation only;
the tests below; a manifest version bump; the mandatory handoff update.
**Nothing else.** Every contract in
[`task-003-api-client-test-connection-proposed.md`](./task-003-api-client-test-connection-proposed.md)
not restated or amended below stands unchanged and is binding. The
AR-021 prohibitions on UI, webhooks, controllers, cron, setup wizard,
domain logic, mutations, Bulk Operations, and REST all remain fully in
force — this prompt authorizes exactly one conscious widening of AR-021:
outbound, read-only GraphQL calls for test connection only.

## Hard rules

- Do not touch `main` or plain `dev`.
- **Read-only only:** no GraphQL mutation string anywhere in the diff;
  the client shell exposes no method capable of sending a mutation; no
  Bulk Operations; no REST calls; no webhook registration.
- Zero UI: no views, menus, actions, wizards, TransientModels, or XML —
  this task adds **no XML file at all**.
- No controllers, no cron.
- No domain logic (product/customer/order/inventory/fulfillment).
- No `mail.thread` / chatter on any model.
- No new security group; no change to
  `security/shopify_connector_security.xml`.
- **No `security/ir.model.access.csv` change.** The job-log write path
  is the sanctioned system-append method (Decision 3), not an ACL
  widening; if this prompt is ever re-issued after a different ChatGPT
  choice, that choice must move this file into Allowed files by name —
  it is not authorized here.
- **`shopify_connector_store_credential.py` is read-only for this
  task:** no new method, no field change, no `sudo()` added to that
  file. Credential reads route only through the existing, unmodified
  `_get_access_token`. The only write this task makes to that model is
  a plain (non-`sudo()`) `write()` of `credential_state` from
  `action_test_connection()`'s own service code (see §3 below) — legal
  only because `action_test_connection()` is Admin-invoked and Admin
  already holds `perm_write=1` on the credential model from Task 002's
  ACL row; if a non-Admin caller somehow reaches this code path, the
  ORM raises `AccessError` from the existing ACL and the write never
  happens. No elevation is used or needed for this write.
- **Exactly two `sudo()` call sites exist in the entire diff after this
  task:** (1) the pre-existing Task 002 `_get_access_token` (untouched,
  a different file, not part of this diff), and (2) exactly one new
  call site inside the job-log system-append method (§4 below). Any
  other `sudo()` anywhere in the diff is a review failure.
- No raw SQL anywhere in the diff.
- No `ir.config_parameter` reads/writes.
- No pacing/backpressure policy (MBQ-51 stays untouched); the throttle
  signal (`extensions.cost.throttleStatus`) is surfaced as structured
  metadata only, never acted on automatically.
- No official-behavior claim for anything not empirically observed or
  already cited in the repo: THROTTLED body shape, invalid-token HTTP
  status, missing-scope error shape, and
  `shop`/`currentAppInstallation` scope requirements are all
  `[Requires external validation before implementation]` until the
  manual-validation step (§Manual validation) observes them; fixtures
  for these must be code-commented `# unofficial/unconfirmed shape`.
- No real Shopify shop, credential, or token value anywhere in code,
  tests, or docs: every token literal is a dummy
  (`shpat_DUMMYDUMMYDUMMY0000000000000000`); manual validation happens
  only against a development store, never a production shop.
- No migrations (none needed).
- Do not modify `shopify_connector_store_credential.py`,
  `shopify_connector_location.py`, `shopify_connector_binding_mixin.py`,
  `shopify_connector_store_settings.py`, `security/*`, `adams_base`, or
  DEC-003 through DEC-020 / `docs/04-decisions/README.md` /
  `docs/05-qa/defect-pattern-log.md`.
- **`core_readiness_check` is untouched by this diff** — no behavior
  change, no `payload_hash` nonce, no new call site creating such a job.
  Its identical latent idempotency-collision defect remains tracked as
  `TD-001`; fixing it is explicitly out of this task's scope.
- Do not start any other task. Stop after opening the draft PR.

## Allowed files (exhaustive)

- `addons/shopify_connector_core/models/shopify_connector_api_client.py` (new)
- `addons/shopify_connector_core/models/shopify_connector_store.py`
  (add `action_test_connection()` only; no field changes — every field
  it writes already exists)
- `addons/shopify_connector_core/models/shopify_connector_job.py`
  (one-line addition to the base `job_type` Selection —
  `('core_test_connection', 'Core Test Connection')` — plus a short
  docstring/comment note on `payload_hash` and/or
  `_compute_idempotency_key` explaining the dual use: real payload
  fingerprint for domain jobs vs. per-run nonce for target-less jobs;
  no other change to this file, and no change to
  `core_readiness_check`'s two existing values or any compute method's
  logic)
- `addons/shopify_connector_core/models/shopify_connector_job_log.py`
  (add the `_system_append` method only — see §4; no field change)
- `addons/shopify_connector_core/models/__init__.py` (one import line)
- `addons/shopify_connector_core/__manifest__.py` (version bump only:
  `19.0.1.1.0` → `19.0.1.2.0`)
- `addons/shopify_connector_core/tests/test_api_client.py` (new)
- `addons/shopify_connector_core/tests/test_test_connection.py` (new)
- `addons/shopify_connector_core/tests/test_job_log_system_append.py` (new)
- `docs/01-research/research-handoff.md` (mandatory handoff update)

## Forbidden files

Everything else. Explicitly: any view/menu/action/wizard/XML file; any
controller/webhook/cron/data file; `shopify_connector_store_credential.py`;
`security/ir.model.access.csv`; `security/shopify_connector_security.xml`;
`shopify_connector_location.py`; `shopify_connector_binding_mixin.py`;
`shopify_connector_store_settings.py`; anything under `addons/adams_base`;
any domain module; any CI/workflow/Dockerfile/requirements file; any
file under `docs/` other than the handoff; any migration directory.

## Implementation requirements (exact)

### 1. `job_type` addition (`shopify_connector_job.py`)

Add exactly one tuple to the existing base `job_type` Selection list:

```python
job_type = fields.Selection(
    selection=[
        ('core_readiness_check', 'Core Readiness Check'),
        ('core_manual_maintenance', 'Core Manual Maintenance'),
        ('core_test_connection', 'Core Test Connection'),
    ],
    required=True,
    index=True,
    readonly=True,
)
```

Add a short comment above `payload_hash` (or inside
`_compute_idempotency_key`'s docstring) stating: `payload_hash` serves
two purposes — a hash of the normalized outbound payload for
target-bearing domain jobs, and a per-run UUID4 nonce for target-less
job types (`core_test_connection` only, as of this task) so that repeat
runs do not collide under the `(store_id, idempotency_key)` unique
constraint. State explicitly that `core_readiness_check` shares the
identical target-less exposure but is **not** fixed by this task
(`TD-001`). No change to `_compute_idempotency_key`'s logic itself — it
already incorporates whatever value `payload_hash` holds.

### 2. API client `shopify.connector.api.client`

New `AbstractModel`, `models/shopify_connector_api_client.py`,
stateless, no table:

```python
_name = 'shopify.connector.api.client'
_description = 'Shopify Connector API Client'
```

- `execute(self, store, query, variables=None)` — the only public
  entry point. Preconditions (defensive; `shop_domain`/`api_version`
  are `required=True` on `store` so these are guards, not
  constructible failure states): raises `UserError` if `shop_domain` or
  `api_version` is falsy. Obtains the token via
  `self.env['shopify.connector.store.credential']._get_access_token(store)`
  (the existing, unmodified Task 002 accessor — its `sudo()` is
  untouched and is not one of this task's two sanctioned sites); raises
  a `ShopifyClientError` (`error_class='shopify_permission_scope_auth'`,
  `credential_invalid=True`) if it returns `False`/empty, without
  attempting a call. Builds the POST body
  `{"query": query, "variables": variables or {}}`; calls
  `self._send(store, body)`; normalizes the result (see below); returns
  a plain dict `{'data': <parsed data>, 'throttle_status': <dict or
  None>}`.
- `_send(self, store, body)` — the **only** method containing an actual
  HTTP call; the transport-injection seam tests override. Sends an
  HTTPS POST to
  `f'https://{store.shop_domain}/admin/api/{store.api_version}/graphql.json'`
  with headers `{'Content-Type': 'application/json',
  'X-Shopify-Access-Token': <token>}` and bounded timeouts —
  `_CONNECT_TIMEOUT_SECONDS = 10`, `_READ_TIMEOUT_SECONDS = 20` (module
  constants, adjustable planning defaults, not an official Shopify
  requirement). Returns the raw HTTP response object (status, headers,
  body) or raises a transport-level error (timeout, DNS, TLS,
  connection refused) that `execute()` normalizes. Never logs the
  request headers or body.
- **Dual-path error normalization** (inside `execute()`, after
  `_send()` returns, applied to both the transport layer and any 200-OK
  GraphQL `errors[]` payload) — the fixed 16-class registry, no 17th
  class, per
  [`task-003-api-client-test-connection-proposed.md`](./task-003-api-client-test-connection-proposed.md)
  §Error normalization, with the two AR-027 refinements below:

  | Observed signal | `error_class` | `credential_invalid` | Plain-language reason (example) |
  | --- | --- | --- | --- |
  | DNS/TLS/connect/timeout; HTTP 5xx; `INTERNAL_SERVER_ERROR` | `shopify_temporary_server_network` | `False` | "Shopify could not be reached right now — this is usually temporary." (`extensions.requestId` included in redacted technical detail when present) |
  | HTTP 401 (if observed) / `ACCESS_DENIED` | `shopify_permission_scope_auth` | **`True`** | "Your access token appears invalid or was revoked — replace it." |
  | HTTP 429 (if observed) / `THROTTLED` | `shopify_throttling_rate_limit` | `False` | "Shopify is asking us to slow down — try again shortly." (fixture labelled `# unofficial/unconfirmed shape` until empirically observed) |
  | HTTP 402 (frozen shop) | `shopify_permission_scope_auth` | **`False`** | "Shopify has frozen this store, most commonly for a billing/payment issue — resolve it in Shopify, then retry." |
  | HTTP 423 (locked shop) | `shopify_permission_scope_auth` | **`False`** | "This store has been locked by Shopify." |
  | HTTP 403 (fraudulent-store block) | `shopify_permission_scope_auth` | **`False`** | "Shopify has flagged this store as fraudulent." |
  | `SHOP_INACTIVE` | `shopify_permission_scope_auth` | **`False`** | "This store is inactive." |
  | Malformed/unparseable response; `MAX_COST_EXCEEDED` on this query; anything unclassifiable | `unknown_system_error` | `False` | Single safety-net path per DEC-009 |

  **Mandatory:** each of the five `shopify_permission_scope_auth` rows
  above carries its own distinct reason string — a single generic
  message reused across any two of them is a review failure.
  `credential_invalid` is a new boolean attribute on the raised
  exception (see below), **not** a new `error_class` value — it exists
  solely so `action_test_connection()` (§3) knows whether to flip
  `credential_state`, per Decision 2's gating rule: only a genuine
  token-invalid signal does so, never a shop-account-state condition.
  Identity mismatch (`shop.myshopifyDomain` ≠ `store.shop_domain`) and
  missing-scope detection are **not** client-level errors — they are
  interpreted by `action_test_connection()` from a successful `execute()`
  response (see §3), per the proposed doc's table.

- **Exception class** — `ShopifyClientError(Exception)`, one class (no
  subclasses needed for this task's scope), attributes: `error_class`
  (one of the fixed 16), `reason` (the plain-language safe message from
  the table), `technical_detail` (redacted; carries `extensions.requestId`
  when present, otherwise the redacted status/body excerpt), and
  `credential_invalid` (bool, default `False`). `str(exc)` returns
  `reason` only — never the technical detail, never any header, never
  the token.
- **Throttle metadata** — when present in the response, parse
  `extensions.cost.throttleStatus.{maximumAvailable,currentlyAvailable,restoreRate}`
  verbatim (official field names) into `throttle_status`; never
  hard-code bucket sizes; absent when the response carries no
  `extensions.cost` block.
- **Version fall-forward** — compare the `X-Shopify-API-Version`
  response header to `store.api_version`; on mismatch, `execute()`
  includes `{'version_fallforward': True, 'served_version': <header
  value>}` in its returned dict (does not raise); `action_test_connection()`
  turns this into a warning-only mirror write (§3), never a failure.
- **Redaction** — every `ShopifyClientError` constructor call and every
  log statement inside this file passes free text through
  `tools.redaction.redact()`; request headers are never logged; no
  `print`/DEBUG body dump exists un-redacted.
- **What this file must not contain:** any mutation-capable method; any
  retry loop (retry policy belongs to the job layer, DEC-009 — this
  client raises exactly once per call); any domain-sync method; any
  webhook/cron/REST code; any `sudo()` (the two sanctioned sites are
  elsewhere — `_get_access_token`, untouched, and the job-log
  system-append method, §4).

### 3. Test connection entry point (`shopify_connector_store.py`)

Add exactly one method, `action_test_connection(self)`, no field
changes to this file (every field it writes already exists on the
merged model). Per store record (`self.ensure_one()`):

1. **Precondition guard:** if `not self.credential_present`, raise
   `UserError` ("Enter a credential before testing the connection.") —
   no job is created, no HTTP call is attempted.
2. **Create the job:** `self.env['shopify.connector.job'].create({...})`
   with `store_id=self.id`, `job_source='setup_readiness_check'`,
   `job_type='core_test_connection'`, `state='running'`,
   `payload_hash=str(uuid.uuid4())` (the per-run nonce — `uuid` is
   Python's standard library `uuid` module; never derive this value
   from the token or any credential-derived value), `started_at=fields.Datetime.now()`.
   Append one `'attempt'` log row via the system-append method (§4):
   `message="Test connection attempt started."`.
3. **Call the client:**
   `result = self.env['shopify.connector.api.client'].execute(self, TEST_CONNECTION_QUERY)`
   where `TEST_CONNECTION_QUERY` is the exact query from
   [`task-003-api-client-test-connection-proposed.md`](./task-003-api-client-test-connection-proposed.md)
   §Test connection contract:

   ```graphql
   query ConnectorTestConnection {
     shop { id name myshopifyDomain }
     currentAppInstallation { accessScopes { handle } }
   }
   ```

4. **On `ShopifyClientError`:** write the store mirrors
   `last_test_connection_result='fail'`,
   `last_test_connection_at=fields.Datetime.now()`,
   `last_test_connection_reason=redact(exc.reason)`; if
   `exc.credential_invalid` is `True`, write `credential_state='invalid'`
   on the store's credential record via a **plain, non-`sudo()`**
   `search()` + `write()` on
   `self.env['shopify.connector.store.credential']` (legal only because
   this method is Admin-invoked and Admin already holds
   `perm_write=1`/`perm_read=1` from Task 002's ACL row — see Hard
   rules); if `exc.credential_invalid` is `False`, `credential_state` is
   left untouched. Set the job's `error_class = exc.error_class`,
   `state='failed_final'` (DEC-009: `shopify_permission_scope_auth` and
   every other class this task can raise carry "no automatic retry,
   manual fix then retry"), `finished_at=fields.Datetime.now()`. Append
   one `'attempt'` log row with `to_state='failed_final'`,
   `message=redact(exc.reason)`, `technical_detail=exc.technical_detail`
   (already redacted by the client).
5. **On success:** parse `result['data']['shop']` and
   `result['data']['currentAppInstallation']['accessScopes']`.
   - **Identity check:** if `shop.myshopifyDomain != self.shop_domain`,
     treat this as a **failure** with `error_class='odoo_validation_configuration'`
     and reason "The connected Shopify store does not match this
     store's configured domain — check the domain and reconnect."; do
     not touch `credential_state` (this is a configuration mismatch,
     not a credential problem); follow the same mirror/job/log writes
     as step 4 with this error class and reason instead.
   - **Pass:** write `last_test_connection_result='pass'`,
     `last_test_connection_at=fields.Datetime.now()`,
     `last_test_connection_reason=False`,
     `credential_last_verified_at=fields.Datetime.now()`,
     `granted_scopes=json.dumps([h['handle'] for h in
     accessScopes])`, `granted_scopes_checked_at=fields.Datetime.now()`.
     If `result.get('version_fallforward')`, additionally write
     `api_health_state='degraded'`,
     `api_health_reason=redact("Shopify served API version %s instead of the configured %s." % (result['served_version'], self.api_version))`
     — a warning, not a failure. Set the job's `state='succeeded'`,
     `finished_at=fields.Datetime.now()`. Append one `'attempt'` log row
     with `to_state='succeeded'`, `message="Connection verified with
     %s." % shop['name']` (redacted defensively even though this string
     is not expected to contain a secret).
6. Returns `None`. Never returns, logs, or embeds the token or any raw
   response body outside the redacted `technical_detail` field.

### 4. Job-log system-append method (`shopify_connector_job_log.py`)

Add exactly one classmethod, the single sanctioned write path for every
system-appended `job.log` row (Decision 3):

```python
@api.model
def _system_append(
    self, job, event_type, message,
    technical_detail=False, payload_snapshot=False,
    from_state=False, to_state=False,
):
    """The one sanctioned write path for system-appended job.log rows.

    No group holds `perm_create` on this model by design -- rows are
    system-appended, not user-authored (AR-019 §10). This is the only
    `sudo()` this file contains, mirroring the Task 002
    `_get_access_token` precedent: never registered as a user-facing
    action, invoked only from other core/domain service code that
    already holds an ACL-gated reference to `job` (all four roles hold
    `perm_read=1` on both `job` and `job.log` today, so this adds no
    new visibility -- only the ability to append the audit trail that
    ACL alone cannot). Every free-text argument is redacted before the
    row is created; `actor_uid` records the acting user, not the
    elevated context.
    """
    self.sudo().create({
        'job_id': job.id,
        'event_type': event_type,
        'from_state': from_state,
        'to_state': to_state,
        'message': redact(message),
        'technical_detail': redact(technical_detail) if technical_detail else technical_detail,
        'payload_snapshot': redact(payload_snapshot) if payload_snapshot else payload_snapshot,
        'actor_uid': self.env.uid,
    })
```

This is the **only** new `sudo()` call site in the diff. It is never
registered as a controller/action/button target — its only callers in
this task are inside `action_test_connection()` (§3). No
`security/ir.model.access.csv` change accompanies it (Decision 3).

### 5. Manifest

Version bump only: `'version': '19.0.1.2.0'`. No dependency, data, or
description change.

## Tests required (exact)

Odoo `TransactionCase` tests under
`addons/shopify_connector_core/tests/`. Every token literal is a dummy.
Reuse the four demo users created in Task 002's `setUpClass` pattern
where a test needs a non-admin identity.

**`test_api_client.py`** (transport-injection-seam fixtures — override
`_send()` to return canned responses, no network):

1. Success fixture (`shop` + `accessScopes`) → `execute()` returns the
   parsed data, no exception.
2. `ACCESS_DENIED` (200-OK GraphQL error) → `ShopifyClientError`,
   `error_class='shopify_permission_scope_auth'`, `credential_invalid=True`.
3. `THROTTLED` (fixture marked `# unofficial/unconfirmed shape`) →
   `shopify_throttling_rate_limit`, `credential_invalid=False`.
4. `MAX_COST_EXCEEDED` (official sample shape) → `unknown_system_error`.
5. `INTERNAL_SERVER_ERROR` with `extensions.requestId` → `shopify_temporary_server_network`;
   assert the `requestId` value appears in `technical_detail`.
6. HTTP 401 → `shopify_permission_scope_auth`, `credential_invalid=True`
   (fixture marked unconfirmed HTTP shape if 401 is not the officially
   documented invalid-token status).
7. HTTP 402 → `shopify_permission_scope_auth`, `credential_invalid=False`,
   reason mentions billing/payment.
8. HTTP 423 → `shopify_permission_scope_auth`, `credential_invalid=False`,
   reason mentions locked.
9. HTTP 403 (fraudulent-store shape) → `shopify_permission_scope_auth`,
   `credential_invalid=False`, reason mentions fraudulent.
10. `SHOP_INACTIVE` → `shopify_permission_scope_auth`,
    `credential_invalid=False`, reason mentions inactive.
11. HTTP 429 → `shopify_throttling_rate_limit`.
12. HTTP 500 → `shopify_temporary_server_network`.
13. Timeout (simulated) → `shopify_temporary_server_network`.
14. Malformed JSON body → `unknown_system_error`.
15. `X-Shopify-API-Version` header mismatch → `execute()` returns
    `version_fallforward=True` and `served_version`, no exception.
16. Assert the five `shopify_permission_scope_auth` reason strings
    (402/423/403/`SHOP_INACTIVE`/`ACCESS_DENIED`-or-401) are pairwise
    distinct — a shared/generic string across any two fails this test.
17. **Redaction:** a fixture whose body/headers embed a dummy
    `shpat_…` token → assert the token is absent from the raised
    exception's `str()`, `.reason`, and `.technical_detail`.
18. **Read-only guarantee:** assert no method on
    `shopify.connector.api.client` can construct a request body
    containing the substring `mutation` — either by source inspection
    of the module (no `mutation` literal anywhere) or by asserting the
    client exposes exactly the `execute`/`_send` surface with no other
    public method.
19. No credential value appears in any `ShopifyClientError` raised by
    any fixture above (leak sweep across `str(exc)`, `exc.reason`,
    `exc.technical_detail`).

**`test_test_connection.py`:**

20. Pass path (using an `execute()` test double / injected `_send()`
    success fixture): all named store mirrors written; `granted_scopes`
    is valid JSON containing the fixture's scope handles; job created
    with `job_type='core_test_connection'`, `job_source=
    'setup_readiness_check'`, reaches `state='succeeded'`; exactly two
    `job.log` rows exist for that job (attempt-started, attempt-succeeded).
21. Identity-mismatch path (`myshopifyDomain` differs from
    `shop_domain`): fails with `odoo_validation_configuration`;
    `credential_state` untouched.
22. Missing-credential precondition: `credential_present=False` → raises
    `UserError` before any `execute()` call; no job created (assert
    `_send` is never invoked — a call-count assertion on the injected
    seam).
23. Auth-failure path (`ACCESS_DENIED`/401 fixture): `credential_state`
    set to `'invalid'`; job `state='failed_final'`,
    `error_class='shopify_permission_scope_auth'`.
24. Shop-state-failure path (402/423/403/`SHOP_INACTIVE` fixture, each
    run separately): job fails with `shopify_permission_scope_auth`;
    `credential_state` is **not** changed from its pre-test value in
    any of the four cases.
25. Version fall-forward on an otherwise-passing run: `api_health_state='degraded'`
    and a redacted `api_health_reason` are written; `last_test_connection_result`
    is still `'pass'`.
26. **Idempotency — the collision guard:** two consecutive
    `action_test_connection()` calls on the same store (both passing,
    or one passing then one failing) both succeed in creating their job
    row — no `store_idempotency_key_uniq` violation — because each run's
    `payload_hash` is a distinct UUID4.
27. **No secret persisted:** after a run using a dummy token, the dummy
    string is absent from every persisted field on `store`, `job`, and
    `job.log` for that run (iterate `fields_get`/`read`).
28. **`core_readiness_check` untouched:** creating a
    `core_readiness_check` job through means available before this task
    (i.e., a bare `create()` with today's schema) still behaves exactly
    as it did before this task — specifically, a second such job for
    the same store with an empty `payload_hash` still collides on
    `store_idempotency_key_uniq` (this test **documents** `TD-001`
    rather than fixing it — it must fail/collide, proving this task did
    not silently alter `core_readiness_check`'s behavior).

**`test_job_log_system_append.py`:**

29. `_system_append` creates exactly one `job.log` row with the given
    `event_type`/`from_state`/`to_state`/`message` (redacted) for the
    given job.
30. A user with no `perm_create` on `job.log` (e.g. the operator demo
    user from Task 002) can still trigger a code path that calls
    `_system_append` indirectly (e.g. by calling
    `action_test_connection()` as that user, if ACL allows the
    triggering action) and the log row is created — proving the
    elevation, not a widened ACL, is what makes this work; a direct
    `self.env['shopify.connector.job.log'].create(...)` (bypassing
    `_system_append`) as that same non-admin user still raises
    `AccessError` — proving the ACL itself is unchanged.
31. **Source-level guard:** the diff's Python files contain exactly two
    `sudo(` occurrences total (the untouched pre-existing one in
    `shopify_connector_store_credential.py`, and the new one in
    `_system_append`) — assert via a source scan in a test, or document
    the grep in the PR body if a source-scan test is judged too
    brittle.
32. Redaction: a dummy token passed as `message`/`technical_detail`/
    `payload_snapshot` to `_system_append` is absent from the persisted
    `job.log` row.

**Applicability rule (Task 001A precedent, restated):** if the
repository still has no Odoo runtime at coding time, write the tests
anyway, `py_compile`-validate them, state plainly in the PR that they
were **not executed**, and make the manual validation below mandatory
review evidence. Do not invent a non-Odoo test harness. Do not install
Odoo/PostgreSQL/CI — infrastructure remains unauthorized.

## Manual validation (live Odoo 19 + PostgreSQL, with a development store — never a production shop)

1. Upgrade the module; `job_type` now offers three values in the UI-less
   ORM sense (`ir.model.fields.selection`); no XML/view exists anywhere
   referencing this task's additions.
2. Set a dummy-invalid token (Task 002's service) → run
   `action_test_connection()` → fails with the auth class, business
   -friendly copy, `credential_state='invalid'`; grep the database and
   server log for the dummy token: zero hits.
3. Set a valid development-store token → `action_test_connection()`
   passes; mirrors + scope snapshot populated; exactly the expected
   job/log rows exist.
4. Run `action_test_connection()` a second time on the same store →
   succeeds again (the idempotency guard proven live, not just in
   tests).
5. **Record the empirical answers** to the still-open behavioral
   questions and file them as a follow-up research note: actual HTTP
   status for an invalid token; actual `THROTTLED` body shape if
   reproducible; whether `shop`/`currentAppInstallation` needed any
   scope; actual missing-scope error shape. Never assert these as
   confirmed without having observed them.
6. Confirm read-only: no product/customer/order/inventory/fulfillment
   record changed on either side; no webhook appeared in the Shopify
   admin for the store.
7. Confirm no menu/action/view/wizard/controller/cron exists anywhere
   in the module referencing this task's work.

## Rollback

Revert the single Task 003 PR. Task 001/002's schema and credential
model are untouched; the store mirror fields and the `job_type` third
value simply stop being used (harmless — `core_test_connection` becomes
an unused enum value, not a dangling reference, since no other model
references it by name). No migration in either direction; no
Shopify-side artifact exists to clean up (structural read-only
guarantee — no mutation, no webhook was ever registered).

## Acceptance criteria

- Only allowed files changed; module installs/upgrades cleanly.
- Client shell + test connection exist exactly per §2–§4 above and per
  every unamended contract in
  `task-003-api-client-test-connection-proposed.md`; the four AR-027
  decisions applied exactly (job-type value; error-class mapping with
  `credential_state` gating and five distinct reasons; job-log
  system-append method; `payload_hash` nonce for `core_test_connection`
  only).
- Read-only guarantee holds structurally (no mutation-capable method)
  and by test (item 18).
- Dual-path error normalization proven by the fixture matrix (items
  1–16); unofficial/unconfirmed shapes labelled as such in code and
  tests, never asserted as official behavior.
- Token provably absent from every output (tests items 17, 19, 27, 32;
  manual grep item 2).
- Exactly two `sudo()` sites in the whole diff (test item 31).
- `core_readiness_check` provably unmodified in behavior (test item 28).
- Empirical verification of the named open behaviors performed and
  recorded during manual validation, or explicitly reported as not
  reproducible.
- No pacing policy implemented (MBQ-51 untouched); throttle signal
  merely surfaced.
- Every gate in
  [`../05-qa/task-003-pre-implementation-review-checklist.md`](../05-qa/task-003-pre-implementation-review-checklist.md)
  §B and
  [`../05-qa/credential-security-redaction-review-checklist.md`](../05-qa/credential-security-redaction-review-checklist.md)
  passes; handoff updated; rollback notes in the PR body.

## Definition of done

Per `CLAUDE.md` §9 / `implementation-task-template.md` §7: code + tests
written (and passing where a runtime exists; execution status stated
honestly otherwise); lint/format clean; `pr-review-checklist.md` §C
satisfied; shortcuts logged in `technical-debt-register.md` (in
addition to the pre-existing `TD-001`, which this task must not touch
except to confirm it remains open and unaffected); only allowed files
changed; handoff updated with the learning-loop section; quality gate
confirmed; **ChatGPT reviews and accepts the implementation against
this prompt before any next task starts.**

## PR requirements

- Draft PR from `claude/task-003-api-client-test-connection` into
  `Shopify-connector`. Title: `Task 003: API client shell and test
  connection`.
- Body must include: objective; base/head SHA; the gate-authorization
  references (AR-027 merge commit `2e51cf02cd54527ff9dc817b6be1e1189f001a83`;
  AR-028 acceptance; the separate Task 003 gate-opening act's merge
  commit); files changed; the four applied decisions; test list +
  execution status (run vs. written-only, stated honestly); manual
  -validation status including the empirically-observed answers; the
  five distinct `shopify_permission_scope_auth` reason strings quoted
  verbatim; rollback notes; explicit confirmations (no mutation, no UI,
  no XML, no webhook/controller/cron, no domain logic, no ACL change,
  exactly two `sudo()` sites, `core_readiness_check` unmodified, no real
  token anywhere); risks; next step (ChatGPT review).
- Leave the PR as **draft**. Do not merge. Do not mark ready. Stop.

## Final response format

Return only: 1. Branch name. 2. Commit SHA(s). 3. PR URL/number.
4. Files changed. 5. Test execution status (run/not run + why).
6. Confirmation the four AR-027 decisions were applied exactly.
7. Confirmation only allowed files changed. 8. Confirmation of every
hard rule (each stated explicitly, including the exactly-two-`sudo()`
count and `core_readiness_check` being unmodified). 9. The empirically
-observed answers to the previously-open behavioral questions (or
explicit non-reproducibility notes). 10. Rollback summary. 11. Risks or
uncertainties. 12. Recommended next step (ChatGPT review; no next task
starts).

**END FINAL TASK PROMPT**
