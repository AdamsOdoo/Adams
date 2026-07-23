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
- **Addon inspected:** `addons/shopify_connector_fulfillment/**` (15 model modules
  + `models/__init__.py`, 1 ACL CSV, 1 security XML, 1 cron XML; verified at
  `2d9cff0`) plus consumed core surfaces in `addons/shopify_connector_core/**`.
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
| `fulfillment_status_raw` | Char | — | Safe (**A4** badge source — §12) |
| `fulfillment_status_normalized` | Char | — | Safe (**A4** badge source — §12) |
| `fulfillment_status_is_success` | Boolean | — | Safe (A4 automation flag) |
| `display_status_raw` | Char | — | Safe (**A7** `FulfillmentDisplayStatus`, display-only per code — §12; **not** A5) |
| `display_status_normalized` | Char | — | Safe (**A7**, display-only; stored = raw — §12) |
| `state_snapshot` | Text (JSON) | — | **Guarded** — raw snapshot (A4+A7 only); render parsed/summarised, never raw dump |
| `schema_warning` | Boolean | — | Safe (unknown-enum flag — §12) |
| `delivered_inconsistency` | Boolean | — | Safe (**A5** delivered-inconsistency seam; declared but data-inert at `2d9cff0` — §12 / risks) |
| `tracking_snapshot` | Text (JSON) | — | **Guarded** — **A5** carrier evidence (parsed `trackingInfo`); parse to chips, not a raw dump — §12 |
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

### 5.8 Core `error_class` (19) / `manual_review_subreason` (9)
`error_class` (**19 members** = 6 base + the 9 `manual_review_subreason` values +
4 tail; verified in `core/models/shopify_connector_job.py` `ERROR_CLASS_SELECTION`):
`shopify_throttling_rate_limit`, `shopify_temporary_server_network`,
`shopify_permission_scope_auth`, `shopify_user_errors_validation`, `odoo_validation_configuration`,
`mapping_missing`, **+ the 9 subreasons**, + `financial_total_mismatch`, `data_shape_schema_mismatch`,
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

Every action mirrors a **server-side** group check. U1 **customer-facing
visibility** gates on the two SEC-2 roles (Connector User / Connector
Administrator); the **server** enforces the internal capability group shown in
"Server gate" below (the two roles resolve to it via implied-group closure). A
hidden button is never the security control (UI/ACL agreement — wave-5 DoR
hard-stop 9): a denied caller gets `AccessError` with zero side effects.

| Action | Model | Server gate | Legal precondition | Legal result | Refusal behaviour |
|---|---|---|---|---|---|
| `action_start_mode2_switch()` | `store.settings` | Admin (`_assert_mode_switch_admin`) | currently `mode1` (idempotent no-op if already `mode2`). *Note: the action itself enforces only the admin gate + the already-`mode2` no-op; a `store connected` check is applied upstream/by the reconciliation cron, **not** by this action — the wizard must not re-derive or gate on it.* | sets `switch_in_progress`+nonce, enqueues `fulfillment_mode_switch_scan`; scan completes/aborts async | `AccessError` if not admin; **idempotent no-op** if already `mode2` |
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

**SEC-2 interaction (binding SEC-2-first — D-P0-2, control-room comment
`5056513213`):** SEC-2 introduces the two customer-facing roles via `implied_ids`
(Option M-A, additive, no XML-ID rename) — **Connector User** = the **new**
`group_shopify_connector_user` (implies operator∪reviewer∪auditor); **Connector
Administrator** = the **existing** `group_shopify_connector_admin`, re-purposed
(implies User → all). U1 **customer-facing UI visibility gates on these two roles**;
the four internal capability groups above **persist as the server-side authorization
primitives** the two roles resolve to. SEC-2 defines the final two-role group XML
IDs (notably the new `group_shopify_connector_user`); U1 must **not** treat that XML
ID as existing before SEC-2 merges runtime-green, and must **not** gate
customer-facing visibility directly on the four internal groups. U1 tests prove
**both** layers (two-role UI visibility + direct-RPC server denial through the
internal groups).

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
| origin `carrier_event_only` | same | (no such origin class; carrier milestones surface via `delivered_inconsistency` + parsed `tracking_snapshot` — **not** the A7 `display_status_*` fields; see §12) |
| origin unknown (unnamed) | same | `external_unknown` |
| review reason `over_fulfillment` | same §4 (cond. 6) | `quantity_overrun` |
| reconciled state `under_review` | same §5 | `review` |
| reconciled state `auto_matched` | same §5 | (absent — not a stored state) |
| reconciled state `rejected` | same §5 | (absent) |

These are logged as **TD (documentation)** in `u1-risks-and-open-questions.md` and
must be reconciled in the U1 copy deck, which maps each **code** value to an
operator label.

**Residual un-annotated superseded-vocabulary locations (outside this reset's
allowed files — logged, not edited here).** Two documents outside the Wave 5 U1
Gate A allowed-files set still carry the superseded `under_review` string
un-annotated: `docs/05-qa/fulfillment-mode-uat-matrix.md` (scenario **UAT-FM-3.3**)
and `docs/02-product/premium-ux-master-specification.md` (**§3 S21**). They are
recorded here and in **TD-003** as residual locations for a separately-authorized
product-doc reconciliation pass; the code value is `review` (§5.3). This reset does
**not** edit those two files (they are not in the allowed set — see
`u1-gate-a-handoff.md`), and their presence does not weaken the code-authoritative
rule.

---

## 11. Gap classification (per §6 of the Gate A prompt)

| Surface | Status | Classification |
|---|---|---|
| Mode display + admin mode-change actions | Present (`fulfillment_operating_mode`, `action_start_mode2_switch`, `action_rollback_to_mode1`) | **Ready for U1** |
| Review workspace record + 3 review actions | Present (`inbound.evidence` + actions) | **Ready for U1** |
| Fulfillment binding + review-release | Present | **Ready for U1** |
| Job/mutation/tracking lineage | Present (job, mutation.attempt, binding, picking) | **Ready for U1** |
| Mode-switch **consequences display** (static consequences + a bounded informational count of open review cases) | **No single backend "consequences summary" read-model exists** (the data exists via jobs/evidence queries) | **Display-and-delegate ONLY** for U1: the wizard shows STATIC consequences + a bounded, ACL-safe, **non-authoritative** informational count (a `search_count` of `inbound.evidence reconciled_state='review'`), labelled non-authoritative; it does **not** compute "review-required", classify blockers, or decide eligibility — the server reconciliation scan is authoritative. An authoritative dynamic preflight would be a **separate backend read-model task (D-P2-5)**, never U1 wizard logic |
| Mode-switch **history list** | Partial — only `fulfillment_last_mode_switch_at/uid` scalars exist (no per-switch log model) | **Optional-later**: U1 surfaces the scalars + the `fulfillment_mode_switch_scan` job log; a dedicated history model is out of U1 scope |
| Read-only aggregate/dashboard endpoint for fulfillment | ABSENT in fulfillment addon (U0's dashboard aggregate lives in core, generic) | **Out of U1 scope** (dashboards are U0/later); U1 uses standard list/search views with bounded defaults |
| Any Shopify read/mutation from UI | Forbidden by design | **Out of scope** |

**No missing surface is inferred.** Where U1 needs a composite (e.g. the switch
consequences), it is built by **reading** existing ACL-safe records with bounded
domains in the view/wizard layer — never by adding backend business logic, and
never used to decide eligibility, classify blockers, or determine "review required"
(those stay server-authoritative; the wizard is display-and-delegate only).

---

## 12. Authoritative status-source & badge matrix (CANONICAL — source-verified at `2d9cff0`)

> **This §12 is the single canonical source-of-truth for every U1 status badge,
> operational visualization, and status-derived surface.** UX/IA §8, the acceptance
> & test matrix, the locked implementation prompt, and the fulfillment/tracking
> prototypes all reference this matrix and **must not re-derive or contradict it**.
> Governing rule (control-room ruling `5058042330`): **never infer a field merely
> because Shopify exposes the enum** — a badge exists in U1 only when an exact
> backing field or sanctioned read seam exists at Wave 4 head
> `2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a`. Status layers are **never merged or
> silently renamed** (status model §1/§9).
>
> The Shopify platform exposes **seven Layer-A enum families (A1–A7)** within the
> status model's four-layer (Layer A/B/C/D) taxonomy. Wave 4 code persists only a
> **subset** of them; the rest are deferred or out of U1. This matrix records what
> is actually backed, not what Shopify could expose.

### 12.1 Backend source & availability

| # | Layer / family | Authoritative source (model) | Exact backing field / read seam | At `2d9cff0` | Raw | Normalized | Source class | U1 disposition |
|---|---|---|---|---|---|---|---|---|
| L0 | **Odoo delivery** | `stock.picking` (Odoo) | `stock.picking.state` | **yes** | n/a (Odoo enum) | n/a | **automation authority** — real stock movement | **Implemented** — lineage node; the sole authority for stock completion |
| A1 | `OrderDisplayFulfillmentStatus` (order roll-up) | `shopify.connector.order.binding` (`_sale`) | `order_binding_id.shopify_fulfillment_status_snapshot` (Char) — indirect, via the evidence→order-binding relation | **yes** (indirect seam) | yes | **no** normalized A1 field | display only | **Represented indirectly** — surfaced through the order-binding lineage; **not** the review-case primary badge |
| A2 | `FulfillmentOrderStatus` (FO work-state) | Shopify FulfillmentOrder — **not persisted by the connector** | **NONE** (no field on `inbound.evidence` or `fulfillment.binding`; `shopify_fulfillment_order_gids` is the FO-GID list, **not** the FO status) | **NO** | — | — | (Shopify: automation input — **not captured**) | **DEFERRED — BACKEND READ SEAM NOT AVAILABLE.** No standalone A2 badge in U1; not inferred from any other layer |
| A3 | `FulfillmentOrderRequestStatus` | Shopify FO `requestStatus` — not persisted | NONE | **NO** | — | — | (Shopify: display + gating — not captured) | **Outside U1** (no seam) |
| A4 | `FulfillmentStatus` (fulfillment result) | `shopify.connector.fulfillment.inbound.evidence` | `fulfillment_status_raw`, `fulfillment_status_normalized`, `fulfillment_status_is_success` | **yes** | yes (`node['status']`) | yes (`A4_FULFILLMENT_STATUS_KNOWN`: SUCCESS/CANCELLED/ERROR/FAILURE + deprecated OPEN/PENDING) | **automation authority** (Mode 2 condition 2 gate) **+ display** | **Implemented** — primary fulfillment-result badge; `_is_success` is the automation flag |
| A5 | `FulfillmentEventStatus` (carrier milestone) | `...inbound.evidence` (+ review reader) | `delivered_inconsistency` (Boolean) **+** `tracking_snapshot` (Text/JSON of `trackingInfo`). **No normalized A5-enum field exists.** | `tracking_snapshot` **yes** (populated from `trackingInfo`; **read** in `review.py:160`); `delivered_inconsistency` **declared but never written `True`** by any Wave-4 path (data-inert — see risks) | `tracking_snapshot` = raw `trackingInfo` (company/number/url) only; **no** raw A5-event field | **no** normalized A5 enum | **display only** + `delivered_inconsistency` is a **derived warning/review state** | **Represented indirectly / partial** — render parsed `tracking_snapshot` chips + the delivered-inconsistency case; **never consume the A7 `display_status_*` fields**; a full normalized A5 milestone timeline is **deferred** (no backing enum) |
| A6 | `FulfillmentHoldReason` | Shopify hold — not persisted | NONE | **NO** | — | — | (Shopify: display only — not captured) | **Outside U1** (no seam) |
| A7 | `FulfillmentDisplayStatus` (display roll-up) | `...inbound.evidence` | `display_status_raw`, `display_status_normalized` — **both** = `node['displayStatus']` (`Fulfillment.displayStatus`) | **yes** | yes | stored **= raw** (no normalization applied at `2d9cff0`) | **display only — never an automation input** (code comment, `inbound_evidence.py:106`) | **Implemented** — A7 display-status badge, **display-only**; **never labelled or iconized as a carrier milestone** (it is not A5) |
| — | State snapshot (audit) | `...inbound.evidence` | `state_snapshot` (Text/JSON — **only** `A4_FulfillmentStatus` + `A7_displayStatus`) | **yes** | yes (raw A4+A7) | n/a | **audit only** | **Lineage/detail** — parsed chips, never a raw dump (§9 guarded) |
| — | Unknown-value flag | `...inbound.evidence` | `schema_warning` (Boolean; set `not is_known` for an unknown A4 value) | **yes** | n/a | n/a | **derived warning** | **Implemented** — "Unknown status (raw value)" chip; fails closed, never success |
| C1 | Connector reconciliation | `...inbound.evidence` | `reconciled_state` (5: observed/review/acknowledged/applied/superseded) | **yes** | n/a | n/a | connector reconciliation state | **Implemented** — reconciliation badge |
| C2 | Review / error condition | `...inbound.evidence` + core `shopify.connector.job` | `review_reason` (20) on evidence; `error_class` (**19**) / `manual_review_subreason` (9) / job `state` (10) on the job | **yes** | n/a | n/a | **derived review/error state** (operator + audit) | **Implemented** — review-reason badge + job error/state |
| C3 | Origin classification | `...inbound.evidence` | `origin_class` (4) + `origin_confirmed` (Boolean) | **yes** | n/a | n/a | automation input (origin gating) + display | **Implemented** — origin chip |
| C4 | Mutation-attempt outcome | core `shopify.connector.mutation.attempt` | `observed_outcome` (4) + `resolution_*` (safe summary — §9) | **yes** | n/a | n/a | **audit / lineage** (safe summary only) | **Lineage/detail** — never the intent/fingerprint/idempotency-key fields (§9) |
| C5 | Binding fulfillment status | `shopify.connector.fulfillment.binding` | `shopify_status_snapshot` (Char) + `shopify_status_normalized` (Char) | **yes** | yes | yes | display only (binding-level snapshot) | **Represented indirectly** — binding lineage badge |

### 12.2 Visual / badge contract (per retained, rendered layer)

Labels/icons are **semantic placeholders** reconciled to the platform FontAwesome
set (P9) at implementation (status model §9). Severity tokens reuse the U0 layer
(calm/info/warning/critical/unknown).

| Layer | Operator label family | Icon family (semantic) | Severity rule | Unknown value | Empty / unavailable |
|---|---|---|---|---|---|
| L0 Odoo delivery | Draft / Waiting / Ready / **Done** / Cancelled | `truck` / `check-circle` | calm→done; info→in-progress | n/a (fixed Odoo enum) | no picking → "—" |
| A1 order roll-up | Not shipped / Partially shipped / Fully shipped / … (status model §2) | `truck-outline` / `truck-half` / `truck-check` | per §2 | `badge-unknown` / `help-circle` (§7) | no snapshot → no badge |
| A4 fulfillment result | Shipped (confirmed) / Cancelled / Error / Failed | `check-circle` / `cancel` / `alert-circle` / `close-octagon` | calm / warning / critical (§4) | "Unknown: RAW", `schema_warning`, never success | no status → "—", `_is_success=false` |
| A5 carrier milestone (tracking + delivered-inconsistency **only**) | tracking chips (carrier/number); **Delivered per carrier — Odoo delivery not validated** (delivered-inconsistency) | `truck-fast` / `package-check`; inconsistency → `alert-decagram` | tracking chips info/calm; **delivered-inconsistency → critical, pinned** (§8) | unknown milestone → §7 ("unknown milestone") | no `trackingInfo` → no chips; `delivered_inconsistency=false` → no inconsistency badge |
| A7 display status (roll-up, display-only) | e.g. Marked as fulfilled / Submitted / Label printed / In transit / Delivered — **shown as "Shopify display status"**, never as a carrier event | `tag` / `information-outline` (distinct from A5 `truck-*`) | calm/info; **never critical by itself** | `badge-unknown` (§7) | no value → "—" |
| C1 reconciliation | Observed / Review Case Open / Acknowledged / Applied / Superseded | `eye` / `hand` / `check` | review → warning/critical; applied → calm | n/a (fixed selection) | default `observed` |
| C2 review reason / error | the 20 review reasons / 19 error classes (operator labels via copy deck) | `tag` / `alert-*` | per reason severity | `unknown_status_value` review reason; `unknown_system_error` | no reason → not a review case |
| C3 origin | Connector-Created / External — Merchant / External — App/Service / External — Unknown Origin | `link` / `store` / `apps` / `help` | neutral/info | `external_unknown` handles the unknown case | default `external_unknown` |
| — unknown-value | Unknown status (raw value) | `help-circle` | warning | (this row **is** the unknown handler) | — |

### 12.3 Binding invariants (enforced by acceptance A22)

- **One badge per layer; layers never merged** (status model §1/§9).
- **Word + icon on every consequential state; colour is never the only signal.**
- **A5 and A7 use clearly different labels and icons** — A7 is the Shopify
  *display-status roll-up* (`display_status_*`), A5 is a *carrier milestone*
  (`tracking_snapshot` + `delivered_inconsistency`). A7 values
  (`MARKED_AS_FULFILLED`, `SUBMITTED`, `LABEL_PRINTED`, `IN_TRANSIT`, `DELIVERED`, …)
  are **never** rendered under a carrier-milestone badge.
- **A4 success ≠ Odoo stock completion; A7 roll-up ≠ carrier delivery.** Only
  `stock.picking.state = done` proves stock movement.
- **`delivered_inconsistency` stays high-visibility when set** (§8), but is
  **data-inert at `2d9cff0`** (declared, never written `True`; likewise
  `review_reason='delivered_not_validated'`) — U1 renders the flag/reason when the
  backend populates it and must not synthesize A5 state from A7 (see
  `u1-risks-and-open-questions.md`).
- **No badge without backing evidence** — A2/A3/A6 are deferred/outside U1; no
  phantom badge.
- **Guarded JSON** (`state_snapshot`, `tracking_snapshot`, `tracking_*_snapshot`,
  `shopify_fulfillment_order_gids`) is parsed to chips/links, **never** dumped; the
  §9 never-render set is never surfaced.
