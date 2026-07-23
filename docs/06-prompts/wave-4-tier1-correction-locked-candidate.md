# Wave 4 Tier-1 Correction — Locked Candidate Implementation Prompt

> **NOT AUTHORIZED FOR USE.** This is a candidate prompt only. Per the
> governing synthesis-reset task, use of this prompt requires the control
> room to first accept `wave-4-tier1-correction-synthesis.md` and this
> ledger. Do not issue this prompt as a live session instruction until that
> acceptance is recorded.

---

## Role

You are the Wave 4 Tier-1 correction implementation worker for `AdamsOdoo/Adams`, under CLAUDE.md §13 (Claude is the default implementation worker for `mvp/program-integration` work; DEC-039/DEC-040 govern). You implement; you do **not** review, accept, ready-mark, or merge your own work. Independent review of your work is a **separate top-level Claude session or a fresh subagent invocation**, never this session/thread.

## Base and expected head

- **Exact base:** the docs-only synthesis head produced by the synthesis-reset session that authored this prompt (recorded in `wave-4-tier1-synthesis-handoff.md` and the PR #189 body at the time this prompt is issued) — **verify live before starting**; do not assume the SHA in this file's original draft is still current.
- **Branch:** `claude/wave-4-fulfillment-gate-b` (continue on the existing PR #189 branch — do not create a new branch or PR).
- **Expected new head:** one final correction candidate, produced as one coherent campaign with ordered internal stages (per the synthesis's recommended structure **B**), not many small correction cycles.

## Complete allowed production files

Confined to `addons/shopify_connector_fulfillment/**` — no `shopify_connector_core`/`_sale`/`_inventory`/`_product` file may be touched:

- `models/stock_picking.py`
- `models/shopify_connector_fulfillment_admission.py`
- `models/shopify_connector_fulfillment_scans.py`
- `models/shopify_connector_fulfillment_inbound.py`
- `models/shopify_connector_job.py` (fulfillment-side scope-key override only)
- `models/shopify_connector_fulfillment_mode2.py`
- `models/shopify_connector_fulfillment_inbound_evidence.py`
- `models/shopify_connector_fulfillment_reader.py`
- `models/shopify_connector_fulfillment_create_strategy.py`
- `models/shopify_connector_store_settings.py` (only if a new watermark/overlap/lookback config field is required)

## Complete allowed test files

- `tests/test_fulfillment_trigger.py`
- `tests/test_fulfillment_admission.py`
- `tests/test_fulfillment_scans.py`
- `tests/test_fulfillment_mode_switch.py`
- `tests/test_fulfillment_concurrency.py`
- `tests/runtime_layer2_fulfillment_concurrency_harness.py`
- `tests/test_fulfillment_mode2_engine.py`
- `tests/test_fulfillment_inbound_evidence.py`
- `tests/test_fulfillment_matching.py`
- `tests/test_fulfillment_reader_pagination.py` (only if a shared helper needs a new fixture variant)
- `tests/test_fulfillment_create_strategy.py`
- `tests/test_fulfillment_vocabulary_guard.py`
- `tests/test_fulfillment_inbound_classification.py`
- `tests/test_fulfillment_location_resolution.py`

No new test filename may be created — every fix lands in an existing, already-frozen test file.

## Complete allowed documentation files

- `docs/05-qa/task-014-fulfillment-tracking-validation-results.md` (record the correction campaign's evidence)
- `docs/05-qa/wave-4-tier1-findings-ledger.md` (mark each theme's disposition as `CORRECTED` once implemented — do not alter the historical record of what the review found)
- `docs/07-implementation-plan/mvp-program-state.md` (Wave 4 Gate B tracker row)
- `docs/01-research/research-handoff.md` (top entry only)
- `docs/05-qa/architecture-review-log.md` (one new sequential AR row for this correction)
- `docs/02-product/fulfillment-operating-modes.md` (Theme H's new review-reason annotation only, classified `[Proposed product decision]`)
- `docs/05-qa/fulfillment-mode-uat-matrix.md` (Theme H annotation; new UAT rows for Theme B's multi-line partial-fulfillment scenario if desired)

## Forbidden files

- Any file under `shopify_connector_core/**`, `shopify_connector_sale/**`, `shopify_connector_product/**`, `shopify_connector_inventory/**` (Themes D and L's would-be fixes live here — **explicitly excluded from this correction**, see below).
- Any file under `docs/07-implementation-plan/wave-5-u1-gate-a/**` (PR #194 remains frozen; do not touch).
- Any manifest, security CSV/XML, CI/workflow file.
- Any new test filename.
- Any new job_type/trigger_origin/error_class/manual_review_subreason selection value beyond Theme H's one new, explicitly-authorized review-reason value.

## Findings this prompt authorizes correcting (11 of 13 themes)

Implement, in this dependency order (per the synthesis's §3 coupling analysis):

1. **Theme G** (vocabulary-guard genuineness) — must land before or with Theme H, since Theme H registers a new value through this guard.
2. **Theme H** (Mode-1 review-reason relabel) — depends on Theme G.
3. **Theme A** (P0-A: `_enqueue_once` transaction poisoning) — `W4-R-P0-001`, `W4-R-P1-001..004`, `W4-S-ADD-001`.
4. **Theme E** (watermark scan boundary) — touches the same file as Theme A; sequence carefully to avoid merge friction.
5. **Theme C** (FO-line quantity/UoM aggregation) — implement before or with Theme B.
6. **Theme B** (P0-B: Mode-2 partial-fulfillment picking-selection integrity + ledger wiring) — `W4-R-P0-002`, `W4-R-P1-005`. **The single most architecturally significant correction; do not treat as routine.**
7. **Theme F** (direct-result status classification).
8. **Theme I** — `W4-R-P2-006` (`F-6`) **only**. Do **not** attempt `W4-R-P2-007` (`F-4`) — it requires a separate architecture decision (see Forbidden below).
9. **Theme J** (`_has_unresolved_create_attempt` terminal-state gap — use `TERMINAL_JOB_STATES`, not a hand-added literal).
10. **Theme K** (concurrency-harness rigor — exit-code assertions + AST-guard strengthening).
11. **Theme M** (governance-doc corrections) — already applied by the synthesis-reset session's own commit; verify still correct at your head, do not re-apply.

## Explicitly NOT authorized by this prompt

- **`W4-R-P1-007` (Theme D)** — multi-company `ir.rule` gap on `shopify.connector.job`/`.mutation.attempt`. Requires a new control-room-scoped DEC and touches `shopify_connector_core`. Do not implement.
- **`W4-R-P2-007` (`F-4`, part of Theme I)** — picking-warehouse cross-check against the resolved Shopify location. Requires an architecture decision closing DEC-011's open "exact mechanism" item. Do not implement; do not read `shopify.connector.location.mapping`; do not add Odoo-location storage to `shopify.connector.location`.
- **`W4-R-P2-011` (Theme L)** — U0 dashboard job-type labels. Lives in `shopify_connector_core`, explicitly forbidden for Wave 4 by `wave-4-definition-of-ready.md` §3. Do not implement.

## Acceptance criteria

The acceptance criteria for each of the 11 authorized themes are the exact criteria listed per-theme in `wave-4-tier1-correction-synthesis.md` §2 and `wave-4-tier1-findings-ledger.md` §3 — restated here as the binding checklist:

- [ ] All 8 `_enqueue_once` call sites (Theme A) are savepoint-wrapped; the two whole-store scan job types no longer share an operation-scope key; a companion recompute step exists for pre-upgrade non-terminal rows of those two job types.
- [ ] A two-line consolidated picking with a single-line partial Shopify fulfillment no longer validates the sibling, un-evidenced line (Theme B); `_c6_no_overrun` reads a real cross-fulfillment ledger keyed consistently (no `fo_line_item_gid`/`line_item_gid` mismatch).
- [ ] A lot/serial-split shipment whose individual move-line quantities each pass but jointly exceed `remainingQuantity` is rejected (Theme C); UoM normalization is applied before comparison.
- [ ] All three scan handlers (Theme E) derive their boundary from the watermark (mode-switch scan: full PD-B4 formula, 30-day default lookback); a bounded one-time catch-up pass covers pre-fix-skipped records.
- [ ] `_classify_direct_fulfillment_create` requires `status == 'SUCCESS'` (Theme F).
- [ ] The vocabulary-guard test is AST-derived, checks both containment directions, and the line-84 tautology is removed (Theme G).
- [ ] The routine Mode-1 observation case uses a new, distinct review-reason value, never `'remote_state_changed'` (Theme H).
- [ ] `_resolve_single_location` fails closed on `shopify_location_active == False` (Theme I, `F-6` only).
- [ ] `_has_unresolved_create_attempt` uses `TERMINAL_JOB_STATES` (Theme J).
- [ ] All 9 concurrency-harness runners assert exit codes; the AST guard requires genuine `Event`/`Queue` synchronization evidence, an actual exitcode comparison, a fixture-scoped durable query, and correct-arity cleanup; the guard's own bundled acceptance example is no longer hollow (Theme K).

## Negative tests (must exist, per theme)

- Theme A: two sequential tracking writes on the same picking while a prior job is non-terminal — the second write's own change must persist.
- Theme B: a two-line picking, single-line partial fulfillment — the sibling line's `stock.move.state` must not become `'done'`; a second, separate Fulfillment event cumulatively exceeding ordered quantity must be rejected.
- Theme C: two move lines on one FO-line jointly exceeding `remainingQuantity` while individually compliant — must raise `ambiguous_match`.
- Theme E: >200-binding fixture for each of the three scan handlers — a blocker outside the old fixed window must still be caught.
- Theme F: a `fulfillment` dict with a real `id` and a non-SUCCESS/absent `status` alongside empty `userErrors` — must not classify as `succeed`.
- Theme H: a regression test asserting Mode-1 observation never yields `'remote_state_changed'`.
- Theme I: a cached, deactivated location — must raise `ambiguous_match`.
- Theme J: a job left `cancelled` (and separately `failed_final`) with no `mutation_attempt` — must not permanently block origin confirmation.
- Theme K: a synthetic runner shaped like the current real 7-runner "captures but never compares" pattern — the strengthened guard must reject it.

## Static checks (before any commit)

- `py_compile` clean across every changed file.
- No `addons/**` file outside the allowed list touched.
- No new job_type/trigger_origin/error_class/manual_review_subreason value beyond Theme H's one authorized addition.
- No re-introduction of any entry in `docs/05-qa/rejected-approaches-log.md`.
- `test_fulfillment_source_guards.py` and all frozen guard tests still pass unmodified.

## Migration / upgrade / uninstall checks

- Theme A's scope-key formula widening: verify a companion recompute step for existing non-terminal rows of the two affected job types (or document why none is needed if no such rows can exist pre-merge).
- Theme E's watermark boundary: verify the one-time catch-up pass is idempotent and does not create duplicate evidence/review cases on replay.
- No destructive migration is authorized by this prompt.

## Concurrency requirements

- Preserve the `UNIQUE(store_id, operation_scope_key)` constraint's cross-process concurrency-safety property unchanged (still refuses a truly concurrent duplicate insert) in both the sequential and genuinely-concurrent reproduction of every Theme A finding.
- Theme B's cross-fulfillment ledger read/write must not reintroduce a TOCTOU window — apply the same fail-closed re-verification discipline Condition 14 already uses.
- Theme K changes only test-infrastructure genuineness — it must not alter the actual concurrency semantics already proven by the 9 scenarios.

## Runtime requirements

- Full frozen fulfillment/sale/inventory suites must re-run green on a fresh, exact-SHA Odoo.sh build after this correction, per DEC-040's mandatory runtime-evidence rule (proportional to this batch's risk and size — this is a Tier-1 mutation-safety/concurrency/data-integrity batch, so full rigor applies, never a lighter skim).
- The nine-process external-multiprocessing campaign remains `DEFERRED BY PRODUCT OWNER — NOT PROVEN` — this correction must not claim it as executed, and Theme K's harness-rigor fix does not itself constitute execution.
- Issue #193's baseline warm-update signatures remain the separate baseline owner — do not re-litigate.

## Shopify prohibition

No live Shopify request or mutation is authorized by this prompt. Any live Shopify validation remains gated by issue #185 (CV-013), unaffected by this correction.

## No self-review / no ready-mark / no merge

The implementing session may not review, accept, ready-mark, or merge its own correction. Independent Claude review (a separate top-level session or a fresh subagent instructed to adversarially re-verify, never summarize) is the default routine gate per DEC-039/DEC-040. ChatGPT review remains an available strategic spot-check, not a prerequisite.

## Exact stop condition

Stop and return to the control room when:

- all 11 authorized themes are implemented, tested, and statically verified; **or**
- a genuinely new candidate-owned P0/P1/material-P2 is discovered during implementation (a synthesis/reset hard stop per the existing Wave 4 gate rules, not authorization for an ad-hoc patch); **or**
- any of the "must not" boundaries above would be violated by the only available correction (escalate rather than improvise).

Do not begin Gate D, Wave 5, U1, U2, or U3 work. Do not touch PR #194. Do not mark this PR ready. Do not merge.
