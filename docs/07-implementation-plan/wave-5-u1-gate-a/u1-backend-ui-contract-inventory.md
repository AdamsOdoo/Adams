# Wave 5 U1 — Backend UI-Contract Inventory (exact, source-verified)

> **Status: Gate A planning artifact — Docs-only. NOT accepted. Authorizes no
> implementation.** Produced 2026-07-23 by the Wave 5 U1 Gate A session.
> **This is the authoritative backend contract for U1.** Every model, field,
> selection value, action, and group named below was read directly from the
> **exact frozen Wave 4 candidate `2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a`**
> (PR #189 head) plus the core surfaces present in the same checkout. Where a
> product/design document names a different value, **the code value below is
> authoritative for U1** and the product value is flagged as superseded in §9.

## 0. Provenance

- **Wave 4 head inspected:** `2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a`.
- **Integration base of this planning session:** `mvp/program-integration@dd0af5d94a7f730e738dca955971e00bb4cc9122`.
- **Addon inspected:** `addons/shopify_connector_fulfillment/**` (17 model files,
  1 ACL CSV, 1 security XML, 1 cron XML) plus consumed core surfaces in
  `addons/shopify_connector_core/**`.
- **Method:** direct `Read`/`Grep` of the checked-out source. No inference; a
  surface not found in source is recorded as ABSENT (§9/§10), never assumed.

U1 code does **not** exist at the integration base; the fulfillment addon lives
only on the Wave 4 branch until PR #189 merges. This has a direct consequence for
the branch strategy (see `u1-branch-dependency-strategy.md`).

---

## 1. Models U1 may consume

### 1.1 New concrete models (owned by `shopify_connector_fulfillment`)

| Model `_name` | Kind | Purpose | Primary U1 use |
|---|---|---|---|
| `shopify.connector.fulfillment.binding` | Model (`_inherit` `shopify.connector.binding.mixin`) | One row per **created Shopify Fulfillment** (keyed on the Fulfillment GID, `UNIQUE(store_id, picking_id)`) | Lineage: picking ⇄ fulfillment; tracking snapshots; review-release entry point |
| `shopify.connector.fulfillment.inbound.evidence` | Model | One row per **observed** Shopify Fulfillment GID; origin + status + reconciliation state; **the review case** | Review workspace record; review actions |
| `shopify.connector.fulfillment.inbound.evidence.line` | Model | Per-line evidence + reconciled-quantity ledger | Review workspace line detail |

### 1.2 Service model (abstract — internal engine; **not** a UI surface)

| Model `_name` | Kind | Note |
|---|---|---|
| `shopify.connector.fulfillment.service` | **AbstractModel** | Hosts every handler/strategy/scan/mode2 engine method. **U1 must never call any `_`-prefixed service method.** Defined in `shopify_connector_fulfillment_reader.py`; extended (same `_name`) by the admission/scans/inbound/mode2/review/create_strategy/tracking_strategy files. |

### 1.3 Core/Odoo models extended by Wave 4 (U1 reads/gates against these)

| Model `_inherit` | What Wave 4 added | U1 relevance |
|---|---|---|
| `shopify.connector.store.settings` | `fulfillment_operating_mode` + mode-switch state fields; `action_start_mode2_switch`, `action_rollback_to_mode1` | **Mode display + mode-change entry point** |
| `shopify.connector.job` | 10 fulfillment `job_type` values (`selection_add`); `fulfillment_tracking_change` `trigger_origin`; operation-scope override | Job/lineage views, filters |
| `shopify.connector.job.dispatch` | Handlers/replay-policies/strategies (abstract) | None — internal only |
| `shopify.connector.readiness.check` | 3 fulfillment readiness checks (abstract) | Mode-2 readiness surfacing |
| `stock.picking` | trigger seams (`_action_done`, `write`) | None to call; picking is a lineage node |

---

## 2. Field inventory — `shopify.connector.store.settings` (fulfillment additions)

Source: `models/shopify_connector_store_settings.py`, `models/shopify_connector_fulfillment_scans.py` (mode-switch actions).

| Field | Type | Selection / comodel | Field-level `groups=` | R/W authority | Safe to display? |
|---|---|---|---|---|---|
| `fulfillment_operating_mode` | Selection | `mode1`, `mode2` (see §5.1); default `mode1`, required | `...group_shopify_connector_admin` | Admin only (field-level) | **Yes** — the mode display |
| `fulfillment_switch_in_progress` | Boolean | — | admin | Admin only | Yes — mode-switch progress indicator |
| `fulfillment_mode_switch_nonce` | Char | — | admin | Admin only | **No** — internal idempotency nonce |
| `fulfillment_last_mode_switch_at` | Datetime | — | admin | Admin only | Yes — switch history |
| `fulfillment_last_mode_switch_uid` | Many2one | `res.users` | admin | Admin only | Yes — switch history (who) |
| `fulfillment_notification_confirmed` | Boolean | — | (none) | writable | Yes — notification confirmation gate |
| `fulfillment_last_reconciliation_at` | Datetime | — | (none) | writable | Yes — reconciliation watermark |

Core store-settings flags U1 also reads (source: `core/models/shopify_connector_store_settings.py`):
`fulfillment_domain_enabled` (Boolean), `notification_default_enabled` (Boolean),
plus sibling `*_domain_enabled` flags. `store_id` links to `shopify.connector.store`.

> **Field-security consequence (Odoo 19 `groups=`):** the five admin-gated fields
> are **invisible in `fields_get`/read for non-admins**. A U1 form that binds them
> for an Operator/Reviewer/Auditor must place them behind the same admin group in
> the view (or a non-admin will get a field-access surprise). Mirror the model
> `groups=` in the view.

---

## 3. Field inventory — `shopify.connector.fulfillment.inbound.evidence` (the review case)

Source: `models/shopify_connector_fulfillment_inbound_evidence.py`. **All fields are `readonly=True`** (system-populated). This is a read/act surface, never a write-form.

| Field | Type | Selection / comodel | Display class |
|---|---|---|---|
| `store_id` | Many2one | `shopify.connector.store` | Safe |
| `order_binding_id` | Many2one | `shopify.connector.order.binding` | Safe (lineage) |
| `fulfillment_binding_id` | Many2one | `shopify.connector.fulfillment.binding` | Safe (lineage) |
| `shopify_fulfillment_gid` | Char | — | Safe (remote ref) |
| `shopify_order_gid` | Char | — | Safe (remote ref) |
| `origin_class` | Selection | §5.2 | Safe |
| `origin_confirmed` | Boolean | — | Safe |
| `fulfillment_status_raw` | Char | — | Safe (badge source) |
| `fulfillment_status_normalized` | Char | — | Safe (badge source) |
| `fulfillment_status_is_success` | Boolean | — | Safe |
| `display_status_raw` | Char | — | Safe (display-only per code) |
| `display_status_normalized` | Char | — | Safe |
| `state_snapshot` | Text (JSON) | — | **Guarded** — raw Layer-A snapshot; render parsed/summarised, never raw dump |
| `schema_warning` | Boolean | — | Safe (unknown-enum flag) |
| `delivered_inconsistency` | Boolean | — | Safe |
| `tracking_snapshot` | Text (JSON) | — | **Guarded** — parse to chips; not a raw dump |
| `reconciled_state` | Selection | §5.3 | Safe |
| `review_reason` | Selection | §5.4 | Safe (badge) |
| `review_detail` | Text | — | Safe — code guarantees this is **sanitized** structured detail, never a raw payload |
| `resolution_actor_uid` | Many2one | `res.users` | Safe |
| `resolution_at` | Datetime | — | Safe |
| `first_observed_at` / `last_observed_at` | Datetime | — | Safe |
| `line_ids` | One2many | evidence line | Safe (line detail) |

Evidence **line** (`...inbound.evidence.line`, all readonly): `evidence_id`,
`fo_line_item_gid` (Char), `line_item_gid` (Char), `sale_line_id` (M2o
`sale.order.line`), `quantity` (Int), `reconciled_quantity` (Int). Helper
`reconciled_quantity_ledger()` returns `{fo_line_item_gid: qty}` (safe to call for display).

---

## 4. Field inventory — `shopify.connector.fulfillment.binding`

Source: `models/shopify_connector_fulfillment_binding.py`. All snapshot fields `readonly=True`; the model declares `_pii_snapshot_fields()` → **`[]`** (fulfillment stores **no** customer PII; tracking data is not PII).

| Field | Type | Display class |
|---|---|---|
| `picking_id` | Many2one `stock.picking` (required, readonly) | Safe (lineage) |
| `order_binding_id` | Many2one `shopify.connector.order.binding` | Safe (lineage) |
| `shopify_gid` (from mixin) | Char = **Fulfillment GID** | Safe (remote ref) |
| `shopify_fulfillment_order_gids` | Text (JSON list of FO GIDs) | Guarded — parse for audit |
| `tracking_numbers_snapshot` | Text (JSON) | Guarded — parse to chips |
| `tracking_company_snapshot` | Char | Safe |
| `tracking_urls_snapshot` | Text (JSON) | Guarded — parse to links |
| `notify_customer_sent` | Boolean | Safe |
| `shopify_status_snapshot` | Char | Safe (badge) |
| `shopify_status_normalized` | Char | Safe (badge) |
| `shopify_last_synced_at` | Datetime | Safe |

Protected (never writable via UI) — `_additional_protected_binding_fields()`
lists: `picking_id`, `order_binding_id`, `shopify_fulfillment_order_gids`,
`tracking_numbers_snapshot`, `tracking_company_snapshot`, `tracking_urls_snapshot`,
`notify_customer_sent`, `shopify_status_snapshot`, `shopify_status_normalized`,
`shopify_last_synced_at`. Constraints: `UNIQUE(store_id, shopify_gid)`,
`UNIQUE(store_id, picking_id)`.

---

## 5. Exact selection vocabularies (code-authoritative)

### 5.1 `fulfillment_operating_mode`
`('mode1', 'Mode 1 — Odoo-Controlled')`, `('mode2', 'Mode 2 — Bidirectional Exact Reconciliation')`. Default `mode1`.

### 5.2 `origin_class` (evidence)
`connector`, `external_merchant`, `external_app`, `external_unknown`.
Labels: Connector-Created / External — Merchant / External — App/Service / External — Unknown Origin.

### 5.3 `reconciled_state` (evidence)
`observed`, `review`, `acknowledged`, `applied`, `superseded`.
Labels: Observed / Review Case Open / Acknowledged (Handled Outside Odoo) / Applied to Odoo / Superseded.

### 5.4 `review_reason` (evidence) — 20 values, exact
`order_binding_missing`, `fulfillment_state_not_success`, `fulfillment_order_unresolved`,
`product_binding_missing`, `line_mapping_ambiguous`, `quantity_overrun`,
`quantity_mismatch`, `location_unmapped`, `picking_ambiguous`, `reservation_invalid`,
`lot_serial_ambiguous`, `already_reconciled`, `binding_conflict`, `remote_state_changed`,
`origin_unconfirmed`, `mode_not_enabled`, `carrier_would_book`, `delivered_not_validated`,
`cancelled_after_validation`, `unknown_status_value`.
> Note: `over_fulfillment` is **absent** (removed vocabulary); the quantity-overrun case is `quantity_overrun`.

### 5.5 Fulfillment `job_type` values (10) — `shopify.connector.job` `selection_add`
`fulfillment_picking_admission`, `fulfillment_create`, `fulfillment_tracking_admission`,
`fulfillment_tracking_update`, `fulfillment_mutation_reconcile`, `fulfillment_inbound_observation`,
`fulfillment_reconciliation_check`, `fulfillment_reconnect_catchup`, `fulfillment_mode_switch_scan`,
`fulfillment_mode2_evaluation`. Mutation domains (remote-effect) = `fulfillment_create` and `fulfillment_tracking_update` only.

### 5.6 `trigger_origin` (fulfillment additions)
Added: `fulfillment_tracking_change`. Merged core value reused: `fulfillment_picking_validation`.

### 5.7 Core `shopify.connector.job` `state` (10) — for lineage/status views
`draft`, `queued`, `running`, `succeeded`, `failed_final`, `skipped`, `cancelled`,
`retry_waiting`, `failed_retryable`, `blocked_manual_review`.
Terminal: `succeeded`, `failed_final`, `skipped`, `cancelled`.

### 5.8 Core `error_class` (16) / `manual_review_subreason` (9)
`error_class`: `shopify_throttling_rate_limit`, `shopify_temporary_server_network`,
`shopify_permission_scope_auth`, `shopify_user_errors_validation`, `odoo_validation_configuration`,
`mapping_missing`, + the 9 subreasons, + `financial_total_mismatch`, `data_shape_schema_mismatch`,
`concurrency_race_conflict`, `unknown_system_error`.
`manual_review_subreason` (9): `ambiguous_match`, `binding_conflict`, `duplicate_risk`,
`no_reconciliation_strategy`, `idempotency_contract_violation`, `store_identity_mismatch`,
`destructive_write_guard_blocked`, `inventory_location_missing`,
`fulfillment_notification_confirmation_missing`.

### 5.9 Core `shopify.connector.mutation.attempt` outcome selections
`observed_outcome`: `pending`, `succeeded`, `failed_clean`, `uncertain`.
`resolution_disposition`: `applied`, `not_applied`. `resolution_source`:
`reconciliation_read`, `manual_admin`.

---

## 6. UI-callable public actions (the ONLY sanctioned action surface)

Every action mirrors a **server-side** group check; a U1 button must be gated by the **same** group (UI/ACL agreement — wave-5 DoR hard-stop 9).

| Action | Model | Server gate | Legal precondition | Legal result | Refusal behaviour |
|---|---|---|---|---|---|
| `action_start_mode2_switch()` | `store.settings` | Admin (`_assert_mode_switch_admin`) | store connected, currently `mode1` | sets `switch_in_progress`+nonce, enqueues `fulfillment_mode_switch_scan`; scan completes/aborts async | `AccessError` if not admin; **idempotent no-op** if already `mode2` |
| `action_rollback_to_mode1()` | `store.settings` | Admin | any time (always allowed) | sets `mode1`, clears switch flag, cancels in-flight `fulfillment_mode2_evaluation` jobs | `AccessError` if not admin |
| `action_release_fulfillment_review(reason=False)` | `fulfillment.binding` | Reviewer **or** Admin (`_release_blocked_mutation`) | exactly one blocked mutation for the binding; pre-C2 (no attempt) **or** `failed_clean` attempt | supersedes the blocked job → one `manual_sync` replacement job | `AccessError` (role); `UserError` (empty reason / not exactly one / **post-C2 uncertain → refused, reconcile-only** / lock contention) |
| `action_import_tracking()` | `inbound.evidence` | Operator/Reviewer/Admin (`_assert_reviewer`) | resolvable outgoing customer picking | writes `carrier_tracking_ref` (non-stock); marks evidence `acknowledged` | `AccessError`; `UserError` if no picking resolves |
| `action_acknowledge_external()` | `inbound.evidence` | Operator/Reviewer/Admin | — | marks evidence `acknowledged` | `AccessError` |
| `action_validate_proposed()` | `inbound.evidence` | Reviewer **or** Admin | 16/16 Mode-2 checklist passes (Q6 carrier guard) | applies the exact local action; else held for review | `AccessError`; `UserError` if checklist fails or held |

> **Mode switching is NOT a job type.** `fulfillment_review_release` is NOT a job
> type. These are sanctioned actions delegating to accepted service helpers.

---

## 7. Internal/private methods U1 must NEVER invoke

All of the following are `_`-prefixed engine internals (Layer 2 / dispatch / scans
/ mode2 / strategies). U1 renders their **effects** (jobs, evidence, bindings,
mutation attempts) but never calls them:

- Dispatch/handlers: `_get_handlers`, `_get_replay_policies`, `_get_reconciliation_strategies`, `_handle_fulfillment_*` (picking_admission, tracking_admission, mutation_reconcile, inbound_observation, reconciliation_check, reconnect_catchup, mode_switch_scan, mode2_evaluation), `_handle_fulfillment_mutation_placeholder`, `_recover_pre_c2_failure`.
- Strategies (create/tracking): `_prepare_local_*`, `_prepare_preconditions_*`, `_transport_*`, `_classify_direct_*`, `_reconcile_*`, `_apply_consequence_*`.
- Mode 2 engine: `_evaluate_mode2`, `_apply_mode2`.
- Review-release internals: `_release_blocked_mutation` (call the **public** `action_release_fulfillment_review` instead), `_find_single_blocked_mutation`, `_handoff_replacement`.
- Enqueue/observation seams: `_enqueue_once`, `_enqueue_picking_admission`, `_enqueue_tracking_admission`, `_observe_fulfillment`, `_read_*` (reader), scan/cron internals.

**Rule for U1:** every button wires only to §6. No U1 code enqueues jobs, creates
mutation attempts, writes protected/snapshot fields, or reads Shopify.

---

## 8. Security groups (exact XML ids) and the ACL matrix

Groups (source: `core/security/shopify_connector_security.xml`):
`shopify_connector_core.group_shopify_connector_auditor`,
`...group_shopify_connector_operator`,
`...group_shopify_connector_reviewer`,
`...group_shopify_connector_admin`.

Fulfillment ACLs (`security/ir.model.access.csv`) — only the two review-workspace
models carry rows; strategy/scan/mode2/service models are Abstract (no table):

| Model | auditor | operator | reviewer | admin |
|---|---|---|---|---|
| `fulfillment.binding` | R | R,C | R,W | R,W,C |
| `fulfillment.inbound.evidence` | R | R,C | R,W | R,W,C |
| `fulfillment.inbound.evidence.line` | R | R,C | R,W | R,W,C |

No `unlink` for any role. Multi-company `ir.rule` scopes binding/evidence to the
bound picking's / order's company (global rules; `sudo` bypasses).

**SEC-2 interaction:** SEC-2 (see `u1-sec2-preflight-ruling.md`) layers two
customer-facing roles (`Connector User`, `Connector Administrator`) **on top of**
these four via `implied_ids` (Option M-A, additive, no XML-ID rename). The four
groups above **persist** as internal capability primitives; U1 gating on them
stays valid post-SEC-2 (User ⇒ operator∪reviewer∪auditor; Administrator ⇒ all).

---

## 9. Safe-display vs sensitive fields (the redaction contract for U1)

**Never render in U1** (transport/idempotency evidence — `shopify.connector.mutation.attempt`):
`remote_mutation_intent` (Json), `preconditions_snapshot` (Json),
`business_intent_fingerprint`, `exact_request_fingerprint`, `shopify_idempotency_key`,
`idempotency_valid_until`, `remote_evidence_refs` (Json), `attempt_token`,
`expected_store_identity`, `expected_connection_generation`. Also never render the
`fulfillment_mode_switch_nonce`, and never surface raw tokens/credentials (these
live on the store credential path, redacted by core).

**Safe mutation-attempt summary for U1 lineage:** `mutation_domain`,
`observed_outcome`, `resolution_disposition`, `resolution_source`,
`resolution_reason` (text), `resolution_uid`, `resolution_at`,
`inconclusive_reconciliation_count`, `transport_attempted`, `created_at`,
`transport_at`, `resolved_at`. (Show *that* a request happened and its disposition
— never the request body, fingerprint, or key.)

**Guarded JSON fields** (`state_snapshot`, `tracking_*_snapshot`,
`shopify_fulfillment_order_gids`): parse and render structured chips/links; never
a raw text dump.

---

## 10. Product-doc vs code vocabulary reconciliation (invented-value guard)

The pre-implementation product docs contain vocabulary that **differs from the
shipped Wave 4 code**. U1 must bind to the **code** values (§5). Superseded product
strings (do **not** use in views/prompts):

| Product doc value | Doc source | Code-authoritative value |
|---|---|---|
| origin `external_service` | `fulfillment-operating-modes.md` §3 | `external_app` |
| origin `carrier_event_only` | same | (no such origin class; carrier milestones surface via `delivered_inconsistency` / status fields) |
| origin unknown (unnamed) | same | `external_unknown` |
| review reason `over_fulfillment` | same §4 (cond. 6) | `quantity_overrun` |
| reconciled state `under_review` | same §5 | `review` |
| reconciled state `auto_matched` | same §5 | (absent — not a stored state) |
| reconciled state `rejected` | same §5 | (absent) |

These are logged as **TD (documentation)** in `u1-risks-and-open-questions.md` and
must be reconciled in the U1 copy deck, which maps each **code** value to an
operator label.

---

## 11. Gap classification (per §6 of the Gate A prompt)

| Surface | Status | Classification |
|---|---|---|
| Mode display + admin mode-change actions | Present (`fulfillment_operating_mode`, `action_start_mode2_switch`, `action_rollback_to_mode1`) | **Ready for U1** |
| Review workspace record + 3 review actions | Present (`inbound.evidence` + actions) | **Ready for U1** |
| Fulfillment binding + review-release | Present | **Ready for U1** |
| Job/mutation/tracking lineage | Present (job, mutation.attempt, binding, picking) | **Ready for U1** |
| Mode-switch **consequences preview** (blocked/running work, review-required, unresolved-external count) as a single backend read | **ABSENT** — the data exists (query jobs/evidence) but no single accepted read-model/method returns a "consequences summary" | **Optional-later** for U1: U1 composes it from bounded ACL-safe searches in the view/wizard layer (no new business logic); a future read-only aggregate endpoint could be added if needed — **decision for control room** |
| Mode-switch **history list** | Partial — only `fulfillment_last_mode_switch_at/uid` scalars exist (no per-switch log model) | **Optional-later**: U1 surfaces the scalars + the `fulfillment_mode_switch_scan` job log; a dedicated history model is out of U1 scope |
| Read-only aggregate/dashboard endpoint for fulfillment | ABSENT in fulfillment addon (U0's dashboard aggregate lives in core, generic) | **Out of U1 scope** (dashboards are U0/later); U1 uses standard list/search views with bounded defaults |
| Any Shopify read/mutation from UI | Forbidden by design | **Out of scope** |

**No missing surface is inferred.** Where U1 needs a composite (e.g. the switch
consequences), it is built by **reading** existing ACL-safe records with bounded
domains in the view/wizard layer — never by adding backend business logic.
