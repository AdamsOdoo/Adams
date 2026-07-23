# Wave 4 Tier-1 Correction Synthesis — PR #189

> **Status: TIER-1 FINDINGS SYNTHESIZED — CORRECTION NOT YET AUTHORIZED.**
> Companion to [`wave-4-tier1-findings-ledger.md`](../05-qa/wave-4-tier1-findings-ledger.md).
> No production, test, or runtime correction was performed to produce this
> document. No Odoo.sh runtime was executed. No Shopify request or mutation
> occurred.

---

## 1. Methodology (high-power research mode justification)

Per CLAUDE.md's "High-power research mode" section, this is the required statement before this session's 23-agent verification fan-out:

- **Why high-power mode was needed:** the control-room ruling requires *independent* re-verification of 24 findings against exact source (not reliance on the reviewer's summary), plus extraction of ~10 governing documents (some exceeding 2,000 lines), plus a U1 (PR #194) impact assessment — a volume of exact-source, line-cited verification that benefits from parallel, dimension-scoped reading rather than a single sequential pass.
- **What each agent investigated:** 13 root-cause-theme verification agents (one per theme A–M below, each re-deriving the reviewer's claims from the actual checked-out source at commit `2d9cff0`); 9 context-extraction agents (DEC-031, DEC-036, DEC-038, DEC-039/040, `fulfillment-operating-modes.md`, `shopify-fulfillment-status-model.md`, the two UAT matrices, `rejected-approaches-log.md`, the architecture-review-log/technical-debt-register consistency check, and the Gate A/B packet inputs); 1 U1 (PR #194) impact agent.
- **Authoritative sources:** the exact reviewed git commit (`2d9cff0`) and exact base (`dd0af5d9`) in a dedicated read-only worktree; the exact PR #194 head (`b38e687`) in a second read-only worktree; all governing DECs/product docs/QA docs in-repo; live shopify.dev fetches for the Shopify `FulfillmentStatus` enum (Theme F).
- **Files updated:** exactly the four canonical synthesis documents plus five existing trackers, listed in §10 of the governing prompt — no `addons/**` file, no test file, no manifest/CI file.
- **Stop condition:** all 24 reviewer findings dispositioned; count discrepancy explained; root-cause themes built; one locked correction prompt drafted; one commit pushed; PR/issue handoffs posted. No correction implementation.
- **Synthesis/verification method:** each theme agent independently re-read full files (not samples), quoted exact line ranges, and produced a disposition with reasoning citing exact code — see the per-theme summaries below, condensed from the full verification transcripts retained in this session's record.
- **Unsupported-claims prevention:** every claim below is either (a) a direct quote/paraphrase of source code or governing docs (labelled Fact), (b) an explicit Inference flagged as such where a primary citation is not yet captured (e.g. Theme C's UoM-override claim), or (c) a Recommendation subject to control-room review. No claim is asserted as Decided beyond what the cited DECs/rulings actually decided.

---

## 2. Root-cause synthesis by theme

Each theme below repeats only what's new beyond the ledger (production/test/doc files, migration, backward-compatibility, concurrency, Layer-2, security/multi-company, uninstall/upgrade, acceptance criteria, rollback). See the ledger for the underlying defect description and disposition.

### Theme A — Transaction-safety around `_enqueue_once` (P0-A baseline)

- **Findings:** `W4-R-P0-001`, `W4-R-P1-001..004`, `W4-S-ADD-001`.
- **Production files:** `stock_picking.py`, `shopify_connector_fulfillment_admission.py`, `shopify_connector_fulfillment_scans.py`, `shopify_connector_fulfillment_inbound.py`, `shopify_connector_job.py`.
- **Test files:** `test_fulfillment_trigger.py`, `test_fulfillment_admission.py`, `test_fulfillment_scans.py`, `test_fulfillment_mode_switch.py`, `test_fulfillment_concurrency.py`, `runtime_layer2_fulfillment_concurrency_harness.py`.
- **Docs:** none beyond the ledger/synthesis/tracker set.
- **Migration/upgrade/uninstall:** `operation_scope_key` is a stored, computed `Char` field. Widening its formula for `fulfillment_reconciliation_check`/`fulfillment_mode_switch_scan` does not add a column, but an Odoo upgrade does **not** automatically recompute already-stored values for untouched existing rows — a companion recompute/migration step is needed for any pre-upgrade non-terminal rows of these two types, or the fix is inert for in-flight jobs until their next state-change re-triggers the compute.
- **Backward-compatibility:** none of the 5 production files' external contracts change shape; only internal error-handling and one computed-field formula change.
- **Concurrency:** the reproduction needs **no true OS concurrency** for the tracking-admission and reconciliation-cron cases (two sequential calls in one process suffice) — but the same `UNIQUE(store_id, operation_scope_key)` constraint is also the genuine cross-process concurrency guard (proven by `test_fulfillment_concurrency.py`'s two-cursor test and the runtime harness). The savepoint fix must preserve the constraint's concurrency-safety property in both the sequential and genuinely-concurrent case.
- **Layer-2 implications:** DEC-036 (Wave 3 Layer 2 gate) is **silent** on both savepoint-wrapped enqueue and job-type-aware scope keys for scan job types — Wave 4 is free to design both, provided the design does not violate the binding C1/C2/NET/C3 cursor/commit discipline or the no-blind-resend/reconcile-first rule for the two mutation job types (unaffected by this theme), and provided the reconciliation-registry fail-closed gate is respected. DEC-031 is the canonical decision governing this exact failure class in the abstract (a transaction-scoped row lock alone does not durably own a job across a rollback) and supplies the umbrella acceptance gate this design must sit within.
- **Security/multi-company:** none of the five defects touch access control or cross-store exposure; the `UNIQUE` constraint is already correctly store-scoped, so every collision discussed is strictly intra-store.
- **Rejected-approaches check:** no match in `rejected-approaches-log.md` (RA-001…RA-024) for savepoint-wrapped enqueue or job-type-aware scope keys for scan jobs.
- **Acceptance criteria:** see the ledger; summarized — a second sequential tracking write while a prior job is non-terminal must complete without discarding its own change; a tracking-admission enqueue collision must end in a classified state, never crash `run_drain()`; a per-store reconciliation-cron collision must not starve every other store; `action_start_mode2_switch` must never raise a raw DB exception to an admin; the two scan job types must stop colliding under the generic key; all 8 `_enqueue_once` call sites must be savepoint-wrapped.
- **Rollback:** each savepoint wrap is an independently-revertable diff hunk with no cross-file coupling; the scope-key formula change is separately revertable and, because it changes a currently-enforced (if accidental) mutual exclusion between the two scan job types, should be reviewed independently of the pure defect-correction savepoint fixes.

### Theme B — Mode-2 picking-selection integrity (P0-B baseline)

- **Findings:** `W4-R-P0-002`, `W4-R-P1-005`.
- **Production files:** `shopify_connector_fulfillment_mode2.py`, `shopify_connector_fulfillment_inbound_evidence.py`.
- **Test files:** `test_fulfillment_mode2_engine.py`, `test_fulfillment_inbound_evidence.py`.
- **Correction boundary (binding P0-B baseline per control-room ruling):** `_quantity_compatible_pickings`/`_c9_picking`/`_validate_picking_local` must reject/exclude any candidate picking whose `move_ids` contains a move for a `sale_line_id` **not** in the current fulfillment's required set, routing to a named review reason rather than proceeding to validate. Odoo 19 has no native way to validate only a caller-selected subset of a picking's moves — the only mechanisms are (a) calling `stock.move._action_done()` directly on a hand-picked subset (bypasses picking-level backorder/state machinery this addon's own `_action_done` override depends on) or (b) splitting the required-quantity portion onto its own moves/sub-picking via `_split()` and a backorder before validating. Given the binding-creation-timing coupling (`_bind_external_fulfillment` binds by `picking.id` **before** validation, under `UNIQUE(store_id, picking_id)`) and the interaction with reservation/lot-serial checks that already run picking-wide, **a picking split is materially riskier and touches more surface than rejecting to review** — reject-to-review is the correct, minimal scope for this correction. A cross-fulfillment reconciliation-ledger writer must also be added: the natural, safe point is inside `_apply_mode2`, immediately **after** `_validate_picking_local` succeeds and evidence is marked `applied` (writing at evaluation time would record a quantity for a fulfillment that could still fail validation). `_c6_no_overrun` must be rewritten to sum reconciled quantity from **other** evidence records for the same order line (not the current record's own, always-empty `line_ids`), and the GID-key mismatch (`fo_line_item_gid` vs. order-level `line_item_gid`) must be resolved as part of this change.
- **Must not:** silently validate the entire picking as a fallback; broadly rewrite `_apply_mode2`, `_bind_external_fulfillment`, `_carrier_would_book`, or the 14 unaffected conditions; change `reconciled_quantity_ledger()`'s own arithmetic (already correct in isolation); introduce speculative picking-splitting/backorder redesign when reject-to-review satisfies the fail-closed requirement with far less blast radius.
- **DEC-038 constraints (Wave 4 Gate A, item-by-item, binding contract):** fulfilled quantity = the picking's per-line **done** `stock.move.line.quantity`, ≤ a **freshly re-read** FO-line `remainingQuantity`; each validated picking (including each backorder picking) fulfills exactly its own done quantities, "no partial automation within one create, unresolved partials → review"; Condition 6 is `PRESERVE` (enforced by the ledger + `remainingQuantity`) and Condition 12 (no duplicate application) also consumes the ledger as dedup evidence; DEC-038 explicitly "decides no exact Odoo field names or code; those are Gate B" — so this correction has latitude to name/implement the ledger mechanism, but not to alter the fixed behavior (enforcement + corroboration + dedup-mirroring + fail-closed-to-review). No new `ERROR_CLASS_SELECTION`/`MANUAL_REVIEW_SUBREASON_SELECTION` value may be introduced (e.g. `over_fulfillment` must not be reinstated) without a separate control-room amendment; quantity-exceeds-remaining classifies as `ambiguous_match`.
- **Migration/upgrade/uninstall:** no schema/data migration — this is a behavior change (a currently-unused table, `shopify.connector.fulfillment.inbound.evidence.line`, gets its first real writer), not a schema change. No uninstall-hook implication.
- **Concurrency:** not itself a race — both bugs are deterministic logic gaps on a single evaluation pass. The fix must be correct under concurrent Mode-2 evaluations of two separate Fulfillment events on the same order (the cross-fulfillment ledger read/write must not reintroduce a TOCTOU window a naive read-then-decide implementation could create) — apply the same fail-closed re-verification discipline Condition 14 already uses for remote state.
- **Security/multi-company:** not assessed as in-scope for this theme (no ACL/record-rule/company-scoping code touched); flagged for the implementing session to confirm.
- **U1/backend-contract implications:** **highest-impact theme** for PR #194 — see §4 below; classified `revalidation_required`.
- **Rollback:** both corrections are additive/restrictive (reject-to-review is stricter than current behavior; a ledger writer adds new writes but doesn't change existing `applied`-evidence semantics) — a straightforward revert with no data migration created.

### Theme C — FO-line quantity/UoM aggregation

- **Findings:** `W4-R-P1-006`, `W4-R-P2-001`.
- **Production files:** `shopify_connector_fulfillment_reader.py` (`_match_picking_to_fo_lines`, lines 264-341; possibly one small adjacent private helper).
- **Test files:** `test_fulfillment_matching.py`, `test_fulfillment_admission.py` (shares the same blind-spot fixture helper).
- **Correction boundary:** group done move lines by resolved `fo_line_id`; sum UoM-normalized quantities per group before any `remainingQuantity` comparison; emit exactly one `{'id','quantity'}` entry per `fo_line_id`; preserve the existing non-aggregation-related fail-closed checks (missing GID → `mapping_missing`; one order-line matching >1 FO line → `ambiguous_match`); preserve the external return shape so `shopify_connector_fulfillment_create_strategy.py` and `shopify_connector_fulfillment_admission.py` require zero changes.
- **Must not:** rewrite the 2-hop reverse-index build (correct, unrelated); touch `_resolve_single_location`/pagination primitives; touch the two call sites' contracts; refactor `_c11_lot_serial` into the reader (a different aggregation check for a different purpose — may be read as reference only).
- **Migration/upgrade/uninstall:** none — pure Python logic fix, no fields/schema/data change.
- **Concurrency:** not applicable — a pure single-call computation gap, invoked twice per picking lifecycle (admission-time and C2-preconditions-time) through the same shared function; one fix closes the gap for both call sites with no locking changes.
- **Security/multi-company:** none directly; the real-world consequence is business-correctness (an over-committed payload could reach Shopify ahead of the FO's true `remainingQuantity`).
- **U1/backend-contract implications:** `likely_changed` — the evidence-line fields (`quantity`, `reconciled_quantity`, `reconciled_quantity_ledger()`) that Theme B also touches change in computed value for real scenarios; `quantity_overrun`/`quantity_mismatch` review-reason firing conditions should be re-checked against the corrected aggregation.

### Theme D — Multi-company record-rule gap (`shopify.connector.job`/`.mutation.attempt`)

- **Finding:** `W4-R-P1-007` — **OUTSIDE ACCEPTED WAVE 4 SCOPE, requires a new DEC.**
- **Would-be production files (future, separate DEC):** `shopify_connector_core/models/shopify_connector_job.py` (a resolvable company path from `res_model`/`res_id` — none exists today), `shopify_connector_core/security/shopify_connector_security.xml`.
- **Would-be test files:** `shopify_connector_core/tests/test_security_hardening.py` (extend) or a new `test_multi_company_isolation.py`.
- **Why this cannot be closed inside PR #189/this wave:** the fix touches `shopify_connector_core`, which is explicitly forbidden by the locked Gate B prompt's allowed/forbidden-files list without a control-room amendment; and no ORM-traversable company path exists on `shopify.connector.job` today (`shopify.connector.store` has no `company_id`), so this is not a mechanical `ir.rule` port — it is new design work.
- **Migration/upgrade/uninstall (for the future fix):** additive (`ir.rule` is evaluated at access time, not persisted) and reversible without data migration; the new company-resolution field/compute would need LC-1 uninstall/reinstall compatibility review.
- **Security/multi-company:** real, currently-unmitigated cross-company read exposure (both models) and cross-company write exposure (job rows only, non-protected fields/sanctioned actions) via direct RPC for the shared, non-company-scoped Operator/Reviewer groups. Root cause predates this PR and affects every domain equally.
- **U1/backend-contract implications:** `revalidation_required` — PR #194 already reads `shopify.connector.job`/`.mutation.attempt` for lineage display; its role-gate/visibility model today only reasons about the two SEC-2 roles + four internal groups, not `ir.rule` company scoping on these two models — a genuine silent gap in the current U1 contract inventory (§8), independent of this theme's own fix timing.
- **Recommended handling:** log as a required future control-room decision (new DEC, core-scoped); do **not** fold into this PR's correction batch; does not block this PR's own merge gate any more than the pre-existing gap already did for every prior wave.

### Theme E — Fixed 200-row scan window vs. watermark boundary

- **Findings:** `W4-R-P1-008`, `W4-R-P1-009`, `W4-R-P2-002`.
- **Production files:** `shopify_connector_fulfillment_scans.py` (all three handlers, `RECONCILE_BATCH` constant), `shopify_connector_store_settings.py` (only if new boundary-support fields are needed).
- **Test files:** `test_fulfillment_scans.py`, `test_fulfillment_mode_switch.py`.
- **Correction boundary:** replace all three fixed `limit=200` queries with logic deriving a scan boundary from `fulfillment_last_reconciliation_at` (reconciliation-check, reconnect-catchup) or the full PD-B4 earlier-of(watermark-minus-overlap, latest-unresolved-evidence-boundary) formula with its 30-day bounded default lookback (mode-switch scan **only** — the 30-day figure is specific to PD-B4/the switch scan in the product doc, not a general figure for the other two handlers); paginate/loop to completion within a fail-closed safety cap per the frozen §11.4 cursor contract, never silently truncating and treating a partial pass as "clean"/"complete." The watermark write must only advance once a pass is known-complete.
- **Must not:** touch `shopify_connector_fulfillment_reader.py`'s GraphQL cursor pagination (a different, already-correct layer); introduce any new `job_type`/`trigger_origin`/`error_class`/`manual_review_subreason` value (frozen per DEC-038 §7.2/§7.3); rewrite `_flag_cancelled_binding`, `_refresh_binding_snapshot`, or the mode-switch abort/complete transitions (correct, untouched).
- **Migration/upgrade/uninstall:** the watermark field itself needs no schema change (already an unconditionally-written nullable `Datetime`). There is a real **operational** backfill implication distinct from schema migration: the buggy fixed-window behavior has already silently starved bindings beyond the window on every store that has run this cron. The correction should include one bounded, idempotent full-catchup pass over pre-existing bindings/order-bindings before switching to a strictly watermark-forward cadence, so records created during the buggy window are not permanently skipped when the fix lands. No uninstall/lifecycle implication.
- **Concurrency:** not a DEC-036/DEC-031 concurrency defect (all three handlers are already `local_only`/`remote_read_replay_safe`); the relevant risk is temporal (a store's binding count grows monotonically, so the blind spot only widens) — the fix must ensure watermark advancement commits only after a scan pass is known-complete, so a crash mid-scan cannot advance the watermark past unprocessed records.
- **Security/multi-company:** none introduced; all three handlers remain store-scoped. Indirect safety-adjacent consequence: `W4-R-P1-008`'s false "clean" declaration lets an Administrator unknowingly enable Mode 2 (auto stock-mutating) while a real unresolved conflict exists outside the scan's blind spot.
- **U1/backend-contract implications:** `likely_changed` — `fulfillment_last_reconciliation_at` and `action_start_mode2_switch()`'s "clean scan" legal precondition are read by PR #194's wizard/mode-switch-consequences display; the real-world completeness of what counts as a "clean scan" should be re-verified once the watermark mechanism actually changes.
- **Rejected-approaches check:** no match for watermark/cursor-based scan boundaries with lookback windows.

### Theme F — Direct-result success classification

- **Finding:** `W4-R-P2-003`.
- **Production files:** `shopify_connector_fulfillment_create_strategy.py` (`_classify_direct_fulfillment_create`, lines 296-347 only).
- **Test files:** `test_fulfillment_create_strategy.py`.
- **Correction boundary:** after establishing `fulfillment_id` is truthy, add a guard that `status == 'SUCCESS'`; if not, return the existing `_uncertain_consequence(...)` helper (routing to `reconcile`, not `fail_final` — a non-SUCCESS status is not proof of non-application either), mirroring the shape of the existing `not fulfillment_id` branch immediately above it.
- **Must not:** touch the reconcile-path functions (already correct); touch `_apply_consequence_fulfillment_create`/`_upsert_fulfillment_binding` (simply never invoked with `action=='succeed'` for this case once fixed); reclassify a non-SUCCESS response as `fail_final`/`failed_clean` (would introduce an unauthorized new-job-creation trigger with no positive non-application evidence); modify the GraphQL document or transport callback; pull in the unrelated inbound-webhook `_normalize_fulfillment_status` helper (different pipeline).
- **Migration/upgrade/uninstall:** none.
- **Concurrency:** none — pure single-call classification logic.
- **Security/multi-company:** none.
- **U1/backend-contract implications:** `likely_changed` — `fulfillment_status_is_success` (the A4 automation-authority flag PR #194's contract inventory documents) changes value for at least the deprecated `OPEN`/`PENDING` cases; acceptance A22 (status-badge layer correctness) and the Mode-2 "condition 2 gate" scenario mapping should be re-verified.

### Theme G — Vocabulary-guard test genuineness

- **Finding:** `W4-R-P2-004`. **Test-only; zero production files.**
- **Test files:** `test_fulfillment_vocabulary_guard.py` only.
- **Correction boundary:** replace the hand-maintained containment check with an AST/source-derived scan mirroring `test_fulfillment_source_guards.py`'s `_model_sources()`/`_string_constants()` pattern, resolving both inline literals and named module-level constants; assert both containment directions; delete/replace the tautological assertion at line 84; add `'unknown_system_error'` once the scan is genuine.
- **Must not:** touch any production file (`'unknown_system_error'` being persisted is legitimate, already-registered behavior); modify `test_fulfillment_source_guards.py` (correct, reference-only); weaken the file's other already-genuine assertions.
- **Migration/upgrade/uninstall/concurrency/security:** none — test-only.
- **U1/backend-contract implications:** `expected_unchanged`.

### Theme H — Mode-1 review-reason mislabel

- **Finding:** `W4-R-P2-005`.
- **Production files:** `shopify_connector_fulfillment_inbound.py`, `shopify_connector_fulfillment_inbound_evidence.py` (new `REVIEW_REASON_SELECTION` value).
- **Test files:** `test_fulfillment_inbound_classification.py`, `test_fulfillment_vocabulary_guard.py` (register the new value — direct dependency on Theme G's fix).
- **Correction boundary:** add one new, distinct `REVIEW_REASON_SELECTION` value for the routine Mode-1 case (exact string is a product-owner naming decision — `external_fulfillment_observed` is one candidate); change `_route_observation`'s else-branch to write it instead of `'remote_state_changed'`; update the locking test assertion; register the new value in the Theme-G vocabulary guard; annotate `docs/02-product/fulfillment-operating-modes.md` §2.2 and/or `docs/05-qa/fulfillment-mode-uat-matrix.md` UAT-FM-1.6, classified `[Proposed product decision]` until accepted.
- **Must not:** touch Condition 14's logic/tests (correct, ~11 dedicated tests); touch Condition 16/`mode_not_enabled` (a distinct, already-correct value); expand `FULFILLMENT_PERSISTED_CORE_CLASSES` (the new value is domain-only, like `quantity_overrun`, not a core job class).
- **Migration/upgrade/uninstall:** adding a Selection choice needs no DB migration; any already-persisted rows with `review_reason='remote_state_changed'` that were actually routine Mode-1 observations remain mislabeled unless a follow-up data backfill relabels them — out of scope for the code+test correction itself, flagged as a follow-up for whoever owns that data (no live merchant data exists pre-RC/UAT per CV-013 gating, so this is a low-urgency note, not a blocker).
- **Concurrency/security:** none.
- **U1/backend-contract implications:** `definitely_changed` — PR #194's contract inventory §5.4 lists `remote_state_changed` as one of "20 values, exact"; this theme renames/splits a distinct code out of it, so the exact count and member list must be re-derived from the corrected head, not assumed unchanged.
- **Rollback:** three isolated, independently-revertable one-line-scale changes; no data migration performed.

### Theme I — Location-resolution scoping

- **Findings:** `W4-R-P2-006` (fix now), `W4-R-P2-007` (needs a future architecture decision).
- **Production files (for `W4-R-P2-006` only):** `shopify_connector_fulfillment_reader.py` (`_resolve_single_location`, lines 356-387 only).
- **Test files:** `test_fulfillment_location_resolution.py`, `test_fulfillment_mode2_engine.py`.
- **Correction boundary (`W4-R-P2-006`):** add a fourth fail-closed check — `shopify_location_active == False` → raise `FulfillmentReadError('ambiguous_match', ...)`, matching the function's three sibling checks exactly.
- **Must not (`W4-R-P2-006`):** touch `_c8_location`, `_c14_remote_state`, `_refresh_location_cache`, the `shopify.connector.location` model, or the outbound create-strategy call site — all already correctly propagate/consume `FulfillmentReadError` from this one function, so fixing it here fixes both the inbound (C8/C14) and outbound call sites at once.
- **`W4-R-P2-007` (do not code-fix in this pass):** would-be files are `_c8_location`, `_quantity_compatible_pickings`, `_select_deterministic_picking` in `shopify_connector_fulfillment_mode2.py` — but the fix must **not** read `shopify.connector.location.mapping` (violates DEC-008/DEC-011/DEC-038 Q3-RULED) and must **not** add Odoo-location storage to `shopify.connector.location` (violates its documented invariant). Escalate to the architecture-review log / a DEC amendment closing DEC-011's still-open cross-check-mechanism item.
- **Migration/upgrade/uninstall (`W4-R-P2-006`):** none — `shopify_location_active` already exists and is already populated; only runtime branching changes.
- **Concurrency (`W4-R-P2-006`):** a location could be deactivated by a concurrent `_refresh_location_cache` run between C8's first resolution and C14's second — both independently re-run the (now-fixed) activeness check on each of their own reads, so a deactivation occurring between the two reads is still caught via C14's existing "location evidence changed on second read" fail-closed path; no new locking needed.
- **Security/multi-company:** none for `W4-R-P2-006` (no create/write/unlink group on the location cache model). `W4-R-P2-007` (not fixed here) introduces no new surface either.
- **U1/backend-contract implications:** `likely_changed` — `location_unmapped` is an existing review-reason value PR #194 already documents; the fix most plausibly changes *when* it fires (a previously-silent success path now correctly lands in review) rather than adding a new vocabulary member, though this cannot be fully ruled out without the corrected source.

### Theme J — `_has_unresolved_create_attempt` terminal-state gap

- **Finding:** `W4-R-P2-008`.
- **Production files:** `shopify_connector_fulfillment_inbound.py` (one function only).
- **Test files:** `test_fulfillment_inbound_classification.py`.
- **Correction boundary:** import `TERMINAL_JOB_STATES` from `shopify_connector_core.models.shopify_connector_job` (same pattern already used elsewhere in this addon) and replace the local `('succeeded','skipped')` literal with it.
- **Must not:** introduce a second/local terminal-states literal; touch `_classify_origin`, `_route_observation`, `_observe_fulfillment`, or `_handle_fulfillment_inbound_observation` (correct once the upstream filter is fixed); touch `action_cancel`/`_audit_probe_superseded`/`_create_lifecycle_audit_job` (their attempt-less-only cancellation gating is correct by design and is *why* this bug is 100% reachable, not itself a defect); touch `TERMINAL_JOB_STATES`/`LEGAL_JOB_TRANSITIONS` in core; touch the pre-existing, currently non-diverging `_TERMINAL_JOB_STATES` duplicate in `shopify_connector_ui_dashboard.py` (flagged as adjacent technical debt, out of scope here).
- **Migration/upgrade/uninstall:** none.
- **Concurrency:** none — the change only narrows a read-only search domain to a strict superset of already-terminal states, all with an empty outgoing-transition set.
- **Security/multi-company:** none — the search already scopes by `store_id`.
- **U1/backend-contract implications:** `likely_changed` — touches `origin_confirmed`/`origin_unconfirmed` and `action_release_fulfillment_review`'s legal precondition, both documented in PR #194's contract inventory; no new selection value implied, but real-world reachability should be re-verified.

### Theme K — Concurrency-harness rigor

- **Findings:** `W4-R-P2-009`, `W4-R-P2-010`. **Test-only; zero production files.**
- **Test files:** `runtime_layer2_fulfillment_concurrency_harness.py`, `test_fulfillment_concurrency.py`.
- **Correction boundary:** add exit-code-vs-expected assertions to the 7 non-asserting runners; strengthen the AST guard to require genuine `Event`(`.wait`/`.set`)/`Queue` synchronization evidence (confirmed: **not** `Barrier`/`Lock` — neither is used anywhere in the harness; requiring them would break all 9 real scenarios), an actual exitcode comparison feeding a raise/assert (not bare attribute presence), a fixture-scoped (non-empty-literal) durable query, and a `_finish_cleanup` call matching the real 3-arg production arity; rewrite the guard's own hollow "genuine orchestration" acceptance fixture so it is actually genuine; add a negative test proving the strengthened guard rejects a synthetic runner shaped like the current real 7-runner "captures but never compares" pattern.
- **Must not:** touch any production file; require `Barrier`/`Lock` evidence; make the guard import/execute Odoo or the harness (must stay AST-only); alter the already-correct assertion logic in `mode_switch_interaction`/`rollback_injection_recovery` beyond the noted addition; land any guard-strengthening change without re-verifying it reports zero violations against the real corrected harness.
- **Migration/upgrade/uninstall/concurrency/security:** none — test-infrastructure only; does not change any production locking/serialization behavior or the actual concurrency semantics being proven.
- **U1/backend-contract implications:** `expected_unchanged`.

### Theme L — U0 dashboard job-type labels (out of Wave-4 scope)

- **Finding:** `W4-R-P2-011` — **OUTSIDE ACCEPTED WAVE 4 SCOPE.**
- **Would-be production file (future, separate PR):** `shopify_connector_core/models/shopify_connector_ui_dashboard.py` (`_job_type_label`, lines 430-439 only).
- **Would-be test files:** `shopify_connector_core/tests/test_ui_dashboard.py`; a new cross-addon test (installing both `core` and `fulfillment`).
- **Why not in this PR:** `git diff` across the exact base/head range shows **zero** changes to this file; it lives in `shopify_connector_core`; `docs/07-implementation-plan/wave-4-definition-of-ready.md` §3 explicitly forbids "dashboards/timelines" in Wave 4, reserved for Wave 5.
- **U1/backend-contract implications:** `expected_unchanged` for PR #194's own contract (a different addon), but flagged as an advisory labeling-consistency check once U1 authors its own job-type copy deck for the same ten values.

### Theme M — Governance-document corrections

- **Findings:** `W4-R-P2-012`, `W4-R-P2-013`. **Documentation-only; zero code/test files.**
- **Correction:** applied directly by this synthesis commit — see §7 below (technical-debt-register.md TD-002 status revert; research-handoff.md stale-prompt annotation).
- **Migration/upgrade/uninstall/concurrency/security/U1 impact:** none.

---

## 3. Dependencies among themes

- **Theme H depends on Theme G**: the new Mode-1 review-reason value must be registered by the *corrected* (AST-derived) vocabulary guard, not the hand-maintained one — sequence G before H, or land them in the same commit with G's guard already generalized.
- **Theme C and Theme B** both touch the evidence-line quantity fields and should be implemented with awareness of each other (Theme C's aggregation fix changes the values Theme B's ledger consumes), though they are separately revertable.
- **Theme A's** scope-key formula change (for the two scan job types) and Theme E's watermark-boundary redesign both touch `shopify_connector_fulfillment_scans.py`; they are independent defects (different functions) but should be sequenced or reviewed together to avoid merge-conflict friction within the same file.
- **Themes D and L** are both **out of this PR's implementable scope** and share the same blocking reason (touch `shopify_connector_core`, forbidden by the locked allowed-files list) — they should be tracked together as a small backlog of "Wave-4-adjacent, core-owned corrections requiring a control-room scope amendment," separate from this PR's own correction batch.
- **Theme I's `F-4` sub-finding** depends on a **new architecture decision** (closing DEC-011's open item) before it can be scheduled at all — it has no dependency on any other theme's correction, but must not be silently folded into Theme I's `F-6` fix (which is independent and immediately correctable).
- No other cross-theme coupling was found; the remaining themes (C partial, F, G, J, K, M) are independently correctable with no shared files or shared behavioral contracts beyond what's noted above.

---

## 4. U1 (PR #194) impact summary

Full per-theme classification and the complete reconciliation checklist were produced by a dedicated read-only analysis of PR #194's exact head (`b38e6874c45559dbf1219cfaec43f05ba5fc959a`) against each of the 13 correction themes. Condensed:

| Theme | Classification | Why |
| --- | --- | --- |
| A | expected_unchanged | Internal engine seam (`_enqueue_once`) is never U1-callable; no new vocabulary member expected |
| **B** | **revalidation_required** | Highest impact: touches `fulfillment.binding` lineage/uniqueness, evidence-line ledger fields, the review-reason vocabulary (a new fail-closed path may be added), reconciled-state transitions, and `action_release_fulfillment_review`'s legal precondition |
| C | likely_changed | Evidence-line quantity fields feed both Theme B and U1's quantity-overrun/mismatch badge rows |
| **D** | **revalidation_required** | U1 already reads `job`/`.mutation.attempt` for lineage; contract §8 is currently silent on company-scoping for these two models — a pre-existing gap independent of this theme's fix timing |
| E | likely_changed | `fulfillment_last_reconciliation_at` and the mode-switch "clean scan" precondition are U1-displayed |
| F | likely_changed | `fulfillment_status_is_success` (A4 automation-authority flag) changes value for at least the deprecated OPEN/PENDING cases |
| G | expected_unchanged | Test-only |
| **H** | **definitely_changed** | Directly renames/splits a review-reason value the contract inventory's §5.4 counts as one of "20 values, exact" |
| I | likely_changed | `location_unmapped` firing conditions change |
| J | likely_changed | Touches `origin_confirmed`/the review-release action's legal precondition |
| K | expected_unchanged | Test-only |
| L | expected_unchanged | Different addon; advisory consistency check only |
| M | expected_unchanged | Documentation-only |

**Bounded post-Wave-4 reconciliation checklist for PR #194** (to be executed by a future U1 session, not this one):

1. Confirm the exact corrected Wave 4 head SHA and update every "Wave 4 head inspected" reference across all four Gate A files.
2. Re-run direct extraction of `addons/shopify_connector_fulfillment/**` at the new head — re-derive, do not patch from memory.
3. Re-count/re-list the `review_reason` selection (§5.4) — confirm whether "20 values, exact" still holds given Theme H's rename/split and Theme B's possible new fail-closed value.
4. Re-verify `error_class`(19)/`manual_review_subreason`(9) membership against Theme A's IntegrityError-to-UserError conversion.
5. Re-verify `job.state`(10)/`job_type`(10) membership against Themes A, E, J.
6. Re-inspect `fulfillment.binding.picking_id` and its `UNIQUE(store_id, picking_id)` constraint against Theme B's fix.
7. Re-inspect evidence-line `quantity`/`reconciled_quantity`/`reconciled_quantity_ledger()` against Themes B and C.
8. Re-inspect `fulfillment_status_is_success`/raw/normalized against Theme F's fix; re-run acceptance A22.
9. Re-inspect `fulfillment_last_reconciliation_at` and the mode-switch "clean scan" precondition against Theme E.
10. Re-inspect the multi-company `ir.rule` statement (§8) against Theme D — determine whether §8 needs an explicit addition naming `job`/`.mutation.attempt`.
11. Re-inspect `location_unmapped` triggers against Theme I.
12. Re-inspect `origin_confirmed`/the release action's legal precondition against Theme J.
13. Diff Theme L's corrected dashboard labels against U1's planned copy-deck for consistency (advisory only — confirm the "out of U1 scope" dashboard boundary still holds).
14. Spot-check Themes G/K/M produced no incidental drive-by change to `addons/shopify_connector_fulfillment/**` or any `wave-5-u1-gate-a/**` file.
15. Treat this as a full re-derivation of contract-inventory §5/§12 against the corrected head, not a patch — and route the revalidated inventory through independent Claude review before the U1 gate reopens. **The revalidating session must never self-accept, ready-mark, or merge PR #194.**

---

## 5. Test and runtime correction matrix

| Requirement (from the task's minimum list) | Owning theme(s) | Evidence class expected once implemented |
| --- | --- | --- |
| Sequential duplicate tracking-admission write (no true concurrency needed) | A (`W4-R-P0-001`) | PY (TransactionCase) + Odoo.sh RUN |
| DB uniqueness collision with a usable caller transaction afterward | A (all) | PY + Odoo.sh RUN |
| `_action_done` enqueue collision | A (`W4-R-P1-001`) | PY + Odoo.sh RUN |
| Partial Shopify fulfillment on a multi-line consolidated picking | B (`W4-R-P0-002`) | PY + Odoo.sh RUN — **no existing fixture in the 767-line `test_fulfillment_mode2_engine.py` constructs this; must be added** |
| Exact line/quantity application (aggregation + UoM) | C | PY + Odoo.sh RUN |
| Sibling lines remain unvalidated | B (`W4-R-P0-002`) | PY + Odoo.sh RUN |
| Repeated partial fulfillments (cumulative overrun) | B (`W4-R-P1-005`) | PY + Odoo.sh RUN |
| Backorder interaction | B | Already covered per DEC-038 items 2/4/5/6 — confirm still green after the fix, no new fixture strictly required unless the reject-to-review path changes backorder-chain behavior |
| No duplicate remote effect | Unaffected by any theme | Already `EXECUTED—PASS` (Stage R1/exact-SHA build `35313169`) — re-confirm unchanged |
| Rollback after local validation failure | B | PY + Odoo.sh RUN |
| Binding creation rollback/atomicity | B (`_bind_external_fulfillment` timing) | PY + Odoo.sh RUN |
| Multi-company boundaries | D | **DEFERRED — requires a separate DEC/core fix; NOT PROVEN within this correction, carried forward unchanged from today's equally-unmitigated state** |
| Access/security boundaries | Unaffected (D deferred) | Already `EXECUTED—PASS`; D's gap persists, unchanged by this correction |
| Post-C2 reconciliation | B (new ledger writer) | PY + Odoo.sh RUN — new coverage needed for the ledger's write timing |
| All affected concurrency scenarios | A, K | A: PY (sequential) + Odoo.sh RUN; K fixes the *harness itself* — the underlying 9-process **external multiprocessing runtime execution remains `DEFERRED BY PRODUCT OWNER — NOT PROVEN`, unchanged by this correction** (Odoo.sh webshell `/dev/shm` read-only blocker, per comment `5055294707`) |

**Preserving the nine-process deferment honestly:** this synthesis makes **no claim** that Theme K's harness-rigor fix, once implemented, changes the nine-process campaign's evidence status. It remains `DEFERRED BY PRODUCT OWNER — NOT PROVEN` per the binding product-owner ruling (comment `5055372944`) until an environment with writable multiprocessing synchronization is authorized. Theme K only ensures that *when* that campaign eventually runs, its own success/failure signal is trustworthy.

**No correction test is claimed as executed by this synthesis.** All entries above are prospective requirements for the future correction session, not evidence this session produced.

---

## 6. Recommended correction structure

Per the task's three options:

- **A. One coherent correction batch** — insufficient framing: it doesn't distinguish the ~11 immediately-correctable themes from the 2-3 that need a separate control-room decision.
- **C. Required architecture redesign needing another control-room decision** — too broad: only Theme D (fully), Theme L (fully), and Theme I's `F-4` sub-finding (partially) actually need this; the other ~10 themes are narrow, well-bounded, source-verified, single-file-or-two-file fixes with no architecture conflict (confirmed by every theme-verification agent independently).
- **B. One correction campaign with ordered internal stages on the same branch and PR, producing one final candidate before review** — **recommended.**

**Rationale:** 11 of the 13 root-cause themes (A, B, C, E, F, G, H, I[`F-6` only], J, K, M) are fully correctable within PR #189's existing allowed-files scope (`addons/shopify_connector_fulfillment/**` + its tests + the QA/tracker docs), with no schema change beyond one additive computed-field-formula widening (Theme A) and one currently-dead-table's-first-writer (Theme B) — neither requires a destructive migration. The internal ordering dependencies (Theme H after Theme G; Themes A/E sequenced within the same file; Theme C before/with Theme B) are exactly the kind of "ordered internal stages on one branch/PR" this structure is designed for, consistent with DEC-040's own large-batch-cadence rule ("target a full wave, or a large, coherent, independently-revertable vertical slice of one, per iteration"). Theme D (fully), Theme L (fully), and Theme I's `F-4` (partially) must be **explicitly carved out** of this correction batch — they require a new control-room decision and, for D/L, touch files outside this PR's authorized scope — and tracked as a small separate backlog, exactly as the existing 9-process campaign and issue #185/#193 are already carried outside this PR's merge gate without blocking it.

---

## 7. Migration / upgrade / uninstall analysis (consolidated)

| Change | Migration required? | Detail |
| --- | --- | --- |
| Theme A savepoint wraps | No | Pure error-handling change |
| Theme A scope-key formula widening | **Yes — operational recompute** | Stored computed field; pre-upgrade non-terminal rows of the two affected job types need a one-time recompute so the fix isn't inert for in-flight jobs |
| Theme B reject-to-review + ledger writer | No | Behavior change on a currently-unused table; no schema change |
| Theme C aggregation/UoM fix | No | Pure logic fix |
| Theme E watermark boundary | **Yes — operational one-time catch-up** | The pre-existing bug has already silently skipped bindings beyond the old window; a bounded, idempotent catch-up pass should run once before switching to strict watermark-forward cadence |
| Theme F/G/K | No | Logic/test-only |
| Theme H new review-reason value | No DB migration | Selection choices need none; a **data-relabeling backfill** is a follow-up note, not a blocker (no live merchant data exists pre-RC/UAT) |
| Theme I (`F-6`) | No | Runtime branching only |
| Theme J | No | Pure logic fix, strict superset of prior terminal states |
| Theme M | No | Documentation only |
| Theme D / Theme L / Theme I (`F-4`) | **Not scheduled by this synthesis** | Deferred to future, separately-authorized work |

**Uninstall implications:** none of the correctable-now themes touch `job_type`/`trigger_origin` selection_add/ondelete machinery, so the existing `_reassign_to_historic_job_type`/trigger-origin normalization callables are unaffected.

---

## 8. Rollback strategy (consolidated)

Every correctable-now theme (A, B, C, E, F, G, H, I[`F-6`], J, K, M) is independently, atomically revertable per-file or per-hunk with no cross-theme coupling beyond the sequencing noted in §3 (which affects *implementation order*, not rollback safety — reverting Theme H alone, for example, does not require also reverting Theme G). No theme introduces a destructive data change; the two operational-recompute/catch-up steps (Theme A's scope-key recompute, Theme E's one-time catch-up) should themselves be implemented idempotently so a rollback-then-reapply cannot create duplicate evidence.

---

## 9. Rejected-approaches compliance (CLAUDE.md §10)

All seven candidate correction mechanisms considered for this synthesis (savepoint-wrapped enqueue; job-type-aware scope keys for scan jobs; picking-split/sub-pick vs. reject-to-review for partial fulfillment; a cross-fulfillment quantity ledger; watermark/cursor-based scan boundaries; company-scoping `ir.rule` additions; AST-based test guards) were checked against `docs/05-qa/rejected-approaches-log.md` (RA-001…RA-024, full file read). **Zero matches.** Two are topically adjacent to existing rejections (RA-023 for picking-validation-granularity concepts; RA-020 for autonomous conflict-resolution concepts) but are mechanically distinct and must not drift toward those specific rejected mechanisms.

---

## 10. Locked correction implementation prompt

See [`wave-4-tier1-correction-locked-candidate.md`](../06-prompts/wave-4-tier1-correction-locked-candidate.md). **Use of that prompt is not authorized until the control room accepts this synthesis.**
