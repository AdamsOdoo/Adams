# Core Naming and Schema Planning — Proposed

> **Documentation-only implementation-planning pass** for the premium **Odoo
> 19 ↔ Shopify Connector**, prepared after ChatGPT accepted the
> [implementation gate readiness audit](../05-qa/implementation-gate-readiness-audit.md)
> (AR-018) on 2026-07-05, after PR #84 merged into `Shopify-connector` at
> merge commit `4bf692dceec4190705f522bc2d32851af4c79e37`. This is the
> "accepted next session" the audit named: a single naming/core-schema
> implementation-planning artifact for MBQ-01, MBQ-02, MBQ-04, MBQ-07,
> MBQ-16, MBQ-19, MBQ-20, MBQ-21, MBQ-44, MBQ-45's residual, and MBQ-62's
> residual. **Revised (2026-07-05) after ChatGPT's REVISE review of the
> original proposal** — see the "Revision note" immediately below the
> Status section. Companion documents:
> [`../03-architecture/master-blueprint-core-substrate.md`](../03-architecture/master-blueprint-core-substrate.md)
> (Part A, the blueprint this pass converts into exact names/schema),
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
> (the MBQ register these proposals target),
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-019**, this pass's own review-log entry).

## Status

- **Proposed for ChatGPT review.**
- **Documentation-only.**
- **Implementation-planning only.**
- **Does not open the implementation gate.**
- **Does not authorize implementation.**
- **Does not create implementation tasks.**
- **Does not create code.**
- **Implementation remains blocked.**

Every naming/schema proposal below becomes a **Decision** only if and when
ChatGPT accepts this document (mirroring the DEC-013 through DEC-020
acceptance pattern). Until then, every table and constant in this document is
a **Recommendation**, per `CLAUDE.md` §8 — nothing here is asserted as
already decided, and no row in `master-blueprint-open-questions.md` is
edited by this pass itself (that edit happens only via a future acceptance
patch, if and when ChatGPT accepts).

**Revision note (2026-07-05):** ChatGPT reviewed the original proposal and
returned **REVISE** — direction accepted, schema needed correction. This
revision: (1) removes `shopify.connector.store.credential` entirely — MBQ-04
is now a **full** slice-1 descope, not a partial resolution; (2) fixes the
`store.settings_id`/One2many-named-singular contradiction by removing the
reverse field; (3) changes `shopify.connector.job.log.job_id` from
`ondelete='cascade'` to `ondelete='restrict'`; (4) gives `job_type` two
core-owned values so the required Selection is never contradictorily empty
before any domain module installs; (5) makes the serialization guard
DB-backed and race-safe via a new `operation_scope_key` field + unique
constraint, kept distinct from `idempotency_key`; (6) removes the
`mail.thread`/tracking commitment, left to a future implementation task.
Six models are now proposed (down from seven). See §16 for what remains a
flagged judgment call versus what this revision corrects outright.

## 1. Purpose

The accepted [implementation gate readiness audit](../05-qa/implementation-gate-readiness-audit.md)
(AR-018, accepted 2026-07-05) found that even the narrowest possible first
implementation slice — a `shopify_connector_core` substrate skeleton with no
Shopify sync logic, no webhooks, and no external API calls — is blocked by
eleven open MBQ rows: MBQ-01, MBQ-02, MBQ-04, MBQ-07, MBQ-16, MBQ-19, MBQ-20,
MBQ-21, MBQ-44, MBQ-45 (residual), and MBQ-62 (residual). Every one of these
rows is either "Implementation planning"-owned (decidable inside a dedicated
naming/schema session rather than requiring a fresh ChatGPT policy round) or,
for MBQ-04 specifically, resolvable by an explicit, full descope rather than
a resolution. This document is that session.

It converts the **already-accepted** core-substrate blueprint
(`master-blueprint-core-substrate.md`, Part A, accepted via DEC-013) —
which deliberately named only proposed **directions**, never committed
Odoo identifiers (Part A's own "naming discipline" note) — into **exact**
proposed Odoo model names, field names/types, retry constants, access/group
identifiers, and `odoo_event` trigger-origin mechanics. It does not
re-litigate anything DEC-003 through DEC-020 already fixed at the
architecture/posture level; it only proposes the naming/schema layer those
decisions still require before a future first implementation task could be
written to the `CLAUDE.md` §9 / `implementation-task-template.md` template.

## 2. Scope

**In scope:**

- Core module (`shopify_connector_core`) internal naming/schema planning.
- Core store/config model names and fields.
- Feature-flag/settings model shape.
- Job/log/error model shape.
- Idempotency key schema.
- Serialization guard mechanism (DB-backed, race-safe).
- Retry constants.
- Access/group XML ID planning.
- `odoo_event` trigger-origin mechanics.
- Credential persistence posture for slice 1 only — **a full, explicit
  descope, not a resolution** (§11).

**Out of scope:**

- Code of any kind (Python, XML, manifest, CSV, tests, CI).
- Odoo module scaffolding of any kind.
- Manifest edits.
- Security CSV creation (row *shapes* are planned in §10; no CSV file is
  created).
- XML views.
- Any credential/secret-storage model, field, or lifecycle-metadata schema —
  fully descoped, not merely deferred (§11).
- Shopify API calls or transport-client design (MBQ-51/52's exact mechanics
  remain a later `core` milestone, not this slice).
- Product/customer/order/inventory/fulfillment domain models (MBQ-55 binding
  model names, MBQ-23–43/56–65 domain schema — all explicitly out of scope
  for a core-only pass).
- Webhooks (receiver/controller design; core's webhook-topic registration
  seam is architecture already accepted by DEC-013, not re-designed here).
- Opening the implementation gate.

## 3. Proposed core model names

Namespace convention: every model uses the `shopify.connector.<entity>`
technical-name prefix (dot-separated, matching the `shopify_connector_core`
module's own underscored name per common Odoo convention, e.g. `sale.order`
for module `sale`). Later domain modules (`shopify_connector_product`,
`_sale`, `_inventory`, `_fulfillment`) are expected to continue this
convention for their own concrete binding models (MBQ-55, out of scope here)
so the naming scheme stays consistent connector-wide without a later rename.

| Concept | Proposed Odoo model name | Abstract / Concrete | Owning addon | Rationale | Related MBQ |
| --- | --- | --- | --- | --- | --- |
| Store / connection | `shopify.connector.store` | Concrete | `shopify_connector_core` | The DEC-006 store-scoping anchor every other core model references; holds connection lifecycle, API version/health, and readiness metadata (Part A §B.1/§B.3) | MBQ-01, MBQ-02 |
| Core settings / feature flags | `shopify.connector.store.settings` | Concrete | `shopify_connector_core` | Kept as its **own** model, not folded onto `store`, so domain modules can cleanly extend it via classic Odoo `_inherit` (Part A §I.3's "domain modules extending core with their own flag fields") without adding fields to the busier store record | MBQ-01, MBQ-02, MBQ-07 |
| Shopify Location reference cache | `shopify.connector.location` | Concrete | `shopify_connector_core` | Minimal, system-maintained, Shopify-side-only reference (Part A §B.4); never stores Odoo-location IDs or mapping decisions | MBQ-01, MBQ-02 |
| Abstract binding contract | `shopify.connector.binding.mixin` | Abstract (`AbstractModel`, no table of its own) | `shopify_connector_core` | The DEC-013-accepted per-domain-concrete-on-core-contract shape (Part A §C.8); concrete domain binding models (MBQ-55, out of scope) will `_inherit` this mixin, not a stored core table | MBQ-01, MBQ-02 (MBQ-11 already resolved — DEC-013) |
| Sync job | `shopify.connector.job` | Concrete | `shopify_connector_core` | The job/log/error/retry substrate (Part A §D); one record per logical sync operation, carrying current state, error class, retry counters, the idempotency key, and the serialization-guard key (§8) | MBQ-01, MBQ-02, MBQ-19, MBQ-20, MBQ-21, MBQ-62 |
| Sync job log / event log | `shopify.connector.job.log` | Concrete | `shopify_connector_core` | A `job`+`log` **split** (see §6) — an append-only child record per attempt/state-transition/manual-action, so retrying a job never overwrites or loses its own history | MBQ-01, MBQ-02, MBQ-19 |
| Error / manual-review record | **Not a separate model** — fields on `shopify.connector.job` (`error_class`, `manual_review_subreason`) | — | — | A dedicated error/manual-review model would duplicate the job's own state machine (D.3/D.8 already model `blocked_manual_review` and its sub-reason as job-level concepts); folding these onto the job keeps the schema conservative and matches how the sync center/error center already read "the job's" state and class (Part A §G/§H) | MBQ-19 |
| Idempotency / operation guard | **Not a separate model** — fields + two uniqueness constraints on `shopify.connector.job` | — | — | Both the idempotency key and the serialization guard operate on the same job table; a separate guard model would just be a shadow index of it (see §8) | MBQ-20, MBQ-21 |
| Optional audit/evidence payload | **Not a separate model** — `payload_snapshot`/`technical_detail` fields on `shopify.connector.job.log` | — | — | Raw request/response bodies and technical detail are per-attempt evidence, which is exactly what a `job.log` row already represents; a fourth model would over-fragment for no query benefit at Phase-1 scale | MBQ-19 |

**Reading this table:** six models are proposed (`store`, `store.settings`,
`location`, `binding.mixin`, `job`, `job.log`). Three candidate "extra"
models named in the audit's own checklist (error/manual-review, idempotency/
operation guard, audit/evidence payload) are explicitly proposed **not** to
exist as separate models, each with its folding target stated. **No
credential model of any kind is proposed for this slice** — see §11. This is
deliberately conservative — see §13 for why this bound matters for later
migration safety.

## 4. Proposed field names and types

All models below include Odoo's automatic `create_date`/`create_uid`/
`write_date`/`write_uid` fields; these are not re-listed per row. `store_id`
is a required `Many2one → shopify.connector.store` on every model except
`store` itself, restated once per model rather than per field for brevity.

### 4.1 `shopify.connector.store`

| Field | Type | Required? | Index? | Unique constraint? | Readonly? | Purpose | Related MBQ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `name` | Char | Yes | No | No | No | Operator-facing display name for the connection | MBQ-01/02 |
| `shop_domain` | Char | Yes | Yes | Yes (per database) | Yes after first save | The `*.myshopify.com` store identity (Part A §B.1) | MBQ-01/02 |
| `state` | Selection (`setup_incomplete`/`connected`/`reconnect_needed`/`disconnected`) | Yes | Yes | No | Yes (system-written) | Connection lifecycle state (Part A §B.1) | MBQ-01/02 |
| `api_version` | Char | Yes | No | No | No | Pinned Shopify Admin GraphQL API version (MBQ-52 policy already accepted; exact upgrade mechanics remain open) | MBQ-01/02 |
| `api_health_state` | Selection (`normal`/`throttled`/`degraded`) | No | No | No | Yes | Honest, named API health indicator (Part A §B.3) | MBQ-01/02 |
| `api_health_reason` | Char | No | No | No | Yes | Plain-language health-state reason | MBQ-01/02 |
| `webhook_ready` | Boolean | No, default `False` | No | No | Yes | Webhook reachability readiness signal (feeds MBQ-06, already decided) | MBQ-01/02 |
| `last_test_connection_result` | Selection (`pass`/`fail`) | No | No | No | Yes | Last explicit test-connection outcome (Part A §E.2) | MBQ-01/02 |
| `last_test_connection_at` | Datetime | No | No | No | Yes | Timestamp of the last test-connection run | MBQ-01/02 |
| `last_test_connection_reason` | Char | No | No | No | Yes | Plain-language reason for pass/fail | MBQ-01/02 |
| `last_readiness_result` | Selection (`pass`/`fail`/`warning`) | No | No | No | Yes | Last `setup_readiness_check` job outcome summary | MBQ-01/02, MBQ-06 |
| `last_readiness_at` | Datetime | No | No | No | Yes | Timestamp of the last readiness-check job | MBQ-01/02 |

**Note:** no standard Odoo `active` field is proposed on `store`. Per MBQ-08
(disconnect must preserve, never hide, the store record), using `active` for
disconnect would risk the record silently disappearing from default-domain
views the moment `active=False` is set — `state = 'disconnected'` is the
correct mechanism, not archiving.

**No credential-related field of any kind is proposed on `store`** — see
§11 for the full MBQ-04 descope. **No settings reverse field is proposed
either** — `shopify.connector.store.settings.store_id` (§4.2) is the sole,
authoritative link between the two models; `store` does not carry a
`settings_id`/`settings_ids` field. A future implementation task may add a
convenience computed field if needed; none is committed here.

### 4.2 `shopify.connector.store.settings`

| Field | Type | Required? | Index? | Unique constraint? | Readonly? | Purpose | Related MBQ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `store_id` | Many2one → `store` | Yes | Yes | Yes (one settings record per store) | Yes after create | Store scoping (DEC-006); the sole link between `store` and `store.settings` | MBQ-01/02/07 |
| `product_domain_enabled` | Boolean | No, default `False` | No | No | No | Domain-enablement flag (Part A §I.1) | MBQ-07 |
| `sale_domain_enabled` | Boolean | No, default `False` | No | No | No | Domain-enablement flag (order + customer, folded per DEC-008) | MBQ-07 |
| `inventory_domain_enabled` | Boolean | No, default `False` | No | No | No | Domain-enablement flag | MBQ-07 |
| `fulfillment_domain_enabled` | Boolean | No, default `False` | No | No | No | Domain-enablement flag | MBQ-07 |
| `product_first_sync_source` | Selection (`shopify_source`/`odoo_source`/`both_match_first`) | No | No | No | No | Product first-sync source-of-truth (Part A §B.6, DEC-006) | MBQ-02/07 |
| `price_source_of_truth` | Selection (`odoo_authoritative`/`shopify_authoritative`) | No | No | No | No | Price source-of-truth (DEC-007 §3) | MBQ-02/07 |
| `notification_default_enabled` | Boolean | No, default `False` | No | No | No | Fulfillment customer-notification default, off unless explicitly enabled (Part A §B.7, DEC-007 §5, RA-009) | MBQ-02/07/41 (already decided) |

**Note:** per-domain **capability** flags (e.g. an inventory apply-mode flag,
a product image-sync toggle) are explicitly **not** named here — Part A
§I.2 routes those to each domain module, contributed to this same model via
`_inherit` when that domain's own naming/schema pass runs. **Field-level
change history for this model is left to implementation planning** — no
dependency on Odoo's `mail` module (`mail.thread`/`tracking=True`) is
committed by this pass. If a future implementation task adopts
`mail.thread`-based tracking for settings-change history, that task's own
manifest `depends` list must declare the `mail` dependency explicitly at
that time; this document neither commits to nor rules out that choice.

### 4.3 `shopify.connector.location`

| Field | Type | Required? | Index? | Unique constraint? | Readonly? | Purpose | Related MBQ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `store_id` | Many2one → `store` | Yes | Yes | Part of composite unique | No | Store scoping | MBQ-01/02 |
| `shopify_location_gid` | Char | Yes | Yes | Yes, with `store_id` (composite) | Yes after create | Shopify Location GID (Part A §B.4) | MBQ-01/02 |
| `name` | Char | Yes | No | No | Yes | Location display name, refreshed from Shopify | MBQ-01/02 |
| `shopify_location_active` | Boolean | No, default `True` | No | No | Yes | Whether Shopify itself reports this location active — **distinct from** Odoo's own `active` field (see note) | MBQ-01/02 |
| `last_synced_at` | Datetime | No | No | No | Yes | Last cache-refresh timestamp | MBQ-01/02, MBQ-43 (residual, out of scope) |

**Note:** no standard Odoo `active` field is proposed here either. A Location
that disappears from Shopify must surface as a review-worthy log entry (Part
A §B.4), not silently vanish from the cache's own default views — the
dedicated `shopify_location_active` field carries that signal without
triggering Odoo's default-domain hiding behavior.

### 4.4 `shopify.connector.binding.mixin` (abstract)

| Field | Type | Required? | Index? | Unique constraint? | Readonly? | Purpose | Related MBQ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `store_id` | Many2one → `store` | Yes | Yes | Part of composite unique (enforced per concrete model) | No | Store scoping (DEC-006 §C.2) | MBQ-01/02 |
| `shopify_gid` | Char | Yes | Yes | Part of composite unique (enforced per concrete model) | Yes after create | The generic Shopify GID identity field; domain-specific concrete models may add further identifier fields alongside it (e.g. inventory's `inventory_item_id`+`location_id`, out of scope here) | MBQ-01/02 |
| `status` | Selection (`active`/`stale`/`manually_overridden`/`review`) | Yes, default `active` | Yes | No | No (system + Reviewer action) | Binding status vocabulary (Part A §C.4) | MBQ-01/02 |
| `match_key` | Selection (`existing_binding`/`sku_reference`/`barcode`/`email`/`manual`) | No | No | No | Yes | Which match key produced this binding | MBQ-01/02 |
| `matched_by_uid` | Many2one → `res.users` | No | No | No | Yes | Who/what matched this binding | MBQ-01/02 |
| `matched_at` | Datetime | No | No | No | Yes | When the match occurred | MBQ-01/02 |
| `override_uid` | Many2one → `res.users` | No | No | No | Yes | Who performed a manual override, if any | MBQ-01/02 |
| `override_at` | Datetime | No | No | No | Yes | When the override occurred | MBQ-01/02 |
| `override_previous_candidate` | Char | No | No | No | Yes | What the automatic candidate was before the override (Part A §C.4 blueprint extension) | MBQ-01/02 |

**Note:** this mixin does **not** include a generic `res_model`/`res_id`
pair — each concrete per-domain binding model (product-template binding,
order binding, etc.; MBQ-55, out of scope) adds its own specific `Many2one`
to the Odoo business object it binds, per DEC-013's per-domain-concrete
shape. The core-level "binding target model/res_id concept" the audit's
field-category list calls for instead lives on `shopify.connector.job`
(§4.5) — a job needs to reference an arbitrary source record generically,
since `core` must never import a domain model (Part A §A.3), whereas a
concrete binding model already knows its own specific target type.

### 4.5 `shopify.connector.job`

| Field | Type | Required? | Index? | Unique constraint? | Readonly? | Purpose | Related MBQ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `store_id` | Many2one → `store` | Yes | Yes | Part of composite unique | Yes after create | Store scoping | MBQ-01/02 |
| `job_source` | Selection (`webhook`/`manual_sync`/`scheduled_sync`/`reconciliation`/`setup_readiness_check`/`export_preview_dry_run`/`odoo_event`) | Yes | Yes | No | Yes after create | The seven accepted job sources (DEC-009 + DEC-019) | MBQ-01/02, MBQ-62 |
| `trigger_origin` | Selection (`inventory_stock_change`/`fulfillment_picking_validation`, extensible via `selection_add`) | No, required only when `job_source = odoo_event` (see §7) | No | No | Yes after create | The `odoo_event` sub-classification (DEC-019) | MBQ-62 |
| `trigger_origin_event_ref` | Char | No | No | No | Yes | Identity of the originating Odoo event (e.g. a `stock.move`/`stock.picking` record reference), distinct from the job's own target (`res_model`/`res_id` below) | MBQ-62 |
| `trigger_origin_event_at` | Datetime | No | No | No | Yes | The Odoo-side event's own timestamp, distinct from enqueue time (DEC-019 audit requirement) | MBQ-62 |
| `job_type` | Selection, with two **core-owned** starting values — `core_readiness_check`, `core_manual_maintenance` — extensible via `selection_add` by domain modules | Yes | Yes | No | Yes after create | Domain-registered job-type/handler-routing value (Part A §A.5.2); also feeds the idempotency key's "operation type" component (§8) — no separate `operation_type` field is proposed. Core registers exactly these two values so the required field is never contradictorily empty before any domain module installs: `core_readiness_check` routes `setup_readiness_check`-sourced jobs to the readiness-check handler; `core_manual_maintenance` covers administrator-triggered internal maintenance (e.g. an orphaned-job sweep) that belongs to `core` itself, not any domain | MBQ-01/02, MBQ-19, MBQ-20 |
| `state` | Selection (`draft`/`queued`/`running`/`succeeded`/`failed_final`/`skipped`/`cancelled`/`retry_waiting`/`failed_retryable`/`blocked_manual_review`) | Yes, default `draft` | Yes | No | Yes (system + action methods) | The ten accepted job states (DEC-009) | MBQ-01/02/19 |
| `error_class` | Selection (16 fixed DEC-009 values) | No | Yes | No | Yes | Set only on failure/blocked states | MBQ-19 |
| `manual_review_subreason` | Selection (the six DEC-009 §D.5.4 confirmation-required classes) | No, required only when `state = blocked_manual_review` | No | No | Yes | Specific sub-reason, never generic (Part A §D.8) | MBQ-19 |
| `retry_count` | Integer | No, default `0` | No | No | Yes (system-incremented) | Retry attempts so far | MBQ-16, MBQ-19 |
| `next_retry_at` | Datetime | No | No | No | Yes | When the next automatic retry is eligible | MBQ-16 |
| `res_model` | Char | No | Yes | Part of composite unique | Yes after create | The source Odoo record's model (generic reference, core never imports domain models) | MBQ-19/20 |
| `res_id` | Integer | No | Yes | Part of composite unique | Yes after create | The source Odoo record's id | MBQ-19/20 |
| `shopify_target_gid` | Char | No | Yes | Part of composite unique | Yes after create | The Shopify target ID, where known, at dispatch time | MBQ-20 |
| `payload_hash` | Char | No | No | Part of composite unique | Yes after create | Hash/version of the payload driving this operation | MBQ-20 |
| `idempotency_key` | Char, computed + stored | Yes | Yes | Yes, with `store_id` (composite) | Yes | Composed from `store_id` + `job_type` + `res_model`/`res_id` + `shopify_target_gid` + `payload_hash` (§8). Persists for the life of the job; answers "is this the same operation, same target, same payload, already known?" — distinct from `operation_scope_key` below | MBQ-20 |
| `operation_scope_key` | Char, nullable | No | Yes | Yes, with `store_id` (composite; `NULL` values do not collide) | Yes (system-managed) | The **DB-backed serialization guard key** (§8). Computed from the coarser tuple `store_id` + `res_model` + `res_id` + `shopify_target_gid` — deliberately excluding `job_type`/`payload_hash` — so *any* concurrent operation against the same target is blocked, not only a retry of the identical operation. Populated while the job is non-terminal; set to `NULL` on reaching a terminal state or being superseded | MBQ-21 |
| `enqueue_decisions` | Text (serialized JSON) | No | No | No | Yes after create | Generic frozen-at-enqueue-time decision set (e.g. notification flag, source-of-truth in force) so retries never silently re-read a changed default (Part A §D.13) | MBQ-19 |
| `superseded_by_job_id` | Many2one → `shopify.connector.job` | No | No | No | Yes | Cancellation/supersede pointer (Part A §D.9) | MBQ-19 |
| `cancel_reason` | Char | No | No | No | Yes | Why a job was cancelled, and by what rule | MBQ-19 |
| `started_at` | Datetime | No | No | No | Yes | Execution start, for age/duration display | MBQ-19 |
| `finished_at` | Datetime | No | No | No | Yes | Terminal-state timestamp | MBQ-19 |

No `active` field is proposed on `job` — jobs are never archived; every
terminal state remains queryable for audit/dashboard history (§12, §13).

### 4.6 `shopify.connector.job.log`

| Field | Type | Required? | Index? | Unique constraint? | Readonly? | Purpose | Related MBQ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `job_id` | Many2one → `job`, `ondelete='restrict'` | Yes | Yes | No | Yes after create | Parent job (one2many from job). **Not** `ondelete='cascade'` — see §12 for why a log row must never be silently destroyed by a job-level deletion | MBQ-19 |
| `store_id` | Many2one → `store`, related to `job_id.store_id`, stored | Yes | Yes | No | Yes | Denormalized for store-scoped queries without a join | MBQ-01/02 |
| `event_type` | Selection (`attempt`/`state_change`/`verification_read`/`manual_action`/`note`) | Yes | Yes | No | Yes after create | What kind of event this row records | MBQ-19 |
| `from_state` / `to_state` | Selection (job state vocabulary) | No | No | No | Yes after create | Populated for `state_change` events | MBQ-19 |
| `message` | Text | Yes | No | No | Yes after create | Human-readable reason, the primary display (Part A §D.11) | MBQ-19 |
| `technical_detail` | Text | No | No | No | Yes after create | Raw error/response, secondary/expandable (Part A §D.12) | MBQ-19 |
| `payload_snapshot` | Text (serialized JSON) | No | No | No | Yes after create | Optional audit/evidence payload capture (folds the "optional payload model" into this row) | MBQ-19 |
| `actor_uid` | Many2one → `res.users` | No | No | No | Yes after create | Who performed a manual action (retry, confirm, override) | MBQ-19 |
| `occurred_at` | Datetime | Yes, default now | Yes | No | Yes after create | When this event actually happened | MBQ-19 |

## 5. Feature flag / settings schema

Resolving MBQ-07 at planning-proposal level:

- **Store-scoped settings record:** `shopify.connector.store.settings`
  (§4.2), one row per store (`store_id` unique), owned by `core`.
- **Domain extension seam:** domain modules add their own capability fields
  to this same model via classic Odoo `_inherit` (Part A §I.2/§A.5.4) —
  no per-domain settings model is introduced, matching DEC-013's accepted
  direction and avoiding the rejected per-domain-ad-hoc-settings alternative.
- **No feature flag may bypass safety guards:** structural rule restated
  from Part A §I.5, unchanged by this proposal — no field on this model, or
  any future domain-contributed field, may be read by a guard-bypass code
  path. This is an implementation-time code-review requirement, not itself
  a schema element.
- **Domain enablement vs. domain configuration distinction:** `..._enabled`
  Boolean fields (§4.2) gate whether a domain's jobs may be enqueued/executed
  at all (Part A §I.1); source-of-truth/notification-default fields are
  **configuration within an enabled domain**, not enablement switches
  themselves — a store can have `product_domain_enabled = True` with a
  `product_first_sync_source` still unset only during setup; the wizard
  (out of scope here, MBQ-03) is expected to require the latter before
  completing setup.
- **Settings live on a separate model, not the store model** — see §3's
  rationale (cleaner extension seam, keeps the store record smaller). The
  link is one-directional: `store.settings.store_id` → `store`; `store`
  carries no reverse field (§4.1).
- **Exact field names for Phase 1 flags** — proposed in §4.2:
  `product_domain_enabled`, `sale_domain_enabled`,
  `inventory_domain_enabled`, `fulfillment_domain_enabled`,
  `product_first_sync_source`, `price_source_of_truth`,
  `notification_default_enabled`.

## 6. Job/log/error schema

Resolving MBQ-19 at planning-proposal level:

- **Job and log are separate models.** `shopify.connector.job` holds the
  current, mutable state of one logical sync operation (state, error class,
  retry counters, idempotency key); `shopify.connector.job.log` is an
  append-only child table of per-attempt/per-event rows. This means a retry
  never overwrites the record of a prior attempt — the full history survives
  exactly the way Part A §D.10's audit requirements ("what was attempted;
  what was actually written... before/after values") demand.
- **Errors are fields on the job, not separate manual-review records.**
  `error_class` and `manual_review_subreason` live directly on `job`; the
  detailed technical error payload for *each* attempt lives on the
  corresponding `job.log` row (`technical_detail`), so a job that fails,
  retries, and fails differently the second time keeps both failures on
  record rather than overwriting the first.
- **Payload storage approach:** `job.log.payload_snapshot` (serialized JSON
  text), one snapshot per logged event, not a separate payload model (§3).
- **State transitions:** the ten accepted DEC-009 states are the `job.state`
  Selection; every transition is expected to write a corresponding
  `job.log` row with `event_type = state_change` and `from_state`/`to_state`
  populated, giving a full state-transition trail without a separate
  state-history model.
- **Retry-eligibility fields:** `retry_count` and `next_retry_at` on `job`
  (§4.5); which error classes are auto-retryable at all is **not** a schema
  field — it is fixed vocabulary (DEC-009 §D.5), looked up by `error_class`
  in code, not stored per job.
- **Manual-review handling fields:** `manual_review_subreason` on `job`;
  resolution is recorded as a `job.log` row with `event_type = manual_action`
  and `actor_uid` set — no separate "resolution" model.
- **Relation to dashboard/sync-center/error-center:** every metric named in
  Part A §F–§H is computed directly from `job`/`job.log` fields (state,
  error_class, job_source, retry_count, age via `create_date`/`started_at`)
  — no separate metrics store (Part A §F.2, RA-013 unchanged).
- **Deletion posture:** `job.log.job_id` uses `ondelete='restrict'`, not
  `cascade` — see §12 for the full rationale. A job is never unlink-able
  while its own log rows exist, and no group is granted Unlink on either
  model in any case (§10).

## 7. Job source and `odoo_event` trigger-origin mechanics

Resolving MBQ-62's residual at planning-proposal level (the semantic
decision itself — `odoo_event` as a seventh job-source value, plus the
requirement that every `odoo_event` job carries a trigger-origin — is
**already accepted by DEC-019** and is not reopened here):

- **Exact `job_source` selection values:** `webhook`, `manual_sync`,
  `scheduled_sync`, `reconciliation`, `setup_readiness_check`,
  `export_preview_dry_run`, `odoo_event` — a Python `Selection` on
  `shopify.connector.job.job_source` (§4.5), matching DEC-009's original six
  plus DEC-019's seventh, verbatim.
- **Exact `trigger_origin` field name:** `trigger_origin`, on the same
  `shopify.connector.job` model (not a separate model) — a `Selection` field,
  extensible via `selection_add` so a later domain module can register an
  additional trigger-origin value without a core schema migration.
- **Exact `trigger_origin` selection values for the two named use cases:**
  - `inventory_stock_change` — "inventory stock-change trigger" (DEC-019).
  - `fulfillment_picking_validation` — "fulfillment picking-validation
    trigger" (DEC-019).
- **Whether `trigger_origin` is required only when `job_source = odoo_event`:**
  yes. Proposed validation rule concept: a model-level constraint
  (conceptually `_check_trigger_origin_required`, not code written here)
  enforcing (a) `trigger_origin` must be set when `job_source = 'odoo_event'`
  and (b) `trigger_origin` must be empty for every other `job_source` value —
  preventing both a silently unclassified `odoo_event` job and an
  accidental trigger-origin value leaking onto an unrelated job source.
- **Validation rule concept:** implemented as an ORM `@api.constrains` on
  `job_source`/`trigger_origin` together (planning-level description only;
  no Python is written by this document).
- **Dashboard/display implications:** the dashboard's "last successful sync
  per domain with mechanism label" card (Part A §F.1.2) and the sync-center
  trigger/source filter (Part A §G.1) both read `job_source` directly, now
  with an honest fourth/seventh bucket (`odoo_event`) instead of a forced
  mislabel; `trigger_origin` is proposed as a secondary, expandable
  filter/column (alongside the existing operator-safe operation reference,
  Part A §G.7), not a first-class dashboard card of its own — consistent
  with Part A §F.4's "no vanity-only metrics" rule, since a raw
  trigger-origin count with no distinct next action would not clear that
  bar on its own.
- **Retry-origin event identity/timestamp:** `trigger_origin_event_ref` and
  `trigger_origin_event_at` (§4.5) satisfy DEC-019's audit requirement that
  the originating Odoo event's identity and its own timestamp (distinct from
  enqueue time) are recorded, extending Part A §D.10's audit shape rather
  than replacing it.

## 8. Idempotency and serialization guard schema

Resolving MBQ-20 and MBQ-21 at planning-proposal level. **Two distinct,
DB-backed keys are proposed on `shopify.connector.job`** — `idempotency_key`
and `operation_scope_key` — because they answer different questions and
need different lifetimes; conflating them into one field cannot express both
guarantees at once.

- **Exact operation-level idempotency key components:** `store_id` +
  `job_type` (feeding "operation type") + `res_model`/`res_id` (source
  record) + `shopify_target_gid` (Shopify target, where known) +
  `payload_hash` (payload version/hash) — matching Part A §D.6's conceptual
  tuple `(store, operation type, source record, Shopify target ID where
  known, payload version/hash)` field-for-field. Composed into
  `idempotency_key` (§4.5). **This key persists for the life of the job** —
  it is never cleared — and answers "is this the same operation, on the
  same target, with the same payload, already known?"
- **Field names/types:** all on `shopify.connector.job` (§4.5): `job_type`
  (Selection), `res_model` (Char), `res_id` (Integer), `shopify_target_gid`
  (Char, nullable), `payload_hash` (Char, nullable), `idempotency_key` (Char,
  computed + stored from the preceding five), `operation_scope_key` (Char,
  nullable, system-managed).
- **Uniqueness scope for `idempotency_key`:** `(store_id, idempotency_key)`
  — a genuinely different payload (different `payload_hash`) naturally
  produces a different key rather than colliding.
- **Hash/payload-version concept:** `payload_hash` is proposed as a hash of
  the normalized outbound payload (or an explicit version counter where the
  domain module tracks payload versions itself) — the exact hashing
  algorithm/normalization rule is an implementation-time detail for whichever
  domain module first needs it, not decided here; this session fixes only
  the **field's existence, name, and role** in the key.
- **Serialization guard mechanism — DB-backed, race-safe, not
  query-time-only:**
  - `operation_scope_key` is computed from the **coarser** tuple `store_id`
    + `res_model` + `res_id` + `shopify_target_gid` — deliberately
    **excluding** `job_type` and `payload_hash`, so that *any* operation
    against the same target is serialized, not only a retry of the
    identical operation. This matches Part A §D.7's own wording —
    "operations against the same `(store, source record, Shopify
    target)`" — which is not scoped to a single operation type.
  - `operation_scope_key` is **populated whenever the job is in a
    non-terminal state** (`draft`/`queued`/`running`/`retry_waiting`/
    `failed_retryable`/`blocked_manual_review`) and a target is known; it is
    **set back to `NULL`** the moment the job reaches any terminal state
    (`succeeded`/`failed_final`/`skipped`/`cancelled`) or is superseded.
  - A **database-level unique constraint on `(store_id,
    operation_scope_key)`** is proposed. PostgreSQL (Odoo's supported
    database) treats each `NULL` as distinct from every other `NULL` in a
    unique index, so any number of terminal-state jobs can coexist with a
    `NULL` `operation_scope_key` — full history is preserved — while at most
    **one row at a time** can hold a given non-null key. A second,
    concurrently-enqueued operation against the same target therefore
    **cannot be activated with a colliding key** — the database itself
    rejects the race, rather than relying on an application-level
    check-then-act query that could still race between the check and the
    write.
  - The enqueue/dispatch code path is expected to catch that constraint
    violation and respond by either routing the new operation to wait
    behind the existing job, or explicitly superseding it
    (`superseded_by_job_id`, §D.9) — **the constraint provides the safety
    guarantee; the application code provides the user-facing behavior on
    top of it.**
  - A job whose `job_type` has no meaningful target (e.g.
    `core_readiness_check`, §4.5) simply never populates
    `operation_scope_key` — the guard is a no-op for job types with nothing
    to serialize against.
  - **No separate lock table is introduced.** The unique constraint on the
    job table itself is the lock — no `SELECT ... FOR UPDATE` or external
    locking mechanism is required as the safety primitive, though the
    enqueue code path may still use a transaction to turn a constraint
    violation into a clean "queued behind existing job" response rather than
    a raw database error.
- **How unresolved ambiguous/manual-review operations prevent conflicting
  dispatch:** a job sitting in `blocked_manual_review` or `retry_waiting`
  keeps its `operation_scope_key` populated (both are non-terminal states),
  so the unique constraint continues to block a new operation against that
  same target until the job reaches a terminal state or is explicitly
  superseded — satisfying Part A §D.7's "serialized while a prior operation
  against that target is unresolved" rule at the database level, not only
  in application logic.
- **Which model owns the guard:** `shopify.connector.job` — no separate
  "operation guard" model or lock table is introduced (§3).
- **`idempotency_key` and `operation_scope_key` are distinct and
  complementary, not redundant:** `idempotency_key` prevents duplicate
  *connector-side processing* of the same operation (persists permanently);
  `operation_scope_key` prevents *any* conflicting operation, same or
  different type, from dispatching concurrently against the same target
  while one is unresolved (exists only while non-terminal). A retried
  instance of the identical operation matches on both keys; a *different*
  operation against the same target matches only on `operation_scope_key`.
- **Connector-side idempotency is permanent, not assumed platform-covered:**
  neither key makes a non-`@idempotent` Shopify mutation safe to resend
  after an ambiguous outcome — the ambiguous-outcome rule (Part A §D.7,
  unchanged, already accepted) still requires a verification read or a
  route to `blocked_manual_review` for those operations specifically.

## 9. Retry constants and backoff policy

Resolving MBQ-16 at planning-proposal level. These are **implementation-planning
defaults**, explicitly proposed as adjustable, cautious starting values —
not final tuned production constants:

| Error-class family | Auto-retry? | Max auto-retry attempts | Backoff schedule | Max retry window |
| --- | --- | --- | --- | --- |
| Shopify throttling/rate-limit; concurrency/race conflict | Yes | 12 | Exponential: 30s base, ×2 multiplier, capped at 30 min, ±20% jitter; honor a Shopify-supplied wait signal when present, in preference to the fixed schedule | 24 hours (aligned to Shopify's own `@idempotent` 24-hour TTL, so an idempotent retry never outlives the window Shopify itself treats as safe) |
| Shopify temporary/server/network, on reads or `@idempotent` writes | Yes | 8 | Same exponential schedule as above | 24 hours |
| Shopify temporary/server/network, on a non-`@idempotent` write (ambiguous outcome) | **No blind retry** | 0 (single verification-read attempt instead, per Part A §D.7, already accepted) | N/A | N/A — routes to `blocked_manual_review` if no safe verification read exists |
| Shopify permission/scope/auth; Shopify userErrors/validation; Odoo validation/configuration; mapping missing; data shape/schema mismatch | No | 0 | N/A — manual fix then operator-triggered retry only | N/A |
| Ambiguous match; binding conflict; duplicate risk; destructive-write guard blocked; inventory location missing; fulfillment notification confirmation missing | No | 0 | N/A — `blocked_manual_review`, Reviewer action required | N/A |
| Financial total mismatch | No | 0 | N/A — conservative, never silent (DEC-007 §6, unchanged) | N/A |
| Unknown/system error | Single safety-net retry only | 1 | Fixed 60s delay, no exponential growth | N/A — routes to `blocked_manual_review` or `failed_final` after the one attempt |

- **Retryable vs. non-retryable classes:** exactly the DEC-009 §D.5
  taxonomy, unchanged — this table only adds numbers to the classes DEC-009
  already marked auto-retryable.
- **Manual-review classes:** unchanged from Part A §D.5.4's six confirmation-
  required classes; 0 automatic attempts, by definition.
- **Rate-limit handling:** throttling/rate-limit gets the widest auto-retry
  ceiling (12) since it is the class most likely to resolve on its own
  within a bounded window; a Shopify-supplied retry-after/cost-throttle
  signal, where the transport layer surfaces one, takes precedence over the
  fixed backoff schedule for that specific wait.
- **Cron safety assumptions:** these counters are entirely connector-owned
  on the `job` model; `ir.cron`'s own failure-deactivation math is not
  reused as retry logic (DEC-005/DEC-009, unchanged). Cron cadence/batch-size
  constants themselves (MBQ-18) are **not** decided by this document — MBQ-18
  was not one of the eleven rows the accepted audit named for this session
  and remains open, routed to whichever session designs the actual cron
  drain loop.

## 10. Access groups and security planning

Resolving MBQ-44 and MBQ-45's residual at planning-proposal level:

- **Exact group XML IDs** (module `shopify_connector_core`):
  - `group_shopify_connector_auditor` — base group (Part A §J.1's "Auditor,"
    P3).
  - `group_shopify_connector_operator` — `implied_ids` includes the auditor
    group (P1).
  - `group_shopify_connector_reviewer` — `implied_ids` includes the auditor
    group (narrower cut of P1/P2).
  - `group_shopify_connector_admin` — `implied_ids` includes both operator
    and reviewer groups, transitively implying auditor (P2).
  - `module_category_shopify_connector` — an `ir.module.category` XML ID so
    the four groups appear together under one "Shopify Connector" heading in
    Settings → Users, rather than under the generic "Other" category.
- **Role hierarchy:** unchanged from the already-accepted DEC-013/DEC-018
  hierarchy (Administrator ⊃ Operator/Reviewer ⊃ Auditor; Operator and
  Reviewer are siblings) — this pass only fixes the XML identifiers, not the
  hierarchy itself.
- **Which groups can read/write core store/config/job/log/error records**
  (planned row shapes, no CSV file created):

  | Model | Auditor | Operator | Reviewer | Admin |
  | --- | --- | --- | --- | --- |
  | `shopify.connector.store` | Read | Read | Read | Read + Write |
  | `shopify.connector.store.settings` | Read | Read | Read | Read + Write |
  | `shopify.connector.location` | Read | Read | Read | Read — no manual Create/Write/Unlink for any group; the cache is system-maintained (§4.3) |
  | `shopify.connector.job` | Read | Read + Write + Create | Read + Write (for resolving `blocked_manual_review`) | Read + Write + Create |
  | `shopify.connector.job.log` | Read | Read | Read | Read — no manual Create/Write/Unlink for any group; log rows are system-appended, not user-authored |

  **No group is granted Unlink on any core model** — jobs, logs, bindings,
  and settings are never user-deletable, matching §12's "no silent
  destructive history deletion" rule and Part A §I.4's "disabling must not
  delete history." This access-level restriction is deliberately reinforced,
  not merely mirrored, at the schema level: `job.log.job_id` uses
  `ondelete='restrict'` (§6, §12), so even a privileged database-level
  action cannot silently cascade-delete a job's log history through the
  foreign key.
- **Record rules for Phase 1 single-company/single-store posture:** **none
  proposed as required.** Phase 1 is a single connected store (DEC-003); a
  `store_id` scoping field already exists on every model (§4), so a future
  multi-store record rule (`[('store_id', 'in', user.allowed_store_ids)]`,
  illustrative only) can be added later without any schema change.
- **What remains for later multi-company/multi-store isolation:** MBQ-46
  (explicitly later-phase, unchanged) — the store-scoping field is present
  now specifically so that a future record rule is the only artifact a
  multi-store phase needs to add, not a model rename or field addition.
- **Planned `ir.model.access.csv` rows:** the table above states, per model
  per group, which of read/write/create/unlink would be granted — **no CSV
  file is created by this document.**

## 11. Credential persistence posture for first slice

Handling MBQ-04 per the task's explicit safe-default instruction —
**revised to a full descope, per ChatGPT's REVISE feedback**:

- **No official Odoo documentation on field-level encryption-at-rest
  mechanisms was fetched or reviewed during this session.** This is a
  planning/synthesis session over already-accepted repository content, not a
  fresh official-doc research session (matching the pattern DEC-018/DEC-019
  followed — "no external research performed, per scope instruction"). Per
  `CLAUDE.md` §7/§8, inventing an unverified Odoo encryption mechanism here
  would be an unsupported claim, not a citable fact.
- **Option A (full descope) is adopted.** The first core slice proposes
  **no credential model of any kind** — not even a lifecycle-metadata-only
  model. Only `store`, `store.settings`, `location`, `binding.mixin`,
  `job`, and `job.log` (§3) are proposed. No real Shopify token, and no
  credential status/rotation/scopes-snapshot schema, is accepted, stored,
  or represented by this slice.
- **Explicit statements:**
  - **No credential model is proposed for the first slice.**
  - **No credential metadata model is proposed for the first slice.**
  - **No secret field is proposed.**
  - **Real credential persistence and credential lifecycle metadata both
    remain blocked by MBQ-04** — neither is resolved, partially or
    otherwise, by this document.
  - **A future MBQ-04 decision may add a credential model later**, after
    (a) ChatGPT reviews official Odoo documentation/source evidence on
    field-level encryption-at-rest and decides a mechanism, and (b) a
    dedicated future session designs that model's shape — this document
    does not pre-design it, not even at the metadata level, so that no
    schema commitment made here has to be revisited once a real mechanism
    is chosen.
- **What is, and is not, resolved:**
  - **Not resolved, not even partially:** MBQ-04 is **not** proposed as
    "partially resolved" by this document. It is **explicitly, fully
    descoped for slice 1** — the correct classification is "proposed not
    resolved / explicitly descoped," not a partial resolution (§14).
  - **Still fully open:** the exact field name, type, storage/encryption
    mechanism, and even the existence of any credential-lifecycle schema.
    Real token storage — and any credential-metadata model — remain blocked
    until either (a) ChatGPT reviews official Odoo documentation/source
    evidence on field-level encryption-at-rest and decides a mechanism, or
    (b) some other explicit ChatGPT decision resolves MBQ-04.
  - **Also still blocked as a consequence:** any connection/test-connection
    flow that would need to *use* a real token (setup wizard credential-entry
    step, live test-connection call) — those remain out of scope for a
    core-only schema slice regardless of MBQ-04, since they also require the
    transport client (MBQ-51/52, a later `core` milestone).

## 12. Constraint and index plan

- **Uniqueness:**
  - `shopify.connector.store.shop_domain` — unique per database.
  - `shopify.connector.store.settings.store_id` — unique (one settings row
    per store; the sole store↔settings link, no reverse field on `store`).
  - `shopify.connector.location` — unique on `(store_id, shopify_location_gid)`.
  - `shopify.connector.job.idempotency_key` — unique on `(store_id,
    idempotency_key)` (persists for the life of the job).
  - `shopify.connector.job.operation_scope_key` — unique on `(store_id,
    operation_scope_key)`, with `NULL` excluded from the collision check
    (standard PostgreSQL unique-index behavior), so terminal jobs never
    block each other while non-terminal jobs against the same target
    genuinely collide (§8).
  - Per-domain concrete binding models (out of scope, MBQ-55) will need
    unique `(store_id, shopify_gid)` and `(store_id, <Odoo record FK>)`,
    restated from Part A §C.2 for forward reference only.
- **Foreign keys:** every non-`store` model above carries a required
  `store_id` Many2one, `ondelete='restrict'` (a store record is never
  deletable while jobs/logs/bindings reference it — disconnect uses `state`,
  not deletion, per MBQ-08). **`shopify.connector.job.log.job_id` is
  `ondelete='restrict'`, not `cascade`** — a job's log rows are its audit
  history, not disposable children; no group is granted Unlink on either
  model in the first place (§10), but the foreign key itself must not
  silently cascade-delete log history if a job row is ever removed through
  a privileged/database-level path outside normal application access. A
  job cannot be deleted while its own log rows exist; deleting the logs
  first would itself destroy the audit trail the logs exist to preserve, so
  in practice neither is expected to be deleted in normal operation.
- **Store-scoping:** present on every model (§4), satisfying DEC-006's
  per-store uniqueness principle even in the single-store Phase 1 MVP.
- **Idempotency keys:** `shopify.connector.job.idempotency_key`, as above.
- **Serialization guard key:** `shopify.connector.job.operation_scope_key`,
  as above — distinct from the idempotency key (§8).
- **Binding uniqueness:** deferred to each concrete domain binding model
  (out of scope), but the abstract mixin's own fields (§4.4) are designed so
  every concrete model can enforce the composite uniqueness without adding
  new mixin fields later.
- **Job duplicate/conflict prevention:** two complementary mechanisms — the
  `idempotency_key` uniqueness constraint prevents duplicate *connector-side
  processing* of the same operation; the `operation_scope_key` uniqueness
  constraint (DB-backed, race-safe — §8) prevents *conflicting concurrent
  dispatch* of any operation, same or different type, against an unresolved
  target.
- **Selection constraints:** `trigger_origin` required iff `job_source =
  'odoo_event'` (§7); `manual_review_subreason` required iff `state =
  'blocked_manual_review'` (§4.5).
- **No silent destructive history deletion:** no `unlink` access is granted
  to any role on `job`, `job.log`, `store.settings`, or `location` (§10);
  `job.log.job_id` is `ondelete='restrict'`, not `cascade` (above);
  disconnect and domain-disable both use state fields, never deletion,
  matching Part A §I.4/§B.1's already-accepted "disabling/disconnecting
  must not delete history" rules.

## 13. Migration and future extensibility notes

- **Consistent naming convention from day one.** Every model uses the
  `shopify.connector.<entity>` prefix; later domain modules' own concrete
  binding models (MBQ-55) are expected to continue it
  (`shopify.connector.product.binding`, etc.), so no later connector-wide
  rename is needed once domain modules land.
- **Job+log split avoids a common regret.** Fixing job/log as two models
  now — rather than one mutable job row — means a retry never has to
  overwrite or reconstruct history that a single-model design would have
  lost; this is fixed once, early, exactly as Part A/Part E's own "must be
  fixed once, early" framing for MBQ-19 anticipated.
- **No one giant module, no over-fragmentation.** Six models cover the full
  core substrate the audit named; three candidate extra models
  (error/manual-review, idempotency/operation-guard, audit-payload) are
  explicitly folded rather than added, and no credential model is proposed
  at all (§11), keeping the schema from over-fragmenting (RA-012 pattern)
  while still giving every domain module a single, shared substrate to
  build on (RA-013 pattern, avoiding duplicated job/log/error abstractions
  per domain).
- **Extension seams avoid later renaming/migration pain:**
  - `store.settings` — domain modules add fields via `_inherit`, no new
    model, no migration when a domain installs.
  - `job.job_type` and `job.trigger_origin` — both `Selection` fields
    extended via `selection_add`, the idiomatic Odoo mechanism for a shared
    field whose vocabulary grows as sibling modules install, without a
    schema migration; `job_type` ships with two core-owned values
    (`core_readiness_check`, `core_manual_maintenance`) so `core` itself
    never depends on a domain module installing first for its own required
    field to be populatable.
  - `job.enqueue_decisions` — a generic JSON field for "whatever enqueue-time
    decision a domain needs preserved across retry," rather than one named
    Boolean/Selection column per domain concern (e.g. a `notification_flag`
    column specific to fulfillment) — avoids a schema migration every time a
    new domain introduces its own enqueue-time decision.
- **Splitting `idempotency_key` from `operation_scope_key` avoids a later
  migration.** Fixing both keys, with different lifetimes and different
  composing tuples, in the same slice avoids having to retroactively add a
  coarser serialization key once code already depends on the finer-grained
  idempotency key as the sole uniqueness mechanism.
- **No credential model proposed avoids a later migration around an
  unresolved mechanism.** Not committing even a lifecycle-metadata model
  now means a future MBQ-04 resolution designs its schema once, against
  real evidence, instead of this pass guessing a shape that resolution
  might then have to alter.
- **No destructive domain uninstall/disable.** No model above is deleted or
  emptied by disabling a domain (Part A §I.4, unchanged) or by disconnecting
  a store (MBQ-08, unchanged) — both are state transitions, never row
  deletions, so the schema never has to design around a data-loss path.
- **Multi-store/multi-company dead ends avoided.** `store_id` scoping exists
  on every model from the first core slice, even though Phase 1 is
  single-store — a later multi-store phase (MBQ-46) needs only new record
  rules (§10), not a schema rename or a retrofitted scoping column.

## 14. MBQ impact if accepted

**Draft register wording only — not applied.** The wording below becomes the
register's actual text only via a future acceptance patch, if and when
ChatGPT accepts this document (mirroring the DEC-013 through DEC-020
pattern). No MBQ row in `master-blueprint-open-questions.md` is edited by
this pass itself.

- **MBQ-01:** *Proposed resolved pending ChatGPT acceptance* — exact Odoo
  model names for every core-substrate concept in scope for a first
  core-only slice (`shopify.connector.store`, `.store.settings`,
  `.location`, `.binding.mixin`, `.job`, `.job.log`) proposed in §3.
  Domain-specific binding model names (MBQ-55) and view/menu XML IDs
  (MBQ-03) remain out of scope and unresolved by this pass.
- **MBQ-02:** *Proposed resolved pending ChatGPT acceptance* — field
  names/types for the six models above proposed in §4, including
  constraint/index design (§12).
- **MBQ-04:** *Proposed not resolved for slice 1 — explicitly, fully
  descoped (Option A).* No credential model, credential metadata model, or
  secret field of any kind is proposed for the first core-only slice (§11).
  Real credential persistence, and the credential lifecycle schema itself,
  both remain fully open, blocked pending official Odoo evidence and a
  separate ChatGPT decision. A future MBQ-04 session may propose a
  credential model once that evidence exists; this document does not
  pre-design one.
- **MBQ-07:** *Proposed resolved pending ChatGPT acceptance* — exact
  technical shape is a store-scoped `shopify.connector.store.settings`
  model (§5), distinct from the store/connection model, extended by domain
  modules via classic Odoo model inheritance, matching DEC-013's accepted
  direction.
- **MBQ-16:** *Proposed resolved pending ChatGPT acceptance* — retry
  ceilings and backoff constants proposed in §9, by error-class family,
  explicitly labelled as adjustable implementation-planning defaults.
- **MBQ-19:** *Proposed resolved pending ChatGPT acceptance* — job+log
  split (`shopify.connector.job` + `.job.log`), with error/manual-review
  fields folded onto the job model rather than a separate model (§3/§6);
  `job.log.job_id` uses `ondelete='restrict'` to protect log history (§12).
- **MBQ-20:** *Proposed resolved pending ChatGPT acceptance* — operation-
  level idempotency key schema proposed in §8 (`store_id` + `job_type` +
  `res_model`/`res_id` + `shopify_target_gid` + `payload_hash`, composed
  into a computed, uniquely-constrained `idempotency_key` field on `job`),
  not a separate model, kept distinct from the serialization-guard key
  (`operation_scope_key`, MBQ-21).
- **MBQ-21:** *Proposed resolved pending ChatGPT acceptance* — the
  serialization guard is proposed as a **DB-backed, race-safe** mechanism
  owned by `shopify.connector.job` (§8): a system-managed
  `operation_scope_key` field, populated only while a job is non-terminal
  and cleared on reaching a terminal state, under a unique constraint on
  `(store_id, operation_scope_key)` — not a query-time-only check, not a
  separate model, and not a queue-level lock table.
- **MBQ-44:** *Proposed partially resolved pending ChatGPT acceptance* —
  planned `ir.model.access.csv` row shapes (which of the four groups get
  read/write/create/unlink per core model) proposed in §10; no CSV file is
  created, and record rules beyond store-scoping are explicitly deferred
  (MBQ-46).
- **MBQ-45 (residual only):** *Proposed resolved pending ChatGPT
  acceptance* — `group_shopify_connector_admin`/`_operator`/`_reviewer`/
  `_auditor` and a `module_category_shopify_connector` XML ID proposed in
  §10. The 1:1 role-to-group mapping and single-shared-surface decision
  themselves are unchanged, already resolved by DEC-018 — this pass adds
  only the missing identifiers.
- **MBQ-62 (residual only):** *Proposed resolved pending ChatGPT
  acceptance* — the `job_source` Selection value `odoo_event` and the
  `trigger_origin` Selection field/values proposed in §7, with a validation
  rule making `trigger_origin` required only when `job_source = odoo_event`.
  The semantic classification itself is unchanged, already resolved by
  DEC-019 — this pass adds only the missing field/model mechanics.

## 15. What remains blocked after this planning pass

- **All first code** — no Odoo module, model file, view, controller,
  security file, manifest, migration, or test is created or authorized by
  this pass.
- **Real credential persistence, and any credential/lifecycle schema at
  all** — MBQ-04 is fully descoped for this slice, not just the secret
  value; no credential model of any kind exists yet (§11).
- **Setup wizard / test-connection flow** — needs both a resolved MBQ-04 (or
  a scoped-out connection step) and a working transport client; neither
  exists yet.
- **Transport/API client** — MBQ-51 (pacing parameters) and MBQ-52's exact
  upgrade mechanics remain open; no GraphQL client design is proposed here.
- **Product/customer/order/inventory/fulfillment domains** — every domain
  model, binding model (MBQ-55), and domain-specific schema question
  (MBQ-23–43, MBQ-56–61, MBQ-63–65's own mechanics) remains untouched and
  open.
- **Webhooks** — the webhook receiver/controller, HMAC verification, and
  dedup mechanics are architecture-accepted (DEC-005/DEC-013) but not
  schema-designed by this pass.
- **Release readiness** — MBQ-18 (cron cadence/throughput), MBQ-49
  (MVP-scale validation), MBQ-54's exact uninstall-guard mechanism, and
  every other "blocks release readiness, not initial coding" row remain
  open, unaffected by this pass.
- **The explicit gate-opening act itself** (`master-blueprint.md`'s
  criterion 3) — not performed, not proposed, not approximated by this
  document under any outcome.
- **Every implementation task** — no file matching `CLAUDE.md` §9 /
  `implementation-task-template.md` is written by this pass or its
  eventual acceptance.

## 16. Recommendation to ChatGPT

**Recommend: accept as revised.** This revision applies every correction
from ChatGPT's REVISE review of the original proposal, as fixes rather than
flagged judgment calls: `shopify.connector.store.credential` is removed
entirely (§3, §11) — MBQ-04 is now a full slice-1 descope, not a partial
resolution; the `store.settings_id`/One2many-named-singular contradiction is
fixed by removing the reverse field (§4.1, §4.2); `job.log.job_id` now uses
`ondelete='restrict'`, not `cascade` (§4.6, §12); `job_type` carries two
core-owned values (`core_readiness_check`, `core_manual_maintenance`) so the
required Selection is never contradictorily empty before any domain module
installs (§4.5); the serialization guard is now a DB-backed
`operation_scope_key` + unique constraint, kept distinct from
`idempotency_key` (§8); and the `mail.thread` tracking commitment is removed,
left to a future implementation task's own manifest dependency choice
(§4.2).

Two judgment calls from the original proposal were not named in the REVISE
feedback and remain genuine design choices, still flagged for scrutiny:

1. **Job+log split** (§6, MBQ-19) — chosen over a single mutable job model.
   If ChatGPT prefers a single-model design (e.g. an append-only `job` model
   with no separate `job.log`), that is an **accept with changes** on §3/§4.5/§4.6
   specifically, not a rejection of the rest of this document.
2. **`enqueue_decisions` as a generic JSON field** (§4.5, §13) rather than
   named columns per domain decision (e.g. a dedicated `notification_flag`
   column) — chosen for extensibility, at the cost of losing native
   column-level typing/indexing on any single decision. If ChatGPT prefers
   named columns for the decisions already known today (Phase 1 has exactly
   one — the fulfillment notification flag), that is a narrow **accept with
   changes** on §4.5 only.

**Do not recommend opening the implementation gate.** None of
`master-blueprint.md`'s five gate-opening criteria changes state because of
this document: criterion 1 remains satisfied only for a zero-UI scope
(unchanged); criterion 2 improves for eleven specific rows but roughly three
dozen other "Blocks implementation: Yes" rows remain untouched (MBQ-03/05/09/
14/23–43/46/48–61/63–65 and others, per the audit's own §4 sweep); criterion
3 (the explicit gate-opening act) is not performed or proposed by this
document under any outcome; criterion 4 (a written implementation task)
remains vacuously unmet — no implementation task exists or is created here;
criterion 5's ambiguity (the DP-003/004/006 escalation row's `ESCALATED`
label) is untouched, unaffected by this pass. **Do not recommend code yet.**
