# V2 Data and API Contracts

> **Status:** implementation contract. Logical names, state vocabularies, security boundaries and response shapes are locked. Physical changes are additive until the contraction stage.

## 1. Contract rules

- `contract_version` is an integer and starts at `1`.
- A breaking response change creates a new method suffix (`_v2`), not an in-place shape change.
- Additive optional fields are allowed within a version; clients ignore unknown fields.
- Every composed read carries a UTC `generated_at`, a truthful `data_through`, `store_generation` and `correlation_id`.
- Every write carries a caller-generated UUID `command_id` and `expected_generation`.
- Decimal/money values are strings; timestamps are ISO 8601 UTC; Shopify identities are canonical GIDs.
- Browser payloads never contain credentials, authorization headers, raw webhook bodies, unrestricted exception text or unredacted PII snapshots.
- `allowed_actions` is authoritative for presentation but never replaces server authorization on submit.

## 2. Persistent model contract

### 2.1 Models preserved unchanged in identity

The following current models remain compatibility APIs:

| Model | Identity/invariant retained |
| --- | --- |
| `shopify.connector.store` | canonical shop domain, company, lifecycle, connection generation |
| `shopify.connector.store.credential` | guarded credential metadata/storage boundary |
| `shopify.connector.store.settings` | store-scoped workflow configuration |
| `shopify.connector.location` | Shopify Location observation/cache |
| `shopify.connector.job` | logical work item, accepted state/error taxonomy, idempotency and operation scope |
| `shopify.connector.job.log` | append-only event evidence |
| `shopify.connector.mutation.attempt` | one mutation intent per job and uncertainty/readback evidence |
| `shopify.connector.webhook.delivery` | payload-free deduplicated delivery envelope |
| every current concrete binding model | per-store Shopify/Odoo identity and uniqueness |
| current match/review/evidence models | audit and recovery history |

No migration changes their `_name`, `_table` or existing XML IDs. Existing record IDs remain stable.

#### Store cardinality, isolation and settings ownership

- One canonical Shopify shop domain maps to one connector store identity; reconnecting never creates a second identity for the same shop.
- One Odoo company may own multiple Shopify stores and a database may contain
  stores for multiple permitted companies. The initial V2 supported capacity
  remains the V1 fail-closed limit of ten stores per database. This is a
  measured support boundary, not a licensing rule: it may be raised or removed
  only after the 20-store profile passes the exact-candidate isolation,
  backlog, latency and query budgets.
- Every credential, settings row, mapping, binding, checkpoint, run, job and rollout flag is store-scoped even when two stores share a company.
- Store children must match both `store_id` and the store-derived `company_id`; same company is not permission to cross store boundaries.
- A store has one effective `shopify.connector.store.settings` record. Historic configuration is represented by the connection/configuration generation and audit evidence, not competing active settings rows.
- Canonical domain and company are editable only while the store is an evidence-free draft. Once bindings/jobs/business evidence exist, changes require the explicit migration path; ordinary Settings cannot retarget the identity.

The logical Administrator settings contract is locked below. Existing physical V1 fields are adapted rather than duplicated; any missing physical field is added only in its owning domain addon.

| Group | Locked logical keys | New-draft default |
| --- | --- | --- |
| Workflows | `product_import`, `product_export`, `order_import`, `inventory_push`, `fulfillment_export` | all disabled until explicitly selected in setup |
| Trigger posture | per-workflow `manual`, `scheduled`, `webhook`, `odoo_event`, `reconciliation`; supported cadence | manual available only for enabled/ready operations; every automatic trigger disabled until its readiness/subscription check passes; reconciliation enabled on activation for every enabled sync domain |
| Product/price authority | first-sync direction, imported field allowlist, media refresh, price/pricelist authority, export field allowlist, attribute-conflict policy | no export authority; no fuzzy/name auto-binding; import preserves protected local fields |
| Orders/customers | financial-status/confirmation policy, manual gateway allowlist, import window, pending-payment handling, test-order inclusion, fallback partner | import creates no unsupported automatic confirmation; ambiguous customer/gateway state goes to review |
| Odoo defaults | company, warehouse, sales team, currency-compatible pricelist, payment term, fiscal position, tax/payment/shipping mappings | unset and readiness-blocking where required |
| Inventory | exact Shopify↔Odoo location mappings, authority, scheduled posture, first-push state | remote mutation disabled; first push unconfirmed |
| Fulfillment | direction, tracking posture and effective customer-notification policy | remote mutation disabled until selected and ready; notification must be explicit in every mutation command/evidence |
| Lifecycle | activation/pause/disconnect/retire plus per-workflow pause | draft; connection test is the only remote operation allowed before readiness |
| Advanced migration | `v2_ui_mode`, `v2_gateway_mode`, `v2_runtime_mode` | `legacy`; Administrator-only and removed after contraction |

The following are constants, not settings: Shopify API version/documents, retry and pagination hard ceilings, binding/idempotency/operation-scope algorithms, generation/tenant fences, mutation verification, raw credential visibility and security retention floors.

### 2.2 New `shopify.connector.run`

One record represents one user or system request that may create multiple jobs.

| Field | Type | Required | Contract |
| --- | --- | --- | --- |
| `name` | Char | yes | human ref generated as `RUN-YYYYMMDD-<sequence>`; not identity |
| `request_key` | Char, indexed | yes | immutable UUID/string command key |
| `store_id` | Many2one store, indexed, restrict | yes | scope root |
| `company_id` | related stored Many2one, indexed | yes | derived from store, readonly |
| `expected_connection_generation` | Integer | yes | captured at admission |
| `workflow` | Selection, indexed | yes | `core`, `product`, `product_export`, `sale`, `inventory`, `fulfillment`, `webhook` |
| `operation` | Char, indexed | yes | registered operation key |
| `trigger` | Selection, indexed | yes | `user`, `cron`, `webhook`, `odoo_event`, `reconciliation`, `system` |
| `actor_uid` | Many2one user, restrict | no | null only for a recorded system trigger; archive users instead of deleting audit identity |
| `requested_at` | Datetime, indexed | yes | UTC |
| `admitted_at` | Datetime | no | set after all admission gates |
| `finished_at` | Datetime, indexed | no | terminal time |
| `state` | Selection, indexed | yes | vocabulary below |
| `scope_summary` | Char | yes | redacted human scope |
| `scope_fingerprint` | Char, indexed | yes | SHA-256 over canonical scope |
| `configuration_snapshot` | Json | yes | allowlisted non-secret settings/generation evidence |
| `result_summary` | Text | no | redacted human result |
| `cancel_requested_at/by/reason` | Datetime/Many2one/Text | no | audited cancellation request |
| `correlation_id` | Char, indexed | yes | non-secret tracing ID |

Constraints/indexes:

- unique `(store_id, request_key)`;
- check generation ≥ 0;
- check terminal states require `finished_at`;
- global company/quarantine record rule equivalent to job;
- service-owned create/write; ordinary RPC cannot manufacture run records.

Run state vocabulary:

`requested`, `admitted`, `running`, `waiting`, `succeeded`, `partially_succeeded`, `failed_retryable`, `blocked_manual_review`, `failed_terminal`, `cancelled`.

Projection rules:

- `requested`: no child is admitted yet;
- `running`: any child is running and none has a higher safety state;
- `waiting`: all incomplete children wait for schedule/throttle/dependency/verification;
- `blocked_manual_review`: any unresolved child requires human action;
- `failed_retryable`: retry-eligible and no child is running;
- `failed_terminal`: at least one terminal failure makes the requested outcome impossible;
- `partially_succeeded`: terminal run with mixed succeeded/skipped/noncritical failure explicitly allowed by operation policy;
- `succeeded`: all required outcomes succeeded or were policy-approved no-ops;
- `cancelled`: cancellation completed before any unresolved remote uncertainty.

### 2.3 Additions to `shopify.connector.job`

| Field | Type | Default | Purpose |
| --- | --- | --- | --- |
| `run_id` | Many2one run, indexed, set null | null for legacy | groups jobs under request |
| `parent_job_id` | Many2one job, indexed, restrict | null | explicit dependency lineage |
| `sequence` | Integer | 10 | order in run |
| `lane` | Selection, indexed | derived from handler | priority class |
| `lane_priority` | Integer, indexed | 100 | lower value first within lane |
| `available_at` | Datetime, indexed | enqueue time | claim eligibility |
| `blocked_by_job_id` | Many2one job, indexed, set null | null | one explicit immediate dependency; complex fan-in stays coordinator-owned |

Existing fields and constraints remain. New job creation requires `run_id` after runtime cutover; legacy rows stay valid. A same-store constraint applies to run/parent/dependency references.

### 2.4 New `shopify.connector.job.attempt`

| Field | Type | Required | Contract |
| --- | --- | --- | --- |
| `job_id` | Many2one job, indexed, restrict | yes | owner |
| `store_id`, `company_id` | related stored, indexed | yes | fail-closed scope |
| `attempt_no` | Integer | yes | starts at 1 per job |
| `claim_token` | Char, indexed | yes | immutable UUID |
| `worker_ref` | Char, indexed | yes | redacted process identity |
| `claimed_at`, `started_at`, `heartbeat_at`, `finished_at` | Datetime | as applicable | UTC lifecycle |
| `outcome` | Selection, indexed | yes | vocabulary below |
| `error_class` | existing selection | no | normalized class |
| `error_code` | Char, indexed | no | stable machine code |
| `safe_message` | Text | no | operator-safe summary |
| `retry_decision` | Selection | no | `retry`, `verify`, `review`, `terminal`, `none` |
| `next_retry_at` | Datetime, indexed | no | scheduling evidence |
| `shopify_request_id` | Char, indexed | no | redacted support ID |
| `requested_cost`, `actual_cost`, `budget_available`, `throttle_delay_ms` | Float/Integer | no | API-cost evidence |
| `request_digest`, `response_digest` | Char | no | SHA-256; not payload |
| `mutation_attempt_id` | Many2one existing mutation attempt | no | remote-write intent |
| `observations` | Json | no | allowlisted bounded metadata |

Attempt outcomes: `claimed`, `running`, `succeeded`, `retry_scheduled`, `verification_required`, `manual_review`, `failed_terminal`, `cancelled`, `owner_lost`.

Constraints/indexes:

- unique `(job_id, attempt_no)` and `(job_id, claim_token)`;
- check attempt number > 0 and cost/delay fields ≥ 0;
- terminal outcome requires `finished_at`;
- same-store constraint for mutation evidence;
- append-only after terminalization except retention masking fields through a sanctioned service.

### 2.5 No generic attention table in initial V2

`item_ref` has the server-minted format `attn:<provider_key>:<source_id>:<state_version>` and is opaque to the browser. The normalized attention DTO is a query projection over existing jobs, mutation attempts, match decisions, mappings and readiness evidence. On every read/write, the server resolves the allowlisted provider, parses positive integer IDs/version, applies record rules, reloads the source and compares the current state version. The reference is not an authorization token and need not be secret. Arbitrary client-supplied model names are rejected.

## 3. Existing uniqueness contracts that must survive

| Domain | Required uniqueness |
| --- | --- |
| Jobs | `(store_id, idempotency_key)`; conflicting nonterminal operation scope; one reconciliation owner per mutation attempt |
| Webhooks | `(store_id, delivery_id)` |
| Product templates | `(store_id, shopify_gid)` and `(store_id, product_template_id)` |
| Product variants | `(store_id, shopify_gid)`, `(store_id, product_variant_id)`, `(store_id, shopify_inventory_item_gid)` |
| Orders | `(store_id, shopify_gid)` and `(store_id, sale_order_id)` |
| Locations | `(store_id, shopify_gid)` and `(store_id, odoo_location_id)` |
| Inventory levels | `(store_id, inventory_item_gid, location_mapping_id)` and `(store_id, variant_binding_id, location_mapping_id)` |
| Fulfillments | `(store_id, shopify_gid)` and `(store_id, picking_id)` |
| Mutation evidence | one mutation attempt per job; unique attempt token within job |

Customer-binding current constraints are preserved exactly even where PII retention masks snapshots. No new matching rule replaces binding identity.

## 4. State vocabularies

### 4.1 Store projection

Keep independent dimensions:

| Dimension | Values |
| --- | --- |
| Connection | `unconfigured`, `testing`, `connected`, `invalid`, `disconnected` |
| Configuration | `incomplete`, `valid`, `stale` |
| Activation | `draft`, `active`, `paused`, `retired` |
| Runtime health | `healthy`, `attention_required`, `degraded`, `blocked`, `unknown` |
| Workflow readiness | `disabled`, `not_ready`, `ready`, `paused` |

The projection maps current physical fields into these values; it does not collapse the source fields into one new column.

### 4.2 Existing job states

Preserve physical values:

`draft`, `queued`, `running`, `succeeded`, `failed_final`, `skipped`, `cancelled`, `retry_waiting`, `failed_retryable`, `blocked_manual_review`.

UI maps `failed_final` to `failed_terminal`; it never rewrites historical values.

### 4.3 Existing error taxonomy

Preserve all current machine codes including throttle/network, auth/scope, Shopify validation, Odoo configuration, missing mapping, ambiguity/binding/duplicate/idempotency/store-identity/destructive-write guards, inventory/fulfillment confirmation, total/schema/concurrency and unknown-system classes. New error codes may refine `error_code` but must map to one existing `error_class` until an ADR changes the taxonomy.

### 4.4 Mutation certainty

Preserve:

- observed outcome: `pending`, `succeeded`, `failed_clean`, `uncertain`;
- merchant write status: `queued`, `sending`, `accepted`, `verified`, `needs_attention`, `rejected`;
- resolution disposition: `applied`, `not_applied`;
- resolution source: `reconciliation_read`, `manual_admin`.

`accepted` is direct Shopify success evidence. Only independent readback can render `verified`.

## 5. Read DTOs

### 5.1 Common envelope

```json
{
  "contract_version": 1,
  "generated_at": "2026-08-30T13:20:00Z",
  "data_through": "2026-08-30T13:19:42Z",
  "store_generation": 18,
  "correlation_id": "sc_01J...",
  "data": {}
}
```

`data_through` is the oldest material observation used for the response, not simply response time.

### 5.2 Overview DTO

```json
{
  "store": {
    "id": 7,
    "name": "Northwind Shopify",
    "shop_domain": "northwind.myshopify.com",
    "company": {"id": 2, "name": "Northwind Trading"},
    "connection": "connected",
    "configuration": "valid",
    "activation": "active",
    "runtime_health": "attention_required"
  },
  "health": {
    "title": "One location blocks inventory publishing",
    "reason": "Warehouse East is not mapped.",
    "severity": "critical",
    "observed_at": "2026-08-30T13:08:00Z",
    "next_check_at": "2026-08-30T13:38:00Z",
    "score": 86,
    "allowed_actions": [{"key": "open_attention", "label": "Resolve mapping", "item_ref": "opaque"}]
  },
  "workflows": [{
    "key": "inventory",
    "label": "Inventory",
    "readiness": "not_ready",
    "health": "blocked",
    "freshness": {"observed_at": "2026-08-30T13:08:00Z", "label": "Observed 12 minutes ago"},
    "attention_count": 1,
    "latest_run_ref": "job:1842"
  }],
  "attention": {"total": 3, "items": []},
  "activity": {"window_days": 7, "succeeded": 318, "held": 3, "series": []},
  "permissions": {"can_start_operation": true, "can_configure": true}
}
```

Health score is presentation support, not an SLO. It is a deterministic weighted projection documented/tested in the query module; no business action depends on it.

### 5.3 Attention summary/detail DTO

Summary fields:

`item_ref`, `state_version`, `provider`, `workflow`, `severity`, `title`, `impact_summary`, `age_seconds`, `owner_role`, `store_id`, `run_ref`, `allowed_actions`.

Detail adds:

```json
{
  "what_happened": "A Shopify location has no approved Odoo mapping.",
  "impact": {"held_records": 142, "unit": "item-location pairs"},
  "evidence_groups": [{
    "key": "incoming",
    "label": "Incoming evidence",
    "rows": [{"label": "Shopify location", "value": "Warehouse East", "kind": "text"}]
  }],
  "allowed_actions": [{
    "key": "map_location_and_preview",
    "label": "Save mapping and preview",
    "required_role": "administrator",
    "requires_reason": false,
    "input_schema": {"odoo_location_id": {"type": "integer", "required": true}},
    "consequence": "The connector will generate a first-push preview; no Shopify quantity will change."
  }],
  "history": []
}
```

Severity is `critical`, `warning` or `info`; it is not copied from the low-level error class without provider logic.

### 5.4 Run DTO

```json
{
  "run_ref": "run:392",
  "display_name": "RUN-20260830-1842",
  "state": "waiting",
  "workflow": "fulfillment",
  "operation": "tracking_update",
  "store": {"id": 7, "name": "Northwind Shopify"},
  "trigger": {"type": "odoo_event", "label": "Picking validation", "actor": null},
  "scope": {"label": "WH/OUT/00491", "operation_scope_key": "fulfillment:picking:491"},
  "configuration_generation": 18,
  "result": {
    "title": "Remote outcome uncertain",
    "message": "The connector is reading Shopify before deciding whether another attempt is safe.",
    "safe_next_action": null
  },
  "jobs": [],
  "timeline": [{
    "event_id": 9918,
    "occurred_at": "2026-08-30T10:42:14.906Z",
    "kind": "response_interrupted",
    "tone": "warning",
    "title": "Response interrupted",
    "detail": "Result was not classified as failure.",
    "technical_detail_available": true
  }],
  "affected_records": [],
  "allowed_actions": []
}
```

Timeline is sorted by `occurred_at`, then stable event ID. Technical details require a separate authorized expansion and are redacted.

### 5.5 Setup DTO

Fields:

- `store` safe metadata;
- six `steps` with `state`, `completed_at`, `blocking_count` and next route;
- current step fields and server validation;
- `readiness_groups` with check key, label, status, evidence and remediation;
- `activation_preview` with workflows, authority, company/defaults, location count and side effects;
- `permissions` and `allowed_actions`.

Credential fields are limited to `present`, `last_replaced_at`, `last_verified_at`, `last_failure_reason` and scope posture.

### 5.6 Operation options DTO

The launcher first calls `get_operation_options_v1(store_id)` and receives registered operations only:

The current P15 DTO is intentionally narrow: `operation_key`, label, workflow,
mode (`read` or `reconciliation`), required role, the single available scope
`store`, an empty `filter_schema`, source-of-truth summary, side-effect
summary, readiness and disabled reason. The registered options are
Administrator-only and operate on one exact store. Preview, mutation and
free-form filter modes are not advertised until a separately reviewed command
contract exists.

The browser does not invent operation names or free-form domains.

### 5.7 Store administration DTOs

`get_store_list_v1(company_ids, state_filter, search, limit, cursor)` returns a bounded page of permitted stores with safe identity, company, connection/activation/runtime health, enabled workflows, freshness, attention count, setup continuation and `allowed_actions`. `All stores` is a read-only aggregate; every write still names exactly one store and company.

`get_store_settings_v1(store_id)` returns the grouped logical settings above, effective values, inherited/default source, field schema, readiness impact, last-change evidence and per-field/group `allowed_actions`. It returns credential presence/verification metadata only. Domain addons register their own typed settings fragments; unknown free-form keys are rejected.

`get_store_admin_summary_v1(store_id)` returns identity immutability reasons, connection generation, lifecycle state, installed capability posture, desired/actual webhook subscriptions, latest readiness result and the permitted pause/disconnect/retire actions. Counts are scoped through the same company/store rules as record lists.

## 6. Write commands

### 6.1 Common write shape

```json
{
  "contract_version": 1,
  "command_id": "8f0b4c91-....",
  "store_id": 7,
  "company_id": 2,
  "expected_generation": 18,
  "payload": {}
}
```

Success:

```json
{
  "status": "accepted",
  "message": "The operation was admitted.",
  "run_ref": "run:392",
  "attention_ref": null,
  "conflict_version": null
}
```

`status` is one of `accepted`, `completed`, `blocked`, `conflict`, `duplicate`.

### 6.2 `start_operation_v1`

Payload:

- `operation_key` from the server registry;
- no scope, filter, execution-mode, preview-fingerprint or free-form reason
  fields are accepted in this foundation slice. The operation is always
  admitted for the exact store named by the command envelope and only when
  the returned option is ready.

The supported keys are deliberately fewer than the long-term launcher shape:
the command accepts only `operation_key`, creates/adopts the named bounded
read/scan or reconciliation job, and returns a job-backed `run_ref`. It never
dispatches arbitrary model/method names or remote mutations.

Response returns the existing run on duplicate `command_id` or identical idempotency scope; it does not create a second request.

### 6.3 `resolve_attention_v1`

Payload:

- `item_ref`;
- `state_version`;
- exact `action_key` returned by detail DTO;
- allowlisted `inputs` matching that action schema;
- `reason` if required.

The handler reloads the source, recomputes allowed transitions and rejects stale/conflicting state. It records actor, reason, old/new state, command ID and linked run.

### 6.4 Setup writes

- `save_setup_step_v1`: requires the canonical durable `step_key`, accepts only
  fields owned by that semantic step and returns the refreshed setup DTO. A
  display ordinal is never an address. Legacy numeric progress is translated
  only by the one-way compatibility map before command validation.
- `replace_credential_v1`: accepts secret once over Odoo RPC; stores through the guarded credential service; returns no secret or prefix derived from it.
- `test_connection_v1`: creates auditable diagnostic work, reports served API version and scope posture.
- `activate_store_v1`: includes readiness snapshot fingerprint; server reruns mandatory checks and generation fence.

### 6.5 Job recovery writes

- `retry_job_v1(job_id, reason)`: only legal for returned retry action; re-admission occurs; uncertain mutation blocks and routes to verification.
- `cancel_job_v1(job_id, reason)`: cancellation request, not a claim that in-flight remote work was undone.
- manual mutation resolution remains Administrator-only and requires disposition, evidence/reason and acknowledged consequence.

### 6.6 Store administration and settings writes

- `create_store_v1`: Administrator-only; accepts name, canonical `.myshopify.com` domain and permitted company; rejects duplicate identity and returns a draft store plus setup route.
- `save_store_settings_group_v1`: accepts one registered group, its current revision/fingerprint and typed values; validates cross-field/domain readiness, increments the relevant configuration generation and returns refreshed settings/readiness.
- `set_workflow_state_v1`: enable, pause, resume or disable one registered workflow; enabling requires installed producer and readiness, while disabling blocks new admission without deleting history.
- `pause_store_v1` / `resume_store_v1`: audited admission controls; resume reruns mandatory readiness.
- `disconnect_store_v1`: blocks new admission, safely settles/verifies queued
  and in-flight work, reconciles connector-owned subscriptions, removes local
  credential usability, increments generation and preserves business/evidence
  records. A merchant-created Shopify custom-app token cannot be remotely
  revoked by this connector; the result DTO must state that external Shopify
  revocation remains an explicit Administrator follow-up instead of claiming
  end-to-end token revocation.
- `retire_store_v1`: prevents new work and hides the store from default daily views; it never hard-deletes bindings, runs or audit history.

No initial V2 command clones settings between stores. A future copy operation must have an explicit allowlist of non-secret defaults, name both source and destination, never copy mappings/bindings/checkpoints/credentials, and rerun destination readiness.

## 7. Problem/error DTO

All public RPC errors normalize to:

```json
{
  "code": "state_conflict",
  "title": "This item changed",
  "detail": "The location was updated after you opened this review.",
  "retryable": false,
  "field_errors": {},
  "attention_ref": "opaque",
  "run_ref": "run:392",
  "correlation_id": "sc_01J..."
}
```

Stable public codes:

`validation_error`, `access_denied`, `store_scope_mismatch`, `stale_generation`, `state_conflict`, `readiness_blocked`, `operation_conflict`, `duplicate_command`, `preview_stale`, `shopify_throttled`, `shopify_unavailable`, `shopify_auth_required`, `shopify_validation`, `verification_required`, `manual_review_required`, `terminal_failure`, `contract_version_unsupported`.

Raw exception class/message is not a public code. Unknown failures return `terminal_failure` plus correlation ID and create redacted internal evidence.

## 8. Idempotency contract

| Layer | Key | Behavior |
| --- | --- | --- |
| User/RPC command | `(store_id, command_id)` | return original result/run |
| Run request | `(store_id, request_key)` | unique durable intent |
| Job | current `(store_id, idempotency_key)` | one logical work item |
| Conflict serialization | current operation-scope uniqueness | one conflicting nonterminal mutation |
| Shopify-supported mutation | current Shopify idempotency key with validity window | reuse only within proven contract |
| Webhook | `(store_id, delivery_id)` plus digest/topic comparison | idempotent acknowledge or conflict review |
| Binding | per-store remote and Odoo uniqueness | idempotent upsert, never duplicate entity |

Canonical fingerprints use sorted, normalized JSON and SHA-256. They exclude timestamps, correlation IDs and display labels. They include store identity/generation, operation, authoritative IDs, requested business values and relevant preconditions.

## 9. Source-of-truth matrix

| Capability | Shopify authority | Odoo authority | Conflict behavior |
| --- | --- | --- | --- |
| Product identity | Shopify GID; existing binding | bound Odoo record | binding wins; conflict to review |
| Product matching | exact binding, then accepted deterministic remote keys | SKU/barcode/reference candidates | no name/fuzzy auto-bind; ambiguity to review |
| Imported title/status/vendor/type/tags/images | Shopify for enabled import fields | protected local fields remain local when policy says so | field-level authority shown; no silent overwrite |
| Product export | Shopify observed current value | explicitly enabled Odoo fields after preview | stale preview rejected; protected fields excluded |
| Customer identity | existing binding; accepted deterministic evidence | selected partner | ambiguity/manual override audited |
| Order commercial facts at import | Shopify order evidence | immutable/imported Odoo sale representation | total/composition mismatch blocks review |
| Odoo order operations | observation only unless explicit supported update | Odoo | connector does not silently rewrite operations from later Shopify edits |
| Inventory quantity | Shopify observed value before activation | Odoo after explicit mapping + first-push confirmation | drift/first push preview; no blind overwrite |
| Location identity | Shopify Location GID | explicit Odoo stock location selection | names advisory only; missing mapping blocks |
| Fulfillment intent/tracking | Shopify fulfillment-order eligibility/status observed | Odoo picking/tracking intent | uncertain mutation readback; no duplicate create |
| Customer notification | Shopify receives explicit mutation value | explicit Odoo/user setting for this action | never hidden/defaulted at send time |
| Connector configuration | Shopify scopes/capabilities observed | Odoo store settings and generation | missing scope blocks readiness |

Any new field crossing systems must be added to this matrix before implementation.

## 10. Shopify gateway operations

Each registered operation has a checked-in GraphQL document, variable schema, normalized result DTO, cost expectation, pagination rule and fixture set. Initial families:

| Gateway | Required use cases |
| --- | --- |
| Store/capability | shop identity, granted scopes, API-version/header verification |
| Locations | enumerate locations, resolve current state |
| Products | page products/variants, read one product/variant, compare update timestamps |
| Product mutations | create/update only through approved product-export handler; readback by canonical GID |
| Orders/customers | page by checkpoint/overlap, read canonical order/customer evidence |
| Inventory | read item/location levels, send bounded quantity changes, reread exact pair |
| Fulfillment | read fulfillment orders/fulfillments, create/update tracking, reread fulfillment result |
| Webhook subscriptions | list desired/current subscriptions, create/delete through reconciliation plan |

### 10.1 Future domain registration contract

Refunds and payouts are planned additive addons, not dormant V2 behavior:

| Future addon | Depends on | Must own before activation |
| --- | --- | --- |
| `shopify_connector_refund` | core, sale and the relevant stock/accounting integration | refund/return observations, authority and eligibility policy, financial/stock mutations, idempotency/readback, settings/readiness, attention/evidence, ACLs and end-to-end journeys |
| `shopify_connector_payout` | core, sale and Odoo accounting | payout/balance-transaction gateway, accounting mapping/reconciliation policy, immutable financial evidence, settings/readiness, attention/evidence, ACLs and end-to-end journeys |

Both register through the existing typed operation, handler, readiness, settings, attention and record-evidence interfaces. They may extend workflow selections through an additive migration. Neither may put arbitrary JSON business logic in core, reuse an unrelated job type, bypass accounting/stock controls or assume that Shopify delivery equals accounting finality.

Exact GraphQL fields remain governed by the pinned operation documents and contract fixtures. A schema/version bump is a dedicated checkpoint that revalidates every operation and served-version header behavior.

## 11. Retention and privacy contract

- Raw webhook payload: never persisted.
- Webhook delivery envelope: preserve current 30-day retention and bounded 2,000-row cleanup batches.
- Credentials/access tokens: preserve existing isolated lifecycle and disconnect/uninstall policy; V2 adds no readable field.
- PII snapshots: preserve the existing retention/masking service and per-binding declarations.
- Runs/jobs/attempts/logs/mutation evidence: preserve existing job evidence; new run/attempt records inherit the job retention decision and are not independently purged in V2.
- Request/response payloads: store digests and bounded allowlisted observations, not raw bodies by default.
- Manual reasons: redact email/phone/secret patterns and cap length before persistence.

A change to retention is a separate privacy/lifecycle decision with upgrade and audit consequences; implementation work may not invent a new default.

## 12. Contract test fixtures

Checked-in fixtures must cover:

- success, partial data and empty pagination;
- top-level GraphQL error and mutation `userErrors`;
- requested/actual cost and throttle status;
- missing/mismatched served API version;
- malformed/oversized JSON;
- duplicate/out-of-order webhook headers and identities;
- remote write success, clean rejection, timeout before send, timeout after send and readback applied/not-applied/inconclusive;
- each domain’s minimum/maximum optional field shapes;
- PII/redaction probes.

Fixtures contain synthetic identities and no copied merchant/customer data.
