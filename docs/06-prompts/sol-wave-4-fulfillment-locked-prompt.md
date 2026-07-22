# Sol — Wave 4 Fulfillment/Tracking Implementation (Gate B) — LOCKED PROMPT

**`LOCKED CANDIDATE — NOT ISSUED; REQUIRES CHATGPT CONTROL-ROOM ACCEPTANCE`**

> This is a **future** Gate B implementation prompt. It is **not issued** and
> authorizes **no** implementation. It becomes usable only after the ChatGPT
> control room (a) accepts the Wave 4 Gate A package — the Task 014 packet + its
> §10 **and §11** addenda, [`../04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md`](../04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md),
> the DoR, and this prompt — (b) accepts the **applied DEC-038 Q1–Q8 rulings** (PR
> #188 comment `5041620950`; no longer open), (c) verifies the base SHA, and (d)
> explicitly opens the Wave 4 Gate B fulfillment gate and issues this prompt.
> Producing it is Gate A governance work; it accepts nothing.
>
> **Bounded control-room correction (2026-07-22):** the uncertain-outcome contract is
> **reconcile-only** (no resend from read absence — §4/§5); the modular file map and
> exact test filenames are frozen (§2/§5); pagination, source-guard precision,
> lifecycle `ondelete`, staff-permission (NOT_PROVEN), and `store.api_version` policy
> are applied. Basis: PR #188 comment `5041620950`.
>
> **Final control-room micro-correction (2026-07-22):** post-C2 `NOT_APPLIED` **never
> authorizes a resend** (post-C2 = **APPLIED / INCONCLUSIVE** only); the taxonomy is
> frozen at **exactly ten job types** (§11.2) with **one shared
> `fulfillment_mutation_reconcile`** (no per-domain reconcile; **no** remote-effect-scope
> inheritance); **`fulfillment_review_release` is not a job type** (sanctioned-helper
> release); **no Wave 4 `webhook` source**; the `fulfillment_tracking_change`
> trigger-origin uses the **dedicated** `_normalize_tracking_change_trigger_origin_on_uninstall`
> callable (not the job-type sink). Basis: PR #188 comment `5042183642` / issue #186
> comment `5042185019`.

---

## 0. Role, authority, base

You are the Wave 4 Gate B implementation worker for
`shopify_connector_fulfillment`. **ChatGPT is the control room** (scope governor,
acceptance, merge authority); the product owner is the business authority; you may
**not** self-accept, mark ready, or merge (issue #186 comment `5038326525`).

- **Repository:** `AdamsOdoo/Adams`.
- **Required base:** `mvp/program-integration@<ACCEPTED_BASE_SHA>` — the current
  integration head after an identity gate (candidate base at Gate A authoring time:
  `ab4f12f5a6857b2f3318ffc3b3f5f371307938bc`; **STOP on drift**; never branch from
  `main`, `Shopify-connector`, a checkpoint ref, or an old wave branch).
- Branch: one focused Wave 4 Gate B branch/PR; draft; unmerged.
- **CV-013 (#185) remains open and critical** — do not close/downgrade it.

## 1. Objective

Implement the complete Wave 4 fulfillment/tracking **backend** — both Mode 1 and
Mode 2 — exactly per the accepted Task 014 packet (D-014-1..8 + the §9/§10/§11
addenda) and DEC-038 (incl. the §7 correction + Q1–Q8 rulings), running every Shopify
mutation under the accepted DEC-036/DEC-031 Layer 2 substrate. No UI (Wave 5). No live
Shopify mutation in Gate B.

## 2. Exact allowed files (candidate allowlist — validate; no wildcards)

**New addon `addons/shopify_connector_fulfillment/` — enumerated modular production
map (NO `**`; NO giant service file; one responsibility per file):**
- `__init__.py`, `__manifest__.py`
  (`depends=['shopify_connector_core','shopify_connector_sale','stock_delivery','sale_stock']`)
- `models/__init__.py`
- **Bindings / evidence:**
  - `models/shopify_connector_fulfillment_binding.py` — the D-014-1 binding
    (`shopify_gid`=Fulfillment GID; `UNIQUE(store_id,shopify_gid)`+`UNIQUE(store_id,picking_id)`)
  - `models/shopify_connector_fulfillment_inbound_evidence.py` — per-fulfillment +
    per-line evidence (origin class, reconciled-quantity ledger, raw+normalized state)
- **Store / settings extension:**
  - `models/shopify_connector_store_settings.py` — `fulfillment_operating_mode`,
    `fulfillment_notification_confirmed`, `fulfillment_last_reconciliation_at`,
    mode-switch state fields
- **Job / dispatch extensions (add-only seams):**
  - `models/shopify_connector_job.py` — the **ten** frozen `job_type` values (§11.2)
    `selection_add` with the job-type-sink `ondelete` `_reassign_to_historic_job_type`,
    **and** the `trigger_origin` value `fulfillment_tracking_change` `selection_add` with
    its **dedicated** `ondelete` callable
    `_normalize_tracking_change_trigger_origin_on_uninstall` (**not** the job-type sink —
    it normalizes the removed value to the core value `fulfillment_picking_validation`,
    audits provenance, and respects the `job_source`/`trigger_origin` constraint);
    `_domain_flag_for_job_type` override; own `_compute_operation_scope_key` for the **two
    mutation types only** (the Q1 literals) — the shared `fulfillment_mutation_reconcile`
    inherits **no** remote-effect scope
  - `models/shopify_connector_job_dispatch.py` — `_get_reconciliation_strategies` /
    `_get_handlers` / `_get_replay_policies` add-only merges; local admission/scan
    handler dispatch
- **Stock trigger extension:**
  - `models/stock_picking.py` — `_action_done` override (Mode 1 admission enqueue,
    adopting `sale_stock` pickings — Q2) + tracking-change enqueue hook
- **Outbound admission / orchestration (no mutation):**
  - `models/shopify_connector_fulfillment_admission.py` — `fulfillment_picking_admission`
    + `fulfillment_tracking_admission`: per-FO decomposition, enqueue create/update jobs
- **Shopify read / pagination / identity matching (read-only):**
  - `models/shopify_connector_fulfillment_reader.py` — **cursor-paginated** FO /
    fulfillment / line-item reads (§8 pagination), the FO-line-item-GID **2-hop**
    matching, location resolution via the **core** `shopify.connector.location` cache
    (never `location.mapping`; Q3 read-only refresh service lives here)
- **Layer 2 mutation strategies (one file per mutation domain — never both in one):**
  - `models/shopify_connector_fulfillment_create_strategy.py` — the 7-callback
    strategy for `fulfillment_create` + the create-domain reconcile read invoked by the
    **shared** `fulfillment_mutation_reconcile` (post-C2: **APPLIED / INCONCLUSIVE only**,
    no resend)
  - `models/shopify_connector_fulfillment_tracking_strategy.py` — the 7-callback
    strategy for `fulfillment_tracking_update` + the tracking-domain reconcile read
    invoked by the same shared `fulfillment_mutation_reconcile`
- **Inbound observation / origin classification:**
  - `models/shopify_connector_fulfillment_inbound.py` — inbound observation +
    origin-classification evidence stack
- **Mode 1 review / Mode 2 evaluation (separate from matching, mutation, scans):**
  - `models/shopify_connector_fulfillment_review.py` — Mode 1 review-case actions
    (import tracking / acknowledge / explicit validate) + the review-release **sanctioned
    service helper** (public binding action → private helper; **not** a job type)
  - `models/shopify_connector_fulfillment_mode2.py` — the 16-condition Mode 2
    evaluator + local application (validate picking); **Q6 carrier fail-closed**
- **Reconciliation / reconnect / mode-switch scans:**
  - `models/shopify_connector_fulfillment_scans.py` — `fulfillment_reconciliation_check`
    + `fulfillment_reconnect_catchup` + `fulfillment_mode_switch_scan` handlers
- **Readiness evaluation:**
  - `models/shopify_connector_readiness_check.py` — `_get_checks` write-scope +
    **staff-permission-axis (NOT_PROVEN)** + **API-version-compat** append (add-only)
- **Security:** `security/ir.model.access.csv`,
  `security/shopify_connector_fulfillment_security.xml`
- **Cron / data:** `data/shopify_connector_fulfillment_cron.xml` (reconciliation cron,
  `noupdate=1`)
- **Tests:** `tests/__init__.py` + the **exact** files enumerated in §5.

> **No single file may own** matching **and** both mutation callbacks **and** the full
> Mode 2 engine **and** inbound reconciliation **and** mode switching **and** review
> release **and** cron scanning — those are the separate files above. A file may carry
> more than one *closely related* responsibility only with a written justification at
> Gate B. **No production or test file outside this enumerated set** may be created
> without an explicit control-room allowlist amendment — a **hard stop**.

**The one named cross-module core edit (D-014-2 / TD-002):**
- `addons/shopify_connector_core/models/shopify_connector_readiness_check.py` —
  symbol **`REQUIRED_MVP_SCOPES`** only: swap `read_fulfillments` →
  `read_merchant_managed_fulfillment_orders` (nothing else in the file).
- `addons/shopify_connector_core/tests/test_readiness_check.py` — the matching
  assertion update only.

**Docs / QA (allowed):**
- `docs/05-qa/task-014-fulfillment-tracking-validation-results.md` (NEW)
- `docs/05-qa/fulfillment-mode-uat-matrix.md` (evidence rows)
- `docs/05-qa/technical-debt-register.md` (TD-002 → Resolved)
- `docs/05-qa/architecture-review-log.md` (append the Gate B row)
- `docs/01-research/research-handoff.md` (top entry + learning loop)
- `docs/07-implementation-plan/mvp-program-state.md`, `docs/05-qa/mvp-acceptance-matrix.md` (Wave 4 rows)

Any cross-module edit beyond the one named core edit must identify the exact file,
symbol, demonstrated need, and regression responsibility, and requires a control-room
amendment (e.g. DEC-038 Q5 on `cod_fulfillment_state` ownership — **default: no sale
edit; fulfillment-owned binding**).

## 3. Exact forbidden files / behavior

- Every other `shopify_connector_core` file and test (except the two named above).
- Every `shopify_connector_product`, `shopify_connector_sale`,
  `shopify_connector_inventory` file — **read only where allowed; edit none**;
  **never import or query `shopify.connector.location.mapping`**.
- `fulfillmentOrderMove` / `fulfillmentOrderHold` / `fulfillmentOrderReleaseHold` /
  every `FULFILLMENT_ORDERS_*` subscription (holds are read-only, D-014-5).
- Legacy `fulfillmentCreateV2` / `fulfillmentTrackingInfoUpdateV2` and any legacy
  REST/Order-Fulfillment path (RA-022).
- Raw HTTP/GraphQL transport bypassing `execute_business` / the accepted API client.
- Refunds, returns/RMA, Shopify-side reverse-fulfillment, product/media export,
  webhooks, OAuth, UI, SEC-2, analytics, `orderMarkAsPaid`, Task 013B.
- `adams_base`; `.github/workflows/*`; `requirements*.txt`; `Dockerfile`.
- **No live Shopify mutation in Gate B.**

## 4. Static / source-guard plan (must be enforced by tests)

Guards scan **exact production paths and GraphQL constants**, not the whole repository
(tests and docs must be free to *name* forbidden surfaces to assert they are
forbidden):

- **No legacy fulfillment surface in production** — `fulfillmentCreateV2` /
  `fulfillmentTrackingInfoUpdateV2` (and any legacy REST/Order-Fulfillment path) must
  not appear in the fulfillment addon's **production GraphQL documents / call paths**
  (RA-022). Tests and docs **may** name them to assert absence.
- **RA-023 line-identity** — every fulfillment production path uses the explicit FO
  `lineItems` connection / `lineItemsByFulfillmentOrder` with an explicit line list;
  **no order-ID-only path** and **no omission-of-`fulfillmentOrderLineItems`** code
  path exists.
- **No `@idempotent`** in any fulfillment **operation string / production GraphQL
  constant** (fulfillment mutations are not on Shopify's 17-mutation list).
- **P0 no-resend-from-absence** — no fulfillment handler can reach a **second**
  `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate` from **any** post-C2 reconcile read
  result; a replacement send is reachable **only** from a proven
  `transport_attempted=false` (nothing sent) or a **synchronous `userErrors` clean
  rejection** — **post-C2 `NOT_APPLIED` is not an actionable Wave 4 verdict and never
  authorizes a resend**; the shared `fulfillment_mutation_reconcile` **cannot enqueue a
  mutation** (§5 tests prove read-absence→INCONCLUSIVE, the no-second-mutation
  source-path, and no-mutation-from-reconcile).
- **Frozen ten-job taxonomy / no webhook source** — the fulfillment job registry holds
  **exactly the ten §11.2 `job_type` values** (one shared `fulfillment_mutation_reconcile`;
  **no** per-domain `*_reconcile`; **no** `fulfillment_review_release` job type); **no
  Wave 4 job admits from `job_source='webhook'`** (webhooks forbidden this wave — §3).
- **Cursor pagination** — decision-critical reads use `pageInfo.hasNextPage`/
  `endCursor` with a fail-closed cap; **no fixed `first: N`** window is used to prove
  absence, select a target, or authorize a mutation.
- **Fixed vocabulary** — persisted `error_class`/`manual_review_subreason` values come
  **only** from the merged `ERROR_CLASS_SELECTION`/`MANUAL_REVIEW_SUBREASON_SELECTION`
  registries; **`over_fulfillment` (and any other new value) must not appear** (no
  17th error class, no new subreason).
- **No `qty_done` / `quantity_done`** field access (absent in Odoo 19 — use
  `stock.move.line.quantity`).
- **No inventory coupling** — no import/query of `shopify.connector.location.mapping`;
  location resolves via the core `shopify.connector.location` cache only.
- **No raw transport** — only `execute_business`; **exact GraphQL document shapes**
  fingerprinted deterministically (byte-identical C2↔wire).
- **Exact scopes + version** — `read_merchant_managed_fulfillment_orders` + conditional
  `write_merchant_managed_fulfillment_orders`; the `fulfill_and_ship_orders`
  **staff-permission axis (NOT_PROVEN, not inferred from scopes)**; all calls through
  **`store.api_version`** (no fulfillment-only pin, never `latest`; readiness blocks
  unsupported/unverified versions).
- **Mutation-context / operation-scope (Q1 literals) / protected-field enforcement**;
  allowed FO states + `supportedActions.CREATE_FULFILLMENT` gate.
- **No secret/PII logging** — recipient names never in fulfillment log messages;
  redaction via `_system_append`.
- **Exact file-boundary enforcement** — a repo guard that fails if any fulfillment
  production or test file appears outside the §2/§5 enumerated allowlist.

## 5. Unit-test plan — exact frozen filenames (each maps to behavior families)

Every behavior gets a **pass + fail-to-review** case. The filename list is
**exhaustive** (no additional test file without a control-room allowlist amendment):

- `tests/__init__.py`
- `test_fulfillment_binding.py` — D-014-1 schema; dual uniqueness; backorder-chain non-collision.
- `test_fulfillment_inbound_evidence.py` — per-fulfillment/per-line evidence layers; reconciled-quantity ledger; raw+normalized state.
- `test_fulfillment_trigger.py` — `_action_done` eligibility matrix; multi-step legs; backorder independence; **adopt `sale_stock` pickings (Q2)**; tracking-change hook; domain gating.
- `test_fulfillment_admission.py` — per-FO decomposition; **>1 FO per location**; enqueue lineage; `mapping_missing`/`ambiguous_match` routing.
- `test_fulfillment_reader_pagination.py` — **cursor pagination to completion**; fail-closed cap; duplicate-node/repeated-cursor/malformed-page; **partial page never = absence / never selects a target**.
- `test_fulfillment_matching.py` — **FO-line-item-GID 2-hop**; skip null-GID lines; qty ≤ `remainingQuantity`; explicit-line-list guard (RA-023).
- `test_fulfillment_location_resolution.py` — `assignedLocation.location`-null fallback; **core cache only, never `location.mapping`**; Q3 read-only refresh; fail-closed on unresolved/ambiguous.
- `test_fulfillment_create_strategy.py` — 7 callbacks; **no `@idempotent` source-guard**; `code_required=False` **positive-success-evidence** classifier; C1/C2/NET/C3; `supportedActions.CREATE_FULFILLMENT` gate; FO-status eligibility.
- `test_fulfillment_tracking_strategy.py` — in-place update; multi-number split; missing-ref-with-note; `notifyCustomer` persisted/never re-read (RA-009).
- `test_fulfillment_idempotency.py` — **P0**: reconcile-only after `transport_attempted=true`; post-C2 has only **APPLIED / INCONCLUSIVE** (**no post-C2 `NOT_APPLIED` replacement**); **read-absence→INCONCLUSIVE**; a replacement is reachable **only** from `transport_attempted=false` or a synchronous `userErrors` clean rejection; the shared `fulfillment_mutation_reconcile` **cannot enqueue a mutation**; **no second mutation from a read miss**; **no-tracking uncertainty fails closed**; **possible-`notifyCustomer` uncertainty fails closed**; `INCONCLUSIVE_RECONCILIATION_CAP=3`→`duplicate_risk`; duplicate prevention.
- `test_fulfillment_inbound_classification.py` — origin evidence stack; own-GID precedence; unknown→external default.
- `test_fulfillment_mode2_engine.py` — **all 16 conditions** (pass + fail-to-review each); **Q6 carrier fail-closed** before validation; deterministic split; no partial automation on ambiguity.
- `test_fulfillment_mode_switch.py` — state machine; idempotent re-confirm; rollback; in-flight Layer 2 jobs **not** cancelled by the switch.
- `test_fulfillment_scans.py` — reconciliation-scan idempotency (uuid nonce); **reconnect catch-up → review in both modes**; watermark.
- `test_fulfillment_review_release.py` — Mode 1 actions (import tracking/acknowledge/explicit validate); the review-release **sanctioned service helper** (public binding action → private helper; **not a job type**) releasing exactly one blocked job / admitting a permitted pre-C2/synchronous-clean-rejection replacement under lineage.
- `test_fulfillment_cod_interplay.py` — COD scenarios 4–13 state derivation; `stock.return.picking` as the only restoration path.
- `test_fulfillment_state_model.py` — 7 Layer-A families raw+normalized; unknown-future-value contract; Delivered-inconsistency case.
- `test_fulfillment_lifecycle.py` — job-type `selection_add` **`ondelete`** sink **and** the dedicated `trigger_origin` callable `_normalize_tracking_change_trigger_origin_on_uninstall` (removed value → core `fulfillment_picking_validation`; exactly one provenance audit; `job_source`/`trigger_origin` constraint intact; either callback order); upgrade/uninstall/reinstall across the full bridge stack; historic queued+running/review+terminal rows; **no removed trigger-origin value survives; zero residue; no orphan attempt/evidence**.
- `test_fulfillment_readiness.py` — `REQUIRED_MVP_SCOPES` swap; write-scope seam; **staff-permission NOT_PROVEN (not inferred from scopes)**; **API-version compat gate** (`store.api_version`).
- `test_fulfillment_vocabulary_guard.py` — persisted `error_class`/`subreason` ∈ merged registries; **`over_fulfillment`/any new value absent**; mapping to accepted vocabulary (DEC-038 §7.2).
- `test_fulfillment_source_guards.py` — RA-022 (no V2/REST/legacy in production paths); RA-023; no-`@idempotent`; no-`qty_done`/`quantity_done`; no `location.mapping` import; no raw transport; **exactly the ten §11.2 job types registered** (no per-domain reconcile, no `fulfillment_review_release` job type); **no `job_source='webhook'`** in any Wave 4 job; **file-boundary guard** (nothing outside §2/§5).
- `test_fulfillment_concurrency.py` — the genuine independent-transaction/process cases of §6 (or the dedicated harness it references); the shared-reconcile **handoff ordering** (predecessor terminalize/supersede → **flush** the mutation op-scope → insert the reconcile job), **no operation-scope collision**, attempt-domain dispatch, duplicate-reconciliation admission prevention, rollback injection.
- Plus the one named core-edit test: `addons/shopify_connector_core/tests/test_readiness_check.py` (assertion update only).

Regression coverage for relevant prior defects / risk-register entries (incl. **SRR-10**
no-tracking fail-closed) is folded into the files above. `action_confirm()` auto-picking
coexistence and the `send_to_shipper` `rate_and_ship` collision are covered by
`test_fulfillment_trigger.py` + `test_fulfillment_mode2_engine.py`.

## 6. Genuine concurrency plan (not savepoints)

Independent-PostgreSQL-transaction/process tests (real commit boundaries; the
merged Layer 2 mutation path requires them — `_drain_mutation_one` is bypassed under
the shared test cursor) for: duplicate admission; operation-scope serialization;
mutation handoff (C1/C2/NET/C3); mode switch; tracking update; reconciliation
replacement; review release; rollback injection; real PostgreSQL contention where
feasible (Odoo stock concurrency serializes at the **quant** layer). **Never
represent savepoints or sequential independent connections as simultaneous
concurrency.**

## 7. Odoo.sh runtime plan (Gate C — evidence wording distinguishes executed /
static / pending)

Exact-head identity; fresh install; upgrade; the focused fulfillment suite; the
complete connector regression; the security matrix; lifecycle + uninstall/reinstall
across the **full bridge stack** (sale/stock/stock_account/delivery/…); zero
residue; concurrency; failure + rollback injection; redaction + leak scan.

## 8. Shopify dev-store validation plan (Gate D — safe; dedicated resources)

Baseline reads; Mode 1 fulfillment; Mode 2 fulfillment; partial fulfillment where
safe; tracking creation; tracking update; repeat/no-op; replay prevention; clean
rejection / review routing where safely reproducible; read-after-write;
cleanup/restoration; proof no unrelated resource changed. **Wave 4 final acceptance
requires both fulfillment dev-store validation AND CV-013 (#185) to execute green.**
Full campaign: `docs/05-qa/fulfillment-mode-uat-matrix.md` (Gate A addendum).

## 9. Rollback plan

- **Implementation rollback:** single-PR revert of the fulfillment addon; the one
  named core `REQUIRED_MVP_SCOPES` edit reverts with it (revert the scope swap and
  its test) — a **narrow, isolated** revert.
- **Data/schema:** the fulfillment addon owns its own tables; uninstall removes
  them; the store-settings/binding fields are additive. **Created Shopify
  fulfillments remain** (no auto-unfulfill); Odoo stock is unaffected by the revert.
- **Jobs / mutation attempts on rollback:** in-flight fulfillment jobs must reach a
  terminal/blocked state (or be admin-resolved) before uninstall; the mutation-
  attempt evidence is immutable audit.
- **Mode-setting rollback:** switching a store back to Mode 1 stops future
  auto-application without corrupting state (modes §6).
- **Dev-store fixtures:** the campaign restores all dedicated resources to baseline.
- **Restore-from-checkpoint** only if a base regression is demonstrated (never
  modify the protected checkpoint).
- **Evidence-before-retry:** a failed gate re-runs only after the exact failure is
  classified and fixed in one consolidated batch.

## 10. Definition of done

Both Mode 1 and Mode 2 backend implemented, tested, and runtime-proven; every
fulfillment mutation runs under Layer 2 (durable attempt; reconciliation-before-
retry; **reconcile-only after `transport_attempted=true` — no resend from read
absence, source-level**); notification default-off proven
incl. retry; RA-022/RA-023 respected (source-level); zero inventory/refund/payout
logic; TD-002 resolved with tests; suites + Odoo.sh green; genuine dev-store
fulfillment evidence for both modes; CV-013 carried; validation-results doc + AR row
+ program-state + acceptance-matrix + handoff + learning-loop updated; **no
`addons/**` file outside the allowlist changed; PR draft/unmerged; no
self-acceptance**.

## 11. Hard stops

Exact-base identity fails; a protected reference changed; a competing authorized
Wave 4 branch/PR exists; fulfillment implementation already exists unexpectedly;
current official Shopify evidence conflicts materially with an accepted decision;
required Odoo 19 source unavailable and the missing behavior is decision-critical; a
**genuinely new** product/commercial ruling beyond the already-ruled DEC-038 Q1–Q8 is
required and unresolved; the design
needs a destructive/irreversible migration; scope would materially change; security
or credential exposure found; a needed file falls outside the frozen allowlist with
no control-room amendment. *(Do not hard-stop for missing Shopify credentials/dev
store — carry CV-013 and continue static/Odoo work.)*

## 12. Final report + prohibitions

Return an evidence-complete report (identity, branch/PR, SHAs, changed files,
Mode 1/Mode 2/16-condition/Layer 2 summaries, tests, runtime, dev-store, CV-013,
rollback), and confirm: no `addons/**` file outside the allowlist changed; no
Shopify mutation occurred without explicit dev-store authorization; PR draft/
unmerged; no self-acceptance / ready-marking / merge; no Gate C-beyond / Wave 5
work started. **Do not self-accept, mark ready, merge, perform a live Shopify
mutation without authorization, or start Wave 5.**
