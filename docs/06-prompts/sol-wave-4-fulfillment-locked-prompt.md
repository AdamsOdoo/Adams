# Sol — Wave 4 Fulfillment/Tracking Implementation (Gate B) — LOCKED PROMPT

**`LOCKED CANDIDATE — NOT ISSUED; REQUIRES CHATGPT CONTROL-ROOM ACCEPTANCE`**

> This is a **future** Gate B implementation prompt. It is **not issued** and
> authorizes **no** implementation. It becomes usable only after the ChatGPT
> control room (a) accepts the Wave 4 Gate A package — the Task 014 packet + its
> §10 addendum, [`../04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md`](../04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md),
> the DoR, and this prompt — (b) rules on DEC-038 Q1–Q7, (c) verifies the base
> SHA, and (d) explicitly opens the Wave 4 Gate B fulfillment gate and issues this
> prompt. Producing it is Gate A governance work; it accepts nothing.

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
Mode 2 — exactly per the accepted Task 014 packet (D-014-1..8 + the §9 and §10
addenda) and DEC-038, running every Shopify mutation under the accepted DEC-036/
DEC-031 Layer 2 substrate. No UI (Wave 5). No live Shopify mutation in Gate B.

## 2. Exact allowed files (candidate allowlist — validate; no wildcards)

**New addon `addons/shopify_connector_fulfillment/` — individually enumerated:**
- `__init__.py`, `__manifest__.py`
  (`depends=['shopify_connector_core','shopify_connector_sale','stock_delivery','sale_stock']`)
- `models/__init__.py`
- `models/shopify_connector_fulfillment_binding.py` — the D-014-1 binding
  (`shopify_gid`=Fulfillment GID; `UNIQUE(store_id,shopify_gid)`+`UNIQUE(store_id,picking_id)`)
- `models/shopify_connector_fulfillment_inbound_evidence.py` — per-fulfillment +
  per-line evidence records (origin class, reconciled-quantity ledger; modes §5)
- `models/shopify_connector_fulfillment_service.py` — the Layer 2 mutation-domain
  service: the 7-callback strategies for `fulfillment_create` /
  `fulfillment_tracking_update`, the matching chain, the Mode 2 16-condition engine,
  the reconcile reads, the review-release helper, the reconciliation-scan handler
- `models/shopify_connector_job.py` — `job_type` `selection_add` +
  `_domain_flag_for_job_type` override + own `_compute_operation_scope_key` (own types only)
- `models/shopify_connector_job_dispatch.py` — `_get_reconciliation_strategies` /
  `_get_handlers` / `_get_replay_policies` add-only merges
- `models/shopify_connector_readiness_check.py` — `_get_checks` write-scope +
  staff-permission-axis append (add-only, in the fulfillment addon)
- `models/shopify_connector_store_settings.py` — `fulfillment_operating_mode` +
  `fulfillment_notification_confirmed` + `fulfillment_last_reconciliation_at` +
  mode-switch state fields
- `security/ir.model.access.csv`, `security/shopify_connector_fulfillment_security.xml`
- `data/shopify_connector_fulfillment_cron.xml` (reconciliation cron, `noupdate=1`)
- `tests/__init__.py` + the §5 test files below

> The **exact split by responsibility** inside this set is validated at Gate B
> (split a file only when real complexity justifies it; no unnecessary
> micro-modules). **No file outside this enumerated set** may be created without an
> explicit control-room allowlist amendment — a **hard stop**.

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

- **No legacy fulfillment surface** — name-specific guards for
  `fulfillmentCreateV2` and `fulfillmentTrackingInfoUpdateV2` (must not appear).
- **RA-023 line-identity** — every fulfillment path uses explicit
  `lineItemsByFulfillmentOrder` via `lineItemsByFulfillmentOrder`/the FO
  `lineItems` connection; **no order-ID-only fulfillment path** exists (the
  omission-of-`fulfillmentOrderLineItems` code path must not exist).
- **No `@idempotent`** in any fulfillment operation string (fulfillment mutations
  are not on Shopify's 17-mutation `@idempotent` list — source-guard).
- **No `qty_done` / `quantity_done`** field access (does not exist in Odoo 19 — use
  `stock.move.line.quantity`; source-guard).
- **No raw transport** — only `execute_business`; **exact GraphQL document shapes**
  fingerprinted deterministically (byte-identical C2↔wire).
- **Exact scopes** — `read_merchant_managed_fulfillment_orders` +
  conditional `write_merchant_managed_fulfillment_orders`; **plus the
  `fulfill_and_ship_orders` staff-permission** axis.
- **Mutation-context / idempotency-key / operation-scope / protected-field
  enforcement**; allowed FO states + the 16-error-class vocabulary (no 17th class).
- **No secret/PII logging** — recipient names never in fulfillment log messages;
  redaction via `_system_append`.
- **Exact file-boundary enforcement** — a repo guard that fails if a fulfillment
  file appears outside the enumerated allowlist.

## 5. Unit-test plan (exact families; each behavior gets a pass + fail-to-review)

Mode 1 outbound; **all 16 Mode 2 conditions** (pass + fail-to-review each); mode
switching (state machine, idempotent re-confirm, rollback); COD + non-COD; partial
delivery; backorder (follow `backorder_id`); multiple pickings; multiple
FulfillmentOrders (incl. **>1 FO per location**); location resolution (incl.
`assignedLocation.location`-null fallback; never `location_mapping`); tracking
creation; tracking update (in-place, multi-number split, missing-ref-with-note);
cancellation (Odoo + Shopify sides); returns boundary (no Shopify fulfillment on a
return); no-op; clean rejection (`userErrors`, positive-success-evidence gate);
uncertain result → verify-adopt/absent-resend/inconclusive-block; reconciliation;
retry + **replacement-job lineage**; review release (admin path for
mutation-evidence jobs); duplicate prevention; company consistency; permissions
(ACL matrix); redaction; the **`supportedActions.CREATE_FULFILLMENT` eligibility
gate**; the **FO-line-item-GID 2-hop matching**; the **`code_required=False`
classifier**; the **`action_confirm()` auto-picking coexistence**; the
**`send_to_shipper` `rate_and_ship` collision**; **staff-permission tests distinct
from API-scope tests**; regression coverage for relevant prior defects / risk-
register entries; and explicit **RA-022 / RA-023** source-guard + behavior tests.

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
retry; no blind-retry path exists — source-level); notification default-off proven
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
product/commercial ruling (DEC-038 Q1–Q7) is required and unresolved; the design
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
