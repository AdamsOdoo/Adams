# Wave 2 — Definition of Ready (Order Import: Task 012 + Area-6 Order-Scan Slice)

> **Status: ACCEPTED by Claude control room, 2026-07-17.** Docs-only gate act.
> Every §3 gate decision below is **Accepted**; every open question is closed
> or explicitly, non-blockingly deferred per
> [`DEC-035`](../04-decisions/DEC-035-wave-2-open-question-dispositions.md).
> **Wave 2 is AUTHORIZED TO START once this docs-only gate PR merges into
> `mvp/program-integration`. Wave 2 implementation has NOT started as of this
> acceptance** — this document and its companions authorize a future,
> separate Sol implementation session using the locked prompt at
> [`../06-prompts/sol-wave-2-order-import-locked-prompt.md`](../06-prompts/sol-wave-2-order-import-locked-prompt.md);
> no code is written by this acceptance act itself.
>
> **Current program state (2026-07-17):** Wave 1 is **merged** (PR #172 merged
> into `mvp/program-integration` via merge commit `d18f9a9997d7da574f629f834e2adb83b492cfc6`;
> CORE-R1, LC-1, JOB-ACTIONS, SEC-1 all merged) and **SRR-03 is CLOSED**
> (corrected-head build `34995642` green at 0 failed / 0 errors / 644 tests).
> The Fable remaining-gap-closure mission (PR #173) is **merged**
> (merge commit `0fb8ccbe8ce54404a57260f82e8226ffa7e6bf73`), making every
> PD-A/B/C/D/E, PD-COD, and PD-RB decision cited in §3 below binding, not
> merely proposed. The COD, fulfillment-mode, reconnect/backfill,
> security/PII, and cross-domain QA matrices exist; the premium UX master
> specification exists. This acceptance was preceded by an exact-codebase
> preflight of `shopify_connector_core`/`_product`/`_sale` — see the
> re-accepted Task 012 packet's "Control-room re-acceptance" section for the
> reconciliation findings. Wave 2 introduces **no PII-masking fields** (the
> MVP has no PII masking; the Wave-1 masking implementation is corrected by
> SEC-2 in Wave 5).

This document instantiates the 7-field standard of
[`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)
at wave granularity for **Wave 2** of the MVP completion program
([`mvp-completion-program.md`](mvp-completion-program.md) §4), and layers on
the 2026-07-16 canonical policy documents produced by the Fable gap-closure
mission. It does not reopen, restate, or supersede the Task 012 packet's
decision closures (D-012-1..12) — see the packet's dated addendum of the
same day.

## 1. Scope statement

Wave 2 = **Shopify order import into Odoo sales orders**, exactly two work
packages behind one control-room wave gate:

1. **Task 012** — order importer, order binding, tax mapping, financial
   gates, per
   [`task-012-order-import-implementation-packet.md`](task-012-order-import-implementation-packet.md)
   (D-012-1..12 + its 2026-07-14 decision closure + the 2026-07-16
   policy-layer addendum), **plus** the policy layer newly specified in
   [`../02-product/sales-order-lifecycle-and-confirmation-policy.md`](../02-product/sales-order-lifecycle-and-confirmation-policy.md)
   (confirmation-policy gate), the Wave-2 slice of
   [`../02-product/cod-lifecycle-and-reconciliation.md`](../02-product/cod-lifecycle-and-reconciliation.md)
   §9 (COD import read-model), and the order-domain slice of
   [`../02-product/reconnect-catchup-backfill-policy.md`](../02-product/reconnect-catchup-backfill-policy.md)
   (watermark catch-up + Administrator backfill preview).
2. **Area-6 order-scan slice** — `order_import_scan` job type, order-scan
   cron, and manual order-sync trigger per
   [`area-6-sync-triggers-implementation-packet.md`](area-6-sync-triggers-implementation-packet.md)
   D-A6-2/3/4/6 as they apply to the order domain (D-A6-5 is already Wave 1
   Task JOB-ACTIONS scope, per DEC-034; Wave 2 consumes it, never
   reimplements it).

**Out of Wave 2 (hard):** inventory, fulfillment, product export, refunds,
invoices/payment automation, abandoned-checkout workspace (PD-AC-2 is
post-MVP), COD fulfillment interplay (Wave 4), COD workspace UI and
`orderMarkAsPaid` (Wave 5+), the two-role migration (SEC-2, Wave 5), all
operator UI beyond nothing-at-all (UI is Wave 5), and the DEC-031 Layer 2
substrate (see §5).

## 2. DoR checklist (per the 7-field template)

### 2.1 Objective

One scoped outcome: a store's Shopify orders are discovered (scheduled scan
/ reconnect catch-up / manual action / Administrator backfill), imported
idempotently into Odoo sale orders through the fail-closed financial gate
family, then routed through the confirmation-policy gate — read-only toward
Shopify, runtime-proven, with zero UI.

### 2.2 Allowed files — exhaustive

Fixed at this re-acceptance. No "or the final name" / "any necessary file"
language. Every file the Wave 2 Sol session may create or edit, scoped to
the minimum Task 012 + Area-6 order-scan slice:

| # | File | State | Purpose | Module | Covering tests | Rollback implication |
|---|---|---|---|---|---|---|
| 1 | `addons/shopify_connector_sale/models/shopify_connector_order_binding.py` | Create | `shopify.connector.order.binding` model (D-012-1 field table); `_odoo_binding_field_name() → 'sale_order_id'` (DEC-034 contract); `_additional_protected_binding_fields()`; `_pii_snapshot_fields()` returning an empty tuple (binding stores no PII, DEC-034/D-012-1) | `shopify_connector_sale` | `test_order_binding.py` | Delete file; `sale.order` rows survive as ordinary data (no cascade) |
| 2 | `addons/shopify_connector_sale/models/shopify_connector_sale_order_line.py` | Create | `_inherit 'sale.order.line'`; adds one indexed readonly `Char` `shopify_line_item_gid` (D-012-1; DEC-013 — no line-binding model) | `shopify_connector_sale` | `test_order_import_mapping.py` | Delete file; drop the additive column (no migration needed, additive-only) |
| 3 | `addons/shopify_connector_sale/models/shopify_connector_order_importer.py` | Create | `shopify.connector.order.importer` AbstractModel service (`import_order_sync`); the four `ORDER_*_QUERY` GraphQL read constants (§4 of the closure); D-012-2..12 financial/tax/customer/product resolution logic; the `job_type='order_import_sync'` `selection_add`+LC-1 `ondelete` seam, `_domain_flag_for_job_type() → 'sale_domain_enabled'` (DEC-035 EQ-PF-1), `_get_handlers()`/`_get_replay_policies() → remote_read_replay_safe` dispatch-extension classes, mirroring `shopify_connector_customer_importer.py`'s seam shape exactly; a module-local AST guard asserting `execute_business`-only usage (DEC-035 EQ-PF-2) | `shopify_connector_sale` | `test_order_import_mapping.py`, `test_order_totals_guard.py`, `test_order_tax_resolution.py`, `test_order_customer_resolution.py`, `test_order_duplicate_prevention.py` | Delete file; no running job references a handler that no longer exists once LC-1's `_reassign_to_historic_job_type` has converted any in-flight rows |
| 4 | `addons/shopify_connector_sale/models/shopify_connector_tax_mapping.py` | Create | `shopify.connector.tax.mapping` model (D-012-9 §5.2/§5.5): `store_id`, `shopify_tax_evidence_key` (versioned SHA-256, `UNIQUE(store_id, shopify_tax_evidence_key)`), `account_tax_id` (restrict); company-scope `@api.constrains` | `shopify_connector_sale` | `test_order_tax_resolution.py` | Delete file/table; no FK from `sale.order`/`account.tax` depends on it surviving |
| 5 | `addons/shopify_connector_sale/models/shopify_connector_order_scan.py` | Create | Area-6 order-scan slice only (D-A6-2/3/4/6 as applied to the order domain): `job_type='order_import_scan'` `selection_add`+LC-1 `ondelete`, `_domain_flag_for_job_type() → 'sale_domain_enabled'`; scan-enumeration handler (`updated_at:>checkpoint−overlap`, `sortKey: UPDATED_AT` — confirmed live, DEC-035 item 10); `action_sync_orders_now()` (manual, `group_shopify_connector_operator`+); `action_sync_selected()` re-enqueue on the order binding; Administrator backfill preview + confirmed-enqueue service methods (PD-RB-8, backend only — no wizard view); watermark advance/hold-back on `sale_order_last_import_checkpoint_at`; collision-safe enqueue via `shopify_target_gid='scan:order'` (D-A6-2). **Does not** implement `product_import_scan`/`customer_import_scan` — explicitly out of this slice (see §1). **Does not** implement `action_manual_retry`/`action_cancel`/`action_resolve_manual_review` — already-merged JOB-ACTIONS scope, only called, never reimplemented. Its own AST guard asserting `execute_business`-only usage (DEC-035 EQ-PF-2) | `shopify_connector_sale` | `test_order_scan_triggers.py` | Delete file; cron/ACL removed by the manifest change (row 10); LC-1 conversion handles any in-flight historic rows |
| 6 | `addons/shopify_connector_sale/models/shopify_connector_store_settings.py` | Modify (existing file, additive `_inherit` fields only) | Add: `order_confirmation_policy` (Selection, default `paid_only` — DEC-035 item 11), `manual_gateway_policy` (default `require_approval`), `approved_manual_gateways`, `order_import_window` (default 30 d), `pending_wait_expiry` (default 24 h / min 1 h / max 7 d — PD-B1), `order_import_include_test`, `order_company_id` (default `env.company`), `order_pricelist_id`, `order_sales_team_id`, `order_payment_term_id` (readiness-blocking while unset), `sale_order_last_import_checkpoint_at` (now the order-domain watermark seed, PD-RB-4) | `shopify_connector_sale` | `test_order_confirmation_policy.py`, `test_order_manual_gateway_overlay.py`, `test_order_watermark_backfill.py` | Revert file; additive fields only, no migration required |
| 7 | `addons/shopify_connector_sale/models/__init__.py` | Modify | Register the four new model files (rows 1–5) | `shopify_connector_sale` | N/A (import-only) | Revert file |
| 8 | `addons/shopify_connector_sale/security/ir.model.access.csv` | Modify | Add auditor/operator/reviewer/admin rows for `shopify.connector.order.binding` and `shopify.connector.tax.mapping`, exactly the customer-binding pattern (`1,0,0,0` / `1,0,1,0` / `1,1,0,0` / `1,1,1,0`); no new group | `shopify_connector_sale` | `test_order_binding.py` (ACL assertions) | Revert file; no group/model removed |
| 9 | `addons/shopify_connector_sale/data/shopify_connector_sale_cron.xml` | Create | One `ir.cron`, order domain only, `noupdate="1"`, interval 15 min (D-A6-3), gated on `sale_domain_enabled` AND the new `order_scheduled_sync_enabled` settings boolean (default False, opt-in) | `shopify_connector_sale` | `test_order_scan_triggers.py` | Delete file; cron removed cleanly (no data depends on its `ir.model.data` XML ID surviving) |
| 10 | `addons/shopify_connector_sale/__manifest__.py` | Modify | Version bump; `depends` becomes `['shopify_connector_core', 'shopify_connector_product', 'sale']` (ARCH PD-3); add the new cron data file to `data` | `shopify_connector_sale` | N/A (manifest; covered indirectly by install/upgrade tests) | Revert file; version rollback per LC-1's additive-migration posture |
| 11 | `addons/shopify_connector_sale/migrations/<next-version>/post-migrate.py` | Create, only if a genuine schema-affecting default/backfill is needed (e.g. seeding `order_confirmation_policy` on existing stores) | Additive/idempotent migration, mirroring core's `19.0.1.8.0/post-migrate.py` pattern exactly | `shopify_connector_sale` | Covered by lifecycle/upgrade runtime evidence, not a dedicated unit test | Delete file; no destructive statement permitted in it (enforced by review, not by an automated guard) |
| 12 | `addons/shopify_connector_sale/tests/test_order_binding.py` | Create | Schema/constraints/mixin, dual uniqueness (`UNIQUE(store_id, shopify_gid)` + `UNIQUE(store_id, sale_order_id)`), restrict FKs, exact protected-field-set assertion (mirrors `test_customer_binding.py`) | `shopify_connector_sale` | Self | Delete file |
| 13 | `addons/shopify_connector_sale/tests/test_order_import_mapping.py` | Create | Happy path incl. confirmation policy, lines/shipping/tip mapping, tax rate-match+creation+reuse, addresses/dedup, metadata, guest paths, custom/gift-card lines, UTC parsing | `shopify_connector_sale` | Self | Delete file |
| 14 | `addons/shopify_connector_sale/tests/test_order_totals_guard.py` | Create | Component/tax/total tolerance checks; six fail-closed pre-creation gate families; bounded whole-order solver (K=2/M=2/C_max=25) | `shopify_connector_sale` | Self | Delete file |
| 15 | `addons/shopify_connector_sale/tests/test_order_tax_resolution.py` | Create | `shopify.connector.tax.mapping` explicit-mapping-only behavior; versioned evidence-key fingerprint; company-scope constraint | `shopify_connector_sale` | Self | Delete file |
| 16 | `addons/shopify_connector_sale/tests/test_order_duplicate_prevention.py` | Create | Order-binding sole-anchor idempotency; `operation_scope_key`/`idempotency_key` collision behavior across scan/catch-up/manual/backfill/repeated-webhook-follow-up-evidence paths | `shopify_connector_sale` | Self | Delete file |
| 17 | `addons/shopify_connector_sale/tests/test_order_customer_resolution.py` | Create | All D-012-5 paths incl. fallback used/unset, ambiguous hold with candidate JSON (D-012-4), archived-only, recall-safety reuse | `shopify_connector_sale` | Self | Delete file |
| 18 | `addons/shopify_connector_sale/tests/test_order_confirmation_policy.py` | Create | Full 8-state × 3-policy matrix (addendum A.3/A.4) | `shopify_connector_sale` | Self | Delete file |
| 19 | `addons/shopify_connector_sale/tests/test_order_manual_gateway_overlay.py` | Create | Manual-gateway overlay incl. approved/unapproved gateways, card-`PENDING` never manual, mixed-transaction `status='review'` routing (DEC-035 item 5) | `shopify_connector_sale` | Self | Delete file |
| 20 | `addons/shopify_connector_sale/tests/test_order_watermark_backfill.py` | Create | Watermark advance/hold-back/overlap/pagination/stale-generation refusal; backfill preview creates no jobs/records; confirmed backfill; resumability; 60-day/`read_all_orders` honesty | `shopify_connector_sale` | Self | Delete file |
| 21 | `addons/shopify_connector_sale/tests/test_order_cod_import_readmodel.py` | Create | COD flag + ledger snapshot + three-dimension state initialization at import (PD-COD-1/3 Wave-2 slice) | `shopify_connector_sale` | Self | Delete file |
| 22 | `addons/shopify_connector_sale/tests/test_order_scan_triggers.py` | Create | Order-scan job/cron/manual-trigger, collision-safe enqueue, `execute_business`-only AST guard (EQ-PF-2) | `shopify_connector_sale` | Self | Delete file |
| 23 | `addons/shopify_connector_sale/tests/__init__.py` | Modify | Register the eleven new test files (rows 12–22) | `shopify_connector_sale` | N/A | Revert file |
| 24 | `docs/05-qa/task-012-order-import-validation-results.md` | Create | Sol's runtime-evidence record (exact Odoo.sh build IDs, verbatim results) | Docs | N/A | Delete file |
| 25 | `docs/05-qa/task-area6-order-scan-validation-results.md` | Create | Sol's runtime-evidence record for the order-scan slice | Docs | N/A | Delete file |
| 26 | `docs/05-qa/architecture-review-log.md` | Modify | Append one new AR row for the Wave 2 implementation closure (mirrors AR-050/051/052 for Wave 1) | Docs | N/A | Revert the appended row |
| 27 | `docs/07-implementation-plan/mvp-program-state.md` | Modify | Wave-status table row 2, sprint-log entry, runtime-evidence log row | Docs | N/A | Revert file |
| 28 | `docs/05-qa/mvp-acceptance-matrix.md` | Modify | Row 9 (and rows 13/14 if they reference order-domain duplicate-prevention/idempotency) status update | Docs | N/A | Revert file |
| 29 | `docs/01-research/research-handoff.md` | Modify | Prepend Sol's own session handoff entry (learning feedback loop section) | Docs | N/A | Revert prepended entry |

Rows 1–23 are `addons/**`; rows 24–29 are `docs/**` (Sol's own required
wave-closure documentation, per the wave-review template's Definition of
Done — distinct from this gate session's own docs-only edits, which are
already merged before Sol's wave starts).

### 2.3 Forbidden files — exhaustive

- **All of `shopify_connector_core`** — every model, security, data,
  migration, and test file. No `.sudo()` call, no ACL row, no selection
  value, no dispatcher/enqueue/readiness-check file may be edited (the
  three-seam `_inherit` pattern used by rows 3 and 5 above requires zero
  core edits — reuse `sale_domain_enabled`, DEC-035 EQ-PF-1).
- **All of `shopify_connector_product`** — every model, importer,
  security, and test file, unless an exact inherited regression is proven
  and the fix is a single named test-only change with its own justification
  in the wave review (no speculative "while I'm in there" edits).
- **Customer importer/binding behavior in `shopify_connector_sale`** beyond
  the read-only reuse already named in row 3/17 above (resolving an order's
  customer via the *existing* `shopify.connector.customer.binding` and
  `shopify.connector.customer.importer` D1 match sequence) — no edit to
  `shopify_connector_customer_binding.py`, `shopify_connector_customer_importer.py`,
  or `shopify_connector_res_partner.py`.
- Any `shopify_connector_inventory*`, `shopify_connector_fulfillment*`,
  product-export, or media file/module (Wave 3–5).
- Any accounting entry, invoice, payment, or refund model/logic anywhere.
- Any payout model/logic.
- All UI/views/menus/actions/wizards/controllers — the backfill "wizard" is
  backend service methods + preview computation only in Wave 2; its screen
  is Wave 5.
- All webhook and OAuth files.
- All `.github/workflows/*`, `Dockerfile`, `docker-compose*`,
  `requirements*.txt`.
- `addons/adams_base` — always, unconditionally.
- The DEC-031 Layer 2 substrate
  ([`../03-architecture/dec-031-layer-2-mutation-safety-design.md`](../03-architecture/dec-031-layer-2-mutation-safety-design.md))
  — no `shopify.connector.mutation.attempt` model, no attempt-identity
  field, no mutation-attempt seam of any kind. Task 012/Area-6 perform zero
  Shopify mutations.
- Protected branches/refs/PRs: `checkpoint/core-r2-readonly-uat-2026-07-15`,
  `Shopify-connector`, `main`, PR #150, PR #151, issue #165 — never
  modified, reset, or force-pushed by this program.
- Any new PII-masking field, masked-order-binding field, mask/unmask toggle,
  masking setting, masking action, or scheduled business-record masking
  addition anywhere (the MVP has no PII masking; Wave 2 does not expand the
  Wave-1 masking implementation).
- Any `manual_review_subreason` `selection_add` — DEC-035's mixed-transaction
  disposition (item 5) uses the existing binding `status='review'` value
  instead; no new manual-review vocabulary is authorized.

No "any necessary file" language is used anywhere above; any file not
listed in §2.2 is forbidden by omission.

### 2.4 Acceptance criteria

All of the Task 012 packet's own §8 criteria, plus the new policy
behaviours:

1. **8-state × 3-policy matrix** — every cell of the confirmation-policy
   matrix (§2.1 of the lifecycle policy) produces exactly the mandated
   outcome (SO / quotation / wait / skip+review / no-import), including
   picking-existence assertions and never-confirm rows.
2. **Manual-gateway overlay** — approved manual gateway `PENDING` behaves
   per `manual_gateway_policy`; unapproved manual gateways and card
   `PENDING` (`manualPaymentGateway=false`) never take the manual path;
   discrimination is by transaction evidence, never `PENDING` alone (PD-B).
3. **Duplicate prevention** — unique `(store_id, shopify_order_gid)`
   binding created atomically with the SO; every re-discovery path (scan,
   catch-up, webhook follow-up, manual, backfill) takes the update path; a
   second SO is structurally impossible.
4. **Fail-closed financial gates** — the six pre-creation gate families,
   total-check ledger, divergent-currency `skipped` routing, and
   explicit-mapping-only tax posture all block **before** any SO exists,
   regardless of confirmation policy; state/transition handling never
   silently rewrites SO financial lines.
5. **Watermark catch-up + backfill preview** — per-store order watermark
   with overlap re-scan and hold-back (PD-RB-4/6/7); reconnect enqueues
   fresh generation scans only (PD-RB-1/2); Administrator backfill runs a
   mandatory read-only preview (new/changed/duplicate/skipped/needs-review
   counts) creating no jobs or records before explicit confirmation, with
   60-day/`read_all_orders` honesty (PD-RB-8); backfilled orders obey the
   same confirmation-policy and COD rules.
6. **COD scenarios at import level** — COD identity captured at import via
   manual-gateway evidence; scenarios 1–3 and 16 of the COD lifecycle
   matrix are satisfiable at the import/read-model level (ledger snapshot,
   three-dimension flags initialized; no stock/fulfillment mechanics —
   those are Wave 4).
7. Task 012 registers `remote_read_replay_safe` (DEC-033); no Layer-2 claim
   and no exactly-once-remote-effect claim anywhere.
8. All existing core/product/sale tests remain green; order-scan cron and
   manual trigger enqueue idempotently (D-A6-2 collision safety).

### 2.5 Tests

The packet's six named test files plus the policy-layer families. Scenario
coverage is defined by the QA matrices — the wave may not close with any
matrix row unmapped to a test or an explicit deferral:

- Lifecycle §9 test hooks 1–9 (state×policy, overlay, transitions,
  idempotency, edits/cancellations, gate ordering, reservation, settings
  changes, null/edge evidence).
- `../05-qa/reconnect-backfill-uat-matrix.md` order-domain rows (watermark
  advance/hold-back, overlap dedup, stale-generation refusal, 60-day
  honesty, preview-count accuracy, resumable backfill) — this matrix
  **exists** (2026-07-16); the wave adopts it as the binding UAT basis.
- `../05-qa/cod-uat-matrix.md` import-level rows (scenarios 1–3, 16) — this
  matrix **exists** (2026-07-16) and is likewise adopted.
- [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md)
  items 9, 13, 14 rows.

### 2.6 Runtime evidence (Odoo.sh — mandatory for Wave 2 closure)

Mirrors the Wave 1 standard (program contract §4 Wave 1) and is **mandatory**
for Wave 2 closure (unlike the read-only dev-store evidence in §2.7, which is
preferred but deferrable): Odoo.sh fresh-install build green; module upgrade;
focused-class runs for every new test file; full existing-domain regression;
security and duplicate-prevention tests; uninstall/reinstall and
zero-residue/no-PII-leak audit per DEC-030/LC-1; exact-head evidence recorded
in `docs/05-qa/task-012-order-import-validation-results.md` with build IDs and
verbatim result quotes. Simulated or extrapolated runtime claims are a
wave-gate rejection.

### 2.7 Dev-store evidence (strongly preferred, NOT a Wave 2 merge blocker)

A read-only live order import against the existing dev store (bounded
sample: at least one PAID order end-to-end, one policy-skip, one wait-state)
with redacted evidence in the validation record is **strongly preferred**.
Because Wave 2 performs no Shopify mutation, this read-only dev-store order
UAT is **not a Wave 2 merge blocker**. If read-only Shopify credentials are
unavailable at wave time, the wave states so transparently, **defers the
read-only dev-store order UAT to Wave 6** (recording it in the Wave 6 UAT
packet), requires **no special product-scope waiver**, and does **not**
present VAL-B2 as completed. Wave 2 is never "implementation-incomplete"
solely because the dev store is unavailable. (Mutation waves 3–5 still
require genuine dev-store mutation evidence before their own wave closure,
unless the product owner later records a specific exception.)

### 2.8 Rollback

Single-wave-PR revert against `mvp/program-integration`; drops
order-binding/tax-mapping tables and new settings fields via DEC-030/LC-1
lifecycle behaviour; read-only toward Shopify, so no remote state to
unwind; Wave 3+ never depends on Wave 2 internals beyond the merged
binding contract, so revert is self-contained.

### 2.9 Residue audit

Post-revert/uninstall: no orphan `ir.model.data`, crons, ACLs, or
selection values (LC-1 `_reassign_to_historic_job_type` registered on all
new job types from the start); no PII residue (bindings carry no customer
PII per D-012-1; evidence fields non-PII per the round-5/6 closures).

### 2.10 Definition of done

Template §7 in full, plus: control-room wave review per
[`../06-prompts/claude-mvp-wave-review-template.md`](../06-prompts/claude-mvp-wave-review-template.md)
accepts and merges into `mvp/program-integration`;
[`mvp-program-state.md`](mvp-program-state.md) and the acceptance matrix
updated; handoff + learning review complete.

### 2.11 Hard-stop conditions

Program hard-stops 1–11 apply verbatim; Wave-2-specific instantiations:

- **Stop 11 — discharged.** SRR-03 is **CLOSED** as of Wave 1's merge
  (2026-07-16); the former "SRR-03 still OPEN at Wave 2 merge" hard-stop no
  longer blocks Wave-1-descended work. If a future validation ever reopened
  the underlying risk, the escalation rule would re-apply, but that is not
  the current state.
- Wave 1 prerequisites (CORE-R1, LC-1, JOB-ACTIONS, SEC-1, SRR-03 closure)
  are **satisfied** — Wave 1 is merged into `mvp/program-integration`
  (PR #172). Their absence is no longer a live blocker.
- Any gate decision in §3 not Accepted at wave-open → stop.
- Dev-store read credentials unavailable is **not** a Wave 2 hard-stop: the
  read-only dev-store order UAT is deferrable to Wave 6 (§2.7), needs no
  waiver, and never marks Wave 2 incomplete.
- Null-financial-status class mapping (OQ-A) or mixed-transaction policy
  (OQ-D) encountered live without an accepted answer → fail closed to
  review and record; if it blocks the matrix, escalate (hard-stop 1).

## 3. Gate-decision table

Every decision below is **Accepted** as of this gate act (2026-07-17),
already binding through PR #173 (§4.A of the Wave 2 gate-preflight
session) or accepted in this same act per
[`DEC-035`](../04-decisions/DEC-035-wave-2-open-question-dispositions.md).

| Gate decision | Source | Wave-2 relevance | Acceptance authority | Status |
| --- | --- | --- | --- | --- |
| PD-A — three-policy `order_confirmation_policy`, `paid_only` default | lifecycle policy §1.1/§10 | Core confirmation gate | Product owner + control room | **Accepted** (binding through PR #173) |
| PD-B — manual-gateway policy + curated list, evidence-discriminated | lifecycle policy §10 | COD/manual path | Product owner + control room | **Accepted** (binding through PR #173) |
| PD-C — full state×policy matrix + transition table | lifecycle policy §10 | Acceptance criterion 1 | Product owner + control room | **Accepted** — DEC-035 items 1/2/5 close the null-status/mixed-transaction gaps in the matrix |
| PD-D — cancellation staging | lifecycle policy §10 | Update-path behaviour | Product owner + control room | **Accepted** |
| PD-E — settings inventory + defaults | lifecycle policy §10 | Allowed-files additions | Product owner + control room | **Accepted** — exact field list frozen in §2.2 row 6 |
| PD-COD-1/3/6 (import-relevant subset; PD-COD-2/4/5 accepted now but exercised Wave 4/5) | COD policy §10 | COD read-model at import | Product owner + control room | **Accepted** — PD-COD-6/OQ-COD-6 closed non-blocking per DEC-035 item 7 |
| PD-RB-1..9 order-domain subset (esp. PD-RB-4/5/6/7/8/9) | reconnect policy §11 | Watermark, catch-up, backfill | Product owner + control room | **Accepted** — OQ-RB-1/5/6 closed per DEC-035 items 8–10 |
| PD-AC-1 (abandoned checkouts never auto-import) | abandoned-checkout policy §8 | Negative boundary for the scan | Product owner + control room | **Accepted** (binding through PR #173, A-7) |
| Roles impact — **none for Wave 2 backend**: existing four groups suffice; two-role migration is Wave 5 SEC-2 and does not gate Wave 2 (new models grant per the migration-forward note in the roles doc §6) | roles doc §5/§6 | Confirmation of non-blocking | Control room (recorded, no new decision) | **Recorded — confirmed non-blocking** |
| **Task 012 packet re-acceptance** — packet + decision closure + the 2026-07-16 policy-layer addendum, as one act | packet §15 preamble + addendum | The wave's core packet | Control room gate act (separate prompt-issue act per §15) | **RE-ACCEPTED, 2026-07-17** — see the packet's own "Control-room re-acceptance" section |
| Area-6 packet acceptance (order-scan slice D-A6-1..4/6) | area-6 packet | Work package 2 | Control room | **ACCEPTED (order-scan slice only), 2026-07-17** — see the packet's own "Control-room re-acceptance" section; product-scan/customer-scan remain out of Wave 2 |

Open questions OQ-A..OQ-E (lifecycle), OQ-COD-6, OQ-RB-1/5/6 — and the two
exact-codebase-preflight questions EQ-PF-1/EQ-PF-2 this session discovered —
are every one **closed or explicitly, non-blockingly deferred** per
[`DEC-035`](../04-decisions/DEC-035-wave-2-open-question-dispositions.md);
none is silently resolved in code.

## 4. Explicit Layer-2 statement

**Wave 2 does NOT require DEC-031 Layer 2.** Task 012 is read-only toward
Shopify and declares `remote_read_replay_safe` per DEC-033; Layer 2 is
reserved for Shopify-mutation domains and is defined as Wave 3 Stage 0
(see [`wave-3-definition-of-ready.md`](wave-3-definition-of-ready.md) §4).
Wave 2 **DOES** require the Area-6 order-scan slice — Area 6's own gate
criterion ("Task 012 merged runtime-green") lands the scan inside this same
wave, after the importer exists within the wave branch.

## 5. Current-status conclusion

**READY. Accepted, 2026-07-17.** All four items that were outstanding as of
2026-07-16 are now closed:

1. ~~All §3 gate decisions are Proposed, none Accepted.~~ **Every §3 gate
   decision is Accepted** (table above).
2. ~~Task 012 packet re-acceptance with the 2026-07-16 addendum not yet
   performed; the §15 prompt-issue gate act not performed.~~ **Task 012
   packet RE-ACCEPTED** (packet's own "Control-room re-acceptance" section);
   the §15 prompt-issue gate act is performed by
   [`../06-prompts/sol-wave-2-order-import-locked-prompt.md`](../06-prompts/sol-wave-2-order-import-locked-prompt.md),
   issued (not executed) by this same gate act.
3. ~~Area-6 packet (order-scan slice) not accepted.~~ **ACCEPTED**, scoped to
   the order-scan slice only (packet's own "Control-room re-acceptance"
   section).
4. ~~This Definition of Ready itself is Proposed, not accepted.~~ **This
   document is ACCEPTED.**

**Already satisfied (unchanged):** Wave 1 merged (CORE-R1, LC-1, JOB-ACTIONS,
SEC-1) and SRR-03 closed; the companion QA matrices
(`../05-qa/reconnect-backfill-uat-matrix.md`, `../05-qa/cod-uat-matrix.md`)
exist. Read-only dev-store order evidence is preferred but not a blocker — if
credentials are unavailable it defers to Wave 6 (§2.7).

**Wave 2 is AUTHORIZED TO START once this docs-only gate PR merges into
`mvp/program-integration`.** Wave 2 implementation itself has **not**
started as of this acceptance — no branch, no code, no PR beyond this
docs-only gate PR exists for Wave 2 implementation. The next authorized
activity after this gate PR merges is issuing the locked Sol prompt at
[`../06-prompts/sol-wave-2-order-import-locked-prompt.md`](../06-prompts/sol-wave-2-order-import-locked-prompt.md)
with the exact post-merge `mvp/program-integration` SHA filled in.
