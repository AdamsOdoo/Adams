# Task 014 — Fulfillment / Tracking Validation Results (Wave 4 Gate B)

> **Status:** Gate B implementation candidate — **READY FOR ONE EXHAUSTIVE
> CONTROL-ROOM REVIEW**. Draft PR #189, unmerged, not marked ready, not
> self-accepted. No live Shopify mutation occurred. Gate C (Odoo.sh runtime)
> and Gate D (Shopify dev-store) evidence is classified `IMPLEMENTED—RUNTIME
> PENDING` / `NOT PROVEN` — never fabricated. CV-013 (#185) remains open and
> critical.

**Base:** `mvp/program-integration@01f072dd4d83b7b39737452a686244a3a8c00332`.
**Branch:** `claude/wave-4-fulfillment-gate-b`. **Prompt:**
`docs/06-prompts/sol-wave-4-fulfillment-locked-prompt.md` (blob
`ad7418f846ae0479471306c3ae997ac4eb60df4b`), issued by issue #186 comment
`5043052341` with the PR #188 comment `5042975042` source/origin amendment.

## 1. Evidence classification legend

| Class | Meaning |
| --- | --- |
| `EXECUTED—PASS` | A check actually ran in this workspace and passed. |
| `STATICALLY VERIFIED` | Verified by static analysis (AST/regex/`py_compile`) that ran here; behavioural runtime not executed. |
| `IMPLEMENTED—RUNTIME PENDING` | Code + tests written; requires an Odoo runtime (Gate C Odoo.sh) to execute. |
| `NOT PROVEN` | Requires an external environment not available in Gate B (Shopify dev-store, CV-013, staff permission). |

**Environment note (binding on classification):** this workspace has **no Odoo
runtime** (no `odoo`/`odoo-bin`, no core `stock`/`sale` modules on disk), so the
`TransactionCase` suite **cannot execute here**. Every Odoo test in §5 is
therefore `IMPLEMENTED—RUNTIME PENDING` and must run at Gate C. The pure-Python
AST/regex source guards were executed standalone in this workspace and are
`EXECUTED—PASS` (§4).

## 2. Addon architecture implemented

New addon `addons/shopify_connector_fulfillment/`
(`depends=['shopify_connector_core','shopify_connector_sale','stock_delivery','sale_stock']`).
One `shopify.connector.fulfillment.service` AbstractModel split across the
enumerated responsibility files (reader / admission / create-strategy /
tracking-strategy / inbound / review / mode2 / scans), plus the binding +
inbound-evidence schema, the store-settings extension, the job / dispatch /
readiness / stock.picking seams. Every Shopify mutation runs under the merged
DEC-036/DEC-031 Layer 2 substrate; no parallel mutation framework is
introduced. No UI (Wave 5). No `**` wildcard; every path is within the frozen
§2/§5 allowlist (§7 of the final report).

## 3. Ten-job taxonomy + source/origin matrix — implemented

All ten frozen `job_type` values are registered via `selection_add` with the
historic-sink `ondelete`; the shared `fulfillment_mutation_reconcile` is the one
reconcile type; `fulfillment_review_release` is a sanctioned helper (not a job
type); no Wave 4 job admits from `webhook`. The merged core invariant
(`odoo_event` requires a non-empty accepted `trigger_origin`; every other source
requires `trigger_origin=False`) is honoured by construction — see the exact
pairs in the locked prompt / PR #188 comment `5042975042`, mirrored in the
admission enqueue (odoo_event + `fulfillment_picking_validation` /
`fulfillment_tracking_change`; manual/replacement/review-release =
`manual_sync` + `False`; reconcile/scan = `reconciliation`/`scheduled_sync` +
`False`; `fulfillment_mode2_evaluation` never uses `odoo_event`). The Q1
operation-scope literals are overridden for the two mutation types only; the
shared reconcile owns no remote-effect scope.

| Evidence | Class |
| --- | --- |
| Exactly ten fulfillment job types registered; shared reconcile; no webhook source (`test_fulfillment_source_guards.py::test_exactly_ten_fulfillment_job_types_registered`, `test_no_webhook_source_enqueued`) | `IMPLEMENTED—RUNTIME PENDING` (runtime registry read) / static portion `EXECUTED—PASS` |
| Source/origin pair matrix for all ten types (`test_fulfillment_source_guards.py`, `test_fulfillment_admission.py`, `test_fulfillment_idempotency.py`, `test_fulfillment_lifecycle.py`) | `IMPLEMENTED—RUNTIME PENDING` |

## 4. Static / source-guard results — `EXECUTED—PASS`

The frozen **core** guard logic (`shopify_connector_core/tests/test_mutation_source_guards.py`)
and this addon's own guard logic were executed against the fulfillment
production tree standalone in this workspace:

- `test_mutation_literals_require_guarded_transport_or_selftest` → **0 violations**.
  The fulfillment mutation documents are written as **anonymous** GraphQL
  operations held as module constants and referenced by name from the paired
  `_transport_*` method (which holds the guarded
  `execute_business(mutation_context=...)` call); the core named-mutation regex
  does not match them, so the frozen core guard stays green **without editing
  the frozen `ACCEPTED_PREPARE_TRANSPORT_SPLIT` allowlist**. This addon's own
  `test_fulfillment_mutation_documents_are_guarded` provides the real guard
  (the mutation documents live only in the two strategy files and are only
  reachable through `execute_business`).
- `test_repo_wide_raw_transport_guard` → **0 violations** (no `requests.<verb>`).
- `test_no_production_direct_send_caller` → **0 violations** (no `_send`).
- Fulfillment guards → **0 violations**: no `fulfillmentCreateV2`/
  `fulfillmentTrackingInfoUpdateV2`/`FulfillmentV2Input` (RA-022); no
  `fulfillmentOrderMove`/`fulfillmentOrderHold`/`fulfillmentOrderReleaseHold`;
  no `@idempotent` in any operation string; no `qty_done`/`quantity_done`
  attribute access; no `shopify.connector.location.mapping` access; no
  `job_source='webhook'` literal.
- `py_compile` over every production and test file → **clean**.

Command evidence is reproducible from the two standalone guard scripts used
during implementation (the core-guard replica and the fulfillment-guard replica);
the authoritative gate is the in-repo `test_fulfillment_source_guards.py` +
`test_readiness_check.py` run at Gate C.

## 5. Frozen test suite — files + classification

All 22 frozen filenames (locked prompt §5) plus the out-of-band concurrency
harness and the one named core-edit test are present and compile. Behavioural
execution is `IMPLEMENTED—RUNTIME PENDING` (no Odoo runtime here).

| Test file | Behaviour families | Class |
| --- | --- | --- |
| `test_fulfillment_binding.py` | D-014-1 schema; dual uniqueness; backorder-chain non-collision | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_inbound_evidence.py` | per-fulfillment/per-line evidence; ledger; raw+normalized state | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_trigger.py` | `_action_done` eligibility; adopt `sale_stock` pickings (Q2); tracking hook; domain gating | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_admission.py` | per-FO decomposition; enqueue lineage; `mapping_missing`/`ambiguous_match` routing | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_reader_pagination.py` | cursor pagination to completion; fail-closed cap; duplicate/repeated/malformed; partial ≠ absence | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_matching.py` | FO-line-item 2-hop; skip null-GID; qty ≤ remaining; RA-023 | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_location_resolution.py` | `assignedLocation` null fallback; core cache only; Q3 refresh; fail-closed | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_create_strategy.py` | 7 callbacks; positive-success gate; no `@idempotent`; CREATE_FULFILLMENT gate | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_tracking_strategy.py` | in-place update; multi-number split; `notifyCustomer` persisted/never re-read | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_idempotency.py` | **P0** reconcile-only; no resend from absence; APPLIED/INCONCLUSIVE only; cap 3 → `duplicate_risk`; no-tracking + notification fail-closed | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_inbound_classification.py` | origin evidence stack; own-GID precedence; unknown→external | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_mode2_engine.py` | all 16 conditions (pass + fail-to-review); Q6 carrier fail-closed; no partial automation | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_mode_switch.py` | state machine; idempotent re-confirm; rollback; in-flight Layer 2 not cancelled | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_scans.py` | reconciliation-scan idempotency (uuid nonce); reconnect → review both modes; watermark | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_review_release.py` | Mode 1 actions; review-release helper (one blocked job; pre-C2/clean-rejection replacement) | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_cod_interplay.py` | COD scenarios 4–13 state derivation; `stock.return.picking` only restoration | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_state_model.py` | 7 Layer-A families raw+normalized; unknown-future-value; Delivered-inconsistency | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_lifecycle.py` | job-type sink + dedicated trigger-origin normalization; zero residue; either order | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_readiness.py` | `REQUIRED_MVP_SCOPES` swap; write-scope; staff NOT_PROVEN; API-version gate | `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_vocabulary_guard.py` | persisted `error_class`/`subreason` ∈ registries; `over_fulfillment` absent | `IMPLEMENTED—RUNTIME PENDING` (static portion `EXECUTED—PASS`) |
| `test_fulfillment_source_guards.py` | the guard families above | static portions `EXECUTED—PASS`; registry portion `IMPLEMENTED—RUNTIME PENDING` |
| `test_fulfillment_concurrency.py` | operation-scope serialization; shared-reconcile handoff; harness contract | harness contract `EXECUTED—PASS`; independent-connection cases `IMPLEMENTED—RUNTIME PENDING` |
| `runtime_layer2_fulfillment_concurrency_harness.py` | genuine independent-process contention (spawn) | contract `EXECUTED—PASS`; process run `IMPLEMENTED—RUNTIME PENDING` (needs a live DB) |
| core `test_readiness_check.py` (edit) | `REQUIRED_MVP_SCOPES` swap assertion | `IMPLEMENTED—RUNTIME PENDING` |

## 6. Genuine concurrency evidence

The out-of-band `runtime_layer2_fulfillment_concurrency_harness.py` uses OS
processes via `multiprocessing.get_context('spawn')` (never `fork`), a
per-process `Registry` + cursor + `Environment`, and real commit boundaries —
mirroring the accepted core harness. Its structural contract is `EXECUTED—PASS`
(AST-verified here). Genuine independent-connection cases
(`test_fulfillment_concurrency.py`: operation-scope serialization via
`db_connect`, shared-reconcile handoff) are `IMPLEMENTED—RUNTIME PENDING` — they
require real pooled cursors on a live database (Gate C).

## 7. Odoo.sh (Gate C) evidence — `IMPLEMENTED—RUNTIME PENDING`

Not executed in Gate B (no Odoo runtime available). The Gate C campaign (locked
prompt §7): exact-head identity; fresh install; upgrade; the focused fulfillment
suite; the complete connector regression; the security matrix; lifecycle +
uninstall/reinstall across the full bridge stack; zero residue; concurrency;
failure + rollback injection; redaction + leak scan.

## 8. Shopify dev-store (Gate D) evidence — `NOT PROVEN`

Not executed and not fabricated. No live Shopify mutation occurred. The Gate D
campaign (locked prompt §8) and **Wave 4 final acceptance require both
fulfillment dev-store validation AND CV-013 (#185) to execute green.**

## 9. CV-013 status

**Issue #185 (`CV-013`) remains OPEN and CRITICAL — not closed or downgraded.**
Wave 4 cannot receive final control-room acceptance, enter a release candidate,
or begin UAT while it is open.

## 10. Pre-runtime adversarial audit — findings + consolidated corrections

One complete pre-freeze adversarial audit was performed (an independent
reviewer pass over every production file + cross-check against the merged core
contracts) before this candidate was frozen. All confirmed defects were fixed
in one consolidated batch; each fix corrected the whole pattern, not just the
first site.

| # | Sev | Finding | Correction |
| --- | --- | --- | --- |
| A1 | **P0** | Both mutation strategies returned `shopify_idempotency_key=''`; the merged core `_validate_prepared_request` hard-requires a **non-empty** string, so **every** `fulfillment_create` / `fulfillment_tracking_update` was rejected pre-C2 (dead outbound path). The Gate A packet's "null/unused" wording is incompatible with the merged Layer 2 request contract. | Both `prepare_preconditions` now supply a non-empty synthetic `uuid.uuid4().hex`. The operation documents carry **no** `@idempotent` directive and never reference the key, so it is persisted on the attempt but **never sent on the wire** (zero Shopify-side effect). "Unused" = no wire idempotency directive. |
| A2 | **P1** | `review-release` `_handoff_replacement` unconditionally wrote `state='cancelled'`; `failed_final → cancelled` is not a legal transition (`LEGAL_JOB_TRANSITIONS`), so releasing a terminal clean-rejection mutation raised. | A terminal `failed_final` predecessor is now **superseded in place** (its operation scope is already released); a cancellable predecessor (`failed_retryable`/`blocked_manual_review`) still cancels + flushes before the replacement is created. |
| A3 | **P2** | The shared reconcile handler validated the reconcile result before the `not_applied → inconclusive` coercion, so a rogue `not_applied` (action `None`) shape was blocked as `duplicate_risk` rather than coerced — the defensive coercion was unreachable. | The handler now coerces any `not_applied` verdict to `inconclusive` **before** validation — real defence-in-depth for the no-resend P0 (the fulfillment callbacks never emit `not_applied`; this guards a future/rogue callback). |
| A4 | **P2** | `_read_order_fulfillments`' nested `fulfillmentLineItems` connection was fetched in one page and not checked for completeness — a fulfillment with >1 page of line items could feed Mode 2 partial data (violating §11.4). | `_read_order_fulfillments` now **fails closed** (`FulfillmentReadError`) when any fulfillment's line-item connection reports `hasNextPage` — Mode 2 → review, reconcile → INCONCLUSIVE, inbound → retry (all fail-closed-safe). |

**Invariants independently confirmed to HOLD** (no change needed): the
source/origin matrix at the single `_enqueue_once` choke point; byte-identical
C2↔wire (operation constant + unmutated variables); the Q1 operation-scope
override (mutation types only; reconcile scope `False`); consequence/reconcile
result shapes; Odoo-19 API usage (`stock.move.line.quantity`, `shopify_line_item_gid`,
carrier fields, sudo binding writes); fixed vocabulary (no `over_fulfillment`);
binding field classification; the Mode 2 double-fulfillment-loop guard (bind
before validate); handler return/arg-order.

**No known P0 or P1 remains.** Residual material P2 carried as an
implementation acceptance criterion for the control-room review / Gate C:

- Mode 2 condition 7 (`quantity_mismatch`) is a pass-through that records the
  required quantities; the actual quantity/coverage decision is enforced by
  condition 9 (`_select_deterministic_picking`), so an under-covering picking
  fails closed as `picking_ambiguous` rather than `quantity_mismatch` — a
  reason-label imprecision only; the fail-closed safety holds.
- Condition 14's "fresh live re-read" reuses the evaluation pass's read
  (fetched at condition 3) rather than issuing a second read; the whole
  evaluation is fresh, but a stricter separate re-read is a Gate-C refinement.

## 11. Rollback notes

Single-PR revert of the fulfillment addon; the one named core
`REQUIRED_MVP_SCOPES` edit reverts with it (and its test). The addon owns its
own tables (uninstall drops them); the additive store-settings/binding fields
are additive. Created Shopify fulfillments remain (no auto-unfulfill); Odoo stock
is unaffected by the revert. In-flight fulfillment jobs must reach a
terminal/blocked state before uninstall; mutation-attempt evidence is immutable
audit. Switching a store back to Mode 1 stops future auto-application without
corrupting state.
