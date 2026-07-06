# Task 003 — API Client Shell and Test Connection (PROPOSED)

> Written to the `CLAUDE.md` §9 implementation-task structure (see
> [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)),
> derived from the architecture package
> [`../03-architecture/credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md).

## Status

**Proposed only. Not authorized.** Task 003 may start only after: (1)
Task 002 is merged and ChatGPT-reviewed; (2) ChatGPT performs an explicit
gate-opening act that **for the first time authorizes outbound Shopify
Admin API calls** (read-only) — the AR-021 gate explicitly forbids
external API calls and test connection, so this is a conscious gate
widening, not a formality; (3) ChatGPT resolves the named decision points
(the `core_test_connection` job-type vocabulary extension; the
`SHOP_INACTIVE`/402/423 class mapping; the job-log system-append write
path — sanctioned elevation in the core log choke point vs. `job.log`
ACL widening; the per-run `payload_hash` nonce for target-less jobs,
which touches accepted AR-019 `idempotency_key` semantics); (4) a
separate final task prompt is issued.

**Acceptance note (2026-07-06, PR #92 acceptance patch;
[`AR-024`](../05-qa/architecture-review-log.md)):** this task plan is
**accepted by ChatGPT as the proposed follow-up plan — not authorized**.
Starting it still requires (1) Task 002 to be merged and reviewed first,
and (2) a separate, explicit API-client/test-connection
gate-opening act. The `core_test_connection` job-type value, the
job-log system-append write path, the per-run `payload_hash`
target-less-idempotency nonce, and the `SHOP_INACTIVE`/402/423/
403-fraudulent shop-state error-class mapping all remain decisions for
the separate final task prompt, not decided by this acceptance.

## Objective

Create the single GraphQL transport boundary
(`shopify.connector.api.client`, AbstractModel, read-only in this task)
and the test-connection service: one read-only query proving
reachability, identity, auth, API version, and granted scopes; results
written to the existing store mirror fields and recorded as a
`setup_readiness_check` job with redacted logs.

## Preconditions

- Task 002 merged (credential model + `_get_access_token` + redaction
  utility exist).
- The gate act above; the final task prompt fixes: the pinned API-version
  planning default (proposed `2026-07`, the latest stable on 2026-07-06),
  timeout constants (adjustable planning defaults), and the job-type
  resolution.
- The Task 001A runtime caveat applies as in Task 002.

## Allowed files

- `addons/shopify_connector_core/models/shopify_connector_api_client.py` (new)
- `addons/shopify_connector_core/models/shopify_connector_store.py`
  (test-connection entry point method only, e.g.
  `action_test_connection()`; no field changes)
- `addons/shopify_connector_core/models/shopify_connector_job.py`
  (**only if** ChatGPT accepts the `core_test_connection` `job_type`
  value — a one-line addition to the base `job_type` selection list;
  `selection_add` remains the domain-module mechanism and is not what
  this is — and/or the per-run `payload_hash` nonce resolution requires
  a documented compute note; if both are rejected, this file is
  untouched and `core_readiness_check` is reused)
- `addons/shopify_connector_core/models/__init__.py` (import line)
- `addons/shopify_connector_core/__manifest__.py` (version bump only)
- `addons/shopify_connector_core/tests/test_api_client.py`,
  `addons/shopify_connector_core/tests/test_test_connection.py` (new)
- `docs/01-research/research-handoff.md` (mandatory handoff update)

## Forbidden files

Everything else. Explicitly: any view/menu/action/wizard XML; any
controller/webhook/cron/data file; the credential model file (read-only
consumer — no changes); security files — no ACL/group changes (**unless**
ChatGPT's job-log write-path resolution explicitly chooses ACL widening
over the recommended system-append elevation, in which case the final
task prompt must move `security/ir.model.access.csv` into Allowed files
by name); job_log/location/binding/settings models; `adams_base`; domain
modules; CI; docs other than the handoff; migrations.

## API client contract

Per the architecture package §API client boundary (authoritative). In
brief: `execute(store, query, variables=None)` POSTs to
`https://{store.shop_domain}/admin/api/{store.api_version}/graphql.json`
with `Content-Type: application/json` and `X-Shopify-Access-Token`
(officially confirmed header); token obtained only via
`_get_access_token` inside the client; bounded timeouts; returns parsed
`data` plus structured throttle metadata
(`extensions.cost.throttleStatus.maximumAvailable/currentlyAvailable/
restoreRate` — verbatim official field names; never hard-coded bucket
sizes); compares `X-Shopify-API-Version` response header to
`store.api_version` and flags fall-forward; **no retry loops** (DEC-009
retry policy belongs to the job layer); **no mutation API surface exists
in this task** — the shell exposes no method that can send a GraphQL
mutation; transport isolated in one overridable private method (e.g.
`_send()`) as the test-injection seam.

## Test connection contract

Per the architecture package §Test connection contract (authoritative).
In brief: Admin-invoked service; preconditions `shop_domain` +
`credential_present` + `api_version`; single read-only query

```graphql
query ConnectorTestConnection {
  shop { id name myshopifyDomain }
  currentAppInstallation { accessScopes { handle } }
}
```

(all fields confirmed in the 2026-07 official reference); on success:
`last_test_connection_result='pass'` + timestamp + reason,
`credential_last_verified_at`, `granted_scopes` +
`granted_scopes_checked_at` snapshot, identity check
(`shop.myshopifyDomain` vs `store.shop_domain`), fall-forward warning if
the version header mismatches; on failure: `'fail'` + plain-language
reason (redacted), `credential_state='invalid'` where the signal is
auth-shaped; every run recorded as one `job_source='setup_readiness_check'`
job with attempt/result `job.log` rows (written through the core
system-append log choke point per ChatGPT's write-path resolution;
repeat runs rely on the per-run `payload_hash` nonce resolution so the
second run's job does not collide with the `(store_id, idempotency_key)`
unique constraint); single attempt, no auto-retry (interactive check;
operator re-runs).

## Read-only guarantee

- The Shopify side of this task is **structurally read-only**: the client
  shell has no mutation method; the test-connection query contains no
  mutation; no webhook registration, no business object creation, no
  domain write, no Odoo business-record write. Odoo-side writes are
  limited to: the store mirror fields named above, `credential_state`,
  `api_health_state/_reason` where applicable, and job/job.log rows.
- A test must assert no code path in this task can emit a request body
  containing `mutation`.

## Error normalization

Dual-path (HTTP status **and** 200-OK `errors[].extensions.code`) into
the fixed 16-class registry — no 17th class:

- DNS/TLS/timeout/5xx/`INTERNAL_SERVER_ERROR` →
  `shopify_temporary_server_network` (include `extensions.requestId` in
  redacted technical detail when present).
- 401 (if observed) / `ACCESS_DENIED` → `shopify_permission_scope_auth`.
- 429 (if observed) / `THROTTLED` → `shopify_throttling_rate_limit`.
- 402/423/403-fraudulent/`SHOP_INACTIVE` →
  `shopify_permission_scope_auth` **(pending ChatGPT confirmation of this
  mapping)** with distinct plain-language reasons.
- Identity mismatch → `odoo_validation_configuration`.
- Unparseable/unexpected (incl. `MAX_COST_EXCEEDED` on this query) →
  `unknown_system_error`.

Officially-undocumented shapes (THROTTLED body; invalid-token HTTP
status; missing-scope error shape; `shop`/`currentAppInstallation` scope
requirements) are handled defensively, encoded as **configurable test
fixtures labelled unofficial**, and carry an **empirical verification
step** in the acceptance criteria — they must never be asserted as
official behavior in code comments or docs.

## Redaction guarantee

Every exception, log line, `job.log` field (`message`,
`technical_detail`, `payload_snapshot`), and store mirror written by this
task passes through the Task 002 `redact()` utility; the job-log sink
choke point is wired in this task (defensive redaction at write time);
request headers are never logged; the token never appears in any output —
proven by tests using dummy `shpat_…` values.

## Tests required

1. **Transport fixtures** via the injection seam: success;
   `ACCESS_DENIED`; `THROTTLED` (fixture labelled unofficial);
   `MAX_COST_EXCEEDED` (official sample shape); `INTERNAL_SERVER_ERROR`
   + `requestId`; HTTP 401/402/423/429/500; timeout; malformed JSON;
   version fall-forward — each asserting the mapped error class and the
   plain-language reason.
2. **Redaction:** a fixture whose body/headers embed a dummy token —
   assert the token is absent from the raised exception's str/args, all
   job.log fields, and every store mirror.
3. **Test connection behavior:** pass path writes all mirrors + snapshot
   + job/log rows; identity-mismatch path; the missing-credential
   precondition fails cleanly without an HTTP call (`shop_domain` and
   `api_version` are `required=True` on the merged store model, so those
   preconditions are satisfied by construction — the service's defensive
   guards for them are exercised only as unit-level checks, not as
   constructible record states); auth-failure path sets
   `credential_state='invalid'`.
4. **Read-only guarantee:** no emittable request body contains
   `mutation`; no Odoo business model is written.
5. **Job accounting:** exactly one job per run; `job_source =
   'setup_readiness_check'`; the accepted job-type value per ChatGPT's
   resolution; job reaches a terminal state; **a second run on the same
   store succeeds** (per-run key resolution proven — no
   `store_idempotency_key_uniq` collision).

Runtime-availability fallback per Task 001A precedent (write +
syntax-validate + manual checklist if no runtime exists; no invented
harness).

## Manual validation

On a live Odoo 19 instance **with a development store** (never a
production shop):

1. Set a dummy-invalid token → test connection fails with the auth class,
   business-friendly copy, no token in any log (grep for the dummy).
2. Set a valid development-store token → pass; mirrors + scope snapshot
   populated; job/log rows present and redacted.
3. Record the **empirical answers** to the open questions: actual HTTP
   status for an invalid token; actual THROTTLED body shape if
   reproducible; whether `shop`/`currentAppInstallation` needed any
   scope; actual missing-scope error shape. File them into the research
   notes as a follow-up doc task.
4. Confirm read-only: no product/customer/order/inventory/fulfillment
   record changed on either side; no webhook appeared in the store.

## Rollback

Revert the Task 003 PR. Task 002's model/utility are untouched; the store
mirror fields simply stop being refreshed (harmless stale data). No
migration; no data cleanup; no Shopify-side artifacts exist to clean up
(read-only guarantee).

## Acceptance criteria

- Only allowed files changed; module upgrades cleanly.
- Client shell + test connection exist per the contracts above; read-only
  guarantee holds structurally and by test.
- Dual-path normalization proven by the fixture matrix; no invented
  official claims (unofficial fixtures labelled).
- Token provably absent from every output (tests + manual grep).
- Empirical verification of the named open behaviors performed and
  recorded (or explicitly reported as not reproducible).
- No pacing policy implemented (MBQ-51 untouched); throttle signal merely
  surfaced.
- [`../05-qa/credential-security-redaction-review-checklist.md`](../05-qa/credential-security-redaction-review-checklist.md)
  gates all pass; handoff updated; rollback notes in the PR.

## Definition of done

Per `CLAUDE.md` §9 / template §7: code + tests written (and passing where
a runtime exists), lint/format clean; `pr-review-checklist.md` §C
satisfied; debt logged; only allowed files changed; handoff updated;
quality gate confirmed; **ChatGPT reviews and accepts before any next
task starts.**

## Explicit exclusions

- **No domain sync** (no product/customer/order/inventory/fulfillment
  logic or calls).
- **No setup wizard UI** (no views/menus/actions/wizard of any kind).
- **No webhooks** (no registration, no receiver, no HMAC code).
- **No dashboard** (no UI surfaces at all).
- **No cron scheduling** — nothing in this task runs unattended; a
  scheduled health probe would be a separate, explicitly scoped and
  justified future task.
- **No mutations, no Bulk Operations, no REST, no pacing policy.**
