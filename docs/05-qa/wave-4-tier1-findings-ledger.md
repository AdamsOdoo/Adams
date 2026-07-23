# Wave 4 Tier-1 Findings Ledger — PR #189 Independent Review Synthesis

> **Status: TIER-1 FINDINGS SYNTHESIZED — CORRECTION NOT YET AUTHORIZED.**
> This is the authoritative, deduplicated, source-verified ledger of every
> finding raised by the independent Tier-1 review of Wave 4 PR #189. It was
> built by a dedicated synthesis session per the binding control-room ruling
> (PR #189 comment `5058826143`), which accepted the review's `REVISE`
> verdict and ordered exactly this normalization before any correction
> implementation. **No production, test, or runtime correction was performed
> to produce this document.**

- **Repository:** `AdamsOdoo/Adams`
- **PR:** #189 ("Wave 4 Gate B: fulfillment and tracking backend")
- **Base:** `mvp/program-integration@dd0af5d94a7f730e738dca955971e00bb4cc9122`
- **Reviewed/rejected head:** `claude/wave-4-fulfillment-gate-b@2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a`
- **Independent Tier-1 review:** PR #189 comment [`5058257403`](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5058257403) — verdict `REVISE`
- **Binding control-room ruling:** PR #189 comment [`5058826143`](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5058826143) — `REVISE ACCEPTED — SYNTHESIS RESET BEFORE ANY CORRECTION IMPLEMENTATION`
- **Verification method:** every finding below was independently re-derived by a fresh reader against the exact reviewed source (a dedicated read-only git worktree pinned to `2d9cff0`), not by trusting the reviewer's summary — see `wave-4-tier1-correction-synthesis.md` §1 for the verification methodology.

---

## 1. Count reconciliation (resolves the 24/25/26 discrepancy)

The review comment states three different totals in different places:

- §1 and §31's closing note: **"26 blocking findings"** / **"26 findings total"**.
- §31's severity subtotals (§32–34): **2 P0 + 9 P1 + 13 material P2 = 24** distinct, named findings (`P0-1`/`P0-2`, `P1-1`…`P1-9`, `F-1`…`F-13`).
- The control-room ruling (comment `5058826143`) additionally asserts the narrative "reports both **25** and 26" findings.

**Resolution.** All three numbers are internally consistent once you separate *distinct root-cause findings* from *raw per-dimension mentions*:

| Count | What it counts | Derivation |
| --- | --- | --- |
| **24** | Distinct, named findings enumerated exactly once in §31's severity-ordered list | `P0-1`, `P0-2` (2) + `P1-1`…`P1-9` (9) + `F-1`…`F-13` (13) = 24. This is the correct, authoritative count of distinct defects. |
| **25** | Raw per-dimension P1 mentions, with the material-P2 double-mention already collapsed but the P1 double-mention *not* collapsed | §25 (Test-quality assessment) explicitly re-raises **both** `P1-5` (the condition-6 test's inability to distinguish real ledger accumulation from dead code) **and** `F-2` (the vocabulary-guard test) a second time, immediately noting "duplicates already counted once each in this report's totals." §34 explicitly states the material-P2 side of this was collapsed ("14 dimension-level findings collapse to 13 distinct root-cause material_P2 items"), but never states the equivalent collapse for `P1-5`'s dimension-level echo. A naive count that applies §34's stated 13-P2 collapse but does **not** additionally collapse `P1-5`'s two dimension mentions yields 2 + 10 + 13 = 25. |
| **26** | Raw per-dimension mentions with **neither** duplicate collapsed | If `F-2` is counted twice (once at §10, once echoed at §25) **and** `P1-5` is counted twice (once at §15, once echoed at §25) — i.e. the naive, uncollapsed dimension-report tally — the total is 2 + 10 + 14 = 26. This matches the review's own headline statements at §1 and §31's closing parenthetical. |

**Verdict:** the correct, authoritative count is **24 distinct findings**. The "26" and "25" headline numbers both come from counting the same two findings (`F-2`, `P1-5`) an extra time because they are *mentioned* in more than one dimension write-up (their "home" dimension, plus an echo in §25's test-quality assessment) — this is explicitly acknowledged by the review's own text ("duplicates already counted once each in this report's totals," §25) but the headline arithmetic in §1/§31 was never corrected to match. **No finding is thereby invalidated** — this is a presentation/arithmetic inconsistency in the review's own summary counters, not a defect in the underlying findings. This synthesis treats **24** as ground truth and additionally logs **one new finding** (`ADDITIONAL-1`, discovered by this synthesis's own independent verification of Theme A, not by the original reviewer) plus **one previously-unlabelled non-blocking observation** (`OBS-1`, present in the review's §8 narrative but never assigned a ledger ID) — see §3 and §4 below.

| Final normalized totals | Count |
| --- | --- |
| P0 | 2 |
| P1 | 9 |
| Material P2 | 13 |
| **Distinct reviewer-raised findings** | **24** |
| New findings surfaced by this synthesis (not in the reviewer's 24) | 1 (`ADDITIONAL-1`, folded into Theme A / P0-A) |
| Named non-blocking observations recoverable from the review text | 1 (`OBS-1`) |
| Tier-3 / further observation / deferred-risk items the review states exist but does not individually enumerate | ~14 (see §5 — **not fabricated**, logged as an open question) |
| Duplicate/merged findings | 0 (no finding was found to be a true duplicate of another; two findings (`F-2`, `P1-5`) are each mentioned in two dimension sections but represent one defect each) |
| Refuted findings | 0 |
| Findings reclassified as outside this PR's implementable scope | 2 (`P1-7` fully; `F-11` fully; `F-4` partially — see §3) |

---

## 2. Extraction and disposition method

For each of the 24 reviewer-raised findings, a dedicated verification agent read the *actual* production/test source at the exact reviewed commit (`2d9cff0`), independently of the reviewer's narrative, and produced: reviewer wording, exact file/line, violated contract, concrete failure mode, production consequence, existing test coverage, missing test coverage, and an independent disposition. See `wave-4-tier1-correction-synthesis.md` §1 for the full methodology and the per-theme verification transcripts (preserved in this session's record).

Disposition vocabulary used below (per the task's required taxonomy):

- **CONFIRMED** — independently re-derived exactly as the reviewer stated.
- **CONFIRMED WITH RECLASSIFICATION** — the underlying defect is confirmed real, but its severity, scope, or correction boundary is refined (broadened, narrowed, or moved outside this PR's implementable scope) based on independent source verification.
- **DUPLICATE** / **PART OF ANOTHER ROOT CAUSE** — not used below; no finding met this bar (see §1).
- **REFUTED** — not used below; no finding was refuted.
- **OUTSIDE ACCEPTED WAVE 4 SCOPE** — the defect is real but its fix requires touching a file outside PR #189's authorized allowed-files list, or requires a new control-room decision, and must not be implemented inside this PR/wave.
- **DEFERRED BY PRODUCT OWNER — NOT PROVEN** — used only for the nine-process concurrency campaign, which remains untouched by this synthesis (see §6).

---

## 3. Full finding ledger

### Root-cause Theme A — Transaction poisoning via unguarded `_enqueue_once` collisions (P0-A baseline)

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P0-001` (reviewer `P0-1`) | P0 | **CONFIRMED** | `stock_picking.py:49-67` |
| `W4-R-P1-001` (reviewer `P1-1`) | P1 | **CONFIRMED WITH RECLASSIFICATION** | `shopify_connector_fulfillment_admission.py:101-134`; `stock_picking.py:24-36,49-67` |
| `W4-R-P1-002` (reviewer `P1-2`) | P1 | **CONFIRMED** | `shopify_connector_fulfillment_admission.py:222-245` |
| `W4-R-P1-003` (reviewer `P1-3`) | P1 | **CONFIRMED** | `shopify_connector_fulfillment_scans.py:201-216` |
| `W4-R-P1-004` (reviewer `P1-4`) | P1 | **CONFIRMED** | `shopify_connector_fulfillment_scans.py:233-253` |
| `W4-S-ADD-001` (new, synthesis-discovered) | P1-equivalent (lower likelihood, same class) | **CONFIRMED** (not reviewer-raised) | `shopify_connector_fulfillment_admission.py:206-211`; `shopify_connector_fulfillment_scans.py:58-62`; `shopify_connector_fulfillment_inbound.py:167-171` |

**Root cause.** Core's default `_compute_operation_scope_key` (`shopify_connector_job.py:722-748`) has no `job_type` component and is backed by a real `UNIQUE(store_id, operation_scope_key)` DB constraint. The fulfillment addon's Q1 override job-type-prefixes the key for the two mutation job types only; the admission/scan job types do not get this prefix, so they can collide with themselves or each other under the generic key. Separately, `_enqueue_once` is a bare search-then-create with **no savepoint** at any of its 8 call sites in this addon; 6 of the 8 (the reviewer's 4 plus 2 more found by this synthesis) catch the resulting `IntegrityError` with a bare `except Exception` (or nothing), leaving the enclosing transaction aborted and silently discarding the caller's own prior work (`W4-R-P0-001`) or crashing an entire dispatch/cron batch (`W4-R-P1-002`/`W4-R-P1-003`) or surfacing a raw DB exception to an admin action (`W4-R-P1-004`).

`W4-R-P1-001` is **confirmed as real** but is best understood as the *general-principle statement* that `W4-R-P0-001`, `W4-R-P1-002`, `W4-R-P1-003`, and `W4-R-P1-004` are each specific instances of — it independently extends the exposure to the `_action_done` path (not just `write()`), and its own count of call sites ("both real call sites") undercounts the true exposure (8 call sites in 4 files). It is retained as its own ledger entry per the task's no-collapsing-without-justification rule, but its correction is inseparable from the other four.

`W4-S-ADD-001` is a **new finding surfaced by this synthesis's own independent verification** (not present in the reviewer's 24/25/26) — three additional unguarded `_enqueue_once` call sites found by a repo-wide grep, at lower individual risk than the four reviewer-named sites but the same defect class. It is folded into Theme A's correction boundary for consistency/defense-in-depth, not counted toward the reviewer's 24.

**Existing/missing test coverage:** see `wave-4-tier1-correction-synthesis.md` §5 (Theme A). In summary: every flagged call site is either untested or its test mocks around the real DB path; one test (`test_fulfillment_scans.py:96-102`) contains a code comment proving the developers already know about the exact collision and manually route around it in the fixture rather than testing the guard.

---

### Root-cause Theme B — Mode-2 partial-fulfillment over-application (P0-B baseline)

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P0-002` (reviewer `P0-2`) | P0 | **CONFIRMED** | `shopify_connector_fulfillment_mode2.py:302-332,422-429` |
| `W4-R-P1-005` (reviewer `P1-5`) | P1 | **CONFIRMED** | `shopify_connector_fulfillment_mode2.py:142-153`; `shopify_connector_fulfillment_inbound_evidence.py:168-179` |

**Root cause.** `_quantity_compatible_pickings` only proves a candidate picking's moves for the *current fulfillment's* required lines are sufficient; it never checks for the *absence* of additional moves belonging to sale lines outside that set. `_validate_picking_local` then calls `picking._action_done()` on the whole, unscoped picking — Odoo 19's `_action_done()` validates every not-done move on the picking(s) in the recordset, with no subset-scoping parameter. A genuine partial Shopify fulfillment covering one line of a two-line consolidated picking therefore silently validates and stock-deducts the sibling, un-evidenced line too, with **zero review case and zero error** (`W4-R-P0-002`). Compounding this, Condition 6's cross-fulfillment "no-overrun" ledger (`reconciled_quantity_ledger()`) is computed but never used — the actual check reads the current (always-empty, never-populated-anywhere-in-production) evidence record's own `line_ids` — so Condition 6 can never catch cumulative over-fulfillment across separate Shopify Fulfillment events on the same order line; a second, independent GID-key mismatch (`fo_line_item_gid` vs. order-level `line_item_gid`) means simply reconnecting the existing ledger call would still not compare like-for-like keys (`W4-R-P1-005`).

This is the single most architecturally significant finding in the entire review. The control room independently confirmed it as a binding P0 baseline (comment `5058826143`).

---

### Root-cause Theme C — FO-line quantity/UoM aggregation

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P1-006` (reviewer `P1-6`) | P1 | **CONFIRMED** | `shopify_connector_fulfillment_reader.py:295-341` |
| `W4-R-P2-001` (reviewer `F-5`) | Material P2 | **CONFIRMED WITH RECLASSIFICATION** | `shopify_connector_fulfillment_reader.py:300,324,333` |

**Root cause.** `_match_picking_to_fo_lines` checks each `stock.move.line`'s quantity against a FO-line's `remainingQuantity` **independently**, never aggregating/decrementing the static `remaining` value across move lines resolving to the same FO-line — a lot/serial-split shipment (a pattern this codebase already anticipates and correctly aggregates for elsewhere, `_c11_lot_serial`) can pass the guard piecemeal while its true sum exceeds `remainingQuantity`, feeding an over-committed, possibly-duplicate-line-id payload straight into the real `fulfillmentCreate` mutation (`W4-R-P1-006`). The same function never reads `stock.move.line.product_uom_id` or performs any UoM conversion (`W4-R-P2-001`) — reclassified from a plain **Fact** to an **Inference** per CLAUDE.md §7/§8, because no primary-source citation for `stock.move.line.product_uom_id`'s independent-override behavior is currently captured under `docs/00-source-materials`; the code-level gap itself (zero UoM-aware code in the file) is independently and directly confirmed regardless of that citation gap.

---

### Root-cause Theme D — Missing multi-company `ir.rule` on `shopify.connector.job`/`.mutation.attempt`

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P1-007` (reviewer `P1-7`) | P1 | **CONFIRMED WITH RECLASSIFICATION — OUTSIDE ACCEPTED WAVE 4 SCOPE** | `shopify_connector_core/security/shopify_connector_security.xml` (no rule exists); `shopify_connector_core/models/shopify_connector_job.py` |

**Root cause.** Confirmed real by full read: `shopify.connector.job` and `.mutation.attempt` carry **zero** company-based `ir.rule` anywhere in the repository (core or any addon); this PR populates the already-unscoped job model with ten new company-linked job types. **Reclassified** because: (1) the gap is pre-existing since Wave 1 and shared equally by every domain (product/sale/inventory), not introduced by this PR; (2) the correct fix location is `shopify_connector_core`, which is **explicitly forbidden** by this PR's own locked allowed/forbidden-files list (`docs/06-prompts/sol-wave-4-fulfillment-locked-prompt.md` §3) without a control-room amendment; (3) `shopify.connector.store` has **no `company_id` field** and `job`'s `res_model`/`res_id` pair is a plain Char+Integer, not ORM-traversable — so the existing `fulfillment.binding`/`.inbound.evidence` `ir.rule` pattern **cannot be mechanically copied**; this exact "store model has no company field" gap already caused an unresolved Wave 1 hard-stop (2026-07-15). **This finding must not be closed inside PR #189 or this wave** — it requires its own control-room-scoped DEC and a distinct implementation task per CLAUDE.md §9, targeting `shopify_connector_core`.

**Decision-lock update (2026-07-23):** the merge/UAT/release-candidate gate, exact implementation owner (candidate "SEC-3"), sequencing, and the frozen target access-control architecture (an `ir_attachment.py`-style `_check_access`/`_search` delegation override, not a stored `company_id` field) are now recorded in [`wave-4-tier1-decision-lock.md`](../07-implementation-plan/wave-4-tier1-decision-lock.md) Decision A. This finding's disposition above is unchanged; only the previously-open merge-gate question is now resolved: **Theme D does not block PR #189's own merge; it blocks external UAT and MVP release-candidate acceptance.**

---

### Root-cause Theme E — Fixed 200-row scan window vs. the PD-B4 watermark boundary

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P1-008` (reviewer `P1-8`) | P1 | **CONFIRMED** | `shopify_connector_fulfillment_scans.py:139-193` |
| `W4-R-P1-009` (reviewer `P1-9`) | P1 | **CONFIRMED** | `shopify_connector_fulfillment_scans.py:112-133` |
| `W4-R-P2-002` (reviewer `F-10`) | Material P2 | **CONFIRMED** | `shopify_connector_fulfillment_scans.py:38-65` |

**Root cause.** All three scan handlers (`_handle_fulfillment_mode_switch_scan`, `_handle_fulfillment_reconnect_catchup`, `_handle_fulfillment_reconciliation_check`) select their candidate record set via an identical `Binding.search([('store_id','=',store.id)], limit=200, order='id asc'|'id desc')` pattern — a fixed, non-advancing, id-ranked window with **zero** relationship to the `fulfillment_last_reconciliation_at` watermark, which is written unconditionally every run but **never read back anywhere in production code** (confirmed by repo-wide grep). This directly contradicts the verbatim, `[Decided 2026-07-17 — PD-B4]` product decision (`docs/02-product/fulfillment-operating-modes.md` §6) requiring an earlier-of(watermark-minus-overlap, latest-unresolved-evidence-boundary) boundary with a 30-day bounded default lookback for the switch scan, and the §7 "every external fulfillment... in both modes" guarantee for reconnect catch-up. For any store with >200 bindings/order-bindings, a real blocker outside the window is invisible: the mode-switch scan declares "clean" and auto-flips to Mode 2 anyway (`W4-R-P1-008`); the reconnect catch-up scan permanently misses gap-period fulfillments beyond the window (`W4-R-P1-009`); the hourly reconciliation cron permanently stops refreshing/scanning bindings beyond the window for the store's lifetime, including the sole detector for a no-auto-reverse-stock Shopify-side cancellation after Odoo validation (`W4-R-P2-002`).

---

### Root-cause Theme F — Direct-result `fulfillmentCreate` success classification bypasses status check

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P2-003` (reviewer `F-1`) | Material P2 | **CONFIRMED** | `shopify_connector_fulfillment_create_strategy.py:296-347` |

**Root cause.** `_classify_direct_fulfillment_create` treats any non-empty `fulfillment.id` with empty `userErrors` as `succeeded`, without ever reading `fulfillment.get('status')` — even though the operation document explicitly requests `status`. The **same file's** reconcile path requires `status == 'SUCCESS'` twice before accepting a fulfillment as positive evidence — a strictly stronger bar. Verified against two live shopify.dev fetches: the active `FulfillmentStatus` enum is exactly `SUCCESS`/`CANCELLED`/`ERROR`/`FAILURE` (`OPEN`/`PENDING` deprecated), so `SUCCESS` is the sole value meaning a completed fulfillment — matching this repo's own DEC-038 §3 condition #2 and `docs/02-product/shopify-fulfillment-status-model.md` §4. (The narrow sub-claim of whether the *synchronous* response can itself carry a non-SUCCESS status alongside empty `userErrors` could not be externally re-confirmed from shopify.dev and is carried as inference; the defect itself is independently and fully provable from the file's own internal inconsistency.)

---

### Root-cause Theme G — Vocabulary-guard test genuineness

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P2-004` (reviewer `F-2`) | Material P2 | **CONFIRMED** | `test_fulfillment_vocabulary_guard.py:25-42,57-64,78-86` |

**Root cause.** The containment allowlist (`FULFILLMENT_PERSISTED_CORE_CLASSES`) is a hand-typed `frozenset`, not AST-derived, despite its own docstring claiming completeness. Confirmed absent: `'unknown_system_error'`, genuinely persisted via `job._transition_failed_final` at `shopify_connector_job_dispatch.py:141`. The only containment test checks a single direction (hand-list ⊆ core-registry), never "production's actual persisted set ⊆ hand-list," so the omission is structurally undetectable. Line 84's `assertEqual(quantity_overrun_core_class, 'ambiguous_match')` is a confirmed tautology (compares a variable to the literal it was assigned two lines above).

---

### Root-cause Theme H — Mode-1 `remote_state_changed` label collision

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P2-005` (reviewer `F-3`) | Material P2 | **CONFIRMED** | `shopify_connector_fulfillment_inbound.py:173-179` |

**Root cause.** The routine Mode-1 "confirmed-external fulfillment observed" case and Mode-2 Condition 14's narrow "fresh second-read detected a state change" gate are two semantically unrelated events, both persisted under the single `review_reason` value `'remote_state_changed'`. `docs/02-product/fulfillment-operating-modes.md` §4 defines this value exclusively as Condition 14's meaning; the Mode-1 baseline path was never assigned any documented code. `test_observe_external_mode1_opens_review_case` locks in the collision as "correct." The reviewer's proposed replacement label (`mode_not_enabled`) is itself already a distinct, semantically-inverted value (Condition 16 / mid-flight mode-switch cancellation) — reusing it would create a **second** collision; a genuinely new `REVIEW_REASON_SELECTION` value is required.

**Decision-lock update (2026-07-23):** the exact new value is now frozen — [`wave-4-tier1-decision-lock.md`](../07-implementation-plan/wave-4-tier1-decision-lock.md) Decision C — `external_fulfillment_observed` (label "External Fulfillment Observed"), verified to collide with nothing in the current `REVIEW_REASON_SELECTION`/`ORIGIN_CLASS_SELECTION`/`RECONCILED_STATE_SELECTION`/core vocabularies. `review_reason`'s current count is 20; it becomes 21 once this lands, which PR #194's contract inventory must re-derive, not assume.

---

### Root-cause Theme I — Location-resolution fail-closed gap + missing warehouse cross-check

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P2-006` (reviewer `F-6`) | Material P2 | **CONFIRMED** | `shopify_connector_fulfillment_reader.py:356-387` |
| `W4-R-P2-007` (reviewer `F-4`) | Material P2 | **CONFIRMED WITH RECLASSIFICATION** | `shopify_connector_fulfillment_mode2.py:172-186,302-332` |

**Root cause.** `_resolve_single_location` has exactly three fail-closed identity-quality checks (null GID, ambiguous multi-location, absent-from-cache) but silently accepts a cached-but-`shopify_location_active=False` location instead of failing closed like its three siblings (`W4-R-P2-006` — a narrow, single-function fix with no architecture conflict). Separately, C8/C14's resolved Shopify location is never cross-checked against the selected picking's actual source warehouse (`W4-R-P2-007`) — **reclassified** because the naive remedy ("reuse existing location-mapping data") is blocked by ratified module-boundary decisions (DEC-008/DEC-011/DEC-038 Q3-RULED) forbidding `shopify_connector_fulfillment` from reading `shopify.connector.location.mapping`; this traces to an item DEC-011 (2026-07-02) explicitly left open ("the exact mechanism... remains open for the Master Blueprint") that Wave 4 Gate A's reconciliation (DEC-038) never closed. `W4-R-P2-007` is squarely inside Wave 4's required scope (Condition 8 is a named required MVP item) so it is **not** outside-Wave-4-scope, but it needs a control-room/architecture decision on the exact cross-check mechanism before any code change — it must not be code-fixed in this pass.

**Decision-lock update (2026-07-23):** [`wave-4-tier1-decision-lock.md`](../07-implementation-plan/wave-4-tier1-decision-lock.md) Decision B splits `W4-R-P2-007`/`F-4` into two: a **permanent** architecture (a new core `shopify.connector.location._resolve_odoo_location()` seam overridden by `shopify_connector_inventory`, never read directly by fulfillment) — still not authorized for this PR, a separate future task — and an **interim, now-authorized** fail-closed correction inside this PR: `_c8_location` must always route to `location_unmapped` review for the warehouse-cross-check dimension until the permanent seam exists, rather than silently returning success once the Shopify location merely resolves. This interim item is added to the correction batch as an extension of this theme (see the updated `wave-4-tier1-correction-locked-candidate.md`).

---

### Root-cause Theme J — `_has_unresolved_create_attempt` terminal-state exclusion gap

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P2-008` (reviewer `F-7`) | Material P2 | **CONFIRMED WITH RECLASSIFICATION** | `shopify_connector_fulfillment_inbound.py:82-102` |

**Root cause.** The job-state filter (`not in ('succeeded','skipped')`) fails to exclude `'cancelled'`, permanently blocking Mode-2 origin confirmation after an admin/disconnect-sweep cancels a stuck job. **Reclassified (broadened, not narrowed):** the canonical `TERMINAL_JOB_STATES = ('succeeded','failed_final','skipped','cancelled')` already exists at `shopify_connector_core/models/shopify_connector_job.py:19` and is already correctly imported/used elsewhere in this exact addon — the local tuple is missing not just `'cancelled'` but also `'failed_final'`, independently reachable with zero `mutation_attempt` via the same production paths. A narrow patch adding only `'cancelled'` would leave an identical, undetected twin defect live for `'failed_final'`. The correct minimal fix imports and reuses `TERMINAL_JOB_STATES` rather than hand-maintaining a third, divergence-prone terminal-state list.

---

### Root-cause Theme K — Concurrency-harness rigor gaps

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P2-009` (reviewer `F-8`) | Material P2 | **CONFIRMED** | `runtime_layer2_fulfillment_concurrency_harness.py` (7 of 9 runners) |
| `W4-R-P2-010` (reviewer `F-9`) | Material P2 | **CONFIRMED** | `test_fulfillment_concurrency.py:27-186,500-531` |

**Root cause.** Child exit codes are captured but never asserted in 7 of 9 scenario runners (only `mode_switch_interaction`/`rollback_injection_recovery` compare) — mechanically confirmed by full read of all 9 runners (`W4-R-P2-009`). The no-fake-success AST guard's exitcode check is pure name-presence (`ast.Attribute` named `exitcode` anywhere in the closure), never a comparison — and the guard's own bundled "genuine orchestration" acceptance example is confirmed semantically hollow on all four alleged counts (no-op process target, zero synchronization, an unscoped `search([])`, a wrong-arity `_finish_cleanup` call) yet passes the guard (`W4-R-P2-010`). This is test-infrastructure-only; no production file is implicated. High-value because it means the still-deferred nine-process runtime campaign could eventually "pass" without proving anything.

---

### Root-cause Theme L — U0 dashboard job-type label gap (out of Wave-4 scope)

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P2-011` (reviewer `F-11`) | Material P2 | **CONFIRMED — OUTSIDE ACCEPTED WAVE 4 SCOPE** | `shopify_connector_core/models/shopify_connector_ui_dashboard.py:430-439` |

**Root cause.** `_job_type_label`'s hand-rolled dict has zero entries for any of fulfillment's ten job types (confirmed genuinely zero-of-ten, not partial); every fulfillment job falls through to the generic "Sync job" label. Confirmed **not** a regression this PR introduced: `git diff dd0af5d9..2d9cff0 -- .../shopify_connector_ui_dashboard.py` is empty. The file lives in `shopify_connector_core`, outside PR #189's authorized allowed-file list, and `docs/07-implementation-plan/wave-4-definition-of-ready.md` §3 explicitly places "dashboards/timelines" in Wave 4's **forbidden** list, reserved for Wave 5. **Must not be patched inside PR #189** — route to the Wave 5/U0 dashboard owner or obtain an explicit control-room scope amendment.

---

### Root-cause Theme M — Governance-document corrections

| ID | Reviewer severity | Disposition | File(s) / lines |
| --- | --- | --- | --- |
| `W4-R-P2-012` (reviewer `F-12`) | Material P2 | **CONFIRMED** | `docs/05-qa/technical-debt-register.md:27` |
| `W4-R-P2-013` (reviewer `F-13`) | Material P2 | **CONFIRMED** | `docs/01-research/research-handoff.md:128-135` |

**Root cause.** TD-002 was marked `**Resolved**` for an unmerged, not-independently-reviewed draft PR — breaking this same register's own TD-001 precedent (a named merge commit + completed, passing, pre-merge Odoo.sh runtime evidence) and directly contradicted by the register's own footer note two lines below ("TD-002... remains Open for code"). Per the register's own status legend, the correct value is `In progress` (`W4-R-P2-012` — **corrected by this synthesis commit**, see §7 below). `research-handoff.md`'s Wave 4 Gate B "Exact next-session prompt" still routes the routine review to "CHATGPT CONTROL ROOM," contradicting DEC-039/DEC-040 (both merged ahead of the reviewed commit), which make independent Claude review the default routine gate; `mvp-program-state.md` already reflects the correct model, confirming the inconsistency is confined to `research-handoff.md` (`W4-R-P2-013` — **corrected by this synthesis commit**, see §7 below).

---

## 4. Non-blocking observation recovered from the review narrative

| ID | Disposition | Detail |
| --- | --- | --- |
| `W4-R-OBS-001` | CONFIRMED (non-blocking) | §8 of the review: `models/__init__.py`'s "dependency order" comment describes an ordering Odoo doesn't actually enforce — a cosmetic, no-reachable-failure observation. No correction required; logged for completeness only. |

## 5. Tier-3 / further observation items — not individually recoverable

The review states (§31 closing note): *"~15 further tier3/observation/deferred_risk items were also raised across dimensions — none blocking, omitted here per the review protocol's non-blocking exclusion."* This synthesis located **exactly one** such item with enough detail to log individually (`W4-R-OBS-001` above, from §8). The remaining ~14 items are referenced only in aggregate; comment `5058257403` does not name, locate, or describe them individually anywhere in its text. **This synthesis does not fabricate content for these ~14 items.** This is logged as an **open question**, not asserted as resolved: a future session with access to the reviewer's own dimension-by-dimension working notes (if retained outside the posted PR comment) could recover them; absent that, they remain non-blocking and unrecoverable from the record actually available to this synthesis.

## 6. Carried, not re-litigated

Per the review's own §30 and the control-room ruling, the following remain unchanged by this synthesis:

1. The nine-process external-multiprocessing campaign: `DEFERRED BY PRODUCT OWNER — NOT PROVEN` (comment `5055372944`).
2. Issue #185 (`CV-013`): open and critical.
3. Issue #193 (baseline warm-update fixture defect): open, separate owner.
4. Additional isolated clean-install / isolated upgrade / full uninstall-reinstall-residue / browser-HOOT-screenshot evidence: `DEFERRED BY PRODUCT OWNER — NOT PROVEN`.

## 7. Static reconciliation proof

- Every one of the review's 24 named findings (`P0-1`,`P0-2`,`P1-1`…`P1-9`,`F-1`…`F-13`) appears in exactly one theme above, exactly once.
- 2 P0 + 9 P1 + 13 material P2 = 24, matching §31's severity subtotals exactly.
- 0 findings refuted; 0 findings are true duplicates (see §1 for why the raw count differs from 24 without any finding being invalid).
- 2 findings (`P1-7`, `F-11`) are fully outside this PR's implementable scope; 1 finding (`F-4`) is partially so (needs an architecture decision, not an in-PR patch).
- 1 new finding (`ADDITIONAL-1`) and 1 recoverable observation (`OBS-1`) were added by this synthesis, both clearly marked as not part of the reviewer's original 24/25/26.

See `wave-4-tier1-correction-synthesis.md` for the full root-cause synthesis, correction boundaries, test/runtime matrix, migration analysis, and U1 impact assessment built from this ledger.
