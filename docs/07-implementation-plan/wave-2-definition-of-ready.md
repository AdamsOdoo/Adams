# Wave 2 — Definition of Ready (Order Import: Task 012 + Area-6 Order-Scan Slice)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Docs-only.
> Acceptance authority: product owner + Claude control room. **Wave 2
> remains unauthorized until this Definition of Ready is accepted and its
> gate decisions are Accepted. No implementation authorized by this
> document.**
>
> **Current program state (2026-07-16):** Wave 1 is **merged** (PR #172 merged
> into `mvp/program-integration` via merge commit `d18f9a99`; CORE-R1, LC-1,
> JOB-ACTIONS, SEC-1 all merged) and **SRR-03 is CLOSED** (corrected-head build
> `34995642` green at 0 failed / 0 errors / 644 tests). The COD, fulfillment-mode,
> reconnect/backfill, security/PII, and cross-domain QA matrices exist; the
> premium UX master specification exists. **Wave 2 is unauthorized and unstarted
> because its gate decisions and this Definition of Ready have not yet been
> accepted — NOT because Wave 1 is unfinished.** Wave 2 introduces **no PII-masking
> fields** (the MVP has no PII masking; the Wave-1 masking implementation is
> corrected by SEC-2 in Wave 5).

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

### 2.2 Allowed files

Base list = the Task 012 §15 locked-prompt ALLOWED FILES list, verbatim
(order binding, importer, sale-order-line extension, store settings, tax
mapping, ACL rows, six named test files, conditional core dispatch seam,
validation-results/AR/handoff docs). **Additions implied by the 2026-07-16
policy docs — packet re-acceptance required (see the packet addendum):**

- `addons/shopify_connector_sale/models/shopify_connector_store_settings.py`
  — additional confirmation-policy settings fields (PD-A/B/E):
  `order_confirmation_policy`, `manual_gateway_policy`,
  `approved_manual_gateways`, `order_import_window`, `pending_wait_expiry`.
- `addons/shopify_connector_sale/models/shopify_connector_order_binding.py`
  — COD operational-ledger snapshot fields and connector state-dimension
  fields (PD-COD-1/3 Wave-2 slice: COD flag, financial-state evidence,
  state-transition audit trail), plus the order watermark fields the
  reconnect policy requires (PD-RB-4 order-domain watermark lives on store
  settings; transition records on the binding).
- Area-6 order-scan slice files per that packet's allowed list as scoped to
  the order domain: `shopify_connector_order_scan.py` (or the packet's exact
  final name), the order-scan cron data file, `test_order_scan_triggers.py`.
- New test files for the policy layer (see §2.4/§2.5): confirmation-policy
  matrix tests, manual-gateway overlay tests, watermark/catch-up tests,
  backfill-preview tests (backend service level — no wizard view files).

The exhaustive final allowed-file list is fixed at packet re-acceptance;
this DoR records the categories so the re-accepted packet cannot silently
widen beyond them.

### 2.3 Forbidden files

- Any addon path outside the re-accepted Task 012 + Area-6 order-slice
  allowlists; every other `shopify_connector_core` /
  `shopify_connector_product` file; `addons/adams_base` (always).
- All Wave 3+ domains: no `shopify_connector_inventory`,
  `shopify_connector_fulfillment`, product-export, or media files.
- The DEC-031 Layer 2 substrate
  ([`../03-architecture/dec-031-layer-2-mutation-safety-design.md`](../03-architecture/dec-031-layer-2-mutation-safety-design.md))
  — **not built in Wave 2** unless separately accepted as its own gated core
  task; Task 012 performs no Shopify mutation and must not create
  `shopify.connector.mutation.attempt` or any Layer-2 model/seam.
- UI beyond minimal: no views, menus, actions, wizards, controllers,
  webhooks, OAuth, CI/workflow/Docker/requirements files. The backfill
  "wizard" ships in Wave 2 as backend service methods + preview computation
  only; its screen is Wave 5.
- Protected references: checkpoint branch, `Shopify-connector`, `main`,
  PR #150/#151, issue #165.

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

Every decision below must be **Accepted** before Wave 2 opens.

| Gate decision | Source | Wave-2 relevance | Acceptance authority |
| --- | --- | --- | --- |
| PD-A — three-policy `order_confirmation_policy`, `paid_only` default | lifecycle policy §1.1/§10 | Core confirmation gate | Product owner + control room |
| PD-B — manual-gateway policy + curated list, evidence-discriminated | lifecycle policy §10 | COD/manual path | Product owner + control room |
| PD-C — full state×policy matrix + transition table | lifecycle policy §10 | Acceptance criterion 1 | Product owner + control room |
| PD-D — cancellation staging | lifecycle policy §10 | Update-path behaviour | Product owner + control room |
| PD-E — settings inventory + defaults | lifecycle policy §10 | Allowed-files additions | Product owner + control room |
| PD-COD-1/3/6 (import-relevant subset; PD-COD-2/4/5 accepted now but exercised Wave 4/5) | COD policy §10 | COD read-model at import | Product owner + control room |
| PD-RB-1..9 order-domain subset (esp. PD-RB-4/5/6/7/8/9) | reconnect policy §11 | Watermark, catch-up, backfill | Product owner + control room |
| PD-AC-1 (abandoned checkouts never auto-import) | abandoned-checkout policy §8 | Negative boundary for the scan | Product owner + control room |
| Roles impact — **none for Wave 2 backend**: existing four groups suffice; two-role migration is Wave 5 SEC-2 and does not gate Wave 2 (new models grant per the migration-forward note in the roles doc §6) | roles doc §5/§6 | Confirmation of non-blocking | Control room (recorded, no new decision) |
| **Task 012 packet re-acceptance** — packet + decision closure + the 2026-07-16 policy-layer addendum, as one act | packet §15 preamble + addendum | The wave's core packet | Control room gate act (separate prompt-issue act per §15) |
| Area-6 packet acceptance (order-scan slice D-A6-1..4/6) | area-6 packet | Work package 2 | Control room |

Open questions OQ-A..OQ-E (lifecycle), OQ-COD-6, OQ-RB-1/5/6 should be
answered or explicitly deferred-with-fail-closed-behaviour at the same gate
sitting; none may be silently resolved in code.

## 4. Explicit Layer-2 statement

**Wave 2 does NOT require DEC-031 Layer 2.** Task 012 is read-only toward
Shopify and declares `remote_read_replay_safe` per DEC-033; Layer 2 is
reserved for Shopify-mutation domains and is defined as Wave 3 Stage 0
(see [`wave-3-definition-of-ready.md`](wave-3-definition-of-ready.md) §4).
Wave 2 **DOES** require the Area-6 order-scan slice — Area 6's own gate
criterion ("Task 012 merged runtime-green") lands the scan inside this same
wave, after the importer exists within the wave branch.

## 5. Current-status conclusion

**READY once gate decisions are Accepted.** As of 2026-07-16, Wave 2 is
**NOT YET ready — but only because its gate decisions and this Definition of
Ready are not yet accepted, not because any Wave 1 prerequisite is
outstanding.** Wave 1 is merged and SRR-03 is closed; the companion QA
matrices exist. The genuinely outstanding list:

1. All §3 gate decisions are Proposed, none Accepted.
2. Task 012 packet re-acceptance with the 2026-07-16 addendum not yet
   performed; the §15 prompt-issue gate act not performed.
3. Area-6 packet (order-scan slice) not accepted.
4. This Definition of Ready itself is Proposed, not accepted.

**Already satisfied (no longer blockers):** Wave 1 merged (CORE-R1, LC-1,
JOB-ACTIONS, SEC-1) and SRR-03 closed; the companion QA matrices
(`../05-qa/reconnect-backfill-uat-matrix.md`, `../05-qa/cod-uat-matrix.md`)
exist. Read-only dev-store order evidence is preferred but not a blocker — if
credentials are unavailable it defers to Wave 6 (§2.7). When items 1–4 close,
Wave 2 may open per the program's normal control-room gate act.
